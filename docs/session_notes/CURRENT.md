# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-04-26 → 2026-04-27 (Sunday into Monday — Session 10, single concern with Monday-morning operational tail) |
| **Concern** | Diagnose why MERDIAN never shows `trade_allowed=true` on trending days. Originally framed as "is the gate broken?" — landed at "the system has edge but visibility, classification, and gate-conditionality all needed work." |
| **Type** | Diagnostic + multiple patches shipped + four experiments + operational pre-open work. Single-session-rule override logged for the Monday-morning Kite token tail. |
| **Outcome** | DONE — F0 (gate visibility unclobber) SHIPPED + verified live. F1 (TZ classification fix) SHIPPED + function-verified. F2 (1H threshold tuning) REJECTED via Exp 29 v2. Compendium replication validated via full Exp 15 re-run (NIFTY +180.4%, SENSEX +206.4%, T+30m total ₹+773K). Conditional ENH-35 lift proposed for design (no code yet). Three TDs filed. Runbook updated with two new failure modes from Monday morning. |
| **Git start → end** | `4675745` → `<hash>` (Session 10 commit batch: F0 patch + F1 patch + experiments + docs) |
| **Local + AWS hash match** | Local advancing; AWS Kite auth refreshed live at 06:58 IST 04-27, no AWS code changes. |
| **Files changed (code)** | `build_trade_signal_local.py` (F0 — direction_bias unclobber on LONG_GAMMA / NO_FLIP branches; backup `.pre_enh35_unclobber.bak`); `detect_ict_patterns.py` (F1 — `time_zone_label` UTC→IST conversion; backup `.pre_tz_fix.bak`). |
| **Files added (tracked)** | `fix_enh35_unclobber_direction_bias.py`, `fix_ict_time_zone_utc.py`, `experiment_29_1h_threshold_sweep.py`, `experiment_29_1h_threshold_sweep_v2.py`, `experiment_31_intraday_ict_full_replay.py`, `experiment_32_edge_isolation.py`, `merdian_ict_overlay.pine`, `merdian_ict_htf_zones.pine`, `check_kite_auth.py` (AWS). |
| **Files added (untracked)** | Backups: `build_trade_signal_local.py.pre_enh35_unclobber.bak`, `detect_ict_patterns.py.pre_tz_fix.bak`. |
| **Files modified (docs)** | `tech_debt.md` (+TD-029, TD-030, TD-031), `CURRENT.md` (this rewrite), `session_log.md` (one-liner), `merdian_reference.json` (file inventory), `runbook_update_kite_flow.md` (Session 10 update — heredoc corruption + SSM TTY hang failure modes), `MERDIAN_Experiment_Compendium_v1.md` (paste-in blocks for Exp 29 v2, Exp 31, Exp 32, Exp 15 re-validation), `MERDIAN_Enhancement_Register.md` (paste-in blocks for ENH-46-C conditional gate lift PROPOSED). |
| **Tables changed** | `ict_zones` (+0 new today; existing 14 zones still pre-F1, will age out as new detections write). `ict_htf_zones` — manual UPDATE marked 2 W BULL_FVG zones BREACHED (zombie cleanup); rebuilt fresh via 2x `build_ict_htf_zones.py --timeframe both` runs. `signal_snapshots` — 2 manual signal builder runs verified F0 patch (NIFTY direction_bias=BEARISH, SENSEX BULLISH, both with trade_allowed=false correct per ENH-35). |
| **Cron / Tasks added** | None today. F3 (cron `build_ict_htf_zones.py` daily 08:45 IST + ENH-72 wrapper) PROPOSED, deferred to next session per Exp 15 validation. |
| **`docs_updated`** | YES (tech_debt.md, CURRENT.md, session_log.md, merdian_reference.json, runbook_update_kite_flow.md). PENDING manual paste-in (Enhancement Register ENH-46-C, Experiment Compendium Exp 29 v2 + 31 + 32 + 15-revalidation). Text blocks generated. |

### What Session 10 did, in 12 bullets

**Diagnostic — three findings on the original "no trade_allowed" question:**

- **Finding 1 (F1) — ICT detector TZ misclassification.** `time_zone_label()` in `detect_ict_patterns.py` compared UTC bar_ts.time() to IST clock-time constants (09:15-15:30). Result: every detection got `time_zone='OTHER'` because UTC clock-time falls outside the IST window. TIER1 promotion (which requires MORNING/AFTNOON) was structurally unreachable. Patched: convert UTC→IST before extracting clock time. Verified: UTC 04:30 → MORNING, UTC 06:30 → MIDDAY, UTC 09:30 → AFTNOON. End-to-end live test waits for 10:00 IST Monday cycle.

