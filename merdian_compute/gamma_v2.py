"""merdian_compute.gamma_v2 -- V2 per-strike exposure, rule v1.1 (ADR-033, scope D).

Stdlib only. Pure: reads no environment, opens no client, touches no network.
Imports nothing from merdian_compute.gamma; V1 is not edited and not called.
Not exported from merdian_compute/__init__.py and not part of the Retail contract.

Rule v1.1 in one paragraph (the ADR text is the authority): one map per symbol,
expiry and run. Per leg: OI = sum of positive oi; gamma = largest vendor gamma > 0.
Guard per leg before averaging: |K - S| > 0.05*S and gamma > 5e-5 -> no gamma.
gamma_strike = mean of both, or the one, or none. net = gamma_strike*(OIc-OIp)*S^2/1e7,
gross = gamma_strike*(OIc+OIp)*S^2/1e7 (Crore; 0 when gamma_strike is none).
in_map = a leg has gamma before the guard. in_band = |K - S| <= 0.05*S. The two
distance tests are exact decimal arithmetic. Run figures: net over the map,
gross figures over the band set (in_band and gross > 0).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

RULE_VERSION = "v2-1.1"
RULE_VERSION_GSS = "v2-1.1-gss"

GUARD_DISTANCE = Decimal("0.05")   # of spot; guard acts strictly beyond, band is at or inside
GUARD_GAMMA = 5e-5
CR_DIVISOR = 1e7


class V2InputError(RuntimeError):
    """The run has no V2 output (more than one expiry, more than one spot, bad spot)."""


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pos(value: Any) -> float | None:
    """A vendor gamma counts only when it is > 0 (zero, missing and negative are 'no gamma')."""
    g = _f(value)
    return g if g is not None and g > 0 else None


def _d(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def _beyond_guard(strike: Decimal, spot: Decimal) -> bool:
    return abs(strike - spot) > GUARD_DISTANCE * spot


def _in_band(strike: Decimal, spot: Decimal) -> bool:
    return abs(strike - spot) <= GUARD_DISTANCE * spot


def strike_gamma_v2(gamma_call: Any, gamma_put: Any, strike: Any, spot: Any) -> tuple[float | None, str | None]:
    """Steps 2 (positivity), 3 and 4 for one strike. Returns (gamma_strike, gamma_legs)."""
    k, s = _d(strike), _d(spot)
    if k is None or s is None or s <= 0:
        raise V2InputError(f"bad strike/spot: {strike!r} / {spot!r}")
    gc, gp = _pos(gamma_call), _pos(gamma_put)
    if _beyond_guard(k, s):
        if gc is not None and gc > GUARD_GAMMA:
            gc = None
        if gp is not None and gp > GUARD_GAMMA:
            gp = None
    if gc is not None and gp is not None:
        return (gc + gp) / 2.0, "both"
    if gc is not None:
        return gc, "call_only"
    if gp is not None:
        return gp, "put_only"
    return None, None


def _strike_row(strike_raw: Any, spot_raw: Any, oi_call: float, oi_put: float,
                gamma_call: float | None, gamma_put: float | None) -> dict[str, Any] | None:
    """One output row from leg-level values (gammas already 'largest > 0 or None')."""
    if oi_call + oi_put <= 0:
        return None
    k, s = _d(strike_raw), _d(spot_raw)
    gamma_strike, legs = strike_gamma_v2(gamma_call, gamma_put, strike_raw, spot_raw)
    in_map = _pos(gamma_call) is not None or _pos(gamma_put) is not None
    s_f = float(s)
    if gamma_strike is None:
        net = 0.0
        gross = 0.0
    else:
        net = gamma_strike * (oi_call - oi_put) * s_f * s_f / CR_DIVISOR
        gross = gamma_strike * (oi_call + oi_put) * s_f * s_f / CR_DIVISOR
    return {
        "strike": float(k),
        "oi_call": oi_call,
        "oi_put": oi_put,
        "gamma_strike": gamma_strike,
        "gamma_legs": legs,
        "in_map": bool(in_map),
        "in_band": _in_band(k, s),
        "net_cr": net,
        "gross_cr": gross,
    }


def _single_expiry(rows: list[dict[str, Any]]) -> None:
    expiries = {str(r.get("expiry_date")) for r in rows if r.get("expiry_date")}
    if len(expiries) > 1:
        raise V2InputError(f"rows carry {len(expiries)} expiries {sorted(expiries)}")


def build_v2_strike_rows(option_rows_raw: list[dict[str, Any]], spot: Any) -> list[dict[str, Any]]:
    """Chain rows (one per leg, RAW, not the usable-filtered rows) -> per-strike V2 rows."""
    s = _d(spot)
    if s is None or s <= 0:
        raise V2InputError(f"bad spot: {spot!r}")
    _single_expiry(option_rows_raw)
    row_spots = {d for d in (_d(r.get("spot")) for r in option_rows_raw) if d is not None and d > 0}
    if len(row_spots) > 1:
        raise V2InputError(f"rows carry {len(row_spots)} distinct spot values")
    if row_spots and next(iter(row_spots)) != s:
        raise V2InputError("spot argument differs from the rows' spot")

    acc: dict[Decimal, dict[str, Any]] = {}
    for r in option_rows_raw:
        k = _d(r.get("strike"))
        if k is None or k <= 0:
            continue
        leg = str(r.get("option_type", "")).upper()
        if leg not in ("CE", "PE"):
            continue
        b = acc.setdefault(k, {"raw": r.get("strike"), "oi": {"CE": 0.0, "PE": 0.0}, "g": {"CE": None, "PE": None}})
        oi = _f(r.get("oi"))
        if oi is not None and oi > 0:
            b["oi"][leg] += oi
        g = _pos(r.get("gamma"))
        if g is not None and (b["g"][leg] is None or g > b["g"][leg]):
            b["g"][leg] = g

    out: list[dict[str, Any]] = []
    for k in sorted(acc):
        b = acc[k]
        row = _strike_row(k, s, b["oi"]["CE"], b["oi"]["PE"], b["g"]["CE"], b["g"]["PE"])
        if row is not None:
            out.append(row)
    return out


def build_v2_strike_rows_from_gss(gss_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stored gex_strike_snapshots rows of ONE run -> per-strike V2 rows (each row's own spot)."""
    _single_expiry(gss_rows)
    seen: set[Decimal] = set()
    out: list[tuple[Decimal, dict[str, Any]]] = []
    for r in gss_rows:
        k = _d(r.get("strike"))
        if k is None or k <= 0:
            continue
        if k in seen:
            raise V2InputError(f"stored rows repeat strike {k}")
        seen.add(k)
        s = _d(r.get("spot"))
        if s is None or s <= 0:
            raise V2InputError(f"stored row has bad spot at strike {k}")
        oc, op = _f(r.get("oi_call")), _f(r.get("oi_put"))
        oc = oc if oc is not None and oc > 0 else 0.0
        op = op if op is not None and op > 0 else 0.0
        row = _strike_row(k, s, oc, op, _pos(r.get("gamma_call")), _pos(r.get("gamma_put")))
        if row is not None:
            out.append((k, row))
    return [row for _, row in sorted(out, key=lambda kv: kv[0])]


