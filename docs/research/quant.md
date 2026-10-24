# Quant agent (agent 13): literature review and design (S2)

Written 24 Oct 2026 for phase S2 (`docs/project/specialists-kickoff.md`). Two research passes ran as parallel sub-agents:
- trend, carry, term structure, basis momentum and positioning;
- volatility and options, correlation and regimes, seasonality.

The quant-research-standards skill set the reporting rules. Every row was opened on the page it cites. "WP" marks numbers from a working paper rather than the published version. *not page-checked* marks anything not confirmed on an opened page. The pillar design is in `docs/research/specialists-architecture.md`.

## 1. Papers: finding → what it changes

### Trend, carry, term structure, positioning
| Finding | What it changes | Source |
|---|---|---|
| **Moskowitz, Ooi & Pedersen (2012).** The 12-month time-series momentum (TSMOM) return is positive for all 58 futures, and 52 are significant (1985–2009). It persists 1–12 months and partly reverses over the next 4 years. Diversified Sharpe is above 1. Vol is an EWMA with a 60-day centre of mass, used at t−1. Speculator positions rise with past returns and mean-revert within a year. | Legs at 1, 3 and 12 months; nothing beyond 12 months (reversal zone). Positioning goes on the same line as trend because they co-move. | https://ideas.repec.org/a/eee/jfinec/v104y2012i2p228-250.html (author PDF) |
| **Hurst, Ooi & Pedersen (2017; AQR 2014 version).** Equal-weight 1/3/12-month TSMOM across 67 markets, 1880–2013: 11.2% net, net Sharpe 0.77, correlation 0.00 with equities. Recent drawdowns are blamed on higher cross-asset correlation. | Supports equal-weight 1/3/12-month legs. Add an average cross-market correlation line. | https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing |
| **Levine & Pedersen (2016).** TSMOM and moving-average crossovers are equivalent representations (R² above 80% between families). | One return-sign definition, no MA "confirmations". The flip level is the close h days ago. | https://rpc.cfainstitute.org/research/financial-analysts-journal/2016/which-trend-is-your-friend |
| **Counterpoint: Huang, Li, Wang & Zhou (2020).** Little asset-by-asset TSMOM evidence; the strategy is "virtually the same" as a historical-mean book (abstract). | Trend state is a past fact, not a forecast. The testing gate already ran TSMOM against long-only and historical-mean books: verdict no edge (`research/index.md`), shown on the tape. | https://profiles.wustl.edu/en/publications/time-series-momentum-is-it-there/ |
| **Counterpoint: Kim, Tse & Wald (2016).** TSMOM results are "largely driven by volatility-scaling returns" (abstract). | Raw sign and vol-scaled distance are separate fields. Never call a scaled backtest trend alpha. | https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html |
| **Hutchinson & O'Brien (2014).** Trend returns are roughly halved in the first 24 months of crises, except in commodities. | Regime is context only (agent 8's episodes), with no reweighting. | https://www.ucc.ie/en/media/research/centreforinvestmentresearch/wp/TrendFollowingFeb2014.pdf |
| **Bhardwaj, Gorton & Rouwenhorst (2014).** CTAs show no alpha against simple futures strategies. | Simple public-rule flip levels are a fair map of systematic flow (agent 8's CTA levels), not a return benchmark. | https://ideas.repec.org/p/ysm/wpaper/amz2429.html |
| **Koijen, Moskowitz, Pedersen & Vrugt (2018, WP).** Commodity carry C = (F1 − F2) / (F2·(T2 − T1)) per month. "Some commodity futures have strong seasonal components", hence carry1-12. Commodities: current carry 11.7%/yr, Sharpe 0.62. Single-asset carry is a level, not a timing tool. | Carry = M1 over M2, annualised, labelled seasonal for gas and gasoline. carry1-12 waits for 12 months of curve. | https://www.nber.org/papers/w19325 |
| **Erb & Harvey (2006).** The average single commodity earns about zero. Backwardated vs contango is the main term-structure state. | Curve state goes beside trend, with "no guarantee of persistence". | https://people.duke.edu/~charvey/Research/Published_Papers/P91_The_strategic_and.pdf |
| **Szymanowska et al. (2014).** Spot premia 5–14% and term premia 1–3% p.a. across sorts; one basis factor (abstract). | Separate the outright move from the spread move once the curve has history. | https://ideas.repec.org/a/bla/jfinan/v69y2014i1p453-482.html |
| **Boons & Porras Prado (2019).** Basis momentum BM = Π₁₂(1+R¹) − Π₁₂(1+R²), from rolled M1 and M2; high-minus-low 18.38%/yr (t 6.73). | Defined in config. It reads n/a until 12 months of rolled M1/M2 returns exist (about Oct 2027), with no shorter proxy. | https://ideas.repec.org/a/bla/jfinan/v74y2019i1p239-279.html |
| **Bakshi, Gao & Rossi (2019); Fuertes, Miffre & Rallis (2010).** Carry and momentum are separate priced dimensions; a double sort beats either alone. | Report them side by side, never as one score. | https://ideas.repec.org/a/inm/ormnsc/v65y2019i2p619-641.html ; https://openaccess.city.ac.uk/id/eprint/6416/ |
| **Hong & Yogo (2012, WP).** 12-month growth in dollar open interest predicts commodity returns (+0.73%/month per sd, t 2.50), at market level. | Open-interest growth over 12 months per market, descriptive only. | https://www.nber.org/system/files/working_papers/w16712/w16712.pdf |
| **Kang, Rouwenhorst & Tang (2020).** Weekly speculator flow and 52-week hedging pressure act with opposite signs; flow effects last about 20 days. | Positioning on two clocks: weekly change and 52-week average. Never a direction call. | https://ideas.repec.org/a/bla/jfinan/v75y2020i1p377-417.html |
| **Gorton, Hayashi & Rouwenhorst (2013).** No evidence that trader positions predict risk premia. | Positioning stays context. The research loop measured the CFTC crowded flag at no edge. | https://ideas.repec.org/a/oup/revfin/v17y2013i1p35-105.html |

### Volatility, correlation, seasonality
| Finding | What it changes | Source |
|---|---|---|
| **CBOE OVX and GVZ** apply the VIX method to USO and GLD ETF options, for "30-day volatility". FRED: OVXCLS from 2007-05-10, GVZCLS from 2008-06-03, carrying a Cboe copyright line. | 21-session realised vol is the comparison. Label the ETF-vs-futures mismatch. No OVX/GVZ in the public post (public-domain rule). | https://fred.stlouisfed.org/series/OVXCLS ; https://fred.stlouisfed.org/series/GVZCLS |
| **Trolle & Schwartz (2010); Prokopczuk, Symeonidis & Wese Simen (2017).** Variance risk premia are significantly negative in energy, and in 18 of 21 commodities. Synthetic implied correlates 98–99.6% with the CBOE indices. | Implied above realised is the normal state, so the gap is judged by its own percentile, never by its sign. Realised above implied gets one line. | https://research.cbs.dk/en/publications/variance-risk-premia-in-energy-commodities/ ; https://ueaeprints.uea.ac.uk/63547/ |
| **Suenaga, Smith & Williams (2008).** Gas vol is higher in winter. | A same-calendar-month vol percentile for energy and grains. | https://ideas.repec.org/a/wly/jfutmk/v28y2008i5p438-463.html |
| **Chen & Mu (2021); Aboura & Chevallier (2013); Christoffersen, Jacobs & Pan (2022).** The vol-return sign differs by commodity and by measure; oil's state-price density is U-shaped. | No "vol up = price down" prior. Implied vol moves are two-sided. | https://discovery.dundee.ac.uk/en/publications/asymmetric-volatility-in-commodity-markets-2/ ; https://ideas.repec.org/a/oup/rfinst/v35y2022i2p1064-1103..html |
| **Daal, Farhat & Wei (2006).** The Samuelson maturity effect is absent in most contracts. | No maturity adjustment. | https://ideas.repec.org/a/wly/revfec/v15y2006i2p113-128.html |
| **Tang & Xiong (2012); Silvennoinen & Thorp (2013); Büyükşahin & Robe (2014).** Commodity-equity correlation rose from the early 2000s, rises with VIX for about half the pairs, and goes with hedge-fund participation. | Correlation regime against its own 3-year band; no causal claim. | https://ideas.repec.org/p/nbr/nberwo/16385.html ; https://ideas.repec.org/a/eee/intfin/v24y2013icp42-65.html |
| **Counterpoint: Forbes & Rigobon (2002).** Measured correlation rises mechanically with vol. | Every correlation line carries the vol change beside it. | https://www.nber.org/papers/w7267 |
| **Kritzman & Li (2010); Ang & Bekaert (2002).** Turbulence is persistent; a calm/stress split is enough for description. | Reuse agent 8's turbulence; no Markov model. | https://ideas.repec.org/a/taf/ufajxx/v66y2010i5p30-41.html |
| **Moreira & Muir (2017) vs Cederburg et al. (2020); Harvey et al. (2018).** Vol management fails out of sample; for commodities the Sharpe effect is "negligible" but tails shrink. | Vol state is risk context. No "vol is high, reduce" wording; sizing stays in `sizing.py`. | https://www.nber.org/papers/w22208 ; https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf |
| **Keloharju, Linnainmaa & Nyberg (2016).** Commodity return seasonality is marginal (t 1.93) on 24 futures. | Seasonality is a norm, labelled "not a signal". | https://www.aqr.com/-/media/AQR/Documents/AQR-Insight-Award/2015/AllSeasons20141219pdf.pdf |
| **Counterpoint: Sullivan, Timmermann & White (1998/2001).** Calendar effects lose significance against the full rule universe. | Never a best or worst bucket. Any seasonal claim goes through the testing gate. | https://www.fmg.ac.uk/publications/discussion-papers/dangers-data-driven-inference-case-calender-effects-stock-returns |
| **Sørensen (2002).** Grain seasonality lives in price levels and the curve (storage). | Prefer seasonal norms for vol and spreads; return norms come second. | https://ideas.repec.org/a/wly/jfutmk/v22y2002i5p393-426.html |

## 2. Where sources disagree, and the resolution
1. **Does TSMOM exist?** MOP and HOP say yes; Huang et al. say it is a historical mean; Kim et al. say it is vol scaling. Resolution: trend is reported as a past fact. Promotion needs the gate, which says no edge (`p_tsmom_mop2012_v1`).
2. **Is implied vol a forecast?** Implied vol is biased upward by the variance premium. Report implied, realised and the gap with its percentile. Never say "realised will catch up".
3. **Oil's leverage sign:** studies conflict, so it is measured, not assumed.
4. **Correlation: structural or mechanical?** Report the vol change beside it and make no causal claim.
5. **Seasonality:** Keloharju et al. vs Sullivan et al. A norm only, and any claim is counted in the BH ledger.
6. **Positioning:** flow and slow act with opposite signs, and positions don't predict premia. Show both clocks as context.

## 3. Design, as built (`pmstack/quant/`, `config/quant.yaml`)
- **trend.py:** reuses agent 8's `risk.cta_levels` (one implementation, no third). Adds:
  - flipped today (sign change between consecutive closes);
  - stretched: |distance| ≥ 2 sd and beyond the 95th/5th percentile of the leg's own history since 2000, a print rule marked "base rate not studied";
  - today's and this week's move in trailing sd (≥ 2 sd prints as "large vs recent vol").
- **vol.py:** 21- and 63-day realised vol, with the 3-year and full-history percentile and regime (low < 20, high > 80, extreme ≥ 95). Also a same-month percentile for energy and grains, the fast-rise ratio, and the implied gap (OVX, GVZ, VIX) judged by its own percentile, with the ETF instrument labelled.
- **corr.py:** 63-day correlation with ES, the dollar and the 10-year, against a 3-year band, with the own-vol change beside it.
- **seasonal.py:** half-month norm for the next bucket: mean with a 95% interval, median, interquartile range, years up, split halves. No rank, no flag.
- **positioning.py:** CFTC managed money % of open interest, from the Friday release: 3-year percentile, weekly flow, 52-week slow average, and 12-month open-interest growth.
- **curve.py:** front spreads and carry from contracts collected since 24 Oct 2026. No curve before that date, and M1 must be within 3 months. Basis momentum reads n/a with the reason.
- **tape.py:** one table per close (`briefs/<date>/quant.json|md`), flags, changes since the previous tape, and context: the average pairwise commodity correlation, plus the testing gate's verdicts on the CTA and CFTC flags and TSMOM. It also numbers the sources for the tape card.
- **Card:** `config/tape_card.schema.json`, validated like state cards (figures tied to tape rows, sources copied unchanged). Skill `.claude/skills/tape/` + `/tape`.
- **Run times:** `.github/workflows/close.yml` (fetch closes, curve and implied vol; on report days EIA/CFTC; file the week's releases with `pmstack file-reports`; build the tape; commit). The routine "Close tape" starts it at 17:15 New York time on weekdays (inside the CME halt in both US clock regimes), then writes, audits and commits the card (Bernardo, 24 Oct: card every weekday).
- **The morning note** reads only the overnight change against these levels: a spec for the notes track, `docs/project/quant-overnight-spec.md`.

## 4. Open points
- The vol estimators differ: agent 8's `cta_levels` uses EWMA λ 0.94, the tape's percentiles use a trailing 60-day sd, and MOP use a 60-day centre of mass. To unify in agent 8's next revision; for now each is documented where it is used.
- Spot vs roll split and "spans roll" flags need the curve history.
- Stretched and flipped are print rules. Register studies (`/research`) before any use beyond description.
