"""Angle selection: map a recipient + their hooks to the best value-prop angle.

Deterministic, rule-based, and explainable — the angle choice is itself a piece
of judgment a reviewer can audit. Falls back to `general_introduction` when
signals are too thin to justify a specific angle (the sparse path).
"""
from __future__ import annotations

from .enrich import Hook
from .model import Recipient


def select_angle(r: Recipient, hooks: list[Hook], cfg: dict) -> tuple[str, str]:
    """Return (angle_key, why_this_angle)."""
    sn = (r.seniority or "").lower()
    ind = (r.industry or "").lower()
    has_specific = any(h.kind == "specific" and h.confidence >= 0.6 for h in hooks)

    # PE/VC building leadership across a portfolio.
    if "private equity" in ind or "venture" in ind or sn == "partner":
        return "portfolio_talent", "PE/VC partner who builds leadership across portfolio cos"

    # Founder / principal making an early high-stakes senior hire.
    if sn in ("founder", "principal") and r.hiring_signal == "strong":
        return "scaling_senior_team", "founder with an explicit senior-hiring signal"
    if sn in ("founder", "principal"):
        return "founder_first_senior_hire", "founder/principal — first senior hire is high-stakes"

    # Owner of a niche/regulated senior function.
    if any(k in ind for k in ("asset management", "wealth", "compliance", "risk", "fund")):
        return "hard_to_fill_niche", "owns a niche/regulated senior function"

    # Visible growth + a hiring signal.
    if r.hiring_signal in ("strong", "medium") and has_specific:
        return "scaling_senior_team", "visible growth with a hiring signal"

    # Thin signals -> honest, category-level introduction.
    return "general_introduction", "signals too thin for a specific angle (sparse path)"
