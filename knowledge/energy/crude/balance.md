# Balance template: crude

Each line is tied to a public series. Values come from code (the pack, `pmstack balance`), never typed here.

| Line | Series | Source | Frequency | Release lag | In repo? |
|---|---|---|---|---|---|
| US commercial crude stocks ex SPR (level vs 5-year same week, z, days of supply) | PET.WCESTUS1.W, PET.W_EPC0_VSD_NUS_DAYS.W | EIA WPSR | weekly | Wed after the week | yes |
| Cushing stocks (with trailing 52-week mean: weak seasonality) | PET.W_EPC0_SAX_YCUOK_MBBL.W | EIA WPSR | weekly | Wed | yes |
| US crude production | PET.WCRFPUS2.W | EIA WPSR (model-based weekly estimate) | weekly | Wed | yes |
| US crude exports, imports, net imports | PET.WCREXUS2.W, PET.WCRIMUS2.W, PET.WCRNTUS2.W | EIA WPSR | weekly | Wed | yes |
| US refinery crude inputs (4-week vs 5-year) | PET.WCRRIUS2.W | EIA WPSR | weekly | Wed | yes |
| US total products supplied (implied demand, 4-week) | PET.WRPUPUS2.W | EIA WPSR | weekly | Wed | yes |
| SPR stocks | PET.WCSSTUS1.W | EIA WPSR | weekly | Wed | yes |
| US oil rigs | PET.E_ERTRRO_XR0_NUS_C.M | Baker Hughes via EIA | monthly | ~1 month | yes (from 24 Oct 2026) |
| World liquids production and consumption, inventory net withdrawals (EIA's view) | steo:PAPR_WORLD, PATC_WORLD, T3_STCHANGE_WORLD @issue | EIA STEO | monthly issues | issue date | yes |
| OPEC production (EIA estimate) | steo:PAPR_OPEC@issue | EIA STEO | monthly | issue date | yes |
| OECD commercial stocks (EIA estimate) | steo:PASC_OECD_T3@issue | EIA STEO | monthly | issue date | yes |
| Country production, refinery runs, trade, stocks | jodi:CC:CRUDEOIL:INDPROD/REFINOBS/TOTEXPSB/TOTIMPSB/CLOSTLV | JODI | monthly | ~1-2 months; vintages from 24 Oct 2026 | yes |
| Brazil crude production | anp:crude_production_kbd | ANP | monthly | ~2 months | yes |
| OPEC secondary-source production | MOMR table | OPEC | monthly | mid-month | no (opec.org blocks scripts) |
| Floating storage, tanker tracking | - | paid (Kpler, Vortexa) | daily | - | no (paid; corporate lane) |
