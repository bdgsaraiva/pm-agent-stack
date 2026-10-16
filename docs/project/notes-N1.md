# Session notes N1: notes, narratives and keys track, 15 Oct 2026

Brief: `docs/project/notes-and-keys-kickoff.md`. Claude Code on the repo, in its own clone (`pm-agent-stack-notes`), because the agent-build session works in the main checkout. Research addendum: `docs/research/consensus.md`, "Data source v2".

## Context
- Bernardo's feedback (15 Oct): the note has no news to link, and tracking the narratives matters most.
- Secrets present (`gh secret list`, names only): `EIA_API_KEY`, `GCP_SA_KEY`, `GCP_PROJECT_ID`, `USDA_FAS_API_KEY`, `NASS_API_KEY`. No key was read, printed or stored.
- The DOC API still answers HTTP 429 from this PC too (probed 15 Oct); it also confirmed the OPEC error comes from the quoted "OPEC+".

## Job 1: narratives back on, with links (done in code; first live run pending)
- **`pmstack/adapters/gdelt_bq.py`**: GDELT GKG on BigQuery (`gdelt-bq.gdeltv2.gkg_partitioned`, filtered on `_PARTITIONTIME`).
  - Series: the 18 frozen queries (+ EPU validation), matched on the words of each article's URL path. The GKG has no article text, so this is a new instrument with new ids `gdeltbq:<qid>:count|share|tone` and `gdeltbq:norm`, never mixed with the DOC series. `sourcecountry:` is dropped (logged).
  - Reads 2 small columns for the series. Only the headline query reads `Extras` (page title), for at most the last 3 days without headlines.
  - Budget: dry run, then `maximum_bytes_billed`. Caps: 60 GB a query, 150 GB a run, 800 GB a month (sandbox free tier 1 TiB), in the committed ledger `data/obs/gdelt_bq/_bytes.json`. A chunk that does not fit is halved down to one day, then the run stops. Order: new days → headlines → backfill (newest first, 14-day chunks, back to 1 Aug 2025).
  - No key (tests, local) → status `skipped`.
- **Headlines**: top 5 distinct titles per narrative per day, ranked by copies (syndication = prominence). Title, source domain, URL, date only (`data/text/gdelt_headlines.parquet`). Kept out of the central-bank text section.
- **consensus.py**: per narrative, the first instrument in `consensus.instruments` (`gdeltbq`, then `gdelt`) with a computed stage wins; BigQuery shows "insufficient history" while it backfills rather than the DOC "stale". After a source switch, the previous-pack comparison falls back to one data day earlier (no false "spreading" alerts on switch day). Each narrative carries up to 3 headlines from its last 7 data days.
- **Narrative tracker** (`data/narratives/tracker.json`): one record per narrative: stage, `since` (first data day of the stage; rebuilt from 180 days of stored series when a record starts, then observed), share, ratio, every change with the headlines seen then. A pack rebuilt for an earlier date never rewrites it.
- **facts.md**: Since column, Source column names the instrument, a "Headlines" list for narratives moving or changing stage.
- **Morning note skill**: the crowd check adds "since <date>" and at most 3 headline links per narrative that changed stage, only from the fact pack. **Friday review skill**: step 3a reads `narratives tracker --changed-since`.
- **Headline audit tooling**: `python -m pmstack narratives audit <id>` draws a reproducible 25-headline sheet spread over the stored days (`docs/research/narrative-audit/<id>.md`); mark y/n; `audit-score <id>` writes the precision into the tracker. To do as soon as headlines exist (after the first BigQuery run).
- **OPEC**: `opec_supply_v1` retired (`retired: true`, history kept, never refetched); `opec_supply_v2` = `OPEC ("output cut" OR ...)`.

## Job 3: keys wiring (done)
- `daily.yml` passes `GCP_SA_KEY`, `GCP_PROJECT_ID`, `USDA_FAS_API_KEY`, `NASS_API_KEY` to the fetch step. The USDA keys are unused until agent 9. `google-cloud-bigquery` added to requirements.

## Job 4: small follow-ups
- **CFTC date (done)**: the consensus map counts a report from its Friday release (Tuesday + 3 days, `cftc_release_lag_days`), as risk.py does.
- **Watch, 15 Oct note (closed)**: the 05:40 BRT run committed the pack at 05:54 BRT, and the note ran at 06:20 on it, with no wait and no "Late data". GitHub's own cron ran late (13:45 UTC) and rebuilt the pack after the note; stable refs kept the note valid. Keep watching the first notes for "Late data".
- Also fixed: adapter `attrs` leaked into Parquet metadata (store now clears them).

## Job 2: note format from the email samples (done 16 Oct)
- Three PDFs (one morning, midday and close note, same day, from a US market newsletter in his work mail) read for structure only. Nothing from them is stored: no names, tickers, figures or text. The text extracts were deleted after the spec; the PDFs themselves are in his Downloads folder for him to delete.
- `skills/morning-note/format.md`: what the models do (one skeleton, three clocks; cross-asset levels in one paragraph; one dominant narrative tied to prices, with price-vs-news reconciliation; bulls vs bears; every news line with its linked source, mostly Bloomberg, Reuters, FT, WSJ; forward ladder; midday breadth; close verdict), the adapted morning note, and the gaps (rate path by meeting, macro calendar, off-narrative news, intraday levels).
- Morning note skill v3: adds Market levels, What's driving it (narrative to price, ≤3 headline links per narrative from the pack), optional Bulls vs bears, and a Watching ladder; 300–500 words.
- Bernardo (16 Oct): **morning note only for now**; midday and close later, if v3 earns its place.

