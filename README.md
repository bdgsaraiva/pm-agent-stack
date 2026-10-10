# pm-agent-stack (personal build)

Research memory and monitors for a cross-asset PM, on public data. Steps 1 and 3a of the agent blueprint:

- **Research memory** — prices (commodities, US equities, Treasury futures, USD), EIA inventories, CFTC positioning, FRED rates/credit/USD and central-bank text in Parquet (queried with DuckDB), plus notes, podcast summaries and a trade journal in markdown.
- **Monitor 3a** — commodity supply-demand, US equities, US rates, USD and central-bank text. Writes a fact pack with every figure linked to its source, and ranked alerts.
- **Decision journal + sizing assistant** — `/journal` captures a paper idea in a minute; every idea gets a suggested size (Kelly-relative risk units, capped, stepped, cut for overlap and drawdown) and flags for under- and over-sizing. Evidence: `docs/research/sizing.md`.
- **Morning note** — a scheduled Claude task reads the fact pack at about 06:30 BRT on weekdays and writes a Docs page (see `skills/morning-note/SKILL.md`).

Design: architecture doc in the Claude Project "Future of Asset Management and Trading". Rules for agents: `CLAUDE.md`.

## Daily flow
1. GitHub Actions, 05:40 BRT Mon–Fri (`.github/workflows/daily.yml`): tests → `python -m pmstack all` → commit `data/`, `briefs/`, `logs/`.
2. Claude scheduled task, about 06:30 BRT: reads `briefs/<today>/facts.md`, writes the note, saves `briefs/<today>/note.md`, logs and pushes.

## Setup
1. Repo secrets (Settings → Secrets and variables → Actions): `EIA_API_KEY` (free, https://www.eia.gov/opendata/register.php) and optionally `FRED_API_KEY` (free; without it the public CSV endpoint is used).
2. Run the workflow once by hand (Actions → daily-fetch-and-monitor → Run workflow). The first run backfills history (EIA from 2018, CFTC from 2020, prices from 2023).

## Swapping a data source
Write `pmstack/adapters/<name>.py` with `KIND` and `fetch(cfg, since)` returning the columns in `pmstack/store.py`, register it in `pmstack/adapters/__init__.py`, and point the source block in `config/sources.yaml` at it. The monitor does not change.

## Known gaps (free data)
Front-month futures only (no full curves); no shipping or weather yet; Yahoo prices are unofficial and personal-use only.
