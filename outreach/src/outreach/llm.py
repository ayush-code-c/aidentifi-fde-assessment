"""Message composition — provider-agnostic.

Two tiers, by design (this maps directly onto the scalability story):
  * "mock"  = a deterministic TEMPLATE composer. Key-free, reproducible, and is
              literally the fallback tier we'd run on the long tail at 100+
              recipients. Good, not bespoke.
  * "anthropic"/"openai" = the BESPOKE tier. Same grounded brief, but the model
              writes in a senior-partner register. Used for high-value recipients.

Crucially, BOTH tiers receive the *same grounded brief*: the angle, the approved
hooks (already confidence-filtered), and explicit instructions never to invent.
Grounding is enforced upstream (only approved hooks are passed) and downstream
(guardrails.py), so neither tier can reference unsourced specifics.
"""
from __future__ import annotations

import json
import re
import textwrap
from dataclasses import dataclass


@dataclass
class Brief:
    first_name: str
    register: str               # "email" | "linkedin"
    greeting: str
    signoff: str
    max_words: int
    angle_thesis: str
    cta: str
    company_one_liner: str
    approved_hooks: list[str]   # already confidence-filtered & sourced (text only)
    is_sparse: bool
    specific_clauses: list[str] = None   # inline-ready clauses (specific hooks)
    category_phrases: list[str] = None   # inline-ready phrases (category hooks)

    def __post_init__(self):
        self.specific_clauses = self.specific_clauses or []
        self.category_phrases = self.category_phrases or []


SYSTEM = (
    "You write business-development outreach for an executive-search firm, in the "
    "register a senior partner would write themselves: direct, specific, no "
    "marketing adjectives, one idea, one soft ask. You may ONLY reference facts in "
    "APPROVED_HOOKS. You must never invent a fact, a mutual connection, a deal, or "
    "a claim that the recipient is hiring unless an approved hook says so. If hooks "
    "are thin, stay general and honest rather than specific and fabricated. Return "
    "JSON: {\"subject\": \"...\", \"body\": \"...\"}."
)


class Composer:
    def __init__(self, provider="mock", model="claude-sonnet-4-6",
                 anthropic_key=None, openai_key=None):
        self.provider = provider
        self.model = model
        self._ak = anthropic_key
        self._ok = openai_key
        self._client = None

    def compose(self, brief: Brief) -> dict:
        if self.provider == "mock":
            return self._template(brief)
        try:
            if self.provider == "anthropic":
                return self._anthropic(brief)
            if self.provider == "openai":
                return self._openai(brief)
        except Exception as exc:  # graceful fallback to template
            out = self._template(brief)
            out["subject"] = out["subject"]
            out["_fallback"] = f"{type(exc).__name__}: composer fell back to template"
            return out
        raise ValueError(f"unknown provider {self.provider!r}")

    # -- bespoke tiers -----------------------------------------------------
    def _prompt(self, b: Brief) -> str:
        hooks = "\n".join(f"- {h}" for h in b.approved_hooks) or "- (none — sparse profile)"
        return textwrap.dedent(f"""\
            ABOUT_US: {b.company_one_liner}
            ANGLE_THESIS: {b.angle_thesis}
            CALL_TO_ACTION: propose {b.cta}
            REGISTER: {b.register}, hard limit {b.max_words} words in the body.
            GREETING: "{b.greeting}"   SIGNOFF: "{b.signoff}"
            SPARSE_PROFILE: {b.is_sparse}  (if true, do NOT imply you know specifics)
            APPROVED_HOOKS (the ONLY facts you may reference):
            {hooks}
            Write the outreach now.""")

    def _anthropic(self, b: Brief) -> dict:
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._ak)
        msg = self._client.messages.create(
            model=self.model, max_tokens=400, system=SYSTEM,
            messages=[{"role": "user", "content": self._prompt(b)}])
        return self._parse(msg.content[0].text, b)

    def _openai(self, b: Brief) -> dict:
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._ok)
        resp = self._client.chat.completions.create(
            model=self.model, max_tokens=400,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": self._prompt(b)}])
        return self._parse(resp.choices[0].message.content, b)

    @staticmethod
    def _parse(raw: str, b: Brief) -> dict:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group()) if m else {"subject": "", "body": raw}
        return {"subject": str(data.get("subject", "")).strip(),
                "body": str(data.get("body", "")).strip()}

    # -- deterministic template tier (also the 100+ scale fallback) --------
    def _template(self, b: Brief) -> dict:
        category = b.category_phrases[0] if b.category_phrases else "your work"
        if b.is_sparse or not b.specific_clauses:
            # honest, category-level opener — no invented specifics
            opener = (f"I run executive search at a firm focused on senior hiring, and "
                      f"{category} puts you squarely in the space we work in.")
            subject = "Senior search — a quick introduction"
            second_line = ""
        else:
            opener = (f"{b.specific_clauses[0]} — that's exactly the kind of moment "
                      f"we're built for.")
            subject = "On your senior hiring"
            second_line = (
                f" {b.specific_clauses[1]}, so that fit problem is likely already on your desk."
                if len(b.specific_clauses) > 1 else ""
            )
        body = (
            f"{b.greeting}\n\n"
            f"{opener} {b.company_one_liner}\n\n"
            f"{b.angle_thesis}{second_line}\n\n"
            f"Would {b.cta} be worth a short slot? Happy to work around you.\n\n"
            f"{b.signoff}"
        )
        body = self._truncate_words(body, b.max_words + 40)  # +greeting/signoff slack
        return {"subject": subject, "body": body}

    @staticmethod
    def _truncate_words(text: str, max_words: int) -> str:
        words = text.split()
        return text if len(words) <= max_words else " ".join(words[:max_words]) + "…"
