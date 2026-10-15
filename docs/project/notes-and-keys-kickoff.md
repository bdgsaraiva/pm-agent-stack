# Kickoff brief: notes, narratives and keys (written 15 Oct 2026)

A separate session from the agent builds (`docs/project/agent-build-kickoff.md`). This session owns the morning note, the narrative tracking, the news sources and the data keys. Both push to the same repo, so pull before every push and stay inside your own files. (Repo copy since 15 Oct; Project paths `claude/…` became `docs/project/…`.)

## 1. Where things stand
- **The morning note runs** (scheduled task 06:18 BRT, trig_01TFXFA9NLQFrkB6dfYg3gFa). The "Data refresh" task (trig_01FJ8P9sYVWPQtBac8oR6EBM) starts the data job at 05:40 BRT. The 12–14 Oct outage is fixed (see `docs/project/agents-plan.md`, row A9).
- **Bernardo's feedback (15 Oct):** the note has no news to link, and what matters most is to keep track of the narratives.
- **Why there are no news links:** the note takes figures only from the fact pack, and the fact pack has no headlines. The narrative series comes from GDELT's DOC API, which has been rate-limited (HTTP 429) and nearly empty since 1 Oct. So the 18 narratives read "stale". The OPEC query also fails with "The specified phrase is too short".
- **Keys:** Bernardo is adding these as GitHub repo secrets, following the steps given in chat on 15 Oct:
  - `USDA_FAS_API_KEY` and `NASS_API_KEY`, for the balance keeper (agent 9, December);
  - `GCP_SA_KEY` (a service-account JSON) and `GCP_PROJECT_ID`, for GDELT via BigQuery.
  - Check which exist with `gh secret list --repo bdgsaraiva/pm-agent-stack`; that lists names only. Never read, print or store a key.

## 2. Jobs for this session, in order
1. **Narratives back on, with links.** Literature first is already done (`docs/research/consensus.md`). The decision here is about the data source:
   - **Measured series:** GDELT through BigQuery once `GCP_SA_KEY` exists. Use the partitioned tables (`gdelt-bq.gdeltv2.gkg_partitioned`, filtered on `_PARTITIONTIME`) and set `maximum_bytes_billed` on every query. Stay inside the BigQuery sandbox's free 1 TiB a month: a daily run reads one day's partition only; the backfill is done once, in chunks. GDELT's own blog shows a 15-day partitioned GKG query reading about 15 GB, against 423 GB for the unpartitioned table. Keep the 18 frozen queries' meaning; a change gets a new `_vN` id (and the OPEC query needs one).
   - **Headlines to link:** the top article URLs per narrative per day. Either take them from the GKG `DocumentIdentifier` field, or from a keyless per-narrative headline feed if one is reliable from GitHub Actions. Store title, source, URL and date only, never article text. The note links at most 3 headlines per narrative that changed stage.
   - **A narrative tracker:** one running record per narrative (stage, share, links, and the date it changed), so the note and the Friday review can say "since when" and "what moved it". Do the 20–30 headline audit per narrative (the GPR/EPU validation step) as soon as headlines exist.
2. **Note format, modelled on Bernardo's emails.** He receives morning, midday and close notes by email (Outlook web) that he considers great models. The access decision was made on 15 Oct; see section 3.
   - From the samples he attaches, write a format spec in `skills/morning-note/format.md`: sections, order, length, tone, how news is linked, and what each of the three notes is for. Keep structure only.
   - Then revise the morning note skill.
   - Ask him once whether he also wants midday and close notes. Each would be a new scheduled task needing a fresh fact pack, so it means intraday data runs.
3. **Keys wiring.** Once the secrets exist:
   - Add the BigQuery adapter (GitHub Actions only, with a time and byte budget like every source).
   - Pass the USDA secrets into `daily.yml` as env vars, ready for agent 9. Don't build agent 9 here.
4. **Small follow-ups:**
   - Agent 7's CFTC percentile counts from the Friday release (risk.py already does).
   - Watch the first notes for "Late data".

## 3. Access to the email models (decided 15 Oct)
- **Use exported samples, not a mailbox connection.**
  - Bernardo saves one recent morning, one midday and one close email as PDF ("Print → Save as PDF" in Outlook web) and attaches them in this session.
  - Read them for structure only. Store no content, figures, names or text from them in the repo, the project, prompts, notes or logs.
  - Delete the local copies after the format spec is written.
- **Why not a connector or the browser:**
  - A model is needed once, not as a daily feed.
  - These look like broker or sell-side notes in his work mailbox, and the personal build's hard rule bars broker research.
  - The Microsoft 365 connector is built for work accounts, so connecting it belongs to the corporate lane, on the corporate Claude account.
- **If he wants the emails as a live input later,** that is the corporate build (Microsoft 365 connector, corporate account), not this repo. Before attaching samples, he checks that sharing them with a personal Claude account is fine under his firm's policy.

## 4. Rules (same as the agent builds)
- Personal build: paper ideas and public data only. Numbers come from code and pass the number auditor.
- Never handle keys: don't print, store or paste them; GitHub secrets only.
- Ask at most once per job, multiple choice, recommended option first. Keep chat replies short.
- **Coordination with the agent-build session:**
  - This session owns `skills/morning-note/`, `pmstack/adapters/` (new news and BigQuery sources), `pmstack/consensus.py`, `config/monitor.yaml`, `config/sources.yaml` and `.github/workflows/daily.yml`.
  - The other session owns new agent modules and their configs.
  - Run `git pull --rebase` before every push. Run the full test suite before every push. Tests must not depend on the real date.
- **Hand-off:** update `docs/project/agents-plan.md` (status rows) and write `docs/project/notes-N1.md`.

## Paste this into a new session on the repo
```
Continue phase 2 of my "Future of Asset Management and Trading" project: the notes, narratives and keys track (not the agent builds).
Read docs/project/notes-and-keys-kickoff.md and follow it, then docs/project/agents-plan.md (row A9 and the watch items).
Jobs in order: (1) narratives back on with headline links (GDELT via BigQuery once GCP_SA_KEY exists; check with gh secret list), plus a narrative tracker; (2) note format modelled on my morning/midday/close emails, from the PDF samples I attach (structure only, store no content); (3) wire the USDA and BigQuery secrets; (4) small follow-ups.
CLAUDE.md has the hard rules. Personal build only: paper ideas and public data. Another session builds agents 10 and 11 in parallel: pull before every push and stay in your own files.
```