def summarise_v2_run(strike_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Step 9 run figures from per-strike V2 rows."""
    in_map = [r for r in strike_rows if r["in_map"]]
    net_cr = sum(r["net_cr"] for r in in_map) if in_map else 0.0
    abs_sum = sum(abs(r["net_cr"]) for r in in_map)
    net_top_share = (max(abs(r["net_cr"]) for r in in_map) / abs_sum) if abs_sum > 0 else None
    band = [r for r in strike_rows if r["in_band"] and r["gross_cr"] > 0]
    if band:
        gross_band_cr = sum(r["gross_cr"] for r in band)
        gross_top_share = max(r["gross_cr"] for r in band) / gross_band_cr
        gross_hhi = sum((r["gross_cr"] / gross_band_cr) ** 2 for r in band)
    else:
        gross_band_cr, gross_top_share, gross_hhi = 0.0, None, None
    return {
        "net_cr": net_cr,
        "net_top_share": net_top_share,
        "gross_band_cr": gross_band_cr,
        "gross_top_share": gross_top_share,
        "gross_hhi": gross_hhi,
        "n_map": len(in_map),
        "n_zero": sum(1 for r in in_map if r["net_cr"] == 0.0),
    }


def count_duplicate_legs(option_rows_raw: list[dict[str, Any]]) -> int:
    """Number of (strike, leg) pairs that have more than one chain row."""
    counts: dict[tuple[Decimal, str], int] = {}
    for r in option_rows_raw:
        k = _d(r.get("strike"))
        leg = str(r.get("option_type", "")).upper()
        if k is None or k <= 0 or leg not in ("CE", "PE"):
            continue
        counts[(k, leg)] = counts.get((k, leg), 0) + 1
    return sum(1 for n in counts.values() if n > 1)
