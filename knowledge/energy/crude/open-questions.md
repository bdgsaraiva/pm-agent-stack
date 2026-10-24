# Open questions: crude

Hand-written questions to test or to ask (agent 11 carries them into calls). The code block at the end is rebuilt by `python -m pmstack knowledge check energy/crude`.

- Does the inventory-to-basis slope (GHR 2013, crude) hold on the repo's own curve data once 250 days of contracts are stored (S2)?
- Cushing fill ratio needs EIA's working-capacity series (semi-annual): find and wire it, then test the Brent-WTI driver.
- Use first-release WPSR values from EIA's issue archive (2011 on) instead of latest values, and measure the difference in the surprise.
- A combination proxy (seasonal norm plus the trailing 4-week change, Alturki & Kurov 2022) fitted out of sample: does it raise the sign hit rate?
- Does the reaction depend on the inventory regime (stocks below vs above the 5-year range) or the trend regime (Bu 2014: none in steep sell-offs)?

<!-- code: prior-vs-estimate (pmstack knowledge check) -->
## Prior vs estimate (code)

No disagreement between a Bernardo prior and an estimate.
<!-- /code -->
