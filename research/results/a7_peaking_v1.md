# Narrative peaking -> direction

Study `a7_peaking_v1` · registered 2026-10-19 · spec 2518c41dd8e9ef54 · as of 2026-10-19 (data through 2026-10-19) · definition c09a3ada5c95462f · verdict **no edge**

**Hypothesis (registered).** When a narrative's 4-week attention is in the top 20% of its history ('peaking'), its markets' next 20-day move relative to its direction differs from other days (two-sided: continuation or 'priced in').

**Source.** Shiller's epidemic shape; Marks/Soros on consensus at extremes (inference); agent 7

**Flag.** `narrative_stage` {"stage": "peaking"}: agent 7 narrative stage == params.stage (spreading | peaking | fading | steady | dormant), on each market the narrative pushes, side = the narrative's sign for that market. Side = narrative sign.
**Outcome.** `signed` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +0.

| | value |
|---|---|
| independent episodes | 261 (117 source-date clusters, 12 sources) |
| first / last episode | 2017-09-15 / 2026-09-11 |
| episodes a year | 28.61 |
| mean side-signed move vs base | 0.117 vs 0.036 sd |
| excess | 0.082 sd; shrunk 0.076; after the 26% haircut 0.061 |
| t (episodes) | 1.13 |
| smallest excess these episodes can detect (80% power) | 0.179 sd |
| share moving with the side | 51.7% |
| placebo p (2000 circular shifts) | 0.3718 (placebo 5-95%: -0.148 to 0.145) |
| Bayesianized p (odds 4:1 / 1:1) | 0.729 / 0.402 |
| across the ledger (17 flag studies) | BH q 0.7023, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2022-05-13) | -0.100 (n 131) · 0.265 (n 130) |
| one year dropped | 0.002 (without 2025) to 0.135 (without 2019) |
| against days in the same trend state | excess_sd 0.077 (261 episodes; 62.8% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.2).

**Hindsight.** This flag's definition was written on 2026-10-10 with this history in view, so its history can show at most 'in-sample only'; live episodes after that date decide.

**Verdict: no edge.** placebo p 0.3718 > 0.05; BH q 0.7023 > 0.1 across the ledger; excess 0.082 sd short of +0.1; halves disagree [-0.1, 0.265].

_LLM-in-sample: 261 of 261 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; its definition was written on 2026-10-10 with that history in view (verdict capped). Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
