---
description: Run the own test set (20 tasks, graded by code, k = 3) before an agent, skill or model change, and compare with the baseline
argument-hint: [what changed, e.g. "model claude-x" or "edited skills/morning-note"] | calibrate | noise
---
Use the evals skill (.claude/skills/evals/SKILL.md). Run three fresh answering runs for the configuration, grade them, compare against the last accepted baseline, read every newly failing answer before believing it, then report pass^3 old → new, tasks fixed and tasks broken in three lines and log the comparison:

$ARGUMENTS
