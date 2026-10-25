# Balance template: copper

Each line is tied to a public series. Values come from code (the pack, `pmstack metals`), never typed here.

| Line | Series | Source | Frequency | Release lag | In repo? |
|---|---|---|---|---|---|
| LME warehouse stocks (level, daily change vs trailing norm) | lme:copper_stock | LME via Westmetall (personal use) | daily | 09:00 London next day | yes |
| SHFE stocks, deliverable and on warrant (level vs 5-year same week) | shfe:cu_stock, shfe:cu_warrants | SHFE (personal use) | weekly | same day, ~15:20 Beijing | yes (from May 2014) |
| Visible stocks (LME + SHFE) and the inventory-implied cash-3m spread | estimates/storage.json | code | weekly | - | yes |
| LME cash-3-month spread | lme:copper_cash, lme:copper_3m | LME via Westmetall | daily | same day | yes |
| COMEX stocks | - | CME (blocks scripts) | daily | - | no |
| LME on-warrant and cancelled warrants | - | LME (licensed) | daily | - | no |
| Chinese imports of refined copper and concentrate | - | China customs (no machine-readable tables) | monthly | ~7-14 days | no |
| World refined balance (production, use) | - | ICSG (members/paid), WBMS (paid) | monthly | ~3 months | no |
| US copper mine production | - | USGS Mineral Industry Surveys (public domain) | monthly | ~3 months | no (candidate) |
| Long-run real price | wb:copper / CPIAUCSL | World Bank, FRED | monthly | ~1 week | yes |
