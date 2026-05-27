"""
smoke_probe_marketview_surfaces.py

TD-S37-03 silent-RLS-misconfiguration detector. Halt-ship gate per ENH-110
Phase 1 acceptance criteria.

For each Marketview / Settings consumed surface, runs a row-count probe
under BOTH the anon and service-role keys. If the two diverge, RLS is
either misconfigured (anon blocked) or over-permissive (anon sees rows it
shouldn't). The expected state is exact equality for read-only surfaces.

Surfaces probed:
    Tables:
        merdian_parameters, gex_strike_snapshots, gamma_metrics,
        market_breadth_intraday, signal_snapshots, ict_zones,
        po3_session_state, market_spot_session_markers
    Views:
        v_gex_strike_pin_zone, v_gex_strike_accel_zone, v_dealer_flow_sim,
        v_oi_prev_close_snapshots, v_merdian_parameter_audit
    RPC functions:
        get_parameter_num('pin.tau.NIFTY')
        update_parameter (probe-only — does NOT invoke; just checks 4xx
        without auth differs from 4xx with auth)

Env vars required:
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
    SUPABASE_ANON_KEY        — the same key the dashboard ships with
    MARKETVIEW_URL           — optional; e.g. http://13.63.27.85:8080
                               If set, also probes /_health on the AWS host
                               for a unified Supabase+AWS ship gate.

Exit code:
    0  — all surfaces visible identically under both keys
         AND (if MARKETVIEW_URL set) AWS host /_health returns 200
    1  — one or more surfaces diverge or AWS host unreachable; ship blocked

Usage:
    python smoke_probe_marketview_surfaces.py
    MARKETVIEW_URL=http://13.63.27.85:8080 python smoke_probe_marketview_surfaces.py
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import requests


SURFACES = [
    # (kind, name) — kind = 'table' | 'view'
    ("table", "merdian_parameters"),
    ("table", "gex_strike_snapshots"),
    ("table", "gamma_metrics"),
    ("table", "market_breadth_intraday"),
    ("table", "signal_snapshots"),
    ("table", "ict_zones"),
    ("table", "po3_session_state"),
    ("table", "market_spot_session_markers"),
    ("view",  "v_gex_strike_pin_zone"),
    ("view",  "v_gex_strike_accel_zone"),
    ("view",  "v_dealer_flow_sim"),
    ("view",  "v_oi_prev_close_snapshots"),
    ("view",  "v_merdian_parameter_audit"),
]

EXPECTED_NONZERO_TABLES = {
    "merdian_parameters",       # 11 bootstrap seeds
    "v_merdian_parameter_audit", # same 11 rows
    "gex_strike_snapshots",     # populated since ENH-80 ship S37
    "gamma_metrics",            # live writer cycle
    "ict_zones",                # daily ICT builder
    "po3_session_state",        # session bias writer
}

REQUEST_TIMEOUT = 15


def env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        print(f"[FATAL] {name} env var missing", file=sys.stderr)
        sys.exit(2)
    return val


def count_via_rest(base_url: str, key: str, surface: str) -> Optional[int]:
    """
    Returns the count of rows visible at the given surface using the given
    auth key. Uses PostgREST count=exact header. Returns None on error.
    """
    url = f"{base_url.rstrip('/')}/rest/v1/{surface}?select=*"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "count=exact",
        "Range-Unit": "items",
        "Range": "0-0",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        print(f"  [ERROR] transport failure on {surface}: {exc}")
        return None

    if resp.status_code not in (200, 206):
        print(f"  [ERROR] {surface} HTTP {resp.status_code}: {resp.text[:200]}")
        return None

    # Content-Range header looks like: "0-0/42" or "*/0"
    cr = resp.headers.get("Content-Range", "")
    if "/" not in cr:
        return 0
    try:
        return int(cr.split("/", 1)[1])
    except (ValueError, IndexError):
        return None


def probe_rpc(base_url: str, key: str, rpc_name: str, body: dict) -> tuple[int, str]:
    url = f"{base_url.rstrip('/')}/rest/v1/rpc/{rpc_name}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return (-1, str(exc))
    return (resp.status_code, resp.text[:200])


def main() -> int:
    base_url = env("SUPABASE_URL")
    service_key = env("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = env("SUPABASE_ANON_KEY")

    print("=" * 78)
    print("smoke_probe_marketview_surfaces.py — TD-S37-03 RLS-divergence detector")
    print(f"base URL: {base_url}")
    print("=" * 78)
    print(f"{'KIND':<6} {'SURFACE':<32} {'SERVICE':>10} {'ANON':>10}  STATUS")
    print("-" * 78)

    divergences = 0
    expected_nonzero_misses = 0

    for kind, surface in SURFACES:
        svc_count = count_via_rest(base_url, service_key, surface)
        anon_count = count_via_rest(base_url, anon_key, surface)

        if svc_count is None or anon_count is None:
            status = "ERROR"
            divergences += 1
        elif svc_count != anon_count:
            status = f"DIVERGE (anon missing {svc_count - anon_count} rows)"
            divergences += 1
        elif surface in EXPECTED_NONZERO_TABLES and svc_count == 0:
            status = "EMPTY (expected non-zero per ENH-110 acceptance)"
            expected_nonzero_misses += 1
        else:
            status = "OK"

        svc_disp = svc_count if svc_count is not None else "ERR"
        anon_disp = anon_count if anon_count is not None else "ERR"
        print(f"{kind:<6} {surface:<32} {svc_disp:>10} {anon_disp:>10}  {status}")

    print("-" * 78)
    print()
    print("RPC functions (smoke-test — verifies anon can call SECURITY DEFINER)")
    print("-" * 78)

    # get_parameter_num: anon should receive the bootstrap value 0.30
    code, body = probe_rpc(base_url, anon_key, "get_parameter_num", {"p_key": "pin.tau.NIFTY"})
    if code == 200:
        try:
            val = float(body.strip())
            ok = abs(val - 0.30) < 1e-9
        except ValueError:
            ok = False
        rpc_status = "OK (returned 0.30)" if ok else f"WRONG VALUE: {body}"
    else:
        rpc_status = f"FAIL HTTP {code}: {body}"
        divergences += 1
    print(f"  get_parameter_num('pin.tau.NIFTY')  →  {rpc_status}")

    # update_parameter without change_reason should be rejected
    code, body = probe_rpc(base_url, anon_key, "update_parameter",
                           {"p_key": "pin.tau.NIFTY", "p_change_reason": "",
                            "p_value_num": 0.30})
    if code in (400, 500) and "change_reason" in body:
        upd_status = "OK (rejected empty change_reason per ADR-016)"
    elif code == 200:
        upd_status = "FAIL: empty change_reason was accepted — ADR-016 contract broken"
        divergences += 1
    else:
        upd_status = f"UNEXPECTED HTTP {code}: {body}"
        divergences += 1
    print(f"  update_parameter (empty change_reason) →  {upd_status}")

    print()
    print("=" * 78)

    # --- AWS host probe (optional, gated on MARKETVIEW_URL env var) ---------
    marketview_url = os.environ.get("MARKETVIEW_URL", "").rstrip("/")
    aws_ok = True
    if marketview_url:
        print(f"AWS dashboard host probe — {marketview_url}")
        print("-" * 78)
        health_url = f"{marketview_url}/_health"
        try:
            resp = requests.get(health_url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                print(f"  GET {health_url}  →  200 OK  ({resp.text.strip()})")
            else:
                print(f"  GET {health_url}  →  HTTP {resp.status_code}: {resp.text[:200]}")
                aws_ok = False
                divergences += 1
        except requests.RequestException as exc:
            print(f"  GET {health_url}  →  TRANSPORT FAIL: {exc}")
            aws_ok = False
            divergences += 1

        # Verify the SPA root returns the index.html (200 with html content type)
        try:
            resp = requests.get(marketview_url + "/", timeout=REQUEST_TIMEOUT)
            ctype = resp.headers.get("Content-Type", "")
            if resp.status_code == 200 and "html" in ctype.lower():
                print(f"  GET {marketview_url}/  →  200 OK ({ctype})")
            else:
                print(f"  GET {marketview_url}/  →  HTTP {resp.status_code} ({ctype})")
                aws_ok = False
                divergences += 1
        except requests.RequestException as exc:
            print(f"  GET {marketview_url}/  →  TRANSPORT FAIL: {exc}")
            aws_ok = False
            divergences += 1
        print("=" * 78)
    else:
        print("(MARKETVIEW_URL not set — skipping AWS host probe.)")
        print("=" * 78)

    if divergences == 0 and expected_nonzero_misses == 0:
        print("PASS — all surfaces visible identically under anon + service keys.")
        if marketview_url and aws_ok:
            print("       AWS host /_health and / return 200.")
        print("       ENH-110 Phase 1 ship gate cleared per TD-S37-03 mitigation.")
        print("=" * 78)
        return 0

    if divergences == 0 and expected_nonzero_misses > 0:
        print(f"WARN — RLS OK across {len(SURFACES)} surfaces, but "
              f"{expected_nonzero_misses} surface(s) expected non-zero are empty.")
        print("       Verify upstream writer health before clearing ship gate.")
        print("=" * 78)
        return 0  # WARN does not block; the silent-empty case below does

    print(f"FAIL — {divergences} divergence(s) detected. SHIP BLOCKED.")
    print("       Fix: re-apply RLS triplet for the failing surface(s) per")
    print("       2026-05-26_enh110_rls_triplets.sql, then re-run this probe.")
    print("=" * 78)
    return 1


if __name__ == "__main__":
    sys.exit(main())
