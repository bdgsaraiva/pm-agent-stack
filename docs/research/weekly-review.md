---
title: Weekly review — literature review
agent: 6 (weekly review / process scorecard)
date: 2026-10-10
status: reviewed before build; code in pmstack/review.py, parameters in config/review.yaml, page in skills/critic-weekly/
docs: https://claude.ai/code/artifact/dfaab6f8-6e05-4058-a5e8-61fe5b69d639
---

# Weekly review — literature review

**Answer.** Score process before outcome, show every outcome statistic with its uncertainty, and end with one if-then goal that code can track. At an R sd of 1.5, telling a +0.25R edge from zero takes about 283–285 closed ideas, so for years the review catches behaviour leaks; it cannot judge skill.

## 1. Trading behaviour

| Finding | What it changes | Source |
|---|---|---|
| Disposition: retail sold 14.8% of paper gains vs 9.8% of losses; Taiwan 0.35 vs 0.14, kept losers did worse (−4.49% vs −2.76% over 12 months). | Journal gains-vs-losses realised; would-have-been R. | Odean 1998 (figures via secondary); Shu et al. |
| Pro futures traders hold losers longer without measurable cost; relative discipline predicts success. A prop team did pay for it. | Score days held past the idea's own invalidation, not the winner/loser gap. | Locke & Mann 2005; Garvey & Murphy 2004 |
| Tilt: prop traders raised trades, size and risk after morning losses (most affected −$4.3k to −14.4k); CBOT locals 31.2% vs 27%. Option market makers did the opposite (more risk after gains). | Count new ideas and their size within 3 days of a −1R or +1R close, both directions. | Garvey, Murphy & Wu; Coval & Shumway 2005; Liu et al. 2010; Thaler & Johnson 1990 |
| Overtrading: most active households ~11.4%/yr vs market 17.9%; better-than-average belief drives volume. | New ideas vs trailing 8-week median. | Barber & Odean 2000, 2001; Glaser & Weber 2007 |
| Sells lag random sells by ~80 bp; earnings-day sells beat other sells by ~154 bp; extreme movers sold more. | Exit trigger tagged at close; R after exit by trigger. | Akepanidtaworn et al. (NBER w29076) |

## 2. Feedback, debriefs, goals

| Finding | What it changes | Source |
|---|---|---|
| Feedback d=0.41 on average but >38% of effects negative; self-focused feedback weakens it; task-level + goal strengthens it. | No praise, blame or comparison; corrective, by idea. | Kluger & DeNisi 1996 |
| Debriefs d=0.67 (~25%); facilitated d=0.75; text enough. | Five-line facilitated debrief. | Tannenbaum & Cerasoli 2013 |
| Debriefing successes and failures beats failures only. | One "what worked" line, mechanical. | Ellis & Davidi 2005 |
| Outcome bias persists even in people who reject it. | Process block first. | Baron & Hershey 1988 |
| Implementation intentions d=0.65 (94 tests); progress monitoring d=0.40, more when recorded and reported. | If-then goal; code counts trigger and action; next Friday opens with it. | Gollwitzer & Sheeran 2006; Harkin et al. 2016 |
| Learning goals beat numeric targets on complex tasks. | Behaviour goals only; never R or P&L. | Seijts & Latham 2005 |
| Fresh start: +33.4% at the start of a week. | Goal starts Monday. | Dai, Milkman & Riis 2014 |
| Practice explains <1% of variance in professions. | The review cuts leaks; no skill claims. | Macnamara et al. 2014 (vs Ericsson 1993) |

## 3. Small samples

| Finding | What it changes | Source |
|---|---|---|
| Law of small numbers: replication odds guessed ~.85 vs ~.48. | State uncertainty explicitly. | Tversky & Kahneman 1971 |
| Streak statistics biased (−8 points for a fair coin, n=100). | No streak-based tilt on outcomes. | Miller & Sanjurjo 2018 |
| Wilson/Jeffreys, not Wald. 3/5 → 23–88%; 12/20 → 39–78%. | Wilson 95% on every hit rate. | Brown, Cai & DasGupta 2001; NIST |
| James-Stein 3.5× more accurate after 45 at-bats; beta-binomial k≈10 for a ±15% prior. | Shrunk hit rate (k=10) first; mean R × n/(n+36). | Efron & Morris 1975 |
| SE of mean R 0.67 at 5 ideas, 0.34 at 20; +0.25R needs ~283–285 ideas; t-interval optimistic with fat tails. | t-interval labelled optimistic + median; standing power caption. | power calculation; simulation |
| Sharpe SE ≈ √((1+SR²/2)/T); min track record for SR 1.5 ≈ 1.2–1.4 yrs, SR 1.0 ≈ 2.7–2.9 yrs. | No Sharpe verdict before then. | Lo 2002; Bailey & López de Prado (via secondary) |
| Multiple testing; 12 weekly metrics → 46% chance of a false flag. | No significance flags; slices only at 20+ each. | Harvey & Liu 2015; Benjamini & Hochberg 1995 |
| Brier components biased at small n; calibrated forecaster's Brier at n=10 spans 0.14–0.31. | Brier only on stated P(win), with a no-claim note under 30; calibration bins from 30 (10 per bin). | Siegert et al.; Bröcker & Smith 2007 |
| Regression to the mean. | Extreme-week caption; no change on one week's outcome. | Kahneman (via onlinestatbook) |

