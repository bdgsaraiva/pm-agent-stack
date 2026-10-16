---
title: Research digester — literature review
agent: 10 (research digester)
date: 2026-10-15
status: reviewed before build; code in pmstack/digest.py, parameters in config/digest.yaml, skill in .claude/skills/digest/
docs: https://claude.ai/code/artifact/2077d29e-dfa5-4bb9-a8ff-8a39d46bbb43
---

# Research digester — literature review

**Answer.** Build the digester around atomic **claim cards** checked by code, not around a summary. LLM summaries of long, conversational sources are wrong often enough to matter: 14.7–51% of interview summaries carry at least one factual error (TofuEval), omissions hit 52–85% of book-length summaries (FABLES), and model-emitted citations are unsupported about half the time (ALCE). So every card carries a verbatim quote that code finds in the transcript, every number on a card must sit in its quote, and the model never supplies a market level. The value is not reading (summaries are a low-utility learning technique) but **reuse at decision time**: a call ledger scored against no-change benchmarks, guest track records, and an index the critic reads when an idea is logged. Public market timers are right 46.9–48% of the time and oil surveys lose to no-change, so a guest's call starts at the base rate and earns weight only through a scored record.

Method: three research passes on 15 Oct 2026 (LLM faithfulness and finance extraction; media and expert-call value; Atlas cards, books and vendors), ~45 papers and pages opened. "Abstract" = only the abstract read; "secondary" = someone else's summary. Book points not page-checked are marked.

## 1. Papers: LLM faithfulness on long, spoken sources

| Finding | What it changes | Source |
|---|---|---|
| 73–79% of pre-LLM summaries hallucinated; entailment correlates with human judgement (Spearman 0.43), ROUGE does not (0.16). Extrinsic content (not in the source) dominates. | No similarity-score quality gate. Rule: no claim without a source span. | Maynez et al. 2020 (read) |
| Showing the supporting span next to a claim cut human verification time 21%. | Each card shows its quote; spot-checks are fast. | Kryscinski et al. 2020, FactCC (read) |
| Sentence-level NLI fixes the granularity mismatch (74.4% balanced accuracy). | Check card vs its own quote, never whole summary vs whole transcript. | Laban et al. 2022, SummaC (abstract) |
| Atomic facts make factuality measurable; ChatGPT 58% supported on biographies. | The **claim card** is the unit; each card scored supported/unsupported. | Min et al. 2023, FActScore (abstract) |
| Interview/dialogue summaries: 4.4–29% of sentences wrong on main topics, 9.4–42% on side topics; 14.7–51% of summaries have ≥1 error. GPT-4 as judge 64.9–90.3 balanced accuracy. | Side-topic remarks (where guests make off-hand calls) get checked too; LLM judge only as a second opinion. | Tang et al. 2024, TofuEval (read) |
| Book-length: unfaithful claims 2.1–11.5% by model; best auto-rater F1 58.2; omissions in 52–85% of summaries; end-of-book over-weighted. | Chunked extraction plus a **coverage check** (windows with no card are listed). | Kim et al. 2024, FABLES (read) |
| Facts in the middle of a long context: 53.8% vs 75.8% at the start, below closed-book (56.1%). | Never one-shot a 2-hour transcript; extract per time window. | Liu et al. 2024, Lost in the middle (read) |
| Long-context synthesis with citations: <20% joint score without retrieval vs ~56% for humans. | Cross-episode questions retrieve stored cards; no synthesis over raw transcripts. | Laban et al. 2024, Summary of a Haystack (abstract) |
| Model citations lack full support ~50% of the time. | A citation the model emits is not evidence: code checks the quote exists. | Gao et al. 2023, ALCE (abstract) |
| A 770M checker matches GPT-4 grounding at ~400× lower cost; most LLMs near chance on SummEdits. | A dedicated checker is affordable later; the summarising model never self-certifies. | Tang, Laban & Durrett 2024; Laban et al. 2023 (abstracts) |
| Hallucination leaderboard (22 Sep 2026): best models 1.8–5%, several frontier models 12–15%. | Newest ≠ most faithful; temperature 0; re-check before changing model. | Vectara leaderboard (read) |
| LLM research summaries overgeneralise 4.85× more than experts; "be accurate" prompts make it worse (OR 1.90); temperature 0 cuts it ~76%. Quantified → generic and past → present are the common shifts. | Hedge words kept verbatim in their own field; no tense or quantifier changes. | Peters & Chin-Yee 2025 (read) |
| ASR: entity WER 45–52% (persons) and 36–44% (organisations) on earnings calls vs 5–10% for dates; Whisper invents whole phrases in ~1% of clips, often at pauses. | Auto-captions are a source of error: names and firms flagged `[ASR?]` unless confirmed; publisher transcripts preferred. | Del Rio et al. 2021, Earnings-21 (read); Koenecke et al. 2024 (abstract) |

