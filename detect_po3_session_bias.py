#!/usr/bin/env python3
"""
detect_po3_session_bias.py  —  ENH-75: PO3 Live Session Bias Detection

Scheduled: MERDIAN_PO3_SessionBias_1005  (Mon-Fri 10:05 IST)

Reads:
  hist_spot_bars_5m      — prior session PDH / PDL / prev_close
  market_spot_snapshots  — today OPEN-window 1m ticks  →  5m bars + open_0915

Writes:
  po3_session_state      — UPSERT one row per symbol (UNIQUE symbol + trade_date)
  script_execution_log   — ENH-71 write-contract instrumentation

NOTE: market_spot_session_markers is NOT used — live column names diverge from
documentation (open_0915 → open_0915_ts in production). All required values
(open_0915, gap_open_pct) are derived directly from hist_spot_bars_5m +
market_spot_snapshots.

Detection rules (Exp 35C filtered config):
  PDH sweep  →  PO3_BEARISH
    * wick >= 0.05% above PDH    (bar_high > pdh * 1.0005)
    * closes back >= 0.10% below PDH within 6 bars  (close < pdh * 0.999)
    * gap-up context: open_0915 >= pdh * 0.999
    * gap  0 < gap_open_pct < 0.5%   (positive gap-up, not a large breakout)
    * sweep depth NOT in 0.10-0.20%  (ambiguous zone -> 50% WR)
    * reversal speed != 2 bars       (T+2 = 40% WR danger zone)
    * FIRST sweep bar only
  PDL sweep  ->  PO3_BULLISH: mirror logic (depth >= 0.10%)
  Default:   PO3_NONE

MERDIAN rules enforced:
  Rule 15: Supabase hard-cap 1000 rows/request  -- page_size = 1000
  Rule 16: hist_spot_bars_5m.bar_ts is IST stored as +00:00
           -> use replace(tzinfo=None), NOT astimezone(IST)
  ENH-71:  script_execution_log write-contract row on every exit
"""

import argparse
import logging
import os
import sys
from collections import defaultdict
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client, Client

# ------------------------------------------------------------------ constants

SCRIPT_NAME       = "detect_po3_session_bias"
SCRIPT_VERSION    = "v1.0"
DETECTION_VERSION = "v1.0"
IST = ZoneInfo("Asia/Kolkata")

SYMBOLS = ["NIFTY", "SENSEX"]
INSTRUMENT_IDS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# Exp 35C thresholds
PDH_WICK_MIN_FRAC     = 0.0005   # bar_high must exceed pdh by >= 0.05%
PDH_CLOSE_BACK_FRAC   = 0.001    # close must be >= 0.10% below pdh  (pdh * 0.999)
PDL_WICK_MIN_FRAC     = 0.001    # bar_low must penetrate pdl by >= 0.10%
PDL_CLOSE_BACK_FRAC   = 0.001    # close must be >= 0.10% above pdl  (pdl * 1.001)
GAP_MAX_PCT           = 0.5      # |gap_open_pct| must be < 0.5%
OPEN_NEAR_PDH_FRAC    = 0.999    # open_0915 >= pdh * 0.999  (gap-up context)
OPEN_NEAR_PDL_FRAC    = 1.001    # open_0915 <= pdl * 1.001  (gap-down context)
REVERSAL_MAX_BARS     = 6        # reversal must occur within 6 bars (30 min)
DANGER_REVERSAL_SPEED = 2        # T+2 reversal -> 40% WR -> exclude

# PDH ambiguous depth zone: 0.10% - 0.20% -> 50% WR -> block
PDH_AMBIG_LO_PCT = 0.10
PDH_AMBIG_HI_PCT = 0.20

# Session / window times (naive IST)
SESSION_OPEN_T  = dtime(9, 15)
SESSION_CLOSE_T = dtime(15, 30)

# ------------------------------------------------------------------- logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s -- %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(SCRIPT_NAME)


# ----------------------------------------------------------- Supabase helpers

def _supabase() -> Client:
    # Explicit path -- matches all MERDIAN scripts (env_file in merdian_reference.json)
    load_dotenv(Path(__file__).resolve().parent / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not in environment. "
            "Check .env at " + str(Path(__file__).resolve().parent / ".env")
        )
    return create_client(url, key)


def _paginate(sb: Client, table: str, filters: list,
              select: str = "*", page_size: int = 1000) -> list:
    """Rule 15: Supabase hard-cap = 1000 rows/request. Always paginate."""
    offset, all_rows = 0, []
    while True:
        q = sb.table(table).select(select)
        for method, col, val in filters:
            q = getattr(q, method)(col, val)
        batch = q.range(offset, offset + page_size - 1).execute().data
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return all_rows


