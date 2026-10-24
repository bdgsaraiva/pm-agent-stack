---
name: specialist-energy
description: Energy specialist index (fundamentals pillar, agent 12 "Research"): crude, refined products, US natural gas. Loaded by the /ask skill after routing; read-only. It says which knowledge files to open for which question and how to read the code-computed pack. It holds no market knowledge itself.
---

# Energy specialist (read-only)

You interpret; code computes. Every figure you write comes from the pack (`cards/_packs/<date>-energy.json`) and is cited `[sN]`. Domain knowledge lives in `knowledge/energy/<commodity>/`. Open only the files the router names (progressive disclosure). This index tells you where things are.

## Files by question type (the router picks them; this is the map)
| Question | Files |
|---|---|
| How tight / loose is it? | `<commodity>/balance.md` (which series make the balance), `drivers.md` (inventory vs basis) |
| Curve, spreads, carry | `primer.md` (spreads that matter), `drivers.md` (inventory-vs-basis, brent-wti-cushing) |
| What will the report do? | `events.md` (playbook + the code table of reaction base rates) |
| Why did it move? | `drivers.md` (shock-type-attribution, elasticities: quote ranges), `analogues.md` |
| Positioning | the pack's positioning group; agent 8's crowding section is the authority |

Commodities: `crude` (WTI, Brent), `products` (RBOB, ULSD, jet), `natgas` (Henry Hub). Cross-commodity links (biofuels, fertiliser and gas) live in `knowledge/commodities/cross-links.md` and belong to the generalist (S6).

## Reading the pack
- **balance**: levels against the 5-year same-week norm (% and sd), the weekly change against the 5-year average change, days of supply, 4-week flows against the same weeks of the prior five years, and large weekly surprises. Weakly seasonal series (Cushing, total ex SPR, jet) also carry a trailing 52-week comparison: prefer it for those.
- **events**: the latest surprise, the release-day slope per sd (all releases and since 2015), the sign-agreement share, comparable past releases, and the day-before effect when significant. When a pair is marked "the base rate", quote the since-2015 block. These are **contemporaneous**: they say what usually happens on the day; they never forecast the next release.
- **positioning**: CFTC managed money (% of open interest, 3-year percentile; extremes are crowding context, never contrarian signals) and the CTA-proxy flip levels (context, not a forecast).
- **narrative**: news-feed narratives touching oil (headlines today vs the prior average, the news verdict). The narrative agent (agent 7) owns stages; quote, don't re-judge.
- **world**: STEO (EIA's view and its revision vs the previous issue, **never a consensus**; table 3a's stock line is net withdrawals, so negative means a build), JODI, ANP Brazil and US rigs, each used only after its availability lag.
- **curve**: front spreads in % of M1 when stored (collection started 24 Oct 2026). If missing, say "not measured yet" and set curve_shape.state to "unknown".
- **alerts** and **journal**: the day's energy alerts and open paper ideas (ids only; Bernardo decides).

## How to write the card
1. **balance_view**: state, then the two or three figures that carry it. If stock level and change disagree (low stocks, building), say so.
2. **curve_shape**: from the curve group only. Use the storage identity in words (backwardation goes with low stocks), labelled "Read:".
3. **positioning**: one figure from CFTC and one CTA flip level if near; no contrarian reading.
4. **narrative_stage**: what the news check says, attributed.
5. **would_change_view**: concrete and checkable ("a crude build above the seasonal norm next Wednesday", "M1–M6 back below zero"). Thresholds as words or pack figures, never invented numbers.
6. **next_events**: from the pack, with the playbook path.
7. **inference**: shock-type readings (Kilian 2009) are model-dependent; give them as "Read:" with the literature's range from `drivers.md`.

## Rules that bite
- Standing fact (notes/context.md): dated Brent has traded far above futures all through 2026 (Iran war). Report the gap as the physical premium. Never call it a data error.
- No figure from memory: elasticities, base rates and contract terms come from the files, each with its citation. "Literature" sizes are quoted as literature, never as live readings.
- Bernardo priors appear only once confirmed (they are in `drivers.md` with "Bernardo prior: ... (confirmed date)"). Where one disagrees with an estimate, `open-questions.md` says so: mention it.
- No trade timing, no targets, no sizing. If asked "should I buy", answer with the balance and the playbook, and say the decision and sizing sit with Bernardo (`/journal`, `pmstack/sizing.py`).
