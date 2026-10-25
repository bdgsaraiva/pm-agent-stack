# Metals specialist: literature review and design (S3)

Written 25 Oct 2026 for phase S3 (`docs/project/specialists-kickoff.md`): gold, copper, aluminium and iron ore. One research pass in this session (web search on the brief's seed reading plus the most cited work it misses) and a source check. Most rows rest on abstract pages, working-paper listings or publisher summaries, not full texts: each row says which. Anything recalled but not confirmed on an opened page is marked *not page-checked*. The pillar's design rules are in `docs/research/specialists-architecture.md`; storage-theory rows shared with energy are in `docs/research/energy.md`.

Rule kept from the brief (§4): **a broker's own quantified sensitivity is never copied in.** One search turned up a bank's per-100-tonne gold sensitivity. It is broker research, so it is not recorded here or in `drivers.yaml`.

## 1. Papers: finding → what it changes

### Long-run prices and supercycles
| Finding | What it changes | Source |
|---|---|---|
| **Stuermer (2018), "150 years of boom and bust".** Annual data 1840–2010: demand shocks, not supply shocks, drive most long-run mineral price swings. Demand effects last up to about 15 years; supply shocks fade within about 5. Supply matters more for copper and tin (oligopolistic structure). | The card names the shock type as inference, and a demand-led boom is described as long-lived. A copper supply disruption is not dismissed by default. Driver `demand-shocks-dominate`. | Dallas Fed WP 1414 https://www.dallasfed.org/-/media/documents/research/papers/2014/wp1414.pdf (abstract; published in Macroeconomic Dynamics 2018, *not page-checked*) |
| **Jacks & Stuermer (2020), "What drives commodity price booms and busts?"** 12–15 commodities from 1870: demand shocks "strongly dominate"; supply shocks are limited and transitory for most commodities; rapid industrialisation and urbanisation drive much of the booms. | Same reading as Stuermer, on a wider set. | Dallas Fed WP 1614 https://www.dallasfed.org/research/papers/2016/wp1614 (WP listing; the Energy Economics version *not page-checked*) |
| **Erten & Ocampo (2013), World Development 44.** Four supercycles since 1865 lasting 30–40 years, with amplitudes 20–40% above or below trend. Non-oil cycles track world GDP (demand-driven). Each non-oil cycle's mean is lower than the last (Prebisch–Singer); metals' long-run trend fell, but less than agriculture's. | Long-run context in code: each metal's real price as a percentile since 1960, vs its trailing 10 years and vs a log-linear trend (`longrun` block). Said as context, never as a cycle-phase call: the band-pass filter they use is unreliable at the sample end. | https://desapublications.un.org/working-papers/super-cycles-commodity-prices-mid-nineteenth-century (WP abstract) |

### Storage, inventories and curves
| Finding | What it changes | Source |
|---|---|---|
| **Fama & French (1988), "Business cycles and the behavior of metals prices", JF 43(5).** Futures prices vary less than spot prices when inventory is low; similarly when it is high. Demand shocks near business-cycle peaks drain inventories and invert the curve. The marginal convenience yield falls at a decreasing rate as inventory rises. | Two code tests on LME data (`storage` block): the cash-3-month spread vs log visible stocks (convex: log), and the cash/3-month volatility ratio vs log stocks. | https://afajof.org/issue/volume-43-issue-5 (abstract) |
| **Geman & Smith (2013), Resources Policy 38(1).** Strong support for both storage predictions (spread and volatility rise as inventory falls) across the six LME base metals. Adding SHFE stocks strengthens the relation. They introduce the "inventory-implied" spot price and volatility. | Visible stocks = LME + SHFE. The card shows the inventory-implied spread from our own fit beside the actual spread. | https://eprints.bbk.ac.uk/id/eprint/4891 (abstract) |
| **Counterpoint: Toyne (1989–2000 sample).** Inventory–variance relations held for four LME metals, not for two. | The test is run per metal, with blocks and a residual unit-root check; a failure is reported, not hidden. | https://ageconsearch.umn.edu/record/125169/ (abstract) |
| **Gorton, Hayashi & Rouwenhorst (2013).** The basis is a decreasing non-linear function of inventories, across commodities. | Same shape as for energy (`docs/research/energy.md`); metals get their own estimate rather than borrowing energy slopes. | https://www.nber.org/papers/w13249 (WP) |
| **Tang & Zhu (2016), "Commodities as collateral", RFS 29(8).** Under capital controls and high domestic rates, metals are imported to China and pledged as collateral; collateral demand explains roughly 12–15% of the industrial-metals price rise since 2007 (WP estimate). | Chinese bonded and visible stocks can move for financing reasons, not consumption. A stock build in China is not read as weak demand by default. Driver `china-collateral-demand`. | https://www.mit.edu/~zhuh/TangZhu_CommodityCollateral_RFS.pdf (paper listing; the 12–15% from the WP, *not page-checked* in the RFS version) |
| **LME warehouse episodes.** In October 2021 the copper cash-3-month spread went from single digits to over $1,000/t as on-warrant stocks fell to about 14,150 t; the LME then capped the prompt backwardation. | Low on-warrant stocks give very convex spreads; LME rule changes break the series. The spread fit runs on weekly data from 2014 and is checked in blocks. | Argus news report https://www.argusmedia.com/en/news/2265366-lme-copper-spreads-backwardated-amid-stock-squeeze (news, not research) |

### China demand
| Finding | What it changes | Source |
|---|---|---|
| **IMF WEO (2006), as reported.** In 2002–05 China accounted for about half the rise in world consumption of aluminium, copper and steel. | China demand is the first-order driver of the base-metals cycle in the primers. | Reported in https://secure.northernminer.com/commodities-markets/editorial-imf-gets-bearish-on-metals/1000056451 (secondary) |
| **Bank of Canada SDP 2016-7.** The Chinese housing boom explains roughly a quarter of the 85% rise in base-metal prices from 2002 to 2010. | Chinese property is a named driver with a literature size. Driver `china-housing`. | https://www.bankofcanada.ca/2016/03/staff-discussion-paper-2016-7/ (summary page) |
| **Roache (2012), IMF WP/12/115, "China's impact on world commodity markets".** Chinese demand shocks have a large effect on metals prices. | Background only; no size taken. | *not page-checked* (search did not return the paper) |
| **Reported consumption overstates use.** Much of China's metal "consumption" is re-exported in finished goods. | Apparent-demand figures are labelled as such. | CME Group education report https://www.cmegroup.com/education/featured-reports/industrial-metals-can-demand-meet-supply-challenge.html (exchange education piece) |

### Aluminium and power
| Finding | What it changes | Source |
|---|---|---|
| China's smelting capacity is capped at about 45 Mt a year (some sources say 45.5) since 2017, with one-for-one replacement. National output has run above the cap in 2026 through debottlenecking. | Chinese supply growth is a policy variable: the primer says so, and the open question asks for a dated output series. | Engineering News / Reuters (Sep 2026) https://www.engineeringnews.co.za/article/capped-at-home-china-extends-its-aluminium-dominance-abroad-reuters-says-2026-09-09; SMM https://news.metal.com/newscontent/103558094 (trade press) |
| Electricity is usually over a third of primary aluminium cost. Most Chinese smelters run on thermal power; hydro provinces (Yunnan, Sichuan) curtail in droughts. | Power cost and hydro conditions are named drivers (`power-cost`), with no size: no study tying curtailment to power prices was found. | S&P Global Commodity Insights news (2021, 2023) https://www.spglobal.com/commodity-insights/en/market-insights/blogs/metals/031723-southeast-asia-may-hold-the-key-to-chinese-aluminum-smelters-production-woes (price-reporting-agency news, not broker research) |

### Iron ore
| Finding | What it changes | Source |
|---|---|---|
| **RBA Bulletin (Sep 2013).** Chinese steel prices behave as a mark-up over iron ore and coking coal costs (structural VECM, weekly 2010–2013). | Iron ore is read through Chinese steel margins. The specialist says there is no free daily ore price or port-stock series here, and answers from monthly prices. | https://www.rba.gov.au/publications/bulletin/2013/sep/2.html |
| Regression studies on 2010–13 data find port inventories, freight and Australia/Brazil exports matter. | Short samples from one regime: not used for sizes. | Negotium (2013) via https://dialnet.unirioja.es/descarga/articulo/7205379.pdf (abstract) |

### Gold
| Finding | What it changes | Source |
|---|---|---|
| **Erb & Harvey (2013), "The Golden Dilemma", FAJ 69(4).** Gold hedges inflation only over centuries, not practical horizons. High real gold prices have been followed by below-average real returns. Emerging-market official buying toward developed-country holdings could lift the real price further: "this time is different" vs mean reversion. | The long-run block shows gold's real price percentile, with this dilemma as the frame. Never read as a forecast. | https://www.nber.org/papers/w18706 (abstract) |
| **Baur & Lucey (2010), Financial Review.** Gold is a hedge against stocks on average and a safe haven in extreme stock-market falls, but only briefly. Later work finds the property is market-specific. | "Safe haven" is a short-window, crash-day property: a card may cite it only for days with large equity falls. | https://econpapers.repec.org/paper/iisdispap/iiisdp198.htm (abstract) |
| **The 2022 break.** Since 2022, emerging-market central banks have bought about 1,000 t a year (2022–24) against about 500 t in the previous decade. Gold rose while real yields rose. | Real yields still give direction, but the level relation broke. Real yields are context in the pack, never a fair-value model. | Janus Henderson commentary https://www.janushenderson.com/hub/article/chart-to-watch-whats-behind-the-divergence-between-gold-and-real-treasury-yields/ (asset-manager commentary; the tonnages trace to the World Gold Council). An academic study over 1968–2015 finds no consistent link between official flows and price (CXO summary https://www.cxoadvisory.com/gold/central-bank-gold-reserveslending-and-gold-price) |

### Scheduled data and reactions
| Finding | What it changes | Source |
|---|---|---|
| No systematic event study of copper on China PMI days was found. News reports show both directions on PMI beats and misses. | The China-days playbook measures **volatility only** (no surprise without a free consensus), with gold as a month-end control and placebo days. | Search 25 Oct (news reports only) |
| NBS publishes the official manufacturing PMI at 09:30 Beijing on the last calendar day of the month, weekends included. Its yearly release calendars for 2018 and 2019 list month-end dates. Earlier timing is not documented here. | The playbook starts in 2018. A weekend release is priced on the next trading day. | NBS calendars https://www.stats.gov.cn/xxgk/sjfb/fbrcb/201907/t20190726_1759234.html, https://www.stats.gov.cn/xxgk/sjfb/fbrcb/201801/t20180118_1759233.html |

## 2. Source check (25 Oct 2026; Bernardo chose all four that passed)
| Source | Result | Used as |
|---|---|---|
| SHFE weekly stocks | JSON `.dat` files from about 2014 to 14 Nov 2025, an HTML page from 21 Nov 2025. Copper, aluminium and gold totals parse in both formats. Personal use. Whether GitHub Actions can reach it is unknown until the first run. | `shfe` block: `shfe:{cu,al}_{stock,warrants}`, `shfe:au_warrants`. Backfilled locally from 2014. |
| LME aluminium and earlier copper | Westmetall (same adapter as copper), history from 2008. **A parser bug was found and fixed:** "January" was rewritten to "Januaryy", so every January and February since 2008 was missing for copper too. | `lme_metals` block; copper 2008–2017 added. |
| IMF monthly metals via FRED | Copper and aluminium from 1992, iron ore monthly (public CSV, no key). | `fred_metals`, with US CPI to deflate. |
| World Bank Pink Sheet | Monthly from 1960, CC BY 4.0. The file address changes monthly, so it is read from the commodity-markets page. | `pinksheet`: copper, aluminium, iron ore, gold. |
| COMEX warehouse stocks | The CME blocks scripted requests (timeout). | Not used. |
| GLD holdings | spdrgoldshares.com returns a PDF or interstitial. | Not used. |
| China customs trade tables | Page reachable, but the data are not in a machine-readable form, and there is no fixed release rule. | Not used; open question. |
| Yahoo iron ore (TIO=F) | Last trade August 2021. | Not used. |

## 3. Where sources disagree, and the resolution
- **Storage theory.** Geman & Smith find strong support; Toyne found it held for four of six metals. Resolution: estimate per metal on our own data, with blocks and an ADF test on the residual. Quote a fit only when the residual is stationary and the block signs agree.
- **Gold and real yields.** Erb & Harvey's mean reversion vs the post-2022 central-bank level shift. Resolution: no fair-value model. Real yields and the dollar are context figures; gold's long-run percentile is shown as context with both readings.
- **Chinese stocks.** A build can mean weak demand or collateral financing (Tang & Zhu). Resolution: the card says which reading it takes and labels it inference.
- **Aluminium cap: 45 vs 45.5 Mt.** Both are cited in `primer.md` with their sources; nothing is computed from either.

## 4. Design changes vs the brief's spec
- **Playbooks without a consensus.** Metals have no EIA-style report. Stock-change reactions use each series' own norm: weekly SHFE changes against the same and adjacent ISO weeks of the prior 5 years, as in the EIA playbooks; daily LME changes against the trailing 250-day mean and sd. China data days measure volatility only.
- **Not built (Bernardo, 25 Oct):** gold on Fed and CPI days, and gold's beta to real yields before and after 2022. Both are open questions.
- **No iron ore playbook.** There is no free daily price or port-stock series. Iron ore is answered from monthly IMF and World Bank prices plus the literature, and the specialist says so.
- **Eras.** The stock playbooks split at 2015, when LME warehouse queue rules took effect. Energy keeps its 2006/2015 eras.
- **Storage spread net of interest (review, 25 Oct).** A 3-month spread carries about r × 91/360 of interest cost, and US rates went from 0 to about 5% over 2014–26. The fit therefore uses the raw spread plus the 3-month T-bill carry, as Fama & French (1988) use an interest-adjusted basis. With the adjustment, both metals' full-sample slopes sit inside their block ranges; on the raw spread they did not.
- **Out-of-sample implied spread.** Fitted without the last 13 weeks; suppressed unless significant, stationary (Engle-Granger 5%) and sign-stable across blocks.

## 5. How it works (worked example, as of 2026-10-23)
`/ask metals: how tight is copper and is the LME backwardation explained by stocks?`
1. **Route.** Code routes the question to the `metals` specialist (copper), with question types balance and curve.
2. **Pack.** `specialist pack metals` builds 43 numbered figures:
   - prices, CFTC and CTA levels, and the narrative check;
   - LME and SHFE stocks with their surprises, and the stock-report base rates;
   - the storage group (raw spread 1.016%; 2.037% net of interest, 98th percentile; visible stocks 43rd percentile; inventory-implied 0.308%; gap 1.73 pp, 99th percentile of the fit's residuals);
   - the PMI-day ratio, the COMEX–LME premium, and the long-run real price.
3. **Card.** The specialist wrote the card (`cards/copper/2026-10-23-metals.json`). Code validated every number against its cited source, and the answer passed the auditor (16 matched, 0 orphans).
4. **Reading (inference, labelled).** The LME curve is far tighter than visible stocks explain. Candidates, none measured here: metal pulled into COMEX sheds, bonded or off-exchange stocks, or a concentrated warrant holding.

Full results and the review: `docs/project/notes-A17.md`.

## 6. Sources (registry)
Rows added to `knowledge/sources.md`: SHFE weekly stocks, LME aluminium (Westmetall), IMF metals via FRED, World Bank Pink Sheet, NBS release calendar, plus the four failed checks.
