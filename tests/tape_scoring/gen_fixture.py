#!/usr/bin/env python3
"""Planted-truth generator for the tape scoring tests (docs/tape/scoring_plan.md section 2).

Writes the extract's exact CSV layout (<out>/<relation>/<day>.csv). The column layout is READ FROM scoring_extract.sql, so
the generator can only write what the extract would emit; tests/test_tape_scoring.py compares that layout with the one
score.py reads.

A Plan is one symbol-day. The plan IS the truth: each guard states what it planted and what the scorer must report.
  S sign   one designated strike-leg (first strike, CE) carries the net: S=+1 -> net sell (buy - sell = -1000, D > 0);
           S=-1 -> net buy. Classified share is planted with the unclassified quantity on the same leg. Other legs are zero.
  R        a spike of `rng` points at the label hm(T)+2, base elsewhere; straddle_atm is 100, so R = rng / 100.
           Cycles that carry a rng must be >= 30 minutes apart (their windows are then disjoint).
  U / roles  gex_cr is U/100 at every strike, U/2 at the leader, U/4 at the runner-up (a 'pin' strike gets +3/10), so
           sum(gex_cr) has the sign U and a magnitude BELOW 1 (the sign-only guard scales it by 1000).
Synthetic cumulative columns are not monotone across grid points: the scorer reads each grid point on its own.
"""
import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta
from fractions import Fraction

IDS = {"NIFTY": "9992f600-51b3-4009-b487-f878692a0bc5", "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71"}
FRONT = "2026-12-10"
NONFRONT = "2026-12-17"
RELS = ("tape_strike_cycle", "tape_events", "tape_chain_events", "tape_chain_runs", "tape_daily_report", "tape_minute",
        "gex_strike_snapshots", "gamma_metrics", "hist_spot_bars_1m")


def ts_ist(day, secs):
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    return "%sT%02d:%02d:%02d+05:30" % (day, h, m, s)


def ts_utc(day, secs):
    d = datetime.strptime(day, "%Y-%m-%d") + timedelta(seconds=secs) - timedelta(hours=5, minutes=30)
    return d.strftime("%Y-%m-%d %H:%M:%S") + ".123456+00"  # engine timestamps carry a fraction; tape_chain_runs.ts_ist does not


def parse_layout(sql_path):
    with open(sql_path, encoding="utf-8") as fh:
        text = fh.read()
    out = {}
    for m in re.finditer(r"--\s*@name\s+(\w+)\s*\nSELECT\s+(.*?)\s+FROM\s+public\.(\w+)", text, re.S):
        name, cols, _ = m.groups()
        out[name] = [c.strip() for c in cols.replace("\n", " ").split(",")]
    return out


