# S69 — Incident & Carry-Forward Capture (2026-08-12 → 08-13)

| Field | Value |
|---|---|
| Document | `docs/session_notes/S69_incident_carryforward.md` |
| Type | **Interim capture — NOT the doc-close.** Records this session's incident findings + undocumented items so nothing is lost. Full formalisation (ADRs, register updates, CLAUDE.md, reference.json bump) is **carried to S70**. |
| Session shape | Live incident response + two source-level bug fixes shipped. Not a build session. |
| HEAD at capture | `60642fc` at first write; **updated `4326f25`** after end-of-session commits (see §5). Commits this session: `a4bdb4c` (build_ict_htf_zones daily-history fix), `4326f25` (this capture + pin/accel migration + dashboard guide). Local == origin == EC2. |
| Why interim | Per Doc Protocol v4 Rule 3, an incident session's findings are captured at close and formalised next session. Operator explicitly deferred full doc-close to S70. |

---

## 0. TL;DR — what happened

Operator reported "no pin/accel zones on TradingView for days." Pulling that thread uncovered a **stack of failures**, most pre-existing and independent of each other, exposed by an 08-12 morning disk-full incident. Two were fixed at source this session; the rest are documented here for S70.

**The chain, root-caused:**

1. **Disk-full (08-12 03:35 UTC)** — the 7.6 GB root hit 100%, which cascaded: killed the WS feed, corrupted `.env` during the morning token rotation (`sed` on a full disk wrote a literal `<real-token>`), and silently failed the `35 3` breadth-baseline cron. **FIXED same-session** (journal vacuum + npm cache + log truncate → 74%; `.env` repaired; feed + baseline restarted).
2. **pin/accel views timing out** — `v_gex_strike_pin_zone` / `v_gex_strike_accel_zone` recompute across the **entire** `gex_strike_snapshots` table (1.06M rows, 250+ sessions) on every call, then the caller keeps only the newest row. Cost grew with the table until it crossed the PostgREST 8s ceiling (`57014`). **This was the actual reason pin/accel vanished.** **FIXED** via a scoped-view migration (§2).
3. **Pine `bar_index` render bug** — pin/accel boxes anchored to `bar_index ± bar_count`, so they rendered on 15m but fell off-canvas on 1h (the "empty left pane"). **FIXED** via a time-anchor patch to `generate_pine_overlay.py` (§3).
4. **M5 ICT detector frozen since June 2** — `ict_zones` newest row is 2026-06-02 (53 trading days). Detector task runs and succeeds but writes nothing. **NOT FIXED — carried (§4).**
5. **CAS market-structure change (SEBI, live 2026-08-03)** — invalidates fixed 15:30-close timing assumptions across the EOD pipeline. **NEW FINDING, NOT FIXED — carried, and it is the lead P0 (§4).**
6. **Daily OB/FVG layer held only 1 prior session** — `build_ict_htf_zones.py` defined `DAILY_LOOKBACK=60` but never used it; the daily detector evaluated a single prior day while the weekly walked 52 weeks (~19 zones). A **second, independent cause** of the thin daily structure we otherwise attributed to M5 staleness. **FIXED this session** (`detect_daily_zones_history()`, commit `a4bdb4c`, S69-C1). See §2b.

---

## 1. Incident timeline & immediate fixes (08-12, FIXED same-session — for the record)

- **Disk:** `journalctl --vacuum-size=100M` (freed 672M) + `npm cache clean --force` (freed 871M) + `truncate -s 0 logs/*.log` (302M→36K) → **74%, 1.9G free**. Journal capped at `SystemMaxUse=200M` in `/etc/systemd/journald.conf`.
- **`.env` corruption:** the morning `sed` on the full disk wrote the literal placeholder `<real-token>` into line 24 (the `<` also caused a shell "newline unexpected" parse error on every `.env` source). Repaired by re-writing the real token **quoted**, then validating via `KiteConnect.profile()` → `OK: Navin Balan`.
- **Feed:** `merdian-wsfeed.service` was `failed` (disk-full crash + systemd rate-limit latch). Cleared with `reset-failed` → `start`. Duplicate feed PIDs from manual restarts caused `1006` WebSocket churn (one WS per Zerodha key) — killed with `kill -9` (SIGTERM is caught by the reconnect handler; Ctrl-C triggers reconnect, does not kill). Confirmed live: 280k+ ticks/10min under systemd.
- **Breadth baseline:** `equity_intraday_last` was 92h stale (last write 08-07, the `35 3` cron failed on the full disk). Manual `refresh_equity_intraday_last.py` → `Done. Wrote 1312 rows`.
- **08-13 confirmation:** token valid (operator rotates manually 06:00–06:30 as routine — **NOT** an auto-refresh failure, correcting an earlier assumption), feed `active`, `equity_intraday_last` refreshed 08-13 03:35 on its own. Full ingest sweep clean. EOD health check for 08-12: **`[OK]` clean session.**

