from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


BASE_DIR = Path(__file__).resolve().parent
HEARTBEAT_DIR = BASE_DIR / "runtime" / "heartbeats"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_heartbeat_dir() -> None:
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)


def _component_file(component_name: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in component_name)
    return HEARTBEAT_DIR / f"{safe_name}.json"


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def write_heartbeat(
    component_name: str,
    *,
    status: str,
    session: Optional[str] = None,
    last_successful_cycle_utc: Optional[str] = None,
    stale_after_seconds: Optional[int] = None,
    notes: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    ensure_heartbeat_dir()

    payload: Dict[str, Any] = {
        "component_name": component_name,
        "last_heartbeat_utc": utc_now_iso(),
        "pid": os.getpid(),
        "status": status,
        "session": session,
        "last_successful_cycle_utc": last_successful_cycle_utc,
        "stale_after_seconds": stale_after_seconds,
        "notes": notes,
    }

    if extra:
        payload["extra"] = extra

    path = _component_file(component_name)
    _write_json_atomic(path, payload)
    return path


def mark_component_ok(
    component_name: str,
    *,
    session: Optional[str] = None,
    last_successful_cycle_utc: Optional[str] = None,
    stale_after_seconds: Optional[int] = None,
    notes: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    return write_heartbeat(
        component_name,
        status="OK",
        session=session,
        last_successful_cycle_utc=last_successful_cycle_utc,
        stale_after_seconds=stale_after_seconds,
        notes=notes,
        extra=extra,
    )


def mark_component_warn(
    component_name: str,
    *,
    session: Optional[str] = None,
    last_successful_cycle_utc: Optional[str] = None,
    stale_after_seconds: Optional[int] = None,
    notes: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    return write_heartbeat(
        component_name,
        status="WARN",
        session=session,
        last_successful_cycle_utc=last_successful_cycle_utc,
        stale_after_seconds=stale_after_seconds,
        notes=notes,
        extra=extra,
    )


def mark_component_error(
    component_name: str,
    *,
    session: Optional[str] = None,
    last_successful_cycle_utc: Optional[str] = None,
    stale_after_seconds: Optional[int] = None,
    notes: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    return write_heartbeat(
        component_name,
        status="ERROR",
        session=session,
        last_successful_cycle_utc=last_successful_cycle_utc,
        stale_after_seconds=stale_after_seconds,
        notes=notes,
        extra=extra,
    )


def load_heartbeat(component_name: str) -> Dict[str, Any]:
    path = _component_file(component_name)
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_all_heartbeats() -> Dict[str, Dict[str, Any]]:
    ensure_heartbeat_dir()

    result: Dict[str, Dict[str, Any]] = {}
    for path in sorted(HEARTBEAT_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

        component_name = payload.get("component_name") or path.stem
        result[str(component_name)] = payload

    return result