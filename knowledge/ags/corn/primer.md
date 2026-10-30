# Primer: corn

This file holds method and sources only. Live levels come from the pack (`python -m pmstack specialist pack ags`).

## Contracts and calendar
- **CBOT corn (ZC=F)**: US cents per bushel, 5,000 bu. Yahoo continuous front month (personal use only); the roll from the expiring month leaves gaps in the series (see the quant tape caveat).
- US marketing year September-August. Planting April-May, pollination July (the key weather window: Schlenker & Roberts 2009, heat above about 29 °C cuts yield steeply), harvest September-November.
- Brazil's second crop (safrinha, planted after soybeans in January-March, harvested June-August) is now the larger Brazilian crop and competes with US exports in the northern autumn.

## Balance (agent 9, in the fact pack)
- US and world stocks-to-use from WASDE as first published, the revision vs the previous report beside USDA's own average miss, and the stocks-to-use percentile since 2007/08. Low stocks-to-use means small shocks move price more (Wright 2011), not a direction.
- Quarterly NASS Grain Stocks (1 March, 1 June, 1 September, 1 December) and weekly crop condition (good + excellent).
- Weekly export sales (USDA ESR): commitments (shipped + outstanding) for the marketing year, vs the same week of earlier years.
- Brazil: Conab's monthly survey as first published (`conab:milho_total`, `conab:milho_2a`), and its revision vs the previous survey. USDA's Brazil numbers differ from Conab's (farmdoc daily 2024): show both, neither is "right".

## Report calendar
| Report | When | Notes |
|---|---|---|
| WASDE | about the 9th-12th, 12:00 ET (08:30 before May 2013) | Playbook: `events.md` |
| Crop Progress | Monday 16:00 ET, April-November (Tuesday or later in holiday weeks) | After the close: priced the next day |
| Grain Stocks | end of March, June, September; mid-January (with the Annual Crop Production) | The year's largest report-day moves |
| Prospective Plantings / Acreage | end of March / end of June, 12:00 ET | Same day as Grain Stocks in March and June |
| Export Sales | Thursday 08:30 ET | Context, no playbook |
| Conab survey | monthly, about the 10th-15th | Brazil; context |
| CFTC COT (corn 002602) | Friday 15:30 ET for Tuesday | |
