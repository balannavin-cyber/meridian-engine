## 2026-04-22 (PM) -- documentation / hygiene -- Session 6: untracked-files triage

**Goal:** Categorize ~50 untracked files in the repo working tree into TRACK / GITIGNORE buckets and commit the result. User preference overrode original TRACK/GITIGNORE/ARCHIVE 3-wave plan into 2-wave (keep on disk, out of git).

**Session type:** documentation / hygiene

**Completed:**
- Wave 1 TRACK: 6 files committed at `48fbf24` -- Documentation Protocol v3, Testing Protocol v1, Master V19, AppendixV18G, AppendixV18H_v2, misplaced session note
- Wave 2 GITIGNORE: 45 at-root debris files covered by 15 leading-slash anchored patterns at `f8a3888` -- /add_*.py /append_*.py /backtest_*.py /check_*.py /debug_*.py /experiment_*.py /fix_*.py /fix_*.ps1 /patch_*.py /update_*.py /create_preopen_task.ps1 /merdian_morning_start.ps1 /watchdog_task.xml /watchdog_task_fixed.xml /enhancement_register_entries_20260420.md
- Final `git status --porcelain` empty -- working tree clean, 2 commits ahead of origin
- First live NIFTY signal captured mid-session at 10:55 IST -- BULL_FVG BLOCKED CONF 32; not acted on during triage session per Rule 3 (one concern)
- Pine Script v20260421 inspected post-upload -- confirmed omits H-timeframe zones despite OI-27 landing them in DB; flagged as candidate TD-011 for Session 7+

**Open after session:**
- Missed-signal investigation (10:55 NIFTY BULL_FVG CONF 32 with breadth COV 0%) -- Session 7 goal
- AWS shadow runner FAILED since 2026-04-15 -- Session 8 candidate
- TD-011 Pine generator 1H zone omission -- Session 7 intake
- V19B appendix for Sessions 3+4 -- deferred to dedicated session
- ENH-60 single-line pre-init fix -- deferred
- Push to origin -- deferred

**Files changed:** `.gitignore` (+18 lines)
**Files added (tracked):** `docs/operational/MERDIAN_Documentation_Protocol_v3.md`, `docs/operational/MERDIAN_Testing_Protocol_v1.md`, `docs/masters/MERDIAN_Master_V19.docx`, `docs/appendices/MERDIAN_AppendixV18G.docx`, `docs/appendices/MERDIAN_AppendixV18H_v2.docx`, `docs/session_notes/session_log_entry_20260417_18.md`
**Schema changes:** none
**Open items closed:** none (hygiene session)
**Open items added:** candidate TD-011 (Pine 1H omission) -- not yet in tech_debt.md, intake deferred
**Git commit hashes:** `48fbf24` (Wave 1), `f8a3888` (Wave 2)
**Next session goal:** Investigate missed NIFTY signal at 10:55 IST -- determine if CONF 32 block was legitimate or breadth-coverage artifact
**docs_updated:** yes

---

## Session log — v3 canonical one-liners (newest first)

