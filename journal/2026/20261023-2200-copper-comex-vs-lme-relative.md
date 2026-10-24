---
id: 20261023-2200-copper-comex-vs-lme-relative
status: open
book: paper
created_utc: '2026-10-23T22:00:00+00:00'
market: Copper COMEX vs LME
instrument: long COMEX copper Dec26 (HGZ26) / short LME copper Dec26
price_ref: rv:20261023-2200-copper-comex-vs-lme-relative
direction: relative
expression: spread
horizon_days: 91
conviction: 2
prob_win: 0.6
entry_price: 100.0
entry_price_source: null
target: 105.0
invalidation_price: 98.0
invalidation: null
size_planned: 0.5
size_unit: risk units (paper)
source: own
source_ref: null
consensus: null
why_different: null
catalysts: null
state:
  sleep: null
  stress: null
tags: []
events: []
spread:
  id: cu_comex_lme_dec26
  long: COMEX copper Dec26 (HGZ26)
  short: LME copper Dec26 (cash/3-month interpolation)
  quote: 'prices are the spread index: 100 x long leg / short leg in a common unit; premium % = price
    - 100'
  url: https://finance.yahoo.com/quote/HGZ26.CMX
  short_url: https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Cu_cash
reward_risk: 2.5
expected_r: 1.1
sizing:
  units: 1.25
  p: 0.525
  p_source: 50% your probability 0.60 + 50% prior for conviction 2 (calibrates after 20 closed ideas;
    2 so far)
  reward_risk: 2.5
  kelly: 0.335
  raw_units: 1.34
  overlap_corr: 0.38
  overlap_with: 20261020-1900-s-p-500-long
  drawdown_r: -1.43
  stop_sd: 2.23
  notes: []
size_suggested: 1.25
checks_at_entry: []
critic:
  card_utc: '2026-10-23T22:00:00+00:00'
  pack_date: '2026-10-23'
  tier: card-only
  silent: true
  silence_reason: 'conviction 2 at 0.5 units: card only'
  prob_before: 0.6
  prob_after: null
  card:
    entry.price: 100.0
    entry.target: 105.0
    entry.invalidation: 98.0
    entry.horizon_days: 91
    entry.horizon_date: '2027-01-22'
    entry.reward_risk: 2.5
    entry.conviction: 2
    entry.source: own
    prob.before_pct: 60.0
    base.target_first_pct: 21.2
    base.stop_first_pct: 56.5
    base.neither_pct: 22.4
    base.win_pct: 37.0
    base.n_starts: 935
    base.n_independent: 14
    base.since: '2021-12-15'
    base.to: '2026-07-22'
    base.horizon_trading_days: 65
    base.target_pct: 5.0
    base.stop_pct: 2.0
    base.gap_pp: 23.0
    tape.last: 100.0
    tape.last_date: '2026-10-23'
    tape.trend_pct: -3.5
    tape.trend_days: 63
    tape.since_entry_pct: 0.0
    tape.r_now: 0.0
    policy.change_bp: 28.0
    policy.date: '2026-10-22'
  rules:
  - zweig-9
  slots: []
  questions: []
---

## Thesis
US should implement a tariff to keep copper in the US. A negative premium would make copper leave the US, the opposite of the objective of the government's policy.

## What breaks it
In fundamentals, no US tariff on copper imports invalidates the idea.

## Outcome