## 2. Papers: finance extraction, numbers and dated material

| Finding | What it changes | Source |
|---|---|---|
| Earnings-call summaries: extract-then-paraphrase gave the best numeric precision (0.916); a baseline produced wrong figures and one dropped "adjusted". | Extract verbatim first, paraphrase second; metric qualifiers (adjusted, YoY, contract month) are part of the number. | Mukherjee et al. 2022, ECTSum (read) |
| GPT-4-Turbo still 15% wrong with oracle evidence; 66% of questions need arithmetic. | The model computes nothing; derived figures (move since recording, distance to a guest's target) come from code. | Islam et al. 2023, FinanceBench (read) |
| "Bloated disclosures" and "Financial statement analysis with LLMs" are **withdrawn** (replication failed / data inconsistencies). | Not cited; LLM-in-finance claims treated as unreplicated by default. | Kim, Muhn & Nikolaev withdrawal notices (read) |
| LLM headline sentiment: Sharpe 6.54 (Q4 2021) → 1.22 (2024), small caps, unprofitable at 20 bp costs. | Tone of a podcast is descriptive, never a signal. | Lopez-Lira & Tang 2023 (read) |
| "COVID-19" leaked into 2019-call outputs 6.8% of the time with a no-future instruction (12.2% without); masked firms re-identified 70%. | Every card carries `as_of` (recording date); terms on a card that are not in its quote are flagged as extrinsic. | Sarkar & Vafa 2024 (read) |
| GPT-4o recalls pre-cutoff S&P levels within 0.61% and is ~17% off after; masked mega-cap calls identified 100%. | The model never supplies levels; a guest's stated level is checked against stored prices for that date. | Lopez-Lira, Tang & Zhu 2025 (read) |
| Model's background knowledge distorts its reading of text ("distraction effect"). | Report only what the speaker said; no "context" from the model. | Glasserman & Lin 2023 (abstract) |

## 3. Papers: how much a guest's call is worth, and how to track it

| Finding | What it changes | Source |
|---|---|---|
| Media pessimism predicts −8.1 bp next day, 6.8 bp reversed over days 2–5; pessimism follows low returns. | Tone stored as descriptive only, next to the asset's move in the 5 trading days before recording (code). | Tetlock 2007 (read) |
| Local coverage raised local trading ~48% (8–9% strict FE); vanished when delivery was disrupted. | Exposure moves behaviour regardless of content: calls reach the critic with a base rate and record attached, never alone. | Engelberg & Parsons 2011 (read) |
| Mad Money: overnight spike, reversed within ~12 days. | A broadcast call is likely priced: the card shows days and move since recording. | Engelberg, Sasseville & Williams 2012 (abstract; CXO secondary) |
| Seeking Alpha negative-word share predicts 3-month returns and earnings surprises. | Reasoned argument can carry information: keep the guest's because/unless, discount the tone. | Chen, De, Hu & Hwang 2014 (read) |
| 68 market timers, 6,582 forecasts: 46.9% right; >70% rare. Method: horizon-matched, detrended, vague calls excluded. | Template for scoring; unscoreable statements get no weight. | CXO Advisory Guru Grades (read) |
| Re-scored by specificity and horizon: 48%; 67.6% of correct calls were short-term. | Specificity (level + date) recorded on the card. | Bailey, Borwein, Salehipour & López de Prado 2018 (read) |
| WSJ panel: none of 33 economists beat a random walk on the bond yield or USD/JPY. | Rates and FX calls scored against no-change. | Mitchell & Pearce 2007 (read) |
| Oil 1–12 months: no-change beat futures at most horizons and was "much more accurate" than surveys. | Commodity calls scored against no-change **and** the futures price on the recording date. | Alquist & Kilian 2008 (read) |
| Expert political judgement: experts barely beat simple models, excuse misses as "off on timing". GJP: training, teams, selection ~10% each; supers persist (~70% kept status). | Each forecast needs a resolvable statement, a deadline and a probability, so a Brier score exists. A guest record means something only after ~15–20 resolved calls. | Tetlock, Mellers, Rohrbaugh & Chen 2014 (read); AI Impacts GJP summary (secondary) |
| Foxes beat hedgehogs on accuracy and calibration. | Style is context, not a weight; the record decides. | Long Now talk summary (secondary) |

## 4. Papers: attention and memory

| Finding | What it changes | Source |
|---|---|---|
| More same-day announcements → weaker immediate reaction, stronger drift. | Push only cards on open ideas or the watch list; the rest stays in the index. | Hirshleifer, Lim & Teoh 2009 (abstract) |
| Friday announcements: 60% of the reaction delayed vs 40%. | Low-attention arrivals get re-surfaced at the Friday review. | DellaVigna & Pollet 2009 (abstract) |
| Recall tests: 61% retained after a week vs 40% for re-reading. Summarisation and re-reading rate "low utility". | The digest's value is retrieval at decision time (journal + critic), not reading. | Roediger & Karpicke 2006 (read); Dunlosky et al. 2013 (read) |

No rigorous study of "second brain" note systems for investors was found; treat such claims as opinion.

## 5. Counterpoint

| Finding | What it changes | Source |
|---|---|---|
| GPT-3 news summaries preferred 57–58% of the time; factual errors "rare". | The narrative gist is not heavily checked. | Goyal, Li & Durrett 2022 (read) |
| LLM rated faithful 0.98 vs 0.93 for freelance writers; more extractive. | Extractiveness helps traceability. | Zhang et al. 2024 (read) |
| Human reference summaries hallucinated more than GPT-4 on most tasks. | Compare the agent against the transcript, not against old hand notes. | Pu, Gao & Wan 2023 (read) |

**Resolution:** these results are on short news. Podcasts are long, spoken, hedged and full of numbers, the conditions where errors are material. So **scale checks to stakes**: the gist is light; every data or forecast card that can reach the critic gets the full checks.

## 6. Atlas investors and institutions

- **Narrow agents, one store** (Balyasny, Coatue Mosaic, Elliott's central research store; Atlas 4C, 4G, 4.5 step 1): one digester with per-source sub-formats (podcast, paper, note, letter) writing into the research memory beside the journal.
- **Questions, not conclusions** (Man Group's PM toolkit drafts questions, 4C): every digest ends with "questions to ask next", which agent 11 carries into the next call.
- **Consensus counted, not asserted** (BlackRock Macro Decoder, J.P. Morgan SpectrumIQ, 4A): per asset, how many stored cards lean each way and the spread of their levels.
- **Diff recurring sources** (Klarman compares years of reports; Marks' dated memo archive, 3D/4G): for a repeat guest or series, the headline is what changed since last time.
- **Sceptical avatar** (Viking, 4G): cards against an open idea go to the critic.
- **Commodity traders** (Hall: structural vs tactical; King: supply responds to price, 3F): horizon splits tactical/structural.
- **Memorisation risk** (Atlas 4.2, 4.7): as-of on every claim; the model never fills in outcomes.
- **Griffin called a gen-AI commodity report "garbage" past its first sentence** (4F): generic prose is the failure mode; keep numbers and named speakers.

## 7. Books (not page-checked unless marked)

- **Ahrens, *How to Take Smart Notes*** (zettelkasten.de, page-checked): one idea per note with a stable id; links say why → card ids, `relation` field (supports / contradicts / updates).
- **Forte, progressive summarisation** (fortelabs.com, page-checked): layers → key-message line (morning note), cards (critic), full note (archive).
- **Tetlock & Gardner, *Superforecasting*** (fs.blog, page-checked): numeric probabilities, "what would change my mind", score with Brier → `probability`, `unless` fields; ledger.
- **Mauboussin** (Wharton interview, page-checked): skill vs luck; under-sampled failure; "what's priced" → keep wrong calls; consensus field.
- **Duke, *Thinking in Bets* / *Quit*** (general knowledge for "resulting"): judge the argument separately from the outcome.
- **Kahneman, Sibony & Sunstein, *Noise*** (secondary): scatter is measurable without truth → periodic re-digest of the same episode to measure label noise (own test set).

## 8. Vendors (build only what stays scarce)

Snipd and Podwise ship podcast transcripts, chapters and highlight export (Podwise has an API/MCP); Perplexity Finance (Quartr) and Bloomberg ship earnings-call summaries; AlphaSense/Tegus ship expert-call transcripts (paid; broker/expert content is out of scope here). **Not shipped by anyone:** Bernardo's format and labels, a call ledger scored against no-change and futures, guest track records (CXO stopped in 2012), and an index tied to his decision journal. Build those; buy or reuse capture.

## 9. Where sources disagree

1. LLM summaries good enough? Yes on short news (Goyal, Zhang, Pu); no on long dialogue, books and numbers (TofuEval, FABLES, FinanceBench, Peters). → Checks scaled to stakes.
2. LLM as judge? Best available on dialogue (TofuEval) vs near chance (SummEdits) → code checks first, LLM second opinion, calibrated on his own episodes.
3. Look-ahead? Minor out of sample (Glasserman & Lin) vs persistent leakage (Sarkar & Vafa; Lopez-Lira et al.) → detect extrinsic content, don't trust instructions.
4. Opinion media: noise (Tetlock 2007, Mad Money) vs information (Chen et al.) → keep argument, discount tone.
5. Expert skill: mostly none (CXO, WSJ, oil surveys) vs a rare persistent minority (GJP) → let the scored record set the weight.

## 10. Design changes vs the plan

| Item | Plan (PM Agent Plan row 10) | Now |
|---|---|---|
| Unit | A note in the summary format | Claim cards (speaker, timestamp, verbatim quote, assets, type data/forecast/opinion, horizon tactical/structural, because/unless, hedge words verbatim, as-of); the 3-part note is rendered from verified cards + a short gist |
| Pipeline | Transcript → note | Chunked extract-then-abstract (~10-minute windows); coverage check lists empty windows |
| Checks | — | Code: quote found in transcript (fuzzy ≥ 0.9), every number on a card inside its quote, extrinsic terms flagged, `[ASR?]` on names and firms from auto-captions, levels a guest states checked against stored prices on the recording date (data cards). LLM judge as a second opinion only |
| Numbers | — | Model computes nothing; move since recording and benchmarks from code with links |
| Calls | — | Call ledger: resolvable forecast cards (market, direction or level, deadline, probability stated or from a fixed hedge lexicon) scored by code against no-change (and futures for commodities); unscoreable calls carry no weight |
| Guest weight | — | Base rate (~47–48%) until ~15 resolved calls; then hit rate with Wilson interval and Brier vs benchmark |
| Index | List of episodes | `notes/index.md` (one line per note) + `notes/claims.jsonl` queried by market, speaker, type, horizon |
| Reuse | Critic and note | Critic card gets `notes.*` facts on the idea's market (cards for/against, latest, guest records), descriptive; morning note ≤ 3 cards on open ideas; `journal new --source podcast --source-ref <note>` checked to exist |
| Recurring sources | — | "What changed since last time" for a repeat guest or series |
| Storage | — | Notes and short quotes committed; full transcripts kept local only (copyright), hash recorded |

## 11. How it works (worked example: live run, 15 Oct 2026)

Source: Mind Asset (Itaú Asset), "Fundos multimercado: IA, alternativos e o futuro da gestão", recorded 2026-10-01 (https://www.youtube.com/watch?v=vQAQYzpWXZw).
1. `digest fetch` stored 24 minutes of Portuguese auto-captions locally (4,341 words, 3 windows, `asr: true`).
2. 14 cards extracted window by window; `digest save`: all 14 quotes anchored, no window uncovered.
3. Flags for his eye: confirm KKR (the captions say "OKR" once), Una Fund, Canada; "New York" is a translation of "Nova York".
4. The cards corrected the 9 Oct hand summary: "200 agents" (not "200+"), "five agents" by year-end (not "five country agents").
5. The two forecasts name no market, so they are unscoreable and carry no weight.
6. The note was rewritten in his format from the cards; audit (after the review fixes and a rewording): 8 of 8 figures matched, 0 orphans.
7. Found by the live run and fixed: `audit --flag` put its banner above a note's YAML header (now after it); the header was audited as prose (now skipped); `hh:mm:ss` timestamps were read as figures (now structure); "AI" matched the Portuguese "aí" after accent folding (acronyms now match case-sensitively); the old note's `guests` list had been split by YAML at a comma.

Example card c8: speaker Arlindo Penteado, 00:15:47, quote "E hoje a gente tá com esses 200 agentes já operando.", claim "About 200 AI agents are already operating.", type data, status ok.

## 12. Independent review (16 Oct 2026): findings fixed

A reviewer that didn't build the agent found 24 defects across agents 10 and 11 (full list: `docs/project/notes-A11.md`). Those in the digester, all fixed with regression tests:
- **A near-match quote could change a number, drop a hedge or add a negation** and pass (similarity 0.86–0.97). Now `quote_altered` blocks any difference from the transcript on a number, negation or hedge: the card must copy the speaker's words.
- **Stale prices scored calls** (FRED stops on 6 Oct): a call now resolves only after its deadline and with a close within 7 days of it, else `pending-data`.
- **Self-certifying fields:** a card could mark its probability "inferred" or itself "translated". Now a card's probability is always "stated" and must appear as a percentage; translation is read from the transcript.
- **Number bypasses:** "USD150", ".5", spoken prefixes ("eighty five" also read as 80), and "1.500" read both ways. Now readings follow the source's language and spoken numbers count only at full value.
- **Names at the start of a claim** ("Citi: …") were unchecked; the month "May" counted as a hedge; a deadline needed no support in the quote; one guest's several cards counted as several views; an episode published after an idea could reach its critic card (now the header's `published` date governs).

## Sources

Theme 1: Maynez et al. 2020 https://arxiv.org/abs/2005.00661 · Kryscinski et al. 2020 https://arxiv.org/abs/1910.12840 · Laban et al. 2022 https://arxiv.org/abs/2111.09525 · Min et al. 2023 https://arxiv.org/abs/2305.14251 · Wang, Cho & Lewis 2020 https://arxiv.org/abs/2004.04228 · Tang et al. 2023 https://arxiv.org/abs/2205.12854 · Tang et al. 2024 (TofuEval) https://arxiv.org/html/2402.13249 · Kim et al. 2024 (FABLES) https://arxiv.org/html/2404.01261 · Liu et al. 2024 https://arxiv.org/abs/2307.03172 · Laban et al. 2024 https://arxiv.org/abs/2407.01370 · Gao et al. 2023 https://arxiv.org/abs/2305.14627 · Tang, Laban & Durrett 2024 https://arxiv.org/abs/2404.10774 · Laban et al. 2023 https://arxiv.org/abs/2305.14540 · Vectara leaderboard https://github.com/vectara/hallucination-leaderboard · Peters & Chin-Yee 2025 https://pmc.ncbi.nlm.nih.gov/articles/PMC12042776/ · Del Rio et al. 2021 https://arxiv.org/abs/2104.11348 · Koenecke et al. 2024 https://arxiv.org/abs/2402.08021

Theme 2: Mukherjee et al. 2022 https://ar5iv.labs.arxiv.org/html/2210.12467 · Islam et al. 2023 https://arxiv.org/abs/2311.11944 · Kim, Muhn & Nikolaev (withdrawn) https://arxiv.org/abs/2306.10224, https://arxiv.org/abs/2407.17866 · Lopez-Lira & Tang 2023 https://arxiv.org/abs/2304.07619 · Glasserman & Lin 2023 https://arxiv.org/abs/2309.17322 · Sarkar & Vafa 2024 https://conference.nber.org/conf_papers/f205530/f205530.pdf · Lopez-Lira, Tang & Zhu 2025 https://arxiv.org/html/2504.14765v2

Theme 3: Tetlock 2007 https://www.columbia.edu/~pt2238/papers/Tetlock_Media_Sentiment_JF.pdf · Engelberg & Parsons 2011 https://conference.nber.org/confer/2009/BEF09/Engelberg_Parsons.pdf · Engelberg, Sasseville & Williams 2012 https://ideas.repec.org/a/inm/ormnsc/v58y2012i2p351-364.html · Chen et al. 2014 https://retirementincomejournal.com/wp-content/uploads/2019/02/SSRN-id1807265.pdf · CXO Guru Grades https://www.cxoadvisory.com/gurus/ · Bailey et al. 2018 https://www.davidhbailey.com/dhbpapers/forecaster-jbcc.pdf · Mitchell & Pearce 2007 https://mgt.ncsu.edu/pdfs/wsjpaper.pdf · Alquist & Kilian 2008 https://crei.cat/wp-content/uploads/2016/09/killian.pdf · Tetlock et al. 2014 https://faculty.wharton.upenn.edu/wp-content/uploads/2015/07/2014---forecasting-tournaments-tools-for-increasing-transparency-and-improving-debate.pdf · AI Impacts GJP https://wiki.aiimpacts.org/featured_articles/evidence_on_good_forecasting_practices_from_the_good_judgment_project

Theme 4–5: Hirshleifer, Lim & Teoh https://mpra.ub.uni-muenchen.de/3110/ · DellaVigna & Pollet https://www.nber.org/papers/w11683 · Roediger & Karpicke 2006 https://psychology.ecu.edu/wp-content/pv-uploads/sites/216/2019/03/Roediger-Karpicke-2006.pdf · Dunlosky et al. 2013 https://www.aft.org/ae/fall2013/dunlosky · Goyal et al. 2022 https://arxiv.org/abs/2209.12356 · Zhang et al. 2024 https://arxiv.org/abs/2301.13848 · Pu et al. 2023 https://arxiv.org/abs/2309.09558

Books and vendors: https://zettelkasten.de/introduction/ · https://fortelabs.com/blog/progressive-summarization-a-practical-technique-for-designing-discoverable-notes/ · https://fs.blog/ten-commandments-for-superforecasters/ · https://knowledge.wharton.upenn.edu/article/michael-mauboussin-on-the-success-equation/ · https://www.oaktreecapital.com/insights/memos · https://www.annieduke.com/books/ · https://www.snipd.com/ · https://podwise.ai/ · https://www.alpha-sense.com/ · https://quartr.com/

Atlas: https://claude.ai/artifact/3DGdbccsP5mrFLt7BzpHcr (sections 3D, 3F, 4.2, 4.5, 4A, 4C, 4G; searched in extracts).
