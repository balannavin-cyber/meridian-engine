"""Pin lane independent implementation of V2 per-strike exposure, rule v1.2.

Written from the rule text only (pre-registration
claude/pin/v2_rule_conformance_prereg_FROZEN_2026-11-25.md, section 3).
Standard library only. Not derived from merdian_compute/gamma_v2.py.

Interpretations where the rule text is silent (each is exercised by the
self-test, so a different reading in the engine's code shows as a mismatch):
  I1  A chain run with no row carrying spot > 0 is an error (S undefined).
  I2  Chain rows whose option_type is neither CE nor PE are ignored.
  I3  A stored-row run carrying more than one expiry is an error (rule scope:
      one map per symbol, expiry and run).
  I4  A missing or unparseable strike, or a strike <= 0, yields no output row.
  I5  From stored rows, a missing or non-positive oi_call / oi_put counts as 0.
  I6  Output rows are ordered by strike ascending; sums run in that order.
  I7  (v1.2, error e) ANY stored row of the run with a missing or non-positive
      spot makes the run an error, whatever its strike or open interest.
  I8  (v1.2, error d) "the same strike" is judged on the decimal value, so
      20000 and 20000.00 are one strike. Rows with a missing strike or a
      strike <= 0 are not strikes and are not counted as repeats.

Changes from the v1.1 implementation (sha256 fbf63b09...0fa783): build_from_gss
now raises on errors (d) and (e) instead of keeping the later row / skipping
the row. Nothing else changed.

The `_mut` argument exists only for the self-test's deliberately broken
versions. Production use leaves it None.
"""
from decimal import Decimal, InvalidOperation

GUARD_GAMMA = 5e-5
BAND = Decimal("0.05")
_NULLS = {"", "null", "none", "nan"}


class V2RunError(Exception):
    """The run has no V2 output under rule v1.1."""


def _dec(x):
    if x is None:
        return None
    if isinstance(x, Decimal):
        return x
    s = str(x).strip()
    if s.lower() in _NULLS:
        return None
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


def _flt(x):
    d = _dec(x)
    return None if d is None else float(d)


def _beyond(k_dec, s_dec, _mut=None):
    """True when |K - S| > 0.05 * S. Exact decimal (rule step 8)."""
    if _mut == "M10":
        k, s = float(k_dec), float(s_dec)
        return abs(k - s) > 0.05 * s
    if _mut == "M5":      # band strict: the edge counts as beyond for the band
        return abs(k_dec - s_dec) >= BAND * s_dec
    return abs(k_dec - s_dec) > BAND * s_dec


def _guard_distance(k_dec, s_dec, _mut=None):
    if _mut == "M6":      # guard acts on the edge too
        return abs(k_dec - s_dec) >= BAND * s_dec
    if _mut == "M10":
        k, s = float(k_dec), float(s_dec)
        return abs(k - s) > 0.05 * s
    return abs(k_dec - s_dec) > BAND * s_dec


def _strike_row(k_dec, s_dec, oi_c, oi_p, g_c, g_p, _mut=None):
    """Steps 3 to 7 for one strike. g_c / g_p are step-2 leg gammas or None."""
    s = float(s_dec)
    in_map = (g_c is not None) or (g_p is not None)          # step 6, before guard
    in_band = not _beyond(k_dec, s_dec, _mut)                 # step 7
    far = _guard_distance(k_dec, s_dec, _mut)

    def guarded(g):
        if g is None:
            return None
        return None if (far and g > GUARD_GAMMA) else g

    if _mut == "M1":      # guard after averaging
        if g_c is not None and g_p is not None:
            gs, legs = (g_c + g_p) / 2.0, "both"
        elif g_c is not None:
            gs, legs = g_c, "call_only"
        elif g_p is not None:
            gs, legs = g_p, "put_only"
        else:
            gs, legs = None, None
        if gs is not None and far and gs > GUARD_GAMMA:
            gs, legs = None, None
    else:
        a, b = guarded(g_c), guarded(g_p)                     # step 3
        if a is not None and b is not None:                   # step 4
            gs, legs = (a + b) / 2.0, "both"
        elif a is not None:
            gs, legs = a, "call_only"
            if _mut == "M2" and oi_p > 0:
                gs = a / 2.0
        elif b is not None:
            gs, legs = b, "put_only"
            if _mut == "M2" and oi_c > 0:
                gs = b / 2.0
        else:
            gs, legs = None, None
        if _mut == "M8":
            in_map = gs is not None

    c_oi, p_oi = oi_c, oi_p
    if _mut == "M11":     # OI on a no-gamma leg dropped
        if g_c is None:
            c_oi = 0.0
        if g_p is None:
            p_oi = 0.0

    if gs is None:
        net = 0.0
        gross = 0.0
    else:
        sign_p = 1.0 if _mut == "M3" else -1.0
        net = gs * (c_oi + sign_p * p_oi) * s * s / 1e7       # step 5
        gross = gs * (c_oi + p_oi) * s * s / 1e7              # step 7
    return {
        "strike": float(k_dec),
        "oi_call": oi_c,
        "oi_put": oi_p,
        "gamma_strike": gs,
        "gamma_legs": legs,
        "in_map": in_map,
        "in_band": in_band,
        "net_cr": net,
        "gross_cr": gross,
    }


