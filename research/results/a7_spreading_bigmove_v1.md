# Narrative spreading -> large moves

Study `a7_spreading_bigmove_v1` · registered 2026-10-19 · spec 25a1855b73a5ff23 · as of 2026-10-19 (data through 2026-10-19) · definition c09a3ada5c95462f · verdict **no edge**

**Hypothesis (registered).** When a narrative enters 'spreading', a move of 1.5 sd or more (either way) in its markets over the next 20 trading days is more likely than on other days.

**Source.** Attention and volatility (Bybee et al.; Tetlock 2007: tone effects are short and reverse); agent 7

**Flag.** `narrative_stage` {"stage": "spreading"}: agent 7 narrative stage == params.stage (spreading | peaking | fading | steady | dormant), on each market the narrative pushes, side = the narrative's sign for that market. Side = narrative sign.
**Outcome.** `big_move` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +1.

| | value |
|---|---|
| independent episodes | 326 (130 source-date clusters, 13 sources) |
| first / last episode | 2017-09-01 / 2026-08-28 |
| episodes a year | 35.74 |
| hits / expected | 53 / 46.29 |
| hit rate vs base rate | 16.26% (95% 12.65% to 20.65%) vs 14.20% |
| lift | 1.145; shrunk 1.137; after the 26% decay haircut 1.107 |
| binomial z | 1.07 |
| smallest lift these episodes can detect (80% power) | 1.35 |
| placebo p (2000 circular shifts) | 0.1909 (placebo 5-95%: 0.739 to 1.257) |
| Bayesianized p (odds 4:1 / 1:1) | 0.732 / 0.406 |
| across the ledger (17 flag studies) | BH q 0.5409, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2022-01-14) | 1.414 (n 165) · 0.871 (n 161) |
| one year dropped | 0.996 (without 2020) to 1.212 (without 2025) |
| against days in the same trend state | lift 1.157 (326 episodes; 52.5% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.3).

**Hindsight.** This flag's definition was written on 2026-10-10 with this history in view, so its history can show at most 'in-sample only'; live episodes after that date decide.

**Verdict: no edge.** placebo p 0.1909 > 0.05; BH q 0.5409 > 0.1 across the ledger; lift 1.145 short of 1.25; halves disagree [1.414, 0.871]; gone without 2020 (0.996).

_LLM-in-sample: 326 of 326 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; its definition was written on 2026-10-10 with that history in view (verdict capped). Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
