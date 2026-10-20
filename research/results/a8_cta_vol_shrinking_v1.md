# Vol-target books shrinking -> direction

Study `a8_cta_vol_shrinking_v1` · registered 2026-10-19 · spec 406138c0a5097f39 · as of 2026-10-19 (data through 2026-10-19) · definition 535a897566e5f2eb · verdict **no edge**

**Hypothesis (registered).** When slow/fast vol < 0.7 (vol-targeted trend books cutting size with no flip), the next 20-day move relative to the trend vote differs from other days (two-sided).

**Source.** Harvey et al. 2018 (vol targeting); agent 8

**Flag.** `cta_vol_shrinking` {}: agent 8 vol-target channel: slow/fast vol < 0.7 (vol-targeted trend books shrinking with no flip); side = the trend vote's direction. Side = trend vote direction.
**Outcome.** `signed` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +0.

| | value |
|---|---|
| independent episodes | 39 (39 source-date clusters, 18 sources) |
| first / last episode | 2006-04-28 / 2026-02-06 |
| episodes a year | 0.96 |
| mean side-signed move vs base | 0.026 vs -0.019 sd |
| excess | 0.045 sd; shrunk 0.030; after the 26% haircut 0.033 |
| t (episodes) | 0.43 |
| smallest excess these episodes can detect (80% power) | 0.262 sd |
| share moving with the side | 53.8% |
| placebo p (2000 circular shifts) | 0.7771 (placebo 5-95%: -0.410 to 0.380) |
| Bayesianized p (odds 4:1 / 1:1) | 0.794 / 0.490 |
| across the ledger (17 flag studies) | BH q 0.8501, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2020-03-13) | 0.180 (n 24) · -0.170 (n 15) |
| one year dropped | -0.048 (without 2008) to 0.137 (without 2020) |
| against days in the same trend state | excess_sd 0.005 (39 episodes; 89.7% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.2).

**Verdict: no edge.** placebo p 0.7771 > 0.05; BH q 0.8501 > 0.1 across the ledger; excess 0.045 sd short of +0.1; halves disagree [0.18, -0.17]; gone without 2008 (-0.048).

_LLM-in-sample: 39 of 39 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
