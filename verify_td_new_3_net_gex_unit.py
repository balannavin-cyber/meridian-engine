"""
verify_td_new_3_net_gex_unit.py — Read-only verification of the TD-NEW-3 patch.

Imports the PATCHED compute_gamma_metrics_local module directly and runs
compute_net_gex against real option_chain_snapshots rows for one healthy
cycle. Compares the patched output against the live gamma_metrics.net_gex
for the same ts.

Expected: patched_net_gex == live_net_gex / 1e7 (within rounding)

Live impact: ZERO. Read-only queries. No writes.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client


PATCHED_PATH = Path(r"C:\GammaEnginePython\compute_gamma_metrics_local_PATCHED.py")

if not PATCHED_PATH.exists():
    print(f"ERROR: patched file not found: {PATCHED_PATH}", file=sys.stderr)
    print("Run fix_td_new_3_net_gex_unit.py first.", file=sys.stderr)
    sys.exit(2)

# Register module in sys.modules BEFORE exec_module (dataclass requirement)
_MODULE_NAME = "compute_gamma_patched_td3"
spec = importlib.util.spec_from_file_location(_MODULE_NAME, PATCHED_PATH)
patched = importlib.util.module_from_spec(spec)
sys.modules[_MODULE_NAME] = patched
spec.loader.exec_module(patched)

compute_net_gex = patched.compute_net_gex


def _connect() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing in .env")
    return create_client(url, key)


SB: Client = _connect()


def fetch_cycle_and_live_net_gex(
    target_ts_iso: str, symbol: str = "NIFTY"
) -> tuple[list[dict], float, str, float | None]:
    head = (
        SB.table("option_chain_snapshots")
          .select("ts, spot")
          .eq("symbol", symbol)
          .gte("ts", target_ts_iso)
          .order("ts")
          .limit(1)
          .execute()
    )
    if not head.data:
        raise RuntimeError(f"No option_chain_snapshots data at or after {target_ts_iso}")
    actual_ts = head.data[0]["ts"]
    spot = float(head.data[0]["spot"])

    chain = (
        SB.table("option_chain_snapshots")
          .select("strike, option_type, gamma, oi, ts, spot")
          .eq("symbol", symbol)
          .eq("ts", actual_ts)
          .limit(1000)
          .execute()
    )
    chain_rows = chain.data

    gm = (
        SB.table("gamma_metrics")
          .select("ts, net_gex")
          .eq("symbol", symbol)
          .gte("ts", actual_ts)
          .order("ts")
          .limit(1)
          .execute()
    )
    live_ng = None
    if gm.data and gm.data[0].get("net_gex") is not None:
        live_ng = float(gm.data[0]["net_gex"])

    return chain_rows, spot, actual_ts, live_ng


def verify_cycle(label: str, target_ts_iso: str) -> None:
    print()
    print(f"=== {label} ===")
    print(f"Target ts (UTC): {target_ts_iso}")

    rows, spot, actual_ts, live_ng = fetch_cycle_and_live_net_gex(target_ts_iso)
    print(f"Actual cycle ts: {actual_ts}")
    print(f"Chain rows:      {len(rows)}")
    print(f"Spot:            {spot:,.2f}")
    if live_ng is not None:
        print(f"LIVE net_gex:    {live_ng:,.0f}  (raw rupees, pre-TD-NEW-3)")
    else:
        print("LIVE net_gex:    None")

    patched_ng = compute_net_gex(rows, spot)
    print(f"PATCHED net_gex: {patched_ng:,.2f}  (Crore, post-TD-NEW-3)")

    if live_ng is not None and live_ng != 0:
        ratio = abs(live_ng / patched_ng) if patched_ng != 0 else float("inf")
        print(f"Ratio live/patched: {ratio:,.0f}  (expect ~1e7 = 10,000,000)")
        within_tolerance = 9.5e6 < ratio < 1.05e7
        print(f"Within 5% of 1e7:  {'YES' if within_tolerance else 'NO'}")

    if patched_ng is not None:
        # Operational sanity: post-Crore-conversion, should be in
        # thousands to tens of thousands range (typical NIFTY net GEX)
        abs_ng = abs(patched_ng)
        op_sane = 100 < abs_ng < 1_000_000
        print(f"Operationally sane (100 < |net_gex| < 1M Cr): {'YES' if op_sane else 'NO'}")


def main() -> int:
    print("TD-NEW-3 verification — patched net_gex unit (Crore)")
    print("=" * 64)

    try:
        # Use a known clean post-TD-NEW-2-fix cycle. Today's data is fine
        # but markets just closed — use yesterday's cycle that we know was healthy
        # (after TD-NEW-2 patch landed but before TD-NEW-3 patch lands)
        verify_cycle(
            "TODAY 09:30 IST",
            "2026-05-11T04:00:00+00:00",
        )
    except Exception as exc:
        print(f"\nERROR during verification: {exc}", file=sys.stderr)
        return 3

    print()
    print("=" * 64)
    print("Decision:")
    print("  Ratio ~1e7 AND operationally sane -> proceed to rename PATCHED -> canonical")
    print("  Ratio != 1e7                       -> the /1e7 divisor didn't take effect")
    print("  Not operationally sane             -> investigate threshold tuning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
