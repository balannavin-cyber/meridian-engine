"""
batch_reconstruct_signals.py

Runs reconstruct_shadow_for_date_local_v3.py across expiry-aligned windows.

Expiry rules:
  Post 2025-09-01:  NIFTY expires Tuesday,  SENSEX expires Thursday
  Pre  2025-09-01:  NIFTY expires Thursday, SENSEX expires Tuesday

Each instrument is reconstructed across complete expiry weeks only:
  NIFTY (post-Sep):  window = Wednesday open -> Tuesday close
  SENSEX (post-Sep): window = Friday open    -> Thursday close
  NIFTY (pre-Sep):   window = Friday open    -> Thursday close
  SENSEX (pre-Sep):  window = Wednesday open -> Tuesday close

Usage:
    python batch_reconstruct_signals.py 2025-10-01 2026-03-30
"""
from __future__ import annotations
import os, subprocess, sys
from datetime import date, timedelta
from pathlib import Path
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
LOG_PATH = BASE_DIR / "logs" / "batch_reconstruct.log"

EXPIRY_CHANGE_DATE = date(2025, 9, 1)
POST_SEP_NIFTY_EXPIRY  = 1  # Tuesday
POST_SEP_SENSEX_EXPIRY = 3  # Thursday
PRE_SEP_NIFTY_EXPIRY   = 3  # Thursday
PRE_SEP_SENSEX_EXPIRY  = 1  # Tuesday

load_dotenv(dotenv_path=ENV_PATH)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()


def log(msg):
    from datetime import datetime, timezone, timedelta as td
    IST = timezone(td(hours=5, minutes=30))
    ts = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_already_done():
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    url = f"{SUPABASE_URL}/rest/v1/shadow_reconstruction_v3?select=reconstruction_date,symbol&limit=5000"
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch done dates: {resp.status_code} {resp.text}")
    return {(r["reconstruction_date"][:10], r["symbol"]) for r in resp.json()}


def expiry_weekday(d, symbol):
    if d >= EXPIRY_CHANGE_DATE:
        return POST_SEP_NIFTY_EXPIRY if symbol == "NIFTY" else POST_SEP_SENSEX_EXPIRY
    return PRE_SEP_NIFTY_EXPIRY if symbol == "NIFTY" else PRE_SEP_SENSEX_EXPIRY


def generate_aligned_dates(start, end, symbol):
    """Generate trading dates within complete expiry-aligned windows."""
    dates = []
    current = start
    while current <= end:
        exp_wd = expiry_weekday(current, symbol)
        win_start_wd = (exp_wd + 1) % 7
        days_since = (current.weekday() - win_start_wd) % 7
        win_start = current - timedelta(days=days_since)
        days_to_exp = (exp_wd - win_start.weekday()) % 7
        if days_to_exp == 0:
            days_to_exp = 7
        win_end = win_start + timedelta(days=days_to_exp)
        # Only include complete windows fully within range
        if win_start >= start and win_end <= end:
            d = win_start
            while d <= win_end:
                if d.weekday() < 5:
                    dates.append(d.isoformat())
                d += timedelta(days=1)
        current = win_end + timedelta(days=1)
    return sorted(set(dates))


def run_reconstruct(date_str, symbol):
    cmd = [sys.executable, str(BASE_DIR / "reconstruct_shadow_for_date_local_v3.py"), date_str]
    try:
        result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=120)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT after 120s"
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    inserted = None
    for line in stdout.splitlines():
        if "Inserted rows returned by Supabase:" in line:
            try:
                inserted = int(line.split(":")[-1].strip())
            except ValueError:
                pass
    if result.returncode == 0:
        return True, f"rc=0 inserted={inserted}"
    all_lines = [l for l in (stdout + stderr).splitlines() if l.strip()]
    last = all_lines[-1][:120] if all_lines else "no output"
    return False, f"rc={result.returncode} | {last}"


def main():
    if len(sys.argv) != 3:
        print("Usage: python batch_reconstruct_signals.py YYYY-MM-DD YYYY-MM-DD")
        return 1
    try:
        start = date.fromisoformat(sys.argv[1])
        end = date.fromisoformat(sys.argv[2])
    except ValueError as e:
        print(f"Invalid date: {e}"); return 1
    if start > end:
        print("Start must be before end"); return 1

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log("=" * 72)
    log("BATCH RECONSTRUCT SIGNALS — EXPIRY ALIGNED")
    log(f"Range: {start} to {end}")
    log("=" * 72)

    already_done = get_already_done()
    log(f"Already done: {len(already_done)} (date,symbol) pairs")

    work_items = []
    for symbol in ["NIFTY", "SENSEX"]:
        aligned = generate_aligned_dates(start, end, symbol)
        todo = [(d, symbol) for d in aligned if (d, symbol) not in already_done]
        log(f"{symbol}: {len(aligned)} aligned dates | {len(aligned)-len(todo)} skipped | {len(todo)} to do")
        work_items.extend(todo)

    work_items.sort(key=lambda x: (x[0], x[1]))
    log(f"Total to reconstruct: {len(work_items)}")
    log("=" * 72)

    if not work_items:
        log("Nothing to do."); return 0

    passed, failed = [], []
    for i, (date_str, symbol) in enumerate(work_items, 1):
        log(f"[{i}/{len(work_items)}] {date_str} {symbol}")
        success, summary = run_reconstruct(date_str, symbol)
        if success:
            passed.append((date_str, symbol))
            log(f"  PASS — {summary}")
        else:
            failed.append((date_str, symbol))
            log(f"  FAIL — {summary}")

    log("=" * 72)
    log(f"COMPLETE — Passed: {len(passed)} | Failed: {len(failed)}")
    if failed:
        for d, s in failed:
            log(f"  FAIL: {d} {s}")
    log("=" * 72)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
