#!/usr/bin/env python3
"""Pin monitor -- the measure. Pure: no I/O, no database, no clock, no globals.

Design: PREREG.md (frozen, sha256
38b366897edd8e06af542988055dc1319a65f36b9995074cc6bfd88ec2a69a22) plus the
pre-data clarifications in build/DECISIONS.md (operator rulings R1-R4,
2026-11-24). Where the two differ, DECISIONS.md says so explicitly; nothing is
decided here that is not written in one of them.

ONE function produces the line: measure_day(). It owns every arithmetic step of
every field. _vs_rank, _pin_band, _gamma_strike and the two timestamp
normalisers are its private, pure helpers -- the self-test calls the same
objects the live run calls, so no measure is implemented twice.

REUSED DEFINITIONS -- not re-derived here:

  VS gross ranking   sql/2026-11-23_s107_v_gex_strike_rank_gross.sql (revision 3)
                     :88-99   gamma_strike and gamma_legs
                     :104     band  abs(strike/spot - 1) <= 0.05
                     :107-108 gross_cr = gamma_strike*(oi_call+oi_put)*spot^2/1e7
                     :127     ranked only where gross_cr > 0
                     :130     order gross_cr DESC, abs(strike-spot), strike
                     :157     lead_rel = (top - second)/top
                     :113-115 n_oi_no_gamma
                     Same rule, same knob names, as
                     fix/order_check_rev3/indep.py:11-15,87,94.

  clear lead         lead >= 0.05, lead = (top - second)/top.
                     Threshold: pin_live_replay_prereg_v2_FROZEN_2026-11-21.md
                     section 5 M1 ("K's lead >= 5 %") and section 6 clause 2
                     ("clear-lead runs").  Formula: analyze_v5.pick(),
                     lookback_v5/analyze_v5.py:139,151, which replay_v2 imports
                     (constructions_v2.py:40). The frozen design applies the
                     threshold to the lead of the construction being judged; the
                     monitor computes one construction, VS, so it is VS's own
                     lead_rel -- same formula, same threshold, same ranking order.

  Pin Band           the live v_gex_strike_pin_zone definition, read 2026-11-24
                     via pg_get_viewdef: def_length 3523,
                     def_md5 89c9ac6aef9eb332ddd28f9062d0e21e, pg 17.6
                     (CLAUDE.md rule 25). Reproduced in _pin_band; see
                     DECISIONS.md R4 for the clause-by-clause mapping.

TIMESTAMPS (condition 6; both tested in the self-test)
  gex_strike_snapshots.ts / gex_cycle_history.ts  true timestamptz -> _run_ts_ist
  hist_spot_bars_1m.bar_ts                        TRUE UTC from 2026-04
                                                  (ruling R2) -> _bar_ts_ist
  The two are the same arithmetic today and are kept as separate named functions
  because they rest on different registered facts and either can change alone.

KNOBS exist only for the mutation controls. The live run passes none of them.
"""
from __future__ import annotations

import statistics
from datetime import date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

# ---- frozen design constants (PREREG.md) ----
MARKET_OPEN = time(9, 15)            # PREREG: "runs in market hours (09:15-15:30 IST)"
MARKET_CLOSE = time(15, 30)          # inclusive; see DECISIONS.md clarification 1
REF_WINDOW = (time(14, 30), time(14, 35))   # PREREG: first run with ts in [14:30, 14:35)
CLOSE_BAR_IST = time(15, 29)         # PREREG: close of the 15:29 one-minute spot bar
BAND_FRAC = 0.05                     # VS rule :104
CLEAR_LEAD = 0.05                    # frozen prereg v2 section 5 M1
TAU_FALLBACK = 0.3                   # pin-zone view :79, used only if the parameter is absent
STRIKE_STEP = {"NIFTY": 50.0, "SENSEX": 100.0}   # PREREG Part 2; asserted against instruments

_KEY = 4   # strike dict key rounding; the view matches neighbours at abs(diff) < 0.0001


# ----------------------------------------------------------------- timestamps
def _run_ts_ist(ts: datetime) -> datetime:
    """gex_* .ts is a true timestamptz -> naive IST wall clock."""
    if ts.tzinfo is None:
        raise ValueError("run ts must be timezone-aware")
    return ts.astimezone(IST).replace(tzinfo=None)


