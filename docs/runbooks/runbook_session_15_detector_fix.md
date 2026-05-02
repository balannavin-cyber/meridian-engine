# RUNBOOK: Session 15 BEAR_FVG Detector Fix (one-shot, completed)

> **Status:** COMPLETED 2026-05-02 (Session 15). This runbook is preserved as audit trail of how a 13-month silent production defect was diagnosed and shipped end-to-end. **Not intended for re-execution** — the underlying bug is fixed and the patches are in production. If you find yourself re-running this, something has gone wrong (likely a reverted commit) and Step 0 below tells you what to check first.

---

| Field | Value |
|---|---|
| **Operation** | Diagnose and fix BEAR_FVG missing across the ICT zone detector and signal pipeline. Result: `hist_pattern_signals.BEAR_FVG` count 0 → 795 over 13 months. |
| **Frequency** | One-shot. Done 2026-05-02. Re-execute only on confirmed regression. |
| **Environment** | Local Windows primary (`C:\GammaEnginePython`). AWS not touched in this fix. |
| **Prerequisites** | (1) Patched scripts in place (renamed canonical names; originals at `_PRE_S15.py`). (2) Supabase service-role credentials in `.env`. (3) Read access to `hist_spot_bars_5m`, `hist_ict_htf_zones`, `hist_pattern_signals`. (4) Write access to `hist_ict_htf_zones`, `ict_htf_zones`, `hist_pattern_signals`. |
| **Expected duration** | Diagnosis + fix as ran in Session 15: ~3 hours of operator time (multi-stage audit + code review + dry-run + backfill + verification). Backfill itself: ~5 minutes for historical, ~1 minute for live, ~2 minutes for signal rebuild. |
| **Who can do this** | Navin or any operator with write access to the production tables AND the patch context from Session 15. Do NOT execute steps 4-6 (the writes) without first running Step 0 to confirm regression. |
| **Last verified** | 2026-05-02 (Session 15 — full execution + end-to-end verification: BEAR_FVG signals 0 → 795). |

---

## When to use this runbook

**Primary use: audit trail.** This runbook documents the fix that closed TD-048 (BEAR_FVG missing across detector pipeline). Read it to understand:

- What the bug was (3 missing detector branches across 2 zone-builder scripts)
- How it was diagnosed (5-step audit, six-bug code review)
- What was fixed and what was deliberately left alone (S1.a + S1.b shipped; S2.a/S2.b/S3.a/S3.b filed as TD-049/050/051/052 for later)
- How verification confirmed end-to-end correctness (canonical 3-bar shape scan → backfill counts → signal rebuild → re-audit)

**Secondary use: regression recovery.** If a future session discovers that BEAR_FVG signals have dropped to 0 (or significantly diverged from the BULL_FVG count), the regression-recovery sequence is at the bottom of this runbook (Failure modes section). Don't re-run the original full sequence blindly.

**Tertiary use: similar bug pattern.** If a future audit finds a different "<X> missing across detector" defect (e.g. SWEEP_REVERSAL never written, or a specific timeframe never produces a specific zone type), this runbook's diagnosis structure is the template:

1. Five-step audit (`diagnostic_<X>_audit.py` modeled on `diagnostic_bear_fvg_audit.py`)
2. Code review of the writer script with bug ranking (S1 fixed inline, S2/S3 filed as separate TDs)
3. Patched-copy approach (`_PATCHED.py` files, dry-run, real run, post-verify rename)
4. End-to-end re-audit with the original diagnostic

---

## Steps

> **Note:** Steps 1-3 are diagnostic and were completed Session 15. Step 4-6 are the actual writes that shipped the fix. Do NOT re-execute Steps 4-6 without first running Step 0 (regression check).

### Step 0 — Regression check (run first, before anything else)

Confirm whether the fix has regressed. The diagnostic from Session 15 is preserved as `diagnostic_bear_fvg_audit.py`.

```powershell
cd C:\GammaEnginePython
python diagnostic_bear_fvg_audit.py
```

What to expect (post-fix state, baseline 2026-05-02):
- **Step 1 distinct pattern_type values**: 5 types including `BEAR_FVG` with non-zero count (was 795 at baseline; should be similar or higher as time progresses)
- **Step 5 canonical scan**: ~1,000-1,200 BEAR_FVG 3-bar shapes in `hist_spot_bars_5m` over 60d (regime-dependent; symmetric within ~10% of BULL_FVG)
- **Last section "Bear-flavoured types in table"**: `{'BEAR_FVG': N, 'BEAR_OB': M}` where N is non-zero

**If Step 1 returns 0 BEAR_FVG with non-zero canonical shapes (Step 5)**: regression confirmed. Investigate which layer regressed before re-executing the original fix:

```powershell
# Check zone table (one layer up from signals)
python diagnostic_hist_ict_htf_zones_distribution.py
```

If `hist_ict_htf_zones.BEAR_FVG` is 0: regression is in the zone builders. Check if the live `build_ict_htf_zones.py` and `build_ict_htf_zones_historical.py` files match `_PRE_S15.py` (someone reverted the patches):

```powershell
fc.exe build_ict_htf_zones.py build_ict_htf_zones_PRE_S15.py
fc.exe build_ict_htf_zones_historical.py build_ict_htf_zones_historical_PRE_S15.py
```

If the patched files match the PRE_S15 files = revert happened. Roll forward by re-renaming. **Do NOT proceed with full Steps 4-6 unless this check is passed.**

If `hist_ict_htf_zones.BEAR_FVG` is non-zero but `hist_pattern_signals.BEAR_FVG` is 0: regression is in the signal builder or its scheduled run. The signal builder is direction-symmetric and innocent — check the schedule, then re-run Step 6 only.

### Step 1 — Five-step BEAR_FVG audit (diagnostic, completed Session 15)

```powershell
python diagnostic_bear_fvg_audit.py
```

What it does (preserves the Session 15 diagnostic structure):
- **S1**: Distinct `pattern_type` values + counts in `hist_pattern_signals`. Reveals BEAR_FVG count = 0 if buggy.
- **S2**: Full schema dump + direction-column distribution per pattern_type.
- **S3**: Sibling table check for any "pattern" / "signal" / "fvg"-named tables that might contain BEAR_FVG.
- **S4**: Bear-day count last 30d (sanity check for "is the market actually one-sided?").
- **S5**: **Manual canonical 3-bar BEAR_FVG shape scan in `hist_spot_bars_5m` over 60d.** This is the load-bearing step — proves whether the raw price data contains BEAR_FVG candles even though signals don't.

What to expect (Session 15 baseline output):
- S1: BEAR_FVG count 795 (post-fix); was 0 pre-fix
- S5: 562 NIFTY + 567 SENSEX = 1,129 canonical BEAR_FVG 3-bar shapes over 60d
- S4: NIFTY 13/28 bear-days = 46.4%; SENSEX 14/28 = 50.0%

### Step 2 — Six-bug code review (analytical, completed Session 15)

Read both zone builder files and look for asymmetries. The Session 15 review identified:

| ID | Severity | Component | Issue | Decision |
|---|---|---|---|---|
| **S1.a** | S1 | `detect_weekly_zones()` in both builders | W BEAR_FVG branch missing (only BULL_FVG implemented) | **FIX in this session** |
| **S1.b** | S1 | `detect_daily_zones()` in both builders | D-FVG entirely missing (any direction) | **FIX in this session** |
| **S15-1H** | S1 | `detect_1h_zones()` in live builder only | 1H BEAR_FVG missing (only BULL_FVG) | **FIX in this session** |
| S2.a | S2 | `detect_daily_zones()` D-OB | Non-standard ICT definition (uses move bar K+1 as OB instead of opposing prior K) | DEFER → TD-049 |
| S2.b | S2 | `detect_daily_zones()` D non-FVG | Validity = exactly 1 day | DEFER → TD-050 |
| S3.a | S3 | All zone builders, PDH/PDL | `+/- 20pt` band hardcoded, symbol-agnostic | DEFER → TD-051 |
| S3.b | S3 | Historical builder zone status | Write-once, never recompute | DEFER → TD-052 (by design — no-lookahead invariant) |

Decision rule (Session 15): fix only S1 bugs (low-risk symmetric mirrors of existing logic). File S2/S3 as separate TDs for explicit decision in a future session.

### Step 3 — Pre-write verification (dry-runs, completed Session 15)

Before any production write, dry-run both patched scripts:

```powershell
python build_ict_htf_zones_historical_PATCHED.py --dry-run --start 2026-04-01 --end 2026-04-30
python build_ict_htf_zones_PATCHED.py --dry-run
```

What to expect:
- Historical dry-run shows zone counts for the slice. Session 15 verification on Apr 2026 17-day slice: W BEAR_FVG > 0, D BULL_FVG > 0, D BEAR_FVG > 0 (all non-zero proves S1.a + S1.b firing).
- Live dry-run shows current cycle's would-be zones for both symbols. 39 NIFTY + 41 SENSEX W zones detected on 2026-05-02 dry-run; small D zone count (~2-3 per symbol) is normal — D-OB only fires when prior session body % ≥ 0.40%.

If dry-runs show BEAR_FVG counts at 0 across both timeframes despite a known bear-period in the slice → patches did not apply correctly. Stop, do not proceed.

### Step 4 — Historical backfill (write, completed 2026-05-02)

Full historical zone backfill against the symmetric detector:

```powershell
python build_ict_htf_zones_historical.py --start 2025-04-01 --end 2026-04-30
```

What to expect:
- Total rows written: ~40,000 (Session 15 result: 40,384 across 264 NIFTY + 263 SENSEX trading days)
- Counts per (symbol, timeframe, pattern_type) printed at end
- Session 15 baseline: W BEAR_FVG=1,384, W BULL_FVG=2,603 (ratio 0.53 — bull-trend regime), D BEAR_FVG=79, D BULL_FVG=84 (ratio 0.94 — symmetric)
- Duration: ~5 minutes
- Idempotent on `(symbol, timeframe, valid_from, valid_to, zone_low, zone_high)` — safe to re-run

Verify with:
```powershell
python diagnostic_hist_ict_htf_zones_distribution.py
```

Expected: BEAR_FVG counts non-zero at both W and D timeframes for both symbols.

### Step 5 — Live builder run (write, completed 2026-05-02)

Live zone builder writes to `ict_htf_zones` (current/active zones, ~85 rows after breach-recheck):

```powershell
python build_ict_htf_zones.py --timeframe both
```

What to expect:
- Output: "85 zones written" (or similar small count)
- Final lines show ACTIVE zones per symbol post breach-recheck (Session 15 baseline: 10 ACTIVE per symbol)
- Most newly-detected W BEAR_FVG zones get marked BREACHED on first run because spot has already moved past them in the past year — by design, not a bug

**NOTE**: The scheduled task `MERDIAN_ICT_HTF_Zones` (08:45 IST Mon-Fri) runs this script automatically with the patched version going forward. Manual run only needed if scheduler missed a run.

### Step 6 — Signal table rebuild (write, completed 2026-05-02)

Rebuild `hist_pattern_signals` from the symmetric zone table. The signal builder is direction-symmetric (verified during Session 15 code review) — no script changes needed:

```powershell
python build_hist_pattern_signals_5m.py
```

What to expect:
- Step 1: `Cleared` (existing rows deleted via `delete-where-source='backfill'` semantics)
- Step 6: signal counts printed at end
- Session 15 baseline: 6,318 → 7,484 rows. **BEAR_FVG: 0 → 795.** BULL_FVG: 1,261 → 1,490. BULL_OB: 2,345 → 2,411. BEAR_OB: 2,660 → 2,736.
- Duration: ~2 minutes

### Step 7 — End-to-end re-verification (completed 2026-05-02)

Re-run the original Step 1 diagnostic and confirm post-fix state:

```powershell
python diagnostic_bear_fvg_audit.py
```

What to expect:
- S1 BEAR_FVG count: 795 (was 0)
- NIFTY 60d: BULL_FVG 274 / BEAR_FVG 150 (ratio 1.83x — bull-skew, regime-driven, filed as TD-056 for investigation)
- SENSEX 60d: BULL_FVG 263 / BEAR_FVG 208 (ratio 1.26x)
- "Bear-flavoured types" line shows non-empty `{'BEAR_FVG': 795, 'BEAR_OB': 2,736}`

If output matches: fix verified end-to-end. **This is where Session 15 ended.**

---

## Verification

After Step 7 above, the fix is verified at three layers:

```powershell
# Layer 1: Detector (zones table)
python diagnostic_hist_ict_htf_zones_distribution.py
# Expected: BEAR_FVG counts non-zero at W and D timeframes for both symbols

# Layer 2: Signal builder (signals table)
python diagnostic_bear_fvg_audit.py
# Expected: hist_pattern_signals BEAR_FVG count > 0 (baseline 795)

# Layer 3: Live (current zones table) — verify scheduled run picks up patched builder
# Wait for next 08:45 IST scheduled run, then:
# (Run from PowerShell against Supabase)
# SELECT symbol, timeframe, pattern_type, COUNT(*)
# FROM ict_htf_zones
# WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
# GROUP BY symbol, timeframe, pattern_type
# ORDER BY symbol, timeframe, pattern_type;
# Expected: BEAR_FVG rows appearing in scheduled output (regime-dependent)
```

---

## Failure modes

| If you see… | It probably means… | Do this |
|---|---|---|
| `hist_pattern_signals.BEAR_FVG` count is 0 again | Either: (a) zone builder reverted to PRE_S15 version, or (b) signal builder schedule failed, or (c) `hist_ict_htf_zones.BEAR_FVG` is 0 (zone backfill issue). | Run Step 0. If files reverted, re-rename `_PRE_S15.py` ↔ canonical and re-run Steps 4-6. If only signal table is empty, re-run Step 6 only. |
| Dry-run (Step 3) shows 0 BEAR_FVG | Patches didn't apply — files are not the patched version. | `fc.exe build_ict_htf_zones_historical.py build_ict_htf_zones_historical_PRE_S15.py` should show differences. If no differences, patches were never applied. |
| Step 4 backfill produces ~40K rows but BEAR_FVG count is way off baseline (e.g., < 500 W BEAR_FVG over 12 months) | Either: (a) market regime has flipped — significantly more bear weeks would push counts higher (not a bug, just market state); or (b) the FVG threshold `FVG_W_MIN_PCT` or `FVG_D_MIN_PCT` has been changed | Compare count against canonical-shape count from `diagnostic_bear_fvg_audit.py` Step 5. If shape count and zone count diverge significantly, threshold may have been tightened. |
| Step 6 signal rebuild fails partway with `delete-where-source` error | The `delete-where-source='backfill'` step requires a row matching that source value. Recent runs may have used `'backfill_5m'` or similar — different source string. | Inspect signal builder: `grep -n "source" build_hist_pattern_signals_5m.py`. Reconcile delete pattern with what the builder actually writes. |
| `recheck_breached_zones` marks every zone BREACHED on first live run | Expected and correct. Most of the new W BEAR_FVG zones formed weeks/months ago; spot has already moved past them. | Not a bug. The breach mark reflects current price reality. Only zones where spot is still on the unbreached side stay ACTIVE. |
| Signal counts grow slowly over multiple manual runs (delete-where-source not actually clearing rows) | The `delete .eq("source", "backfill").execute()` pattern doesn't match the actual `source` value being written by the builder | Confirmed Session 15: source value written is `'backfill_5m'` not `'backfill'`. The delete pattern is a no-op. Workaround: manual `DELETE FROM hist_pattern_signals WHERE source = 'backfill_5m'` before rebuild. Long-term fix needed. |