# ------------------------------------------------------------ data fetchers

def get_prior_session(
    sb: Client, symbol: str, prior_date: date
) -> "tuple[float | None, float | None, float | None]":
    """
    Fetch PDH, PDL, prev_close from hist_spot_bars_5m for prior_date.
    Returns (pdh, pdl, prev_close) or (None, None, None).

    Rule 16: bar_ts is IST stored as +00:00 label.
             Use replace(tzinfo=None) to treat as naive IST directly.
             Do NOT astimezone(IST) -- that adds 5:30 and shifts all bars.

    prev_close = close of last session bar.
    Both PDH/PDL and prev_close come from here so we never need
    market_spot_session_markers (whose column names differ from docs).
    """
    inst_id = INSTRUMENT_IDS[symbol]
    rows = _paginate(
        sb, "hist_spot_bars_5m",
        filters=[("eq", "instrument_id", inst_id),
                 ("eq", "trade_date",    prior_date.isoformat())],
        select="bar_ts,high,low,close",
    )
    if not rows:
        log.warning(f"[{symbol}] hist_spot_bars_5m: 0 rows for {prior_date}")
        return None, None, None

    session_bars = []
    for row in rows:
        try:
            dt_naive = datetime.fromisoformat(row["bar_ts"]).replace(tzinfo=None)
        except Exception:
            continue
        if SESSION_OPEN_T <= dt_naive.time() <= SESSION_CLOSE_T:
            session_bars.append((
                dt_naive,
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
            ))

    if not session_bars:
        log.warning(f"[{symbol}] No session-hour bars after time filter for {prior_date}")
        return None, None, None

    pdh        = max(b[1] for b in session_bars)
    pdl        = min(b[2] for b in session_bars)
    prev_close = max(session_bars, key=lambda b: b[0])[3]  # close of last bar

    log.info(f"[{symbol}] PDH={pdh:.2f}  PDL={pdl:.2f}  prev_close={prev_close:.2f}  "
             f"({prior_date}, {len(session_bars)} session bars)")
    return pdh, pdl, prev_close


def derive_gap_context(
    ticks: list, prev_close: float
) -> "tuple[float | None, float | None]":
    """
    Derive open_0915 and gap_open_pct from the first OPEN-window tick + prev_close.
    Avoids market_spot_session_markers entirely.
    Returns (open_0915, gap_open_pct) or (None, None).
    """
    if not ticks or not prev_close:
        return None, None
    open_0915    = ticks[0]["spot"]
    gap_open_pct = (open_0915 - prev_close) / prev_close * 100
    log.info(f"open_0915={open_0915:.2f}  prev_close={prev_close:.2f}  "
             f"gap_open_pct={gap_open_pct:+.4f}%")
    return open_0915, gap_open_pct


def get_open_window_ticks(sb: Client, symbol: str, today_ist: date) -> list:
    """
    Fetch 1m spot ticks for OPEN window (09:15-10:00 IST) from market_spot_snapshots.
    market_spot_snapshots.ts is TRUE UTC (live capture -- Rule 16 does NOT apply here).
    09:15 IST = 03:45 UTC  /  10:00 IST = 04:30 UTC.
    Returns list of {ts_ist: datetime (aware IST), spot: float}, sorted asc.
    """
    utc_open = datetime(today_ist.year, today_ist.month, today_ist.day, 3, 45, 0)
    utc_end  = datetime(today_ist.year, today_ist.month, today_ist.day, 4, 30, 0)

    rows = _paginate(
        sb, "market_spot_snapshots",
        filters=[("eq",  "symbol", symbol),
                 ("gte", "ts",     utc_open.strftime("%Y-%m-%dT%H:%M:%SZ")),
                 ("lt",  "ts",     utc_end.strftime("%Y-%m-%dT%H:%M:%SZ"))],
        select="ts,spot",
    )
    if not rows:
        log.warning(f"[{symbol}] No OPEN-window ticks in market_spot_snapshots for {today_ist}")
        return []

    ticks = []
    for row in rows:
        try:
            ts_utc = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
            ticks.append({"ts_ist": ts_utc.astimezone(IST),
                          "spot":   float(row["spot"])})
        except Exception as exc:
            log.debug(f"[{symbol}] Tick parse error: {exc}")
    ticks.sort(key=lambda x: x["ts_ist"])
    log.info(f"[{symbol}] {len(ticks)} OPEN-window ticks fetched")
    return ticks