def _bar_ts_ist(bar_ts: datetime) -> datetime:
    """hist_spot_bars_1m.bar_ts is TRUE UTC (ruling R2) -> naive IST wall clock.

    NOT the legacy IST-as-UTC handling of Rule 16 / TD-029, which applies to the
    pre-2026-04-07 era only.
    """
    if bar_ts.tzinfo is None:
        raise ValueError("bar_ts must be timezone-aware")
    return bar_ts.astimezone(IST).replace(tzinfo=None)


def close_bar_label_utc(day: date, close_ist: time = CLOSE_BAR_IST,
                        force_label: datetime | None = None) -> datetime:
    """The UTC instant the day's close bar is labelled with.

    15:29 IST minute-start -> '<day> 09:59:00+00'. KNOB force_label is mutant (f).
    """
    if force_label is not None:
        return force_label
    return datetime.combine(day, close_ist, tzinfo=IST).astimezone(UTC)


# ------------------------------------------------------------------ VS ranking
def _gamma_strike(cg, pg):
    """VS rule :88-99. A leg counts only when it is a number strictly > 0."""
    cg = 0.0 if cg is None else float(cg)
    pg = 0.0 if pg is None else float(pg)
    if cg > 0.0 and pg > 0.0:
        return (cg + pg) / 2.0, "both"
    if cg > 0.0:
        return cg, "call_only"
    if pg > 0.0:
        return pg, "put_only"
    return 0.0, "none"


def _vs_rank(legs: dict, spot: float, *, band: float = BAND_FRAC,
             require_positive_gross: bool = True, tie_higher: bool = False) -> dict:
    """Rank one run and one expiry leg by the VS gross rule.

    legs: {strike: {"gamma_call","gamma_put","oi_call","oi_put"}}.
    KNOB require_positive_gross is mutant (e); tie_higher is mutant (c).
    """
    if not (spot and spot > 0):
        raise ValueError("spot must be > 0")
    scale = (spot * spot) / 1e7

    gross, tags = {}, {}
    n_in_set = n_oi_no_gamma = 0
    for K in sorted(legs):
        e = legs[K]
        if abs(K / spot - 1.0) > band:
            continue
        n_in_set += 1
        gs, tag = _gamma_strike(e.get("gamma_call"), e.get("gamma_put"))
        oi_tot = float(e.get("oi_call") or 0.0) + float(e.get("oi_put") or 0.0)
        tags[K] = tag
        if tag == "none":
            if oi_tot > 0.0:
                n_oi_no_gamma += 1
        gv = gs * oi_tot * scale
        if gv > 0.0 or not require_positive_gross:
            gross[K] = gv

    sgn = -1.0 if tie_higher else 1.0
    seq = sorted(gross, key=lambda K: (-gross[K], abs(K - spot), sgn * K))

    lead_rel = None
    if len(seq) >= 2 and gross[seq[0]] > 0.0:
        lead_rel = (gross[seq[0]] - gross[seq[1]]) / gross[seq[0]]

    n_one_leg = sum(1 for K in seq if tags[K] in ("call_only", "put_only"))
    return {
        "n_in_set": n_in_set,
        "n_ranked": len(seq),
        "n_oi_no_gamma": n_oi_no_gamma,
        "n_one_leg_ranked": n_one_leg,
        "share_one_leg": (n_one_leg / len(seq)) if seq else None,
        "pin": seq[0] if seq else None,
        "lead_rel": lead_rel,
        "seq": seq,
        "gross": gross,
        "tags": tags,
    }


