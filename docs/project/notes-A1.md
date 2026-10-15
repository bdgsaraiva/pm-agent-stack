# Session A1 notes — AI-agent phase kickoff, 4 Oct 2026

## What happened
- Read the kickoff, research plan, notes-S9 and Atlas 4.3/4.5/4.6/4.7.
- Tested the environment: the Claude cloud workspace's shell cannot reach EIA, FRED, CFTC, BCB, Fed or Yahoo (only package registries); WebFetch could not read the BCB API (robots) or the FRED CSV. So numeric data must be fetched elsewhere → GitHub Actions.
- No data connectors in the account (only Spotify). GitHub not linked to Claude.
- Asked 4 design questions. Answers: GitHub Actions + cloud task; just Bernardo; 06:30 BRT Docs + push; free data only.
- Wrote the architecture doc (Docs): https://claude.ai/code/artifact/b3d8514a-d6e6-4756-9864-474e1c35e429
- Built the repo `pm-agent-stack` locally, offline-tested (6 tests), committed, zipped and sent as `pm-agent-stack-v0.1.zip`.

## Repo contents (v0.1)
- `pmstack/adapters/`: eia (API v2 seriesid, key), cftc (Socrata 72hh-3qpy, managed money and producer/merchant, net % OI), fred (API key or public CSV), bcb (SGS 432/433/1 + Focus annual medians via Olinda), yahoo (chart endpoint; personal use only), rss (Fed, ECB, BoE, BoJ RSS; BCB Copom JSON — format unverified).
- `pmstack/store.py`: Parquet per source per year + DuckDB views `obs`, `text`. Every row: source, series_id, name, date, value, unit, freq, source_url, fetched_at.
- `pmstack/monitor.py`: price moves (1d return vs 60-day vol, live overnight move vs last close for futures/FX), EIA weekly change vs 5-year same-week (±1 week) average, CFTC managed-money net % OI 3-year percentile and weekly change z, FRED moves, BCB Selic/IPCA/PTAX and Focus week-on-week revisions, central-bank text in the last 36 h with whole-word keyword match (EN + PT). Output `briefs/<date>/facts.md|json`, `alerts.json`. Data-health section with fetch errors, stale series and known gaps.
- `skills/morning-note/SKILL.md`: the note's inputs, rules (quote only fact-pack figures with links; facts vs inference; no sizing), structure, delivery (Docs page, `note.md`, log, commit, push).
- `CLAUDE.md`: hard rules (no fund data; numbers from code; log runs; licences; quant gate).
- Templates: `notes/research`, `notes/calls`, `notes/podcasts` (TTU seed format), `journal/` (incl. rejected ideas, agent input kept separate from decision), `portfolio/positions_dummy.csv`.

## Issues found while testing (fixed)
- Futures/FX daily bars dated today are live at 05:40 BRT → separated "last close" from "live vs close".
- Substring keyword matching ("ata" in "data") → whole-word regex.
- Monthly series (IPCA, IMF) wrongly flagged stale → monthly threshold 75 days.
- Single-file Parquet would bloat git history → year partitions.

## Not yet verified
- Live API responses (field names, encodings, throttling). First Action run is the test; read its log.
- EIA series IDs for Cushing (W_EPC0_SAX_YCUOK_MBBL), exports (WCREXUS2), SPR (WCSSTUS1) — standard IDs but unconfirmed against the live API.
- BCB Copom JSON endpoint and fields.
- Docs creation and push notification from a scheduled task.

## Scheduled task prompt (to create once the repo exists)
Name: "Morning note (commodities + CB)". Cron: `CRON_TZ=America/Sao_Paulo 24 6 * * 1-5`. Push notifications on. Repo `pm-agent-stack` attached with push access.

> Clone the private repo `<owner>/pm-agent-stack`. Read `CLAUDE.md`, then follow `skills/morning-note/SKILL.md` exactly to write today's morning note (today = current date in America/Sao_Paulo). Quote only figures from `briefs/<today>/facts.md`, each with its link. Create the Docs page, save `briefs/<today>/note.md`, log the run with `python -m pmstack log`, commit and push. End with the three key points and the Docs link.
