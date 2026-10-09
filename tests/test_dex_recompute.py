#!/usr/bin/env python3
"""S93 / ENH-140 (P6) -- offline DEX recompute against a frozen golden day.

Recomputes the DEX standing book in Python from tests/golden/2026-10-01_SENSEX,
INDEPENDENTLY of sql/2026-10-09_s93_v_dex_standing_book.sql, and emits the
expected table that the view is later compared against.

    ( ulimit -v 700000; python3 tests/test_dex_recompute.py )

TWO MODES.

  (default)  Offline. Recompute from the frozen golden day, run A1-A9, and
             write the expected table.

  --compare --view <view.csv> --chain <chain.csv>
             VIEW CHECK 4i. Recompute from <chain.csv> and diff strike by
             strike against <view.csv>, which is the live view's own output.
             The recompute is this file's, so the comparison is between two
             independent implementations; the expected values are computed
             here and never read back off the view (S81). Both inputs are
             exported with bin/roq.sh, e.g.

               \\pset format csv
               SELECT symbol, expiry_date, strike, call_dex_cr, put_dex_cr,
                      net_dex_cr, run_id
                 FROM public.v_dex_standing_book ORDER BY symbol, expiry_date, strike;

               \\pset format csv
               SELECT symbol, expiry_date, strike, option_type, oi, delta, iv, spot, run_id
                 FROM public.option_chain_snapshots
                WHERE run_id IN (<the run_ids the view returned>);

             Export BOTH in one roq.sh invocation, or re-export together if a
             new run lands between them -- a latest-run-scoped view compared
             against a chain read taken at another moment is the S81
             false-alarm shape, and the run_id column is what detects it.

CLAUDE.md rule 23: NOT between 08:30 and 15:40 IST on a weekday, and never
without an explicit `ulimit -v`. The fixture is 31,914 chain rows over 81 cycles
(counts.csv) -- exactly the memory profile that rule exists for. The guard below
refuses rather than relying on the caller to remember.

=============================================================================
WHAT THIS FILE TESTS, AND WHAT IT DOES NOT
=============================================================================
It tests THIS PYTHON RECOMPUTE. It does not and cannot test the view: there is
no database offline. Saying so precisely matters, because an assertion that
passes here is not evidence about the SQL.

  * The SQL's scale and sign are tested by VIEW CHECK 4c (an independent
    in-SQL recompute with different algebra).
  * The SQL's agreement with THIS recompute, strike by strike, is VIEW CHECK
    4i -- the view against the CSV this file writes. That is where a doubled
    PE sign flip in the SQL would be caught.
  * The SQL's session-liveness clause reads market_spot_snapshots live and is
    tested by SECTION 4 against 2026-10-02 (distinct_spot = 1 on both
    symbols). A8 below exercises the same selector logic offline on the
    fixture's own copy of that relation, which is a test of the LOGIC, not of
    the deployed view.

Every assertion's expected value comes from outside this recompute (rule 0
clause 3: an expected value obtained by running the thing is not an assertion):

  A1  gex_cr rebuilt here == the fixture's STORED gex_cr, per strike, joined
      BY run_id, < 1e-6 Cr.
      Source: inputs/gex_strike.csv.gz, written by PRODUCTION. THE LOAD-BEARING
      CHECK -- DEX shares the /1e7 scaling, the oi convention and the CE/PE
      handling with GEX, so a scale or sign error in the harness surfaces here.
      Joined by run_id because that is the key §2(c) measured the two relations
      share; equal ts between them is not an established fact.
  A2  every positive oi is an exact multiple of the lot (SENSEX 20).
      Source: public.instruments.lot_size, and ADR-014 §2.3's S75 correction
      ("Dhan reports oi already lot-multiplied"). NOT from the fixture.
  A3  [RECOMPUTE] put_dex <= 0 and call_dex >= 0 wherever the side has OI and a
      live delta, and the negative case is non-vacuous.
      Source: the measured storage convention (PE delta is stored negative).
      Catches a doubled PE flip IN THIS FILE. The view's is 4i.
  A4  [RECOMPUTE] a side with OI and no delta is None, never 0.0, and the
      no-delta OI is fully accounted for.
      Source: the gap definition, cross-checked against an independent
      row-level count over the same run. Catches a COALESCE(.., 0) HERE.
  A6  no row has delta == 0 with iv > 0 and oi > 0 -- the gap marker's
      precondition. Source: measured over 55,228 rows of 2026-10-08.
      If this fires it is a REAL FINDING about the vendor, not a test bug.
  A7  the settled-run selector picks the last cycle at or before 15:15 IST and
      that cycle is one the fixture holds.
      Source: the ENH-126 river rule + the fixture's own ts list.
  A8  the SESSION SELECTOR's liveness clause, run over the fixture's own
      market_spot_snapshots rows -- the same relation the view reads. The live
      fixture day must be ACCEPTED and a synthetic copy with one frozen spot
      must be REJECTED, with row and cycle counts identical across the two.
      Source: the house liveness rule (ADR-030 / ENH-133 §3.6) and the measured
      2026-10-02 control. The synthetic copy is what makes it a test: the live
      fixture alone would pass a selector with no liveness clause at all.
      NOT TESTED HERE: clause 1 (explicit trading_calendar closure) -- the
      fixture carries no calendar rows, so clause 1 is live-only (Section 4).
  A9  the fixture's own dte, and whether it exercises S*'s dte-0 refusal.

  A5 WAS DELETED. It asserted sum(net) + one-sided-gap residue == leg_call +
  leg_put, which is an algebraic identity of the lines above it and so could
  not fail (rule 0 clause 1/3). No external expected value for the leg totals
  exists offline -- the fixture carries gamma, not delta -- so the leg-total
  property is tested by VIEW CHECK 4d (additivity, in SQL) and 4i (against this
  CSV), and the numbers are PRINTED here as observations, never asserted.

FIXTURE LIMITS, stated rather than discovered: the golden day carries W1 ONLY
(expiry_date is 2026-10-01 on every row) at dte 0, so it exercises one leg and
cannot exercise multi-leg ranking or the dte > 0 path.

OUTPUT. The expected table goes to docs/research/s93_priority/p6/expected/.
tests/golden/2026-10-01_SENSEX/ is FROZEN (R2.1, MANIFEST.sha256) and this file
never writes into it.

Exit 0 = all pass. Exit 1 = a real failure. Exit 2 = refused to run.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import resource
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "tests" / "golden" / "2026-10-01_SENSEX"
OUTDIR = REPO / "docs" / "research" / "s93_priority" / "p6" / "expected"
SYMBOL = "SENSEX"
LOT = 20                     # A2 source: public.instruments.lot_size (SENSEX)
IST = timezone(timedelta(hours=5, minutes=30))
CEIL_HHMM = 1515             # ENH-126 / v_gex_net_gamma_river: last run <= 15:15 IST
CR = 1e7                     # TD-NEW-3 crore convention, as signed_gamma_exposure
TOL_CR = 1e-6

failures: list[str] = []
notes: list[str] = []
observations: list[str] = []


def rule23_guard() -> None:
    """Refuse rather than trust the caller. Mirrors tests/run_offline.sh."""
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY:
        print("REFUSED: rule 23 -- run under ( ulimit -v 700000; ... )")
        sys.exit(2)
    now = datetime.now(IST)
    hhmm = now.hour * 100 + now.minute
    if now.isoweekday() <= 5 and 830 <= hhmm < 1540:
        print(f"REFUSED: rule 23 -- blocked 08:30-15:40 IST on weekdays "
              f"(now {now:%H:%M} IST)")
        sys.exit(2)


def check_manifest() -> None:
    """The fixture is frozen; a changed input invalidates every number below."""
    man = GOLDEN / "MANIFEST.sha256"
    bad, n = [], 0
    for line in man.read_text().splitlines():
        if not line.strip():
            continue
        want, rel = line.split(None, 1)
        p = GOLDEN / rel.strip().lstrip("./")
        if not p.exists():
            bad.append(f"missing {rel.strip()}")
            continue
        n += 1
        if hashlib.sha256(p.read_bytes()).hexdigest() != want:
            bad.append(f"sha mismatch {rel.strip()}")
    if bad:
        failures.append("FIXTURE: " + "; ".join(bad))
    else:
        notes.append(f"fixture MANIFEST.sha256 verified, {n} files")


def load_csv_gz(name: str) -> list[dict]:
    with gzip.open(GOLDEN / "inputs" / name, "rt", newline="") as fh:
        return list(csv.DictReader(fh))


def num(v):
    if v is None or v == "":
        return None
    return float(v)


def ist_hhmm(ts: str) -> int:
    d = datetime.fromisoformat(ts).astimezone(IST)
    return d.hour * 100 + d.minute


# ----------------------------------------------------------- session selector
def session_is_live(spot_rows: list[dict], session_date, symbol: str) -> int:
    """Clause 2 of the session selector, on market_spot_snapshots.

    Returns count(DISTINCT spot) for that symbol and date up to 15:15 IST --
    the house liveness rule (ADR-030 / ENH-133 §3.6). > 1 means a session.
    """
    seen = set()
    for r in spot_rows:
        if r["symbol"] != symbol:
            continue
        d = datetime.fromisoformat(r["ts"]).astimezone(IST)
        if d.date() != session_date or d.hour * 100 + d.minute > CEIL_HHMM:
            continue
        seen.add(r["spot"])
    return len(seen)


def pick_settled_ts(rows: list[dict]) -> str | None:
    """A7: last cycle at or before 15:15 IST. Ordered by ts, never created_at."""
    best = None
    for r in rows:
        if ist_hhmm(r["ts"]) <= CEIL_HHMM and (best is None or r["ts"] > best):
            best = r["ts"]
    return best


def recompute(rows: list[dict]) -> tuple[dict, dict]:
    """Per-strike DEX and GEX for one run. Returns (dex_by_strike, gex_by_strike).

    DEX: delta * oi * spot / 1e7. ONE power of spot, and NO PE sign flip --
    delta already carries its own sign. GEX is rebuilt alongside with the
    production formula (gamma * oi * spot^2 / 1e7, PE NEGATED, plus the
    TD-NEW-2 deep-ITM guard) purely so A1 can anchor the scale.
    """
    per: dict[float, dict] = {}
    for r in rows:
        k = num(r["strike"])
        ot = (r["option_type"] or "").upper()
        oi = num(r["oi"]) or 0.0
        delta = num(r["delta"])
        # gamma is only needed for the A1 GEX anchor. A 4i chain export does not
        # carry it; r.get keeps the DEX path usable without it, and A1 then fails
        # loudly as vacuous rather than passing on nothing.
        gamma = num(r.get("gamma")) or 0.0
        iv = num(r["iv"]) or 0.0
        spot = num(r["spot"]) or 0.0
        b = per.setdefault(k, {
            "strike": k, "spot": spot,
            "oi_call": 0.0, "oi_put": 0.0,
            "delta_call": None, "delta_put": None,
            "call_gap": False, "put_gap": False,
            "gex_cr": 0.0,
        })
        gap = (delta is None) or (delta == 0.0 and iv == 0.0)
        if ot == "CE":
            b["oi_call"] += oi
            b["delta_call"] = delta
            b["call_gap"] = gap
        elif ot == "PE":
            b["oi_put"] += oi
            b["delta_put"] = delta
            b["put_gap"] = gap

        # --- GEX rebuild, production formula verbatim (A1 anchor) ------------
        if gamma != 0.0 and oi > 0.0 and spot > 0.0:
            if not (k > 0 and abs(k - spot) / spot > 0.05 and abs(gamma) > 5e-5):
                base = gamma * oi * (spot ** 2) / CR
                b["gex_cr"] += -base if ot == "PE" else base

    out: dict[float, dict] = {}
    for k, b in per.items():
        spot = b["spot"]
        if b["oi_call"] == 0:
            call_dex = 0.0
        elif b["call_gap"]:
            call_dex = None
        else:
            call_dex = b["delta_call"] * b["oi_call"] * spot / CR
        if b["oi_put"] == 0:
            put_dex = 0.0
        elif b["put_gap"]:
            put_dex = None
        else:
            put_dex = b["delta_put"] * b["oi_put"] * spot / CR
        net = None if (call_dex is None or put_dex is None) else call_dex + put_dex
        out[k] = {
            **b,
            "call_dex_cr": call_dex,
            "put_dex_cr": put_dex,
            "net_dex_cr": net,
            "oi_call_no_delta": b["oi_call"] if b["call_gap"] else 0.0,
            "oi_put_no_delta": b["oi_put"] if b["put_gap"] else 0.0,
        }
    return out, {k: b["gex_cr"] for k, b in per.items()}


def load_csv(path: Path) -> list[dict]:
    with Path(path).open(newline="") as fh:
        return list(csv.DictReader(fh))


def compare_mode(view_path: str, chain_path: str) -> int:
    """VIEW CHECK 4i -- the live view against this file's independent recompute.

    Fails if any strike's call/put/net differs by more than 1e-6 Cr, if either
    side holds a strike the other does not, or if the two exports do not cover
    the same run_ids (a new run landed between them -- the S81 false alarm).
    """
    view = load_csv(Path(view_path))
    chain = load_csv(Path(chain_path))
    if not view:
        failures.append("4i: the view export is empty")
        return report()
    if not chain:
        failures.append("4i: the chain export is empty")
        return report()

    v_runs = {r["run_id"] for r in view if r.get("run_id")}
    c_runs = {r["run_id"] for r in chain if r.get("run_id")}
    if v_runs != c_runs:
        failures.append(f"4i: the two exports cover different runs -- view {sorted(v_runs)} "
                        f"vs chain {sorted(c_runs)}. A new run landed between the reads; "
                        f"re-export both together (S81 false-alarm shape)")
        return report()
    notes.append(f"4i run_ids match across both exports: {len(v_runs)} run(s)")

    # recompute per (symbol, expiry_date) from the chain alone
    by_leg: dict[tuple, list[dict]] = {}
    for r in chain:
        by_leg.setdefault((r["symbol"], r["expiry_date"]), []).append(r)
    recomputed: dict[tuple, dict] = {}
    for leg, rows in by_leg.items():
        dex, _ = recompute(rows)
        for k, d in dex.items():
            recomputed[(leg[0], leg[1], k)] = d

    seen, worst, worst_at, n_cmp = set(), 0.0, None, 0
    for r in view:
        key = (r["symbol"], r["expiry_date"], float(r["strike"]))
        seen.add(key)
        got = recomputed.get(key)
        if got is None:
            failures.append(f"4i: the view holds {key} and the recompute does not")
            continue
        n_cmp += 1
        for col, mine in (("call_dex_cr", got["call_dex_cr"]),
                          ("put_dex_cr", got["put_dex_cr"]),
                          ("net_dex_cr", got["net_dex_cr"])):
            theirs = r.get(col, "")
            if (theirs == "" or theirs is None) != (mine is None):
                failures.append(f"4i: {key} {col} NULL-ness differs -- view "
                                f"{theirs!r}, recompute {mine!r}")
                continue
            if mine is None:
                continue
            d = abs(float(theirs) - mine)
            if d > worst:
                worst, worst_at = d, (key, col)
            if d > TOL_CR:
                failures.append(f"4i: {key} {col} differs by {d:.3e} Cr "
                                f"(view {float(theirs):.6f}, recompute {mine:.6f})")
    missing = set(recomputed) - seen
    if missing:
        failures.append(f"4i: the recompute holds {len(missing)} strikes the view does not "
                        f"(e.g. {sorted(missing)[:3]})")
    if n_cmp == 0:
        failures.append("4i: nothing was compared -- vacuous")
    elif not failures:
        where = "" if worst_at is None else f" at {worst_at[0]} {worst_at[1]}"
        notes.append(f"4i view matches the independent recompute on {n_cmp} strikes, "
                     f"max abs diff {worst:.3e} Cr{where}")
    return report()


def main() -> int:
    argv = sys.argv[1:]
    if "--compare" in argv:
        def opt(name: str) -> str:
            if name not in argv:
                print(f"REFUSED: --compare needs {name} <path>")
                sys.exit(2)
            return argv[argv.index(name) + 1]
        # no rule 23 guard: --compare reads two small CSVs, loads no golden day
        return compare_mode(opt("--view"), opt("--chain"))

    rule23_guard()
    if not GOLDEN.exists():
        print(f"REFUSED: fixture not found at {GOLDEN}")
        return 2
    check_manifest()

    ocs = load_csv_gz("ocs.csv.gz")
    gss = load_csv_gz("gex_strike.csv.gz")
    spot_rows = load_csv_gz("spot.csv.gz")
    notes.append(f"loaded {len(ocs)} chain rows, {len(gss)} gex_strike rows, "
                 f"{len(spot_rows)} market_spot_snapshots rows")

    # ---- A7: the settled run -----------------------------------------------
    settled_ts = pick_settled_ts(ocs)
    all_ts = sorted({r["ts"] for r in ocs})
    if settled_ts is None:
        failures.append("A7: no cycle at or before 15:15 IST")
        return report()
    if settled_ts not in all_ts:
        failures.append("A7: settled ts is not a cycle the fixture holds")
    else:
        later_eligible = [t for t in all_ts if t > settled_ts and ist_hhmm(t) <= CEIL_HHMM]
        if later_eligible:
            failures.append(f"A7: {len(later_eligible)} later cycles also sit at or before "
                            f"15:15 -- the selector did not pick the last")
        else:
            d = datetime.fromisoformat(settled_ts).astimezone(IST)
            n_after = len([t for t in all_ts if t > settled_ts])
            notes.append(f"A7 settled ts {d:%Y-%m-%d %H:%M:%S} IST; "
                         f"{n_after} later cycles correctly excluded (all after 15:15)")

    run = [r for r in ocs if r["ts"] == settled_ts]
    run_ids = {r["run_id"] for r in run}
    if len(run_ids) != 1:
        failures.append(f"A7: the settled cycle carries {len(run_ids)} run_ids; "
                        f"expected exactly one (one leg)")
    run_id = next(iter(run_ids))
    dex, gex = recompute(run)

    # ---- A1: GEX rebuild vs the fixture's STORED gex_cr, joined BY run_id ---
    stored = {num(r["strike"]): num(r["gex_cr"]) for r in gss if r["run_id"] == run_id}
    if not stored:
        failures.append(f"A1: fixture gex_strike holds no rows for run_id {run_id}")
    else:
        worst, worst_k, n_cmp, missing = 0.0, None, 0, 0
        for k, want in stored.items():
            got = gex.get(k)
            if got is None:
                missing += 1
                continue
            n_cmp += 1
            d = abs(got - (want or 0.0))
            if d > worst:
                worst, worst_k = d, k
        if missing:
            failures.append(f"A1: {missing} strikes in gex_strike are absent from the chain "
                            f"for the same run_id")
        if worst > TOL_CR:
            failures.append(f"A1: gex_cr rebuild differs by {worst:.3e} Cr at strike "
                            f"{worst_k} (tolerance {TOL_CR:.0e}) -- the /1e7 scaling, the oi "
                            f"convention or the CE/PE handling is wrong, and DEX shares all "
                            f"three")
        elif n_cmp == 0:
            failures.append("A1: nothing was compared -- the assertion is vacuous")
        else:
            notes.append(f"A1 gex_cr rebuild matches production on {n_cmp} strikes "
                         f"(run_id {run_id[:8]}), max abs diff {worst:.3e} Cr")

    # ---- A2: oi is a quantity, an exact multiple of the lot ----------------
    bad = [(num(r["strike"]), r["option_type"], num(r["oi"]))
           for r in run if (num(r["oi"]) or 0) > 0 and (num(r["oi"]) or 0) % LOT != 0]
    n_pos = sum(1 for r in run if (num(r["oi"]) or 0) > 0)
    if bad:
        failures.append(f"A2: {len(bad)} positive-oi rows are not multiples of the SENSEX "
                        f"lot {LOT} (e.g. {bad[:3]}) -- if the vendor switched to contract "
                        f"counts, every Rs figure is out by {LOT}x")
    elif n_pos == 0:
        failures.append("A2: no positive-oi rows -- the assertion is vacuous")
    else:
        notes.append(f"A2 all {n_pos} positive-oi rows are exact multiples of {LOT}")

    # ---- A3 [RECOMPUTE]: the sign, i.e. the doubled-flip check -------------
    n_put_pos = sum(1 for d in dex.values()
                    if d["put_dex_cr"] is not None and d["put_dex_cr"] > 0)
    n_call_neg = sum(1 for d in dex.values()
                     if d["call_dex_cr"] is not None and d["call_dex_cr"] < 0)
    n_put_neg = sum(1 for d in dex.values()
                    if d["put_dex_cr"] is not None and d["put_dex_cr"] < 0)
    if n_put_pos or n_call_neg:
        failures.append(f"A3 [recompute]: {n_put_pos} strikes have put_dex > 0 and "
                        f"{n_call_neg} have call_dex < 0. If put_dex > 0 on every put "
                        f"strike, the GEX PE sign flip was copied and the negation is doubled")
    elif n_put_neg == 0:
        failures.append("A3 [recompute]: no strike has put_dex < 0 -- vacuous, so it is not "
                        "testing the sign")
    else:
        notes.append(f"A3 [recompute] sign holds: {n_put_neg} strikes with put_dex < 0, "
                     f"0 positive; 0 call_dex < 0. (The VIEW's sign is 4c/4i.)")

    # ---- A4 [RECOMPUTE]: NULL is a gap, never a zero -----------------------
    viol, gap_oi = 0, 0.0
    for d in dex.values():
        if d["call_gap"] and d["oi_call"] > 0 and d["call_dex_cr"] == 0.0:
            viol += 1
        if d["put_gap"] and d["oi_put"] > 0 and d["put_dex_cr"] == 0.0:
            viol += 1
        gap_oi += d["oi_call_no_delta"] + d["oi_put_no_delta"]
    # independent row-level count over the same run -- not derived from `dex`
    expect_gap_oi = sum((num(r["oi"]) or 0.0) for r in run
                        if (num(r["oi"]) or 0) > 0
                        and (num(r["delta"]) is None
                             or (num(r["delta"]) == 0.0 and (num(r["iv"]) or 0.0) == 0.0)))
    n_gap = sum(1 for d in dex.values()
                if d["call_dex_cr"] is None or d["put_dex_cr"] is None)
    if viol:
        failures.append(f"A4 [recompute]: {viol} gap sides published 0.0 instead of None")
    elif abs(gap_oi - expect_gap_oi) > 0.5:
        failures.append(f"A4 [recompute]: no-delta OI accounting is off: pivot-side "
                        f"{gap_oi:.0f} vs row-side {expect_gap_oi:.0f}")
    elif n_gap == 0:
        failures.append("A4 [recompute]: no gap strikes in the fixture -- vacuous, so it is "
                        "not testing the gap path")
    else:
        notes.append(f"A4 [recompute] gaps are None not 0.0; {n_gap} gap strikes, "
                     f"{gap_oi:.0f} units of un-deltaed OI, matching an independent "
                     f"row-level count. (The VIEW's is 4d.)")

    # ---- A6: the gap marker's precondition ---------------------------------
    odd = [(num(r["strike"]), r["option_type"], num(r["iv"]))
           for r in run
           if (num(r["oi"]) or 0) > 0 and num(r["delta"]) == 0.0
           and (num(r["iv"]) or 0.0) > 0]
    if odd:
        failures.append(f"A6: {len(odd)} rows carry delta = 0 beside a LIVE iv "
                        f"(e.g. {odd[:3]}). This is a REAL FINDING, not a test bug: the "
                        f"marker 'delta = 0 AND iv = 0' no longer separates a gap from a "
                        f"true zero")
    else:
        notes.append("A6 no row has delta = 0 with iv > 0; the gap marker still separates "
                     "an absent greek from a true zero")

    # ---- A8: the session selector's liveness clause, on the real relation --
    sess_date = datetime.fromisoformat(settled_ts).astimezone(IST).date()
    live_n = session_is_live(spot_rows, sess_date, SYMBOL)
    frozen_rows = [dict(r, spot="72143.8") for r in spot_rows]
    frozen_n = session_is_live(frozen_rows, sess_date, SYMBOL)
    n_live_in_window = sum(
        1 for r in spot_rows
        if r["symbol"] == SYMBOL
        and datetime.fromisoformat(r["ts"]).astimezone(IST).date() == sess_date
        and ist_hhmm(r["ts"]) <= CEIL_HHMM)
    if live_n <= 1:
        failures.append(f"A8: the fixture day reads distinct_spot = {live_n} on "
                        f"market_spot_snapshots and would be REJECTED as frozen -- the "
                        f"golden day is supposed to be a live session")
    elif frozen_n != 1:
        failures.append(f"A8: the synthetic frozen copy reads distinct_spot = {frozen_n}, "
                        f"so it does not exercise the liveness clause")
    else:
        notes.append(f"A8 liveness clause separates them on the SAME relation the view "
                     f"reads: live fixture distinct_spot = {live_n} (accepted), synthetic "
                     f"frozen copy = 1 (rejected), both over an identical {n_live_in_window} "
                     f"rows in the window. Clause 1 (explicit calendar closure) is NOT "
                     f"tested here -- the fixture carries no trading_calendar rows, so it "
                     f"is live-only, Section 4 vs 2026-10-02")

    # ---- A9: the fixture's dte --------------------------------------------
    exp = {r["expiry_date"] for r in run}
    if len(exp) != 1:
        failures.append(f"A9: the settled cycle carries {len(exp)} expiries; expected W1 only")
    else:
        exp_date = datetime.strptime(next(iter(exp)), "%Y-%m-%d").date()
        dte = (exp_date - sess_date).days
        if dte == 0:
            notes.append("A9 fixture dte = 0, so S*'s evalset would refuse this run "
                         "(SKIPPED_EXPIRY, never floored -- S62). The dte > 0 path is NOT "
                         "exercised by this fixture")
        else:
            notes.append(f"A9 fixture dte = {dte}; the dte-0 refusal path is NOT exercised")

    # ---- observations, printed and NOT asserted (see the A5 note) ----------
    leg_call = sum(d["call_dex_cr"] or 0.0 for d in dex.values())
    leg_put = sum(d["put_dex_cr"] or 0.0 for d in dex.values())
    sum_net = sum(d["net_dex_cr"] for d in dex.values() if d["net_dex_cr"] is not None)
    observations.append(f"leg totals: call {leg_call:.2f} put {leg_put:.2f} "
                        f"net {leg_call + leg_put:.2f} Cr over {len(dex)} strikes")
    observations.append(f"sum(net_dex_cr) {sum_net:.2f} Cr differs from the leg total by "
                        f"{(leg_call + leg_put) - sum_net:.2f} Cr -- the one-sided-gap "
                        f"residue. NOT asserted here (no external expected value exists "
                        f"offline); asserted by view checks 4d and 4i")

    # ---- emit the expected table for view check 4i ------------------------
    OUTDIR.mkdir(parents=True, exist_ok=True)
    outp = OUTDIR / "dex_standing_book_1001_SENSEX.csv"
    with outp.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "session_date", "expiry_date", "run_id", "settled_ts",
                    "spot", "strike", "delta_call", "delta_put", "oi_call", "oi_put",
                    "call_dex_cr", "put_dex_cr", "net_dex_cr",
                    "oi_call_no_delta", "oi_put_no_delta"])
        for k in sorted(dex):
            d = dex[k]
            w.writerow([SYMBOL, sess_date, next(iter(exp)), run_id, settled_ts,
                        f"{d['spot']:.2f}", f"{k:.1f}",
                        "" if d["delta_call"] is None else f"{d['delta_call']:.5f}",
                        "" if d["delta_put"] is None else f"{d['delta_put']:.5f}",
                        f"{d['oi_call']:.0f}", f"{d['oi_put']:.0f}",
                        "" if d["call_dex_cr"] is None else f"{d['call_dex_cr']:.10f}",
                        "" if d["put_dex_cr"] is None else f"{d['put_dex_cr']:.10f}",
                        "" if d["net_dex_cr"] is None else f"{d['net_dex_cr']:.10f}",
                        f"{d['oi_call_no_delta']:.0f}", f"{d['oi_put_no_delta']:.0f}"])
    notes.append(f"wrote {outp.relative_to(REPO)} ({len(dex)} strikes) for view check 4i")
    return report()


def report() -> int:
    for n in notes:
        print(f"  ok   {n}")
    for o in observations:
        print(f"  obs  {o}")
    for f in failures:
        print(f"  FAIL {f}")
    print(f"DEX_RECOMPUTE {'PASS' if not failures else 'FAIL'} "
          f"({len(notes)} ok, {len(observations)} observed, {len(failures)} failed)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
