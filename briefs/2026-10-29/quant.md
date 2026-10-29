# Tape after the close: 2026-10-29

Computed by code (`pmstack quant tape`): trend legs and CTA flip levels, realised and implied vol, correlation regime, positioning, half-month seasonality, front curve. Descriptive only: nothing here is a signal. Method: `docs/research/quant.md`.

## What changed

- Trend legs that flipped today: ES=F:21
- Stretched legs (distance to flip beyond 2 sd and the 95th/5th percentile of its history since 2000; a print rule, base rate not studied): ZN=F:21
- Vol rising fast (21-day vol at least 1.5x the 63-day): none
- Vol in the extreme regime (at or above the 95th percentile of its full history): none
- Implied-minus-realised gap outside its 3-year 10-90 band: BZ=F, CL=F, GC=F
- Correlation outside its 3-year 10-90 band: BZ=F~ES=F, CL=F~ES=F, HO=F~DX-Y.NYB, SI=F~ES=F
- Positioning at a 3-year extreme (CFTC, from the Friday release): RB=F, NG=F, SB=F
- Large moves vs recent vol (1-day or 5-day beyond 2 trailing sd): NQ=F, ZN=F
- Average pairwise 63-day correlation across 12 commodity markets: 0.1 (percentile 1 of the last 3 years)
- Measured by the testing gate (research/index.md): a8_crowded_adverse_v1 no edge; a8_crowded_entry_v1 no edge; a8_cta_correction_v1 no edge; a8_cta_panic_v1 no edge; a8_cta_panic_v2 no edge; a8_cta_rebound_v1 no edge; a8_cta_rolloff_v1 no edge; a8_cta_vol_shrinking_v1 no edge; p_tsmom_mop2012_v1 no edge. Stretched and flipped are print rules with no study yet.
- Since the 2026-10-28 tape: newly stretched ZN=F:21; no longer stretched ZC=F:21, ZW=F:21

## Markets

