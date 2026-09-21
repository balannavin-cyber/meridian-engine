#!/usr/bin/env python3
"""M1 era 2 -- decay curve on BOTH mid and last, and the divergence between them.

WHY THIS EXISTS. Era 1 has no bid/ask, so its decay curve is measured on
`close`, a last-trade print. Era 2 carries bid/ask, so the same curve can be
measured both ways. The mid-minus-last divergence measured here is the ERROR
BAR on every era-1 figure: if it is small relative to the 50/60/70/80 spacing
of the harvest sweep, era 1's curve can choose a threshold; if it is
comparable, era 1 can only bracket one.

TWO DIFFERENT N's, AND CONFLATING THEM UNDERSTATES THIS BADLY.
  * The DECAY CURVE is a per-CYCLE property. Era 2 holds roughly 14 cycles per
    symbol, which is THIN by the brief's own N<20 rule.
  * The DIVERGENCE is a per-STAMP property -- two prices observed at the same
    instant. ~14 cycles x ~5 days x 2 sides is on the order of 140 paired
    observations per symbol, which is ample for a spread-bias distribution.
Both are reported, each with its own N. An earlier draft of this analysis
declared era 2 "thin" on the cycle count alone and nearly abandoned the
calibration the whole comparison depends on.

TWO WINDOWS, TREATED AS A COHORT BOUNDARY.
  W1  historical_option_chain_snapshots  2026-03-16 .. 2026-06-03
  W2  option_chain_snapshots             2026-08-24 .. 2026-09-11
Between them only gex_strike_snapshots exists, and it carries NO price column
(ADR-015, 14 cols), so there is no premium at all from 2026-06-04 to
2026-08-23. The two windows are measured separately and their divergence
distributions compared BEFORE any pooling.

W2 IS POST-CAS. From 2026-08-03 (ADR-022) F&O continuous trading ends 15:15
and the close is set by auction 15:15-15:35, with index derivatives running to
15:40. So a 15:25 stamp on an OPTION is a real trade, but the UNDERLYING is
inside its auction window at that moment -- which bears on the spot-proximity
test used for tested/untested, not on the option prices themselves.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import srs_io as io
import srs_cycles as cyc
from explore import (LEGS, SQRT252, THRESHOLDS, STAMP_ORDER, STATE_ORDER,
                     base_rates, fmt_n, pct, regime_of, round_to, sort_key,
                     terciles, _ser, _deser)

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "srs_exploration_2026-09-21_m1_era2.md"
CACHE = HERE / ".m1_era2_cycles.json"

WINDOWS = [
    ("W1", "historical_option_chain_snapshots", dt.date(2026, 3, 16), dt.date(2026, 6, 3)),
    ("W2", "option_chain_snapshots", dt.date(2026, 8, 24), dt.date(2026, 9, 11)),
]
CADENCE = 5          # 5-minute chain snapshots -> 10-minute staleness budget


def qs(xs, ps=(0.05, 0.25, 0.50, 0.75, 0.95)):
    xs = sorted(xs)
    if not xs:
        return [None] * len(ps)
    n = len(xs)
    return [xs[min(n - 1, max(0, int(round(p * (n - 1)))))] for p in ps]


def trading_days(symbol, lo, hi):
    """Candidate days from volatility_snapshots (small, spans both eras)."""
    rows = io._rows("volatility_snapshots",
                    [("select", "ts"), ("symbol", f"eq.{symbol}"),
                     ("ts", f"gte.{lo.isoformat()}"),
                     ("ts", f"lt.{(hi + dt.timedelta(days=1)).isoformat()}"),
                     ("order", "ts.asc")])
    return sorted({io.ist_clock("volatility_snapshots", r["ts"]).date() for r in rows})


def mid_of(row):
    """(bid+ask)/2, or None when the quote is not two-sided and sane.

    A zero or crossed quote is not a price. Returning it as one would put the
    divergence it produces into the error bar as though it were spread.
    """
    b, a = row.get("bid"), row.get("ask")
    if b is None or a is None:
        return None
    b, a = float(b), float(a)
    if b <= 0 or a <= 0 or a < b:
        return None
    return (a + b) / 2.0


def cycle_metrics_era2(symbol, relation, cyc_rec):
    days, expiry = cyc_rec["days"], cyc_rec["expiry"]
    d1, dlast = days[0], days[-1]
    end_excl = (dlast + dt.timedelta(days=1)).isoformat()
    sym_f = [("symbol", f"eq.{symbol}")]

    vs = io._rows("volatility_snapshots",
                  [("select", "ts,spot,atm_iv_avg")] + sym_f
                  + [("ts", f"gte.{d1.isoformat()}"), ("ts", f"lt.{end_excl}"),
                     ("order", "ts.asc")])
    vs_idx = cyc.ist_index("volatility_snapshots", vs, "ts")
    if not vs_idx:
        return None, "no volatility_snapshots rows in cycle"
    e, _, why = cyc.pick_anchor(vs_idx, d1, cyc.ANCHOR_REF, CADENCE)
    if e is None:
        return None, f"Day-1 10:30 spot/IV: {why}"
    if e[1].get("spot") is None or e[1].get("atm_iv_avg") is None:
        return None, "Day-1 10:30 spot or atm_iv_avg is NULL"
    spot_ref = float(e[1]["spot"])
    atm_iv = float(e[1]["atm_iv_avg"])
    sigma_d = spot_ref * (atm_iv / 100.0) / SQRT252
    if sigma_d <= 0:
        return None, f"non-positive sigma_daily from atm_iv={atm_iv}"

    step = 50 if symbol == "NIFTY" else 100
    k_atm = round_to(spot_ref, step)
    k_pe = int(math.floor(spot_ref * 0.99 / step) * step)
    k_ce = int(math.ceil(spot_ref * 1.01 / step) * step)
    contracts = {("ATM", "CE"): k_atm, ("ATM", "PE"): k_atm,
                 ("OTM", "PE"): k_pe, ("OTM", "CE"): k_ce}

    series = {}
    for (tag, ot), k in contracts.items():
        rows = io._rows(relation,
                        [("select", "ts,bid,ask,ltp,volume,oi")] + sym_f
                        + [("expiry_date", f"eq.{expiry.isoformat()}"),
                           ("strike", f"eq.{k}"), ("option_type", f"eq.{ot}"),
                           ("ts", f"gte.{d1.isoformat()}"),
                           ("ts", f"lt.{end_excl}"), ("order", "ts.asc")])
        series[(tag, ot)] = cyc.ist_index(relation, rows, "ts")
        if not series[(tag, ot)]:
            return None, f"no chain rows for {tag} {ot} strike {k} expiry {expiry}"

    def quote_at(key, day, target):
        ent, _, why = cyc.pick_anchor(series[key], day, target, CADENCE)
        if ent is None:
            return None, None, why
        r = ent[1]
        ltp = r.get("ltp")
        return (mid_of(r), (float(ltp) if ltp is not None else None), None)

    ref_mid, ref_ltp = {}, {}
    for key in contracts:
        m, l, why = quote_at(key, d1, cyc.ANCHOR_REF)
        if m is None or m <= 0:
            return None, f"Day-1 10:30 {key[0]}_{key[1]} mid: {why or 'no two-sided quote'}"
        if l is None or l <= 0:
            return None, f"Day-1 10:30 {key[0]}_{key[1]} ltp: {why or 'non-positive'}"
        ref_mid[key], ref_ltp[key] = m, l

    def legs(d):
        return {"OTM_PE": d[("OTM", "PE")], "OTM_CE": d[("OTM", "CE")],
                "STRADDLE": d[("ATM", "CE")] + d[("ATM", "PE")]}
    rl_mid, rl_ltp = legs(ref_mid), legs(ref_ltp)

    spots = [float(r["spot"]) for _, r in vs_idx if r.get("spot") is not None]
    tested = {"OTM_PE": min(abs(s - k_pe) for s in spots) <= 0.5 * sigma_d,
              "OTM_CE": min(abs(s - k_ce) for s in spots) <= 0.5 * sigma_d,
              "STRADDLE": min(abs(s - k_atm) for s in spots) <= 0.5 * sigma_d}

    stamps = []
    for n, day in enumerate(days, 1):
        targets = [(f"D{n}", cyc.ANCHOR_CLOSE)]
        if day == expiry:
            targets.append(("EXP1300", cyc.ANCHOR_EXPIRY))
        for label, target in targets:
            mids, ltps, miss = {}, {}, []
            for key in contracts:
                m, l, why = quote_at(key, day, target)
                if m is None:
                    miss.append(f"{key[0]}_{key[1]} mid: {why or 'no two-sided quote'}")
                if l is None or l <= 0:
                    miss.append(f"{key[0]}_{key[1]} ltp: {why or 'non-positive'}")
                mids[key], ltps[key] = m, l
            if miss:
                stamps.append({"label": label, "day": day, "rejected": "; ".join(miss)})
                continue
            lm, ll = legs(mids), legs(ltps)
            dmid = {lg: (1.0 - lm[lg] / rl_mid[lg]) * 100.0 for lg in LEGS}
            dltp = {lg: (1.0 - ll[lg] / rl_ltp[lg]) * 100.0 for lg in LEGS}
            stamps.append({"label": label, "day": day, "rejected": None,
                           "decay": dmid, "decay_ltp": dltp,
                           "div_pp": {lg: dltp[lg] - dmid[lg] for lg in LEGS},
                           "zero_prev_vol": {lg: False for lg in LEGS}})

    return {"symbol": symbol, "expiry": expiry, "n_days": len(days),
            "window": cyc_rec["window"], "spot_ref": spot_ref, "atm_iv": atm_iv,
            "sigma_d": sigma_d, "em": rl_mid["STRADDLE"], "k_atm": k_atm,
            "k_pe": k_pe, "k_ce": k_ce, "tested": tested, "stamps": stamps}, None


def collect():
    measured, excluded = [], []
    for wname, relation, lo, hi in WINDOWS:
        for sym in ("NIFTY", "SENSEX"):
            days = trading_days(sym, lo, hi)
            front = cyc.front_expiry_by_day_chain(relation, [("symbol", f"eq.{sym}")],
                                                  "ts", days, horizon_days=14)
            breaks = cyc.assert_monotonic_front_expiry(front)
            ok, bad, tested = cyc.verify_expiry_day_membership(front)
            print(f"{wname} {sym}: {len(days)}d, chain front on {len(front)}d, "
                  f"monotonicity_breaks={len(breaks)}, front(E)==E {ok}/{tested}")
            cycles = cyc.build_cycles(days, front)
            for c in cycles:
                c["window"] = wname
                if not c["complete"]:
                    excluded.append((f"{wname}/{sym}", c["expiry"], len(c["days"]),
                                     c["reason"]))
            comp = [c for c in cycles if c["complete"]]
            print(f"{wname} {sym}: {len(comp)} complete cycles")
            for c in comp:
                rec, why = cycle_metrics_era2(sym, relation, c)
                if rec is None:
                    excluded.append((f"{wname}/{sym}", c["expiry"], len(c["days"]), why))
                else:
                    measured.append(rec)
            print(f"  running total measured={len(measured)} requests={io.REQUESTS_MADE}")
    return measured, excluded


def render(measured, excluded):
    w = []
    a = w.append
    by_sym = defaultdict(list)
    for c in measured:
        by_sym[c["symbol"]].append(c)
    cuts = {s: terciles([c["atm_iv"] for c in cs]) for s, cs in by_sym.items()}

    dec_mid, dec_ltp, div = (defaultdict(list) for _ in range(3))
    div_win = defaultdict(list)
    n_pairs = 0
    for c in measured:
        rg = regime_of(c["atm_iv"], cuts[c["symbol"]])
        for s in c["stamps"]:
            if s["rejected"]:
                continue
            for lg in LEGS:
                state = "tested" if c["tested"][lg] else "untested"
                for st in (state, "pooled"):
                    k = (c["symbol"], "all", lg, st, s["label"])
                    dec_mid[k].append(s["decay"][lg])
                    dec_ltp[k].append(s["decay_ltp"][lg])
                    div[(c["symbol"], lg, st, s["label"])].append(s["div_pp"][lg])
                    div_win[(c["window"], c["symbol"], st)].append(s["div_pp"][lg])
                n_pairs += 1

    a("# M1 era 2 -- decay on mid and on last, and the divergence between them")
    a("")
    a(f"Generated {dt.date.today().isoformat()}. Read-only.")
    a("")
    a("## Cohort, and the two N's")
    a("")
    a(f"Measured cycles: **{len(measured)}**. Excluded: **{len(excluded)}**. "
      f"Paired (mid, last) stamp-legs: **{n_pairs}**.")
    a("")
    a("These are different units and must not be conflated:")
    a("")
    a("- the **decay curve** is per CYCLE, so era 2 is THIN and marked so;")
    a("- the **divergence** is per STAMP -- two prices at the same instant -- so "
      f"its N is {n_pairs}, which is not thin. This is the quantity the era-1 "
      "error bar needs.")
    a("")
    a("## Two windows, and the hole between them")
    a("")
    a("| window | source | span | note |")
    a("|---|---|---|---|")
    a("| W1 | `historical_option_chain_snapshots` | 2026-03-16 .. 2026-06-03 | |")
    a("| -- | *none* | 2026-06-04 .. 2026-08-23 | **no premium exists.** "
      "`gex_strike_snapshots` is the only per-strike source and carries NO price "
      "column (ADR-015, 14 cols). |")
    a("| W2 | `option_chain_snapshots` | 2026-08-24 .. 2026-09-11 | post-CAS "
      "(ADR-022): F&O continuous trade ends 15:15, index derivatives run to "
      "15:40, so a 15:25 option stamp is real but the UNDERLYING is mid-auction. |")
    a("")
    a("### Divergence by window -- checked BEFORE pooling")
    a("")
    a("Percentage points of the decay ratio, `decay(last) - decay(mid)`. "
      "Positive means the last-trade price makes decay look LARGER than the "
      "two-sided quote does.")
    a("")
    a("| window | symbol | state | N | P05 | P25 | median | P75 | P95 |")
    a("|---|---|---|---:|---:|---:|---:|---:|---:|")
    for k in sorted(div_win):
        xs = div_win[k]
        p = qs(xs)
        a(f"| {k[0]} | {k[1]} | {k[2]} | {fmt_n(len(xs))} | "
          + " | ".join(f"{v:+.1f}" for v in p) + " |")
    a("")
    a("## E2.A  Divergence by Day-N and state -- the era-1 error bar")
    a("")
    a("The spread widens as an option decays, so this is reported per stamp.")
    a("")
    a("| symbol | leg | state | stamp | N | P05 | P25 | median | P75 | P95 |")
    a("|---|---|---|---|---:|---:|---:|---:|---:|---:|")
    for k in sorted(div, key=lambda x: (x[0], x[1], STATE_ORDER.get(x[2], 9),
                                        STAMP_ORDER.index(x[3])
                                        if x[3] in STAMP_ORDER else 99)):
        xs = div[k]
        p = qs(xs)
        a(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {fmt_n(len(xs))} | "
          + " | ".join(f"{v:+.1f}" for v in p) + " |")
    a("")
    a("## E2.B  Decay curve on MID (primary) -- per cycle, THIN")
    a("")
    a("| symbol | leg | state | stamp | N | P25 | median | P75 | median on LAST |")
    a("|---|---|---|---|---:|---:|---:|---:|---:|")
    for k in sorted(dec_mid, key=sort_key):
        if k[4] not in STAMP_ORDER:
            continue
        p25, med, p75 = pct(dec_mid[k])
        _, medl, _ = pct(dec_ltp[k])
        a(f"| {k[0]} | {k[2]} | {k[3]} | {k[4]} | {fmt_n(len(dec_mid[k]))} | "
          f"{p25:.1f} | {med:.1f} | {p75:.1f} | {medl:.1f} |")
    a("")
    a("## Excluded cycles")
    a("")
    a("| window/symbol | expiry | days | why |")
    a("|---|---|---:|---|")
    for s, e, n, why in excluded:
        a(f"| {s} | {e} | {n} | {why} |")
    a("")
    return "\n".join(w) + "\n"


def main():
    refetch = "--refetch" in sys.argv
    if not refetch and CACHE.exists():
        payload = json.loads(CACHE.read_text(), object_hook=_deser)
        measured = payload["measured"]
        excluded = [tuple(x) for x in payload["excluded"]]
        print(f"reusing {len(measured)} measured cycles (pass --refetch to re-sweep)")
    else:
        measured, excluded = collect()
        with CACHE.open("w", encoding="utf-8") as fh:
            json.dump({"measured": measured, "excluded": excluded}, fh, default=_ser)
    body = render(measured, excluded)
    with RESULTS.open("w", encoding="utf-8") as fh:
        fh.write(body)
    print(f"\nmeasured={len(measured)} excluded={len(excluded)} "
          f"requests={io.REQUESTS_MADE}")
    print(f"wrote {RESULTS}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except io.Probe as e:
        print(f"FATAL probe failure: {e}", file=sys.stderr)
        raise SystemExit(2) from None
