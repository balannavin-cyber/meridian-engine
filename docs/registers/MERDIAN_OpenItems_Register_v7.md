# MERDIAN — Master Open Items & Enhancement Status Register

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Edition | v7 — Session Update — 2026-04-13 |
| Source documents | Open Items Register v6 · Session 2026-04-13 |
| Current latest appendix | V18F v2 (2026-04-12) |
| Authority | This document aggregates and does not supersede any master. |

---

### Session Changes (2026-04-13)

**Completed this session:**
- OI-07 CLOSED — experiment_15b date type fix + lot size correction. Run complete.
- OI-08 CLOSED — ENH-38 Kelly sizing live end-to-end (runner → ict_zones → signal_snapshots)
- OI-09 CLOSED — capital_tracker live, seeded, controllable via set_capital.py + dashboard
- OI-10 CLOSED — Signal Rule Book v1.1 written (docs/research/MERDIAN_Signal_RuleBook_v1.1.md)

**Also completed:**
- Signal dashboard live (merdian_signal_dashboard.py, port 8766)
- hist_spot_bars_1m backfill Apr 7–10 via Zerodha Kite (3,000 rows)
- Capital floor lowered to ₹10K for trial runs

**Open items added:** None

**Shadow gate:** Session 9 today (Mon 2026-04-14), session 10 tomorrow (Tue 2026-04-15)

---

### Research Session Changes (2026-04-11 through 2026-04-12)

**Experiments completed:** 2 (full year), 2b, 2c, 2c v2, 5, 8, 10c, 15, 16 — all 11 scheduled experiments complete except 15b (date type fix pending, not blocking).

**Key decisions made:**
- Futures experiments permanently closed — options only
- INR 50L capital ceiling and INR 25L sizing freeze established
- Strategy D (Full Kelly tiered) selected for live implementation
- T+30m exit confirmed over ICT structure break
- MEDIUM (1H zone) context confirmed — keep in ENH-37
- BEAR_OB AFTERNOON hard skip rule established
- Signal Rule Book v1.1 ready to write (ENH-40)

**Open items added:** OI-07, OI-08, OI-09, OI-10

**Shadow gate:** 8/10 sessions complete (Mon/Tue = sessions 9 and 10)

---

## Section 1 — Critical Fixes

### C-07b — Pre-open capture gap (09:00-09:08 window)
**Status:** OPEN

Supervisor starts at 09:14 IST, missing the pre-open 09:08 capture window. AWS cron captures at 09:08 but only 4–5 snapshots per session — insufficient for bar construction. Architectural fix required.

All other C-series items: CLOSED — see v5.

---

## Section 5 — Open Items Register (OI series)

### OI-01 through OI-06
**Status:** CLOSED — see v5

---

### OI-07 — Experiment 15b completion
**Status:** CLOSED — 2026-04-13

Fix: `_daily_str = {str(k): v for k, v in daily_ohlcv.items()}` passed to `detect_daily_zones`. LOT_SIZE corrected: NIFTY=75 (majority of backtest year), SENSEX=20.

Results: Strategy C combined +6,764% (₹2.75Cr). Strategy D combined +16,249% (₹6.54Cr). MERDIAN-filtered universe (Exp 16) outperforms pure ICT (Exp 15b) — regime filter confirmed additive.

---

### OI-08 — ENH-38 Live Kelly Sizing Implementation
**Status:** CLOSED — 2026-04-13

End-to-end implementation: `merdian_utils.py` (Kelly functions + lot cost), `detect_ict_patterns_runner.py` (reads capital_tracker, writes lots to ict_zones), `build_trade_signal_local.py` (forwards lots to signal_snapshots). Schema: ict_zones +3 cols, signal_snapshots +3 cols. See ENH-38 in Enhancement Register v6 for full detail.

---

### OI-09 — Capital Tracker Table
**Status:** CLOSED — 2026-04-13

Live in Supabase. Capital floor lowered to ₹10K for trial runs. Control via `set_capital.py` CLI or dashboard SET button.

---

### OI-10 — Signal Rule Book v1.1
**Status:** CLOSED — 2026-04-13

`docs/research/MERDIAN_Signal_RuleBook_v1.1.md` written. 13 rule changes: 4 NEW, 3 CHANGED, 5 CONFIRMED, 1 CLOSED. Supersedes v1.0 (git fcdf620).

