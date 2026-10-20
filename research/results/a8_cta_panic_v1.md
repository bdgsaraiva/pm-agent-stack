# Panic state -> trend side loses

Study `a8_cta_panic_v1` · registered 2026-10-19 · spec c46dc37034bbe0e0 · as of 2026-10-19 (data through 2026-10-19) · definition 2aca7bd93c6d4bb7 · verdict **no edge**

**Hypothesis (registered).** In a panic state (24-month return < 0, 126-day vol >= 80th percentile of ~3 years) the next 20-day move on the 12-month trend's side is worse than on other days (momentum crashes).

**Source.** Daniel & Moskowitz 2016 (momentum crashes in panic states); agent 8

**Flag.** `cta_panic` {}: agent 8 panic state (Daniel & Moskowitz): 24-month return < 0 and 126-day vol at or above its 80th percentile of ~3 years; side = the 12-month sign; params.only = short scores only a down 12-month trend, as the live flag ("rebound risk on a with-trend short") does. Side = 12-month trend sign.
**Outcome.** `signed` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: -1.

| | value |
|---|---|
| independent episodes | 180 (180 source-date clusters, 21 sources) |
| first / last episode | 1988-01-08 / 2026-06-18 |
| episodes a year | 4.44 |
| mean side-signed move vs base | 0.045 vs -0.017 sd |
| excess | 0.062 sd; shrunk 0.055; after the 26% haircut 0.046 |
| t (episodes) | 0.77 |
| smallest excess these episodes can detect (80% power) | 0.199 sd |
| share moving with the side | 52.2% |
| placebo p (2000 circular shifts) | 0.7706 (placebo 5-95%: -0.174 to 0.154) |
| Bayesianized p (odds 4:1 / 1:1) | 0.800 / 0.500 |
| across the ledger (17 flag studies) | BH q 0.8501, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2015-01-23) | 0.193 (n 90) · -0.069 (n 90) |
| one year dropped | 0.006 (without 2008) to 0.165 (without 2020) |
| against days in the same trend state | excess_sd 0.050 (180 episodes; 81.1% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.3).

**Verdict: no edge.** placebo p 0.7706 > 0.05; BH q 0.8501 > 0.1 across the ledger; excess 0.062 sd short of -0.1; halves disagree [0.193, -0.069]; gone without 2020 (0.165).

_LLM-in-sample: 180 of 180 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
