# Drivers: sugar

Rendered from `drivers.yaml` by `pmstack/knowledge.py`; do not edit by hand. Each size says where it came from (literature, own estimate, Bernardo prior). Status comes from the testing gate (`/research`); "untested" claims are hypotheses, not signals.

## brazil-mix

- **Claim:** Brazil's mills shift cane from sugar to ethanol when ethanol pays more (ethanol parity with gasoline, the real).
- **Driver → target:** Ethanol vs sugar returns in Brazil → World sugar supply and No. 11
- **Sign / lag:** + / weeks to a season
- **Status:** literature only
- **Source:** Trade press (S&P Global news); broker notes found in the search are not used
- Notes: No size: the quantified sources were broker or consultancy research.

## enso

- **Claim:** ENSO shifts Asian monsoon and Brazilian rainfall, and with them cane yields.
- **Driver → target:** Oceanic Niño Index → World sugar supply
- **Sign / lag:** ? / months
- **Status:** literature only
- **Source:** Ubilava (2018)
- Size, literature: 30 % of price variation at intermediate horizons attributed to ENSO shocks (up to; working-paper listing) ([Ubilava (2018), AJAE 100(1)](https://ideas.repec.org/a/oup/ajagec/v100y2018i1p239-263..html), WP listing)

## wasde-day-volatility

- **Claim:** WASDE days are more volatile than other days for raw sugar.
- **Driver → target:** WASDE release day → ICE No. 11 daily return volatility
- **Sign / lag:** 0 / release day
- **Status:** untested
- **Source:** own estimate (pmstack ags)
- Size, own estimate: 0.952 report-day abs(return)/sd over the 10 days either side (paired t -1.09), n 298, as of 2026-10-29 ([regression](knowledge/ags/sugar/estimates/wasde-days.json#local))
- Notes: No effect: No. 11 is a world market and WASDE's sugar lines are US (#16).
