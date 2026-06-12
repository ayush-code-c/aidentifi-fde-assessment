# Submission checklist

Send a single email to **shashank@aidentifi.com** by the deadline (7 days from
kickoff, 23:59 SGT) with the Git repo URL and all deliverables linked/attached.

## Before you send - do these (the human-in-the-loop items)

- [ ] **Live Coresignal pull (Q1).** Get the 300-credit trial. Set
      `CORESIGNAL_API_KEY` and `JATAYU_MODE=live` in `jatayu/.env`. Run the dev
      validation pulls (~50 credits), then the production pull. Re-run
      `python -m jatayu run …`. Replace the committed offline deliverables with
      the live ones. Confirm `credit_log_production.csv` shows real spend.
- [ ] **Swap in 5 real outreach recipients (Q2).** Replace
      `outreach/data/recipients.csv` with 5 real people sourced legally (keep ≥2
      sparse). Re-run; review the 5 outputs.
- [ ] **Record Loom 1 (Jatayu)** per `LOOM_SCRIPTS.md`. Paste the share link below.
- [ ] **Record Loom 2 (Outreach)** per `LOOM_SCRIPTS.md`. Paste the share link below.
- [ ] **Pick a real LLM provider** (optional but recommended for Q2 quality): set
      `OUTREACH_LLM_PROVIDER=anthropic` + key, re-run, eyeball the register.
- [ ] **Push the repo** to GitHub (private; add the reviewer) and confirm the URL.

## Deliverables to link in the email

- [ ] Git repo URL
- [ ] Q1 - Jatayu README + architecture doc
- [ ] Q1 - top-10 Excel shortlist
- [ ] Q1 - raw production pull CSV (filter-precision audit)
- [ ] Q1 - scoring intermediate CSV
- [ ] Q1 - credit log CSV (dev + production)
- [ ] Q1 - Loom 1 link: ____________________
- [ ] Q1b - config migration document
- [ ] Q2 - outreach repo + 5 outputs + architecture doc
- [ ] Q2 - Loom 2 link: ____________________
- [ ] Q3 - improvement roadmap
- [ ] Q4 - Company Brain

## Clarifying questions (brief allows up to 5 in first 48h)

If you want to use them, the highest-value ones to ask Aidentifi:
1. Confirm the Coresignal credit cost model (per-profile collect = 1 credit?) so
   the credit log is accurate.
2. Can they share even ~20 labelled profiles from a past mandate's shortlist? It
   would let you calibrate ranking against real ground truth (Q3 #1).
3. Confirm the exact Coresignal product/endpoint they expect (clean Employee API,
   bulk download) and any account quirks.

If unanswered, the repo documents its assumptions and proceeds - as the brief
instructs after 48h.

## Honest "what I cut" note (brief invites this)

State plainly in the email what is offline-only vs live-run, and that the Looms +
live pull were done by you on top of the delivered system. The brief explicitly
prefers a complete Q1 with thoughtful Q1b over a rushed pass at everything - this
submission completes all five, with the live data pull and Looms as the
final human steps.
