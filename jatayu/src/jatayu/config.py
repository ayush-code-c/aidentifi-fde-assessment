"""Configuration & runtime settings loading.

Two layers:
  1. Mandate config (YAML)   - *what* we are looking for. Versioned, reviewable.
  2. Runtime settings (.env) - *how* we run: credentials, mode, LLM provider.

Nothing secret ever lives in the mandate YAML, so configs are safe to commit.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Optional .env support - works without it (env vars still read).
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - optional dependency
    pass


def load_mandate(path: str | Path) -> dict[str, Any]:
    """Load and lightly validate a mandate YAML config."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    _validate(cfg, path)
    return cfg


def _validate(cfg: dict[str, Any], path: Path) -> None:
    required_top = {"mandate", "filter", "scoring", "ranking", "output"}
    missing = required_top - set(cfg)
    if missing:
        raise ValueError(f"{path}: missing top-level sections: {sorted(missing)}")
    weights = [s["weight"] for s in cfg["scoring"]["sub_scores"].values()]
    total = round(sum(weights), 4)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"{path}: sub-score weights must sum to 1.0, got {total}. "
            "Recruiter overrides must re-normalise."
        )


@dataclass
class Settings:
    """Runtime settings resolved from environment variables."""

    # offline = use fixtures (no credits, no network). live = real Coresignal.
    mode: str = field(default_factory=lambda: os.getenv("JATAYU_MODE", "offline"))

    coresignal_api_key: str | None = field(
        default_factory=lambda: os.getenv("CORESIGNAL_API_KEY")
    )
    coresignal_base_url: str = field(
        default_factory=lambda: os.getenv(
            "CORESIGNAL_BASE_URL", "https://api.coresignal.com/cdapi/v2"
        )
    )

    # LLM provider for the rubric pass. "mock" needs no key and is deterministic.
    llm_provider: str = field(
        default_factory=lambda: os.getenv("JATAYU_LLM_PROVIDER", "mock")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("JATAYU_LLM_MODEL", "claude-sonnet-4-6")
    )
    anthropic_api_key: str | None = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )
    openai_api_key: str | None = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )

    fixtures_path: str = field(
        default_factory=lambda: os.getenv(
            "JATAYU_FIXTURES", "fixtures/mandate_a_raw_profiles.json"
        )
    )

    def require_live(self) -> None:
        if self.mode == "live" and not self.coresignal_api_key:
            raise RuntimeError(
                "JATAYU_MODE=live but CORESIGNAL_API_KEY is unset. "
                "Set it in .env or run offline mode."
            )

    def autoselect_fixtures(self, cfg: dict[str, Any]) -> None:
        """In offline mode, point fixtures_path at THIS mandate's fixtures
        (e.g. mandate_b_invdir_sfo -> fixtures/mandate_b_raw_profiles.json)
        unless the caller explicitly pinned JATAYU_FIXTURES. Without this,
        every mandate would silently fall back to Mandate A's fixtures.
        """
        if self.mode != "offline" or "JATAYU_FIXTURES" in os.environ:
            return
        mandate_id = str(cfg.get("mandate", {}).get("id", ""))
        parts = mandate_id.split("_")
        if len(parts) >= 2:
            candidate = f"fixtures/{parts[0]}_{parts[1]}_raw_profiles.json"
            if Path(candidate).exists():
                self.fixtures_path = candidate
