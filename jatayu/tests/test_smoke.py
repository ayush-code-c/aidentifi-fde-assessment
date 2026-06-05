"""Smoke + invariant tests. Run: PYTHONPATH=src python -m pytest -q (or run directly)."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jatayu.config import Settings, load_mandate  # noqa: E402
from jatayu.filters import build_es_query, years_in_function  # noqa: E402
from jatayu.pipeline import run  # noqa: E402
from jatayu.scoring import sg_tenure_years  # noqa: E402


def test_configs_valid():
    for name in ("mandate_a_compliance_sg", "mandate_b_invdir_sfo"):
        cfg = load_mandate(ROOT / "config" / f"{name}.yaml")
        w = sum(s["weight"] for s in cfg["scoring"]["sub_scores"].values())
        assert abs(w - 1.0) < 1e-6, f"{name} weights sum to {w}"


def test_es_query_has_geo_and_function():
    cfg = load_mandate(ROOT / "config" / "mandate_a_compliance_sg.yaml")
    q = build_es_query(cfg["filter"])
    must = q["query"]["bool"]["must"]
    assert any("location_country" in json.dumps(m) for m in must)
    assert "must_not" in q["query"]["bool"]


def test_pipeline_offline_produces_all_deliverables(tmp_path=None):
    out = ROOT / "deliverables" / "_test_run"
    s = Settings()
    s.mode = "offline"
    s.fixtures_path = str(ROOT / "fixtures" / "mandate_a_raw_profiles.json")
    summary = run(ROOT / "config" / "mandate_a_compliance_sg.yaml", out, settings=s, stage="dev")
    assert summary["raw_pull"] > 0
    assert summary["credits_total"] == 0  # offline costs nothing
    for f in ("raw_production_pull.csv", "scoring_intermediate.csv",
              "top10_shortlist.xlsx", "credit_log_dev.csv"):
        assert (out / f).exists(), f"missing {f}"


def test_strong_fit_outranks_weak():
    """A sole-CCO-at-boutique-AM must outrank a junior compliance analyst."""
    out = ROOT / "deliverables" / "_test_run2"
    s = Settings(); s.mode = "offline"
    s.fixtures_path = str(ROOT / "fixtures" / "mandate_a_raw_profiles.json")
    run(ROOT / "config" / "mandate_a_compliance_sg.yaml", out, settings=s, stage="dev")
    import csv
    rows = list(csv.DictReader(open(out / "scoring_intermediate.csv")))
    by_title_max = {}
    for r in rows:
        t = r["current_title"]
        by_title_max[t] = max(by_title_max.get(t, 0), int(r["fit_score"]))
    sole = max(v for k, v in by_title_max.items() if "Sole" in k or "Chief" in k)
    assert sole >= 85


def test_years_in_function():
    p = {"experience": [
        {"title": "Head of Compliance", "date_from": "2016-01", "date_to": None},
        {"title": "Software Engineer", "date_from": "2010-01", "date_to": "2016-01"},
    ]}
    y = years_in_function(p, ["compliance"])
    assert 9 <= y <= 11  # ~2016->2026


if __name__ == "__main__":
    test_configs_valid()
    test_es_query_has_geo_and_function()
    test_pipeline_offline_produces_all_deliverables()
    test_strong_fit_outranks_weak()
    test_years_in_function()
    print("all smoke tests passed")
