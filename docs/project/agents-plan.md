# AI-Agent Phase — Plan and Status

Phase 2 of the Project "Future of Asset Management and Trading". Started 4 Oct 2026. Owner: Bernardo.

> Repo copy since 15 Oct 2026 (`docs/project/`); this is the source of truth for build sessions. The claude.ai Project's `claude/agents-plan.md` is a snapshot as of 15 Oct.

- **PM Agent Plan (Docs) — the agent roster, specs and 12-week schedule:** https://claude.ai/code/artifact/e528ae0e-8679-497e-bd99-7f86be400ae9
- **Architecture doc (Docs):** https://claude.ai/code/artifact/b3d8514a-d6e6-4756-9864-474e1c35e429 (revised 9 Oct for moats); repo copy of the original: `docs/architecture.md`
- **PM Mandala (Docs):** https://claude.ai/code/artifact/84d1ed92-f956-45b5-9c25-224daff4c5f8 — goal Sharpe 1.5+ on the whole book over 3 years (commodity book already 1.9 since Jul 2023; full record 0.9 since Mar 2021); 8 pillars; 64 actions tagged Human / AI assists / Vendor; Zweig rules for the critic
- **Sizing assistant — literature review (Docs):** https://claude.ai/code/artifact/5e35dad7-b607-40ce-8e88-5466c037c3c8 (repo copy: `docs/research/sizing.md`)
- **Critic + number auditor — literature review (Docs):** https://claude.ai/code/artifact/48d36e62-379d-4820-88f7-346f6d775b45 (repo copy: `docs/research/critic.md`)
- **Weekly review — literature review (Docs):** https://claude.ai/code/artifact/dfaab6f8-6e05-4058-a5e8-61fe5b69d639 (repo copy: `docs/research/weekly-review.md`)
- **Consensus & narrative monitor — literature review (Docs):** https://claude.ai/code/artifact/40d845c6-a148-4504-9a03-f33b90072127 (repo copy: `docs/research/consensus.md`)
- **Risk & crowding — literature review (Docs), incl. "Stress testing v2":** https://claude.ai/code/artifact/f4a74a73-6de9-4269-8832-8b7959f1f5d2 (repo copy: `docs/research/risk.md`)
- **Research digester — literature review (Docs):** https://claude.ai/code/artifact/2077d29e-dfa5-4bb9-a8ff-8a39d46bbb43 (repo copy: `docs/research/digester.md`)
- **Network & reputation — literature review (Docs):** https://claude.ai/code/artifact/4e2f97b5-206a-451d-8e39-69854e5d30a9 (repo copy: `docs/research/network.md`)
- **Code:** private repo https://github.com/bdgsaraiva/pm-agent-stack (Claude GitHub App installed)
- **Daily data:** GitHub Actions workflow `daily.yml` (secrets EIA_API_KEY set; FRED optional); GDELT 12-minute budget; job timeout 40 min; ~13–19 min a run. **Started at 05:40 BRT Mon–Fri by the scheduled task "Data refresh" (trig_01FJ8P9sYVWPQtBac8oR6EBM, no push)**, because GitHub's own cron started 5–9 hours late (12–14 Oct); the cron stays as a backup. Since 14 Oct a failing offline test no longer blocks the fetch and fact pack (the job still shows red). Prices and FRED carry history back to 1986 (one-time deep fetch, run 38086467424)
- **Morning note v2:** scheduled task "Morning note" (trig_01TFXFA9NLQFrkB6dfYg3gFa), weekdays 06:18 BRT, push notification, auto-approve. If today's fact pack is missing it starts the data job and waits up to 25 minutes (notification then starts "Late data: waited <n> min"). Figures audited (fix once, flag the rest); crowd check (stage changes and idea placement only); risk line (exceptions only, plus the book's worst historical day). v2 test note (9 Oct): https://claude.ai/code/artifact/830732a4-174d-4369-bbc2-786bfc14d317
- **Friday review:** scheduled task "Friday review" (trig_01Q9SQrQjkA72XNpf2LP5pg3), Fridays 18:17 BRT, push notification, auto-approve; first run 16 Oct. Critic pass + process scorecard + risk and stress (when 2+ paper ideas are open: worst 20-day window, worst episodes) + 5-line debrief + one if-then goal.
- **Kickoff brief for new build sessions:** `docs/project/agent-build-kickoff.md` (paste prompt at its end). Builds run in Claude Code on this repo from 15 Oct.
- **Parallel track (notes, narratives, keys):** `docs/project/notes-and-keys-kickoff.md`
- **Session notes:** `docs/project/notes-A1.md` … A1 (kickoff, v0.1), A2 (frontier scan, video, frameworks), A3 (journal, note v2, video placement, CV figures, agent plan), A4 (sizing assistant, literature-first rule, USDA route), A5 (critic + number auditor), A6 (weekly review), A7 (consensus & narrative monitor), A8 (risk & crowding, incl. v2 long-history stress), A11 (research digester + network & reputation)

