from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from gamma_engine_heartbeat import mark_component_error, mark_component_ok, mark_component_warn


BASE_DIR = Path(__file__).resolve().parent
TELEMETRY_DIR = BASE_DIR / "runtime" / "telemetry"
HEARTBEAT_DIR = BASE_DIR / "runtime" / "heartbeats"

LATEST_JSON = TELEMETRY_DIR / "latest_health_snapshot.json"
EVENT_LOG_JSONL = TELEMETRY_DIR / "health_events.jsonl"

ALERTS_JSONL = TELEMETRY_DIR / "alerts.jsonl"
ALERT_STATE_JSON = TELEMETRY_DIR / "alert_state.json"
LATEST_ALERTS_JSON = TELEMETRY_DIR / "latest_alerts.json"

DEFAULT_INTERVAL_SECONDS = 30
DEFAULT_MAX_ALERT_ROWS = 5000
DEFAULT_RECENT_EVENT_LOOKBACK = 20
ALERT_DAEMON_HEARTBEAT_STALE_AFTER_SECONDS = 120

ALERT_DAEMON_COMPONENT_NAME = "gamma_engine_alert_daemon"

HEARTBEAT_COMPONENTS = [
    "gamma_engine_supervisor",
    "run_option_snapshot_intraday_runner",
    "gamma_engine_telemetry_logger",
    "gamma_engine_alert_daemon",
]


@dataclass
class AlertRecord:
    detected_at_utc: str
    alert_level: str
    alert_code: str
    fingerprint: str
    summary: str
    engine: Optional[str]
    pipeline: Optional[str]
    symbol_sync: Optional[str]
    session: Optional[str]
    summary_line: Optional[str]
    source: str
    details: Dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


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


def trim_jsonl_file(path: Path, keep_last: int) -> None:
    if keep_last <= 0 or not path.exists():
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines(True)
    except Exception:
        return

    if len(lines) <= keep_last:
        return

    path.write_text("".join(lines[-keep_last:]), encoding="utf-8")


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def build_fingerprint(
    alert_code: str,
    summary_line: Optional[str],
    extra: Optional[str] = None,
) -> str:
    parts = [normalize_text(alert_code), normalize_text(summary_line), normalize_text(extra)]
    return " | ".join(parts)


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    text = normalize_text(value)
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

    base_status = normalize_text(payload.get("status")).upper()

    if age is not None and stale_after_int is not None and age > stale_after_int:
        return "STALE"

    if base_status in {"ERROR", "FAILED"}:
        return "ERROR"

    if base_status in {"WARN", "WARNING"}:
        return "WARN"

    if base_status in {"OK", "INFO"}:
        return "OK"

    return base_status if base_status else "UNKNOWN"


def load_heartbeat_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for component_name in HEARTBEAT_COMPONENTS:
        path = heartbeat_file_path(component_name)
        payload = read_json(path)

        rows.append(
            {
                "component_name": component_name,
                "path": str(path),
                "payload": payload,
                "display_status": heartbeat_display_status(payload),
                "age_seconds": heartbeat_age_seconds(payload) if payload else None,
            }
        )

    return rows


def _write_alert_daemon_heartbeat(
    *,
    status: str,
    notes: str,
    session: Optional[str] = None,
    last_successful_cycle_utc: Optional[str] = None,
    interval_seconds: Optional[int] = None,
    active_alert_count: Optional[int] = None,
    latest_engine: Optional[str] = None,
    latest_pipeline: Optional[str] = None,
    latest_symbol_sync: Optional[str] = None,
) -> None:
    extra: Dict[str, Any] = {
        "alert_state_path": str(ALERT_STATE_JSON),
        "latest_alerts_path": str(LATEST_ALERTS_JSON),
        "alerts_log_path": str(ALERTS_JSONL),
    }

    if interval_seconds is not None:
        extra["interval_seconds"] = interval_seconds
    if active_alert_count is not None:
        extra["active_alert_count"] = active_alert_count
    if latest_engine is not None:
        extra["latest_engine"] = latest_engine
    if latest_pipeline is not None:
        extra["latest_pipeline"] = latest_pipeline
    if latest_symbol_sync is not None:
        extra["latest_symbol_sync"] = latest_symbol_sync

    if status == "OK":
        mark_component_ok(
            ALERT_DAEMON_COMPONENT_NAME,
            session=session,
            last_successful_cycle_utc=last_successful_cycle_utc,
            stale_after_seconds=ALERT_DAEMON_HEARTBEAT_STALE_AFTER_SECONDS,
            notes=notes,
            extra=extra,
        )
    elif status == "WARN":
        mark_component_warn(
            ALERT_DAEMON_COMPONENT_NAME,
            session=session,
            last_successful_cycle_utc=last_successful_cycle_utc,
            stale_after_seconds=ALERT_DAEMON_HEARTBEAT_STALE_AFTER_SECONDS,
            notes=notes,
            extra=extra,
        )
    else:
        mark_component_error(
            ALERT_DAEMON_COMPONENT_NAME,
            session=session,
            last_successful_cycle_utc=last_successful_cycle_utc,
            stale_after_seconds=ALERT_DAEMON_HEARTBEAT_STALE_AFTER_SECONDS,
            notes=notes,
            extra=extra,
        )


