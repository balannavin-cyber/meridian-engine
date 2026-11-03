"""Merged chain events E1 / E2 (+ counted E3) from a per-strike chain export (tape phase T1b, plan D-10 to D-12).

PURE: stdlib only, no clock, no randomness, no I/O. The chain half of T1b. Nothing in this module reads a
tape row, and no tape module reads this one; the join is made later, by the scoring SQL.

Input rows (dicts of strings): run_id, symbol, ts, expiry_date, strike, oi_call, oi_put, gex_cr.
A run is one (symbol, ts). Its FRONT expiry is the smallest expiry_date at that ts (the S81 selector).
Only runs at or after 10:00:00 IST take part. Consecutive runs of the same symbol and front expiry form pairs.

  E1  the strike with the largest |gex_cr| differs from the previous run's.        K = new leader.
  E2  the call wall (largest oi_call) or put wall (largest oi_put) changes strike, or the wall strike's own
      OI changes by >= 5 % of its previous-run value (exact integers: 100*|d| >= 5*prev).  K = wall strike.
  E3  sign(sum gex_cr) changes: COUNTED only, never a row.
Merge: the same kind at the same K within 900 s of the FIRST counted event of that (kind, K) is merged into it
(merged_n += 1); the anchor is the counted event, not the last merged one. Ties in an argmax go to the lowest strike.
"""
import math
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
WINDOW_START_SOD = 10 * 3600
MERGE_SECONDS = 900
OI_PCT = 5

EVENT_COLS = ("symbol", "expiry", "kind", "ts_ist", "strike", "prev_strike", "prev_value", "new_value", "merged_n")
RUN_COLS = ("symbol", "expiry", "ts_ist", "run_id", "n_strikes", "leader_strike", "call_wall", "put_wall",
            "net_sign", "in_window")
FEASIBILITY = {"NIFTY": (501, 19), "SENSEX": (548, 19)}


def parse_ts(s):
    dt = datetime.fromisoformat(s.strip())
    if dt.tzinfo is None:
        raise ValueError("timestamp without an offset: %r" % s)
    return dt.astimezone(IST)


def _oi(s):
    s = (s or "").strip()
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        return int(float(s))


def _f(s):
    s = (s or "").strip()
    return float(s) if s else 0.0


def _argmax(pairs):
    """pairs: [(strike, value)] sorted by strike. Returns (strike or None, tie_count). None when max <= 0."""
    best, bk, ties = None, None, 0
    for k, v in pairs:
        if best is None or v > best:
            best, bk, ties = v, k, 1
        elif v == best:
            ties += 1
    if best is None or best <= 0:
        return None, 0
    return bk, ties


def build_runs(rows, day=None):
    """-> ({symbol: [run dicts sorted by time]}, counters)."""
    cnt = {"rows": 0, "other_day_rows": 0, "non_front_rows": 0, "run_id_conflicts": 0, "argmax_ties": 0}
    groups = {}
    for r in rows:
        cnt["rows"] += 1
        dt = parse_ts(r["ts"])
        if day is not None and dt.strftime("%Y-%m-%d") != day:
            cnt["other_day_rows"] += 1
            continue
        groups.setdefault((r["symbol"], dt), []).append(r)
    by_sym = {}
    for (sym, dt) in sorted(groups):
        grp = groups[(sym, dt)]
        front = min(g["expiry_date"] for g in grp)
        cnt["non_front_rows"] += sum(1 for g in grp if g["expiry_date"] != front)
        fr = [g for g in grp if g["expiry_date"] == front]
        if len({g["run_id"] for g in fr}) > 1:
            cnt["run_id_conflicts"] += 1
            continue
        seen = {}
        for g in fr:
            k = float(g["strike"])
            if k in seen:
                raise ValueError("duplicate strike %s in run %s %s" % (g["strike"], sym, g["ts"]))
            seen[k] = (_oi(g["oi_call"]), _oi(g["oi_put"]), _f(g["gex_cr"]))
        ks = sorted(seen)
        leader, t1 = _argmax([(k, abs(seen[k][2])) for k in ks])
        cw, t2 = _argmax([(k, seen[k][0]) for k in ks])
        pw, t3 = _argmax([(k, seen[k][1]) for k in ks])
        cnt["argmax_ties"] += (t1 > 1) + (t2 > 1) + (t3 > 1)
        tot = math.fsum(seen[k][2] for k in ks)
        sod = dt.hour * 3600 + dt.minute * 60 + dt.second
        by_sym.setdefault(sym, []).append({
            "symbol": sym, "expiry": front, "epoch": int(dt.timestamp()), "ts_ist": dt.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
            "run_id": fr[0]["run_id"], "n_strikes": len(ks), "strikes": seen, "leader": leader, "call_wall": cw,
            "put_wall": pw, "net_sign": (tot > 0) - (tot < 0), "in_window": sod >= WINDOW_START_SOD})
    return by_sym, cnt


def raw_events(runs):
    """runs: one symbol's runs in time order. Returns (events, e3_count, expiry_restarts)."""
    ev, e3, restarts = [], 0, 0
    prev, sign = None, 0
    for cur in runs:
        if not cur["in_window"]:
            continue
        if prev is not None and prev["expiry"] != cur["expiry"]:
            restarts += 1
            prev, sign = None, 0
        ns = cur["net_sign"] or sign
        if prev is not None:
            if sign and ns and ns != sign:
                e3 += 1
            _pair(prev, cur, ev)
        sign = ns or sign
        prev = cur
    return ev, e3, restarts


