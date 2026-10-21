---
title: AI compute-demand signals — sources and evidence
agent: morning-note input (AI narrative: applications, cloud compute, data centres)
date: 2026-10-21
status: probed and built; code in pmstack/ai_signals.py + adapters (getdeploying, akash, dramexchange, openrouter, ramp, census_c30, tsmc, kcs), parameters in config/ai_signals.yaml and config/sources.d/ai_signals.yaml
---

# AI compute-demand signals — sources and evidence

**Answer.** Eight of the ten sources Bernardo's other AI monitor uses are free and readable. They now feed a
descriptive **"AI demand signals"** section of the fact pack. Each signal is tagged to the AI narrative's part it bears on:
- **applications**: OpenRouter tokens, Ramp AI Index;
- **cloud compute**: GPU rental prices from GetDeploying, Akash utilisation and prices;
- **data centres**: Census data-centre construction, TSMC monthly revenue, Korean chip exports, DRAM spot.

Two sources were skipped:
- **Silicon Data**: the indices need its paid API or portal, and its terms bar copying;
- **Taiwan MOF exports**: the site timed out; TSMC revenue covers the same leg.

OpenRouter is built but waits for a free API key (secret `OPENROUTER_API_KEY`).

The evidence that these series *predict* anything about AI capex or AI equities is thin. It is mostly practitioner
commentary, with no tested lead-lag. So the section has **no thresholds and no alerts**, and every "what up means"
line is labelled inference. A signal would need a registered study in the research loop (agent 12) before it could
be anything more than context.

Method: probes from Bernardo's PC on 21 Oct 2026. Each probe recorded the HTTP status, format, key or login, terms,
update frequency and history, followed by a live parse of every source. Eight web searches covered the literature.
Labels used below: "abstract" = only the abstract read; "secondary" = someone else's summary; "page" = the source's
own page read.

## 1. What each signal has been shown to say

