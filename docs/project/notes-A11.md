# Session notes A11: research digester (agent 10) and network & reputation (agent 11), 15–16 Oct 2026

Literature reviews (Docs): digester https://claude.ai/code/artifact/2077d29e-dfa5-4bb9-a8ff-8a39d46bbb43 · network https://claude.ai/code/artifact/4e2f97b5-206a-451d-8e39-69854e5d30a9 · repo: `docs/research/digester.md`, `docs/research/network.md`
Branch: `agents-10-11` (first build session run in Claude Code on Bernardo's PC).

## Context
- **Gate 1 Nov not met:** 0 of 10 paper ideas (only the Brent example), 0 of 2 Friday reviews (the first is 16 Oct). Bernardo: "Build anyway."
- **Local setup:** the PC had only Python 3.7 (32-bit). Bernardo approved installing uv; `.venv` (gitignored) now holds Python 3.12 and `requirements.txt`. Run tests with `PYTHONUTF8=1` on Windows: without it two old tests fail on encoding (`test_audit_matches_flags_orphans_dates_and_refs`, `test_one_failing_source_does_not_stop_others`); both pass in UTF-8 mode, so they are not real failures. Long scratchpad paths hit the Windows 260-character limit: use `.projtmp/` (gitignored).
- Three research sub-agents ran in parallel: digester papers; network papers, MNPI and privacy law; Atlas cards, books and vendors. Pages were opened; abstract-only and secondary reads are marked.
- **His answers to the questions:**
  - Digester capture: paste a link or a file (YouTube captions fetched by code).
  - Contacts: a separate private repo on his personal GitHub.
  - Public note: a short post (≤ 300 words) with one chart.
  - Language: English.

## What the evidence said (short)
- **Summaries go wrong on long spoken sources:** 14.7–51% of interview summaries carry an error (TofuEval); omissions in 52–85% of long summaries (FABLES); model citations unsupported ~50% (ALCE); numbers 15% wrong with perfect evidence (FinanceBench). → Claim cards with verbatim quotes, checked by code.
- **Guest calls are near coin flips:** market timers 46.9–48% (CXO; Bailey et al.); no WSJ economist beat a random walk on yields; oil surveys lose to no-change (Alquist & Kilian). Skill exists but shows only in scored records (GJP). → Call ledger; prior 47.4% until 15 resolved calls.
- **Networks:** moderately weak ties move careers most (Rajkumar et al. 2022); bridging gives better ideas (Burt 2004); dormant ties are valuable and people pick by comfort (Levin, Walter & Murnighan). The legal network premium is small (20–30 bp, Rossi et al.); the big "network wins" on record are insider cases (Martoma, PGR); CVM Res. 44 art. 13 reaches anyone with access. → MNPI attestation, role flags, give-first framing.
- **Privacy:** LGPD and GDPR apply to a professional contact list (no household exemption). → Separate private repo, minimal fields, forget command, no names outside `contacts.yaml`.
- Two widely cited LLM-finance papers (Kim, Muhn & Nikolaev) are **withdrawn**: not cited.

## What shipped
**Agent 10 — `pmstack/digest.py` + `config/digest.yaml`, skill `.claude/skills/digest/` + `/digest`**
- Capture: YouTube captions (publisher captions preferred, auto-captions marked `asr`), VTT/SRT/TXT, PDF and HTML. Full transcripts in `data/transcripts/` (gitignored); quotes ≤ 40 words.
- Claim cards checked by code: quote found in the transcript (token similarity ≥ 0.85, near the stated time first), numbers in the claim inside the quote (English and Portuguese number words, decimal commas), imported names flagged (non-blocking for translated Portuguese sources), hedges kept, deadline after the recording date, known markets only, stated levels vs the stored close, `[ASR?]` on caption names. Status ok / flagged / rejected; only ok cards reach the ledger and the critic.
- Call ledger (`digest calls`): direction, level at close or touch, flat band, beat no-change, Brier; scored only on prices up to the as-of date; speaker records with Wilson intervals, weight from 15 resolved calls.
- `digest facts`: moves since the recording and in the 5 sessions before (the only market numbers a note may add). `digest index` → `notes/index.md`. `digest diff`, `digest view`.
- Critic: `notes.*` facts on the idea's market as of the idea date; a counter question only from 2+ cards against and more against than with.
- Journal: a `notes/...` source must exist; a `call` source must be a name-free id (`call:YYYY-MM-DD-NN`).
- Friday review skill: one line per guest call resolved this week or due next week.
- Auditor: skips a note's YAML header, keeps the banner after the header (it used to land above it and break the note), treats `hh:mm:ss` as structure.

**Agent 11 — `pmstack/network.py` + `config/network.yaml`, skill `.claude/skills/network/` + `/network`**
- Storage: `../pm-network` (or `PM_NETWORK_HOME`), created by `network init`; only `contacts.yaml` holds names; calls are `calls/YYYY/YYYY-MM-DD-NN.md` with contact ids; run-log lines carry ids and counts only.
- Call notes: MNPI attestation required ("received" → refused with the stop / don't trade / tell compliance message); every promise a dated follow-up (default next day); sensitive fields refused.
- `due` (overdue, cadence gaps by layer, second touch 14–28 days), `reconnect` (dormant ≥ 365 days, novelty × engagement + one seeded random pick), `prep`, `monthly` (calls a week, follow-ups on time, bridging share, top-5/15 concentration, reciprocity, give:ask, new and decayed ties, cadence; targets beside), `forget`, `compliance-log`.
- Public post: `public pack` (facts + chart from public-domain series only: FRED, EIA, CFTC; Yahoo refused under the licence rule; CFTC counted from its Friday release), `add-call`, `score`, `check` (≤ 300 words, disclaimer, no contact names, scorecard once calls exist). Posts live in `notes/public/`.

## Live runs (15–16 Oct)
- **Agent 10, Mind Asset episode** (YouTube `vQAQYzpWXZw`, recorded 1 Oct): 24 minutes of Portuguese auto-captions, 3 windows, 14 cards, all anchored, no window uncovered. Flags for his eye: confirm "KKR" (captions say "OKR" once), "Una Fund", "Canada"; "New York" is a translation. The cards corrected the 9 Oct hand summary ("200 agents", not "200+"; "five agents", not "five country agents"). Both forecasts name no market, so they are unscoreable. The note was rewritten in his format; audit 10 of 10 figures matched, 0 orphans.
- **Agent 11:** the workflow ran on a demo repo with fictional contacts (`.projtmp/`, not committed): phone field refused, MNPI note refused, follow-ups dated, a dormant allocator surfaced. Public pack on dated Brent (FRED DCOILBRENTEU) as of 15 Oct: last 125.44 on 6 Oct; the chart is in the network Docs page. Spot carries the 2026 physical premium (standing fact), so a post must say "dated Brent".
- Tests: 40 new offline tests (synthetic prices, no network), including the review regressions.

## Independent review (16 Oct): 24 defects, all fixed
A sub-agent that didn't build the agents reviewed the staged diff (the first attempt hit the usage limit). Each fix has a regression test (`tests/test_digest.py`, `tests/test_network_review.py`).
1. **(High)** A near-match quote could change a number, drop a hedge or add "not" and still pass → `quote_altered`: a fuzzy match may not differ from the transcript on a number, negation or hedge.
2. Public scorecard could fall back to Yahoo for a call without a recorded series → re-resolves the public series every time; a mismatch is refused.
3. Calls were scored on stale prices (FRED ends 6 Oct) → a call resolves the day after its deadline and only with a close within 7 days of it; otherwise `pending-data`.
4. A card could label its own probability "inferred" or itself "translated" → a card probability is always "stated" and must appear as a percentage; translation comes from the transcript language.
5. Numbers glued to letters (USD150), ".5", spoken prefixes ("eighty five" also 80), probabilities matching any number, and "1.500" read both ways → language-aware readings, full spoken values only, percentages for probabilities.
6. Names at the start of a claim ("Citi: …") were never checked → checked unless a common word.
7. The auditor skipped any text between two opening "---" lines → only a real YAML header (with type or date) is skipped; its `questions` and `source_note` are audited.
8. Follow-ups closed later counted as closed on earlier dates → open on any date before they were closed.
9. A first call with an old contact counted as a new tie (and asked for a second touch) → it is a reconnect.
10. The post check silently skipped names when the network repo was missing, and missed surnames → it says so, and matches name parts of 4+ letters.
11. `forget` reused ids and left shared calls' text → ids never reused (`last_id`); shared calls listed under `redact_by_hand`.
12. "May" (the month) read as a hedge; deadlines unchecked → month ignored; a deadline with no time phrase is flagged.
13. Flat calls with a level scored as "down"; a level equal to the start read as "down" → flat ignores the level side; equal level = flat.
14. Claim numbers read two ways; "12y" mangled → claims in English convention; market names stripped on word boundaries.
15–18. Future months, nested or camelCase sensitive keys (`phoneNumber`, `personal.spouse`), a network home inside this repo, malformed notes or cards, bad CLI input → refused or skipped with a message.
19. The critic counted cards, not people → counter question from 2+ distinct speakers.
20. An episode recorded before an idea but published after reached its card → header `published` sets when cards become usable.
21. Contact names elsewhere in a journal entry → flagged when the private repo is on the machine.
22. "None received." was read as "received" → normalised; a separate message for an unreadable attestation.
23. Backdated packs dropped CFTC → the report public on the as-of date is used.
24. "# 3 things…" set the issue number → taken from "note #N".
Nits fixed: call drafts live in the private repo (gitignored) and are deleted; "Name (Firm)" and "Name" are one speaker; "Will" vs "will" matched case-sensitively. Kept: critic facts quote a claim's text (its numbers are checked on the card).

After the fixes the live note was re-digested (14/14 ok) and re-audited (8 of 8 figures matched, 0 orphans). A heredoc quirk in Git Bash turned `\b` into backspace characters during the fixes; caught by a scan of every changed file (none left).

## Open items
- **Bernardo:** create the private GitHub repo `pm-network` on the personal account (2FA, never an employer org), run `python -m pmstack network init`, add it as `origin`. Check the fund's code of ethics on contact notes and public writing before the first post.
- **Git identity:** this PC had no git author configured; the commit waits for his choice.
- **Merge:** the Friday review task runs on `main`; the guest-call lines reach it only after `agents-10-11` is merged.
- **Morning note (notes-and-keys track):** may add "≤ 3 cards on open ideas" from `digest view`; not wired here (that session owns the skill).
- **Own test set (next):** re-digest one episode to measure label noise; hand-label 30–50 cards to calibrate the quote threshold and an optional entailment checker (MiniCheck-class).
- **PM Agent Plan doc: updated from this session (16 Oct)**: roster rows 10 and 11 → Running; the lead now names ten running agents with links to both review pages; the schedule paragraph says they shipped 15 Oct before the gate and that the own test set and agent 9 can move earlier. Not changed: the doc has no per-agent sections for 10 and 11 to link (only the roster and a "Call notes" bullet), and the Atlas card updates from A3.4 remain queued for a claude.ai chat.
