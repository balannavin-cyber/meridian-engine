"""
merdian_live_dashboard.py

Live MERDIAN monitoring dashboard. Serves at http://localhost:8765
Auto-refreshes every 30 seconds. Action buttons trigger scheduled tasks.

Usage:
    python merdian_live_dashboard.py
    python merdian_live_dashboard.py --port 8765 --no-browser
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import requests as req

BASE_DIR = Path(__file__).resolve().parent
TELEMETRY_DIR = BASE_DIR / "runtime" / "telemetry"
HEARTBEAT_DIR = BASE_DIR / "runtime" / "heartbeats"
LATEST_JSON = TELEMETRY_DIR / "latest_health_snapshot.json"
ENV_PATH = BASE_DIR / ".env"
IST = timezone(timedelta(hours=5, minutes=30))

load_dotenv(dotenv_path=ENV_PATH)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

# ── Actions available via button clicks ───────────────────────────────────────
ACTIONS = {
    "start_supervisor": {
        "label": "Start Supervisor",
        "cmd": ["powershell", "-Command", "Start-ScheduledTask -TaskName MERDIAN_Intraday_Supervisor_Start"],
        "confirm": "Start the intraday supervisor and runner?"
    },
    "run_preflight": {
        "label": "Run Preflight",
        "cmd": ["python", str(BASE_DIR / "run_preflight.py"), "--mode", "full"],
        "confirm": "Run full preflight check?"
    },
    "refresh_token": {
        "label": "Refresh Token",
        "cmd": ["python", str(BASE_DIR / "refresh_dhan_token.py")],
        "confirm": "Refresh Dhan API token now?"
    },
    "run_health": {
        "label": "Run Health Check",
        "cmd": ["python", str(BASE_DIR / "gamma_engine_health_check.py")],
        "confirm": None
    },
    "start_tape": {
        "label": "Start Market Tape",
        "cmd": ["powershell", "-Command", "Start-ScheduledTask -TaskName MERDIAN_Market_Tape_1M"],
        "confirm": "Start 1-minute market tape runner?"
    },
}

# ── Data helpers ──────────────────────────────────────────────────────────────

def read_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def sb_get(table: str, params: str) -> List[Dict]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    try:
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        r = req.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=headers, timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def get_table_freshness() -> Dict[str, Dict]:
    tables = {
        "signal_snapshots": "created_at",
        "market_state_snapshots": "ts",
        "gamma_metrics": "ts",
        "volatility_snapshots": "ts",
        "weighted_constituent_breadth_snapshots": "ts",
    }
    now = datetime.now(timezone.utc)
    result = {}
    for table, col in tables.items():
        rows = sb_get(table, f"select={col}&order={col}.desc&limit=1")
        if rows and rows[0].get(col):
            ts_str = rows[0][col][:26].replace(" ", "T")
            if "+" not in ts_str[10:] and "Z" not in ts_str:
                ts_str += "+00:00"
            ts_str = ts_str.replace("Z", "+00:00")
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                lag = int((now - ts).total_seconds())
                ist_ts = ts.astimezone(IST).strftime("%H:%M:%S IST")
                result[table] = {"lag": lag, "ts": ist_ts, "stale": lag > 600}
            except Exception:
                result[table] = {"lag": None, "ts": "error", "stale": True}
        else:
            result[table] = {"lag": None, "ts": "no data", "stale": True}
    return result


def get_heartbeats() -> Dict[str, Dict]:
    components = [
        "gamma_engine_supervisor",
        "run_option_snapshot_intraday_runner",
        "gamma_engine_telemetry_logger",
        "gamma_engine_alert_daemon",
    ]
    now = datetime.now(timezone.utc)
    result = {}
    for comp in components:
        hb_file = HEARTBEAT_DIR / f"{comp}.json"
        data = read_json(hb_file)
        if data.get("last_heartbeat_utc"):
            try:
                ts = datetime.fromisoformat(data["last_heartbeat_utc"].replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age = int((now - ts).total_seconds())
                stale_after = data.get("stale_after_seconds", 180)
                result[comp] = {
                    "status": data.get("status", "UNKNOWN"),
                    "age": age,
                    "stale": age > stale_after,
                    "notes": data.get("notes", ""),
                }
            except Exception:
                result[comp] = {"status": "ERROR", "age": None, "stale": True, "notes": "parse error"}
        else:
            result[comp] = {"status": "MISSING", "age": None, "stale": True, "notes": "no heartbeat file"}
    return result


def get_current_signal() -> Dict:
    rows = sb_get("signal_snapshots", "select=symbol,action,confidence_score,trade_allowed,ts&order=ts.desc&limit=2")
    result = {}
    for row in rows:
        sym = row.get("symbol", "?")
        result[sym] = {
            "action": row.get("action", "?"),
            "confidence": row.get("confidence_score", "?"),
            "trade_allowed": row.get("trade_allowed", False),
            "ts": row.get("ts", "")[:19].replace("T", " "),
        }
    return result


def collect_data() -> Dict:
    snapshot = read_json(LATEST_JSON)
    heartbeats = get_heartbeats()
    freshness = get_table_freshness()
    signals = get_current_signal()
    now_ist = datetime.now(IST)

    return {
        "now": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "snapshot": snapshot,
        "heartbeats": heartbeats,
        "freshness": freshness,
        "signals": signals,
        "engine": snapshot.get("engine", "UNKNOWN"),
        "pipeline": snapshot.get("pipeline", "UNKNOWN"),
        "session": snapshot.get("session", "UNKNOWN"),
        "pipeline_details": snapshot.get("pipeline_details", {}),
        "quick_summary": snapshot.get("quick_summary", {}),
    }

# ── HTML generation ───────────────────────────────────────────────────────────

STATUS_COLORS = {
    "OK": ("#1a7a1a", "#e8f5e9"),
    "HEALTHY": ("#1a7a1a", "#e8f5e9"),
    "LIVE": ("#1a7a1a", "#e8f5e9"),
    "STALE": ("#b45000", "#fff3e0"),
    "WARN": ("#b45000", "#fff3e0"),
    "ATTENTION": ("#b45000", "#fff3e0"),
    "ERROR": ("#8b0000", "#ffebee"),
    "MISSING": ("#8b0000", "#ffebee"),
    "UNKNOWN": ("#555", "#f5f5f5"),
}

def status_style(status: str) -> str:
    color, bg = STATUS_COLORS.get(str(status).upper(), ("#555", "#f5f5f5"))
    return f"color:{color};background:{bg};padding:2px 8px;border-radius:4px;font-weight:500;font-size:13px"

def fmt_lag(lag_seconds) -> str:
    if lag_seconds is None:
        return "?"
    if lag_seconds < 60:
        return f"{lag_seconds}s"
    if lag_seconds < 3600:
        return f"{lag_seconds//60}m {lag_seconds%60}s"
    return f"{lag_seconds//3600}h {(lag_seconds%3600)//60}m"

def build_html(data: Dict) -> str:
    snap = data["snapshot"]
    hb = data["heartbeats"]
    fresh = data["freshness"]
    sigs = data["signals"]
    pipeline = data["pipeline_details"]
    quick = data["quick_summary"]
    engine_status = data["engine"]
    session = data["session"]

    engine_color = "#1a7a1a" if engine_status == "HEALTHY" else "#b45000" if engine_status == "ATTENTION" else "#8b0000"

    # Build pipeline rows
    def pipeline_row(symbol):
        stages = pipeline.get(symbol, [])
        cells = ""
        for stage in stages:
            st = stage.get("status", "?")
            age = stage.get("age_seconds", 0)
            ts = stage.get("ts", "")
            color, bg = STATUS_COLORS.get(st.upper(), ("#555", "#f5f5f5"))
            cells += f"""
            <td style="text-align:center;padding:6px 4px">
                <div style="{status_style(st)}">{st}</div>
                <div style="font-size:11px;color:#666;margin-top:2px">{ts}</div>
                <div style="font-size:11px;color:#888">{fmt_lag(age)}</div>
            </td>"""
        return cells

    # Build heartbeat rows
    hb_rows = ""
    hb_labels = {
        "gamma_engine_supervisor": "Supervisor",
        "run_option_snapshot_intraday_runner": "Runner",
        "gamma_engine_telemetry_logger": "Telemetry",
        "gamma_engine_alert_daemon": "Alert Daemon",
    }
    for comp, label in hb_labels.items():
        h = hb.get(comp, {})
        st = "OK" if not h.get("stale") else "STALE"
        age = h.get("age")
        hb_rows += f"""
        <tr style="border-bottom:1px solid #eee">
            <td style="padding:8px 12px;font-size:13px">{label}</td>
            <td style="padding:8px 12px;text-align:center"><span style="{status_style(st)}">{st}</span></td>
            <td style="padding:8px 12px;text-align:center;font-size:12px;color:#666">{fmt_lag(age)} ago</td>
            <td style="padding:8px 12px;font-size:12px;color:#888">{h.get("notes","")[:60]}</td>
        </tr>"""

    # Build freshness rows
    fresh_rows = ""
    fresh_labels = {
        "signal_snapshots": "Signals",
        "market_state_snapshots": "Market State",
        "gamma_metrics": "Gamma",
        "volatility_snapshots": "Volatility",
        "weighted_constituent_breadth_snapshots": "Breadth (WCB)",
    }
    for table, label in fresh_labels.items():
        f = fresh.get(table, {})
        stale = f.get("stale", True)
        st = "STALE" if stale else "OK"
        fresh_rows += f"""
        <tr style="border-bottom:1px solid #eee">
            <td style="padding:8px 12px;font-size:13px">{label}</td>
            <td style="padding:8px 12px;text-align:center"><span style="{status_style(st)}">{st}</span></td>
            <td style="padding:8px 12px;text-align:center;font-size:12px;color:#666">{f.get("ts","?")}</td>
            <td style="padding:8px 12px;text-align:center;font-size:12px;color:#666">{fmt_lag(f.get("lag"))}</td>
        </tr>"""

    # Build signal rows
    sig_rows = ""
    for sym in ["NIFTY", "SENSEX"]:
        s = sigs.get(sym, {})
        action = s.get("action", "—")
        conf = s.get("confidence", "—")
        allowed = s.get("trade_allowed", False)
        ts = s.get("ts", "—")
        action_color = "#1a7a1a" if action == "BUY_CE" else "#8b0000" if action == "BUY_PE" else "#555"
        sig_rows += f"""
        <tr style="border-bottom:1px solid #eee">
            <td style="padding:8px 12px;font-weight:500">{sym}</td>
            <td style="padding:8px 12px;text-align:center;color:{action_color};font-weight:500">{action}</td>
            <td style="padding:8px 12px;text-align:center">{conf}</td>
            <td style="padding:8px 12px;text-align:center">{"✓ YES" if allowed else "✗ NO"}</td>
            <td style="padding:8px 12px;font-size:12px;color:#666">{ts}</td>
        </tr>"""

    # Action buttons
    btn_html = ""
    for action_id, action_info in ACTIONS.items():
        confirm_msg = (action_info.get("confirm") or "").replace("'", "")
        confirm_attr = ""
        if action_info.get("confirm"):
            msg = action_info["confirm"].replace("'", "")
            confirm_attr = f'onclick="return confirm(\"{msg}\")"'
        btn_html += f"""
        <form method="POST" action="/action/{action_id}" style="display:inline">
            <button type="submit" {confirm_attr}
                style="margin:4px;padding:8px 16px;border:1px solid #ccc;border-radius:6px;
                       background:#fff;cursor:pointer;font-size:13px;font-weight:500">
                {action_info["label"]}
            </button>
        </form>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="30">
