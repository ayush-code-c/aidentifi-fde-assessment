# Jatayu - Sourcing & Ranking Tool (Q1)

Given a mandate brief, Jatayu returns a tightly-fit, ranked shortlist of
candidates with minimal human effort. The engine is **mandate-agnostic**: every
mandate-specific decision lives in a YAML config, so switching from a Singapore
compliance search to a family-office investment search is a config change, not a
code change (proven - see [`docs/q1b_config_migration.md`](docs/q1b_config_migration.md)).

**Executed mandate:** Mandate A - Sole Compliance Officer, Singapore Asset Manager.
**Migration-only mandate:** Mandate B - Investment Director, SG Single Family Office.

---

## TL;DR - run it in 30 seconds (no keys, no credits)

```bash
cd jatayu
pip install -r requirements.txt          # PyYAML + openpyxl is enough for offline
export PYTHONPATH=src

# regenerate the synthetic fixtures (optional; already committed)
python fixtures/_generate_fixtures.py

# run the full pipeline offline -> writes every deliverable
python -m jatayu run \
  --mandate config/mandate_a_compliance_sg.yaml \
  --out deliverables/mandate_a
```

Outputs land in `deliverables/mandate_a/`:

| File | Brief deliverable |
|---|---|
| `raw_production_pull.csv` | **Raw production pull** (audited for filter precision) |
| `scoring_intermediate.csv` | **Scoring intermediate** (raw pull + every computed score) |
| `top10_shortlist.xlsx` | **Top-10 shortlist** (exact required columns) |
| `credit_log_dev.csv` / `credit_log_production.csv` | **Credit log** (two sheets) |

Inspect the compiled Coresignal query without running anything:

```bash
python -m jatayu show-query --mandate config/mandate_a_compliance_sg.yaml
```

---

## Two run modes

| | `offline` (default) | `live` |
|---|---|---|
| Data | local JSON fixtures | real Coresignal clean API |
| Credits | **0** | real (logged per call) |
| Keys | none | `CORESIGNAL_API_KEY` |
| Purpose | dev, CI, demo, reproducible grading | the real production pull |

The pipeline code is identical in both modes - only the client backend swaps
(`FixtureClient` ↔ `LiveClient`). The fixtures mirror the Coresignal clean
Employee schema (field names + nesting), so nothing downstream changes.

### Going live (your Coresignal trial)

```bash
cp .env.example .env          # then fill in CORESIGNAL_API_KEY
# set JATAYU_MODE=live and (optionally) a real LLM provider in .env

# 1) DEV: validate the filter cheaply (1 credit, collects nothing) and iterate
#    the YAML until the match count looks tight before spending collect credits.
python -m jatayu preview --mandate config/mandate_a_compliance_sg.yaml

# 2) PRODUCTION: run the real pull (a few search credits + ~220 collect credits)
python -m jatayu run --mandate config/mandate_a_compliance_sg.yaml \
                     --out deliverables/mandate_a --stage production
```

Verified against Coresignal v2 docs: auth is an **`apikey`** header (the client
sets this for you), credits are **1 per search request and 1 per collect**, and
the `/search/es_dsl/preview` endpoint backs `jatayu preview` for cheap dev
validation. See the credit-accounting section of the architecture doc.

> **Note for the reviewer:** the committed `deliverables/` were produced in
> **offline** mode (synthetic data, 0 credits) so the repo runs anywhere with no
> account. The `credits_spent_on_this_candidate` column is therefore 0 in the
> committed copy; it is populated automatically from the credit ledger on a live
> run. The credit-allocation *strategy* (dev/prod split, pre-screen-before-spend)
> is real and is described in the architecture doc.

---

## How it works (4 steps)

```
config (YAML)                       ┌─────────────────────────────────────────┐
   │   filter / scoring / ranking   │  src/jatayu/                              │
   ▼                                │                                           │
1. FILTER   filters.py  ──ES DSL──▶ │  coresignal_client.py  (live | fixture)   │
2. PRE-SCREEN (free, local) ──────▶ │  pipeline.py orchestrates, ledger logs    │
3. ENRICH   collect (credits) ────▶ │  every credit-bearing call                │
4. SCORE    scoring.py  (det+LLM) ─▶ │  ranking.py -> outputs.py                  │
            rank + flag + rationale └─────────────────────────────────────────┘
```

1. **Filter** - `filters.py` compiles the YAML `filter:` block into a Coresignal
   Elasticsearch query. Hard on geography + function, permissive on title (the
   brief warns title-matching over-includes); the firm-scale / business-model
   discrimination is pushed into scoring where we can *reason* instead of
   *exclude*.
2. **Pre-screen** - a **free, local** gate drops obvious non-fits *before* we
   pay to enrich them. No production credit is ever spent on a profile we could
   reject for free.
3. **Enrich** - collect full clean profiles (the credit-bearing step). Every
   call is recorded in the `CreditLedger`.
4. **Score → Rank** - each sub-score blends transparent **deterministic rules**
   (declared in YAML) with an **LLM rubric** pass for nuance. `fit_score = Σ
   weightᵢ × blended_sub_scoreᵢ`. Ranking is a deterministic, explainable sort
   with config tie-breakers, per-candidate flags, and a templated rationale.

Full design rationale, the credit strategy, and the **Mandate Selection
Rationale** are in [`docs/architecture.md`](docs/architecture.md).

---

## The recruiter override path (scoring transparency)

Everything a recruiter would want to change is in the config, not the code:

- **Sub-score weights** - `scoring.sub_scores.<name>.weight` (must sum to 1.0;
  the loader enforces it).
- **LLM-vs-deterministic blend** - `llm_blend_default` or per sub-score.
- **What counts as signal** - the `deterministic.positive/negative` rule lists.
- **Flags & confidence thresholds** - `ranking.flag_rules`, `ranking.confidence`.

And every number is auditable: `scoring_intermediate.csv` emits the
deterministic score, the LLM score, the blended value, **and the exact rule hits**
(e.g. `+35 title~'chief compliance officer'`) for every sub-score of every
candidate. No black boxes.

---

## Repo layout

```
jatayu/
├── config/
│   ├── mandate_a_compliance_sg.yaml   # executed mandate (the inference logic)
│   └── mandate_b_invdir_sfo.yaml      # proves config-driven generality
├── src/jatayu/
│   ├── config.py            # YAML + .env loading, weight validation
│   ├── filters.py           # YAML -> Coresignal ES query (+ offline predicate)
│   ├── coresignal_client.py # LiveClient | FixtureClient, both credit-logged
│   ├── credit_ledger.py     # single source of truth for credit spend
│   ├── llm.py               # anthropic | openai | deterministic mock
│   ├── scoring.py           # deterministic rules + LLM blend
│   ├── ranking.py           # sort, tie-breakers, flags, rationale
│   ├── outputs.py           # raw pull / scoring intermediate / top-10 xlsx
│   └── pipeline.py          # orchestration + credit discipline
├── fixtures/                # synthetic profiles (Coresignal-shaped)
├── tests/test_smoke.py      # invariants incl. "strong fit outranks weak"
├── deliverables/            # generated outputs (committed demo copy)
└── docs/
    ├── architecture.md      # design, trade-offs, credit strategy, mandate rationale
    └── q1b_config_migration.md
```

## Testing

```bash
PYTHONPATH=src python tests/test_smoke.py     # or: python -m pytest -q tests
```

The suite asserts config validity, that the ES query carries the geo + function
gates, that all deliverables are produced offline at 0 credits, and the key
ranking invariant - **a sole-CCO-at-a-boutique outranks a junior analyst.**
