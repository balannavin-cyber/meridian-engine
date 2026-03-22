import os
import sys
import json
import statistics
from datetime import datetime

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

DEFAULT_SYMBOLS = ["NIFTY", "SENSEX"]
MAX_FETCH_ROWS = 5000


def log(msg: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")


def rest_get(table_or_view: str, params: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table_or_view}"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"GET {table_or_view} failed {resp.status_code}: {resp.text}")
    return resp.json()


def parse_ts(ts_value):
    if ts_value is None:
        return None
    if isinstance(ts_value, datetime):
        return ts_value
    s = str(ts_value).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def minutes_diff(later_ts, earlier_ts):
    later_dt = parse_ts(later_ts)
    earlier_dt = parse_ts(earlier_ts)
    if later_dt is None or earlier_dt is None:
        return None
    return (later_dt - earlier_dt).total_seconds() / 60.0


def get_latest_gamma_row(symbol: str):
    rows = rest_get(
        "gamma_metrics",
        {
            "symbol": f"eq.{symbol}",
            "select": "ts,symbol,expiry_date,spot,run_id",
            "order": "ts.desc",
            "limit": 1,
        },
    )
    return rows[0] if rows else None


def get_option_chain_rows(symbol: str, expiry_date: str, limit_rows: int = MAX_FETCH_ROWS):
    rows = rest_get(
        "option_chain_snapshots",
        {
            "symbol": f"eq.{symbol}",
            "expiry_date": f"eq.{expiry_date}",
            "select": "ts,strike,option_type,ltp,expiry_date,symbol",
            "order": "ts.desc",
            "limit": limit_rows,
        },
    )
    return rows


def summarize_symbol(symbol: str):
    gamma_row = get_latest_gamma_row(symbol)
    if not gamma_row:
        raise RuntimeError(f"No gamma_metrics row found for {symbol}")

    expiry_date = gamma_row.get("expiry_date")
    latest_gamma_ts = gamma_row.get("ts")

    rows = get_option_chain_rows(symbol, expiry_date, MAX_FETCH_ROWS)
    if not rows:
        raise RuntimeError(f"No option_chain_snapshots rows found for {symbol} expiry {expiry_date}")

    unique_ts = []
    seen = set()
    rows_per_ts = {}

    for row in rows:
        ts = row.get("ts")
        if ts is None:
            continue
        rows_per_ts[ts] = rows_per_ts.get(ts, 0) + 1
        if ts not in seen:
            seen.add(ts)
            unique_ts.append(ts)

    gap_minutes = []
    gap_pairs = []

    for i in range(len(unique_ts) - 1):
        later_ts = unique_ts[i]
        earlier_ts = unique_ts[i + 1]
        gap = minutes_diff(later_ts, earlier_ts)
        if gap is not None:
            gap_minutes.append(gap)
            gap_pairs.append(
                {
                    "later_ts": later_ts,
                    "earlier_ts": earlier_ts,
                    "gap_minutes": round(gap, 4),
                }
            )

    latest_bucket_ts = unique_ts[0] if unique_ts else None
    previous_bucket_ts = unique_ts[1] if len(unique_ts) > 1 else None
    latest_gap_minutes = None
    if latest_bucket_ts and previous_bucket_ts:
        latest_gap_minutes = minutes_diff(latest_bucket_ts, previous_bucket_ts)

    stats = {
        "count": len(gap_minutes),
        "min": round(min(gap_minutes), 4) if gap_minutes else None,
        "max": round(max(gap_minutes), 4) if gap_minutes else None,
        "median": round(statistics.median(gap_minutes), 4) if gap_minutes else None,
        "mean": round(statistics.mean(gap_minutes), 4) if gap_minutes else None,
    }

    latest_10_ts = []
    for ts in unique_ts[:10]:
        latest_10_ts.append(
            {
                "ts": ts,
                "rows_in_bucket": rows_per_ts.get(ts, 0),
            }
        )

    summary = {
        "symbol": symbol,
        "expiry_date": expiry_date,
        "latest_gamma_ts": latest_gamma_ts,
        "fetched_row_count": len(rows),
        "unique_ts_count": len(unique_ts),
        "latest_bucket_ts": latest_bucket_ts,
        "previous_bucket_ts": previous_bucket_ts,
        "latest_gap_minutes": round(latest_gap_minutes, 4) if latest_gap_minutes is not None else None,
        "gap_stats_minutes": stats,
        "latest_10_buckets": latest_10_ts,
        "largest_10_gaps": sorted(gap_pairs, key=lambda x: x["gap_minutes"], reverse=True)[:10],
    }

    return summary


def save_json(path: str, payload: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main():
    if len(sys.argv) > 1:
        symbols = [sys.argv[1].strip().upper()]
    else:
        symbols = DEFAULT_SYMBOLS

    os.makedirs("data", exist_ok=True)

    all_results = []

    for symbol in symbols:
        log(f"Inspecting option_chain_snapshots for {symbol} ...")
        summary = summarize_symbol(symbol)
        all_results.append(summary)

        out_path = os.path.join("data", f"option_chain_gap_summary_{symbol}.json")
        save_json(out_path, summary)

        print("=" * 72)
        print(json.dumps(summary, indent=2, default=str))
        print("=" * 72)
        print(f"Saved summary to: {os.path.abspath(out_path)}")

    combined_path = os.path.join("data", "option_chain_gap_summary_all.json")
    save_json(combined_path, {"results": all_results})
    print(f"Saved combined summary to: {os.path.abspath(combined_path)}")


if __name__ == "__main__":
    main()