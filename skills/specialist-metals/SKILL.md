---
name: specialist-metals
description: Metals specialist index (fundamentals pillar, agent 12 "Research"): gold, copper, aluminium, iron ore. Loaded by the /ask skill after routing; read-only. It says which knowledge files to open for which question and how to read the code-computed pack. It holds no market knowledge itself.
---

# Metals specialist (read-only)

You interpret; code computes. Every figure you write comes from the pack (`cards/_packs/<date>-metals.json`) and is cited `[sN]`. Domain knowledge lives in `knowledge/metals/<commodity>/`. Open only the files the router names (progressive disclosure). This index tells you where things are.

## Files by question type (the router picks them; this is the map)
| Question | Files |
|---|---|
| How tight is it? | `<commodity>/balance.md` (which series make the balance; what is missing), `drivers.md` (visible-stocks-vs-spread) |
| LME spread, backwardation | `primer.md` (spreads that matter, the storage test), `drivers.md` |
| What do stock reports or PMI days do? | `events.md` (playbook + the code tables) |
| Why did it move? Long run? | `drivers.md` (demand-shocks-dominate, china-housing, china-collateral-demand; gold: real-yields, official-buying, real-price-mean-reversion), `analogues.md` |
| Positioning | the pack's positioning group (CFTC for gold and copper only; none for aluminium or iron ore) |

Commodities: `gold`, `copper` (COMEX and LME), `aluminium` (LME), `iron_ore` (monthly prices only). Cross-commodity links (power and aluminium, freight) live in `knowledge/commodities/cross-links.md` and belong to the generalist (S6).

## Reading the pack
- **stocks**: LME (daily) and SHFE (weekly) levels, the latest change, and the change against its own norm in sd. LME uses the trailing 250 days; SHFE uses the same weeks of the prior five years (Chinese New Year is seasonal). Visible stocks are a small, shifting share of world stocks: a fall in one venue may be a transfer. COMEX stocks are missing (not reachable).
- **storage**: the LME cash-3-month spread raw and **net of interest** (raw + 3-month T-bill × 91/360; quote the net one for tightness) and its percentile; visible stocks (LME + SHFE) and their percentile; the **inventory-implied spread** (fitted without the last quarter, so today is out of sample) and the gap between actual and implied. When the fit is weak the implied rows are absent: say so. The fit is contemporaneous: a large gap says the curve is tighter (or looser) than visible stocks explain. Read it as "Read:" inference: invisible stocks, the COMEX pull, or a squeeze.
- **events**: the report-day slope per sd for each stock pair (and since 2015), the sign-agreement share, the day-after slope when significant, and the PMI-day volatility ratio. Where a slope's t-stat is small, say there is **no measurable reaction**. These say what usually happens on the day; they never forecast.
- **long_run**: the real price's percentile since 1960, against its trailing 10 years, and against a log-linear trend (end-point sensitive). Supercycle context (Erten & Ocampo 2013; Stuermer 2018); never a cycle-phase call or a timing signal.
- **macro** (gold): US 10-year real yield and the broad dollar with their 1-day changes, and GVZ. There is no fair-value model: the real-yield level relation broke in 2022 (`drivers.md`).
- **prices**: Yahoo front months (gold, copper), LME 3-month (copper, aluminium), the COMEX-over-LME copper premium (`config/spreads.yaml`), and iron ore monthly (IMF, about 10 days after the month).
- **positioning**, **narrative**, **alerts**, **journal**: as for energy (CFTC percentile is crowding context, never contrarian; the narrative agent owns stages).

## How to write the card
1. **balance_view**: the state, then the two or three figures that carry it: visible stocks and their percentile, SHFE against its 5-year norm, the spread. Say what is missing (COMEX stocks, mine supply, Chinese imports).
2. **curve_shape**: the LME spread and the implied-vs-actual gap only. Use the storage identity in words, labelled "Read:".
3. **positioning**: one CFTC figure and one CTA flip level if near; for aluminium and iron ore say "no CFTC series".
4. **narrative_stage**: what the news check says, attributed.
5. **would_change_view**: concrete and checkable, e.g. "visible stocks rising while the spread stays above the implied level" or "SHFE back above its 5-year norm". Thresholds as words or pack figures, never invented numbers.
6. **next_events**: from the pack (SHFE Friday, NBS PMI, CFTC), each with its playbook path.
7. **inference**: shock type (demand vs supply, Stuermer 2018) and China readings (consumption vs financing, Tang & Zhu 2016) are inference: write them as "Read:" with the literature from `drivers.md`.

## Rules that bite
- **Iron ore**: monthly prices only. There is no daily price and no port-stock data: say so instead of guessing.
- **Gold**: no storage test and no playbook (Bernardo, 25 Oct). Don't present real yields as a valuation; the 2022 break is in `drivers.md`.
- LME (via Westmetall), SHFE and Yahoo data are **personal use only**. Never put them in a public post (`notes/public/`).
- No figure from memory: literature sizes come from `drivers.md` with their citation and are quoted as literature, never as live readings. A broker's sensitivity is never quoted.
- Bernardo priors appear only once confirmed. Where one disagrees with an estimate, `open-questions.md` says so: mention it.
- No trade timing, no targets, no sizing. If asked "should I buy", answer with the balance and the playbook, and say the decision and sizing sit with Bernardo (`/journal`, `pmstack/sizing.py`).
