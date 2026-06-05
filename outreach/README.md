# Outreach Generator (Q2)

Generates personalised BD outreach to senior decision-makers Aidentifi might want
to start conversations with — grounded in each recipient's professional context,
in the register a senior partner would write themselves.

The core stance: **personalise from evidence with confidence, degrade gracefully
when evidence is thin, and never fabricate to fill a gap.**

## Run it (no keys, no cost)

```bash
cd outreach
pip install -r requirements.txt        # PyYAML is enough for the template tier
export PYTHONPATH=src
python -m outreach run \
  --recipients data/recipients.csv \
  --positioning config/aidentifi_positioning.yaml \
  --out outputs
```

Writes one `.md` per recipient in `outputs/` plus `_run_summary.json`. Each file
has the outreach **and** a "Reviewer panel" showing the angle chosen, the hooks
used (with confidence), hooks dropped below threshold, and any grounding flags.

Use a real LLM for the bespoke tier:

```bash
cp .env.example .env        # set ANTHROPIC_API_KEY
OUTREACH_LLM_PROVIDER=anthropic python -m outreach run --recipients data/recipients.csv \
  --positioning config/aidentifi_positioning.yaml --out outputs
```

## Recipients are data, not code

`data/recipients.csv` — swap in your own (the brief says bring your own data;
source legally via your LinkedIn / Coresignal trial). The five committed ones are
realistic synthetic stand-ins across varied industry/seniority/hiring patterns;
**two (R4, R5) are deliberately sparse** to exercise the low-information path.

| | Recipient | Profile | Angle chosen |
|---|---|---|---|
| R1 | Founder/CEO, fintech (explicit hiring post) | rich | `scaling_senior_team` |
| R2 | PE Partner (portfolio boards) | rich | `portfolio_talent` |
| R3 | COO, independent asset manager | rich | `hard_to_fill_niche` |
| R4 | Family-office Principal (name+title only) | **sparse** | `founder_first_senior_hire` → category-level |
| R5 | Head of People, healthcare (name+title only) | **sparse** | `general_introduction` → category-level |

## How it works

```
recipient (CSV) ─▶ extract_hooks ─▶ confidence-filter ─▶ select_angle ─▶ compose ─▶ guardrail
                   (evidence+conf)   (sparse?)            (rule-based)   (tier)     (anti-hallucination)
```

1. **Extract hooks** (`enrich.py`) — turn raw fields into citable facts, each
   with a confidence assigned by *source reliability* (an explicit hiring post >
   a bio inference > a bare title) and a `kind` (`specific` vs `category`).
2. **Confidence filter** (`pipeline._approve_hooks`) — only hooks above
   `min_hook_confidence` may be referenced. If the best *specific* hook is too
   weak, the recipient is flagged **sparse** and the message stays category-level.
3. **Select angle** (`angles.py`) — deterministic rules map the recipient to the
   best value-prop angle; thin signals fall back to a general introduction.
4. **Compose** (`llm.py`) — two tiers, same grounded brief (see architecture doc).
5. **Guardrail** (`guardrails.py`) — scan output for unsourced proper nouns,
   unsupported hiring claims, or implied prior relationships; surface as flags.

Full design + scalability + what-breaks-at-100 in
[`docs/architecture.md`](docs/architecture.md).

## Test

```bash
PYTHONPATH=src python tests/test_smoke.py
```
Asserts ≥2 sparse recipients handled, that the guardrail catches fabricated
specifics (Davos / Goldman Sachs / a made-up company), and that the grounded
template tier emits zero flags.
