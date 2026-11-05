"""MERIDIAN tape scoring: H-A (agreement of the tape sign with the chain sign) and H-B (tape lead over chain events).

Implements pre-registration v0.4 (sha256 b45477d36eba6930ab41171a3405c10cf6ecb0bd1fbb04b52d09a5c2129acd57)
literally; docs/tape/scoring_plan.md (v0.2) and docs/tape/scoring_plan_v04.md (its diff) carry every first definition
(DEF-n) and override (OVR-n).

  python -m services.tape_scoring.score --inputs <dir> --out <dir> [--fixture] [--rerun-defect "<text>"]

Standard library only. No database, no network, no .env. Reads CSVs laid out as <inputs>/<relation>/<day>.csv
(the extract's layout). Exact arithmetic (fractions) for every sign, argmax, median and threshold comparison.
Sign only: no gex_cr / gamma magnitude and no D value reaches the output; the one magnitude-derived figure is the
scale-free share of |gex_cr| inside the subscribed window (descriptive, v0.4 section 1).

Entry-time discipline (CLAUDE.md rule 0a), one sentence per quantity:
  S at a cycle reads the tape rows stamped G-25 .. G only, G = floor5(T) (each covers [stamp-5, stamp), all < T);
  a tape event's wall / runner-up come from the latest run with ts <= the event's ts_ist;
  a lead reads tape events with t <= T only;  R(T) reads spot bars labelled hm(T) .. hm(T)+29 (the outcome, by design;
  the bar labelled hm(T) starts at G:00, the instant the run's spot describes - v0.4 section 1).
The descriptive block (window coverage, sign changes, per-label H-B, T4) is built by descriptive() and no decision
function reads it.
"""
import argparse
import bisect
import csv
import hashlib
import json
import os
import random
import re
import sys
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from fractions import Fraction

from services.tape_scoring import wilcoxon

PREREG_SHA = "b45477d36eba6930ab41171a3405c10cf6ecb0bd1fbb04b52d09a5c2129acd57"
IST = timezone(timedelta(hours=5, minutes=30))
PKG = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(PKG))
HASHED = ("scoring_extract.sql", "run_extract.sh", "score.py", "wilcoxon.py")
LEDGER = os.path.join(ROOT, "docs", "tape", "scoring_hashes.md")
RUNS_FIXED = os.path.join(ROOT, "docs", "tape", "scoring_runs.json")
SYMS = ("NIFTY", "SENSEX")
US_MIN = 60 * 10 ** 6

# The pre-registered parameters. One literal each; tests/test_tape_scoring.py (sc-params) lists them and their values.
PARAMS = {
    "ha_first_G_min": 600,
    "ha_last_G_min": 885,
    "cycle_share_min_pct": 50,
    "min_cycles_per_group": 3,
    "ha_min_days": 20,
    "ha_min_median_delta": Fraction(1, 10),
    "ha_p_max": Fraction(1, 10),
    "r_horizon_min": 30,
    "r_min_bars": 25,
    "hb_min_events": 300,
    "hb_min_days": 15,
    "hb_cov_min": Fraction(1, 2),
    "hb_lead_yes_min": 10,
    "hb_lead_no_max": 5,
    "match_window_min": 60,
    "null_draws": 100,
    "bootstrap_B": 1000,
    "null_pctile": 95,
    "completeness_min_pct": 95,
    "completeness_minutes": 375,
    "late_share_min_pct": 50,
    "trigger_expiries": 6,
    "trigger_days": 30,
    "wilcoxon_normal_above": 60,
    "spot_clock_min_pct": 95,
    "passive_side": {"CE": "ask", "PE": "ask"},
    "s_window_min": 30,
    "s_window_bins": 6,
    "e2_oi_move_pct": 5,
}
NO_T4 = "NOT COMPUTED (no tape_minute input)"
# one tape_strike_cycle row: expiry, strike, leg, the 5-minute bin columns (read for S) and the cumulative columns
# (extracted, never read for S in v0.4)
CycRow = namedtuple("CycRow", "exp k leg b5 s5 u5 g5 bc sc uc gc")
OPTIONAL = frozenset(("tape_minute_oi",))

MATCH = {
    "E1": frozenset(("T1", "T2")),
    "E2-call": frozenset(("T1", "T3")),
    "E2-put": frozenset(("T1", "T3")),
}

_TAPE = ("symbol", "trading_day")
COLS = {
    "tape_strike_cycle": _TAPE + ("expiry", "strike", "leg", "ts_ist", "buy_5", "sell_5", "uncl_5", "gap_5", "buy_cum",
                                  "sell_cum", "uncl_cum", "gap_cum", "first_seen_ts_ist", "run_id"),
    "tape_events": _TAPE + ("expiry", "strike", "leg", "kind", "ts_ist", "side", "magnitude", "run_id"),
    "tape_chain_events": _TAPE + ("expiry", "kind", "ts_ist", "strike", "merged_n", "run_id"),
    "tape_chain_runs": _TAPE + ("expiry", "ts_ist", "chain_run_id", "leader_strike", "call_wall", "put_wall",
                                "net_sign", "in_window", "run_id"),
    "tape_daily_report": _TAPE + ("classified_share_late", "report", "g3", "run_id"),
    "tape_minute": _TAPE + ("minute_ist", "run_id"),
    "gex_strike_snapshots": ("run_id", "symbol", "ts", "expiry_date", "strike", "gamma_call", "gamma_put", "oi_call",
                             "oi_put", "gex_cr"),
    "gamma_metrics": ("run_id", "symbol", "ts", "expiry_date", "straddle_atm"),
    "hist_spot_bars_1m": ("instrument_id", "trade_date", "bar_ts", "open", "high", "low", "close"),
    # OPTIONAL input (operator ruling, 2026-11-05): Kite OI per strike-leg-minute for the descriptive T4 only
    "tape_minute_oi": _TAPE + ("role", "opt_type", "strike", "expiry", "minute_ist", "oi", "run_id"),
}
INSTRUMENT_SYMBOL = {"9992f600-51b3-4009-b487-f878692a0bc5": "NIFTY", "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71": "SENSEX"}

