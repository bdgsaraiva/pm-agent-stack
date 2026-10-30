# Event playbooks: wheat

Same reports and method as corn. Wheat's WASDE-day effect is the smallest of the three grains (a world market where US numbers carry less), and winter and spring wheat condition are measured separately against SRW futures (no HRW or spring wheat contract is stored).

<!-- code: reaction base rates (pmstack ags --write) -->
## Reaction base rates (code, as of 2026-10-29)

### Report days (volatility)
Daily closes (Yahoo continuous front month, personal use only) on report days vs other days; exact dates from USDA ESMIS. Local ratio = the report day against the 10 trading days either side (a seasonal control: June-July days are volatile anyway). Placebo = the same days shifted 5 trading days back or 10 forward, other report days left out. Contemporaneous: predicts nothing. Full numbers: `estimates/*-days.json`.

| Report day | Market | Events | Vol ratio (report / other) | Local ratio vs +-10 days (paired t) | Big-move rate report vs other (lift) | Levene p | Halves | Placebo -5d / +10d: vol ratio, local | Eras: ratio |
|---|---|---|---|---|---|---|---|---|---|
| WASDE (months without Grain Stocks) | CBOT wheat (SRW) | 297 (2000-2026) | 1.10 | 1.09 (1.8) | 13% vs 13% (1.04) | 0.035 | 1.08 / 1.13 | 1.01, 1.00 / 0.83, 0.83 | 2000_to_2012 1.09 (146); since_2013-01-11 1.12 (151) |
| January WASDE + annual Crop Production + Grain Stocks | CBOT wheat (SRW) | 27 (2000-2026) | 1.67 | 1.85 (3.1) | 30% vs 13% (2.35) | 0.001 | 2.03 / 1.14 | 0.84, 1.33 / 0.71, 1.05 | - |
| March and June Grain Stocks + Prospective Plantings / Acreage | CBOT wheat (SRW) | 53 (2000-2026) | 1.79 | 1.79 (4.1) | 43% vs 12% (3.49) | 0.000 | 1.94 / 1.56 | 0.81, 0.78 / 1.40, 1.29 | - |
| September Grain Stocks (alone) | CBOT wheat (SRW) | 30 (2000-2026) | 1.45 | 1.56 (2.5) | 27% vs 13% (2.12) | 0.004 | 1.48 / 1.45 | 0.82, 0.75 / -, - | - |

WASDE revision proxy (2021 on, WASDE as first published): same-day return per 1 sd of the US ending-stocks revision vs the previous report -0.219% (t -0.6, 54 reports); only 7 revisions of at least 1 sd, too few for a sign-agreement rate. No consensus is stored, so this is a weak, attenuated proxy.

### Crop Progress (condition)
Next-day return (the report comes out at 16:00 ET, after the close) vs the week's good + excellent change against its seasonal norm (same and adjacent ISO weeks of the prior 5 seasons), in sd. Sign hit = a bigger-than-normal improvement with a price fall. Release dates from ESMIS.

| Crop vs market | Events | Sign hit at abs(z) >= 1 (95% CI) | Slope per 1 sd (t) | Slope per 1 pp (t) | July-August: slope per sd (n) | Halves | Placebo day before / after (t) |
|---|---|---|---|---|---|---|---|
| winter wheat condition (good + excellent) vs CBOT wheat (SRW) | 119 (2019-2026) | 51% of 45 (37%-65%) | -0.22% (-1.5) | -0.136% (-1.5) | - (8) | -0.13 / -0.39 | -0.39 (-2.5) / 0.22 (1.7) |
| spring wheat condition (good + excellent) vs CBOT wheat (SRW) | 76 (2020-2026) | 61% of 28 (42%-76%) | -0.24% (-1.4) | -0.069% (-1.0) | -0.32 (52) | -0.47 / 0.26 | -0.35 (-1.5) / 0.10 (0.4) |

Condition data from 2015 (NASS Quick Stats): the norm needs five prior seasons, so events start in 2019, 2020. Report-day categories are disjoint: WASDE excludes January (its day is shared with Grain Stocks and the annual Crop Production), and Grain Stocks alone is September only (March and June share the day with Prospective Plantings and Acreage). Sugar (#11) is a world market: US crop reports are shown for context only.
<!-- /code -->
