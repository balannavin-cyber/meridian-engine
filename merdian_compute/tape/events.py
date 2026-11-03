"""Tape event candidates: CONC and THIN (tape phase T1b, plan D-6 to D-8).

PURE: stdlib only, no clock, no randomness, no I/O. Strike-agnostic candidates at every subscribed
strike-leg, within one day, from that strike-leg's own history only. Nothing here knows which strike is
interesting; a later stage decides that.

CONC (z-rule). agg = buy + sell in a 5-minute bin. For bin T the history is this strike-leg's bins strictly
before T. z = (agg - mean) / pstdev over that history, decided in exact integers: with n bins, S = sum, Q = sum
of squares, d = n*agg - S and v = n*Q - S*S, z >= 3 <=> v > 0 and d >= 0 and d*d >= 9*v. Needs n >= MIN_PRIOR.
An event needs two consecutive such bins; it is stamped at the second bin's T.

THIN (depth collapse). For a minute row's bid_qty_5 (and ask_qty_5, separately): value <= 50 % of the median of
the same series over the previous 30 clock minutes (present values only, at least 20 of them) for two
consecutive minutes. Depth is the END-of-minute snapshot, known only at the minute's close, so the event is
stamped at the close of the second minute (m + 1:00), never at m:00.

Onset only: after an event the strike-leg is disarmed until a bin (minute) on which the condition is false.
"""
import json
import math

MIN_PRIOR = 12
THIN_WINDOW = 30
THIN_MIN_WINDOW = 20
SESSION_OPEN = 555
SESSION_END = 930

EVENT_COLS = ("symbol", "expiry", "strike", "leg", "kind", "ts_ist", "side", "magnitude", "detail_json")


def _ts(day, m):
    return "%sT%02d:%02d:00+05:30" % (day, m // 60, m % 60)


def conc_events(bins):
    """bins: [(T_minutes, buy_5, sell_5)] consecutive from the strike-leg's first bin.
    Returns [{"T", "side", "z1", "z2", "n1", "n2", "agg1", "agg2"}]."""
    out = []
    n = S = Q = 0
    prev_c, armed, prev = False, True, None
    for (T, buy, sell) in bins:
        agg = buy + sell
        c, z = False, None
        if n >= MIN_PRIOR:
            v = n * Q - S * S
            d = n * agg - S
            if v > 0:
                z = d / math.sqrt(v)
                if d >= 0 and d * d >= 9 * v:
                    c = True
        if c and prev_c and armed:
            side = "buy" if buy > sell else ("sell" if sell > buy else "flat")
            out.append({"T": T, "side": side, "z1": prev[0], "z2": z, "n1": prev[1], "n2": n,
                        "agg1": prev[2], "agg2": agg})
            armed = False
        if not c:
            armed = True
        prev_c, prev = c, (z, n, agg)
        n += 1
        S += agg
        Q += agg * agg
    return out


def _median2(sorted_vals):
    w = len(sorted_vals)
    return sorted_vals[w // 2] * 2 if w % 2 else sorted_vals[w // 2 - 1] + sorted_vals[w // 2]


def thin_events(depth, which):
    """depth: {minute: (bid_qty_5, ask_qty_5)}; which 0 = bid, 1 = ask.
    Returns [{"m", "side", "v", "v_prev", "median", "w"}] (m = the second minute of the pair)."""
    vals = {m: d[which] for m, d in depth.items() if d[which] is not None and SESSION_OPEN <= m < SESSION_END}
    out, flag, armed = [], {}, True
    for m in sorted(vals):
        v = vals[m]
        win = sorted(vals[k] for k in range(m - THIN_WINDOW, m) if k in vals)
        w = len(win)
        c, med2 = False, 0
        if w >= THIN_MIN_WINDOW:
            med2 = _median2(win)
            if med2 > 0 and 4 * v <= med2:
                c = True
        if c and flag.get(m - 1) and armed:
            out.append({"m": m, "side": "bid" if which == 0 else "ask", "v": v, "v_prev": vals[m - 1],
                        "median": med2 / 2.0, "w": w})
            armed = False
        if not c:
            armed = True
        flag[m] = c
    return out


def _r6(x):
    return None if x is None else round(x, 6)


def candidates(tokens):
    """tokens: the 'tokens' list from cycle.build_cycle. Option strike-legs only (CE / PE)."""
    ev = []
    for t in tokens:
        if t["leg"] not in ("CE", "PE"):
            continue
        base = (t["symbol"], t["expiry"], t["strike"], t["leg"])
        for e in conc_events(t["bins"]):
            det = {"z_1": _r6(e["z1"]), "z_2": _r6(e["z2"]), "n_prior_1": e["n1"], "n_prior_2": e["n2"],
                   "agg_1": e["agg1"], "agg_2": e["agg2"]}
            ev.append(base + ("CONC", _ts(t["day"], e["T"]), e["side"], e["z2"], det))
        for which in (0, 1):
            for e in thin_events(t["depth"], which):
                det = {"depth": e["v"], "depth_prev": e["v_prev"], "median_30": _r6(e["median"]),
                       "n_window": e["w"], "minute": "%02d:%02d" % (e["m"] // 60, e["m"] % 60)}
                ev.append(base + ("THIN", _ts(t["day"], e["m"] + 1), e["side"], e["v"] / e["median"], det))
    ev.sort(key=lambda x: (x[0], x[1] or "", float(x[2] or 0.0), x[3], x[4], x[5], x[6]))
    return ev


def _q(s):
    if any(ch in s for ch in ',"\n'):
        return '"' + s.replace('"', '""') + '"'
    return s


def render_events_csv(ev):
    lines = [",".join(EVENT_COLS)]
    for sym, exp, strike, leg, kind, ts, side, mag, det in ev:
        lines.append(",".join([sym, exp or "", strike or "", leg, kind, ts, side, "%.6f" % mag,
                               _q(json.dumps(det, sort_keys=True, separators=(",", ":")))]))
    return "\n".join(lines) + "\n"
