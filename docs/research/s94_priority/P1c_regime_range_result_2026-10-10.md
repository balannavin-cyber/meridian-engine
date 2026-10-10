# P1c — γ regime → realised range: RESULT

| Field | Value |
|---|---|
| **Pre-registration** | `P1c_regime_range_prereg_2026-10-10.md`, `git hash-object abde07cae6c671e7a070b79a2987ac88c5c0e963`, commit `ed4979b`. |
| **Scorer** | `p1c/p1c_score.py`, at the parsing fix `4a74885`. The committed scorer (`ed4979b`) raised `ValueError` on row 1 because P1 exports `ats_ist` as time-only. That happened **before any range was computed**. The fix changes parsing only. The §3 rule (predictor t0 = P1's `ats_ist`, to the second) is unchanged, and it held on every session. |
| **Inputs** | Outcome: P1's committed `part2_extract_2026-10-09.json` (md5 `70be3c52…`), `anchor = t0`. Predictors: `p1c/p1c_regime_2026-10-10.csv`, 180 lines, sha256 `f527717ee3fc8213259672ee8e2ea1dffb2a36c5417e8a7f304fe829c2fa163f`, from `p1c_regime_extract.sql` through `bin/roq.sh`. It stays local (`.gitignore *.csv`, TD-S93-NEW-2) and is pinned by the hash. Its sha256 was re-checked before scoring. |
| **Scored** | 2026-10-10 ~09:29 IST (S94), operator-run. Seed 20261010, 10,000 resamples, exit 0. |

**Verdict (§5, NIFTY only): INCONCLUSIVE.** The holdout pinned-positive group has **6** sessions,
below the pre-registered minimum of 8.

## Scorer output, verbatim

```
## NIFTY — PRIMARY

HHI calibration median 0.056188

| half | n pinned-positive | n other | mean range σ (PP) | mean range σ (other) | e = other − PP | 95% CI |
|---|---:|---:|---:|---:|---:|---|
| cal | 14 | 42 | 0.712 | 0.849 | 0.136 | — |
| hold | 6 | 23 | 0.920 | 0.943 | 0.023 | not tested (group < 8) |

Descriptive (all sessions): mean range σ by net γ sign and by DTE bucket
- net γ > 0: n 56, mean 0.899
- net γ ≤ 0: n 29, mean 0.775
- DTE 0: n 19, mean 0.714
- DTE 1: n 17, mean 0.693
- DTE 2–3: n 0, mean nan
- DTE 4+: n 49, mean 0.969

## SENSEX — descriptive

HHI calibration median 0.042120

| half | n pinned-positive | n other | mean range σ (PP) | mean range σ (other) | e = other − PP | 95% CI |
|---|---:|---:|---:|---:|---:|---|
| cal | 18 | 38 | 0.655 | 0.802 | 0.146 | — |
| hold | 9 | 19 | 0.711 | 0.828 | 0.117 | [-0.096, 0.329] |

Descriptive (all sessions): mean range σ by net γ sign and by DTE bucket
- net γ > 0: n 50, mean 0.739
- net γ ≤ 0: n 34, mean 0.808
- DTE 0: n 18, mean 0.660
- DTE 1: n 17, mean 0.843
- DTE 2–3: n 34, mean 0.761
- DTE 4+: n 15, mean 0.821

**Verdict (§5, NIFTY only): INCONCLUSIVE (a holdout group has fewer than 8 sessions)**
```

Group sizes reconcile with P1: NIFTY holdout 6 + 23 = 29, SENSEX 9 + 19 = 28.

## Descriptive observations — post hoc, NOT findings, not claimable

1. **The second limb would fail regardless of n.** The NIFTY holdout e (0.023) is below half the
   calibration e (0.136 / 2 = 0.068). Under §5 a tested NO would follow from that limb alone.
   The verdict is still **INCONCLUSIVE**: the minimum-group gate comes first by pre-registration,
   and it is not reordered after the fact.
2. **Positive in calibration and much smaller in holdout**, on NIFTY. That is the same shape as
   P1's pattern (a): what a calibration-fitted effect looks like when it does not transfer.
   SENSEX kept more of it (0.146 → 0.117), with an interval that includes 0.
3. **Net γ sign alone points opposite ways on the two symbols.** NIFTY positive-γ days had the
   larger mean range in σ (0.899 vs 0.775); SENSEX had the smaller (0.739 vs 0.808). Neither symbol
   shows a plain "positive γ means a calm day" pattern.
4. **Range in σ is lowest near expiry on NIFTY** (DTE 0–1 ≈ 0.70 vs DTE 4+ 0.97). DTE is a reporting
   stratum (P1 §5.1), not a selection. NIFTY has no DTE 2–3 sessions in this sample.

None of these authorises a gate, a sizing input, a display change or a build. A larger-n
re-test would be a **new** pre-registration. The obvious candidate is a forward holdout of sessions
after 2026-10-09, using this pre-registration's definitions unchanged.

## Consequences for the track (nothing applied)

- **P1c → DONE: INCONCLUSIVE** (the item reached a pre-registered end state). Assumption Register,
  dampening row: proposed annotation *"P1c (S94) INCONCLUSIVE at n = 29 holdout. The calibration
  effect did not carry to the NIFTY holdout at the point estimates. The row stays VALIDATED
  indirectly (Exp 17/19, directional), with no range evidence."* It is filed at doc-close.
- **Taken with P1 (levels: NO) and P2 (dealer sign: REGIME-DEPENDENT):** none of the three tests
  of the γ board's reading has produced a pre-registered YES. That is a statement about the
  evidence so far, not a refutation.
