# Drivers: gold

Rendered from `drivers.yaml` by `pmstack/knowledge.py`; do not edit by hand. Each size says where it came from (literature, own estimate, Bernardo prior). Status comes from the testing gate (`/research`); "untested" claims are hypotheses, not signals.

## real-yields

- **Claim:** Higher US real yields go with a weaker gold price.
- **Driver → target:** US 10-year real yield (DFII10) → Gold price
- **Sign / lag:** - / same day to months
- **Status:** literature only
- **Source:** Erb & Harvey (2013); post-2022 commentary (Janus Henderson)
- Notes: The direction still holds day to day, but the level relation broke from 2022 as emerging-market central banks doubled their buying. No fair-value model. Beta before/after 2022: open question.

## official-buying

- **Claim:** Central-bank gold buying lifts the real gold price.
- **Driver → target:** Official-sector purchases (tonnes) → Real gold price
- **Sign / lag:** + / quarters
- **Status:** literature only
- **Source:** Erb & Harvey (2013) (emerging-market holdings scenario); a 1968-2015 study finds no consistent relation (CXO summary)
- Notes: No size: a broker per-tonne sensitivity exists and is not used (brief section 4); academic evidence is weak.

## real-price-mean-reversion

- **Claim:** High real gold prices have been followed by below-average real returns.
- **Driver → target:** Real gold price vs its history → Subsequent real gold return
- **Sign / lag:** - / years
- **Status:** literature only
- **Source:** Erb & Harvey (2013), The Golden Dilemma, FAJ 69(4)
- Notes: The authors frame it as a dilemma: mean reversion vs 'this time is different' (emerging-market official demand). Context for estimates/longrun.json, never a timing signal.

## safe-haven

- **Claim:** Gold holds or rises on extreme equity-market falls, briefly.
- **Driver → target:** Large equity drawdown days → Gold return
- **Sign / lag:** + / days
- **Status:** literature only
- **Source:** Baur & Lucey (2010), Financial Review
- Notes: Short-lived; market-specific in later work. Gold was sold for cash early in 2008 and 2020.
