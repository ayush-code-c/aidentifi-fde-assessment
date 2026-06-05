"""Config + runtime settings for the outreach generator."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover
    pass


def load_positioning(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass
class Settings:
    provider: str = field(default_factory=lambda: os.getenv("OUTREACH_LLM_PROVIDER", "mock"))
    model: str = field(default_factory=lambda: os.getenv("OUTREACH_LLM_MODEL", "claude-sonnet-4-6"))
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
