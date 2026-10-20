# Persistent turbulence -> S&P falls

Study `a8_turbulence_v1` · registered 2026-10-19 · spec 5566d9a20c018d33 · as of 2026-10-19 (data through 2026-10-19) · definition 7648b2f0290dd31d · verdict **no edge**

**Hypothesis (registered).** When turbulence stays in its top 20% on 3 of 5 days, a 1.5 sd fall in S&P 500 futures over the next 20 trading days (vol-scaled, so not just higher vol) is more likely than on other days.

**Source.** Kritzman & Li 2010 (turbulence persists and precedes losses); Borio et al. (stress tests are not early warnings); agent 8 risk_turbulence warning

**Flag.** `turbulence_persistent` {"market": "ES=F"}: agent 8 turbulence warning: Mahalanobis turbulence of the universe in its top 20% (last ~3 years) on 3 of the last 5 days, covariance from data up to that day; scored on params.market (default ES=F) with side +1 (long). Side = long params.market.
**Outcome.** `adverse` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +1.

| | value |
|---|---|
| independent episodes | 57 (57 source-date clusters, 1 sources) |
| first / last episode | 1989-03-31 / 2026-06-18 |
| episodes a year | 1.51 |
| hits / expected | 6 / 3.24 |
| hit rate vs base rate | 10.53% (95% 4.91% to 21.12%) vs 5.68% |
| lift | 1.853; shrunk 1.631; after the 26% decay haircut 1.631 |
| binomial z | 1.58 |
| smallest lift these episodes can detect (80% power) | 2.59 |
| placebo p (2000 circular shifts) | 0.0840 (placebo 5-95%: 0.309 to 1.853) |
| Bayesianized p (odds 4:1 / 1:1) | 0.607 / 0.279 |
| across the ledger (17 flag studies) | BH q 0.4101, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2008-01-18) | 1.214 (n 29) · 2.515 (n 28) |
| one year dropped | 1.328 (without 2015) to 1.993 (without 2022) |
| against days in the same trend state | lift 1.864 (56 episodes; 57.9% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.35).

**Verdict: no edge.** placebo p 0.084 > 0.05; BH q 0.4101 > 0.1 across the ledger.

_LLM-in-sample: 57 of 57 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
