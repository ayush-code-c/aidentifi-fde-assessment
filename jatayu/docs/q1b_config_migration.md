# Q1b - Configuration Migration Document

**From:** Mandate A (executed) - Sole Compliance Officer, SG Asset Manager
**To:** Mandate B (migration) - Investment Director, SG Single Family Office

The claim Jatayu makes is that switching mandates is a **config change, not a
code change**. This document shows exactly how, and - more importantly - where
that claim *strains*. Mandate B has already been run through the unmodified
engine; its outputs are in `deliverables/mandate_b/`. The full target config is
[`config/mandate_b_invdir_sfo.yaml`](../config/mandate_b_invdir_sfo.yaml).

---

## 1. Diff against the existing config

Real values, unified-diff style (A → B). Unchanged lines elided with `…`.

```diff
  mandate:
-   id: mandate_a_compliance_sg
-   name: "Sole Compliance Officer - Singapore Asset Manager"
+   id: mandate_b_invdir_sfo
+   name: "Investment Director - Singapore Single Family Office"

  filter:
    location: { countries: ["Singapore"] }      # unchanged
    active_experience: true                       # unchanged
    title_any:
-     - "compliance" / "chief compliance" / "head of compliance"
-     - "compliance officer" / "MLRO" / "risk and compliance"
+     - "investment director" / "portfolio manager" / "chief investment officer"
+     - "head of investments" / "investment manager" / "managing director"
+     - "investment principal" / "head of portfolio"
    industry_any:
-     - "Investment Management" / "Asset Management" / "Financial Services"
-     - "Venture Capital & Private Equity" / "Capital Markets"
+     - "Investment Management" / "Capital Markets" / "Financial Services"
+     - "Venture Capital & Private Equity"
+     - "Banking"                  # ADDED: private banks are a valid feeder pool
    must_not_title:
-     - "audit associate" / "audit senior" / "intern" / "student"
+     - "analyst" / "associate" / "intern" / "relationship manager"
-   must_not_current_company: ["Monetary Authority of Singapore"]   # REMOVED
    experience:
-     min_years_in_function: 7
-     function_keywords: ["compliance", "regulatory", "MLRO", "risk and compliance"]
+     min_years_in_function: 13
+     function_keywords: ["portfolio", "investment", "asset allocation", "buy-side", "fund"]
    pull:
-     target_raw_profiles: 220
+     target_raw_profiles: 200

  scoring:
-   llm_blend_default: 0.5
+   llm_blend_default: 0.55          # fuzzier pool -> lean on judgment
    sub_scores:
-     compliance_ownership (0.30) / firm_type_fit (0.25) / mas_regulatory_fit (0.25)
-     business_model_fit (0.12) / singapore_commitment (0.08)
+     multi_asset_pm (0.35) / sfo_mfo_fit (0.25) / private_markets_access (0.18)
+     sg_roots (0.14) / seniority_calibration (0.08)

  ranking:
    top_n: 10                                      # unchanged
-   tie_breakers: [compliance_ownership, mas_regulatory_fit, years_relevant_experience]
+   tie_breakers: [multi_asset_pm, sfo_mfo_fit, years_relevant_experience]
```

Everything above is data. No `.py` file changes to produce the Mandate B run.

---

## 2. Search-filter changes (per change, with reasoning)

| Filter | Change | Reasoning |
|---|---|---|
| `location.countries` | **Keep** `["Singapore"]` | Both mandates are SG-based. Reusable verbatim. |
| `title_any` | **Replace** | Different function entirely. Note B's titles are *vaguer* (`managing director`, `head of investments`) - SFO PMs hide behind generic titles, so the gate is necessarily looser and leans harder on scoring to disambiguate. |
| `industry_any` | **Add `Banking`** | A *excludes* pure banking (weak pool); B *includes* private banking as a legitimate feeder (HNW/FO-facing PB with a PM book). Same field, opposite intent - a clean example of why exclusion belongs in scoring, not the filter. |
| `must_not_title` | **Replace** | A strips audit juniors; B strips `analyst`/`associate` (step-up risk) and `relationship manager` (sales, no PM book). |
| `must_not_current_company` (MAS) | **Remove** | Irrelevant to B. The ex-regulator concern is A-specific. |
| `experience.min_years_in_function` | **7 → 13** | A is 8–15 yrs; B is 15+. Floored below nominal in both cases to absorb Coresignal date-rounding. |
| `experience.function_keywords` | **Replace** | Drives the years-in-function calc; must match investment roles, not compliance roles. |

**A filter that is *not* reusable:** `must_not_current_company:
[Monetary Authority of Singapore]`. It encodes an A-specific failure mode
(regulator-with-no-industry-side). Nothing in B replaces it 1:1; the nearest B
analogue - excluding pure sell-side - is better expressed as a *scoring penalty*
(`sfo_mfo_fit` negative rule) than a hard exclude, because a sell-side PM who
later ran a discretionary book is a real candidate.

---

## 3. Scoring-weight changes (numerical)

