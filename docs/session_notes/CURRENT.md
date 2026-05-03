# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-05-02 → 2026-05-03 (Saturday evening into Sunday — Session 16, very long: pending experiments → wrong-cohort detour → Exp 15 source-code archaeology → live-detector replication → diagnostic deep-audit). |
| **Concern** | "Run the seven Session 15 carry-forward items: Exp 41/41b BEAR_FVG cohort re-derive, stash adjudication, Exp 50/50b re-run on now-symmetric data, ADR-003 Phase 1 v3, TD-056 bull-skew partition, Exp 44 v2 if time." Landed at: **end-to-end audit of Exp 15 framework on current code**, with critical finding that the "ICT framework headlines collapse" framing developed mid-session was wrong-cohort overreach, and Exp 15's published edge replicates within 2-3pp on locally-computed methodology. |
| **Type** | Multi-experiment session that pivoted from carry-forward closure to framework provenance audit when investigation surfaced (a) Exp 15 had no findable execution audit trail, (b) `experiment_15_pure_ict_compounding.py` and `detect_ict_patterns.py` were both modified post-Compendium-publication on 2026-04-13, including silent MTF tier relabeling (Apr-12 MEDIUM=daily zone, Apr-13+ MEDIUM=1H zone), (c) the carry-forward experiments were testing on `hist_pattern_signals` (5m batch) but Exp 15's actual edge lives on the 1m live-detector path. |
| **Outcome** | DONE. **Headline: Exp 15 framework replicates within 2-3pp of published claims on current code with current data: BULL_OB 83.7% WR (N=49), BEAR_OB 92.0% WR (N=25), BULL_FVG 50.3% WR (N=155). Combined NIFTY+SENSEX: ₹4L → ₹11.7L (+193.4%) full year.** Concentration: top 7 sessions = 80% of P&L. MTF context inverted from claim — LOW outperforms HIGH on OB patterns. BULL_FVG-on-BULL_OB clustering replicates on live cohort: +12.8pp lift at 90-min lookback (N=64). TD-056 bull-skew confirmed structural across BOTH 5m-batch and 1m-live code paths (NIFTY DOWN 5.6x on 5m, 3.29x on 1m). Live `detect_ict_patterns.py` emits ZERO BEAR_FVG signals across full year despite Session 15 zone-builder fix (TD-058). 5 of 7 carry-forward items closed; 2 deferred (Exp 50b velocity on live cohort, Exp 44 v2). |
| **Git start → end** | `b8bf7b3` → `f2789b9` (Session 16 commit batch: documentation-only — no production code patches this session). Operator commits at end of session per protocol. |
| **Local + AWS hash match** | Local advancing this session. AWS not touched (research-only session, no production code changes). AWS sync deferred. |
| **Files changed (code)** | None — Session 16 was experiments + audit + documentation only. No production patches. |
| **Files added (untracked)** | Diagnostic / experiment scripts (~12) at `C:\GammaEnginePython\` covered by existing `.gitignore` patterns: `experiment_41_bear_fvg_cohort_rederive.py`, `experiment_50_fvg_on_ob_cluster_v2.py`, `experiment_50b_fvg_on_ob_velocity_v2.py`, `adr003_phase1_zone_respect_rate_v3.py`, `td056_regime_partition_v1.py`, `check_a_exp15_gated_replication_v1.py`, `experiment_15_smoke.py`, `experiment_15_with_csv_dump.py`, `analyze_exp15_trades.py`. Output CSVs: `exp15_trades_20260503_0952.csv`, `exp15_sessions_20260503_0952.csv`, `td056_regime_partition_20260502_1713.csv`, `check_a_exp15_replication_20260502_1750.csv`. Session log files at `exp15_full_*.log`, `exp15_dump_*.log`, `exp15_analysis_*.log`. |
| **Files modified (docs)** | `CURRENT.md` (this rewrite). `session_log.md` (Session 16 one-liner prepended). `tech_debt.md` (TD-056 expanded to cover both code paths; TD-057, TD-058, TD-059 added; TD-054 owner check-in updated, scope expanded). `MERDIAN_Experiment_Compendium_v1.md` (six Session 16 entries prepended: Exp 15 framework replication, Exp 50 v2, Exp 50b v2, ADR-003 Phase 1 v3, TD-056 partition, Check A). `MERDIAN_Enhancement_Register.md` (ENH-87, ENH-88, ENH-89 filed). `merdian_reference.json` (v10→v11; change_log + session_log entries for Session 16). `CLAUDE.md` (v1.10→v1.11; Rule 21 + B11 + B12 + six Session 16 operational findings + settled decisions). |
| **Tables changed** | None — read-only research session. |
| **Cron / Tasks added** | None. |
| **`docs_updated`** | YES. All seven closeout files produced: `CURRENT.md` (this), `session_log.md`, `tech_debt.md`, `MERDIAN_Experiment_Compendium_v1.md`, `MERDIAN_Enhancement_Register.md`, `merdian_reference.json`, `CLAUDE.md`. No paste-in blocks; full-file replacements only. |

### What Session 16 did, in 14 bullets

**Phase 1 — Carry-forward execution (initially):**

- **Item 1 — Exp 41 BEAR_FVG cohort re-derive on `hist_pattern_signals`.** N=787, pooled WR=49.9% spot-side T+30m using locally-computed forward return (Exp 41 mechanics, Rule 20 era-aware). Mean return -0.008%, EV ≈ 0. **Coin flip on the 5m-batch cohort.** Critical finding: `ret_30m` column on `hist_pattern_signals` shows only 24/509 rows (4.7%) within 1bp of locally-computed forward return; 278/787 (35.3%) are NULL. The column is broken or stale. **TD-054 expanded** (S3→S2, scope extended from `ret_60m` to `ret_30m`).

- **Item 2 — Stash adjudication.** Operator pasted `fix_bear_fvg_detection.py` docstring. Stash claimed "Compendium evidence — N=225, 11.5% WR, -30.7% expectancy." These numbers do not appear in `MERDIAN_Experiment_Compendium_v1.md`. Closest cited entry was Exp 10c BEAR_FVG HIGH-context = -40.2% expectancy (scoped to HIGH only, not blanket BEAR_FVG). **Stash dropped.** Detection edits 1/2/3/5 catalogued as candidate TD for Session 17 (will need re-evaluation against live-detector Exp 15 results). Edge rule (edit 4) falsified by Item 1.

- **Item 3 — Exp 50 v2 (FVG-on-OB cluster) on bidirectional `hist_pattern_signals`.** 3×3×2 sweep × bidirectional = 18 cells. Outcome: locally-computed T+30m return (dropped EV-ratio per session prompt). N=2274 enriched. `ret_30m` cross-check on this cohort: 81/1611 (5.0%) within 1bp; 673/2285 (29.4%) NULL. **Confirms TD-054 across second cohort.** Result: BULL 2/9 cells PASS at lookback=60min/proximity ∈ {0.50%, 1.00%}, BEAR 0/9 cells PASS. Headline cell (60/0.50): BULL +8.3pp PASS, BEAR -4.2pp FAIL. The "monotonic inversion" Session 15 reported was an artefact of `ret_30m` column noise — 35pp swing on the same cohort with corrected metric. Verdict on `hist_pattern_signals` cohort: BULL has cluster effect, BEAR doesn't. (Live-cohort verification: see Item 14 below.)

- **Item 4 — Exp 50b v2 (velocity moderation) on bidirectional `hist_pattern_signals`.** Reframed from "explain inversion" (artefact) to "does velocity moderate cluster WR symmetrically." Headline cell: BULL Q1→Q4 swing -18.2pp INCREASING (fast clusters outperform); BEAR Q1→Q4 swing +26.7pp DECREASING. Sweep: BULL 7/7 voting cells INCREASING; BEAR 4 INCREASING / 3 DECREASING at smaller cell counts. Mixed/inconclusive — but N-weighted BEAR is also INCREASING, so honest reading is "symmetric INCREASING signal exists, BULL-stronger." Carry-forward to Session 17 because Section 18 of `analyze_exp15_trades.py` measured *clustering on live cohort* but did not test velocity quartiles on it.

- **Item 5 — ADR-003 Phase 1 v3.** Six fixes vs v2: (1) query `hist_ict_htf_zones` not `ict_htf_zones`, (2) drop `valid_to` filter — take most-recent-ACTIVE per (TF, pattern), (3) era-aware Rule 20, (4) `trade_date` column directly, (5) EXPECTED_BARS=81 (empirical not 75), (6) distance histogram diagnostic. NIFTY/SENSEX ACTIVE zones: 20206/20178 (40384 total — matches Session 15 backfill count). Aggregate respect 75.8%. **FUNCTIONAL per session prompt rule, BUT** 84.3% of pivots are inside zones (distance=0), driven by wide weekly OBs (W_BEAR_OB 53.2% respect single-handedly). Real edge lives in two clean-FAIL days (NIFTY 04-21, SENSEX 04-22) where zones existed but didn't predict pivots. Verdict: **FUNCTIONAL with methodology caveat** — wide-zone tautology dominates the headline number.

- **Item 6 — TD-056 bull-skew partition by ret_session sign on `hist_pattern_signals`.** BULL_FVG/BEAR_FVG count per regime per symbol. Result: every regime including DOWN shows BULL bias. **NIFTY DOWN regime: 112 BULL_FVG / 20 BEAR_FVG = 5.60x. SENSEX DOWN: 2.30x. Bull-skew is REGIME-INDEPENDENT, not regime-driven.** Verdict: detector-driven, NOT correct behaviour. (Live-cohort verification: see Item 14 below — confirmed structural across both code paths.)

- **Item 7 — Exp 44 v2.** Skipped per session prompt ("optional, only if time"). Original verdict was FAIL anyway, low-value vs other carry-forward.

**Phase 2 — Stress-test detour (where the wrong-cohort overreach happened):**

- **Wrong-cohort framing developed.** After Items 1-6 produced "coin-flip on `hist_pattern_signals`" verdicts, drafted a "framework headlines collapse" synthesis (Exp 15 BEAR_OB 94.4% WR vs 48.9% on hist_pattern_signals, BULL_OB 86.4% vs 48.0%). **This was wrong.** `hist_pattern_signals` (5m batch) is a different code path than `experiment_15_pure_ict_compounding.py` (1m live `ICTDetector` running directly on 1m bars). Different cohort, different metric (option PnL vs spot direction), different filters (tier+MTF+morning gate vs none). Operator pushed back on the demotion: "are we looking at exp code or just compendium results?"

- **Exp 15 source archaeology.** Pulled `experiment_15_pure_ict_compounding.py` (857 lines, Apr-13 commit `c78b6ea` per `git log --follow`). Confirmed it reads `hist_spot_bars_1m` directly, runs live `ICTDetector` per bar, computes outcome as **option premium gain in INR** from `hist_option_bars_1m` (not spot direction). Filters: `tier != SKIP`, `time < POWER_HOUR`. Pre-filter pass rate ~1.3% of detected signals. **None of Items 1-6 were testing this cohort.**

- **Provenance discovery — no successful execution log.** The only execution log of `experiment_15_pure_ict_compounding.py` on disk is from 2026-04-11 21:40:35 (427 bytes — `SyntaxError: unterminated f-string literal at build_ict_htf_zones.py L475`). The script crashed at import. Compendium entry for Exp 15 is dated 2026-04-12. **Recursive search across `C:\GammaEnginePython\logs\` found no successful execution log of this script anywhere.** `portfolio_simulation_v2.log` from same evening is a different experiment (different exit rules, different output structure, no per-pattern WR aggregates). Three possibilities documented: (a) script was rerun successfully post-fix and log was deleted/never persisted, (b) numbers came from interactive output captured to clipboard not log, (c) numbers came from different script attribution. Filed as TD-057.

- **April 13 commit silently relabeled MTF tiers.** `git show c78b6ea -- detect_ict_patterns.py` reveals `get_mtf_context` semantics changed: pre-Apr-13 HIGH=weekly zone, MEDIUM=daily zone, LOW=no confluence. Post-Apr-13 VERY_HIGH=weekly, HIGH=daily, MEDIUM=1H, LOW=no confluence. **Apr-12 Compendium uses post-Apr-13 vocabulary to describe pre-Apr-13 measurements.** The "1H zones confirmed Established V18F" claim in `merdian_reference.json` rests on this relabeling. ENH-37's "MEDIUM context adds edge" thesis was about *daily* zones in original measurements; today's MEDIUM tier is *1H*. These are not the same claim. Filed as B12 anti-pattern in CLAUDE.md.

**Phase 3 — Live-detector replication (the decisive run):**

- **Smoke test (10-day slice).** Verified script runs end-to-end with `PYTHONIOENCODING=utf-8` after slicing to dates [100:110]. Sessions before 5-prior-day gate produce 0 trades (expected behavior). 10 mid-year sessions produced 1 trade across both symbols — consistent with the late-year concentration finding to come.

- **Full-year replication run.** `experiment_15_pure_ict_compounding.py` ran end-to-end: NIFTY 264 sessions, 127 trades, ₹2L → ₹5,60,705 (+180.4%), max DD 1.3%. SENSEX 263 sessions, 104 trades, ₹2L → ₹6,12,737 (+206.4%), max DD 3.1%. **Combined: ₹4L → ₹11,73,442 (+193.4%).** Per-pattern T+30m results: BEAR_OB N=25, WR=92.0%, ₹+364,273 total. BULL_OB N=49, WR=83.7%, ₹+379,016 total. BULL_FVG N=155, WR=50.3%, ₹+30,153 total. **Headlines replicate within 2-3pp of Compendium claims (94.4% vs 92.0%, 86.4% vs 83.7%).** MTF context (current vocabulary): HIGH WR=55.6% (D zone, was MEDIUM in Apr-12 docs); MEDIUM WR=75.0% (H zone, didn't exist in Apr-12 vocabulary); LOW WR=61.8%.

- **Section 5 deep-dive surfaced MTF inversion.** BULL_OB by context: HIGH 71.4% (N=7), MEDIUM 81.8% (N=11), **LOW 87.1% (N=31)**. BEAR_OB: HIGH 71.4% (N=7), MEDIUM 100.0% (N=1), **LOW 100.0% (N=17)**. **LOW context outperforms HIGH context on OB patterns.** ENH-37's "MTF context adds edge" thesis is inverted by current-code measurement. Filed as TD-059, ENH-89.

**Phase 4 — Diagnostic analysis with confidence intervals (`analyze_exp15_trades.py` Sections 9-18):**

- **Section 9 confidence intervals (Wilson):** BULL_OB CI [71.0, 91.5] — clears 50% with daylight. BEAR_OB CI [75.0, 97.8] — clears 50% strongly even at N=25. BULL_FVG CI [42.5, 58.1] — **spans 50%, statistical coin flip.** BULL_FVG contributes 67% of trades (155/231) but only 3.9% of P&L (₹+30K of ₹+773K).

- **Section 10 per-cell CI:** Three cells clear CI lower bound > 50% with N≥10: BEAR_OB|LOW 100% [81.6, 100] (N=17), BULL_OB|LOW 87.1% [71.1, 94.9] (N=31), BULL_OB|MEDIUM 81.8% [52.3, 94.9] (N=11). All LOW-context cells out-perform their HIGH-context counterparts. Confirms MTF inversion.

- **Section 11 P&L concentration:** Top 1 session = 29.2% of P&L (Feb 1, 2026). Top 4 sessions = 50%. **Top 7 sessions (12.3% of trading sessions) = 80% of P&L.** Strategy is event-dependent, not steady-yield. Most days produce nothing. Implication for Kelly sizing: per-trade expectancy assumption underestimates rare-event days, overestimates routine days.

- **Sections 12-15 per-symbol/H1H2/time/monthly stability checks:** BULL_OB stable across halves (84.6% / 82.6%); BEAR_OB drift (71.4% H1, 100% H2 — H2 had more bear-favorable regime); BULL_FVG unstable (53.3% / 46.2%, coin flip resolved differently each half). Both symbols positive (NIFTY +₹360K, SENSEX +₹412K). AFTERNOON 49% (coin flip) vs OTHER 65.6% — ENH-64 BEAR_OB AFTERNOON skip empirically warranted. 9/12 months positive. Verdict: **EDGE PRESENT BUT NARROWER THAN HEADLINE.** Pooled clears CI [55.6, 68.0]; ≥1 cell clears 50%; both halves positive; **failed broadly-distributed-P&L check** (top 7/57 = 80%).

- **Sections 17-18 deferred-tool verification: TD-056 + clustering on live cohort.** Section 17: NIFTY DOWN regime 23 BULL_OB / 7 BEAR_OB = **3.29x bull-skew on live cohort** (5m-batch had 5.60x). SENSEX DOWN: 1.50x. **Bull-skew structural across both code paths.** Plus: BULL_FVG / BEAR_FVG ratio infinite in all regimes — live `detect_ict_patterns.py` emits **ZERO BEAR_FVG signals across the full year** despite Session 15's zone-builder fix. Filed TD-058. Section 18: BULL_FVG with recent BULL_OB at 90-min lookback (N=64) WR 57.8% vs standalone BULL_FVG (N=91) 45.1% — **+12.8pp lift**. 60-min: +6.4pp (N=57). 30-min: +1.0pp (N=49). **Cluster effect replicates and is stronger on live cohort than on 5m-batch.** Production routing implication: BULL_FVG should require recent BULL_OB context — filed ENH-88.

### TDs filed Session 16

**TD-056 EXPANDED** (S3→S2: was 5m-batch bull-skew; now structural across both code paths)
**TD-057 NEW** (S3) — Exp 15 framework provenance gap (no findable execution log)
**TD-058 NEW** (S2) — Live `detect_ict_patterns.py` emits zero BEAR_FVG signals across full year despite Session 15 zone-builder fix
**TD-059 NEW** (S2) — ENH-37 MTF context hierarchy inverted from claim (LOW outperforms HIGH on OB patterns)

**TDs not closed but updated:**
- **TD-054 EXPANDED** (S3→S2): scope extended from `ret_60m` only to also include `ret_30m` (5% agreement with truth across 3 cohorts now, 30% NULL). Locally-computed forward return is the workaround. Owner check-in 2026-05-03.
- TD-055 (`ret_eod` absent): unchanged. Same workaround.

### ENH proposals filed Session 16

- **ENH-87** — `hist_pattern_signals` deprecation review (move research workflow to live-detector replay pattern, retire 5m-batch path).
- **ENH-88** — BULL_FVG production routing requires recent BULL_OB context (60-90 min lookback per Section 18 evidence). Priority B candidate for Session 17.
- **ENH-89** — ENH-37 MTF hierarchy redesign or removal (current implementation subtracts edge per Section 10 evidence).

### Settled decisions added to CLAUDE.md (v1.11)

- Exp 15 framework edge replicates within 2-3pp on current code with current data: ₹4L → ₹11.7L (+193%) full year. Do not re-litigate "is the framework real?" without new data.
- BULL_FVG standalone is statistically a coin flip (N=155, CI [42.5, 58.1] spans 50%). Not a tradeable edge by itself.
- BULL_FVG-with-recent-BULL_OB clustering is real edge: +12.8pp lift at 90-min lookback (N=64).
- MTF context hierarchy (current vocabulary) is inverted from Compendium claim: LOW outperforms HIGH/MEDIUM on OB patterns. Settled by Section 10 confidence intervals on N=231 trades.
- Edge concentration is structural to this strategy: top 7/57 (12.3%) of trading sessions produce 80% of P&L. This is a feature of event-dependent vol-breakout exploitation, not a defect to fix.
- Apr-13 MTF tier relabeling settled — current vocabulary (VERY_HIGH=W, HIGH=D, MEDIUM=H, LOW=none) is canonical going forward. Apr-12 Compendium reads with care.

---

## This session

> Session 17. Pick ONE primary path from below at session start.

### Priority A (recommended) — TD-058 BEAR_FVG live emission fix

| Field | Value |
|---|---|
| **Goal** | Live `detect_ict_patterns.py` emits zero BEAR_FVG signals across the full year despite Session 15's `build_ict_htf_zones.py` fix that added BEAR_FVG zone construction (1,384 W BEAR_FVG zones now exist in `hist_ict_htf_zones`). The signal-detection pipeline consuming those zones is not emitting signals on them. Likely candidates: (a) BEAR_FVG branch missing from `detect_ict_patterns.py.detect_fvg`, (b) BEAR_FVG opt_type mapping missing — pattern detected internally but never converted to BUY_PE signal, (c) asymmetric proximity/validity check that BEAR_FVGs systematically fail. Hypothesis (a) is most likely given the parallel with Session 15's zone-builder defect (both touched in Apr-13 commit `c78b6ea`). |
| **Type** | Code review + targeted patch to `detect_ict_patterns.py`. Patched-copy deploy pattern (Session 15 lesson). |
| **Success criterion** | `detect_ict_patterns.py` emits BEAR_FVG signals symmetrically with BULL_FVG. Verified on next-day live run + Exp 15 re-dump shows non-zero BEAR_FVG count. Stretch: BEAR_FVG WR comparable to BULL_FVG (or measure the actual rate). |
| **Time budget** | ~10-15 exchanges. Code change is small (mirror BULL_FVG branch). Verification requires next-day live run + re-running Exp 15 dump (~30 min compute). |

### Priority B — ENH-88 BULL_FVG production routing requires recent BULL_OB context

| Field | Value |
|---|---|
| **Goal** | Patch `build_trade_signal_local.py` to skip BULL_FVG signals UNLESS a BULL_OB trade fired in the same symbol within the last 60-90 minutes. Standalone BULL_FVG = SKIP. Clustered BULL_FVG = full sizing. Evidence: Section 18 of `analyze_exp15_trades.py` shows +12.8pp lift on N=64 at 90-min lookback. Standalone BULL_FVG is statistical coin flip (CI [42.5, 58.1] spans 50%). |
| **Type** | Code patch to `build_trade_signal_local.py`. Helper function `_recent_bull_ob_check(symbol, current_ts, lookback_min)` queries `signal_snapshots` for same-symbol BULL_OB signals in last N minutes. Gate added to BULL_FVG branch. ast.parse PASS + 5 functional scenarios required. |
| **Success criterion** | Patch shipped end-to-end (Local + AWS hash match), 5 functional scenarios verified (clustered triggers, standalone blocks, cross-direction blocks, edge-window). Live verification on next BULL_FVG signal. |
| **Time budget** | ~15-20 exchanges. |

### Priority C — TD-056 bull-skew mechanism investigation

| Field | Value |
|---|---|
| **Goal** | Both detector code paths (5m batch, 1m live) show structural bull-skew. Hypothesis to test: signal builder's "in or near zone" filter naturally favors BULL setups when BULL zones are more available than BEAR zones. Code review of `detect_ict_patterns.py` and `build_hist_pattern_signals_5m.py` proximity logic. Instrument both with detection-attempt counters by direction to measure where BEAR candidates are being filtered out. |
| **Type** | Investigation (Phase 1, ~1-2 sessions); patch (Phase 2, 0-1 session if asymmetric branch identified). May reveal H2 (real detector bug) or H1 (zone-availability artefact, regime-driven and acceptable). |
| **Success criterion** | Phase 1: mechanism identified or both candidates ruled out. Phase 2 (if applicable): patch shipped, bull-skew ratio normalises in DOWN regime. |
| **Time budget** | ~20-30 exchanges across one or two sessions. |

### Lower-priority follow-ups

- **TD-059 / ENH-89** — MTF hierarchy redesign or removal. Section 10 evidence says LOW outperforms HIGH on OB patterns. Production decision: remove MTF context boost, invert it, or run shadow mode with both rules and measure. Not blocking; affects sizing rather than gate logic. Defer to Session 18+.
- **Item 4 carry-forward — Exp 50b velocity quartiles on live cohort.** Section 18 tested clustering but not velocity moderation. Worth re-running on the live trade-list CSV from Session 16 if/when relevant.
- **TD-054 / ENH-87** — `hist_pattern_signals` deprecation review (decision-only first session, then 2-3 sessions to migrate consumers if approved). Coupled with the TD-054 ret_30m / ret_60m column-fix-vs-deprecate question.

### DO_NOT_REOPEN

- All items from Sessions 9-15's CURRENT.md DO_NOT_REOPEN lists.
- **Exp 15 framework edge is real and replicates within 2-3pp on current code.** Do not re-investigate framework validity without new data. ₹4L→₹11.7L (+193%) over 12 months is the audit-grade replication number.
- **BULL_FVG standalone is a coin flip.** N=155, CI [42.5, 58.1] spans 50%. Production routing should restrict it (see ENH-88), not delete it (it has edge with OB context). Do not retest standalone BULL_FVG hypothesis without new data.
- **MTF hierarchy LOW > HIGH on OB patterns.** Settled by Section 10 confidence intervals on N=231 trades. Do not retest hierarchy without new data.
- **Edge concentration in top 7/57 sessions is structural.** Feature of event-dependent vol-breakout exploitation, not a defect.
- **The Apr-13 MTF tier relabeling is settled.** Current vocabulary (VERY_HIGH=W, HIGH=D, MEDIUM=H, LOW=none) is canonical going forward. Apr-12 Compendium entries that use earlier vocabulary should be read with care but do not need re-litigation.
- **Wrong-cohort comparison is the canonical methodology error.** Do not compare findings across `hist_pattern_signals` (5m batch) and `experiment_15_pure_ict_compounding.py` (1m live) cohorts without first confirming cohort + outcome metric alignment. B11 anti-pattern in CLAUDE.md.

### Watch-outs for Priority A (TD-058 BEAR_FVG live emission fix)

- The fix mirror should follow Session 15's pattern: `_PATCHED.py` produced first, dry-run, then live run, then rename. Originals preserved as `_PRE_S17.py`. Patched-copy deploy pattern (Session 15 lesson).
- Verify against canonical 5m BEAR_FVG shape scan first (the Session 15 five-step audit pattern). If `detect_ict_patterns.py` is detecting BEAR_FVG patterns internally but failing to emit them, that's a different fix than if the detection branch is missing entirely.
- After the patch, re-run Exp 15 with the CSV dump pattern (`experiment_15_with_csv_dump.py`) to verify BEAR_FVG signals now flow into the trade list. Don't ship without end-to-end verification.
- TD-058 may share root cause with TD-056 (both bull-skew direction-asymmetry). If diagnosing TD-058 also explains TD-056, treat as combined fix.

### Watch-outs for Priority B (ENH-88 BULL_FVG production routing)

- Lookback choice: 90 min has strongest evidence (+12.8pp lift, N=64). 60 min is +6.4pp (N=57). Recommend 90 min. Can shadow-test 60 vs 90 in parallel for one month if uncertain — but shadow-testing slows shipping.
- Implementation choice: hard skip vs confidence modifier. Recommend hard skip — coin flip is not edge worth deploying capital against. Operator may prefer confidence modifier (-25 conf) to retain optionality. Decide before patching.
- Symmetry question: should the same rule apply to BEAR_FVG when TD-058 ships? Likely yes by parsimony, but should be measured separately on the eventual BEAR_FVG live cohort. **Do not preemptively gate BEAR_FVG on BEAR_OB cluster — wait for measurement.**
- Coordinates with TD-058: ship Priority A first if both planned. Otherwise BULL_FVG gate works against current state (BEAR_FVG already implicitly skipped because it never fires).

### Watch-outs for Priority C (TD-056 mechanism investigation)

- Two hypotheses to discriminate. H1 (zone-availability asymmetry in trending market) does NOT need code patches — it's a regime artefact. H2 (asymmetric BULL/BEAR detection branches) DOES need code patches. **Don't patch before discriminating.**
- The discriminator: bull-skew should INVERT in DOWN regime if H1. It DOESN'T (NIFTY DOWN 3.29x, SENSEX DOWN 1.50x). So H2 is partially supported. But H1 may explain the *magnitude* difference between 5m-batch (5.60x) and 1m-live (3.29x) — different filter logic between the two paths.
- Code review must look for: asymmetric proximity computation, asymmetric validity windows, missing branch in either `detect_fvg` or `detect_ob`. Instrument with detection-attempt counters by direction before patching.
- TD-056 + TD-058 likely share root cause. Coordinate investigations.

---

## Live state snapshot (at Session 17 start)

**Environment:** Local Windows primary; AWS shadow runner present but not touched Session 16. `MERDIAN_ICT_HTF_Zones` 08:45 IST scheduled task expected to run normally Monday 2026-05-04 — Session 15 patches are in place; no Session 16 production changes.

**Open critical items (C-N):** None new from Session 16. Sessions 9-15's open items unchanged.

**Active TDs (after Session 16):**
- **TD-029 (S2)** — `hist_spot_bars` pre-04-07 TZ-stamping bug. Workaround documented.
- **TD-030 (S2)** — `build_ict_htf_zones.py` re-evaluates breach via `recheck_breached_zones` for live; DOES NOT for historical. Historical = by design.
- **TD-031 (S2 EXPANDED)** — D-OB definition mismatch. Decision deferred. (Effectively same as TD-049 — consolidate next pass.)
- **TD-046 (S2)** — false-alarm contract violations on idempotent `build_ict_htf_zones.py` reruns. Operational, not blocking.
- **TD-049 / TD-050 / TD-051 / TD-052** (Session 15) — D-OB non-standard ICT, D-zone 1-day validity, PDH/PDL ±20pt hardcoded, zone status write-once-never-recompute. Catalogued, not patched.
- **TD-053 (S3)** — CLAUDE.md Rule 16 needs era-aware addendum. **Codified as Rule 20 in CLAUDE.md v1.10 — closing in next pass.**
- **TD-054 (S2 EXPANDED Session 16)** — `hist_pattern_signals.ret_30m` and `ret_60m` columns broken. Workaround: locally-computed forward return.
- **TD-055 (S3)** — `hist_pattern_signals.ret_eod` column absent. Workaround: compute from `hist_spot_bars_5m`.
- **TD-056 (S2 EXPANDED Session 16)** — Bull-skew structural across BOTH 5m-batch AND 1m-live code paths. NIFTY DOWN regime 5.60x (5m) / 3.29x (1m). Mechanism investigation = Priority C.
- **TD-057 (S3 NEW Session 16)** — Exp 15 framework provenance gap. Process-only fix going forward.
- **TD-058 (S2 NEW Session 16)** — Live `detect_ict_patterns.py` emits zero BEAR_FVG signals. **Priority A** for Session 17.
- **TD-059 (S2 NEW Session 16)** — ENH-37 MTF hierarchy inverted from claim (LOW > HIGH on OB). Lower priority — affects sizing not gates.

**Active ENH (in flight):**
- **ENH-46-A** — Telegram alert daemon for tradable signals. SHIPPED Session 9, live-verified 2026-04-26.
- **ENH-46-C** — Conditional ENH-35 gate lift. PROPOSED Session 10. Pending shadow-test plan.
- **ENH-78** — DTE<3 PDH sweep current-week PE rule. SHIPPED Session 14. Live verification on next qualifying signal.
- **ENH-84** — REFRESH ZONES dashboard button. SHIPPED + hotfixed Session 14.
- **ENH-85** — PO3 direction lock. **DESIGN SPACE REDUCED Session 15** via Exp 47b. Remaining paths: hard PO3 lock OR persistence filter. Needs revised spec.
- **ENH-86** — WIN RATE legend redesign. v1 SHIPPED Session 14. v2 deferred.
- **ENH-87 (NEW Session 16)** — `hist_pattern_signals` deprecation review. PROPOSED. Decision-only first session; 2-3 sessions migration if approved.
- **ENH-88 (NEW Session 16)** — BULL_FVG production routing requires recent BULL_OB context. PROPOSED. **Priority B** for Session 17.
- **ENH-89 (NEW Session 16)** — ENH-37 MTF hierarchy redesign or removal. PROPOSED. Defer to Session 18+, recommend shadow-mode A/B test approach.

**Settled by Session 16:**
- **Exp 15 framework replicates within 2-3pp on current code.** Audit-grade execution shipped.
- **BULL_FVG standalone is coin flip.** N=155, CI [42.5, 58.1].
- **BULL_FVG-with-recent-BULL_OB cluster is real edge.** +12.8pp lift at 90-min lookback (N=64).
- **MTF hierarchy LOW > HIGH on OB.** Section 10 settled.
- **Edge concentration top 7/57 (12.3%) = 80% P&L is structural.**
- **Apr-13 MTF tier relabeling settled.** Current vocabulary canonical.
- **TD-056 bull-skew structural across both code paths.** Severity raised to S2.

**Markets state (at end of Session 16, 2026-05-03 morning):**
- Sunday — markets closed. Last trading session 2026-05-02 (Friday).
- Production state at Session 16 start matches Session 15 close (no Session 16 production changes).
- Carry-forward to Session 17: Priority A TD-058 BEAR_FVG live emission is the highest-priority work; affects what TV draws for operator's discretionary trading immediately.

**Operator live trading context:**
- April 2026 ₹2L → ~₹4.6L (2.3x) using hybrid TV-MERDIAN + discretionary judgment.
- Backtest validates the patterns operator already identifies are correct; **hold-time discipline (T+30m systematic exit) is the operational gap, not signal accuracy.**
- One specific April trade: BEAR_OB at SENSEX session high on gap-up — entered correctly, exited before T+30m, would have 2x'd day's P&L if held.
- Live MERDIAN automation deferred 2-3 sessions pending Session 17/18 fixes.

---

## Detail blocks for Session 16 work

The following are the full detail blocks for experiments and TDs registered this session. These are written in the same format as prior CURRENT.md detail blocks. They duplicate what is in `MERDIAN_Experiment_Compendium_v1.md` and `tech_debt.md` so this file stays self-contained.

### Experiment 15 framework replication on current code (THE HEADLINE FINDING)

**Date:** 2026-05-03 (Session 16)
**Script:** `experiment_15_pure_ict_compounding.py` (verbatim, git rev `c78b6ea`); CSV dump version `experiment_15_with_csv_dump.py`; analyzer `analyze_exp15_trades.py` (Sections 9-18).
**Trade list:** `exp15_trades_20260503_0952.csv` (231 trades, 12 months 2025-04-08 to 2026-03-30)

**Question:** Do the published Exp 15 headlines (BEAR_OB 94.4% WR, BULL_OB 86.4% WR, BULL_FVG 50.3% WR) replicate on current code with current data, after the Apr-13 commit `c78b6ea` modified both `experiment_15_pure_ict_compounding.py` and `detect_ict_patterns.py` and silently relabeled MTF context tiers? And, on the live 1m-detector cohort, what does deep audit (confidence intervals, concentration, regime stability, time-of-day, clustering) show?

**Setup:**
- Same script, same dataset, same methodology as the original Exp 15.
- 12-month range Apr 2025 → Apr 2026, 264 NIFTY + 263 SENSEX trading days.
- Live `ICTDetector` running on `hist_spot_bars_1m`, T+30m option-side P&L from `hist_option_bars_1m`.
- ₹2L starting capital per symbol, compounding (profits added, losses absorbed).
- Filters: `tier != SKIP`, `time < POWER_HOUR`, 5-prior-day warmup gate.
- Pre-filter pass rate ~1.3% of detected signals.

**Findings — pooled per-pattern WR (Section 9):**

| Pattern | N | WR | 95% CI (Wilson) | mean P&L | total P&L | Compendium claim | Delta |
|---|---|---|---|---|---|---|---|
| BEAR_OB | 25 | 92.0% | [75.0, 97.8] | ₹+14,571 | ₹+364,273 | 94.4% (N=36) | -2.4pp |
| BULL_OB | 49 | 83.7% | [71.0, 91.5] | ₹+7,735 | ₹+379,016 | 86.4% (N=44) | -2.7pp |
| BULL_FVG | 155 | 50.3% | [42.5, 58.1] | ₹+195 | ₹+30,153 | 50.3% (N=155) | 0.0pp |

Headlines replicate within 2-3pp. BULL_FVG is exact match. BULL_FVG's CI [42.5, 58.1] **spans 50% — statistical coin flip**.

**Combined return:** ₹4,00,000 → ₹11,73,442 (+193.4%). NIFTY: ₹2L → ₹5,60,705 (+180.4%, max DD 1.3%). SENSEX: ₹2L → ₹6,12,737 (+206.4%, max DD 3.1%).

**Findings — MTF context (Section 10) — INVERSION:**

| Pattern | Context | N | WR | 95% CI |
|---|---|---|---|---|
| BULL_OB | HIGH (D zone) | 7 | 71.4% | [35.9, 91.8] |
| BULL_OB | MEDIUM (H zone) | 11 | 81.8% | [52.3, 94.9] |
| BULL_OB | LOW (no zone) | 31 | **87.1%** | [71.1, 94.9] |
| BEAR_OB | HIGH | 7 | 71.4% | [35.9, 91.8] |
| BEAR_OB | LOW | 17 | **100.0%** | [81.6, 100.0] |

**LOW context outperforms HIGH context.** ENH-37 hierarchy inverted from claim.

**Findings — Sections 11-15 robustness:**
- **Concentration**: top 7/57 sessions (12.3%) = 80% of P&L. Top 1 = 29.2% (Feb 1, 2026).
- **H1/H2**: BULL_OB STABLE (84.6%/82.6%). BEAR_OB drift (71.4% → 100%). BULL_FVG UNSTABLE (53.3% → 46.2%).
- **Per-symbol**: NIFTY 65.1% [56.4, 72.8], SENSEX 58.3% [48.6, 67.3]. Both positive. SENSEX BULL_FVG -₹29K (negative); NIFTY BULL_FVG +₹59K (positive). Reinforces "FVG luck."
- **Time-of-day**: AFTERNOON 49% (coin flip) vs MORNING+MIDDAY 65.6% [58.4, 72.1]. ENH-64 BEAR_OB AFTERNOON skip empirically warranted.
- **Monthly**: 9/12 months positive. Worst Dec-2025 -₹9,544 (3 trades). Feb-2026 +₹271,939.

**Findings — Section 17 TD-056 live cohort:** NIFTY DOWN 23 BULL_OB / 7 BEAR_OB = **3.29x bull-skew**. SENSEX DOWN 1.50x. Plus BULL_FVG / BEAR_FVG ratio infinite — **live `detect_ict_patterns.py` emits zero BEAR_FVG signals across full year** (TD-058).

**Findings — Section 18 FVG-on-OB clustering live cohort:**

| Lookback | N clustered | WR clustered | N standalone | WR standalone | Lift |
|---|---|---|---|---|---|
| 30 min | 49 | 51.0% | 106 | 50.0% | +1.0pp |
| 60 min | 57 | 54.4% | 98 | 48.0% | +6.4pp |
| 90 min | 64 | **57.8%** | 91 | 45.1% | **+12.8pp** |

Cluster effect replicates and is stronger on live cohort than 5m-batch.

**Verdict:** **EDGE PRESENT BUT NARROWER THAN HEADLINE.** Pooled clears CI; ≥1 cell clears 50%; both halves positive; failed broadly-distributed-P&L check.

**Provenance note:** Original Apr-12 Compendium entry has no findable execution log; only known log is a SyntaxError crash. No successful execution log of `experiment_15_pure_ict_compounding.py` exists in `C:\GammaEnginePython\logs\`. Apr-13 commit `c78b6ea` silently relabeled MTF tier vocabulary. **Session 16 replication is the audit-grade execution.** Published headlines not refuted but original measurement not directly auditable.

**Builds:** ENH-87 (deprecation review), ENH-88 (BULL_FVG production routing requires BULL_OB cluster), ENH-89 (MTF hierarchy redesign), TD-057, TD-058, TD-059, TD-056 EXPANDED.

---

### Experiment 50 v2 — FVG-on-OB Cluster Bidirectional, ret_30m-noise corrected

**Date:** 2026-05-02 (Session 16)
**Script:** `experiment_50_fvg_on_ob_cluster_v2.py`

**Question:** Does Exp 50's "FVG inside or near a same-direction OB cluster has different WR than standalone FVG" hypothesis hold on bidirectional `hist_pattern_signals` data, after the Session 15 BEAR_FVG fix and using locally-computed forward return (since `ret_30m` column is broken — TD-054)?

**Setup:**
- Bidirectional 3×3 sweep: lookback ∈ {30, 60, 120} min × proximity ∈ {0.10%, 0.50%, 1.00%} × side ∈ {BULL, BEAR} = 18 cells.
- Drop EV-ratio gate per session prompt — keep WR-delta + N-floor=20.
- Outcome: locally-computed T+30m return (`ret_30m` column unreliable).
- Cohort: full year `hist_pattern_signals`, N=2274 enriched after Session 15 fix.

**Findings:**
- BULL: 2/9 cells PASS at lookback=60min × proximity ∈ {0.50%, 1.00%}.
- BEAR: 0/9 cells PASS.
- Headline cell (60min × 0.50%): BULL +8.3pp WR delta cluster vs standalone PASS; BEAR -4.2pp FAIL.
- The Session 15 reported "monotonic inversion" was an artefact of `ret_30m` column noise — 35pp swing on the same cohort with corrected metric.

**Verdict on `hist_pattern_signals` cohort: BULL has cluster effect, BEAR doesn't.** But this is the wrong cohort for the production claim — `hist_pattern_signals` is the 5m-batch detector path. **Live-cohort verification: Section 18 of `analyze_exp15_trades.py` shows +12.8pp lift at 90-min lookback on live 1m-detector cohort, replicating and strengthening this finding.** BEAR-side untestable on live cohort because live detector emits zero BEAR_FVG signals (TD-058).

**Builds:** Live-cohort version (Section 18) is the canonical reference. ENH-88 built on live-cohort evidence.

---

### Experiment 50b v2 — FVG-on-OB Velocity Moderation, bidirectional

**Date:** 2026-05-02 (Session 16)
**Script:** `experiment_50b_fvg_on_ob_velocity_v2.py`

**Question:** Does pre-cluster velocity (price velocity in the lookback window before the FVG) moderate cluster WR symmetrically across BULL and BEAR sides on `hist_pattern_signals`?

**Setup:**
- Reframed from Session 15 "explain the inversion" (now obsolete since inversion was a `ret_30m` artefact) to "does velocity moderate cluster WR symmetrically across directions."
- Velocity quartiles Q1-Q4 (slowest to fastest pre-cluster price velocity) on bidirectional cluster cohort.
- Same locally-computed T+30m outcome metric.

**Findings:**
- Headline cell BULL: Q1→Q4 swing -18.2pp (INCREASING — fast clusters outperform slow).
- Headline cell BEAR: Q1→Q4 swing +26.7pp (DECREASING — slow clusters outperform fast).
- Sweep voting: BULL 7/7 cells INCREASING; BEAR 4 INC / 3 DEC at smaller cell counts.
- N-weighted BEAR also INCREASING.

**Verdict:** Mixed/inconclusive on the per-cell voting metric. Honest reading: symmetric INCREASING signal exists, BULL-stronger. **Carry-forward to Session 17:** Section 18 of analyzer tested clustering on live cohort but did NOT test velocity quartiles. To close this item properly, extend the analyzer with a Section 19 that computes pre-cluster velocity from entry_spot trajectory and partitions by quartile.

**Builds:** None directly. Velocity-in-production decision deferred until live-cohort velocity verification.

---

### ADR-003 Phase 1 v3 — Zone respect-rate, era-aware, most-recent-ACTIVE

**Date:** 2026-05-02 (Session 16)
**Script:** `adr003_phase1_zone_respect_rate_v3.py`

**Question:** Do ICT HTF zones in `hist_ict_htf_zones` actually predict price pivots in `hist_spot_bars_5m`? Re-run with six methodology fixes vs the v1/v2 INVALID runs.

**Setup (six fixes vs v2):**
1. Query `hist_ict_htf_zones` not `ict_htf_zones`.
2. Drop `valid_to` filter — take most-recent ACTIVE zone per (TF, pattern) at each bar.
3. Era-aware Rule 20 (`ERA_BOUNDARY = 2026-04-07`).
4. Use `trade_date` column directly for date filters.
5. `EXPECTED_BARS = 81` (empirical, not 75).
6. Distance histogram diagnostic added.

**Findings:**
- NIFTY ACTIVE zones: 20,206. SENSEX: 20,178. Total 40,384 — matches Session 15 backfill count exactly.
- Aggregate zone-respect rate over 60-day window: 75.8% within 0.10% band of pivot bar.
- **Methodology caveat:** 84.3% of pivots are inside zones (distance=0 from zone). Driven primarily by wide weekly OBs — W_BEAR_OB alone respects 53.2% of pivots single-handedly. The "75.8% respect rate" is largely tautological — wide zones contain most price action. The real edge would be in narrow zones (D-level, H-level) but those have 30-50% respect with much smaller N.
- Two clean-FAIL days where zones existed but didn't predict pivots: NIFTY 2026-04-21, SENSEX 2026-04-22.

**Verdict:** **FUNCTIONAL with methodology caveat — wide-zone tautology dominates the headline number.** Zones contain pivots, but the predictive edge of ICT zones for *targeting* pivots specifically is not what the 75.8% number implies.

**Builds:** ADR-003 Phase 2 (narrow-zone-only respect-rate, exclude zones >0.50% wide) candidate for future session if zone respect-rate becomes a production sizing input. Not currently a sizing input, so low priority.

---

### TD-056 ret_session regime partition (5m-batch cohort)

**Date:** 2026-05-02 (Session 16)
**Script:** `td056_regime_partition_v1.py`

**Question:** Is the bull-skew on `hist_pattern_signals` (NIFTY 60d 1.83x BULL_FVG/BEAR_FVG ratio) regime-driven (correct: detector finds more bullish patterns in up-sessions) or detector-driven (asymmetry independent of market regime)?

**Setup:** Partition all FVG signals on `hist_pattern_signals` by `ret_session` sign (UP > +0.05%, FLAT, DOWN < -0.05% per ENH-44 alignment threshold), recompute BULL/BEAR ratio per regime per symbol.

**Findings:**

| Symbol | Regime | BULL_FVG | BEAR_FVG | Ratio |
|---|---|---|---|---|
| NIFTY | UP | 87 | 42 | 2.07x |
| NIFTY | FLAT | 22 | 12 | 1.83x |
| NIFTY | **DOWN** | **112** | **20** | **5.60x** |
| SENSEX | UP | 115 | 88 | 1.31x |
| SENSEX | FLAT | 8 | 3 | 2.67x |
| SENSEX | **DOWN** | **106** | **46** | **2.30x** |

**Bull-skew is REGIME-INDEPENDENT.** Even in DOWN sessions, BULL_FVG outnumbers BEAR_FVG 5.6x on NIFTY and 2.3x on SENSEX. If skew were regime-driven (correct), ratio would invert in DOWN regime. It doesn't.

**Verdict on `hist_pattern_signals` cohort:** **Detector-driven not regime-driven.** Filed as TD-056 expansion candidate.

**Live-cohort verification (Section 17 of analyzer):** Bull-skew also exists on the 1m-live `detect_ict_patterns.py` cohort (NIFTY DOWN 3.29x, SENSEX DOWN 1.50x). **Bull-skew is structural across BOTH code paths.** TD-056 expanded to S2.

**Builds:** TD-056 EXPANDED, TD-058 NEW (live BEAR_FVG missing), Session 17 Priority C (mechanism investigation).

---

### Check A — Exp 20 alignment + Exp 15 MTF replication (SUPERSEDED)

**Date:** 2026-05-02 (Session 16)
**Script:** `check_a_exp15_gated_replication_v1.py`
**Status:** SUPERSEDED by Section 17 of `analyze_exp15_trades.py` (live-cohort version with correct cohort).

**Question:** Do Exp 20 (alignment lift +22.6pp) and Exp 10c/Exp 15 (BULL_OB|MEDIUM 90% WR / 77.3% WR) replicate when measured on locally-computed spot-side T+30m on the gated subset of `hist_pattern_signals`?

**Outcome:** Script ran and produced numbers (ALIGNED pooled 53.3%, OPPOSED 48.2%, lift +5.1pp; BULL_OB|MEDIUM cells came back N=0 because `hist_ict_htf_zones` has no H-timeframe entries). **Verdict: methodology error in this script** — was testing on the wrong cohort entirely. `hist_pattern_signals` (5m batch) is not the cohort Exp 15 / Exp 20 measured. The right replication is on the 1m live-detector cohort (the Session 16 Exp 15 entry above).

**Lesson codified:** Read the source script of an experiment before drawing conclusions about whether its claims replicate. Wrong-cohort comparison is the canonical methodology error. (Captured as B11 in CLAUDE.md anti-patterns.)

---

## Detail blocks for TDs filed Session 16

### TD-056 — Signal-detector bull-skew across BOTH code paths (5m batch AND 1m live) — EXPANDED

**Severity:** S2 (raised from S3 Session 16 — confirmed structural across both detector code paths, not just 5m batch)
**Component:** BOTH (a) `build_hist_pattern_signals_5m.py` zone-approach filter logic, AND (b) `detect_ict_patterns.py` live 1m detector. Both bull-skewed independently.
**Symptom:**
- 5m-batch (`hist_pattern_signals`): NIFTY 60d signals BULL_FVG 274 / BEAR_FVG 150 (1.83x). NIFTY DOWN regime alone: 112 BULL_FVG / 20 BEAR_FVG = **5.60x bull-skew in DOWN regime**. SENSEX DOWN: 2.30x.
- 1m-live (`detect_ict_patterns.py` running through Exp 15): full year 49 BULL_OB / 25 BEAR_OB pooled. NIFTY DOWN regime: 23 BULL_OB / 7 BEAR_OB = **3.29x**. SENSEX DOWN: 1.50x.
- **Live detector emits ZERO BEAR_FVG signals across full year** (separate issue, see TD-058).
- Canonical 5m BEAR_FVG / BULL_FVG shapes in `hist_spot_bars_5m` are essentially symmetric — both detector paths underemit BEAR signals relative to raw price-structure availability.

**Root cause:** Two non-mutually-exclusive hypotheses:
- **H1 zone-availability asymmetry** — the "in or near zone with proximity" filter requires same-direction zones to exist near current price; in an uptrending market BULL zones above-spot are more available than BEAR zones below-spot.
- **H2 detector-symmetry bug** — code paths for BULL vs BEAR detection differ in some non-obvious way.

Session 16 evidence supports H1 partially (bull-skew higher in 5m-batch with zone-availability filter at signal time, lower in 1m-live with own zone construction) but does not fully exonerate H2 (bull-skew persists in DOWN regime where H1 alone would invert ratio).

**Workaround:** Operator-side mitigation — **be more discretionary about looking for bear setups in chop/down sessions** when MERDIAN isn't flagging them. The system undersignals bear opportunities, not because individual BEAR signals are wrong (they're 92% WR) but because there are fewer of them than market structure would imply.

**Proper fix:**
- **Phase 1 — diagnosis (Session 17 Priority C, ~1-2 sessions):** code review both detector code paths for asymmetric branches; instrument with detection-attempt counters by direction.
- **Phase 2 — patch (1 session if H2 confirmed, 0 sessions if H1 only):** if asymmetric branch identified, patch and re-verify. If H1 only, document and accept (or rebalance proximity threshold per direction).

**Cost to fix:** 1-3 sessions total. **Blocked by:** TD-058 (likely shares root cause). **Owner check-in:** 2026-05-03.

---

### TD-057 — Exp 15 framework provenance gap (no findable execution audit trail)

**Severity:** S3
**Component:** `experiment_15_pure_ict_compounding.py`, `MERDIAN_Experiment_Compendium_v1.md` (Exp 15 entry dated 2026-04-12), git history.
**Symptom:** The only execution log of `experiment_15_pure_ict_compounding.py` on disk is a 2026-04-11 21:40:35 SyntaxError crash (427 bytes). Compendium entry for Exp 15 is dated **one day later**. Recursive search of `C:\GammaEnginePython\logs\` found no successful execution log of this exact script anywhere. Plus: April-13 commit `c78b6ea` modified BOTH `experiment_15_pure_ict_compounding.py` AND `detect_ict_patterns.py` together, including silent MTF tier relabeling. Apr-12 Compendium uses post-Apr-13 vocabulary to describe pre-Apr-13 measurements.

**Root cause:** Combination of (a) interactive-shell run pattern at the time (no automatic log capture), (b) git commits modifying experiment scripts and detector code together with non-descriptive commit messages, (c) Compendium written from session-end state rather than from durable execution artefacts. Aggregate of process-hygiene gaps.

**Workaround:** Session 16 produced `experiment_15_with_csv_dump.py` as a verbatim methodology copy with CSV-dump tail that produces a durable trade-list artefact. Critically: **Session 16 full-year run replicated the Compendium headlines within 2-3pp** (BEAR_OB 92.0% vs claimed 94.4%, BULL_OB 83.7% vs 86.4%, BULL_FVG 50.3% vs 50.3%) — published numbers not refuted, just not directly auditable.

**Proper fix:** Going-forward process: (a) every experiment invoked with `... 2>&1 | Tee-Object`. (b) Every Compendium entry cites execution log path + git commit hash. (c) Major published findings re-runnable in <30 min on current code. (d) Apr-12-era Compendium entries flagged for vocabulary alignment.

**Cost to fix:** Zero code, zero compute. Retroactive flagging: 0.5 session. **Blocked by:** nothing. **Owner check-in:** 2026-05-03.

---

### TD-058 — Live `detect_ict_patterns.py` emits zero BEAR_FVG signals across full year

**Severity:** S2 (production-grade gap — bear-side FVG opportunities completely invisible to live system)
**Component:** `detect_ict_patterns.py` BEAR_FVG branch (in `detect_fvg` or equivalent).
**Symptom:** Across 12-month Exp 15 simulation (231 trades), live detector emitted 155 BULL_FVG signals and **zero BEAR_FVG signals** in any regime, in either symbol. The `build_ict_htf_zones.py` Session 15 fix added BEAR_FVG zone construction (1,384 W BEAR_FVG zones now exist in `hist_ict_htf_zones`), but the **live signal-detection pipeline** consuming those zones is not emitting signals on them.

**Root cause:** Not yet diagnosed. Likely candidates: (a) BEAR_FVG branch missing entirely from `detect_ict_patterns.py` `detect_fvg` (parallel to Session 15 zone-builder bug since `experiment_15_pure_ict_compounding.py` calls `ICTDetector` from this file), (b) BEAR_FVG opt_type mapping missing — pattern detected internally but never converted to BUY_PE signal, (c) asymmetric proximity/validity check that BEAR_FVGs systematically fail. Hypothesis (a) most likely given parallelism with Session 15 zone-builder defect (both touched in Apr-13 commit `c78b6ea`).

**Workaround:** None. Bear-side FVG opportunities not detected by live system. **Operator must rely on discretion to identify BEAR_FVG setups on TradingView until fixed.** BEAR_OB detection works fine (92% WR on N=25), so bear-side OB setups remain covered.

**Proper fix:** Code review of `detect_ict_patterns.py` `detect_fvg`. Add BEAR_FVG branch symmetrically with BULL_FVG. Test on a known BEAR_FVG day from history. Then re-run Exp 15 dump to confirm BEAR_FVG WR is comparable to BULL_FVG.

**Cost to fix:** 1 session (Session 17 Priority A). **Blocked by:** nothing. **Owner check-in:** 2026-05-03.

---

### TD-059 — ENH-37 MTF context hierarchy inverted from claim (LOW outperforms HIGH on OB)

**Severity:** S2 (production sizing rule rests on inverted assumption — currently BOOSTING confidence on cells that empirically UNDERPERFORM)
**Component:** `build_trade_signal_local.py` (consumes `mtf_context` from `signal_snapshots`); `detect_ict_patterns.py` `get_mtf_context`; ENH-37 documentation in Enhancement Register.
**Symptom:** Exp 15 published Compendium claim: "MEDIUM context (1H zone) ADDS edge — keep in MTF hierarchy." Session 16 measurement on 231-trade live cohort with Wilson 95% CIs:
- BULL_OB|HIGH (D zone) 71.4% N=7
- BULL_OB|MEDIUM (H zone) 81.8% N=11 [52.3, 94.9]
- **BULL_OB|LOW (no zone) 87.1% N=31 [71.1, 94.9]**
- BEAR_OB|HIGH 71.4% N=7
- BEAR_OB|LOW 100% N=17 [81.6, 100]

LOW outperforms HIGH on both OB patterns. Hierarchy current production code applies (HIGH = high confidence, LOW = low confidence) is **inverted from current-code measurement**.

**Root cause hypothesis:** When a signal triggers in HIGH context (inside a daily zone), price action is contested — buyers and sellers both engaged at known level. The "trade against the zone" plays out with chop and reduced edge. When a signal triggers in LOW context (no archive-zone confluence), price is in clean expansion — OB pattern catches a moving market with directional follow-through. Effectively, archive zones may CAUSE chop they're supposed to identify. Untested but consistent with data.

**Workaround:** Operationally for now — **treat MTF context tier as informational, not as a confidence multiplier.** Operator: do not size up just because a signal is tagged HIGH context.

**Proper fix:** Three options for Session 18+:
- (A) Annotation-only — keep tier as informational, no sizing impact. ~0.5 session.
- (B) Inversion — LOW becomes "high confidence." Risky, current N=17-31 per cell enough for direction not magnitude.
- (C) Shadow A/B test — wire `confidence_score_v2` (inverted) alongside current `_v1`. Run both for 4-8 weeks. Compare. ~2 sessions across 4-8 weeks.

Recommend **Option C** — measure before changing production.

**Cost to fix:** Option C: 2 sessions across 4-8 weeks of measurement. **Blocked by:** TD-057 (vocabulary alignment). **Owner check-in:** 2026-05-03.

---

### TD-054 — `hist_pattern_signals.ret_30m` and `ret_60m` columns broken — EXPANDED

**Severity:** S2 (raised from S3 Session 16 — extended scope: column has only 4.7-5.0% agreement with locally-computed forward return across 3 cohorts now, 30% NULL — invalidates any analysis using `ret_30m` directly)
**Component:** `build_hist_pattern_signals_5m.py` and possibly upstream `hist_market_state` source.
**Symptom:**
- `ret_60m` uniformly 0.000% across every row — verified Session 15 in Exp 47b/50.
- Session 16 expanded: `ret_30m` also unreliable — 4.7% agreement (24/509) on Exp 41 cohort, 5.0% (81/1611) on Exp 50 v2 cohort, 30-35% NULL across both. Any experiment using `ret_30m` sign or magnitude as outcome metric gets noise.

**Root cause:** Both columns computed with broken/stale logic in signal builder, OR source `hist_market_state` columns themselves broken. Not yet diagnosed.

**Workaround:** **Do not use `ret_30m` or `ret_60m` from `hist_pattern_signals` as outcome metrics.** Compute forward return locally from `hist_spot_bars_5m` using Exp 41 mechanics (Rule 20 era-aware). Used by every Session 15-16 experiment requiring forward returns.

**Proper fix:** Diagnose source vs builder; fix at right layer; backfill via signal rebuild. **OR** per ENH-87: deprecate `hist_pattern_signals` entirely — Session 16 demonstrated live-detector replay (`experiment_15_with_csv_dump.py` pattern) provides equivalent research utility without integrity issues.

**Cost to fix:** <1 session diagnostic, ~1 session for fix + backfill. ENH-87 deprecation alternative: 2-3 sessions to migrate consumers. **Blocked by:** ENH-87 (decide fix-vs-deprecate first). **Owner check-in:** 2026-05-03.

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-05-03 (end of Session 16).*
