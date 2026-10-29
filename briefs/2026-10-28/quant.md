# Tape after the close: 2026-10-28

Computed by code (`pmstack quant tape`): trend legs and CTA flip levels, realised and implied vol, correlation regime, positioning, half-month seasonality, front curve. Descriptive only: nothing here is a signal. Method: `docs/research/quant.md`.

## What changed

- Trend legs that flipped today: HO=F:21, NG=F:21, NG=F:63, GC=F:63, GC=F:252, ZC=F:63
- Stretched legs (distance to flip beyond 2 sd and the 95th/5th percentile of its history since 2000; a print rule, base rate not studied): ZC=F:21, ZW=F:21
- Vol rising fast (21-day vol at least 1.5x the 63-day): none
- Vol in the extreme regime (at or above the 95th percentile of its full history): none
- Implied-minus-realised gap outside its 3-year 10-90 band: BZ=F, CL=F, GC=F
- Correlation outside its 3-year 10-90 band: BZ=F~ES=F, CL=F~ES=F, RB=F~ES=F, HO=F~ES=F, HO=F~DX-Y.NYB, NQ=F~ES=F
- Positioning at a 3-year extreme (CFTC, from the Friday release): RB=F, NG=F, SB=F
- Large moves vs recent vol (1-day or 5-day beyond 2 trailing sd): NG=F
- Average pairwise 63-day correlation across 12 commodity markets: 0.09 (percentile 1 of the last 3 years)
- Measured by the testing gate (research/index.md): a8_crowded_adverse_v1 no edge; a8_crowded_entry_v1 no edge; a8_cta_correction_v1 no edge; a8_cta_panic_v1 no edge; a8_cta_panic_v2 no edge; a8_cta_rebound_v1 no edge; a8_cta_rolloff_v1 no edge; a8_cta_vol_shrinking_v1 no edge; p_tsmom_mop2012_v1 no edge. Stretched and flipped are print rules with no study yet.
- Since the 2026-10-27 tape: newly stretched ZW=F:21; no longer stretched none

## Markets

