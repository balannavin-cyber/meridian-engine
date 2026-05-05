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

### TD-071 — Stale 2025 zones still showing ACTIVE due to `expire_old_zones()` order bug in `build_ict_htf_zones.py`

| | |
|---|---|
| **Severity** | S2 (operational hygiene — zone status incorrect for ~year-old zones; visual noise on Pine, can affect detector if zones queried by status only without date filter) |
| **Discovered** | 2026-05-05 (Session 20 — observed during HTF zone rebuild after spot data backfill; some 2025 zones from June through November still showing ACTIVE despite breach by current spot price) |
| **Component** | `build_ict_htf_zones.py` zone build pipeline; specifically the order of `expire_old_zones()` vs `upsert_zones()` vs `recheck_breached_zones()` |
| **Symptom** | Old zones (e.g., July 2025 BULL_OB at price 18,500 when current NIFTY spot is 24,051) still show `status='ACTIVE'` in `ict_htf_zones`. They should be `BREACHED` (price moved through them) or expired by date (older than `valid_to`). Q1 from Session 20 rebuild showed 18 W BULL_OB BREACHED but with `oldest=2025-06-02 newest=2026-02-16` indicating recheck DID work for some — but mix of old ACTIVE remains. |
| **Root cause** | `expire_old_zones()` runs BEFORE `upsert_zones()` in build pipeline — meaning it operates on previous run's data, not the new zone set. The `upsert` writes ACTIVE for newly detected zones (correct) but doesn't re-trigger expire on the upserted set. `recheck_breached_zones()` correctly handles price-breach cases but not date-expiry cases. Session 13 partially addressed via "moved recheck after upsert" comment but order logic still not fully right. |
| **Workaround** | Manual SQL DELETE or status-update for stale zones; tomorrow morning's auto-rebuild covers the ~248-day lookback so very old zones eventually drop out as detector window slides. Not blocking. |
| **Proper fix** | Reorder pipeline: (1) detect new zones, (2) `upsert_zones()` writes ACTIVE for newly-detected, (3) `recheck_breached_zones()` for price-breach across ALL zones (new + existing), (4) `expire_old_zones()` for date-expiry across ALL zones. Verify each transition idempotent. |
| **Cost to fix** | ~6 exchanges (code review + reorder + verify on test data) |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-05 |

---

### TD-070 — `prev_move < 0` over-filters BULL_OB candidates in `detect_weekly_zones()`

