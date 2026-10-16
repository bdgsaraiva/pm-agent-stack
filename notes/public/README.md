# Monthly public commodity note (agent 11)

Numbered short posts (<= 300 words + one chart, English), drafted with `/network post`, published by Bernardo.
Rules (docs/research/network.md, config/network.yaml `public:`):
- Public-domain data only: charts and scored calls use FRED, EIA or CFTC series (`network public pack`). Never Yahoo data, never fund data, never broker research.
- Never attribute a view to a contact or firm ("a trader told me" is out). `network public check` looks for contact names.
- One call per post with probability, invalidation and review date, recorded in `calls.yaml` (`network public add-call`) and scored by code (`network public score`). Every post after the first carries a scorecard line and "what I got wrong".
- Figures audited: `python -m pmstack audit <post> --facts <pack.json>`.
- Bernardo checks his fund's code of ethics on public writing before the first post.
