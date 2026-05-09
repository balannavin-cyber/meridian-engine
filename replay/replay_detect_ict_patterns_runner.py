"""
replay.replay_detect_ict_patterns_runner — Replay mirror of detect_ict_patterns_runner.py.

Differences from detect_ict_patterns_runner.py:
  1. Reads hist_spot_bars_1m LIVE filtered by bar_ts < replay_ts (immutable past data;
     strict less-than excludes the in-progress boundary bar).
  2. Reads ict_htf_zones LIVE filtered by replay_date (immutable past data;
     HTF zones are built once at 08:45 IST and don't change intraday).
  3. Reads ict_zones_replay (not ict_zones) for active intraday zone breach checks.
  4. Reads market_state_snapshots_replay for atm_iv (latest at-or-before replay_ts).
  5. Writes ict_zones_replay (new patterns + breach updates + Kelly lot updates).
  6. SKIPS the hourly 1H zone rebuild — HTF zones already live for replay_date,
     don't trigger writes to live ict_htf_zones from replay.
  7. trade_date comes from --replay-ts, not datetime.now().
  8. CLI: --replay-ts, --symbol.
  9. exit_code=1 on errors (NOT 0 non-blocking) — replay should fail loud.

REUSED LIBRARIES (no replay version):
  - detect_ict_patterns.{ICTDetector, Bar, HTFZone}: pure detection logic
  - merdian_utils.{compute_kelly_lots, LOT_SIZES, effective_sizing_capital}: pure
  - capital_tracker LIVE read for Kelly: replay uses today's capital (not historical).
    This is acceptable — replay tests pattern detection logic, not historical capital state.

Live impact: ZERO writes to live. READS from hist_spot_bars_1m, ict_htf_zones,
instruments, capital_tracker (immutable historical reference).

Author: Session 24 (2026-05-09)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client

from detect_ict_patterns import ICTDetector, Bar, HTFZone
from merdian_utils import compute_kelly_lots, LOT_SIZES

from replay.replay_clock import IST, parse_replay_ts, replay_today_ist, to_iso_utc
from replay.replay_execution_log import ExecutionLog


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

PAGE_SIZE = 1_000


def log(msg: str) -> None:
    ts = datetime.now(tz=timezone.utc).astimezone(IST).strftime("%H:%M:%S IST")
    print(f"[{ts}] {msg}", flush=True)


def fetch_with_retry(query_fn, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return query_fn()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            time.sleep(2 ** attempt)


# ============================================================================
# REPLAY: data loaders with replay_ts filtering
# ============================================================================

def load_replay_spot_bars(sb, inst_id: str, replay_date: date, replay_ts: datetime) -> List[Bar]:
    """REPLAY: load hist_spot_bars_1m for replay_date with bar_ts < replay_ts (strict).

    Strict less-than because bar at e.g. 03:45 represents the minute STARTING
    at 03:45 — its data is only complete at 03:46. At replay boundary 03:45,
    we want bars 03:30-03:44 (i.e., bars whose bar_ts < 03:45). This mirrors
    what live saw at the moment it ran the 03:45 cycle.
    """
    all_rows: List[Dict[str, Any]] = []
    offset = 0
    replay_ts_iso = to_iso_utc(replay_ts)
    while True:
        rows = fetch_with_retry(lambda: (
            sb.table("hist_spot_bars_1m")
            .select("bar_ts, trade_date, open, high, low, close")
            .eq("instrument_id", inst_id)
            .eq("trade_date", str(replay_date))
            .eq("is_pre_market", False)
            .lt("bar_ts", replay_ts_iso)
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
        try:
            bars.append(Bar(
                bar_ts=datetime.fromisoformat(r["bar_ts"].replace("Z", "+00:00")),
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                trade_date=date.fromisoformat(r["trade_date"]),
            ))
        except Exception:
            continue
    return bars


def load_prior_session_hl(sb, inst_id: str, replay_date: date):
    """Get prior session high/low — try up to 5 prior days for weekends/holidays."""
    for days_back in range(1, 6):
        d = replay_date - timedelta(days=days_back)
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
            prior_low = min(float(r["low"]) for r in rows)
            return prior_high, prior_low
    return None, None


def load_active_htf_zones(sb, symbol: str, replay_date: date) -> List[HTFZone]:
    """Read ict_htf_zones LIVE for replay_date (immutable past)."""
    rows = fetch_with_retry(lambda: (
        sb.table("ict_htf_zones")
        .select("id, symbol, timeframe, pattern_type, direction, "
                "zone_high, zone_low, status")
        .eq("symbol", symbol)
        .eq("status", "ACTIVE")
        .lte("valid_from", str(replay_date))
        .gte("valid_to", str(replay_date))
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


def load_active_intraday_zones_replay(sb, symbol: str, replay_date: date) -> List[Dict[str, Any]]:
    """REPLAY: read ict_zones_replay for breach checking."""
    rows = fetch_with_retry(lambda: (
        sb.table("ict_zones_replay")
        .select("id, symbol, pattern_type, direction, zone_high, zone_low, "
                "status, detected_at_ts")
        .eq("symbol", symbol)
        .eq("trade_date", str(replay_date))
        .eq("status", "ACTIVE")
        .execute().data
    ))
    return rows


def load_atm_iv_replay(sb, symbol: str, replay_ts: datetime) -> Optional[float]:
    """REPLAY: read market_state_snapshots_replay for atm_iv."""
    try:
        replay_ts_iso = to_iso_utc(replay_ts)
        rows = fetch_with_retry(lambda: (
            sb.table("market_state_snapshots_replay")
            .select("volatility_features")
            .eq("symbol", symbol)
            .lte("ts", replay_ts_iso)
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


def get_nearest_expiry_replay(sb, symbol: str, replay_date: date) -> Optional[date]:
    """REPLAY: get expiry from option_chain_snapshots_replay (not live)."""
    try:
        rows = fetch_with_retry(lambda: (
            sb.table("option_chain_snapshots_replay")
            .select("expiry_date")
            .eq("symbol", symbol)
            .gte("ts", f"{replay_date.isoformat()}T00:00:00Z")
            .lte("ts", f"{replay_date.isoformat()}T23:59:59Z")
            .order("expiry_date", desc=False)
            .limit(1)
            .execute().data
        ))
        if rows and rows[0].get("expiry_date"):
            return date.fromisoformat(rows[0]["expiry_date"])
    except Exception:
        pass
    return None


def load_capital_for_symbol(sb, symbol: str) -> float:
    """Read live capital_tracker. Wall-clock capital is acceptable for replay
    Kelly sizing — we're testing pattern logic, not historical capital state."""
    try:
        cap_resp = fetch_with_retry(lambda: (
            sb.table("capital_tracker")
            .select("capital")
            .eq("symbol", symbol)
            .limit(1)
            .execute()
        ))
        if cap_resp.data:
            return float(cap_resp.data[0]["capital"])
    except Exception:
        pass
    return 200_000.0  # conservative floor


