---
description: Ask the fundamentals pillar (agent 12 "Research"). "/ask energy: <question>" goes to one specialist; plain "/ask <question>" is routed by code (orchestrator from S6)
argument-hint: [energy:] <question> [--date YYYY-MM-DD]
---
Use the ask skill (.claude/skills/ask/SKILL.md): route the question with `python -m pmstack route`, build the specialist's input pack, read only the files the route names, write and save a state card (code validates it), answer in at most eight lines with every figure cited from the pack, audit the answer, then log:

$ARGUMENTS
