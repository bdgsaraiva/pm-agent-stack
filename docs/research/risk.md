# Risk and crowding (agent 8): literature review

Full write-up (Docs): https://claude.ai/code/artifact/f4a74a73-6de9-4269-8832-8b7959f1f5d2 · 10 Oct 2026

**Bottom line.** The evidence supports *measuring* concentration and stress losses in R and *describing* crowding, not predicting crashes from positioning.
- Correlations rise in sell-offs, mostly on the downside; part of the rise is mechanical. Stress P&L uses a stress matrix; no alert fires on a raw correlation jump.
- Stress losses come from scenario shocks, not sigma multiples, with stops honoured and gapped.
- CFTC levels mostly restate returns; weekly changes carry a small, short reversal; crowding matters most when funding stresses.
- CTA levels are context. Early warnings rest on realised losses and persistent turbulence.

Bernardo's choices (10 Oct 2026): **no budget caps, numbers only**; **amber early, red = the sizing cut counting open marks**; **replays + 6 named shocks + worst case**.

## Papers: crowding, deleveraging, fire sales

| Finding | What it changes | Source |
|---|---|---|
| Aug 2007: contrarian book −3.99% day 1, +8.20% over 5 days; factors back within 2% by 13 Aug | Stop-outs on cross-market deleveraging days are a post-mortem tag, not an override | [Khandani & Lo](https://www.nber.org/system/files/working_papers/w14465/w14465.pdf) |
| A 6%-vol book lost ~25% in 4 days, >30 sd of its 4-day vol | Stress from scenario shocks; gapped column (loss can exceed 1R) | [Pedersen 2009](https://www.nber.org/system/files/working_papers/w15297/w15297.pdf) |
| Margin and loss spirals; illiquidity co-moves, more in down markets | Funding state (HY OAS change, VIX) conditions crowding | [Brunnermeier & Pedersen 2009](https://www.princeton.edu/~markus/research/papers/liquidity.pdf) |
| Comomentum: −1.07%/month in years 1–2 after high-crowding periods; equities only | Not built (horizon years; partly restates vol) | [Lou & Polk](https://personal.lse.ac.uk/polk/research/comomentum.pdf) |
| Post-2008: +1 sd VIX → index traders −0.20 sd, hedge funds −0.12 sd, ag prices ~−1.5%; insignificant before 2008 | Risk-off funding scenario; crowding red only when funding stresses | [Cheng, Kirilenko & Xiong 2015](https://www.cftc.gov/idc/groups/public/@economicanalysis/documents/file/oce_convectiverisk0314.pdf) |
| Fire sales: −10.07% event quarter, +7.74% months 4–12 | Crowding = path risk to the stop | [Coval & Stafford](https://www.nber.org/papers/w11357.pdf) |
| Dislocations last months when outside capital is scarce | No snap-back assumed | [Mitchell, Pedersen & Pulvino](https://www.nber.org/system/files/working_papers/w12877/w12877.pdf) |
| Index-commodity correlation with oil <0.1 → ~0.5 by 2009 | Calm correlations understate stress | [Tang & Xiong](https://www.nber.org/system/files/working_papers/w16385/w16385.pdf) |
| Counterpoint: stock–commodity correlation 0.05 → 0.52 → back near zero; tracks the default spread | Stress matrix from turbulence, not a fixed regime | [Bhardwaj, Gorton & Rouwenhorst 2015](https://www.nber.org/system/files/working_papers/w21243/w21243.pdf) |
| Hedge-fund share raises equity–commodity correlation; index traders don't | Managed money is the crowding variable | [Büyükşahin & Robe](https://www.ou.edu/dam/price/Finance/Oklahoma_conference/2011/Michel%20Robe%20paper.pdf) |
| Hedge-fund position changes lower vol (crude, natgas) | No "vol risk" caption on heavy length | [Brunetti, Büyükşahin & Harris](https://www.bankofcanada.ca/wp-content/uploads/2015/11/wp2015-42.pdf) |
| Counterpoint: positions predict in 1 of 10 markets; returns lead in 10 of 10 | CFTC level never alerts; ex-trend residual shown | [Sanders, Irwin & Merrin 2009](https://ageconsearch.umn.edu/record/54547/files/JARE_Aug09__04R_pp276-296.pdf) |
| Weekly speculator changes: ~−0.17% next week per 3% of OI; gone in 20 days; levels don't predict | "Crowded entry" from the weekly change z-score | [Kang, Rouwenhorst & Tang](https://www7.uc.cl/economia/finance_uc/docs/conferences/11th/Rouwenhorst-Tale%20of%20two%20premiums.pdf) |
| Return-based crowding ~5x weaker than order-flow crowding | Not built | [Volpati et al. 2020](https://arxiv.org/pdf/2001.04185) |
| Counterpoint (abstract): crowding relates negatively to momentum crash risk | Flags log base rate and lift before alerting | [Barroso, Edelen & Karehnke](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/crowding-and-tail-risk-in-momentum-returns/870ADE1D7ADCE877CD4C3F5E71581E15) |

## Papers: correlation and stress testing

| Finding | What it changes | Source |
|---|---|---|
| Downside tail correlation rises with the threshold (0.53 → 0.68); upside falls | Stress matrix from turbulent days | [Longin & Solnik 2001](https://repec.cepr.org/repec/cpr/ceprdp/Dp2538.pdf) |
| Downside correlation +11.6 pts above normal; petroleum most asymmetric | Calm/stress pair, not GARCH | [Ang & Chen 2002](https://drupalgsb-test.paas.cc.columbia.edu/sites/default/files-efs/pubfiles/1516/corr.pdf) |
| Counterpoint: correlation rises mechanically with variance | No correlation-breakdown alert | [Forbes & Rigobon 2002](https://www.nber.org/system/files/working_papers/w7267/w7267.pdf) |
| Turbulence = Mahalanobis distance; persists for weeks | Top-20% days define stress; 3 of 5 days persistent = warning | [Kritzman & Li 2010](https://rpc.cfainstitute.org/research/financial-analysts-journal/2010/skulls-financial-turbulence-and-risk-management) |
| Worst case inside a plausibility ellipsoid beats hand-picked scenarios | Worst case at k = 3 with implied moves | [Breuer et al. 2009](https://www.ijcb.org/sites/default/files/journal/v5n3/ijcb-v5n3-how-find-plausible-severe-and-useful-stress-scenarios.pdf) |
| Stress tests need probabilities, in one framework with normal risk | k on every row; normal sd and stress on one table | [Berkowitz 1999](https://www.federalreserve.gov/pubs/feds/1999/199929/199929pap.pdf) |
| Drive a few factors, push consistently to every holding | Named scenarios via conditional mean under the stress matrix | [Rebonato & Denev](https://mpra.ub.uni-muenchen.de/30534/) |
| Empirical-likelihood scenarios need many tail points | Not built | [Glasserman, Kang & Kang 2015](https://www.financialresearch.gov/working-papers/files/OFRwp0007_GlassermanKangKang_StressScenarioSelectionbyEmpiricalLikelihood.pdf) |
| Constant-correlation shrinkage improves estimates | Ledoit–Wolf on both matrices | [Ledoit & Wolf](https://econ-papers.upf.edu/papers/691.pdf) |
| 0.94 decay too short for covariance | EWMA 0.94 for vol only; 250 days for correlation | [Tan & Zohren](https://arxiv.org/pdf/2012.05757v2) |
| DR² = effective independent bets | Effective independent ideas, capped at the count | [Portfolio Optimizer on Choueifaty](https://portfoliooptimizer.io/blog/the-diversification-ratio-measuring-portfolio-diversification) |
| Oil demand vs supply shocks move stocks oppositely; oil–equity sign is regime-dependent | Two oil scenarios with opposite equity signs | [Kilian & Park 2009](https://cepr.org/publications/dp6166); [Datta et al. 2018](https://www.federalreserve.gov/econres/feds/files/2018058pap.pdf) |
| Stress tests are poor early warnings | Warnings from realised signals only | [Borio, Drehmann & Tsatsaronis 2012](https://www.bis.org/publ/work369.htm) |

## Papers: CTA levels and vol-target flows

| Finding | What it changes | Source |
|---|---|---|
| Trend 1–12 months; positions scaled to vol | Vol-target scale beside the sign | [Moskowitz, Ooi & Pedersen 2012](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf) |
| CTA share of the market: commodities 5.8%, equities 0.2% | CTA levels matter most in commodities | [Hurst, Ooi & Pedersen](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf) |
| Fast and slow disagree ~35% of months | Correction/Rebound as a state | [Goulding, Harvey & Mazzoleni](https://benny.aeaweb.org/conference/2021/preliminary/paper/492Ds6fk) |
| Momentum crashes in panic states | Panic flag on with-trend shorts | [Daniel & Moskowitz 2016](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf) |
| Vol targeting helps tails everywhere, Sharpe only in equities/credit | Vol-target scale (60 ÷ 20 half-life); risk tool only | [Harvey et al. 2018](https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf); counterpoint [Cederburg et al. 2020](https://www.lehigh.edu/~xuy219/research/COWY.pdf) |
| Speeds correlate 22%; no capacity effect | Every leg's level shown | [Baltas & Kosowski](https://efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2012-Barcelona/papers/BK_MOMF_Full.pdf) |
| Dollar flows need an AUM guess | Direction and distance only | [Macrosynergy](https://macrosynergy.com/research/estimating-the-positioning-of-trend-followers/) |

## Atlas and books
- Atlas 1.8 / 2C: platforms lost together in the March 2026 war week and the July AI slide → both are replays from our own closes.
- Kovner, Englander: correlated bets are one bet → effective independent ideas, clusters. Howard, Platt, Tudor Jones: mechanical cuts after drawdowns → one red rule, the sizing cut. Bouchaud: crowding as a risk factor; synthetic histories → replays and driver scenarios. Loeb: cut before stress spreads → open marks count.
- Turtle rules (transcription): 4 / 6 / 10 / 12 unit limits; a 10% drawdown cuts notional 20% → template only; Bernardo chose no caps.
- Pedersen, Rebonato, Bookstaber, Lowenstein, Grinold & Kahn, Taleb, Carver: general knowledge, not page-checked (see the Docs page).

## Where sources disagree (resolution)
- Correlation in sell-offs: use the stress matrix for P&L; never alert on a raw jump.
- Crowding as a predictor: levels are context; weekly changes get a short-horizon flag; red only under funding stress; every flag logs base rate and lift before it may alert.
- Commodity–equity sign: never fixed; two oil scenarios.
- Scenario type: all three (worst case, replays, named), each with k.
- CTA flows: small and temporary on average; levels are context.

## Independent review (12 defects, all fixed before commit)
1. A late price on one series made a false amber jump → marks carry the last close.
2. One idea market reset the model window → turbulence and stress days on the universe only; other markets pairwise, shrunk, PSD-repaired.
3. Look-ahead in `--date` runs → ideas filtered to the as-of day; replays ending later are "not yet happened"; CFTC counted from its Friday release; sizing marks to the as-of close.
4. Red ordered closes and open marks wrongly → one daily marked curve for amber and red.
5. Pack and sizing could disagree on red; example book claimed a cut → one shared function; no red for the example book.
6. Duplicate markets overstated the worst case → exposures summed by market.
7. Past-stop ideas showed the same honoured and gapped loss → exited at today's mark.
8. Replays ignored the path → the window's worst point decides the stop.
9. Effective ideas above the count on hedged books → capped, raw shown.
10. Ideas missing from a scenario were silent → named in the row.
11. Holiday fills made false dates → trading days from the universe; observed last dates.
12. Closed ideas outside the model jumped at close → the curve uses all journal refs and explicit-R closes.
Nits fixed: exact chi-square for k; render can't crash facts.md; facts.json written as strict JSON; turbulence alert links to prices; render reads thresholds from config.
