"""gamma_v2_writer.py -- ADR-033 writer hook for V2 exposure (rule v1.2).

Called by compute_gamma_metrics_local.py AFTER the V1 rows (gamma_metrics and
gex_strike_snapshots) have been written. It never raises to its caller: every failure is
printed to stderr and returned as a status string, so a V2 problem can never stop or fail
the V1 run. The live p3b2 presence check (V0) is what reports a run with V1 rows and no V2 rows.

OFF by default. It runs only when the environment variable MERDIAN_GAMMA_V2 is "1", so the
code can be deployed before the tables exist. Skipped under --shadow (no shadow V2 tables).

Writes ONLY public.gex_strike_v2 and public.gex_run_v2. Reads nothing from the database.
"""
from __future__ import annotations

import os
import sys
from typing import Any

from merdian_compute import gamma_v2

STRIKE_TABLE = "gex_strike_v2"
RUN_TABLE = "gex_run_v2"
CHUNK = 500


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
