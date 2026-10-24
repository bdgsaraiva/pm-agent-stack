# Kickoff brief: specialist agents on the Donnelly pillars

Written 24 Oct 2026 in the claude.ai Project chat, for a Claude Code session on the repo `bdgsaraiva/pm-agent-stack`. The paste prompt is at the end.

Architecture literature review (Docs, with diagrams): https://claude.ai/artifact/9xswr5TNBCGb86wogRrTrB. If the session can't open Docs links, §2 below holds everything it needs.

---

## 0. First steps in the session

1. **Save this brief.** Save it as `docs/project/specialists-kickoff.md` and commit it.
2. **Read, in this order:**
   - `docs/project/agents-plan.md`
   - `docs/project/agent-build-kickoff.md` (its §3 workflow and §5 rules still apply)
   - the latest `docs/project/notes-A*.md`
   - `CLAUDE.md`
   - then run `python -m pytest -q`
3. **Check the gate.** The 1 Nov gate needs 10 paper ideas and 2 Friday reviews; check with `python -m pmstack journal stats`. If it isn't met, say so in one line and ask once: build anyway, or wait.
4. **Check the parallel track.** The "notes, narratives and keys" track owns the morning note, `pmstack/consensus.py`, the news and BigQuery adapters, `config/sources.yaml`, `config/monitor.yaml` and `.github/workflows/daily.yml`. Find out from `agents-plan.md` and the git log whether it is still active.
   - If it is active, stay out of those files: write specs for it and leave the code to it.
   - If it is closed, this session owns them; say so in `agents-plan.md`.

## 1. Goal and decisions (Bernardo, 24 Oct)

The next phase builds specialist agents for commodity and macro knowledge, plus market tracking. The architecture follows Brent Donnelly's pillars ("Trade Outside the Box"). The derivatives box sits inside the quant pillar.

| Pillar | What it is | Runs |
|---|---|---|
| **Fundamentals** | An orchestrator routes a question to read-only specialists: Energy, Metals, Ags, Macro context. A research generalist combines their state cards. | Ad hoc, when Bernardo asks. A no-model job files new releases into memory on report days. |
| **Behavioral** | One narrative agent. It evolves the morning note's consensus map so it measures narratives that are starting, growing, peaking or fading. | Morning now; also at the close later. |
| **Technical and quant** | One quant agent over a code library, not an orchestrator with specialists. Modules: trend and CTA levels, carry and curve, volatility and options, correlation and regime, seasonality, positioning. | After the close; the morning note carries only the overnight change. |

The existing agents stay downstream: critic, sizing, risk and crowding, weekly review, journal. Bernardo decides; sizing and execution stay human.

**Recommendations Bernardo accepted:**
- **Quant agent.** One agent over a code library. Volatility and options is the first module to split into its own sub-agent, once it needs its own knowledge base.
- **Specialist layers.** One layer under the generalist now, two at most later. Add an asset-class layer only where a class has 3+ specialists with real cross-links.
- **Specialist depth and merging.** Start with deep specialists (Energy, Metals, Ags). Later merge them into one Commodities specialist, but merge the routing, not the knowledge. The knowledge stays in files organised by commodity.
- **Knowledge.** Free sources, the literature and Bernardo's own studies, plus a search for sources that put us ahead of the average specialist.
- **Bloomberg.** Terminal data stays off the laptop and out of the repo, because the Desktop API licence keeps data on the authorised computer.
  - Licensed routes later, in the corporate lane: Bloomberg Enterprise MCP on Data License Plus, or Trading Technologies.
  - Data adapters stay swappable.

## 2. What the literature says, and the design rules it gives

