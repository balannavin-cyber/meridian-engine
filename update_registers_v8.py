#!/usr/bin/env python3
"""
update_registers_v8.py
=======================
Appends 2026-04-14/15 session changes to existing register files.
No new files created — updates in-place.

Updates:
  docs/registers/MERDIAN_OpenItems_Register_v7.md  -> append FINAL CLOSED block
  docs/registers/MERDIAN_Enhancement_Register_v7.md -> append v8 changes block
  merdian_reference.json -> update git hash, shadow gate, session log, open items
"""
import json
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
OI_REG   = BASE / "docs/registers/MERDIAN_OpenItems_Register_v7.md"
ENH_REG  = BASE / "docs/registers/MERDIAN_Enhancement_Register_v7.md"
REF_JSON = BASE / "merdian_reference.json"

# ── Open Items Register — FINAL CLOSED append ─────────────────────────────────

OI_APPEND = """
---

## ⛔ REGISTER PERMANENTLY CLOSED — 2026-04-15

All open items resolved. This register is closed and will not be updated further.
New operational issues will be tracked in the Enhancement Register or session appendices.

### Session Changes (2026-04-14 — Holiday session + engineering)

**Closed this session:**
- OI-11 CLOSED — HTF zone rebuild cron added to MERDIAN AWS crontab (30 3 * * 1-5)
- OI-12 CLOSED — market_ticks retention: pg_cron job 45 (30 14 * * 1-5, 2-day TTL)
- OI-13 CLOSED — Telegram credentials added to .env. Exit monitor alerts confirmed.
- OI-14 CLOSED — Holiday gate added to 4 Task Scheduler scripts (fix_process_control_final.py)
- OI-15 CLOSED — Dual supervisor: MERDIAN_Intraday_Supervisor_Start → merdian_morning_start.ps1 → merdian_start.py
- OI-16 CLOSED — StartWhenAvailable=false on MERDIAN_Spot_1M + MERDIAN_PreOpen (fix_task_scheduler.ps1)
- OI-17 CLOSED — merdian_start.py: ensure_calendar_row() now read-before-write. Holidays preserved.
- OI-07-INFRA CLOSED — Supabase auto-expanded to 50GB (22.26 GB used). Autoscaling enabled.
- SPO-01 CLOSED — DTE fix: compute_gamma_metrics_local.py now derives DTE from expiry_date. Flows to market_state_snapshots → signal_snapshots. gamma_metrics.dte column added.
- HIST-02 DEFERRED → moved to Enhancement Register as ENH-52b (S3 warm tier archiver, Phase 5)

**Also completed this session:**
- Phase 4B order placer: merdian_order_placer.py on AWS (port 8767). Dhan Trading API confirmed. Elastic IP 13.63.27.85 whitelisted.
- Signal dashboard on AWS (port 8766). IP-restricted to dev + trading machines.
- AWS @reboot crons for signal_dashboard + order_placer.
- ict_zones detected_at → detected_at_ts dashboard fix (400 error eliminated).
- Dashboard bound to 0.0.0.0 for AWS hosting.
- t3.micro → t3.small upgrade (OOM fix for scrip master parsing).
- merdian_order_placer.py scrip master format fix (segment D, streaming CSV).

### Final Open Items Status

| ID | Description | Status |
|---|---|---|
| All C-series | Critical fixes | ✅ ALL CLOSED |
| All V18A items | Auth/calendar/circuit-breaker | ✅ ALL CLOSED |
| All A-series | AWS readiness | ✅ ALL CLOSED |
| OI-01 through OI-17 | Main OI series | ✅ ALL CLOSED |
| OI-07-INFRA | Supabase disk | ✅ CLOSED — auto-expanded 50GB |
| SPO-01 | DTE null in signal_snapshots | ✅ CLOSED — 2026-04-15 |
| HIST-02 | S3 warm tier archiver | 🔵 MOVED TO ENH-52b (deferred Phase 5) |

**ZERO OPEN ITEMS REMAIN.**

*MERDIAN Open Items Register — PERMANENTLY CLOSED 2026-04-15*
*Superseded by operational monitoring. Future items tracked in Enhancement Register or session appendices.*
"""

