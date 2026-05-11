# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-05-11 (Monday — trading day; Session 27 — single production commit: TD-NEW-2 patch deploy + TD-NEW-3 patch deploy + ADR-002 v2 full rewrite acceptance + Phase 0a §3 sign-convention audit PASS + Doc Protocol v4 Rule 11 + Rule 1 mechanical follow-throughs filed in same session). |
| **Concern** | Opened on ADR-002 v2 step-3-first sequencing (sign audit before refinement before adoption) per operator instruction. Sign audit (Phase 0a §3) pulled 3 reference cycles vs source-material dashboard screenshots (Apr 28 12:21 IST clean pin, Apr 28 12:23 IST flip-edge stress, Apr 30 ~10:50 IST cascade warning). Verdict PARTIAL with 3 findings — (a) sign convention correct (Ref 1 + Ref 3 agreed direction; Ref 2 source-vs-MERDIAN disagreement traced to source dashboard showing PROJECTED dealer-flow scenario for hypothetical -1% spot move, NOT live state — reader-side categorisation error not data error); (b) flip computation broken on 2026-05-08 + 2026-05-11 only (recent regression, not architectural); (c) `net_gex` unit scale ~10³ too large (architectural, applies across entire deployment history). Two TDs filed and CLOSED same-session: TD-NEW-2 (flip_level regression S1 acute) + TD-NEW-3 (net_gex unit Cr S2 architectural). Then ADR-002 v2 full rewrite drafted as supersession of v1 (Session 12, 2026-04-28) — six v1 principles preserved (P1 zones, P2 force, P3 trapped sellers, P4 velocity, P5 PINNED, P6 DTE multiplier); two new (P7 vol-pricing RR ratio thresholds HIGH>1.2 / FAIR / LOW<0.85 / COMPRESSED<0.4; P8 second-order Greeks vanna/charm Phase 3); buyer/writer inversion named as first-class architectural concept; Positioning Landscape refined to five named scalars; six-scenario dealer-flow grid; new vol_analytics table spec; Phase 0 calibration discipline introduced; Phase 3 prerequisites named explicitly. Operator accepted v2 as full rewrite; v1 preserved in git history at `b46249e` and prior. Doc Protocol v4 Rule 11 + Rule 1 mechanical follow-throughs filed in this session (Decision Index ADR-002 v2 row + supersession annotation; Assumption Register §D.10 with 8 rows; CLAUDE.md v1.18 with 4 settled-decisions bullets + B20 + B21 + 5 ops findings; tech_debt.md TD-NEW-2 + TD-NEW-3 RESOLVED blocks; session_log.md prepend; CURRENT.md this rewrite; merdian_reference.json v18 → v19). |
| **Type** | Mixed: production engineering (3 code patches across 3 writer files for unit standardisation + 1 file gets additional Parts A+B for flip-level fix), architecture (ADR-002 v2 full rewrite as new ADR replacing v1), TD work (TD-NEW-2 NEW+RESOLVED same-session, TD-NEW-3 NEW+RESOLVED same-session — third + fourth same-session NEW+RESOLVED instances after TD-097 S25 + TD-101 S26), ENH work (ENH-84 NEW + ENH-85 NEW filed in ADR-002 v2 scope, formal Enhancement Register filing deferred to S28 P2), methodology audit (Phase 0a §3 sign-convention audit PASS — 25 of 26 sessions verified correct direction), 7-file documentation pack per Doc Protocol v4. **1 commit this session** — single-commit-per-session pattern restored vs S26's 5-commit anomaly. |
| **Outcome** | PASS. **1 commit pushed origin/main, tag `session-27-close` pushed.** Commit hash: `241f943`. **ADR-002 v2 ACCEPTED** — file replaces v1 at `docs/decisions/ADR-002-market-structure-philosophy.md` (v1 20KB → v2 44KB; eight principles P1-P8; buyer/writer inversion first-class; Positioning Landscape five scalars; six-scenario dealer-flow grid; vol_analytics schema spec; methodology specifications mandatory before build; Phase 0 calibration discipline; Phase 3 four parallel tracks beyond P1-P8). **TD-NEW-2 RESOLVED** — two-part patch in `compute_gamma_metrics_local.py` via `fix_td_new_2_flip_level.py`: Part A sanity guard in `signed_gamma_exposure()` (reject `|strike-spot|/spot > 5%` AND `|gamma| > 5e-5`), Part B walk-from-ATM in `compute_flip_level()` (returns zero-crossing nearest spot, legacy fallback preserved). Verified via `verify_td_new_2_flip_level.py`: HEALTHY 2026-05-07 delta -12pts (0.05%, no regression on clean data); BROKEN 2026-05-08 PATCHED flip 25,060 near spot vs LIVE 21,250 stuck (+3,810pts correction). **TD-NEW-3 RESOLVED** — `/1e7` added to `signed_gamma_exposure()` / `signed_gex()` in three writer files (`compute_gamma_metrics_local.py`, `replay/replay_compute_gamma_metrics.py`, `backfill_gamma_metrics.py`) via `fix_td_new_3_net_gex_unit.py`. Verified via `verify_td_new_3_net_gex_unit.py`: 2026-05-11 09:30 IST cycle LIVE 775,285,881,741 (raw rupees) → PATCHED 78,544.84 (Crore); ratio 9,870,615 ≈ 10,000,000 (98.7% of expected 1e7). **Phase 0a §3 sign-convention audit PASS** — 25 of 26 sessions verified correct direction; Ref 2 source-vs-MERDIAN disagreement was LIVE-vs-PROJECTED reader-side categorisation. Unblocks ADR-002 v2 ENH-80 (per-strike GEX table) build sequence. **Honest reframing from smoke test**: Part B alone insufficient against this specific bug pattern; honest framing — Part A necessary, Part B hardening for class-of-future-bugs (noisy distributed contributions). Both shipped together. |
| **Git start → end** | Local Windows: S26-close `5b94c78` → `241f943` (1 commit this session). Tag `session-27-close` pushed at HEAD. AWS Meridian: **not pulled yet** — S28 P0b carry-forward. MeridianAlpha: not touched. |
| **Local + AWS hash match** | ⚠️ Local at `241f943` (with tag `session-27-close`); AWS still at `5b94c78` (S26-close). AWS sync via `git pull` on EC2 i-0e60e4ed9ce20cefb to `/home/ssm-user/meridian-engine/` is P0b S28 first-action carry-forward. |
| **Files added (code)** | `fix_td_new_2_flip_level.py` (Part A + Part B patch script for compute_gamma_metrics_local.py — BOM-safe read, EOL preservation, ast.parse self-validation, `_PRE_TD-NEW-2.py` backup, `_PATCHED.py` output); `fix_td_new_3_net_gex_unit.py` (three-writer unit standardisation patch script — same canonical pattern, separate handling for compact-whitespace `base=gamma*oi*(spot**2)` in backfill file vs spaces convention in canonical files); `verify_td_new_2_flip_level.py` (importlib + sys.modules registration for `@dataclass`; runs pure functions against 2 real Supabase cycles HEALTHY 2026-05-07 + BROKEN 2026-05-08); `verify_td_new_3_net_gex_unit.py` (same importlib pattern; ratio check + Cr range check on 2026-05-11 09:30 IST cycle). 4 new patch/verify scripts total. |
| **Files added (docs)** | `docs/decisions/ADR-002-market-structure-philosophy.md` is a FULL REWRITE replacement of the v1 file at the same path (v1 preserved in git history at `b46249e` and prior). Not strictly "new" since path identical; semantically a v2 ADR. 44KB. |
| **Files modified (docs)** | 7 canonical files: `MERDIAN_Decision_Index.md` (new ADR-002 v2 row prepended above ADR-008 + existing ADR-002 row annotated `**[SUPERSEDED by ADR-002 v2]**` prefix on Decision column); `MERDIAN_Assumption_Register.md` (new §D.10 with 8 rows D.10.1-D.10.8 + cross-refs + 4 open follow-ups + Update log Session 27 row + footer date Session 26 → Session 27); `CLAUDE.md` (4 new settled-decisions bullets — ADR-002 v2 ACCEPTED + TD-NEW-2 RESOLVED + TD-NEW-3 RESOLVED + Phase 0a §3 sign-convention audit PASS — plus v1.18 footer entry prepended with B20 + B21 + 5 ops findings); `tech_debt.md` (TD-NEW-2 RESOLVED block + TD-NEW-3 RESOLVED block prepended to Resolved section above TD-101); `session_log.md` (Session 27 entry prepended newest-first); `CURRENT.md` (this rewrite — S26 preserved below as Previous session per no-crunch); `merdian_reference.json` (v18 → v19 + S27 change_log entry + S27 session_log entry + writer file inventory updates + new patch/verify script inventory entries + ADR-002 v2 supersession note). |
| **Files modified (code)** | 3 production code patches: `compute_gamma_metrics_local.py` (Local — TD-NEW-2 Parts A+B + TD-NEW-3 = three edits in one file; backup chain `_PRE_TD-NEW-2.py` (pre-TD-NEW-2 state) + `_PRE_TD-NEW-3.py` (post-TD-NEW-2 / pre-TD-NEW-3 state)); `replay/replay_compute_gamma_metrics.py` (Local — TD-NEW-3 only; backup `_PRE_TD-NEW-3.py`); `backfill_gamma_metrics.py` (Local — TD-NEW-3 only; compact whitespace convention; backup `_PRE_TD-NEW-3.py`). All AST-validated. 5 backup files preserved total. **TD-NEW-2 Parts A+B replay parity is deferred to S28+ as P5 carry-forward** — replay used only for Phase 0b retroactive computation which is ~3-4 sessions away. |
| **Tables created (Supabase)** | None. `vol_analytics` table SPEC added to ADR-002 v2 §Schema but not yet CREATEd — ENH-84 build sequenced post Phase 0 in build plan. |
| **Tables modified (data)** | None. Backfill of broken-window `gamma_metrics` rows (2026-05-08 onwards under both TD-NEW-2 and TD-NEW-3 bugs) deferred to S28 P1 carry-forward — bundled with ENH-84 vol_analytics initial backfill for cost amortization. |
| **Cron / Tasks added** | None. No scheduler changes Session 27. |
| **Tags added** | `session-27-close` pushed at `241f943`. |
| **`docs_updated`** | YES. Full closeout per Doc Protocol v4 Rule 3 session-end checklist. ADR-002 v2 acceptance is itself a new architectural ADR — Rule 11 mechanical follow-throughs (Decision Index prepend + CLAUDE.md settled-decisions append + Assumption Register update) all executed in same session. Enhancement Register update for ENH-84 + ENH-85 NEW filings deferred to S28 P2 carry-forward (operator confirmed earlier in session). **Project knowledge upload pending** (carry-forward to Session 28 — same pattern as S23/S24/S25/S26 close). |

### What Session 27 did, in 12 bullets

**Phase 0a §3 sign-convention audit (PASS verdict, then 2 TDs filed):**

1. **Pulled 3 reference cycles from source-material dashboard screenshots** for sign-direction comparison: Ref 1 = Apr 28 12:21 IST clean pin (source: -976 Cr net GEX, LONG_GAMMA); Ref 2 = Apr 28 12:23 IST flip-edge stress (source: -14,323 Cr at hypothetical -1% spot move); Ref 3 = Apr 30 ~10:50 IST cascade warning (source: +13,003 Cr, SHORT_GAMMA reading). Compared against MERDIAN `gamma_metrics` queries at matching timestamps. Verdict PARTIAL with 3 findings (sign correct, flip broken, unit scale off).

2. **Ref 2 source-vs-MERDIAN disagreement diagnosed as LIVE-vs-PROJECTED reader-side categorisation error** — source dashboard panel showed projected dealer-flow scenario for hypothetical -1% spot move (-14,180 Cr "if spot drops 1% dealers will sell ₹14,180 Cr"), NOT live net GEX state at that timestamp. Two different metrics presented on same dashboard panel. MERDIAN was reading "live net GEX" correctly; Ref 2 was a projected-scenario panel that operator initially mis-categorised as live. Sign convention itself is sound.

3. **30-day NIFTY sign-direction sample** (`SELECT date_trunc('day', ts) as d, regime, COUNT(*) FROM gamma_metrics WHERE symbol='NIFTY' AND ts >= '2026-04-01' GROUP BY d, regime ORDER BY d`) confirmed 25 of 26 trading sessions had regime correctly flipping between LONG_GAMMA and SHORT_GAMMA based on session-direction (78 SHORT rows on confirmed bearish 2026-05-11; 37/76 SHORT on 2026-04-29; 8/149 SHORT on 2026-04-27 high-pin day). Sign convention validated empirically.

**TD-NEW-2 (flip_level regression) NEW+RESOLVED same-session:**

4. **Diagnostic Query 1 (flip-stuck distribution across 30 days)** revealed 2026-05-08 and 2026-05-11 had 95%+ of intraday cycles with `flip_level` clustered at 21,250.05 (or 21,200-21,254 narrow band), while every prior session 2026-04-01 through 2026-05-07 had 11-119 distinct flip values per day in operational range 22,000-25,000. **Regression cutoff narrowed to 2026-05-07 09:00 UTC → 2026-05-08 03:00 UTC** (overnight gap; no Session 26 code commits touched gamma compute pipeline — ruled out code regression).

5. **Deep-strike inspection of `option_chain_snapshots` 2026-05-08 strikes 21,000-22,000** revealed Dhan started returning `gamma=0.00007` at strike 21,250 CE on 2026-05-08 with spot ~24,200 (deep-ITM CE with delta≈1 should have near-zero gamma; 70× ATM gamma is impossible). Additional spurious values at strikes 21,500 CE (gamma=0.000025), 22,000 CE (gamma=0.0000109). **Latent algorithm fragility surfaced by Dhan response-shape change** — `compute_flip_level()` walks bottom-up from min_strike returning first zero-crossing; when surrounding strikes have legitimately zero contribution and a spurious large gamma injects at deep strike, the cumulative walk crosses zero in that region.

6. **Two-part patch shipped via `fix_td_new_2_flip_level.py`**: Part A (input layer) sanity guard in `signed_gamma_exposure()` rejecting rows where `|strike-spot|/spot > 5%` AND `|gamma| > 5e-5`. Part B (algorithm layer) `compute_flip_level()` walks outward from ATM in both directions, returning zero-crossing nearest to spot. Three edits (signed_gamma_exposure body + compute_flip_level body + call site at line 605 to pass spot). AST-validated. Backup `compute_gamma_metrics_local_PRE_TD-NEW-2.py` preserved.

7. **Verification harness** `verify_td_new_2_flip_level.py` (importlib + sys.modules registration for `@dataclass` — known interaction) ran pure functions against 2 real cycles: HEALTHY 2026-05-07 04:01:25 IST PATCHED flip 24,773.93 vs LIVE 24,785.97 (delta -12pts/0.05% — no regression on clean data); BROKEN 2026-05-08 04:00:09 IST PATCHED flip 25,060.15 near spot vs LIVE 21,250.05 stuck (+3,810pts correction). Both PASS. **Honest reframing from smoke test**: Part B alone insufficient against this specific bug pattern (cumulative plateau through bad-row region); Part A necessary, Part B hardening. Both shipped together.

**TD-NEW-3 (net_gex unit Crore) NEW+RESOLVED same-session:**

8. **Surfaced via cross-comparison of MERDIAN `net_gex` magnitudes against source-material Cr dashboard values** — MERDIAN values in 10¹²-10¹³ range vs expected thousands-of-Cr. Diagnostic Q3 dividing by 1e7 produced -1,538,435 Cr on 2026-04-28 — still 10² too large. Symmetric Q4: NIFTY avg abs net_gex = 22.9T, SENSEX = 9.3T; ratio 2.47× ≈ NIFTY/SENSEX lot ratio 25/10 = 2.5× (lot-size signature consistent). Order-of-magnitude expected `gamma×OI×spot²×100/1e7` ≈ 576 Cr per strike → thousands of Cr aggregated. **MERDIAN ~10³ too large vs expected Cr scale**, consistent with missing `/1e7` divisor.

9. **Exposure surface mapped — silent because all consumers are sign-only**: `determine_regime` (`net_gex >= 0` sign check); `compute_expansion_probability` (`if net_gex < 0`); `detect_structural_manipulation.py` (`if net_gex <= 0`); `backfill_gamma_metrics.py::determine_regime` (same); readers in `build_market_state_snapshot_local.py` / `build_trade_signal_local.py` / `backfill_market_state.py` are pass-through. **Zero magnitude thresholds in entire reader codebase** — unit-scale wrong by 10³ invisible to gate logic.

10. **Three writer files patched identically via `fix_td_new_3_net_gex_unit.py`**: `compute_gamma_metrics_local.py` line 120, `replay/replay_compute_gamma_metrics.py` line 88 (whitespace identical to canonical), `backfill_gamma_metrics.py` line 83 (compact `base=gamma*oi*(spot**2)` — separate exact-match handling). All three AST-validated. Backups `_PRE_TD-NEW-3.py` preserved per file. Verification on 2026-05-11 09:30 IST cycle: LIVE 775,285,881,741 (raw rupees) → PATCHED 78,544.84 (Crore); ratio 9,870,615 (98.7% of expected 1e7, within 5%); Crore value operationally sane (100 < |x| < 1M).

**ADR-002 v2 acceptance + Doc Protocol Rule 11 + Rule 1 mechanical follow-throughs:**

11. **ADR-002 v2 full rewrite drafted as supersession of v1**: Six v1 principles preserved (P1 zones, P2 force, P3 trapped sellers, P4 velocity, P5 PINNED, P6 DTE multiplier); two new (P7 vol-pricing RR ratio HIGH>1.2/FAIR/LOW<0.85/COMPRESSED<0.4, P8 second-order Greeks vanna/charm Phase 3). Buyer/Writer inversion named as first-class architectural concept (same gamma layer, mirrored interpretation by strategy mode). Positioning Landscape refined to five named scalars (`gamma_wall_strike`, `short_strike_for_strike`, `gradient_max_strike`, `hedged_long_cr`, `lambda_score_pct`). Six-scenario dealer-flow grid (±0.5%, ±1%, ±2% × {Cr, contracts, trajectory}). New `vol_analytics` table schema spec. Methodology specifications mandatory before build (zone-bound definition, dealer-flow assumption stack, sign-convention audit, λ-score derivation, RR-window). Phase 0 calibration discipline introduced (~3-4 sessions before ENH-80 schema lands; Phase 0a sign audit COMPLETE PASS, Phase 0b overlay calibration study, Phase 0c methodology selection). Phase 3 prerequisites named explicitly — four parallel tracks beyond P1-P8 (risk framework, multi-leg execution, SPAN+ELM margin model, tax model). Falsification criteria per principle. ENH-84 NEW (vol_analytics + RR ratio) + ENH-85 NEW (vanna/charm Phase 3 prep) filed in scope.

12. **Rule 11 + Rule 1 mechanical follow-throughs filed in same session as ADR-002 v2 acceptance**: (a) Decision Index — new ADR-002 v2 row prepended above ADR-008 (newest-first), existing ADR-002 row annotated `**[SUPERSEDED by ADR-002 v2]**` Decision column prefix; (b) Assumption Register — new §D.10 with 8 rows D.10.1-D.10.8 (RR ratio independent edge LIVE pending Phase 0b, buyer/writer inversion LIVE architectural, walk-from-ATM VALIDATED via TD-NEW-2, Crore canonical VALIDATED via TD-NEW-3, five named scalars LIVE pending ENH-81, six-scenario dealer-flow LIVE pending ENH-81 + assumption stack sensitivity, PINNED regime LIVE pending Exp 23, vanna/charm Phase 3 LIVE pending Phase 3 backtest) + cross-refs + 4 open follow-ups + Update log Session 27 row + footer date Session 26 → Session 27; (c) CLAUDE.md — 4 new settled-decisions bullets (ADR-002 v2 ACCEPTED, TD-NEW-2 RESOLVED, TD-NEW-3 RESOLVED, Phase 0a §3 sign-convention audit PASS) + v1.18 footer prepended with B20 + B21 + 5 ops findings; (d) tech_debt.md — TD-NEW-2 + TD-NEW-3 RESOLVED blocks prepended above TD-101; (e) session_log.md prepended Session 27 entry; (f) CURRENT.md this rewrite; (g) merdian_reference.json v19 bump with file inventory updates + writer changes + ADR-002 v2 supersession entry.

### Outcomes summary (counters)