| Finding | Design rule |
|---|---|
| LLM agent systems built like trading firms (TradingAgents 2024, FinCon NeurIPS 2024, AlphaAgents 2025) show gains only on short equity backtests. FINSABER (2025) finds the gains deteriorate over 20 years and 100+ symbols. Profit Mirage (2025): almost every published agent fails to beat random once past the model's knowledge cutoff. | No LLM trade timing. Signals are computed in code; agents explain and flag. Evaluate forward only. |
| The only controlled commodity test (Wang et al., Jun 2026): LLM tilts beat a fixed rule by +0.04 Sharpe (p 0.07–0.09) on 15 commodity ETFs. Debate did not beat the best single agent. Debate or Vote (NeurIPS 2025): voting explains most of debate's gains. | The LLM is a constrained interpretation layer that returns a JSON contract. Average independent views; no free debate. The existing critic stays the targeted challenger. |
| Kim et al. (2025, 180 setups): an orchestrator that reviews sub-agent work holds error amplification to 4.4× (17.2× for agents that don't check each other). Multi-agent setups lost 39–70% on sequential reasoning, and tool-heavy tasks pay the most overhead. Anthropic's research system: +90.2% on breadth tasks at ~15× chat tokens. Cognition: share full context; parallel writers stay fragile. MAST (NeurIPS 2025): failures come from loose specs, misalignment between agents, and weak verification. | One orchestrator; specialists are read-only; one writer to memory. Explicit task specs, a verifier (the number auditor) and stop rules. Parallel specialists only for breadth sweeps. Depth of two layers at most. |
| Agent Skills (Anthropic 2025): expertise lives in folders that load only when relevant. Bloomberg's Enterprise MCP (29 Sep 2026) ships data plus "skills" and calls data readiness the bottleneck. | Specialists are skill folders plus memory, not fine-tuned models. They improve with each new model. |
| FinMem (2023): memory in layers by horizon. FinCon: lessons from P&L go only to the analyst concerned. Zep/Graphiti (2025): bi-temporal facts that are invalidated, not deleted. | Point-in-time memory with valid-from, valid-to and recorded-at dates. Journal lessons are routed to that commodity's notes. |
| Beyond Polarity (2026): LLM scores on energy news for relevance, intensity, uncertainty and forwardness add weekly WTI information. Intensity and uncertainty matter most. | The narrative agent scores those dimensions, not just tone. Scores go to the research loop (agent 12) as features. |

## 3. Target architecture

### 3.1 Shared foundations (built first)
- **Point-in-time memory: a DuckDB table `facts`.**
  - Columns: `subject`, `predicate`, `value`, `unit`, `valid_from`, `valid_to`, `recorded_at`, `source_url`, `source_type`, `confidence`, `author`.
  - Nothing is overwritten. A new fact supersedes the old one by setting the old one's `valid_to`.
  - Add an `as_of(date)` query and tests proving no look-ahead.
  - Only code functions write to it, always with provenance.
- **State card.**
  - A JSON schema with a validator, in `config/state_card.schema.json`.
  - Fields: subject, as-of date, balance view, curve shape, positioning, narrative stage, what changed, what would change the view, next events, stated probability (optional), confidence, sources (each figure with its link), author.
  - The same schema at every level: a Commodities card = the commodity cards + a cross-links section.
- **Routing in config: `config/agents.yaml`.** It maps question types and commodities to specialists. Adding or removing a layer is a config change, a router prompt and a test run.
- **Knowledge folders, by commodity, never inside a prompt:**
  - `knowledge/<complex>/<commodity>/` holds:
    - `primer.md`: contracts, delivery, spreads that matter, seasonality, report calendar;
    - `drivers.md`: testable claims with sign, lag and source;
    - `balance.md`: a template, with each line tied to a public series;
    - `events.md`: playbooks per scheduled report, with reaction base rates computed by code;
    - `analogues.md`, linked to agent 8's stress library;
    - `lessons.md`, from closed journal ideas;
    - `open-questions.md`.
  - `skills/specialist-<complex>/SKILL.md` is the index, loaded by progressive disclosure.
  - `knowledge/commodities/cross-links.md` (biofuels, fertiliser and gas, power and aluminium, freight) exists from day one and is owned by the generalist.
- **Source registry: `knowledge/sources.md`.** One row per source: free or paid, licence for personal use, reachable from GitHub Actions, history length, release time, whether vintages exist.

### 3.2 Fundamentals pillar
- **Specialists:** Energy (crude, products, natural gas); Metals (gold, copper, aluminium, iron ore); Ags (corn, soybeans, wheat, sugar); Macro context (US rates, USD, US equities, as context for commodities).
- **Read-only.** Specialists read memory, knowledge and the fact pack, and return a state card. They never write files themselves; code saves their cards.
- **Orchestrator plus research generalist,** triggered by a `/research <question>` command. The generalist answers from the cards and the cross-links file, with sources, and passes the number auditor.
- **Weekly breadth sweep (optional, later).** All specialists in parallel, one card each. Off by default; it costs tokens.
- **Agent 9 (balance keeper) folds into the specialists.** The balance templates live in `balance.md`.

### 3.3 Behavioral pillar: the narrative agent
- **Lifecycle stages** (starting, growing, peaking, fading) are defined by measured rules on attention share, its acceleration, breadth of sources, tone and the dimension scores in §2. They are tested on history before any stage alerts.
- **Seed reading:** Shiller, *Narrative Economics* (contagion models); Bybee et al. (news attention); the existing `docs/research/consensus.md`.
- **Output:** a narrative tracker, with one running record per narrative (stage, since when, what moved it, top linked headlines).
- If the parallel track is active, this session writes `docs/project/narrative-agent-spec.md` and leaves the code to that track.

### 3.4 Technical and quant pillar
- **Code library `pmstack/quant/`,** with modules for trend and CTA levels (reuse agent 8), carry and curve, volatility and options, correlation and regime (reuse `risk.py`), seasonality, and positioning (CFTC from the Friday release).
- **The quant agent reads one table and writes a "tape card":** what is stretched, what flipped, what changed against vol, all with figures from code.
- **When to split a module:** when it needs its own knowledge base, or its output no longer fits one read. Volatility and options is the first candidate.

### 3.5 Run times
- **Quant, after the close.**
  - A new workflow `.github/workflows/close.yml`, owned by this track, started by a scheduled task near 19:10 BRT on weekdays. That is after the CME daily close in both US clock regimes (US clocks change on 1 Nov). GitHub's own cron runs hours late, which was the 14 Oct lesson.
  - It writes `briefs/<date>/quant.md|json`.
  - The morning note reads only the overnight change against those levels. That change goes to the parallel track as a request if it is active.
- **Report-day filing.** The no-model job runs in the same workflow on report days.
- **Budgets.** Give each new data source a time budget. Check the GitHub Actions minutes for a second weekday run.

## 4. Knowledge base

- **Inbox: `knowledge/inbox/`,** for Bernardo's studies and selected reports.
  - Before ingesting any file, confirm its type.
  - His own non-fund studies and public reports (agencies, central banks, academic work) are fine.
  - Broker or sell-side research and anything from the fund are not. Don't read those beyond what is needed to classify them, store nothing from them, and ask him to remove them. That includes summaries or extracts of broker reports made elsewhere, such as with the corporate account.
  - Bernardo's own notes in his own words are fine: frameworks, which drivers matter, and which public data sources are worth tracking, even if he first met them in broker research. They must carry no broker figures, forecasts, charts or text.
  - Every quantified relationship in `drivers.md` (e.g. price or timespread response per unit of supply, demand or inventory change) records where its size came from:
    - `literature` (cited paper or agency study);
    - `own estimate` (computed by code from public data, point-in-time, with the regression stored);
    - `Bernardo prior` (his experience, to be tested).
    - A broker's own quantified sensitivity is never copied in.
    - Where a prior and the estimate disagree, flag it as an open question.
  - Broker-informed knowledge belongs to a later corporate copy of these specialists (same folder layout, corporate account), not to this repo.
- **Ingestion is agent 10 (research digester), folded in here.** For each document:
  - a summary in his podcast-summary format: key messages; then numbers and arguments; consensus vs contrarian; confidence; horizon;
  - its testable claims extracted into `drivers.md`, each with its source;
  - its facts filed in memory with their dates.
- **Edge-source hunt.** Verify each candidate against the registry fields in §3.1, and record the ones that pass. The Brazil-origin data is the likely edge. Candidates (not yet checked):

| Complex | Candidates |
|---|---|
| Energy | EIA weekly and STEO, JODI, OPEC monthly report, Baker Hughes rig count, ANP (Brazil) |
| Metals | LME stocks, SHFE weekly stocks, China customs trade, USGS |
| Ags and sugar | USDA (WASDE, export sales, crop progress, PSD), Conab, UNICA, Secex export data, US Drought Monitor |
| Cross-cutting | NOAA ENSO, ECMWF open data, Copernicus Sentinel imagery, FAO AMIS, World Bank Pink Sheet, ALFRED vintages |

## 5. Build order (one phase per session unless small; literature first for each)

| Phase | Builds | Seed reading (verify; add the most cited work they miss) |
|---|---|---|
| S0 | Foundations (§3.1), inbox ingestion (agent 10), state-card validator. Commit `docs/research/specialists-architecture.md` from §2 and the Docs review | Already reviewed (§2) |
| S1 | Energy specialist + EIA report playbook with reaction base rates | Kilian (2009); Baumeister & Kilian (2016); Hamilton (2009); Working (1949) and the theory of storage; Fama & French (1987); Gorton, Hayashi & Rouwenhorst (2013); EIA and OPEC methodology; Atlas cards (Andurand, Hall, King) |
| S2 | Quant agent + `close.yml` + scheduled task | Moskowitz, Ooi & Pedersen (2012); Hurst, Ooi & Pedersen (2017); Koijen et al. (2018) carry; Erb & Harvey (2006); Szymanowska et al. (2014); Bakshi, Gao & Rossi (2019); Trolle & Schwartz (2010) energy variance premia; Hong & Yogo (2012); quant-research-standards skill |
| S3 | Metals specialist | Stuermer (2018); Erten & Ocampo (2013) supercycles; LME and SHFE stock data; China demand and power-cost literature |
| S4 | Ags specialist (needs `USDA_FAS_API_KEY` and `NASS_API_KEY`, which Bernardo adds before 14 Dec) | Adjemian (2012) and Isengildina-Massa et al. on WASDE; weather and ENSO; Conab and UNICA methods |
| S5 | Macro context specialist (lighter) | Existing FRED and consensus material |
| S6 | Orchestrator, research generalist, cross-links file, `/research` command | §2 |
| Later | Narrative agent (or its spec, §3.3); merge into Commodities when the rule in §6 holds; split vol and options; agent 11 (network and reputation); agent 12 (research loop) tests every flag's base rate and lift | |

Update the queue in `agents-plan.md` to this order.

## 6. Evaluation and the merge rule

- **Per-commodity test set from S1.**
  - About 20 dated questions per commodity, with known answers from public material.
  - Re-run before any change to the model, prompt or knowledge layout.
- **Forward-only scoring:**
  - explanations that held the next day;
  - flags that came before 2-sd moves (base rate and lift, via agent 12);
  - Brier score on stated probabilities.
- **No LLM backtest on dates the model may have read.** If a historical check is unavoidable, mask the dates.
- **Merge rule.** Merge Energy, Metals and Ags routing into one Commodities specialist when all three hold:
  - each specialist passes its test set;
  - the combined SKILL.md index fits the context budget;
  - cross-commodity questions are frequent.
  - The merge ships only if test scores hold.
- **Number auditor.** It runs on every written output.

## 7. Rules (unchanged from `agent-build-kickoff.md` §5, plus three)

- **Personal build.** Paper ideas and public data only. No fund positions, P&L, orders, broker research or proprietary notes.
- **Code computes, the model writes.** Specialists are read-only. Agents ask questions; Bernardo decides; no trade instructions.
- **Focus markets.** Commodities, US equities, US rates, USD. Standing fact: dated Brent has traded far above futures all through 2026 (Iran war); it is not a data error.
- **Never handle keys.** Tell Bernardo where to add GitHub secrets.
- **Asking.** Ask at most once per phase, multiple choice, recommended option first. Keep chat replies short; findings go in the docs.
- **Pushing.** Run `git pull --rebase` and the full test suite before every push. Tests never depend on the real date or on test order.
- **Look-ahead.** Anything with `--date` uses only what was known on that date; test it.
- **New: Bloomberg.** No Bloomberg Terminal data in the repo, prompts or logs (Desktop API licence).
- **New: specialists don't write.** Memory writes go only through code functions that carry provenance.
- **New: no knowledge in prompts.** Domain knowledge never lives in a prompt; it lives in `knowledge/`, so routing can change without a rebuild.

## 8. Hand-off per phase

- Commit and push.
- Update `docs/project/agents-plan.md` (status, decisions, queue) and write `docs/project/notes-A<n>.md`.
- Update `CLAUDE.md` and the README.
- Update any scheduled task prompt that should use the new agent. When creating a task, say which approval setting it got.
- List the Docs updates the session couldn't make (PM Agent Plan roster).
- End with 2–3 lines in chat: what shipped, and what comes next.

---

## Paste this into a new Claude Code session on the repo

```
Start the specialist-agents phase of my "Future of Asset Management and Trading" project. The brief is the file I'm attaching (specialists-kickoff.md): save it as docs/project/specialists-kickoff.md, commit, and follow it.
Architecture: Donnelly pillars — fundamentals (orchestrator + read-only Energy, Metals, Ags and Macro-context specialists + a research generalist, ad hoc), one narrative agent, one quant agent over a code library (after the close). Knowledge lives in files by commodity; point-in-time memory; code computes, the model writes; I decide.
Start with phase S0 (foundations + inbox ingestion), then S1 (Energy). Check the 1 Nov gate first and ask once if it isn't met. Literature first for each phase, at most one multiple-choice round, then build, test, live run, and hand off as the brief says.
CLAUDE.md has the hard rules. Personal build only. Check whether the notes-and-keys track is still active and stay out of its files if it is.
```
