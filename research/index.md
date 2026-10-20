# Research loop — index

Built 2026-10-20 by `python -m pmstack research index`. 18 studies registered, 35 runs and 0 peeks (runs that wrote nothing) in the ledger. Verdicts carry the Benjamini-Hochberg q across every registered flag study (missing or insufficient ones count with p = 1), so a verdict can change as the ledger grows. Gate: config/research.yaml; method: docs/research/research-loop.md.

| study | agent | flag / outcome | episodes | effect | placebo p | BH q | verdict |
|---|---|---|---|---|---|---|---|
| `a7_fading_v1` | 7 | `narrative_stage` signed 20d | 427 | excess -0.20 sd | 0.005 | 0.085 | **in-sample only** |
| `a7_label_crowded_v1` | 7 | `consensus_label` adverse 20d | 352 | lift 0.88 (6.53% vs 7.43%) | 0.751 | 0.850 | **no edge** |
| `a7_label_self_reinforcing_v1` | 7 | `consensus_label` signed 20d | 57 | excess -0.11 sd | 0.698 | 0.850 | **no edge** |
| `a7_label_twilight_v1` | 7 | `consensus_label` adverse 20d | 69 | lift 1.95 (14.49% vs 7.42%) | 0.046 | 0.391 | **no edge** |
| `a7_peaking_v1` | 7 | `narrative_stage` signed 20d | 261 | excess 0.08 sd | 0.372 | 0.702 | **no edge** |
| `a7_spreading_bigmove_v1` | 7 | `narrative_stage` big_move 20d | 326 | lift 1.15 (16.26% vs 14.20%) | 0.191 | 0.541 | **no edge** |
| `a7_spreading_follow_v1` | 7 | `narrative_stage` signed 20d | 326 | excess -0.16 sd | 0.966 | 0.966 | **no edge** |
| `a8_crowded_adverse_v1` | 8 | `cftc_crowded` adverse 20d | 360 | lift 1.00 (7.50% vs 7.49%) | 0.545 | 0.850 | **no edge** |
| `a8_crowded_entry_v1` | 8 | `cftc_crowded_entry` signed 20d | 489 | excess 0.02 sd | 0.680 | 0.850 | **no edge** |
| `a8_crowded_red_v1` | 8 | `crowded_red` adverse 20d | 170 | lift 1.29 (9.41% vs 7.31%) | 0.190 | 0.541 | **no edge** |
| `a8_cta_correction_v1` | 8 | `cta_state` signed 20d | 1206 | excess 0.06 sd | 0.306 | 0.702 | **no edge** |
| `a8_cta_panic_v1` | 8 | `cta_panic` signed 20d | 180 | excess 0.06 sd | 0.771 | 0.850 | **no edge** |
| `a8_cta_panic_v2` | 8 | `cta_panic` signed 20d | 114 | excess 0.09 sd | 0.800 | 0.850 | **no edge** |
| `a8_cta_rebound_v1` | 8 | `cta_state` signed 20d | 909 | excess 0.07 sd | 0.097 | 0.410 | **no edge** |
| `a8_cta_rolloff_v1` | 8 | `cta_rolloff_flip` signed 5d | 8290 | excess 0.01 sd | 0.348 | 0.702 | **no edge** |
| `a8_cta_vol_shrinking_v1` | 8 | `cta_vol_shrinking` signed 20d | 39 | excess 0.04 sd | 0.777 | 0.850 | **no edge** |
| `a8_turbulence_v1` | 8 | `turbulence_persistent` adverse 20d | 57 | lift 1.85 (10.53% vs 5.68%) | 0.084 | 0.410 | **no edge** |
| `p_tsmom_mop2012_v1` | paper | `tsmom` | 477 months | Sharpe 0.63, alpha t 2.21 | - | DSR 0.576 | **no edge** |

## Graveyard

Every study that did not pass, with the rule it failed. Never deleted: each one is a trial that raises the bar for the next.

