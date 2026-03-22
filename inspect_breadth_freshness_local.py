import os
import json

import requests
from dotenv import load_dotenv


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment.")

HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}


def rest_get(table_or_view: str, params: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table_or_view}"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"GET {table_or_view} failed {resp.status_code}: {resp.text}")
    return resp.json()


def fetch_one(table_name: str, order: str = "ts.desc"):
    rows = rest_get(
        table_name,
        {
            "select": "*",
            "order": order,
            "limit": 1,
        },
    )
    return rows[0] if rows else None


def fetch_many(table_name: str, limit_rows: int = 10, order: str = "ts.desc"):
    return rest_get(
        table_name,
        {
            "select": "*",
            "order": order,
            "limit": limit_rows,
        },
    )


def fetch_max_trade_date(table_name: str):
    rows = rest_get(
        table_name,
        {
            "select": "trade_date",
            "order": "trade_date.desc",
            "limit": 1,
        },
    )
    return rows[0] if rows else None


def main():
    latest_view = fetch_one("latest_market_breadth_intraday", "ts.desc")
    latest_table = fetch_one("market_breadth_intraday", "ts.desc")
    latest_intraday_last = fetch_one("equity_intraday_last", "ts.desc")
    recent_intraday_rows = fetch_many("market_breadth_intraday", 10, "ts.desc")

    latest_equity_eod = fetch_max_trade_date("equity_eod")
    latest_breadth_daily = fetch_max_trade_date("breadth_indicators_daily")

    payload = {
        "intraday": {
            "latest_market_breadth_intraday": latest_view,
            "latest_market_breadth_intraday_ts": latest_view.get("ts") if latest_view else None,
            "market_breadth_intraday_latest_row": latest_table,
            "market_breadth_intraday_latest_ts": latest_table.get("ts") if latest_table else None,
            "equity_intraday_last_latest_row": latest_intraday_last,
            "equity_intraday_last_latest_ts": latest_intraday_last.get("ts") if latest_intraday_last else None,
            "market_breadth_intraday_recent_rows": recent_intraday_rows,
        },
        "daily": {
            "equity_eod_latest_trade_date_row": latest_equity_eod,
            "equity_eod_latest_trade_date": latest_equity_eod.get("trade_date") if latest_equity_eod else None,
            "breadth_indicators_daily_latest_trade_date_row": latest_breadth_daily,
            "breadth_indicators_daily_latest_trade_date": latest_breadth_daily.get("trade_date") if latest_breadth_daily else None,
        },
    }

    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()