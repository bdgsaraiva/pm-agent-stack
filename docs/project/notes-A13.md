# Session notes A13: research loop (agent 12), 16–20 Oct 2026

Literature review (Docs): https://claude.ai/code/artifact/61591aa4-b36e-4808-a851-f5c74364f298 · repo: `docs/research/research-loop.md`
Branch: `agents-10-11` (= main after Bernardo's merge on 19 Oct), Claude Code on Bernardo's PC; pushed to main.

## Context
- **Gate 1 Nov not met** (1 journal entry, the example; 0 of 2 Friday reviews). Bernardo: "Build anyway".
- **His answers (19 Oct):**
  - "supported" = BH q ≤ 10% across every study + placebo p ≤ 5% (the literature's resolution);
  - fetch CFTC 2006–2019 once;
  - wiring = verdict tags in the Risk section and on the critic card (no alert added or removed).
- **Research:** three research sub-agents (multiple testing; replication, decay and binary flags; LLM look-ahead and AI loops), ~80 sources, the quant-research-standards skill, Atlas cards (Man AlphaGPT, Two Sigma, HRT, Harding, Bouchaud, Asness). Two passes and the reviewer hit the account's session limit and were resumed; one stalled on a watchdog.
- **Ownership:** no edit to consensus.py, sources.yaml, monitor.yaml, daily.yml or the morning note. The other session finished its merge of main into the branch (19 Oct) while this one was paused.
- **Disclosure:** an engine smoke run on 16–19 Oct printed preliminary numbers for 7 flags and TSMOM before they were registered. Their outcome, horizon and direction were fixed in the build plan before that run and not changed; each such registration carries a `smoke_seen` note.

## What the evidence said (short)
- **Count every trial:** HLZ t > 3 for a literature with hidden tests; with our own ledger, the exact N and BH (Chen; JKP); DSR reproduced to 4 digits (0.9004 / 0.9505).
- **Binary flags:** lift against the base rate on independent episodes (KLR; Berg & Pattillo: 37% vs 24% out of sample, 63% false alarms); expect ~1.5 lifts.
- **Decay:** −26% out of sample, −58% after publication (McLean & Pontiff).
- **COT:** positions follow trends; no lead (Sanders, Irwin & Merrin); dated at the Friday release (Wang).
- **TSMOM:** MOP vs Huang et al. (≈ the historical mean); AQR cost table (Hurst, Ooi & Pedersen).
- **LLMs:** GPT-4o recalls S&P levels to 0.61% before its cutoff (Lopez-Lira, Tang & Zhu); "forget" prompts fail (Sarkar & Vafa); frozen hypothesis and sign at Man.

## What shipped
**Agent 12 — research loop** (`pmstack/research.py`, `pmstack/qstats.py`, `config/research.yaml`, `research/`, skill `.claude/skills/research/` + `/research`)
- **Registry:** `research/studies/<id>.yaml`, validated (no result fields), hashed at registration into `research/ledger.jsonl`; an edit is a new id; unregistered specs refused; a no-write run is a "peek" line; each registration carries the drafting model's recall probe.
- **Flags, point in time, with the agents' own functions** (weekly grid): narrative stage (consensus.stage_of on the last valid day), consensus labels (trend, positioning, _label), CFTC crowded / crowded entry / crowded red (dated at the release, Monday in holiday weeks), CTA roll-off flip / state / vol shrinking / panic (risk.cta_levels), turbulence persistence.
- **Event study:** vol-scaled outcomes from the first close after the data were public; episodes collapsed (gap ≥ h); same-market, same-side, same-window base rates; lift or excess; shrunk (n0 = 20) and decay-haircut effects; Wilson interval; minimum detectable lift; trend-state-matched lift; halves; drop-one-year; live episodes since the rule was frozen.
- **Inference:** circular-shift placebo, one calendar shift per draw for every source; BH across every registered flag study (missing at p = 1), its own family for the opposite direction; Holm, BY, Bayesianized p, signed HLZ t beside it.
- **Verdicts:** supported / no edge / reversed / in-sample only (hindsight-written definitions until 20 live episodes agree) / insufficient; strategies supported / decayed / no edge. A definition hash (config + code) frozen at the first hashed run blocks "supported" if it changes. The index rewrites every result page with its final verdict and keeps the graveyard.
- **Strategy:** time-series momentum (MOP 2012) with variants, alpha vs the long-only and historical-mean books (HAC), AQR cost table swept 0–4×, deflated Sharpe over every registered variant, the paper's sample / after it / after publication.
- **Data:** CFTC disaggregated 2006–2019 fetched once (14 year files in `data/obs/cftc/`, 49,560 rows; no edit to sources.yaml).
- **Wiring:** Risk section line "Measured by the research loop" under the CTA table and a `measured` field per idea (`risk._research_tags`, `_measured`); critic facts `research.crowded`, `research.label`, `research.spreading` (`critic._research_fact`); all point in time; the risk caption says no crowding or CTA flag alerts unless supported.
- **Tests:** `tests/test_research.py`, 29 offline tests (DSR worked examples, look-ahead walls, planted vs random flags, copied-null placebo, agents' own numbers, registry freeze, verdict rules, wiring).

## Results (as of 19 Oct, data through 16 Oct)
- **No agent 7 or 8 flag may alert.** 16 of 17 flag studies are no edge.
- **Fading narratives** (their markets move against the narrative): excess −0.20 sd on 427 episodes, both halves −0.20, placebo p 0.005, BH q 0.085 → **in-sample only** (definitions written 10 Oct with the history in view; needs 20 live episodes).
- Twilight label lift 1.95 on 69 episodes (BH q 0.391); persistent turbulence lift 1.85 on 57 (placebo p 0.084); spreading narratives lean the opposite way (excess −0.16 sd), failing BH there.
- **CFTC crowded** 2007–2026: lift 1.00 (7.50% vs 7.49%) on 360 episodes. CTA roll-off excess 0.01 sd on 8,290 episodes.
- **TSMOM** 1987–2026: Sharpe 0.63 after costs; alpha t 2.21 vs the long-only book (below the t ≥ 3 bar for an imported idea); DSR 0.58; Sharpe 0.77 in the paper's sample, 0.51 after publication → no edge.

## Independent review: 18 defects (3 High, 9 Medium, 6 Low), all fixed
Details in `docs/research/research-loop.md` §9. The High ones: per-source placebo shifts (a copied null flag rejected 23% at 5%), result pages keeping a partial-family verdict, and "reversed" skipping the gate. Each has a regression test.

## Checks
- **Own test set:** before (16 Oct, 3 runs) pass^3 18 of 20; after (20 Oct) 19 of 20; `new_worse` empty → accepted (logged `evals:compare`). The research skill text changed after the after-runs (verdict list, quoting rule); no eval task uses it.
- **Full suite:** 243 passed before the review fixes; re-run after them (see the commit).
- **Auditor:** a sample summary of two studies matched 10 of 10 figures against their result JSON (the result JSON carries `audit_subject`).

## Open items
- **Bernardo:** the PM Agent Plan doc: roster row 12 → Running (trigger `/research`; inputs: the research memory and the agents' functions; job: test flags and papers, verdict + graveyard), and the per-agent section with the review link. Not changed from this session.
- **Other session (notes and keys):** backdated packs in a CFTC holiday week (release on Monday) let `consensus.positioning`, `risk.crowding` and the monitor's `positioning_extreme` use a report before its release (lag 3 days from Tuesday); live packs are not affected because the fetch runs before the release. The monitor's positioning alerts also have no release lag at all. The research loop dates flags at the true release.
- **Agent 12 v2:** a quarterly re-run of every study (live episodes accumulate; fading narratives could lift its cap); the Friday review could list verdict changes; PBO when a study sweeps a grid; a cost multiplier on stress days; a token-probability recall test if an endpoint exposes it; agent 9's balances as flags (GHR low-inventory signal).
- **Gate numbers to revisit with Bernardo** once 10+ more studies exist: min_lift 1.25, min_excess 0.10 sd, the V[SR] floor.