## Tests
- New: `tests/test_narratives_bq.py` (11: query translation, safe SQL literals, budget halving, ledger and month cap, daily vs backfill order, headlines, instrument choice, switch comparison, tracker, headline audit, CFTC lag). `test_pipeline` expects `gdelt_bq` as skipped offline.
- Local runs on Windows need `PYTHONUTF8=1` (one existing test writes an em dash without an encoding; fine on Linux).

## First live run and fix (16 Oct)
- Run 38830655542 (manual dispatch): `fetch:gdelt_bq` ok, 27 GB, backfill to 1 Aug 2025 done in one run, 93 headlines; pack built with stages, Since and headline links. GKG totals intact (~300k a weekday), so the DOC collapse was the API's only.
- URL-path match too thin (14 of 18 narratives under 20 a day) → new instrument `gdeltbqt` (title or URL path, ~0.17 GB a day), preferred in `consensus.instruments`; headlines re-drawn with the same match. Gap rule made weekday-aware (weekends ~0.55x). Path-only series kept, not updated.

## Title-or-path backfill (16 Oct, run 38882411686)
- `fetch:gdelt_bq` ok: 79.6 GB this run (month 106.9 GB of the 800 GB cap), 191 headlines, no errors.
- Coverage barely moved (Hormuz ~118 a day, US pump prices ~105, trade war ~22). **15 of 18 narratives are still under 20 articles a day**: the frozen phrases were written for full-text search and rarely appear in titles or URLs. Measured with stage, since and headlines: Hormuz (fading since 2026-08-10), trade war (fading since 2026-09-15), US pump prices (fading since 2026-10-07).
- Options (not done; needs a design pass): (a) title-friendly `_v2` phrasings that keep each narrative's meaning; (b) GDELT GKG themes (`V2Themes`, tagged from full text) as another instrument; lowering the 20-a-day floor is rejected (noise).

## Open / next
- First Actions run with BigQuery: check `fetch:gdelt_bq` in `logs/runs.jsonl` (bytes_gb, month_gb, errors), `gdeltbq:norm` (did the 1 Oct collapse reach the GKG too?), and articles a day per narrative under URL-path matching.
- Headline audit per narrative once headlines exist; GPR/EPU check still later.
- After the `gdeltbqt` backfill: articles a day per narrative under title-or-path; any still under 20 need a query re-version.

## Narrative coverage v2 (16 Oct, afternoon)
Task: fix the thin GKG coverage (15 of 18 narratives under 20 a day on `gdeltbqt`). Research rows: `docs/research/consensus.md`, "Narrative definitions v2".
- **Code.** `gdelt_bq.py` query terms `theme:NAME` (GKG Themes, tagged from the full text) and `org:name` (Organizations), mixed with title/URL words in any clause; a column is read only when a query names it. Optional `store_key`; headline days are counted per block's own query ids. `consensus.py`: a gdelt_bq block with its own `queries:` (each with `narrative:`) is an instrument whose definitions map narrative → query id; headlines follow the picked query; the tracker restarts a record on a definition change (`query_id` kept); `narratives audit` takes a narrative or query id.
- **Measurement first.** `python -m pmstack narratives measure <spec>` (`pmstack/narrative_measure.py`), run by the manual workflow `narratives-measure.yml` (concurrency group `daily`, commits the result and the byte ledger). Two rounds: runs 38919162340 (12.7 GB) and 38919760475 (12.7 GB). Specs and results in `docs/research/narrative-measure/`.
- **Findings.** Title phrasings precise but some thin; single themes noisy (any mention, many machine-translated articles); hybrids (subject in the title, angle from title words or a theme) work best.
- **Decision.** New instrument `gdeltbq2` (block `gdelt_bq_v2`, series `gdeltbq2:<id>:*`, data `data/obs/gdelt_bq_v2/`), first in `consensus.instruments`, with 10 narrative definitions + the EPU replica: OPEC (`opec_supply_v3`), Russia, gas/LNG, copper (broadened to copper attention), gold, crop weather, trade war, Fed hikes, inflation scare, AI bubble. Hormuz and pump prices stay on `gdeltbqt`. **Six stay "insufficient coverage"**: oil glut, China stimulus, Fed cuts, recession, weak dollar, US fiscal (no candidate cleared 20 a day in both windows with its meaning kept).
- **Budget.** ~0.36 GB a day; backfill to 1 Aug 2025 ≈ 160 GB = two runs at the 150 GB run cap; then ~1.5 GB a run. Month after the measurement: 133 GB of the 800 GB cap.
- Tests: `test_narratives_bq.py` 18 (theme/org matching, columns read only when named, measurement SQL and summary, v2 choice and headlines, v2 block fetch); `test_pipeline` expects `gdelt_bq_v2` skipped offline.

Open after this:
- Headline audit (20–30) of each v2 definition before any validation claim; the copper and crop definitions are the loosest.
- The 20-a-day floor cannot tell a quiet narrative from an unmeasurable one (Fed cuts while the Fed hikes). Option for Bernardo: show "quiet" when a definition cleared the floor over its own history but not in the last 4 weeks.
