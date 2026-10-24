# Session notes A15: specialists S0 (foundations) and S1 (Energy), 24 Oct 2026

Brief: `docs/project/specialists-kickoff.md` (saved and committed first). Claude Code on Bernardo's PC, in its own git worktree (`claude/specialists-kickoff-27d712`), rebased on main before building.

## Bernardo's decisions (24 Oct)
- **Gate (1 Nov):** not met (4 of 10 paper ideas plus the example; 1 of 2 Friday reviews, 23 Oct). "Build anyway".
- **Architecture:** "Agent 12 will become the orchestrator + the specialists. We have to merge this architecture with the previous one." The drawing of the merged total architecture is at https://claude.ai/artifact/Bz9g7sbKwn5truYMPQmpct (repo `docs/project/architecture-total.html`). Reading taken: agent 12 "Research" = the fundamentals pillar. The research loop becomes its testing gate (`/research`), agent 9's balances fold into the specialists, agent 7 is the narrative agent, and a new agent 13 "Quant" runs over `pmstack/quant/`. **To confirm with Bernardo** on the drawing.
- **Command:** `/ask energy: <question>` for one specialist now; plain `/ask` goes to the orchestrator from S6.
- **His numbers:** they arrive next week as "Bernardo prior", through the inbox, each confirmed by him in chat before filing ("Inbox + confirm").
- **S1 sources:** all four that passed: ANP Brazil, EIA STEO vintages, JODI snapshots, EIA monthly rigs.
- **Card runs:** ad hoc `/ask` only (no scheduled Energy card) until the orchestrator exists.

## Parallel track
The notes-and-keys track was treated as **active**: it was never closed in `agents-plan.md`, and its last commits were on 21 Oct. This session did not touch the morning note, `consensus.py`, the news and BigQuery adapters, `config/sources.yaml`, `config/monitor.yaml` or `daily.yml`. New sources went in `config/sources.d/energy.yaml`, which the daily job merges with no workflow edit. One small edit was outside the agent's own files: `pmstack/adapters/eia.py` now accepts a per-series `url`, so gas and rig series link to the right EIA page; existing series are unchanged.

## What shipped
**S0 foundations**
- `pmstack/facts.py`: an append-only log `data/facts/facts.jsonl` with two clocks. Valid time is `valid_from/valid_to`. Knowledge time is `available_at`, the public date (backfills carry the real release date), plus `recorded_at`. `valid_to` is derived from the next fact, so an earlier read still sees the old fact open. A revision with the same `valid_from` wins only from its own availability. Retractions are rows of their own. `record` requires a `pmstack.*` writer, `source_url` and `source_type`. `record_changed` files batch snapshots (JODI).
- `config/state_card.schema.json` + `pmstack/cards.py`: one contract at every level. The validator is a dependency-free schema subset plus semantic checks: no source dated after `as_of`, every `[sN]` exists, and every number in the text equals a cited source value. Windows, years and written dates are excepted, and shares may be written as %. Cards are never overwritten.
- `config/agents.yaml` + `pmstack/route.py`: an explicit prefix wins, otherwise keyword hits decide. The router returns the question types and the exact files to load. Planned specialists say "not built yet". Questions for another pillar are pointed there.
- `knowledge/` (README, `_template/`, `sources.md`, `commodities/cross-links.md`) and `pmstack/knowledge.py`: `drivers.yaml` is written only by code and rendered to `drivers.md`. Size provenance is enforced: literature needs a source and URL; an own estimate needs its stored regression and as-of date; a Bernardo prior goes only through `confirm-prior`; broker names are refused. `knowledge check` writes prior-vs-estimate disagreements into `open-questions.md`, and every size is also a dated fact.
- `knowledge/inbox/` + `pmstack/inbox.py`: screen the first pages only, then Bernardo confirms the type. A refused file (broker or fund) keeps only its hash in the ledger, and he is asked to delete it. Allowed files go through the digester. Facts from a document are filed only when the number is inside a checked card's quote.

