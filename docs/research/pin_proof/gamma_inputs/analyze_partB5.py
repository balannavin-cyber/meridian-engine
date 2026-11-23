#!/usr/bin/env python3
"""Aggregate the B5 day-existence probes.

Input  : _partB5_raw.txt -- "MONTH|sym|cal_day|has_rows|first_bar_ts|trade_date|bar_clock_date"
         (the probe emits unaligned, tuples-only rows; day ordering is done here because
         the outer ORDER BY was removed to satisfy the plan condition "no Sort node")
Output : stdout. No database access, no writes to tracked files.

Cross-check column comes from hist_greeks_backfill_log (_q01.txt), which is the WRITER'S
log, not the table's contents -- a disagreement is the finding, not an error to smooth.
"""
import sys
from collections import defaultdict

RAW = sys.argv[1] if len(sys.argv) > 1 else "_partB5_raw.txt"

# DONE days per month with rows_written > 0, from _q01.txt (q01 FIRSTDAY).
LOG = {
    "NIFTY":  {"2025-04": 14, "2025-05": 17, "2025-06": 17, "2025-07": 18,
               "2025-08": 15, "2025-09": 17, "2025-10": 17, "2025-11": 15,
               "2025-12": 17, "2026-01": 16, "2026-02": 17, "2026-03": 14},
    "SENSEX": {"2025-04": 13, "2025-05": 17, "2025-06": 16, "2025-07": 18,
               "2025-08": 15, "2025-09": 18, "2025-10": 16, "2025-11": 15,
               "2025-12": 18, "2026-01": 15, "2026-02": 17, "2026-03": 15},
}

days = defaultdict(list)
mismatch = []
with open(RAW) as fh:
    for line in fh:
        line = line.rstrip("\n")
        if not line:
            continue
        p = line.split("|")
        if len(p) < 7:
            continue
        month, sym, cal_day, has_rows, first_bar_ts, trade_date, bar_clock_date = p[:7]
        hr = has_rows.strip() == "t"
        days[(sym, month)].append((cal_day, hr, first_bar_ts, trade_date, bar_clock_date))
        # the whole point of returning both: a disagreement must surface, not hide
        if hr and trade_date.strip() and bar_clock_date.strip() \
           and trade_date.strip() != bar_clock_date.strip():
            mismatch.append((sym, cal_day, trade_date, bar_clock_date))

print("### B5 distinct trading days per month with a front-expiry greeks row")
print("# measured by day-existence probe (one row read per calendar day), NOT by aggregate")
print("sym|month|cal_days|days_with_rows|log_DONE_days|agrees_with_log")
tot = defaultdict(int)
for sym in ("NIFTY", "SENSEX"):
    for month in sorted(m for (s, m) in days if s == sym):
        v = sorted(days[(sym, month)])
        n = sum(1 for d in v if d[1])
        lg = LOG.get(sym, {}).get(month)
        tot[sym] += n
        agree = "YES" if lg == n else f"NO (log {lg}, probe {n})"
        print(f"{sym}|{month}|{len(v)}|{n}|{lg if lg is not None else 'n/a'}|{agree}")
    print(f"# {sym}: {tot[sym]} days with rows across the window")

print()
print("### trade_date vs bar_ts clock date, on the first row of each day with rows")
if not mismatch:
    print("# 0 disagreements -- the stored trade_date equals the clock date of bar_ts on")
    print("# every probed row, so the TD-029-family labelling holds for this store and the")
    print("# two columns are interchangeable for day identity in this window.")
else:
    print("sym|cal_day|trade_date|bar_clock_date")
    for m in mismatch:
        print("|".join(m))
    print(f"# {len(mismatch)} disagreements -- day identity is NOT interchangeable; "
          f"every B5 day count above is ambiguous until this is resolved.")

print()
print("### month-count differences between probe and writer's log "
      "(counts only; offsetting day differences would cancel)")
print("sym|month|probe|log|delta")
any_delta = False
for sym in ("NIFTY", "SENSEX"):
    for month in sorted(m for (s, m) in days if s == sym):
        n = sum(1 for d in sorted(days[(sym, month)]) if d[1])
        lg = LOG.get(sym, {}).get(month)
        if lg is not None and lg != n:
            any_delta = True
            print(f"{sym}|{month}|{n}|{lg}|{n - lg:+d}")
if not any_delta:
    print("# none -- probe and writer's log agree on every month, both symbols")
