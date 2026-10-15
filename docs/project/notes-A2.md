# Session A2 notes — moats, frontier scan, edge frameworks (7–9 Oct 2026)

Bernardo's brief: (1) don't build what will be commoditised within months (as data scraping was by MCPs); check the frontier so we focus on what is still a differentiator in a year. (2) Edge vs the average PM and moats in one year, using the Itaú Asset video. (3) Explore with him Donnelly's "Trade Outside the Box" (edge beyond the four disciplines), the Ohtani mandala chart (goal → 8 pillars → 8 actions each) and Marty Zweig's 17 investing rules. On 9 Oct he asked for the questions as multiple choice, and changed the focus to commodities, US equities and macro (US rates, USD) — not Petrobras, Vale, BRL, IBOV.

Outputs: PM Mandala doc https://claude.ai/code/artifact/84d1ed92-f956-45b5-9c25-224daff4c5f8 ; architecture doc revised (new "Revision, 9 Oct 2026" section); repo live on GitHub; morning-note scheduled task. Status in agents-plan.md.

## 1. Frontier scan: what is commoditised or arriving within ~12 months

| Area | Who ships it (date) | Implication for our build |
|---|---|---|
| Licensed data access via MCP | Bloomberg Enterprise MCP for Data License Plus, 100m+ securities, 50k+ fields, entitlement check on every agent request; real-time and Terminal integration "planned" (29 Sep 2026). FactSet MCP (Dec 2025). LSEG MCP on Claude, Copilot, Gemini, Amazon Quick (2026). S&P Global incl. Energy/Platts MCP; S&P AI-ready commodities data in M365 Copilot. Kpler MCP for cargo/vessel flows via ChatGPT or Claude (Jan 2026). Moody's MCP app. Open-source FRED MCP servers. A-Team: "the MCP layer is commoditised"; the open problem is entitlements and agent identity | Do not invest further in adapters/scrapers. Personal: keep the free adapters as a thin cache. Corporate: use vendor MCPs; Bloomberg via DL+ if licensed |
| Morning briefs, monitoring, thesis health checks | Bloomberg ASKB roadmap (Apr 2026): ASKB Workflows = trigger-based morning briefs, "thesis health checks", pre/post-earnings; PORT and RMS bring firm content into ASKB. AlphaSense SuperAnalyst (3 Jun 2026): always-on monitoring agent with source-linked briefs. Anthropic "Market Researcher" template (5 May 2026) | Generic morning note and generic critic will be commodities. Build only the parts tied to Bernardo's book, rules and history |
| Finance agent templates and office integration | Anthropic (5 May 2026): 10 templates, 17 data partners, Excel/PowerPoint/Word add-ins, Claude Managed Agents. OpenAI ChatGPT for Financial Services (10 Sep 2026), aimed at bankers and equity research | Runtime, scheduling, audit logs, Excel work: buy. Templates are equity/banking-first; commodity macro still underserved (Atlas pattern 12) |
| Behaviour analytics | Essentia Analytics: 50+ analyses, ex-ante nudges (claims +160 bp/yr for engaged managers); Baillie Gifford feeds Essentia decision data into its AI stack (21 Sep 2026). Built on equity manager data | Poor fit for a futures/commodity book. The scarce input is the PM's own decision data |
| Natural-language backtesting | QuantConnect, HeyTraders, Backtrex etc.; BacktestBench (2026) | Idea→code is commodity; the evaluator and the record of killed ideas are not |
| Agent capability trend | METR: autonomous task length doubling every ~4–7 months (estimates vary) | Design to swap models; keep own evals |
| Retail agents | Robinhood rolled out OpenAI/Anthropic trading agents to ~29m customers; ~30m agent transactions a day (29 Sep 2026, Fortune) | Faster consensus and herding; crowding and narrative contagion become measurable |

**Durable in a year (moats):** (1) own decision data (journal with conviction, expected payoff, invalidation, rejected ideas, outcomes; call notes; alert feedback); (2) codified personal rules and sizing calibration; (3) critic built on own history; (4) own model test set; (5) commodity specialism with US macro as context — underserved by equity-first vendors; (6) consensus measurement for second-order views; (7) human edges AI amplifies: sizing/ergodicity, psychology, network, learning speed.