| Finding | What it changes | Source |
|---|---|---|
| AI-related investment was a large share of US GDP growth in 2025. The St. Louis Fed splits it into information-processing equipment, software, R&D and **data-centre construction** (data centres were the smallest piece, a few hundredths of a pp a quarter). Furman put equipment + software at ~92% of H1 2025 growth. Goldman argues the net contribution was near zero, because most AI hardware is imported. | Data-centre construction (Census) is the slowest and smallest leg of the build-out. Chips (TSMC, Korea) and equipment carry most of the spending, so the section shows all of them, not construction alone. | St. Louis Fed, "Tracking AI's Contribution to GDP Growth", On the Economy, Jan 2026 (secondary: search snippets); Richmond Fed Econ Focus 2026 Q1–Q2 (secondary); Goldman via Gizmodo (secondary) |
| Census has published **data centres as their own private construction category since mid-2024**; before that they sat inside Office. The category comes from the Construction Progress Reporting Survey and is revised for months. | Use the SAAR series from the time-series workbook. Show the date as the reference month and count it from ~2 months after. Treat the last two prints as revisable (the adapter keeps the latest fetch). | Census C30 workbook `privsatime.xlsx` (page, column "Data center", Jan 2014 →); Our World in Data indicator notes (secondary) |
| Korea's 10- and 20-day customs prints are the first hard trade data each month, and chips are ~45% of Korean exports in 2026. Markets read them as a proxy for the **semiconductor and memory cycle**. Economists warn they are partial, depend on working days and are revised. | Show the chip figure **like-for-like**: a 1–20 print against last month's 1–20. Show the y/y KCS publishes beside it, and keep the window in the series name. Keep the first-published value. No signal claims. | KCS releases (page + PDF, 21 Oct 2026); news coverage of the "canary" framing (secondary: AJOT, Panjiva). No peer-reviewed lead-lag study found |
| TSMC makes nearly all leading AI accelerators. Its monthly revenue arrives about 3 weeks before the quarter's results. It also carries phones and PCs and is in NT$. | Show it as data-centre hardware, with a "NT$-sensitive, not only AI" reading note. Compare it vs the previous month and the same month a year ago (seasonality is strong: no 4-week window). | TSMC IR monthly revenue pages (page) |
| GPU rental prices fell sharply as H100 supply caught up (2024–25), then **turned up during 2026**. Commentators read rising old-chip prices and full utilisation as demand ahead of supply, and falling rentals with idle capacity as a glut. Trackers disagree on the level by 2x: on-demand vs committed vs marketplace, and provider mix. | Use **one consistent methodology** (GetDeploying: each provider's median, then the median across providers, on demand) and show changes, not levels against other trackers. Add the provider count (coverage changes move a median) and an old-generation chip (A100) as the "all vintages absorbed" check. | GetDeploying methodology (page: 57,799 weekly observations since Jul 2024, 88 providers); Silicon Data blog posts on H100 price moves (secondary); UOB "Compute is revenue" (secondary: summary only); Latent Space "$2 H100s" (secondary) |
| Akash is a decentralised marketplace with a few hundred GPUs and a handful of providers per model. | Colour only. The utilisation history goes back to Feb 2024; the prices are snapshots whose history starts with our own fetches. Never cited alone. | Akash console API (page) |
| AI servers pulled DRAM capacity toward HBM and server DDR5. Hyperscalers bought more DDR5 than expected in late 2025 and a shortage followed. TrendForce expected the HBM3e/DDR5 price ratio to narrow from 4–5x to 1–2x by end-2026. | DDR5 spot plus a server RDIMM module are the free, daily read on memory tightness. Spot is a thin retail market that leads contract but is not what hyperscalers pay. DDR4 is kept as the "legacy capacity squeezed" contrast. | TrendForce press notes Dec 2025 / Jan 2026 (secondary: EE Times Asia, TrendForce listings) |
| OpenRouter routed >100 trillion tokens a year by mid-2025, but its mix is skewed: roleplay is over half of open-weight use, enterprise use is thin, and one account once moved the metrics by 20 points. | Tokens per day as a **7-day mean** (weekday noise), plus the top model's share as a concentration check. Read it as developer/agent demand on one router, not the market. | a16z + OpenRouter, "State of AI: an empirical 100 trillion token study", Dec 2025, arXiv 2601.10088 (secondary: a16z post, Implicator critique) |
| Card and bill-pay data give a monthly, firm-level read on paid AI adoption. Survey measures are far lower: the Census BTOS showed ~5% of firms using AI in early 2024, against ~30–31% of Ramp's firms paying for AI in Jan–Mar 2024 (Ramp page data). The wording and the sample drive the level. | Show the Ramp **changes** (pp vs previous month, 3 months, 1 year), not the level as "the adoption rate". Vendor lines are share, not total demand. | Ramp AI Index methodology (page: 85,000+ firms); Bonney et al. 2024, NBER WP 32319 / CES-WP-24-16 (abstract) |

## 2. Source probe (21 Oct 2026)

| Source | Measures | Access | Licence / terms | Frequency, history | Verdict |
|---|---|---|---|---|---|
| **GetDeploying** GPU price dataset | On-demand $/GPU-hr per model, median of providers | `https://getdeploying.com/dataset/gpu-prices/weekly.csv` HTTP 200, CSV, no key | **CC BY 4.0** (cite GetDeploying) | Weekly (latest week partial), updated daily; 53 trailing weeks per model | **Wired** (`ai_gpu_gd`: H100, H200, B200, B300, GB200, A100, MI300X) |
| **Akash** console API | Network GPU utilisation; per-model price and availability | `console-api.akash.network/v1/gpu-prices`, `/graph-data/gpuUtilization`, JSON 200, no key | Public API, no stated licence | Utilisation daily since Feb 2024; prices are snapshots | **Wired** (`ai_gpu_akash`), colour only |
| **Silicon Data** (SDH100RT, H200, B200 indices) | Standardised rental indices | Product pages 200, but "daily readings are temporarily unavailable"; chart is a client-side portal; API (docs.silicondata.com) needs a paid key | Terms: no copying, distributing or framing without consent; personal download only, unmodified. Indices are also distributed on Bloomberg/Refinitiv | Daily | **Skipped**: no free machine-readable reading. GetDeploying covers the same question |
| **DRAMeXchange** | DDR5/DDR4 chip spot (daily), DDR5 RDIMM module spot (weekly), session average | Home page 200, HTML table; history needs a TrendForce membership | Terms forbid reproduction or distribution without consent | Daily (Taiwan business days); no free history | **Wired, personal use only** (`ai_dram`), like Yahoo: one number per item per day for Bernardo's note, never in a public post. The repo is private (Bernardo confirmed 21 Oct 2026: OK to use); data/ is committed there, never copied to a public post or repo |
| **OpenRouter** Data API, rankings-daily | Tokens per day, top 50 models + "other" | `openrouter.ai/api/v1/datasets/rankings-daily`; 401 without a key; any free OpenRouter key works; 30 req/min, 500/day | **CC BY 4.0** ("Source: OpenRouter (openrouter.ai/rankings), as of <meta.as_of>") | Daily, from 2025-01-01, ≤366 days per call | **Wired, waiting for a key** (`ai_tokens_or`, status "skipped" until the `OPENROUTER_API_KEY` secret is set; daily.yml passes it) |
| **Ramp AI Index** | Share of US businesses paying for AI; AI share of spend; per vendor | `ramp.com/data/ai-index` 200 (11 MB page); data embedded in the Next.js payload; no key; robots allows `/data/` | Public page, media kit offered; no data licence stated: cite "Ramp AI Index" | Monthly, mid-month for the prior month; since Jul 2023 | **Wired** (`ai_ramp`). Brittle: a page redesign breaks the parse (logged as an error) |
| **US Census C30** construction spending | Private SAAR by type: data centres, electric power, nonresidential | `census.gov/construction/c30/xlsx/privsatime.xlsx` 200, no key. The Census API (`eits/vip`) now answers "Missing Key", the file does not | Public domain | Monthly, ~1st business day of M+2; data centres since Jan 2014 | **Wired** (`ai_census_dc`; xlsx parsed with the standard library) |
| **TSMC** monthly revenue | Consolidated net revenue, NT$ mn, and y/y | `investor.tsmc.com/english/monthly-revenue/<year>` 200, HTML table; no key | Public IR disclosure | Monthly, ~10th of M+1; pages from 1999 | **Wired** (`ai_tsmc`, from 2022) |
| **Korea Customs** (관세청) 10/20-day and monthly releases | Exports, chip exports ($, y/y, share) | Press board `customs.go.kr/kcs/na/ntt/selectNttList.do?mi=2891&bbsId=1362` 200; release page by POST; PDF attachment (needs the session cookie and a Referer); server drops connections now and then (retried) | **KOGL type 1** (공공누리 출처표시): free reuse with attribution | 1–10 (~11th), 1–20 (~21st), monthly final (~15th); board pages go back years | **Wired** (`ai_kcs`). The 1st-of-month preliminary is skipped: KCS's version states no chip figure (MOTIE's joint release has it, in another format). When the release text omits the chip $ figure, it is computed from share × total and marked "derived" |
| **Taiwan MOF** export releases | ICT and electronic-component exports | `mof.gov.tw/Eng` answered once, then timed out at the TLS handshake; `portal.sw.nat.gov.tw` timed out | Government open data | Monthly, ~7th–9th | **Skipped for now**: unreachable from this PC. Retry later or use data.gov.tw. TSMC revenue covers the Taiwan AI-hardware leg |

