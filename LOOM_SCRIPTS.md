# Loom recording scripts

I can't record video, so here are tight, shot-by-shot scripts to record both
Looms yourself. Keep each well under the 15-minute cap. Record in this order;
have a terminal + the Excel + the credit log open in tabs before you hit record.

---

## Loom 1 - Jatayu (target 6–8 min)

**Goal the brief states:** show the tool running, walk ONE candidate from raw
Coresignal data to final rank, and show the credit meter.

1. **(0:00–0:45) Frame the problem.** "Mandate A: sole compliance officer at a
   Singapore asset manager. The brief warns title-matching over-includes, so the
   whole design separates *exclusion* (cheap filter) from *discrimination*
   (scoring). Two run modes; I'll show offline so it's reproducible, then point at
   the one flag that makes it live."
2. **(0:45–1:45) Config is the mandate.** Open `config/mandate_a_compliance_sg.yaml`.
   Scroll the `filter:` block - "permissive on title, hard on geography +
   function, named wrong-pools excluded." Then `scoring.sub_scores:` - "five
   weighted dimensions, each blends deterministic rules with an LLM rubric. A
   recruiter tunes these weights, not the code."
3. **(1:45–2:30) Show the compiled query.** Run
   `python -m jatayu show-query --mandate config/mandate_a_compliance_sg.yaml`.
   "This is the actual Coresignal ES query the YAML compiles to - geography +
   function must, wrong-pools must_not."
4. **(2:30–3:30) Run it.** Run the `python -m jatayu run …` command. Read the JSON
   summary aloud: "44 candidates searched → filter → 23 in the raw pull → scored
   → ranked. Credits this run: 0, because offline. In live mode this line shows
   the real spend." **This is the credit meter** - point at `credits_total`,
   `credits_dev`, `credits_production`.
5. **(3:30–5:30) Walk ONE candidate raw → rank.** Open
   `deliverables/mandate_a/scoring_intermediate.csv`. Pick the rank-1 candidate.
   Show their `*__det`, `*__llm`, `*__blended` columns and the `*__hits` column -
   "here's the exact rule that fired: `+35 title~'chief compliance officer'`.
   Nothing is a black box." Then open `top10_shortlist.xlsx`, find the same
   person: read their `fit_score`, sub-scores, `rationale`, `confidence`,
   `concerns_or_flags`.
6. **(5:30–6:30) Show the sparse case.** Scroll to a `confidence=low` candidate.
   "Great title, empty summary - high potential, low confidence, surfaced not
   hidden. Fit and confidence are separate axes." Open the credit log CSV briefly.
7. **(6:30–7:00) Close.** "Going live is one `.env` flag; the strategy is 50 dev /
   ~220 production / ~30 reserve, and we never spend a credit enriching a profile
   we could reject for free first."

---

## Loom 2 - Outreach (target 4–6 min)

**Goal the brief states:** one recipient end-to-end.

1. **(0:00–0:40) Frame.** "The failure mode for senior outreach is saying
   something specific that's wrong. So the system is organised around evidence
   with calibrated confidence - the model writes last and writes least."
2. **(0:40–1:30) Data + config.** Open `data/recipients.csv` - "recipients are
   data; two are deliberately sparse." Open `config/aidentifi_positioning.yaml` -
   show the angle library and the `min_hook_confidence` / `sparse_if…` knobs.
3. **(1:30–2:15) Run it.** `python -m outreach run …`. Read the summary: "5
   recipients, 2 sparse, 0 grounding flags."
4. **(2:15–3:45) Walk ONE rich recipient end-to-end.** Open `outputs/R1_Marcus_Lim.md`.
   Read the message, then the **Reviewer panel**: angle chosen + why, the hooks
   used with confidence, the hook dropped below threshold. "The opener cites his
   actual Series-B hiring post - a 0.90-confidence hook - and nothing else."
5. **(3:45–5:00) Walk ONE sparse recipient.** Open `outputs/R4_Priya_Nair.md`.
   "Name and title only. The system refuses to invent - it degrades to a
   category-level intro, flags it SPARSE, and tells the reviewer to verify. No
   hallucinated company, no fake hiring claim." Mention the guardrail test that
   catches a fabricated 'Davos / Goldman Sachs' specific.
6. **(5:00–5:30) Scale.** "Same template tier is the 100+ fallback; the
   architecture doc covers the triage queue and repetition controls."
