"""Evidence extraction: turn a recipient's raw data into HOOKS with confidence.

A hook is a single, citable fact the message is allowed to lean on. Each carries
a confidence in [0,1] and a `kind`:
  * specific  — a concrete, recipient-unique fact (a post, a named event, a
                stated hiring intent). High value, must be well-sourced.
  * category  — role/industry/seniority truth. Always available, low specificity;
                safe to use for sparse recipients without fabricating.

Confidence is assigned by SOURCE, not by the model's enthusiasm. An explicit
hiring statement the recipient wrote is high; an inference from a bio is medium;
a bare title is category-level. This is the core anti-hallucination primitive:
the generator may only use hooks above the configured confidence threshold, so a
sparse recipient simply has fewer high-confidence hooks and gets a more generic
(but honest) message.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .model import Recipient


@dataclass
class Hook:
    text: str          # the fact, phrased for the model to reference
    confidence: float  # 0..1, assigned by source reliability
    kind: str          # "specific" | "category"
    basis: str         # which field it came from (audit trail)


HIRING_WORDS = re.compile(
    r"\b(hir(e|ing)|recruit|build(ing)? out|expand(ing)?|scal(e|ing)|"
    r"open role|leadership|senior (hire|role|leader))\b",
    re.I,
)


def extract_hooks(r: Recipient) -> list[Hook]:
    hooks: list[Hook] = []

    # --- specific hooks (high value, source-graded) ---------------------
    if r.recent_activity:
        # Quoted/explicit activity is the strongest signal we have.
        conf = 0.85 if '"' in r.recent_activity or "'" in r.recent_activity else 0.75
        if HIRING_WORDS.search(r.recent_activity):
            conf = max(conf, 0.9)
        hooks.append(Hook(r.recent_activity.strip().strip('"'), conf, "specific",
                          "recent_activity"))

    if r.hiring_signal == "strong":
        hooks.append(Hook("is actively hiring senior leadership", 0.85, "specific",
                          "hiring_signal"))
    elif r.hiring_signal == "medium":
        hooks.append(Hook("appears to be building out senior functions", 0.55,
                          "specific", "hiring_signal"))

    if r.bio:
        # Bio facts are useful but inferred — capped at medium confidence, and we
        # only surface the most concrete sentence, not the whole bio.
        sent = _most_concrete_sentence(r.bio)
        if sent:
            hooks.append(Hook(sent, 0.6, "specific", "bio"))

    # --- category hooks (always available, never fabricated) ------------
    if r.title and r.has_company:
        hooks.append(Hook(f"{r.title} at {r.company}", 0.95, "category",
                          "title+company"))
    elif r.title:
        hooks.append(Hook(f"a {r.title}", 0.9, "category", "title"))
    if r.industry:
        hooks.append(Hook(f"works in {r.industry}", 0.9, "category", "industry"))

    # sort by confidence desc, specific before category at equal confidence
    hooks.sort(key=lambda h: (-h.confidence, 0 if h.kind == "specific" else 1))
    return hooks


def _most_concrete_sentence(bio: str) -> str:
    """Pick the bio sentence with the most concrete signal (numbers, verbs)."""
    sentences = re.split(r"(?<=[.;])\s+", bio)
    if not sentences:
        return ""
    def score(s):
        return (len(re.findall(r"\d", s)) * 2
                + len(re.findall(r"\b(scaled|founded|built|led|owns|closed|sits)\b", s, re.I)))
    best = max(sentences, key=score)
    return best.strip() if score(best) > 0 else ""
