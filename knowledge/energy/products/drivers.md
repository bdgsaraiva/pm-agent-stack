# Drivers: products

Rendered from `drivers.yaml` by `pmstack/knowledge.py`; do not edit by hand. Each size says where it came from (literature, own estimate, Bernardo prior). Status comes from the testing gate (`/research`); "untested" claims are hypotheses, not signals.

## inventory-vs-basis-heating-oil

- **Claim:** Lower distillate (heating oil) inventories vs normal go with a higher basis.
- **Driver → target:** Inventory vs normal (I/I*) → Basis, near minus next (%/yr)
- **Sign / lag:** - / same month
- **Status:** literature only
- **Source:** Gorton, Hayashi & Rouwenhorst (2013)
- Size, literature: -137.6 %/yr basis per unit I/I* (at I/I* = 1) ([GHR NBER WP 13249 (heating oil, t -6.03)](https://www.nber.org/system/files/working_papers/w13249/w13249.pdf), Table 3)

## eia-gasoline-surprise

- **Claim:** A bigger-than-normal draw in US gasoline stocks goes with a RBOB rise on release day.
- **Driver → target:** US gasoline stocks, weekly change minus 5-year same-week average (sd) → RBOB front-month return on the WPSR release day
- **Sign / lag:** - / same day (contemporaneous)
- **Status:** untested
- **Source:** pmstack events (EIA WPSR, Yahoo)
- Size, own estimate: -0.529 % per 1 sd surprise, 90% CI -0.637 to -0.421, n 1343, as of 2026-10-23 ([regression](knowledge/energy/products/estimates/wpsr-gasoline.json))
- Notes: Explains the release-day move; predicts nothing. Similar slope in both halves of 2001-2026.

## eia-distillate-surprise

- **Claim:** A bigger-than-normal draw in US distillate stocks goes with a ULSD rise on release day.
- **Driver → target:** US distillate stocks, weekly change minus 5-year same-week average (sd) → ULSD front-month return on the WPSR release day
- **Sign / lag:** - / same day (contemporaneous)
- **Status:** untested
- **Source:** pmstack events (EIA WPSR, Yahoo)
- Size, own estimate: -0.424 % per 1 sd surprise, 90% CI -0.524 to -0.324, n 1344, as of 2026-10-23 ([regression](knowledge/energy/products/estimates/wpsr-distillate.json))
- Notes: Explains the release-day move; predicts nothing. Similar slope in both halves of 2001-2026.
