"""E1/E3: push the freshly-minted Dhan token and login status to the retail box
over SSH as a one-line-per-field drop file. Standard library only.

Every function here catches its own exceptions and returns a bool; none of them
ever raises into the caller, writes to .env / system_config / runtime/, or logs
a secret value -- only a name, a byte count and a refusal reason code."""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

SSH_USER = "retaildrop"
MAX_LINES = 8
MAX_BYTES = 4096
_PRINTABLE_LOW = 0x20
_PRINTABLE_HIGH = 0x7E


def _now_ist() -> datetime:
    return datetime.now(IST)


def _log(name: str, content: bytes, ok: bool, reason: str) -> None:
    print(f"DHAN DROP name={name} bytes={len(content)} {'ok' if ok else 'refused'} reason={reason}")


def _unsafe_reason(text: str) -> str | None:
    """Returns a reason code if text is unsafe to send over ssh stdin, else None."""
    if len(text.encode("utf-8")) > MAX_BYTES:
        return "too_large"
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if len(lines) > MAX_LINES:
        return "too_many_lines"
    for ch in text:
        if ch == "\n":
            continue
        if not (_PRINTABLE_LOW <= ord(ch) <= _PRINTABLE_HIGH):
            return "non_ascii"
    return None


def _ssh_put(name: str, content: str) -> bool:
    content_bytes = content.encode("utf-8")
    key_path = os.getenv("MERIDIAN_RETAIL_DROP_KEY", "").strip()
    known_hosts = os.getenv("MERIDIAN_RETAIL_DROP_KNOWN_HOSTS", "").strip()
    host = os.getenv("MERIDIAN_RETAIL_DROP_HOST", "").strip()
    if not key_path or not known_hosts or not host:
        _log(name, content_bytes, False, "not_configured")
        return False
    try:
        result = subprocess.run(
            [
                "ssh",
                "-F", "/dev/null",
                "-i", key_path,
                "-o", "BatchMode=yes",
                "-o", "IdentitiesOnly=yes",
                "-o", "ConnectTimeout=10",
                "-o", "StrictHostKeyChecking=yes",
                "-o", f"UserKnownHostsFile={known_hosts}",
                f"{SSH_USER}@{host}",
                "put", name,
            ],
            input=content_bytes,
            timeout=30,
            capture_output=True,
        )
    except Exception:
        _log(name, content_bytes, False, "ssh_exception")
        return False
    if result.returncode != 0:
        _log(name, content_bytes, False, "ssh_failed")
        return False
    _log(name, content_bytes, True, "sent")
    return True


def send_dhan_drop(access_token: str, expiry_time: str, client_id: str) -> bool:
    try:
        token = (access_token or "").strip()
        if not token:
            _log("dhan", b"", False, "empty_token")
            return False
        client = (client_id or "").strip()
        if not client:
            _log("dhan", b"", False, "empty_client_id")
            return False
        expires = expiry_time.strip() if expiry_time and expiry_time.strip() else "unknown"
        minted_at = _now_ist().isoformat(timespec="seconds")
        values = {
            "broker": "dhan",
            "access_token": token,
            "expires": expires,
            "minted_at": minted_at,
            "client_id": client,
        }
        # Reject an embedded newline in any single value BEFORE joining -- a value
        # carrying its own "\n" would otherwise smuggle an extra key=value line onto
        # the wire that never passed the per-line checks below (secret-key, length).
        if any("\n" in v for v in values.values()):
            _log("dhan", b"", False, "embedded_newline")
            return False
        lines = [f"{k}={v}" for k, v in values.items()]
        probe = "\n".join(lines).encode("utf-8", "replace")
        for line in lines:
            key = line.split("=", 1)[0]
            if "secret" in key.lower():
                _log("dhan", probe, False, "secret_key")
                return False
        if "+05:30" not in minted_at:
            _log("dhan", probe, False, "bad_minted_at")
            return False
        content = "\n".join(lines) + "\n"
        reason = _unsafe_reason(content)
        if reason is not None:
            _log("dhan", content.encode("utf-8", "replace"), False, reason)
            return False
        return _ssh_put("dhan", content)
    except Exception:
        try:
            _log("dhan", b"", False, "exception")
        except Exception:
            pass
        return False


def send_dhan_login_status(ok: bool) -> bool:
    try:
        ts = _now_ist().isoformat(timespec="seconds")
        if "+05:30" not in ts:
            _log("dhan_login_status", b"", False, "bad_minted_at")
            return False
        line = f"{'ok' if ok else 'failed'} {ts}\n"
        reason = _unsafe_reason(line)
        if reason is not None:
            _log("dhan_login_status", line.encode("utf-8", "replace"), False, reason)
            return False
        return _ssh_put("dhan_login_status", line)
    except Exception:
        try:
            _log("dhan_login_status", b"", False, "exception")
        except Exception:
            pass
        return False