## Standing rule: literature first
Before building any agent:
1. Review the most cited papers, the Atlas investor cards and the specialist books.
2. Write `docs/research/<agent>.md` (finding → design change → source) and a Docs version.
3. Then build.

Applied to agents 4 (9 Oct), 5, 6, 7 and 8 (10 Oct), 10 and 11 (15 Oct), and to the agent 8 v2 revision (stress testing practice and vendors).

## Agent roster (from the PM Agent Plan)
**Running (10):**
1. Data pipeline (code).
2. Morning note (audited).
3. Journal clerk (`/journal`).
4. Sizing assistant (in the journal; drawdown cut on the marked book since agent 8).
5. Critic + number auditor (card and questions on every idea; `pmstack audit`).
6. Weekly review (scorecard + one tracked goal, in the Friday review).
7. Consensus & narrative monitor ("Consensus map" in the fact pack). Built 10 Oct, before the gate, at Bernardo's request.
8. Risk & crowding ("Risk and crowding" in the fact pack; `pmstack risk`). Built 10 Oct, before the gate (not met), at Bernardo's request; v2 the same evening: stress on history back to 1986.
10. Research digester (`/digest`: claim cards checked by code, call ledger, `notes/index.md`, critic hook). Built 15 Oct, before the gate (not met), at Bernardo's request.
11. Network & reputation (`/network`: debriefs, follow-ups, reconnects, monthly page, monthly public post). Contacts in a separate private repo. Built 15 Oct, before the gate.

**Next, in order:**
- **Gate 1 Nov:** 10 paper ideas logged, 2 Friday reviews (16 and 23 Oct).
- Own test set (7–13 Dec).
- 9 balance keeper (EIA + USDA, 14 Dec–3 Jan).
- 12 research loop (4–17 Jan). Its first jobs include the base rate and lift of agent 7's and agent 8's flags.
- Quarterly vendor review (15 Jan 2027).

**Corporate lane:** deferred (decided 9 Oct).

**Cross-cutting:** literature review before each agent; number auditor on every written output; own test set (~20 tasks) before any agent or model change; one skill + one trigger + one log line per agent; humans decide.