def _pair(prev, cur, ev):
    base = {"symbol": cur["symbol"], "expiry": cur["expiry"], "epoch": cur["epoch"], "ts_ist": cur["ts_ist"]}
    if prev["leader"] is not None and cur["leader"] is not None and prev["leader"] != cur["leader"]:
        ev.append(dict(base, kind="E1", strike=cur["leader"], prev_strike=prev["leader"],
                       prev_value=prev["strikes"][prev["leader"]][2], new_value=cur["strikes"][cur["leader"]][2]))
    for kind, idx, key in (("E2-call", 0, "call_wall"), ("E2-put", 1, "put_wall")):
        a, b = prev[key], cur[key]
        if a is None or b is None:
            continue
        pv, nv = prev["strikes"][a][idx], cur["strikes"][b][idx]
        if a != b:
            ev.append(dict(base, kind=kind, strike=b, prev_strike=a, prev_value=pv, new_value=nv))
        else:
            own_prev, own_cur = prev["strikes"][a][idx], cur["strikes"][a][idx]
            if own_prev > 0 and 100 * abs(own_cur - own_prev) >= OI_PCT * own_prev:
                ev.append(dict(base, kind=kind, strike=a, prev_strike=a, prev_value=own_prev, new_value=own_cur))


def merge(events):
    """events chronological per symbol. Returns counted events (with merged_n) and the number merged away."""
    counted, anchor, merged_away = [], {}, 0
    for e in sorted(events, key=lambda x: (x["symbol"], x["epoch"], x["kind"], x["strike"])):
        k = (e["symbol"], e["kind"], e["strike"])
        a = anchor.get(k)
        if a is not None and e["epoch"] - a["epoch"] <= MERGE_SECONDS:
            a["merged_n"] += 1
            merged_away += 1
        else:
            e = dict(e, merged_n=1)
            anchor[k] = e
            counted.append(e)
    return counted, merged_away


def process(rows, day=None):
    by_sym, cnt = build_runs(rows, day)
    events, per_sym = [], {}
    for sym in sorted(by_sym):
        runs = by_sym[sym]
        raw, e3, restarts = raw_events(runs)
        counted, merged_away = merge(raw)
        events += counted
        kinds = {}
        for e in counted:
            kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        raw_kinds = {}
        for e in raw:
            raw_kinds[e["kind"]] = raw_kinds.get(e["kind"], 0) + 1
        per_sym[sym] = {"runs": len(runs), "runs_in_window": sum(1 for r in runs if r["in_window"]),
                        "runs_pre_window": sum(1 for r in runs if not r["in_window"]),
                        "raw_events": dict(sorted(raw_kinds.items())), "counted_events": dict(sorted(kinds.items())),
                        "counted_total": len(counted), "merged_away": merged_away, "e3_flips": e3,
                        "expiry_restarts": restarts, "first_run": runs[0]["ts_ist"], "last_run": runs[-1]["ts_ist"]}
        if sym in FEASIBILITY:
            n, d = FEASIBILITY[sym]
            per_day = n / d
            per_sym[sym]["feasibility"] = {"v02_events": n, "v02_days": d, "v02_per_day": round(per_day, 6),
                                           "this_day": len(counted),
                                           "within_x0.5_to_x2": 0.5 * per_day <= len(counted) <= 2 * per_day}
    events.sort(key=lambda x: (x["symbol"], x["epoch"], x["kind"], x["strike"]))
    runs_all = [r for s in sorted(by_sym) for r in by_sym[s]]
    return {"events": events, "runs": runs_all, "per_symbol": per_sym, "counters": cnt}


def _k(v):
    return "%d" % v if v == int(v) else "%.2f" % v


def _val(v):
    return "%d" % v if isinstance(v, int) else "%.6f" % v


def render_events_csv(events):
    lines = [",".join(EVENT_COLS)]
    for e in events:
        lines.append(",".join([e["symbol"], e["expiry"], e["kind"], e["ts_ist"], _k(e["strike"]), _k(e["prev_strike"]),
                               _val(e["prev_value"]), _val(e["new_value"]), str(e["merged_n"])]))
    return "\n".join(lines) + "\n"


def render_runs_csv(runs):
    lines = [",".join(RUN_COLS)]
    for r in runs:
        lines.append(",".join([r["symbol"], r["expiry"], r["ts_ist"], r["run_id"], str(r["n_strikes"]),
                               "" if r["leader"] is None else _k(r["leader"]),
                               "" if r["call_wall"] is None else _k(r["call_wall"]),
                               "" if r["put_wall"] is None else _k(r["put_wall"]),
                               str(r["net_sign"]), "1" if r["in_window"] else "0"]))
    return "\n".join(lines) + "\n"


def render_text(day, per_sym, counters):
    L = ["MERIDIAN tape T1b - chain events for %s" % day, ""]
    for sym, s in per_sym.items():
        L.append("=== %s ===" % sym)
        L.append("  runs %d (in window %d, before 10:00 %d); first %s last %s"
                 % (s["runs"], s["runs_in_window"], s["runs_pre_window"], s["first_run"], s["last_run"]))
        L.append("  counted events per kind: " + ", ".join("%s %d" % kv for kv in s["counted_events"].items())
                 + "; total %d; merged away %d" % (s["counted_total"], s["merged_away"]))
        L.append("  E3 net-sign flips (counted only, no rows): %d; front-expiry changes: %d" % (s["e3_flips"], s["expiry_restarts"]))
        f = s.get("feasibility")
        if f:
            L.append("  v0.2 feasibility: %d events over %d days = %.1f a day; this day %d -> %s"
                     % (f["v02_events"], f["v02_days"], f["v02_per_day"], f["this_day"],
                        "within x0.5..x2" if f["within_x0.5_to_x2"] else "FAR OFF the v0.2 rate (outside x0.5..x2, a reporting band only)"))
    L.append("")
    L.append("counters: " + ", ".join("%s=%d" % kv for kv in sorted(counters.items())))
    return "\n".join(L) + "\n"
