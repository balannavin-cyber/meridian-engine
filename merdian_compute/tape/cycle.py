"""Five-minute cycle aggregator (tape phase T1b, plan D-2 to D-5).

PURE: stdlib only, no clock, no randomness, no I/O. Turns tape_minute.csv rows (dicts of strings) into
per-strike-leg 5-minute cycle rows. The tape half of T1b: nothing in this module reads any other data set.

Bin membership (plan D-2): a minute row labelled m (the minute START, so it holds m:00..m:59) belongs to
the bin T with T-5 <= m < T. Bin T is stamped T and holds nothing from after T. The grid is 09:20..15:30.
A strike-leg's rows start at the bin that contains its first subscription minute; before that there is no
row, never a zero-filled one.
"""
SESSION_OPEN = 555   # 09:15 in minutes since midnight
SESSION_END = 930    # 15:30; minute rows with 555 <= m < 930 are in session
FIRST_T = 560        # 09:20
LAST_T = 930         # 15:30
STEP = 5

CYCLE_COLS = ("symbol", "expiry", "strike", "leg", "token", "tradingsymbol", "T", "buy_5", "sell_5", "uncl_5",
              "gap_5", "trades_5", "buy_15", "sell_15", "buy_30", "sell_30", "balance_5", "balance_15",
              "balance_30", "resting_imb", "classified_share_5", "buy_cum", "sell_cum", "uncl_cum", "gap_cum",
              "oi_last", "oi_delta_5", "minutes_present_5", "first_seen_T")
_FLOATS = ("balance_5", "balance_15", "balance_30", "resting_imb", "classified_share_5")


def hm_min(s):
    return int(s[0:2]) * 60 + int(s[3:5])


