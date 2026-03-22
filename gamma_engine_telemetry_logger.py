from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from gamma_engine_heartbeat import mark_component_error, mark_component_ok, mark_component_warn


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime" / "telemetry"

SNAPSHOT_JSONL = RUNTIME_DIR / "health_snapshots.jsonl"
LATEST_JSON = RUNTIME_DIR / "latest_health_snapshot.json"
LATEST_TXT = RUNTIME_DIR / "latest_health_check_output.txt"
EVENT_LOG_JSONL = RUNTIME_DIR / "health_events.jsonl"

DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_MAX_SNAPSHOTS = 5000
TELEMETRY_HEARTBEAT_STALE_AFTER_SECONDS = 180

TELEMETRY_COMPONENT_NAME = "gamma_engine_telemetry_logger"

SUMMARY_PATTERN = re.compile(
    r"ENGINE:\s*(?P<engine>[^|]+?)\s*\|\s*"
    r"PIPELINE:\s*(?P<pipeline>[^|]+?)\s*\|\s*"
    r"SYMBOL_SYNC:\s*(?P<symbol_sync>[^|]+?)\s*\|\s*"
    r"SESSION:\s*(?P<session>.+?)\s*$"
)

SECTION_DIVIDER_PATTERN = re.compile(r"^-{10,}\s*$")
GENERIC_LABEL_VALUE_PATTERN = re.compile(r"^\s*([^:]+?)\s*:\s*(.+?)\s*$")
PIPELINE_STAGE_PATTERN = re.compile(
    r"^(?P<stage>[A-Za-z_]+)\s+status=\s*(?P<status>\S+)\s+ts=(?P<ts>.+?)\s+age=(?P<age>\d+)s\s*$"
)
QUICK_SUMMARY_PATTERN = re.compile(
    r"^(?P<symbol>NIFTY|SENSEX)\s+\|\s+"
    r"options=(?P<options>\S+)\s+\|\s+"
    r"gamma=(?P<gamma>\S+)\s+\|\s+"
    r"vol=(?P<vol>\S+)\s+\|\s+"
    r"mom=(?P<mom>\S+)\s+\|\s+"
    r"state=(?P<state>\S+)\s+\|\s+"
    r"signal=(?P<signal>\S+)\s+\|\s+"
    r"mode=(?P<mode>.+?)\s*$"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_runtime_dirs() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def trim_jsonl_file(path: Path, keep_last: int) -> None:
    if keep_last <= 0 or not path.exists():
        return

    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) <= keep_last:
        return

    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines[-keep_last:])


def normalize_label(label: str) -> str:
    label = label.strip().lower()
    label = re.sub(r"[^a-z0-9]+", "_", label)
    label = re.sub(r"_+", "_", label)
    return label.strip("_")


def run_health_check(python_executable: str) -> Dict[str, Any]:
    command = [python_executable, "gamma_engine_health_check.py"]

    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    elapsed = time.perf_counter() - started

    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
        "duration_seconds": round(elapsed, 6),
    }


def parse_summary_line(stdout: str) -> Dict[str, Optional[str]]:
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = SUMMARY_PATTERN.search(line)
        if match:
            return {
                "engine": match.group("engine").strip(),
                "pipeline": match.group("pipeline").strip(),
                "symbol_sync": match.group("symbol_sync").strip(),
                "session": match.group("session").strip(),
                "summary_line": line,
            }

    return {
        "engine": None,
        "pipeline": None,
        "symbol_sync": None,
        "session": None,
        "summary_line": None,
    }


def parse_general_fields(stdout: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}

    for raw_line in stdout.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("=") or SECTION_DIVIDER_PATTERN.match(stripped):
            continue

        if stripped in {
            "GAMMA ENGINE HEALTH CHECK",
            "Live-cycle lag summary:",
            "Quick summary:",
            "NIFTY PIPELINE",
            "SENSEX PIPELINE",
            "Pipeline order:",
        }:
            continue

        if PIPELINE_STAGE_PATTERN.match(stripped):
            continue

        if QUICK_SUMMARY_PATTERN.match(stripped):
            continue

        match = GENERIC_LABEL_VALUE_PATTERN.match(stripped)
        if not match:
            continue

        label = normalize_label(match.group(1))
        value = match.group(2).strip()

        if not label:
            continue

        if label == "engine":
            continue

        fields[label] = value

    return fields


