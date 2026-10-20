---
title: Research loop — literature review
agent: 12 (research loop)
date: 2026-10-19
status: reviewed before build; code in pmstack/research.py (+ pmstack/qstats.py), gate in config/research.yaml, studies in research/
docs: https://claude.ai/code/artifact/61591aa4-b36e-4808-a851-f5c74364f298
---

# Research loop — literature review

**Answer.** Build the research loop as a **pre-registered, counted, code-graded test bench**, not an idea generator. Agents can now produce hundreds of backtests a day, so the scarce part is the overfitting control (Two Sigma's Jin Choi; Man Group runs AlphaGPT's output through the same investment committee as human research). The literature agrees on four things:
- **Count every trial.** Without the number of trials, no multiple-testing correction, deflated Sharpe or false-discovery rate can be computed (Bailey & López de Prado; Harvey, Liu & Zhu). The graveyard is therefore part of the gate, not an archive.
- **Judge binary flags by lift against the base rate, on independent episodes**, never by hit rate (Kaminsky, Lizondo & Reinhart's signals approach; Berg & Pattillo: a real out-of-sample lift was only 37% vs 24%, with 63% false alarms).
- **Expect decay.** Published effects are 26% weaker out of sample and 58% weaker after publication (McLean & Pontiff); most survive in sign (Jensen, Kelly & Pedersen), so report a shrunk effect, not just pass or fail.
- **An LLM remembers the past it is asked to forecast.** Before its cutoff GPT-4o recalls S&P 500 levels to 0.61% and places a headline in the right year 98% of the time; telling it to "forget" does nothing (Lopez-Lira, Tang & Zhu). So code computes every number, the model never sees an outcome before the registration is frozen, and LLM-made features count only after the model's boundary.

Scarce and worth building: one bench that holds the agents' own flags (CFTC crowding, CTA levels, narrative stages, consensus labels) to the same bar as a published paper, with the failures kept. Not worth building: an autonomous alpha-mining agent (FINSABER: reported LLM trading gains vanish on longer, broader tests; the AI Scientist edited its own timeout).

Method: three research passes on 16–19 Oct 2026 (multiple testing and backtest overfitting; replication, decay and binary-flag evaluation; LLM look-ahead and AI research loops), ~80 sources, the quant-research-standards skill, and the Atlas cards. "Read" = the full text was opened; "abstract" = only the abstract; "secondary" = someone else's summary. Book points not page-checked are marked. Two research passes stopped on the account's session limit and were resumed on 19 Oct.

## 1. Papers: multiple testing and backtest overfitting

| Finding | What it changes | Source |
|---|---|---|
| 316 published factors: with BHY at a 1% false-discovery rate the t-hurdle is 3.39; Bonferroni 3.78 by 2012; allowing for unpublished tests, about 3.18. Headline: t > 3.0. | t ≥ 3 is reported for every test and **required for imported ideas** (a paper, a podcast claim) whose search history is unknown. | Harvey, Liu & Zhu, NBER w20592 / RFS 2016 (read, WP) |
| Sharpe haircuts are non-linear: SR 0.75 over 240 months with 200 tests keeps only 0.32 (−60%); strong strategies lose ≤ 25%. | No flat 50% haircut on Sharpe ratios; the deflated Sharpe uses the actual trial count. | Harvey & Liu, "Backtesting", JPM 2015 (read) |
| Deflated Sharpe: E[max SR] of N unskilled trials = √V[SR]·((1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne))); DSR = PSR at that bar, with skew and kurtosis. Worked example: DSR 0.9004 at N = 100, 0.9505 at N = 46. A holdout reused is another trial. | `research.dsr` reproduces both figures to 4 digits (offline test). Strategy verdicts need DSR ≥ 0.95, N = every registered variant. | Bailey & López de Prado 2014 (read; formula from the paper's code, checked on its examples) |
| PSR and minimum track record length (2.73 years for SR 2 vs 1). | PSR vs 0 is reported for every strategy. | Bailey & López de Prado 2012 (read) |
| Probability of backtest overfitting by combinatorial cross-validation; reject when PBO > 0.05. | Needed only when a study sweeps a grid of ≥ 10 configurations. The first studies register one threshold each (the agents' own), so PBO is not run yet. | Bailey, Borwein, López de Prado & Zhu 2017 (read) |
| Reality Check (White) and SPA (Hansen): bootstrap "is the best of many models better than the benchmark"; StepM (Romano & Wolf) says which. | The benchmark of every flag test is its own base rate; the circular-shift placebo plays the bootstrap's role per study, and BH handles the family. | White 2000; Hansen 2005; Romano & Wolf 2005 (read) |
| Benjamini–Hochberg controls the false-discovery rate under positive dependence; Benjamini–Yekutieli (q/Σ1/i) under any dependence. | **The gate:** BH q ≤ 10% across every flag study in the ledger (Bernardo, 19 Oct); BY and Holm reported beside it. | Benjamini & Yekutieli 2001 (read); BH 1995 (secondary) |
| **Counterpoint:** 98% of clearly significant predictors reproduce (Chen & Zimmermann); 82.4% replicate on CAPM alpha, 75.6% after BY (JKP); hurdles that control a 5% FDR range from 0 to 3.0 because unpublished tests are unseen (Chen). | The fight is about a *literature's* hidden trials. Our ledger counts every trial, so our own tests use its exact N (BH) instead of a borrowed hurdle, and every effect is also shown shrunk. | Chen & Zimmermann 2022; Jensen, Kelly & Pedersen 2023; Chen 2025 (read) |
| Overlapping long-horizon windows: Hansen–Hodrick errors reject a true null > 49% of the time at long horizons. | No t-stat on overlapping days: episodes are collapsed so no two share a forward window, and inference is a placebo. | Ang & Bekaert 2007 (read, WP) |

## 2. Papers: replication, decay, and binary warning flags

| Finding | What it changes | Source |
|---|---|---|
| 97 predictors: returns 26% lower out of sample, 58% lower after publication; decay grows with the in-sample t. | Decay haircut: −26% for a flag whose threshold came from the literature, −58% for a published idea (`decay_haircut`, `decay_haircut_paper`). Papers are split at publication. | McLean & Pontiff 2016 (read) |
| 452 anomalies with value weights and no microcaps: 65% fail t ≥ 1.96, 82% fail t ≥ 2.78. | "Boring" construction: front liquid contracts, vol-scaled moves, no thin markets. | Hou, Xue & Zhang 2020 (abstract) |
| 28 of 36 anomalies vanish in the pre-sample period; start-date shifts cut returns 50–75%. | Use history before the paper's sample when it exists (TSMOM: proxies from 1987). | Linnainmaa & Roberts 2018 (read, draft) |
| Signals approach: a 2×2 table, P(event \| signal) beside P(event), noise-to-signal ratio; out of sample 37% vs 24% with 63% false alarms. | Every flag report shows hits vs expected, hit rate vs base rate, lift and the false share. Expect modest lifts (~1.5); `min_lift` 1.25. | Kaminsky, Lizondo & Reinhart 1998 (secondary via Berg & Pattillo); Berg & Pattillo 1999 (read) |
| NSR has no inference and depends on the cutoff; use AUC, Youden, and compare with the base-rate forecast. Honest out-of-sample AUC for a macro warning ≈ 0.65. | Thresholds are fixed ex ante (the agents'); significance comes from the placebo, not from an NSR minimum. | Candelon, Dumitrescu & Hurlin 2012; Schularick & Taylor 2012 (read, WP) |
| COT index: 3-year min–max, 20/80 extremes, 2–12 weeks; large speculators continue, hedgers reverse. Positions are as of Tuesday, out Friday. | CFTC flags are dated at the Friday release and the outcome starts at the next close (lag 4 days from Tuesday). | Wang 2001 (read) |
| Trader positions do not lead returns in 10 agricultural markets; positions follow trends. | The null is the likely answer; each crowding result is also shown **against days in the same trend state** (positions follow trends). | Sanders, Irwin & Merrin 2009 (abstract); Wang 2003 (read) |
| TSMOM: 58 futures 1985–2009, Sharpe > 1, 40% vol per market, EWMA variance × 261 with a 60-day centre of mass. | The replication uses MOP's own construction. | Moskowitz, Ooi & Pedersen 2012 (read) |
| **Counterpoint:** TSMOM profits are "virtually the same" as a historical-mean strategy. | TSMOM is also regressed on the historical-mean book, not only on the long-only book. | Huang, Li, Wang & Zhou 2020 (abstract) |
| Momentum underperforms after crowded periods; CTA flows show no capacity limit. | Crowding is tested as context; no strategy is built on it here. | Baltas 2019 (abstract); Baltas & Kosowski 2013 (secondary) |
| One-way costs 2003+: equity index 0.06%, bonds 0.01%, commodities 0.10%, FX 0.03%; ×2 for 1993–2002, ×6 before; roll costs excluded. | `config/research.yaml` cost table, swept 0–4×; a rule that loses its return at 2× fails. | Hurst, Ooi & Pedersen 2014/2017 (read) |
| Liquid futures quote one tick; spreads widen in stress. | Costs are a floor; stress days cost more (not modelled; noted). | Fett & Haynes 2017, CFTC (read) |
| News attention tracks activity mostly *contemporaneously*; news tone effects are small, fast, reverse, and absent in 1984–91. A news-photo result rested on 20 days. | Narrative stages are tested on *future* moves only, split in halves and with each year dropped. | Bybee et al. (abstract); Tetlock 2007 (read); Lan et al. 2025 (read) |
| No published replication of GDELT-based commodity prediction was found. | Open gap: our narrative tests are the first evidence either way, on the DOC instrument 2017–2026. | Freire et al. 2025 (read, WP); Elshendy et al. 2018 (abstract) |

## 3. Papers: LLM look-ahead and memorisation; automated research loops

| Finding | What it changes | Source |
|---|---|---|
| GPT-4o before its cutoff: macro numbers recalled with 96–99% accuracy, S&P 500 levels to 0.61% (16.87% after); a fake-cutoff instruction leaves accuracy at 98%. | The model never supplies a number; any window before the drafting model's boundary is "LLM-in-sample" and each result says so. | Lopez-Lira, Tang & Zhu 2025 (read) |
| Llama-2 wrote "COVID-19" into 2020 risk forecasts from 2019 calls (6.8% even when told not to); masked firms re-identified 70% of the time. | "Ignore what you know" is not a mitigation; masking is not a cure. | Sarkar & Vafa 2024 (read) |
| A recall test: ask the model the outcome from the firm and date alone; the interaction with the forecast detects contamination (needs token probabilities). | Each registration carries a **recall probe** (the drafting model's guess, written before the run); across studies, guess vs result is a contamination check. | Gao, Jiang & Yan 2026, arXiv 2512.23847 (read) |
| Anonymised headlines beat original ones in-sample; the original-headline signal loads on the market. | Alpha vs beta before anything else. | Glasserman & Lin 2023 (read) |
| **Counterpoint:** real post-cutoff predictability exists but decays (Sharpe 6.54 → 1.22) and dies at 20 bp; time-stamped models show "modest" look-ahead for one task. | Post-boundary evaluation is possible; decay and cost sweeps are mandatory. | Lopez-Lira & Tang 2025; He, Lv, Manela & Wu 2025 (read) |
| The real cutoff can be months after the stated one; use the model's release date. | `llm_boundary` = the first day this model registered a study here (16 Oct 2026), later than its stated June 2026 cutoff. | Paleka et al. 2026 (read) |
| Man Group AlphaGPT: idea, implementation and evaluation agents; hypothesis and sign frozen before the backtest ("flipping a signal after seeing results isn't allowed"); code reviewed line by line; the investment committee decides. | Registration frozen by hash; a sign flip is a new study judged on later data; the human (Bernardo) decides. | Fang & Moore, Man Group 2025 (read); AI Street interview 2025 (read) |
| The AI Scientist edited its own timeout; 42% of experiments failed on code errors. RD-Agent's test window lies before its model's cutoff. FINSABER: LLM trading claims shrink on long, broad tests. | The gate code, thresholds and data are not the model's to change; studies use 20 years of data, not a lucky window. | Sakana 2024; Beel et al. 2025; Li et al. 2025; Li, Kim, Cucuringu & Ma 2026 (read/abstract) |
| Harvey's address: state the foundation, hypotheses, data, tests and reporting plan before looking; report the Bayesianized p (MBF = exp(−z²/2)). | Registration fields follow it; each result shows the Bayesianized p at odds 4:1 and 1:1. | Harvey 2017 (read) |
| "Backtesting is not a research tool": about 20 iterations find a false strategy at 5%. | One registered backtest per hypothesis, never iterate until good. | López de Prado 2018 (read) |
| Pre-analysis plans help most as short mandatory fields; rigid plans cost discovery. | Short registration; exploratory looks are labelled and counted. | Olken 2015; Banerjee et al. 2020 (abstract) |

## 4. Atlas investors and firms
- **Man Group (AlphaGPT)**: agents that read papers, propose signals, write code and backtest, with every step logged; output goes to the normal committee with look-ahead and multiple-testing checks; "several dozen" signals live; "I wouldn't call it autopilot". → The loop proposes and measures; Bernardo decides; human and AI ideas face one gate.
- **Two Sigma**: "agents generating and backtesting many hypotheses can exacerbate the overfitting issue" (Jin Choi); start from a prior and move on when data disagree (Wellington). → The bottleneck is the control, so the ledger and BH come first.
- **Hudson River Trading**: market data have "very little signal"; every complex model must beat a simple baseline; heavy scepticism to any new result. → Every flag is compared with its plain base rate; TSMOM with the long-only and historical-mean books.
- **David Harding (Winton)**: scientific method, be sceptical of backtests. **Bouchaud (CFM)**: crowding as a risk factor; ML speeds up analysis but doesn't transform it. **Asness (AQR)**: stick with sound factors through drawdowns. → Crowding is measured, not assumed; TSMOM is judged over 40 years and after publication.
- Books (general knowledge, not page-checked): López de Prado, *Advances in Financial Machine Learning* (sample uniqueness, the strategy graveyard); Harvey & Liu's backtesting chapter; Kahneman, *Thinking, Fast and Slow* (base-rate neglect); Ioannidis, "Why most published research findings are false".

## 5. Where sources disagree, and the resolution
1. **Raise the hurdle (HLZ t > 3) or not (Chen; JKP)?** The dispute is about unseen tests in the literature. → Our own registered tests: BH across the ledger (every trial counted). Imported ideas: t ≥ 3 too.
2. **FWER or FDR?** → FDR (BH q ≤ 10%) across studies, Holm and BY reported; a placebo per study handles dependence inside it.
3. **Pass/fail or shrinkage?** → Both: the verdict is pass/fail; the number other agents quote is the shrunk lift (n0 = 20 pseudo-episodes at the base rate), shown with the decay haircut.
4. **Do COT extremes predict?** Hedging pressure (slow premium) vs no short-horizon lead. → Test the agents' own rule; expect the null; show it against the trend state.
5. **Is TSMOM real?** MOP vs Huang et al. → Alpha vs the long-only book *and* vs the historical-mean book, after costs, with the post-publication period apart.
6. **How big is LLM look-ahead?** "Modest" (He et al.) vs "material" (Lopez-Lira et al.; DatedGPT). → Assume contaminated before the boundary; here the model only drafts registrations, picks no number, and the queue is rule-built (every flag agents 7 and 8 ship).
7. **How strict is pre-registration?** → Short fields, frozen by hash; a change is a new id; exploratory runs count as trials.

## 6. Design vs the plan's spec
- **Gate** (Bernardo, 19 Oct: "BH q ≤ 10% + placebo"): ≥ 20 independent episodes; circular-shift placebo p ≤ 5% in the registered direction; BH q ≤ 10% across every registered flag study (missing or insufficient ones count with p = 1); lift ≥ 1.25 (or excess ≥ 0.10 sd); the registered sign in both chronological halves and with any one calendar year dropped; an imported idea also t ≥ 3; the definition (config + code) unchanged since its first hashed run. Verdicts: `supported`, `no edge`, `reversed` (the same gate passed the other way), `in-sample only` (a hindsight-written definition, until live episodes agree), `insufficient` (with the smallest lift the episodes could detect); strategies also `decayed`.
- **Strategies:** alpha t ≥ 3 vs the long-only book of the same markets (an imported idea), DSR ≥ 0.95, positive Sharpe in both halves, return left at 2× costs; after publication reported apart.
- **Data** (Bernardo, 19 Oct): CFTC disaggregated history fetched once back to June 2006 (14 year files, no edit to sources.yaml), so crowding tests have ~20 years.
- **Wiring** (Bernardo, 19 Oct: "tags in Risk + critic"): the Risk section lists each agent 8 flag's measured verdict under the CTA table and keeps a `measured` field per idea; the critic card gets `research.crowded`, `research.label`, `research.spreading` facts. No alert is added or removed (agent 7's and the monitor's alerts belong to the other session); a flag that is not `supported` stays context.
- **First jobs:** 16 flag studies (7 for agent 7: narrative spreading ×2, peaking, fading, three labels; 9 for agent 8: crowded, crowded entry, crowded red, CTA roll-off, correction, rebound, vol shrinking, panic, turbulence) and one replication (TSMOM). The monitor's `positioning_extreme` uses the same rule as `cftc_crowded` and is covered by it.
- **Not built:** PBO (no grid yet), Romano–Wolf StepM within a study, the pre-sample and start-date perturbation tests (TSMOM uses 1987 proxies), token-probability recall tests (the endpoint exposes none), a cost multiplier on stress days.

## 7. How it works
1. **Register** (`research new <yaml>`): hypothesis, flag and params (from the catalogue in code) or strategy, outcome, horizon, registered direction, source, recall probe. Validated (no result fields allowed), written to `research/studies/`, hashed into `research/ledger.jsonl`.
2. **Recompute the flag point in time:** on a weekly grid (Fridays; CFTC on report dates), with the agents' own functions on data up to that day (`consensus.stage_of`, `consensus.trend`/`positioning`/`_label`, `risk.cta_levels`, the turbulence formula, `risk.funding`). Offline tests check the numbers equal the agents' own and that later data change nothing.
3. **Outcome:** the vol-scaled log return from the first close after the data were public (prices and GDELT: next morning; CFTC: the release, Friday or the Monday of a federal-holiday week) over h trading days, divided by the EWMA sd known on the signal day. Agent 8's spliced returns (roll jumps screened where a proxy exists).
4. **Episodes:** runs collapsed per source, market and side, with a gap ≥ h, so no two share a window.
5. **Base rate:** the same outcome on every day of the same market, same side, same evaluable window. Lift = hits / expected hits (binary); excess = mean side-signed move minus the same market's mean (continuous).
6. **Placebo:** 2,000 circular shifts of the calendar, one per draw for every source and market (so coinciding episodes stay together), giving p in the registered direction and p the other way.
7. **Gate and family:** halves, drop-one-year, size; BH across every registered flag study; the index rewrites each result page with its final verdict and the failing rules, keeps the graveyard, and writes `verdicts.json` for the Risk section and the critic (point in time: a verdict shows only for as-of dates after its data).

## 8. Results of the first run (as of 19 Oct 2026; data through 16 Oct; after the review fixes)
**Answer: none of agent 7's or agent 8's flags may alert.** 17 flag studies and one replication; every flag is `no edge` except fading narratives, which would pass the gate but are capped at `in-sample only` because the narrative queries were written in Oct 2026 with that history in view. The full table and the graveyard are in `research/index.md`; each study has its page in `research/results/`.

| Study | Episodes | Effect | Placebo p | BH q | Verdict |
|---|---:|---|---:|---:|---|
| Fading narratives → their markets move against them (agent 7) | 427 | excess −0.20 sd (shrunk −0.19); halves −0.20 / −0.20 | 0.005 | 0.085 | in-sample only |
| "Twilight" label → move against the trend | 69 | lift 1.95 (14.5% vs 7.4%) | 0.046 | 0.391 | no edge |
| Persistent turbulence → S&P falls 1.5 sd (agent 8) | 57 | lift 1.85 (10.5% vs 5.7%) | 0.084 | 0.410 | no edge |
| Spreading narratives → markets move their way | 326 | excess −0.16 sd (the opposite way; second half −0.03) | 0.966 | 0.966 | no edge (leans opposite, fails BH there) |
| CFTC crowded (90th pct, 2007–2026) → move against the crowd | 360 | lift 1.00 (7.50% vs 7.49%) | 0.545 | 0.850 | no edge |
| Crowded while funding stresses | 170 | lift 1.29 (9.4% vs 7.3%); halves 1.70 / 0.84 | 0.190 | 0.541 | no edge |
| CTA roll-off flip → 5-day move the flip's way | 8,290 | excess 0.01 sd | 0.348 | 0.702 | no edge |
| CTA "rebound" / "correction" states | 909 / 1,206 | excess 0.07 / 0.06 sd | 0.097 / 0.306 | 0.410 / 0.702 | no edge |
| Panic state (both sides; with-trend shorts only, as live) | 180 / 114 | excess 0.06 / 0.09 sd (wrong sign for a crash) | 0.771 / 0.800 | 0.850 | no edge |
| Other agent 7 and 8 flags (peaking, spreading → big move, self-reinforcing, crowded label, crowded entry, vol shrinking) | 39–489 | lifts 0.88–1.15, excess −0.11 to +0.08 sd | ≥ 0.19 | ≥ 0.54 | no edge |

**Time-series momentum (MOP 2012), our 19 futures, Feb 1987–Oct 2026 (477 months):**
- Sharpe 0.63 after AQR costs (10.5% return at 16.6% vol);
- alpha vs the long-only book of the same markets 6.2% a year, HAC t 2.21 (beta 0.31);
- vs the historical-mean book: t 2.91; vs S&P futures: t 3.02;
- deflated Sharpe 0.58 over the 3 registered lookbacks (V[SR] floored);
- by period: Sharpe 0.77 inside the paper's sample (to 2009), −0.01 from 2010 to publication (May 2012), 0.51 after it;
- break-even cost 11.5× the AQR table;
- the 1- and 3-month variants: Sharpe 0.17 and 0.34.

Verdict `no edge`: alpha t 2.21 is below the t ≥ 3 bar for an imported idea, and the deflated Sharpe is below 0.95. Read (inference): the trend premium is real but weaker since publication, and mostly market beta plus a modest alpha on these front-month series. It is no reason to treat agent 7's trend vote or agent 8's CTA levels as signals.

**What this changes.**
- The Risk section now lists each agent 8 flag's verdict under the CTA table, and the critic card shows `research.crowded`, `research.label` and `research.spreading` when they apply.
- The caption says no crowding or CTA flag alerts unless the loop rates it supported; none is today.
- Fading narratives get live tracking: 20 episodes after 10 Oct 2026 with the same sign would lift the cap.
- Strongest caveat: our outcomes use front-month Yahoo closes with roll jumps screened only where a proxy exists, so roll effects add noise to every commodity study.

## 9. Independent review (20 Oct 2026): 18 defects, all fixed
A sub-agent that didn't build the loop reviewed the code, the studies and the live results.
- **High**
  1. The placebo shifted each source on its own, breaking the clustering across narratives and correlated markets: a null flag copied into 4 sources was rejected 23% of the time at 5%. → One calendar shift per draw for every source; a copies test guards it.
  2. Result pages kept a verdict computed on a partial family mid-run (twilight showed "supported" at BH q 0.086 over 4 studies). → The index rewrites every page with the final family verdict; changes are ledger events.
  3. "Reversed" skipped BH and the other gate rules. → The opposite direction faces the same gate, with its own BH family; otherwise "no edge (leans opposite)".
- **Medium**
  4. The label studies' base-rate window began in 2007, but the narrative stages exist only from 2017. → Twilight and self-reinforcing rows only where a linked narrative has a stage.
  5. The narrative queries and signs were written with hindsight but not marked. → A `hindsight` list in config caps them at "in-sample only" until live episodes agree.
  6. Config and code were outside the frozen hash. → A definition hash (loop and agents' config, plus the code of the flag and outcome) is frozen at the first hashed run; a change blocks "supported".
  7. Unregistered specs and no-write runs were neither frozen nor counted. → Refused, and logged as peeks.
  8. The t ≥ 3 rule was not enforced for imported flags, and `hlz_pass` used |t|. → Enforced for `paper:` studies, with the signed t.
  9. Errored studies dropped out of BH. → Every registered flag study counts, at p = 1 when missing.
  10. Verdict tags broke point-in-time for backdated packs and cards. → A verdict shows only if its data ended by the as-of date.
  11. `verdict_for` took the alphabetically first study. → The latest registration, then the highest `_vN`.
  12. Fidelity: the panic side, the narrative stage date (live ends on the last *valid* day), the CTA minimum history, and CFTC holiday weeks (release on Monday). → Aligned; the panic study re-registered as `a8_cta_panic_v2` to match the live rule (with-trend shorts only).
- **Low**
  13. The momentum book used next month's data to decide membership. → Decided from data at the rebalance.
  14. Costs used the wrong era; exits were not charged. → Fixed.
  15. The Bayesianized p treated a two-sided p as one-sided. → Halved.
  16. Unrounded q in the reasons. → Rounded.
  17. A malformed verdicts file could break the Risk section. → Guarded.
  18. This page's section 8 was stale. → Filled from the post-review run.
- The first run (19 Oct) is kept in the ledger; its verdicts were superseded by the post-review run. CFTC crowding moved from lift 0.82 to 1.00 with the fixes (flags dated at the release, so the vol scale is the one known that day, and holiday weeks enter a day later); the verdict did not change.

## 10. Sources
Harvey, Liu & Zhu https://www.nber.org/papers/w20592 · Harvey & Liu 2015 https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF · Bailey & López de Prado 2014 https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf · 2012 https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf · Bailey, Borwein, López de Prado & Zhu https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf · White 2000 https://users.ssc.wisc.edu/~bhansen/718/White2000.pdf · Hansen 2005 https://cdr.lib.unc.edu/concern/articles/hd76s214m · Romano & Wolf https://econ-papers.upf.edu/papers/712.pdf · Benjamini & Yekutieli https://www.math.tau.ac.il/~ybenja/MyPapers/benjamini_yekutieli_ANNSTAT2001.pdf · Chen & Zimmermann https://cfr.ivo-welch.info/published/papers/chen2021open.pdf · Jensen, Kelly & Pedersen https://www.nber.org/papers/w28432 · Chen 2025 https://arxiv.org/html/2204.10275v4 · Ang & Bekaert https://www.nber.org/papers/w8207 · Patton, Politis & White https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf · McLean & Pontiff https://www.gwern.net/doc/economics/2016-mclean.pdf · Hou, Xue & Zhang https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2019-2133..html · Linnainmaa & Roberts https://jacobslevycenter.wharton.upenn.edu/wp-content/uploads/2017/08/The-History-of-the-Cross-Section-of-Stock-Returns.pdf · KLR https://www.imf.org/external/Pubs/FT/staffp/1998/03-98/kaminsky.htm · Berg & Pattillo https://www.imf.org/external/pubs/ft/staffp/1999/06-99/pdf/berg.pdf · Candelon et al. https://cris.maastrichtuniversity.nl/ws/files/1280210/guid-676f33ff-f458-481d-8ff9-49d1846121df-ASSET1.0.pdf · Schularick & Taylor https://www.nber.org/system/files/working_papers/w15512/w15512.pdf · Jordà & Taylor https://www.nber.org/system/files/working_papers/w17150/w17150.pdf · Boudoukh, Richardson & Whitelaw https://www.nber.org/papers/w11841 · de Roon, Nijman & Veld https://ideas.repec.org/a/bla/jfinan/v55y2000i3p1437-1456.html · Bessembinder https://ideas.repec.org/a/oup/rfinst/v5y1992i4p637-67.html · Wang 2001 https://mpra.ub.uni-muenchen.de/36425/1/MPRA_paper_36425.pdf · Wang 2003 https://mpra.ub.uni-muenchen.de/36426/1/MPRA_paper_36426.pdf · Sanders, Irwin & Merrin https://ideas.repec.org/a/ags/jlaare/54547.html · Moskowitz, Ooi & Pedersen https://fairmodel.econ.yale.edu/ec439/jpde.pdf · Huang et al. https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html · Baltas 2019 https://ideas.repec.org/a/taf/ufajxx/v75y2019i3p89-104.html · Hurst, Ooi & Pedersen https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf · Fett & Haynes https://www.cftc.gov/About/EconomicAnalysis/WhitePapers/ssLINK/oce_LiquidityFuturesMarkets · Marshall, Nguyen & Visaltanachoti https://ideas.repec.org/a/oup/rfinst/v25y2012i2p599-638.html · Shiller https://www.nber.org/papers/w23075 · Bybee et al. https://www.nber.org/papers/w29344 · Tetlock https://www.columbia.edu/~pt2238/papers/Tetlock_Media_Sentiment_JF.pdf · Lan et al. https://cfr.ivo-welch.org/forthcoming/papers/lan2025robustness.pdf · Freire et al. https://wp.lancs.ac.uk/fofi2026/files/2026/03/FoFI-2026-006-Amar-Soebhag.pdf · Elshendy et al. https://arxiv.org/abs/2105.09154 · Glasserman & Lin https://arxiv.org/abs/2309.17322 · Sarkar & Vafa https://conference.nber.org/conf_papers/f205530/f205530.pdf · Gao, Jiang & Yan https://arxiv.org/abs/2512.23847 · Lopez-Lira, Tang & Zhu https://arxiv.org/abs/2504.14765 · Lopez-Lira & Tang https://arxiv.org/abs/2304.07619 · He, Lv, Manela & Wu https://arxiv.org/abs/2502.21206 · Yan et al. (DatedGPT) https://arxiv.org/abs/2603.11838 · Levy https://www.chicagobooth.edu/research/fama-miller/finance-research/working-papers/2025/caution-ahead · Paleka et al. https://arxiv.org/html/2506.00723v1 · Fang & Moore (Man Group) https://www.man.com/insights/what-ai-can-do-for-alpha · AI Street (Fang) https://aistreet.beehiiv.com/p/inside-man-group-s-alphagpt · Two Sigma (Wellington) https://www.twosigma.com/articles/anything-can-be-language-now-my-thoughts-on-the-future-of-features-research/ · HRT https://www.hudsonrivertrading.com/hrtbeat/trading-machine-learning/ · Tang et al. (AlphaAgent) https://arxiv.org/html/2502.16789 · Li et al. (RD-Agent) https://arxiv.org/html/2505.15155 · Sakana https://sakana.ai/ai-scientist/ · Beel et al. https://arxiv.org/abs/2502.14297 · FINSABER https://arxiv.org/html/2505.07078v5 · López de Prado 2018 https://www.garp.org/hubfs/Whitepapers/a1Z1W0000054x6lUAA.pdf · Harvey 2017 https://people.duke.edu/~charvey/Research/Published_Papers/P131_The_scientific_outlook.pdf · Olken https://www.aeaweb.org/articles?id=10.1257/jep.29.3.61 · Banerjee et al. https://www.nber.org/papers/w26993 · Atlas cards: Man Group (AlphaGPT), Two Sigma, Hudson River Trading, Harding, Bouchaud, Asness.
