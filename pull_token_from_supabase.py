#!/usr/bin/env python3
"""
MERDIAN — pull_token_from_supabase.py with S42 Phase 1.b staleness check (TD-S41-NEW-2)
"""
from __future__ import annotations

import os
import socket
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv


class TokenStalenessError(Exception):
    """Raised when pulled token is older than acceptable threshold (>18h)."""
    pass


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
IST = timezone(timedelta(hours=5, minutes=30))

DHAN_LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
DHAN_EXPIRYLIST_URL = "https://api.dhan.co/v2/optionchain/expirylist"

PROBE_TIMEOUT_SECONDS = 8
SUPABASE_TIMEOUT_SECONDS = 15
AUDIT_LOG_TIMEOUT_SECONDS = 10

HOST_TAG = "aws"
SCRIPT_TAG = "pull_token_from_supabase.py"


def _now_ist_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def log(msg: str) -> None:
    print(f"[{_now_ist_str()}] {msg}", flush=True)


def mask(token: str) -> str:
    if not token:
        return "<empty>"
    n = len(token)
    if n < 12:
        return f"<short:{n}>"
    return f"{token[:6]}...{token[-6:]}"


def _audit_payload(
    *,
    event: str,
    endpoint: Optional[str],
    token: str,
    token_source: str,
    http_status: Optional[int],
    response_excerpt: Optional[str],
    notes: Optional[str],
) -> dict:
    return {
        "host": HOST_TAG,
        "script": SCRIPT_TAG,
        "event": event,
        "endpoint": endpoint,
        "token_prefix": (token[:6] if token else None),
        "token_suffix": (token[-6:] if token and len(token) >= 6 else None),
        "token_length": (len(token) if token else 0),
        "token_source": token_source,
        "http_status": http_status,
        "response_excerpt": (response_excerpt[:200] if response_excerpt else None),
        "notes": notes,
    }


def write_audit_row(supabase_url: str, supabase_key: str, payload: dict) -> None:
    try:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        r = requests.post(
            f"{supabase_url}/rest/v1/dhan_token_probe_log",
            headers=headers,
            json=payload,
            timeout=AUDIT_LOG_TIMEOUT_SECONDS,
        )
        if r.status_code >= 300:
            log(f"WARN: audit row write returned {r.status_code}: {r.text[:120]}")
    except Exception as e:
        log(f"WARN: audit row write failed (non-fatal): {type(e).__name__}: {e}")


def probe_dhan_endpoint(
    url: str,
    *,
    payload: dict,
    token: str,
    client_id: str,
) -> tuple[Optional[int], str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "access-token": token,
        "client-id": client_id,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=PROBE_TIMEOUT_SECONDS)
        return r.status_code, (r.text or "")
    except Exception as e:
        return None, f"<exception: {type(e).__name__}: {e}>"


def atomic_write_env(env_path: Path, token: str) -> tuple[bool, str]:
    try:
        if not env_path.exists():
            return False, f".env not found at {env_path}"
        env_text = env_path.read_text(encoding="utf-8")
        lines = env_text.splitlines()
        updated: list[str] = []
        replaced = False
        for line in lines:
            if line.startswith("DHAN_API_TOKEN="):
                updated.append(f"DHAN_API_TOKEN={token}")
                replaced = True
            else:
                updated.append(line)
        if not replaced:
            updated.append(f"DHAN_API_TOKEN={token}")
        out_text = "\n".join(updated).rstrip() + "\n"

        tmp = env_path.with_suffix(env_path.suffix + ".tmp")
        tmp.write_text(out_text, encoding="utf-8")
        tmp.replace(env_path)
        return True, f"replaced_existing={replaced}"
    except Exception as e:
        return False, f"<exception: {type(e).__name__}: {e}>"


