#!/usr/bin/env python3
"""Apply the FUTURES CONTRACT RULE (BLOCKED.txt, fixed 2026-11-20) to _partH_raw.txt.

READ-ONLY, NO DATABASE ACCESS. Reads only _partH_raw.txt.

The rule, as recorded BEFORE any Fyers price was used:
  F        -- close of the Fyers bar at the EXACT true-UTC instant (reading 'UTC',
              off_sec 0). NO neighbour fill.
  CONTRACT -- among contracts holding a bar at that instant, the one with the smallest
              expiry_date >= the IST trade date. By measured expiry_date, never by
              contract_series.
  MISSING  -- no bar at that instant: F missing, minute EXCLUDED and COUNTED.
  UNSTABLE -- fut_dte < 3: flagged, EXCLUDED and COUNTED.
  NEXT CONTRACT USED -- the contract used is not the nearest-expiry contract seen in the
              UTC-reading windows at the three sampled minutes: COUNTED, NOT excluded.
  VOLUME   -- reported alongside F; a zero-volume bar is FLAGGED.

Reports counts and the per-minute table only. Computes NO r, states no conclusion, and
uses no Fyers price in any sensitivity.
"""
import json
import sys
from collections import defaultdict

RAW = sys.argv[1] if len(sys.argv) > 1 else "_partH_raw.txt"
MINUTES = ("10:00", "12:30", "15:00")

# Day sets are FIXED HERE, not derived from the data, so a day absent from the raw file
# is still expected, printed and counted rather than silently vanishing.
DAYS = {
    "NIFTY": ["2025-04-01", "2025-05-02", "2025-06-02", "2025-07-01", "2025-08-01",
              "2025-09-01", "2025-10-01", "2025-11-03", "2025-12-01", "2026-01-01",
              "2026-02-01", "2026-03-04"],
    "SENSEX": ["2025-04-02", "2025-05-02", "2025-06-02", "2025-07-02", "2025-08-01",
               "2025-09-01", "2025-10-03", "2025-11-03", "2025-12-01", "2026-01-02",
               "2026-02-01", "2026-03-02"],
}
EXPECTED_PER_SYMBOL = len(MINUTES) * 12          # 36
EXPECTED_TOTAL = EXPECTED_PER_SYMBOL * 2         # 72

# ---- (1) the exact parameters this run is using ----
print("### Parameters in force for this run")
for sym in ("NIFTY", "SENSEX"):
    print(f"DAYS[{sym}] ({len(DAYS[sym])}): {' '.join(DAYS[sym])}")
print(f"MINUTES ({len(MINUTES)}): {' '.join(MINUTES)}")
print(f"EXPECTED_PER_SYMBOL: {EXPECTED_PER_SYMBOL}")
print(f"EXPECTED_TOTAL: {EXPECTED_TOTAL}")
print(f"RAW: {RAW}")
print()

h1_all = []          # every H1 row, unfiltered, for the tname/reading diagnostics
h3_seen = set()      # (sym, day) that produced an H3 line
with open(RAW) as fh:
    for line in fh:
        line = line.rstrip("\n")
        if not line:
            continue
        sym, day, tag, payload = line.split("|", 3)
        d = json.loads(payload)
        if tag == "H1":
            h1_all.append((sym, day, d))
        elif tag == "H3":
            h3_seen.add((sym, day))

# ---- (2a) expected symbol-days with no H3 line ----
print("### Expected SYM|DATE with no H3 line in the raw file")
missing_h3 = [(s, d) for s in ("NIFTY", "SENSEX") for d in DAYS[s]
              if (s, d) not in h3_seen]
if not missing_h3:
    print("# none -- every expected symbol-day produced an H3 line")
else:
    for s, d in missing_h3:
        print(f"{s}|{d}")
print(f"# expected symbol-days: {len(DAYS['NIFTY']) + len(DAYS['SENSEX'])}, "
      f"with an H3 line: {len(h3_seen)}, without: {len(missing_h3)}")

