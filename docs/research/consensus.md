# Consensus & narrative monitor (agent 7): literature review

Full write-up (Docs): https://claude.ai/code/artifact/40d845c6-a148-4504-9a03-f33b90072127 · 10 Oct 2026

**Bottom line.** The evidence supports *describing* the crowd, not trading against it.
- News attention, measured as a share of all coverage, is a real state variable.
- Tone effects are small, reverse within days and decay after publication.
- CFTC extremes and trend signs mostly restate the same price move.

So the monitor maps where attention, positioning and trend sit relative to Bernardo's ideas. It stays descriptive until a component passes the quant-research gate.

## Papers: narratives and news text

| Finding | What it changes | Source |
|---|---|---|
| Narratives spread like epidemics: reach depends on contagion vs forgetting. Paths are hump-shaped and can revive. Word counts are an imperfect measure. | Stages from level and slope (spreading, peaking, fading, dormant, steady); no fitted contagion model | [Shiller 2017](https://www.nber.org/papers/w23075.pdf) |
| About 11m Dow Jones articles: 13 narrative "epidemics" from 1995 to 2016, averaging 4–5 months | Read the last 4 weeks against the prior 26 | [Larsen & Thorsrud](https://www.ifo.de/DocDL/cesifo1_wp7468.pdf) |
| Salience moves beliefs: negative front-page stories on down days raise perceived crash probabilities | Intensity matters more than tail volume | [Goetzmann, Kim & Shiller](https://www.nber.org/system/files/working_papers/w22143/revisions/w22143.rev0.pdf) |
| Tetlock: 1 sd of pessimism → −8.1 bp next day, reversed over days 2–5. Garcia: about 12 bp in recessions, mostly reversed in 4 days | Tone is an attention flag, not a direction | [Tetlock 2007](https://www.columbia.edu/~pt2238/papers/Tetlock_Media_Sentiment_JF.pdf); [Garcia 2013](https://leeds-faculty.colorado.edu/garcia/media_v33.pdf) |
| 73.8% of general "negative" words aren't negative in finance; "crude" is one of them | GDELT tone compared only with its own history | [Loughran & McDonald 2011](https://www.uts.edu.au/globalassets/sites/default/files/adg_cons2015_loughran-mcdonald-je-2011.pdf) |
| Attention share across 180 WSJ topics explains 25% of market return variation in-sample and 17.8% out of sample | Strongest support for an attention map (contemporaneous) | [Bybee, Kelly, Manela & Xiu](https://www.nber.org/system/files/working_papers/w29344/w29344.pdf) |
| The sign of sentiment flips by topic and period. Energy-topic shares raise the oil R² (draft) | Interpret each narrative by topic; oil text is a hypothesis for the gate | [Calomiris & Mamaysky](https://nber.org/papers/w24430.pdf); [Cakir Melek et al.](https://www.eia.gov/finance/markets/reports_presentations/2019/calomiris_paper.pdf) |
| Daily news predicts for 1–2 days; weekly aggregates for about 13 weeks | Score weekly windows, not single days | [Heston & Sinha](https://www.federalreserve.gov/econresdata/feds/2016/files/2016048pap.pdf) |
| Dictionaries fit when prior knowledge is strong. Validate with 20–30 hand-read documents. Topic models are unstable | Hand-written frozen queries; headline audit before any validation claim | [Gentzkow, Kelly & Taddy](https://web.stanford.edu/%7Egentzkow/research/text-as-data.pdf) |
| EPU and GPR: conjunction queries divided by total coverage; audit correlation 0.86–0.93 | Query template (share of total); GPR and EPU are the later validation series | [Baker, Bloom & Davis 2016](https://users.ssc.wisc.edu/~mchinn/bakerbloomdavis_QJE2016.pdf); [Caldara & Iacoviello 2022](https://www.matteoiacoviello.com/gpr_files/GPR_PAPER.pdf) |
| FOMC wording leads the funds rate; a Fed-specific dictionary beats general ones | Fed keyword counts, described only | [Lucca & Trebbi](https://nber.org/system/files/working_papers/w15367/w15367.pdf); [Gardner, Scotti & Vega](https://www.federalreserve.gov/econres/feds/files/2021074pap.pdf) |
| High attention brings price pressure, then reversal; uncovered names earn about 3% a year more | Flag quiet ideas as well as crowded ones | [Da, Engelberg & Gao](https://conference.nber.org/confer/2009/mms09/Da_Engelberg_Gao.pdf); [Fang & Peress](https://www.insead.edu/sites/insead/files/assets/faculty-personal-site/lily-hua-fang/documents/media-coverage-and-the-cross-section-of-stock-returns.pdf) |
| Published predictors lose 58% after publication | Descriptive only; every score stored for later tests | [McLean & Pontiff](https://counterpointfunds.com/wp-content/uploads/2017/07/PredictabilityMcleanPontiff.pdf) |

## Papers: positioning, trend and CTA proxies

| Finding | What it changes | Source |
|---|---|---|
| Time-series momentum persists 1–12 months, then partly reverses. Speculators add after gains | MM percentile and trend score are collinear: shown side by side, not as two votes | [Moskowitz, Ooi & Pedersen 2012](https://fairmodel.econ.yale.edu/ec439/jpde.pdf) |
| Equal-weighted 1/3/12-month trend: net Sharpe 0.77 since 1880, but 0.62 in 2000–2013 | The canonical blend | [Hurst, Ooi & Pedersen](https://www.TrendFollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf) |
| The blend explains R² 0.36–0.64 of CTA returns | A description of trend followers' direction, not a position estimate | [AQR, Demystifying Managed Futures](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/Demystifying-Managed-Futures.pdf) |
| A capped continuous score matches the sign rule's Sharpe with less turnover | Direction plus capped strength | [Baltas & Kosowski 2017](https://www.cmegroup.com/education/files/demystifiing-time-series-momentum-strategies.pdf) |
| Out of sample only 3 of 55 assets show significant trend | The proxy describes; it does not predict | [Huang, Li, Wang & Zhou 2020](https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html) |
| The 3-year 20/80 percentile rule: 5 rejections in 30 tests; returns lead positions in all 10 markets | Extremes = crowding context, never a timing call | [Sanders, Irwin & Merrin 2009](https://ageconsearch.umn.edu/record/54547/files/JARE_Aug09__04R_pp276-296.pdf) |
| Managed money moves with price about 70% of weeks | Agreement flag between trend and MM; disagreement is the interesting case | [Fishe & Smith](https://arefiles.ucdavis.edu/uploads/filer_public/e7/80/e7805170-bc16-4683-b3c4-52b6b0b34a96/speculation_fishe_smith_final.pdf) |
| Inventories and basis earn the commodity premium; positions don't predict it | Front months only: no curve state yet (known gap) | [Gorton, Hayashi & Rouwenhorst 2013](https://www.nber.org/papers/w13249.pdf) |
| Crowding shows up as co-movement and makes reversals larger | Crowded = fragile; timing unknowable | [Lou & Polk](https://personal.lse.ac.uk/polk/research/hhab117.pdf); [Brunnermeier & Pedersen](https://markus.scholar.princeton.edu/publications/market-liquidity-and-funding-liquidity) |
| CFTC data are as of Tuesday, published Friday; "managed money" includes discretionary funds | Captions on every CFTC line; MM ≠ CTAs | [CFTC notes](https://www.cftc.gov/MarketReports/CommitmentsofTraders/DisaggregatedExplanatoryNotes/index.htm) |
| A promoted signal needs t > 3 after counting every variant tried | Log every lookback and threshold before any promotion | [Harvey, Liu & Zhu 2016](https://nber.org/papers/w20592) |

## GDELT
- **API.** DOC 2.0 API, free and keyless; terms allow use with a citation and link.
  - `timelinevolraw` returns the count and `norm` (all articles monitored that day). `timelinetone` returns tone.
  - Timelines are documented back to 1 Jan 2017. There is no official rate limit; third parties cite one request per 5 seconds.
- **Known biases.** Source growth (we use share, not counts), syndication, regional bias, machine translation, a general tone dictionary and unannounced gaps. Event-level validity is about 21% (Wang et al. 2016), so we use aggregate attention only.
- **Fixes.**
  - Share of the total, not raw counts.
  - A gap day is dropped when `norm` falls more than 40% below its 28-day median.
  - At least 20 articles a day on average, else "insufficient coverage".
  - Weekly windows.
  - A human audit of 20–30 headlines per query before any validation claim.

## Atlas, books, vendors
- **Druckenmiller:** the crowd is right most of the time; don't be caught in the rest. → The map shows where the crowd is.
- **Marks:** second-level thinking, "what is priced in?" → Each idea is placed with the crowd, against it, or quiet.
- **Soros:** reflexivity. → "Self-reinforcing" and "twilight" labels, marked as inference.
- **Tudor Jones:** the tape. → The trend score sits beside every narrative.
- **Bouchaud:** flows and trend chasing. → The CTA proxy belongs on the map.
- **Asness:** social herding. → Measuring it matters more.
- **Books** (general knowledge): Donnelly, *Trade Outside the Box*; Shiller, *Narrative Economics*; Soros, *The Alchemy of Finance*; Marks, *The Most Important Thing*.
- **Podcast trend knowledge** (CTA lookbacks, vol targets, unwinds): to be added as an upgrade when Bernardo shares it (`notes/podcasts/top-traders-unplugged/`).
- **Vendors:** RavenPack (entity news analytics) and AlphaSense (corporate vendor review). Bloomberg sentiment is never brought into this repo. What stays ours is the map against the journal's ideas.

## Design (as built)

| Rule | Now | Source |
|---|---|---|
| News measure | Share of all monitored articles (count / norm), daily rows, read in 4-week windows; tone only as a change in sd against the query's own prior 26 weeks | Baker, Bloom & Davis; Wang et al.; Heston & Sinha |
| Stage | Windows end on the narrative's **last data day**. Spread = ln(4-week share / prior 26-week share); level percentile = mid-rank of the 28-day mean in its own history. Spreading: spread > +0.4 and up in 2 of the last 3 weeks. Fading: spread < −0.4 or more than 30% below the 8-week peak. Peaking: 80th percentile or above. Dormant: below the 20th. Otherwise steady. Stages need 240 days of history; none is given when the last data day is more than 4 days old ("stale") | Shiller; Larsen & Thorsrud |
| Queries | 18 frozen queries with version ids, each tagged with the markets it pushes and which way, plus an EPU-style validation query | Gentzkow et al.; EPU |
| Validation | Every narrative "unvalidated" until checked against GPR or EPU and a headline audit (later, by Bernardo's choice) | Caldara & Iacoviello |
| Trend proxy | Average sign of 21/63/252-day returns (display) and the integer vote (logic: 2 of 3 legs = a direction); capped strength; flip level per leg | Hurst, Ooi & Pedersen; Baltas & Kosowski |
| CFTC | 3-year managed-money percentile on the idea's side; agreement flag; caption "crowding context, not a forecast; MM ≠ CTAs" | Sanders et al.; Fishe & Smith |
| Labels | twilight, self-reinforcing, crowded, quiet, mixed per market; with the crowd, against it, quiet, mixed per idea; all marked inference | Soros; Marks; Fang & Peress |
| Alert | `narrative_spreading` when a narrative is spreading and the **previous fact pack** (up to 7 days back) did not show it; with no previous pack, against the stage one data day earlier | — |
| Rule | Descriptive until the quant gate; every score stored | McLean & Pontiff; Harvey, Liu & Zhu |

**Decided by Bernardo (10 Oct).**
- The 18-narrative commodity-first set.
- The full map in the daily fact pack; the morning note mentions only stage changes and his ideas; the critic card carries the crowd facts.
- GPR/EPU validation later.

**Stays human:** the second-order view. The map says where the crowd is; he decides what it has wrong.

## Independent review (10 Oct): findings and fixes

| # | Finding | Fix |
|---|---|---|
| 1 | The spreading alert missed about half of transitions: data run a day behind the pack, so "today vs yesterday" shared the newest data day | Windows anchored on the last data day; the alert compares against the previous pack's stage (fallback: one data day earlier); the masking test removed; regression test |
| 2 | A trend score of ±0.33 (2 of 3 legs) was treated as flat because of rounding | Logic uses the integer vote; the score is display only |
| 3 | `_stable_ranks`: duplicate (kind, id) keys swapped alerts; old files without `rank` crashed; alerts that no longer fire were treated as live | Pairing by exact text, then in order; `rank` defaults to position; `no_longer_firing` alerts are kept for refs but excluded from render, critic (severity order) and monthly counts |
| 4 | GDELT could push the Actions job past 30 minutes under rate limiting | 8-minute budget; stop after 2 consecutive failing queries; one HTTP try per attempt; no sleep after the last try; job timeout 40 minutes; skipped queries catch up next run |
| 5 | The auditor accepted one narrative's figure under another's name (shared words "oil", "fed") | Narrative rows carry an `audit_subject` of words only their name has; the consensus part of facts.md is checked from facts.json |
| 6 | GDELT details: hourly points, missing norm forcing refetch, per-source restart leaving holes, unquoted links | Per-day sums (tone mean); history keyed on counts; each query restarts from its own last day; `urllib.parse.quote` |
| 7 | Stale data still staged; NaN in JSON; ties ranked at the top | "stale" stage; no NaN; mid-rank percentile; header says "own history" |
| 8 | This file was missing | Written |

Also found while testing: a narrative with no tone rows crashed `tone_change` (now returns none).

## First live runs (10 Oct)
1. **Run 1 (v1 code)** was cancelled at the 30-minute job limit, as the review predicted; nothing was committed.
2. **Run 2 (fixed code)** finished in about 12 minutes and committed.
   - GDELT works from Actions: timelines go back to **1 Jan 2017** at **one point per day** (Hormuz: 3,532 days), which settles both open questions from the review.
   - HTTP 429 ("one request every 5 seconds") still came back at a 6-second pace. Only the Hormuz query landed before the run stopped asking; the rest catch up over the next runs.
3. **GDELT's own coverage collapsed after 1 Oct.**
   - Articles monitored per day: about 100–175k in late September, 61,712 on 2 Oct, 3,958 on 6 Oct, 678 on 8 Oct.
   - 3–5 Oct and 7 Oct are missing outright; so are 14–19 Sep.
   - The gap rule drops these days, and narratives now anchor on the last *valid* day. So Hormuz shows **stale (data through 1 Oct)** rather than a stage built on broken days. Before the collapse the same data read: "fading", at 0.47x its prior 26 weeks but at the 94th percentile of its own history.
4. **Adapter changes from the live run.**
   - Back off 30 s, then 60 s, on a refused call.
   - 12-minute budget; stop after 3 calls fail in a row.
   - Missing series are fetched first.
   - Counts are kept when the tone call fails, and each series restarts from its own last day.

Run 3 (fixed code, 30–60 s backoff): every GDELT call got HTTP 429, so nothing new landed. GitHub's shared runner addresses are probably throttled as a group. Daily runs keep trying within the budget.

Read (inference): the monitor stays stale until GDELT's totals recover. If the collapse lasts, the fallback is GDELT's raw files or another news source; that decision is Bernardo's.
