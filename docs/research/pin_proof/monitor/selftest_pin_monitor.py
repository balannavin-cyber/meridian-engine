#!/usr/bin/env python3
"""Pin monitor self-test. Synthetic days only -- no database, no network.

Every expectation below is HAND-COMPUTED from the fixture and written here
BEFORE the run (the arithmetic is shown in the comment beside each number), so
the assertions state a belief rather than record an observation
(CLAUDE.md rule 0, clause 3).

Scenarios required by the build conditions, and where each lives:
  a run with no rankable pin ............ day A, run R2 (11:00)
  no run in [14:30, 14:35) .............. day B
  P = N ................................. day C (and the N tie is there too)
  a tie on gross_cr ..................... day A, run R3 (13:00)
  a pin outside the Pin Band ............ day A, runs R3 and R4
  an expiry day ......................... day C (dte 0)
  hand-computed band walk (ruling R4) ... BAND section, days A and D
  both timestamp conventions ............ TIME section

Mutation controls (each must make at least one check FAIL):
  (a) reference window [14:35, 14:40)
  (b) close from the 15:28 bar
  (c) nearest-to-spot tie to the higher strike
  (d) distance to spot at reference instead of to the close
  (e) gross_cr > 0 dropped
  (f) close label 15:29:00+00 instead of 09:59:00+00
  (g) tau changed from the resolved value

Run: ( ulimit -v 700000; PYTHONDONTWRITEBYTECODE=1 python3 -B selftest_pin_monitor.py )
Exit 0 all pass, 3 any failure.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pin_monitor_lib import (  # noqa: E402
    COLUMNS, UTC, _bar_ts_ist, _pin_band, _run_ts_ist, close_bar_label_utc,
    format_line, measure_day,
)

LOG = []
OK = True
NP = NF = 0


def chk(name, cond, detail=""):
    global OK, NP, NF
    cond = bool(cond)
    OK = OK and cond
    if cond:
        NP += 1
    else:
        NF += 1
    LOG.append(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))


def eq(a, b, tol=1e-9):
    if a is None or b is None:
        return a is b or a == b
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) <= tol
        except (TypeError, ValueError):
            return False
    return a == b


# ---------------------------------------------------------------- fixtures
def srow(run, ts_utc, exp, dte, spot, K, gc, gp, oc, op, gex):
    return {"run_id": run, "ts": ts_utc, "expiry_date": exp, "dte": dte,
            "strike": K, "spot": spot, "gamma_call": gc, "gamma_put": gp,
            "oi_call": oc, "oi_put": op, "gex_cr": gex}


def brow(run, ts_utc, exp, pin):
    return {"run_id": run, "ts": ts_utc, "expiry_date": exp, "pin_leader_strike": pin}


def U(d, h, m):
    return datetime(d.year, d.month, d.day, h, m, tzinfo=UTC)


# ============================================================== DAY A
# NIFTY 2026-11-25, spot 25000 at every run, front expiry 2026-11-27 (dte 2),
# next leg 2026-12-04. spot^2/1e7 = 25000^2/1e7 = 62.5 exactly, so every
# gross_cr below is an exact decimal.
DA = date(2026, 11, 25)
EA, EA2 = date(2026, 11, 27), date(2026, 12, 4)
A_rows, A_board = [], []

# R0 09:10 IST = 03:40 UTC -- PRE-OPEN, must be excluded. Its 24000 strike would
# win every ranking if it were not (gross 0.01*20000*62.5 = 12500).
A_rows += [srow("R0", U(DA, 3, 40), EA, 2, 25000, 24000, 0.01, 0.01, 10000, 10000, 9.0),
           srow("R0", U(DA, 3, 40), EA, 2, 25000, 25000, 0.0001, 0.0001, 100, 100, 1.0)]

# R1 09:15 IST = 03:45 UTC -- the inclusive open boundary.
#   24950 gs 0.0002 oi 200 -> 0.0002*200*62.5 =  2.50
#   25000 gs 0.0004 oi 200 -> 0.0004*200*62.5 =  5.00  <- pin
#   25050 gs 0.0001 oi 200 -> 0.0001*200*62.5 =  1.25
#   lead = (5.00-2.50)/5.00 = 0.50 -> clear. one-leg 0/3. oi-no-gamma 0.
#   band: step 50, peak 25000 (gex 8.0), thr 0.3*8 = 2.4;
#         down 24950 gex 1.0 < 2.4 stop; up 25050 gex 3.0 >= 2.4 join;
#         25100 absent -> [25000, 25050] n 2. pin inside.
A_rows += [srow("R1", U(DA, 3, 45), EA, 2, 25000, 24950, 0.0002, 0.0002, 100, 100, 1.0),
           srow("R1", U(DA, 3, 45), EA, 2, 25000, 25000, 0.0004, 0.0004, 100, 100, 8.0),
           srow("R1", U(DA, 3, 45), EA, 2, 25000, 25050, 0.0001, 0.0001, 100, 100, 3.0)]
A_board += [brow("R1", U(DA, 3, 45), EA, 25000)]          # equals the pin

# R2 11:00 IST = 05:30 UTC -- a chain and NO rankable pin (the stop condition).
#   both strikes have no gamma on either leg; 25000 holds OI -> oi_no_gamma 1.
#   band: step 50, pos {25000: 2.0}, peak 25000, thr 0.6; 25050 gex 0.0 not > 0
#         -> [25000, 25000] n 1. A band with no pin.
A_rows += [srow("R2", U(DA, 5, 30), EA, 2, 25000, 25000, 0.0, 0.0, 500, 500, 2.0),
           srow("R2", U(DA, 5, 30), EA, 2, 25000, 25050, 0.0, 0.0, 0, 0, 0.0)]
A_board += [brow("R2", U(DA, 5, 30), EA, 25000)]          # run is not rankable -> not paired

# R3 13:00 IST = 07:30 UTC -- a TIE on gross_cr, and both tie-breaks exercised.
#   24950 gs 0.0004 oi 200 -> 5.00
#   25050 gs 0.0004 oi 200 -> 5.00   equal gross; |24950-25000| = |25050-25000| = 50
#                                    -> distance ties too -> LOWER strike -> 24950
#   25000 gs 0.0001 oi 200 -> 1.25
#   lead = (5.00-5.00)/5.00 = 0.0 -> NOT a clear lead.
#   band: step 50, peak 25000 (gex 9.0), thr 2.7; 24950 gex 1.0 < 2.7 stop;
#         25050 gex 1.0 < 2.7 stop -> [25000, 25000] n 1. pin 24950 OUTSIDE.
A_rows += [srow("R3", U(DA, 7, 30), EA, 2, 25000, 24950, 0.0004, 0.0004, 100, 100, 1.0),
           srow("R3", U(DA, 7, 30), EA, 2, 25000, 25000, 0.0001, 0.0001, 100, 100, 9.0),
           srow("R3", U(DA, 7, 30), EA, 2, 25000, 25050, 0.0004, 0.0004, 100, 100, 1.0)]
# no Board row at R3 -> excluded from the pin-vs-Board denominator

# R4 14:30 IST = 09:00 UTC -- THE REFERENCE RUN.
#   23000 |23000/25000-1| = 0.08 > 0.05 -> out of the set entirely
#   24900 gs mean(0.0001,0.0003) = 0.0002 oi 200 -> 0.0002*200*62.5  =  2.50
#   24950 gs 0.0002 oi 400                      -> 0.0002*400*62.5  =  5.00
#   25000 gs mean(0.0004,0.0002) = 0.0003 oi 1000 -> 0.0003*1000*62.5 = 18.75
#   25050 put_only 0.0006 oi 600                -> 0.0006*600*62.5  = 22.50
#   25100 no gamma, oi 1400 > 0                 -> oi_no_gamma, gross 0, unranked
#   25150 gs 0.0010 oi 800                      -> 0.0010*800*62.5  = 50.00  <- pin
#   n_in_set 6, n_ranked 5, one-leg 1/5 = 0.2, oi_no_gamma 1
#   lead = (50.00-22.50)/50.00 = 0.55 -> clear
#   band: all strikes incl 23000 -> diffs 1900,50,50,50,50,50 -> step 50
#         pos excludes 25100 (gex -1.0); peak 25000 (gex 10.0), thr 3.0
#         down 24950 gex 2.0 < 3.0 stop; up 25050 gex 4.0 >= 3.0 join;
#         25100 not positive -> stop -> [25000, 25050] n 2. pin 25150 OUTSIDE.
#   N = listed strike nearest spot 25000 -> 25000 (distance 0). P != N.
for K, gc, gp, oc, op, gx in [(23000, 0.0002, 0.0002, 1000, 1000, 5.0),
                              (24900, 0.0001, 0.0003, 100, 100, 1.0),
                              (24950, 0.0002, 0.0002, 200, 200, 2.0),
                              (25000, 0.0004, 0.0002, 500, 500, 10.0),
                              (25050, 0.0, 0.0006, 300, 300, 4.0),
                              (25100, 0.0, 0.0, 700, 700, -1.0),
                              (25150, 0.0010, 0.0010, 400, 400, 2.0)]:
    A_rows.append(srow("R4", U(DA, 9, 0), EA, 2, 25000, K, gc, gp, oc, op, gx))
# R4's NEXT expiry leg. gross 0.002*2000*62.5 = 250 at 25200, so taking the wrong
# leg -- or pooling the two -- yields pin 25200 instead of 25150.
A_rows += [srow("R4", U(DA, 9, 0), EA2, 9, 25000, 25200, 0.002, 0.002, 1000, 1000, 3.0),
           srow("R4", U(DA, 9, 0), EA2, 9, 25000, 25250, 0.0001, 0.0001, 100, 100, 1.0)]
A_board += [brow("R4", U(DA, 9, 0), EA, 25000),           # B for the FRONT leg
            brow("R4", U(DA, 9, 0), EA2, 25200)]          # the next leg's Board row

# R5 15:30 IST = 10:00 UTC -- the inclusive close boundary, and ONE ranked
#   strike only, so lead_rel is undefined.
#   25000 gs 0.0002 oi 200 -> 2.50 <- pin ; 25100 no gamma, oi 0 -> not counted
#   band: strikes [25000, 25100] -> step 100 (a sparse run has a bigger step);
#         peak 25000 (gex 4.0), thr 1.2; 25100 gex 1.0 < 1.2 -> [25000,25000] n 1.
A_rows += [srow("R5", U(DA, 10, 0), EA, 2, 25000, 25000, 0.0002, 0.0002, 100, 100, 4.0),
           srow("R5", U(DA, 10, 0), EA, 2, 25000, 25100, 0.0, 0.0, 0, 0, 1.0)]
A_board += [brow("R5", U(DA, 10, 0), EA, 25100)]          # differs from the pin

# R6 15:35 IST = 10:05 UTC -- POST-CLOSE, must be excluded.
A_rows += [srow("R6", U(DA, 10, 5), EA, 2, 25000, 24000, 0.01, 0.01, 10000, 10000, 9.0),
           srow("R6", U(DA, 10, 5), EA, 2, 25000, 25000, 0.0001, 0.0001, 100, 100, 1.0)]

# Bars: the true 15:29 IST close is 09:59 UTC. The other two are decoys that
# mutants (b) and (f) must land on.
A_bars = [{"bar_ts": U(DA, 9, 59), "close": 25080.0},     # 15:29 IST  <- the one
          {"bar_ts": U(DA, 9, 58), "close": 25010.0},     # 15:28 IST  -> mutant (b)
          {"bar_ts": U(DA, 15, 29), "close": 25500.0}]    # 20:59 IST  -> mutant (f)

A_READ_AT = "2026-11-25 16:35:00"

EXP_A = {
    "date": "2026-11-25", "symbol": "NIFTY",
    "expiry_date": "2026-11-27", "dte": 2, "is_expiry_day": False,
    # market runs R1,R2,R3,R4,R5 -- R0 and R6 excluded
    "n_runs_market": 5, "n_runs_rankable": 4, "share_rankable": 4 / 5,
    # n_ranked [3,0,3,5,1] -> sorted [0,1,3,3,5] -> 3
    "median_n_ranked": 3,
    # share_one_leg over n_ranked>0: [0.0,0.0,0.2,0.0] -> sorted [0,0,0,0.2] -> 0.0
    "median_share_one_leg": 0.0,
    # oi_no_gamma [0,1,0,1,0] -> sorted [0,0,0,1,1] -> 0
    "median_n_oi_no_gamma": 0,
    # clear: R1 0.50 yes, R3 0.00 no, R4 0.55 yes, R5 undefined no
    "n_clear_lead": 2, "share_clear_lead": 2 / 4, "n_lead_undefined": 1,
    # pins 25000, 24950, 25150, 25000 -> 3 changes
    "n_pin_changes": 3,
    # paired: R1, R4, R5 (R3 has no Board row, R2 has no pin); equal: R1 only
    "n_runs_board_both": 3, "n_pin_eq_board": 1, "share_pin_eq_board": 1 / 3,
    # band and pin: R1,R3,R4,R5; outside: R3, R4
    "n_runs_band_and_pin": 4, "n_pin_outside_band": 2,
    "share_pin_outside_band": 2 / 4, "n_runs_band_no_pin": 1,
    "tau_used": 0.3,
    "has_ref_run": True, "ref_ts_ist": "2026-11-25 14:30:00", "ref_spot": 25000.0,
    "pin_P": 25150.0, "board_B": 25000.0, "near_N": 25000.0, "p_eq_n": False,
    "close_1529": 25080.0, "close_read_at_ist": A_READ_AT,
    "dist_P_pts": 70.0, "dist_P_steps": 70 / 50,          # |25080-25150| = 70
    "dist_B_pts": 80.0, "dist_B_steps": 80 / 50,          # |25080-25000| = 80
    "dist_N_pts": 80.0, "dist_N_steps": 80 / 50,
    "abs_close_minus_ref_spot": 80.0, "strike_step": 50.0,
    "stop_flag": True, "stop_reason": "no rankable pin at 11:00:00",
}

# ============================================================== DAY B
# SENSEX 2026-11-26. Runs at 14:25 and 14:36 IST -- NOTHING in [14:30, 14:35).
# spot 80000 -> spot^2/1e7 = 640. Both runs identical:
#   79900 / 80100 gs 0.0001 oi 200 -> 0.0001*200*640 = 12.8
#   80000        gs 0.0002 oi 200 -> 0.0002*200*640 = 25.6  <- pin
#   lead = (25.6-12.8)/25.6 = 0.5 -> clear
#   band: step 100, peak 80000 (gex 5.0), thr 1.5; both neighbours gex 1.0 < 1.5
#         -> [80000, 80000] n 1. pin inside.
DB = date(2026, 11, 26)
EB = date(2026, 11, 27)
B_rows, B_board = [], []
for run, h, m in [("S1", 8, 55), ("S2", 9, 6)]:           # 14:25 and 14:36 IST
    for K, g, gx in [(79900, 0.0001, 1.0), (80000, 0.0002, 5.0), (80100, 0.0001, 1.0)]:
        B_rows.append(srow(run, U(DB, h, m), EB, 1, 80000, K, g, g, 100, 100, gx))
    B_board.append(brow(run, U(DB, h, m), EB, 80000))
B_bars = [{"bar_ts": U(DB, 9, 59), "close": 80050.0}]
B_READ_AT = "2026-11-26 16:33:00"

EXP_B = {
    "date": "2026-11-26", "symbol": "SENSEX",
    "expiry_date": None, "dte": None, "is_expiry_day": None,
    "n_runs_market": 2, "n_runs_rankable": 2, "share_rankable": 1.0,
    "median_n_ranked": 3, "median_share_one_leg": 0.0, "median_n_oi_no_gamma": 0,
    "n_clear_lead": 2, "share_clear_lead": 1.0, "n_lead_undefined": 0,
    "n_pin_changes": 0,
    "n_runs_board_both": 2, "n_pin_eq_board": 2, "share_pin_eq_board": 1.0,
    "n_runs_band_and_pin": 2, "n_pin_outside_band": 0,
    "share_pin_outside_band": 0.0, "n_runs_band_no_pin": 0,
    "tau_used": 0.3,
    # no reference run -> every Part 2 MEASURE blank. The close is still the
    # recorded read (DECISIONS.md clarification 7).
    "has_ref_run": False, "ref_ts_ist": None, "ref_spot": None,
    "pin_P": None, "board_B": None, "near_N": None, "p_eq_n": None,
    "close_1529": 80050.0, "close_read_at_ist": B_READ_AT,
    "dist_P_pts": None, "dist_P_steps": None, "dist_B_pts": None,
    "dist_B_steps": None, "dist_N_pts": None, "dist_N_steps": None,
    "abs_close_minus_ref_spot": None, "strike_step": 100.0,
    "stop_flag": False, "stop_reason": None,
}

# ============================================================== DAY C
# NIFTY 2026-11-27, EXPIRY DAY (dte 0), one market run at 14:30 IST, spot 25025.
# spot^2/1e7 = 25025^2/1e7 = 62.6250625
#   25000 gs 0.0004 oi 200 -> 0.0004*200*62.6250625 = 5.01000500  <- pin
#   25050 gs 0.0001 oi 200 -> 0.0001*200*62.6250625 = 1.25250125
#   lead = (5.010005 - 1.25250125)/5.010005 = 0.75 -> clear
#   N: |25000-25025| = |25050-25025| = 25 -> TIE -> lower -> 25000 = P, so P = N.
#   band: step 50, peak 25000 (gex 5.0), thr 1.5; 25050 gex 1.0 < 1.5
#         -> [25000, 25000] n 1. pin inside.
DC = date(2026, 11, 27)
EC = date(2026, 11, 27)
C_rows = [srow("C1", U(DC, 9, 0), EC, 0, 25025, 25000, 0.0004, 0.0004, 100, 100, 5.0),
          srow("C1", U(DC, 9, 0), EC, 0, 25025, 25050, 0.0001, 0.0001, 100, 100, 1.0)]
C_board = [brow("C1", U(DC, 9, 0), EC, 25050)]
C_bars = [{"bar_ts": U(DC, 9, 59), "close": 25010.0},
          {"bar_ts": U(DC, 9, 58), "close": 25100.0},
          {"bar_ts": U(DC, 15, 29), "close": 25600.0}]
C_READ_AT = "2026-11-27 16:31:00"

EXP_C = {
    "date": "2026-11-27", "symbol": "NIFTY",
    "expiry_date": "2026-11-27", "dte": 0, "is_expiry_day": True,
    "n_runs_market": 1, "n_runs_rankable": 1, "share_rankable": 1.0,
    "median_n_ranked": 2, "median_share_one_leg": 0.0, "median_n_oi_no_gamma": 0,
    "n_clear_lead": 1, "share_clear_lead": 1.0, "n_lead_undefined": 0,
    "n_pin_changes": 0,
    "n_runs_board_both": 1, "n_pin_eq_board": 0, "share_pin_eq_board": 0.0,
    "n_runs_band_and_pin": 1, "n_pin_outside_band": 0,
    "share_pin_outside_band": 0.0, "n_runs_band_no_pin": 0,
    "tau_used": 0.3,
    "has_ref_run": True, "ref_ts_ist": "2026-11-27 14:30:00", "ref_spot": 25025.0,
    "pin_P": 25000.0, "board_B": 25050.0, "near_N": 25000.0, "p_eq_n": True,
    "close_1529": 25010.0, "close_read_at_ist": C_READ_AT,
    "dist_P_pts": 10.0, "dist_P_steps": 10 / 50,          # |25010-25000|
    "dist_B_pts": 40.0, "dist_B_steps": 40 / 50,          # |25010-25050|
    "dist_N_pts": 10.0, "dist_N_steps": 10 / 50,
    "abs_close_minus_ref_spot": 15.0,                     # |25010-25025|
    "strike_step": 50.0, "stop_flag": False, "stop_reason": None,
}

DAYS = [
    ("A", DA, "NIFTY", A_rows, A_board, A_bars, A_READ_AT, 50.0, EXP_A),
    ("B", DB, "SENSEX", B_rows, B_board, B_bars, B_READ_AT, 100.0, EXP_B),
    ("C", DC, "NIFTY", C_rows, C_board, C_bars, C_READ_AT, 50.0, EXP_C),
]


def run_day(spec, **knobs):
    tag, day, sym, rows, bd, bars, read_at, step, _ = spec
    tau = knobs.pop("tau", 0.3)
    return measure_day(day, sym, rows, bd, bars, tau, step, read_at, **knobs)


# ================================================================== TIME
LOG.append("TIME -- the two storage conventions (condition 6)")
LOG.append("-" * 72)
chk("T1 gex ts 09:00:00+00 (true timestamptz) -> 14:30 IST",
    _run_ts_ist(U(DA, 9, 0)) == datetime(2026, 11, 25, 14, 30),
    str(_run_ts_ist(U(DA, 9, 0))))
chk("T2 bar_ts 09:59:00+00 (TRUE UTC, ruling R2) -> 15:29 IST",
    _bar_ts_ist(U(DA, 9, 59)) == datetime(2026, 11, 25, 15, 29),
    str(_bar_ts_ist(U(DA, 9, 59))))
chk("T3 the 15:29 IST close bar is labelled 09:59:00+00",
    close_bar_label_utc(DA) == U(DA, 9, 59), str(close_bar_label_utc(DA)))
# Negative control: the legacy IST-as-UTC handling (Rule 16) would read 09:59 as
# 09:59 IST. This asserts the two conventions are NOT interchangeable, so
# swapping the legacy rule back in fails here rather than silently shifting bars.
chk("T4 legacy replace(tzinfo=None) would give 09:59, not 15:29 -- conventions differ",
    U(DA, 9, 59).replace(tzinfo=None) != _bar_ts_ist(U(DA, 9, 59)),
    f"legacy {U(DA, 9, 59).replace(tzinfo=None)} vs utc->ist {_bar_ts_ist(U(DA, 9, 59))}")
for fn, nm in ((_run_ts_ist, "_run_ts_ist"), (_bar_ts_ist, "_bar_ts_ist")):
    try:
        fn(datetime(2026, 11, 25, 9, 0))
        chk(f"T5 {nm} refuses a naive datetime", False, "no error raised")
    except ValueError:
        chk(f"T5 {nm} refuses a naive datetime", True)
LOG.append("")

# ================================================================== BAND
# Hand-computed band walks (ruling R4). gex maps are {strike: gex_cr}.
LOG.append("BAND -- hand-computed walks against the live view's rule")
LOG.append("-" * 72)
b_r4 = _pin_band({23000: 5.0, 24900: 1.0, 24950: 2.0, 25000: 10.0,
                  25050: 4.0, 25100: -1.0, 25150: 2.0}, 25000.0, 0.3)
chk("B1 day A R4 band = [25000, 25050] n 2, peak 25000, step 50",
    b_r4 == {"lo": 25000.0, "hi": 25050.0, "n": 2, "peak": 25000.0,
             "step": 50.0, "tau": 0.3}, str(b_r4))
b_r3 = _pin_band({24950: 1.0, 25000: 9.0, 25050: 1.0}, 25000.0, 0.3)
chk("B2 day A R3 band = [25000, 25000] n 1 (thr 2.7 stops both neighbours)",
    (b_r3["lo"], b_r3["hi"], b_r3["n"]) == (25000.0, 25000.0, 1), str(b_r3))
b_r3t = _pin_band({24950: 1.0, 25000: 9.0, 25050: 1.0}, 25000.0, 0.1)
chk("B3 same run at tau 0.1 -> [24950, 25050] n 3 (thr 0.9 admits both)",
    (b_r3t["lo"], b_r3t["hi"], b_r3t["n"]) == (24950.0, 25050.0, 3), str(b_r3t))
b_r5 = _pin_band({25000: 4.0, 25100: 1.0}, 25000.0, 0.3)
chk("B4 a sparse run derives step 100 from its OWN strikes",
    b_r5["step"] == 100.0, str(b_r5))
chk("B5 one strike -> no strike_step row -> NO band",
    _pin_band({25000: 9.0}, 25000.0, 0.3) is None)
chk("B6 no strike with gex_cr > 0 -> empty peak -> NO band",
    _pin_band({25000: 0.0, 25050: -4.0}, 25000.0, 0.3) is None)
# A gap stops the walk even though the strike beyond it clears the threshold:
# step 50, peak 25000 (10.0), thr 3.0; 25050 (5.0) joins; 25100 absent -> stop,
# so 25150 (9.0) is never reached.
b_gap = _pin_band({25000: 10.0, 25050: 5.0, 25150: 9.0}, 25000.0, 0.3)
chk("B7 a gap stops the walk -- 25150 (9.0) unreached",
    (b_gap["lo"], b_gap["hi"], b_gap["n"], b_gap["step"]) == (25000.0, 25050.0, 2, 50.0),
    str(b_gap))
# peak tie on gex_cr: 24900 and 25100 both 8.0; |24900-25010| = 110 vs
# |25100-25010| = 90 -> nearer to spot wins -> peak 25100.
b_tie = _pin_band({24900: 8.0, 25000: 1.0, 25100: 8.0}, 25010.0, 0.3)
chk("B8 peak tie on gex_cr resolved by nearer to spot -> 25100",
    b_tie["peak"] == 25100.0, str(b_tie))
LOG.append("")

# ================================================= the three days, field by field
for spec in DAYS:
    tag, day, sym, _, _, _, _, _, exp = spec
    LOG.append(f"DAY {tag} -- {sym} {day} -- every field of the line")
    LOG.append("-" * 72)
    rec = run_day(spec)
    for c in COLUMNS:
        chk(f"{tag}.{c} = {exp[c]!r}", eq(rec[c], exp[c]), f"got {rec[c]!r}")
    LOG.append("")

# the formatted line for day A, asserted whole
LOG.append("LINE -- the formatted csv line (day A)")
LOG.append("-" * 72)
WANT_A = (
    "2026-11-25,NIFTY,2026-11-27,2,false,"
    "5,4,0.800000,3.0,0.000000,0.0,"
    "2,0.500000,1,3,"
    "3,1,0.333333,"
    "4,2,0.500000,1,0.3000,"
    "true,2026-11-25 14:30:00,25000.00,"
    "25150.00,25000.00,25000.00,false,"
    "25080.00,2026-11-25 16:35:00,"
    "70.00,1.4000,80.00,1.6000,80.00,1.6000,"
    "80.00,50.00,true,no rankable pin at 11:00:00"
)
got_a = format_line(run_day(DAYS[0]))
chk("L1 day A line is exactly the hand-written line", got_a == WANT_A,
    f"\n  got  {got_a}\n  want {WANT_A}")
chk("L2 header has one name per column, and the count is the 42 named in the "
    "design (date..stop_reason)", len(COLUMNS) == len(set(COLUMNS)) == 42,
    f"{len(COLUMNS)} columns")
chk("L3 the hand-written line has one field per column",
    len(WANT_A.split(",")) == len(COLUMNS),
    f"{len(WANT_A.split(','))} fields vs {len(COLUMNS)} columns")
LOG.append("")

# ================================================================ MUTANTS
LOG.append("MUTANTS -- each must make at least one check FAIL")
LOG.append("-" * 72)
MUTANTS = [
    ("a  reference window [14:35, 14:40)",
     {"ref_window": (time(14, 35), time(14, 40))}, ["A", "B"]),
    ("b  close taken from the 15:28 bar",
     {"close_bar_ist": time(15, 28)}, ["A", "C"]),
    ("c  nearest-to-spot tie resolved to the HIGHER strike",
     {"tie_higher": True}, ["C"]),
    ("d  distance taken to spot at reference, not to the close",
     {"dist_to": "ref_spot"}, ["A", "C"]),
    ("e  gross_cr > 0 condition dropped",
     {"require_positive_gross": False}, ["A"]),
    ("f  close label 15:29:00+00 instead of 09:59:00+00",
     {"force_close_label": datetime(2026, 11, 25, 15, 29, tzinfo=timezone.utc)}, ["A"]),
    ("g  tau 0.1 instead of the resolved 0.3",
     {"tau": 0.1}, ["A"]),
]
for name, knobs, tags in MUTANTS:
    broke = []
    for spec in DAYS:
        if spec[0] not in tags:
            continue
        exp = spec[8]
        try:
            rec = run_day(spec, **dict(knobs))
        except Exception as e:                       # a mutant that cannot even run
            broke.append(f"{spec[0]}:raised {type(e).__name__}")
            continue
        for c in COLUMNS:
            if not eq(rec[c], exp[c]):
                broke.append(f"{spec[0]}.{c} {exp[c]!r}->{rec[c]!r}")
    chk(f"M({name}) breaks at least one check", len(broke) >= 1,
        f"{len(broke)} broken: " + "; ".join(broke[:6]) +
        (" ..." if len(broke) > 6 else ""))
LOG.append("")

# ============================================================== GATE DETECTOR
# The EXPLAIN gate's PASS is only meaningful if its detector can fire.
LOG.append("GATE -- the EXPLAIN gate's own Seq Scan detector")
LOG.append("-" * 72)
from pin_monitor_day import seq_scan_offenders  # noqa: E402

OFFENDING = """ Sort  (cost=1..2 rows=1 width=1)
   ->  Seq Scan on gex_strike_snapshots  (cost=0.00..9.99 rows=1 width=1)
         Filter: (symbol = 'NIFTY'::text)"""
CLEAN = """ Index Scan using idx_gss_ts on gex_strike_snapshots  (cost=0.43..20.88 rows=1 width=1)
   InitPlan 1
     ->  Seq Scan on instruments  (cost=0.00..1.02 rows=1 width=16)"""
chk("G1 a Seq Scan on a guarded table IS flagged",
    len(seq_scan_offenders(OFFENDING)) == 1, str(seq_scan_offenders(OFFENDING)))
chk("G2 a Seq Scan on instruments beside an index scan is NOT flagged",
    seq_scan_offenders(CLEAN) == [], str(seq_scan_offenders(CLEAN)))
THREE = (" Seq Scan on option_chain_snapshots\n"
         " Seq Scan on hist_spot_bars_1m\n"
         " Seq Scan on gex_cycle_history")
chk("G3 all three are flagged -- gex_cycle_history included (ruling R5)",
    len(seq_scan_offenders(THREE)) == 3, str(seq_scan_offenders(THREE)))
LOG.append("")

# ======================================================= CROSS-CHECK vs indep
# The VS ranking must agree with the lane's existing independent recomputation,
# fix/order_check_rev3/indep.py, on the same legs and spot. indep.py is imported
# READ-ONLY and is neither copied nor edited; if the two disagree on any group,
# this fails and the build is not done.
LOG.append("CROSS -- _vs_rank against fix/order_check_rev3/indep.py measure()")
LOG.append("-" * 72)
INDEP_DIR = Path(__file__).resolve().parents[1] / "fix" / "order_check_rev3"
sys.path.insert(0, str(INDEP_DIR))
try:
    import indep                                          # noqa: E402
    chk("X0 indep.py imports read-only from fix/order_check_rev3", True,
        str(INDEP_DIR))
except Exception as e:                                    # noqa: BLE001
    indep = None
    chk("X0 indep.py imports read-only from fix/order_check_rev3", False,
        f"{type(e).__name__}: {e} -- the cross-check cannot run")

if indep is not None:
    from pin_monitor_lib import _vs_rank                  # noqa: E402

    def groups(rows):
        """Every (run_id, expiry_date) group of a fixture, front and next legs."""
        out = {}
        for r in rows:
            d = out.setdefault((r["run_id"], r["expiry_date"]),
                               {"spot": float(r["spot"]), "legs": {}})
            d["legs"][round(float(r["strike"]), 4)] = r
        return out

    n_groups = 0
    for tag, _, _, rows, _, _, _, _, _ in DAYS:
        for (run, exp), grp in sorted(groups(rows).items(), key=lambda kv: str(kv[0])):
            n_groups += 1
            spot = grp["spot"]
            mine = _vs_rank({K: {"gamma_call": r["gamma_call"],
                                 "gamma_put": r["gamma_put"],
                                 "oi_call": r["oi_call"], "oi_put": r["oi_put"]}
                             for K, r in grp["legs"].items()}, spot)
            theirs = indep.measure({K: {"c_gamma": r["gamma_call"],
                                        "p_gamma": r["gamma_put"],
                                        "c_oi": r["oi_call"], "p_oi": r["oi_put"]}
                                    for K, r in grp["legs"].items()}, spot)
            w = f"{tag}/{run}/{exp}"
            chk(f"X {w} sequence", mine["seq"] == theirs["sequence"],
                f"mine {mine['seq']} vs indep {theirs['sequence']}")
            for f_mine, f_theirs in (("n_in_set", "n_in_set"),
                                     ("n_ranked", "n_ranked"),
                                     ("n_oi_no_gamma", "n_oi_no_gamma"),
                                     ("lead_rel", "lead_rel")):
                chk(f"X {w} {f_mine}", eq(mine[f_mine], theirs[f_theirs]),
                    f"mine {mine[f_mine]!r} vs indep {theirs[f_theirs]!r}")
    chk("X* every fixture group was compared", n_groups == 11, f"{n_groups} groups")
LOG.append("")

LOG.append(f"SELF-TEST {'ALL PASS' if OK else 'FAILED'}  ({NP} pass, {NF} fail)")
sys.stdout.write("\n".join(LOG) + "\n")
raise SystemExit(0 if OK else 3)
