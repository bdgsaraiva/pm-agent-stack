# CFTC crowded -> move against the crowd

Study `a8_crowded_adverse_v1` · registered 2026-10-19 · spec 6bb64d6fcd2c5649 · as of 2026-10-19 (data through 2026-10-19) · definition 4e3fba293e936537 · verdict **no edge**

**Hypothesis (registered).** When managed money is at or beyond its 3-year 90th (10th) percentile, a 1.5 sd move against that side over the next 20 trading days, counted from the Friday release, is more likely than on other days.

**Source.** Wang 2001 (COT extremes); Sanders, Irwin & Merrin 2009 (no lead); docs/research/risk.md; agent 8 crowding, agent 7 'crowded', the monitor's positioning_extreme (same rule)

**Flag.** `cftc_crowded` {"pct": 90}: CFTC managed money at or beyond params.pct (default 90) of its 3-year range on a side (agent 8 crowding, agent 7 'crowded', the monitor's positioning_extreme); side = the crowded side; dated at the release (Friday, or Monday in a federal-holiday week) and scored from the next close. Side = crowded side.
**Outcome.** `adverse` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +1.

| | value |
|---|---|
| independent episodes | 360 (360 source-date clusters, 10 sources) |
| first / last episode | 2007-06-08 / 2026-08-28 |
| episodes a year | 18.59 |
| hits / expected | 27 / 26.98 |
| hit rate vs base rate | 7.50% (95% 5.21% to 10.69%) vs 7.49% |
| lift | 1.001; shrunk 1.001; after the 26% decay haircut 1.001 |
| binomial z | 0.00 |
| smallest lift these episodes can detect (80% power) | 1.50 |
| placebo p (2000 circular shifts) | 0.5447 (placebo 5-95%: 0.704 to 1.343) |
| Bayesianized p (odds 4:1 / 1:1) | 0.800 / 0.500 |
| across the ledger (17 flag studies) | BH q 0.8501, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2016-02-24) | 0.943 (n 180) · 1.061 (n 180) |
| one year dropped | 0.888 (without 2025) to 1.073 (without 2015) |
| against days in the same trend state | lift 1.059 (359 episodes; 88.3% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.2).

**Verdict: no edge.** placebo p 0.5447 > 0.05; BH q 0.8501 > 0.1 across the ledger; lift 1.001 short of 1.25; halves disagree [0.943, 1.061]; gone without 2025 (0.888).

_LLM-in-sample: 360 of 360 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
