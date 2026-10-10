# pm-agent-stack (personal build)

Research memory and monitors for a cross-asset PM, on public data. Steps 1 and 3a of the agent blueprint:

- **Research memory** — prices (commodities, US equities, Treasury futures, USD), EIA inventories, CFTC positioning, FRED rates/credit/USD and central-bank text in Parquet (queried with DuckDB), plus notes, podcast summaries and a trade journal in markdown.
- **Monitor 3a** — commodity supply-demand, US equities, US rates, USD and central-bank text. Writes a fact pack with every figure linked to its source, and ranked alerts.
- **Decision journal + sizing assistant** — `/journal` captures a paper idea in a minute; every idea gets a suggested size (Kelly-relative risk units, capped, stepped, cut for overlap and drawdown) and flags for under- and over-sizing. Evidence: `docs/research/sizing.md`.
- **Critic** (agent 5) — every new idea gets a card computed by code (market base rate for its target/stop/horizon, similar past ideas, trend, CFTC crowding, 2y-yield direction, the day's alerts, Zweig rule triggers) and at most three questions: a pre-mortem by default, a counter-argument or rule question only when the data gives a reason. Answers live in the entry. Fridays 18:17 BRT: "what breaks this trade" for ideas where something changed (`skills/critic-weekly/`). Evidence: `docs/research/critic.md`.
- **Consensus and narrative monitor** (agent 7) — a "Consensus map" in the daily fact pack: 18 news narratives scored as a share of all GDELT coverage (spreading, peaking, fading, steady, dormant), a trend-follower proxy and CFTC managed-money percentile per market, a label per market and a placement per open idea (with the crowd, against it, quiet, mixed; all inference). The morning note mentions only stage changes and his ideas; the critic card carries the crowd facts. Descriptive only until the quant gate. Evidence: `docs/research/consensus.md`.
- **Risk and crowding** (agent 8) — a "Risk and crowding" section in the daily fact pack, all in paper R: a risk table per open idea (R now, stop in daily sd, 1-sd day in R, share of stress risk, cluster, CFTC crowding on its side, flags), effective independent ideas, stress P&L on history back to 1986 (futures from ~2000, spot/index proxies before): a 32-episode library replayed day by day, the worst 1/5/20/60-day windows for today's book, 9 named one-month shocks under stress, 2008 and 2022 correlations, and the worst case at k = 3 (stops honoured and gapped), CTA trigger levels, and warnings (amber drawdown, the sizing cut counting open marks, clustered losses, persistent turbulence). `python -m pmstack risk` prints the stress report on demand. Descriptive only. Evidence: `docs/research/risk.md`.
- **Weekly review** (agent 6) — every Friday the scorecard puts process first (invalidation, P(win), sizing by the rule, critic answered, exits tagged), then leaks against his own baseline (held past invalidation, tilt after big closes, overtrading, exits by trigger), then outcomes gated by sample size with intervals and shrinkage, and one if-then goal for next week that code tracks. Evidence: `docs/research/weekly-review.md`.
- **Number auditor** — `python -m pmstack audit <file>` checks every figure, date and alert ref in a written output against the fact pack and the journal; the morning note fixes problems once and flags the rest at the top.
- **Morning note** — a scheduled Claude task reads the fact pack at 06:18 BRT on weekdays and writes a Docs page (see `skills/morning-note/SKILL.md`).

Design: architecture doc in the Claude Project "Future of Asset Management and Trading". Rules for agents: `CLAUDE.md`.

## Daily flow
1. GitHub Actions, 05:40 BRT Mon–Fri (`.github/workflows/daily.yml`): tests → `python -m pmstack all` → commit `data/`, `briefs/`, `logs/`.
2. Claude scheduled task, 06:18 BRT: reads `briefs/<today>/facts.md`, writes the note, audits its figures, saves `briefs/<today>/note.md`, logs and pushes.
3. Fridays 18:17 BRT, Claude scheduled task "Friday review": `critic weekly` + `review weekly`, writes `briefs/<today>/critic-weekly.md` (critic pass, scorecard, debrief, next week's goal) and a Docs page.

## Setup
1. Repo secrets (Settings → Secrets and variables → Actions): `EIA_API_KEY` (free, https://www.eia.gov/opendata/register.php) and optionally `FRED_API_KEY` (free; without it the public CSV endpoint is used).
2. Run the workflow once by hand (Actions → daily-fetch-and-monitor → Run workflow). The first run backfills history (EIA from 2018, CFTC from 2020, prices from 2023).

## Swapping a data source
Write `pmstack/adapters/<name>.py` with `KIND` and `fetch(cfg, since)` returning the columns in `pmstack/store.py`, register it in `pmstack/adapters/__init__.py`, and point the source block in `config/sources.yaml` at it. The monitor does not change.

## Known gaps (free data)
Front-month futures only (no full curves); no shipping or weather yet; Yahoo prices are unofficial and personal-use only.
