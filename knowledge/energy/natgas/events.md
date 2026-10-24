# Event playbooks: natgas

## wngsr: EIA Weekly Natural Gas Storage Report
- **What and when.** Lower 48 working gas as of Friday 9:00 CST, released Thursday 10:30 ET; holidays move it (often a day earlier). Methodology: https://ir.eia.gov/ngs/methodology.html. Revisions above 500 MMcf are published, and reclassifications of 4 Bcf or more are excluded from implied flow.
- **Surprise.** The week's change minus the 5-year same-week norm, in sd (the same definition as for petroleum). EIA's own 5-year average uses daily interpolation, so the two will not match exactly. Surprises under about 4 Bcf sit inside EIA's sampling error (about 2 Bcf).
- **What the literature found.** Gas reacts two to three times more per sd than petroleum, and only on the release day (Chiou-Wei, Linn & Zhu 2014; Linn et al. 2017). Release-interval volatility is about six times other days (Linn & Zhu 2004, intraday). Daily gas volatility does respond to surprises, unlike crude's (Chebbi 2019). Reactions are larger in the injection season and when stocks are high (Farhangdoost & Etienne 2020), and some later samples find them shrinking: estimate on rolling windows.
- **Control days.** Mondays have higher gas volatility (Mu 2007); the playbook will exclude them from the control days.
- **Status.** The gas series (`eia_ng`) is fetched from the 24 Oct 2026 data run on. The table below fills in once it is stored (`pmstack events --write`).

