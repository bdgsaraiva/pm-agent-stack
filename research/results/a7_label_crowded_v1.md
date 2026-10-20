# Crowded label -> move against the crowd

Study `a7_label_crowded_v1` · registered 2026-10-19 · spec 280b6b3d98e3d8df · as of 2026-10-19 (data through 2026-10-19) · definition f976d8296b2efce8 · verdict **no edge**

**Hypothesis (registered).** Markets labelled 'crowded' (CFTC >= 90th percentile on the trend's side) see a 1.5 sd move against the trend over the next 20 trading days more often than other days.

**Source.** Brunnermeier & Pedersen; Sanders, Irwin & Merrin (positions follow trends: expect the null); agent 7

**Flag.** `consensus_label` {"label": "crowded"}: agent 7 consensus-map label == params.label (self-reinforcing | twilight | crowded | quiet | mixed) from its own trend vote, CFTC percentile and the DOC narrative stages; side = the trend direction. Side = trend direction.
**Outcome.** `adverse` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +1.

| | value |
|---|---|
| independent episodes | 352 (352 source-date clusters, 10 sources) |
| first / last episode | 2007-06-08 / 2026-09-18 |
| episodes a year | 18.19 |
| hits / expected | 23 / 26.15 |
| hit rate vs base rate | 6.53% (95% 4.39% to 9.61%) vs 7.43% |
| lift | 0.880; shrunk 0.886; after the 26% decay haircut 0.911 |
| binomial z | -0.64 |
| smallest lift these episodes can detect (80% power) | 1.50 |
| placebo p (2000 circular shifts) | 0.7511 (placebo 5-95%: 0.688 to 1.377) |
| Bayesianized p (odds 4:1 / 1:1) | 0.800 / 0.500 |
| across the ledger (17 flag studies) | BH q 0.8501, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2015-11-06) | 0.817 (n 177) · 0.946 (n 175) |
| one year dropped | 0.795 (without 2025) to 0.953 (without 2015) |
| against days in the same trend state | lift 0.929 (352 episodes; 99.4% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.2).

**Verdict: no edge.** placebo p 0.7511 > 0.05; BH q 0.8501 > 0.1 across the ledger; lift 0.88 short of 1.25; halves disagree [0.817, 0.946]; gone without 2025 (0.795).

_LLM-in-sample: 352 of 352 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; the flag rule came from the literature and predates this test. Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
