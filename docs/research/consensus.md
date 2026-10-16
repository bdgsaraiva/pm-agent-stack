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

## Data source v2 (15 Oct): GDELT through BigQuery, headline links, narrative tracker
Notes-and-keys track (`docs/project/notes-and-keys-kickoff.md`). Bernardo's feedback: the note has no news to link, and tracking the narratives matters most.

| Finding | What it changes | Source |
|---|---|---|
| The DOC API refuses GitHub's shared runner addresses (HTTP 429 on most calls since 10 Oct) | The measured series move to GDELT's public BigQuery copy, read with a service account (repo secrets `GCP_SA_KEY`, `GCP_PROJECT_ID`); the DOC adapter stays as a fallback | Run 3 above; GDELT BigQuery docs |
| The GKG is partitioned by ingest day; a partitioned query reads only the days asked for (GDELT's blog: ~15 GB for 15 days vs 423 GB unpartitioned). BigQuery bills by the columns read, across the partitions read | Filter on `_PARTITIONTIME`; the daily series read two small columns (`DocumentIdentifier`, `V2Tone`); only the headline query reads `Extras` (page title), for 3 days at most | GDELT blog on the partitioned GKG; BigQuery pricing |
| The BigQuery sandbox gives 1 TiB of queries a month free | Dry run before every query, then `maximum_bytes_billed`; caps of 60 GB a query, 150 GB a run, 800 GB a month, in a committed ledger (`data/obs/gdelt_bq/_bytes.json`); a chunk that does not fit is halved, then the run stops | BigQuery sandbox docs |
| The GKG holds no article text, so the DOC full-text queries cannot be replayed as they are | A new instrument with new ids (`gdeltbq:<qid>:*`): each frozen query is matched on the words of the article's URL path (most sites put the headline there). Operators like `sourcecountry:` are dropped and logged. Never mixed with the DOC series inside one narrative | GKG 2.0 codebook |
| Event-level validity is low (Wang et al.: ~21%) and URL-path matching is new | Every narrative stays "unvalidated"; the 20–30 headline audit (`pmstack narratives audit <id>`) is drawn from stored headlines and scored into the tracker (share of headlines that are really about the narrative) | Wang et al. 2016; Gentzkow, Kelly & Taddy |
| Readers need "since when" and "what moved it", not just today's stage | Narrative tracker (`data/narratives/tracker.json`): stage, first data day of the stage (rebuilt from 180 days of stored series when a record starts; then observed), every change with the headlines seen then | Shiller (narratives as epidemics: the timing matters) |
| Syndication inflates counts (a known GDELT bias) | Used as a prominence ranking for headlines only (most-carried titles first), never in the share | Consensus review above |

**Not yet known (first Actions run will tell).** (1) Real bytes per day of the two columns, and of `Extras`. The caps hold whatever they are. (2) Whether GDELT's ingest collapse after 1 Oct also shows in the GKG on BigQuery: `gdeltbq:norm` will show it, and the gap rule then drops those days just as for the DOC series. (3) How many articles the URL-path match keeps per narrative; a narrative under 20 a day reads "insufficient coverage".

**OPEC query.** `opec_supply_v1` was retired: the DOC API rejects the quoted "OPEC+" ("The specified phrase is too short", confirmed 15 Oct). `opec_supply_v2` drops it; every "OPEC+" article also contains the word OPEC, so the meaning holds.

**CFTC date.** The consensus map now counts a CFTC report from its Friday release (Tuesday + 3 days), as risk.py does, so a pack built on a Thursday never uses that week's report.

**First live run (16 Oct, 00:45 UTC, run 38830655542).** URL-path instrument (`gdeltbq`): backfill to 1 Aug 2025 in one run, 27 GB (about 0.06 GB a day for the series; the headline query with `Extras` read 0.51 GB for 3 days). 93 headline rows. Findings:
1. **No collapse in the GKG.** `gdeltbq:norm` runs at about 300k web articles a weekday through 15 Oct with no gap; the post-1 Oct collapse was the DOC API's alone.
2. **URL-path matching is too thin:** only Hormuz (~90 a day), US pump prices (~92), trade war (~19) and inflation scare (~11) had material counts; 14 of 18 narratives read "insufficient coverage".
3. **Weekends are ~0.55x a weekday** in the GKG, so the gap rule (28-day median) dropped ordinary weekends.

Changes: a second instrument `gdeltbqt` matches each phrase in the page title **or** the URL path (a separator keeps a phrase from spanning the two), at ~0.17 GB a day (whole backfill ~75 GB). It is first in `consensus.instruments`; the path-only series stay stored, no longer updated. The gap rule now compares each day with the median of the same weekday over the last 4 weeks.

## Narrative definitions v2 (16 Oct): GKG themes and title phrasings
Problem: on `gdeltbqt` 15 of 18 narratives stay under the 20-articles-a-day floor; the frozen phrases were written for full-text search and rarely appear in titles or URLs. Lowering the floor stays rejected (noise).

**Literature and docs (before measuring).**

| Finding | What it changes | Source |
|---|---|---|
| The GKG `Themes` field lists every theme GDELT's keyword tagger found anywhere in the article's full text (including machine-translated articles); themes come from GDELT's own taxonomy (ECON_, ENV_, NATURAL_DISASTER_, TAX_ lists) and the World Bank topical taxonomy (WB_). A theme marks a mention, not the article's main subject | A theme conjunction is the nearest thing the GKG has to the DOC full-text queries the narratives were frozen with (e.g. drought theme AND corn/wheat/soy theme ≈ the frozen crop-weather query). Single broad themes (ENV_OIL, ECON_INFLATION) are topics, not narratives: used only as one leg of a conjunction | [GKG 2.0 introduction](https://blog.gdeltproject.org/introducing-gkg-2-0-the-next-generation-of-the-gdelt-global-knowledge-graph/); [World Bank taxonomy in the GKG](https://blog.gdeltproject.org/world-bank-group-topical-taxonomy-now-in-gkg/); [GKG tutorial (keyword tagging, noise)](https://nbviewer.jupyter.org/github/dmasad/GDELT_Intro/tree/master/GKG%20Tutorial.ipynb) |
| GDELT's themes lookup (Nov 2021) lists every theme with its count; the `Themes` field is ~569 GB in total and `V2Themes` (with character offsets) ~1.2 TB | Definitions read `Themes` (V1, no offsets: about half the bytes); theme names are taken from the lookup and measured, never guessed | [Themes lookup](https://blog.gdeltproject.org/new-november-2021-gkg-2-0-themes-lookup/) ([file](https://data.gdeltproject.org/api/v2/guides/LOOKUP-GKGTHEMES.TXT)) |
| EPU: the policy term set was chosen from a 12,009-article human audit to minimise false positives plus false negatives; human and computer indices correlate 0.86–0.93 | Term choice is measured, not intuited: each candidate gets a random title sample read for precision, and the definition with the closest meaning that clears the floor wins; the 20–30 headline audit stays the validation step | [Baker, Bloom & Davis 2016](https://users.ssc.wisc.edu/~mchinn/bakerbloomdavis_QJE2016.pdf); [EPU methods review](https://arxiv.org/pdf/2308.10304) |
| BBD's term set is narrow: about one relevant article in ten is retrieved, and recall can rise a lot at little cost to precision (preliminary) | Recall, not only precision, matters: title-only phrasings are expected to be precise but sparse, so broader phrasings and theme conjunctions are measured side by side | [Brandt 2021 (DoCMA WP)](https://econpapers.repec.org/RePEc:zbw:docmaw:5) |
| GPR counts articles matching word groups by category (threats vs acts), as a share of all articles, from 10 newspapers | Keep one share-of-all measure per narrative; categories map to separate frozen definitions, never summed across instruments | [Caldara & Iacoviello](https://matteoiacoviello.com/gpr.htm) |
| GDELT's own EPU measure used keyword co-occurrence (economy terms twice plus uncertainty) on full text, normalised by total volume; GDELT notes false positives remain | The GKG's EPU_ themes (EPU_ECONOMY, EPU_POLICY_*, EPU_UNCERTAINTY, in the lookup) look like this term set as themes (inference: not documented) and give a cheap EPU replica for the later validation | [GDELT EU/EPU post](https://blog.gdeltproject.org/a-simple-narrative-measure-of-economic-uncertainty-and-economic-policy-uncertainty/) |
| Dictionary methods suit strong priors but must be validated by reading documents | Every v2 definition stays "unvalidated"; the measurement stores a reproducible random title sample per candidate | [Gentzkow, Kelly & Taddy](https://web.stanford.edu/%7Egentzkow/research/text-as-data.pdf) |

**Measured (16 Oct, two Actions runs, 25.4 GB in all; results in `docs/research/narrative-measure/2026-10-16-result.md` and `2026-10-16b-result.md`).** Windows 2–15 Oct and 15–28 Jun 2026; ~267k and ~299k web articles a day; each candidate with 12 randomly drawn distinct titles.
1. **Bytes per day by column** (dry run): Extras (title) 0.13 GB, Themes 0.15, V2Themes 0.33, Organizations 0.013, GCAM 2.66. A v2 series query (title, URL, tone, Themes) reads ~0.36 GB a day.
2. **Title phrasings are precise but some are thin.** E.g. OPEC in the title 19.7 a day; recession words 13.9–14.9; China stimulus words under 2.
3. **Single themes are topics, and noisy.** `ECON_NATGASPRICE` or LNG themes: 318 a day, but about a third of sampled titles are about gas; copper + shortage themes: 33 a day, mostly off-topic; the drought-and-crop theme conjunction: 107 a day, mostly off-topic. Themes are tagged on machine-translated articles too, so theme matches pull in non-English titles a reader cannot check.
4. **Hybrids work best:** the subject in the title, the narrative's angle from title words or a theme (Russia and oil in the title + SANCTIONS in the text: 224 and 65 a day, every sampled title on the diesel deal or sanctions).

**Decision (new instrument `gdeltbq2`, block `gdelt_bq_v2` in `config/sources.yaml`, first in `consensus.instruments`).** Per narrative, the definition with the closest meaning that clears 20 a day in both windows with on-topic samples; ids are new (`<narrative>_v2`, OPEC `_v3`); the frozen DOC queries and the `gdeltbqt` series are untouched.

| Narrative | Measured with | Articles a day (Oct / Jun) | Note |
|---|---|---:|---|
| Hormuz / Iran, US pump prices | frozen query on `gdeltbqt` (unchanged) | 66 / 604; 95 / 131 | already measurable |
| OPEC+ supply policy | `opec_supply_v3`: OPEC or oil output in the title | 30.5 / 26.1 | adds "oil output/production" phrases |
| Russian oil sanctions | `russia_oil_v2`: Russia + oil in the title, SANCTIONS theme | 224 / 65 | |
| Natural gas / LNG | `natgas_lng_v2`: gas/LNG title phrases | 96 / 120 | |
| Copper shortage / AI power demand | `copper_shortage_v2`: copper in the title | 56 / 50 | **broadened**: copper attention overall (shortage angle alone 7–8 a day) |
| Gold buying / reserves | `gold_buying_v2`: gold in the title + central bank/reserve themes or buying words | 43 / 68 | |
| Crop weather / drought | `crop_weather_v2`: crop in the title + weather in title or drought/heat/flood theme | 39 / 24 | broader than corn/soy/wheat; many Indian monsoon stories in October |
| Trade war / tariffs | `trade_war_v2`: tariffs or trade war in the title | 104 / 98 | frozen v1 fell to 17.3 in October |
| Fed hikes | `fed_hike_v2`: Fed + hike word in the title | 54 / 53 | |
| Inflation scare | `inflation_scare_v2`: inflation + rising/fear word in the title | 116 / 56 | |
| AI bubble | `ai_bubble_v2`: AI + bubble/selloff word in the title | 25 / 28 | near the floor on weekends (8 a day) |
| EPU replica (validation) | `epu_replica_v2`: GKG EPU themes | 1,563 / 2,025 | validation only |
| Oil glut, China stimulus, Fed cuts, recession, weak dollar, US fiscal | frozen query on `gdeltbqt` | best candidates 2 / 16, 22 / 9 (off-topic), 5 / 12, 15 / 12, 25 / 20 (half the titles are dollar *strength*), 39 / 10 | **stay "insufficient coverage"**: nothing cleared 20 in both windows with the meaning kept. Inference: in October 2026 (sampled headlines speak of an oil supply shock and Fed hikes) several of these are genuinely quiet; the floor cannot tell quiet from unmeasurable |

12 of 18 narratives now have a definition that clears the floor; stages appear once the v2 backfill (~160 GB, two runs) gives 240 days. Every v2 definition stays "unvalidated" until its 20–30 headline audit (`python -m pmstack narratives audit <narrative or query id>`).

**Live (daily run 38923131160, 16 Oct).** `fetch:gdelt_bq_v2` ok: 143.2 GB, backfill to 1 Aug 2025 done in one run (441 days), 356 headline rows; month 275.0 GB of the 800 GB cap. Today's pack: **10 of 18 narratives have a computed stage with headline links** (Hormuz, Russian oil sanctions, US pump prices, gas/LNG, copper, gold, crop weather, trade war, Fed hikes, inflation scare) plus the EPU replica (validation). OPEC (18.7 a day over 4 weeks) and AI bubble (16.3) read "insufficient coverage" although they cleared 20 in the measured windows. Over the 441 stored days their 4-week average cleared 20 on 86% and 52% of days; Fed hikes shows a stage now but was under 20 on 73% of days. So the floor hides quiet periods of a working definition (inference): the "quiet" label in the follow-ups is the fix to weigh, not a looser definition.