def parse_quick_summary(stdout: str) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}

    for raw_line in stdout.splitlines():
        stripped = raw_line.strip()
        match = QUICK_SUMMARY_PATTERN.match(stripped)
        if not match:
            continue

        symbol = match.group("symbol").strip()
        result[symbol] = {
            "options": match.group("options").strip(),
            "gamma": match.group("gamma").strip(),
            "vol": match.group("vol").strip(),
            "mom": match.group("mom").strip(),
            "state": match.group("state").strip(),
            "signal": match.group("signal").strip(),
            "mode": match.group("mode").strip(),
        }

    return result


def parse_pipeline_sections(stdout: str) -> Dict[str, List[Dict[str, Any]]]:
    sections: Dict[str, List[Dict[str, Any]]] = {
        "NIFTY": [],
        "SENSEX": [],
    }

    current_symbol: Optional[str] = None

    for raw_line in stdout.splitlines():
        stripped = raw_line.strip()

        if stripped == "NIFTY PIPELINE":
            current_symbol = "NIFTY"
            continue

        if stripped == "SENSEX PIPELINE":
            current_symbol = "SENSEX"
            continue

        if not current_symbol:
            continue

        match = PIPELINE_STAGE_PATTERN.match(stripped)
        if not match:
            continue

        sections[current_symbol].append(
            {
                "stage": match.group("stage").strip(),
                "status": match.group("status").strip(),
                "ts": match.group("ts").strip(),
                "age_seconds": int(match.group("age")),
            }
        )

    return sections


def classify_event_level(
    engine: Optional[str],
    pipeline: Optional[str],
    symbol_sync: Optional[str],
) -> str:
    values = [engine, pipeline, symbol_sync]

    if any(v is None for v in values):
        return "ERROR"

    joined = " | ".join(values).upper()

    if "ERROR" in joined or "FAILED" in joined:
        return "ERROR"

    if "STALE" in joined or "MISSING" in joined or "DRIFT" in joined:
        return "WARN"

    if "HEALTHY" in joined or "OK" in joined or "CLOSED_OK" in joined or "STANDBY" in joined:
        return "INFO"

    return "INFO"