# -------------------------------------------------------------------- Pin Band
def _pin_band(gex_by_strike: dict, spot: float, tau: float) -> dict | None:
    """Recompute v_gex_strike_pin_zone's band for one run and one expiry leg.

    gex_by_strike: {strike: gex_cr} -- ALL strikes of the run and leg, no 5 %
    filter (the view's `scoped` has none).

    Returns {"lo","hi","n","peak","step","tau"} or None when the view would
    produce no row: no strike with gex_cr > 0, or fewer than two distinct
    strikes (then `strike_step` has no row and the anchor join is empty).
    """
    strikes = sorted({round(float(K), _KEY) for K in gex_by_strike})
    if len(strikes) < 2:
        return None                       # no strike_step row -> no band
    step = min(b - a for a, b in zip(strikes, strikes[1:]) if b - a > 0)

    pos = {round(float(K), _KEY): float(g) for K, g in gex_by_strike.items()
           if g is not None and float(g) > 0.0}
    if not pos:
        return None                       # peak CTE is empty -> no band

    # peak: gex_cr DESC, abs(strike - spot); `strike` added as a deterministic
    # third key (DECISIONS.md clarification 4).
    peak = min(pos, key=lambda K: (-pos[K], abs(K - spot), K))
    thr = tau * pos[peak]

    walked = {peak}
    for d in (-1.0, 1.0):
        K = round(peak + d * step, _KEY)
        while K in pos and pos[K] >= thr:
            walked.add(K)
            K = round(K + d * step, _KEY)

    return {"lo": min(walked), "hi": max(walked), "n": len(walked),
            "peak": peak, "step": step, "tau": tau}


# ------------------------------------------------------------------ the line
COLUMNS = [
    "date", "symbol", "expiry_date", "dte", "is_expiry_day",
    "n_runs_market", "n_runs_rankable", "share_rankable",
    "median_n_ranked", "median_share_one_leg", "median_n_oi_no_gamma",
    "n_clear_lead", "share_clear_lead", "n_lead_undefined",
    "n_pin_changes",
    "n_runs_board_both", "n_pin_eq_board", "share_pin_eq_board",
    "n_runs_band_and_pin", "n_pin_outside_band", "share_pin_outside_band",
    "n_runs_band_no_pin", "tau_used",
    "has_ref_run", "ref_ts_ist", "ref_spot",
    "pin_P", "board_B", "near_N", "p_eq_n",
    "close_1529", "close_read_at_ist",
    "dist_P_pts", "dist_P_steps", "dist_B_pts", "dist_B_steps",
    "dist_N_pts", "dist_N_steps",
    "abs_close_minus_ref_spot", "strike_step",
    "stop_flag", "stop_reason",
]

_FMT = {
    "share_rankable": "{:.6f}", "median_share_one_leg": "{:.6f}",
    "share_clear_lead": "{:.6f}", "share_pin_eq_board": "{:.6f}",
    "share_pin_outside_band": "{:.6f}",
    "median_n_ranked": "{:.1f}", "median_n_oi_no_gamma": "{:.1f}",
    "tau_used": "{:.4f}",
    "ref_spot": "{:.2f}", "pin_P": "{:.2f}", "board_B": "{:.2f}",
    "near_N": "{:.2f}", "close_1529": "{:.2f}",
    "dist_P_pts": "{:.2f}", "dist_B_pts": "{:.2f}", "dist_N_pts": "{:.2f}",
    "dist_P_steps": "{:.4f}", "dist_B_steps": "{:.4f}", "dist_N_steps": "{:.4f}",
    "abs_close_minus_ref_spot": "{:.2f}", "strike_step": "{:.2f}",
}


def format_line(rec: dict) -> str:
    """One CSV line. Blank means not measured -- never a zero (CLAUDE.md: NULL is a gap)."""
    out = []
    for c in COLUMNS:
        v = rec[c]
        if v is None:
            out.append("")
        elif isinstance(v, bool):
            out.append("true" if v else "false")
        elif c in _FMT:
            out.append(_FMT[c].format(v))
        else:
            out.append(str(v))
    for s in out:
        if "," in s or "\n" in s:
            raise ValueError(f"field would break the csv: {s!r}")
    return ",".join(out)


def header_line() -> str:
    return ",".join(COLUMNS)