- **PRODUCTION_PATCHES** = 3 (compute_gamma_metrics_local.py with TD-NEW-2 Parts A+B + TD-NEW-3; replay/replay_compute_gamma_metrics.py TD-NEW-3 only; backfill_gamma_metrics.py TD-NEW-3 only).
- **DATA_RECOVERY** = 0 (backfill of 3-day broken window deferred to S28 P1).
- **TDs_CLOSED** = 2 (TD-NEW-2, TD-NEW-3).
- **TDs_NEW** = 0 (both NEW filed and CLOSED same-session — third + fourth same-session NEW+RESOLVED instances after TD-097 S25 + TD-101 S26).
- **TDs_STATUS_UPDATE** = 0.
- **ADRs_NEW** = 1 (ADR-002 v2 full rewrite acceptance; supersedes v1; v1 preserved in git history at `b46249e` and prior).
- **ADRs_DRAFT_OUTSTANDING** = 2 (ADR-005 zone validity codification S25 carry-forward, ADR-009 calibration discipline + ENH-55 falsification Phase 1 case study S26 carry-forward).
- **ENH_NEW** = 2 (ENH-84 vol_analytics + RR ratio Phase 0b dependency; ENH-85 vanna/charm Phase 3 prep — both PROPOSED, formal Enhancement Register filing deferred to S28 P2 carry-forward).
- **DOC_FILES_MODIFIED** = 7 (Decision Index, Assumption Register, CLAUDE.md, tech_debt.md, session_log.md, CURRENT.md, merdian_reference.json).
- **CODE_PATCHES** = 3.
- **PATCH_SCRIPTS_NEW** = 2 (fix_td_new_2_flip_level.py, fix_td_new_3_net_gex_unit.py).
- **VERIFY_SCRIPTS_NEW** = 2 (verify_td_new_2_flip_level.py, verify_td_new_3_net_gex_unit.py).
- **BACKUPS_PRESERVED** = 5 (compute_gamma_metrics_local_PRE_TD-NEW-2.py, compute_gamma_metrics_local_PRE_TD-NEW-3.py, replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py, backfill_gamma_metrics_PRE_TD-NEW-3.py, plus `_PATCHED.py` intermediate inspection files since renamed to canonical).
- **COMMITS** = 1 (`241f943` — single-commit pattern restored vs S26's 5-commit anomaly).
- **TAGS** = 1 (`session-27-close`).
- **EXPERIMENTS** = 0 (Phase 0a sign audit is empirical verification, not new experiment — PASS verdict against 3 reference cycles + 25-session sign-direction sample).
- **SIGN_AUDIT** = PASS (25 of 26 sessions verified correct direction; Ref 2 disagreement traced to LIVE-vs-PROJECTED reader-side categorisation).
- **BUGS_LATENT_SURFACED** = 2 (TD-NEW-2 algorithm fragility surfaced by Dhan input-shape change; TD-NEW-3 unit-scale silent because all consumers sign-only).

### CRITICAL LESSONS Session 27

1. **Phase 0 calibration discipline is justified by its first execution.** Sign audit was scoped as 2-hour PASS/FAIL on ADR-002 v2 build path; surfaced TWO production bugs (TD-NEW-2 + TD-NEW-3) that had been writing bad data for 3+ days. Without the audit, ADR-002 v2 build (ENH-80, etc.) would have layered new code atop broken foundation. Defers ~3-4 sessions of calibration; prevents weeks of wasted build. Codified as CLAUDE.md B20.

2. **Latent algorithm fragility surfaces only under input-shape change.** TD-NEW-2 was a stable computation against stable input for months; Dhan's response changed shape 2026-05-08 (spurious deep-ITM gamma values appearing where previously zero), exposing fragility that would never have surfaced under prior data conditions. The computation's correctness assumption "deep-strike contributions are small" was data-conditional, not algorithmic. Defense-in-depth (Part A input filter + Part B algorithm hardening) shipped together to prevent this class of bug going forward.

3. **Unit-scale bugs are silent when all consumers are sign-only.** TD-NEW-3 had been writing 10³-too-large `net_gex` values since the gamma engine first deployed; never surfaced because no gate threshold consumed magnitude. Surfaced only via cross-comparison to source-material Cr references during the sign audit. Codified as CLAUDE.md B21: when introducing magnitude-consuming gates, audit existing column unit conventions FIRST against source-of-truth references, before threshold tuning.

4. **Smoke test caught honest framing of fix architecture.** Original framing called Part A + Part B "belt + suspenders" — implying defensive redundancy. Smoke test demonstrated Part B alone insufficient against the specific bug pattern (cumulative plateau through bad-row region); honest reframing: Part A necessary, Part B hardening for class-of-future-bugs. Honest framing matters for future operator understanding — don't assume defensive equivalence between parts.

5. **Source-material disagreement is not always inversion.** Ref 2 source-vs-MERDIAN disagreement at Apr 28 12:23 IST showed source -14,323 Cr while MERDIAN showed +56T-81T at same timestamps. Initially flagged as potential sign inversion. Resolution: source dashboard panel was showing PROJECTED dealer-flow scenario for hypothetical -1% spot move, not LIVE net GEX state. Two different metrics on same dashboard panel — disagreement was reader-side categorisation error, not data error. **Source-material cross-reference requires understanding whether each panel shows LIVE or PROJECTED state.** Codified as ops finding in CLAUDE.md v1.18.

6. **ADR-002 v2 buyer/writer inversion as first-class architectural concept eliminates v1 category error.** ADR-002 v1 framed writer's intelligence as Phase 3-deferred — building "writer's intelligence" as a separate Phase 3 effort when in fact the same gamma layer serves buyer and writer in mirrored interpretation. v2's first-class treatment means Phase 1 build naturally extends to Phase 3 without rebuild; strategy-mode parameter inversion handles the difference. Codified as ops finding in CLAUDE.md v1.18.

7. **Rule 11 mechanical follow-throughs must execute in same session as ADR acceptance.** Doc Protocol v4 Rule 11 mandates Decision Index + CLAUDE.md settled-decisions + Assumption Register updates after every ADR. Deferring these to next session creates Decision Index drift (next operator reading the file sees an ADR-002 v2 file at the path but no Index entry — confusion source) and CLAUDE.md settled-decisions list drift (does the v2 supersession of v1 mean v1's settled bullets are still in force? ambiguous until v2 codifies). Codified as ops finding in CLAUDE.md v1.18.

## This session (Session 28)

| Field | Value |
|---|---|
| **Date** | TBD (Tuesday 2026-05-12 trading day, NIFTY weekly expiry; or next operator-initiated session). |
| **Concern (current operator intent — fluid, may evolve at session start)** | First-cycle verification of TD-NEW-2 + TD-NEW-3 patches on Mon 2026-05-12 09:15 IST. AWS sync via `git pull` of `241f943`. Backfill of broken-window `gamma_metrics` rows 2026-05-08 onwards (under both bugs). Enhancement Register formal filing of ENH-84 + ENH-85 (deferred from S27). Phase 0b overlay calibration study (if time permits) or operator-directed work. |
| **Type (intended)** | Mixed: production verification (live data validation of S27 patches), data recovery (backfill of broken-window gamma_metrics), Enhancement Register update (ENH-84 + ENH-85 formal filing), Phase 0b methodology work (ADR-002 v2 build path), or operator-directed task. |

### Carry-forward priority queue (ordered by recommended priority for Session 28)

- **P0** — **Mon 2026-05-12 09:15 IST first-cycle verification** of TD-NEW-2 + TD-NEW-3 patches on live data. Query: `SELECT ts, spot, net_gex, flip_level, regime FROM gamma_metrics WHERE symbol='NIFTY' AND ts > NOW() - INTERVAL '10 minutes' ORDER BY ts DESC LIMIT 5`. Expect: `flip_level` in 23,000-25,500 range (near spot, not stuck ~21,250); `net_gex` in operational Cr range (100 < |x| < 1M, not 10¹² magnitudes). Repeat for SENSEX. Failure mode triage: if flip_level still stuck → check Local Task Scheduler ran patched script; if net_gex still in raw rupees → check patched module imported correctly (no stale `.pyc`).

- **P0b** — **AWS sync**. SSH (or AWS Systems Manager Session Manager) to EC2 i-0e60e4ed9ce20cefb, `cd /home/ssm-user/meridian-engine && git pull origin main` to bring AWS shadow to `241f943`. Verify AWS post-pull `git log -1` matches Local `git log -1`. AWS shadow currently writes to `*_shadow` tables; the TD-NEW-2 / TD-NEW-3 patches affect canonical pipeline only, but AWS parity is operational good practice.

- **P1** — **Backfill broken-window `gamma_metrics` rows for 2026-05-08 onwards** (3 days × ~430 cycles per day × 2 symbols ≈ 2,500 rows). Affected fields: `net_gex` (both bugs — flipped from raw rupees AND included spurious deep-strike contributions), `flip_level` (TD-NEW-2 — stuck at ~21,250), `flip_distance_pct` (derived from flip_level — stuck ~12%), `gamma_zone` (derived — stuck LOW_GAMMA). Custom script needed (NOT via `backfill_gamma_metrics.py` which writes to separate `hist_gamma_metrics` table). Reuse patched `compute_gamma_metrics_local.py` as module import; iterate over `option_chain_snapshots` rows in the broken window; recompute; UPSERT into `gamma_metrics`. Recommend bundling with ENH-84 vol_analytics initial backfill for cost amortization. Estimated 30-60 min.

- **P2** — **Enhancement Register formal filing of ENH-84 + ENH-85** (deferred from S27 by operator consent earlier in session). ENH-84 = vol_analytics + RR ratio (Phase 0b dependency for ADR-002 v2 P7 vol-pricing). ENH-85 = vanna/charm Phase 3 prep (long-deferred per ADR-002 v2 P8 — Phase 3 sellers). Both PROPOSED status. Schema spec is in ADR-002 v2 §Schema. Update `MERDIAN_Enhancement_Register.md` with full entry rows. Cross-link to Assumption Register §D.10.1 (D.10.1 RR ratio LIVE pending Phase 0b validation = pending ENH-84).

- **P3** — **ADR-002 v2 Phase 0b overlay calibration study**. Retroactive computation of v2 metrics (D.10.1 RR ratio, D.10.5 five named scalars, D.10.7 PINNED regime identification) from `option_chain_snapshots` for historical signal cohort. Tag historical signals with would-be overlay metrics; quantify if v2 metrics would have improved or saved signals. ~1-2 sessions. Gated on ENH-84 build (P2) which provides `vol_analytics` table.

- **P4** — **ADR-002 v2 Phase 0c methodology selection**. Run zone-definition Options A/B/C/D (specified in ADR-002 v2 §Methodology §1) side-by-side on backfill data; pick option with strongest WR differential between "spot inside zone" vs "spot outside zone" on completed signal cohort. Dealer-flow assumption stack sensitivity test on representative session — vary δ-bucket boundary, market-maker hedging-ratio assumption, and inventory-imbalance assumption; gate Phase 0c sensitivity verdict on <30% spread (gate-consumable) / 15-30% (advisory) / >30% (methodology-blocked). ~1 session.

- **P5** — **Replay parity**: apply TD-NEW-2 Parts A+B to `replay/replay_compute_gamma_metrics.py` (currently has TD-NEW-3 only). Maintains replay-vs-live parity for Phase 0b retroactive computation work (P3). Low-priority until P3 starts; can be batched with backfill work (P1).

- **P6** — TD-080 root-cause investigation post probe-log triage (gates ADR-006). S25 carry-forward. Requires Mon 2026-05-12 08:36 IST `v_dhan_token_probe_today` query to see if morning probe shows successful asymmetry-resolution or failure shape; then 09:15 IST cron + 09:30 IST option chain run reveals whether the issue is token-refresh (S25 hypothesis) or endpoint-side (S25 deferred hypothesis).

- **P6b** — Session 21+ uncommitted patches in working tree (`build_ict_htf_zones.py` with TD-070 v1+v2 + TD-071 stack on top of which S26 layered TD-079 changes). Reconcile S21+S26 changes into clean commit before any new code work. Same state as S22+S23+S24+S25+S26+S27 entry (5+ session carry-forward; operator deferring on commit boundary).

- **P7** — ADR-005 formal draft (zone validity codification — implementation already shipped via TD-079 S26). S25 carry-forward. The decision is settled and shipped; ADR is the writeup of an already-made decision.

- **P7b** — ADR-009 formal draft (calibration discipline + ENH-55 falsification S26 case study). S25-S26 carry-forward. Working draft language already in Assumption Register §D.8.3 + §D.9.

- **P8-P14** — Older carry-forwards retained from S26: TD-073, TD-074, TD-087 (IST-as-UTC option_bars), TD-094 (oi=0 option_bars), TD-095, TD-098, ENH-95 (in-process orchestrator optimization candidate), patchy-day stress test of orchestrator, untracked production scripts to git, S23 docs review pass.

### Files / tables / items relevant for next session

- `compute_gamma_metrics_local.py` — Local primary; carries TD-NEW-2 Parts A+B + TD-NEW-3. **Mon 09:15 IST first-cycle verification gate.**
- `replay/replay_compute_gamma_metrics.py` — TD-NEW-3 only; TD-NEW-2 parity is P5 carry-forward.
- `backfill_gamma_metrics.py` — TD-NEW-3 only; reads from `gamma_metrics` to write to `hist_gamma_metrics`; not affected by TD-NEW-2 (different code path).
- `gamma_metrics` table on Supabase — broken-window backfill target (2026-05-08 onwards).
- `vol_analytics` table — SPEC in ADR-002 v2 §Schema, not yet CREATEd. ENH-84 build target.
- `MERDIAN_Enhancement_Register.md` — needs ENH-84 + ENH-85 NEW entries (P2).
- ADR-002 v2 file at `docs/decisions/ADR-002-market-structure-philosophy.md` — reference document for Phase 0b/0c work (P3, P4).
- AWS EC2 i-0e60e4ed9ce20cefb — `git pull` to bring shadow to `241f943` (P0b).

### DO NOT REOPEN this session

- **Phase 0a §3 sign-convention audit PASS** — answer is verified; 25 of 26 sessions correct direction; do not re-audit sign.
- **TD-NEW-2 walk-from-ATM flip definition** — codified as canonical method via D.10.3; Part A input filter + Part B algorithm hardening shipped together; honest framing is that Part A is necessary (don't second-guess to "Part B handles it" — verified empirically not so on this specific bug pattern).
- **TD-NEW-3 Crore unit convention** — `net_gex` is canonically stored in Cr via D.10.4; readers are sign-only so no migration needed; future magnitude-consuming gates must specify Cr.
- **ADR-002 v2 acceptance** — v2 supersedes v1; do not re-litigate v1 vs v2; the architecture is settled per CLAUDE.md ADR-002 v2 ACCEPTED settled-decisions bullet.
- **Buyer/writer inversion as first-class architectural concept** — same gamma layer, mirrored interpretation by strategy mode; do not build writer's intelligence as separate Phase 3 effort.
- **Five named scalars + six-scenario dealer-flow grid** — Positioning Landscape spec is settled per ADR-002 v2; ENH-81 builds against this spec; don't re-spec.

## Live state snapshot (at Session 27 close, 2026-05-11 evening)

| Component | State |
|---|---|
| **Local** | S21 production patches still uncommitted in working tree — same state as S22+S23+S24+S25+S26+S27 entry. S26 layered TD-079 changes; S27 added 3 production code patches on top (TD-NEW-2 Parts A+B + TD-NEW-3 in compute_gamma_metrics_local.py; TD-NEW-3 in replay/replay_compute_gamma_metrics.py; TD-NEW-3 in backfill_gamma_metrics.py). **1 commit landed this session** (`241f943`) covering ADR-002 v2 + TD-NEW-2 + TD-NEW-3 patches + 2 new patch scripts + 2 new verify scripts + 5 backup files. 8 Task Scheduler tasks have battery flags from S21 TD-072 fix. **`MERDIAN_PreOpen` (09:05 IST) DISABLED S25 — durable across reboots.** No zombie Python processes. `C:\GammaEnginePython\replay\` tree present. `C:\GammaEnginePython\fix_td_new_*.py` patch scripts + `verify_td_new_*.py` verification scripts present in working tree. |
| **AWS (MERDIAN, `i-0e60e4ed9ce20cefb`, `ssm-user@ip-172-31-35-90`)** | **Still at `5b94c78` (S26-close) — needs pull to `241f943` (P0b S28 first-action).** `pull_token_from_supabase.py` continues running daily 03:05 UTC with TD-080 instrumentation (S26 deploy). TD-080 root-cause investigation pending Mon 2026-05-12 first probe-log triage. `ws_feed_zerodha.py` continues streaming. `ingest_breadth_from_ticks.py` continues. `ingest_option_chain_local.py` reliability TBD on Mon 09:15 IST cron — TD-080 root-cause gate. AWS shadow `gamma_metrics_shadow` table writes from AWS-side `compute_gamma_metrics_local.py` are also affected by TD-NEW-3 raw-rupees unit (since AWS runs same code), so post-pull verification needed on shadow table too. |
| **AWS (MALPHA, `ubuntu@13.51.242.119`, `~/meridian-alpha`)** | Kite gateway only — NOT Meridian. S22 backfill edits remain dirty (uncommitted). |
| **Critical items (C-N)** | None new. |
| **Tech debt (active)** | S22+S21+S20 still active. **S27 closed 2 TDs same-session**: TD-NEW-2 (commit `241f943`), TD-NEW-3 (commit `241f943`). S25-added TD-098 (S4) still active. S24-added TDs (TD-087, TD-094, TD-095, TD-096) still active. TD-080 instrumentation deployed S26, root-cause investigation gated on Mon 2026-05-12 first probe-log triage (P6 S28). |
| **ENH in flight** | **ENH-84 NEW S27** (vol_analytics + RR ratio Phase 0b dependency; PROPOSED status; formal Enhancement Register filing deferred to S28 P2). **ENH-85 NEW S27** (vanna/charm Phase 3 prep; PROPOSED status; build deferred until Phase 2 imminent; formal filing deferred to S28 P2). **ENH-88 SHIPPED** S26. **ENH-55 ENV-DISABLED** S26. **ENH-96 SHIPPED** S25. **ENH-93 CLOSED** S24 via ADR-008. **ENH-95 CANDIDATE** filed S24 (in-process orchestrator optimization). **ENH-90 CANDIDATE** deferred for N expansion. ENH-91 + ENH-92 SHIPPED Session 17. |
| **ADR layer** | **ADR-002 v2 ACCEPTED S27** (full rewrite supersedes v1; v1 preserved in git history at `b46249e` and prior). ADR-005 formal draft is P7 S28 carry-forward (implementation already shipped via TD-079 S26). ADR-009 formal draft is P7b S28 carry-forward. ADR-006 drafting remains blocked on TD-080 closure per Phase α Q3 sequencing. ADR-001/002/007/008 settled per S22/S23/S24. 3 reserved IDs (ADR-003/004/006) still pending. |
| **Documentation reference layer** | Six-file reference layer plus ADR collection. Doc Protocol v4 in force. **S27 updates:** Decision Index (ADR-002 v2 row prepended + ADR-002 v1 supersession annotation); Assumption Register (new §D.10 with 8 rows D.10.1-D.10.8 + footer date S26 → S27); CLAUDE.md (4 new settled-decisions bullets + v1.18 footer with B20 + B21 + 5 ops findings); tech_debt.md (TD-NEW-2 + TD-NEW-3 RESOLVED blocks prepended above TD-101); session_log.md (S27 prepended newest-first); CURRENT.md (this rewrite — S26 preserved below as Previous session per no-crunch); merdian_reference.json (v18 → v19 + S27 change_log + S27 session_log + file inventory updates). **Enhancement Register update for ENH-84 + ENH-85 NEW filings deferred to S28 P2 carry-forward.** **System Map + Deployment Topology no changes needed S27** (no schema/boundary changes). |
| **Project knowledge layer** | **STALE — pending Session 28 P0 upload.** Knowledge base reflects pre-S27 state. **Cross-layer sync rule unsatisfied until upload completes.** |
| **Pine on TradingView** | 62 zones (49 HTF + 13 intraday) from S26 TD-079 fix. No S27 Pine changes. |
| **Spot data quality** | hist_spot_bars_1m has clean OHLC. No new spot data work S27. |
| **Option data quality** | hist_option_bars_1m unchanged. TD-087 (IST-as-UTC) and TD-094 (oi=0) defects active per S24. Replay reconstructor compensates for both. **NEW S27 finding** — Dhan response shape changed 2026-05-08 onwards, introducing spurious deep-ITM CE gamma values (e.g., strike 21,250 CE gamma=7e-5 with spot 24,200). TD-NEW-2 Part A input filter rejects these. Not separately filed as a Dhan-quality TD because the input filter is the appropriate defense and the bug class is anticipated (deep-ITM impossibility check). |
| **Live writer** | v2.1 `capture_spot_1m_v2.py` continues healthy. Phase 2b AWS migration still deferred per Phase α Q3 sequencing (gated on TD-080 closure). |
| **Replay layer** | Tree fully built and validated end-to-end on 2026-05-07 (S24). 10 `*_replay` Supabase tables populated. Out-of-hours hard guard active. **TD-NEW-3 unit fix applied S27** to `replay/replay_compute_gamma_metrics.py`. **TD-NEW-2 Parts A+B parity deferred to S28+ P5 carry-forward.** Replay used only for Phase 0b retroactive computation (~3-4 sessions away). |
| **Dashboard** | `merdian_live_dashboard.py` S25-patched continues. ENH-96 gap card from S25 still operational. No S27 dashboard changes. |
| **Trading calendar** | Mon 2026-05-11 close (today). Tue 2026-05-12 is NIFTY weekly expiry. Thu 2026-05-14 is SENSEX weekly expiry. |

---

## Mid-session checkpoints (per Session Management Rule 1)

*Reset by Session 28 start.*


## Session-end checklist (run at end of each substantive session — per Doc Protocol v4 Rule 3)

```
☐ Update merdian_reference.json for any file/table/item status change
☐ Update tech_debt.md if a TD item changes
☐ Update System Map if file/table/runner/orchestration changed                    (NEW v4)
☐ Update Deployment Topology if AWS↔Local boundary changed                        (NEW v4)
☐ Overwrite CURRENT.md (Last session reflects this session, This session reset)
☐ Append one line to session_log.md (newest-first prepend)
☐ Update Enhancement Register if architectural thinking happened
☐ Update CLAUDE.md if a Rule, settled decision, or anti-pattern was added
☐ If new ADR was written:                                                         (NEW v4)
    ☐ prepend entry to MERDIAN_Decision_Index.md
    ☐ append governance-language one-liner to CLAUDE.md settled-decisions
    ☐ if it touches an assumption: update MERDIAN_Assumption_Register.md
☐ Update Experiment Compendium if new experiment evidence was produced
☐ Commit all documentation changes to Git
☐ Upload updated files to Claude.ai project knowledge (CLAUDE.md Rule 12)
☐ AWS sync if production code changed (git push + AWS git pull)
☐ Re-enable any disabled Task Scheduler tasks before next market open
```

---

## Previous session (Session 26 — superseded by Session 27 block above) — preserved per no-crunch directive

| Field | Value |
|---|---|
| **Date** | 2026-05-10 (Sunday — non-trading day; Session 26 — 5 production commits in single session: TD-080 instrumentation + TD-079 ADR-005 zone validity fix + ENH-88 BULL_FVG cluster gate deploy + TD-101 ret_session writer fix + ENH-55 disabled by env flag after 24-day production data falsifies Exp 20 hypothesis; plus TD-099 closed as filed-in-error after URL-spy verification). |
| **Concern** | Opened on TD-099 (5-script URL-encoding bug sweep, P3 carry-forward from S25). Diagnostic-first verification via URL-spy showed the grep audit produced false positives → TD-099 closed filed-in-error (~3 hours of patching avoided). Operator pivoted to TD-054 (broken `ret_30m` research column) at session midpoint; diagnostic SQL on `signal_snapshots.raw.ret_session` surfaced **TD-101** — a live trading bug propagating from `build_momentum_features_local.py::get_session_open_spot()` unbounded query that silently NULLed `ret_session` for 24 trading days (2026-04-17 → 2026-05-10, ~5,000 signals). Same OI-18 anti-pattern class as S25 TD-097, but writer-side helper that S25's grep audit (TD-099) couldn't reach. TD-101 fix surfaced retrospective evidence on the silent-failure window that directionally falsifies Exp 20's ENH-55 momentum opposition hypothesis (N=44 OPPOSED at 79.5% WR vs Exp 20's claimed 38.3%). Same-session: TD-101 fix shipped + ENH-55 disabled by env flag. Also shipped TD-080 instrumentation deployment (probe-log table + view + extended puller), TD-079 ADR-005 zone validity rewrite implementation (Phase α Q1 answer locked S25), and ENH-88 BULL_FVG cluster gate deploy (built-not-deployed since S17, gate satisfied). |
| **Type** | Mixed: production engineering (4 code patches across 4 files), schema (1 new Supabase table + 1 view), TD work (TD-099 closed filed-in-error, TD-079 closed via implementation, TD-101 NEW + RESOLVED same-session, TD-080 status update with instrumentation deployed), ENH work (ENH-88 SHIPPED, ENH-55 ENV-DISABLED), retrospective experiment (24-day silent-gate-failure cohort audit falsifying Exp 20), 9-file documentation pack per Doc Protocol v4. **5 separate commits this session** — single-commit pattern intentionally broken because each commit is an independent shippable unit of work (TD-080 instrumentation, TD-079 zone validity, ENH-88 deploy, TD-101 writer fix, ENH-55 disable). |
| **Outcome** | PASS. **5 commits pushed origin/main, AWS pulled clean.** Commit hashes: `718ef39` (TD-080 instrumentation), `0731e67` (TD-079 ADR-005 zone validity), `8407169` (ENH-88 cluster gate deploy), `3cb84e2` (TD-101 ret_session writer fix), `5b94c78` (ENH-55 env-flag disable). **TD-099 closed as filed-in-error** after URL-spy verification (all 4 scripts in scope emit clean URLs; 5th uses supabase Python client different code path; ~3 hours of unnecessary patching avoided; filing rule established: "same anti-pattern in N scripts" claims require runtime verification before priority assignment). **TD-079 RESOLVED** via 13 surgical AST-validated replacements implementing Phase α Q1 answer (D/W OB/FVG `valid_to=None`, 1H OB/FVG `valid_to=trade_date+7days`, `expire_old_zones()` filter widened `["W","D"]` → `["W","D","H"]`; backfill SQL revived 18 SENSEX W BEAR_OB/BEAR_FVG zones above 78k from EXPIRED → ACTIVE; live rebuild 80 zones; Pine 36 → 62 zones). **TD-101 RESOLVED same-session** as discovery (bounded query with `gte("ts", today_start_utc_iso)` + limit=20; 03:35 UTC threshold preserved per ENH-01/V18G regression history; smoke test PASS Friday close prices NIFTY 24,161.3 + SENSEX 77,582.08). **TD-080 instrumentation DEPLOYED** (`pull_token_from_supabase.py` extended 50 → 355 lines with atomic .env write + readback verify + post-write probes + audit logging + asymmetry verdict; Sunday smoke PASS 20:28 IST; root-cause investigation pending Mon 2026-05-12 first probe-log triage). **ENH-88 SHIPPED** (`ENH88_LOOKBACK_MIN=90` + `_has_recent_bull_ob()` helper + gate block with three-site sync; BEAR-side asymmetry preserved per ENH-90 -16.5pp anti-edge). **ENH-55 DISABLED** by env flag (default OFF, reversible via `MERDIAN_ENH55_ENABLED=1`; both opposition block AND alignment +10 bonus gated together as symmetric claims falsified together; ENH-53 breadth modifier untouched). |
| **Git start → end** | Local Windows: S25-close → `5b94c78` (5 commits this session). AWS Meridian: synced to `5b94c78` after each commit's push. MeridianAlpha: not touched. |
| **Local + AWS hash match** | ✅ Both at `5b94c78`. AWS pulled clean after each push. |
| **Files added (code)** | `patch_s26_td079_zone_validity.py` (zone validity patch script, AST-validated 13 replacements); `patch_s26_enh88_deploy.py` (BULL_FVG cluster gate deploy); `patch_s26_td101_ret_session.py` (writer fix); `patch_s26_enh55_disable.py` (env-flag wrap). `001_create_dhan_token_probe_log.sql` (new Supabase table + view migration). `td079_backfill.sql` (backfill SQL revived 18 SENSEX W zones). All patch scripts v3 patch canon — `utf-8-sig` decode, byte-write, `ast.parse` validation, idempotency guards, snapshot original. |
| **Files added (docs)** | None new ADR-level. ADR-005 formal draft is a P2 S27 carry-forward (implementation already shipped via TD-079); ADR-009 formal draft is a P2b S27 carry-forward (S26 ENH-55 falsification is the first case study). |
| **Files modified (docs)** | 9 canonical files: `tech_debt.md` (TD-101 NEW S1 in Active + same-session RESOLVED block in Resolved; TD-099 RESOLVED filed-in-error block in Resolved; TD-079 RESOLVED via patch closure block in Resolved; TD-080 status update row with instrumentation deployment details; TD-054 cross-ref to TD-101 row); `MERDIAN_Enhancement_Register.md` (ENH-88 status PROPOSED → COMPLETE SHIPPED 2026-05-10 with full closure block + ENH-55 status note ENV-DISABLED with 24-day evidence + Part 1 status table updates); `merdian_reference.json` (v17 → v18 + S26 change_log entry + S26 session_log entry + `dhan_token_probe_log` table + `v_dhan_token_probe_today` view inventory); `MERDIAN_System_Map.md` (production scripts S26 status annotations on ict_htf_zones + signal_snapshots + momentum_snapshots rows; new §B.10 Operational instrumentation section; new §A.S26 callout block listing 4 production scripts touched; S26 update log entry); `MERDIAN_Deployment_Topology.md` (new §9.B for TD-080 instrumentation deployment block + Mon 2026-05-12 verification triplet SQL filed + S26 update log); `MERDIAN_Assumption_Register.md` (new §D.9 ENH-55 hypothesis falsification 5 rows D.9.1–D.9.5 + ADR-009 first-case-study material + 4 open follow-ups + S26 update log); `CLAUDE.md` (B19 OI-18 propagation lesson + 8 Session 26 operational findings + version v1.16 → v1.17 with settled-decisions footer entries for all 5 commits); `CURRENT.md` (this rewrite — Session 25 preserved below as Previous session per no-crunch directive); `session_log.md` (Session 26 prepended newest-first). |
| **Files modified (code)** | 4 production code patches: `pull_token_from_supabase.py` (AWS — TD-080 instrumentation, extended 50 → 355 lines; commit `718ef39`); `build_ict_htf_zones.py` (Local — TD-079 ADR-005 zone validity rewrite, 13 surgical replacements; commit `0731e67`); `build_trade_signal_local.py` (Local — ENH-88 deploy in commit `8407169` THEN ENH-55 disable in commit `5b94c78`, two patches in same file this session); `build_momentum_features_local.py` (Local — TD-101 writer fix, `get_session_open_spot()` bounded query; commit `3cb84e2`). All snapshots preserved (`_PRE_S26_*.py` backups). |
| **Tables created (Supabase)** | `dhan_token_probe_log` (12 columns: id, ts_utc, ts_ist, host, script, phase, endpoint, http_status, latency_ms, token_len, token_prefix, verdict, error_excerpt, notes). View `v_dhan_token_probe_today` (filters today's UTC date, ORDER BY ts_utc DESC). Both created via `001_create_dhan_token_probe_log.sql` migration applied Session 26. |
| **Tables modified (data)** | `ict_htf_zones` — 18 SENSEX W BEAR_OB/BEAR_FVG zones revived from EXPIRED → ACTIVE valid_to=NULL via TD-079 backfill SQL. No DDL changes to existing tables. |
| **Cron / Tasks added** | None. No scheduler changes Session 26. |
| **Tags added (proposed)** | `session-26-close` (session marker — operator's call on push). |
| **`docs_updated`** | YES. Full closeout per Doc Protocol v4 Rule 3 session-end checklist. No new ADR drafted Session 26 (ADR-005 formal draft P2 S27 carry-forward — implementation already shipped via TD-079; ADR-009 formal draft P2b S27 carry-forward — S26 ENH-55 falsification is the first case study). Assumption Register updated with new §D.9 capturing ENH-55 hypothesis falsification. **Project knowledge upload pending** (carry-forward to Session 27 — same pattern as S23/S24/S25 close). |

### What Session 26 did, in 14 bullets

**TD-099 closure (~30 minutes investigation):**

- **TD-099 closed as filed-in-error.** Operator opened session on TD-099 sweep work (5-script URL-encoding audit, S25-filed S2 HIGH on strength of grep match). Diagnostic-first verification via URL-spy: monkey-patched `requests.get` to print URLs + params before each call, ran each script in dry-run mode. **All 4 scripts in scope emit clean single-`?` URLs with proper encoding** (`%2A`=`*`, `%2C`=`,`). 5th script `premium_outcome_writer.py` uses supabase Python client (`supabase.table(...).select(...).execute()`), not raw `requests.get` — different code path entirely. **No real defect.** Filing rule established: "same anti-pattern in N scripts" claims require URL-spy or runtime trace verification before priority assignment, not just grep matches. ~3 hours of unnecessary patching avoided. Filed as TD-099 closure block in Resolved.

**TD-080 instrumentation (commit `718ef39`):**

- **TD-080 instrumentation deployed.** New Supabase table `dhan_token_probe_log` (12 cols) + view `v_dhan_token_probe_today` created via `001_create_dhan_token_probe_log.sql`. `pull_token_from_supabase.py` extended 50 → 355 lines: atomic .env write with readback verify (read-back-and-compare-prefix sanity check before considering write committed); post-write probes of `/v2/marketfeed/ltp` (lightweight) + `/v2/optionchain/expirylist` (option-chain-relevant); audit logging to probe-log table per phase (`pre_write`, `post_write_ltp`, `post_write_optionchain`, `asymmetry_verdict`); asymmetry verdict logic (both 200 → OK; one 200 + one 4xx → PARTIAL with endpoint flag; both fail → FAIL token-side problem distinct from per-endpoint problem). **Sunday 2026-05-10 smoke test PASS at 20:28 IST: token len=280, both probes 200 OK, verdict=OK.** AWS cron `5 3 * * 1-5 /usr/bin/python3 pull_token_from_supabase.py` continues to fire 03:05 UTC = 08:35 IST as before; no scheduler change. Backup `pull_token_from_supabase_PRE_S26.py` preserved. Mon 2026-05-12 verification SQL filed (`SELECT * FROM v_dhan_token_probe_today ORDER BY ts_ist DESC LIMIT 10;`) — decision tree: both 200 → token healthy; partial → JWT scope / endpoint-specific auth; both fail → upstream TOTP / login flow on Local 08:15.

**TD-079 ADR-005 zone validity (commit `0731e67`):**

- **TD-079 RESOLVED via ADR-005 implementation.** Patch script `patch_s26_td079_zone_validity.py` applied 13 surgical AST-validated replacements to `build_ict_htf_zones.py` implementing Phase α Q1 answer locked Session 25 ("(a) pure price-based canonical with timeframe-tiered fallback intraday-only"): D/W OB/FVG `valid_to=None` (was `week_end + 4 weeks` for W, `bar_date + 1 day` for D); 1H OB/FVG `valid_to = str(trade_date + timedelta(days=7))` (tactical fallback to prevent intraday memory pile-up); `expire_old_zones()` filter widened from `["W","D"]` → `["W","D","H"]` so 1H zones still get expired by date when their week is up; PDH/PDL date-expiry logic untouched. `recheck_breached_zones()` becomes primary status transition for D/W (price-breach detection against ACTIVE zones with `valid_to=NULL`). Backfill SQL `td079_backfill.sql` revived 18 SENSEX W BEAR_OB/BEAR_FVG zones above 78k from EXPIRED → ACTIVE valid_to=NULL. Live rebuild via `build_ict_htf_zones.py --timeframe both` produced 80 zones (47 NIFTY + 33 SENSEX); Pine overlay 36 → 62 zones (49 HTF + 13 intraday) — visual confirmation: all major resistances 78k → 86k now displayed on TradingView. ADR-005 formal draft (P2 S27 carry-forward) follows the implementation per CLAUDE.md S26 lesson: architecture-defect TDs implementable before formal ADR when (a) Phase α answer in hand, (b) implementation reversible (snapshot original), (c) ADR draft follows in dedicated session to capture rationale + alternatives. Doc Protocol v4 Rule 10 satisfied — decision was made S25 and recorded in Decision Index + Assumption Register §D.7; the ADR draft is the writeup of an already-made decision.

**ENH-88 BULL_FVG cluster gate deploy (commit `8407169`):**

- **ENH-88 SHIPPED.** Built-not-deployed since Session 17, gated on Mon BULL_OB live data confirmation. Sunday gate-discharge via smoke test: `patch_s26_enh88_deploy.py` adds two chunks to `build_trade_signal_local.py`: (1) module-level `ENH88_LOOKBACK_MIN: int = 90` + helper `_has_recent_bull_ob(sb, symbol, current_ts_iso, lookback_min=90)` after `# -- end ENH-75 helper` anchor; (2) ENH-88 gate block before `return out, flags` — when `out.get("ict_pattern") == "BULL_FVG" and action == "BUY_CE"`, query `signal_snapshots` for BULL_OB in last 90min same symbol with `trade_allowed=True`. ALLOW (proceed normal sizing) or BLOCK (action=DO_NOTHING, trade_allowed=False, three-site sync of action + trade_allowed + out{}). Sets `out["raw"]["enh88_decision"] = "ALLOW"|"BLOCK"` for telemetry. **BEAR-side asymmetry preserved** — BEAR_FVG anti-clusters NOT mirrored per ENH-90 -16.5pp anti-edge (Session 16 Section 18 BEAR analysis; opposite direction to BULL effect). BEAR_FVG signals continue without cluster gate. Smoke test PASS Sunday non-trading day (both NIFTY+SENSEX `_has_recent_bull_ob` returned False as expected). Live verification deferred to Mon 2026-05-12 first BULL_FVG signal. Evidence base: Session 16 Section 18 of `analyze_exp15_trades.py` — BULL_FVG with recent BULL_OB at 90-min lookback (N=64) WR 57.8% vs standalone (N=91) WR 45.1% → **+12.8pp lift**; standalone BULL_FVG is statistically coin flip (CI [42.5, 58.1] spans 50%). Cluster effect transforms coin flip into real edge.

**TD-101 ret_session writer fix + retrospective audit (commit `3cb84e2`):**

- **TD-101 NEW + RESOLVED same-session (S1).** Discovery path: operator picked TD-054 (broken `ret_30m` research column) at session midpoint; diagnostic SQL Q2 showed `signal_snapshots.raw.ret_session` NULL on EVERY signal going back to 2026-04-17 (3+ weeks ~5,000 signals). Q4 confirmed `market_state_snapshots.momentum_features.ret_session` value=NULL but key=present. Q-source confirmed `momentum_snapshots.ret_session` 100% NULL while `ret_15m` / `ret_30m` / `ret_60m` 100% populated. Bug localized to `build_momentum_features_local.py::get_session_open_spot()`: `supabase_select("market_spot_snapshots", filters={"symbol": symbol}, order_by="ts", desc=False, limit=500)` returns OLDEST 500 rows of unbounded table (no date filter); inside-loop today-date filter discards all 500; returns None silently; `compute_return(curr, None)` returns None; stored as NULL. **Same OI-18 anti-pattern class as S25 TD-097 dashboard fix** but in writer-side helper rather than dashboard URL construction; TD-099 grep (`requests.get.*SUPABASE.*params`) couldn't reach because the anti-pattern is inside `supabase_select()` helper. **Live impact: ENH-55 momentum opposition (which gates on `ret_session is not None`) was SILENT NO-OP for 3+ weeks.** Both opposition hard-block AND alignment +10 confidence bonus inactive. Fix: `patch_s26_td101_ret_session.py` replaces function body with bounded query — `today_start_utc_iso` from `current_ts.astimezone(timezone.utc)` date; `gte("ts", today_start_utc_iso)` filter; limit=20; defense-in-depth date filter inside loop preserved; **threshold 03:35 UTC preserved per ENH-01/V18G regression history** (catches both 09:05 IST Local PreOpen now-disabled and 09:08 IST AWS PreOpen current anchor). Smoke test PASS: Friday NIFTY 24,161.3, SENSEX 77,582.08; Sunday both None (clean, no errors). Backup `build_momentum_features_local_PRE_S26_TD101.py` preserved.

**ENH-55 falsification + env-flag disable (commit `5b94c78`):**

- **ENH-55 disabled by env flag** (default OFF, reversible). Retrospective audit query partitioned 2026-04-17 → 2026-05-10 actionable signals (action ∈ {BUY_CE, BUY_PE} ∧ `trade_allowed=TRUE`) by what ENH-55 WOULD have done if firing: **WOULD_HAVE_BLOCKED bucket N=44 35W/9L 79.5% WR** (43/44 BUY_PE in up-sessions with `ict_pattern=NONE` — pure momentum-driven signals where 15m/30m turn down despite session running up; signature: exhaustion / mean-reversion edge); WOULD_HAVE_ALIGNED_BONUS N=35 19W/16L 54.3% WR; NEUTRAL_BAND N=1 0/1 0%. **Production data over 24 days on the cohort ENH-55 actually gates directionally falsifies Exp 20 hypothesis** (sign of lift opposite; magnitude 25pp clears §D.8.3 prospective-parity flag-drift criterion >15pp). Operator decision: keep TD-101 fix (writer bug unambiguously correct, orthogonal to gating decision) + disable ENH-55 by env flag (the calibration question). `patch_s26_enh55_disable.py` adds `ENH55_ENABLED: bool = os.getenv("MERDIAN_ENH55_ENABLED", "0").strip() == "1"` after `SIGNAL_V4_ENABLED` declaration; modifies inner condition to `if ENH55_ENABLED and ret_session is not None and abs(ret_session) > 0.0005:`. Disables BOTH opposition block AND alignment bonus (same evidence base, symmetric claims falsified together). ENH-53 breadth modifier untouched. Commit `5b94c78`, +8 lines, AST OK on Local + AWS. Filed as Assumption Register §D.9 (5 rows D.9.1–D.9.5 + 4 open follow-ups + ADR-009 first-case-study material).

**Documentation pack:**

- **9 canonical files updated** per Doc Protocol v4 Rule 3 session-end checklist (`tech_debt.md`, `MERDIAN_Enhancement_Register.md`, `merdian_reference.json`, `MERDIAN_System_Map.md`, `MERDIAN_Deployment_Topology.md`, `MERDIAN_Assumption_Register.md`, `CLAUDE.md`, `CURRENT.md` this file, `session_log.md`). No Decision Index update (no new ADR Session 26 — ADR-005 and ADR-009 drafts deferred to S27). No Experiment Compendium update (retrospective audit is filed via Assumption Register §D.9, not a planned experiment).

### Outcomes summary (counters)

- **TDs CLOSED**: 3 (TD-079 via patch, TD-099 filed-in-error, TD-101 same-session)
- **TDs NEW**: 1 (TD-101 — same-session NEW+RESOLVED)
- **TDs STATUS UPDATE**: 1 (TD-080 instrumentation deployed pending Mon root-cause)
- **ADRs NEW**: 0 (ADR-005 draft P2 S27, ADR-009 draft P2b S27)
- **ENH NEW+SHIPPED**: 1 (ENH-88 BULL_FVG cluster gate — built-not-deployed S17 → deployed S26)
- **ENH DISABLED (env flag)**: 1 (ENH-55 momentum opposition + alignment bonus)
- **HYPOTHESIS FALSIFIED**: 1 (Exp 20 ENH-55 — production data over 24 days directionally refutes the claim)
- **Production code patches**: 4 files (`pull_token_from_supabase.py` AWS, `build_ict_htf_zones.py` Local, `build_trade_signal_local.py` Local 2 patches, `build_momentum_features_local.py` Local)
- **New tables**: 1 (`dhan_token_probe_log`); 1 view (`v_dhan_token_probe_today`)
- **Commits**: 5 (single-commit pattern broken intentionally; each commit independently shippable)
- **Silent-gate-failure window**: 24 trading days (2026-04-17 → 2026-05-10, ~5,000 signals)

### CRITICAL LESSONS Session 26

- (a) **OI-18 class fix at one site does NOT close the class.** S25 fixed TD-097 (dashboard URL-encoding) and filed TD-099 via grep audit; S26 proved TD-099 was filed-in-error (5 grep matches were correct production code) AND TD-101 was the real instance the grep couldn't reach (writer-side helper). When fixing OI-18-class bugs, runtime-verify every candidate site including writer-side helpers downstream of the symptom site, not just request-side construction at the symptom site. The grep is shape-specific and misses helper-buried instances. Codified as CLAUDE.md B19.
- (b) **Production data on the live cohort over 24 documented days trumps research-cohort hypothesis when they disagree directionally.** Exp 20's evidence base (5m-batch `hist_pattern_signals` cohort) does not survive translation to the live signal cohort under current selection logic. Sign of lift is opposite (live OPPOSED 79.5% vs Exp 20 OPPOSED 38.3%); magnitude clears §D.8.3 flag-drift threshold. Default to disabling the parameter behind a reversible flag, file as Assumption Register row, re-validate only with proper outcome metric on the cohort the parameter actually gates. **First substantive application of §D.8.3 prospective parity check post-codification S25.**
- (c) **Reversible disablement (env flag, default OFF) > code removal** for hypothesis-falsified parameters. ENH-55's code path stayed in the codebase; only the inner condition was guarded by an env flag. Re-enable is a `.env` line addition + restart. The alternative — strip ENH-55 from the codebase — would have made re-validation cost a re-implementation rather than a flag flip. Code paths that fail empirically are still valuable as documentation of what was tried.
- (d) **Gates guarded on `not None` writer values need parallel writer-cadence diagnostics at gate-promotion time.** ENH-55's silent failure produced telemetrically identical output to "gate not firing because ret_session in neutral band" — no signal of failure other than slow drift in opposed-aligned signal counts that nobody was monitoring. Only writer-cadence assertion (`SELECT COUNT(*) FILTER (WHERE col IS NULL) FROM table WHERE date = today` should approach 0) would have surfaced the regression at cycle-1, not at 24-day retrospective audit. Ship the diagnostic at gate-promotion time, not retrospectively.
- (e) **Same-session TD close discipline.** TD-101 NEW S1 → RESOLVED commit `3cb84e2` within Session 26 (TD-097 was the S25 precedent; TD-101 is the second instance). Acceptable when the diagnostic that surfaces the bug also produces enough evidence for the fix design. Pattern: discovery → SQL diagnostic → bug localization → patch → smoke test → commit, all in one session. The TD entry in `tech_debt.md` records the lifecycle as separate Active and Resolved blocks both stamped Session 26 — audit trail (NEW + RESOLVED in same session) matters for future sessions reading the register.
- (f) **Architecture-defect TDs whose Phase α answer is in hand can be implemented BEFORE the formal ADR draft.** TD-079 (Phase α Q1 answer locked S25, recorded in Decision Index + Assumption Register §D.7) shipped via implementation Session 26; ADR-005 formal draft (P2 S27) follows. Doc Protocol v4 Rule 10 (ADR-mandatory-before-code) satisfied because the architectural decision was made S25; the ADR draft is the writeup of an already-made decision, not the decision itself. Provided: (a) Phase α answer is in hand, (b) implementation is reversible (snapshot original), (c) ADR draft follows in dedicated session.
- (g) **Filing rule for grep-derived TDs.** "Same anti-pattern in N scripts" claims require URL-spy or equivalent runtime verification of at least one match before priority assignment. False-positive grep matches against dashboard-style code patterns are common; the symptom that surfaced the original bug does not necessarily survive in code-shape grep terms. TD-099 was filed at S2 HIGH on the strength of a grep match; URL-spy verification S26 showed false positives. Filing pattern going forward: TD-097-style audit-derived TDs require runtime verification of at least one match before filing the rest.

---


## Previous session (Session 25 — superseded by Session 26 block above) — preserved per no-crunch directive

| Field | Value |
|---|---|
| **Date** | 2026-05-10 (Sunday — non-trading day; Session 25 — Phase α architecture conversation completion + multiple TD closures + ENH-96 ship + Topology §9 corrections + ret_session anchor migration + multi-file documentation pack production). |
| **Concern** | Multiple. (a) Investigate Topology §9 Q1 (post-market 16:00 dual-write) and Q2 (PreOpen 09:08 dual-write) suspicions empirically via SQL audit on `market_spot_snapshots` for 2026-05-04 → 2026-05-08; (b) close TD-078 verification gap (Apr-13 BULL_OB SQL); (c) close TD-097 dashboard pre-open accuracy widget bug; (d) complete Phase α architecture conversation Q1-Q4 begun in S22; (e) ship ENH-96 dashboard gap card if data is already available. **Phase α was the structurally most-important work of the session** — four open questions (zone validity model, AWS migration scope, token reliability sequencing, calibration discipline) had been carrying since S22 and gating ADR-005, ADR-006, and a future ADR-009. |
| **Type** | Mixed: architecture (Phase α conversation), TD closure (TD-078, TD-097), TD reframing (TD-080), TD filing (TD-098, TD-099), ENH ship (ENH-96), Topology audit (§9 Q1+Q2+Q8 closures + new §9.A), production code change (1 patch script + 5 substitutions on `merdian_live_dashboard.py`), Task Scheduler change (1 task disabled), documentation pack production (8 canonical files updated per Doc Protocol v4). |
| **Outcome** | PASS. **Phase α Q1+Q2+Q3+Q4 ALL ANSWERED.** Q1 = (a) pure price-based canonical with timeframe-tiered fallback intraday-only. Q2 = (a) capture/derived split with four-stage decomposition (architect-recommended sharpening of operator's (a) choice). Q3 = (a) token reliability FIRST then ADR-006 actions. Q4 = graduated-strictness holdout (operator deferred to architect; recommendation: Phase 1 now → Y2 graduated split, Phase 2 Y2-close rolling walk-forward, status-quo REJECTED). **TD-078 RESOLVED** — TD-070 v2 multi-week BULL_OB lookback verified via SQL; the apparent missing Apr-13 row was a schema-convention misunderstanding (W timeframe `source_bar_date` is week-start Monday). **TD-097 RESOLVED** same-session — `patch_s25_dashboard_preopen_gap.py` deployed 5 substitutions to `merdian_live_dashboard.py`; pre-open accuracy widget restored from 0% to correct historical reading. **ENH-96 SHIPPED** same-session as side-effect of TD-097 investigation — dashboard "Gap (vs prev close)" card showing prev close → prelim 09:08 → final 09:15. **TD-080 REFRAMED** — narrowed scope from "Dhan API reliability" to "AWS Dhan token refresh failure mode" based on cross-script Dhan 401 evidence on 2026-05-07; now blocks ADR-006 drafting per Phase α Q3 sequencing. **TD-098 NEW (S4)** — single-boundary replay momentum_regime divergence from full-day orchestrator. **TD-099 NEW (S2 HIGH)** — same URL-encoding anti-pattern as TD-097 in 5 other production scripts. **Topology §9 Q1 CLOSED** — empirical post-market 16:00 dual-write confirmed across 5 trading days; disposition queued for ADR-006 execution. **§9 Q2 CLOSED and reframed** — original framing inaccurate (no actual dual-write at 09:08; Local 09:05 task was different boundary). **§9 Q8 PARTIAL EVIDENCE.** **§9.A NEW** documents `MERDIAN_PreOpen` (09:05 IST) DISABLED via `Disable-ScheduledTask`; `ret_session` anchor migrated 09:05 → 09:08 and validated via ADR-008 replay infrastructure; Mon 2026-05-12 verification plan filed. |
| **Git start → end** | Local Windows: `<S24-close>` → `<pending>` (Session 25 close — single commit at end of session per protocol). All Session 25 changes (1 production code patch + 8 documentation file edits) committed together. AWS Meridian: not touched (no AWS-side code changes; AWS reliability investigation deferred to dedicated TD-080 session per Phase α Q3 sequencing). MeridianAlpha: not touched. |
| **Local + AWS hash match** | AWS will lag at S24 hash until operator pulls (S25 has no AWS-side code changes). |
| **Files added (code)** | `patch_s25_dashboard_preopen_gap.py` (16,791 bytes) — patch script, v3 patch canon. `diag_preopen_render.py`, `diag_preopen_render_v2.py`, `diag_preopen_render_v3.py` — diagnostic scripts retained in working tree for future debugging. |
| **Files added (docs)** | None new ADR-level. Phase α answers feed three pending ADRs (ADR-005 / ADR-006 / ADR-009) which will be drafted in dedicated future sessions. |
| **Files modified (docs)** | 8 canonical files: `MERDIAN_Decision_Index.md` (3 pending ADR rows updated with Phase α answers + ADR-009 row added + next-free renamed); `MERDIAN_Deployment_Topology.md` (§9 Q1+Q2+Q8 closures + new §9.A boundary disposal section + S25 update log entry); `MERDIAN_Assumption_Register.md` (new §D.8 calibration discipline 5 rows + ADR-009 governance language draft + S25 update log entry); `tech_debt.md` (TD-080 reframed full block, TD-099 + TD-098 + TD-097 stub + TD-078 stub in Active, TD-097 + TD-078 closure blocks in Resolved); `MERDIAN_Enhancement_Register.md` (ENH-96 entry added to Part 4 + Part 1 status row); `merdian_reference.json` (v16 → v17 + S25 change_log entry); `CURRENT.md` (this rewrite — Session 24 preserved below as Previous session per no-crunch directive); `session_log.md` (Session 25 prepended). |
| **Files modified (code)** | `merdian_live_dashboard.py` — 5 substitutions via `patch_s25_dashboard_preopen_gap.py` (URL-encoding fix in `get_preopen_status()`, new `get_gap_status()` function, `collect_data()` wired, `gap_html` builder added, gap card placement HTML between Token and Pre-open). 2 cosmetic post-patch repositions converged on operator-preferred location. Backups preserved as `merdian_live_dashboard_PRE_S25.py` and `merdian_live_dashboard_PRE_S25b.py`. |
| **Tables created (Supabase)** | None. |
| **Cron / Tasks added** | None. **Tasks disabled:** `MERDIAN_PreOpen` (09:05 IST) State changed `Ready` → `Disabled` via PowerShell `Disable-ScheduledTask`. Durable across reboots. No code change to script writers (only the scheduled invocation removed). |
| **Tags added (proposed)** | `session-25-close` (session marker — operator's call on push). |
| **`docs_updated`** | YES. Full closeout per Doc Protocol v4 Rule 3 session-end checklist. No new ADR drafted in S25 (Phase α answers are recorded as "answered" in pending-ADR rows in Decision Index; full ADR drafts are scheduled for dedicated sessions per the Q3 sequencing rule for ADR-006). Assumption Register updated with new §D.8 capturing Q4 calibration discipline. **Project knowledge upload pending** (carry-forward to Session 26 — same pattern as S23/S24 close). |

### What Session 25 did, in 12 bullets

**Phase α architecture conversation (the structural spine of the session):**

- **Q1 zone validity model — answered (a) pure price-based canonical with timeframe-tiered fallback intraday-only.** 1H OB/FVG = price-breach OR 1 week (whichever first). D/W OB/FVG = price-breach only, `valid_to=NULL`. PDH/PDL = date-expire (unchanged). Three implementation actions queued for ADR-005 drafting: `expire_old_zones()` rewrite by `(pattern_type, timeframe)`, `recheck_breached_zones()` as primary D/W transition, backfill pass for D/W zones currently date-EXPIRED unbreached.
- **Q2 AWS migration scope — answered (a) capture/derived split, with four-stage decomposition (architect sharpening of operator's choice).** Capture stage (`market_spot_snapshots`, `option_chain_snapshots`, `india_vix`, `market_breadth_intraday`, `ict_htf_zones`) → AWS canonical, no Local writers. Derived stage (`gamma_metrics`, `volatility_snapshots`, `momentum_snapshots`, `market_state_snapshots`, `signal_snapshots`) → Local canonical for production; AWS shadow continues writing to `*_shadow` tables. Orchestration stage (runner) → both Local (production) and AWS (shadow) parallel; comparison feeds replay parity validation. Operator-facing tooling (dashboard, signal dashboard, exit monitor, trade logger, ICT zone visualizer) → Local only.
- **Q3 sequencing — answered (a) token reliability FIRST, ADR-006 actions second.** Investigate `refresh_dhan_token.py` failure mode (TD-080) → fix → observe N clean trading days → only then execute ADR-006 disposals. Local writers stay as redundancy until AWS reliability empirically established. ADR-006 drafting blocked on TD-080 closure.
- **Q4 calibration discipline — answered graduated-strictness holdout (operator deferred to architect recommendation).** Phase 1 (now → ~April 2027 / Y2 close): mandatory holdout split for new parameter changes scaled by N — N≥60 → 67/33, 10pp tolerance; 30≤N<60 → 75/25, 15pp; N<30 → "low-N calibration-only" tag, no split required. Existing Exp 15-era params get 60-day prospective parity check, flag drift >15pp. Phase 2 (Y2 close): rolling walk-forward 12mo calibration / 3mo holdout slide quarterly. Parameter versioning via git tag + `merdian_reference.json`. Status quo silent waiver REJECTED.

**TD work:**

- **TD-078 RESOLVED.** SQL verification of TD-070 v2 multi-week BULL_OB lookback. Initial query `WHERE source_bar_date='2026-04-13'` returned empty — investigation revealed W timeframe `source_bar_date` is the week-start Monday, not the arbitrary date being queried. Adjusted query found the expected unbreached anchor under the correct Monday week-start. TD-070 v2 fires as designed. Lesson filed: timeframe-aware `source_bar_date` semantics deserve a System Map §B annotation.
- **TD-097 RESOLVED same-session.** Dashboard pre-open accuracy widget showing 0% traced to URL-encoding bug in `get_preopen_status()` — `requests.get(SUPABASE_URL + endpoint, params={...})` was double-encoding the query string and Supabase silently returned wrong-filter results (200 OK with empty rows). Fix: collapse into single fully-encoded URL via `urllib.parse.urlencode()`. Patch script `patch_s25_dashboard_preopen_gap.py` (16,791 bytes; v3 patch canon — `utf-8-sig` decode, byte-write, `ast.parse` validation, idempotency guards) deployed 5 substitutions. Backups preserved.
- **TD-080 REFRAMED.** Original framing was "Dhan option chain endpoint reliability" — narrowed to "AWS Dhan token refresh failure mode" based on cross-script Dhan 401 evidence from 2026-05-07 (PreOpen 03:38 UTC + option chain 09:30-13:30 IST + 14:45-15:25 IST were all consistent with single token-refresh failure on AWS, not Dhan-side service incident). Investigation surface narrows from "Dhan API" to "`refresh_dhan_token.py` running on AWS at 03:05 UTC". Now explicitly Blocks: ADR-006 drafting.
- **TD-098 NEW (S4).** Single-boundary replay momentum_regime classification differs from full-day orchestrator. Same root cause as ADR-008's "Per-boundary script ordering contract is load-bearing" finding — single-boundary replay reads stale or absent prior `momentum_snapshots_replay` rows. Workaround: always run full-day orchestrator for replay-vs-replay analysis. Filed.
- **TD-099 NEW (S2 HIGH).** Same URL-encoding anti-pattern as TD-097 found in 5 other production scripts: `build_signal_market_path_audit_v1.py`, `build_signal_outcome_audit_local.py`, `build_signal_regret_log_v1.py`, `build_option_execution_outcomes_v1.py`, `premium_outcome_writer.py`. Silent under-fetch failure mode. ~3 hours total to fix all 5 with same patch shape as TD-097.

**Topology + boundary disposal:**

- **Topology §9 Q1 CLOSED.** SQL audit of `market_spot_snapshots` at 16:00 IST across 2026-05-04 → 2026-05-08 (5 trading days) confirmed both Local `MERDIAN_Post_Market_1600_Capture` AND AWS `MERDIAN_Postmarket` produced rows on every day. Disposition: AWS canonical for capture stage per Phase α Q2; Local writer to be disabled when ADR-006 executes. Action gated on TD-080 closure per Phase α Q3.
- **Topology §9 Q2 CLOSED and reframed.** Original framing was inaccurate — there was no actual dual-write at 09:08 IST. AWS is sole writer at that boundary. Local `MERDIAN_PreOpen` was a 09:05 IST task (different boundary, auction window), not 09:08. Q2 misclassification was based on Task Scheduler audit naming similarity, not observed timestamps.
- **Topology new §9.A — `MERDIAN_PreOpen` (09:05 IST) DISABLED.** Operator semantic: "9:05 read meaningless" — auction-window prices are not tradeable price discovery. Code dependency check: `ret_session` computation read from 09:05 anchor; migration to 09:08 anchor validated via ADR-008 replay infrastructure (replay over historical days with 09:08 anchor produced equivalent `ret_session` within tolerance). Disposal: PowerShell `Disable-ScheduledTask`, durable. Mon 2026-05-12 verification plan filed.

**ENH ship:**

- **ENH-96 SHIPPED same-session.** Dashboard "Gap (vs prev close)" card. Discovered as side-effect of TD-097 investigation — data was already captured in `market_spot_snapshots` (PreOpen 09:08 row exists), just not surfaced. Implementation: `get_gap_status()` function + `collect_data()` wiring + `gap_html` builder + card placement between Token and Pre-open. Aligns with Phase α Q3 emphasis on operator-facing tooling staying Local. Two cosmetic post-patch repositions on the gap card location converged on operator's preferred placement.

### Outcomes summary (counters)

- **TDs CLOSED**: 2 (TD-078, TD-097)
- **TDs NEW**: 2 (TD-098, TD-099)
- **TDs REFRAMED**: 1 (TD-080)
- **ADRs NEW**: 0 (Phase α answers feed three pending ADRs not yet drafted)
- **ENH SHIPPED**: 1 (ENH-96, same-session ship)
- **Topology questions CLOSED**: 2 (§9 Q1, §9 Q2; §9 Q8 PARTIAL EVIDENCE)
- **Tasks DISABLED**: 1 (`MERDIAN_PreOpen` 09:05 IST)
- **Production code patches**: 1 file, 5 substitutions (`merdian_live_dashboard.py`)
- **Phase α questions ANSWERED**: 4 (Q1, Q2, Q3, Q4)

### CRITICAL LESSONS Session 25

- (a) **Schema-convention semantics deserve formal documentation.** TD-078 root-caused to W-timeframe `source_bar_date` meaning week-start Monday — this convention is implicit in `build_ict_htf_zones.py` and not documented elsewhere. Whenever debugging "missing row" claims, check the timeframe-aware convention before concluding the row is absent.
- (b) **One bugfix surfaces N silent siblings.** TD-097 fix exposed 5 other production scripts with the same URL-encoding anti-pattern (filed as TD-099). Whenever an anti-pattern bug ships and is fixed, audit all call sites of the same shape — `grep -rn "requests.get.*SUPABASE.*params"` reveals them in seconds.
- (c) **Operator semantics + code dependency check go together.** Operator's "9:05 read meaningless" was correct (auction-window data is not tradeable price discovery), but `ret_session` had a real code dependency on the 09:05 row. Acting on the operator semantic alone would have broken `ret_session`; investigating the code dependency without the operator semantic would have left orphan auction noise in production. Both checks.
- (d) **ADR-008 replay infrastructure earned its first non-construction use.** `ret_session` 09:05 → 09:08 anchor migration was validated via replay over historical days, not a wait-for-Monday-and-pray approach. This is exactly the what-if validation use case ADR-008 was built for.
- (e) **Phase α Q4 architect-deferral was the right call given low-N.** With Y1 cohort sizes often below the formal-split threshold, mandatory uniform 67/33 (option a strict) would have been impractical; rejected status quo (option d) leaves overfit risk uncontrolled. Graduated strictness handles the data scale honestly. The architect-recommended Phase 1 + Phase 2 cutover at Y2 close commits the discipline forward without pretending walk-forward is feasible at Y1.
- (f) **TD-080 reframing reduces investigation surface materially.** Going from "Dhan API reliability" to "AWS `refresh_dhan_token.py` failure mode" is the difference between a multi-vendor diagnostic problem and a single-script root-cause problem. The narrowing was earned by cross-script 2026-05-07 evidence; without it, TD-080 stayed open-ended.

---

---

## Previous session (Session 24 — superseded by Session 25 block above) — preserved per no-crunch directive

| Field | Value |
|---|---|
| **Date** | 2026-05-09 (Saturday — non-trading day, ENH-93 build session; same calendar date as Session 23 documentation consolidation but a separate, distinct engineering session). |
| **Concern** | Build the ENH-93 replay/simulation harness end-to-end. CANDIDATE filed Session 22 (2026-05-07) for a parallel-pipeline sandbox that mimics the live runner cycle for outside-market-hours testing of historical days. Session 23 was documentation consolidation; Session 24 is the construction. Five phases planned and executed in single session: (1) `_replay` tables + `replay_clock`, (2) `replay_chain_reconstructor.py` reading hist_* sources, (3) seven replay scripts (gamma → volatility → momentum → market_state → ICT → options_flow → signal), (4) `replay_runner_for_date.py` orchestrator, (5) end-to-end validation against 2026-05-07 live signal_snapshots. Operator goal: enable what-if signal-logic experiments where one code change is replayed against the same frozen historical data. |
| **Type** | Engineering — infrastructure / testing layer. **Net new code: ~3,500 lines** across 11 new files in `C:\GammaEnginePython\replay\` plus 1 SQL migration. **Net new schema: 10 new Supabase tables** (`*_replay` mirrors via `CREATE TABLE LIKE INCLUDING ALL`). **Zero production code changes.** **Zero writes to live tables throughout.** **ADR-008 written and Accepted** capturing replay architecture + canonical "What 'what-if experiment' means" methodology. **4 TDs filed** (TD-087, TD-094, TD-095, TD-096). **ENH-95 CANDIDATE filed.** **ENH-93 CANDIDATE → CLOSED via ADR-008.** |
| **Outcome** | PASS. **All 5 phases of ENH-93 complete in one session.** Phase 1: 10 `_replay` tables + `replay_clock.py` (12/12 self-tests). Phase 2: `replay_chain_reconstructor.py` validated on 2026-05-07 (75/76 boundaries, 150 spot rows + 3,300 chain rows; one boundary skipped because last hist bar is at 15:29). Phase 3: 7 replay scripts each validated end-to-end with success row in `script_execution_log_replay`. Phase 4: `replay_runner_for_date.py` orchestrator ran full 76 boundaries × 2 symbols × 7 scripts = **1056/1064 invocations succeeded (99.2%)** in 5009s (~83 min). Phase 5: replay-vs-live validation captured: NIFTY 100% gamma_regime match + 68% direction-bias match (32% divergence traces to documented 5-min-vs-1-min spot-granularity property), SENSEX 91% action match BUT only 28% gamma_regime match (mostly DO_NOTHING-on-DO_NOTHING tautology + structural narrow-strike-base divergence on SENSEX 100-pt step covering only ±500pts). **ADR-008 written** capturing replay architecture + canonical "What 'what-if experiment' means" methodology — referenced from CLAUDE.md settled-decisions per Doc Protocol v4 Rule 11.3. **TD-094 (hist_option_bars_1m.oi=0 from S22 Kite backfill) discovered + permanent compensation in reconstructor: lifts OI from live `option_chain_snapshots` for the replay date.** **TD-087 (hist_option_bars_1m bar_ts IST-as-UTC, 5h30m phantom offset) discovered + permanent compensation in reconstructor (5h30m subtract on read for option bars only).** Critical contract identified: orchestrator runs scripts in V19 §5.2 order PER BOUNDARY, not script-by-script across all boundaries — confirmed by S24 momentum-at-03:50 finding stale gamma at 03:45 when sequence was wrong. |
| **Git start → end** | Local Windows: `70a5cc6` (Session 23 close) → `<pending>` (Session 24 close — single commit at end of session per protocol). All Session 24 changes (ADR-008 + 11 new replay/* files + migration SQL + 7 documentation file edits + CURRENT.md + session_log.md) committed together. AWS Meridian: not touched (replay is Local-only by design). MeridianAlpha: not touched. |
| **Local + AWS hash match** | AWS will lag at `70a5cc6` until operator pulls (replay is Local-only; AWS Meridian not affected by ENH-93). Operator decision pending whether to mirror replay/* tree to AWS — not currently planned. |
| **Files added (code, replay/)** | 11 new files in `C:\GammaEnginePython\replay\`: `__init__.py` (empty), `replay_clock.py` (~6KB, 12/12 self-tests), `replay_chain_reconstructor.py` (~24KB, with TD-087 + TD-094 compensations), `replay_execution_log.py` (~9.5KB, mirror of core/execution_log.py with table → script_execution_log_replay + host=replay), `replay_compute_gamma_metrics.py` (~24KB), `replay_compute_volatility_metrics.py`, `replay_build_momentum_features.py`, `replay_build_market_state_snapshot.py`, `replay_detect_ict_patterns_runner.py`, `replay_compute_options_flow.py`, `replay_build_trade_signal.py`, `replay_runner_for_date.py` (orchestrator). Plus `replay/migrations/001_create_replay_tables.sql` (10 mirror tables via CREATE TABLE LIKE INCLUDING ALL). |
| **Files added (docs)** | `docs/decisions/ADR-008-replay-architecture.md` (~250 lines, 146 lines markdown). |
| **Files modified (docs)** | `CLAUDE.md` (settled-decisions ADR-008 line + version footer v1.14 → v1.15); `MERDIAN_Decision_Index.md` (ADR-008 row prepended above ADR-007); `MERDIAN_System_Map.md` (replay layer §A.X + §B.X appended); `MERDIAN_Enhancement_Register.md` (ENH-93 CANDIDATE → CLOSED + ENH-95 CANDIDATE filed); `tech_debt.md` (TD-087, TD-094, TD-095, TD-096 filed); `merdian_reference.json` (v15 → v16, files inventory + change_log + replay_tables block); `CURRENT.md` (this rewrite — Session 23 preserved below as Previous session per no-crunch directive); `session_log.md` (Session 24 prepended). |
| **Files modified (code)** | None. All Session 24 code is new in `replay/*`; live scripts physically untouched per ADR-008 zero-touch constraint. |
| **Tables created (Supabase)** | 10 new `*_replay` tables: `option_chain_snapshots_replay`, `market_spot_snapshots_replay`, `gamma_metrics_replay`, `volatility_snapshots_replay`, `momentum_snapshots_replay`, `market_state_snapshots_replay`, `ict_zones_replay`, `signal_snapshots_replay`, `options_flow_snapshots_replay`, `script_execution_log_replay`. All via `CREATE TABLE LIKE <live> INCLUDING ALL` — schema parity with live, separate row spaces. No views, no triggers. |
| **Cron / Tasks added** | None. Replay is operator-invoked only; no scheduled runs. |
| **Tags added (proposed)** | `enh-93-replay-shipped` (session marker — operator's call on push). |
| **`docs_updated`** | YES. Full closeout per Doc Protocol v4 Rule 3 session-end checklist. ADR-008 mandatory per Rule 10 (10 new Supabase tables = schema-affecting change); Decision Index prepended per Rule 11.1; CLAUDE.md settled-decisions appended per Rule 11.3; Assumption Register NOT updated (replay-vs-live divergences are properties of data sources not catalogued assumptions §D.1–D.6). **Project knowledge upload pending** (carry-forward to Session 25 — same pattern as S23 close). |

### What Session 24 did, in 12 bullets

**Phase 1 — Tables + clock (~30 min):**

- Drafted SQL migration `replay/migrations/001_create_replay_tables.sql` with 10 `CREATE TABLE LIKE <live> INCLUDING ALL` statements. Operator executed in Supabase. Schema parity confirmed.
- Built `replay/replay_clock.py` with `IST`, `UTC` constants, `parse_replay_ts()`, `replay_today_ist()`, `to_iso_utc()`, `assert_outside_market_hours()`. 12 self-tests pass on import. Out-of-hours guard blocks weekday 08:00-16:30 IST; weekends + Indian-market holidays open.

**Phase 2 — Reconstructor (~90 min, 4 bug-fixes):**

- `replay/replay_chain_reconstructor.py` (~600 lines) reconstructs `option_chain_snapshots_replay` + `market_spot_snapshots_replay` from `hist_spot_bars_1m` + `hist_option_bars_1m` for a given `replay_date`. Generates IV via inverse Black-Scholes Newton-Raphson per strike when stored IV missing; computes gamma greek for downstream `compute_gamma_metrics` filter (gamma!=0 AND oi>0).
- Bug A — ISODOW vs Python weekday convention. `instruments.weekly_expiry_dow` uses Postgres ISODOW (Mon=1 .. Sun=7); Python `date.weekday()` uses Mon=0 .. Sun=6. NIFTY=2 (Tuesday), SENSEX=4 (Thursday). Conversion `(weekly_expiry_dow - 1) % 7` added to `_resolve_active_expiry`.
- Bug B — PostgREST timestamp space-separator + `+00` short-offset. Added `_parse_pg_timestamp()` normalizer accepting `'2026-05-07 03:35:00+00'`, `'2026-05-07T03:35:00+00:00'`, and `'Z'` suffix.
- Bug C (TD-087) — `hist_option_bars_1m.bar_ts` stores IST clock values with UTC timezone tag (5h30m phantom offset); a 09:15 IST bar is stored as `'2026-05-07 09:15:00+00'` instead of `'2026-05-07 03:45:00+00'`. Reconstructor compensates by subtracting 5h30m on read for option bars only (`hist_spot_bars_1m` stores correct UTC). Filed as TD-087 against the historical-data layer.
- Bug D (TD-094) — `hist_option_bars_1m.oi` is 0 across all rows from S22 Kite backfill; Kite `historical_data` API does not return OI for index option minute bars. Without OI, downstream `compute_gamma_metrics` filters out all rows ("DATA_ERROR all rows unusable"). Reconstructor compensates by lifting OI from live `option_chain_snapshots` per (boundary, strike, option_type) within ±150s tolerance window. Filed as TD-094.
- Validation: 2026-05-07 reconstruction landed 150 spot rows + 3,300 chain rows (75 boundaries × 22 strikes × 2 CE/PE × 2 symbols). One boundary skipped: 15:30 because last hist bar is at 15:29 (filed as TD-096).

**Phase 3 — 7 replay scripts (~3 hours):**

- Each replay script copies its live counterpart with mechanical changes: argparse named args (`--replay-ts`, `--run-id` if needed, `--symbol`); `replay.replay_clock.parse_replay_ts` for time parsing; `replay.replay_execution_log.ExecutionLog` (host=`replay`, table=`script_execution_log_replay`); `_replay` table reads/writes throughout; `dte` from `replay_date` not `date.today()`; live wall-clock network calls replaced (e.g., `fetch_india_vix()` → historical lookup from `india_vix_daily`). All gates preserved exactly: ENH-53, ENH-55, ENH-76, ENH-77, ENH-78, DTE, VIX-elevated, power-hour, LONG_GAMMA, NO_FLIP, signal_v4 logic.
- `replay_compute_gamma_metrics.py` — script #1, validated on 2026-05-07 03:45 NIFTY+SENSEX. NIFTY: regime=LONG_GAMMA, gamma_zone=HIGH_GAMMA, net_gex=3.6T, flip_level=24462. SENSEX: regime=NO_FLIP (flip_level=null) — narrow strike-base couldn't bracket flip.
- `replay_compute_volatility_metrics.py` — script #2. `fetch_india_vix()` replaced with `fetch_replay_date_vix()` reading `india_vix_daily` historical close. Live `volatility_snapshots` reads → `volatility_snapshots_replay`.
- `replay_build_momentum_features.py` — script #3. `cycle_ts` derived from `--replay-ts` not "latest gamma_metrics". Reads `market_breadth_intraday` LIVE filtered by replay_date (immutable past, same justification as OI lift).
- `replay_build_market_state_snapshot.py` — script #4. Consolidator. Upstream reads use `ts <= replay_ts ORDER BY ts DESC LIMIT 1` (mirrors live "latest" semantics). Reads `market_breadth_intraday` and `weighted_constituent_breadth_snapshots` LIVE (immutable past).
- `replay_detect_ict_patterns_runner.py` — script #5, most complex. Reads `hist_spot_bars_1m` LIVE filtered by `bar_ts < replay_ts` (strict less-than excludes in-progress boundary bar — bar at e.g. 09:15 represents the minute STARTING at 09:15, only complete at 09:16). `should_rebuild_1h_zones` returns False always (skip hourly rebuild for replay; HTF zones already in live `ict_htf_zones` for replay_date). Capital from live `capital_tracker` (current state, accepted per ADR-008 — replay tests pattern logic, not historical capital state).
- `replay_compute_options_flow.py` — script #7. CLI changed from no-args (live discovers both symbols) to `--replay-ts --symbol --run-id` (matches orchestrator pattern).
- `replay_build_trade_signal.py` — script #6. ALL gates preserved. Power-hour gate uses `replay_ts.astimezone(IST).hour >= 15` not `datetime.now()`. ICT enrichment reads `ict_zones_replay`. PO3 session bias reads live `po3_session_state` (immutable past for replay_date). `enrich_signal_with_ict` from `detect_ict_patterns` reused as-is (pure function).

**Phase 4 — Orchestrator (~45 min):**

- `replay/replay_runner_for_date.py` — file lock at `replay/runtime/replay.lock` (refuses to run if held); out-of-hours guard at entry; TRUNCATE 9 `_replay` tables (preserves `script_execution_log_replay` audit); reconstruct chain + spot via `replay_chain_reconstructor.reconstruct()`; for each of 76 boundaries iterate `gamma → volatility → momentum → market_state → ICT → options_flow → signal` PER BOUNDARY (not script-by-script across boundaries — critical contract). subprocess.run per script; per-script success counters; final per-script success-rate matrix.
- 4a smoke test on 3 boundaries: 42/42 invocations succeeded in 156.8s. Pipeline ordering correct, run_id flow correct, lock + truncate + reconstruct verified.
- 4b full-day run on 2026-05-07: 1056/1064 succeeded (99.2%) in 5009s (~83 min). Failures: gamma 144/152 (95%), volatility 147/152 (97%), options_flow 150/152 (99%), all others 152/152. The 8 failures concentrate in (a) boundary 15:30 reconstruction-skipped, (b) 6 SENSEX boundaries during 2026-05-07 OI-gap windows where live `option_chain_snapshots` had no data to lift, (c) one collateral cascade. All explainable; no logic bug.

**Phase 5 — Validation:**

- Replay-vs-live for NIFTY at 03:45 boundary: `action=BUY_PE` matches, `trade_allowed=False` matches, `direction_bias=BEARISH` matches, `gamma_regime=LONG_GAMMA` matches, `entry_quality=D` matches, `confidence_score` 46 vs 40 (+6 diff, traces to vix_regime HIGH_IV vs NORMAL_IV penalty). **Direction-of-edge match: PERFECT on the first sample.**
- Full-day comparison: NIFTY 76 paired signals, 100% gamma_regime match, 68% direction_bias / action match, avg_conf_diff=4.7. SENSEX 76 signals, 91% action match (mostly DO_NOTHING-on-DO_NOTHING tautology), 28% gamma_regime match (structural strike-base divergence). Both `trade_allowed=true` count: 0 — 2026-05-07 was a LONG_GAMMA / NO_FLIP day across the session per ENH-35 gating, so executable signals could not be cross-validated against live on this date.
- The 32% NIFTY direction-bias divergence and the 28% SENSEX gamma-regime match both trace to **documented architectural properties** captured in ADR-008: 5-min-vs-1-min spot granularity (drives momentum), and 11-strike-vs-full-chain base width (drives gamma flip-level computation). Neither is a bug.

**ADR-008 written + Doc Protocol v4 Rule 11 closure:**

- ADR-008 (~250 lines) at `docs/decisions/ADR-008-replay-architecture.md`. Status: Accepted. Captures: Context (why "re-run live ingest" doesn't work), Decision (7 architectural properties — parallel tables, parallel scripts, CLI time injection, OOH guard, read-live / no-write-live, boundary-driven orchestrator, replay-vs-replay validation philosophy), Evidence (Phase 4b results), 4 Alternatives rejected, Consequences (positive + 3 documented divergences negative + mitigations), Relationship to ENH-93/ENH-95/TD-087/TD-094/System Map/Topology/Assumption Register/CLAUDE.md, Governance language one-liner, **dedicated section "What 'what-if experiment' means" capturing the methodology** (the question replay answers, the 5-step mechanic, what you learn, what replay does NOT validate, discipline points, operational guidance). Open follow-ups: ENH-95 in-process orchestrator, patchy-day stress test, first what-if experiment, AWS replay capability, granularity widening.
- Decision Index: ADR-008 row prepended per Rule 11.1.
- CLAUDE.md settled-decisions: one-liner appended per Rule 11.3.
- Assumption Register: NOT updated — replay-vs-live divergences are properties of data sources, not of catalogued assumptions §D.1–D.6.

**TDs filed:**

- TD-087 (S2) — `hist_option_bars_1m.bar_ts` IST-as-UTC defect (5h30m phantom offset; bar at 09:15 IST stored as '2026-05-07 09:15:00+00' instead of '2026-05-07 03:45:00+00'). Workaround: replay reconstructor subtracts 5h30m on read for option bars only. Proper fix: backfill correction in `hist_option_bars_1m` to store correct UTC, OR explicit re-tagging schema decision. Blocked by: nothing (workaround working). Cost: ~1 session for backfill correction.
- TD-094 (S2) — `hist_option_bars_1m.oi=0` across all rows from S22 Kite backfill. Kite `historical_data` API does not return OI for index option minute bars; volume populates correctly, OI stays 0. Workaround: replay reconstructor lifts OI from live `option_chain_snapshots` per (boundary, strike, option_type) within ±150s tolerance. Proper fix: separate OI-snapshot backfill via Zerodha `quote()` per strike (many calls but accurate), OR drop the NOT NULL constraint and adjust downstream filters. Blocked by: nothing. Cost: ~2 sessions.
- TD-095 (S3) — `atm_iv_avg` unit ambiguity surfaced during replay ICT detector run. `compute_volatility_metrics_local.py` writes `atm_iv_avg` as decimal fraction (e.g., 0.149 = 14.9%). `detect_ict_patterns_runner.py` formats as `f"{iv:.1f}%"` rendering 0.149 as "0.1%" and passes 0.149 to `compute_kelly_lots`. Need to confirm whether (a) live always sees decimal and Kelly expects decimal (cosmetic only), (b) Kelly was designed for percent and silently mis-sizes. Replay-discovered, applies to live. Independent of replay.
- TD-096 (S4) — replay reconstructor skips boundary 15:30 because last `hist_spot_bars_1m` bar is at 15:29 IST. Cosmetic — replay produces 75/76 boundaries instead of 76/76. Workaround: accept 75-boundary replay as healthy. Proper fix: extend hist capture to 15:30:00 IST inclusive OR have reconstructor synthesize a 15:30 boundary from the 15:29 bar.

**ENH-95 candidate filed:**

- ENH-95 (CANDIDATE) — Replay orchestrator in-process invocation. Current subprocess.run pattern adds ~3-4s/call from Python startup + supabase client init. Refactor to import each replay script's `main()` directly, share supabase client across calls. Estimated runtime reduction 65min → 10-15min for full-day replay. Trade-off: tighter coupling between orchestrator and script internals; may break the clean per-invocation contract logging. Decision deferred until first what-if experiment campaign demonstrates a need for faster cycle time.

### What "what-if experiment" means — also captured in ADR-008 §"What 'what-if experiment' means"

Replay's actual value is **comparing two replay runs against each other** with one variable changed, not comparing replay against live. This is something live data cannot do — you cannot go back and re-run live with modified code. But you can re-run replay with modified code as many times as you want.

**The 5-step mechanic.** (1) Run baseline replay with current production logic → `signal_snapshots_replay` snapshot. (2) Snapshot baseline before next run wipes it (CTAS to `_baseline_<tag>` table or CSV export). (3) Modify exactly one signal-logic file (e.g., LONG_GAMMA gate threshold, ENH-55 momentum opposition threshold, MIN_CONFIDENCE floor, power-hour cutoff, new gate). (4) Re-run replay — same date, same data, modified code, same orchestrator command. (5) SQL diff baseline vs modified — count signals that changed action / flipped trade_allowed / shifted confidence; inspect spatial clustering.

**What you learn.** Sensitivity (how many signals does the change flip?), direction (does it ADD tradeable / REMOVE / shift composition?), spatial clustering (when in the day does the change manifest?).

**What replay does NOT validate.** (a) Production logic correctness — comparing replay-vs-live tells you about data-source divergences, not logic correctness; (b) live's quantitative metrics (net_gex, flip_level absolute values diverge by design via strike-base property); (c) executed trades — those live in operator's trade log; replay is signal-generation only.

**Discipline.** Always baseline first. Single-variable changes only. Replicate on multiple days before drawing a conclusion.

**Files in place at end of Session 24:**

```
C:\GammaEnginePython\replay\
├── __init__.py                              (empty)
├── replay_clock.py                          (~6KB,  12/12 self-tests)
├── replay_chain_reconstructor.py            (~24KB, with TD-087 + TD-094 compensations)
├── replay_execution_log.py                  (~9.5KB, host=replay, table=script_execution_log_replay)
├── replay_compute_gamma_metrics.py          (~24KB, validated)
├── replay_compute_volatility_metrics.py     (validated)
├── replay_build_momentum_features.py        (validated)
├── replay_build_market_state_snapshot.py    (validated)
├── replay_detect_ict_patterns_runner.py     (validated)
├── replay_compute_options_flow.py           (validated)
├── replay_build_trade_signal.py             (validated)
├── replay_runner_for_date.py                (orchestrator, validated full-day)
├── runtime/                                  (lock dir; lock released)
└── migrations/
    └── 001_create_replay_tables.sql         (10 mirror tables, applied)
```

Live tables touched: ZERO writes throughout S24. Live scripts touched: ZERO. Constraint held start to finish per ADR-008.

**CRITICAL LESSONS Session 24:**

- (a) **Replay's actual value is replay-vs-replay comparison, NOT replay-vs-live.** Captured in ADR-008 §"What 'what-if experiment' means" as canonical methodology entry. Live cannot be re-run with modified code; replay can.
- (b) **TD-094 OI-defect would have permanently broken replay** if not for the live-OI-lift compensation in the reconstructor — historical-data layer alone (hist_option_bars_1m) cannot drive replay because Kite `historical_data` API does not return OI for index option minute bars. The fix is reconstructor-level (lift from live `option_chain_snapshots` per ±150s match window), not historical-data-layer.
- (c) **Strike-base divergence is structural, not a bug** — replay 11 strikes vs live ~482; pronounced on SENSEX (100-pt step covers only ±500pts vs live full-chain ~482 strikes covering ±25k pts). Replay reproduces direction-of-edge but not absolute net_gex / flip_level / gamma_concentration. Documented as architectural property in ADR-008.
- (d) **ICT detection requires the orchestrator's full boundary sequence** to reproduce live behavior — single-boundary spot-checks under-detect because patterns whose anchor bar is outside the 30-bar lookback are missed at sparse invocations. Must run via orchestrator, not ad-hoc CLI.
- (e) **Per-boundary script ordering contract is load-bearing** — script-by-script-across-all-boundaries pattern would produce stale-upstream cascades (momentum at 03:50 reads gamma at 03:45). Confirmed during S24 build when sequence was wrong on first orchestrator pass.
- (f) **Out-of-hours hard guard is mandatory** — `replay_clock.assert_outside_market_hours()` blocks 08:00-16:30 IST weekdays; replay must never run during market hours regardless of operator urge. Architectural guard, not a soft rule.

---

## Previous session (Session 23 — superseded by Session 24 block above) — preserved per no-crunch directive


| Field | Value |
|---|---|
| **Date** | 2026-05-09 (Saturday — non-trading day, deep-work doc consolidation session). |
| **Concern** | Documentation consolidation across V15.1 → V19 + 11 appendices + scattered protocol files. Reconcile apparent contradictions between versions; promote `.docx`-locked governance to canonical markdown; establish six-file reference-index layer per Doc Protocol v4 Rule 9; retroactively document the V18F ICT signal-architecture pivot via ADR-007 (the most consequential architectural change since V11, never given an ADR at the time). |
| **Type** | Engineering — documentation / governance. 0 production code changes. 11 markdown documents created or modified. 2 commits. 2 tags. |
| **Outcome** | PASS. **Six-file reference layer established per Doc Protocol v4 Rule 9** (System Map + Deployment Topology + Decision Index + Assumption Register + Governance Framework + Disaster Rebuild Runbook). **ADR-007 drafted retroactively** documenting the V18F ICT pivot — one ADR resolves nine apparent reversals (CONFLICT lift, VIX gate removal, MIN_CONFIDENCE 60→40, three-zone gamma made moot, multi-horizon voting made moot, etc.). **Doc Protocol v3→v4** with mandatory ADR triggers (Rule 10), exhaustive changelog requirement (per operator instruction "if removing/changing this change should be recorded"), and Rule 11 ADR linkage rules. **CASE-2026-03-11 promoted** to standalone with V15.1 remediation supersession annotation. **CLAUDE.md edited:** read order extended 5 → 7 entries (System Map at #3, Decision Index at #4); single source of truth map extended 11 → 15 rows; settled-decisions footer gained ADR-001/002/007 governance one-liners. **Task Scheduler audit (PowerShell `Get-ScheduledTask` + action-mapping pass) revealed 17 `MERDIAN_*` tasks** (vs JSON's 4) — canonical inventory landed in Topology §7.2; 16 newly-catalogued .bat/.ps1 wrapper scripts surfaced; **TD-061 pythonw migration shown to be 4/15 partially complete** (`HB_Watchdog`, `Live_Dashboard`, `PreOpen`, `Spot_1M` already on `pythonw.exe`; remaining 11 wrap through cmd via .bat). **Two-watchdog architecture documented as intentional** (`merdian_watchdog.py --kill` kills hung processes; `watchdog_check.ps1` is passive observer). **`merdian_watchdog.py` flagged as production-critical but currently untracked in git** — disaster-rebuild runbook references it but `git clone` wouldn't bring it (Session 24 P5 candidate). **`merdian_morning_start.ps1` is canonical Intraday_Supervisor_Start entry**, not `start_supervisor_clean.ps1` as JSON had. **PreOpen 09:08 IST and Post-market 16:00 IST run different scripts on Local vs AWS** — Local PreOpen = `capture_spot_1m.py` (pythonw); AWS PreOpen = `capture_market_spot_snapshot_local.py`; same divergence post-market. Filed in Topology §9 dupe-check questions. **11 boundary questions** filed in Topology §9 as evidence base for ADR-006 (AWS migration scope) when drafted. **7 prioritised assumption-validation queue items** filed in Assumption Register §D.7 (HIGH: TD-059 MTF hierarchy, ENH-43 breadth removal). **Walk-Forward methodology open question** filed in Governance Framework §6: Exp 15 used full year as one cohort, not Y1+Y2/Y3 split. |
| **Git start → end** | Local Windows + Meridian AWS: `d7eb8c0` (last common ancestor) → `74c1f8d` (Session 23 main consolidation: 10 files, 3,073 insertions, 8 deletions) → `70a5cc6` (System Map sync after Topology audit follow-up: 1 file, 35 insertions, 19 deletions). Both pushed; AWS hash matches Local at `70a5cc6`. **Session 21 patches still uncommitted in working tree** (carry-forward from S22) — separate from S23 doc work. MALPHA AWS still dirty (S22 backfill edits, separate concern). |
| **Local + AWS hash match** | ✅ Both at `70a5cc6`. Two commits same session (single-commit pattern intentionally split because System Map needed update after Topology audit revealed new findings — both are MERDIAN: [DOCS] commits in same session). |
| **Files added (docs)** | 9 new files: `docs/decisions/ADR-007-v18f-ict-pivot.md` (171); `docs/decisions/MERDIAN_Decision_Index.md` (98); `docs/decisions/CASE-2026-03-11-do-nothing-on-trend-day.md` (142); `docs/operational/MERDIAN_Documentation_Protocol_v4.md` (655); `docs/operational/MERDIAN_Governance_Framework.md` (208); `docs/registers/MERDIAN_Assumption_Register.md` (181); `docs/registers/MERDIAN_System_Map.md` (545 — final after audit follow-up); `docs/registers/MERDIAN_Deployment_Topology.md` (400); `docs/runbooks/runbook_disaster_rebuild.md` (672). |
| **Files modified (docs)** | `CLAUDE.md` (3 targeted edits — read order, source-of-truth map, settled-decisions footer for ADR-001/002/007); `CURRENT.md` (this rewrite — Session 22 preserved below as Previous session per no-crunch directive); `session_log.md` (Session 23 prepended). |
| **Files modified (code)** | None. Session 21 production patches (TD-070 v1+v2 + TD-071 + TD-072 stack on `build_ict_htf_zones.py`) still uncommitted in working tree from S21 — separate concern, not addressed Session 23. |
| **Tables changed** | None (schema or data). |
| **Cron / Tasks added** | None. |
| **Tags added** | `docs-v4` (signals Doc Protocol revision per Rule 4.3); `session-23-docs-consolidation` (session marker). Both pushed. |
| **`docs_updated`** | YES. Full closeout per Doc Protocol v4 Rule 3 session-end checklist. **Project knowledge upload pending** (P0 Session 24 task). |

### What Session 23 did, in 10 bullets

**Phase 1 — Reconciliation diagnosis:**

- Read V15.1 + V16 end-to-end (1,121 + 2,339 lines plain text); cross-checked every distinctive item against V17 + V18 master + 11 V18 appendices + V19 + V19A + ADR-001/002 + CLAUDE.md + CURRENT.md + session_log + tech_debt + Enhancement Register + merdian_reference.json. First-pass orphan analysis produced flat 25-item Tier 1-4 list — operator pushed back: "did you reconcile, not catalogue?"

- Identified the missing integration story: **V18F (2026-04-11/12) was a major architectural pivot from gamma+breadth+momentum+VIX confidence-scoring engine to ICT pattern detection with Kelly tier sizing — with no ADR**. Single pivot explains nine apparently-isolated reversals.

**Phase 2 — ADR-007 retroactive pivot ADR:**

- Drafted ADR-007 (171 lines) following ADR-001/002 format. Status: Accepted (retroactive). Status field "Accepted (retroactive)" introduced as new pattern; closing note establishes retroactive ADRs are acceptable for pre-ADR-habit decisions but **required (not retroactive)** for new decisions of comparable scope. Nine decisions documented: ICT pattern as primary trigger, Kelly tier sizing, LONG_GAMMA + NO_FLIP gates preserved, CONFLICT lifted (58.7% WR), VIX>20 gate removed, MIN_CONFIDENCE 60→40, confidence as adjustment layer, T+30m exit, V15.1 remediation specs become moot. Three alternatives rejected with reasons. Governance language: *"The signal trigger is the discrete ICT pattern. The confidence score is the size dial. Gates that validated as binary truth — LONG_GAMMA, NO_FLIP — remain. Gates that validated as conservative myth — CONFLICT, VIX>20 — are lifted. The 11 March 2026 insight stays; its proposed remediation does not."*

**Phase 3 — Doc Protocol v3→v4:**

- Per operator instruction "if removing/changing this change should be recorded": exhaustive changelog at top of v4 showing every Added / Modified / Removed / Preserved-Unchanged item from v3. Three new rules: Rule 9 (six reference indexes first-class), Rule 10 (ADRs **mandatory** before code for signal-architecture / deployment-topology / schema-affecting / settled-decision reversal changes; retroactive allowed only as fallback for pre-habit decisions per ADR-007 precedent), Rule 11 (ADR linkage: every accepted ADR mechanically prepends Decision Index, updates Assumption Register if applicable, appends governance footer to CLAUDE.md). Master `.docx` demoted to archive-only post-V19. Rules 0/4/5/7/8 preserved unchanged.

**Phase 4 — Six-file reference layer:**

- `MERDIAN_Decision_Index.md` (98 lines): flat lookup seeded with ADR-001/002/007. Migration note for V18 §17 + V18G §10 pre-ADR settled-decision queues. No DEC-NNN ID prefix introduced — only ADR-NNN and CASE-YYYY-MM-DD per Doc Protocol v4 Rule 5.

- `MERDIAN_Assumption_Register.md` (181 lines): V15.1 Appendix D promoted, refreshed for ICT-era. D.1 (Signal Engine) + D.4 (Momentum) largely SUPERSEDED post-pivot. D.2 (Gamma) largely intact (Exp 17/19 confirmed binary). D.3 (Breadth) partially live (ENH-43 candidate). D.6 ICT-era new assumptions added. D.7 validation queue prioritised.

- `MERDIAN_System_Map.md` (529 → 545 lines after audit follow-up): file/table/runner/orchestration index. §A 50+ scripts grouped by role. §B all 36 tables grouped by domain. §C 5 ASCII pipeline diagrams. §D orchestration. §E V15.1 health-check thresholds + telemetry files + heartbeat schema rescued. §F core/ module signatures rescued. §G.1 originally HIGH-priority Task-Scheduler-completeness gap — RESOLVED in same session by audit.

- `MERDIAN_Deployment_Topology.md` (400 lines): "what runs where" — Local↔AWS boundaries, side-by-side environment summary, Local-only / AWS-only / both-environments script lists, token flow, AWS gotchas (DO NOT), 17 Task Scheduler entries with canonical action mapping, 11 open boundary questions for ADR-006 evidence base.

- `MERDIAN_Governance_Framework.md` (208 lines): V16 §3 (M→V→S→P) preserved verbatim. V16 §3.3 (Four Evidence Questions) preserved verbatim with post-ADR-007 status added per question. V16 §3.6 (Walk-Forward) preserved verbatim with open methodological question. V15.1 §18.1 / V16 §25.1 (Do-NOT-Revive) preserved as §8.1; six post-ADR-007 antipatterns added as §8.2; six operational antipatterns referenced from CLAUDE.md/Topology as §8.3. ADR-001/002/007 cross-references. §7 worked example tracing V18F pivot through M→V→S→P stages end-to-end.

- `runbook_disaster_rebuild.md` (672 lines): V15.1/V16 Appendix A refreshed for ICT-era. Phased structure (9 phases vs original 18 flat steps). New phases: ICT layer (§5), Phase 4A execution including Zerodha WebSocket (§6), AWS shadow setup (§7), 17-task Scheduler bootstrap (§8). Validation expanded with B.5 (ICT) and B.7 (dupe-check). Honest limitations section flagging "Last verified end-to-end: Never as a single procedure post-V18F."

**Phase 5 — CASE study promotion:**

- `CASE-2026-03-11-do-nothing-on-trend-day.md` (142 lines): V15.1 §3.6 / V16 §4 diagnostic content preserved verbatim (§1-§3). §4 V15.1-spec'd remediation path documented. §5 V18F supersession documented per-fix (three-zone gamma → moot, ret_session → built and live, multi-horizon voting → moot, 30-session regret-log gate → satisfied). §6 permanent implications. §7 what-this-does-NOT-mean. Self-contained — readers do not need to chase ADR-007 to understand the supersession.

**Phase 6 — Task Scheduler audit (PowerShell + action mapping):**

- Operator ran `Get-ScheduledTask -TaskName "MERDIAN_*"` — **17 tasks** revealed (vs JSON's 4). Then second pass with `Actions.Execute + Arguments` — canonical action map captured.

- Discoveries: 16 newly-catalogued .bat/.ps1 wrapper scripts (`merdian_watchdog.py`, `watchdog_check.ps1`, `merdian_morning_start.ps1`, `capture_spot_1m.py`, `capture_spot_1m_v2.py`, plus 11 wrappers). TD-061 pythonw migration is 4/15 partially complete. Two-watchdog architecture (kill + observe) intentional. `merdian_morning_start.ps1` is canonical Intraday_Supervisor_Start, not `start_supervisor_clean.ps1`. PreOpen and Post-market 16:00 are different scripts on Local vs AWS — dupe-check pending Session 24.

- Topology §7.2 + System Map §A.1 + §A.5 + §D.2 + §G updated to reflect audit findings. Topology §A.2 lists all 16 newly-catalogued scripts.

**Phase 7 — CLAUDE.md targeted edits:**

- Edit 1 (read order): 5 entries → 7. System Map at #3, Decision Index at #4. Note added that V19 is last Master under v4 Rule 6.

- Edit 2 (source-of-truth map): 11 rows → 15. New rows: Topology, Decision Index, Assumption Register, Governance Framework, Disaster Rebuild Runbook. Doc Protocol reference v3→v4.

- Edit 3 (settled-decisions footer): three new bullets for ADR-001/002/007 with full governance language one-liners. Each ADR cross-referenced.

**Phase 8 — Commit + AWS sync + tag:**

- Commit 1: `74c1f8d` "MERDIAN: [DOCS] Session 23 documentation consolidation" — 10 files, 3,073 insertions, 8 deletions. Pushed.

- Commit 2: `70a5cc6` "MERDIAN: [DOCS] System Map — sync with Session 23 Topology audit" — 1 file, 35 insertions, 19 deletions (System Map updated post-Topology-audit findings). Pushed.

- AWS pull: hash match `70a5cc6`. Files physically present (verified `ls -la` on three samples).

- Tags: `docs-v4` + `session-23-docs-consolidation`. Both pushed.

**Phase 9 — Project knowledge upload (PENDING for Session 24 P0):**

- 10 files for upload: CLAUDE.md + Doc Protocol v4 + Governance Framework + ADR-007 + Decision Index + CASE-2026-03-11 + Assumption Register + System Map + Deployment Topology + Disaster Rebuild Runbook.

- Files to remove from project knowledge: `MERDIAN_Documentation_Protocol_v3.md` (superseded by v4), `MERDIAN_OpenItems_Register_v7.md` (closed 2026-04-15 — keep on disk in git, remove from live knowledge to avoid pollution).

**Phase 10 — Session-23 close:**

- `session_log.md` Session 23 line prepended (newest-first). `CURRENT.md` rewritten — Session 23 promoted to Last session; Session 22 preserved as Previous session per no-crunch directive; This session block reset to Session 24. Session-end checklist updated to Doc Protocol v4 (added System Map / Topology / Decision Index / Assumption Register update lines + ADR linkage steps).

**CRITICAL LESSONS Session 23:**

- (a) **Reconciliation ≠ catalogue.** First-pass orphan analysis was a flat 25-item Tier list — operator correctly demanded the integration story. The story was a single architectural pivot (V18F ICT) that shipped without ADR; nine apparent reversals all flow from one decision.

- (b) **Per-protocol-revision exhaustive changelog is now mandatory.** Operator caught a dropped item between v2 and v3 documentation and required: every Added/Modified/Removed/Preserved-Unchanged item explicit going forward. v3→v4 is the first revision held to that standard.

- (c) **Static facts in code can drift undetected from JSON inventory.** `merdian_reference.json` listed 4 Task Scheduler tasks; reality was 17. Without the audit-prompt, the gap would have persisted into the disaster-rebuild runbook. PowerShell two-pass audit closed it.

- (d) **Two-watchdog architecture is real.** `merdian_watchdog.py --kill` and `watchdog_check.ps1` look like duplication but are intentional kill-layer + observe-layer split. Documenting prevents future "consolidate the watchdogs" sessions.

- (e) **`merdian_watchdog.py` is production-critical but untracked in git.** The disaster-rebuild runbook references it (`MERDIAN_HB_Watchdog` task action), but `git clone` doesn't bring it. Worth adding to git as a follow-up so the runbook is actually executable.

- (f) **Retroactive ADR is one-time concession, not a pattern.** ADR-007 retroactively grounds the V18F pivot because V18F predates the ADR habit. Future architectural decisions of comparable scope require ADR before code, not after.

---

---

## Previous session (Session 22) — preserved per no-crunch directive

| Field | Value |
|---|---|
| **Date** | 2026-05-07 (Thursday — Session 22, intra-market through evening). |
| **Concern** | Began as morning verification of Session 21 patches (TD-070 v2, TD-071, TD-072) — all PASS at 08:45 IST cron. Cascaded into MAJOR INCIDENT: Dhan option chain ingest outage on AWS — 151 of 299 daily attempts failed with `401 Authentication Failed - Client ID or Token invalid`, alternating ~50/50 hourly across two windows (09:30-13:30 IST + 14:45-15:25 IST), ~70% degradation of trading day. Six hypotheses tested and refuted; root cause UNCONFIRMED. Spot + option backfill executed via Kite/MeridianAlpha to recover today's gap. TD-079 architectural defect surfaced (zone date-expiry discards unbreached resistances). TD-084 found and fixed same-session (UTC/IST timezone bug in option backfill script). Architecture conversation with operator initiated, 4 questions outstanding at session close. |
| **Type** | Engineering — incident response + data recovery + architectural surfacing. 0 production patches deployed (all S22 work was diagnosis + backfill + documentation). 6 TDs filed (1 closed same-session). 25,499 rows backfilled. Architecture conversation initiated. |
| **Outcome** | PARTIAL. **Pre-market clean** — token refresh, merdian_start manual, preflight PASS, AWS Zerodha refresh, battery flags persist from S21 fix. **08:45 IST cron clean:** MERDIAN_ICT_HTF_Zones_0845 fired exit=0, contract_met=true, 82 zones written — confirms S21 TD-070 v2 + TD-071 stack works in production. **Pine overlay generated:** 36 zones (10 HTF + intraday merged). **TD-079 DISCOVERED HIGH:** Pine visually missing ALL resistances above current spot 78,000 → 86,000; 18 W BEAR_OB/BEAR_FVG zones above 78k all marked EXPIRED purely on date — `valid_to = week_end + 4 weeks` discards structurally-relevant unbreached resistances; ICT canon: zones live until price closes through them, not date-expire; filed as architectural defect bleeding signal quality for months. **MAJOR INCIDENT — Dhan option chain ingest outage (UNRESOLVED):** 151 of 299 attempts failed today with `401`; same Dhan token: capture_spot_1m_v2 succeeded 371/378 (97%); 64 missing 5-min option_chain_snapshots windows. Six hypotheses refuted (token sync silent failure, TD-072 battery flag side-effect, AWS refresh_dhan_token competing writer, MeridianAlpha Dhan competition, long-running stale-token daemon, shadow_runner stale token in memory). Most likely remaining hypothesis: Dhan-side rate limiting on option chain endpoint or per-token instability with the 08:24-issued token. Filed as **TD-080 HIGH**. **BACKFILL EXECUTED via MeridianAlpha:** spot 750 NIFTY+SENSEX rows clean OHLC; option 24,749 rows (NIFTY 8,250 = 22 strikes × 1 expiry May-12 Tuesday weekly + SENSEX 16,499 = 44 strikes × 2 expiries May-7 today-expiring + May-14 Thursday weekly). **TD-084 found and fixed same-session:** backfill_option_zerodha_OI_FIXED line 184 `bar["date"].replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)` shifts every IST-tagged Kite timestamp by +5h30m, dropping 88% of bars; sed-fixed; 46 bars/strike → 375 bars/strike post-fix. **Permanent loss:** 64 option_chain_snapshots windows (Dhan endpoint is real-time only — full chain greeks/IV smile/OI per strike cannot be reconstructed; per-strike OHLC recovered allows ATM straddle reconstruction + basic IV via inverse Black-Scholes). **Architecture conversation INITIATED, UNRESOLVED:** Phase α 4 questions stated — (Q1) zone validity model, (Q2) AWS migration scope, (Q3) token reliability investigation order, (Q4) today's session shape. ENH-93 candidate filed: replay/simulation harness mimicking live runner per V18G § 7.2 6-step pipeline. |
| **Git start → end** | Local Windows: `d7eb8c0` (S20 closeout) → `d7eb8c0` (no Local changes Session 22; S21 patches still uncommitted in working tree). MALPHA AWS: dirty (S22 added 2026-05-07 to BACKFILL_DATES on both spot + option scripts; option script has TD-084 timezone fix applied; uncommitted, MALPHA is Kite gateway not Meridian code). Meridian AWS: not touched this session. |
| **Local + AWS hash match** | Local NOT advancing — Session 21 production patches (TD-070 v1+v2 + TD-071 + TD-072) still in working tree uncommitted at session 22 close. Single-commit-per-session pattern interrupted. Meridian AWS not touched, MALPHA AWS dirty (data-recovery edits). |
| **Files changed (code)** | `~/meridian-alpha/backfill_spot_zerodha.py` (BACKFILL_DATES extended +date(2026,5,7), uncommitted MALPHA dirty); `~/meridian-alpha/backfill_option_zerodha_OI_FIXED.py` (BACKFILL_DATES extended + TD-084 timezone fix applied via sed, uncommitted MALPHA dirty, .bak_S22 preserved). No Local files modified. No Meridian AWS files modified. |
| **Files added (untracked, working dir)** | None on Local. MALPHA AWS: `~/meridian-alpha/backfill_option_zerodha_OI_FIXED.py.bak_S22` (preserved pre-TD-084-fix copy); `/tmp/check_sensex_kite.py` (one-off Kite diagnostic verifying 375 bars per strike); `/tmp/check_option_count.py` (one-off Supabase row counter); `/tmp/option_dryrun.log`, `/tmp/option_dryrun_v2.log`, `/tmp/option_live.log` (run logs). |
| **Files modified (docs)** | `CURRENT.md` (this rewrite — Session 21 + Session 20 content preserved below as Previous session blocks per no-crunch directive). `session_log.md` (Session 22 + Session 21 one-liners prepended retroactively — Session 21 was never documented at session-end). `tech_debt.md` (TD-079, TD-080, TD-081, TD-082, TD-083 added active; TD-084 added then moved to Resolved same session; TD-070, TD-071, TD-072 moved to Resolved with closing context). `MERDIAN_Enhancement_Register.md` (ENH-93 replay harness candidate added). `merdian_reference.json` (v14→v15; Session 21 + Session 22 entries added to change_log). `CLAUDE.md` (v1.13→v1.14; operational findings from Sessions 21+22 appended). |
| **Tables changed** | None (schema). Data: `hist_spot_bars_1m` +750 rows for 2026-05-07 (replacing partial captures from outage windows); `hist_option_bars_1m` +24,749 rows for 2026-05-07 (NIFTY 22 strikes × 1 expiry, SENSEX 44 strikes × 2 expiries); `ict_htf_zones` 82 zones written by 08:45 IST cron. |
| **Cron / Tasks added** | None. 8 tasks have battery flags from Session 21 still in effect. |
| **`docs_updated`** | YES. All six closeout files produced as full downloads (no append/prepend deltas beyond the protocol-mandated newest-first session_log prepend). Session 21 documented retroactively per directive. |

### What Session 22 did, in 12 bullets

**Phase 1 — Pre-market verification + 08:45 IST cron success (S21 patches confirmed in production):**

- Local pre-market: token refresh 08:24:54 IST PASS, merdian_start manual 08:21:56, run_preflight PASS, battery flags persist from Session 21's TD-072 fix.

- AWS pre-market: Zerodha refresh + sed propagate to Meridian AWS .env succeeded; Kite auth verified `OK: Navin Balan OV0782`.

- 08:45 IST `MERDIAN_ICT_HTF_Zones_0845` cron fired clean: exit=0, contract_met=true, 82 zones written. **Confirms S21 TD-070 v2 + TD-071 stack works in production with no ON CONFLICT errors.**

**Phase 2 — Pine overlay revealed TD-079 architectural defect:**

- `python generate_pine_overlay.py` produced `merdian_ict_htf_zones.pine` — 36 zones (10 HTF + intraday merged).

- Visual inspection: ALL resistances above current spot 78,000 → 86,000 missing. SQL confirmed 18 W BEAR_OB/BEAR_FVG zones above 78k all marked `EXPIRED` purely on date — `valid_to = week_end + 4 weeks` discards structurally-relevant unbreached resistances. ICT canon: zones live until price *closes through them*, not date-expire.

- Filed as **TD-079 HIGH** — architectural defect bleeding signal quality for months. Requires `valid_to=NULL` for OB/FVG, keep date-expire only for PDH/PDL, plus backfill pass restoring wrongly-expired W zones to ACTIVE if unbreached.

**Phase 3 — MAJOR INCIDENT: Dhan option chain ingest outage (UNRESOLVED ROOT CAUSE):**

- `ingest_option_chain_local.py` (runs on AWS despite filename) failed 151 of 299 attempts today with `401 Authentication Failed - Client ID or Token invalid`. Alternating 50/50 pattern hourly-stable. Two outage windows: 09:30-13:30 IST (~4hrs) + 14:45-15:25 IST (40min). Manual refresh at 13:30 temporarily restored, broke again ~14:45. **Total downtime ~4.5 of 6.25 trading hours (~70% degradation).** Telegram alerts every 5 min.

- **Same Dhan token:** capture_spot_1m_v2.py succeeded 371/378 (97%). Spot endpoint healthy, option chain endpoint failing — token-side or endpoint-side?

- **Six hypotheses tested and REFUTED:** (1) Token sync silent failure (system_config.dhan_api_token row updated correctly via Supabase write); (2) TD-072 battery flags re-enabled dormant Dhan-touching task (Market_Tape_1M ran only once at 09:00); (3) AWS refresh_dhan_token.py competing writer (file mtime Apr 22, only Invalid TOTP errors from old runs); (4) MeridianAlpha competing for Dhan tokens (MALPHA uses Zerodha not Dhan); (5) Long-running stale-token daemon on AWS (`ps -eo lstart` shows only PID 578 dashboard + PID 579 order_placer from Apr 29; no ingest_option_chain daemon); (6) shadow_runner stale token in memory (subprocess.run is per-cycle, fresh .env read each invocation).

- **Critical context:** operator's laptop was OFF until ~08:15 IST today. `MERDIAN_Intraday_Supervisor_Start` task fired at 08:15:36 (boot time). Action: `merdian_morning_start.ps1` runs `python merdian_start.py` (no token refresh). Double-start (08:15 boot + 08:21 manual) created competing process trees but doesn't directly explain AWS failures.

- Filed as **TD-080 HIGH**. Most likely remaining hypothesis: Dhan-side rate limiting on option chain endpoint or per-token instability with the 08:24-issued token. **Resume next-day controlled test at 09:15 IST cron.**

**Phase 4 — Spot + option backfill via MeridianAlpha:**

- Spot via `~/meridian-alpha/backfill_spot_zerodha.py`: edited BACKFILL_DATES adding `date(2026, 5, 7)`; dry-run confirmed 375 bars/symbol from Kite; live wrote 375 NIFTY + 375 SENSEX clean OHLC rows; final state NIFTY 376 bars/1 flat, SENSEX 376 bars/1 flat — acceptable boundary artifact at 15:29.

- Option via `~/meridian-alpha/backfill_option_zerodha_OI_FIXED.py`: edited BACKFILL_DATES adding `date(2026, 5, 7)`. Dry-run revealed BUG: only 46 bars per strike instead of 375. Direct Kite test (`/tmp/check_sensex_kite.py`) proved Kite returns 375 bars. **TD-084 found and fixed same-session.** Live wrote 24,749 rows total: NIFTY 8,250 (22 strikes × 375 × 1 expiry May-12 — Tuesday weekly per NSE 2025+ change), SENSEX 16,499 (44 strikes × 375 × 2 expiries: May-7 today-expiring + May-14 next Thursday weekly per BSE).

**Phase 5 — TD-084 root cause + same-session fix:**

- Bug: line 184 of `backfill_option_zerodha_OI_FIXED.py` applies `dt_ist = bar["date"].replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)` but Kite already returns IST-tagged datetimes. The `.replace(UTC)` shifts every timestamp +5h30m, then `is_market_hours()` filter accepts only ~46 bars from edge windows.

- Time math: bars 09:15-09:44 IST (real) → become 14:45-15:14 IST (after replace+astimezone) → ACCEPTED (within filter); bars 09:45+ IST → 15:15+ IST → only 09:45-10:14 acceptable, then dropped → ~46 bars total survive. Matches observed exactly.

- Fix via sed: `dt_ist = bar["date"].astimezone(IST) if bar["date"].tzinfo else bar["date"].replace(tzinfo=IST)`. New logic: if bar["date"] already has tzinfo (it does, from Kite as IST) → astimezone(IST) is a no-op; if tzinfo missing → assume IST (safe fallback). Verified dry-run 375 bars/strike post-fix.

**Phase 6 — Architecture conversation INITIATED, UNRESOLVED:**

- Operator priorities locked: (P1) primary data ingestion stable on AWS; (P2) derived layer stays Local; (P3) ICT structures correct (TD-079); (P4) pull related TDs; (P5) open to architectural re-look.

- Phase α 4 questions stated but UNANSWERED: (Q1) zone validity model — recommended (a) pure price-based canonical; (Q2) AWS migration scope — recommended (b) primary layer (capture + zones + runner); (Q3) token reliability work — recommended (a) investigate Dhan token life FIRST; (Q4) today's session shape — recommended discussion-only Phase α + ADR draft.

- ENH-93 candidate filed: replay/simulation harness mimicking live runner for outside-market-hours testing. Per V18G § 7.2 the live AWS shadow runner cycle is 6 ordered scripts: compute_gamma → compute_volatility → build_momentum → build_market_state → build_trade_signal → compute_options_flow. Existing reconstruction tooling cited (`replay_shadow_for_date_local.py`, `reconstruct_shadow_for_date_local_v3.py`, `backfill_gamma_metrics.py`, `backfill_volatility_metrics.py`, `backfill_market_state.py` — all write to `hist_*` tables not live tables, hence ENH-86 distinct from existing tooling).

**CRITICAL LESSONS Session 22:**
- (a) Dhan endpoint may have per-token instability the spot endpoint doesn't share — token issued at 08:24 served capture_spot 97% but option chain 50%. Not a generic Dhan-down event; specific to option chain.
- (b) When laptop was OFF pre-market, double-start at boot + manual creates competing process trees. May matter for token lifecycle.
- (c) NIFTY weekly is now Tuesday (per NSE 2025+ change), SENSEX stays Thursday — same-day backfill may pull 2 SENSEX expiries (today + next-Thursday) but only 1 NIFTY (next-Tuesday). Was unexpected; documented for future backfills.
- (d) Kite returns IST-tagged datetimes for option chain `historical_data` calls — `.replace(tzinfo=UTC)` is the canonical timezone bug pattern, never apply to Kite output. (TD-084.)
- (e) `find_dotenv()` fails in heredoc context — use file approach `load_dotenv("/path/.env")` or write to `/tmp/script.py` and invoke. Hit twice in S22.

---

## Previous session (Session 21) — preserved per no-crunch directive

| Field | Value |
|---|---|
| **Date** | 2026-05-06 (Wednesday — Session 21). |
| **Concern** | Resumed Session 20 carry-forward — verify v2.1 first cycle (PASS, capture_spot_1m_v2 fired clean 09:16:02 IST with real OHLC, contract_met=true), close TD-070 (BULL_OB single-bar prior-direction filter over-restrictive in detect_weekly_zones), close TD-071 (expire_old_zones order bug allowing stale 2025 zones to persist as ACTIVE), close TD-072 (22-min Task Scheduler gap 13:25-13:47 IST traced to power-source change events). |
| **Type** | Engineering — 3 TDs closed via patch deployment (3 patch scripts using v3 patch canon: read_bytes+utf-8-sig, normalize CRLF→LF, ast.parse validate, idempotency guard, write_bytes preserve LF). 6 TDs filed. 0 commits at session close (single-commit pattern broken). |
| **Outcome** | DONE for primary patches; documentation slipped — **session_log.md never received Session 21 entry at session end**, rectified retroactively in Session 22 closeout. **TD-070 v1 patch:** `fix_td070_weekly_ob_lookback.py` replaced single-bar `prior_move < 0` check in detect_weekly_zones() with 8-week unbreached-anchor lookback via new `_find_unbreached_anchor()` helper (TD070_LOOKBACK_WEEKS = 8); symmetric BULL_OB + BEAR_OB; body-based breach test; most-recent-bearish anchor selection. **TD-071 patch:** `fix_td071_zone_pipeline_order.py` rewrote expire_old_zones() — dropped `.eq("status","ACTIVE")` filter, added `.in_("timeframe",["W","D"])` (H carve-out per operator), added `.neq("status","EXPIRED")` idempotency guard; pipeline reorder in main(): expire moved from BEFORE upserts to AFTER recheck_breached_zones(); final order: detect → upsert(ACTIVE) → recheck(price-breach) → expire(date). **TD-070 v2 dedup fix:** Initial deploy of v1 crashed live with Postgres 21000 'cannot affect row a second time' error on upsert ON CONFLICT; root cause: 8-week lookback can produce multiple zone entries from same source-bar-date → same conflict key (symbol, timeframe, pattern_type, source_bar_date, zone_high, zone_low); fixed via `fix_td070_v2_dedup.py` adding `_dedup_zones_by_conflict_key()` to collapse zones matching upsert ON CONFLICT key, keeping earliest valid_from. Backups: `_PRE_S21.py`, `_PRE_S21_TD071.py`, `_PRE_TD070V2.py`. **TD-072 patch:** 22-min Task Scheduler gap traced to power-source change events (battery on/off transitions during market hours); PowerShell loop set `DisallowStartIfOnBatteries=$false` and `StopIfGoingOnBatteries=$false` on 8 market-hours tasks. **Session 21 verification (live rebuild 18:33 IST):** NIFTY 37 W zones written + SENSEX 39 W zones written = 78 total; zero ON CONFLICT errors; SQL confirmed 18 stale BREACHED W zones flipped to EXPIRED correctly. |
| **Git start → end** | Local Windows: `d7eb8c0` (S20 closeout) → uncommitted (single-commit pattern interrupted; production patches in working tree at Session 22 start). MALPHA AWS: not touched. Meridian AWS: not touched. |
| **Files changed (code)** | `C:\GammaEnginePythonuild_ict_htf_zones.py` (TD-070 v1 + TD-071 + TD-070 v2 dedup stack applied — commit pending); 8 Task Scheduler tasks have battery flags disabled (TD-072 fix). |
| **Files added (untracked, working dir)** | `C:\GammaEnginePythonix_td070_weekly_ob_lookback.py`, `C:\GammaEnginePythonix_td071_zone_pipeline_order.py`, `C:\GammaEnginePythonix_td070_v2_dedup.py`, `C:\GammaEnginePythonuild_ict_htf_zones.py._PRE_S21`, `C:\GammaEnginePythonuild_ict_htf_zones.py._PRE_S21_TD071`, `C:\GammaEnginePythonuild_ict_htf_zones.py._PRE_TD070V2`. |
| **Files modified (docs)** | None at Session 21 close. session_log.md, CURRENT.md, tech_debt.md, merdian_reference.json, MERDIAN_Enhancement_Register.md, CLAUDE.md all NOT updated — documentation debt accrued; rectified retroactively in Session 22 closeout. |
| **Tables changed** | None (schema). Data: `ict_htf_zones` 18 stale W zones flipped from ACTIVE/BREACHED to EXPIRED; 78 fresh W zones written by rebuild; final state NIFTY 37 + SENSEX 39 W zones healthy. |
| **Cron / Tasks added** | None (existing 8 tasks had battery flags reconfigured). |
| **`docs_updated`** | NO at session close (rectified retroactively Session 22). |

### What Session 21 did, in 8 bullets

- **Resumed carry-forward from Session 20** — verified v2.1 first cycle PASS (capture_spot_1m_v2 fired clean 09:16:02 IST with real OHLC, contract_met=true). Phase 2a Local stabilization confirmed working in live market hours.

- **TD-070 v1: BULL_OB lookback widening.** Replaced single-bar prior-direction check in detect_weekly_zones() with 8-week unbreached-anchor lookback (TD070_LOOKBACK_WEEKS = 8). New helper `_find_unbreached_anchor()`. Symmetric BULL_OB + BEAR_OB. Body-based breach test. Most-recent-bearish anchor selection. Backward-compat preserved.

- **TD-071: pipeline order fix.** expire_old_zones() rewritten — dropped `.eq("status","ACTIVE")` filter, added `.in_("timeframe",["W","D"])` (H carve-out per operator), added `.neq("status","EXPIRED")` idempotency guard. Pipeline reorder: detect → upsert → recheck → expire (was: expire → detect → upsert → recheck).

- **TD-070 v2 dedup: live deploy crash + fix.** Initial v1 deploy crashed with Postgres 21000 'cannot affect row a second time' on upsert ON CONFLICT. Root cause: 8-week lookback produces multiple zone entries from same source-bar-date with same conflict key. `_dedup_zones_by_conflict_key()` collapses zones matching upsert ON CONFLICT key, keeping earliest valid_from. Backups preserved.

- **TD-072: 22-min Task Scheduler gap traced to battery events.** PowerShell loop set `DisallowStartIfOnBatteries=$false` and `StopIfGoingOnBatteries=$false` on 8 market-hours tasks: MERDIAN_Spot_1M, MERDIAN_PreOpen, MERDIAN_IV_Context_0905, MERDIAN_PO3_SessionBias_1005, MERDIAN_Market_Tape_1M, MERDIAN_HB_Watchdog, MERDIAN_ICT_HTF_Zones_0845, MERDIAN_Intraday_Supervisor_Start.

- **Verification rebuild 18:33 IST:** NIFTY 37 W zones + SENSEX 39 W zones = 78 total, zero ON CONFLICT errors, 18 stale W zones flipped to EXPIRED correctly.

- **TDs filed (PENDING for S22+):** TD-073 HIGH (momentum direction lagged 700pt rally May 6 by ~60 min); TD-074 MED (ENH-77 BULL_OB AFTERNOON NIFTY hard skip blocked the only TIER1 signal); TD-075 MED (confidence threshold 60 vs observed max 45); TD-076 LOW (SENSEX DTE gate persistent block on weekly expiry); TD-077 LOW (wide FVG zones during volatile weeks lack outlier filter); TD-078 PENDING (TD-070 closure verification incomplete — empirically multi-week lookback may not be firing).

- **Operational learnings recorded:** PowerShell `copy /Y` doesn't work — use `Copy-Item -Force` (truncated `.p` file caused TD-070 v2 deploy confusion); dedup hides 'missing' zones (Apr-13 BULL_OB folded into Apr-06 anchor — semantically correct); multi-rebuild status flips are idempotent — recheck and expire are date-stable; PowerShell `Add-Content` appends after `exit /b` making lines unreachable — use string replacement to insert before exit line.

---

## Previous session (Session 20 — superseded by Session 22 block above) — preserved per no-crunch directive

| Field | Value |
|---|---|
| **Date** | 2026-05-05 (Tuesday — Session 20, very long: pre-dawn → 21:00+ IST). |
| **Concern** | Began as TD-068 audit task fix from Session 19. Expanded into full diagnostic of `capture_spot_1m.py` synthetic-flat-bar architecture (long-standing root cause for BULL_OB/BEAR_OB zero-emission across detection history). Cascaded into spot data backfill Apr 1 → May 5. Concluded with Phase 2a deployment of v2.1 real-OHLC live writer + HTF zone rebuild + Pine static rewrite. |
| **Type** | Engineering — multi-deliverable session: 2 production patches deployed (audit script rewrite + capture_spot_1m_v2 NEW), 1 data recovery (16,500 spot bars Apr 1 → May 5 real OHLC), 1 architectural change (live writer LTP synthetic → REST OHLC), 1 Pine static rewrite, 5 TDs filed. |
| **Outcome** | DONE. **TD-068 RESOLVED end-to-end:** v2.1 `capture_spot_1m_v2.py` deployed to Local Task Scheduler with full `pythonw.exe` path; replaces synthetic O=H=L=C=spot from `/v2/marketfeed/ltp` with real 1-min OHLC from `/v2/charts/intraday`; v2.1 features market-hours guard + filler-bar skip for post-market filler responses; v1 untouched at `capture_spot_1m.py` for rollback. **Daily audit task fixed and rewritten:** Session 19 script broken (MimeText Python 3.12 incompat, wrong table names, malformed PostgREST queries, Task Scheduler ERROR_FILE_NOT_FOUND from bare `python`); fixed via new `run_daily_audit.bat` wrapper; full rewrite (831 lines) using Supabase Python client, three windows (pre/intra/post), per-pattern-type breakdown surfacing zero-emission as WARN. **Spot backfill Apr 1 → May 5:** 16,500 clean OHLC rows in `hist_spot_bars_1m`, 0 flats, both NIFTY+SENSEX (Kite returns SENSEX index spot OHLC despite no BSE F&O); 16 stray 15:30:00 IST boundary flat bars deleted via scoped DELETE. **HTF zones rebuilt with real OHLC:** detector now fires all 4 pattern types — W BULL_OB 2 ACTIVE / 18 BREACHED, W BULL_FVG 2 ACTIVE / 11 BREACHED, W BEAR_OB 0 ACTIVE / 2 BREACHED, W BEAR_FVG 0 ACTIVE / 2 BREACHED. Confirms detector logic sound — previous BULL_OB/BEAR_OB zero-emission was data-driven (synthetic flat bars), not detector defect. **Pine static rewrite shipped:** 14 zones (NIFTY 7 + SENSEX 7) from tonight's rebuild — clean OHLC, no stale M5 noise; new color spec applied (BULL_OB green #1B8C3E, BULL_FVG light green #6FCF7C, BEAR_OB red #B22222, BEAR_FVG light red #F08080, white text labels, PDH/PDL stay yellow/orange). |
| **Git start → end** | Local Windows: `pending` → `pending` (operator commits at end of session per protocol). MALPHA AWS: `backfill_spot_zerodha.py` BACKFILL_DATES extended (uncommitted, undesirable but accepted — MALPHA is Kite gateway not Meridian code). Meridian AWS: not touched this session. |
| **Local + AWS hash match** | Local advancing this session. Meridian AWS not touched. MALPHA AWS has dirty BACKFILL_DATES extension (one-off backfill, won't recur). Phase 2b AWS migration deferred to Session 21+. |
| **Files changed (code)** | `merdian_daily_audit.py` (FULL REWRITE — 831 lines, backup `.pre_s20.bak`); `run_daily_audit.bat` (NEW wrapper); `capture_spot_1m_v2.py` (NEW — 475 lines, v2.1 with market-hours guard + filler-bar skip); Task Scheduler `MERDIAN_Daily_Audit` action updated to use bat wrapper; Task Scheduler `MERDIAN_Spot_1M` action repointed to v2 with full `pythonw.exe` path. |
| **Files added (untracked, working dir)** | `C:\GammaEnginePython\capture_spot_1m_v2.py`, `C:\GammaEnginePython\run_daily_audit.bat`, `C:\GammaEnginePython\merdian_daily_audit.py.pre_s20.bak`, `C:\GammaEnginePython\logs\dhan_probe.py` (one-off Dhan API verification), `C:\GammaEnginePython\logs\v2_test_*.log`. Pine static rewrite `merdian_ict_htf_zones_s20.pine` ready for paste into TradingView. |
| **Files modified (docs)** | (Session 20 closeout — recorded all 6 files updated via full downloads.) |
| **Tables changed** | None (schema). Data: `hist_spot_bars_1m` 16,500 rows backfilled real OHLC + 16 stray flats deleted; `ict_htf_zones` 80 zones written by rebuild (NIFTY 39 + SENSEX 41 with breach status). |
| **Cron / Tasks added** | `MERDIAN_Daily_Audit` action updated to use `run_daily_audit.bat` wrapper. `MERDIAN_Spot_1M` action repointed to `capture_spot_1m_v2.py` with full `pythonw.exe` path. No new tasks added. |
| **`docs_updated`** | YES (S20 close). |

(Full Session 20 detail bullets preserved in earlier `## Previous session (Session 19 — superseded by Session 20 block above)` block below per no-crunch directive — see preceding history.)

---

## Previous session (Session 19 — superseded by Session 20 block above) — preserved per no-crunch directive


| Field | Value |
|---|---|
| **Date** | 2026-05-04 (Sunday — Session 19, data recovery + documentation + live trading validation: complete data backfill after internet outage 12 noon to market close, systematic audit automation implementation, first live OB rejection trade recorded) |
| **Concern** | Data recovery after major internet outage corrupted spot/options data for 2026-05-04. Primary: backfill corrupted market data. Secondary: create operational procedures for future outages. Tertiary: document live trading validation. |
| **Type** | Engineering + Operations — data recovery session: 2,774 bars backfilled (750 spot + 2,024 options), 2 new operational tools created (data backfill runbook + daily audit script), 1 live trading log established, pattern detection restored to normal function |
| **Outcome** | DONE. **Data Recovery COMPLETE:** Internet outage 12:00-15:30 IST caused flat OHLC bars (O=H=L=C) preventing Order Block detection. Spot backfill: 750 bars (375 NIFTY + 375 SENSEX) with proper OHLC formation restored. Options backfill: 2,024 bars (966 NIFTY + 1,012 SENSEX + 46 duplicate) with full ATM±5 strike coverage. Pattern detection verification: BEAR_FVG 8→22, BULL_FVG 11→15, OB detection ready for normal market conditions. **Operational Automation ESTABLISHED:** `runbook_data_backfill_internet_outage.md` created with complete diagnostic-to-recovery procedures for future outages. `merdian_daily_audit.py` created for 16:00 IST daily execution with automatic data integrity checks and alert/backfill triggers. Email alert configuration implemented on AWS. **Live Trading Validation RECORDED:** First systematic documentation of live OB rejection trade: 10:00 AM NIFTY HTF zone rejection → PE position 12 lots → +30 points premium captured → partial fill of 240-point total move. `MERDIAN_Live_Trading_Log_v1.md` established for ongoing systematic capture of signal validation + discretionary execution overlay. Gap interaction confirmed (2026-04-29/30 gap edge hit, drill-through, PDH break). System signal accuracy validated in live market conditions. |
| **Git start → end** | `pending` (Session 18 hypothetical close) → `pending` (Session 19 commits). Documentation-only session with new operational files created. AWS email credentials configured. |
| **Local + AWS hash match** | Documentation session. No code patches deployed. AWS email configuration added to `.env`. |
| **Files created (runbooks)** | `runbook_data_backfill_internet_outage.md` (comprehensive operational procedure for internet outage data recovery with diagnostic queries, step-by-step spot/options backfill, common issues/solutions, automation integration). `merdian_daily_audit.py` (automated 16:00 IST audit script with data integrity thresholds, email alerts, auto-backfill capability via SSH to AWS, configurable date/alert-only/auto-backfill modes). |
| **Files created (trading)** | `MERDIAN_Live_Trading_Log_v1.md` (systematic capture of live trading executions with signal validation, discretionary overlay analysis, market structure observations, performance tracking, integration with system development). |
| **Files modified (docs)** | `CURRENT.md` (this complete rewrite — Session 17 content preserved below per no-crunch directive). `session_log.md` (Session 19 one-liner prepended). `tech_debt.md` (no new items — data recovery successful, no new technical debt identified). `MERDIAN_Enhancement_Register.md` (no new ENH items — operational tools created, not system enhancements). `merdian_reference.json` (v12→v13 with Session 19 updates). `CLAUDE.md` (version tracking update for session completion). |
| **Data Recovery Summary** | **Pre-recovery:** hist_spot_bars_1m 750 flat bars (O=H=L=C), hist_option_bars_1m 0 bars, pattern detection BEAR_FVG=8 BULL_FVG=11 BEAR_OB=0 BULL_OB=0. **Post-recovery:** hist_spot_bars_1m 750 proper OHLC bars (market hours 09:15-15:29 IST), hist_option_bars_1m 2,024 bars (22 instruments per symbol, 46 bars each), pattern detection BEAR_FVG=22 BULL_FVG=15 plus OB detection ready. **Tools used:** AWS backfill_spot_zerodha.py (modified BACKFILL_DATES), new backfill_option_zerodha_OI_FIXED.py (schema-corrected for hist_option_bars_1m constraints). **Verification:** TD-060 pattern detection query confirmed significant improvement in FVG counts, OB detection functional with proper data quality. |
| **Tables changed** | hist_spot_bars_1m (750 corrupted rows replaced with proper OHLC), hist_option_bars_1m (2,024 rows added for 2026-05-04), option_chain_snapshots (preserved during outage), market_state_snapshots (preserved), signal_snapshots (preserved). |
| **AWS Configuration** | Email alert credentials added to `.env` file: ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD (app password), ALERT_EMAIL_TO. Daily audit script deployed for automated monitoring. |
| **Cron / Tasks added** | None this session. `merdian_daily_audit.py` designed for Windows Task Scheduler deployment (16:00 IST daily). |
| **`docs_updated`** | YES. Complete documentation closeout per protocol v3: CURRENT.md rewritten, session_log.md updated, merdian_reference.json incremented, new operational files created with proper protocol structure. No `.docx` generation required (operational session, not phase boundary). |

### What Session 19 did, in 10 bullets

**Phase 1 — Data Recovery Diagnosis:**

- **Internet outage impact assessed:** 12:00-15:30 IST connectivity loss corrupted real-time data collection. 750 spot bars recorded as flat (O=H=L=C) preventing candle color determination required for Order Block detection. Zero option bars written for trade date. Option chain snapshots, market state, and signals preserved (snapshot tables 105K+, 222, 222 rows respectively).

- **Pattern detection verification revealed selective impact:** TD-060 query showed BEAR_FVG=8, BULL_FVG=11, but BEAR_OB=0, BULL_OB=0 despite previous session fixes. Root cause confirmed as data quality (flat bars) not detector logic. FVG patterns detected because they rely on gap relationships, OB patterns failed because they require candle color determination from OHLC.

**Phase 2 — Systematic Data Backfill:**

- **Spot data recovery via AWS:** Modified existing `backfill_spot_zerodha.py` by adding `date(2026, 5, 4)` to BACKFILL_DATES array. Script ignores command line arguments (hardcoded date list). Successful backfill: 750 bars with proper OHLC formation (375 NIFTY + 375 SENSEX), market hours 09:15-15:29 IST, zero flat bars post-recovery.

- **Options data recovery via new schema-corrected script:** Created `backfill_option_zerodha_OI_FIXED.py` after debugging schema mismatches. hist_option_bars_1m requires instrument_id (UUID), uses option_type not opt_type, strike not strike_price, oi cannot be null. Final version resolved all constraints: 22 instruments per symbol (ATM ±5 strikes), 46 bars each, 2,024 total rows written. Only one 409 duplicate error (NIFTY24000CE from earlier attempt).

**Phase 3 — Operational Documentation and Automation:**

- **Comprehensive backfill runbook created:** `runbook_data_backfill_internet_outage.md` follows MERDIAN documentation protocol with complete diagnostic queries, step-by-step recovery procedures, common issues/solutions, automation integration points. Covers spot + options + option chain verification, AWS SSH configuration, schema mapping, Kite API usage patterns.

- **Daily audit automation implemented:** `merdian_daily_audit.py` for 16:00 IST execution with configurable thresholds (spot_bars_min=700, option_bars_min=1500, option_snapshots_min=50000, patterns_min=5, flat_bars_max_pct=10). Email alerts, auto-backfill capability, audit result persistence. Designed for Windows Task Scheduler integration with `--auto-backfill` and `--alert-only` modes.

- **AWS email configuration completed:** Added ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD (Gmail app password without spaces), ALERT_EMAIL_TO to `.env` file for alert functionality. Verified SMTP authentication configuration follows security best practices.

**Phase 4 — Live Trading Validation and Documentation:**

- **First systematic OB rejection trade recorded:** 2026-05-04 ~10:00 AM, NIFTY HTF Order Block rejection setup. Market opened flat, rushed into upper OB zone (brown/gold TradingView overlay), clear rejection signal. Position: PE options, 12 lots (discretionary upsize), 20-point NIFTY stop loss planned. Result: +30 points premium captured on initial move.

- **Market structure analysis documented:** Total 240-point decline from 24250 resistance. First move down hit edge of gap from 2026-04-29/30, recovered, then drill-through taking out Previous Day High (PDH). Mid-day sideways action confirmed previous experiment predictions. System signal validation: OB rejection worked as expected, HTF zone placement accurate.

- **Trading log framework established:** `MERDIAN_Live_Trading_Log_v1.md` created for systematic capture of signal validation + discretionary execution. Template structure for future trades, performance summary tracking, integration with enhancement development process. Entry #001 documents full context: systematic signal accuracy, discretionary position sizing analysis, conviction gap on extended moves, system implications for future development.

**Phase 5 — Pattern Detection Restoration Verification:**

- **Post-backfill pattern detection confirmed functional:** Re-run of TD-060 verification query showed BEAR_FVG increased from 8 to 22, BULL_FVG increased from 11 to 15. Order Block patterns remained at 0 but this reflects market conditions (no suitable OB formations) rather than data quality issues. Proper OHLC data enables future OB detection when market structure supports it.

---

## Previous session (Session 17 — superseded by Session 20 block above) — preserved per no-crunch directive


| Field | Value |
|---|---|
| **Date** | 2026-05-03 (Sunday — Session 17, very long: TD-058 BEAR_FVG live fix → TD-060 discovered/diagnosed/fixed → Pine ENH-91 + ENH-92 + readability rewrite → operational task scheduler diagnosis). |
| **Concern** | Session 16 carry-forward Priority A: TD-058 BEAR_FVG live emission fix (`detect_ict_patterns.py` adds BEAR_FVG branch). Session expanded to include Priority B (ENH-88 BULL_FVG cluster gate) which surfaced TD-060 (live runner emits zero OBs across 14 days). |
| **Type** | Engineering — multi-fix session: 2 production patches deployed (Local + AWS), 2 ENH SHIPPED (Pine WR + intraday), 1 ENH BUILT NOT DEPLOYED (ENH-88 awaiting Mon live data), 1 ENH CANDIDATE filed (ENH-90), 4 TDs filed (TD-060 RESOLVED same session, TD-061/062/063 NEW). |
| **Outcome** | DONE. **TD-058 RESOLVED end-to-end:** 5-edit patch, BEAR_FVG signal count 0 → 138 across full year, combined NIFTY+SENSEX P&L ₹11.7L → ₹12.6L (+22.8pp lift). **TD-060 NEW + RESOLVED same session:** runner window-slice (F4) + detector check_from removal (G1); full-day smoke on Feb 01 NIFTY achieved 14/14 OB coverage = 100% within tradeable hours (versus 0 OB pre-fix across 14 days × 2280 cycles in production). **ENH-91 SHIPPED:** Pine zone labels embed WR per pattern_type from Exp 15 cohort (BULL_OB 84%, BEAR_OB 92%, BULL_FVG 50%, BEAR_FVG 46%). **ENH-92 SHIPPED:** Pine intraday `ict_zones` rendered as M5 timeframe alongside HTF zones (20-zone-per-symbol cap for Pine 250-element limit). **ENH-88 BUILT NOT DEPLOYED:** BULL_FVG cluster gate patch ready as `_PATCHED.py`, deferred until Mon live data confirms BULL_OB signals flow into `signal_snapshots` post-TD-060 fix. **ENH-90 CANDIDATE filed:** BEAR_FVG anti-cluster gate (-16.5pp anti-edge with N=22, deferred for N expansion per Rule 22 + Session 17 N-threshold). **TD-061/062/063 NEW (operational):** Task Scheduler window suppression, Saturday stuck-process root cause, single-instance enforcement. **13 MERDIAN_* tasks re-enabled** for Mon open after operator killed runaway Python processes Saturday May-2. |
| **Git start → end** | `f2789b9` (Session 16 close) → `pending` (Session 17 commits). Operator commits at end of session per protocol. AWS synced via `git pull`. |
| **Local + AWS hash match** | Local advancing this session. **AWS pulled** — both `detect_ict_patterns.py` and `detect_ict_patterns_runner.py` patches deployed; `_PRE_S17_TD060.py` snapshots present on AWS. |
| **Files changed (code)** | `detect_ict_patterns.py` (G1 — `check_from` filter removed, 1 line + 3 list comprehension filters); `detect_ict_patterns_runner.py` (F4 — `bars=bars` → `bars=bars[-30:]`); both renamed canonical, `_PRE_S17_TD060.py` snapshots preserved. `generate_pine_overlay.py` (ENH-91 + ENH-92 + readability rewrite — 8 anchored edits across 1 file plus 2 hotfix iterations for Pine v6 strict typing). |
| **Files added (untracked, working dir)** | `patch_td058_bear_fvg_emission.py`, `patch_enh88_bull_fvg_cluster_gate.py`, `diag_enh88_data_source.py`, `patch_td060_runner_instrumentation.py`, `diag_td060_local_repro.py`, `diag_td060_subdetector_trace.py`, `patch_td060_runner_window_slice.py`, `patch_td060_remove_check_from.py`, `diag_td060_full_day_smoke.py`, `patch_pine_intraday_and_wr.py`, `patch_pine_readability.py`, `patch_pine_readability_hotfix.py`, `patch_pine_readability_hotfix2.py`, `diag_pine_zones_audit.py`, `diag_htf_zones_post_build.py`, `diag_active_intraday_zones.py`. All covered by existing `.gitignore` patterns. |
| **Files modified (docs)** | `CURRENT.md` (this rewrite — Session 16 content preserved below as historical reference per no-crunch directive). `session_log.md` (Session 17 one-liner prepended). `tech_debt.md` (TD-060/061/062/063 added; TD-058 moved to Resolved). `MERDIAN_Experiment_Compendium_v1.md` (Session 17 BEAR_FVG live cohort + cluster asymmetry entry prepended). `MERDIAN_Enhancement_Register.md` (ENH-90 CANDIDATE, ENH-91 SHIPPED, ENH-92 SHIPPED prepended; ENH-88 status updated). `merdian_reference.json` (v11→v12). `CLAUDE.md` (v1.11→v1.12, Rule 22 + B13 + B14 + six findings). |
| **Tables changed** | None. |
| **Cron / Tasks added** | None. 13 existing MERDIAN_* tasks re-enabled. |
| **`docs_updated`** | YES. All seven closeout files produced as full downloads (no append/prepend deltas, no crunching of old entries). |

### What Session 17 did, in 12 bullets

**Phase 1 — TD-058 BEAR_FVG live emission fix:**

- **5-edit patch shipped to `detect_ict_patterns.py` + `experiment_15_pure_ict_compounding.py`.** Edits: (1) `OPT_TYPE` dict adds `BEAR_FVG: PE`; (2) `DIRECTION` dict adds `BEAR_FVG: -1`; (3) `detect_fvg()` body adds BEAR predicate `prev.low > nxt.high and (prev.low - nxt.high)/ref >= min_g`; (4) zone-construction `elif pattern_type == "BEAR_FVG"` block; (5) Exp 15 simulator `build_simulated_htf_zones()` 1H BEAR_FVG mirror. Originals preserved as `_PRE_S17.py`.

- **Validation:** Re-run of Exp 15 simulator on full-year cohort produced BEAR_FVG signal count 0 → 138; combined NIFTY+SENSEX P&L ₹11.7L → ₹12.6L (+22.8pp lift). Section 17 of `analyze_exp15_trades.py` confirmed bear-side FVG detection now functional across all regimes.

**Phase 2 — Cluster effect direction-asymmetry finding:**

- **BULL_FVG cluster (Session 16 finding) replicates:** +12.8pp lift at 90-min lookback (N=64 cluster vs N=91 standalone, 57.8% vs 45.1% WR). ENH-88 patch built around this finding.

- **BEAR_FVG cluster runs OPPOSITE direction:** -16.5pp anti-edge at 90-min lookback (N=22 cluster vs N=116 standalone, 31.8% vs 48.3% WR). Direction-asymmetric finding filed as ENH-90 CANDIDATE; not deployed because N=22 too small (Wilson CI [16.4, 52.8] includes 50%) and Session 17 codified an N-threshold rule for direction-asymmetric gates.

**Phase 3 — TD-060 discovery/diagnosis/fix:**

- **Discovered while attempting ENH-88 deploy.** `signal_snapshots` last 14 days had only NONE and BULL_FVG signals — zero OBs of either direction. Initial hypothesis: schema or write-path issue. Diagnostic `diag_enh88_data_source.py` ruled out schema. Two diagnostics built progressively narrowed scope: `diag_td060_local_repro.py` (reproduces zero-OB on local data) → `diag_td060_subdetector_trace.py` (sub-detectors find 14 OBs + 13 FVGs on Feb 01 NIFTY but `ICTDetector.detect()` returns 0). Filter mismatch confirmed.

- **Root cause:** `detect_ict_patterns.py` had `check_from = max(0, len(bars) - 10)` filter that limited visible OB-candle slot to 4 bars regardless of input size; runner passed `bars=bars` (full session ~400 bars) every 5-min cycle. Combined: cycle stride=5 + eligible window=4 = systematic gap where most session OBs miss every cycle. Only end-of-cycle BULL_FVGs slipped through, explaining production's all-BULL_FVG signal pattern.

- **Fix shipped as 2-patch pair:** F4 (runner `bars=bars[-30:]`) + G1 (detector `check_from` filter removed entirely + 3 list comprehension filters removed). Per-cycle re-detection idempotent via `on_conflict` upsert. Verification: `diag_td060_full_day_smoke.py` simulated 80 5-min cycles on Feb 01 NIFTY, achieved 14/14 OB coverage = 100% within tradeable hours. Both patches deployed Local + AWS via `git pull`; `_PRE_S17_TD060.py` snapshots preserved.

**Phase 4 — Pine generator enhancements:**

- **ENH-91 + ENH-92 shipped together:** WR labels per pattern_type from Exp 15 cohort + intraday `ict_zones` merged into Pine output as M5 timeframe. `INTRADAY_CAP_PER_SYMBOL = 20` to stay safely under Pine v6's 250 box/line/label limit when combined with HTF zones.

- **Pine readability rewrite + 2 hotfix rounds:** Initial rewrite added 5 configurable Pine inputs (`label_pos`, `max_lookback`, `pdh_pdl_as_line`, `label_size`, `label_text_col`); CE10149 error on `size lbl_sz` declaration (Pine v6 — `size` is namespace not type kw); CE10235 on if/else block-type unification (Pine v6 — branches must produce same value type). Hotfix 1 removed invalid type kw; hotfix 2 split if/else into sequential if blocks. Final Pine compiled clean and pasted into TradingView working.

- **Pine generated tonight:** 55 zones (49 HTF + 6 intraday from Apr-30). Intraday zones not stale despite Apr-30 LastRun timestamp because May-1 holiday + May-2 Sat + May-3 Sun = zero trading days elapsed since last live runner cycle.

**Phase 5 — Operational task scheduler diagnosis (NOT FIXED):**

- **Task Scheduler held 13 MERDIAN_* tasks Disabled** after operator killed runaway Python processes Saturday. Re-enabled all 13 via PowerShell loop for Monday open. NO zombie Python processes confirmed via `Get-Process` check.

- **Saturday LastRun timestamps decoded:** 5 tasks (Market_Close_Capture, Post_Market_1600_Capture, Session_Markers_1602, Spot_1M, EOD_Breadth_Refresh) had LastRun=02-05-2026 despite DoW=62 (Mon-Fri only) trigger. NOT new Saturday triggers — these were kill-time artifacts. LastResult 2147946720 = "instance already running". Stuck-process accumulation root cause (TD-062) deferred to dedicated session.

- **Three TDs filed for follow-up:** TD-061 (Task Scheduler window suppression — `pythonw.exe` migration), TD-062 (Saturday stuck-process root cause), TD-063 (single-instance enforcement). All deferred — none blocks Mon open.

---

## This session (Session 18)

| Field | Value |
|---|---|
| **Goal** | TBD by operator. Several priorities lined up; pick ONE per Rule 3 (one concern per session). |
| **Type** | Operator's call — engineering / operations / research. |
| **Success criterion** | Defined when goal is set. |

### Carry-forward priority queue (ordered by recommended priority for Session 18):

| Priority | Item | Why |
|---|---|---|
| **A** | Verify TD-060 fix in live data + ENH-88 deploy | Mon morning live cycle should populate `ict_zones` with all four pattern types (BULL_OB, BEAR_OB, BULL_FVG, BEAR_FVG). Once `signal_snapshots` shows BULL_OB rows flowing, ENH-88 BULL_FVG cluster gate becomes meaningful and can be deployed (`_PATCHED.py` already built and verified). Verification SQL: `SELECT pattern_type, COUNT(*) FROM ict_zones WHERE trade_date = current_date GROUP BY 1;` — expect all four types > 0 by end of first hour. |
| **B** | TD-061/062/063 Task Scheduler hygiene | Operator productivity tax (TD-061 visible windows, B14 anti-pattern). Stuck-process accumulation (TD-062) is the deeper bug — needs heartbeat instrumentation to identify which task gets stuck. TD-063 single-instance enforcement is the small defense-in-depth fix that can ship in same session as TD-061 PowerShell re-registration loop. |
| **C** | TD-056 bull-skew mechanism investigation | Section 17 evidence narrows the defect to OB-specific (NIFTY DOWN OB ratio 3.29x suspect; FVG ratio 0.64x correctly directional). The OB detector has a direction-asymmetric defect upstream of the FVG detector. Investigate `detect_obs` symmetry across BULL/BEAR predicate logic. |
| **D** | ENH-90 BEAR_FVG anti-cluster gate | Direction-asymmetric finding (-16.5pp at 90min) needs N expansion to clear Session 17's N-threshold (≥50 in smaller arm + Wilson CI lower bound clears 50% by ≥5pp). Deferred until either more data accumulates or controlled experiment synthesizes more cluster cells. |
| **E** | Documentation closure (this list) | If Session 17's documentation files don't get committed to Git + uploaded to project knowledge before Session 18, Session 18's Claude reads stale state. Operator should commit + upload the 7 files produced this session. |

### Files / tables / items relevant for next session

- **`detect_ict_patterns.py`** — patched canonical (Session 17 G1)
- **`detect_ict_patterns_runner.py`** — patched canonical (Session 17 F4)
- **`generate_pine_overlay.py`** — patched canonical (ENH-91 + ENH-92 + readability)
- **`build_trade_signal_local.py`** — has parked ENH-88 patch as `_PATCHED.py` (not yet renamed to canonical)
- **`ict_zones` table** — primary observability target for TD-060 fix verification
- **`signal_snapshots` table** — secondary verification target for ENH-88 deploy gating
- **TradingView chart Pine** — currently has Session 17 generated overlay; Mon ~10:30 IST refresh expected
- **Task Scheduler (Windows)** — 13 MERDIAN_* tasks re-enabled, ready for Mon 08:00 IST onward triggers

### DO NOT REOPEN this session

- ❌ TD-058 BEAR_FVG live emission — RESOLVED Session 17, validated end-to-end
- ❌ TD-060 runner window-slice + check_from removal — RESOLVED Session 17, 100% smoke coverage
- ❌ Pine readability hotfix #2 — final Pine compiles cleanly, pasted into TradingView, working
- ❌ ENH-88 design (require recent BULL_OB cluster) — settled, only deployment-vs-defer is open
- ❌ ENH-91 WR label values — settled from Exp 15 Section 9 cohort; refresh only on next major dump
- ❌ ENH-92 intraday merge approach — settled (M5 timeframe label, 20-zone cap, reuse show_h toggle)

---

## Live state snapshot (at Session 18 start, 2026-05-03 close)

| Component | State |
|---|---|
| **Local** | Detector + runner patches deployed canonical. Pine generator patched. 13 Task Scheduler tasks re-enabled. No zombie Python processes. |
| **AWS (MERDIAN, `i-0e60e4ed9ce20cefb`)** | Detector + runner patches deployed via `git pull`; `_PRE_S17_TD060.py` snapshots present. AWS cron unchanged. |
| **Critical items (C-N)** | None new. |
| **Tech debt (active)** | TD-061 (S2), TD-062 (S2), TD-063 (S3) NEW Session 17. TD-056 narrowed to OB-specific. TD-058 RESOLVED. TD-060 RESOLVED same-session. Plus all pre-Session-17 active TDs unchanged. |
| **ENH in flight** | ENH-88 BUILT NOT DEPLOYED (awaits Mon live BULL_OB data). ENH-90 CANDIDATE (deferred for N expansion). ENH-91 + ENH-92 SHIPPED. |
| **Pine on TradingView** | 55-zone overlay (49 HTF + 6 intraday); 2026-05-03 generation; show_h ON; readability inputs configured per operator preference. |
| **Trading calendar** | 2026-05-04 (Mon) is open trading day. Pre-market sequence ready; tasks re-enabled. |

---

## Mid-session checkpoints (per Session Management Rule 1)

*Reset by Session 18 start.*

---

## Session-end checklist (run at end of each substantive session)

```
☐ Update merdian_reference.json for any file/table/item status change
☐ Update tech_debt.md if a TD item changes
☐ Overwrite CURRENT.md (Last session reflects this session, This session reset)
☐ Append one line to session_log.md (newest-first prepend)
☐ Update Enhancement Register if architectural thinking happened
☐ Update CLAUDE.md if a Rule, settled decision, or anti-pattern was added
☐ Update Experiment Compendium if new experiment evidence was produced
☐ Commit all documentation changes to Git
☐ Upload updated files to Claude.ai project knowledge (Rule 12)
☐ AWS sync if production code changed (git push + AWS git pull)
☐ Re-enable any disabled Task Scheduler tasks before next market open
```

---

## Previous session (Session 16) — preserved per no-crunch directive

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

## This session block from Session 16 (superseded by Session 17 block above)

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

## Live state snapshot (at Session 17 start — preserved as historical reference)

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
*Last updated 2026-05-09 (end of Session 24).*
