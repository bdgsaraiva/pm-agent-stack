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

Cross-episode index: `notes/podcasts/index.md`, one line per episode with tags and assets, so the critic and the morning note can search by asset.
