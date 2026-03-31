"""
MERDIAN Preflight Harness — Common Helpers
==========================================
Shared utilities for all preflight stages.
Handles: env loading, result formatting, pass/fail aggregation,
         logging, Telegram alerting, Supabase connectivity.

Usage: imported by all stage files and run_preflight.py
"""

import os
import sys
import json
import time
import datetime
import subprocess
import traceback

# ── Constants ─────────────────────────────────────────────────────
VERSION = "v1"
MERDIAN_ROOT_LOCAL = r"C:\GammaEnginePython"
MERDIAN_ROOT_AWS   = "/home/ssm-user/meridian-engine"

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"
WARN = "WARN"

# ── Environment Detection ──────────────────────────────────────────

def detect_environment():
    """Detect whether running on Local (Windows) or AWS (Linux)."""
    if sys.platform.startswith("win"):
        return "local"
    return "aws"

def get_merdian_root():
    env = detect_environment()
    if env == "local":
        return MERDIAN_ROOT_LOCAL
    return MERDIAN_ROOT_AWS

def get_env_file_path():
    return os.path.join(get_merdian_root(), ".env")

# ── .env Loading ──────────────────────────────────────────────────

def load_env(env_path=None):
    """
    Load .env file into os.environ.
    Returns (success, missing_keys).
    """
    if env_path is None:
        env_path = get_env_file_path()

    required_keys = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "DHAN_CLIENT_ID",
        "DHAN_API_TOKEN",
    ]

    if not os.path.exists(env_path):
        return False, f".env file not found at {env_path}", []

    loaded = {}
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ[key] = val
                    loaded[key] = val
    except Exception as e:
        return False, f"Failed to parse .env: {e}", []

    missing = [k for k in required_keys if not os.environ.get(k)]
    if missing:
        return False, f"Missing required keys: {missing}", missing

    return True, "OK", []

# ── Result Building ────────────────────────────────────────────────

def make_check(name, status, detail="", elapsed_ms=None):
    """Build a single check result dict."""
    r = {
        "name": name,
        "status": status,
        "detail": detail,
    }
    if elapsed_ms is not None:
        r["elapsed_ms"] = elapsed_ms
    return r

def make_stage_result(stage_id, environment, checks, started_at, finished_at=None):
    """Build a stage result dict."""
    if finished_at is None:
        finished_at = now_iso()

    passed  = sum(1 for c in checks if c["status"] == PASS)
    failed  = sum(1 for c in checks if c["status"] == FAIL)
    warned  = sum(1 for c in checks if c["status"] == WARN)
    skipped = sum(1 for c in checks if c["status"] == SKIP)

    overall = PASS if failed == 0 else FAIL

    return {
        "stage": stage_id,
        "environment": environment,
        "status": overall,
        "started_at": started_at,
        "finished_at": finished_at,
        "summary": {
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "skipped": skipped,
            "total": len(checks),
        },
        "checks": checks,
    }

# ── Time Helpers ───────────────────────────────────────────────────

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def now_ist_str():
    ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist_offset).strftime("%Y-%m-%d %H:%M:%S IST")

def elapsed_ms(start_time):
    return int((time.time() - start_time) * 1000)

# ── Output Helpers ─────────────────────────────────────────────────

def print_header(title):
    print()
    print("=" * 72)
    print(f"  {title}")
    print(f"  {now_ist_str()}")
    print("=" * 72)

def print_check(check):
    icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️ ", "SKIP": "⏭️ "}.get(check["status"], "❓")
    ms_str = f"  ({check.get('elapsed_ms', '')}ms)" if check.get("elapsed_ms") else ""
    print(f"  {icon} {check['name']}{ms_str}")
    if check["detail"] and check["status"] != PASS:
        print(f"       {check['detail']}")

def print_stage_summary(result):
    s = result["summary"]
    status_icon = "✅ PASS" if result["status"] == PASS else "❌ FAIL"
    print()
    print(f"  Stage {result['stage']}:  {status_icon}  "
          f"({s['passed']} passed, {s['failed']} failed, "
          f"{s['warned']} warned, {s['skipped']} skipped)")

# ── Report I/O ────────────────────────────────────────────────────

