# Jatayu — Architecture & Design (Q1)

## 1. Design goal and the one decision everything follows from

The brief grades two ground-truth metrics above all: **filter precision** (how
many 90%+ fits are in the raw pull) and **ranking quality** (top-10 vs the
team's real shortlist). Those two are 45/80 of Q1.

The single decision that shapes the whole system: **separate *exclusion* from
*discrimination*.**

- The **filter** (Step 1) only excludes on attributes where a wrong value means
  a near-certain non-fit: wrong country, wrong function, a named wrong-pool
  (current regulator, audit intern). It stays *permissive on title*, because the
  brief explicitly warns that "Compliance + Singapore + Asset Management" title
  matching returns hundreds of wrong fits — the signal isn't in the title.
- The **scoring** (Step 3) does the *discrimination* — firm scale, license type,
  sole-ownership, business-model fit. Here we can **reason and rank** rather than
  **exclude and lose**. A false negative in the filter is invisible and
  unrecoverable; a low score is auditable and reversible.

This is why filter precision and ranking quality are not in tension in this
design: the filter maximises recall of *plausible* profiles cheaply, and scoring
converts that into precision at the top.

## 2. Pipeline

```
FILTER → PRE-SCREEN(free) → ENRICH(credits) → SCORE(det+LLM) → RANK → EMIT
```

| Step | Module | Credit-bearing? | Why it's where it is |
|---|---|---|---|
| Filter / search | `filters.py`, client `search_ids` | No (IDs only) | Cheap recall of the plausible universe |
| Pre-screen | `pipeline._pre_screen` | **No (local)** | Reject obvious non-fits *before* paying to enrich |
| Enrich / collect | client `collect` | **Yes** | The only step that spends credits |
| Score | `scoring.py` + `llm.py` | No | Deterministic rules + LLM rubric blend |
| Rank / flag / rationale | `ranking.py` | No | Deterministic, explainable sort |
| Emit | `outputs.py` | No | The five CSV/XLSX deliverables |

Credit discipline is structural, not a guideline: the only credit-spending call
sits *after* a free local gate, so we cannot accidentally spend on a profile we
could have rejected for nothing.

## 3. Why config-driven (and what that bought)

Everything mandate-specific is declarative YAML; the Python is generic. Concretely:

- **`filter:`** compiles to a Coresignal ES query *and* to an in-process
  predicate used on fixtures — one source of truth, so offline dev and live runs
  select identically.
- **`scoring.sub_scores:`** declares each dimension's weight, deterministic
  rules, LLM blend ratio, and rubric text.
- **`ranking:`** declares tie-breakers, flag rules, and confidence thresholds.

Payoffs: (a) a recruiter tunes weights/flags without touching code; (b) the same
binary runs Mandate B (demonstrated, `deliverables/mandate_b/`); (c) configs are
reviewable diffs in PRs — the search *strategy* is versioned, not buried in code.

Trade-off accepted: a config schema is a contract. Genuinely novel mandates can
outgrow it and need new rule *types* in `scoring._eval_rule` (e.g. a graph
signal). I treat that as expected evolution, not failure — see Q1b §6.

## 4. Scoring: deterministic + LLM blend

Each sub-score is computed two ways and blended (`llm_blend`, 0–1 per sub-score):

- **Deterministic** — transparent rules over the profile text/structure
  (`+35 title~'chief compliance officer'`, `−25 company~'DBS'`). Cheap, fast,
  fully auditable, reproducible. Starts at a neutral baseline (35) and rules
  move it.
- **LLM rubric** — a short, JSON-constrained judgment on the nuance the brief
  describes ("sole ownership of the full stack", "boutique AM scale", "AI
  onboarding under own license"). Captures texture rules can't.

Blend ratio is a *mandate* property: Mandate A leans deterministic (0.5 — signal
is observable in license/title/firm language); Mandate B leans LLM (0.55 — fuzzier
pool, archetypes weighted by judgment). The LLM call is **defensive**: JSON-only,
parsed leniently, and any failure degrades to a neutral 50 with a flag rather
than killing a 250-credit run.

**Provider-agnostic LLM:** `anthropic`, `openai`, or a key-free deterministic
`mock`. The committed demo uses `mock` so grading is reproducible with zero
external dependencies; a real provider is one `.env` line.

## 5. Confidence ≠ fit (the sparse-profile stance)

Fit and confidence are orthogonal axes. A profile with a perfect title at a
boutique AM but an empty summary scores **high fit, low confidence** — surfaced,
not hidden, with the thin-data caveat explicit. In the demo run the four
deliberately sparse strong-fit profiles land at fit ≈ 68 with
`confidence=low`, exactly the "great-looking but unverified" bucket a recruiter
must personally check. We never fabricate detail to inflate a sparse profile.

## 6. Credit accounting & allocation

**Cost model (verified against Coresignal docs).** Credits are charged **per
successful request (HTTP 200)**: **1 per `/search/es_dsl` request** (each page),
**1 per `/search/es_dsl/preview`**, and **1 per `/collect/{id}`**
(`CreditLedger.COST_SEARCH / COST_PREVIEW / COST_COLLECT`). So the dominant cost
is collect — searching the universe is one credit per page, collecting a profile
is one credit each. Multisource enrichment is out of scope per the brief.
([ref](https://docs.coresignal.com/employee-api/clean-employee-api))

**Live-mode discipline — preview before you collect.** Because search returns
only IDs (no profile fields), you cannot pre-screen on profile content before
paying to collect. The discipline therefore lives in two places: (1) the ES
filter does the geography/function/industry/exclusion gating **server-side**, so
the ID set is already tight; (2) **`jatayu preview`** (the `/preview` endpoint, 1
credit, collects nothing) lets you validate a filter's match count and tune the
YAML *before* spending collect credits. The one gate that can't run pre-collect
is `min_years_in_function` (needs the experience array), so the local pre-screen
applies it post-collect as a safety net — it should drop few profiles if the
filter is well-tuned. In **offline** mode collect is free, so the pipeline
collects-then-pre-screens to the identical final set.

**Planned allocation (of the 300 trial credits).**

| Phase | Credits | Purpose |
|---|---:|---|
| Dev / filter validation | ~50 | Mostly cheap `preview` calls (1 credit, 0 collects) to tune the filter, plus 2–3 small collect pulls (15–30 profiles) to eyeball raw precision before scaling. Validate that the *raw pull* (not the ranked list) is dense with fits. |
| Production pull | ~220 | One disciplined run: a few search-page credits + ~220 collect credits against the tuned filter (`pull.target_raw_profiles: 220`). |
| Reserve | ~30 | A second corrective pull if dev surfaces a filter gap (e.g. a missed title variant). |

I keep the suggested 50/250 shape but hold ~30 of the production budget as a
**reserve** rather than committing all 250 to the first pull — the highest-value
credit is the one that fixes a filter you only discover is leaky *after* you see
real data. **Planned vs actual** is reconstructable directly from the credit log
(`stage` column splits dev/production; sum `credit_cost`).

If 300 proves insufficient I would (per the brief's options) document the exact
shortfall from the dev pull's measured precision and *ask*, with the number — a
second trial account to brute-force volume is the worse signal here, because on
Mandate A the constraint is filter quality, not volume.

## 7. Mandate Selection Rationale

**Chosen: Mandate A (Sole Compliance Officer, SG Asset Manager).**

**Why A.** The two heaviest metrics reward *observable* signal. Mandate A's fit
texture maps onto attributes that genuinely surface in Coresignal data: title +
seniority (CCO / sole / head of compliance), employer industry and **scale**
(boutique AM vs bulge-bracket bank vs Big-4 advisory vs regulator), and
license/product language (CMS, Accredited Investor, VCC, open-architecture) that
appears in summaries and role descriptions. The brief's own "good vs weak" lists
are almost a feature spec — that is a search I can build defensible inference
logic for, which is exactly what raises filter precision and ranking alignment.

**What concerned me about B.** Mandate B is *harder than it looks* in three ways
that hit my approach specifically: (1) SFO professionals keep **deliberately thin
LinkedIn presence**, so Coresignal coverage is sparse precisely on the best
candidates — a data-availability problem no scoring cleverness fixes; (2) the
ideal profile is **fuzzier** — multiple plausible archetypes (ex-SFO PM,
private-bank PM-with-book, senior buy-side discretionary) that reasonable people
weight differently, so ranking alignment with the team is more subjective and
my weights are a *bet*; (3) "multi-asset discretionary PM track record" is a
**claim** more than a keyword — distinguishing a real cross-asset PM from a
single-asset specialist with broad-sounding language needs evidence the public
profile often omits. A, by contrast, has crisper ground truth.

**What concerned me about A.** It is *easy to over-include* (the title trap), and
the truest signal — sole-officer vs member-of-a-team, AI-onboarding *under own
license* vs retail/IFA distribution — is often only in prose, not structured
fields. My mitigation is the permissive-filter / discriminating-score split plus
LLM rubric on the prose, but I am betting Coresignal summaries are rich enough to
carry that nuance; where they are thin, my confidence axis flags it honestly
rather than guessing.

**What the tool would need to handle *both* well.** (1) A coverage/ enrichment
fallback for thin profiles (the binding constraint on B) — e.g. an
evidence-presence gate that routes low-data-but-high-title candidates to a
human-review queue rather than down-ranking them. (2) Per-archetype scoring
profiles (B has several; A is essentially one), i.e. scoring against the *best-
matching* archetype rather than one averaged rubric. (3) A relationship/deal-flow
signal that simply isn't in employment history. These are named honestly in
[`q1b_config_migration.md`](q1b_config_migration.md) §4 ("what breaks") and §6
("code changes needed anyway").

## 8. What I'd change with more time

1. **Calibrate against ground truth.** The deterministic point values and weights
   are reasoned, not fitted. Given even ~30 labelled profiles from the team's real
   shortlist I'd tune weights to maximise rank correlation (a small logistic /
   pairwise-ranking fit) instead of hand-set points.
2. **Two-pass enrichment to save credits.** Score on the cheap search payload
   first, collect full profiles only for the top slice — cutting production
   credits materially without losing top-10 quality.
3. **Evidence extraction, not keyword matching.** Replace some regex rules with a
   structured LLM extraction ("did this person own compliance solo? Y/N + quote")
   so rationales cite verbatim evidence and sparse-profile handling improves.
4. **De-duplication & company normalisation.** Coresignal company strings vary
   ("UOB" vs "United Overseas Bank"); a normalisation table would sharpen the
   firm-scale signal that drives `firm_type_fit`.
5. **A thin review UI** exposing the scoring intermediate with one-click weight
   overrides and re-rank — closing the recruiter-override loop end to end.

## 9. Known limitations (honest)

- Demo numbers come from synthetic fixtures; absolute fit values are only
  meaningful relative to each other until run live against real data.
- The `mock` LLM is a stand-in that biases toward signal words — good enough to
  show *shape*, not a substitute for a real rubric pass on real prose.
- Credit costs assume 1/profile collect; verify against the live trial meter.
- Nationality / PR status (relevant to both mandates) is not reliably in
  Coresignal; handled as a soft tenure-proxy signal and a flag, never a hard gate.
