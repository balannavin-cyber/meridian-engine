"""Minute rows, G3 aggregation, verdict and report rendering (tape phase T1a, plan D-6 to D-8).

PURE: stdlib only, no clock, no randomness, no I/O. Everything here turns numbers into numbers or
strings; the CLI wrapper (services/tape_offline/process_day.py) does all reading and writing.

Data quality only: completeness, classified share, rule mix, invariants. Nothing in this module joins
a tape row with any other data set.
"""
import json
from collections import Counter

BUCKETS = ("pre_0915", "0915_1000", "1000_1100", "1100_1200", "1200_1300", "1300_1400", "1400_1500",
           "1500_1530", "post_1530", "unknown")
EARLY = ("0915_1000",)
SESSION_BUCKETS = tuple(b for b in BUCKETS if b not in ("pre_0915", "post_1530", "unknown"))   # a special day's in-window hours
SPECIAL_VERDICT = "NOT EVALUATED (special session)"
LATE = ("1000_1100", "1100_1200", "1200_1300", "1300_1400", "1400_1500", "1500_1530")
GROUPS = ("ATM3_CE", "ATM3_PE", "OTHER_CE", "OTHER_PE", "FUT", "NO_ATM")
OPTION_GROUPS = ("ATM3_CE", "ATM3_PE", "OTHER_CE", "OTHER_PE", "NO_ATM")
REASONS = ("bad_line", "stale_date", "no_exchange_ts", "unmapped_token", "duplicate", "late_beyond_watermark",
           "volume_regression", "no_volume")
RULES = ("above_ask", "below_bid", "above_mid", "below_mid", "tick_up", "tick_down", "tick_flat", "no_quote", "gap")
IMPLIED = {"above_ask": "BUY", "below_bid": "SELL", "above_mid": "BUY", "below_mid": "SELL", "tick_up": "BUY",
           "tick_down": "SELL", "tick_flat": "UNCL", "no_quote": "UNCL"}

# G3 thresholds (percent of volume, integer arithmetic), written beside the definition they come from:
# 50 % in the first 45 minutes, 70 % afterwards. MIN_DELTAS is a floor below which a share is noise.
EARLY_MIN_PCT = 50
LATE_MIN_PCT = 70
MIN_DELTAS = 200

COLS = ("day", "sym", "role", "opt_type", "strike", "expiry", "token", "tradingsymbol", "minute", "buy_qty",
        "sell_qty", "uncl_qty", "gap_qty", "trades", "vwap", "bid_qty_5", "ask_qty_5", "oi", "oi_delta",
        "exch_ts_max")
_ROLE_ORDER = {"FUT": 0, "OPT": 1}


class RuleParityError(AssertionError):
    """The rule label and the side classify() returned disagree: the rule column would be lying."""


def bucket_of(hhmm, win=None):
    """Hour bucket of an IST HH:MM. ``win`` = (open, close) on a special session, else None. A special window
    must lie inside 09:15-15:40 (the processor refuses others), so before open / at-or-after close map to the
    existing pre_0915 / post_1530 buckets and the minutes in between keep their clock-hour bucket. The F&O
    close of a special session can be 15:40 (Muhurat 2026-11-08, NSE/FAOP/76940): there the in-window minutes
    from 15:30 belong to the session, so the 1500_1530 bucket runs to the window close on a special day. (A
    normal day, win=None, is unchanged: 15:30 and later is post_1530.)"""
    if not isinstance(hhmm, str) or len(hhmm) != 5 or hhmm[2] != ":":
        return "unknown"
    if win is not None:
        if hhmm < win[0]:
            return "pre_0915"
        if hhmm >= win[1]:
            return "post_1530"
        if hhmm >= "15:00":
            return "1500_1530"
    if hhmm < "09:15":
        return "pre_0915"
    if hhmm < "10:00":
        return "0915_1000"
    if hhmm >= "15:30":
        return "post_1530"
    if hhmm >= "15:00":
        return "1500_1530"
    h = int(hhmm[:2])
    return "%02d00_%02d00" % (h, h + 1)


