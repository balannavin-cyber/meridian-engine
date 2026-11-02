#!/usr/bin/env python3
"""Synthetic segment-day generator for the T1a offline processor (docs/tape/T1a_plan.md section 2).

Writes the real recorder layout (<SYM>/<day>/seg_HHMM[_rN].ndjson.gz, session/<day>/subscriptions_*.json,
daily_report, MANIFEST.sha256) and computes the GROUND TRUTH ITSELF: every delta's side is planted by
construction (the packet's price is chosen relative to the previous packet's quote from the intent
name), and the Truth object counts what was planted. Nothing here imports the code under test.

Prices live on a 1/8 grid, so (bid + ask) / 2 is exact in binary floating point.

  python3 tests/tape_t1a/gen_day.py --perf OUT_DIR     # 4-million-packet day, no truth
"""
import gzip
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
NS = 10 ** 9
DAY = "2026-11-02"
PREV = "2026-10-30"
SIDE = {"above_ask": "BUY", "below_bid": "SELL", "above_mid": "BUY", "below_mid": "SELL",
        "tick_up": "BUY", "tick_down": "SELL", "tick_flat": "UNCL", "no_quote": "UNCL"}
RICH = ["above_ask", "below_bid", "above_mid", "below_mid", "tick_up", "tick_down",
        "no_quote", "tick_flat", "zero", "above_ask", "below_bid", "zero"]
SYMS = {
    "NIFTY": dict(idx=256265, fut=7000001, base=5000000, atm=25000, step=50, idx_price=25000.0, fut_price=25010.0),
    "SENSEX": dict(idx=265, fut=7000002, base=6000000, atm=80000, step=100, idx_price=80000.0, fut_price=80010.0),
}
_ISO = {}


def esec(day, hms):
    return int(datetime.fromisoformat("%sT%s+05:30" % (day, hms)).timestamp())


def iso(sec):
    v = _ISO.get(sec)
    if v is None:
        if len(_ISO) > 100000:
            _ISO.clear()
        v = _ISO[sec] = datetime.fromtimestamp(sec, IST).isoformat()
    return v


