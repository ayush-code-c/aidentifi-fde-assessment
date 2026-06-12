"""Scoring engine - deterministic features blended with an LLM rubric pass.

Each sub-score is computed twice:
  * deterministic - transparent, auditable rules declared in the mandate YAML.
  * llm           - a rubric judgment for the nuanced "texture" the brief
                    describes (sole-ownership, firm-scale fit, etc.).
The two are blended per-sub-score (`llm_blend`). This is the recruiter-override
path: every number traces back to a config weight or a logged rule hit, and the
per-rule contributions are emitted into the scoring-intermediate CSV.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .filters import years_in_function, _role_years, _year
from .llm import LLMScorer

DET_BASELINE = 35  # deterministic score floor before rule contributions


@dataclass
class SubScoreResult:
    name: str
    label: str
    weight: float
    deterministic: int
    llm: int
    llm_why: str
    blended: int
    hits: list[str] = field(default_factory=list)  # human-readable rule hits


@dataclass
class ScoredProfile:
    profile: dict
    sub_scores: dict[str, SubScoreResult]
    fit_score: int
    years_relevant: float
    confidence: str
    flags: list[str]
    rationale: str = ""


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def _corpus(profile: dict) -> str:
    parts = [
        str(profile.get("title", "")),
        str(profile.get("headline", "")),
        str(profile.get("summary", "")),
    ]
    for e in profile.get("experience", []):
        parts += [
            str(e.get("title", "")),
            str(e.get("description", "")),
            str(e.get("company_name", "")),
            str(e.get("company_industry", "")),
        ]
    parts += [str(s) for s in profile.get("skills", [])]
    for ed in profile.get("education", []):
        parts.append(str(ed.get("title", "")) + " " + str(ed.get("subtitle", "")))
    return " \n ".join(parts).lower()


def _titles(profile: dict) -> str:
    out = [str(profile.get("title", "")), str(profile.get("headline", ""))]
    out += [str(e.get("title", "")) for e in profile.get("experience", [])]
    return " | ".join(out).lower()


def _summary(profile: dict) -> str:
    return str(profile.get("summary", "")).lower()


def sg_tenure_years(profile: dict) -> float:
    """Years of Singapore-based experience (proxy for local roots/commitment)."""
    total = 0.0
    saw_sg_role = False
    for e in profile.get("experience", []):
        loc = (str(e.get("location", "")) + str(e.get("company_location", ""))).lower()
        if "singapore" in loc:
            saw_sg_role = True
            total += _role_years(e)
    if total == 0.0 and str(profile.get("location_country", "")).lower() == "singapore":
        # No per-role geo, but currently in SG: approximate by total career span.
        years = [
            _year(e.get("date_from"))
            for e in profile.get("experience", [])
            if _year(e.get("date_from"))
        ]
        if years:
            total = max(0.0, 2026 - min(years))
    return round(total, 1)


def _company_sizes(profile: dict) -> list[int]:
    out = []
    for e in profile.get("experience", []):
        s = e.get("company_size")
        if isinstance(s, (int, float)):
            out.append(int(s))
        elif isinstance(s, str):
            m = re.search(r"\d[\d,]*", s)
            if m:
                out.append(int(m.group().replace(",", "")))
    return out


def _moved_buy_side(profile: dict) -> bool:
    buy = ("investment management", "asset management", "venture capital", "family office")
    return any(
        any(b in str(e.get("company_industry", "")).lower() for b in buy)
        for e in profile.get("experience", [])
    )


# ---------------------------------------------------------------------------
# Deterministic rule evaluation
# ---------------------------------------------------------------------------
def _eval_rule(profile: dict, rule: dict, fn_keywords: list[str]) -> tuple[float, str | None]:
    """Return (points_applied, hit_label_or_None)."""
    pts = rule.get("points", 0)
    titles = _titles(profile)
    summary = _summary(profile)
    corpus = _corpus(profile)

    if "any_title" in rule:
        for t in rule["any_title"]:
            if t.lower() in titles:
                return pts, f"title~'{t}'"
        return 0, None
    if "regex_summary" in rule:
        if re.search(rule["regex_summary"], summary, re.I):
            return pts, f"summary~/{rule['regex_summary']}/"
        return 0, None
    if "regex_any" in rule:
        matches = re.findall(rule["regex_any"], corpus, re.I)
        if matches:
            if rule.get("repeatable"):
                n = len(set(m if isinstance(m, str) else m[0] for m in matches))
                applied = min(rule.get("cap", pts * n), pts * n)
                return applied, f"text~/{rule['regex_any']}/x{n}"
            return pts, f"text~/{rule['regex_any']}/"
        return 0, None
    if "company_industry_any" in rule:
        inds = " | ".join(
            str(e.get("company_industry", "")).lower()
            for e in profile.get("experience", [])
        )
        for i in rule["company_industry_any"]:
            if i.lower() in inds:
                return pts, f"industry~'{i}'"
        return 0, None
    if "company_size_lte" in rule:
        sizes = _company_sizes(profile)
        if sizes and min(sizes) <= rule["company_size_lte"]:
            return pts, f"company_size<= {rule['company_size_lte']}"
        return 0, None
    if "company_size_gte" in rule:
        sizes = _company_sizes(profile)
        if sizes and max(sizes) >= rule["company_size_gte"]:
            return pts, f"company_size>= {rule['company_size_gte']}"
        return 0, None
    if "company_name_any" in rule:
        names = " | ".join(
            str(e.get("company_name", "")).lower() for e in profile.get("experience", [])
        )
        for n in rule["company_name_any"]:
            if n.lower() in names:
                if rule.get("only_if_no_industry_move") and _moved_buy_side(profile):
                    return 0, None
                return pts, f"company~'{n}'"
        return 0, None
    if "sg_tenure_years_gte" in rule:
        if sg_tenure_years(profile) >= rule["sg_tenure_years_gte"]:
            return pts, f"sg_tenure>= {rule['sg_tenure_years_gte']}"
        return 0, None
    if "sg_tenure_years_lte" in rule:
        if sg_tenure_years(profile) <= rule["sg_tenure_years_lte"]:
            return pts, f"sg_tenure<= {rule['sg_tenure_years_lte']}"
        return 0, None
    if "years_in_function_between" in rule:
        lo, hi = rule["years_in_function_between"]
        y = years_in_function(profile, fn_keywords)
        if lo <= y <= hi:
            return pts, f"years_in_function in [{lo},{hi}]"
        return 0, None
    if "years_in_function_lte" in rule:
        if years_in_function(profile, fn_keywords) <= rule["years_in_function_lte"]:
            return pts, f"years_in_function<= {rule['years_in_function_lte']}"
        return 0, None
    return 0, None


def _deterministic_subscore(profile, sub_cfg, fn_keywords):
    score = float(DET_BASELINE)
    hits: list[str] = []
    det = sub_cfg.get("deterministic", {})
    for rule in det.get("positive", []):
        pts, label = _eval_rule(profile, rule, fn_keywords)
        if pts:
            score += pts
            if label:
                hits.append(f"+{pts:g} {label}")
    for rule in det.get("negative", []):
        pts, label = _eval_rule(profile, rule, fn_keywords)
        if pts:
            score += pts  # pts already negative
            if label:
                hits.append(f"{pts:g} {label}")
    return int(max(0, min(100, round(score)))), hits


# ---------------------------------------------------------------------------
# Top-level scoring
# ---------------------------------------------------------------------------
def score_profile(profile: dict, cfg: dict, llm: LLMScorer) -> ScoredProfile:
    scoring_cfg = cfg["scoring"]
    fn_keywords = cfg["filter"].get("experience", {}).get("function_keywords", [])
    default_blend = scoring_cfg.get("llm_blend_default", 0.5)
    corpus = _corpus(profile)

    results: dict[str, SubScoreResult] = {}
    fit = 0.0
    for name, sub in scoring_cfg["sub_scores"].items():
        det, hits = _deterministic_subscore(profile, sub, fn_keywords)
        blend = sub.get("llm_blend", default_blend)
        if blend > 0 and sub.get("llm_rubric"):
            r = llm.score(sub["llm_rubric"], corpus)
            llm_score, why = r.score, r.justification
        else:
            llm_score, why = det, "deterministic-only"
        blended = int(round((1 - blend) * det + blend * llm_score))
        results[name] = SubScoreResult(
            name=name, label=sub.get("label", name), weight=sub["weight"],
            deterministic=det, llm=llm_score, llm_why=why, blended=blended, hits=hits,
        )
        fit += sub["weight"] * blended

    fit_score = int(round(fit))
    years = years_in_function(profile, fn_keywords)
    confidence = _confidence(profile, cfg)
    flags = _flags(profile, results, cfg)
    return ScoredProfile(
        profile=profile, sub_scores=results, fit_score=fit_score,
        years_relevant=years, confidence=confidence, flags=flags,
    )


def _confidence(profile: dict, cfg: dict) -> str:
    rules = cfg["ranking"].get("confidence", {})
    need = rules.get("high_if_fields_present", [])
    present = all(profile.get(f) for f in need)
    summary_len = len(str(profile.get("summary", "")))
    if summary_len < rules.get("low_if_summary_chars_lt", 0):
        return "low"
    if present:
        return "high"
    return "medium"


def _flags(profile, results: dict[str, SubScoreResult], cfg: dict) -> list[str]:
    flags: list[str] = []
    for rule in cfg["ranking"].get("flag_rules", []):
        if "if_sub_score_below" in rule:
            for sub_name, thresh in rule["if_sub_score_below"].items():
                if sub_name in results and results[sub_name].blended < thresh:
                    flags.append(rule["flag"])
        if "if_sg_tenure_below_years" in rule:
            if sg_tenure_years(profile) < rule["if_sg_tenure_below_years"]:
                flags.append(rule["flag"])
    # de-dup, preserve order
    seen = set()
    return [f for f in flags if not (f in seen or seen.add(f))]
