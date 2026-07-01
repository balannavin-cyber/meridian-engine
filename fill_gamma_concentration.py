from __future__ import annotations

"""
fill_gamma_concentration.py  --  TD-S58-NEW-1 concentration backfill.

gamma_concentration (Herfindahl-style dominance: max|gex| / sum|gex| over the
signed strike_map) is 100% empty in the pre-existing hist_gamma_metrics table.
The historical per-strike GEX that built that table was discarded; the column is
only recoverable by RE-DERIVING per-strike gamma from raw bars -- which solve_bar
already does. concentration is SCALE-INVARIANT (a ratio), so the sidecar's flat-r
gamma reproduces it exactly regardless of the 1e7 net_gex convention.

This script:
  --validate : recompute concentration on the LIVE overlap two ways -- from
               gex_strike_snapshots (live per-strike, authoritative) vs from a
               solve_bar reconstruction of the same bars -- and confirm they
               agree. GATE before any historical write. Read-only.
  --symbol/--from/--to [--apply] : recompute concentration from the sidecar's
               per-strike gamma at each existing hist_gamma_metrics bar_ts in
               range, and UPDATE only the gamma_concentration column on the
               matching (symbol, bar_ts) row. Idempotent; touches no other column.

Concentration formula is verbatim from compute_gamma_metrics_local.py.
"""

import argparse
import sys
from urllib.parse import urlencode

import requests
import backfill_hist_greeks as b   # solve_bar, get, iid_for, parse_ts, spot_map_for_date, signed_gex_vec, etc.


# ---- concentration: verbatim from compute_gamma_metrics_local.compute_gamma_concentration
def gamma_concentration(strike_map):
    if not strike_map:
        return None
    total_abs = sum(abs(v) for v in strike_map.values())
    if total_abs <= 0:
        return None
    max_abs = max(abs(v) for v in strike_map.values())
    return max_abs / total_abs if max_abs > 0 else None


def patch_one(table, match, body):
    """PostgREST PATCH: update rows matching `match` filters with `body`. Returns count."""
    base, h = b._cfg()
    hh = dict(h, **{"Content-Type": "application/json", "Prefer": "return=representation"})
    url = f"{base}/rest/v1/{table}?{urlencode(match)}"
    r = requests.patch(url, headers=hh, json=body, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"PATCH {table} {r.status_code}: {r.text[:160]}")
    return len(r.json())


# ---------------------------------------------------------------- VALIDATION (live overlap)
def conc_from_gss(symbol, ts):
    """Concentration from live per-strike gex_strike_snapshots at one ts (authoritative)."""
    rows = b.get("gex_strike_snapshots", {"select": "strike,gex_cr",
                 "symbol": f"eq.{symbol}", "ts": f"eq.{ts}"}, cap_pages=2)
    if not rows:
        return None
    sm = {}
    for r in rows:
        k = float(r["strike"]); g = float(r.get("gex_cr") or 0)
        sm[k] = sm.get(k, 0.0) + g
    return gamma_concentration(sm)


