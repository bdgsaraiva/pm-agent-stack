# Large weekly positioning change -> direction

Study `a8_crowded_entry_v1` · registered 2026-10-19 · spec 4d544b69c0233b3b · as of 2026-10-19 (data through 2026-10-19) · definition b2ee978b7182283b · verdict **no edge**

**Hypothesis (registered).** After a weekly managed-money change of 2 sd or more, the market's next 20-day move relative to the change differs from other days (two-sided: continuation or exhaustion).

**Source.** Wang 2001 (large speculators: continuation); Wang 2003 (no superior forecasting); agent 8 'crowded entry', the monitor's positioning_shift

**Flag.** `cftc_crowded_entry` {"z": 2.0}: weekly managed-money change at or beyond params.z (default 2) sd of 3 years of weekly changes (agent 8 'crowded entry', the monitor's positioning_shift); side = the direction of the change. Side = direction of the change.
**Outcome.** `signed` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +0.

| | value |
|---|---|
| independent episodes | 489 (489 source-date clusters, 10 sources) |
| first / last episode | 2007-06-08 / 2026-08-28 |
| episodes a year | 25.25 |
| mean side-signed move vs base | 0.026 vs 0.004 sd |
| excess | 0.022 sd; shrunk 0.021; after the 26% haircut 0.016 |
| t (episodes) | 0.43 |
| smallest excess these episodes can detect (80% power) | 0.127 sd |
| share moving with the side | 49.1% |
| placebo p (2000 circular shifts) | 0.6802 (placebo 5-95%: -0.091 to 0.093) |
| Bayesianized p (odds 4:1 / 1:1) | 0.786 / 0.479 |
| across the ledger (17 flag studies) | BH q 0.8501, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2016-05-20) | 0.008 (n 245) · 0.037 (n 244) |
| one year dropped | -0.014 (without 2020) to 0.046 (without 2017) |
| against days in the same trend state | excess_sd 0.016 (488 episodes; 72.6% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.2).

**Verdict: no edge.** placebo p 0.6802 > 0.05; BH q 0.8501 > 0.1 across the ledger; excess 0.022 sd short of +0.1; gone without 2020 (-0.014).

_LLM-in-sample: 489 of 489 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
