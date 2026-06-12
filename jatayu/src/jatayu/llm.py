"""Provider-agnostic LLM scorer for the rubric pass.

Providers:
  * "anthropic" - Claude (uses ANTHROPIC_API_KEY).
  * "openai"    - GPT (uses OPENAI_API_KEY).
  * "mock"      - deterministic, key-free. Scores by hashing rubric+evidence
                  into a stable pseudo-judgment. Lets the whole pipeline run and
                  produce every deliverable with zero external dependencies, and
                  makes offline runs reproducible.

The rubric pass returns an integer 0-100 plus a one-line justification. We force
JSON output and parse defensively; any failure degrades to a neutral 50 with a
flag rather than crashing a 250-credit production run.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass


@dataclass
class RubricResult:
    score: int          # 0-100
    justification: str
    ok: bool = True     # False => model failed, neutral fallback used


SYSTEM = (
    "You are a meticulous executive-search analyst. You score how well a "
    "candidate matches one specific rubric dimension. You never invent facts not "
    "present in the evidence. If evidence is thin, you score conservatively and "
    "say so. Respond ONLY with compact JSON: "
    '{"score": <int 0-100>, "why": "<<=20 words>"}.'
)


class LLMScorer:
    def __init__(self, provider: str, model: str, anthropic_key=None, openai_key=None):
        self.provider = provider
        self.model = model
        self._anthropic_key = anthropic_key
        self._openai_key = openai_key
        self._client = None

    # -- public ------------------------------------------------------------
    def score(self, rubric: str, evidence: str) -> RubricResult:
        prompt = (
            f"RUBRIC:\n{rubric}\n\nCANDIDATE EVIDENCE:\n{evidence[:6000]}\n\n"
            "Score this dimension 0-100."
        )
        try:
            raw = self._call(prompt)
            return self._parse(raw)
        except Exception as exc:  # never let one profile kill the run
            return RubricResult(50, f"llm-fallback: {type(exc).__name__}", ok=False)

    # -- providers ---------------------------------------------------------
    def _call(self, prompt: str) -> str:
        if self.provider == "mock":
            return self._mock(prompt)
        if self.provider == "anthropic":
            return self._anthropic(prompt)
        if self.provider == "openai":
            return self._openai(prompt)
        raise ValueError(f"unknown LLM provider {self.provider!r}")

    def _anthropic(self, prompt: str) -> str:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._anthropic_key)
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=120,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    def _openai(self, prompt: str) -> str:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._openai_key)
        resp = self._client.chat.completions.create(
            model=self.model,
            max_tokens=120,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content

    def _mock(self, prompt: str) -> str:
        """Deterministic stand-in. Biases toward signal words so the mock still
        produces a sensible ranking shape for demos (not random noise)."""
        ev = prompt.lower()
        h = int(hashlib.sha256(prompt.encode()).hexdigest(), 16) % 21  # 0-20 jitter
        base = 40 + h
        boosts = [
            "sole compliance", "chief compliance", "cms licen", "accredited investor",
            "open-architecture", "vcc", "multi-asset", "family office", "discretionary",
            "boutique", "private equity", "hedge fund",
        ]
        penalties = ["retail", "ifa only", "analyst", "associate", "audit", "intern"]
        for b in boosts:
            if b in ev:
                base += 9
        for p in penalties:
            if p in ev:
                base -= 8
        score = max(0, min(100, base))
        return json.dumps({"score": score, "why": "mock deterministic score"})

    # -- parsing -----------------------------------------------------------
    @staticmethod
    def _parse(raw: str) -> RubricResult:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return RubricResult(50, "unparseable", ok=False)
        data = json.loads(m.group())
        score = int(max(0, min(100, round(float(data.get("score", 50))))))
        why = str(data.get("why", ""))[:140]
        return RubricResult(score, why)
