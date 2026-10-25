# Primer: aluminium

This file holds method and sources only. Live levels come from the pack.

## Contracts and prices
- **LME aluminium** (primary, high grade): official cash and 3-month prices, USD per tonne. Via Westmetall, personal use only (`lme:aluminium_cash`, `lme:aluminium_3m`).
  - This is the reference price here. COMEX aluminium (ALI=F) barely trades on Yahoo (zero volume most days, checked 25 Oct), so it is not used.
- Regional premiums (US Midwest, Rotterdam, the Japan quarterly) carry tariffs and freight. None is stored.

## Spreads and stocks
- **LME cash minus 3-month** (net of interest) and **visible stocks** (LME daily + SHFE weekly) feed the same storage test as copper (`estimates/storage.json`).
- Warehouse queues and financing deals distorted LME aluminium stocks until the LME's queue rules took effect from 2015. The stock playbook therefore splits at 2015.
- Much of the world's aluminium sits off-exchange (financing deals, producer stocks), so visible stocks understate the total more than for copper.

## Cost and supply
- **Power** is usually over a third of primary smelting cost (S&P Global news; general for the industry).
  - Most Chinese smelters run on coal-fired power, and the hydro provinces (Yunnan, Sichuan) curtail in droughts.
  - Europe's 2021–22 power shock shut smelters (general knowledge, not page-checked).
- **China's capacity cap**: about 45 Mt a year since 2017 (some sources say 45.5), with one-for-one replacement.
  - National output ran above the cap in 2026 through debottlenecking (Reuters via Engineering News, Sep 2026; SMM).
  - Chinese supply growth is therefore a policy variable, not a price response.
- Alumina and bauxite (Guinea, Australia) are upstream bottlenecks. No series is stored.

## Report calendar
| What | When | Notes |
|---|---|---|
| LME stocks | Daily, 09:00 London | As for copper. |
| SHFE weekly stocks | Last trading day of the week, about 15:20 Beijing | |
| NBS manufacturing PMI | Last calendar day of the month, 09:30 Beijing | Volatility only. |

## Data in the repo
| What | Series id | Source | Since |
|---|---|---|---|
| LME cash, 3-month, stocks | lme:aluminium_cash, lme:aluminium_3m, lme:aluminium_stock | Westmetall (`lme_metals`) | 2008 |
| SHFE stocks, on warrant | shfe:al_stock, shfe:al_warrants | SHFE | May 2014 |
| Aluminium, monthly | PALUMUSDM; wb:aluminium | IMF via FRED; World Bank Pink Sheet | 1992; 1960 |
| Positioning | none | (no CFTC series) | |
