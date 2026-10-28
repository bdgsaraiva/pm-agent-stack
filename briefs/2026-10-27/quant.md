# Tape after the close: 2026-10-27

Computed by code (`pmstack quant tape`): trend legs and CTA flip levels, realised and implied vol, correlation regime, positioning, half-month seasonality, front curve. Descriptive only: nothing here is a signal. Method: `docs/research/quant.md`.

## What changed

- Trend legs that flipped today: HO=F:21, NG=F:21, NG=F:63, GC=F:63, HG=F:21, ZC=F:63, ES=F:21
- Stretched legs (distance to flip beyond 2 sd and the 95th/5th percentile of its history since 2000; a print rule, base rate not studied): ZC=F:21
- Vol rising fast (21-day vol at least 1.5x the 63-day): none
- Vol in the extreme regime (at or above the 95th percentile of its full history): none
- Implied-minus-realised gap outside its 3-year 10-90 band: BZ=F, CL=F
- Correlation outside its 3-year 10-90 band: BZ=F~ES=F, CL=F~ES=F, RB=F~ES=F, HO=F~ES=F, HO=F~DX-Y.NYB, GC=F~ES=F
- Positioning at a 3-year extreme (CFTC, from the Friday release): RB=F, NG=F, SB=F
- Large moves vs recent vol (1-day or 5-day beyond 2 trailing sd): HO=F, NG=F
- Average pairwise 63-day correlation across 12 commodity markets: 0.09 (percentile 1 of the last 3 years)
- Measured by the testing gate (research/index.md): a8_crowded_adverse_v1 no edge; a8_crowded_entry_v1 no edge; a8_cta_correction_v1 no edge; a8_cta_panic_v1 no edge; a8_cta_panic_v2 no edge; a8_cta_rebound_v1 no edge; a8_cta_rolloff_v1 no edge; a8_cta_vol_shrinking_v1 no edge; p_tsmom_mop2012_v1 no edge. Stretched and flipped are print rules with no study yet.
- Since the 2026-10-26 tape: newly stretched none; no longer stretched SI=F:21, ZW=F:21

## Markets

