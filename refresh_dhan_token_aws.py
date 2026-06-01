#!/usr/bin/env python3
"""
refresh_dhan_token_aws.py — AWS-side Dhan token refresh (S42 Phase 1.c)

Runs on AWS via cron at 08:15 IST (canonical refresh time).
Uses dhan_token_refresh_lib for portable Dhan API logic.
Writes refreshed token to Supabase system_config table.

Does NOT write to local .env (AWS .env is ephemeral).
Supabase becomes the single source of truth; Local and AWS both read from it.

Credentials sourced from:
- DHAN_CLIENT_ID, DHAN_PIN, DHAN_TOTP_SEED from .env (AWS env vars)
- SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY from .env (AWS env vars)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# Import portable library
from dhan_token_refresh_lib import (
    refresh_with_totp_retry,
    DhanRateLimitError,
    DhanTokenRefreshError,
)


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
IST = timezone(timedelta(hours=5, minutes=30))


def require_env(name: str) -> str:
    """Read required environment variable."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def log(msg: str) -> str:
    """Log with IST timestamp."""
    ts = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    return line


def write_token_to_supabase(
    supabase_url: str,
    supabase_key: str,
    token: str,
    expiry_time: str,
) -> bool:
    """
    Write refreshed token to Supabase system_config.dhan_api_token row.
    Returns True on success, False on failure (non-fatal).
    """
    try:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        payload = {
            "config_value": token,
            "updated_at": "now()",
            "updated_by": "aws_token_refresh",
        }
        r = requests.patch(
            f"{supabase_url}/rest/v1/system_config?config_key=eq.dhan_api_token",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if r.status_code in (200, 204):
            log(f"✓ Token written to Supabase (expiry: {expiry_time})")
            return True
        else:
            log(f"✗ Supabase write failed ({r.status_code}): {r.text[:120]}")
            return False
    except Exception as e:
        log(f"✗ Supabase write exception: {type(e).__name__}: {e}")
        return False


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)
    
    log("=== AWS Token Refresh (S42 Phase 1.c) ===")
    log(f"Host: AWS EC2 ({os.getenv('HOSTNAME', 'unknown')})")
    
    try:
        client_id = require_env("DHAN_CLIENT_ID")
        pin = require_env("DHAN_PIN")
        totp_seed = require_env("DHAN_TOTP_SEED")
        supabase_url = require_env("SUPABASE_URL").rstrip("/")
        supabase_key = require_env("SUPABASE_SERVICE_ROLE_KEY")
    except RuntimeError as e:
        log(f"✗ Config error: {e}")
        return 1
    
    # Refresh token using portable library
    try:
        log("Calling Dhan API...")
        token_response = refresh_with_totp_retry(
            client_id=client_id,
            pin=pin,
            totp_seed=totp_seed,
            max_retries=1,
        )
    except DhanRateLimitError as e:
        log(f"⚠ Rate limit: {e}")
        log("(Token was refreshed by another caller within 2 min — not a failure)")
        return 0  # Exit cleanly; token is valid
    except DhanTokenRefreshError as e:
        log(f"✗ Token refresh failed: {e}")
        return 1
    except Exception as e:
        log(f"✗ Unexpected error: {type(e).__name__}: {e}")
        return 1
    
    # Extract token and expiry
    access_token = str(token_response.get("accessToken", "")).strip()
    expiry_time = str(token_response.get("expiryTime", "")).strip()
    
    if not access_token:
        log(f"✗ No accessToken in response: {json.dumps(token_response)}")
        return 1
    
    log(f"✓ Token obtained from Dhan (len={len(access_token)}, expiry={expiry_time})")
    
    # Write to Supabase
    if not write_token_to_supabase(supabase_url, supabase_key, access_token, expiry_time):
        log("✗ Failed to write token to Supabase (see above for details)")
        return 1
    
    log("=== AWS Token Refresh COMPLETE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
