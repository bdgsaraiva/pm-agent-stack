# Event playbooks: products

## wpsr: EIA Weekly Petroleum Status Report
- **What and when.** EIA's survey of US petroleum supply for the week ending Friday 07:00. Tables go up Wednesday at 10:30 ET and the full PDF at 13:00. In holiday weeks the release moves, usually to Thursday 12:00 ET (schedule: https://www.eia.gov/petroleum/supply/weekly/schedule.php). Weekly data are "generally not revised"; the crude balancing item is the "crude oil supply adjustment" (WPSR Appendix B, https://www.eia.gov/petroleum/supply/weekly/pdf/appendixb.pdf).
- **What to read first.** Gasoline stocks for RBOB and distillate stocks for ULSD against their seasonal norms. Each product's futures react to the other products' surprises too (Linn et al. 2017), so read all three stock changes together. The distillate reaction held in both halves of 2001-2026; gasoline's weakened somewhat.
- **How the surprise is measured here.** No survey is stored. The surprise is the week's change minus the average change in the same and adjacent weeks of the prior five years, in sd of those changes: the same number as the fact pack's EIA table and Balances section. The literature measures surprises against a survey, and analysts add information beyond seasonal norms (Gay, Simkins & Turac 2009; Ederington et al. 2019). For crude the survey removes only about a quarter of the weekly change's variance (derived from Miao et al. 2018). A slope against this proxy is therefore a **lower bound** (noisy surprises attenuate it: Halova, Kurov & Kucher 2014). Sign agreement and conditional moves are the headline numbers.
- **The day before is part of the reaction.** API publishes Tuesday at 16:30 ET, after the NYMEX settle, so its news lands in Wednesday's close-to-close return. Pre-positioning also shows up on day -1 (Miao et al. 2018: the coming surprise is significant at lead -1). The repo data agree (see the placebo column below), so do not read the release day as the whole move.
- **Eras.** The petroleum reaction weakened after 24-hour electronic trading in June 2006 (Linn et al., EIA workshop 2017). The table shows the since-2015 block. When it is under half the full-sample slope, the recent block is the base rate (Cushing today).
- **Pitfalls.** Weekly product supplied is noisy (use the 4-week average). A large crude adjustment makes the crude change noisy. Never write "vs consensus": the proxy is a seasonal norm. A base rate explains the release-day move; it does not predict the next one. Nothing here may alert until the testing gate (`/research`) passes it.
- **Reading a coming release.** Next release date: in the pack (`next_events`). The pack also carries the latest surprise, the comparable past releases (same side, at least as large) and the since-2015 slope. Write any expectation as "Read:" inference, never as a forecast.

<!-- code: reaction base rates (pmstack events --write) -->
## Reaction base rates (code, as of 2026-10-23)

Daily closes (Yahoo continuous front month, personal use only) on release days vs other days. Surprise = the week's change minus the average change in the same and adjacent weeks of the prior 5 years, in sd of those changes (the fact pack's surprise z). Contemporaneous: explains the release-day move, predicts nothing. Full numbers: `estimates/*.json`.

| Report / pair | Events | Vol ratio (release / other) | Big-move rate release vs other (lift) | Sign hit at abs(z) >= 1 (95% CI) | Slope per 1 sd (t) | Slope per unit (t) | Halves: slope per sd | Since 2015: slope per sd (t), hit | Placebo day before / after (t) |
|---|---|---|---|---|---|---|---|---|---|
| wpsr US gasoline stocks vs RBOB | 1343 (2001-2026) | 1.08 | 16% vs 10% (1.54) | 67% of 449 (62%-71%) | -0.53% (-8.1) | -0.245% per 1 million barrels (-7.8) | -0.65 / -0.42 | -0.41 (-4.1), 64% | -0.06 (-0.9) / -0.13 (-2.1) |
| wpsr US distillate stocks vs ULSD | 1344 (2001-2026) | 1.04 | 16% vs 12% (1.30) | 66% of 487 (62%-70%) | -0.42% (-7.0) | -0.229% per 1 million barrels (-7.0) | -0.41 / -0.44 | -0.43 (-4.2), 65% | -0.06 (-0.8) / 0.08 (1.4) |

Release dates follow EIA's rule (Wednesday 10:30 ET for petroleum, Thursday for gas; holidays shift them) and are approximate around holidays (EIA's holiday alternates are mostly Thursday 12:00 ET, still before the settle). Slopes against a free proxy are attenuated lower bounds (Halova, Kurov & Kucher 2014); the day before carries part of the reaction (API Tuesday 16:30 ET; Miao et al. 2018). Outliers beyond 8 robust sd (roll gaps, April 2020) are dropped and counted in the JSON.
<!-- /code -->
