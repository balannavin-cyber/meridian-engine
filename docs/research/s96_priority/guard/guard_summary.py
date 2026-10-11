#!/usr/bin/env python3
"""S96 / TD-S95-NEW-1 (c) survey summary. Reads ~/guard_out/*.csv (guard_run.sh). No database. Decides nothing.

Per symbol-session: the share of front DEX gross (and of OI) on suspect legs, by signature, across the day.
  S1 = volume 0 so far on a leg with OI;  S2 = S1 and oi_change = oi (OI appeared with no trade).
Prints one line per symbol-session, the three TD-S95-NEW-1 days marked '*', then per symbol the separation
between the marked days and the rest at every time bucket.
Run: python3 -I guard_summary.py [OUT]
"""
import csv, os, sys
from collections import defaultdict
from statistics import median

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/guard_out')
MARKED = {('SENSEX', '2026-09-25'), ('SENSEX', '2026-09-28'), ('SENSEX', '2026-09-29')}
BUCKETS = (('early', '09:15:00', '10:00:00'), ('mid', '10:00:00', '14:30:00'), ('late', '14:30:00', '15:15:01'))


def share(a, b):
    a, b = float(a or 0), float(b or 0)
    return a / b if b > 0 else None


def bucket(t):
    for n, lo, hi in BUCKETS:
        if lo <= t < hi:
            return n


rows = defaultdict(list)
for fn in sorted(os.listdir(OUT)):
    if not fn.endswith('.csv'):
        continue
    with open(os.path.join(OUT, fn), newline='') as f:
        for r in csv.DictReader(f):
            rows[(r['symbol'], r['session_date'])].append(r)

fmt = lambda v: '   -  ' if v is None else f'{100 * v:6.2f}'
print('sym     session     dte cyc  vol_null | S1 gross% min/med/max     | S2 gross% min/med/max     | S2 oi% max | S2 legs max')
sep = defaultdict(lambda: defaultdict(lambda: {'m': [], 'u': []}))
for (sym, d), rs in sorted(rows.items()):
    rs.sort(key=lambda r: r['cycle_ist'])
    s1 = [share(r['gross_s1'], r['gross_all']) for r in rs]
    s2 = [share(r['gross_s2'], r['gross_all']) for r in rs]
    s2o = [share(r['oi_s2'], r['oi_all']) for r in rs]
    v1 = [x for x in s1 if x is not None]
    v2 = [x for x in s2 if x is not None]
    v2o = [x for x in s2o if x is not None]
    mark = '*' if (sym, d) in MARKED else ' '
    print(f'{sym:7} {d}{mark} {rs[0]["dte"]:>3} {len(rs):3}  {max(int(r["n_vol_null"]) for r in rs):6}  | '
          f'{fmt(min(v1) if v1 else None)} {fmt(median(v1) if v1 else None)} {fmt(max(v1) if v1 else None)} | '
          f'{fmt(min(v2) if v2 else None)} {fmt(median(v2) if v2 else None)} {fmt(max(v2) if v2 else None)} | '
          f'{fmt(max(v2o) if v2o else None)}    | {max(int(r["n_s2"]) for r in rs):4}')
    for r, a, b in zip(rs, s1, s2):
        bk = bucket(r['cycle_ist'])
        key = 'm' if (sym, d) in MARKED else 'u'
        if a is not None:
            sep[(sym, 'S1')][bk][key].append(a)
        if b is not None:
            sep[(sym, 'S2')][bk][key].append(b)

print('\nSeparation per bucket: unmarked max  vs  marked min  (a clean threshold exists if unmarked max < marked min)')
for (sym, sig), bks in sorted(sep.items()):
    for bk in ('early', 'mid', 'late'):
        u, m = bks[bk]['u'], bks[bk]['m']
        um = max(u) if u else None
        mm = min(m) if m else None
        verdict = '-' if um is None or mm is None else ('SEPARATES' if um < mm else 'OVERLAPS')
        print(f'  {sym:7} {sig}  {bk:5}  unmarked max {fmt(um)} %  ({len(u)} cycles)   marked min {fmt(mm)} %  ({len(m)} cycles)   {verdict}')
