"""fill_2026_04_16_breeze.py — surgical Breeze backfill for the one
missing trading day in BOTH chain tables.

Context:
  S35 diagnosis of TD-S34-NEW-4 confirmed:
    - hist_option_bars_1m: empty post-2026-04-01 (vendor → MERDIAN-ingest tier transition)
    - historical_option_chain_snapshots: dense post-2026-04-01 EXCEPT 2026-04-16
      (both NIFTY and SENSEX returned zero rows on the probe; appears to be a
      genuine MERDIAN ingest outage on that single day)
  ENH-106 v8 dual-source reader handles the rest of the post-Apr window from HOCS,
  but 2026-04-16 needs an external source. ICICI Breeze is the only known retail
  API providing post-expiry full-chain options data (no ATM±N cap unlike Dhan's
  /charts/rollingoption). 3-year lookback, 5000 calls/day cap, 100/min throttle.

Architectural choice (per session discussion):
  - Write the surgical fill into `hist_option_bars_1m` (the canonical historical chain
    table) and NOT into `historical_option_chain_snapshots`. Reason: HOCS is a live-
    capture table populated by `ingest_option_chain_local`; back-dating fills into it
    confuses provenance. hist_option_bars_1m is already the "historical-write" table.
  - With v8 dual-source reader active, the writer will read 2026-04-16 from
    hist_option_bars_1m (pre-boundary... wait, no — 2026-04-16 is POST 2026-04-01
    boundary, so v8 routes to HOCS first and finds nothing). Therefore EITHER:
      (a) The Breeze fill goes into HOCS (matches the v8 routing tier), OR
      (b) The Breeze fill goes into hist_option_bars_1m AND we extend v8 to fall back
          to hist_option_bars_1m when HOCS misses.
  - This script implements (a): write to historical_option_chain_snapshots in the
    HOCS schema shape, source='breeze_backfill_s35'. v8 reader picks it up natively.

Schema mapping (Breeze → historical_option_chain_snapshots):
  Breeze field         HOCS column     Notes
  ─────────────────    ─────────────   ─────────────────────────────────────────
  datetime             ts              parsed IST → UTC via tzlocal-style aware conv
  open/high/low/close  (not stored)    HOCS is point-in-time, not OHLC
  close                ltp             trader-actual at-bar-close
  volume               volume          carry-forward
  open_interest        oi              carry-forward
  (derived: strike)    strike          input parameter, written back
  (derived: expiry)    expiry_date     input parameter, written back
  (derived: right)     option_type     CALL→CE, PUT→PE
  (derived: symbol)    symbol          input parameter
  spot                 spot            from Breeze if returned; else NULL
  source               source          'breeze_backfill_s35'

Rate-limit envelope:
  - 100 calls/min: throttle 0.7s between calls = 85/min ceiling.
  - 5000/day hard cap: this script runs ~150 calls for a single day. Safe.

Idempotency:
  - Pre-check: query HOCS for existing 2026-04-16 rows. If any present, ABORT
    (script is for the empty case only).
  - Write path: bulk INSERT with no ON CONFLICT (HOCS has no natural unique key
    on ts+strike+expiry+symbol+option_type; relies on emptiness).

Auth (env vars; .env loaded if present):
  BREEZE_API_KEY
  BREEZE_API_SECRET
  BREEZE_SESSION_TOKEN  (generated daily via Breeze TOTP flow; valid until midnight IST)

Usage:
  python fill_2026_04_16_breeze.py --dry-run
  python fill_2026_04_16_breeze.py --symbol NIFTY
  python fill_2026_04_16_breeze.py   # both symbols
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

# Optional dotenv
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

UTC = timezone.utc
IST = ZoneInfo("Asia/Kolkata")

TARGET_DATE = date(2026, 4, 16)

# Same canonical strike grids as build_ict_primitives.py
STRIKE_INTERVAL = {"NIFTY": 50.0, "SENSEX": 100.0}

# Strike window padding around the per-symbol zone-band observed in the
# S35 scope query for 2026-04-16. ±15 strikes covers the full retest cohort
# strike spread plus held-strike drift through the trading day.
STRIKE_PAD_BELOW = 15
STRIKE_PAD_ABOVE = 15

# Breeze rate-limit pacing
BREEZE_CALL_INTERVAL_SEC = 0.7  # ~85 calls/min, under 100/min cap

# Source tag on HOCS rows we write
SOURCE_TAG = "breeze_backfill_s35"


# ============================================================================
# Per-symbol scope (derived from S35 scope query 2026-04-16 row)
# ============================================================================

SCOPE = {
    "NIFTY": {
        # From S35 scope query: spot_low_band=23907.4, spot_high_band=24372.7
        # Anchor ATM at midpoint, pad ±15 strikes
        "anchor_spot": 24140.0,  # midpoint, rounded toward 50-grid
        "breeze_stock_code": "NIFTY",
        "exchange_code": "NFO",
    },
    "SENSEX": {
        # From S35 scope query: spot_low_band=77063.4, spot_high_band=78543.1
        # Anchor ATM at midpoint, pad ±15 strikes
        "anchor_spot": 77800.0,
        "breeze_stock_code": "SENSEX",
        "exchange_code": "BFO",
    },
}


# ============================================================================
# Logging
# ============================================================================

def log(msg: str) -> None:
    print(msg, flush=True)


# ============================================================================
# Supabase client
# ============================================================================

def get_supabase_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not url or not key:
        raise SystemExit("[FATAL] SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


# ============================================================================
# Breeze client
# ============================================================================

def get_breeze_client():
    """Construct an authenticated BreezeConnect session.

    Requires `breeze-connect` package installed:
      pip install breeze-connect
    """
    try:
        from breeze_connect import BreezeConnect
    except ImportError:
        raise SystemExit(
            "[FATAL] breeze-connect not installed.\n"
            "        Install with: pip install breeze-connect"
        )

    api_key = os.environ.get("BREEZE_API_KEY")
    api_secret = os.environ.get("BREEZE_API_SECRET")
    session_token = os.environ.get("BREEZE_SESSION_TOKEN")
    if not api_key or not api_secret or not session_token:
        raise SystemExit(
            "[FATAL] BREEZE_API_KEY, BREEZE_API_SECRET, BREEZE_SESSION_TOKEN "
            "must be set in environment.\n"
            "        Generate session token via Breeze login flow each morning."
        )

    bz = BreezeConnect(api_key=api_key)
    bz.generate_session(api_secret=api_secret, session_token=session_token)
    return bz


# ============================================================================
# Expiry calendar lookup (matches build_ict_primitives.py logic)
# ============================================================================

INSTRUMENT_ID_BY_SYMBOL = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}


def load_expiries_around(sb, symbol: str, target: date,
                          window_days: int = 28) -> list[date]:
    """Pull distinct expiry_date values from hist_atm_option_bars_5m within ±window_days of target.

    Returns sorted list of (date) — same calendar source the v7/v8 writer uses,
    so the held-strike PnL recompute will pick the same expiries.
    """
    iid = INSTRUMENT_ID_BY_SYMBOL[symbol]
    lo = target - timedelta(days=window_days)
    hi = target + timedelta(days=window_days)
    expiries: set = set()
    page = 0
    while True:
        offset = page * 1000
        res = (
            sb.table("hist_atm_option_bars_5m")
              .select("expiry_date")
              .eq("instrument_id", iid)
              .gte("expiry_date", lo.isoformat())
              .lte("expiry_date", hi.isoformat())
              .range(offset, offset + 999)
              .execute()
        )
        rows = res.data or []
        for r in rows:
            exp = r.get("expiry_date")
            if exp:
                expiries.add(date.fromisoformat(exp) if isinstance(exp, str) else exp)
        if len(rows) < 1000:
            break
        page += 1
    return sorted(expiries)


def select_relevant_expiries(all_expiries: list[date], target: date) -> list[date]:
    """Pick the expiries that matter for a single-day retest cohort on `target`:
      - nearest weekly >= target (DTE 0-7)
      - next weekly (DTE 7-14) as a safety margin
      - nearest monthly (longest in the 28-day window)
    Deduped, ordered ascending. ≤3 expiries to keep API call count bounded.
    """
    future = [e for e in all_expiries if e >= target]
    if not future:
        return []
    picks = set()
    picks.add(future[0])  # nearest weekly (or same-day expiry)
    if len(future) >= 2:
        picks.add(future[1])
    # Monthly = latest expiry in the window (~28d out)
    if len(future) >= 1:
        picks.add(future[-1])
    return sorted(picks)


# ============================================================================
# Breeze data fetch + HOCS write
# ============================================================================

def fetch_breeze_options(bz, symbol: str, expiry: date, strike: float,
                          right: str, target: date) -> list[dict]:
    """Fetch 1-min OHLC + OI + volume for one (symbol, expiry, strike, right) on target.

    Returns list of records from Breeze API. Empty list on no-data or error.
    """
    # Breeze expects ISO 8601 with Z suffix on dates
    from_dt = datetime.combine(target, datetime.min.time()).replace(
        hour=9, minute=15, tzinfo=IST
    )
    to_dt = datetime.combine(target, datetime.min.time()).replace(
        hour=15, minute=30, tzinfo=IST
    )
    # Breeze convention: send as IST-naive ISO with Z (broker handles tz mapping)
    from_iso = from_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    to_iso = to_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    expiry_iso = datetime.combine(expiry, datetime.min.time()).replace(
        hour=7, tzinfo=UTC
    ).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    try:
        resp = bz.get_historical_data_v2(
            interval="1minute",
            from_date=from_iso,
            to_date=to_iso,
            stock_code=SCOPE[symbol]["breeze_stock_code"],
            exchange_code=SCOPE[symbol]["exchange_code"],
            product_type="options",
            expiry_date=expiry_iso,
            right=right.lower(),  # "call" or "put"
            strike_price=str(int(strike)),
        )
    except Exception as ex:
        log(f"  [!] breeze error {symbol} {expiry} {strike} {right}: {ex}")
        return []

    if not isinstance(resp, dict):
        log(f"  [!] breeze unexpected response shape {symbol} {expiry} {strike} {right}: {type(resp).__name__}")
        return []
    if resp.get("Status") and resp.get("Status") != 200:
        log(f"  [!] breeze Status={resp.get('Status')} Error={resp.get('Error')} "
            f"{symbol} {expiry} {strike} {right}")
        return []

    data = resp.get("Success") or []
    if not isinstance(data, list):
        return []
    return data


def breeze_records_to_hocs_rows(records: list[dict], symbol: str, expiry: date,
                                  strike: float, opt_type: str) -> list[dict]:
    """Convert Breeze 1-min OHLC records to HOCS-shaped rows for INSERT.

    Each Breeze record is a 1-min bar. We store ONE HOCS row per Breeze bar at
    the bar's IST 1-min boundary, converted to UTC, with close as ltp.
    """
    out: list[dict] = []
    for rec in records:
        dt_raw = rec.get("datetime")
        close = rec.get("close")
        if dt_raw is None or close is None:
            continue
        # Breeze returns IST naive strings like "2024-05-20 09:15:00"
        try:
            if isinstance(dt_raw, str):
                # Try ISO first, then space-separated
                try:
                    dt_naive = datetime.fromisoformat(dt_raw.replace("T", " ").rstrip("Z"))
                except ValueError:
                    dt_naive = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M:%S")
            elif isinstance(dt_raw, datetime):
                dt_naive = dt_raw.replace(tzinfo=None)
            else:
                continue
            ts_utc = dt_naive.replace(tzinfo=IST).astimezone(UTC)
        except Exception:
            continue

        oi = rec.get("open_interest") or rec.get("OI") or rec.get("oi")
        vol = rec.get("volume") or rec.get("Volume") or rec.get("vol")
        try:
            ltp = float(close)
            oi_val = int(oi) if oi is not None else None
            vol_val = int(vol) if vol is not None else None
        except (ValueError, TypeError):
            continue

        out.append({
            "ts": ts_utc.isoformat(),
            "symbol": symbol,
            "expiry_date": expiry.isoformat(),
            "strike": float(strike),
            "option_type": opt_type,
            "ltp": ltp,
            "oi": oi_val,
            "volume": vol_val,
            "source": SOURCE_TAG,
            # The remaining HOCS columns (bid, ask, iv, delta, gamma, theta, vega, spot,
            # dte, raw) are LEFT NULL — Breeze 1m OHLC endpoint does not return them.
            # ENH-106 v8 only needs ltp for held-strike PnL; downstream gamma layer
            # consumers (compute_gamma_metrics_local) will skip rows lacking the greek
            # fields, which is correct: live capture is the canonical source for those.
        })
    return out


def pre_flight_hocs_emptiness(sb) -> None:
    """Refuse to run if HOCS already has data for 2026-04-16 on either symbol."""
    for symbol in ("NIFTY", "SENSEX"):
        res = (
            sb.table("historical_option_chain_snapshots")
              .select("ts", count="exact")
              .eq("symbol", symbol)
              .gte("ts", "2026-04-16T00:00:00+00:00")
              .lt("ts", "2026-04-17T00:00:00+00:00")
              .limit(1)
              .execute()
        )
        n = res.count if hasattr(res, "count") and res.count is not None else len(res.data or [])
        if n > 0:
            raise SystemExit(
                f"[ABORT] HOCS already has {n} rows for {symbol} on 2026-04-16.\n"
                f"        Script is for the empty case only. Inspect and delete first if intentional."
            )


def run(symbol_filter: Optional[str], dry_run: bool) -> int:
    sb = get_supabase_client()
    if not dry_run:
        pre_flight_hocs_emptiness(sb)
        log("[pre-flight] HOCS confirmed empty for 2026-04-16 on both symbols")

    bz = get_breeze_client() if not dry_run else None

    symbols = [symbol_filter] if symbol_filter else list(SCOPE.keys())
    total_calls = 0
    total_rows = 0

    for symbol in symbols:
        if symbol not in SCOPE:
            log(f"[!] unknown symbol {symbol}; skipping")
            continue
        cfg = SCOPE[symbol]
        grid = STRIKE_INTERVAL[symbol]
        anchor_atm = round(cfg["anchor_spot"] / grid) * grid
        strikes = [
            anchor_atm + (i * grid)
            for i in range(-STRIKE_PAD_BELOW, STRIKE_PAD_ABOVE + 1)
        ]
        log(f"\n=== {symbol}  anchor_atm={anchor_atm}  strikes={strikes[0]}..{strikes[-1]} "
            f"({len(strikes)} strikes) ===")

        all_expiries = load_expiries_around(sb, symbol, TARGET_DATE)
        expiries = select_relevant_expiries(all_expiries, TARGET_DATE)
        log(f"  expiry calendar yielded {len(all_expiries)} total; selected {len(expiries)}: {expiries}")
        if not expiries:
            log(f"  [!] no expiries available for {symbol} around {TARGET_DATE}; skipping")
            continue

        for expiry in expiries:
            for opt_type, right in [("CE", "call"), ("PE", "put")]:
                expected_calls_remaining = (
                    (len(expiries) - expiries.index(expiry)) * 2 - (1 if right == "call" else 0)
                ) * len(strikes)
                log(f"  -- expiry={expiry} {opt_type} ({len(strikes)} strikes) "
                    f"~{expected_calls_remaining} calls remaining in this expiry tier --")

                rows_for_block: list[dict] = []
                for strike in strikes:
                    if dry_run:
                        log(f"    [dry] would fetch {symbol} {expiry} {strike} {right}")
                        total_calls += 1
                        continue

                    recs = fetch_breeze_options(bz, symbol, expiry, strike, right, TARGET_DATE)
                    total_calls += 1
                    if recs:
                        rows = breeze_records_to_hocs_rows(recs, symbol, expiry, strike, opt_type)
                        rows_for_block.extend(rows)
                    time.sleep(BREEZE_CALL_INTERVAL_SEC)

                if rows_for_block and not dry_run:
                    # Batch insert in 500-row chunks
                    for i in range(0, len(rows_for_block), 500):
                        chunk = rows_for_block[i:i + 500]
                        try:
                            sb.table("historical_option_chain_snapshots").insert(chunk).execute()
                        except Exception as ex:
                            log(f"    [!] HOCS insert failed (chunk @{i}): {ex}")
                            break
                    total_rows += len(rows_for_block)
                    log(f"    wrote {len(rows_for_block)} rows to HOCS for "
                        f"{symbol} {expiry} {opt_type}")
                elif not dry_run:
                    log(f"    [!] no data returned for any strike of "
                        f"{symbol} {expiry} {opt_type}")

    log(f"\n[done] {total_calls} breeze calls, {total_rows} HOCS rows written  "
        f"(dry_run={dry_run})")
    if dry_run:
        log(f"       At {BREEZE_CALL_INTERVAL_SEC}s/call, est wallclock = "
            f"{total_calls * BREEZE_CALL_INTERVAL_SEC / 60:.1f} min")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--symbol", choices=["NIFTY", "SENSEX"],
                   help="Limit to one symbol (default: both)")
    p.add_argument("--dry-run", action="store_true",
                   help="Plan only; no API calls, no DB writes")
    args = p.parse_args()
    return run(args.symbol, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
