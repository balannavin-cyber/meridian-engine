# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-04-29 (Session 13 — engineering / live trading day) |
| **Concern** | ENH-75 (PO3 Live Session Bias Detection) — required. ENH-76/77 if time. |
| **Type** | Engineering + live operations. Full trading day. |
| **Outcome** | DONE: ENH-75, ENH-76, ENH-77, Exp 42, ENH-84/85/86 filed, breach detection fix, WS feed task, Pine entry-band + colors + toggles. ENH-85 built then reverted (premature). |
| **Git start → end** | `15720d6` → pending commit (Sessions 11+12+13 all uncommitted). |
| **Local + AWS hash match** | Local ahead of origin. AWS token refreshed; preflight PASS; AWS idle (not reactivated as shadow). |
| **Files changed (code)** | `detect_po3_session_bias.py` (NEW), `build_trade_signal_local.py` (ENH-75/76/77 patches), `build_ict_htf_zones.py` (breach recheck order fix), `generate_pine_overlay.py` (entry-band + colors + toggles), `run_ict_htf_zones_daily.bat` (hourly zones added) |
| **Files added (scripts)** | `detect_po3_session_bias.py`, `run_po3_session_bias_once.bat`, `run_ws_feed_zerodha.bat` |
| **Tables changed** | `po3_session_state` (NEW), `signal_snapshots` (+`po3_session_bias` column) |
| **Cron / Tasks added** | `MERDIAN_PO3_SessionBias_1005` (Mon-Fri 10:05 IST), `MERDIAN_WS_Feed_0900` (Mon-Fri 09:00 IST) |
| **`docs_updated`** | YES — session_log, CURRENT.md, Enhancement Register |

### What Session 13 did, in bullets

**ENH-75 — PO3 Live Session Bias Detection (SHIPPED):**
- `detect_po3_session_bias.py` — reads prior session PDH/PDL from `hist_spot_bars_5m`, today's OPEN-window ticks from `market_spot_snapshots`, applies Exp 35C filters (wick ≥0.05%, close-back ≥0.10% within 6 bars, gap 0–0.5%, reversal speed ≠T+2, depth not in 0.10–0.20% ambiguous zone)
- `po3_session_state` table created — UPSERT per symbol per day with `po3_session_bias`, `pdh_used`, `pdl_used`, `sweep_depth_pct`, `reversal_bar_idx`, `gap_open_pct_used`
- `signal_snapshots.po3_session_bias` column added (DDL: `ENH75_DDL.sql`)
- `build_trade_signal_local.py` patched — `_get_po3_bias()` reads from `po3_session_state` per cycle
- `MERDIAN_PO3_SessionBias_1005` task registered — fires Mon-Fri 10:05 IST
- Live verified 10:05:03 IST: NIFTY 46 ticks → 9 5m bars, gap_open_pct=+0.416%, BEAR wick at 09:15 no reversal → PO3_NONE. Both symbols UPSERTED. ✓
- `market_spot_session_markers` NOT used — live column names differ from docs (`open_0915` → `open_0915_ts`). Open_0915 derived from first OPEN-window tick; gap computed from prev_close in `hist_spot_bars_5m`.

**ENH-76 — BEAR_OB MIDDAY gate on PO3_BEARISH (SHIPPED):**
- Window 11:30–13:30 IST. If `ict_pattern=BEAR_OB` and `action=BUY_PE` in MIDDAY: gate passes only if `po3_session_bias=PO3_BEARISH`. Otherwise → DO_NOTHING.
- Evidence: Exp 40 — 88.2% WR T+30m (N=17 SENSEX), +39.1pp lift over baseline.

**ENH-77 — BULL_OB AFTERNOON SENSEX gate on PO3_BULLISH (SHIPPED):**
- Window 13:30–15:00 IST. SENSEX: gate passes only if `po3_session_bias=PO3_BULLISH`. NIFTY: hard skip always (50% WR).
- Evidence: Exp 40 — SENSEX 73.7% WR T+30m (N=19), +16.8pp lift.

**Exp 42 — Composition rate (DONE — research):**
- BEAR_OB MIDDAY occurs in 72.5% of all sessions (169/233 NIFTY, 166/229 SENSEX). Unfiltered WR 48%, EV negative. Pattern is abundant; PO3_BEARISH is the rare gate (~7% of sessions). Confirms ENH-76 design: the session bias is the bottleneck, not the pattern.

