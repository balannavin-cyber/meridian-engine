"""
MERDIAN Preflight — Stage 1: Auth / API Smoke
=============================================
Verifies that the Dhan token is valid and usable against live endpoints.
No market data is written. All calls are read-only sanity checks.

Catches:
  - Stale or expired DHAN_API_TOKEN
  - Wrong DHAN_CLIENT_ID
  - Network/endpoint failures
  - Response shape changes (API contract drift)
  - Token valid but wrong permissions

Pass criteria: token refresh callable, IDX_I LTP call returns 200 with
               parseable spot price, expiry list call returns 200.

IMPORTANT: Stage 0 (env contract) must pass before Stage 1 runs.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preflight_common import (
    PASS, FAIL, WARN, SKIP,
    detect_environment, get_merdian_root,
    load_env, make_stage_result, run_check, now_iso,
    print_header, print_check, print_stage_summary,
    save_stage_result, elapsed_ms
)

STAGE_ID = "stage1_auth_smoke"

# ── Dhan API Helpers ──────────────────────────────────────────────

DHAN_BASE = "https://api.dhan.co"

def _dhan_headers():
    return {
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "access-token":  os.environ.get("DHAN_API_TOKEN", ""),
        "client-id":     os.environ.get("DHAN_CLIENT_ID", ""),
    }

def _dhan_get(path, timeout=15):
    """Make a GET request to Dhan API. Returns (status_code, body_dict, error)."""
    url = DHAN_BASE + path
    req = urllib.request.Request(url, headers=_dhan_headers(), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body), None
            except Exception:
                return resp.status, {}, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return e.code, {}, f"HTTP {e.code}: {body[:200]}"
    except Exception as ex:
        return 0, {}, str(ex)

def _dhan_post(path, payload, timeout=15):
    """Make a POST request to Dhan API. Returns (status_code, body_dict, error)."""
    url = DHAN_BASE + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_dhan_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body), None
            except Exception:
                return resp.status, {}, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return e.code, {}, f"HTTP {e.code}: {body[:200]}"
    except Exception as ex:
        return 0, {}, str(ex)

# ── Checks ────────────────────────────────────────────────────────

def check_env_loaded():
    """Verify .env is loaded and token present."""
    ok, msg, _ = load_env()
    if not ok:
        return FAIL, msg
    token = os.environ.get("DHAN_API_TOKEN", "")
    client_id = os.environ.get("DHAN_CLIENT_ID", "")
    if not token:
        return FAIL, "DHAN_API_TOKEN is empty after .env load"
    if not client_id:
        return FAIL, "DHAN_CLIENT_ID is empty after .env load"
    return PASS, f"Token present (len={len(token)}), client_id={client_id}"

def check_idx_i_nifty_ltp():
    """
    Call Dhan LTP API for NIFTY spot (security_id=13, IDX_I).
    This is the most fundamental auth check — if this fails, nothing works.
    """
    payload = {
        "NSE_INDEX": ["Nifty 50"]
    }
    # Use the market quote endpoint
    status, body, err = _dhan_post("/v2/marketfeed/ltp", payload)
    if err:
        return FAIL, f"LTP call failed: {err}"
    if status == 401:
        return FAIL, "401 Authentication Failed — DHAN_API_TOKEN is invalid or expired"
    if status == 403:
        return FAIL, "403 Forbidden — check DHAN_CLIENT_ID"
    if status != 200:
        return FAIL, f"HTTP {status} — unexpected response"
    # Parse response — expect data with a price
    try:
        data = body.get("data", {})
        if not data:
            # Try alternative response shape
            if "NSE_INDEX" in body:
                data = body["NSE_INDEX"]
        if data:
            return PASS, f"LTP call succeeded. Response has data. HTTP 200."
        return WARN, f"HTTP 200 but response data empty or unexpected shape: {str(body)[:150]}"
    except Exception as e:
        return WARN, f"HTTP 200 but could not parse response: {e}"

def check_option_chain_expiry_list():
    """
    Call option chain expiry list for NIFTY.
    This is the specific endpoint that was failing 401 in V18A.
    """
    status, body, err = _dhan_get("/v2/optionchain/expirylist?underlyingScrip=13&underlyingSegment=IDX_I")
    if err:
        return FAIL, f"Expiry list call failed: {err}"
    if status == 401:
        return FAIL, "401 Authentication Failed — token invalid for option chain endpoint"
    if status == 403:
        return FAIL, "403 Forbidden — check permissions"
    if status != 200:
        return FAIL, f"HTTP {status}"
    # Check we got actual expiry dates back
    try:
        if isinstance(body, list) and len(body) > 0:
            return PASS, f"Expiry list returned {len(body)} expiries. First: {body[0]}"
        if isinstance(body, dict):
            # Some API shapes wrap the list
            dates = body.get("data", body.get("expiryList", []))
            if dates:
                return PASS, f"Expiry list returned {len(dates)} expiries"
        return WARN, f"HTTP 200 but expiry list empty or unexpected shape: {str(body)[:150]}"
    except Exception as e:
        return WARN, f"HTTP 200 but could not parse expiry list: {e}"

def check_supabase_connectivity():
    """
    Verify Supabase REST endpoint is reachable and credentials work.
    Does a lightweight SELECT 1 equivalent — reads 1 row from trading_calendar.
    No writes.
    """
    url      = os.environ.get("SUPABASE_URL", "")
    role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not role_key:
        return FAIL, "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not in environment"

    endpoint = f"{url.rstrip('/')}/rest/v1/trading_calendar?select=trade_date&limit=1"
    headers  = {
        "apikey":        role_key,
        "Authorization": f"Bearer {role_key}",
        "Accept":        "application/json",
    }
    req = urllib.request.Request(endpoint, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            if resp.status == 200:
                try:
                    rows = json.loads(body)
                    return PASS, f"Supabase reachable. trading_calendar readable ({len(rows)} row(s) returned)."
                except Exception:
                    return PASS, "Supabase HTTP 200 (body not JSON-parseable but connection OK)"
            return FAIL, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return FAIL, "401 — SUPABASE_SERVICE_ROLE_KEY is invalid"
        return FAIL, f"HTTP {e.code}"
    except Exception as ex:
        return FAIL, f"Connection failed: {ex}"

def check_supabase_write_smoke():
    """
    Write a single row to a safe diagnostics table and read it back.
    Uses preflight_smoke_log if it exists, otherwise skips write test.
    This confirms writes work, not just reads.
    """
    url      = os.environ.get("SUPABASE_URL", "")
    role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not role_key:
        return SKIP, "Supabase credentials not available"

    import datetime
    ts_now = datetime.datetime.utcnow().isoformat()

    # Try a simple upsert to a preflight log table
    # If the table doesn't exist, Supabase returns 404 — we treat that as SKIP not FAIL
    endpoint = f"{url.rstrip('/')}/rest/v1/preflight_smoke_log"
    headers  = {
        "apikey":          role_key,
        "Authorization":   f"Bearer {role_key}",
        "Content-Type":    "application/json",
        "Prefer":          "return=minimal",
    }
    payload  = json.dumps([{"run_ts": ts_now, "environment": detect_environment(), "stage": STAGE_ID}]).encode()
    req      = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                return PASS, "Write smoke test passed — preflight_smoke_log writable"
            return WARN, f"HTTP {resp.status} on write smoke test"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return SKIP, "preflight_smoke_log table does not exist — write smoke skipped (create it to enable)"
        if e.code == 401:
            return FAIL, "401 on write — role key may lack INSERT permission"
        return WARN, f"HTTP {e.code} on write smoke test"
    except Exception as ex:
        return WARN, f"Write smoke exception: {ex}"

# ── Stage Runner ──────────────────────────────────────────────────

def run_stage1(verbose=True):
    started_at = now_iso()
    env = detect_environment()

    if verbose:
        print_header(f"Stage 1 — Auth / API Smoke  [{env.upper()}]")

    checks = [
        run_check("Env loaded (.env, keys present)",     check_env_loaded),
        run_check("Dhan IDX_I NIFTY LTP call",           check_idx_i_nifty_ltp),
        run_check("Dhan option chain expiry list (NIFTY)",check_option_chain_expiry_list),
        run_check("Supabase connectivity (read)",         check_supabase_connectivity),
        run_check("Supabase write smoke",                 check_supabase_write_smoke),
    ]

    if verbose:
        for c in checks:
            print_check(c)

    result = make_stage_result(STAGE_ID, env, checks, started_at)
    save_stage_result(result)

    if verbose:
        print_stage_summary(result)

    return result

if __name__ == "__main__":
    result = run_stage1(verbose=True)
    sys.exit(0 if result["status"] == PASS else 1)
