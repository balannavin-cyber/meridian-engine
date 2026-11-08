#!/usr/bin/env python3
"""Tape live L0 fixture: one synthetic segment day + chain export with planted labels (docs/tape/L0_plan.md section 7).

  python tests/tape_live/gen_live.py OUT_DIR

Writes OUT_DIR/raw/<day>/{NIFTY,SENSEX,session}/<day>/... in the bucket layout, OUT_DIR/chain/gex_strike_snapshots_<SYM>.csv
(the export columns: run_id, symbol, ts, expiry_date, strike, oi_call, oi_put, gex_cr) and returns PLANTED, the label expected at
chosen grid points. PLANTED is written from the plan below, by hand, never by running services/tape_live.

Precision follows the loaded days: NIFTY lot 65 / SENSEX lot 20 quantities, depth totals 650-1625, OI in the 10^5-10^6 range,
exchange timestamps at whole seconds, recv 250 ms later, segments = floor(recv, 5 min), gzip with mtime 0 (deterministic bytes).

Plan (minutes are IST):
  every token, every minute 08:56..15:34: packet A at :15 carries the minute's volume, packet B at :45 carries none (it only sets
  the end-of-minute depth). Even minutes print at the ask (BUY), odd minutes at the bid (SELL). Baseline volume per minute is
  2 lots in even bins and 3 lots in odd bins (bin index from 09:20), so CONC needs a planted burst and nothing else fires.
  Ask/bid depth = 5 levels x 325 (NIFTY) / 5 x 100 (SENSEX); a THIN drop sets the ask levels to 130 / 40 (= 40 % of the total).
  NIFTY 23550 CE  burst 40 lots/min in minutes 10:55-11:04 (bins 11:00, 11:05 -> CONC stamped 11:05);
                  ask drop at minutes 11:01, 11:02 (THIN ask stamped 11:03)                  -> HIT at 11:05, 11:10, 11:15
  NIFTY 23500 PE  burst in minutes 11:55-12:04 (CONC 12:05)                                  -> ABSORBED 12:05..12:15
                  ask drop at minutes 14:01, 14:02 (THIN ask 14:03)                          -> THINNING 14:05..14:15
  NIFTY 23500 CE  bid drop at minutes 12:31, 12:32 (THIN bid 12:33): a bid-side event that must never become N
  SENSEX 77100 PE never trades (volume constant)                                             -> NO_READ untraded from 10:00
  NIFTY 23650 CE  subscribed at 11:33 (subscriptions_113300.json), packets from 11:34: the mid-day map change
  chain: NIFTY runs every 5 min from 09:00:21; call wall 23550 except runs 13:00-13:10 (23700, not subscribed); put wall 23500.
         SENSEX runs from 09:30:21 (09:20, 09:25 have no run); call wall 77000, put wall 77100.
         A second, later expiry with larger OI is present in every run and must be ignored (front expiry only).
"""
import gzip
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

DAY = "2026-11-06"
IST = timezone(timedelta(hours=5, minutes=30))
NS = uuid.UUID("6f1d6b2e-2c8e-4a41-9d0a-5a1e0c0b7a11")

LOT = {"NIFTY": 65, "SENSEX": 20}
LVL = {"NIFTY": 325, "SENSEX": 100}
LVL_THIN = {"NIFTY": 130, "SENSEX": 40}
EXPIRY = {"NIFTY": "2026-11-09", "SENSEX": "2026-11-12"}
FUT_EXP = {"NIFTY": "2026-11-23", "SENSEX": "2026-11-26"}
BACK_EXP = {"NIFTY": "2026-11-16", "SENSEX": "2026-11-19"}
PRICE = {"NIFTY": 140.0, "SENSEX": 410.0}

