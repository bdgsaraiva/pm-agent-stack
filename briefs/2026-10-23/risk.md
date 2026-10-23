# Risk and crowding — 2026-10-23

## Risk and crowding (descriptive; in paper R)

Risk model: daily log returns of front-month closes (Yahoo continuous contracts, roll gaps not adjusted) spliced with spot/index proxies where a contract has no close (flagged). Current vol = EWMA 0.94; calm correlation = last 250 days; stress correlation = the top-20% turbulence days of the whole history; both shrunk toward constant correlation (Ledoit & Wolf).
Model window 2003-12-02 to 2026-10-23; 1122 stress days; shrinkage calm 0.07, stress 0.02.

**Market state:** turbulence percentile 91 of the last 756 days (2026-10-23); 2 of the last 5 days in the top 20%. HY OAS 3.40% (2026-10-22), +67bp over 21 observations ([FRED](https://fred.stlouisfed.org/series/BAMLH0A0HYM2)). VIX 20.4, percentile 65 since 1990-01-02 (2026-10-23). Funding **stressing**.

**Book:** 3 ideas, 2.8 effective independent ideas (stress matrix). Daily sd 0.49R calm, 0.89R stress. Open -1.86R; -1.39R more if every stop is hit. Book -2.16R from its 10-day high; -2.16R over 60 days (closed R + open marks; sizing halves at -4.0R).

| Idea | Dir | Size | Last (date) | R now | Stop (daily sd) | 1-sd day (R) | Share of stress risk | Cluster | CFTC pct on side (w/w z; ex-trend pct; report date) | Flags |
|---|---|---:|---|---:|---:|---:|---:|---:|---|---|
| Gold `20261020-1900-gold-long` | long | 1.25 | 4038.50 (2026-10-23) | -0.54 | 1.9 | 0.30 | 23% | 1 | 40 (-0.5; 2; 2026-10-13) | trend leg flips by roll-off within 5 days (63d, 252d) |
| S&P 500 `20261020-1900-s-p-500-long` | long | 1.00 | 7665.25 (2026-10-23) | -0.24 | 6.1 | 0.13 | 26% | 2 | n/a | - |
| US 10y rates `20261020-1900-us-10y-rates-short` | short | 1.00 | 106.20 (2026-10-23) | -0.95 | 0.1 | 0.42 | 50% | 3 | n/a | - |

Share of stress risk sums to 100%; a negative share is a hedge. CFTC levels mostly restate past returns (returns lead positions in 10 of 10 markets: Sanders, Irwin & Merrin). Crowding is context; it turns red only when funding is stressing. No crowding or CTA flag alerts unless the research loop (agent 12) rates it supported; its measured verdicts are listed under the CTA table.

**Worst historical windows for today's book** (searched 1986-01-03 to 2026-10-23, 10309 days; FRTB-style: the window in which this book would have lost most; spot/index proxies where a contract had no close; markets with no series that day inferred from those that printed (12% of market-days)).

| Horizon | Window (start close to end close) | Stops honoured (R) | Gapped (R) | Days on proxies | Days inferred | Biggest losers | Moves |
|---:|---|---:|---:|---:|---:|---|---|
| 1d | 2008-11-28 to 2008-12-01 | -4.69 | -4.69 | 0% | 0% | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | ES=F -8.9%, GC=F -5.1%, ZN=F +1.6% |
| 5d | 1987-10-15 to 1987-10-22 | -0.30 | -11.06 | 67% | 33% | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | ES=F -16.7%, ZN=F +8.2%, GC=F +3.3% |
| 20d | 2020-02-14 to 2020-03-16 | -2.14 | -12.73 | 0% | 0% | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | ES=F -28.5%, GC=F -6.1%, ZN=F +5.4% |
| 60d | 2008-09-25 to 2008-12-19 | -3.05 | -20.83 | 0% | 0% | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | ES=F -26.7%, ZN=F +13.6%, GC=F -4.7% |

**What hurts this book most** (reverse stress: average moves on its worst 103 days since 1986-01-03, x 0.85 for fat tails; Glasserman, Kang & Kang): GC=F -1.3%, ES=F -2.6%, ZN=F +0.7% = -1.62R a day. Worst days: 2008-12-01, 1987-10-20, 2009-03-18.

**Episode library** (replayed day by day on today's book; relative moves). Stress P&L in R from today's marks. Replays run day by day: 'stops honoured' exits at the first close beyond the stop (a gap can cost more than 1R); 'gapped' holds to the end. Instantaneous shocks cap honoured losses at the stop. k = plausibility: the scenario's Mahalanobis distance under the stress matrix (scaled to its length), converted to a one-market sd equivalent, so 3 is about as rare as a 3-sd move in one market. Stress tests are not early warnings (Borio et al.).

| Episode | Window | Source | k | Stops honoured (R) | Gapped (R) | Vol-scaled, gapped (R) | Worst inside (R) | Biggest losers | Proxy share | Key moves |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---|
| Black Monday (Oct 1987) | 1987-10-14 to 1987-10-19 | ours | 9.8 | -0.33 | -3.84 | -1.68 | -3.84 | `20261020-1900-s-p-500-long` (inferred: 20261020-1900-gold-long) | 100% | BZ=F +2.2%, ES=F -26.3%, NQ=F -21.2%, ZN=F -0.1%, DX-Y.NYB -1.4% |
| Iraq invades Kuwait (Aug-Oct 1990) | 1990-08-01 to 1990-10-11 | ours | 2.6 | +5.00 | +2.97 | +4.26 | +0.00 | `20261020-1900-s-p-500-long` (inferred: 20261020-1900-gold-long) | 100% | BZ=F +106.5%, ES=F -16.9%, NQ=F -26.0%, ZN=F -4.0%, DX-Y.NYB -5.3% |
| Desert Storm oil collapse (Jan 1991) | 1991-01-16 to 1991-01-17 | ours | 10.4 | -0.80 | -0.80 | -0.94 | -0.80 | `20261020-1900-us-10y-rates-short`, `20261020-1900-gold-long` (inferred: 20261020-1900-gold-long) | 100% | BZ=F -30.3%, ES=F +3.7%, NQ=F +3.1%, ZN=F +1.2%, DX-Y.NYB -2.0% |
| Bond massacre (1994) | 1994-02-03 to 1994-11-07 | ours | 1.0 | +14.51 | +14.61 | +17.03 | +0.00 | `20261020-1900-s-p-500-long` (inferred: 20261020-1900-gold-long) | 100% | BZ=F +18.3%, ES=F -3.7%, NQ=F -2.4%, ZN=F -13.5%, DX-Y.NYB -9.8% |
| Asian crisis (H2 1997) | 1997-06-30 to 1997-12-31 | NBIM | 0.2 | +0.79 | -4.33 | -7.38 | -5.11 | `20261020-1900-us-10y-rates-short`, `20261020-1900-gold-long` (inferred: 20261020-1900-gold-long) | 100% | BZ=F -12.1%, ES=F +9.6%, NQ=F +3.5%, ZN=F +5.1%, DX-Y.NYB +4.2% |
| Russia default and LTCM (Aug-Sep 1998) | 1998-07-31 to 1998-09-30 | NBIM | 1.3 | +1.43 | -6.90 | -16.89 | -6.90 | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` (inferred: 20261020-1900-gold-long) | 100% | BZ=F +17.2%, ES=F -9.2%, NQ=F -2.3%, ZN=F +7.1%, DX-Y.NYB -5.0% |
| Dot-com bust (Sep 2000-Mar 2001) | 2000-08-31 to 2001-03-31 | NBIM | 5.5 | -1.90 | -12.07 | -13.83 | -13.51 | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | 7% | BZ=F -30.4%, ES=F -23.9%, NQ=F -61.8%, ZN=F +5.3%, DX-Y.NYB +4.2% |
| 9/11 (Sep 2001) | 2001-08-31 to 2001-09-30 | NBIM | 3.0 | +0.53 | -1.28 | +0.26 | -2.38 | `20261020-1900-s-p-500-long`, `20261020-1900-us-10y-rates-short` | 2% | BZ=F -18.1%, ES=F -8.3%, NQ=F -20.2%, ZN=F +1.4%, DX-Y.NYB +0.1% |
| Iraq war premium unwinds (Mar 2003) | 2003-03-07 to 2003-03-21 | ours | 2.7 | -0.12 | +3.87 | +4.53 | -0.86 | `20261020-1900-gold-long` | 0% | BZ=F -25.8%, ES=F +7.1%, NQ=F +11.0%, ZN=F -4.1%, DX-Y.NYB +4.0% |
| Commodity and inflation surge (Sep 2007-Jul 2008) | 2007-08-31 to 2008-07-11 | Man (regime) | 0.6 | +9.61 | +1.66 | +4.81 | -2.90 | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | 1% | BZ=F +98.8%, ES=F -16.0%, NQ=F -8.7%, ZN=F +6.1%, DX-Y.NYB -10.8% |
| Global financial crisis (May 2008-Feb 2009) | 2008-04-30 to 2009-02-28 | NBIM | 1.4 | -2.40 | -13.52 | -9.81 | -22.35 | `20261020-1900-s-p-500-long`, `20261020-1900-us-10y-rates-short` | 1% | BZ=F -60.3%, ES=F -47.0%, NQ=F -41.9%, ZN=F +6.7%, DX-Y.NYB +21.4% |
| Lehman (Sep 2008-Mar 2009) | 2008-09-01 to 2009-03-02 | Eurex | 2.0 | -2.23 | -10.73 | -8.40 | -17.63 | `20261020-1900-s-p-500-long`, `20261020-1900-us-10y-rates-short` | 0% | BZ=F -64.6%, ES=F -45.0%, NQ=F -42.1%, ZN=F +5.4%, DX-Y.NYB +14.9% |
| Euro crisis and US downgrade (Apr-Nov 2011) | 2011-03-31 to 2011-11-30 | NBIM | 0.2 | +4.66 | -5.53 | -2.06 | -10.51 | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | 0% | BZ=F -5.0%, ES=F -5.7%, NQ=F -1.8%, ZN=F +9.3%, DX-Y.NYB +3.3% |
| US drought, grains spike (Jun-Aug 2012) | 2012-06-15 to 2012-08-10 | ours | 0.0 | -0.25 | +1.51 | +1.39 | -1.44 | `20261020-1900-gold-long` | 0% | BZ=F +15.7%, ES=F +5.0%, NQ=F +6.8%, ZN=F -0.7%, DX-Y.NYB +1.2% |
| Gold crash (Apr 2013) | 2013-04-11 to 2013-04-15 | ours | 4.5 | -1.94 | -4.35 | -5.62 | -4.35 | `20261020-1900-gold-long`, `20261020-1900-s-p-500-long` | 0% | BZ=F -3.7%, ES=F -2.8%, NQ=F -2.4%, ZN=F +0.4%, DX-Y.NYB +0.2% |
| Taper tantrum (May-Aug 2013) | 2013-04-30 to 2013-08-31 | NBIM | 0.1 | -0.38 | +5.58 | +12.05 | -0.84 | `20261020-1900-gold-long` | 0% | BZ=F +11.7%, ES=F +2.4%, NQ=F +6.7%, ZN=F -6.0%, DX-Y.NYB +0.4% |
| Oil collapse (H2 2014) | 2014-06-30 to 2014-12-31 | NBIM | 0.6 | -1.61 | -3.20 | -4.56 | -5.47 | `20261020-1900-gold-long`, `20261020-1900-us-10y-rates-short` | 0% | BZ=F -49.0%, ES=F +5.1%, NQ=F +10.2%, ZN=F +1.3%, DX-Y.NYB +13.1% |
| China devaluation (Jun-Sep 2015) | 2015-05-31 to 2015-09-30 | NBIM | 0.0 | -2.07 | -3.73 | -4.41 | -3.84 | `20261020-1900-s-p-500-long`, `20261020-1900-gold-long` | 0% | BZ=F -18.0%, ES=F -9.4%, NQ=F -7.7%, ZN=F +0.3%, DX-Y.NYB -0.6% |
| Oil glut trough (Nov 2015-Jan 2016) | 2015-11-03 to 2016-01-20 | ours | 0.6 | -1.80 | -3.85 | -3.56 | -3.85 | `20261020-1900-s-p-500-long`, `20261020-1900-us-10y-rates-short` | 0% | BZ=F -44.8%, ES=F -11.8%, NQ=F -12.3%, ZN=F +1.4%, DX-Y.NYB +2.0% |
| Volatility blow-up (Feb 2018) | 2018-02-01 to 2018-02-08 | ours | 0.5 | -2.29 | -1.75 | -2.24 | -1.75 | `20261020-1900-s-p-500-long`, `20261020-1900-gold-long` | 0% | BZ=F -6.2%, ES=F -8.1%, NQ=F -8.4%, ZN=F -0.3%, DX-Y.NYB +1.8% |
| Q4 2018 sell-off | 2018-08-31 to 2018-12-31 | NBIM | 0.1 | +0.88 | -2.28 | -3.51 | -3.02 | `20261020-1900-s-p-500-long`, `20261020-1900-us-10y-rates-short` | 0% | BZ=F -30.5%, ES=F -13.7%, NQ=F -17.3%, ZN=F +1.3%, DX-Y.NYB +1.1% |
| Abqaiq attack (Sep 2019) | 2019-09-13 to 2019-09-16 | ours | 2.6 | -0.21 | -0.21 | -0.16 | -0.21 | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | 0% | BZ=F +14.6%, ES=F -0.2%, NQ=F -0.4%, ZN=F +0.4%, DX-Y.NYB +0.4% |
| Covid crash (Feb-Mar 2020) | 2020-01-31 to 2020-03-31 | NBIM | 3.1 | -2.82 | -8.55 | -10.83 | -11.51 | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | 1% | BZ=F -66.6%, ES=F -15.1%, NQ=F -7.9%, ZN=F +5.3%, DX-Y.NYB +1.7% |
| OPEC+ price war (Mar 2020) | 2020-03-06 to 2020-03-09 | ours | 6.9 | -2.27 | -2.27 | -1.29 | -2.27 | `20261020-1900-s-p-500-long`, `20261020-1900-us-10y-rates-short` | 0% | BZ=F -24.1%, ES=F -7.3%, NQ=F -6.5%, ZN=F +0.9%, DX-Y.NYB -1.1% |
| Russia invades Ukraine (Feb-Jun 2022) | 2022-02-01 to 2022-06-30 | Eurex | 0.7 | -0.91 | +4.92 | +8.46 | -0.03 | `20261020-1900-s-p-500-long` | 0% | BZ=F +28.8%, ES=F -16.4%, NQ=F -23.1%, ZN=F -7.3%, DX-Y.NYB +8.6% |
| Inflation and rate shock (Jan-Sep 2022) | 2021-12-31 to 2022-09-30 | NBIM | 1.2 | +13.68 | +8.46 | +13.07 | +0.00 | `20261020-1900-s-p-500-long`, `20261020-1900-gold-long` | 0% | BZ=F +13.1%, ES=F -24.3%, NQ=F -32.4%, ZN=F -14.1%, DX-Y.NYB +17.2% |
| SVB and regional banks (Mar 2023) | 2023-03-08 to 2023-03-17 | ours | 1.9 | +1.51 | -2.50 | -1.31 | -2.83 | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | 0% | BZ=F -11.7%, ES=F -0.9%, NQ=F +3.0%, ZN=F +4.2%, DX-Y.NYB -1.8% |
| Yen carry unwind (Aug 2024) | 2024-07-31 to 2024-08-05 | ours | 1.3 | -1.83 | -3.13 | -3.60 | -3.13 | `20261020-1900-us-10y-rates-short`, `20261020-1900-s-p-500-long` | 0% | BZ=F -5.5%, ES=F -6.1%, NQ=F -7.6%, ZN=F +2.0%, DX-Y.NYB -1.4% |
| Tariff shock (Feb-Apr 2025) | 2025-02-18 to 2025-04-08 | NBIM | 0.7 | -1.82 | -5.63 | -5.50 | -6.52 | `20261020-1900-s-p-500-long`, `20261020-1900-us-10y-rates-short` | 0% | BZ=F -17.2%, ES=F -18.3%, NQ=F -22.4%, ZN=F +2.4%, DX-Y.NYB -3.8% |
| Iran war week, Hormuz closed (Mar 2026) | 2026-02-27 to 2026-03-09 | ours | 1.4 | +0.44 | +0.34 | +1.69 | -0.08 | `20261020-1900-gold-long`, `20261020-1900-s-p-500-long` | 0% | BZ=F +26.0%, ES=F -1.3%, NQ=F -0.1%, ZN=F -1.2%, DX-Y.NYB +1.6% |
| Ceasefire, oil collapse (Apr 2026) | 2026-04-07 to 2026-04-10 | ours | 1.2 | +0.76 | +0.90 | +0.35 | +0.00 | `20261020-1900-us-10y-rates-short` | 0% | BZ=F -12.9%, ES=F +3.0%, NQ=F +3.7%, ZN=F +0.2%, DX-Y.NYB -1.0% |
| AI-stock slide (Jul 2026) | 2026-07-16 to 2026-07-29 | ours | 0.2 | -0.39 | +0.09 | +0.23 | -0.14 | `20261020-1900-s-p-500-long` | 0% | BZ=F +7.7%, ES=F -3.0%, NQ=F -6.4%, ZN=F -0.3%, DX-Y.NYB +0.1% |

Vol-scaled = each market's move x (its vol now / its vol when the episode began) (Hull & White). Worst inside = the book's lowest point during the window, gapped. Proxy share = share of the loss resting on proxy, screened or inferred days.

**Named driver shocks** (one month; other markets move by their conditional mean given the drivers). Gapped R under the stress matrix and under each crisis window's correlations; isolated = drivers only. A sign flip means the answer depends on which correlations hold.

| Scenario | Drivers | k | Stops honoured (R) | Gapped, stress (R) | Gapped, 2008 (bonds rally as stocks fall) (R) | Gapped, 2022 (stocks and bonds fall together) (R) | Isolated (R) | Analogue episodes (gapped R) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Oil supply spike | BZ=F +25.0%, ES=F -3.0% | 0.9 | +0.28 | +0.28 | +1.45 | +0.35 | -0.56 | Iraq invades Kuwait (Aug-Oct 1990) +2.97; Iran war week, Hormuz closed (Mar 2026) +0.34 |
| Demand collapse | BZ=F -20.0%, ES=F -8.0%, ZN=F +2.0% | 0.6 | -1.03 | -3.87 | -4.35 | -3.95 | -3.64 | Global financial crisis (May 2008-Feb 2009) -13.52; Covid crash (Feb-Mar 2020) -8.55 |
| Fed hike shock | ZN=F -2.5%, DX-Y.NYB +2.0% | 0.6 | +2.34 | +2.24 | +2.47 | +1.70 | +2.70 | Bond massacre (1994) +14.61; Inflation and rate shock (Jan-Sep 2022) +8.46 |
| AI equity unwind | NQ=F -15.0%, ES=F -10.0% | 1.4 | -0.88 | -2.53 | -2.35 | -1.44 | -1.85 | Dot-com bust (Sep 2000-Mar 2001) -12.07; AI-stock slide (Jul 2026) +0.09 |
| USD squeeze | DX-Y.NYB +4.0% | 1.2 | -0.40 | -0.72 | -1.38 | -0.39 | +0.00 | Lehman (Sep 2008-Mar 2009) -10.73 |
| Risk-off funding shock | ^VIX +60.0%, ES=F -6.0% | 0.6 | -0.82 | -1.69 | -2.04 | -0.78 | -1.11 | Covid crash (Feb-Mar 2020) -8.55; Yen carry unwind (Aug 2024) -3.13 |
| Hedges fail (decorrelation) | ES=F -10.0%, ZN=F -3.0%, GC=F -6.0% | 1.0 | +1.90 | -0.20 | -0.20 | -0.20 | -0.20 | Inflation and rate shock (Jan-Sep 2022) +8.46 |
| Crop failure | ZC=F +30.0%, ZS=F +20.0%, ZW=F +25.0% | 1.5 | +2.32 | +2.32 | +4.84 | +0.31 | +0.00 | US drought, grains spike (Jun-Aug 2012) +1.51 |
| Inflation re-acceleration | BZ=F +15.0%, GC=F +10.0%, ZN=F -4.0% | 1.3 | +7.84 | +7.84 | +7.75 | +6.63 | +6.95 | Commodity and inflation surge (Sep 2007-Jul 2008) +1.66; Inflation and rate shock (Jan-Sep 2022) +8.46 |

**Worst case inside the plausibility ellipsoid** (Breuer et al.; stress matrix): 5 days at k = 3: -1.39R honoured, -7.41R gapped (ES=F -10.1%, GC=F -6.5%, ZN=F +3.6%; loss by market: ZN=F -3.8R, ES=F -1.9R, GC=F -1.7R); 20 days at k = 3: -1.39R honoured, -14.66R gapped (ES=F -19.2%, GC=F -12.5%, ZN=F +7.2%; loss by market: ZN=F -7.8R, ES=F -3.6R, GC=F -3.3R).

**CTA levels** (trend-follower proxy, observed closes). Prices at which a simple 1/3/12-month trend model would flip sign: describes likely systematic positioning, not a forecast. Published evidence finds trend-flow price pressure small (about 0.2% a week) and fading or reversing within about 4 weeks (Kang, Rouwenhorst & Tang).

| Market | Last (date) | Daily sd | Flip 1m / 3m / 12m | Distance in daily sd | Flips by roll-off within 5 days | Vol-target scale | State | 24m return, vol pctile |
|---|---|---:|---|---|---|---:|---|---|
| Gold front month (GC=F) | 4038.50 (2026-10-23) | 1.15% | 4298.00 / 4077.00 / 4065.40 | -5.4 / -0.8 / -0.6 | 3m in 2d, 12m in 3d | 1.22 | aligned | +46.3%, 76 |
| S&P 500 e-mini (ES=F) | 7665.25 (2026-10-23) | 0.68% | 7767.00 / 7448.25 / 6737.00 | -1.9 / +4.2 / +18.9 | - | 1.11 | correction | +30.1%, 31 |
| 10y T-note future (ZN=F) | 106.20 (2026-10-23) | 0.39% | 104.86 / 108.58 / 113.80 | +3.2 / -5.6 / -17.6 | - | 0.87 | rebound | -4.6%, 34 |
| Brent front month (BZ=F) | 111.04 (2026-10-23) | 2.25% | 106.60 / 88.36 / 62.59 | +1.8 / +10.2 / +25.5 | - | 1.24 | aligned | +46.0%, 81 |
| US dollar index (DX-Y.NYB) | 101.74 (2026-10-23) | 0.29% | 101.29 / 101.51 / 98.90 | +1.5 / +0.8 / +9.9 | 1m in 5d | 1.08 | aligned | -2.2%, 2 |
| Copper front month (HG=F) | 6.48 (2026-10-23) | 1.33% | 6.72 / 6.34 / 4.96 | -2.7 / +1.7 / +20.1 | 1m in 5d, 3m in 5d | 1.19 | correction | +49.1%, 41 |
| Soybeans front month (ZS=F) | 1274.75 (2026-10-23) | 0.98% | 1317.50 / 1208.50 / 1034.75 | -3.4 / +5.5 / +21.3 | - | 1.04 | correction | +29.9%, 73 |

**Measured by the research loop (agent 12)** — each flag above against its base rate, before any may alert: `cftc_crowded` {"pct": 90}: no edge (lift 1.00, shrunk 1.00; 7.50% vs base 7.49%; 360 episodes, adverse 20d; as of 2026-10-19); `cftc_crowded_entry` {"z": 2.0}: no edge (excess 0.02 sd, shrunk 0.02; 489 episodes, signed 20d; as of 2026-10-19); `crowded_red` {"pct": 90}: no edge (lift 1.29, shrunk 1.26; 9.41% vs base 7.31%; 170 episodes, adverse 20d; as of 2026-10-19); `cta_state` {"state": "correction"}: no edge (excess 0.06 sd, shrunk 0.06; 1206 episodes, signed 20d; as of 2026-10-19); `cta_panic`: no edge (excess 0.06 sd, shrunk 0.06; 180 episodes, signed 20d; as of 2026-10-19); `cta_panic` {"only": "short"}: no edge (excess 0.09 sd, shrunk 0.07; 114 episodes, signed 20d; as of 2026-10-19); `cta_state` {"state": "rebound"}: no edge (excess 0.07 sd, shrunk 0.07; 909 episodes, signed 20d; as of 2026-10-19); `cta_rolloff_flip`: no edge (excess 0.01 sd, shrunk 0.01; 8290 episodes, signed 5d; as of 2026-10-19); `cta_vol_shrinking`: no edge (excess 0.04 sd, shrunk 0.03; 39 episodes, signed 20d; as of 2026-10-19); `turbulence_persistent` {"market": "ES=F"}: no edge (lift 1.85, shrunk 1.63; 10.53% vs base 5.68%; 57 episodes, adverse 20d; as of 2026-10-19). Details: research/index.md.

Descriptive only: no component is a signal until it passes the quant-research gate. Suggestions and decisions stay with the PM.
