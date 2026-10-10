---
title: Sizing assistant — literature review
agent: 4 (sizing)
date: 2026-10-09
status: reviewed before build; code in pmstack/sizing.py, parameters in config/journal.yaml
---

# Sizing assistant — literature review

**Why this agent.** Bernardo named his biggest leak as *sizing too small on his best ideas*. The goal is Sharpe 1.5+ over three years. Sizing is the one pillar where a rule, applied the same way every time, beats feel, and where his own record (conviction, payoff, outcome) becomes the edge once it builds up.

**Rule for every agent:** read the most cited papers, the Atlas and the specialist books first; write down what changes in the design; then build.

## 1. Papers

| Source | Finding | What it changes |
|---|---|---|
| Kelly (1956); Thorp | Growth-optimal stake f* = p − (1−p)/b. Thorp used fractions of it in practice. | Core formula, used for *relative* size between ideas. |
| MacLean, Thorp & Ziemba (2010), *Quantitative Finance* | Never bet more than Kelly: at twice Kelly, growth falls to the risk-free rate. Fractional Kelly trades growth for lower drawdown risk. Kelly bets can be very large. | Hard cap; an **oversized** flag. |
| Baker & McHale (2013), *Decision Analysis* | When p is estimated, not known, the optimal bet shrinks below Kelly. | A stated P(win) is blended 50/50 with the record; the record is shrunk toward a prior. |
| Haghani & Dewey (2016) | 61 finance-trained people with a 60% coin, $25 to start, cap $250: 28% went bust, 21% reached the cap, average payout $91. Bets were erratic; 18 went all-in; only 5 knew Kelly. | Size by rule, not feel; record suggested vs taken. |
| Haghani & White, *The Missing Billionaires* (2023) | Sizing decides outcomes; required return rises with the square of risk; use Kelly or a fraction of it. | Same as above; a drawdown rule. |
| Antón, Cohen & Polk, "Best Ideas" | Managers' best ideas beat the market and their other holdings by about 2.8–4.5%/yr; most other holdings show no significant outperformance. Over-diversification comes from career risk, asset gathering, regulation and investor behaviour. | Size best ideas up: **undersized-vs-suggestion** flag at conviction 4–5. |
| Lamont (Acadian, 2025) | The best-ideas result comes from diversified portfolios; most evidence says concentrated portfolios do *not* earn higher alpha. | Concentrate risk in best ideas **inside** a diversified book; correlation cut. |
| Akepanidtaworn, Di Mascio, Imas & Schmidt (2023), *Journal of Finance* | Institutional PMs' buys beat a random counterfactual; their sells underperform it. Attention goes to buying; selling uses a crude heuristic. | **Exit review**: what each closed idea did after the exit, up to its horizon. |
| Moreira & Muir (2017), *Journal of Finance* | Cutting exposure when volatility is high raises factor Sharpe ratios in-sample. | — |
| Cederburg, O'Doherty, Wang & Yan (2020), *JFE* | Across 103 equity strategies, real-time volatility-managed versions generally do *not* beat the unmanaged ones. | Volatility normalises risk; it is not a timing signal. |
| Harvey et al. (2018), Man Group | Volatility targeting raises Sharpe for equities and credit, negligibly for bonds, commodities and FX; it reduces left-tail events in all. | Stop distance measured in daily std devs (**stop-in-noise**); no vol-timing overlay on commodities. |
| Tetlock, *Superforecasting* | Calibration is measurable (Brier score) and improves with a tracked record. | **Brier score** by conviction in the sizing review. |
| Peters (2019), *Nature Physics* | Wealth compounds over time, not across parallel worlds: time-average growth, not expected value, is what an investor lives through. | Avoid the ruin path: drawdown cut. |

## 2. Specialist books (from general knowledge; not page-checked)

