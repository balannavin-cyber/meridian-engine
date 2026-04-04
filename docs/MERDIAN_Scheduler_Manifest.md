# MERDIAN Windows Task Scheduler — Ownership Manifest
**Last updated:** 2026-04-04 (V18C session)  
**Git hash at creation:** 3ec6212  
**Authority:** This document is the single authoritative record of all Windows Task Scheduler tasks for MERDIAN Local.

---

## Governing Rules

- **Supervisor owns runner startup exclusively.** No other task may launch `run_option_snapshot_intraday_runner.py` directly.
- **All tasks must run `-WindowStyle Hidden`.** No popup terminal windows.
- **trading_calendar is the execution control plane.** Scripts must check `is_open` before acting on market data.
- **One task, one job.** No repetition intervals except where explicitly noted and justified.

---

## Active Tasks (State: Ready)

### MERDIAN_Dhan_Token_Refresh
| Field | Value |
|---|---|
| Trigger | Daily, Mon–Fri, 08:15 IST (02:45 UTC) — fires once at 08:15 IST |
| Script | `run_token_refresh.bat` |
| What it does | Runs `refresh_dhan_token.py` → writes fresh Dhan token to `.env` → syncs token to `system_config.dhan_api_token` in Supabase |
| Owner | Local Windows machine |
| Notes | AWS no longer runs its own token refresh. AWS pulls token from Supabase at 09:10 IST via cron. Fixed V18C: was double-firing due to repetition interval. |

---

### MERDIAN_Intraday_Supervisor_Start
| Field | Value |
|---|---|
| Trigger | Daily, Mon–Fri, 09:14 IST |
| Script | `start_merdian_intraday_supervisor.ps1` |
| What it does | Starts `gamma_engine_supervisor.py`. Supervisor then starts and manages `run_option_snapshot_intraday_runner.py`. |
| Owner | This task is the **sole owner** of runner startup |
| Notes | Fixed V18C: was Disabled while legacy `MERDIAN_Intraday_Session_Start` was incorrectly enabled. Now correctly enabled. |

---

### MERDIAN_Watchdog
| Field | Value |
|---|---|
| Trigger | Repeating every 5 minutes (PT5M) during session hours |
| Script | `watchdog_check.ps1` |
| What it does | Checks if `gamma_engine_supervisor.py` process is alive. If dead during market hours on a trading day: fires Telegram alert + restarts via `MERDIAN_Intraday_Supervisor_Start` |
| Owner | Standalone — no dependency on other tasks |
| Notes | Rebuilt V18C. Old script referenced non-existent tasks. New script has trading_calendar guard (SKIP on holidays) and market hours guard (09:00–15:35 IST only). Repetition interval is intentional for watchdog pattern. |

---

### MERDIAN_Market_Tape_1M
| Field | Value |
|---|---|
| Trigger | Daily, Mon–Fri, scheduled start (verify exact time) |
| Script | `run_market_tape_1m.py` |
| What it does | Captures 1-minute spot + futures tape. Archives to historical tables. Session-controlled via trading_calendar. |
| Owner | Standalone |
| Notes | Was Disabled in V18B (OI-03: token conflict assessment). Re-enabled V18C after confirming no token conflict — both runners read same `.env` value. |

---

### MERDIAN_IV_Context_0905
| Field | Value |
|---|---|
| Trigger | Daily, Mon–Fri, 09:05 IST |
| Script | IV context capture script (verify script name) |
| What it does | Once-per-morning IV context snapshot before session opens |
| Owner | Standalone |

---

### MERDIAN_Market_Close_Capture
| Field | Value |
|---|---|
| Trigger | Daily, Mon–Fri, at or near 15:30 IST |
| Script | Market close capture script (verify script name) |
| What it does | Captures closing market state snapshot |
| Owner | Standalone |

---

### MERDIAN_Post_Market_1600_Capture
| Field | Value |
|---|---|
| Trigger | Daily, Mon–Fri, 16:00 IST |
| Script | Post-market capture script (verify script name) |
| What it does | Captures post-market data at 16:00 IST |
| Owner | Standalone |

---

### MERDIAN_Session_Markers_1602
| Field | Value |
|---|---|
| Trigger | Daily, Mon–Fri, 16:02 IST |
| Script | Session markers script (verify script name) |
| What it does | Writes session boundary markers after close |
| Owner | Standalone |

---

### MERDIAN_EOD_Breadth_Refresh
| Field | Value |
|---|---|
| Trigger | Daily, Mon–Fri, after market close |
| Script | EOD breadth refresh script (verify script name) |
| What it does | Refreshes end-of-day breadth data |
| Owner | Standalone |

---

## Disabled Tasks

### MERDIAN_Intraday_Session_Start
| Field | Value |
|---|---|
| State | **DISABLED — do not re-enable** |
| Reason | Legacy direct launcher. Was incorrectly enabled while supervisor task was disabled. Launched `run_option_snapshot_intraday_runner.py` directly, competing with supervisor. Disabled V18C. |
| Replacement | `MERDIAN_Intraday_Supervisor_Start` |

---

## AWS Cron Schedule (for reference)

| Time (UTC) | Time (IST) | Job |
|---|---|---|
| 03:55 Mon–Fri | 08:25 IST | `pull_token_from_supabase.py` — pulls Dhan token written by Local at 08:15 |
| 03:38 Mon–Fri | 09:08 IST | `capture_market_spot_snapshot_local.py` — pre-open spot capture |
| 03:45 Mon–Fri | 09:15 IST | `run_merdian_shadow_runner.py` — AWS shadow pipeline |
| 10:30 Mon–Fri | 16:00 IST | `capture_postmarket_1600.py` |
| 10:40 Mon–Fri | 16:10 IST | `run_equity_eod_until_done.py` |

---

## Items Requiring Verification on Next Live Session

- Exact trigger times for: `MERDIAN_IV_Context_0905`, `MERDIAN_Market_Close_Capture`, `MERDIAN_Post_Market_1600_Capture`, `MERDIAN_Session_Markers_1602`, `MERDIAN_EOD_Breadth_Refresh`
- Exact script names for the above tasks
- S-04: Confirm pipeline runs through 15:30 without the 15:10 stop (now that duplicate launcher is disabled)