def build_from_chain(option_rows_raw, _mut=None):
    """Rule v1.1 from raw chain rows of ONE run. Returns a list of per-strike dicts.

    Raises V2RunError when the run has no V2 output.
    """
    expiries = set()
    spots = set()
    for r in option_rows_raw:
        e = r.get("expiry_date")
        if e is not None and str(e).strip().lower() not in _NULLS:
            expiries.add(str(e).strip())
        sp = _dec(r.get("spot"))
        if sp is not None and sp > 0:
            spots.add(sp)
    if len(expiries) > 1:
        raise V2RunError("more than one expiry in the run")
    if len(spots) > 1:
        raise V2RunError("more than one distinct spot in the run")
    if not spots:
        raise V2RunError("no row with spot > 0")                # I1
    s_dec = next(iter(spots))

    legs = {}   # strike -> {"CE": [oi_sum, gamma or None], "PE": [...]}
    for r in option_rows_raw:
        k = _dec(r.get("strike"))
        if k is None or k <= 0:                                  # I4
            continue
        ot = str(r.get("option_type", "")).strip().upper()
        if ot not in ("CE", "PE"):                               # I2
            continue
        slot = legs.setdefault(k, {"CE": [0.0, None], "PE": [0.0, None]})[ot]
        oi = _flt(r.get("oi"))
        if oi is not None and oi > 0:                            # step 1
            slot[0] += oi
        g = _flt(r.get("gamma"))
        if _mut == "M4":
            if g is not None and g != 0 and (slot[1] is None or abs(g) > abs(slot[1])):
                slot[1] = g
        elif _mut == "M7":   # gammas summed across rows
            if g is not None and g > 0:
                slot[1] = g if slot[1] is None else slot[1] + g
        else:
            if g is not None and g > 0 and (slot[1] is None or g > slot[1]):   # step 2
                slot[1] = g

    out = []
    for k in sorted(legs):
        (oi_c, g_c), (oi_p, g_p) = legs[k]["CE"], legs[k]["PE"]
        if oi_c + oi_p <= 0:                                     # row set
            continue
        out.append(_strike_row(k, s_dec, oi_c, oi_p, g_c, g_p, _mut))
    return out


def build_from_gss(gss_rows, _mut=None):
    """Rule v1.1 from stored per-strike rows of ONE run."""
    expiries = set()
    for r in gss_rows:
        e = r.get("expiry_date")
        if e is not None and str(e).strip().lower() not in _NULLS:
            expiries.add(str(e).strip())
    if len(expiries) > 1:
        raise V2RunError("more than one expiry in the run")       # I3

    rows = {}
    for r in gss_rows:
        s_dec = _dec(r.get("spot"))
        if s_dec is None or s_dec <= 0:
            if _mut != "M13":
                raise V2RunError("stored row with a missing or non-positive spot")   # error (e), I7
            continue
        k = _dec(r.get("strike"))
        if k is None or k <= 0:
            continue
        if k in rows and _mut != "M12":
            raise V2RunError("stored rows repeat a strike")                          # error (d), I8
        oi_c = _flt(r.get("oi_call"))
        oi_p = _flt(r.get("oi_put"))
        oi_c = oi_c if (oi_c is not None and oi_c > 0) else 0.0   # I5
        oi_p = oi_p if (oi_p is not None and oi_p > 0) else 0.0
        if oi_c + oi_p <= 0:
            rows[k] = None                                        # seen, no output row
            continue
        g_c = _flt(r.get("gamma_call"))
        g_p = _flt(r.get("gamma_put"))
        if _mut == "M4":
            g_c = g_c if (g_c is not None and g_c != 0) else None
            g_p = g_p if (g_p is not None and g_p != 0) else None
        else:
            g_c = g_c if (g_c is not None and g_c > 0) else None
            g_p = g_p if (g_p is not None and g_p > 0) else None
        rows[k] = _strike_row(k, s_dec, oi_c, oi_p, g_c, g_p, _mut)
    return [rows[k] for k in sorted(rows) if rows[k] is not None]


def summarise(strike_rows, _mut=None):
    """Rule v1.1 step 9."""
    in_map = [r for r in strike_rows if r["in_map"]]
    net = 0.0
    abs_sum = 0.0
    max_abs = 0.0
    for r in in_map:
        net += r["net_cr"]
        abs_sum += abs(r["net_cr"])
        max_abs = max(max_abs, abs(r["net_cr"]))
    if _mut == "M9":
        band = [r for r in strike_rows if r["gross_cr"] > 0]
    else:
        band = [r for r in strike_rows if r["in_band"] and r["gross_cr"] > 0]
    gb = 0.0
    for r in band:
        gb += r["gross_cr"]
    if band:
        top = max(r["gross_cr"] for r in band) / gb
        hhi = 0.0
        for r in band:
            hhi += (r["gross_cr"] / gb) ** 2
    else:
        top, hhi = None, None
    return {
        "net_cr": net,
        "net_top_share": (max_abs / abs_sum) if abs_sum > 0 else None,
        "gross_band_cr": gb,
        "gross_top_share": top,
        "gross_hhi": hhi,
        "n_map": len(in_map),
        "n_zero": sum(1 for r in in_map if r["net_cr"] == 0.0),
    }


def count_duplicate_legs(option_rows_raw):
    """Number of (strike, leg) pairs carrying more than one chain row."""
    seen = {}
    for r in option_rows_raw:
        k = _dec(r.get("strike"))
        ot = str(r.get("option_type", "")).strip().upper()
        if k is None or k <= 0 or ot not in ("CE", "PE"):
            continue
        seen[(k, ot)] = seen.get((k, ot), 0) + 1
    return sum(1 for n in seen.values() if n > 1)