# --------------------------------------------------------------- the measure
def measure_day(day: date, symbol: str, strike_rows: list, board_rows: list,
                bar_rows: list, tau: float, instruments_strike_step: float,
                close_read_at_ist: str | None, *,
                ref_window: tuple = REF_WINDOW,
                close_bar_ist: time = CLOSE_BAR_IST,
                force_close_label: datetime | None = None,
                band: float = BAND_FRAC,
                require_positive_gross: bool = True,
                tie_higher: bool = False,
                dist_to: str = "close") -> dict:
    """Produce the whole line for one symbol-day. The only measure in the system.

    strike_rows  gex_strike_snapshots rows: run_id, ts(aware), expiry_date, dte,
                 strike, spot, oi_call, oi_put, gamma_call, gamma_put, gex_cr
    board_rows   gex_cycle_history rows: run_id, ts(aware), expiry_date,
                 pin_leader_strike
    bar_rows     hist_spot_bars_1m rows: bar_ts(aware), close
    tau          resolved as the view resolves it, by the caller
    close_read_at_ist  when the close bar was read (ruling R3); passed in, not
                 taken from a clock, so this function stays pure

    KNOBS, in order of the mutation controls: ref_window (a), close_bar_ist (b),
    tie_higher (c), dist_to (d), require_positive_gross (e), force_close_label
    (f); tau itself is (g). The live run passes none of them.
    """
    if dist_to not in ("close", "ref_spot"):
        raise ValueError(f"unknown dist_to {dist_to!r}")
    if symbol not in STRIKE_STEP:
        raise ValueError(f"unknown symbol {symbol!r}")

    step = STRIKE_STEP[symbol]
    if instruments_strike_step is not None and float(instruments_strike_step) != step:
        raise ValueError(
            f"instruments.strike_step is {instruments_strike_step} for {symbol}, "
            f"PREREG says {step} -- refusing to measure")

    # ---- group rows into (run_id, expiry_date), then keep each run's FRONT leg
    runs: dict = {}
    for r in strike_rows:
        k = (r["run_id"], r["expiry_date"])
        g = runs.setdefault(k, {"run_id": r["run_id"], "ts": r["ts"],
                                "expiry_date": r["expiry_date"], "dte": r["dte"],
                                "spot": float(r["spot"]), "legs": {}, "gex": {}})
        K = round(float(r["strike"]), _KEY)
        g["legs"][K] = {"gamma_call": r["gamma_call"], "gamma_put": r["gamma_put"],
                        "oi_call": r["oi_call"], "oi_put": r["oi_put"]}
        g["gex"][K] = r["gex_cr"]

    front: dict = {}
    for (run_id, expiry), g in runs.items():
        cur = front.get(run_id)
        if cur is None or expiry < cur["expiry_date"]:
            front[run_id] = g

    board = {(b["run_id"], b["expiry_date"]): b for b in board_rows}

    # ---- market-hours runs, in time order
    mkt = []
    for g in front.values():
        t = _run_ts_ist(g["ts"])
        if MARKET_OPEN <= t.time() <= MARKET_CLOSE:
            mkt.append((t, g))
    mkt.sort(key=lambda x: (x[0], str(x[1]["run_id"])))

    per_run = []
    for t_ist, g in mkt:
        vs = _vs_rank(g["legs"], g["spot"], band=band,
                      require_positive_gross=require_positive_gross,
                      tie_higher=tie_higher)
        bd = _pin_band(g["gex"], g["spot"], tau)
        b = board.get((g["run_id"], g["expiry_date"]))
        per_run.append({
            "t": t_ist, "g": g, "vs": vs, "band": bd,
            "board_pin": (None if b is None or b.get("pin_leader_strike") is None
                          else round(float(b["pin_leader_strike"]), _KEY)),
        })

    # ---- Part 1
    n_runs_market = len(per_run)
    rankable = [x for x in per_run if x["vs"]["pin"] is not None]
    n_rankable = len(rankable)

    med_ranked = statistics.median([x["vs"]["n_ranked"] for x in per_run]) if per_run else None
    one_leg = [x["vs"]["share_one_leg"] for x in per_run if x["vs"]["n_ranked"] > 0]
    med_one_leg = statistics.median(one_leg) if one_leg else None
    med_oi_no_g = statistics.median([x["vs"]["n_oi_no_gamma"] for x in per_run]) if per_run else None

    n_clear = sum(1 for x in rankable
                  if x["vs"]["lead_rel"] is not None and x["vs"]["lead_rel"] >= CLEAR_LEAD)
    n_lead_undef = sum(1 for x in rankable if x["vs"]["lead_rel"] is None)

    pins = [x["vs"]["pin"] for x in rankable]
    n_pin_changes = sum(1 for a, b in zip(pins, pins[1:]) if a != b)

    both = [x for x in rankable if x["board_pin"] is not None]
    n_eq_board = sum(1 for x in both if x["vs"]["pin"] == x["board_pin"])

    band_and_pin = [x for x in rankable if x["band"] is not None]
    n_outside = sum(1 for x in band_and_pin
                    if not (x["band"]["lo"] <= x["vs"]["pin"] <= x["band"]["hi"]))
    n_band_no_pin = sum(1 for x in per_run
                        if x["vs"]["pin"] is None and x["band"] is not None)

    # ---- PREREG Part 1 stop condition: a market-hours run with a chain and no
    # rankable pin. Reported; the line is still produced.
    bad = [x for x in per_run if x["vs"]["n_in_set"] > 0 and x["vs"]["pin"] is None]
    stop_flag = bool(bad)
    stop_reason = None
    if bad:
        stop_reason = ("no rankable pin at " +
                       " ".join(x["t"].strftime("%H:%M:%S") for x in bad[:5]) +
                       (" (+%d more)" % (len(bad) - 5) if len(bad) > 5 else ""))

    # ---- Part 2
    ref = None
    for x in per_run:
        if ref_window[0] <= x["t"].time() < ref_window[1]:
            ref = x
            break

    want = close_bar_label_utc(day, close_bar_ist, force_close_label)
    close = None
    for br in bar_rows:
        if br["bar_ts"].astimezone(UTC) == want.astimezone(UTC):
            close = float(br["close"])
            break

    rec = {c: None for c in COLUMNS}
    rec.update({
        "date": day.isoformat(), "symbol": symbol,
        "n_runs_market": n_runs_market, "n_runs_rankable": n_rankable,
        "share_rankable": (n_rankable / n_runs_market) if n_runs_market else None,
        "median_n_ranked": med_ranked, "median_share_one_leg": med_one_leg,
        "median_n_oi_no_gamma": med_oi_no_g,
        "n_clear_lead": n_clear,
        "share_clear_lead": (n_clear / n_rankable) if n_rankable else None,
        "n_lead_undefined": n_lead_undef,
        "n_pin_changes": n_pin_changes,
        "n_runs_board_both": len(both), "n_pin_eq_board": n_eq_board,
        "share_pin_eq_board": (n_eq_board / len(both)) if both else None,
        "n_runs_band_and_pin": len(band_and_pin), "n_pin_outside_band": n_outside,
        "share_pin_outside_band": (n_outside / len(band_and_pin)) if band_and_pin else None,
        "n_runs_band_no_pin": n_band_no_pin,
        "tau_used": tau,
        "has_ref_run": ref is not None,
        "close_1529": close, "close_read_at_ist": close_read_at_ist,
        "strike_step": step, "stop_flag": stop_flag, "stop_reason": stop_reason,
    })

    if ref is None:
        # PREREG: no such run -> the day's Part 2 fields are blank and the day is
        # counted as "no reference run". Blank, never zero.
        return rec

    g = ref["g"]
    P = ref["vs"]["pin"]
    B = ref["board_pin"]
    listed = sorted(g["legs"])
    sgn = -1.0 if tie_higher else 1.0
    N = min(listed, key=lambda K: (abs(K - g["spot"]), sgn * K)) if listed else None

    anchor = close if dist_to == "close" else g["spot"]

    def _d(strike):
        if strike is None or anchor is None:
            return None, None
        pts = abs(anchor - strike)
        return pts, pts / step

    dP, sP = _d(P)
    dB, sB = _d(B)
    dN, sN = _d(N)

    rec.update({
        "expiry_date": g["expiry_date"].isoformat(), "dte": g["dte"],
        "is_expiry_day": g["dte"] == 0,
        "ref_ts_ist": ref["t"].strftime("%Y-%m-%d %H:%M:%S"),
        "ref_spot": g["spot"],
        "pin_P": P, "board_B": B, "near_N": N,
        "p_eq_n": (None if (P is None or N is None) else P == N),
        "dist_P_pts": dP, "dist_P_steps": sP,
        "dist_B_pts": dB, "dist_B_steps": sB,
        "dist_N_pts": dN, "dist_N_steps": sN,
        "abs_close_minus_ref_spot": (None if close is None else abs(close - g["spot"])),
    })
    return rec
