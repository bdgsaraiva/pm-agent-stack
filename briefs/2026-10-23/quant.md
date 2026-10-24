# Tape after the close: 2026-10-23

Computed by code (`pmstack quant tape`): trend legs and CTA flip levels, realised and implied vol, correlation regime, positioning, half-month seasonality, front curve. Descriptive only: nothing here is a signal. Method: `docs/research/quant.md`.

## What changed

- Trend legs that flipped today: NG=F:63, ZC=F:63
- Stretched legs (distance to flip beyond 2 sd and the 95th/5th percentile of its history since 2000; a print rule, base rate not studied): SI=F:21, ZC=F:21, SB=F:63
- Vol rising fast (21-day vol at least 1.5x the 63-day): none
- Vol in the extreme regime (at or above the 95th percentile of its full history): none
- Implied-minus-realised gap outside its 3-year 10-90 band: ES=F
- Correlation outside its 3-year 10-90 band: BZ=F~ES=F, CL=F~ES=F, RB=F~ES=F, HO=F~ES=F, HO=F~DX-Y.NYB, SB=F~DX-Y.NYB
- Positioning at a 3-year extreme (CFTC, from the Friday release): RB=F, NG=F, SB=F
- Large moves vs recent vol (1-day or 5-day beyond 2 trailing sd): NG=F
- Average pairwise 63-day correlation across 12 commodity markets: 0.09 (percentile 1 of the last 3 years)
- Measured by the testing gate (research/index.md): a8_crowded_adverse_v1 no edge; a8_crowded_entry_v1 no edge; a8_cta_correction_v1 no edge; a8_cta_panic_v1 no edge; a8_cta_panic_v2 no edge; a8_cta_rebound_v1 no edge; a8_cta_rolloff_v1 no edge; a8_cta_vol_shrinking_v1 no edge; p_tsmom_mop2012_v1 no edge. Stretched and flipped are print rules with no study yet.

## Markets

