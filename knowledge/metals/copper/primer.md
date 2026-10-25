# Primer: copper

This file holds method and sources only. Live levels come from the pack (`python -m pmstack specialist pack metals`).

## Contracts and prices
- **COMEX copper (HG=F)**: USD per pound, 25,000 lb. Yahoo continuous front month (personal use only).
  - Since July 2025 the US tariff question has opened a COMEX-over-LME premium.
  - The relative trade lives in `config/spreads.yaml` (`cu_comex_lme_dec26`). Agent 8 replays the tariff days (`cu_tariff_2025`, `cu_exempt_2025`).
- **LME copper**: official cash settlement and 3-month price, USD per tonne. Set in the second ring session, about 12:30 London. Via Westmetall, personal use only (`lme:copper_cash`, `lme:copper_3m`). 1 t = 2,204.62 lb.
- **SHFE copper**: CNY per tonne, VAT included. The price is not stored; only SHFE stocks are.

## Spreads that matter
- **LME cash minus 3-month**, in % of the 3-month price here (positive = backwardation).
  - This is the storage state: visible stocks and the spread move together (Fama & French 1988; Geman & Smith 2013).
  - Since October 2021 the LME has capped the prompt backwardation in squeezes, so extreme spreads are truncated by rule.
- **COMEX minus LME** (the tariff premium since 2025), and the Shanghai premium (import arbitrage; not stored).

## Stocks and the storage test
- **Visible stocks** = LME warehouse stocks (daily, Westmetall) + SHFE weekly stocks (Friday, deliverable quality).
  - COMEX stocks are not reachable (the CME blocks scripts).
  - Bonded Shanghai stocks are only partly in the SHFE total.
  - Visible stocks are a small share of world stocks and move between venues on arbitrage, so a fall in one venue may be a transfer to another.
- `estimates/storage.json` (code) fits the spread **net of interest** (raw spread + 3-month T-bill × 91/360: a 3-month spread carries the interest cost, and US rates went from 0 to about 5% over the sample), realised vol and the cash/3-month vol ratio on log visible stocks.
  - Method: weekly since 2014, Newey-West errors over at least 26 weeks, three chronological blocks, and an ADF test on the residual against the Engle-Granger critical value.
  - Today's **inventory-implied spread** comes from a fit that leaves out the last 13 weeks, so today is scored out of sample. The fit is the full sample, or the latest block when the full slope lies outside the blocks' range.
  - The implied spread is suppressed unless that fit is significant, its residual stationary and the block signs agree. On the 23 Oct run the spread fit passes for copper and aluminium; the vol fits do not.
- **China financing.** Under capital controls metal can be held as collateral (Tang & Zhu 2016), so Chinese stock moves are not read as consumption by default.

## Demand and supply
- China is about half of world refined copper use. This is general knowledge, not page-checked. Reported consumption overstates use, because much is re-exported in goods (CME education report).
- Property and grid investment are the classic drivers. Bank of Canada (2016): Chinese housing explains about a quarter of the 2002–2010 base-metal rise.
- Copper is one of the metals where supply shocks matter more, because of its oligopolistic structure (Stuermer 2018), and mine disruptions are common.
  - No free mine-output series is wired. World Bureau of Metal Statistics and ICSG data are paid or delayed.

## Report calendar
| What | When | Notes |
|---|---|---|
| LME stocks | Daily, 09:00 London, for the previous day's moves | Dated here at the day Westmetall lists them. A one-day offset is possible; the playbook's day-after placebo checks it. |
| SHFE weekly stocks | Last trading day of the week, about 15:20 Beijing | Chinese holidays move or skip it. |
| NBS manufacturing PMI | Last calendar day of the month, 09:30 Beijing | Playbook: volatility only (`events.md`). |
| CFTC COT (copper 085692) | Friday 15:30 ET for Tuesday | Monday in holiday weeks. |

## Data in the repo
| What | Series id | Source | Since |
|---|---|---|---|
| COMEX copper front month | HG=F | Yahoo | 2000 |
| LME cash, 3-month, stocks | lme:copper_cash, lme:copper_3m, lme:copper_stock | Westmetall (`lme`, `lme_metals`) | 2008 |
| SHFE stocks, on warrant | shfe:cu_stock, shfe:cu_warrants | SHFE (`shfe`) | May 2014 |
| Copper, monthly | PCOPPUSDM; wb:copper | IMF via FRED; World Bank Pink Sheet | 1992; 1960 |
| COMEX Dec-26 contract | HGZ26.CMX | Yahoo (`prices_rv`) | 2023 |
| Managed money (COT) | cftc 085692 | CFTC | 2010 |
