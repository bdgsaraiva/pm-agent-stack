# Balance template: gold

Gold has no flow balance that prices it month to month: the above-ground stock dwarfs mine supply. The lines below are context, each tied to a public series.

| Line | Series | Source | Frequency | Release lag | In repo? |
|---|---|---|---|---|---|
| US 10-year real yield | DFII10 | FRED | daily | 1 day | yes |
| Broad trade-weighted dollar | DTWEXBGS | FRED | daily | ~1 week | yes |
| Gold implied vol | GVZCLS | CBOE via FRED | daily | 1 day | yes |
| Managed money net | cftc 088691 | CFTC | weekly | Friday for Tuesday | yes |
| SHFE gold on warrant | shfe:au_warrants | SHFE (personal use) | weekly | same day | yes |
| Central bank purchases, ETF holdings, jewellery and bar demand | - | World Gold Council (registration) | quarterly | ~1 month | no |
| Long-run real price | wb:gold / CPIAUCSL | World Bank, FRED | monthly | ~1 week | yes |