def validate(symbol, day="2025-09-19"):
    """Historical gate: confirm the reconstruction's strike_map reproduces the EXISTING
    hist_gamma_metrics net_gex on the same bars (sign + 1e7-scaled magnitude). Live
    gex_strike_snapshots (2026-05-25+) does NOT overlap raw hist bars (<=2026-05-07),
    so concentration can't be checked both ways directly. But concentration and net_gex
    are both pure functions of the SAME strike_map -- so if our strike_map reproduces
    the table's net_gex, concentration off that identical map is trustworthy by
    construction. Validates against the exact table being filled. Read-only."""
    iid = b.iid_for(symbol)
    existing = b.get("hist_gamma_metrics",
                     {"select": "bar_ts,net_gex", "symbol": f"eq.{symbol}",
                      "trade_date": f"eq.{day}", "order": "bar_ts.asc"})
    if not existing:
        print(f"{symbol}: no hist_gamma_metrics rows on {day}"); return 1
    scache = b.spot_map_for_date(iid, day)
    print(f"{symbol}: validating reconstruction vs existing net_gex on {day} "
          f"({len(existing)} rows)")

    n = sgn = 0; ratios = []; concs = []
    for r in existing:
        bts = r["bar_ts"]
        if bts not in scache:
            continue
        res = b.solve_bar(iid, bts, day, spot_cache=scache)
        if res[0] == "SKIP_EXPIRY" or res[1] is None:
            continue
        sm = res[1]
        rec_ng = sum(sm.values())                 # reconstructed net_gex (Cr-scaled, /1e7)
        ex_ng = float(r["net_gex"]) if r.get("net_gex") is not None else None
        if ex_ng is None or ex_ng == 0:
            continue
        n += 1
        if (rec_ng >= 0) == (ex_ng >= 0):
            sgn += 1
        ratios.append(ex_ng / rec_ng)             # expect ~1e7 (table stores unscaled)
        c = gamma_concentration(sm)
        if c is not None:
            concs.append(c)
    print("=" * 56)
    if n:
        ratios.sort(); concs.sort()
        med_r = ratios[len(ratios)//2]
        print(f"  matched bars   : {n}")
        print(f"  net_gex sign   : {sgn}/{n} ({100*sgn/n:.0f}%)")
        print(f"  scale (tbl/rec): median {med_r:,.0f}  (expect ~1e7)")
        if concs:
            print(f"  concentration  : min {concs[0]:.3f}  median {concs[len(concs)//2]:.3f}  max {concs[-1]:.3f}")
        ok = (sgn / n >= 0.90) and (5e6 <= abs(med_r) <= 2e7)
        print("  GATE:", "PASS -- strike_map reproduces table net_gex; concentration trustworthy."
              if ok else "REVIEW -- strike_map diverges from table net_gex.")
        rc = 0 if ok else 1
    else:
        print("  no matched bars"); rc = 1
    print("=" * 56)
    return rc


# ---------------------------------------------------------------- FILL (historical)
def fill(symbol, d_from, d_to, apply):
    iid = b.iid_for(symbol)
    # existing rows in range that still need concentration
    existing = b.get("hist_gamma_metrics",
                     {"select": "bar_ts,trade_date,gamma_concentration", "symbol": f"eq.{symbol}",
                      "and": f"(trade_date.gte.{d_from},trade_date.lte.{d_to})",
                      "order": "bar_ts.asc"})
    if not existing:
        print(f"{symbol}: no hist_gamma_metrics rows in {d_from}..{d_to}"); return 1
    todo = [r for r in existing if r.get("gamma_concentration") is None]
    print(f"{symbol}: {len(existing)} rows in range, {len(todo)} need concentration. apply={apply}\n",
          flush=True)

    # group target bar_ts by trade_date; solve each day's spot cache once
    from collections import defaultdict
    bydate = defaultdict(list)
    for r in todo:
        bydate[r["trade_date"]].append(r["bar_ts"])

    filled = matched = 0
    for d in sorted(bydate.keys()):
        scache = b.spot_map_for_date(iid, d)
        if not scache:
            print(f"  {d}: no spot cache, skip"); continue
        day_filled = 0
        for bts in bydate[d]:
            if bts not in scache:          # existing bar_ts must exist in raw bars to re-solve
                continue
            res = b.solve_bar(iid, bts, d, spot_cache=scache)
            if res[0] == "SKIP_EXPIRY" or res[1] is None:
                continue
            conc = gamma_concentration(res[1])
            if conc is None:
                continue
            matched += 1
            if apply:
                k = patch_one("hist_gamma_metrics",
                              {"symbol": f"eq.{symbol}", "bar_ts": f"eq.{bts}"},
                              {"gamma_concentration": conc})
                filled += k; day_filled += k
        print(f"  {d}: solved={len(bydate[d]):>4} filled={day_filled:>4} "
              f"{'WROTE' if apply else 'dry'}", flush=True)
    print(f"\n{symbol}: matched={matched} {'updated' if apply else '(dry)'}={filled}")
    return 0


def fill_fast(symbol, d_from, d_to, apply):
    """Day-batched fill: read stored sidecar gamma + bulk vendor oi per day, build the
    signed strike_map from STORED gamma (no per-bar re-solve, no per-bar chain GET).
    Concentration is scale-invariant so this reproduces fill() exactly. ~10x fewer
    round-trips. Expiry days have no sidecar rows -> naturally produce no fill."""
    import numpy as np
    iid = b.iid_for(symbol)
    existing = b.get("hist_gamma_metrics",
                     {"select": "bar_ts,trade_date,gamma_concentration", "symbol": f"eq.{symbol}",
                      "and": f"(trade_date.gte.{d_from},trade_date.lte.{d_to})",
                      "order": "bar_ts.asc"})
    if not existing:
        print(f"{symbol}: no hist_gamma_metrics rows in {d_from}..{d_to}"); return 1
    todo = [r for r in existing if r.get("gamma_concentration") is None]
    print(f"{symbol}: {len(existing)} rows in range, {len(todo)} need concentration. "
          f"apply={apply} [FAST]\n", flush=True)
    from collections import defaultdict
    bydate = defaultdict(set)
    for r in todo:
        bydate[r["trade_date"]].add(r["bar_ts"])

    filled = matched = 0
    for d in sorted(bydate.keys()):
        want = bydate[d]
        # one bulk GET of the day's stored gamma (sidecar) -- carries expiry_date
        side = b.get("hist_option_greeks_1m",
                     {"select": "bar_ts,strike,option_type,expiry_date,gamma",
                      "instrument_id": f"eq.{iid}", "trade_date": f"eq.{d}",
                      "order": "bar_ts.asc"})
        if not side:
            print(f"  {d}: no sidecar rows (expiry/unsolved), skip"); continue
        # one bulk GET of the day's vendor oi -- carries expiry_date for exact join
        vend = b.get("hist_option_bars_1m",
                     {"select": "bar_ts,strike,option_type,expiry_date,oi",
                      "instrument_id": f"eq.{iid}", "trade_date": f"eq.{d}",
                      "order": "bar_ts.asc"})
        scache = b.spot_map_for_date(iid, d)
        # key includes expiry_date: prevents cross-expiry oi collapse (slow path uses front expiry)
        oi_map = {(r["bar_ts"], float(r["strike"]), str(r["option_type"]), r["expiry_date"]):
                  float(r.get("oi") or 0) for r in vend}
        # group sidecar by bar_ts
        by_bar = defaultdict(list)
        for r in side:
            by_bar[r["bar_ts"]].append(r)

        day_rows = []
        for bts, srows in by_bar.items():
            if bts not in want or bts not in scache:
                continue
            spot = scache[bts]
            # match slow path: front expiry only = min(expiry_date >= trade_date)
            exps = [r["expiry_date"] for r in srows if r.get("expiry_date") and r["expiry_date"] >= d]
            if not exps:
                continue
            front = min(exps)
            K, G, OI, ISP = [], [], [], []
            for r in srows:
                if r.get("gamma") is None or r.get("expiry_date") != front:
                    continue
                k = float(r["strike"]); ot = str(r["option_type"]); ex = r["expiry_date"]
                K.append(k); G.append(float(r["gamma"]))
                OI.append(oi_map.get((bts, k, ot, ex), 0.0))
                ISP.append(ot.upper().startswith("P"))
            if len(K) < 6:
                continue
            K = np.array(K); G = np.array(G); OI = np.array(OI); ISP = np.array(ISP)
            gex = b.signed_gex_vec(G, OI, ISP, K, spot)
            sm = defaultdict(float)
            for i in range(len(K)):
                if K[i] > 0:
                    sm[K[i]] += gex[i]
            conc = gamma_concentration(dict(sm))
            if conc is None:
                continue
            matched += 1
            day_rows.append((bts, conc))
        if apply:
            for bts, conc in day_rows:
                filled += patch_one("hist_gamma_metrics",
                                    {"symbol": f"eq.{symbol}", "bar_ts": f"eq.{bts}"},
                                    {"gamma_concentration": conc})
        print(f"  {d}: bars={len(by_bar):>4} filled={len(day_rows):>4} "
              f"{'WROTE' if apply else 'dry'}", flush=True)
    print(f"\n{symbol}: matched={matched} {'updated' if apply else '(dry)'}={filled} [FAST]")
    return 0


def verify_fast(symbol, d_from, d_to):
    """Run the REAL fill_fast strike_map logic and compare concentration to the values
    already in hist_gamma_metrics (written by the validated slow fill). Read-only.
    Proves fill_fast == fill before trusting --fast on unfilled ranges."""
    import numpy as np
    iid = b.iid_for(symbol)
    existing = b.get("hist_gamma_metrics",
                     {"select": "bar_ts,trade_date,gamma_concentration", "symbol": f"eq.{symbol}",
                      "and": f"(trade_date.gte.{d_from},trade_date.lte.{d_to})",
                      "order": "bar_ts.asc"})
    have = {r["bar_ts"]: r["gamma_concentration"] for r in existing
            if r.get("gamma_concentration") is not None}
    if not have:
        print("no filled rows to verify against in range"); return 1
    from collections import defaultdict
    bydate = defaultdict(set)
    for r in existing:
        if r["bar_ts"] in have:
            bydate[r["trade_date"]].add(r["bar_ts"])

    diffs = []
    for d in sorted(bydate.keys()):
        want = bydate[d]
        side = b.get("hist_option_greeks_1m",
                     {"select": "bar_ts,strike,option_type,expiry_date,gamma",
                      "instrument_id": f"eq.{iid}", "trade_date": f"eq.{d}", "order": "bar_ts.asc"})
        if not side:
            continue
        vend = b.get("hist_option_bars_1m",
                     {"select": "bar_ts,strike,option_type,expiry_date,oi",
                      "instrument_id": f"eq.{iid}", "trade_date": f"eq.{d}", "order": "bar_ts.asc"})
        scache = b.spot_map_for_date(iid, d)
        oi_map = {(r["bar_ts"], float(r["strike"]), str(r["option_type"]), r["expiry_date"]):
                  float(r.get("oi") or 0) for r in vend}
        by_bar = defaultdict(list)
        for r in side:
            by_bar[r["bar_ts"]].append(r)
        for bts, srows in by_bar.items():
            if bts not in want or bts not in scache:
                continue
            spot = scache[bts]
            exps = [r["expiry_date"] for r in srows if r.get("expiry_date") and r["expiry_date"] >= d]
            if not exps:
                continue
            front = min(exps)
            K, G, OI, ISP = [], [], [], []
            for r in srows:
                if r.get("gamma") is None or r.get("expiry_date") != front:
                    continue
                k = float(r["strike"]); ot = str(r["option_type"])
                K.append(k); G.append(float(r["gamma"]))
                OI.append(oi_map.get((bts, k, ot, front), 0.0))
                ISP.append(ot.upper().startswith("P"))
            if len(K) < 6:
                continue
            K = np.array(K); G = np.array(G); OI = np.array(OI); ISP = np.array(ISP)
            gex = b.signed_gex_vec(G, OI, ISP, K, spot)
            sm = defaultdict(float)
            for i in range(len(K)):
                if K[i] > 0:
                    sm[K[i]] += gex[i]
            conc = gamma_concentration(dict(sm))
            if conc is not None and have.get(bts) is not None:
                diffs.append(abs(conc - float(have[bts])))
    diffs.sort()
    print("=" * 56)
    print(f"{symbol} fill_fast vs table  ({d_from}..{d_to})")
    if diffs:
        print(f"  bars compared : {len(diffs)}")
        print(f"  max |diff|    : {diffs[-1]:.2e}")
        print(f"  median |diff| : {diffs[len(diffs)//2]:.2e}")
        print("  VERDICT:", "EQUIVALENT -- --fast safe" if diffs[-1] < 1e-9 else "DIVERGENT")
    else:
        print("  no bars compared")
    print("=" * 56)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="NIFTY")
    ap.add_argument("--from", dest="d_from")
    ap.add_argument("--to", dest="d_to")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--fast", action="store_true", help="day-batched read of stored gamma (no re-solve)")
    ap.add_argument("--verify", action="store_true", help="compare fill_fast output to filled table values")
    args = ap.parse_args()
    if args.validate:
        return validate(args.symbol)
    if args.verify:
        return verify_fast(args.symbol, args.d_from, args.d_to)
    if not (args.d_from and args.d_to):
        print("need --from and --to (or --validate)"); return 2
    if args.fast:
        return fill_fast(args.symbol, args.d_from, args.d_to, args.apply)
    return fill(args.symbol, args.d_from, args.d_to, args.apply)


if __name__ == "__main__":
    sys.exit(main())
