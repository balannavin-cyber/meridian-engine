#!/usr/bin/env python3
"""
dhan_token_refresh_lib.py — Portable Dhan token refresh logic (S42 Phase 1.c)

Core functionality for refreshing Dhan access tokens:
- TOTP generation from seed
- Dhan API call with error handling
- Rate limit detection
- TOTP window retry logic

Used by both Local (refresh_dhan_token.py) and AWS (refresh_dhan_token_aws.py).
Portable: no filesystem dependencies, no environment-specific logic.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, Optional

import pyotp
import requests


DHAN_TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"
DHAN_REQUEST_TIMEOUT_SECONDS = 30
TOTP_RETRY_WAIT_SECONDS = 30


class DhanTokenRefreshError(Exception):
    """Base error for token refresh failures."""
    pass


class DhanRateLimitError(DhanTokenRefreshError):
    """Dhan rejected request due to rate limit (someone else refreshed within 2 min)."""
    pass


class DhanTOTPError(DhanTokenRefreshError):
    """TOTP code was invalid."""
    pass


def generate_totp(seed: str) -> str:
    """Generate current TOTP code from seed."""
    return pyotp.TOTP(seed).now()


def request_dhan_token(
    client_id: str,
    pin: str,
    totp_code: str,
    timeout: int = DHAN_REQUEST_TIMEOUT_SECONDS,
) -> Dict:
    """
    Request access token from Dhan API.
    
    Args:
        client_id: Dhan client ID
        pin: Dhan PIN
        totp_code: Current TOTP code
        timeout: Request timeout in seconds
    
    Returns:
        Dict with keys: accessToken, expiryTime, ...
    
    Raises:
        DhanRateLimitError: if rate-limited (token generated within 2 min)
        DhanTOTPError: if TOTP is invalid
        DhanTokenRefreshError: for other errors
    """
    resp = requests.post(
        DHAN_TOKEN_URL,
        params={
            "dhanClientId": client_id,
            "pin": pin,
            "totp": totp_code,
        },
        timeout=timeout,
    )

    if resp.status_code >= 300:
        error_text = resp.text
        
        # Detect specific error modes
        if "Invalid TOTP" in error_text:
            raise DhanTOTPError(f"Invalid TOTP code (status {resp.status_code}): {error_text}")
        
        if "once every 2 minutes" in error_text:
            raise DhanRateLimitError(
                f"Rate limited: token generated within 2 minutes (status {resp.status_code}): {error_text}"
            )
        
        # Generic error
        raise DhanTokenRefreshError(
            f"Dhan token request failed (status {resp.status_code}): {error_text}"
        )

    data = resp.json()
    if not isinstance(data, dict):
        raise DhanTokenRefreshError(f"Unexpected Dhan token response: {resp.text}")

    access_token = str(data.get("accessToken", "")).strip()
    if not access_token:
        raise DhanTokenRefreshError(f"Dhan token response missing accessToken: {json.dumps(data)}")

    return data


def refresh_with_totp_retry(
    client_id: str,
    pin: str,
    totp_seed: str,
    max_retries: int = 1,
    retry_wait_seconds: int = TOTP_RETRY_WAIT_SECONDS,
) -> Dict:
    """
    Request token with automatic TOTP window retry.
    
    If TOTP fails on first attempt, waits for next TOTP window (30s)
    and retries once. Rate limit errors are not retried.
    
    Args:
        client_id: Dhan client ID
        pin: Dhan PIN
        totp_seed: TOTP seed for code generation
        max_retries: Number of TOTP retry attempts
        retry_wait_seconds: Wait time before TOTP retry
    
    Returns:
        Token response dict (accessToken, expiryTime, ...)
    
    Raises:
        DhanRateLimitError: if rate-limited (not retried)
        DhanTokenRefreshError: for other errors after all retries exhausted
    """
    import time as _time
    
    totp_code = generate_totp(totp_seed)
    
    try:
        return request_dhan_token(client_id, pin, totp_code)
    except DhanTOTPError as e:
        if max_retries <= 0:
            raise DhanTokenRefreshError(f"TOTP failed and no retries left: {e}") from e
        
        # TOTP window mismatch — wait for next window and retry
        _time.sleep(retry_wait_seconds)
        totp_code = generate_totp(totp_seed)
        
        try:
            return request_dhan_token(client_id, pin, totp_code)
        except DhanRateLimitError:
            # Rate limit hit on retry means someone else just refreshed.
            # Token is already valid; treat as success.
            raise
        except DhanTOTPError as retry_e:
            raise DhanTokenRefreshError(f"TOTP failed on retry: {retry_e}") from retry_e
    except DhanRateLimitError:
        # Rate limit is not an error — someone else refreshed recently.
        # Token in storage is already valid.
        raise
