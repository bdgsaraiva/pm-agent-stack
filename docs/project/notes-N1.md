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

## Job 2: note format from the email samples (waiting)
- Waiting for the three PDFs (morning, midday, close). Plan: read for structure only, write `skills/morning-note/format.md`, revise the skill, delete local copies, ask once about midday/close notes.

## Tests
- New: `tests/test_narratives_bq.py` (11: query translation, safe SQL literals, budget halving, ledger and month cap, daily vs backfill order, headlines, instrument choice, switch comparison, tracker, headline audit, CFTC lag). `test_pipeline` expects `gdelt_bq` as skipped offline.
- Local runs on Windows need `PYTHONUTF8=1` (one existing test writes an em dash without an encoding; fine on Linux).

## First live run and fix (16 Oct)
- Run 38830655542 (manual dispatch): `fetch:gdelt_bq` ok, 27 GB, backfill to 1 Aug 2025 done in one run, 93 headlines; pack built with stages, Since and headline links. GKG totals intact (~300k a weekday), so the DOC collapse was the API's only.
- URL-path match too thin (14 of 18 narratives under 20 a day) → new instrument `gdeltbqt` (title or URL path, ~0.17 GB a day), preferred in `consensus.instruments`; headlines re-drawn with the same match. Gap rule made weekday-aware (weekends ~0.55x). Path-only series kept, not updated.

## Open / next
- First Actions run with BigQuery: check `fetch:gdelt_bq` in `logs/runs.jsonl` (bytes_gb, month_gb, errors), `gdeltbq:norm` (did the 1 Oct collapse reach the GKG too?), and articles a day per narrative under URL-path matching.
- Headline audit per narrative once headlines exist; GPR/EPU check still later.
- After the `gdeltbqt` backfill: articles a day per narrative under title-or-path; any still under 20 need a query re-version.
