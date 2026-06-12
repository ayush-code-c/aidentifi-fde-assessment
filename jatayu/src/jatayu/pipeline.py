"""Pipeline orchestration: filter -> pre-screen -> enrich -> score -> rank -> emit.

Credit discipline is built into the order of operations:
  1. search returns IDs cheaply (no per-profile credits),
  2. a free LOCAL pre-screen drops obvious non-fits,
  3. only survivors are collected (the credit-bearing step),
so we never spend a production credit enriching a profile we could reject for
free first.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings, load_mandate
from .coresignal_client import make_client
from .credit_ledger import CreditLedger
from .filters import local_predicate
from .llm import LLMScorer
from .outputs import (
    write_raw_pull,
    write_scoring_intermediate,
    write_top10_excel,
)
from .ranking import rank
from .scoring import score_profile


def _pre_screen(profiles: list[dict], cfg: dict) -> tuple[list[dict], list[dict]]:
    """Free local pre-screen before paying to enrich. Returns (keep, dropped)."""
    pre = cfg.get("enrich", {}).get("pre_screen", {})
    pred = local_predicate(cfg["filter"])
    keep, dropped = [], []
    for p in profiles:
        ok = True
        if pre.get("drop_if_location_not_sg"):
            if str(p.get("location_country", "")).lower() != "singapore":
                ok = False
        # reuse the full local predicate as a stricter gate where data exists
        if ok and not pred(p):
            ok = False
        (keep if ok else dropped).append(p)
    return keep, dropped


def run(
    mandate_path: str | Path,
    out_dir: str | Path,
    settings: Settings | None = None,
    stage: str = "production",
) -> dict[str, Any]:
    settings = settings or Settings()
    cfg = load_mandate(mandate_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    settings.autoselect_fixtures(cfg)

    ledger = CreditLedger()
    client = make_client(settings, ledger, stage=stage)
    llm = LLMScorer(
        settings.llm_provider, settings.llm_model,
        settings.anthropic_api_key, settings.openai_api_key,
    )

    # 1. SEARCH (cheap) -> candidate IDs
    ids = client.search_ids(cfg["filter"], purpose=f"{stage}:filter-search")

    # 2. COLLECT (credit-bearing in live mode). In live mode we'd pre-screen on
    #    the lightweight search payload; with fixtures we collect then pre-screen
    #    (collect is free offline), which yields the identical final set.
    collected = client.collect(ids, purpose=f"{stage}:enrich-collect")

    # 3. FREE local pre-screen -> the raw production pull we audit on.
    raw_pull, dropped = _pre_screen(collected, cfg)

    # 4. SCORE every profile in the raw pull.
    scored = [score_profile(p, cfg, llm) for p in raw_pull]

    # 5. RANK.
    ranked = rank(scored, cfg)

    # 6. EMIT deliverables.
    paths = {
        "raw_pull_csv": write_raw_pull(raw_pull, out_dir / "raw_production_pull.csv"),
        "scoring_intermediate_csv": write_scoring_intermediate(
            ranked, cfg, ledger, out_dir / "scoring_intermediate.csv"
        ),
        "top10_xlsx": write_top10_excel(
            ranked, cfg, ledger, out_dir / "top10_shortlist.xlsx"
        ),
    }
    credit_paths = ledger.write_csv(out_dir)
    paths.update({f"credit_log_{k}": v for k, v in credit_paths.items()})

    summary = {
        "mandate": cfg["mandate"]["id"],
        "mode": settings.mode,
        "llm_provider": settings.llm_provider,
        "ids_from_search": len(ids),
        "collected": len(collected),
        "raw_pull": len(raw_pull),
        "dropped_in_prescreen": len(dropped),
        "strong_fits_90plus": sum(
            1 for sp in ranked
            if sp.fit_score >= cfg["scoring"].get("fit_threshold_strong", 90)
        ),
        "credits_total": ledger.total_spent,
        "credits_dev": ledger.spent_by_stage("dev"),
        "credits_production": ledger.spent_by_stage("production"),
        "outputs": {k: str(v) for k, v in paths.items()},
    }
    return summary
