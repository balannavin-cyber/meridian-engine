from pathlib import Path
import re
import sys

path = Path(r"C:\GammaEnginePython\build_momentum_features_local.py")
text = path.read_text(encoding="utf-8")

if "from postgrest.exceptions import APIError" not in text:
    if "from supabase import Client, create_client" in text:
        text = text.replace(
            "from supabase import Client, create_client",
            "from supabase import Client, create_client\nfrom postgrest.exceptions import APIError"
        )
    elif "from supabase import create_client" in text:
        text = text.replace(
            "from supabase import create_client",
            "from supabase import create_client\nfrom postgrest.exceptions import APIError"
        )
    else:
        print("ERROR: could not find supabase import line")
        sys.exit(1)

pattern = r"def insert_momentum\(row: dict\[str, Any\]\) -> None:.*?def main\(\) -> None:"
if not re.search(pattern, text, flags=re.DOTALL):
    pattern = r"def insert_momentum\(row\):.*?def main\(\):"

replacement = """def insert_momentum(row: dict[str, Any]) -> None:
    try:
        (
            SUPABASE
            .table("momentum_snapshots")
            .upsert(row, on_conflict="symbol,ts")
            .execute()
        )
        print("Momentum snapshot upsert complete.")
        print(f"symbol={row.get('symbol')}")
        print(f"ts={row.get('ts')}")
        print(f"ret_5m={row.get('ret_5m')}")
        print(f"ret_15m={row.get('ret_15m')}")
        print(f"ret_30m={row.get('ret_30m')}")
        print(f"ret_60m={row.get('ret_60m')}")
        print(f"ret_session={row.get('ret_session')}")
        print(f"atm_straddle_change={row.get('atm_straddle_change')}")
        print(f"price_vs_vwap_pct={row.get('price_vs_vwap_pct')}")
        print(f"vwap_slope={row.get('vwap_slope')}")
        print(f"momentum_regime={row.get('momentum_regime')}")
    except APIError as e:
        msg = str(e)
        if "uq_momentum_snapshots_symbol_ts" in msg or "duplicate key value violates unique constraint" in msg:
            print("Momentum snapshot already exists for (symbol, ts). Treating as success.")
            print(f"symbol={row.get('symbol')}")
            print(f"ts={row.get('ts')}")
            return
        raise

def main() -> None:"""

new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)

if count != 1:
    print(f"ERROR: expected to replace exactly 1 insert_momentum block, got {count}")
    sys.exit(1)

path.write_text(new_text, encoding="utf-8")
print("Patched build_momentum_features_local.py successfully.")
