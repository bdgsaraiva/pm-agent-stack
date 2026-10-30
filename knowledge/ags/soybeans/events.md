# Event playbooks: soybeans

Same reports and method as corn (`knowledge/ags/corn/events.md`). Soybeans react to WASDE less than corn. On the March/June days the +10-day placebo is high but rests on few days (see the JSON: days and t); quote the local ratio with its paired t. The key US weather window is August, when condition matters most.

<!-- code: reaction base rates (pmstack ags --write) -->
## Reaction base rates (code, as of 2026-10-29)

### Report days (volatility)
Daily closes (Yahoo continuous front month, personal use only) on report days vs other days; exact dates from USDA ESMIS. Local ratio = the report day against the 10 trading days either side (a seasonal control: June-July days are volatile anyway). Placebo = the same days shifted 5 trading days back or 10 forward, other report days left out. Contemporaneous: predicts nothing. Full numbers: `estimates/*-days.json`.

| Report day | Market | Events | Vol ratio (report / other) | Local ratio vs +-10 days (paired t) | Big-move rate report vs other (lift) | Levene p | Halves | Placebo -5d / +10d: vol ratio, local | Eras: ratio |
|---|---|---|---|---|---|---|---|---|---|
| WASDE (months without Grain Stocks) | CBOT soybeans | 295 (2000-2026) | 1.24 | 1.19 (3.1) | 17% vs 13% (1.30) | 0.000 | 1.24 / 1.23 | 0.90, 0.98 / 0.83, 0.82 | 2000_to_2012 1.24 (144); since_2013-01-11 1.23 (151) |
| January WASDE + annual Crop Production + Grain Stocks | CBOT soybeans | 27 (2000-2026) | 2.02 | 2.31 (4.2) | 59% vs 13% (4.66) | 0.000 | 2.30 / 1.45 | 0.91, 1.18 / 0.82, 0.93 | - |
| March and June Grain Stocks + Prospective Plantings / Acreage | CBOT soybeans | 53 (2000-2026) | 1.75 | 1.91 (4.5) | 55% vs 13% (4.35) | 0.000 | 1.64 / 1.79 | 0.83, 0.86 / 2.61, 1.62 | - |
| September Grain Stocks (alone) | CBOT soybeans | 30 (2000-2026) | 1.26 | 1.63 (2.7) | 20% vs 13% (1.55) | 0.052 | 1.20 / 1.36 | 0.77, 1.06 / -, - | - |

WASDE revision proxy (2021 on, WASDE as first published): same-day return per 1 sd of the US ending-stocks revision vs the previous report -0.467% (t -1.2, 54 reports); only 4 revisions of at least 1 sd, too few for a sign-agreement rate. No consensus is stored, so this is a weak, attenuated proxy.

### Crop Progress (condition)
Next-day return (the report comes out at 16:00 ET, after the close) vs the week's good + excellent change against its seasonal norm (same and adjacent ISO weeks of the prior 5 seasons), in sd. Sign hit = a bigger-than-normal improvement with a price fall. Release dates from ESMIS.

| Crop vs market | Events | Sign hit at abs(z) >= 1 (95% CI) | Slope per 1 sd (t) | Slope per 1 pp (t) | July-August: slope per sd (n) | Halves | Placebo day before / after (t) |
|---|---|---|---|---|---|---|---|
| soybeans condition (good + excellent) vs CBOT soybeans | 118 (2020-2026) | 51% of 39 (36%-66%) | -0.20% (-1.6) | -0.169% (-1.7) | -0.38 (62) | -0.27 / -0.05 | -0.05 (-0.6) / 0.09 (1.1) |

Condition data from 2015 (NASS Quick Stats): the norm needs five prior seasons, so events start in 2020. Report-day categories are disjoint: WASDE excludes January (its day is shared with Grain Stocks and the annual Crop Production), and Grain Stocks alone is September only (March and June share the day with Prospective Plantings and Acreage). Sugar (#11) is a world market: US crop reports are shown for context only.
<!-- /code -->
