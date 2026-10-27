# Tape after the close: 2026-10-26

Computed by code (`pmstack quant tape`): trend legs and CTA flip levels, realised and implied vol, correlation regime, positioning, half-month seasonality, front curve. Descriptive only: nothing here is a signal. Method: `docs/research/quant.md`.

## What changed

- Trend legs that flipped today: NG=F:63, ZC=F:63
- Stretched legs (distance to flip beyond 2 sd and the 95th/5th percentile of its history since 2000; a print rule, base rate not studied): SI=F:21, ZC=F:21, ZW=F:21
- Vol rising fast (21-day vol at least 1.5x the 63-day): none
- Vol in the extreme regime (at or above the 95th percentile of its full history): none
- Implied-minus-realised gap outside its 3-year 10-90 band: BZ=F, CL=F, ES=F
- Correlation outside its 3-year 10-90 band: BZ=F~ES=F, CL=F~ES=F, RB=F~ES=F, HO=F~ES=F, HO=F~DX-Y.NYB
- Positioning at a 3-year extreme (CFTC, from the Friday release): RB=F, NG=F, SB=F
- Large moves vs recent vol (1-day or 5-day beyond 2 trailing sd): BZ=F, HO=F, NG=F, SB=F
- Average pairwise 63-day correlation across 12 commodity markets: 0.08 (percentile 1 of the last 3 years)
- Measured by the testing gate (research/index.md): a8_crowded_adverse_v1 no edge; a8_crowded_entry_v1 no edge; a8_cta_correction_v1 no edge; a8_cta_panic_v1 no edge; a8_cta_panic_v2 no edge; a8_cta_rebound_v1 no edge; a8_cta_rolloff_v1 no edge; a8_cta_vol_shrinking_v1 no edge; p_tsmom_mop2012_v1 no edge. Stretched and flipped are print rules with no study yet.
- Since the 2026-10-24 tape: newly stretched SI=F:21, ZC=F:21, ZW=F:21; no longer stretched none

## Markets

