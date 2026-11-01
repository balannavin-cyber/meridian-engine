#!/usr/bin/env python3
"""Tape T0 guards (docs/tape/T0_plan.md §8). Offline: no network, no credentials, no kiteconnect,
no boto3 -- FakeKite / FakeTicker / FakeS3 / ManualClock are injected.

  python3 tests/test_tape_t0.py [--root DIR] [--only GUARD]

--root runs the guards against another copy of the tree (tests/tape_mutants.py uses it).
Last line: "TAPE T0 PASS (11/11 guards, N/N unit checks)" or "TAPE T0 FAIL ...". Exit 0 / 1.
"""
import argparse
import ast
import base64
import gzip
import hashlib
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import date, datetime, timedelta

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--only", default=None)
ARGS = ap.parse_args()
ROOT = os.path.abspath(ARGS.root)
sys.path.insert(0, ROOT)

DAY = "2026-11-02"          # a Monday
PREV = "2026-10-30"         # the Friday before
TMP = []


def tmpdir():
    d = tempfile.mkdtemp(prefix="tape_t0_")
    TMP.append(d)
    return d


# ======================================================================== fakes
class ManualClock:
    def __init__(self, ns):
        self.ns = ns

    def now_ns(self):
        return self.ns

    def sleep(self, s):
        self.ns += int(s * 1e9)

    def set(self, ns):
        self.ns = ns


def ist_ns(day, hms):
    from services.tape_runner import clock as clk
    return clk.ist_ns(day, hms)


