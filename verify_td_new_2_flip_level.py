"""
verify_td_new_2_flip_level.py — Read-only verification of the TD-NEW-2 patch.

Imports the PATCHED module directly (no rename of canonical needed) and runs
its pure functions against real option_chain_snapshots rows for two reference
cycles: one healthy (2026-05-07) and one broken (2026-05-08). Compares the
patched flip_level output against the live gamma_metrics row for that same ts.

Live impact: ZERO. Two SELECT queries per cycle. No writes.

Acceptance:
  HEALTHY cycle  -> patched flip_level should match live flip_level (no regression)
  BROKEN cycle   -> patched flip_level should land near spot (24,000-25,500 range),
                    NOT stuck at ~21,250 like the live value
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client


# ---------------------------------------------------------------------------
# Load patched module by direct file path (no rename of canonical required)
# ---------------------------------------------------------------------------

PATCHED_PATH = Path(r"C:\GammaEnginePython\compute_gamma_metrics_local_PATCHED.py")

if not PATCHED_PATH.exists():
    print(f"ERROR: patched file not found: {PATCHED_PATH}", file=sys.stderr)
    print("Run fix_td_new_2_flip_level.py first.", file=sys.stderr)
    sys.exit(2)

# IMPORTANT: register the module in sys.modules BEFORE exec_module, otherwise
# @dataclass decorators inside the loaded module fail with NoneType.__dict__.
# This is a documented importlib + dataclass interaction.
_MODULE_NAME = "compute_gamma_patched"
spec = importlib.util.spec_from_file_location(_MODULE_NAME, PATCHED_PATH)
patched = importlib.util.module_from_spec(spec)
sys.modules[_MODULE_NAME] = patched  # <-- required for @dataclass classes inside
spec.loader.exec_module(patched)

signed_gamma_exposure = patched.signed_gamma_exposure
build_strike_exposure_map = patched.build_strike_exposure_map
compute_flip_level = patched.compute_flip_level
compute_net_gex = patched.compute_net_gex


# ---------------------------------------------------------------------------
# Supabase connect (mirrors replay/replay_compute_gamma_metrics.py pattern)
# ---------------------------------------------------------------------------

def _connect() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing in .env")
    return create_client(url, key)


SB: Client = _connect()


# ---------------------------------------------------------------------------
# Data fetch — find one full cycle near a target timestamp
# ---------------------------------------------------------------------------

def fetch_cycle_and_live_flip(
    target_ts_iso: str, symbol: str = "NIFTY"
) -> tuple[list[dict], float, str, float | None]:
    """
    Find the option_chain_snapshots cycle nearest target_ts_iso (>=), pull all
    rows for that exact ts, and pull the live gamma_metrics row for that ts.

    Returns (chain_rows, spot, actual_ts, live_flip_level).
    """
    # 1. Find the actual ts of the nearest cycle
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

    # 2. Pull all chain rows for that exact ts (~482 expected; well under 1000-row cap)
    chain = (
        SB.table("option_chain_snapshots")
          .select("strike, option_type, gamma, oi, ts, spot, expiry_date")
          .eq("symbol", symbol)
          .eq("ts", actual_ts)
          .limit(1000)
          .execute()
    )
    chain_rows = chain.data

    # 3. Pull the live gamma_metrics row for that ts (or nearest)
    gm = (
        SB.table("gamma_metrics")
          .select("ts, spot, net_gex, flip_level, regime")
          .eq("symbol", symbol)
          .gte("ts", actual_ts)
          .order("ts")
          .limit(1)
          .execute()
    )
    live_flip = None
    if gm.data and gm.data[0].get("flip_level") is not None:
        live_flip = float(gm.data[0]["flip_level"])

    return chain_rows, spot, actual_ts, live_flip


# ---------------------------------------------------------------------------
# Verification per cycle
# ---------------------------------------------------------------------------

def verify_cycle(label: str, target_ts_iso: str, expected: str) -> None:
    print()
    print(f"=== {label} ===")
    print(f"Target ts (UTC): {target_ts_iso}")

    rows, spot, actual_ts, live_flip = fetch_cycle_and_live_flip(target_ts_iso)
    print(f"Actual cycle ts: {actual_ts}")
    print(f"Chain rows:      {len(rows)}")
    print(f"Spot:            {spot:,.2f}")
    if live_flip is not None:
        print(f"LIVE flip_level: {live_flip:,.2f}")
    else:
        print("LIVE flip_level: None")

    # Compute via PATCHED module (Part A filters bad rows in signed_gamma_exposure;
    # Part B walks-from-ATM in compute_flip_level)
    strike_map = build_strike_exposure_map(rows, spot)
    net_gex = compute_net_gex(rows, spot)
    patched_flip = compute_flip_level(strike_map, spot)

    print(f"PATCHED net_gex:    {net_gex:,.0f}")
    if patched_flip is not None:
        dist_pts = patched_flip - spot
        dist_pct = abs(dist_pts) / spot * 100
        print(f"PATCHED flip_level: {patched_flip:,.2f} ({dist_pts:+,.0f} pts, {dist_pct:.2f}%)")
    else:
        print("PATCHED flip_level: None")

    print(f"Expected:        {expected}")

    # Compare
    if live_flip is not None and patched_flip is not None:
        delta = patched_flip - live_flip
        delta_pct = abs(delta) / live_flip * 100
        print(f"Delta vs live:   {delta:+,.2f} pts ({delta_pct:.2f}%)")


# ---------------------------------------------------------------------------
# Main — run two reference verifications
# ---------------------------------------------------------------------------

def main() -> int:
    print("TD-NEW-2 verification — patched compute_flip_level vs live data")
    print("=" * 64)

    try:
        # HEALTHY: 2026-05-07 09:30 IST = 04:00 UTC. Pre-regression.
        # Live flip was ~24,800 range. Patched should match closely.
        verify_cycle(
            "HEALTHY CYCLE — 2026-05-07 ~09:30 IST",
            "2026-05-07T04:00:00+00:00",
            "PATCHED flip near LIVE flip (~24,800). NO regression.",
        )

        # BROKEN: 2026-05-08 09:30 IST = 04:00 UTC. Post-regression.
        # Live flip was stuck at ~21,250. Patched should resolve near spot.
        verify_cycle(
            "BROKEN CYCLE — 2026-05-08 ~09:30 IST",
            "2026-05-08T04:00:00+00:00",
            "PATCHED flip near spot (24,000-25,500), NOT 21,250.",
        )

    except Exception as exc:
        print(f"\nERROR during verification: {exc}", file=sys.stderr)
        return 3

    print()
    print("=" * 64)
    print("Verification complete. Decision:")
    print("  - If HEALTHY delta < 50 pts AND BROKEN flip near spot -> proceed to rename + backfill")
    print("  - If HEALTHY shows large delta -> Part B introduced regression, investigate")
    print("  - If BROKEN still stuck      -> Part A threshold may need adjustment, investigate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
