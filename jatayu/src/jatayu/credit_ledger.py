"""Credit ledger — every credit-bearing Coresignal call is recorded here.

The ledger is the single source of truth for the credit-log deliverable and for
per-candidate credit attribution in the final Excel. Discipline is graded, so
nothing touches the network without going through a ledger entry.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class CreditEntry:
    timestamp: str
    endpoint: str
    search_query_or_profile_id: str
    credit_cost: int
    profiles_returned: int
    stage_purpose: str          # e.g. "dev:filter-validation", "prod:enrich"
    useful_yes_no: str          # self-rated: "yes" / "no" / "partial"
    notes: str
    stage: str = "production"   # "dev" or "production" — splits the two sheets
    profile_id: str = ""        # for per-candidate attribution


class CreditLedger:
    """Accumulates credit entries and writes the credit-log CSV deliverable."""

    # Coresignal v2 clean Employee API credit costs. Per the docs, credits are
    # charged PER SUCCESSFUL REQUEST (HTTP 200): one credit per search request and
    # one per collect request. See docs/architecture.md "Credit Accounting".
    # Ref: https://docs.coresignal.com/employee-api/clean-employee-api
    COST_SEARCH = 1      # 1 credit per /search/es_dsl request (each page)
    COST_PREVIEW = 1     # 1 credit per /search/es_dsl/preview request (dev validation)
    COST_COLLECT = 1     # 1 credit per /collect/{id} request

    def __init__(self) -> None:
        self.entries: list[CreditEntry] = []

    def record(self, **kwargs) -> CreditEntry:
        kwargs.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        entry = CreditEntry(**kwargs)
        self.entries.append(entry)
        return entry

    @property
    def total_spent(self) -> int:
        return sum(e.credit_cost for e in self.entries)

    def spent_by_stage(self, stage: str) -> int:
        return sum(e.credit_cost for e in self.entries if e.stage == stage)

    def spent_on_profile(self, profile_id: str) -> int:
        return sum(
            e.credit_cost for e in self.entries if e.profile_id == profile_id
        )

    def write_csv(self, out_dir: str | Path) -> dict[str, Path]:
        """Write two-sheet credit log as two CSV files (dev + production)."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        cols = [
            "timestamp", "endpoint", "search_query_or_profile_id", "credit_cost",
            "profiles_returned", "stage_purpose", "useful_yes_no", "notes",
        ]
        written: dict[str, Path] = {}
        for stage in ("dev", "production"):
            path = out_dir / f"credit_log_{stage}.csv"
            rows = [e for e in self.entries if e.stage == stage]
            with path.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=cols)
                w.writeheader()
                for e in rows:
                    d = asdict(e)
                    w.writerow({k: d[k] for k in cols})
            written[stage] = path
        return written