# ============================================================================
# REPLAY: zone writes (all to _replay table)
# ============================================================================

def write_new_zones_replay(sb, patterns: List, replay_date: date) -> int:
    """REPLAY: write detected patterns to ict_zones_replay."""
    if not patterns:
        return 0
    written = 0
    for p in patterns:
        try:
            row = p.to_db_row()
            # Ensure trade_date is replay_date, not wall-clock
            row["trade_date"] = str(replay_date)
            fetch_with_retry(lambda: (
                sb.table("ict_zones_replay")
                .upsert(row, on_conflict="symbol,session_bar_ts,pattern_type")
                .execute()
            ))
            written += 1
        except Exception as e:
            log(f"  Warning: zone write failed ({getattr(p, 'pattern_type', '?')}): {e}")
    return written


def mark_zones_broken_replay(sb, broken_ids: List[str], current_spot: float, replay_ts: datetime) -> int:
    """REPLAY: mark breached zones in ict_zones_replay as BROKEN."""
    if not broken_ids:
        return 0
    now_ts = to_iso_utc(replay_ts)
    marked = 0
    for zone_id in broken_ids:
        try:
            fetch_with_retry(lambda: (
                sb.table("ict_zones_replay")
                .update({
                    "status": "BROKEN",
                    "broken_at_ts": now_ts,
                    "break_price": current_spot,
                    "updated_at": now_ts,
                })
                .eq("id", zone_id)
                .execute()
            ))
            marked += 1
        except Exception as e:
            log(f"  Warning: could not mark zone {zone_id} broken: {e}")
    return marked