**S1 Energy**
- Literature: three parallel passes (oil economics, storage and curves; reactions to scheduled reports and how to measure surprise; source check) plus the Atlas cards (Andurand, Hall, King). Written up in `docs/research/energy.md`.
- `pmstack/events.py` + `config/energy.yaml`: reaction base rates for the EIA reports (WPSR and WNGSR) on daily closes.
  - The surprise uses **the fact pack's definition**: same and adjacent ISO weeks of the prior five years, in sd. So the playbook and the pack show one number.
  - Release dates follow EIA's rule; holiday shifts are approximate.
  - Statistics: vol ratio, big-move lift, sign agreement with Wilson intervals, slope per sd and per unit with HC1 errors, halves, eras (before June 2006, 2006–2014, since 2015), the recency rule, day-before and day-after placebos, and an outlier screen.
- Results on repo data, as of 2026-10-23 (contemporaneous, never a forecast):
  - WTI: 1,341 releases, −0.35% per sd (t −5.8); −0.22% since 2015; sign hit 64% of 453.
  - RBOB on gasoline: −0.53% per sd (t −8.1). ULSD on distillate: −0.42% per sd, stable in both halves.
  - Brent's link to US stocks faded in the second half of the sample.
  - Cushing: the since-2015 block is the base rate, at −0.07%.
  - WTI moves the day before the release at −0.18% per sd (t −3.3), consistent with Miao et al. (2018) and with API's Tuesday report.
- `pmstack/specialist.py`: a numbered input pack built point in time. It draws on the fact pack (latest on or before the date), the events code, the curve, and STEO/JODI/ANP/rigs after their availability lags.
- `pmstack/quant/curve.py`: the first quant-library module, front spreads from stored contracts.
- Adapters:
  - `yahoo_curve`: next 12 or 6 contracts per energy root, personal use. Collection starts now because Yahoo keeps no expired contracts.
  - `steo`: one workbook per issue. Ids are lower case in table 3a. The stock line is net withdrawals, so negative means a build (label fixed after a live check).
  - `jodi`: country crude balances; vintages go to the facts log.
  - `anp`: national production in m3 and kb/d, plus fuel sales.
  - Blocks `eia_ng` (gas storage) and `eia_rigs`.
  - `openpyxl` added to `requirements.txt` and installed in the venv with uv.
