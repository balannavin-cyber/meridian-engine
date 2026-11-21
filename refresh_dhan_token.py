from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict

import pyotp
import requests
from dotenv import load_dotenv

try:
    import dhan_drop
except Exception:
    dhan_drop = None


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
TOKEN_STATUS_FILE = BASE_DIR / "runtime" / "token_status.json"
TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"

IST = timezone(timedelta(hours=5, minutes=30))

# E10 / D2: 300s login-attempt spacing guard, shared by cron, the dashboard
# button and a manual run via one stamp file (bin/dhan_login.sh).
LOGIN_ATTEMPT_STAMP = BASE_DIR / "logs" / "dhan_login_attempt.stamp"
LOGIN_ATTEMPT_SPACING_S = 300


def _now_ist() -> datetime:
    return datetime.now(IST)


def _send_dhan_drop(access_token: str, expiry_time: str, client_id: str) -> bool:
    """E1: a missing or broken dhan_drop helper must never stop the login."""
    if dhan_drop is None:
        return False
    try:
        return bool(dhan_drop.send_dhan_drop(access_token, expiry_time, client_id))
    except Exception:
        return False


def _send_dhan_login_status(ok: bool) -> bool:
    """E3: a missing or broken dhan_drop helper must never stop the login."""
    if dhan_drop is None:
        return False
    try:
        return bool(dhan_drop.send_dhan_login_status(ok))
    except Exception:
        return False


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


def _write_login_attempt_stamp() -> None:
    """E10 / D2: written before every HTTP request to Dhan, including the
    in-run 30s TOTP retry, so a crash mid-request still counts. Creates
    logs/ if it does not exist yet. Fails open: a logs/ that cannot be
    written must never block the request."""
    try:
        LOGIN_ATTEMPT_STAMP.parent.mkdir(parents=True, exist_ok=True)
        tmp = LOGIN_ATTEMPT_STAMP.with_suffix(".stamp.tmp")
        tmp.write_text(_now_ist().isoformat(timespec="seconds"), encoding="utf-8")
        tmp.replace(LOGIN_ATTEMPT_STAMP)
    except OSError:
        print(f"WARNING: could not write login attempt stamp at {LOGIN_ATTEMPT_STAMP}; proceeding anyway.")


def _login_attempt_guard() -> int | None:
    """E10 / D2: seconds remaining if the last login attempt was under
    LOGIN_ATTEMPT_SPACING_S ago, else None (the run is allowed)."""
    if not LOGIN_ATTEMPT_STAMP.exists():
        return None
    try:
        last = datetime.fromisoformat(LOGIN_ATTEMPT_STAMP.read_text(encoding="utf-8").strip())
        age_s = (_now_ist() - last).total_seconds()
    except (OSError, ValueError, TypeError):
        return None
    if 0 <= age_s < LOGIN_ATTEMPT_SPACING_S:
        return max(1, round(LOGIN_ATTEMPT_SPACING_S - age_s))
    return None


def request_dhan_token(client_id: str, pin: str, totp_code: str) -> Dict:
    _write_login_attempt_stamp()
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


