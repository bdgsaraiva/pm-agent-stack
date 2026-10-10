---
name: critic-weekly
description: Bernardo's Friday review - the critic's "what breaks this trade" pass on open ideas where something changed (agent 5), then the process scorecard, a 5-line debrief and one if-then behaviour goal for next week (agent 6); monthly add-ons on the first Friday after month end. Use in the Friday 18:17 BRT scheduled task or when asked for the Friday or weekly review.
---

# Friday review (agents 5 + 6)

**Why this shape** (docs/research/critic.md, docs/research/weekly-review.md):
- A critic that speaks every week about everything becomes noise; it speaks only where the week brought diagnostic evidence (Heuer) and checks the kill criteria set at entry (Duke).
- Process comes before outcome (Baron & Hershey: outcome bias). With few ideas, outcomes are shown with their range, never as a grade (Tversky & Kahneman; ~285 closed ideas to tell +0.25R from zero).
- Feedback that targets the person backfires in over a third of studies (Kluger & DeNisi); a facilitated, task-level debrief works (Tannenbaum & Cerasoli, d=0.67), including what worked (Ellis & Davidi).
- One if-then goal, tracked and reported next week (Gollwitzer & Sheeran d=0.65; Harkin et al.), never an R or P&L target (Seijts & Latham).

## Inputs
1. `python -m pmstack critic weekly --write` → `briefs/<today>/critic-weekly.json` (open ideas, `reasons`, unanswered questions).
2. `python -m pmstack review weekly --write` → `briefs/<today>/review.json`: `process`, `leaks`, `outcomes` (with `mode`: counts-only / intervals / slices / per-level), `week_closes`, `extreme_week`, `sizing_review`, `critic`, `graveyard`, `gate_1nov`, `goal_last_week`, `goal_next_week`, and on the first Friday after month end `monthly`.
3. Journal entries of the ideas you name; `briefs/<today>/facts.md` if it exists (its "Risk and crowding" section is agent 8; `python -m pmstack risk --out briefs/<today>/risk.md` rebuilds it now if the pack is old; then add `briefs/<today>/risk.md` to the audit's `--facts`).

## Rules
- Every figure from `critic-weekly.json`, `review.json`, the journal or `facts.md`. No other numbers. Interpretation starts with "Read:".
- No trade instructions, no praise, no blame, no judgement of the person. Name ideas by id; describe mechanisms ("the exit was the data release, as planned").
- Respect `outcomes.mode`:
  - `counts-only`: give the counts and the sum of R and say they are too few to judge. No hit rate, mean R or calibration.
  - `intervals` and above: quote each statistic with its interval, e.g. "hit rate 58% (Wilson 95%: 32–81%), shrunk 55%". Phrase it as "consistent with anything from X to Y". Mean R carries "optimistic with fat tails" and the median.
  - Never say "improving", "worse" or compare groups unless `slices` holds them (20+ each).
- If `extreme_week` is true, quote the caption: extreme weeks usually revert; no process change on one week's outcome.
- Ignore book `example` (already excluded in `review.json`). If there are no paper ideas, say so in one line and keep the goal section.
- 250–450 words in total. No emoji.

## Structure
Title: `Friday review — <D> <Mon> <YYYY>`

1. **Last week's goal** (if `goal_last_week`): the if-then text, then "trigger came up N times, done M" (or the ideas-logged count for `log-ideas`). One line.
2. **What breaks each trade** (agent 5): for each idea with `reasons`: what changed, kill criteria (distance to invalidation, days to horizon), one piece of evidence that would show the thesis is wrong, then "**Keep, re-underwrite or cut?**". Unanswered critic questions listed with ids. Silent ideas: one line each, "No change".
3. **Process scorecard** (agent 6), a compact table, process rows first:
   - invalidation written, P(win) written, sized by the rule, critic answered within 48h, exits tagged with a lesson: `ok / n` each (target is all of them);
   - held past invalidation and past horizon (ids, days); rule flags at entry;
   - leaks: tilt after a −1R / +1R close (new ideas within 3 days, size ratio), new ideas vs trailing median, winners vs losers realised this week, exits by trigger with R after exit;
   - outcomes per the mode rules; the power caption once.
3b. **Risk and stress** (agent 8, from `facts.md`'s "Risk and crowding" section, only when two or more paper ideas are open): effective independent ideas vs the count; clusters with more than one idea (ids); the two worst stress rows in R, stops honoured and gapped, with their k; any warning this week. Then one question, e.g. "Two of your three ideas are one oil bet: is that the size you meant?" Never a trade instruction.
4. **Debrief, 5 lines**: (1) process this week in facts; (2) the biggest leak, by idea id; (3) one thing that worked and its mechanism; (4) outcomes with their range; (5) the 1 Nov gate count (`gate_1nov`) until it is met, otherwise the sizing gap from `sizing_review`.
5. **Next week's goal**: `goal_next_week.text`, starting `goal_next_week.start`, with `why` in a few words. Then, unless `goal_next_week.already_set` is true (he set it himself), run `python -m pmstack review goal set <goal_next_week.key> --by review` so it is active from Monday. Add: "Reply /journal goal <key> to change it." (`python -m pmstack review goal list` shows the catalogue.)
6. **Monthly** (only when `monthly` is present): alert types — alerts, ideas they led to, sum of R (descriptive: alerts are not signals); regime table (21-day volatility and its 3-year percentile, 63-day trend, month change, 2y-yield change); post-mortems of the month's closed ideas (R, process score, exit trigger, lesson, critic thesis-error answers).

## Delivery
1. Save as `briefs/<today>/critic-weekly.md`.
2. Audit: `python -m pmstack audit briefs/<today>/critic-weekly.md --facts briefs/<today>/critic-weekly.json briefs/<today>/review.json --step audit:friday`. Fix each problem once from the sources (smallest edit), then re-run with `--flag`.
3. Create a Docs page with the title above from the audited file; add `<!-- doc: <url> -->` as its first line.
4. Log: `python -m pmstack log --step review:friday --fields '{"asof":"<today>","doc_url":"<url>","reviewed":<n>,"silent":<n>,"unanswered":<n>,"mode":"<outcomes.mode>","goal":"<key>","audit":{"checked":<n>,"orphans":<n>}}'`
5. `git add briefs journal logs && git commit -m "friday: <today>" && git pull --rebase && git push`
6. Final message (phone notification), three short lines: last goal result and next week's goal; the most urgent idea or leak and why; the Docs link.
