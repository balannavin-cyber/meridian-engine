#!/usr/bin/env python3
"""M-P7 scorer. Pre-registered with docs/research/s96_priority/p7/MP7_flow_badge_prereg_2026-10-11.md.

Reads only the CSVs mp7_run.sh wrote under OUT (default ~/mp7_out). No database access.
Order is fixed and load-bearing:
  Part 0a  Rule 13: any range naming a study table excludes the dates it overlaps.
  Part 0b  Control: the replay must reproduce the LIVE book and P5 anchor for the control date.
           If it does not, the scorer STOPS before any sign is computed (prereg section 5).
  Part 1   Badge states per cycle, the three reported measures, the verdict (prereg sections 6-7).
Run with:  python3 -I mp7_score.py [OUT]
"""
import csv, json, os, sys
from collections import defaultdict
from decimal import Decimal as D
from statistics import median, quantiles

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/mp7_out')
TOL = D('1e-9')                       # Rs crore; numeric arithmetic on both sides (prereg 5)
UNTRADED_SENSEX = {'2026-09-25', '2026-09-28', '2026-09-29'}   # TD-S95-NEW-1 (prereg 3.4)
MIN_SESSIONS = 20                     # per symbol, primary sample (prereg 7)
MAX_ABSTAIN = D('0.5')                # prereg 7, derivation there
BUCKETS = (('early', '09:15:00', '10:00:00'), ('mid', '10:00:00', '14:30:00'), ('late', '14:30:00', '15:15:01'))


def stop(msg):
    print('STOP: ' + msg)
    sys.exit(3)


