# Tape after the close: 2026-10-30

Computed by code (`pmstack quant tape`): trend legs and CTA flip levels, realised and implied vol, correlation regime, positioning, half-month seasonality, front curve. Descriptive only: nothing here is a signal. Method: `docs/research/quant.md`.

## What changed

- Trend legs that flipped today: RB=F:63, HO=F:21, GC=F:252, HG=F:63, ZC=F:63, ES=F:21, ES=F:63, NQ=F:63, DX-Y.NYB:21
- Stretched legs (distance to flip beyond 2 sd and the 95th/5th percentile of its history since 2000; a print rule, base rate not studied): GC=F:21, SI=F:21, NQ=F:21
- Vol rising fast (21-day vol at least 1.5x the 63-day): none
- Vol in the extreme regime (at or above the 95th percentile of its full history): none
- Implied-minus-realised gap outside its 3-year 10-90 band: BZ=F, CL=F, GC=F
- Correlation outside its 3-year 10-90 band: BZ=F~ES=F, CL=F~ES=F, HO=F~DX-Y.NYB, GC=F~ES=F, SI=F~ES=F
- Positioning at a 3-year extreme (CFTC, from the Friday release): RB=F, NG=F, SB=F
- Large moves vs recent vol (1-day or 5-day beyond 2 trailing sd): GC=F, SI=F, ES=F, NQ=F
- Average pairwise 63-day correlation across 12 commodity markets: 0.11 (percentile 3 of the last 3 years)
- Measured by the testing gate (research/index.md): a8_crowded_adverse_v1 no edge; a8_crowded_entry_v1 no edge; a8_cta_correction_v1 no edge; a8_cta_panic_v1 no edge; a8_cta_panic_v2 no edge; a8_cta_rebound_v1 no edge; a8_cta_rolloff_v1 no edge; a8_cta_vol_shrinking_v1 no edge; p_tsmom_mop2012_v1 no edge. Stretched and flipped are print rules with no study yet.
- Since the 2026-10-29 tape: newly stretched GC=F:21, NQ=F:21, SI=F:21; no longer stretched ZN=F:21

## Markets

