"""
batch_backfill_volatility.py

Runs backfill_volatility_metrics.py across all historical dates.
Skips dates already present in hist_volatility_snapshots.

Usage:
    python batch_backfill_volatility.py
    python batch_backfill_volatility.py 2025-10-01 2025-12-31
    python batch_backfill_volatility.py 2025-10-01 2025-12-31 NIFTY
"""
from __future__ import annotations
import os, subprocess, sys
from datetime import date, timedelta
from pathlib import Path
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "logs" / "batch_backfill_volatility.log"

load_dotenv(dotenv_path=BASE_DIR / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

KNOWN_RANGES = {
    "NIFTY":  ("2025-04-01", "2026-03-30"),
    "SENSEX": ("2025-04-01", "2026-03-30"),
}

def log(msg):
    from datetime import datetime, timezone, timedelta as td
    IST = timezone(td(hours=5, minutes=30))
    ts = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def sb_get(path, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{path}{'?' + params if params else ''}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"GET {path} failed {r.status_code}: {r.text[:200]}")
    return r.json()

def get_weekdays(start, end):
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates

def get_done(symbol):
    rows = sb_get("hist_volatility_snapshots", f"symbol=eq.{symbol}&select=trade_date&limit=5000")
    return {r["trade_date"] for r in rows}

def run_one(trade_date, symbol):
    cmd = [sys.executable, str(BASE_DIR / "backfill_volatility_metrics.py"), trade_date, symbol]
    try:
        result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=180)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT after 180s"
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    upserted = None
    for line in stdout.splitlines():
        if "Upserted:" in line:
            try: upserted = int(line.split(":")[1].strip().split()[0])
            except: pass
    if result.returncode == 0:
        return True, f"rc=0 upserted={upserted}"
    all_lines = [l for l in (stdout+stderr).splitlines() if l.strip()]
    last = all_lines[-1][:120] if all_lines else "no output"
    return False, f"rc={result.returncode} | {last}"

def main():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    symbols = ["NIFTY", "SENSEX"]
    start_filter = end_filter = None
    for arg in sys.argv[1:]:
        if arg.upper() in ("NIFTY", "SENSEX"):
            symbols = [arg.upper()]
        elif len(arg)==10 and arg[4]=="-" and start_filter is None:
            start_filter = arg
        elif len(arg)==10 and arg[4]=="-" and end_filter is None:
            end_filter = arg

    log("="*72)
    log("BATCH BACKFILL VOLATILITY METRICS")
    log(f"Symbols: {symbols} | Filter: {start_filter or 'all'} to {end_filter or 'all'}")
    log("="*72)

    work_items = []
    for symbol in symbols:
        ks, ke = KNOWN_RANGES[symbol]
        eff_start = date.fromisoformat(max(ks, start_filter) if start_filter else ks)
        eff_end = date.fromisoformat(min(ke, end_filter) if end_filter else ke)
        all_dates = get_weekdays(eff_start, eff_end)
        log(f"Fetching done dates for {symbol}...")
        done = get_done(symbol)
        todo = [(d, symbol) for d in all_dates if d not in done]
        log(f"{symbol}: {len(all_dates)} weekdays | {len(done)} done | {len(todo)} to process")
        work_items.extend(todo)

    work_items.sort(key=lambda x: (x[0], x[1]))
    log(f"Total to process: {len(work_items)}")
    log("="*72)

    if not work_items:
        log("Nothing to do."); return 0

    passed, failed = [], []
    for i, (trade_date, symbol) in enumerate(work_items, 1):
        log(f"[{i}/{len(work_items)}] {trade_date} {symbol}")
        success, summary = run_one(trade_date, symbol)
        if success:
            passed.append((trade_date, symbol))
            log(f"  PASS — {summary}")
        else:
            failed.append((trade_date, symbol))
            log(f"  FAIL — {summary}")

    log("="*72)
    log(f"COMPLETE — Passed: {len(passed)} | Failed: {len(failed)}")
    if failed:
        for d,s in failed: log(f"  FAIL: {d} {s}")
    log("="*72)
    return 0 if not failed else 1

if __name__=="__main__":
    raise SystemExit(main())