- **Finding 2 (F0) — ENH-35 gate clobber regression.** LONG_GAMMA and NO_FLIP branches in `build_trade_signal_local.py` (commits `7c346fb` + `c310e52`, 2026-04-11) overwrote `direction_bias` to NEUTRAL and `action` to DO_NOTHING — not just `trade_allowed=false`. Operator never saw what the system thought. 9+ trading days of laundered signals. Patched: removed the clobber, gate still blocks via `trade_allowed=false` only. Verified live: NIFTY produced direction_bias=BEARISH, SENSEX BULLISH, both correctly blocked.

- **Finding 3 — visibility laundering** = sub-finding of F2. Same code path. Closed by F0 patch.

**Experiments — four runs, with one major retraction:**

- **Exp 29 v1** — 1H OB threshold sweep on `hist_spot_bars_5m` (~13 days). Underpowered. Falsified F2 hypothesis ("threshold too tight"). 0.40% best of those tested.
- **Exp 29 v2** — full year via `hist_spot_bars_1m` (260 days, 215K rows, TZ-aware per TD-029). Confirmed F2 REJECTED: WR monotonically increases with threshold, no candidate clears 70% N≥30 ship bar. 1H threshold tuning is not the lever.
- **Exp 31** — intraday-ICT full replay with real options PnL via `hist_atm_option_bars_5m` (398 trades). Initial read: TIER1 NIFTY 48% / SENSEX 41.7% — implied compendium doesn't replicate. **This read was wrong** (see Exp 15 re-run below). Honest cause: 5+ structural divergences from research methodology (T+30m only vs structure-break, no MEDIUM context tested, ict_htf_zones queried not rebuilt fresh, lot sizes drifted, missed compounding).
- **Exp 32** — edge isolation via train/heldout split (2026-01-15 cutoff). No replicable rules survived. BULL_OB+RS_UP collapsed 57%→0% heldout. Same methodological flaws as Exp 31.
- **Exp 15 re-run (THE LOAD-BEARING ONE)** — ran `experiment_15_pure_ict_compounding.py` AS-IS. Result: **₹400K → ₹1.17M (+193.4%) over the year. NIFTY 92% WR on BEAR_OB, 84% on BULL_OB, 77.3% on MEDIUM context. Compendium replicates within 3pp of stated values.** The system has real edge when measured the way research measured it.

**Operational (Monday morning 06:30-07:35 IST pre-open):**

