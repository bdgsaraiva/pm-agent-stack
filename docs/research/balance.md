---
title: Balance keeper — literature review
agent: 9 (balance keeper)
date: 2026-10-16
status: reviewed before build; code in pmstack/balance.py + adapters (wasde, usda_psd, nass; eia reused), parameters in config/balance.yaml and config/sources.d/balance.yaml
docs: (Docs page pending: see notes-A12)
---

# Balance keeper — literature review

**Answer.** Build the balance keeper as a **descriptive** engine. It states where oil inventories and grain stocks-to-use sit against a *trailing* norm, and how far each new report moved against an expectation code can build from free data. It never forecasts a price or calls a market bullish or bearish.

The theory of storage and its tests agree on the core:
- low inventories go with backwardation, a higher basis and higher volatility, and the effect is non-linear (Working; Gorton, Hayashi & Rouwenhorst; Symeonidis et al.);
- so stocks are shown as level vs norm, as a position in the range, and as "below/above the 5-year range", not only as a z-score.

The same literature warns against reading those numbers naively:
- oil inventories mostly carry precautionary demand and supply smoothing, not flow demand (Kilian & Murphy);
- the academic "normal" inventory is a two-sided filter that looks ahead (GHR's HP trend);
- no free consensus exists for EIA or USDA, and naive surprises are noisier and bias any price response toward zero (Halova et al.);
- USDA reports keep their news value (Karali et al. 2019), but the market absorbs them within minutes (Adjemian & Irwin 2018).

So the value is **context at decision time** (fact pack, critic), not speed. Scarce and worth building: one audited table across oil and grains, with WASDE as first published, surprises shown beside USDA's own historical error, and links into the critic. Not worth building: satellite tank data (Kpler, Vortexa) and EIA's or USDA's own charts.

Method: two research passes on 16 Oct 2026 (papers; data and practice), ~80 pages opened, plus a local check of the WASDE files. "Abstract" = only the abstract read; "secondary" = someone else's summary. Book points not page-checked are marked.

## 1. Papers: storage, inventories, curve, stocks-to-use

| Finding | What it changes | Source |
|---|---|---|
| Cost of carry with a convenience yield; the convenience yield falls at a decreasing rate as stocks rise (supply-of-storage curve). | Stocks are read with the curve, on a non-linear scale. The curve is a known gap: the store has front months only. | Kaldor 1939; Working 1949; Brennan 1958 (secondary, via GHR and Symeonidis) |
| 31 commodities, 1969–2006: the convenience yield is a decreasing, non-linear function of inventories. In low-inventory months the basis is above average for every commodity. | The core quantity is inventory relative to normal. | Gorton, Hayashi & Rouwenhorst 2007/2013 (read, NBER) |
| GHR's "normal" inventory is an HP trend, a two-sided filter that uses future data. | **No two-sided filters.** The norm is the same week of the prior five years, using only what was public on the as-of date. | GHR §3 fn. 8 (read) |
| Inventories are persistent (de-seasonalised autocorrelation > 0.9); seasonality differs by commodity. | Levels move slowly; the weekly news is the change against the 5-year same-week change (already in the monitor). | GHR §3 (read) |
| Low-inventory portfolio beat high by 8.06% a year (t = 3.19), 1969–2006. | A return claim is a **signal** and goes through the quant gate. The keeper does not make it. | GHR §4.2 (read) |
| 21 commodities 1993–2011: low inventory goes with backwardation; crude has the largest basis coefficient (1% deviation ↔ 0.67% on the 6-month basis). No seasonality in monthly crude stocks. | Test seasonality per series rather than assume it. A curve–stocks mismatch is "to investigate" (inference). | Symeonidis, Prokopczuk, Brooks & Lazar 2012 (read, MPRA) |
| A storage model with a non-negativity constraint gives skewed prices and rare violent spikes. | Tight states are asymmetric: show the position in the range and "below the 5-year low" explicitly. | Deaton & Laroque 1992 (abstract) |
| World stocks-to-use excluding China vs detrended real price: −0.40 (wheat), −0.50 (maize); stocks data "unreliable" but useful with prices. | World **ex-China** stocks-to-use beside world and US. Labelled uncertain; a vulnerability indicator, not a forecast. | Bobenrieth, Wright & Zeng 2013 (slides read) |
| Corn price = a + b/stocks-to-use: 86% of variation within 2007/08–2014/15; the curve shifted after 2006 (ethanol). US stocks-to-use beats world for US prices. | Stocks-to-use **percentile since 2007/08**, US first, world beside it. No price mapping. | Good & Irwin 2015; Irwin & Good 2016, farmdoc daily (read) |
| Tight old-crop stocks failed to lift prices in 2013/14, 2020/21 and 2024/25 because a big new crop was expected. | **New-crop stocks-to-use beside old-crop**, always. | Janzen 2025, farmdoc daily (read) |

## 2. Papers: oil shocks and the weekly report

| Finding | What it changes | Source |
|---|---|---|
| Oil shocks come from supply, aggregate demand and oil-specific (precautionary) demand, with different effects. | A draw does not identify the shock: any attribution is labelled inference. | Kilian 2009 (abstract) |
| Short run: 29% of inventory variation is speculative demand and 26% supply shocks; long run: 87% of real price variation is flow demand. | "Build = bearish" is not a law. The keeper describes; the critic asks why. | Kilian & Murphy 2014 (read, WP) |
| A VAR with inventories beats no-change at 1–3 months only; global inventory data lag ~5 months. | Real-time vintages only. The keeper makes no forecast. | Alquist, Kilian & Vigfusson 2011 (read) |
| Measured surprises contain error; corrected price responses are ~2× OLS for petroleum. | Report surprise sizes; **never derive a sensitivity** from naive surprises. | Halova, Kurov & Kucher 2014 (abstract) |
| The Bloomberg survey's s.d. (1.62 mb) is half the actual change's (3.47 mb); futures move the day before, with the coming surprise. | Name surprises "vs the 5-year same-week change", never "vs consensus". Wednesday's reaction understates the information (API on Tuesday). | Miao, Ramchander, Wang & Yang (read, JFM revision) |
| Markets weight analyst forecasts beyond statistical models. | A code expectation is inferior to a consensus: the label says what it is. | Gay, Simkins & Turac 2009 (abstract) |
| EIA's 5-year range = high and low of the **same week over the prior five years**, current year excluded. Weekly stocks are the most accurate weekly variable; the crude "adjustment" is the balancing line. | Replicate EIA's definition exactly (`norm_years: 5`). Track the adjustment as a data-quality flag. | EIA WPSR Appendix B (read) |
| From 21 Oct 2026 WPSR Tables 11, 12, 14 and the appendices are discontinued. | Use API series ids only (stable); re-test the EIA adapter after 21 Oct. | EIA WPSR page, 16 Oct 2026 (read) |
| Weekly exports were understated by 16% in H1 2016; distillate seasonality broke after 2008. | Flows are 4-week averages; norms come from a recent 5-year window. | EIA Today in Energy 2016, 2017 (read) |
| Days of supply = stocks / 4-week product supplied (ignores supply). | Use EIA's own days-of-supply series, with the caveat. | EIA Today in Energy 2022 (read) |
| The crude adjustment includes "transfers to crude oil supply" since Nov 2023. | Its band is computed on post-break data only (`break_date`). | EIA notes (secondary) |
| STEO quantities: 12-month production MAPE 5–7%; prices 25–35%. | STEO quantities are a usable free expectation (v2); prices are not. | Agovic 2026 (read) |

## 3. Papers: USDA reports

| Finding | What it changes | Source |
|---|---|---|
| WASDE price effects are larger in Crop Production months and **when stocks are low**. | Each revision is shown with the stocks-to-use percentile beside it. | Adjemian 2012 (secondary: ERS summary) |
| Surprise sizes have not shrunk, and price reactions have grown. | USDA reports stay worth tracking. | Karali et al. 2019 (abstract) |
| Volatility spikes on reports fade within minutes (2009–2014). | No speed edge: context for the 06:18 note, not timing. | Adjemian & Irwin 2018 (abstract) |
| Crop condition moves corn and soy most in July–August, and the reactions have grown. | Condition changes alert only in key months (`key_months: [7, 8]`). | Lehecka 2014 (abstract) |
| Condition-implied yield: SE 4.6 bu at the end of the season, 9.3 bu in late June. | A free yield expectation for v2; near-useless in June. | Irwin & Hubbs 2018 (read) |
| WAOB May–July trend yield: mean absolute error 5.98% (May); large misses in drought years. | The previous USDA number is the expectation; USDA's own error is the scale. | Irwin, Good & Sanders 2015 (read) |
| USDA revisions are smoothed (small crops get smaller, big get bigger). | A "revision continuation" reading is inference and goes to the quant gate. | Isengildina, Irwin & Good 2004/06 (read) |
| Grain Stocks surprises are best read as % of implied use; NASS's relative standard error for 1 Sep is 4.4% (corn), 7.1% (soy). | v2: stocks vs WASDE-implied stocks. v1: stocks vs year ago and the 5-year same quarter. | Irwin, Good & Sanders 2016 (read) |
| Most studies find USDA forecasts biased or inefficient, yet newsworthy. | Store every vintage. The WASDE CSV keeps **values as first published**. | Sanginabadi 2017 meta-analysis (read) |

## 4. Data and practice

| Finding | What it changes | Source |
|---|---|---|
| **WASDE CSV**: one file per report (`oce-wasde-report-data-YYYY-MM.csv`), values as first published, 16 columns. Each file carries USDA's **reliability table** for that month (average and largest miss vs final, RMSE %, years above/below). www.usda.gov answered some clients with 403; the `usda.azureedge.us` mirror serves the same files. | Adapter `wasde`: no key, a vintage store. Revisions are shown beside USDA's own average miss, converted to bushels where the table is in metric tons. Fallback to the mirror. | USDA OCE Historical WASDE Report Data (read; local check 16 Oct: Aug–Oct 2026 files, 4,353 rows) |
| The same files carry **World** and **World Less China** lines for corn, soybeans and wheat. | World and world ex-China stocks-to-use straight from WASDE, first published. PSD is needed only for world sugar and long histories. | Local check of the Oct 2026 file |
| FAS OpenData PSD: header `API_KEY`; world/country by commodity and year. Codes: corn 0440000, wheat 0410000, soybeans 2222000, sugar 0612000. The swagger has no response models. | Adapter `usda_psd` with loose field matching; `balance probe` prints what came back on the first live run. | FAS swagger (read); FAS PSD code table (read) |
| NASS Quick Stats: `key`, `short_desc`, `agg_level_desc=NATIONAL`, 50,000-row cap; required notice "not endorsed or certified by NASS". Crop Progress is Monday 16:00 ET; Grain Stocks dates are in the 2026 schedule. | Adapter `nass`. Every value is dated **when it became public**, not at its reference date. The notice goes under the section. | NASS API page; 2026 PFEI schedule (read) |
| EIA: the WPSR is out Wednesday 10:30 ET (Thursday 12:00 ET after a Monday holiday). API v2 `seriesid` route, 5,000 rows a call; public domain with credit. | EIA week ending Friday is available from the Thursday pack (`available_lag_days.eia: 6`). New series ids are in `config/sources.d/balance.yaml`. | EIA schedule, API docs, Weekly Supply Estimates (read) |
| API's weekly bulletin and the Reuters/Bloomberg polls are paid and licensed. No free consensus exists. | The expectation is code-built and labelled as such. | API WSB page (read) |

## 5. Atlas investors and books
- **Andurand**: fundamentals and imbalances are his edge, but a political event (the April ceasefire) wiped out the trade. → Balances are context; the critic asks what removes the imbalance overnight.
- **Andy Hall**: "being early is indistinguishable from being wrong". → v2: how long a stated imbalance has failed to show up in stocks.
- **Doug King**: supply responds to price; commodities refuse to trend forever. → Positioning (CFTC) sits beside balances on the critic card.
- **Kovner**: know what is already priced. → Surprises are measured against an expectation, and the label says it is not a consensus.
- **Paul Tudor Jones**: price before the story. → Balance facts never override price or the risk agent.
- Books (general knowledge, not page-checked):
  - Williams & Wright, *Storage and Commodity Markets*: the storage model, with price convex in stocks;
  - Tomek & Kaiser, *Agricultural Product Prices*: the reciprocal stocks-to-use form;
  - Geman, *Commodities and Commodity Derivatives*: convenience yield;
  - Downey, *Oil 101*: how balances are read;
  - Pirrong, *The Economics of Commodity Trading Firms*: inventories and spreads drive physical trade.

## 6. Where sources disagree, and the resolution
1. **Is crude seasonal?** Symeonidis finds no seasonality in monthly crude stocks, while EIA and GHR show strong seasonality in products. → Same-week norms for all (the EIA convention), with the z-score beside them. A per-series seasonality test is a v2 item.
2. **What is "normal"?** GHR use an HP trend (two-sided), Ye et al. a trend plus dummies, the industry the prior-5-year range. → The EIA 5-year convention, because it is computable in real time and it is what the market reads.
3. **Does stocks-to-use set price?** Yes within a regime (Good & Irwin), but the curve shifts, and fails when the next crop dominates (Janzen). → Percentile since 2007/08, new crop beside old crop, no price mapping.
4. **Survey vs naive expectations.** Analysts beat models (Gay et al.), yet the survey explains little of the weekly variance (Miao et al.). → Naive surprises, named honestly, never turned into sensitivities.
5. **Are reports still news?** Older work says their effect diminished; newer, broader evidence (Karali et al.) says reactions grew. → Track the revisions; the critic shows them as context.

## 7. Design vs the plan's spec
- **Scope v1** (Bernardo, 16 Oct): oil and grains, with corn, soybeans, wheat and sugar.
  - **Oil:** EIA's full weekly balance (stocks, implied demand, runs, net imports, days of supply, adjustment).
  - **Grains and sugar:** WASDE as first published plus PSD history and world sugar.
  - **Crops:** NASS crop condition and quarterly stocks.
- **Output** (Bernardo): a "Balances" section in the daily fact pack plus `bal.*` facts on the critic card. A balance that leans against an idea (stocks ≥ 1 sd above the 5-year same-week average for a long, ≤ −1 sd for a short; or a stocks-to-use percentile ≥ 80 / ≤ 20) becomes a counter-question basis at severity 1.4. That is below trend and crowding, as context.
- **Alerts** (realised, dated, fresh within 7 days):
  - a key stock outside its 5-year same-week range with |z| ≥ 2;
  - a WASDE ending-stocks revision of at least USDA's average miss for that month;
  - a crop-condition change of ≥ 5 points in July–August.
- **No look-ahead:** every number is used from its availability date (EIA week + 6 days; WASDE, NASS and PSD the day after release). NASS stocks are dated at their release, never their reference date.
- **Not built (v2, or vendor):**
  - STEO quantities as a monthly expectation;
  - ESR export sales pace;
  - Grain Stocks vs WASDE-implied stocks;
  - condition-implied yield;
  - curve spreads (no free back months);
  - time-to-confirmation of a stated imbalance;
  - satellite inventories (vendor; not scarce).

## 8. How it works, with a worked example (local run, 16 Oct 2026, EIA history in the repo + WASDE files)
1. `fetch` (GitHub Actions) stores the new series:
   - `eia_bal`;
   - `wasde` (2021 → today, one CSV per report);
   - `usda_psd` (from 2007/08);
   - `nass`.
2. `monitor.build` calls `balance.build(asof)`, which loads only what was public on the as-of date.
3. **Oil:** US distillate stocks for the week ending 2026-10-09 were 102,611 kbbl:
   - 11.1% under their 2021–2025 same-week average, at −1.9 sd;
   - below the 2021–2025 same-week range (low 106,187).
   The section shows it as "(below)"; |z| < 2, so no alert. A long HO=F idea would get `bal.stock_vs_5y_pct` and `bal.stock_z` on its critic card, but no counter (tight stocks agree with a long).
4. **Grains:** the 9 Oct WASDE put 2026/27 US corn ending stocks at 1,849 million bushels:
   - +282 vs the 11 Sep report;
   - USDA's average miss for an October projection is 331, so it is not an alert;
   - stocks-to-use 11.3%, against 12.7% for 2025/26;
   - world and world ex-China 21.2% / 11.6% (WASDE).
5. **The morning note** (other session) may quote any of these, audited against facts.json. A reading such as "distillate tight into winter" is labelled inference.

## 9. Sources
Kaldor 1939; Working 1949; Brennan 1958 (secondary) · Fama & French 1987 https://ideas.repec.org/a/ucp/jnlbus/v60y1987i1p55-73.html · Deaton & Laroque 1992 https://ideas.repec.org/a/oup/restud/v59y1992i1p1-23..html · Gorton, Hayashi & Rouwenhorst https://www.nber.org/papers/w13249 · Symeonidis et al. 2012 https://mpra.ub.uni-muenchen.de/39903/1/MPRA_paper_39903.pdf · Brennan, Williams & Wright 1997 https://ideas.repec.org/a/ecj/econjl/v107y1997i443p1009-22.html · Bobenrieth, Wright & Zeng 2013 https://www.fields.utoronto.ca/programs/scientific/13-14/envirofinance/riskmgt/Bobenrieth.pdf · Westcott & Hoffman 1999 https://ers.usda.gov/publications/47277 · Good & Irwin 2015 https://farmdocdaily.illinois.edu/2015/04/relationship-stock-to-use-and-corn-prices.html · Irwin & Good 2016 https://farmdocdaily.illinois.edu/?p=11370 · Janzen 2025 https://farmdocdaily.illinois.edu/2025/07/the-corn-market-works-to-explain-itself.html · Kilian 2009 https://www.aeaweb.org/articles?id=10.1257/aer.99.3.1053 · Kilian & Murphy https://www.frbsf.org/Kilian_Role-of-Inventories-and-Speculative-Trading.pdf · Alquist, Kilian & Vigfusson 2011 https://www.federalreserve.gov/pubs/ifdp/2011/1022/ifdp1022.pdf · Ye, Zyren & Shore 2002 https://www.eia.gov/petroleum/archive/crudeforecast1.pdf · Halova, Kurov & Kucher 2014 https://ideas.repec.org/a/wly/jfutmk/v34y2014i10p911-933.html · Miao et al. https://api.mountainscholar.org/server/api/core/bitstreams/9938aa1b-96a3-466b-ac76-7710737b5b72/content · Bu 2014 https://buaa.globalimpact.cn/en/publications/effect-of-inventory-announcements-on-crude-oil-price-volatility/ · Gay, Simkins & Turac 2009 https://ideas.repec.org/a/wly/jfutmk/v29y2009i5p451-477.html · EIA WPSR Appendix B https://www.eia.gov/petroleum/supply/weekly/pdf/appendixb.pdf · EIA WPSR https://www.eia.gov/petroleum/supply/weekly/ · EIA schedule https://www.eia.gov/petroleum/supply/weekly/schedule.php · EIA API docs https://www.eia.gov/opendata/documentation.php · EIA Weekly Supply Estimates https://www.eia.gov/dnav/pet/pet_sum_sndw_dcus_nus_w.htm · EIA TIE 2015 https://www.eia.gov/todayinenergy/detail.php?id=21472 · 2016 https://www.eia.gov/todayinenergy/detail.php?id=27752 · 2017 https://www.eia.gov/todayinenergy/detail.php?id=32732 · 2022 https://www.eia.gov/todayinEnergy/detail.php?id=54619 · Agovic 2026 https://odr.chalmers.se/bitstreams/93a5cc61-7247-4d98-911e-32c30ddb9088/download · Adjemian 2012 https://www.ers.usda.gov/amber-waves/2012/june/wasde · Isengildina-Massa et al. 2008 https://ideas.repec.org/a/wly/agribz/v24y2008i4p473-490.html · Karali et al. 2019 https://ideas.repec.org/a/eee/jfpoli/v84y2019icp66-76.html · Adjemian & Irwin 2018 https://ideas.repec.org/a/oup/ajagec/v100y2018i4p1151-1171..html · Lehecka 2013 https://ideas.repec.org/p/ags/saea13/142491.html · Irwin, Good & Sanders 2015 https://farmdocdaily.illinois.edu/2015/04/understanding-and-evaluating-waob-usda-corn.html · Irwin & Hubbs 2018 https://farmdocdaily.illinois.edu/2018/06/measuring-the-accuracy-of-forecasting-corn-and-soybean-yield.html · Isengildina, Irwin & Good 2004 https://farmdoc.illinois.edu/assets/meetings/nccc134/conf_2004/pdf/confp04-04.pdf · Egelkraut et al. 2002 https://farmdoc.illinois.edu/assets/meetings/nccc134/conf_2002/pdf/confp02-02.pdf · Irwin, Good & Sanders 2016 https://farmdocdaily.illinois.edu/2016/07/revisiting-usda-corn-and-soybean-grain-stocks.html · Sanginabadi 2017 https://arxiv.org/pdf/1801.06575 · Tang & Xiong 2012 https://www.nber.org/papers/w16385 · Hamilton & Wu 2014 https://econweb.ucsd.edu/~jhamilto/commodity_index.pdf · Szymanowska et al. 2014 https://ideas.repec.org/a/bla/jfinan/v69y2014i1p453-482.html · WASDE data https://usda.azureedge.us/node/42884 · FAS OpenData https://apps.fas.usda.gov/OpenData/swagger/docs/v1 · NASS Quick Stats API https://quickstats.nass.usda.gov/api · NASS 2026 schedule https://data.nass.usda.gov/Publications/2026-NASS-PFEI-Schedule.pdf · API WSB https://www.api.org/energy-insights/statistics/wsb · Kpler https://www.kpler.com/product/commodities/inventories-analytics · Atlas cards: Andurand, Hall, King, Kovner, Tudor Jones.