def rule_of(prev, pkt):
    """Which branch of classify() decided this delta. prev / pkt carry .ltp .bid .ask."""
    p, bid, ask = pkt.ltp, prev.bid, prev.ask
    if p is None or bid is None or ask is None or not (0 < bid <= ask):
        return "no_quote"
    if p >= ask:
        return "above_ask"
    if p <= bid:
        return "below_bid"
    mid = (bid + ask) / 2.0
    if p > mid:
        return "above_mid"
    if p < mid:
        return "below_mid"
    lp = prev.ltp
    if lp is not None and p > lp:
        return "tick_up"
    if lp is not None and p < lp:
        return "tick_down"
    return "tick_flat"


def check_rule(rule, side):
    if IMPLIED.get(rule) != side:
        raise RuleParityError("rule %r implies %r but classify returned %r" % (rule, IMPLIED.get(rule), side))


# ------------------------------------------------------------------------------ minute rows
class MinuteBook:
    """(token, minute) -> quantities. Row slots: 0 buy, 1 sell, 2 uncl, 3 gap, 4 trades, 5 price*qty,
    6 qty, 7 bid_qty_5, 8 ask_qty_5, 9 oi, 10 exch_ts_max."""

    def __init__(self):
        self._r = {}

    def touch(self, tok, mn, pk):
        r = self._r.get((tok, mn))
        if r is None:
            r = self._r[(tok, mn)] = [0, 0, 0, 0, 0, 0.0, 0, None, None, None, None]
        r[7], r[8], r[9] = pk.bq, pk.aq, pk.oi
        if pk.exts is not None and (r[10] is None or pk.exts > r[10]):
            r[10] = pk.exts

    def add(self, tok, mn, side, qty, price):
        r = self._r[(tok, mn)]
        if side == "BUY": r[0] += qty
        elif side == "SELL": r[1] += qty
        elif side == "UNCL": r[2] += qty
        else: r[3] += qty
        if side != "GAP":
            r[4] += 1
            if price is not None:
                r[5] += price * qty
                r[6] += qty

    def rows(self, day, meta):
        out = []
        last_oi = {}
        for (tok, mn) in sorted(self._r):
            r = self._r[(tok, mn)]
            m = meta[tok]
            prev = last_oi.get(tok)
            oi_delta = (r[9] - prev) if (r[9] is not None and prev is not None) else None
            if r[9] is not None:
                last_oi[tok] = r[9]
            out.append({"day": day, "sym": m["sym"], "role": m["role"], "opt_type": m.get("opt_type"),
                        "strike": m.get("strike"), "expiry": m.get("expiry"), "token": tok,
                        "tradingsymbol": m.get("tradingsymbol"), "minute": mn, "buy_qty": r[0], "sell_qty": r[1],
                        "uncl_qty": r[2], "gap_qty": r[3], "trades": r[4],
                        "vwap": (r[5] / r[6]) if r[6] else None, "bid_qty_5": r[7], "ask_qty_5": r[8],
                        "oi": r[9], "oi_delta": oi_delta, "exch_ts_max": r[10]})
        out.sort(key=lambda x: (x["sym"], _ROLE_ORDER.get(x["role"], 2), x["strike"] or 0.0, x["opt_type"] or "",
                                x["token"], x["minute"]))
        return out


# ------------------------------------------------------------------------------ G3 cells
class G3Book:
    def __init__(self):
        self.cells = {}
        self.discards = {}

    def add(self, bucket, group, side, rule, qty):
        c = self.cells.get((bucket, group))
        if c is None:
            c = self.cells[(bucket, group)] = {"q": [0, 0, 0, 0], "rules": {}, "hist": Counter()}
        c["q"][("BUY", "SELL", "UNCL", "GAP").index(side)] += qty
        r = c["rules"].setdefault(rule, [0, 0])
        r[0] += qty
        r[1] += 1
        if side != "GAP":
            c["hist"][qty] += 1

    def disc(self, reason, bucket):
        k = (reason, bucket)
        self.discards[k] = self.discards.get(k, 0) + 1

    def export(self):
        cells = {}
        for (bk, grp), c in sorted(self.cells.items()):
            cells.setdefault(bk, {})[grp] = {"q": list(c["q"]), "rules": {k: list(v) for k, v in sorted(c["rules"].items())},
                                             "hist": {str(k): v for k, v in sorted(c["hist"].items())}}
        disc = {r: {b: self.discards.get((r, b), 0) for b in BUCKETS} for r in REASONS}
        return cells, disc