## 2. Video — Mind Asset (Itaú Asset), "Fundos multimercado: IA, alternativos e o futuro da gestão", 1 Oct 2026, 24:45
Guest: Arlindo Penteado (head of Multimesas and the Global Dinâmico family). Transcript read 9 Oct from the player's auto-captions (video muted and paused throughout).
- Industry splits into specialist pods vs platforms; multi-strats outgrow single managers. Itaú = platform (infrastructure, data, market access, risk, compliance, capital for specialists).
- Alpha/beta separation for 15+ years → specialisation. Focus now on "single pods" (one geography or asset class) plugged into their AI infrastructure.
- AI: structured project started ~a year ago — real-time data, news, research → economist agent builds a country macro view (started with Canada) → portfolio agents trade under a set philosophy, human-supervised. Now 200+ agents in the cloud; Australia and Canada live, US and Brazil in testing. "Gestão ciborgue": 3 desks on the platform; the human governs the machine (also a regulatory requirement).
- Key gain: measurability — hit rate at each link (inflation agent → chief-economist agent → portfolio agents → trades over a set horizon).
- Standardisable into agents: portfolio construction, regime analysis, asset pricing, econometrics, curve analysis, risk ("Excel replacing the HP-12C"). Stays human: deep knowledge of the underlying asset, experience, time, dedication. Specialisation replaces the generalist "visionary" macro view. Competition for alpha global and "brutal". He adds "posso estar errado".
- Numbers (firm-reported): Multimesas 7 years; private markets from ~R$3bn credit desk to R$45bn (real estate, specials, agro, listed, infra); 122 managers; NY and Miami teams; partnerships with KKR (private markets) and an international hedge fund (name unclear in captions) that allocates to them as LatAm/EM alpha source; offshore fund launching by year-end. Alternatives grow ~10%/yr real; ~20% of global AuM, >50% of revenue (stated, unsourced). AI results "very good" (unquantified).

## 3. Frameworks and Bernardo's answers (9 Oct, multiple choice)
- Goal (centre square): top-decile risk-adjusted → **Sharpe 1.5+ over 3 years** (current 0.9 since Mar 2021).
- Edge today: all four Donnelly boxes (fundamentals, technicals, behavioral, quant/derivatives).
- Main leak: **under-sizing best ideas**. Sizing today: discretionary by conviction.
- Specialisation: P&L best in commodities, good in US equities and macro; future focus should be where the human edge lasts longest → recommendation in the Mandala: commodities as specialism, US equities/rates/USD as context; confirm with P&L by asset class.
- Zweig: mixed — hard checks #2, #3, #11, #14 + added "size your best ideas"; monthly review #7, #8, #10; prompts for the rest.
- Donnelly themes to add: psychology; poker and bet sizing; second-order thinking and narrative.
- Intangibles: strength = health, energy, focus; to improve = network, information flow, reputation.
- Pillars kept: Fundamentals, Price action, Positioning & narrative, Derivatives & quant, Sizing & risk, Psychology, Network & reputation, Learning & AI stack. 64 actions: 42 AI assists, 16 human, 6 vendor.
- Time for building: 5–10 hours a week.
- Sources for Donnelly's book: Google Books description (published 2 Apr 2026); themes from his announcement post (search snippet). Chapter content not read.

## 4. Build and ops (9 Oct)
- Repo https://github.com/bdgsaraiva/pm-agent-stack pushed; Claude GitHub App installed.
- First live Actions run: FRED, Yahoo prices, central-bank RSS OK; CFTC HTTP 400 (column `prod_merc_positions_long_all` doesn't exist) → adapter now picks the column spelling that exists; EIA needs `EIA_API_KEY` secret.
- Fixes from reading the live fact pack: "live" bar only if fetched before the session close (17:00 BRT cash, 18:00 BRT futures/FX); fetch times printed in UTC (were BRT labelled UTC); Yahoo's daily series can lag the session → append regularMarketPrice; Yahoo has no history for CNH=X and 000300.SS → USD/CNY and Shanghai Composite; data health lists series with <20 points; broad USD is weekly; dropped IMF iron ore (≈3-month lag).
- Focus switch: FRED adds 2y, 30y, 2s10s, 10y real, SOFR, HY OAS; prices add S&P/Nasdaq/Russell/VIX, XLE/XLB, ES/NQ, ZN/ZT, EUR/JPY/CNY/AUD, silver, wheat; Brazil tickers and BCB block removed (adapter kept).
- Scheduled task "Morning note" (weekdays 06:18 BRT, push, auto-approve) test-fired: note quality good — every figure linked, inference labelled, correct Columbus Day note; flagged FRED Brent spot (125.44 on 6 Oct) far above the front-month future (worth a look: dated vs futures).
- Cowork chat with CV/headhunter material is not visible from Claude Code sessions; needs uploading as Project files.
