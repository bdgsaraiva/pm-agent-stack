# Drivers: aluminium

Rendered from `drivers.yaml` by `pmstack/knowledge.py`; do not edit by hand. Each size says where it came from (literature, own estimate, Bernardo prior). Status comes from the testing gate (`/research`); "untested" claims are hypotheses, not signals.

## demand-shocks-dominate

- **Claim:** Long-run metal price swings are driven mostly by demand shocks (industrialisation, urbanisation); supply shocks are smaller and shorter.
- **Driver → target:** World (China-led) industrial demand → Real metal price
- **Sign / lag:** + / years
- **Status:** literature only
- **Source:** Stuermer (2018); Jacks & Stuermer (2020); Erten & Ocampo (2013)
- Size, literature: 15 years an effect lasts: demand shocks up to ~15, supply shocks ~5, range 5.0 to 15.0 ([Stuermer (2014 WP; Macroeconomic Dynamics 2018), 150 years of boom and bust](https://www.dallasfed.org/-/media/documents/research/papers/2014/wp1414.pdf), abstract)
- Notes: Copper and tin are exceptions where supply shocks matter more (oligopolistic structure). Context for the long-run block, never a timing signal.

## visible-stocks-vs-spread

- **Claim:** Lower visible stocks (LME + SHFE) go with a stronger LME backwardation (cash over 3-month): the theory of storage.
- **Driver → target:** Log visible stocks (LME + SHFE) → LME cash-3m spread, % of 3-month
- **Sign / lag:** - / same week
- **Status:** untested (study `Weekly SHFE report days since 2014; Newey-West errors; 3 chronological blocks; ADF on the residual`)
- **Source:** Fama & French (1988); Geman & Smith (2013); own estimate (pmstack metals)
- Size, own estimate: -0.657 pp of the net-of-interest cash-3m spread (% of 3m) per 1 log unit of visible stocks, full sample (Newey-West t -4.14), n 637, as of 2026-10-23 ([regression](knowledge/metals/aluminium/estimates/storage.json#fits.spread_pct))
- Size, own estimate: -0.326 same, latest block 2022-08 to 2026-07 (t -0.44; the last quarter held out), n 200, as of 2026-10-23 ([regression](knowledge/metals/aluminium/estimates/storage.json#fits.spread_pct.blocks))
- Notes: Spread net of interest (raw + 3-month T-bill x 91/360; review S3: the raw spread mixed in the rate level). Blocks agree in sign: True; full slope inside the block range: True; residual ADF t -7.74 (Engle-Granger 5% critical -3.34). Today's inventory-implied spread is fitted without the last quarter and suppressed when the fit is weak. The volatility predictions (realised vol, cash/3m vol ratio) are not supported on these data: block signs disagree. Contemporaneous, never a forecast.

## lme-stock-surprise

- **Claim:** A bigger-than-normal LME stock draw goes with a price rise on the report day.
- **Driver → target:** LME stock change vs its own norm, in sd → LME aluminium 3-month daily return
- **Sign / lag:** - / report day
- **Status:** untested
- **Source:** own estimate (pmstack metals); method as the EIA playbooks
- Size, own estimate: -0.0228 % per 1 sd stock surprise (report day, 90% CI), 90% CI -0.046 to 0.0, n 4637, as of 2026-10-23 ([regression](knowledge/metals/aluminium/estimates/stocks-lme_aluminium.json))
- Size, own estimate: -0.008 % per 1 sd stock surprise, since 2015 (90% CI), 90% CI -0.027 to 0.01, n 2983, as of 2026-10-23 ([regression](knowledge/metals/aluminium/estimates/stocks-lme_aluminium.json#eras.since_2015))
- Notes: Sign hit 0.529 of 414 reports with abs(z) >= 1; day before -0.031 (t -1.96), day after -0.014 (t -1.34). Contemporaneous association, predicts nothing.

## shfe-stock-surprise

- **Claim:** A bigger-than-normal SHFE stock draw goes with a price rise on the report day.
- **Driver → target:** SHFE stock change vs its own norm, in sd → LME aluminium 3-month daily return
- **Sign / lag:** - / report day
- **Status:** untested
- **Source:** own estimate (pmstack metals); method as the EIA playbooks
- Size, own estimate: -0.0103 % per 1 sd stock surprise (report day, 90% CI), 90% CI -0.136 to 0.115, n 340, as of 2026-10-23 ([regression](knowledge/metals/aluminium/estimates/stocks-shfe_aluminium.json))
- Size, own estimate: -0.01 % per 1 sd stock surprise, since 2015 (90% CI), 90% CI -0.136 to 0.115, n 340, as of 2026-10-23 ([regression](knowledge/metals/aluminium/estimates/stocks-shfe_aluminium.json#eras.since_2015))
- Notes: Sign hit 0.514 of 107 reports with abs(z) >= 1; day before -0.162 (t -2.06), day after 0.015 (t 0.25). Contemporaneous association, predicts nothing.

## china-pmi-day-volatility

- **Claim:** NBS PMI days are more volatile than other days.
- **Driver → target:** NBS manufacturing PMI release day → Daily return volatility
- **Sign / lag:** + / release day
- **Status:** untested
- **Source:** own estimate (pmstack metals); gold on the same days as the month-end control
- Size, own estimate: 0.922 sd of returns on NBS PMI days / other days, n 105, as of 2026-10-23 ([regression](knowledge/metals/aluminium/estimates/china-nbs_pmi.json))
- Notes: Ratio vs the gold control 0.941; placebo -5/+5 trading days {'-5d': 1.077, '+10d': 1.048}. Since 2018 (release rule documented by NBS calendars).

## power-cost

- **Claim:** Higher power costs (coal in China, gas-linked power in Europe) raise the aluminium cost curve and curtail smelters.
- **Driver → target:** Smelter power cost → Aluminium price, smelter output
- **Sign / lag:** + / months
- **Status:** literature only
- **Source:** S&P Global Commodity Insights news (power usually over a third of cost); no study found tying curtailments to power prices
- Notes: No size: no quantified public study found (25 Oct). Candidate for Bernardo's priors.

## china-capacity-cap

- **Claim:** China's ~45 Mt smelting capacity cap (since 2017) limits Chinese supply growth to debottlenecking.
- **Driver → target:** Chinese capacity policy → World primary supply growth
- **Sign / lag:** - / years
- **Status:** literature only
- **Source:** Reuters via Engineering News (Sep 2026); SMM
- Notes: Sources disagree on 45 vs 45.5 Mt; output ran above the cap in 2026 through debottlenecking.
