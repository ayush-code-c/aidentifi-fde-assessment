"""Coresignal client — two interchangeable backends.

* LiveClient    — real Coresignal clean-profile API (search + collect/bulk).
* FixtureClient — loads local JSON fixtures; zero credits, zero network.

Both implement the same interface so the pipeline is identical in dev/offline
testing and in production. Every credit-bearing operation is logged through the
shared CreditLedger so the credit-log deliverable is a byproduct of running,
not a thing we reconstruct afterwards.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .credit_ledger import CreditLedger
from .filters import build_es_query, local_predicate


class CoresignalError(RuntimeError):
    pass


class BaseClient:
    def __init__(self, ledger: CreditLedger, stage: str = "production"):
        self.ledger = ledger
        self.stage = stage

    def search_ids(self, filter_cfg: dict, *, purpose: str) -> list[str]:
        raise NotImplementedError

    def collect(self, ids: list[str], *, purpose: str) -> list[dict]:
        raise NotImplementedError


class LiveClient(BaseClient):
    """Talks to the real Coresignal v2 clean Employee API."""

    def __init__(self, api_key: str, base_url: str, ledger: CreditLedger, stage="production"):
        super().__init__(ledger, stage)
        import requests  # local import so offline runs need no requests

        self._requests = requests
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )

    def search_ids(self, filter_cfg: dict, *, purpose: str) -> list[str]:
        query = build_es_query(filter_cfg)
        target = filter_cfg.get("pull", {}).get("target_raw_profiles", 200)
        url = f"{self.base_url}/employee_clean/search/es_dsl"
        resp = self.session.post(url, data=json.dumps(query), timeout=60)
        if resp.status_code != 200:
            raise CoresignalError(f"search failed {resp.status_code}: {resp.text[:300]}")
        ids = resp.json()
        ids = [str(i) for i in ids][:target]
        # Search itself is not charged on the clean API (charged on collect).
        self.ledger.record(
            endpoint="employee_clean/search/es_dsl",
            search_query_or_profile_id=json.dumps(query["query"])[:200],
            credit_cost=CreditLedger.COST_SEARCH,
            profiles_returned=len(ids),
            stage_purpose=purpose,
            useful_yes_no="yes",
            notes=f"ES DSL search; capped at target {target}",
            stage=self.stage,
        )
        return ids

    def collect(self, ids: list[str], *, purpose: str) -> list[dict]:
        out: list[dict] = []
        for cid in ids:
            url = f"{self.base_url}/employee_clean/collect/{cid}"
            resp = self.session.get(url, timeout=60)
            if resp.status_code == 404:
                self.ledger.record(
                    endpoint="employee_clean/collect",
                    search_query_or_profile_id=cid, credit_cost=0,
                    profiles_returned=0, stage_purpose=purpose,
                    useful_yes_no="no", notes="404 not found", stage=self.stage,
                    profile_id=cid,
                )
                continue
            if resp.status_code != 200:
                raise CoresignalError(f"collect {cid} failed {resp.status_code}")
            profile = resp.json()
            out.append(profile)
            self.ledger.record(
                endpoint="employee_clean/collect",
                search_query_or_profile_id=cid,
                credit_cost=CreditLedger.COST_COLLECT,
                profiles_returned=1, stage_purpose=purpose,
                useful_yes_no="yes", notes="profile collected", stage=self.stage,
                profile_id=str(cid),
            )
        return out


class FixtureClient(BaseClient):
    """Offline backend backed by a JSON list of profiles. No credits, no net."""

    def __init__(self, fixtures_path: str | Path, ledger: CreditLedger, stage="dev"):
        super().__init__(ledger, stage)
        self.fixtures_path = Path(fixtures_path)
        with self.fixtures_path.open("r", encoding="utf-8") as fh:
            self._profiles: list[dict] = json.load(fh)
        self._by_id = {str(p["id"]): p for p in self._profiles}

    def search_ids(self, filter_cfg: dict, *, purpose: str) -> list[str]:
        pred = local_predicate(filter_cfg)
        ids = [str(p["id"]) for p in self._profiles if pred(p)]
        target = filter_cfg.get("pull", {}).get("target_raw_profiles", 200)
        ids = ids[:target]
        self.ledger.record(
            endpoint="fixture/search",
            search_query_or_profile_id="local_predicate(mandate.filter)",
            credit_cost=0, profiles_returned=len(ids), stage_purpose=purpose,
            useful_yes_no="yes", notes="offline fixture search (0 credits)",
            stage=self.stage,
        )
        return ids

    def collect(self, ids: list[str], *, purpose: str) -> list[dict]:
        out = []
        for cid in ids:
            p = self._by_id.get(str(cid))
            if p is None:
                continue
            out.append(p)
            # Offline = 0 credits, but we still log so dev discipline is visible.
            self.ledger.record(
                endpoint="fixture/collect",
                search_query_or_profile_id=str(cid), credit_cost=0,
                profiles_returned=1, stage_purpose=purpose,
                useful_yes_no="yes", notes="offline fixture collect (0 credits)",
                stage=self.stage, profile_id=str(cid),
            )
        return out


def make_client(settings, ledger: CreditLedger, stage: str = "production") -> BaseClient:
    """Factory: returns LiveClient or FixtureClient per settings.mode."""
    if settings.mode == "live":
        settings.require_live()
        return LiveClient(
            settings.coresignal_api_key, settings.coresignal_base_url, ledger, stage
        )
    return FixtureClient(settings.fixtures_path, ledger, stage)