**Key correction recorded:** the Zerodha token is rotated **manually by the operator every morning** — it is not, and was never, a MALPHA auto-refresh mechanism. The 08-12 "dead token" was `.env` *corruption* from the full-disk `sed`, not expiry. This **removes** "MALPHA token pipeline broken" from the priority list.

---

## 2. FIX SHIPPED — pin/accel view scoping (ADR-grade, DB migration)

**File:** `sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql` (applied to Supabase this session; **not yet committed to git — see §5**).

**Problem:** `v_gex_strike_pin_zone` and `v_gex_strike_accel_zone` (ENH-81, 2026-05-25) run `strike_step`, `peak`/`trough`, and the recursive `walk` across **all** `gex_strike_snapshots` (1.06M rows), producing pin/accel zones for every historical snapshot ever taken. The generator then does `ORDER BY ts DESC LIMIT 1` — discarding all but the newest. A recursive walk over a million rows to return one row. As the table grew, the view crossed 8s and began returning `57014` statement-timeout → the generator's `fetch_positioning_landscape` failed → pin/accel silently dropped from the overlay.

**Fix:** added a `latest_run` CTE (`DISTINCT ON (symbol) ... ORDER BY symbol, ts DESC`) and a `scoped` CTE that inner-joins `gex_strike_snapshots` to it, so every downstream CTE only ever touches the current snapshot (~80 strikes/symbol) instead of all history. **Output byte-identical for the latest snapshot** (all the generator reads); only stops computing pin/accel for ancient history nobody queries. Plus a supporting index `ix_gex_strike_snap_sym_ts ON gex_strike_snapshots (symbol, ts DESC)`.

**Verified post-apply — both views return instantly with today's data:**
- NIFTY: PIN 24,450–24,700 · ACCEL 24,200–24,350
- SENSEX: PIN 78,100–78,700 · ACCEL 77,400–77,800

**S70 obligations:** commit the migration to `sql/`; write **ADR-021** (core-table read-path change, Rule 10 mandatory); update `MERDIAN_System_Map.md` (view definitions) and Decision Index.

**Related pre-existing debt surfaced (do not lose):**
- `τ_pin` / `τ_accel` still **hardcoded 0.3** in the views. The ENH-83 parameterisation (`get_parameter_num('pin.tau.'||symbol)`) is *selected* in the output but the walk still uses literal `0.3` — the closure patch `patch_s39_enh83_view_tau_rewrite.py` **has not run** (TD-S37-01). Noted in the generator source comments.

---

## 2b. FIX SHIPPED & COMMITTED — daily-history OB/FVG (`build_ict_htf_zones.py`, `a4bdb4c`)

**Discovered after the initial capture was written**, while reviewing `git status` at session close. `build_ict_htf_zones.py` had an uncommitted, undocumented change (`# S69-C1-DAILY-HISTORY`) — a real fix, not an accident.

**Problem:** `detect_daily_zones()` evaluates exactly ONE prior session. `DAILY_LOOKBACK = 60` was defined but never referenced, so the daily OB/FVG layer could never accumulate the way the weekly layer does (`detect_weekly_zones()` walks 52 weeks, holds ~19 live zones; the daily held 1). This is a **second, independent cause** of the thin daily intraday structure — distinct from the M5 detector freeze (§4 P0-CARRY-2). We spent much of the session attributing thin intraday structure to M5 staleness; this lookback bug was also contributing.