# ---- (2b) distinct tname and reading values found in H1 ----
tnames = sorted({d["tname"] for _, _, d in h1_all})
readings = sorted({d["reading"] for _, _, d in h1_all})
print()
print("### Distinct values found in H1")
print(f"tname   : {{{', '.join(tnames)}}}")
print(f"reading : {{{', '.join(readings)}}}")
if set(tnames) != set(MINUTES):
    print(f"# ABORT: tname set {{{', '.join(tnames)}}} is not exactly "
          f"{{{', '.join(MINUTES)}}}; no table printed.")
    sys.exit(2)

# UTC-reading rows only, indexed by (sym, day, minute)
h1 = defaultdict(list)
for sym, day, d in h1_all:
    if d["reading"] == "UTC":
        h1[(sym, day, d["tname"])].append(d)

# Nearest expiry seen IN THE UTC-READING WINDOWS AT THE THREE SAMPLED MINUTES, ANY
# OFFSET. This is not "anywhere on the day": nothing outside those windows was read, so
# a nearer contract trading only at other times is invisible here and
# NEXT_CONTRACT_USED can under-report.
day_nearest = {}
for (sym, day, minute), rows in h1.items():
    for r in rows:
        e = r.get("expiry_date")
        if e is None or e < day:
            continue
        k = (sym, day)
        if k not in day_nearest or e < day_nearest[k]:
            day_nearest[k] = e

print()
print("### Per-minute application of the FUTURES CONTRACT RULE")
print("# nearest-expiry reference = nearest expiry seen in the UTC-reading windows at")
print("# the three sampled minutes, any offset -- NOT anywhere on the day.")
print("# A TIED minute prints EVERY tied row and its F is NOT used.")
print("sym|day|minute|F_at_offset0|contract|expiry|fut_dte|close|volume|flags")
counts = defaultdict(lambda: defaultdict(int))
for sym in ("NIFTY", "SENSEX"):
    for day in DAYS[sym]:
        for minute in MINUTES:
            rows = h1.get((sym, day, minute), [])
            at0 = [r for r in rows
                   if float(r["off_sec"]) == 0.0
                   and r.get("expiry_date") is not None
                   and r["expiry_date"] >= day]
            counts[sym]["minutes"] += 1
            if not at0:
                counts[sym]["f_missing"] += 1
                # (3) DIAGNOSTIC, set ONLY when a row in the window sits at a non-zero
                # offset. A window holding only offset-0 rows that failed the expiry
                # test is plain MISSING. Fills nothing, changes no exclusion.
                if any(float(r["off_sec"]) != 0.0 for r in rows):
                    counts[sym]["missing_but_bar_off0"] += 1
                    print(f"{sym}|{day}|{minute}|MISSING|-|-|-|-|-|"
                          f"EXCLUDED_F_MISSING,DIAG_BAR_AT_NONZERO_OFFSET")
                else:
                    print(f"{sym}|{day}|{minute}|MISSING|-|-|-|-|-|EXCLUDED_F_MISSING")
                continue
            chosen_expiry = min(r["expiry_date"] for r in at0)
            tied = [r for r in at0 if r["expiry_date"] == chosen_expiry]
            counts[sym]["f_available"] += 1
            # Minute-level flags, counted ONCE per minute, from the chosen expiry.
            minute_flags = []
            nearest = day_nearest.get((sym, day))
            if nearest is not None and chosen_expiry != nearest:
                minute_flags.append("NEXT_CONTRACT_USED")
                counts[sym]["next_contract_used"] += 1
            fut_dte = tied[0].get("fut_dte")
            is_unstable = fut_dte is not None and int(fut_dte) < 3
            if is_unstable:
                minute_flags.append("EXCLUDED_UNSTABLE")
                counts[sym]["excluded_unstable"] += 1
            if any(r.get("volume") is not None and int(r["volume"]) == 0 for r in tied):
                counts[sym]["zero_volume"] += 1
            if len(tied) > 1:
                counts[sym]["tie"] += 1
                # A tied minute that is ALSO unstable is already removed by the unstable
                # exclusion. Subtracting the full tie count from the survivors would
                # remove it a second time, so the tie count is split and only
                # tie_not_unstable is used in the arithmetic.
                # Invariant: tie = tie_not_unstable + tied_and_unstable.
                if is_unstable:
                    counts[sym]["tied_and_unstable"] += 1
                else:
                    counts[sym]["tie_not_unstable"] += 1
            # (2) print EVERY tied row; for a tie, no single row is taken as F.
            for r in sorted(tied, key=lambda x: x["symbol"]):
                flags = list(minute_flags)
                if len(tied) > 1:
                    flags.append(f"TIE({len(tied)})")
                    flags.append("F_NOT_USED")
                if r.get("volume") is not None and int(r["volume"]) == 0:
                    flags.append("ZERO_VOLUME")
                print(f"{sym}|{day}|{minute}|present|{r['symbol']}|{chosen_expiry}|"
                      f"{r.get('fut_dte')}|{r['close']}|{r.get('volume')}|"
                      f"{','.join(flags) if flags else '-'}")