- `a7_fading_v1` (in-sample only): would be supported on its history, but its definition was written on 2026-10-10 with that history in view; 0 live episodes since (needs 20 with the same sign) [2026-10-19]
- `a7_label_crowded_v1` (no edge): placebo p 0.7511 > 0.05; BH q 0.8501 > 0.1 across the ledger; lift 0.88 short of 1.25; halves disagree [0.817, 0.946]; gone without 2025 (0.795) [2026-10-19]
- `a7_label_self_reinforcing_v1` (no edge): placebo p 0.6982 > 0.05; BH q 0.8501 > 0.1 across the ledger; excess -0.113 sd short of +0.1; halves disagree [-0.287, 0.067]; gone without 2024 (-0.208) [2026-10-19]
- `a7_label_twilight_v1` (no edge): BH q 0.391 > 0.1 across the ledger [2026-10-19]
- `a7_peaking_v1` (no edge): placebo p 0.3718 > 0.05; BH q 0.7023 > 0.1 across the ledger; excess 0.082 sd short of +0.1; halves disagree [-0.1, 0.265] [2026-10-19]
- `a7_spreading_bigmove_v1` (no edge): placebo p 0.1909 > 0.05; BH q 0.5409 > 0.1 across the ledger; lift 1.145 short of 1.25; halves disagree [1.414, 0.871]; gone without 2020 (0.996) [2026-10-19]
- `a7_spreading_follow_v1` (no edge): leans the opposite way (placebo p 0.0345) but fails the gate there: BH q 0.5865 > 0.1 across the ledger [2026-10-19]
- `a8_crowded_adverse_v1` (no edge): placebo p 0.5447 > 0.05; BH q 0.8501 > 0.1 across the ledger; lift 1.001 short of 1.25; halves disagree [0.943, 1.061]; gone without 2025 (0.888) [2026-10-19]
- `a8_crowded_entry_v1` (no edge): placebo p 0.6802 > 0.05; BH q 0.8501 > 0.1 across the ledger; excess 0.022 sd short of +0.1; gone without 2020 (-0.014) [2026-10-19]
- `a8_crowded_red_v1` (no edge): placebo p 0.1904 > 0.05; BH q 0.5409 > 0.1 across the ledger; halves disagree [1.701, 0.839] [2026-10-19]
- `a8_cta_correction_v1` (no edge): placebo p 0.3058 > 0.05; BH q 0.7023 > 0.1 across the ledger; excess 0.058 sd short of +0.1 [2026-10-19]
- `a8_cta_panic_v1` (no edge): placebo p 0.7706 > 0.05; BH q 0.8501 > 0.1 across the ledger; excess 0.062 sd short of -0.1; halves disagree [0.193, -0.069]; gone without 2020 (0.165) [2026-10-19]
- `a8_cta_panic_v2` (no edge): placebo p 0.8001 > 0.05; BH q 0.8501 > 0.1 across the ledger; excess 0.088 sd short of -0.1; halves disagree [0.146, 0.031]; gone without 2020 (0.148) [2026-10-19]
- `a8_cta_rebound_v1` (no edge): placebo p 0.0965 > 0.05; BH q 0.4101 > 0.1 across the ledger; excess 0.07 sd short of +0.1 [2026-10-19]
- `a8_cta_rolloff_v1` (no edge): placebo p 0.3478 > 0.05; BH q 0.7023 > 0.1 across the ledger; excess 0.006 sd short of +0.1; halves disagree [0.018, -0.006] [2026-10-19]
- `a8_cta_vol_shrinking_v1` (no edge): placebo p 0.7771 > 0.05; BH q 0.8501 > 0.1 across the ledger; excess 0.045 sd short of +0.1; halves disagree [0.18, -0.17]; gone without 2008 (-0.048) [2026-10-19]
- `a8_turbulence_v1` (no edge): placebo p 0.084 > 0.05; BH q 0.4101 > 0.1 across the ledger [2026-10-19]
- `p_tsmom_mop2012_v1` (no edge): alpha t 2.21 < 3.0 vs the long-only book; deflated Sharpe 0.5759 < 0.95 (3 trials) [2026-10-19]

_Descriptive research, not signals or trade instructions; decisions stay with the PM._
