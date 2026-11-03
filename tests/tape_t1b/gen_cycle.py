"""Synthetic tape_minute.csv + subscriptions generator with PLANTED truth (tape T1b, docs/tape/T1b_plan.md section 2).

Ground truth is decided here, by construction and by brute-force loops that share no code with merdian_compute:
every expected number below comes from this file, never from the module under test.
"""
import csv
import json
import os
import random
import statistics
from fractions import Fraction

DAY = "2026-11-03"
EXPIRY_OPT = "2026-11-05"
EXPIRY_FUT = "2026-11-24"
COLS = ["day", "sym", "role", "opt_type", "strike", "expiry", "token", "tradingsymbol", "minute", "buy_qty",
        "sell_qty", "uncl_qty", "gap_qty", "trades", "vwap", "bid_qty_5", "ask_qty_5", "oi", "oi_delta", "exch_ts_max"]
OPEN, END = 555, 930          # 09:15, 15:30 in minutes


def hm(m):
    return "%02d:%02d" % (m // 60, m % 60)


def iso(m):
    return "%sT%s:00+05:30" % (DAY, hm(m))


class Tok:
    def __init__(self, token, sym, role, opt, strike, added, first_T, expiry=None):
        self.token, self.sym, self.role, self.opt, self.strike = token, sym, role, opt, strike
        self.added, self.first_T = added, first_T
        self.expiry = expiry or (EXPIRY_FUT if role == "FUT" else EXPIRY_OPT)
        self.mins = {}      # in-session minute -> dict
        self.oos = {}       # out-of-session minute -> dict
        self.emits = True

    @property
    def leg(self):
        return "FUT" if self.role == "FUT" else self.opt

    @property
    def tsym(self):
        return "%s%s%s" % (self.sym, self.strike if self.strike is not None else "FUT", self.opt or "")


def mrow(buy=0, sell=0, uncl=0, gap=0, trades=0, bid=1000, ask=1000, oi=100000):
    return {"buy": buy, "sell": sell, "uncl": uncl, "gap": gap, "trades": trades, "bid": bid, "ask": ask, "oi": oi}


def fill(tok, first_m=OPEN, fn=None):
    for m in range(first_m, END):
        tok.mins[m] = fn(m) if fn else mrow()
    return tok


# ---------------------------------------------------------------------------------------- reference detectors
def ref_conc(aggs):
    """Reference CONC with statistics.pstdev and float z; returns [(index, z1, z2)]."""
    out, armed, prev_c = [], True, False
    z_prev = None
    for i, a in enumerate(aggs):
        c, z = False, None
        if i >= 12:
            prior = aggs[:i]
            sd = statistics.pstdev(prior)
            if sd > 0:
                z = (a - statistics.fmean(prior)) / sd
                c = z >= 3
        if c and prev_c and armed:
            out.append((i, z_prev, z))
            armed = False
        if not c:
            armed = True
        prev_c, z_prev = c, z
    return out


def ref_thin(vals):
    """vals: {minute: value or None}. Reference THIN with statistics.median and exact Fractions."""
    out, flag, armed = [], {}, True
    for m in sorted(k for k in vals if vals[k] is not None):
        win = [vals[k] for k in range(m - 30, m) if vals.get(k) is not None]
        c = False
        if len(win) >= 20:
            med = Fraction(statistics.median(win))
            c = med > 0 and Fraction(vals[m]) <= med / 2
        if c and flag.get(m - 1) and armed:
            out.append(m)
            armed = False
        if not c:
            armed = True
        flag[m] = c
    return out


# ---------------------------------------------------------------------------------------- the planted day
ALT = lambda i: 90 if i % 2 == 0 else 110      # mean 100, population std 10


def conc_token(token, strike, plan):
    """plan: {bin index: agg}; other bins alternate 90 / 110. agg goes into the first minute of the bin, as buy."""
    t = Tok(token, "NIFTY", "OPT", "CE", strike, "09:00", 560)
    for m in range(OPEN, END):
        t.mins[m] = mrow()
    for i in range(75):
        agg = plan.get(i, ALT(i))
        t.mins[OPEN + 5 * i]["buy"] = agg
    return t


def depth_token(token, strike, bid=None, ask=None):
    bid, ask = bid or {}, ask or {}
    t = Tok(token, "NIFTY", "OPT", "CE", strike, "09:00", 560)
    for m in range(OPEN, END):
        j = m - OPEN
        b = bid.get(j, 1000)
        t.mins[m] = mrow(bid=None if b == "ABSENT" else b, ask=ask.get(j, 1000))
    return t


def planted():
    """-> (tokens, hand_events). hand_events: {(strike, kind, side): [expected ts]} planted by hand."""
    toks = []
    # --- CONC
    c1 = conc_token(3001, 25000, {12: 1000, 13: 1000})
    c2 = conc_token(3002, 25100, {14: 1000})
    c3 = conc_token(3003, 25200, {11: 1000, 12: 1000})
    flat = {i: 100 for i in range(75)}
    flat.update({14: 1000, 15: 1000})
    c4 = conc_token(3004, 25300, flat)
    c5 = conc_token(3005, 25400, {12: 125, 13: 130})
    c6 = conc_token(3006, 25500, {12: 1000, 13: 5000, 14: 25000, 15: 125000})
    toks += [c1, c2, c3, c4, c5, c6]
    # --- THIN (flows all zero)
    toks.append(depth_token(4001, 26000, bid={30: 500, 31: 500}))
    toks.append(depth_token(4002, 26100, bid={30: 500}))
    toks.append(depth_token(4003, 26200, bid={30: 510, 31: 510}))
    trap = {j: 100 for j in range(16)}
    trap.update({j: 1000 for j in range(16, 30)})
    trap.update({30: 60, 31: 60})
    toks.append(depth_token(4004, 26300, bid=trap))
    toks.append(depth_token(4005, 26400, bid={60: 300, 61: 300, 62: "ABSENT", 63: 300, 64: 300, 65: 300}))
    toks.append(depth_token(4006, 26500, ask={40: 400, 41: 400}))
    hand = {
        (25000, "CONC", "buy"): [iso(560 + 5 * 13)],
        (25500, "CONC", "buy"): [iso(560 + 5 * 13)],
        (26000, "THIN", "bid"): [iso(OPEN + 31 + 1)],
        (26400, "THIN", "bid"): [iso(OPEN + 61 + 1)],
        (26500, "THIN", "ask"): [iso(OPEN + 41 + 1)],
    }
    return toks, hand


def random_tokens(rng):
    toks = []

    def flows(m):
        return mrow(buy=rng.randint(0, 9), sell=rng.randint(0, 9), uncl=rng.randint(0, 3),
                    gap=40 if rng.random() < 0.04 else 0, trades=rng.randint(0, 9), bid=rng.randint(900, 1100),
                    ask=rng.randint(900, 1100), oi=100000 + rng.randint(0, 5000))
    spec = [(1001, "NIFTY", "OPT", "CE", 24500), (1002, "NIFTY", "OPT", "PE", 24500), (1003, "NIFTY", "OPT", "CE", 24600),
            (1004, "NIFTY", "FUT", None, None), (2001, "SENSEX", "OPT", "CE", 80000)]
    for tk, sym, role, opt, strike in spec:
        toks.append(fill(Tok(tk, sym, role, opt, strike, "09:00", 560), fn=flows))
    late = Tok(1005, "NIFTY", "OPT", "CE", 24700, "10:03", 605)
    fill(late, first_m=603, fn=flows)
    toks.append(late)
    holey = Tok(1006, "NIFTY", "OPT", "PE", 24400, "09:00", 560)
    for m in range(OPEN, END):
        if rng.random() < 0.2:
            continue
        r = flows(m)
        if rng.random() < 0.1:
            r["oi"] = None
        holey.mins[m] = r
    toks.append(holey)
    toks[0].oos = {545: mrow(buy=7, sell=3, uncl=1), 935: mrow(buy=4, sell=2, uncl=0, gap=9)}
    toks[1].oos = {480: mrow(buy=11, sell=5, uncl=2)}
    return toks


def write_day(root, toks, extra_map_tokens=()):
    inp = os.path.join(root, "in")
    sess = os.path.join(root, "session", DAY)
    os.makedirs(inp, exist_ok=True)
    os.makedirs(sess, exist_ok=True)
    with open(os.path.join(inp, "tape_minute.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(COLS)
        for t in sorted(toks, key=lambda x: x.token):
            allm = dict(t.oos)
            allm.update(t.mins)
            for m in sorted(allm):
                r = allm[m]
                w.writerow([DAY, t.sym, t.role, t.opt or "", "" if t.strike is None else "%d" % t.strike, t.expiry,
                            t.token, t.tsym, hm(m), r["buy"], r["sell"], r["uncl"], r["gap"], r["trades"], "",
                            "" if r["bid"] is None else r["bid"], "" if r["ask"] is None else r["ask"],
                            "" if r["oi"] is None else r["oi"], "", ""])

    def row(t, added):
        return {"token": t.token, "sym": t.sym, "role": t.role, "strike": None if t.strike is None else float(t.strike),
                "opt_type": t.opt, "tradingsymbol": t.tsym, "expiry": t.expiry, "added_minute": added, "reason": "x"}
    early = [row(t, t.added) for t in toks if t.added == "09:00"] + [row(Tok(t, "NIFTY", "OPT", "CE", 99999, "09:00", 560), "09:00")
                                                                      for t in extra_map_tokens]
    full = early + [row(t, t.added) for t in toks if t.added != "09:00"]
    for name, rows in (("subscriptions_090000.json", early), ("subscriptions_100300.json", full)):
        with open(os.path.join(sess, name), "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"day": DAY, "written_ist": name, "n": len(rows), "tokens": rows}, fh)
    return inp, os.path.join(root, "session")


# ---------------------------------------------------------------------------------------- brute-force truth
def fmt(v, kind="int"):
    if v is None:
        return ""
    return "%.6f" % v if kind == "f" else str(v)


def truth_cycle(tok):
    """{T: {field: expected string}} for one token, by brute force over minutes. Independent of cycle.py."""
    Ts = list(range(tok.first_T, END + 1, 5))
    res, cum, prev_oi = {}, [0, 0, 0, 0], None
    per = []
    for idx, T in enumerate(Ts):
        ms = [m for m in range(T - 5, T) if m in tok.mins]
        sums = [sum(tok.mins[m][k] for m in ms) for k in ("buy", "sell", "uncl", "gap", "trades")]
        per.append(sums)
        for i in range(4):
            cum[i] += sums[i]
        last = max(ms) if ms else None
        bid = tok.mins[last]["bid"] if last is not None else None
        ask = tok.mins[last]["ask"] if last is not None else None
        resting = None if bid is None or ask is None or bid + ask <= 0 else (bid - ask) / (bid + ask)
        oims = [m for m in ms if tok.mins[m]["oi"] is not None]
        oi = tok.mins[max(oims)]["oi"] if oims else None
        b15 = sum(p[0] for p in per[max(0, idx - 2):idx + 1])
        s15 = sum(p[1] for p in per[max(0, idx - 2):idx + 1])
        b30 = sum(p[0] for p in per[max(0, idx - 5):idx + 1])
        s30 = sum(p[1] for p in per[max(0, idx - 5):idx + 1])
        bal = lambda b, s: None if b + s == 0 else (b - s) / (b + s)
        cls = sums[0] + sums[1] + sums[2]
        res[T] = {"buy_5": fmt(sums[0]), "sell_5": fmt(sums[1]), "uncl_5": fmt(sums[2]), "gap_5": fmt(sums[3]),
                  "trades_5": fmt(sums[4]), "buy_15": fmt(b15), "sell_15": fmt(s15), "buy_30": fmt(b30), "sell_30": fmt(s30),
                  "balance_5": fmt(bal(sums[0], sums[1]), "f"), "balance_15": fmt(bal(b15, s15), "f"),
                  "balance_30": fmt(bal(b30, s30), "f"), "resting_imb": fmt(resting, "f"),
                  "classified_share_5": fmt(None if cls == 0 else (sums[0] + sums[1]) / cls, "f"),
                  "buy_cum": fmt(cum[0]), "sell_cum": fmt(cum[1]), "uncl_cum": fmt(cum[2]), "gap_cum": fmt(cum[3]),
                  "oi_last": fmt(oi), "oi_delta_5": fmt(oi - prev_oi if (oi is not None and prev_oi is not None and idx > 0) else None),
                  "minutes_present_5": fmt(len(ms)), "first_seen_T": iso(tok.first_T)}
        prev_oi = oi
    return res


def truth_totals(toks):
    """In-session and out-of-session quantity totals per category, by brute force."""
    ins = {"buy": 0, "sell": 0, "uncl": 0, "gap": 0}
    oos = dict(ins)
    for t in toks:
        for m, r in t.mins.items():
            for k in ins:
                ins[k] += r[k]
        for m, r in t.oos.items():
            for k in oos:
                oos[k] += r[k]
    return ins, oos


def expected_events(toks, hand):
    """Independent reference over ALL option tokens; also asserts it equals the hand-planted list for planted tokens."""
    ev = set()
    for t in toks:
        if t.leg not in ("CE", "PE"):
            continue
        aggs = [sum(t.mins[m]["buy"] + t.mins[m]["sell"] for m in range(T - 5, T) if m in t.mins) for T in range(t.first_T, END + 1, 5)]
        for i, z1, z2 in ref_conc(aggs):
            T = t.first_T + 5 * i
            side = "buy" if sum(t.mins[m]["buy"] for m in range(T - 5, T) if m in t.mins) > sum(t.mins[m]["sell"] for m in range(T - 5, T) if m in t.mins) else "sell"
            ev.add((t.sym, t.expiry, "%d" % t.strike, t.leg, "CONC", iso(T), side))
        for which, side in (("bid", "bid"), ("ask", "ask")):
            vals = {m: r[which] for m, r in t.mins.items()}
            for m in ref_thin(vals):
                ev.add((t.sym, t.expiry, "%d" % t.strike, t.leg, "THIN", iso(m + 1), side))
    got_hand = {}
    for e in ev:
        got_hand.setdefault((int(e[2]), e[4], e[6]), []).append(e[5])
    for k, v in hand.items():
        assert sorted(got_hand.get(k, [])) == sorted(v), "generator self-check: hand-planted %r vs reference %r" % (k, got_hand.get(k))
    planted_strikes = {t.strike for t in toks if t.token >= 3000}
    for e in ev:
        if int(e[2]) in planted_strikes:
            assert (int(e[2]), e[4], e[6]) in hand, "generator self-check: unplanted event %r" % (e,)
    return ev


def conc_z_truth(t):
    """z1, z2 of the planted burst (c1), by statistics.pstdev on the prior bins only."""
    aggs = [sum(t.mins[m]["buy"] + t.mins[m]["sell"] for m in range(T - 5, T)) for T in range(t.first_T, END + 1, 5)]
    z = lambda i: (aggs[i] - statistics.fmean(aggs[:i])) / statistics.pstdev(aggs[:i])
    return z(12), z(13)


def build(root, rng_seed=1234):
    rng = random.Random(rng_seed)
    ptoks, hand = planted()
    toks = random_tokens(rng) + ptoks
    # the z2-3 case must really sit in [2, 3) at both bins (a setup check, not a test of the code)
    c5 = [t for t in ptoks if t.token == 3005][0]
    aggs = [sum(c5.mins[m]["buy"] for m in range(T - 5, T)) for T in range(560, END + 1, 5)]
    for i in (12, 13):
        z = (aggs[i] - statistics.fmean(aggs[:i])) / statistics.pstdev(aggs[:i])
        assert 2.0 <= z < 3.0, "setup: z-between-2-and-3 case is z=%.3f at bin %d" % (z, i)
    ev = expected_events(toks, hand)
    inp, sess = write_day(root, toks, extra_map_tokens=(5001,))
    return {"inp": inp, "sess": sess, "toks": toks, "hand": hand, "events": ev,
            "totals": truth_totals(toks), "c1": [t for t in ptoks if t.token == 3001][0]}


def build_full(root, n_strikes=45, seed=99):
    """A synthetic full day: 2 symbols x (n_strikes x 2 legs + FUT), 08:00..15:39 every minute."""
    rng = random.Random(seed)
    toks, tk = [], 10000
    for sym, base, step in (("NIFTY", 24000, 50), ("SENSEX", 79000, 100)):
        for role, opt, strike in [("FUT", None, None)] + [("OPT", o, base + step * i) for i in range(n_strikes) for o in ("CE", "PE")]:
            tk += 1
            t = Tok(tk, sym, role, opt, strike, "09:00", 560)
            for m in range(480, 940):
                r = mrow(buy=rng.randint(0, 9), sell=rng.randint(0, 9), uncl=rng.randint(0, 3), trades=rng.randint(0, 9),
                         bid=rng.randint(900, 1100), ask=rng.randint(900, 1100), oi=100000 + rng.randint(0, 5000))
                (t.mins if OPEN <= m < END else t.oos)[m] = r
            toks.append(t)
    inp, sess = write_day(root, toks)
    return {"inp": inp, "sess": sess, "toks": toks}
