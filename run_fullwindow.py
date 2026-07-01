from __future__ import annotations

"""
run_fullwindow.py  --  observable orchestration for the step-4 full-window backfill.

Runs, per (symbol, month): backfill_hist_greeks.py --apply  THEN
fill_gamma_concentration.py --apply. Each day-line is timestamped so a stall is
visible (no new line for minutes = stuck). All output tees to a logfile. Any
non-zero subprocess exit aborts LOUDLY with the failing command. Resumable:
both underlying scripts skip already-DONE work, so a re-run continues.

  python3 run_fullwindow.py --symbol NIFTY
  python3 run_fullwindow.py --symbol SENSEX
  python3 run_fullwindow.py --symbol NIFTY --months 2025-04,2025-05   # subset

Default month set = the raw-bar window minus the already-done NIFTY Sep-Dec.
Adjust --from-month/--to-month as the raw-bar coverage dictates.
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime, date
from calendar import monthrange

LOGFILE = "fullwindow_backfill.log"


def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def month_bounds(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    last = monthrange(y, m)[1]
    return f"{ym}-01", f"{ym}-{last:02d}"


def all_months(from_month, to_month):
    out = []
    y, m = int(from_month[:4]), int(from_month[5:7])
    ey, em = int(to_month[:4]), int(to_month[5:7])
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1; y += 1
    return out


def run_cmd(label, args):
    """Run a subprocess, streaming each stdout line with a timestamp prefix.
    Aborts loudly (sys.exit) on non-zero return."""
    log(f">>> {label}: {' '.join(args)}")
    t0 = time.time()
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    last_line = time.time()
    for line in proc.stdout:
        line = line.rstrip("\n")
        if line.strip():
            log(f"    {line}")
            last_line = time.time()
    proc.wait()
    dt = time.time() - t0
    if proc.returncode != 0:
        log(f"!!! ABORT: {label} exited {proc.returncode} after {dt:.0f}s. "
            f"Resume by re-running the same command (DONE work is skipped).")
        sys.exit(proc.returncode)
    log(f"<<< {label} done in {dt:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="NIFTY")
    ap.add_argument("--from-month", default="2025-04")
    ap.add_argument("--to-month", default="2026-05")
    ap.add_argument("--months", help="comma list, overrides from/to (e.g. 2025-04,2025-05)")
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()

    months = (args.months.split(",") if args.months
              else all_months(args.from_month, args.to_month))
    log("=" * 64)
    log(f"FULL-WINDOW backfill start  symbol={args.symbol}  months={len(months)} "
        f"({months[0]}..{months[-1]})  log={LOGFILE}")
    log("=" * 64)

    t_start = time.time()
    for i, ym in enumerate(months, 1):
        d_from, d_to = month_bounds(ym)
        log(f"--- [{i}/{len(months)}] {args.symbol} {ym}  ({d_from}..{d_to}) ---")
        run_cmd(f"solve {args.symbol} {ym}",
                [args.python, "backfill_hist_greeks.py", "--symbol", args.symbol,
                 "--from", d_from, "--to", d_to, "--apply"])
        run_cmd(f"fill  {args.symbol} {ym}",
                [args.python, "fill_gamma_concentration.py", "--symbol", args.symbol,
                 "--from", d_from, "--to", d_to, "--apply"])
        elapsed = time.time() - t_start
        log(f"=== {ym} complete. elapsed {elapsed/60:.1f} min, "
            f"{i}/{len(months)} months done ===")

    log("=" * 64)
    log(f"ALL DONE  symbol={args.symbol}  total {(time.time()-t_start)/60:.1f} min")
    log("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