def build_snapshot(result: Dict[str, Any]) -> Dict[str, Any]:
    stdout = result["stdout"]
    summary = parse_summary_line(stdout)
    general_fields = parse_general_fields(stdout)
    quick_summary = parse_quick_summary(stdout)
    pipeline_details = parse_pipeline_sections(stdout)

    snapshot: Dict[str, Any] = {
        "captured_at_utc": utc_now_iso(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_executable": sys.executable,
        "health_check_command": result["command"],
        "health_check_returncode": result["returncode"],
        "health_check_duration_seconds": result["duration_seconds"],
        "engine": summary["engine"],
        "pipeline": summary["pipeline"],
        "symbol_sync": summary["symbol_sync"],
        "session": summary["session"],
        "summary_line": summary["summary_line"],
        "parsed_fields": general_fields,
        "quick_summary": quick_summary,
        "pipeline_details": pipeline_details,
        "stdout": stdout,
        "stderr": result["stderr"],
    }

    snapshot["event_level"] = classify_event_level(
        snapshot["engine"],
        snapshot["pipeline"],
        snapshot["symbol_sync"],
    )

    return snapshot


def record_event_if_needed(snapshot: Dict[str, Any]) -> None:
    level = snapshot.get("event_level", "INFO")
    returncode = snapshot.get("health_check_returncode", 1)

    if level == "INFO" and returncode == 0:
        return

    event = {
        "captured_at_utc": snapshot["captured_at_utc"],
        "event_level": level,
        "engine": snapshot.get("engine"),
        "pipeline": snapshot.get("pipeline"),
        "symbol_sync": snapshot.get("symbol_sync"),
        "session": snapshot.get("session"),
        "health_check_returncode": returncode,
        "summary_line": snapshot.get("summary_line"),
    }

    append_jsonl(EVENT_LOG_JSONL, event)


def persist_snapshot(snapshot: Dict[str, Any], max_snapshots: int) -> None:
    append_jsonl(SNAPSHOT_JSONL, snapshot)
    write_json(LATEST_JSON, snapshot)
    write_text(LATEST_TXT, snapshot.get("stdout", ""))

    trim_jsonl_file(SNAPSHOT_JSONL, max_snapshots)
    trim_jsonl_file(EVENT_LOG_JSONL, max_snapshots)

    record_event_if_needed(snapshot)


def _write_telemetry_heartbeat(
    *,
    status: str,
    notes: str,
    session: Optional[str] = None,
    last_successful_cycle_utc: Optional[str] = None,
    interval_seconds: Optional[int] = None,
    latest_engine: Optional[str] = None,
    latest_pipeline: Optional[str] = None,
    latest_symbol_sync: Optional[str] = None,
) -> None:
    extra: Dict[str, Any] = {
        "latest_json_path": str(LATEST_JSON),
        "snapshot_log_path": str(SNAPSHOT_JSONL),
        "event_log_path": str(EVENT_LOG_JSONL),
    }

    if interval_seconds is not None:
        extra["interval_seconds"] = interval_seconds
    if latest_engine is not None:
        extra["latest_engine"] = latest_engine
    if latest_pipeline is not None:
        extra["latest_pipeline"] = latest_pipeline
    if latest_symbol_sync is not None:
        extra["latest_symbol_sync"] = latest_symbol_sync

    if status == "OK":
        mark_component_ok(
            TELEMETRY_COMPONENT_NAME,
            session=session,
            last_successful_cycle_utc=last_successful_cycle_utc,
            stale_after_seconds=TELEMETRY_HEARTBEAT_STALE_AFTER_SECONDS,
            notes=notes,
            extra=extra,
        )
    elif status == "WARN":
        mark_component_warn(
            TELEMETRY_COMPONENT_NAME,
            session=session,
            last_successful_cycle_utc=last_successful_cycle_utc,
            stale_after_seconds=TELEMETRY_HEARTBEAT_STALE_AFTER_SECONDS,
            notes=notes,
            extra=extra,
        )
    else:
        mark_component_error(
            TELEMETRY_COMPONENT_NAME,
            session=session,
            last_successful_cycle_utc=last_successful_cycle_utc,
            stale_after_seconds=TELEMETRY_HEARTBEAT_STALE_AFTER_SECONDS,
            notes=notes,
            extra=extra,
        )


def run_once(
    python_executable: str,
    max_snapshots: int,
    quiet: bool,
    interval_seconds: Optional[int] = None,
) -> int:
    result = run_health_check(python_executable)
    snapshot = build_snapshot(result)
    persist_snapshot(snapshot, max_snapshots)

    hb_status = "OK" if result["returncode"] == 0 else "ERROR"
    hb_notes = (
        "Telemetry snapshot captured successfully"
        if result["returncode"] == 0
        else "Health check returned non-zero exit code"
    )

    _write_telemetry_heartbeat(
        status=hb_status,
        notes=hb_notes,
        session=snapshot.get("session"),
        last_successful_cycle_utc=snapshot.get("captured_at_utc"),
        interval_seconds=interval_seconds,
        latest_engine=snapshot.get("engine"),
        latest_pipeline=snapshot.get("pipeline"),
        latest_symbol_sync=snapshot.get("symbol_sync"),
    )

    if not quiet:
        print("=" * 72)
        print("GAMMA ENGINE TELEMETRY LOGGER")
        print("=" * 72)
        print(f"Captured at UTC : {snapshot['captured_at_utc']}")
        print(f"Return code     : {snapshot['health_check_returncode']}")
        print(f"Duration (sec)  : {snapshot['health_check_duration_seconds']}")
        print(f"Engine          : {snapshot.get('engine')}")
        print(f"Pipeline        : {snapshot.get('pipeline')}")
        print(f"Symbol Sync     : {snapshot.get('symbol_sync')}")
        print(f"Session         : {snapshot.get('session')}")
        print(f"Event Level     : {snapshot.get('event_level')}")
        print(f"Latest JSON     : {LATEST_JSON}")
        print(f"Snapshot Log    : {SNAPSHOT_JSONL}")
        print(f"Event Log       : {EVENT_LOG_JSONL}")

    return 0 if result["returncode"] == 0 else result["returncode"]


def run_loop(
    python_executable: str,
    interval_seconds: int,
    max_snapshots: int,
    quiet: bool,
) -> int:
    print("=" * 72)
    print("GAMMA ENGINE TELEMETRY LOGGER - LOOP MODE")
    print("=" * 72)
    print(f"Polling every {interval_seconds} seconds")
    print(f"Writing to      {RUNTIME_DIR}")
    print("Press Ctrl+C to stop.")
    print()

    _write_telemetry_heartbeat(
        status="OK",
        notes="Telemetry logger loop started",
        interval_seconds=interval_seconds,
    )

    while True:
        try:
            run_once(
                python_executable=python_executable,
                max_snapshots=max_snapshots,
                quiet=quiet,
                interval_seconds=interval_seconds,
            )
        except Exception as exc:
            error_snapshot = {
                "captured_at_utc": utc_now_iso(),
                "hostname": platform.node(),
                "platform": platform.platform(),
                "python_executable": sys.executable,
                "health_check_command": [python_executable, "gamma_engine_health_check.py"],
                "health_check_returncode": -1,
                "health_check_duration_seconds": 0.0,
                "engine": None,
                "pipeline": None,
                "symbol_sync": None,
                "session": None,
                "summary_line": None,
                "parsed_fields": {},
                "quick_summary": {},
                "pipeline_details": {"NIFTY": [], "SENSEX": []},
                "stdout": "",
                "stderr": f"Telemetry logger exception: {exc}",
                "event_level": "ERROR",
            }
            persist_snapshot(error_snapshot, max_snapshots)

            _write_telemetry_heartbeat(
                status="ERROR",
                notes=f"Telemetry logger exception: {exc}",
                session=None,
                last_successful_cycle_utc=utc_now_iso(),
                interval_seconds=interval_seconds,
            )

            if not quiet:
                print(f"[ERROR] Telemetry logger exception: {exc}")

        time.sleep(interval_seconds)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persist Gamma Engine health-check telemetry snapshots."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one capture only and exit.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Polling interval in seconds for loop mode. Default: {DEFAULT_INTERVAL_SECONDS}",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to use for running gamma_engine_health_check.py",
    )
    parser.add_argument(
        "--max-snapshots",
        type=int,
        default=DEFAULT_MAX_SNAPSHOTS,
        help=f"Maximum lines to retain in JSONL logs. Default: {DEFAULT_MAX_SNAPSHOTS}",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce console output.",
    )
    return parser


def main() -> int:
    ensure_runtime_dirs()

    parser = build_arg_parser()
    args = parser.parse_args()

    if args.interval <= 0:
        print("ERROR: --interval must be greater than 0")
        return 1

    if args.max_snapshots <= 0:
        print("ERROR: --max-snapshots must be greater than 0")
        return 1

    if args.once:
        return run_once(
            python_executable=args.python,
            max_snapshots=args.max_snapshots,
            quiet=args.quiet,
            interval_seconds=args.interval,
        )

    return run_loop(
        python_executable=args.python,
        interval_seconds=args.interval,
        max_snapshots=args.max_snapshots,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    raise SystemExit(main())