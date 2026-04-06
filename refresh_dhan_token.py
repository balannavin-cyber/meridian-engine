from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict

import pyotp
import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
TOKEN_STATUS_FILE = BASE_DIR / "runtime" / "token_status.json"
TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"

IST = timezone(timedelta(hours=5, minutes=30))


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def read_env_lines(path: Path) -> list[str]:
    if not path.exists():
        raise RuntimeError(f".env file not found: {path}")
    return path.read_text(encoding="utf-8").splitlines()


def upsert_env_value(lines: list[str], key: str, value: str) -> list[str]:
    prefix = f"{key}="
    replaced = False
    out: list[str] = []
    for line in lines:
        if line.startswith(prefix):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}")
    return out


def write_env_lines(path: Path, lines: list[str]) -> None:
    text = "\n".join(lines).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")


def generate_totp(seed: str) -> str:
    return pyotp.TOTP(seed).now()


def request_dhan_token(client_id: str, pin: str, totp_code: str) -> Dict:
    resp = requests.post(
        TOKEN_URL,
        params={
            "dhanClientId": client_id,
            "pin": pin,
            "totp": totp_code,
        },
        timeout=30,
    )

    if resp.status_code >= 300:
        raise RuntimeError(
            f"Dhan token request failed ({resp.status_code}): {resp.text}"
        )

    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected Dhan token response: {resp.text}")

    access_token = str(data.get("accessToken", "")).strip()
    if not access_token:
        raise RuntimeError(f"Dhan token response missing accessToken: {json.dumps(data)}")

    return data


def write_token_status(success: bool, expiry_time: str, error: str = "") -> None:
    """Write token status to runtime/token_status.json for dashboard consumption."""
    TOKEN_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    now_ist = datetime.now(IST)
    payload = {
        "success": success,
        "refreshed_at_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "refreshed_at_iso": now_ist.isoformat(),
        "expiry_time": expiry_time,
        "error": error,
    }
    tmp = TOKEN_STATUS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(TOKEN_STATUS_FILE)


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)

    client_id = require_env("DHAN_CLIENT_ID")
    pin = require_env("DHAN_PIN")
    totp_seed = require_env("DHAN_TOTP_SEED")

    totp_code = generate_totp(totp_seed)

    try:
        token_response = request_dhan_token(client_id, pin, totp_code)
    except RuntimeError as e:
        error_msg = str(e)
        # If Invalid TOTP, try next code window
        if "Invalid TOTP" in error_msg:
            import time as _time
            print(f"WARNING: Invalid TOTP on first attempt. Waiting 30s for next window...")
            _time.sleep(30)
            totp_code = generate_totp(totp_seed)
            token_response = request_dhan_token(client_id, pin, totp_code)
        else:
            write_token_status(False, "", error_msg)
            raise

    access_token = str(token_response["accessToken"]).strip()
    expiry_time = str(token_response.get("expiryTime", "")).strip()

    env_lines = read_env_lines(ENV_PATH)
    env_lines = upsert_env_value(env_lines, "DHAN_API_TOKEN", access_token)
    write_env_lines(ENV_PATH, env_lines)

    # Write token status file for dashboard
    write_token_status(True, expiry_time)

    print("=" * 72)
    print("DHAN TOKEN REFRESH SUCCESS")
    print("=" * 72)
    print(f"Updated file: {ENV_PATH}")
    if expiry_time:
        print(f"Expiry time: {expiry_time}")
    print("DHAN_API_TOKEN has been refreshed in .env")

    # Sync token to Supabase so AWS can read it
    try:
        supabase_url = require_env("SUPABASE_URL")
        supabase_key = require_env("SUPABASE_SERVICE_ROLE_KEY")
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        payload = {
            "config_value": access_token,
            "updated_at": "now()",
            "updated_by": "local_token_refresh",
        }
        r = requests.patch(
            f"{supabase_url}/rest/v1/system_config?config_key=eq.dhan_api_token",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if r.status_code in (200, 204):
            print("Token synced to Supabase successfully.")
        else:
            print(f"WARNING: Supabase sync returned {r.status_code}: {r.text}")
    except Exception as e:
        print(f"WARNING: Supabase sync failed (non-fatal): {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