def classify_stage_alerts(snapshot: Dict[str, Any]) -> List[AlertRecord]:
    alerts: List[AlertRecord] = []
    detected_at = utc_now_iso()

    pipeline_details = snapshot.get("pipeline_details", {}) or {}

    for symbol in ("NIFTY", "SENSEX"):
        rows = pipeline_details.get(symbol, []) or []
        for row in rows:
            stage = normalize_text(row.get("stage"))
            status = normalize_text(row.get("status")).upper()
            if status in {"", "OK"}:
                continue

            alert_level = "ERROR" if status in {"ERROR", "FAILED"} else "WARN"
            summary = f"{symbol} stage {stage} status is {status}"
            fingerprint = build_fingerprint(
                alert_code=f"STAGE_{symbol}_{stage}_{status}",
                summary_line=snapshot.get("summary_line"),
                extra=f"{symbol}|{stage}|{status}",
            )
            alerts.append(
                AlertRecord(
                    detected_at_utc=detected_at,
                    alert_level=alert_level,
                    alert_code=f"STAGE_{symbol}_{stage}_{status}",
                    fingerprint=fingerprint,
                    summary=summary,
                    engine=snapshot.get("engine"),
                    pipeline=snapshot.get("pipeline"),
                    symbol_sync=snapshot.get("symbol_sync"),
                    session=snapshot.get("session"),
                    summary_line=snapshot.get("summary_line"),
                    source="latest_health_snapshot",
                    details={
                        "symbol": symbol,
                        "stage": stage,
                        "status": status,
                        "ts": row.get("ts"),
                        "age_seconds": row.get("age_seconds"),
                    },
                )
            )

    return alerts


