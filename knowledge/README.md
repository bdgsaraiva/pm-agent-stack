# knowledge/: what the specialists know, by commodity

Domain knowledge lives here, never in a prompt, so routing (`config/agents.yaml`) can change without a rebuild (specialists-kickoff.md section 7). A specialist loads its skill index (`skills/specialist-<complex>/SKILL.md`) and then only the files the router names for the question.

```
knowledge/
  sources.md                    source registry: licence, Actions reachability, history, release time, vintages
  commodities/cross-links.md    links between complexes (biofuels, fertiliser and gas, power and aluminium, freight); owned by the generalist
  inbox/                        files Bernardo drops (gitignored except README and ledger); see inbox/README.md
  _template/                    the seven files every commodity folder starts from
  <complex>/<commodity>/
    primer.md                   contracts, delivery, spreads that matter, seasonality, report calendar
    drivers.yaml / drivers.md   testable claims with sign, lag and size provenance (code-written; .md rendered)
    balance.md                  balance template, each line tied to a public series
    events.md                   playbooks per scheduled report, reaction base rates computed by code
    analogues.md                past episodes, linked to agent 8's stress library
    lessons.md                  from closed journal ideas
    open-questions.md           hand-written questions + a code block "Prior vs estimate"
```

Rules:
- **Numbers:** a figure in these files is either a citation (literature, agency method) with its link, or a pointer to the code that computes it (a series id, a study id, an estimate file). Live levels are never written here: they come from `briefs/<date>/facts.json` and the facts log (`pmstack facts as-of`).
- **Size provenance** for every quantified driver: `literature`, `own_estimate` or `bernardo_prior` (`pmstack/knowledge.py` enforces it). A broker's quantified sensitivity is never copied in.
- **Personal build:** public material and Bernardo's own non-fund notes only. Broker-informed knowledge belongs to the corporate copy (same layout, corporate account).
- **Who writes:** drivers, facts and the code blocks are written by `pmstack` functions; primers and playbooks are written in build sessions and reviewed by Bernardo. Specialists (at question time) only read.
