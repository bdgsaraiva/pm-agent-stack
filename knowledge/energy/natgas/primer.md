# Primer: US natural gas (Henry Hub)

This file holds method and sources only. Live levels come from the pack.

## Contracts
NYMEX Henry Hub natural gas (NG=F), quoted in USD per MMBtu and delivered at Henry Hub, Louisiana. General knowledge, not page-checked.

## Storage and seasons
- The **injection season** runs from about April to October and the **withdrawal season** from November to March. Prices react more to storage surprises in the injection season and when inventories are high (Farhangdoost & Etienne 2020). The playbook splits by season once enough gas history is stored.
- Weather (heating and cooling degree days against normal) moves both price and volatility (Mu 2007). Weather data are not in the repo yet.
- Gas volatility is higher on Mondays and on storage-report days (Mu 2007). Mondays are kept out of the control days in the gas playbook.

## Report calendar
| Report | When | Notes |
|---|---|---|
| EIA Weekly Natural Gas Storage Report | Thursday 10:30 ET; holidays move it | Stocks are as of Friday 9:00 CST. Revisions above 500 MMcf are published. Reclassifications of 4 Bcf or more are excluded from implied flow. EIA's 5-year average uses daily interpolation, so it will not match a recomputation from weekly levels. Sampling error is about 2 Bcf on a typical change (https://ir.eia.gov/ngs/methodology.html). |

## Data in the repo
| What | Series id | Source | Since |
|---|---|---|---|
| Lower 48 working gas | NG.NW2_EPG0_SWO_R48_BCF.W | EIA (`eia_ng`, from 24 Oct 2026) | 2010 |
| Henry Hub front month | NG=F | Yahoo | 2000 |
| Henry Hub spot | DHHNGSP | FRED | 1997 |
| US gas rigs (monthly) | PET.E_ERTRRG_XR0_NUS_C.M | EIA (`eia_rigs`) | 1990 |
| Curve contracts (12 months) | NGZ26.NYM, ... | Yahoo (`prices_curve`) | 24 Oct 2026 |