| | |
|---|---|
| **Severity** | S2 (detector tuning — costs 5-10 valid BULL_OB zones across lookback per Session 20 observation; doesn't break system, just under-detects) |
| **Discovered** | 2026-05-05 (Session 20 — observed during HTF zone rebuild on real OHLC; Apr-13 was a +2.27% bullish week that should generate a BULL_OB but didn't because immediately-prior week Apr-06 was also bullish at +4.26%; detector's `prev_move < 0` constraint requires immediately-prior week to be bearish) |
| **Component** | `build_ict_htf_zones.py::detect_weekly_zones()` BULL_OB candidate filter |
| **Symptom** | BULL_OB candidates filtered out when prior week was also bullish, even though canonical ICT definition allows OB to form against any nearby bearish candle (not strictly the immediately-prior one). Result: detector under-counts BULL_OB zones in sustained bull-trend periods. |
| **Root cause** | Code uses simplified single-bar prior-move check: `prior_move = pct(prior["open"], prior["close"]); if prior_move < 0:`. Canonical ICT: BULL_OB is the LAST DOWN CANDLE before a bullish impulse move; can be 1-3 bars back, not strictly the immediately-prior one. |
| **Workaround** | None — BULL_OB count is empirically still high (2 ACTIVE / 18 BREACHED on NIFTY 252-week lookback, sufficient for production routing). The under-detection is asymmetric (bull markets affected more) but doesn't break detection logic. |
| **Proper fix** | Replace `if prior_move < 0` with "scan back N bars (3-5) for any bearish candle whose body becomes the OB anchor". Match canonical ICT definition. Verify backward-compat: existing detected zones should remain detected; only NEW candidates surface. |
| **Cost to fix** | ~4 exchanges (code change + unit test on 5 known cases + production verify) |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-05 |

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

### TD-061 — Task Scheduler entry points spawn visible console windows during pre-market and post-market hours (operator productivity tax)

| | |
|---|---|
| **Severity** | S2 (non-blocking but degrades operator workflow — windows flashing during chart prep cause mistypes and break concentration) |
| **Discovered** | 2026-05-03 (Session 17 — operator reported "all of Friday and Saturday there were a gazillion terminal windows opening and shutting through the day even outside supposed market hours (both holidays). When I checked there were 6-7 processes running. Why?") |
| **Component** | Windows Task Scheduler tasks: MERDIAN_PreOpen, MERDIAN_Spot_1M, MERDIAN_Dhan_Token_Refresh, MERDIAN_Intraday_Supervisor_Start, MERDIAN_Market_Tape_1M, MERDIAN_PO3_SessionBias_1005, MERDIAN_Post_Market_1600_Capture, MERDIAN_Session_Markers_1602, MERDIAN_Spot_MTF_Rollup_1600, MERDIAN_WS_Feed_0900, MERDIAN_ICT_HTF_Zones_0845, MERDIAN_IV_Context_0905, MERDIAN_EOD_Breadth_Refresh, MERDIAN_Market_Close_Capture (13 tasks). |
| **Symptom** | Each scheduled task spawns a `python.exe` process which opens a console window. Even when the script's holiday-gate logic correctly exits clean (per ENH-66), the visible console pop-up interrupts operator workflow. Cumulative: 25-30 window flashes per 5-min cycle reported in session_log Apr-13 entry (partial fix applied to `run_option_snapshot_intraday_runner.py` subprocess calls only). On holidays/weekends, every Mon-Fri-triggered task fires, hits calendar gate, exits, but flashes a window. |
| **Root cause** | Task action runs `python.exe` (console executable) instead of `pythonw.exe` (no-console). The CREATE_NO_WINDOW subprocess flag fix from Session Apr-13 was applied selectively to inner subprocess calls within `run_option_snapshot_intraday_runner.py` but not propagated to top-level Task Scheduler entry points. |
| **Workaround** | Operator has been killing runaway processes manually when noise becomes intolerable; this disables tasks until manually re-enabled (as happened May-2 this session — re-enabled via PowerShell loop on May-3). |
| **Proper fix** | Two-option choice: (a) Migrate Task Scheduler entry points from `python.exe` to `pythonw.exe`. Same script runs but no console window. Caveat: scripts that print to stdout without a redirect file lose that output; for MERDIAN tasks that already write to `script_execution_log` Supabase table, this is safe. (b) Wrap each task action with PowerShell `-WindowStyle Hidden` launcher. More complex, briefer flash residue. Pick (a). Verification: re-register one task (e.g. MERDIAN_Spot_1M, highest cycle frequency), confirm no window appears on next trigger AND `script_execution_log` row still written. Then propagate to remaining 12 tasks. |
| **Cost to fix** | 1 dedicated session (~15 exchanges) — re-register all 13 tasks, test each. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-03 |

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

### TD-063 — Single-instance enforcement missing on Task Scheduler tasks (defense in depth against TD-062)

| | |
|---|---|
| **Severity** | S3 (cosmetic — defense-in-depth; doesn't itself cause failures but lets TD-062's stuck-process accumulation grow unbounded) |
| **Discovered** | 2026-05-03 (Session 17 — investigation of TD-062 revealed that Task Scheduler's default `MultipleInstances` setting allows new instance to attempt start even when previous still running, leading to the 2147946720 errors observed) |
| **Component** | Task Scheduler XML triggers / settings for all 13 MERDIAN_* tasks |
| **Symptom** | When a task instance hangs (TD-062 root cause), subsequent scheduled triggers fire and try to launch a new instance, get rejected with 2147946720, but no automatic cleanup of the stuck instance occurs. Process count grows over the day. |
| **Root cause** | Default `MultipleInstances=Parallel` (or absent setting interpreted as Parallel) on Task Scheduler tasks. Should be `IgnoreNew` (skip new fire if previous still running) or `StopExisting` (kill old one and start new). |
| **Workaround** | Operator kills accumulated processes manually; current state. |
| **Proper fix** | Set `MultipleInstances=IgnoreNew` on all 13 MERDIAN_* tasks via PowerShell `Set-ScheduledTask` or XML edit. This makes the symptom of TD-062 self-clearing on each successive trigger (skips the stuck instance, no error, scheduled work resumes once stuck instance times out or is killed). Alternative: `StopExisting` is more aggressive — kills the stuck instance forcibly, may corrupt state for some scripts. Default to `IgnoreNew`. |
| **Cost to fix** | 1 PowerShell loop, ~10 minutes including verification. Could be batched with TD-061 re-registration. |
| **Blocked by** | nothing (independent of TD-061/TD-062 root cause work) |
| **Owner check-in** | 2026-05-03 |

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
| **Owner check-in** | 2026-05-03 (Session 16 — extended scope, locally-computed workaround in active use) |

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
| **Fix applied** | Three patches in two scripts: (a) **S1.a** = added W BEAR_FVG branch in `detect_weekly_zones()` mirroring the existing W BULL_FVG branch; threshold `FVG_W_MIN_PCT=0.10%`. (b) **S1.b** = added D BULL_FVG and D BEAR_FVG detection in `detect_daily_zones()`; new constants `FVG_D_MIN_PCT=0.10%` and `D_FVG_VALID_DAYS=5` (D-FVG validity window 5 calendar days, longer than D-OB which retains TD-050's 1-day issue). (c) **S15-1H** = added BEAR_FVG branch to `detect_1h_zones()` in live builder mirroring existing BULL_FVG branch. Patches applied to both `build_ict_htf_zones_historical.py` (S1.a + S1.b) and `build_ict_htf_zones.py` (S1.a + S1.b + S15-1H). |
| **Backfill executed** | (1) `build_ict_htf_zones_historical_PATCHED.py` full backfill: 264 NIFTY + 263 SENSEX trading days = 40,384 rows written to `hist_ict_htf_zones`. Counts: W BEAR_FVG=1,384, W BULL_FVG=2,603 (ratio 0.53 — bull-trend regime, makes sense), D BEAR_FVG=79, D BULL_FVG=84 (ratio 0.94 — symmetric, makes sense). (2) `build_ict_htf_zones_PATCHED.py --timeframe both` live run: 85 zones written to `ict_htf_zones`, 10 ACTIVE per symbol post breach-recheck. (3) `build_hist_pattern_signals_5m.py` (no code change — direction-symmetric verified): `hist_pattern_signals` 6,318 → 7,484 rows. **BEAR_FVG: 0 → 795.** |
| **Files renamed (after backfill verified)** | `build_ict_htf_zones.py` and `build_ict_htf_zones_historical.py` ARE NOW the patched versions; originals preserved as `build_ict_htf_zones_PRE_S15.py` and `build_ict_htf_zones_historical_PRE_S15.py`. Scheduled task `MERDIAN_ICT_HTF_Zones` (08:45 IST Mon-Fri) automatically uses patched live builder going forward. |
| **End-to-end re-verification** | `diagnostic_bear_fvg_audit.py` re-run post-rebuild: BEAR_FVG count 795 (was 0). NIFTY 60d signals: BULL_FVG 274 / BEAR_FVG 150. SENSEX 60d: BULL_FVG 263 / BEAR_FVG 208. Asymmetry 1.83x (NIFTY) / 1.26x (SENSEX) noted as residual finding — canonical 5m shapes are ~symmetric (NIFTY 562 BEAR / 587 BULL; SENSEX 567 / 575) so signal builder may have a regime-driven bull-skew filter. Filed as TD-056 for investigation. |
| **Bugs intentionally NOT fixed (catalogued as separate TDs)** | TD-049 (D-OB definition non-standard ICT — uses move bar K+1 as OB instead of opposing prior K), TD-050 (D-zone non-FVG validity = 1 day), TD-051 (PDH/PDL `+/-20pt` hardcoded), TD-052 (zone status workflow write-once-never-recompute on historical builder). All four candidates for Session 16 Candidate D. Decision to ship S1 only was deliberate: low-risk symmetric mirror of existing logic, unblocks Exp 50/50b re-run on bidirectional data without forcing definition-change discussions in the same session. |
| **Lessons** | **(a) Verify experiment results against market reality before believing them.** Operator's chart-based challenge to "0 BEAR_FVG over 13 months" was the only thing that surfaced this 13-month silent bug — the zone builder, signal builder, and downstream consumers had been running clean across multiple sessions without anyone noticing the asymmetry. The bug was discoverable by inspection but not by automated test. **(b) Full-file PATCHED.py copies + post-verification rename is the safe deploy pattern (vs in-place edit).** Allows dry-run, real-run, end-to-end verification, and rollback as discrete steps; rollback is one rename. Operator preferred this pattern over `.bak` files. **(c) When a known-incomplete detector (S1.a / S1.b) is being patched, run a code review to surface what else is wrong before patching** — the six-bug catalogue (TD-049/050/051/052 + S1.a + S1.b) emerged from one review pass; spreading discovery across multiple sessions would have been more expensive. **(d) Direction-symmetry verification on the signal builder before patching the detector** — by confirming `build_hist_pattern_signals_5m.py` was innocent first, Session 15 avoided the trap of patching the signal builder symptomatically while leaving the zone-builder root cause intact. The 5-step audit S5 (canonical shape scan) was the test that proved this. |

---

*MERDIAN tech_debt.md v1 — created concurrent with CLAUDE.md and Documentation Protocol v3. Updated Session 18 (2026-05-04): TD-061/063/056/065 RESOLVED, TD-062 PARTIAL (heartbeat foundation), TD-064/066/067 NEW (migrated from closed OpenItems Register). Update inline as items are added/closed; commit with `MERDIAN: [OPS] tech_debt — <action>`.*
