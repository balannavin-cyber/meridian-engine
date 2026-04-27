# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-04-26 → 2026-04-27 (Session 10 — single-concern with Monday-morning operational tail and post-market research extension) |
| **Concern** | Diagnose why MERDIAN never shows `trade_allowed=true` on trending days. Originally framed as "is the gate broken?" — landed at "the system has edge but visibility, classification, and gate-conditionality all needed work, and the dashboard layer has its own untrustworthiness." |
| **Type** | Diagnostic + multiple patches shipped + four experiments in main session + one new full experiment (Exp 33) in post-market extension + live verification of F0/F1/ENH-46-A + dashboard reliability investigation. Single-session-rule override logged twice (Monday-morning Kite tail; post-market research extension). |
| **Outcome** | DONE — F0 (gate visibility unclobber) SHIPPED + verified live (4 cycles confirmed BEARISH on LONG_GAMMA). F1 (TZ classification fix) SHIPPED + verified live across two of five buckets (OPEN at 09:21/09:28 IST, MORNING at 10:16 IST). F2 (1H threshold tuning) REJECTED via Exp 29 v2. Compendium replication validated via full Exp 15 re-run (NIFTY +180.4%, SENSEX +206.4%, T+30m total ₹+773K). ENH-46-A daemon caught real contract violation 10:25 IST and alerted via Telegram (first-day production value). Pine HTF zones overlay regenerated post-discovery that earlier version had only 5 of 18 active zones. Three live-observed bug discoveries: dashboard renders trade-direction inconsistent with DB ground truth (TD-032); `wcb_regime` field NULL but dashboard shows BULLISH (TD-035); `confidence_score` flat-lined for 90+ minutes (TD-036). Experiment 33 designed, debugged through 5 iterations, and run to completion: inside-bar-before-expiry breakout/breakdown thesis tested, supported (93% break rate, 71% next-day continuation), N=14 across NIFTY+SENSEX weekly+monthly buckets. Six new TDs filed (TD-032 through TD-037). Two new ENH proposed (ENH-46-D Pine live JSON feed, ENH-47 Inside-bar-before-expiry next-week ATM trade structure). |
| **Git start → end** | `4675745` → `15720d6` (Session 10 main commit batch). Extension work post-15720d6: Exp 33 scripts + this CURRENT update + TD/ENH/Compendium updates pending commit. |
| **Local + AWS hash match** | Local + origin + AWS all confirmed at `15720d6` after Session 10 main commits. Extension work brings local ahead until next commit + push + AWS pull cycle. |
| **Files changed (code, main session)** | `build_trade_signal_local.py` (F0 — direction_bias unclobber on LONG_GAMMA / NO_FLIP branches; backup `.pre_enh35_unclobber.bak`); `detect_ict_patterns.py` (F1 — `time_zone_label` UTC→IST conversion; backup `.pre_tz_fix.bak`). |
| **Files added (extension)** | `experiment_33_inside_bar_before_expiry.py`, `experiment_33_analyse.py`, `experiment_33_analyse_stage2.py`, `experiment_33_candidates.csv`, `experiment_33_controls_A_expiry_no_inside.csv`, `experiment_33_controls_B_inside_no_expiry.csv`, `experiment_33_analysis.csv`, `experiment_33_stage2.csv`. |
| **Files modified (docs, this update)** | `tech_debt.md` (+TD-032, TD-033, TD-034, TD-035, TD-036, TD-037 → 626 lines becomes 776 lines), `CURRENT.md` (this rewrite), `session_log.md` (Session 10 entry extended with extension), `merdian_reference.json` (Exp 33 scripts + dashboard discovery in change_log + new file inventory entries), `MERDIAN_Experiment_Compendium_v1.md` (+Experiment 33 entry, prepended above Exp 15 re-validation), `MERDIAN_Enhancement_Register.md` (ENH-46-C updated with TD-032 dependency block; +ENH-46-D, +ENH-47 appended). |
| **Tables changed** | `signal_snapshots` — multiple cycles produced during 09:30-15:30 IST trading day, all `trade_allowed=false` correctly per ENH-35 gate. `ict_zones` — 6 BULL_FVG detections produced (4 OPEN-window 09:21/09:28/09:44/09:46 + 2 MORNING-window 10:16, all marked BROKEN as price moved). `ict_htf_zones` — 18 active rows per symbol confirmed (was previously thought to be 4-10 due to bad SQL filter). `script_execution_log` — capture_spot_1m.py 10:25 IST cycle wrote `contract_met=false` (single blip, 10:24 and 10:26 normal). |
| **Cron / Tasks added** | None. F3 (cron `build_ict_htf_zones.py` daily 08:45 IST + ENH-72 wrapper) PROPOSED, deferred to Session 11 per Exp 15 validation. |
| **`docs_updated`** | YES — all six canonical files updated as full overwrites in this extension closeout. |