## Status
| # | Item | Status |
|---|------|--------|
| A1 | Design questions, architecture doc, repo v0.1 | Done (4 Oct) |
| A2 | Frontier scan; Itaú video; edge frameworks; PM Mandala; repo live; focus switch; live data fixes; scheduled note | Done (7–9 Oct) |
| A3.1 | Decision journal (capture, hard checks, stats, graveyard, open-book view) | Done (9 Oct), 10 tests |
| A3.2 | Morning note v2 + `notes/context.md` | Done (9 Oct), test-fired |
| A3.3 | Video into the project (podcast note, alert-ref scoring, pod-ready principle) | Done (9 Oct) |
| A3.4 | Atlas: Itaú Asset AI card update (text queued in notes-A3) | **Queued**, fresh claude.ai chat (the Atlas is a claude.ai artifact) |
| A3.5 | Mandala corrected with CV figures | Done (9 Oct) |
| A3.6 | Data fixes (backfill new/thin series; configured-only staleness) | Done (9 Oct) |
| A3.7 | PM Agent Plan doc; open questions decided | Done (9 Oct) |
| A4.1 | Sizing literature review (13 papers, Atlas cards, 8 books) | Done (9 Oct) |
| A4.2 | Sizing assistant in the journal: suggestion on every idea, 5 flags, `size`, `sizing-review`; 9 tests (27 total) | Done (9 Oct), commit aad1bbc |
| A4.3 | Kickoff brief for the next build chats (`agent-build-kickoff.md`) | Done (10 Oct) |
| A5.1 | Critic + auditor literature review (~40 papers, Atlas cards, 7 books), Docs + `docs/research/critic.md` | Done (10 Oct) |
| A5.2 | Critic (card, slots, save/answer/withdraw/outcome, weekly, stats) + number auditor; journal, note and Friday wiring; 15 tests (42 total); independent review, 11 defects fixed | Done (10 Oct), commit 6a5681f |
| A5.3 | Friday review scheduled task (18:17 BRT); morning-note task prompt updated for the audit | Done (10 Oct) |
| A6.1 | Weekly review literature review (~45 sources: behaviour, feedback and goals, small-sample statistics, Atlas, vendors), Docs + `docs/research/weekly-review.md` | Done (10 Oct) |
| A6.2 | Weekly review: `pmstack/review.py`, goal catalogue and tracking, exit trigger at close, monthly section; auditor binds figures to their own market; 16 tests (58 total); independent review, 11 defects fixed | Done (10 Oct), commit a050657 |
| A6.3 | Friday review task prompt updated; first goal set (`log-ideas` from 12 Oct) | Done (10 Oct) |
| A7.1 | Consensus monitor literature review (~35 papers on narratives, news text, positioning and trend; GDELT docs and biases; Atlas; books; vendors), Docs + `docs/research/consensus.md` | Done (10 Oct) |
| A7.2 | Consensus monitor: GDELT adapter (19 frozen queries), `pmstack/consensus.py` (stages, trend vote, CFTC, labels, idea placement, Fed wording), "Consensus map" in facts.md, critic crowd facts, note crowd check. Stable alert refs on rebuilt packs (closes the 9 Oct follow-up). Independent review, 8 defects fixed. 13 tests (71 total) | Done (10 Oct), commits 5c3dd3f, a8906d1, 9e64e4a |
| A7.3 | Live runs: GDELT history to 1 Jan 2017 at one point a day confirmed. HTTP 429 at 6 s pacing, so the backfill completes over several runs. GDELT's coverage collapsed after 1 Oct (678 articles on 8 Oct vs ~120k), so narratives read "stale" until it recovers | Done (10 Oct); watch |
| A8.1 | Risk & crowding literature review (~45 sources: crowding and fire sales, correlation and stress testing, CTA and vol-target flows, Atlas, books), Docs + `docs/research/risk.md`. 3 questions answered | Done (10 Oct) |
| A8.2 | Risk & crowding v1: `pmstack/risk.py` + `config/risk.yaml` (risk model, risk table in R, effective ideas, clusters, stress rows, CTA levels, crowding, warnings), fact-pack section, `pmstack risk` CLI, note and Friday skill lines; sizing drawdown cut on the marked book. Independent review, 12 defects fixed. 17 tests (88 total) | Done (10 Oct), commit 09d2017 |
| A8.3 | Live run v1 on repo data: only the example idea is open, so the book reads "example". A sample risk line passed the number auditor | Done (10 Oct) |
| A8.4 | v2 research (Bernardo: "the past shocks only look at a short history"): standard setters (BCBS, FRTB, CPMI-IOSCO, Fed GMS, EACH) and vendors and firms (MSCI, Bloomberg, Axioma, BlackRock, CME, Eurex, LCH, NBIM, Man, AQR); Docs section + `docs/research/risk.md` v2 | Done (10 Oct) |
| A8.5 | v2 build: one-time deep fetch from 1986 (prices, FRED; run 38086467424, 12.5 min, ok); `risk.history` (spliced returns, proxies, roll screen); 32-episode library replayed day by day; worst 1/5/20/60-day windows for today's book + reverse stress; 9 one-month named shocks under stress/2008/2022 correlations + isolated + analogues; worst case at 5 and 20 days. Independent review 8 defects + 2 from the live run, all fixed. 96 tests | Done (10 Oct), commits 5fc1c51, 211f6a2 |
| A9 | **Morning note outage 12–14 Oct** (three "data not refreshed" notes). Causes: (1) the fake GDELT test data shifted with the real date, so `test_narrative_stages_from_fake_gdelt` failed and stopped every data run before the fact pack; (2) GitHub's cron started the job 5–9 hours late (10:59–15:10 BRT). Fixes: date-proof fake data; tests no longer block the fetch; "Data refresh" scheduled task starts the job at 05:40 BRT; the note starts it and waits if the pack is missing. Verified: the task started run 38660994249 (18.5 min, success) and the 14 Oct pack built with every section | Done (14 Oct), commit 7493cd9 |
| A10 | Hand-off docs copied into the repo (`docs/project/`) so builds can run in Claude Code; this folder is now the source of truth. Gate re-checked: 0 of 10 paper ideas, 0 of 2 Friday reviews | Done (15 Oct) |
| N1.1 | Narratives on BigQuery: `adapters/gdelt_bq.py` (GKG partitioned, URL-path match of the frozen queries, new ids `gdeltbq:*`; dry run + byte caps 60/150/800 GB, ledger), headline links (title, source, URL, date), consensus picks the instrument per narrative, narrative tracker (`data/narratives/tracker.json`: since when, changes, headlines), facts.md Since + Headlines, note and Friday skills, headline-audit CLI. 11 tests. See `notes-N1.md` | Done in code (15 Oct); **first live run pending** |
| N1.2 | Keys wired: `daily.yml` passes GCP and USDA secrets to the fetch step (USDA unused until agent 9) | Done (15 Oct) |
| N1.3 | Follow-ups: `opec_supply_v1` retired → `opec_supply_v2`; consensus CFTC percentile from the Friday release | Done (15 Oct) |
| N1.4 | Note format from Bernardo's morning/midday/close email samples: `skills/morning-note/format.md` (structure only) and morning note v3 (levels, narrative-to-price paragraph with headline links, bulls vs bears, watching ladder) | Done (16 Oct). Morning only for now (Bernardo) |
| N1.5 | Title-or-path GKG instrument (`gdeltbqt`) after the first run left 14 of 18 narratives thin; weekday-aware gap rule | Done (16 Oct) |
| Watch | First note on the new setup (15 Oct): ran 06:20 BRT on the 05:54 BRT pack, with no wait and no "Late data". The 13:55 UTC commit was GitHub's late cron rebuilding the pack afterwards (refs stable). Keep watching for "Late data" | Closed 15 Oct; watch continues |
| Watch | GDELT: DOC API still HTTP 429; totals collapsed after 1 Oct. BigQuery route built (N1.1): check the first run's bytes, `gdeltbq:norm` (does the collapse show in the GKG too?) and articles a day per narrative | notes-and-keys track |
| Next | Coverage: 15 of 18 narratives under 20 articles a day on the GKG (title or URL path). Options: title-friendly `_v2` phrasings, or GKG themes as an instrument (notes-N1) | notes-and-keys track |
| Next | Headline audit (20–30 per narrative, `pmstack narratives audit <id>`): possible now for Hormuz, US pump prices, trade war | notes-and-keys track |
| A11.1 | Literature reviews for agents 10 and 11 (three research passes, ~45 + ~38 sources, Atlas cards, books, vendors), Docs + `docs/research/digester.md`, `docs/research/network.md`. Gate checked: not met; Bernardo: "Build anyway". 4 questions answered | Done (15 Oct) |
| A11.2 | Agent 10: `pmstack/digest.py` + `config/digest.yaml`, skill + `/digest`; critic `notes.*` facts and counter basis; journal source-ref guard; Friday review lists resolved/due guest calls. Auditor: skips YAML headers, banner after header, timestamps structural | Done (15 Oct), branch `agents-10-11` |
| A11.3 | Agent 11: `pmstack/network.py` + `config/network.yaml`, skill + `/network`; private-repo storage, MNPI attestation, follow-ups, reconnects, monthly metrics, forget, compliance log; public post pack from public-domain series only (FRED/EIA/CFTC) | Done (15 Oct), branch `agents-10-11` |
| A11.4 | Live runs: Mind Asset episode re-digested (14/14 cards anchored, audit 8/8 matched, 0 orphans after the review fixes; corrected "200+" and "five country agents" in the 9 Oct summary); public pack + chart on dated Brent (FRED); network workflow on a demo repo. Independent review: 24 defects, all fixed (notes-A11). 40 new offline tests | Done (16 Oct) |
| Waiting | Private GitHub repo for contacts (personal account, never an employer org, 2FA): then `python -m pmstack network init` and add it as origin. Check the fund's code of ethics on contact notes and public writing before the first post | **Bernardo** |
| Follow-up | Agent 7 upgrades: podcast trend-following knowledge (when shared, in `notes/podcasts/top-traders-unplugged/`), GPR/EPU validation + headline audit, curve/basis data | Later |
| Follow-up | Agent 8: (consensus.py's CFTC percentile now lags to the Friday release, N1.3); sizing's overlap cut still uses a 60-day correlation (risk uses 250 days + shrinkage) — build track. Metals, grains and softs keep unadjusted roll days (no free back-adjusted series) | Later |
| Waiting | Paper ideas in the journal (gate 1 Nov needs 10; 0 as of 15 Oct, only the example) | **Bernardo** |
| Done | USDA keys as repo secrets: `USDA_FAS_API_KEY` and `NASS_API_KEY` set 15 Oct, passed to the fetch step (N1.2) | Done (15 Oct) |
| Next | Own test set (FinanceBench-style, ~20 real tasks; include a re-digest of one episode to measure label noise and calibrate the card checks on 30–50 hand-labelled cards), then agent 9 balance keeper | Next build session |

## Decisions log (newest first)
| Date | Decision |
|------|----------|
| 16 Oct 2026 | Note format from his email models (structure only); morning note v3; midday and close notes not now (Bernardo). Narratives read the GKG title-or-path instrument |
| 15 Oct 2026 | Agents 10 and 11 built before the gate (not met: 0 of 10 ideas, 0 of 2 Friday reviews). Bernardo: "Build anyway" |
| 15 Oct 2026 | Digester: capture by pasted link or file (YouTube captions fetched by code); full transcripts local only; claim cards checked by code; guest calls scored against stored prices, prior 47.4% until 15 resolved calls |
| 15 Oct 2026 | Network: contacts and call notes in a separate private repo on the personal GitHub account; public note = short post (≤ 300 words) + one chart, in English, from public-domain data only |
| 15 Oct 2026 | Narratives move to GDELT on BigQuery as a new instrument (`gdeltbq:*`, URL-path match of the frozen queries; the GKG has no text). DOC series kept as a fallback, never mixed. Byte caps 60 GB/query, 150 GB/run, 800 GB/month. Headlines stored as title, source, URL and date only. Narrative tracker added. The notes track works in its own clone |
| 15 Oct 2026 | Agent builds move to Claude Code on the repo. Hand-off docs live in `docs/project/` (source of truth from now); the Project's `claude/` files are a 15 Oct snapshot. Docs pages and the Atlas stay claude.ai artifacts |
| 15 Oct 2026 | Parallel track split off: a separate session owns the morning note, news/BigQuery adapters, consensus.py, config/sources.yaml, config/monitor.yaml and daily.yml (`notes-and-keys-kickoff.md`) |
| 14 Oct 2026 | Data job started by a scheduled task at 05:40 BRT (GitHub cron kept as backup); offline tests report but never block the data refresh; test fake data must not depend on the real date; the morning note starts the job and waits when the pack is missing |
| 10 Oct 2026 | Agent 8 v2 (Bernardo's review): stress tests run on history back to 1986. Futures from ~2000, spot/index/yield proxies before (flagged). Old episodes never dropped. FRTB-style worst windows for today's book. Named shocks are one-month moves under stress, 2008 and 2022 correlations. Raw moves are the headline; vol-scaled is a second column. The turbulence warning, panic flag and critic base rate keep ~3–4-year lookbacks |
| 10 Oct 2026 | Agent 8 built before the gate (not met: 0 of 10 ideas, 0 of 2 Friday reviews). Bernardo: "Gate not met: build anyway" |
| 10 Oct 2026 | Risk & crowding: no budget caps, numbers only (effective ideas, share of stress risk, clusters). Amber at −3R from the 10-day high or 3+ clustered ideas at −0.5R; red = the sizing cut (−4R over 60 days), now on the marked book with open marks, through one shared function. Stress set: replays + named driver shocks + worst case at k = 3 |
| 10 Oct 2026 | Risk design from the evidence: stress P&L from scenarios, never sigma multiples, with stops honoured and gapped. Stress correlation from turbulence days. CFTC levels never alert; crowding red only under funding stress; only realised signals alert. CTA levels are context, not a forecast |
| 10 Oct 2026 | Agent 7 built before the gate (Bernardo: "go ahead with the next agent"). GDELT tried as the news source. Podcast trend knowledge to come as an upgrade |
| 10 Oct 2026 | Consensus monitor: 18 commodity-first + macro narratives (+1 EPU-style validation query). Full map daily in the fact pack; the note shows only stage changes and idea placement; the critic card carries the crowd facts. GPR/EPU validation later |
| 10 Oct 2026 | Consensus design from the evidence: attention = share of all coverage, read in 4-week vs 26-week windows. Tone only vs its own history. Trend vote of 1/3/12-month legs and CFTC percentile side by side (collinear, not two votes). Extremes = crowding context, never contrarian. Labels are inference. Descriptive until the quant gate |
| 10 Oct 2026 | Weekly review: proposed goal active Monday unless Bernardo changes it (his own choice is never overwritten). Exit trigger required at close (inferred from price at target or invalidation). Monthly section on the first Friday after month end |
| 10 Oct 2026 | Weekly review design from the evidence: process before outcome. Counts only under 10 closed ideas; intervals and shrinkage after; slices from 30 at 20 each. Brier on stated P(win) only. Tilt in both directions. Held past own invalidation, not the winner/loser gap. One if-then behaviour goal, never an R or P&L target. Review week = 7 days to 18:00 BRT Friday |
| 10 Oct 2026 | Critic asks right after capture (idea saved first). P(win) restated after the card. Unanswered questions resurface Friday |
| 10 Oct 2026 | No control group for the critic until 50 closed ideas; measure by before/after changes and per-question hit rates |
| 10 Oct 2026 | Number auditor on the morning note: fix each problem once, then banner what is left; never hold the note |
| 10 Oct 2026 | Critic design from the evidence: pre-mortem by default. Counter only on a contradicting card fact; rule only when triggered; cap 3. Card only at conviction 1–2 and ≤0.5 units. No repeat on a market within 30 days. Code picks slots, the model words them. Questions frozen. Outside view = market base rate until 6 similar ideas exist |
| 10 Oct 2026 | Friday review runs 18:17 BRT (jittered off 18:30), same task for agent 6 |
| 9 Oct 2026 | Sizing: Kelly used for relative size only (normal idea = 1.0 unit). Cap 2.0; 0.25 steps. Stated P(win) blended 50/50 with record. Overlap cut. 4R paper drawdown halves sizes. Flags for under-sizing (conviction 4–5 below 0.75× suggestion), over-sizing, stop in noise, no edge |
| 9 Oct 2026 | Literature review before every agent (papers, Atlas, books), written up before code |
| 9 Oct 2026 | Friday review 18:30 BRT. Contacts stored by name, role and firm. USDA via FAS API + NASS (no FAS/WASDE MCP exists; NASS MCP optional). Nothing corporate for now |
| 9 Oct 2026 | Agent plan: 12 narrow agents around the journal; gate 1 Nov on 10 logged ideas |
| 9 Oct 2026 | Morning note v2: journal-first, exceptions only; generic market recap dropped (commoditised) |
| 9 Oct 2026 | Decision journal is personal-build paper/example only; alert refs link alert → idea → outcome |
| 9 Oct 2026 | Standing fact: dated Brent far above futures all 2026 because of the Iran war, not a data error |
| 9 Oct 2026 | Commodity book Sharpe 1.9 since Jul 2023 vs 0.9 full record → commodities are the specialism; goal = whole book at 1.5+ |
| 9 Oct 2026 | Biggest leak: under-sizing best ideas; sizing discretionary by conviction |
| 9 Oct 2026 | Zweig: hard checks #2, #3, #11, #14 + "size your best ideas"; #7, #8, #10 monthly review; rest prompts |
| 9 Oct 2026 | Donnelly themes: psychology, poker/bet sizing, second-order + narrative. Improve network/reputation. 5–10 h/week |
| 9 Oct 2026 | Focus: commodities, US equities, US rates, USD; not Petrobras/Vale/BRL/IBOV |
| 7 Oct 2026 | Build for moats: don't build what vendors ship within ~12 months; data adapters frozen |
| 4 Oct 2026 | GitHub Actions + scheduled Claude task; sole user; morning note Docs + push; free data only |