def build_snapshot_alerts(snapshot: Dict[str, Any]) -> List[AlertRecord]:
    alerts: List[AlertRecord] = []
    detected_at = utc_now_iso()

    returncode = int(snapshot.get("health_check_returncode", 0) or 0)
    event_level = normalize_text(snapshot.get("event_level")).upper()
    engine = normalize_text(snapshot.get("engine")).upper()
    pipeline = normalize_text(snapshot.get("pipeline")).upper()
    symbol_sync = normalize_text(snapshot.get("symbol_sync")).upper()

    if not snapshot:
        fingerprint = build_fingerprint("SNAPSHOT_MISSING", None, "latest snapshot missing")
        alerts.append(
            AlertRecord(
                detected_at_utc=detected_at,
                alert_level="ERROR",
                alert_code="SNAPSHOT_MISSING",
                fingerprint=fingerprint,
                summary="Latest health snapshot file is missing or unreadable",
                engine=None,
                pipeline=None,
                symbol_sync=None,
                session=None,
                summary_line=None,
                source="latest_health_snapshot",
                details={},
            )
        )
        return alerts

    if returncode != 0:
        fingerprint = build_fingerprint(
            "HEALTHCHECK_NONZERO_RETURN", snapshot.get("summary_line"), str(returncode)
        )
        alerts.append(
            AlertRecord(
                detected_at_utc=detected_at,
                alert_level="ERROR",
                alert_code="HEALTHCHECK_NONZERO_RETURN",
                fingerprint=fingerprint,
                summary=f"Health check returned non-zero exit code: {returncode}",
                engine=snapshot.get("engine"),
                pipeline=snapshot.get("pipeline"),
                symbol_sync=snapshot.get("symbol_sync"),
                session=snapshot.get("session"),
                summary_line=snapshot.get("summary_line"),
                source="latest_health_snapshot",
                details={"health_check_returncode": returncode},
            )
        )

    if event_level in {"WARN", "ERROR"}:
        fingerprint = build_fingerprint(f"EVENT_LEVEL_{event_level}", snapshot.get("summary_line"))
        alerts.append(
            AlertRecord(
                detected_at_utc=detected_at,
                alert_level=event_level,
                alert_code=f"EVENT_LEVEL_{event_level}",
                fingerprint=fingerprint,
                summary=f"Snapshot event level is {event_level}",
                engine=snapshot.get("engine"),
                pipeline=snapshot.get("pipeline"),
                symbol_sync=snapshot.get("symbol_sync"),
                session=snapshot.get("session"),
                summary_line=snapshot.get("summary_line"),
                source="latest_health_snapshot",
                details={"event_level": event_level},
            )
        )

    if engine in {"ERROR", "FAILED"}:
        fingerprint = build_fingerprint("ENGINE_CRITICAL", snapshot.get("summary_line"), engine)
        alerts.append(
            AlertRecord(
                detected_at_utc=detected_at,
                alert_level="ERROR",
                alert_code="ENGINE_CRITICAL",
                fingerprint=fingerprint,
                summary=f"Engine status is {engine}",
                engine=snapshot.get("engine"),
                pipeline=snapshot.get("pipeline"),
                symbol_sync=snapshot.get("symbol_sync"),
                session=snapshot.get("session"),
                summary_line=snapshot.get("summary_line"),
                source="latest_health_snapshot",
                details={"engine": snapshot.get("engine")},
            )
        )
    elif engine in {"STALE", "WARN", "WARNING"}:
        fingerprint = build_fingerprint("ENGINE_WARN", snapshot.get("summary_line"), engine)
        alerts.append(
            AlertRecord(
                detected_at_utc=detected_at,
                alert_level="WARN",
                alert_code="ENGINE_WARN",
                fingerprint=fingerprint,
                summary=f"Engine status is {engine}",
                engine=snapshot.get("engine"),
                pipeline=snapshot.get("pipeline"),
                symbol_sync=snapshot.get("symbol_sync"),
                session=snapshot.get("session"),
                summary_line=snapshot.get("summary_line"),
                source="latest_health_snapshot",
                details={"engine": snapshot.get("engine")},
            )
        )

    if pipeline in {"ERROR", "FAILED"}:
        fingerprint = build_fingerprint("PIPELINE_CRITICAL", snapshot.get("summary_line"), pipeline)
        alerts.append(
            AlertRecord(
                detected_at_utc=detected_at,
                alert_level="ERROR",
                alert_code="PIPELINE_CRITICAL",
                fingerprint=fingerprint,
                summary=f"Pipeline status is {pipeline}",
                engine=snapshot.get("engine"),
                pipeline=snapshot.get("pipeline"),
                symbol_sync=snapshot.get("symbol_sync"),
                session=snapshot.get("session"),
                summary_line=snapshot.get("summary_line"),
                source="latest_health_snapshot",
                details={"pipeline": snapshot.get("pipeline")},
            )
        )
    elif pipeline in {"STALE", "WARN", "WARNING"}:
        fingerprint = build_fingerprint("PIPELINE_WARN", snapshot.get("summary_line"), pipeline)
        alerts.append(
            AlertRecord(
                detected_at_utc=detected_at,
                alert_level="WARN",
                alert_code="PIPELINE_WARN",
                fingerprint=fingerprint,
                summary=f"Pipeline status is {pipeline}",
                engine=snapshot.get("engine"),
                pipeline=snapshot.get("pipeline"),
                symbol_sync=snapshot.get("symbol_sync"),
                session=snapshot.get("session"),
                summary_line=snapshot.get("summary_line"),
                source="latest_health_snapshot",
                details={"pipeline": snapshot.get("pipeline")},
            )
        )

    if symbol_sync in {"ERROR", "FAILED", "MISSING", "DRIFT"}:
        level = "ERROR" if symbol_sync in {"ERROR", "FAILED"} else "WARN"
        fingerprint = build_fingerprint("SYMBOL_SYNC_ALERT", snapshot.get("summary_line"), symbol_sync)
        alerts.append(
            AlertRecord(
                detected_at_utc=detected_at,
                alert_level=level,
                alert_code="SYMBOL_SYNC_ALERT",
                fingerprint=fingerprint,
                summary=f"Symbol sync status is {symbol_sync}",
                engine=snapshot.get("engine"),
                pipeline=snapshot.get("pipeline"),
                symbol_sync=snapshot.get("symbol_sync"),
                session=snapshot.get("session"),
                summary_line=snapshot.get("summary_line"),
                source="latest_health_snapshot",
                details={"symbol_sync": snapshot.get("symbol_sync")},
            )
        )

    alerts.extend(classify_stage_alerts(snapshot))
    return alerts


