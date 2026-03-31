from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

import pyotp
import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"


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


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)

    client_id = require_env("DHAN_CLIENT_ID")
    pin = require_env("DHAN_PIN")
    totp_seed = require_env("DHAN_TOTP_SEED")

    totp_code = generate_totp(totp_seed)
    token_response = request_dhan_token(client_id, pin, totp_code)

    access_token = str(token_response["accessToken"]).strip()
    expiry_time = str(token_response.get("expiryTime", "")).strip()

    env_lines = read_env_lines(ENV_PATH)
    env_lines = upsert_env_value(env_lines, "DHAN_API_TOKEN", access_token)
    write_env_lines(ENV_PATH, env_lines)

    print("=" * 72)
    print("DHAN TOKEN REFRESH SUCCESS")
    print("=" * 72)
    print(f"Updated file: {ENV_PATH}")
    if expiry_time:
        print(f"Expiry time: {expiry_time}")
    print("DHAN_API_TOKEN has been refreshed in .env")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())