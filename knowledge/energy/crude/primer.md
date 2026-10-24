# Primer: crude oil (WTI, Brent)

This file holds method and sources only. Live levels come from the pack (`pmstack specialist pack energy`), never from here.

## Contracts and delivery
- **ICE Brent futures:** 1,000 barrels. Delivered by exchange of futures for physical (EFP), with an option to cash settle against the ICE Brent Index. Trading stops on the last business day of the second month before the contract month (the March contract expires on the last business day of January). Source: https://www.ice.com/products/219/Brent-Crude-Futures (page-checked 24 Oct 2026).
- **NYMEX WTI (CL):** physically delivered at Cushing, Oklahoma. Spec page: https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.contractSpecs.html. The page timed out on 24 Oct 2026, so the contract terms here are general knowledge, not page-checked.
- **Dated Brent vs futures:** the repo's spot series is EIA's Brent spot via FRED (DCOILBRENTEU); the futures are Yahoo BZ=F. **Standing fact (notes/context.md):** dated Brent has traded far above futures all through 2026 (Iran war, Hormuz risk). Report the gap as the physical premium, and flag only a sharp change in it.

## Spreads that matter
- **Front timespreads (M1–M2, M1–M6):** the slope of the curve is the market's read of storage. Low stocks go with backwardation; high stocks go with contango, up to full carry (theory of storage; GHR 2013). Part of the basis is a risk premium whose sign changed after 2005 (Hamilton & Wu 2014). Code: `pmstack/quant/curve.py` (contracts collected from 24 Oct 2026; Yahoo, personal use).
- **Brent–WTI:** follows Cushing capacity use, the business cycle and the WTI prompt slope. The Cushing stock level alone is not significant (Büyükşahin et al. 2013). Driver `brent-wti-cushing`.
- **Cracks** (products minus crude): see `knowledge/energy/products/primer.md`.

## Seasonality
US crude stocks build in Q1, draw through the summer driving season and rebuild in autumn. The balance keeper measures this per series (`balance.seasonality`: the share of weekly-change variance explained by month, and how stable it is). Crude passes the check. Cushing and total stocks ex SPR are flagged weak (agent 9, 20 Oct 2026), so they are also shown against their trailing 52-week mean.

## Report calendar
| Report | Publisher | When | What moves | Playbook |
|---|---|---|---|---|
| Weekly Petroleum Status Report | EIA | Wed 10:30 ET (holiday weeks usually Thu 12:00 ET; schedule https://www.eia.gov/petroleum/supply/weekly/schedule.php) | US crude, gasoline, distillate and Cushing stocks; production, exports | `events.md` |
| API weekly statistics | API (paid) | Tue 16:30 ET, after the NYMEX settle | Lands in Wednesday's close-to-close return | not stored |
| Short-Term Energy Outlook | EIA | monthly, around noon ET (https://www.eia.gov/outlooks/steo/release_schedule.php) | EIA's world balance and price path (EIA's view, never a consensus) | source `steo` |
| OPEC Monthly Oil Market Report | OPEC | mid-month | secondary-source production | not stored (opec.org blocks scripts) |
| JODI oil database | JODI | monthly (calendar on jodidata.org) | country production, refinery runs, trade, stocks | source `jodi` |
| CFTC Commitments of Traders | CFTC | Fri 15:30 ET for Tuesday | managed money positioning | facts.md, source `cftc` |

## Data in the repo
| What | Series id | Source | Since |
|---|---|---|---|
| US crude stocks ex SPR | PET.WCESTUS1.W | EIA (`eia`) | 1982 |
| Cushing stocks | PET.W_EPC0_SAX_YCUOK_MBBL.W | EIA (`eia`) | 2004 |
| US crude production, exports | PET.WCRFPUS2.W, PET.WCREXUS2.W | EIA (`eia`) | 2018 backfill |
| US crude imports, refinery inputs | PET.WCRIMUS2.W, PET.WCRRIUS2.W | EIA (`eia_bal`) | 2015 backfill |
| WTI, Brent front month | CL=F, BZ=F | Yahoo (personal use) | 2000 / 2007 |
| Brent spot | DCOILBRENTEU | FRED (EIA) | 1987 |
| Curve contracts (12 months) | CLZ26.NYM, BZF27.NYM, ... | Yahoo (`prices_curve`) | 24 Oct 2026 |
| STEO issues | steo:SERIES@issue | EIA archive (`steo`) | 2014 issues |
| JODI country balances | jodi:CC:CRUDEOIL:FLOW | JODI (`jodi`) | 2015 |
| Brazil crude production | anp:crude_production_kbd | ANP (`anp`) | 1997 |
| US oil rigs (monthly) | PET.E_ERTRRO_XR0_NUS_C.M | EIA (`eia_rigs`) | 1990 |
| WTI managed money | CFTC 067651 | CFTC (`cftc`) | 2006 |
