# Balance template: soybeans

Each line is tied to a public series. Values come from code (the pack), never typed here.

| Line | Series | Source | Frequency | Release lag | In repo? |
|---|---|---|---|---|---|
| US ending stocks, use, stocks-to-use (first published) and revision | wasde:soybeans:united-states:* | USDA WASDE (agent 9) | monthly | report day 12:00 ET | yes (2021 on) |
| World and world ex China stocks-to-use | wasde:soybeans:world:*, PSD | USDA WASDE / FAS PSD | monthly | report day | yes |
| Stocks-to-use percentile since 2007/08 | psd:soybeans:* | FAS PSD (agent 9) | monthly | - | yes |
| Quarterly stocks | nass:soybeans-grain-stocks-measured-in-bu | NASS Grain Stocks | quarterly | report day | yes |
| Crop condition (good + excellent) | nass:soybeans-condition-* | NASS Crop Progress | weekly in season | Monday 16:00 ET | yes (2015 on) |
| Export commitments, weekly net sales | fas_esr:soybeans:* | USDA FAS Export Sales | weekly | Thursday 08:30 ET (+8 days used) | yes |
| Brazil production (survey, first published) | conab:soja | Conab | monthly | publication day | yes (about 2021/22 on) |
| US drought (% area D1-D4) | usdm:conus:d1 | US Drought Monitor | weekly | Thursday | yes (CONUS only) |
| ENSO (ONI) | noaa:oni | NOAA CPC | monthly | ~10 days | yes |
| Crush | WASDE lines | WASDE | monthly | - | yes (in WASDE rows) |
| Daily weather (heat in August) | - | NOAA/ECMWF (not wired) | daily | - | no |
