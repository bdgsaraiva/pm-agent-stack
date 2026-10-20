# Session notes A14: issues 1, 5, 9, 10, narrative discovery (agent 7 two-step) and agent 9 v2 items, 20 Oct 2026

Literature reviews: `docs/research/narrative-discovery.md` (new); agent 9 v2 research (STEO vintages, ESR, FGIS, ERS, condition models) kept for later in `.projtmp/lit-balance-v2.md` and summarised below. Claude Code on Bernardo's PC, main checkout (no other session running).

## Bernardo's decisions (20 Oct)
- **Gate:** weekday 18:00 BRT `journal-nudge` scheduled task (Auto mode): one push notification on days with no paper idea logged, with the count towards 10.
- **Public note:** the first 2–3 monthly notes are private drafts (`notes/public/drafts/`), scored like published calls.
- **EIA key leak:** he deletes artifact 12068127300 himself and keeps the key.
- **Narratives become a two-step function:** (1) discovery from the news with a low bar, a theme with many sources on its first day flagged; (2) selection in conversation with him, with price and positioning context. Day-1 themes reach him in the next morning note; every candidate shown, daily, grouped by market; a dismissal hides a candidate 30 days or until it reaches 3x its sources at dismissal.
- **Gold:** "gold buying" means buying, reserves and flows, not daily price reports.
- **Headline-audit splits:** trade war #22 on topic; inflation #15, #18 and pump prices #12 not.
- **Agent 9 v2:** none of the four additions for now (export pace, Grain Stocks vs implied, STEO lens, condition yield). Done anyway: the FAS fix, the seasonality flag; the WPSR re-check waits for the 21 Oct release.

## Issues
- **1 (FAS key): fixed in code.** FAS moved the API to `api.fas.usda.gov` (api.data.gov key, `X-Api-Key` header); the old `apps.fas.usda.gov/OpenData` base answers 403/500. Checked with api.data.gov's public `DEMO_KEY`; the balance probe (run 39454198471) then stored 1,880 PSD rows with the existing secret. No new key needed.
- **5 (narratives):**
  - Headline audit of 12 definitions (25 headlines each; two blind model labellers, 96.3% agreement, kappa 0.91; Bernardo settled the splits): Fed hikes 100%, Hormuz 96%, Russian oil 96%, AI bubble 92%, pump prices 84%, inflation scare 80%, trade war 76%, natural gas 76%, gold 44%, crop weather 44%, OPEC+ 20%, copper 16%. Precision is stored in the tracker (`narratives audit-score`). Summary: `docs/research/narrative-audit/README.md`.
  - Measurement round 3 (run 39422459227, 5.7 GB): precise copper, OPEC+ and crop definitions run 2–7 articles a day; gold "buying only" ~9 a day; gold with price moves ~47 a day but mostly retail "gold price today" pages. Hence the two-step redesign.
- **9 (Windows encoding):** every test file read/write is UTF-8; the suite no longer needs `PYTHONUTF8=1`.
- **10 (one checkout per session):** rule in `CLAUDE.md` ("Parallel sessions") and both kickoff briefs: every parallel session works in its own git worktree.