<title>MERDIAN Live Dashboard</title>
<style>
  body {{font-family:Arial,sans-serif;margin:0;padding:0;background:#f8f8f8;color:#222}}
  .header {{background:#1a1a2e;color:#fff;padding:14px 24px;display:flex;justify-content:space-between;align-items:center}}
  .header h1 {{margin:0;font-size:20px;letter-spacing:1px}}
  .header .meta {{font-size:13px;color:#aaa;text-align:right}}
  .section {{background:#fff;margin:12px 16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.08);overflow:hidden}}
  .section-title {{background:#f0f0f0;padding:8px 16px;font-size:13px;font-weight:600;color:#444;border-bottom:1px solid #e0e0e0;text-transform:uppercase;letter-spacing:0.5px}}
  table {{width:100%;border-collapse:collapse}}
  th {{background:#fafafa;padding:8px 12px;text-align:left;font-size:12px;color:#666;border-bottom:1px solid #eee;font-weight:600}}
  .status-bar {{padding:12px 24px;display:flex;gap:24px;align-items:center;flex-wrap:wrap}}
  .status-pill {{padding:6px 16px;border-radius:20px;font-size:13px;font-weight:600}}
  .actions {{padding:12px 16px}}
  .refresh-note {{font-size:11px;color:#aaa;text-align:right;padding:4px 16px 8px}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>MERDIAN Live Dashboard</h1>
    <div style="font-size:12px;color:#aaa;margin-top:2px">Market Structure Intelligence Engine</div>
  </div>
  <div class="meta">
    <div style="font-size:16px;color:#fff">{data["now"]}</div>
    <div>Session: <strong style="color:#ffd700">{session}</strong></div>
    <div>Auto-refresh every 30s</div>
  </div>
</div>

<div class="status-bar" style="background:#fff;border-bottom:1px solid #eee;margin:0">
  <div>Engine: <span class="status-pill" style="background:#e8f5e9;color:{engine_color}">{engine_status}</span></div>
  <div>Pipeline: <span style="{status_style(data["pipeline"])}">{data["pipeline"]}</span></div>
  <div style="margin-left:auto;font-size:12px;color:#888">Snapshot: {snap.get("captured_at_utc","?")[:19]} UTC</div>
</div>

<div class="section">
  <div class="section-title">Pipeline Stages</div>
  <table>
    <tr>
      <th style="width:80px">Symbol</th>
      <th style="text-align:center">Options</th>
      <th style="text-align:center">Gamma</th>
      <th style="text-align:center">Volatility</th>
      <th style="text-align:center">Momentum</th>
      <th style="text-align:center">Market State</th>
      <th style="text-align:center">Signal</th>
    </tr>
    <tr style="border-bottom:1px solid #eee">
      <td style="padding:6px 12px;font-weight:500">NIFTY</td>
      {pipeline_row("NIFTY")}
    </tr>
    <tr>
      <td style="padding:6px 12px;font-weight:500">SENSEX</td>
      {pipeline_row("SENSEX")}
    </tr>
  </table>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:0 12px;margin:0 16px">

  <div class="section" style="margin:12px 0">
    <div class="section-title">Latest Signals</div>
    <table>
      <tr><th>Symbol</th><th>Action</th><th>Confidence</th><th>Trade Allowed</th><th>Time</th></tr>
      {sig_rows if sig_rows else '<tr><td colspan="5" style="padding:12px;color:#888;text-align:center">No signal data</td></tr>'}
    </table>
  </div>

  <div class="section" style="margin:12px 0">
    <div class="section-title">Component Heartbeats</div>
    <table>
      <tr><th>Component</th><th>Status</th><th>Last Beat</th><th>Notes</th></tr>
      {hb_rows}
    </table>
  </div>

</div>

<div class="section">
  <div class="section-title">Table Freshness (Supabase)</div>
  <table>
    <tr><th>Table</th><th>Status</th><th>Last Row (IST)</th><th>Lag</th></tr>
    {fresh_rows}
  </table>
</div>

<div class="section">
  <div class="section-title">Actions</div>
  <div class="actions">{btn_html}</div>
  <div style="padding:0 16px 10px;font-size:11px;color:#aaa">
    Actions run in background. Check logs or refresh dashboard to see results.
  </div>
</div>

<div class="refresh-note">Dashboard auto-refreshes every 30 seconds · MERDIAN v18C</div>

</body>
</html>"""

# ── HTTP server ───────────────────────────────────────────────────────────────

class DashboardHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # suppress access logs

    def do_GET(self):
        try:
            data = collect_data()
            html_content = build_html(data)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())

    def do_POST(self):
        path = self.path
        if not path.startswith("/action/"):
            self.send_response(404)
            self.end_headers()
            return

        action_id = path[len("/action/"):]
        action = ACTIONS.get(action_id)

        if not action:
            self.send_response(404)
            self.end_headers()
            return

        # Run action in background thread
        def run():
            try:
                subprocess.Popen(
                    action["cmd"],
                    cwd=str(BASE_DIR),
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
            except Exception as e:
                print(f"Action error: {e}")

        threading.Thread(target=run, daemon=True).start()

        # Redirect back to dashboard
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = HTTPServer(("localhost", args.port), DashboardHandler)
    url = f"http://localhost:{args.port}"
    print(f"MERDIAN Live Dashboard running at {url}")
    print("Press Ctrl+C to stop.")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
