# Drivers: copper

Rendered from `drivers.yaml` by `pmstack/knowledge.py`; do not edit by hand. Each size says where it came from (literature, own estimate, Bernardo prior). Status comes from the testing gate (`/research`); "untested" claims are hypotheses, not signals.

## demand-shocks-dominate

- **Claim:** Long-run metal price swings are driven mostly by demand shocks (industrialisation, urbanisation); supply shocks are smaller and shorter.
- **Driver → target:** World (China-led) industrial demand → Real metal price
- **Sign / lag:** + / years
- **Status:** literature only
- **Source:** Stuermer (2018); Jacks & Stuermer (2020); Erten & Ocampo (2013)
- Size, literature: 15 years an effect lasts: demand shocks up to ~15, supply shocks ~5, range 5.0 to 15.0 ([Stuermer (2014 WP; Macroeconomic Dynamics 2018), 150 years of boom and bust](https://www.dallasfed.org/-/media/documents/research/papers/2014/wp1414.pdf), abstract)
- Notes: Copper and tin are exceptions where supply shocks matter more (oligopolistic structure). Context for the long-run block, never a timing signal.

## china-housing

- **Claim:** Chinese property construction drives base-metal demand and prices.
- **Driver → target:** Chinese housing investment → Base-metal prices
- **Sign / lag:** + / quarters
- **Status:** literature only
- **Source:** Bank of Canada Staff Discussion Paper 2016-7
- Size, literature: 0.25 share of the 85% base-metal price rise in 2002-2010 explained by the Chinese housing boom ([Bank of Canada SDP 2016-7](https://www.bankofcanada.ca/2016/03/staff-discussion-paper-2016-7/), summary page)

## china-collateral-demand

- **Claim:** Under capital controls and high Chinese rates, copper is imported and held as loan collateral, adding demand unrelated to use.
- **Driver → target:** Collateral (financing) demand in China → Industrial-metal prices; Chinese stocks
- **Sign / lag:** + / months
- **Status:** literature only
- **Source:** Tang & Zhu (2016), Review of Financial Studies 29(8)
- Size, literature: 11.9 to 15.0 % of the industrial-metals price rise since 2007 explained by collateral demand (WP) ([Tang & Zhu, Commodities as collateral (WP version)](https://www.mit.edu/~zhuh/TangZhu_CommodityCollateral_RFS.pdf), abstract (WP))
- Notes: A Chinese stock build may be financing, not weak demand: say which reading the card takes.

## visible-stocks-vs-spread

- **Claim:** Lower visible stocks (LME + SHFE) go with a stronger LME backwardation (cash over 3-month): the theory of storage.
- **Driver → target:** Log visible stocks (LME + SHFE) → LME cash-3m spread, % of 3-month
- **Sign / lag:** - / same week
- **Status:** untested (study `Weekly SHFE report days since 2014; Newey-West errors; 3 chronological blocks; ADF on the residual`)
- **Source:** Fama & French (1988); Geman & Smith (2013); own estimate (pmstack metals)
- Size, own estimate: -0.673 pp of the net-of-interest cash-3m spread (% of 3m) per 1 log unit of visible stocks, full sample (Newey-West t -5.28), n 637, as of 2026-10-23 ([regression](knowledge/metals/copper/estimates/storage.json#fits.spread_pct))
- Size, own estimate: -0.699 same, latest block 2022-08 to 2026-07 (t -3.81; the last quarter held out), n 200, as of 2026-10-23 ([regression](knowledge/metals/copper/estimates/storage.json#fits.spread_pct.blocks))
- Notes: Spread net of interest (raw + 3-month T-bill x 91/360; review S3: the raw spread mixed in the rate level). Blocks agree in sign: True; full slope inside the block range: True; residual ADF t -6.03 (Engle-Granger 5% critical -3.34). Today's inventory-implied spread is fitted without the last quarter and suppressed when the fit is weak. The volatility predictions (realised vol, cash/3m vol ratio) are not supported on these data: block signs disagree. Contemporaneous, never a forecast.

## lme-stock-surprise

- **Claim:** A bigger-than-normal LME stock draw goes with a price rise on the report day.
- **Driver → target:** LME stock change vs its own norm, in sd → COMEX copper daily return
- **Sign / lag:** - / report day
- **Status:** untested
- **Source:** own estimate (pmstack metals); method as the EIA playbooks
- Size, own estimate: -0.1621 % per 1 sd stock surprise (report day, 90% CI), 90% CI -0.201 to -0.123, n 4589, as of 2026-10-23 ([regression](knowledge/metals/copper/estimates/stocks-lme_copper.json))
- Size, own estimate: -0.18 % per 1 sd stock surprise, since 2015 (90% CI), 90% CI -0.219 to -0.14, n 2917, as of 2026-10-23 ([regression](knowledge/metals/copper/estimates/stocks-lme_copper.json#eras.since_2015))
- Notes: Sign hit 0.574 of 886 reports with abs(z) >= 1; day before -0.046 (t -1.88), day after -0.083 (t -3.69). Contemporaneous association, predicts nothing.

## shfe-stock-surprise

- **Claim:** A bigger-than-normal SHFE stock draw goes with a price rise on the report day.
- **Driver → target:** SHFE stock change vs its own norm, in sd → COMEX copper daily return
- **Sign / lag:** - / report day
- **Status:** untested
- **Source:** own estimate (pmstack metals); method as the EIA playbooks
- Size, own estimate: 0.0003 % per 1 sd stock surprise (report day, 90% CI), 90% CI -0.131 to 0.131, n 340, as of 2026-10-23 ([regression](knowledge/metals/copper/estimates/stocks-shfe_copper.json))
- Size, own estimate: 0.0 % per 1 sd stock surprise, since 2015 (90% CI), 90% CI -0.131 to 0.131, n 340, as of 2026-10-23 ([regression](knowledge/metals/copper/estimates/stocks-shfe_copper.json#eras.since_2015))
- Notes: Sign hit 0.504 of 123 reports with abs(z) >= 1; day before -0.069 (t -0.97), day after 0.031 (t 0.48). Contemporaneous association, predicts nothing.

## china-pmi-day-volatility

- **Claim:** NBS PMI days are more volatile than other days.
- **Driver → target:** NBS manufacturing PMI release day → Daily return volatility
- **Sign / lag:** + / release day
- **Status:** untested
- **Source:** own estimate (pmstack metals); gold on the same days as the month-end control
- Size, own estimate: 0.97 sd of returns on NBS PMI days / other days, n 105, as of 2026-10-23 ([regression](knowledge/metals/copper/estimates/china-nbs_pmi.json))
- Notes: Ratio vs the gold control 0.99; placebo -5/+5 trading days {'-5d': 0.968, '+10d': 0.895}. Since 2018 (release rule documented by NBS calendars).