**Pine generator overhaul (SHIPPED):**
- Entry-band clipping: BEAR_OB/PDH zones capped at 80pt (NIFTY) / 250pt (SENSEX), showing resistance entry band only. Dashed far-edge line with label marks original zone boundary.
- Color scheme: BULL_OB=solid green (#1B8C3E), BULL_FVG=lime (#7EC85A), BEAR_OB=dark crimson (#8B0000), BEAR_FVG=salmon (#E05555). Opacity: T1 full, T2 medium, T3 ghost.
- TradingView settings toggles: Show Weekly/Daily/Hourly zones, Show OBs/FVGs/PDH-PDL. All generated draw_zone calls include `show` parameter wired to correct toggle.
- `bar_index` negative guard: `math.max(0, bar_index - look_back)` — fixes blank chart on daily TF for zones >252 trading days old.
- Symbol detection moved before `draw_zone` function — fixes forward-reference crash.
- Hourly zones (`--timeframe H`) added to `run_ict_htf_zones_daily.bat` — runs after W+D rebuild at 08:45 IST.

**Breach detection order fix (SHIPPED):**
- `recheck_breached_zones()` was called BEFORE `upsert_zones()`. Upsert wrote `status='ACTIVE'` on every run, overwriting BREACHED. Fix: recheck now runs AFTER all upserts for each symbol.
- Verified: may-09 BULL_OB (24,008–24,411), aug-08 BULL_OB (24,363–24,600), apr-24 BULL_OB (23,897–24,391) all correctly BREACHED after fix.

**WS feed task registered:**
- `MERDIAN_WS_Feed_0900` — fires Mon-Fri 09:00 IST, starts `ws_feed_zerodha.py` as long-running process (8hr limit), logs to `logs/ws_feed_zerodha.log`.
- Root cause: `ws_feed_zerodha.py` not started by any supervisor or task — `market_ticks` table empty all day — breadth ingest returned 0 ticks all session. Breadth regime read stale yesterday's BEARISH row. Fixed for tomorrow.

**AWS:**
- Token refreshed via SSM. Preflight PASS (all 4 stages). `merdian_pm.py` needed two fixes for Linux: `BASE = Path('/home/ssm-user/meridian-engine')` and `creationflags=CREATE_NO_WINDOW` removed. AWS left idle — not reactivated as shadow this session.

**ENH-85 built and reverted:**
- PO3 direction lock patch written, applied, then reverted. Reason: locking direction for full session prevents legitimate intraday reversals. Needs proper experiment (Exp 43) before re-attempting. `build_trade_signal_local.pre_enh85.bak` remains on disk.

---

## What went wrong today

| Issue | Root cause | Fixed? |
|---|---|---|
| Breadth = 0 all session | `ws_feed_zerodha.py` not started; `market_ticks` empty | ✅ Task registered |
| Breadth regime BEARISH (market BULLISH) | Stale apr-28 row read all day | ✅ Will resolve tomorrow |
| BULL_OB zones not BREACHED | `recheck_breached_zones()` ran before `upsert_zones()` | ✅ Fixed |
| Pine zones blank on daily TF | Negative `bar_index - look_back` | ✅ Fixed |
| NIFTY BLOCKED at open | gamma_regime=NO_FLIP → ENH-35 gate | Not a bug |
| SENSEX BLOCKED all day | DTE=1 (expiry tomorrow) | Not a bug |
| Signal flip-flop BUY_CE between BUY_PEs | ENH-55 `ret_session` crosses zero intraday | Deferred → Exp 43 |
| EXIT AT showing wrong time | TD-038 UTC not IST | Carried forward |
| AWS terminal frozen | `merdian_start.py` Windows-only script run on Linux | Resolved via reboot |

---

## This session → next session

> Session 14. Primary candidates:

**Candidate A (high priority) — ENH-78: DTE<3 PDH sweep → current-week PE rule**
- Small patch to signal engine. Evidence: Exp 35D — PDH DTE<3 current-week PE = 90.9% WR (N=11), +125% SENSEX option. No prerequisite.

**Candidate B — Exp 43: Signal Direction Stability**
- Research session. Question: what is the minimum stability criterion for `direction_bias` before firing a signal? Options: persistence filter (N consecutive cycles same direction), slower momentum anchor (ret_30m not ret_session), hysteresis. Query `hist_pattern_signals` for direction flip-flop frequency and outcome correlation.

**Candidate C — TD-038: EXIT AT shows UTC not IST**
- Small dashboard fix. `card()` computes `exit_ts = signal_ts + 30min` — needs IST conversion. Live trading risk.

**Candidate D — ENH-84: Dashboard "Refresh Zones + Pine" button**
- Small. Calls `build_ict_htf_zones.py --timeframe H` + `generate_pine_overlay.py` on demand from dashboard. Returns updated `.pine` file for copy-paste.

**Candidate E — ENH-86: Dashboard WIN RATE section redesign**
- Medium. Separate signal quality (WR, EV, N) from execution (tier, lots, BLOCKED/ALLOWED) into two visual blocks. Remove tier from signal quality display.

**DO_NOT_REOPEN for Session 14:**
- ENH-75/76/77 design — shipped.
- Exp 42 composition rate — answered (72.5% session frequency, PO3 is the gate).
- ENH-85 direction lock — deferred to Exp 43. Do NOT re-implement without experiment backing.
- Breach detection ordering — fixed.
- Pine entry-band clipping approach — settled.
- ADR-002 principles — settled.

---

## Live state snapshot (Session 14 start)

**Environment:** Local Windows primary (all 5 processes running). AWS idle (token fresh, preflight clean, code 2+ weeks behind local).

**Git state:** Local ahead of origin. Sessions 11+12+13 all uncommitted. Pending commit covers: Session 11 experiment scripts, Session 12 docs (ADR-002, Enhancement Register rewrite, merdian_reference.json v7), Session 13 code (ENH-75/76/77, breach fix, Pine generator, task registrations).

**Active TDs:**
- TD-029 (S2) — `hist_spot_bars` pre-04-07 TZ bug. Workaround: `replace(tzinfo=None)`.
- TD-032 (S2) — Dashboard ↔ DB inconsistency. PATCHED Session 11 extension. Pending 10-cycle live verification. **BLOCKER for ENH-46-C.**
- TD-034 (S2) — `hist_atm_option_bars_5m` undersampled on dte=0.
- TD-035 (S3) — `wcb_regime` NULL since 2026-03-19. direction_bias unreliable on breadth-driven days.
- TD-038 (S2 live risk) — EXIT AT shows UTC not IST.
- TD-039 (S3) — SENSEX DTE=2 on expiry day (expected 0).
- TD-NEW-A (S2) — CLOSED Session 13: breach recheck order fixed.
- TD-NEW-B (S2) — CLOSED Session 13: WS feed task registered.

**Rules (non-negotiable):**
- Rule 14: `hist_pattern_signals.ret_30m` is PERCENTAGE POINTS — divide by 100.
- Rule 15: Supabase hard cap 1000 rows/request — `page_size=1000`.
- Rule 16: `hist_spot_bars_5m.bar_ts` stored IST as +00:00 — `replace(tzinfo=None)`.
- Bug B4: `hist_spot_bars_5m` has no `is_pre_market` column — filter by time.
- Rule 5: All patch scripts end with `ast.parse()` validation before writing.
- Encoding: read `decode('utf-8-sig')`, write CRLF-aware.

**Active ENH status:**
- ENH-46-C: BLOCKED on TD-032.
- ENH-46-D: SHIPPED (entry-band Pine generator + toggles + colors).
- ENH-75: SHIPPED + live-verified.
- ENH-76: SHIPPED.
- ENH-77: SHIPPED.
- ENH-78: PROPOSED — next build target.
- ENH-79: PROPOSED.
- ENH-80–83: PROPOSED — sequenced after ENH-75 data accumulates.
- ENH-84: PROPOSED — dashboard Pine refresh button.
- ENH-85: PROPOSED-DEFERRED — pending Exp 43.
- ENH-86: PROPOSED — dashboard WIN RATE redesign.

**Proven edges (live from today):**

| Edge | WR | N | EV/trade | Gate | Status |
|---|---|---|---|---|---|
| E4 BEAR_OB MIDDAY + PO3_BEARISH | 88.2% T+30m | 17 | 116.5 pts SENSEX | ENH-76 | **LIVE** |
| E5 BULL_OB AFT + PO3_BULLISH (SENSEX) | 73.7% T+30m | 19 | 35.5 pts SENSEX | ENH-77 | **LIVE** |
| E1 PDH First-Sweep → PO3 bias | 93.3% EOD | 15 | ~97 pts NIFTY | ENH-75 | **LIVE** |
| E3 PDH DTE<3 → current-week PE | 90.9% EOD | 11 | +125% option SENSEX | ENH-78 | PROPOSED |
| E6 PWL Refined Weekly | 76.9% EOW | 13 | +534 pts SENSEX | ENH-79 | PROPOSED |
| E7 PWL Weekly + Daily Confluence | 100% EOD | 5 | T+2D +534 pts SENSEX | ENH-79 | PROPOSED |

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-04-29 (end of Session 13).*