def kite_naive(day, hms):
    """What kiteconnect's ticker produces: datetime.fromtimestamp(epoch) in the PROCESS zone."""
    return datetime.fromtimestamp(ist_ns(day, hms) // 10**9)


NIFTY_STRIKES = [22000 + 50 * i for i in range(121)]       # 22000 .. 28000
SENSEX_STRIKES = [70000 + 100 * i for i in range(201)]     # 70000 .. 90000
TOK = {}


def _instruments():
    nfo, bfo = [], []
    t = 10_000
    for name, seg, strikes, out in (("NIFTY", "NFO", NIFTY_STRIKES, nfo), ("SENSEX", "BFO", SENSEX_STRIKES, bfo)):
        for exp in (date(2026, 11, 4), date(2026, 11, 11), date(2026, 10, 28)):   # front, next, expired
            for k in strikes:
                for ot in ("CE", "PE"):
                    t += 1
                    out.append({"instrument_token": t, "name": name, "segment": seg + "-OPT", "exchange": seg,
                                "instrument_type": ot, "strike": float(k), "expiry": exp,
                                "tradingsymbol": "%s%s%d%s" % (name, exp.strftime("%y%m%d"), k, ot)})
                    if exp == date(2026, 11, 4):
                        TOK[(name, k, ot)] = t
        for exp in (date(2026, 11, 25), date(2026, 12, 30)):
            t += 1
            out.append({"instrument_token": t, "name": name, "segment": seg + "-FUT", "exchange": seg,
                        "instrument_type": "FUT", "strike": 0.0, "expiry": exp,
                        "tradingsymbol": "%s%sFUT" % (name, exp.strftime("%y%b").upper())})
            if exp == date(2026, 11, 25):
                TOK[(name, "FUT")] = t
        out.append({"instrument_token": t + 500, "name": name + "50", "segment": seg + "-OPT", "exchange": seg,
                    "instrument_type": "CE", "strike": 1.0, "expiry": date(2026, 11, 3), "tradingsymbol": "DECOY"})
    return {"NFO": nfo, "BFO": bfo}


INSTR = _instruments()
TOK[("NIFTY", "IDX")] = 256265
TOK[("SENSEX", "IDX")] = 265


class FakeKite:
    def __init__(self, profile_fails=False, prices=None, quote=None, quote_fails=False):
        self.profile_fails = profile_fails
        self.prices = prices or {"NSE:NIFTY 50": 25000.0, "BSE:SENSEX": 80000.0}
        self.quote_resp = quote
        self.quote_fails = quote_fails
        self.calls = []

    def profile(self):
        self.calls.append("profile")
        if self.profile_fails:
            raise PermissionError("Incorrect `api_key` or `access_token`.")
        return {"user_id": "XX0000"}

    def instruments(self, exch):
        self.calls.append("instruments:" + exch)
        return [dict(r) for r in INSTR[exch]]

    def ltp(self, keys):
        self.calls.append("ltp")
        tok = {"NSE:NIFTY 50": 256265, "BSE:SENSEX": 265}
        return {k: {"instrument_token": tok[k], "last_price": self.prices[k]} for k in keys}

    def quote(self, keys):
        self.calls.append("quote")
        if self.quote_fails:
            raise ConnectionError("down")
        return self.quote_resp or {}


class FakeTicker:
    MODE_FULL = "full"

    def __init__(self):
        self.subscribed = set()
        self.calls = []
        self.connected_called = False
        self.on_ticks = self.on_connect = self.on_close = self.on_error = None
        self.on_reconnect = self.on_noreconnect = None

    def connect(self, threaded=False, **kw):
        self.connected_called = True

    def subscribe(self, toks):
        self.calls.append(("subscribe", list(toks)))
        self.subscribed |= set(toks)

    def unsubscribe(self, toks):
        self.calls.append(("unsubscribe", list(toks)))
        self.subscribed -= set(toks)

    def set_mode(self, mode, toks):
        self.calls.append(("set_mode", mode, list(toks)))

    def close(self, *a):
        self.calls.append(("close",))


class FakeS3:
    def __init__(self, mode="ok"):
        self.mode = mode
        self.objects = {}
        self.puts = []

    def put_object(self, Bucket, Key, Body, ServerSideEncryption=None, ContentMD5=None):
        existed = os.path.exists(Body.name)
        data = Body.read()
        md5 = hashlib.md5(data)
        self.puts.append({"key": Key, "existed": existed, "sse": ServerSideEncryption, "md5": md5.hexdigest()})
        if self.mode == "fail":
            raise ConnectionError("S3 unreachable")
        if ContentMD5 != base64.b64encode(md5.digest()).decode():
            raise ValueError("BadDigest")
        self.objects[Key] = data
        etag = md5.hexdigest() if self.mode == "ok" else "0" * 32
        return {"ETag": '"%s"' % etag}


def idx_pkt(sym, price, day, hms, **extra):
    d = {"tradable": False, "mode": "full", "instrument_token": TOK[(sym, "IDX")], "last_price": price,
         "ohlc": {"high": price, "low": price, "open": price, "close": price}, "change": 0.0,
         "exchange_timestamp": kite_naive(day, hms)}
    d.update(extra)
    return d


def full_pkt(token, price, vol, day, hms, bid=None, ask=None, **extra):
    bid = price - 0.5 if bid is None else bid
    ask = price + 0.5 if ask is None else ask
    d = {"tradable": True, "mode": "full", "instrument_token": token, "last_price": price,
         "last_traded_quantity": 75, "average_traded_price": price, "volume_traded": vol,
         "total_buy_quantity": 1000, "total_sell_quantity": 1000,
         "ohlc": {"open": price, "high": price, "low": price, "close": price}, "change": 0.0,
         "last_trade_time": kite_naive(day, hms), "oi": 100, "oi_day_high": 120, "oi_day_low": 90,
         "exchange_timestamp": kite_naive(day, hms),
         "depth": {"buy": [{"quantity": 75, "price": bid - 0.05 * i, "orders": 1} for i in range(5)],
                   "sell": [{"quantity": 75, "price": ask + 0.05 * i, "orders": 1} for i in range(5)]}}
    d.update(extra)
    return d


def make_recorder(kite=None, s3=None, start="08:50", cap=None, root=None):
    from services.tape_runner.recorder import Recorder
    clock = ManualClock(ist_ns(DAY, start))
    tickers = []

    def factory():
        t = FakeTicker()
        tickers.append(t)
        return t
    rec = Recorder(kite or FakeKite(), factory, s3 or FakeS3(), clock, root=root or tmpdir(),
                   bucket="test-bucket", spool_cap=cap, threaded=False, secrets=("SECRETKEY", "SECRETTOKEN"),
                   log=lambda m: None)
    return rec, clock, tickers


def boot_open_day(rec, clock, tickers, nifty=25000.0, sensex=80000.0):
    """08:50 profile, 08:55 resolve+connect, today-dated index packet, 09:00 options."""
    assert rec.step(clock.now_ns()) is None
    clock.set(ist_ns(DAY, "08:55"))
    assert rec.step(clock.now_ns()) is None
    t = tickers[0]
    t.on_connect(t, {})
    clock.set(ist_ns(DAY, "09:00:01"))
    t.on_ticks(t, [idx_pkt("NIFTY", nifty, DAY, "09:00:01"), idx_pkt("SENSEX", sensex, DAY, "09:00:01")])
    assert rec.step(clock.now_ns()) is None
    return t


def s3_records(s3, prefix):
    out = []
    for key in sorted(s3.objects):
        if key.startswith(prefix) and key.endswith(".ndjson.gz"):
            for line in gzip.decompress(s3.objects[key]).decode().splitlines():
                out.append((key, json.loads(line)))
    return out


def run_to_stop(rec, clock):
    clock.set(ist_ns(DAY, "15:40"))
    return rec.step(clock.now_ns())


# ======================================================================== guards
def g_classify_synthetic():
    from merdian_compute.tape.classify import classify, MinuteAccumulator, BUY, SELL, UNCL
    cells = []
    for seed in (1, 2, 3, 4, 5):
        rnd = random.Random(seed)
        bid, ask, vol, last = 100.0, 100.5, 0, 100.25
        prev = None
        acc = MinuteAccumulator()
        planted = []   # (qty, true side) per classified packet
        total_dv, correct, first = 0, 0, None
        for i in range(4000):
            quote_ok = rnd.random() > 0.05
            r = rnd.random()
            if prev is None or r < 0.15:
                dv, true, p = 0, None, last                      # quote-only update
            else:
                dv = rnd.choice([25, 50, 75, 150, 300])
                kind = rnd.random()
                true = BUY if rnd.random() < 0.5 else SELL
                tick = 0.05
                if kind < 0.45:                                  # at the touch
                    p = ask if true == BUY else bid
                elif kind < 0.55:                                # through the touch
                    p = ask + tick if true == BUY else bid - tick
                else:                                            # inside the spread, off mid
                    mid = (bid + ask) / 2
                    p = round(mid + (0.1 if true == BUY else -0.1), 2)
                if rnd.random() < 0.08:                          # ground-truth noise: hidden/odd prints
                    true = SELL if true == BUY else BUY
            vol += dv
            c = round(100 + rnd.uniform(-2, 2), 2)              # the quote AFTER this packet's trade
            bid, ask = c - 0.25, c + 0.25
            depth = ({"buy": [{"price": bid, "quantity": 75, "orders": 1}],
                      "sell": [{"price": ask, "quantity": 75, "orders": 1}]} if quote_ok else {})
            pkt = {"instrument_token": 1, "last_price": p, "volume_traded": vol, "depth": depth}
            tr = classify(prev, pkt)
            if prev is None:
                first = tr
            minute = "09:%02d" % (15 + i // 200)
            acc.add(minute, tr)
            if dv > 0:
                total_dv += dv
                if prev is not None and prev.get("depth"):
                    planted.append((dv, true))
                    if tr.side == true:
                        correct += dv
            prev = pkt
            last = p
        tot = acc.totals()
        cons = tot["buy_qty"] + tot["sell_qty"] + tot["uncl_qty"]
        classed = sum(q for q, _ in planted)
        share = correct / classed if classed else 0
        ok = share >= 0.80 and cons == total_dv and first.qty == 0 and first.side is None
        cells.append((ok, "seed %d: correct %.3f of classifiable volume, buy+sell+uncl=%d vs sum(dv)=%d, first=%s"
                      % (seed, share, cons, total_dv, tuple(first))))
    # a negative delta is a reset, not a trade; the next delta is measured from the reset packet
    a = {"volume_traded": 1000, "last_price": 10, "depth": {"buy": [{"price": 9.9}], "sell": [{"price": 10.1}]}}
    b = {"volume_traded": 10, "last_price": 10.1}
    c = {"volume_traded": 60, "last_price": 10.1}
    rb, rc = classify(a, b), classify(b, c)
    cells.append((rb.qty == 0 and rb.side is None and rc.qty == 50 and rc.side == UNCL,
                  "reset: %s then %s (UNCL, qty kept)" % (tuple(rb), tuple(rc))))
    return cells


FORBID_MODS = {"time", "random", "socket", "ssl", "http", "urllib", "requests", "asyncio", "secrets", "uuid"}


def g_classify_purity():
    base = os.path.join(ROOT, "merdian_compute", "tape")
    cells, bad = [], []
    files = sorted(f for f in os.listdir(base) if f.endswith(".py"))
    for f in files:
        tree = ast.parse(open(os.path.join(base, f)).read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in FORBID_MODS:
                        bad.append("%s: import %s" % (f, a.name))
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in FORBID_MODS:
                    bad.append("%s: from %s" % (f, node.module))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("now", "utcnow", "today"):
                    bad.append("%s: .%s(" % (f, node.func.attr))
    cells.append((len(files) >= 2 and not bad, "%d files scanned; forbidden: %s" % (len(files), bad or "none")))
    return cells


def g_segments_rotate():
    from services.tape_runner.segments import SegmentWriter
    from services.tape_runner.serialize import ctl_record
    spool = tmpdir()
    closed = []
    w = SegmentWriter(spool, ["NIFTY"], on_closed=closed.append, process_start_ns=1)

    def rec(i, ns):
        return {"k": "pkt", "id": i, "recv_ns": ns}
    t_a, t_b = ist_ns(DAY, "09:19:59.9"), ist_ns(DAY, "09:20:00.0")
    w.write("NIFTY", rec("A", t_a), t_a)
    w.write("NIFTY", rec("B", t_b), t_b)
    start, end = ist_ns(DAY, "09:21:00"), ist_ns(DAY, "09:40:59")   # crosses 09:25, :30, :35, :40
    sent = ["A", "B"]
    for i in range(10_000):
        ns = start + (end - start) * i // 10_000
        w.write("NIFTY", rec(i, ns), ns)
        sent.append(i)
    w.tick(ist_ns(DAY, "09:45:00"))
    seen, where = [], {}
    for p in closed:
        for line in gzip.open(p, "rt"):
            r = json.loads(line)
            if r.get("k") == "pkt":
                seen.append(r["id"])
                where[r["id"]] = os.path.basename(p)
    cells = [
        (where.get("A") == "seg_0915.ndjson.gz", "09:19:59.9 -> %s" % where.get("A")),
        (where.get("B") == "seg_0920.ndjson.gz", "09:20:00.0 -> %s" % where.get("B")),
        (sorted(map(str, seen)) == sorted(map(str, sent)),
         "%d sent, %d read back from %d gz files (multiset equal: %s)"
         % (len(sent), len(seen), len(closed), sorted(map(str, seen)) == sorted(map(str, sent)))),
        (len(closed) == 6, "files: %s" % [os.path.basename(p) for p in closed]),
    ]
    return cells


def _seg_file(spool, name="seg_0915.ndjson.gz", body=b"x" * 1000):
    d = os.path.join(spool, "NIFTY", DAY)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    with open(p, "wb") as fh:
        fh.write(body)
    return p


def g_upload_verify():
    from services.tape_runner.uploader import Uploader
    cells = []
    # good ETag: deleted only after a put that saw the file
    root = tmpdir()
    spool = os.path.join(root, "spool")
    p = _seg_file(spool)
    md5 = hashlib.md5(open(p, "rb").read()).hexdigest()
    s3 = FakeS3("ok")
    u = Uploader(s3, "b", spool, os.path.join(root, "manifest"))
    u.enqueue(p)
    u.process_once(0)
    put = s3.puts[0] if s3.puts else {}
    cells.append((not os.path.exists(p) and put.get("existed") is True and put.get("md5") == md5
                  and s3.objects.get("NIFTY/%s/seg_0915.ndjson.gz" % DAY) is not None and put.get("sse") == "AES256",
                  "good ETag: file gone=%s, put saw the file=%s, key=%s" % (not os.path.exists(p), put.get("existed"), put.get("key"))))
    man = u.manifest_lines(DAY)
    cells.append((len(man) == 1 and man[0]["md5"] == md5 and man[0]["attempts"] == 1,
                  "manifest row: %s" % (man[0] if man else None)))
    # corrupted ETag: file kept, retried with backoff, then shipped when S3 answers correctly
    root = tmpdir()
    spool = os.path.join(root, "spool")
    p = _seg_file(spool)
    s3 = FakeS3("corrupt")
    u = Uploader(s3, "b", spool, os.path.join(root, "manifest"))
    u.enqueue(p)
    u.process_once(0)
    kept1 = os.path.exists(p)
    u.process_once(int(0.5e9))           # not yet due (backoff 1 s)
    n_puts_early = len(s3.puts)
    u.process_once(int(1.0e9))           # due: second attempt, still corrupt
    kept2 = os.path.exists(p)
    s3.mode = "ok"
    u.process_once(int(3.0e9))           # backoff 2 s -> due at 3 s
    cells.append((kept1 and kept2 and n_puts_early == 1 and len(s3.puts) == 3 and not os.path.exists(p)
                  and u.counts["NIFTY"]["retried"] == 1 and u.counts["NIFTY"]["failed_attempts"] == 2,
                  "corrupt ETag: kept after 1st=%s, 2nd=%s; puts=%d (early=%d); shipped on 3rd=%s; counts=%s"
                  % (kept1, kept2, len(s3.puts), n_puts_early, not os.path.exists(p), u.counts.get("NIFTY"))))
    # exception: file kept
    root = tmpdir()
    spool = os.path.join(root, "spool")
    p = _seg_file(spool)
    u = Uploader(FakeS3("fail"), "b", spool, os.path.join(root, "manifest"))
    u.enqueue(p)
    u.process_once(0)
    cells.append((os.path.exists(p) and u.pending() == [p], "S3 exception: file kept and queued"))
    return cells


def g_subs_grow_only():
    rec, clock, tickers = make_recorder()
    t = boot_open_day(rec, clock, tickers)
    original = set(t.subscribed)
    n_open = len(original)
    # NIFTY moves 14 listed strikes (700 pts) -> window must grow
    clock.set(ist_ns(DAY, "09:30:01"))
    t.on_ticks(t, [idx_pkt("NIFTY", 25700.0, DAY, "09:30:01")])
    rec.step(clock.now_ns())
    after = set(t.subscribed)
    unsub = [c for c in t.calls if c[0] == "unsubscribe"]
    new_atm_ce = TOK[("NIFTY", 25700, "CE")]
    far_new = TOK[("NIFTY", 25700 + 50 * 20, "PE")]
    # a reconnect re-sends the full set, never a subset
    t.on_close(t, 1006, "drop")
    t.on_connect(t, {})
    resent = [c for c in t.calls if c[0] == "subscribe"][-1][1]
    run_to_stop(rec, clock)
    subs_objs = sorted(k for k in rec.uploader.s3.objects if "/subscriptions_" in k)
    last = json.loads(rec.uploader.s3.objects[subs_objs[-1]]) if subs_objs else {"tokens": []}
    toks_in_json = {r["token"]: r for r in last["tokens"]}
    all_have_minute = all(re.fullmatch(r"\d\d:\d\d", r.get("added_minute") or "") for r in last["tokens"])
    grown = [r for r in last["tokens"] if r.get("reason") == "grow"]
    return [
        (n_open == 4 + 82 + 62, "open: %d tokens subscribed (4 idx/fut + 82 NIFTY + 62 SENSEX expected 148)" % n_open),
        (original <= after and new_atm_ce in after and far_new in after,
         "after a 14-strike move: original window kept=%s, new ATM + far edge added=%s, total=%d"
         % (original <= after, new_atm_ce in after and far_new in after, len(after))),
        (not unsub, "unsubscribe calls: %d" % len(unsub)),
        (set(resent) == after, "reconnect re-sent %d tokens (full set %d)" % (len(resent), len(after))),
        (set(toks_in_json) == after and all_have_minute and grown and all(r["added_minute"] == "09:30" for r in grown),
         "%s: %d tokens, every one with added_minute=%s, %d added at 09:30 by grow"
         % (subs_objs[-1].split("/")[-1] if subs_objs else None, len(toks_in_json), all_have_minute, len(grown))),
    ]


def g_ctl_records():
    rec, clock, tickers = make_recorder()
    t = boot_open_day(rec, clock, tickers)
    fut = TOK[("NIFTY", "FUT")]
    clock.set(ist_ns(DAY, "10:00:00"))
    t.on_ticks(t, [full_pkt(fut, 25100, 1000, DAY, "10:00:00", tid="before")])
    clock.set(ist_ns(DAY, "10:00:05"))
    t.on_close(t, 1006, "connection lost access_token=SECRETTOKEN")
    clock.set(ist_ns(DAY, "10:00:07"))
    t.on_reconnect(t, 1)
    clock.set(ist_ns(DAY, "10:00:09"))
    t.on_connect(t, {})
    clock.set(ist_ns(DAY, "10:00:10"))
    t.on_ticks(t, [full_pkt(fut, 25101, 1075, DAY, "10:00:10", tid="after")])
    rec.step(clock.now_ns())
    assert run_to_stop(rec, clock) == 0
    recs = [r for _, r in s3_records(rec.uploader.s3, "NIFTY/")]
    ctls = [r["ctl"] for r in recs if r.get("k") == "ctl"]
    tids = [r.get("tid") for r in recs if r.get("k") == "pkt" and r.get("tid")]
    order = [r.get("ctl") or r.get("tid") for r in recs if r.get("ctl") in ("disconnect", "reconnect", "connect")
             or r.get("tid")]
    raw = b"".join(rec.uploader.s3.objects.values())
    leaked = any(gzip.decompress(v).find(b"SECRETTOKEN") >= 0 for k, v in rec.uploader.s3.objects.items()
                 if k.endswith(".gz")) or b"SECRETTOKEN" in raw
    rep = json.loads(rec.uploader.s3.objects["session/%s/daily_report_%s.json" % (DAY, DAY)])
    return [
        ("disconnect" in ctls and "reconnect" in ctls, "ctl records in NIFTY segments: %s" % sorted(set(ctls))),
        (order[-4:] == ["disconnect", "reconnect", "connect", "after"] and tids == ["before", "after"],
         "sequence %s; packets recorded around the drop: %s" % (order[-5:], tids)),
        (not leaked, "token text redacted from ctl reasons: %s" % (not leaked)),
        (rep["reconnects"] == 1 and rep["disconnects"] == 1, "report reconnects=%d disconnects=%d"
         % (rep["reconnects"], rep["disconnects"])),
    ]


def g_spool_cap():
    cap = 50 * 1024 * 1024
    rec, clock, tickers = make_recorder(s3=FakeS3("fail"), cap=cap)
    t = boot_open_day(rec, clock, tickers)
    fut = TOK[("NIFTY", "FUT")]
    rnd = random.Random(7)
    blob = lambda: "%032x" % rnd.getrandbits(128) * 64            # 2 KB, poorly compressible
    sent, code, i, vol = [], None, 0, 0
    t0 = ist_ns(DAY, "09:20:00")
    while code is None and i < 40_000:
        ns = t0 + i * 10_000_000                                   # 100 packets/s -> segments rotate
        clock.set(ns)
        batch = []
        for _ in range(50):
            vol += 75
            batch.append(full_pkt(fut, 25000, vol, DAY, "09:20:00", tid=i, pad=blob()))
            sent.append(i)
            i += 1
        t.on_ticks(t, batch)
        code = rec.step(clock.now_ns())
    on_disk = []
    for dp, _, files in os.walk(rec.spool):
        for f in files:
            p = os.path.join(dp, f)
            opener = gzip.open if f.endswith(".gz") else open
            if f.endswith(".gz") or f.endswith(".part"):
                for line in opener(p, "rt"):
                    r = json.loads(line)
                    if r.get("k") == "pkt" and r.get("tid") is not None:
                        on_disk.append(r["tid"])
    hb = json.load(open(rec.heartbeat_path))
    return [
        (code == 75, "exit code %s after %d packets (cap 50 MB, S3 always failing)" % (code, len(sent))),
        (sorted(on_disk) == sent, "every packet still on disk: %d of %d" % (len(on_disk), len(sent))),
        (hb["state"] == "SPOOL_CAP", "heartbeat state=%s" % hb["state"]),
    ]


def _unit_text():
    return open(os.path.join(ROOT, "services", "tape_runner", "tape-runner.service")).read()


def _directives(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", ";", "[")) and "=" in line:
            k, v = line.split("=", 1)
            out.append((k.strip(), v.strip()))
    return out


def g_token_fail():
    rec, clock, tickers = make_recorder(kite=FakeKite(profile_fails=True))
    code = rec.step(clock.now_ns())
    hb = json.load(open(rec.heartbeat_path))
    rpes = [v for k, v in _directives(_unit_text()) if k == "RestartPreventExitStatus"]
    has78 = any("78" in v.split() for v in rpes)
    return [
        (code == 78, "failing profile() -> exit %s" % code),
        (hb["state"] == "TOKEN_FAIL" and not tickers, "heartbeat %s; ticker created=%s" % (hb["state"], bool(tickers))),
        (has78, "unit RestartPreventExitStatus=%s contains 78: %s" % (rpes, has78)),
    ]


def g_closed_day():
    rec, clock, tickers = make_recorder()
    assert rec.step(clock.now_ns()) is None
    clock.set(ist_ns(DAY, "08:55"))
    rec.step(clock.now_ns())
    t = tickers[0]
    t.on_connect(t, {})
    base = set(t.subscribed)
    clock.set(ist_ns(DAY, "08:55:02"))
    t.on_ticks(t, [idx_pkt("NIFTY", 25000, PREV, "15:30:00"), idx_pkt("SENSEX", 80000, PREV, "15:30:00"),
                   full_pkt(TOK[("NIFTY", "FUT")], 25100, 5000, PREV, "15:29:59"),
                   full_pkt(TOK[("SENSEX", "FUT")], 80100, 5000, PREV, "15:29:59")])
    code = None
    for hm in ("09:00", "09:05", "09:10", "09:15", "09:16"):
        clock.set(ist_ns(DAY, hm))
        code = rec.step(clock.now_ns())
        if code is not None:
            break
    opt_tokens = {v for k, v in TOK.items() if len(k) == 3}
    subscribed_opts = (t.subscribed - base) & opt_tokens
    key = "session/%s/CLOSED" % DAY
    body = json.loads(rec.uploader.s3.objects[key]) if key in rec.uploader.s3.objects else None
    cells = [
        (code == 0, "exit %s at %s" % (code, hm)),
        (body is not None and body.get("verdict") == "CLOSED", "CLOSED uploaded: %s" % body),
        (not subscribed_opts, "option tokens subscribed: %d" % len(subscribed_opts)),
    ]
    # absence is not a verdict: no packets at all and quote fails -> NOT closed, options subscribed
    rec2, clock2, tick2 = make_recorder(kite=FakeKite(quote_fails=True))
    rec2.step(clock2.now_ns())
    clock2.set(ist_ns(DAY, "08:55"))
    rec2.step(clock2.now_ns())
    tick2[0].on_connect(tick2[0], {})
    clock2.set(ist_ns(DAY, "09:16"))
    code2 = rec2.step(clock2.now_ns())
    cells.append((code2 is None and len(tick2[0].subscribed) == 148
                  and "session/%s/CLOSED" % DAY not in rec2.uploader.s3.objects,
                  "no packets + quote fails -> not closed (exit %s), %d tokens" % (code2, len(tick2[0].subscribed))))
    return cells


FENCE = [("User", "tape"), ("EnvironmentFile", "/etc/tape/kite_api.env"),
         ("EnvironmentFile", "/etc/tape/kite_token.env"), ("EnvironmentFile", "/etc/tape/aws.env"),
         ("MemoryMax", "400M"), ("CPUWeight", "20"), ("Nice", "10"), ("LimitAS", "2000000000"),
         ("WorkingDirectory", "/var/lib/tape"), ("Restart", "on-failure"), ("RestartSec", "10"),
         ("RestartPreventExitStatus", "78 75"), ("ReadWritePaths", "/var/lib/tape"),
         ("ProtectSystem", "strict"), ("NoNewPrivileges", "true")]


def g_fence():
    d = _directives(_unit_text())
    missing = [f for f in FENCE if f not in d]
    exec_ok = ("ExecStart", "/var/lib/tape/venv/bin/python -m services.tape_runner") in d
    timer = open(os.path.join(ROOT, "services", "tape_runner", "tape-runner.timer")).read()
    td = _directives(timer)
    no_opt = "/opt/tape" not in _unit_text()
    return [
        (not missing, "unit directives missing: %s" % (missing or "none")),
        (exec_ok and no_opt, "ExecStart uses /var/lib/tape/venv: %s; no /opt/tape: %s" % (exec_ok, no_opt)),
        (("OnCalendar", "Mon..Fri *-*-* 08:50:00 Asia/Kolkata") in td and ("Persistent", "true") in td
         and "[Install]" not in [l.strip() for l in _unit_text().splitlines()], "timer weekday 08:50 IST persistent; unit has no [Install]"),
    ]


BAD_IMPORT = re.compile(r"^(supabase|psycopg2?|dhan.*|requests|merdian_compute|core|dotenv)$")
BAD_TEXT = ("postgres://", "postgresql://", "supabase.co", "place_order", "modify_order", "cancel_order")


def g_no_db_no_dhan():
    base = os.path.join(ROOT, "services", "tape_runner")
    bad_imp, bad_txt, n = [], [], 0
    for f in sorted(os.listdir(base)):
        p = os.path.join(base, f)
        if not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8").read()
        n += 1
        for s in BAD_TEXT:
            if s in text:
                bad_txt.append("%s: %s" % (f, s))
        if f.endswith(".py"):
            for node in ast.walk(ast.parse(text)):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    mods = [node.module or ""]
                for m in mods:
                    if BAD_IMPORT.match(m.split(".")[0]):
                        bad_imp.append("%s: %s" % (f, m))
    return [(n >= 10 and not bad_imp and not bad_txt,
             "%d files; forbidden imports %s; forbidden strings %s" % (n, bad_imp or "none", bad_txt or "none"))]


GUARDS = [("classify-synthetic", g_classify_synthetic), ("classify-purity", g_classify_purity),
          ("segments-rotate", g_segments_rotate), ("upload-verify", g_upload_verify),
          ("subs-grow-only", g_subs_grow_only), ("ctl-records", g_ctl_records), ("spool-cap", g_spool_cap),
          ("token-fail", g_token_fail), ("closed-day", g_closed_day), ("fence", g_fence),
          ("no-db-no-dhan", g_no_db_no_dhan)]


# ======================================================================== unit checks (not guards)
def u_timestamps_two_tz():
    code = ("import sys;sys.path.insert(0,%r);from datetime import datetime;"
            "from services.tape_runner.serialize import to_ist_iso;"
            "print(to_ist_iso(datetime.fromtimestamp(%d)))" % (ROOT, ist_ns(DAY, "09:25") // 10**9))
    outs = {}
    for tz in ("UTC", "Asia/Kolkata", "America/New_York"):
        env = dict(os.environ, TZ=tz)
        outs[tz] = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True).stdout.strip()
    want = "2026-11-02T09:25:00+05:30"
    return [(set(outs.values()) == {want}, "epoch of 09:25 IST rendered %s (want %s)" % (outs, want))]


def u_gzip_deterministic():
    from services.tape_runner.segments import gzip_file
    d = tmpdir()
    src = os.path.join(d, "a.part")
    open(src, "w").write("line\n" * 1000)
    a = open(gzip_file(src, os.path.join(d, "a.gz")), "rb").read()
    os.utime(src, (1, 1))
    b = open(gzip_file(src, os.path.join(d, "b.gz")), "rb").read()
    return [(a == b and gzip.decompress(a) == b"line\n" * 1000, "gzip bytes identical across runs/mtimes: %s" % (a == b))]


def u_resolve():
    from services.tape_runner.instruments import resolve
    u = resolve(FakeKite(), date(2026, 11, 2))
    n, s = u.symbols["NIFTY"], u.symbols["SENSEX"]
    ok = (n.index.token == 256265 and s.index.token == 265 and n.future.token == TOK[("NIFTY", "FUT")]
          and all(i.expiry == "2026-11-04" for i in n.options.values()) and len(n.strikes) == 121
          and len(n.window_tokens(n.atm_pos(25010))) == 82 and len(s.window_tokens(s.atm_pos(80000))) == 62)
    u2 = resolve(FakeKite(), date(2026, 11, 4))          # expiry day: front is today
    u3 = resolve(FakeKite(), date(2026, 11, 5))          # day after: next weekly
    return [(ok, "front expiry 2026-11-04, front future, windows 82/62, decoy name excluded"),
            (u2.symbols["NIFTY"].options[(25000.0, "CE")].expiry == "2026-11-04"
             and u3.symbols["NIFTY"].options[(25000.0, "CE")].expiry == "2026-11-11", "expiry-day and day-after roll")]


def u_restart_state():
    root = tmpdir()
    rec, clock, tickers = make_recorder(root=root)
    t = boot_open_day(rec, clock, tickers)
    clock.set(ist_ns(DAY, "10:00:00"))
    t.on_ticks(t, [full_pkt(TOK[("NIFTY", "FUT")], 25000, 100, DAY, "10:00:00")])
    rec.step(clock.now_ns())
    n_before = len(rec.subscribed)
    pk = rec.stats.packets["NIFTY"]
    # process dies; a new one starts at 11:00 on the same root
    from services.tape_runner.recorder import Recorder
    clock2 = ManualClock(ist_ns(DAY, "11:00:00"))
    tk = []
    rec2 = Recorder(FakeKite(), lambda: tk.append(FakeTicker()) or tk[-1], rec.uploader.s3, clock2, root=root,
                    bucket="b", threaded=False, log=lambda m: None)
    rec2.step(clock2.now_ns())
    tk[0].on_connect(tk[0], {})
    return [(rec2.stats.packets["NIFTY"] == pk and len(rec2.stats.restarts) == 1 and rec2.options_on
             and tk[0].subscribed == set(rec.subscribed) and len(rec2.subscribed) == n_before,
             "restart resumes counters (%d pkts), restores %d subscriptions, restarts=%d"
             % (rec2.stats.packets["NIFTY"], len(tk[0].subscribed), len(rec2.stats.restarts)))]


def u_report_gaps_and_skew():
    rec, clock, tickers = make_recorder()
    t = boot_open_day(rec, clock, tickers)
    sfut = TOK[("SENSEX", "FUT")]
    fut = TOK[("NIFTY", "FUT")]
    sec = ist_ns(DAY, "09:15:00")
    vol = 0
    plan = []
    s = 0
    while s < 6 * 3600 + 15 * 60:
        plan.append(s)
        s += 12 if s == 3600 else (75 if s == 7202 else 5)   # one 12 s and one 75 s gap planted
    for s in plan:
        ns = sec + s * 10**9 + 400_000_000                    # receive 0.4 s after the exchange second
        clock.set(ns)
        hms = (datetime(2026, 11, 2, 9, 15) + timedelta(seconds=s)).strftime("%H:%M:%S")
        vol += 75
        t.on_ticks(t, [full_pkt(fut, 25000, vol, DAY, hms), full_pkt(sfut, 80000, vol, DAY, hms)])
        if s % 60 == 0:
            rec.step(ns)
    run_to_stop(rec, clock)
    rep = json.loads(rec.uploader.s3.objects["session/%s/daily_report_%s.json" % (DAY, DAY)])
    n = rep["symbols"]["NIFTY"]
    g10 = [g["seconds"] for g in n["feed_gaps_gt10s"]]
    g60 = [g["seconds"] for g in n["feed_gaps_gt60s"]]
    sk = n["clock_skew"]
    man = rec.uploader.s3.objects.get("session/%s/MANIFEST.sha256" % DAY, b"").decode()
    keys_in_man = {l.split("  ")[1] for l in man.splitlines()}
    expect_keys = set(rec.uploader.s3.objects) - {"session/%s/MANIFEST.sha256" % DAY}
    # Rule 0: the skew check must be able to fail -- a naive IST wall time mislabelled as the
    # process zone (the TD-029 shape) has to read FAIL.
    from services.tape_runner.serialize import packet_record, skew_seconds
    from services.tape_runner.stats import skew_verdict
    recv = ist_ns(DAY, "10:00:00")
    wrong = full_pkt(fut, 1, 1, DAY, "10:00:00")
    wrong["exchange_timestamp"] = datetime(2026, 11, 2, 10, 0, 0) if os.environ.get("TZ", "UTC") != "Asia/Kolkata" \
        else datetime(2026, 11, 2, 4, 30, 0)
    bad = skew_seconds(packet_record(wrong, "NIFTY", "FUT", recv))
    return [
        (g10 == [12.0, 75.0] and g60 == [75.0], "gaps >10s %s, >60s %s" % (g10, g60)),
        (sk["verdict"] == "OK" and 0.3 <= sk["median_s"] <= 0.5 and sk["max_s"] < 1,
         "clock skew NIFTY median %s s max %.3f s n=%d verdict %s" % (sk["median_s"], sk["max_s"], sk["n"], sk["verdict"])),
        (skew_verdict(bad) == "FAIL", "mislabelled naive timestamp reads skew %.0f s -> %s" % (bad, skew_verdict(bad))),
        (keys_in_man == expect_keys and rep["closed"] is None and rep["classified"] is None,
         "MANIFEST.sha256 lists %d keys = every uploaded object incl. the report" % len(keys_in_man)),
        (all(k in n for k in ("packets", "packets_per_minute", "reconnects", "uploads", "spool_high_water_bytes",
                              "subscribed_count", "last_packet_ist", "clock_skew")), "report per-symbol fields present"),
    ]


def u_smoke_skew_fails_loudly():
    from services.tape_runner.smoke import run_smoke

    class T(FakeTicker):
        def __init__(self, ts_fn):
            super().__init__()
            self.ts_fn = ts_fn

        def connect(self, threaded=False, **kw):
            self.on_connect(self, {})
            self.on_ticks(self, [idx_pkt("NIFTY", 25000, DAY, "10:00:00", exchange_timestamp=self.ts_fn())])

    cells = []
    for label, fn, want in (("correct", lambda: kite_naive(DAY, "10:00:00"), 0),
                            ("ist-wall-time-as-local", lambda: datetime(2026, 11, 2, 10, 0, 0)
                             if os.environ.get("TZ", "UTC") != "Asia/Kolkata" else datetime(2026, 11, 2, 4, 30), 3)):
        out = []
        code = run_smoke(FakeKite(), lambda: T(fn), ManualClock(ist_ns(DAY, "10:00:01")), wait_s=0, out=out.append)
        skew_lines = [l for l in out if "CLOCK_SKEW NIFTY" in l]
        cells.append((code == want and skew_lines and (want == 0 or any("SMOKE FAIL: CLOCK SKEW" in l for l in out)),
                      "smoke %s: exit %s; %s" % (label, code, skew_lines[0] if skew_lines else "no skew line")))
    return cells


UNITS = [u_timestamps_two_tz, u_gzip_deterministic, u_resolve, u_restart_state, u_report_gaps_and_skew,
         u_smoke_skew_fails_loudly]


def main():
    results = []
    guards = [(n, f) for n, f in GUARDS if ARGS.only in (None, n)]
    for name, fn in guards:
        try:
            cells = fn()
            ok = bool(cells) and all(c[0] for c in cells)
        except Exception:
            cells = [(False, "EXCEPTION " + traceback.format_exc().strip().splitlines()[-1])]
            ok = False
        results.append((name, ok))
        print("%s %s" % ("PASS" if ok else "FAIL", name))
        for c in cells:
            print("    [%s] %s" % ("ok" if c[0] else "XX", c[1]))
    unit_ok = unit_n = 0
    if ARGS.only is None:
        for fn in UNITS:
            try:
                cells = fn()
            except Exception:
                cells = [(False, "EXCEPTION " + traceback.format_exc().strip().splitlines()[-1])]
            for c in cells:
                unit_n += 1
                unit_ok += bool(c[0])
                print("    unit %s [%s] %s" % (fn.__name__, "ok" if c[0] else "XX", c[1]))
    for d in TMP:
        shutil.rmtree(d, ignore_errors=True)
    g_ok = sum(1 for _, ok in results if ok)
    passed = g_ok == len(results) and unit_ok == unit_n and results
    print("TAPE T0 %s (%d/%d guards, %d/%d unit checks)" % ("PASS" if passed else "FAIL", g_ok, len(results),
                                                         unit_ok, unit_n))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