| Mandate A sub-score | wt | → | Mandate B sub-score | wt | Disposition |
|---|---:|---|---|---:|---|
| compliance_ownership | 0.30 | → | multi_asset_pm | 0.35 | **Replaced** - the dominant axis flips from "owns compliance solo" to "has run multi-asset money". |
| firm_type_fit | 0.25 | → | sfo_mfo_fit | 0.25 | **Reframed** - both ask "right *kind* of seat"; firm-scale heuristic → SFO/discretionary-mandate heuristic. |
| mas_regulatory_fit | 0.25 | → | - | - | **Dropped** - licensing fluency is near-irrelevant for a PM seat. |
| business_model_fit | 0.12 | → | private_markets_access | 0.18 | **Reframed + up-weighted** - product familiarity → relationships/deal-flow, which matters more for an SFO PM. |
| singapore_commitment | 0.08 | → | sg_roots | 0.14 | **Kept, up-weighted** - "commitment to stay" is louder in B (Citizen/PR strongly preferred). |
| - | - | → | seniority_calibration | 0.08 | **New** - B uniquely risks *over*-scoped candidates (would not report to a principal); A had no such ceiling. |

Weights re-normalise to 1.0 (loader enforces). Net: one dropped axis
(regulatory), one new axis (seniority ceiling), three reframed, one kept.

---

## 4. What breaks - where my architecture genuinely struggles on B

Four honest failure modes (not "it generalises perfectly"):

1. **Data coverage is the binding constraint, and I can't config my way out.**
   SFO professionals keep deliberately thin LinkedIn/Coresignal footprints. My
   filter + scoring assume the signal is *present in the profile*. For B's best
   candidates it often isn't there at all. A leaky filter still finds people;
   missing data finds *nobody*. No weight change fixes an empty profile - this is
   the real reason I did not choose B.

2. **"Multi-asset discretionary PM" is a claim, not a keyword.** My deterministic
   rules reward strings like `multi-asset`, `asset allocation`, `discretionary`.
   A single-asset specialist who writes broad-sounding prose scores falsely high;
   a genuine cross-asset PM who writes tersely scores falsely low. A's signals
   (title=CCO, employer=boutique AM, "CMS licence") are far more verifiable than
   B's. The LLM blend helps but inherits the same thin evidence.

3. **Multiple archetypes, one averaged rubric.** B legitimately has 3+ winning
   shapes (ex-SFO PM / private-bank-PM-with-book / senior buy-side discretionary).
   My engine scores everyone against the *same* weighted rubric, so a strong
   private-bank candidate is penalised on `sfo_mfo_fit` for not being ex-SFO even
   though they're a valid archetype. A is essentially mono-archetype, so this
   never bit. Honest fix needs per-archetype scoring (see §6).

4. **The decisive signal - relationships / deal-flow - is barely in employment
   history.** `private_markets_access` tries to proxy it from prose, but GP
   networks and private-bank relationships live in activity and connections, not
   job titles. My architecture has no view of that data, so this 0.18-weight axis
   is the weakest-grounded score in the whole config.

---

## 5. Estimated credit allocation if I ran B today

I would **re-shape the 300 split** because B's bottleneck is coverage, not the
size of one clean pull.

| Phase | Mandate A (actual plan) | Mandate B (would be) | Why different |
|---|---:|---:|---|
| Dev / filter validation | ~50 | **~80** | B's filter is vaguer (generic titles) and needs *more* iteration to find a precise-enough query; I'd spend more on small exploratory pulls reading raw profiles. |
| Production pull | ~220 | **~150** | The qualified universe is genuinely smaller; spending 220 would mostly buy near-duplicates and noise, not fits. |
| Reserve | ~30 | **~70** | Larger reserve to fund a *second* differently-filtered pull (e.g. by-employer at known SFOs/MFOs) because no single query will have good recall on a low-footprint pool. |

Headline: B is a **wider-net, multi-query, lower-yield-per-credit** problem; A is
a **single disciplined pull** problem. Same 300 budget, deliberately different
shape - and on B I'd be quicker to *ask for more credits with the measured
shortfall* (per the brief), since the constraint is real coverage scarcity, not
my discipline.

---

## 6. Code changes I'd genuinely need anyway (can't be config)

Being honest about the limits of the config abstraction:

1. **Per-archetype scoring** (fixes §4.3). Today one rubric scores everyone.
   Supporting "score against the best-matching of N archetypes, take the max"
   needs a new `scoring.archetypes:` construct *and* engine code in `scoring.py`
   to branch and select. This is the biggest honest gap.

2. **A coverage / data-sufficiency router** (fixes §4.1). A new pre-scoring stage
   that detects thin-but-promising profiles and routes them to a human-review
   queue instead of down-ranking them - new control flow in `pipeline.py`, not a
   YAML knob.

3. **New deterministic rule *types*** for relationship/deal-flow signals
   (fixes §4.4) - e.g. a connections/network feature. `scoring._eval_rule` only
   knows the rule kinds I've implemented; a `network_overlap` rule is new Python.

4. **Company normalisation** for the SFO/MFO/private-bank landscape - useful for
   A, closer to *necessary* for B where employer identity carries more of the
   signal and SFO names are inconsistent.

If this list were empty I'd be overclaiming. That it's four items long is the
honest read: the config abstraction cleanly handles *mandates of the same shape*
(swap a search), and starts to strain when the new mandate has a structurally
different evidence model - which B does.