# token, sym, role, strike, opt_type, added_minute, first packet minute
TOKENS = [
    (10101, "NIFTY", "OPT", 23500, "CE", "08:55", "08:56"),
    (10102, "NIFTY", "OPT", 23500, "PE", "08:55", "08:56"),
    (10103, "NIFTY", "OPT", 23550, "CE", "08:55", "08:56"),
    (10104, "NIFTY", "OPT", 23550, "PE", "08:55", "08:56"),
    (10105, "NIFTY", "OPT", 23600, "CE", "08:55", "08:56"),
    (10106, "NIFTY", "OPT", 23600, "PE", "08:55", "08:56"),
    (10190, "NIFTY", "FUT", None, None, "08:55", "08:56"),
    (10199, "NIFTY", "IDX", None, None, "08:55", "08:56"),
    (20201, "SENSEX", "OPT", 77000, "CE", "08:55", "08:56"),
    (20202, "SENSEX", "OPT", 77000, "PE", "08:55", "08:56"),
    (20203, "SENSEX", "OPT", 77100, "CE", "08:55", "08:56"),
    (20204, "SENSEX", "OPT", 77100, "PE", "08:55", "08:56"),
    (20290, "SENSEX", "FUT", None, None, "08:55", "08:56"),
]
LATE_TOKEN = (10107, "NIFTY", "OPT", 23650, "CE", "11:33", "11:34")
# Rebuild-scope day only (build(root, scope=True), docs/tape/L2_rebuild_scope_plan.md section 4).
SCOPE_TOKENS = [(20205, "SENSEX", "OPT", 77200, "CE", "12:03", "12:04"),
                (10108, "NIFTY", "OPT", 23750, "CE", "12:33", "12:34"),
                (20206, "SENSEX", "OPT", 77200, "PE", "12:33", "12:34"),
                (20207, "SENSEX", "OPT", 77300, "CE", "14:03", "14:04")]
SCOPE_META_TOKEN = 20203                      # its tradingsymbol differs in the late-arriving, earlier-sorting 085500 file
# arrivals: the 085500 file at 13:35 (case e); SENSEX seg_1350 at 14:05, after seg_1355 (case f)
SCOPE_ARRIVAL = {"session/subscriptions_085500.json": "13:35", "SENSEX/seg_1350.ndjson.gz": "14:05"}
UNTRADED = {20204}
BURST = {10103: range(655, 665), 10102: range(715, 725)}          # minutes with 40 lots
ASK_DROP = {10103: (661, 662), 10102: (841, 842)}
BID_DROP = {10101: (751, 752)}

FIRST_MIN, LAST_MIN = 8 * 60 + 56, 15 * 60 + 34


