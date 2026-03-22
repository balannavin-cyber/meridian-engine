from __future__ import annotations

import argparse
import html
import json
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent
TELEMETRY_DIR = BASE_DIR / "runtime" / "telemetry"
HEARTBEAT_DIR = BASE_DIR / "runtime" / "heartbeats"

LATEST_JSON = TELEMETRY_DIR / "latest_health_snapshot.json"
EVENT_LOG_JSONL = TELEMETRY_DIR / "health_events.jsonl"
SNAPSHOT_JSONL = TELEMETRY_DIR / "health_snapshots.jsonl"

ALERT_STATE_JSON = TELEMETRY_DIR / "alert_state.json"
LATEST_ALERTS_JSON = TELEMETRY_DIR / "latest_alerts.json"
ALERTS_JSONL = TELEMETRY_DIR / "alerts.jsonl"

DASHBOARD_HTML = TELEMETRY_DIR / "gamma_engine_monitor_dashboard.html"

DEFAULT_REFRESH_SECONDS = 30
DEFAULT_EVENT_LIMIT = 20
DEFAULT_SNAPSHOT_LIMIT = 50
DEFAULT_ALERT_HISTORY_LIMIT = 30

HEARTBEAT_COMPONENTS = [
    "gamma_engine_supervisor",
    "run_option_snapshot_intraday_runner",
    "gamma_engine_telemetry_logger",
    "gamma_engine_alert_daemon",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_jsonl_tail(path: Path, limit: int) -> List[Dict[str, Any]]:
    if not path.exists() or limit <= 0:
        return []

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    items: List[Dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def heartbeat_file_path(component_name: str) -> Path:
    return HEARTBEAT_DIR / f"{component_name}.json"


def heartbeat_age_seconds(payload: Dict[str, Any]) -> Optional[int]:
    dt = parse_iso_datetime(payload.get("last_heartbeat_utc"))
    if dt is None:
        return None
    age = (datetime.now(timezone.utc) - dt).total_seconds()
    if age < 0:
        age = 0
    return int(age)


def heartbeat_display_status(payload: Dict[str, Any]) -> str:
    if not payload:
        return "MISSING"

    age = heartbeat_age_seconds(payload)
    stale_after = payload.get("stale_after_seconds")

    try:
        stale_after_int = int(stale_after) if stale_after is not None else None
    except Exception:
        stale_after_int = None

    base_status = str(payload.get("status") or "UNKNOWN").upper()

    if age is not None and stale_after_int is not None and age > stale_after_int:
        return "STALE"

    if base_status in {"ERROR", "FAILED"}:
        return "ERROR"

    if base_status in {"WARN", "WARNING"}:
        return "WARN"

    if base_status in {"OK", "INFO"}:
        return "OK"

    return base_status if base_status else "UNKNOWN"


def load_heartbeat_payloads() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for component_name in HEARTBEAT_COMPONENTS:
        path = heartbeat_file_path(component_name)
        payload = read_json(path)

        age_seconds = heartbeat_age_seconds(payload) if payload else None
        display_status = heartbeat_display_status(payload)

        rows.append(
            {
                "component_name": component_name,
                "path": str(path),
                "exists": bool(payload),
                "display_status": display_status,
                "last_heartbeat_utc": payload.get("last_heartbeat_utc") if payload else None,
                "age_seconds": age_seconds,
                "pid": payload.get("pid") if payload else None,
                "session": payload.get("session") if payload else None,
                "status": payload.get("status") if payload else None,
                "stale_after_seconds": payload.get("stale_after_seconds") if payload else None,
                "last_successful_cycle_utc": payload.get("last_successful_cycle_utc") if payload else None,
                "notes": payload.get("notes") if payload else "Heartbeat file missing",
                "extra": payload.get("extra", {}) if payload else {},
            }
        )

    return rows


def status_class(value: Any) -> str:
    text = str(value or "").upper()

    if any(token in text for token in ["ERROR", "FAILED", "DOWN", "BROKEN", "MISSING"]):
        return "status-error"
    if any(token in text for token in ["WARN", "STALE", "DRIFT", "ATTENTION"]):
        return "status-warn"
    if any(token in text for token in ["OK", "HEALTHY", "INFO", "CLOSED_OK", "STANDBY", "OPEN"]):
        return "status-ok"
    return "status-neutral"


def render_badge(label: str, value: Any) -> str:
    cls = status_class(value)
    return (
        f'<div class="badge-card">'
        f'<div class="badge-label">{esc(label)}</div>'
        f'<div class="badge-value {cls}">{esc(value)}</div>'
        f'</div>'
    )


def render_key_value_table(data: Dict[str, Any], title: str) -> str:
    rows = []
    for key, value in data.items():
        rows.append(
            "<tr>"
            f"<td>{esc(key)}</td>"
            f"<td>{esc(value)}</td>"
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="2">No data</td></tr>')

    return (
        f'<section class="panel">'
        f'<h2>{esc(title)}</h2>'
        '<table class="kv-table">'
        '<thead><tr><th>Field</th><th>Value</th></tr></thead>'
        '<tbody>'
        + "".join(rows) +
        '</tbody></table></section>'
    )


def render_pipeline_table(symbol: str, rows_data: List[Dict[str, Any]]) -> str:
    rows = []
    for row in rows_data:
        status = row.get("status", "")
        rows.append(
            "<tr>"
            f"<td>{esc(row.get('stage'))}</td>"
            f"<td class='{status_class(status)}'>{esc(status)}</td>"
            f"<td>{esc(row.get('ts'))}</td>"
            f"<td>{esc(row.get('age_seconds'))}</td>"
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="4">No pipeline data</td></tr>')

    return (
        f'<section class="panel">'
        f'<h2>{esc(symbol)} Pipeline</h2>'
        '<table class="pipeline-table">'
        '<thead><tr><th>Stage</th><th>Status</th><th>Timestamp</th><th>Age (s)</th></tr></thead>'
        '<tbody>'
        + "".join(rows) +
        '</tbody></table></section>'
    )


def render_events_table(events: List[Dict[str, Any]]) -> str:
    rows = []
    for event in reversed(events):
        level = event.get("event_level", "")
        rows.append(
            "<tr>"
            f"<td>{esc(event.get('captured_at_utc'))}</td>"
            f"<td class='{status_class(level)}'>{esc(level)}</td>"
            f"<td>{esc(event.get('engine'))}</td>"
            f"<td>{esc(event.get('pipeline'))}</td>"
            f"<td>{esc(event.get('symbol_sync'))}</td>"
            f"<td>{esc(event.get('session'))}</td>"
            f"<td>{esc(event.get('summary_line'))}</td>"
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="7">No warning/error events recorded</td></tr>')

    return (
        '<section class="panel">'
        '<h2>Recent Health Events</h2>'
        '<table class="events-table">'
        '<thead><tr>'
        '<th>Captured UTC</th>'
        '<th>Level</th>'
        '<th>Engine</th>'
        '<th>Pipeline</th>'
        '<th>Symbol Sync</th>'
        '<th>Session</th>'
        '<th>Summary</th>'
        '</tr></thead>'
        '<tbody>'
        + "".join(rows) +
        '</tbody></table></section>'
    )


def render_recent_snapshots_table(snapshots: List[Dict[str, Any]]) -> str:
    rows = []
    for snap in reversed(snapshots):
        rows.append(
            "<tr>"
            f"<td>{esc(snap.get('captured_at_utc'))}</td>"
            f"<td class='{status_class(snap.get('engine'))}'>{esc(snap.get('engine'))}</td>"
            f"<td class='{status_class(snap.get('pipeline'))}'>{esc(snap.get('pipeline'))}</td>"
            f"<td class='{status_class(snap.get('symbol_sync'))}'>{esc(snap.get('symbol_sync'))}</td>"
            f"<td>{esc(snap.get('session'))}</td>"
            f"<td>{esc(snap.get('health_check_duration_seconds'))}</td>"
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="6">No snapshots found</td></tr>')

    return (
        '<section class="panel">'
        '<h2>Recent Snapshots</h2>'
        '<table class="events-table">'
        '<thead><tr>'
        '<th>Captured UTC</th>'
        '<th>Engine</th>'
        '<th>Pipeline</th>'
        '<th>Symbol Sync</th>'
        '<th>Session</th>'
        '<th>Duration (s)</th>'
        '</tr></thead>'
        '<tbody>'
        + "".join(rows) +
        '</tbody></table></section>'
    )


def render_active_alerts_table(active_alerts: List[Dict[str, Any]]) -> str:
    rows = []
    for alert in active_alerts:
        level = alert.get("alert_level", "")
        rows.append(
            "<tr>"
            f"<td>{esc(alert.get('detected_at_utc'))}</td>"
            f"<td class='{status_class(level)}'>{esc(level)}</td>"
            f"<td>{esc(alert.get('alert_code'))}</td>"
            f"<td>{esc(alert.get('summary'))}</td>"
            f"<td>{esc(alert.get('engine'))}</td>"
            f"<td>{esc(alert.get('pipeline'))}</td>"
            f"<td>{esc(alert.get('symbol_sync'))}</td>"
            f"<td>{esc(alert.get('session'))}</td>"
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="8">No active alerts</td></tr>')

    return (
        '<section class="panel">'
        '<h2>Active Alerts</h2>'
        '<table class="events-table">'
        '<thead><tr>'
        '<th>Detected UTC</th>'
        '<th>Level</th>'
        '<th>Code</th>'
        '<th>Summary</th>'
        '<th>Engine</th>'
        '<th>Pipeline</th>'
        '<th>Symbol Sync</th>'
        '<th>Session</th>'
        '</tr></thead>'
        '<tbody>'
        + "".join(rows) +
        '</tbody></table></section>'
    )


def render_alert_history_table(alert_history: List[Dict[str, Any]]) -> str:
    rows = []
    for alert in reversed(alert_history):
        level = alert.get("alert_level", "")
        rows.append(
            "<tr>"
            f"<td>{esc(alert.get('detected_at_utc'))}</td>"
            f"<td class='{status_class(level)}'>{esc(level)}</td>"
            f"<td>{esc(alert.get('alert_code'))}</td>"
            f"<td>{esc(alert.get('summary'))}</td>"
            f"<td>{esc(alert.get('source'))}</td>"
            f"<td>{esc(alert.get('summary_line'))}</td>"
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="6">No historical alerts logged</td></tr>')

    return (
        '<section class="panel">'
        '<h2>Alert History</h2>'
        '<table class="events-table">'
        '<thead><tr>'
        '<th>Detected UTC</th>'
        '<th>Level</th>'
        '<th>Code</th>'
        '<th>Summary</th>'
        '<th>Source</th>'
        '<th>Summary Line</th>'
        '</tr></thead>'
        '<tbody>'
        + "".join(rows) +
        '</tbody></table></section>'
    )


def render_heartbeat_table(heartbeats: List[Dict[str, Any]]) -> str:
    rows = []
    for hb in heartbeats:
        display_status = hb.get("display_status", "UNKNOWN")
        rows.append(
            "<tr>"
            f"<td>{esc(hb.get('component_name'))}</td>"
            f"<td class='{status_class(display_status)}'>{esc(display_status)}</td>"
            f"<td>{esc(hb.get('status'))}</td>"
            f"<td>{esc(hb.get('session'))}</td>"
            f"<td>{esc(hb.get('last_heartbeat_utc'))}</td>"
            f"<td>{esc(hb.get('age_seconds'))}</td>"
            f"<td>{esc(hb.get('stale_after_seconds'))}</td>"
            f"<td>{esc(hb.get('pid'))}</td>"
            f"<td>{esc(hb.get('last_successful_cycle_utc'))}</td>"
            f"<td>{esc(hb.get('notes'))}</td>"
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="10">No heartbeat data found</td></tr>')

    return (
        '<section class="panel">'
        '<h2>Component Liveness</h2>'
        '<table class="events-table">'
        '<thead><tr>'
        '<th>Component</th>'
        '<th>Display Status</th>'
        '<th>Base Status</th>'
        '<th>Session</th>'
        '<th>Last Heartbeat UTC</th>'
        '<th>Age (s)</th>'
        '<th>Stale After (s)</th>'
        '<th>PID</th>'
        '<th>Last Success UTC</th>'
        '<th>Notes</th>'
        '</tr></thead>'
        '<tbody>'
        + "".join(rows) +
        '</tbody></table></section>'
    )


def heartbeat_summary_counts(heartbeats: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {
        "ok": 0,
        "warn": 0,
        "error": 0,
        "missing": 0,
    }

    for hb in heartbeats:
        status = str(hb.get("display_status") or "").upper()
        if status == "OK":
            counts["ok"] += 1
        elif status in {"WARN", "STALE"}:
            counts["warn"] += 1
        elif status in {"ERROR", "FAILED"}:
            counts["error"] += 1
        elif status == "MISSING":
            counts["missing"] += 1
        else:
            counts["warn"] += 1

    return counts


def build_dashboard_html(
    latest: Dict[str, Any],
    events: List[Dict[str, Any]],
    snapshots: List[Dict[str, Any]],
    alert_state: Dict[str, Any],
    latest_alerts: Dict[str, Any],
    alert_history: List[Dict[str, Any]],
    heartbeats: List[Dict[str, Any]],
    refresh_seconds: int,
) -> str:
    parsed_fields = latest.get("parsed_fields", {}) or {}
    quick_summary = latest.get("quick_summary", {}) or {}
    pipeline_details = latest.get("pipeline_details", {}) or {}

    nifty_quick = quick_summary.get("NIFTY", {})
    sensex_quick = quick_summary.get("SENSEX", {})

    active_alerts = latest_alerts.get("active_alerts", []) or []
    active_alert_count = alert_state.get("active_alert_count", 0)
    updated_alerts_at = alert_state.get("updated_at_utc")

    hb_counts = heartbeat_summary_counts(heartbeats)
    generated_at = utc_now_iso()

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="{refresh_seconds}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gamma Engine Monitor Dashboard</title>
<style>
    body {{
        font-family: Arial, Helvetica, sans-serif;
        margin: 0;
        padding: 0;
        background: #0f172a;
        color: #e5e7eb;
    }}
    .container {{
        max-width: 1700px;
        margin: 0 auto;
        padding: 24px;
    }}
    h1 {{
        margin: 0 0 8px 0;
        font-size: 32px;
    }}
    h2 {{
        margin-top: 0;
        font-size: 22px;
    }}
    .subtle {{
        color: #94a3b8;
        margin-bottom: 20px;
    }}
    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 20px;
    }}
    .grid-2 {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
        gap: 20px;
        margin-bottom: 20px;
    }}
    .panel {{
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 20px;
        overflow-x: auto;
        box-shadow: 0 8px 24px rgba(0,0,0,0.20);
    }}
    .badge-card {{
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.20);
    }}
    .badge-label {{
        font-size: 13px;
        text-transform: uppercase;
        color: #94a3b8;
        margin-bottom: 10px;
        letter-spacing: 0.5px;
    }}
    .badge-value {{
        font-size: 26px;
        font-weight: 700;
    }}
    .status-ok {{
        color: #22c55e;
        font-weight: 700;
    }}
    .status-warn {{
        color: #f59e0b;
        font-weight: 700;
    }}
    .status-error {{
        color: #ef4444;
        font-weight: 700;
    }}
    .status-neutral {{
        color: #e5e7eb;
        font-weight: 700;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
    }}
    th, td {{
        text-align: left;
        border-bottom: 1px solid #243041;
        padding: 10px 8px;
        font-size: 14px;
        vertical-align: top;
    }}
    th {{
        color: #93c5fd;
    }}
    .mono {{
        font-family: Consolas, "Courier New", monospace;
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 13px;
        background: #020617;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 14px;
    }}
</style>
</head>
<body>
<div class="container">
    <h1>Gamma Engine Monitor Dashboard</h1>
    <div class="subtle">
        Generated at UTC: {esc(generated_at)} |
        Auto-refresh: every {refresh_seconds} seconds |
        Source file: {esc(LATEST_JSON)}
    </div>

    <div class="grid">
        {render_badge("Engine", latest.get("engine"))}
        {render_badge("Pipeline", latest.get("pipeline"))}
        {render_badge("Symbol Sync", latest.get("symbol_sync"))}
        {render_badge("Session", latest.get("session"))}
        {render_badge("Event Level", latest.get("event_level"))}
        {render_badge("Return Code", latest.get("health_check_returncode"))}
    </div>

    <div class="grid">
        {render_badge("Overall Status", parsed_fields.get("overall_status"))}
        {render_badge("Session Mode", parsed_fields.get("session_mode"))}
        {render_badge("Premarket Start", parsed_fields.get("premarket_start"))}
        {render_badge("Market Open", parsed_fields.get("market_open"))}
        {render_badge("Market Close", parsed_fields.get("market_close"))}
        {render_badge("Now", parsed_fields.get("now"))}
    </div>

    <div class="grid">
        {render_badge("Active Alerts", active_alert_count)}
        {render_badge("Alert State Updated", updated_alerts_at)}
        {render_badge("Latest Engine", alert_state.get("latest_engine"))}
        {render_badge("Latest Pipeline", alert_state.get("latest_pipeline"))}
        {render_badge("Latest Symbol Sync", alert_state.get("latest_symbol_sync"))}
        {render_badge("Latest Session", alert_state.get("latest_session"))}
    </div>

    <div class="grid">
        {render_badge("Heartbeat OK", hb_counts.get("ok"))}
        {render_badge("Heartbeat Warn/Stale", hb_counts.get("warn"))}
        {render_badge("Heartbeat Error", hb_counts.get("error"))}
        {render_badge("Heartbeat Missing", hb_counts.get("missing"))}
    </div>

    {render_heartbeat_table(heartbeats)}

    <div class="grid-2">
        {render_key_value_table(parsed_fields, "Parsed Fields")}
        {render_key_value_table(nifty_quick, "NIFTY Quick Summary")}
    </div>

    <div class="grid-2">
        {render_key_value_table(sensex_quick, "SENSEX Quick Summary")}
        <section class="panel">
            <h2>Summary Line</h2>
            <div class="mono">{esc(latest.get("summary_line"))}</div>
        </section>
    </div>

    <div class="grid-2">
        {render_pipeline_table("NIFTY", pipeline_details.get("NIFTY", []))}
        {render_pipeline_table("SENSEX", pipeline_details.get("SENSEX", []))}
    </div>

    {render_active_alerts_table(active_alerts)}
    {render_alert_history_table(alert_history)}
    {render_recent_snapshots_table(snapshots)}
    {render_events_table(events)}

    <section class="panel">
        <h2>Latest Raw Health Check Output</h2>
        <div class="mono">{esc(latest.get("stdout", ""))}</div>
    </section>
</div>
</body>
</html>
"""
    return html_doc


def generate_dashboard(
    refresh_seconds: int,
    event_limit: int,
    snapshot_limit: int,
    alert_history_limit: int,
) -> Path:
    latest = read_json(LATEST_JSON)
    events = read_jsonl_tail(EVENT_LOG_JSONL, event_limit)
    snapshots = read_jsonl_tail(SNAPSHOT_JSONL, snapshot_limit)
    alert_state = read_json(ALERT_STATE_JSON)
    latest_alerts = read_json(LATEST_ALERTS_JSON)
    alert_history = read_jsonl_tail(ALERTS_JSONL, alert_history_limit)
    heartbeats = load_heartbeat_payloads()

    html_doc = build_dashboard_html(
        latest=latest,
        events=events,
        snapshots=snapshots,
        alert_state=alert_state,
        latest_alerts=latest_alerts,
        alert_history=alert_history,
        heartbeats=heartbeats,
        refresh_seconds=refresh_seconds,
    )

    DASHBOARD_HTML.write_text(html_doc, encoding="utf-8")
    return DASHBOARD_HTML


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Gamma Engine local monitoring dashboard.")
    parser.add_argument(
        "--refresh-seconds",
        type=int,
        default=DEFAULT_REFRESH_SECONDS,
        help=f"HTML auto-refresh interval in seconds. Default: {DEFAULT_REFRESH_SECONDS}",
    )
    parser.add_argument(
        "--event-limit",
        type=int,
        default=DEFAULT_EVENT_LIMIT,
        help=f"How many recent health-event rows to show. Default: {DEFAULT_EVENT_LIMIT}",
    )
    parser.add_argument(
        "--snapshot-limit",
        type=int,
        default=DEFAULT_SNAPSHOT_LIMIT,
        help=f"How many recent snapshot rows to show. Default: {DEFAULT_SNAPSHOT_LIMIT}",
    )
    parser.add_argument(
        "--alert-history-limit",
        type=int,
        default=DEFAULT_ALERT_HISTORY_LIMIT,
        help=f"How many alert-history rows to show. Default: {DEFAULT_ALERT_HISTORY_LIMIT}",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the generated dashboard in the default browser.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.refresh_seconds <= 0:
        print("ERROR: --refresh-seconds must be greater than 0")
        return 1

    if args.event_limit < 0:
        print("ERROR: --event-limit must be 0 or greater")
        return 1

    if args.snapshot_limit < 0:
        print("ERROR: --snapshot-limit must be 0 or greater")
        return 1

    if args.alert_history_limit < 0:
        print("ERROR: --alert-history-limit must be 0 or greater")
        return 1

    dashboard_path = generate_dashboard(
        refresh_seconds=args.refresh_seconds,
        event_limit=args.event_limit,
        snapshot_limit=args.snapshot_limit,
        alert_history_limit=args.alert_history_limit,
    )

    print("=" * 72)
    print("GAMMA ENGINE MONITOR DASHBOARD")
    print("=" * 72)
    print(f"Dashboard written to: {dashboard_path}")

    if args.open_browser:
        webbrowser.open(dashboard_path.resolve().as_uri())
        print("Opened dashboard in browser.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())