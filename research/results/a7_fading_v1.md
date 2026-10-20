# Narrative fading -> direction

Study `a7_fading_v1` · registered 2026-10-19 · spec 4b09ae74f9039325 · as of 2026-10-19 (data through 2026-10-19) · definition 21adf2c4d80f4c24 · verdict **in-sample only**

**Hypothesis (registered).** When a narrative is 'fading' (spread below -0.4 or 30% off its 8-week peak), its markets' next 20-day move relative to its direction differs from other days (two-sided).

**Source.** Larsen & Thorsrud (waves last months); agent 7

**Flag.** `narrative_stage` {"stage": "fading"}: agent 7 narrative stage == params.stage (spreading | peaking | fading | steady | dormant), on each market the narrative pushes, side = the narrative's sign for that market. Side = narrative sign.
**Outcome.** `signed` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +0.

| | value |
|---|---|
| independent episodes | 427 (193 source-date clusters, 13 sources) |
| first / last episode | 2017-09-01 / 2026-09-04 |
| episodes a year | 46.81 |
| mean side-signed move vs base | -0.179 vs 0.021 sd |
| excess | -0.201 sd; shrunk -0.192; after the 26% haircut -0.148 |
| t (episodes) | -2.83 |
| smallest excess these episodes can detect (80% power) | 0.176 sd |
| share moving with the side | 47.8% |
| placebo p (2000 circular shifts) | 0.0050 (placebo 5-95%: -0.132 to 0.115) |
| Bayesianized p (odds 4:1 / 1:1) | 0.072 / 0.019 |
| across the ledger (17 flag studies) | BH q 0.0850, BY q 0.2924, Holm p 0.0850, t >= 3: no |
| halves (split 2021-12-23) | -0.204 (n 216) · -0.197 (n 211) |
| one year dropped | -0.248 (without 2021) to -0.063 (without 2020) |
| against days in the same trend state | excess_sd -0.193 (427 episodes; 48.5% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.2).

**Hindsight.** This flag's definition was written on 2026-10-10 with this history in view, so its history can show at most 'in-sample only'; live episodes after that date decide.

**Verdict: in-sample only.** would be supported on its history, but its definition was written on 2026-10-10 with that history in view; 0 live episodes since (needs 20 with the same sign).

_LLM-in-sample: 427 of 427 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; its definition was written on 2026-10-10 with that history in view (verdict capped). Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
