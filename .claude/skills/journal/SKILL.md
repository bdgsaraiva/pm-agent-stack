---
name: journal
description: Capture, update, close or reject an idea in Bernardo's decision journal in under a minute, from a free-text or voice-style message ("long Dec Brent, conviction 4, out below 95, target 115"). Use when he says journal, log this idea, I'm taking/passing on a trade, close/stop out an idea, or asks for journal stats.
---

# Decision journal — 60-second capture

The journal is the moat: conviction, expected payoff, invalidation, where the idea came from, and what happened, recorded at the time. Speed matters more than polish; never turn capture into an interview.

## Rules
- **Personal build: paper ideas and examples only.** If the message describes a real fund position (sizes, P&L, the fund's book), do not record it here; say in one line that it belongs in the corporate build, and offer to log it as a paper idea without fund details.
- **Bernardo decides.** Checks are questions, not vetoes. The only hard stop is an open idea with no invalidation (Zweig #3).
- Never invent numbers. Prices you don't get from him come from the research memory (`--price-ref`), which stamps the source.

## 1. Parse what he said
Map his words to fields (all optional unless marked):
- **market** (required), **direction** (required: long / short / relative / vol), **conviction** 1–5 (required)
- **thesis** (required: one or two sentences in his words), **breaks**: what proves it wrong
- `--price-ref` from the research memory when the market has one: Brent `BZ=F`, WTI `CL=F`, RBOB `RB=F`, ULSD `HO=F`, Henry Hub `NG=F`, gold `GC=F`, silver `SI=F`, copper `HG=F`, soybeans `ZS=F`, corn `ZC=F`, wheat `ZW=F`, sugar `SB=F`, coffee `KC=F`, S&P `ES=F`, Nasdaq `NQ=F`, 10y note `ZN=F`, 2y note `ZT=F`, DXY `DX-Y.NYB`, EUR/USD `EURUSD=X`, USD/JPY `JPY=X`
- entry / target / invalidation prices; `--invalidation` for a condition that isn't a price
- `--size-planned` in paper risk units (1 = his normal size), `--horizon-days`, `--prob-win` (0–1)
- `--expression` (futures / options / spread) and `--instrument` (e.g. "Dec26 Brent 110 calls")
- `--source`: own / alert / note / podcast / call / broker / consensus / news, with `--source-ref` (alert as `alerts:<date>#<rank>`, a note path, a podcast episode)
- `--consensus` (what the market thinks) and `--why-different` (his second-order edge)
- `--sleep` and `--stress` (1–5) if he mentions them

## 2. Ask once, only for what's missing
If any of conviction, invalidation (for an open idea), target, size or source is missing, ask **one** round with AskUserQuestion (multiple choice, he prefers it), up to 4 questions. Examples: conviction 2 / 3 / 4 / 5; size 0.5 / 1 / 1.5 / 2 units; source own / alert / call / podcast. If AskUserQuestion isn't available, ask in one short line. If he says "skip", record what you have.

## 3. Record
```
python -m pmstack journal new --market "Brent" --direction long --conviction 4 \
  --thesis "..." --breaks "..." --price-ref BZ=F --target 115 --invalidation-price 95 \
  --size-planned 1 --source own --horizon-days 30
```
- Idea not yet traded: `--status idea`. Later: `python -m pmstack journal event <id> --action open --price <p> --reason "..."`.
- **Passed on an idea** (rejected ideas are the graveyard the critic learns from): record with `--status idea`, then `python -m pmstack journal reject <id> --reason "..."`.
- Add / reduce: `journal event <id> --action add|reduce --size <units> --price <p> --reason "..."`.
- Close: `journal close <id> --exit-price <p> --process <1-5> --lesson "..."` (or `--r <R>` for relative-value and vol trades).

## 4. Show the result in three lines max
- The id, reward-to-risk and expected R (if computable).
- Each flag as a question, e.g. "Conviction 5 but size 1.0 is below your median 1.5: size up, or is the conviction lower than you said?"
- A block (no invalidation): ask for the level, then re-run.

## 5. Save
`git add journal logs && git commit -m "journal: <id>" && git pull --rebase && git push`

## Stats on request
`python -m pmstack journal stats` (hit rate, average R, R and size by conviction, holding time of winners vs losers, results by idea source, the graveyard's would-have-been R) and `python -m pmstack journal book` (open ideas vs latest prices, distance to invalidation). Report the numbers as printed; label any reading as inference.
