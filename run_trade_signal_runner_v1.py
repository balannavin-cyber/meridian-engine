import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from core.supabase_client import SupabaseClient


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["NIFTY", "SENSEX"]
STALE_SIGNAL_MINUTES = 120


def _load_env_from_file() -> Dict[str, str]:
    env_path = BASE_DIR / ".env"
    values: Dict[str, str] = {}

    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line:
            continue
        if line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def _get_supabase_credentials() -> Dict[str, str]:
    file_env = _load_env_from_file()

    supabase_url = os.getenv("SUPABASE_URL") or file_env.get("SUPABASE_URL") or ""
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or file_env.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    anon_key = os.getenv("SUPABASE_ANON_KEY") or file_env.get("SUPABASE_ANON_KEY") or ""

    api_key = service_key or anon_key

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL not found in environment or .env")

    if not api_key:
        raise RuntimeError(
            "Need SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY in environment or .env"
        )

    return {
        "url": supabase_url.rstrip("/"),
        "api_key": api_key,
    }


def _insert_data_quality_event(
    event_type: str,
    severity: str,
    symbol: Optional[str],
    ticker: Optional[str],
    pipeline: str,
    detail: Dict[str, Any],
    notes: str,
) -> None:
    creds = _get_supabase_credentials()

    url = f"{creds['url']}/rest/v1/data_quality_events"
    headers = {
        "apikey": creds["api_key"],
        "Authorization": f"Bearer {creds['api_key']}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    payload = [{
        "event_ts": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "severity": severity,
        "symbol": symbol,
        "ticker": ticker,
        "pipeline": pipeline,
        "detail": detail,
        "resolved": False,
        "notes": notes,
    }]

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()


def _parse_iso_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    try:
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _is_stale_signal_ts(signal_ts: Any, max_minutes: int) -> bool:
    dt = _parse_iso_dt(signal_ts)
    if dt is None:
        return True

    now_utc = datetime.now(timezone.utc)
    age_seconds = (now_utc - dt).total_seconds()
    return age_seconds > (max_minutes * 60)


def _latest_trade_signal_file() -> Path:
    return DATA_DIR / "latest_trade_signal.json"


def _combined_trade_signals_file() -> Path:
    return DATA_DIR / "latest_trade_signals.json"


def run_signal_builder(symbol: str) -> Dict[str, Any]:
    cmd = [sys.executable, str(BASE_DIR / "build_trade_signal_local.py"), symbol]

    result = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout.rstrip())

    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.rstrip())

        _insert_data_quality_event(
            event_type="signal_runner_subprocess_failure",
            severity="error",
            symbol=symbol,
            ticker=symbol,
            pipeline="signal_runner",
            detail={
                "symbol": symbol,
                "returncode": result.returncode,
                "stderr": result.stderr[-4000:] if result.stderr else "",
                "stdout_tail": result.stdout[-4000:] if result.stdout else "",
                "command": cmd,
            },
            notes="build_trade_signal_local.py failed inside signal runner",
        )

        raise RuntimeError(f"Signal builder failed for {symbol} with code {result.returncode}")

    signal_file = _latest_trade_signal_file()
    if not signal_file.exists():
        _insert_data_quality_event(
            event_type="signal_runner_zero_signals",
            severity="error",
            symbol=symbol,
            ticker=symbol,
            pipeline="signal_runner",
            detail={
                "symbol": symbol,
                "reason": "latest_trade_signal_json_missing",
            },
            notes="Signal builder succeeded but latest_trade_signal.json was not found",
        )
        raise RuntimeError(f"latest_trade_signal.json not found after building signal for {symbol}")

    with open(signal_file, "r", encoding="utf-8") as f:
        signal = json.load(f)

    return signal


