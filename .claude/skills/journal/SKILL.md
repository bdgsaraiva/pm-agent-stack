---
name: journal
description: Capture, update, close or reject an idea in Bernardo's decision journal in under a minute, from a free-text or voice-style message ("long Dec Brent, conviction 4, out below 95, target 115"). Use when he says journal, log this idea, I'm taking/passing on a trade, close/stop out an idea, answers or pushes back on a critic question, sets the weekly goal, or asks for journal or critic stats.
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
- **Relative trade** (two legs, e.g. "long COMEX copper vs short LME"): `--spread <id>` from `python -m pmstack spreads list` (config/spreads.yaml) instead of `--direction`/`--price-ref`. Long the spread = long the first leg. Entry, target and invalidation are typed as the **premium % of the long leg over the short leg** (0 = parity, "bought at the same price") and stored as the index (100 + premium); the idea is marked on `rv:<id>`, so R, sizing, critic and risk work as usual. No spread defined for the pair: add a block to config/spreads.yaml first (legs, unit factor, LME prompt), never journal it as a bare `relative`. `--at <ISO time>` records a trade he made earlier.
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
- Move the stop or target on an open idea: `journal event <id> --action stop|target --price <p> --reason "..."`. Code records old and new value, recomputes reward-to-risk, expected R and the size suggestion, and refuses a stop at or through entry (or a target on the wrong side). R at close stays in units of the first stop. Never edit the entry file by hand for this; critic questions stay as saved.
- Close: `journal close <id> --exit-price <p> --process <1-5> --lesson "..." --trigger <target|invalidation|event|time|extreme|funding|ad-hoc>` (R is computed for spread ideas from the exit index level; `--r <R>` for vol trades and relative ideas without a spread). The trigger is required unless the exit price is at or through the target or invalidation; if he didn't say why he exited, ask once with AskUserQuestion (event / time / extreme move / funding another idea / ad hoc). Always ask for one lesson.
- Weekly goal (agent 6): `/journal goal <key>` → `python -m pmstack review goal set <key>` (starts next Monday; `--start <date>` to change); `review goal show`, `review goal drop`, `review goal list` for the catalogue. Goals are behaviours from the catalogue, never R or P&L targets.

## 4. Show the result in three lines max
- The id, reward-to-risk and expected R (if computable).
- **Suggested size** from the output's `sizing.units` next to his planned size, e.g. "Suggested 1.75 units (p 0.60, 3.0:1), you planned 1.0". Quote it as advice; he decides. If `units` is 0, say why from `sizing.notes` (no edge, or too small).
- Each flag as a question, e.g. "Conviction 5 but size 1.0 is below your median 1.5: size up, or is the conviction lower than you said?"
- A block (no invalidation): ask for the level, then re-run.

Sizing flags read like this: `undersized-vs-suggestion` → "Conviction 5 and the suggestion is 1.75; you planned 1.0. Size it, or is conviction lower than you said?"; `oversized` → "Above the suggestion and past the optimum: what makes this one different?"; `stop-in-noise` → "Your stop is under 1 daily move away: widen and size down?"; `drawdown` → "Paper drawdown is past 4R, so sizes are halved."

## 4b. Critic (agent 5), right after capture
The idea is already saved; the critic never slows capture. `journal new` stored a card on the entry (`critic:` block): the outside view, crowding, trend, rule triggers and the question slots code picked. Then:
1. `python -m pmstack critic card <id>` prints the card (`facts`, each with value and source) and `slots` (0–3: `premortem`, `counter`, `rule`, each with `facts` to cite and a `brief`).
2. **Silent** (`silent: true`, small low-conviction idea) → show one line of the card (base rate, crowding) and stop. No questions.
3. Otherwise write **one question per slot**, nothing more:
   - **premortem**: "It is <entry.horizon_date> and this lost 1R. What happened? Name at least one reason that is a thesis error, not luck." Add `base.stop_first_pct` if on the card.
   - **counter**: the strongest case against, built **only** on the slot's facts, stating the critic's own number ("Random entries with your target and stop won 38% of the time; you imply 50%. What do you know that they don't?"). Never generic devil's advocacy.
   - **rule**: the Zweig rule in the brief, as one question about this idea.
   Every figure must be on the card. Save: `python -m pmstack critic save <id> --json '[{"slot":"premortem","facts":["entry.horizon_date"],"text":"..."}]'`. If it returns problems (unplanned slot, no fact cited, a figure not on the card), fix the wording and save again.
4. Show, after the size line: the card in one line (e.g. "Outside view: random entries won 49.7% (target first 31.9%, stop first 38.3%; 928 starts since 2023-01-03). Crowd: 17th pct on your side.") and the questions numbered. If `tier` is `before-sizing`, say "Answer before sizing up." Then ask: "Your P(win) after the card?" (optional).
5. **Answers** (now or later, in his words): `python -m pmstack critic answer <id> --q q1 --text "..." [--thesis-error] --reaction useful|known|irrelevant --premise valid|wrong --changed none|size|stop|target|prob|horizon|pass` and `--prob-after 0.45`. A change is logged as a journal event with reason "critic"; also run the matching `journal event` (reduce, stop, target, etc.) if he changes the trade.
6. **Pushback**: questions are frozen. If he disagrees, don't soften or apologise; withdraw only when he brings a new fact: `critic withdraw <id> --q q2 --new-fact "..."`. Otherwise keep the question and record his answer.
7. At close, for each question: did the named risk happen? `critic outcome <id> --q q1 --happened yes|no`.

## 5. Save
`git add journal logs && git commit -m "journal: <id>" && git pull --rebase && git push`

## Stats on request
`python -m pmstack critic stats`: questions asked and answered, decisions changed (events with reason "critic"), by template, false-alarm rate (premise wrong), mean P(win) shift, Brier before vs after once 5 ideas have both. Method: `docs/research/critic.md`.
`python -m pmstack journal size <id>` recomputes the suggestion on today's record (`--write` stores it). `python -m pmstack journal sizing-review` gives suggested vs planned by conviction, R left on the table, Brier score (calibration) and what closed ideas did after he exited. Method and sources: `docs/research/sizing.md`.
`python -m pmstack journal stats` (hit rate, average R, R and size by conviction, holding time of winners vs losers, results by idea source, the graveyard's would-have-been R) and `python -m pmstack journal book` (open ideas vs latest prices, distance to invalidation). Report the numbers as printed; label any reading as inference.
