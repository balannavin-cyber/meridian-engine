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

ENH-72 instrumentation contract:
  - expected_writes = {"ict_zones": 0}  -- FLOOR of 0.
    Rationale: most cycles produce ZERO new patterns (patterns are rare
    events). Setting floor=1 would fail contract_met on 80%+ of cycles.
    contract_met=true whenever the script reaches log.complete() cleanly.
  - record_write("ict_zones", new_patterns_count) tracks actual writes.
  - Updates (breach marks, Kelly lot updates) are NOT counted toward the
    contract -- they modify existing rows, not create new ones. Tracked
    in completion notes for operator visibility.
  - NON-BLOCKING PHILOSOPHY PRESERVED: all exit_with_reason paths exit 0
    (not 1) to match the original "don't halt runner" design. The
    script_execution_log row still gets proper exit_reason=DATA_ERROR etc.
    but the OS-level exit code stays 0 so the runner proceeds.
  - Notes format:
    bars=N htf={N} active={N} new_patterns=N broken=N
    [hourly_written=N] [kelly_failed=true] [insufficient_bars=true]
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
from merdian_utils import (  # ENH-38v2, OI-26 fix
    effective_sizing_capital, compute_kelly_lots,
    get_nearest_expiry, LOT_SIZES,
)

# ENH-72 write-contract layer. See docs/MERDIAN_Master_V19.docx governance
# rule `script_execution_log_contract`. Pattern mirrored from target 6
# (build_trade_signal_local.py): symbol-at-construction, no set_symbol().
from core.execution_log import ExecutionLog


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

IST      = ZoneInfo("Asia/Kolkata")
PAGE_SIZE = 1_000

# How many bars to look back for sub-cycle detection
DETECTION_LOOKBACK = 90   # last 90 1-min bars (~1.5 hours of context)

# OI-27 fix (2026-04-21): HOURLY_ZONE_WINDOW_MINUTES / is_hour_boundary()
# replaced with should_rebuild_1h_zones() (defined below). The time-window
# check fired only when minute-of-hour was 0-2, but the production runner
# cycle schedule (every 5 min offset from 09:14 start) rarely landed in
# that window. Result: zero 1H zones in ict_htf_zones ever.
# Data-driven replacement works for any cycle schedule: rebuild once per
# hour per symbol, no-op if already done.

# ENH-63 expiry index cache REMOVED 2026-04-21 (OI-26). Superseded by
# get_nearest_expiry() which reads option_chain_snapshots directly. The
# Dhan-sourced expiry is already cached server-side per-run; no need for
# a client-side index.


def log(msg: str) -> None:
    ts = datetime.now(tz=timezone.utc).astimezone(IST).strftime("%H:%M:%S IST")
    print(f"[{ts}] {msg}", flush=True)


def now_ist() -> datetime:
    return datetime.now(tz=timezone.utc).astimezone(IST)


def should_rebuild_1h_zones(sb, symbol: str) -> bool:
    """
    True if no 1H zones have been written for this symbol in the current
    hour yet. Data-driven replacement for the old time-window
    is_hour_boundary() check (OI-27).

    Why:
      Old logic (minute < 3) required the cycle to land in minutes 0-2
      of each hour. Production runner schedule offset from 09:14 never
      hits that window -- result: zero 1H zones in ict_htf_zones ever.

    Benefits of this approach:
      - Works for any cycle schedule (:00/:05/:10 or :14/:19/:24 etc)
      - Still fires at most once per hour per symbol (idempotent upsert
        means re-firing is harmless, but wasting work has no benefit)
      - Fails open on query error: when in doubt, rebuild

    Args:
        sb:     supabase client
        symbol: "NIFTY" or "SENSEX"

    Returns:
        True  if we should build 1H zones this cycle
        False if 1H zones for current hour already exist
    """
    ist_now = now_ist()
    hour_start_ist = ist_now.replace(minute=0, second=0, microsecond=0)
    # Convert to UTC for Supabase created_at filter (stored UTC by convention)
    hour_start_utc = hour_start_ist.astimezone(timezone.utc).isoformat()
    try:
        rows = fetch_with_retry(lambda: (
            sb.table("ict_htf_zones")
            .select("id")
            .eq("symbol", symbol)
            .eq("timeframe", "H")
            .gte("created_at", hour_start_utc)
            .limit(1)
            .execute().data
        ))
        return not rows  # True = no 1H rows yet this hour -> rebuild
    except Exception:
        # On query error, default to rebuilding (fail-open). Better to
        # redundantly build once than silently skip the hourly rebuild.
        return True


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
    """Get latest atm_iv from market_state_snapshots.

    Schema fix 2026-04-21: original code queried `market_state` column
    which does not exist in current schema. The table stores features as
    separate JSONB columns (gamma_features, volatility_features, etc.).
    Now reads volatility_features.atm_iv_avg directly -- matches how
    build_trade_signal_local.py consumes the same field.

    Returns None on any failure -- atm_iv is an optional input for the
    detector; downstream uses fallback thresholds when unavailable.
    """
    try:
        rows = fetch_with_retry(lambda: (
            sb.table("market_state_snapshots")
            .select("volatility_features")
            .eq("symbol", symbol)
            .order("ts", desc=True)
            .limit(1)
            .execute().data
        ))
        if not rows:
            return None
        vol = rows[0].get("volatility_features") or {}
        if isinstance(vol, str):
            import json
            vol = json.loads(vol)
        iv = vol.get("atm_iv_avg") or vol.get("atm_iv")
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

