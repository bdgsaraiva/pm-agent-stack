# Tape after the close: 2026-10-24

Computed by code (`pmstack quant tape`): trend legs and CTA flip levels, realised and implied vol, correlation regime, positioning, half-month seasonality, front curve. Descriptive only: nothing here is a signal. Method: `docs/research/quant.md`.

**No new close for most markets today (holiday or failed fetch): flips and big moves are suppressed.**

## What changed

- Trend legs that flipped today: none
- Stretched legs (distance to flip beyond 2 sd and the 95th/5th percentile of its history since 2000; a print rule, base rate not studied): none
- Vol rising fast (21-day vol at least 1.5x the 63-day): none
- Vol in the extreme regime (at or above the 95th percentile of its full history): none
- Implied-minus-realised gap outside its 3-year 10-90 band: none
- Correlation outside its 3-year 10-90 band: none
- Positioning at a 3-year extreme (CFTC, from the Friday release): none
- Large moves vs recent vol (1-day or 5-day beyond 2 trailing sd): none
- Average pairwise 63-day correlation across 12 commodity markets: 0.09 (percentile 1 of the last 3 years)
- Measured by the testing gate (research/index.md): a8_crowded_adverse_v1 no edge; a8_crowded_entry_v1 no edge; a8_cta_correction_v1 no edge; a8_cta_panic_v1 no edge; a8_cta_panic_v2 no edge; a8_cta_rebound_v1 no edge; a8_cta_rolloff_v1 no edge; a8_cta_vol_shrinking_v1 no edge; p_tsmom_mop2012_v1 no edge. Stretched and flipped are print rules with no study yet.
- Since the 2026-10-23 tape: newly stretched none; no longer stretched SB=F:63, SI=F:21, ZC=F:21

## Markets

