import requests
from datetime import datetime

SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SERVICE_ROLE_KEY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def fetch_pending_signals():
    url = f"{SUPABASE_URL}/rest/v1/signal_snapshots?select=id,symbol,signal_ts,spot_price&order=id.asc"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json()

def fetch_option_chain(symbol, ts):
    url = f"{SUPABASE_URL}/rest/v1/option_chain_snapshots"
    params = {
        "symbol": f"eq.{symbol}",
        "ts": f"lte.{ts}",
        "order": "ts.desc",
        "limit": 200
    }
    res = requests.get(url, headers=HEADERS, params=params)
    res.raise_for_status()
    return res.json()

def find_atm_strike(spot, strikes):
    return min(strikes, key=lambda x: abs(x - spot))

def upsert_snapshot(payload):
    url = f"{SUPABASE_URL}/rest/v1/option_atm_snapshots"
    res = requests.post(url, headers=HEADERS, json=payload)
    res.raise_for_status()

def main():
    print("========================================================")
    print("MERDIAN - Build ATM Option Snapshots V1")
    print("========================================================")

    signals = fetch_pending_signals()
    print(f"Signals fetched: {len(signals)}")

    for i, sig in enumerate(signals, start=1):
        try:
            signal_id = sig["id"]
            symbol = sig["symbol"]
            ts = sig["signal_ts"]
            spot = float(sig["spot_price"])

            chain = fetch_option_chain(symbol, ts)

            if not chain:
                print(f"[{i}] Skipped {signal_id} | no option chain")
                continue

            strikes = list(set([row["strike"] for row in chain]))
            atm = find_atm_strike(spot, strikes)

            ce = next((x for x in chain if x["strike"] == atm and x["option_type"] == "CE"), None)
            pe = next((x for x in chain if x["strike"] == atm and x["option_type"] == "PE"), None)

            payload = {
                "signal_snapshot_id": signal_id,
                "symbol": symbol,
                "signal_ts": ts,
                "atm_strike": atm,
                "ce_price": ce["ltp"] if ce else None,
                "pe_price": pe["ltp"] if pe else None,
                "ce_iv": ce["iv"] if ce else None,
                "pe_iv": pe["iv"] if pe else None
            }

            upsert_snapshot(payload)

            print(f"[{i}] Done signal {signal_id} | ATM={atm}")

        except Exception as e:
            print(f"[{i}] ERROR signal {sig.get('id')} | {str(e)}")

    print("========================================================")
    print("Completed ATM snapshot build")
    print("========================================================")


if __name__ == "__main__":
    main()