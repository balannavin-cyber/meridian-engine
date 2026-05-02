# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-05-01 → 2026-05-02 (Friday evening into Saturday — Session 15, very long: pending experiments → multi-stage diagnostic chain → production code review → end-to-end production patch shipped). |
| **Concern** | "Run the four PROPOSED Session 14 EOD experiments (Exp 44 inverted hammer cascade + Exp 47 direction stability anchor + Exp 49 Apr-only Exp 15 replication + ADR-003 Phase 1 zone respect-rate) before they age out." Landed at: discovery and end-to-end fix of a 13-month-old production detector defect (BEAR_FVG missing from `hist_pattern_signals`). |
| **Type** | Multi-experiment session that pivoted to upstream production debugging. Single-concern rule honoured at the experiment-batch level; the BEAR_FVG investigation was a forced pivot when Exp 50 surfaced "0 BEAR_FVG signals over 13 months" — impossible per market structure, evidence the data path was broken. Five-step audit → six-bug code review → S1 patches shipped to two production scripts → 40,384-row historical zone backfill → live zone builder rewrite → signal table rebuild → end-to-end verification. |
| **Outcome** | DONE. **Headline: BEAR_FVG signal count 0 → 795 in `hist_pattern_signals`.** Two production scripts patched and renamed to canonical filenames; both `_PRE_S15.py` originals preserved. Eight TDs registered (1 CLOSED, 4 NEW OPEN, 1 RETRACTED, 2 EXPANDED, 1 carry-forward). Six experiments registered with verdicts. ADR-003 Phase 1 outcome flagged INVALID (TZ-handling methodology bug in script, not the system). Exp 50 / Exp 50b BULL-only data invalidated; carry-forward to Session 16 to re-run on now-symmetric data. |
| **Git start → end** | `8543e08` → `8543e08` (Session 15 commit batch: BEAR_FVG patches to live + historical builders, file renames, closeout doc updates). Operator commits at end of session per protocol. |
| **Local + AWS hash match** | Local advancing this session. AWS not touched (no live trading work — pure backfill + research session). AWS sync deferred. |
| **Files changed (code)** | `build_ict_htf_zones_historical.py` (PATCHED in place: S1.a W BEAR_FVG, S1.b D BULL_FVG + D BEAR_FVG; original preserved as `build_ict_htf_zones_historical_PRE_S15.py`). `build_ict_htf_zones.py` (PATCHED in place: S1.a W BEAR_FVG, S1.b D BULL_FVG + D BEAR_FVG, plus 1H BEAR_FVG mirror in `detect_1h_zones`; original preserved as `build_ict_htf_zones_PRE_S15.py`). `build_hist_pattern_signals_5m.py` NOT modified (verified direction-symmetric during code review — innocent of the bug). |
| **Files added (tracked)** | None this session — patches were full-file replacements of existing tracked code. |
| **Files added (untracked)** | Diagnostic scripts (~12) + experiment scripts (Exp 44, 47, 47b, 50, 50b) + verification script (`verify_d_ob_thresholds.py`) — all live in `C:\GammaEnginePython\` and are .gitignored under existing `experiment_*.py` / `diagnostic_*.py` patterns. |
| **Files modified (docs)** | `tech_debt.md` (8 entries — see "TDs filed Session 15" below). `MERDIAN_Enhancement_Register.md` (Exp 44/47/47b/50/50b registered with verdicts). `MERDIAN_Experiment_Compendium_v1.md` (entries for Exp 44, 47b, 50, 50b, ADR-003 Phase 1 outcome). `ADR-003-ict-zone-architecture-review.md` (Phase 1 results section added with INVALID verdict). `CURRENT.md` (this rewrite). `session_log.md` (Session 15 one-liner). `merdian_reference.json` (file inventory updated to reflect renames). `SESSION_15_DETECTOR_FIX.md` runbook (new — describes the BEAR_FVG fix sequence). |
| **Tables changed** | `hist_ict_htf_zones`: +40,384 rows from full backfill on patched historical builder (W BEAR_FVG = 1,384 rows, D BULL_FVG = 84, D BEAR_FVG = 79, plus refreshed BULL/BEAR_OB and PDH/PDL across 264 trading days × 2 symbols). `ict_htf_zones`: +85 rows from one live run of patched builder (10 ACTIVE per symbol post breach-recheck). `hist_pattern_signals`: full delete-and-rebuild via `build_hist_pattern_signals_5m.py` — 6,318 → 7,484 rows. **BEAR_FVG signals: 0 → 795** (the headline number). BULL_FVG: 1,261 → 1,490. BULL_OB: 2,345 → 2,411. BEAR_OB: 2,660 → 2,736. |
| **Cron / Tasks added** | None. Existing `MERDIAN_ICT_HTF_Zones` scheduled task (08:45 IST Mon-Fri) automatically picks up the patched builder tomorrow morning since the rename was in-place. |
| **`docs_updated`** | YES. All seven closeout files produced: `CURRENT.md` (this), `session_log.md`, `MERDIAN_Enhancement_Register.md`, `MERDIAN_Experiment_Compendium_v1.md`, `tech_debt.md`, `ADR-003-ict-zone-architecture-review.md`, `SESSION_15_DETECTOR_FIX.md` runbook. No paste-in blocks; full file replacements only. |

### What Session 15 did, in 14 bullets

**Phase 1 — Pending experiments run (initially):**

- **Exp 47 — DIRECTION STABILITY ANCHOR (INVALID).** Ran `experiment_47_direction_stability_anchors.py` testing whether ret_30m/60m/session as alternative anchors reduce same-session direction flips vs ENH-55 V4. Result: 99-100% per-pattern WR — tautological. Bug: Exp 47 used `ret_30m` (forward-looking outcome per Rule 14) as both POLICY and OUTCOME variable, predicting itself. Verdict INVALID. Filed Exp 47b.

- **Exp 44 — INVERTED HAMMER CASCADE (FAIL).** Ran `experiment_44_inverted_hammer_cascade.py` (NIFTY 09:30-10:00 IST V-recovery seed observation from Session 14 EOD). Tested across (symbol, cascade_pct ∈ {0.20-0.45}, lookback_bars ∈ {3-9}, side ∈ {bull/bear}, horizon ∈ {6,12,30 bars}). No (sym,cas,lb,side,horizon) cell hit WR≥70 + N≥30 ship bar. Verdict FAIL.

- **ADR-003 Phase 1 — ZONE RESPECT-RATE (INVALID).** Ran `adr003_phase1_zone_respect_rate_v2.py` (zone respect-rate over last 10 trading days, both symbols). Initial v1 raw result 0% respect across all timeframes triggered investigation. Discovered post-04-07 `hist_spot_bars_5m` apparent coverage 27.5% — script-side TZ-handling bug in CLAUDE.md Rule 16 application (Rule 16 valid pre-04-07 only; post-04-07 needs era-aware `astimezone(IST)`). Filed bug discovery; ADR-003 Phase 1 verdict INVALID pending Phase 1 v3 with era-aware TZ handling.

- **Exp 47b — BACKWARDS-LOOKING ANCHORS (HYPOTHESIS FALSIFIED).** Ran `experiment_47b_backwards_anchor.py` with proper backwards-looking anchors (ret_30m_back, ret_60m_back computed from `hist_spot_bars_5m`). Result: backwards anchors flip MORE than ret_session, not less. ret_30m_back: 213% MORE flips/session. ret_60m_back: 187% more. ENH-85 design space "use a slower anchor" empirically falsified. Remaining ENH-85 paths: hard PO3 lock OR persistence filter.

- **Exp 49 — APR 2026 OUT-OF-SAMPLE EXP 15 (DEFERRED).** `experiment_15_pure_ict_compounding.py` source has zero ISO date strings AND zero `datetime(Y,M,D)` constructors — dates computed dynamically. Auto-patch via regex impossible. Three v1/v2/v3 wrapper attempts. Deferred to Session 16 contingent on operator pasting source date computation lines.

**Phase 2 — Exp 50 surfaces the upstream bug:**

- **Exp 50 — FVG-ON-OB CLUSTER vs STANDALONE (FAIL with anomaly).** Per request to test ICT's PD Array Matrix hypothesis (FVG above BULL_OB = institutional sponsorship + structural foundation). Ran 3×3 (lookback × proximity) sweep. 1/9 cells PASS (only 120min/0.50% loose threshold). Headline: cluster-FVG WR 24% vs standalone 36.7% — INVERSION of ICT's prediction. **Discovered: hist_pattern_signals has 1,261 BULL_FVG and 0 BEAR_FVG signals over 13 months across both symbols.** Operator challenged this as impossible — sustained bear price periods clearly visible on weekly chart Apr 2024-2026.

- **Exp 50b — VELOCITY TEST ON THE INVERSION (MARGINAL).** Tested whether Exp 50's inversion is exhaustion-driven (tight clusters → fast pre-FVG velocity → over-extended FVG). 3/7 cells DECREASING WR with velocity. Headline cell PASS, sweep at 43% (below 60% bar). Verdict MARGINAL. Findings BULL-only — invalid until Exp 50 re-run on bear-side data.

**Phase 3 — Five-step BEAR_FVG audit:**

- **Five-step diagnostic chain** ran via `diagnostic_bear_fvg_audit.py`: (S1) distinct pattern_type values + counts, (S2) full schema + direction-column distribution, (S3) sibling table check, (S4) bear-day count last 30d (sanity), (S5) manual canonical 3-bar BEAR_FVG shape scan in `hist_spot_bars_5m`. **Results conclusive: 1,129 canonical BEAR-FVG 3-bar shapes exist in 5m bars over 60d, but 0 BEAR_FVG signals exist in `hist_pattern_signals` for the same window. NIFTY 13 bear-days / 28 sessions = 46.4% bear-share, SENSEX 50.0%. H1 (detector-side asymmetry) confirmed.** Subsequently traced: bug NOT in `build_hist_pattern_signals_5m.py` (verified direction-symmetric — would emit BEAR_FVG signals if BEAR_FVG zones existed in `hist_ict_htf_zones`). Bug is one layer upstream in the zone builder.

- **Six-bug code review of `build_ict_htf_zones_historical.py`:** S1.a W BEAR_FVG missing, S1.b D-FVG entirely missing (any direction), S2.a D-OB definition non-standard ICT (uses move bar itself, not opposing prior bar), S2.b D-zone validity exactly 1 day for non-FVG, S3.a PDH/PDL `+/-20` band hardcoded (3.2x narrower in % on SENSEX vs NIFTY), S3.b status workflow write-once-never-recompute. Decided to fix S1.a + S1.b only (low-risk, unblocks Exp 50/50b re-run). S2/S3 catalogued as new TDs, intentionally not touched in this patch.

**Phase 4 — Patch + backfill + verification:**

- **Historical builder patch shipped.** `build_ict_htf_zones_historical_PATCHED.py` produced with S1.a (8-line W BEAR_FVG block) + S1.b (~30-line D BULL/BEAR_FVG block, new constants `FVG_D_MIN_PCT=0.10%` and `D_FVG_VALID_DAYS=5`). Dry-run on 17-day slice 2026-04-01..2026-04-30 verified S1.a/S1.b firing. Full backfill ran 264 NIFTY + 263 SENSEX trading days = 40,384 rows written. Counts: W BEAR_FVG 1,384, W BULL_FVG 2,603 (ratio 0.53 — bull-trend regime), D BEAR_FVG 79, D BULL_FVG 84 (ratio 0.94 — symmetric).

- **Live builder patch shipped.** `build_ict_htf_zones_PATCHED.py` produced with same S1.a + S1.b plus 1H BEAR_FVG branch in `detect_1h_zones` (parallel bug). Dry-run + live run completed: 85 zones written to `ict_htf_zones`, 10 ACTIVE per symbol post breach-recheck. 1H detector verified would emit on hourly cycle (will run on next 1H boundary trigger via runner).

- **Signal rebuild on patched zones.** `build_hist_pattern_signals_5m.py` ran (no code change — direction-symmetric). Read `hist_ict_htf_zones` (now 40,384 rows including 1,384 W BEAR_FVG). `hist_pattern_signals` rebuilt from scratch via existing `delete-where-source='backfill'` logic. **Result: 6,318 → 7,484 rows. BEAR_FVG 0 → 795. BULL_FVG 1,261 → 1,490** (existing rows refreshed, plus new W BEAR_FVG / D-FVG zones generating signals). End-to-end pipeline now symmetric.

- **Final verification.** `diagnostic_bear_fvg_audit.py` re-run: BEAR_FVG count 795. NIFTY 60d: BULL_FVG 274 / BEAR_FVG 150. SENSEX 60d: BULL_FVG 263 / BEAR_FVG 208. Asymmetry 1.83x (NIFTY) / 1.26x (SENSEX) noted for Session 16 follow-up — canonical 5m shapes are ~symmetric so signal builder may have a residual bull-skew filter (likely zone-side proximity selecting BULL zones above-spot more often in uptrending market). Not blocking; flagged TD candidate.

**TDs filed today: TD-NEW × 4 (live builder bull-skew filter, ret_60m unpopulated, ret_eod missing, era-aware Rule 16 addendum needed). TD-EXPANDED × 2 (TD-031 D-detector now framed as criteria mismatch not just underactive, TD-046 false-alarm contracts — carried forward unchanged). TD-CLOSED × 1 (S1 BEAR_FVG defect — closed by this session's patches). TD-RETRACTED × 1 (initial "27.5% bar coverage" claim — was script-side TZ-bug, not pipeline failure).**

---

## This session

> Session 16. Pick ONE primary path from below at session start.

### Candidate A (recommended) — Re-run Exp 50 / Exp 50b on now-symmetric data

| Field | Value |
|---|---|
| **Goal** | Both experiments produced findings on BULL-only data. Exp 50 had 1/9 cells PASS with monotonic inversion of ICT's hypothesis. Exp 50b found exhaustion-theory MARGINAL (3/7 cells decreasing). Now `hist_pattern_signals` has 795 BEAR_FVG signals — re-running both experiments produces 18 cells (vs 9), proper bear-side velocity test, and either confirms the inversion is real (with bear-side replication) or shows it was a BULL-only artefact. Either result is publishable to the compendium. |
| **Type** | Re-run existing scripts. No code changes (Exp 50 / 50b are filter-on-pattern_type — the new BEAR_FVG rows automatically populate the BEAR side of the sweep). |
| **Success criterion** | Both experiments produce verdicts. Compendium entries closed. ENH candidate (if Exp 50b PASSes on full data) filed. |
| **Time budget** | ~10-15 exchanges. Scripts already exist; run is ~5 minutes each. |

### Candidate B — Investigate live `ict_htf_zones` bull-skew filter

| Field | Value |
|---|---|
| **Goal** | NIFTY 60d shows BULL_FVG 274 vs BEAR_FVG 150 (1.83x bull skew) in `hist_pattern_signals` despite canonical 5m bear-FVG shape count being roughly equal to bull-FVG (562 BEAR vs 587 BULL per Step 5 audit). Either: (a) signal builder's "in-zone or near-zone with proximity" filter favours BULL_FVG signals because BULL zones above-spot are more available in uptrending market, or (b) zone validity windows differ for BULL vs BEAR. Investigation. Filed as TD candidate this session. |
| **Type** | Investigation + possible patch to `build_hist_pattern_signals_5m.py`. |
| **Success criterion** | Either: ratio explained as market-regime artefact (no fix needed, document and close), OR concrete filter bug identified + fix proposed. |
| **Time budget** | ~10-20 exchanges. |

### Candidate C — ADR-003 Phase 1 v3 (era-aware TZ handling) + Exp 44 v2

| Field | Value |
|---|---|
| **Goal** | ADR-003 Phase 1 verdict was INVALID due to script-side TZ handling bug (Rule 16 applied verbatim to post-04-07 era data). v3 with era-aware TZ-handling re-runs respect-rate diagnostic. Same TZ bug affects Exp 44 — ~22 of 263 sessions (post-04-07) had 9-bar in-session windows instead of 76-bar windows, biasing the verdict. Exp 44 v2 with era-aware TZ. Both small. |
| **Type** | Two re-runs with TZ fix. Possibly an addendum to CLAUDE.md Rule 16 documenting era boundary. |
| **Success criterion** | ADR-003 Phase 1 reaches a clean verdict (PASS/FAIL/MARGINAL with evidence). Exp 44 verdict re-confirmed or revised. CLAUDE.md Rule 16 era-awareness clarified. |
| **Time budget** | ~15-20 exchanges. |

### Candidate D — Address S2/S3 zone-builder bugs catalogued this session

| Field | Value |
|---|---|
| **Goal** | TD-S2.a (D-OB definition non-standard ICT — uses move bar as OB instead of prior opposing bar; W-OB uses standard def, D-OB doesn't), TD-S2.b (D-zone non-FVG validity = 1 day; D zones effectively expire by next session, explaining ADR-003 Phase 1's "0 D zones in lookback" finding), TD-S3.a (PDH/PDL `+/-20pt` hardcoded, 3.2x narrower in % on SENSEX), TD-S3.b (zone status write-once-never-recompute, ADR-003 status filter was a no-op). |
| **Type** | Code review + targeted patches (any subset of the four). |
| **Success criterion** | Whichever TDs are tackled get patched + verified. The S2.a D-OB definition change is the highest-value: standard ICT definition would generate more D BEAR_OB candidates (per Session 15 manual replay). |
| **Time budget** | ~20-30 exchanges depending on scope. |

### Candidate E — Exp 49 (Apr-only Exp 15 replication) — IF source dates can be located

| Field | Value |
|---|---|
| **Goal** | Test whether Exp 15's edge claims hold on April 2026 out-of-sample (the month after the Session 10 re-validation window). `experiment_15_pure_ict_compounding.py` has no ISO date literals or `datetime(Y,M,D)` constructors — dates computed dynamically. Three regex-based wrapper attempts (v1, v2, v3) failed. Either operator pastes source lines computing the backtest date range (5-10 lines max), or skip permanently. |
| **Type** | Out-of-sample validation experiment. |
| **Success criterion** | Apr WR within 5pp of full-year baseline → PASS. >10pp drop → FAIL. Either is publishable. |
| **Time budget** | ~10 exchanges if source available; else 0. |

### DO_NOT_REOPEN

- All items from Sessions 9-14's CURRENT.md DO_NOT_REOPEN lists.
- **BEAR_FVG missing detector** — CLOSED Session 15. Patches shipped; backfill verified; signals 0→795. Do not re-investigate; re-running diagnostic still verifies fix held.
- **Exp 50 / 50b on BULL-only data** — INVALID DATA SOURCE. Verdicts of "FAIL with anomaly" and "MARGINAL" hold for the BULL side of the data they tested. Do not cite as evidence about FVG-on-OB hypothesis; re-run on symmetric data first.
- **Exp 47 v1 (forward-anchor as policy)** — INVALID by construction (used outcome as policy variable). Superseded by Exp 47b. Do not re-cite.
- **ADR-003 Phase 1 v1 / v2 verdicts** — INVALID due to TZ-handling bug. Do not cite "0% raw respect rate" as evidence about zone integrity; v3 needed.
- **"27.5% bar coverage in hist_spot_bars_5m post-04-07"** — RETRACTED. Was script-side TZ-handling bug applying CLAUDE.md Rule 16 (pre-04-07 convention) verbatim to post-04-07 era data. Real coverage is ~100% post-04-07 per `diagnostic_bar_coverage_audit_v3.py` using `trade_date` column. Do not re-investigate.
- **"FVG-on-OB cluster has higher probability than standalone FVG"** (ICT PD Array claim per Exp 50 question) — currently UNRESOLVED on bidirectional data. BULL-only data showed inversion. Do not act on the claim either direction until Session 16 re-run.

### Watch-outs for Candidate A (re-run Exp 50/50b)

- The headline cell for Exp 50 (60min lookback / 0.50% proximity) had N=75 cluster-FVGs on BULL side. Bear side likely produces 50-100 cluster-pairs in the same cell — borderline statistical power. The 18-cell sweep is the robustness check. Don't over-read any single cell.
- Exp 50 had a known issue with the EV-ratio criterion — when both standalone and cluster EVs are tiny negatives, the ratio is a meaningless multiple of two near-zeros. WR delta is the reliable signal. **Drop EV-ratio criterion when re-running**, keep WR-delta + N-floor only.
- Exp 50b's velocity-decreasing-WR test had 1 quartile of 19 cluster-pairs at the headline cell — quartiles will be more robust on the bigger N from bidirectional data.
- The BULL-side findings (1/9 cells PASS, monotonic inversion, exhaustion MARGINAL) **may or may not hold** on bear side. Truly symmetric markets would replicate; asymmetric regimes won't. This is the test.

### Watch-outs for Candidate B (bull-skew investigation)

- The signal builder's `APPROACH_PCT = 0.005` filter (close within 0.5% of zone) and the "in zone or near zone bear/bull side" logic creates an inherent asymmetry: a zone above current spot needs spot rising to approach, a zone below needs spot falling. In an uptrending market, more BULL zones get approached than BEAR zones get approached. This is likely the regime explanation, not a bug.
- Confirming this requires partitioning the 60d data by ret_session sign and recomputing the bull/bear ratio per regime. If the ratio inverts in down-regimes, the filter is regime-driven and correct. If the ratio stays bull-skewed in down-regimes, there's a real filter bug.
- **Do NOT add new filter logic** without an explicit Exp filed and shadow-tested.

### Watch-outs for Candidate D (S2/S3 zone-builder fixes)

- S2.a (D-OB definition change) is the highest-value but also highest-risk. Changing the OB definition retroactively invalidates every D BULL_OB and D BEAR_OB row in `hist_ict_htf_zones` (118 BULL + 135 BEAR rows from full backfill). Either: (a) re-run full backfill after fix, OR (b) ship for new detections only and document version boundary. Decide before patching.
- S2.b (D-zone validity 1 day for non-FVG) — the 1-day validity might be intentional (D zones are by nature short-lived). Don't fix without an explicit decision on whether they should persist multiple days. The decision affects how downstream `detect_ict_patterns_runner.py` queries them.
- S3.a (PDH/PDL `+/-20pt`) — symbol-asymmetry verified during code review (NIFTY ~0.08% / SENSEX ~0.025%). Fix would multiply SENSEX bands by ~3x. May affect existing TIER assignments and signal generation thresholds. Audit downstream consumers before patching.
- S3.b (zone status workflow) — `recheck_breached_zones` on the live builder DOES update status correctly (verified in code review). The historical builder writes status='ACTIVE' once and never touches it. This is by design (no-lookahead audit invariant). Don't conflate live and historical workflows.

---

## Live state snapshot (at Session 16 start)

**Environment:** Local Windows primary; AWS shadow runner present but not touched Session 15.

**Open critical items (C-N):** None new from Session 15. Sessions 9-14's open items unchanged.

**Active TDs (after Session 15):**
- **TD-029 (S2)** — `hist_spot_bars` pre-04-07 TZ-stamping bug. Workaround documented. RELATED but distinct from new TD-NEW-RULE16-ERA-AWARE (Rule 16 needs era-aware addendum to CLAUDE.md).
- **TD-030 (S2)** — `build_ict_htf_zones.py` re-evaluates breach via `recheck_breached_zones` for live; DOES NOT for historical. Historical = by design (no-lookahead). Live closed by 2026-04-29 fix.
- **TD-031 (S2 EXPANDED Session 15)** — D-OB definition mismatch confirmed via manual replay (6 expected vs 1-2 actual). Originally framed as "underactive"; Session 15 reframed as **non-standard ICT detector definition** (uses move bar K+1 as OB instead of opposing prior K). Decision needed.
- **TD-S2.a (S2 NEW Session 15)** — D-OB detector uses non-standard ICT definition. W-OB uses standard. Inconsistent. (Effectively same item as TD-031 expanded; consolidating into TD-031 in next register pass.)
- **TD-S2.b (S2 NEW Session 15)** — D-zone non-FVG validity = exactly 1 day. Same root pattern as previously-documented H-zone single-day validity bug (line 53 H zones, all single-day, all EXPIRED).
- **TD-S3.a (S3 NEW Session 15)** — PDH/PDL `+/-20` points hardcoded. Symbol-agnostic; 3.2x narrower in % terms on SENSEX vs NIFTY.
- **TD-S3.b (S3 NEW Session 15)** — Zone status workflow — write-once ACTIVE, never recomputed retrospectively (historical builder). ADR-003 Phase 1 status filter was a no-op.
- **TD-NEW-RULE16-ERA-AWARE (S3 NEW Session 15)** — CLAUDE.md Rule 16 needs era-aware addendum. Pre-04-07 → `replace(tzinfo=None)`. Post-04-07 → `astimezone(IST_TZ)`. Most repo scripts apply Rule 16 verbatim and have a latent bug on post-04-07 data. Affects ADR-003 Phase 1 verdict. Filed Session 15.
- **TD-NEW-RET60M (S3 NEW Session 15)** — `ret_60m` column in `hist_pattern_signals` is uniformly 0 across all rows. Pattern probably never populated. Affects any experiment that uses 60m forward returns as outcome.
- **TD-NEW-RETEOD (S3 NEW Session 15)** — `ret_eod` column entirely absent from `hist_pattern_signals`. EOD analysis impossible from this table alone.
- **TD-NEW-LIVE-BUILDER-BULL-SKEW (S3 NEW Session 15)** — NIFTY signals 60d: BULL_FVG 274 vs BEAR_FVG 150. SENSEX: 263 vs 208. 1.83x / 1.26x bull skew despite canonical shapes being ~symmetric. Possibly regime-driven (uptrending market means BULL zones more often above spot when approached); needs investigation. Candidate B above.
- **TD-046 (S2 carry-forward from S14, unchanged)** — false-alarm contract violations on idempotent `build_ict_htf_zones.py` reruns from REFRESH ZONES button. Operational, not blocking.

**Active ENH (in flight):**
- **ENH-46-A** — Telegram alert daemon for tradable signals. SHIPPED Session 9, live-verified 2026-04-26. Operator tail still untested on real SHORT_GAMMA window.
- **ENH-46-C** — Conditional ENH-35 gate lift. PROPOSED Session 10. Design unchanged; pending shadow-test plan execution.
- **ENH-78** — DTE<3 PDH sweep current-week PE rule. SHIPPED Session 14. Live verification on next qualifying signal.
- **ENH-84** — REFRESH ZONES dashboard button. SHIPPED + hotfixed Session 14.
- **ENH-85** — PO3 direction lock. **DESIGN SPACE REDUCED Session 15** via Exp 47b: "use a slower anchor" empirically falsified. Remaining paths: hard PO3 lock OR persistence filter. Needs revised spec.
- **ENH-86** — WIN RATE legend redesign. v1 SHIPPED Session 14. v2 BLOCKED/ALLOWED prominence redesign deferred.

**Settled by Session 15:**
- **BEAR_FVG defect**: CLOSED. Two production scripts patched. End-to-end pipeline symmetric. 795 BEAR_FVG signals now in `hist_pattern_signals` where 0 existed before.
- **ENH-85 "slower anchor" path**: REJECTED via Exp 47b. Backwards-looking anchors flip 187-213% MORE than ret_session.
- **Exp 44 inverted hammer**: FAIL (with TZ-bug caveat — re-run as Exp 44 v2 in Session 16 with era-aware Rule 16 if revisiting).
- **Bar coverage gap (initial 27.5% claim)**: RETRACTED. Was script-side TZ-handling bug, not pipeline failure.
- **D-detector criteria mismatch (TD-031)**: CONFIRMED via Session 15 manual replay. Reframing pending in next TD pass.

**Markets state (at end of Session 15, 2026-05-02 evening):**
- NIFTY 24,044 — D PDH 24,072-24,092 directly overhead (28 pts), D PDL 23,789-23,809 ~250 pts below. W PDL 23,847-23,887 between. W BULL_FVG 22,714-23,556 ~1,300 pts below.
- SENSEX 76,914 — D PDH 77,266-77,286 ~370 pts overhead, D PDL 76,256-76,276 ~660 pts below. W PDL clusters at 76,553 / 75,848. W BULL_FVG 73,164-75,868 ~1,000 pts below.
- After Session 15 patches: live `ict_htf_zones` has 10 ACTIVE zones per symbol. Most newly-detected W BEAR_FVG zones got marked BREACHED on first run because spot has already moved past them in the past year (by design — not a bug).
- Carry-forward to Session 16: re-run Exp 50 / 50b on now-symmetric data is the highest-priority work.

---

## Detail blocks for Session 15 work

The following are the full detail blocks for experiments and TDs registered this session. These are written in the same format as prior CURRENT.md detail blocks. They duplicate what is in `MERDIAN_Experiment_Compendium_v1.md` and `tech_debt.md` so this file stays self-contained.

### Experiment 44 — Inverted Hammer Cascade (FAIL)

**Date:** 2026-05-01 (Session 15)
**Script:** `experiment_44_inverted_hammer_cascade.py`

**Question:** From Session 14 EOD seed observation (NIFTY 09:30-10:00 IST V-recovery from -300pt opening cliff), is there a tradeable bearish-cascade-then-bullish-mirror pattern? Sweep cascade depth, lookback bars, side, and forward horizon.

**Setup:**
- Source: `hist_spot_bars_5m` Apr 2025 → Apr 2026, both symbols, in-session 09:15-15:30 IST per Rule 16 (note: pre-04-07 Rule 16 applied verbatim; post-04-07 era affected by TZ-handling bug, ~22 of 263 sessions impacted — see TD-NEW-RULE16-ERA-AWARE).
- Cascade definition: spot drops `cascade_pct` (sweep ∈ {0.20, 0.25, 0.30, 0.35, 0.40, 0.45}%) within `lookback_bars` (sweep ∈ {3, 5, 7, 9}) of session open.
- Side: bull (long after cascade) and bear (short after upward push from session open).
- Forward horizon: 6, 12, 30 bars (30m, 60m, ~2.5h).
- Win: forward return aligned with side at horizon.
- Decision: ship if (sym, cas, lb, side, horizon) cell hits WR≥70 AND N≥30.

**Findings:**
- Total cells tested: 6 cascades × 4 lookbacks × 2 sides × 3 horizons × 2 symbols = 288 cells.
- No cell met BOTH the 70% WR AND N≥30 thresholds simultaneously.
- Highest WR cells were N=4-12 (underpowered).
- Highest-N cells (>50) had WR in the 48-58% range.
- The seed pattern (NIFTY V-recovery) appears to be a single-instance memorable observation, not a generalisable rule.

**Verdict — FAIL.** No tradeable rule. Closed.

**Caveat:** ~22 sessions (post-04-07 era) were analysed with TZ-restricted in-session windows (~9 bars vs ~76 bars) due to the script applying Rule 16 verbatim. Re-run as Exp 44 v2 with era-aware TZ handling could revise the verdict. Filed as Session 16 Candidate C contingent.

**Builds:** None.

---

### Experiment 47 — Direction Stability Anchor (INVALID)

**Date:** 2026-05-01 (Session 15)
**Script:** `experiment_47_direction_stability_anchors.py`

**Question:** Does using `ret_30m`, `ret_60m`, or `ret_session` as a slower anchor instead of ENH-55 V4's current anchor reduce same-session direction flips? Hypothesis: a slower anchor stabilises bias and reduces flip-flop.

**Setup:**
- Pulled `hist_pattern_signals` rows.
- For each signal, computed direction-policy using each candidate anchor (sign of the metric).
- Counted same-session flips per anchor per symbol.
- Computed per-pattern WR using the anchor as the policy and `ret_30m` sign as the outcome.

**Findings:**
- Per-pattern WR: 99-100% across all anchors. Suspicious — no real-world classifier achieves this.
- Diagnosis: `ret_30m` was used as BOTH the policy (direction) and the outcome. The classifier was predicting the sign of `ret_30m` from the sign of `ret_30m`. Tautological.
- Per Rule 14: `ret_30m` in `hist_pattern_signals` is forward-looking T+30m return AFTER signal entry. Using it as a policy means using future data to decide direction.

**Verdict — INVALID.** Tautological. Superseded by Exp 47b which uses backwards-looking anchors.

**Builds:** None.

---

### Experiment 47b — Backwards-Looking Anchors (HYPOTHESIS FALSIFIED)

**Date:** 2026-05-01 (Session 15)
**Script:** `experiment_47b_backwards_anchor.py`

**Question:** Same as Exp 47 but with backwards-looking anchors only. Are `ret_30m_back` (close[now] - close[6 bars ago]) or `ret_60m_back` (close[now] - close[12 bars ago]) more stable than `ret_session` (the ENH-55 V4 anchor, also backwards-looking but anchored to session open with zero rolling)?

**Setup:**
- Pulled `hist_pattern_signals` rows + matching `hist_spot_bars_5m` for backwards lookups.
- For each signal at bar B: computed `ret_30m_back` = (close[B] - close[B-6]) / close[B-6], and `ret_60m_back` = (close[B] - close[B-12]) / close[B-12].
- Counted same-session direction flips per anchor.
- Computed per-pattern WR using each anchor as policy and `ret_30m` (forward) sign as outcome — Rule 14 compliant.

**Findings:**

| Policy | Same-session flips/session | Multiplier vs ret_session |
|---|---|---|
| ret_session (baseline) | 0.27 | 1.00x |
| ret_30m_back | 0.85 | **3.13x more flips** |
| ret_60m_back | 0.77 | **2.87x more flips** |

- ret_30m_back flips 213% MORE than ret_session.
- ret_60m_back flips 187% MORE than ret_session.
- Per-pattern WR using backwards anchors: 53-58% (within noise).

**Verdict — HYPOTHESIS FALSIFIED.** Backwards-looking rolling anchors flip MORE, not less. The ENH-85 design space "use a slower anchor" is closed. ret_session (anchored to session open, zero rolling) is structurally the slowest available anchor.

**Implication for ENH-85:** Remaining design paths are (a) hard PO3 lock (anchor flips disallowed regardless of underlying signal), (b) persistence filter (require N consecutive same-direction signals before flipping). Filed for Session 16+ design.

**Builds:** ENH-85 design space reduced.

---

### Experiment 50 — FVG-on-OB Cluster vs Standalone (FAIL with anomaly)

**Date:** 2026-05-01 (Session 15)
**Script:** `experiment_50_fvg_on_ob_cluster.py`

**Question:** Per ICT's PD Array Matrix theory: does an FVG forming after price leaves an OB (in the same direction) have higher WR than a standalone FVG? Theory: cluster = institutional sponsorship + structural foundation = higher probability.

**Setup:**
- Pulled BULL_FVG and BULL_OB signals from `hist_pattern_signals`. (Discovered: BEAR_FVG count = 0, BEAR_OB count = 2,660. Asymmetric. Investigation triggered — see TDs.)
- Cluster definition: BULL_FVG within `lookback_min` minutes after a BULL_OB, with FVG zone within `proximity_pct` of OB zone.
- Sweep: `lookback_min` ∈ {30, 60, 120}, `proximity_pct` ∈ {0.20, 0.50, 1.00}.
- Outcome: ret_30m sign.
- Decision: PASS = cluster WR ≥ standalone WR + 5pp AND cluster EV_30m ≥ standalone EV_30m × 1.3 AND cluster N ≥ 30.

**Findings (BULL-only, since no BEAR_FVG signals existed):**

| Lookback | Prox% | N_cluster | WR_cluster | WR_standalone | WR_delta | Verdict |
|---|---|---|---|---|---|---|
| 30 | 0.20 | 8 | 0.0% | 36.2% | -36.2pp | FAIL (N too low) |
| 30 | 0.50 | 47 | 21.3% | 36.5% | -15.2pp | FAIL |
| 30 | 1.00 | 63 | 30.2% | 36.2% | -6.1pp | FAIL |
| 60 | 0.20 | 13 | 15.4% | 36.1% | -20.8pp | FAIL |
| 60 | 0.50 | 75 | 24.0% | 36.7% | -12.7pp | FAIL |
| 60 | 1.00 | 110 | 37.3% | 35.8% | +1.5pp | FAIL |
| 120 | 0.20 | 36 | 36.1% | 35.9% | +0.2pp | FAIL |
| **120** | **0.50** | **187** | **41.2%** | **35.0%** | **+6.2pp** | **PASS (1/9 cells)** |
| 120 | 1.00 | 242 | 49.2% | 32.8% | +16.4pp | FAIL (EV-ratio mis-calibrated) |

- 1/9 cells PASS at the 120min/0.50% loose threshold only.
- Pattern shows monotonic INVERSION of ICT's prediction at tight thresholds: cluster WR is WORSE than standalone WR. Effect grows as thresholds tighten (smallest at 30min/0.20% = -36.2pp).
- The trend is monotonic and consistent across the sweep grid.

**Verdict — FAIL with anomaly.** Inversion plausibly explained by either (a) exhaustion (tight cluster = price moved fast = FVG forms over-extended, fails more), or (b) survivorship bias (cluster definition expands → standalone bucket loses higher-quality FVGs that had a "background" OB → standalone WR drops disproportionately, making cluster look better at loose thresholds). Tested via Exp 50b.

**CRITICAL UNRELATED FINDING — bug discovery:** During Exp 50 setup, discovered `hist_pattern_signals` contains 1,261 BULL_FVG and 0 BEAR_FVG signals over 13 months. Per market structure (sustained bear periods clearly visible on weekly chart), this is impossible. Triggered five-step BEAR_FVG audit and end-to-end production fix.

**Builds:** None directly from Exp 50. The bug discovery led to S1 production patches.

**Carry-forward:** Re-run on now-symmetric data in Session 16 (Candidate A). 18 cells (vs 9) with bear-side data added.

---

### Experiment 50b — Velocity Test on Cluster Inversion (MARGINAL)

**Date:** 2026-05-01 (Session 15)
**Script:** `experiment_50b_fvg_on_ob_velocity.py`

**Question:** Is Exp 50's cluster-FVG inversion driven by exhaustion? Hypothesis: tight clusters (small lookback + small proximity) imply fast pre-FVG velocity, which means price is over-extended at the FVG, and FVG fails more often. Test: partition cluster-FVGs by velocity quartile and check if WR drops as velocity rises.

**Setup:**
- Reused Exp 50 cluster definition.
- For each cluster pair (FVG, OB): velocity = abs(fvg_price - ob_price) / delta_min.
- Partitioned cluster pairs into velocity quartiles (Q1 lowest, Q4 highest).
- Measured WR per quartile per (lookback_min, proximity_pct) cell.
- Decision: PASS = headline cell shows DECREASING WR Q1→Q4 AND ≥60% of cells (N≥20) show same direction.

**Findings (BULL-only):**

| Lookback | Prox% | N_pairs | WR_Q1 | WR_Q4 | Direction |
|---|---|---|---|---|---|
| 30 | 0.50 | 47 | 28.6% | 16.7% | DECREASING |
| 30 | 1.00 | 63 | 31.3% | 25.0% | DECREASING |
| 60 | 0.50 | 75 | 36.8% | 13.3% | **DECREASING** (headline) |
| 60 | 1.00 | 110 | 39.3% | 35.7% | DECREASING (slight) |
| 120 | 0.50 | 187 | 51.1% | 38.3% | DECREASING |
| 120 | 1.00 | 242 | 55.7% | 47.5% | INCREASING (anomaly cell) |
| 30 | 0.20 / 60 | 0.20 / 120 | 0.20 | various | various | (cell-by-cell mixed) |

- Headline cell PASSes (DECREASING).
- 3 of 7 voting cells (N≥20) show DECREASING.
- Sweep PASS rate = 43% (below 60% bar).

**Verdict — MARGINAL.** Direction supports exhaustion hypothesis at the headline cell, but sweep robustness fails. Could be (a) real exhaustion, (b) survivorship in standalone bucket (Exp 50 alternative explanation), or (c) noise. **Cannot ship as a filter without bidirectional validation.**

**Builds:** None.

**Carry-forward:** Re-run on bidirectional data in Session 16 (Candidate A).

---

### ADR-003 Phase 1 — Zone Respect-Rate (INVALID — TZ-handling methodology bug)

**Date:** 2026-05-01 (Session 15, Phase 1 ran)
**Script:** `adr003_phase1_zone_respect_rate_v2.py`

**Question:** Per ADR-003 Session 14 EOD proposal: do `ict_htf_zones` and `hist_ict_htf_zones` zones reflect price-pivot behaviour? Compute respect-rate (% of zone touches where spot reverses within zone) over last 10 trading days for each timeframe.

**Setup (v2):**
- Pulled active zones from both tables for last 10 sessions.
- For each zone, found 5m bars where spot entered the zone (high ≥ zone_low AND low ≤ zone_high).
- For each entry, classified as RESPECTED (spot reversed within zone) or BROKEN (spot exited the other side).
- Computed respect-rate per (symbol, timeframe, pattern_type).

**Initial findings (v1, v2):**
- Raw respect-rate: 0% across all timeframes for both symbols.
- Apparent post-04-07 bar coverage in `hist_spot_bars_5m`: 27.5% (vs ~100% pre-04-07).
- D zone count in lookback: 0 (W zones found, but no D zones).

**Diagnosis (mid-investigation):**
- The 27.5% coverage was a script-side bug. CLAUDE.md Rule 16 (apply `replace(tzinfo=None)` to bar_ts then filter to in-session 09:15-15:30) is correct for pre-04-07 era only. Post-04-07 bars are stored as true UTC, not IST-as-UTC. So `replace(tzinfo=None)` produces a UTC clock-time, and filtering to 09:15-15:30 IST drops most of the day.
- Real coverage post-04-07 is ~100% per `diagnostic_bar_coverage_audit_v3.py` (which uses `trade_date` column instead of bar_ts time filter).
- The 0 D zones were a separate finding — the historical D-zone detector has 1-day validity windows for non-FVG zones (TD-S2.b), so D zones effectively expire by next session and don't appear in 10-day lookback queries.

**Verdict — INVALID.** Methodology compromised by script-side TZ-handling bug. Redo as Phase 1 v3 with era-aware TZ handling.

**Builds:** Found two TDs: TD-NEW-RULE16-ERA-AWARE (Rule 16 needs era-aware addendum) and reinforced TD-S2.b (D-zone single-day validity).

**Carry-forward:** Phase 1 v3 in Session 16 (Candidate C).

---

## Detail blocks for TDs filed Session 15

### TD-S1-BEAR-FVG-DETECTOR (CLOSED Session 15) — BEAR_FVG missing across detector pipeline

| | |
|---|---|
| **Severity** | S1 (production-affecting; 13-month silent bug) |
| **Discovered** | 2026-05-01 (Session 15, during Exp 50 setup; confirmed via 5-step audit `diagnostic_bear_fvg_audit.py`) |
| **Component** | `build_ict_htf_zones_historical.py` and `build_ict_htf_zones.py` (both zone builders) |
| **Symptom** | `hist_pattern_signals` contained 0 BEAR_FVG signals over 13 months across NIFTY + SENSEX, despite 1,129 canonical BEAR-FVG 3-bar shapes existing in `hist_spot_bars_5m` (60d) and 46-50% of recent sessions being bear days. `hist_ict_htf_zones` had 0 BEAR_FVG of 35,862 rows. |
| **Root cause** | Zone builders had no BEAR_FVG branch in `detect_weekly_zones()` (only BULL_FVG implemented). `detect_daily_zones()` had no FVG detection of either direction. `detect_1h_zones()` had only BULL_FVG. Three locations affected, two scripts. Signal builder `build_hist_pattern_signals_5m.py` was direction-symmetric and innocent (would have emitted BEAR_FVG if zones existed). |
| **Workaround** | n/a — direct fix shipped this session. |
| **Proper fix** | Three S1.a/S1.b/S15-1H patches applied to both zone builders, then full historical backfill (40,384 rows), then signal table rebuild via `build_hist_pattern_signals_5m.py`. Verified end-to-end: BEAR_FVG signal count 0 → 795. |
| **Cost to fix** | 1 session (this one). |
| **Status** | **CLOSED 2026-05-02.** Patches in production. |

### TD-S2.a — D-OB detector uses non-standard ICT definition

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-05-01 (Session 15, code review of `build_ict_htf_zones_historical.py`) |
| **Component** | `detect_daily_zones()` in both historical and live builders. |
| **Symptom** | D-OB detector marks the prior bar K+1 (the move bar itself) as the OB. Standard ICT defines an OB as the LAST opposing-color candle BEFORE the displacement (i.e. K, not K+1). W-OB uses standard ICT definition; D-OB does not. Inconsistent across timeframes within the same script. |
| **Root cause** | Detector logic in `detect_daily_zones()` checks `prior_move >= OB_MIN_MOVE_PCT` and writes the prior bar itself. Should check K-1 + K pair where K is the displacement bar and K-1 is opposing-color. Carried forward from initial implementation. |
| **Workaround** | None. The symptom is that D BEAR_OB candidates fire ~6 expected vs 1-2 actual per Session 15 manual replay — false negatives at the standard ICT definition, but the detector is by its current definition working. |
| **Proper fix** | Change D-OB detector to standard ICT definition. Decide retroactivity: re-run full backfill OR document version boundary. |
| **Cost to fix** | <1 session if retroactive backfill, 1 session if version-boundary documentation. |
| **Status** | OPEN. (Session 16 Candidate D.) |

### TD-S2.b — D-zone validity = 1 day for non-FVG zones

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-05-01 (Session 15, code review) |
| **Component** | `detect_daily_zones()` in both builders. |
| **Symptom** | D-zone non-FVG validity = exactly 1 day (`valid_from = valid_to = target_date`). D zones effectively expire by next session. ADR-003 Phase 1 v2 saw 0 D zones in 10-day lookback because each D zone's `valid_to < lookback_start_date`. |
| **Root cause** | Hardcoded `valid_to = target_date` in detector. Same root pattern as previously-documented H-zone single-day validity bug (53 H zones ever written, all single-day, all EXPIRED). |
| **Workaround** | None. May be intentional (D zones short-lived by design), but if intentional should be documented; if unintentional should be extended to N-day window. |
| **Proper fix** | Decide: extend D-zone validity to N days (e.g. 2-5 like the new D-FVG validity), OR document 1-day as intentional and adjust downstream consumers. |
| **Cost to fix** | <1 session. |
| **Status** | OPEN. (Session 16 Candidate D.) |

### TD-S3.a — PDH/PDL `+/-20` band hardcoded, symbol-agnostic

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15, code review) |
| **Component** | `detect_weekly_zones()` and `detect_daily_zones()` in both builders. |
| **Symptom** | PDH/PDL zones get `zone_high = level + 20`, `zone_low = level - 20` regardless of symbol. NIFTY at 24,000 → 20pt = ~0.083%. SENSEX at 80,000 → 20pt = ~0.025%. SENSEX PDH/PDL zones are 3.2x narrower in % terms. |
| **Root cause** | Hardcoded `+/- 20` constant. |
| **Workaround** | None. Live trading is asymmetric across symbols at this PDH/PDL level. |
| **Proper fix** | Replace with `+/- (level * BAND_PCT)` where BAND_PCT is a config constant (e.g. 0.05% to give NIFTY ~12pt, SENSEX ~40pt). Audit downstream consumers (TIER assignment, signal generation thresholds) before patching. |
| **Cost to fix** | <1 session for code; 1 session for downstream audit. |
| **Status** | OPEN. (Session 16 Candidate D.) |

### TD-S3.b — Zone status workflow: write-once-never-recompute (historical builder)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15, code review) |
| **Component** | `build_ict_htf_zones_historical.py`. (Live builder is correct: `recheck_breached_zones` updates status — verified in code review.) |
| **Symptom** | Historical builder writes `status='ACTIVE'` once per zone and never recomputes. ADR-003 Phase 1 v2 filtered on `status='ACTIVE'` and the filter was a no-op (every historical zone is ACTIVE because no recheck logic exists). |
| **Root cause** | By-design absence of recheck logic in historical builder (no-lookahead audit invariant: as-of-date snapshot must not be polluted by future price action). |
| **Workaround** | Don't filter on `status` in queries against `hist_ict_htf_zones`. Compute breach manually using `hist_spot_bars_5m` per query. |
| **Proper fix** | Either: (a) add a separate `historical_zone_status` view that joins zones with subsequent bars to derive status as-of any date — preserves no-lookahead invariant in source table, OR (b) document that `status` field on `hist_ict_htf_zones` is meaningless for historical queries. |
| **Cost to fix** | 1 session for view; <1 session for documentation-only. |
| **Status** | OPEN. (Session 16 Candidate D.) |

### TD-NEW-RULE16-ERA-AWARE — CLAUDE.md Rule 16 needs era-aware addendum

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15, ADR-003 Phase 1 + Exp 44 + Exp 50 + diagnostic_bar_coverage_audit) |
| **Component** | `CLAUDE.md` Rule 16 (TZ handling guidance for `bar_ts`). |
| **Symptom** | Rule 16 says: apply `replace(tzinfo=None)` to bar_ts and filter to in-session 09:15-15:30. This is correct for pre-04-07 era (bars stored as IST-labelled-as-UTC). Post-04-07 era stores bars as true UTC. Applying Rule 16 verbatim post-04-07 produces a UTC clock-time and filtering to 09:15-15:30 IST drops most of the day. Multiple Session 15 scripts (Exp 44 indirectly, ADR-003 Phase 1 directly, Exp 50 unaffected since it uses bar_ts only for ordering) hit this latent bug. |
| **Root cause** | Rule 16 was written when only the pre-04-07 era existed; post-04-07 era introduced 2026-04-07 was not retroactively documented in Rule 16. |
| **Workaround** | Era-aware: pre-04-07 use `replace(tzinfo=None)`; post-04-07 use `astimezone(IST_TZ)`. Verified in `diagnostic_bar_coverage_audit_v3.py` which avoids the issue entirely by using `trade_date` column. |
| **Proper fix** | Edit `CLAUDE.md` Rule 16 to add era boundary at 2026-04-07 with code snippet for both eras. Audit all repo scripts that apply Rule 16 verbatim and patch them. |
| **Cost to fix** | <1 session for CLAUDE.md edit; ~1 session for repo audit + patches. |
| **Status** | OPEN. |

### TD-NEW-RET60M — `ret_60m` column is uniformly 0 in `hist_pattern_signals`

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15, Exp 47 review when ret_60m showed 0.000% across all rows) |
| **Component** | `build_hist_pattern_signals_5m.py` and possibly upstream `hist_market_state` source. |
| **Symptom** | `ret_60m` column in `hist_pattern_signals` is 0.000% across every single row — verified in Exp 47b output and Exp 50 output. |
| **Root cause** | Most likely the column is never populated (default value persists). Could also be the source `hist_market_state.ret_60m` is itself 0 for all rows. Not yet diagnosed. |
| **Workaround** | None. Use `hist_spot_bars_5m` to compute 60m forward returns directly when needed (more expensive but correct). |
| **Proper fix** | Diagnose where `ret_60m` should come from. If `hist_market_state.ret_60m` is the source, fix that. If signal builder is supposed to compute it, add the computation. |
| **Cost to fix** | <1 session diagnostic, 1 session for fix + backfill. |
| **Status** | OPEN. |

### TD-NEW-RETEOD — `ret_eod` column entirely absent from `hist_pattern_signals`

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15, Exp 50 setup tried to compute EOD outcome) |
| **Component** | `build_hist_pattern_signals_5m.py` schema; `hist_pattern_signals` table. |
| **Symptom** | `ret_eod` column does not exist on `hist_pattern_signals`. EOD analysis on this table alone is impossible. |
| **Root cause** | Column was never added to schema. |
| **Workaround** | Compute EOD outcome from `hist_spot_bars_5m` directly. |
| **Proper fix** | Add `ret_eod` to `hist_pattern_signals` schema; patch `build_hist_pattern_signals_5m.py` to compute it from session-end bar; backfill via signal rebuild. |
| **Cost to fix** | 1 session. |
| **Status** | OPEN. |

### TD-NEW-LIVE-BUILDER-BULL-SKEW — Signal builder bull-skew vs canonical shape symmetry

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-02 (Session 15, post-rebuild verification) |
| **Component** | `build_hist_pattern_signals_5m.py` (zone-approach filter logic). |
| **Symptom** | NIFTY 60d signals: BULL_FVG 274 vs BEAR_FVG 150 (1.83x bull skew). SENSEX 60d: BULL_FVG 263 vs BEAR_FVG 208 (1.26x bull skew). Canonical 5m BEAR_FVG / BULL_FVG shapes in `hist_spot_bars_5m` are essentially symmetric (NIFTY 562 BEAR / 587 BULL; SENSEX 567 / 575). Asymmetry must come from the signal builder's filter logic. |
| **Root cause** | Suspected: signal builder applies `APPROACH_PCT = 0.005` filter (close within 0.5% of zone) and "in zone or near zone bear/bull side" logic. In an uptrending market, BULL zones are more often above-spot (and therefore approachable from below) than BEAR zones are below-spot (approachable from above). Likely a regime artefact, not a bug — but unverified. |
| **Workaround** | None. Live trading sees more BULL_FVG signals than BEAR_FVG signals as a result. May be acceptable (regime-driven) or may need filter rebalancing. |
| **Proper fix** | Investigate (Session 16 Candidate B): partition 60d data by regime (ret_session sign) and recompute bull/bear ratio per regime. If ratio inverts in down-regimes, filter is regime-driven and correct (close as documented). If ratio stays bull-skewed in down-regimes, filter has a real asymmetry bug. |
| **Cost to fix** | ~1 session investigation, +0-1 session for fix if needed. |
| **Status** | OPEN. (Session 16 Candidate B.) |

### TD-NEW-RETRACTED-BAR-COVERAGE — "27.5% bar coverage" claim retracted

| | |
|---|---|
| **Severity** | n/a (retracted — was script bug, not real issue) |
| **Discovered** | 2026-05-01 (Session 15, ADR-003 Phase 1 v2) |
| **Component** | n/a (initial claim was about `hist_spot_bars_5m`, but the apparent gap was a script-side filter bug, not a pipeline failure) |
| **Symptom (initial, wrong)** | "Post-04-07 `hist_spot_bars_5m` has only 27.5% of expected bars in-session." |
| **Root cause (correct)** | Script applied CLAUDE.md Rule 16 (`replace(tzinfo=None)` then filter to 09:15-15:30 IST) verbatim to post-04-07 era. Post-04-07 bars are stored as true UTC; the filter dropped to ~9 bars/day (the UTC 09:15-10:00 ≈ IST 14:45-15:30 overlap window). Real coverage is ~100% per `diagnostic_bar_coverage_audit_v3.py` which filters by `trade_date` column instead. |
| **Workaround / Resolution** | Use `trade_date` column for date filters, not bar_ts time filter. Or apply era-aware Rule 16 (see TD-NEW-RULE16-ERA-AWARE). |
| **Status** | RETRACTED. The pipeline is healthy. The Rule 16 era-awareness need is filed separately. |

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-05-02 (end of Session 15).*