def _idempotency_skip() -> bool:
    """OI-21 guard: if token_status.json shows a success less than 90
    seconds old, skip. Protects against any caller double-invoking
    (Task Scheduler + dashboard button + TOTP retry + preflight).
    90s is under Dhan's 120s rate-limit window but comfortably above
    the normal end-to-end refresh duration (~1-2s)."""
    if not TOKEN_STATUS_FILE.exists():
        return False
    try:
        status = json.loads(TOKEN_STATUS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not status.get("success"):
        return False
    iso = status.get("refreshed_at_iso", "")
    if not iso:
        return False
    try:
        last = datetime.fromisoformat(iso)
    except ValueError:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=IST)
    age_s = (datetime.now(IST) - last).total_seconds()
    if 0 <= age_s < 90:
        print(f"[IDEMPOTENT] Token refreshed {age_s:.1f}s ago (< 90s). "
              f"Skipping Dhan call; .env is current.")
        return True
    return False


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)

    # E10 / D2: 300s login-attempt spacing guard. Runs before the OI-21
    # idempotency skip below; in normal operation this guard refuses first,
    # since a success under 90s old is also an attempt under 300s old.
    remaining = _login_attempt_guard()
    if remaining is not None:
        print(f"REFUSED: last login attempt was less than {LOGIN_ATTEMPT_SPACING_S}s ago; "
              f"{remaining}s remaining before the next attempt is allowed.")
        return 3

    # OI-21 fix 2026-04-22: idempotency guard.
    if _idempotency_skip():
        return 0

    try:
        client_id = require_env("DHAN_CLIENT_ID")
        pin = require_env("DHAN_PIN")
        totp_seed = require_env("DHAN_TOTP_SEED")
    except RuntimeError:
        _send_dhan_login_status(False)
        raise

    totp_code = generate_totp(totp_seed)

    try:
        try:
            token_response = request_dhan_token(client_id, pin, totp_code)
        except RuntimeError as e:
            error_msg = str(e)
            # If Invalid TOTP, try next code window
            if "Invalid TOTP" in error_msg:
                import time as _time
                # OI-21 fix 2026-04-22: was sleep(120) which matched
                # Dhan's 2-minute rate-limit window exactly and caused
                # the retry to fail with "Token can be generated once
                # every 2 minutes". TOTP windows are 30 seconds wide;
                # one window is sufficient.
                print("WARNING: Invalid TOTP on first attempt. Waiting 30s for next window...")
                _time.sleep(30)
                totp_code = generate_totp(totp_seed)
                try:
                    token_response = request_dhan_token(client_id, pin, totp_code)
                except RuntimeError as retry_e:
                    retry_msg = str(retry_e)
                    if "once every 2 minutes" in retry_msg:
                        # Another caller (or a prior invocation of ours)
                        # refreshed within 2 minutes. Dhan rejected our
                        # retry but the live token is already valid.
                        # Not a real failure.
                        print(f"INFO: rate-limit hit on retry; token was refreshed elsewhere within 2min. "
                              f"Exiting cleanly. ({retry_msg})")
                        write_token_status(False, "", f"rate_limited_after_totp_retry: {retry_msg}")
                        return 2
                    write_token_status(False, "", retry_msg)
                    _send_dhan_login_status(False)
                    raise
            elif "once every 2 minutes" in error_msg:
                # OI-21 fix: first-attempt rate-limit means someone
                # else just refreshed (likely us within the last 2 min
                # from a concurrent invocation). Token in .env is good.
                print(f"INFO: rate-limit hit on first attempt; token refreshed elsewhere within 2min. "
                      f"Exiting cleanly. ({error_msg})")
                write_token_status(False, "", f"rate_limited: {error_msg}")
                return 2
            else:
                write_token_status(False, "", error_msg)
                _send_dhan_login_status(False)
                raise
    except Exception as e:
        # RuntimeError branches above already sent their own failed status;
        # anything else here (Timeout, ConnectionError, malformed JSON, ...)
        # has not, and must before propagating (D7).
        if not isinstance(e, RuntimeError):
            _send_dhan_login_status(False)
        raise

    access_token = str(token_response["accessToken"]).strip()
    expiry_time = str(token_response.get("expiryTime", "")).strip()

    env_lines = read_env_lines(ENV_PATH)
    env_lines = upsert_env_value(env_lines, "DHAN_API_TOKEN", access_token)
    write_env_lines(ENV_PATH, env_lines)

    # Write token status file for dashboard
    write_token_status(True, expiry_time)

    # E1/E3: push the fresh token + login status to the retail box.
    if _send_dhan_drop(access_token, expiry_time, client_id):
        _send_dhan_login_status(True)

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