def recv_iso(ns):
    s, rem = divmod(ns, NS)
    return datetime.fromtimestamp(s, IST).replace(microsecond=rem // 1000).isoformat()


def hm(sec):
    return iso(sec)[11:16]


def bucket(mm):
    """Independent restatement of the plan's hour buckets (section D-8)."""
    if mm < "09:15":
        return "pre_0915"
    if mm < "10:00":
        return "0915_1000"
    if mm >= "15:30":
        return "post_1530"
    if mm >= "15:00":
        return "1500_1530"
    h = int(mm[:2])
    return "%02d00_%02d00" % (h, h + 1)


def share_cycle(k):
    """10-slot cycle with exactly k classified intents."""
    cls = ["above_ask", "below_bid", "tick_up", "tick_down", "above_mid", "below_mid",
           "above_ask", "below_bid", "tick_up", "tick_down"][:k]
    unc = ["no_quote" if i % 2 else "tick_flat" for i in range(10 - k)]
    return cls + unc


class Spec:
    def __init__(self, **kw):
        self.day = DAY
        self.t_start = "09:54:59"
        self.t_end = "10:04:59"
        self.early = RICH
        self.late = RICH
        self.dv = [25, 50, 75, 150, 300, 75, 25]
        self.events = True
        self.layout = "segments"      # or "one_file"
        self.shuffle = None           # seed: shuffle lines inside every segment file
        self.n_strikes = 9
        self.syms = ("NIFTY", "SENSEX")
        self.__dict__.update(kw)


class Tok:
    def __init__(self, sym, token, role, strike, opt, ts, group, price, first_s, emits=True):
        self.sym, self.token, self.role, self.strike, self.opt = sym, token, role, strike, opt
        self.ts, self.group, self.price, self.first_s, self.emits = ts, group, price, first_s, emits
        self.vol = 10000 + token % 1000
        self.vol_first = self.vol
        self.bid, self.ask = price - 0.5, price + 0.5
        self.n = 0
        self.ord = 0


class Truth:
    def __init__(self):
        self.minute, self.cells, self.rules, self.discards = {}, {}, {}, {}
        self.pkt_lines, self.baseline, self.gap_pairs, self.gap_qty = {}, {}, {}, {}
        self.vol, self.nopkt, self.tok_group, self.tok_sym, self.tok_ts = {}, {}, {}, {}, {}
        self.gap_events, self.opt_deltas, self.meta = {}, {}, {}
        self.files = []

    def disc(self, sym, reason, bk, n=1):
        k = (sym, reason, bk)
        self.discards[k] = self.discards.get(k, 0) + n


def universe(spec):
    out = {}
    t0 = esec(spec.day, spec.t_start)
    grow_s = esec(spec.day, "10:02:00")
    n = spec.n_strikes
    for sym in spec.syms:
        c = SYMS[sym]
        toks = [Tok(sym, c["idx"], "IDX", None, None, sym + " IDX", "IDX", c["idx_price"], t0)]
        toks.append(Tok(sym, c["fut"], "FUT", None, None, sym + "FUT", "FUT", c["fut_price"], t0))
        for i in range(n):
            k = c["atm"] + c["step"] * (i - n // 2)
            grp = "ATM3" if abs(k - c["atm"]) <= 3 * c["step"] else "OTHER"
            for j, ot in enumerate(("CE", "PE")):
                tk = c["base"] + 2 * i + j
                px = 1000.0 + (tk % 13) * 8
                noshow = spec.events and i == n - 1 and ot == "PE"
                toks.append(Tok(sym, tk, "OPT", float(k), ot, "%s%d%s" % (sym, k, ot), "%s_%s" % (grp, ot),
                                px, t0, emits=not noshow))
        if spec.events:
            k = c["atm"] + c["step"] * (n // 2 + 1)
            toks.append(Tok(sym, c["base"] + 2 * n, "OPT", float(k), "CE", "%s%dCE" % (sym, k), "OTHER_CE",
                            1000.0, grow_s))
        for o, t in enumerate(x for x in toks if x.role != "IDX" and x.emits):
            t.ord = o
        out[sym] = toks
    return out


def price_for(x, t):
    if x in ("baseline", "gapbase", "zero", "no_quote"):
        return t.price
    if x == "above_ask":
        return t.ask + 0.5
    if x == "below_bid":
        return t.bid - 0.5
    mid = (t.bid + t.ask) / 2.0
    if x == "above_mid":
        return mid + 0.125
    if x == "below_mid":
        return mid - 0.125
    return mid                       # tick_up / tick_down / tick_flat


def quote_for(y, p):
    if y == "tick_up":
        return p - 0.25, p + 0.75
    if y == "tick_down":
        return p - 0.75, p + 0.25
    if y == "no_quote":
        return 0.0, p + 0.5
    return p - 0.5, p + 0.5


def full_rec(t, s, recv, p, bid, ask, vol, oi):
    k = t.n
    bq = [10 + (k + i) % 7 + 3 * i for i in range(5)]
    aq = [12 + (k + 2 * i) % 5 + 2 * i for i in range(5)]
    rec = {"k": "pkt", "sym": t.sym, "role": t.role, "recv_ns": recv, "recv_ist": recv_iso(recv),
           "tradable": True, "mode": "full", "instrument_token": t.token, "last_price": p,
           "last_traded_quantity": 75, "volume_traded": vol, "total_buy_quantity": sum(bq) * 10,
           "total_sell_quantity": sum(aq) * 10,
           "ohlc": {"open": p, "high": p, "low": p, "close": p}, "change": 0.0, "last_trade_time": iso(s),
           "oi": oi, "oi_day_high": oi + 5, "oi_day_low": oi - 5, "exchange_timestamp": iso(s),
           "depth": {"buy": [{"quantity": bq[i], "price": bid - 0.05 * i, "orders": 1} for i in range(5)],
                     "sell": [{"quantity": aq[i], "price": ask + 0.05 * i, "orders": 1} for i in range(5)]}}
    return rec, sum(bq), sum(aq)


def dumps(rec):
    return json.dumps(rec, separators=(",", ":"))


def ctl(kind, recv, **kw):
    rec = {"k": "ctl", "ctl": kind, "recv_ns": recv, "recv_ist": recv_iso(recv)}
    rec.update(kw)
    return rec


def generate(spec, sink, truth=None):
    """sink(sym, recv_ns, line, kind, bk) is called for every record. kind: pkt|ctl|raw."""
    uni = universe(spec)
    t0, t1 = esec(spec.day, spec.t_start), esec(spec.day, spec.t_end)
    gs, ge = esec(spec.day, "09:57:20"), esec(spec.day, "09:57:50")
    t_split = esec(spec.day, "10:00:00")
    ev = spec.events
    reg = {}
    if ev:
        for o, hms in ((3, "09:56:10"), (4, "09:56:40"), (5, "09:58:30"), (6, "09:59:50"),
                       (3, "10:01:10"), (9, "10:03:30"), (10, "10:04:10")):
            reg[(o, esec(spec.day, hms))] = True
    for sym in spec.syms:
        if truth is not None:
            for t in uni[sym]:
                if t.role == "IDX":
                    continue
                truth.tok_group[t.token] = t.group
                truth.tok_sym[t.token] = sym
                truth.tok_ts[t.token] = t.ts
            truth.nopkt[sym] = [t.ts for t in uni[sym] if t.role != "IDX" and not t.emits]
            truth.pkt_lines[sym] = 0
            truth.baseline[sym] = 0
            truth.gap_pairs[sym] = 0
            truth.gap_qty[sym] = 0
        sink(sym, t0 * NS - 3 * NS, dumps(ctl("connect", t0 * NS - 3 * NS, pid=1, process_start_ns=t0 * NS - 9 * NS,
                                              n_tokens=len(uni[sym]), first=True)), "ctl", None)
    if ev:
        gev = [("disconnect", gs * NS - 250000000, dict(code=1006, reason="gap")),
               ("reconnect", ge * NS - 800000000, dict(attempt=1)),
               ("connect", ge * NS - 500000000, dict(pid=1, process_start_ns=t0 * NS - 9 * NS, n_tokens=1, first=False)),
               ("error", gs * NS - 200000000, dict(code=1006, reason="planted"))]
        for sym in spec.syms:
            for kind, rn, kw in gev:
                sink(sym, rn, dumps(ctl(kind, rn, **kw)), "ctl", None)
            if truth is not None:
                truth.gap_events[sym] = [(k, r) for k, r, _ in gev if k != "error"]

    def intent(t, s):
        if s == t.first_s:
            return "baseline"
        if ev and s == ge and t.first_s < gs:
            return "gapbase"
        cyc = spec.early if s < t_split else spec.late
        return cyc[(s - t0 - 1) % len(cyc)]

    def nxt(s):
        return ge if ev and s == gs - 1 else s + 1

    for s in range(t0, t1 + 1):
        if ev and gs <= s < ge:
            continue
        for sym in spec.syms:
            for t in uni[sym]:
                if not t.emits or s < t.first_s:
                    continue
                recv = s * NS + (100 + (t.token % 7) * 100) * 1000000
                if t.role == "IDX":
                    rec = {"k": "pkt", "sym": sym, "role": "IDX", "recv_ns": recv, "recv_ist": recv_iso(recv),
                           "tradable": False, "mode": "full", "instrument_token": t.token,
                           "last_price": t.price, "ohlc": {"open": t.price, "high": t.price, "low": t.price,
                                                         "close": t.price}, "change": 0.0,
                           "exchange_timestamp": iso(s)}
                    sink(sym, recv, dumps(rec), "pkt", bucket(hm(s)))
                    if truth is not None:
                        truth.pkt_lines[sym] += 1
                    continue
                x = intent(t, s)
                p = price_for(x, t)
                y = intent(t, nxt(s)) if nxt(s) <= t1 else "zero"
                bid, ask = quote_for(y, p)
                if x == "baseline" or x == "zero":
                    dv = 0
                elif x == "gapbase":
                    dv = 4000 + (t.token % 11) * 100
                else:
                    dv = spec.dv[(s - t0 - 1) % len(spec.dv)]
                t.vol += dv
                t.n += 1
                oi = 1000 + 3 * t.n + t.token % 5
                rec, bq, aq = full_rec(t, s, recv, p, bid, ask, t.vol, oi)
                mk, bk = hm(s), bucket(hm(s))
                sink(sym, recv, dumps(rec), "pkt", bk)
                if truth is not None:
                    truth.pkt_lines[sym] += 1
                    row = truth.minute.setdefault((t.token, mk), dict(B=0, S=0, U=0, G=0, trades=0, pv=0.0, pq=0,
                                                                      bq=0, aq=0, oi=0, exts=""))
                    row["bq"], row["aq"], row["oi"], row["exts"] = bq, aq, oi, iso(s)
                    cell = truth.cells.setdefault((sym, bk, t.group), [0, 0, 0, 0])
                    if x == "baseline":
                        truth.baseline[sym] += t.vol
                        truth.vol[t.token] = [t.vol, t.vol]
                    elif dv > 0 and x == "gapbase":
                        row["G"] += dv
                        cell[3] += dv
                        r = truth.rules.setdefault((sym, "gap"), [0, 0])
                        r[0] += dv
                        r[1] += 1
                        truth.gap_pairs[sym] += 1
                        truth.gap_qty[sym] += dv
                    elif dv > 0:
                        side = SIDE[x]
                        row[{"BUY": "B", "SELL": "S", "UNCL": "U"}[side]] += dv
                        cell[{"BUY": 0, "SELL": 1, "UNCL": 2}[side]] += dv
                        row["trades"] += 1
                        row["pv"] += p * dv
                        row["pq"] += dv
                        r = truth.rules.setdefault((sym, x), [0, 0])
                        r[0] += dv
                        r[1] += 1
                        if t.role == "OPT":
                            w = "early" if s < t_split else "late"
                            truth.opt_deltas[(sym, w)] = truth.opt_deltas.get((sym, w), 0) + 1
                    truth.vol[t.token][1] = t.vol
                if (t.ord, s) in reg:
                    rr = dict(rec)
                    rr["recv_ns"] = recv + 50000000
                    rr["recv_ist"] = recv_iso(rr["recv_ns"])
                    rr["volume_traded"] = t.vol - 100
                    sink(sym, rr["recv_ns"], dumps(rr), "pkt", bk)
                    if truth is not None:
                        truth.pkt_lines[sym] += 1
                        truth.disc(sym, "volume_regression", bk)
                t.price, t.bid, t.ask = p, bid, ask
    return uni


# ---------------------------------------------------------------------------------- files
def _gz(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as g:
            g.write(("\n".join(lines) + "\n").encode("utf-8"))


def _seg_label(recv_ns):
    return hm((recv_ns // (300 * NS)) * 300)


def _rotate(label, rn):
    return dumps(ctl("rotate", rn, seg=label, prev_seg=None, process_start_ns=1))


def noise(spec, uni, truth, per_sym):
    """Planted noise lines appended to per_sym[sym] = list of (recv_ns, line, kind, bk)."""
    for sym in spec.syms:
        c = SYMS[sym]
        lst = per_sym[sym]
        opt = [t for t in uni[sym] if t.role == "OPT" and t.emits]
        for i, (hms, ms) in enumerate((("09:54:59", 450), ("09:54:59", 450), ("09:54:59", 450),
                                       ("10:02:30", 450), ("10:02:30", 450))):
            t = opt[i]
            s = esec(spec.day, hms)
            rn = s * NS + ms * 1000000
            rec = {"k": "pkt", "sym": sym, "role": "OPT", "recv_ns": rn, "recv_ist": recv_iso(rn),
                   "tradable": True, "mode": "full", "instrument_token": t.token, "last_price": 777.0,
                   "volume_traded": 777, "exchange_timestamp": PREV + "T15:29:59+05:30",
                   "depth": {"buy": [{"quantity": 1, "price": 776.5, "orders": 1}],
                             "sell": [{"quantity": 1, "price": 777.5, "orders": 1}]}}
            lst.append((rn, dumps(rec), "pkt", None))
            bk = bucket(hm(s))
            truth.disc(sym, "stale_date", bk)
            truth.pkt_lines[sym] += 1
        for hms in ("09:58:00", "10:01:00"):
            s = esec(spec.day, hms)
            rn = s * NS + 250000000
            rec = {"k": "pkt", "sym": sym, "role": "OPT", "recv_ns": rn, "recv_ist": recv_iso(rn),
                   "instrument_token": 9999001, "last_price": 5.0, "volume_traded": 10,
                   "exchange_timestamp": iso(s), "depth": {"buy": [], "sell": []}}
            lst.append((rn, dumps(rec), "pkt", None))
            truth.disc(sym, "unmapped_token", bucket(hm(s)))
            truth.pkt_lines[sym] += 1
        for hms in ("09:56:00", "10:03:00"):
            rn = esec(spec.day, hms) * NS + 5000000
            lst.append((rn, '{"k":"pkt","sym":"%s","role":"OPT","recv_ns":%d,"instrument_tok' % (sym, rn), "raw", None))
            truth.disc(sym, "bad_line", "unknown")
        pk = sorted((x for x in lst if x[2] == "pkt" and x[3] is not None))
        step = max(1, len(pk) // 6)
        for x in pk[1::step][:6]:
            lst.append((x[0], x[1], "pkt", x[3]))
            truth.disc(sym, "duplicate", x[3])
            truth.pkt_lines[sym] += 1


def build_day(root, spec=None):
    spec = spec or Spec()
    truth = Truth()
    per_sym = {s: [] for s in spec.syms}

    def sink(sym, rn, line, kind, bk):
        per_sym[sym].append((rn, line, kind, bk))

    uni = generate(spec, sink, truth)
    if spec.events:
        noise(spec, uni, truth, per_sym)
    rnd = random.Random(spec.shuffle)
    files = []
    for sym in spec.syms:
        lst = sorted(per_sym[sym], key=lambda x: x[0])
        base = os.path.join(root, sym, spec.day)
        if spec.layout == "one_file":
            lines = [_rotate("0945", lst[0][0])] + [x[1] for x in lst]
            if spec.shuffle is not None:
                rnd.shuffle(lines)
            p = os.path.join(base, "seg_0945.ndjson.gz")
            _gz(p, lines)
            files.append(p)
            continue
        segs = {}
        for x in lst:
            segs.setdefault(x[0] // (300 * NS), []).append(x)
        for sg in sorted(segs):
            label = hm(sg * 300).replace(":", "")
            xs = segs[sg]
            name = "seg_%s.ndjson.gz" % label
            if spec.events and sym == "NIFTY" and label == "0955":
                cut = len(xs) * 6 // 10
                a, b = xs[:cut], xs[cut:]
                dup = [x for x in a if x[2] == "pkt" and x[3] is not None][5::40][:20]
                for x in dup:
                    truth.disc(sym, "duplicate", x[3])
                    truth.pkt_lines[sym] += 1
                parts = [(name, a), ("seg_%s_r1.ndjson.gz" % label, b + dup)]
            else:
                parts = [(name, xs)]
            for nm, part in parts:
                lines = [_rotate(label, sg * 300 * NS)] + [x[1] for x in part]
                if spec.shuffle is not None:
                    rnd.shuffle(lines)
                p = os.path.join(base, nm)
                _gz(p, lines)
                files.append(p)
    # dup of planted-noise packets whose bucket is None (stale/unmapped copies) is never made: bk None skipped
    sess = os.path.join(root, "session", spec.day)
    os.makedirs(sess, exist_ok=True)
    rows = []
    for sym in spec.syms:
        for t in uni[sym]:
            rows.append({"token": t.token, "sym": sym, "role": t.role, "strike": t.strike, "opt_type": t.opt,
                         "tradingsymbol": t.ts, "expiry": "2026-11-05" if t.role == "OPT" else None,
                         "added_minute": "09:00", "reason": "open_window"})
    first = [r for r in rows if not (r["role"] == "OPT" and r["token"] in
                                    [t.token for s_ in spec.syms for t in uni[s_] if t.first_s > esec(spec.day, spec.t_start)])]
    for nm, rr in (("subscriptions_094500.json", first), ("subscriptions_100300.json", rows)):
        if nm == "subscriptions_100300.json" and not spec.events:
            continue
        p = os.path.join(sess, nm)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"day": spec.day, "written_ist": spec.day + "T09:45:00+05:30", "n": len(rr), "tokens": rr}, fh)
        files.append(p)
    rp = os.path.join(sess, "daily_report_%s.json" % spec.day)
    with open(rp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"day": spec.day, "closed": False, "restarts": [], "reconnects": 1, "disconnects": 1,
                   "unknown_tokens": 2, "symbols": {s: {"packets": truth.pkt_lines[s], "feed_gaps_gt10s": [1],
                                                        "feed_gaps_gt60s": []} for s in spec.syms}}, fh)
    files.append(rp)
    write_manifest(root, spec.day, files)
    truth.files = files
    truth.uni = uni
    truth.spec = spec
    return truth


def write_manifest(root, day, files):
    lines = []
    for p in sorted(files):
        key = os.path.relpath(p, root).replace(os.sep, "/")
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        lines.append("%s  %s" % (h, key))
    mp = os.path.join(root, "session", day, "MANIFEST.sha256")
    with open(mp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------------- perf day
class SegSink:
    """Streaming writer for the performance day: a segment is written once a later one is seen."""

    def __init__(self, root, day):
        self.root, self.day, self.buf, self.top = root, day, {}, 0
        self.n = 0

    def __call__(self, sym, rn, line, kind, bk):
        sg = rn // (300 * NS)
        if sg > self.top:
            self.top = sg
            self.flush(below=sg)
        self.buf.setdefault((sym, sg), []).append(line)
        self.n += 1

    def flush(self, below=None):
        for key in sorted(self.buf):
            sym, sg = key
            if below is not None and sg >= below:
                continue
            label = hm(sg * 300).replace(":", "")
            lines = [_rotate(label, sg * 300 * NS)] + self.buf.pop(key)
            _gz(os.path.join(self.root, sym, self.day, "seg_%s.ndjson.gz" % label), lines)


def build_perf(root, n_strikes=45):
    spec = Spec(events=False, t_start="09:14:59", t_end="15:29:59", n_strikes=n_strikes)
    sink = SegSink(root, spec.day)
    uni = generate(spec, sink, None)
    sink.flush()
    sess = os.path.join(root, "session", spec.day)
    os.makedirs(sess, exist_ok=True)
    rows = [{"token": t.token, "sym": s, "role": t.role, "strike": t.strike, "opt_type": t.opt,
             "tradingsymbol": t.ts, "expiry": "2026-11-05" if t.role == "OPT" else None,
             "added_minute": "09:00", "reason": "open_window"} for s in spec.syms for t in uni[s]]
    with open(os.path.join(sess, "subscriptions_091000.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"day": spec.day, "written_ist": spec.day + "T09:10:00+05:30", "n": len(rows), "tokens": rows}, fh)
    return sink.n


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--perf":
        n = build_perf(sys.argv[2])
        print("perf day written: %d records" % n)
    else:
        print(__doc__)
