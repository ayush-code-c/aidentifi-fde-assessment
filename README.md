# Aidentifi: Forward Deployed Engineer Assessment

Submission repo. Two tools, two strategic documents, one config-migration doc,
and one diagnostic essay. Everything runs end-to-end **with no external accounts**
(offline/mock modes); switching to live data is a `.env` change, documented per
tool.

**Executed Q1 mandate:** Mandate A: Sole Compliance Officer, Singapore Asset
Manager. (Rationale + Mandate B migration included.)

---

## Deliverable map (→ rubric)

| Q | Weight | Deliverable | Where |
|---|---:|---|---|
| **Q1** | 40% | Jatayu sourcing & ranking tool (config-driven, README) | [`jatayu/`](jatayu/) |
| | | ↳ Architecture doc (+ Mandate Selection Rationale) | [`jatayu/docs/architecture.md`](jatayu/docs/architecture.md) |
| | | ↳ Top-10 shortlist (Excel, exact columns) | [`jatayu/deliverables/mandate_a/top10_shortlist.xlsx`](jatayu/deliverables/mandate_a/) |
| | | ↳ Raw production pull (CSV — the filter-precision audit file) | `jatayu/deliverables/mandate_a/raw_production_pull.csv` |
| | | ↳ Scoring intermediate (CSV) | `jatayu/deliverables/mandate_a/scoring_intermediate.csv` |
| | | ↳ Credit log (CSV, dev + production sheets) | `jatayu/deliverables/mandate_a/credit_log_*.csv` |
| **Q1b** | 15% | Configuration Migration Document (→ Mandate B) | [`jatayu/docs/q1b_config_migration.md`](jatayu/docs/q1b_config_migration.md) |
| **Q2** | 20% | Outreach generator (tool + 5 outputs, 2 sparse) | [`outreach/`](outreach/) · [`outreach/outputs/`](outreach/outputs/) |
| | | ↳ Architecture doc (+ scalability story) | [`outreach/docs/architecture.md`](outreach/docs/architecture.md) |
| **Q3** | 10% | Improvement roadmap (2 pages, $ + weeks) | [`docs/Q3_improvement_roadmap.md`](docs/Q3_improvement_roadmap.md) |
| **Q4** | 15% | Company Brain (2 pages) | [`docs/Q4_company_brain.md`](docs/Q4_company_brain.md) |
| — | — | Loom recording scripts (shot-by-shot) | [`LOOM_SCRIPTS.md`](LOOM_SCRIPTS.md) |
| — | — | Submission checklist | [`SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md) |

## Run both tools in two minutes (no keys)

```bash
# Q1 — Jatayu
cd jatayu && pip install -r requirements.txt && export PYTHONPATH=src
python -m jatayu run --mandate config/mandate_a_compliance_sg.yaml --out deliverables/mandate_a

# Q2 — Outreach
cd ../outreach && pip install -r requirements.txt && export PYTHONPATH=src
python -m outreach run --recipients data/recipients.csv \
  --positioning config/aidentifi_positioning.yaml --out outputs
```

Tests: `PYTHONPATH=src python tests/test_smoke.py` in each tool directory.

---

## ⚠️ Read this: what's complete vs what needs you (human-in-the-loop)

I built everything that can be built without your private accounts, and wired up
(but could not execute) the three things that genuinely require you. Being
explicit so nothing is mistaken for done:

**Fully complete and runnable now**
- Both tools, all code, all configs, all four documents.
- Every Q1 supporting deliverable is *generated* by the tool (committed copies in
  `jatayu/deliverables/mandate_a/`), produced **offline from synthetic, Coresignal-
  shaped fixtures** so the repo runs anywhere at **0 credits**.
- The deterministic-mock LLM makes every run reproducible with no API key.

**Needs you — and exactly how to do it**
1. **The live Coresignal production pull.** The committed Q1 deliverables use
   synthetic data, so `credits_spent_on_this_candidate` is 0 in the committed
   copy. To produce the *real* filter-precision pull the brief audits: get your
   300-credit trial, put `CORESIGNAL_API_KEY` + `JATAYU_MODE=live` in
   `jatayu/.env`, and re-run the same command. The credit log populates itself.
   The credit *strategy* (50 dev / ~220 prod / ~30 reserve, pre-screen-before-
   spend) is real and lives in `jatayu/docs/architecture.md`.
2. **The two Loom videos.** I can't record video. [`LOOM_SCRIPTS.md`](LOOM_SCRIPTS.md)
   has a shot-by-shot script for each (one Jatayu candidate from raw → rank with
   the credit meter on screen; one outreach recipient end-to-end).
3. **Real outreach recipients.** `outreach/data/recipients.csv` ships realistic
   synthetic stand-ins (2 deliberately sparse). Swap in 5 real people sourced
   legally from your own access; no code changes — it's pure data.

**Why this split is honest, not a shortcut:** the brief says "we evaluate the
systems you build more heavily than the outputs they produce." The system is
complete and demonstrably correct on fixtures; the outputs that need live credits
or your LinkedIn access are one config flag / one CSV away, and the path is
documented and tested.

## A note on the IP bounty

Per the brief, I retain IP by default; Aidentifi holds the 12-month option on the
Q1 (Jatayu) logic described in `jatayu/docs/architecture.md`.