### What Session 10 did, in 18 bullets

**Diagnostic — three findings on the original "no trade_allowed" question:**

- **Finding 1 (F1) — ICT detector TZ misclassification.** `time_zone_label()` in `detect_ict_patterns.py` compared UTC bar_ts.time() to IST clock-time constants (09:15-15:30). Result: every detection got `time_zone='OTHER'` because UTC clock-time falls outside the IST window. TIER1 promotion (which requires MORNING/AFTNOON) was structurally unreachable. Patched: convert UTC→IST before extracting clock time. Verified live across two buckets (OPEN, MORNING) on 04-27 trading day.

- **Finding 2 (F0) — ENH-35 gate clobber regression.** LONG_GAMMA and NO_FLIP branches in `build_trade_signal_local.py` (commits `7c346fb` + `c310e52`, 2026-04-11) overwrote `direction_bias` to NEUTRAL and `action` to DO_NOTHING — not just `trade_allowed=false`. Operator never saw what the system thought. 9+ trading days of laundered signals. Patched: removed the clobber, gate still blocks via `trade_allowed=false` only. Verified live: NIFTY produced direction_bias=BEARISH consistently throughout 04-27 morning, SENSEX BEARISH on most cycles, both correctly blocked.

- **Finding 3 — visibility laundering** = sub-finding of F2. Same code path. Closed by F0 patch.

**Experiments — five total, with one major retraction:**

- **Exp 29 v1** — 1H OB threshold sweep on `hist_spot_bars_5m` (~13 days). Underpowered. Falsified F2 hypothesis ("threshold too tight"). 0.40% best of those tested.
- **Exp 29 v2** — full year via `hist_spot_bars_1m` (260 days, 215K rows, TZ-aware per TD-029). Confirmed F2 REJECTED.
- **Exp 31** — intraday-ICT full replay with real options PnL. **INVALID for compendium replication** — 5+ structural divergences from research methodology.
- **Exp 32** — edge isolation via train/heldout split. Same flaws as Exp 31. **INVALID.**
- **Exp 15 re-run (THE LOAD-BEARING ONE)** — ran `experiment_15_pure_ict_compounding.py` AS-IS. Result: **₹400K → ₹1.17M (+193.4%) over the year. NIFTY 92% WR on BEAR_OB, 84% on BULL_OB, 77.3% on MEDIUM context. Compendium replicates within 3pp of stated values.**
- **Exp 33 (extension) — inside-bar before expiry breakout thesis.** N=14 across NIFTY+SENSEX weekly+monthly. 93% break rate, 71% next-day continuation, 93% mid-of-range close on expiry day. Pin thesis rejected. Breakout thesis supported. ENH-47 proposed (next-week ATM long-options trade structure).

**Operational (Monday morning 06:30-07:35 IST pre-open):**