### Access from GitHub Actions
- **All sources were reached from Bernardo's PC only.** Runner access is unverified until the first data-job run after the merge.
- **Likely to block cloud IPs:** the browser-like pages (Ramp, DRAMeXchange, TSMC) and the Korea Customs board. Google News already answers 503 to runners.
- **Unlikely to block:** the APIs and files (GetDeploying CSV, Akash, OpenRouter, Census xlsx).
- **Failure is contained:** every block has `budget_s` and `timeout_s`. An adapter error is logged as that source's error, and the next source runs.
- **What a blocked source does to the pack:** the section shows the last stored value with its date, and adds "(stale)" once it is older than its frequency allows.

## 3. Design (what was built and why)
- **Part tags** come from config. Each signal belongs to one part: applications, cloud compute or data centres. The note judges each part bullish or bearish in its own words; the pack only supplies numbers.
- **Comparisons** for each signal:
  - vs the previous print;
  - vs the print nearest 4 weeks, 3 months and 1 year earlier (within a frequency tolerance);
  - % change for prices and amounts, pp for series already in %.
  - Monthly series skip the 4-week window. Korean prints compare only with the previous print of the same kind.
- **Point in time.** Monthly series are dated at the reference month and count only from date + `lag_days`: TSMC 40, Ramp 45, Census 61, OpenRouter 1. A pack rebuilt for an earlier date never shows a later release.
- **Display.** Tokens are a 7-day mean in trillions; Census is shown in $bn SAAR, TSMC in NT$ bn.
- **No alerts.** `build()` always returns an empty alert list; a test pins this.
- **What to do before promoting any signal:** register a study in `research/studies/` with base rate, lift, placebo and BH. Candidates:
  - Korean chip-export y/y turns vs SOX drawdowns;
  - H100 rental 3-month change vs hyperscaler capex revisions.

