# Risk and crowding — 2026-10-30

## Risk and crowding (descriptive; in paper R)

Risk model: daily log returns of front-month closes (Yahoo continuous contracts, roll gaps not adjusted) spliced with spot/index proxies where a contract has no close (flagged). Current vol = EWMA 0.94; calm correlation = last 250 days; stress correlation = the top-20% turbulence days of the whole history; both shrunk toward constant correlation (Ledoit & Wolf).
Model window 2003-12-02 to 2026-10-30; 1123 stress days; shrinkage calm 0.07, stress 0.02.

**Market state:** turbulence percentile 92 of the last 756 days (2026-10-30); 1 of the last 5 days in the top 20%. HY OAS 3.26% (2026-10-29), +14bp over 21 observations ([FRED](https://fred.stlouisfed.org/series/BAMLH0A0HYM2)). VIX 19.4, percentile 60 since 1990-01-02 (2026-10-30). Funding not stressing.

**Book:** 2 ideas, 1.8 effective independent ideas (stress matrix). Daily sd 0.26R calm, 0.72R stress. Open -0.21R; -1.29R more if every stop is hit. Book -1.42R from its 10-day high; -1.42R over 60 days (closed R + open marks; sizing halves at -4.0R).

| Idea | Dir | Size | Last (date) | R now | Stop (daily sd) | 1-sd day (R) | Share of stress risk | Cluster | CFTC pct on side (w/w z; ex-trend pct; report date) | Flags |
|---|---|---:|---|---:|---:|---:|---:|---:|---|---|
| S&P 500 `20261020-1900-s-p-500-long` | long | 1.00 | 7614.75 (2026-10-30) | -0.36 | 4.6 | 0.14 | 32% | 1 | n/a | - |
| Copper COMEX vs LME `20261023-2200-copper-comex-vs-lme-relative` | relative | 0.50 | 100.61 (2026-10-29) | +0.30 | 3.8 | 0.18 | 68% | 2 | n/a | - |

Share of stress risk sums to 100%; a negative share is a hedge. CFTC levels mostly restate past returns (returns lead positions in 10 of 10 markets: Sanders, Irwin & Merrin). Crowding is context; it turns red only when funding is stressing. No crowding or CTA flag alerts unless the research loop (agent 12) rates it supported; its measured verdicts are listed under the CTA table.

**Worst historical windows for today's book** (searched 1986-01-03 to 2026-10-30, 10314 days; FRTB-style: the window in which this book would have lost most; spot/index proxies where a contract had no close; markets with no series that day inferred from those that printed (27% of market-days)).

| Horizon | Window (start close to end close) | Stops honoured (R) | Gapped (R) | Days on proxies | Days inferred | Biggest losers | Moves |
|---:|---|---:|---:|---:|---:|---|---|
| 1d | 2025-07-30 to 2025-07-31 | -5.49 | -5.49 | 0% | 0% | `20261023-2200-copper-comex-vs-lme-relative`, `20261020-1900-s-p-500-long` | rv:20261023-2200-copper-comex-vs-lme-relative -21.6%, ES=F -0.3% |
| 5d | 2025-07-24 to 2025-07-31 | -5.87 | -5.87 | 0% | 0% | `20261023-2200-copper-comex-vs-lme-relative`, `20261020-1900-s-p-500-long` | rv:20261023-2200-copper-comex-vs-lme-relative -23.0%, ES=F -0.4% |
| 20d | 2008-09-12 to 2008-10-10 | -1.75 | -6.08 | 0% | 0% | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | ES=F -29.1%, rv:20261023-2200-copper-comex-vs-lme-relative -2.8% |
| 60d | 2008-08-27 to 2008-11-20 | -1.33 | -8.35 | 0% | 0% | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | ES=F -41.6%, rv:20261023-2200-copper-comex-vs-lme-relative -2.7% |

**What hurts this book most** (reverse stress: average moves on its worst 103 days since 1986-01-03, x 0.85 for fat tails; Glasserman, Kang & Kang): ES=F -2.7%, rv:20261023-2200-copper-comex-vs-lme-relative -3.0% = -1.25R a day. Worst days: 2025-07-31, 1987-10-19, 2009-01-14.

**Episode library** (replayed day by day on today's book; relative moves). Stress P&L in R from today's marks. Replays run day by day: 'stops honoured' exits at the first close beyond the stop (a gap can cost more than 1R); 'gapped' holds to the end. Instantaneous shocks cap honoured losses at the stop. k = plausibility: the scenario's Mahalanobis distance under the stress matrix (scaled to its length), converted to a one-market sd equivalent, so 3 is about as rare as a 3-sd move in one market. Stress tests are not early warnings (Borio et al.).

| Episode | Window | Source | k | Stops honoured (R) | Gapped (R) | Vol-scaled, gapped (R) | Worst inside (R) | Biggest losers | Proxy share | Key moves |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---|
| Black Monday (Oct 1987) | 1987-10-14 to 1987-10-19 | ours | 9.8 | -1.05 | -4.55 | -2.66 | -4.55 | `20261020-1900-s-p-500-long` (inferred: 20261023-2200-copper-comex-vs-lme-relative) | 100% | BZ=F +2.2%, ES=F -26.3%, NQ=F -21.2%, ZN=F -0.1%, DX-Y.NYB -1.4% |
| Iraq invades Kuwait (Aug-Oct 1990) | 1990-08-01 to 1990-10-11 | ours | 2.6 | -0.24 | -2.26 | -2.36 | -2.26 | `20261020-1900-s-p-500-long` (inferred: 20261023-2200-copper-comex-vs-lme-relative) | 100% | BZ=F +106.5%, ES=F -16.9%, NQ=F -26.0%, ZN=F -4.0%, DX-Y.NYB -5.3% |
| Desert Storm oil collapse (Jan 1991) | 1991-01-16 to 1991-01-17 | ours | 10.4 | +0.31 | +0.31 | +0.24 | +0.00 | `20261023-2200-copper-comex-vs-lme-relative` (inferred: 20261023-2200-copper-comex-vs-lme-relative) | 100% | BZ=F -30.3%, ES=F +3.7%, NQ=F +3.1%, ZN=F +1.2%, DX-Y.NYB -2.0% |
| Bond massacre (1994) | 1994-02-03 to 1994-11-07 | ours | 1.0 | -0.34 | -0.34 | -0.85 | -1.53 | `20261020-1900-s-p-500-long` (inferred: 20261023-2200-copper-comex-vs-lme-relative) | 100% | BZ=F +18.3%, ES=F -3.7%, NQ=F -2.4%, ZN=F -13.5%, DX-Y.NYB -9.8% |
| Asian crisis (H2 1997) | 1997-06-30 to 1997-12-31 | NBIM | 0.2 | +1.48 | +1.48 | +1.07 | -0.36 | `20261023-2200-copper-comex-vs-lme-relative` (inferred: 20261023-2200-copper-comex-vs-lme-relative) | 100% | BZ=F -12.1%, ES=F +9.6%, NQ=F +3.5%, ZN=F +5.1%, DX-Y.NYB +4.2% |
| Russia default and LTCM (Aug-Sep 1998) | 1998-07-31 to 1998-09-30 | NBIM | 1.3 | -0.15 | -1.06 | -0.61 | -2.36 | `20261020-1900-s-p-500-long` (inferred: 20261023-2200-copper-comex-vs-lme-relative) | 100% | BZ=F +17.2%, ES=F -9.2%, NQ=F -2.3%, ZN=F +7.1%, DX-Y.NYB -5.0% |
| Dot-com bust (Sep 2000-Mar 2001) | 2000-08-31 to 2001-03-31 | NBIM | 5.7 | -1.54 | -5.42 | -5.41 | -6.03 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` (inferred: 20261023-2200-copper-comex-vs-lme-relative) | 25% | BZ=F -30.4%, ES=F -23.9%, NQ=F -61.8%, ZN=F +5.3%, DX-Y.NYB +4.2% |
| 9/11 (Sep 2001) | 2001-08-31 to 2001-09-30 | NBIM | 3.1 | -1.55 | -2.40 | -1.92 | -3.81 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` (inferred: 20261023-2200-copper-comex-vs-lme-relative) | 36% | BZ=F -18.1%, ES=F -8.3%, NQ=F -20.2%, ZN=F +1.4%, DX-Y.NYB +0.1% |
| Iraq war premium unwinds (Mar 2003) | 2003-03-07 to 2003-03-21 | ours | 2.9 | +1.43 | +1.43 | +0.98 | -0.60 | - (inferred: 20261023-2200-copper-comex-vs-lme-relative) | 8% | BZ=F -25.8%, ES=F +7.1%, NQ=F +11.0%, ZN=F -4.1%, DX-Y.NYB +4.0% |
| Commodity and inflation surge (Sep 2007-Jul 2008) | 2007-08-31 to 2008-07-11 | Man (regime) | 0.7 | -0.54 | -2.76 | -1.63 | -2.76 | `20261020-1900-s-p-500-long` (inferred: 20261023-2200-copper-comex-vs-lme-relative) | 6% | BZ=F +98.8%, ES=F -16.0%, NQ=F -8.7%, ZN=F +6.1%, DX-Y.NYB -10.8% |
| Global financial crisis (May 2008-Feb 2009) | 2008-04-30 to 2009-02-28 | NBIM | 1.2 | -2.11 | -9.58 | -6.60 | -9.75 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | 0% | BZ=F -60.3%, ES=F -47.0%, NQ=F -41.9%, ZN=F +6.7%, DX-Y.NYB +21.4% |
| Lehman (Sep 2008-Mar 2009) | 2008-09-01 to 2009-03-02 | Eurex | 1.7 | -1.39 | -8.90 | -5.98 | -8.90 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | 0% | BZ=F -64.6%, ES=F -45.0%, NQ=F -42.1%, ZN=F +5.4%, DX-Y.NYB +14.9% |
| Euro crisis and US downgrade (Apr-Nov 2011) | 2011-03-31 to 2011-11-30 | NBIM | 0.1 | -1.41 | +0.19 | -0.45 | -4.07 | `20261020-1900-s-p-500-long` | 1% | BZ=F -5.0%, ES=F -5.7%, NQ=F -1.8%, ZN=F +9.3%, DX-Y.NYB +3.3% |
| US drought, grains spike (Jun-Aug 2012) | 2012-06-15 to 2012-08-10 | ours | 0.0 | +1.36 | +1.36 | +1.02 | -0.63 | - | 0% | BZ=F +15.7%, ES=F +5.0%, NQ=F +6.8%, ZN=F -0.7%, DX-Y.NYB +1.2% |
| Gold crash (Apr 2013) | 2013-04-11 to 2013-04-15 | ours | 0.0 | -0.29 | -0.29 | -0.44 | -0.65 | `20261020-1900-s-p-500-long` | 0% | BZ=F -3.7%, ES=F -2.8%, NQ=F -2.4%, ZN=F +0.4%, DX-Y.NYB +0.2% |
| Taper tantrum (May-Aug 2013) | 2013-04-30 to 2013-08-31 | NBIM | 0.1 | +0.69 | +0.69 | +0.54 | -0.30 | - | 1% | BZ=F +11.7%, ES=F +2.4%, NQ=F +6.7%, ZN=F -6.0%, DX-Y.NYB +0.4% |
| Oil collapse (H2 2014) | 2014-06-30 to 2014-12-31 | NBIM | 0.6 | -1.53 | +0.48 | +1.17 | -1.78 | `20261023-2200-copper-comex-vs-lme-relative` | 1% | BZ=F -49.0%, ES=F +5.1%, NQ=F +10.2%, ZN=F +1.3%, DX-Y.NYB +13.1% |
| China devaluation (Jun-Sep 2015) | 2015-05-31 to 2015-09-30 | NBIM | 0.0 | -0.16 | -1.18 | -1.70 | -2.11 | `20261020-1900-s-p-500-long` | 0% | BZ=F -18.0%, ES=F -9.4%, NQ=F -7.7%, ZN=F +0.3%, DX-Y.NYB -0.6% |
| Oil glut trough (Nov 2015-Jan 2016) | 2015-11-03 to 2016-01-20 | ours | 0.6 | -1.44 | -2.42 | -1.83 | -2.51 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | 0% | BZ=F -44.8%, ES=F -11.8%, NQ=F -12.3%, ZN=F +1.4%, DX-Y.NYB +2.0% |
| Volatility blow-up (Feb 2018) | 2018-02-01 to 2018-02-08 | ours | 0.5 | -2.29 | -1.82 | -2.28 | -1.89 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | 0% | BZ=F -6.2%, ES=F -8.1%, NQ=F -8.4%, ZN=F -0.3%, DX-Y.NYB +1.8% |
| Q4 2018 sell-off | 2018-08-31 to 2018-12-31 | NBIM | 0.1 | -0.80 | -2.56 | -3.95 | -3.12 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | 0% | BZ=F -30.5%, ES=F -13.7%, NQ=F -17.3%, ZN=F +1.3%, DX-Y.NYB +1.1% |
| Abqaiq attack (Sep 2019) | 2019-09-13 to 2019-09-16 | ours | 2.9 | -0.66 | -0.66 | -0.51 | -0.66 | `20261023-2200-copper-comex-vs-lme-relative`, `20261020-1900-s-p-500-long` | 0% | BZ=F +14.6%, ES=F -0.2%, NQ=F -0.4%, ZN=F +0.4%, DX-Y.NYB +0.4% |
| Covid crash (Feb-Mar 2020) | 2020-01-31 to 2020-03-31 | NBIM | 3.2 | +0.16 | -1.96 | -1.84 | -5.09 | `20261020-1900-s-p-500-long` | 2% | BZ=F -66.6%, ES=F -15.1%, NQ=F -7.9%, ZN=F +5.3%, DX-Y.NYB +1.7% |
| OPEC+ price war (Mar 2020) | 2020-03-06 to 2020-03-09 | ours | 7.0 | -1.17 | -1.17 | -0.30 | -1.17 | `20261020-1900-s-p-500-long` | 0% | BZ=F -24.1%, ES=F -7.3%, NQ=F -6.5%, ZN=F +0.9%, DX-Y.NYB -1.1% |
| Russia invades Ukraine (Feb-Jun 2022) | 2022-02-01 to 2022-06-30 | Eurex | 0.6 | -1.64 | -3.46 | -2.32 | -4.47 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | 0% | BZ=F +28.8%, ES=F -16.4%, NQ=F -23.1%, ZN=F -7.3%, DX-Y.NYB +8.6% |
| Inflation and rate shock (Jan-Sep 2022) | 2021-12-31 to 2022-09-30 | NBIM | 1.2 | -1.48 | -4.68 | -3.78 | -5.26 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | 0% | BZ=F +13.1%, ES=F -24.3%, NQ=F -32.4%, ZN=F -14.1%, DX-Y.NYB +17.2% |
| SVB and regional banks (Mar 2023) | 2023-03-08 to 2023-03-17 | ours | 1.7 | -0.41 | -0.41 | -0.24 | -0.87 | `20261023-2200-copper-comex-vs-lme-relative`, `20261020-1900-s-p-500-long` | 0% | BZ=F -11.7%, ES=F -0.9%, NQ=F +3.0%, ZN=F +4.2%, DX-Y.NYB -1.8% |
| Yen carry unwind (Aug 2024) | 2024-07-31 to 2024-08-05 | ours | 1.2 | -1.11 | -1.11 | -0.99 | -1.11 | `20261020-1900-s-p-500-long` | 0% | BZ=F -5.5%, ES=F -6.1%, NQ=F -7.6%, ZN=F +2.0%, DX-Y.NYB -1.4% |
| Tariff shock (Feb-Apr 2025) | 2025-02-18 to 2025-04-08 | NBIM | 0.7 | -1.53 | -4.44 | -3.91 | -4.44 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | 0% | BZ=F -17.2%, ES=F -18.3%, NQ=F -22.4%, ZN=F +2.4%, DX-Y.NYB -3.8% |
| Iran war week, Hormuz closed (Mar 2026) | 2026-02-27 to 2026-03-09 | ours | 1.4 | +0.20 | +0.20 | -0.05 | -0.22 | `20261020-1900-s-p-500-long` | 0% | BZ=F +26.0%, ES=F -1.3%, NQ=F -0.1%, ZN=F -1.2%, DX-Y.NYB +1.6% |
| Ceasefire, oil collapse (Apr 2026) | 2026-04-07 to 2026-04-10 | ours | 1.2 | +1.17 | +1.17 | +0.71 | +0.00 | - | 0% | BZ=F -12.9%, ES=F +3.0%, NQ=F +3.7%, ZN=F +0.2%, DX-Y.NYB -1.0% |
| AI-stock slide (Jul 2026) | 2026-07-16 to 2026-07-29 | ours | 0.2 | -0.64 | -0.64 | -0.63 | -0.64 | `20261020-1900-s-p-500-long`, `20261023-2200-copper-comex-vs-lme-relative` | 0% | BZ=F +7.7%, ES=F -3.0%, NQ=F -6.4%, ZN=F -0.3%, DX-Y.NYB +0.1% |
| US copper tariff announced (Jul 2025) | 2025-07-07 to 2025-07-09 | ours | 1.8 | +2.92 | +2.92 | +1.75 | +0.00 | - | 0% | BZ=F +0.9%, ES=F +0.5%, NQ=F +0.7%, ZN=F +0.3%, DX-Y.NYB -0.0% |
| Refined copper exempted from the tariff (Jul 2025) | 2025-07-29 to 2025-07-31 | ours | 6.5 | -5.54 | -5.54 | -1.99 | -5.54 | `20261023-2200-copper-comex-vs-lme-relative`, `20261020-1900-s-p-500-long` | 0% | BZ=F +0.0%, ES=F -0.5%, NQ=F -0.4%, ZN=F -0.3%, DX-Y.NYB +1.1% |

Vol-scaled = each market's move x (its vol now / its vol when the episode began) (Hull & White). Worst inside = the book's lowest point during the window, gapped. Proxy share = share of the loss resting on proxy, screened or inferred days.

**Named driver shocks** (one month; other markets move by their conditional mean given the drivers). Gapped R under the stress matrix and under each crisis window's correlations; isolated = drivers only. A sign flip means the answer depends on which correlations hold.

| Scenario | Drivers | k | Stops honoured (R) | Gapped, stress (R) | Gapped, 2008 (bonds rally as stocks fall) (R) | Gapped, 2022 (stocks and bonds fall together) (R) | Isolated (R) | Analogue episodes (gapped R) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Oil supply spike | BZ=F +25.0%, ES=F -3.0% | 0.9 | -0.22 | -0.22 | +0.52 | -0.12 | -0.55 | Iraq invades Kuwait (Aug-Oct 1990) -2.26; Iran war week, Hormuz closed (Mar 2026) +0.20 |
| Demand collapse | BZ=F -20.0%, ES=F -8.0%, ZN=F +2.0% | 0.6 | -1.13 | -1.96 | -2.48 | -2.13 | -1.47 | Global financial crisis (May 2008-Feb 2009) -9.58; Covid crash (Feb-Mar 2020) -1.96 |
| Fed hike shock **sign flip** | ZN=F -2.5%, DX-Y.NYB +2.0% | 0.6 | +0.04 | +0.04 | +0.54 | -0.99 | +0.00 | Bond massacre (1994) -0.34; Inflation and rate shock (Jan-Sep 2022) -4.68 |
| AI equity unwind | NQ=F -15.0%, ES=F -10.0% | 1.3 | -0.93 | -2.14 | -2.07 | -2.35 | -1.84 | Dot-com bust (Sep 2000-Mar 2001) -5.42; AI-stock slide (Jul 2026) -0.64 |
| USD squeeze | DX-Y.NYB +4.0% | 1.2 | -0.78 | -0.78 | -0.53 | -1.35 | +0.00 | Lehman (Sep 2008-Mar 2009) -8.90 |
| Risk-off funding shock | ^VIX +60.0%, ES=F -6.0% | 0.6 | -0.94 | -1.40 | -1.35 | -1.65 | -1.11 | Covid crash (Feb-Mar 2020) -1.96; Yen carry unwind (Aug 2024) -1.11 |
| Hedges fail (decorrelation) | ES=F -10.0%, ZN=F -3.0%, GC=F -6.0% | 1.0 | -1.16 | -2.36 | -1.72 | -3.06 | -1.84 | Inflation and rate shock (Jan-Sep 2022) -4.68 |
| Crop failure | ZC=F +30.0%, ZS=F +20.0%, ZW=F +25.0% | 1.5 | +1.50 | +1.50 | +3.40 | +0.27 | +0.00 | US drought, grains spike (Jun-Aug 2012) +1.36 |
| Inflation re-acceleration | BZ=F +15.0%, GC=F +10.0%, ZN=F -4.0% | 1.3 | +1.33 | +1.33 | +1.42 | +0.03 | +0.00 | Commodity and inflation surge (Sep 2007-Jul 2008) -2.76; Inflation and rate shock (Jan-Sep 2022) -4.68 |

**Worst case inside the plausibility ellipsoid** (Breuer et al.; stress matrix): 5 days at k = 3: -1.29R honoured, -5.19R gapped (rv:20261023-2200-copper-comex-vs-lme-relative -13.8%, ES=F -9.3%; loss by market: rv:20261023-2200-copper-comex-vs-lme-relative -3.5R, ES=F -1.7R); 20 days at k = 3: -1.29R honoured, -9.75R gapped (rv:20261023-2200-copper-comex-vs-lme-relative -25.8%, ES=F -17.7%; loss by market: rv:20261023-2200-copper-comex-vs-lme-relative -6.5R, ES=F -3.3R).

**CTA levels** (trend-follower proxy, observed closes). Prices at which a simple 1/3/12-month trend model would flip sign: describes likely systematic positioning, not a forecast. Published evidence finds trend-flow price pressure small (about 0.2% a week) and fading or reversing within about 4 weeks (Kang, Rouwenhorst & Tang).

| Market | Last (date) | Daily sd | Flip 1m / 3m / 12m | Distance in daily sd | Flips by roll-off within 5 days | Vol-target scale | State | 24m return, vol pctile |
|---|---|---:|---|---|---|---:|---|---|
| S&P 500 e-mini (ES=F) | 7614.75 (2026-10-30) | 0.77% | 7724.00 / 7628.25 / 6922.75 | -1.8 / -0.2 / +12.3 | - | 1.06 | correction | +29.7%, 40 |
| Copper COMEX vs LME (rv:20261023-2200-copper-comex-vs-lme-relative) | 100.61 (2026-10-29) | 0.70% | 100.85 / 104.31 / 104.14 | -0.3 / -5.2 / -4.9 | - | 1.43 | aligned | +0.4%, 12 |
| Brent front month (BZ=F) | 112.33 (2026-10-30) | 2.13% | 102.31 / 83.77 / 64.92 | +4.4 / +13.8 / +25.8 | - | 1.27 | aligned | +57.9%, 81 |
| US dollar index (DX-Y.NYB) | 101.96 (2026-10-30) | 0.27% | 102.10 / 99.96 / 99.22 | -0.5 / +7.4 / +10.2 | 1m in 1d | 1.11 | correction | -2.2%, 0 |
| Gold front month (GC=F) | 3884.90 (2026-10-30) | 1.40% | 4202.30 / 4090.50 / 4000.70 | -5.6 / -3.7 / -2.1 | - | 1.13 | aligned | +39.7%, 78 |
| Copper front month (HG=F) | 6.51 (2026-10-30) | 1.25% | 6.48 / 6.51 / 5.23 | +0.3 / -0.1 / +17.4 | 1m in 2d | 1.21 | aligned | +50.2%, 41 |
| Soybeans front month (ZS=F) | 1234.00 (2026-10-30) | 0.89% | 1284.00 / 1168.75 / 1080.25 | -4.5 / +6.1 / +15.0 | - | 1.09 | correction | +26.7%, 73 |

**Measured by the research loop (agent 12)** — each flag above against its base rate, before any may alert: `cftc_crowded` {"pct": 90}: no edge (lift 1.00, shrunk 1.00; 7.50% vs base 7.49%; 360 episodes, adverse 20d; as of 2026-10-19); `cftc_crowded_entry` {"z": 2.0}: no edge (excess 0.02 sd, shrunk 0.02; 489 episodes, signed 20d; as of 2026-10-19); `crowded_red` {"pct": 90}: no edge (lift 1.29, shrunk 1.26; 9.41% vs base 7.31%; 170 episodes, adverse 20d; as of 2026-10-19); `cta_state` {"state": "correction"}: no edge (excess 0.06 sd, shrunk 0.06; 1206 episodes, signed 20d; as of 2026-10-19); `cta_panic`: no edge (excess 0.06 sd, shrunk 0.06; 180 episodes, signed 20d; as of 2026-10-19); `cta_panic` {"only": "short"}: no edge (excess 0.09 sd, shrunk 0.07; 114 episodes, signed 20d; as of 2026-10-19); `cta_state` {"state": "rebound"}: no edge (excess 0.07 sd, shrunk 0.07; 909 episodes, signed 20d; as of 2026-10-19); `cta_rolloff_flip`: no edge (excess 0.01 sd, shrunk 0.01; 8290 episodes, signed 5d; as of 2026-10-19); `cta_vol_shrinking`: no edge (excess 0.04 sd, shrunk 0.03; 39 episodes, signed 20d; as of 2026-10-19); `turbulence_persistent` {"market": "ES=F"}: no edge (lift 1.85, shrunk 1.63; 10.53% vs base 5.68%; 57 episodes, adverse 20d; as of 2026-10-19). Details: research/index.md.

Descriptive only: no component is a signal until it passes the quant-research gate. Suggestions and decisions stay with the PM.
