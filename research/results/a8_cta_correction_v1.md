# CTA state 'correction' -> direction

Study `a8_cta_correction_v1` · registered 2026-10-19 · spec da60ef6f8e661c75 · as of 2026-10-19 (data through 2026-10-19) · definition 9f0118d045c79d9f · verdict **no edge**

**Hypothesis (registered).** In the 'correction' state (12-month leg up, 1-month down) the next 20-day move relative to the 12-month trend differs from other days (two-sided).

**Source.** Agent 8 CTA state; MOP (1-12 month persistence)

**Flag.** `cta_state` {"state": "correction"}: agent 8 CTA state == params.state (correction: 12-month leg up, 1-month down; rebound: the reverse); side = the 12-month sign. Side = 12-month trend sign.
**Outcome.** `signed` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +0.

| | value |
|---|---|
| independent episodes | 1206 (1206 source-date clusters, 21 sources) |
| first / last episode | 1988-09-30 / 2026-09-18 |
| episodes a year | 29.77 |
| mean side-signed move vs base | 0.120 vs 0.063 sd |
| excess | 0.058 sd; shrunk 0.057; after the 26% haircut 0.043 |
| t (episodes) | 1.87 |
| smallest excess these episodes can detect (80% power) | 0.077 sd |
| share moving with the side | 56.3% |
| placebo p (2000 circular shifts) | 0.3058 (placebo 5-95%: -0.068 to 0.099) |
| Bayesianized p (odds 4:1 / 1:1) | 0.703 / 0.372 |
| across the ledger (17 flag studies) | BH q 0.7023, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2013-04-19) | 0.051 (n 604) · 0.064 (n 602) |
| one year dropped | 0.036 (without 2013) to 0.079 (without 2012) |
| against days in the same trend state | excess_sd 0.046 (1206 episodes; 71.7% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.3).

**Verdict: no edge.** placebo p 0.3058 > 0.05; BH q 0.7023 > 0.1 across the ledger; excess 0.058 sd short of +0.1.

_LLM-in-sample: 1206 of 1206 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