## Sources
- GetDeploying, GPU price trends and dataset (CC BY 4.0): https://getdeploying.com/gpu-price-trends, https://getdeploying.com/dataset/gpu-prices
- Akash console API: https://console-api.akash.network/v1/gpu-prices
- Silicon Data H100 index page and terms: https://www.silicondata.com/products/silicon-index/h100, https://www.silicondata.com/terms-of-use
- DRAMeXchange home and terms: https://www.dramexchange.com/, https://www.dramexchange.com/About/TermsOfUse
- OpenRouter Data API (licence, limits): https://openrouter.ai/docs/cookbook/administration/data-api
- Ramp AI Index: https://ramp.com/data/ai-index
- Census construction spending, historical data: https://www.census.gov/construction/c30/historical_data.html
- TSMC monthly revenue: https://investor.tsmc.com/english/monthly-revenue
- Korea Customs Service press releases: https://www.customs.go.kr/kcs/na/ntt/selectNttList.do?mi=2891&bbsId=1362
- St. Louis Fed, Tracking AI's Contribution to GDP Growth (Jan 2026): https://www.stlouisfed.org/on-the-economy/2026/jan/tracking-ai-contribution-gdp-growth
- Richmond Fed Econ Focus 2026 Q1–Q2: https://www.richmondfed.org/publications/research/econ_focus/2026/q1-q2_feature2
- Bonney et al., Tracking Firm Use of AI in Real Time (NBER WP 32319): https://www.nber.org/papers/w32319
- a16z + OpenRouter, State of AI (100T tokens): https://www.a16z.com/state-of-ai ; critique: https://www.implicator.ai/the-100-trillion-token-mirage-what-openrouters-ai-report-actually-reveals/
- TrendForce on DDR5 capacity crowding (via EE Times Asia): https://www.eetasia.com/trendforce-higher-ddr5-profitability-intensifies-capacity-crowding/
- Korea as a "canary" for trade (secondary): https://panjiva.com/research/south-koreas-the-canary-in-the-coal-mine-for-global-trade-slowdown/24227
- GPU rental price commentary (secondary): https://latent.space/p/gpu-bubble, https://www.uob.com.sg/assets/web-resources/private/pdfs/compute-is-revenue.pdf