_TS = re.compile(r"^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d)(?::(\d\d)(?:\.(\d+))?)?\s*(Z|[+-]\d\d(?::?\d\d)?)?$")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------------------------------- parsing

def parse_ts(s):
    m = _TS.match((s or "").strip())
    if not m:
        raise ValueError("bad timestamp %r" % s)
    y, mo, d, h, mi, se, fr, off = m.groups()
    if off is None:
        raise ValueError("timestamp without an offset: %r" % s)
    if off == "Z":
        tz = timezone.utc
    else:
        digits = off[1:].replace(":", "")
        delta = timedelta(hours=int(digits[:2]), minutes=int(digits[2:4]) if len(digits) >= 4 else 0)
        tz = timezone(-delta if off[0] == "-" else delta)
    us = int((fr or "0").ljust(6, "0")[:6])
    return datetime(int(y), int(mo), int(d), int(h), int(mi), int(se or 0), us, tzinfo=tz).astimezone(IST)


def us_of(dt):
    return (dt - _EPOCH) // timedelta(microseconds=1)


def hm(dt):
    return dt.hour * 60 + dt.minute


def frac(s):
    s = (s or "").strip()
    return None if s == "" else Fraction(s)


def to_int(s):
    f = Fraction((s or "0").strip() or "0")
    if f.denominator != 1:
        raise ValueError("not an integer quantity: %r" % s)
    return int(f)


def fstr(x):
    if x is None:
        return None
    if isinstance(x, float):
        return "%.6e" % x
    x = Fraction(x)
    return "%s (%.6f)" % (str(x), float(x))


