from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.dhan_client import DhanClient
# ENH-71 write-contract layer. ExecutionLog records every invocation to
# script_execution_log with expected vs actual writes, exit_reason, and
# contract_met. Pattern mirrored from capture_spot_1m.py (the V19/V18G
# ENH-71 reference implementation). See docs/MERDIAN_Master_V19.docx
# governance rule `script_execution_log_contract`.
from core.execution_log import ExecutionLog
from core.supabase_client import SupabaseClient
from gamma_engine_retry_utils import retry_call


SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()


UNDERLYING_MAP = {
    "NIFTY": {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I",
        "strike_step": 50,
    },
    "SENSEX": {
        "UnderlyingScrip": 51,
        "UnderlyingSeg": "IDX_I",
        "strike_step": 100,
    },
}


# ── ENH-72 expected-write floors ──────────────────────────────────────────────
# These are FLOORS — minimum row counts below which something is clearly
# broken. They are NOT precise expectations.
#
# Rationale:
#   FULL mode typically returns ~534 (NIFTY) / ~606 (SENSEX) rows per cycle,
#   but natural variation (chain depth, expiry rollover, partial responses)
#   makes a hard 500 threshold produce false contract_met=False rows. We
#   pick 50 as the floor: a chain that returns fewer than 50 rows is
#   broken (Dhan returned almost nothing OR the parser dropped most strikes).
#
#   ATM_ONLY mode uses width_each_side=2 -> 5 strikes × (CE+PE) = 10 rows
#   max in normal conditions. Floor 8 allows for 1 missing CE/PE block in
#   liquid NIFTY/SENSEX chains.
#
#   Trend-based anomaly detection ("FULL was 500 yesterday, 250 today")
#   lives in v_script_execution_health_30m, not here. The contract answers
#   "did the script do its job?", not "is today's count typical?".
EXPECTED_FLOOR = {
    "FULL":     50,
    "ATM_ONLY":  8,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def normalize_mode(mode: str) -> str:
    mode = str(mode or "FULL").strip().upper()
    if mode not in {"FULL", "ATM_ONLY"}:
        raise RuntimeError(f"Unsupported mode: {mode}. Use FULL or ATM_ONLY.")
    return mode


def filter_oc_for_atm_only(
    symbol: str,
    spot: float | None,
    oc: dict[str, Any],
    width_each_side: int = 2,
) -> dict[str, Any]:
    """
    Keep only strikes around ATM.
    width_each_side=2 means:
      ATM-2, ATM-1, ATM, ATM+1, ATM+2
    """
    if spot is None:
        return oc

    strike_keys: list[int] = []
    for strike_key in oc.keys():
        strike_val = to_int(strike_key)
        if strike_val is not None:
            strike_keys.append(strike_val)

    if not strike_keys:
        return oc

    strike_keys = sorted(set(strike_keys))

    atm_strike = min(strike_keys, key=lambda s: abs(s - spot))
    atm_index = strike_keys.index(atm_strike)

    start_index = max(0, atm_index - width_each_side)
    end_index = min(len(strike_keys), atm_index + width_each_side + 1)

    selected_strikes = set(strike_keys[start_index:end_index])

    filtered: dict[str, Any] = {}
    for strike_key, strike_block in oc.items():
        strike_val = to_int(strike_key)
        if strike_val is not None and strike_val in selected_strikes:
            filtered[str(strike_key)] = strike_block

    return filtered


def extract_option_rows(
    symbol: str,
    expiry_date: str,
    snapshot_ts: str,
    run_id: str,
    spot: float | None,
    option_chain_response: dict[str, Any],
    mode: str = "FULL",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    data = option_chain_response.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Option chain response missing dict at key 'data'")

    oc = data.get("oc")
    if not isinstance(oc, dict):
        raise RuntimeError("Option chain response missing dict at key data['oc']")

    mode = normalize_mode(mode)
    if mode == "ATM_ONLY":
        oc = filter_oc_for_atm_only(symbol=symbol, spot=spot, oc=oc, width_each_side=2)

    for strike_key, strike_block in oc.items():
        strike = to_int(strike_key)
        if strike is None:
            continue

        if not isinstance(strike_block, dict):
            continue

        option_key_map = {
            "ce": "CE",
            "pe": "PE",
        }

        for dhan_key, option_type in option_key_map.items():
            option_raw = strike_block.get(dhan_key)
            if not isinstance(option_raw, dict):
                continue

            greeks = option_raw.get("greeks") or {}
            previous_oi = option_raw.get("previous_oi")

            oi = to_int(option_raw.get("oi"))
            oi_change = None
            if oi is not None and previous_oi is not None:
                try:
                    oi_change = int(oi - int(float(previous_oi)))
                except Exception:
                    oi_change = None

            row = {
                "ts": snapshot_ts,
                "symbol": symbol,
                "expiry_date": expiry_date,
                "spot": to_float(spot),
                "strike": strike,
                "option_type": option_type,
                "ltp": to_float(option_raw.get("last_price")),
                "bid": to_float(option_raw.get("top_bid_price")),
                "ask": to_float(option_raw.get("top_ask_price")),
                "oi": oi,
                "oi_change": oi_change,
                "volume": to_int(option_raw.get("volume")),
                "iv": to_float(option_raw.get("implied_volatility")),
                "delta": to_float(greeks.get("delta")),
                "gamma": to_float(greeks.get("gamma")),
                "theta": to_float(greeks.get("theta")),
                "vega": to_float(greeks.get("vega")),
                "raw": option_raw,
                "run_id": run_id,
            }
            rows.append(row)

    return rows


def _is_market_holiday() -> tuple[bool, str]:
    """
    Defense-in-depth holiday check against trading_calendar.

    Returns (is_holiday, today_str_ist).

    The supervisor already calendar-gates the runner, so this is a guard
    against direct manual invocation on a closed day. It MUST fail open:
    if Supabase is unreachable, the script should still run (the runner
    has already done the authoritative gating).
    """
    today_str = str(datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Kolkata")).date())
    if not SUPABASE_URL or not SUPABASE_KEY:
        return (False, today_str)
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/trading_calendar",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Accept": "application/json",
            },
            params={"trade_date": f"eq.{today_str}", "select": "is_open,open_time"},
            timeout=10,
        )
        if r.status_code == 200:
            rows = r.json()
            if rows:
                row = rows[0]
                if (not row.get("is_open", True)) or row.get("open_time") is None:
                    return (True, today_str)
    except Exception as e:
        # Fail open: never block ingest on a calendar-lookup failure.
        print(f"  [WARN] Calendar check failed (proceeding): {e}", file=sys.stderr)
    return (False, today_str)


def _classify_dhan_error(err: Exception) -> str:
    """
    Map a Dhan-side exception to an ExecutionLog reason.

    401 / 'Unauthorized' / 'token invalid' language -> TOKEN_EXPIRED so
    refresh_dhan_token monitoring fires the right alert. Everything else
    -> DATA_ERROR (generic upstream failure).
    """
    msg = str(err)
    auth_hint = (
        "401" in msg
        or "Unauthorized" in msg
        or "Authentication" in msg
        or ("token" in msg.lower() and "invalid" in msg.lower())
    )
    return "TOKEN_EXPIRED" if auth_hint else "DATA_ERROR"


def ingest_symbol(symbol: str, mode: str, log: ExecutionLog) -> int:
    """
    Run the ingest. Returns exit code (0 on success). All exit paths route
    through `log` so script_execution_log always gets a final row.
    """
    symbol = symbol.upper().strip()
    mode = normalize_mode(mode)

    if symbol not in UNDERLYING_MAP:
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"Unsupported symbol: {symbol}. Use NIFTY or SENSEX.",
        )

    underlying = UNDERLYING_MAP[symbol]

    print("=" * 72)
    print("Gamma Engine - Local Python ingest_option_chain")
    print("=" * 72)
    print(f"Symbol: {symbol}")
    print(f"Mode: {mode}")
    print(f"UnderlyingScrip: {underlying['UnderlyingScrip']}")
    print(f"UnderlyingSeg: {underlying['UnderlyingSeg']}")
    print("-" * 72)

    # Construct broker / DB clients. If env vars are missing the constructors
    # tend to raise — classify as DEPENDENCY_MISSING so monitoring distinguishes
    # "the .env is broken" from "the upstream is broken".
    try:
        dhan = DhanClient()
        sb = SupabaseClient()
    except Exception as e:
        return log.exit_with_reason(
            "DEPENDENCY_MISSING",
            exit_code=1,
            error_message=f"Client init failed: {e}",
        )

    # Step 1: expiry list. Token-expiry usually surfaces here first.
    try:
        expiry_resp = retry_call(
            lambda: dhan.get_expiry_list(
                underlying_scrip=underlying["UnderlyingScrip"],
                underlying_seg=underlying["UnderlyingSeg"],
            ),
            attempts=3,
            delay_seconds=5.0,
            backoff_multiplier=1.5,
            label=f"{symbol} get_expiry_list",
        )
    except Exception as e:
        return log.exit_with_reason(
            _classify_dhan_error(e),
            exit_code=1,
            error_message=f"get_expiry_list failed: {e}",
        )

    expiries = expiry_resp.get("data")
    if not isinstance(expiries, list) or not expiries:
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"No expiries returned for {symbol}: {str(expiry_resp)[:500]}",
        )

    expiry_date = str(expiries[0])
    print(f"Selected expiry: {expiry_date}")

    # Step 2: option chain.
    try:
        chain_resp = retry_call(
            lambda: dhan.get_option_chain(
                underlying_scrip=underlying["UnderlyingScrip"],
                underlying_seg=underlying["UnderlyingSeg"],
                expiry=expiry_date,
            ),
            attempts=3,
            delay_seconds=5.0,
            backoff_multiplier=1.5,
            label=f"{symbol} get_option_chain",
        )
    except Exception as e:
        return log.exit_with_reason(
            _classify_dhan_error(e),
            exit_code=1,
            error_message=f"get_option_chain failed: {e}",
        )

    data = chain_resp.get("data")
    if not isinstance(data, dict):
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"Option chain response missing data dict: {str(chain_resp)[:500]}",
        )

    spot = to_float(data.get("last_price"))
    if spot is None:
        spot = to_float(data.get("spot_price"))

    snapshot_ts = utc_now_iso()
    run_id = str(uuid.uuid4())

    # Extract rows. extract_option_rows can raise on malformed 'oc' shape.
    try:
        rows = extract_option_rows(
            symbol=symbol,
            expiry_date=expiry_date,
            snapshot_ts=snapshot_ts,
            run_id=run_id,
            spot=spot,
            option_chain_response=chain_resp,
            mode=mode,
        )
    except Exception as e:
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"extract_option_rows failed: {e}",
        )

    if not rows:
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"No option rows extracted for {symbol} in mode={mode}",
        )

    print(f"Extracted rows: {len(rows)}")
    # ── STDOUT API CONTRACT ──────────────────────────────────────────────────
    # Both run_option_snapshot_intraday_runner.py and run_merdian_shadow_runner.py
    # parse the EXACT line "Run ID: <uuid>" to extract run_id for the gamma /
    # volatility steps that follow. See V19 §15 governance rule
    # `stdout_run_id_api_contract`. DO NOT change this prefix without
    # updating BOTH runners' parse logic in the same commit.
    print(f"Run ID: {run_id}")
    print(f"Spot: {spot}")
    print("-" * 72)
    print("Writing rows to Supabase...")

    try:
        inserted = retry_call(
            lambda: sb.insert("option_chain_snapshots", rows),
            attempts=3,
            delay_seconds=5.0,
            backoff_multiplier=1.5,
            label=f"{symbol} insert option_chain_snapshots",
        )
    except Exception as e:
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"Supabase insert failed: {e}",
        )

    # If sb.insert returns a list of inserted rows, prefer that count;
    # otherwise fall back to len(rows) -- the count we ATTEMPTED to write.
    # The original script used 0 in the fallback case which understates writes.
    inserted_count = len(inserted) if isinstance(inserted, list) else len(rows)
    print(f"Inserted rows returned by Supabase: {inserted_count}")

    # ENH-71: record the actual write count. ExecutionLog computes
    # contract_met by comparing this against EXPECTED_FLOOR[mode].
    log.record_write("option_chain_snapshots", inserted_count)

    print("INGEST OPTION CHAIN COMPLETED")
    return log.complete()