| Market | Close | 1d % | Trend 1m / 3m / 12m (flip; distance sd) | State | Vol 21d (3y pctile; regime) | 21d/63d | Implied - realised (gap pctile) | MM % OI (pctile) | Carry ann. % | Next half-month norm: median % [IQR] (years) |
|---|---|---|---|---|---|---|---|---|---|---|
| [Brent](https://finance.yahoo.com/quote/BZ=F) | 116.72 | +3.14 | + 106.6 (+3.6) / + 88.36 (+11.0) / + 62.59 (+24.7) | aligned | 30.4 (51; normal) | 0.70 | +24.9 (98) | - (-) | +53.9 | -1.03 [-5.2, +1.4] (19) |
| [WTI](https://finance.yahoo.com/quote/CL=F) | 103.27 | +3.82 | + 94.61 (+3.3) / + 82.61 (+8.5) / + 58.5 (+21.5) | aligned | 38.9 (68; normal) | 0.88 | +17.7 (95) | 2.0 (14) | +27.7 | -1.87 [-5.9, +1.4] (26) |
| [RBOB](https://finance.yahoo.com/quote/RB=F) | 3.2116 | +1.10 | - 3.5646 (-3.8) / - 3.3273 (-1.3) / + 1.865 (+19.8) | correction | 33.9 (56; normal) | 0.79 | - (-) | 27.8 (99) | +31.9 | -2.40 [-8.2, +0.2] (25) |
| [ULSD](https://finance.yahoo.com/quote/HO=F) | 4.9842 | +1.06 | + 4.7303 (+1.8) / + 4.1116 (+6.8) / + 2.2496 (+28.0) | aligned | 44.1 (78; high) | 0.98 | - (-) | 4.9 (61) | +49.4 | -2.67 [-6.8, +3.9] (26) |
| [Henry Hub](https://finance.yahoo.com/quote/NG=F) | 2.64 | -5.58 | -* 3.297 (-8.6) / - 2.767 (-1.8) / - 3.45 (-10.3) | aligned | 46.5 (19; normal) | 1.09 | - (-) | -9.2 (1) | -161.3 | -4.60 [-10.3, +4.1] (26) |
| [Gold](https://finance.yahoo.com/quote/GC=F) | 4007.9 | -1.29 | - 4298 (-5.3) / - 4077 (-1.3) / - 4065.4 (-1.1) | aligned | 19.0 (59; normal) | 0.91 | +5.5 (87) | 25.9 (33) | - | +0.69 [-1.3, +2.9] (26) |
| [Silver](https://finance.yahoo.com/quote/SI=F) | 53.711 | -1.92 | -* 63.457 (-7.3) / - 58.472 (-3.7) / + 47.461 (+5.4) | correction | 37.0 (66; normal) | 1.03 | - (-) | - (-) | - | +1.54 [-2.3, +4.7] (26) |
| [COMEX copper](https://finance.yahoo.com/quote/HG=F) | 6.476 | +1.78 | - 6.7185 (-2.8) / + 6.339 (+1.6) / + 4.961 (+20.0) | correction | 18.6 (25; normal) | 0.88 | - (-) | 14.6 (49) | - | +0.25 [-3.4, +4.0] (26) |
| [Corn](https://finance.yahoo.com/quote/ZC=F) | 456 | -0.98 | -* 527.5 (-9.1) / +! 451.75 (+0.6) / + 423 (+4.7) | correction | 22.2 (64; normal) | 0.88 | - (-) | 9.0 (79) | - | -0.27 [-3.4, +1.4] (26) |
| [Soybeans](https://finance.yahoo.com/quote/ZS=F) | 1256.5 | +0.28 | - 1317.5 (-4.5) / + 1208.5 (+3.7) / + 1034.75 (+18.4) | correction | 12.6 (8; low) | 0.73 | - (-) | 20.2 (89) | - | +1.36 [-0.5, +4.8] (26) |
| [Wheat](https://finance.yahoo.com/quote/ZW=F) | 625 | +0.04 | - 707 (-6.5) / - 660 (-2.9) / + 503.75 (+11.5) | correction | 20.2 (17; low) | 0.69 | - (-) | - (-) | - | -1.23 [-4.0, +0.8] (26) |
| [Sugar](https://finance.yahoo.com/quote/SB=F) | 20.24 | +0.55 | + 17.58 (+6.5) / +* 14.58 (+15.2) / + 15.1 (+13.6) | aligned | 39.0 (92; high) | 1.16 | - (-) | 21.9 (99) | - | -0.09 [-3.6, +3.2] (26) |
| [S&P 500 e-mini](https://finance.yahoo.com/quote/ES=F) | 7659.75 | -0.58 | - 7767 (-2.0) / + 7448.25 (+3.9) / + 6737 (+18.0) | correction | 9.8 (17; normal) | 0.84 | +9.5 (93) | - (-) | - | +1.56 [-0.2, +2.8] (26) |
| [Nasdaq 100 e-mini](https://finance.yahoo.com/quote/NQ=F) | 29117.8 | -0.08 | - 30766.8 (-4.5) / + 28190 (+2.6) / + 25039.2 (+12.3) | correction | 18.1 (55; normal) | 0.93 | - (-) | - (-) | - | +1.55 [-0.8, +4.0] (26) |
| [US 10y note](https://finance.yahoo.com/quote/ZN=F) | 106.156 | -0.23 | + 104.859 (+3.8) / - 108.578 (-6.9) / - 113.797 (-21.4) | rebound | 5.7 (74; normal) | 1.13 | - (-) | - (-) | - | -0.09 [-0.9, +0.7] (26) |
| [US dollar index](https://finance.yahoo.com/quote/DX-Y.NYB) | 101.81 | +0.20 | + 101.29 (+1.7) / + 101.51 (+1.0) / + 98.9 (+9.4) | aligned | 4.8 (25; low) | 0.97 | - (-) | - (-) | - | -0.01 [-1.3, +1.5] (40) |

Legend: `!` flipped today, `*` stretched. Seasonality: a norm (median and interquartile range of the next half-month in earlier years), descriptive and never a signal; 24 buckets, so about one clears 5% by chance. Implied vol: OVX is options on the USO ETF and GVZ on GLD, not on the futures; implied above realised is the normal state. Prices are Yahoo continuous front months: 3- and 12-month flip levels can sit on an expired contract and roll gaps enter vol and seasonal norms. Curve and carry from contracts collected since 24 Oct 2026 (Yahoo, personal use). Implied vol: CBOE OVX/GVZ/VIX via FRED.
