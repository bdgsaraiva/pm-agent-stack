# CTA leg flips by roll-off -> move the flip's way

Study `a8_cta_rolloff_v1` · registered 2026-10-19 · spec 5461865e7eca0470 · as of 2026-10-19 (data through 2026-10-19) · definition 41ddf4a5aeaf96e3 · verdict **no edge**

**Hypothesis (registered).** When a 1/3/12-month trend leg will flip by roll-off within 5 days at today's price, the market moves in the direction of the flip over the next 5 trading days more than on other days (trend-follower flows).

**Source.** Hurst, Ooi & Pedersen; Baltas & Kosowski; agent 8 CTA levels

**Flag.** `cta_rolloff_flip` {}: agent 8 CTA levels: a trend leg (21/63/252 days) flips by roll-off within 5 days at today's price; side = the sign the soonest leg flips to. Side = flip direction.
**Outcome.** `signed` over 5 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +1.

| | value |
|---|---|
| independent episodes | 8290 (8290 source-date clusters, 21 sources) |
| first / last episode | 1986-05-16 / 2026-10-09 |
| episodes a year | 204.62 |
| mean side-signed move vs base | 0.006 vs -0.001 sd |
| excess | 0.006 sd; shrunk 0.006; after the 26% haircut 0.005 |
| t (episodes) | 0.54 |
| smallest excess these episodes can detect (80% power) | 0.029 sd |
| share moving with the side | 49.9% |
| placebo p (2000 circular shifts) | 0.3478 (placebo 5-95%: -0.026 to 0.025) |
| Bayesianized p (odds 4:1 / 1:1) | 0.787 / 0.481 |
| across the ledger (17 flag studies) | BH q 0.7023, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2013-08-02) | 0.018 (n 4148) · -0.006 (n 4142) |
| one year dropped | 0.002 (without 2007) to 0.011 (without 2018) |
| against days in the same trend state | excess_sd 0.010 (8290 episodes; 30.8% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.2).

**Verdict: no edge.** placebo p 0.3478 > 0.05; BH q 0.7023 > 0.1 across the ledger; excess 0.006 sd short of +0.1; halves disagree [0.018, -0.006].

_LLM-in-sample: 8290 of 8290 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
