#!/usr/bin/env python3
"""
relate_ambient_to_open_local.py  —  ENH-116 build-sequence step 4 (pre-market reconciler)
"Compute at rest, relate at open."

Tiny, single-responsibility counterpart to compile_market_environment_local.py: takes
last night's settled market_environment_snapshots row (keyed for_session_date=today) and
this morning's OPENING gamma structure (the session's first live gamma_metrics cycle),
decides whether the open CONFIRMS or SHIFTS the settled prior, and PATCHes the relate-half
of session_prior onto today's row. Milliseconds; nothing here can hang the open.

Run just after the open (~09:20 IST) once the first live gamma cycle has landed.
Display-not-gate. No ExecutionLog by design (mirrors capture_premarket_0908.py minimalism).
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
SOURCE = "ambient_compiler_s62"   # must match the compiler's row source


def now_ist():
    return datetime.now(IST)


def log(msg):
    print(f"[{now_ist().isoformat()}] {msg}", flush=True)


def _get(path, params):
    r = requests.get(f"{REST}/{path}", headers=HEADERS, params=list(params), timeout=60)
    r.raise_for_status()
    return r.json()


def _patch_prior(symbol, for_session, new_prior):
    r = requests.patch(
        f"{REST}/market_environment_snapshots",
        headers={**HEADERS, "Prefer": "return=minimal"},
        params=[("symbol", f"eq.{symbol}"),
                ("for_session_date", f"eq.{for_session}"),
                ("source", f"eq.{SOURCE}")],
        data=json.dumps({"session_prior": new_prior}), timeout=60)
    if r.status_code not in (200, 204):
        raise RuntimeError(f"patch -> {r.status_code}: {r.text[:300]}")


def _regime_label(reg):
    return {"LONG_GAMMA": "POSITIVE_γ", "SHORT_GAMMA": "NEGATIVE_γ",
            "NO_FLIP": "MIXED"}.get(reg, "MIXED")


def relate_symbol(symbol, for_session, latest_gamma=False):
    # last night's settled ambient row for this session
    rows = _get("market_environment_snapshots", [
        ("symbol", f"eq.{symbol}"), ("for_session_date", f"eq.{for_session.isoformat()}"),
        ("source", f"eq.{SOURCE}"), ("order", "created_at.desc"), ("limit", "1"),
        ("select", "ambient_regime,net_gex_regime,price_vs_breadth_div,session_prior"),
    ])
    if not rows:
        log(f"{symbol}: no settled ambient row for {for_session} — did the compiler run? SKIP")
        return None
    amb = rows[0]

    # opening structure: the session's first live gamma cycle (or, in proof mode,
    # the latest cycle available regardless of day)
    if latest_gamma:
        gopen = _get("gamma_metrics", [
            ("symbol", f"eq.{symbol}"), ("order", "ts.desc"), ("limit", "1"),
            ("select", "ts,spot,regime,flip_level,max_gamma_strike,net_gex"),
        ])
    else:
        day_start_utc = datetime.combine(for_session, datetime.min.time(),
                                         tzinfo=IST).astimezone(UTC)
        gopen = _get("gamma_metrics", [
            ("symbol", f"eq.{symbol}"), ("ts", f"gte.{day_start_utc.isoformat()}"),
            ("order", "ts.asc"), ("limit", "1"),
            ("select", "ts,spot,regime,flip_level,max_gamma_strike,net_gex"),
        ])
    if not gopen:
        log(f"{symbol}: no opening gamma cycle for {for_session} — run after the open. SKIP")
        return None
    g = gopen[0]
    open_regime = _regime_label(g.get("regime"))

    settled_regime = amb.get("net_gex_regime")
    verdict = "CONFIRMS" if open_regime == settled_regime else "SHIFTS"
    conviction = "prior holds" if verdict == "CONFIRMS" else "prior weakened — regime moved overnight"

    pin = g.get("max_gamma_strike")
    flip = g.get("flip_level")
    relate = (f"OPEN {verdict}: settled {amb.get('ambient_regime')} "
              f"({settled_regime}, breadth {amb.get('price_vs_breadth_div')}) vs open "
              f"{open_regime} pin {pin} flip {flip} -> {conviction}.")

    base = amb.get("session_prior") or ""
    new_prior = f"{base}  ||  {relate}" if base else relate
    _patch_prior(symbol, for_session.isoformat(), new_prior)
    log(f"{symbol}: {verdict} (settled {settled_regime} / open {open_regime})")
    return relate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--for-session", help="target for_session_date YYYY-MM-DD (default: today IST)")
    ap.add_argument("--latest-gamma", action="store_true",
                    help="proof mode: use the latest gamma cycle instead of the session's first")
    args = ap.parse_args()

    if not SUPABASE_URL or not SERVICE_KEY:
        log("FATAL: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not in env")
        return 2

    proof = bool(args.for_session or args.latest_gamma)
    if not proof:
        from core.trading_calendar_gate import assert_trading_day_or_exit
        assert_trading_day_or_exit(log=log)

    for_session = (datetime.fromisoformat(args.for_session).date()
                   if args.for_session else now_ist().date())
    for sym in SYMBOLS:
        try:
            relate_symbol(sym, for_session, args.latest_gamma)
        except Exception as e:
            log(f"{sym}: ERROR {e} — continuing")
    log("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