| Market | Close | 1d % | Trend 1m / 3m / 12m (flip; distance sd) | State | Vol 21d (3y pctile; regime) | 21d/63d | Implied - realised (gap pctile) | MM % OI (pctile) | Carry ann. % | Next half-month norm: median % [IQR] (years) |
|---|---|---|---|---|---|---|---|---|---|---|
| [Brent](https://finance.yahoo.com/quote/BZ=F) | 109.76 | -5.96 | + 104.32 (+2.0) / + 84.09 (+10.5) / + 65.99 (+20.1) | aligned | 37.1 (67; normal) | 0.84 | +29.6 (98) | - (-) | +54.0 | -1.03 [-5.2, +1.4] (19) |
| [WTI](https://finance.yahoo.com/quote/CL=F) | 100.88 | -2.31 | + 92.41 (+3.3) / + 79.26 (+9.0) / + 61.79 (+18.4) | aligned | 38.9 (68; normal) | 0.89 | +21.1 (97) | 2.0 (14) | +26.8 | -1.87 [-5.9, +1.4] (26) |
| [RBOB](https://finance.yahoo.com/quote/RB=F) | 3.1202 | -2.85 | - 3.3934 (-3.1) / - 3.3345 (-2.5) / + 1.9269 (+17.8) | correction | 31.2 (44; normal) | 0.72 | - (-) | 27.8 (99) | +28.2 | -2.40 [-8.2, +0.2] (25) |
| [ULSD](https://finance.yahoo.com/quote/HO=F) | 4.7 | -5.70 | + 4.6847 (+0.1) / + 4.1509 (+4.4) / + 2.403 (+24.0) | aligned | 48.8 (83; high) | 1.04 | - (-) | 4.9 (61) | +34.8 | -2.67 [-6.8, +3.9] (26) |
| [Henry Hub](https://finance.yahoo.com/quote/NG=F) | 3.037 | +15.04 | - 3.196 (-1.9) / +! 2.662 (+4.9) / - 3.344 (-3.6) | aligned | 69.3 (60; normal) | 1.37 | - (-) | -9.2 (1) | -175.4 | -4.60 [-10.3, +4.1] (26) |
| [Gold](https://finance.yahoo.com/quote/GC=F) | 4029.9 | +0.55 | - 4321.2 (-5.3) / - 4038.7 (-0.2) / - 4145.6 (-2.1) | aligned | 19.0 (59; normal) | 0.92 | +5.4 (86) | 25.9 (33) | - | +0.69 [-1.3, +2.9] (26) |
| [Silver](https://finance.yahoo.com/quote/SI=F) | 54.108 | +0.74 | -* 64.245 (-7.5) / - 57.296 (-2.5) / + 48.482 (+4.8) | correction | 36.7 (65; normal) | 1.02 | - (-) | - (-) | - | +1.54 [-2.3, +4.7] (26) |
| [COMEX copper](https://finance.yahoo.com/quote/HG=F) | 6.508 | +0.49 | - 6.6955 (-2.2) / + 6.322 (+2.2) / + 5.082 (+18.9) | correction | 18.7 (25; normal) | 0.89 | - (-) | 14.6 (49) | - | +0.25 [-3.4, +4.0] (26) |
| [Corn](https://finance.yahoo.com/quote/ZC=F) | 454 | -0.44 | -* 528.25 (-9.5) / -! 458.5 (-0.6) / + 428 (+3.7) | correction | 22.1 (62; normal) | 0.88 | - (-) | 9.0 (79) | - | -0.27 [-3.4, +1.4] (26) |
| [Soybeans](https://finance.yahoo.com/quote/ZS=F) | 1253.75 | -0.22 | - 1319 (-4.8) / + 1212 (+3.2) / + 1044.75 (+17.3) | correction | 12.5 (8; low) | 0.72 | - (-) | 20.2 (89) | - | +1.36 [-0.5, +4.8] (26) |
| [Wheat](https://finance.yahoo.com/quote/ZW=F) | 615 | -1.60 | -* 703.25 (-7.1) / - 662.5 (-4.0) / + 513 (+9.6) | correction | 20.6 (19; low) | 0.70 | - (-) | - (-) | - | -1.23 [-4.0, +0.8] (26) |
| [Sugar](https://finance.yahoo.com/quote/SB=F) | 19.1 | -5.63 | + 17.5 (+4.1) / + 14.55 (+12.6) / + 15.29 (+10.3) | aligned | 44.9 (99; high) | 1.25 | - (-) | 21.9 (99) | - | -0.09 [-3.6, +3.2] (26) |
| [S&P 500 e-mini](https://finance.yahoo.com/quote/ES=F) | 7726.25 | +0.87 | - 7803.75 (-1.5) / + 7465.25 (+5.0) / + 6775 (+19.1) | correction | 10.1 (20; normal) | 0.87 | +9.7 (94) | - (-) | - | +1.56 [-0.2, +2.8] (26) |
| [Nasdaq 100 e-mini](https://finance.yahoo.com/quote/NQ=F) | 29488.2 | +1.27 | - 30889.2 (-4.0) / + 27922 (+4.7) / + 25254 (+13.4) | correction | 18.8 (61; normal) | 0.96 | - (-) | - (-) | - | +1.55 [-0.8, +4.0] (26) |
| [US 10y note](https://finance.yahoo.com/quote/ZN=F) | 106.172 | +0.01 | + 104.859 (+3.8) / - 108.812 (-7.6) / - 113.484 (-20.5) | rebound | 5.7 (74; normal) | 1.14 | - (-) | - (-) | - | -0.09 [-0.9, +0.7] (26) |
| [US dollar index](https://finance.yahoo.com/quote/DX-Y.NYB) | 102.044 | +0.23 | + 100.97 (+3.6) / + 101.38 (+2.2) / + 98.94 (+10.6) | aligned | 4.7 (22; low) | 0.94 | - (-) | - (-) | - | -0.01 [-1.3, +1.5] (40) |

Legend: `!` flipped today, `*` stretched. Seasonality: a norm (median and interquartile range of the next half-month in earlier years), descriptive and never a signal; 24 buckets, so about one clears 5% by chance. Implied vol: OVX is options on the USO ETF and GVZ on GLD, not on the futures; implied above realised is the normal state. Prices are Yahoo continuous front months: 3- and 12-month flip levels can sit on an expired contract and roll gaps enter vol and seasonal norms. Curve and carry from contracts collected since 24 Oct 2026 (Yahoo, personal use). Implied vol: CBOE OVX/GVZ/VIX via FRED.
