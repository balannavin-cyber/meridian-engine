# backfill_shadow_sources_for_date_local.py

import sys
import requests
from datetime import datetime, timedelta, timezone

SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_KEY = "YOUR_SERVICE_ROLE_KEY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

SYMBOLS = ["NIFTY", "SENSEX"]

# ---------------------------
# Helpers
# ---------------------------

def fetch_market_state_rows(reconstruction_date):
    url = f"{SUPABASE_URL}/rest/v1/market_state_snapshots"
    params = {
        "select": "*",
        "trade_date": f"eq.{reconstruction_date}"
    }
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()


def exists_row(table, symbol, ts):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {
        "select": "ts",
        "symbol": f"eq.{symbol}",
        "ts": f"eq.{ts}",
        "limit": 1
    }
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return len(r.json()) > 0


def insert_row(table, payload):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.post(url, headers=HEADERS, json=payload)
    r.raise_for_status()


# ---------------------------
# Feature builders (STUBS)
# ---------------------------

def build_momentum(symbol, ts):
    # TODO: replace with your real logic
    return {
        "symbol": symbol,
        "ts": ts,
        "momentum_regime_v2": "DOWN",
        "ret_session": -0.3,
        "ret_30m": -0.1,
        "ret_60m": -0.2
    }


def build_options_flow(symbol, ts):
    # TODO: replace with real Dhan / chain logic
    return {
        "symbol": symbol,
        "ts": ts,
        "flow_regime": "BEARISH_FLOW"
    }


def build_smdm(symbol, ts):
    # TODO: replace with real logic
    return {
        "symbol": symbol,
        "ts": ts,
        "smdm_pattern": "NONE"
    }


# ---------------------------
# Main backfill
# ---------------------------

def run_backfill(reconstruction_date):

    print("=" * 72)
    print("MERDIAN - backfill_shadow_sources_for_date")
    print("=" * 72)

    rows = fetch_market_state_rows(reconstruction_date)

    print(f"Fetched market_state rows: {len(rows)}")

    momentum_created = 0
    flow_created = 0
    smdm_created = 0

    for row in rows:
        symbol = row["symbol"]
        ts = row["ts"]

        # -------- Momentum --------
        if not exists_row("momentum_snapshots_v2", symbol, ts):
            payload = build_momentum(symbol, ts)
            insert_row("momentum_snapshots_v2", payload)
            momentum_created += 1

        # -------- Options Flow --------
        if not exists_row("options_flow_snapshots", symbol, ts):
            payload = build_options_flow(symbol, ts)
            insert_row("options_flow_snapshots", payload)
            flow_created += 1

        # -------- SMDM --------
        if not exists_row("smdm_snapshots", symbol, ts):
            payload = build_smdm(symbol, ts)
            insert_row("smdm_snapshots", payload)
            smdm_created += 1

    print("-" * 72)
    print(f"Momentum rows created: {momentum_created}")
    print(f"Options flow rows created: {flow_created}")
    print(f"SMDM rows created: {smdm_created}")
    print("-" * 72)
    print("BACKFILL COMPLETED")


# ---------------------------
# CLI
# ---------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backfill_shadow_sources_for_date_local.py YYYY-MM-DD")
        sys.exit(1)

    reconstruction_date = sys.argv[1]
    run_backfill(reconstruction_date)