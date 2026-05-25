# MERDIAN Technical Debt Register

**Purpose:** A single living markdown file for *known broken-ish things* that aren't blocking but shouldn't be forgotten. This file fills the gap between:

- **C-N (critical)** in `merdian_reference.json` → must fix before next live session
- **ENH-N (enhancement)** in `Enhancement_Register.md` → forward-looking proposal, may never be built
- **Session-local tasks** in `session_log.md` → don't persist past today
- **Tech debt (this file)** → persistent, known, has a workaround, will be paid down when convenient

If an item doesn't fit those four buckets, it doesn't get tracked.

---

## How to use this file

1. **Add an item** when you discover a real issue mid-session that has a workaround and isn't blocking. Use the template below.
2. **Update an item** when the workaround changes, severity changes, or you learn more about root cause.
3. **Close an item** when fixed — move it to the `# Resolved (audit trail)` section at the bottom with the closing commit hash. Never delete.
4. **Promote** to C-N if it becomes blocking, or to ENH-N if it grows into a real enhancement.

---

## Severity scale

| Sev | Meaning | Response time |
|---|---|---|
| **S1** | Production-impacting workaround in place. Fix this sprint. | Within 5 sessions |
| **S2** | Non-blocking but degrades a real user-facing or research workflow. | Within 15 sessions |
| **S3** | Cosmetic, performance-tolerable, or affects only edge cases. | When convenient |
| **S4** | Anti-pattern flagged for future refactor. No active impact. | Aspirational |

---

## Item template

```markdown
### TD-<NNN> — <one-line title>

| | |
|---|---|
| **Severity** | S1 / S2 / S3 / S4 |
| **Discovered** | YYYY-MM-DD (session/appendix ref) |
| **Component** | <file path or table or system area> |
| **Symptom** | What you observe when this hits |
| **Root cause** | What we believe causes it (or "unknown") |
| **Workaround** | What is currently being done to live with it |
| **Proper fix** | What the real fix looks like |
| **Cost to fix** | <est sessions or hours> |
| **Blocked by** | <ENH-N, TD-N, or "nothing"> |
| **Owner check-in** | <date when last reviewed> |
```

---

## Active debt

> Items below are illustrative seeds based on the project state I've read.
> Audit and adjust before committing — replace with the real current state.

### TD-S35-NEW-1 — `historical_option_chain_snapshots` strike-coverage structural limit on MERDIAN-ingest tier

| | |
|---|---|
| **Filed** | 2026-05-24 (Session 35) |
| **Severity** | S2 |
| **Component** | `historical_option_chain_snapshots` (HOCS, post-Apr-2026 chain data); `ingest_option_chain_local.py` (live writer producing HOCS rows). |
| **Symptom** | Post-S35 full recompute on the v8 dual-source reader recovered 317/541 (58%) post-Apr-2026 retests to non-NULL `option_pnl_*`; +14 via Breeze 2026-04-16 surgical fill = 331/541. Of remaining 210 NULL post-Apr retests: 132 are level primitives (PDH/PDL/PWH/PWL/PMH/PML — direction=NONE, architecturally exempt). True residual ≈75 zone-primitive retest NULLs spread across post-Apr-2026 dates. Diagnostic partition by `formation_atm_status` shows the failures predominantly `formation_OK_retest_FAIL` or `formation_TOTAL_FAIL` for primitives whose spot drift from formation to retest exceeded the live writer's strike capture window. |
| **Root cause** | `ingest_option_chain_local.py` captures an **ATM±N strike window per 5-min cycle** (N a constant in the writer — observably ~10-15 strikes either side of running ATM based on HOCS row counts). When a primitive forms at spot X and is retested at spot X + ΔX such that the held-strike (the ATM strike at formation) falls outside the ATM±N window at retest moment, the live writer never captured that strike's 5-min snapshot at retest_5m. The chain prefetch in `_prefetch_chain_for_primitives` (ENH-106 v8 path) finds no row for (held_strike, retest_5m) in HOCS — premium lookup returns NULL → outcome columns NULL. This is a property of the live writer's capture configuration, not a defect of the reader. |
| **Impact** | (a) Permanent ceiling on post-Apr-2026 cohort coverage from MERDIAN-ingest tier alone; ~75 retests across the post-Apr-2026 window (~14% of the 541-retest cohort) in the long-spot-drift regime. (b) ADR-012 spot-anchored SL doctrine validation cohort unaffected (n=65 W+D+H zone retests clears n≥50 threshold). (c) Phase 3 GEX time-series build per ADR-002 v2 affected if it requires dense full-chain history. (d) Selection-research arc per D.16.2 / ENH-108 unaffected in spirit but the missed primitives represent a non-random sample (large-drift trades). |
| **Workaround** | (a) Restrict cohort analyses to retests where formation and retest spot are within roughly ±2%. (b) Surgical Breeze backfill per affected (date, strike, expiry, opt_type) tuple via `fill_2026_04_16_breeze_v3.py` analog. (c) Accept the residual as architectural limit of MERDIAN-ingest tier and document in cohort summaries. |
| **Proper fix** | Two paths: (1) **Widen the live writer's strike window** in `ingest_option_chain_local.py` from ATM±N to ATM±2N or symbol-aware ATM±(N + spot_volatility×factor); ~1 session investigation + writer patch + 2-3 weeks observation; storage cost roughly doubles for HOCS (~5.3 GB instead of 2.67 GB). (2) **Graduate Breeze rollingoption / get_historical_data_v2 to canonical historical backfill source** per ADR-013 PROPOSED + ENH-109; replaces MERDIAN-ingest tier as the post-Apr-2026 canonical, retains live writer only for real-time intraday consumption. Cost ~2-3 sessions (Breeze fetcher build + scheduler + verification cohort). |
| **Cost to fix** | Path 1: ~1-1.5 sessions + ongoing storage. Path 2: ~2-3 sessions + ongoing Breeze quota management (5000 calls/day). |
| **Blocked by** | Path 1 unblocked. Path 2 blocked on ADR-013 acceptance + n≥3 successful Breeze-tier backfills. |
| **Owner check-in** | 2026-05-24 (S35) — filed at session close; decision deferred to S36+. |

---

### TD-S35-NEW-2 — Pre-Apr-2026 vendor uncatalogued in System Map (critical institutional knowledge at risk)

| | |
|---|---|
| **Filed** | 2026-05-24 (Session 35) |
| **Severity** | S1 |
| **Component** | `hist_option_bars_1m` (54.8M rows pre-Apr-2026); `hist_atm_option_bars_5m` (vendor aggregation source); `hist_spot_bars_5m` + `hist_spot_bars_1m` (pre-Apr vendor spot data); `MERDIAN_System_Map.md` (documentation gap). |
| **Symptom** | The pre-2026-04-01 chain history in `hist_option_bars_1m` (54.8M rows / paid through 2026-04-07) was discovered by S35 diagnostic to be vendor-purchased ("we paid for it" per operator) but the vendor identity, contract terms, renewal cadence, refresh cadence, data format spec, exchange-mappings (`stock_code` conventions), and contact details are NOT documented in MERDIAN_System_Map.md or MERDIAN_Deployment_Topology.md. Currently this is the only known retail-accessible source for full-chain SENSEX history >2 years; the source is critical for all pre-Apr-2026 cohort work (every prior ENH-100/103/106 study + ADR-009 holdout splits + ADR-011 chain-table held-strike doctrine + S33 retest-cohort validation depends on it). |
| **Root cause** | Documentation gap — the vendor was integrated when MERDIAN was younger and the cataloguing discipline that produced System Map / Topology was not yet established. Through 5+ sessions of working with this table, the vendor identity has been referenced verbally between Navin and Claude but never written down. Bus-factor of one. |
| **Impact** | (a) Knowledge-loss risk: vendor identity, contract terms, refresh cadence not preserved anywhere outside operator memory; renewal cycle / contract end-date unknown to the documented system. (b) Any future investigation of "why did `hist_option_bars_1m` stop updating?" or "can we extend the contract?" requires operator manual recall. (c) ADR-013 PROPOSED (Breeze canonical historical backfill) — its rationale and replacement-cost analysis cannot be made cleanly without documenting what's being replaced. (d) If operator becomes unavailable, future Claude sessions will have to re-derive the vendor identity from external context, which may not be possible. |
| **Workaround** | None — the gap is documentation, not code. |
| **Proper fix** | Add a vendor catalog section to `MERDIAN_System_Map.md` (or new `MERDIAN_Vendor_Registry.md` if scope warrants): vendor identity, contract terms, refresh / delivery cadence, data format spec, `stock_code` mappings, contact info, renewal date, contingency / replacement options (ENH-109 Breeze graduation). Per Doc Protocol v4 Rule 7 (System Map currency). |
| **Cost to fix** | ~15-30 min operator time to dictate vendor details; ~30 min Claude time to write the catalog entry. |
| **Blocked by** | Operator availability for the dictation session. |
| **Owner check-in** | 2026-05-24 (S35) — filed at session close; S36+ scheduling. |

---

### TD-S35-NEW-3 — SENSEX symbology on ICICI Breeze API: `stock_code="BSESEN"` not `"SENSEX"`, undocumented in Breeze public docs

| | |
|---|---|
| **Filed** | 2026-05-24 (Session 35) |
| **Severity** | S4 |
| **Component** | ICICI Breeze API (`breeze-connect` SDK ≥1.0.69); `fill_2026_04_16_breeze_v3.py` (S35 backfill script); future SENSEX-on-Breeze consumers. |
| **Symptom** | During S35 Breeze surgical fill of 2026-04-16 chain gap, NIFTY worked with `stock_code="NIFTY" exchange_code="NFO"` returning full chain data; SENSEX returned empty `Success=[]` with `Status=200` (not an error, just no data) for every (`stock_code`, `exchange_code`) combination tested in the obvious mapping space. Empirical 6-variant probe (`SENSEX/BFO`, `SENSEX/NFO`, `SNSXIN/BFO`, `BSXSEN/BFO`, `BSESEN/BFO`, `BSESNS/BFO`) found `stock_code="BSESEN"` with `exchange_code="BFO"` as the only working combination — returns the expected ~30-strike full chain. The string `BSESEN` is not present in Breeze's official documentation pages (`api.icicidirect.com/breezeapi/documents/`) or any public ICICI Direct integration material that operator or Claude could locate. |
| **Root cause** | ICICI Direct internal symbology — `BSESEN` is the BSE-internal symbol for the SENSEX index option series on the Breeze API surface. Vendor-internal naming with documentation gap on Breeze's side. |
| **Impact** | (a) Any future SENSEX-on-Breeze code-path will hit the same dead end without the empirical knowledge. (b) ADR-013 (Breeze canonical historical backfill) when it graduates to canonical will need this codified. (c) If Breeze deprecates or renames `BSESEN`, MERDIAN's Breeze paths break silently (returns empty Success not error). |
| **Workaround** | None — the working value is `BSESEN`; no alternative path. |
| **Proper fix** | Add a "Breeze symbology" section to MERDIAN_System_Map.md (or `MERDIAN_Deployment_Topology.md` §Breeze) codifying: NIFTY=`NIFTY`/`NFO`, SENSEX=`BSESEN`/`BFO`. Update `fill_2026_04_16_breeze_v3.py` `SCOPE` constant docstring to flag the symbol mapping as TD-S35-NEW-3-canon. Add to any future Breeze fetcher script (ENH-109) the mapping as a `BREEZE_SYMBOL_MAP` constant at module top. |
| **Cost to fix** | ~10 min documentation; ~5 min code-comment addition. |
| **Blocked by** | Nothing. |
| **Owner check-in** | 2026-05-24 (S35) — filed at session close. |

---

### TD-S35-NEW-4 — `build_ict_primitives.py` writer is INSERT-only on `ict_primitive_outcomes`; schema column additions do not backfill existing rows

| | |
|---|---|
| **Filed** | 2026-05-24 (Session 35) |
| **Severity** | S3 |
| **Component** | `build_ict_primitives.py` (`upsert_outcomes` function); `ict_primitive_outcomes` table schema-add workflow. |
| **Symptom** | S35 verification of ENH-106 v8 dual-source reader and ADR-012 v9 SL writer both required separate manual `DELETE FROM ict_primitive_outcomes WHERE primitive_id IN (...)` SQL operations on the test cells before re-running the writer — because the writer's `upsert_outcomes` function is INSERT-only with existence-check semantics: rows whose `primitive_id` already exist in the outcomes table are skipped silently (logged as "inserted 0 outcomes"), so newly-added schema columns on those existing rows never get populated. For the v8 single-cell test on 2026-05-14 NIFTY M5, the writer ran cleanly, logged "inserted 0 outcomes," and the freshly computed `option_pnl_source` + `option_pnl_*` columns silently never landed in DB. Same issue blocked ADR-012 v9 verification until similar DELETE was run on the same cell. |
| **Root cause** | `upsert_outcomes` was written with INSERT-only idempotency semantics for compose-with-detector recompute workflows; the assumption was that an existing outcome row is canonical and should not be touched (preserving order of arrival of detections during streaming/batch runs). The assumption breaks when *new schema columns* are added — the existing row has NULL on the new column, the writer skips the row, and the column never populates. Fundamentally a column-add-without-upsert anti-pattern in the writer architecture. |
| **Impact** | (a) Every schema-add session (ENH-100 v3, ENH-103 v6, ENH-106 v8, ADR-012 v9) requires either TRUNCATE + full recompute (~30-60 min wallclock) OR per-cohort DELETE + targeted recompute as a manual step before populated rows appear. (b) Confusing during verification — "inserted 0 outcomes" log is misleading when intent was "update existing rows with new schema columns." (c) Existing 19,571 S35 outcomes do not have v9 sl_* columns populated until S36 TRUNCATE-and-rebuild executes. |
| **Workaround** | Manual DELETE before recompute on the affected cohort; for full schema-add deployment, TRUNCATE + full backfill. |
| **Proper fix** | Three options: (a) **Switch `upsert_outcomes` to UPSERT semantics on schema-stable columns** — explicit `INSERT ... ON CONFLICT (primitive_id) DO UPDATE SET <changed_cols>`; preserves idempotency for compose-with-detector workflows while allowing schema-add backfills. (b) **Add a "force_update" mode** — `MERDIAN_OUTCOMES_FORCE_UPDATE=1` env flag that switches the writer to UPDATE-or-INSERT for the duration of a session; sticks with INSERT-only default. (c) **Add a separate `backfill_outcomes_columns.py` helper** that re-computes only the new columns via SQL UPDATE join, bypassing the writer entirely. Option (c) is the lightest-weight + matches existing pattern of one-off backfill helpers. |
| **Cost to fix** | (a) ~1 session writer refactor + comprehensive smoke testing. (b) ~30 min env-flag + branch in upsert_outcomes. (c) ~1-2 hour helper script per schema-add (no writer change). |
| **Blocked by** | Nothing structurally; design decision needed. Option (c) is lowest-risk for S36 ADR-012 v9 cohort population (do TRUNCATE + full recompute as plan-of-record, defer fix to follow-on session). |
| **Owner check-in** | 2026-05-24 (S35) — filed at session close. |

---

### TD-S34-NEW-4 — `hist_option_bars_1m` post-2026-04-01 coverage gap (vendor → MERDIAN-ingest tier transition)

| | |
|---|---|
| **Filed** | 2026-05-24 (Session 34) |
| **Severity** | S2 |
| **Component** | `hist_option_bars_1m` chain table (54.8M rows pre-Apr-2026); MERDIAN chain ingest pipeline (post-Apr-2026 writer path, location TBD). |
| **Symptom** | Two-query diagnostic on S34 backtest (SL-fix on 7-day retest cohort) returned ZERO rows for both NIFTY and SENSEX on all nine probed post-2026-04-01 dates: 2026-04-01, 04-07, 04-09, 04-13, 04-16, 04-24, 05-12, 05-14, 05-18. Pre-2026-04-01 dates in the same cohort (2025-05-08 through 2026-01-20) returned full chain data — entry premium, intraday walk, EOD close all populated. The 22-row retest cohort assembled from `ict_primitive_outcomes.first_retest_ts` on ≥1% move-days collapsed to 7 usable rows; the 15 lost rows all fall in the post-Apr-2026 window. |
| **Root cause (operator framing 2026-05-24)** | Pre-Apr-2026 chain data is **vendor-purchased** — full, validated, dense across the 12-month window the operator paid for and verified. Post-Apr-2026 chain data is **MERDIAN-ingested** via a different writer path (location TBD — either a separate table/schema not under the same name, or a partial ingestion failure into `hist_option_bars_1m`). The "MERDIAN failed to ingest entirely" framing cannot be the full picture — plenty of full-ingestion days have been observed post-Apr-2026 elsewhere in the system (S29-S33 cohort work consumed data from that window). The gap is therefore *either* a storage-path mismatch (post-Apr-2026 chain data lives in a sibling table/location and `hist_option_bars_1m` writer was never extended to the new ingest tier) *or* partial-ingest failure scoped to a subset of dates within the writer's actual coverage. Initial framing of "Kite token expiry on MALPHA (TD-080-adjacent)" was incorrect — corrected per operator 2026-05-24. |
| **Impact** | (a) Backtest cohorts spanning the tier transition are artifically truncated — any retest cohort or primitive-outcomes consumer that touches post-Apr-2026 dates loses option-PnL columns silently. (b) ADR-009 holdout windows that include post-Apr-2026 lose their option-PnL anchor for affected primitives. (c) ENH-103/106 v7 outcomes for any primitive retested post-Apr-2026 are NULL on the 5 option-PnL columns — the affected cohort size is not yet quantified. (d) S34 spot-anchored SL doctrine validation (n=7) cannot expand to n≥50 until the gap closes — directly blocks the doctrine's promotion from "finding" to "validated rule." |
| **Workaround** | Restrict backtests and cohort selection to `trade_date <= '2026-03-30'` until the gap is diagnosed and closed. Document the transition date in any cohort summary so consumers of derived stats know they're operating on a truncated window. |
| **Proper fix** | Three sub-steps: (1) **Diagnose the tier transition** — locate where post-Apr-2026 chain data actually lives (separate table name? separate schema? in-process writer that targets `hist_option_bars_1m` but fails on specific dates?). Inspect MERDIAN chain-ingest writer code-paths + scheduler history + DB schema for sibling tables. (2) **Unify the storage** — if data lives elsewhere, migrate or shadow-write to `hist_option_bars_1m` so the canonical chain table reflects the full window. If partial-ingest, fix the failure mode + backfill missing dates via `backfill_option_zerodha_OI_FIXED.py` analog. (3) **Re-run ENH-106 v7 outcomes pass** against primitives retested in the post-Apr-2026 window to populate the option-PnL columns. |
| **Cost to fix** | ~1 session diagnostic (locate the post-Apr-2026 data) + ~1 session unification/backfill + ~30 min compute for outcomes recompute. Total 1-2 sessions assuming no surprise complications during diagnostic. |
| **Blocked by** | Nothing structurally; diagnostic can begin immediately. If diagnostic reveals MALPHA Zerodha token issues for the ingest path, work merges with TD-NEW-7 (token automation, S29+). |
| **Owner check-in** | 2026-05-24 — pending S35+ schedule. |
| **Resolution (S35 2026-05-24)** | **CLOSED-MECHANICAL.** Diagnosis confirmed two-tier architecture: pre-Apr-2026 chain lives in `hist_option_bars_1m` (vendor-purchased, 54.8M rows, uncatalogued vendor — filed as TD-S35-NEW-2); post-Apr-2026 chain lives in **`historical_option_chain_snapshots` (HOCS)** — 2.67M rows / 2.67 GB / 41 trading days at 5-min cadence keyed on `symbol` text not `instrument_id` uuid, `ltp` not `close`, written by `ingest_option_chain_local.py`. Calendar overlap clean on the boundary (NIFTY HOCS first expiry 2026-03-24 / SENSEX 2026-03-19; vendor last expiry 2026-04-07 NIFTY / 2026-04-02 SENSEX). Writer-side fix: `ENH-106 (S35) v8` adds boundary 2026-04-01 UTC + per-tuple split routing (pre→vendor 1m / post→HOCS 5m / mixed→both); `v8.1` UNION'd expiry calendars; `v8.2` swapped HOCS pagination for RPC `get_hocs_distinct_expiries(text)` + `(symbol, expiry_date)` covering index (sub-100ms vs 9-15 min). New audit column `option_pnl_source TEXT` values `vendor_hist_1m` / `merdian_hist_5m` / NULL. Full recompute S35: 19,571 outcomes (NIFTY 8,925 + SENSEX 10,646) in 2,107s; 1,716,572 pre bars + 49,204 post cycles across 2,773 (strike, expiry, type) tuples. 2026-04-16 single-day true gap filled via Breeze surgical write (107,630 HOCS rows: NIFTY 61,899 + SENSEX 45,731). Post-Apr retest cohort recovery 317/541 mechanical + 14 Breeze 04-16 = 331/541. Zone-primitive denominator (excluding 132 architecturally-exempt level primitives — direction=NONE, no CE/PE mapping): 331/409 = **81% recovery**. Residual 75 NULL post-Apr zone-primitive retests attributed to HOCS strike-coverage structural limit (`ingest_option_chain_local` captures ATM±N strike window, retests with large spot drift miss held-strike); filed as TD-S35-NEW-1. Earlier "Kite token expiry on MALPHA (TD-080-adjacent)" framing remains superseded. |

---

### TD-S33-NEW-1 — `hist_atm_option_bars_5m` reason-to-exist re-evaluation post-wick-experiment retirement

| | |
|---|---|
| **Filed** | 2026-05-22 (Session 33) |
| **Severity** | S3 (orphan-candidate; non-blocking) |
| **Component** | `hist_atm_option_bars_5m` table (27,082 rows), written by `build_atm_option_bars_mtf.py`, currently read by `experiment_26_option_wick_reversal.py` + `experiment_27_premium_ict.py` + `experiment_27b_premium_small_sweep.py`. Aggregated ATM table with vendor-pre-picked atm_strike per 5m bar + CE/PE OHLC + wick-ratio columns. |
| **Symptom** | Post-ADR-011, ENH-100/103 no longer read this table for ATM PnL computation (now reads `hist_option_bars_1m` chain). Table retains active readers (the three wick-reversal experiments). If/when those experiments are retired or migrated to chain-based wick computation, this table becomes orphaned. |
| **Root cause** | Architectural narrowing — table was built for wick analysis at ATM (its original purpose); ENH-100 v3 misused it for held-strike PnL (corrected by ADR-011 v7 to use chain). Wick experiments remain its only active consumers. |
| **Workaround** | None needed currently — table serves its original purpose for wick experiments. |
| **Proper fix** | Two-step gate: (a) when wick experiments are deprecated / retired, audit whether any other consumer has emerged; (b) if no consumers, drop the table + retire `build_atm_option_bars_mtf.py` writer + remove from Topology / System Map. Until then, no action. |
| **Cost to fix** | <1 hour drop + writer retirement + doc updates, gated on wick experiment retirement decision. |
| **Blocked by** | Operator decision on wick experiment lifecycle (no current plan to retire). |
| **Owner check-in** | Revisit at wave 1.5 / wave 2 ICT primitive build planning, or when wick experiments are formally retired. |

---

### TD-S33-NEW-2 — v6 dead code in `compute_atm_pnl_and_dte` trailing for-loop + retired `_atm_anchor_at` / `_atm_future_at` helpers

| | |
|---|---|
| **Filed** | 2026-05-22 (Session 33) |
| **Severity** | S4 (anti-pattern flagged for future refactor; no behavioral impact) |
| **Component** | `C:\GammaEnginePython\build_ict_primitives.py` lines ~1002-1022 (trailing v3 for-loop after v7 head's early `return out`) + `_atm_anchor_at` (lines ~871-907) + `_atm_future_at` (lines ~910-942). Helpers retired by ADR-011 / ENH-106 but bodies left in place to minimize patch surface. |
| **Symptom** | Three blocks of dead code: (a) v3 same-strike for-loop in `compute_atm_pnl_and_dte` is unreachable (v7 head returns before reaching it); (b) `_atm_anchor_at` is no longer called by any caller (v7 `compute_atm_pnl_and_dte` and `compute_retest_atm_pnl` use `_chain_premium_at`); (c) `_atm_future_at` same. Python doesn't error on unreachable code or unreferenced functions; AST validation passes. |
| **Root cause** | Patch surface minimization — ENH-106 v7 patch script (`patch_s33_enh106_chain_heldstrike_atm_pnl_writer.py`) made 4 substitutions; replacing entire function bodies would have required ~150 more lines of `old_str` match and risk of substitution failure on whitespace edge cases. Dead code path was the safer trade-off. |
| **Workaround** | None needed — dead code is inert. |
| **Proper fix** | Next writer refactor session: (a) delete `_atm_anchor_at` + `_atm_future_at` function bodies entirely; (b) delete the trailing v3 for-loop in `compute_atm_pnl_and_dte` after the v7 `return out`. AST-validate. ~15 min work. |
| **Cost to fix** | ~15 min in next writer refactor session. |
| **Blocked by** | nothing |
| **Owner check-in** | At next `build_ict_primitives.py` edit, or proactively if file readability matters before then. |

---

### TD-S33-NEW-3 — Post-v7 falsification audit needs re-scope

| | |
|---|---|
| **Filed** | 2026-05-22 (Session 33) |
| **Severity** | S2 (audit was committed-to in ENH-100 falsification criterion; now tautological in current form; needs replacement design) |
| **Component** | ENH-100 falsification criterion specified "ATM PnL columns must agree with `hist_option_bars_1m` premium-percent change to within 5% on a 100-sample audit." Post-ADR-011 / ENH-106 v7, both audit and writer read the SAME chain table — agreement is by construction. |
| **Symptom** | The original audit criterion no longer falsifies anything because it would compare the writer's chain read against the auditor's chain read of the same rows. Both will agree by construction unless one of them has a bug — but the bug class is different (strike-rounding correctness, expiry calendar lookup correctness, cache key computation). |
| **Root cause** | Source-table change invalidates the original audit design. |
| **Workaround** | None needed for trading decisions (ADR-011 evidence is the cohort-flip, which itself IS a strong falsification — universally negative→universally positive median is not a noise artifact). |
| **Proper fix** | New audit design: (a) sample 50-100 primitives across (symbol, tf, primitive_type, direction) cells; (b) for each, independently compute ATM strike via spot lookup + manual rounding; (c) independently identify nearest weekly expiry via direct DOW + holiday rule (NOT the empirical calendar — to cross-check the calendar lookup); (d) compare to writer's stored strike + expiry. Confirms strike-rounding + expiry-calendar logic, not the trivial chain-read agreement. |
| **Cost to fix** | ~3-4 hours: audit script + 50-100 sample selection + cross-computation + verdict report. |
| **Blocked by** | nothing |
| **Owner check-in** | S34+ depending on priority vs other carry-forward; non-blocking for trading decisions. |

---

### TD-S33-NEW-4 — D-TF horizon extension — `mfe_pct` + `time_to_mfe_min` columns may already answer "what horizon makes D-TF tradeable"

| | |
|---|---|
| **Filed** | 2026-05-22 (Session 33) |
| **Severity** | S3 (analysis-only; SQL against existing columns; informs future D-TF horizon design) |
| **Component** | `ict_primitive_outcomes` columns `mfe_pct` + `time_to_mfe_min` populated by ENH-100 for all primitives. D-TF cells show positive spot WR (~67% NIFTY D BULL_FVG; ~66% SENSEX) but negative option PnL median at 30m/60m horizons. EOD horizons also negative on D-TF retest cohort. |
| **Symptom** | D-TF spot edge is real but plays out over hours not 30 minutes — theta drains during the 30m/60m hold window before the spot move materializes. Without a longer-horizon option-PnL column, the option-tradeability of D-TF cells cannot be assessed without manual chain-table reads. |
| **Root cause** | ATM_PNL_WINDOWS_MIN constant is `[5, 15, 30, 60]` — designed for M5 cells (where spot moves fast). D-TF cells have spot move time-scales of 2-4 hours. No data layer change required; the data ALREADY exists in `mfe_pct` columns (spot MFE) but not in option-PnL form. |
| **Workaround** | SQL analysis using `mfe_pct` + `time_to_mfe_min` per (symbol, tf, primitive_type, direction) — answers "what horizon would D-TF cells be tradeable at if option PnL tracks spot MFE." If MFE peaks at +90-180m on D-TF cells, that's the candidate horizon. |
| **Proper fix** | Phase 1 — SQL-only analysis: aggregate `mfe_pct` + `time_to_mfe_min` per D-TF cell; verify hypothesis that MFE peaks 90-180m post-formation on D-TF. Phase 2 — if confirmed, decide between (a) extend ATM_PNL_WINDOWS_MIN to include 120m + 180m (writer change + re-backfill), OR (b) use `forward_120m_pct` × derived option-PnL-from-spot model (analysis-only, no writer work). |
| **Cost to fix** | Phase 1: ~30 min SQL analysis. Phase 2 decision-pending. |
| **Blocked by** | nothing |
| **Owner check-in** | S34+ depending on priority. |

---

### TD-S31B-NEW-1 — Pine v6 visual MTF-breach overlay deferred (Task 5 descoped after 5-version iteration with 6 Pine v6 ergonomic walls)

| | |
|---|---|
| **Filed** | 2026-05-21 (Session 31-B) |
| **Severity** | S3 (cosmetic / operator-facing tooling not on critical path; ADR-004 Wave 1 IMPLEMENTED end-to-end on data layer; visual overlay is operator convenience for TradingView) |
| **Component** | `/mnt/user-data/outputs/MERDIAN_ICT_Primitives_canonical.pine` (v1 472 lines through v5 537 lines; final v5 descoped by operator). Visual MTF rendering of `ict_primitives` table on TradingView Pine v6 overlay. |
| **Symptom** | Five Pine v6 iterations hit six independent ergonomic walls before operator descoped: (a) zones rendering as active regardless of breach due to Pine v6 descending for-loop `for i = array.size(arr) - 1 to 0` never executing without explicit `by -1`; (b) D BULL_OBs that should be broken still active due to CE10235 "Return type of if/switch blocks not compatible" — required moving `label.new()` to standalone if block no else; (c) per-TF close fetches via `request.security(sym, "W", close[1], lookahead=lookahead_off)` double-shift bug returning close from 2 periods ago (same bug broke PDH/PDL fetches showing Levels=0 in diagnostic); (d) `var int` global mutation prohibited in functions per CE10088 "Cannot modify global variable in function" — required `var array<int> = array.from(0)` one-element-array workaround; (e) `max_boxes_count=500` hard cap silently GC's overflow boxes (1428 of 1928 zones get GC'd silently — mutations on GC'd boxes are silent no-ops, so any UI state change including breach detection fails to render); (f) PDH/PDL canonical fetch idiom requires `[high[1], low[1]] + lookahead=barmerge.lookahead_on` to work both same-TF and cross-TF. Final v5 used `showBroken=false` default to bypass GC trap; visual rendering technically works at 158 active zones but operator decision: "Its messed up. Lets drop the pine script for now and proceed with the rest." |
| **Root cause** | Pine v6 ergonomic constraints are **systemic not incidental** — six independent classes of bugs surface when attempting to mirror Python detector logic verbatim with MTF rendering on a single overlay. The `max_boxes_count=500` hard cap is architectural (Pine v6 platform constraint) — cannot be increased; requires either TF filtering for <500 zones, GC-aware rendering, or alternative display patterns (multi-pane, multiple scripts). Task 5 estimated as 0.5-1 session at S31-A planning grew to 5 iterations because the constraint set was not understood up front. |
| **Workaround** | Operators consume `ict_primitives` table directly via SQL queries against Supabase or via downstream Python tools rendering to PNG/SVG (not TradingView native overlay). Data layer (ADR-004 Wave 1 IMPLEMENTED end-to-end) is unaffected — all 19,399 primitives + 19,399 outcomes are queryable via standard Supabase REST + SQL. Pine overlay is a convenience layer for TradingView users, not a critical-path artifact. |
| **Proper fix** | Wave 1.5 or later session — architectural redesign with explicit constraint design: (a) TF filtering to keep visible zones <500 (e.g., show only D + W + last 24h of M5); (b) GC-aware rendering — accept that broken zones disappear (showBroken=false) and accept the visual asymmetry vs Python detector; (c) alternative display patterns — multi-pane Pine layout, separate Pine script per TF, or external rendering tool. **Decision required at wave 1.5 planning:** is visual MTF-breach worth Pine-v6 architectural complexity, or substitute external rendering? Cost estimate: 2-3 sessions for architectural design + implementation if Pine-v6 path; 1 session for external rendering substitute. |
| **Pine v6 engineering catalog (codified for future Pine work)** | (1) Descending for-loops require explicit `by -1` — `for i = N-1 to 0` never executes (silent zero iterations, no compile error). (2) if/else branches must return matching types per CE10235 — pull `label.new()` into standalone if block (no else, no type-compat check). (3) `var int` global mutation from inside functions prohibited per CE10088 — wrap in `var array<int> = array.from(0)`, mutate via `array.set(arr, 0, new_val)`. (4) `close[1] + lookahead_off` double-shifts — canonical previous-completed-close idiom is `close[1] + lookahead_on` OR `close + lookahead_off` (not both). (5) PDH/PDL canonical idiom: `[high[1], low[1]] + lookahead=barmerge.lookahead_on` (works both same-TF and cross-TF). (6) `max_boxes_count` hard cap 500 in Pine v6 — cannot render >500 zones; either reduce zone count via TF filtering, delete on breach (showBroken=false), or accept GC. Mutations on GC'd boxes are silent no-ops, **not errors** — this is the trap that produced 4 iterations of S31-B Pine debugging. |
| **Cost to fix** | 2-3 sessions architectural redesign if Pine-v6 path; 1 session external rendering substitute. **Blocked by:** Operator decision on visual MTF-breach value vs Pine-v6 architectural complexity. **Owner check-in:** When wave 1.5 (ADR-004 Wave 2) planning begins or earlier if operator requests visual overlay sooner. |

---

| | |
|---|---|
| **Severity** | S1 (highest-leverage S30 finding; all gate-stack analyses on OB patterns work on 0.5% non-random sample by construction; per-OB-pattern live-cohort re-validation cannot proceed until attachment is restored) |
| **Discovered** | 2026-05-17 (Session 30 — `s30_gate_audit_and_ob_attachment.py` joined `ict_zones` against `signal_snapshots` on (symbol, ts within zone validity window, spot inside [zone_low, zone_high])) |
| **Component** | `enrich_signal_with_ict()` in `build_trade_signal_local.py` (or its callers / its `detect_ict_patterns.py` callee — exact site to be localized S31). Detection in `ict_zones` is correct; defect is at attachment time. |
| **Symptom** | BULL_OB zone-touches 4,882 over 8 weeks → only 26 tagged BULL_OB in `signal_snapshots.ict_pattern` (0.5% attachment rate). BEAR_OB zone-touches 3,139 → **zero** tagged BEAR_OB in `signal_snapshots.ict_pattern` (0% attachment rate). Most zone-touches end up tagged NONE or as FVG when adjacent FVG zones exist. Cohort-level: BULL_OB live-cohort N=5 (cannot replicate Compendium 84% at this N); BEAR_OB live-cohort N=0 (cannot replicate Compendium 92%). |
| **Root cause** | Unknown precisely — S30 audit confirmed (a) `ict_zones` rows have correct `pattern_type` (BULL_OB / BEAR_OB) and correct (symbol, valid_from, valid_to, zone_high, zone_low); (b) `signal_snapshots` rows captured at zone-touch timestamps with correct spot inside zone range; (c) yet `signal_snapshots.ict_pattern` does not get populated. Defect is in the join/lookup logic at attachment time, not in zone definition or signal capture. Top suspects: (1) `enrich_signal_with_ict()` may filter OB zones by some condition that excludes most of them (e.g. status, MTF context, validity recency); (2) priority ordering may prefer adjacent FVG zones over containing OB zones; (3) `detect_ict_patterns.py` runner pre-S17-TD060 single-bar window logic may still leak into the attachment path even after the S17 fix. |
| **Workaround** | None for OB cohort analysis. Continue trading discretionary on TV-displayed OB zones (these are sourced from `ict_zones` and remain correct). MERDIAN signal stream contains correct OB zones but does not surface them in `ict_pattern` column. FVG-tagged cohort analyses remain valid (BULL_FVG N=99 / BEAR_FVG N=107 from S30 v5 cohort). |
| **Proper fix** | (1) Read `enrich_signal_with_ict()` and trace OB-attachment path; (2) reproduce zero-tagging case on a single zone-touch row from S30 audit (e.g. an explicit BULL_OB zone-touch on 2026-05-06 14:26 NIFTY); (3) localize defect; (4) patch via patched-copy AST-validated pattern (mirror of S26 / S29 / S30 deployment workflow); (5) backfill `ict_pattern` column on historical `signal_snapshots` rows (~3 month window, ~12K rows) — optional if forward-only attachment is sufficient for S31+ re-validation; (6) re-run `s30_gate_audit_and_ob_attachment.py` post-fix to verify attachment rate ≥80% (operational threshold per S30 finding). |
| **Cost to fix** | ~1 session (~2-4 hours): defect localization + patch + smoke test + verification audit. Backfill of historical rows is optional and adds ~30 min if scoped. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-17 |

---

### TD-S30-NEW-4 — DTE=0 cohort behavior unknown — live cohort N too small for verdict

| | |
|---|---|
| **Severity** | S2 (orthogonal to OB attachment defect; if BULL_OB / BEAR_OB cohort grows post-TD-S30-NEW-3 fix, DTE=0 sub-cohort may surface independent gate-direction question) |
| **Discovered** | 2026-05-17 (Session 30 — `s30_gate_audit_and_ob_attachment.py` 8-dimension audit included DTE bucket but live cohort N per DTE bucket was too small for statistically meaningful verdict on DTE=0 specifically) |
| **Component** | `build_trade_signal_local.py` DTE gate (currently rejects DTE=0 in some configurations); evaluation on live cohort blocked on N expansion |
| **Symptom** | DTE=0 live cohort sub-N is insufficient for confidence-bounded verdict; cannot determine whether the DTE=0 gate suppresses positive-EV or negative-EV setups on live cohort. Bound: 89 of 211 setups were on weekly expiry (DTE 0-2); only ~30-35 of those were DTE=0; sub-cohort WR is wide CI. |
| **Root cause** | Sub-cohort sample size; not a code defect. Needs natural cohort growth (continued live signal capture; ~1-2 months for N≥30 per pattern × DTE=0 bucket) before statistically meaningful verdict can be reached. |
| **Workaround** | Keep DTE gate at S29 settings until N≥30 per pattern × DTE=0 sub-cohort. Document this as known unknown rather than gate any DTE=0 decisions on insufficient evidence. |
| **Proper fix** | (a) Wait for natural N accumulation; (b) re-run audit when N≥30; (c) decide based on live-cohort sub-bucket WR + CI bounds (D.13.1 principle applies; D.9.3 cohort-translation discipline applies). |
| **Cost to fix** | ~1-2 months calendar (N accumulation); ~30 min audit re-run when N met. |
| **Blocked by** | TD-S30-NEW-3 partially (if OB attachment defect is in DTE-conditional logic, fixing it may surface different DTE behavior); live cohort N≥30 per pattern × DTE bucket. |
| **Owner check-in** | 2026-05-17 |

---

### TD-S30-NEW-5 — Gate stack inversion on three context dimensions (gamma / breadth / vix) — investigation queued

| | |
|---|---|
| **Severity** | S2 (live cohort empirical evidence shows three gates suppress positive-EV buckets; gate-stack inversion mechanism is unknown; may be cohort-translation hazard or may be live-cohort-specific structural finding) |
| **Discovered** | 2026-05-17 (Session 30 — `s30_gate_audit_and_ob_attachment.py` 8-dimension audit per-bucket WR + mean + median across gamma_regime, breadth_regime, vix_regime) |
| **Component** | Three gates in `build_trade_signal_local.py`: (a) LONG_GAMMA hard-block; (b) BEARISH-ALIGNED breadth modifier; (c) HIGH VIX rejection path. All three are currently active on production (not env-disabled). |
| **Symptom** | (a) gamma_regime LONG_GAMMA WR 55.1% N=158 (gated BLOCK) vs SHORT_GAMMA WR 73.3% N=15 (gated PASS) — gating direction correct but rejected bucket is huge (15× the size of the gated-PASS bucket); bulk of high-edge setups blocked. (b) breadth_regime BEARISH-ALIGNED WR 64.7% (gate suppresses on alignment claim). (c) vix_regime HIGH WR 61.2% N=49 (gate suppresses on elevated path). All three gate-direction decisions inverted on live cohort vs the cohort they were derived from (likely `hist_pattern_signals` 5m-batch). |
| **Root cause** | Unknown — multiple hypotheses: (1) Cohort-translation hazard (D.13.1) — gates were validated on 5m-batch cohort and direction-of-edge is opposite on live cohort; same as ENH-76/77/88 + tier mult finding. (2) Mechanism difference — buyer's edge on live cohort may live in different regime/condition windows than research cohort. (3) Sample size — SHORT_GAMMA N=15 is tiny; the 73.3% may be coincidence. Investigation needs each gate isolated in dedicated study. |
| **Workaround** | Gates remain active at S30 close (env-flag disablement scope limited to ENH-76/77/88 + tier mult per S30 decision). LONG_GAMMA hard-block is the highest-impact gate; if it's a false-block, the operator-visible cost is ~158 setups/8 weeks = ~20 setups/week of potential positive-EV signals suppressed. Cost to investigate < cost of leaving suppression in place. |
| **Proper fix** | Per-gate dedicated study: (a) extract live-cohort pure-ICT setups by each gate decision (PASS / BLOCK); (b) measure WR + mean + median P&L per bucket; (c) compute Wilson CI bounds + p-value vs Compendium settled baseline; (d) decide based on D.13.1 cohort-translation discipline + statistical significance. Output: 3 separate findings for ADR-009 §S30+ case studies; possible env-flag disablement of one or more gates pending live-cohort re-validation. |
| **Cost to fix** | ~1 session per gate (3 gates × 1 session = ~3 sessions sequenced). Recommend LONG_GAMMA first (highest leverage). Investigation does not deploy code changes; deployment decisions per gate follow per D.13.1. |
| **Blocked by** | nothing (orthogonal to TD-S30-NEW-3 OB attachment; uses FVG cohort which is correctly attached). |
| **Owner check-in** | 2026-05-17 |

---

### TD-S30-NEW-6 — Replay infrastructure (`replay_build_trade_signal.py`) lacks ENH-88 — header line 15 attests S17 ENH was added post-S24 build

| | |
|---|---|
| **Severity** | S3 (replay parity gap; affects what-if experiment validity on any cohort that includes BULL_FVG cluster gate decisions; ~30 min patch) |
| **Discovered** | 2026-05-17 (Session 30 — operator confirmed via inspection of `C:\GammaEnginePython\replay\replay_build_trade_signal.py` header line 15 which lists ENH versions baked in at S24 build: ENH-53/55/76/77/78; ENH-88 was shipped S17 post-replay-build at S24, never back-ported to replay) |
| **Component** | `replay/replay_build_trade_signal.py` (Local — replay parity file for `build_trade_signal_local.py` per ADR-008 zero-touch constraint) |
| **Symptom** | Replay-time signal generation lacks ENH-88 BULL_FVG cluster gate logic. Any what-if experiment that hinges on whether ENH-88 fires (gate PASS / BLOCK) will produce results that don't match the live decision tree as it existed during the replay window. Specifically: live signal_snapshots rows captured S26+ may have `cautions` array containing "ENH-88: BULL_FVG standalone blocked" entries, but replay re-runs of the same boundary would NOT produce that caution because the replay file's gate logic predates ENH-88. |
| **Root cause** | Standard architectural drift between live and replay — when ENH-88 was shipped S17, the canonical workflow per ADR-008 §replay-vs-live parity required parallel patch to replay file; this back-port was not executed S17 nor at any subsequent session. Replay file is at S24-build state; live file is at S30-build state (now includes 4 env-flag gates + tier mult force from S30 + ENH-88 from S17). |
| **Workaround** | Avoid what-if experiments that intersect ENH-88 gate decisions until parity restored. Compendium settled cohort metrics on BULL_FVG remain valid (Compendium predates ENH-88 in scope). |
| **Proper fix** | Apply ENH-88 patch to `replay_build_trade_signal.py` mirroring the live ship S17 (commit at S26 deploy was `8407169` per CURRENT.md S26 block): add `ENH88_LOOKBACK_MIN: int = 90` + `_has_recent_bull_ob()` helper + ENH-88 gate block before `return out, flags`; sync three sites action + trade_allowed + out{} as in live; set `out["raw"]["enh88_decision"]`. AST-validate post-patch. Smoke test via single-boundary replay invocation matching a live signal_snapshots row known to have "ENH-88: BULL_FVG standalone blocked" caution; verify replay produces same caution. |
| **Cost to fix** | ~30 min (single-file patch + smoke test). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-17 |

---

### TD-S30-NEW-7 — Hold-time bucket study scope — formal N≥100 per exit-bucket measurement on live cohort

| | |
|---|---|
| **Severity** | S3 (S30 found hold-time persistence inversely correlated with edge on live cohort; T+30m Compendium-settled exit timing may be past asymmetric-winners-tail exhaustion; warrants formal study with proper N) |
| **Discovered** | 2026-05-17 (Session 30 — `s30_path1_live_cohort_pnl_v4.py` persistence × P&L analysis on live cohort) |
| **Component** | Exit timing decision (currently T+30m Compendium-settled). Affects: realized cohort P&L distribution; hold-time discipline in operator's hybrid TV-MERDIAN + discretionary workflow; future automation choice of exit logic. |
| **Symptom** | S30 v4 measured 4 exit buckets on live cohort: flipped-10-20m bucket WR 64.3% mean +4.00% (BEST); flipped-20-30m WR 56.5% mean +2.20%; held-full-30m exit WR 50% mean -1.80% (WORST); persistence-flipped-and-recovered WR mid-range. Direction: asymmetric winners are time-localized to first 10-20 min after signal; holding past 20m captures progressively more mean-reversion than continuation. Compendium settled WR (BEAR_OB 92% / BULL_OB 84% / BULL_FVG 50%) is measured at T+30m; if live-cohort optimal exit is T+10-20m, Compendium WR understates actual hold-the-right-time WR by an unknown but non-zero margin. Magnitude finding S30 cohort N=211 (total) ÷ 4 buckets = ~50/bucket — sufficient for direction-of-edge finding, insufficient for formal cohort verdict. |
| **Root cause** | Multiple hypotheses: (1) ICT signals are time-localized to entry mechanic (zone-touch + reversal) and don't have continuation thesis beyond 20 min; (2) cohort-wide mean-reversion regime; (3) selection bias in flipped vs held-full buckets. Investigation needed to disentangle. |
| **Workaround** | Operator discretionary trading already exits faster than T+30m on intuition — S30 finding empirically validates intuition. No production gate is on hold-time so no immediate code action needed. |
| **Proper fix** | Formal hold-time bucket study: (a) live cohort N≥100 per exit-bucket measurement; (b) compute WR + mean + median P&L per bucket × per ICT pattern type (BULL_FVG / BEAR_FVG / BULL_OB / BEAR_OB after TD-S30-NEW-3 fix); (c) compute Wilson CI bounds; (d) decide based on directional consistency across patterns + statistical significance whether to file ADR-010+ codifying live-cohort optimal exit window. ADR candidate if T+30m settled timing is empirically superseded. |
| **Cost to fix** | ~1 session for the study (data already accumulated). Ongoing analysis as cohort grows. |
| **Blocked by** | TD-S30-NEW-3 partially (per-pattern bucket counts need OB attachment to be useful for OB patterns; FVG patterns can proceed regardless). |
| **Owner check-in** | 2026-05-17 |

---

### TD-NEW-A — `market_ticks` retention runaway → 62 GB bloat → INSERT timeouts cascading into breadth outage (RESOLVED Session 29 in-flight)

**RESOLVED Session 29 (2026-05-14) in-flight as part of Incident §1 firefighting.** Full closure block is in the **Resolved (audit trail)** section below. Original pg_cron `delete-old-market-ticks` (jobid 45, `30 14 * * 1-5`, 2-day horizon) had been failing every weekday for 14+ consecutive runs since at least 2026-04-30 with `ERROR: canceling statement due to statement timeout` (Postgres 57014). Failed deletes accumulated `market_ticks` to 62 GB (22 GB heap + 40 GB indexes). At that size, `ws_feed_zerodha.py` bulk INSERT (2282 instruments × tick rate) began exceeding statement_timeout, producing 6+ hour breadth cascade on 2026-05-14. Fix: `TRUNCATE public.market_ticks` (62 GB → 856 kB in <1s, DDL primitive); `cron.unschedule(45)`; new `cron.schedule('prune-market-ticks', '*/30 * * * 1-5', $$DELETE FROM public.market_ticks WHERE ts < now() - interval '1 hour'$$)` → jobid 46. Design rationale: cadence 1/day → 1/30min, horizon 2days → 1hour decouples worst-case DELETE workload from cron cadence. Codified as CLAUDE.md B25 (TRUNCATE vs DELETE) + Topology §6.10 (token edits don't restart consumers; this TD's Root Cause A partner) + OI-12 RE-RESOLVED block in `MERDIAN_OpenItems_Register_v7.md`. See also `CASE-2026-05-14-breadth-cascade-token-and-bloat.md`.

---

### TD-NEW-B — `pg_cron` job failures invisible by default — needs polling daemon or session-start gate

| | |
|---|---|
| **Severity** | S1 (root cause of the 14+ day silent failure that escalated into the 2026-05-14 breadth cascade; without telemetry the next pg_cron failure class will also escalate silently before operator-visible symptoms surface) |
| **Discovered** | 2026-05-14 (Session 29 firefighting — surfaced during TD-NEW-A diagnosis when `cron.job_run_details` revealed 10 consecutive `delete-old-market-ticks` failures going back to at least 2026-04-30) |
| **Component** | `cron.job_run_details` Supabase system table records every cron run with `status` and `return_message`, but no MERDIAN telemetry polls it. New cron jobs (jobid 46 `prune-market-ticks` from TD-NEW-A fix) introduce the same blind spot until polling is implemented. |
| **Symptom** | Pg_cron job fails every weekday for weeks; downstream consumer eventually breaks; root cause invisible until cascade. Example: `delete-old-market-ticks` failed 14+ weekdays before 2026-05-14 breadth outage. |
| **Root cause** | No telemetry layer for `cron.job_run_details`. `merdian_pipeline_alert_daemon.py` (Local) polls Supabase tables but does not query the `cron` schema. Telegram alert daemon doesn't subscribe to cron-failure events. |
| **Workaround** | Manual session-start checklist SQL (per CLAUDE.md B26 + Topology §6.11): `SELECT jobname, status, return_message, start_time FROM cron.job_run_details d JOIN cron.job j USING (jobid) WHERE start_time > now() - interval '7 days' AND status != 'succeeded' ORDER BY start_time DESC;` Empty result = healthy. Any rows = investigate. Operator session-start ritual addition. |
| **Proper fix** | Either (a) extension of `merdian_pipeline_alert_daemon.py` to query `cron.job_run_details` every N minutes and Telegram-alert on any `status != 'succeeded'` row in last 24h, or (b) dashboard widget on `merdian_live_dashboard.py` surfacing recent cron failures. Approach (a) closes the failure class more aggressively; (b) requires operator to look at dashboard. Recommend (a). |
| **Cost to fix** | 1-2 sessions (Telegram daemon extension or dashboard widget; needs decision on alert deduplication policy). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-14 |

---

### TD-NEW-C — `ws_feed_zerodha.py` silent on Supabase 500 / token errors (extends TD-NEW-9)

| | |
|---|---|
| **Severity** | S2 (extends TD-NEW-9 — when WS feed reconnect-loops because Supabase rejects writes with 500 statement_timeout, the script silently retries indefinitely; no Telegram alert; operator has to grep logs to discover. Today on 2026-05-14 6+ hours of silent retries before manual log tail revealed `Supabase write error 500: ... statement timeout`) |
| **Discovered** | 2026-05-14 (Session 29 firefighting — `tail -f logs/ws_feed.log` revealed silent reconnect loop after restart with new token; the error class was distinct from TD-NEW-9's silent-on-success class but shared the same script and same "operator must manually grep logs" workaround) |
| **Component** | `ws_feed_zerodha.py` running on MERDIAN AWS — error logging is `print()` to log file only; no Telegram alert path; no escalation when retry count exceeds threshold |
| **Symptom** | Feeder receives ticks, attempts INSERT to `market_ticks`, Supabase returns 500 with statement_timeout, feeder retries indefinitely. No alert. Logs show repeated `Supabase write error 500: {...}` lines. Operator only finds out via downstream breadth-cascade symptoms hours later. |
| **Root cause** | No Telegram alert wiring in `ws_feed_zerodha.py`. The `import telegram_utils; telegram_utils.send_alert(...)` pattern used by other MERDIAN scripts is not present. |
| **Workaround** | Operator session-start session-start log tail: `tail -n 50 logs/ws_feed.log` looking for `error` / `500` / `timeout` substrings. |
| **Proper fix** | Bundle with TD-NEW-9 (silent-on-success heartbeat). Same touch point — add: (a) every N=1000 ticks log `[HEARTBEAT] N ticks processed, last_ts=X, latency=Yms`; (b) on any non-200 Supabase response, log error + send Telegram alert (dedupe by 5-min window); (c) on N=3 consecutive Supabase errors in 60s, escalate Telegram alert priority. |
| **Cost to fix** | <1 session if merged with TD-NEW-9 (~45 min). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-14 |

---

### TD-NEW-D — `ws_feed_zerodha.py` log timestamps `[HH:MM:SS IST]` are actually UTC (cosmetic)

| | |
|---|---|
| **Severity** | S2 (cosmetic — logs are mislabeled and 5h30m off but otherwise functional; operator triage time increases when reading timestamps in logs that are not what they claim) |
| **Discovered** | 2026-05-14 (Session 29 firefighting — verified via two adjacent log entries: `[04:27:06 IST]` actually issued at 09:57 IST; `[12:39:43 IST]` actually issued at 18:09 IST; 5h30m apart in real time despite both labeled IST) |
| **Component** | `ws_feed_zerodha.py` log prefix construction — uses `datetime.now()` which returns naive local-system-time UTC on AWS Ubuntu, then formats with `[%H:%M:%S IST]` literal string |
| **Symptom** | Log lines display incorrect `IST` timestamp by 5h30m. Operator manually adds 5h30m every read. |
| **Root cause** | `datetime.now()` on AWS Ubuntu returns UTC (no IST timezone). Format string hardcodes `IST` literal. |
| **Workaround** | Operator mental conversion. |
| **Proper fix** | Single-line change: `datetime.now()` → `datetime.now(ZoneInfo('Asia/Kolkata'))`. Bundle with TD-NEW-9 + TD-NEW-C in next ws_feed touch. |
| **Cost to fix** | 15 minutes at next ws_feed_zerodha.py touch. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-14 |

---

### TD-NEW-E — Topology §7.2 Task Scheduler inventory stale (17→19 entries) (CLOSED Session 29 in doc-close rewrite)

**CLOSED Session 29 (2026-05-14) as documentation gap.** Topology §7.2 was rewritten in S29 close commit: 17-task table → 19-task table reflecting S29 audit final state. Two newly-discovered tasks (`MERDIAN_Dhan_Token_Refresh`, `MERDIAN_Intraday_Session_Start`) added with action-untouched/settings-hardened state. Filed-and-closed pattern (same shape as TD-NEW-11 S28).

---

### TD-NEW-F — `runbook_update_kite_flow.md` missing Step 2d (consumer-restart) (RESOLVED Session 29 via runbook edits)

**RESOLVED Session 29 (2026-05-14) via 5 verbatim markdown edits applied at S29 close.** Header `Last verified` row updated to 2026-05-14 + Step 2d inserted between Step 2c and Step 3 + 2 new failure-mode rows + 2026-05-14 architectural-gap addition + change-history row. Closes the runbook gap that produced the 2026-05-14 breadth cascade incident (operator ran token-refresh sequence twice with correct `.env` end-state but did not restart the consumer process holding the prior token in memory). Codified as CLAUDE.md B24 (`.env` edits do not propagate to running processes) + Topology §6.10 new gotcha.

---

### TD-NEW-H — `backfill_volatility_snapshots.py` NULL `expiry_date` schema violation produces 7 daily pre-market CRASHes

| | |
|---|---|
| **Severity** | S2 (recurring CRASH count contributes to false-alarm noise; backfill writes are partially-blocked rather than fully-blocked, so research data is partially populated; pollutes script_execution_log audit) |
| **Discovered** | 2026-05-14 (Session 29 firefighting — surfaced during script_execution_log attribution analysis showing 7 daily CRASHes from `backfill_volatility_snapshots.py`) |
| **Component** | `backfill_volatility_snapshots.py` — pre-market backfill for `volatility_snapshots`; the script attempts INSERT with NULL `expiry_date` for some rows |
| **Symptom** | 7 CRASH exit_reason rows per day in `script_execution_log` from `backfill_volatility_snapshots.py`. Postgres rejects INSERT because `volatility_snapshots.expiry_date NOT NULL` constraint. Rows that should write don't write; backfill is partially incomplete. |
| **Root cause** | Unknown — needs source read of `backfill_volatility_snapshots.py`. Likely: query returns row with no expiry_date populated (e.g. weekend cycle or pre-market window before option chain populated). |
| **Workaround** | None active; partial backfill data is acceptable for research-only context. |
| **Proper fix** | Read source; identify whether NULL `expiry_date` rows should (a) be filtered out before INSERT (likely), (b) get a sentinel expiry_date value, or (c) trigger schema change to allow NULL. Then patch. |
| **Cost to fix** | <1 session (read script + 1-3 line patch + smoke test). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-14 |

---

### TD-NEW-I — Daily audit thresholds `spot_bars_per_symbol_min` + `market_spot_snapshots_per_symbol` too tight (RESOLVED Session 29)

**RESOLVED Session 29 (2026-05-14).** Full closure block is in the **Resolved (audit trail)** section below. `merdian_daily_audit.py` thresholds `spot_bars_per_symbol_min: 370` + `market_spot_snapshots_per_symbol: 370` flagged FAIL on days with 98% coverage (367/375). 2026-05-14 audit returned 4-fail FAIL OVERALL spuriously when actual coverage was 367/375 NIFTY and 366/375 SENSEX. Patched both thresholds to 365. Patch via `patch_s29_td_new_i_j_v2.py` (v1 abandoned due to regex undercatch). Backup `merdian_daily_audit_PRE_S29_TD_NEW_I_J_V2.py`. Codification: audit thresholds should match actual coverage realities (375 bars/day market, allow for 2-3 known gap minutes from operational timing windows). See `CASE-2026-05-14-spot-gap-backfill.md`.

---

### TD-NEW-J — `capture_spot_1m_v2.py` emits `'OUTSIDE_MARKET_HOURS'` exit_reason (= TD-083; RESOLVED Session 29)

**RESOLVED Session 29 (2026-05-14) — same root cause as TD-083, unified closure.** Full closure block is in the **Resolved (audit trail)** section below. `capture_spot_1m_v2.py` emitted exit_reason `'OUTSIDE_MARKET_HOURS'` against `chk_exit_reason_valid` closed-set constraint causing daily false-alarm CRASH rows. Patched call-site L346 + docstring L36 to `'OFF_HOURS'` via `patch_s29_td_new_i_j_v2.py`. Backup `capture_spot_1m_v2_PRE_S29_TD_NEW_I_J_V2.py`. Codification (B23 evolution): when code-side string literal renamed, prose-side references must update in lockstep OR rewrite prose to preserve grep-discoverability of old name. Patch v2 used `OFF_HOURS (was OUTSIDE_MARKET_HOURS pre-TD-NEW-J 2026-05-14)` in docstring to satisfy both.

---

### TD-061 — Task Scheduler entry points spawn visible console windows during pre-market and post-market hours (RESOLVED Session 29)

**RESOLVED Session 29 (2026-05-14).** Full closure block is in the **Resolved (audit trail)** section below. **NOTE: This TD was footer-claimed-RESOLVED at S18; body remained in Active section; S23 audit confirmed only 4/15 migrated; S29 audit found 19 tasks (up from 17 at S23) with only 4/19 on pythonw at S29-start. The earlier "RESOLVED" claim was a body-state-vs-footer-claim divergence — fixed at S29 close per Doc Protocol v4 candidate Rule N.** S29 firefighting completed the migration: `migrate_to_pythonw.ps1` (v2 — v1 abandoned due to regex shell-redirection capture bug); 13/19 tasks now on `pythonw.exe` directly; 18/19 with `Hidden=$true + MultipleInstances=IgnoreNew` settings; 5 residual flashes are low-frequency sources (Intraday_Supervisor_Start, Watchdog, Intraday_Session_Start, Dhan_Token_Refresh, Market_Tape_1M-broken). New `run_ict_htf_zones_daily.py` Python orchestrator replaces 3-step `.bat` for ICT_HTF_Zones_0845 task. Backups under `backups\scheduler\20260514_184211\` + `backups\scheduler\20260514_190443\`. See Topology §7.2 final-state table (S29 update) + `CASE-2026-05-14-breadth-cascade-token-and-bloat.md` (companion incident).

---

### TD-NEW-13 — Python 3.10 `fromisoformat()` rejects non-3/6-digit microsecond fractions (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. TD-NEW-4 `_dte_from_ts` helper passed Local Python 3.12 smoke on 5 sample rows but failed 60/587 backfill cycles on AWS Python 3.10 with `ValueError: Invalid isoformat string`. Supabase serializes PostgreSQL timestamps with variable microsecond precision (2-7 digits common); Python 3.10 accepts only exactly 3 or 6 digits; Python 3.12 is permissive. Fix: regex normalize microseconds to exactly 6 digits via pad/truncate before `fromisoformat()` in `_dte_from_ts` helper. Commit `447634c`. Retry on 60 failed run_ids: 60/60 success post-patch. Codified as Assumption Register §D.11.3 + Deployment Topology §6.9 + CLAUDE.md B22 (cross-Python-version stdlib semantics).

---

### TD-NEW-12 — AWS shadow runner writes to production `gamma_metrics` instead of `gamma_metrics_shadow` (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. Shadow architecture not implemented since MERDIAN AWS shadow runner deployment (~2026-04-29). `compute_gamma_metrics_local.py` on MERDIAN AWS wrote to production `gamma_metrics` table for 13 days; race-condition double-writes against the same `(symbol, ts)` row that Local was upserting (UPSERT semantics determined which value persisted per cycle). `gamma_metrics_shadow` table existed in Supabase but had 0 rows. Architectural invariant per Deployment Topology §6.5 silently violated. Fix: `--shadow` flag plumbing (TARGET_TABLE constant routes read + write + telemetry) + AWS wrapper line 479 passes flag + schema reconciliation (7 missing cols + UNIQUE constraint). Commits `72622a9` + `de23467`. Codified as Assumption Register §D.11.1 + Deployment Topology §6.5 update + §6.8 new gotcha + CLAUDE.md S28 settled bullet.

---

### TD-NEW-11 — `merdian_order_placer.py` not catalogued in Deployment Topology §3 AWS-only scripts (RESOLVED Session 28 documentation gap)

**RESOLVED Session 28 (2026-05-13) as documentation gap.** Full closure in S28 doc-close rewrite of `MERDIAN_Deployment_Topology.md` — §3 row added for Phase 4B Order Placer (HTTP server port 8767, Dhan-IP-whitelisted Elastic IP `13.63.27.85`, `@reboot` cron, deployed 2026-04-29). §7.1 @reboot cron entry added. §8.2 log path `logs/order_placer.log` added. Filed as S3 documentation gap surfaced when investigating TD-NEW-10 (which was filed-in-error as un-audited process; investigation showed it was intentional Phase 4B service, just absent from docs). No code change needed.

---

### TD-NEW-10 — `merdian_order_placer.py` running deployed but un-audited (CLOSED Session 28 filed-in-error)

**CLOSED Session 28 (2026-05-13) as filed-in-error.** Full closure block is in the **Resolved (audit trail)** section below. Process discovered running on MERDIAN AWS during S28 investigation; PID 579 confirmed; filed as "un-audited process". Investigation surfaced: intentional Phase 4B Order Placer (HTTP server port 8767, Dhan-IP-whitelisted Elastic IP, @reboot cron, deployed 2026-04-29 — predates current session's full Topology audit). Not a defect. Real issue was documentation gap → TD-NEW-11 filed and closed same session by adding row to Topology §3 + §7.1 + §8.2. CLAUDE.md S28 settled-decision bullet codifies the canonical "audited live, confirmed intentional" closure pattern.

---

### TD-NEW-9 — `ws_feed_zerodha.py` silent on success; no INFO heartbeat for nominal operation

| | |
|---|---|
| **Severity** | S2 (operational hygiene — when WS feed appears stuck, operator cannot distinguish "stuck/dead" from "running fine but silent on success" without grep'ing for new ticks landing in `market_ticks` table; cost is investigation time, not signal quality). |
| **Discovered** | 2026-05-13 (Session 28 — S28 drift period included a ~5 min WS feed outage triage where operator suspected stuck process; root cause was Zerodha-side connectivity which resolved via reconnect after 60s cycles, but script-side logs were silent making the diagnosis slower than necessary). |
| **Component** | `ws_feed_zerodha.py` running on MERDIAN AWS — currently logs only on errors, reconnects, and structural events. No periodic heartbeat or per-N-tick INFO line. |
| **Symptom** | `tail -f logs/ws_feed.log` shows no output during nominal operation. Operator cannot confirm liveness without cross-checking `market_ticks` table writes (DB-side proxy). When MERDIAN_WS_Stop pkill fires at 15:32 IST, log just stops mid-silence; no "shutting down" or "tick count summary" line. |
| **Root cause** | Original `ws_feed_zerodha.py` design optimized for low log volume; no heartbeat-style instrumentation. Standard pattern across other long-running MERDIAN scripts is per-cycle INFO line on `script_execution_log` table, but WS feed runs continuously not in cycles. |
| **Workaround** | Cross-check `SELECT MAX(ts) FROM market_ticks WHERE symbol='NIFTY'` to confirm liveness. Costs ~15-30 seconds during a triage. |
| **Proper fix** | Add per-N-tick INFO heartbeat (e.g., every 1000 ticks log `[HEARTBEAT] N ticks processed, last tick TIMESTAMP, latency Xms`). Plus shutdown handler: on SIGTERM/SIGINT log final summary before exit. Plus periodic (every 60s) liveness line even if 0 ticks processed in window — distinguishes "alive but idle" from "dead". |
| **Cost to fix** | <1 session (~30-45 min — ws_feed_zerodha.py is the touch point; tests local before AWS git pull). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-13 |

---

### TD-NEW-8 — MERDIAN_WS_Stop cron `pkill -f` ignores SIGTERM; 9 zombies accumulate (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. MERDIAN AWS crontab entry `02 10 * * 1-5 pkill -f ws_feed_zerodha.py` (15:32 IST WS stop) was sending SIGTERM (default `kill -15`). `ws_feed_zerodha.py` ignored SIGTERM (no signal handler installed); accumulated 9 zombies over Apr 30 → May 11 (~1.4GB RAM impact). Fix: `pkill -9 -f` (SIGKILL) — kernel kills process unconditionally. Config-only change. Topology §7.1 updated. CLAUDE.md S28 settled-decision bullet.

---

### TD-NEW-7 — MALPHA → MERDIAN AWS Zerodha token propagation is manual `sed`; should be Supabase `system_config` automation (Dhan-flow mirror)

| | |
|---|---|
| **Severity** | S1 (production-impacting — two outages in two months (2026-04-22 + 2026-05-12) directly traced to this manual step; live signal pipeline can't function on AWS without Kite-token-dependent scripts working; Local has its own Kite auth path so production decisions continue, but AWS shadow + AWS-side per-strike OHLC backfill paths break). |
| **Discovered** | 2026-05-13 (Session 28 — surfaced via MALPHA-as-third-environment Topology gap analysis; two operational outages had been investigated separately but never connected to the architectural cause; S28 doc-close work made the dependency visible). |
| **Component** | MALPHA AWS (Zerodha Kite token gateway, `~/meridian-alpha`, `ubuntu@13.51.242.119`) writes new Zerodha access token to local `.env`; operator manually runs `sed` on MERDIAN AWS `/home/ssm-user/meridian-engine/.env` to propagate. No automation. |
| **Symptom** | When Zerodha access token expires (typically once per market day per Kite Connect TOS), MALPHA refreshes via headless-interactive browser-TOTP flow on its own EC2. The new token is in MALPHA's `.env` only. Until operator manually runs the `sed` step on MERDIAN AWS, MERDIAN-AWS-side scripts that import `kiteconnect` (`ingest_option_chain_local.py` AWS path for shadow chain; any Zerodha-side per-strike OHLC backfill; `check_kite_auth.py`) operate against stale token and fail. Two outages observed: 2026-04-22 morning, 2026-05-12 morning. Both presented as AWS-side option-chain ingest failure; investigation each time traced to stale Zerodha token. |
| **Root cause** | Architectural — MALPHA writes only locally, no Supabase write. The original MALPHA design treated MALPHA as a self-contained Kite gateway; the dependency from MERDIAN AWS for Kite-side calls emerged later (around the time `ingest_option_chain_local.py` AWS path was extended to call Kite REST). The manual `sed` step was a temporary workaround that became permanent. |
| **Workaround** | Operator manually runs the `sed` step on MERDIAN AWS after MALPHA refresh. ~3 minutes per occurrence. Forgotten or delayed → outage. |
| **Proper fix** | Mirror the Dhan token flow exactly: (1) MALPHA writes refreshed Zerodha access token to Supabase `system_config` table (key = `ZERODHA_ACCESS_TOKEN`, write_ts, host=`malpha`). (2) MERDIAN AWS `pull_token_from_supabase.py` (currently Dhan-only) extended to also pull Zerodha key; writes to `/home/ssm-user/meridian-engine/.env`. (3) AWS cron `MERDIAN_Token_Refresh_Zerodha` at e.g. 03:10 UTC = 08:40 IST (5 min after Dhan token pull to allow MALPHA replication). Closes the failure class. Runbook update: `docs/runbooks/runbook_update_kite_flow.md` updated to remove manual sed step and document the automation. |
| **Cost to fix** | ~60-90 min spans MALPHA + MERDIAN AWS + Supabase. Per the Dhan-flow precedent (which works reliably), the pattern is known. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-13 |

---

### TD-NEW-6 — Local `MERDIAN_WS_Feed_0900` task is a dead-stub firing daily; pollutes logs (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. Local Task Scheduler `MERDIAN_WS_Feed_0900` (~09:00 IST Mon-Fri) was wired to `cmd.exe /c run_ws_feed_zerodha.bat` (wraps `ws_feed_zerodha.py`). Actual production WS feed runs on MERDIAN AWS only (browser-TOTP auth flow can't run headless on AWS unless gateway-routed, but the Local invocation was a vestigial design that never produced useful ticks — `market_ticks` writes came from AWS or were absent). Daily firings polluted `task_output.log` + `script_execution_log` with no-op runs that occasionally crashed mid-session interrupting operator workflow. Fix: PowerShell `Disable-ScheduledTask -TaskName MERDIAN_WS_Feed_0900` (durable). Topology §2 + §7.2 updated. CLAUDE.md S28 settled-decision bullet.

---

### TD-NEW-5 — Pine overlay regeneration not chained off `MERDIAN_ICT_HTF_Zones_0845`; operator must run manually (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. `run_ict_htf_zones_daily.bat` (wraps `build_ict_htf_zones.py --timeframe both`) was producing fresh `ict_htf_zones` rows at 08:45 IST but `generate_pine_overlay.py` (which produces the TradingView Pine v6 overlay file from current zone state) had to be run manually each session. Operator missed runs occasionally → stale Pine overlay rendered against current price action with old zones. Fix: bat file extended with Call 3 (`python generate_pine_overlay.py --output dashboards\ict_overlay.pine`) chained after the two existing zone-build calls. Config-only change. Topology §A.2 + §7.2 updated. CLAUDE.md S28 settled-decision bullet.

---

### TD-NEW-4 — `compute_gamma_metrics_local.py` `dte` payload derived from `date.today()` not `result.ts.date()` (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. `upsert_gamma_metrics()` computed `dte` as `(date.fromisoformat(result.expiry_date) - date.today()).days`. Live writes were correct because `result.ts ≈ now` (within seconds). Backfill writes were systematically wrong — running compute on 2026-05-12 NIFTY data on 2026-05-13 produced `dte = -1` instead of `dte = 0` (the run was on its expiry day). Latent bug, surfaced during TD-NEW-12 smoke test. Fix: `_dte_from_ts(result)` helper at module level derives as-of date from `result.ts` in IST; payload line uses helper. Bundled in commit `72622a9`. Cross-validated 2026-05-12 NIFTY run_id `e2dd1a09-...`: post-patch dte=0 (correct), pre-patch dte=-1 (wrong). Codified as Assumption Register §D.11.2 + CLAUDE.md S28 settled bullet.

---

### TD-099 — URL-encoding bug pattern audit (RESOLVED Session 26 as filed-in-error)

**RESOLVED Session 26 (2026-05-10) as filed-in-error.** Full closure block is in the **Resolved (audit trail)** section below. Operator picked TD-099 at S26 opening for sweep work; URL-spy verification (intercepted `requests.get` calls) showed all 4 scripts in scope emit clean single-`?` URLs with proper encoding — match was a false-positive grep against dashboard-style code patterns. ~3 hours of unnecessary patching avoided. Filing rule established: "same anti-pattern in N other scripts" claims require URL-spy or runtime trace verification before priority assignment, not just grep matches. CLAUDE.md B19 codifies the broader OI-18 propagation lesson (TD-099 grep was shape-specific to URL construction; the real propagation site was TD-101 inside a writer-side helper that grep couldn't reach).

---

### TD-101 — `build_momentum_features_local.py::get_session_open_spot()` unbounded query NULLs `ret_session` (RESOLVED Session 26 same-session)

**RESOLVED Session 26 (2026-05-10) same-session as discovery.** Full closure block is in the **Resolved (audit trail)** section below. Patch script `patch_s26_td101_ret_session.py` replaces `get_session_open_spot()` body with bounded query — `today_start_utc_iso` derived from `current_ts.astimezone(timezone.utc)` date; `gte("ts", today_start_utc_iso)` filter; limit=20; defense-in-depth date filter inside loop preserved; threshold 03:35 UTC preserved per ENH-01/V18G regression history (catches both 09:05 IST Local PreOpen now-disabled and 09:08 IST AWS PreOpen current anchor). Smoke test PASS Friday 2026-05-08 close prices: NIFTY 24,161.3, SENSEX 77,582.08; Sunday both None (clean, no errors). Backup `build_momentum_features_local_PRE_S26_TD101.py` preserved. Commit `3cb84e2`. **Same OI-18 anti-pattern class as S25 TD-097 dashboard fix** — propagation never reached this writer-side helper because S25 TD-099 grep audit was shape-specific to URL construction. Live impact: ENH-55 momentum opposition gate (which gates on `ret_session is not None`) was silent no-op for 24 trading days 2026-04-17 → 2026-05-10, ~5,000 signals. Surfaced retrospective evidence (N=44 OPPOSED at 79.5% WR vs Exp 20's claimed 38.3%) directionally falsifying Exp 20 hypothesis, prompting same-session ENH-55 disablement by env flag (commit `5b94c78`, default OFF, reversible via `MERDIAN_ENH55_ENABLED=1`). Filed as Assumption Register §D.9 (5 rows D.9.1–D.9.5 + 4 open follow-ups + ADR-009 first-case-study material). CLAUDE.md B19 codifies the broader OI-18 propagation lesson.

---

### TD-098 — Single-boundary replay momentum_regime classification differs from full-day orchestrator

| | |
|---|---|
| **Severity** | S4 (replay-side artifact; affects what-if experiment interpretation when single boundaries are spot-checked rather than running the full orchestrator). |
| **Discovered** | 2026-05-10 (Session 25 — observed during S25 ret_session anchor migration validation; replay invoked at single boundaries produced different `momentum_regime` than the same boundary inside a full-day orchestrator run). |
| **Component** | `replay/replay_build_momentum_features.py` — when invoked standalone at a single `--replay-ts`, downstream momentum_regime classification can differ from the full-day orchestrator's value at the same boundary. |
| **Symptom** | Single-boundary replay reports e.g. `momentum_regime='BULLISH_TRENDING'` at 11:05 IST. Full-day orchestrator running 09:15→15:30 reports `momentum_regime='BULLISH_PULLBACK'` at the same 11:05 boundary. Discrepancy traces to upstream state (prior `session_vwap` series, prior momentum_snapshots row for ret_session_anchor) being computed differently when replay starts mid-session vs. running through every boundary in sequence. |
| **Root cause** | Likely: `momentum_snapshots_replay` filters with `ts <= replay_ts ORDER BY ts DESC LIMIT 1` for "prior cycle" lookup; in single-boundary mode this returns whatever's already in the table from a previous run (possibly nothing, possibly stale) instead of an in-sequence prior boundary's row. Confirmed pattern matches what ADR-008 `'What what-if experiment means'` framework already noted: "Per-boundary script ordering contract is load-bearing." Single-boundary spot-checks under-detect for the same reason ICT pattern detection does — patterns whose anchor bar is outside 30-bar lookback at sparse invocations. Same logic applies to momentum sequence dependencies. |
| **Workaround** | Always run full-day orchestrator for replay-vs-replay comparison. Single-boundary invocation acceptable only for plumbing smoke-tests, not for momentum-regime classification analysis. Document in ADR-008 §'Single-boundary caveat' (already partially noted; expand in S26 or whenever ADR-008 is next touched). |
| **Proper fix** | Two options: (a) require single-boundary replay invocation to fail-fast if no prior `momentum_snapshots_replay` row exists for the same `replay_date` and `run_id` (defensive guard); (b) document the constraint and rely on operator discipline. Option (a) is safer; ~1 session of work. |
| **Cost to fix** | ~1 session for option (a); zero code for option (b). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-10 |

---

### TD-097 — Dashboard pre-open status URL-encoding bug (RESOLVED Session 25)

**RESOLVED Session 25 (2026-05-10).** Full closure block is in the **Resolved (audit trail)** section below. Patch script `patch_s25_dashboard_preopen_gap.py` deployed; 5 substitutions applied to `merdian_live_dashboard.py`; ENH-96 (gap display widget) shipped same-session as side-effect of the investigation.

---

### TD-096 — Replay reconstructor skips boundary 15:30 because last `hist_spot_bars_1m` bar is at 15:29 IST

| | |
|---|---|
| **Severity** | S4 (cosmetic — replay produces 75/76 boundaries instead of 76/76; downstream effect is one missing replay row at the session-close boundary). |
| **Discovered** | 2026-05-09 (Session 24 — observed during ENH-93 Phase 4b full-day orchestrator run on 2026-05-07). |
| **Component** | `C:\GammaEnginePython\replay\replay_chain_reconstructor.py` `_reconstruct_symbol`; the `direct datetime lookup` in `bars_by_ts.get(boundary_utc, [])` returns empty for the 15:30 IST boundary because no `hist_option_bars_1m` row has bar_ts=15:30 IST (last hist bar is 15:29 IST). Reconstructor reports `boundaries: emitted=75 skipped=1` per symbol. |
| **Symptom** | One boundary missing per symbol per replay run (76 generated → 75 emitted). Per-script success matrix shows N/152 instead of N/154 baseline-corrected. Phase 4b 2026-05-07 run: gamma 144/152, volatility 147/152, options_flow 150/152 — all reflect this skipped boundary cascading to dependent scripts. |
| **Root cause** | `hist_spot_bars_1m` and `hist_option_bars_1m` capture bars whose `bar_ts` represents the bar START minute. Session ends 15:30 IST inclusive, so the last bar STARTS at 15:29 IST (covers 15:29:00–15:29:59) and there is no bar starting at 15:30:00. Replay's boundary generator emits 76 5-min boundaries 09:15–15:30 inclusive; the 15:30 one has no corresponding hist bar. |
| **Workaround** | Accept 75-boundary replay as healthy. None of the per-script success criteria fail because of this — the orchestrator's per-script success-rate matrix is the trustworthy diagnostic. |
| **Proper fix** | Two options: (a) extend `hist_spot_bars_1m` capture to write a 15:30:00 bar at session close (operational change to capture pipeline; requires upstream coordination); (b) reconstructor synthesizes a 15:30 boundary by carrying forward 15:29's close as 15:30's spot (single-line addition; preserves bar count parity). Option (b) is simpler but introduces a synthetic-bar source that future debugging needs to be aware of. |
| **Cost to fix** | ~30min (option b) to ~1 session (option a). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-09 |

---

### TD-095 — `atm_iv_avg` unit ambiguity surfaces in `detect_ict_patterns_runner.py` Kelly sizing path

| | |
|---|---|
| **Severity** | S3 (potentially mis-sizes Kelly lots if Kelly was designed for percent — observed cosmetically as `iv=0.1%` in detector log when actual IV is 14.9%; functional impact pending verification of `compute_kelly_lots` IV-input expectation). |
| **Discovered** | 2026-05-09 (Session 24 — observed during ENH-93 Phase 3 ICT detector run on 2026-05-07; replay surfaced the issue but it applies to live identically). |
| **Component** | `compute_volatility_metrics_local.py` (writes `atm_iv_avg`); `detect_ict_patterns_runner.py` `load_atm_iv` reader + Kelly-lot writer; `merdian_utils.compute_kelly_lots` (consumer). |
| **Symptom** | `compute_volatility_metrics_local.py` writes `atm_iv_avg` as decimal fraction (e.g., 0.149 for 14.9%). Live and replay `detect_ict_patterns_runner.py` reads `vol.get("atm_iv_avg")`, formats as `f"{iv:.1f}%"` rendering 0.149 as "0.1%" in the log line, AND passes 0.149 to `compute_kelly_lots(_, _, _, current_spot, atm_iv_pct, dte_days)`. The parameter name `atm_iv_pct` suggests percent expected but receives decimal. |
| **Root cause** | Unit drift between writer (decimal) and consumer (parameter named `_pct` suggests percent). Has been latent across both production paths since at least Session 13 ENH-37 wiring. Replay made it visible because the detector log printed under operator inspection. |
| **Workaround** | None operationally — Kelly outputs lot counts that look reasonable (T1:112, T2:90, T3:45 for INR 25,000 capital) so end-state is not obviously broken. May or may not be silently mis-sizing depending on Kelly's IV-elasticity term. |
| **Proper fix** | Inspect `compute_kelly_lots` signature + IV-elasticity math. Decide which unit is canonical (decimal or percent). Fix writer or consumer to align. Then audit every other consumer of `atm_iv_avg` (signal builder reads it for HIGH_IV gate; gamma metrics; etc.) for the same drift. Likely 1-2 hour investigation + small patch. |
| **Cost to fix** | ~1 session (find canonical, audit consumers, patch). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-09 |

---

### TD-094 — `hist_option_bars_1m.oi=0` across all rows from S22 Kite backfill (Kite `historical_data` API does not return OI for index option minute bars) — RECLASSIFIED STALE Session 29

| | |
|---|---|
| **Session 29 status — RECLASSIFIED STALE (2026-05-16)** | **Verified empirically that the source-data limitation described below NO LONGER APPLIES.** Vendor-purchased historical data has replaced the S22 Kite backfill in `hist_option_bars_1m`. S29 query (`SELECT date_trunc('month', bar_ts) AS m, COUNT(*), AVG(oi)::int AS avg_oi, MAX(oi) FROM hist_option_bars_1m GROUP BY m ORDER BY m`) returns OI populated 99.9% across all 12 months Apr 2025 → Mar 2026: avg ~1M, max 66M per row. The replay reconstructor's live-OI-lift compensation (`_fetch_live_oi_for_replay`) remains correct architecturally but is no longer needed for OI specifically — historical OI is now in `hist_option_bars_1m` directly. **TD-094 is reclassified as stale documentation, not an active code defect.** When the original S22 backfill was replaced with vendor data is unknown (no commit marker in scope); finding the replacement boundary is not blocking but worth documenting. **Operational discipline lesson:** when a TD claims a data limitation, verify against current table state before designing around the limitation. Codified into CLAUDE.md S29 operational findings. **Unblocks Phase 0b dimensions** that were gated on gamma-context: P1 LONG_GAMMA, P3 flip_distance, P5 PINNED proxy (initial S29 P5 run was constrained by gamma_metrics sparsity — backfill `backfill_gamma_metrics_to_main.py` running at S29 close to produce full-cohort gamma_metrics for re-run). Also unblocks ENH-80 per-strike GEX work. **Action:** retain entry in tech_debt for audit history; mark RECLASSIFIED-STALE in footer; do not re-open as active. |
| **Severity** | S2 (would have permanently broken ENH-93 replay reconstructor without the live-OI-lift compensation; affects any future research / replay that needs OI from `hist_option_bars_1m`). |
| **Discovered** | 2026-05-09 (Session 24 — diagnosed during ENH-93 Phase 2 reconstructor build when `replay_compute_gamma_metrics` returned `DATA_ERROR all option rows filtered out as unusable` for run_id from reconstructed chain). |
| **Component** | `hist_option_bars_1m` Supabase table; data was written by S22 Kite backfill (`backfill_option_zerodha_OI_FIXED.py`); root cause is Kite Connect `historical_data` API behavior, not the backfill script. |
| **Symptom** | Direct query: `SELECT COUNT(*), MIN(oi), MAX(oi) FROM hist_option_bars_1m WHERE trade_date='2026-05-07'` returns ~8,250 rows for NIFTY with oi MIN=0 MAX=0. Volume populates correctly (e.g., 114,790 / 942,240 / 1,945,645 — full session traded volumes). Downstream consequence: replay reconstructor wrote chain rows with oi=0; `compute_gamma_metrics` filter `gamma!=0 AND oi>0` drops every row; gamma computation fails entirely. |
| **Root cause** | Kite Connect `historical_data` REST endpoint returns OHLC + Volume for index option minute bars but does NOT include open interest. OI is only available via real-time WebSocket OI ticks (KiteTicker `oi` field at run-time) or `quote()` REST calls (snapshot per-strike, run-time only — not historical). The S22 backfill assumed implicitly that historical_data returned OI; it does not. The defect was undetected because S22 backfill was followed immediately by ENH-93 work which initially planned to use only volume from hist_option_bars_1m. |
| **Workaround** | Permanent compensation in `replay_chain_reconstructor.py` `_fetch_live_oi_for_replay`: lifts OI from live `option_chain_snapshots` per (boundary, strike, option_type) tuple within ±150s tolerance window of each replay 5-min boundary. Live OI for past dates is immutable; this is a permitted READ from live per ADR-008. Tested on 2026-05-07: NIFTY 35,668 live rows → 35,668 entries across 74/76 boundaries; SENSEX 31,820 live rows → 30,100 entries across 70/76 boundaries (6 SENSEX boundaries in 2026-05-07 OI-gap windows have no live data to lift, producing oi=0 in those replay rows; cascades to gamma/volatility/options_flow failures at those boundaries). |
| **Proper fix** | Three options: (a) Re-backfill OI via Zerodha `quote()` per strike — many calls but accurate, requires per-day per-strike snapshot capture; (b) Drop `hist_option_bars_1m.oi NOT NULL` constraint, write NULL when unavailable, change downstream filters from `oi > 0` to `oi IS NULL OR oi > 0` — preserves backfill semantics but loses signal on actual zero-OI strikes; (c) Skip `hist_option_bars_1m` entirely for OI in research/replay; always lift from live `option_chain_snapshots` (current replay strategy) — works for any date where live captured the chain, fails for dates where live ingest was completely down. Recommend (a) for proper fix when research needs OI from past dates beyond what live captured. |
| **Cost to fix** | (a) ~2 sessions (per-strike `quote()` snapshot capture script + backfill of historical date range). (b) <1 session (DDL + filter audit). (c) Already in place via reconstructor. |
| **Blocked by** | Decision: which historical date ranges need OI? If only ENH-93 replay use case, (c) suffices. If broader research (e.g., regime studies on 2024-2025 historical data), (a) or (b) needed. |
| **Owner check-in** | 2026-05-09 |

---

### TD-087 — `hist_option_bars_1m.bar_ts` IST-as-UTC defect (5h30m phantom offset; only on option bars, not spot bars)

| | |
|---|---|
| **Severity** | S2 (silently mis-aligns option bars by 5h30m if read naively; replay reconstructor compensates but every other consumer needs awareness). |
| **Discovered** | 2026-05-09 (Session 24 — diagnosed during ENH-93 Phase 2 reconstructor build when boundary lookups returned no option bars at canonical UTC boundaries despite 8,250 rows present). |
| **Component** | `hist_option_bars_1m` Supabase table `bar_ts` column; introduced by some S22 backfill or upstream historical-data ingest path (specific root commit not identified). `hist_spot_bars_1m.bar_ts` is correctly stored UTC; the defect is option-bars-only. |
| **Symptom** | A bar that represents the 09:15 IST minute (= 03:45 UTC) is stored as `'2026-05-07 09:15:00+00'` instead of `'2026-05-07 03:45:00+00'`. The clock value is IST but the timezone tag is UTC, so `datetime.fromisoformat()` yields a datetime that is 5h30m AHEAD of the true UTC instant. Downstream code that does direct UTC-boundary lookup (`bars_by_ts.get(boundary_utc, [])`) finds nothing. |
| **Root cause** | Either upstream Kite-historical-data response timestamps are in IST and the ingest path tagged them `+00:00` without conversion, OR a `.replace(tzinfo=...)` instead of `.astimezone(...)` was used somewhere in the backfill chain. Closely related to TD-084 (S22 same-session resolution: `backfill_option_zerodha_OI_FIXED.py` had `.replace(tzinfo=ZoneInfo('UTC')).astimezone(IST)` which mis-shifted timestamps) — TD-087 is the residual defect where the timestamps in the table never got corrected. |
| **Workaround** | Permanent compensation in `replay_chain_reconstructor.py` `_fetch_hist_option_bars`: subtracts `timedelta(hours=5, minutes=30)` from each parsed `bar_ts` before storing as `bar_ts_dt`. Documented in code comment: "DO NOT apply this adjustment to hist_spot_bars_1m — that table stores correct UTC." |
| **Proper fix** | Two options: (a) Backfill correction — `UPDATE hist_option_bars_1m SET bar_ts = bar_ts - INTERVAL '5 hours 30 minutes'` after verifying every row is affected (must be all-or-none; mixed rows would corrupt the fix). (b) Schema decision: rename column to `bar_ts_ist_as_utc` to make the convention explicit, document, and adjust every consumer. Option (a) preferred — single DDL run, all consumers get correct UTC. |
| **Cost to fix** | (a) ~30min for the UPDATE + verification queries; ~1 session if the audit reveals mixed rows requiring per-row inspection. |
| **Blocked by** | Verification that all hist_option_bars_1m rows uniformly have the defect (no mixed-correctness). |
| **Owner check-in** | 2026-05-09 |

---

### TD-084 — `backfill_option_zerodha_OI_FIXED.py` UTC/IST timezone bug truncated Kite output to 46 bars per strike (RESOLVED same session)

> **Status: RESOLVED** Session 22 (2026-05-07) — see Resolved (audit trail) below for closure details. Listed here briefly to reflect the discovery of a pattern: any code that does `.replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)` to a Kite-returned `historical_data` datetime is wrong (Kite returns IST-tagged datetimes natively).

---

### TD-083 — ExecutionLog rejects `OUTSIDE_MARKET_HOURS` exit_reason from capture_spot_1m_v2 (RESOLVED Session 29 via TD-NEW-J)

**RESOLVED Session 29 (2026-05-14) — same root cause as TD-NEW-J, unified closure.** See TD-NEW-J entry above + Resolved (audit trail) section below. Fix routed via code-side rename rather than enum migration: `'OUTSIDE_MARKET_HOURS'` → `'OFF_HOURS'` at `capture_spot_1m_v2.py` call-site L346 + docstring L36 (`patch_s29_td_new_i_j_v2.py`). The `'NO_DATA'` exit_reason mentioned in original filing was a sibling case not exercised in production this session — recommend separate audit if it ever fires.

---

### TD-082 — `ingest_option_chain_local.py` contract miscalibration: backfill spike of 482 writes vs expected 50 logged as success (write-contract too permissive)

| | |
|---|---|
| **Severity** | S3 (degrades audit signal but doesn't break the pipeline; backfill-style spikes blur the line between "real run wrote 50 rows successfully" and "10x burst-write somehow" — both green) |
| **Discovered** | 2026-05-07 (Session 22 — surfaced during ingest_option_chain failure pattern audit; one row in `script_execution_log` showed 482 actual_writes for `option_chain_snapshots` where typical run writes ~50) |
| **Component** | `ingest_option_chain_local.py::_write_exec_log()` and the `contract_met` predicate |
| **Symptom** | One run on 2026-05-07 logged 482 rows written to option_chain_snapshots, compared to typical 50 per run. `contract_met=true` because predicate is `actual_writes >= 1`. The 482-row write was likely a multi-cycle accumulation from a partially-stuck process or coalesced retry, not a single intended cycle. |
| **Root cause hypothesis** | Either (a) script had a stuck cycle that buffered N cycles' worth of writes, or (b) write-batching accumulated mid-outage and flushed at recovery. Not yet diagnosed. |
| **Workaround** | None. Audit treats >300-row writes as anomaly worth investigating but doesn't fail the contract. |
| **Proper fix** | Tighten contract: `contract_met = (actual_writes >= 30 and actual_writes <= 100)` for option_chain_snapshots — outside that band is contract violation regardless of direction (zero rows = bad ingest, 500 rows = stuck or stale buffer). |
| **Cost to fix** | ~3 exchanges (read script, identify write path, tighten predicate, verify on backfill day). |
| **Blocked by** | TD-080 (Dhan outage diagnosis — same script, same module). |
| **Owner check-in** | 2026-05-07 |

---

### TD-081 — No data-freshness guard between primary ingestion and derived layers — signal builder produces signals on stale data without warning

| | |
|---|---|
| **Severity** | S2 HIGH (architectural — when primary ingestion is partially failing as Session 22, the derived signal layer continues to produce output based on last-good snapshot, which can be 30-60 minutes stale; signals get fired into Telegram with no staleness flag) |
| **Discovered** | 2026-05-07 (Session 22 — observed during Dhan outage; while ingest_option_chain failed 50% of cycles, build_trade_signal_local.py continued producing signal_snapshots rows; downstream consumers had no way to know the option_chain underlying signals was stale) |
| **Component** | `build_trade_signal_local.py`, `compute_gamma_metrics_local.py`, `compute_volatility_metrics_local.py`, etc. — the derived chain. Architectural defect spans the pipeline. |
| **Symptom** | When Dhan ingest fails for 30+ minutes, derived layer still emits signals using the last successful option_chain_snapshots row as if it were current. Signal confidence/direction gets computed against stale data. |
| **Root cause** | No upstream-freshness check before derived computation. Each derived script reads the latest row of its source table; if the source table hasn't received a fresh row, the derived script proceeds anyway. |
| **Workaround** | None operationally. Operator trusts pipeline + ad-hoc inspects script_execution_log when alerts surface. |
| **Proper fix** | Each derived script must check `option_chain_snapshots.created_at` (or upstream equivalent) and reject if older than max-staleness threshold (e.g., 10 min for 5-min cycle). Reject = exit with SKIPPED_STALE_SOURCE; don't write a signal. Telegram alert escalates if N consecutive cycles skip. Pattern: ENH-71 instrumentation layer extended with a "freshness gate" predicate. |
| **Cost to fix** | ~2 sessions (design + implement across 6 scripts + test). Likely should be filed as ENH-93 not just TD. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-07 |

---

### TD-080 — AWS Dhan token refresh failure mode (cross-script Dhan 401 outage on 2026-05-07; reframed Session 25; PROMOTED to S1 RECURRING Session 29)

| | |
|---|---|
| **Session 29 status update — PROMOTED to S1 RECURRING (2026-05-14)** | **Third documented occurrence (S22 2026-05-07 151/299; S28 2026-05-13 alluded; S29 2026-05-14 99/808 = 12.3% failure rate over 4h19m).** Same token, same `/v2/optionchain` endpoint, same alternating-window symptom shape. Per-token rate-limit instability hypothesis (S22) now corroborated across 3 sessions. **Priority elevated from S2 HIGH to S1 RECURRING.** **ENH spec for rate-limit-aware retry layer + circuit breaker in `ingest_option_chain_local.py` is P0 carry-forward to S30.** Likely fix track: (a) exponential backoff with per-token quota tracking; (b) circuit breaker pause after 429 to avoid escalating to threatened "user being blocked"; (c) dedicated runbook for Dhan 429 storm response. See `CASE-2026-05-14-spot-gap-backfill.md` §5 for full S29 occurrence analysis. Pre-S29 instrumentation (S26 probe-log) is still relevant input but is now upstream of a confirmed production-blocking failure class, not just a diagnostic curiosity. |
| **Severity** | S2 HIGH (loses ~70% of trading day's option chain ingest; permanent loss of full chain greeks/IV smile/OI per strike for outage windows; option_chain_snapshots gap of 64 5-min windows on 2026-05-07) |
| **Discovered** | 2026-05-07 (Session 22 — incident from 09:30 IST onwards, 151 of 299 attempts failed with `401 Authentication Failed - Client ID or Token invalid`). **Reframed S25 2026-05-10:** investigation surface narrowed from "Dhan option chain endpoint reliability" to "AWS Dhan token refresh failure mode" based on cross-script 401 evidence on 2026-05-07. |
| **Component** | `refresh_dhan_token.py` running on AWS at 03:05 UTC (08:35 IST) — single source for AWS-side Dhan tokens consumed by `ingest_option_chain_local.py` AND PreOpen 03:38 UTC (`capture_postmarket_1600.py` not affected). Cross-script 401s on 2026-05-07 (PreOpen 03:38 UTC + option chain 09:30-13:30 IST + 14:45-15:25 IST) point to single token-refresh failure on AWS, not a Dhan-side service incident. |
| **Symptom** | Alternating 50/50 success/fail pattern across full trading day on 2026-05-07; hourly-stable. Two outage windows: 09:30-13:30 IST (~4hrs) + 14:45-15:25 IST (40min). Manual token refresh at 13:30 IST temporarily restored, broke again ~14:45. Same token served `/charts/intraday` (capture_spot_1m_v2) at 97% throughout — endpoint-specific behavior consistent with token being valid for some endpoint paths and not others, which is itself evidence of token-refresh-mode partial success rather than Dhan-side endpoint-specific block. |
| **Root cause** | **UNCONFIRMED but narrowed.** Working hypothesis (S25): `refresh_dhan_token.py` on AWS occasionally produces a token that is partially valid (works for `/charts/intraday`, fails for `/optionchain` or similar) — possibly due to a token-scope or session-binding issue at refresh time. Six hypotheses from S22 remain refuted (token sync silent failure, TD-072 battery side-effect, AWS competing writer, MeridianAlpha competition, stale-token daemon, shadow_runner in-memory stale token). New focus: the refresh script's actual API call sequence and what the freshly-issued token's effective scope is. |
| **Workaround** | Local-side Dhan ingestion via Kite/MeridianAlpha backfill remains operational redundancy until AWS reliability established. Validated end-to-end Session 22 (24,749 rows for 2026-05-07). |
| **Proper fix** | Dedicated investigation session: (a) instrument `refresh_dhan_token.py` with full-response logging; (b) compare freshly-issued token's response on `/charts/intraday` vs `/optionchain` immediately post-refresh; (c) reproduce on a controlled day; (d) once root cause is identified, harden refresh script and observe N clean trading days before declaring TD-080 closed. |
| **Cost to fix** | 1 dedicated investigation session for root-cause + 1 session for hardening + N trading days observation. |
| **Blocked by** | Nothing — investigation session is the next logical work item. |
| **Blocks** | **ADR-006 drafting (Phase α Q3 sequencing — token reliability FIRST, ADR-006 actions second).** Local Capture writers (16:00 post-market dual-write disposal, 09:08 PreOpen disposal) cannot execute until AWS Dhan-token-dependent reliability is established across N clean trading days. |
| **Owner check-in** | 2026-05-10 (S26 instrumentation deployed — see below). Next investigation: post-Mon-2026-05-12 probe-log triage; dedicated root-cause session if probe-log evidence supports a hypothesis. |
| **Session 26 status update (instrumentation)** | **DEPLOYED** Session 26 commit `718ef39` — root-cause investigation pending Mon 2026-05-12 first probe-log triage (P0b S27). New Supabase table `dhan_token_probe_log` (12 columns) + view `v_dhan_token_probe_today`. `pull_token_from_supabase.py` extended 50 → 355 lines: atomic .env write with readback verify; post-write probes of Dhan `/v2/marketfeed/ltp` + `/v2/optionchain/expirylist` immediately after .env write; audit logging to probe-log table; asymmetry verdict logic (both 200 → OK; one 200 + one 4xx → PARTIAL with endpoint flag; both fail → FAIL token-side problem). Sunday 2026-05-10 smoke test PASS at 20:28 IST: token len=280, both probes 200 OK, verdict=OK. AWS cron `5 3 * * 1-5 /usr/bin/python3 pull_token_from_supabase.py` continues to fire 03:05 UTC = 08:35 IST as before; no scheduler change. **Mon 2026-05-12 verification SQL** (Topology §9.B documented): `SELECT * FROM v_dhan_token_probe_today ORDER BY ts_ist DESC LIMIT 10;` Decision tree: both 200 → token side healthy if option-chain still fails 09:15 IST then endpoint-side investigation; partial → JWT scope / endpoint-specific auth; both fail → upstream TOTP / login flow on Local 08:15. Backup `pull_token_from_supabase_PRE_S26.py` preserved. **Status remains UNRESOLVED** until probe-log evidence supports a root-cause hypothesis; instrumentation is the input to investigation, not the closure. |

---

### TD-079 — Zone date-expiry vs ICT canon (RESOLVED Session 26 via ADR-005 implementation)

**RESOLVED Session 26 (2026-05-10).** Full closure block is in the **Resolved (audit trail)** section below. Patch script `patch_s26_td079_zone_validity.py` applied 13 surgical replacements AST-validated implementing Phase α Q1 answer (S25 architecture conversation): D/W OB/FVG `valid_to=None` price-breach-only canonical; 1H OB/FVG `valid_to=str(trade_date+timedelta(days=7))` tactical fallback; `expire_old_zones()` filter widened `["W","D"]` → `["W","D","H"]`; PDH/PDL date-expiry unchanged. Backfill SQL revived 18 SENSEX W BEAR_OB/BEAR_FVG zones above 78k from EXPIRED → ACTIVE valid_to=NULL. Live rebuild produced 80 zones; Pine overlay 36 → 62 zones (49 HTF + 13 intraday). Commit `0731e67`. ADR-005 formal draft (P2 S27 carry-forward) follows the implementation per CLAUDE.md S26 lesson: architecture-defect TDs implementable before formal ADR when Phase α answer in hand and decision recorded in Decision Index + Assumption Register §D.7.

---

### TD-078 — TD-070 closure verification incomplete — empirically multi-week BULL_OB lookback may not be firing as designed

**RESOLVED Session 25 (2026-05-10).** Full closure block is in the **Resolved (audit trail)** section below. SQL verification confirmed TD-070 v2 multi-week unbreached-anchor lookback fires as designed; the apparent absence of an Apr-13 BULL_OB row was a schema-convention misunderstanding, not a missed detection.

---

### TD-077 — Wide FVG zones during volatile weeks lack outlier filter

| | |
|---|---|
| **Severity** | S4 LOW (cosmetic + signal-quality edge case — during high-volatility weeks FVG zones can span 800-1500 points which dominate the Pine overlay and reduce visual clarity) |
| **Discovered** | 2026-05-06 (Session 21 — observed during HTF zone rebuild; one BEAR_FVG on NIFTY spans 1,200 points) |
| **Component** | `build_ict_htf_zones.py` FVG detection (no outlier filter on zone_high - zone_low spread) |
| **Symptom** | Volatile weeks produce FVG zones with high-low spread of 800-1500 points (compared to typical 100-300). These dominate Pine overlay, can mask narrower more-actionable zones, and produce overly-large stop levels if zone is used for execution. |
| **Root cause** | Detection includes any 3-bar imbalance regardless of size. No upper bound on zone spread. |
| **Workaround** | Operator visually filters wide zones during analysis. Pine `show_h` toggle helps. Not blocking. |
| **Proper fix** | Add `MAX_ZONE_SPREAD_PCT` parameter (e.g., 1.5% of underlying for W) and reject FVG candidates wider than that. Verify on Session 21's wide-zone case. |
| **Cost to fix** | ~2 exchanges. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-07 |

---

### TD-076 — SENSEX DTE gate persistent block on weekly expiry

| | |
|---|---|
| **Severity** | S4 LOW (operator-tier visibility issue; the DTE gate skips signals on SENSEX expiry day every Thursday which is a high-edge expiry-gamma window) |
| **Discovered** | 2026-05-06 (Session 21 — observed signal_snapshots for SENSEX Thursday expiry day showing all DTE=0 SKIPPED) |
| **Component** | `build_trade_signal_local.py` DTE gate logic (`signal_snapshots.dte_gate_blocked`) |
| **Symptom** | Every SENSEX Thursday expiry day shows all signals SKIPPED with reason `DTE=0`. SENSEX expiry-gamma is one of the higher-edge windows historically (Exp 9 SMDM analysis). Gate is over-conservative. |
| **Root cause** | DTE gate built around NIFTY's previous Thursday-expiry pattern when NIFTY was Thursday-weekly. With NIFTY moved to Tuesday and SENSEX still Thursday, the gate doesn't account for SENSEX-specific edge on its own expiry. |
| **Workaround** | Operator manually overrides on SENSEX expiry days. |
| **Proper fix** | Per-symbol DTE gate: NIFTY Tuesday allows DTE=0 with attenuation; SENSEX Thursday allows DTE=0 with full sizing (or ENH-77-style time-band routing for expiry-gamma window). |
| **Cost to fix** | ~1 session. |
| **Blocked by** | TD-074 (related ENH-77 routing review). |
| **Owner check-in** | 2026-05-07 |

---

### TD-075 — Confidence threshold 60 vs observed max 45 (gate never reached)

| | |
|---|---|
| **Severity** | S3 MED (production gate set to 60 but live signals top out at confidence 45; gate is effectively dead code — never trips, never blocks anything; likely should be lowered to 40-45 or made dynamic) |
| **Discovered** | 2026-05-06 (Session 21 — confidence histogram across signal_snapshots showed max=45, gate at 60 never reached) |
| **Component** | `build_trade_signal_local.py` confidence threshold for trade_allowed gating |
| **Symptom** | trade_allowed always FALSE due to confidence < 60 threshold; no signals ever pass to execution layer. Effective trading gate is purely operator-discretionary at this point. |
| **Root cause** | Threshold derived from a different signal-generation regime (pre-ENH-35? pre-V4?). Hasn't been recalibrated since then. |
| **Workaround** | Operator-discretionary execution. Trade_allowed gate ignored. |
| **Proper fix** | Recalibrate threshold based on observed distribution: median, p75, p90 across last 30 days. Or make threshold dynamic by regime (LONG_GAMMA vs SHORT_GAMMA different). |
| **Cost to fix** | ~1 session — distributional analysis + threshold revision + 2-week shadow validation per Master V15 18.1 rule. |
| **Blocked by** | signal_regret_log accumulation (Master V15 says 30+ sessions before threshold change). |
| **Owner check-in** | 2026-05-07 |

---

### TD-074 — ENH-77 BULL_OB AFTERNOON NIFTY hard skip blocked the only TIER1 signal

| | |
|---|---|
| **Severity** | S3 MED (over-aggressive routing rule — ENH-77 hard-skips BULL_OB+AFTERNOON+NIFTY; 2026-05-06 had a 700pt rally for which the only TIER1 BULL_OB signal was hard-skipped, costing capture) |
| **Discovered** | 2026-05-06 (Session 21 — post-mortem on missed TIER1 signal on 700pt rally afternoon) |
| **Component** | `build_trade_signal_local.py` — ENH-77 time-of-day routing for BULL_OB |
| **Symptom** | BULL_OB signals in AFTERNOON time band (12:00-15:00 IST) on NIFTY are hard-routed to SKIP. The 2026-05-06 rally had a TIER1 BULL_OB at ~13:00 that should have triggered; was skipped per ENH-77 rule. |
| **Root cause** | ENH-77 rule was derived from cohort analysis showing AFTERNOON BULL_OB underperforms; but the rule is hard-skip not attenuation, eliminating the long tail of high-edge AFTERNOON cases. Direction-asymmetric defect: BEAR_OB+AFTERNOON not hard-skipped, only BULL_OB. |
| **Workaround** | Operator-discretionary execution overrides. |
| **Proper fix** | Replace hard-skip with attenuation (size_mult 0.5x instead of 0x) OR rebuild ENH-77 with finer time bands (12:00-13:30 vs 13:30-15:00 may be different cohorts). |
| **Cost to fix** | ~1 session — ENH-77 cohort review + rule revision + 2-week shadow validation. |
| **Blocked by** | signal_regret_log accumulation (same as TD-075). |
| **Owner check-in** | 2026-05-07 |

---

### TD-073 — Momentum direction lagged 700pt rally May 6 by ~60 min

| | |
|---|---|
| **Severity** | S2 HIGH (signal-quality defect — momentum_direction component of build_trade_signal lagged the 2026-05-06 700pt rally by ~60 min; signal stayed BEARISH/NEUTRAL while spot was already in clear bullish expansion; downstream signal direction wrong throughout the lag window) |
| **Discovered** | 2026-05-06 (Session 21 — observed during live trading on rally day) |
| **Component** | `build_momentum_features_local.py` — `momentum_direction` derivation; possibly `ret_session` or `vwap_slope` lag |
| **Symptom** | Spot rallied from 24,200 to 24,900 over ~13:00-14:30 IST window. `momentum_snapshots.momentum_direction` stayed `BEARISH` until ~14:00 then flipped `NEUTRAL` then finally `BULLISH` at ~14:30 — by which point most of the move was over. Lag of ~60 min vs price action. |
| **Root cause hypothesis** | `ret_session` uses session_open as reference; if session opened weak and rallied, ret_session takes time to flip sign. `vwap_slope` is a lagging indicator by construction. Multi-vote system (5 momentum components) may have 3 lagging components dragging the vote. |
| **Workaround** | Operator-discretionary direction override during live trading (but then signal confidence is also wrong). |
| **Proper fix** | Diagnose which of the 5 momentum components is laggiest; consider replacing with a faster-responding indicator (e.g., 5m return + 15m return weighted majority) OR add a "fast momentum override" when 5m return exceeds 0.5%. |
| **Cost to fix** | ~1.5 sessions — instrument each component + correlate with price; design replacement; shadow-test. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-07 |

---


### TD-069 — D timeframe doesn't generate OB/FVG even with real data (W and 1H do)

| | |
|---|---|
| **Severity** | S2 (architectural — daily timeframe contributes 0 directional zones; only PDH/PDL liquidity levels; loses one timeframe of context for ICT MTF context computation) |
| **Discovered** | 2026-05-05 (Session 20 — HTF zone rebuild after spot data backfill produced 33 W OB/FVG NIFTY + 35 SENSEX with real OHLC, but D timeframe produced 0 OB/FVG for both symbols — only PDH/PDL) |
| **Component** | `build_ict_htf_zones.py::detect_daily_zones()` |
| **Symptom** | After spot data backfill produced clean real OHLC for Apr 1 → May 5, weekly detector fired 33+35 OB/FVG zones across full year (correctly distinguishing real candle direction). Daily detector fired 0 OB/FVG despite operating on the same underlying data — only generating PDH/PDL. Direct example: May 4 NIFTY (+0.49% close-vs-open ≥ 0.40% threshold) should fire D-OB but didn't. |
| **Root cause** | Unknown — code review needed. Possible candidates: (a) D detector uses different threshold than W (perhaps stricter `OB_MIN_MOVE_PCT`); (b) D detector requires 3+ trading days for FVG (`prior_dates[-3]`) but only-prior-day for OB — interaction with date logic may have a bug; (c) `target_date` computed differently than W; (d) D detector reads from different source (`daily_ohlcv` aggregated from minute bars) where aggregation may drop OHLC variation. |
| **Workaround** | None — system functions, just loses D-timeframe MTF context. W and 1H zones provide sufficient ICT context for current detection. |
| **Proper fix** | Code review of `detect_daily_zones()` vs `detect_weekly_zones()`. Identify divergence. Likely 1-line or threshold change. |
| **Cost to fix** | ~6 exchanges (read code, identify cause, patch, verify) |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-05 |

---

### TD-068 — `capture_spot_1m.py` writes synthetic O=H=L=C=spot bars to `hist_spot_bars_1m` (RESOLVED same session via v2.1 deployment)

| | |
|---|---|
| **Severity** | S1 (production-impacting — entire BULL_OB / BEAR_OB pattern detection blind to live data because all candles are flat O=H=L=C from synthetic bar; OB detection requires candle direction) |
| **Discovered** | 2026-05-05 (Session 20 — surfaced via Session 19 audit script (broken at time of discovery, fixed in same session) flagging BULL_OB/BEAR_OB zero-emission in `ict_zones`; locked diagnosis after triple-verification: source code reads `O=H=L=C=spot` literally per docstring; today's bars sampled = 376/376 flat; `script_execution_log` confirmed `capture_spot_1m.py` is sole writer to `hist_spot_bars_1m` with 3,897 runs in 30 days) |
| **Component** | `capture_spot_1m.py` synthetic bar writer (lines 165-178: `bar_rows.append({"open": spot, "high": spot, "low": spot, "close": spot, ...})`) |
| **Symptom** | Despite running every minute during market hours and writing to both `market_spot_snapshots` (live spot dashboard) and `hist_spot_bars_1m` (ICT detector input), the bars table contained only synthetic flat candles. ICT detection requires candle direction (`open vs close`); cannot fire on flat bars. Result: 7+ days of zero BULL_OB / BEAR_OB emission in `ict_zones`. |
| **Root cause** | Original `capture_spot_1m.py` design treats `hist_spot_bars_1m` as snapshot table not OHLC table — uses `/v2/marketfeed/ltp` endpoint which returns single price; writes that as O=H=L=C to satisfy schema. Likely unintended consequence of dual-purpose script (spot snapshot + bar writer) where original requirement was just spot capture. OB detection added later assumed real OHLC; never noticed flat bars because BULL_FVG / BEAR_FVG can fire on consecutive close prices alone. |
| **Workaround** | None — went straight to fix. |
| **Proper fix** | `capture_spot_1m_v2.py` (475 lines, v2.1) shipped Session 20: drop-in replacement using `/v2/charts/intraday` endpoint which returns full 1-min OHLC arrays. v2.1 features: market-hours guard (skip outside 09:15-15:30 IST), filler-bar skip (V=0+flat detection prevents post-market filler writes). Same .env vars, same instrumentation, same heartbeat wrapper. Task Scheduler `MERDIAN_Spot_1M` action repointed to v2 with full `pythonw.exe` path. v1 untouched at `capture_spot_1m.py` for rollback. **Backfill of pre-Session-20 historical data:** 16,500 rows for Apr 1 → May 5 backfilled real OHLC via Kite `historical_data` (16 stray 15:30 boundary flats deleted post-backfill). HTF zone rebuild on backfilled data confirmed all 4 ICT pattern types now fire. |
| **Cost to fix** | ~25 exchanges including diagnostic oscillation, backfill, v2 design + write + deploy. Closed same session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-05 — RESOLVED via v2.1 deployment. **Verification deferred to next live cycle** 2026-05-06 09:16:02 IST: query `script_execution_log` for capture_spot_1m_v2 invocations + `hist_spot_bars_1m` for is_flat=false on today's bars. |

---

### TD-067 — Intraday backfill detector for Apr 1 → today historical pattern record

| | |
|---|---|
| **Severity** | S2 (research enablement — system functions live, but historical intraday pattern record for Apr 1 → May 5 missing because pre-TD-068 data was synthetic flats; once backfilled real OHLC exists, detection should be replayed to populate `ict_zones` for those days) |
| **Discovered** | 2026-05-05 (Session 20 — after spot data backfill produced clean real OHLC for Apr 1 → May 5, recognized that runner-based intraday detection only runs forward-going on today's bars; days before today have no `ict_zones` records on real OHLC) |
| **Component** | New script needed: `backfill_ict_zones.py` that walks each day's `hist_spot_bars_1m` and runs `ICTDetector` on each session's bars |
| **Symptom** | `ict_zones` table has no historical records for Apr 1 → May 5 patterns detected on real OHLC. Research/replay queries against this table see zero or mostly-empty data for that range. Live runner only fills today's slot going forward. |
| **Workaround** | None needed for production (live detection works on today). For research replay, run `experiment_15_pure_ict_compounding.py` which simulates detection per session (different code path, different output format). |
| **Proper fix** | Build `backfill_ict_zones.py`: load `hist_spot_bars_1m` for date range, group by symbol+trade_date, instantiate `ICTDetector`, walk bars, write to `ict_zones` with same schema as live runner. Verify against today's real-time output. ~30 min build + run for Apr 1 → May 5 (22 trading days × 2 symbols). |
| **Cost to fix** | ~10 exchanges (build + verify + run) |
| **Blocked by** | TD-068 RESOLVED (real OHLC exists for Apr 1 → May 5 now) |
| **Owner check-in** | 2026-05-05 |

---

### TD-060 — Live runner emits zero OBs across 14 days due to detect_ict_patterns check_from filter / runner cycle stride mismatch (RESOLVED same session)

| | |
|---|---|
| **Severity** | S1 (production-impacting — entire bear-side OB and most FVG signal flow blind to live system) |
| **Discovered** | 2026-05-03 (Session 17 — uncovered while attempting ENH-88 BULL_FVG cluster gate deploy; `signal_snapshots` last 14 days had only NONE and BULL_FVG, zero OBs of either direction; investigation revealed runner cycles 14 × ~2280 = ~32,000 invocations producing zero OB rows in `ict_zones`) |
| **Component** | `detect_ict_patterns_runner.py` invocation of `detector.detect()` AND `detect_ict_patterns.py` `check_from = max(0, len(bars) - 10)` filter |
| **Symptom** | Despite Session 17 TD-058 detector patch (BEAR_FVG branch added) and Session 15 zone-builder fix (1,384 W BEAR_FVG zones in `hist_ict_htf_zones`), the live `ict_zones` table had only 76 BULL_FVG rows and 0 OBs/BEAR_FVG/JUDAS over 14 trading days. Sub-detectors (`detect_obs`, `detect_fvg`) found 14 OBs + 13 FVGs on Feb 01 NIFTY when called directly; `ICTDetector.detect()` returned 0 patterns on the same data. |
| **Root cause** | Two-bug pair. (a) `detect_ict_patterns.py` had `check_from = max(0, len(bars) - 10)` filter that limited visible OB-candle slot to indices `[len-10, len-7]` — exactly 4 bars wide regardless of input size, because `detect_obs` caps `i in range(n - 6)`. (b) `detect_ict_patterns_runner.py` passed `bars=bars` (full session ~400 bars) every 5-min cycle. Combined: cycle stride=5 bars + eligible window=4 bars = systematic gap where most session OBs miss every cycle. Only OBs at session-idx N where some cycle ends at N+7..N+10 surfaced; those ending exactly on cycle boundaries (multiples-of-5+10) caught their target. End-of-day BULL_FVGs slipped through more often than mid-day BEAR_OBs, explaining the all-BULL_FVG production rows. |
| **Workaround** | None applied — went straight to fix. |
| **Proper fix** | F4 + G1 patch pair shipped as TD-060 fix: (F4) `detect_ict_patterns_runner.py` line `bars=bars` → `bars=bars[-30:]` so per-cycle scan window is bounded to last 30 bars. (G1) `detect_ict_patterns.py` `check_from` line + 3 `if idx >= check_from` filters from list comprehensions removed entirely. Per-cycle re-detection of older patterns is idempotent via `on_conflict` upsert in `write_new_zones()`. Verification: `diag_td060_full_day_smoke.py` simulated 80 5-min cycles on Feb 01 NIFTY, achieved 14/14 OB coverage = 100% within tradeable hours (versus 9/14 = 64% with F4 alone, 0/14 pre-fix). Both patches deployed Local + AWS via `git pull`; `_PRE_S17_TD060.py` snapshots preserved. |
| **Cost to fix** | ~6 exchanges of diagnostic + 2 patches + 3 hotfix iterations on related Pine work. Closed same session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-03 — RESOLVED |

---

### TD-061 — Task Scheduler entry points spawn visible console windows during pre-market and post-market hours (RESOLVED Session 29 — see Resolved section)

**SEE Active-section S29 entry above and Resolved (audit trail) closure block below.** Original Active body (S17 filing) preserved in commit history (`git show HEAD~N:tech_debt.md` to recover pre-S29 text).

---

### TD-062 — Saturday LastRun timestamps on 5 Task Scheduler tasks despite DoW=62 (Mon-Fri) trigger — stuck-process accumulation root cause unknown

| | |
|---|---|
| **Severity** | S2 (operational hygiene — stuck Python processes accumulate across days, eventually requiring kill, which disables tasks until manual re-enable; root cause hidden) |
| **Discovered** | 2026-05-03 (Session 17 — Get-ScheduledTask diagnostic showed Market_Close_Capture, Post_Market_1600_Capture, Session_Markers_1602, Spot_1M, EOD_Breadth_Refresh all had LastRun timestamps from 02-05-2026 (Saturday) despite all having `DoW=62` = Mon-Fri only triggers; LastResult 2147946720 = 0x80070420 = 'instance is currently running') |
| **Component** | Task Scheduler interaction with long-running Python processes; possibly Spot_1M or Supervisor entering hung state on holiday-day calendar queries |
| **Symptom** | Saturday LastRun timestamps decoded NOT as new Saturday triggers (DoW=62 correctly excludes Saturday) but as kill-time artifacts when operator killed the running instances. The LastResult code 2147946720 means a previous instance was still alive when the next scheduled fire attempted to start — Task Scheduler refused to start a duplicate, returned the error code, and recorded the time as LastRun. The accumulated processes were the same task's previous instance still running, NOT new Saturday firings. |
| **Root cause** | Unknown. Hypothesis: a script called by one of the affected tasks (likely Spot_1M which fires every minute, or the Supervisor which spawns child processes) hangs on a Supabase call, network call, or holiday-gate evaluation when calendar state is unusual (NULL open_time per Incident #1 class, or just slow-responding). Task instance never exits. Subsequent triggers fire, find existing instance, error out with 2147946720. Process count grows. |
| **Workaround** | Operator manually kills runaway processes when noticeable; killing disables the task in Windows Task Scheduler until manually re-enabled. Done May-3 this session for all 13 MERDIAN_* tasks. |
| **Proper fix** | Three steps: (1) Identify which script gets stuck — instrument every long-running task with a heartbeat write to `script_execution_log` (or local heartbeat file with rolling timestamp); compare actual LastRun vs heartbeat to find which task's instances outlive their schedule. (2) Add timeout to all Supabase calls in calendar-gate code paths (currently no timeout means a stuck connection hangs forever). (3) Add `subprocess.Popen(timeout=N)` or signal-based kill to supervisor child processes so a stuck Python script gets reaped after reasonable wall time. |
| **Cost to fix** | 1 session for instrumentation, 1 session for fix once root cause identified. |
| **Blocked by** | TD-061 (window-suppression fix may interact — pythonw.exe migration could change process lifecycle behavior; do TD-062 instrumentation first) |
| **Owner check-in** | 2026-05-03 |

---

### TD-063 — Single-instance enforcement missing on Task Scheduler tasks (RESOLVED Session 29 — see Resolved section)

**RESOLVED Session 29 (2026-05-14).** Full closure block in Resolved (audit trail) section below. **NOTE: Same body-state-vs-footer-claim divergence as TD-061** — footer-claimed-RESOLVED at S18; body remained Active. S29 applied: `MultipleInstances=IgnoreNew` setting now hardened on 18/19 MERDIAN_* tasks via `migrate_to_pythonw.ps1` v2 settings pass. 1 failure on `MERDIAN_Intraday_Supervisor_Start` documented as known limitation (multi-trigger XML quirk in PowerShell's `Set-ScheduledTask -Settings <obj>` — workaround: build full `Register-ScheduledTask` XML + `Force` overwrite). See Topology §7.2 final-state table.

---

---

### TD-001 — `pull_token_from_supabase.py` deployed but not in `merdian_reference.json` Block 3 inventory until v18D audit

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-04 (Appendix V18D_v2 audit fix M-01) |
| **Component** | `merdian_reference.json` files inventory |
| **Symptom** | File exists in production, listed in Block 9 failure modes, missing from Block 3 inventory |
| **Root cause** | Inventory update lag — file added in production before being added to JSON |
| **Workaround** | Audit caught it; corrected in V18D v2 |
| **Proper fix** | Pre-commit hook that diffs deployed `*.py` files against `merdian_reference.json` files keys |
| **Cost to fix** | 2 sessions |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-19 |

---

### TD-002 — `breadth_regime` NULL before 2025-07-16 in `hist_market_state`

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | Appendix V18F v2 Block 4 |
| **Component** | `public.hist_market_state` |
| **Symptom** | Any signal validation that filters by `breadth_regime` silently drops Apr–Jul 2025 sessions |
| **Root cause** | Breadth indicator backfill started 2025-07-16; earlier rows have NULL |
| **Workaround** | Validation queries explicitly mark coverage as `2025-07-16 onwards` and exclude earlier sessions |
| **Proper fix** | Backfill `breadth_regime` for Apr–Jul 2025 from raw `equity_eod` |
| **Cost to fix** | 1 session (similar to other backfill scripts) |
| **Blocked by** | nothing — can be done any time |
| **Owner check-in** | — |

---

### TD-003 — `experiment_15b` `detect_daily_zones` date type mismatch (now CLOSED — kept here as template example)

| | |
|---|---|
| **Severity** | ~~S2~~ → moved to Resolved |

*See "Resolved" section below for the closing entry. Keeping the template visible here so future tech debt items have an example to follow.*

---

### TD-004 — `BFO_CONTRACT_05062025.csv` permanent ingestion failure (malformed Date column header)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | Appendix V18D v2 (SENSEX F+O corrected ingest) |
| **Component** | SENSEX F+O daily ingestion pipeline |
| **Symptom** | One file fails ingestion every time it's encountered; logs flag it, pipeline continues |
| **Root cause** | Source CSV from exchange has a malformed header for that single date |
| **Workaround** | Skip-list the file in the ingestion runner; rebuild that date's gamma from adjacent days if needed |
| **Proper fix** | Manually clean and re-ingest the one file; update the source-file checksum |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | — |

---

### TD-005 — `option_execution_price_history` table marked DEPRECATED but not yet DROPPED

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | merdian_reference.json (E-06) |
| **Component** | `public.option_execution_price_history` |
| **Symptom** | Table exists in DB, takes up space, no writers, one stale reader pending migration |
| **Root cause** | `build_option_execution_outcomes_v1.py` migration pending |
| **Workaround** | Mark DEPRECATED in JSON, no new writes |
| **Proper fix** | Complete the outcome engine migration (E-06), then `DROP TABLE` |
| **Cost to fix** | 2 sessions |
| **Blocked by** | E-06 migration |
| **Owner check-in** | 2026-04-19 |

---

### TD-006 — `run_market_tape_1m.py` disabled due to DhanError 401 / Windows ACCESS_VIOLATION

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-07 (merdian_reference.json files entry) |
| **Component** | `run_market_tape_1m.py`, `MERDIAN_Market_Tape_1M` Task Scheduler task |
| **Symptom** | DhanError 401 every run, returncode=3221225786 (Windows ACCESS_VIOLATION), 390 extra Dhan calls/day |
| **Root cause** | Unknown — auth path through this runner differs from main runners |
| **Workaround** | Task disabled. Tape data not currently captured at 1m granularity. |
| **Proper fix** | Either rebuild against shared auth helper (preferred) or formally deprecate and remove |
| **Cost to fix** | 2–3 sessions |
| **Blocked by** | Decision: do we still want 1m market tape? If no → close as WONTFIX |
| **Owner check-in** | — |

---

### TD-007 — `is_pre_market` column in `hist_spot_bars_1m` is vestigial

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-22 (OI-18 investigation during Session 5 — see `session_log.md` 2026-04-22 entry) |
| **Component** | `public.hist_spot_bars_1m` column + all producers and consumers (20+ files) |
| **Symptom** | Column is always written `false` by every producer (`capture_spot_1m.py`, `backfill_spot_zerodha.py`, all backfill and MTF builders). Every consumer filters `.eq("is_pre_market", False)` — the filter drops zero rows because no producer ever writes `True`. Dead code path masquerading as a semantic filter. |
| **Root cause** | Column was added with intent to mark pre-open (09:00–09:14 IST) bars so they could be excluded from analytics. Writer-side implementation was never completed; consumers were written defensively with the filter assumption. Nobody noticed because the filter is functionally a no-op. |
| **Workaround** | None needed — column works, just adds no value. Pre-open bars ARE being captured and used in analytics today; the filter is decorative. |
| **Proper fix** | Two mutually exclusive paths:<br>  (a) Make the column honest — writer computes `is_pre_market = (IST time of bar_ts between 09:00:00 and 09:14:59)`. All consumers accept the new filter semantics. Requires one-time backfill to retag historical pre-open rows from `False` to `True`. Multi-file, ~20 consumer files to review.<br>  (b) Drop the column + drop all `.eq("is_pre_market", False)` filters from consumers. Schema-breaking but simpler. ~1 session. |
| **Cost to fix** | 2–3 sessions for (a), 1 session for (b) |
| **Blocked by** | Decision: is the pre-open exclusion semantics actually wanted, or is it a bug-shaped assumption that no one actually depends on? If wanted → (a). If not → (b). |
| **Owner check-in** | 2026-04-22 |

---

### TD-009 — `.bak` file debris in `docs/registers/`

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-22 (V19A Block 11.4) |
| **Component** | `docs/registers/` directory |
| **Symptom** | Six intermediate `.bak` files left over from the 2026-04-19/20 register unification work: `MERDIAN_Enhancement_Register_v7.md.bak` (35 KB), `_v7.md.bak_v8_20260419_112002` (29 KB), `_v7.md.pre_enh5954.bak` (40 KB), `_v7.md.pre_enh6364.bak` (41 KB), `_v7.md.pre_enh64_close.bak` (45 KB), `_v7.md.pre_enh65.bak` (45 KB). Total ~235 KB. Also present: 5 `merdian_reference.json.bak_*` files totaling ~415 KB. No operational value post-unification. |
| **Root cause** | Safety-backup pattern during `fix_enh*.py` patch runs created these incidentally. Never cleaned up after the patches landed. `.gitignore` now prevents new `.bak` files being tracked (commit `bca369d`), but existing files on disk remain. |
| **Workaround** | Ignore. Not tracked in git anymore. Disk cost trivial. |
| **Proper fix** | Move to `docs/registers/archive/` for audit trail, or delete outright. Archive is the safer default — disk is cheap, audit trail is valuable. |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-22 |

---

### TD-010 — PowerShell 5.1 `Get-Content` defaults to cp1252 when reading UTF-8 files

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-22 (verifying `session_log.md` post-prepend; sibling of OI-20 write-path BOM issue but different path — this one is read-side) |
| **Component** | PS 5.1 default decoder in `Get-Content`, `Select-String`, `Import-Csv`, and most PS file-reading cmdlets |
| **Symptom** | UTF-8 multi-byte characters in files (em-dash `—` = `E2 80 94`, middle dot `·` = `C2 B7`, curly quotes, etc.) display as multi-character cp1252 mojibake — e.g. `—` renders as `â€”`, `·` renders as `Â·`. **File bytes on disk are correct**; only the PS display is wrong. Verified by re-reading the same file with `-Encoding UTF8` flag which renders correctly. |
| **Root cause** | PS 5.1 reads bytes then decodes them with cp1252 by default. The `$PROFILE` fix from OI-20 (which set `$OutputEncoding`, `[Console]::OutputEncoding`, `[Console]::InputEncoding` to UTF-8 without BOM) addresses the OUTPUT / stdout / argv-to-git-commit paths. It does NOT control `Get-Content`'s INPUT decoder — that is governed by the cmdlet's internal default which remains cp1252 on PS 5.1. Two orthogonal PS 5.1 defaults; OI-20 fix covered one, TD-010 is the other. |
| **Workaround** | Pass `-Encoding UTF8` explicitly to every `Get-Content`, `Select-String`, `Import-Csv` call when the target file contains non-ASCII. Irritating but correct. |
| **Proper fix** | Extend `$PROFILE` with `$PSDefaultParameterValues['*:Encoding']='utf8'` — sets UTF-8 as the default for every cmdlet that accepts an `-Encoding` parameter. Verified safe: does not affect cmdlets without an `-Encoding` param; explicit `-Encoding` passes still override. Long-term answer is PS 7 but that's a multi-session migration with Task Scheduler retest burden. |
| **Cost to fix** | <1 session for the `$PROFILE` addition. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-22 |

### TD-015 — `run_preflight.py` 4-stage preflight system is undocumented; reinvented as one-off

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-24 (Session 7 close + Friday post-market work, morning preflight) |
| **Component** | `run_preflight.py`, runbook coverage, CLAUDE.md "Common operations" table |
| **Symptom** | A canonical 4-stage preflight (env / auth / db / runner_drystart) exists at `run_preflight.py` but is referenced by no runbook, not in CLAUDE.md's operations table, and not surfaced in `merdian_reference.json` operations index. On 2026-04-24 morning the chat re-invented it as `preflight_20260424.py` (now an untracked file in working tree, gitignored as `preflight_*.py` scratch). Future sessions will re-invent it again unless the canonical path is surfaced. |
| **Root cause** | Documentation gap. `run_preflight.py` predates the runbook layer (Rule 11, 2026-04-22); never retroactively given a runbook entry. Tribal knowledge that didn't survive the Session 6 -> 7 chat boundary. |
| **Workaround** | Operator memory. One-off `preflight_20260424.py` written for today, never run again; not committed. |
| **Proper fix** | (a) Create `docs/runbooks/runbook_run_preflight.md` from `RUNBOOK_TEMPLATE.md` documenting the four stages, expected exit codes, when to run each, and the standard "all-PASS = green to start day" criterion. (b) Add row to CLAUDE.md "Common operations" table. (c) Delete `preflight_20260424.py` from working tree. (d) Confirm `merdian_reference.json` has a `files.run_preflight.py` entry; add if missing. |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-24 |

---

### TD-016 — Dhan TOTP scheduled task fails with `Invalid TOTP`; manual run with same seed succeeds

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-24 08:15 IST scheduled task |
| **Component** | `refresh_dhan_token.py`, `MERDIAN_Refresh_Dhan_Token` Task Scheduler task, Dhan TOTP auth path |
| **Symptom** | 08:15 IST scheduled invocation of `refresh_dhan_token.py` returned `Invalid TOTP`. Manual run of the same script at 09:03 IST, same seed, same host, succeeded on first attempt. Both inside Dhan's accepted TOTP window. No diagnostic context captured at the failing run beyond the error string. |
| **Root cause** | Unknown. Three plausible causes, none yet confirmed: (a) Windows clock drift not surfaced by `w32tm /query /status`; (b) TOTP seed cache mismatch between Task Scheduler service context and interactive PowerShell; (c) Dhan-side rate-limit silently rejecting first call when a stale failed-login is still cached upstream. |
| **Workaround** | Manual `python refresh_dhan_token.py` at session start when the scheduled task fails. AWS picks up the new token via `pull_token_from_supabase.py` after the manual run completes. Token refresh is operator-supervised at session start anyway, so the failure mode is non-blocking — but it costs ~5 minutes per occurrence. |
| **Proper fix** | When the failure recurs, run a 30-minute diagnostic capture: (1) `w32tm /stripchart /computer:time.windows.com` against +/-10s of the 08:15 fire moment, (2) capture exact request/response (envvars, CWD, egress IP, computed TOTP value at the same wall-clock) for scheduled-context vs interactive-context, (3) diff. One of the three suspected causes should fall out. Until reproduction, document the manual-fallback procedure in `runbook_update_dhan_token.md`'s failure-modes section. |
| **Cost to fix** | 1 session diagnosis when it recurs (cannot reproduce on demand). Possibly +1 session for the actual fix once root cause is identified. |
| **Blocked by** | Recurrence — cannot reproduce on demand. Next 08:15 IST `Invalid TOTP` is the trigger. |
| **Owner check-in** | 2026-04-24 |

---

### TD-017 — `build_ict_htf_zones.py --timeframe H` has no scheduled invocation

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-24 (pre-market `--timeframe H` returned 0 zones; investigation confirmed this is structurally correct but the post-market scheduled run is missing) |
| **Component** | `build_ict_htf_zones.py`, Windows Task Scheduler + AWS cron coverage for `--timeframe H` |
| **Symptom** | The 09:00 IST cron runs `--timeframe D` only. `--timeframe H` requires >= 2 completed 1H candles of the current session and is therefore a no-op pre-market — confirmed not a bug (added to CURRENT.md DO_NOT_REOPEN). But there is no post-market scheduled invocation, so 1H HTF zones in `ict_htf_zones` lag behind D zones whenever the operator forgets the manual run. |
| **Root cause** | Original cron deployment included `--timeframe D` only. Post-market H requirement was identified during today's investigation but never converted into a scheduled task. Behaviour of the builder is correct; scheduling coverage is incomplete. |
| **Workaround** | Manual post-market run by operator. Inconsistently performed — 1H zone freshness is therefore best-effort. |
| **Proper fix** | Add Windows Task Scheduler task **and** AWS cron entry at 16:15 IST (15 min after EOD ingest) running `python build_ict_htf_zones.py --timeframe H`. Mirror logging, exit-code capture, and Telegram alert pattern of the existing 09:00 IST D-timeframe task. Update `merdian_reference.json` cron inventory. Verify whether OI-11 maps cleanly to this concern; if so, mark OI-11 as superseded by TD-017 in the historical OI register (register itself stays closed per Rule 9). |
| **Cost to fix** | 1 session (Task Scheduler + AWS cron + JSON inventory + runbook touch in `runbook_*` if appropriate) |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-24 |

---

### TD-018 — `build_ict_htf_zones.py:468` uses deprecated `datetime.utcnow()`

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-24 (DeprecationWarning surfaced during D-timeframe build run) |
| **Component** | `build_ict_htf_zones.py` line 468 (and likely other callsites repo-wide) |
| **Symptom** | `DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).` emitted on every D build. No functional impact today; will hard-break when the cpython release that removes `utcnow()` reaches the deployed Python. |
| **Root cause** | Code written against pre-3.12 Python. `datetime.utcnow()` was deprecated in Python 3.12. |
| **Workaround** | Ignore the warning. Builder produces correct zones. |
| **Proper fix** | Replace `datetime.utcnow()` at `build_ict_htf_zones.py:468` with `datetime.now(timezone.utc)` (and add `from datetime import timezone` import). Verify call-site treats the resulting tz-aware datetime correctly — tz-aware vs naive comparison is the typical breakage on this migration. While in there, `grep -rn "utcnow()" *.py` for other callsites and fix in the same patch — there are likely several. |
| **Cost to fix** | <1 session for `build_ict_htf_zones.py:468` alone; ~1 session for codebase-wide migration. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-24 |

---

---

### TD-019 — `hist_spot_bars_5m` pipeline stale since 2026-04-15; blocks forward research validation

| | |
|---|---|
| **Severity** | ~~S2~~ → CLOSED 2026-04-26 (Session 9) |
| **Discovered** | 2026-04-25 (Session 8 — Exp 17 backtest discovered last bar 2026-04-15 09:55) |
| **Component** | `hist_spot_bars_5m`, `hist_spot_bars_1m`, `build_spot_bars_mtf.py`, `capture_spot_1m.py`, `MERDIAN_Spot_1M` Task Scheduler task |
| **Symptom** | `hist_spot_bars_5m` last bar 2026-04-15 15:25 IST for both NIFTY and SENSEX. 10 calendar-day / 7 trading-day gap as of 2026-04-26. The 2026-04-24 NIFTY -393 / SENSEX -1,100 cascade event — the motivating event for Experiment 17 — was missing from the dataset, blocking forward overlay validation of any current research. |
| **Root cause** | (FINAL) `build_spot_bars_mtf.py` was uninstrumented (no `script_execution_log` writes ever) AND was never bound to Task Scheduler. It was a manual on-demand full-history rebuild. Last manual run was on or around 2026-04-15 EOD; nobody ran it again until Session 9. Capture pipeline (`capture_spot_1m.py`, `market_spot_snapshots`, `hist_spot_bars_1m`) was healthy throughout — the gap was purely downstream. The originally-hypothesised candidate causes ((a) Task Scheduler silent fail, (b) aggregator cron broken, (c) capture writer error) were all refuted by Q-A audit (no script in `script_execution_log` ever claimed `hist_spot_bars_5m` as a write target) and Q-B trading-day pattern (clean 150-row days through 04-15 with no irregular bulk-load shape). |
| **Workaround** | None needed post-fix. |
| **Proper fix** | Applied 2026-04-26 in three changes (all delivered same session, override of "no fix in diagnosis session" rule logged): (1) **Instrument** — patched `build_spot_bars_mtf.py` with ENH-71 `core.execution_log.ExecutionLog`. `expected_writes={"hist_spot_bars_5m": 1, "hist_spot_bars_15m": 1}` (minimum-1 row semantics catches "ran cleanly but wrote nothing"). Wraps `_run()` in try/except → `exit_with_reason('CRASH', ...)` for unhandled exceptions. Patch scripts: `fix_td019_instrument_build_spot_bars_mtf.py` (+1830 bytes) + `fix_td019_add_sys_import.py` (+11 bytes) — second was a follow-up because original file never imported `sys`. Both ast.parse() validated; backup at `build_spot_bars_mtf.py.pre_td019.bak`. (2) **Backfill** — manual `python build_spot_bars_mtf.py` run wrote 42,324 5m rows + 14,440 15m rows in 116s. Idempotent on `idx_hist_spot_5m_key` / `idx_hist_spot_15m_key` unique indexes. Verified via `script_execution_log`: `exit_reason=SUCCESS, contract_met=true, host=local, git_sha=1de239a`. (3) **Schedule** — registered `MERDIAN_Spot_MTF_Rollup_1600` Task Scheduler task. Daily 16:00 IST Mon-Fri. Wrapper `run_spot_mtf_rollup_once.bat` matches existing MERDIAN task pattern (logs to `logs\task_output.log`). Smoke-tested same session: second SUCCESS row in `script_execution_log` 11:37 IST, `LastTaskResult=0`, `NextRunTime=2026-04-27 16:00`. |
| **Cost to fix** | Delivered in 1 session (Session 9, 2026-04-26). |
| **Blocked by** | — closed. |
| **Owner check-in** | CLOSED 2026-04-26 |

---

### TD-020 — LONG_GAMMA gate on 2026-04-24 strongly directional day — diagnosis required before ADR-002 ratification

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-25 (Session 8 — chart review of 2026-04-24 NIFTY -393 / SENSEX -1,100 intraday cascade) |
| **Component** | `build_market_state_snapshot_local.py` (gamma regime classification), gating logic in `build_trade_signal_local.py`, `options_flow_snapshots`, ADR-002 (in-flight) |
| **Symptom** | 2026-04-24 was the strongest directionally-bearish intraday day of the recent month: NIFTY -393 pts H-L (-1.6%), SENSEX -1,100 pts H-L (-1.4%). CURRENT.md "Live trading" block records BULL_FVG TIER2 signals on both indices BLOCKED by LONG_GAMMA gate. LONG_GAMMA classification implies dealer-driven mean reversion expected; the actual price action was strongly trending. Concern: if BEAR setups were also generated and also blocked, the gate left a high-conviction directional opportunity on the table; if BEAR setups were NOT generated despite the bearish breadth context, that is a separate signal-generation question. ADR-002 is currently being drafted around the assumption that the gate "did its job" by blocking trades — that framing is not yet evidence-supported for the strongest test case in recent history. |
| **Root cause** | Unknown. Three sub-hypotheses to discriminate: (a) **Regime classification was correct** but local positioning differed from net (Exp 23 territory — net GEX positive but local-near-spot GEX negative); gate fired correctly given the data it had, but the data was the wrong granularity for the regime question. (b) **Regime classification was wrong** — net GEX was actually negative all day but classifier returned LONG_GAMMA due to bug, stale source_ts, or threshold miscalibration. (c) **Regime classification was correct AND positioning was correct** — gamma did try to hedge, but other forces (breadth-driven momentum, news flow, FII positioning) dominated; gate is doing what it's designed to do, ADR-002 framing stands. |
| **Workaround** | None operationally — Phase 4A live trading continues. ADR-002 drafting paused until diagnosis completes. |
| **Proper fix** | Session 9 diagnosis (sub-hypotheses to discriminate): (1) Pull `options_flow_snapshots` for 2026-04-24 09:15-15:30 IST, both indices, every snapshot. Plot net GEX time series. Confirm regime classification matches the reported LONG_GAMMA state at each cycle. (2) Pull all signals generated 2026-04-24 from signal pipeline output — every direction (bull AND bear), every tier. Confirm whether BEAR signals were generated and what gate dispositioned them. (3) Compute local-vs-net gamma divergence (Exp 23 framework — strikes within ±0.5% of spot vs full chain). If they diverge significantly, this is the smoking gun for sub-hypothesis (a). (4) Check `source_ts` freshness on the gamma JSONB block during 2026-04-24 — Candidate D's concern. If the gamma block was reading stale data, that's sub-hypothesis (b). |
| **Cost to fix** | 1 session for diagnosis (read-only DB queries, no code change). Outcome determines whether Session 10 needs a code fix or ADR-002 can ratify as-is. |
| **Blocked by** | TD-019 partially — the spot bar gap on 2026-04-24 means we have GEX/options data for that day but not 5m spot bars. GEX time-series + tick data should be sufficient for the diagnosis without 5m spot bars. |
| **Owner check-in** | 2026-04-25 |


**Disposition (2026-04-25, Session 8 extended diagnosis):** All three originally-hypothesised sub-causes refuted or moot. Replaced by sub-hypothesis (d), undocumented at filing.

**Evidence:**
- `gamma_metrics` 2026-04-24 09:15-14:25 IST: 100 NIFTY rows + 123 SENSEX rows. `regime='LONG_GAMMA'` on every row. NIFTY `net_gex` range +5.3T to +18.6T. SENSEX `net_gex` range +185B to +2.2T (avg +1.5T). No regime flip, no sign change in net_gex. Classification was numerically correct.
- `signal_snapshots` 2026-04-24 full day: 245 rows (122 NIFTY, 123 SENSEX). `ict_pattern='NONE'` on all 245. `direction_bias='NEUTRAL'` on all 245. `action='DO_NOTHING'` on all 245. **Zero ICT setups generated all day, either direction, either index.**
- `hist_pattern_signals`, `signal_snapshots_shadow`, `signal_state_snapshots` 2026-04-24: zero rows in each. The 245 signal_snapshots rows are the complete 2026-04-24 signal record.

**Sub-hypothesis evaluation:**
- (a) Local-vs-net divergence: MOOT -- gate had no signals to filter, so its granularity is irrelevant for 2026-04-24.
- (b) Regime classification was wrong: REFUTED -- net_gex strongly positive throughout, LONG_GAMMA correctly assigned.
- (c) Regime correct AND gate worked as designed: PARTIALLY SUPPORTED but misleading -- regime call was correct, but the gate did not protect anything because it received no inputs to gate.
- **(d) NEW: ICT pattern detector silent on the strongest directional day of the recent month.** Cannot be diagnosed under TD-020 scope (which assumed gate-behaviour question). Filed as TD-022.

**Reconciliation with Session 7 CURRENT.md statement:** Session 7's CURRENT.md described "BULL_FVG TIER2 signals on both indices BLOCKED by LONG_GAMMA gate" on 2026-04-24. The signal_snapshots data does not support this -- no BULL_FVG signals existed. Either Session 7's CURRENT.md was incorrect (the more likely explanation; possibly described expected behaviour rather than observed), or BULL_FVG signals were generated and rejected upstream of signal_snapshots in a layer not yet identified. This warrants a brief check in Session 9 of any pre-`signal_snapshots` log/queue that might hold rejected setups; if no such layer exists, treat the Session 7 statement as erroneous and update DO_NOT_REOPEN.

**Impact on ADR-002:** Cannot ratify the "gate-protected posture" framing. The protection on 2026-04-24 was not the gate; it was the absence of signals. ADR-002 remains BLOCKED, now blocked on TD-022 (the real causal question), not TD-020 (which is closed).

**Status:** CLOSED -- diagnosed.
**Closed:** 2026-04-25
**Closed_by:** Session 8 extended diagnosis
**Successor:** TD-022 (ICT detector silent on cascade days)

---

### TD-021 -- Two undocumented operational conventions surfaced during Session 8

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-25 (Session 8) |
| **Component** | `.gitignore`, `merdian_pm.py`, `merdian_start.py` |
| **Symptom** | Two small things that bit operations during this session and will bite again unless documented. (a) `.gitignore` line 78 `/experiment_*.py` blocks default-add of new experiment scripts at repo root; convention is to force-add experiments worth keeping reproducible (precedent: `experiment_15.py`, `experiment_15b.py`, `experiment_17_bull_zone_break_cascade.py`). The convention is undocumented anywhere. Cost when missed: one extra commit and a confused user. (b) Adding a new managed process requires two parallel edits -- `merdian_pm.py` PROCESSES dict AND `merdian_start.py` hardcoded list at line 150. ENH-73 deployment hit this exactly: pm_stop killed the process correctly (saw it in PROCESSES) but pm_start didn't launch it (start.py's loop didn't include it). |
| **Root cause** | Both are missing-documentation issues, not bugs. (a) gitignore convention only became apparent when a new experiment was force-added; no comment in `.gitignore` flags it. (b) Schema duplication between `merdian_pm.PROCESSES` and `merdian_start.py`'s hardcoded loop. Originally fine when there were 3 processes; now there are 5 and the redundancy has cost. |
| **Workaround** | Operator memory + this register entry. |
| **Proper fix** | (a) Add a one-line comment above `.gitignore:78` reading something like `# experiment_*.py is default-ignored to keep scratch out of git. Force-add (git add -f) for experiments worth retaining. Precedent: experiment_15.py, experiment_15b.py, experiment_17_bull_zone_break_cascade.py.` (b) Refactor `merdian_start.py` line 150 to iterate over `pm.PROCESSES.keys()` directly, eliminating the second list. ~5 line change. After this, adding a process anywhere requires only one edit. |
| **Cost to fix** | <1 session -- bundle into a future OPS commit. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-25 |

---

### TD-022 -- ICT pattern detector generated zero setups on 2026-04-24 directional cascade day; live signal generation may be silently skipping cascade conditions

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-25 (Session 8 extended TD-020 diagnosis) |
| **Component** | ICT pattern detector (`build_ict_zones.py` / `build_ict_htf_zones.py` upstream; `build_trade_signal_local.py` integration), `signal_snapshots`, `hist_pattern_signals` |
| **Symptom** | 2026-04-24 was the strongest bearish intraday day of the recent month (NIFTY -1.6%, SENSEX -1.4%, NIFTY broke W BULL_FVG 24,074-24,241 by 09:30 IST and cascaded -393 pts intraday; SENSEX similar at 77,636 cascading -1,100 pts). The chart-visible W BULL_FVG zones existed in `ict_htf_zones` (confirmed by 2026-04-25 morning chart screenshots labelled "W BULL_FVG 24,074 PRICE INSIDE [Apr 17]"). Despite this, `signal_snapshots` for 2026-04-24 contains 245 rows, ALL with `ict_pattern='NONE'`, `direction_bias='NEUTRAL'`, `action='DO_NOTHING'`. The live ICT detector did not register the zone interaction or the break. Phase 4A's apparent risk-aversion on this day was not produced by the gate (LONG_GAMMA gate on 2026-04-24 received zero signals to filter -- see TD-020 disposition); it was produced by detector silence. |
| **Root cause** | Unknown. Three plausible classes, requires investigation: (1) **Lookback/window mismatch** -- detector may require zone status that `ict_htf_zones` doesn't yet have; e.g. detector reads `status='ACTIVE'` but the W BULL_FVG was already `BREACHED` by mid-morning, removing it from candidates. (2) **Detector input gap** -- TD-019 stale `hist_spot_bars_5m` may already have been affecting live detection on 2026-04-24 (last bar 2026-04-15 means detector reading from a 9-day-stale price feed by 2026-04-24, possibly outputting NONE because no fresh candles to anchor patterns to). (3) **Pattern type filter** -- detector may be configured to detect only certain ICT patterns (e.g. `BREAK_OF_STRUCTURE`, `LIQUIDITY_SWEEP`) and the cascade pattern of "open inside zone, break below, close below" doesn't map to any registered pattern. |
| **Workaround** | None. Phase 4A is currently relying on detector silence as if it were intentional risk control. Any apparent system success on directional days is unverified -- could be skill, could be silence. |
| **Proper fix** | Session 9 (NEW Candidate A, replacing TD-020 LONG_GAMMA diagnosis): (1) Read `build_trade_signal_local.py` and the ICT detector entry-point. Document what input each pattern type requires from `ict_htf_zones` and `hist_spot_bars_5m`. (2) Replay 2026-04-24 against the detector with current data: pull a single 2026-04-24 bar from Kite REST (one-off, doesn't fix TD-019), feed it to the detector against the ict_htf_zones at that moment in time (`created_at <= 2026-04-24 09:30:00 IST`), see what the detector outputs. (3) If detector outputs NONE for a clear cascade input, that's a pattern-coverage bug -- file ENH. (4) If detector outputs a setup but signal_snapshots shows NONE, that's an integration bug between detector and writer -- file ENH. (5) If detector errors or silently fails on missing 5m bars, that's TD-019's fault -- closure of TD-019 closes this. |
| **Cost to fix** | 1-2 sessions for diagnosis. Fix scope unknown until diagnosis completes. |
| **Blocked by** | Partially TD-019 -- if root cause is TD-019, then TD-019's repair is also TD-022's repair. Diagnosis itself can proceed before TD-019 fix. |
| **Owner check-in** | 2026-04-26 |
| **Blocks** | (was: ADR-002 ratification) -- now superseded by TD-020 reframing |

**Disposition (2026-04-26, Session 9 deep-dive):** TD-022's filed framing
("ICT pattern detector silent on cascade day") was structurally wrong. The
detector ran 404 cycles on 2026-04-24 (per script_execution_log), wrote 3
ict_zones rows for the day (1 NIFTY + 2 SENSEX BULL_FVG TIER2), and produced
output as designed. The "silence" observed in signal_snapshots is downstream
of `enrich_signal_with_ict()` in build_trade_signal_local.py, which filters
zones by direction matching `action`: `direction = +1 if action=="BUY_CE" else -1`.
With `action='DO_NOTHING'` (set upstream by the LONG_GAMMA gate firing on
every cycle), the directional filter matches nothing, returns empty,
ict_pattern is set to NONE. ICT is an innocent passenger; the gate is the
driver.

**Real cause (re-attributed to TD-020 reframing):** LONG_GAMMA gate fired
correctly as designed on every cycle, setting `direction_bias='NEUTRAL'`,
`action='DO_NOTHING'`, `trade_allowed=False`. Session 8 disposition concluded
"gate had no signals to filter; ICT detector silent" — that was reading the
gate's OUTPUT (NEUTRAL/DO_NOTHING) as if it were the gate's INPUT. See TD-020
(reopened/closed-correctly).

**Status:** CLOSED -- duplicate of TD-020 (correctly reframed).
**Closed:** 2026-04-26 (Session 9)
**Closed by:** TD-020 reframing + ENH-37 source read

---

### TD-023 — Uninstrumented data producers (anti-pattern, audit pending)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-26 (Session 9 — surfaced during TD-019 closure) |
| **Component** | All scripts that write to data tables; `script_execution_log` audit coverage |
| **Symptom** | The TD-019 silence was hidden for 7 trading days because `build_spot_bars_mtf.py` never wrote a row to `script_execution_log`. Any producer not wired into ENH-71 contract logging can fail invisibly until a downstream consumer notices. A Q-A audit during TD-019 (searching `script_execution_log` for `actual_writes` / `expected_writes` referencing the stale table) returned zero rows — proving the table had no instrumented producer. By extension, every other public data table needs the same audit; producers that fail the same query are the same kind of trap waiting to spring. |
| **Root cause** | ENH-71 propagation was scoped to a known set of scripts (ENH-72 closed 9, TD-014 added the 10th). Producers outside that explicit set were never required to instrument. `build_spot_bars_mtf.py` was outside the set because it was treated as a "manual rebuild tool" rather than a production writer. Same risk applies to any other manual / occasional / one-off writer that targets a production table. |
| **Workaround** | None active. Operator memory + this register entry. |
| **Proper fix** | Audit pass: (1) `select tablename from pg_tables where schemaname='public'` to list all public data tables. (2) For each, run the Q-A pattern: `WHERE actual_writes::text LIKE '%<table>%' OR expected_writes::text LIKE '%<table>%'` against `script_execution_log`. Tables with zero hits = uninstrumented producer somewhere. (3) `Get-ChildItem -Recurse -Include *.py \| Select-String -Pattern "<table>" -List` to locate the writer(s). (4) Patch each using the `build_spot_bars_mtf.py` template (~10 lines per script). File one sub-TD per uninstrumented producer found; close as patched. |
| **Cost to fix** | 1-2 sessions for the audit. Patching pace depends on producer count. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-024 — 19:01 IST writes to `market_spot_snapshots` (post-close anomaly, two cases)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — Q3 freshness query during TD-019 diagnosis) |
| **Component** | `market_spot_snapshots`, `hist_spot_bars_5m`, possibly `capture_spot_1m.py`, possibly ENH-73 heartbeat |
| **Symptom** | (a) 2026-04-24 `market_spot_snapshots` and `hist_spot_bars_1m` show writes at 19:01:02 IST for both NIFTY and SENSEX. `capture_spot_1m.py` is documented as 09:14-15:31 IST per `MERDIAN_Spot_1M` Task Scheduler task. A 19:01 write is ~3.5 hours after schedule end. `script_execution_log` shows `capture_spot_1m.py` last_run 2026-04-24 19:01:01 IST — the script ran, it just ran outside its window. (b) 2026-04-13 (Mon) `hist_spot_bars_5m` shows 152 bars (vs typical 150) with `last_bar` at 16:10 IST. Two extra post-close 5m bars. Different table, different mechanism, but same family (post-close write). |
| **Root cause** | Unknown. Candidate causes: (1) ENH-73 Telegram alerts + 10-min heartbeat deployed Session 8 — fits 04-24 timing but not 04-13 (12 days earlier, before ENH-73). (2) Undocumented EOD job not in Task Scheduler inventory. (3) Manual run not recorded in operator memory. (4) Clock or tz handling issue at the wrapping shell layer. |
| **Workaround** | Not a data-correctness issue; bars and snapshots are well-formed. No active mitigation needed. |
| **Proper fix** | Query `script_execution_log` for `capture_spot_1m.py` rows where `started_at` falls outside the 09:14-15:31 IST window. Identify host/git_sha pattern. If ENH-73 heartbeat: document as expected behaviour, update `merdian_reference.json` cadence string. If different invoker: trace via Task Scheduler history or `.bat` log files for the same date. |
| **Cost to fix** | <1 session for diagnosis. Resolution scope depends on cause. |
| **Blocked by** | nothing — investigation can run any time. Bundle with TD-023 audit if convenient. |
| **Owner check-in** | 2026-04-26 |

---

### TD-025 — `build_spot_bars_mtf.py` re-aggregates full history every run (compute waste)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — observed during TD-019 patch design) |
| **Component** | `build_spot_bars_mtf.py` |
| **Symptom** | Each invocation reloads ALL 1m bars (~210k rows across NIFTY+SENSEX = ~282 trading days × 75 bars × 2 instruments) and re-aggregates the entire history into 5m + 15m, even when only the last day's worth of new data needs producing. At 116s/run × 252 trading days/year × 2 outputs = ~16 hours/year of wasted compute. Idempotent upserts on the unique index mean it's not incorrect, just wasteful. |
| **Root cause** | Original design as a manual on-demand full-history rebuild tool (TD-019 closure context). Was never re-architected after being scheduled as a daily task. |
| **Workaround** | None needed — daily 116s runtime is comfortably within Task Scheduler's 30-min `ExecutionTimeLimit`. |
| **Proper fix** | Parameterise on a date window. Default to "since `MAX(bar_ts)` in `hist_spot_bars_5m`" or "today's `trade_date` only". Full rebuild remains available via `--full` flag for backfills (so the TD-019 backfill recipe is preserved). Reduces typical run from ~116s to <10s. |
| **Cost to fix** | <1 session. |
| **Blocked by** | nothing. Defer until other priorities clear. |
| **Owner check-in** | 2026-04-26 |

---

### TD-026 — PowerShell scripts must be ASCII-only (encoding pitfall)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — `register_spot_mtf_rollup_task.ps1` failed parse due to em-dashes) |
| **Component** | All `.ps1` and `.bat` files in repo |
| **Symptom** | Windows PowerShell 5.x defaults to ANSI/Windows-1252 when reading a `.ps1` without a BOM. Non-ASCII characters (em-dashes `—`, box-drawing `─`, smart quotes, etc.) get mangled and produce misleading parser errors that point at lines BEFORE the actual offending byte. Exact failure mode encountered Session 9: em-dash on line 52 → parser reported "Missing closing '}' in statement block" at line 51. Wasted one round trip. |
| **Root cause** | Windows PowerShell 5.x text-handling default, not a script bug. Same family as TD-010 (`Get-Content -Encoding UTF8` requirement). PowerShell 7+ defaults to UTF-8 and would not have hit this. |
| **Workaround** | Re-emit script as pure ASCII: replace `—` with `--`, `─` with `-`, smart quotes with straight quotes, box-drawing with `\|`/`+`/`-`. |
| **Proper fix** | Convention, not a code change: all `.ps1` and `.bat` in this repo are ASCII-only. No em-dashes in comments, no box-drawing in banners. Add a one-line note to CLAUDE.md alongside TD-010 / `Get-Content -Encoding UTF8` so the rule is visible at session start. |
| **Cost to fix** | Convention-only; no fix to apply. Closes when documented in CLAUDE.md. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-027 — `merdian_pipeline_alert_daemon` scope drifted from name

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — Item 4 of TD-022 follow-up parking lot) |
| **Component** | `merdian_pipeline_alert_daemon.py`, ENH-73 + ENH-46-A |
| **Symptom** | The daemon's name and ENH-73 description suggest broad "pipeline alerting." Initial implementation alerted only on infrastructure failures from `script_execution_log`. ENH-46-A extended it to also alert on tradable signals (signal_snapshots). The file now does two distinct jobs but is named for one. |
| **Root cause** | ENH-73 was scoped narrowly during Session 8 deployment (infrastructure visibility); name and description used the broader "pipeline" term that implied wider scope. Documentation drift between intent and implementation, not a bug. ENH-46-A absorbed the gap rather than splitting into a new daemon. |
| **Workaround** | None needed; the daemon does what it does correctly post-ENH-46-A. This TD is about clarity going forward. |
| **Proper fix** | Two paths, mutually exclusive: (a) **Rename narrowly**: rename to `merdian_infra_alert_daemon.py`, keep ENH-73 narrow, treat ENH-46-A as a separate daemon `merdian_signal_alert_daemon.py`. Cleaner separation of concerns, requires file rename + Task Scheduler / pm.PROCESSES + state.json migration. (b) **Embrace the broad name**: keep the file name; document the multi-mode behaviour in the daemon docstring and ENH-73 description; accept a kitchen-sink. Recommendation: (b) for now, revisit if scope balloons further (e.g. third alerting domain added later). |
| **Cost to fix** | <1 session. Not urgent. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-028 — `merdian_pm.py` silently fails on unknown process name

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-26 (Session 9 — ENH-46-A daemon restart) |
| **Component** | `merdian_pm.py`, `start()` and `status()` functions |
| **Symptom** | Calling `python merdian_pm.py stop merdian_pipeline_alert_daemon` (full script filename instead of registry key `pipeline_alert`) returned no output and took no action. Calling `python merdian_pm.py status` also returned no output (whether the registry was empty or the function silently no-op'd is unclear). Net effect: operator believed the daemon had been stopped/restarted when in fact it had not, leading to ~10 minutes of confusion (PID 24968 still running with old code while operator thought new code was loaded). The pm tool's `start()` returns `False, f"Unknown: {name}"` on miss — but only the print path was checked; the actual return path was not surfaced, so the user saw nothing. |
| **Root cause** | Two issues entangled: (1) `start()` and `stop()` print the result tuple via wrappers in some code paths but not others — when called via `python merdian_pm.py <cmd> <name>` from CLI, the bool/msg tuple is returned but not echoed. (2) `status` likely outputs only when there are processes to report, suppressing the "no processes registered" case entirely. Either should fail loudly. |
| **Workaround** | Use the actual registry keys (`pipeline_alert`, `health_monitor`, `signal_dashboard`, `supervisor`, `exit_monitor`) not the script filenames. For start/restart, fall back to direct `Start-Process` PowerShell launch (used in Session 9 to relaunch the alert daemon after `merdian_pm.py start pipeline_alert` produced no output). |
| **Proper fix** | Three changes: (a) print the `(ok, msg)` tuple unconditionally at the top of every CLI handler. (b) emit `[OK] No matching processes` (or similar) from `status` when registry is empty. (c) consider raising on unknown process name (rather than `return False, "Unknown: ..."`) so silent-fail can't happen. <1 session. Bundle with TD-021 fix on the `merdian_start.py` dual-list issue (same file family, related cleanup). |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-029 — `hist_spot_bars_1m` and `hist_spot_bars_5m` pre-04-07 era TZ-stamping bug

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-26 (Session 10 mid-experiment, hist_spot_bars_5m TZ diagnostic) |
| **Component** | `hist_spot_bars_1m`, `hist_spot_bars_5m` (rows with `trade_date < 2026-04-07`) |
| **Symptom** | Pre-04-07 rows have IST clock-time stored under UTC tzinfo marker. Approximately 2,820 rows in 5m table affected. 1m table also affected (Q-1M-TZ-DIAGNOSTIC confirmed identical era boundary). |
| **Root cause** | One-off ingest event 2026-04-18 04:43 UTC misclassified the timezone metadata for previously-ingested historical bars. Post-04-07 rows are correctly UTC-stamped (current writer behaviour is correct). |
| **Workaround** | Era-aware CASE on `trade_date` in queries: pre-04-07 → strip-tzinfo-and-reattach-IST; post-04-07 → standard UTC→IST conversion. Used successfully in Exp 29 v2, Exp 31, Exp 32, Exp 15 re-run. Code pattern documented at `experiment_29_1h_threshold_sweep_v2.py:canonicalize_ts_to_ist()`. |
| **Proper fix** | Two options: (a) **Repair**: `UPDATE hist_spot_bars_1m / 5m SET bar_ts = bar_ts - INTERVAL '5 hours 30 minutes' WHERE trade_date < '2026-04-07' AND created_at BETWEEN '2026-04-18 04:43' AND '2026-04-18 04:45';`. Cleaner long-term, but irreversible if scope is wrong. (b) **Document**: write era boundary into `merdian_reference.json`, add CASE-on-trade_date helper to query helpers. Safer. Recommendation: Path A (repair) once scope confirmed via full row-count audit. |
| **Cost to fix** | <1 session if Path A; ~2 sessions if Path B (helper + audit + propagation). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-030 — `build_ict_htf_zones.py` doesn't re-evaluate breach on existing active zones

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-27 (Session 10 pre-open ops) |
| **Component** | `build_ict_htf_zones.py` (all timeframes; affects `ict_htf_zones` table integrity) |
| **Symptom** | Two W BULL_FVG zones (NIFTY 24,074-24,241, SENSEX 77,636-78,203) formed 2026-04-20 remained `status='ACTIVE'` after Friday 04-24's selloff broke through them. Zones with `valid_to >= today` AND `status='ACTIVE'` AND price already below `zone_low` (BULL) or above `zone_high` (BEAR) constitute zombie zones that mislead MTF context lookups. |
| **Root cause** | Script applies breach filter at *write time* during detection of new candidate zones — eliminates already-violated candidates before INSERT. Does NOT re-evaluate existing active zones for breach when subsequent price action breaks them. The "Expired old zones before <date>" log line is date-based expiry only, not breach-based invalidation. |
| **Workaround** | Manual SQL UPDATE per session when zones are visibly stale. Zombie-zone detection query: compute current spot vs zone boundaries with directional CASE, mark BULL_BREACHED if spot < zone_low / BEAR_BREACHED if spot > zone_high. Then UPDATE matching IDs to `status='BREACHED', valid_to=CURRENT_DATE`. Used 2026-04-27 pre-open with success (cleared 2 zombie BULL_FVG zones). |
| **Proper fix** | Add a re-evaluation pass at the start of every `build_ict_htf_zones.py` run: for each existing `status='ACTIVE'` zone, compute its current breach status against the most recent bar's close. If breached, UPDATE to BREACHED before detecting new candidates. Incremental cost minimal — one extra SELECT + conditional UPDATE per active zone, runs once per script invocation. |
| **Cost to fix** | <1 session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-031 — D BEAR_OB / D BEAR_FVG detection underactive in `build_ict_htf_zones.py`

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-27 (Session 10 pre-open ops, post-rebuild zone audit) |
| **Component** | `build_ict_htf_zones.py` daily zone detection (D BEAR_OB and D BEAR_FVG specifically) |
| **Symptom** | Q-D-BEAR-COVERAGE returned: D BEAR_OB total ever written = 2 (last 2026-04-11). D BEAR_FVG total ever written = 0. D BULL_OB = 4 lifetime, D BULL_FVG = 0. Despite multiple visibly bearish daily candles in the past two weeks (NIFTY -1.87% week ending 04-24, SENSEX -1.29%, both with strong red 1D bars 04-23/04-24), the script wrote zero new D BEAR structures. |
| **Root cause** | **(Session 15 update)** Original hypotheses partly confirmed via manual replay during Session 15 code review. Two distinct issues: (a) D-FVG detection was entirely missing from `detect_daily_zones()` for both directions — closed Session 15 as part of TD-048 (BEAR_FVG defect) via S1.b patch; D BEAR_FVG count post-backfill = 79 rows. (b) D-OB detector uses a non-standard ICT definition (uses move bar K+1 itself as OB instead of opposing prior K) — this is the root cause of D BEAR_OB underactivity. Standard ICT definition would generate ~6 D BEAR_OB candidates per Session 15 manual replay vs 1-2 actual. **Promoted to TD-049** for definitional fix. |
| **Workaround** | None for D-OB underactivity. D BULL_FVG / D BEAR_FVG now populated post-Session 15 patches — those parts are no longer underactive. |
| **Proper fix** | D-FVG portion CLOSED via TD-048 fix Session 15. D-OB portion remaining — see TD-049. |
| **Cost to fix** | D-FVG portion done. D-OB portion: <1 session if retroactive backfill, 1 session if version-boundary documentation (decision pending — see TD-049). |
| **Blocked by** | TD-049 (carries the D-OB definitional fix forward) |
| **Owner check-in** | 2026-05-02 (Session 15 reframing — D-FVG closed, D-OB remains open as TD-049) |

---

### TD-032 — Dashboard execution panel ignores `direction_bias` / `action`, displays trades inconsistent with DB ground truth

| | |
|---|---|
| **Severity** | S2 (becomes S1 the moment ENH-46-C ships and trade_allowed=true rows appear) |
| **Discovered** | 2026-04-27 (Session 10 live, post-F0 unmasking) |
| **Component** | `merdian_signal_dashboard.py` execution panel rendering pipeline |
| **Symptom** | Multiple observed inconsistencies between dashboard execution panel and `signal_snapshots` ground truth, observed live during 2026-04-27 trading session: (a) At 11:21 IST, NIFTY signal_snapshots row had `direction_bias=BEARISH, action=BUY_PE, atm_strike=24050, spot=24068.8`. Dashboard rendered: "Strike 24,100 CE / premium ₹85" — wrong instrument (CE not PE), wrong strike (24,100 not 24,050). (b) At 11:38 IST, dashboard rendered "▲ BUY CE / Strike 24,000 CE" while DB had `direction_bias=BEARISH, action=BUY_PE, atm_strike=24050` — dashboard showed BULLISH instrument while DB was BEARISH. (c) At 12:10 IST, dashboard correctly showed ▼ SELL/BUY PE / Strike 24,050 CE — strike-number now matched but instrument label still CE despite BUY_PE action. Pattern is non-deterministic across cycles. |
| **Root cause (provisional)** | Pattern-driven hardcoding ruled out (dashboard CAN render PE on BULL_FVG patterns at other times). Most likely candidates: (a) race condition between cycle's signal_snapshots write and dashboard's multi-field render, (b) dashboard reads some fields from a different/stale source while reading other fields fresh, (c) in-memory cached state in dashboard process clobbering periodic reads. The DB is consistently correct; the dashboard is the unreliable layer. Pre-F0 the inconsistency was masked because direction_bias was clobbered to NEUTRAL on every LONG_GAMMA cycle (the F0 regression). F0's unclobber unmasked the dashboard rendering bug that has presumably existed for weeks. |
| **Workaround** | Always validate against `signal_snapshots` directly before placing any trade. Dashboard is unreliable for direction/strike/instrument-type rendering. `SELECT direction_bias, action, atm_strike, spot FROM signal_snapshots WHERE symbol=$1 ORDER BY ts DESC LIMIT 1`. |
| **Proper fix** | Source code audit of `merdian_signal_dashboard.py` rendering pipeline. Identify which fields come from where, ensure single-source-of-truth (DB row at render time) for the action/strike/instrument triple. Add a "DB-vs-display consistency check" log line at every render: if dashboard-computed strike/instrument differs from DB row, log warning. |
| **Cost to fix** | 1-2 sessions for diagnosis + fix. |
| **Blocked by** | nothing — investigation can run any time |
| **BLOCKER FOR** | **ENH-46-C ship.** Conditional gate lift cannot promote any signal to live `trade_allowed=true` while operator cannot trust dashboard to show correct trade direction. Without TD-032 fixed, an operator looking at the dashboard could place a CE trade when the system intended PE (or vice-versa), causing a 100%-direction-wrong loss. |
| **Owner check-in** | 2026-04-27 |

---

### TD-033 — Dashboard "SELL / BUY PE" label conflation

| | |
|---|---|
| **Severity** | S3 (cosmetic/confusing but does not change actual order routing) |
| **Discovered** | 2026-04-27 (Session 10 live) |
| **Component** | `merdian_signal_dashboard.py` direction label rendering |
| **Symptom** | Dashboard direction label concatenates direction-bias short-form ("SELL" or "BUY") with action ("BUY_CE" or "BUY_PE"), producing strings like "▼ SELL / BUY PE" or "▲ BUY / BUY CE". Two different concepts (short-form bias label vs concrete trade action) shown as one combined label. No real OMS does this. Confusing for operators, especially under stress. |
| **Root cause** | Dashboard rendering layer building label string from two fields without disambiguating them. Likely an early-stage UI prototype that never got cleaned up. |
| **Workaround** | None needed; just confusing. Read the dashboard label as: short-form before the slash = bias, after slash = trade action. The action is what would be placed. |
| **Proper fix** | Display action (BUY_CE / BUY_PE) prominently as the trade. Display direction_bias separately as a regime tag if at all. Or remove the bias label entirely — `gamma_regime` and `wcb_regime` already render in the gate footer. |
| **Cost to fix** | <1 session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-034 — `hist_atm_option_bars_5m` severely undersampled on expiry days (dte=0)

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-27 (Session 10 extension, while running Experiment 33) |
| **Component** | `hist_atm_option_bars_5m` ingestion pipeline + the resulting backtest data quality |
| **Symptom** | Only 11 NIFTY expiry days (dte=0) and 22 SENSEX expiry days observed in 2025-04-01 to 2026-03-30 window. Expected ~50 per symbol (one per weekly expiry day, including monthlies). NIFTY coverage rate: 22%. SENSEX coverage rate: 44%. The `hist_atm_option_bars_5m` table has reasonable coverage on non-expiry days (247 distinct dates) but loses most expiry-day rows. |
| **Impact** | Any backtest research on expiry-day behaviour has 22-44% sample coverage. Affects retrospective analysis of: Exp 31 (expiry-day options replay), Exp 33 (inside-bar before expiry), future ENH-46-C shadow analysis on expiry days, any expiry-day-conditional ICT filter design. The Experiment 33 result of "71% next-day continuation" is based on N=14 instead of the ~50 inside-bar-before-expiry candidates a full coverage would have surfaced. |
| **Root cause (hypotheses)** | (a) Ingestion script has an expiry-day exclusion filter (intentional or accidental), (b) ATM-strike-only filter drops rows when ATM changes intraday on volatile expiries (intraday strike migration), (c) ingestion failures on expiry days due to API rate limits or option chain volatility, (d) a `dte > 0` filter somewhere upstream. None confirmed. |
| **Workaround** | Use spot data (`hist_spot_bars_1m`) for expiry-day characterisation where possible — full coverage. Use option_chain_snapshots' 14-day window for fill-in. For backtests requiring multi-month expiry-day option data, accept the smaller sample. |
| **Proper fix** | Trace ingestion logic. Identify why dte=0 rows are missing. If filter bug → patch + backfill. If API/timing issue → add retry logic + flag missing days. Backfill historical expiry days from upstream (Dhan/Zerodha) where API allows. |
| **Cost to fix** | ~2 sessions diagnostic, ~1-2 sessions backfill if data sources available. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-035 — `signal_snapshots.wcb_regime` is NULL on all rows but dashboard shows "BULLISH"

| | |
|---|---|
| **Severity** | S3 (cosmetic on dashboard, may indicate routing inconsistency) |
| **Discovered** | 2026-04-27 (Session 10 live, during DB-vs-dashboard verification) |
| **Component** | `signal_snapshots` table + dashboard wcb_regime rendering |
| **Symptom** | `SELECT wcb_regime FROM signal_snapshots WHERE ts >= CURRENT_DATE LIMIT 10` returns null on every row. Dashboard footer shows "LONG_GAMMA  BULLISH" — the BULLISH portion is wcb_regime per the rendering logic, but DB has NULL. Dashboard must be reading wcb_regime from a different source (likely `wcb_alignment` field or a separate `market_state_snapshots` table) but the contract is undocumented. |
| **Impact** | Two layers may be making decisions on different wcb_regime sources without explicit acknowledgment. ENH-35 gate logic that depends on wcb_regime classification could be operating on `wcb_alignment` (related but not identical) or on `market_state_snapshots.wcb_regime` (separate table) — unverified which. Architecturally suspect. |
| **Workaround** | Treat dashboard's wcb display as informational only, not as the gate's wcb input. For verification, query `market_state_snapshots` directly, or read `signal_snapshots.wcb_alignment`. |
| **Proper fix** | Source-trace `build_trade_signal_local.py` and `merdian_signal_dashboard.py` to find where wcb_regime is read for each. Either: (a) populate `signal_snapshots.wcb_regime` correctly on every cycle (if it should always be set), or (b) drop the column from signal_snapshots if it's redundant with wcb_alignment / market_state_snapshots, or (c) document explicitly that the column is intentionally null and the canonical source is elsewhere. |
| **Cost to fix** | <1 session — diagnostic + decide which path. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-036 — `signal_snapshots.confidence_score` flat-lines for hours

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-27 (Session 10 live, during signal_snapshots monitoring) |
| **Component** | `build_trade_signal_local.py` confidence scoring logic |
| **Symptom** | `confidence_score` for NIFTY = 20.0 across 10 cycles spanning 11:18 to 12:10 IST. SENSEX = 32.0 across same window. Earlier 09:31-09:41 IST window also NIFTY=20, SENSEX=32. Score has not moved for at least 1 hour, possibly the entire session. |
| **Impact** | Confidence score should respond to changing market state. Either: (a) score is computed only at coarser granularity (e.g., once per session) and held constant — design choice but not documented, (b) score is computed per cycle but inputs aren't moving enough to change it — possible but unlikely over 90+ minutes of price action, (c) bug pinning score to a constant. Without diagnostic, hard to know which. |
| **Workaround** | Don't use confidence_score for any trade decision. Treat it as deprecated until validated. |
| **Proper fix** | Source-trace confidence scoring logic. Decide whether it should be dynamic or static. If dynamic → fix update cadence. If static → rename to something like `static_confidence_baseline` to clarify. |
| **Cost to fix** | <1 session diagnostic. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-037 — Schema column-name inconsistency across timestamp-bearing tables

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-27 (Session 10 extension, surfaced by repeated SQL errors during Exp 33 development) |
| **Component** | Database schema across multiple tables |
| **Symptom** | Three different timestamp column conventions across canonical tables: `signal_snapshots` uses `ts`, `hist_spot_bars_1m` uses `bar_ts`, `ict_zones` uses both `detected_at_ts` and `session_bar_ts`, `option_chain_snapshots` uses `ts`, `market_spot_snapshots` uses `ts`, `hist_atm_option_bars_5m` uses `bar_ts`, `script_execution_log` uses `started_at` and `finished_at`. Ad-hoc queries error out frequently with "column ts does not exist" or similar; consumes time iterating through column-discovery queries. |
| **Impact** | Friction on ad-hoc queries during live diagnostics. Real cost: during Session 10 extension, 4 query iterations were needed before getting to working SQL for `hist_spot_bars_1m` — adds up to ~10 minutes of iteration time when troubleshooting under market hours. Also makes Claude/AI sessions less efficient because column names can't be predicted from one table to another. |
| **Workaround** | Always run column-discovery query first when querying a new table: `SELECT column_name FROM information_schema.columns WHERE table_name='X'`. Document common patterns in a Session 11+ schema reference card. |
| **Proper fix** | Aspirational schema-hygiene refactor — standardise on `bar_ts` for time-series bar data, `ts` for snapshot/event data, `created_at`/`updated_at` as sidecars. Would require migrations and code refactors across all readers. Not worth scheduling unless an unrelated migration is happening. |
| **Cost to fix** | ~3-5 sessions for schema migration + reader updates. Cost-benefit not favourable for now. |
| **Blocked by** | nothing — but not a priority |
| **Owner check-in** | 2026-04-27 |

---

### TD-038 — `hist_spot_bars_5m` has no `is_pre_market` column (schema assumption mismatch)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-28 (Session 11 Exp 34 bug B1) |
| **Component** | `hist_spot_bars_5m`, any research script querying it |
| **Symptom** | Scripts that filter `.eq("is_pre_market", False)` raise `APIError 42703: column does not exist`. First hit: Exp 34 initial run returned 0 events because the Supabase query failed silently. |
| **Root cause** | The column `is_pre_market` does not exist in `hist_spot_bars_5m`. Pre-market exclusion must be done by filtering `bar_ts` to session hours (09:15–15:30 IST). |
| **Workaround** | Filter by time: `WHERE EXTRACT(HOUR FROM bar_ts AT TIME ZONE 'Asia/Kolkata') * 60 + EXTRACT(MINUTE ...) BETWEEN 555 AND 930`. In Python (with TD-029 workaround applied): filter post-fetch using `9*60+15 <= bar_minutes(dt) <= 15*60+30`. |
| **Proper fix** | Either (a) add `is_pre_market` column as a computed boolean on insert, or (b) document the absence in `merdian_reference.json` tables entry and ensure all scripts use time-based filtering. Option b is lighter. |
| **Cost to fix** | <0.5 sessions for option b. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-28 |

---

### TD-039 — `hist_pattern_signals.ret_30m` stored as percentage points, not decimal fraction

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-28 (Session 11 Exp 41 — ret_30m inflated by 100x, corrected in Exp 41B) |
| **Component** | `hist_pattern_signals` table, `ret_30m` and `ret_60m` columns |
| **Symptom** | Any script that uses `ret_30m` as a decimal fraction (multiplying directly by spot price) gets numbers 100x too large. Exp 41 showed SENSEX E4 EV = −11,649 pts per trade, clearly impossible. |
| **Root cause** | `ret_30m` is populated as a percentage (e.g., 0.1351 = 0.1351% move, not 13.51%). The schema comment or docs do not make this explicit. |
| **Workaround** | Divide `ret_30m` by 100 before using as a decimal fraction. Sign convention: BEAR_OB wins when `ret_30m < 0` (spot fell). BULL_OB wins when `ret_30m > 0`. Codified in CLAUDE.md Rule 14. |
| **Proper fix** | Either (a) update all writers to store as decimal fraction (breaking change to any existing consumers), or (b) rename column to `ret_30m_pct` to make the unit explicit in the schema. Option b is safer. Also add column comment in Supabase: `COMMENT ON COLUMN hist_pattern_signals.ret_30m IS 'Spot return in percentage points (divide by 100 for fraction)'`. |
| **Cost to fix** | <0.5 sessions for option b + comment. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-28 |

---

> **Session 14 TDs (TD-040 through TD-047) noted in `session_log.md` line 1 are not yet filed in this register.** Historical gap — their content lives in the Session 14 one-liner. Backfill in a future operational session is OPEN. Session 15 TDs below resume at TD-048.

---

### TD-048 — *(see Resolved section — CLOSED Session 15: BEAR_FVG defect across detector pipeline)*

The numeric ID TD-048 is reserved for the BEAR_FVG defect closed in Session 15. Full entry lives in **Resolved (audit trail)** below since it was opened and closed within the same session. Cross-referenced here for ID continuity.

---

### TD-049 — D-OB detector uses non-standard ICT definition (D timeframe only)

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced during code review of `build_ict_htf_zones_historical.py` for the BEAR_FVG defect; consolidates "TD-S2.a" working name from Session 15 closeout) |
| **Component** | `detect_daily_zones()` in both `build_ict_htf_zones.py` and `build_ict_htf_zones_historical.py` |
| **Symptom** | D-OB detector marks the prior bar K+1 (the move bar itself) as the OB. Standard ICT defines an OB as the LAST opposing-color candle BEFORE the displacement (i.e., bar K, not K+1). W-OB in `detect_weekly_zones()` uses the standard ICT definition; D-OB does not. Inconsistent across timeframes within the same script. |
| **Root cause** | Detector logic in `detect_daily_zones()` checks `prior_move >= OB_MIN_MOVE_PCT` and writes the prior bar itself as the OB zone. Should look back one further bar to find the last opposing-color candle. Carried forward from initial Phase-1 implementation. |
| **Workaround** | None. The system uses the current (non-standard) D-OB definition. Symptom: D BEAR_OB candidates fire ~6 expected per Session 15 manual replay vs 1-2 actual = false negatives at standard ICT criterion. |
| **Proper fix** | Change D-OB detector to standard ICT definition (find K-1 = last opposing-color bar before K = displacement bar). Decision required: (a) re-run full historical backfill on `hist_ict_htf_zones` after fix (invalidates 118 BULL + 135 BEAR D-OB rows from Session 15 backfill), or (b) ship for new detections only and document version boundary. Recommendation: option (a) since backfill cost is ~5 minutes (proven during Session 15). |
| **Cost to fix** | <1 session for code + retroactive backfill. |
| **Blocked by** | nothing — investigation can run any time. Operator decision needed on retroactivity. |
| **Owner check-in** | 2026-05-02 |

---

### TD-050 — D-zone non-FVG validity = 1 day (single-session expiry)

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced during ADR-003 Phase 1 v2 investigation when "0 D zones in 10-day lookback" pointed at validity bug; consolidates "TD-S2.b") |
| **Component** | `detect_daily_zones()` in both `build_ict_htf_zones.py` and `build_ict_htf_zones_historical.py` (D-OB and D PDH/PDL specifically — D BULL_FVG / D BEAR_FVG were given 5-day validity in the Session 15 S1.b patch via `D_FVG_VALID_DAYS=5`) |
| **Symptom** | D-zone non-FVG validity = exactly 1 day (`valid_from = valid_to = target_date`). D zones effectively expire by next session. ADR-003 Phase 1 v2 saw 0 D zones in 10-day lookback because each D zone's `valid_to < lookback_start_date`. Same root pattern as previously-documented H-zone single-day-validity bug (line 53 H zones, all single-day, all EXPIRED). |
| **Root cause** | Hardcoded `valid_to = target_date` in detector, written when D zones were considered ephemeral. Whether 1-day validity is intentional or unintentional has never been documented. |
| **Workaround** | None. Downstream consumers (signal builder, `detect_ict_patterns_runner.py`) querying `valid_from <= today AND valid_to >= today` see D-OB / D PDH / D PDL only on the day of detection, not subsequent days. |
| **Proper fix** | Decide: (a) extend D-zone non-FVG validity to N days (e.g., 2-5 like the new D-FVG validity), OR (b) document 1-day as intentional and adjust downstream consumers to use a different date filter (e.g., look up most recent ACTIVE zone). |
| **Cost to fix** | <1 session for either path. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-02 |

---

### TD-051 — PDH/PDL `+/-20` band hardcoded, symbol-agnostic

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced during code review for BEAR_FVG defect; consolidates "TD-S3.a") |
| **Component** | `detect_weekly_zones()` and `detect_daily_zones()` in both builders. Live `detect_1h_zones()` for session-high/session-low PDH-PDL also uses `+/- 10` (separate constant) |
| **Symptom** | PDH/PDL zones get `zone_high = level + 20`, `zone_low = level - 20` regardless of symbol. NIFTY at ~24,000 → 20pt = ~0.083%. SENSEX at ~80,000 → 20pt = ~0.025%. SENSEX PDH/PDL zones are 3.2x narrower in % terms. 1H session-high/low uses `+/- 10` which is even more asymmetric. |
| **Root cause** | Hardcoded `+/- 20` constant in both builders' D and W detection blocks; `+/- 10` in 1H detector. Single literal, no symbol-conditional logic. |
| **Workaround** | None. Live trading is asymmetric across symbols at this PDH/PDL level. May be acceptable (band is small relative to zone width for OB/FVG zones used as primary structure) but worth quantifying before deciding. |
| **Proper fix** | Replace with `+/- (level * BAND_PCT)` where `BAND_PCT` is a config constant per timeframe (e.g., 0.05% W/D = NIFTY ~12pt / SENSEX ~40pt). Audit downstream consumers (TIER assignment in `detect_ict_patterns.py`, signal generation `APPROACH_PCT` interactions in `build_hist_pattern_signals_5m.py`) before patching — band changes may shift TIER thresholds. |
| **Cost to fix** | <1 session for code; ~1 session for downstream audit. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-02 |

---

### TD-052 — Zone status workflow: write-once, never-recompute (historical builder only)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced during ADR-003 Phase 1 v2 investigation when status filter on `hist_ict_htf_zones` was a no-op; consolidates "TD-S3.b") |
| **Component** | `build_ict_htf_zones_historical.py` (live `build_ict_htf_zones.py` is correct: `recheck_breached_zones` updates status — verified in Session 15 code review) |
| **Symptom** | Historical builder writes `status='ACTIVE'` once per zone and never recomputes. ADR-003 Phase 1 v2 filtered on `status='ACTIVE'` and the filter was a no-op (every historical zone is ACTIVE because no recheck logic exists in the historical builder). Total `hist_ict_htf_zones.status='ACTIVE'` post-Session-15-backfill = 40,384 = 100% of rows. |
| **Root cause** | By-design absence of recheck logic in the historical builder. The no-lookahead audit invariant says: as-of-date snapshot of `hist_ict_htf_zones` must NOT be polluted by future price action. The historical builder honours this by never recomputing status. The implication — that `status` is meaningless on `hist_ict_htf_zones` — is undocumented. |
| **Workaround** | Don't filter on `status` in queries against `hist_ict_htf_zones`. Compute breach manually using `hist_spot_bars_5m` per query (more expensive but correct and respects no-lookahead). Live `ict_htf_zones` queries can use `status` correctly. |
| **Proper fix** | Either: (a) add a separate `historical_zone_status_at(zone_id, as_of_date)` view/function that joins zones with subsequent bars to derive status as-of any date — preserves no-lookahead invariant in source table, OR (b) document that `status` field on `hist_ict_htf_zones` is meaningless and add a CHECK constraint or column comment. Recommendation: (b) for documentation cost, then (a) when a query genuinely needs status (none currently). |
| **Cost to fix** | <1 session for documentation-only; 1-2 sessions for view+function approach. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-02 |

---

### TD-053 — CLAUDE.md Rule 16 needs era-aware addendum (post-04-07 era)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced via ADR-003 Phase 1 v2 + Exp 44 + `diagnostic_bar_coverage_audit_v2.py`; consolidates "TD-NEW-RULE16-ERA-AWARE") |
| **Component** | `CLAUDE.md` Rule 16 (TZ handling guidance for `bar_ts`); affects every repo script that applies the rule |
| **Symptom** | Rule 16 says: apply `replace(tzinfo=None)` to bar_ts and filter to in-session 09:15-15:30. This is correct for pre-04-07 era (bars stored as IST-labelled-as-UTC, the "TD-029 era"). Post-04-07 era stores bars as true UTC. Applying Rule 16 verbatim post-04-07 produces a UTC clock-time and filtering to 09:15-15:30 IST drops most of the day (~9 bars vs ~76 bars per session). Hits any script analysing post-04-07 data with verbatim Rule 16. |
| **Root cause** | Rule 16 was written when only the pre-04-07 era existed. Post-04-07 era introduced 2026-04-07 was not retroactively documented in Rule 16. **Related:** TD-029 (the underlying TZ-stamping bug that created the era boundary). |
| **Workaround** | Era-aware: pre-04-07 use `replace(tzinfo=None)`; post-04-07 use `astimezone(IST_TZ)`. Verified in `diagnostic_bar_coverage_audit_v3.py` which avoids the issue entirely by filtering on `trade_date` column instead of bar_ts time. |
| **Proper fix** | Edit `CLAUDE.md` Rule 16 to add era boundary at 2026-04-07 with code snippet for both eras. Audit all repo scripts that apply Rule 16 verbatim and patch them. Affected scripts identified in Session 15: ADR-003 Phase 1 (v1, v2 INVALID), `experiment_44_inverted_hammer_cascade.py` (verdict survives caveat re-evaluation but v2 re-run cleaner). |
| **Cost to fix** | <1 session for CLAUDE.md edit; ~1 session for repo audit + patches. |
| **Blocked by** | nothing — operator can edit CLAUDE.md anytime; audit can run any session |
| **Owner check-in** | 2026-05-02 |

---

### TD-054 — `ret_60m` column is uniformly 0 in `hist_pattern_signals`

| | |
|---|---|
| **Severity** | S2 (raised from S3 Session 16 — extended scope: column has only 4.7-5.0% agreement with locally-computed forward return across 3 cohorts now, 30% NULL — invalidates any analysis using `ret_30m` directly) |
| **Discovered** | 2026-05-01 (Session 15 — surfaced when Exp 47 review showed `ret_60m` 0.000% across all rows; consolidates "TD-NEW-RET60M"). 2026-05-03 (Session 16) extended scope: `ret_30m` column on same table also broken, not just `ret_60m`. Local re-derive on 3 separate cohorts (Exp 41, Exp 50 v2, ADR-003 Phase 1 v3 indirectly) shows 5% agreement with locally-computed forward return. |
| **Component** | `build_hist_pattern_signals_5m.py` and possibly upstream `hist_market_state` source |
| **Symptom** | `ret_60m` column in `hist_pattern_signals` is 0.000% across every single row — verified Session 15 in Exp 47b output and Exp 50 output. Session 16 expanded: `ret_30m` also unreliable — 4.7% agreement (24/509) with locally-computed forward return on Exp 41 cohort, 5.0% (81/1611) on Exp 50 v2 cohort, 30-35% NULL across both. Any experiment using `ret_30m` sign or magnitude as outcome metric gets noise. |
| **Root cause** | Most likely both columns are computed with broken or stale logic in the signal builder, OR the source `hist_market_state` columns are themselves broken. Not yet diagnosed. |
| **Workaround** | **Do not use `ret_30m` or `ret_60m` columns from `hist_pattern_signals` as outcome metrics.** Compute forward return locally from `hist_spot_bars_5m` using Exp 41 mechanics (Rule 20 era-aware): join signal `bar_ts` to spot bars, find bar at signal_ts and signal_ts + 30/60 minutes, compute `(close_t30 - close_t0) / close_t0 * 100`. Used by every Session 15-16 experiment that needed forward returns. More expensive but correct. |
| **Proper fix** | Diagnose: (a) check `hist_market_state.ret_60m` for population (run a SELECT DISTINCT, MIN, MAX, COUNT against the column). If null/zero, fix at source. If populated correctly there, the signal builder isn't reading it — patch the signal builder to read and forward. Same diagnosis for `ret_30m`. (b) Backfill all `hist_pattern_signals` rows after fix via signal rebuild. **OR**, per ENH-87 (Session 16 filed): consider deprecating `hist_pattern_signals` entirely — Session 16 demonstrated that live-detector replay (`experiment_15_with_csv_dump.py` pattern) provides equivalent research utility without the integrity issues. Decision deferred to Session 17/18. |
| **Cost to fix** | <1 session diagnostic, ~1 session for fix + backfill if pursued. ENH-87 deprecation alternative: 2-3 sessions to migrate downstream consumers. |
| **Blocked by** | ENH-87 (deprecation review) — recommend deciding fix-vs-deprecate before fixing. |
| **Owner check-in** | 2026-05-03 (Session 16 — extended scope, locally-computed workaround in active use); 2026-05-10 (Session 26 — confirmed orthogonal to TD-101 live-side fix). |
| **Cross-reference TD-101** | TD-101 fixed the LIVE-side `momentum_snapshots.ret_session` writer (`build_momentum_features_local.py::get_session_open_spot()` unbounded-query OI-18 anti-pattern). TD-054 is the RESEARCH-side `hist_pattern_signals.ret_30m` / `ret_60m` columns broken by separate writer (`build_hist_pattern_signals_5m.py` and possibly `hist_market_state` source). The two bugs are in different code paths writing different tables; the live fix does not auto-resolve the research-side defect. Locally-computed forward-return workaround per Session 15-16 experiments remains in active use for any analysis on `hist_pattern_signals`. TD-054 status unchanged: defer fix-vs-deprecate decision per ENH-87 (deprecation review). |

---

### TD-055 — `ret_eod` column entirely absent from `hist_pattern_signals`

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced when Exp 50 setup tried to compute EOD outcome; consolidates "TD-NEW-RETEOD") |
| **Component** | `build_hist_pattern_signals_5m.py` schema; `hist_pattern_signals` table schema |
| **Symptom** | `ret_eod` column does not exist on `hist_pattern_signals`. EOD analysis on this table alone is impossible — every EOD-outcome experiment must JOIN to `hist_spot_bars_5m` and compute the session-end forward return per row. |
| **Root cause** | Column was never added to schema. Existing forward-return columns are `ret_30m` (TD-039: stored as percentage points) and `ret_60m` (TD-054: zeros). |
| **Workaround** | Compute EOD outcome from `hist_spot_bars_5m` directly (or from the daily OHLCV close vs signal-bar close). Used in this form by Session 15 experiments (Exp 44 horizons, ADR-003 Phase 1). |
| **Proper fix** | (a) `ALTER TABLE hist_pattern_signals ADD COLUMN ret_eod NUMERIC(10,6);` (decimal-fraction this time per TD-039 lesson — name it `ret_eod_pct` to match unit-explicit convention from TD-039 proper-fix path). (b) Patch `build_hist_pattern_signals_5m.py` to compute it from session-end bar (15:25 IST, idx -1 of session). (c) Backfill via signal rebuild. |
| **Cost to fix** | 1 session including schema migration, code, backfill, verification. |
| **Blocked by** | TD-039 (column-naming convention decision affects this) — recommend coordinating both fixes. |
| **Owner check-in** | 2026-05-02 |

---

### TD-056 — Signal-detector bull-skew across BOTH code paths (5m batch AND 1m live)

| | |
|---|---|
| **Severity** | S2 (raised from S3 Session 16 — confirmed structural across both detector code paths, not just 5m batch) |
| **Discovered** | 2026-05-02 (Session 15 — surfaced post-BEAR_FVG fix verification on `hist_pattern_signals` 5m batch); 2026-05-03 (Session 16 — Section 17 of `analyze_exp15_trades.py` confirmed live `detect_ict_patterns.py` 1m cohort also bull-skewed; not a 5m-batch-specific artefact) |
| **Component** | BOTH (a) `build_hist_pattern_signals_5m.py` zone-approach filter logic, AND (b) `detect_ict_patterns.py` live 1m detector. Both are bull-skewed independently. |
| **Symptom** | **5m-batch (`hist_pattern_signals`)**: NIFTY 60d signals BULL_FVG 274 / BEAR_FVG 150 (1.83x). NIFTY DOWN regime alone: 112 BULL_FVG / 20 BEAR_FVG = **5.60x bull-skew in DOWN regime**. SENSEX DOWN: 2.30x. **1m-live (`detect_ict_patterns.py` running through Exp 15)**: full year 49 BULL_OB / 25 BEAR_OB pooled. NIFTY DOWN regime: 23 BULL_OB / 7 BEAR_OB = **3.29x**. SENSEX DOWN: 1.50x. Plus: **live detector emits ZERO BEAR_FVG signals across full year**, despite Session 15's `build_ict_htf_zones.py` BEAR_FVG fix (separate issue, see TD-058). Canonical 5m BEAR_FVG / BULL_FVG shapes in `hist_spot_bars_5m` are essentially symmetric (NIFTY 562 BEAR / 587 BULL; SENSEX 567 / 575) — both detector paths underemit BEAR signals relative to raw price-structure availability. |
| **Root cause** | Two non-mutually-exclusive hypotheses: **(H1) zone-availability asymmetry** — the "in or near zone with proximity" filter requires same-direction zones to exist near current price; in an uptrending market BULL zones above-spot are more available than BEAR zones below-spot, so the filter naturally tags more BULL signals. **(H2) detector-symmetry bug** — code paths for BULL vs BEAR detection differ in some non-obvious way (e.g., asymmetric proximity, asymmetric validity windows, missing branch). Session 16 evidence supports H1 partially (bull-skew ratio higher in 5m-batch which has zone-availability filter at signal time, lower in 1m-live which has its own zone construction) but does not fully exonerate H2 (bull-skew persists in DOWN regime where H1 alone would invert the ratio). Mechanism investigation deferred to Session 17 Priority C. |
| **Workaround** | None automated. Operationally: live trading sees more BULL setups than BEAR setups as a result. Operator-side mitigation: **be more discretionary about looking for bear setups in chop/down sessions**, especially when MERDIAN isn't flagging them — the system undersignals bear opportunities, not because individual BEAR signals are wrong (they're 92% WR on the live cohort) but because there are fewer of them than market structure would imply. |
| **Proper fix** | **Phase 1 — mechanism diagnosis (Session 17 Priority C, ~1-2 sessions investigation):** code review `detect_ict_patterns.py` for asymmetric BULL/BEAR branches (proximity computation, validity, opt_type mapping); code review `build_hist_pattern_signals_5m.py` zone-approach filter for direction-asymmetric thresholds; instrument both with detection-attempt counters by direction to measure where BEAR candidates are being filtered out. **Phase 2 — patch (1 session if H2 confirmed, 0 sessions if H1 only):** if asymmetric branch identified, patch and re-verify. If H1 only, document as regime-driven and accept (or rebalance proximity threshold per direction). |
| **Cost to fix** | 1-3 sessions total (Phase 1 + optional Phase 2). |
| **Blocked by** | TD-058 (BEAR_FVG live emission — likely shares root cause with TD-056 H2). Recommend coordinating both investigations. |
| **Owner check-in** | 2026-05-03 (Session 16 — confirmed structural, not 5m-batch-specific; Phase 1 deferred to Session 17 Priority C) |

---

### TD-057 — Exp 15 framework provenance gap (no findable execution audit trail)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-03 (Session 16 — surfaced during framework audit when stress-testing Compendium claims) |
| **Component** | `experiment_15_pure_ict_compounding.py`, `MERDIAN_Experiment_Compendium_v1.md` (Exp 15 entry dated 2026-04-12), git history |
| **Symptom** | The only execution log of `experiment_15_pure_ict_compounding.py` on disk is from 2026-04-11 21:40:35, 427 bytes, showing `SyntaxError: unterminated f-string literal at build_ict_htf_zones.py L475`. The script crashed at import. Compendium entry for Exp 15 dated **one day later** (2026-04-12) reports detailed per-pattern findings (BEAR_OB N=36 94.4% WR, BULL_OB N=44 86.4% WR, BULL_FVG N=155 50.3% WR, BULL_OB MEDIUM 90% WR N=45). Recursive search of `C:\GammaEnginePython\logs\` found no successful execution log of this exact script anywhere. `portfolio_simulation_v2.log` from same evening (21:47:10) is a different experiment with different exit rules and no per-pattern WR aggregates. Three possibilities: (a) script rerun successfully post-fix and log deleted/never persisted, (b) numbers from interactive output captured to clipboard not log, (c) numbers from different script attribution. Plus: April-13 commit `c78b6ea` modified BOTH `experiment_15_pure_ict_compounding.py` AND `detect_ict_patterns.py` together, including silent MTF tier relabeling — pre-Apr-13 vocabulary (HIGH=W, MEDIUM=D, LOW=none) became post-Apr-13 (VERY_HIGH=W, HIGH=D, MEDIUM=H, LOW=none). The Apr-12 Compendium uses post-Apr-13 vocabulary to describe pre-Apr-13 measurements. The "1H zones confirmed Established V18F" claim in `merdian_reference.json` rests on this relabeling. |
| **Root cause** | Combination of: (a) interactive-shell run pattern at the time (no automatic log capture), (b) git commits modifying experiment scripts and detector code together with non-descriptive commit messages making provenance hard to reconstruct, (c) Compendium written from session-end state rather than from durable execution artefacts. Not a defect in any single component — an aggregate of process-hygiene gaps. |
| **Workaround** | Session 16 produced `experiment_15_with_csv_dump.py` as a verbatim methodology copy of the original with a CSV-dump tail that produces a durable trade-list artefact (`exp15_trades_<stamp>.csv`). Future research that depends on Exp 15 results uses the CSV pattern, not direct re-attribution to the Apr-12 Compendium claims. Critically: **Session 16 full-year run replicated the Compendium headlines within 2-3pp** (BEAR_OB 92.0% vs claimed 94.4%, BULL_OB 83.7% vs 86.4%, BULL_FVG 50.3% vs 50.3%) — so the published numbers, while audit-traceless, are not refuted. |
| **Proper fix** | (a) Going forward: every experiment must be invoked with `... 2>&1 \| Tee-Object -FilePath <log>` (already in canonical session pattern). (b) Every Compendium entry must cite the execution log path and git commit hash from which findings were derived. (c) Major published findings should be re-runnable in <30 min with current code; if they aren't, the methodology has drifted. (d) Apr-12-era Compendium entries should be flagged as "vocabulary aligned to post-Apr-13 MTF relabeling" so future readers don't conflate "MEDIUM" across the boundary. |
| **Cost to fix** | Going-forward fix is process-only (zero code, zero compute). Retroactive flagging of Apr-12-era entries: 0.5 session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-03 |

---


### TD-059 — ENH-37 MTF context hierarchy inverted from claim (LOW outperforms HIGH on OB patterns)

| | |
|---|---|
| **Severity** | S2 (production sizing rule rests on inverted assumption — currently BOOSTING confidence on cells that empirically UNDERPERFORM) |
| **Discovered** | 2026-05-03 (Session 16 — Section 10 of `analyze_exp15_trades.py` per-cell confidence intervals on N=231 live-cohort trades) |
| **Component** | `build_trade_signal_local.py` (consumes `mtf_context` from `signal_snapshots`); `detect_ict_patterns.py` `get_mtf_context` (computes the tier label); ENH-37 documentation in Enhancement Register |
| **Symptom** | Exp 15 published Compendium claim: "MEDIUM context (1H zone) ADDS edge — keep in MTF hierarchy." Session 16 measurement on 231-trade live cohort with Wilson 95% CIs: **BULL_OB|HIGH (D zone) 71.4% N=7, BULL_OB|MEDIUM (H zone) 81.8% N=11 [52.3, 94.9], BULL_OB|LOW (no zone) 87.1% N=31 [71.1, 94.9]**. **BEAR_OB|HIGH 71.4% N=7, BEAR_OB|MEDIUM 100% N=1, BEAR_OB|LOW 100% N=17 [81.6, 100]**. LOW context outperforms HIGH on BOTH BULL_OB and BEAR_OB. The hierarchy current production code applies (HIGH = high confidence, LOW = low confidence) is **inverted from current-code measurement**. (Note: current vocabulary differs from Apr-12 Compendium — see TD-057 — but even using current vocabulary on current data, the hierarchy is wrong.) |
| **Root cause** | Hypothesis: when a signal triggers in HIGH context (inside a daily zone), the price action is contested — buyers and sellers are both engaged at a known level. The "trade against the zone" logic plays out, but with chop and reduced edge. When a signal triggers in LOW context (no archive-zone confluence), price is in clean expansion — the OB pattern catches a moving market with directional follow-through. Effectively, archive zones may CAUSE the chop they're supposed to identify. Untested hypothesis but consistent with the data. |
| **Workaround** | Operationally for now: **treat MTF context tier as informational, not as a confidence multiplier.** When operator sees a BULL_OB or BEAR_OB on TradingView, do not size up just because it's tagged HIGH context. The pattern itself is the edge; the context tier is currently misleading. |
| **Proper fix** | Three options for Session 18+ to evaluate: **(a) Remove MTF context as a confidence multiplier** — keep as an informational annotation but don't let it affect sizing or tier classification. **(b) Invert it** — LOW becomes "high confidence" in production scoring. Risky without more data; current N=17-31 per cell is enough for direction but not for magnitude. **(c) Run shadow mode with both rules** — keep current production rule live, run alternative rule in shadow, log signal_snapshots with both `confidence_score_v1` (current) and `confidence_score_v2` (alternative) for 4-8 weeks, then compare. Recommend (c) — measure before changing production. |
| **Cost to fix** | (a) ~0.5 session (annotation-only change). (b) ~1 session (invert + verify nothing else depends on the tier ordering). (c) ~1 session to wire shadow mode + 4-8 weeks of measurement + 1 session to decide and ship. |
| **Blocked by** | TD-057 (vocabulary alignment) — fix should clearly state which MTF vocabulary is canonical (Apr-12 vs Apr-13+) before redesigning. |
| **Owner check-in** | 2026-05-03 |

---

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| Hand-patching files on AWS to fix something fast | Creates Local↔AWS drift, no audit trail | Use BREAK_GLASS protocol; doc in Change Protocol Step 8 |
| `print()` left in production code | Pollutes logs; hides real signals | Pre-commit Step 1.5 catches this |
| Hardcoded Windows paths in files destined for AWS | Breaks AWS run silently | Pre-commit Step 1.5 catches this |
| Patch script (`fix_*.py`) without `ast.parse()` validation | Invalid syntax shipped, found at market open | Standing rule (CLAUDE.md #5) — ast.parse every patch |
| Creating a new `OI-N` ID | Register is closed | Use this file (TD-N), ENH-N, or C-N |
| Pasting full master into session | Burns context window, dilutes focus | Targeted JSON lookup per Session Mgmt Rule 4 |
| Mixing concerns in one session | Accelerates context degradation | Split sessions per Session Mgmt Rule 3 |

---

## Resolved (audit trail)

> Closed items live here forever. Never delete — they are evidence of work done and decisions made.

### TD-NEW-2 (closed) — `flip_level` regression: stuck at ~21,250 due to spurious deep-ITM CE gamma from Dhan

| | |
|---|---|
| **Filed** | 2026-05-11 (Session 27 — discovery via Phase 0a §3 sign-convention audit Q3 stuck-flip diagnostic across 30-day NIFTY lookback) |
| **Closed** | 2026-05-11 (Session 27 same-session — third same-session NEW+RESOLVED pattern after TD-097 S25 + TD-101 S26) |
| **Closing commit** | `241f943` |
| **Severity at filing** | S1 (production gamma engine writing meaningless flip values for 3+ trading days; ENH-35 LONG_GAMMA gate consumes these values; impacts live trading signals on every cycle 2026-05-08 onwards) |
| **Component** | `compute_gamma_metrics_local.py::signed_gamma_exposure()` (input layer) + `compute_gamma_metrics_local.py::compute_flip_level()` (algorithm layer). Primary live writer of `gamma_metrics.flip_level`. |
| **Discovery path** | Session 27 began with ADR-002 v2 step-3 first sequencing (sign audit before refinement before adoption). Audit pulled 3 reference cycles from source-material dashboard screenshots (Apr 28 12:21 IST clean pin, Apr 28 12:23 IST flip-edge stress, Apr 30 ~10:50 IST cascade warning) for MERDIAN-vs-source comparison. MERDIAN's `flip_level` at Apr 30 ~10:50 IST showed 24,218-24,263 across 4 cycles while source dashboard read flip at 23,877 (370-pt gap). Diagnostic Query 1 (flip-stuck hourly distribution across 30 days) revealed 2026-05-08 and 2026-05-11 had 95%+ of rows with `flip_level` clustered at 21,250.05 across multiple distinct intraday cycles, while every prior session (2026-04-01 through 2026-05-07) showed 11-119 distinct flip values per day with operationally reasonable ranges (mostly 22,000-25,000). Regression window narrowed to 2026-05-07 09:00 UTC → 2026-05-08 03:00 UTC. **Cutoff diagnosis ruled out code regression** (no Session 26 commits touched gamma compute pipeline). Diagnostic Query Apr-28-vs-May-08 inspection of `option_chain_snapshots` deep-strike rows 21,000-22,000 revealed Dhan started returning `gamma=0.00007` at strike 21,250 CE on 2026-05-08 (oi=130, spot ~24,200). For deep-ITM CE with delta≈1, gamma should be near zero; 70× ATM gamma is impossible for a legitimate ITM option. Additional spurious values at strikes 21,500 CE (gamma=0.000025), 22,000 CE (gamma=0.0000109) confirmed multiple bad rows. **Latent algorithm fragility surfaced by input-shape change**, not a code regression. |
| **Symptom** | `gamma_metrics.flip_level` stuck at 21,250.05 (or 21,200-21,254 narrow band) across 95%+ of intraday cycles on 2026-05-08 + 2026-05-11. Spot ~24,200 across same window → `flip_distance_pct` resolves to ~12% (3,000+ pts from spot), placing every cycle deep into LOW_GAMMA zone per `determine_gamma_zone()` thresholds (<0.5%=HIGH, <1.5%=MID, ≥1.5%=LOW). Operational flip should be within ~1-2% of spot during normal market structure. Production `gamma_zone` field LOW_GAMMA across the broken window contributes to ENH-35 gate decisions on every signal cycle. |
| **Root cause** | Two-layer fragility. **Layer 1 (input)**: `signed_gamma_exposure()` accepted all rows from Dhan unconditionally (only rejected `gamma == 0.0 or oi <= 0.0 or spot <= 0.0`); no sanity guard for impossible-for-deep-ITM gamma values. **Layer 2 (algorithm)**: `compute_flip_level()` walked cumulative GEX bottom-up from `min_strike=17,850` and returned first zero-crossing. When Dhan's spurious deep-ITM CE gamma injects positive contributions at deep strikes where surrounding strikes have legitimately zero contribution (because deep-OTM/deep-ITM options have near-zero legitimate gamma), the running sum crosses zero at the spurious strike's neighborhood and the algorithm returns that as `flip_level` — semantically the "first crossing walking up from min_strike" but operationally meaningless. The algorithm's correctness assumption "deep-strike contributions are small" was data-conditional, not algorithmic — held for entire prior history under Dhan's pre-2026-05-08 response shape, broke when input shape changed. |
| **Fix** | Two-part patch via `fix_td_new_2_flip_level.py` (canonical patch pattern: BOM-safe read via `read_bytes() + decode('utf-8-sig')`, EOL detection + preservation on write via `write_bytes`, `ast.parse()` self-validation before write, `_PRE_TD-NEW-2.py` backup, `_PATCHED.py` output for inspection). **Part A (necessary fix)** modifies `signed_gamma_exposure()` to reject rows where `\|strike-spot\|/spot > 5%` AND `\|gamma\| > 5e-5` (5× typical ATM gamma; well outside legitimate deep-ITM values; reject threshold calibrated against HEALTHY 2026-05-07 data — zero false positives observed in verification). **Part B (algorithm hardening)** modifies `compute_flip_level()` to accept optional `spot` parameter and walk outward from ATM in both directions, returning zero-crossing nearest to spot (operational flip definition). Legacy bottom-up walk preserved as fallback when `spot=None` (backward compatibility for callers that haven't been updated). Three edits applied: `signed_gamma_exposure` body + `compute_flip_level` body + call site at line 605 to pass `spot`. AST OK. |
| **Validation** | Verification harness `verify_td_new_2_flip_level.py` imports PATCHED module via importlib (sys.modules registration required pre-exec_module for `@dataclass` GammaMetricsResult declaration — known importlib + dataclass interaction). Runs pure functions against 2 real `option_chain_snapshots` cycles: **HEALTHY 2026-05-07 04:01:25 IST** — LIVE flip 24,785.97 vs PATCHED flip 24,773.93, delta -12.05pts (0.05%); confirms no regression on clean data, sanity guard threshold well-calibrated. **BROKEN 2026-05-08 04:00:09 IST** — LIVE flip 21,250.05 stuck vs PATCHED flip 25,060.15 near-spot (spot 24,239), delta +3,810pts correction. Both PASS. Also notable: PATCHED `net_gex` on broken cycle dropped from 22T to 2.27T after Part A filtering — multiple bad rows filtered, not just strike 21,250. Renamed PATCHED → canonical via `del compute_gamma_metrics_local.py && ren compute_gamma_metrics_local_PATCHED.py compute_gamma_metrics_local.py`. Backup `compute_gamma_metrics_local_PRE_TD-NEW-2.py` preserved. **Live verification queued for Mon 2026-05-12 09:15 IST first cycle** — SQL `SELECT ts, spot, net_gex, flip_level, regime FROM gamma_metrics WHERE symbol='NIFTY' AND ts > NOW() - INTERVAL '10 minutes'` expects flip_level in 23,000-25,500 range (operational, near spot), not stuck ~21,250. |
| **Honest reframing from smoke test** | Original framing called Part A + Part B "belt + suspenders" — implying defensive redundancy. Smoke test caught important framing correction: Part B alone is **insufficient** against this specific bug pattern. The spurious contribution at strike 21,250 sits in a region where all surrounding strikes have legitimately zero contribution; walk-from-ATM cumulative stays uniformly positive through the bad-row plateau and only dips to zero at the strike below — that's a zero-crossing walk-from-ATM correctly detects, but it's not the operational flip. Honest reframing: **Part A is necessary; Part B is hardening for class-of-future-bugs** (noisy distributed contributions, multiple small spurious values across the chain). Both parts shipped together, but the framing matters for future operator understanding — don't assume defensive equivalence between parts. |
| **Live impact (silent-failure window)** | 2026-05-08 → 2026-05-11 (3 trading days, ~430 cycles per day × 2 symbols ≈ 2,500 cycles total). `flip_level` field stuck at ~21,250 across the window. `flip_distance_pct` field stuck at ~12%. `gamma_zone` field stuck at LOW_GAMMA. ENH-35 LONG_GAMMA gate consumes regime (which is sign-only from `net_gex`, so regime classification was correct) but downstream signal logic that reads `flip_distance_pct` magnitude saw stale values across the window. Backfill of broken-window `gamma_metrics` rows for 2026-05-08 onwards deferred to S28+ as P1 carry-forward (custom script reusing patched compute module, not via `backfill_gamma_metrics.py` which writes to separate `hist_gamma_metrics`). |
| **Replay parity** | `replay/replay_compute_gamma_metrics.py` carries its own copy of `signed_gamma_exposure` + `compute_flip_level` (replay script comment: "All Black-Scholes / pure-function logic unchanged"). Replay file received TD-NEW-3 unit fix in same session but **TD-NEW-2 Parts A+B parity is deferred** to S28+ carry-forward — replay used only for Phase 0b retroactive computation which is ~3-4 sessions away. Replay-vs-live parity restoration is P5 S28 carry-forward. |
| **Lesson (codified as CLAUDE.md B20 + B21)** | **B20**: Phase 0 calibration discipline is justified by its first execution. Sign audit was scoped as 2-hour PASS/FAIL on ADR-002 v2 build path; surfaced TWO production bugs (TD-NEW-2 + TD-NEW-3) that had been writing bad data for 3+ days. Without the audit, ADR-002 v2 build (ENH-80, etc.) would have layered new code atop broken foundation. **B21 (companion to TD-NEW-3)**: unit-scale bugs are silent when all consumers sign-only. Both lessons codified for B19 audit-derived patterns going forward. **Additional codification**: latent algorithm fragility surfaces only under input-shape change — TD-NEW-2 was stable for months against stable input; Dhan response-shape change 2026-05-08 (spurious deep-ITM gamma values where previously zero) exposed fragility that prior data never triggered. Defense-in-depth (Part A input filter + Part B algorithm hardening) is the appropriate response class. |
| **Related** | TD-NEW-3 (same-session sibling — net_gex unit standardisation; both surfaced via same audit), TD-097 (S25 precedent for same-session NEW+RESOLVED pattern), TD-101 (S26 second instance of same-session pattern), ADR-002 v2 §Methodology §3 sign-convention audit (mandate that surfaced this defect), CLAUDE.md B20 + B21 + "ADR-002 v2 ACCEPTED" + "TD-NEW-2 RESOLVED" settled-decisions bullets, Assumption Register §D.10.3 (walk-from-ATM canonical flip definition codified from this resolution). |

---

### TD-NEW-3 (closed) — `net_gex` stored in raw rupees ~10³ too large vs operational Crore convention

| | |
|---|---|
| **Filed** | 2026-05-11 (Session 27 — surfaced during cross-comparison of MERDIAN `net_gex` magnitudes against source-material Cr dashboard values during Phase 0a sign-convention audit) |
| **Closed** | 2026-05-11 (Session 27 same-session — fourth same-session NEW+RESOLVED pattern after TD-097 S25 + TD-101 S26 + TD-NEW-2 (this session)) |
| **Closing commit** | `241f943` |
| **Severity at filing** | S2 architectural (silent unit-scale bug across entire gamma engine deployment history; no live-trading impact because all downstream consumers are sign-only; but blocks any cross-comparison to source-of-truth Cr references and blocks every magnitude-consuming future gate from ADR-002 v2 build sequence) |
| **Component** | Three production writer files with duplicate `signed_gamma_exposure` / `signed_gex` implementations: `compute_gamma_metrics_local.py::signed_gamma_exposure()` (live writer line 110), `replay/replay_compute_gamma_metrics.py::signed_gamma_exposure()` (replay writer line 65), `backfill_gamma_metrics.py::signed_gex()` (historical writer line 82). All three return `gamma * oi * spot²` in raw rupees with no `/1e7` Crore conversion. |
| **Discovery path** | During Phase 0a sign-convention audit (TD-NEW-2 sibling), comparison of MERDIAN `gamma_metrics.net_gex` values against source-material dashboard Cr values (e.g., -976 Cr, -14,323 Cr, +13,003 Cr) showed MERDIAN magnitudes in 10¹²-10¹³ range — clearly off by orders of magnitude. Diagnostic Q3 dividing MERDIAN values by `1e7` produced -1,538,435 Cr on 2026-04-28 cycle — still 10² too large vs expected Cr range. Symmetric diagnostic Q4 across symbols revealed NIFTY avg abs `net_gex` = 22.9T, SENSEX = 9.3T; ratio 2.47× ≈ NIFTY/SENSEX lot ratio 25/10=2.5× confirms lot-size signature consistent (rules out symbol-specific bug). Order-of-magnitude expected calculation: `gamma×OI×spot² × 100 / 1e7` for NIFTY ATM (gamma~0.0001, OI~1M aggregate, spot²~5.76e8) produces ~576 Cr per strike ≈ thousands of Cr aggregated. MERDIAN's 22.9T is ~10³ too large vs expected Cr scale, consistent with missing `/1e7` divisor. |
| **Why this was silent** | Audit of every downstream consumer of `net_gex` field in production codebase (grep across active production scripts, filtering out backups/checkpoints): `compute_gamma_metrics_local.py::determine_regime` line 470 (`net_gex >= 0` sign-only); `compute_gamma_metrics_local.py::compute_expansion_probability` line 447 (`if net_gex < 0` sign-only); `backfill_gamma_metrics.py::determine_regime` line 109 (same sign-only check); `detect_structural_manipulation.py` line 491 (`if net_gex <= 0` sign-only); `build_market_state_snapshot_local.py` (pass-through read forwarding to `market_state_snapshots.net_gex`); `backfill_market_state.py` (pass-through); `build_trade_signal_local.py` line 480 (pass-through forwarding to `signal_snapshots.raw.net_gex`); replay equivalents (mirror of live). **Zero magnitude thresholds in entire reader codebase** — every consumer is sign-only or pass-through. Unit-scale wrong by 10³ is therefore invisible to gate logic. Surfaced only via cross-comparison to source-material Cr references during the sign audit. |
| **Root cause** | Standard practitioner convention for net GEX storage is `gamma × OI × spot² × 100 / 1e7` (rupees scaled to Crore for operational legibility). MERDIAN's `signed_gamma_exposure` (and parallel `signed_gex` in backfill) returned `gamma × oi × spot²` raw — missing the Crore conversion. Storage column `gamma_metrics.net_gex` was labeled with implied Cr semantics (operator dashboards expect Cr values; ADR-002 v2 Positioning Landscape specs all values in Cr) but never actually stored as Cr. Bug present since gamma engine first deployment; never surfaced because no consumer checked magnitude. |
| **Fix** | Patch script `fix_td_new_3_net_gex_unit.py` applies `/1e7` to `base` calculation in all three writer files identically. Edit text precisely matched per file (whitespace conventions differ between files — canonical files use `base = gamma * oi * (spot ** 2)` with spaces; backfill uses compact `base=gamma*oi*(spot**2)`). Each file: read with BOM-safe `decode('utf-8-sig')`, EOL detected (compute_gamma_metrics_local.py=LF, replay=CRLF, backfill=LF) and preserved on write via `write_bytes`, `ast.parse()` self-validation before write, `_PRE_TD-NEW-3.py` backup per file, `_PATCHED.py` output for inspection. Note: `compute_gamma_metrics_local.py` already carried TD-NEW-2 Parts A+B at time of TD-NEW-3 patch (sequential application same session); backup chain `_PRE_TD-NEW-2.py` (pre-TD-NEW-2 state) + `_PRE_TD-NEW-3.py` (post-TD-NEW-2 / pre-TD-NEW-3 state) preserves full history. |
| **Validation** | Verification harness `verify_td_new_3_net_gex_unit.py` (mirrors TD-NEW-2 harness pattern — importlib with sys.modules registration for dataclass) runs `compute_net_gex` on real 2026-05-11 04:00:09 IST cycle. **LIVE pre-patch**: `net_gex` = 775,285,881,741 (raw rupees in `gamma_metrics` column). **PATCHED**: `net_gex` = 78,544.84 (Crore from patched compute). Ratio LIVE/PATCHED = 9,870,615 ≈ 10,000,000 (98.7% of expected 1e7, within 5% tolerance — the 1.3% deviation traces to TD-NEW-2 Part A filter rejecting some bad rows in the patched compute that were included in the raw LIVE total, not to unit-conversion math). Both decision criteria PASS: ratio ~1e7, Crore value in operational range (100 < |x| < 1M Cr). Renamed three PATCHED → canonical via PowerShell `del ... && ren ...` sequence. All backups preserved. |
| **Live impact** | Zero — all downstream consumers sign-only. No gate behavior change. Only display/audit value change: `gamma_metrics.net_gex` column from S28 09:15 IST onwards stores Cr (operationally legible numbers in thousands-of-Cr range), dashboards will display sane values, future magnitude-consuming gates from ADR-002 v2 build sequence have correct unit baseline. |
| **Backfill scope** | `gamma_metrics` rows from full deployment history through 2026-05-11 are stored in raw rupees. Going forward (Mon 2026-05-12 09:15 IST onwards) writes Cr. Two unit conventions coexist in the table — a `WHERE ts >= '2026-05-12'` filter or a transformation column would be needed for any historical-Cr cross-comparison. Backfill is **P1 S28 carry-forward** along with TD-NEW-2 broken-window backfill — both bundled (cost amortization) — via custom script reusing patched compute module. Estimated 30-60 min. |
| **Replay parity** | Replay file received this TD-NEW-3 unit fix in same session. TD-NEW-2 Parts A+B replay parity is deferred to S28+ (separate carry-forward) — replay used only for Phase 0b retroactive computation which is ~3-4 sessions away. |
| **Lesson (codified as CLAUDE.md B21)** | Unit-scale bugs are silent when all consumers are sign-only. TD-NEW-3 had been writing 10³-too-large values since the gamma engine first deployed; never surfaced because no gate threshold consumed magnitude. Surfaced only via cross-comparison to source-material Cr references during the sign audit. **B21 rule**: when introducing magnitude-consuming gates, audit existing column unit conventions FIRST against source-of-truth references, before threshold tuning. Otherwise threshold values get fitted against meaningless internal-only numbers and become invisible to external operator interpretation. ADR-002 v2 build sequence (ENH-81 force scenarios in Cr, ENH-84 RR ratio, λ-score) would have ingested wrong-unit baseline if this bug had not been caught pre-build. |
| **Related** | TD-NEW-2 (same-session sibling — flip_level regression; both surfaced via same Phase 0a audit), TD-097 (S25 precedent for same-session NEW+RESOLVED), TD-101 (S26 second instance), ADR-002 v2 §Methodology §3 sign-convention audit + §Schema Crore unit requirement for all scalars, CLAUDE.md B21 + "TD-NEW-3 RESOLVED" settled-decisions bullet, Assumption Register §D.10.4 (Crore canonical unit codified from this resolution). |

---

### TD-NEW-13 (closed) — Python 3.10 `fromisoformat()` rejects non-3/6-digit microsecond fractions

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced during P1 broken-window backfill retry after TD-NEW-12 + TD-NEW-4 patches landed; 60/587 cycles failed on AWS Python 3.10) |
| **Closed** | 2026-05-13 (Session 28 same-session — fifth same-session NEW+RESOLVED pattern after TD-097 S25 + TD-101 S26 + TD-NEW-2/3 S27) |
| **Closing commit** | `447634c` |
| **Severity at filing** | S2 (production-blocking for backfill operations; live writes succeeded because timestamps from `result.ts` written by AWS at sub-second precision happen to have exactly 6-digit microseconds; failure mode is cross-version stdlib semantic gap, surfaces at scale on historical-data parse paths) |
| **Component** | `compute_gamma_metrics_local.py::_dte_from_ts()` (helper added in TD-NEW-4 fix); reads `result.ts` ISO timestamp, parses via `datetime.fromisoformat()` to derive as-of date for `dte` payload. |
| **Discovery path** | Post-TD-NEW-12 + TD-NEW-4 patches deployed Local + AWS via git pull (commit `72622a9`), S28 P1 broken-window backfill executed on MERDIAN AWS: `for run_id in failed_run_ids: python compute_gamma_metrics_local.py --shadow --run-id "$run_id"`. 587 run_ids targeted; 527 succeeded, 60 failed with `ValueError: Invalid isoformat string: '2026-05-08T03:45:12.123456789+00:00'` or similar (varied microsecond digits 2-7). Failure pattern: timestamps with microsecond fraction having 2, 4, 5, or 7 digits (NOT 3 or 6) — Python 3.10 stdlib `fromisoformat()` accepts only those two precisions; anything else raises. Local Python 3.12 smoke test had passed on 5 sample rows because the sample happened to include only 3/6-digit microsecond timestamps. |
| **Symptom** | `ValueError: Invalid isoformat string: '...'` on `datetime.fromisoformat(ts_iso)` calls inside `_dte_from_ts`. Backfill cycles fail; rows not written to `gamma_metrics_shadow`; backfill script logs failures. No production impact during live writes because AWS-written `result.ts` timestamps consistently have 6-digit microseconds. |
| **Root cause** | Python stdlib `datetime.fromisoformat()` API is not portable across runtime versions for variable-microsecond-precision input. Python 3.10 stdlib accepts ISO timestamps with microsecond fraction of exactly 3 digits or exactly 6 digits; raises `ValueError` for any other precision. Python 3.12 stdlib accepts arbitrary precision (truncates or pads internally). Supabase serializes PostgreSQL timestamps with variable precision (2-7 digits common, depending on `pg_clock_gettime()` resolution and database default). Local development on Python 3.12 sees no problem; AWS production on Python 3.10 fails for cross-precision timestamps. Cross-version stdlib semantic gap. |
| **Fix** | Patch script `fix_td_new_13_microsecond_normalize.py` modifies `_dte_from_ts()` to regex-normalize the microsecond fraction to exactly 6 digits before calling `fromisoformat()`. Regex pattern: `r'\.(\d+)([+-]\d{2}:\d{2})?$'` — matches the microsecond + optional timezone offset tail; group 1 is the microsecond digits; pad with zeros to 6 if shorter, truncate to 6 if longer; reassemble. Canonical patch pattern: BOM-safe read, EOL detection (LF on file) + preservation, `ast.parse()` self-validation before write, `_PRE_TD-NEW-13.py` backup. Cross-version-tested: pattern works on Python 3.10 + 3.12 identically. |
| **Validation** | Local smoke test: 8 sample timestamps with microsecond fractions of 2, 3, 4, 5, 6, 7 digits + edge cases (no microsecond, no timezone) all parse correctly post-patch. AWS retry on the 60 failed run_ids: 60/60 success. Post-retry `gamma_metrics_shadow` row count matched target (587/587 for broken-window across 2026-05-08 + 2026-05-11). `still_unpatched = 0` on all 4 day/symbol diagnostics. |
| **Lesson (codified as CLAUDE.md B22 + Topology §6.9)** | **B22**: any Python module that parses ISO timestamps from Supabase MUST run cross-version-compatible code paths. Normalize the microsecond fraction to exactly 6 digits via regex pad/truncate before `fromisoformat()`. Verify on AWS, not just Local — Local Python 3.12 smoke testing is necessary but not sufficient. Long-term: align Python versions across Local + AWS. Until then, normalize defensively. **Topology §6.9** codifies the operational rule with affected-symptoms diagnostic shape. Future Supabase-timestamp-parse code paths adopt this normalization helper directly. |
| **Related** | TD-NEW-4 (sibling — both fixes in `_dte_from_ts` helper; TD-NEW-4 added the helper, TD-NEW-13 hardened it for cross-Python), TD-NEW-12 (parent — surfaced during TD-NEW-12 backfill retry phase), CLAUDE.md B22 + "TD-NEW-13 RESOLVED" settled-decisions bullet, Assumption Register §D.11.3 (cross-Python microsecond normalization invariant), Deployment Topology §6.9 (new AWS gotcha). |

---

### TD-NEW-12 (closed) — AWS shadow runner writes to production `gamma_metrics` instead of `gamma_metrics_shadow`

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — discovery during TD-080-adjacent investigation; SQL audit of today's `gamma_metrics` rows showed 2 writes per `(symbol, ts)` bucket per cycle, AWS-written `script_execution_log` rows confirmed `actual_writes: {"gamma_metrics": 1}` — literally writing to production table; `gamma_metrics_shadow` had 0 rows for 13 days) |
| **Closed** | 2026-05-13 (Session 28 same-session — sixth same-session NEW+RESOLVED pattern) |
| **Closing commit** | `72622a9` (compute patch + schema fix) + `de23467` (AWS wrapper patch) |
| **Severity at filing** | S1 (architectural — `gamma_metrics_shadow` table empty for 13 days; `evaluate_shadow_vs_live.py` evaluation cohort non-existent; production `gamma_metrics` rows had race-condition double-writes from Local + AWS competing on UPSERT; downstream readers consume whichever value won the race; behavior is "production data has noise but isn't corrupted because both writers compute the same thing on the same input" — not catastrophic but architectural integrity violated). |
| **Component** | `compute_gamma_metrics_local.py::upsert_gamma_metrics()` (hardcoded `"gamma_metrics"` table name across SELECT for prior + UPSERT for current + ExecutionLog telemetry); `run_merdian_shadow_runner.py` line 479 (subprocess invocation passed no flag to redirect writes to shadow table); `gamma_metrics_shadow` Supabase table (7 missing columns vs production `gamma_metrics` + missing UNIQUE constraint matching the UPSERT on_conflict). |
| **Discovery path** | S28 P0 closed 09:25 IST 2026-05-12 (TD-NEW-2/3 live cycle PASS). S28 mandate then drifted to investigating why TD-080 probe-log monitoring showed AWS-side option-chain ingest succeeding cleanly while signal_snapshots were not appearing — diagnostic SQL revealed AWS shadow runner was producing `script_execution_log` rows with `actual_writes: {"gamma_metrics": 1}` (the production table, not shadow). Cross-check: `SELECT symbol, ts, COUNT(*) FROM gamma_metrics WHERE ts > NOW() - INTERVAL '1 hour' GROUP BY symbol, ts HAVING COUNT(*) > 1` returned 2 writes per `(symbol, minute-bucket)` row for every cycle. Cross-check on shadow: `SELECT COUNT(*) FROM gamma_metrics_shadow WHERE ts > NOW() - INTERVAL '13 days'` returned 0. AWS option-chain ingest writes were therefore being upserted INTO PRODUCTION gamma_metrics, double-writing the same row Local had just written. UPSERT semantics determined which value persisted (typically AWS's because AWS cron at +0 to +30 seconds runs after Local at 0-second cycle boundary). Architectural intent per Topology §6.5 ("shadow ≠ live") silently violated since AWS shadow runner deployment (~2026-04-29). |
| **Symptom** | (1) `gamma_metrics_shadow` Supabase table has 0 rows. (2) `gamma_metrics` has 2 writes per `(symbol, ts)` per cycle since Apr 29. (3) AWS `script_execution_log` rows have `actual_writes: {"gamma_metrics": 1}` — telemetry honest but pointing at production target. (4) `evaluate_shadow_vs_live.py` (the comparison runner) would return zero-result trivially because cohort is empty; not exercised since deployment so no one noticed. |
| **Root cause** | `compute_gamma_metrics_local.py` was written assuming Local-only deployment. Hardcoded `"gamma_metrics"` table name in `fetch_prior_gamma_metrics()` SELECT, `upsert_gamma_metrics()` UPSERT, and `ExecutionLog` telemetry constructor. AWS shadow runner deployment added `run_merdian_shadow_runner.py` as the AWS-side wrapper; the wrapper invokes `compute_gamma_metrics_local.py` as a subprocess but passes no flag to redirect writes. The architectural intent was either (a) refactor `compute_gamma_metrics_local.py` for parameterized target table, OR (b) write a separate `compute_gamma_metrics_local_shadow.py`. Neither was done; the hardcode shipped to AWS via `git pull` and the architectural invariant was silently violated. Compounded by `gamma_metrics_shadow` table schema drift: created via `CREATE TABLE gamma_metrics_shadow LIKE gamma_metrics` (no `INCLUDING ALL` — columns only, no constraints/indexes); 7 columns added to production over time (dte, gamma_zone, otm_oi_velocity, raw, run_type, spot_vs_range, straddle_velocity) never propagated to shadow; UNIQUE(symbol,ts) constraint missing. |
| **Fix** | Two coordinated patches. **Compute patch** (commit `72622a9`) via `fix_td_new_12_shadow_flag.py`: (a) module-level `USE_SHADOW = "--shadow" in sys.argv` sniff before custom argv parser runs (must use sys.argv inspection, not parsed args, because the custom parser raises on unknown flags). (b) `TARGET_TABLE = "gamma_metrics_shadow" if USE_SHADOW else "gamma_metrics"` constant. (c) `fetch_prior_gamma_metrics()` SELECT routed via TARGET_TABLE. (d) `upsert_gamma_metrics()` UPSERT routed via TARGET_TABLE. (e) `ExecutionLog` `expected_writes` dict keyed by TARGET_TABLE + `record_write()` instrumentation honest about actual table. (f) Strip `--shadow` from argv list before custom parser sees it. Also bundled TD-NEW-4 dte-from-result.ts fix into same compute patch commit. **AWS wrapper patch** (commit `de23467`) via `fix_run_merdian_shadow_runner.py`: appends `"--shadow"` to subprocess args list at line 479. **Schema reconciliation** via SQL `ALTER TABLE gamma_metrics_shadow ADD COLUMN IF NOT EXISTS <col> <type>` for each of 7 missing columns + `ALTER TABLE gamma_metrics_shadow ADD CONSTRAINT gamma_metrics_shadow_symbol_ts_key UNIQUE (symbol, ts)` + `NOTIFY pgrst, 'reload schema'` to clear PostgREST schema cache. |
| **Validation** | Local smoke test Path 1 (no `--shadow` flag): `python compute_gamma_metrics_local.py --once --symbol NIFTY` writes 1 row to `gamma_metrics`; `actual_writes={"gamma_metrics": 1}`. Path 2 (`--shadow` flag): same script + `--shadow` writes 1 row to `gamma_metrics_shadow`; `actual_writes={"gamma_metrics_shadow": 1}`. AWS smoke at 07:07 IST 2026-05-13 via `ssm-user` SSH: deploy patched files via `git pull`, manual invocation of `python compute_gamma_metrics_local.py --shadow --once --symbol NIFTY` confirmed write to `gamma_metrics_shadow` table; full shadow runner cycle at 09:15 IST cron 2026-05-13 (live trading day) deferred to S29 first observation. |
| **Live impact** | Reader codebase audit confirmed all consumers of `gamma_metrics.net_gex` + `flip_level` + `gamma_zone` are sign-only or pass-through (zero magnitude thresholds), so the 13-day race-condition double-write window produced no incorrect production decisions — Local and AWS compute the same value on the same input (option_chain_snapshots), so whichever value persisted was correct. `evaluate_shadow_vs_live.py` cohort starts at S29 09:15 IST cron forward (TD-NEW-14-OPTIONAL Q14 in Topology §9 for backfill decision). |
| **Lesson (codified as Topology §6.5 update + §6.8 + Assumption Register §D.11.1 + CLAUDE.md S28 settled-decision bullet)** | (1) **Schema-present-behavior-absent deployment is a silent architectural-invariant violation.** Existence of `gamma_metrics_shadow` table was treated by Topology §6.5 narrative as evidence the architecture was wired; in reality the code did not enforce it. Going forward: for any architectural separation that depends on flag/parameter wiring, verify the wiring is exercised end-to-end at deployment time. Schema-only proxies for separation are insufficient. Smoke test must include `actual_writes` telemetry showing the expected target table. (2) **`CREATE TABLE ... LIKE` without `INCLUDING ALL` is a maintenance trap.** Constraints + indexes + defaults must be propagated separately. Audit every `_shadow` paired table for this gap. Topology §6.8 new gotcha. (3) **`NOTIFY pgrst, 'reload schema'` is mandatory after ALTER.** PostgREST caches schema for performance; does not auto-reload on DDL. |
| **Related** | TD-NEW-4 (bundled into same compute patch commit `72622a9` — different bug, same touch point), TD-NEW-13 (surfaced during TD-NEW-12 backfill retry — Python 3.10 microsecond rejection), Assumption Register §D.11.1 (shadow architecture invariant codified from this resolution), Topology §6.5 (update — narrative-only enforcement → architectural enforcement) + §6.8 (new — shadow schema parity gotcha), CLAUDE.md "TD-NEW-12 RESOLVED" settled bullet, ENH-93 `evaluate_shadow_vs_live.py` (becomes meaningful S29 09:15 IST cron forward). |

---

### TD-NEW-11 (closed) — `merdian_order_placer.py` not catalogued in Deployment Topology

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced during TD-NEW-10 investigation; the un-audited process turned out to be intentional but documentation gap was real) |
| **Closed** | 2026-05-13 (Session 28 — closed by S28 doc-close rewrite of `MERDIAN_Deployment_Topology.md`) |
| **Closing commit** | `<S28-doc-close>` (single commit covering all 7 doc-close files including Topology rewrite) |
| **Severity at filing** | S3 (documentation gap; no production impact; affects only Topology reader integrity going forward) |
| **Component** | `MERDIAN_Deployment_Topology.md` §3 AWS-only scripts (missing `merdian_order_placer.py` row); §7.1 AWS cron entries (missing `@reboot merdian_order_placer.py` line); §8.2 MERDIAN AWS runtime artifacts (missing `logs/order_placer.log` path). |
| **Symptom** | Process `merdian_order_placer.py` running on MERDIAN AWS as HTTP server on port 8767 since 2026-04-29 was not documented in any Topology section. Future sessions reading the Topology would not know it exists; future Topology audits would surface it as un-audited (which is exactly what happened in S28 → TD-NEW-10). |
| **Root cause** | Documentation drift — the order placer was deployed during a session that did not include a Topology update commit. Pre-existing register hygiene gap. |
| **Workaround** | None applicable; cosmetic. |
| **Fix** | Three rows added in S28 Topology rewrite: §3 row with full why-AWS-only rationale (Dhan IP whitelisting of AWS Elastic IP `13.63.27.85`; Local's multi-WAN home network has unstable IP); §7.1 `@reboot` cron entries section (also adds `@reboot merdian_signal_dashboard.py` which had the same gap but was less visible); §8.2 log path `logs/order_placer.log`. Plus §1 side-by-side row updated for "Phase 4B order placer (Dhan REST)" with Local=❌ MERDIAN AWS=✅ MALPHA=❌. |
| **Validation** | Topology rewrite verified — §3 row present, §7.1 @reboot block present, §8.2 log path present. Cross-checked with TD-NEW-10 closure that pointed at this same fix. |
| **Lesson** | Catalog-gap TDs are real even when no production impact — they surface in audits as un-audited processes (TD-NEW-10 was the first instance). Filing TD-NEW-11 as a separate S3 even though the work was done in the same session preserves the audit trail showing the gap was identified, scoped, and closed cleanly. |
| **Related** | TD-NEW-10 (filed-in-error parent — the un-audited process discovery surfaced this documentation gap), Deployment Topology §3 + §7.1 + §8.2 + §1 + §9.C (S28 boundary discoveries section). |

---

### TD-NEW-10 (closed) — `merdian_order_placer.py` running deployed but un-audited (filed-in-error after investigation)

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — discovered via `ps aux | grep python` on MERDIAN AWS during S28 drift period investigation) |
| **Closed** | 2026-05-13 (Session 28 same-session as filed-in-error after investigation) |
| **Closing commit** | n/a (no code change; documentation gap closed via TD-NEW-11) |
| **Severity at filing** | S2 (filed as un-audited process — could be benign or could be unauthorized; investigation needed) |
| **Component** | `merdian_order_placer.py` running on MERDIAN AWS as PID 579 (S28 inspection); HTTP server bound to port 8767; spawned via `@reboot` cron entry. |
| **Discovery path** | S28 drift period included broader audit of MERDIAN AWS process state (post-P0 closure). `ps aux | grep python` on MERDIAN AWS showed `python merdian_order_placer.py` running with PID 579. Process was not in Topology §3 AWS-only scripts list; not in §7.1 cron table; not mentioned in `merdian_reference.json` AWS runtime files inventory. Filed as un-audited process at S2 ("unknown process running on production EC2"). |
| **Symptom** | Process running on MERDIAN AWS; not documented; appeared as unauthorized or forgotten infrastructure on first inspection. |
| **Investigation** | (1) Read `merdian_order_placer.py` source on Local (committed to git): HTTP server providing endpoints `/place_order`, `/square_off`, `/order_status`, `/margin` for Dhan Trading API integration; called by Local dashboard's PLACE ORDER button. (2) Read git log: file added in Session 18 / V18G Phase 4B build; intentional Phase 4B Order Placer service. (3) Cross-check Dhan API documentation: Trading API endpoints (vs read-only endpoints) require IP-whitelisted source; MERDIAN AWS Elastic IP `13.63.27.85` is whitelisted; Local's multi-WAN home network IP is not stable enough to whitelist. (4) Cross-check crontab: `@reboot /bin/bash -lc 'set -a; . ./.env; set +a; nohup python /home/ssm-user/meridian-engine/merdian_order_placer.py > logs/order_placer.log 2>&1 &'` confirmed @reboot persistent service. (5) Disposition: not a defect; not unauthorized; deployed as intended in Phase 4B; missing from Topology because the deployment-time Topology update commit was skipped. |
| **Closure** | Filed-in-error at S28. Real issue (documentation gap) split out as TD-NEW-11. The un-audited-process framing was wrong; "Phase 4B service in production since 2026-04-29" framing is correct. |
| **Lesson** | When an unexpected production process is discovered, file as "unaudited" first (S1-S2), investigate, then close as filed-in-error if intentional. Document the absence in whatever register should have caught it; close the documentation gap in the same session. This separates "real defect" from "documentation drift" cleanly. Codified as CLAUDE.md S28 settled-decision bullet (canonical "audited live, confirmed intentional" closure pattern). |
| **Related** | TD-NEW-11 (sibling — documentation gap closed in same session by S28 Topology rewrite), CLAUDE.md S28 settled bullet codifying the closure pattern, Deployment Topology §3 + §7.1 + §8.2. |

---

### TD-NEW-8 (closed) — MERDIAN_WS_Stop cron `pkill -f` ignores SIGTERM; 9 zombies accumulate

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced during AWS process audit; 9 ws_feed_zerodha.py zombies + 1 active = 10 instances, ~1.4GB RAM impact) |
| **Closed** | 2026-05-13 (Session 28 same-session via crontab edit) |
| **Closing commit** | n/a (crontab edit, not code commit; logged in `logs/aws_crontab_snapshot_*.txt`) |
| **Severity at filing** | S2 (operational hygiene — accumulating zombies eventually require manual `kill -9 -f ws_feed_zerodha.py` + cron restart; not yet blocking but unsustainable) |
| **Component** | MERDIAN AWS crontab line `02 10 * * 1-5 pkill -f ws_feed_zerodha.py` (15:32 IST WS stop, intended to gracefully stop WS feed at session close). |
| **Discovery path** | S28 AWS process audit during drift period: `ps aux | grep ws_feed_zerodha` showed 10 instances; only 1 currently active (PID from today's WS feed), 9 zombies from prior days. Memory footprint ~140MB per zombie = ~1.26GB zombies + ~150MB active. Crontab inspection showed `pkill -f ws_feed_zerodha.py` (default SIGTERM = signal 15). |
| **Symptom** | 9 zombie processes accumulated over Apr 30 → May 11 (10 trading days). RAM consumption ~1.4GB on t3.small (2GB total). System swap usage rising. WS feed restart at 09:00 IST each Mon-Fri morning was succeeding but the prior day's instance was not exiting on 15:32 IST stop. |
| **Root cause** | `ws_feed_zerodha.py` has no SIGTERM handler installed (`signal.signal(signal.SIGTERM, ...)` absent). Default Python SIGTERM behavior is to interrupt blocking I/O calls; `kiteconnect.KiteTicker.connect()` runs an asyncio event loop that consumes the SIGTERM at the Python interpreter level but the WebSocket I/O continues. Process appears to receive the signal but does not exit. `pkill -f ws_feed_zerodha.py` (default SIGTERM) therefore returns success (signal delivered) but process does not exit. Each subsequent run @ 09:00 IST spawns a new instance; previous zombie remains. |
| **Fix** | Crontab edit: `pkill -f ws_feed_zerodha.py` → `pkill -9 -f ws_feed_zerodha.py` (SIGKILL = signal 9; kernel kills process unconditionally regardless of handlers). Single-character change. Snapshot of crontab pre-edit + post-edit preserved in `logs/aws_crontab_snapshot_20260513_*.txt`. Active zombies cleaned manually: `pkill -9 -f ws_feed_zerodha.py` once + restart cron entry. |
| **Validation** | Post-edit `ps aux | grep ws_feed_zerodha`: zero processes (clean kill of all 10). Post-edit cron entry verified via `crontab -l | grep ws_feed`. Monday 2026-05-19 09:00 IST WS feed start → 15:32 IST WS stop will be the first full lifecycle test; expect zero residual zombies post-15:32. |
| **Live impact** | Zero — WS feed was producing ticks correctly while zombies accumulated; only memory pressure was the side effect. Could have eventually OOM'd the t3.small. |
| **Lesson** | Default SIGTERM is not always sufficient for processes that ignore or mishandle the signal. When `pkill -f <pattern>` is the lifecycle terminator and the target process has no explicit SIGTERM handler, use SIGKILL (`-9` flag). Long-term proper fix: install signal handler in `ws_feed_zerodha.py` that gracefully shuts down KiteTicker before exit; not done because (a) SIGKILL works reliably, (b) WS feed is stateless from MERDIAN's perspective (ticks land in `market_ticks` per-row; mid-shutdown loss of <1s of ticks is acceptable). Filed as candidate enhancement only if signal-handler hygiene becomes important. |
| **Related** | TD-NEW-9 (sibling — `ws_feed_zerodha.py` silent-on-success logging; would help diagnose zombie state from log alone instead of `ps aux`), Deployment Topology §7.1 updated, CLAUDE.md S28 settled bullet. |

---

### TD-NEW-6 (closed) — Local `MERDIAN_WS_Feed_0900` task is dead-stub; pollutes logs

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced during Topology audit; Local task firing daily but `market_ticks` writes traced to MERDIAN AWS only) |
| **Closed** | 2026-05-13 (Session 28 same-session via PowerShell `Disable-ScheduledTask`) |
| **Closing commit** | n/a (Task Scheduler state change, durable across reboots) |
| **Severity at filing** | S3 (operational hygiene — Local task fires daily but produces no useful work; `script_execution_log` rows pollute audit trail; occasional mid-session crashes interrupt operator workflow) |
| **Component** | Windows Task Scheduler `MERDIAN_WS_Feed_0900` (~09:00 IST Mon-Fri), wired to `cmd.exe /c run_ws_feed_zerodha.bat` → wraps `ws_feed_zerodha.py`. Per Deployment Topology §2, the actual production WS feed runs on MERDIAN AWS only (Kite browser-TOTP auth flow can't run headless on AWS unless gateway-routed, but the Local invocation was vestigial design that never produced useful ticks). |
| **Discovery path** | S28 Topology audit: cross-check `market_ticks` table for `host`/`source` column to identify which environment writes ticks. All recent ticks tagged with AWS host. Local task `MERDIAN_WS_Feed_0900` confirmed firing daily at 09:00 IST per `script_execution_log` rows but writing zero ticks to `market_ticks` (Local Kite auth path produces ticks for breadth ingest but those go to `market_breadth_intraday`, not `market_ticks`). Local task was vestigial. |
| **Symptom** | Daily firings on Mon-Fri 09:00 IST pollute `task_output.log` + `script_execution_log` with no-op runs that occasionally crashed mid-session (network error mid-WS connection attempt) interrupting operator workflow. |
| **Root cause** | Vestigial design — `MERDIAN_WS_Feed_0900` was added when the WS feed architecture was Local-first; subsequent migration to AWS-first (around Session 18 / V18G) deprecated the Local invocation but the Task Scheduler entry was never disabled. |
| **Fix** | `Disable-ScheduledTask -TaskName MERDIAN_WS_Feed_0900` via PowerShell. Durable across reboots. No code change. Task remains in Task Scheduler for re-enable if needed (e.g., if AWS WS feed becomes unavailable and Local-as-fallback is desired). |
| **Validation** | Post-disable: task state confirmed `Disabled` via `Get-ScheduledTask MERDIAN_WS_Feed_0900`. Mon-Fri 09:00 IST onwards: no new `script_execution_log` rows for `MERDIAN_WS_Feed_0900`. No interruptions to operator workflow. |
| **Live impact** | Zero — Local task was producing no useful ticks before disable. AWS-side WS feed continues unchanged. |
| **Lesson** | Vestigial Task Scheduler entries accumulate across migration boundaries. Audit task list periodically against actual data flow (which environment writes which table). Disable-not-delete preserves rollback option. Codified as CLAUDE.md S28 settled bullet. Topology §7.2 updated with `State=Disabled` annotation. |
| **Related** | Deployment Topology §2 + §7.2 (note about state), Deployment Topology §A.2 (run_ws_feed_zerodha.bat is now wrapper for disabled task), CLAUDE.md S28 settled bullet. |

---

### TD-NEW-5 (closed) — Pine overlay regeneration not chained off `MERDIAN_ICT_HTF_Zones_0845`

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced when operator noticed Pine overlay rendering against stale zones during Mon morning chart prep) |
| **Closed** | 2026-05-13 (Session 28 same-session via bat file edit) |
| **Closing commit** | n/a (bat file edit on Local; not committed to repo as it's environment config) |
| **Severity at filing** | S2 (operational — stale Pine overlay means operator chart prep uses yesterday's zones; signal context wrong) |
| **Component** | `run_ict_htf_zones_daily.bat` (Local Task Scheduler wrapper at 08:45 IST Mon-Fri) was running `build_ict_htf_zones.py --timeframe both` correctly but `generate_pine_overlay.py` (which reads `ict_htf_zones` rows + writes TradingView Pine v6 overlay file to `dashboards/ict_overlay.pine`) was a manual step operator had to remember to run each morning. |
| **Discovery path** | Mon 2026-05-12 morning: operator opened TradingView, noticed Pine overlay rendering zones from 2026-05-09 (Friday) instead of today's fresh zones. Manual run of `python generate_pine_overlay.py --output dashboards\ict_overlay.pine` produced fresh overlay; reload in TradingView showed today's zones correctly. Pattern repeated 2-3 times prior weeks; operator had been working around it but called it out for S28 fix. |
| **Symptom** | Pine overlay file at `dashboards/ict_overlay.pine` not updated after 08:45 IST zone build; remains stale until operator runs `generate_pine_overlay.py` manually. Stale overlay = chart context wrong = signal interpretation wrong. |
| **Root cause** | `run_ict_htf_zones_daily.bat` chained Call 1 (`--timeframe D`) + Call 2 (`--timeframe H`) but no Call 3 for Pine regeneration. Original bat file design treated Pine generation as a separate downstream operation; the dependency was not formalized. |
| **Fix** | Edit `run_ict_htf_zones_daily.bat` to add Call 3: `python generate_pine_overlay.py --output dashboards\ict_overlay.pine` after the two existing build calls. PowerShell `(Get-Content path) -replace 'exit /b 0', "newcontent\r\nexit /b 0" | Set-Content path` pattern (TD-067 / Session 21 lesson — `Add-Content` after `exit /b` makes line unreachable). Config-only change. |
| **Validation** | Manual run of patched bat file: zones built + Pine overlay file regenerated; file mtime updated. Mon 2026-05-19 08:45 IST scheduled run will be the first auto-test; expect Pine overlay file mtime to be 08:45 IST + few seconds. |
| **Live impact** | Zero retroactive impact (manual fallback always available). Forward impact: removes one manual step from operator morning checklist. |
| **Lesson** | Downstream auto-publication artifacts (Pine overlays, dashboards, exported CSVs) should be chained off the upstream data refresh task, not left as manual steps. Codified as CLAUDE.md S28 settled bullet + Topology §A.2 + §7.2 (action column updated). |
| **Related** | Deployment Topology §A.2 (run_ict_htf_zones_daily.bat row updated), Topology §7.2 (MERDIAN_ICT_HTF_Zones_0845 row updated), `generate_pine_overlay.py` (downstream artifact), CLAUDE.md S28 settled bullet. |

---

### TD-NEW-4 (closed) — `compute_gamma_metrics_local.py` `dte` payload from `date.today()` not `result.ts.date()`

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced during TD-NEW-12 smoke test which exercised backfill code path that production live writes don't stress) |
| **Closed** | 2026-05-13 (Session 28 same-session — bundled with TD-NEW-12 fix into same commit `72622a9`) |
| **Closing commit** | `72622a9` |
| **Severity at filing** | S2 (latent bug; surfaces only on backfill / replay paths where compute is run on historical data; live writes unaffected because result.ts ≈ now within seconds) |
| **Component** | `compute_gamma_metrics_local.py::upsert_gamma_metrics()` — `dte` payload field computed as `(date.fromisoformat(result.expiry_date) - date.today()).days`. |
| **Discovery path** | TD-NEW-12 fix smoke test required exercising the backfill path (running compute on 2026-05-12 data on 2026-05-13). Post-patch row in `gamma_metrics_shadow`: `dte = -1` for NIFTY 2026-05-12 09:15 IST cycle. Expected: `dte = 0` (NIFTY's expiry on that Tuesday was the same day per new NIFTY weekly expiry calendar). Investigation: `result.ts.date() = 2026-05-12`; `date.today() = 2026-05-13`; expiry_date = `2026-05-12`. `(date(2026-05-12) - date(2026-05-13)).days = -1`. Code was using wall clock instead of cycle's actual timestamp. |
| **Symptom** | Backfill / replay computes produce `dte` values that are off-by-N-days where N = days between cycle's actual timestamp and wall clock at run time. Live writes are correct because the gap is sub-second. |
| **Root cause** | `date.today()` returns the wall clock date at the moment the function executes. For live writes this matches the cycle date. For backfill/replay/repair runs, the cycle date is in the past; using `date.today()` produces wrong as-of date. Standard pattern in payload-computation code is to use the result's own timestamp field for any temporal derivation. |
| **Fix** | Module-level helper `_dte_from_ts(result)` added to `compute_gamma_metrics_local.py`. Helper extracts as-of date from `result.ts` (timestamp field) in IST timezone (consistent with rest of MERDIAN's IST convention). Payload line in `upsert_gamma_metrics()` updated to use helper. Canonical patch pattern: BOM-safe read, EOL preservation, `ast.parse()` validation, `_PRE_TD-NEW-4.py` backup. Bundled into commit `72622a9` (TD-NEW-12 + TD-NEW-4 together — both fixes to `compute_gamma_metrics_local.py` to amortize one deploy cycle). |
| **Validation** | Cross-validation 2026-05-12 NIFTY run_id `e2dd1a09-...`: pre-patch `dte = -1` (wrong); post-patch `dte = 0` (correct). Same cycle, same data, helper-derived as-of date matches result.ts.date(). |
| **Live impact** | Zero on live writes (sub-second gap). Backfill / replay corrected forward; pre-S28 backfilled rows have `dte` values from when they were computed (typically wrong by N days), filed as candidate cleanup if any downstream consumer reads `dte` on historical rows (none confirmed — `dte` is mostly diagnostic). |
| **Lesson (codified as Assumption Register §D.11.2 + CLAUDE.md S28 settled bullet)** | All `dte`-class temporal payload fields must be derived from result's own timestamp field, never wall clock. Wall-clock derivation is correct only for live writes where the gap is sub-second; backfill/replay/repair paths produce wrong values silently. Canonical pattern: module-level `_<field>_from_ts(result)` helpers. Future temporal-payload fields adopt same pattern. Surfaced via TD-NEW-12 smoke test which exercised the rarely-stressed code path; live cadence alone is not sufficient validation surface for temporal-payload logic. |
| **Related** | TD-NEW-12 (parent — bundled into same commit; both fixes touch `compute_gamma_metrics_local.py`), TD-NEW-13 (sibling — Python 3.10 stdlib gap in `_dte_from_ts` helper surfaced during backfill retry), Assumption Register §D.11.2 (result-ts-based dte invariant codified), CLAUDE.md S28 settled bullet, Phase 0a + 0b retroactive backfill paths (use this fix). |

---

### TD-101 (closed) — `build_momentum_features_local.py::get_session_open_spot()` unbounded query NULLs `ret_session`

| | |
|---|---|
| **Filed** | 2026-05-10 (Session 26 — discovery via diagnostic SQL after TD-099 closure) |
| **Closed** | 2026-05-10 (Session 26 same-session) |
| **Closing commit** | `3cb84e2` |
| **Severity at filing** | S1 (live trading bug — silently NULLed `ret_session` for 3+ trading weeks; broke ENH-55 momentum opposition gate which became silent no-op for the entire window) |
| **Component** | `build_momentum_features_local.py::get_session_open_spot()` (Local primary pipeline) |
| **Discovery path** | Operator picked TD-054 (broken `ret_30m` research column) at session opening after closing TD-099 as filed-in-error. Diagnostic SQL Q2 (`SELECT raw->>'ret_session' FROM signal_snapshots WHERE ts >= '2026-04-17' AND raw->>'ret_session' IS NULL`) showed NULL on every signal back to 2026-04-17 (3+ weeks; ~5,000 signals across multiple trading days). Q4 confirmed `market_state_snapshots.momentum_features.ret_session` value=NULL but key=present on every row. Q-source (`SELECT COUNT(*) FILTER (WHERE ret_session IS NOT NULL) FROM momentum_snapshots WHERE ts >= '2026-04-17'`) confirmed `momentum_snapshots.ret_session` 100% NULL while `ret_15m` / `ret_30m` / `ret_60m` were 100% populated — bug isolated to ret_session-specific compute path. |
| **Symptom** | `momentum_snapshots.ret_session` NULL on every row 2026-04-17 → 2026-05-10. Propagated to `market_state_snapshots.momentum_features.ret_session` NULL (consolidator forwarded the NULL). Propagated to `signal_snapshots.raw.ret_session` NULL (signal builder reads from market_state_snapshots and forwards). ENH-55 inner condition `if ret_session is not None and abs(ret_session) > 0.0005:` evaluated to False on every signal — gate did not fire opposition block, did not award alignment +10 bonus. Telemetrically identical to "gate not firing because ret_session in neutral band" — no ERROR logs, no contract violations. Silent failure. |
| **Root cause** | `get_session_open_spot()` body: `rows = supabase_select("market_spot_snapshots", filters={"symbol": symbol}, order_by="ts", desc=False, limit=500)`. Returns OLDEST 500 rows in unbounded `market_spot_snapshots` table (no date filter, no time-range filter on the order_by column). Today-date filter inside loop discards all 500. Returns None silently. Downstream `compute_return(curr, None)` returns None. Stored as NULL. Same OI-18 anti-pattern shape as S25 TD-097 dashboard fix (unbounded `order_by`+`limit` returning oldest rows; today-filter inside loop) but in writer-side helper rather than dashboard URL construction. |
| **Why TD-099 grep didn't catch it** | TD-099 audit grep was `requests.get.*SUPABASE.*params` — shape-specific to dashboard's REST URL construction pattern. TD-101's anti-pattern is inside `supabase_select()` helper (Python client wrapper), not at top-level URL construction. Grep couldn't match because the bug is buried inside a helper call. The class of bug is the same; the code shape isn't. |
| **Fix** | Patch script `patch_s26_td101_ret_session.py` (v3 patch canon — `utf-8-sig` decode, byte-write, `ast.parse` validation, idempotency guards, snapshot original). Replaces `get_session_open_spot()` body with bounded query: `today_start_utc_iso` derived from `current_ts.astimezone(timezone.utc)` date; `gte("ts", today_start_utc_iso)` filter; `limit=20` (down from 500 — bounded query needs only first ~20 rows of today to find threshold-crossing); defense-in-depth date filter inside loop preserved (idempotent safety net); threshold 03:35 UTC preserved per ENH-01 / V18G regression history (catches both 09:05 IST Local PreOpen now-disabled and 09:08 IST AWS PreOpen current anchor). Backup `build_momentum_features_local_PRE_S26_TD101.py` preserved. AST OK on Local + AWS post-pull. |
| **Validation** | Smoke test on Friday 2026-05-08 close prices (no Sunday data; replay invocation): NIFTY returned 24,161.3 (correct first-tick-after-09:08 spot), SENSEX returned 77,582.08 (correct first-tick-after-09:08 spot). Sunday 2026-05-10 invocation returned None for both as expected (no data on non-trading day). No errors, no exceptions. **Live verification** deferred to Mon 2026-05-12 first cycle: `SELECT COUNT(*) FILTER (WHERE ret_session IS NOT NULL) / COUNT(*) FROM momentum_snapshots WHERE ts >= CURRENT_DATE + INTERVAL '4 hours'` should approach 100% from second cycle onwards (first cycle may legitimately neutral if open == 09:08 spot). |
| **Live impact (silent-failure window)** | 2026-04-17 → 2026-05-10 (24 trading days, ~5,000 signals). ENH-55 momentum opposition gate (Exp 20 evidence: ALIGNED 60.9% WR vs OPPOSED 38.3% WR, +22.6pp lift) was silent no-op for entire window — both opposition hard-block AND alignment +10 confidence bonus inactive. Production data on the cohort that ENH-55 *would have* gated produced retrospective audit results that directionally falsify Exp 20 hypothesis (see TD-101 cascade impact below). |
| **Cascade impact — ENH-55 disablement (commit `5b94c78`)** | Retrospective audit on the silent-failure window partitioned actionable signals (action ∈ {BUY_CE, BUY_PE} ∧ `trade_allowed=TRUE`) into ENH-55-decision buckets: WOULD_HAVE_BLOCKED (opposed) N=44 79.5% WR; WOULD_HAVE_ALIGNED_BONUS N=35 54.3% WR; NEUTRAL_BAND N=1 0% WR. Sign of lift opposite to Exp 20; magnitude (gap of 25pp between WOULD_BLOCK and WOULD_ALIGN) clears Assumption Register §D.8.3 prospective-parity flag-drift criterion (>15pp). Decomposition: all 44 OPPOSED-but-winning trades are BUY_PE in up-sessions; 43/44 have `ict_pattern=NONE` — pure momentum-driven signals where 15m/30m turn down despite session running up; signature is intraday-rollover-of-up-session-strength = exhaustion / mean-reversion edge. Operator decision: keep TD-101 fix (writer bug unambiguously correct, orthogonal to gating decision) + disable ENH-55 by env flag (the calibration question). `patch_s26_enh55_disable.py` adds `ENH55_ENABLED: bool = os.getenv("MERDIAN_ENH55_ENABLED", "0").strip() == "1"` after `SIGNAL_V4_ENABLED` declaration; modifies inner condition to `if ENH55_ENABLED and ret_session is not None and abs(ret_session) > 0.0005:`. Disables BOTH opposition block AND alignment bonus (same evidence base, symmetric claims falsified together). ENH-53 breadth modifier untouched. Default OFF; reversible. Filed as Assumption Register §D.9 (5 rows D.9.1–D.9.5 + 4 open follow-ups + ADR-009 first-case-study material). |
| **Lesson (codified as CLAUDE.md B19)** | When an OI-18-class bug ships and is fixed at one site, the closure of the class requires (a) URL-spy or runtime-trace verification of every candidate site, not just grep — the grep is shape-specific and misses helper-buried instances; (b) audit must extend to writer-side helpers downstream of the symptom site, not just request-side construction at the symptom site. Filing rule: "same anti-pattern in N scripts" claims require runtime verification before priority assignment. The grep is the trigger to investigate, not the verdict. TD-097 was fixed; TD-099 was filed-in-error; TD-101 was the real instance the grep audit missed. Cost of grep-only audit: 24 days of broken gate before retrospective evidence cascade surfaced it. |
| **Related** | TD-097 (precedent — S25 fix at one OI-18 site), TD-099 (closed filed-in-error S26 — grep audit produced false matches), CLAUDE.md B19 (lesson codification), Assumption Register §D.9 (ENH-55 falsification 5 rows), ENH-55 entry (status COMPLETE PROMOTED ENV-DISABLED). |

---

### TD-099 (closed) — URL-encoding bug pattern audit (filed-in-error after URL-spy verification)

| | |
|---|---|
| **Filed** | 2026-05-10 (Session 25 — sweep filed at S2 HIGH after TD-097 dashboard fix on strength of `grep -rn "requests.get.*SUPABASE.*params"` matching 5 production scripts) |
| **Closed** | 2026-05-10 (Session 26 — closed as filed-in-error after URL-spy verification) |
| **Closing commit** | None (no code changes — diagnostic-only closure) |
| **Severity at filing** | S2 HIGH (presumed silent under-fetch in 5 production scripts, same shape as TD-097) |
| **Severity at closure** | N/A (filed-in-error — no real defect existed) |
| **Component** | Five production scripts: `build_signal_market_path_audit_v1.py`, `build_signal_outcome_audit_local.py`, `build_signal_regret_log_v1.py`, `build_option_execution_outcomes_v1.py`, `premium_outcome_writer.py`. |
| **Verification method** | URL-spy: monkey-patched `requests.get` to print URLs and params before each call, ran each script in dry-run mode, inspected emitted URLs. |
| **Outcome** | All 4 scripts in scope (`build_signal_market_path_audit_v1.py`, `build_signal_outcome_audit_local.py`, `build_signal_regret_log_v1.py`, `build_option_execution_outcomes_v1.py`) emit clean single-`?` URLs with proper encoding (`%2A`=`*`, `%2C`=`,`). 5th script `premium_outcome_writer.py` uses supabase Python client (`supabase.table(...).select(...).execute()`), not raw `requests.get` — different code path entirely; the grep matched a comment or unrelated import line. **No actual instances of TD-097 anti-pattern in any of the 5 scripts.** |
| **Why grep produced false-positives** | Grep regex `requests.get.*SUPABASE.*params` matched both broken TD-097 form (URL with embedded `?col=eq.{val}` AND params dict — the double-encoding bug shape) and standard-correct form (clean URL + params dict only — Python client's normal pattern). Regex is shape-specific to "URL contains params" not "URL is broken". Distinguishing requires either (a) more specific regex matching `URL_with_query_string + params=`, or (b) runtime URL-spy verification. The latter is the canonical verification pattern. |
| **Cost avoided** | ~3 hours of unnecessary patching (5 scripts × ~30min each per S25 estimate). |
| **Lesson (codified as CLAUDE.md B19 + filing rule)** | Before assigning priority to a "same anti-pattern in N scripts" claim, verify with URL-spy or equivalent runtime trace, not grep alone. False-positive grep matches against dashboard-style code patterns are common; the symptom that surfaced the original bug (silent 200-OK with empty results) does not necessarily survive in code-shape grep terms. **Filing pattern going forward:** TD-097-style audit-derived TDs require runtime verification of at least one match before filing the rest. The grep is the trigger to investigate, not the verdict. **Note:** while TD-099 was filed-in-error, the TD-101 instance (real propagation, writer-side helper that the grep couldn't reach by construction) confirms the broader OI-18 propagation concern was correct in principle even if the specific grep targets were wrong. |
| **Related** | TD-097 (precedent), TD-101 (real propagation site the grep missed), CLAUDE.md B19 (lesson). |

---

### TD-079 (closed) — Zone date-expiry vs ICT canon (architectural defect — RESOLVED via ADR-005 implementation)

| | |
|---|---|
| **Filed** | 2026-05-07 (Session 22 — Pine overlay visually missing all >78k resistances surfaced architectural defect) |
| **Closed** | 2026-05-10 (Session 26 — implementation shipped per Phase α Q1 answer locked S25) |
| **Closing commit** | `0731e67` |
| **Severity at filing** | S2 HIGH (architectural defect bleeding signal quality across months of trading) |
| **Component** | `build_ict_htf_zones.py::expire_old_zones()` — applied date-based expiry uniformly across pattern_types regardless of ICT canon. |
| **Symptom (pre-fix)** | Unbreached structurally-relevant W zones (especially BEAR_OB/BEAR_FVG resistances above current spot during a bull market) marked EXPIRED on the 4-weeks-after-source-bar boundary regardless of whether price ever closed through them. Pine overlay visually missing all resistances above 78,000 throughout the 2026-04 → 2026-05 bull leg. Detector still emitted new zones each rebuild but the historical archive of unbreached structure was silently discarded. |
| **Root cause** | `valid_to` model was wrong for OB/FVG. Per ICT canon: zones live until price *closes through them*, not date-expire. PDH/PDL legitimately date-expire (they are daily levels by definition). OB/FVG should expire only on price-breach, never on date. Original code conflated the two pattern type families with uniform date-expiry logic. |
| **Phase α Q1 answer (S25 architecture conversation)** | (a) pure price-based canonical with timeframe-tiered fallback intraday-only — D/W OB/FVG = price-breach only, `valid_to=NULL`; 1H OB/FVG = price-breach OR 1 week (whichever first; tactical fallback to prevent intraday memory pile-up); PDH/PDL = date-expire (unchanged). |
| **Implementation (Session 26)** | Patch script `patch_s26_td079_zone_validity.py` applied 13 surgical replacements AST-validated to `build_ict_htf_zones.py`: (1) D/W OB/FVG zones written with `valid_to=None` (was `week_end + 4 weeks` for W, `bar_date + 1 day` for D); (2) 1H OB/FVG zones written with `valid_to = str(trade_date + timedelta(days=7))` (tactical fallback); (3) PDH/PDL date-expiry logic untouched; (4) `expire_old_zones()` filter widened from `["W","D"]` → `["W","D","H"]` so 1H zones get expired by date when their week is up; (5) `recheck_breached_zones()` becomes the primary status transition for D/W (price-breach detection runs against any ACTIVE zone with `valid_to=NULL`). Backup `build_ict_htf_zones_PRE_S26.py` preserved. |
| **Backfill SQL** | `td079_backfill.sql` applied: `UPDATE ict_htf_zones SET status='ACTIVE', valid_to=NULL WHERE timeframe IN ('W','D') AND pattern_type IN ('BULL_OB','BEAR_OB','BULL_FVG','BEAR_FVG') AND status='EXPIRED' AND zone_high > <breach_test>` with subsequent breach-recheck pass. Revived 18 SENSEX W BEAR_OB/BEAR_FVG zones above 78k from EXPIRED → ACTIVE valid_to=NULL. |
| **Validation** | Live rebuild via `build_ict_htf_zones.py --timeframe both` produced 80 zones (47 NIFTY + 33 SENSEX); Pine overlay regenerated via `generate_pine_overlay.py` shows 62 zones (49 HTF + 13 intraday) up from S25's 36; visual confirmation: all major resistances 78k → 86k now displayed on TradingView. |
| **ADR-005 status** | Phase α Q1 answer locked S25, recorded in `docs/decisions/MERDIAN_Decision_Index.md` and `docs/registers/MERDIAN_Assumption_Register.md` §D.7. ADR-005 formal draft (P2 S27 carry-forward) follows the implementation per CLAUDE.md S26 lesson: architecture-defect TDs implementable before formal ADR when (a) Phase α answer is in hand, (b) implementation is reversible (snapshot original), (c) ADR draft follows in dedicated session to capture rationale + alternatives. Doc Protocol v4 Rule 10 ADR-mandatory-before-code is satisfied because the architectural decision was made S25 and recorded in Decision Index + Assumption Register §D.7; the ADR draft is the writeup of an already-made decision. |
| **Side effect** | Pine overlay zone count grew 36 → 62 (+72%); operator-side discretionary use restored to mid-March 2026 baseline coverage of resistance/support stack. |
| **Related** | ADR-005 (formal draft pending S27 P2), Phase α Q1 answer (Decision Index, Assumption Register §D.7), `build_ict_htf_zones.py` snapshot `_PRE_S26.py`. |

---

### TD-097 (closed) — Dashboard pre-open status URL-encoding bug producing 0% accuracy widget on `merdian_live_dashboard.py`

| | |
|---|---|
| **Closed** | 2026-05-10 (Session 25, same-session as discovery and fix) |
| **Closing commit** | (single S25 commit — see session-end commit message) |
| **Fix applied** | Patch script `patch_s25_dashboard_preopen_gap.py` (16,791 bytes; v3 patch canon — `utf-8-sig` decode, byte-write, `ast.parse` validation, idempotency guards). 5 substitutions applied to `C:\GammaEnginePython\merdian_live_dashboard.py`: (1) `get_preopen_status()` URL-encoding fixed by collapsing `requests.get(url, params={...})` into a single fully-encoded URL via `urllib.parse.urlencode()`; (2) `get_gap_status()` new function added (gap-card data path); (3) `collect_data()` wired to invoke `get_gap_status()` alongside existing status getters; (4) `gap_html` builder added; (5) gap card placement HTML inserted between Token card and Pre-open card. Backups preserved as `merdian_live_dashboard_PRE_S25.py` and `merdian_live_dashboard_PRE_S25b.py` (post-FIX1 cosmetic reposition). Two cosmetic post-patch repositionings on the gap-card location. |
| **Validation** | Pre-fix: dashboard pre-open accuracy widget showed `0%` because the URL-encoding double-applied caused Supabase to return zero matching rows (silent failure — endpoint returned 200 OK with empty results). Post-fix on 2026-05-10 evening: dashboard pre-open accuracy widget returned correct historical reading; gap card displays `prev close → prelim gap (16:00 vs 09:08) → final gap (16:00 vs 09:15)` with valid data. Diagnostic scripts `diag_preopen_render.py`, `_v2.py`, `_v3.py` retained in tree for future debugging. |
| **Lesson** | The same `requests.get(SUPABASE_URL + endpoint, params={...})` URL-encoding anti-pattern exists in 5 other production scripts (filed as TD-099). Whenever one occurrence of this bug ships and is fixed, audit all `requests.get` call sites in the codebase for the same pattern — `grep -rn "requests.get.*SUPABASE.*params"` reveals them in seconds. Same root cause as TD-097 will produce silent under-fetch in any of those 5 scripts whenever they run in production. |
| **ENH side-effect** | ENH-96 (gap display widget on dashboard) shipped as same-session side-effect of this investigation — the data was already captured (PreOpen 09:08 row exists in `market_spot_snapshots`); the dashboard just wasn't surfacing it. ENH-96 entry in Enhancement Register tracks the feature beyond the bugfix. |

---

### TD-078 (closed) — TD-070 closure verification incomplete — empirically multi-week BULL_OB lookback may not be firing as designed

| | |
|---|---|
| **Closed** | 2026-05-10 (Session 25) |
| **Closing commit** | (single S25 commit — see session-end commit message) |
| **Fix applied** | No code change required. SQL verification per the proper-fix procedure: `SELECT * FROM ict_htf_zones WHERE timeframe='W' AND pattern_type='BULL_OB' AND source_bar_date='2026-04-13'`. Initial result: empty. Investigation revealed the convention used by `build_ict_htf_zones.py` for W-timeframe `source_bar_date` is the **week-start Monday date** (e.g. `2026-04-13` BULL_OB anchor lives under `source_bar_date='2026-04-13'` ONLY if Apr 13 was a Monday week-start; if the week started on a different Monday, the anchor lives under that Monday's date). Adjusted query to scan W BULL_OB zones across April-May 2026 produced the expected anchor row tied to the correct Monday week-start. TD-070 v2 multi-week unbreached-anchor lookback fires as designed. |
| **Validation** | Adjusted SQL: `SELECT source_bar_date, prior_move, status FROM ict_htf_zones WHERE timeframe='W' AND pattern_type='BULL_OB' ORDER BY source_bar_date DESC LIMIT 20` returned the expected unbreached-anchor row from a Monday in mid-April 2026 with `status='ACTIVE'`. Confirms the Apr-13 sustained-bull-week BULL_OB candidate was correctly captured under the v2 lookback logic, not silently dropped by the dedup. The "missing" original-query result was a schema-convention misunderstanding, not a missed detection. |
| **Lesson** | `ict_htf_zones.source_bar_date` semantics differ by timeframe — for W timeframe it's the Monday week-start, for D it's the bar's calendar date, for 1H it's the hour bucket date. This convention is implicit in `build_ict_htf_zones.py` and not documented elsewhere. Filed for inclusion in System Map §B annotations on `ict_htf_zones` schema. Whenever debugging a "missing" zone row, check the timeframe-aware convention before concluding the row is absent. |

---

### TD-084 (closed) — `backfill_option_zerodha_OI_FIXED.py` UTC/IST timezone bug truncated Kite output to 46 bars per strike

| | |
|---|---|
| **Closed** | 2026-05-07 (Session 22, same-session as discovery) |
| **Closing commit** | uncommitted MALPHA dirty (~/meridian-alpha/backfill_option_zerodha_OI_FIXED.py with .bak_S22 preserved). MALPHA dirty acceptable per S20 directive (Kite gateway only). |
| **Fix applied** | sed-replaced line 184: `dt_ist = bar["date"].replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)` → `dt_ist = bar["date"].astimezone(IST) if bar["date"].tzinfo else bar["date"].replace(tzinfo=IST)`. New logic: if bar["date"] already has tzinfo (it does, from Kite as IST) → astimezone(IST) is a no-op; if tzinfo missing → assume IST (safe fallback). |
| **Validation** | Pre-fix dry-run: 46 bars/strike per SENSEX strike on 2026-05-07. Direct Kite probe via `/tmp/check_sensex_kite.py`: 375 bars confirmed (full session). Post-fix dry-run: 375 bars/strike for both NIFTY+SENSEX. Live run wrote 24,749 rows (NIFTY 8,250 = 22 strikes × 1 expiry; SENSEX 16,499 = 44 strikes × 2 expiries). Verified per-strike via SQL `SELECT strike, expiry_date, option_type, COUNT(*) FROM hist_option_bars_1m WHERE trade_date='2026-05-07' GROUP BY 1,2,3` showing 375 bars/contract uniformly. |
| **Lesson** | Kite returns IST-tagged datetimes for `historical_data` calls — applying `.replace(tzinfo=ZoneInfo("UTC"))` is the canonical timezone bug pattern, never apply to Kite output. The same bug pattern can appear anywhere in the codebase that consumes Kite historical data; audit `grep -rn "tzinfo=ZoneInfo.*UTC.*astimezone(IST)"` to find latent instances. Filed as a CLAUDE.md operational finding. |

---

### TD-072 (closed) — 22-min Task Scheduler gap 13:25-13:47 IST traced to power-source change events

| | |
|---|---|
| **Closed** | 2026-05-06 (Session 21) |
| **Closing commit** | uncommitted (S21 patches still in working tree at S22 close) |
| **Fix applied** | PowerShell loop set `DisallowStartIfOnBatteries=$false` and `StopIfGoingOnBatteries=$false` on 8 market-hours tasks: MERDIAN_Spot_1M, MERDIAN_PreOpen, MERDIAN_IV_Context_0905, MERDIAN_PO3_SessionBias_1005, MERDIAN_Market_Tape_1M, MERDIAN_HB_Watchdog, MERDIAN_ICT_HTF_Zones_0845, MERDIAN_Intraday_Supervisor_Start. |
| **Validation** | Battery flags persist verified at Session 22 pre-market (08:00 IST PowerShell `Get-ScheduledTask | Get-ScheduledTaskSettings`). 08:45 IST cron fired clean Session 22 — no gap re-occurrence. |
| **Lesson** | Windows Task Scheduler default `DisallowStartIfOnBatteries=$true` + `StopIfGoingOnBatteries=$true` is a silent killer for laptop-based production systems. Apply battery flags to every market-hours task at task creation time, not after a gap is observed. Codified as CLAUDE.md operational finding. |

---

### TD-071 (closed) — Stale 2025 zones still showing ACTIVE due to `expire_old_zones()` order bug in `build_ict_htf_zones.py`

| | |
|---|---|
| **Closed** | 2026-05-06 (Session 21) |
| **Closing commit** | uncommitted (S21 patches still in working tree at S22 close) |
| **Fix applied** | `fix_td071_zone_pipeline_order.py` (v3 patch canon). expire_old_zones() rewritten — dropped `.eq("status","ACTIVE")` filter, added `.in_("timeframe",["W","D"])` (H carve-out per operator), added `.neq("status","EXPIRED")` idempotency guard. Pipeline reorder in main(): expire moved from BEFORE upserts to AFTER recheck_breached_zones(). Final order: detect → upsert(ACTIVE) → recheck(price-breach) → expire(date). Backup `_PRE_S21_TD071.py` preserved. |
| **Validation** | Session 21 18:33 IST verification rebuild: 18 stale BREACHED W zones flipped to EXPIRED correctly (the very issue TD-071 was filed to fix). Session 22 08:45 IST cron: 82 zones written, 0 ON CONFLICT errors, expiry transitions correct. |
| **Lesson** | Pipeline ordering matters in idempotent zone management — the order detect → upsert → recheck → expire is the only correct one because: (a) detect produces new candidates; (b) upsert writes ACTIVE for new + leaves existing untouched; (c) recheck flips status based on price action across new + existing; (d) expire flips date-based across all. Reordering any step makes the sequence non-idempotent or produces wrong final state. |

---

### TD-070 (closed) — `prev_move < 0` over-filters BULL_OB candidates in `detect_weekly_zones()` (TD-070 v1 + v2 dedup stack)

| | |
|---|---|
| **Closed** | 2026-05-06 (Session 21) |
| **Closing commit** | uncommitted (S21 patches still in working tree at S22 close) |
| **Fix applied** | TWO-STAGE FIX: **Stage 1 (TD-070 v1):** `fix_td070_weekly_ob_lookback.py` replaced single-bar `prior_move < 0` check in detect_weekly_zones() with 8-week unbreached-anchor lookback via new `_find_unbreached_anchor()` helper (`TD070_LOOKBACK_WEEKS = 8`); symmetric BULL_OB + BEAR_OB; body-based breach test; most-recent-bearish anchor selection; backward-compat preserved. **Stage 2 (TD-070 v2 dedup):** Initial v1 deploy crashed live with Postgres 21000 'cannot affect row a second time' error on upsert ON CONFLICT. Root cause: 8-week lookback can produce multiple zone entries from same source-bar-date → same conflict key (symbol, timeframe, pattern_type, source_bar_date, zone_high, zone_low). Fixed via `fix_td070_v2_dedup.py` adding `_dedup_zones_by_conflict_key()` to collapse zones matching upsert ON CONFLICT key, keeping earliest valid_from. Backups `_PRE_S21.py`, `_PRE_TD070V2.py` preserved. |
| **Validation** | Session 21 18:33 IST verification rebuild: NIFTY 37 W zones + SENSEX 39 W zones = 78 total, zero ON CONFLICT errors. Session 22 08:45 IST cron: 82 zones written cleanly. **Verification gap: TD-078 PENDING** — Apr-13 BULL_OB SQL not yet run to confirm new lookback actually catches sustained-bull-week BULL_OB candidates that prev_move<0 would have rejected. |
| **Lesson** | (a) When relaxing a filter to widen acceptance, ALWAYS verify that the upsert ON CONFLICT key handles the new multiplicity. The 8-week lookback can produce 1-3 zone entries per source bar; ON CONFLICT predicate must dedupe upstream of the upsert. (b) `prev_move < 0` single-bar check was a simplified ICT canon shortcut; canonical ICT allows scanning 1-3 bars back for any bearish candle. The simplification was wrong in sustained bull markets. (c) v3 patch canon (read_bytes+utf-8-sig, normalize CRLF→LF, ast.parse validate, idempotency guard, write_bytes preserve LF, output `_PATCHED.py` then operator-rename) is the only correct way to apply Python source patches on Windows; bare PowerShell string-replacement breaks on encoding/line-endings. |

---

### TD-058 (closed) — Live `detect_ict_patterns.py` emitted zero BEAR_FVG signals across full year

| | |
|---|---|
| **Closed** | 2026-05-03 (Session 17) |
| **Closing commit** | `pending` (Session 17 batch — both detector and runner patches deployed Local + AWS; `_PRE_S17.py` and `_PRE_S17_TD060.py` snapshots preserved) |
| **Fix applied** | `patch_td058_bear_fvg_emission.py` made 5 surgical edits across 2 files: (1) `detect_ict_patterns.py` `OPT_TYPE` dict added `BEAR_FVG: PE`; (2) `DIRECTION` dict added `BEAR_FVG: -1`; (3) `detect_fvg()` body added BEAR predicate `prev.low > nxt.high and (prev.low - nxt.high)/ref >= min_g` mirroring the BULL clause; (4) zone-construction `elif pattern_type == "BEAR_FVG"` block added with `zone_high = bars[idx-1].low`, `zone_low = bars[idx+1].high`; (5) `experiment_15_pure_ict_compounding.py` `build_simulated_htf_zones()` 1H BEAR_FVG mirror added. Originals preserved as `_PRE_S17.py`. |
| **Validation** | Re-run of Exp 15 simulator on full-year cohort: BEAR_FVG signal count went from 0 → 138 across 12 months. Combined NIFTY+SENSEX P&L: ₹11.7L → ₹12.6L (+22.8pp lift on already-strong baseline). Per-pattern T+30m analysis confirmed BEAR_FVG WR 45.7% [37.6, 54.0] (CI spans 50% — coin flip standalone, parallel to BULL_FVG; cluster effect to be measured separately per ENH-90 candidate). Section 17 of `analyze_exp15_trades.py` confirmed bear-side FVG detection now functional across all regimes. |
| **Lesson** | Parallel direction-asymmetric defects exist across the codebase: Session 15 fixed the same pattern in `build_ict_htf_zones.py` (zone-builder side); Session 17 fixed the live-detector mirror. Whenever a direction-asymmetric bug surfaces in one component, audit the parallel component immediately — same author, same era, same blind spot likely applies. Codified as a check pattern in CLAUDE.md Session 17 footer. |

---

### TD-003 (closed) — `experiment_15b` `detect_daily_zones` date type mismatch

| | |
|---|---|
| **Closed** | 2026-04-13 (Appendix V18F follow-on session) |
| **Closing commit** | `<hash>` |
| **Fix applied** | `_daily_str = {str(k): v for k, v in daily_ohlcv.items()}` passed to `detect_daily_zones`. LOT_SIZE corrected: NIFTY=75, SENSEX=20. |
| **Lesson** | `date.fromisoformat()` inside `detect_daily_zones` requires string keys; tracking it as TD vs OI made the lifecycle visible. |

---

### TD-008 (closed) — Enhancement Register ENH-72 status drift

| | |
|---|---|
| **Closed** | 2026-04-22 (same session as discovery) |
| **Closing commit** | Session 2026-04-22 batched [OPS] commit (hash TBD at commit time) |
| **Fix applied** | `fix_td008_enh72_register_flip.py` — performed 5 exact string-match replacements in `MERDIAN_Enhancement_Register.md` (lines at ~114, 152, 1892, 1999, 2064), flipping `PROPOSED` → `CLOSED 2026-04-21`. Appended 1,916-byte closure block after the ENH-72 detail section with commit chain `3a22735..f121fca` and per-script live-validation numbers. File size 114,396 → 116,392 bytes. Backup preserved at `.pre_td008.bak`. |
| **Validation** | `Select-String` for `ENH-72.*PROPOSED` returns zero results post-patch. `Select-String` for `ENH-72.*CLOSED` returns 5+ matches (original 5 flipped locations + new matches in the closure block). |
| **Lesson** | Documentation-drift between the JSON authoritative-state layer and the markdown human-readable register is a real class of bug. The `enhancement_register_delta_<date>.md` delta-file pattern used on 2026-04-21 was an anti-pattern — it deferred the real register update indefinitely. **Going forward:** when an ENH closes, update the unified register in the same commit as the JSON and the session_log. No delta files. |

---

### TD-014 (closed) — `ingest_breadth_from_ticks.py` write-contract instrumentation

| | |
|---|---|
| **Closed** | 2026-04-23 (Session 7) |
| **Closing commit** | `1630726` |
| **Fix applied** | Added `_write_exec_log()` helper and instrumentation at all exit paths of `main()`. Writes one row to `script_execution_log` per invocation with `host='local'`, `exit_code`, `exit_reason` from `chk_exit_reason_valid` enum (SUCCESS / SKIPPED_NO_INPUT / DATA_ERROR), `contract_met` flag, `actual_writes` JSONB. `contract_met` is True iff `coverage_pct >= 50%` AND `market_breadth_intraday` write succeeded. Telemetry write wrapped in try/except so failure cannot crash the pipeline (preserves write-path correctness regardless of telemetry state). |
| **Validation** | Tested 2026-04-23 19:09 IST — `SKIPPED_NO_INPUT` path exercised (market closed, no ticks in 10-min window). Row written to `script_execution_log` with `host='local'`, `exit_code=1`, `contract_met=false`, `actual_writes={market_breadth_intraday:0, breadth_intraday_history:1}`. Production run 2026-04-24 first cycle 09:31 IST exercised SUCCESS path with realistic 291/983 BEARISH breadth, `contract_met=true`. |
| **Lesson** | Write-contract instrumentation on every persistence-side script is non-optional. Without `script_execution_log` rows, the 27-day breadth cascade silent failure had no detection signal. The `coverage_pct >= 50% + write_succeeded` rule is what makes the contract enforceable rather than aspirational. ENH-71 (foundation) + ENH-72 (propagation to 9 critical scripts) + this TD-014 (10th, breadth-specific) form the full instrumentation layer. |

---

### TD-019 (closed) — `hist_spot_bars_5m` pipeline stale since 2026-04-15

| | |
|---|---|
| **Closed** | 2026-04-26 (Session 9) |
| **Closing commit** | `<hash>` (Session 9 commit batch) |
| **Fix applied** | Three changes in one session (override of no-fix-in-diagnosis-session rule logged): (1) Patched `build_spot_bars_mtf.py` with ENH-71 `core.execution_log.ExecutionLog` instrumentation. `expected_writes={"hist_spot_bars_5m": 1, "hist_spot_bars_15m": 1}` (minimum-1 row semantics); try/except wrap → `CRASH` exit reason on unhandled exceptions. (2) Backfilled 42,324 5m rows + 14,440 15m rows via `python build_spot_bars_mtf.py`, 116s, idempotent on `idx_hist_spot_5m_key` / `idx_hist_spot_15m_key`. (3) Registered `MERDIAN_Spot_MTF_Rollup_1600` Task Scheduler task. Daily 16:00 IST Mon-Fri via `run_spot_mtf_rollup_once.bat` wrapper (mirrors existing MERDIAN task pattern; logs to `logs\task_output.log`). |
| **Validation** | `script_execution_log` shows two SUCCESS rows for `build_spot_bars_mtf.py` on 2026-04-26 (manual run 11:22 IST, smoke-test invocation via Task Scheduler 11:37 IST). Both `contract_met=true`, both `actual_writes={"hist_spot_bars_5m": 42324, "hist_spot_bars_15m": 14440}`, durations 116s and 118s. `Get-ScheduledTaskInfo MERDIAN_Spot_MTF_Rollup_1600` returns `LastTaskResult=0, NextRunTime=2026-04-27 16:00:00`. |
| **Files changed** | `build_spot_bars_mtf.py` (patched in place; `+1841` bytes; backup `build_spot_bars_mtf.py.pre_td019.bak`). New: `run_spot_mtf_rollup_once.bat`, `register_spot_mtf_rollup_task.ps1`, `fix_td019_instrument_build_spot_bars_mtf.py`, `fix_td019_add_sys_import.py`. Updated: `merdian_reference.json` (build_spot_bars_mtf entry status + cadence + scheduled_tasks block + ENH-73 + TD entries), `tech_debt.md` (this entry + TD-023..026), `CURRENT.md` (full rewrite for Session 10), `session_log.md` (one-liner). |
| **Lesson** | (a) "Manual on-demand rebuild" is a data-pipeline anti-pattern — it survives one operator's memory gap by exactly zero days. Every writer to a production table must be both instrumented (ENH-71) and scheduled. (b) Q-A pattern (`script_execution_log.actual_writes::text LIKE '%<table>%'`) is the canonical detector for uninstrumented producers — the absence of a hit IS the smoking gun. Filed as TD-023 to audit-and-patch the rest of the producers. (c) Override of "no fix in diagnosis session" rule was justified by the user this session ("overheads are too much to carry to next") but burned the firebreak that the rule was protecting. The rule pays its rent across multiple sessions; future overrides should be rare and explicit. |

---

### TD-020 (closed) — LONG_GAMMA gate on 2026-04-24 strongly directional day -- diagnosis required before ADR-002 ratification

| | |
|---|---|
| **Closed** | 2026-04-26 (Session 9 reframing; Session 8's prior close was incorrect) |
| **Closing commit** | `<hash>` (Session 9 second-batch commit) |
| **Original Session 8 disposition (NOW SUPERSEDED):** Concluded "gate had no signals to filter; ICT detector silent" and pointed at TD-022 as the real cause. That conclusion was wrong. |
| **Corrected disposition (2026-04-26, Session 9):** The LONG_GAMMA gate DID fire on every 2026-04-24 cycle, exactly as designed. Source path in `build_trade_signal_local.py`: when `gamma_regime == "LONG_GAMMA"`, three things happen in sequence: `cautions.append(...)`, `action = "DO_NOTHING"`, `trade_allowed = False`, **`direction_bias = "NEUTRAL"`**. The gate setting `direction_bias=NEUTRAL` is part of firing, not evidence the gate received nothing. Session 8 saw the gate's OUTPUT (NEUTRAL/DO_NOTHING) and read it as the gate's INPUT (no signals). |
| **Evidence (Session 9 verification):** Q-022-A: 245 signal_snapshots rows on 04-24, all `direction_bias='NEUTRAL'`, all `action='DO_NOTHING'`, `gamma_regime='LONG_GAMMA'` on every row, `net_gex` strongly positive throughout. Q-022-10: gamma_regime breakdown 04-20 to 04-24 confirmed 100% LONG_GAMMA / NO_FLIP coverage on 04-22 / 04-23 (NIFTY) / 04-24 — and on those exact dates, zero PE rows. PE rows fired only in the brief SHORT_GAMMA windows on 04-21 (3 PEs) and 04-23 (35 PEs). |
| **Why this matters:** The gate is mechanically correct. The question of whether it should have fired on a -1.6%/-1.4% directional cascade day is a CALIBRATION question, not a BEHAVIOUR question. ENH-35's 47.7% historical accuracy on LONG_GAMMA cycles validates the gate against a population average; whether the directional sub-population within LONG_GAMMA is mis-served is the question Exp 28/28b investigated (see Compendium). |
| **Files referenced (no code changed for this TD):** `build_trade_signal_local.py` (read-only confirmation of gate logic in the LONG_GAMMA branch). |
| **Validation:** None coded. The disposition is documentary — a corrected reading of existing live data. |
| **Lesson** | When a gate's design includes mutating the inputs it conditions on (here: gate sets `direction_bias=NEUTRAL` AS PART of firing), reading the resulting state to ask "did the gate fire?" is circular. Always trace the gate from its trigger, not from its visible aftermath. Session 8 made the inverse error and chained TD-022 onto a flawed premise; Session 9's deep-dive into source restored the ordering. Going forward, any TD that hypothesises "gate did/didn't fire" must verify by reading source flow, not output state. |

---

### TD-048 (closed) — BEAR_FVG missing across detector pipeline (13-month silent bug)

| | |
|---|---|
| **Closed** | 2026-05-02 (Session 15) |
| **Closing commit** | `8543e08` (Session 15 commit batch — production patches to `build_ict_htf_zones_historical.py` and `build_ict_htf_zones.py`, full historical backfill, signal table rebuild) |
| **Original symptom** | `hist_pattern_signals` contained 0 BEAR_FVG signals over 13 months across NIFTY + SENSEX (2025-04 → 2026-04), despite 1,129 canonical BEAR-FVG 3-bar shapes existing in `hist_spot_bars_5m` over 60d alone, and 46-50% of recent sessions being bear-direction days. `hist_ict_htf_zones` had 0 BEAR_FVG of 35,862 rows pre-fix. |
| **Discovery vehicle** | Exp 50 (FVG-on-OB cluster vs standalone) ran during Session 15. Operator challenged the "0 BEAR_FVG over 13 months" finding as impossible per market structure — sustained bear periods clearly visible on weekly chart Apr 2024-2026, NIFTY -17% Aug 2024 → Mar 2025. Triggered `diagnostic_bear_fvg_audit.py` 5-step audit (S1 distinct pattern_type counts; S2 schema + direction columns; S3 sibling tables; S4 daily candle bear-share; S5 manual canonical 3-bar BEAR_FVG shape scan in `hist_spot_bars_5m`). Audit conclusive on H1 (detector-side asymmetry): 1,129 canonical shapes in 5m bars vs 0 in `hist_pattern_signals` = bug must be detector or signal builder. Subsequently traced: `build_hist_pattern_signals_5m.py` is direction-symmetric (innocent — would emit BEAR_FVG signals if zones existed); bug is upstream in zone builders. |
| **Root cause** | Zone builders had no BEAR_FVG branch in `detect_weekly_zones()` (only BULL_FVG implemented). `detect_daily_zones()` had no FVG detection of either direction. `detect_1h_zones()` (live builder only) had only BULL_FVG. Three locations affected, two scripts. Code review of `build_ict_htf_zones_historical.py` surfaced six bugs ranked S1 (symptom-causing, fixed) / S2 (related but separate, catalogued as TD-049, TD-050) / S3 (cosmetic but real, catalogued as TD-051, TD-052). |
---

### TD-S30-CANDIDATE-1 — Live `compute_gamma_metrics_local.py` regressed on TD-NEW-3 Cr unit conversion (~10^7 factor too large)

| | |
|---|---|
| **Severity** | S2 (consumers using `gamma_concentration` ratio + `flip_distance_pct` are unit-invariant and unaffected; consumers using `net_gex` magnitude thresholds would be biased; data-integrity audit material) |
| **Discovered** | 2026-05-15 (Session 29 — surfaced during full-year `gamma_metrics` backfill parity comparison: backfill `net_gex` is in plausible ±10K-1M Cr range; live `gamma_metrics` rows post-S27 commit `241f943` show ±trillions/quadrillions; ratio matches exactly the `/1e7` Cr conversion that TD-NEW-3 was supposed to apply. Live writer apparently regressed at some point between S27 close commit `241f943` and S29 start.) |
| **Component** | `compute_gamma_metrics_local.py` net_gex unit handling — TD-NEW-3 S27 mandated `/1e7` to convert raw rupees → Crores. Regression site to be identified via `git log -p compute_gamma_metrics_local.py | grep -E '1e7\|net_gex'` between S27 close (`241f943`) and present HEAD. |
| **Symptom** | `gamma_metrics.net_gex` in live cycle rows is ~10^7 too large vs expected Cr-scale magnitudes. Backfill writer (independent reimplementation) writes correct Cr-scale values. Difference is unit conversion, not signal direction. |
| **Root cause** | UNCONFIRMED — needs git log + diff investigation. Hypothesis: a refactor or bundled commit removed the `/1e7` line that TD-NEW-3 added; alternatively the constant is applied but at a wrong point in the compute chain. |
| **Workaround** | Phase 0b consumers in S29 only use `gamma_concentration` (ratio) + `flip_distance_pct` (signed scalar in pct points) — both unit-invariant. Phase 1+ buyer-side consumers that may threshold on `net_gex` magnitude would be biased. Recommend: use backfill values for any analysis comparing magnitudes across history. |
| **Proper fix** | (S30 work) — identify regression commit via `git log -p compute_gamma_metrics_local.py` between `241f943` and current; restore `/1e7` conversion; re-validate via live cycle parity comparison against backfill output. |
| **Cost to fix** | <1 session (git diff + 1-line patch + smoke test). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-15 (filed as TD-S30 candidate at S29 close) |

---

(End of S29 new TDs section — original Active debt continues below)

| **Fix applied** | Three patches in two scripts: (a) **S1.a** = added W BEAR_FVG branch in `detect_weekly_zones()` mirroring the existing W BULL_FVG branch; threshold `FVG_W_MIN_PCT=0.10%`. (b) **S1.b** = added D BULL_FVG and D BEAR_FVG detection in `detect_daily_zones()`; new constants `FVG_D_MIN_PCT=0.10%` and `D_FVG_VALID_DAYS=5` (D-FVG validity window 5 calendar days, longer than D-OB which retains TD-050's 1-day issue). (c) **S15-1H** = added BEAR_FVG branch to `detect_1h_zones()` in live builder mirroring existing BULL_FVG branch. Patches applied to both `build_ict_htf_zones_historical.py` (S1.a + S1.b) and `build_ict_htf_zones.py` (S1.a + S1.b + S15-1H). |
| **Backfill executed** | (1) `build_ict_htf_zones_historical_PATCHED.py` full backfill: 264 NIFTY + 263 SENSEX trading days = 40,384 rows written to `hist_ict_htf_zones`. Counts: W BEAR_FVG=1,384, W BULL_FVG=2,603 (ratio 0.53 — bull-trend regime, makes sense), D BEAR_FVG=79, D BULL_FVG=84 (ratio 0.94 — symmetric, makes sense). (2) `build_ict_htf_zones_PATCHED.py --timeframe both` live run: 85 zones written to `ict_htf_zones`, 10 ACTIVE per symbol post breach-recheck. (3) `build_hist_pattern_signals_5m.py` (no code change — direction-symmetric verified): `hist_pattern_signals` 6,318 → 7,484 rows. **BEAR_FVG: 0 → 795.** |
| **Files renamed (after backfill verified)** | `build_ict_htf_zones.py` and `build_ict_htf_zones_historical.py` ARE NOW the patched versions; originals preserved as `build_ict_htf_zones_PRE_S15.py` and `build_ict_htf_zones_historical_PRE_S15.py`. Scheduled task `MERDIAN_ICT_HTF_Zones` (08:45 IST Mon-Fri) automatically uses patched live builder going forward. |
| **End-to-end re-verification** | `diagnostic_bear_fvg_audit.py` re-run post-rebuild: BEAR_FVG count 795 (was 0). NIFTY 60d signals: BULL_FVG 274 / BEAR_FVG 150. SENSEX 60d: BULL_FVG 263 / BEAR_FVG 208. Asymmetry 1.83x (NIFTY) / 1.26x (SENSEX) noted as residual finding — canonical 5m shapes are ~symmetric (NIFTY 562 BEAR / 587 BULL; SENSEX 567 / 575) so signal builder may have a regime-driven bull-skew filter. Filed as TD-056 for investigation. |
| **Bugs intentionally NOT fixed (catalogued as separate TDs)** | TD-049 (D-OB definition non-standard ICT — uses move bar K+1 as OB instead of opposing prior K), TD-050 (D-zone non-FVG validity = 1 day), TD-051 (PDH/PDL `+/-20pt` hardcoded), TD-052 (zone status workflow write-once-never-recompute on historical builder). All four candidates for Session 16 Candidate D. Decision to ship S1 only was deliberate: low-risk symmetric mirror of existing logic, unblocks Exp 50/50b re-run on bidirectional data without forcing definition-change discussions in the same session. |
| **Lessons** | **(a) Verify experiment results against market reality before believing them.** Operator's chart-based challenge to "0 BEAR_FVG over 13 months" was the only thing that surfaced this 13-month silent bug — the zone builder, signal builder, and downstream consumers had been running clean across multiple sessions without anyone noticing the asymmetry. The bug was discoverable by inspection but not by automated test. **(b) Full-file PATCHED.py copies + post-verification rename is the safe deploy pattern (vs in-place edit).** Allows dry-run, real-run, end-to-end verification, and rollback as discrete steps; rollback is one rename. Operator preferred this pattern over `.bak` files. **(c) When a known-incomplete detector (S1.a / S1.b) is being patched, run a code review to surface what else is wrong before patching** — the six-bug catalogue (TD-049/050/051/052 + S1.a + S1.b) emerged from one review pass; spreading discovery across multiple sessions would have been more expensive. **(d) Direction-symmetry verification on the signal builder before patching the detector** — by confirming `build_hist_pattern_signals_5m.py` was innocent first, Session 15 avoided the trap of patching the signal builder symptomatically while leaving the zone-builder root cause intact. The 5-step audit S5 (canonical shape scan) was the test that proved this. |

---

### TD-061 (closed) — Task Scheduler entry points spawn visible console windows (S29 RESOLUTION)

| | |
|---|---|
| **Severity at close** | S2 → RESOLVED |
| **Discovered** | 2026-05-03 (Session 17) |
| **Closed** | 2026-05-14 (Session 29 firefighting — full closure after S17/S18 partial closure was insufficient; body-state-vs-footer-claim divergence documented as Doc Protocol v4 candidate Rule N input) |
| **Root cause confirmed** | Task action ran `python.exe` (console) instead of `pythonw.exe` (no-console). Earlier sessions migrated 4/19 tasks; S29 completed the remaining 9 migrations + hardened settings on 18/19 tasks. |
| **Fix applied** | (1) `migrate_to_pythonw.ps1` (v2 — v1 abandoned due to regex shell-redirection capture bug). Two-phase application: phase 1 hit 13 .bat-wrapping tasks via regex-extract-py-script-path approach; v1 captured shell redirection metacharacters as `pythonw` args (caught before -Apply by dry-run review); v2 whitelisted argument shapes + blacklisted shell metas. Phase 2 (after operator pasted 4 wrapper-internal contents) dropped 4 PowerShell/.bat wrappers that called `pythonw.exe` internally — re-pointed tasks at the `pythonw.exe` direct invocation. (2) New `run_ict_htf_zones_daily.py` Python orchestrator replaces `.bat` for ICT_HTF_Zones_0845 (the 3-step chain with rc-fold + banner format couldn't collapse to single pythonw call). `sys.executable` propagation ensures pythonw all the way down. (3) Settings tightened on 18/19 tasks: `Hidden=$true + MultipleInstances=IgnoreNew + ExecutionTimeLimit=30min + battery flags`. |
| **State at close (S29 audit final)** | **13 of 19 actions on pythonw.exe** (was 4 at S29-start). **18 of 19 settings tightened.** Residual 5 window-flash sources are low-frequency: `Intraday_Supervisor_Start` (08:00 + logon — multi-trigger XML quirk in PowerShell `Set-ScheduledTask` blocked the single settings update; documented as known limitation), `Watchdog` (interval, PowerShell so can't migrate to pythonw), `Intraday_Session_Start` (cadence pending operator verification — newly-discovered S29 task), `Dhan_Token_Refresh` (once-per-morning), `Market_Tape_1M` (broken since 2026-04-07; firing daily as Ready but failing 401). |
| **Backups** | `backups\scheduler\20260514_184211\*.xml` (18 task XMLs from v1 -Apply run); `backups\scheduler\20260514_190443\*.xml` (4 task XMLs from phase-2 wrapper-drop run). Rollback path: `Register-ScheduledTask -Xml (Get-Content <backup>.xml -Raw) -TaskName <name> -Force`. |
| **Orphaned wrappers (cleanup pending)** | `run_ict_htf_zones_daily.bat`, `run_eod_breadth_refresh.ps1`, `run_iv_context_once.ps1`, `run_po3_session_bias_once.bat` — kept on disk unreferenced from Task Scheduler. Delete in cleanup pass after 1 week of new-config stability (operator action 2026-05-21+). Filed in System Map §A.9. |
| **Lessons** | **(a) TD body-state must match footer-claim** (Doc Protocol v4 candidate Rule N) — S18 footer claimed TD-061 RESOLVED; body remained Active; S23 audit confirmed only 4/15 migrated; the discrepancy was visible in Topology §7.2 but never reflected back. **(b) Regex capture of arbitrary trailing tokens unsafe in command-injection contexts** (B28) — v1 of `migrate_to_pythonw.ps1` greedily captured `>>`, `2>&1`, etc. as pythonw args. **(c) Wrapper-to-direct migration: comments vs code state alignment** — when retiring a `.bat`/`.ps1`, document orphaning explicitly so future operators don't grep-discover the stale file as if it were canonical. **(d) Single-trigger `Set-ScheduledTask` reliability ≠ multi-trigger** — multi-trigger tasks (Weekly + AtLogon on Supervisor) require full XML re-register instead. |
| **Related** | TD-063 (single-instance enforcement — bundled into same `migrate_to_pythonw.ps1` settings pass; both RESOLVED same session), CLAUDE.md B24 + B25 + B26 + B27 + B28 (S29 anti-pattern lines), Topology §7.2 (19-task table rewrite S29), CLAUDE.md S29 settled-decisions footer entry. |

---

### TD-063 (closed) — Single-instance enforcement missing on Task Scheduler tasks (S29 RESOLUTION)

| | |
|---|---|
| **Severity at close** | S3 → RESOLVED |
| **Discovered** | 2026-05-03 (Session 17) |
| **Closed** | 2026-05-14 (Session 29 firefighting — bundled into TD-061 settings pass) |
| **Root cause** | Default `MultipleInstances=Parallel` allowed new instance to attempt start even when previous still running, leading to `2147946720` errors observed in S17. |
| **Fix applied** | `MultipleInstances=IgnoreNew` applied on 18/19 MERDIAN_* tasks via `migrate_to_pythonw.ps1` v2 settings pass. Skipped new fire if previous still running; symptom of TD-062 stuck-process accumulation is now self-clearing on each successive trigger. |
| **State at close** | 18/19 tasks hardened. The 1 failure: `MERDIAN_Intraday_Supervisor_Start` retains loose settings due to multi-trigger XML quirk in PowerShell's `Set-ScheduledTask -Settings <obj>` (Weekly Mon-Fri + AtLogon = two triggers, `Set-ScheduledTask` couldn't apply settings cleanly). Workaround documented in Topology §7.2 Note: build full `Register-ScheduledTask` XML + `Force` overwrite, or skip settings-only update for multi-trigger tasks. Filed as TD candidate for next Task Scheduler touch. |
| **Backups** | Same as TD-061 (bundled). |
| **Related** | TD-061 (bundled — same migration script + same session closure), TD-062 (stuck-process root cause — IgnoreNew makes TD-062 self-clearing rather than ever-accumulating; TD-062 root cause investigation remains open but is now less urgent). |

---

### TD-NEW-A (closed) — `market_ticks` retention runaway → 62 GB bloat → INSERT timeouts (S29 IN-FLIGHT RESOLUTION)

| | |
|---|---|
| **Severity at close** | S1 → RESOLVED |
| **Discovered** | 2026-05-14 (Session 29 firefighting — during Incident §1 diagnosis of breadth cascade) |
| **Closed** | 2026-05-14 (Session 29 same-session — seventh same-session NEW+RESOLVED pattern after TD-097 S25 + TD-101 S26 + TD-NEW-2/3 S27 + TD-NEW-4/5/6/8/12/13 S28) |
| **Discovery trail** | Initial hypothesis was simple token-stale (matched 2026-04-22 pattern); operator ran token-refresh twice with no improvement. Restart of `ws_feed_zerodha.py` revealed `Supabase write error 500: {"code":"57014","message":"canceling statement due to statement timeout"}` in feeder log — the smoking gun for second root cause. Table size query: 62 GB total (22 GB heap + 40 GB indexes). `cron.job_run_details` query showed 10 consecutive `delete-old-market-ticks` (jobid 45) failures since at least 2026-04-30 with same statement_timeout error. Failed deletes accumulated unbounded; at ~62 GB even bulk INSERTs began exceeding statement_timeout, producing the cascade. |
| **Root cause** | Two-tier: (A) original schedule `30 14 * * 1-5` + horizon `2 days` produced a worst-case DELETE workload that, once table crossed a threshold, exceeded statement_timeout. (B) `cron.job_run_details` failures are invisible by default (no MERDIAN telemetry polls it; filed as TD-NEW-B). The combination meant pg_cron was silently failing for 14+ weekdays before downstream consumer (`ws_feed_zerodha.py`) noticed. |
| **Fix applied** | (1) `pkill -9 -f ws_feed_zerodha.py` to release write locks. (2) `TRUNCATE public.market_ticks` (62 GB → 856 kB in <1s; DDL primitive — DELETE itself would have timed out at this size). (3) `cron.unschedule(45)` retired the broken job. (4) `cron.schedule('prune-market-ticks', '*/30 * * * 1-5', $$DELETE FROM public.market_ticks WHERE ts < now() - interval '1 hour'$$)` created jobid 46. (5) Restart `ws_feed_zerodha.py`; verified next INSERT successful + no 500 errors in log. |
| **Design rationale (new schedule)** | Cadence increased 1/day → 1/30min (worst-case DELETE workload now ~30 min of accumulation ≈ ~1 GB, well inside statement_timeout). Horizon shortened 2 days → 1 hour (breadth ingest reads only last 10 min; 1-hour horizon caps table size at ~1 GB during active session). Active Mon-Fri = 1-5 unchanged (holiday no-feed produces no DELETE workload either way). |
| **Cost incurred** | `market_breadth_intraday`: 0 rows for 2026-05-14 (not recoverable — 10-min rolling window is ephemeral). `signal_snapshots.breadth_regime`: NULL for all 697 signals 2026-05-14 (replay reads `market_breadth_intraday` so also not recoverable). Operator hours: ~3h incident response. Trading: degraded signals 09:15 onwards; hybrid discretionary process compensated, no live trades on bad data. |
| **Lessons** | **B25 (TRUNCATE vs DELETE on bloated tables)** — for tables under statement_timeout pressure, DELETE itself is timing out; TRUNCATE is O(1) DDL primitive. **B26 (pg_cron failures invisible by default)** — `cron.job_run_details` is not polled; needs alerting layer (TD-NEW-B). **Compound-incident diagnostic discipline** — operator pattern-matched first hypothesis (token-stale) and tried fix twice with no improvement; the third diagnostic step (log tail of restarted process) revealed the independent second root cause. Codified into B24 + B25 + B26 + operational findings in CLAUDE.md S29 section. |
| **Related** | OI-12 RE-RESOLVED block in `MERDIAN_OpenItems_Register_v7.md` (same fix; OI-12 was originally closed 2026-04-14 with the now-failed jobid 45; permanent closure marker preserved per no-crunch but new closure block records the structural redesign). TD-NEW-B S1 (the alerting-layer fix for the silent-pg_cron-failure failure class), TD-NEW-C S2 (`ws_feed_zerodha.py` silent on Supabase 500 — the symptom-side counterpart). Topology §6.10 + §6.11 new gotchas. `CASE-2026-05-14-breadth-cascade-token-and-bloat.md` full incident chronology. |

---

### TD-NEW-I (closed) — Daily audit thresholds 370 → 365 (S29 RESOLUTION)

| | |
|---|---|
| **Severity at close** | S3 → RESOLVED |
| **Discovered** | 2026-05-14 (Session 29 firefighting) |
| **Closed** | 2026-05-14 (Session 29 same-session — eighth same-session NEW+RESOLVED pattern) |
| **Root cause** | `merdian_daily_audit.py` thresholds `spot_bars_per_symbol_min: 370` + `market_spot_snapshots_per_symbol: 370` were too tight against 98% coverage reality. 2026-05-14 audit returned `OVERALL: FAIL` on 367/375 NIFTY and 366/375 SENSEX (~98% coverage). Operational reality: 375 bars/day theoretical maximum (375 minutes 09:15→15:29 inclusive at 1-min cadence) but typical day has 2-5 known gap minutes from operational timing windows (writer cycle micro-jitter, Dhan endpoint stress, etc). |
| **Fix applied** | `patch_s29_td_new_i_j_v2.py` (v1 abandoned — regex undercaught threshold sites). 2 single-line changes in `merdian_daily_audit.py`: `spot_bars_per_symbol_min: 370 → 365`, `market_spot_snapshots_per_symbol: 370 → 365`. AST-validated. Backup `merdian_daily_audit_PRE_S29_TD_NEW_I_J_V2.py`. |
| **Verification** | 2026-05-15 daily audit should return PASS on the affected thresholds (1-day forward verification). Filed as auto-verification in `CASE-2026-05-14-spot-gap-backfill.md` §8 forward verification list. |
| **Lessons** | Audit thresholds should match operational reality, not theoretical maximum. ~98% coverage with known intra-day gap windows is healthy; 370 was a research-time threshold (when system was fresh and gap-free); 5 years of operational data shows 365 is the right baseline. Periodic threshold-vs-reality calibration pass is operationally healthy. |
| **Related** | TD-NEW-J (= TD-083; bundled into same patch script `patch_s29_td_new_i_j_v2.py`), `CASE-2026-05-14-spot-gap-backfill.md`. |

---

### TD-NEW-J (closed) — `capture_spot_1m_v2.py` emits 'OUTSIDE_MARKET_HOURS' against closed-set enum (= TD-083, S29 RESOLUTION)

| | |
|---|---|
| **Severity at close** | S3 → RESOLVED (also closes TD-083 as same root cause) |
| **Discovered** | 2026-05-07 (Session 22 — filed as TD-083); re-discovered S29 during script_execution_log attribution analysis showing daily false-alarm CRASH rows |
| **Closed** | 2026-05-14 (Session 29 — ninth same-session NEW+RESOLVED pattern; TD-NEW-J + TD-083 unified closure) |
| **Root cause** | `capture_spot_1m_v2.py` v2.1 added clean exit reasons (`'OUTSIDE_MARKET_HOURS'`, `'NO_DATA'`) that didn't exist in the `chk_exit_reason_valid` closed-set enum constraint. INSERT silently fails or gets reclassified as CRASH; daily false-alarm Telegram alerts. |
| **Fix applied** | `patch_s29_td_new_i_j_v2.py` made 2 surgical changes: (a) call-site L346: `"OUTSIDE_MARKET_HOURS"` → `"OFF_HOURS"` (matches enum's closed set); (b) docstring L36: `"OUTSIDE_MARKET_HOURS"` → `"OFF_HOURS (was OUTSIDE_MARKET_HOURS pre-TD-NEW-J 2026-05-14)"` — preserves grep-discoverability of the old name. Patch v1 was abandoned because its regex undercaught the docstring change site + risked docstring breakage. AST-validated. Backup `capture_spot_1m_v2_PRE_S29_TD_NEW_I_J_V2.py`. |
| **Verification** | 2026-05-15 forward: 0 CRASH rows attributable to `OUTSIDE_MARKET_HOURS` in `script_execution_log` from `capture_spot_1m_v2.py`. |
| **Lessons (B23 evolution)** | When a code-side string literal is renamed, the prose-side references must be updated in lockstep OR the prose rewritten to preserve grep-discoverability of the old name (the `(was X pre-TD-Y date)` pattern). v1 of the patch chose to leave docstring untouched; v2 chose the annotated rewrite. Future patch scripts should default to the annotated rewrite. |
| **Related** | TD-NEW-I (bundled into same patch script), TD-083 (same root cause; closed simultaneously). |

---

*MERDIAN tech_debt.md v1 — created concurrent with CLAUDE.md and Documentation Protocol v3. Updated Session 18 (2026-05-04): TD-061/063/056/065 RESOLVED, TD-062 PARTIAL (heartbeat foundation), TD-064/066/067 NEW (migrated from closed OpenItems Register). Updated Session 28 (2026-05-13): TD-NEW-4 + TD-NEW-5 + TD-NEW-6 + TD-NEW-8 + TD-NEW-12 + TD-NEW-13 RESOLVED same-session (six NEW+RESOLVED, fifth/sixth same-session pattern after TD-097 S25 + TD-101 S26 + TD-NEW-2/3 S27); TD-NEW-7 (S1, MALPHA→MERDIAN AWS Zerodha token automation) + TD-NEW-9 (S2, ws_feed silent-on-success heartbeat) NEW pending S29+; TD-NEW-10 CLOSED filed-in-error (merdian_order_placer.py confirmed intentional Phase 4B); TD-NEW-11 CLOSED documentation gap (Topology §3 + §7.1 + §8.2 updated in same-session S28 doc-close rewrite). **Updated Session 29 (2026-05-14 firefighting + 2026-05-14→2026-05-16 build): TD-061 + TD-063 RESOLVED (both were footer-claimed-RESOLVED at S18 with body-state Active — body-state-vs-footer-claim divergence; S23 audit confirmed only 4/15 migrated; S29 audit found 19 tasks and only 4/19 on pythonw at S29-start; S29 firefighting completed via `migrate_to_pythonw.ps1` v2 — 13/19 pythonw + 18/19 Hidden+IgnoreNew; new orchestrator `run_ict_htf_zones_daily.py` replaces `.bat`). TD-083 RESOLVED via TD-NEW-J unified closure (`capture_spot_1m_v2.py` exit_reason `'OUTSIDE_MARKET_HOURS'` → `'OFF_HOURS'` via `patch_s29_td_new_i_j_v2.py`). TD-080 PROMOTED to S1 RECURRING (3rd documented occurrence: S22 + S28 + S29; ENH spec for Dhan 429 retry layer + circuit breaker is P0 carry-forward to S30). TD-094 RECLASSIFIED-STALE (vendor data replaced broken S22 Kite backfill; OI populated 99.9%; unblocks Phase 0b gamma-context dimensions). NEW + RESOLVED same-session (ninth/tenth same-session pattern): TD-NEW-A S1 (`market_ticks` 62GB bloat → INSERT timeouts → 6h breadth cascade — TRUNCATE + new cron jobid 46), TD-NEW-I S3 (audit thresholds 370 → 365), TD-NEW-J S3 (= TD-083). NEW + CLOSED in documentation: TD-NEW-E S3 (Topology §7.2 17→19 staleness — closed via §7.2 rewrite), TD-NEW-F S2 (`runbook_update_kite_flow.md` Step 2d missing — closed via 5 runbook edits). NEW pending S30+: TD-NEW-B S1 (`pg_cron` health-check daemon — alerting layer for cron.job_run_details failures), TD-NEW-C S2 (`ws_feed_zerodha.py` silent on Supabase 500 — merge with TD-NEW-9), TD-NEW-D S2 (`ws_feed_zerodha.py` log timestamps mislabeled UTC-as-IST), TD-NEW-H S2 (`backfill_volatility_snapshots.py` NULL `expiry_date` schema violation). TD-S30-CANDIDATE-1 S2 (live `compute_gamma_metrics_local.py` regressed on TD-NEW-3 Cr unit — net_gex in raw rupees ~10^7 too large vs backfill; investigate S30). Five same-session NEW+RESOLVED in single session (TD-NEW-A + TD-NEW-I + TD-NEW-J + TD-NEW-E + TD-NEW-F) — new session record. Update inline as items are added/closed; commit with `MERDIAN: [OPS] tech_debt — <action>`. **Updated Session 30 (2026-05-17 — diagnostic + production patch session): 5 NEW TDs filed pending S31+ at top of Active section — TD-S30-NEW-3 S1 (OB attachment broken at signal-builder layer; highest-leverage S30 finding; 4,882 BULL_OB zone-touches → 0.5% attached / 3,139 BEAR_OB → 0% attached; detection correct, defect at `enrich_signal_with_ict()` or callers; S31 P0 investigation), TD-S30-NEW-4 S2 (DTE=0 cohort N too small for verdict), TD-S30-NEW-5 S2 (gate stack inversion on gamma/breadth/vix — three gates suppress positive-EV buckets; per-gate dedicated study queued), TD-S30-NEW-6 S3 (replay_build_trade_signal.py lacks ENH-88 per ADR-008 header line 15 attestation; ~30 min patch), TD-S30-NEW-7 S3 (hold-time bucket study scope — N≥100 per exit-bucket measurement; live cohort shows T+10-20m optimal vs T+30m Compendium-settled). TD-S30-CANDIDATE-1 (S29 carry-forward, live `compute_gamma_metrics_local.py` Cr unit regression) remains un-actioned at S30 close; carries forward as S31 P0_PRIMARY (not retracted, not investigated). 0 TDs CLOSED Session 30; 1 carry-forward un-actioned. ENH-76/77/88 + tier mult ENV-DISABLED via commit `2604fc2` per D.13.1 cohort-translation general principle codification. **Updated Session 35 (2026-05-24 — TD-S34-NEW-4 closure + dual-source chain reader + Breeze surgical fill + ADR-012 SL writer ship): TD-S34-NEW-4 CLOSED-MECHANICAL — Resolution block appended; 81% zone-primitive recovery via ENH-106 v8/v8.1/v8.2 + Breeze 04-16 surgical fill; structural residual carries forward as TD-S35-NEW-1. 4 NEW TDs filed pending S36+ at top of Active section: TD-S35-NEW-1 S2 (HOCS strike-coverage structural limit — `ingest_option_chain_local` ATM±N capture window); TD-S35-NEW-2 S1 (pre-Apr-2026 chain vendor uncatalogued — critical institutional knowledge at risk, bus-factor-of-one); TD-S35-NEW-3 S4 (SENSEX Breeze symbology `stock_code="BSESEN"` not "SENSEX"); TD-S35-NEW-4 S3 (`build_ict_primitives.py upsert_outcomes` is INSERT-only on existing rows — schema column adds require manual DELETE before recompute populates new columns). 1 TD CLOSED in resolution block (TD-S34-NEW-4); 0 same-session NEW+RESOLVED this session. 7 TDs carry-forward un-actioned. ADR-012 IMPLEMENTED via writer v9 (5 sl_* columns + spot-anchored SL evaluation block); single-cell n=5 verified; full validation cohort gated on S36 TRUNCATE + full recompute. ADR-013 PROPOSED (Breeze canonical historical backfill source). ENH-109 PROPOSED (Breeze rollingoption + get_historical_data_v2 graduation). MERDIAN AWS instance ID drift surfaced (memory `i-0e60e4ed9ce20cefb` → console `i-0878c118835386ec2`; reconcile at S36).*