## What shipped
- **Agent 9:** `usda_psd.py` on the new host; `balance.seasonality` per stock series (share of weekly-change variance by month, stability between window halves; weak → 52-week comparison, no range alert). Live: Cushing (0.06 / 0.17), jet (0.07 / 0.57) and total stocks ex SPR (0.07 / 0.47) flagged; crude, gasoline, distillate, propane stable. Tests: `tests/test_balance_v2.py`.
- **Narrative discovery (agent 7 step 1):** `pmstack/discovery.py`, `pmstack/adapters/gdelt_disc.py`, `config/discovery.yaml`, `config/sources.d/discovery.yaml`; "Narrative discovery" section in facts.md; `narrative_new` alert for day-1 themes in focus markets; morning-note bullet; skill `.claude/skills/narratives/` + `/narratives review` (step 2). Tests: `tests/test_discovery.py`.
  - Query 1 counts title words and word pairs per distinct source in BigQuery (English records only), so only aggregates come back; query 2 fetches titles for flagged terms only. ~0.35 GB a day on the shared byte ledger.
  - Score: share of the day's distinct sources vs its own EWMA/EWM variance (half-life 14 days) with a 3-domain noise floor; "rising" = score >= 4 with >= 5 domains; "new" = <= 2 domains on each of the last 28 days and >= 8 today. From nothing, a term needs ~15 sources to score 4, so day 1 is caught by "new".
  - Candidate lists are written once per UTC day and used from the next day; context (move in sd, base rate, 20-day vol, CFTC before vs latest) is point-in-time.
  - Day aggregates (~1-2 MB a day) are not in git: the data job keeps them in its Actions cache (restore before the fetch, save after); if the cache is evicted the backfill rebuilds them. Candidate lists and decisions are in git.
  - A Monday pack shows Friday, Saturday and Sunday's lists, repeats merged. Decisions apply from the next pack (the CLI list applies today's).
- **Independent review of discovery:** 17 defects (2 High: Python scoring loop could overrun the data job; Monday pack lost Friday/Saturday), all fixed; table in `docs/research/narrative-discovery.md`, "Review". The data job timeout went from 40 to 50 minutes (GDELT budgets 12 + 10 + 10 + 6).

## First live run of discovery (run 39467453179, 20 Oct)
- 38 history days stored in the 6-minute budget (~9.5 s a query), Actions cache saved: 15.9 MiB (~0.4 MB a day, smaller than estimated). No candidate list yet: the backfill took the whole budget. Fix: the adapter now stores only the 28 days the candidate day needs, writes the list, then continues the history (test added). 49 history days left: the next run or two finish them.
- The run's data commit lost a race with the other track's 17:53 data commit (binary Parquet conflicts in the rebase); the discovery cache is unaffected and tomorrow's 05:40 run refetches the rest.
- Shared BigQuery ledger: October at 454 GB of the 800 GB monthly cap after this run. `gdelt_bq_v2` spent 81 GB in each of the two runs today (its fill pass for new queries); if it repeats daily, the month cap stops all BigQuery sources, discovery included, around 24 Oct. Flagged to the notes track.

## Agent 9 v2 research (kept for later)
- 106 STEO vintages (2018–2026, free archive xlsx): stock paths barely beat a seasonal-naive path (3–16% lower MAE; no edge for crude and total commercial since 2023); production forecasts clearly better (0.16 vs 0.24 mb/d). STEO = "EIA's view" and revisions, never the expectation for surprises.
- Export pace without a key: the weekly ESR summary xlsx (latest two weeks: commitments, year-ago, WASDE projection) plus FGIS inspection CSVs from 2014. Pace predicts little early in the year (end-Q1 corn sales 36–66% of final exports).
- Grain Stocks vs implied: ERS yearbook CSV; feed-and-residual quarterly share sd 0.033 (Q1) ≈ ±190 mbu on Dec 1 implied stocks: a band, never a point.
- Condition yield: Irwin–Good out of sample RMSPE ~4% in August; Beguería & Maneta's gain rests on leave-one-out (look-ahead) and fails out of sample.
- No free live back-month futures (EIA C1–C4 end 5 Apr 2024): curve spreads deferred.

## Open items
- **Discovery:** watch the first live runs (backfill pace, bytes per day, cache size); candidates appear once 28 days are stored; then `discovery placebo` to size the daily list, and the first `/narratives review`.
- **Bernardo:** create `pm-network`; delete artifact 12068127300; code-of-ethics check; 10 paper ideas by 1 Nov; settle copper, OPEC+, crop weather and gold in the first review.
- **WPSR:** after the 21 Oct release, run `python -m pmstack balance probe` on the 22 Oct pack and repoint the v1 "Appendix B" citation.
