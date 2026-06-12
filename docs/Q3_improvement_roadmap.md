# Q3 - Improvement Roadmap

**Budget:** USD 5,000 per tool (USD 10,000 total). **Time:** 5 weeks total,
allocated across both tools. Dollars fund *non-engineering* costs (labeling, API
credits, data, contractor hours); weeks are my engineering time.

**Allocation at a glance**

| | Jatayu | Outreach | Total |
|---|---:|---:|---:|
| Budget | $5,000 | $5,000 | $10,000 |
| Time | 3.25 wks | 1.75 wks | 5.0 wks |

I weight engineering time toward **Jatayu** because filter precision + ranking
are the metrics with the biggest measured differential and the steepest curve to
climb; Outreach is closer to "good" already and its gains are mostly workflow.

---

## Tool 1 - Jatayu  ($5,000 / 3.25 weeks)

### #1 - Ground-truth calibration harness *(highest ROI)*
The weights and point values are currently *reasoned, not fitted*. The single
biggest lever on ranking quality is learning them from the team's real
shortlists.

- **Build:** export ~120 historically-sourced profiles the team labelled
  (shortlisted / rejected) across 2–3 past mandates; a pairwise-ranking fit
  (logistic on sub-score features) to learn weights + point values; a held-out
  rank-correlation report per mandate shape.
- **Budget:** $1,400 labeling/cleanup contractor (≈40 hrs) · $400 Coresignal
  credits to reconstruct the calibration set · $200 LLM API for the rubric pass
  during tuning = **$2,000**.
- **Time:** **1.5 weeks.**
- **Expected impact:** top-10 overlap with the team's actual shortlist from an
  estimated **~50% → ~75%** on AAAM-shape (Mandate-A) mandates; Spearman rank
  correlation target ≥ 0.6 on held-out.
- **Trade-off accepted:** weights tuned on past mandates can over-fit the firm's
  historical taste and travel worse to a genuinely new mandate shape; I accept
  reduced novelty-robustness in exchange for tracking the team on its bread-and-
  butter searches, which is what the metric rewards.

### #2 - Two-pass enrichment (credit-efficient wide net)
Today we collect (pay for) every searched profile, which caps how wide the filter
net can be inside 300 credits.

- **Build:** score a cheap **first pass** on the lightweight search payload
  (title/company/industry), collect full profiles only for the top slice; lets
  us cast a wider initial net and *re-filter* on real precision.
- **Budget:** $700 Coresignal credits for A/B pull experiments (wide-net vs
  current) · $300 LLM API = **$1,000**.
- **Time:** **1.0 week.**
- **Expected impact:** count of 90%+ fits in the raw production pull from an
  estimated **~35% → ~55%** of the pull (wider net, same budget); credits per
  90%+ fit down **~40%**.
- **Trade-off accepted:** the first pass scores on thinner data, so a few strong-
  but-terse profiles get cut before enrichment; mitigated by a "low-data-high-
  title" bypass, but some recall risk remains.

### #3 - Evidence extraction replacing brittle regex
Some deterministic rules over-reward keyword-stuffed profiles and under-reward
terse strong ones.

- **Build:** an LLM extraction step that returns structured, *quoted* evidence
  per dimension ("sole compliance owner? Y/N + verbatim quote"), feeding both the
  score and the rationale.
- **Budget:** $700 LLM API (dev + eval over the calibration set) · $300 contractor
  spot-check of extraction accuracy = **$1,000**.
- **Time:** **0.75 week.**
- **Expected impact:** false-high rate on keyword-stuffed profiles down from an
  estimated **~25% → ~10%**; rationales cite verbatim evidence (qualitative, but
  measured by reviewer "trust the rationale" rate).
- **Trade-off accepted:** adds latency and per-profile LLM cost to scoring; fine
  at top-200 scale, would need batching beyond that.

---

## Tool 2 - Outreach  ($5,000 / 1.75 weeks)

### #1 - Guardrail-as-gate + triage workflow *(highest ROI)*
The grounding guardrail currently *reports*; at 100 recipients it must *gate*.

- **Build:** auto-classify each draft into send-eligible / review-queue / reject
  using existing flags + confidence + recipient tier; a one-screen review UI for
  the queue.
- **Budget:** $1,200 a few days of a contract front-end dev for the review UI ·
  $300 LLM API for batch testing = **$1,500**.
- **Time:** **0.75 week.**
- **Expected impact:** partner review time per 100 recipients from an estimated
  **~3 hrs → <1 hr**; share of sent messages with an unsupported specific claim
  **→ <2%**.
- **Trade-off accepted:** a conservative gate sends fewer fully-automated messages
  (more land in the review queue), trading raw throughput for claim-safety - the
  right trade for senior outreach.

### #2 - Sparse-coverage enrichment hop + skeleton variant banks
Two scale failures at once: thin median profiles and template repetition.

- **Build:** a light Coresignal lookup to lift ≥1 specific hook before degrading
  to category-level; per-angle bank of 3–4 skeleton variants chosen by recipient-
  id hash; batch near-duplicate detector.
- **Budget:** $1,500 Coresignal credits for the enrichment hop at volume ·
  $500 LLM API for variant generation/eval = **$2,000**.
- **Time:** **0.75 week.**
- **Expected impact:** share of recipients with ≥1 specific hook from an estimated
  **~40% → ~70%**; max pairwise message similarity within a 100-batch below
  **0.6** (cosine), eliminating obvious twins.
- **Trade-off accepted:** the enrichment hop spends credits on BD prospects (not
  billable mandates), so it needs a per-campaign budget cap; deeper personalisation
  for thin profiles costs real money.

### #3 - Reply tracking + CTA A/B feeding angle selection
Close the loop on what actually books meetings.

- **Build:** lightweight reply/booking tracking; A/B two CTAs per angle; feed
  booked-rate back into angle weights.
- **Budget:** $1,000 (email/tracking tooling subscription for the campaign window
  + minor integration cost) = **$1,000**.
- **Time:** **0.25 week** (instrument now, value compounds over later campaigns).
- **Expected impact:** establishes the **booked-meeting rate** as the north-star
  metric (currently unmeasured); target a measurable lift of **+1–2pp** on
  reply-to-meeting over the first two campaigns once angle weights are tuned.
- **Trade-off accepted:** real signal needs volume and time, so this pays off
  later than the other two; I fund it small and early precisely because the data
  it gathers is the input to *next* quarter's improvements.

---

## The cross-tool trade-off I'm accepting

Spending 3.25 of 5 weeks on Jatayu means Outreach gets workflow-and-coverage
fixes but **no model-quality / calibration work** this cycle - its register
quality stays at "good template + decent LLM," not "indistinguishable from a
partner." I accept that because Jatayu's metrics (filter precision, ranking
alignment) are where the largest graded differential sits and where calibration
has the steepest payoff; Outreach's marginal dollar is better spent making the
existing quality *survive 100× scale* than making 5 messages 10% prettier.
