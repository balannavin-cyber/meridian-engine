from __future__ import annotations

from pprint import pprint

from core.config import get_settings
from core.supabase_client import SupabaseClient
from core.dhan_client import DhanClient


def main() -> None:
    settings = get_settings()

    print("=" * 72)
    print("Gamma Engine - Test Core Layer")
    print("=" * 72)
    print(f"Base dir: {settings.base_dir}")
    print(f"Data dir: {settings.data_dir}")
    print(f"Logs dir: {settings.logs_dir}")
    print(f"Supabase URL: {settings.supabase_url}")
    print(f"Timeout seconds: {settings.timeout_seconds}")
    print("-" * 72)

    sb = SupabaseClient()
    rows = sb.select(
        table="dhan_scrip_map",
        select_expr="ticker,dhan_security_id,exchange",
        limit=3,
        order="ticker.asc",
    )

    print("Supabase test OK. Sample rows:")
    pprint(rows)
    print("-" * 72)

    dhan = DhanClient()
    expiry_data = dhan.get_expiry_list(
        underlying_scrip=13,
        underlying_seg="IDX_I",
    )

    print("Dhan expiry-list test OK. Response:")
    pprint(expiry_data)
    print("-" * 72)
    print("CORE LAYER TEST PASSED")


if __name__ == "__main__":
    main()