- **Zerodha token verified** at 06:58 IST after debugging heredoc-corruption + SSM TTY hang. `check_kite_auth.py` persisted to AWS.
- **HTF zones rebuilt** at 07:16 IST and 07:30 IST. Two zombie BULL_FVG zones manually marked BREACHED.
- **Pine overlay updated** with current zones — but discovered at 08:55 IST it was incomplete (5 of 18 zones rendered). Regenerated with all 18 zones per symbol.
- **Runbook updated** — `runbook_update_kite_flow.md` Session 10 addition: heredoc-corruption + SSM TTY hang failure modes.

**Live operational findings (post-market-open 04-27):**

- **F0 verified live.** Multiple cycles 09:30 onwards showed `direction_bias='BEARISH', action='BUY_PE', gamma_regime='LONG_GAMMA', trade_allowed=false`. Pre-F0 these would have shown `direction_bias='NEUTRAL'`. F0 is working in production.
- **F1 verified live across two of five buckets.** Detections at 09:21 and 09:28 IST classified `time_zone='OPEN'` (correct: 09:15 ≤ t < 10:00). Detection at 10:16 IST classified `time_zone='MORNING'` (correct: 10:00 ≤ t < 11:30). Function-level verified UTC→IST conversion is working end-to-end live.
- **ENH-46-A daemon caught real contract violation.** 10:25:02 IST `capture_spot_1m.py` cycle had `actual_writes={market_spot_snapshots:2}` only (missing `hist_spot_bars_1m`). Telegram alert sent. 10:26 IST cycle recovered. Single 1m-bar gap remains in historical record (recoverable from market_spot_snapshots if needed). First-day production value of ENH-46-A demonstrated.
- **System stably BEARISH for 50+ minutes.** Spot drifted 24,068 → 24,036 (-32 pts) while system maintained BEARISH bias every cycle — gate working correctly on LONG_GAMMA, fading the bullish FVG setup into W PDH 24,054-24,094 overhead resistance.
- **Filed TD-029, TD-030, TD-031** in main session. Filed TD-032, TD-033, TD-034, TD-035, TD-036, TD-037 during extension.