def build_event_log_alerts(events: List[Dict[str, Any]]) -> List[AlertRecord]:
    alerts: List[AlertRecord] = []
    detected_at = utc_now_iso()

    for event in events:
        level = normalize_text(event.get("event_level")).upper()
        if level not in {"WARN", "ERROR"}:
            continue

        summary_line = event.get("summary_line")
        fingerprint = build_fingerprint(
            "EVENT_LOG_ALERT", summary_line, f"{event.get('captured_at_utc')}|{level}"
        )
        alerts.append(
            AlertRecord(
                detected_at_utc=detected_at,
                alert_level=level,
                alert_code="EVENT_LOG_ALERT",
                fingerprint=fingerprint,
                summary=f"Recent event log contains {level} entry",
                engine=event.get("engine"),
                pipeline=event.get("pipeline"),
                symbol_sync=event.get("symbol_sync"),
                session=event.get("session"),
                summary_line=summary_line,
                source="health_events_jsonl",
                details=event,
            )
        )

    return alerts


def build_heartbeat_alerts(heartbeat_rows: List[Dict[str, Any]]) -> List[AlertRecord]:
    alerts: List[AlertRecord] = []
    detected_at = utc_now_iso()

    for row in heartbeat_rows:
        component_name = row.get("component_name")
        payload = row.get("payload", {}) or {}
        display_status = normalize_text(row.get("display_status")).upper()
        age_seconds = row.get("age_seconds")

        session = payload.get("session")
        base_status = normalize_text(payload.get("status")).upper()
        notes = payload.get("notes")

        if display_status == "MISSING":
            fingerprint = build_fingerprint(
                "HEARTBEAT_MISSING", None, component_name
            )
            alerts.append(
                AlertRecord(
                    detected_at_utc=detected_at,
                    alert_level="ERROR",
                    alert_code="HEARTBEAT_MISSING",
                    fingerprint=fingerprint,
                    summary=f"Heartbeat missing for component {component_name}",
                    engine=None,
                    pipeline=None,
                    symbol_sync=None,
                    session=session,
                    summary_line=None,
                    source="heartbeat_monitor",
                    details={
                        "component_name": component_name,
                        "path": row.get("path"),
                    },
                )
            )
            continue

        if display_status == "STALE":
            fingerprint = build_fingerprint(
                "HEARTBEAT_STALE", None, f"{component_name}|{age_seconds}"
            )
            alerts.append(
                AlertRecord(
                    detected_at_utc=detected_at,
                    alert_level="WARN",
                    alert_code="HEARTBEAT_STALE",
                    fingerprint=fingerprint,
                    summary=f"Heartbeat stale for component {component_name}",
                    engine=None,
                    pipeline=None,
                    symbol_sync=None,
                    session=session,
                    summary_line=None,
                    source="heartbeat_monitor",
                    details={
                        "component_name": component_name,
                        "age_seconds": age_seconds,
                        "stale_after_seconds": payload.get("stale_after_seconds"),
                        "base_status": base_status,
                        "notes": notes,
                    },
                )
            )
            continue

        if base_status in {"WARN", "WARNING"}:
            fingerprint = build_fingerprint(
                "HEARTBEAT_BASE_WARN", None, component_name
            )
            alerts.append(
                AlertRecord(
                    detected_at_utc=detected_at,
                    alert_level="WARN",
                    alert_code="HEARTBEAT_BASE_WARN",
                    fingerprint=fingerprint,
                    summary=f"Heartbeat base status WARN for component {component_name}",
                    engine=None,
                    pipeline=None,
                    symbol_sync=None,
                    session=session,
                    summary_line=None,
                    source="heartbeat_monitor",
                    details={
                        "component_name": component_name,
                        "base_status": base_status,
                        "notes": notes,
                    },
                )
            )
            continue

        if base_status in {"ERROR", "FAILED"}:
            fingerprint = build_fingerprint(
                "HEARTBEAT_BASE_ERROR", None, component_name
            )
            alerts.append(
                AlertRecord(
                    detected_at_utc=detected_at,
                    alert_level="ERROR",
                    alert_code="HEARTBEAT_BASE_ERROR",
                    fingerprint=fingerprint,
                    summary=f"Heartbeat base status ERROR for component {component_name}",
                    engine=None,
                    pipeline=None,
                    symbol_sync=None,
                    session=session,
                    summary_line=None,
                    source="heartbeat_monitor",
                    details={
                        "component_name": component_name,
                        "base_status": base_status,
                        "notes": notes,
                    },
                )
            )

    return alerts


