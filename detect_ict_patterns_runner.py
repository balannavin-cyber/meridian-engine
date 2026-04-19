#!/usr/bin/env python3
"""
detect_ict_patterns_runner.py
ENH-37 — ICT Pattern Detection Runner Integration

Called by run_option_snapshot_intraday_runner.py every 5-minute cycle,
between build_market_state_snapshot_local.py and build_trade_signal_local.py.

What this script does each cycle:
  1. Load today's spot bars from hist_spot_bars_1m (or live spot table)
  2. Load active HTF zones from ict_htf_zones
  3. Run ICTDetector on last 10 bars (sub-cycle detection)
  4. Write new ACTIVE zones to ict_zones (deduplicated by unique index)
  5. Check existing ACTIVE zones for breaches — mark BROKEN if spot closed through
  6. If on an hour boundary (first cycle of a new hour): build 1H HTF zones

Usage:
    python detect_ict_patterns_runner.py NIFTY
    python detect_ict_patterns_runner.py SENSEX

Exit codes:
    0 — success (or non-fatal error — non-blocking step)
    1 — fatal error
"""

import os
import sys
import time
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client

from detect_ict_patterns import (
    ICTDetector, Bar, HTFZone,
    enrich_signal_with_ict,
)
from build_ict_htf_zones import detect_1h_zones, upsert_zones
from merdian_utils import (  # ENH-38v2
    effective_sizing_capital, compute_kelly_lots,
    build_expiry_index_simple, nearest_expiry_db, LOT_SIZES,
)

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

IST      = ZoneInfo("Asia/Kolkata")
PAGE_SIZE = 1_000

# How many bars to look back for sub-cycle detection
DETECTION_LOOKBACK = 90   # last 90 1-min bars (~1.5 hours of context)

# Hour boundary check: run 1H zone builder if within first 3 minutes of hour
HOURLY_ZONE_WINDOW_MINUTES = 3

# ENH-63: process-lifetime cache for expiry index.
# build_expiry_index_simple issues 12 paginated Supabase queries per call.
# Expiry dates are near-static -- per-process caching (vs per-cycle rebuild)
# cuts daily query volume from ~1,728 to 1 per symbol.
_EXPIRY_INDEX_CACHE: dict = {}


def log(msg: str) -> None:
    ts = datetime.now(tz=timezone.utc).astimezone(IST).strftime("%H:%M:%S IST")
    print(f"[{ts}] {msg}", flush=True)


def now_ist() -> datetime:
    return datetime.now(tz=timezone.utc).astimezone(IST)


def is_hour_boundary() -> bool:
    """True if we're in the first HOURLY_ZONE_WINDOW_MINUTES of a new hour."""
    n = now_ist()
    return n.minute < HOURLY_ZONE_WINDOW_MINUTES


def fetch_with_retry(query_fn, max_attempts=4):
    for attempt in range(max_attempts):
        try:
            return query_fn()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            time.sleep(2 ** attempt)


# ── Data loaders ──────────────────────────────────────────────────────

def load_today_spot_bars(sb, inst_id: str, trade_date: date) -> list[Bar]:
    """Load today's intraday spot bars. Returns list[Bar] sorted by time."""
    all_rows, offset = [], 0
    while True:
        rows = fetch_with_retry(lambda: (
            sb.table("hist_spot_bars_1m")
            .select("bar_ts, trade_date, open, high, low, close")
            .eq("instrument_id", inst_id)
            .eq("trade_date", str(trade_date))
            .eq("is_pre_market", False)
            .order("bar_ts")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute().data
        ))
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    bars = []
    for r in all_rows:
        bars.append(Bar(
            bar_ts=datetime.fromisoformat(r["bar_ts"]),
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
            trade_date=date.fromisoformat(r["trade_date"]),
        ))
    return bars


