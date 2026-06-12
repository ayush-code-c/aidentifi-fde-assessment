# Q4 - Company Brain

## 1. What it means, specifically for executive search

A Company Brain for executive search is **not** a RAG assistant over the firm's
documents, and it is not a better CRM. Candidate data is a commodity - it can be
re-pulled from Coresignal or LinkedIn on any given morning. The thing that is
*not* re-pullable, and therefore the only thing worth institutionalising, is the
firm's **accumulated judgment about people against mandates, and how that
judgment turned out.**

So I define it precisely: the Company Brain is the **queryable institutional
memory of fit-judgments and their outcomes** - every mandate's *real* (often
unstated) success criteria, every candidate ever assessed against them, the
ranking the firm gave, the decision the client made, and what happened to the
placement afterwards. It is a **calibration engine**, not a knowledge store. Its
job is to make the next ranking better than the last by remembering how the last
one was right or wrong.

## 2. Architecture sketch

**Captured**
- *Mandate objects*: the brief **plus** the inferred fit criteria behind it (the
  Jatayu config is literally this, versioned).
- *Assessment records*: every sourced candidate, their sub-scores, the rationale,
  and any **recruiter override** (the tool's score vs the human's final rank).
- *Decision feedback*: who the client shortlisted, interviewed, rejected - and the
  stated reason.
- *Outcome records*: who was hired, and placement tenure / success at 6 and 12
  months.

**Where it lives**
A candidate ⇄ mandate ⇄ outcome **graph** (the edges are the judgments), a
**vector index** over rationales/briefs for semantic recall, and the **scoring
configs as first-class versioned artifacts** so "how we defined fit" is itself
history.

**How it's queried / by whom**
- *A recruiter opening a new mandate* asks: "Show everyone we've assessed for a
  *sole-CCO-at-a-boutique-SG-AM* shape, ranked, with what the client decided and
  how the placement held up." They get a calibrated shortlist **seeded from
  history**, plus the deltas this mandate has vs past ones - and Jatayu's config
  pre-populated from the matching archetype.
- *A partner* asks: "Which fit signals actually predicted client acceptance last
  year?" - pipeline-level analytics, not a single search.
- *Mid-mandate*, the same recruiter logs an override; that write is the Brain
  learning, not an afterthought.

## 3. Top 3 data sources to ingest first (ranked by ROI per unit of effort)

1. **Past mandate outcomes - client decisions + placement tenure.** *Highest ROI.*
   It is the ground-truth label that calibrates everything else, it already
   exists (ATS, emails, partner notes), and ingestion is modest structuring work.
   Without it the Brain has opinions but no scorecard. (It is also exactly the
   label set Jatayu's Q3 calibration needs.)
2. **Recruiter rationale + overrides - the *why* behind each ranking.** High ROI
   because it encodes the firm's tacit judgment, and it is *cheap to capture if
   you instrument the tools to emit it* - Jatayu already produces a rationale and
   an override path, so this is near-free to start logging now.
3. **The raw sourced-candidate corpus + fit scores (every Jatayu run).** Lower
   immediate ROI but *compounding*: it's large, structured, and a free byproduct
   of doing the work - but it's inert until sources #1 and #2 give it labels and
   reasons. Ingest continuously, mine later.

Order is deliberate: **labels before reasons before raw volume.** Most firms do
the reverse (hoard profiles first) and wonder why the Brain never gets smarter.

## 4. What it should learn over time (signal humans miss or forget)

- **Calibration drift:** which signals recruiters *believe* matter vs which
  actually predicted acceptance and tenure (e.g. "VCC exposure correlated with
  client shortlisting but not with a successful 12-month placement; sole-ownership
  predicted both").
- **Client taste fingerprints:** the gap between what a client *says* in the brief
  and who they *actually* pick - revealed preference per client.
- **Mandate archetypes:** the firm re-discovers the same handful of search shapes
  repeatedly; the Brain names them and pre-loads the config and prior shortlist.
- **Re-engagement timing:** the candidate rejected as "too junior" two years ago
  who is now exactly right - humans forget the pipeline; the Brain doesn't.
- **Per-recruiter calibration:** whose "90% fit" actually means 90%, so scores
  become comparable across the team.

## 5. One non-obvious insight

**The obvious-LLM-summary version** (what Opus would produce): *"A Company Brain
centralises the firm's collective knowledge - past placements, candidate
profiles, client relationships - into a searchable AI layer so recruiters find
information faster, onboard quicker, and get better recommendations that improve
as more data accumulates."* That framing optimises for **retrieval of what you
kept**, and what firms instinctively keep is their **wins**.

**My claim, which differs:** the highest-value data in an executive-search Brain
is the data firms currently treat as garbage - the **negative space and the
errors.** Who the client *passed on* and what happened to them next; the
candidate you ranked #1 who flamed out; the brief that turned out to be wrong;
every recruiter override against the tool. **Calibration is a function of your
mistakes, not your successes** - a Brain that only remembers placements learns
almost nothing, because a placement confounds fit with luck, chemistry and
politics, while a *rejection-with-an-outcome* is a clean-ish counterfactual. So
the Brain's primary engineering job is not retrieval; it is **systematically
instrumenting the loss** - capturing overrides, rejections, and churned
placements as the crown-jewel dataset - which is precisely the exhaust most
"company brain" projects discard as noise or as embarrassing. The moat is the
counterfactuals, not the corpus.

The difference is operational, not philosophical: the obvious version tells you to
*ingest more*; mine tells you to *instrument failure* - and to build the tools
(Jatayu included) so that every disagreement and every bad outcome is a logged,
structured training example by default.

## 6. What I'm least sure about

Whether **client decisions are a clean enough label to learn from.** Clients hire
for reasons that have nothing to do with candidate quality - internal politics, a
board member's referral, chemistry, timing, budget. If I calibrate the firm's fit
model on "the client shortlisted them," I may be training it to **predict client
behaviour rather than candidate quality**, and those two diverge exactly when it
matters most (the strong candidate the client politically couldn't hire). My
insight in §5 leans hard on outcomes-as-signal, so it is most exposed precisely
here: the negative/counterfactual data is only as good as the cleanliness of the
outcome label attached to it, and in this domain that label is noisy and
confounded. I'd de-risk it by separating two outcome signals - *client decision*
(noisy, political) vs *placement tenure/success* (slower but cleaner) - and
trusting the latter more, but I'm genuinely unsure that even 12-month tenure is
clean enough to be a training target rather than a weak prior.
