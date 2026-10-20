# CTA state 'rebound' -> direction

Study `a8_cta_rebound_v1` · registered 2026-10-19 · spec b76e05b08fc6f9cb · as of 2026-10-19 (data through 2026-10-19) · definition 9f0118d045c79d9f · verdict **no edge**

**Hypothesis (registered).** In the 'rebound' state (12-month leg down, 1-month up) the next 20-day move relative to the 12-month trend differs from other days (two-sided).

**Source.** Agent 8 CTA state; MOP

**Flag.** `cta_state` {"state": "rebound"}: agent 8 CTA state == params.state (correction: 12-month leg up, 1-month down; rebound: the reverse); side = the 12-month sign. Side = 12-month trend sign.
**Outcome.** `signed` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +0.

| | value |
|---|---|
| independent episodes | 909 (909 source-date clusters, 21 sources) |
| first / last episode | 1987-02-20 / 2026-09-04 |
| episodes a year | 22.44 |
| mean side-signed move vs base | 0.027 vs -0.043 sd |
| excess | 0.070 sd; shrunk 0.069; after the 26% haircut 0.052 |
| t (episodes) | 2.09 |
| smallest excess these episodes can detect (80% power) | 0.084 sd |
| share moving with the side | 49.9% |
| placebo p (2000 circular shifts) | 0.0965 (placebo 5-95%: -0.104 to 0.071) |
| Bayesianized p (odds 4:1 / 1:1) | 0.501 / 0.201 |
| across the ledger (17 flag studies) | BH q 0.4101, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2014-10-10) | 0.063 (n 455) · 0.077 (n 454) |
| one year dropped | 0.043 (without 2013) to 0.084 (without 2020) |
| against days in the same trend state | excess_sd 0.063 (909 episodes; 67.8% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.3).

**Verdict: no edge.** placebo p 0.0965 > 0.05; BH q 0.4101 > 0.1 across the ledger; excess 0.07 sd short of +0.1.

_LLM-in-sample: 909 of 909 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
