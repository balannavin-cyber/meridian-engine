"""Stream rebuild of recorded tape segments into classified volume (tape phase T1a, plan D-2 to D-5, D-7).

PURE: stdlib only, no clock, no randomness, no I/O. The CLI feeds raw bytes lines in, one segment file at
a time, and calls end_group() after each 5-minute slot. This module never reads a file.

Ordering. The packets of one symbol are ordered by (exchange epoch, recv_ns, sha256 of the raw line):
a total order that depends only on line content, so file order, line order inside a file and collision
copies of the same line cannot change the result. A reorder buffer holds the last ten minutes and releases
packets older than (slot start - 600 s) in that order.

Volume. A volume delta between two consecutive chain packets of one token ends in exactly one of BUY,
SELL, UNCL (merdian_compute.tape.classify, unchanged) or GAP (a disconnect / reconnect / connect control
record lies between the two packets). A packet whose cumulative volume is BELOW the token's previous
chain packet is a stale snapshot: it is counted under volume_regression and never becomes the new
previous packet. Every excluded packet is counted per reason and hour; none is dropped silently.
"""
import bisect
import hashlib
import heapq
import json
import re
from collections import namedtuple
from datetime import datetime
from functools import lru_cache

from . import classify as C
from . import minute as M

SEG_RE = re.compile(r"^seg_(\d{4})(?:_c(\d+))?(?:_r(\d+))?\.ndjson\.gz$")
SUB_RE = re.compile(r"^subscriptions_(\d{6})(?:_(\d+))?\.json$")
GAP_KINDS = ("disconnect", "reconnect", "connect")
CTL_COUNTED = ("connect", "disconnect", "reconnect", "watchdog")   # distinct (kind, recv_ns) per symbol file
WATERMARK_S = 600

Pkt = namedtuple("Pkt", "token ex recv vol ltp atp bid ask bq aq oi exts mn bk dg")


def parse_seg_name(name):
    m = SEG_RE.match(name)
    if not m:
        return None
    return (m.group(1), int(m.group(2) or 0), int(m.group(3) or 0))


def order_segments(paths):
    """Segment files in processing order: (HHMM, _cN, _rN, name). Names that are not segments are dropped."""
    keyed = []
    for p in paths:
        base = re.split(r"[\\/]", p)[-1]
        k = parse_seg_name(base)
        if k is not None:
            keyed.append((k, base, p))
    keyed.sort()
    return [p for _, _, p in keyed]


def sub_sort_key(name):
    m = SUB_RE.match(name)
    return (0, m.group(1), int(m.group(2) or 1), name) if m else (1, "", 0, name)


_META_FIELDS = ("token", "sym", "role", "strike", "opt_type", "tradingsymbol", "expiry")


def build_token_map(items):
    """items: [(file name, parsed json)]. Files in name order; the first file naming a token fixes it."""
    meta, conflicts = {}, []
    for name, doc in sorted(items, key=lambda it: sub_sort_key(it[0])):
        for row in doc.get("tokens", []):
            try:
                tok = int(row["token"])
            except (KeyError, TypeError, ValueError):
                continue
            m = {k: row.get(k) for k in _META_FIELDS}
            m["token"] = tok
            if isinstance(m["strike"], (int, float)) and not isinstance(m["strike"], bool):
                m["strike"] = float(m["strike"])
            old = meta.get(tok)
            if old is None:
                meta[tok] = m
            elif old != m:
                conflicts.append({"token": tok, "file": name, "fields": sorted(k for k in _META_FIELDS if old[k] != m[k])})
    return meta, conflicts


@lru_cache(maxsize=8192)
def _epoch(s):
    return datetime.fromisoformat(s).timestamp()