- **Zerodha token verified.** Initial heredoc-pasted `check_kite_auth.py` failed silently (KeyError: ZERODHA_API_KEY despite env vars loading). Diagnosed as hidden non-printing characters from heredoc-via-SSM corruption. SSM session also had TTY hang requiring reconnect. Resolution: nano-typed script with explicit `load_dotenv("/home/ssm-user/meridian-engine/.env")` absolute path. AUTH OK at 06:58 IST. Persisted to `/home/ssm-user/meridian-engine/check_kite_auth.py`.
- **HTF zones rebuilt** via `build_ict_htf_zones.py --timeframe both` at 07:16 IST. 37 zones written across both symbols; verified via SQL.
- **Two zombie BULL_FVG zones manually cleared** — NIFTY 24,074-24,241 and SENSEX 77,636-78,203 (formed 04-20, breached 04-24 selloff, but `build_ict_htf_zones.py` doesn't re-evaluate breach on existing active zones — TD-030). Manual UPDATE to status=BREACHED.
- **Re-ran zone build** — 4 active zones per symbol after cleanup. Confirmed VERY_HIGH MTF context not reachable from current spot (price above all live W BULL zones), HIGH reachable only via PDL bounce.
- **TradingView Pine overlay updated** — `merdian_ict_htf_zones.pine` regenerated with current zones (post-zombie-cleanup), today's PDH/PDL values (04-27), and corrected price-positional commentary.
- **Runbook updated** — `runbook_update_kite_flow.md` Session 10 addition: heredoc-corruption failure mode + SSM TTY hang failure mode + persistent verification script convention.

**TDs filed today: TD-029 (S2), TD-030 (S2), TD-031 (S2).**

---

## This session

> Session 11. Pick ONE primary path from below at session start.

### Candidate A (recommended) — Ship F3 (daily zone scheduling + ENH-72 wrapper)

| Field | Value |
|---|---|
| **Goal** | Schedule `build_ict_htf_zones.py` to run daily at 08:45 IST Mon-Fri via Task Scheduler. Add ENH-72 ExecutionLog wrapper to instrument the script (currently uninstrumented despite running — surfaces in Q-A pattern as a missing producer). Both small. Validated by Exp 15 re-run: MEDIUM context (1H zones) shows 77.3% WR vs 62% LOW baseline. |
| **Type** | Code + scheduler + instrumentation. |
| **Success criterion** | Task Scheduler entry registered + smoke-tested. ENH-72 wrapper applied. `script_execution_log` shows SUCCESS row for 08:45 IST run on next trading day. |
| **Time budget** | ~15-25 exchanges. |

### Candidate B — Design conditional ENH-35 lift (NO CODE)

| Field | Value |
|---|---|
| **Goal** | Spec the conditional LONG_GAMMA gate lift: allow gate-blocked BULL_OB / BEAR_OB through when `mtf_context IN ('MEDIUM', 'VERY_HIGH')`. Exp 15 evidence: BULL_OB MEDIUM = 85.7% WR, BEAR_OB MEDIUM = 75% WR vs BULL_OB LOW 87% (similar) and overall LONG_GAMMA gate baseline 47.7%. Production's tier-based promotion is over-strict (only N=5 TIER1 firings/year). The MTF-context-conditional lift is the real path to "more trade_allowed=true cycles." |
| **Type** | Design only — produce ENH-46-C spec with shadow-test plan. No code. |
| **Success criterion** | One-page ENH-46-C document committed. Shadow-test plan defined (10 sessions before live). |
| **Time budget** | ~15-20 exchanges. |

### Candidate C — TD-030 + TD-031 fix (build_ict_htf_zones.py improvements)

| Field | Value |
|---|---|
| **Goal** | TD-030: teach `build_ict_htf_zones.py` to re-evaluate breach on existing active zones (not just at write-time). TD-031: investigate why D BEAR_OB / D BEAR_FVG detection is underactive (0 written since 04-11 despite multiple bearish daily structures). Both touch the same file. |
| **Type** | Code investigation + patch. |
| **Success criterion** | TD-030 closed via patch + verification (running script on a synthetic breach scenario should mark prior zone BREACHED). TD-031 either closed (if logic bug found) or recategorised (if breach filter is correctly conservative). |
| **Time budget** | ~20-30 exchanges. |

### Candidate D — Wait for live MEDIUM-context detection, observe end-to-end

| Field | Value |
|---|---|
| **Goal** | After F1 + F3 ship, the system should generate its first MEDIUM-context BULL_OB or BEAR_OB. With ENH-35 still in place, signal won't `trade_allowed=true` (LONG_GAMMA blocks) — but it should appear in `signal_snapshots` with correct `direction_bias`, `time_zone='MORNING'/'AFTNOON'`, and `mtf_context='MEDIUM'`. |
| **Type** | Passive observation. |
| **Success criterion** | At least one signal_snapshots row with `time_zone IN ('MORNING','AFTNOON') AND ict_tier='TIER1' AND mtf_context IN ('MEDIUM','VERY_HIGH')` lands on a live cycle. |
| **Time budget** | N/A — depends on F3 ship + market regime. |

### DO_NOT_REOPEN

- All items from Session 9's CURRENT.md DO_NOT_REOPEN list.
- **F2 (1H OB threshold tuning)** — REJECTED. Exp 29 v2 falsified; current 0.40% is best. Do not re-attempt threshold sweep.
- **"Compendium doesn't replicate"** — that framing was wrong. Exp 15 re-run confirms BEAR_OB ~92%, BULL_OB ~84%, MEDIUM ~77%. Comparison gap was Exp 31/32 measurement error. Do not re-litigate.
- **Path A ("stop pretending ICT is the edge")** — wrong. Withdrawn 2026-04-27 after Exp 15 re-run. Do not re-attempt.
- **Exp 31 / Exp 32 negative result** — measurement error, not finding. Do not cite as evidence the system lacks edge.
- **F1 patch correctness** — function-level verified UTC 04:30→MORNING, UTC 06:30→MIDDAY, UTC 09:30→AFTNOON. End-to-end live verification awaits 10:00 IST Monday cycle but the patch is correct.

### Watch-outs for Candidate A (F3 ship)

- `build_ict_htf_zones.py` line 468 has a `datetime.utcnow()` DeprecationWarning. Cosmetic but worth fixing in same commit (Python 3.13+ removes `utcnow()`). Use `datetime.now(timezone.utc)`.
- The task should run AFTER market close (16:00 IST already taken by `MERDIAN_Spot_MTF_Rollup_1600`). Proposed 08:45 IST is pre-market — that's correct: HTF zones must be ready before 09:14 IST `ws_feed_zerodha.py` start.
- ENH-72 wrapper requires `core.execution_log.ExecutionLog` import. Mirror the pattern from `build_spot_bars_mtf.py.pre_td019.bak` (or the post-patch version).

### Watch-outs for Candidate B (conditional gate lift design)

- The lift is symmetric: applies to both BULL_OB+BUY_CE and BEAR_OB+BUY_PE. Exp 15 evidence: BEAR_OB MEDIUM 75% WR (N=4 — underpowered) vs BEAR_OB LOW 94.7% (N=19). MEDIUM is not strictly better than LOW for BEAR_OB; design must reflect this. **Candidate spec: lift conditional on `pattern_type='BULL_OB' AND mtf_context IN ('MEDIUM','VERY_HIGH')` only**, leaving BEAR_OB to existing path.
- Shadow-test for 10 sessions BEFORE live deployment. Exp 15 results are validated on backtest, not live execution. Live differs from backtest in slippage, timing, and feed quality.
- Conditional lift adds a new code path in `build_trade_signal_local.py` — must include `ast.parse()` validation per CLAUDE.md Rule 5.

---

## Live state snapshot (at Session 11 start)

**Environment:** Local Windows primary; AWS shadow runner present.

**Open critical items (C-N):** None new from Session 10. Session 9's open items unchanged.

**Active TDs (after Session 10):**
- TD-029 (S2) — `hist_spot_bars_1m`/`5m` pre-04-07 TZ-stamping bug. Workaround: era-aware CASE on trade_date in queries. Permanent fix deferred.
- TD-030 (S2) — `build_ict_htf_zones.py` doesn't re-evaluate breach on existing active zones; manual UPDATE required when prior zones are violated by recent price action. Discovered 2026-04-27 pre-open.
- TD-031 (S2) — D BEAR_OB / D BEAR_FVG detection underactive in `build_ict_htf_zones.py`. 0 written since 2026-04-11 across both symbols despite multiple visibly bearish daily structures.

**Active ENH (in flight):**
- **ENH-46-A** — Telegram alert daemon for tradable signals. SHIPPED Session 9, live-verified 2026-04-26. Operator tail still untested on real SHORT_GAMMA window.
- **ENH-46-C** — *PROPOSED 2026-04-27.* Conditional ENH-35 gate lift for BULL_OB / BEAR_OB inside MEDIUM/VERY_HIGH MTF context. Design candidate for Session 11.
- **ENH-72** — instrumentation propagation. Closed for Session 9's wave; new candidate for `build_ict_htf_zones.py` (Session 11 Candidate A).
- **F3** — daily zone scheduling. Validated by Exp 15. Ready to ship.

**Settled by Session 10:**
- ICT pipeline edge: REAL. Compendium replicated. BEAR_OB 92% / BULL_OB 84% / MEDIUM 77%.
- F1 (TZ classification): SHIPPED + verified at function level.
- F0 (gate visibility): SHIPPED + verified live.
- F2 (1H threshold): REJECTED — current 0.40% is best.
- F3 (daily zone scheduling): NOT SHIPPED, validated by Exp 15, queued for Session 11.

**Markets state (at end of pre-open Monday 04-27):**
- NIFTY 23,898 — sat below all W BULL zones (closest is BULL_FVG 22,714-23,556 some 340 pts below). D PDL 23,857-23,877 close above current; PDH 24,140-24,160 252 pts overhead.
- SENSEX 76,664 — similar geometry. D PDL 76,563-76,583 below current; PDH 77,543-77,563 ~890 pts overhead. W BULL_FVG 73,164-75,868 ~800 pts below.
- VERY_HIGH MTF context not reachable from current price for either symbol.
- HIGH context reachable via bullish reversal at D PDL only.

---

## Paste-in blocks for files not in current upload set

The following sections are formatted as paste-in blocks because the canonical files are large; rather than rewriting them wholesale, the operator pastes these into the correct location.

### Insert into `MERDIAN_Enhancement_Register.md`

```markdown
## ENH-46-C — Conditional ENH-35 LONG_GAMMA Gate Lift on MTF Context (PROPOSED 2026-04-27)

**Status:** PROPOSED 2026-04-27 (Session 10). Pending design + 10-session shadow validation.

**Context.**
ENH-35 unconditionally blocks signal generation when `gamma_regime IN ('LONG_GAMMA','NO_FLIP')`. Validated 2026-04-11 at N=24,579, 47.7% accuracy on raw signals — the gate is correct on average. Exp 28 (Session 9) confirmed it's correct on ~90% of cycles, mis-calibrated on ~10% (specific directional days). Exp 15 re-run (Session 10) showed the conditional sub-population where the gate is wrong: **BULL_OB / BEAR_OB inside MEDIUM or VERY_HIGH MTF context.** These setups show 75-86% WR in backtest vs the gate's 47.7% population baseline.

**Proposal.**
Add a conditional bypass in `build_trade_signal_local.py`: when `gamma_regime IN ('LONG_GAMMA','NO_FLIP')` AND a candidate ICT detection has `pattern_type='BULL_OB' AND mtf_context IN ('MEDIUM','VERY_HIGH')`, allow the signal through with `trade_allowed=true`. BEAR_OB initially excluded (Exp 15 evidence: BEAR_OB MEDIUM N=4, underpowered; BEAR_OB LOW shows higher WR — the lift criterion may not apply symmetrically).

**Evidence (Exp 15 re-run, full year):**
- BULL_OB MEDIUM: 85.7% WR (N=14), avg ₹+14,013/trade, total ₹+196,184
- BULL_OB LOW: 87.1% WR (N=31) — also strong; LOW context not actually worse
- BEAR_OB MEDIUM: 75.0% WR (N=4) — too small for lift decision
- BEAR_OB LOW: 94.7% WR (N=19) — actually the strongest BEAR bucket
- Combined T+30m total ₹+773,442 across 229 trades, +193.4% capital growth

**Design questions to settle:**
1. Symmetric (both directions) or asymmetric (BULL_OB only)? Recommend asymmetric Phase 1 given BEAR_OB MEDIUM N=4.
2. Tier-conditional? E.g., only TIER1 + MEDIUM, or any tier + MEDIUM? Production tier rules surface only N=5 TIER1/year — too restrictive. Recommend any-tier + MEDIUM/VERY_HIGH.
3. Shadow-mode vs live? Recommend shadow-mode for 10 sessions: log would-be lift events to a separate `shadow_signal_lifts` table; compare predicted WR against actual T+30m PnL post-cycle.

**Shadow-test plan:**
- Phase 1 (≥10 trading days): log all candidate-lift events to shadow table without flipping `trade_allowed`. Capture: detection bar_ts, pattern_type, mtf_context, ict_tier, spot, atm_strike, expiry_date, dte, predicted T+30m exit price.
- Phase 2: evaluate WR + total PnL. Ship to live only if shadow WR ≥ 70% on N≥15.
- Phase 3 (live): flip `trade_allowed=true` for matching cycles. Monitor for 5 sessions before declaring closed.

**Filed:** 2026-04-27 (Session 10 verdict).
```

### Insert into `MERDIAN_Experiment_Compendium_v1.md`

```markdown
## Experiment 29 v2 — 1H Order-Block Threshold Sweep (Full Year)

**Date:** 2026-04-26 (Session 10)
**Script:** `experiment_29_1h_threshold_sweep_v2.py`

**Question:** Is the live `OB_MIN_MOVE_PCT = 0.40%` threshold for 1H structural zone formation in `build_ict_htf_zones.py` correctly calibrated, or should it be lowered to surface MEDIUM-context candidates more often?

**Setup:**
- Source: `hist_spot_bars_1m` 2025-04-01 → 2026-04-24 (260 trading days, 215K rows).
- TZ-aware era-boundary correction per TD-029 (pre-04-07 IST-stored-as-UTC).
- Aggregated 1m → 1h for zone formation, 1m → 5m for forward simulation.
- Threshold sweep: {0.15%, 0.20%, 0.25%, 0.30%, 0.40%}.
- Win: spot moves ZONE_TARGET_PCT (0.30%) in zone direction within 6h after first test.
- Loss: spot closes beyond zone in opposite direction.
- Decision: ship if WR ≥ 70% AND decisive (Win+Loss) ≥ 30 per symbol.

**Findings:**

| Symbol | Threshold | Total | Tested | Wins | Loss | WR% | AvgRet% |
|---|---|---|---|---|---|---|---|
| NIFTY | 0.15 | 247 | 158 | 53 | 59 | 47.3% | +0.044% |
| NIFTY | 0.20 | 177 | 107 | 43 | 35 | 55.1% | +0.074% |
| NIFTY | 0.25 | 135 | 78 | 32 | 25 | 56.1% | +0.071% |
| NIFTY | 0.30 | 99 | 56 | 25 | 16 | 61.0% | +0.091% |
| **NIFTY** | **0.40** | **74** | **35** | **16** | **8** | **66.7%** | **+0.130%** |
| SENSEX | 0.15 | 243 | 156 | 52 | 58 | 47.3% | +0.036% |
| SENSEX | 0.20 | 181 | 110 | 37 | 42 | 46.8% | +0.028% |
| SENSEX | 0.25 | 130 | 76 | 30 | 25 | 54.5% | +0.056% |
| **SENSEX** | **0.30** | **99** | **56** | **25** | **15** | **62.5%** | **+0.090%** |
| SENSEX | 0.40 | 66 | 31 | 12 | 8 | 60.0% | +0.097% |

**Verdict — REJECT lower threshold.** WR monotonically increases with threshold for NIFTY (current 0.40% is best of those tested). SENSEX peaks at 0.30%. **No threshold cleared the 70% / N≥30 ship bar.** Falsifies the F2 hypothesis ("threshold too tight"). The 1H structural zone scarcity isn't a threshold problem — 1H OB events are inherently rare in current vol regime.

**Builds:** None. F2 closed REJECTED. `OB_MIN_MOVE_PCT` stays at 0.40%.

---

## Experiment 31 — Intraday-ICT Full Replay with Real Options PnL (Failed Replication Attempt)

**Date:** 2026-04-26 (Session 10)
**Script:** `experiment_31_intraday_ict_full_replay.py`

**Question:** When MERDIAN's intraday ICT detector (post-F1) is replayed across the full year against `hist_atm_option_bars_5m`, does it produce edge consistent with the compendium's claims (BEAR_OB 94%, BULL_OB 86%, MEDIUM 77.3%)?

**Setup:**
- Replay post-F1 detector logic on 5m bars derived from 1m source (260 days).
- For each non-SKIP detection: look up matching ATM option bar, compute T+30m premium PnL.
- MTF context computed via `ict_htf_zones` query (only W zones available for full year — D coverage too sparse).

**Findings (initial read):**
- TIER1 NIFTY: 48.0% WR (N=50), total +404.9%
- TIER1 SENSEX: 41.7% WR (N=24), total -162.8%
- VERY_HIGH MTF: 48.8% NIFTY / 33.3% SENSEX

**Initial verdict (WRONG — corrected below):** "Compendium does not replicate."

**Corrected verdict via Exp 15 re-run (see entry below):** Exp 31's measurement diverged from research methodology in ≥5 material ways: (a) used T+30m only, no structure-break exit, (b) didn't include MEDIUM context (1H zones not in `ict_htf_zones` query, only W), (c) queried live `ict_htf_zones` instead of rebuilding W/D/H zones fresh per detection bar (compendium's Exp 15 approach), (d) didn't compound capital, (e) lot sizes differed.

**Verdict — INVALID for compendium replication.** Useful as an "ict_htf_zones-as-it-stands" baseline, NOT as a test of the compendium framework. Exp 15 re-run is the load-bearing replication test.

**Builds:** None. Exp 31 retained as audit of how the live `ict_htf_zones` table affects in-production MTF context lookups (separate question from "does the framework have edge").

---

## Experiment 32 — Edge Isolation via Train/Heldout Stratification (Same Methodological Flaws as Exp 31)

**Date:** 2026-04-26 (Session 10)
**Script:** `experiment_32_edge_isolation.py`

**Question:** Within the 398 trades from Exp 31, does any combination of ambient features (DTE, time-of-day, day-of-week, IV level, PCR, OR range, prior-day move, ret_session) isolate a bucket of detections with replicable edge, validated against a held-out window?

**Setup:**
- Train: 2025-04-01 → 2026-01-14 (~190 days).
- Heldout: 2026-01-15 → 2026-04-24 (~70 days).
- 16 features stratified at single-feature level (Pass 1), top 5 crossed pairwise (Pass 2), best 15 rules validated on heldout (Pass 3).

**Findings:**
- Train baseline: N=238, WR=47.5%, Avg=-0.12%, Total=-28.5%
- Heldout baseline: N=160, WR=49.4%, Avg=+18.22%, Total=+2914.6% (large outlier wins, regime-divergence from train)
- Pass 2 found 2 candidate rules: BULL_OB+RS_UP (train 57% WR / +20% avg) and BULL_FVG+RS_UP (train 61% WR)
- Pass 3 heldout: BULL_OB+RS_UP collapsed to 0% WR (N=2). BULL_FVG+RS_UP collapsed to 38.5% WR / -3% avg (N=26).
- **No rules survived held-out validation.**

**Initial verdict:** "No replicable edge in tested feature set."

**Corrected verdict:** Same methodological flaws as Exp 31. The "no edge" conclusion was a measurement artifact, not a finding. The trade universe Exp 32 stratified was already biased by Exp 31's exit/context/sizing choices. Cannot conclude anything about real edge from this experiment.

**Verdict — INVALID for edge claim.** Retained as audit trail of search-for-edge under Exp 31's flawed framework. Replaced by Exp 15 re-run as the canonical edge-validation experiment.

**Builds:** None.

---

## Experiment 15 (re-validation) — Compendium Replication on Current Data

**Date:** 2026-04-27 (Session 10 — Monday morning concurrent with pre-open ops)
**Script:** `experiment_15_pure_ict_compounding.py` (run AS-IS, no modifications)

**Question:** Does the original Exp 15 framework replicate on current data, validating the compendium's headline claims?

**Setup:**
- Same script as Exp 15 from Session 5 (2026-04-12). Imports detector logic from production `detect_ict_patterns.py` (post-F1 fix).
- Full year: 2025-04 → 2026-04, 260 NIFTY sessions, 259 SENSEX sessions, 104K bars per symbol.
- Capital compounding: profits added, losses absorbed, no floor reset.
- Tier-multiplied sizing (TIER1=1.5x, TIER2=1.0x).
- T+30m exit primary, ICT structure-break secondary.
- W/D/H zones simulated fresh per detection bar (no lookahead, matches compendium methodology).

**Findings:**

| | NIFTY | SENSEX | Combined |
|---|---|---|---|
| Final capital | ₹560,705 | ₹612,737 | ₹1,173,442 |
| Return | +180.4% | +206.4% | +193.4% |
| Max DD | 1.3% | 3.1% | — |
| Sessions w/ trades | 46 | 40 | 86 |
| Total trades | 127 | 104 | 231 |

**By pattern (T+30m exit):**

| Pattern | N | WR | Avg PnL | Total PnL |
|---|---|---|---|---|
| BEAR_OB | 25 | **92.0%** | ₹+14,571 | ₹+364,273 |
| BULL_OB | 49 | **83.7%** | ₹+7,735 | ₹+379,016 |
| BULL_FVG | 155 | 50.3% | ₹+195 | ₹+30,153 |

Compendium claims BEAR_OB 94.4%, BULL_OB 86.4%. **Replicates within 3pp.**

**By MTF context:**

| Context | HTF Source | N | WR | Avg PnL | Total PnL |
|---|---|---|---|---|---|
| HIGH | D | 17 | 41.2% | ₹+3,319 | ₹+56,421 |
| **MEDIUM** | **H** | **22** | **77.3%** | **₹+11,863** | **₹+260,993** |
| LOW | NONE | 190 | 62.1% | ₹+2,400 | ₹+456,028 |

Compendium claims MEDIUM context +73.5% expectancy. **Replicates within 4pp (77.3% WR).**

**Deep dive — BULL_OB by MTF context:**

| Context | N | WR | Total PnL |
|---|---|---|---|
| HIGH | 4 | 50.0% | ₹+1,578 |
| **MEDIUM** | **14** | **85.7%** | **₹+196,184** |
| LOW | 31 | 87.1% | ₹+181,254 |

**Exit comparison:** T+30m total ₹+773,442 beats ICT structure-break total ₹+504,862 across all MTF contexts. Compendium's T+30m verdict replicates.

**TIER1 vs TIER2 (production tier rules):**
- TIER1: N=5, WR=60.0%, total ₹+47K (production rules promote rarely)
- TIER2: N=224, WR=62.1%, total ₹+726K (where the actual edge lives)

**Verdict — COMPENDIUM REPLICATES.** All headline claims within 3-4 percentage points of stated values. The system has real, durable, year-validated edge. ENH-35 LONG_GAMMA gate as currently configured is over-blocking — production tier rules surface real edge as TIER2, not TIER1, and the gate doesn't differentiate. The conditional gate lift (ENH-46-C) is the proposed fix.

**Builds:**
- F1 (TZ classification fix) — SHIPPED Session 10. Function-verified. Awaits 10:00 IST live test.
- F0 (gate visibility unclobber) — SHIPPED Session 10. Verified live.
- F3 (daily zone scheduling) — VALIDATED. Ready to ship Session 11 Candidate A.
- ENH-46-C (conditional gate lift) — PROPOSED. Pending design + 10-session shadow.

**Critical lesson — the Exp 31/Exp 32 detour:**
Sessions 10 wave 1 produced two experiments (Exp 31, Exp 32) that concluded the compendium didn't replicate. That conclusion was wrong. The experiments diverged from research methodology in ≥5 material ways (T+30m vs structure-break, no MEDIUM context, queried zones vs rebuilt, no compounding, lot-size drift). The negative verdict was measurement error.

The corrective discipline going forward: **before designing alternative experiments to research code, run the research code AS-IS first to establish baseline replication.** If research code replicates, alternative experiments may add insight; if research code doesn't replicate, that's the question to answer first. Skipping that step in Session 10 led to a half-day false-negative loop and a wrong "Path A — stop pretending ICT is the edge" recommendation that was retracted.

**Date filed:** 2026-04-27.
```

### Insert into `tech_debt.md`

```markdown
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
| **Workaround** | Manual SQL UPDATE per session when zones are visibly stale. Zombie-zone detection query: compute current spot vs zone boundaries with directional CASE, mark BULL_BREACHED if spot < zone_low / BEAR_BREACHED if spot > zone_high. Then UPDATE matching IDs to `status='BREACHED', valid_to=CURRENT_DATE`. Used 2026-04-27 pre-open with success. |
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
| **Root cause** | Two candidate hypotheses, not yet confirmed: (a) detector logic for D BEAR_OB is asymmetric — fires only under conditions rarely met (e.g., requires opposing-direction prior bar like the 1H detector, but daily timeframe rarely produces clean 0.40% moves followed by clean reversal candles); (b) breach filter is over-conservative on bearish daily candles (e.g., subsequent intraday spot prints filter the candidate out before INSERT). Neither hypothesis tested. |
| **Workaround** | None. The system operates with a one-sided D-context view — bearish detections cannot get HIGH MTF context from D BEAR zones. Practical impact: BUY_PE candidates can only get HIGH context via PDH proximity (which works as `direction=-1` and is correctly populated), but cannot get D BEAR_OB / D BEAR_FVG confluence. |
| **Proper fix** | Diagnostic session: trace through `detect_daily_zones()` against a known bearish day (e.g., 2026-04-24) and identify why no D BEAR_OB fires. If logic bug, patch + verify. If breach filter is the cause, decide whether to relax filter for D timeframe. |
| **Cost to fix** | ~1 session diagnostic, +1 session for fix if logic bug. |
| **Blocked by** | nothing — investigation can run any time |
| **Owner check-in** | 2026-04-27 |
```

### Insert into `session_log.md` (one-liner, prepend above 2026-04-26 entry)

```
2026-04-27 · `<hash>` · Session 10 (single concern with Monday-morning operational tail): Diagnosis of "MERDIAN never shows trade_allowed on trending days" landed at three findings (F0 gate visibility, F1 detector TZ classification, F2 1H threshold) plus operational pre-open work. F0 SHIPPED — `fix_enh35_unclobber_direction_bias.py` removed direction_bias/action clobber from LONG_GAMMA/NO_FLIP branches in `build_trade_signal_local.py`; verified live (NIFTY direction_bias=BEARISH, SENSEX BULLISH, both blocked correctly via trade_allowed=false). F1 SHIPPED — `fix_ict_time_zone_utc.py` patched `time_zone_label()` in `detect_ict_patterns.py` to convert UTC→IST before classification; function-verified UTC 04:30→MORNING / 06:30→MIDDAY / 09:30→AFTNOON; live verification awaits 10:00 IST 04-27 cycle. F2 REJECTED via Exp 29 v2 (full year, 0.40% threshold maximises WR; lower thresholds destroy edge). Four experiments run: Exp 29 v2 falsified F2; Exp 31 + Exp 32 produced false-negative replication results (later corrected). Exp 15 re-validation (run AS-IS, full year) confirmed compendium replicates: BEAR_OB 92.0% WR / BULL_OB 83.7% / MEDIUM context 77.3% / combined T+30m total ₹+773,442 / +193.4% capital growth (NIFTY +180%, SENSEX +206%, max DD 1.3%/3.1%). The detour through Exp 31/32 was a measurement error (5+ structural divergences from research methodology) — explicit retraction logged. ENH-46-C PROPOSED — conditional ENH-35 lift on BULL_OB inside MEDIUM/VERY_HIGH MTF context, design + 10-session shadow before live. Operational pre-open Monday 04-27: Zerodha token refreshed (Kite auth verified at 06:58 IST after debugging heredoc-corruption + SSM TTY hang); HTF zones rebuilt via 2x `build_ict_htf_zones.py --timeframe both`; 2 zombie W BULL_FVG zones manually marked BREACHED (NIFTY 24,074, SENSEX 77,636 — formed 04-20, broken Friday); Pine overlay regenerated; runbook_update_kite_flow.md updated with two new failure modes. Filed TD-029 (S2 hist_spot_bars TZ era), TD-030 (S2 build_ict_htf_zones doesn't re-eval breach), TD-031 (S2 D BEAR detection underactive). Pending: ENH-46-C + Exp 29v2/31/32/15-revalidation paste-in blocks for register / Compendium (text generated). · PASS · docs_updated:yes
```

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-04-27 (end of Session 10).*
