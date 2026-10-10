---
name: critic-weekly
description: Friday pass of the critic (agent 5) - "what breaks this trade" for each open idea in Bernardo's journal where something changed this week, ending with keep, re-underwrite or cut as a question; silent on ideas where nothing changed. Use in the Friday 18:17 BRT scheduled task or when asked for the Friday critic or weekly review. Agent 6 (process scorecard) will add its section to the same page.
---

# Friday critic (agent 5)

**Why this shape** (docs/research/critic.md): a critic that speaks every week about everything becomes noise people learn to ignore (alert overrides 49–96%; acceptance falls ~30% per extra prompt). It speaks only where the week brought diagnostic evidence (Heuer), checks the kill criteria he set at entry, a state and a date (Duke: invalidation and horizon), and asks rather than tells (Druckenmiller: never keep a position just because of the original thesis).

## Inputs
1. `python -m pmstack critic weekly --write` (date = today in America/Sao_Paulo). It writes `briefs/<today>/critic-weekly.json`: for each open idea, last price, week move in % and in weekly sd, R so far, share of the risk distance left, horizon date, crowding change since the card, the week's alerts on that market, unanswered critic questions, and `reasons` (empty = nothing changed = `silent`).
2. The journal entry of each idea with reasons (`journal/<YYYY>/<id>.md`): thesis, what breaks it, the critic card and answers.
3. `briefs/<today>/facts.md` if it exists.

## Rules
- Every figure from `critic-weekly.json`, the journal or `facts.md`, with its source link. No other numbers. Interpretation starts with "Read:".
- No trade instructions. Each idea ends with a question, never a verdict.
- Ignore book `example` ideas, except: if they are the only open ideas, write one line ("No open paper ideas; the example Brent idea is shown for format") and do the example once, labelled EXAMPLE.
- Silent ideas get one line in a closing list: "No change: <market> (<id>)".
- 150–300 words. No emoji.

## Structure
Title: `Friday review — <D> <Mon> <YYYY>`

1. **What breaks each trade.** For each idea with reasons, 2–4 lines:
   - what changed (the reasons, with figures);
   - the kill criteria: distance to invalidation and days to the horizon date; if invalidated or past horizon, say so first;
   - "What evidence next week would tell you the thesis is wrong?" — one diagnostic item, tied to the thesis or its "what breaks it";
   - end: "**Keep, re-underwrite or cut?**"
2. **Unanswered critic questions.** List them with their idea id (from `open_questions`), so he can answer with `/journal`.
3. **No change.** The silent ideas, one line.
4. (Agent 6 adds the process scorecard here.)

## Delivery
1. Save as `briefs/<today>/critic-weekly.md`.
2. Audit: `python -m pmstack audit briefs/<today>/critic-weekly.md --facts briefs/<today>/critic-weekly.json --step audit:critic-weekly`. Fix each problem once from the sources (smallest edit), then re-run with `--flag`.
3. Create a Docs page with the title above from the audited file; add `<!-- doc: <url> -->` as its first line.
4. Log: `python -m pmstack log --step critic:friday --fields '{"asof":"<today>","doc_url":"<url>","reviewed":<n>,"silent":<n>,"unanswered":<n>,"audit":{"checked":<n>,"orphans":<n>}}'`
5. `git add briefs logs && git commit -m "friday: <today>" && git pull --rebase && git push`
6. Final message (phone notification), three short lines: ideas to review / silent / unanswered questions; the most urgent idea and why; the Docs link.
