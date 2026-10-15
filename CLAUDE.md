# pm-agent-stack — rules for any Claude session in this repo

This is Bernardo's **personal** build of a PM agent stack (Steps 1–3 of the blueprint in `docs/architecture.md`). It runs on public data only.

## Hard rules
- **No fund data here.** Never write the fund's positions, sizes, P&L, order history, broker research or proprietary notes into this repo, a prompt, a note or a log — not even as a summary. `portfolio/` and `journal/` hold dummy or public-idea files only. The corporate build lives elsewhere.
- **Numbers come from code.** Agents quote figures only from `briefs/<date>/facts.md` (or a DuckDB query over `data/`, the journal, or a critic card), with the source link. No figures from memory or the web in a note. Every written output is run through `python -m pmstack audit` before it is published.
- **Facts vs inference.** Label interpretation. No trade instructions. Size suggestions come only from `pmstack/sizing.py`, in paper risk units, as advice; decisions stay with the PM.
- **Log every agent run** with `python -m pmstack log --step <name> --fields '<json>'`.
- **Licences.** `pmstack/adapters/yahoo.py` is unofficial and personal-use only; do not port it. Never add Bloomberg-derived data to this repo.
- **Literature first.** Before building any agent, review the most cited papers, the Atlas investor cards and the specialist books; write `docs/research/<agent>.md` (finding → what it changes → source) and build from it.
- **Quant standards.** Alerts are not signals. Anything promoted to a signal goes through the quant-research gate (alpha vs beta, out-of-sample, multiple-testing haircut, costs, look-ahead and memorisation checks).

## Layout
- `config/sources.yaml` — data sources; one block per adapter (swap adapters here)
- `config/monitor.yaml` — alert thresholds
- `pmstack/` — adapters, store (Parquet + DuckDB), monitor, run log, CLI
- `data/obs/<source>/<year>.parquet`, `data/text/<source>.parquet` — research memory (numbers, policy text)
- `briefs/<date>/` — `facts.md`, `facts.json`, `alerts.json`, `note.md`
- `notes/` — research, calls, podcasts (markdown with YAML header); `notes/context.md` — standing facts Bernardo has stated (agents take them as given)
- `journal/<YYYY>/<id>.md` — decision journal (paper/example ideas only): conviction, payoff, invalidation, source, events, outcome; `pmstack/journal.py` runs the hard checks and stats
- `pmstack/sizing.py` — sizing assistant (agent 4): Kelly-relative units, cap, steps, drawdown cut (on the marked book since agent 8: open marks count), flags, review
- `pmstack/critic.py` + `config/critic.yaml` — critic (agent 5): card (outside view, reference class, tape, crowd, policy, alerts, Zweig triggers), slot plan, save/answer/withdraw/outcome, Friday `weekly`, `stats`. Code picks the questions; the model only words them; saved questions are frozen
- `pmstack/review.py` + `config/review.yaml` — weekly review (agent 6): process scorecard (process first, leaks, outcomes gated by sample size with intervals and shrinkage), goal catalogue and tracking (`journal/goals.yaml`), monthly section. Review week = 7 days ending 18:00 BRT Friday
- `pmstack/consensus.py` + `config/monitor.yaml` (`consensus:`) — consensus and narrative monitor (agent 7): GDELT attention stages for 18 frozen narratives (+1 validation query), trend-follower proxy (1/3/12-month vote, strength, flip levels), CFTC percentile beside it, labels and idea placement (all inference), Fed wording counts; `narrative_spreading` alert vs the previous pack. Descriptive only, every narrative "unvalidated" until GPR/EPU + headline audit
- `pmstack/risk.py` + `config/risk.yaml` — risk and crowding (agent 8): risk model (EWMA vol; calm and stress correlation, Ledoit–Wolf), risk table in R, effective independent ideas, clusters, stress P&L in R (replays, named driver shocks, worst case at k = 3; stops honoured and gapped), CTA levels, crowding per idea (red only when funding stresses), one marked book curve for amber and red warnings. Since v2 (10 Oct evening) stress runs on history back to 1986 (`risk.history`: futures from ~2000, spot/index/yield proxies before, roll screen): a 32-episode library replayed day by day, the worst 1/5/20/60-day windows for today's book, named shocks under stress/2008/2022 correlations. `risk.marked_drawdown` is also the sizing assistant's drawdown cut (open marks count). Only realised signals alert; nothing after the as-of date is used
- `pmstack/fetch.py` — `history_start` (prices, FRED: 1986) = one-time deep fetch per series, marked in `data/obs/<source>/_history.json`; a `--backfill` goes back to it too
- `pmstack/adapters/gdelt.py` — GDELT DOC 2.0 (free, keyless; cite "The GDELT Project" with a link). Unreachable from the cloud sandbox: runs in GitHub Actions only, with a 12-minute budget and 30–60 s backoff on HTTP 429; missing series are fetched first and catch up next run. Queries are frozen: an edit gets a new `_vN` id
- `docs/project/` — project hand-off docs (plan and status `agents-plan.md`, kickoff briefs, session notes `notes-A<n>.md`). Source of truth since 15 Oct 2026; start any new build session from `docs/project/agent-build-kickoff.md`
- `pmstack/audit.py` — number auditor: every figure, date and alert ref in an output checked against `facts.json`/`facts.md`/journal; `--flag` writes the banner
- `docs/research/` — literature review behind each agent (risk.md for agent 8)
- `skills/morning-note/` — the 06:18 BRT note (v2: journal-first, audited); `skills/critic-weekly/` — the Friday 18:17 BRT review (critic pass + scorecard + one goal); `.claude/skills/journal/` + `/journal` command — 60-second idea capture, then the critic's card and questions
- `logs/runs.jsonl` — audit trail

## Commands
```
python -m pmstack all              # fetch every source, then build today's fact pack
python -m pmstack fetch --only eia # one source
python -m pmstack monitor --date 2026-10-05
python -m pmstack journal new|event|close|reject|list|stats|book|check   # decision journal (close needs --trigger)
python -m pmstack journal size <id> | sizing-review                     # sizing assistant
python -m pmstack critic card <id> | save <id> --json '[...]' | answer <id> --q q1 ... | weekly --write | stats   # critic
python -m pmstack review weekly [--date D] [--write] [--monthly] | goal show|set <key>|drop|list   # weekly review
python -m pmstack risk [--date D] [--out file.md]   # risk and crowding stress report (agent 8)
python -m pmstack audit briefs/<date>/note.md [--facts extra.json ...] [--flag]   # number auditor
python -m pytest -q                # offline tests
```
Query the memory: `python -c "from pmstack import store; print(store.connect().execute('select source, count(*) from obs group by 1').df())"`
