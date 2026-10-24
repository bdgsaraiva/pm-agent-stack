# Relative trades (two-leg ideas) — 24 Oct 2026

Bernardo asked for full support of relative trades after logging long COMEX Dec26 / short LME Dec26 copper at 0.5R.
Before this change a `relative` idea could be written to the journal but no agent priced it: no R, no size
suggestion, no critic card, no risk or stress row. Build: `pmstack/spreads.py`, `config/spreads.yaml`,
`pmstack/adapters/westmetall.py`, `pmstack/adapters/spread.py`, `config/sources.d/spreads.yaml`.

| Finding | What it changes | Source |
|---|---|---|
| COMEX copper (HG) trades 25,000 lb, quoted in USD (and cents) per pound; LME copper trades 25 t lots, quoted in USD per tonne. 1 t = 2,204.62262 lb. | Legs are converted to USD/t before the ratio; a stored COMEX price above 50 is read as cents and divided by 100. | CME HG contract specs https://www.cmegroup.com/markets/metals/base/copper.contractSpecs.html ; LME copper https://www.lme.com/en/metals/non-ferrous/lme-copper/contract-specifications (not re-read 24 Oct) |
| LME prompts run daily to 3 months, weekly to 6 months, then monthly on the third Wednesday. Official prices are published for cash and 3-month; a Dec26 prompt (16 Dec 2026) sits between them from mid-September. | LME Dec26 = cash + w x (3-month - cash), w = days from cash (T+2) to the prompt over days from cash to 3 months; used only while the prompt sits between them, never extrapolated. | LME trading structure https://www.lme.com/en/trading/contract-types/futures (not re-read 24 Oct) |
| The COMEX-LME premium is a US tariff expectation: it widened after the 50% copper tariff was announced on 8 Jul 2025 and collapsed when refined cathode was left out of it on 30 Jul 2025. | Two replays added to the episode library (`cu_tariff_2025`, `cu_exempt_2025`): the kill scenario Bernardo named is in the stress table, measured on our own closes. | White House proclamation "Adjusting Imports of Copper into the United States", 30 Jul 2025 (public reporting; not re-read 24 Oct) |
| A ratio index (100 x long / short) has log returns equal to long one leg and short the other at equal notional; levels below zero cannot occur. | The spread is stored as a price-like index, so the risk model (log returns, EWMA vol, Ledoit-Wolf correlation), the critic's random-entry base rates and the sizing assistant's stop-in-sd run unchanged. Premium % = index - 100. | Standard; same convention as the risk model's spliced returns (docs/research/risk.md) |
| Daily closes are not synchronous (LME official prices ~12:30-13:00 London, COMEX settlement 13:30 New York), and Yahoo's HG=F is not back-adjusted at rolls. | The idea is rebased to the PM's own fill (rv:<id> = spread x entry / spread at the first close on or after entry day). Exact legs (HGZ26 + LME Dec26 interpolation) from mid-Sep 2026; earlier history is chain-linked on HG=F / LME 3-month returns (levels never spliced) and carries HG=F roll jumps: treat stress rows before Sep 2026 as approximate. | docs/research/risk.md (roll screen); Westmetall table layout |

## What stays the same
- Descriptive only. A spread is a price for the agents, not a signal; anything promoted goes through the quant-research gate.
- Crowding (CFTC) and narrative placement read single markets: relative ideas show "n/a" there.
- LME prices are licensed: `lme:*` and every spread that uses them are personal use only, never in a public post (network.py's public pack uses public-domain series only), never ported to the corporate build.

## Convention
Long the spread = long the first leg, short the second. A relative idea is captured with `--spread <id>`; entry, target
and invalidation are typed as the premium % (0 = parity) and stored as the index (100 + premium).
