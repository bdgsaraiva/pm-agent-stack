# Session notes A16: specialists S2, the Quant agent (agent 13), 24 Oct 2026

Brief: `docs/project/specialists-kickoff.md` (section 3.4, 3.5, S2 in section 5). Same worktree as A15 (`claude/specialists-kickoff-27d712`), synced with main first (no new commits there).

## Bernardo's decision (24 Oct)
- **Tape card every weekday:** the routine at 17:15 New York time starts `close.yml`, waits, then writes, audits and commits the card.

## Literature
Two parallel passes plus the quant-research-standards skill, written up in `docs/research/quant.md`.
- Trend: MOP 2012, HOP 2017, Levine & Pedersen; counterpoints Huang et al. 2020 and Kim, Tse & Wald 2016.
- Carry and term structure: KMPV 2018, Erb & Harvey, Szymanowska, Boons & Porras Prado, Bakshi et al., Fuertes et al.
- Positioning: Hong & Yogo, Kang, Rouwenhorst & Tang, GHR.
- Vol: Trolle & Schwartz, Prokopczuk et al., the OVX/GVZ methodology.
- Correlation: Tang & Xiong, Silvennoinen & Thorp; counterpoint Forbes & Rigobon.
- Seasonality: Keloharju et al.; counterpoint Sullivan, Timmermann & White.
- Vol targeting: Moreira & Muir vs Cederburg et al.; Harvey et al.