**Fix:** new `detect_daily_zones_history(daily_ohlcv, symbol, target_date, lookback=DAILY_LOOKBACK)` emitting **OB/FVG only** across the 60-session window. Carefully bounded:
- **PDH/PDL deliberately excluded** — remains the single-prior-day emission from `detect_daily_zones()` (S59 single-emission precondition; looping it would produce ~120 unfiltered levels/symbol and silently reverse that fix).
- **Detection rule identical** to `detect_daily_zones()` — same `OB_MIN_MOVE_PCT` body test, same (non-standard-ICT S2.a) prior-bar-as-OB definition, same `FVG_D_MIN_PCT`, same 3-bar convention, `valid_to=None` (ADR-005/TD-079). Only the session count changes, so the **Exp-15 cohort behind `WR_BY_PATTERN` stays valid** (ADR-009 cohort-translation).
- **Dedup required** by upsert conflict key before batching (TD-070 v2 / Postgres 21000).

**Committed** `a4bdb4c` as its own logical change. **S70 obligation:** this is a signal-affecting code change — evaluate whether it needs a TD entry or ADR note (Rule 10), and verify the daily layer now accumulates as intended on the next build (watch for the TD-070 dedup path firing).

---

## 3. FIX SHIPPED — Pine positioning time-anchor (frontend, not ADR)

**File:** `generate_pine_overlay.py` (patched on Local via `patch_s69_pine_positioning_time_anchor.py`; **backup `_PRE_S69`**; **not yet committed — §5**).

**Problem:** pin/accel `box.new` / `label.new` used `bar_index - 30` / `bar_index + 50` / `bar_index + 90` — bar-**count** offsets. "+50 bars" = 50 × timeframe-minutes of future space: ~12h on 15m (on-screen), ~50h on 1h (off the right edge). Boxes/labels rendered off-canvas on the 1h pane → operator's "empty left pane."

**Fix:** four render lines converted to **time-anchored** `xloc=xloc.bar_time` with millisecond offsets (`time - 172800000` / `time + 259200000` / `time + 432000000` = −2d / +3d / +5d), which are timeframe-independent. `extend=extend.right` unchanged. Fixture-tested (4/4 count==1, ast clean, idempotent).

**S70 obligations:** commit; note in System Map that Local is now the **canonical Pine-generation host** (Local runs the current generator; the box runs an older one that masks M5 staleness — see §4). **Reconcile Local↔box generator divergence** (Local: 106–110 zones honest; box: 139 zones with stale M5 merged).

**Verification still open:** operator to confirm the 1h TV pane now renders pin/accel after reload. Not yet confirmed at capture time.

---

## 4. CARRIED TO S70 — not fixed this session

### P0-CARRY-1 — CAS invalidates EOD close-timing assumptions (NEW, time-sensitive)

**SEBI Closing Auction Session went live 2026-08-03** (NSE + BSE, F&O/Category-I stocks). Verified via web search this session. Material changes:

