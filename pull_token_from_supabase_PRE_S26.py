from __future__ import annotations
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing from .env")
        return 1

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
    }
    r = requests.get(
        f"{supabase_url}/rest/v1/system_config?config_key=eq.dhan_api_token&select=config_value",
        headers=headers,
        timeout=15,
    )
    if r.status_code != 200:
        print(f"ERROR: Supabase returned {r.status_code}: {r.text}")
        return 1

    rows = r.json()
    if not rows:
        print("ERROR: No dhan_api_token row found in system_config")
        return 1

    token = rows[0]["config_value"].strip()
    if not token or token == "placeholder":
        print("ERROR: Token in Supabase is empty or still placeholder")
        return 1

    env_text = ENV_PATH.read_text(encoding="utf-8")
    lines = env_text.splitlines()
    updated = []
    replaced = False
    for line in lines:
        if line.startswith("DHAN_API_TOKEN="):
            updated.append(f"DHAN_API_TOKEN={token}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append(f"DHAN_API_TOKEN={token}")

    ENV_PATH.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
    print("Token pulled from Supabase and written to .env successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
