# Event playbooks: sugar

No US report playbook: raw sugar No. 11 is a world market, and WASDE days show no extra volatility (table below). The Brazilian biweekly crush (UNICA) is the report that matters, and it is not available as data (latest PDF only).

<!-- code: reaction base rates (pmstack ags --write) -->
## Reaction base rates (code, as of 2026-10-29)

### Report days (volatility)
Daily closes (Yahoo continuous front month, personal use only) on report days vs other days; exact dates from USDA ESMIS. Local ratio = the report day against the 10 trading days either side (a seasonal control: June-July days are volatile anyway). Placebo = the same days shifted 5 trading days back or 10 forward, other report days left out. Contemporaneous: predicts nothing. Full numbers: `estimates/*-days.json`.

| Report day | Market | Events | Vol ratio (report / other) | Local ratio vs +-10 days (paired t) | Big-move rate report vs other (lift) | Levene p | Halves | Placebo -5d / +10d: vol ratio, local | Eras: ratio |
|---|---|---|---|---|---|---|---|---|---|
| WASDE (months without Grain Stocks) | ICE raw sugar No. 11 | 301 (2000-2026) | 0.94 | 0.95 (-1.1) | 11% vs 12% (0.88) | 0.931 | 0.97 / 0.88 | 1.03, 1.06 / 1.01, 0.93 | 2000_to_2012 0.97 (150); since_2013-01-11 0.88 (151) |

Condition data from 2015 (NASS Quick Stats): the norm needs five prior seasons, so events start in -. Report-day categories are disjoint: WASDE excludes January (its day is shared with Grain Stocks and the annual Crop Production), and Grain Stocks alone is September only (March and June share the day with Prospective Plantings and Acreage). Sugar (#11) is a world market: US crop reports are shown for context only.
<!-- /code -->
