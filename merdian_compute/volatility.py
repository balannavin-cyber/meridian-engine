"""merdian_compute.volatility — ATM IV of one chain batch (the walls' sigma input).

S101_C3_ATM_IV: the helpers below were moved byte-identical from
compute_volatility_metrics_local.py at 11f2cbe; derive_atm_iv is main()'s ATM-IV statements,
cut with two counted substitutions (see S101 C3). Pure: no I/O, no env, no network, no DB.
Any edit here changes the live writer: replay + offline suite first.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional


def parse_iso_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        return None


def parse_iso_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        s = str(value).strip()
        # Pad fractional seconds to 6 digits for Python 3.10 compatibility
        import re
        s = re.sub(r'(\.\d{1,5})([+-]|Z|$)', lambda m: m.group(1).ljust(7, '0') + m.group(2), s)
        s = s.replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def get_expiry_type(expiry_date: date, symbol: str) -> str:
    if symbol.upper() == "NIFTY":
        return "WEEKLY" if expiry_date.weekday() == 1 else "MONTHLY"
    if symbol.upper() == "SENSEX":
        return "WEEKLY" if expiry_date.weekday() == 3 else "MONTHLY"
    return "UNKNOWN"


def get_strike_step(symbol: str) -> int:
    if symbol.upper() == "NIFTY":
        return 50
    if symbol.upper() == "SENSEX":
        return 100
    raise RuntimeError(f"Unsupported symbol: {symbol}")


def find_atm_strike(spot: float, symbol: str) -> int:
    step = get_strike_step(symbol)
    return int(round(float(spot) / step) * step)


def find_row(rows: List[Dict[str, Any]], strike: int, option_type: str) -> Optional[Dict[str, Any]]:
    for row in rows:
        try:
            row_strike = int(float(row.get("strike")))
        except Exception:
            continue

        row_option_type = str(row.get("option_type", "")).upper()
        if row_strike == strike and row_option_type == option_type.upper():
            return row
    return None


# The twelve names derive_atm_iv returns on success, in the writer's unpack order.
ATM_IV_KEYS = ('first', 'symbol', 'expiry_date', 'ts_value', 'spot', 'atm_strike', 'ce_row', 'pe_row', 'atm_call_iv', 'atm_put_iv', 'atm_iv_avg', 'iv_skew')


def _atm_iv_error(reason: str, *, exit_code: int, error_message: str) -> dict[str, Any]:
    """An exit the writer turns back into log.exit_with_reason(reason, exit_code=, error_message=)."""
    return {"error": (reason, exit_code, error_message)}


def derive_atm_iv(
    option_rows: List[Dict[str, Any]],
    on_symbol: Optional[Callable[[str], Any]] = None,
) -> dict[str, Any]:
    """ATM call / put IV, their average and skew from ONE chain batch (one symbol, one expiry).

    Returns {'error': None, <ATM_IV_KEYS>...} or {'error': (reason, exit_code, message)}.
    atm_strike = round(spot / step) * step with step 50 NIFTY / 100 SENSEX (other symbols are a
    DATA_ERROR); IVs are the rows' `iv` as delivered; atm_iv_avg = (call + put) / 2;
    iv_skew = put - call. on_symbol (the writer passes its ledger's set_symbol) is called once
    the symbol is known, at exactly the point the writer called it; retail passes nothing.
    """
    first = option_rows[0]

    try:
        symbol = str(first["symbol"]).upper()
    except Exception as e:
        return _atm_iv_error(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"Could not extract symbol from chain: {e}",
        )

    # Backfill symbol onto the log row now that we know it. set_symbol() is a
    # PATCH to script_execution_log's RUNNING row -- see core/execution_log.py
    # (added Session 3 for run_id-contract scripts).
    if on_symbol is not None:
        on_symbol(symbol)

    expiry_date = parse_iso_date(first.get("expiry_date"))
    ts_value = parse_iso_dt(first.get("ts") or first.get("created_at"))
    spot = safe_float(first.get("spot"))

    if expiry_date is None:
        return _atm_iv_error(
            "DATA_ERROR",
            exit_code=1,
            error_message="expiry_date missing from option rows",
        )
    if ts_value is None:
        return _atm_iv_error(
            "DATA_ERROR",
            exit_code=1,
            error_message="ts missing from option rows",
        )
    if spot is None:
        return _atm_iv_error(
            "DATA_ERROR",
            exit_code=1,
            error_message="spot missing from option rows",
        )

    try:
        atm_strike = find_atm_strike(spot, symbol)
    except Exception as e:
        return _atm_iv_error(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"find_atm_strike failed: {e}",
        )

    ce_row = find_row(option_rows, atm_strike, "CE")
    pe_row = find_row(option_rows, atm_strike, "PE")

    if ce_row is None:
        return _atm_iv_error(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"ATM CE row not found for symbol={symbol}, strike={atm_strike}",
        )
    if pe_row is None:
        return _atm_iv_error(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"ATM PE row not found for symbol={symbol}, strike={atm_strike}",
        )

    atm_call_iv = safe_float(ce_row.get("iv"))
    atm_put_iv = safe_float(pe_row.get("iv"))

    if atm_call_iv is None:
        return _atm_iv_error(
            "DATA_ERROR",
            exit_code=1,
            error_message="ATM call IV missing",
        )
    if atm_put_iv is None:
        return _atm_iv_error(
            "DATA_ERROR",
            exit_code=1,
            error_message="ATM put IV missing",
        )

    atm_iv_avg = (atm_call_iv + atm_put_iv) / 2.0
    iv_skew = atm_put_iv - atm_call_iv

    return {"error": None, "first": first, "symbol": symbol, "expiry_date": expiry_date, "ts_value": ts_value, "spot": spot, "atm_strike": atm_strike, "ce_row": ce_row, "pe_row": pe_row, "atm_call_iv": atm_call_iv, "atm_put_iv": atm_put_iv, "atm_iv_avg": atm_iv_avg, "iv_skew": iv_skew}
