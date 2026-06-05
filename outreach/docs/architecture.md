# Outreach Generator — Architecture (Q2)

## The one idea

Personalised outreach has a single failure mode that matters at the senior level:
**saying something specific that turns out to be wrong** (or obviously generic
dressed up as specific). So the whole system is organised around *evidence with
calibrated confidence*, not around prose generation. The model writes last and
writes least; the leverage is in deciding **what may be said at all**.

## Pipeline & where the judgment lives

```
CSV ─▶ extract_hooks ─▶ confidence gate ─▶ angle select ─▶ compose (tier) ─▶ guardrail ─▶ md + reviewer panel
        evidence         specific/sparse?    rule-based       template|LLM      verify
```

- **`enrich.extract_hooks`** assigns confidence by **source**, not by model
  enthusiasm: an explicit hiring post = 0.85–0.9; a hiring *signal* flag = 0.55;
  a bio inference = 0.6; a bare title/industry = category-level (always true,
  low specificity). This is the anti-hallucination primitive — fabrication is
  prevented *before* generation by simply not handing the model unsupported facts.
- **`pipeline._approve_hooks`** enforces `min_hook_confidence` and a cap on
  specifics. If the best specific hook is below `sparse_if_top_hook_below`, the
  recipient is **sparse** and the message is held to category level.
- **`angles.select_angle`** is deterministic and auditable — the angle choice is
  itself reviewable judgment, not a model whim.
- **`guardrails.check_grounding`** is the backstop: even a well-behaved LLM can
  drift, so we scan the *output* for unsourced proper nouns, hiring claims with
  no supporting hook, and implied prior relationships, and surface them as flags.

## What's automated vs templated vs bespoke — and why the lines are there

| Layer | Treatment | Why |
|---|---|---|
| Recipient ingestion, hook extraction, confidence scoring, angle selection, grounding check | **Fully automated** | Deterministic, testable, and the same whether you run 5 or 500. This is where correctness lives, so it must not depend on a model. |
| Message *skeleton* — greeting, value-prop one-liner, angle thesis, CTA, signoff, length per channel | **Templated (config)** | These don't vary per person, only per *angle/channel*. Templating them keeps voice consistent and cost ~zero, and gives a clean fallback tier. |
| The *opening specific sentence* and phrasing | **Bespoke (LLM tier)** for high-value recipients; **deterministic template** for the long tail | Bespoke phrasing is where money is made on a senior warm intro — but only the opener genuinely needs it. The template tier produces grounded, grammatical (if plainer) copy for everyone else. |

I drew the line at *the opening specific sentence* because that is the only part
whose quality materially changes whether a senior person replies, and it is the
only part that benefits from a model's judgment about tone and emphasis. The
value prop, CTA, and structure are a firm-level decision, not a per-recipient one
— templating them is correct, not lazy.

**Why mock = template = scale-fallback (not a toy).** The committed demo runs the
deterministic template tier so it's reproducible with no key. That same tier is
deliberately the production fallback for the long tail at 100+ — so "the demo
without an API key" and "the thing that scales" are the *same code path*, which
is the honest way to show it works.

## Sparse-profile handling (explicitly tested)

The brief asks three things; here's the mechanism for each:

- **Do you hallucinate to fill the gap?** No — the model only ever receives
  approved hooks. A sparse recipient simply has no high-confidence specific hook
  to hand over, so there is nothing to hallucinate *from*. R4/R5 demonstrate this.
- **Do you degrade gracefully?** Yes — sparse recipients get a category-level
  message (role/industry truth, which is never fabricated) and a softer,
  no-pressure CTA, rather than a forced fake-specific opener.
- **Do you flag uncertainty to the user?** Yes — every sparse output is labelled
  `SPARSE ⚠️` with "specifics intentionally omitted; verify before sending," and
  the reviewer panel lists exactly which hooks were available and which were
  dropped below threshold.

## Scalability — making this work at 100+

**What stays the same.** Ingestion, hook extraction, confidence, angle selection,
guardrails — all linear, deterministic, and cheap. Per-recipient LLM cost is
rounding error on one warm conversation (the brief's own framing), so cost is not
the constraint; **review bandwidth and quality drift are.**

**What breaks at 100, concretely:**

1. **Output repetition / template fatigue.** With one template skeleton per
   angle, recipients sharing an angle get structurally identical messages. At 5
   it's invisible; at 100 a recipient who's CC'd with a peer notices. → *Fix:*
   an angle has a small bank of skeleton variants, selected by a hash of the
   recipient id; plus a near-duplicate detector across a sending batch.
2. **Profile-coverage drift.** At 100 the *distribution* shifts sparse — the
   median recipient is thinner than your hand-picked five. The sparse path must
   be the common case, not the exception. → *Fix:* a coverage dashboard and a
   per-batch "share sparse" gate that routes thin profiles to a light enrichment
   step (Coresignal lookup) before giving up on specificity.
3. **Quality drift on the bespoke tier.** LLM phrasing quality is non-uniform;
   a few in 100 will be off-register or subtly off-claim. → *Fix:* the guardrail
   becomes a *gate*, not just a reporter — messages with flags or over-length
   are auto-held for human review; only clean ones queue to send.
4. **Review bottleneck.** A partner cannot read 100 drafts. → *Fix:* triage —
   auto-send-eligible (clean, high-confidence, low-stakes), review-queue (flags
   or top-tier recipients), and reject (no usable hook + no enrichment). The
   reviewer panel already produced per message is exactly the triage payload.

**What I'd add to handle 100 well (in priority order):**
1. **Guardrail-as-gate + triage queue** (turns the existing flags into a workflow).
2. **Skeleton variant banks + batch near-duplicate detection** (kills repetition).
3. **A thin enrichment hop for sparse profiles** (lift coverage before degrading).
4. **A/B-able CTAs and reply tracking** (close the loop on what actually books
   meetings, and feed it back into angle selection).

## If I made the same choice for all five — the defense

I did *not*: angle and tier both vary by recipient (R1 scaling, R2 portfolio, R3
niche, R4/R5 category-level intros; bespoke tier for rich, template for sparse).
The one global choice is the **value-prop framing** (AI-native search, calibrated
fit) — defended because it's a *firm* positioning, not a per-recipient variable;
varying it per recipient would be incoherent, not personalised.

## Honest limitations

- The committed demo uses the template tier; real register quality needs the LLM
  tier with a key. The architecture is identical either way.
- Hook extraction is regex/heuristic; richer evidence (post threads, news) would
  need real connectors and is out of scope here.
- The guardrail is precision-oriented (few false flags) — a determined
  fabrication in a single-word company name could slip; the multiword,
  hiring-claim, and relationship checks catch the high-risk cases.
