import os
from dotenv import load_dotenv
import requests

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

print("=== CHECK SIGNAL SNAPSHOTS ===")
r = requests.get(
    f"{url}/rest/v1/signal_snapshots?select=ts,symbol&limit=5",
    headers=headers
)
print(r.json())

print("\n=== CHECK SHADOW SIGNAL SNAPSHOTS ===")
r2 = requests.get(
    f"{url}/rest/v1/shadow_signal_snapshots_v3?select=ts,symbol&limit=5",
    headers=headers
)
print(r2.json())

print("\n=== CHECK INTRADAY OHLC ===")
r3 = requests.get(
    f"{url}/rest/v1/intraday_ohlc?select=ts,symbol&limit=5",
    headers=headers
)
print(r3.json())