**TDs filed today:**
- Main: TD-029 (S2 hist_spot_bars TZ era), TD-030 (S2 build_ict_htf_zones doesn't re-eval breach), TD-031 (S2 D BEAR detection underactive).
- Extension: TD-032 (S2 dashboard ↔ DB inconsistency, BLOCKER for ENH-46-C), TD-033 (S3 dashboard label conflation), TD-034 (S2 hist_atm_option_bars_5m undersampled on dte=0), TD-035 (S3 wcb_regime NULL routing), TD-036 (S3 confidence_score flat-line), TD-037 (S4 schema column-name inconsistency).

**ENH proposals filed:**
- Main: ENH-46-C (conditional gate lift on MEDIUM/VERY_HIGH MTF context).
- Extension: ENH-46-D (Pine HTF zones live JSON feed, eliminates manual regeneration), ENH-47 (Inside-bar-before-expiry next-week ATM trade structure, sourced from Exp 33).

**Critical lesson surfaced in extension:** The retraction of "Path A — stop pretending ICT is the edge" framing happened because Exp 31/32 were measurement errors. The corrective discipline is: **before designing alternative experiments to research code, run the research code AS-IS first to establish baseline replication.** Now codified in CLAUDE.md anti-patterns. The Session 10 extension also surfaced the SQL column-name iteration friction (TD-037) — Claude/AI sessions should always run `information_schema.columns` first when querying a new table.

---

## This session

> Session 11. Pick ONE primary path from below at session start.

### Candidate A (recommended) — Ship F3 (daily zone scheduling + ENH-72 wrapper)

| Field | Value |
|---|---|
| **Goal** | Schedule `build_ict_htf_zones.py --timeframe both` to run daily at 08:45 IST Mon-Fri via Task Scheduler. Add ENH-72 ExecutionLog wrapper to instrument the script. Both small. Validated by Exp 15 re-run: MEDIUM context (1H zones) shows 77.3% WR vs 62% LOW baseline. |
| **Type** | Code + scheduler + instrumentation. |
| **Success criterion** | Task Scheduler entry registered + smoke-tested. ENH-72 wrapper applied. `script_execution_log` shows SUCCESS row for 08:45 IST run on next trading day. |
| **Time budget** | ~15-25 exchanges. |

### Candidate B — Address TD-032 (Dashboard ↔ DB inconsistency)

| Field | Value |
|---|---|
| **Goal** | Source-trace `merdian_signal_dashboard.py` rendering pipeline. Identify why dashboard renders trade direction inconsistent with `signal_snapshots` ground truth. Fix to ensure single-source-of-truth read. Add DB-vs-display consistency log line. |
| **Type** | Diagnostic + code patch. |
| **Success criterion** | Dashboard render demonstrably matches signal_snapshots row across 10+ test cycles spanning both BULLISH and BEARISH direction_bias. |
| **Why this matters** | TD-032 is BLOCKER for ENH-46-C ship. Without it fixed, conditional gate lift cannot promote any signal to live trade_allowed=true while operator-facing dashboard can show wrong instrument. |
| **Time budget** | ~20-30 exchanges. |

### Candidate C — Design ENH-46-C spec (no code) — DEFERRED until TD-032 closes

| Field | Value |
|---|---|
| **Goal** | Spec the conditional LONG_GAMMA gate lift design. Exp 15 evidence: BULL_OB MEDIUM = 85.7% WR, BEAR_OB MEDIUM = 75% WR vs gate's 47.7% population baseline. |
| **Type** | Design only — produce ENH-46-C document with shadow-test plan. No code. |
| **Success criterion** | One-page spec committed. Shadow-test plan defined. |
| **Status** | **Deferred until TD-032 closes** (per BLOCKER FOR relationship in tech_debt.md). |

### Candidate D — TD-030 + TD-031 fix (build_ict_htf_zones.py improvements)

| Field | Value |
|---|---|
| **Goal** | TD-030: teach `build_ict_htf_zones.py` to re-evaluate breach on existing active zones. TD-031: investigate why D BEAR_OB / D BEAR_FVG detection is underactive (0 written since 04-11). |
| **Type** | Code investigation + patch. |
| **Time budget** | ~20-30 exchanges. |

### Candidate E — ENH-46-D design (Pine live JSON feed)

| Field | Value |
|---|---|
| **Goal** | First 10-min capability check: does Pine v6 support HTTP GET to JSON endpoints? If yes, design the generator + Pine consumer architecture. If no, design fallback (auto-regenerate Pine source from JSON template). |
| **Type** | Investigation + design. |
| **Time budget** | ~25-40 exchanges. |

### Candidate F — Extend Exp 33 (loose inside-bar definition + IV-conditional split)

| Field | Value |
|---|---|
| **Goal** | Re-run Exp 33 with loose inside-bar definition (today's range ≤ 60% of yesterday's, with overlap) to expand candidate pool from N=14 to ~30-40. Split test group by IV-at-D-1 (above/below median) — pin thesis may apply only in high-IV environments. |
| **Type** | Research extension. |
| **Time budget** | ~15-25 exchanges. |

### DO_NOT_REOPEN

- All items from Session 9's CURRENT.md DO_NOT_REOPEN list.
- **F2 (1H OB threshold tuning)** — REJECTED. Exp 29 v2 falsified.
- **"Compendium doesn't replicate"** — wrong framing. Exp 15 re-run confirms BEAR_OB ~92%, BULL_OB ~84%, MEDIUM ~77%.
- **Path A ("stop pretending ICT is the edge")** — wrong. Withdrawn 2026-04-27.
- **Exp 31 / Exp 32 negative result** — measurement error, not finding.
- **F1 patch correctness** — verified live across OPEN and MORNING buckets.
- **Inside-bar before expiry pin thesis** — REJECTED via Exp 33 (only 7% pin rate).
- **Dashboard renders direction off pattern_type** — wrong framing of TD-032. The dashboard does NOT hardcode direction off pattern. It is non-deterministic across cycles. TD-032 root cause is not "pattern hardcoding."

### Watch-outs

- ENH-46-C ship is gated on TD-032. Don't try to advance ENH-46-C to shadow-test until TD-032 has closed.
- ENH-47 (inside-bar-before-expiry trade) is N=14 evidence — discretionary use first, automation last.
- Project knowledge re-upload per Documentation Protocol v3 Rule 12 is required after Session 10 extension closes — same 8 files as before.
- Session 11 should NOT attempt ENH-46-C live promotion. Even with shadow data, TD-032 must close first.

---

## Live state snapshot (at Session 11 start)

**Environment:** Local Windows primary; AWS shadow runner present but down since 2026-04-13 (separate concern, pre-existing).

**Open critical items (C-N):** None new from Session 10.

**Active TDs (post-extension):**
- TD-029 (S2) — `hist_spot_bars_1m`/`5m` pre-04-07 TZ-stamping bug. Workaround documented.
- TD-030 (S2) — `build_ict_htf_zones.py` doesn't re-evaluate breach on existing zones.
- TD-031 (S2) — D BEAR_OB / D BEAR_FVG detection underactive.
- **TD-032 (S2) — Dashboard ↔ DB inconsistency. BLOCKER for ENH-46-C ship.**
- TD-033 (S3) — Dashboard "SELL / BUY PE" label conflation.
- TD-034 (S2) — `hist_atm_option_bars_5m` severely undersampled on dte=0 (~22-44% coverage).
- TD-035 (S3) — `signal_snapshots.wcb_regime` NULL but dashboard shows BULLISH.
- TD-036 (S3) — `confidence_score` flat-lined for 90+ minutes.
- TD-037 (S4) — Schema column-name inconsistency across timestamp-bearing tables.

**Active ENH (in flight):**
- **ENH-46-A** — Telegram alert daemon. SHIPPED Session 9, live-verified production value 2026-04-27 morning when it caught real contract violation.
- **ENH-46-C** — Conditional ENH-35 gate lift, BULL_OB MEDIUM/VERY_HIGH context. **BLOCKED on TD-032 fix.** Cannot ship until dashboard-DB consistency verified.
- **ENH-46-D** — Pine HTF zones live JSON feed. PROPOSED 2026-04-27. Pending Pine v6 HTTP capability check + design.
- **ENH-47** — Inside-bar-before-expiry next-week ATM trade structure. PROPOSED 2026-04-27 from Exp 33. Discretionary use first; automation requires larger sample.
- **ENH-72** — Instrumentation propagation. New candidate for `build_ict_htf_zones.py` (Session 11 Candidate A).
- **F3** — Daily zone scheduling. Validated by Exp 15. Ready to ship.

**Settled by Session 10 extension:**
- F0 (gate visibility unclobber): SHIPPED + verified live multi-cycle.
- F1 (TZ classification): SHIPPED + verified live across OPEN and MORNING buckets.
- F2 (1H threshold): REJECTED.
- F3 (daily zone scheduling): NOT SHIPPED, validated by Exp 15, queued for Session 11.
- Compendium replication: confirmed.
- Dashboard reliability: known broken on direction/strike/instrument-type rendering (TD-032).
- Inside-bar-before-expiry breakout thesis: SUPPORTED in N=14 sample, ENH-47 filed.
- ENH-46-A daemon: live production value demonstrated.

**End-of-day 04-27 state:**
- NIFTY closed somewhere in or near 24,012-24,098 range — needs query to confirm whether today is a strict inside bar vs Friday's 23,857-24,140. If yes, tomorrow is a NIFTY monthly expiry candidate matching ENH-47 conditions.
- SENSEX similar geometry.
- ENH-46-A daemon running on Local at PID 22812 (assuming continuous from morning verification).

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-04-27 (end of Session 10, post-market extension closeout).*