- Knowledge: `knowledge/energy/{crude,products,natgas}` (primers, drivers, balance templates, playbooks with the code table, analogues linked to agent 8's replays, open questions). Drivers carry 10 literature sizes and 4 own estimates.
- Skills: `.claude/skills/ask/` + `.claude/commands/ask.md` (route, pack, read, card, save, answer, audit, log) and `skills/specialist-energy/SKILL.md` (an index only).
- Test set: `evals/energy/` + `pmstack/cevals.py`. 20 dated tasks (4 sealed) with data-driven graders: number, eq, contains, any, list, bool, abstain, forbidden wording, no trade. Baseline: three independent answering sessions, **pass^3 20/20** (Wilson 0.84–1.0). The graders were spot-checked against bad answers.
- Live run: `/ask energy: how tight is the crude balance and what does Wednesday's EIA report usually do?`. The card was saved (`cards/crude/2026-10-23-energy.json`, 22 sources). The answer `cards/answers/2026-10-23-crude-balance-and-eia.md` audited 14 matched, 0 orphans. Logged as `ask:energy`.
- Tests: 30 specialist tests across `tests/test_specialists_s0.py`, `tests/test_specialists_energy.py` and `tests/test_energy_sources.py`.

## Independent review (a sub-agent that did not build it): 18 defects (3 High, 8 Medium, 7 Low)
| # | Sev | Defect | Fix |
|---|---|---|---|
| 1 | High | The card validator trusted the card's own `sources` list, so the model could write a "source" and cite it; a string value whitelisted every number inside it | `cards save` needs `--pack`. Every source must be a row of the input pack (same id, value, date, url). String values no longer enter the pool. |
| 2 | High | STEO's sheet date is the forecast *completion* date; EIA releases days later (look-ahead) | Availability = sheet date + 7 days (`STEO_RELEASE_LAG_DAYS`). |
| 3 | High | Validator holes: the sign was ignored; 4-digit numbers were skipped as years ("2,050 $/oz"); "25 days" was skipped as a window | An explicit sign must match. A year is skipped only with no comma, `$` or unit. Windows = hyphenated spans or counts of weeks, months, years, sessions or releases (never days). |
| 4 | Med | `facts.known` kept one of three literature sizes from the same day | Deduplicate on source too; `valid_to` = next *later* valid_from. |
| 5 | Med | `record` was idempotent only within one second | With no release time given, an identical fact is a no-op. |
| 6 | Med | Gas report holiday rule wrong (Monday holidays, Christmas Wednesday) | Shift by the holiday's weekday (gas: Mon 0, Tue/Wed +1, Thu −1; oil: Mon–Wed +1) plus an `exceptions` list for dates checked against EIA's schedule. |
| 7 | Med | The pack read revised JODI/ANP values; the JODI lag was tight | JODI lag 60 days. Labels say "latest vintage: revised, not as first published". |
| 8 | Med | Curve positions were wrong before collection started (deferred contracts read as M1) | No curve before 24 Oct 2026. M1 must be within 3 months. |
| 9 | Med | `facts.jsonl` was appended by the daily job and by local sessions with no merge rule | `.gitattributes`: union merge for `data/facts/facts.jsonl` and `logs/runs.jsonl`. |
| 10 | Med | `knowledge add` accepted a prior carrying a `confirmed` key; estimates were backdated to their data cutoff | Priors are refused in `add`. A size's availability = when it was filed. |
| 11 | Med | A broker or fund refusal could be overturned; office files and scanned PDFs passed the screen as empty text | A refusal is final per hash. Unreadable formats are not screened ("classify by hand, refuse if in doubt"). |
| 12 | Low | A bare-date availability means the end of the day UTC | Documented; callers can pass a time. Open. |
| 13 | Low | Look-ahead check skipped undated sources; `probability.by` was unchecked | Numeric sources need a date; `by` must be after `as_of`. |
| 14 | Low | STEO re-downloaded unreadable months every run | Skip list `data/obs/steo/_skip.json`. |
| 15 | Low | Daily job run time | Budgets cut (STEO, JODI, curve 90 s; ANP timeout 45 s). Check the first full run. |
| 16 | Low | `conditional()` assumed the last priced release was the latest; "Oct 24, 2026" was not read as a date; numpy values | Fixed all three. The 2006 era boundary follows Linn et al.'s date (June 2006, cited). |
| 17 | Low | Gas surprises use the revised storage series | Open (first-release values are an open question). |
| 18 | Low | "gas" or "storage" alone did not reach natgas | Keywords added. Commodities are ordered by hits. |
Tests: 30 specialist tests after the fixes (including regression tests for findings 1, 3, 4, 5, 6, 8, 10 and 11). The energy fixtures were re-checked against regenerated estimates (unchanged), and the live card re-validated against its pack.

## Open items
- **First Actions run:** check `fetch:eia_ng|prices_curve|steo|jodi|anp|eia_rigs` in `logs/runs.jsonl`. The STEO backfill resumes over runs (newest first). Check that ANP is reachable from a datacentre IP. The rig ids are unverified (EIA key-only API); a wrong id shows as a per-series error.
- Then `python -m pmstack events --write` to fill the gas table.
- **S2 needs:** about 250 days of curve contracts before an own estimate of inventory vs basis; the Cushing working-capacity series; the cross-product matrix; first-release WPSR values from EIA's issue archive.
- **Bernardo:** studies into `knowledge/inbox/`; confirm the architecture reading; the Docs updates below.

## PM Agent Plan (Docs) updates this session could not make
- Roster: agent 12 = "Research" (fundamentals pillar: orchestrator, specialists, generalist, testing gate); agent 13 "Quant" (new); agent 9 folded into the specialists; agent 10 = inbox ingestion.
- Schedule: specialists queue S0–S6 (S0 and S1 done 24 Oct).
- Links: the architecture drawing, `docs/research/specialists-architecture.md`, `docs/research/energy.md`.
- A Docs version of the Energy literature review (repo copy only so far).