def dedupe_alerts(alerts: List[AlertRecord]) -> List[AlertRecord]:
    seen = set()
    deduped: List[AlertRecord] = []
    for alert in alerts:
        if alert.fingerprint in seen:
            continue
        seen.add(alert.fingerprint)
        deduped.append(alert)
    return deduped


def load_previous_state() -> Dict[str, Any]:
    return read_json(ALERT_STATE_JSON)


def save_current_state(
    active_alerts: List[AlertRecord],
    latest_snapshot: Dict[str, Any],
) -> None:
    state = {
        "updated_at_utc": utc_now_iso(),
        "active_alert_count": len(active_alerts),
        "active_fingerprints": [a.fingerprint for a in active_alerts],
        "latest_summary_line": latest_snapshot.get("summary_line"),
        "latest_engine": latest_snapshot.get("engine"),
        "latest_pipeline": latest_snapshot.get("pipeline"),
        "latest_symbol_sync": latest_snapshot.get("symbol_sync"),
        "latest_session": latest_snapshot.get("session"),
    }
    write_json(ALERT_STATE_JSON, state)

    latest_alerts_payload = {
        "updated_at_utc": utc_now_iso(),
        "active_alerts": [asdict(a) for a in active_alerts],
    }
    write_json(LATEST_ALERTS_JSON, latest_alerts_payload)


def diff_alert_states(
    previous_fingerprints: List[str],
    current_alerts: List[AlertRecord],
) -> Tuple[List[AlertRecord], List[str]]:
    previous = set(previous_fingerprints)
    current = {a.fingerprint for a in current_alerts}

    new_alerts = [a for a in current_alerts if a.fingerprint not in previous]
    cleared = sorted(previous - current)
    return new_alerts, cleared


def persist_new_alerts(new_alerts: List[AlertRecord], max_alert_rows: int) -> None:
    for alert in new_alerts:
        append_jsonl(ALERTS_JSONL, asdict(alert))
    trim_jsonl_file(ALERTS_JSONL, max_alert_rows)


def print_cycle_report(
    latest_snapshot: Dict[str, Any],
    active_alerts: List[AlertRecord],
    new_alerts: List[AlertRecord],
    cleared_alerts: List[str],
) -> None:
    print("=" * 72)
    print("GAMMA ENGINE ALERT DAEMON")
    print("=" * 72)
    print(f"Checked at UTC   : {utc_now_iso()}")
    print(f"Summary line     : {latest_snapshot.get('summary_line')}")
    print(f"Active alerts    : {len(active_alerts)}")
    print(f"New alerts       : {len(new_alerts)}")
    print(f"Cleared alerts   : {len(cleared_alerts)}")
    print(f"Alert state file : {ALERT_STATE_JSON}")
    print(f"Alert log file   : {ALERTS_JSONL}")

    for alert in new_alerts:
        print(f"[NEW {alert.alert_level}] {alert.summary}")

    for fp in cleared_alerts:
        print(f"[CLEARED] {fp}")


def evaluate_alerts(event_lookback: int) -> Tuple[Dict[str, Any], List[AlertRecord]]:
    latest_snapshot = read_json(LATEST_JSON)
    recent_events = read_jsonl_tail(EVENT_LOG_JSONL, event_lookback)
    heartbeat_rows = load_heartbeat_rows()

    alerts: List[AlertRecord] = []
    alerts.extend(build_snapshot_alerts(latest_snapshot))
    alerts.extend(build_event_log_alerts(recent_events))
    alerts.extend(build_heartbeat_alerts(heartbeat_rows))

    active_alerts = dedupe_alerts(alerts)
    return latest_snapshot, active_alerts


