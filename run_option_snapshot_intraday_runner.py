from __future__ import annotations

import atexit
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from trading_calendar import (
    MissingSessionConfigError,
    TradingCalendarError,
    current_session_state,
)

IST = ZoneInfo("Asia/Kolkata")

BASE_DIR = Path(r"C:\GammaEnginePython")
LOG_PATH = BASE_DIR / "option_snapshot_intraday_runner.log"
LOCK_PATH = BASE_DIR / "run_option_snapshot_intraday_runner.lock"

SYMBOLS = ["NIFTY", "SENSEX"]

CYCLE_MINUTES = 5

TIMEOUT_LIVE_DEFAULT = 240
TIMEOUT_SHADOW_DEFAULT = 180
TIMEOUT_BREADTH = 300
TIMEOUT_WCB = 180
TIMEOUT_INGEST = 240
TIMEOUT_ARCHIVE = 180
TIMEOUT_GAMMA = 240
TIMEOUT_VOL = 240
TIMEOUT_MOMENTUM = 240
TIMEOUT_STATE = 240
TIMEOUT_SIGNAL = 240
TIMEOUT_SHADOW_SIGNAL = 180

SHADOW_FAILURE_IS_NON_BLOCKING = True

LOCK_STALE_SECONDS = 900
LOCK_HEARTBEAT_UPDATE_SECONDS = 15

UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}\b"
)


def now_ist() -> datetime:
    return datetime.now(IST)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ts() -> str:
    return now_ist().strftime("%Y-%m-%d %H:%M:%S %Z")


def log(message: str) -> None:
    line = f"[{ts()}] {message}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_active_market_session() -> bool:
    try:
        return current_session_state() == "REGULAR_SESSION"
    except (MissingSessionConfigError, TradingCalendarError) as exc:
        log(f"Trading calendar unavailable for option runner: {exc}")
        return False


def next_cycle_time(dt: datetime) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    minute_bucket = (dt.minute // CYCLE_MINUTES) * CYCLE_MINUTES
    current_bucket = dt.replace(minute=minute_bucket)
    if dt == current_bucket:
        return dt
    return current_bucket + timedelta(minutes=CYCLE_MINUTES)


def sleep_until(target: datetime) -> None:
    while True:
        now = now_ist()
        remaining = (target - now).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 5))


def _read_lock_payload() -> dict:
    if not LOCK_PATH.exists():
        return {}
    try:
        raw = LOCK_PATH.read_text(encoding="utf-8").strip()
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _write_lock_payload(payload: dict) -> None:
    LOCK_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _process_is_running(pid: int | None) -> bool:
    if not pid:
        return False

    try:
        if os.name == "nt":
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return str(pid) in proc.stdout
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def _parse_iso_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def update_lock_heartbeat() -> None:
    if not LOCK_PATH.exists():
        return

    payload = _read_lock_payload()
    payload["pid"] = os.getpid()
    payload["last_heartbeat_utc"] = now_utc_iso()
    payload["last_heartbeat_local"] = ts()
    _write_lock_payload(payload)


def acquire_lock() -> None:
    if LOCK_PATH.exists():
        data = _read_lock_payload()

        pid = data.get("pid")
        created_at = float(data.get("created_at_epoch", 0) or 0)
        last_heartbeat = _parse_iso_datetime(data.get("last_heartbeat_utc"))

        age = time.time() - created_at if created_at else None
        heartbeat_age = None
        if last_heartbeat is not None:
            heartbeat_age = (datetime.now(timezone.utc) - last_heartbeat).total_seconds()

        alive = _process_is_running(pid)
        stale = False
        if heartbeat_age is not None:
            stale = heartbeat_age > LOCK_STALE_SECONDS
        elif age is not None:
            stale = age > LOCK_STALE_SECONDS

        # IMPORTANT:
        # Do NOT reclaim a lock if the process still appears alive.
        # That risks double runners.
        if alive:
            log(
                f"Another runner appears active (pid={pid}, stale={stale}, "
                f"heartbeat_age={heartbeat_age}). Exiting."
            )
            sys.exit(255)

        log(
            f"Reclaiming stale/dead lock file "
            f"(pid={pid}, stale={stale}, alive={alive}, heartbeat_age={heartbeat_age})."
        )
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except Exception as e:
            log(f"WARNING: Failed to remove stale lock: {e}")

    payload = {
        "pid": os.getpid(),
        "created_at_epoch": time.time(),
        "created_at_local": ts(),
        "created_at_utc": now_utc_iso(),
        "last_heartbeat_utc": now_utc_iso(),
        "last_heartbeat_local": ts(),
        "script": Path(__file__).name,
    }
    _write_lock_payload(payload)
    log(f"Lock acquired: {LOCK_PATH}")


