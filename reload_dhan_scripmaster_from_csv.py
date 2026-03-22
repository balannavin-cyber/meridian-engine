from __future__ import annotations

import csv
import math
import os
import sys
from typing import Any, Dict, Iterable, List

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


# ============================================================================
# MERDIAN - Reload dhan_scripmaster from Dhan detailed CSV
# ----------------------------------------------------------------------------
# Purpose:
#   Refresh public.dhan_scripmaster with the latest Dhan instrument master.
#
# What this script does:
#   1. Reads local CSV downloaded from Dhan:
#        C:\gammaenginepython\api-scrip-master-detailed.csv
#   2. Deletes all existing rows from public.dhan_scripmaster
#   3. Inserts fresh rows in chunks through Supabase REST
#
# IMPORTANT:
#   - This script FULL-RELOADS the table.
#   - It assumes the CSV already uses direct column names matching the table.
#   - It drops blank headers and unknown columns automatically.
# ============================================================================


if load_dotenv is not None:
    load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

CSV_PATH = r"C:\gammaenginepython\api-scrip-master-detailed.csv"

REQUEST_TIMEOUT_SECONDS = 120
CHUNK_SIZE = 1000


class ConfigError(RuntimeError):
    pass


class SupabaseError(RuntimeError):
    pass


TARGET_TABLE_COLUMNS = {
    "SECURITY_ID",
    "EXCH_ID",
    "SEGMENT",
    "INSTRUMENT",
    "EXPIRY_CODE",
    "DISPLAY_NAME",
    "LOT_UNITS",
    "TRADING_SYMBOL",
    "SM_EXPIRY_DATE",
    "STRIKE_PRICE",
    "OPTION_TYPE",
    "TICK_SIZE",
    "EXPIRY_FLAG",
    "INSTRUMENT_TYPE",
    "SERIES",
    "TRADING_STATUS",
    "PRECISION",
    "MULTIPLIER",
    "ISIN",
    "FREEZE_QTY",
    "LOT_SIZE",
    "SECURITY_DESC",
    "EXCH_INSTRUMENT_ID",
    "UNDERLYING_SYMBOL",
    "SHORT_NAME",
    "UPPER_PRICE_BAND",
    "LOWER_PRICE_BAND",
    "FACE_VALUE",
    "SCRIP_CODE",
    "CA_LEVEL1",
    "CA_LEVEL2",
    "CA_LEVEL3",
    "MSI_FLAG",
    "MSI_YN",
    "PP_YN",
    "SETTLEMENT_TYPE",
    "BD_YN",
    "EXPIRY_WEEK_MONTH",
    "SCRIPSETT",
    "NO_DECIMAL_LOC",
    "TRADING_UNIT",
}


def require_env(name: str, value: str) -> str:
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def print_header() -> None:
    print("=" * 72)
    print("MERDIAN - Reload dhan_scripmaster from Dhan detailed CSV")
    print("=" * 72)


def get_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": "return=minimal",
    }


def chunked(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
        if value.lower() == "nan":
            return None
    return value


def clean_header(header: Any) -> str:
    if header is None:
        return ""
    return str(header).strip().replace("\ufeff", "")


def read_csv_rows(csv_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows: List[Dict[str, Any]] = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise RuntimeError("CSV has no header row.")

        cleaned_headers = [clean_header(h) for h in reader.fieldnames]
        blank_headers = [h for h in cleaned_headers if h == ""]
        usable_headers = [h for h in cleaned_headers if h in TARGET_TABLE_COLUMNS]
        unknown_headers = [h for h in cleaned_headers if h and h not in TARGET_TABLE_COLUMNS]

        print(f"[INFO] CSV headers found: {len(cleaned_headers)}")
        print(f"[INFO] Blank headers dropped: {len(blank_headers)}")
        print(f"[INFO] Usable headers: {len(usable_headers)}")
        print(f"[INFO] Unknown headers dropped: {len(unknown_headers)}")

        if usable_headers:
            print("[INFO] Usable header sample:")
            for header in usable_headers[:10]:
                print(f"  - {header}")

        if unknown_headers:
            print("[INFO] Unknown header sample:")
            for header in unknown_headers[:10]:
                print(f"  - {header}")

        for raw_row in reader:
            db_row: Dict[str, Any] = {}
            for raw_key, raw_value in raw_row.items():
                key = clean_header(raw_key)
                if not key:
                    continue
                if key not in TARGET_TABLE_COLUMNS:
                    continue
                db_row[key] = normalize_value(raw_value)

            if db_row:
                rows.append(db_row)

    if not rows:
        raise RuntimeError("CSV read successfully but contained zero usable data rows.")

    return rows


def delete_existing_rows() -> None:
    print("[STEP] Deleting existing rows from public.dhan_scripmaster ...")
    url = f"{SUPABASE_URL}/rest/v1/dhan_scripmaster"
    response = requests.delete(
        url,
        headers=get_headers(),
        params={"SECURITY_ID": "not.is.null"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise SupabaseError(
            f"Delete failed | status={response.status_code} | body={response.text}"
        )
    print("[OK] Existing rows deleted.")


def insert_rows(rows: List[Dict[str, Any]]) -> None:
    url = f"{SUPABASE_URL}/rest/v1/dhan_scripmaster"

    total = len(rows)
    inserted = 0
    chunk_no = 0
    total_chunks = math.ceil(total / CHUNK_SIZE)

    for batch in chunked(rows, CHUNK_SIZE):
        chunk_no += 1
        response = requests.post(
            url,
            headers=get_headers(),
            json=batch,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code >= 300:
            raise SupabaseError(
                f"Insert failed | chunk={chunk_no}/{total_chunks} | "
                f"status={response.status_code} | body={response.text}"
            )
        inserted += len(batch)
        print(f"[INSERT] chunk={chunk_no}/{total_chunks} | rows={inserted}/{total}")


def summarize_rows(rows: List[Dict[str, Any]]) -> None:
    print(f"[INFO] Usable CSV rows loaded: {len(rows)}")

    nifty_opt = 0
    sensex_opt = 0
    max_nifty_expiry = None
    max_sensex_expiry = None

    for row in rows:
        underlying = row.get("UNDERLYING_SYMBOL")
        instrument = row.get("INSTRUMENT")
        expiry = row.get("SM_EXPIRY_DATE")

        if underlying == "NIFTY" and instrument == "OPTIDX":
            nifty_opt += 1
            if expiry and (max_nifty_expiry is None or expiry > max_nifty_expiry):
                max_nifty_expiry = expiry

        if underlying == "SENSEX" and instrument == "OPTIDX":
            sensex_opt += 1
            if expiry and (max_sensex_expiry is None or expiry > max_sensex_expiry):
                max_sensex_expiry = expiry

    print(
        f"[CHECK] NIFTY OPTIDX rows={nifty_opt} | latest expiry={max_nifty_expiry}"
    )
    print(
        f"[CHECK] SENSEX OPTIDX rows={sensex_opt} | latest expiry={max_sensex_expiry}"
    )


def main() -> int:
    print_header()

    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)

    print(f"[STEP] Reading CSV: {CSV_PATH}")
    rows = read_csv_rows(CSV_PATH)
    summarize_rows(rows)

    confirm = input(
        "Type YES to DELETE and RELOAD public.dhan_scripmaster: "
    ).strip()

    if confirm != "YES":
        print("[ABORTED] Confirmation not received. No changes made.")
        return 1

    delete_existing_rows()
    insert_rows(rows)

    print("[DONE] public.dhan_scripmaster fully reloaded.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise