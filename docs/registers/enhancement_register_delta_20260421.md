# MERDIAN Enhancement Register — Delta 2026-04-21

**Purpose:** Addendum to Enhancement Register v7 covering Session 3+4 of 2026-04-21. To be merged into v8 during next documentation debt closeout.

**Context:** Enhancement Register v7 on disk stops at ENH-59 (2026-04-13). Sessions between 2026-04-13 and 2026-04-21 added ENH-60 through ENH-74+ which are referenced in code comments and commits but not yet in the register. This delta captures tonight's additions only. Full v8 overhaul to cover the ENH-60..71 gap deferred to a future session.

---

## ENH-72 — ExecutionLog Write-Contract Propagation (9 of 9 critical scripts)

| Field | Detail |
|---|---|
| Status | **COMPLETE** — all 9 targets |
| Sessions | 2 (base layer), 3 (targets 1-5), 4 (targets 6-9) |
| Updated | 2026-04-21 |
| Authority | V19 §15 governance rule `script_execution_log_contract` |

**What this programme delivered:**

Every production script in the 5-minute pipeline now records each invocation to `script_execution_log` with:
- `exit_reason` classification (SUCCESS, DATA_ERROR, DEPENDENCY_MISSING, TOKEN_EXPIRED, HOLIDAY_GATE, SKIPPED_NO_INPUT)
- `contract_met` boolean (actual writes ≥ expected floor)
- `duration_ms` timing
- Structured `notes` for operator triage (symbol coverage, feature flags, subsystem degradation)
- `error_message` for failure triage

**Scripts instrumented:**

| # | Script | Contract | Commit |
|---|---|---|---|
| 1 | ingest_option_chain_local.py | {option_chain_snapshots: 50 or 8 by mode} | 3a22735 |
| 2 | compute_gamma_metrics_local.py | {gamma_snapshots: 1} via set_symbol helper | d676a73 |
| 3 | compute_volatility_metrics_local.py | {volatility_snapshots: 1} via set_symbol | 2173002 |
| 4 | build_momentum_features_local.py | {momentum_snapshots: 1} | 74e15a0 |
| 5 | build_market_state_snapshot_local.py | {market_state_snapshots: 1} | 70df409 |
| 6 | build_trade_signal_local.py | {signal_snapshots: 1}, ict_failed/enh06_failed flags, action in notes | b3d88fa |
| 7 | compute_options_flow_local.py | {options_flow_snapshots: 1} floor, partial-success tolerant | 1e75a74 |
| 8 | ingest_breadth_intraday_local.py | {equity_intraday_last: 100}, 4-layer guard → HOLIDAY_GATE | dd66076 |
| 9 | detect_ict_patterns_runner.py | {ict_zones: 0} floor, non-blocking exit 0 preserved | f121fca |

**Production validation (2026-04-21 trading day, live):**
- 1,871 total invocations logged across targets 1-5 during full session
- 5 failures (~99.7% clean rate)
- Failures classified correctly: 3 DATA_ERROR (Dhan timeouts), 2 incidental
- Final cycle 15:27 IST clean shutdown

**Critical behaviour decisions baked in:**
- `action=DO_NOTHING` is NOT a failure — it's a reasoned decision. contract_met=true for all successful decisions including DO_NOTHING.
- `trade_allowed=False` is NOT a failure — it's a gate firing. contract_met=true.
- Detector "no patterns found" (ict_zones floor=0) is NOT a failure — patterns are rare events.
- HOLIDAY_GATE exits (CalendarSkip) record cleanly instead of crashing.

**Remaining known contract hazards (out of ENH-72 scope):**
- signal_snapshots, volatility_snapshots use INSERT not UPSERT — duplicate (symbol, ts) would 23505. Latent; no production repro.
- ENH-72 instrumented everything but did NOT refactor the underlying write operations. Contracts audit data flow, not trade logic.

---

## ENH-37 ADDENDUM — 1H zone trigger made data-driven (supersedes is_hour_boundary time-window check)

| Field | Detail |
|---|---|
| Parent | ENH-37 (ICT Pattern Detection Layer) |
| Updated | 2026-04-21 |
| Trigger | OI-27 (1H zones never triggered in production) |
| Commit | d15c494 |

**Problem:** Original `is_hour_boundary()` in `detect_ict_patterns_runner.py` returned True only when `minute < 3`. Production runner cycle schedule (5-min offset from 09:14 start) never lands in minutes 0-2. Result: `detect_1h_zones` never called, `ict_htf_zones` had ZERO rows with timeframe='H' across the entire life of the pipeline.

**Fix:** Replaced time-window check with `should_rebuild_1h_zones(sb, symbol)`. Queries `ict_htf_zones` directly for existing H-timeframe rows in current hour. Rebuilds if none found. Works for any cycle schedule (whether :00/:05/:10 or :14/:19/:24). Idempotent upsert means re-firing would be harmless, but the check prevents wasted work. Fails open on query error.

**Verification:** 4 1H zones now visible in ict_htf_zones (first time ever in production). PDH/PDL for both NIFTY and SENSEX from today's session. No BULL_OB/BEAR_OB/BULL_FVG detected today because hourly moves didn't cross the 0.40% OB_MIN_MOVE_PCT threshold — that threshold is calibration, separate from this fix.

**Secondary fix (same commit):** `build_ict_htf_zones.py` had `if __name__ == "__main__": main()` positioned mid-file at line 559, before `detect_1h_zones` was defined at line 600+. CLI `python build_ict_htf_zones.py --timeframe H` crashed with NameError. Runner path via `from build_ict_htf_zones import detect_1h_zones` was unaffected. Moved `__main__` block to end of file.

---

## ENH-38 ADDENDUM — expiry lookup source changed to option_chain_snapshots

| Field | Detail |
|---|---|
| Parent | ENH-38 (Live Kelly Tiered Sizing) |
| Updated | 2026-04-21 |
| Trigger | OI-26 (SENSEX dte=-54d, NIFTY dte=252d observed) |
| Commit | 49c5e3c |

**Problem:** Kelly sizing input `dte_days` was computed via `build_expiry_index_simple(sb, inst_id) → nearest_expiry_db(trade_date, index)` in `merdian_utils.py`. The index was built by sampling `hist_option_bars_1m.expiry_date` at hardcoded monthly dates spanning 2025-04-01 through 2026-03-03. On 2026-04-21 the entire hardcoded window was in the past, producing a stale index with no future expiries. `nearest_expiry_db` fell through to `expiry_index[-1]` returning historical expiries, producing impossible DTEs (SENSEX -54d, NIFTY 252d).

**Fix:** New function `get_nearest_expiry(sb, symbol)` reads the latest `option_chain_snapshots.expiry_date` directly. This field is written every 5-minute cycle by `ingest_option_chain_local.py` from Dhan's live option chain response. Dhan itself handles NSE holiday-driven expiry shifts (Thursday holiday → Wednesday expiry, etc.) natively in its API, so the value is always correct without a local calendar.

**Architectural principle:** Don't re-implement calendar logic that the upstream broker API already handles correctly. Use the authoritative source.

**Retired (no current callers, kept for audit trail):**
- `build_expiry_index_simple()` — DEPRECATED
- `nearest_expiry_db()` — DEPRECATED
- ENH-63 `_EXPIRY_INDEX_CACHE` dict — REMOVED

**Smoke validation:**
- NIFTY dte=0d (correct — NIFTY weekly expires Tuesday 2026-04-21, today)
- SENSEX dte=2d (correct — SENSEX weekly expires Thursday 2026-04-23)

---

## ENH-63 — Expiry Index Cache

| Field | Detail |
|---|---|
| Status | **RETIRED 2026-04-21** (superseded by ENH-38 addendum) |

Original purpose: cache `build_expiry_index_simple()` output across cycles to avoid 12 paginated queries per call. Removed with OI-26 fix — the whole expiry index approach is obsolete, replaced by single-query `get_nearest_expiry()` reading the authoritative `option_chain_snapshots.expiry_date`.

---

## Non-Enhancement Fix: OI-24 (ICT schema mismatch)

| Field | Detail |
|---|---|
| Type | Bug fix (documented here because OI Register v7 is permanently closed) |
| Updated | 2026-04-21 |
| Commit | f121fca (folded into ENH-72 target 9) |

**Problem:** `detect_ict_patterns_runner.py` `load_atm_iv()` queried `market_state_snapshots.market_state` — a column that doesn't exist. The table stores features as separate JSONB columns (`volatility_features`, `gamma_features`, etc.). Original script's tail `sys.exit(0)` on any exception had silently masked this error in production for an unknown duration.

**Fix:** `load_atm_iv()` now reads `volatility_features.atm_iv_avg` directly — matches how `build_trade_signal_local.py` consumes the same field. Entire function body wrapped in try/except returning None (atm_iv is an optional input for the detector; downstream uses fallback thresholds).

**Why this matters beyond the immediate fix:** This is exactly the kind of silent degradation ENH-72 was designed to surface. Pre-instrumentation, the pipeline logged "all green" while a critical enrichment was failing. Post-instrumentation, the failure surfaced in `script_execution_log` as `exit_reason=DATA_ERROR` with the specific error message — we could see and fix it within one session.

---

*Delta document 2026-04-21 — to merge into Enhancement Register v8 at next full documentation update.*
