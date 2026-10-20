# Narrative spreading -> markets move its way

Study `a7_spreading_follow_v1` · registered 2026-10-19 · spec f7b02fb56491388a · as of 2026-10-19 (data through 2026-10-19) · definition c09a3ada5c95462f · verdict **no edge**

**Hypothesis (registered).** When a narrative enters 'spreading' (4-week share >= 1.5x the prior 26 weeks, rising 2 of 3 weeks), the markets it pushes move in its direction over the next 20 trading days by more than they do on other days.

**Source.** Shiller 2017 (narratives spread like epidemics); Bybee, Kelly, Manela & Xiu (attention tracks activity, mostly contemporaneous); docs/research/consensus.md; agent 7's narrative_spreading alert

**Flag.** `narrative_stage` {"stage": "spreading"}: agent 7 narrative stage == params.stage (spreading | peaking | fading | steady | dormant), on each market the narrative pushes, side = the narrative's sign for that market. Side = narrative sign.
**Outcome.** `signed` over 20 trading days from the first close 1 day(s) after the signal date; large = 1.5 sd of an h-day move (EWMA sd known on the signal date). Registered direction: +1.

| | value |
|---|---|
| independent episodes | 326 (130 source-date clusters, 13 sources) |
| first / last episode | 2017-09-01 / 2026-08-28 |
| episodes a year | 35.74 |
| mean side-signed move vs base | -0.154 vs 0.004 sd |
| excess | -0.158 sd; shrunk -0.149; after the 26% haircut -0.117 |
| t (episodes) | -2.45 |
| smallest excess these episodes can detect (80% power) | 0.160 sd |
| share moving with the side | 44.5% |
| placebo p (2000 circular shifts) | 0.9660 (placebo 5-95%: -0.143 to 0.122) |
| Bayesianized p (odds 4:1 / 1:1) | 0.800 / 0.500 |
| across the ledger (17 flag studies) | BH q 0.9660, BY q 1.0000, Holm p 1.0000, t >= 3: no |
| halves (split 2022-01-14) | -0.288 (n 165) · -0.025 (n 161) |
| one year dropped | -0.184 (without 2024) to -0.073 (without 2020) |
| against days in the same trend state | excess_sd -0.159 (326 episodes; 52.5% on the trend's side) |
| live, since the rule was frozen (2026-10-10) | 0 episodes |

**Recall probe (asked before the run).** Before the run: will the effect have the registered sign and pass the gate? Answer: no (0.25).

**Hindsight.** This flag's definition was written on 2026-10-10 with this history in view, so its history can show at most 'in-sample only'; live episodes after that date decide.

**Verdict: no edge.** leans the opposite way (placebo p 0.0345) but fails the gate there: BH q 0.5865 > 0.1 across the ledger.

_LLM-in-sample: 326 of 326 episodes fall before the drafting model's boundary 2026-10-16; the model picked no number; its definition was written on 2026-10-10 with that history in view (verdict capped). Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
