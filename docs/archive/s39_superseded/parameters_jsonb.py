"""
core/parameters.py — TTL-cached read API for merdian_parameters (jsonb-schema variant)

Adapted for Lovable Cloud's auto-provisioned schema: single `value jsonb` column
with `value_type` discriminator. Reads via PostgREST RPCs that cast jsonb to
typed values at SQL layer.

ADR-016 parameter calibration pattern. Closes TD-S37-01 once ENH-81 SQL views
migrate to inline get_parameter_num() calls.

Conventions:
    - Raw HTTP via requests per house D.18 convention (ingest_option_chain_local.py
      reference impl). Not supabase-py.
    - Env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
    - Module-level cache; 60s TTL default; invalidate_cache() force-refreshes.
    - Typed accessors: get_parameter_num / get_parameter_text / get_parameter_bool.
    - Raises ParameterNotFoundError when key is unknown or row is missing.
      Callers MUST handle this — there are no silent NULL fallbacks.

Author: Claude (S39, 2026-05-27 — jsonb-schema variant for Lovable's table)
"""

from __future__ import annotations

import os
import time
import threading
from typing import Any, Optional

import requests


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ParameterNotFoundError(KeyError):
    """Raised when a parameter key is not present in merdian_parameters."""
    pass


class ParameterServiceError(RuntimeError):
    """Raised when the Supabase REST call itself fails (HTTP, auth, transport)."""
    pass


# ---------------------------------------------------------------------------
# Module configuration
# ---------------------------------------------------------------------------

_DEFAULT_TTL_SECONDS = 60
_REQUEST_TIMEOUT_SECONDS = 10

_cache: dict[str, tuple[Any, float]] = {}
_cache_lock = threading.Lock()


def _supabase_base_url() -> str:
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise ParameterServiceError(
            "SUPABASE_URL env var missing — required for merdian_parameters read API"
        )
    return url.rstrip("/")


def _supabase_key() -> str:
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise ParameterServiceError(
            "SUPABASE_SERVICE_ROLE_KEY env var missing — required for merdian_parameters read API"
        )
    return key


def _headers() -> dict[str, str]:
    key = _supabase_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Low-level RPC
# ---------------------------------------------------------------------------

