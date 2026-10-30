# Drivers: corn

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
- **Driver → target:** WASDE (months without Grain Stocks) release day → CBOT corn daily return volatility
- **Sign / lag:** + / release day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Adjemian (2012) for WASDE
- Size, own estimate: 1.314 mean abs(return)/sd on report days over the 10 days either side (paired t 5.2), n 295, as of 2026-10-29 ([regression](knowledge/ags/corn/estimates/wasde-days.json#local))
- Notes: Vs all other days 1.271; placebo local ratios -5d 0.937, +10d 0.802. Day categories are disjoint (no day counted twice). Contemporaneous, predicts nothing.

## january-day-volatility

- **Claim:** January WASDE + annual Crop Production + Grain Stocks days are more volatile than the days around them.
- **Driver → target:** January WASDE + annual Crop Production + Grain Stocks release day → CBOT corn daily return volatility
- **Sign / lag:** + / release day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Adjemian (2012) for WASDE
- Size, own estimate: 3.255 mean abs(return)/sd on report days over the 10 days either side (paired t 5.0), n 25, as of 2026-10-29 ([regression](knowledge/ags/corn/estimates/january-days.json#local))
- Notes: Vs all other days 2.246; placebo local ratios -5d 1.069, +10d 0.942. Day categories are disjoint (no day counted twice). Contemporaneous, predicts nothing.

## stocks-plantings-day-volatility

- **Claim:** March and June Grain Stocks + Prospective Plantings / Acreage days are more volatile than the days around them.
- **Driver → target:** March and June Grain Stocks + Prospective Plantings / Acreage release day → CBOT corn daily return volatility
- **Sign / lag:** + / release day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Adjemian (2012) for WASDE
- Size, own estimate: 2.691 mean abs(return)/sd on report days over the 10 days either side (paired t 6.39), n 52, as of 2026-10-29 ([regression](knowledge/ags/corn/estimates/stocks_plantings-days.json#local))
- Notes: Vs all other days 2.388; placebo local ratios -5d 0.821, +10d 0.978. Day categories are disjoint (no day counted twice). Contemporaneous, predicts nothing.

## grain-stocks-alone-day-volatility

- **Claim:** September Grain Stocks (alone) days are more volatile than the days around them.
- **Driver → target:** September Grain Stocks (alone) release day → CBOT corn daily return volatility
- **Sign / lag:** + / release day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Adjemian (2012) for WASDE
- Size, own estimate: 1.917 mean abs(return)/sd on report days over the 10 days either side (paired t 3.4), n 30, as of 2026-10-29 ([regression](knowledge/ags/corn/estimates/grain_stocks_alone-days.json#local))
- Notes: Vs all other days 1.578; placebo local ratios -5d 0.841, +10d None. Day categories are disjoint (no day counted twice). Contemporaneous, predicts nothing.

## wasde-ending-stocks-revision

- **Claim:** A US ending-stocks revision up (vs the previous WASDE) goes with a lower price on the day.
- **Driver → target:** Revision of US ending stocks vs the previous report, in sd → Same-day return
- **Sign / lag:** - / report day
- **Status:** untested
- **Source:** own estimate (pmstack ags), WASDE as first published (agent 9)
- Size, own estimate: -1.1193 % per 1 sd revision (90% CI; t -3.93), 90% CI -1.5874 to -0.6513, n 54, as of 2026-10-29 ([regression](knowledge/ags/corn/estimates/wasde-days.json#revision))
- Notes: Only 8 revisions of at least 1 sd: too few for a sign-agreement rate. No consensus is stored: part of the revision was expected, so the slope is attenuated.

## condition-corn

- **Claim:** A bigger-than-seasonal improvement in corn condition goes with a lower price the next day.
- **Driver → target:** Weekly good + excellent change vs its seasonal norm, in sd → ZC=F next-day return
- **Sign / lag:** - / next trading day
- **Status:** untested
- **Source:** own estimate (pmstack ags); Lehecka (2014) finds reactions, strongest July-August
- Size, own estimate: -0.2633 % per 1 sd condition surprise (90% CI), 90% CI -0.463 to -0.064, n 132, as of 2026-10-29 ([regression](knowledge/ags/corn/estimates/crop_progress-corn.json))
- Notes: From 2020 (five prior seasons for the norm, changes across seasons left out): t -2.1742; sign hit 0.609 of 46.

## july-heat

- **Claim:** Heat above about 29 °C during pollination cuts corn yields steeply.
- **Driver → target:** Degree days above 29 °C (July) → US corn yield
- **Sign / lag:** - / same season
- **Status:** literature only
- **Source:** Schlenker & Roberts (2009)
- Size, literature: 29 °C threshold above which corn yields fall steeply (soybeans 30 °C) ([Schlenker & Roberts (2009), PNAS](https://pmc.ncbi.nlm.nih.gov/articles/PMC2747166), abstract)
- Notes: No daily temperature data are stored (open question).
