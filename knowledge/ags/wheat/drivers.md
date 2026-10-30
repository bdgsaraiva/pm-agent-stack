# Drivers: wheat

Rendered from `drivers.yaml` by `pmstack/knowledge.py`; do not edit by hand. Each size says where it came from (literature, own estimate, Bernardo prior). Status comes from the testing gate (`/research`); "untested" claims are hypotheses, not signals.

## stocks-to-use

- **Claim:** Low stocks-to-use makes price more sensitive to small supply and demand shocks (spikes happen near minimal stocks).
- **Driver → target:** Stocks-to-use (WASDE, agent 9) and its percentile → Price level and volatility
- **Sign / lag:** - / same season
- **Status:** literature only
- **Source:** Wright (2011/2012); Adjemian (2012) (larger WASDE effects at low carryover)
- Notes: Read as sensitivity, not direction. No size: the relation is non-linear and the literature gives no portable slope.

## enso

- **Claim:** ENSO shifts global yields: El Niño has raised soybean yields and changed other crops slightly; La Niña lowers yields of all four major crops.
- **Driver → target:** Oceanic Niño Index (NOAA) → Global yields; prices at intermediate horizons
- **Sign / lag:** ? / months to a season
- **Status:** literature only
- **Source:** Iizumi et al. (2014); Ubilava (2018)
- Size, literature: -4.3 to 0.8 % change in global-mean maize, rice and wheat yields in El Niño years (soybeans: likely higher) ([Iizumi et al. (2014), Nature Communications 5:3712](https://eprints.whiterose.ac.uk/id/eprint/80272/), abstract)
- Size, literature: -4.5 to 0.0 % change in global-mean yields of maize, rice, wheat and soybeans in La Niña years ([Iizumi et al. (2014), Nature Communications 5:3712](https://eprints.whiterose.ac.uk/id/eprint/80272/), abstract)
- Size, literature: 30 % of price variation at intermediate horizons attributed to ENSO shocks (up to; working-paper listing) ([Ubilava (2018), AJAE 100(1)](https://ideas.repec.org/a/oup/ajagec/v100y2018i1p239-263..html), WP listing)
- Notes: Context, never a forecast: effects differ by region and crop calendar.

## wasde-day-volatility

- **Claim:** WASDE (months without Grain Stocks) days are more volatile than the days around them.
- **Driver → target:** WASDE (months without Grain Stocks) release day → CBOT wheat (SRW) daily return volatility
- **Sign / lag:** + / release day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Adjemian (2012) for WASDE
- Size, own estimate: 1.086 mean abs(return)/sd on report days over the 10 days either side (paired t 1.79), n 293, as of 2026-10-29 ([regression](knowledge/ags/wheat/estimates/wasde-days.json#local))
- Notes: Vs all other days 1.103; placebo local ratios -5d 1.003, +10d 0.831. Day categories are disjoint (no day counted twice). Contemporaneous, predicts nothing.

## january-day-volatility

- **Claim:** January WASDE + annual Crop Production + Grain Stocks days are more volatile than the days around them.
- **Driver → target:** January WASDE + annual Crop Production + Grain Stocks release day → CBOT wheat (SRW) daily return volatility
- **Sign / lag:** + / release day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Adjemian (2012) for WASDE
- Size, own estimate: 1.847 mean abs(return)/sd on report days over the 10 days either side (paired t 3.14), n 26, as of 2026-10-29 ([regression](knowledge/ags/wheat/estimates/january-days.json#local))
- Notes: Vs all other days 1.669; placebo local ratios -5d 1.327, +10d 1.049. Day categories are disjoint (no day counted twice). Contemporaneous, predicts nothing.

## stocks-plantings-day-volatility

- **Claim:** March and June Grain Stocks + Prospective Plantings / Acreage days are more volatile than the days around them.
- **Driver → target:** March and June Grain Stocks + Prospective Plantings / Acreage release day → CBOT wheat (SRW) daily return volatility
- **Sign / lag:** + / release day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Adjemian (2012) for WASDE
- Size, own estimate: 1.791 mean abs(return)/sd on report days over the 10 days either side (paired t 4.11), n 51, as of 2026-10-29 ([regression](knowledge/ags/wheat/estimates/stocks_plantings-days.json#local))
- Notes: Vs all other days 1.794; placebo local ratios -5d 0.783, +10d 1.286. Day categories are disjoint (no day counted twice). Contemporaneous, predicts nothing.

## grain-stocks-alone-day-volatility

- **Claim:** September Grain Stocks (alone) days are more volatile than the days around them.
- **Driver → target:** September Grain Stocks (alone) release day → CBOT wheat (SRW) daily return volatility
- **Sign / lag:** + / release day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Adjemian (2012) for WASDE
- Size, own estimate: 1.564 mean abs(return)/sd on report days over the 10 days either side (paired t 2.46), n 30, as of 2026-10-29 ([regression](knowledge/ags/wheat/estimates/grain_stocks_alone-days.json#local))
- Notes: Vs all other days 1.446; placebo local ratios -5d 0.751, +10d None. Day categories are disjoint (no day counted twice). Contemporaneous, predicts nothing.

## wasde-ending-stocks-revision

- **Claim:** A US ending-stocks revision up (vs the previous WASDE) goes with a lower price on the day.
- **Driver → target:** Revision of US ending stocks vs the previous report, in sd → Same-day return
- **Sign / lag:** - / report day
- **Status:** untested
- **Source:** own estimate (pmstack ags), WASDE as first published (agent 9)
- Size, own estimate: -0.2193 % per 1 sd revision (90% CI; t -0.63), 90% CI -0.7963 to 0.3577, n 54, as of 2026-10-29 ([regression](knowledge/ags/wheat/estimates/wasde-days.json#revision))
- Notes: Only 7 revisions of at least 1 sd: too few for a sign-agreement rate. No consensus is stored: part of the revision was expected, so the slope is attenuated.

## condition-winter-wheat

- **Claim:** A bigger-than-seasonal improvement in winter wheat condition goes with a lower price the next day.
- **Driver → target:** Weekly good + excellent change vs its seasonal norm, in sd → ZW=F next-day return
- **Sign / lag:** - / next trading day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Lehecka (2014) finds reactions, strongest July-August
- Size, own estimate: -0.2191 % per 1 sd condition surprise (90% CI), 90% CI -0.458 to 0.02, n 119, as of 2026-10-29 ([regression](knowledge/ags/wheat/estimates/crop_progress-winter_wheat.json))
- Notes: From 2019 (five prior seasons for the norm, changes across seasons left out): t -1.5064 (not significant on its own); sign hit 0.511 of 45.

## condition-spring-wheat

- **Claim:** A bigger-than-seasonal improvement in spring wheat condition goes with a lower price the next day.
- **Driver → target:** Weekly good + excellent change vs its seasonal norm, in sd → ZW=F next-day return
- **Sign / lag:** - / next trading day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Lehecka (2014) finds reactions, strongest July-August
- Size, own estimate: -0.2446 % per 1 sd condition surprise (90% CI), 90% CI -0.536 to 0.047, n 76, as of 2026-10-29 ([regression](knowledge/ags/wheat/estimates/crop_progress-spring_wheat.json))
- Notes: From 2020 (five prior seasons for the norm, changes across seasons left out): t -1.3802 (not significant on its own); sign hit 0.607 of 28.
