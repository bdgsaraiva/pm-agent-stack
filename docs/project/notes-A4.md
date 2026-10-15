# Session notes A4 — Sizing assistant (agent 4), 9 Oct 2026

## Asked
"Go ahead with the sizing assistant. For this one like every assistant, first go through the most famous and discussed papers as well as the Atlas and specialized books and authors."

## Done
- Literature review → Docs: https://claude.ai/code/artifact/5e35dad7-b607-40ce-8e88-5466c037c3c8 ; repo `docs/research/sizing.md`.
- Papers used: Kelly/Thorp; MacLean, Thorp & Ziemba 2010; Baker & McHale 2013; Haghani & Dewey 2016; Haghani & White 2023; Antón, Cohen & Polk (Best Ideas, 2.8–4.5%/yr); Lamont/Acadian Mar 2025 (concentration ≠ alpha); Akepanidtaworn et al. 2023 JF (sells worse than random); Moreira & Muir 2017 vs Cederburg et al. 2020 JFE (103 strategies, no real-time gain) and Harvey et al. 2018 (no Sharpe gain in commodities/FX/bonds); Tetlock; Peters 2019.
- Books (general knowledge, not page-checked): Carver, López de Prado ch. 10, Vince, Tharp, Grinold & Kahn, Duke, Spitznagel, Donnelly.
- Atlas: Druckenmiller, Soros, Rokos, Tepper, Stuhlberger (size when right); Tudor Jones, Howard, Platt/Englander, Haidar (cut after losses); Kovner (exit first); Parker, Turtles (risk sizing, correlation limits); Thorp, Jakurski (fractions, survival); Atlas 3.1 (right 50–55%).
- Code (commit aad1bbc): `pmstack/sizing.py`; `config/journal.yaml` `sizing:` block; journal stores `sizing` + `size_suggested` on every long/short idea; flags no-edge, undersized-vs-suggestion, oversized, stop-in-noise, drawdown; CLI `journal size <id> [--write]`, `journal sizing-review` (suggested vs planned by conviction, R left on the table, Brier, R after exit). 27 tests pass. `/journal` skill shows the suggestion next to planned size.
- Worked sizes (priors, no record): conviction 3 at 2:1 = 1.0; conviction 5 at 1:1 = 0.75; conviction 5 at 4:1+ = 2.0 cap. Example Brent long (≈1.2:1, conviction 3) = 0.25.
- CLAUDE.md: literature-first rule; facts-vs-inference rule now allows size suggestions from sizing.py as advice.
- PM Agent Plan doc: agent 4 → Running; section 4 notes the build and the literature-first rule.

## USDA route (explained to Bernardo 9 Oct)
No MCP exists for USDA FAS (PSD, WASDE-linked data, export sales). Plan: balance keeper calls the FAS Open Data API (key from https://apps.fas.usda.gov/opendatawebV2/#/home → repo secret `USDA_FAS_API_KEY`) and NASS Quick Stats (key → `NASS_API_KEY`) from GitHub Actions. Optional ad-hoc MCP for NASS: kin5/nass-mcp-server (local) or the third-party pipeworx gateway (key handling unclear — not recommended for keys).

## Next
Agent 5 critic + number auditor, week of 19 Oct — literature review first (pre-mortems: Klein; base rates: Kahneman/Tetlock; red-teaming; Zweig/Mandala rules; LLM self-critique and verification papers).