def readback_token_from_env(env_path: Path) -> str:
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DHAN_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)

    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    dhan_client_id = os.getenv("DHAN_CLIENT_ID", "").strip()

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing from .env",
              file=sys.stderr)
        return 1

    log(f"Pull starting on host={socket.gethostname()}")

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
    }
    try:
        r = requests.get(
            f"{supabase_url}/rest/v1/system_config"
            f"?config_key=eq.dhan_api_token"
            f"&select=config_value,updated_at,updated_by",
            headers=headers,
            timeout=SUPABASE_TIMEOUT_SECONDS,
        )
    except Exception as e:
        print(f"ERROR: Supabase GET exception: {type(e).__name__}: {e}",
              file=sys.stderr)
        return 1

    if r.status_code != 200:
        print(f"ERROR: Supabase returned {r.status_code}: {r.text}",
              file=sys.stderr)
        return 1

    rows = r.json()
    if not rows:
        print("ERROR: No dhan_api_token row found in system_config",
              file=sys.stderr)
        return 1

    token = (rows[0].get("config_value") or "").strip()
    sb_updated_at = str(rows[0].get("updated_at", "") or "")
    sb_updated_by = str(rows[0].get("updated_by", "") or "")

    if not token or token == "placeholder":
        print("ERROR: Token in Supabase is empty or still placeholder",
              file=sys.stderr)
        return 1

    # STALENESS CHECK: TD-S41-NEW-2 interim fix
    try:
        token_updated = datetime.fromisoformat(sb_updated_at.replace("Z", "+00:00"))
        token_age_hours = (datetime.now(timezone.utc) - token_updated).total_seconds() / 3600
        if token_age_hours > 18:
            msg = (f"TokenStalenessError: pulled token is {token_age_hours:.1f}h old "
                   f"(> 18h threshold). Local refresh may have failed. "
                   f"Check Local Task Scheduler task MERDIAN_Dhan_Token_Refresh. "
                   f"updated_at={sb_updated_at}")
            print(f"ERROR: {msg}", file=sys.stderr)
            write_audit_row(
                supabase_url, supabase_key,
                _audit_payload(
                    event="staleness_check_failed",
                    endpoint=None,
                    token=token,
                    token_source="supabase_system_config",
                    http_status=None,
                    response_excerpt=None,
                    notes=msg,
                ),
            )
            raise TokenStalenessError(msg)
    except ValueError as e:
        log(f"WARN: Could not parse token updated_at={sb_updated_at!r} as ISO datetime: {e} "
            f"(staleness check skipped; assuming fresh)")

    log(f"Pulled from Supabase: token={mask(token)} len={len(token)} "
        f"updated_at={sb_updated_at} updated_by={sb_updated_by}")

    ok, msg = atomic_write_env(ENV_PATH, token)
    if not ok:
        print(f"ERROR: .env atomic write failed: {msg}", file=sys.stderr)
        return 1
    log(f".env atomic write OK ({msg})")

    readback = readback_token_from_env(ENV_PATH)
    readback_match = (readback == token)
    if not readback_match:
        log(f"WARN: .env readback MISMATCH! pulled={mask(token)} readback={mask(readback)}")
    else:
        log(f".env readback confirms token={mask(readback)}")

    write_audit_row(
        supabase_url, supabase_key,
        _audit_payload(
            event="pull_write",
            endpoint=None,
            token=token,
            token_source="supabase_system_config",
            http_status=200,
            response_excerpt=None,
            notes=(f"sb_updated_at={sb_updated_at} "
                   f"sb_updated_by={sb_updated_by} "
                   f"readback_match={readback_match}"),
        ),
    )

    if not dhan_client_id:
        log("WARN: DHAN_CLIENT_ID missing — skipping post-write probes "
            "(token write itself succeeded; cron exit clean)")
        print("Token pulled from Supabase and written to .env successfully.")
        return 0

    log("--- Post-write Dhan endpoint probes (TD-080 diagnostic) ---")

    log("Probe 1/2: POST /v2/marketfeed/ltp body={IDX_I:[13]}")
    status1, body1 = probe_dhan_endpoint(
        DHAN_LTP_URL,
        payload={"IDX_I": [13]},
        token=token,
        client_id=dhan_client_id,
    )
    log(f"Probe 1 result: status={status1} body[:120]={body1[:120]!r}")
    write_audit_row(
        supabase_url, supabase_key,
        _audit_payload(
            event="post_write_probe",
            endpoint="/v2/marketfeed/ltp",
            token=token,
            token_source="freshly_pulled",
            http_status=status1,
            response_excerpt=body1,
            notes="probe_index=1 symbol=NIFTY segment=IDX_I",
        ),
    )

    log("Probe 2/2: POST /v2/optionchain/expirylist body={UnderlyingScrip:13,UnderlyingSeg:IDX_I}")
    status2, body2 = probe_dhan_endpoint(
        DHAN_EXPIRYLIST_URL,
        payload={"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"},
        token=token,
        client_id=dhan_client_id,
    )
    log(f"Probe 2 result: status={status2} body[:120]={body2[:120]!r}")
    write_audit_row(
        supabase_url, supabase_key,
        _audit_payload(
            event="post_write_probe",
            endpoint="/v2/optionchain/expirylist",
            token=token,
            token_source="freshly_pulled",
            http_status=status2,
            response_excerpt=body2,
            notes="probe_index=2 symbol=NIFTY segment=IDX_I",
        ),
    )

    if status1 == 200 and status2 == 200:
        log("VERDICT: both probes 200 OK at write time. Token is full-scope at issuance.")
    elif status1 == 200 and status2 != 200:
        log(f"VERDICT: DECISIVE asymmetry. /marketfeed/ltp=200 but /optionchain/expirylist={status2}.")
    elif status1 != 200 and status2 == 200:
        log(f"VERDICT: INVERSE asymmetry. /optionchain/expirylist=200 but /marketfeed/ltp={status1}.")
    else:
        log(f"VERDICT: BOTH probes failed. ltp={status1} expirylist={status2}.")

    print("Token pulled from Supabase and written to .env successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
