"""Build the Coresignal search query (Elasticsearch DSL) from mandate config.

Coresignal's clean "Employee/Member" search API accepts an ES bool query. We
translate the declarative `filter:` block of the mandate YAML into that DSL.
Keeping this in one place means a recruiter changing the mandate never has to
understand Elasticsearch - they edit YAML, we compile.

The same builder also exposes `local_predicate()` - the identical filter logic
applied in-process to fixtures in offline mode, so offline and live runs select
the same candidates.
"""
from __future__ import annotations

import re
from typing import Any


def build_es_query(filter_cfg: dict[str, Any]) -> dict[str, Any]:
    """Compile mandate `filter:` into a Coresignal ES bool query."""
    must: list[dict] = []
    should: list[dict] = []
    must_not: list[dict] = []

    # --- geography (hard) ---
    countries = filter_cfg.get("location", {}).get("countries", [])
    if countries:
        must.append({"terms": {"location_country": [c for c in countries]}})

    # --- active role (hard) ---
    if filter_cfg.get("active_experience"):
        must.append({"term": {"active_experience": True}})

    # --- function gate on title/headline (permissive OR) ---
    title_any = filter_cfg.get("title_any", [])
    if title_any:
        must.append(
            {
                "bool": {
                    "should": [
                        {"match_phrase": {"title": t}} for t in title_any
                    ]
                    + [{"match_phrase": {"headline": t}} for t in title_any],
                    "minimum_should_match": 1,
                }
            }
        )

    # --- industry gate (permissive OR over experience.company_industry) ---
    industry_any = filter_cfg.get("industry_any", [])
    if industry_any:
        must.append(
            {
                "bool": {
                    "should": [
                        {"match_phrase": {"experience.company_industry": i}}
                        for i in industry_any
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    # --- exclusions ---
    for t in filter_cfg.get("must_not_title", []):
        must_not.append({"match_phrase": {"title": t}})
    for c in filter_cfg.get("must_not_current_company", []):
        must_not.append({"match_phrase": {"active_experience_company_name": c}})

    query = {"query": {"bool": {}}}
    if must:
        query["query"]["bool"]["must"] = must
    if should:
        query["query"]["bool"]["should"] = should
    if must_not:
        query["query"]["bool"]["must_not"] = must_not
    return query


# ---------------------------------------------------------------------------
# Local (offline) equivalent of the same filter, applied to fixture profiles.
# ---------------------------------------------------------------------------
def local_predicate(filter_cfg: dict[str, Any]):
    """Return a predicate(profile)->bool mirroring the ES query, for fixtures."""
    countries = {c.lower() for c in filter_cfg.get("location", {}).get("countries", [])}
    title_any = [t.lower() for t in filter_cfg.get("title_any", [])]
    industry_any = [i.lower() for i in filter_cfg.get("industry_any", [])]
    mn_title = [t.lower() for t in filter_cfg.get("must_not_title", [])]
    mn_company = [c.lower() for c in filter_cfg.get("must_not_current_company", [])]
    exp_cfg = filter_cfg.get("experience", {})
    min_years = exp_cfg.get("min_years_in_function", 0)
    fn_kw = [k.lower() for k in exp_cfg.get("function_keywords", [])]

    def _titles(profile) -> list[str]:
        out = [str(profile.get("title", "")), str(profile.get("headline", ""))]
        for e in profile.get("experience", []):
            out.append(str(e.get("title", "")))
        return [t.lower() for t in out if t]

    def _industries(profile) -> list[str]:
        return [
            str(e.get("company_industry", "")).lower()
            for e in profile.get("experience", [])
        ]

    def pred(profile) -> bool:
        # geography
        if countries:
            loc = str(profile.get("location_country", "")).lower()
            if loc not in countries:
                return False
        # active role
        if filter_cfg.get("active_experience") and not profile.get(
            "active_experience", True
        ):
            return False
        titles = _titles(profile)
        joined_titles = " | ".join(titles)
        # function gate
        if title_any and not any(t in joined_titles for t in title_any):
            return False
        # industry gate
        if industry_any:
            inds = " | ".join(_industries(profile))
            if not any(i in inds for i in industry_any):
                return False
        # exclusions
        if any(any(t in tt for tt in titles) for t in mn_title):
            return False
        cur_company = str(
            profile.get("active_experience_company_name", "")
            or profile.get("current_company", "")
        ).lower()
        if any(c in cur_company for c in mn_company):
            return False
        # min years in function
        if min_years:
            if years_in_function(profile, fn_kw) < min_years:
                return False
        return True

    return pred


def years_in_function(profile, fn_keywords: list[str]) -> float:
    """Approximate total years spent in roles matching the function keywords."""
    total = 0.0
    for e in profile.get("experience", []):
        title = str(e.get("title", "")).lower()
        if fn_keywords and not any(k in title for k in fn_keywords):
            continue
        total += _role_years(e)
    return round(total, 1)


def _role_years(exp: dict) -> float:
    """Years for one role; uses explicit duration_months if present else dates."""
    if exp.get("duration_months"):
        return exp["duration_months"] / 12.0
    df, dt = exp.get("date_from"), exp.get("date_to")
    if not df:
        return 0.0
    y0 = _year(df)
    y1 = _year(dt) if dt else 2026  # open role -> assume present
    if y0 is None or y1 is None:
        return 0.0
    return max(0.0, y1 - y0)


def _year(s: str | None) -> int | None:
    if not s:
        return None
    m = re.search(r"(19|20)\d{2}", str(s))
    return int(m.group()) if m else None
