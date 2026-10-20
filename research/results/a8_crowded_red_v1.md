# Crowded under funding stress -> move against the crowd

Study `a8_crowded_red_v1` · registered 2026-10-19 · spec f4298080a4eac822 · as of 2026-10-19 (data through 2026-10-19) · definition b9818435ae73b77b · verdict **no edge**

**Hypothesis (registered).** Crowded positioning while funding is stressing (VIX >= 80th percentile or HY OAS +50bp in 21 days) is followed by a 1.5 sd move against the crowd over 20 trading days more often than other days.

**Source.** Brunnermeier & Pedersen 2009; Cheng, Kirilenko & Xiong 2015; agent 8 'crowded red'

**Flag.** `crowded_red` {"pct": 90}: crowded (cftc_crowded) while funding is stressing on the release day (agent 8 'crowded red': VIX at or above its 80th percentile since 1990, or HY OAS +50bp over 21 days). Side = crowded side.
**Outcome.** `adverse` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +1.

| | value |
|---|---|
| independent episodes | 170 (170 source-date clusters, 10 sources) |
| first / last episode | 2007-07-27 / 2026-03-13 |
| episodes a year | 8.78 |
| hits / expected | 16 / 12.42 |
| hit rate vs base rate | 9.41% (95% 5.88% to 14.74%) vs 7.31% |
| lift | 1.288; shrunk 1.258; after the 26% decay haircut 1.213 |
| binomial z | 1.06 |
| smallest lift these episodes can detect (80% power) | 1.74 |
| placebo p (2000 circular shifts) | 0.1904 (placebo 5-95%: 0.566 to 1.529) |
| Bayesianized p (odds 4:1 / 1:1) | 0.732 / 0.405 |
| across the ledger (17 flag studies) | BH q 0.5409, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2015-08-21) | 1.701 (n 88) · 0.839 (n 82) |
| one year dropped | 1.139 (without 2011) to 1.444 (without 2018) |
| against days in the same trend state | lift 1.311 (170 episodes; 87.6% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.3).

**Verdict: no edge.** placebo p 0.1904 > 0.05; BH q 0.5409 > 0.1 across the ledger; halves disagree [1.701, 0.839].

_LLM-in-sample: 170 of 170 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