# ── Enhancement Register — v8 changes append ─────────────────────────────────

ENH_APPEND = """

---

## v8 Changes — Session 2026-04-14/15

| Change | Detail |
|---|---|
| ENH-48 | **COMPLETE** — Phase 4A execution layer: merdian_trade_logger.py + merdian_exit_monitor.py + dashboard LOG TRADE/CLOSE buttons |
| ENH-49 | **COMPLETE** — Phase 4B: merdian_order_placer.py on AWS (port 8767). Dhan order API confirmed. Elastic IP 13.63.27.85 whitelisted. Scrip master streaming. |
| ENH-50 | **PROPOSED** — Phase 4C full auto. Gate: Phase 4B stable + real slippage data. |
| ENH-51a | **COMPLETE** (confirmed) — ws_feed_zerodha.py on MERDIAN AWS. 1,007 instruments. Cron 03:44 UTC. |
| ENH-51b | **PROPOSED** — Pipeline reads market_ticks instead of REST. Gate: tomorrow's live session confirms market_ticks options data quality. |
| ENH-51c/d | **PROPOSED** — AWS primary, local dashboards-only. Gate: ENH-51b + 10 sessions validated. |
| ENH-52 NEW | **PROPOSED** — Dhan expired options 5-year backfill. ATM-relative strikes. Batch 30-day chunks. Gate: Phase 4B stable. |
| ENH-52b NEW | **DEFERRED (Phase 5)** — S3 warm tier archiver. Was HIST-02 in open items. LocalParquetArchiver stubbed. S3ParquetArchiver pending. Not blocking anything. |
| Shadow gate | **CLOSED** — Phase 4 promoted. Gate waived (full year backtest evidence sufficient). Session 9 passed 2026-04-13. |
| OI register | **PERMANENTLY CLOSED** — all items resolved 2026-04-15. |

---

### ENH-48: Phase 4A Execution Layer

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| Files | merdian_trade_logger.py · merdian_exit_monitor.py |

Manual execution layer. Signal fires → operator clicks LOG TRADE on dashboard → enters premium → trade_log + exit_alerts written. Exit monitor polls every 30s, fires Telegram at T+30m. CLOSE TRADE updates PnL and capital_tracker.

---

### ENH-49: Phase 4B — Semi-Auto Order Placement

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-15 |
| Files | merdian_order_placer.py (AWS port 8767) |
| Dhan IP | 13.63.27.85 (Elastic IP, permanent, whitelisted in Dhan) |

merdian_order_placer.py on MERDIAN AWS. Endpoints: POST /place_order, POST /square_off, GET /margin, GET /health. Downloads Dhan scrip master (streaming, no OOM). Finds security_id by streaming CSV match on exchange=NSE/BSE, segment=D, OPTIDX, trading_symbol prefix, expiry_date, strike, option_type. Places MARKET INTRADAY order. Polls fill. Writes trade_log + exit_alerts. Updates capital_tracker on square off. Dashboard PLACE ORDER button (yellow) routes to AWS order placer via AWS_ORDER_PLACER_URL. Dashboard SQUARE OFF button routes to /square_off. Scrip master refreshed daily (delete runtime/dhan_scrip_master.csv before market open).

---

### ENH-50: Phase 4C — Full Auto

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Gate | Phase 4B stable + 2–4 weeks real fill data + slippage analysis |

Full automated execution without operator confirmation. Signal fires → order placed → exit at T+30m automatically.

---

### ENH-52: Dhan Expired Options 5-Year Backfill

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-14 |
| Gate | Phase 4B stable |

Use Dhan Data API expired options endpoint to extend hist_option_bars_1m back to 2021. Provides 1-min OHLCV + IV + OI for NIFTY/SENSEX expired contracts. Constraint: ATM-relative strikes (ATM±10 for indices). Requires mapping ATM-relative → absolute strike using hist_spot_bars_1m spot prices. 30-day chunks. Current dataset is 1 year (Apr 2025–Mar 2026). 5-year extension adds COVID recovery, rate cycle, and multiple volatility regime data.

---

### ENH-52b: S3 Warm Tier Archiver (was HIST-02)

| Field | Detail |
|---|---|
| Status | **DEFERRED — Phase 5** |
| Added | 2026-04-15 (moved from OI register HIST-02) |

LocalParquetArchiver stubbed at C:\\GammaEnginePython\\data\\warm_tier\\. S3ParquetArchiver pending AWS credentials and bucket setup. Not blocking any current pipeline. DuckDB backtest harness on S3 Parquet also deferred. Build after Phase 4C stable.

---

### Infrastructure Changes (2026-04-14/15)

| Item | Detail |
|---|---|
| t3.micro → t3.small | AWS instance upgraded. 2GB RAM. Required for scrip master parsing (32MB CSV). |
| Elastic IP | 13.63.27.85 allocated + associated to i-0878c118835386ec2. Permanent. |
| Dhan IP whitelist | 13.63.27.85 added to Dhan Static IP Setting (IP Address 1). |
| AWS signal dashboard | merdian_signal_dashboard.py running on AWS port 8766. Bound to 0.0.0.0. IP-restricted to 103.39.127.162 + 103.30.127.162. |
| AWS @reboot crons | signal_dashboard + order_placer auto-start on reboot via crontab @reboot. |
| Task Scheduler fix | MERDIAN_Intraday_Supervisor_Start → merdian_morning_start.ps1 → merdian_start.py. Single control plane. StartWhenAvailable=false on Spot_1M + PreOpen. |
| Holiday gates | 4 scripts patched: build_market_spot_session_markers.py, capture_market_spot_snapshot_local.py, compute_iv_context_local.py, run_equity_eod_until_done.py. Calendar check before any API call. |
| merdian_start.py | ensure_calendar_row() read-before-write. Holidays never overwritten. |
| SPO-01 fix | compute_gamma_metrics_local.py derives DTE from expiry_date. gamma_metrics.dte column added. Flows to market_state_snapshots → signal_snapshots. |
| ict_zones fix | Dashboard order column detected_at → detected_at_ts. Eliminates 391 daily 400 errors. |
| Supabase disk | Auto-expanded to 50GB. 22.26GB used. Autoscaling enabled. |
| market_ticks retention | pg_cron job 45: DELETE WHERE ts < now() - interval '2 days'. Daily 20:00 IST weekdays. |
| HTF zone cron AWS | 30 3 * * 1-5 build_ict_htf_zones.py --timeframe D on MERDIAN AWS. |
| Telegram | TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env. Exit monitor alerts confirmed working. |

---

## Updated Summary Table

| ID | Title | Tier | Status |
|---|---|---|---|
| ENH-01 | ret_session momentum | 1 | **COMPLETE** |
| ENH-02 | Put/Call Ratio signal | 1 | **COMPLETE** |
| ENH-03 | Volume/OI ratio signal | 1 | **COMPLETE** |
| ENH-04 | Chain-wide IV skew signal | 1 | **COMPLETE** |
| ENH-05 | CONFLICT resolution logic | 1 | SUPERSEDED by SE-01 (ENH-35) |
| ENH-06 | Pre-trade cost filter | 1 | **COMPLETE** |
| ENH-07 | Basis-implied risk-free rate | 1 | **COMPLETE** |
| ENH-08 | Vega bucketing by expiry | 1 | DEFERRED |
| ENH-28 | Historical data ingest pipeline | 1 | **COMPLETE** |
| ENH-29 | Signal premium outcome measurement | 1 | PIVOTED |
| ENH-30 | SMDM infrastructure | 1 | PARTIAL — non-blocking shadow steps running |
| ENH-31 | Expiry calendar utility | 1 | **COMPLETE** — merdian_utils.py |
| ENH-32 | S3 warm tier archiver | 1 | STUBBED — see ENH-52b |
| ENH-33 | Pure-Python BS IV engine | 1 | **PRODUCTION** |
| ENH-34 | Live monitoring dashboard | 1 | **PRODUCTION** |
| ENH-35 | Historical signal validation | 1 | **COMPLETE** |
| ENH-36 | hist_* to live 1-min spot | 1 | **COMPLETE** |
| ENH-37 | ICT pattern detection layer | 1 | **COMPLETE** |
| ENH-38 | Live Kelly tiered sizing | 1 | **COMPLETE** |
| ENH-39 | Capital ceiling enforcement | 1 | **COMPLETE** |
| ENH-40 | Signal Rule Book v1.1 | 1 | **COMPLETE** |
| ENH-41 | BEAR_OB DTE gate — combined structure | 1 | DOCUMENTED — code pending execution layer |
| ENH-42 | Session pyramid | 2 | DEFERRED — post Phase 4B |
| ENH-43 | Signal dashboard | 1 | **COMPLETE** |
| ENH-44 | Capital management | 1 | **COMPLETE** |
| ENH-45 | hist_spot_bars_1m Zerodha backfill | 1 | **COMPLETE** |
| ENH-46 | Process Manager | 1 | **COMPLETE** |
| ENH-47 | MERDIAN_PreOpen task | 1 | **COMPLETE** |
| ENH-48 | Phase 4A execution layer | 1 | **COMPLETE** |
| ENH-49 | Phase 4B semi-auto order placement | 1 | **COMPLETE** |
| ENH-50 | Phase 4C full auto | 2 | PROPOSED |
| ENH-51a | ws_feed_zerodha.py on AWS | 1 | **COMPLETE** |
| ENH-51b | Pipeline reads market_ticks | 1 | PROPOSED — gate: live tick data confirmed |
| ENH-51c | AWS primary, local dashboards-only | 1 | PROPOSED — gate: ENH-51b + 10 sessions |
| ENH-51d | Local runner cutover | 1 | PROPOSED |
| ENH-51e | MeridianAlpha intraday WebSocket | 3 | DEFERRED — G-01 must fix first |
| ENH-51f | Unified portfolio management | 4 | DEFERRED — Phase 5 |
| ENH-52 | Dhan expired options 5-year backfill | 2 | PROPOSED |
| ENH-52b | S3 warm tier archiver | 3 | DEFERRED — Phase 5 |
| ENH-09 | Heston calibration layer | 2 | PROPOSED |
| ENH-10 to ENH-27 | Downstream of Heston | 2-4 | PROPOSED |

*MERDIAN Enhancement Register — v8 appended 2026-04-15*
*Base document: Enhancement Register v7 (2026-04-13 evening)*
"""

