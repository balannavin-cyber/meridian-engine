"""Synthetic gex_strike_snapshots export with PLANTED chain events (tape T1b, docs/tape/T1b_plan.md section 2).

The expected event list is written here BY HAND from the timeline below; nothing is computed by the module under test.
Times are IST. Strikes 24300..24700. gex magnitudes: leader 1000, others 100 (sign set per run).
"""
import csv
import hashlib
import os

DAY = "2026-11-03"
STRIKES = [24300, 24400, 24500, 24600, 24700]
A, K = 24400, 24600            # the two leaders that alternate
BASE_CALL, BASE_PUT = 24700, 24300
FRONT, BACK = "2026-11-05", "2026-11-12"
HEADER = ["run_id", "symbol", "ts", "expiry_date", "strike", "oi_call", "oi_put", "gex_cr"]


def hm(h, m):
    return h * 60 + m


# (minute IST, leader, call wall strike, call wall oi, put wall strike, put wall oi, gex sign)
TIMELINE = [
    (hm(9, 50), 24700, BASE_CALL, 100000, BASE_PUT, 100000, 1),     # before 10:00: ignored (a different leader)
    (hm(9, 55), 24700, BASE_CALL, 100000, BASE_PUT, 100000, 1),
    (hm(10, 0), A, BASE_CALL, 100000, BASE_PUT, 100000, 1),
    (hm(10, 10), A, 24600, 100000, BASE_PUT, 100000, 1),             # E2-call: wall 24700 -> 24600
    (hm(10, 20), A, 24600, 100000, BASE_PUT, 105000, 1),             # E2-put:  put wall OI +5.0 %
    (hm(10, 25), A, 24600, 100000, BASE_PUT, 110145, 1),             # +4.9 % of 105000: NO event
    (hm(10, 30), K, 24600, 100000, BASE_PUT, 110145, 1),             # E1 -> K
    (hm(10, 32), A, 24600, 100000, BASE_PUT, 110145, 1),             # E1 -> A
    (hm(10, 34), K, 24600, 100000, BASE_PUT, 110145, 1),             # E1 -> K  (4 min after the counted one)
    (hm(10, 36), A, 24600, 100000, BASE_PUT, 110145, 1),             # E1 -> A
    (hm(10, 38), K, 24600, 100000, BASE_PUT, 110145, 1),             # E1 -> K  (8 min after the counted one)
    (hm(10, 42), A, 24600, 100000, BASE_PUT, 110145, 1),             # E1 -> A  (10 min after the counted A)
    (hm(10, 46), K, 24600, 100000, BASE_PUT, 110145, 1),             # E1 -> K  (16 min after the counted K: separate)
    (hm(10, 50), K, 24600, 100000, BASE_PUT, 110145, 1),
    (hm(10, 55), K, 24600, 100000, BASE_PUT, 110145, -1),            # E3 flip (counted only)
    (hm(11, 0), K, 24600, 100000, BASE_PUT, 110145, 1),              # E3 flip back
]

# Hand-expected COUNTED events: (kind, minute IST, strike, prev_strike, merged_n)
EXPECTED = [
    ("E2-call", hm(10, 10), 24600, 24700, 1),
    ("E2-put", hm(10, 20), 24300, 24300, 1),
    ("E1", hm(10, 30), K, A, 3),        # 10:30, 10:34, 10:38
    ("E1", hm(10, 32), A, K, 3),        # 10:32, 10:36, 10:42
    ("E1", hm(10, 46), K, A, 1),
]
EXPECTED_E3 = 2
EXPECTED_RAW = {"E1": 7, "E2-call": 1, "E2-put": 1}


def ts_str(minute, offset):
    if offset == "+00:00":
        u = minute - 330
        return "%sT%02d:%02d:00+00:00" % (DAY, u // 60, u % 60)
    return "%sT%02d:%02d:00+05:30" % (DAY, minute // 60, minute % 60)


def rows_for(symbol, offset="+00:00", timeline=TIMELINE):
    rows = []
    for (minute, leader, cw, cw_oi, pw, pw_oi, sign) in timeline:
        ts = ts_str(minute, offset)
        for expiry, run_id in ((FRONT, "r-%s-%d-F" % (symbol, minute)), (BACK, "r-%s-%d-B" % (symbol, minute))):
            for k in STRIKES:
                if expiry == FRONT:
                    lead = leader
                else:
                    lead = 24300 if minute % 2 == 0 else 24500       # the back expiry flips its leader every run
                gex = (1000 if k == lead else 100) * sign
                oi_c = (cw_oi if k == cw else 1000) if expiry == FRONT else (5000 if k == 24500 else 1000)
                oi_p = (pw_oi if k == pw else 1000) if expiry == FRONT else (5000 if k == 24400 else 1000)
                rows.append([run_id, symbol, ts, expiry, k, oi_c, oi_p, "%.6f" % gex])
    return rows


def write(root, symbol="NIFTY", offset="+00:00", timeline=TIMELINE, sidecar=True):
    os.makedirs(root, exist_ok=True)
    name = "gex_strike_snapshots_%s.csv" % symbol
    path = os.path.join(root, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(HEADER)
        w.writerows(rows_for(symbol, offset, timeline))
    if sidecar:
        with open(path, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        with open(path + ".sha256", "w", encoding="utf-8", newline="\n") as fh:
            fh.write("%s  %s\n" % (digest, name))
    return path