def hm(m):
    return "%02d:%02d" % (m // 60, m % 60)


def epoch(m, s):
    return datetime(2026, 11, 6, m // 60, m % 60, s, tzinfo=IST).timestamp()


def tsym(tok):
    t, sym, role, k, ot = tok[:5]
    if role == "FUT":
        return "%s26NOVFUT" % sym
    if role == "IDX":
        return "NSE:NIFTY 50"
    return "%s26N%s%d%s" % (sym, "09" if sym == "NIFTY" else "12", k, ot)


def meta_row(tok):
    t, sym, role, k, ot, added, _ = tok
    return {"token": t, "sym": sym, "role": role, "strike": k, "opt_type": ot, "tradingsymbol": tsym(tok),
            "expiry": None if role == "IDX" else (FUT_EXP[sym] if role == "FUT" else EXPIRY[sym]),
            "added_minute": added, "reason": "fixture"}


def lots_per_min(tok, m):
    t, sym = tok[0], tok[1]
    if t in UNTRADED:
        return 0
    if m in BURST.get(t, ()):
        return 40
    b = (m - 555) // 5 if m >= 555 else 0
    return 2 if b % 2 == 0 else 3


def packets(tok):
    t, sym, role, k, ot, _added, first = tok
    m0 = int(first[:2]) * 60 + int(first[3:])
    vol, out = 1000 * LOT[sym], []
    oi = 250000 + 13 * LOT[sym] * (t % 7)
    for m in range(m0, LAST_MIN + 1):
        q = lots_per_min(tok, m) * LOT[sym]
        ask_l = LVL_THIN[sym] if m in ASK_DROP.get(t, ()) else LVL[sym]
        bid_l = LVL_THIN[sym] if m in BID_DROP.get(t, ()) else LVL[sym]
        p = PRICE[sym] + (t % 5)
        bid, ask = p - 0.5, p + 0.5
        oi += LOT[sym] * (m % 3)
        for sec, dq in ((15, q), (45, 0)):
            vol += dq
            ltp = ask if m % 2 == 0 else bid
            ex = epoch(m, sec)
            rec = {"k": "pkt", "sym": sym, "role": role, "recv_ns": int(ex) * 1000000000 + 250000000,
                   "recv_ist": datetime.fromtimestamp(ex + 0.25, IST).isoformat(timespec="microseconds"),
                   "instrument_token": t, "exchange_timestamp": datetime.fromtimestamp(ex, IST).isoformat()}
            if role == "IDX":
                rec.update({"last_price": 23548.0 + (m % 4)})
            else:
                rec.update({"last_price": ltp, "average_traded_price": p, "volume_traded": vol, "oi": oi,
                            "depth": {"buy": [{"quantity": bid_l, "price": bid - 0.05 * i, "orders": 2} for i in range(5)],
                                      "sell": [{"quantity": ask_l, "price": ask + 0.05 * i, "orders": 2} for i in range(5)]}})
            out.append(rec)
    return out


def dumps(rec):
    return json.dumps(rec, separators=(",", ":"), sort_keys=True).encode("utf-8")


def write_raw(root, scope=False):
    base = os.path.join(root, "raw", DAY)
    segs = {}
    first_ctl = {"NIFTY": False, "SENSEX": False}
    for tok in TOKENS + [LATE_TOKEN] + (SCOPE_TOKENS if scope else []):
        for rec in packets(tok):
            ns = rec["recv_ns"]
            slot = int((ns // 1000000000 - epoch(0, 0)) // 300) * 5
            segs.setdefault((tok[1], slot), []).append((ns, dumps(rec)))
    for (sym, slot) in sorted(segs):
        lines = sorted(segs[(sym, slot)])
        if not first_ctl[sym]:
            first_ctl[sym] = True
            rn = int(epoch(8, 55) * 1e9) + 1000000
            lines.insert(0, (rn, dumps({"k": "ctl", "ctl": "connect", "recv_ns": rn, "process_start_ns": rn - 5})))
        d = os.path.join(base, sym, DAY)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "seg_%s.ndjson.gz" % hm(slot).replace(":", "")), "wb") as fh:
            fh.write(gzip.compress(b"".join(l + b"\n" for _, l in lines), mtime=0))
    sd = os.path.join(base, "session", DAY)
    os.makedirs(sd, exist_ok=True)
    files = [("subscriptions_085501.json", TOKENS), ("subscriptions_113300.json", TOKENS + [LATE_TOKEN])]
    if scope:
        files += scope_sub_files()
    for name, toks in files:
        doc = {"day": DAY, "n": len(toks), "tokens": [t if isinstance(t, dict) else meta_row(t) for t in toks]}
        with open(os.path.join(sd, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return base


def chain_rows(sym):
    rows = []
    start = 9 * 60 if sym == "NIFTY" else 9 * 60 + 30
    strikes = list(range(23400, 23701, 50)) if sym == "NIFTY" else list(range(76900, 77201, 100))
    for m in range(start, 15 * 60 + 31, 5):
        ts = datetime(2026, 11, 6, m // 60, m % 60, 21, 500000, tzinfo=IST).astimezone(timezone.utc).isoformat()
        rid = str(uuid.uuid5(NS, "%s-%s" % (sym, ts)))
        if sym == "NIFTY":
            cw = 23700 if 13 * 60 <= m <= 13 * 60 + 10 else 23550
            pw = 23500
        else:
            cw, pw = 77000, 77100
        for k in strikes:
            oc = 4000000 + 1300 * (m % 7) if k == cw else 400000 + 65 * (k % 300)
            op = 4500000 + 1300 * (m % 5) if k == pw else 380000 + 65 * (k % 200)
            rows.append([rid, sym, ts, EXPIRY[sym], "%.1f" % k, str(oc), str(op), "%.6f" % ((k - strikes[3]) * 0.0137)])
        for k in strikes:   # back expiry: larger OI everywhere; must never be read
            rows.append([rid, sym, ts, BACK_EXP[sym], "%.1f" % k, str(9000000 + k), str(9100000 + k), "0.500000"])
    return rows


def write_chain(root):
    d = os.path.join(root, "chain")
    os.makedirs(d, exist_ok=True)
    paths = []
    for sym in ("NIFTY", "SENSEX"):
        p = os.path.join(d, "gex_strike_snapshots_%s.csv" % sym)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("run_id,symbol,ts,expiry_date,strike,oi_call,oi_put,gex_cr\n")
            for r in chain_rows(sym):
                fh.write(",".join(r) + "\n")
        paths.append(p)
    return paths


# (symbol, HH:MM, wall) -> (label, partial, reason). From the plan above, by hand.
PLANTED = {
    ("NIFTY", "09:20", "call"): ("NO_READ", False, "insufficient history"),
    ("NIFTY", "09:30", "call"): ("NO_READ", False, "insufficient history"),
    ("NIFTY", "09:35", "call"): ("NO_READ", False, "flow not yet evaluable"),
    ("NIFTY", "10:15", "call"): ("NO_READ", False, "flow not yet evaluable"),
    ("NIFTY", "10:20", "call"): ("QUIET", False, ""),
    ("NIFTY", "11:00", "call"): ("QUIET", False, ""),
    ("NIFTY", "11:05", "call"): ("HIT", False, ""),
    ("NIFTY", "11:10", "call"): ("HIT", False, ""),
    ("NIFTY", "11:15", "call"): ("HIT", False, ""),
    ("NIFTY", "11:20", "call"): ("QUIET", False, ""),
    ("NIFTY", "13:00", "call"): ("NO_READ", False, "wall outside subscribed window"),
    ("NIFTY", "13:10", "call"): ("NO_READ", False, "wall outside subscribed window"),
    ("NIFTY", "13:15", "call"): ("QUIET", False, ""),
    ("NIFTY", "12:00", "put"): ("QUIET", False, ""),
    ("NIFTY", "12:05", "put"): ("ABSORBED", False, ""),
    ("NIFTY", "12:15", "put"): ("ABSORBED", False, ""),
    ("NIFTY", "12:20", "put"): ("QUIET", False, ""),
    ("NIFTY", "14:00", "put"): ("QUIET", False, ""),
    ("NIFTY", "14:05", "put"): ("THINNING", False, ""),
    ("NIFTY", "14:15", "put"): ("THINNING", False, ""),
    ("NIFTY", "14:20", "put"): ("QUIET", False, ""),
    ("SENSEX", "09:20", "call"): ("NO_READ", False, "no chain run"),
    ("SENSEX", "09:25", "put"): ("NO_READ", False, "no chain run"),
    ("SENSEX", "09:30", "call"): ("NO_READ", False, "insufficient history"),
    ("SENSEX", "09:35", "call"): ("NO_READ", False, "flow not yet evaluable"),
    ("SENSEX", "10:20", "call"): ("QUIET", False, ""),
    ("SENSEX", "15:30", "call"): ("QUIET", False, ""),
    ("SENSEX", "09:55", "put"): ("NO_READ", False, "flow not yet evaluable"),
    ("SENSEX", "10:00", "put"): ("NO_READ", False, "untraded wall (vendor OI)"),
    ("SENSEX", "15:30", "put"): ("NO_READ", False, "untraded wall (vendor OI)"),
}
# The segment whose late arrival changes exactly one label, and that label (verify / first-wins guards). Held one cycle, it still
# arrives in key order (with seg_1105), so it needs no rebuild.
LATE_SEG = ("NIFTY", "seg_1100.ndjson.gz", "11:10")
# A segment that arrives AFTER two later ones of its symbol: out of order, so the writer must rebuild (equal-offline guard).
LATE_SEG_OOO = ("NIFTY", "seg_1200.ndjson.gz", "12:20")
LATE_LABEL = (("NIFTY", "11:05", "call"), ("QUIET", False, ""))
# The run whose final walls differ from the live ones in the chain_run_differs scenario.
WALL_CHANGE = ("NIFTY", "11:10", "call_wall", "23600", ("NIFTY", "11:10", "call"))


def scope_sub_files():
    """The scope day's extra subscription files (docs/tape/L2_rebuild_scope_plan.md section 4), cumulative like the recorder."""
    base = TOKENS + [LATE_TOKEN]
    s1, n2, s2, s3 = SCOPE_TOKENS
    meta_chg = dict(meta_row(next(t for t in TOKENS if t[0] == SCOPE_META_TOKEN)))
    meta_chg["tradingsymbol"] += "X"
    return [("subscriptions_120300.json", base + [s1]),                 # case a: SENSEX only
            ("subscriptions_123300.json", base + [s1, n2, s2]),         # case c: both
            ("subscriptions_130300.json", base + [s1, n2, s2]),         # case d: nothing new
            ("subscriptions_085500.json", [meta_chg]),                  # case e: sorts first, arrives late
            ("subscriptions_140300.json", base + [s1, n2, s2, s3])]     # case f: SENSEX, with a late SENSEX segment


def build(root, scope=False):
    """scope=True: the rebuild-scope day (live-rebuild-scope guard); the default day is byte-unchanged."""
    raw = write_raw(root, scope)
    chain = write_chain(root)
    return {"raw": raw, "chain": chain, "day": DAY}


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1]), indent=1))
