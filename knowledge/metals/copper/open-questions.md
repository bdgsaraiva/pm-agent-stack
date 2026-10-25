# Open questions: copper

Hand-written questions to test or to ask (agent 11 carries them into calls). The code block at the end is rebuilt by `python -m pmstack knowledge check metals/copper`.

- Is the LME stock dating right (report published at 09:00 on the day Westmetall lists it)? The day-after slope is significant: check against LME's own stock report for a few dates.
- Add COMEX stocks (CME blocks scripts): any other public route? The 2025 tariff moved metal into COMEX sheds.
- Combine SHFE bonded stocks and Shanghai premium (Yangshan) once a free source exists: does the visible-stocks fit improve?
- The storage fit's intercept shifts between blocks: is it the 2021 LME backwardation cap, the tariff premium, or a change in the share of stocks that is visible?
- China customs trade days: build a dated calendar (GACC press releases) and run the volatility playbook.
- Bernardo's priors on copper drivers (arriving through the inbox) vs these estimates.