## 4. Atlas, books, vendors

- **Atlas:** NBIM's first AI money came from an Investment Simulator scoring PMs' timing, sizing and reactions (4.5 step 5); Cohen coaches with behaviour data ("holding losers too long"); JPMorgan Spectrum flags holdings past their best holding period; Dalio "Pain + Reflection = Progress"; Druckenmiller "don't spend 48 hours punishing yourself"; Tudor Jones "losers average losers"; Soros and Kovner on exits.
- **Mandala:** Zweig #2 weekly; #7, #8, #10 monthly.
- **Books** (not page-checked): Steenbarger (process goals, study your best trades), Tharp (R, expectancy; SQN is a t-statistic), Mauboussin (luck → judge process), Duke (resulting).
- **Vendors:** Essentia (exit timing, holding-period decay, nudges), Alpha Theory (sizing vs targets), Cabot (sell discipline), Inalytics (attribution). All need years of real history; the paper build keeps light, journal-native versions; for the corporate build they go on the January vendor review.

## 5. Where sources disagree

Tilt direction (both measured); holding losers costly? (judge against own invalidation); feedback helps vs hurts (task-level + goal); successes (mechanism, not praise); deliberate practice (leaks, not skill); vendor sizing gains (direction, not effect size).

## 6. Design changes vs the plan

| Rule | Plan | Now |
|---|---|---|
| Order | stats, commentary | Process block first, outcomes after |
| Small samples | — | <10 counts only; 10–29 intervals + shrunk; 30+ slices (20 each) and 3-bin calibration; 100+ per level |
| Hit rate | raw | Shrunk (k=10 to sizing priors) + Wilson; raw beside |
| Average R | raw | Mean + t-interval (optimistic) + median; shrunk n/(n+36); power caption |
| Holding losers | winner vs loser time | Days past invalidation and horizon; medians only at 10 each |
| Tilt | count | New ideas and size within 3 days of ±1R closes, both directions; vs prior median size |
| Overtrading | count | vs trailing 8-week median |
| Exits | sizing-review exits | Trigger tagged at close (required); R after exit by trigger, complete windows only |
| Calibration | Brier | Stated P(win) only |
| Trends | — | None until 20 per group; no significance flags |
| Extreme week | — | Regression-to-the-mean caption |
| Commentary | 5 lines | Debrief: process; biggest leak; what worked; outcomes with range; gate or sizing gap |
| Goal | one goal | One if-then goal from a 9-item catalogue, most misses over 4 weeks; active Monday unless he changes it; his own goal never overwritten; tracked by code |
| Monthly | #7, #8, #10 | Alerts acted on by kind (descriptive); regime table; post-mortems |
| Window | — | 7 days ending 18:00 BRT Friday |

Decided by Bernardo (10 Oct): goal active Monday unless changed; exit trigger required at close; monthly on the first Friday after month end.

## 7. Live run and review

9 Oct: only the example in the journal → counts-only, gate 0 of 10, proposed goal `log-ideas` from 12 Oct; monthly (September, for format): Brent 21-day vol 42.5% (80th pct), RBOB 52.3% (93rd), dollar 4.5% (14th), 2y +71bp over 63 days. Draft Friday page: 34 of 34 figures matched by the auditor.

Independent review (separate agent) found 11 defects, all fixed with tests: weekend/Friday-evening entries in no week; Friday proposal overwrote his goal; invalidation goal counted closed/untaken ideas and notes written before the cross; 4-week window vs one-week median; Brier on the sizing blend; critic questions judged before 48h; zero suggestion never a sizing miss; passes broke the after-loss pause; auditor let one market's figure vouch for another and read line-start figures as list numbers.

## Sources
Full linked list in the Docs page (above).
