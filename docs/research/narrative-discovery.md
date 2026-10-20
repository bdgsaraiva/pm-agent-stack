---
title: Narrative discovery and selection — literature review
agent: 7 (consensus and narrative monitor), two-step redesign
date: 2026-10-20
status: reviewed before build; code in pmstack/discovery.py + pmstack/adapters/gdelt_disc.py, parameters in config/discovery.yaml, skill in .claude/skills/narratives/
---

**Decided with Bernardo (20 Oct 2026).** Narratives become a two-step function: (1) discovery from the news with a low bar, where a theme with many sources on its first day is flagged; (2) selection in conversation with him, with price and positioning context beside each candidate. Answers: a day-1 theme reaches him in the next morning note (one daily query, no midday run); every candidate above the bar is shown, daily, grouped by market; a dismissal hides a candidate for 30 days or until it grows to 3x its size at dismissal, whichever comes first. Gold buying counts buying, reserves and flows, not daily price reports. Headline-audit splits: trade war #22 on topic; inflation #15, #18 and pump prices #12 not.

# Narrative discovery and selection — literature review
Draft, 20 Oct 2026. Scratch file (`.projtmp/`, untracked). It builds on `docs/research/consensus.md` (share of total, stages, the 20-a-day floor, the quiet rule, Kleinberg 2003, overdispersion, Bybee et al. 25%/17.8%, EPU/GPR, Tetlock, Da-Engelberg-Gao, McLean-Pontiff, Harvey-Liu-Zhu), on `docs/research/narrative-audit/README.md` (copper 4/25, OPEC+ 5/25, crop 11/25, gold 11-18/25), on `docs/research/research-loop.md` (agent 12 gate) and on `docs/project/notes-N1.md`. Those findings are not repeated here.

**Reading status.** "Read" means the full text was opened and the cited passage was checked. "Abstract" means only the abstract or a landing page was read. "Vendor page" means marketing copy, with no independent check.

**Bottom line.**
- **Separate the two jobs.** Discovery runs on a cheap daily aggregate with a deliberately low bar. Selection is a short human review with code-computed context. Tracking stays exactly as it is now: frozen, audited definitions with a 20-a-day floor.
- **Unit of discovery: English page-title n-grams**, counted once per source domain, with keyword pairs to group them. GKG themes and entities are only a secondary channel, because the audit showed theme matches are mostly mentions rather than subjects.
- **Score each unit against its own trailing baseline**, using the share of all titles with a noise floor. Raise a separate day-1 "new" flag when a unit that was near zero over the last 28 days appears from many independent domains.
- **Present price and CFTC context as co-movement only.** The best evidence for news attention is contemporaneous, and it is strongest for volatility. Any "does it predict" question goes to agent 12.

---

## a) Burst, emerging-topic and first-story detection

