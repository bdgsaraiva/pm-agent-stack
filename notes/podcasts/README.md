# Podcast summaries

Seed for the research memory: the Top Traders Unplugged summarisation pipeline moves here.
One markdown file per episode: `notes/podcasts/<series>/<YYYY-MM-DD>-<slug>.md`, with this header:

```
---
type: podcast
series: ""            # e.g. Top Traders Unplugged / Global Macro, Systematic Investor, Ideas Lab
episode: ""
date: YYYY-MM-DD
guests: []
assets: []
tags: []
url: ""
---
```

Body, in the standing summary format:
1. Key messages and conclusions (bullets).
2. Main numbers, data and arguments by guest and host.
3. Where relevant: consensus vs contrarian views; confidence of each argument (data / forecast / opinion); time horizon of each thesis.

Since 15 Oct 2026 episodes are digested with `/digest` (agent 10, `.claude/skills/digest/`): checked claim cards sit beside each note in `<note>.cards.json`, and `python -m pmstack digest index` rebuilds the cross-source index at `notes/index.md`. Add `questions:` (to ask next) to the header; agent 11 carries them into calls.
