# pm-agent-stack — rules for any Claude session in this repo

This is Bernardo's **personal** build of a PM agent stack (Steps 1–3 of the blueprint in `docs/architecture.md`). It runs on public data only.

## Hard rules
- **No fund data here.** Never write the fund's positions, sizes, P&L, order history, broker research or proprietary notes into this repo, a prompt, a note or a log — not even as a summary. `portfolio/` and `journal/` hold dummy or public-idea files only. The corporate build lives elsewhere.
- **Numbers come from code.** Agents quote figures only from `briefs/<date>/facts.md` (or a DuckDB query over `data/`), with the source link. No figures from memory or the web in a note.
- **Facts vs inference.** Label interpretation. No trade instructions or sizing; decisions stay with the PM.
- **Log every agent run** with `python -m pmstack log --step <name> --fields '<json>'`.
- **Licences.** `pmstack/adapters/yahoo.py` is unofficial and personal-use only; do not port it. Never add Bloomberg-derived data to this repo.
- **Quant standards.** Alerts are not signals. Anything promoted to a signal goes through the quant-research gate (alpha vs beta, out-of-sample, multiple-testing haircut, costs, look-ahead and memorisation checks).

## Layout
- `config/sources.yaml` — data sources; one block per adapter (swap adapters here)
- `config/monitor.yaml` — alert thresholds
- `pmstack/` — adapters, store (Parquet + DuckDB), monitor, run log, CLI
- `data/obs/<source>/<year>.parquet`, `data/text/<source>.parquet` — research memory (numbers, policy text)
- `briefs/<date>/` — `facts.md`, `facts.json`, `alerts.json`, `note.md`
- `notes/` — research, calls, podcasts (markdown with YAML header); `journal/` — trade ideas incl. rejected
- `skills/` — instructions for agents (morning-note; critic next)
- `logs/runs.jsonl` — audit trail

## Commands
```
python -m pmstack all              # fetch every source, then build today's fact pack
python -m pmstack fetch --only eia # one source
python -m pmstack monitor --date 2026-10-05
python -m pytest -q                # offline tests
```
Query the memory: `python -c "from pmstack import store; print(store.connect().execute('select source, count(*) from obs group by 1').df())"`
