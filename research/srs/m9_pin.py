#!/usr/bin/env python3
"""M9 -- does the pin hold? Read-only.

THE CLAIM UNDER TEST. The GEX layer of the pre-registration assumes price is
drawn toward concentrated gamma. M3 measures expected versus realised *move*,
which is a different claim. This tests the pin directly.

WHAT WOULD FALSIFY A POSITIVE RESULT, stated before any number is produced.
A pin claim is not "settlement lands near the max-gamma strike" -- settlement
lands near spot too, and spot is near the max-gamma strike, so that statement
is nearly self-satisfying. The claim is that the max-gamma strike forecasts
settlement BETTER THAN CURRENT SPOT DOES. So:

    pin holds   <=>  |settlement - max_gamma_strike|  <  |settlement - spot|
                     measured at the SAME stamp, both in sigma_daily

If the share of cycles where max-gamma beats spot sits at ~50%, there is no
pin effect in this data whatever a chart looks like. A negative result here is
as valuable as a positive one and is reported with equal weight.

WHICH "MAX-GAMMA STRIKE", AND WHY NOT THE OBVIOUS ONE.
This uses ABSOLUTE gamma concentration -- argmax over strikes of
sum(gamma * OI) across CE and PE -- NOT the net signed quantity that
MERDIAN's `gamma_metrics.max_gamma_strike` computes.

That is deliberate. ADR-024 Amendment A (S79) establishes that the stored
column is the max NET-long-gamma strike (CE contribution minus PE), and that
its position above spot is *arithmetic from OI imbalance, not positioning*:
under put-call parity call and put gamma are equal at a strike, so the sign of
gex_cr is driven by which side is OTM, which flips at spot. Measuring the pin
against that quantity would measure a tautology. Absolute concentration is the
quantity the pin story is actually about -- where dealer gamma is largest,
irrespective of sign.

SETTLEMENT IS A PROXY. Official weekly settlement is a 30-minute VWAP of the
underlying, which this database does not carry. The proxy is the spot close at
the 15:25 anchor on expiry day. Era 1 is entirely pre-CAS (ADR-022 takes
effect 2026-08-03), so 15:25 is inside normal continuous trading throughout
this window and the proxy is close. It is still a proxy and is labelled one.

COVERAGE IS REPORTED, NEVER SILENTLY DROPPED. The greeks sidecar covers 193 of
247 NIFTY trading days and 192 of 246 SENSEX, so stamps will be missing. Every
stamp that cannot be computed is counted and attributed.

STOP CONDITION. Fewer than 30 cycles per symbol with a computable max-gamma
strike at a stamp -> that stamp reports INSUFFICIENT and no verdict.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

import srs_io as io
import srs_cycles as cyc

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".m1_era1_cycles.json"
RESULTS = HERE / "srs_exploration_2026-09-21_m9_pin.md"

MIN_CYCLES = 30          # brief's stop condition, per symbol per stamp
WINDOW_MIN = 5           # staleness budget on 1m data


def _deser(d):
    return dt.date.fromisoformat(d["__date__"]) if "__date__" in d else d


def qs(xs, ps=(0.5, 0.75)):
    s = sorted(xs)
    if not s:
        return [None] * len(ps)
    n = len(s)
    return [s[min(n - 1, max(0, int(round(p * (n - 1)))))] for p in ps]


def max_gamma_strike(iid, expiry, day, target):
    """argmax_strike sum(gamma * OI) over CE and PE, at the last bar <= target.

    Two requests. The greeks sidecar decides the anchor minute; the OI is then
    read at exactly that minute so gamma and OI describe the same instant.
    Returns (strike, anchor_ist, n_strikes) or (None, None, reason).
    """
    lo = (dt.datetime.combine(day, target)
          - dt.timedelta(minutes=WINDOW_MIN)).isoformat()
    hi = dt.datetime.combine(day, target).isoformat()
    g = io._rows("hist_option_greeks_1m",
                 [("select", "bar_ts,strike,option_type,gamma"),
                  ("instrument_id", f"eq.{iid}"),
                  ("expiry_date", f"eq.{expiry.isoformat()}"),
                  ("bar_ts", f"gte.{lo}"), ("bar_ts", f"lte.{hi}"),
                  ("gamma", "not.is.null")])
    if not g:
        return None, None, "no greeks rows in anchor window"
    anchor = max(r["bar_ts"] for r in g)
    gam = {(float(r["strike"]), r["option_type"]): float(r["gamma"])
           for r in g if r["bar_ts"] == anchor and r.get("gamma") is not None}
    if not gam:
        return None, None, "no gamma at anchor minute"
    b = io._rows("hist_option_bars_1m",
                 [("select", "strike,option_type,oi"),
                  ("instrument_id", f"eq.{iid}"),
                  ("expiry_date", f"eq.{expiry.isoformat()}"),
                  ("bar_ts", f"eq.{anchor}"), ("oi", "not.is.null")])
    oi = {(float(r["strike"]), r["option_type"]): float(r["oi"]) for r in b}
    per = defaultdict(float)
    for key, gv in gam.items():
        if key in oi:
            per[key[0]] += abs(gv) * oi[key]
    if not per:
        return None, None, "greeks and OI share no (strike, option_type) at anchor"
    k = max(per, key=per.get)
    return k, cyc.ist_index("hist_option_greeks_1m",
                            [{"bar_ts": anchor}], "bar_ts")[0][0], len(per)


def main():
    payload = json.loads(CACHE.read_text(), object_hook=_deser)
    cycles = payload["measured"]
    inst = io._rows("instruments", [("select", "id,symbol")])
    ids = {r["symbol"]: r["id"] for r in inst if r.get("symbol")}

    rows, miss = [], defaultdict(int)
    for i, c in enumerate(cycles, 1):
        sym, expiry, sig = c["symbol"], c["expiry"], c["sigma_d"]
        days = sorted({s["day"] for s in c["stamps"]})
        iid = ids[sym]

        spot_rows = io._rows("hist_spot_bars_5m",
                             [("select", "bar_ts,close"), ("symbol", f"eq.{sym}"),
                              ("bar_ts", f"gte.{days[0].isoformat()}"),
                              ("bar_ts", f"lt.{(days[-1] + dt.timedelta(days=1)).isoformat()}"),
                              ("order", "bar_ts.asc")])
        sidx = cyc.ist_index("hist_spot_bars_5m", spot_rows, "bar_ts")
        se, _, why = cyc.pick_anchor(sidx, expiry, cyc.ANCHOR_CLOSE, 5)
        if se is None:
            miss["settlement unavailable"] += 1
            continue
        settle = float(se[1]["close"])

        stamps = [("Day1_1030", days[0], cyc.ANCHOR_REF)]
        if len(days) >= 3:
            stamps.append(("Day3_close", days[2], cyc.ANCHOR_CLOSE))
        if len(days) >= 2:
            stamps.append(("DTE1_close", days[-2], cyc.ANCHOR_CLOSE))

        for label, day, target in stamps:
            k, anchor, info = max_gamma_strike(iid, expiry, day, target)
            if k is None:
                miss[f"{label}: {info}"] += 1
                continue
            sp_e, _, _w = cyc.pick_anchor(sidx, day, target, 5)
            if sp_e is None:
                miss[f"{label}: no spot at stamp"] += 1
                continue
            spot = float(sp_e[1]["close"])
            rows.append({"symbol": sym, "expiry": expiry, "stamp": label,
                         "d_gamma": abs(settle - k) / sig,
                         "d_spot": abs(settle - spot) / sig,
                         "n_strikes": info})
        if i % 20 == 0:
            print(f"  {i}/{len(cycles)} cycles  rows={len(rows)} "
                  f"requests={io.REQUESTS_MADE}")

    # ---- render
    w = []
    a = w.append
    a("# M9 -- does the pin hold?")
    a("")
    a(f"Generated {dt.date.today().isoformat()}. Read-only, era 1 "
      f"(2025-04-01 .. 2026-03-30), {len(cycles)} candidate cycles.")
    a("")
    a("## What would falsify a positive result")
    a("")
    a("A pin claim is **not** \"settlement lands near the max-gamma strike\" -- "
      "settlement lands near spot, and spot is near the max-gamma strike, so "
      "that statement is nearly self-satisfying. The claim is that the "
      "max-gamma strike forecasts settlement **better than current spot does**, "
      "at the same stamp. A beat-share near 50% is no pin effect, whatever a "
      "chart looks like.")
    a("")
    a("## Which max-gamma strike, and why not the stored one")
    a("")
    a("Absolute gamma concentration -- `argmax_K sum(|gamma| * OI)` over CE and "
      "PE -- **not** MERDIAN's `gamma_metrics.max_gamma_strike`. ADR-024 "
      "Amendment A (S79) establishes that the stored column is the max "
      "NET-long-gamma strike and that its offset from spot is *arithmetic from "
      "OI imbalance, not positioning*: under put-call parity call and put gamma "
      "are equal at a strike, so the sign of `gex_cr` is set by which side is "
      "OTM, which flips at spot. Testing the pin against that quantity would "
      "test a tautology.")
    a("")
    a("Settlement is a **proxy**: the spot close at the 15:25 anchor on expiry "
      "day. Official weekly settlement is a 30-minute VWAP the database does "
      "not carry. Era 1 is entirely pre-CAS (ADR-022 effective 2026-08-03), so "
      "15:25 is inside normal continuous trading throughout.")
    a("")
    a("## M9.A  Distance to settlement, in sigma_daily")
    a("")
    a("| symbol | stamp | N | median gamma | P75 gamma | median spot | P75 spot "
      "| gamma beats spot | verdict |")
    a("|---|---|---:|---:|---:|---:|---:|---:|---|")
    by = defaultdict(list)
    for r in rows:
        by[(r["symbol"], r["stamp"])].append(r)
    order = {"Day1_1030": 0, "Day3_close": 1, "DTE1_close": 2}
    summary = []
    for k in sorted(by, key=lambda x: (x[0], order.get(x[1], 9))):
        rs = by[k]
        n = len(rs)
        mg, p75g = qs([r["d_gamma"] for r in rs])
        ms, p75s = qs([r["d_spot"] for r in rs])
        beat = 100.0 * sum(1 for r in rs if r["d_gamma"] < r["d_spot"]) / n
        verdict = "INSUFFICIENT" if n < MIN_CYCLES else (
            "gamma better" if beat > 50 else "spot better or equal")
        summary.append((k[0], k[1], n, beat, verdict, mg, ms))
        a(f"| {k[0]} | {k[1]} | {n}{'*' if n < MIN_CYCLES else ''} | {mg:.2f} | "
          f"{p75g:.2f} | {ms:.2f} | {p75s:.2f} | {beat:.0f}% | {verdict} |")
    a("")
    a(f"`N*` marks a cell below the brief's stop condition of {MIN_CYCLES} "
      f"cycles; those report INSUFFICIENT and carry no verdict.")
    a("")
    a("## M9.B  Does the advantage grow as DTE falls?")
    a("")
    a("The reference claim is that the pull strengthens into expiry. That "
      "predicts the beat-share rising from Day-1 through Day-3 to 1 DTE.")
    a("")
    a("| symbol | Day1_1030 | Day3_close | DTE1_close | rising? |")
    a("|---|---:|---:|---:|---|")
    for sym in ("NIFTY", "SENSEX"):
        seq = [next((s[3] for s in summary if s[0] == sym and s[1] == st), None)
               for st in ("Day1_1030", "Day3_close", "DTE1_close")]
        if any(v is None for v in seq):
            a(f"| {sym} | " + " | ".join("-" if v is None else f"{v:.0f}%"
                                         for v in seq) + " | incomplete |")
            continue
        rising = seq[0] <= seq[1] <= seq[2]
        a(f"| {sym} | " + " | ".join(f"{v:.0f}%" for v in seq)
          + f" | {'yes' if rising else 'NO'} |")
    a("")
    a("## Coverage -- stamps that could not be computed")
    a("")
    a("| reason | count |")
    a("|---|---:|")
    for r, n in sorted(miss.items(), key=lambda kv: -kv[1]):
        a(f"| {r} | {n} |")
    if not miss:
        a("| none | 0 |")
    a("")
    a("The greeks sidecar covers 193 of 247 NIFTY and 192 of 246 SENSEX era-1 "
      "trading days, so missing stamps are expected. They are counted here "
      "rather than dropped.")
    a("")
    with RESULTS.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(w) + "\n")

    print(f"\nrows={len(rows)}  missing_stamps={sum(miss.values())}  "
          f"requests={io.REQUESTS_MADE}")
    for sym, st, n, beat, verdict, mg, ms in summary:
        print(f"  {sym} {st}: N={n} beat={beat:.0f}% "
              f"med_gamma={mg:.2f} med_spot={ms:.2f} -> {verdict}")
    print(f"wrote {RESULTS.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except io.Probe as e:
        print(f"FATAL probe failure: {e}", file=sys.stderr)
        raise SystemExit(2) from None