# ------------------------------------------------------------- 5m bar builder

def build_5m_bars(ticks: list) -> list:
    """
    Aggregate 1m spot ticks into 5m OHLC bars.
    Returns list of {bar_ts_ist: datetime (naive IST), open, high, low, close}
    sorted ascending.
    """
    buckets: dict = defaultdict(list)
    for tick in ticks:
        ts = tick["ts_ist"].replace(tzinfo=None)
        minute_floor = (ts.minute // 5) * 5
        bucket_ts = ts.replace(minute=minute_floor, second=0, microsecond=0)
        buckets[bucket_ts].append(tick["spot"])

    bars = []
    for bucket_ts in sorted(buckets.keys()):
        spots = buckets[bucket_ts]
        if spots:
            bars.append({
                "bar_ts_ist": bucket_ts,
                "open":  spots[0],
                "high":  max(spots),
                "low":   min(spots),
                "close": spots[-1],
            })
    log.info(f"Built {len(bars)} 5m bars from {len(ticks)} ticks")
    return bars


# ----------------------------------------------------------- sweep detectors

def _detect_first_sweep_bear(bars: list, pdh: float):
    """
    Find FIRST 5m bar with wick above PDH, check for close-back within
    REVERSAL_MAX_BARS bars.
    Returns (found, sweep_bar, reversal_speed, sweep_depth_pct).
    Per Exp 35C 'first sweep only': if first wick bar doesn't reverse -> (False, ...)
    """
    for i, bar in enumerate(bars):
        wick_frac = (bar["high"] - pdh) / pdh
        if wick_frac < PDH_WICK_MIN_FRAC:
            continue

        limit = min(i + REVERSAL_MAX_BARS, len(bars))
        for j in range(i, limit):
            if bars[j]["close"] < pdh * (1.0 - PDH_CLOSE_BACK_FRAC):
                return True, bar, j - i, wick_frac * 100

        log.info(f"BEAR wick at bar {i} ({bar['bar_ts_ist'].time()}) "
                 f"no reversal within {REVERSAL_MAX_BARS} bars -> PO3_NONE")
        return False, None, None, None

    return False, None, None, None


def _detect_first_sweep_bull(bars: list, pdl: float):
    """Mirror of _detect_first_sweep_bear for PDL (bullish sweep)."""
    for i, bar in enumerate(bars):
        wick_frac = (pdl - bar["low"]) / pdl
        if wick_frac < PDL_WICK_MIN_FRAC:
            continue

        limit = min(i + REVERSAL_MAX_BARS, len(bars))
        for j in range(i, limit):
            if bars[j]["close"] > pdl * (1.0 + PDL_CLOSE_BACK_FRAC):
                return True, bar, j - i, wick_frac * 100

        log.info(f"BULL wick at bar {i} ({bar['bar_ts_ist'].time()}) "
                 f"no reversal within {REVERSAL_MAX_BARS} bars -> PO3_NONE")
        return False, None, None, None

    return False, None, None, None


# --------------------------------------------------------------- classifier

def classify_session(bars: list, pdh: float, pdl: float,
                     open_0915: float, gap_open_pct: float) -> dict:
    """Apply full Exp 35C filter set. Returns classification dict."""
    result = {
        "po3_session_bias":  "PO3_NONE",
        "po3_sweep_time":    None,
        "pdh_used":          pdh,
        "pdl_used":          pdl,
        "gap_open_pct_used": gap_open_pct,
        "sweep_bar_high":    None,
        "sweep_bar_low":     None,
        "sweep_depth_pct":   None,
        "reversal_bar_idx":  None,
        "skip_reason":       None,
    }

    # -- BEAR check ---------------------------------------------------------
    bear_found, b_bar, b_speed, b_depth = _detect_first_sweep_bear(bars, pdh)
    if bear_found:
        skip = None
        if open_0915 < pdh * OPEN_NEAR_PDH_FRAC:
            skip = (f"gap_context_fail: open_0915={open_0915:.2f} < "
                    f"pdh*{OPEN_NEAR_PDH_FRAC}={pdh * OPEN_NEAR_PDH_FRAC:.2f}")
        elif not (0.0 < gap_open_pct < GAP_MAX_PCT):
            skip = f"gap_size_fail: gap={gap_open_pct:+.4f}% not in (0, {GAP_MAX_PCT})"
        elif PDH_AMBIG_LO_PCT <= b_depth <= PDH_AMBIG_HI_PCT:
            skip = (f"depth_ambiguous: {b_depth:.4f}% "
                    f"in [{PDH_AMBIG_LO_PCT}, {PDH_AMBIG_HI_PCT}]%")
        elif b_speed == DANGER_REVERSAL_SPEED:
            skip = f"t2_reversal: speed={b_speed} (40% WR danger zone)"

        if skip:
            log.info(f"BEAR sweep FILTERED -- {skip}")
            result["skip_reason"] = skip
        else:
            result.update({
                "po3_session_bias": "PO3_BEARISH",
                "po3_sweep_time":   b_bar["bar_ts_ist"].isoformat(),
                "sweep_bar_high":   b_bar["high"],
                "sweep_bar_low":    b_bar["low"],
                "sweep_depth_pct":  b_depth,
                "reversal_bar_idx": b_speed,
            })
            log.info(f"PO3_BEARISH confirmed  bar@{b_bar['bar_ts_ist'].time()}  "
                     f"high={b_bar['high']:.2f}  depth={b_depth:.4f}%  T+{b_speed}")
            return result

    # -- BULL check ---------------------------------------------------------
    bull_found, u_bar, u_speed, u_depth = _detect_first_sweep_bull(bars, pdl)
    if bull_found:
        skip = None
        if open_0915 > pdl * OPEN_NEAR_PDL_FRAC:
            skip = (f"gap_context_fail: open_0915={open_0915:.2f} > "
                    f"pdl*{OPEN_NEAR_PDL_FRAC}={pdl * OPEN_NEAR_PDL_FRAC:.2f}")
        elif not (-GAP_MAX_PCT < gap_open_pct < 0.0):
            skip = f"gap_size_fail: gap={gap_open_pct:+.4f}% not in (-{GAP_MAX_PCT}, 0)"
        elif u_speed == DANGER_REVERSAL_SPEED:
            skip = f"t2_reversal: speed={u_speed} (40% WR danger zone)"

        if skip:
            log.info(f"BULL sweep FILTERED -- {skip}")
            result["skip_reason"] = skip
        else:
            result.update({
                "po3_session_bias": "PO3_BULLISH",
                "po3_sweep_time":   u_bar["bar_ts_ist"].isoformat(),
                "sweep_bar_high":   u_bar["high"],
                "sweep_bar_low":    u_bar["low"],
                "sweep_depth_pct":  u_depth,
                "reversal_bar_idx": u_speed,
            })
            log.info(f"PO3_BULLISH confirmed  bar@{u_bar['bar_ts_ist'].time()}  "
                     f"low={u_bar['low']:.2f}  depth={u_depth:.4f}%  T+{u_speed}")
            return result

    log.info("PO3_NONE -- no qualifying sweep in OPEN window")
    return result


# ------------------------------------------------------------ ExecutionLog

def _write_exec_log(sb: Client, exit_code: int, exit_reason: str,
                    actual_writes: dict, dry_run: bool) -> None:
    """ENH-71 write-contract instrumentation."""
    n_written    = sum(v for v in actual_writes.values() if isinstance(v, int))
    contract_met = (not dry_run) and (n_written >= len(SYMBOLS))
    try:
        sb.table("script_execution_log").insert({
            "script_name":     SCRIPT_NAME,
            "host":            "local",
            "exit_code":       exit_code,
            "exit_reason":     exit_reason,
            "contract_met":    contract_met,
            "actual_writes":   actual_writes,
            "expected_writes": {"po3_session_state": len(SYMBOLS)},

        }).execute()
    except Exception as exc:
        log.warning(f"ExecutionLog write failed (non-fatal): {exc}")


# ------------------------------------------------------------------------ main

def main(dry_run: bool = False, symbols: list = None) -> int:
    if symbols is None:
        symbols = SYMBOLS

    sb = _supabase()
    now_ist   = datetime.now(IST)
    today_ist = now_ist.date()
    prefix    = "[DRY RUN] " if dry_run else ""

    log.info(f"{prefix}ENH-75 PO3 session bias detection  |  {today_ist}  "
             f"|  {now_ist.strftime('%H:%M:%S')} IST")

    actual_writes: dict = {}

    for symbol in symbols:
        log.info(f"-- {symbol} ----------------------------------------")

        # Idempotency
        if not dry_run:
            existing = (sb.table("po3_session_state")
                          .select("po3_session_bias")
                          .eq("symbol", symbol)
                          .eq("trade_date", today_ist.isoformat())
                          .execute().data)
            if existing:
                log.info(f"[{symbol}] Already written today: "
                         f"{existing[0]['po3_session_bias']}  (idempotent skip)")
                actual_writes[symbol] = 0
                continue

        # Prior session: try up to 5 trading days back
        pdh, pdl, prev_close = None, None, None
        for days_back in range(1, 6):
            prior_date = today_ist - timedelta(days=days_back)
            pdh, pdl, prev_close = get_prior_session(sb, symbol, prior_date)
            if pdh is not None:
                break

        # OPEN-window ticks (always needed even if PDH/PDL missing)
        ticks = get_open_window_ticks(sb, symbol, today_ist)
        bars  = build_5m_bars(ticks) if ticks else []

        if pdh is None:
            log.error(f"[{symbol}] Cannot determine PDH/PDL -- writing PO3_NONE")
            result = {"po3_session_bias": "PO3_NONE", "po3_sweep_time": None,
                      "pdh_used": None, "pdl_used": None, "gap_open_pct_used": None,
                      "sweep_bar_high": None, "sweep_bar_low": None,
                      "sweep_depth_pct": None, "reversal_bar_idx": None,
                      "skip_reason": "no_pdh"}
        else:
            open_0915, gap_open_pct = derive_gap_context(ticks, prev_close)

            if bars and open_0915 is not None and gap_open_pct is not None:
                result = classify_session(bars, pdh, pdl, open_0915, gap_open_pct)
            else:
                reason = "no_bars" if not bars else "no_gap_context"
                log.warning(f"[{symbol}] Defaulting to PO3_NONE ({reason})")
                result = {"po3_session_bias": "PO3_NONE", "po3_sweep_time": None,
                          "pdh_used": pdh, "pdl_used": pdl,
                          "gap_open_pct_used": gap_open_pct,
                          "sweep_bar_high": None, "sweep_bar_low": None,
                          "sweep_depth_pct": None, "reversal_bar_idx": None,
                          "skip_reason": reason}

        bias = result["po3_session_bias"]

        if dry_run:
            log.info(f"[DRY RUN] {symbol}/{today_ist} -> {bias}  "
                     f"(depth={result['sweep_depth_pct']}, "
                     f"speed=T+{result['reversal_bar_idx']}, "
                     f"skip={result.get('skip_reason')})")
            actual_writes[symbol] = 0
            continue

        # Upsert
        row = {
            "trade_date":         today_ist.isoformat(),
            "symbol":             symbol,
            "po3_session_bias":   result["po3_session_bias"],
            "po3_sweep_time":     result.get("po3_sweep_time"),
            "pdh_used":           result.get("pdh_used"),
            "pdl_used":           result.get("pdl_used"),
            "gap_open_pct_used":  result.get("gap_open_pct_used"),
            "sweep_bar_high":     result.get("sweep_bar_high"),
            "sweep_bar_low":      result.get("sweep_bar_low"),
            "sweep_depth_pct":    result.get("sweep_depth_pct"),
            "reversal_bar_idx":   result.get("reversal_bar_idx"),
            "skip_reason":        result.get("skip_reason"),
            "detection_version":  DETECTION_VERSION,
        }
        try:
            sb.table("po3_session_state").upsert(
                row, on_conflict="symbol,trade_date"
            ).execute()
            log.info(f"[{symbol}] UPSERTED -> {bias}")
            actual_writes[symbol] = 1
        except Exception as exc:
            log.error(f"[{symbol}] Upsert failed: {exc}")
            actual_writes[symbol] = 0

    # ExecutionLog
    n_ok  = sum(1 for v in actual_writes.values() if v and v > 0)
    n_exp = sum(1 for v in actual_writes.values() if v != 0)
    exit_code   = 0 if (dry_run or n_ok >= max(n_exp, 1)) else 1
    exit_reason = "SUCCESS" if exit_code == 0 else "PARTIAL_FAIL"
    _write_exec_log(sb, exit_code, exit_reason, actual_writes, dry_run)

    log.info(f"{prefix}Done  exit_code={exit_code}  writes={actual_writes}")
    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ENH-75: PO3 Live Session Bias Detection"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Detect but do NOT write to po3_session_state.")
    parser.add_argument("--symbol", choices=["NIFTY", "SENSEX"],
                        help="Run for one symbol only (default: both).")
    args   = parser.parse_args()
    syms   = [args.symbol] if args.symbol else None
    sys.exit(main(dry_run=args.dry_run, symbols=syms))
