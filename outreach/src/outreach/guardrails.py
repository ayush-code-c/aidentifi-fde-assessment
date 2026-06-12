"""Anti-hallucination guardrail: verify the generated message is grounded.

After composition we scan the message for SPECIFICS (capitalised multi-word
proper nouns, quoted phrases) that do not trace back to an approved hook or the
recipient's own known fields. Anything unsourced is flagged. This is the
'do you hallucinate to fill the gap?' check made mechanical - for sparse
recipients especially, where the temptation to invent is highest.

The guardrail does not silently rewrite; it returns flags so the reviewer (and
the per-recipient report) sees exactly what was unverifiable. That is the
'flag uncertainty to the user' behaviour the brief asks for.
"""
from __future__ import annotations

import re

from .model import Recipient

# Words that are allowed even though capitalised (sentence starts, our own name).
_STOP = {
    "Hi", "Best", "Would", "Saw", "Given", "Happy", "The", "I", "Aidentifi",
    "Senior", "On", "AI", "It", "We", "Your", "A", "An", "Our", "If", "That",
    "This", "There",
}


def check_grounding(message: dict, recipient: Recipient, approved_hooks: list[str]) -> list[str]:
    flags: list[str] = []
    text = f"{message.get('subject','')} {message.get('body','')}"

    known = " ".join([
        recipient.name, recipient.title, recipient.company, recipient.industry,
        recipient.location, " ".join(approved_hooks),
    ]).lower()

    # 1. Unsourced proper nouns. We flag a capitalised token sequence only when it
    #    looks like a real name/org, not a sentence-initial English word. Rule:
    #    multi-word capitalised sequences always checked; single capitalised words
    #    only when they appear MID-sentence (a sentence-initial single capital is
    #    almost always ordinary prose, not a proper noun).
    for m in re.finditer(r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)", text):
        token = m.group(1)
        words = token.split()
        head = words[0]
        # sentence-initial? look at the last non-space char before the match.
        start = m.start()
        prev = text[:start].rstrip()
        sentence_initial = (not prev) or prev[-1] in ".!?:\n"
        if head in _STOP:
            continue
        if token.lower() in known or all(w.lower() in known for w in words):
            continue
        if len(words) == 1 and sentence_initial:
            continue  # ordinary sentence start, not a proper noun
        flags.append(f"unsourced proper noun: '{token}'")

    # 2. Claims of hiring when no hook supports it.
    hooks_l = " ".join(approved_hooks).lower()
    if re.search(r"\b(you'?re hiring|your open role|the role you'?re filling)\b", text, re.I):
        if "hir" not in hooks_l and recipient.hiring_signal not in ("strong", "medium"):
            flags.append("asserts recipient is hiring with no supporting hook")

    # 3. Fabricated relationship.
    if re.search(r"\b(we met|last time|as we discussed|our mutual|reconnect)\b", text, re.I):
        flags.append("implies a prior relationship that is not in the data")

    # de-dup
    seen = set()
    return [f for f in flags if not (f in seen or seen.add(f))]
