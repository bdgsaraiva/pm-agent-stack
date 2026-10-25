# Event playbooks: copper

## LME daily stocks
- **What and when.** The LME publishes warehouse stocks at 09:00 London for the previous day's deliveries in and out. Westmetall lists them with the day's official prices; the repo dates them at that day.
- **What to read first.** The change against its trailing norm (z), then the cash-3-month spread: a draw with a widening backwardation is the storage signature (Fama & French 1988). LME stock moves are often transfers between venues or warrant moves (cancellations ahead of load-out), so read a single day with care.
- **Base rate (code, below).** COMEX copper moves against the LME stock surprise on the report day, with similar slopes in both halves and both eras. But the day after carries part of the move too (or the dating is off by a day), and the day before is close to significant: price and warehouse flows feed each other (falling prices bring metal into LME sheds). Treat the slope as a contemporaneous association, not the information content of the report.

## SHFE weekly stocks
- **What and when.** Last trading day of the week, about 15:20 Beijing, before London and New York trade that day. Deliverable-quality stock and the part on warrant, by warehouse.
- **Base rate (code, below).** No measurable reaction of COMEX copper to the SHFE surprise. Changes that span a skipped holiday week are dropped (not comparable with one-week norms), and the norm needs five full prior years, so the table starts in 2020. The SHFE number still matters as a level: it is half of the visible-stocks figure in the storage test, and it swings with the Chinese New Year build and spring draw (the 5-year same-week norm takes care of the season, but the holiday moves across ISO weeks).

## NBS manufacturing PMI days
- **What and when.** 09:30 Beijing on the last calendar day of the month (NBS calendars), weekends included; a weekend release is priced on the next trading day.
- **Base rate (code, below).** Copper's volatility on PMI days is no higher than on other days, against gold on the same days and against placebo days. No surprise is measured (no free consensus), so this says only that the day is not unusually volatile on average.

## Pitfalls
- Never write "vs consensus": every surprise here is against the series' own norm.
- Visible stocks are a small, shifting share of world stocks; COMEX stocks (missing here) absorbed metal in the 2025 tariff episode.
- Nothing here may alert until the testing gate (`/research`) passes it.

<!-- code: reaction base rates (pmstack metals --write) -->
## Reaction base rates (code, as of 2026-10-23)

### Stock changes
Daily closes on stock-report days vs other days. Surprise = the change vs its own norm (SHFE weekly: same and adjacent ISO weeks of the prior 5 years; LME daily: trailing 250-day mean and sd of daily changes), in sd. Sign hit = a bigger-than-normal draw with a price rise. Contemporaneous: predicts nothing. Full numbers: `estimates/stocks-*.json`.

| Pair | Events | Vol ratio (report / other) | Big-move rate report vs other (lift) | Sign hit at abs(z) >= 1 (95% CI) | Slope per 1 sd (t) | Slope per 1,000 t (t) | Halves: slope per sd | Since 2015: slope per sd (t) | Placebo day before / after (t) |
|---|---|---|---|---|---|---|---|---|---|
| LME copper stocks vs COMEX copper (daily) | 4589 (2008-2026) | - | - vs - (-) | 57% of 886 (54%-61%) | -0.16% (-6.8) | -0.032% (-6.7) | -0.16 / -0.17 | -0.18 (-7.5) | -0.05 (-1.9) / -0.08 (-3.7) |
| SHFE copper stocks vs COMEX copper (weekly) | 340 (2020-2026) | 1.10 | 15% vs 12% (1.26) | 50% of 123 (42%-59%) | 0.00% (0.0) | 0.001% (0.2) | -0.01 / 0.01 | 0.00 (0.0) | -0.07 (-1.0) / 0.03 (0.5) |

### China data days
Volatility of daily returns on NBS manufacturing PMI days (last calendar day of the month, 09:30 Beijing; weekend releases priced next trading day) vs other days. Gold on the same days is the month-end control; placebo = the same days shifted 5 trading days back or 10 forward (clear of the first week of the month: ISM, Caixin, payrolls); weekend releases share the first trading day with ISM and Caixin, so weekday releases are also shown alone. No surprise measure (no free consensus).

| Market | Events | Vol ratio (PMI day / other) | vs gold control | Big-move rate PMI vs other (lift) | Levene p | Halves | Placebo -5d / +10d | Weekday releases only: ratio (n) |
|---|---|---|---|---|---|---|---|---|
| COMEX copper | 105 (2018-2026) | 0.97 | 0.99 | 12% vs 13% (0.96) | 0.773 | 0.88 / 1.04 | 0.97 / 0.90 | 0.94 (75) |
| COMEX gold (month-end control) | 105 (2018-2026) | 0.98 | - | 17% vs 13% (1.34) | 0.742 | 1.08 / 0.93 | 0.89 / 0.91 | 0.85 (75) |

LME stocks are dated at the day Westmetall lists them; LME publishes them at 09:00 London for the previous day's moves, so a one-day offset is possible (the day-after placebo would show it). Prices and stocks via Westmetall (LME) and SHFE: personal use only. A daily report leaves no other days, so vol ratio and big-move lift are blank for LME. China customs trade days are not covered (no dated calendar yet: open-questions.md).
<!-- /code -->