- **F&O stocks:** continuous trading ends **15:15** (was 15:30) → CAS auction 15:15–15:35 → **single equilibrium closing price** (replaces the 15:00–15:30 VWAP for these names).
- **Index & stock derivatives (NIFTY/SENSEX F&O — MERDIAN's instruments):** trading **extended to 15:40**; post-close 15:50–16:00.
- **Pre-open** similarly restructured from **2026-09-07** (random close 15:08-ish, order-type phases).

**Why this matters to MERDIAN:** the entire EOD pipeline assumes "15:30 = clean settled close." That assumption is now false for F&O names, and several jobs fire *inside* the new auction/extended-derivatives window:

| Job | Schedule | CAS exposure |
|---|---|---|
| `MERDIAN_ICT_EOD` (M5 detector) | **15:35 IST** (Local Task Scheduler) | Fires **during** the 15:15–15:40 auction/derivatives window — bars are no longer settled continuous-session bars. |
| `build_ict_htf_zones.py` daily-close logic | EOD | "Close" definition changed for F&O; daily OHLC may be mid-auction. |
| ambient compiler `eod_spot` / settlement anchor | `0 16` (16:00 IST) | Likely OK (after 16:00) but the **close-price definition** it anchors to changed — verify it reads the CAS equilibrium price, not a stale VWAP. |
| `capture_postmarket_1600` | `30 10` UTC (16:00 IST) | Probably safe (post-everything) — confirm. |
| `market_spot_session_markers` (`40 10`) | 16:10 IST | Confirm close semantics. |

**S70 action:** full audit of every close/EOD-anchored job against the new 15:15/15:35/15:40 reality. Re-time `MERDIAN_ICT_EOD` to fire **after 15:40** (ideally ≥15:45). Reconcile the "settled close" definition for F&O instruments. **This is ADR-grade** — frame as **ADR-022: "CAS (Aug 2026) invalidates fixed 15:30-close timing across the EOD pipeline"** (external market-structure change → ADR-002 philosophy adaptation). **Time-sensitive: live now, silently affecting EOD-timed jobs.**

### P0-CARRY-2 — M5 ICT detector frozen 53 trading days (June 2)

`ict_zones` newest ACTIVE `trade_date` = **2026-06-02**. The `MERDIAN_ICT_EOD` Local task is **healthy** (`State: Ready`, `LastTaskResult: 0`, `LastRunTime: 13-08 17:13`, runner `detect_ict_patterns_runner.py` present, last modified 2026-05-17). It **runs and succeeds but writes nothing** → the table stays frozen at the last day a pattern qualified.

**Root cause (near-certain, per S68 ADR-019/ADR-016 notes):** `OB_MIN_MOVE_PCT = 0.40%` is **empirically unreachable** — 30-session max move NIFTY 0.366% / SENSEX 0.369%. Nothing clears 0.40%, so the detector finds zero order blocks every run. June 2 was the last day a move exceeded 0.40%.

**S70 action:** ADR-016 recalibration (candidate `OB_MIN_MOVE_PCT = 0.25%`). **Governance constraint (ADR-009):** changing it invalidates the WR cohort behind every `WR 84%`/`WR 92%` label — must be done with calibration discipline (SQL committed to `docs/research/` first), not a blind edit. **Also (CAS interaction):** whatever the new threshold, the detector's 15:35 run must be re-timed per P0-CARRY-1 or it reads auction bars.

**Also flagged:** the M5 detector is an **AWS orphan** — it only ever ran on Local Windows Task Scheduler, never on the box (not in AWS crontab, no runner log on EC2). A subsystem that silently depends on the operator's desktop being on at 15:35 is fragile. Consider migrating to the box as part of the fix.

### P0-CARRY-3 — EBS disk undersized (the true infra root cause)

7.6 GB root. This morning's entire cascade traces to it hitting 100%. Journal cap (200M) only delays recurrence; `market_ticks` (rolling) + `gex_strike_snapshots` (1.06M rows, growing) + npm/apt caches will refill it. **S70 action:** grow the EBS volume, and/or DB-side retention on `market_ticks` / `gex_strike_snapshots`. This is the fix that prevents a repeat of 08-12.

### P1-CARRY-4 — EOD health-check coverage gap

`scripts/eod_health_check.py` returned **`[OK]` on 08-12** while pin/accel, M5, and the GEX views were all broken — because it doesn't check those tables. It even disclaims it ("a green DB here does not vouch for Marketview render"). **S70 action:** extend it to assert freshness on `ict_zones`, `gex_strike_snapshots`, `v_gex_strike_pin_zone`, `v_gex_strike_accel_zone`. Had it covered these, all of this would have alerted weeks ago instead of being found by staring at TradingView.

### P1-CARRY-5 — `fetch_positioning_landscape` has no freshness floor

The S69 hardening added a recency floor to `fetch_intraday_zones` (drops stale M5) but **not** to `fetch_positioning_landscape`. With the view now fast this is latent, but if the GEX writer ever stalls, the generator will silently emit stale pin/accel instead of failing loud. **S70 action:** add the same `ts >= today` guard.

### P2-CARRY-6 — token-rotation hardening (operator routine)

The 08-12 corruption came from a `sed` on a full disk with an unquoted value and no post-write validation. Fold the disk-safe pattern into the operator's 06:00 routine: `df -h` guard → `cp .env .env.bak` → **quoted** value → `KiteConnect.profile()` validation. (This is a runbook update, not code.)

---

## 5. NOT YET COMMITTED — git state for S70

**UPDATE (end of session):** the SQL migration and the daily-history fix **were committed** before close. Current state:

**COMMITTED this session** (HEAD `4326f25`, Local == origin == EC2):
- `build_ict_htf_zones.py` daily-history fix — `a4bdb4c`.
- `sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql` (pin/accel view scoping) — `4326f25`. **Already applied to Supabase live earlier in the session**, now also in git.
- `docs/session_notes/S69_incident_carryforward.md` (this file, v1) + `docs/runbooks/reading_the_ambient_trajectory_dashboard.md` — `4326f25`.

**STILL UNCOMMITTED — carried to S70 (deliberately held):**
1. `generate_pine_overlay.py` time-anchor patch — applied on **Local** (`_PRE_S69` backup), **not committed**, **not on the box** (box still runs the old generator). Held because Local↔box generator divergence is unreconciled (§3) — committing now commits the divergence. **S70 must decide the canonical host, then commit + deploy.**
2. `merdian_ict_htf_zones.pine` (regenerated overlay) — Local working copy, uncommitted (follows the generator decision).
3. `merdian_eod_ict.bat` — untracked; part of the M5-detector-orphan cleanup (§4 P0-CARRY-2).

**Also note:** this v1 capture file was committed with a now-stale §0 HEAD line and no mention of the `a4bdb4c` daily-history fix (both discovered/committed after it was written). **This v2 corrects both.** If S70 sees only the committed v1, these two deltas are the correction.

---

## 6. S70 DOC-CLOSE OBLIGATIONS (the deferred formalisation)

When S70 completes documentation, the following are owed per Doc Protocol v4 Rule 3 + Rule 11:

- **ADR-021** — pin/accel view scoping (core-table read-path; Rule 10). Decision Index + CLAUDE.md footer + System Map view defs.
- **ADR-022** — CAS EOD-timing invalidation (external market-structure change). Decision Index + CLAUDE.md footer + Deployment Topology (cron re-timing).
- **ADR-016 follow-through** — `OB_MIN_MOVE_PCT` recalibration, with `docs/research/` SQL per ADR-009 before any register entry.
- **tech_debt.md** — TD entries for: disk resize (P0), health-check coverage gap, `fetch_positioning_landscape` freshness floor, τ hardcode (TD-S37-01 still open), Local↔box generator divergence, M5-detector-as-AWS-orphan.
- **`build_ict_htf_zones` daily-history (`a4bdb4c`, S69-C1)** — evaluate for a TD/ADR note (signal-affecting, Rule 10); confirm the daily layer accumulates and the TD-070 dedup path holds. Update `WR_BY_PATTERN` provenance note if the daily cohort N changes.
- **MERDIAN_System_Map.md** — new/changed views; `gex_strike_snapshots` row count + new index; canonical Pine host.
- **MERDIAN_Deployment_Topology.md** — CAS cron re-timing; disk incident + journal cap; EBS resize when done.
- **MERDIAN_Assumption_Register.md** — refute "15:30 = settled close"; record "token is manually rotated, not auto-refreshed."
- **CURRENT.md** — S69 as last session (this incident).
- **session_log.md** — S69 entry.
- **merdian_reference.json** — v47 → v48; source entry.
- **CLAUDE.md** — v1.45 → v1.46; settled-decision footers from ADR-021/022.

---

## 7. S70 PRIORITY STACK (revised from this session's findings)

1. **P0 — CAS EOD-timing audit** (ADR-022) — live now, silently corrupting EOD-timed jobs. Re-time `MERDIAN_ICT_EOD` past 15:40 first.
2. **P0 — M5 detector recalibration** (ADR-016, `OB_MIN_MOVE_PCT` 0.40→0.25 with ADR-009 discipline).
3. **P0 — EBS disk resize** — the infra root cause of 08-12.
4. **P0 — commit + deploy** the two shipped fixes (§5); write ADR-021.
5. **P1 — health-check coverage** + `fetch_positioning_landscape` freshness floor.
6. **P1 — Local↔box generator reconciliation**; migrate M5 detector off Local Task Scheduler.
7. **Then — the original S69 P0 (deferred all session):** ENH-119 momentum layer (vwap debt close → conditioned tile → horizon ladder → `ret_session` lane). *This never started — the entire session was the incident.*

**Banked backlog (unchanged):** TD-S60-NEW-5 (core.config Windows BASE_DIR); ENH-SDM `three_wick_reversal`; `datetime.utcnow()` deprecation; momentum vwap-unit scaling; 68-row `ohlc()` tail; ENH-117 branded sign-in; ENH-118 vol-regime lens.

---

*Interim capture — Session 69, 2026-08-13. This is NOT the doc-close; it is the carry-forward record so the incident findings survive to S70, where ADR-021, ADR-022, the ADR-016 follow-through, and the full register/CLAUDE.md/reference.json formalisation will be completed. The pin/accel data + render fixes shipped this session; everything else is documented above as carried.*
