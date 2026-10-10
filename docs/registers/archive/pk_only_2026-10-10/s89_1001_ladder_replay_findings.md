# 2026-10-01 SENSEX 0DTE — full-day ladder replay (S89, run 2026-10-05)

**Status: EXPLORATORY, one day, nothing pre-registered.** Descriptive only. Not evidence for a rule. The product is not named here, per the standing rule.

**Artefacts (box):** `scratch/s89_1001/ladder_replay_1001.sql` (sha256 `c7c1d4b764c4e663d88e9d5bf5b8917486b9a74c3a1908c1990b735f7da64600`), `ladder_replay_1001.csv` (76 rows). Run via `bin/roq.sh`, exit 0, nothing committed. Source `option_chain_snapshots`, front expiry 2026-10-01, 76 FULL cycles × 394 rows (no ATM_ONLY rows in window, so that guard was not exercised).

**Question (operator):** if selling calls and following the fall, at what point does the ladder say the selling is slowing, stopping or reversing?

## 1. Cross-engine check vs the target's 11:51 screen (spot 72,393.90)

| | Result |
|---|---|
| Leader strike | MATCH — 72,400 at our 11:45 / 11:50 / 11:55 |
| Top-5 set | MATCH — {72400, 72300, 72500, 72200, 72000}; ranks 2/3 swapped |
| % of leader | 72300, 72200 within 2 pts; 72000 +4 to +12; **72500 +21 to +29** (also +27 at 11:40, spot 72,400.2 — not a timing artefact) |
| Leader net sign | his SHORT at −0.1K (≈0); ours LONG — near-zero, sign not meaningful |
| Non-leader sides | 4/4 match |

His "pressure %" on that screen equals his own Γ-at-strike / Γ-at-leader on all 12 rows (±1, display rounding). So at dte 0 his pressure ranking did **not** invert gamma. Consistent with D-5a (C0 *is* the gamma order); does **not** reopen the decline (guardrail stands). The 72,500 weight gap is unexplained; his per-minute IV re-solve vs vendor Greeks is one candidate, untested.

## 2. The day, phase by phase (OI-change figures in vendor OI units, this day only)

| Phase | Spot | What the ladder showed |
|---|---|---|
| **A 09:15–12:05 range** | 72,240–72,514 | Leader pinned 72,500/72,400; no trend |
| **B 12:05–13:00 fall** | 72,377 → **71,591** | Call writing every cycle (2.4 / 2.8 / 1.9 / 1.3 / 3.8M; **5.2M at 12:50**). Today's flow negative. Leader stepped 72,400 → 72,300 (12:20) → 72,000 SHORT (12:25). HHI fell 0.088 → **0.058** (pin dissolved); runner-up 59% at 12:50 |
| B false stop 12:35–12:40 | +64 pts | Flow turned positive 2 cycles; **put long-unwind 3.7M** (put buyers booking), not put writing. Fall resumed 12:45 |
| **First low 12:50–13:10** | low 71,591 at 13:00, +152 at 13:05 | Today's flow turned **positive at 12:50 and stayed positive all day**. Call short-cover 0.9M (12:50), **1.2M (13:00)**. Put writing **after** the low: 1.7M (13:05), **3.7M (13:10)**. Short γ in 500 pts below spot thinned −662k → −422k |
| **C 13:05–14:05 grind lower** | → **71,302** (lower low) | Call writing resumed every cycle (1.1–2.5M). No put writing at scale. Leader stepped 72,000 → 71,700 (13:25) → 71,500 (13:45). Today's flow stayed positive but decayed 1,268k → 116k |
| **D 14:10–14:35 reversal** | 71,302 → 71,737 | **Call writing 0** at 14:10/14:15. **Call cover + put writing together**: 14:10 (1.1M + 2.4M), 14:15 (1.7M + 4.2M), 14:35 (**5.0M** + 3.4M). Leader jumped 71,500 → 72,000 at 14:35 |
| E 14:40–15:15 pin into close | → 72,010 | Leader 72,000; HHI 0.08 → 0.15+, runner-up 99% → 46% (pin locking). 15:15–15:25 spot frozen at 72,010.1 (auction); 15:30 row is a close artefact |

## 3. What separated stop from reversal on this day

- **Stop (not reversal):** today's flow flips positive and stays (≥3 cycles), plus call short-cover ≥~1M while price is still falling. Fired at 12:50–13:00, at the first low. A lower low followed, and call sellers who held kept gaining slowly.
- **Reversal:** call writing goes to ~0 **and** call short-cover ≥~1M **and** put writing ≥~1.5M **in the same cycle**, for 2+ cycles. Fired only at 14:10/14:15, one cycle after the day's low. Did not fire at 13:00.
- **False floor:** put long-unwind (put buyers booking) ≠ put writing (12:35–12:40).
- **Lagging or weak:** leader steps followed spot rather than leading it; the leader jump up (14:35) was coincident with the reversal, not early. This script's flip was below spot all day (positive only 15:20–15:30) and NULL on 37/76 rows — not useful.
- **Noisy as binary flags:** `ce_short_cover>0` changed 36 times and `pe_short_build>0` 32 times. Only magnitude and persistence separated anything.

## 4. Limits

n = 1 day, one symbol, dte 0. Thresholds (1M / 1.5M) are in this day's vendor OI units and are not portable. Chosen after looking. S88 already found 10-01 indistinguishable from five other expiry days before 12:15. **Before any of this becomes a rule:** pre-register the stop/reversal definitions with scale-free thresholds (e.g. as a share of standing OI) and test across all captured expiry days in the post-parity replay (`claude/parity_dovetail_and_post_parity_plan_S89.md`). Classification feeds D-4 (flow-vs-book in ENH-98 scope).
