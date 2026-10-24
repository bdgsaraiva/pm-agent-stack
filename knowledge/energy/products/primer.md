# Primer: refined products (RBOB gasoline, ULSD / heating oil, jet)

This file holds method and sources only. Live levels come from the pack.

## Contracts
- NYMEX RBOB gasoline (RB=F) and NY Harbor ULSD (HO=F): quoted in USD per gallon and delivered in New York Harbor. General knowledge, not page-checked (CME pages timed out on 24 Oct 2026).

## Spreads that matter
- **Cracks:** product price minus crude price in the same unit (USD/gal × 42 = USD/bbl). The 3-2-1 crack approximates a refinery margin. Not computed yet; it arrives with the S2 carry-and-curve module.
- **RBOB grade switch:** summer-grade contracts (April–September) price above winter grade, which shows up as a jump in the continuous series at the switch. Agent 8's roll screen catches it. Read RBOB moves around March and September with care (general knowledge, not page-checked).

## Seasonality
Gasoline stocks draw into the summer driving season. Distillate stocks draw with winter heating and harvest demand. Jet stocks are flagged weakly seasonal (agent 9 check, 20 Oct 2026).

## Report calendar
WPSR, Wednesday 10:30 ET: gasoline and distillate stocks, and products supplied (implied demand). Use the 4-week average for products supplied: the weekly figure is noisy, and EIA says it is usually within about ±2% of the monthly PSM (https://www.eia.gov/tools/faqs/faq.php?id=1398&t=6). Playbook: `events.md`.

## Data in the repo
| What | Series id | Source | Since |
|---|---|---|---|
| US gasoline stocks | PET.WGTSTUS1.W | EIA | 1990 |
| US distillate stocks | PET.WDISTUS1.W | EIA | 1982 |
| US jet stocks | PET.WKJSTUS1.W | EIA (`eia_bal`) | 2015 backfill |
| Products supplied (gasoline, distillate, jet, total) | PET.WGFUPUS2.W, PET.WDIUPUS2.W, PET.WKJUPUS2.W, PET.WRPUPUS2.W | EIA (`eia_bal`) | 2015 backfill |
| RBOB, ULSD front month | RB=F, HO=F | Yahoo | 2000 |
| NY Harbor spot gasoline, heating oil | DGASNYH, DHOILNYH | FRED | 1986 |
| Brazil fuel sales (diesel, gasoline C, ethanol, jet, LPG, fuel oil) | anp:sales_m3:* | ANP | 1990 |
| Curve contracts (6 months) | RBZ26.NYM, HOZ26.NYM, ... | Yahoo (`prices_curve`) | 24 Oct 2026 |