def release_lock() -> None:
    try:
        if LOCK_PATH.exists():
            data = _read_lock_payload()
            lock_pid = data.get("pid")
            if lock_pid is None or int(lock_pid) == os.getpid():
                LOCK_PATH.unlink()
                log(f"Lock released: {LOCK_PATH}")
            else:
                log(
                    f"Lock file not removed because it belongs to another pid "
                    f"(lock pid={lock_pid}, current pid={os.getpid()})."
                )
    except Exception as e:
        log(f"WARNING: Failed to release lock: {e}")


def handle_exit(signum=None, frame=None) -> None:
    if signum is not None:
        log(f"Received signal {signum}. Shutting down.")
    release_lock()
    raise SystemExit(0)


def run_cmd(args: list[str], timeout: int, step_name: str, non_blocking: bool = False) -> tuple[bool, str]:
    cmd_str = " ".join(f'"{a}"' if " " in a else a for a in args)
    log(f"START {step_name}: {cmd_str}")

    try:
        proc = subprocess.run(
            args,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if stdout:
            log(f"{step_name} STDOUT:\n{stdout}")
        if stderr:
            log(f"{step_name} STDERR:\n{stderr}")

        if proc.returncode != 0:
            msg = f"{step_name} failed with return code {proc.returncode}"
            if non_blocking:
                log(f"WARNING: {msg} (non-blocking)")
                return False, stdout
            raise RuntimeError(msg)

        log(f"END {step_name}: success")
        return True, stdout

    except subprocess.TimeoutExpired:
        msg = f"{step_name} timed out after {timeout}s"
        if non_blocking:
            log(f"WARNING: {msg} (non-blocking)")
            return False, ""
        raise RuntimeError(msg)


def run_with_fallbacks(
    script_name: str,
    arg_variants: list[list[str]],
    timeout: int,
    step_name: str,
    non_blocking: bool = False,
) -> tuple[bool, str]:
    py = sys.executable
    last_error = None

    for variant in arg_variants:
        args = [py, str(BASE_DIR / script_name), *variant]
        try:
            ok, out = run_cmd(args, timeout=timeout, step_name=step_name, non_blocking=False)
            return ok, out
        except Exception as e:
            last_error = e
            log(f"{step_name}: variant failed -> {variant} :: {e}")

    if non_blocking:
        log(f"WARNING: {step_name} failed across all variants (non-blocking): {last_error}")
        return False, ""

    raise RuntimeError(f"{step_name} failed across all variants: {last_error}")


def extract_run_id(stdout: str) -> str:
    if not stdout:
        raise RuntimeError("No stdout returned by ingest step; cannot extract run_id.")

    matches = UUID_RE.findall(stdout)
    if not matches:
        raise RuntimeError("Unable to find UUID run_id in ingest stdout.")

    for line in stdout.splitlines():
        if "run id" in line.lower():
            m = UUID_RE.search(line)
            if m:
                return m.group(0)

    return matches[-1]


def run_live_cycle_for_symbol(symbol: str) -> None:
    log(f"========== LIVE PIPELINE START [{symbol}] ==========")

    ok, ingest_out = run_with_fallbacks(
        "ingest_option_chain_local.py",
        [[symbol]],
        timeout=TIMEOUT_INGEST,
        step_name=f"{symbol} ingest_option_chain",
    )
    if not ok:
        raise RuntimeError(f"{symbol} ingest failed unexpectedly.")

    run_id = extract_run_id(ingest_out)
    log(f"{symbol} run_id extracted: {run_id}")

    run_with_fallbacks(
        "archive_option_chain_history.py",
        [[run_id]],
        timeout=TIMEOUT_ARCHIVE,
        step_name=f"{symbol} archive_option_chain_history",
    )

    run_with_fallbacks(
        "compute_gamma_metrics_local.py",
        [[run_id, symbol], [symbol, run_id], [run_id]],
        timeout=TIMEOUT_GAMMA,
        step_name=f"{symbol} compute_gamma_metrics",
    )

    run_with_fallbacks(
        "compute_volatility_metrics_local.py",
        [[run_id, symbol], [symbol, run_id], [run_id]],
        timeout=TIMEOUT_VOL,
        step_name=f"{symbol} compute_volatility_metrics",
    )

    run_with_fallbacks(
        "build_momentum_features_local.py",
        [[symbol]],
        timeout=TIMEOUT_MOMENTUM,
        step_name=f"{symbol} build_momentum_features_live",
        non_blocking=True,
    )

    run_with_fallbacks(
        "build_market_state_snapshot_local.py",
        [[symbol]],
        timeout=TIMEOUT_STATE,
        step_name=f"{symbol} build_market_state",
    )

    run_with_fallbacks(
        "build_trade_signal_local.py",
        [[symbol]],
        timeout=TIMEOUT_SIGNAL,
        step_name=f"{symbol} build_trade_signal_live",
    )

    run_with_fallbacks(
        "compute_options_flow_local.py",
        [[run_id, symbol], [symbol, run_id], [run_id], [symbol]],
        timeout=TIMEOUT_SHADOW_DEFAULT,
        step_name=f"{symbol} compute_options_flow",
        non_blocking=SHADOW_FAILURE_IS_NON_BLOCKING,
    )

    run_with_fallbacks(
        "compute_momentum_features_v2_local.py",
        [[symbol]],
        timeout=TIMEOUT_SHADOW_DEFAULT,
        step_name=f"{symbol} compute_momentum_features_v2",
        non_blocking=SHADOW_FAILURE_IS_NON_BLOCKING,
    )

    run_with_fallbacks(
        "compute_smdm_local.py",
        [[symbol, run_id], [run_id, symbol], [symbol], [run_id]],
        timeout=TIMEOUT_SHADOW_DEFAULT,
        step_name=f"{symbol} compute_smdm",
        non_blocking=SHADOW_FAILURE_IS_NON_BLOCKING,
    )

    run_with_fallbacks(
        "build_shadow_signal_v3_local.py",
        [[symbol]],
        timeout=TIMEOUT_SHADOW_SIGNAL,
        step_name=f"{symbol} build_shadow_signal_v3",
        non_blocking=SHADOW_FAILURE_IS_NON_BLOCKING,
    )

    log(f"========== LIVE PIPELINE END [{symbol}] ==========")


def run_full_cycle() -> None:
    cycle_started = now_ist()
    log("==================================================")
    log("CYCLE START")
    log("==================================================")

    run_with_fallbacks(
        "ingest_breadth_intraday_local.py",
        [[]],
        timeout=TIMEOUT_BREADTH,
        step_name="ingest_breadth_intraday",
    )

    run_with_fallbacks(
        "build_wcb_snapshot_local.py",
        [[], ["NIFTY"], ["SENSEX"]],
        timeout=TIMEOUT_WCB,
        step_name="build_wcb_snapshot",
    )

    for symbol in SYMBOLS:
        run_live_cycle_for_symbol(symbol)

    duration = (now_ist() - cycle_started).total_seconds()
    log(f"CYCLE END — duration={duration:.1f}s")
    log("")


def main() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    atexit.register(release_lock)

    acquire_lock()
    log("Runner started.")

    last_heartbeat_write = 0.0

    while True:
        now_epoch = time.time()
        if now_epoch - last_heartbeat_write >= LOCK_HEARTBEAT_UPDATE_SECONDS:
            update_lock_heartbeat()
            last_heartbeat_write = now_epoch

        if not is_active_market_session():
            log("Outside active market session. Exiting runner cleanly.")
            break

        now = now_ist()
        target = next_cycle_time(now)
        if target > now:
            log(f"Waiting for next 5-minute boundary: {target.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            sleep_until(target)

        update_lock_heartbeat()
        last_heartbeat_write = time.time()

        if not is_active_market_session():
            log("No longer inside active market session after wait. Exiting runner cleanly.")
            break

        try:
            run_full_cycle()
        except Exception as e:
            log(f"CYCLE ERROR (continuing to next cycle): {e}")

        update_lock_heartbeat()
        last_heartbeat_write = time.time()

    release_lock()


if __name__ == "__main__":
    main()