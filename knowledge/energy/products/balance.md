# Balance template: products

| Line | Series | Source | Frequency | Release lag | In repo? |
|---|---|---|---|---|---|
| US gasoline stocks, days of supply | PET.WGTSTUS1.W, PET.W_EPM0_VSD_NUS_DAYS.W | EIA WPSR | weekly | Wed | yes |
| US distillate stocks, days of supply | PET.WDISTUS1.W, PET.W_EPD0_VSD_NUS_DAYS.W | EIA WPSR | weekly | Wed | yes |
| US jet stocks (weak seasonality) | PET.WKJSTUS1.W | EIA WPSR | weekly | Wed | yes |
| Products supplied: gasoline, distillate, jet (4-week) | PET.WGFUPUS2.W, PET.WDIUPUS2.W, PET.WKJUPUS2.W | EIA WPSR | weekly | Wed | yes |
| Refinery utilisation | PET.WPULEUS3.W | EIA WPSR | weekly | Wed | yes |
| Brazil fuel sales: diesel, gasoline C, hydrated ethanol, jet, LPG, fuel oil | anp:sales_m3:* | ANP | monthly | ~2 months | yes |
| Cracks (product minus crude) | from RB=F, HO=F, CL=F, BZ=F | code (S2 curve module) | daily | - | not yet |