def main(symbol: str, log_handle: ExecutionLog) -> int:
    """
    Inner orchestration. Returns exit code (all 0 per non-blocking design).
    All exit paths route through log_handle so script_execution_log
    always gets a final row.

    Returns tuple of (exit_code, stats_dict) is NOT used -- the log
    completion happens inside this function before the outer wrapper
    in __main__.
    """
    # ── Supabase client construction (env-var check) ─────────────────
    if not SUPABASE_URL or not SUPABASE_KEY:
        return log_handle.exit_with_reason(
            "DEPENDENCY_MISSING",
            exit_code=0,  # non-blocking per script design
            error_message="Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY",
        )

    try:
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return log_handle.exit_with_reason(
            "DEPENDENCY_MISSING",
            exit_code=0,
            error_message=f"Supabase client init failed: {e}",
        )

    now        = now_ist()
    trade_date = now.date()

    log(f"ICT detector start [{symbol}] {now.strftime('%H:%M:%S IST')}")

    # Fetch instrument ID
    try:
        inst_rows = fetch_with_retry(lambda: (
            sb.table("instruments")
            .select("id")
            .eq("symbol", symbol)
            .execute().data
        ))
    except Exception as e:
        return log_handle.exit_with_reason(
            "DATA_ERROR",
            exit_code=0,
            error_message=f"instruments table query failed: {e}",
        )

    if not inst_rows:
        log(f"ERROR: instrument not found for {symbol}")
        return log_handle.exit_with_reason(
            "DATA_ERROR",
            exit_code=0,
            error_message=f"No instruments row for symbol={symbol}",
        )
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
    try:
        bars = load_today_spot_bars(sb, inst_id, trade_date)
    except Exception as e:
        return log_handle.exit_with_reason(
            "DATA_ERROR",
            exit_code=0,
            error_message=f"load_today_spot_bars failed: {e}",
        )

    if len(bars) < 10:
        log(f"  Insufficient bars ({len(bars)}) — skipping detection")
        # Not an error -- pre-market or insufficient data. SUCCESS with
        # note flag so operators can see why no patterns emerged.
        log_handle.record_write("ict_zones", 0)
        return log_handle.complete(
            notes=f"bars={len(bars)} insufficient_bars=true"
        )

    try:
        prior_high, prior_low = load_prior_session_hl(sb, inst_id, trade_date)
        htf_zones  = load_active_htf_zones(sb, symbol, trade_date)
        active_zones = load_active_intraday_zones(sb, symbol, trade_date)
        atm_iv     = load_atm_iv(sb, symbol)
    except Exception as e:
        return log_handle.exit_with_reason(
            "DATA_ERROR",
            exit_code=0,
            error_message=f"supporting data load failed: {e}",
        )

    current_spot = bars[-1].close

    log(f"  {len(bars)} bars | {len(htf_zones)} HTF zones | "
        f"{len(active_zones)} active zones | "
        f"spot={current_spot:,.1f} | iv={atm_iv:.1f}%" if atm_iv else
        f"  {len(bars)} bars | {len(htf_zones)} HTF zones | "
        f"{len(active_zones)} active zones | spot={current_spot:,.1f}")

    # ── Zone breach checking ──────────────────────────────────────────
    detector     = ICTDetector(symbol=symbol)
    broken_count = 0
    try:
        broken_ids = detector.check_zone_breaches(active_zones, current_spot)
        if broken_ids:
            broken_count = mark_zones_broken(sb, broken_ids, current_spot)
            log(f"  Marked {broken_count} zones BROKEN at {current_spot:,.1f}")
    except Exception as e:
        # Non-fatal -- continue with detection even if breach-check failed
        log(f"  Warning: zone breach check failed (non-blocking): {e}")

    # ── Pattern detection (last 10 bars) ──────────────────────────────
    new_patterns_count = 0
    try:
        patterns = detector.detect(
            bars=bars,
            atm_iv=atm_iv,
            htf_zones=htf_zones,
            prior_high=prior_high,
            prior_low=prior_low,
        )

        if patterns:
            new_patterns_count = write_new_zones(sb, patterns)
            for p in patterns:
                log(f"  NEW ZONE: {p.pattern_type} {p.ict_tier} "
                    f"mtf={p.mtf_context} zone={p.zone_low:,.0f}-{p.zone_high:,.0f} "
                    f"size={p.ict_size_mult}x")
            log(f"  Written {new_patterns_count} new zones")
        else:
            log(f"  No new patterns detected")
    except Exception as e:
        # Non-fatal per script's design philosophy
        log(f"  Warning: pattern detection failed (non-blocking): {e}")

    # ── 1H zone builder (data-driven, once per hour per symbol) ──────
    # OI-27 fix: check ict_htf_zones directly rather than time-window.
    hourly_written = 0
    hourly_failed = False
    hourly_triggered = False
    if should_rebuild_1h_zones(sb, symbol):
        hourly_triggered = True
        log(f"  Hour rollover detected — building 1H HTF zones...")
        try:
            h_zones = detect_1h_zones(sb, inst_id, symbol, trade_date)
            hourly_written = upsert_zones(sb, h_zones, dry_run=False)
            log(f"  1H zones: {hourly_written} written ({len(h_zones)} detected)")
        except Exception as e:
            hourly_failed = True
            log(f"  Warning: 1H zone build failed (non-blocking): {e}")

    # -- ENH-38v2: write Kelly lots to active ict_zones (real lot cost) -------
    # OI-26 fix (2026-04-21): Replaced build_expiry_index_simple /
    # nearest_expiry_db (which sampled hist_option_bars_1m with hardcoded
    # 2025-2026 date windows) with get_nearest_expiry which reads
    # option_chain_snapshots.expiry_date -- the authoritative value that
    # Dhan already computes including NSE holiday-driven expiry shifts.
    kelly_failed = False
    try:
        # Get days to next expiry for lot cost estimation
        try:
            _next_exp = get_nearest_expiry(sb, symbol)
            _dte_days = (_next_exp - trade_date).days if _next_exp else 2
            # Safety floor: if for any reason DTE came back negative
            # (e.g. stale option_chain_snapshots row from a past expiry),
            # fall back to the conservative 2-day default rather than
            # propagate bad math into Kelly sizing.
            if _dte_days < 0:
                _dte_days = 2
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
        kelly_failed = True
        log(f'  Warning: Kelly lots write failed (non-blocking): {_kelly_err}')
    # -- ENH-38v2 end ----------------------------------------------------------

    log(f"ICT detector complete [{symbol}]")

    # ENH-72: record new-zone writes against the contract. Updates
    # (breach marks, Kelly lot updates) don't count -- they modify
    # existing rows, not create new ones. Contract floor is 0 so
    # even 0 new patterns = contract_met.
    log_handle.record_write("ict_zones", new_patterns_count)

    # Completion notes track ALL activity this cycle for operator triage.
    note_parts = [
        f"bars={len(bars)}",
        f"htf={len(htf_zones)}",
        f"active={len(active_zones)}",
        f"new_patterns={new_patterns_count}",
        f"broken={broken_count}",
    ]
    if hourly_triggered:
        note_parts.append(f"hourly_written={hourly_written}")
    if hourly_failed:
        note_parts.append("hourly_failed=true")
    if kelly_failed:
        note_parts.append("kelly_failed=true")

    return log_handle.complete(notes=" ".join(note_parts))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python detect_ict_patterns_runner.py <SYMBOL>")
        sys.exit(1)

    symbol = sys.argv[1].upper()
    if symbol not in ("NIFTY", "SENSEX"):
        print(f"ERROR: Unknown symbol {symbol}")
        sys.exit(1)

    # ── ENH-72 write-contract declaration ────────────────────────────
    # Contract: floor=0 rows to ict_zones. Most cycles produce ZERO new
    # patterns -- patterns are rare events. contract_met=True whenever
    # the script reaches log.complete() cleanly. Any new-pattern writes
    # are bonus. Updates (breach marks, Kelly updates) are not counted.
    #
    # symbol at construction (NIFTY or SENSEX) -- no set_symbol() needed.
    log_handle = ExecutionLog(
        script_name="detect_ict_patterns_runner.py",
        expected_writes={"ict_zones": 0},
        symbol=symbol,
        notes="ICT pattern detector",
    )

    try:
        rc = main(symbol, log_handle)
        sys.exit(rc)
    except Exception as e:
        # Final safety net -- catch anything that escaped classification
        # in main(). Still exit 0 per non-blocking design.
        print(f"[FATAL] {e}", flush=True)
        try:
            log_handle.exit_with_reason(
                "DATA_ERROR",
                exit_code=0,
                error_message=f"Uncaught exception in main(): {e}",
            )
        except Exception:
            pass  # If ExecutionLog itself is broken, don't compound the failure
        sys.exit(0)  # exit 0 — non-blocking, don't halt runner