def min_hm(m):
    return "%02d:%02d" % (m // 60, m % 60)


def ts_of(day, m):
    return "%sT%s:00+05:30" % (day, min_hm(m))


def bin_of(m):
    return 555 + 5 * ((m - 555) // 5 + 1)


def _iv(s):
    return None if s is None or s == "" else int(s)


def _ratio(a, b):
    d = a + b
    return None if d <= 0 else (a - b) / d


def build_cycle(rows, added):
    """rows: iterable of dict(str -> str) with the tape_minute.csv columns. added: {token(int): 'HH:MM'}.

    Returns {"rows": [cycle row dicts], "tokens": [per-token event inputs], "info": counters}."""
    toks = {}
    info = {"rows_in": 0, "rows_in_session": 0, "rows_out_of_session": 0,
            "qty_out_of_session": {"buy": 0, "sell": 0, "uncl": 0, "gap": 0}}
    for r in rows:
        info["rows_in"] += 1
        tok = int(r["token"])
        m = hm_min(r["minute"])
        t = toks.get(tok)
        if t is None:
            t = toks[tok] = {"r0": r, "mins": {}}
        buy, sell, uncl, gap = int(r["buy_qty"]), int(r["sell_qty"]), int(r["uncl_qty"]), int(r["gap_qty"])
        if m < SESSION_OPEN or m >= SESSION_END:
            info["rows_out_of_session"] += 1
            q = info["qty_out_of_session"]
            q["buy"] += buy
            q["sell"] += sell
            q["uncl"] += uncl
            q["gap"] += gap
            continue
        if m in t["mins"]:
            raise ValueError("duplicate minute row: token %d minute %s" % (tok, r["minute"]))
        info["rows_in_session"] += 1
        t["mins"][m] = (buy, sell, uncl, gap, int(r["trades"]), _iv(r["bid_qty_5"]), _iv(r["ask_qty_5"]), _iv(r["oi"]))

    out_rows, out_tokens = [], []
    info.update({"tokens_seen": len(toks), "tokens_no_session_rows": [], "first_seen_fallback": [],
                 "data_before_added": [], "tokens_in_map_without_rows": sorted(set(added) - set(toks))})
    keys = {}
    order = sorted(toks, key=lambda k: (toks[k]["r0"]["sym"], 0 if toks[k]["r0"]["role"] == "FUT" else 1,
                                        float(toks[k]["r0"]["strike"] or 0.0), toks[k]["r0"]["opt_type"], k))
    for tok in order:
        t = toks[tok]
        r0, mins = t["r0"], t["mins"]
        if not mins:
            info["tokens_no_session_rows"].append(tok)
            continue
        leg = "FUT" if r0["role"] == "FUT" else r0["opt_type"]
        key = (r0["sym"], r0["expiry"], r0["strike"], leg)
        if key in keys:
            raise ValueError("two tokens for one strike-leg: %r tokens %d and %d" % (key, keys[key], tok))
        keys[key] = tok
        fm = min(mins)
        a = added.get(tok)
        if a is None:
            info["first_seen_fallback"].append(tok)
            seen = fm
        else:
            seen = min(hm_min(a), fm)
            if fm < hm_min(a):
                info["data_before_added"].append(tok)
        first_T = bin_of(max(seen, SESSION_OPEN))

        bins = {}
        for m in sorted(mins):
            buy, sell, uncl, gap, trades, bid, ask, oi = mins[m]
            T = bin_of(m)
            b = bins.get(T)
            if b is None:
                b = bins[T] = [0, 0, 0, 0, 0, 0, None, None, None]
            b[0] += buy
            b[1] += sell
            b[2] += uncl
            b[3] += gap
            b[4] += trades
            b[5] += 1
            b[6], b[7] = bid, ask
            if oi is not None:
                b[8] = oi

        cb = cs = cu = cg = 0
        hist = []
        prev_oi = None
        have_prev = False
        ev_bins = []
        day = r0["day"]
        for T in range(first_T, LAST_T + 1, STEP):
            b = bins.get(T) or [0, 0, 0, 0, 0, 0, None, None, None]
            cb += b[0]
            cs += b[1]
            cu += b[2]
            cg += b[3]
            hist.append((b[0], b[1]))
            b15, s15 = sum(x[0] for x in hist[-3:]), sum(x[1] for x in hist[-3:])
            b30, s30 = sum(x[0] for x in hist[-6:]), sum(x[1] for x in hist[-6:])
            resting = None if b[6] is None or b[7] is None else _ratio(b[6], b[7])
            cls = b[0] + b[1] + b[2]
            out_rows.append({
                "symbol": r0["sym"], "expiry": r0["expiry"], "strike": r0["strike"], "leg": leg, "token": tok,
                "tradingsymbol": r0["tradingsymbol"], "T": ts_of(day, T),
                "buy_5": b[0], "sell_5": b[1], "uncl_5": b[2], "gap_5": b[3], "trades_5": b[4],
                "buy_15": b15, "sell_15": s15, "buy_30": b30, "sell_30": s30,
                "balance_5": _ratio(b[0], b[1]), "balance_15": _ratio(b15, s15), "balance_30": _ratio(b30, s30),
                "resting_imb": resting,
                "classified_share_5": None if cls <= 0 else (b[0] + b[1]) / cls,
                "buy_cum": cb, "sell_cum": cs, "uncl_cum": cu, "gap_cum": cg,
                "oi_last": b[8], "oi_delta_5": (b[8] - prev_oi) if (have_prev and b[8] is not None and prev_oi is not None) else None,
                "minutes_present_5": b[5], "first_seen_T": ts_of(day, first_T)})
            prev_oi, have_prev = b[8], True
            ev_bins.append((T, b[0], b[1]))
        out_tokens.append({"symbol": r0["sym"], "expiry": r0["expiry"], "strike": r0["strike"], "leg": leg,
                           "token": tok, "day": day, "role": r0["role"], "bins": ev_bins,
                           "depth": {m: (v[5], v[6]) for m, v in mins.items()}})
    out_rows.sort(key=lambda x: (x["symbol"], x["expiry"] or "", float(x["strike"] or 0.0), x["leg"], x["T"]))
    return {"rows": out_rows, "tokens": out_tokens, "info": info}


def _fmt(col, v):
    if v is None:
        return ""
    if col in _FLOATS:
        return "%.6f" % v
    return str(v)


def render_cycle_csv(rows):
    lines = [",".join(CYCLE_COLS)]
    for r in rows:
        lines.append(",".join(_fmt(c, r[c]) for c in CYCLE_COLS))
    return "\n".join(lines) + "\n"
