# Headline audit, first pass (20 Oct 2026)

Twelve narrative definitions with stored headlines, 25 headlines each (`python -m pmstack narratives audit <id>`: a reproducible draw over the stored days). Two blind model labellers marked each headline y (about the narrative) or n (false match) from the headline and URL words only, against the meanings in `config/sources.yaml`. They agreed on 96.3% of the 300 headlines (Cohen's kappa 0.91). Precision below is the share both marked y, with a Wilson 95% interval; disagreements are listed for Bernardo's call and are not yet written into the sheets.

| Definition | A: y/25 | B: y/25 | Both y | Precision (Wilson 95%) | Disagreements (#) |
|---|---:|---:|---:|---|---|
| `fed_hike_v2` | 25 | 25 | 25 | 87–100% | - |
| `hormuz_iran_v1` | 24 | 24 | 24 | 80–99% | - |
| `russia_oil_v2` | 24 | 24 | 24 | 80–99% | - |
| `ai_bubble_v2` | 23 | 23 | 23 | 75–98% | - |
| `us_gasoline_v1` | 22 | 21 | 21 | 65–94% | 12 |
| `inflation_scare_v2` | 21 | 21 | 20 | 61–91% | 15, 18 |
| `natgas_lng_v2` | 19 | 19 | 19 | 57–89% | - |
| `trade_war_v2` | 19 | 18 | 18 | 52–86% | 22 |
| `crop_weather_v2` | 11 | 11 | 11 | 27–63% | - |
| `gold_buying_v2` | 11 | 18 | 11 | 27–63% | 1, 3, 4, 5, 8, 11, 18 |
| `opec_supply_v3` | 5 | 5 | 5 | 9–39% | - |
| `copper_shortage_v2` | 4 | 4 | 4 | 6–35% | - |

**Read (inference):** Hormuz, Russian oil, Fed hikes, AI bubble, US pump prices and inflation scare are precise enough to read. Trade war and natural gas are usable with care. Copper (mostly junior-miner press releases and copper theft), OPEC+ (mostly demand forecasts and the OPEC Fund) and crop weather (pumpkins, sport "harvest") are not. Gold depends on whether daily price reports count as "gold buying" (the labellers split on that rule).

Round 3 of the measurement (`docs/research/narrative-measure/2026-10-20-result.md`, 5.7 GB) tested tighter definitions: precise copper, OPEC+ and crop definitions average 2-7 articles a day, far under the 20-a-day floor; gold with price moves reaches 47 a day but is mostly retail "gold price today" pages.
