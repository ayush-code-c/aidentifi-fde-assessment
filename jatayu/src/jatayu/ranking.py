"""Ranking + rationale generation.

Ranking is a deterministic sort on fit_score with config-declared tie-breakers,
so the order is reproducible and explainable. Rationale is templated from the
candidate's own strongest/weakest sub-scores - plain English, 2-4 lines - so it
never asserts anything the scores don't support (no hallucinated detail).
"""
from __future__ import annotations

from typing import Any

from .scoring import ScoredProfile


def rank(scored: list[ScoredProfile], cfg: dict) -> list[ScoredProfile]:
    tb = cfg["ranking"].get("tie_breakers", [])

    def key(sp: ScoredProfile):
        k = [-sp.fit_score]
        for t in tb:
            if t == "years_relevant_experience":
                k.append(-sp.years_relevant)
            elif t in sp.sub_scores:
                k.append(-sp.sub_scores[t].blended)
        return tuple(k)

    ranked = sorted(scored, key=key)
    for sp in ranked:
        sp.rationale = _rationale(sp, cfg)
    return ranked


def _rationale(sp: ScoredProfile, cfg: dict) -> str:
    subs = sorted(sp.sub_scores.values(), key=lambda s: -s.blended)
    strongest = subs[0]
    weakest = subs[-1]
    p = sp.profile
    title = p.get("current_title") or p.get("title") or "-"
    company = p.get("current_company") or p.get("active_experience_company_name") or "-"

    line1 = (
        f"{title} at {company}; ~{sp.years_relevant:g} yrs in-function. "
        f"Strongest on {strongest.label.lower()} ({strongest.blended})."
    )
    # name the single best deterministic evidence hit if any
    evidence = next((h for h in strongest.hits if h.startswith("+")), None)
    line2 = (
        f"Key signal: {evidence.split(' ', 1)[1]}." if evidence
        else "Fit driven mainly by rubric judgment; deterministic signal thin."
    )
    line3 = (
        f"Watch: {weakest.label.lower()} is the soft spot ({weakest.blended})."
        if weakest.blended < 55
        else "No major dimension below threshold."
    )
    return " ".join([line1, line2, line3])
