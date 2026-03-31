from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class PreflightError(Exception):
    pass


def now_ist_str() -> str:
    from datetime import timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(tz=IST).isoformat()


def log(msg: str) -> None:
    print(f"[{now_ist_str()}] {msg}")


class StageResult:
    def __init__(self, name: str):
        self.name = name
        self.status = "PASS"
        self.checks: List[Dict[str, Any]] = []
        self.started_at = now_ist_str()
        self.finished_at: Optional[str] = None

    def add_check(self, name: str, status: str, detail: str = ""):
        if status == "FAIL":
            self.status = "FAIL"
        self.checks.append({
            "name": name,
            "status": status,
            "detail": detail
        })

    def finalize(self):
        self.finished_at = now_ist_str()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "checks": self.checks,
        }


def run_subprocess(cmd: List[str], timeout: int = 60) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": "TIMEOUT"
        }


def ensure_env_loaded(env_path: str):
    if not os.path.exists(env_path):
        raise PreflightError(f".env not found at {env_path}")

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()


def write_report(report_path: str, data: Dict[str, Any]):
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def append_history(history_path: str, data: Dict[str, Any]):
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")