---
title: Network and reputation — literature review
agent: 11 (network and reputation)
date: 2026-10-15
status: reviewed before build; code in pmstack/network.py, parameters in config/network.yaml, skill in .claude/skills/network/
docs: https://claude.ai/code/artifact/4e2f97b5-206a-451d-8e39-69854e5d30a9
---

# Network and reputation — literature review

**Answer.** Run the network as a small, deliberate portfolio, not a contact count. Keep a few high-bandwidth anchors per core market, rotate moderately weak bridging ties, and reconnect dormant ones on purpose. Close every promise as a dated, named task. Build reputation through a scheduled, numbered public note with a scored record of past calls. The evidence says the network pays mainly in better questions, sanity checks across clusters and career optionality, not alpha: the legal centrality premium is 20–30 bp a year, and the big "network wins" in enforcement records are insider cases. So every call note carries an MNPI attestation, contacts carry a role-based risk flag, and nothing public attributes a view to a named person.

Method: three research passes on 15 Oct 2026 (network structure, investing networks and MNPI, reputation, follow-up and decay, privacy law; Atlas cards; books and vendors), ~38 sources and ~55 pages opened. Read status per row: full, abstract, or secondary.

## 1. Papers: network structure

| Finding | What it changes | Source |
|---|---|---|
| LinkedIn randomised test (~20M users, ~600k job moves): inverted U — moderately weak ties (~10 mutual connections) moved jobs most; strong ties mattered more in less digital industries. | Score tie strength and aim at the middle band; physical commodity contacts (less digital) lean on strong ties, US rates/USD on weak ones. | Rajkumar et al. 2022, *Science* (abstract + MIT News) |
| Weak ties are local bridges into other clusters and carry non-redundant information. | A `cluster` tag per contact so bridging and bonding ties can be counted. | Granovetter 1973 (original scan unreadable; Easley & Kleinberg ch. 3) |
| 673 Raytheon managers: those spanning structural holes earned more, were promoted more and had better-rated ideas; most value lost with the first redundant contacts. | Monthly bridging share; before a public note, run the thesis past someone from another cluster. | Burt 2004, *AJS* (full) |
| Dormant ties (3+ years) reconnected gave knowledge as useful as current ties, with more novelty and kept trust; value did not fall down the top-10 list (r = −0.074). | Weekly reconnect suggestion with one random pick from the shortlist. | Levin, Walter & Murnighan 2011 (full) |
| Reconnecting: 94% got valuable advice; most value from higher-status, briefly known contacts; people choose by comfort; 90% enjoyed it; face-to-face 5.63/7 vs phone 5.29. | Rank candidates by novelty × engagement, not comfort; suggest in-person when possible. | Walter, Levin & Murnighan 2016, *MIT SMR* (full) |
| Strong ties give more useful knowledge through trust; with trust controlled, weak ties win on novelty. | A 1–5 competence-trust field; weak-tie input weighted by it. | Levin & Cross 2004 (abstract) |
| Embedded ties help up to a threshold, then isolate. | Monitor the share of conversations going to the top 15. | Uzzi 1997 (abstract) |
| Diversity costs bandwidth; with fast-refreshing information, +1 sd bandwidth → +0.35 sd novel information vs +0.07 for diversity. | 2–3 high-bandwidth anchors per core market (oil, ags, UST, USD). | Aral & Van Alstyne 2011 (full) |
| Facebook networks ~155–183; inner layers 4.1 and 13.6 (Dunbar's ~5 and ~15); online doesn't extend capacity. | Layers 5/15/50/150 set cadence; never use contact count as a KPI. | Dunbar 2016 (full) |

## 2. Papers: networks in investing, and MNPI

| Finding | What it changes | Source |
|---|---|---|
| Fund managers earn up to 8.4% a year more on firms with school-tied boards. | `how_met` stored, but issuer insiders are the MNPI frontier: flag them. | Cohen, Frazzini & Malloy 2008 (abstract + HBS) |
| Analysts' school-tie edge 9.36%/yr before Reg FD, ~0 after. | Much "network alpha" was selective disclosure. Aim the network at interpretation and cross-market bridges. | Cohen, Frazzini & Malloy 2010 (abstract + HBS) |
| Word of mouth: +0.13 pp holdings per 1 pp same-city peer change. | Log "idea heard from" (privately) so the journal can test network-sourced ideas; herding check in call notes. | Hong, Kubik & Stein 2005 (full) |
| Neighbours hold more similar stocks. | "My view vs the room's view" field. | Pool, Stoffman & Yonker 2015 (abstract) |
| VC centrality: +1 sd → +3.2–6.5 pp exit rates. | Being the person others bring commodity questions to is the goal the public note serves. | Hochberg, Ljungqvist & Lu 2007 (full) |
| UK pension managers: +1 sd centrality → +0.20–0.31%/yr risk-adjusted. | The legal premium is modest; the network is for reputation and options. | Rossi et al. 2018 (full) |
| Interpersonal talk drew institutional attention to boom stocks (~75% vs 53%, from a partly legible scan). | "What drew my attention" field. | Shiller & Pound 1989 (full scan) |
| Expert-network calls on private firms: ~60% higher odds of a capital raise. | Calls carry information, which is why they are also the MNPI vector. | Liu, Merkley, Pacelli & Volant 2025 (full) |
| Martoma: $276M from a trial-committee doctor reached via an expert network; PGR: >$30M via moonlighting employees. | Role at firm decides MNPI risk: flag issuer insiders, government data staff, regulators, OPEC delegates. | SEC 2012-237, 2011-40 (full) |
| SEC exam alert 2022: advisers failed to log expert calls, review notes and monitor related trading. | The call log is built so a compliance reviewer could read it: date, role/firm, topics, attestation. | K&L Gates summary (secondary) |
| CVM Res. 44/2021 art. 13: bars **anyone** with access to undisclosed material information from using it; professional relationships trigger a presumption of knowledge. | Mandatory attestation; if MNPI was received the note is not stored and the agent says: stop, don't trade, tell compliance. | CVM 44 consolidated text (full) |

## 3. Papers: reputation and public writing

| Finding | What it changes | Source |
|---|---|---|
| All-American analysts' forecasts get *better* under conflicts; bank reputation alone doesn't discipline. | The note runs under his own name with a public record. | Fang & Yasuda 2009 (abstract) |
| Analyst pay follows All-Star status and visibility, not forecast accuracy. | Track both currencies: reach (sends, replies) and a scored hit rate. | Groysberg, Healy & Maber 2011 (abstract) |
| WSJ "Category Kings": ~31% higher quarterly flows than near-misses, ~7× performance-chasing. | Fixed date, numbered issues, consistent format. | Kaniel & Parham 2017 (secondary) |
| Shareholder letters: tone inconsistent with performance reduces flows. | Mandatory "what I got wrong" section. | Hillert, Niessen-Ruenzi & Ruenzi 2023 (abstract) |
| Seeking Alpha opinions predict returns. | Public long-form views are read and can carry information. | Chen et al. 2014 (abstract) |
| Escalation: responsible subjects reinvested $13.07M of $20M; replications mixed. | Every public call has an invalidation trigger and review date; fear of error must not stop publication. | Staw 1976 (full); FORRT replication atlas |
| Generosity → status; frequent favour exchange strengthens both status and productivity. | Give log vs ask log; aim for frequent small gives. | Flynn 2003 (abstract) |

## 4. Papers: follow-up and decay

| Finding | What it changes | Source |
|---|---|---|
| If-then plans: d = 0.65 over 94 tests. | Every "I'll send / intro / talk in X" becomes a dated if-then task (default 24h for recap and promised item). | Gollwitzer & Sheeran 2006 (abstract) |
| Reminders work when they name the specific goal. | Reminders name the item and the person. | Karlan et al. 2016 (abstract) |
| Stable "social signature" despite 41% churn of the top 20 in six months. | Monitor concentration (top 5/15 share), not individual ties. | Saramäki et al. 2014 (full) |
| ~43% of active phone ties gone four weeks later; each extra call +3.8% persistence odds; reciprocity predicts survival; new ties decay fastest. | Second touch 2–4 weeks after a first call; log who initiated. | Raeder et al. 2011 (full); Burt 2000 via secondary |
| Physician ties: ~40% dissolved within a year. | Cadence by layer (5: 2 weeks; 15: monthly; 50: quarterly; 150: twice a year). | Zhang & King 2021 (full) |

## 5. Privacy and law (not legal advice)

- **LGPD art. 4 I** exempts only "exclusively private and non-economic" processing; a professional contact list is neither, so assume LGPD applies. Legal basis: **legitimate interest** (art. 7 IX), with minimisation, security and deletion on request. **Sensitive categories** (art. 5 II: health, politics, religion, etc.) are never stored.
- **GDPR** household exemption excludes professional activity (art. 2(2)(c), recital 18; *Ryneš*: narrowly construed) — EU-resident contacts are in scope.
- **GitHub private repos** are readable by the owner and invitees (and org owners for org repos): never an employer-owned org.
- **The fund's code of ethics** usually covers a PM's industry contacts and public writing: Bernardo checks it before the first public note.

## 6. Counterpoints

- Instrumental networking feels "dirty" and lowers networking frequency (Casciaro, Gino & Kouchaki 2014, secondary) → frame prompts around giving and learning; track give:ask; no pressure KPIs.
- Network "alpha" mostly vanished with fair-disclosure rules (CFM 2010) and the legal premium is small (Rossi et al.) → don't sell the pillar to yourself as an alpha engine.
- Bigger isn't better: diversity costs bandwidth, the weakest ties help least, capacity caps near 150 → quality per layer.

## 7. Atlas investors and institutions

- **Morgan Stanley Debrief** (4A): notes, drafted follow-up email, CRM update; adoption came from removing a chore → the agent's core is the **post-call debrief**.
- **XP's adviser CRM** (4E): the conversation log, not the model, is the asset → capture every call as structured data from day one.
- **EQT Motherbrain** (4B): people and the links between them → contacts as a small graph (introduced-by, alumni).
- **Andurand, Doug King** (3F): deep physical-market networks → tag contacts by place in the value chain (producer, trader, shipper, analyst, policy).
- **Druckenmiller** (4F): the best AI calls came from people → "who told me what, when, and were they right": agent 10's speaker records cover named public guests; private contacts are scored only privately.
- **Millennium digital twins** (4C): prepare and draft, never decide or send → the agent drafts; Bernardo sends.
- **Marks, Ackman, Burry** (3D): dated, candid, archived public writing builds a franchise → memo format with a scored archive.
- **Atlas 5.8** (careers): track records travel; options are platform pods, SMAs with Gulf allocators, AI sleeves → an `allocator` cluster with a slow keep-warm cadence; the monthly page doubles as process evidence.

## 8. Books (not page-checked unless marked)

- **Grant, *Give and Take*** (sive.rs notes, page-checked): five-minute favours; dormant ties; "otherish" giving with a time cap.
- **Ferrazzi, *Never Eat Alone*** (reader notes): follow up within a day; ping with useful content; prep before meetings.
- **Burt, *Brokerage and Closure*** (Wikipedia): brokerage for ideas, closure for trust → bridging share plus an inner circle.
- **Hoffman & Casnocha, *The Start-up of You*** (Entrepreneur, page-checked): ABZ planning → contacts tagged by the plan they serve.
- **Cialdini, *Influence*** (influenceatwork.com, page-checked): reciprocity (give first, personalised), commitment (public dated calls), authority via warm intros.
- **Dorie Clark, *Stand Out*** (dorieclark.com): a distinctive point of view; network → audience → community.

## 9. Vendors

Affinity and DealCloud (enterprise relationship intelligence), Mesh (ex-Clay), Dex and folk (personal CRMs with reminders and job-change alerts), Monica (open-source, self-hostable), Granola (meeting notes with action items). **None** ties call notes to a decision journal, carries an MNPI attestation, or scores public calls. Build the thin layer (schema, follow-ups, metrics, note scorecard); a personal CRM can be a capture source later.

## 10. Where sources disagree

1. Weak vs strong ties → a bimodal portfolio: anchors per market + rotating moderately weak bridges (Rajkumar reconciles Granovetter, Aral & Van Alstyne, Levin & Cross).
2. Maintain every tie? → cadence for inner layers, deliberate reactivation for dormant ones (decay studies vs Levin et al.).
3. Embeddedness → watch concentration and bridging together (Uzzi vs Burt).
4. Investment value of networks → real but small and partly illegal; aim at interpretation (CFM 2010, Rossi, SEC cases).
5. Public writing → visibility pays, inconsistency is punished → schedule + scorecard + "what I got wrong".
6. Motivation → frame as giving (Flynn, Walter) to counter the "dirty" effect (Casciaro).

## 11. Design changes vs the plan

| Item | Plan (PM Agent Plan row 11) | Now |
|---|---|---|
| Core | Call notes, contact map, follow-ups | Post-call debrief: structured note, dated follow-ups parsed from promises, contact update, drafted recap (never sent) |
| Contact fields | Name, role, firm | + cluster, value-chain role, layer, tie strength, competence trust, how met / introduced by, first/last contact, last initiator, next touch, give/ask log, `mnpi_risk` by role, plan (A/B/Z); no sensitive categories, no personal life |
| Call note | Template | + topics, public sources mentioned, what drew attention, my view vs the room's, questions carried from agent 10, **MNPI attestation** (no attestation → not saved) |
| Follow-ups | Reminders | If-then tasks with dates and named items; overdue list; second touch 2–4 weeks after a first call |
| Reconnect | — | Weekly 1–2 dormant candidates (no contact ≥ 12 months), novelty × engagement, one random pick |
| Metrics | Calls a week; follow-ups closed | + follow-ups closed on time, bridging share, top-5/15 concentration, reciprocity, give:ask, new vs decayed ties, layer cadence met; never contact count |
| Monthly page | Monthly CIO page (corporate) | Personal monthly network page (metrics, overdue, reconnects, cadence gaps); CIO page stays corporate |
| Public note | Monthly commodity note | Numbered memo on a fixed date: one theme, public data only, figures audited, calls with probability, invalidation and review date, last month's scorecard and "what I got wrong"; no named sources; disclaimer; bridge test before publishing; Bernardo publishes |
| Track record | — | `network/public_calls` scored by code from stored prices |
| Privacy | — | Private, personal-account storage; minimal fields; `forget` command; yearly purge of 5-year-idle contacts with no reconnect value |

## 12. How it works (worked example: live run, 15–16 Oct 2026)

Contacts ran on a demo repo with fictional people (`.projtmp/`, never committed); the public pack ran on real public data.
1. `network init` created `contacts.yaml`, `calls/`, `monthly/` and a README with these privacy rules.
2. A contact with a `phone` field was refused ("fields never stored").
3. A debrief saved as call `2026-10-13-01` with two follow-ups: "send the CFTC managed-money table" (owner me, due next day) and "intro to a tanker broker" (owner them, due 20 Oct).
4. A call marked "MNPI received" was refused and nothing was written.
5. `network due` (16 Oct) showed the table 2 days overdue; `network reconnect` surfaced a dormant allocator contact (898 days).
6. `network public pack --market BZ=F` as of 15 Oct used Brent spot from EIA via FRED (DCOILBRENTEU), not the personal-use Yahoo futures: last 125.44 on 6 Oct; 12-month range 59.93–138.21. A Yahoo-only market is refused. Spot carries the 2026 physical premium, so a post must say "dated Brent".
7. Found by the live run and fixed: the first pack used the Yahoo futures series, which the licence rule bars from public posts; the CFTC report was counted from its Tuesday date instead of the Friday release.

## 13. Independent review (16 Oct 2026): findings fixed

Of the reviewer's 24 defects (full list: `docs/project/notes-A11.md`), these were in agent 11, all fixed with regression tests:
- **Licence:** the public scorecard could fall back to Yahoo for a call without a recorded series; it now re-resolves the public series and refuses a mismatch.
- **Look-ahead:** follow-ups closed later counted as closed on earlier dates; backdated packs dropped CFTC instead of using the report public then.
- **Metrics:** a first call with an old contact counted as a new tie (so reconnects always read 0) and asked for a second touch.
- **Privacy:** ids were reused after `forget` (now never); shared calls kept text about a forgotten person (now listed for redaction); nested or camelCase sensitive keys passed; a network home inside this repo was allowed (now refused); the post check skipped names silently without the repo and missed surnames; contact names elsewhere in a journal entry are now flagged.
- **Robustness:** "None received." read as "received"; future months crashed; bad CLI input crashed; the issue number came from any "#N".

## Sources

Theme 1: Rajkumar et al. 2022 https://news.mit.edu/2022/weak-ties-linkedin-employment-0915 · Granovetter 1973 https://snap.stanford.edu/class/cs224w-readings/granovetter73weakties.pdf; Easley & Kleinberg ch. 3 https://www.cs.cornell.edu/home/kleinber/networks-book/networks-book-ch03.pdf · Burt 2004 https://snap.stanford.edu/class/cs224w-readings/Burt04StructureHole.pdf · Levin, Walter & Murnighan 2011 https://business.gwu.edu/sites/g/files/zaxdzs5326/files/15_FP.SP_Walter.J_15levin_2011a.pdf · Walter, Levin & Murnighan 2016 https://business.gwu.edu/sites/g/files/zaxdzs5326/files/11_FP.SP_Walter.J_11walter_2016a.pdf · Levin & Cross 2004 https://levin.rutgers.edu/?p=466 · Uzzi 1997 https://www.kellogg.northwestern.edu/faculty/research/detail/1997/social-structure-and-competition-in-interfirm-networks-the-paradox · Aral & Van Alstyne 2011 https://iacmr.org/wp-content/uploads/sites/26/2024/05/1.Aral-and-Van-Alstyne-2011-The-Diversity-Bandwidth-Trade-off.pdf · Dunbar 2016 https://pmc.ncbi.nlm.nih.gov/articles/PMC4736918/

Theme 2: Cohen, Frazzini & Malloy 2008 https://www.nber.org/papers/w13121 · 2010 https://ideas.repec.org/a/bla/jfinan/v65y2010i4p1409-1437.html · Hong, Kubik & Stein 2005 https://www.columbia.edu/~hh2679/ThyNeighborJF.pdf · Pool, Stoffman & Yonker 2015 https://ideas.repec.org/a/bla/jfinan/v70y2015i6p2679-2732.html · Hochberg, Ljungqvist & Lu 2007 https://www.stat.berkeley.edu/~aldous/Networks/hochberg.pdf · Rossi et al. 2018 https://openaccess.city.ac.uk/id/eprint/17528/1/wp1609.pdf · Shiller & Pound 1989 https://nber.org/system/files/working_papers/w1851/w1851.pdf · Liu et al. 2025 https://faculty.marshall.usc.edu/Gerard-Hoberg/CETAFE/papers/paper8.pdf · SEC 2012-237 https://www.sec.gov/news/press/2012/2012-237.htm · SEC 2011-40 https://www.sec.gov/news/press/2011/2011-40.htm · SEC 2022 alert (K&L Gates) https://www.klgates.com/SECs-Division-of-Examinations-Issues-Risk-Alert-on-Investment-Adviser-MNPI-Compliance-Issues-5-4-2022 · CVM 44/2021 https://conteudo.cvm.gov.br/export/sites/cvm/legislacao/resolucoes/anexos/001/resol044consolid.pdf

Theme 3: Fang & Yasuda 2009 https://ideas.repec.org/a/oup/rfinst/v22y2009i9p3735-3777.html · Groysberg, Healy & Maber 2011 https://ideas.repec.org/a/bla/joares/v49y2011i4p969-1000.html · Kaniel & Parham 2017 (secondary) https://mas360.moneylife.in/article/does-media-attention-influence-investment-decisions/1879.html · Hillert et al. https://safe-frankfurt.de/publications/working-papers/details/publicationname/mutual-fund-shareholder-letters-flows-performance-and-managerial-behavior.html · Chen et al. 2014 https://ideas.repec.org/a/oup/rfinst/v27y2014i5p1367-1403..html · Staw 1976 https://www.gwern.net/doc/psychology/cognitive-bias/sunk-cost/1976-staw.pdf · FORRT https://forrt.org/flora-replication-atlas/doi/10.1016/0030-5073(76)90005-2/ · Flynn 2003 https://www.gsb.stanford.edu/faculty-research/publications/how-much-should-i-help-how-often-effects-generosity-frequency-favor

Theme 4: Gollwitzer & Sheeran 2006 https://kops.uni-konstanz.de/entities/publication/2e749bfb-8533-437c-8203-7e788c910c5f · Karlan et al. https://www.nber.org/papers/w16205 · Saramäki et al. 2014 https://pmc.ncbi.nlm.nih.gov/articles/PMC3903242/ · Raeder et al. 2011 https://ar5iv.labs.arxiv.org/html/1102.1753 · Zhang & King 2021 https://pmc.ncbi.nlm.nih.gov/articles/PMC9048141/

Privacy: LGPD art. 4 https://lgpd-brazil.info/chapter_01/article_04 · art. 5 https://lgpd-brazil.info/chapter_01/article_05 · art. 7 https://lgpd-brazil.info/chapter_02/article_07 · GDPR art. 2 https://gdpr-info.eu/art-2-gdpr/ · recital 18 https://gdpr-info.eu/recitals/no-18/ · Ryneš (FRA) https://fra.europa.eu/en/node/17583 · GitHub https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories

Counterpoint: Casciaro, Gino & Kouchaki 2014 https://insight.kellogg.northwestern.edu/article/networking-is-a-dirty-business

Books and vendors: https://sive.rs/book/GiveAndTake · https://mickmel.substack.com/p/notes-from-never-eat-alone-by-keith · https://en.wikipedia.org/wiki/Ronald_Stuart_Burt · https://www.entrepreneur.com/article/223099 · https://www.influenceatwork.com/7-principles-of-persuasion/ · https://dorieclark.com/books/ · https://www.affinity.co/ · https://www.intapp.com/dealcloud/ · https://me.sh/ · https://getdex.com/ · https://www.folk.app/ · https://www.monicahq.com/ · https://www.granola.ai/

Atlas: https://claude.ai/artifact/3DGdbccsP5mrFLt7BzpHcr (sections 3D, 3F, 4A, 4B, 4C, 4E, 4F, 5.8; searched in extracts).
