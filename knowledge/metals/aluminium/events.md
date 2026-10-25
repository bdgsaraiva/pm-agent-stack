# Event playbooks: aluminium

## LME daily stocks
- **What and when.** As for copper: published at 09:00 London, dated here at the day Westmetall lists them.
- **Base rate (code, below).** A small reaction in 2008–2014 that is gone since 2015. Through 2014 LME aluminium stocks were dominated by warehouse queues and financing deals; the LME's queue rules took effect from 2015.

## SHFE weekly stocks
- **Base rate (code, below).** No measurable reaction of LME aluminium to the SHFE surprise.

## NBS manufacturing PMI days
- **Base rate (code, below).** No extra volatility on PMI days against the gold control or placebo days.

## Pitfalls
- Much aluminium sits off-exchange: visible stocks understate the total and can move on financing, not use.
- Chinese supply is capped by policy (~45 Mt); output news from China is a policy story first.
- Nothing here may alert until the testing gate passes it.

<!-- code: reaction base rates (pmstack metals --write) -->
## Reaction base rates (code, as of 2026-10-23)

### Stock changes
Daily closes on stock-report days vs other days. Surprise = the change vs its own norm (SHFE weekly: same and adjacent ISO weeks of the prior 5 years; LME daily: trailing 250-day mean and sd of daily changes), in sd. Sign hit = a bigger-than-normal draw with a price rise. Contemporaneous: predicts nothing. Full numbers: `estimates/stocks-*.json`.

| Pair | Events | Vol ratio (report / other) | Big-move rate report vs other (lift) | Sign hit at abs(z) >= 1 (95% CI) | Slope per 1 sd (t) | Slope per 1,000 t (t) | Halves: slope per sd | Since 2015: slope per sd (t) | Placebo day before / after (t) |
|---|---|---|---|---|---|---|---|---|---|
| LME aluminium stocks vs LME aluminium 3-month (daily) | 4637 (2008-2026) | - | - vs - (-) | 53% of 414 (48%-58%) | -0.02% (-1.6) | -0.003% (-2.5) | -0.06 / -0.01 | -0.01 (-0.8) | -0.03 (-2.0) / -0.01 (-1.3) |
| SHFE aluminium stocks vs LME aluminium 3-month (weekly) | 340 (2020-2026) | 1.03 | 12% vs 13% (0.91) | 51% of 107 (42%-61%) | -0.01% (-0.1) | -0.002% (-0.3) | -0.02 / -0.01 | -0.01 (-0.1) | -0.16 (-2.1) / 0.01 (0.2) |

### China data days
Volatility of daily returns on NBS manufacturing PMI days (last calendar day of the month, 09:30 Beijing; weekend releases priced next trading day) vs other days. Gold on the same days is the month-end control; placebo = the same days shifted 5 trading days back or 10 forward (clear of the first week of the month: ISM, Caixin, payrolls); weekend releases share the first trading day with ISM and Caixin, so weekday releases are also shown alone. No surprise measure (no free consensus).

| Market | Events | Vol ratio (PMI day / other) | vs gold control | Big-move rate PMI vs other (lift) | Levene p | Halves | Placebo -5d / +10d | Weekday releases only: ratio (n) |
|---|---|---|---|---|---|---|---|---|
| LME aluminium 3-month | 105 (2018-2026) | 0.92 | 0.94 | 12% vs 12% (0.99) | 0.396 | 0.85 / 0.98 | 1.08 / 1.05 | 0.90 (75) |
| COMEX gold (month-end control) | 105 (2018-2026) | 0.98 | - | 17% vs 13% (1.34) | 0.742 | 1.08 / 0.93 | 0.89 / 0.91 | 0.85 (75) |

LME stocks are dated at the day Westmetall lists them; LME publishes them at 09:00 London for the previous day's moves, so a one-day offset is possible (the day-after placebo would show it). Prices and stocks via Westmetall (LME) and SHFE: personal use only. A daily report leaves no other days, so vol ratio and big-move lift are blank for LME. China customs trade days are not covered (no dated calendar yet: open-questions.md).
<!-- /code -->
