# Kickoff brief: build the next agents (literature first)

Paste the short prompt at the bottom into a new Claude Code session on this repo. The session reads this brief and follows it. Written 10 Oct 2026 after agent 4 (sizing); updated the same day after agents 5 (critic + number auditor), 6 (weekly review), 7 (consensus and narrative monitor) and 8 (risk and crowding) shipped. Moved into the repo (`docs/project/`) on 15 Oct 2026 so Claude Code sessions can read it.

---

## 1. Where things stand
- **Running (12 of 12):**
  - 1 data pipeline (GitHub Actions, started 05:40 BRT by the "Data refresh" scheduled task; GDELT included, with a 12-minute budget);
  - 2 morning note (scheduled task 06:18 BRT, trig_01TFXFA9NLQFrkB6dfYg3gFa, figures audited, risk line on exceptions);
  - 3 journal clerk (`/journal`);
  - 4 sizing assistant (inside the journal; drawdown cut on the marked book since agent 8);
  - 5 critic + number auditor (card and questions on every idea; `python -m pmstack audit`);
  - 6 weekly review (scorecard + one tracked goal; "Friday review" scheduled task Fridays 18:17 BRT, trig_01Q9SQrQjkA72XNpf2LP5pg3);
  - 7 consensus and narrative monitor (the "Consensus map" in the daily fact pack). Built 10 Oct, before the gate, at my request;
  - 8 risk and crowding (the "Risk and crowding" section in the fact pack; `python -m pmstack risk`; risk and stress in the Friday review). Built 10 Oct, before the gate (not met), at my request.
  - 10 research digester (`/digest`) and 11 network and reputation (`/network`, contacts in a separate private repo). Built 15 Oct, before the gate (not met), at my request; see notes-A11.
- **Queue, in order:** own test set, 9 balance keeper and 12 research loop done (16–20 Oct; notes-A12, notes-A13) → v2 items (agent 9 STEO/export sales; agent 12 quarterly re-runs) → vendor review 15 Jan 2027.
- **Gate 1 Nov:** 10 paper ideas in the journal and 2 Friday reviews before the next agents. Check `python -m pmstack journal stats`. If the gate isn't met, say so in one line and let me choose: build anyway, or wait. (15 Oct: 0 of 10 ideas, only the example; first Friday review 16 Oct.)

## 2. Read first (in this order, only what you need)
1. `docs/project/agents-plan.md`: status table, decisions log, standing rules.
2. The latest session notes, `docs/project/notes-A11.md` (and A8 if needed).
3. **PM Agent Plan** (Docs): https://claude.ai/code/artifact/e528ae0e-8679-497e-bd99-7f86be400ae9. This has the roster table and the agent specs; read it with the Docs tools, by search or section, not whole. If the session can't open Docs links, work from `agents-plan.md` and say which Docs updates are left for a claude.ai chat.
4. **Literature reviews**, the template for every review. Repo copies in `docs/research/` (sizing, critic, weekly-review, consensus, risk). Docs versions:
   - sizing: https://claude.ai/code/artifact/5e35dad7-b607-40ce-8e88-5466c037c3c8
   - critic: https://claude.ai/code/artifact/48d36e62-379d-4820-88f7-346f6d775b45
   - weekly review: https://claude.ai/code/artifact/dfaab6f8-6e05-4058-a5e8-61fe5b69d639
   - consensus monitor: https://claude.ai/code/artifact/40d845c6-a148-4504-9a03-f33b90072127
   - risk and crowding: https://claude.ai/code/artifact/f4a74a73-6de9-4269-8832-8b7959f1f5d2
   - research digester: https://claude.ai/code/artifact/2077d29e-dfa5-4bb9-a8ff-8a39d46bbb43
   - network and reputation: https://claude.ai/code/artifact/4e2f97b5-206a-451d-8e39-69854e5d30a9
