# Clarifying questions for Aidentifi (first-48h window)

The brief allows up to 5 written questions in the first 48 hours; after that,
document assumptions and proceed. These are ordered by how much they change the
work - ask the top ones first. Copy/paste-ready below.

---

**To:** shashank@aidentifi.com
**Subject:** FDE assignment - a few clarifying questions

Hi Shashank,

Thanks for the brief - it's a genuinely good problem. A few questions while I'm
inside the 48-hour window; I'll document assumptions and proceed on anything you
don't get to.

1. **Ground-truth calibration data.** Ranking quality is graded against your
   team's actual shortlist. Could you share even ~15–25 anonymised profiles (or
   Coresignal IDs) from a past mandate of similar shape, labelled
   shortlisted/rejected? It would let me calibrate weights against your real
   taste rather than my priors - and it's the single biggest lever on the
   ranking-alignment metric.

2. **Coresignal product/endpoint scope.** I've built against the **v2 Clean
   Employee API** (`/employee_clean/search/es_dsl` + `/collect/{id}`, `apikey`
   header, 1 credit per search request and per collect). Can you confirm that's
   the intended product and that bulk-collect is available on the trial, so my
   credit log matches how your account actually meters?

3. **Mandate-A firm-scale signal.** The decisive "boutique independent AM vs
   bulge-bracket / Big-4 / regulator" distinction often isn't a clean structured
   field in Coresignal. Do you have a preferred source of truth for **firm AUM /
   headcount** (e.g. a curated SG AM list I can normalise against), or should I
   treat company-size + industry as the best available proxy?

4. **"AI onboarding under own licence."** For Mandate A, how strictly should
   direct **Accredited-Investor onboarding under the firm's own CMS licence**
   gate a candidate - is it a hard must-have (filter), or a strong positive that
   can be outweighed (score)? I've modelled it as a heavily-weighted score, not a
   filter, to avoid losing strong-but-terse profiles.

5. **Credit top-up preference.** If the dev pull shows 300 credits won't reach a
   dense-enough raw pull, do you prefer I (a) request additional credits with the
   measured shortfall, or (b) spin up a second trial account? You said both are
   tracked - I'd default to (a) for Mandate A since the constraint there is filter
   quality, not raw volume, but want to respect your preference.

Happy to proceed on sensible defaults for any of these. Thanks!

[name]

---

### Why these five (internal note, don't send)

- **Q1** is the highest-leverage ask - it directly raises the ranking metric and
  feeds the Q3 calibration roadmap. Lead with it.
- **Q2** de-risks the credit log being graded against a wrong cost model.
- **Q3/Q4** are the two places Mandate A's signal is genuinely ambiguous (firm
  scale; how hard to gate AI-onboarding) - asking shows you found the real edges.
- **Q5** turns the credit constraint into a judgment conversation, which the brief
  explicitly says it's evaluating.
- Deliberately **not** asking: anything answered in the FAQ (LLM keys, LinkedIn
  scraping, IP), or anything the brief says is intentionally under-specified and
  "part of the test" (weighting judgment, mandate choice).