def _pctl(hist, num, den):
    n = sum(hist.values())
    if not n:
        return None
    rank = -(-n * num // den)
    acc = 0
    for k in sorted(hist):
        acc += hist[k]
        if acc >= rank:
            return k
    return max(hist)


def _merge(cells):
    q, rules, hist = [0, 0, 0, 0], {}, Counter()
    for c in cells:
        for i in range(4):
            q[i] += c["q"][i]
        for k, v in c["rules"].items():
            r = rules.setdefault(k, [0, 0])
            r[0] += v[0]
            r[1] += v[1]
        for k, v in c["hist"].items():
            hist[int(k)] += v
    return {"q": q, "rules": rules, "hist": hist}


def _r6(x):
    return None if x is None else round(x, 6)


def cell_json(c):
    b, s, u, g = c["q"]
    ex = b + s + u
    hist = c["hist"] if isinstance(c["hist"], Counter) else Counter({int(k): v for k, v in c["hist"].items()})
    return {"buy": b, "sell": s, "uncl": u, "gap": g,
            "share_ex_gap": _r6((b + s) / ex) if ex else None,
            "share_incl_gap": _r6((b + s) / (ex + g)) if ex + g else None,
            "rules": {k: {"qty": v[0], "count": v[1]} for k, v in sorted(c["rules"].items())},
            "delta": {"n": sum(hist.values()), "p50": _pctl(hist, 50, 100), "p99": _pctl(hist, 99, 100),
                      "max": max(hist) if hist else None}}


def _window(cells, buckets):
    q = [0, 0, 0, 0]
    n = 0
    for bk in buckets:
        for grp in OPTION_GROUPS:
            c = cells.get(bk, {}).get(grp)
            if c:
                for i in range(4):
                    q[i] += c["q"][i]
                n += sum(c["hist"].values())
    return q, n


def verdict(cells, special=False):
    out = {}
    if special:
        # G3's early / late split does not apply to a special session: one overall share, no PASS / FAIL
        q, n = _window(cells, SESSION_BUCKETS)
        tot = q[0] + q[1] + q[2]
        out["overall"] = {"classified_qty": q[0] + q[1], "volume_ex_gap": tot, "gap_qty": q[3], "n_deltas": n,
                          "share_pct": _r6(100.0 * (q[0] + q[1]) / tot) if tot else None}
        return SPECIAL_VERDICT, out
    for name, bks in (("early", EARLY), ("late", LATE)):
        q, n = _window(cells, bks)
        tot = q[0] + q[1] + q[2]
        out[name] = {"classified_qty": q[0] + q[1], "volume_ex_gap": tot, "gap_qty": q[3], "n_deltas": n,
                     "share_pct": _r6(100.0 * (q[0] + q[1]) / tot) if tot else None}
    out["thresholds_pct"] = {"early": EARLY_MIN_PCT, "late": LATE_MIN_PCT, "min_deltas": MIN_DELTAS}
    e, l = out["early"], out["late"]
    if e["n_deltas"] < MIN_DELTAS or l["n_deltas"] < MIN_DELTAS:
        return "NOT EVALUATED", out
    ok = (e["classified_qty"] * 100 >= EARLY_MIN_PCT * e["volume_ex_gap"]
          and l["classified_qty"] * 100 >= LATE_MIN_PCT * l["volume_ex_gap"])
    return ("PASS" if ok else "FAIL"), out


# ------------------------------------------------------------------------------ invariants
def check_invariants(rows, spans, pkt_lines, accounted):
    """Rows are the rows that will be WRITTEN; spans are the replay's own volume_last - volume_first."""
    sums = {}
    for r in rows:
        sums[r["token"]] = sums.get(r["token"], 0) + r["buy_qty"] + r["sell_qty"] + r["uncl_qty"] + r["gap_qty"]
    fails = []
    for tok in sorted(spans):
        want = int(spans[tok][1] - spans[tok][0])
        if sums.get(tok, 0) != want:
            fails.append({"token": tok, "rows_sum": sums.get(tok, 0), "volume_span": want})
    total_rows = sum(sums.values())
    total_span = sum(int(v[1] - v[0]) for v in spans.values())
    ds = not fails and total_rows == total_span
    pc = pkt_lines == accounted
    return {"ok": ds and pc, "delta_sum_ok": ds, "packet_conservation_ok": pc, "failures": fails[:20],
            "rows_sum_total": total_rows, "volume_span_total": total_span, "pkt_lines": pkt_lines,
            "accounted": accounted}


# ------------------------------------------------------------------------------ report
def symbol_section(res, special=False):
    cells = res["cells"]
    v, detail = verdict(cells, special)
    if not res["invariants"]["ok"]:
        v = "INVALID"
    hours = {bk: {grp: cell_json(c) for grp, c in sorted(gs.items())} for bk, gs in cells.items()}
    by_group = {}
    for grp in GROUPS:
        cs = [gs[grp] for gs in cells.values() if grp in gs]
        if cs:
            by_group[grp] = cell_json(_merge(cs))
    allc = [c for gs in cells.values() for c in gs.values()]
    rule_mix = {k: {"qty": x[0], "count": x[1]} for k, x in sorted(_merge(allc)["rules"].items())}
    return {"verdict": v, "verdict_detail": detail, "invariants": res["invariants"], "packets": res["counters"],
            "discards": res["discards"], "hours": hours, "by_group": by_group, "rule_mix": rule_mix,
            "baseline_qty": res["baseline_qty"], "tokens_no_packets": res["tokens_no_packets"],
            "gaps": res["gaps"], "restarts": res["restarts"], "errors": res["errors"],
            "ctl_events": res.get("ctl_events", {})}


def reconcile(symbols, daily):
    """Daily-report connection counters against the control lines in the segments (T0.1 plan s3). The ctl lines
    are written to every symbol's file, so one symbol's counts are THE event log. Each check names the event it
    compares; a report that predates a counter simply has no check for it."""
    if not isinstance(daily, dict) or daily.get("unreadable") or not symbols:
        return {"ok": None, "note": "no readable daily report"}
    sym = "NIFTY" if "NIFTY" in symbols else sorted(symbols)[0]
    ev = symbols[sym].get("ctl_events") or {}
    checks = []

    def chk(name, log, rep):
        if rep is not None:
            checks.append({"name": name, "log": log, "report": rep, "ok": log == rep})
    chk("connects", ev.get("connect", 0), daily.get("connects"))
    chk("reconnects (= connects - 1)", max(0, ev.get("connect", 0) - 1), daily.get("reconnects"))
    chk("disconnects", ev.get("disconnect", 0), daily.get("disconnects"))
    chk("reconnect_attempts", ev.get("reconnect", 0), daily.get("reconnect_attempts"))
    chk("watchdog_trips", ev.get("watchdog", 0), daily.get("watchdog_trips"))
    return {"ok": all(c["ok"] for c in checks), "symbol": sym, "checks": checks}


def build_report(day, results, daily, conflicts, inputs, session=None):
    special = bool(session and session.get("kind") == "special")
    rep = {"schema": "g3_report_v1", "day": day,
           "symbols": {s: symbol_section(r, special) for s, r in sorted(results.items())},
           "daily_report": daily, "token_map": {"conflicts": conflicts}, "inputs": inputs}
    rep["reconcile"] = reconcile(rep["symbols"], daily)
    if special:
        rep["session"] = session
    return rep


def render_json(obj):
    return json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def _fmt(col, v):
    if v is None:
        return ""
    if col == "vwap":
        return "%.6f" % v
    if col == "strike":
        return "%d" % v if v == int(v) else "%.2f" % v
    return str(v)


def render_csv(rows):
    lines = [",".join(COLS)]
    for r in rows:
        lines.append(",".join(_fmt(c, r[c]) for c in COLS))
    return "\n".join(lines) + "\n"


def render_text(rep):
    L = ["MERIDIAN tape T1a - G3 report for %s" % rep["day"], ""]
    for sym, s in rep["symbols"].items():
        d = s["verdict_detail"]
        L.append("=== %s: G3 VERDICT %s ===" % (sym, s["verdict"]))
        if "overall" in d:
            w = d["overall"]
            sp = "n/a" if w["share_pct"] is None else "%.2f %%" % w["share_pct"]
            ses = rep.get("session") or {}
            L.append("  %-12s classified share %s of option volume, %d option deltas (special session %s: no early / late split;"
                     " bucket pre_0915 = before the open, post_1530 = at or after the close)"
                     % ("%s-%s" % (ses.get("open"), ses.get("close")), sp, w["n_deltas"], ses.get("label")))
        else:
            for name, label in (("early", "09:15-10:00"), ("late", "10:00-15:30")):
                w = d[name]
                sp = "n/a" if w["share_pct"] is None else "%.2f %%" % w["share_pct"]
                L.append("  %-12s classified share %s of option volume, %d option deltas (need >= %d %%, >= %d deltas)"
                         % (label, sp, w["n_deltas"], d["thresholds_pct"][name], d["thresholds_pct"]["min_deltas"]))
        iv = s["invariants"]
        L.append("  invariants: %s (rows sum %d vs volume span %d; packets %d read, %d accounted)"
                 % ("OK" if iv["ok"] else "VIOLATED", iv["rows_sum_total"], iv["volume_span_total"],
                    iv["pkt_lines"], iv["accounted"]))
        pk = s["packets"]
        L.append("  lines %d: packets %d, ctl %d, bad %d, other %d; chain %d, index %d, gap pairs %d"
                 % (pk["lines"], pk["pkt_lines"], pk["ctl_lines"], pk["bad_lines"], pk["other_lines"],
                    pk["chain_pkts"], pk["index_pkts"], pk["gap_pairs"]))
        L.append("  baseline volume (before first packet, side unknown): %d; restarts: %d" % (s["baseline_qty"], s["restarts"]))
        L.append("  excluded packets by reason and hour (every excluded packet is counted here)")
        L.append("  %-22s" % "" + "".join("%10s" % b for b in BUCKETS))
        for r in REASONS:
            L.append("  %-22s" % r + "".join("%10d" % s["discards"][r][b] for b in BUCKETS))
        L.append("  classified share by hour and group (share ex-gap | incl-gap, quantities in contracts)")
        L.append("  %-10s %-9s %10s %10s %10s %10s %8s %8s %7s %7s %7s" % (
            "hour", "group", "buy", "sell", "uncl", "gap", "ex-gap", "incl", "d.p50", "d.p99", "d.max"))
        for bk in BUCKETS:
            for grp, c in s["hours"].get(bk, {}).items():
                L.append("  %-10s %-9s %10d %10d %10d %10d %8s %8s %7s %7s %7s" % (
                    bk, grp, c["buy"], c["sell"], c["uncl"], c["gap"], _pc(c["share_ex_gap"]),
                    _pc(c["share_incl_gap"]), c["delta"]["p50"], c["delta"]["p99"], c["delta"]["max"]))
        L.append("  rule mix (qty / deltas): " + ", ".join("%s %d/%d" % (k, v["qty"], v["count"]) for k, v in s["rule_mix"].items()))
        g = s["gaps"]
        L.append("  gap events %d (%s); gap pairs %d; gap volume %d"
                 % (len(g["events"]), ", ".join(e["kind"] for e in g["events"]), g["gap_pairs"], g["gap_qty"]))
        L.append("  tokens with no packets (%d): %s" % (len(s["tokens_no_packets"]), ", ".join(s["tokens_no_packets"][:20])))
        for e in s["errors"]:
            L.append("  ctl error: code=%s reason=%s" % (e["code"], e["reason"]))
        L.append("")
    dr = rep.get("daily_report")
    if dr:
        L.append("daily_report: " + json.dumps(dr, sort_keys=True))
    rc = rep.get("reconcile") or {}
    if rc.get("checks"):
        L.append("reconcile (daily report vs control lines in %s): %s" % (rc["symbol"], "OK" if rc["ok"] else "MISMATCH"))
        for c in rc["checks"]:
            L.append("  %-26s log %s  report %s  %s" % (c["name"], c["log"], c["report"], "ok" if c["ok"] else "MISMATCH"))
    if rep["token_map"]["conflicts"]:
        L.append("token map conflicts: %d" % len(rep["token_map"]["conflicts"]))
    L.append("inputs: " + json.dumps(rep["inputs"], sort_keys=True))
    return "\n".join(L) + "\n"


def _pc(x):
    return "-" if x is None else "%.1f%%" % (100.0 * x)