def load_prior_session_hl(sb, inst_id: str, trade_date: date):
    """Get prior session high and low for sweep detection."""
    prior_date = trade_date - timedelta(days=1)
    # Try up to 5 prior days (weekends/holidays)
    for days_back in range(1, 6):
        d = trade_date - timedelta(days=days_back)
        rows = fetch_with_retry(lambda: (
            sb.table("hist_spot_bars_1m")
            .select("high, low")
            .eq("instrument_id", inst_id)
            .eq("trade_date", str(d))
            .eq("is_pre_market", False)
            .execute().data
        ))
        if rows:
            prior_high = max(float(r["high"]) for r in rows)
            prior_low  = min(float(r["low"])  for r in rows)
            return prior_high, prior_low
    return None, None


def load_active_htf_zones(sb, symbol: str, trade_date: date) -> list[HTFZone]:
    """Load active HTF zones valid for today."""
    rows = fetch_with_retry(lambda: (
        sb.table("ict_htf_zones")
        .select("id, symbol, timeframe, pattern_type, direction, "
                "zone_high, zone_low, status")
        .eq("symbol", symbol)
        .eq("status", "ACTIVE")
        .lte("valid_from", str(trade_date))
        .gte("valid_to", str(trade_date))
        .execute().data
    ))
    zones = []
    for r in rows:
        zones.append(HTFZone(
            id=r["id"],
            symbol=r["symbol"],
            timeframe=r["timeframe"],
            pattern_type=r["pattern_type"],
            direction=int(r["direction"]),
            zone_high=float(r["zone_high"]),
            zone_low=float(r["zone_low"]),
            status=r["status"],
        ))
    return zones


def load_active_intraday_zones(sb, symbol: str, trade_date: date) -> list[dict]:
    """Load active intraday zones for breach checking."""
    rows = fetch_with_retry(lambda: (
        sb.table("ict_zones")
        .select("id, symbol, pattern_type, direction, zone_high, zone_low, "
                "status, detected_at_ts")
        .eq("symbol", symbol)
        .eq("trade_date", str(trade_date))
        .eq("status", "ACTIVE")
        .execute().data
    ))
    return rows


def load_atm_iv(sb, symbol: str) -> float | None:
    """Get latest atm_iv from market_state_snapshots."""
    rows = fetch_with_retry(lambda: (
        sb.table("market_state_snapshots")
        .select("market_state")
        .eq("symbol", symbol)
        .order("ts", desc=True)
        .limit(1)
        .execute().data
    ))
    if not rows:
        return None
    try:
        ms = rows[0].get("market_state") or {}
        if isinstance(ms, str):
            import json
            ms = json.loads(ms)
        vol = ms.get("volatility_features") or {}
        iv  = vol.get("atm_iv_avg") or vol.get("atm_iv")
        return float(iv) if iv is not None else None
    except Exception:
        return None


# ── Zone writes ───────────────────────────────────────────────────────

def write_new_zones(sb, patterns: list) -> int:
    """Write detected patterns as new ACTIVE zones to ict_zones."""
    if not patterns:
        return 0

    rows = [p.to_db_row() for p in patterns]
    written = 0

    for row in rows:
        try:
            # Upsert on unique key: (symbol, session_bar_ts, pattern_type)
            fetch_with_retry(lambda: (
                sb.table("ict_zones")
                .upsert(row,
                        on_conflict="symbol,session_bar_ts,pattern_type")
                .execute()
            ))
            written += 1
        except Exception as e:
            log(f"  Warning: zone write failed ({row['pattern_type']}): {e}")

    return written


def mark_zones_broken(sb, broken_ids: list[str], current_spot: float) -> int:
    """Mark breached zones as BROKEN."""
    if not broken_ids:
        return 0

    now_ts = datetime.now(tz=timezone.utc).isoformat()
    marked = 0

    for zone_id in broken_ids:
        try:
            fetch_with_retry(lambda: (
                sb.table("ict_zones")
                .update({
                    "status":       "BROKEN",
                    "broken_at_ts": now_ts,
                    "break_price":  current_spot,
                    "updated_at":   now_ts,
                })
                .eq("id", zone_id)
                .execute()
            ))
            marked += 1
        except Exception as e:
            log(f"  Warning: could not mark zone {zone_id} broken: {e}")

    return marked