# ── merdian_reference.json update ────────────────────────────────────────────

def update_reference_json():
    if not REF_JSON.exists():
        print(f"ERROR: {REF_JSON} not found")
        return False

    shutil.copy2(REF_JSON, REF_JSON.with_suffix(".json.bak_v4"))

    with open(REF_JSON, encoding="utf-8") as f:
        ref = json.load(f)

    # Update meta
    ref["_meta"]["version"] = "v4"
    ref["_meta"]["generated"] = "2026-04-15"
    ref["_meta"]["sources"].extend([
        "MERDIAN_AppendixV18G.docx (2026-04-13/14)",
        "Session 2026-04-14/15 — Phase 4B + AWS migration + register closure"
    ])

    # Update git
    ref["git"]["current_hash"] = "c7daf7b"
    ref["git"]["local_status"] = "CLEAN"
    ref["git"]["aws_status"] = "CLEAN — in sync at c7daf7b"

    # Update shadow gate
    ref["shadow_gate"] = {
        "sessions_complete": 10,
        "sessions_required": 10,
        "status": "CLOSED — Phase 4 PROMOTED. Gate waived 2026-04-13 (full year backtest evidence sufficient). Session 9 passed live."
    }

    # Update task scheduler
    ref["task_scheduler"] = {
        "MERDIAN_Market_Tape_1M": "DISABLED — 2026-04-07",
        "MERDIAN_Intraday_Supervisor_Start": "ACTIVE — calls merdian_morning_start.ps1 → merdian_start.py. Mon-Fri 08:00.",
        "MERDIAN_Live_Dashboard": "ACTIVE — merdian_live_dashboard.py — AtLogon",
        "MERDIAN_Spot_1M": "ACTIVE — capture_spot_1m.py — 09:14-15:31 Mon-Fri — StartWhenAvailable=false — holiday gate added",
        "MERDIAN_PreOpen": "ACTIVE — capture_spot_1m.py — 09:05 Mon-Fri — StartWhenAvailable=false — holiday gate added",
        "MERDIAN_IV_Context_0905": "ACTIVE — compute_iv_context_local.py — 09:05 Mon-Fri — holiday gate added",
        "MERDIAN_Session_Markers_1602": "ACTIVE — build_market_spot_session_markers.py — 16:02 Mon-Fri — holiday gate added",
        "MERDIAN_Post_Market_1600_Capture": "ACTIVE — capture_market_spot_snapshot_local.py — 16:00 Mon-Fri — holiday gate added",
        "MERDIAN_EOD_Breadth_Refresh": "ACTIVE — run_equity_eod_until_done.py — 16:15 Mon-Fri — holiday gate added",
        "MERDIAN_Market_Close_Capture": "ACTIVE — 15:29 Mon-Fri"
    }

    # Update open items — all closed
    if "open_items" in ref:
        for k in ref["open_items"]:
            ref["open_items"][k]["status"] = "CLOSED"

    # Update SPO-01 and HIST-02 in open_items if they exist
    for key in list(ref.get("open_items", {}).keys()):
        ref["open_items"][key]["status"] = "CLOSED"

    # Add new entries
    if "open_items" not in ref:
        ref["open_items"] = {}
    ref["open_items"]["SPO-01"] = {
        "title": "DTE null in signal_snapshots",
        "status": "CLOSED — 2026-04-15. compute_gamma_metrics_local.py derives DTE from expiry_date. gamma_metrics.dte column added (ALTER TABLE). Flows to market_state_snapshots → signal_snapshots."
    }
    ref["open_items"]["OI-07-INFRA"] = {
        "title": "Supabase disk monitoring",
        "status": "CLOSED — auto-expanded to 50GB. 22.26GB used. Autoscaling enabled."
    }
    ref["open_items"]["HIST-02"] = {
        "title": "S3 warm tier archiver",
        "status": "DEFERRED → ENH-52b. Phase 5. Not blocking."
    }
    ref["open_items"]["register_status"] = "PERMANENTLY CLOSED — 2026-04-15. All items resolved."

    # Add AWS infrastructure
    ref["environments"]["aws"]["elastic_ip"] = "13.63.27.85"
    ref["environments"]["aws"]["instance_type"] = "t3.small"
    ref["environments"]["aws"]["role"] = "SHADOW + ORDER PLACER + DASHBOARD"
    ref["environments"]["aws"]["services"] = {
        "signal_dashboard": "port 8766 — 0.0.0.0 — IP restricted",
        "order_placer": "port 8767 — 0.0.0.0 — Dhan whitelisted",
        "ws_feed_zerodha": "cron 03:44 UTC — market_ticks",
        "shadow_runner": "cron 03:45 UTC — full pipeline"
    }

    # Add Dhan trading config
    ref["dhan_trading"] = {
        "order_api": "ACTIVE — v2/orders confirmed 200",
        "whitelisted_ip": "13.63.27.85 (AWS Elastic IP)",
        "trading_apis_active": ["Order Placement", "Position Management", "Statement Reports", "Order Postbacks", "CDSL Authorisation", "Portfolio and Funds"],
        "order_placer_url": "http://13.63.27.85:8767",
        "scrip_master_url": "https://images.dhan.co/api-data/api-scrip-master.csv",
        "scrip_master_segment": "D (not NSE_FNO/BSE_FNO)",
        "scrip_master_exchange": "NSE (NIFTY) / BSE (SENSEX)",
        "note": "Refresh scrip master daily — delete runtime/dhan_scrip_master.csv before market open"
    }

    # Update session log
    ref["session_log"].extend([
        {
            "date": "2026-04-13",
            "appendix": "MERDIAN_AppendixV18G.docx",
            "git_end": "a215049",
            "items_closed": ["OI-07", "OI-08", "OI-09", "OI-10", "C-07b", "ENH-46", "ENH-47", "ENH-48", "ENH-51a"],
            "summary": "Engineering session. Process manager. Live 1-min spot. Phase 4A execution layer. Signal engine upgrades ENH-01/02/04/06/07. Zerodha WebSocket on AWS (1007 instruments). Phase 4 promoted. Shadow gate waived."
        },
        {
            "date": "2026-04-14/15",
            "appendix": "Session — Phase 4B + AWS + Register Closure",
            "git_end": "c7daf7b",
            "items_closed": ["OI-11", "OI-12", "OI-13", "OI-14", "OI-15", "OI-16", "OI-17", "OI-07-INFRA", "SPO-01", "ENH-49"],
            "summary": "Holiday session. All OIs closed. Process control fixed (dual supervisor, holiday gates, StartWhenAvailable). Phase 4B order placer on AWS (Dhan API, Elastic IP, scrip master). Signal dashboard on AWS port 8766. t3.small upgrade. DTE fix (SPO-01). ict_zones column fix. Open Items Register permanently closed."
        }
    ])

    # Add rules
    ref["rules"]["oi_register_closed"] = "Open Items Register is PERMANENTLY CLOSED as of 2026-04-15. All items resolved. New operational issues tracked in Enhancement Register or session appendices."
    ref["rules"]["order_api_ip"] = "All Dhan order API calls must originate from AWS Elastic IP 13.63.27.85. Local machine IP is dynamic — never place orders from local."
    ref["rules"]["scrip_master_refresh"] = "Delete runtime/dhan_scrip_master.csv on AWS before each market session to get fresh instrument list with current weekly expiries."
    ref["rules"]["holiday_gate"] = "All Task Scheduler scripts check trading_calendar before executing. merdian_start.py reads before writing calendar row — never overwrites holidays."
    ref["rules"]["single_control_plane"] = "merdian_start.py is the ONLY morning startup command. Task Scheduler fires it at 08:00 via merdian_morning_start.ps1. Do not run gamma_engine_supervisor.py directly."

    with open(REF_JSON, "w", encoding="utf-8") as f:
        json.dump(ref, f, indent=2, ensure_ascii=False)

    print(f"OK: {REF_JSON} updated to v4")
    return True


def append_to_file(path: Path, content: str, label: str) -> bool:
    if not path.exists():
        print(f"ERROR: {path} not found")
        return False
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)
    print(f"OK: appended to {path.name} ({label})")
    return True


def main():
    print("=" * 60)
    print("MERDIAN Register Update — 2026-04-15")
    print("=" * 60)

    results = []

    # 1. Open Items Register
    results.append(append_to_file(OI_REG, OI_APPEND, "FINAL CLOSED block"))

    # 2. Enhancement Register
    results.append(append_to_file(ENH_REG, ENH_APPEND, "v8 changes + ENH-49/52/52b + infra"))

    # 3. Reference JSON
    results.append(update_reference_json())

    print()
    if all(results):
        print("All registers updated. Commit with:")
        print("  git add docs/registers/MERDIAN_OpenItems_Register_v7.md")
        print("  git add docs/registers/MERDIAN_Enhancement_Register_v7.md")
        print("  git add merdian_reference.json")
        print('  git commit -m "Registers v8: all OIs closed, ENH updated, reference v4"')
        print("  git push")
    else:
        print("Some updates failed — check errors above.")

    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