def read(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def sgn(x):
    return (x > 0) - (x < 0)


def bucket(t):
    for name, lo, hi in BUCKETS:
        if lo <= t < hi:
            return name
    return None


# ---------------------------------------------------------------- Part 0a  Rule 13
r13 = read(os.path.join(OUT, 'part0a_rule13.csv'))
# the file holds two result sets; the second (total_rows_visible) has its own header line
hits = [r for r in r13 if r.get('hits_study_tables') == 't']
with open(os.path.join(OUT, 'part0a_rule13.csv')) as f:
    lines = f.read().splitlines()
try:
    visible = int(lines[lines.index('total_rows_visible') + 1])
except (ValueError, IndexError):
    stop('Rule 13 control row missing from part0a_rule13.csv')
if visible < 1:
    stop('merdian_ro sees 0 rows of data_contamination_ranges -- the Rule 13 check cannot find a range (TD-S94-NEW-1)')
excluded_dates = set()
for h in hits:
    s = h['contamination_start'][:10]
    e = (h['contamination_end'] or '9999-12-31')[:10]
    excluded_dates.add((s, e, h['contamination_id']))
print(f'Part 0a  Rule 13: {visible} rows visible; {len(hits)} range(s) name a study table')


def rule13_excluded(day):
    return any(s <= day <= e for s, e, _ in excluded_dates)


# ---------------------------------------------------------------- Part 0b  live control
ctl = read(os.path.join(OUT, 'part0b_control_live.csv'))
book = {r['symbol']: r for r in ctl if r['src'] == 'book'}
p5 = {r['symbol']: r for r in ctl if r['src'] == 'p5'}
if not book or set(book) != set(p5):
    stop(f'control: book symbols {sorted(book)} vs P5 symbols {sorted(p5)}')
for sym, b in book.items():
    p = p5[sym]
    day = b['session_date']
    if p['session_date'] != day or p['expiry_date'] != b['expiry_date']:
        stop(f'control {sym}: book {day}/{b["expiry_date"]} vs P5 {p["session_date"]}/{p["expiry_date"]}')
    path = os.path.join(OUT, 'cycles', day + '.csv')
    if not os.path.exists(path):
        stop(f'control {sym}: no replay file for {day} (the control date must lie in the sample window)')
    rows = [r for r in read(path) if r['symbol'] == sym and r['cycle_ist'] == b['t_ist']]
    if len(rows) != 1:
        stop(f'control {sym}: {len(rows)} replay rows at the settled cycle {b["t_ist"]}')
    r = rows[0]
    checks = [('expiry', r['expiry_date'] == b['expiry_date']),
              ('book_call', abs(D(r['book_call']) - D(b['a1'])) <= TOL),
              ('book_put_v', abs(D(r['book_put_v']) - D(b['a2'])) <= TOL),
              ('oi_qty', D(r['oi_qty']) == D(b['a3'])),
              ('book_gap_oi_v', D(r['book_gap_oi_v']) == D(b['a4'])),
              ('anchor_ist', r['anchor_ist'] == p['t_ist']),
              ('anchor_oi_qty', D(r['anchor_oi_qty']) == D(p['a1'])),
              ('anchor_n_strikes', int(r['anchor_n_strikes']) == int(p['a2']))]
    bad = [n for n, ok in checks if not ok]
    if bad:
        stop(f'control {sym} {day}: replay disagrees with the live views on {bad}')
    print(f'Part 0b  control {sym} {day} {b["t_ist"]}: all 8 fields equal (book_call {b["a1"]}, anchor {p["t_ist"]})')

# ---------------------------------------------------------------- Part 1  sample
status = []
for fn in sorted(os.listdir(os.path.join(OUT, 'status'))):
    status += read(os.path.join(OUT, 'status', fn))
cycles = defaultdict(list)
for fn in sorted(os.listdir(os.path.join(OUT, 'cycles'))):
    for r in read(os.path.join(OUT, 'cycles', fn)):
        cycles[(r['symbol'], r['session_date'])].append(r)

tally = defaultdict(lambda: defaultdict(int))
primary, secondary = defaultdict(list), defaultdict(list)
for s in status:
    sym, day = s['symbol'], s['session_date']
    st = s['status']
    if st == 'ANCHORED' and rule13_excluded(day):
        st = 'RULE13'
    if st == 'ANCHORED' and not cycles.get((sym, day)):
        st = 'NO_CYCLES'
    tally[sym][st] += 1
    if st != 'ANCHORED':
        continue
    rows = sorted(cycles[(sym, day)], key=lambda r: r['cycle_ist'])
    if sym == 'SENSEX' and day in UNTRADED_SENSEX:
        secondary[sym].append((day, rows))
    else:
        primary[sym].append((day, rows))

print('\nPart 1  sessions by status (status files):')
for sym in sorted(tally):
    print(f'  {sym}: ' + ', '.join(f'{k} {v}' for k, v in sorted(tally[sym].items())))

integrity = defaultdict(int)


def state(r):
    """Badge state for one cycle: SAME / OPPOSITE / ABSTAIN (prereg 4)."""
    bc, fc = D(r['book_call']), D(r['flow_call'])
    bv, bp = sgn(bc + D(r['book_put_v'])), sgn(bc + D(r['book_put_p']))
    fv, fp = sgn(fc + D(r['flow_put_v'])), sgn(fc + D(r['flow_put_p']))
    if fv == 0 or bv == 0 or fv != fp or bv != bp:
        return 'ABSTAIN', fv
    return ('SAME' if fv == bv else 'OPPOSITE'), fv


def score(sample):
    out = {}
    for sym in sorted(sample):
        per = defaultdict(lambda: defaultdict(int))
        ratio = defaultdict(list)
        gapshare = []
        pairs = defaultdict(lambda: [0, 0, 0, 0])   # badge same, badge n, flow-sign same, flow-sign n
        for day, rows in sample[sym]:
            prev = None
            for r in rows:
                if int(r['n_dupe_strikes']):
                    integrity['dupe_strike_cycles'] += 1
                if D(r['spot_spread']) != 0:
                    integrity['multi_spot_cycles'] += 1
                b = bucket(r['cycle_ist'])
                st, fsign = state(r)
                for key in (b, 'all'):
                    per[key][st] += 1
                g = D(r['flow_gross_v'])
                net = D(r['flow_call']) + D(r['flow_put_v'])
                if g > 0:
                    for key in (b, 'all'):
                        ratio[key].append(float(abs(net) / g))
                a = D(r['abs_doi_qty'])
                if a > 0:
                    gapshare.append(float(D(r['flow_gap_doi_v']) / a))
                if prev is not None:
                    for key in (b, 'all'):
                        pairs[key][0] += st == prev[0]
                        pairs[key][1] += 1
                        if fsign != 0 and prev[1] != 0:
                            pairs[key][2] += fsign == prev[1]
                            pairs[key][3] += 1
                prev = (st, fsign)
        res = {'sessions': len(sample[sym])}
        for key in ('early', 'mid', 'late', 'all'):
            n = sum(per[key].values())
            q = quantiles(ratio[key], n=4) if len(ratio[key]) >= 2 else [None] * 3
            res[key] = {
                'cycles': n,
                'abstain': per[key]['ABSTAIN'], 'same': per[key]['SAME'], 'opposite': per[key]['OPPOSITE'],
                'abstain_share': (per[key]['ABSTAIN'] / n) if n else None,
                'flow_net_over_gross_p25_p50_p75': q,
                'badge_persistence': (pairs[key][0] / pairs[key][1]) if pairs[key][1] else None,
                'flow_sign_persistence': (pairs[key][2] / pairs[key][3]) if pairs[key][3] else None,
            }
        res['flow_gap_share_median'] = median(gapshare) if gapshare else None
        out[sym] = res
    return out


P = score(primary)
S = score(secondary)
print('\nPart 1  PRIMARY sample' + (f'; integrity: {dict(integrity)}' if integrity else '; integrity: no duplicate strikes, one spot per cycle'))
for sym, res in P.items():
    print(f'\n  {sym}: {res["sessions"]} sessions; median flow gap share {res["flow_gap_share_median"]}')
    print('    bucket  cycles  abstain  same  opposite  abstain_share  |net|/gross p25/p50/p75   badge_persist  flow_sign_persist')
    for key in ('early', 'mid', 'late', 'all'):
        x = res[key]
        q = '/'.join('-' if v is None else f'{v:.3f}' for v in x['flow_net_over_gross_p25_p50_p75'])
        f = lambda v: '-' if v is None else f'{v:.3f}'
        print(f'    {key:6}  {x["cycles"]:6}  {x["abstain"]:7}  {x["same"]:4}  {x["opposite"]:8}  {f(x["abstain_share"]):>13}  {q:>24}  {f(x["badge_persistence"]):>13}  {f(x["flow_sign_persistence"]):>17}')
if S:
    print('\nSECONDARY (SENSEX 09-25 / 09-28 / 09-29, TD-S95-NEW-1), reported, not scored:')
    print(json.dumps(S, indent=1, default=str))

# ---------------------------------------------------------------- verdict (prereg 7)
verdict = {}
for sym in ('NIFTY', 'SENSEX'):
    r = P.get(sym)
    if r is None or r['sessions'] < MIN_SESSIONS:
        verdict[sym] = 'INCONCLUSIVE'
    else:
        verdict[sym] = 'SPEAKS' if D(str(r['all']['abstain_share'])) <= MAX_ABSTAIN else 'SILENT'
if 'INCONCLUSIVE' in verdict.values():
    overall = 'INCONCLUSIVE'
elif all(v == 'SPEAKS' for v in verdict.values()):
    overall = 'BUILD'
else:
    overall = 'DECLINED-ON-EVIDENCE'
print(f'\nVERDICT per symbol {verdict} -> DEX badge: {overall}')
json.dump({'primary': P, 'secondary': S, 'tally': {k: dict(v) for k, v in tally.items()},
           'integrity': dict(integrity), 'verdict': verdict, 'overall': overall},
          open(os.path.join(OUT, 'mp7_score.json'), 'w'), indent=1, default=str)