| Market | Close | 1d % | Trend 1m / 3m / 12m (flip; distance sd) | State | Vol 21d (3y pctile; regime) | 21d/63d | Implied - realised (gap pctile) | MM % OI (pctile) | Carry ann. % | Next half-month norm: median % [IQR] (years) |
|---|---|---|---|---|---|---|---|---|---|---|
| [Brent](https://finance.yahoo.com/quote/BZ=F) | 110.52 | -2.95 | + 102.59 (+3.2) / + 89.03 (+9.2) / + 65.62 (+22.3) | aligned | 30.8 (52; normal) | 0.77 | +25.2 (97) | - (-) | +44.7 | -1.03 [-5.2, +1.4] (19) |
| [WTI](https://finance.yahoo.com/quote/CL=F) | 102.78 | +2.88 | + 89.38 (+5.4) / + 83.59 (+8.0) / + 61.31 (+19.9) | aligned | 37.3 (63; normal) | 0.89 | +16.4 (94) | 2.0 (14) | +20.6 | -1.87 [-5.9, +1.4] (26) |
| [RBOB](https://finance.yahoo.com/quote/RB=F) | 3.1122 | -0.81 | - 3.2782 (-2.1) / - 3.2847 (-2.2) / + 1.9204 (+19.3) | correction | 30.1 (40; normal) | 0.71 | - (-) | 27.8 (99) | +23.1 | -2.40 [-8.2, +0.2] (25) |
| [ULSD](https://finance.yahoo.com/quote/HO=F) | 4.6433 | -2.76 | -! 4.8979 (-2.0) / + 4.2094 (+3.7) / + 2.4361 (+24.0) | correction | 44.9 (79; high) | 1.02 | - (-) | 4.9 (61) | +37.0 | -2.67 [-6.8, +3.9] (26) |
| [Henry Hub](https://finance.yahoo.com/quote/NG=F) | 3.026 | +12.20 | +! 3.011 (+0.2) / +! 2.758 (+3.4) / - 3.442 (-4.7) | rebound | 60.7 (45; normal) | 1.26 | - (-) | -9.2 (1) | -88.8 | -4.60 [-10.3, +4.1] (26) |
| [Gold](https://finance.yahoo.com/quote/GC=F) | 4054.4 | -0.50 | - 4179.7 (-2.3) / -! 4100.1 (-0.8) / +! 4019.7 (+0.6) | correction | 15.4 (35; normal) | 0.75 | +7.2 (94) | 25.9 (33) | - | +0.69 [-1.3, +2.9] (26) |
| [Silver](https://finance.yahoo.com/quote/SI=F) | 53.457 | -1.54 | - 60.668 (-5.6) / - 58.815 (-4.2) / + 46.562 (+6.1) | correction | 34.0 (57; normal) | 0.95 | - (-) | - (-) | - | +1.54 [-2.3, +4.7] (26) |
| [COMEX copper](https://finance.yahoo.com/quote/HG=F) | 6.6415 | +0.29 | + 6.5435 (+1.1) / + 6.4445 (+2.3) / + 5.1405 (+19.4) | aligned | 18.5 (24; normal) | 0.90 | - (-) | 14.6 (49) | - | +0.25 [-3.4, +4.0] (26) |
| [Corn](https://finance.yahoo.com/quote/ZC=F) | 451.25 | +0.56 | -* 522 (-9.2) / +! 445.75 (+0.8) / + 428.75 (+3.2) | correction | 22.6 (68; normal) | 0.91 | - (-) | 9.0 (79) | - | -0.27 [-3.4, +1.4] (26) |
| [Soybeans](https://finance.yahoo.com/quote/ZS=F) | 1231 | +0.14 | - 1297.75 (-4.9) / + 1177.25 (+4.2) / + 1067.25 (+13.3) | correction | 10.5 (2; low) | 0.63 | - (-) | 20.2 (89) | - | +1.36 [-0.5, +4.8] (26) |
| [Wheat](https://finance.yahoo.com/quote/ZW=F) | 599.25 | -1.80 | -* 692.75 (-8.0) / - 663.5 (-5.6) / + 526 (+7.2) | correction | 19.8 (15; low) | 0.67 | - (-) | - (-) | - | -1.23 [-4.0, +0.8] (26) |
| [Sugar](https://finance.yahoo.com/quote/SB=F) | 19.36 | +0.83 | + 17.82 (+3.6) / + 14.43 (+12.8) / + 14.46 (+12.8) | aligned | 44.5 (99; high) | 1.24 | - (-) | 21.9 (99) | - | -0.09 [-3.6, +3.2] (26) |
| [S&P 500 e-mini](https://finance.yahoo.com/quote/ES=F) | 7744.25 | -0.18 | + 7732 (+0.2) / + 7472.5 (+5.4) / + 6908.25 (+17.1) | aligned | 9.8 (18; normal) | 0.91 | +7.7 (83) | - (-) | - | +1.56 [-0.2, +2.8] (26) |
| [Nasdaq 100 e-mini](https://finance.yahoo.com/quote/NQ=F) | 29515.2 | -1.00 | - 30613.2 (-3.2) / + 28237.8 (+3.8) / + 25963.8 (+11.1) | correction | 19.3 (65; normal) | 1.05 | - (-) | - (-) | - | +1.55 [-0.8, +4.0] (26) |
| [US 10y note](https://finance.yahoo.com/quote/ZN=F) | 106.156 | +0.10 | + 104.422 (+5.2) / - 108.547 (-7.1) / - 113.422 (-21.1) | rebound | 5.5 (67; normal) | 1.10 | - (-) | - (-) | - | -0.09 [-0.9, +0.7] (26) |
| [US dollar index](https://finance.yahoo.com/quote/DX-Y.NYB) | 102.124 | -0.19 | + 101.37 (+2.5) / + 100.01 (+7.1) / + 98.78 (+11.3) | aligned | 4.8 (25; low) | 1.04 | - (-) | - (-) | - | -0.01 [-1.3, +1.5] (40) |

Legend: `!` flipped today, `*` stretched. Seasonality: a norm (median and interquartile range of the next half-month in earlier years), descriptive and never a signal; 24 buckets, so about one clears 5% by chance. Implied vol: OVX is options on the USO ETF and GVZ on GLD, not on the futures; implied above realised is the normal state. Prices are Yahoo continuous front months: 3- and 12-month flip levels can sit on an expired contract and roll gaps enter vol and seasonal norms. Curve and carry from contracts collected since 24 Oct 2026 (Yahoo, personal use). Implied vol: CBOE OVX/GVZ/VIX via FRED.
