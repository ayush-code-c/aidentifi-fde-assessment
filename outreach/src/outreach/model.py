"""Recipient data model + CSV loader. Recipients are data-driven, never hardcoded."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Recipient:
    id: str
    name: str
    title: str = ""
    company: str = ""
    industry: str = ""
    location: str = ""
    seniority: str = ""
    channel: str = "email"
    linkedin_url: str = ""
    bio: str = ""
    recent_activity: str = ""
    hiring_signal: str = "unknown"   # strong | medium | weak | unknown
    source: str = ""

    @property
    def first_name(self) -> str:
        return self.name.split()[0] if self.name else "there"

    @property
    def has_company(self) -> bool:
        return bool(self.company) and "undisclosed" not in self.company.lower()


def load_recipients(path: str | Path) -> list[Recipient]:
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(Recipient(**{k: (v or "").strip() for k, v in r.items()}))
    return rows
