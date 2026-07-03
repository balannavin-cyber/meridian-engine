#!/usr/bin/env python3
"""
accrue_expiry_outcomes.py  —  ENH-116 forward-accrual labeler (companion to the seed)

Each expiry day, writes one expiry_outcomes row labeled with the LIVE v2 ambient state
(from that morning's market_environment_snapshots verdict) + the settlement outcome.
This is what makes v_expiry_base_rates discriminate: the S64 seed labeled history with
breadth NULL so every row is ambient_regime=RANGE; every expiry from here forward carries
a real reconciled verdict (TREND_UP / DISTRIBUTION / UNSTABLE / …).

Runs daily post-market (after the evening compiler). Detects an expiry via
gamma_metrics.expiry_date == today; on non-expiry days it no-ops. One-shot-safe:
UPSERT on (symbol, expiry_date, source). Operator-invoked or cron'd; --dry-run + --as-of.

DESIGN:
  * ambient-going-in  : market_environment_snapshots WHERE for_session_date = expiry
      (the compiler's row written the evening before). If absent -> SKIP (never fabricate
      a coarse ambient read; the whole point is the live verdict). Sourced separately from
      the seed so forward rows are distinguishable, though v_expiry_base_rates pools both.
  * open pin/flip/conc: the expiry session's first gamma_metrics cycle.
  * outcome           : spot open/high/low/settlement from the day's gamma_metrics cycles.
  * open_pin_strike   : ATM = opening spot rounded to strike step — SAME definition as the
      seed ([M1]) so settlement_vs_open_pin_pct is comparable across the pooled cohort.
  * expiry_type       : MONTHLY if next week crosses into a new month, else WEEKLY (v1
      forward heuristic; tunable). resolved threshold shares --pin-threshold-pct with seed.
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
REST = f"{SUPABASE_URL}/rest/v1"
HEADERS = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}",
           "Content-Type": "application/json"}

SYMBOLS = ["NIFTY", "SENSEX"]
STEP = {"NIFTY": 50, "SENSEX": 100}
SOURCE_LIVE = "expiry_memory_live"          # forward rows (rich ambient)
SOURCE_COMPILER = "ambient_compiler_s62"    # market_environment_snapshots source to read


def now_ist():
    return datetime.now(IST)


def log(msg):
    print(f"[{now_ist().isoformat()}] {msg}", flush=True)


def _get(path, params):
    r = requests.get(f"{REST}/{path}", headers=HEADERS, params=list(params), timeout=60)
    r.raise_for_status()
    return r.json()


def _upsert(row):
    r = requests.post(
        f"{REST}/expiry_outcomes",
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
        params=[("on_conflict", "symbol,expiry_date,source")],
        data=json.dumps(row), timeout=60)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"upsert -> {r.status_code}: {r.text[:300]}")


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _participant_tilt(env):
    """Reduce the env row's L3 fields to a tilt label — mirrors the compiler's v1 vote."""
    fii = _f(env.get("fii_index_fut_ls_delta_5d"))
    asym = _f(env.get("cycle_oi_call_put_asym"))
    pro = _f(env.get("pro_options_imbalance"))
    if fii is None and asym is None and pro is None:
        return None
    def sgn(x):
        return 0 if not x else (1 if x > 0 else -1)
    score = sgn(fii) * 1.0 - sgn(asym) * 0.5 + sgn(pro) * 0.5
    return "BULLISH" if score > 0.5 else "BEARISH" if score < -0.5 else "NEUTRAL"


def _day_bounds_utc(d):
    lo = datetime.combine(d, datetime.min.time(), tzinfo=IST).astimezone(UTC)
    hi = datetime.combine(d + timedelta(days=1), datetime.min.time(), tzinfo=IST).astimezone(UTC)
    return lo.isoformat(), hi.isoformat()


def label_if_expiry(symbol, as_of, pin_threshold_pct, dry_run):
    lo, hi = _day_bounds_utc(as_of)
    cycles = _get("gamma_metrics", [
        ("symbol", f"eq.{symbol}"),
        ("ts", f"gte.{lo}"), ("ts", f"lt.{hi}"),
        ("order", "ts.asc"),
        ("select", "ts,spot,expiry_date,flip_level,max_gamma_strike,gamma_concentration,pin_risk_score"),
    ])
    if not cycles:
        log(f"{symbol}: no gamma_metrics for {as_of} — SKIP")
        return None

    expiry = cycles[0].get("expiry_date")
    if expiry != as_of.isoformat():
        log(f"{symbol}: {as_of} is not an expiry (front expiry {expiry}) — no-op")
        return None

    # ambient-going-in: the compiler's verdict written the evening before
    env_rows = _get("market_environment_snapshots", [
        ("symbol", f"eq.{symbol}"), ("for_session_date", f"eq.{as_of.isoformat()}"),
        ("source", f"eq.{SOURCE_COMPILER}"), ("order", "created_at.desc"), ("limit", "1"),
        ("select", "ambient_regime,lens_alignment,gex_regime_persistence_20d,"
                   "price_vs_breadth_div,cycle_oi_call_put_asym,fii_index_fut_ls_delta_5d,"
                   "pro_options_imbalance,macro_tilt"),
    ])
    if not env_rows:
        log(f"{symbol}: EXPIRY {as_of} but no ambient row (compiler didn't run) — SKIP, "
            f"cannot label without the live verdict")
        return None
    env = env_rows[0]

    opn = cycles[0]
    open_spot = _f(opn.get("spot"))
    settlement = _f(cycles[-1].get("spot"))
    spots = [_f(c.get("spot")) for c in cycles if _f(c.get("spot")) is not None]
    if not open_spot or not settlement or not spots:
        log(f"{symbol}: EXPIRY {as_of} but null spot — SKIP")
        return None
    day_high, day_low = max(spots), min(spots)

    open_pin = float(round(open_spot / STEP[symbol]) * STEP[symbol])   # ATM, seed-consistent
    settle_pct = round((settlement - open_pin) / open_pin * 100, 4)
    resolved = ("PINNED" if abs(settle_pct) < pin_threshold_pct else
                "BROKE_UP" if settle_pct > 0 else "BROKE_DOWN")
    range_pct = round((day_high - day_low) / open_spot * 100, 4)
    expiry_type = "MONTHLY" if (as_of + timedelta(days=7)).month != as_of.month else "WEEKLY"

    row = {
        "symbol": symbol, "expiry_date": as_of.isoformat(), "expiry_type": expiry_type,
        "ambient_regime": env.get("ambient_regime"),
        "lens_alignment": env.get("lens_alignment"),
        "gex_regime_persistence": _f(env.get("gex_regime_persistence_20d")),
        "concentration_at_open": _f(opn.get("gamma_concentration")),
        "breadth_div_at_open": env.get("price_vs_breadth_div"),
        "participant_tilt": _participant_tilt(env),
        "macro_tilt": env.get("macro_tilt"),
        "open_pin_strike": open_pin,
        "open_flip_level": _f(opn.get("flip_level")),
        "open_pin_risk_score": _f(opn.get("pin_risk_score")),
        "resolved": resolved,
        "settlement_vs_open_pin_pct": settle_pct,
        "intraday_range_pct": range_pct,
        "accel_zone_triggered": None,
        "source": SOURCE_LIVE,
    }
    log(f"{symbol} EXPIRY {as_of} [{expiry_type}]: {resolved} settle={settle_pct:+.2f}% "
        f"range={range_pct:.2f}% pin={open_pin:.0f} ambient={env.get('ambient_regime')}/"
        f"{env.get('lens_alignment')} tilt={_participant_tilt(env)}"
        + (" (dry-run)" if dry_run else ""))
    if not dry_run:
        _upsert(row)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", help="session date YYYY-MM-DD (default: today IST)")
    ap.add_argument("--pin-threshold-pct", type=float, default=0.25,
                    help="|settle vs open pin| below this = PINNED (matches the seed)")
    ap.add_argument("--dry-run", action="store_true", help="compute + print, no write")
    args = ap.parse_args()

    if not SUPABASE_URL or not SERVICE_KEY:
        log("FATAL: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not in env")
        return 2

    from core.trading_calendar_gate import is_trading_day, assert_trading_day_or_exit
    as_of = (datetime.fromisoformat(args.as_of).date() if args.as_of else now_ist().date())
    if not args.as_of:
        assert_trading_day_or_exit(log=log)
    elif not is_trading_day(as_of.isoformat()):
        log(f"{as_of} is not a trading day — nothing to accrue")
        return 0

    labeled = 0
    for sym in SYMBOLS:
        try:
            if label_if_expiry(sym, as_of, args.pin_threshold_pct, args.dry_run):
                labeled += 1
        except Exception as e:
            log(f"{sym}: ERROR {e} — continuing")
    log(f"DONE labeled={labeled}" + (" (dry-run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