2026-04-28 · `pending` · Session 12 (documentation/philosophy -- gamma dashboard analysis + ADR-002 + register overhaul): Gamma dashboard built by a successful options writer (short-gamma seller) analysed against MERDIAN Gamma Engine. Six structural gaps identified: (1) MERDIAN stores scalar GEX metrics only -- no per-strike histogram, so pin zones, acceleration zones, and local vs aggregate divergence are all invisible; (2) binary LONG/SHORT regime based on net_gex sign misclassifies PINNED sessions where local GEX around spot is strongly positive but net GEX is negative -- documented in Appendix D, Exp 23 is the validation path; (3) no acceleration zone as a first-class engine output (flip level stored but not the zone above it where short-gamma writers are trapped); (4) direction only, no force -- dealer Cr flow magnitude is the actual edge, not regime label; (5) no regime velocity -- max gamma migration and gex_velocity are untracked; (6) DTE used as binary execution gate only, not as force multiplier. ADR-002 authored (docs/decisions/ADR-002-market-structure-philosophy.md): six principles P1 (zones not points), P2 (force not direction), P3 (know where sellers panic), P4 (regime velocity), P5 (local beats aggregate), P6 (DTE is force multiplier). Capital scaling roadmap settled: Phase 1 = naked options buying (~25,000 lot capacity ceiling before market impact), Phase 2 = debit spreads at ceiling, Phase 3 = defined-risk selling (NOT naked) requiring full P1-P5 implementation first. GEX weekly time-series storage decision: store per-strike GEX at 5-min cadence across full expiry week -- data already in option_chain_snapshots, aggregation only, ~15,600 rows/day. ENH-80 (per-strike GEX time-series + zone bounds -- PROPOSED), ENH-81 (dealer flow simulator + regime velocity -- PROPOSED), ENH-82 (PINNED gamma regime -- PROPOSED, blocked on Exp 23), ENH-83 (DTE-adjusted force multiplier -- PROPOSED, deferred Phase 1.5+) filed. Build sequencing locked: ENH-75 → ENH-80 → ENH-81 → Exp 23 → ENH-82 → ENH-83. MERDIAN_Enhancement_Register.md rewritten as single unified file covering ENH-01 through ENH-83 (prior file was fragmented with multiple delta/appendix sections appended). merdian_reference.json bumped to v7: Session 12 change_log entry, ADR-002 file registered, gex_strike_snapshots PROPOSED table added with DDL, gamma_metrics proposed new columns documented, governance rules added for ret_30m percentage points (Rule 14), Supabase 1000-row cap (Rule 15), bar_ts TZ workaround (Rule 16), ADR-002 principles, capital scaling roadmap. NOTE: ENH-75 (PO3 live detection -- Session 12 primary build target) was NOT built. Session fully consumed by Item A (gamma dashboard discussion deferred from Session 11). ENH-75 is Session 13 primary. · docs_updated:yes
2026-04-28 · `pending` · Session 11 (single concern — ICT research agenda): Full experimental session. 11 experiments run (Exp 34–41B). Concern: identify new intraday and multi-day edges by testing ICT liquidity concepts (BSL/SSL, PO3/AMD, weekly HTF context) against 12 months of NIFTY/SENSEX bar data. 7 edges proven, 4 concepts ruled out. Key findings: (1) Naked PDH/PDL sweeps = FAIL (Exp 34, WR=11%). (2) PDH first-sweep filtered = 93.3% bearish EOD WR (Exp 35C PASS, N=15). (3) PDL first-sweep filtered = 72% bullish EOD (Exp 35C PASS, N=25). (4) PDH DTE<3 → current-week PE: T+1D WR=72.7%; current-week beats next-week (mean +125% SENSEX, Exp 35D PASS). (5) BEAR_OB MIDDAY + PO3_BEARISH = 88.2% T+30m WR, +39pp lift, EV=116.5pts SENSEX / 16.8pts NIFTY (Exp 40 PASS — highest new signal). (6) BULL_OB AFTERNOON + PO3_BULLISH (SENSEX only) = 64.5% WR, +17pp lift, EV=35.5pts (Exp 40 PASS; NIFTY 50% → discarded). (7) PWL refined weekly sweep = 76.9% EOW, T+2D mean +534pts SENSEX (Exp 39B PASS). (8) PWL weekly + daily PDL confluence = 100% conf-day WR (N=5 — highest conviction). Ruled out: PO3 as OB amplifier (Exp 36 FAIL), London kill zone combined (Exp 37 partial — 13:30-14:00 BEAR_OB 77.8% promising), weekly sweep unrefined (Exp 39 FAIL). Core structural insight: PO3 sweep = session bias setter only; trade is BEAR_OB MIDDAY (bearish sessions) or BULL_OB AFTERNOON SENSEX (bullish sessions). MAE analysis (Exp 41): MAE P90=94pts NIFTY / 373pts SENSEX — SENSEX short-DTE options not viable at sweep entry. Entry timing: T+0 always beats waiting. ret_30m stored as percentage points (÷100 for decimal). Kelly fractions capped at 5-8% until N=30 live events. TradingView examples produced (pull_edge_examples.py + MERDIAN_Edge_Examples_Session11.docx). New ENH: ENH-75 (PO3 live detection), ENH-76 (BEAR_OB MIDDAY gate), ENH-77 (BULL_OB AFTERNOON gate SENSEX), ENH-78 (DTE<3 PDH current-week PE rule), ENH-79 (PWL weekly swing detection). Bugs fixed in all scripts: is_pre_market column absent, Supabase 1000-row cap, TD-029 timezone replace(tzinfo=None). · EXPERIMENTS_RUN=11 · EDGES_FOUND=7 · docs_updated:yes
2026-04-28 · `46dbdc1` · Session 11 EXTENSION (post-market, multi-concern override logged): F3 SHIPPED — `build_ict_htf_zones.py` instrumented with ENH-71 ExecutionLog (`fix_f3_instrument_build_ict_htf_zones_v3.py`); `MERDIAN_ICT_HTF_Zones_0845` Task Scheduler registered (daily Mon-Fri 08:45 IST); 3 SUCCESS rows in `script_execution_log` (DRY_RUN + manual 35 zones + Start-ScheduledTask smoke test 35 zones, all `contract_met=true`). TD-017 CLOSED. TD-032 PATCHED — root cause confirmed: `build()` read `opt_type` from `ict_zones.opt_type` (ICT pattern direction before ENH-35 gate overrides); on LONG_GAMMA days gate overrides bullish ICT to BUY_PE — dashboard rendered CE. Fix: `opt_type` unconditional from `signal_snapshots.action`; render audit log `[DASHBOARD]` lines to stderr per page load. Patch `fix_td032_dashboard_opt_type_v2.py`. Pending 10-cycle live verification 2026-04-29. Candidate G: `.gitignore` audited — `/fix_*.py` + `/fix_*.ps1` over-broad rules removed; `preflight/output/` silenced; garbage entries removed; 58 files committed (40+ historical fix/check scripts entering git for first time). TD-030 CLOSED — `recheck_breached_zones()` added to `build_ict_htf_zones.py`; runs after OHLCV load, marks mitigated ACTIVE zones BREACHED. TD-031 CLOSED — breach filter split: OB/FVG written unconditionally; PDH/PDL still proximity-filtered; 72 zones written (was 35). ENH-46-D PARTIAL — `generate_pine_overlay.py` generator shipped (proximity tier system: T1=full opacity within 2% of spot, T2=medium 2-5%, T3=ghost >5%); `/download_pine` dashboard endpoint + PINE OVERLAY button added. Live session 09:15 IST: FIRST EVER gate open — SENSEX `trade_allowed=true` fired + Telegram delivered. Found: `wcb_regime=NULL` all session (regression to 2026-03-19, only 32/2171 rows ever populated); `direction_bias=BEARISH` while `breadth_regime=BULLISH` — signal untrustworthy, operator correctly did not trade. Exit timer displaying UTC not IST in EXIT AT label (TD-038 filed). SENSEX DTE=2 on expiry day 04-28 (TD-039 filed). Encoding lessons: BOM → `decode(utf-8-sig)`; CRLF → `write_bytes`. · PASS · docs_updated:yes
2026-04-27 · `15720d6` · Session 10 (single concern with Monday-morning operational tail and post-market research extension): Diagnosis of "MERDIAN never shows trade_allowed on trending days" landed at three findings (F0 gate visibility, F1 detector TZ classification, F2 1H threshold) plus operational pre-open work plus full live-trading-day verification plus Experiment 33 inside-bar-before-expiry research. F0 SHIPPED — `fix_enh35_unclobber_direction_bias.py` removed direction_bias/action clobber from LONG_GAMMA/NO_FLIP branches in `build_trade_signal_local.py`; **verified live across multiple cycles 09:30-15:30 IST** (NIFTY direction_bias=BEARISH consistently throughout morning, both blocked correctly via trade_allowed=false). F1 SHIPPED — `fix_ict_time_zone_utc.py` patched `time_zone_label()` in `detect_ict_patterns.py` to convert UTC→IST before classification; **verified live across two of five buckets** (OPEN at 09:21/09:28 IST classified correctly; MORNING at 10:16 IST classified correctly). F2 REJECTED via Exp 29 v2 (full year, 0.40% threshold maximises WR; lower thresholds destroy edge). Five experiments run: Exp 29 v2 falsified F2; Exp 31 + Exp 32 produced false-negative replication results (later corrected); Exp 15 re-validation (run AS-IS, full year) confirmed compendium replicates: BEAR_OB 92.0% WR / BULL_OB 83.7% / MEDIUM context 77.3% / combined T+30m total ₹+773,442 / +193.4% capital growth (NIFTY +180%, SENSEX +206%, max DD 1.3%/3.1%); Exp 33 (extension) tested inside-bar-before-expiry breakout/breakdown thesis — N=14 across NIFTY+SENSEX weekly+monthly buckets, 93% break rate, 71% next-day continuation, 93% mid-of-range close, pin thesis REJECTED (only 7% pin rate), breakout thesis SUPPORTED, novel finding next-week ATM > same-week ATM as trade structure due to next-day continuation gap. The detour through Exp 31/32 was a measurement error (5+ structural divergences from research methodology) — explicit retraction logged. ENH-46-A daemon caught real contract violation 10:25 IST (capture_spot_1m wrote market_spot_snapshots but missed hist_spot_bars_1m on single cycle, recovered next minute) — Telegram-alerted within 2 minutes — **first-day production value of Session 9's daemon work demonstrated**. ENH-46-C PROPOSED (conditional ENH-35 lift on BULL_OB inside MEDIUM/VERY_HIGH MTF context, design + 10-session shadow before live) — **subsequently BLOCKED on TD-032 dashboard reliability fix**. ENH-46-D PROPOSED (Pine HTF zones live JSON feed, eliminates manual regeneration after every zone change). ENH-47 PROPOSED (Inside-bar-before-expiry next-week ATM long-options trade structure, sourced from Exp 33; discretionary use first, automation last). Operational pre-open Monday 04-27: Zerodha token refreshed (Kite auth verified at 06:58 IST after debugging heredoc-corruption + SSM TTY hang); HTF zones rebuilt via 2x `build_ict_htf_zones.py --timeframe both`; 2 zombie W BULL_FVG zones manually marked BREACHED (NIFTY 24,074, SENSEX 77,636); Pine overlay regenerated initially incomplete (5 of 18 active zones), regenerated again with full 18 zones per symbol after discovery at 08:55 IST; runbook_update_kite_flow.md updated with two new failure modes. **Critical extension finding: dashboard rendering inconsistent with DB ground truth across multiple observed cycles.** At 11:21 IST dashboard showed "Strike 24,100 CE / premium ₹85" while signal_snapshots had `direction_bias=BEARISH, action=BUY_PE, atm_strike=24050`. At 11:38 IST dashboard rendered "▲ BUY CE / Strike 24,000 CE" while DB had `direction_bias=BEARISH, action=BUY_PE`. Pattern non-deterministic across cycles. F0's unclobber unmasked a dashboard bug that has presumably existed for weeks (pre-F0 the NEUTRAL clobber masked it). Filed as TD-032 — **BLOCKER FOR ENH-46-C SHIP** (cannot promote conditional gate lift to live trade_allowed=true while operator-facing dashboard can show wrong instrument). Filed TD-029 (S2 hist_spot_bars TZ era), TD-030 (S2 build_ict_htf_zones doesn't re-eval breach), TD-031 (S2 D BEAR detection underactive), TD-032 (S2 dashboard ↔ DB inconsistency, BLOCKER), TD-033 (S3 dashboard label conflation), TD-034 (S2 hist_atm_option_bars_5m undersampled on dte=0, ~22-44% coverage), TD-035 (S3 wcb_regime NULL routing), TD-036 (S3 confidence_score flat-line), TD-037 (S4 schema column-name inconsistency). Pending: project knowledge re-upload per Documentation Protocol v3 Rule 12. · PASS · docs_updated:yes
2026-04-26 · `<hash>` · Session 9 (two waves): WAVE 1 -- TD-019 CLOSED end-to-end. Diagnosed cause was *neither* of the originally hypothesised candidates -- `build_spot_bars_mtf.py` was uninstrumented AND never bound to Task Scheduler. Three changes delivered (override of no-fix-in-diagnosis-session rule logged): (1) ENH-71 instrumented via `fix_td019_instrument_build_spot_bars_mtf.py` + `fix_td019_add_sys_import.py` (both ast.parse validated); (2) backfilled 7 trading days = 42,324 5m + 14,440 15m rows in 116s; (3) registered `MERDIAN_Spot_MTF_Rollup_1600` Task Scheduler task -- daily 16:00 IST Mon-Fri -- smoke-tested. Q-A pattern (`actual_writes::text LIKE '%<table>%'`) established as canonical detector for uninstrumented producers. Filed TD-023, TD-024, TD-025, TD-026. WAVE 2 -- triggered by operator concern "never seen a trade unblocked in weeks". Q-022 sequence (1,017 BUY_PE rows + 1 BUY_CE in 21 days, only 3 trade_allowed=true) led to: (a) TD-020 REFRAMING -- Session 8's "gate had no signals to filter" close was wrong, gate FIRED on every 04-24 cycle as designed (LONG_GAMMA branch sets direction_bias=NEUTRAL AS PART of firing); (b) TD-022 closed as duplicate of TD-020 (ICT subsystem innocent; detector ran 404 cycles + wrote 3 ict_zones rows on 04-24 + enrich_signal_with_ict correctly returned NONE because action=DO_NOTHING upstream); (c) Exp 28 ran -- gate correct on ~90% of cycles, mis-calibrated on 8 (date,symbol) pairs across 5 dates with cleanly-directional EOD moves >0.5% (down: 03-11, 04-09, 04-16, 04-20, 04-24; up: 04-07, 04-13, 04-21); (d) Exp 28b ran -- `or_range_pct >= 0.55%` (opening-range expansion 09:15-09:29 as % of open) catches 8/14 DIRECTIONAL with 0/10 false positives on cleaned NOISE set, but underpowered (N=24); needs out-of-sample; (e) ENH-46-A SHIPPED end-to-end -- patched `merdian_pipeline_alert_daemon.py` to also poll signal_snapshots and Telegram-alert on `action != DO_NOTHING AND trade_allowed = true` via `fix_enh46a_signal_alerts.py` + follow-up `fix_enh46a_init_bug.py` (init was unreachable on warm starts); daemon relaunched (PID 19636); verified end-to-end with synthetic INSERT (Telegram delivered). Filed TD-027 (alert daemon scope drift, S4), TD-028 (`merdian_pm.py` silent fail on unknown name + on `status`, S3). ENH-46-B PROPOSED, deferred. Pending: ENH-46-A + Exp 28/28b paste-in blocks for v7 register / Compendium (text generated; not in upload set). · PASS · docs_updated:yes
2026-04-23 · `48d1b6e` · Session 7: breadth cascade root cause CLOSED (C-09 equity_intraday_last stale 27 days -> refresh_equity_intraday_last.py on AWS 09:05 IST cron) + TD-014 breadth writer instrumentation + runbook_update_kite_flow filled + CLAUDE.md v1.3 Rule 13 data contamination registry + C-10 OPEN Kite token propagation manual (Session 9 candidate) · PASS · docs_updated:yes
2026-04-22 · `90b8c2d` · close 6 OIs + v1.1 adoption + tech_debt TD-007/008/009 + ENH-72 register fix shipped · PASS · docs_updated:yes
2026-04-21 · `7bfa6f3` · ENH-72 propagation 9/9 + OI-24/26/27 fixes + Phase 1/2/3 ops (spot backfill, ICT HTF rebuild, Task Scheduler repair) · PASS · docs_updated:yes
2026-04-20 · `e95002b` · outage root cause + ENH-66/68/71 + ENH register unification + 7-script holiday-gate propagation · PASS · docs_updated:yes

---

*Entries above this line follow Documentation Protocol v3 one-liner format. Entries below are legacy v2-protocol block entries retained as audit detail. For new sessions, add a one-liner above; do not add new block entries.*

---

## 2026-04-22 — engineering / operations — Session 5: OI series permanent closure (6 OIs closed) + PS 5.1 encoding fix

**Goal:** Close all 6 open OI items (18, 19, 20, 21, 22, 23) carried forward from Session 3+4 resume prompt, so the OI-* namespace can be permanently retired per Documentation Protocol v2 Rule 5 (`no_new_oi_register`). Each closure to be surgical, single-purpose, with ast.parse() validated patch scripts per V18H governance.

**Session type:** engineering / operations

**Completed:**

OI-22 CLOSED — Dhan transient-failure vs auth-failure alert routing (commit d130044, preceded by 2b6e2bb short commit):
- Root cause: `AUTH_FAILURE_PATTERNS` in `run_option_snapshot_intraday_runner.py` included the substring `"accessToken"`, which matched any ingest stdout/stderr that printed request headers during transient network timeouts. Result: transient timeouts produced `OPTION_AUTH_BREAK` Telegram alerts, falsely suggesting a token refresh was required.
- Fix: removed `"accessToken"` from `AUTH_FAILURE_PATTERNS`. Added new `TRANSIENT_FAILURE_PATTERNS` list (ReadTimeout, ConnectTimeout, ConnectionError, Max retries exceeded, HTTPSConnectionPool, Read timed out, Connection aborted) and `_is_transient_failure()` helper. Dispatcher now checks transient first; issues distinct `OPTION_TRANSIENT_FAIL` alert that explicitly tells the operator NOT to refresh the token. Auth path retightened to "Dhan 401 / token invalid" wording.
- Patch script: `fix_oi22_transient_vs_auth.py` with ast.parse() guard.

OI-23 CLOSED — MERDIAN_SIGNAL_V4 docstring/code default drift (commit 873a866):
- Code default is `"1"` (V4 on) since commit e986cbb post-ENH-53/55 validation. Docstring block in `build_trade_signal_local.py` lines 59-64 still said "Default is off. Enable explicitly for shadow sessions. Flip default only after 5 clean shadow sessions per Change Protocol."
- Fix: rewrote the Flag comment block to document current state (default "1", V3 escape hatch via `MERDIAN_SIGNAL_V4=0`). No code change.
- Patch script: `fix_oi23_signal_v4_docstring.py`.

OI-20 CLOSED — PS 5.1 UTF-8 BOM injection into git commit subjects (commit 93d2d80, disposition note at `docs/session_notes/20260422_oi20_encoding_disposition.md`):
- Finding: commits 3a22735 through d15c494 (9 Session 3+4 commits) carry literal UTF-8 BOM (`EF BB BF`) bytes embedded in commit subjects, confirmed via `git log --format="%s" | Format-Hex`. Not a display artifact.
- Root cause: PowerShell 5.1 default console encoding is cp850 / cp1252 (WindowsCodePage=1252). When `git commit -m "..."` received a message containing non-ASCII (em-dash —), PS 5.1's pipeline transcoding emitted UTF-8-WITH-BOM and git stored the bytes verbatim. `i18n.commitEncoding` was unset.
- Disposition: history NOT rewritten. Force-push cost across Local + MERDIAN AWS + MeridianAlpha consumer exceeds benefit for cosmetic BOMs. Commit hashes preserved as audit trail.
- Fix forward: PowerShell `$PROFILE` created at `C:\Users\balan\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` forcing `$OutputEncoding`, `Console.OutputEncoding`, `Console.InputEncoding` to `UTF8Encoding::new($false)` — UTF-8 without BOM. Git global config: `i18n.commitEncoding=utf-8`, `i18n.logOutputEncoding=utf-8`. Verification commit confirmed no BOM (subject starts at byte `4F`, not `EF BB BF`).
- Residual limitation documented: PS 5.1 still cannot pass non-ASCII characters through `-m "..."` argv serialization (em-dash degraded to `?`). Going-forward discipline: ASCII only in commit subjects, or use `git commit -F message.txt` for non-ASCII.

OI-19 CLOSED — Out of scope (commit 7a4bae5, disposition note at `docs/session_notes/20260422_oi19_out_of_scope.md`):
- Resume prompt carried OI-19 as "MeridianAlpha kernel reboot (non-urgent)".
- Disposition: MeridianAlpha is a separate system from MERDIAN (separate repo, scope limited to corporate actions data and Zerodha token refresh per V19 §3.1). Its host-level maintenance is not tracked in the MERDIAN register. No action required; item should not have been filed under MERDIAN OI.

OI-18 CLOSED — Dashboard preopen false-negative (commit 6917094):
- Investigation disproved the resume-prompt framing ("capture_spot_1m doesn't set is_pre_market=true on pre-open bars"). Live SQL confirmed pre-open bars at 09:05 and 09:14 IST are written correctly to `hist_spot_bars_1m` with `is_pre_market=false`. Every consumer across the codebase (ICT detection, MTF bars, HTF zones, experiments) queries `.eq("is_pre_market", False)`. The `is_pre_market` column is effectively vestigial — always False writer-side, always filtered on False consumer-side.
- Actual root cause (two bugs in `merdian_live_dashboard.get_preopen_status()`): (a) `sb_get("market_spot_snapshots", "select=ts,spot,symbol&order=ts.asc&limit=10")` returned the 10 oldest rows in an ever-growing table, not today's rows — permanent NOT CAPTURED after day one; (b) window filter `dt.hour == 9 and dt.minute < 9` covered 09:00-09:08 only, missed the 09:14 bar.
- Fix: query today's rows via `ts>=start-of-IST-day UTC ISO` lower bound, widen window to `dt.minute < 15` (pre-open closes at market open 09:15), return up to 6 rows instead of 3.
- Not fixed (deliberate): the vestigial `is_pre_market` column. Deferred as a separate cleanup opportunity outside this OI closure.
- Patch script: `fix_oi18_dashboard_preopen.py`.

OI-21 CLOSED — refresh_dhan_token hardening (commit f7b9366):
- Investigation disproved the resume-prompt framing ("silent fail when invoked by Task Scheduler"). Post-OI-16 scheduled task runs succeed: LastTaskResult=0 at 2026-04-21 18:15:06, `runtime/token_status.json` shows `success: true, refreshed_at_iso: 2026-04-21T18:15:07.661476+05:30`. Historical `'python' is not recognized` entries in `logs/dhan_token_refresh.log` are pre-OI-16 ghosts already resolved by absolute Python path fix.
- Residual real bug in `refresh_dhan_token.py` main() retry path: line showed `print("...Waiting 30s...")` but `_time.sleep(120)`. The 120-second sleep matched Dhan's 2-minute token-generation rate-limit window exactly; the retry landed on the boundary and frequently tripped the `"Token can be generated once every 2 minutes"` error. This internal cascade accounted for the rate-limit entries observed in the log.
- Three fixes applied: (1) retry sleep 120s → 30s (one TOTP window, well under rate-limit boundary); (2) idempotency guard at main() entry — reads `token_status.json`, if last success < 90s old prints `[IDEMPOTENT]` and returns 0 without calling Dhan, protects against any double-caller (scheduled task + dashboard button at line 57 of `merdian_live_dashboard.py` + TOTP retry self-fire + preflight stages); (3) explicit rate-limit handling in both first-attempt and retry paths — writes `token_status.json` with error, returns distinct exit code 2 (recently-refreshed-elsewhere, not a failure).
- Patch script: `fix_oi21_token_refresh_hardening.py`.

**Governance outcome:**

- All 6 OIs (OI-18 through OI-23) from Session 3+4 resume prompt are now CLOSED. The OI-* namespace is permanently retired per Documentation Protocol v2 Rule 5 (`no_new_oi_register`, governance rules line 1664 of `merdian_reference.json`). Future operational issues route to Enhancement Register (ENH-N, persistent) or `merdian_reference.json` `open_items` C-N (critical production) only.
- Confirmed during this session: Session 3+4 OI-16/17/24/25/26/27 entries in session_log were never formally added to `merdian_reference.json` `open_items` — consistent with Rule 5. They functioned as session-local labels for tracked work, not persistent register entries. Same disposition applies to OI-18/19/20/21/22/23: session-local labels, closed within the same session, no register entry required.

**Open after session:**
- Documentation debt closeout (this session's primary next step):
  - V19A appendix — consolidated coverage of Session 1+2 (2026-04-20: ENH-66/68/71 outage + architecture) + Session 3+4 (2026-04-21: ENH-72 + OI-24/26/27 fixes + backfill + ICT rebuild + Task Scheduler repair) + Session 5 (2026-04-22: 6 OI closures + PS 5.1 encoding fix). Per user direction, post-V19 appendices use V19A / V19B / V19C naming, not V18I/J/K.
  - Enhancement Register overhaul (on-disk v7 stops at ENH-59, missing ENH-60 through ENH-74+). New version to reconcile.
- Session 6 (ENH-74): live config rebuild — NOT STARTED
- Session 7 (ENH-67/69/73): dashboard + alerts — downstream

**Files changed (core/):**
- `run_option_snapshot_intraday_runner.py` (OI-22: transient vs auth split)
- `build_trade_signal_local.py` (OI-23: docstring alignment, no code change)
- `merdian_live_dashboard.py` (OI-18: get_preopen_status rewrite)
- `refresh_dhan_token.py` (OI-21: retry sleep, idempotency guard, rate-limit handling)

**Files added (patch scripts + disposition notes):**
- `fix_oi22_transient_vs_auth.py`
- `fix_oi23_signal_v4_docstring.py`
- `fix_oi18_dashboard_preopen.py`
- `fix_oi21_token_refresh_hardening.py`
- `docs/session_notes/20260422_oi20_encoding_disposition.md`
- `docs/session_notes/20260422_oi19_out_of_scope.md`

**Environment changes:**
- PowerShell profile created: `C:\Users\balan\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` — enforces UTF-8 without BOM on all three encoding channels.
- Git global config: `i18n.commitEncoding=utf-8`, `i18n.logOutputEncoding=utf-8`.

**Schema changes:** none

**Open items closed (6):** OI-18, OI-19, OI-20, OI-21, OI-22, OI-23

**Open items added / diagnosed:** none (OI namespace retired)

**Git commit chain (Session 5):** `2b6e2bb` → `d130044` → `873a866` → `93d2d80` → `7a4bae5` → `6917094` → `f7b9366`

**Next session goal:** Write V19A appendix consolidating all post-V19 work (three sessions: 2026-04-20, 2026-04-21, 2026-04-22) per 13-block structure + attached session-documentation checklist. Self-review for completeness across sessions before commit.

**docs_updated:** yes (this entry + `docs/session_notes/20260422_oi19_out_of_scope.md` + `docs/session_notes/20260422_oi20_encoding_disposition.md`)

---

## 2026-04-21 — engineering / operations — Session 3+4: ENH-72 propagation (9 of 9) + backfill + ICT rebuild + Task Scheduler repair + ICT pipeline cleanup

**Goal:** Complete ENH-72 (ExecutionLog write-contract) propagation to all 9 critical pipeline scripts. In parallel: backfill missing spot bars (04-16/17/20), rebuild ICT HTF zones, regenerate Pine Script, fix MERDIAN_Dhan_Token_Refresh task config, diagnose dashboard "NOT CAPTURED" false negative. Late-session pivot: close three high-value bug fixes surfaced by working ExecutionLog instrumentation (OI-24 ICT schema mismatch, OI-26 broken expiry lookup, OI-27 1H zones never triggering).

**Session type:** engineering / operations

**Completed:**

ENH-72 ExecutionLog propagation (9 of 9 targets — programme COMPLETE):
- Target 1: ingest_option_chain_local.py — commit 3a22735 (Session 2 carry-over)
- Target 2: compute_gamma_metrics_local.py — commit d676a73 + set_symbol() helper
- Target 3: compute_volatility_metrics_local.py — commit 2173002
- Target 4: build_momentum_features_local.py — commit 74e15a0
- Target 5: build_market_state_snapshot_local.py — commit 70df409
- Target 6: build_trade_signal_local.py — commit b3d88fa (signal engine, ict_failed/enh06_failed flags, action in notes)
- Target 7: compute_options_flow_local.py — commit 1e75a74 (no-arg batch, floor=1 for partial success)
- Target 8: ingest_breadth_intraday_local.py — commit dd66076 (4-layer guard preserved, CalendarSkip→HOLIDAY_GATE)
- Target 9: detect_ict_patterns_runner.py — commit f121fca (floor=0, non-blocking exit 0 preserved, schema bugfix)
- Live production validation across targets 1-5 during 2026-04-21 trading day: 1,871 invocations, 5 failures, ~99.7% clean rate

Phase 1 — hist_spot_bars_1m backfill (2026-04-21 ~17:28 IST):
- Identified: 04-20 had 260 garbage rows with shifted timestamps (11:09-20:38 IST); 04-16/17 missing entirely
- Deleted 520 bad rows for 04-20
- Recovered backfill_spot_zerodha.py from Local via scp to MeridianAlpha (file wiped by failed nano edit, recovered via sed)
- Ran Kite backfill: 2,250 rows written (3 dates × 2 symbols × 375 bars), all 09:15-15:29 IST

Phase 2 — ICT HTF zone rebuild + Pine Script regeneration (~17:34 IST):
- build_ict_htf_zones.py processed 249 daily bars per symbol (full year)
- 35 zones written, 10 active per symbol after expiry filter
- NIFTY: D PDH 24,470, D PDL 24,311+24,231, fresh W BULL_FVG 24,074-24,241 (Apr 17)
- SENSEX: D PDH 78,944, D PDL 78,364+78,193, fresh W BULL_FVG 77,636-78,203 (Apr 17)
- Pine Script regenerated with updated zones and flip-to-support annotations

Phase 3 — Task Scheduler repair + dashboard diagnosis (~18:00 IST):
- MERDIAN_Dhan_Token_Refresh task config fix: Set-ScheduledTask with absolute Python path + WorkingDirectory
- Manual trigger verified 18:03:58 LastTaskResult=0; interactive refresh at 18:10 confirmed new token
- MERDIAN_PreOpen task config verified correct; task fires at 09:05 with exit 0
- Dashboard "NOT CAPTURED" diagnosed as false negative: capture_spot_1m.py writes data correctly but does NOT set is_pre_market=true flag; dashboard filters on that flag

Late-session fixes (ENH-72 instrumentation surfaced these hidden bugs):
- OI-24 CLOSED: detect_ict_patterns_runner.py load_atm_iv() was reading non-existent market_state_snapshots.market_state column. Original sys.exit(0) tail block had been silently masking this in production. Fixed to read volatility_features.atm_iv_avg directly. Commit f121fca (in the Target 9 ENH-72 commit).
- OI-26 CLOSED: merdian_utils.build_expiry_index_simple had hardcoded sample_dates [2025-04..2026-03]. On 2026-04-21 it returned stale historical expiries; nearest_expiry_db fell through to expiry_index[-1] producing SENSEX dte=-54d and NIFTY dte=252d. Replaced with get_nearest_expiry(sb, symbol) reading option_chain_snapshots.expiry_date (authoritative Dhan-sourced value, includes NSE holiday-driven shifts). Old functions kept DEPRECATED for audit trail. ENH-63 expiry index cache retired. Commit 49c5e3c.
- OI-27 CLOSED: ict_htf_zones had ZERO rows with timeframe='H' in its entire history. Two independent bugs: (a) is_hour_boundary() gated on minute<3, production runner cycles never landed in that window, (b) `if __name__ == "__main__": main()` positioned mid-file in build_ict_htf_zones.py before detect_1h_zones was defined, crashing CLI --timeframe H. Fix (a): replaced with data-driven should_rebuild_1h_zones(sb, symbol) — checks ict_htf_zones directly, rebuilds once per hour per symbol regardless of cycle schedule. Fix (b): moved __main__ block to end of file. Smoke confirmed 4 1H zones now visible in ict_htf_zones (first time ever). Commit d15c494.

Diagnosed but not fixed:
- OI-25: NIFTY atm_iv=2.5% observed. Investigation traced to BS-solver IV degeneracy on expiry day (NIFTY expired today 2026-04-21 at Tuesday close, last 10 min pricing near-zero extrinsic value → tiny computed IV). NOT a unit mismatch. Pipeline propagates the Dhan-returned raw IV correctly through every stage. V19 §15:00 IST session-time gate in build_trade_signal already prevents any trade decision based on these degenerate values. Cosmetic issue in Kelly lot display on expiry-day afternoons, no production impact.

**Open after session:**
  - Tomorrow: live validation of instrumented scripts (targets 6-9) + 1H zone writing (should fire at 10:00+ IST) + nearest_expiry_db replacement
  - Session 5 (ENH-74): live config rebuild — NOT STARTED
  - Session 6 (ENH-67/69/73): dashboard + alerts — requires C-08 already resolved
  - Documentation debt:
    - V18I appendix (Session 2 ENH-66/68/71)
    - V18J appendix (Session 3 ENH-72 targets 1-5)
    - V18K appendix (Session 4 targets 6-9 + OI-24/26/27 fixes + Phase 1/2/3 ops)
    - Enhancement Register v8 overhaul (v7 on disk stops at ENH-59; missing ENH-60 through ENH-74+)

**Files changed (core/):**
  - compute_gamma_metrics_local.py, compute_volatility_metrics_local.py (Session 3 targets 2-3)
  - build_momentum_features_local.py, build_market_state_snapshot_local.py (targets 4-5)
  - build_trade_signal_local.py, compute_options_flow_local.py (Session 4 targets 6-7)
  - ingest_breadth_intraday_local.py (target 8)
  - detect_ict_patterns_runner.py (target 9 ENH-72 + OI-24 schema fix + OI-26 expiry swap + OI-27 hour trigger)
  - build_ict_htf_zones.py (OI-27 CLI __main__ position fix)
  - merdian_utils.py (OI-26 new get_nearest_expiry function, deprecation markers on old expiry index functions)
  - core/execution_log.py (set_symbol helper added, Session 3)
  - backfill_spot_zerodha.py on MeridianAlpha (BACKFILL_DATES updated)

**Schema changes:** none

**Open items closed (6):**
  - OI-16 CLOSED — MERDIAN_Dhan_Token_Refresh task config fixed via Set-ScheduledTask with absolute paths
  - OI-17 CLOSED — hist_spot_bars_1m 04-16/17/20 backfilled (2,250 rows)
  - OI-24 CLOSED — detect_ict_patterns_runner load_atm_iv schema bug (fixed in commit f121fca)
  - OI-26 CLOSED — nearest_expiry_db broken DTE, replaced by get_nearest_expiry reading option_chain_snapshots (commit 49c5e3c)
  - OI-27 CLOSED — 1H zone detection never triggered, data-driven rebuild + CLI __main__ fix (commit d15c494)

**Open items added / diagnosed (5 remain):**
  - OI-18 — capture_spot_1m.py does not set is_pre_market=true flag for pre-open bars
  - OI-19 DEFERRED — MeridianAlpha pending kernel reboot, non-urgent
  - OI-20 COSMETIC — UTF-8 BOM prefix in Session 3+4 commits
  - OI-21 — refresh_dhan_token.py silent fail when invoked via Task Scheduler
  - OI-22 — Telegram alert wording misleading for transient Dhan timeouts
  - OI-23 — MERDIAN_SIGNAL_V4 docstring/code drift
  - OI-25 DIAGNOSED (not a bug) — NIFTY atm_iv=2.5% is expiry-day BS-solver IV degeneracy, gated downstream by V19 §15:00 session cutoff

**Git commit hashes (Session 3+4 full chain):** 3a22735 → d676a73 → 2173002 → 74e15a0 → 70df409 → b3d88fa → 1e75a74 → dd66076 → f121fca → 49c5e3c → d15c494

**Next session goal:** Tomorrow morning validation window 09:15-11:00 IST. Verify: (a) all 9 instrumented scripts produce SUCCESS rows in first live cycle, (b) 1H zones fire at ~10:00 IST boundary (first hourly rebuild), (c) Kelly lots sizing shows realistic counts for SENSEX (NIFTY will cycle back to real IV once new weekly is current). Then either begin Session 5 (ENH-74 live config) or start documentation debt closeout (V18J/V18K appendices + Enhancement Register v8).

**docs_updated:** yes (this entry + enhancement_register_delta_20260421.md)

---
## 2026-04-20 — live_canary / code_debug / architecture — Outage + re-engineering programme Sessions 1+2

**Goal:** Diagnose and fix the morning's 3-hour silent pipeline outage; ship the architectural foundation (ENH-66 holiday-gate root cause + ENH-68 tactical runner env reload + ENH-71 write-contract layer) to prevent a recurrence of the bug class.

**Session type:** live_canary / code_debug / architecture

**Completed:**
  - **Morning outage diagnosed end-to-end.** 09:15 IST: seven production scripts silently exited "Market holiday" on a trading day. Root cause: V18G holiday-gate logic treats `open_time IS NULL` as "market closed"; `trading_calendar` row auto-inserted by `merdian_start.py` carried `{trade_date, is_open=True}` only — `open_time` and `close_time` NULL. Scripts exited cleanly with code 0. Dashboard, Task Scheduler, supervisor all green. Pipeline flowing zero rows for 3 hours until 11:39 IST when the row was patched live via direct Supabase PATCH.
  - **Second compounding bug surfaced at 11:26 IST.** Dhan token expired ~10:06 IST (OPTION_AUTH_BREAK Telegram alert fired). `refresh_dhan_token.py` updated `.env` at 11:00:10 IST successfully, but the runner process (PID 18036, started 09:15:34) held the stale in-memory token from its startup `load_dotenv()` call. Every cycle 401 from 11:26 to 12:26 IST. Only `merdian_stop.py` + `merdian_start.py` fixed it. 60 additional minutes lost.
  - **Pipeline recovered 12:26+ IST.** NIFTY NO_FLIP DO_NOTHING conf=16, SENSEX NO_FLIP DO_NOTHING conf=28. No bad trades taken during the outage window.
  - **Post-mortem conducted honestly.** Central insight: every symptom traces to ONE absence — MERDIAN has no write-contract enforcement. Scripts declare success by exit code 0; nothing verifies they did their actual job. Preflight probe-tests pass while pipeline is already broken. Dashboard green lights based on "last row wrote recently," not "expected rows wrote this cycle."
  - **6-session re-engineering programme approved.** Sessions 1 through 6 sequenced: stop the bleeding, write-contract layer, propagate, preflight rewrite, live config, dashboard truth + alerts. Each session produces own commit chain, register entry, replay-validation. No merges without validation paste in chat transcript.
  - **Session 1 shipped (ENH-66, ENH-68 tactical).** Two patches, two commits:
    - Commit `8f83859` — ENH-66: `ensure_calendar_row()` in `merdian_start.py` patched at INSERT path (include open_time/close_time for weekday rows) and existing-row PATCH path (backfill NULL times). UTF-8 BOM stripped as side effect. Validation: DELETE calendar row → re-creates with times populated; `capture_spot_1m.py` writes rows instead of silent-exit; regression test `is_open=False` → correct holiday exit.
    - Commit `b195499` — ENH-68 tactical: guarded `load_dotenv(override=True)` at top of `run_full_cycle()` in `run_option_snapshot_intraday_runner.py`. One reload per 5-minute cycle. Log line per cycle for audit trail. Graceful degradation if python-dotenv unavailable. Strategic replacement filed as ENH-74 for Session 5.
  - **Session 2 shipped (ENH-71 write-contract layer foundation).** Commit `260c7d0`. Three deliverables:
    - SQL: `public.script_execution_log` table with closed-set CHECK constraint on `exit_reason` (11 values). Partial indexes on `contract_met=false` and non-SUCCESS rows. View `public.v_script_execution_health_30m` for dashboard/alert consumption. RLS policies.
    - Code: `core.execution_log.ExecutionLog` helper class. API: `record_write(table, n)`, `exit_with_reason(reason, ...)`, `complete(notes)`. Opening row INSERT at construction. Finalise PATCH with computed `contract_met`. `atexit` hook catches crashes → `exit_reason='CRASH'` with traceback. Invalid reasons coerced to CRASH. Best-effort writes; never raises into caller.
    - Reference implementation: `capture_spot_1m.py` converted. Declares `expected_writes={market_spot_snapshots: 2, hist_spot_bars_1m: 2}`. Six exit paths classified.
  - **ENH-71 validated live against Supabase (6 tests).** Empty table + accessible view + CHECK constraint rejected INVALID_REASON; smoke SUCCESS met=True; contract violation (1 of 3) met=False; atexit crash path CRASH; HOLIDAY_GATE early exit met=False; live run of converted `capture_spot_1m.py` SUCCESS met=True 2+2 writes 1114ms. **Replay of today's exact outage**: flipped `is_open=False`, row recorded `reason=HOLIDAY_GATE met=False expected={...: 2, ...: 2} actual={} notes='trading_calendar says closed'`. Today's silent exit is now a dashboard-visible, alertable row.
  - **Enhancement Register updated (commit `7174690`).** Previous commit `ccaa418` had compressed many ENH-01..65 entry blocks when adding ENH-66..74. Recovered via `git checkout HEAD~1 -- ...` to restore full 88107-byte / 1737-line original. Applied `append_enh66_to_74.py` — strictly-additive patch with 7 anchor-validated edits, uniqueness-checked, size-must-grow guard. Net: 1737 → 2049 lines (+312), all ENH-01..65 prose untouched. Added 9 new entry blocks (ENH-66..74), MERDIAN Re-engineering Programme section, 2026-04-20 change log row, trailer update.
  - **AWS synced.** `git pull` on i-0878c118835386ec2 after stash/merge of AWS-local gitignore extensions (commit `22334fb`). Zerodha token patched on MeridianAlpha and pushed to AWS via ssh+sed.

**Open after session:**
  - **ENH-67** (NEW, PROPOSED): `latest_market_breadth_intraday` is a VIEW — dashboard shows stale BULLISH counter while WCB aggregate correctly shows BEARISH. Cosmetic; signal engine uses `wcb_regime` which is correct. Session 6 of programme.
  - **ENH-69** (NEW, PROPOSED): Supervisor staleness threshold (60s) < observed cycle duration (146.6s) → false "Runner not healthy" restart loop. Recommend option 3: richer heartbeat signal. Session 6.
  - **ENH-70** (NEW, PROPOSED): Preflight rewrite — replace import/connectivity probes with dry-run write-contract enforcement. `capture_spot_1m.py --dry-run` would have caught today's bug at 08:53 IST. Session 4. Depends on ENH-71 + ENH-72.
  - **ENH-72** (NEW, PROPOSED): Propagate ExecutionLog to 9 remaining critical scripts (ingest_option_chain, ingest_breadth_intraday, capture_market_spot_snapshot_local, compute_iv_context_local, build_market_spot_session_markers, run_equity_eod_until_done, refresh_dhan_token, build_ict_htf_zones, detect_ict_patterns_runner, build_trade_signal_local). Session 3. ~20 min per conversion once pattern established.
  - **ENH-73** (NEW, PROPOSED): Dashboard truth + alert daemon contract-violation rules. Per-stage RED/AMBER/GREEN from `v_script_execution_health_30m`. Alert rules on `contract_met=FALSE`, `HOLIDAY_GATE` during market hours, cascade detection, freshness. Session 6.
  - **ENH-74** (NEW, PROPOSED): Live config layer — `core/live_config.py` with 30s-TTL-cached function-based accessors replacing all `os.environ[...]` / `os.getenv(...)` reads. Strategic replacement of ENH-68 tactical. Eliminates stale-in-memory bug class. Session 5.
  - **Working tree hygiene**: ~45 untracked scratch scripts (`fix_*.py`, `check_*.py`, `debug_*.py`, `experiment_*.py`, `*.ps1`) accumulated in repo root. Today's patches (`fix_enh66.py`, `fix_enh68.py`, `fix_capture_spot_1m_exec_log.py`, `append_enh66_to_74.py`) joined the graveyard. Candidate ENH-75. Weekend cleanup.
  - **Tomorrow morning verification (≥ 09:00 IST 2026-04-21)**: (1) `merdian_start.py` prints `2026-04-21 -> TRADING DAY (is_open=True) inserted (new row)` with both times populated; (2) runner log shows `ENH-68: .env reloaded for this cycle (override=True)` every 5 min; (3) `script_execution_log` accumulates one `capture_spot_1m.py` row per minute with `exit_reason='SUCCESS'`, `contract_met=True`.

**Files changed:**
  - `merdian_start.py` (ENH-66: ensure_calendar_row() at 2 sites; BOM strip)
  - `run_option_snapshot_intraday_runner.py` (ENH-68: dotenv import + per-cycle reload)
  - `capture_spot_1m.py` (ENH-71: ExecutionLog integration as reference implementation)
  - `docs/registers/MERDIAN_Enhancement_Register.md` (appended ENH-66..74 entries + Programme section)
  - `.gitignore` (AWS-local merge, commit 22334fb)

**Files added:**
  - `core/execution_log.py` (ENH-71: ExecutionLog helper class)
  - `sql/20260420_script_execution_log.sql` (ENH-71: table + view + RLS DDL)

**Schema changes:**
  - NEW TABLE `public.script_execution_log` (15 columns including exit_reason CHECK constraint, expected_writes/actual_writes jsonb, contract_met boolean).
  - NEW VIEW `public.v_script_execution_health_30m` (per-script 30-min rollup).
  - `trading_calendar` row behaviour: auto-inserted weekday rows now carry `open_time='09:15:00'` and `close_time='15:30:00'` (ENH-66).

**Open items closed:** none (existing items)
**Open items added:** ENH-66, ENH-67, ENH-68, ENH-69, ENH-70, ENH-71, ENH-72, ENH-73, ENH-74
**Git commit hash:** 7174690 (HEAD of origin/main after all four commits: 8f83859 → b195499 → 260c7d0 → ccaa418 (superseded) → 7174690)
**Next session goal:** Session 3 of programme — propagate ExecutionLog to `ingest_option_chain_local.py` first (highest write volume; converts today's Dhan 401 failures from log spam to TOKEN_EXPIRED-classified audit rows), then remaining 8 critical scripts in priority order.
**docs_updated:** yes

---

## 2026-04-19 — code_build — ENH-53 + ENH-55 build, validate, promote

**Goal:** Implement ENH-53 (breadth hard-gate removal) + ENH-55 (momentum opposition block) in build_trade_signal_local.py behind MERDIAN_SIGNAL_V4 feature flag, validate via historical replay, promote to default.

**Session type:** code_build

**Completed:**
  - Built V4 logic in build_trade_signal_local.py: new `infer_direction_bias_v4(momentum_direction)` helper; ENH-53 post-action +5 breadth modifier (0 when opposing); ENH-55 post-action opposition block (abs(ret_session) > 0.0005 AND action opposes sign → DO_NOTHING, trade_allowed=False) and alignment bonus (+10 when aligned); old implicit +20 breadth+momentum alignment bonus removed under V4.
  - V3 path preserved bit-identical including known latent quirks: flow-modifier block action-reference, trade_allowed=True DTE override.
  - Feature flag MERDIAN_SIGNAL_V4 read once at module import. Commit 8f70822 (default "0"), commit e986cbb (default "1" post-validation).
  - ast.parse validation passed (ENH-59 compliance) on both build_trade_signal_local.py and backtest_signal_v4.py.
  - Built backtest_signal_v4.py — replays each market_state_snapshots row through build_signal twice (flag off/on), writes side-by-side CSV. Patched wrapper intercepts options_flow_snapshots Supabase queries to return empty, neutralizing the pre-existing UnboundLocalError without modifying the production file. Preserves V3↔V4 delta isolation.
  - NIFTY 2026-03-16/20/24/25 replay: 171 rows, 0 errors, 170 SAME, 1 V4_OPENED, 0 V4_BLOCKED, 0 DIRECTION_FLIP, 0 OTHER. Mean Δ confidence -4.64. Window LONG_GAMMA-dominated.
  - SENSEX 2026-03-16/20/24/25 replay: 169 rows, 0 errors, 144 SAME, 25 V4_OPENED, 0 V4_BLOCKED, 0 DIRECTION_FLIP, 0 OTHER. Mean Δ confidence -4.80.
  - Spot-check of all 25 SENSEX V4_OPENED rows: every row BEARISH breadth + BULLISH momentum + SHORT_GAMMA, ret_session 0.86%-1.4%, V3=DO_NOTHING → V4=BUY_CE. Confidence distribution 40/44/50/54 traces cleanly to modifier stack. No anomalies.
  - Trade_allowed-flip check (action same but trade_allowed differs) empty on both symbols.
  - SQL audit of 60-day history: 0 rows where momentum_regime field explicitly opposes ret_session. ENH-55 opposition block confirmed as safety rail with no historical fire cases. Aligned +10 bonus fires on V4_OPENED and aligned-SAME paths where |ret_session| > 0.0005.
  - Promotion: source default flipped "0" → "1". .env updated locally (gitignored). Confirmation run: `signal_v4=True` with no env var set.

**Open after session:**
  - ENH-60 (NEW): UnboundLocalError pre-init in build_trade_signal_local flow-modifier block
  - ENH-61 (NEW): V3 trade_allowed=True unconditional reset at DTE block (cosmetic)
  - ENH-62 (NEW): Shadow runner dead since 2026-04-15 (unblocks shadow-required validations)
  - Post-promotion monitoring: first live trading day confirm V4_OPENED fires on BEARISH+BULLISH+SHORT_GAMMA in live cycle

**Files changed:** build_trade_signal_local.py (V4 build + default flip), .env (local, gitignored)
**Files added:** backtest_signal_v4.py (dev/shadow tool, uncommitted)
**Schema changes:** none — signal_snapshots raw JSONB gains two observability keys (signal_v4, ret_session); no DDL change required
**Open items closed:** ENH-53, ENH-55 (promoted)
**Open items added:** ENH-60, ENH-61, ENH-62
**Git commit hashes:** 8f70822 (feature-flagged build), e986cbb (default flip)
**Next session goal:** Fix ENH-60 (single-line `action = "DO_NOTHING"` pre-init). Track A commit, Default-safe.
**docs_updated:** yes

---

## 2026-04-19 — code_debug — C-08 breadth writer fix (closes VIEW-upsert bug)

**Goal:** Diagnose and fix stale latest_market_breadth_intraday data, validate V18H_v2's proposed DDL before applying.

**Session type:** code_debug

**Completed:**
  - Diagnosed root cause: commit 4599bb8 (2026-04-16) introduced ingest_breadth_from_ticks.py which upserts to a VIEW (latest_market_breadth_intraday). Supabase silently drops upserts to non-materialised views. Underlying table market_breadth_intraday had no writer since cutover.
  - Applied fix: one-line change — target table corrected from view to market_breadth_intraday with composite PK on_conflict="ts,universe_id".
  - Verified via direct upsert test (Saturday, market closed): test row with universe_id=excel_v1 appeared in view within 30s. Cleanup confirmed.
  - Found V18H_v2's proposed DDL was wrong on three dimensions (object to rebuild, PK design, column count) — had it been applied blindly the first upsert would have failed.
  - Updated merdian_reference.json: C-08 closed, registered ingest_breadth_from_ticks.py (missing since 4599bb8), added breadth_intraday_history table entry, retired ingest_breadth_intraday_local.py entry.

**Open after session:**
  - RESEARCH-OI-11 + RESEARCH-OI-12 (remove breadth hard gate, add momentum opposition block) — now unblocked
  - RESEARCH-OI-14 (shadow gate sessions 9+10 verify) — still pending
  - RESEARCH-OI-16 (proposed): audit merdian_reference.json files section for post-V18F additions that slipped through registration
  - AWS shadow runner still FAILED since 2026-04-15 — not touched this session

**Files changed:** ingest_breadth_from_ticks.py, docs/registers/merdian_reference.json, docs/session_notes/20260419_c08_breadth_writer.md, docs/session_notes/session_log.md
**Schema changes:** none
**Open items closed:** C-08
**Open items added:** RESEARCH-OI-16 (proposed)
**Git commit hash:** (pending — this session)
**Next session goal:** RESEARCH-OI-11 + RESEARCH-OI-12 — implement breadth-gate removal and momentum-opposition block in build_trade_signal_local.py. Shadow test 5 sessions.
**docs_updated:** yes

---

## 2026-04-17/18 � Research + Infrastructure � MTF OHLCV Build + Experiments 17-27b

**Goal:** Build 5m/15m OHLCV infrastructure and run experiment series to validate/reject LONG_GAMMA gate, breadth gate, momentum gate, and sweep reversal signal.
**Session type:** architecture + research

**Completed:**
  - Zerodha + Dhan tokens refreshed, 36 ICT zones built, Pine Script updated to v7
  - Fixed IndentationError in run_option_snapshot_intraday_runner.py (breadth block wrong indent)
  - Live NIFTY trade: BUY_CE manual ICT sweep reversal � PDL sweep 24,136 ? W PDH rejection ? +25%
  - Built hist_spot_bars_5m (41,248 rows) and hist_spot_bars_15m (14,072 rows)
  - Built hist_atm_option_bars_5m (27,082 rows) and hist_atm_option_bars_15m (9,601 rows) with wick metrics
  - Built hist_pattern_signals (6,318 rows) backfilled on 5m bars with option premium outcomes
  - Confirmed: all ICT pattern detection on 5m bars. 1m = execution only.
  - Exp 17: LONG_GAMMA gate confirmed correct (54.6% WR on BEAR_OB)
  - Exp 18: OI walls and ICT zones independent � OI synthesis REJECTED
  - Exp 19 (5m): No LONG_GAMMA asymmetry � symmetric gate correct
  - Exp 20 (5m): Momentum alignment +22.6pp � ALIGNED 60.9% vs OPPOSED 38.3% � hard gate confirmed
  - Exp 23/23b/23c: Sweep reversal 17-19% WR � discretionary only, ENH-54 REJECTED
  - Exp 25 (5m): Breadth 1.0pp spread � noise � ENH-43 remove hard gate
  - Exp 26: Option wick 1.7pp � no edge. SHORT_GAMMA PE wick 76.9% (N=13) � monitor
  - Exp 27: ICT in premium space � 37K signals too loose � no broad edge
  - Exp 27b: Small PE premium sweep <1% = 64.5% WR (N=107) � ENH-45 PROPOSED
  - ENH register v6 and Open Items register v7 written and committed

**Open after session:**
  - C-08: latest_market_breadth_intraday is VIEW not TABLE � upsert silently fails
  - OI-11: Remove breadth hard gate (ENH-43) � build pending
  - OI-12: Add momentum opposition hard block (ENH-44) � build pending
  - OI-13: Patch script syntax validation standard � add to Change Protocol
  - OI-14: Shadow gate sessions 9 and 10 (Apr 14/15) � verify pass/fail
  - OI-15: Premium sweep monitoring � log live PE sweeps <1%, target 50 occurrences
  - AWS Shadow Runner: FAILED since Apr 15 � investigate

**Files changed:** build_spot_bars_mtf.py, build_atm_option_bars_mtf.py, build_hist_pattern_signals.py, build_hist_pattern_signals_5m.py, fix_atm_option_build.py, fix_expiry_lookup.py, fix_runner_indent.py, experiment_17-27b scripts, run_option_snapshot_intraday_runner.py, MERDIAN_Enhancement_Register_v6.md, MERDIAN_OpenItems_Register_v7.md
**Schema changes:** NEW hist_spot_bars_5m, hist_spot_bars_15m, hist_atm_option_bars_5m, hist_atm_option_bars_15m, hist_pattern_signals
**Open items closed:** none
**Open items added:** OI-11, OI-12, OI-13, OI-14, OI-15, C-08
**Git commit hash:** d9e8293 (scripts) / 20abef9 (session log)
**Next session goal:** Implement OI-11 + OI-12 � remove breadth gate and add momentum opposition block in build_signal_v3.py, shadow test 5 sessions.
**docs_updated:** yes

---


## 2026-04-13 (late night) — engineering / documentation — WebSocket deployment, Phase 4A completion, V18G audit + v2

**Goal:** Deploy Zerodha WebSocket feed on MERDIAN AWS, complete remaining Phase 4A wiring, build AppendixV18G rebuild-grade documentation, conduct independent audit, produce v2.

**Session type:** engineering / documentation

**Completed:**

ENH-51a — Zerodha WebSocket Feed:
- `ws_feed_zerodha.py` deployed on MERDIAN AWS (i-0878c118835386ec2)
- kiteconnect installed on MERDIAN AWS. ZERODHA_API_KEY + ZERODHA_ACCESS_TOKEN added to MERDIAN AWS .env
- market_ticks DDL applied to MERDIAN Supabase (bigserial PK, 3 indexes, 19 columns)
- Instrument load: 45,712 NFO rows → 998 options + 6 futures + 3 spots = 1,007 total (within 3,000 limit)
- Spot-only dry run: NIFTY 50 23,842.65 | NIFTY BANK 55,605.05 | INDIA VIX 20.50 — all 3 ticks fired
- Live write test: 3 rows in market_ticks confirmed (2026-04-14 02:25:44 UTC)
- AWS cron added: 44 3 * * 1-5 (start 09:14 IST), 02 10 * * 1-5 (stop 15:32 IST)
- --ddl flag bug fixed (was inside __main__ block, hung on WebSocket load). fix_ws_ddl.py applied. Committed a215049.
- Git: beb8709 (ws_feed_zerodha.py) → a215049 (--ddl fix)

Phase 4 architecture design:
- Option A (manual, NOW) → B (semi-auto, after 2-4wk live data) → C (full auto, after 4B stable)
- Option B: merdian_order_placer.py + position monitor via Dhan API
- Option C: merdian_auto_executor.py + merdian_risk_gate.py
- Execution architecture documented in Enhancement Register v7 (ENH-49/50)

WebSocket broker architecture finalised:
- Zerodha KiteTicker: NIFTY full chain (3,000 limit, 100% GEX accuracy, 1,007 instruments)
- Dhan REST: SENSEX only (Zerodha has no BSE F&O) — unchanged
- MeridianAlpha: stays EOD via Zerodha Kite REST. Same Supabase. Integration deferred pending G-01.
- ENH-51 revised architecture documented and committed (355d5cf → 173a63f)

Pre-market and scheduler gap documented:
- Zerodha WebSocket does NOT serve pre-market (09:00–09:08 call auction). MERDIAN_PreOpen (Dhan) covers this.
- HTF zone rebuild (build_ict_htf_zones.py --timeframe D) is MANUAL — unresolved scheduler gap. Needs cron on AWS.
- systemd service documented as the correct supervisor pattern for AWS primary (not Python supervisor)

AppendixV18G:
- V18G v1 written (756 paragraphs, validated)
- Independent audit conducted: 19 findings (6 HIGH, 8 MEDIUM, 5 LOW)
- Key HIGH findings: F-02 fix_dashboard_v2 regex damage missing, F-03 three CAPITAL_FLOOR locations, F-05 options_flow_snapshots absent, F-09 ict_zones/ict_htf_zones/momentum_snapshots absent, F-14 Dhan option chain API missing
- V18G v2 rewritten incorporating all 19 findings (1,017 paragraphs, validated)
- All registers and JSON updated per protocol

**Files changed:** ws_feed_zerodha.py (NEW on MERDIAN AWS), fix_ws_ddl.py, Enhancement Register v7 (ENH-51a/b/c/d/e/f revised), session_log.md (this prepend)

**Schema changes:** market_ticks (NEW in MERDIAN Supabase — DDL applied)

**Open items closed:** ENH-51a (ws_feed_zerodha.py deployed and validated)

**Open items added:** OI-11 (HTF zone cron on AWS), OI-12 (market_ticks retention cron), OI-13 (Telegram credentials)

**Git commit hash:** a215049 (Local + MERDIAN AWS)

**Next session goal:** First live session with all systems (session 10). Pre-market: build_ict_htf_zones.py --timeframe D, python merdian_start.py, python run_preflight.py. Verify: AWS write_cycle_status, ret_session non-null, ICT zones ~09:30, market_ticks populating.

**docs_updated:** yes

---

## 2026-04-13 (late evening) — engineering — Phase 4A + ENH-02/04/06/07 + Signal Engine

**Goal:** Wire options flow into signal engine, build Phase 4A execution layer, close remaining Tier 1 ENH items.

**Session type:** engineering

**Completed:**

ENH-02/04/07 — Options flow wired into confidence scoring:
- `build_trade_signal_local.py`: fetches `options_flow_snapshots` each cycle
- PCR BEARISH+BUY_PE → +5, PCR BULLISH+BUY_CE → +5, contra → -4
- SKEW FEAR+BUY_PE → +4, SKEW GREED+BUY_CE → +4
- FLOW PE_ACTIVE+BUY_PE → +3, FLOW CE_ACTIVE+BUY_CE → +3
- ENH-07: basis_pct note added (futures premium/discount vs spot)
- Max lift on aligned signal: +12 confidence
- All stored in raw JSONB (no DDL needed)

ENH-06 — Pre-trade cost filter:
- `build_trade_signal_local.py`: validates lot sizing against capital at signal time
- Reads capital_tracker, estimates lot cost via estimate_lot_cost()
- If deployed > allocated × 1.10: reduces to 1 lot, adds caution
- Stores enh06_capital_ok, enh06_allocated, enh06_lot_cost in raw JSONB

Phase 4A — Manual execution layer:
- `merdian_trade_logger.py`: CLI trade logger. Reads latest signal, prompts entry price, writes trade_log + exit_alerts rows. Also handles --show (open trades) and --close (exit + PnL)
- `merdian_exit_monitor.py`: polls exit_alerts every 30s, fires console + Telegram alert at T+30m
- `merdian_signal_dashboard.py`: LOG TRADE button (green, appears when action ≠ DO_NOTHING), CLOSE TRADE button (always visible), modal dialogs, POST /log_trade + /close_trade endpoints
- `merdian_pm.py`: exit_monitor added to PROCESSES dict
- `merdian_start.py`: exit_monitor added to startup sequence
- Process manager fix: DETACHED_PROCESS removed (breaks supabase client), single file handle passed to Popen

Phase 4 architecture decisions:
- Option A (manual) now live
- Option B (semi-auto): merdian_order_placer.py + position monitor — after 2-4 weeks 4A data
- Option C (full auto): auto executor + risk gate — after 4B proven stable
- trade_log + exit_alerts tables confirmed existing and empty

**Open after session:**
- Telegram credentials not in .env — exit_monitor alerts console-only until configured
- Phase 4B: merdian_order_placer.py (Dhan API order placement)
- ENH-08: vega bucketing — deferred (weekly options only, low value)
- ENH-30: SMDM — deferred post-Phase 4
- Shadow gate session 10 tomorrow (Tue 2026-04-15) — then Phase 4 full promotion decision

**Files changed:** build_trade_signal_local.py (ENH-02/04/06/07), merdian_signal_dashboard.py (LOG TRADE button + endpoints), merdian_pm.py (exit_monitor + loghandle fix), merdian_start.py (exit_monitor in start order), merdian_trade_logger.py (NEW), merdian_exit_monitor.py (NEW)

**Schema changes:** None (trade_log + exit_alerts already existed)

**Open items closed:** ENH-02 (PCR), ENH-04 (IV skew/flow), ENH-06 (pre-trade cost filter), ENH-07 (basis note)

**Open items added:** None

**Git commit hash:** 54272e1

**Next session goal:** Shadow gate session 10. Pre-market: python merdian_start.py then python run_preflight.py. If session clean → Phase 4 promotion decision.

**docs_updated:** yes

---

## 2026-04-13 (evening) — engineering — Process Manager, ENH-36 Live Spot, ENH-01 ret_session, Bug Fixes

**Goal:** Post-market engineering. Process manager, live 1-min spot capture, ICT backfill, signal timestamp fix, AWS status writer fix, ret_session fix.

**Session type:** engineering

**Completed:**

ENH-46 — Process Manager:
- `merdian_pm.py` — core library: start processes in background (no terminal), PID registry at `runtime/merdian_pids.json`, stop/status/duplicate detection, port conflict check
- `merdian_start.py` — single morning startup command: Step 0 auto-inserts trading_calendar row (permanent V18A-03 fix), Step 1 kills all, Step 2 starts health_monitor + signal_dashboard + supervisor in background
- `merdian_stop.py` — kills all registered + unregistered MERDIAN processes
- `merdian_status.py` — shows all processes with PID, uptime, port, duplicate warnings. `--watch` mode (5s refresh)
- Health monitor: process status panel added (MERDIAN Processes card with PID/status/port per process)
- Zero terminal windows needed — all processes log to `logs/pm_<n>.log`

ENH-36 / ENH-47 — Live 1-min spot capture:
- `capture_spot_1m.py` — calls Dhan IDX_I, writes to `market_spot_snapshots` AND `hist_spot_bars_1m` (synthetic bar O=H=L=C=spot, truncated to minute)
- Task: `MERDIAN_Spot_1M` — every 1 minute, 09:14–15:31 IST Mon–Fri
- Task: `MERDIAN_PreOpen` — fires 09:05 IST Mon–Fri (closes C-07b permanently)
- Dashboard refresh: 60s (was 300s)

C-07b CLOSED — MERDIAN_PreOpen task fires at 09:05 IST Mon–Fri, before supervisor starts at 09:14. Pre-open spot now captured reliably.

ENH-01 — ret_session fix:
- `build_momentum_features_local.py` line ~224: threshold changed from `03:45 UTC` to `03:35 UTC` so MERDIAN_PreOpen capture at 09:05 IST (03:35 UTC) is accepted as session open price
- `ret_session` was computing but returning None because `market_spot_snapshots` had no rows after 03:45 UTC
- From tomorrow: `ret_session` will be non-null, feeding into momentum_regime (2.5x weight)

hist_spot_bars_1m backfill (today's session):
- 750 rows backfilled via Zerodha Kite on MeridianAlpha AWS (375 bars × 2 symbols)
- Confirmed: both instruments at 376 bars (375 + 1 test bar from capture_spot_1m test)

Signal dashboard fixes:
- Spot source changed from `market_spot_snapshots` to `signal_snapshots` (updates every 5-min cycle)
- Signal timestamp UTC→IST conversion fixed (was showing 03:55 IST instead of 09:25 IST)

AWS shadow runner fix:
- `write_cycle_status_to_supabase`: `json=payload` → `json=[payload]`, added `on_conflict=config_key`, removed `"updated_at": "now()"` string, added error logging
- Health monitor STALE 80h display will clear from tomorrow's first cycle
- Git: ab87044 (AWS) + c78b6ea (Local)

Capital floor lowered:
- `merdian_utils.py` + dashboard: CAPITAL_FLOOR 200,000 → 10,000 for trial runs

**Open after session:**
- Shadow gate session 10 tomorrow (Tue 2026-04-15)
- ENH-41 code: BEAR_OB DTE=0/1 combined structure (rule documented, code pending execution layer)
- capital_tracker auto-update after T+30m trade close (needs execution layer)
- ENH-02 PCR signal, ENH-04 IV skew (in progress)

**Files changed:** merdian_pm.py (NEW), merdian_start.py (NEW), merdian_stop.py (NEW), merdian_status.py (NEW), capture_spot_1m.py (NEW), set_capital.py (NEW), backfill_spot_zerodha.py (NEW), merdian_signal_dashboard.py (NEW), merdian_live_dashboard.py (process panel), build_momentum_features_local.py (ret_session threshold), run_merdian_shadow_runner.py (AWS — cycle status writer fix), merdian_utils.py (capital floor)

**Schema changes:** None

**Open items closed:** C-07b (MERDIAN_PreOpen task), ENH-01 (ret_session threshold fix)

**Open items added:** None

**Git commit hash:** c78b6ea (Local) | ab87044 (AWS runner fix)

**Next session goal:** Shadow gate session 10 (tomorrow). Pre-market: `python merdian_start.py` then `python run_preflight.py`.

**docs_updated:** yes

---

## 2026-04-13 — engineering / documentation — ENH-38 Full Build + Dashboard + Registers

**Goal:** Close all open items from research session: Kelly sizing end-to-end, signal dashboard, backfill, Signal Rule Book v1.1, register updates.

**Session type:** engineering / documentation

**Completed:**

OI-09 — capital_tracker table:
- CREATE TABLE public.capital_tracker (symbol PK, capital numeric, updated_at timestamptz)
- Seeded NIFTY + SENSEX at INR 2L each
- Capital floor lowered to INR 10K for trial runs

OI-08 / ENH-38 — Live Kelly tiered sizing (end-to-end):
- merdian_utils.py: LOT_SIZES (NIFTY=65, SENSEX=20), effective_sizing_capital(), estimate_lot_cost() (spot × IV × √DTE × 0.4), compute_kelly_lots(). ACTIVE_KELLY single-line strategy switch.
- detect_ict_patterns_runner.py: reads capital_tracker each cycle, fetches DTE via nearest_expiry_db, computes _lots_t1/t2/t3 with real lot cost, writes to ict_zones. Log: "Kelly lots (lot_size=65, dte=2d, iv=16.3%) T1:x T2:x T3:x"
- build_trade_signal_local.py: reads lots from active ict_zones row, forwards to signal_snapshots.ict_lots_t1/t2/t3
- Supabase: ict_zones +3 cols, signal_snapshots +3 cols
- Lot sizes corrected: NIFTY=65 (Jan 2026), SENSEX=20. Live patchers: patch_kelly_sizing.py → patch_kelly_lot_cost.py → patch_signal_kelly_lots.py

OI-07 — experiment_15b:
- Date type fix: _daily_str = {str(k): v for k, v in daily_ohlcv.items()} passed to detect_daily_zones
- LOT_SIZE corrected: NIFTY=75 (majority of backtest year), SENSEX=20
- Run complete. Results: Strategy C +6,764% combined, Strategy D +16,249% combined. MERDIAN-filtered universe (Exp 16) outperforms pure ICT (Exp 15b) — regime filter confirmed additive.

ENH-43 — Signal dashboard (merdian_signal_dashboard.py, port 8766):
- Action, confidence, ICT pattern/tier/WR/MTF, execution block (strike, expiry, DTE, live premium, lot cost, deployed capital), exit countdown timer (⚡ EXIT NOW at T+30m), active-pattern-only WR legend per card, regime pills, BLOCKED/TRADE ALLOWED badge, hard rules banner. Auto-refresh 5min.

ENH-44 — Capital management:
- set_capital.py: CLI setter supporting NIFTY/SENSEX/BOTH, ceiling notes, show command
- Dashboard: per-symbol number input + SET button, POST /set_capital, instant feedback without page reload

ENH-45 — hist_spot_bars_1m backfill (Apr 7–10):
- Zerodha Kite 1-min historical API via MeridianAlpha AWS instance (same Supabase)
- backfill_spot_zerodha.py: 4 dates × 2 symbols × 375 bars = 3,000 rows
- Upserts on (instrument_id, bar_ts). Verified: all 8 pairs at exactly 375 bars, 09:15–15:29 IST (UTC 03:45–09:59 confirmed)
- Enables correct daily zone pre-building for Apr 7–10 sessions

OI-10 / ENH-40 — Signal Rule Book v1.1:
- docs/research/MERDIAN_Signal_RuleBook_v1.1.md written
- 13 rule changes from v1.0: 4 NEW, 3 CHANGED, 5 CONFIRMED, 1 CLOSED
- Covers all patterns, MTF hierarchy, exit rules, signal engine gates, capital/sizing, quick reference card

**Open after session:**
- Shadow gate sessions 9 and 10 (today Monday, Tuesday)
- C-07b: pre-open capture gap — architectural fix pending
- ENH-41: BEAR_OB DTE combined structure — documented in Rule Book, code pending execution layer
- capital_tracker auto-update after T+30m trade close (requires execution layer)

**Files changed:** merdian_utils.py (Kelly sizing + lot cost), detect_ict_patterns_runner.py (Kelly block), build_trade_signal_local.py (lots passthrough), merdian_signal_dashboard.py (NEW — port 8766), set_capital.py (NEW), backfill_spot_zerodha.py (NEW — MeridianAlpha AWS)

**Schema changes:** capital_tracker (NEW — 3 cols), ict_zones (+ict_lots_t1/t2/t3), signal_snapshots (+ict_lots_t1/t2/t3)

**Open items closed:** OI-07, OI-08, OI-09, OI-10

**Open items added:** None

**Git commit hash:** [pending commit]

**Next session goal:** Shadow gate session 9 today (live market). Pre-market: python build_ict_htf_zones.py --timeframe D. Start merdian_signal_dashboard.py on port 8766.

**docs_updated:** yes

---

## 2026-04-12 — research — Full Experiment Series + Sizing Architecture + Documentation

**Goal:** Complete all 11 overnight experiments, analyse results, establish sizing architecture, document everything.

**Session type:** research / documentation

**Git end:** e24297f (Local + AWS in sync)

**Documents produced this session:**
- MERDIAN_AppendixV18F_v2.docx (rebuild-grade, audit-corrected) — docs/appendices/
- MERDIAN_Enhancement_Register_v5.md — docs/registers/
- MERDIAN_OpenItems_Register_v6.md — docs/registers/
- MERDIAN_Experiment_Compendium_v1.md — docs/registers/
- merdian_reference.json v3 — docs/registers/ (git updated, shadow gate 8/10, 6 new files, 3 new tables, 8 new governance rules, research_findings key added)
- session_log.md — prepended (this entry)

**Completed:**

Overnight runner fixes (encoding + expiry):
- UTF-8 cp1252 encoding fixed via PYTHONIOENCODING=utf-8 in subprocess env
- EXPIRY_WD compute_dte patched in all remaining scripts via fix_remaining_errors.py
- build_ict_htf_zones.py f-string corruption repaired
- 8/11 experiments completed overnight. 3 remaining fixed and run this session.

All 11 experiments now complete (full year Apr 2025–Mar 2026):

Experiment results summary:
- Exp 2: BULL_OB 88.9% WR +41.9% T+30m, BEAR_OB 73.0% +34.9%. BEAR_OB AFTERNOON -24.7% (hard skip). BULL_OB AFTERNOON 100% WR +75.3% (new TIER1).
- Exp 2b: Options beat futures on every pattern/DTE. Only exception: BEAR_OB DTE=0 and DTE=1 (combined structure wins). Futures experiments permanently closed.
- Exp 2c: Fixed-6 beats pyramid 1→2→3 on every pattern. Session pyramid deferred (ENH-42).
- Exp 2c v2: Judas T2 rate 12%→44% with T+15m confirmation window. Still fixed position wins.
- Exp 5: VIX gate removed for BULL_OB and BULL_FVG. Kept for BEAR_OB HIGH_IV. IV-scaled sizing per pattern established.
- Exp 8: MOM_YES = strongest filter (+21.6pp lift on BEAR_OB). IMP_WEK preferred over IMP_STR.
- Exp 10c: MEDIUM context (1H zone) outperforms HIGH (daily) for BULL_OB (+73.5% vs +40.7%). BULL_FVG|HIGH|DTE=0 new TIER1 rule (+58.9%, 87.5% WR). BEAR_FVG HIGH context destroys edge (-40.2%).
- Exp 15: Pure ICT, 1-lot compounding. BEAR_OB 94.4% WR. MEDIUM (1H zone) 77.3% WR. T+30m beats ICT structure break by 41%. Max DD 1.1% NIFTY.
- Exp 16: Kelly tiered sizing with capital ceiling. Strategy C (Half Kelly) +18,585% INR 7.47Cr. Strategy D (Full Kelly) +44,234% INR 17.7Cr. Both realistic and tradeable with INR 25L/50L ceiling.

Key decisions:
1. Futures experiments permanently closed. Options only.
2. INR 50L capital ceiling — liquidity constraint. INR 25L sizing freeze.
3. Strategy D (Full Kelly) selected for live. Start with C, upgrade after 3-6 months.
4. T+30m exit confirmed final. No further exit experiments needed.
5. 1H zones (MEDIUM context) confirmed in ENH-37 hierarchy.
6. BEAR_OB AFTERNOON hard skip rule.
7. BEAR_OB DTE=0/1 combined structure (futures + CE insurance) not pure PE.

Experiment 15b started but incomplete (date type mismatch in detect_daily_zones). Non-blocking.

Documentation produced:
- Enhancement Register v5
- Open Items Register v6
- MERDIAN_Experiment_Compendium_v1.md (new)
- session_log.md prepended (this entry)

Next session goals:
1. Shadow gate sessions 9 and 10 (Monday and Tuesday)
2. Build capital_tracker Supabase table (OI-09)
3. Implement ENH-38 Live Kelly Sizing in runner
4. Update Signal Rule Book v1.1 (OI-10)
5. Fix and run Experiment 15b (OI-07)

**Git commit:** fee7b7c → [pending after doc commit]

---

## 2026-04-11 — research / engineering — ENH-35 Validation + ENH-37 Full Build + Signal Engine Overhaul

**Goal:** Validate signal engine accuracy, apply ENH-35 findings, build ENH-37 ICT detection layer end-to-end.

**Session type:** research / engineering

**Completed:**

Expiry bug found and fixed:
- NIFTY switched Thursday→Tuesday expiry Sep 2025. Hardcoded `EXPIRY_WD = {"NIFTY": 3}` caused all post-Aug 2025 sessions to be skipped as "no option data" in all 11 experiment scripts. DB confirmed full option coverage Apr 2025–Mar 2026 (not a vendor gap — a code bug).
- Fix: `merdian_utils.py` — `build_expiry_index_simple()` + `nearest_expiry_db()`. All 11 scripts patched via `patch_expiry_fix.py`. ENH-31 CLOSED.

Experiments 14 + 14b — session pyramid definitively closed:
- Exp 14 (v1, mid-bounce): Pyramid -₹9,044 (22% WR) vs single T+30m +₹8,329 (100% WR) across 9 sessions.
- Exp 14b (v2, confirmed reversal): v2 improved v1 by ₹3,133 but still -₹12,645 vs single trade.
- Verdict: Single T+30m exit on first OB remains optimal. Session pyramid deferred to post-ENH-42 (WebSocket + bullish sessions needed).

ENH-35 — three validation runs:
- Run 1 (baseline): NIFTY 47.4% below random, 25,762 signals
- Run 2 (+3 changes): SHORT_GAMMA 55.5%, overall still noisy, 8,967 signals
- Run 3 (+6 changes): NIFTY 58.6% STRONG EDGE, 244 signals/year
- Final: trade_allowed=YES pool 268 bars, 55.2% accuracy. Phase 4 target met.
- Key finding: CONFLICT BUY_CE (breadth BULLISH + momentum BEARISH) = 67.9% at N=661 — the old CONFLICT rule was blocking the best trades.

Six signal engine changes applied and validated:
1. CONFLICT BUY_CE now trades (58.7% SENSEX / 55.4% NIFTY)
2. LONG_GAMMA → DO_NOTHING (47.7% — below random)
3. NO_FLIP → DO_NOTHING (45-48% — below random)
4. VIX gate removed (HIGH_IV has more edge — Experiment 5)
5. Confidence threshold 60→40 (edge in conf_20-49 band)
6. Power hour gate — no signals after 15:00 IST (SENSEX 20.8% expiry noise eliminated)

ENH-37 ICT Pattern Detection Layer — all 6 steps complete:
- `ict_zones` (28 cols) + `ict_htf_zones` (16 cols) created in Supabase
- `detect_ict_patterns.py` — ICTDetector class, VERY_HIGH/HIGH/MEDIUM/LOW MTF hierarchy, tier assignment from Experiment 8, breach detection
- `build_ict_htf_zones.py` — W/D/H zone builder. 1H layer added after design discussion (bridges timeframe gap). 39 zones written on first run.
- `detect_ict_patterns_runner.py` — runner integration, every 5-min cycle, non-blocking
- Signal engine enriched: ict_pattern, ict_tier, ict_size_mult, ict_mtf_context (4 new columns in signal_snapshots)
- Dashboard: ICT zones card + signal display updated
- 1H zone rationale: weekly/daily zones are pre-market. Without 1H, a 1M pattern in a bullish 1H structure incorrectly gets LOW context. 1H refreshes hourly during session.

**Open after session:**
- C-07b: Pre-open capture gap still open (supervisor starts 09:14)
- R-04: Dynamic exit v2 — deferred to Phase 4 execution layer
- Shadow gate: 8/10 — sessions 9+10 Monday/Tuesday
- Phase 4 decision: after session 10
- Rerun Exp 5, 8, 10c, portfolio sims on full year data (expiry fix now applied)
- Monday pre-market: `python build_ict_htf_zones.py --timeframe D`

**Files changed:** merdian_utils.py (NEW), patch_expiry_fix.py (NEW), experiment_14_session_pyramid.py (NEW), experiment_14b_session_pyramid_v2.py (NEW), detect_ict_patterns.py (NEW), build_ict_htf_zones.py (NEW), detect_ict_patterns_runner.py (NEW), patch_runner_ict.py (NEW), patch_signal_ict.py (NEW), patch_dashboard_ict.py (NEW), build_trade_signal_local.py (6 changes), run_option_snapshot_intraday_runner.py (ICT step wired), merdian_live_dashboard.py (ICT zones card), run_validation_analysis.py (replay engine updated)

**Schema changes:** ict_zones (NEW — 28 cols), ict_htf_zones (NEW — 16 cols), signal_snapshots (+ict_pattern, +ict_tier, +ict_size_mult, +ict_mtf_context)

**Open items closed:** ENH-31 (expiry calendar), ENH-35 (validation), S-05 (signal accuracy), S-06 (expiry bug), C-09 (power hour noise), R-01 (VIX gate), R-02 (sequence filter), R-03 (gamma gate), R-08 (session pyramid)

**Open items added:** none new

**Git commit hash:** 26c5e72 (Local + AWS)

**Next session goal:** Shadow sessions 9+10 results → Phase 4 promotion decision. If approved: wire ict_size_mult to order quantity (ENH-38), scope ENH-42 WebSocket.

**docs_updated:** yes

---

## 2026-04-10 / 2026-04-11 — research / architecture — ICT Research Series Complete + Signal Rule Book v1.0

**Goal:** Complete the full ICT pattern research series (Experiments 0–13) while monitoring live pipeline. Produce Signal Rule Book v1.0 as implementation-ready document.

**Session type:** research / architecture

**Completed:**

Pipeline (live session 2026-04-10):
- Token refresh Task Scheduler did NOT fire at 08:15 — manually triggered at 08:22 ✅
- Preflight OVERALL PASS (Local) ✅
- AWS token pulled (cron confirmed) ✅
- Supervisor start_supervisor_clean.ps1 failed due to parameter conflict (-NoNewWindow + -WindowStyle) — manually started supervisor at 08:31 ✅
- Runner lock file path mismatch (supervisor looks for runner.lock, runner uses run_option_snapshot_intraday_runner.lock) — cleared manually at 10:28 ✅
- Pipeline ran clean from 10:28 through 15:30 both symbols ✅
- BUY_PE both symbols, confidence 44, trade_allowed=False (VIX gate — but see research below)
- C-07b pre-open NOT CAPTURED (fix was deployed but pre-open runs before supervisor + runner start)
- AWS shadow: cycle OK 09:15, 11:45 — A-05 confirmed working ✅
- Shadow gate: today = session 8/10

Research series — all experiments completed:
- Experiment 0: Symmetric return distribution. Full year base rate 49.7% UP / 50.3% DOWN — essentially random. Market spent 10/12 months NEUTRAL. Only Nov 2025 BULL (55.6%) and Mar 2026 BEAR (55.3%). LOW_VOL Jul-Oct 2025 (0.0-0.2% large moves). HIGH_VOL Apr 2025 + Jan-Mar 2026 (1.5-4.2% large moves).
- Experiment 2: Options P&L — BULL_OB +70%, BEAR_OB +43%, BULL_FVG +34%, JUDAS_BULL +30%. BEAR_FVG -31%, BEAR_BREAKER -46% (never trade).
- Experiment 2b: Futures vs options — options dominate on % (leverage). Futures pyramid on OBs gives 31% of Fixed-6 reward for 12% risk (2.6× better Sharpe).
- Experiment 2c v1+v2: Pyramid entry. OBs confirm in 5 min (T2 80-93%). Judas needs 15-25 min (T2 rose from 12% to 44% with longer window but pyramid expectancy unchanged — Judas = options only).
- Experiment 5: VIX gate stress test. BEAR_OB|HIGH_IV +174.6% vs +84.8% MED_IV. ALL patterns better in HIGH_IV. VIX gate is BACKWARDS — must be removed.
- Experiment 8: Sequence detection. BEAR_OB|MOM_YES +187% (90% WR). BEAR_OB|IMP_STR -7.4% (avoid). Morning 10:00-11:30: BEAR_OB +296.6% 100% WR. BULL_OB|OPEN +3.4% 45% WR (skip).
- Experiment 9: SMDM. NEUTRAL — no structural difference expiry vs normal. Expiry sweep reversal edge lives in DTE=0 gamma, already captured by BOS_BEAR|HIGH|DTE=0.
- Experiment 10/10b/10c: ICT patterns. BULL_OB|MEDIUM +132.8% 100% WR. JUDAS_BULL|HIGH +56.6% 100% WR. MTF lift: JUDAS_BULL +42.4%, BULL_OB +25%.
- Experiment 11+12: Regime intersection. BULL_OB regime-independent (LONG_GAMMA +65.7% ≈ NO_FLIP +62.3%). JUDAS_BULL needs LONG_GAMMA. BEAR_OB|BEARISH momentum +141%.
- Experiment 12b: Repeatability by vol regime. BULL_FVG STRUCTURAL ★★★ (all 3 regimes). Others LIKELY STRUCTURAL ★★.
- Experiment 13: Signal Rule Book v1.0 — built as formatted .docx, 676 paragraphs, 8 sections. Covers pattern tiers, quality filters, execution rules, regime gate changes, portfolio simulation.

Documents produced:
- docs/research/MERDIAN_Signal_RuleBook_v1.docx — Signal Rule Book v1.0 ✅ Committed fcdf620
- docs/research/merdian_all_experiment_results.md — 677-line consolidated results reference ✅

**Open after session:**
- C-07b: Pre-open capture — supervisor/runner start after 09:08, architectural gap remains
- start_supervisor_clean.ps1: fix -NoNewWindow + -WindowStyle parameter conflict
- Runner lock file: supervisor must check run_option_snapshot_intraday_runner.lock (not runner.lock)
- Task Scheduler token refresh: investigate why 08:15 task did not fire
- R-01: Remove VIX gate from build_trade_signal_local.py — replace with IV-scaled sizing (NEW)
- R-02: Add sequence quality filter to signal engine — IMP_STR skip + MOM_YES tier sizing (NEW)
- R-03: Relax gamma regime gate for BULL_OB, BEAR_OB, BULL_FVG — keep for JUDAS_BULL only (NEW)
- R-04: Implement dynamic exit v2 in signal/execution layer (NEW)
- Shadow gate: 8/10 — 2 more clean sessions needed

**Files changed:** docs/research/MERDIAN_Signal_RuleBook_v1.docx (NEW), docs/research/merdian_all_experiment_results.md (NEW), experiment_0-13 scripts (research only, not production)
**Schema changes:** None
**Open items closed:** OI-08 (validation analysis — addressed by research series), E-05 (SMDM — research confirmed neutral, no full implementation needed)
**Open items added:** R-01 (VIX gate removal), R-02 (sequence filter), R-03 (gamma gate relax), R-04 (dynamic exit v2)
**Git commit hash:** fcdf620 (Signal Rule Book committed) | experiment results md pending commit
**Next session goal:** Commit all pending files (experiment scripts, results md, updated registers). Fix start_supervisor_clean.ps1 parameter conflict. Fix runner lock path mismatch. Investigate Task Scheduler token refresh. Continue shadow gate sessions (8/10).
**docs_updated:** yes

---

## 2026-04-09 — live_canary / code_debug — Fourth Live Session + Post-Market Fixes

**Goal:** Run fourth live session and deploy all outstanding post-market fixes.

**Session type:** live_canary / code_debug

**Completed:**

Morning startup:
- Supervisor PID 16248 still alive from April 6 — manually killed and restarted clean PID 1640 at 08:29
- Both preflights passed (Local + AWS) — token auto-refreshed at 07:54 with TOTP retry working
- Runner auto-started by supervisor at 09:15 ✅ — first time fully automatic
- AWS shadow auto-started via cron at 09:15 (PID 95553) ✅

Live session:
- NIFTY: 37,350 rows (09:18–15:27) ✅ Full session
- SENSEX: 42,000 rows (09:19–15:28) ✅ Full session
- NIFTY: BUY_PE all session, confidence 44, trade_allowed=False
- SENSEX: BUY_PE all session, confidence 48, trade_allowed=False
- VIX: 19-20 range — HIGH regime (down from 26+ PANIC on April 6)
- SENSEX: SHORT_GAMMA detected — first time observed in live session
- Breadth: LIVE — Advances 229, Declines 594, BEARISH
- Transient Supabase RemoteProtocolError at 13:17 — one partial cycle, self-healed on next cycle

Post-market fixes deployed (all 5):
1. `start_supervisor_clean.ps1` — kills old supervisor before starting new one. Task Scheduler updated to call PS1 wrapper. Root cause: Task Scheduler started new process without killing old one; old process held lock file preventing fresh starts.
2. AWS Guard 4 (LTP staleness) skipped — `equity_intraday_last` not maintained on AWS shadow. This was preventing `write_cycle_status_to_supabase()` from being called. AWS shadow block now writes status to Supabase after each cycle.
3. `merdian_live_dashboard.py` — `parse_ist_dt` made more robust to handle all Supabase timestamp formats (fixes `?` timestamps on NIFTY pipeline stages).
4. `stage2_db_contract.py` — `check_trading_calendar_week_ahead` now uses Python `trading_calendar` module instead of Supabase table count (fixes false warning — new calendar stores holidays only, not every trading day).
5. Dashboard preflight encoding — already in dashboard fix above (ASCII sanitize + PYTHONIOENCODING).

Task scheduler audit:
- All 8 remaining tasks confirmed needed
- MERDIAN_Market_Tape_1M already disabled yesterday

**Open after session:**
- C-07b: Pre-open capture gap still architectural — supervisor too late for 09:00-09:08 window
- AWS shadow cycle status: not yet verified in dashboard (will confirm tomorrow when shadow runner cycles with Guard 4 fix)
- E-35: run_validation_analysis.py — next engineering priority
- Shadow gate: 7/10 (verify exact count — April 6 was partial, April 7 was delayed)

**Files changed:** start_supervisor_clean.ps1 (new), merdian_live_dashboard.py (timestamp + encoding fix), stage2_db_contract.py (calendar check fix), run_merdian_shadow_runner.py (Guard 4 skip)
**Schema changes:** None
**Open items closed:** S-10 (supervisor lock), A-05 (AWS shadow status write), C-03 (WCB confirmed live), C-07a (AWS premarket confirmed), S-04 (no late stops confirmed), M-02 (premarket recording confirmed)
**Open items added:** E-35 (run_validation_analysis.py)
**Git commit hash:** 858de8f (Local + AWS)
**Next session goal:** Verify AWS shadow status in dashboard, fix C-07b pre-open gap, build E-35 run_validation_analysis.py
**docs_updated:** yes

---

## 2026-04-08 — live_canary / code_debug — Third Live Session

**Goal:** Run third live session. Monitor for supervisor auto-start and AWS shadow.

**Session type:** live_canary / code_debug

**Completed:**

Morning startup:
- Supervisor PID 16248 still alive from April 6 — manually killed, started clean PID 1640 at 08:29
- Both preflights passed. Dhan HTTP 500 on expiry list at first attempt — Dhan server hiccup, cleared on retry
- Token auto-refreshed with TOTP retry (Invalid TOTP on first attempt, waited 30s, succeeded)
- Runner auto-started by supervisor at 09:15 ✅
- AWS shadow auto-started via cron at 09:15 (PID 84986) ✅

Live session:
- NIFTY: 37,350 rows (09:18–15:27) ✅ Full session
- SENSEX: 42,000+ rows (09:19–15:28) ✅ Full session
- VIX dropping from 26+ to 19-20 range — market recovering
- SENSEX: SHORT_GAMMA first observed
- Breadth: LIVE, Advances 405, Declines 965, BEARISH
- Transient Supabase RemoteProtocolError at 13:17 — self-healed on next cycle

Pre-open data confirmed in Supabase:
- NIFTY 23,855 / SENSEX 77,298 at 09:08:02 IST — written by AWS cron capture_premarket_0908.py
- Dashboard showed NOT CAPTURED because it queries wrong table — C-07b root cause partially identified

**Open after session:**
- Supervisor persistent lock root cause confirmed — PID 16248 never dies, new Task Scheduler start exits finding lock occupied
- AWS shadow Guard 4 blocking Supabase status write
- Dashboard ? timestamps on NIFTY — parse_ist_dt bug
- Dashboard preflight button cp1252 — cosmetic but annoying

**Files changed:** None (observations and root cause identification only)
**Schema changes:** None
**Open items closed:** S-04 (confirmed no late stops), C-07a (confirmed AWS premarket capture working)
**Open items added:** S-10 (supervisor persistent lock root cause confirmed)
**Git commit hash:** 17ac20a (no code changes this session)
**Next session goal:** Deploy all 5 post-market fixes — supervisor PS1 wrapper, AWS Guard 4, dashboard timestamp, preflight calendar check, dashboard encoding
**docs_updated:** yes

---

## 2026-04-07 — live_canary / code_debug — Second Live Session + Operational Fixes

**Goal:** Run second live market session and resolve operational failures carried over from day 1.

**Session type:** live_canary / code_debug

**Completed:**

Morning failures (root causes and fixes):
- Supervisor did not auto-start runner — PID 16248 from yesterday had loaded old trading_calendar.py before the rewrite was deployed. Running Python process does not reload imported modules from disk. Fix: added weekly 08:00 Mon-Fri trigger to MERDIAN_Intraday_Supervisor_Start task — supervisor now restarts fresh every morning.
- AWS token 401 at 09:00 — cron at 08:25 IST pulled token before Local's Supabase sync completed. Fixed: AWS cron shifted from 08:25 (03:55 UTC) to 08:35 (03:05 UTC).
- Runner started manually at 09:32, first cycle 09:35. Session ran 09:35–15:28.

Live session:
- NIFTY: 34,452 option chain rows (09:42–15:27) ✅. BUY_PE all session, confidence 48–64, trade_allowed=False (VIX panic gate >25)
- SENSEX: 33,600 rows (09:43–15:28) ✅. BUY_PE / DO_NOTHING, confidence 28–56, trade_allowed=False
- Breadth: LIVE — Advances 387, Declines 934, BEARISH — heavily bearish day
- AWS shadow runner: auto-started via cron at 09:15 (PID 80952), ran full session ✅

Task scheduler audit:
- MERDIAN_Market_Tape_1M DISABLED — was failing every run (DhanError 401), producing no useful output, and making 390 extra Dhan API calls/day contributing to 429 rate limiting on breadth ingest
- All other 8 tasks confirmed correct and needed

**Open after session:**
- C-07b: Pre-open capture still missed — supervisor starts at 09:14, too late for 09:00-09:08 window
- Dashboard preflight button cp1252 encoding error — cosmetic only, preflight works from command line
- Shadow gate count: 6/10 (verify)
- ENH-35: run_validation_analysis.py — next build priority

**Files changed:** None (Task Scheduler and crontab changes only — no code changes)
**Schema changes:** None
**Open items closed:** OI-03 (MERDIAN_Market_Tape_1M disabled — confirmed broken and harmful)
**Open items added:** None
**Git commit hash:** 8a992ee (no code changes today)
**Next session goal:** Fix C-07b pre-open capture gap, fix dashboard preflight encoding, build ENH-35 run_validation_analysis.py
**docs_updated:** yes

---

## 2026-04-06 — live_canary / code_debug / architecture — First Live Session + Architecture Repairs

**Goal:** Run first live market session (NIFTY/SENSEX options pipeline) and repair all root-cause failures discovered during the session.

**Session type:** live_canary / code_debug / architecture

**Completed:**

Live session:
- Runner started manually at 09:26 IST after calendar and syntax fixes (first cycle 09:30)
- NIFTY: BUY_PE action=48 confidence, trade_allowed=False (VIX panic gate >25 correctly blocked)
- SENSEX: DO_NOTHING, confidence=36
- VIX: 26.41 — PANIC regime, 100th percentile, VIX_UPTREND all session
- SMDM: NIFTY squeeze_score=4, SQUEEZE pattern active
- Full pipeline completed: options → gamma → volatility → momentum → market_state → signal → options_flow → momentum_v2 → SMDM → structural_alerts → shadow_v3
- AWS shadow runner manually started 09:46 IST, ran until 15:30 IST market close

Post-market architecture repairs:
- trading_calendar.py full rewrite — rule-based. Old design required manual row per date; missing row = system failure (root cause of today's morning failure). New: weekdays open by default, weekends closed by computation, NSE holidays are the only stored exceptions. No manual date insertion ever required again.
- trading_calendar.json rebuilt — holidays-only format. 23 NSE holiday entries for 2025-2026. Old 371-line manually maintained sessions list replaced.
- merdian_live_dashboard.py full rewrite (v2) — session state computed live from calendar (never stale), token block with expiry countdown, pre-open block (09:00-09:08) with spot capture status, pipeline stages showing actual values (spot, VIX, regime, signal action), breadth block with advances/declines, AWS shadow runner block via Supabase, action buttons with inline result within 5s (no click and pray), cp1252 encoding fixed for Windows.
- refresh_dhan_token.py — added runtime/token_status.json write after every attempt. Added TOTP retry: waits 30s and retries with next TOTP window on Invalid TOTP error.
- run_merdian_shadow_runner.py — breadth ingest disabled on AWS. Both Local and AWS were hitting the same Dhan token simultaneously causing 56/56 chunks returning 429 all day. AWS shadow is read-only for breadth. Also added write_cycle_status_to_supabase() — writes cycle_ok, breadth_coverage, per_symbol status to system_config table after each cycle for dashboard consumption.
- run_option_snapshot_intraday_runner.py — CREATE_NO_WINDOW flag added to subprocess calls. Eliminates 25-30 terminal windows flashing per 5-minute cycle.
- Task Scheduler MERDIAN_Live_Dashboard — updated with PYTHONIOENCODING=utf-8.

**Open after session:**
- C-07b confirmed: pre-open capture gap — supervisor task fires at 09:14, misses 09:00-09:08 window. Architectural fix needed.
- Shadow gate count: verify 5/10 after today
- Supabase disk usage: unverified post-session (was 9.5GB pre-session)
- ENH-35: run_validation_analysis.py — next build priority
- ENH-36: hist_* to live promotion pipeline — after ENH-35

**Files changed:** trading_calendar.py (full rewrite), trading_calendar.json (full rewrite), merdian_live_dashboard.py (full rewrite v2), refresh_dhan_token.py (token_status.json + TOTP retry), run_option_snapshot_intraday_runner.py (CREATE_NO_WINDOW), run_merdian_shadow_runner.py (breadth disabled + Supabase status write)
**Schema changes:** None
**Open items closed:** Calendar root cause resolved (permanent fix)
**Open items added:** C-07b confirmed (pre-open capture gap)
**Git commit hash:** 627a1b5 (Local + AWS)
**Next session goal:** Monitor second live session tomorrow — verify token refresh automatic at 08:15, preflight from dashboard, supervisor auto-start at 09:14, pipeline green by 09:25
**docs_updated:** yes

---

## 2026-04-04 / 2026-04-05 — code_debug / infrastructure / architecture — V18C Session + Historical Backfill Sprint

**Goal:** Close all actionable open items from Groups 1–5, build historical gamma backfill pipeline, ingest vendor correction data, build live monitoring dashboard.

**Session type:** code_debug / infrastructure / architecture (extended — 2 days)

**Completed:**
- V18A-01: Token refresh race condition fixed — Local writes token to Supabase, AWS pulls at 08:25 IST
- OI-03: MERDIAN_Market_Tape_1M re-enabled
- C-04/C-05/C-06: Closed from query evidence
- S-01/S-02: Supervisor task swap — MERDIAN_Intraday_Supervisor_Start enabled, legacy launcher disabled
- S-05: Table freshness checks added to gamma_engine_telemetry_logger.py
- S-07: watchdog_check.ps1 rebuilt with trading_calendar guard and market hours gate
- S-08: MERDIAN_Scheduler_Manifest.md created in docs/
- S-03/S-06/M-01: Confirmed already built — closed
- A-04: Python 3.10 compatibility fix on AWS (datetime.UTC → timezone.utc)
- E-03: India VIX signal rules added to build_shadow_signal_v3_local.py (shadow only)
- D-09/E-06: 13 shadow table DDLs documented in docs/MERDIAN_Shadow_Tables_DDL.md
- Token refresh timing corrected to 08:15 IST per Change Protocol Rule 6
- MERDIAN_Live_Dashboard: live HTTP monitoring dashboard built (localhost:8765)
- Three new Supabase tables: hist_gamma_metrics, hist_volatility_snapshots, hist_market_state
- backfill_gamma_metrics.py: pure-Python BS IV + GEX computation from hist_option_bars_1m
- batch_backfill_gamma.py: batch wrapper — 421/514 dates passed
- batch_reconstruct_signals.py: expiry-aligned batch reconstruction wrapper
- Vendor correction files ingesting: SENSEX F+O contractwise (247 files, 19M rows)
- OpenItems Register converted from docx to markdown — v4 edition

**Open after session:**
- F+O vendor ingest running (MAY/JUN 2025, JAN 2026 SENSEX data)
- SENSEX gamma backfill for May–Jun 2025 and Jan 2026 (after ingest)
- C-03/C-07a/C-07b/S-04/A-05/M-02: require Monday live session
- Shadow gate: 4/10 sessions — needs 6 more clean live sessions
- backfill_volatility_metrics.py and backfill_market_state.py: not yet built
- Appendix V18D: required per documentation protocol

**Files changed:** merdian_live_dashboard.py (NEW), backfill_gamma_metrics.py (NEW), batch_backfill_gamma.py (NEW), batch_reconstruct_signals.py (NEW), gamma_engine_telemetry_logger.py, watchdog_check.ps1, build_shadow_signal_v3_local.py, refresh_dhan_token.py, ingest_equity_eod_local.py (AWS), docs/MERDIAN_Scheduler_Manifest.md, docs/registers/MERDIAN_OpenItems_Register_v4.md, docs/MERDIAN_Shadow_Tables_DDL.md

**Schema changes:** hist_gamma_metrics (NEW), hist_volatility_snapshots (NEW), hist_market_state (NEW), system_config row dhan_api_token (NEW)

**Open items closed:** V18A-01, OI-03, C-01, C-02, C-04, C-05, C-06, C-08, A-03, A-04, E-03, D-09/E-06, S-01–S-08, M-01, Group 3 steps 3.1–3.6, Group 4 items 4.1/4.3/4.6

**Git commit hash:** 0655599

**Next session goal:** Run SENSEX gamma backfill for vendor-corrected months. Build backfill_volatility_metrics.py. Write Appendix V18D.

**docs_updated:** yes

---

## How to Add New Entries

Copy this template and prepend to the top of this file (newest first):

```markdown
## YYYY-MM-DD — [Session type] — [Topic]

**Goal:** [one sentence]
**Session type:** code_debug / architecture / documentation / live_canary / planning

**Completed:**
  - [bullet with evidence]
  - [bullet with evidence]

**Open after session:**
  - [bullet]

**Files changed:** [comma-separated, or "none"]
**Schema changes:** [describe, or "none"]
**Open items closed:** [IDs, or "none"]
**Open items added:** [IDs, or "none"]
**Git commit hash:** [hash]
**Next session goal:** [one sentence, specific]
**docs_updated:** yes / no / na
```

---

*MERDIAN Session Log — started 2026-03-31 — append newest entry at top*

