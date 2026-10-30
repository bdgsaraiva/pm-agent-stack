# Event playbooks: corn

## WASDE
- **What and when.** USDA's monthly supply and demand estimates, about the 9th-12th at 12:00 ET (08:30 before May 2013). Exact dates from USDA ESMIS.
- **Base rate (code, below).** Corn's WASDE-day volatility is above the 10 days either side; placebo days are not. The table's WASDE row leaves out January (shared with Grain Stocks: its own row). The literature finds larger effects at low carryover (Adjemian 2012): read agent 9's stocks-to-use percentile beside it.
- **Revision proxy (2021 on).** Same-day return vs the revision of US ending stocks against the previous report, in sd. There is no consensus, so part of the revision was expected: a weak proxy.

## Crop Progress
- **What and when.** Monday 16:00 ET, after the close (Tuesday or later in holiday weeks), April-November. Priced the next day.
- **Base rate (code, below).** Better-than-seasonal condition goes with a lower next-day price in every crop; corn's slope is significant, the others are not on their own (see the t-stats). The literature finds reactions strongest in July-August and growing (Lehecka 2014).

## January, March/June and September report days
- **What.** Grain Stocks shares its day with the January WASDE and annual Crop Production, and with Prospective Plantings (March) and Acreage (June); only September stands alone. The table keeps these as separate rows so no day counts twice.
- **Base rate (code, below).** The year's largest report days are January and the end of June/March: corn's volatility is several times the days around them. September Grain Stocks alone moves less.

## Pitfalls
- Never write "vs consensus": no survey is stored; every surprise is against a seasonal norm or the previous report.
- The front-month roll gaps sit in the closes; the outlier screen drops the worst.
- Nothing here may alert until the testing gate (`/research`) passes it.

<!-- code: reaction base rates (pmstack ags --write) -->
## Reaction base rates (code, as of 2026-10-29)

### Report days (volatility)
Daily closes (Yahoo continuous front month, personal use only) on report days vs other days; exact dates from USDA ESMIS. Local ratio = the report day against the 10 trading days either side (a seasonal control: June-July days are volatile anyway). Placebo = the same days shifted 5 trading days back or 10 forward, other report days left out. Contemporaneous: predicts nothing. Full numbers: `estimates/*-days.json`.

| Report day | Market | Events | Vol ratio (report / other) | Local ratio vs +-10 days (paired t) | Big-move rate report vs other (lift) | Levene p | Halves | Placebo -5d / +10d: vol ratio, local | Eras: ratio |
|---|---|---|---|---|---|---|---|---|---|
| WASDE (months without Grain Stocks) | CBOT corn | 297 (2000-2026) | 1.27 | 1.31 (5.2) | 23% vs 12% (1.90) | 0.000 | 1.21 / 1.33 | 0.89, 0.94 / 0.81, 0.80 | 2000_to_2012 1.22 (146); since_2013-01-11 1.32 (151) |
| January WASDE + annual Crop Production + Grain Stocks | CBOT corn | 27 (2000-2026) | 2.25 | 3.25 (5.0) | 63% vs 12% (5.10) | 0.000 | 2.47 / 1.84 | 0.70, 1.07 / 0.68, 0.94 | - |
| March and June Grain Stocks + Prospective Plantings / Acreage | CBOT corn | 53 (2000-2026) | 2.39 | 2.69 (6.4) | 66% vs 12% (5.45) | 0.000 | 2.38 / 2.45 | 0.93, 0.82 / 1.21, 0.98 | - |
| September Grain Stocks (alone) | CBOT corn | 30 (2000-2026) | 1.58 | 1.92 (3.4) | 30% vs 12% (2.41) | 0.000 | 1.50 / 1.60 | 0.67, 0.84 / -, - | - |

WASDE revision proxy (2021 on, WASDE as first published): same-day return per 1 sd of the US ending-stocks revision vs the previous report -1.119% (t -3.9, 54 reports); only 8 revisions of at least 1 sd, too few for a sign-agreement rate. No consensus is stored, so this is a weak, attenuated proxy.

### Crop Progress (condition)
Next-day return (the report comes out at 16:00 ET, after the close) vs the week's good + excellent change against its seasonal norm (same and adjacent ISO weeks of the prior 5 seasons), in sd. Sign hit = a bigger-than-normal improvement with a price fall. Release dates from ESMIS.

| Crop vs market | Events | Sign hit at abs(z) >= 1 (95% CI) | Slope per 1 sd (t) | Slope per 1 pp (t) | July-August: slope per sd (n) | Halves | Placebo day before / after (t) |
|---|---|---|---|---|---|---|---|
| corn condition (good + excellent) vs CBOT corn | 132 (2020-2026) | 61% of 46 (46%-74%) | -0.26% (-2.2) | -0.177% (-1.8) | -0.30 (62) | -0.27 / -0.24 | -0.03 (-0.3) / 0.09 (0.8) |

Condition data from 2015 (NASS Quick Stats): the norm needs five prior seasons, so events start in 2020. Report-day categories are disjoint: WASDE excludes January (its day is shared with Grain Stocks and the annual Crop Production), and Grain Stocks alone is September only (March and June share the day with Prospective Plantings and Acreage). Sugar (#11) is a world market: US crop reports are shown for context only.
<!-- /code -->