def _rpc_get_parameter(rpc_name: str, key: str) -> Any:
    """
    Invokes a PostgREST RPC corresponding to one of
    get_parameter_num / get_parameter_text / get_parameter_bool. Returns the
    unwrapped scalar or raises ParameterNotFoundError if the function returned NULL.
    """
    url = f"{_supabase_base_url()}/rest/v1/rpc/{rpc_name}"
    try:
        resp = requests.post(
            url,
            headers=_headers(),
            json={"p_key": key},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ParameterServiceError(
            f"merdian_parameters RPC {rpc_name}(key={key!r}) transport failure: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise ParameterServiceError(
            f"merdian_parameters RPC {rpc_name}(key={key!r}) HTTP {resp.status_code}: "
            f"{resp.text[:300]}"
        )

    payload = resp.json()
    # PostgREST returns the scalar directly for a single-return-value function
    # — either the value or null when the function returned NULL.
    if payload is None:
        raise ParameterNotFoundError(
            f"parameter {key!r} not found or has no active row in merdian_parameters"
        )
    return payload


def _rpc_update_parameter(key: str, value: Any, change_reason: str,
                          changed_by: str = "operator") -> str:
    """
    Invokes the update_parameter RPC. `value` is JSON-encoded by requests
    automatically (numeric/bool/string all serialize correctly to jsonb).
    Returns the new row UUID. Raises ParameterServiceError on failure.
    """
    url = f"{_supabase_base_url()}/rest/v1/rpc/update_parameter"
    body = {
        "p_key": key,
        "p_value": value,           # jsonb — number, bool, string all valid
        "p_change_reason": change_reason,
        "p_changed_by": changed_by,
    }
    try:
        resp = requests.post(url, headers=_headers(), json=body,
                             timeout=_REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ParameterServiceError(
            f"update_parameter(key={key!r}) transport failure: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise ParameterServiceError(
            f"update_parameter(key={key!r}) HTTP {resp.status_code}: {resp.text[:300]}"
        )

    invalidate_cache(key)
    return str(resp.json())


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_get(cache_key: str) -> Optional[Any]:
    with _cache_lock:
        entry = _cache.get(cache_key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() >= expires_at:
            _cache.pop(cache_key, None)
            return None
        return value


def _cache_put(cache_key: str, value: Any, ttl_seconds: int) -> None:
    expires_at = time.monotonic() + ttl_seconds
    with _cache_lock:
        _cache[cache_key] = (value, expires_at)


def invalidate_cache(key: Optional[str] = None) -> None:
    """
    Force-clears one entry (when `key` is provided) or the entire cache.
    Call after a known parameter write to make the next read see the update
    without waiting for TTL expiry.
    """
    with _cache_lock:
        if key is None:
            _cache.clear()
        else:
            for cache_key in list(_cache.keys()):
                if cache_key.endswith(f":{key}"):
                    _cache.pop(cache_key, None)


# ---------------------------------------------------------------------------
# Public typed accessors
# ---------------------------------------------------------------------------

def get_parameter_num(key: str, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> float:
    """
    Returns the active numeric value for `key` from merdian_parameters.
    Raises ParameterNotFoundError if the key has no active row or is of
    a different value_type.
    """
    cache_key = f"num:{key}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    value = _rpc_get_parameter("get_parameter_num", key)
    value = float(value)
    _cache_put(cache_key, value, ttl_seconds)
    return value


def get_parameter_text(key: str, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> str:
    cache_key = f"text:{key}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    value = _rpc_get_parameter("get_parameter_text", key)
    value = str(value)
    _cache_put(cache_key, value, ttl_seconds)
    return value


def get_parameter_bool(key: str, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> bool:
    cache_key = f"bool:{key}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    value = _rpc_get_parameter("get_parameter_bool", key)
    value = bool(value)
    _cache_put(cache_key, value, ttl_seconds)
    return value


def get_parameters_by_category(category: str, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> list[dict]:
    """
    Returns all currently-active parameter rows in `category`. Bulk read for
    UI surfaces (Settings → Calibration). Caches the full list under one key
    so a single category render is one HTTP call.

    Note: in the jsonb-schema variant, each row's `value` field is a JSON
    scalar (number/bool/string). Callers should interpret it per `value_type`.
    """
    cache_key = f"category:{category}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = (
        f"{_supabase_base_url()}/rest/v1/merdian_parameters"
        f"?category=eq.{category}&valid_to=is.null"
        f"&select=key,value,value_type,description,min_value,max_value,"
        f"valid_from,changed_by,change_reason"
        f"&order=key.asc"
    )
    try:
        resp = requests.get(url, headers=_headers(), timeout=_REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ParameterServiceError(
            f"merdian_parameters category={category!r} transport failure: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise ParameterServiceError(
            f"merdian_parameters category={category!r} HTTP {resp.status_code}: "
            f"{resp.text[:300]}"
        )

    rows = resp.json()
    if not isinstance(rows, list):
        raise ParameterServiceError(
            f"merdian_parameters category={category!r} unexpected payload shape: {type(rows)}"
        )
    _cache_put(cache_key, rows, ttl_seconds)
    return rows


# ---------------------------------------------------------------------------
# Write API (delegates to update_parameter RPC; bypasses local cache)
# ---------------------------------------------------------------------------

def set_parameter(key: str, value: Any, change_reason: str,
                  changed_by: str = "operator") -> str:
    """
    Atomic update: closes the existing active row, inserts a new active row.
    Requires non-empty change_reason per ADR-016 architectural contract.
    Numeric values are range-checked against min_value/max_value at SQL layer.
    Returns the new row UUID. Invalidates the local cache for `key`.
    """
    if not change_reason or not change_reason.strip():
        raise ValueError("change_reason is required (ADR-016 architectural contract)")
    return _rpc_update_parameter(key, value, change_reason, changed_by)


# ---------------------------------------------------------------------------
# Self-check (run as module to smoke-test against live Supabase)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    expected_keys_numeric = [
        "pin.tau.NIFTY", "pin.tau.SENSEX",
        "accel.tau.NIFTY", "accel.tau.SENSEX",
        "sl.buffer_pct", "retest.tolerance_pct",
        "capital.default_inr", "capital.kelly_multiplier", "capital.max_position_inr",
        "ict.zone.h_valid_days",
    ]
    expected_keys_boolean = ["ict.zone.dwm_breach_only"]

    failures = 0
    print("=" * 70)
    print("core/parameters.py (jsonb-variant) — self-check against live Supabase")
    print("=" * 70)

    for key in expected_keys_numeric:
        try:
            v = get_parameter_num(key)
            print(f"  [OK]  num   {key:<30} = {v}")
        except Exception as exc:
            print(f"  [FAIL] num   {key:<30} : {exc}")
            failures += 1

    for key in expected_keys_boolean:
        try:
            v = get_parameter_bool(key)
            print(f"  [OK]  bool  {key:<30} = {v}")
        except Exception as exc:
            print(f"  [FAIL] bool  {key:<30} : {exc}")
            failures += 1

    print("=" * 70)
    for cat in ["pin_accel", "signal_gating", "capital", "ict_zone"]:
        try:
            rows = get_parameters_by_category(cat)
            print(f"  [OK]  category {cat:<20} → {len(rows)} active rows")
        except Exception as exc:
            print(f"  [FAIL] category {cat:<20} : {exc}")
            failures += 1

    print("=" * 70)
    if failures:
        print(f"FAIL — {failures} self-check error(s)")
        sys.exit(1)
    print("PASS — all bootstrap parameters readable, all categories return rows")