def expire_prior_session_zones(sb, symbol: str, trade_date: date) -> None:
    """Mark all ACTIVE zones from prior sessions as EXPIRED."""
    try:
        fetch_with_retry(lambda: (
            sb.table("ict_zones")
            .update({"status": "EXPIRED",
                     "updated_at": datetime.now(tz=timezone.utc).isoformat()})
            .eq("symbol", symbol)
            .lt("trade_date", str(trade_date))
            .eq("status", "ACTIVE")
            .execute()
        ))
    except Exception as e:
        log(f"  Warning: could not expire prior zones: {e}")


# ── Main ──────────────────────────────────────────────────────────────

def main(symbol: str) -> int:
    sb         = create_client(SUPABASE_URL, SUPABASE_KEY)
    now        = now_ist()
    trade_date = now.date()

    log(f"ICT detector start [{symbol}] {now.strftime('%H:%M:%S IST')}")

    # Fetch instrument ID
    inst_rows = fetch_with_retry(lambda: (
        sb.table("instruments")
        .select("id")
        .eq("symbol", symbol)
        .execute().data
    ))
    if not inst_rows:
        log(f"ERROR: instrument not found for {symbol}")
        return 1
    inst_id = inst_rows[0]["id"]
    # -- ENH-38: read current capital from capital_tracker -----------------
    try:
        _cap_resp = fetch_with_retry(lambda: (
            sb.table('capital_tracker')
            .select('capital')
            .eq('symbol', symbol)
            .limit(1)
            .execute()
        ))
        _current_capital = float(_cap_resp.data[0]['capital']) if _cap_resp.data else 200_000.0
    except Exception as _cap_err:
        log(f'  Warning: capital_tracker read failed: {_cap_err} -- using floor')
        _current_capital = 200_000.0
    # -- ENH-38 end --------------------------------------------------------


    # ── Session start: expire prior zones ─────────────────────────────
    # Only do this once per session (first cycle after 09:15)
    if now.hour == 9 and now.minute < 20:
        expire_prior_session_zones(sb, symbol, trade_date)
        log(f"  Expired prior session zones for {symbol}")

    # ── Load data ─────────────────────────────────────────────────────
    bars = load_today_spot_bars(sb, inst_id, trade_date)
    if len(bars) < 10:
        log(f"  Insufficient bars ({len(bars)}) — skipping detection")
        return 0

    prior_high, prior_low = load_prior_session_hl(sb, inst_id, trade_date)
    htf_zones  = load_active_htf_zones(sb, symbol, trade_date)
    active_zones = load_active_intraday_zones(sb, symbol, trade_date)
    atm_iv     = load_atm_iv(sb, symbol)
    current_spot = bars[-1].close

    log(f"  {len(bars)} bars | {len(htf_zones)} HTF zones | "
        f"{len(active_zones)} active zones | "
        f"spot={current_spot:,.1f} | iv={atm_iv:.1f}%" if atm_iv else
        f"  {len(bars)} bars | {len(htf_zones)} HTF zones | "
        f"{len(active_zones)} active zones | spot={current_spot:,.1f}")

    # ── Zone breach checking ──────────────────────────────────────────
    detector     = ICTDetector(symbol=symbol)
    broken_ids   = detector.check_zone_breaches(active_zones, current_spot)
    if broken_ids:
        n = mark_zones_broken(sb, broken_ids, current_spot)
        log(f"  Marked {n} zones BROKEN at {current_spot:,.1f}")

    # ── Pattern detection (last 10 bars) ──────────────────────────────
    patterns = detector.detect(
        bars=bars,
        atm_iv=atm_iv,
        htf_zones=htf_zones,
        prior_high=prior_high,
        prior_low=prior_low,
    )

    if patterns:
        n = write_new_zones(sb, patterns)
        for p in patterns:
            log(f"  NEW ZONE: {p.pattern_type} {p.ict_tier} "
                f"mtf={p.mtf_context} zone={p.zone_low:,.0f}-{p.zone_high:,.0f} "
                f"size={p.ict_size_mult}x")
        log(f"  Written {n} new zones")
    else:
        log(f"  No new patterns detected")

    # ── 1H zone builder (hourly) ──────────────────────────────────────
    if is_hour_boundary():
        log(f"  Hour boundary — building 1H HTF zones...")
        try:
            h_zones = detect_1h_zones(sb, inst_id, symbol, trade_date)
            n = upsert_zones(sb, h_zones, dry_run=False)
            log(f"  1H zones: {n} written ({len(h_zones)} detected)")
        except Exception as e:
            log(f"  Warning: 1H zone build failed (non-blocking): {e}")

    # -- ENH-38v2: write Kelly lots to active ict_zones (real lot cost) -------
    try:
        # Get days to next expiry for lot cost estimation
        try:
            _expiry_idx = _EXPIRY_INDEX_CACHE.get(inst_id)
            if _expiry_idx is None:
                _expiry_idx = build_expiry_index_simple(sb, inst_id)
                _EXPIRY_INDEX_CACHE[inst_id] = _expiry_idx
            _next_exp = nearest_expiry_db(trade_date, _expiry_idx)
            _dte_days = (_next_exp - trade_date).days if _next_exp else 2
        except Exception:
            _dte_days = 2   # conservative fallback
        _atm_iv_pct = atm_iv if atm_iv else 0.0   # None -> 0 triggers fallback

        _lots_t1 = compute_kelly_lots(_current_capital, 'TIER1', symbol,
                                      current_spot, _atm_iv_pct, _dte_days)
        _lots_t2 = compute_kelly_lots(_current_capital, 'TIER2', symbol,
                                      current_spot, _atm_iv_pct, _dte_days)
        _lots_t3 = compute_kelly_lots(_current_capital, 'TIER3', symbol,
                                      current_spot, _atm_iv_pct, _dte_days)

        fetch_with_retry(lambda: (
            sb.table('ict_zones')
            .update({
                'ict_lots_t1': _lots_t1,
                'ict_lots_t2': _lots_t2,
                'ict_lots_t3': _lots_t3,
            })
            .eq('symbol', symbol)
            .eq('trade_date', str(trade_date))
            .eq('status', 'ACTIVE')
            .execute()
        ))
        _lot_size = LOT_SIZES.get(symbol, 65)
        log(f'  Kelly lots (lot_size={_lot_size}, dte={_dte_days}d, '
            f'iv={_atm_iv_pct:.1f}%, spot={current_spot:,.0f}) '
            f'T1:{_lots_t1} T2:{_lots_t2} T3:{_lots_t3} '
            f'(capital=INR {_current_capital:,.0f})')
    except Exception as _kelly_err:
        log(f'  Warning: Kelly lots write failed (non-blocking): {_kelly_err}')
    # -- ENH-38v2 end ----------------------------------------------------------

    log(f"ICT detector complete [{symbol}]")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python detect_ict_patterns_runner.py <SYMBOL>")
        sys.exit(1)

    symbol = sys.argv[1].upper()
    if symbol not in ("NIFTY", "SENSEX"):
        print(f"ERROR: Unknown symbol {symbol}")
        sys.exit(1)

    try:
        rc = main(symbol)
        sys.exit(rc)
    except Exception as e:
        print(f"[FATAL] {e}", flush=True)
        sys.exit(0)  # exit 0 — non-blocking, don't halt runner