print()
print("### Counts per symbol and in total")
print("metric|NIFTY|SENSEX|TOTAL")
keys = [
    ("minutes", "minutes examined"),
    ("f_available", "F available at offset 0"),
    ("f_missing", "F missing (EXCLUDED)"),
    ("excluded_unstable", "excluded as unstable, fut_dte < 3"),
    ("next_contract_used", "next contract used (counted, NOT excluded)"),
    ("zero_volume", "minutes with a zero-volume bar at the chosen expiry (flagged)"),
    ("tie", "TIE: >1 row at offset 0 with the chosen expiry (F not used)"),
    ("tied_and_unstable", "  of which also unstable (already excluded as unstable)"),
    ("tie_not_unstable", "  of which not unstable (the figure subtracted below)"),
    ("missing_but_bar_off0",
     "DIAGNOSTIC: F-missing minutes with a bar at a NON-ZERO offset (fills nothing)"),
]
for k, label in keys:
    n, s = counts["NIFTY"][k], counts["SENSEX"][k]
    print(f"{label}|{n}|{s}|{n + s}")

print()
print("### Reconcile: tie = tie_not_unstable + tied_and_unstable")
print("scope|tie|tie_not_unstable|tied_and_unstable|result")
rt = rtn = rtu = 0
for sym in ("NIFTY", "SENSEX"):
    t, tn, tu = (counts[sym]["tie"], counts[sym]["tie_not_unstable"],
                 counts[sym]["tied_and_unstable"])
    rt += t; rtn += tn; rtu += tu
    print(f"{sym}|{t}|{tn}|{tu}|{'OK' if t == tn + tu else 'MISMATCH'}")
print(f"TOTAL|{rt}|{rtn}|{rtu}|{'OK' if rt == rtn + rtu else 'MISMATCH'}")

print()
print("### Expected-count check")
for sym in ("NIFTY", "SENSEX"):
    got = counts[sym]["minutes"]
    print(f"{sym}|minutes examined {got}|expected {EXPECTED_PER_SYMBOL}|"
          f"{'OK' if got == EXPECTED_PER_SYMBOL else 'MISMATCH'}")
tot = counts["NIFTY"]["minutes"] + counts["SENSEX"]["minutes"]
print(f"TOTAL|minutes examined {tot}|expected {EXPECTED_TOTAL}|"
      f"{'OK' if tot == EXPECTED_TOTAL else 'MISMATCH'}")

print()
print("### Minutes surviving the rule's exclusions")
print("# Two lines per symbol. A COUNT ONLY: no r is computed and no pass criterion is")
print("# applied. surviving = F available minus excluded-as-unstable.")
print("# surviving_ex_ties additionally removes TIED minutes that are NOT already")
print("# excluded as unstable, so no minute is subtracted twice.")
print("scope|surviving|surviving_ex_ties|of_minutes")
for sym in ("NIFTY", "SENSEX"):
    surv = counts[sym]["f_available"] - counts[sym]["excluded_unstable"]
    # tie_not_unstable, NOT tie: a tied-and-unstable minute is already gone.
    surv_nt = surv - counts[sym]["tie_not_unstable"]
    print(f"{sym}|{surv}|{surv_nt}|{counts[sym]['minutes']}")
tot_s = sum(counts[s]["f_available"] - counts[s]["excluded_unstable"]
            for s in ("NIFTY", "SENSEX"))
tot_snt = tot_s - sum(counts[s]["tie_not_unstable"] for s in ("NIFTY", "SENSEX"))
print(f"TOTAL|{tot_s}|{tot_snt}|{tot}")