| Market | Close | 1d % | Trend 1m / 3m / 12m (flip; distance sd) | State | Vol 21d (3y pctile; regime) | 21d/63d | Implied - realised (gap pctile) | MM % OI (pctile) | Carry ann. % | Next half-month norm: median % [IQR] (years) |
|---|---|---|---|---|---|---|---|---|---|---|
| [Brent](https://finance.yahoo.com/quote/BZ=F) | 112.33 | -2.22 | + 102.31 (+4.2) / + 83.77 (+13.3) / + 64.92 (+24.8) | aligned | 29.5 (50; normal) | 0.80 | +28.7 (98) | - (-) | +57.4 | -1.03 [-5.2, +1.4] (19) |
| [WTI](https://finance.yahoo.com/quote/CL=F) | 102.95 | +0.93 | + 92.87 (+4.2) / + 80.34 (+10.0) / + 60.48 (+21.5) | aligned | 36.8 (60; normal) | 0.91 | +19.6 (96) | 1.7 (13) | +21.5 | -1.87 [-5.9, +1.4] (26) |
| [RBOB](https://finance.yahoo.com/quote/RB=F) | 3.1144 | -2.22 | - 3.4026 (-3.6) / +! 2.9667 (+2.0) / + 1.9737 (+18.7) | correction | 25.6 (25; low) | 0.66 | - (-) | 27.4 (97) | +64.0 | -2.40 [-8.2, +0.2] (25) |
| [ULSD](https://finance.yahoo.com/quote/HO=F) | 4.655 | -1.71 | +! 4.642 (+0.1) / + 3.8772 (+6.8) / + 2.4243 (+24.4) | aligned | 38.1 (68; normal) | 0.91 | - (-) | 3.4 (46) | +37.5 | -2.67 [-6.8, +3.9] (26) |
| [Henry Hub](https://finance.yahoo.com/quote/NG=F) | 2.883 | -2.34 | - 2.967 (-1.0) / + 2.781 (+1.3) / - 3.376 (-5.6) | aligned | 50.5 (28; normal) | 1.14 | - (-) | -12.3 (1) | -171.9 | -4.60 [-10.3, +4.1] (26) |
| [Gold](https://finance.yahoo.com/quote/GC=F) | 3884.9 | -3.63 | -* 4202.3 (-6.4) / - 4090.5 (-4.2) / -! 4000.7 (-2.4) | aligned | 19.5 (61; normal) | 0.89 | +7.3 (94) | 26.6 (38) | - | +0.69 [-1.3, +2.9] (26) |
| [Silver](https://finance.yahoo.com/quote/SI=F) | 49.135 | -5.86 | -* 60.725 (-9.7) / - 57.667 (-7.3) / + 47.721 (+1.3) | correction | 38.5 (67; high) | 1.03 | - (-) | - (-) | - | +1.54 [-2.3, +4.7] (26) |
| [COMEX copper](https://finance.yahoo.com/quote/HG=F) | 6.5095 | -1.09 | + 6.482 (+0.3) / -! 6.514 (-0.1) / + 5.2335 (+16.8) | aligned | 18.7 (25; normal) | 0.91 | - (-) | 12.0 (41) | - | +0.25 [-3.4, +4.0] (26) |
| [Corn](https://finance.yahoo.com/quote/ZC=F) | 447.5 | -0.83 | - 502.25 (-7.4) / -! 449.25 (-0.3) / + 434 (+2.0) | correction | 18.7 (35; normal) | 0.76 | - (-) | 4.4 (68) | - | -0.27 [-3.4, +1.4] (26) |
| [Soybeans](https://finance.yahoo.com/quote/ZS=F) | 1234 | +1.17 | - 1284 (-3.7) / + 1168.75 (+5.1) / + 1080.25 (+12.5) | correction | 11.4 (5; low) | 0.68 | - (-) | 19.8 (87) | - | +1.36 [-0.5, +4.8] (26) |
| [Wheat](https://finance.yahoo.com/quote/ZW=F) | 603.25 | -0.08 | - 682.75 (-6.8) / - 651 (-4.2) / + 532.25 (+6.9) | correction | 18.6 (10; low) | 0.65 | - (-) | - (-) | - | -1.23 [-4.0, +0.8] (26) |
| [Sugar](https://finance.yahoo.com/quote/SB=F) | 19.37 | -0.51 | + 18.94 (+1.0) / + 15.01 (+11.1) / + 14.42 (+12.9) | aligned | 36.9 (88; normal) | 1.04 | - (-) | 19.7 (95) | - | -0.09 [-3.6, +3.2] (26) |
| [S&P 500 e-mini](https://finance.yahoo.com/quote/ES=F) | 7614.75 | -1.80 | -! 7724 (-2.3) / -! 7628.25 (-0.3) / + 6922.75 (+15.2) | correction | 11.8 (42; normal) | 1.07 | +7.3 (81) | - (-) | - | +1.56 [-0.2, +2.8] (26) |
| [Nasdaq 100 e-mini](https://finance.yahoo.com/quote/NQ=F) | 28543 | -3.45 | -* 30760.5 (-6.9) / -! 28891.8 (-1.1) / + 26262.5 (+7.7) | correction | 22.7 (81; normal) | 1.17 | - (-) | - (-) | - | +1.55 [-0.8, +4.0] (26) |
| [US 10y note](https://finance.yahoo.com/quote/ZN=F) | 106.641 | +0.43 | + 104.656 (+6.0) / - 108.422 (-5.3) / - 112.906 (-18.1) | rebound | 5.6 (71; normal) | 1.12 | - (-) | - (-) | - | -0.09 [-0.9, +0.7] (26) |
| [US dollar index](https://finance.yahoo.com/quote/DX-Y.NYB) | 101.964 | -0.07 | -! 102.1 (-0.5) / + 99.96 (+6.8) / + 99.22 (+9.3) | correction | 4.3 (10; low) | 0.93 | - (-) | - (-) | - | -0.01 [-1.3, +1.5] (40) |

Legend: `!` flipped today, `*` stretched. Seasonality: a norm (median and interquartile range of the next half-month in earlier years), descriptive and never a signal; 24 buckets, so about one clears 5% by chance. Implied vol: OVX is options on the USO ETF and GVZ on GLD, not on the futures; implied above realised is the normal state. Prices are Yahoo continuous front months: 3- and 12-month flip levels can sit on an expired contract and roll gaps enter vol and seasonal norms. Curve and carry from contracts collected since 24 Oct 2026 (Yahoo, personal use). Implied vol: CBOE OVX/GVZ/VIX via FRED.
