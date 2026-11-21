"""Part 0 step 3: futures expiry days.

hist_future_bars_1m.expiry_date is NULL on all 260,126 NIFTY rows (measured,
Part 0 step 2), so these are inferred from the OI ladder, except the last
session, which the rule cannot decide and which is operator-supplied.
Every decision is printed with the margin that produced it.
"""
import calendar
import csv
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import futoi_lib as L

fut = L.load_futures()
sessions = sorted(fut.keys())
rows = L.detect_futures_expiries(fut, sessions)
expiries, prov = L.futures_expiry_dates(fut, sessions)

with open(os.path.join(L.DATA, "futures_expiries.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=[
        "date", "next", "decidable", "rolled", "ladder_only", "reason", "argmin",
        "margin_ratio", "corroborated", "oi_s1_d", "oi_s2_d", "oi_s3_d",
        "oi_s1_next", "oi_s2_next"])
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k) for k in w.fieldnames})

rolled = [r for r in rows if r["rolled"]]
undec = [r for r in rows if not r["decidable"]]
lad = [r for r in rows if r.get("ladder_only")]

print("futures sessions in window:               %d" % len(sessions))
print("session pairs the ladder could decide:    %d of %d" % (len(rows) - len(undec), len(rows)))
print("undecidable (missing series at close):    %d" % len(undec))
print("last session (%s) has no d+1 -> the ladder cannot decide it" % sessions[-1])
print()
print("--- clause (a) ladder-argmin ALONE, kept for audit ---")
la_m = [r["margin_ratio"] for r in lad if r["margin_ratio"]]
no_m = [r["margin_ratio"] for r in rows if r["decidable"] and not r.get("ladder_only") and r["margin_ratio"]]
print("fires on:                                 %d session pairs" % len(lad))
if la_m and no_m:
    print("weakest FIRING margin:                    %.2fx" % min(la_m))
    print("strongest NON-FIRING margin:              %.2fx" % max(no_m))
    print("separation:                               %s"
          % ("NONE -- clause (a) alone is a coin toss at the boundary"
             if min(la_m) <= max(no_m) else "clean"))
fp = [r["margin_ratio"] for r in lad if not r["rolled"] and r["margin_ratio"]]
mins = [r["margin_ratio"] for r in rolled if r["margin_ratio"]]
print()
print("--- clause (a) AND (b), the rule applied ---")
print("fires on:                                 %d session pairs" % len(rolled))
if mins:
    print("weakest margin among them:                %.2fx" % min(mins))
if fp:
    print("strongest margin among (a)-only rows:     %.2fx" % max(fp))
print()
print("%-12s %-12s %12s %12s %12s %12s  %8s  %s" % (
    "expiry", "next sess", "OI_s1(d)", "OI_s2(d)", "OI_s3(d)", "OI_s1(d+1)", "margin", "corrob"))
for r in rolled:
    print("%-12s %-12s %12.0f %12.0f %12s %12.0f  %8s  %s" % (
        r["date"], r["next"], r["oi_s1_d"], r["oi_s2_d"],
        ("%.0f" % r["oi_s3_d"]) if r["oi_s3_d"] is not None else "-",
        r["oi_s1_next"], ("%.2fx" % r["margin_ratio"]) if r["margin_ratio"] else "inf",
        r["corroborated"]))

print()
print("=== FINAL futures expiry list (section 2 exclusions, M1 eligibility) ===")
print("%-12s  %-9s  %s" % ("date", "weekday", "provenance"))
bym = {}
for d in expiries:
    wd = calendar.day_name[dt.date.fromisoformat(d).weekday()]
    print("%-12s  %-9s  %s" % (d, wd, prov[d]))
    bym.setdefault(d[:7], []).append(d)
print()
months = ["2025-%02d" % m for m in range(4, 13)] + ["2026-%02d" % m for m in range(1, 4)]
ok_count = len(expiries) == 12
ok_months = all(len(bym.get(m, [])) == 1 for m in months) and set(bym) == set(months)
print("count == 12:                              %s (measured %d)" % (ok_count, len(expiries)))
print("exactly one per month 2025-04..2026-03:   %s" % ok_months)
for m in months:
    got = bym.get(m, [])
    if len(got) != 1:
        print("   MONTH OFF: %s -> %r" % (m, got))
if not (ok_count and ok_months):
    print()
    print("STOP: the futures expiry list does not meet the stated expectation.")
    sys.exit(3)
print()
print("CHECK PASSED -- 12 futures expiries, exactly one per calendar month.")
with open(os.path.join(L.DATA, "futures_expiry_list.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["date", "weekday", "provenance"])
    for d in expiries:
        w.writerow([d, calendar.day_name[dt.date.fromisoformat(d).weekday()], prov[d]])
