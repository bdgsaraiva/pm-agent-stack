# Self-reinforcing label -> continuation

Study `a7_label_self_reinforcing_v1` · registered 2026-10-19 · spec 2b8824ff46a4addc · as of 2026-10-19 (data through 2026-10-19) · definition f976d8296b2efce8 · verdict **no edge**

**Hypothesis (registered).** Markets labelled 'self-reinforcing' (trend, a spreading narrative the same way, CFTC leaning >= 70th percentile on that side) continue in the trend's direction over the next 20 trading days more than other days.

**Source.** Soros reflexivity (inference); Moskowitz, Ooi & Pedersen 2012; agent 7 labels

**Flag.** `consensus_label` {"label": "self-reinforcing"}: agent 7 consensus-map label == params.label (self-reinforcing | twilight | crowded | quiet | mixed) from its own trend vote, CFTC percentile and the DOC narrative stages; side = the trend direction. Side = trend direction.
**Outcome.** `signed` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +1.

| | value |
|---|---|
| independent episodes | 57 (57 source-date clusters, 8 sources) |
| first / last episode | 2017-09-01 / 2026-07-17 |
| episodes a year | 6.25 |
| mean side-signed move vs base | -0.063 vs 0.050 sd |
| excess | -0.113 sd; shrunk -0.083; after the 26% haircut -0.083 |
| t (episodes) | -0.81 |
| smallest excess these episodes can detect (80% power) | 0.345 sd |
| share moving with the side | 45.6% |
| placebo p (2000 circular shifts) | 0.6982 (placebo 5-95%: -0.366 to 0.267) |
| Bayesianized p (odds 4:1 / 1:1) | 0.800 / 0.500 |
| across the ledger (17 flag studies) | BH q 0.8501, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2022-01-28) | -0.287 (n 29) · 0.067 (n 28) |
| one year dropped | -0.208 (without 2024) to 0.006 (without 2021) |
| against days in the same trend state | excess_sd -0.160 (57 episodes; 100.0% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.25).

**Hindsight.** This flag's definition was written on 2026-10-10 with this history in view, so its history can show at most 'in-sample only'; live episodes after that date decide.

**Verdict: no edge.** placebo p 0.6982 > 0.05; BH q 0.8501 > 0.1 across the ledger; excess -0.113 sd short of +0.1; halves disagree [-0.287, 0.067]; gone without 2024 (-0.208).

_LLM-in-sample: 57 of 57 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; its definition was written on 2026-10-10 with that history in view (verdict capped). Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