def run_once(
    event_lookback: int,
    max_alert_rows: int,
    quiet: bool,
    interval_seconds: Optional[int] = None,
) -> int:
    previous_state = load_previous_state()
    previous_fingerprints = previous_state.get("active_fingerprints", []) or []

    latest_snapshot, active_alerts = evaluate_alerts(event_lookback=event_lookback)
    new_alerts, cleared_alerts = diff_alert_states(previous_fingerprints, active_alerts)

    persist_new_alerts(new_alerts, max_alert_rows)
    save_current_state(active_alerts, latest_snapshot)

    hb_status = "OK" if len(active_alerts) == 0 else "WARN"
    hb_notes = (
        "Alert daemon evaluated successfully with no active alerts"
        if len(active_alerts) == 0
        else f"Alert daemon evaluated successfully with {len(active_alerts)} active alert(s)"
    )

    _write_alert_daemon_heartbeat(
        status=hb_status,
        notes=hb_notes,
        session=latest_snapshot.get("session"),
        last_successful_cycle_utc=utc_now_iso(),
        interval_seconds=interval_seconds,
        active_alert_count=len(active_alerts),
        latest_engine=latest_snapshot.get("engine"),
        latest_pipeline=latest_snapshot.get("pipeline"),
        latest_symbol_sync=latest_snapshot.get("symbol_sync"),
    )

    if not quiet:
        print_cycle_report(
            latest_snapshot=latest_snapshot,
            active_alerts=active_alerts,
            new_alerts=new_alerts,
            cleared_alerts=cleared_alerts,
        )

    return 0


def run_loop(interval_seconds: int, event_lookback: int, max_alert_rows: int, quiet: bool) -> int:
    print("=" * 72)
    print("GAMMA ENGINE ALERT DAEMON - LOOP MODE")
    print("=" * 72)
    print(f"Polling every {interval_seconds} seconds")
    print(f"Latest snapshot  : {LATEST_JSON}")
    print(f"Event log        : {EVENT_LOG_JSONL}")
    print(f"Alert log        : {ALERTS_JSONL}")
    print("Press Ctrl+C to stop.")
    print()

    _write_alert_daemon_heartbeat(
        status="OK",
        notes="Alert daemon loop started",
        interval_seconds=interval_seconds,
    )

    while True:
        try:
            run_once(
                event_lookback=event_lookback,
                max_alert_rows=max_alert_rows,
                quiet=quiet,
                interval_seconds=interval_seconds,
            )
        except Exception as exc:
            error_alert = AlertRecord(
                detected_at_utc=utc_now_iso(),
                alert_level="ERROR",
                alert_code="ALERT_DAEMON_EXCEPTION",
                fingerprint=build_fingerprint("ALERT_DAEMON_EXCEPTION", None, str(exc)),
                summary=f"Alert daemon exception: {exc}",
                engine=None,
                pipeline=None,
                symbol_sync=None,
                session=None,
                summary_line=None,
                source="alert_daemon",
                details={"exception": str(exc)},
            )
            append_jsonl(ALERTS_JSONL, asdict(error_alert))
            trim_jsonl_file(ALERTS_JSONL, max_alert_rows)

            _write_alert_daemon_heartbeat(
                status="ERROR",
                notes=f"Alert daemon exception: {exc}",
                last_successful_cycle_utc=utc_now_iso(),
                interval_seconds=interval_seconds,
            )

            if not quiet:
                print(f"[ERROR] Alert daemon exception: {exc}")

        time.sleep(interval_seconds)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gamma Engine telemetry-driven alert daemon.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one alert evaluation cycle and exit.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Polling interval in seconds for loop mode. Default: {DEFAULT_INTERVAL_SECONDS}",
    )
    parser.add_argument(
        "--event-lookback",
        type=int,
        default=DEFAULT_RECENT_EVENT_LOOKBACK,
        help=f"How many recent health events to inspect. Default: {DEFAULT_RECENT_EVENT_LOOKBACK}",
    )
    parser.add_argument(
        "--max-alert-rows",
        type=int,
        default=DEFAULT_MAX_ALERT_ROWS,
        help=f"Maximum alert log rows to retain. Default: {DEFAULT_MAX_ALERT_ROWS}",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce console output.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.interval <= 0:
        print("ERROR: --interval must be greater than 0")
        return 1

    if args.event_lookback < 0:
        print("ERROR: --event-lookback must be 0 or greater")
        return 1

    if args.max_alert_rows <= 0:
        print("ERROR: --max-alert-rows must be greater than 0")
        return 1

    if args.once:
        return run_once(
            event_lookback=args.event_lookback,
            max_alert_rows=args.max_alert_rows,
            quiet=args.quiet,
            interval_seconds=args.interval,
        )

    return run_loop(
        interval_seconds=args.interval,
        event_lookback=args.event_lookback,
        max_alert_rows=args.max_alert_rows,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    raise SystemExit(main())