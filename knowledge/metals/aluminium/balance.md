# Balance template: aluminium

Each line is tied to a public series. Values come from code (the pack, `pmstack metals`), never typed here.

| Line | Series | Source | Frequency | Release lag | In repo? |
|---|---|---|---|---|---|
| LME warehouse stocks | lme:aluminium_stock | LME via Westmetall (personal use) | daily | 09:00 London next day | yes |
| SHFE stocks, deliverable and on warrant | shfe:al_stock, shfe:al_warrants | SHFE (personal use) | weekly | same day | yes (from May 2014) |
| Visible stocks (LME + SHFE) and the inventory-implied spread | estimates/storage.json | code | weekly | - | yes |
| LME cash-3-month spread | lme:aluminium_cash, lme:aluminium_3m | LME via Westmetall | daily | same day | yes |
| China primary output vs the ~45 Mt cap | - | NBS (monthly, Chinese site) | monthly | ~15 days | no (candidate) |
| World primary production | - | International Aluminium Institute (public monthly table) | monthly | ~20 days | no (candidate) |
| Long-run real price | wb:aluminium / CPIAUCSL | World Bank, FRED | monthly | ~1 week | yes |
