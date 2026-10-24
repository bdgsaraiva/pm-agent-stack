# Specialist agents: architecture review and design rules (S0)

Written 24 Oct 2026 for phase S0 of the specialists build (`docs/project/specialists-kickoff.md`). The literature was reviewed in the claude.ai Project chat on 24 Oct (Docs, with diagrams: https://claude.ai/artifact/9xswr5TNBCGb86wogRrTrB). This file is the repo copy of its findings and of the design that follows from them. **Proposed total architecture (drawing):** https://claude.ai/artifact/Bz9g7sbKwn5truYMPQmpct (repo copy `docs/project/architecture-total.html`).

The brief marks S0's reading as "already reviewed (section 2)". The rows below carry that review forward unchanged. This session did not re-open the papers, so its figures are the Project review's and are marked as such. S1 onward re-opens every source it uses.

## 1. Findings and what they change

| Finding (source as reviewed in the Project chat) | What it changes here |
|---|---|
| LLM agent systems built like trading firms (TradingAgents 2024; FinCon, NeurIPS 2024; AlphaAgents 2025) show gains only on short equity backtests. FINSABER (2025): the gains deteriorate over 20 years and 100+ symbols. Profit Mirage (2025): almost every published agent fails to beat random once past the model's knowledge cutoff. | No LLM trade timing. Code computes the signals; agents explain and flag. Evaluation is forward only (section 6 of the brief). |
| The only controlled commodity test (Wang et al., Jun 2026): LLM tilts beat a fixed rule by +0.04 Sharpe (p 0.07–0.09) on 15 commodity ETFs, and debate did not beat the best single agent. Debate or Vote (NeurIPS 2025): voting explains most of debate's gains. | The LLM is a constrained interpretation layer that returns a JSON contract (the **state card**). Independent views are averaged with no free debate. The critic (agent 5) stays the targeted challenger. |
| Kim et al. (2025, 180 set-ups): an orchestrator that reviews sub-agent work holds error amplification to 4.4× (17.2× when agents don't check each other). Multi-agent set-ups lost 39–70% on sequential reasoning, and tool-heavy tasks pay the most overhead. Anthropic's research system: +90.2% on breadth tasks at ~15× chat tokens. Cognition: share full context, because parallel writers stay fragile. MAST (NeurIPS 2025): failures come from loose specs, misalignment between agents and weak verification. | One orchestrator. Specialists are read-only, and code is the one writer to memory. Explicit task specs (the router names the specialist, question type and files), a verifier (card validator + number auditor) and stop rules. Parallel specialists only for breadth sweeps (off by default). Two layers at most. |
| Agent Skills (Anthropic 2025): expertise lives in folders that load only when relevant. Bloomberg Enterprise MCP (29 Sep 2026) ships data plus "skills" and calls data readiness the bottleneck. | Specialists are skill folders plus memory (`skills/specialist-<complex>/`, `knowledge/<complex>/<commodity>/`), not fine-tuned models, so they improve with each new model. No knowledge lives in prompts. |
| FinMem (2023): memory in layers by horizon. FinCon: lessons from P&L go only to the analyst concerned. Zep/Graphiti (2025): bi-temporal facts that are invalidated, not deleted. | Point-in-time memory: `pmstack/facts.py`, with valid time, knowledge time (available_at, recorded_at), supersession without deletion, and `as_of(date)`. Journal lessons go to that commodity's `lessons.md`. |
| Beyond Polarity (2026): LLM scores on energy news for relevance, intensity, uncertainty and forwardness add weekly WTI information, with intensity and uncertainty mattering most. | The narrative agent (agent 7) scores those dimensions, not just tone, and the scores go to the testing gate as features. The spec goes to the notes track while it is active. |

## 2. Merged architecture (Bernardo, 24 Oct: "Agent 12 will become the orchestrator + the specialists")

The 12-agent roster and the three pillars merge as follows (drawing linked above):

- **Writers (code only):** data pipeline (1) with a new close run; report-day filer (new, no model); inbox ingestion (10, the digester); lessons router.
- **Memory:** market data (Parquet + DuckDB, fact packs); the facts table (new, point in time); knowledge by commodity (new); journal and saved cards.
- **Fundamentals pillar = agent 12 "Research":** `/ask` reaches the orchestrator, which routes by `config/agents.yaml` to the read-only Energy, Metals, Ags and Macro-context specialists; the research generalist combines their cards with `knowledge/commodities/cross-links.md`. The existing research loop becomes the pillar's **testing gate** (`/research`, unchanged). It tests driver "own estimates" against literature and Bernardo's priors, and it measures every pillar's flags for base rate and lift before any may alert. Balances (ex agent 9) live in each commodity's `balance.md`.
- **Behavioral pillar = agent 7 "Narratives":** discovery → selection with Bernardo → lifecycle tracker (starting, growing, peaking, fading) → news dimension scores. The notes track owns its code while active.
- **Technical and quant pillar = agent 13 "Quant" (new):** one agent over `pmstack/quant/` (trend and CTA levels from agent 8, carry and curve, volatility and options, correlation and regime from `risk.py`, seasonality, positioning), writing a tape card after the close. Volatility and options splits off first.
- **Outputs and decision loop (unchanged, downstream):** morning note (2), close tape, `/ask` answers, Friday review (6); journal (3) → critic (5, reads state cards) → sizing (4) → risk and crowding (8) → weekly review (6) → lessons.
- **Verification on every output:** number auditor, state-card validator, own test set plus ~20 questions per commodity, forward scoring (explanations that held, flags before 2-sd moves, Brier), run log.
- **Outside the repo:** network and reputation (11), private repo. The specialists' open questions feed its call prep.

Command decision (Bernardo, 24 Oct): `/ask energy: <question>` goes to one specialist from S1, and plain `/ask <question>` goes to the orchestrator from S6. `/research` stays the testing gate.

## 3. S0 design, as built

| Piece | File | Rule it enforces |
|---|---|---|
| Facts log | `data/facts/facts.jsonl`, `pmstack/facts.py` | Append-only JSON lines, merged by git like the run log. `record()` requires a `pmstack.*` writer, `source_url` and `source_type`. Two clocks: `valid_from/valid_to` (the world) and `available_at` (public from; backfills carry the real release date) plus `recorded_at` (the repo's write time, for audit). A newer fact closes the old one's `valid_to`, derived on read so earlier reads still see it open. A revision with the same `valid_from` wins from its own `available_at` (vintages). `as_of(d)` = facts true on d and public by the end of d. DuckDB view `facts` via `facts.connect()`. |
| State card | `config/state_card.schema.json`, `pmstack/cards.py` | Same schema at every level (commodity, complex, generalist; a complex card lists `children` and `cross_links`). Validator: schema (dependency-free subset), no source dated after `as_of`, every `[sN]` cited exists, and **every number in a text field equals a cited source value** (windows like "4-week" and plain years excepted). `save` never overwrites. |
| Routing | `config/agents.yaml`, `pmstack/route.py` | Code picks the specialist (explicit `energy:` prefix wins, else keyword hits), the question type and the knowledge files to load. Planned specialists answer "not built yet". Questions for another pillar are pointed there. Adding a layer = config + router prompt + test run. |
| Knowledge | `knowledge/` (README, `_template/`, `sources.md`, `commodities/cross-links.md`), `pmstack/knowledge.py` | Drivers in `drivers.yaml` (code-written) rendered to `drivers.md`. Each size is `literature` (source + url), `own_estimate` (stored regression + as_of) or `bernardo_prior` (only through the confirm step). Broker names in a size are refused. `knowledge check` writes prior-vs-estimate disagreements (opposite sign, prior outside the interval, or >50% apart) into `open-questions.md`. Every size is also a dated fact. |
| Inbox | `knowledge/inbox/`, `pmstack/inbox.py` | Screen the first pages only, then Bernardo confirms the type. Broker or fund files are refused: not read further, the ledger keeps only the hash, and he is asked to delete them. Allowed files go through the digester (summary in his podcast format, checked claim cards). His numbers are proposed priors that he confirms one by one (decision 24 Oct: "Inbox + confirm"). Facts from a document are filed only when the number is inside a checked card's quote. |

## 4. Open points

- **Agent numbering:** "Quant" takes 13. Agent 9's code (`balance.py`) stays; its knowledge moves into each specialist's `balance.md`.
- **The narrative agent spec** (`docs/project/narrative-agent-spec.md`) is written for the notes track while that track is active (section 3.3 of the brief).
- **Re-check in S1:** the Project review's figures above (Kim et al. 4.4×/17.2×; Anthropic +90.2%; Wang et al. +0.04 Sharpe) are quoted from it. S1 re-opens only what it uses.