5. **PM Mandala** (Docs): https://claude.ai/code/artifact/84d1ed92-f956-45b5-9c25-224daff4c5f8. Pillars, Zweig rules, goal Sharpe 1.5+ over 3 years.
6. **Atlas**: https://claude.ai/artifact/3DGdbccsP5mrFLt7BzpHcr. The page is too large to read whole (~230k tokens). If the session can open it, pull only the investor cards and sections relevant to the agent, by searching the saved file. `docs/project/notes-S9.md` summarises Sections 4–5 (patterns, blueprint).
7. **Repo**: `CLAUDE.md` (hard rules), then run `python -m pytest -q` (~5 minutes on Linux; ~16 on Bernardo's Windows PC, with the `.venv` from notes-A11).

## 3. The workflow for each agent (one agent per session unless it's small)
1. **Literature review first.**
   - Cover the most cited papers, the recent ones, and at least one serious counterpoint.
   - Cover the Atlas investor cards that bear on it, and the specialist books and authors.
   - Open every page you take a claim or number from; a search snippet is not a source.
   - Mark book points you couldn't page-check as "general knowledge, not page-checked".
   - Use parallel sub-agents for the searches if available (agent 8 used three, one per theme).
2. **Write it up twice:**
   - **Docs page "<Agent> — literature review"**, same shape as the earlier ones (if the session can't create Docs pages, the repo copy is enough and the Docs version is made later from a claude.ai chat):
     - papers table (finding → what it changes → source);
     - Atlas investors and books;
     - where sources disagree and the resolution;
     - design changes vs the plan's spec;
     - how it works, with a worked example;
     - sources.
   - **`docs/research/<agent>.md`** in the repo, committed with the code.
3. **Ask only what the literature leaves open.**
   - Up to 3 questions, multiple choice (I prefer it).
   - Put the recommended option first.
   - Then build without waiting for more approval.
4. **Build:**
   - **Code computes, the model writes.** Config goes in `config/*.yaml`.
   - **One skill, one trigger, one log line.** Skill in `skills/` or `.claude/skills/`; trigger is a schedule, a `/command` or an event.
   - **Logging:** every run logs to `logs/runs.jsonl` via `python -m pmstack log`.
   - **Tests:** offline tests in `tests/` with fake HTTP, like the existing ones. Fake data are reset per fixture, so tests don't depend on order, and never depend on the real date (the 12–14 Oct outage).
   - **No look-ahead:** anything with a `--date` uses only data, ideas and reports available on that date (agent 8's review found four ways this leaks). Test it explicitly.
   - **Wiring:** into the journal or fact pack where the spec says.
   - **New data sources:** they run only in GitHub Actions. Give each a time budget, so the 40-minute job (tests ~5 min) always reaches its commit step.
   - **Scheduled tasks:**
     - Created with the scheduling tools, never local cron.
     - Times written with `CRON_TZ=America/Sao_Paulo`.
     - Push notification on.
     - Say which approval setting the task got.
5. **Check the work:**
   - Run the full test suite and a live run on real data from the repo.
   - The Actions job log can't be downloaded from the session; read `logs/runs.jsonl` and the committed briefs after `git pull`.
   - Run the number auditor on every written output: `python -m pmstack audit <file> [--facts <json or md>]`.
   - Take a screenshot of any Docs chart before calling it done.
   - For high-stakes outputs, have a sub-agent that didn't build it review it. It found 11, 11, 8 and 12 real defects in agents 5, 6, 7 and 8.
6. **Hand off:**
   - Commit and push with the session's attribution lines.
   - Update in the PM Agent Plan doc (or list the update for a claude.ai chat): roster status, the agent's section with a link to its review, the schedule if dates moved.
   - Update `docs/project/agents-plan.md` (status, decisions log) and write `docs/project/notes-A<n>.md`.
   - Update `CLAUDE.md` (layout, commands) and the README.
   - If a scheduled task should use the new agent, update its prompt (agent 8 updated the Friday review's).
   - Say in chat, in 2–3 lines, what shipped and the next agent.

## 4. Agent briefs and seed reading
Seed lists are starting points, not conclusions: verify each one, add the most cited work they miss, and drop what doesn't hold.

### 5. Critic + number auditor — DONE 10 Oct (see notes-A5, docs/research/critic.md)
### 6. Weekly review — DONE 10 Oct (see notes-A6, docs/research/weekly-review.md)
### 7. Consensus and narrative monitor — DONE 10 Oct (see notes-A7, docs/research/consensus.md)
Planned upgrades (owned by the notes-and-keys track since 15 Oct, see `notes-and-keys-kickoff.md`):
- My consolidated trend-following knowledge from the podcast project (CTA lookbacks, vol targets, how crowded trend trades unwind), credited per guest and episode, filed under `notes/podcasts/top-traders-unplugged/`.
- GPR/EPU validation plus a 20–30 headline audit per narrative.
- Curve and basis data, once a source exists.
### 8. Risk and crowding — DONE 10 Oct (see notes-A8, docs/research/risk.md)
Follow-ups: align consensus.py's CFTC date to the Friday release (notes-and-keys track), and the sizing overlap cut to 250 days plus shrinkage. Agent 12 measures every crowding and CTA flag's base rate and lift before any may alert.

### 10. Research digester — DONE 15 Oct (see notes-A11, docs/research/digester.md)
### 11. Network and reputation — DONE 15 Oct (see notes-A11, docs/research/network.md)
### 12. Research loop — DONE 20 Oct (see notes-A13, docs/research/research-loop.md). First run: no agent 7 or 8 flag may alert.

### Next agents (same workflow; seed lists to start from)
- **Own test set:** evaluation design for LLM agents (FinanceBench; evals and test-set literature); about 20 real tasks with known good answers.
- **9 Balance keeper:**
  - Working (1949) and the theory of storage;
  - Gorton, Hayashi & Rouwenhorst (2013);
  - Kilian (2009), oil shocks;
  - Adjemian (2012) and Isengildina-Massa et al. on WASDE announcement effects;
  - EIA weekly report and USDA methodology.
  - Needs repo secrets `USDA_FAS_API_KEY` and `NASS_API_KEY` from me.
- **12 Research loop:**
  - Harvey, Liu & Zhu (2016);
  - Bailey & López de Prado, deflated Sharpe;
  - McLean & Pontiff (2016), post-publication decay;
  - Hou, Xue & Zhang (2020), replication;
  - White (2000), reality check;
  - look-ahead and memorisation bias in LLMs (Glasserman & Lin; Sarkar & Vafa);
  - the quant-research-standards skill.

## 5. Rules that don't change
- **Personal build only.**
  - Paper and example ideas, public data. No fund positions, sizes, P&L, orders, broker research or proprietary notes anywhere: repo, prompts, notes, logs.
  - Corporate work is deferred.
- **Numbers.** Every number in an output comes from code over the research memory or the journal, with its source link, and passes the number auditor. Label interpretation as inference. Agents ask questions; I decide; no trade instructions.
- **Focus markets.** Commodities, US equities, US rates, USD. Not Petrobras, Vale, BRL or IBOV.
- **Standing fact.** Dated Brent has traded far above futures all through 2026 because of the Iran war; it's not a data error.
- **Build only what stays scarce.** If a vendor now ships something (data MCPs, generic briefs, thesis checks), don't build it. Note it for the vendor review.
- **Data access.** The cloud shell can't reach data sites (GDELT returns 403 from it), so data goes through GitHub Actions. The Yahoo adapter is personal-use only.
- **Never handle keys.** Never enter or store API keys or tokens. Tell me where to add them (GitHub repo secrets).
- **Browser.** If you use one, keep it quiet: muted and paused, no sound.
- **Working style.** Ask in multiple choice, at most once per agent. Keep chat replies short; findings go in the docs.
- **Parallel track.** Another session owns the morning note, news/BigQuery adapters, `pmstack/consensus.py`, `config/sources.yaml`, `config/monitor.yaml` and `.github/workflows/daily.yml` (see `notes-and-keys-kickoff.md`). Stay out of those files; run `git pull --rebase` and the full test suite before every push. **Work in your own git worktree, never in the main checkout while another session runs** (`CLAUDE.md`, "Parallel sessions").

---

## Paste this into a new Claude Code session on the repo

```
Continue phase 2 of my "Future of Asset Management and Trading" project: build the next AI agents, literature first.
Read docs/project/agent-build-kickoff.md and follow it, with docs/project/agents-plan.md and docs/project/notes-A11.md. Start with the own test set, then agent 9 (balance keeper), after checking the 1 Nov gate; if it isn't met, ask me once: build anyway or wait.
For each agent: literature review (papers, Atlas investor cards, specialist books) → docs/research/<agent>.md (+ Docs page if you can create one) → at most 3 multiple-choice questions → build, test, live run → commit, update docs/project/agents-plan.md and a new docs/project/notes-A<n>.md, and list any PM Agent Plan doc updates you couldn't make.
CLAUDE.md has the hard rules. Personal build only: paper ideas and public data. Another session owns the morning note, news adapters, consensus.py, config/sources.yaml, config/monitor.yaml and daily.yml: pull before every push and stay out of those files.
```