class Plan:
    def __init__(self, sym, day, expiry=FRONT, minutes=375, late_share="70.0", restart_at=None, daily_report=True,
                 spot="ok", gex_scale=1, gamma_scale=1, nonfront=False, close_1529=None, base=22000, straddle=100,
                 unsub=()):
        self.sym, self.day, self.expiry = sym, day, expiry
        self.minutes, self.late_share, self.restart_at, self.daily_report = minutes, late_share, restart_at, daily_report
        self.spot, self.gex_scale, self.gamma_scale, self.nonfront = spot, gex_scale, gamma_scale, nonfront
        self.close_1529, self.base, self.straddle, self.unsub = close_1529, base, straddle, set(unsub)
        self.strikes = [Fraction(base + 50 * i) for i in range(-6, 6)]
        s = self.strikes
        self.roles = {"leader": s[3], "runner": s[7], "cw": s[8], "pw": s[4], "pin": None}
        self.runs, self.grid, self.chain, self.tape, self.drop = [], {}, [], [], set()

    def add_run(self, G, off=21, U=1, S=1, share=70, rng=None, tape=True, **roles):
        self.runs.append({"G": G, "off": off, "U": U, "rng": rng, "roles": dict(self.roles, **roles)})
        if tape:
            self.grid[G] = (-1000 if S == 1 else 1000, share)
        return self

    def add_chain(self, G, off, kind, K, merged_n=1):
        self.chain.append({"G": G, "off": off, "kind": kind, "K": Fraction(K), "merged_n": merged_n})
        self.grid.setdefault(G, (0, 100))
        return self

    def add_tape(self, secs, kind, strike, leg, side):
        self.tape.append({"secs": secs, "kind": kind, "strike": Fraction(strike), "leg": leg, "side": side})
        return self

    # ---- emission
    def rows(self):
        R = {r: [] for r in RELS}
        sym, day, s = self.sym, self.day, self.strikes
        rid = "load-%s" % day
        sub = [k for k in s if k not in self.unsub]
        for G in sorted(self.grid):
            net, share = self.grid[G]
            b0, s0 = max(net, 0), max(-net, 0)
            p = 0
            while ((b0 + s0 + 2 * p) * (100 - share)) % share:
                p += 1
            cls = b0 + s0 + 2 * p
            u = cls * (100 - share) // share
            for k in sub:
                for leg in ("CE", "PE"):
                    des = (k == sub[0] and leg == "CE")
                    R["tape_strike_cycle"].append({
                        "symbol": sym, "trading_day": day, "expiry": self.expiry, "strike": str(k), "leg": leg,
                        "ts_ist": ts_ist(day, G * 60), "buy_cum": b0 + p if des else 0, "sell_cum": s0 + p if des else 0,
                        "uncl_cum": u if des else 0, "gap_cum": 7 if des else 0,
                        "first_seen_ts_ist": ts_ist(day, 560 * 60), "run_id": rid})
            R["tape_strike_cycle"].append({  # a FUT row at every grid point: must be ignored
                "symbol": sym, "trading_day": day, "expiry": "", "strike": "", "leg": "FUT", "ts_ist": ts_ist(day, G * 60),
                "buy_cum": 5, "sell_cum": 5, "uncl_cum": 0, "gap_cum": 0, "first_seen_ts_ist": ts_ist(day, 560 * 60),
                "run_id": rid})
        labels_needed = set()
        for i, run in enumerate(self.runs):
            T = run["G"] * 60 + run["off"]
            rr = run["roles"]
            run_id = "%s-%s-%03d" % (sym, day, i)
            gsc = Fraction(1, 100) * self.gamma_scale
            for k in s:
                g = Fraction(run["U"], 100)
                if k == rr["leader"]:
                    g = Fraction(run["U"], 2)
                elif k == rr["runner"]:
                    g = Fraction(run["U"], 4)
                if rr["pin"] is not None and k == rr["pin"] and k != rr["leader"]:
                    g = Fraction(3, 10)
                R["gex_strike_snapshots"].append({
                    "run_id": run_id, "symbol": sym, "ts": ts_utc(day, T), "expiry_date": self.expiry, "strike": str(k),
                    "gamma_call": str(gsc), "gamma_put": str(gsc), "oi_call": 1000 if k == rr["cw"] else 10,
                    "oi_put": 1000 if k == rr["pw"] else 10, "gex_cr": str(g * self.gex_scale)})
                if self.nonfront:
                    R["gex_strike_snapshots"].append({
                        "run_id": run_id + "-nf", "symbol": sym, "ts": ts_utc(day, T), "expiry_date": NONFRONT,
                        "strike": str(k), "gamma_call": str(gsc), "gamma_put": str(gsc), "oi_call": 5, "oi_put": 5,
                        "gex_cr": str(g * self.gex_scale)})
            R["gamma_metrics"].append({"run_id": run_id, "symbol": sym, "ts": ts_utc(day, T), "expiry_date": self.expiry,
                                       "straddle_atm": self.straddle})
            R["tape_chain_runs"].append({
                "symbol": sym, "trading_day": day, "expiry": self.expiry, "ts_ist": ts_ist(day, T), "chain_run_id": run_id,
                "leader_strike": str(rr["leader"]), "call_wall": str(rr["cw"]), "put_wall": str(rr["pw"]),
                "net_sign": run["U"], "in_window": "t" if T >= 600 * 60 else "f", "run_id": rid})
        for e in self.chain:
            R["tape_chain_events"].append({
                "symbol": sym, "trading_day": day, "expiry": self.expiry, "kind": e["kind"],
                "ts_ist": ts_ist(day, e["G"] * 60 + e["off"]), "strike": str(e["K"]), "merged_n": e["merged_n"], "run_id": rid})
        for t in self.tape:
            R["tape_events"].append({
                "symbol": sym, "trading_day": day, "expiry": self.expiry, "strike": str(t["strike"]), "leg": t["leg"],
                "kind": t["kind"], "ts_ist": ts_ist(day, t["secs"]), "side": t["side"], "magnitude": "3.5", "run_id": rid})
        if self.daily_report:
            restarts = []
            if self.restart_at is not None:
                restarts.append({"prev_state": "TOKEN_FAIL", "process_start_ist": ts_ist(day, self.restart_at * 60)})
            R["tape_daily_report"].append({
                "symbol": sym, "trading_day": day, "classified_share_late": self.late_share,
                "report": json.dumps({"restarts": restarts}),
                "g3": '{"verdict_detail": {"late": {"share_pct": %s}}}' % self.late_share, "run_id": rid})
        for i in range(self.minutes):
            R["tape_minute"].append({"symbol": sym, "trading_day": day, "minute_ist": ts_ist(day, (555 + i) * 60), "run_id": rid})
        # spot bars
        bars = {}
        for run in self.runs:
            if run["rng"] is None:
                continue
            m0 = (run["G"] * 60 + run["off"]) // 60
            for m in range(m0 + 1, m0 + 31):
                bars.setdefault(m, [self.base, self.base, self.base])
            if run["rng"]:
                bars[m0 + 2][0] = self.base + run["rng"]
        if self.close_1529 is not None:
            bars.setdefault(929, [self.base, self.base, self.base])[2] = self.close_1529
        if self.spot != "none":
            for m in sorted(bars):
                if m in self.drop:
                    continue
                h, l, c = bars[m]
                label = m * 60 if self.spot == "ok" else None
                ts = ts_utc(self.day, m * 60) if self.spot == "ok" else "%s %02d:%02d:00+00" % (self.day, m // 60, m % 60)
                R["hist_spot_bars_1m"].append({"instrument_id": IDS[sym], "trade_date": day, "bar_ts": ts,
                                               "open": c, "high": h, "low": l, "close": c})
        return R


class Dataset:
    def __init__(self):
        self.plans = []

    def add(self, plan):
        self.plans.append(plan)
        return plan

    def write(self, out, sql_path, truth=None, manifest=False):
        layout = parse_layout(sql_path)
        by_day = {}
        for p in self.plans:
            for rel, rows in p.rows().items():
                by_day.setdefault(p.day, {r: [] for r in RELS})[rel] += rows
        for day, rels in by_day.items():
            for rel in RELS:
                os.makedirs(os.path.join(out, rel), exist_ok=True)
                with open(os.path.join(out, rel, day + ".csv"), "w", encoding="utf-8", newline="") as fh:
                    w = csv.DictWriter(fh, fieldnames=layout[rel], restval="", extrasaction="ignore", lineterminator="\n")
                    w.writeheader()
                    w.writerows(rels[rel])
        if truth is not None:
            with open(os.path.join(out, "FIXTURE_TRUTH.json"), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(truth, fh, sort_keys=True)
        if manifest:
            lines = []
            for rel in RELS:
                for f in sorted(os.listdir(os.path.join(out, rel))):
                    lines.append("%s\t%s/%s" % (hashlib.sha256(open(os.path.join(out, rel, f), "rb").read()).hexdigest(), rel, f))
            with open(os.path.join(out, "manifest.tsv"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(lines) + "\n")
        return out


def omnibus(null=False, ndays=22):
    """22 days x 2 symbols. Belief (stated before measuring): H-A YES both (planted delta 0.15 every day, 22 >= 20 days);
    H-B YES both on the planted fixture (308 events a symbol; kinds 0-2 matched at planted leads 20..34 min, kind 3 never); NO on --null."""
    ds = Dataset()
    rnd = random.Random(20261103)
    d0 = datetime(2026, 10, 5)
    for di in range(ndays):
        day = (d0 + timedelta(days=di)).strftime("%Y-%m-%d")
        for sym in ("NIFTY", "SENSEX"):
            p = ds.add(Plan(sym, day, base=22000 if sym == "NIFTY" else 72000))
            for i, G in enumerate(range(600, 870, 30)):
                p.add_run(G, 21, U=1, S=1 if i % 2 == 0 else -1, rng=30 if i % 2 == 0 else 45)
            for G in (560, 590, 890, 900):
                p.add_run(G, 21, U=1, S=1, rng=40)
            r = p.roles
            # kind 3 sits at a strike that is no role and has no tape events: uncovered by construction
            kinds = (("E1", r["runner"], "CE", True), ("E2-call", r["cw"], "CE", True), ("E2-put", r["pw"], "PE", True),
                     ("E2-call", p.strikes[9], "CE", False))
            for i in range(14):
                m = 660 + 4 * i
                G, off = (m // 5) * 5, (m % 5) * 60 + 10
                kind, K, leg, planted = kinds[i % 4]
                p.add_chain(G, off, kind, K)
                T = G * 60 + off
                if null:
                    for _ in range(2):
                        k2 = p.strikes[rnd.randrange(12)]
                        p.add_tape((T - rnd.randrange(5, 56) * 60) // 60 * 60, "CONC", k2, rnd.choice(("CE", "PE")), "buy")
                else:
                    if planted:
                        p.add_tape((T - (20 + i % 15) * 60) // 60 * 60, "CONC", K, leg, "buy")
                    for k2 in (p.strikes[0], p.strikes[11]):
                        for lg in ("CE", "PE"):
                            p.add_tape((T - 180) // 60 * 60, "CONC", k2, lg, "sell")
    return ds


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--null", action="store_true")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    a = ap.parse_args(argv)
    sql = os.path.join(a.root, "services", "tape_scoring", "scoring_extract.sql")
    omnibus(null=a.null).write(a.out, sql, truth={"fixture": True, "kind": "null" if a.null else "planted", "generator": "omnibus"})
    print("FIXTURE WRITTEN %s null=%s" % (a.out, a.null))
    return 0


if __name__ == "__main__":
    sys.exit(main())