## What shipped
- **`pmstack/quant/`**: trend (reuses agent 8's `cta_levels`), vol, corr, seasonal, positioning, curve (carry; basis momentum n/a until 12 months of curve), tape.
- **`config/quant.yaml`**: 16 markets (energy, metals, ags, ES, NQ, ZN, DXY).
- **`config/sources.d/quant.yaml`**: OVX and GVZ via FRED; checked live (both to 2026-10-22).
- **`pmstack/filer.py` (`pmstack file-reports`)**: the report-day filer, no model. It files the WPSR and WNGSR series and CFTC managed money into the facts log with their release time. Release times are assumed conservatively at the EST offset, so in summer they read an hour late, never early. Idempotent: 40 facts on the first run, 0 on the second. Point-in-time reads checked (the 15 Oct holiday Thursday).
- **`.github/workflows/close.yml`**: fetches closes, curve and implied vol, plus EIA (Wednesday/Thursday) and CFTC (Friday); files releases; builds the tape; commits. It shares the `daily` concurrency group with the morning job. Backup cron 20:40 BRT.
- **Routine "Close tape"** (trig_01VH8Gy3b9eCVHfCi6xitsXQ): weekdays 17:15 New York time (18:15 BRT while the US is on summer time, 19:15 BRT after 1 Nov), Opus 5.5, **auto permission mode**, push notification. First run Monday 26 Oct.
- **Tape card**: `config/tape_card.schema.json`, validated by `pmstack/cards.py` (same rules as state cards). Skill `.claude/skills/tape/` + `/tape`.
- **Notes track spec**: `docs/project/quant-overnight-spec.md`, the overnight change against the flip levels for the morning note.
- **Live run (tape as of 2026-10-23)**:
  - flips: Henry Hub and corn 3-month legs;
  - stretched: silver 1-month, corn 1-month, sugar 3-month;
  - VIX gap at the 93rd percentile of three years;
  - average commodity cross-correlation 0.09, percentile 1 of three years.
  - Card `cards/tape/2026-10-23-quant.json`; answer `cards/answers/2026-10-23-tape.md` audited 16 matched / 0 orphans.
- **Tests**: `tests/test_quant.py`, 12 cases: flips, stretch, vol regime and implied gap, correlation band, seasonal point in time, CFTC release lag, carry, tape build and card, filer point in time with revisions and backlog, tape-card validator (wrong citation, relabel, trade words, one card a day), stale close and stable ids. Full suite 424 passed.
- **Actions minutes**: October so far about 670 (daily job about 18 minutes a run). The close job adds about 5 minutes a weekday.

## Independent review (a sub-agent that did not build it): 16 findings (3 High, 8 Medium, 5 Low)
| # | Sev | Finding | Fix |
|---|---|---|---|
| 1 | High | The filer back-dated revisions: a revised value got the original release time, so a read as of release day saw the revision (look-ahead in the facts log) | A value already known with a different figure is filed at the time it is seen. A first print keeps its release time only if filed within 7 days of release, so backlog weeks are known from the filing. Local log re-filed under the new rule |
| 2 | High | The tape-card validator matched figures to any source (264 rows, many 0-100 integers) and checked neither labels nor wording | A source must equal its pack row (label and origin too). Each figure must match a source cited in its own sentence; a sentence with figures and no citation fails. Banned trade and forecast words on tape cards. Applies to state cards too (the Energy card re-validates) |
| 3 | High | Brent positioning was the WTI series (067651) | `cftc` dropped for BZ=F |
| 4 | Med | A stale close (holiday, failed fetch) re-reported yesterday's flips | `stale` per market and per tape. Flips and big moves are suppressed. The routine writes no card on a stale tape |
| 5 | Med | "Beyond 2 sd" meant nothing for the 3- and 12-month legs; the printed distance (EWMA 0.94) and its percentile (60-day sd) were different numbers | One distance series (trailing 60-day daily sd), printed and ranked. Threshold scaled to h-day sd (distance / sqrt(h) ≥ 1) |
| 6 | Med | The CFTC release lag was fixed at 3 days (Monday release in holiday weeks) | Positioning and the filer use the holiday-aware release, checked identical to `research.cftc_release` on every Tuesday since 2015, with the calendar cached (the first version made the tape take 2 minutes) |
| 7 | Med | Implied vol (FRED, a day behind) was compared with today's realised vol | The gap uses realised vol on the implied index's own date |
| 8 | Med | The backup cron ran every day and rebuilt the tape; source ids were positional | The backup skips a day whose tape exists. Source ids are stable hashes of each row's origin |
| 9 | Med | Commit races between the bot and the routine | Push retry loop, tape artifact, union merge for JSONL logs. The routine captures its run id, watches it, checks the tape is fresh, and never writes the tape itself |
| 10 | Med | Yahoo roll gaps sit in the 3/12-month flip levels and the seasonal norms | Caveat in the tape and skill. Roll-adjusted series wait for the curve history |
| 11 | Med | 19:10 BRT is after Globex reopens while the US is on summer time | The routine runs at 17:15 New York time (inside the halt in both regimes) |
| 12 | Low | Correlation differenced before joining calendars | Closes joined first, then differenced |
| 13 | Low | "Now" in the average correlation was a day old | The last step always included |
| 14 | Low | The correlation band rests on few independent windows | `independent_windows` reported |
| 15 | Low | `watch` forced at least one line | May be empty |
| 16 | Low | Re-runs made duplicate tape cards | One tape card a day; a second save is refused |
Live run redone under the new rules: tape rebuilt, card re-saved, answer audited 16 matched / 0 unbound / 0 orphans (the first draft had 4 unbound: "-9.1 daily sd" hides the unit from the auditor, so the skill now says "-9.1 sd (daily)").

## Workflow live check
Run 40142464672 (Saturday 24 Oct, dispatched once by hand): all steps succeeded in about 1.5 minutes: prices, curve (21,946 contract rows from 2025), OVX/GVZ history (9,526 rows), filer (nothing new), tape written and marked stale (no Saturday close), committed (93642e9). The routine first runs Monday 26 Oct at 17:15 New York time.

## Open items
- Watch the first close run and routine (Monday 26 Oct, 17:15 New York time = 18:15 BRT).
- The vol estimators differ: agent 8's EWMA 0.94 vs the tape's trailing 60-day sd vs MOP's 60-day centre of mass. Unify in agent 8's next revision.
- Stretched and flipped are print rules: register studies before any use beyond description.
- The notes track picks up the overnight-change spec when it resumes.

## PM Agent Plan (Docs) updates this session could not make
- Roster: agent 13 "Quant" live (tape after the close, daily card).
- Schedule: S2 done 24 Oct.
- A Docs version of the quant literature review (repo copy only so far).
