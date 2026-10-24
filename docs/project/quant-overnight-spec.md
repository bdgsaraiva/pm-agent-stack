# Request to the notes track: the overnight change against the close tape (S2, 24 Oct 2026)

From the specialists track (agent 13, Quant). The notes-and-keys track owns the morning note, so this is a spec. The code goes into the note's own files when that track picks it up.

## What exists now
- `.github/workflows/close.yml` runs after the US close (started at 17:15 New York time on weekdays by the routine "Close tape"). It writes `briefs/<date>/quant.json` and `quant.md`.
- For each market, `quant.json` holds:
  - `markets.<id>.trend.legs.{21,63,252}`: `sign`, `flip_level`, `distance_sd`, `distance_pctile`, `stretched`, `rolloff_flip_days`;
  - `markets.<id>.trend.daily_sd_pct`;
  - `markets.<id>.vol`: `rv_short`, `regime`, `iv_minus_rv`, `gap_pctile`;
  - `flags` and `changes` (vs the previous tape).

## What the morning note should add (one short block, exceptions only)
1. **Read the previous close's tape:** the newest `briefs/<d>/quant.json` with d earlier than today.
2. **Take the overnight price** from today's fact pack: `prices[].live` when present, else the latest close.
3. **For each market and leg**, compute (code, not the model):
   - `crossed`: the overnight price is on the other side of `flip_level` from the leg's `sign` at the close.
   - `near`: |log(overnight / flip_level)| ≤ 1 × `daily_sd_pct` / 100, and not crossed.
   - Same check for any leg with `rolloff_flip_days` = 1 (it flips today by roll-off at an unchanged price).
4. **The note shows only crossed or near legs**, one line each: market, leg (1m / 3m / 12m), flip level, overnight price, distance in daily sd. Figures come from the tape and the pack, so the number auditor can pass them with `--facts briefs/<prev>/quant.json`.
5. **No reading.** These are levels where simple trend models would change sign: context, not a forecast. Published trend-flow pressure is small and fades within weeks (`docs/research/risk.md`, `docs/research/quant.md`).

## Test to add with it
Build a synthetic tape and a pack with a live price on each side of a flip level. Check crossed, near and none. Check that a tape dated today or later is never read (point in time).
