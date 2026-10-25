# Primer: iron ore

This file holds method and sources only. Live levels come from the pack.

## What is (and is not) here
- **No daily price.**
  - The benchmark trades on DCE (Dalian, CNY) and SGX (62% Fe, USD), and neither is free to store.
  - Yahoo's COMEX iron ore (TIO=F) stopped in August 2021.
  - So iron ore is answered from **monthly** prices: IMF via FRED (`PIORECRUSDM`, from 1992) and the World Bank Pink Sheet (`wb:iron_ore`, from 1960). Each is used from its availability, about a week after the month for both.
- **No port stocks.** Paid providers (Mysteel, SteelHome) compile Chinese port inventories; none is stored.
- Say so in the card's gaps: a question about a daily price or port stocks gets an honest "not in the repo".

## What moves it (frames, all inference)
- **Chinese steel.**
  - China makes about half the world's steel (general knowledge).
  - Steel prices behave as a mark-up over iron ore and coking coal (RBA Bulletin, Sep 2013; weekly VECM 2010–13), so ore follows Chinese steel margins and output.
  - Property construction is the largest use of steel.
- **Seaborne supply** is concentrated in Australia and Brazil: Vale, BHP, Rio Tinto, Fortescue (general knowledge).
  - Brazil-origin supply (Vale) is a possible edge source. No free monthly series is wired yet (open question).
- **Long run**: the real price percentile since 1960 and its deviation from trend (`estimates/longrun.json`). The main analogue is the 2003–2011 China supercycle (Erten & Ocampo 2013).

## Data in the repo
| What | Series id | Source | Since |
|---|---|---|---|
| Iron ore, monthly | PIORECRUSDM | IMF via FRED | 1992 |
| Iron ore, monthly | wb:iron_ore | World Bank Pink Sheet | 1960 |
