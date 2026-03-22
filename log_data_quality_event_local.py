import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import requests


BASE_DIR = Path(__file__).resolve().parent


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
        raise RuntimeError("Need SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY in environment or .env")

    return {
        "url": supabase_url.rstrip("/"),
        "api_key": api_key,
    }


def insert_event(payload: Dict) -> None:
    creds = _get_supabase_credentials()

    url = f"{creds['url']}/rest/v1/data_quality_events"
    headers = {
        "apikey": creds["api_key"],
        "Authorization": f"Bearer {creds['api_key']}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    response = requests.post(url, headers=headers, json=[payload], timeout=30)
    response.raise_for_status()

    rows = response.json()
    print(f"Inserted rows returned by Supabase: {len(rows)}")


def main() -> None:
    if len(sys.argv) < 3:
        raise RuntimeError(
            "Usage: python .\\log_data_quality_event_local.py <event_type> <pipeline> "
            "[severity] [symbol] [ticker]"
        )

    event_type = sys.argv[1].strip()
    pipeline = sys.argv[2].strip()
    severity = sys.argv[3].strip() if len(sys.argv) >= 4 else "warning"
    symbol = sys.argv[4].strip() if len(sys.argv) >= 5 else None
    ticker = sys.argv[5].strip() if len(sys.argv) >= 6 else None

    payload = {
        "event_ts": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "severity": severity,
        "symbol": symbol,
        "ticker": ticker,
        "pipeline": pipeline,
        "detail": {
            "source": "manual_local_logger",
            "argv": sys.argv[1:]
        },
        "resolved": False,
        "notes": "Manual test event inserted from local Python"
    }

    print("=" * 70)
    print("Gamma Engine - Log Data Quality Event")
    print("=" * 70)
    print(json.dumps(payload, indent=2))

    insert_event(payload)

    print("DATA QUALITY EVENT LOGGED")


if __name__ == "__main__":
    main()