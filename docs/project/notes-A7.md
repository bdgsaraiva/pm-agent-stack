# Session notes A7: consensus & narrative monitor (agent 7), 10 Oct 2026

Literature review (Docs): https://claude.ai/code/artifact/40d845c6-a148-4504-9a03-f33b90072127 · repo: `docs/research/consensus.md`
Commits: 5c3dd3f (v1), a8906d1 (review fixes), 9e64e4a (live-run fixes). Tests: 71 pass (~5 min).

## Context
- Built before the 1 Nov gate (0 of 10 paper ideas) because Bernardo asked to "go ahead with the next agent". He is back from vacation Tuesday to log ideas; ideas logged here are paper ideas.
- He declined the GDELT research sub-agent by accident, then said: try GDELT; his consolidated trend-podcast knowledge will come later as an upgrade.
- This session can't see his separate podcast-learning project. The upgrade goes in `notes/podcasts/top-traders-unplugged/` when he shares it.
- His answers to the 3 questions: 18 commodity-first + macro narratives; full map daily in the fact pack, the note showing changes only, and the critic card carrying crowd facts; GPR/EPU validation later.

## What the evidence said (short)
- Attention measured as a share of all coverage is a real state variable (Bybee et al.; EPU/GPR method).
- Tone effects are small and reverse within days (Tetlock; Garcia). General dictionaries misread "crude" (Loughran & McDonald).
- Trend sign and CFTC managed money mostly restate price, so they are shown side by side, not as two votes (Moskowitz et al.; Fishe & Smith). Extremes are not contrarian (Sanders et al.: 5 of 30 tests).
- Result: describe, don't trade. Every score is stored for the quant gate.

## What shipped
**GDELT adapter** (`pmstack/adapters/gdelt.py`): 19 frozen queries (18 + EPU-style validation). Per query and day it stores count, share (count/norm) and tone, plus `gdelt:norm`.
- Runs only in Actions.
- 12-minute budget; 30/60 s backoff on refused calls; stops after 3 failing calls in a row.
- Missing series are fetched first, and each series restarts from its own last day.

**`pmstack/consensus.py`**
- Narrative stages: windows end on the last *valid* day (gap days dropped); "stale" when that day is over 4 days old; mid-rank percentile.
- Trend vote of the 1/3/12-month legs; the score is display only.
- CFTC percentile with an agreement flag.
- Labels and idea placement (inference).
- Fed wording counts.
- `narrative_spreading` alert vs the previous pack.

**Fact pack:** "Consensus map" section in facts.md. Rebuilt packs keep alert refs stable (closes the 9 Oct follow-up); alerts that no longer fire stay listed but are never treated as live.

**Critic card:** `map.trend_score`, `map.label`, narratives with or against the idea; contradiction basis "narrative".

**Auditor:** a narrative figure binds only to words unique to its name.

**Morning note:** the crowd check covers stage changes vs the previous pack and idea placement only.

## Independent review: 8 defects, all fixed
1. The spreading alert missed about half of the turns (data run a day behind). It now compares with the previous pack.
2. A 2-of-3-legs trend (score 0.33) was read as flat. It now uses the integer vote; this affected 9 of 14 markets.
3. Alert refs were swapped on rebuild when keys duplicated; old files crashed; alerts no longer firing were treated as live.
4. The job could exceed 30 minutes under rate limits. It now has a time budget, the timeout is 40 min, and the backoff is fixed.
5. The auditor matched one narrative's figure under another's name ("oil", "fed").
6. Adapter details: hourly points, missing norm, per-query holes, unquoted links.
7. Stale stages, NaN in JSON, ties at the top.
8. `docs/research/consensus.md` was missing.

Also found: an empty tone series crashed `tone_change`, and the fake test data depended on test order (now reset per fixture).

## Live runs (10 Oct)
- Run 1 (v1) was cancelled at the 30-minute limit.
- Run 2 finished in about 12 minutes.
  - GDELT history goes back to **1 Jan 2017 at one point per day** (Hormuz: 3,532 days).
  - HTTP 429 came back even at one call per 6 s, so only Hormuz landed and the backfill completes over several runs.
- **GDELT's coverage collapsed after 1 Oct:** 61,712 articles on 2 Oct, 3,958 on 6 Oct, 678 on 8 Oct, vs about 100–175k a day in late September. 3–5 and 7 Oct are missing, as are 14–19 Sep. The monitor shows narratives as "stale, data through 1 Oct".
- On pre-collapse data, Hormuz / Iran oil supply was fading: 0.47x its prior 26 weeks, but at the 94th percentile of its own history.
- Trend vote: Brent, WTI, gold, heating oil, natgas, RBOB, corn, soybeans and wheat have 2 of 3 legs up (1-month down). RBOB, corn and soybeans are crowded (CFTC 95–100th percentile).
- Run 3 (38067821838): every GDELT call got HTTP 429, even with 30–60 s backoff, so nothing new landed. GitHub's shared runner addresses are probably throttled as a group (GDELT's call). Daily runs keep trying within their 12-minute budget. Trend, CFTC and idea placement work meanwhile.

## Open items
- **Watch GDELT** (429s and its collapsed totals). If narratives are still empty or stale by about 1 Nov, Bernardo decides a fallback. Options: GDELT via Google BigQuery (needs a Google Cloud key as a repo secret, which he adds), GDELT raw daily files (incremental only), or another news source.
- **Upgrades:** podcast trend knowledge; GPR/EPU validation + a 20–30 headline audit per narrative; curve/basis data.
- **Next agent:** 8 risk & crowding after the gate. It can build on `sections.consensus` (CFTC percentile, trend vote, flip levels, narratives per market).
- **Lessons for the kickoff:**
  - Commit `docs/research/<agent>.md` with the code.
  - Give every new data source a time budget.
  - The Actions job log can't be downloaded from the session; read `logs/runs.jsonl` after `git pull`.