| Market | Close | 1d % | Trend 1m / 3m / 12m (flip; distance sd) | State | Vol 21d (3y pctile; regime) | 21d/63d | Implied - realised (gap pctile) | MM % OI (pctile) | Carry ann. % | Next half-month norm: median % [IQR] (years) |
|---|---|---|---|---|---|---|---|---|---|---|
| [Brent](https://finance.yahoo.com/quote/BZ=F) | 111.66 | -1.33 | + 106.6 (+1.8) / + 88.36 (+9.3) / + 62.59 (+22.9) | aligned | 29.4 (50; normal) | 0.68 | - (-) | - (-) | - | -1.03 [-5.2, +1.4] (19) |
| [WTI](https://finance.yahoo.com/quote/CL=F) | 103.44 | +3.99 | + 94.61 (+3.4) / + 82.61 (+8.5) / + 58.5 (+21.6) | aligned | 39.1 (69; normal) | 0.89 | - (-) | 2.0 (14) | - | -1.87 [-5.9, +1.4] (26) |
| [RBOB](https://finance.yahoo.com/quote/RB=F) | 3.1276 | -1.54 | - 3.5646 (-4.8) / - 3.3273 (-2.3) / + 1.865 (+18.9) | correction | 33.6 (55; normal) | 0.79 | - (-) | 27.8 (99) | - | -2.40 [-8.2, +0.2] (25) |
| [ULSD](https://finance.yahoo.com/quote/HO=F) | 4.8039 | -2.60 | + 4.7303 (+0.5) / + 4.1116 (+5.5) / + 2.2496 (+26.7) | aligned | 45.0 (79; high) | 0.99 | - (-) | 4.9 (61) | - | -2.67 [-6.8, +3.9] (26) |
| [Henry Hub](https://finance.yahoo.com/quote/NG=F) | 3.047 | +8.98 | - 3.297 (-3.0) / +! 2.767 (+3.7) / - 3.45 (-4.8) | aligned | 54.2 (33; normal) | 1.22 | - (-) | -9.2 (1) | - | -4.60 [-10.3, +4.1] (26) |
| [Gold](https://finance.yahoo.com/quote/GC=F) | 4010 | -1.24 | - 4298 (-5.2) / - 4077 (-1.2) / - 4065.4 (-1.0) | aligned | 18.9 (59; normal) | 0.91 | - (-) | 25.9 (33) | - | +0.69 [-1.3, +2.9] (26) |
| [Silver](https://finance.yahoo.com/quote/SI=F) | 53.96 | -1.47 | -* 63.457 (-7.1) / - 58.472 (-3.5) / + 47.461 (+5.6) | correction | 36.8 (66; normal) | 1.03 | - (-) | - (-) | - | +1.54 [-2.3, +4.7] (26) |
| [COMEX copper](https://finance.yahoo.com/quote/HG=F) | 6.4975 | +2.12 | - 6.7185 (-2.5) / + 6.339 (+1.9) / + 4.961 (+20.2) | correction | 19.0 (27; normal) | 0.90 | - (-) | 14.6 (49) | - | +0.25 [-3.4, +4.0] (26) |
| [Corn](https://finance.yahoo.com/quote/ZC=F) | 456 | -0.98 | -* 527.5 (-9.1) / +! 451.75 (+0.6) / + 423 (+4.7) | correction | 22.2 (64; normal) | 0.88 | - (-) | 9.0 (79) | - | -0.27 [-3.4, +1.4] (26) |
| [Soybeans](https://finance.yahoo.com/quote/ZS=F) | 1269.5 | +1.32 | - 1317.5 (-3.5) / + 1208.5 (+4.7) / + 1034.75 (+19.4) | correction | 13.6 (20; low) | 0.77 | - (-) | 20.2 (89) | - | +1.36 [-0.5, +4.8] (26) |
| [Wheat](https://finance.yahoo.com/quote/ZW=F) | 625 | +0.04 | - 707 (-6.5) / - 660 (-2.9) / + 503.75 (+11.5) | correction | 20.2 (17; low) | 0.69 | - (-) | - (-) | - | -1.23 [-4.0, +0.8] (26) |
| [Sugar](https://finance.yahoo.com/quote/SB=F) | 20.26 | +0.65 | + 17.58 (+6.6) / +* 14.58 (+15.2) / + 15.1 (+13.6) | aligned | 39.0 (92; high) | 1.16 | - (-) | 21.9 (99) | - | -0.09 [-3.6, +3.2] (26) |
| [S&P 500 e-mini](https://finance.yahoo.com/quote/ES=F) | 7672.5 | -0.42 | - 7767 (-1.7) / + 7448.25 (+4.2) / + 6737 (+18.3) | correction | 9.7 (16; normal) | 0.84 | +9.5 (93) | - (-) | - | +1.56 [-0.2, +2.8] (26) |
| [Nasdaq 100 e-mini](https://finance.yahoo.com/quote/NQ=F) | 29175 | +0.11 | - 30766.8 (-4.3) / + 28190 (+2.8) / + 25039.2 (+12.5) | correction | 18.2 (56; normal) | 0.93 | - (-) | - (-) | - | +1.55 [-0.8, +4.0] (26) |
| [US 10y note](https://finance.yahoo.com/quote/ZN=F) | 106.125 | -0.26 | + 104.859 (+3.7) / - 108.578 (-7.0) / - 113.797 (-21.5) | rebound | 5.8 (75; normal) | 1.13 | - (-) | - (-) | - | -0.09 [-0.9, +0.7] (26) |
| [US dollar index](https://finance.yahoo.com/quote/DX-Y.NYB) | 101.752 | +0.14 | + 101.29 (+1.5) / + 101.51 (+0.8) / + 98.9 (+9.2) | aligned | 4.8 (24; low) | 0.96 | - (-) | - (-) | - | -0.01 [-1.3, +1.5] (40) |

Legend: `!` flipped today, `*` stretched. Seasonality: a norm (median and interquartile range of the next half-month in earlier years), descriptive and never a signal; 24 buckets, so about one clears 5% by chance. Implied vol: OVX is options on the USO ETF and GVZ on GLD, not on the futures; implied above realised is the normal state. Prices are Yahoo continuous front months: 3- and 12-month flip levels can sit on an expired contract and roll gaps enter vol and seasonal norms. Curve and carry from contracts collected since 24 Oct 2026 (Yahoo, personal use). Implied vol: CBOE OVX/GVZ/VIX via FRED.