def _num(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return x


def _lvl_price(levels):
    if not levels or not isinstance(levels, list):
        return None
    lvl = levels[0]
    return _num(lvl.get("price")) if isinstance(lvl, dict) else None


def _sum_qty(levels):
    if not isinstance(levels, list):
        return None
    t = 0
    for lvl in levels[:5]:
        q = _num(lvl.get("quantity")) if isinstance(lvl, dict) else None
        if q is not None:
            t += q
    return t


def _recv_bucket(rec, win=None):
    ri = rec.get("recv_ist")
    return M.bucket_of(ri[11:16], win) if isinstance(ri, str) and len(ri) >= 16 else "unknown"


def parse_line(raw, day, win=None):
    """One raw line -> ("bad"|"other", None) | ("ctl", (kind, recv_ns, rec)) | ("drop", (reason, bucket))
    | ("pkt", Pkt)."""
    try:
        rec = json.loads(raw)
    except ValueError:
        return "bad", None
    if not isinstance(rec, dict):
        return "bad", None
    k = rec.get("k")
    rn = rec.get("recv_ns")
    if k == "ctl":
        if isinstance(rn, int) and not isinstance(rn, bool):
            return "ctl", (rec.get("ctl"), rn, rec)
        return "bad", None
    if k != "pkt":
        return "other", None
    tok = rec.get("instrument_token")
    if isinstance(tok, bool) or not isinstance(tok, int) or isinstance(rn, bool) or not isinstance(rn, int):
        return "bad", None
    exts = rec.get("exchange_timestamp")
    if not isinstance(exts, str) or len(exts) < 16:
        return "drop", ("no_exchange_ts", _recv_bucket(rec, win), tok)
    if exts[:10] != day:
        return "drop", ("stale_date", _recv_bucket(rec, win), tok)
    try:
        ex = _epoch(exts)
    except ValueError:
        return "drop", ("no_exchange_ts", _recv_bucket(rec, win), tok)
    depth = rec.get("depth")
    buy = sell = None
    if isinstance(depth, dict):
        buy, sell = depth.get("buy"), depth.get("sell")
    mn = exts[11:16]
    return "pkt", Pkt(tok, ex, rn, _num(rec.get("volume_traded")), _num(rec.get("last_price")),
                      _num(rec.get("average_traded_price")), _lvl_price(buy), _lvl_price(sell),
                      _sum_qty(buy), _sum_qty(sell), _num(rec.get("oi")), exts, mn, M.bucket_of(mn, win),
                      hashlib.sha256(raw).digest()[:16])


def mini(p):
    """The five fields classify() reads, as the nested dict it expects."""
    return {"volume_traded": p.vol, "last_price": p.ltp, "average_traded_price": p.atp,
            "depth": {"buy": [{"price": p.bid}], "sell": [{"price": p.ask}]}}


class SymbolReplay:
    def __init__(self, sym, day, meta, win=None):
        self.sym, self.day = sym, day
        self.win = win                       # (open, close) "HH:MM" on a special session, else None
        self.ctl_n = {k: 0 for k in CTL_COUNTED}
        self.meta = {t: m for t, m in meta.items() if m.get("sym") == sym}
        self.strikes = sorted({m["strike"] for m in self.meta.values()
                               if m["role"] == "OPT" and m.get("strike") is not None})
        self.sidx = {k: i for i, k in enumerate(self.strikes)}
        self.heap, self.seq = [], 0
        self.state, self.last_key = {}, {}
        self.book, self.g3 = M.MinuteBook(), M.G3Book()
        self.events, self.ev_set, self.errors, self.procs = [], set(), [], set()
        self.err_set = set()
        self.idx_price, self._atm = None, (None, None)
        self.seen = set()
        self.seen_ctl = set()
        self.c = dict(lines=0, pkt_lines=0, ctl_lines=0, bad_lines=0, other_lines=0, chain_pkts=0, index_pkts=0,
                      gap_pairs=0)
        self.gap_qty = 0
        self.baseline_qty = 0

    # -- intake --------------------------------------------------------------------
    def disc(self, reason, bucket):
        self.g3.disc(reason, bucket)

    def feed(self, raw):
        self.c["lines"] += 1
        kind, val = parse_line(raw, self.day, self.win)
        if kind == "bad":
            self.c["bad_lines"] += 1
            self.disc("bad_line", "unknown")
            return
        if kind == "other":
            self.c["other_lines"] += 1
            return
        if kind == "ctl":
            self.c["ctl_lines"] += 1
            self._ctl(*val)
            return
        self.c["pkt_lines"] += 1
        if kind == "drop":
            self.disc(val[0], val[1])
            return
        if val.token not in self.meta:
            self.disc("unmapped_token", val.bk)
            return
        self.seen.add(val.token)
        heapq.heappush(self.heap, (val.ex, val.recv, val.dg, self.seq, val))
        self.seq += 1

    def _ctl(self, kind, rn, rec):
        if kind == "watchdog":
            if ("watchdog", rn) not in self.seen_ctl:
                self.seen_ctl.add(("watchdog", rn))
                self.ctl_n["watchdog"] += 1       # not a gap event: the disconnect that follows is
        if kind in GAP_KINDS and (kind, rn) not in self.ev_set:
            self.ctl_n[kind] += 1
            self.ev_set.add((kind, rn))
            bisect.insort(self.events, rn)
        if kind == "connect" and isinstance(rec.get("process_start_ns"), int):
            self.procs.add(rec["process_start_ns"])
        if kind == "error" and (rn, rec.get("code"), rec.get("reason")) not in self.err_set:
            self.err_set.add((rn, rec.get("code"), rec.get("reason")))
            self.errors.append({"recv_ns": rn, "code": rec.get("code"), "reason": rec.get("reason")})

    def end_group(self, hhmm):
        wm = _epoch("%sT%s:%s:00+05:30" % (self.day, hhmm[:2], hhmm[2:])) - WATERMARK_S
        self._release(wm)

    def _release(self, wm):
        while self.heap and self.heap[0][0] < wm:
            self._chain(heapq.heappop(self.heap)[4])

    # -- chain ---------------------------------------------------------------------
    def _gap_between(self, a, b):
        lo, hi = (a.recv, b.recv) if a.recv <= b.recv else (b.recv, a.recv)
        i = bisect.bisect_right(self.events, lo)
        return i < len(self.events) and self.events[i] <= hi

    def _atm_idx(self):
        p = self.idx_price
        if self._atm[0] != p:
            n = len(self.strikes)
            if not n:
                j = -999
            else:
                i = bisect.bisect_left(self.strikes, p)
                if i == 0:
                    j = 0
                elif i == n:
                    j = n - 1
                else:
                    j = i - 1 if p - self.strikes[i - 1] <= self.strikes[i] - p else i
            self._atm = (p, j)
        return self._atm[1]

    def _group(self, m):
        if m["role"] == "FUT":
            return "FUT"
        if self.idx_price is None:
            return "NO_ATM"
        k = self.sidx.get(m.get("strike"))
        ot = m.get("opt_type") if m.get("opt_type") in ("CE", "PE") else "CE"
        return ("ATM3_" if k is not None and abs(k - self._atm_idx()) <= 3 else "OTHER_") + ot

    def _book(self, m, pk, side, rule, qty, price):
        self.book.add(pk.token, pk.mn, side, qty, price)
        self.g3.add(pk.bk, self._group(m), side, rule, qty)

    def _chain(self, pk):
        tok = pk.token
        key = (pk.ex, pk.recv, pk.dg)
        last = self.last_key.get(tok)
        if last is not None:
            if key == last:
                self.disc("duplicate", pk.bk)
                return
            if key < last:
                self.disc("late_beyond_watermark", pk.bk)
                return
        self.last_key[tok] = key
        m = self.meta[tok]
        if m["role"] == "IDX":
            self.c["index_pkts"] += 1
            if pk.ltp is not None:
                self.idx_price = pk.ltp
            return
        if pk.vol is None:
            self.disc("no_volume", pk.bk)
            return
        st = self.state.get(tok)
        if st is not None and pk.vol < st[0].vol:
            self.disc("volume_regression", pk.bk)
            return
        self.c["chain_pkts"] += 1
        self.book.touch(tok, pk.mn, pk)
        if st is None:
            self.state[tok] = [pk, pk.vol, pk.vol]
            self.baseline_qty += int(pk.vol)
            return
        prev = st[0]
        dv = int(pk.vol - prev.vol)
        if self._gap_between(prev, pk):
            self.c["gap_pairs"] += 1
            if dv > 0:
                self.gap_qty += dv
                self._book(m, pk, "GAP", "gap", dv, None)
        elif dv > 0:
            tr = C.classify(mini(prev), mini(pk))
            rule = M.rule_of(prev, pk)
            M.check_rule(rule, tr.side)
            self._book(m, pk, tr.side, rule, tr.qty, tr.price)
        st[0] = pk
        st[2] = pk.vol

    # -- result --------------------------------------------------------------------
    def finish(self):
        self._release(float("inf"))
        cells, disc = self.g3.export()
        rows = self.book.rows(self.day, self.meta)
        spans = {t: [s[1], s[2]] for t, s in self.state.items()}
        accounted = self.c["chain_pkts"] + self.c["index_pkts"] + sum(
            n for r, bs in disc.items() if r != "bad_line" for n in bs.values())
        inv = M.check_invariants(rows, spans, self.c["pkt_lines"], accounted)
        nopkt = sorted(m.get("tradingsymbol") or "token:%d" % t for t, m in self.meta.items() if t not in self.seen)
        return {"sym": self.sym, "counters": dict(self.c), "discards": disc, "cells": cells, "rows": rows,
                "invariants": inv, "baseline_qty": self.baseline_qty, "tokens_no_packets": nopkt,
                "gaps": {"events": [{"kind": k, "recv_ns": r} for k, r in sorted(self.ev_set, key=lambda e: (e[1], e[0]))],
                         "gap_pairs": self.c["gap_pairs"], "gap_qty": self.gap_qty},
                "restarts": max(0, len(self.procs) - 1), "errors": sorted(self.errors, key=lambda e: e["recv_ns"]),
                "ctl_events": dict(self.ctl_n)}