def insert_signal_run_via_rest(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    creds = _get_supabase_credentials()

    url = f"{creds['url']}/rest/v1/signal_runs"
    headers = {
        "apikey": creds["api_key"],
        "Authorization": f"Bearer {creds['api_key']}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    response = requests.post(url, headers=headers, json=[payload], timeout=30)
    response.raise_for_status()

    try:
        return response.json()
    except Exception:
        return []


def main() -> None:
    started_at = datetime.now(timezone.utc)

    print("=" * 72)
    print("Gamma Engine - Signal Runner V1")
    print("=" * 72)
    print(f"Started at: {started_at.isoformat()}")
    print("-" * 72)

    signals: List[Dict[str, Any]] = []
    signal_ids: Dict[str, Any] = {}
    gamma_run_ids: Dict[str, Any] = {}
    breadth_source: Optional[str] = None
    breadth_ts: Optional[str] = None

    success_symbols: List[str] = []
    failed_symbols: List[str] = []

    for symbol in SYMBOLS:
        print("=" * 72)
        print(f"RUNNING SIGNAL ENGINE FOR {symbol}")
        print("=" * 72)

        try:
            signal = run_signal_builder(symbol)
            signals.append(signal)
            success_symbols.append(symbol)

            signal_ids[symbol] = signal.get("id")
            gamma_run_ids[symbol] = signal.get("source_run_id")

            if breadth_source is None:
                breadth_source = signal.get("breadth_source_table")

            raw = signal.get("raw", {}) or {}
            breadth_row = raw.get("breadth_row", {}) or {}
            if breadth_ts is None:
                breadth_ts = breadth_row.get("ts")

            signal_ts = signal.get("ts")
            if _is_stale_signal_ts(signal_ts, STALE_SIGNAL_MINUTES):
                _insert_data_quality_event(
                    event_type="stale_signal_timestamp",
                    severity="warning",
                    symbol=symbol,
                    ticker=symbol,
                    pipeline="signal_runner",
                    detail={
                        "symbol": symbol,
                        "signal_ts": signal_ts,
                        "stale_threshold_minutes": STALE_SIGNAL_MINUTES,
                    },
                    notes="Signal timestamp appears stale relative to runner execution time",
                )

        except Exception as exc:
            failed_symbols.append(symbol)
            print(str(exc))

    combined_file = _combined_trade_signals_file()
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=2, default=str)

    print("-" * 72)
    print(f"Combined signals saved to: {combined_file}")

    if len(signals) == 0:
        _insert_data_quality_event(
            event_type="signal_runner_zero_signals",
            severity="error",
            symbol=None,
            ticker=None,
            pipeline="signal_runner",
            detail={
                "success_symbols": success_symbols,
                "failed_symbols": failed_symbols,
            },
            notes="Signal runner completed with zero successful signals",
        )
        raise RuntimeError("Signal runner produced zero signals")

    status = "complete"
    notes = None

    if failed_symbols and success_symbols:
        status = "partial_failure"
        notes = f"Failed symbols: {', '.join(failed_symbols)}"

        _insert_data_quality_event(
            event_type="signal_runner_partial_failure",
            severity="warning",
            symbol=None,
            ticker=None,
            pipeline="signal_runner",
            detail={
                "success_symbols": success_symbols,
                "failed_symbols": failed_symbols,
                "signal_count": len(signals),
            },
            notes="Signal runner succeeded for some symbols and failed for others",
        )

    elif failed_symbols and not success_symbols:
        status = "failed"
        notes = f"All symbols failed: {', '.join(failed_symbols)}"

        _insert_data_quality_event(
            event_type="signal_runner_zero_signals",
            severity="error",
            symbol=None,
            ticker=None,
            pipeline="signal_runner",
            detail={
                "success_symbols": success_symbols,
                "failed_symbols": failed_symbols,
            },
            notes="Signal runner failed for all symbols",
        )
        raise RuntimeError("Signal runner failed for all symbols")

    run_payload = {
        "run_ts": started_at.isoformat(),
        "symbols": success_symbols,
        "breadth_source": breadth_source,
        "breadth_ts": breadth_ts,
        "gamma_run_ids": gamma_run_ids,
        "signal_ids": signal_ids,
        "status": status,
        "notes": notes,
    }

    inserted_rows = insert_signal_run_via_rest(run_payload)

    print("-" * 72)
    print(f"Inserted signal_runs rows returned by Supabase: {len(inserted_rows)}")
    print("SIGNAL RUNNER V1 COMPLETED")


if __name__ == "__main__":
    main()