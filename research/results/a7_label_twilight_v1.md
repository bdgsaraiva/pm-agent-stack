# Twilight label -> move against the trend

Study `a7_label_twilight_v1` · registered 2026-10-19 · spec 75ebef5068964bbf · as of 2026-10-19 (data through 2026-10-19) · definition f976d8296b2efce8 · verdict **no edge**

**Hypothesis (registered).** Markets labelled 'twilight' (crowded >= 90th percentile on the trend side while the narrative behind it fades) see a 1.5 sd move against the trend over the next 20 trading days more often than other days.

**Source.** Baltas 2019 (divergence premia underperform after crowding); agent 7

**Flag.** `consensus_label` {"label": "twilight"}: agent 7 consensus-map label == params.label (self-reinforcing | twilight | crowded | quiet | mixed) from its own trend vote, CFTC percentile and the DOC narrative stages; side = the trend direction. Side = trend direction.
**Outcome.** `adverse` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +1.

| | value |
|---|---|
| independent episodes | 69 (69 source-date clusters, 8 sources) |
| first / last episode | 2017-09-01 / 2026-09-04 |
| episodes a year | 7.56 |
| hits / expected | 10 / 5.12 |
| hit rate vs base rate | 14.49% (95% 8.07% to 24.66%) vs 7.42% |
| lift | 1.954; shrunk 1.740; after the 26% decay haircut 1.706 |
| binomial z | 2.25 |
| smallest lift these episodes can detect (80% power) | 2.21 |
| placebo p (2000 circular shifts) | 0.0460 (placebo 5-95%: 0.391 to 1.788) |
| Bayesianized p (odds 4:1 / 1:1) | 0.492 / 0.195 |
| across the ledger (17 flag studies) | BH q 0.3910, BY q 1.0000, Holm p 0.7360, t >= 3: no |
| halves (split 2022-02-11) | 1.144 (n 35) · 2.805 (n 34) |
| one year dropped | 1.667 (without 2025) to 2.277 (without 2018) |
| against days in the same trend state | lift 2.099 (69 episodes; 100.0% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.25).

**Hindsight.** This flag's definition was written on 2026-10-10 with this history in view, so its history can show at most 'in-sample only'; live episodes after that date decide.

**Verdict: no edge.** BH q 0.391 > 0.1 across the ledger.

_LLM-in-sample: 69 of 69 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; its definition was written on 2026-10-10 with that history in view (verdict capped). Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
