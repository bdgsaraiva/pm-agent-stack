# Time-series momentum (Moskowitz, Ooi & Pedersen 2012) on our futures

Study `p_tsmom_mop2012_v1` · registered 2026-10-19 · spec 00facc548cbbd2bb · as of 2026-10-19 (data through 2026-10-19) · definition b1b6b38fdfb1938c · verdict **no edge**

**Hypothesis (registered).** A 12-month time-series momentum book (sign of the past 12-month return, 40% vol per market, monthly) earns alpha over the long-only book of the same markets after costs, and keeps a positive Sharpe after publication. The 1- and 3-month lookbacks are registered variants and count as trials.

**Source.** Moskowitz, Ooi & Pedersen 2012 (JFE); Hurst, Ooi & Pedersen (costs); Huang, Li, Wang & Zhou 2020 (counterpoint: no better than the historical mean); agent 7's trend vote and agent 8's CTA levels use it

**Strategy.** `tsmom` {"lookbacks": [21, 63, 252], "primary": 252, "markets": ["CL=F", "NG=F", "HO=F", "RB=F", "GC=F", "SI=F", "HG=F", "ZC=F", "ZS=F", "ZW=F", "KC=F", "SB=F", "ES=F", "NQ=F", "ZN=F", "ZT=F", "DX-Y.NYB", "EURUSD=X", "JPY=X"]}; markets: CL=F, NG=F, HO=F, RB=F, GC=F, SI=F, HG=F, ZC=F, ZS=F, ZW=F, KC=F, SB=F, ES=F, NQ=F, ZN=F, ZT=F, DX-Y.NYB, EURUSD=X, JPY=X.

| | value |
|---|---|
| months | 477 (1987-02-27 to 2026-10-19) |
| annual return / vol / Sharpe (AQR costs) | 10.54% / 16.62% / 0.63 |
| alpha vs the long-only book (annual, HAC t, beta) | 6.17% (t 2.21, beta 0.314) |
| alpha vs the historical-mean strategy | 8.23% (t 2.91, beta 0.299) |
| alpha vs S&P 500 futures | 8.88% (t 3.02, beta 0.171) |
| deflated Sharpe (3 trials) | 0.5759 (expected best monthly SR of noise 0.1741; V[SR] floored) |
| probabilistic Sharpe vs 0 | 1.0000 |
| break-even cost | 11.5x the AQR table |
| in paper sample (1987-02-27 to 2009-12-31) | Sharpe 0.77, 275 months |
| after sample before pub (2009-12-31 to 2012-05-01) | Sharpe -0.01, 28 months |
| after publication (2012-05-01 to 2026-10-19) | Sharpe 0.51, 174 months |
| halves (split 2006-12-29) | Sharpe 0.80 · 0.46 |

Variants (all registered, all counted): 21 days: Sharpe 0.17; 63 days: Sharpe 0.34; 252 days: Sharpe 0.63

Cost sweep (x the AQR table): 0x: Sharpe 0.69, alpha t 2.58; 1x: Sharpe 0.63, alpha t 2.21; 2x: Sharpe 0.57, alpha t 1.84; 4x: Sharpe 0.45, alpha t 1.11

**Recall probe (asked before the run).** Before the run: does 12-month TSMOM have a positive Sharpe after 2012 on these markets? Answer: yes, weaker than before (0.6).

**Verdict: no edge.** alpha t 2.21 < 3.0 vs the long-only book; deflated Sharpe 0.5759 < 0.95 (3 trials).

_LLM-in-sample: the whole history precedes the drafting model's boundary 2026-10-16 (the paper and its result are in the model's memory; judge the post-publication period). Data: Outcomes use agent 8's spliced daily returns (Yahoo front-month closes, roll jumps screened against a spot or index proxy where one exists; markets without a proxy keep unadjusted roll days). Before the futures exist, spot and index proxies carry no roll or carry return. Descriptive research, not a signal or a trade instruction; decisions stay with the PM._
