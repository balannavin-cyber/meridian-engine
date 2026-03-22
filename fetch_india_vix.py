import time
from typing import Any, Dict, Optional

import requests


NSE_HOME_URL = "https://www.nseindia.com/"
NSE_ALL_INDICES_URL = "https://www.nseindia.com/api/allIndices"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Origin": "https://www.nseindia.com",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def classify_vix(vix_value: float) -> str:
    if vix_value < 12:
        return "LOW"
    if vix_value < 18:
        return "NORMAL"
    if vix_value < 25:
        return "HIGH"
    return "PANIC"


def _extract_vix_row(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = payload.get("data", [])
    for row in rows:
        index_name = str(row.get("index", "")).strip().upper()
        if index_name == "INDIA VIX":
            return row
    return None


def fetch_india_vix(max_attempts: int = 5, sleep_seconds: float = 1.5) -> Dict[str, Any]:
    last_error: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        session = requests.Session()
        session.headers.update(HEADERS)

        try:
            # Warm-up request. NSE may 403 this sometimes; do not fail on it.
            try:
                session.get(NSE_HOME_URL, timeout=20)
                time.sleep(0.8)
            except Exception:
                pass

            resp = session.get(NSE_ALL_INDICES_URL, timeout=20)
            resp.raise_for_status()

            payload = resp.json()
            row = _extract_vix_row(payload)

            if row is None:
                raise RuntimeError("INDIA VIX not found in NSE allIndices response.")

            last_val = row.get("last")
            change_val = row.get("variation")

            if last_val is None:
                raise RuntimeError("INDIA VIX found but 'last' value missing.")

            india_vix = float(last_val)
            vix_change = float(change_val) if change_val is not None else None
            vix_regime = classify_vix(india_vix)

            return {
                "india_vix": india_vix,
                "vix_change": vix_change,
                "vix_regime": vix_regime,
                "raw_vix_row": row,
            }

        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(sleep_seconds * attempt)
            else:
                break

    raise RuntimeError(f"Failed to fetch India VIX after {max_attempts} attempts: {last_error}")


def main() -> None:
    result = fetch_india_vix()
    print("India VIX fetch OK")
    print(result)


if __name__ == "__main__":
    main()