| Market | Close | 1d % | Trend 1m / 3m / 12m (flip; distance sd) | State | Vol 21d (3y pctile; regime) | 21d/63d | Implied - realised (gap pctile) | MM % OI (pctile) | Carry ann. % | Next half-month norm: median % [IQR] (years) |
|---|---|---|---|---|---|---|---|---|---|---|
| [Brent](https://finance.yahoo.com/quote/BZ=F) | 111.54 | -3.28 | + 103.53 (+3.4) / + 90.12 (+9.6) / + 64.4 (+24.8) | aligned | 31.3 (53; normal) | 0.78 | +30.2 (99) | - (-) | +44.1 | -1.03 [-5.2, +1.4] (19) |
| [WTI](https://finance.yahoo.com/quote/CL=F) | 102.86 | +0.08 | + 90.42 (+5.2) / + 84.67 (+7.9) / + 60.15 (+21.6) | aligned | 37.3 (63; normal) | 0.89 | +21.3 (97) | 2.0 (14) | +23.4 | -1.87 [-5.9, +1.4] (26) |
| [RBOB](https://finance.yahoo.com/quote/RB=F) | 3.1011 | -2.28 | - 3.4378 (-4.2) / - 3.2216 (-1.6) / + 1.9252 (+19.5) | correction | 25.5 (25; low) | 0.60 | - (-) | 27.8 (99) | +29.3 | -2.40 [-8.2, +0.2] (25) |
| [ULSD](https://finance.yahoo.com/quote/HO=F) | 4.584 | -4.80 | - 4.9569 (-2.9) / + 4.1215 (+4.0) / + 2.3872 (+24.6) | correction | 46.8 (80; high) | 1.05 | - (-) | 4.9 (61) | +34.8 | -2.67 [-6.8, +3.9] (26) |
| [Henry Hub](https://finance.yahoo.com/quote/NG=F) | 2.905 | +3.12 | - 3.026 (-1.5) / + 2.747 (+2.0) / - 3.345 (-5.1) | aligned | 48.6 (23; normal) | 1.11 | - (-) | -9.2 (1) | -162.2 | -4.60 [-10.3, +4.1] (26) |
| [Gold](https://finance.yahoo.com/quote/GC=F) | 4033.3 | -0.45 | - 4186.7 (-2.8) / - 4107 (-1.4) / + 3983.1 (+1.0) | correction | 15.4 (35; normal) | 0.75 | +7.5 (95) | 25.9 (33) | - | +0.69 [-1.3, +2.9] (26) |
| [Silver](https://finance.yahoo.com/quote/SI=F) | 52.22 | -2.31 | - 60.098 (-6.3) / - 57.591 (-4.4) / + 47.125 (+4.6) | correction | 34.5 (59; normal) | 0.97 | - (-) | - (-) | - | +1.54 [-2.3, +4.7] (26) |
| [COMEX copper](https://finance.yahoo.com/quote/HG=F) | 6.5895 | -0.78 | + 6.559 (+0.4) / + 6.436 (+1.8) / + 5.1405 (+19.1) | aligned | 18.7 (25; normal) | 0.91 | - (-) | 14.6 (49) | - | +0.25 [-3.4, +4.0] (26) |
| [Corn](https://finance.yahoo.com/quote/ZC=F) | 451.25 | -0.11 | - 500.75 (-6.6) / + 440.75 (+1.5) / + 432 (+2.8) | correction | 18.9 (38; normal) | 0.76 | - (-) | 9.0 (79) | - | -0.27 [-3.4, +1.4] (26) |
| [Soybeans](https://finance.yahoo.com/quote/ZS=F) | 1234.5 | +0.82 | - 1293 (-4.4) / + 1172 (+4.9) / + 1078.25 (+12.7) | correction | 11.0 (4; low) | 0.66 | - (-) | 20.2 (89) | - | +1.36 [-0.5, +4.8] (26) |
| [Wheat](https://finance.yahoo.com/quote/ZW=F) | 603.25 | +0.71 | - 675.75 (-6.3) / - 639.25 (-3.2) / + 529 (+7.2) | correction | 19.3 (13; low) | 0.67 | - (-) | - (-) | - | -1.23 [-4.0, +0.8] (26) |
| [Sugar](https://finance.yahoo.com/quote/SB=F) | 19.52 | +0.93 | + 17.63 (+4.5) / + 14.66 (+12.5) / + 14.37 (+13.4) | aligned | 44.2 (99; high) | 1.24 | - (-) | 21.9 (99) | - | -0.09 [-3.6, +3.2] (26) |
| [S&P 500 e-mini](https://finance.yahoo.com/quote/ES=F) | 7710 | -0.94 | -! 7715.5 (-0.1) / + 7519.25 (+4.0) / + 6925.75 (+17.1) | correction | 10.4 (24; normal) | 0.96 | +7.0 (79) | - (-) | - | +1.56 [-0.2, +2.8] (26) |
| [Nasdaq 100 e-mini](https://finance.yahoo.com/quote/NQ=F) | 29218.2 | -2.54 | - 30698.8 (-4.6) / + 28404.2 (+2.6) / + 26163.5 (+10.3) | correction | 20.9 (72; normal) | 1.10 | - (-) | - (-) | - | +1.55 [-0.8, +4.0] (26) |
| [US 10y note](https://finance.yahoo.com/quote/ZN=F) | 106.531 | +0.69 | +* 104.203 (+7.1) / - 108 (-4.4) / - 113.469 (-20.3) | rebound | 5.9 (77; normal) | 1.15 | - (-) | - (-) | - | -0.09 [-0.9, +0.7] (26) |
| [US dollar index](https://finance.yahoo.com/quote/DX-Y.NYB) | 101.92 | -0.26 | + 101.45 (+1.6) / + 99.8 (+7.2) / + 98.69 (+11.0) | aligned | 4.9 (28; low) | 1.06 | - (-) | - (-) | - | -0.01 [-1.3, +1.5] (40) |

Legend: `!` flipped today, `*` stretched. Seasonality: a norm (median and interquartile range of the next half-month in earlier years), descriptive and never a signal; 24 buckets, so about one clears 5% by chance. Implied vol: OVX is options on the USO ETF and GVZ on GLD, not on the futures; implied above realised is the normal state. Prices are Yahoo continuous front months: 3- and 12-month flip levels can sit on an expired contract and roll gaps enter vol and seasonal norms. Curve and carry from contracts collected since 24 Oct 2026 (Yahoo, personal use). Implied vol: CBOE OVX/GVZ/VIX via FRED.