def get_output_dir():
    root = get_merdian_root()
    out = os.path.join(root, "preflight", "output")
    os.makedirs(out, exist_ok=True)
    return out

def save_stage_result(result):
    """Save stage result to preflight/output/latest_<stage>.json"""
    out_dir = get_output_dir()
    path = os.path.join(out_dir, f"latest_{result['stage']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

def save_final_report(report):
    """Save final orchestrator report."""
    out_dir = get_output_dir()
    # latest
    latest = os.path.join(out_dir, "latest_preflight_report.json")
    with open(latest, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    # history
    history = os.path.join(out_dir, "preflight_history.jsonl")
    with open(history, "a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")
    # human summary
    summary = os.path.join(out_dir, "latest_preflight_summary.txt")
    with open(summary, "w", encoding="utf-8") as f:
        f.write(build_summary_text(report))
    return latest

def build_summary_text(report):
    lines = [
        "MERDIAN PREFLIGHT SUMMARY",
        "=" * 50,
        f"Time:        {report.get('started_at_ist', '')}",
        f"Environment: {report.get('environment', '')}",
        f"Mode:        {report.get('mode', '')}",
        f"Overall:     {report.get('overall_status', '')}",
        f"Canary OK:   {'YES' if report.get('live_canary_allowed') else 'NO'}",
        "",
    ]
    for sr in report.get("stage_results", []):
        s = sr["summary"]
        icon = "✅" if sr["status"] == PASS else "❌"
        lines.append(f"  {icon} {sr['stage']:30s}  "
                     f"{s['passed']}P {s['failed']}F {s['warned']}W")
        for c in sr["checks"]:
            if c["status"] != PASS:
                ci = {"FAIL": "  ❌", "WARN": "  ⚠️ ", "SKIP": "  ⏭️ "}.get(c["status"], "  ?")
                lines.append(f"      {ci} {c['name']}: {c['detail']}")
    lines.append("")
    return "\n".join(lines)

# ── Telegram Alert ─────────────────────────────────────────────────

def send_telegram_alert(message, token=None, chat_id=None):
    """
    Send a Telegram alert. Reads TELEGRAM_BOT_TOKEN and
    TELEGRAM_CHAT_ID from environment if not provided.
    Returns (success, detail).
    """
    try:
        import urllib.request
        token   = token   or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return False, "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — alert not sent"

        url     = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
        req     = urllib.request.Request(url, data=payload,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return True, "Alert sent"
            return False, f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)

def alert_preflight_result(report):
    """Send Telegram alert with preflight outcome."""
    env    = report.get("environment", "unknown")
    status = report.get("overall_status", "UNKNOWN")
    mode   = report.get("mode", "")
    icon   = "✅" if status == PASS else "❌"
    failed = [sr["stage"] for sr in report.get("stage_results", [])
              if sr["status"] == FAIL]

    msg = f"{icon} MERDIAN PREFLIGHT {status}\n"
    msg += f"Env: {env}  Mode: {mode}\n"
    msg += f"Time: {report.get('started_at_ist', '')}\n"
    if failed:
        msg += f"Failed stages: {', '.join(failed)}\n"
    if not report.get("live_canary_allowed"):
        msg += "⛔ Live canary NOT allowed\n"
    else:
        msg += "🟢 Live canary allowed\n"

    send_telegram_alert(msg)

# ── Git Helpers ────────────────────────────────────────────────────

def get_git_hash():
    """Get current Git commit hash. Returns (hash, error)."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            capture_output=True, text=True,
            cwd=get_merdian_root(), timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip(), None
        return None, result.stderr.strip()
    except Exception as e:
        return None, str(e)

# ── Safe Runner ────────────────────────────────────────────────────

def run_check(name, fn):
    """
    Run a single check function safely.
    fn must return (status, detail) tuple.
    Returns a check dict.
    """
    t0 = time.time()
    try:
        status, detail = fn()
        return make_check(name, status, detail, elapsed_ms(t0))
    except Exception as e:
        tb = traceback.format_exc()
        return make_check(name, FAIL, f"Exception: {e}\n{tb}", elapsed_ms(t0))
