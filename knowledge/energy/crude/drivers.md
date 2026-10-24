# Drivers: crude

Rendered from `drivers.yaml` by `pmstack/knowledge.py`; do not edit by hand. Each size says where it came from (literature, own estimate, Bernardo prior). Status comes from the testing gate (`/research`); "untested" claims are hypotheses, not signals.

## inventory-vs-basis

- **Claim:** Lower inventories relative to normal go with a higher basis (backwardation): the convenience yield falls, non-linearly, as stocks rise.
- **Driver → target:** Inventory vs normal (I/I*, actual over HP-trend inventory) → Basis, near minus next contract (%/yr)
- **Sign / lag:** - / same month
- **Status:** literature only
- **Source:** Theory of storage (Kaldor 1939; Working 1949; Brennan 1958; Pindyck 2001); Gorton, Hayashi & Rouwenhorst (2013)
- Size, literature: -303.9 %/yr basis per unit I/I* (at I/I* = 1) ([Gorton, Hayashi & Rouwenhorst (2013), NBER WP 13249 (crude, t -6.06, R2 0.46; WP numbers)](https://www.nber.org/system/files/working_papers/w13249/w13249.pdf), Table 3)
- Notes: For energy, slopes at I/I* = 1 and 0.75 do not differ significantly: use a roughly linear local slope. Part of the basis is a risk premium whose sign changed after 2005 (Hamilton & Wu 2014). Own estimate on repo data waits for the S2 curve module (collection started 24 Oct 2026).

## price-elasticity-of-demand

- **Claim:** World oil demand responds little to price in the short run.
- **Driver → target:** Real oil price → World oil demand (use)
- **Sign / lag:** - / impact (one month)
- **Status:** literature only
- **Source:** Kilian & Murphy (2014); Baumeister & Hamilton (2019); Caldara, Cavallo & Iacoviello (2019)
- Size, literature: -0.26 elasticity, range -0.54 to -0.09 ([Kilian & Murphy (2011 WP), 68% band](https://www.frbsf.org/Kilian_Role-of-Inventories-and-Speculative-Trading.pdf), p.27, Table 2)
- Size, literature: -0.35 elasticity ([Baumeister & Hamilton (2015 WP), posterior median](https://www.socialpolitik.de/sites/default/files/ausschuss/makrooekonomie/update_09_11_2017/DP2017-03_BaumeisterHamilton.pdf), p.24, Table 2)
- Size, literature: -0.08 elasticity ([Caldara, Cavallo & Iacoviello (2019), narrative/IV estimate](https://www.matteoiacoviello.com/research_files/CCI.pdf), pp.3, 12)
- Notes: Estimates depend on identification (Baumeister & Hamilton 2020 vs Kilian & Zhou 2019): quote the range, never one number. Hamilton (2009): a 5.5 mb/d demand shift against flat supply takes $55 to $142 at elasticity 0.06, to $97 at 0.10.

## price-elasticity-of-supply

- **Claim:** World oil supply responds little to price within a month.
- **Driver → target:** Real oil price → World oil production
- **Sign / lag:** + / impact (one month)
- **Status:** literature only
- **Source:** Kilian & Murphy (2014); Baumeister & Hamilton (2019); Caldara, Cavallo & Iacoviello (2019)
- Size, literature: 0.025 elasticity ([Kilian & Murphy (2011 WP), upper bound](https://www.frbsf.org/Kilian_Role-of-Inventories-and-Speculative-Trading.pdf), p.12)
- Size, literature: 0.16 elasticity ([Baumeister & Hamilton (2015 WP), posterior median](https://www.socialpolitik.de/sites/default/files/ausschuss/makrooekonomie/update_09_11_2017/DP2017-03_BaumeisterHamilton.pdf), p.24)
- Size, literature: 0.081 elasticity ([Caldara, Cavallo & Iacoviello (2019), narrative/IV estimate](https://www.matteoiacoviello.com/research_files/CCI.pdf), pp.3, 12)
- Notes: Setting it to zero cuts the supply share of price variance from about 36% to about 2% (CCI Table 5): attributing a move to supply or demand is model-dependent inference.

## opec-supply-news

- **Claim:** OPEC announcements that signal less future supply raise the price at once, lower production only gradually and build inventories first.
- **Driver → target:** OPEC supply-news shock (futures move on announcement days) → World oil inventories
- **Sign / lag:** + / peak response, months
- **Status:** literature only
- **Source:** Känzig (2021) AER
- Size, literature: 1.2 % inventories per news shock that lifts the oil price 10% ([Känzig (2021), MPRA WP](https://mpra.ub.uni-muenchen.de/106249/1/MPRA_paper_106249.pdf), pp.19-20)
- Notes: On OPEC days a price rise with stocks building is consistent with supply news, not a contradiction.

## brent-wti-cushing

- **Claim:** The Brent-WTI spread follows Cushing infrastructure bottlenecks, the business cycle and the WTI prompt slope; the Cushing stock level alone is not significant.
- **Driver → target:** Cushing capacity utilisation and WTI prompt slope → Brent-WTI spread
- **Sign / lag:** ? / same month
- **Status:** literature only
- **Source:** Büyükşahin, Lee, Moser & Robe (2013), Energy Journal; WP https://www.eia.gov/finance/markets/reports_presentations/2012PaperBrentWTI.pdf
- Notes: Use the Cushing fill ratio (stocks over working capacity) and the WTI M1-M2, not barrels. Positioning predicts but does not Granger-cause the spread.

## shock-type-attribution

- **Claim:** Oil price moves have causes with different dynamics: precautionary demand (immediate, large, persistent), aggregate demand (delayed, sustained), supply disruptions (small, transitory).
- **Driver → target:** Shock type (supply, aggregate demand, oil-specific demand) → Real oil price path
- **Sign / lag:** ? / up to 14 months
- **Status:** literature only
- **Source:** Kilian (2009) AER; Ready (2018) for a daily equity-based split
- Notes: Any decomposition is model-dependent inference: show a range, label it.

## eia-crude-surprise-wti

- **Claim:** A bigger-than-normal draw in US crude stocks (vs the 5-year same-week change) goes with a WTI rise on release day.
- **Driver → target:** US crude stocks ex SPR, weekly change minus 5-year same-week average (sd) → WTI front-month return on the WPSR release day
- **Sign / lag:** - / same day (contemporaneous)
- **Status:** untested
- **Source:** pmstack events (EIA WPSR, Yahoo CL=F); see events.md
- Size, own estimate: -0.348 % per 1 sd surprise, 90% CI -0.447 to -0.249, n 1341, as of 2026-10-23 ([regression](knowledge/energy/crude/estimates/wpsr-crude_wti.json))
- Notes: Explains the release-day move; predicts nothing. The day before also moves with the surprise (t about -3): API's Tuesday report or leakage, so the release-day slope understates the total reaction.

## eia-crude-surprise-brent

- **Claim:** The same US crude surprise moves Brent less than WTI, and not at all in the second half of the sample.
- **Driver → target:** US crude stocks ex SPR surprise (sd) → Brent front-month return on release day
- **Sign / lag:** - / same day (contemporaneous)
- **Status:** untested
- **Source:** pmstack events
- Size, own estimate: -0.159 % per 1 sd surprise, 90% CI -0.264 to -0.053, n 988, as of 2026-10-23 ([regression](knowledge/energy/crude/estimates/wpsr-crude_brent.json))
- Notes: Second-half slope near zero: US stocks matter less for the waterborne benchmark in the US export era (inference).