---

## Related

- **Related runbooks**: None — this is a one-shot fix, not a recurring operation.
- **Related tech debt**:
  - **TD-048** (CLOSED 2026-05-02) — BEAR_FVG missing across detector pipeline. This runbook documents its closure.
  - **TD-049** (OPEN) — D-OB detector non-standard ICT definition. Found during Step 2 code review; deferred.
  - **TD-050** (OPEN) — D-zone non-FVG validity = 1 day. Found during Step 2 code review; deferred.
  - **TD-051** (OPEN) — PDH/PDL `+/- 20pt` hardcoded. Found during Step 2 code review; deferred.
  - **TD-052** (OPEN) — Zone status workflow write-once-never-recompute (historical builder). Found during Step 2 code review; documented as by-design.
  - **TD-053** (OPEN) — CLAUDE.md Rule 16 needs era-aware addendum. Discovered during Phase 1 of ADR-003, related but not part of TD-048 fix.
  - **TD-054** (OPEN) — `ret_60m` column uniformly 0.
  - **TD-055** (OPEN) — `ret_eod` column missing.
  - **TD-056** (OPEN) — Signal builder bull-skew investigation. Surfaced post-fix verification (1.83x NIFTY / 1.26x SENSEX BULL_FVG vs BEAR_FVG ratio).
- **Related code files**:
  - `build_ict_htf_zones.py` (PATCHED in place — current canonical version; original at `build_ict_htf_zones_PRE_S15.py`)
  - `build_ict_htf_zones_historical.py` (PATCHED in place — current canonical version; original at `build_ict_htf_zones_historical_PRE_S15.py`)
  - `build_hist_pattern_signals_5m.py` (NOT modified — direction-symmetric verified during code review)
  - `diagnostic_bear_fvg_audit.py` (5-step audit; preserved as the regression-detection script)
  - `diagnostic_hist_ict_htf_zones_distribution.py` (zone-layer verification)
- **Related tables**:
  - `hist_spot_bars_5m` (read-only source for canonical 3-bar shape scan)
  - `hist_ict_htf_zones` (historical zone table, written by historical builder; +40,384 rows from Session 15 backfill)
  - `ict_htf_zones` (live zone table, written by live builder; +85 rows from Session 15 live run)
  - `hist_pattern_signals` (signal table; rebuilt 6,318 → 7,484 rows; BEAR_FVG 0 → 795)
- **Related ADRs**:
  - `ADR-003-ict-zone-architecture-review.md` (Phase 1 ran in same session; INVALID due to TZ-handling bug; the BEAR_FVG fix was a side-effect of Phase 1 setup, not the architecture answer)
- **Related experiments** (in `MERDIAN_Experiment_Compendium_v1.md`):
  - **Exp 50** (FAIL with anomaly) — the bug-discovery vehicle. Operator's challenge to the "0 BEAR_FVG over 13 months" finding triggered this entire diagnostic chain.
  - **Exp 50b** (MARGINAL) — velocity test on Exp 50's inversion. BULL-only — invalid until Session 16 re-run on now-symmetric data.

---

## Change history

| Date | Change | Commit |
|---|---|---|
| 2026-05-02 | Created. Documents Session 15 BEAR_FVG fix end-to-end. | `<hash>` (Session 15 commit batch) |

---

*Runbook — commit with `MERDIAN: [OPS] runbook_session_15_detector_fix — created`.*
