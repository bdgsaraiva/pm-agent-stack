# Ags specialist: literature review and design (S4)

Written 30 Oct 2026 for phase S4 (`docs/project/specialists-kickoff.md`): corn, soybeans, wheat, sugar. One research pass in this session (the brief's seed reading plus the most cited work it misses) and a source check. Most rows rest on abstract pages and working-paper listings, not full texts: each row says which. Anything recalled but not confirmed on an opened page is marked *not page-checked*. Agent 9's evidence for WASDE, PSD and NASS balances is in `docs/research/balance.md`; storage theory is shared with `energy.md` and `metals.md`.

Rule kept from the brief (§4): no broker's quantified sensitivity is copied in. Search results on the Brazil sugar/ethanol mix were mostly broker or consultancy notes (StoneX, Czapp); they are not used.

## 1. Papers: finding → what it changes

### Scheduled USDA reports
| Finding | What it changes | Source |
|---|---|---|
| **Adjemian (2012), "Quantifying the WASDE announcement effect", AJAE 94(1).** WASDE releases move corn, soybean and wheat futures significantly. The effect holds across contract months, is not limited to months with NASS crop surveys, is larger when carryover is low (soybeans, wheat), and is absorbed quickly. | WASDE-day volatility playbook per market. The split by stocks-to-use regime is an open question: agent 9's percentile history starts in 2021, too few reports. | RePEc listing https://ideas.repec.org/a/oup/ajagec/v94y2012i1p238-256.html (findings via secondary summaries, *not page-checked* in the paper) |
| **Karali, Isengildina-Massa, Irwin, Adjemian & Johansson (2019), Food Policy 84.** Surprise size (USDA estimate minus analysts' expectations) has stayed about the same over time. Price reactions to most reports have *grown*, even where private data compete. | Do not assume USDA reports are "priced in". The playbooks report an early and a recent era. | https://ideas.repec.org/a/eee/jfpoli/v84y2019icp66-76.html (abstract) |
| **Isengildina-Massa, Karali, Irwin, Adjemian & Johansson (2021), "When does USDA information have the most impact on crop and livestock markets?", J. Commodity Markets 22.** | Title only in this pass: seasonality of report effects is a known question. | https://ideas.repec.org/a/eee/jocoma/v22y2021ics2405851320300143.html (*not page-checked*) |
| **Lehecka (2014), JARE 39(1).** Crop Progress and Condition reports, 1986–2012: close-to-open return variability differs on release days. Reactions are quick, strongest in July and August, and have grown over time. | The crop-progress playbook measures the next-day move against the condition change. It reports July–August separately from the rest of the season. | https://ideas.repec.org/a/ags/jlaare/168261.html (abstract) |
| Grain Stocks and Acreage (end of March and June) often bring the year's largest report-day moves in corn and soybeans. Extension commentary shows both large moves and reversals. | Volatility-only playbook. There is no consensus here, so there is no surprise measure. | farmdoc daily, e.g. https://farmdocdaily.illinois.edu/2018/07/implications-usda-reports-corn-soybeans.html (extension commentary) |
| USDA moved WASDE, Crop Production, Grain Stocks, Acreage and Prospective Plantings from 08:30 to 12:00 ET, during trading hours, from 11 January 2013. | WASDE days are priced on the same day's close in both regimes; the eras split at 11 Jan 2013. | Agri-Pulse "USDA to begin noon-time crop reports on January 11"; USDA release-time notice (Sep 2012) https://www.usda.gov/sites/default/files/documents/USDA_Release_time_change_9_19_12.pdf (seen in search) |

### Stocks, weather and ENSO
| Finding | What it changes | Source |
|---|---|---|
| **Wright (2011/2012), "The economics of grain price volatility".** Price spikes happen when aggregate stocks are near minimal feasible levels. The balance of consumption, supply and stocks still explains these markets. | Stocks-to-use and its percentile (agent 9) are the first balance figures on the card. Low stocks-to-use is read as "small shocks move price more", never as a direction. | World Bank Research Observer (2012); summary https://www.agriskmanagementforum.org/content/price-volatility-agricultural-commodities-market-fundamentals (secondary) |
| **Schlenker & Roberts (2009), PNAS.** Yields rise with temperature up to about 29 °C for corn and 30 °C for soybeans, and fall steeply above. | Heat during pollination (July) is the key US weather risk. Daily temperature data are not stored (open question): the card says so instead of guessing. | https://pmc.ncbi.nlm.nih.gov/articles/PMC2747166 (abstract) |
| **Iizumi et al. (2014), Nature Communications 5:3712.** El Niño likely raises global-mean soybean yields and changes maize, rice and wheat by −4.3% to +0.8%. La Niña years tend to show below-normal global yields for all four (−4.5% to 0%). | ENSO is a named driver with literature sizes. ONI (NOAA) is in the pack as context, never as a forecast. | https://eprints.whiterose.ac.uk/id/eprint/80272/ (abstract) |
| **Ubilava (2018), AJAE 100(1).** ENSO shocks are linked to agricultural and metal prices. Up to 30% of price variation at intermediate horizons is attributed to ENSO (WP listing). El Niño effects are stronger than La Niña's. | Same driver; size quoted as "up to", from the working-paper listing. | https://ideas.repec.org/a/oup/ajagec/v100y2018i1p239-263..html; UC Davis seminar listing (WP) |

### Brazil
| Finding | What it changes | Source |
|---|---|---|
| USDA's Brazil soybean estimates have run above Conab's since 2018/19, and the gap is widening (yield and area). USDA builds balance-sheet-consistent numbers; Conab uses surveys, models and crop tours. | The card shows Conab's survey as first published, beside USDA's world numbers. Neither is "right". The open question tracks the gap. | farmdoc daily (Apr 2024) https://farmdocdaily.illinois.edu/2024/04/what-explains-the-disparity-between-usda-and-conab-over-brazils-soybean-crop-size.html |
| Brazil's Centre-South mills switch cane between sugar and ethanol on relative returns (ethanol parity with gasoline, the real). | A frame for sugar in the primer only, with no sizes: the quantitative sources found were broker or consultancy notes. ANP's Brazil fuel sales (S1) stay context. | Trade press, S&P Global news (2022) |

## 2. Source check (30 Oct 2026; Bernardo chose three of four)
| Source | Result | Used as |
|---|---|---|
| USDA ESMIS release archive | `esmis.nal.usda.gov/publication/<slug>`: every release with date and time, back to the 1970s (WASDE). It also lists future scheduled dates, which the adapter drops. | `esmis`: exact days for WASDE, Crop Progress, Grain Stocks, Acreage, Prospective Plantings |
| Conab surveys | One page per monthly survey with "Publicado em" and a per-product workbook. Workbooks are .xlsx from about 2021/22; older ones are .xls and skipped. Old pages were re-published in 2025, so the page date is checked against the survey month in the file name. | `conab`: `conab:<crop>:production:<year>@<publication date>` (vintages) |
| USDA export sales | API moved to `api.fas.usda.gov/api/esr` (same api.data.gov key as PSD). One row per country and week; summed by the adapter. Market year labelled by its end year. | `fas_esr` |
| NOAA ONI | Plain-text file, 1950 on. | `noaa_oni` |
| US Drought Monitor | Statistics API (CSV), cumulative D0–D4 shares; CONUS and states by postal code. | `usdm`: CONUS (state statistics answered once, then empty: open question) |
| World Bank Pink Sheet | Maize, soybeans, US HRW wheat, world sugar added to the S3 block. | long-run real prices |
| UNICA | Only the latest biweekly PDF is online; no archive. | Not used |
| Secex / ComexStat | Public API, rate-limited (HTTP 429 every few calls). | Not chosen |

## 3. Design
- **Report days are disjoint categories** (review S4): WASDE without January; January (WASDE + annual Crop Production + Grain Stocks); March and June (Grain Stocks + Prospective Plantings / Acreage); September Grain Stocks alone. No day counts twice.
- **WASDE days.** Volatility ratio (report day vs other days), a local ratio vs the 10 trading days either side (the seasonal control), big-move lift and placebo days per market, since 2000, with exact dates from ESMIS. Placebos leave out every USDA report day and every Crop Progress reaction day (the Tuesday after a Monday report). Where WASDE is stored as first published (2021 on, agent 9), the same-day return is also fitted against the US ending-stocks revision vs the previous report, in sd of revisions. This is a weak proxy: there is no consensus, so the market already knew part of the revision.
- **Crop progress.** The good/excellent change on the week (changes across the gap between seasons left out), against the average change in the same and adjacent weeks of the prior five seasons, in sd; an event needs changes from five distinct prior seasons. Priced on the next trading day's close, because the report comes out at 16:00 ET after the close. Corn, soybeans, winter and spring wheat from 2015 (NASS Quick Stats), so events start in 2020. July–August is split from the rest.
- **January, March/June and September days.** Volatility only.
- **Sugar.** No US report playbook: US crop reports don't move world sugar (#11). The sugar card relies on prices, CFTC, WASDE and PSD balances and long-run prices; UNICA is not available.
- Same statistics code as the energy and metals playbooks: `events.base_rates` and `metals.day_vol`.

## 4. How it works (worked example)
Written after the live run, in `docs/project/notes-A18.md`.
