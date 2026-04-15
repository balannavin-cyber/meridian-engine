#!/usr/bin/env python3
"""Fix: update only merdian_reference.json with correct path."""
import json
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
REF_JSON = BASE / "docs/registers/merdian_reference.json"

if not REF_JSON.exists():
    print(f"ERROR: {REF_JSON} not found")
    raise SystemExit(1)

shutil.copy2(REF_JSON, REF_JSON.with_suffix(".json.bak_v4"))

with open(REF_JSON, encoding="utf-8") as f:
    ref = json.load(f)

ref["_meta"]["version"] = "v4"
ref["_meta"]["generated"] = "2026-04-15"
ref["_meta"]["sources"].extend([
    "MERDIAN_AppendixV18G.docx (2026-04-13/14)",
    "Session 2026-04-14/15 — Phase 4B + AWS migration + register closure"
])

ref["git"]["current_hash"] = "c7daf7b"
ref["git"]["local_status"] = "CLEAN"
ref["git"]["aws_status"] = "CLEAN — in sync at c7daf7b"

ref["shadow_gate"] = {
    "sessions_complete": 10,
    "sessions_required": 10,
    "status": "CLOSED — Phase 4 PROMOTED. Gate waived 2026-04-13."
}

ref["task_scheduler"] = {
    "MERDIAN_Market_Tape_1M": "DISABLED — 2026-04-07",
    "MERDIAN_Intraday_Supervisor_Start": "ACTIVE — merdian_morning_start.ps1 -> merdian_start.py. Mon-Fri 08:00.",
    "MERDIAN_Live_Dashboard": "ACTIVE — merdian_live_dashboard.py — AtLogon",
    "MERDIAN_Spot_1M": "ACTIVE — capture_spot_1m.py — 09:14-15:31 Mon-Fri — StartWhenAvailable=false — holiday gate",
    "MERDIAN_PreOpen": "ACTIVE — capture_spot_1m.py — 09:05 Mon-Fri — StartWhenAvailable=false — holiday gate",
    "MERDIAN_IV_Context_0905": "ACTIVE — compute_iv_context_local.py — 09:05 Mon-Fri — holiday gate",
    "MERDIAN_Session_Markers_1602": "ACTIVE — build_market_spot_session_markers.py — 16:02 Mon-Fri — holiday gate",
    "MERDIAN_Post_Market_1600_Capture": "ACTIVE — capture_market_spot_snapshot_local.py — 16:00 Mon-Fri — holiday gate",
    "MERDIAN_EOD_Breadth_Refresh": "ACTIVE — run_equity_eod_until_done.py — 16:15 Mon-Fri — holiday gate",
    "MERDIAN_Market_Close_Capture": "ACTIVE — 15:29 Mon-Fri"
}

if "open_items" in ref:
    for k in ref["open_items"]:
        ref["open_items"][k]["status"] = "CLOSED"
else:
    ref["open_items"] = {}

ref["open_items"]["SPO-01"] = {
    "title": "DTE null in signal_snapshots",
    "status": "CLOSED 2026-04-15. compute_gamma_metrics_local.py derives DTE from expiry_date. gamma_metrics.dte column added."
}
ref["open_items"]["OI-07-INFRA"] = {
    "title": "Supabase disk monitoring",
    "status": "CLOSED — auto-expanded to 50GB. 22.26GB used. Autoscaling enabled."
}
ref["open_items"]["HIST-02"] = {
    "title": "S3 warm tier archiver",
    "status": "DEFERRED -> ENH-52b. Phase 5."
}
ref["open_items"]["register_status"] = "PERMANENTLY CLOSED 2026-04-15. All items resolved."

ref["environments"]["aws"]["elastic_ip"] = "13.63.27.85"
ref["environments"]["aws"]["instance_type"] = "t3.small"
ref["environments"]["aws"]["role"] = "SHADOW + ORDER PLACER + DASHBOARD"
ref["environments"]["aws"]["services"] = {
    "signal_dashboard": "port 8766 — IP restricted to 103.39.127.162 + 103.30.127.162",
    "order_placer": "port 8767 — Dhan whitelisted 13.63.27.85",
    "ws_feed_zerodha": "cron 03:44 UTC — market_ticks",
    "shadow_runner": "cron 03:45 UTC"
}

ref["dhan_trading"] = {
    "order_api": "ACTIVE — v2/orders confirmed 200",
    "whitelisted_ip": "13.63.27.85",
    "order_placer_url": "http://13.63.27.85:8767",
    "scrip_master_segment": "D (not NSE_FNO/BSE_FNO)",
    "scrip_master_exchange": "NSE (NIFTY) / BSE (SENSEX)",
    "note": "Delete runtime/dhan_scrip_master.csv on AWS before each session for fresh weekly expiries"
}

ref["session_log"].extend([
    {
        "date": "2026-04-13",
        "appendix": "MERDIAN_AppendixV18G.docx",
        "git_end": "a215049",
        "items_closed": ["OI-07", "OI-08", "OI-09", "OI-10", "C-07b", "ENH-46", "ENH-47", "ENH-48", "ENH-51a"],
        "summary": "Process manager. Live 1-min spot. Phase 4A. Signal engine upgrades. Zerodha WebSocket AWS. Phase 4 promoted."
    },
    {
        "date": "2026-04-14/15",
        "appendix": "Session — Phase 4B + AWS + Register Closure",
        "git_end": "c7daf7b",
        "items_closed": ["OI-11", "OI-12", "OI-13", "OI-14", "OI-15", "OI-16", "OI-17", "OI-07-INFRA", "SPO-01", "ENH-49"],
        "summary": "All OIs closed. Process control fixed. Phase 4B order placer on AWS. Dashboard on AWS. t3.small. DTE fix. OI register permanently closed."
    }
])

if "rules" not in ref:
    ref["rules"] = {}
ref["rules"]["oi_register_closed"] = "Open Items Register PERMANENTLY CLOSED 2026-04-15."
ref["rules"]["order_api_ip"] = "All Dhan orders from AWS Elastic IP 13.63.27.85 only."
ref["rules"]["scrip_master_refresh"] = "Delete runtime/dhan_scrip_master.csv on AWS before each market session."
ref["rules"]["holiday_gate"] = "All Task Scheduler scripts check trading_calendar. merdian_start.py reads before writing."
ref["rules"]["single_control_plane"] = "merdian_start.py is the ONLY morning startup. Task Scheduler fires via merdian_morning_start.ps1."

with open(REF_JSON, "w", encoding="utf-8") as f:
    json.dump(ref, f, indent=2, ensure_ascii=False)

print(f"OK: {REF_JSON} updated to v4")