| # | Rule | Type |
|---|---|---|
| 1 | BEAR_OB AFTERNOON (13:00–14:30) → HARD SKIP. 17% WR. | NEW |
| 2 | BULL_OB AFTERNOON (13:00–15:00) → TIER1. 100% WR. | NEW |
| 3 | BULL_FVG\|HIGH\|DTE=0 → TIER1. 87.5% WR. | NEW |
| 4 | JUDAS_BULL confirmation → T+15m. T2 rate 12%→44%. | NEW |
| 5 | BEAR_OB DTE=0/1 → combined structure. Not pure PE. | CHANGED |
| 6 | BULL_FVG unconfluenced → TIER3 min sizing. 50.3% WR. | CHANGED |
| 7 | BEAR_FVG HIGH context → remove zone filter. | CHANGED |
| 8 | T+30m exit → CONFIRMED FINAL. | CONFIRMED |
| 9 | BEAR_OB MORNING → CONFIRMED TIER1. 100% WR. | CONFIRMED |
| 10 | BULL_OB DTE=0 → CONFIRMED TIER1. 100% WR. | CONFIRMED |
| 11 | 1H zones (MEDIUM) → CONFIRMED in ENH-37. | CONFIRMED |
| 12 | MOM_YES → CONFIRMED strongest filter. | CONFIRMED |
| 13 | Exit timing question → CLOSED. | CLOSED |

---

## Section 6 — Shadow Gate Tracking

| Session | Date | Status |
|---|---|---|
| 1–8 | 2026-04-06 to 2026-04-11 | PASSED |
| 9 | 2026-04-14 Monday | **PENDING — today** |
| 10 | 2026-04-15 Tuesday | PENDING |

Post-gate: Phase 4 promotion decision → ENH-41 code build → Execution layer Phase 1 → capital auto-update → ENH-42 WebSocket (deferred).

---

*MERDIAN Open Items Register v7 — 2026-04-13*
*Supersedes v6 (2026-04-12).*


### OI-11 — HTF Zone Rebuild Not Automated on AWS
| Field | Value |
|---|---|
| Priority | MEDIUM |
| Opened | 2026-04-14 |
| Blocking | ENH-51c (AWS primary) — if runner migrates to AWS but HTF zones not rebuilt, ICT detector uses stale zones |
| Description | build_ict_htf_zones.py --timeframe D is currently MANUAL pre-market only. Must be added as AWS cron before AWS becomes primary compute. |
| Fix | Add to MERDIAN AWS crontab: 30 3 * * 1-5 cd /home/ssm-user/meridian-engine && /bin/bash -lc 'set -a; . .env; set +a; python3 build_ict_htf_zones.py --timeframe D >> logs/htf_zones.log 2>&1' |
| Build when | Before ENH-51c (AWS primary promotion) |

---

### OI-12 — market_ticks Retention Cron Not Set
| Field | Value |
|---|---|
| Priority | MEDIUM |
| Opened | 2026-04-14 |
| Blocking | Storage growth — market_ticks grows ~1,007 rows per tick event during market hours |
| Description | market_ticks table has no retention policy. During live market hours at full tick frequency, table will grow rapidly. 2-day retention recommended. |
| Fix | Add Supabase pg_cron job: SELECT cron.schedule('delete-old-ticks', '0 20 * * 1-5', $$DELETE FROM market_ticks WHERE ts < now() - interval ''2 days''$$); OR add to AWS post-market cron. |
| Build when | Before ENH-51b (pipeline reads market_ticks) |

---

### OI-13 — Telegram Credentials Not in .env
| Field | Value |
|---|---|
| Priority | MEDIUM |
| Opened | 2026-04-14 |
| Blocking | merdian_exit_monitor.py Telegram alerts — currently console-only |
| Description | TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID missing from local .env. Exit monitor runs and polls correctly but cannot send Telegram alerts at T+30m. |
| Fix | Add to C:\GammaEnginePython\.env: TELEGRAM_BOT_TOKEN=<token> and TELEGRAM_CHAT_ID=<chat_id>. Create bot via @BotFather if not already done. |
| Build when | Next session |

---