def main() -> int:
    if len(sys.argv) < 2:
        # Usage error -- no log row written. ExecutionLog requires a script
        # contract (symbol, mode, expected_writes) and we have no symbol yet.
        # Operators see the usage message immediately on stderr.
        print(
            "Usage: python .\\ingest_option_chain_local.py SYMBOL [FULL|ATM_ONLY]",
            file=sys.stderr,
        )
        return 2

    symbol_arg = sys.argv[1].upper().strip()
    mode_arg = sys.argv[2] if len(sys.argv) >= 3 else "FULL"

    # Normalise mode early so we can pick the right contract floor.
    try:
        mode = normalize_mode(mode_arg)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    # ── ENH-72 write-contract declaration ────────────────────────────────────
    # One invocation = one symbol = one mode. expected_writes is the FLOOR;
    # see EXPECTED_FLOOR comment for the rationale on why this is not the
    # typical row count. notes carries mode/floor for dashboard filtering.
    log = ExecutionLog(
        script_name="ingest_option_chain_local.py",
        expected_writes={"option_chain_snapshots": EXPECTED_FLOOR[mode]},
        symbol=symbol_arg,
        notes=f"mode={mode} floor={EXPECTED_FLOOR[mode]}",
    )

    # Defense-in-depth holiday gate. The supervisor already calendar-gates
    # the runner, but operators may invoke this script directly for tests.
    # On a real holiday this exits cleanly. On a trading day where the
    # calendar is misconfigured, contract_met=False surfaces the bug.
    is_holiday, today_str = _is_market_holiday()
    if is_holiday:
        print(f"[{today_str}] Market holiday — ingest_option_chain exiting cleanly.")
        return log.exit_with_reason(
            "HOLIDAY_GATE",
            notes=f"trading_calendar says closed for {today_str}",
        )

    return ingest_symbol(symbol_arg, mode_arg, log)


if __name__ == "__main__":
    sys.exit(main())
