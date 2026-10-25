# Primer: gold

This file holds method and sources only. Live levels come from the pack.

## Contracts and prices
- **COMEX gold (GC=F)**: USD per troy ounce, 100 oz. Yahoo continuous front month (personal use only).
  - The London OTC market (LBMA prices) is the physical reference. FRED stopped carrying LBMA prices in 2022, so none is stored.
- **Implied vol**: GVZ (CBOE, on GLD options; `fred_quant`). The quant tape compares it with realised vol.
- **Long run**: World Bank Pink Sheet monthly gold from 1960 (`wb:gold`), deflated by US CPI in `estimates/longrun.json`.

## What moves it (frames, all inference)
- **Real yields and the dollar.**
  - Higher US real yields have gone with weaker gold. The level relation broke from 2022, when emerging-market central banks bought about 1,000 t a year (2022–24) against about 500 t a year before. The figures are the World Gold Council's, as quoted by Janus Henderson.
  - Real yields (DFII10) and the broad dollar (DTWEXBGS) are context figures in the pack. There is no fair-value model here.
- **Valuation frame** (Erb & Harvey 2013):
  - gold hedges inflation only over centuries;
  - high real prices have been followed by below-average real returns;
  - official buying may make "this time different".

  The long-run block gives the real-price percentile; the card states both readings.
- **Safe haven.** Gold is a hedge against stocks on average and a short-lived safe haven in crashes (Baur & Lucey 2010). Cite it only for days with large equity falls.
- **No stocks-and-curve storage test.** Gold's above-ground stock is huge relative to annual mine supply, so the theory of storage does not price it the way it prices copper (general knowledge).
  - SHFE gold on warrant is stored (`shfe:au_warrants`), as a China-demand context figure only.
- **Not stored:** central bank purchases, ETF holdings and Chinese and Indian physical demand. The World Gold Council reports them quarterly, behind registration. GLD holdings were not reachable (25 Oct).

## Report calendar
| What | When | Notes |
|---|---|---|
| CFTC COT (gold 088691) | Friday 15:30 ET for Tuesday | Monday in holiday weeks. |
| FOMC, US CPI | Fed and BLS calendars | No playbook (Bernardo, 25 Oct); open question. |
| SHFE weekly gold on warrant | Friday | Context only. |

## Data in the repo
| What | Series id | Source | Since |
|---|---|---|---|
| COMEX gold front month | GC=F | Yahoo | 2000 |
| GVZ | GVZCLS | CBOE via FRED | 2008 |
| US 10y real yield, broad dollar | DFII10, DTWEXBGS | FRED | 2003, 2006 |
| Gold, monthly | wb:gold | World Bank Pink Sheet | 1960 |
| SHFE gold on warrant | shfe:au_warrants (kg) | SHFE | 2014 |
| Managed money (COT) | cftc 088691 | CFTC | 2010 |
