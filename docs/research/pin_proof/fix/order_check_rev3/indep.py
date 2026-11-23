#!/usr/bin/env python3
"""Independent recomputation for the rev-3 order check.

ALL measure arithmetic lives in measure() and nowhere else, so self_test.py can
call the same function the live comparison calls, and each mutation control can
alter exactly one named knob rather than re-implementing the measure.

Definitions are taken verbatim from PREREG.md "Design":
  gamma_strike  mean of the two leg gammas when both > 0; the one that is > 0; none
  gamma_legs    both / call_only / put_only / none
  gross_cr      gamma_strike x (oi_call + oi_put) x spot^2 / 1e7
  band          abs(strike/spot - 1) <= 0.05
  rank          gross_cr desc, then nearer to spot, then lower strike
  lead_rel      (top - second) / top
  n_oi_no_gamma in-set strikes with OI > 0 and no gamma on either leg

The three knobs (band, oi_filter, tiebreak) carry their PREREG values as
defaults. They exist for the mutation controls; the live run never passes them.
"""
from __future__ import annotations


def _present(g) -> bool:
    """A leg gamma counts as present only when it is a number strictly > 0.

    The vendor field is never absent (measured, fix/audit/decomp.md item 0) --
    it renders as the string "0.0" when blank -- so None and 0.0 must both read
    as 'no gamma on this leg' or call_only/put_only would never be reached.
    """
    return g is not None and g > 0.0


def measure(legs: dict, spot: float, *, band: float = 0.05,
            oi_filter: bool = True,
            tiebreak: str = "nearer_then_lower") -> dict:
    """legs: {strike: {"c_gamma","p_gamma","c_oi","p_oi"}}; gammas may be None.

    Returns the per-symbol-expiry record the comparison reads. Pure: no I/O, no
    globals, no mutation of `legs`.
    """
    if not (spot and spot > 0):
        raise ValueError("spot must be > 0")
    if tiebreak not in ("nearer_then_lower", "lower_then_nearer"):
        raise ValueError(f"unknown tiebreak {tiebreak!r}")

    scale = (spot * spot) / 1e7

    in_set, legs_map, gross = [], {}, {}
    n_oi_no_gamma = n_call_only = n_put_only = n_gamma_zero_oi = 0

    for K in sorted(legs):
        e = legs[K]
        if abs(K / spot - 1.0) > band:
            continue
        in_set.append(K)

        cg, pg = e.get("c_gamma"), e.get("p_gamma")
        c_ok, p_ok = _present(cg), _present(pg)
        oi_tot = (e.get("c_oi") or 0.0) + (e.get("p_oi") or 0.0)

        if c_ok and p_ok:
            gs, tag = (cg + pg) / 2.0, "both"
        elif c_ok:
            gs, tag = cg, "call_only"
            n_call_only += 1
        elif p_ok:
            gs, tag = pg, "put_only"
            n_put_only += 1
        else:
            gs, tag = None, "none"
            # KNOB 2: oi_filter. PREREG says OI > 0; dropping it is mutant M2.
            if (oi_tot > 0.0) or (not oi_filter):
                n_oi_no_gamma += 1

        legs_map[K] = tag
        if gs is not None:
            gv = gs * oi_tot * scale
            # RANKING CONDITION. Operator ruling 2026-11-23 20:00 IST, made
            # after the EXPLAIN gate and BEFORE any data read. Basis: the pin
            # lane's own revision-2 draft
            # 2026-11-21_pin_v_gex_strike_rank_gross_DRAFT.sql, WHERE
            # gross_cr > 0 -- which is where n_ranked was defined. A strike
            # carrying a gamma but zero total OI has gross_cr = 0 and is NOT
            # ranked, so n_ranked counts in-set strikes with gross_cr > 0.
            # This is a clarification of PREREG, not a relaxation: the PREREG
            # left the zero-gross case unstated and no rows had been seen.
            if gv > 0.0:
                gross[K] = gv
            else:
                n_gamma_zero_oi += 1

    # KNOB 3: tiebreak. PREREG order is gross desc, nearer to spot, lower strike.
    if tiebreak == "nearer_then_lower":
        key = lambda K: (-gross[K], abs(K - spot), K)
    else:                                    # mutant M1: the two swapped
        key = lambda K: (-gross[K], K, abs(K - spot))
    seq = sorted(gross, key=key)

    lead_rel = None
    if len(seq) >= 2 and gross[seq[0]] > 0.0:
        lead_rel = (gross[seq[0]] - gross[seq[1]]) / gross[seq[0]]

    return {
        "n_in_set": len(in_set),
        "n_ranked": len(seq),
        "n_oi_no_gamma": n_oi_no_gamma,
        "n_call_only": n_call_only,
        "n_put_only": n_put_only,
        # Reported, not judged. Non-zero means the ranking condition above was
        # actually exercised by this run rather than merely present in the code.
        "n_gamma_zero_oi": n_gamma_zero_oi,
        "sequence": seq,
        "legs_map": legs_map,
        "gross": gross,
        "lead_rel": lead_rel,
    }
