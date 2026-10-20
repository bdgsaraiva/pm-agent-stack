# Panic state on a with-trend short -> rebound

Study `a8_cta_panic_v2` · registered 2026-10-20 · spec 4c0fbbc9bc015238 · as of 2026-10-19 (data through 2026-10-19) · definition 2aca7bd93c6d4bb7 · verdict **no edge**

**Hypothesis (registered).** In a panic state with a down 12-month trend (the case agent 8 flags live as "rebound risk on a with-trend short"), the next 20-day move on the short side is worse than on other days, i.e. the market rebounds.

**Source.** Daniel & Moskowitz 2016 (momentum crashes in panic states); agent 8's live flag (risk.py, with-trend shorts only). v1 scores both 12-month sides; this version matches the live flag (independent review, 20 Oct 2026, finding 12a)

**Flag.** `cta_panic` {"only": "short"}: agent 8 panic state (Daniel & Moskowitz): 24-month return < 0 and 126-day vol at or above its 80th percentile of ~3 years; side = the 12-month sign; params.only = short scores only a down 12-month trend, as the live flag ("rebound risk on a with-trend short") does. Side = 12-month trend sign.
**Outcome.** `signed` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: -1.

| | value |
|---|---|
| independent episodes | 114 (114 source-date clusters, 21 sources) |
| first / last episode | 1988-01-08 / 2026-06-12 |
| episodes a year | 2.81 |
| mean side-signed move vs base | 0.045 vs -0.043 sd |
| excess | 0.088 sd; shrunk 0.075; after the 26% haircut 0.065 |
| t (episodes) | 0.85 |
| smallest excess these episodes can detect (80% power) | 0.259 sd |
| share moving with the side | 53.5% |
| placebo p (2000 circular shifts) | 0.8001 (placebo 5-95%: -0.235 to 0.198) |
| Bayesianized p (odds 4:1 / 1:1) | 0.800 / 0.500 |
| across the ledger (17 flag studies) | BH q 0.8501, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2014-07-16) | 0.146 (n 57) · 0.031 (n 57) |
| one year dropped | 0.015 (without 2008) to 0.148 (without 2020) |
| against days in the same trend state | excess_sd 0.081 (114 episodes; 86.8% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.25).

**Verdict: no edge.** placebo p 0.8001 > 0.05; BH q 0.8501 > 0.1 across the ledger; excess 0.088 sd short of -0.1; halves disagree [0.146, 0.031]; gone without 2020 (0.148).

_LLM-in-sample: 114 of 114 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
