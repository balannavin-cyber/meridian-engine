"""fill_2026_04_16_breeze.py v2 — Breeze surgical fill for 2026-04-16 gap.

v2 changes from v1 (delivered earlier in S35):
  - load_expiries_around() now UNIONs vendor (hist_atm_option_bars_5m) +
    MERDIAN-ingest (historical_option_chain_snapshots via get_hocs_distinct_expiries RPC)
    calendars. v1 only queried vendor side which caps at 2026-04-02/04-07 and yields
    zero expiries for 2026-04-16; v2 picks up the HOCS expiries (2026-04-16, 2026-04-23,
    2026-04-30 are all in HOCS per S35 audit).
  - Prerequisite: v8.2 RPC `get_hocs_distinct_expiries(text)` must be deployed.

Context (unchanged from v1):
  S35 diagnosis confirmed both chain tables are empty on 2026-04-16 (single-day MERDIAN
  ingest outage). ICICI Breeze is the only known retail API with post-expiry full-chain
  options data (no ATM±N cap). 3-year lookback, 5000 calls/day cap, 100/min throttle.
  Writes into historical_option_chain_snapshots (matches v8 post-boundary tier routing).

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
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

UTC = timezone.utc
IST = ZoneInfo("Asia/Kolkata")

TARGET_DATE = date(2026, 4, 16)

STRIKE_INTERVAL = {"NIFTY": 50.0, "SENSEX": 100.0}
STRIKE_PAD_BELOW = 15
STRIKE_PAD_ABOVE = 15
BREEZE_CALL_INTERVAL_SEC = 0.7
SOURCE_TAG = "breeze_backfill_s35"
RUN_ID = str(uuid.uuid4())  # v3: one run_id per script invocation; HOCS run_id is NOT NULL

INSTRUMENT_ID_BY_SYMBOL = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

SCOPE = {
    "NIFTY": {
        "anchor_spot": 24140.0,
        "breeze_stock_code": "NIFTY",
        "exchange_code": "NFO",
    },
    "SENSEX": {
        "anchor_spot": 77800.0,
        "breeze_stock_code": "SENSEX",
        "exchange_code": "BFO",
    },
}


def log(msg: str) -> None:
    print(msg, flush=True)


def get_supabase_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not url or not key:
        raise SystemExit("[FATAL] SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


def get_breeze_client():
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
# v2 — Expiry calendar lookup with vendor + HOCS UNION
# ============================================================================

def load_expiries_around(sb, symbol: str, target: date,
                          window_days: int = 28) -> list[date]:
    """v2: UNION vendor (hist_atm_option_bars_5m) + MERDIAN-ingest (HOCS via RPC) calendars.

    For 2026-04-16, the vendor calendar caps at 2026-04-02 (SENSEX) / 2026-04-07 (NIFTY)
    so it yields no in-window expiries. HOCS calendar covers 2026-03-19..2026-05-27 and
    is queried via the v8.2 RPC `get_hocs_distinct_expiries(symbol)` (~325ms per symbol).

    Returns sorted list of date objects within ±window_days of target.
    """
    lo = target - timedelta(days=window_days)
    hi = target + timedelta(days=window_days)
    expiries: set = set()

    # --- Source 1: vendor (hist_atm_option_bars_5m, instrument_id-keyed) ---
    iid = INSTRUMENT_ID_BY_SYMBOL[symbol]
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
    vendor_count = len(expiries)

    # --- Source 2: HOCS via v8.2 RPC ---
    hocs_added = 0
    try:
        rpc_res = sb.rpc("get_hocs_distinct_expiries", {"_symbol": symbol}).execute()
        for r in rpc_res.data or []:
            exp = r.get("expiry_date") if isinstance(r, dict) else None
            if exp is None:
                continue
            d = date.fromisoformat(exp) if isinstance(exp, str) else exp
            if lo <= d <= hi:
                if d not in expiries:
                    hocs_added += 1
                expiries.add(d)
    except Exception as ex:
        log(f"  [!] HOCS RPC failed for {symbol}: {ex}  (proceeding with vendor-only)")

    log(f"  [v2] expiry calendar {symbol}: vendor={vendor_count} + hocs_in_window={hocs_added} "
        f"= total={len(expiries)} distinct in [{lo}, {hi}]")
    return sorted(expiries)


def select_relevant_expiries(all_expiries: list[date], target: date) -> list[date]:
    """Pick the expiries that matter for a single-day retest cohort on `target`:
      - nearest weekly >= target
      - next weekly
      - nearest monthly (longest in window)
    Up to 3 expiries to bound API calls.
    """
    future = [e for e in all_expiries if e >= target]
    if not future:
        return []
    picks = set()
    picks.add(future[0])
    if len(future) >= 2:
        picks.add(future[1])
    if len(future) >= 1:
        picks.add(future[-1])
    return sorted(picks)


def fetch_breeze_options(bz, symbol: str, expiry: date, strike: float,
                          right: str, target: date) -> list[dict]:
    """Fetch 1-min OHLC + OI + volume for one (symbol, expiry, strike, right) on target."""
    from_dt = datetime.combine(target, datetime.min.time()).replace(
        hour=9, minute=15, tzinfo=IST
    )
    to_dt = datetime.combine(target, datetime.min.time()).replace(
        hour=15, minute=30, tzinfo=IST
    )
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
            right=right.lower(),
            strike_price=str(int(strike)),
        )
    except Exception as ex:
        log(f"  [!] breeze error {symbol} {expiry} {strike} {right}: {ex}")
        return []

    if not isinstance(resp, dict):
        log(f"  [!] breeze unexpected shape {symbol} {expiry} {strike} {right}: {type(resp).__name__}")
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
    """Convert Breeze 1-min OHLC records to HOCS-shaped rows for INSERT."""
    out: list[dict] = []
    for rec in records:
        dt_raw = rec.get("datetime")
        close = rec.get("close")
        if dt_raw is None or close is None:
            continue
        try:
            if isinstance(dt_raw, str):
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
            "run_id": RUN_ID,
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
                f"        Inspect and delete first if re-fill intended."
            )


def run(symbol_filter: Optional[str], dry_run: bool) -> int:
    sb = get_supabase_client()
    if not dry_run:
        pre_flight_hocs_emptiness(sb)
        log("[pre-flight] HOCS confirmed empty for 2026-04-16 on both symbols")
    log(f"[v3] run_id = {RUN_ID}")

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
        log(f"  selected expiries: {expiries}")
        if not expiries:
            log(f"  [!] no expiries available for {symbol} around {TARGET_DATE}; skipping")
            continue

        for expiry in expiries:
            for opt_type, right in [("CE", "call"), ("PE", "put")]:
                log(f"  -- expiry={expiry} {opt_type} ({len(strikes)} strikes) --")

                rows_for_block: list[dict] = []
                for strike in strikes:
                    if dry_run:
                        total_calls += 1
                        continue

                    recs = fetch_breeze_options(bz, symbol, expiry, strike, right, TARGET_DATE)
                    total_calls += 1
                    if recs:
                        rows = breeze_records_to_hocs_rows(recs, symbol, expiry, strike, opt_type)
                        rows_for_block.extend(rows)
                    time.sleep(BREEZE_CALL_INTERVAL_SEC)

                if rows_for_block and not dry_run:
                    inserted_this_block = 0
                    block_failed = False
                    for i in range(0, len(rows_for_block), 500):
                        chunk = rows_for_block[i:i + 500]
                        try:
                            sb.table("historical_option_chain_snapshots").insert(chunk).execute()
                            inserted_this_block += len(chunk)
                        except Exception as ex:
                            log(f"    [!] HOCS insert failed (chunk @{i}): {ex}")
                            block_failed = True
                            break
                    total_rows += inserted_this_block
                    if block_failed:
                        log(f"    [!] HOCS write FAILED after {inserted_this_block} of "
                            f"{len(rows_for_block)} rows for {symbol} {expiry} {opt_type}")
                    else:
                        log(f"    wrote {inserted_this_block} rows to HOCS for "
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
    p.add_argument("--symbol", choices=["NIFTY", "SENSEX"])
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    return run(args.symbol, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