- **Ralph Vince, optimal f** — the growth-optimal fraction comes with brutal drawdowns, so practitioners trade well below it.
- **Van Tharp** — R-multiples and expectancy (already the journal's unit).
- **Robert Carver, *Systematic Trading*** — forecasts are scaled and capped (at 2× the average); half Kelly at most. His "semi-automatic trader" makes the call and lets a framework size it. *This is the model here.*
- **Marcos López de Prado, *Advances in Financial Machine Learning*, ch. 10** — size from predicted probability; discretise the size so small changes don't cause trades.
- **Grinold & Kahn** — information ratio ≈ skill × √breadth: many independent bets beat a few correlated ones.
- **Annie Duke, *Thinking in Bets*** — judge the decision, not the outcome (the journal's process score).
- **Mark Spitznagel, *Safe Haven*** — avoid the large loss that compounds against you.
- **Brent Donnelly, *Trade Outside the Box*** — bet sizing as a skill on its own, from poker.

## 3. What the Atlas investors do

- **Size hard when right:** Druckenmiller ("sizing up hard when you are right and cutting quickly when you are wrong"), Soros ("go for the jugular"), Rokos (size up only at high conviction), Tepper (size up when policy removes the downside), Stuhlberger (few large positions).
- **Cut after losses:** Tudor Jones, Howard ("conviction is not a waiver"; limits cut after drawdowns), Platt and Englander (hard stop-outs per team), Haidar (−43% needs +75% to recover).
- **Decide the exit first:** Kovner — the stop sits where the idea is proven wrong.
- **Size by risk, limit correlation:** Parker (equal risk per position), the Turtles (fixed fractional risk; limits on correlated units).
- **Fractions, survival:** Thorp (fractional Kelly), Jakurski (survival first, size by probabilities).
- **Atlas 3.1:** sizing and asymmetry beat hit rate; good traders are right 50–55% of the time.

## 4. Where the sources disagree, and the resolution

- **Concentration.** Best Ideas vs Lamont → concentrate *risk* in the best ideas, keep breadth in the book; correlation cut.
- **Volatility.** Moreira & Muir vs Cederburg et al. and Harvey et al. → use volatility to normalise risk and spot stops in the noise, not to time.
- **Kelly.** Growth-optimal vs ruin → Kelly only for relative size; the absolute risk per unit is far below even half Kelly (for the reference idea, full Kelly is 25% of capital at risk), so the binding limits are the cap and the drawdown rule.

## 5. Design changes from the draft

| Rule | Draft | Now | Source |
|---|---|---|---|
| Cap | 3.0 units | **2.0 units** | Carver; MacLean, Thorp & Ziemba |
| Steps | continuous | **0.25 units; below 0.25 = pass** | López de Prado |
| Stated P(win) | used raw | **blended 50/50 with the record** | Baker & McHale; Tetlock |
| Losses | — | **paper drawdown ≥ 4R in 60 days halves sizes** | Tudor Jones, Howard, Platt; Peters |
| Over-sizing | — | **flag above 1.25× suggestion or the cap** | MacLean, Thorp & Ziemba |
| Under-sizing | below own median | **also below 0.75× suggestion at conviction 4–5** | Best Ideas; his stated leak |
| Exits | — | **R the idea added after exit, to horizon** | Akepanidtaworn et al. |
| Calibration | — | **Brier score; hit rate vs prior by conviction** | Tetlock |
| Volatility | stop in sd flagged | unchanged; no vol timing | Cederburg et al.; Harvey et al. |

**Stays human:** the final size, the risk budget behind one unit, and every override. The journal records both numbers so the review can show, in R, whether overriding paid.

## Sources

- MacLean, Thorp & Ziemba, "Good and bad properties of the Kelly criterion": https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf
- Baker & McHale (2013): https://pubsonline.informs.org/doi/fpi/10.1287/deca.2013.0271
- Haghani & Dewey (2016): https://papers.ssrn.com/abstract=2856963
- Haghani & White, *The Missing Billionaires*: https://en.wikipedia.org/wiki/The_Missing_Billionaires
- Antón, Cohen & Polk, "Best Ideas" (summary): https://alphatheory.com/blog/best-ideas-update
- Lamont (Acadian, 2025): https://www.acadian-asset.com/investment-insights/equities/concentrated-portfolio-managers
- Akepanidtaworn et al., "Selling Fast and Buying Slow": https://nber.org/papers/w29076
- Moreira & Muir, "Volatility Managed Portfolios": https://www.nber.org/papers/22208
- Cederburg et al. (2020): https://experts.arizona.edu/en/publications/on-the-performance-of-volatility-managed-portfolios/
- Harvey et al., "The Impact of Volatility Targeting": https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf
- Carver, *Systematic Trading* (notes): https://www.cxoadvisory.com/big-ideas/a-few-notes-on-systematic-trading
- Peters (2019): https://www.exploring-economics.org/en/discover/the-ergodicity-problem-in-economics/
- Atlas investor cards: https://claude.ai/artifact/3DGdbccsP5mrFLt7BzpHcr