def expire_prior_session_zones_replay(sb, symbol: str, replay_date: date) -> None:
    """REPLAY: expire prior-session active zones in ict_zones_replay only."""
    try:
        fetch_with_retry(lambda: (
            sb.table("ict_zones_replay")
            .update({"status": "EXPIRED",
                     "updated_at": datetime.now(tz=timezone.utc).isoformat()})
            .eq("symbol", symbol)
            .lt("trade_date", str(replay_date))
            .eq("status", "ACTIVE")
            .execute()
        ))
    except Exception as e:
        log(f"  Warning: could not expire prior zones in replay: {e}")


# ============================================================================
# Main
# ============================================================================

def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="replay_detect_ict_patterns_runner")
    parser.add_argument("--replay-ts", required=True)
    parser.add_argument("--symbol", required=True, choices=["NIFTY", "SENSEX"])
    return parser.parse_args(argv)


def main(args: argparse.Namespace, log_handle: ExecutionLog) -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return log_handle.exit_with_reason(
            "DEPENDENCY_MISSING", 1,
            error_message="Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY"
        )

    try:
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return log_handle.exit_with_reason(
            "DEPENDENCY_MISSING", 1,
            error_message=f"Supabase client init failed: {e}"
        )

    try:
        replay_ts = parse_replay_ts(args.replay_ts)
    except ValueError as e:
        return log_handle.exit_with_reason(
            "DATA_ERROR", 1, error_message=f"Invalid --replay-ts: {e}"
        )

    symbol = args.symbol.upper()
    replay_date = replay_today_ist(replay_ts)

    log(f"ICT detector REPLAY start [{symbol}] replay_ts={args.replay_ts}")

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
            "DATA_ERROR", 1,
            error_message=f"instruments query failed: {e}"
        )

    if not inst_rows:
        return log_handle.exit_with_reason(
            "DATA_ERROR", 1,
            error_message=f"No instruments row for symbol={symbol}"
        )
    inst_id = inst_rows[0]["id"]

    # Capital for Kelly sizing
    current_capital = load_capital_for_symbol(sb, symbol)

    # ── Session start expire prior zones (first cycle of replay session) ───
    replay_ts_ist = replay_ts.astimezone(IST)
    if replay_ts_ist.hour == 9 and replay_ts_ist.minute < 20:
        expire_prior_session_zones_replay(sb, symbol, replay_date)
        log(f"  Expired prior session zones in replay for {symbol}")

    # ── Load data ─────────────────────────────────────────────────────────
    try:
        bars = load_replay_spot_bars(sb, inst_id, replay_date, replay_ts)
    except Exception as e:
        return log_handle.exit_with_reason(
            "DATA_ERROR", 1,
            error_message=f"load_replay_spot_bars failed: {e}"
        )

    if len(bars) < 10:
        log(f"  Insufficient bars ({len(bars)} < 10) — skipping detection")
        log_handle.record_write("ict_zones_replay", 0)
        return log_handle.complete(
            notes=f"replay_ts={args.replay_ts} bars={len(bars)} insufficient_bars=true"
        )

    try:
        prior_high, prior_low = load_prior_session_hl(sb, inst_id, replay_date)
        htf_zones = load_active_htf_zones(sb, symbol, replay_date)
        active_zones = load_active_intraday_zones_replay(sb, symbol, replay_date)
        atm_iv = load_atm_iv_replay(sb, symbol, replay_ts)
    except Exception as e:
        return log_handle.exit_with_reason(
            "DATA_ERROR", 1,
            error_message=f"supporting data load failed: {e}"
        )

    current_spot = bars[-1].close

    iv_str = f"{atm_iv:.1f}%" if atm_iv else "n/a"
    log(f"  {len(bars)} bars | {len(htf_zones)} HTF zones | "
        f"{len(active_zones)} active zones | spot={current_spot:,.1f} | iv={iv_str}")

    # ── Zone breach checking ──────────────────────────────────────────────
    detector = ICTDetector(symbol=symbol)
    broken_count = 0
    try:
        broken_ids = detector.check_zone_breaches(active_zones, current_spot)
        if broken_ids:
            broken_count = mark_zones_broken_replay(sb, broken_ids, current_spot, replay_ts)
            log(f"  Marked {broken_count} zones BROKEN at {current_spot:,.1f}")
    except Exception as e:
        log(f"  Warning: zone breach check failed (non-blocking): {e}")

    # ── Pattern detection (last 30 bars per TD-060) ───────────────────────
    new_patterns_count = 0
    try:
        patterns = detector.detect(
            bars=bars[-30:],
            atm_iv=atm_iv,
            htf_zones=htf_zones,
            prior_high=prior_high,
            prior_low=prior_low,
        )
        if patterns:
            new_patterns_count = write_new_zones_replay(sb, patterns, replay_date)
            for p in patterns:
                log(f"  NEW ZONE: {p.pattern_type} {getattr(p, 'ict_tier', '?')} "
                    f"mtf={getattr(p, 'mtf_context', '?')} "
                    f"zone={p.zone_low:,.0f}-{p.zone_high:,.0f}")
            log(f"  Written {new_patterns_count} new zones to ict_zones_replay")
        else:
            log(f"  No new patterns detected")
    except Exception as e:
        log(f"  Warning: pattern detection failed (non-blocking): {e}")

    # ── 1H zone rebuild SKIPPED in replay ─────────────────────────────────
    # HTF zones for replay_date are already in live ict_htf_zones (built once
    # at 08:45 IST on the actual trading day). Replay reads them; doesn't rebuild.

    # ── Kelly lots update on active replay zones ──────────────────────────
    kelly_failed = False
    try:
        next_exp = get_nearest_expiry_replay(sb, symbol, replay_date)
        dte_days = (next_exp - replay_date).days if next_exp else 2
        if dte_days < 0:
            dte_days = 2
        atm_iv_pct = atm_iv if atm_iv else 0.0

        lots_t1 = compute_kelly_lots(current_capital, "TIER1", symbol, current_spot, atm_iv_pct, dte_days)
        lots_t2 = compute_kelly_lots(current_capital, "TIER2", symbol, current_spot, atm_iv_pct, dte_days)
        lots_t3 = compute_kelly_lots(current_capital, "TIER3", symbol, current_spot, atm_iv_pct, dte_days)

        fetch_with_retry(lambda: (
            sb.table("ict_zones_replay")
            .update({
                "ict_lots_t1": lots_t1,
                "ict_lots_t2": lots_t2,
                "ict_lots_t3": lots_t3,
            })
            .eq("symbol", symbol)
            .eq("trade_date", str(replay_date))
            .eq("status", "ACTIVE")
            .execute()
        ))

        lot_size = LOT_SIZES.get(symbol, 65)
        log(f"  Kelly lots (lot_size={lot_size}, dte={dte_days}d, "
            f"iv={atm_iv_pct:.1f}%, spot={current_spot:,.0f}) "
            f"T1:{lots_t1} T2:{lots_t2} T3:{lots_t3} "
            f"(capital=INR {current_capital:,.0f})")
    except Exception as e:
        kelly_failed = True
        log(f"  Warning: Kelly lots write failed (non-blocking): {e}")

    log(f"ICT detector REPLAY complete [{symbol}]")

    log_handle.record_write("ict_zones_replay", new_patterns_count)

    note_parts = [
        f"replay_ts={args.replay_ts}",
        f"bars={len(bars)}",
        f"htf={len(htf_zones)}",
        f"active={len(active_zones)}",
        f"new_patterns={new_patterns_count}",
        f"broken={broken_count}",
    ]
    if kelly_failed:
        note_parts.append("kelly_failed=true")

    return log_handle.complete(notes=" ".join(note_parts))


if __name__ == "__main__":
    try:
        args = parse_args(sys.argv[1:])
    except SystemExit:
        raise

    symbol = args.symbol.upper()

    log_handle = ExecutionLog(
        script_name="replay_detect_ict_patterns_runner.py",
        expected_writes={"ict_zones_replay": 0},  # floor=0; patterns are rare
        symbol=symbol,
        notes="ICT pattern detector REPLAY",
    )

    try:
        rc = main(args, log_handle)
        sys.exit(rc)
    except Exception as e:
        print(f"[FATAL] {e}", flush=True)
        try:
            log_handle.exit_with_reason("DATA_ERROR", 1, error_message=f"Uncaught: {e}")
        except Exception:
            pass
        sys.exit(1)