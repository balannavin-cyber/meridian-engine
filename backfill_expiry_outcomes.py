#!/usr/bin/env python3
"""
backfill_expiry_outcomes.py  —  ENH-116 build-sequence step 3 (Measure artifact)

Seeds public.expiry_outcomes retroactively from the S62/S63 backfilled history:
one labeled row per weekly/monthly expiry per symbol, capturing (a) the ambient
state going IN (as of expiry morning) and (b) the OUTCOME (pinned / broke, magnitude).
Stores; does not predict. Base rates (Phase B) come later, as a query over this store.

One-shot, resumable, operator-invoked (like backfill_participant_oi.py) — NOT cron'd,
so no ExecutionLog. `--dry-run` prints; `--force` re-labels existing rows.

AUTHORITATIVE SOURCES (no fragile DOW rule):
  * expiry enumeration : hist_atm_option_bars_5m.expiry_date (distinct). NOTE: this is
      a PARTIAL ATM backfill (~72% coverage) so it UNDER-enumerates weeklies; full
      coverage needs a distinct-expiry RPC over hist_option_bars_1m (S35
      get_hocs_distinct_expiries precedent). Tracked as a coverage follow-up.
  * settlement + intraday range + open : hist_spot_bars_5m (OHLC; bar_ts IST-as-+00:00).
  * regime / concentration / flip      : hist_gamma_metrics (bar_ts IST-as-UTC :59).

MODELING CALLS (override via flags / edit; documented so they aren't silent):
  [M1] open_pin_strike  = ATM at open = opening spot rounded to the strike step
       (NIFTY 50 / SENSEX 100). Reproduces hist_atm_option_bars_5m.atm_strike without
       depending on that partial ATM table (which rolls to next contract at expiry
       open); open_flip_level (hist_gamma_metrics.flip_level) is stored alongside as
       the structural anchor.
  [M2] resolved: |settlement_vs_open_pin_pct| < --pin-threshold-pct (default 0.25)
       -> PINNED; else BROKE_UP / BROKE_DOWN by sign.
  [M3] accel_zone_triggered -> NULL (no historical accel-zone bounds in the aggregate
       hist series); open_pin_risk_score -> NULL (live-only S41 column).
  [M4] ambient-going-in breadth/participant/macro -> NULL for the historical window
       (breadth chain is sparse/unstable pre-S57; ENH-115 participant starts 2025-05-28
       with schema not yet wired). gex persistence + concentration + regime ARE filled.

All bar_ts across the three hist tables carry the IST clock with a +00:00 label, so an
IST calendar day E is selected with gte '{E}T00:00:00+00:00' / lt '{E+1}...'.
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta, date

import requests
from dotenv import load_dotenv

load_dotenv()

UTC = timezone.utc
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
REST = f"{SUPABASE_URL}/rest/v1"
HEADERS = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}",
           "Content-Type": "application/json"}
PAGE = 1000

SYMBOLS = ["NIFTY", "SENSEX"]
SOURCE = "expiry_memory_s62"      # matches the DDL default; bump to _s64 to taste
STEP = {"NIFTY": 50, "SENSEX": 100}   # strike step -> ATM pin from opening spot ([M1])


def log(msg):
    print(f"[{datetime.now(UTC).isoformat()}] {msg}", flush=True)


# ---------------------------------------------------------------- PostgREST I/O
def _get(path, params, paginate=True):
    """params is a LIST OF TUPLES (never a dict — dup keys drop silently; S63)."""
    if not paginate:
        r = requests.get(f"{REST}/{path}", headers=HEADERS, params=list(params), timeout=60)
        r.raise_for_status()
        return r.json()
    rows, offset = [], 0
    while True:
        pp = list(params) + [("limit", str(PAGE)), ("offset", str(offset))]
        r = requests.get(f"{REST}/{path}", headers=HEADERS, params=pp, timeout=60)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < PAGE:
            return rows
        offset += PAGE


def _upsert(row):
    r = requests.post(
        f"{REST}/expiry_outcomes",
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
        params=[("on_conflict", "symbol,expiry_date,source")],
        data=json.dumps(row), timeout=60)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"upsert -> {r.status_code}: {r.text[:300]}")


# ---------------------------------------------------------------- helpers
def _day_bounds(d):
    return (f"{d.isoformat()}T00:00:00+00:00",
            f"{(d + timedelta(days=1)).isoformat()}T00:00:00+00:00")


def _naive_ist(ts_iso):
    """hist bar_ts stores the IST clock labelled +00:00 -> strip tz (Rule 16)."""
    return datetime.fromisoformat(ts_iso.replace("Z", "+00:00")).replace(tzinfo=None)


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _regime_label(reg):
    return {"LONG_GAMMA": "POSITIVE_γ", "SHORT_GAMMA": "NEGATIVE_γ",
            "NO_FLIP": "MIXED"}.get(reg, "MIXED")


def _daily_last(rows):
    by_date = {}
    for r in rows:
        d = _naive_ist(r["bar_ts"]).date()
        if d not in by_date or r["bar_ts"] > by_date[d]["bar_ts"]:
            by_date[d] = r
    return [by_date[d] for d in sorted(by_date)]


def reconcile(net_gex_regime, div):
    lens_alignment = "DIVERGENT" if div in ("BEARISH_DIV", "BULLISH_DIV") else "ALIGNED"
    if div == "BEARISH_DIV":
        ambient = "DISTRIBUTION"
    elif div == "BULLISH_DIV":
        ambient = "ACCUMULATION"
    elif net_gex_regime == "POSITIVE_γ":
        ambient = "RANGE"
    elif net_gex_regime == "NEGATIVE_γ":
        ambient = "UNSTABLE"
    else:
        ambient = "RANGE"
    return ambient, lens_alignment


# ---------------------------------------------------------------- enumeration
def list_expiries(symbol):
    rows = _get("hist_atm_option_bars_5m", [
        ("symbol", f"eq.{symbol}"),
        ("select", "expiry_date"),
        ("order", "expiry_date.asc"),
    ])
    seen = sorted({r["expiry_date"] for r in rows if r.get("expiry_date")})
    expiries = [date.fromisoformat(e) for e in seen]
    # MONTHLY = last expiry in its (year, month); others WEEKLY
    last_in_month = {}
    for e in expiries:
        last_in_month[(e.year, e.month)] = e
    monthly = set(last_in_month.values())
    return [(e, "MONTHLY" if e in monthly else "WEEKLY") for e in expiries]


# ---------------------------------------------------------------- per-expiry
def label_expiry(symbol, e, etype, pin_threshold_pct):
    lo, hi = _day_bounds(e)

    spot = _get("hist_spot_bars_5m", [
        ("symbol", f"eq.{symbol}"),
        ("bar_ts", f"gte.{lo}"), ("bar_ts", f"lt.{hi}"),
        ("order", "bar_ts.asc"), ("select", "bar_ts,open,high,low,close"),
    ])
    if not spot:
        log(f"  {symbol} {e} [{etype}]: no spot session on expiry date — SKIP")
        return None

    open_spot = _f(spot[0].get("open"))
    settlement = _f(spot[-1].get("close"))
    day_high = max(_f(r.get("high")) for r in spot)
    day_low = min(_f(r.get("low")) for r in spot)
    if not open_spot or not settlement:
        log(f"  {symbol} {e}: null open/settlement — SKIP")
        return None

    # [M1] open_pin = ATM at open = opening spot rounded to the strike step.
    # Reproduces hist_atm_option_bars_5m.atm_strike without depending on that partial
    # ATM backfill (which rolls to next contract at expiry open, so expiry_date=E rows
    # don't exist on date E).
    open_pin = float(round(open_spot / STEP[symbol]) * STEP[symbol])

    settle_pct = round((settlement - open_pin) / open_pin * 100, 4)
    if abs(settle_pct) < pin_threshold_pct:
        resolved = "PINNED"
    elif settle_pct > 0:
        resolved = "BROKE_UP"
    else:
        resolved = "BROKE_DOWN"
    range_pct = round((day_high - day_low) / open_spot * 100, 4)

    gopen = _get("hist_gamma_metrics", [
        ("symbol", f"eq.{symbol}"),
        ("bar_ts", f"gte.{lo}"), ("bar_ts", f"lt.{hi}"),
        ("order", "bar_ts.asc"), ("select", "flip_level,gamma_concentration,regime,net_gex"),
    ], paginate=False)
    open_flip = _f(gopen[0].get("flip_level")) if gopen else None
    conc_open = _f(gopen[0].get("gamma_concentration")) if gopen else None
    net_gex_regime = _regime_label(gopen[0].get("regime")) if gopen else None

    plo, _ = _day_bounds(e - timedelta(days=35))
    prior = _get("hist_gamma_metrics", [
        ("symbol", f"eq.{symbol}"),
        ("bar_ts", f"gte.{plo}"), ("bar_ts", f"lt.{lo}"),
        ("order", "bar_ts.asc"), ("select", "bar_ts,regime,net_gex"),
    ])
    daily = _daily_last(prior)[-20:]
    persistence = None
    if daily:
        longs = sum(1 for r in daily if r.get("regime") == "LONG_GAMMA")
        persistence = round(longs / len(daily), 4)

    ambient, alignment = reconcile(net_gex_regime, "NEUTRAL")   # [M4] breadth NULL historically

    row = {
        "symbol": symbol, "expiry_date": e.isoformat(), "expiry_type": etype,
        "ambient_regime": ambient, "lens_alignment": alignment,
        "gex_regime_persistence": persistence, "concentration_at_open": conc_open,
        "breadth_div_at_open": None, "participant_tilt": None, "macro_tilt": None,
        "open_pin_strike": open_pin, "open_flip_level": open_flip,
        "open_pin_risk_score": None,
        "resolved": resolved, "settlement_vs_open_pin_pct": settle_pct,
        "intraday_range_pct": range_pct, "accel_zone_triggered": None,
        "source": SOURCE,
    }
    log(f"  {symbol} {e} [{etype}]: {resolved} settle={settle_pct:+.2f}% "
        f"range={range_pct:.2f}% pin={open_pin:.0f} persist={persistence} amb={ambient}")
    return row


# ---------------------------------------------------------------- main
def existing_keys(symbol):
    rows = _get("expiry_outcomes", [
        ("symbol", f"eq.{symbol}"), ("source", f"eq.{SOURCE}"),
        ("select", "expiry_date"),
    ])
    return {r["expiry_date"] for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", choices=SYMBOLS, help="one symbol (default: both)")
    ap.add_argument("--pin-threshold-pct", type=float, default=0.25,
                    help="[M2] |settle vs open pin| below this = PINNED (default 0.25)")
    ap.add_argument("--dry-run", action="store_true", help="compute + print, no write")
    ap.add_argument("--force", action="store_true", help="re-label expiries already present")
    args = ap.parse_args()

    if not SUPABASE_URL or not SERVICE_KEY:
        log("FATAL: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not in env")
        return 2

    today = datetime.now(UTC).date()
    symbols = [args.symbol] if args.symbol else SYMBOLS
    total_written = 0

    for sym in symbols:
        expiries = [(e, t) for (e, t) in list_expiries(sym) if e < today]
        done = set() if (args.dry_run or args.force) else existing_keys(sym)
        todo = [(e, t) for (e, t) in expiries if e.isoformat() not in done]
        log(f"{sym}: {len(expiries)} expiries in window, {len(todo)} to label "
            f"({len(expiries) - len(todo)} already present)")

        for e, etype in todo:
            try:
                row = label_expiry(sym, e, etype, args.pin_threshold_pct)
            except Exception as ex:
                log(f"  {sym} {e}: ERROR {ex} — continuing")
                continue
            if row and not args.dry_run:
                _upsert(row)
                total_written += 1

    log(f"DONE wrote={total_written}" + (" (dry-run, no writes)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