| Finding | What it changes | Source |
|---|---|---|
| Kleinberg's batched-arrival model: batch *t* has r_t relevant documents out of d_t; states emit binomially with p0 = R/D and p1 = s·p0; a burst's weight is the cost saved by being in the high state. Run on raw lower-cased paper **titles**, the top-weighted bursts were nearly all content words, not stop-words. | Title words, scored as a share of all titles, are a sound discovery unit. **Look-ahead trap:** p0 = R/D uses the whole sample. Online use must take p0 from a trailing window only. | [Kleinberg 2002/2003, §4](https://www.cs.cornell.edu/home/kleinber/bhs.pdf) (read) |
| SigniTrend scores sig = (x − max{EWMA, β}) / (√EWMVar + β), using frequencies normalised by the day's document count. EWMA/EWMVar are updated incrementally, with a half-life setting the learning rate. The bias β is set to the background noise level ("10 occurrences by chance" for Twitter) and acts as a noise filter for rare terms. Word **pairs** catch topics whose words are not individually popular. Updates should follow the source's natural cycle (daily for news). | This is the scoring rule: share-normalised EWMA z with a noise floor β, plus word pairs. β turns "low bar" into one explicit parameter. Update once per complete day. | [Weiler dissertation, ch. 5–6 (SigniTrend, KDD 2014)](https://edoc.ub.uni-muenchen.de/20370/2/Weiler_Michael.pdf) (read) |
| SigniTrend's authors say the z is a heuristic, not a hypothesis test. With thousands of terms watched, the three-sigma rule does not hold, but they want "multiple events every day". Estimating x on an incomplete epoch is hard because the day's total is unknown. On 2013 Reuters/Bloomberg news, the top trend of the year was a **Reuters artifact** (233 research-alert boilerplate items). Finance and sports dominated the rest. | False-alarm control is by ranking plus a daily budget, not by p-values. Cap each domain at one count per unit per day, and suppress boilerplate. A same-day flag on a partial day needs a projected day total (see open question 1). | same (read) |
| A Poisson "last count" background is very noisy: for a big spike almost any threshold gives many false positives. An averaged background is better. A template model ("looks like known trending series") is the most robust but lags. | Never compare with yesterday alone. Use a trailing multi-week, weekday-adjusted baseline. | [Twitter/Gnip trend-detection repo](https://github.com/twitterdev/Gnip-Trend-Detection) (read README) |
| Streaming first-story detection: novelty is 1 − cosine to the nearest earlier document (LSH, with a fallback to recent documents). Output ranked by thread size or by **unique users** beat random only slightly (events-vs-rest average precision 24.1 and 24.5 vs 16.5). Moving low-entropy threads (spam) to the back raised it to **34.0**. Inter-annotator kappa was 0.65. | Rank by **distinct sources**, not raw copies. Demote low-diversity clusters (one wire's boilerplate, junior-miner press releases). Expect modest precision: most of what is shown will be dismissed. | [Petrović, Osborne & Lavrenko 2010](https://aclanthology.org/N10-1021.pdf) (read) |
| UMass TDT-3: the best first-story detection normalised cost was 0.81, against 0.14 for link detection. "Any first story detection system based on a tracking approach is unlikely to be sufficiently accurate." | Per-article novelty detection is not worth building here. Detect bursts of aggregate counts per unit instead, as EMM and GPHIN do. | [Allan et al., UMass at TDT-3](https://ciir-publications.cs.umass.edu/pub/web/getpdf.php?id=201) (read) |
| EMM NewsBrief/MedISys: articles are clustered every 10 minutes over a 4-hour window. A cluster is "breaking" when it is a large **new** cluster with no overlap with earlier ones, or when it is rising fast, using **article counts and the number of different sources**. A new cluster overlapping an old one by at least 10% of articles is linked to it. MedISys alerts compare each category × country count over 24 hours with its **14-day average, normalised by weekday**, ranked by that ratio. A threat drops off the top list after a few days of coverage. | Two flags: "new" (large, no overlap with tracked or earlier candidates) and "rising" (ratio against a weekday-adjusted trailing average). Link a candidate to an existing narrative at ≥10% title overlap. Novelty decays: a candidate leaves the list after a few days unless it grows. | [Steinberger et al. 2009, EMM](https://arxiv.org/pdf/1309.5290) (read); [Steinberger et al. 2015](https://arxiv.org/pdf/1603.02604) (read) |
| GPHIN deduplicates with word-triplet overlap plus shingling (MinHash). Duplicates are clustered and flagged, not deleted, and the first version is the exemplar. This exists "to avoid duplicate stories hijacking trend detection". | Count each normalised title once and each domain once. Keep the copy count only as a prominence ranking (as the headlines already do). Use the earliest copy as the exemplar link. | [Carter et al. 2020, GPHIN redesign](https://arxiv.org/pdf/2004.04596) (read) |
| GPHIN narrative discovery: each day it looks for **statistically unusual pairs of non-generic keywords plus locations**, giving **20–50 new narratives a day out of up to 10,000 articles**, "small enough for an analyst to digest". Topic models are used only to detect change points inside narratives already found. | Pairs (keyword+keyword or keyword+entity) are the practical discovery unit. A daily budget of a few dozen is what a dedicated team handles, so one PM needs a far smaller budget (5–12). Topic models are not needed for discovery. | same (read) |

## b) Unit of discovery on the GDELT GKG; pitfalls; cost

| Finding | What it changes | Source |
|---|---|---|
| GDELT's own Live Trends breaks articles into themes and compares the density of every **location × theme** pair over the last 45 minutes with the previous 45 minutes and 6 hours. It ranks pairs for burst, breakout, trending or stabilising behaviour and shows the top 60. Caveat: a "narrative" can be one big story or several unrelated small ones lifting the same theme. A plateaued big story drops out. | Theme × entity pairs are GDELT's own trend unit. Their weakness is the same one our audit found: unrelated stories share a theme. Use them only as a secondary channel, always shown with titles. | [GDELT Live Trends Dashboard](https://blog.gdeltproject.org/announcing-the-gdelt-live-trends-dashboard/) (read) |
| GKG fields. **GKGRECORDID** carries a capital "T" after the dash for machine-translated documents, so English and non-English can be split on the record id alone. **V1Themes** lists themes found anywhere in the document; V2EnhancedThemes adds offsets. **V2.1AllNames** holds all proper names, including named events and laws, and is "maximally inclusive". **TranslationInfo** gives the source language. | Discovery v1 counts **English titles only** (`GKGRECORDID NOT LIKE '%-T%'`), with an English-only denominator. Use Themes (V1), never V2Themes: offsets are not needed and cost twice as much. AllNames is a candidate for a later entity channel (bytes to be dry-run). | [GKG 2.1 codebook](http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf) (read) |
| Bytes per day by column (our dry run, 20 Oct): DocumentIdentifier 0.031 GB, SourceCollectionIdentifier 0.002, Extras (title) 0.132, Themes 0.153, **V2Themes 0.333**, Organizations 0.013, V2Organizations 0.021, Locations 0.037, GCAM 2.66. | A titles-plus-domain query is about 0.17 GB a day. Adding Themes and Organizations for the secondary channel brings it to about 0.35 GB a day (~11 GB a month). A 90-day baseline backfill is about 32 GB once. The month stood at 289 GB of the 800 GB cap on 20 Oct. | `docs/research/narrative-measure/2026-10-20-result.md` (ours) |
| Web News NGrams 3.0 (BigQuery `gdeltv2.webngrams`): unigrams with context from article **body** text in 152 languages, with a decile position. Titles are not included. It has an elevated number of duplicate records, and one example query used 19 TB. | Not a discovery source for us: body text, too costly, and no titles. Title n-grams come from GKG `Extras`. | [GDELT NGrams 3.0 announcement](https://blog.gdeltproject.org/announcing-the-new-web-news-ngrams-3-0-dataset/) (read); [historical search post](https://blog.gdeltproject.org/?p=15175) (abstract) |
| Sparse vs dense representations for news stream clustering: TF-IDF on **title + content** scored BCubed F1 94.4; doc2vec scored 90.0 and over-split stories (785 clusters vs 222 true); combining the two did not beat TF-IDF. | Group a day's flagged titles with TF-IDF cosine. Embeddings are not needed for v1. | [Staykovski et al. 2019](https://ceur-ws.org/Vol-2342/paper6.pdf) (read) |
| An entity-aware fine-tuned BERT plus TF-IDF and time improves stream clustering by about 3 points over the same model without entities. Timestamps keep separate events from merging. | Later upgrade, if TF-IDF clusters merge unrelated stories: add entity tokens (Organizations/Persons) and a time window. | [Saravanakumar et al. 2021](https://arxiv.org/pdf/2101.11059) (read) |
| GDELT quality. US and Western media are over-represented. In one 10-day comparison, GDELT and Event Registry had no overlap in their top 10 sources. Collection methods "might change". The Event table has ~55% accuracy on key fields and up to 20% redundancy. | Score each unit against its own history, as a share of the English total, and watch the domain mix: show the candidate's domain count and its press-release share. Treat any change in GDELT's method (like the Oct 2026 DOC collapse) as a gap, not a burst. | [ONS GDELT quality note](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/deaths/methodologies/globaldatabaseofeventslanguageandtonegdeltdataqualitynote) (read); [Hong et al. 2025, *Data*](https://ideas.repec.org/a/gam/jdataj/v10y2025i10p158-d1762908.html) (abstract) |
| Our own GKG facts (notes-N1, consensus.md). There is no ingest collapse in the GKG (~300k web articles a weekday). Weekends run about 0.55× a weekday. The DOC API collapsed after 1 Oct 2026 and refuses GitHub runners. Themes are tagged on machine-translated text. The copper audit was dominated by junior-miner press releases. | Use a weekday-adjusted baseline. GKG on BigQuery is the source, never DOC. Exclude translated records. Keep a press-release domain list (globenewswire, prnewswire, newsfile, accesswire, businesswire): such domains count but are flagged, and a candidate carried mostly by them is demoted. | `docs/project/notes-N1.md`; audit README |

## c) Narrative and finance evidence: attention vs prices and positioning

| Finding | What it changes | Source |
|---|---|---|
| Bybee, Kelly, Manela & Xiu, beyond the 25% R² already cited. Returns are regressed on **AR(1) innovations** in topic attention, not levels. The authors call the correlations "not causal narratives". "Oil market" attention tracks crude oil volatility, and "recession" attention predicts output and employment in a VAR. **Narrative retrieval:** the model flags the articles behind a move for a human to read. | Context compares the **surprise** in attention (today vs its own baseline) with the price move, not the level. The review screen is a narrative-retrieval device: headlines behind a burst sit next to the move, and the human interprets. | [Bybee et al., NBER w29344](https://www.nber.org/system/files/working_papers/w29344/w29344.pdf) (read) |
| NVIX (WSJ front page, 1890–2009): out-of-sample fit to VIX R² 0.34. 1 sd of NVIX raises annualised excess returns by 4 pp over 3 months. War and government-policy concerns explain 53% and 22% of risk-premium variation. **Look-ahead footnote:** the text weights were trained on data that came after the prediction sample. | Slow-moving concern measures can predict over months. Weights fitted on later data are a look-ahead risk: a promoted definition is frozen at promotion and never re-fitted backward. | [Manela & Moreira 2013 (JFE 2017)](https://www.aeaweb.org/conference/2014/retrieve.php?pdfid=452) (read) |
| Hedging climate news: innovations are AR(1) residuals of a WSJ climate-news index. Mimicking portfolios reach out-of-sample correlations with those innovations of up to 30% (monthly). | Even a well-built news series co-moves with prices only modestly. Show co-movement as a correlation with a range, never as a "driver" claim. | [Engle et al., NBER w25734](https://www.nber.org/system/files/working_papers/w25734/w25734.pdf) (read) |
| Crude oil with RavenPack, keeping only relevance = 100 and novelty = 100 (the **first story** of an event). Geopolitical news has a strong immediate impact but no predictability. Macro news predicts oil monthly: 1 sd of GDP-growth news gives +2.90 pp the next month, t = 2.26. Daily adjusted R² is only 6.66%. Event-day overreaction to unrest and disaster news reverses on days 4–5. | Most commodity narratives in our list (Hormuz, sanctions) are the geopolitical kind: expect contemporaneous co-movement and reversal, not drift. Show the move on the burst day **and** the days after, so the PM sees reversals. | [Brandt & Gao (WP 2016; JEF 2019)](https://conference.nber.org/conf_papers/f89483/f89483.pdf) (read) |
| Bloomberg News Trends counts (crude, OPEC, metals, grains…) help predict oil futures returns, mainly in downturns. Accuracy falls with maturity, and the choice of variable-selection method changes results materially. | Weak, regime-dependent, specification-sensitive evidence. Nothing in the review screen implies a forecast. (Bloomberg-derived data is never brought into the repo anyway.) | [Cepni, Nguyen & Şensoy 2022](https://repository.bilkent.edu.tr/items/ea02c6cb-d622-4edb-b17e-505e38b6e7a8/full) (read) |
| Google search attention improves commodity **volatility** forecasts in and out of sample in energy, metals and agriculture. | Attention relates more reliably to volatility than to direction. Context shows the change in realised volatility around the burst next to the return. | [Basistha, Kurov & Wolfe 2015](https://farmdoc.illinois.edu/assets/meetings/nccc134/conf_2015/pdf/Basistha_Kurov_Wolfe_NCCC_134_2015.pdf) (read, preliminary) |
| Bloomberg reading/search attention (institutional) reacts faster than Google (retail), leads to permanent rather than temporary price adjustment, and drifts occur where institutions do not pay attention. | GDELT measures the *supply* of news, not institutional reading. The screen says "news volume", never "investor attention". | [Ben-Rephael, Da & Israelsen (WP 2016; RFS 2017)](https://www.abfer.org/media/abfer-events-2016/annual-conference/investment-finance/153-it-depends-on-where-you-search-a-comparison-of-institutional-and-retail-attention.pdf) (read) |
| **Gap: no study was found that links news attention to CFTC managed-money positioning.** Searches covered COT + media/news/sentiment and managed money + news. The positioning literature already in consensus.md says positions follow price (Sanders et al.; Fishe & Smith). | CFTC context is descriptive: MM net and its 3-year percentile at the last report released before the burst vs the latest report. No claim that narratives move positions. It also carries the caveat that disaggregated COT covers only our 10 commodity markets. Rates, USD and equity futures would need the TFF report, which is not built. | searches logged in this session; consensus.md |

## d) Human-in-the-loop triage

| Finding | What it changes | Source |
|---|---|---|
| GPHIN relevance scoring: high scores publish automatically, **low scores are suppressed automatically, and only the middle band is triaged by analysts**. A hand-curated blacklist of common false-positive terms is applied. Analyst feedback periodically retrains the scorer. | Three bands: (1) above the bar and touching focus markets → shown; (2) above the bar but outside focus, or low-diversity → a collapsed "also rising" line; (3) below → logged only. A dismissed list of terms and clusters acts as the blacklist. | [Carter et al. 2020](https://arxiv.org/pdf/2004.04596) (read) |
| Nigeria event-based surveillance: of 43,631 raw signals, **138 (0.3%) were escalated and 63 (46%) of those verified**. Linked signals on the same subject within 2 days were clustered as one. | A steep funnel is normal. Measure the funnel (flagged → shown → watched → promoted). Cluster repeats within a short window so one story is one candidate. | [Beebeejaun et al. 2021, *EID* 27(3)](https://wwwnc.cdc.gov/eid/article/27/3/pdfs/20-0141.pdf) (read) |
| EMM's lesson: machines make mistakes humans spot at once (a song about "tuberculosis"). Users must be able to drill down to the original articles and see enough cases to judge confidence. NewsDesk is a moderation tool for selecting and editing machine output. | Each candidate shows its titles with links and a small **random** sample of titles (not only the top-carried ones), so precision can be judged at a glance, the same lesson as the headline audit. | [Steinberger et al. 2015](https://arxiv.org/pdf/1603.02604) (read) |
| Active learning caveat: labels gathered by a model's own queries are a **biased sample**, not i.i.d. Off-the-shelf batch query strategies can do worse than random. The practical stopping rule is economic, not statistical. | Dismissals and promotions are not a training set for estimating misses. Add a small weekly **random audit slice** from below the bar to estimate what the bar misses. Don't build a learner until there are a few hundred decisions. | [Settles 2009, TR 1648](https://khoury.northeastern.edu/home/vip/teach/MLcourse/4_boosting/materials/settles.activelearning.pdf) (read) |
| Petrović et al. evaluate a ranked alert list by average precision against human labels. TDT uses a detection cost that weights misses vs false alarms. | Score the review itself: precision@K (share of shown candidates watched or promoted), days from first flag to promotion, and misses found by the audit slice. Report these monthly in the Friday review. | [Petrović et al. 2010](https://aclanthology.org/N10-1021.pdf) (read) |

## e) Vendors: build vs buy

| Vendor | What it does (as read) | Note | Source |
|---|---|---|---|
| Bloomberg News Trends / MRN | Companies and topics with the most media and reader attention; "news heat" (most written about) and readership from 30,000+ sources; alerts on breaking stories. | Readership is the institutional-attention measure GDELT lacks. Licence: never into this repo. It could serve Bernardo's own eyeball check at work. | [Bloomberg News](https://professional.bloomberg.com/products/bloomberg-terminal/news/) (vendor page); [Global Custodian 2010](https://www.globalcustodian.com/bloomberg-adds-unique-offerings-to-machine-readable-news/) (read) |
| RavenPack | Entity/event taxonomy (6,895 event types in RPA 1.0), event similarity analytics over 365 days, relevance and novelty scores. Novelty 100 = first story of an event. 25,000+ sources, point-in-time. | The novelty score is the deduplicated first-story flag we build cheaply with title hashing. For a corporate build. | [RavenPack on WRDS](https://wrds-www.wharton.upenn.edu/documents/1395/RavenPack.pdf) (vendor page); Brandt & Gao (read) |
| AlphaSense | Smart Topics / trending topics across transcripts and documents for watchlists or industries; Smart Synonyms query expansion. | Strong on corporate documents; not a news-burst detector. The help centre is behind a login, so only the abstract was read. Corporate vendor review (consensus.md). | [Smart Synonyms](https://www.alpha-sense.com/blog/product/alphasense-smart-synonyms) (vendor page) |
| Permutable AI | Narrative and sentiment intelligence for oil, gas, LNG, metals and agriculture; claims to detect when narratives move beyond headline noise; API, Excel, alerts. **No validation figures published.** | Closest in purpose. An unvalidated black box can't pass agent 12's gate. Demo only. | [Permutable, energy & commodities](https://permutable.ai/energy-and-commodity-traders/) (vendor page) |
| Accern | No-code NLP themes and sentiment from news and filings; **acquired by Wand AI, Feb 2025**. | Vendor risk is real: drop it. | [IDP Software profile](https://idp-software.com/vendors/accern/) (read) |
| GDELT | Free and open. Live Trends (theme × location, 45-minute windows); GKG on BigQuery; NGrams 3.0. | What we already pay nothing for. Its trend dashboards are not point-in-time or stored, so we compute our own. | [GDELT data](https://www.gdeltproject.org/data.html) (read) |

**Build vs buy (inference).** Build discovery on the GKG: about 11 GB a month, licensed with citation, stored point-in-time and testable by agent 12. What is personal and can't be bought is the *selection* against Bernardo's ideas, journal and markets. Vendors' discovery is better (premium sources, entity resolution, readership), but none publishes validation, and Bloomberg/RavenPack data can't enter this repo. If the corporate build licenses RavenPack or Bloomberg, swap the adapter; the review flow and tracker stay the same.

---

## Where sources disagree

1. **Is a per-story first-story flag worth it?** UMass TDT says FSD built on tracking is "unlikely to be sufficiently accurate" (cost 0.81). Petrović makes it fast but event precision stays low (AP 34). RavenPack sells novelty flags. → We don't detect first stories. We flag **first days of a burst** in aggregate counts. The earliest deduplicated title is shown as the exemplar.
2. **The right null for counts.** Twitter's open-source Gnip detector offers a Poisson background. Our data and Grasland et al. show strong overdispersion. SigniTrend uses EWMA mean and variance with a noise floor and says it is not a test. Kleinberg uses a cost-based automaton. → Use the SigniTrend form: it is empirical about variance and has an explicit floor. Kleinberg's two-state weight is only a persistence check over days 2–5.
3. **Themes vs words.** GDELT Live Trends and GPHIN discover on theme/keyword × location pairs. Kleinberg and SigniTrend use words and word pairs. Our audit found theme matches mostly off-topic, because a theme marks a mention. → Titles first; themes and entities only as a corroborating channel.
4. **Topic models.** Bybee et al. build on an LDA with 180 topics and get stable economic results. Gentzkow et al. (already cited) warn that topic models are unstable. GPHIN uses them only inside known narratives. → No topic model for discovery. TF-IDF clustering groups titles for display.
5. **Dense vs sparse.** TF-IDF beat doc2vec (Staykovski). Entity-aware BERT added about 3 points (Saravanakumar). → Sparse first; embeddings only if merges or splits become a review problem.
6. **Contemporaneous vs predictive.** Attention explains same-period returns (Bybee) and volatility (Basistha et al.). NVIX and macro news (Brandt & Gao) predict over months. Geopolitical news (Brandt & Gao) and tone (Tetlock) reverse within a week. Cepni et al.'s oil result depends on the specification. → The screen shows **co-movement**: burst day and window around it, against a base rate. It never shows a forecast, and any predictive claim goes through agent 12.
7. **Whose attention.** Bloomberg readership (institutional) leads and moves prices permanently. Google (retail) gives temporary pressure. GDELT is the supply of news. → Label it "news volume"; don't import attention-paper effect sizes.

---

## Design proposal

### 1. Unit of discovery
- **Primary unit:** title terms. These are unigrams and bigrams from English page titles (`Extras` `<PAGE_TITLE>`, records whose `GKGRECORDID` has no "-T").
  - Text is lower-cased and stop-words are removed.
  - The site-name suffix after the last " - " or " | " is cut.
  - Pure numbers and dates are dropped.
  - Each term is counted as **distinct source domains per day** (`SourceCommonName`). A domain counts at most once per term per day.
- **Pairs:** for terms that pass a pre-screen, the pairs of them that co-occur in at least 3 titles (SigniTrend; GPHIN keyword pairs). Pairs catch "Rio Tinto + Mongolia" when neither word is unusual alone.
- **Secondary channel** (corroboration, never shown alone): `Themes` × top `Organizations` pairs, counted in SQL and aggregated (GDELT Live Trends; GPHIN). A candidate gets a "themes agree" tag when its titles' records share a rising theme.
- **Clustering for display:** flagged terms and pairs are grouped into **candidates**. Two terms join when they share ≥ 30% of their titles (Jaccard). Then the day's titles inside a candidate are grouped by TF-IDF cosine (Staykovski) to pick the medoid title as its name (EMM). A candidate is a set of terms, a set of titles and a label written from its titles (the model only words it; code picks it, as in the critic).

### 2. Daily query and cost (BigQuery, one partition)
```sql
-- A: titles (English, web), returned row-level for local n-gram counting  (~0.17 GB billed; dry-run the two id columns)
SELECT SourceCommonName AS domain, DocumentIdentifier AS url,
       REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>') AS title
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME = TIMESTAMP(@day) AND SourceCollectionIdentifier = 1
  AND NOT REGEXP_CONTAINS(GKGRECORDID, r'-T');
-- B: theme x organisation pairs, aggregated in SQL (~0.17 GB billed); only pairs with >= 3 domains returned
SELECT theme, org, COUNT(DISTINCT SourceCommonName) AS domains
FROM `gdelt-bq.gdeltv2.gkg_partitioned`,
     UNNEST(SPLIT(Themes, ';')) AS theme,
     UNNEST(SPLIT(LOWER(Organizations), ';')) AS org   -- sketch; normalise as in gdelt_bq.py
WHERE _PARTITIONTIME = TIMESTAMP(@day) AND SourceCollectionIdentifier = 1 AND NOT REGEXP_CONTAINS(GKGRECORDID, r'-T')
  AND theme != '' AND org != ''
GROUP BY 1, 2 HAVING domains >= 3;
```
- **Cost.** About 0.35 GB a day (≈ 11 GB a month) on the measured columns. `GKGRECORDID` and `SourceCommonName` are not measured yet: dry-run them first. A 90-day baseline backfill is about 32 GB once.
- **Same rails as `gdelt_bq.py`:** dry run, `maximum_bytes_billed`, ledger and caps.
- **Avoid:** V2Themes (0.33 GB alone), GCAM (2.66), NGrams 3.0 (TB-scale).
- **Storage.** Counting runs locally on ~150–250k English titles. Only a compact daily aggregate is stored: term or pair → domains, distinct titles, total copies, for terms with ≥ 2 domains, at `data/obs/gdelt_disc/<year>.parquet`. Titles are stored only for flagged candidates in the headline table. Baselines then read local history, never BigQuery again.
- **Point in time.** Each day's candidate list is written once to `data/narratives/candidates/<date>.json` and never rewritten. A late GKG file revises counts but not past lists.

### 3. Scoring with a low bar, and the day-1 flag
- **Share.** For each unit: x_t = domains_t / N_t, where N_t is all English web domain-title pairs that day. Baseline = EWMA and EWMVar of x over valid days, half-life 14 days, weekday-adjusted by dividing by the unit-free weekday factor of N (EMM; notes-N1 weekend ratio 0.55).
- **Score.** s = (x − max(EWMA, β)) / (√EWMVar + β), with β equal to **3 domains** expressed as a share of N_t (SigniTrend's bias term: "noise level").
- **Two flags, both cheap:**
  - **Rising:** s ≥ 4 and domains_t ≥ 5.
  - **New (day-1):** the unit had ≤ 2 domains on every valid day of the trailing 28, and today ≥ **8 distinct domains** (EMM: a large new cluster with no overlap; Petrović: rank by unique sources). This fires on the **first complete day** a theme appears with many articles.
- **Low bar by design.**
  - These thresholds are far below the 20-a-day tracking floor. Discovery only nominates; it never stages.
  - All thresholds sit in `config/monitor.yaml` (`discovery:`), each with a version id. A change gets a new id, and the old candidate lists keep theirs.
- **Demotions:**
  - **Diversity:** fewer than 3 domains carry ≥ 60% of copies, or the press-release-domain share is ≥ 50% (copper lesson).
  - **Low entropy:** fewer than 3 distinct normalised titles (one wire item; SigniTrend's Reuters artifact; Petrović's spam).
  - **Calendar boilerplate:** recurring scheduled terms ("WASDE", "payrolls" on release days) are tagged "scheduled". They stay visible but rank below unscheduled ones.
- **False-alarm control:**
  - No p-values. Rank by s and show a fixed **daily budget K** (open question 2).
  - **Placebo, once at build:** run the scorer over the stored 441 days and report candidates per day, median and 90th percentile, to set K honestly.
  - **Persistence tag:** a candidate that stays above its baseline on days 2–5 gets "sustained" (Kleinberg two-state weight > 0 over the run), separate from one-day spikes.
- **Same-day option.** An extra run on the partial UTC day compares counts so far with the same hours of the trailing weekdays. This is SigniTrend's incomplete-epoch problem. Projected day totals are noisier, so only "new" flags with ≥ 8 domains so far are shown.

### 4. Deduplication
- **Normalised title.** Lower-case, strip punctuation, drop the site suffix, collapse whitespace, then hash. The **earliest** copy by `DATE` is the exemplar (GPHIN).
- **Units count distinct domains**, not copies. Copies are kept only for the prominence ranking of headlines (as now).
- **MinHash 3-shingles over titles** (GPHIN shingling) merge near-identical rewrites ("Oil jumps as…" / "Oil prices jump as…") when Jaccard ≥ 0.6. Titles are short, so this is cheap locally.
- **Candidate-level linking.** A new candidate whose titles overlap ≥ 10% with yesterday's candidate (EMM), or which matches a tracked narrative's frozen query on ≥ 30% of its titles, is an **update** to that item, not new. It shows as "tracked narrative X: rising".

### 5. Relevance filter to the focus markets
- **Lexicon map.** `config/discovery.yaml` holds a hand-written lexicon map, market id → terms (e.g. `CL=F`: crude, oil, brent, wti, opec, refinery, barrels; `ZC=F`: corn, maize, ethanol; Fed/UST: fed, fomc, powell, treasury, yields, auction; USD: dollar, dxy, yen, yuan…). It covers every market in `config/sources.yaml`'s CFTC and price lists, plus US equity sector and index terms.
- **Matching.** A candidate touches a market when ≥ 20% of its titles match the market's lexicon or a theme from the market's theme list (ECON_*, ENV_OIL…).
- **Not filtered out (low bar).** Candidates touching no focus market go to the collapsed "outside focus" line. They are dropped only if the dismissed list matches.
- **Ranking.** Within the budget: day-1 flags touching a focus market first, then by s. Bernardo's open journal ideas' markets break ties.

### 6. Context shown for selection (code-computed, point in time, all descriptive)
For each candidate, with t0 = its first flagged day and "as of" = the pack date:

| Block | Content | Rule |
|---|---|---|
| Attention | domains today, share, s, first flag day, 60-day sparkline of domains, "new"/"rising"/"sustained", languages excluded, press-release share | from the discovery store; nothing after as-of |
| Headlines | 5 most-carried distinct titles with links + 5 **random** distinct titles from the candidate | EMM drill-down; the random five show precision honestly |
| Markets touched | each matched market, with the share of titles that matched | lexicon map; Bernardo can edit the mapping in review |
| Price | close-to-close return on t0, over t0−5→t0−1 (before) and t0→as-of (since), in units of 60-day EWMA vol (as risk.py); change in 20-day realised vol since t0; **base rate**: the share of all days in the last 3 years with a vol-scaled move at least this large | Bybee: innovations; Basistha et al.: vol; a 1.5-sd day is common, and the base rate says so |
| Positioning | CFTC managed-money net (% of OI) and its 3-year percentile from the last report **released** before t0 (Friday rule, `cftc_release_lag_days`) vs the latest released report; "no report since t0" when none; trend proxy vote (`consensus.trend`) | descriptive; caption "positions follow price; MM ≠ CTAs"; rates/USD/equities: "no CFTC (TFF not built)" |
| Ideas | open journal ideas in the touched markets, with side | journal only (paper ideas) |
| Caption | "Co-movement on the burst days, not a cause or forecast. N candidates shown today; with this many, some large moves line up by chance." | multiple-testing honesty (Harvey et al.; agent 12) |

The model words the candidate's label and one sentence summarising its headlines. **Every number comes from code** (CLAUDE.md), and the model never sees prices before writing the label (research-loop memorisation rule).

### 7. Review conversation (selection with Bernardo)
1. **Surface.** The fact pack carries `discovery` (candidates, K shown + "also rising" count). The morning note mentions at most the **day-1 flags touching a focus market** (one line each, with ≤ 2 headline links). The full list is on request.
2. **Review.** `/narratives review` (or the Friday skill step) shows the candidates one block each. Bernardo answers per candidate:
   - **Promote:** "track it".
   - **Watch N days:** default 14. It re-shows only if it grows (domains ≥ 2× the level at the watch decision) or becomes sustained.
   - **Dismiss**, with a reason code: `noise` (false match), `not-market` (real but irrelevant), `duplicate-of:<id>`, `known` (already in his head; still logged).
   - He can also edit the markets touched.
3. **Memory.** Every decision is appended to `data/narratives/decisions.jsonl`: date, candidate id, terms, features at decision time, reason, markets.
   - Dismissed term sets suppress matching candidates (≥ 50% term overlap) for the suppression period (open question 3), unless they grow past the re-surface rule.
   - `noise` dismissals feed a term blacklist (GPHIN), applied before scoring. Each entry has a date, so its effect is auditable.
4. **Audit slice.** Each Friday, 3 random candidates from just below the bar are shown with "would you have wanted this?" This estimates misses without the active-learning bias (Settles).
5. **Scorekeeping** (monthly, in the review): precision@K, the funnel (flagged → shown → watched → promoted), median days from first flag to promotion, misses from the audit slice. Thresholds change only by config version, after a month's data.

### 8. Promotion to a frozen definition and audit
1. **Draft.** Code drafts a title-phrase query from the candidate's top terms and pairs, with the press-release exclusions used in round 3 (e.g. `(rio tinto OR oyu tolgoi) (mongolia OR ...)`). Bernardo edits the meaning line.
2. **Measure.** `narratives measure` runs with the candidate in a spec: two windows (the burst window and a quiet window), articles a day, 25 random titles.
3. **Audit.** The 25-title headline audit uses two blind labellers plus Bernardo on disagreements (same protocol as 20 Oct). Freeze only at ≥ 70% precision (Wilson lower bound reported). Otherwise narrow and re-measure, or keep it as "watched". Every attempt is recorded as a trial.
4. **Freeze.** The definition gets id `<name>_v1` in `gdelt_bq_v2.queries` with `narrative:`, the markets it pushes and which way, and `discovered_on: t0` and `promoted_on`. It joins `consensus.instruments` and the tracker, with its first record starting at the promotion date. **No backward re-fitting** (NVIX footnote): history before promotion is computed with the frozen query and marked "pre-discovery".
5. **Floor.** The usual 20-a-day floor and quiet rule apply. A narrow promoted theme can sit "quiet" or "insufficient coverage", which is honest.
6. **Agent 12.** Any claim that discovered narratives "lead" prices is registered as a study. The family includes every candidate ever shown (the decisions log is the trial count), and the narrative stage test on future moves only applies.

---

## Open questions for Bernardo

**1. When must a day-1 theme reach you?**
- (a) In the 06:18 BRT note the morning after its first full UTC day (cheapest: one daily query, ~0.35 GB).
- (b) As (a), plus a midday run (about 13:00 BRT) on the partial day, showing only "new" flags with ≥ 8 domains so far that touch a focus market (+~0.2 GB a run, noisier).
- (c) As (b), but the midday run posts every new flag, not only focus-market ones.

**2. How many candidates do you want to see, and where?**
- (a) Top 5 a day in the fact pack; the note mentions only day-1 flags in focus markets; the full review on Fridays.
- (b) Top 10 a day plus a collapsed "outside focus" count; review whenever you ask (`/narratives review`).
- (c) Every candidate above the bar, grouped by market, reviewed daily.

**3. How long should a dismissal suppress a candidate?**
- (a) 30 days, then it may reappear.
- (b) Until it grows to ≥ 3× its level at dismissal (no time limit).
- (c) Both: whichever comes first (30 days or ≥ 3× growth).
- (d) Permanently, unless you lift it by hand.