def jsonable(o):
    if isinstance(o, Fraction):
        return fstr(o)
    if isinstance(o, float):
        return fstr(o)
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    return o


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return Fraction(s[n // 2]) if n % 2 else Fraction(s[n // 2 - 1] + s[n // 2], 2)


# ---------------------------------------------------------------------------------------------------- inputs

def discover_days(inputs):
    days = set()
    for rel in COLS:
        d = os.path.join(inputs, rel)
        if os.path.isdir(d):
            days.update(f[:-4] for f in os.listdir(d) if re.match(r"^\d{4}-\d\d-\d\d\.csv$", f))
    return sorted(days)


def read_rel(inputs, rel, day):
    p = os.path.join(inputs, rel, day + ".csv")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        missing = [c for c in COLS[rel] if c not in (rd.fieldnames or [])]
        if missing:
            raise ValueError("%s/%s.csv: missing columns %s" % (rel, day, missing))
        return list(rd)


def load_day(inputs, day):
    return {rel: read_rel(inputs, rel, day) for rel in COLS}


def verify_manifest(inputs):
    """manifest.tsv: '<sha256>\\t<relative path>' per CSV. Returns a list of problems (empty = verified)."""
    p = os.path.join(inputs, "manifest.tsv")
    if not os.path.exists(p):
        return ["manifest.tsv absent"]
    listed, problems = {}, []
    with open(p, encoding="utf-8", newline="") as fh:
        for line in fh.read().splitlines():
            if line.strip():
                h, rel = line.split("\t")
                listed[rel.strip().replace("\\", "/")] = h.strip()
    for rel, h in sorted(listed.items()):
        fp = os.path.join(inputs, *rel.split("/"))
        if not os.path.exists(fp):
            problems.append("listed but absent: " + rel)
        elif hashlib.sha256(open(fp, "rb").read()).hexdigest() != h:
            problems.append("sha256 differs: " + rel)
    for r in COLS:
        d = os.path.join(inputs, r)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith(".csv") and (r + "/" + f) not in listed:
                problems.append("present but not listed: %s/%s" % (r, f))
    return problems


# ---------------------------------------------------------------------------------------------------- per-day work

def quarantine_reasons(sym, minutes, daily_rows):
    """DEF-2 / DEF-3 / DEF-4. minutes: set of minute-of-day with a tape_minute row; daily_rows: {symbol: row}."""
    reasons = []
    k = len({m for m in minutes if 555 <= m < 930})
    if 100 * k < PARAMS["completeness_min_pct"] * PARAMS["completeness_minutes"]:
        reasons.append("COMPLETENESS")
    row = daily_rows.get(sym)
    share = None
    if row is not None:
        try:
            share = json.loads(row["g3"], parse_float=Fraction)["verdict_detail"]["late"]["share_pct"]
        except (TypeError, KeyError, ValueError):
            share = None
    if share is None:
        reasons.append("UNVERIFIABLE")
    elif share < PARAMS["late_share_min_pct"]:
        reasons.append("LATE_SHARE")
    for r in daily_rows.values():
        try:
            restarts = json.loads(r["report"]).get("restarts") or []
        except (TypeError, ValueError, AttributeError):
            continue
        for e in restarts:
            if e.get("prev_state") == "TOKEN_FAIL":
                m = hm(parse_ts(e["process_start_ist"]))
                if 555 <= m < 930:
                    reasons.append("TOKEN_RESTART")
                    break
        if "TOKEN_RESTART" in reasons:
            break
    return reasons  # quarantine verdict


def window_stamps(G):
    """v0.4 section 1: the six tape_strike_cycle stamps G-25, G-20, ..., G; stamp t covers [t-5, t), so [G-30, G)."""
    return [G - 5 * i for i in range(PARAMS["s_window_bins"])]


def tape_sign(cyc, G, expiry, window, strikes, only=None):
    """-> (S or None, why, info). v0.4: D30 = -sum over window strike-legs of gamma * (sum buy_5 - sum sell_5) over the
    six bins stamped G-25..G; share over the same bins; S = sign(D30). cyc: {stamp: [CycRow]}; window: strikes at G.
    A strike-leg missing some of the six rows contributes the rows present."""
    src = [r for st in window_stamps(G) for r in cyc.get(st, ())]
    share_src = src
    win = set(window)
    keep = lambda r: r.exp == expiry and r.leg in ("CE", "PE") and r.k in win and (only is None or r.k == only)  # noqa: E731
    net, legs, g = {}, set(), 0
    for r in src:
        if keep(r):
            net[(r.k, r.leg)] = net.get((r.k, r.leg), 0) + (r.b5 - r.s5)
            legs.add((r.k, r.leg))
            g += r.g5
    b = s = u = 0
    for r in share_src:
        if keep(r):
            b, s, u = b + r.b5, s + r.s5, u + r.u5
    d_sum = Fraction(0)
    missing = 0
    for (k, leg), nv in net.items():
        gam = strikes.get(k)
        gv = None if gam is None else (gam[0] if leg == "CE" else gam[1])
        if gv is None:
            missing += 1
            continue
        d_sum += gv * nv
    cls = b + s
    tot = cls + u
    info = {"gap": g, "missing_gamma_legs": missing, "legs": len(legs)}
    if not legs or tot == 0:
        return None, "zero_denominator", info
    if 100 * cls < PARAMS["cycle_share_min_pct"] * tot:
        return None, "share_below_min", info
    D = -d_sum
    S = (D > 0) - (D < 0)
    if S == 0:
        return None, "d_zero", info
    return S, "", info


CLOSE_AUCTION_BAR = 929  # 15:29, the closing-auction bar: excluded from every range (v0.4 section 1)


def spot_range(bars, t_dt):
    """v0.4 section 1 / section 6: bars labelled hm(T) .. hm(T)+29 (minute-start labels), 15:29 never selected."""
    m0 = hm(t_dt)
    present = [bars[m] for m in range(m0, m0 + PARAMS["r_horizon_min"]) if m in bars and m != CLOSE_AUCTION_BAR]
    if len(present) < PARAMS["r_min_bars"]:
        return None, len(present)
    return max(p[0] for p in present) - min(p[1] for p in present), len(present)


def load_spot(rows, day, cnt):
    """-> {symbol: {label: (high, low, close)}}, {symbol: ok}. Refuses a day whose clock looks IST-as-UTC (DEF clock check)."""
    bars = {s: {} for s in SYMS}
    seen = {s: [0, 0] for s in SYMS}
    for r in rows or []:
        sym = INSTRUMENT_SYMBOL.get(r["instrument_id"].strip())
        if sym is None:
            cnt["spot_unknown_instrument"] = cnt.get("spot_unknown_instrument", 0) + 1
            continue
        dt = parse_ts(r["bar_ts"])
        if dt.strftime("%Y-%m-%d") != day:
            cnt["spot_other_day_rows"] = cnt.get("spot_other_day_rows", 0) + 1
            continue
        h, l, c = frac(r["high"]), frac(r["low"]), frac(r["close"])
        if h is None or l is None:
            continue
        m = hm(dt)
        seen[sym][0] += 1
        if 555 <= m <= 929:
            seen[sym][1] += 1
        if m in bars[sym]:
            raise ValueError("duplicate spot bar %s %s" % (sym, r["bar_ts"]))
        bars[sym][m] = (h, l, c)
    ok = {}
    for s in SYMS:
        n, inside = seen[s]
        ok[s] = n > 0 and 100 * inside >= PARAMS["spot_clock_min_pct"] * n
        if not ok[s]:
            bars[s] = {}
    return bars, ok


def label_event(kind, leg, side, strike, run):
    labels = set()
    cw, pw, ru = run["call_wall"], run["put_wall"], run["runner_up"]
    if kind == "CONC":
        if (leg == "CE" and strike == cw) or (leg == "PE" and strike == pw):
            labels.add("T1")
        if ru is not None and strike == ru:
            labels.add("T2")
    elif kind == "THIN":
        if side == PARAMS["passive_side"][leg] and ((leg == "CE" and strike == cw) or (leg == "PE" and strike == pw)):
            labels.add("T3")
    return labels


def _run_summary(dt, rows):
    strikes = {}
    for r in rows:
        k = Fraction(r["strike"])
        if k in strikes:
            raise ValueError("duplicate strike %s in run %s" % (r["strike"], r["ts"]))
        strikes[k] = (frac(r["gamma_call"]), frac(r["gamma_put"]), Fraction(r["gex_cr"]))
    total = sum((v[2] for v in strikes.values()), Fraction(0))
    U = (total > 0) - (total < 0)
    ranked = sorted(strikes, key=lambda k: (-abs(strikes[k][2]), k))
    pos = sorted((k for k in strikes if strikes[k][2] > 0), key=lambda k: (-strikes[k][2], k))
    return {"dt": dt, "us": us_of(dt), "G": (hm(dt) // 5) * 5, "strikes": strikes, "U": U,
            "leader": ranked[0] if ranked else None, "runner_up": ranked[1] if len(ranked) > 1 else None,
            "pin": pos[0] if pos else None}


def score_day_symbol(day, sym, T, spot_bars, spot_ok, minutes, daily_rows):
    """Everything one (symbol, day) contributes. Returns a dict; hypotheses are assembled later over non-quarantined days."""
    c = {}

    def bump(key, n=1):
        c[key] = c.get(key, 0) + n

    out = {"day": day, "sym": sym, "quarantine": quarantine_reasons(sym, minutes, daily_rows)}
    # -- tape cycle rows by grid point
    cyc = {}
    for r in T["tape_strike_cycle"] or []:
        if r["symbol"] != sym:
            continue
        dt = parse_ts(r["ts_ist"])
        if dt.minute % 5 or dt.second or dt.microsecond:
            raise ValueError("tape_strike_cycle ts_ist off the 5-minute grid: %s" % r["ts_ist"])
        if (r["leg"] or "").strip() not in ("CE", "PE"):
            bump("tape_rows_fut_or_other_ignored")
            continue
        cyc.setdefault(hm(dt), []).append(CycRow(
            r["expiry"].strip(), Fraction(r["strike"]), r["leg"].strip(), to_int(r["buy_5"]), to_int(r["sell_5"]),
            to_int(r["uncl_5"]), to_int(r["gap_5"]), to_int(r["buy_cum"]), to_int(r["sell_cum"]), to_int(r["uncl_cum"]),
            to_int(r["gap_cum"])))
    windows = {}
    for G, rows in cyc.items():
        for exp in {r.exp for r in rows}:
            windows[(G, exp)] = sorted({r.k for r in rows if r.exp == exp})
    # -- chain runs (walls) and straddle
    cruns = {}
    for r in T["tape_chain_runs"] or []:
        if r["symbol"] == sym:
            # tape_chain_runs.ts_ist is rendered with whole seconds (chain_events.py strftime); gex_strike_snapshots.ts may carry
            # a fraction. The two name one run, so they are joined on the whole second.
            cruns[us_of(parse_ts(r["ts_ist"])) // 10 ** 6] = r
    straddle = {}
    for r in T["gamma_metrics"] or []:
        if r["symbol"] == sym:
            straddle[r["run_id"].strip()] = frac(r["straddle_atm"])
    # -- front runs from gex_strike_snapshots
    groups = {}
    for r in T["gex_strike_snapshots"] or []:
        if r["symbol"] != sym:
            continue
        dt = parse_ts(r["ts"])
        if dt.strftime("%Y-%m-%d") != day:
            bump("gss_other_day_rows")
            continue
        groups.setdefault(us_of(dt), (dt, []))[1].append(r)
    runs = []
    for us in sorted(groups):
        dt, grp = groups[us]
        front = min(g["expiry_date"].strip() for g in grp)
        fr = [g for g in grp if g["expiry_date"].strip() == front]
        bump("gss_non_front_rows", len(grp) - len(fr))
        if len({g["run_id"].strip() for g in fr}) > 1:
            bump("run_id_conflicts")
            continue
        run = _run_summary(dt, fr)
        run.update({"expiry": front, "run_id": fr[0]["run_id"].strip()})
        cr = cruns.get(us // 10 ** 6)
        run["call_wall"] = frac(cr["call_wall"]) if cr else None
        run["put_wall"] = frac(cr["put_wall"]) if cr else None
        if cr is None:
            bump("runs_without_chain_runs_row")
        else:
            if cr["chain_run_id"].strip() != run["run_id"]:
                bump("chain_run_id_mismatch")
            if int(cr["net_sign"]) != run["U"]:
                bump("net_sign_vs_U_mismatch")
        runs.append(run)
    # -- cycles
    cycles, offsets = [], []
    for run in runs:
        G = run["G"]
        offsets.append(run["dt"].hour * 3600 + run["dt"].minute * 60 + run["dt"].second - G * 60)
        rec = {"G": G, "U": run["U"], "S": None, "R": None, "t": run["us"], "run": run}
        win = windows.get((G, run["expiry"]))
        if cyc.get(G) is None or win is None:
            bump("cycle_no_tape_row_at_G")
        else:
            S, why, info = tape_sign(cyc, G, run["expiry"], win, run["strikes"])
            rec["S"] = S
            bump("legs_missing_gamma", info["missing_gamma_legs"])
            bump("gap_window_total", info["gap"])
            if S is None:
                bump("cycle_s_undefined_" + why)
            # descriptive only (v0.4 section 1): wall membership and the share of |gex_cr| inside the window
            ws = set(win)
            tot = sum((abs(v[2]) for v in run["strikes"].values()), Fraction(0))
            ins = sum((abs(v[2]) for k, v in run["strikes"].items() if k in ws), Fraction(0))
            rec["cov"] = {"call_wall_in_window": run["call_wall"] in ws, "put_wall_in_window": run["put_wall"] in ws,
                          "gexabs_share_in_window": (ins / tot) if tot else None}
        if run["U"] == 0:
            bump("cycle_u_zero")
        if not spot_ok.get(sym):
            bump("cycle_spot_clock_refused")
        else:
            st = straddle.get(run["run_id"])
            if st is None or st <= 0:
                bump("cycle_no_straddle")
            else:
                rng, nbars = spot_range(spot_bars[sym], run["dt"])
                if rng is None:
                    bump("cycle_r_bars_lt_min")
                else:
                    rec["R"] = rng / st
        cycles.append(rec)
    out["cycles"] = cycles
    out["offsets"] = offsets
    # -- expiry-day pin (secondary)
    out["pin"] = None
    if runs and runs[0]["expiry"] == day:
        r1415 = next((r for r in runs if r["G"] == 855), None)
        if r1415 is not None and cyc.get(855) and windows.get((855, r1415["expiry"])):
            pin = r1415["pin"]
            if pin is None:
                bump("pin_none")
            else:
                S, why, _ = tape_sign(cyc, 855, r1415["expiry"], windows[(855, r1415["expiry"])], r1415["strikes"], only=pin)
                close = (spot_bars[sym].get(929) or (None, None, None))[2]
                st = straddle.get(r1415["run_id"])
                if close is None or st is None or st <= 0:
                    bump("pin_no_close_or_straddle")
                else:
                    dist = abs(close - pin)
                    grp = "undefined" if S is None else ("agree" if S == r1415["U"] else "disagree")
                    out["pin"] = {"group": grp, "dist": dist, "ratio": dist / st}
    out["expiry_day"] = bool(runs) and runs[0]["expiry"] == day
    # -- tape events -> labels and a per-strike index (events >= 10:00 only: DEF-5)
    idx = {}
    run_us = [r["us"] for r in runs]
    nlab = {"T1": 0, "T2": 0, "T3": 0, "conc_unlabelled": 0, "thin_unlabelled": 0}
    for r in T["tape_events"] or []:
        if r["symbol"] != sym or (r["leg"] or "").strip() not in ("CE", "PE") or not (r["strike"] or "").strip():
            continue
        dt = parse_ts(r["ts_ist"])
        if hm(dt) < PARAMS["ha_first_G_min"]:
            bump("tape_events_before_10")
            continue
        i = bisect.bisect_right(run_us, us_of(dt)) - 1
        labels = set()
        if i < 0:
            bump("tape_events_no_reference_run")
        elif runs[i]["expiry"] != r["expiry"].strip():
            bump("tape_events_other_expiry")
        else:
            labels = label_event(r["kind"].strip(), r["leg"].strip(), r["side"].strip(), Fraction(r["strike"]), runs[i])
        for lb in labels:
            nlab[lb] += 1
        if not labels:
            nlab["conc_unlabelled" if r["kind"].strip() == "CONC" else "thin_unlabelled"] += 1
        idx.setdefault(Fraction(r["strike"]), []).append(
            (us_of(dt), tuple(sorted(labels)), r["kind"].strip(), r["leg"].strip(), r["side"].strip()))
    out["labels"] = nlab
    # -- chain events
    events = []
    for r in T["tape_chain_events"] or []:
        if r["symbol"] != sym:
            continue
        dt = parse_ts(r["ts_ist"])
        G = (hm(dt) // 5) * 5
        K = Fraction(r["strike"])
        win = windows.get((G, r["expiry"].strip()))
        if win is None:
            bump("chain_events_no_tape_grid")
            continue
        if K not in win:
            bump("chain_events_outside_window")
            continue
        events.append({"us": us_of(dt), "kind": r["kind"].strip(), "K": K, "window": win})
    events.sort(key=lambda e: (e["us"], e["kind"], e["K"]))
    # counted events are consumed as-is: pre-registration merge was applied by T1b and is never repeated here
    counted = events
    out["events"] = counted
    out["idx"] = idx
    out["t4"] = t4_events(day, sym, T.get("tape_minute_oi"), runs)  # descriptive only: its own index, never idx
    out["counts"] = c
    return out


def t4_events(day, sym, rows, runs):
    """v0.4 section 3 (descriptive): T4 OI_MOVE. None when the optional tape_minute_oi input is absent.
    Per front-expiry CE/PE strike-leg and 5-minute cycle [G, G+5): base = OI of the latest minute row labelled < G; the first
    minute m in [G, G+5) with 100*|oi_m - base| >= e2_oi_move_pct*base (base > 0) fires one T4 stamped (m+1):00 (the
    minute's OI is known at its close). Kept only at the reference run's call wall (CE) / put wall (PE), stamps >= 10:00.
    Returns {strike: [(us, leg)]}."""
    if rows is None:
        return None
    if not runs:
        return {}
    expiry = runs[0]["expiry"]
    series = {}
    for r in rows:
        if r["symbol"] != sym or (r["opt_type"] or "").strip() not in ("CE", "PE") or r["expiry"].strip() != expiry:
            continue
        if not (r["oi"] or "").strip() or not (r["strike"] or "").strip():
            continue
        m = hm(parse_ts(r["minute_ist"]))
        series.setdefault((Fraction(r["strike"]), r["opt_type"].strip()), {})[m] = to_int(r["oi"])
    d0 = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=IST)
    run_us = [x["us"] for x in runs]
    out = {}
    for (k, leg), s in sorted(series.items()):
        ms = sorted(s)
        for G in range(555, 930, 5):
            prior = [m for m in ms if m < G]
            if not prior:
                continue
            base = s[prior[-1]]
            if base <= 0:
                continue
            hit = next((m for m in ms if G <= m < G + 5
                        and 100 * abs(s[m] - base) >= PARAMS["e2_oi_move_pct"] * base), None)
            if hit is None or hit + 1 < PARAMS["ha_first_G_min"]:
                continue
            us = us_of(d0 + timedelta(minutes=hit + 1))
            i = bisect.bisect_right(run_us, us) - 1
            if i < 0:
                continue
            wall = runs[i]["call_wall"] if leg == "CE" else runs[i]["put_wall"]
            if wall == k:
                out.setdefault(k, []).append((us, leg))
    return out


# ---------------------------------------------------------------------------------------------------- hypotheses

def decide_ha(deltas):
    n = len(deltas)
    med = _median(deltas) if n else None
    w = wilcoxon.signed_rank_greater(deltas) if n else None
    p = None if w is None else Fraction(w["p"])
    if n < PARAMS["ha_min_days"]:
        verdict = "INSUFFICIENT"
    elif med >= PARAMS["ha_min_median_delta"] and p <= PARAMS["ha_p_max"]:
        verdict = "YES"
    else:
        verdict = "NO"
    return {"verdict": verdict, "n_days": n, "median_delta": med, "p": None if w is None else w["p"],
            "method": None if w is None else w["method"], "n_eff": None if w is None else w["n_eff"],
            "zeros_dropped": None if w is None else w["zeros_dropped"], "switch_n": wilcoxon.NORMAL_ABOVE}


def combine(a, b):
    if a == "YES" and b == "YES":
        return "YES"
    if a == "NO" and b == "NO":
        return "NO"
    return "MIXED"


def decide_hb(n, ndays, cov, lead, null_cov, null_lead):
    """cov: Fraction; lead, null_lead: Fraction minutes or None."""
    if n < PARAMS["hb_min_events"] or ndays < PARAMS["hb_min_days"]:
        return "INSUFFICIENT", []
    no = []
    if lead is None or lead <= PARAMS["hb_lead_no_max"]:
        no.append("lead<=5")
    if cov < PARAMS["hb_cov_min"]:
        no.append("coverage<1/2")
    if cov <= null_cov:
        no.append("coverage<=null95")
    if lead is None or lead <= null_lead:
        no.append("lead<=null95")
    if no:
        return "NO", no
    if lead >= PARAMS["hb_lead_yes_min"]:
        return "YES", []
    return "MARGINAL", []


def _lead_us(idx, K, T_us, pred):
    lo = T_us - PARAMS["match_window_min"] * US_MIN
    cands = [e for e in idx.get(K, ()) if lo < e[0] <= T_us and pred(e)]
    if not cands:
        return None
    best = max(cands, key=lambda e: e[0])
    return T_us - best[0]


def _null_pred(ckind):
    if ckind == "E1":
        return lambda e: e[2] == "CONC"
    leg = "CE" if ckind == "E2-call" else "PE"
    side = PARAMS["passive_side"][leg]
    return lambda e: e[3] == leg and (e[2] == "CONC" or (e[2] == "THIN" and e[4] == side))


def seed_bytes():
    with open(os.path.abspath(__file__), "rb") as fh:
        return hashlib.sha256(fh.read()).digest()


def stream(sym):
    return random.Random(int.from_bytes(hashlib.sha256(seed_bytes() + b"|" + sym.encode()).digest()[:8], "big"))


def hb_symbol(sym, day_data, nonq_days):
    rng = stream(sym)
    real, per_day, draws_evaluated = [], {}, 0
    for day in nonq_days:
        d = day_data[day]
        idx = d["idx"]  # T1/T2/T3 candidates only; T4 lives in d["t4"] and never reaches this index (v0.4 section 3)
        for e in d["events"]:
            lead = _lead_us(idx, e["K"], e["us"], lambda x, k=e["kind"]: bool(set(x[1]) & MATCH[k]))
            real.append((lead, e["kind"]))
            pred = _null_pred(e["kind"])
            dr = []
            for _ in range(PARAMS["null_draws"]):
                k2 = e["window"][rng.randrange(len(e["window"]))]
                l2 = _lead_us(idx, k2, e["us"], pred)
                dr.append((l2 is not None, l2))
                draws_evaluated += 1
            per_day.setdefault(day, []).append(dr)
    n = len(real)
    covered = [l for l, _ in real if l is not None]
    cov = Fraction(len(covered), n) if n else Fraction(0)
    lead = Fraction(_median(covered), US_MIN) if covered else None
    B, D = PARAMS["bootstrap_B"], len(nonq_days)
    covs, leads = [], []
    for _ in range(B):
        total = hit = 0
        ls = []
        for _d in range(D):
            for dr in per_day.get(nonq_days[rng.randrange(D)], ()):
                ok, l = dr[rng.randrange(len(dr))]
                total += 1
                if ok:
                    hit += 1
                    ls.append(l)
        covs.append(Fraction(hit, total) if total else Fraction(0))
        leads.append(Fraction(_median(ls), US_MIN) if ls else Fraction(0))
    covs.sort()
    leads.sort()
    k = (PARAMS["null_pctile"] * B + 99) // 100 - 1
    null_cov, null_lead = (covs[k], leads[k]) if D else (Fraction(0), Fraction(0))
    verdict, reasons = decide_hb(n, D, cov, lead, null_cov, null_lead)
    return {"verdict": verdict, "no_reasons": reasons, "n_events": n, "n_days": D, "coverage": cov,
            "median_lead_min": lead, "null95_coverage": null_cov, "null95_lead_min": null_lead,
            "null_draws_per_event": PARAMS["null_draws"], "null_draws_evaluated": draws_evaluated,
            "bootstrap_B": B, "by_kind": {k: sum(1 for _, kk in real if kk == k) for k in sorted(MATCH)}}


def _nearest(idx, K, T_us, pred):
    """the tape event that sets the pooled lead (same selection as _lead_us), or None."""
    lo = T_us - PARAMS["match_window_min"] * US_MIN
    cands = [e for e in idx.get(K, ()) if lo < e[0] <= T_us and pred(e)]
    return max(cands, key=lambda e: e[0]) if cands else None


def _lead_summary(leads):
    return {"covered": len(leads), "median_lead_min": Fraction(_median(leads), US_MIN) if leads else None}


def descriptive(acc):
    """v0.4 reporting additions. Reads the per-day work; returns a block no decision function receives."""
    out = {}
    for s in SYMS:
        days = sorted(acc[s])
        cov_days, per_cycle, sign_changes = {}, {}, {}
        attr, any_l = {}, {L: {"events": 0, "leads": []} for L in ("T1", "T2", "T3")}
        t4_ev, t4_leads, t4_days_missing, t4_any = 0, [], [], False
        n_events = 0
        for day in days:
            d = acc[s][day]
            cs = sorted(d["cycles"], key=lambda c: c["G"])
            cov = [dict(c["cov"], G=c["G"]) for c in cs if c.get("cov")]
            per_cycle[day] = cov
            if cov:
                n = len(cov)
                shares = [x["gexabs_share_in_window"] for x in cov if x["gexabs_share_in_window"] is not None]
                cov_days[day] = {"cycles": n,
                                 "call_wall_in_window_frac": Fraction(sum(1 for x in cov if x["call_wall_in_window"]), n),
                                 "put_wall_in_window_frac": Fraction(sum(1 for x in cov if x["put_wall_in_window"]), n),
                                 "gexabs_share_in_window_median": _median(shares) if shares else None}
            seq = [c["S"] for c in cs if _ha_in_clock(c["G"]) and c["S"] is not None]
            sign_changes[day] = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
            for e in d["events"]:
                n_events += 1
                kind = e["kind"]
                best = _nearest(d["idx"], e["K"], e["us"], lambda x, k=kind: bool(set(x[1]) & MATCH[k]))
                if best is not None:
                    cls = "+".join(sorted(set(best[1]) & MATCH[kind]))
                    attr.setdefault(cls, []).append(e["us"] - best[0])
                for L in ("T1", "T2", "T3"):
                    if L in MATCH[kind]:
                        any_l[L]["events"] += 1
                        b2 = _nearest(d["idx"], e["K"], e["us"], lambda x, L=L: L in x[1])
                        if b2 is not None:
                            any_l[L]["leads"].append(e["us"] - b2[0])
            if d["t4"] is None:
                t4_days_missing.append(day)
                continue
            t4_any = True
            for e in d["events"]:
                if e["kind"] not in ("E2-call", "E2-put"):
                    continue
                t4_ev += 1
                leg = "CE" if e["kind"] == "E2-call" else "PE"
                lo = e["us"] - PARAMS["match_window_min"] * US_MIN
                c = [u for u, lg in d["t4"].get(e["K"], ()) if lg == leg and lo < u <= e["us"]]
                if c:
                    t4_leads.append(e["us"] - max(c))
        hb_attr = {k: _lead_summary(v) for k, v in sorted(attr.items())}
        hb_any = {L: dict(_lead_summary(v["leads"]), events=v["events"],
                          coverage=Fraction(len(v["leads"]), v["events"]) if v["events"] else None) for L, v in any_l.items()}
        if not t4_any:
            t4 = NO_T4
        else:
            t4 = dict(_lead_summary(t4_leads), e2_events=t4_ev, days_without_input=t4_days_missing,
                      coverage=Fraction(len(t4_leads), t4_ev) if t4_ev else None,
                      note="descriptive only; T4 never enters the T1/T2/T3 match set (v0.4 section 3)")
        out[s] = {"window_coverage_per_day": cov_days, "window_coverage_per_cycle": per_cycle,
                  "s_sign_changes_1000_1445": sign_changes, "s_sign_changes_exploration_median": Fraction(5, 2),
                  "hb_by_label": {"events": n_events, "attribution": hb_attr,
                                  "attribution_covered_total": sum(v["covered"] for v in hb_attr.values()),
                                  "any_label": hb_any},
                  "t4": t4}
    return out


def _ha_in_clock(G):
    return PARAMS["ha_first_G_min"] <= G <= PARAMS["ha_last_G_min"]


def ha_symbol(day_data, nonq_days):
    pos, neg, pop_G = [], [], []
    m = PARAMS["min_cycles_per_group"]
    agree_pop = [0, 0, 0, 0]
    agree_all = [0, 0, 0, 0]
    for day in nonq_days:
        cs = day_data[day]["cycles"]
        for c in cs:
            if c["S"] is not None and c["U"] != 0 and c["G"] >= PARAMS["ha_first_G_min"]:
                agree_all[0] += 1
                agree_all[1] += c["S"] == c["U"]
                agree_all[2] += c["S"] > 0
                agree_all[3] += c["U"] > 0
        pop = [c for c in cs if _ha_in_clock(c["G"]) and c["S"] is not None and c["U"] != 0 and c["R"] is not None]
        for c in pop:
            pop_G.append(c["G"])
            agree_pop[0] += 1
            agree_pop[1] += c["S"] == c["U"]
            agree_pop[2] += c["S"] > 0
            agree_pop[3] += c["U"] > 0
        for stratum, lst in ((1, pos), (-1, neg)):
            ag = [c["R"] for c in pop if c["U"] == stratum and c["S"] == stratum]
            di = [c["R"] for c in pop if c["U"] == stratum and c["S"] == -stratum]
            if len(ag) >= m and len(di) >= m:
                lst.append(_median(di) - _median(ag))

    def rate(a):
        n, k, ps, pu = a
        if not n:
            return {"n": 0}
        pS, pU = Fraction(ps, n), Fraction(pu, n)
        return {"n": n, "agree_rate": Fraction(k, n), "p_S_pos": pS, "p_U_pos": pU,
                "independence_base_rate": pS * pU + (1 - pS) * (1 - pU)}

    sec_neg = None
    if neg:
        w = wilcoxon.signed_rank_less(neg)
        sec_neg = {"n_days": len(neg), "median_delta": _median(neg), "p_delta_lt_0": w["p"], "method": w["method"]}
    pins = {"agree": [], "disagree": [], "undefined": []}
    for day in nonq_days:
        pn = day_data[day]["pin"]
        if pn:
            pins[pn["group"]].append(pn)
    pin_out = {g: {"n": len(v), "median_dist_points": _median([p["dist"] for p in v]) if v else None,
                   "median_dist_over_straddle": _median([p["ratio"] for p in v]) if v else None} for g, v in pins.items()}
    res = decide_ha(pos)
    res.update({"population_cycles": len(pop_G), "population_G_min": min(pop_G) if pop_G else None,
                "population_G_max": max(pop_G) if pop_G else None,
                "secondary": {"agreement_ha_population": rate(agree_pop),
                              "agreement_all_cycles_ge_10": rate(agree_all),
                              "stratum_U_neg_prediction_reversed": sec_neg, "expiry_day_pin": pin_out}})
    return res


# ---------------------------------------------------------------------------------------------------- run

def run(inputs, _keep=None):
    days = discover_days(inputs)
    acc = {s: {} for s in SYMS}
    quarantined = {s: {} for s in SYMS}
    counts = {s: {} for s in SYMS}
    offsets = {s: [] for s in SYMS}
    load_runs = {}
    expiry_days = {s: [] for s in SYMS}
    recorded_days = []
    for day in days:
        T = load_day(inputs, day)
        for rel in COLS:
            if T[rel] is None and rel not in OPTIONAL:
                counts.setdefault("_files", {}).setdefault("missing_" + rel, []).append(day)
        if T["tape_daily_report"]:
            recorded_days.append(day)
        load_runs[day] = {rel: len({r["run_id"] for r in T[rel]}) for rel in COLS
                          if T[rel] and "run_id" in T[rel][0] and rel in ("tape_strike_cycle", "tape_events",
                                                                        "tape_chain_events", "tape_chain_runs",
                                                                        "tape_daily_report", "tape_minute")}
        c0 = {}
        bars, ok = load_spot(T["hist_spot_bars_1m"], day, c0)
        daily = {r["symbol"]: r for r in T["tape_daily_report"] or []}
        minutes = {s: set() for s in SYMS}
        for r in T["tape_minute"] or []:
            if r["symbol"] in minutes:
                minutes[r["symbol"]].add(hm(parse_ts(r["minute_ist"])))
        for s in SYMS:
            d = score_day_symbol(day, s, T, bars, ok, minutes[s], daily)
            for k, v in list(d["counts"].items()) + list(c0.items()):
                counts[s][k] = counts[s].get(k, 0) + v
            if d["quarantine"]:
                quarantined[s][day] = d["quarantine"]
            else:
                acc[s][day] = d
            if d["expiry_day"]:
                expiry_days[s].append(day)
            offsets[s] += d["offsets"]
            if d["quarantine"]:
                counts[s]["events_in_quarantined_days"] = counts[s].get("events_in_quarantined_days", 0) + len(d["events"])
            counts[s].setdefault("_labels", {})
            for k, v in d["labels"].items():
                counts[s]["_labels"][k] = counts[s]["_labels"].get(k, 0) + v
    if _keep is not None:
        _keep["acc"], _keep["quarantined"] = acc, quarantined
    result = {"prereg_sha": PREREG_SHA, "seed_int": int.from_bytes(seed_bytes()[:8], "big"),
              "params": PARAMS, "days": days, "recorded_days": recorded_days, "load_runs": load_runs,
              "quarantine": quarantined, "expiry_days": expiry_days, "symbols": {}}
    ha_v, hb_v = {}, {}
    desc = descriptive(acc)
    for s in SYMS:
        nonq = sorted(acc[s])
        ha = ha_symbol(acc[s], nonq)
        hb = hb_symbol(s, acc[s], nonq)
        off = sorted(offsets[s])
        result["symbols"][s] = {
            "counts": {k: v for k, v in sorted(counts[s].items()) if not k.startswith("_")},
            "tape_labels": counts[s].get("_labels", {}),
            "clock_floor_offset_s": {"n": len(off), "min": off[0] if off else None,
                                     "median": _median(off) if off else None, "max": off[-1] if off else None},
            "non_quarantined_days": nonq, "H_A": ha, "H_B": hb}
        ha_v[s], hb_v[s] = ha["verdict"], hb["verdict"]
    result["files_missing"] = counts.get("_files", {})
    result["descriptive"] = desc
    result["H_A"] = dict(ha_v, overall=combine(*[ha_v[s] for s in SYMS]))
    result["H_B"] = dict(hb_v, overall=combine(*[hb_v[s] for s in SYMS]))
    return result


def render_report(res):
    L = ["MERIDIAN tape scoring (pre-registration v0.4 %s)" % PREREG_SHA, "seed_int %d" % res["seed_int"],
         "days %d, recorded %d" % (len(res["days"]), len(res["recorded_days"])), ""]
    L.append("H-A: " + json.dumps(res["H_A"], sort_keys=True))
    L.append("H-B: " + json.dumps(res["H_B"], sort_keys=True))
    for s in SYMS:
        S = res["symbols"][s]
        L += ["", "== %s ==" % s, "quarantined days: " + (json.dumps(res["quarantine"][s], sort_keys=True) or "none"),
              "counts: " + json.dumps(S["counts"], sort_keys=True),
              "tape labels: " + json.dumps(S["tape_labels"], sort_keys=True),
              "floor offset s: " + json.dumps(S["clock_floor_offset_s"], sort_keys=True)]
        for h in ("H_A", "H_B"):
            L.append("%s: %s" % (h, json.dumps({k: v for k, v in S[h].items() if k != "secondary"}, sort_keys=True)))
        L.append("H-A secondary: " + json.dumps(S["H_A"]["secondary"], sort_keys=True))
        dd = res.get("descriptive", {}).get(s, {})
        L.append("descriptive (no decision input): " + json.dumps(
            {k: v for k, v in dd.items() if k != "window_coverage_per_cycle"}, sort_keys=True))
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------------- gates

def file_hashes():
    out = {}
    for n in HASHED:
        with open(os.path.join(PKG, n), "rb") as fh:
            b = fh.read()
        if b"\r" in b:
            raise ValueError("%s contains CR; hashes are defined over LF files (.gitattributes eol=lf)" % n)
        out[n] = hashlib.sha256(b).hexdigest()
    return out


def check_hashes():
    """Recompute the four sha256 values and compare with the LAST entry of docs/tape/scoring_hashes.md (v0.4: the ledger
    is append-only and each entry begins '## Entry'). That entry must name this file's PREREG_SHA. -> differences."""
    diffs = []
    try:
        with open(LEDGER, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return ["ledger file absent: " + LEDGER]
    blocks = text.split("\n## Entry")
    text = blocks[-1]
    if len(blocks) < 2 or PREREG_SHA not in text:
        diffs.append("the last ledger entry does not name pre-registration %s" % PREREG_SHA)
    for n, h in file_hashes().items():
        m = re.search(r"services/tape_scoring/%s[^0-9a-f\n]*([0-9a-f]{64})" % re.escape(n), text)
        if not m:
            diffs.append("%s: not listed in the ledger" % n)
        elif m.group(1) != h:
            diffs.append("%s: ledger %s != file %s" % (n, m.group(1), h))
    return diffs


def check_run_once(prev, rerun_defect):
    if prev == 0:
        return None
    if prev == 1 and rerun_defect and rerun_defect.strip():
        return None
    if prev == 1:
        return "a scoring run is already recorded; a re-run needs --rerun-defect \"<defect in the code>\""
    return "two scoring runs are already recorded; no further run is permitted"


def trigger(res):
    ex = {s: len(res["expiry_days"][s]) for s in SYMS}
    ok = all(v >= PARAMS["trigger_expiries"] for v in ex.values()) or len(res["recorded_days"]) >= PARAMS["trigger_days"]
    return ok, "expiry days per index %s; recorded trading days %d (need >= %d expiries per index or >= %d days)" % (
        ex, len(res["recorded_days"]), PARAMS["trigger_expiries"], PARAMS["trigger_days"])


def _prev_runs(out_dir):
    n = 0
    for p in (os.path.join(out_dir, "scoring_runs.json"), RUNS_FIXED):
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                n = max(n, len(json.load(fh).get("runs", [])))
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m services.tape_scoring.score")
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fixture", action="store_true")
    ap.add_argument("--rerun-defect", default=None)
    a = ap.parse_args(argv)
    has_truth = os.path.exists(os.path.join(a.inputs, "FIXTURE_TRUTH.json"))
    if a.fixture != has_truth:
        print("REFUSED: --fixture requires FIXTURE_TRUTH.json in --inputs, and a real run refuses it (fixture=%s, truth file=%s)"
              % (a.fixture, has_truth))
        return 2
    if not a.fixture:
        diffs = check_hashes()
        if diffs:
            print("REFUSED: HASH MISMATCH against docs/tape/scoring_hashes.md")
            for d in diffs:
                print("  " + d)
            return 3
        err = check_run_once(_prev_runs(a.out), a.rerun_defect)
        if err:
            print("REFUSED: " + err)
            return 4
        probs = verify_manifest(a.inputs)
        if probs:
            print("REFUSED: input manifest: " + "; ".join(probs[:5]))
            return 5
    res = run(a.inputs)
    if not a.fixture:
        ok, msg = trigger(res)
        print("TRIGGER %s: %s" % ("MET" if ok else "NOT MET", msg))
        if not ok:
            return 6
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "score_result.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(jsonable(res), sort_keys=True, indent=1) + "\n")
    with open(os.path.join(a.out, "score_report.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_report(jsonable(res)))
    if not a.fixture:
        entry = {"when_utc": datetime.now(timezone.utc).isoformat(), "rerun_defect": a.rerun_defect,
                 "hashes": file_hashes(), "seed_int": res["seed_int"]}
        for p in (os.path.join(a.out, "scoring_runs.json"), RUNS_FIXED):
            runs = []
            if os.path.exists(p):
                with open(p, encoding="utf-8") as fh:
                    runs = json.load(fh).get("runs", [])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"runs": runs + [entry]}, indent=1) + "\n")
    print("SCORING DONE fixture=%s H-A=%s H-B=%s" % (a.fixture, res["H_A"]["overall"], res["H_B"]["overall"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
