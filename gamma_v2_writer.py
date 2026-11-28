"""gamma_v2_writer.py -- ADR-033 writer hook for V2 exposure (rule v1.2).

Called by compute_gamma_metrics_local.py AFTER the V1 rows (gamma_metrics and
gex_strike_snapshots) have been written. It never raises to its caller: every failure is
printed to stderr and returned as a status string, so a V2 problem can never stop or fail
the V1 run. The live p3b2 presence check (V0) is what reports a run with V1 rows and no V2 rows.

OFF by default. It runs only when the environment variable MERDIAN_GAMMA_V2 is "1", so the
code can be deployed before the tables exist. Skipped under --shadow (no shadow V2 tables).

Writes ONLY public.gex_strike_v2 and public.gex_run_v2. Reads nothing from the database.

The hook calls write_v2_bounded, which runs write_v2 in a daemon thread and waits at most
MERDIAN_GAMMA_V2_TIMEOUT_S seconds (default 10). A V2 write that hangs therefore costs the V1
run at most that long, and nothing raised inside the thread (BaseException included) reaches
the caller. A write that times out may leave strike rows with no run row: p3b2 V0 reports that
run and the stored-row backfill repairs it.
"""
from __future__ import annotations

import os
import sys
import threading
from typing import Any

from merdian_compute import gamma_v2

STRIKE_TABLE = "gex_strike_v2"
RUN_TABLE = "gex_run_v2"
CHUNK = 500
DEFAULT_TIMEOUT_S = 10.0


def enabled() -> bool:
    return os.getenv("MERDIAN_GAMMA_V2", "").strip() == "1"


def v2_payloads(option_rows_raw: list[dict[str, Any]], *, run_id: str, symbol: str, ts: str,
                expiry_date: str, dte: int | None, spot: Any,
                rule_version: str = gamma_v2.RULE_VERSION) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Pure. Chain rows -> (gex_strike_v2 rows, gex_run_v2 row). Raises gamma_v2.V2InputError."""
    strike_rows = gamma_v2.build_v2_strike_rows(option_rows_raw, spot)
    summary = gamma_v2.summarise_v2_run(strike_rows)
    ident = {"run_id": run_id, "symbol": symbol, "ts": ts, "expiry_date": expiry_date, "dte": dte}
    out = [{**ident, "spot": spot, **r, "rule_version": rule_version} for r in strike_rows]
    run_row = {**ident, "spot": spot, **summary,
               "n_dup_legs": gamma_v2.count_duplicate_legs(option_rows_raw), "rule_version": rule_version}
    return out, run_row


def write_v2(client: Any, option_rows_raw: list[dict[str, Any]] | None, *, run_id: str, symbol: str, ts: str,
             expiry_date: str, dte: int | None, spot: Any, shadow: bool = False) -> str:
    """Returns one of: DISABLED, SKIPPED_SHADOW, NO_ROWS, INPUT_ERROR, WRITE_ERROR, OK n=<rows>."""
    try:
        if not enabled():
            return "DISABLED"
        if shadow:
            return "SKIPPED_SHADOW"
        if not option_rows_raw:
            print(f"[gamma_v2] run_id={run_id} no chain rows handed to the hook", file=sys.stderr)
            return "NO_ROWS"
        try:
            strike_rows, run_row = v2_payloads(option_rows_raw, run_id=run_id, symbol=symbol, ts=ts,
                                               expiry_date=expiry_date, dte=dte, spot=spot)
        except gamma_v2.V2InputError as e:
            print(f"[gamma_v2] run_id={run_id} symbol={symbol} INPUT_ERROR (no V2 output, by rule): {e}", file=sys.stderr)
            return "INPUT_ERROR"
        for i in range(0, len(strike_rows), CHUNK):
            client.table(STRIKE_TABLE).upsert(strike_rows[i:i + CHUNK], on_conflict="run_id,strike,expiry_date").execute()
        client.table(RUN_TABLE).upsert(run_row, on_conflict="run_id,symbol,expiry_date").execute()
        print(f"gex_strike_v2_rows_written={len(strike_rows)} rule_version={gamma_v2.RULE_VERSION}")
        return f"OK n={len(strike_rows)}"
    except Exception as e:  # noqa: BLE001 -- the hook must never break the V1 run
        print(f"[gamma_v2] run_id={run_id} symbol={symbol} WRITE_ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return "WRITE_ERROR"


def timeout_s() -> float:
    """Seconds the hook may wait for the V2 write. Unset, unparsable or non-positive -> the default."""
    try:
        v = float(os.getenv("MERDIAN_GAMMA_V2_TIMEOUT_S", "").strip())
    except ValueError:
        return DEFAULT_TIMEOUT_S
    return v if v > 0 else DEFAULT_TIMEOUT_S


def write_v2_bounded(client: Any, option_rows_raw: list[dict[str, Any]] | None, *, shadow: bool = False, **ident: Any) -> str:
    """write_v2 with a time bound. Returns write_v2's status, or TIMEOUT after <s>s, or THREAD_ERROR."""
    if not enabled():
        return "DISABLED"
    if shadow:
        return "SKIPPED_SHADOW"
    box: dict[str, str] = {}

    def _work() -> None:
        try:
            box["status"] = write_v2(client, option_rows_raw, shadow=shadow, **ident)
        except BaseException as e:  # noqa: BLE001 -- nothing from V2 may reach the V1 run
            box["status"] = f"THREAD_ERROR {type(e).__name__}"

    limit = timeout_s()
    t = threading.Thread(target=_work, name="gamma_v2_write", daemon=True)
    t.start()
    t.join(limit)
    if t.is_alive():
        print(f"[gamma_v2] run_id={ident.get('run_id')} symbol={ident.get('symbol')} TIMEOUT after {limit:g}s "
              f"(the write is abandoned; p3b2 V0 will report the run if it is incomplete)", file=sys.stderr)
        return f"TIMEOUT after {limit:g}s"
    return box.get("status", "THREAD_ERROR no status")