| Market | Close | 1d % | Trend 1m / 3m / 12m (flip; distance sd) | State | Vol 21d (3y pctile; regime) | 21d/63d | Implied - realised (gap pctile) | MM % OI (pctile) | Carry ann. % | Next half-month norm: median % [IQR] (years) |
|---|---|---|---|---|---|---|---|---|---|---|
| [Brent](https://finance.yahoo.com/quote/BZ=F) | 111.09 | -4.08 | + 105.28 (+2.1) / + 90.74 (+8.0) / + 65.94 (+20.6) | aligned | 33.4 (58; normal) | 0.82 | +29.4 (98) | - (-) | +52.1 | -1.03 [-5.2, +1.4] (19) |
| [WTI](https://finance.yahoo.com/quote/CL=F) | 101.22 | -0.53 | + 92.6 (+3.3) / + 84.46 (+6.8) / + 61.5 (+18.6) | aligned | 38.4 (67; normal) | 0.92 | +20.4 (97) | 2.0 (14) | +22.2 | -1.87 [-5.9, +1.4] (26) |
| [RBOB](https://finance.yahoo.com/quote/RB=F) | 3.0883 | -4.05 | - 3.3377 (-2.9) / - 3.3978 (-3.5) / + 1.9227 (+17.6) | correction | 32.5 (50; normal) | 0.75 | - (-) | 27.8 (99) | +27.9 | -2.40 [-8.2, +0.2] (25) |
| [ULSD](https://finance.yahoo.com/quote/HO=F) | 4.6063 | -6.22 | -! 4.7553 (-1.1) / + 4.3701 (+1.9) / + 2.4031 (+23.4) | correction | 49.6 (84; high) | 1.08 | - (-) | 4.9 (61) | +43.6 | -2.67 [-6.8, +3.9] (26) |
| [Henry Hub](https://finance.yahoo.com/quote/NG=F) | 3.056 | +17.45 | +! 3 (+0.7) / +! 2.725 (+4.3) / - 3.304 (-2.9) | rebound | 71.5 (65; normal) | 1.35 | - (-) | -9.2 (1) | -141.0 | -4.60 [-10.3, +4.1] (26) |
| [Gold](https://finance.yahoo.com/quote/GC=F) | 4058.9 | +0.51 | - 4168.4 (-2.0) / +! 4036.3 (+0.4) / - 4137.8 (-1.5) | aligned | 15.1 (34; normal) | 0.73 | +4.4 (79) | 25.9 (33) | - | +0.69 [-1.3, +2.9] (26) |
| [Silver](https://finance.yahoo.com/quote/SI=F) | 54.293 | +0.34 | - 61.22 (-5.3) / - 57.863 (-2.8) / + 48.377 (+5.1) | correction | 33.8 (57; normal) | 0.95 | - (-) | - (-) | - | +1.54 [-2.3, +4.7] (26) |
| [COMEX copper](https://finance.yahoo.com/quote/HG=F) | 6.622 | +1.75 | +! 6.566 (+0.6) / + 6.2735 (+4.1) / + 5.0935 (+20.1) | aligned | 18.5 (24; normal) | 0.87 | - (-) | 14.6 (49) | - | +0.25 [-3.4, +4.0] (26) |
| [Corn](https://finance.yahoo.com/quote/ZC=F) | 450 | -1.10 | -* 523 (-9.5) / +! 449 (+0.1) / + 423.25 (+3.9) | correction | 22.1 (63; normal) | 0.89 | - (-) | 9.0 (79) | - | -0.27 [-3.4, +1.4] (26) |
| [Soybeans](https://finance.yahoo.com/quote/ZS=F) | 1243.5 | +0.18 | - 1288.25 (-3.3) / + 1178 (+5.1) / + 1041.75 (+16.6) | correction | 10.7 (3; low) | 0.64 | - (-) | 20.2 (89) | - | +1.36 [-0.5, +4.8] (26) |
| [Wheat](https://finance.yahoo.com/quote/ZW=F) | 611.75 | -0.69 | - 688.75 (-6.5) / - 660.75 (-4.2) / + 512.5 (+9.7) | correction | 19.8 (15; low) | 0.67 | - (-) | - (-) | - | -1.23 [-4.0, +0.8] (26) |
| [Sugar](https://finance.yahoo.com/quote/SB=F) | 19.2 | +0.52 | + 17.46 (+4.1) / + 14.5 (+12.2) / + 14.97 (+10.8) | aligned | 44.8 (99; high) | 1.25 | - (-) | 21.9 (99) | - | -0.09 [-3.6, +3.2] (26) |
| [S&P 500 e-mini](https://finance.yahoo.com/quote/ES=F) | 7753.5 | +0.51 | +! 7746.75 (+0.1) / + 7351.25 (+7.7) / + 6827 (+18.5) | aligned | 9.8 (18; normal) | 0.88 | +8.4 (87) | - (-) | - | +1.56 [-0.2, +2.8] (26) |
| [Nasdaq 100 e-mini](https://finance.yahoo.com/quote/NQ=F) | 29850.8 | +1.40 | - 30566.2 (-2.0) / + 27342 (+7.6) / + 25509.2 (+13.5) | correction | 19.2 (65; normal) | 0.99 | - (-) | - (-) | - | +1.55 [-0.8, +4.0] (26) |
| [US 10y note](https://finance.yahoo.com/quote/ZN=F) | 105.891 | -0.21 | + 104.484 (+4.2) / - 108.781 (-8.4) / - 113.438 (-21.6) | rebound | 5.6 (71; normal) | 1.11 | - (-) | - (-) | - | -0.09 [-0.9, +0.7] (26) |
| [US dollar index](https://finance.yahoo.com/quote/DX-Y.NYB) | 102.408 | +0.44 | + 101.2 (+4.1) / + 100.8 (+5.4) / + 98.95 (+11.8) | aligned | 4.8 (25; low) | 0.98 | - (-) | - (-) | - | -0.01 [-1.3, +1.5] (40) |

Legend: `!` flipped today, `*` stretched. Seasonality: a norm (median and interquartile range of the next half-month in earlier years), descriptive and never a signal; 24 buckets, so about one clears 5% by chance. Implied vol: OVX is options on the USO ETF and GVZ on GLD, not on the futures; implied above realised is the normal state. Prices are Yahoo continuous front months: 3- and 12-month flip levels can sit on an expired contract and roll gaps enter vol and seasonal norms. Curve and carry from contracts collected since 24 Oct 2026 (Yahoo, personal use). Implied vol: CBOE OVX/GVZ/VIX via FRED.
