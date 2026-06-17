from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import tempfile
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


# ============================================================================
# MERDIAN - Reload dhan_scripmaster from Dhan detailed CSV   (AWS port)
# ----------------------------------------------------------------------------
# Port of reload_dhan_scripmaster_from_csv.py for AWS EC2 (eu-north-1).
#
# Changes vs the Local/Windows original:
#   1. De-Windowed source resolution. Source priority:
#        --csv PATH  >  env DHAN_SCRIPMASTER_CSV (if file exists)  >  fetch URL
#      Fetch URL: --url  >  env DHAN_SCRIPMASTER_URL  >  DEFAULT_SCRIPMASTER_URL
#   2. Non-interactive. The blocking input("YES") prompt is gone.
#      DRY-RUN BY DEFAULT (reads + validates + reports, writes NOTHING).
#      Pass --apply to actually reload.  (Patch-canon-v3 dry-run discipline.)
#   3. ATOMIC reload. The original DELETE-then-INSERT left the live table EMPTY
#      if any insert chunk failed (= total contract-resolution outage). This
#      version bulk-loads a staging table, validates it, then calls a single
#      transactional RPC swap_dhan_scripmaster() so the live table is never
#      empty mid-reload (insert failure rolls the delete back).
#   4. Contract-resolution gate. Validates that BOTH NIFTY and SENSEX have
#      FUTIDX (and OPTIDX) contracts whose latest expiry is >= the current
#      month. Dry-run reports it; --apply ABORTS before any write if it fails,
#      unless --force is given. This is the "verify June contracts resolve"
#      check from the S56 plan, enforced in code.
#
# Prereq (one-time DDL, see swap_dhan_scripmaster() + dhan_scripmaster_staging).
# ============================================================================


if load_dotenv is not None:
    # absolute-path load so cron (no inherited shell env) works regardless of cwd
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
    else:
        load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

# NOTE: confirm this is the URL Local actually downloads the detailed master
# from. If Local pulls it differently, set env DHAN_SCRIPMASTER_URL or pass
# --url. Left as the documented public Dhan detailed-master endpoint.
DEFAULT_SCRIPMASTER_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"

LIVE_TABLE = "dhan_scripmaster"
STAGING_TABLE = "dhan_scripmaster_staging"
SWAP_RPC = "swap_dhan_scripmaster"

REQUEST_TIMEOUT_SECONDS = 120
FETCH_TIMEOUT_SECONDS = 180
CHUNK_SIZE = 1000


class ConfigError(RuntimeError):
    pass


class SupabaseError(RuntimeError):
    pass


class ValidationError(RuntimeError):
    pass


TARGET_TABLE_COLUMNS = {
    "SECURITY_ID", "EXCH_ID", "SEGMENT", "INSTRUMENT", "EXPIRY_CODE",
    "DISPLAY_NAME", "LOT_UNITS", "TRADING_SYMBOL", "SM_EXPIRY_DATE",
    "STRIKE_PRICE", "OPTION_TYPE", "TICK_SIZE", "EXPIRY_FLAG",
    "INSTRUMENT_TYPE", "SERIES", "TRADING_STATUS", "PRECISION", "MULTIPLIER",
    "ISIN", "FREEZE_QTY", "LOT_SIZE", "SECURITY_DESC", "EXCH_INSTRUMENT_ID",
    "UNDERLYING_SYMBOL", "SHORT_NAME", "UPPER_PRICE_BAND", "LOWER_PRICE_BAND",
    "FACE_VALUE", "SCRIP_CODE", "CA_LEVEL1", "CA_LEVEL2", "CA_LEVEL3",
    "MSI_FLAG", "MSI_YN", "PP_YN", "SETTLEMENT_TYPE", "BD_YN",
    "EXPIRY_WEEK_MONTH", "SCRIPSETT", "NO_DECIMAL_LOC", "TRADING_UNIT",
}


# ---------------------------------------------------------------------------
# env / http helpers
# ---------------------------------------------------------------------------

def require_env(name: str, value: str) -> str:
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def print_header() -> None:
    print("=" * 72)
    print("MERDIAN - Reload dhan_scripmaster from Dhan detailed CSV (AWS)")
    print("=" * 72)


def get_headers(prefer: str = "return=minimal") -> Dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": prefer,
    }


def chunked(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


# ---------------------------------------------------------------------------
# source resolution: local CSV preferred, else fetch
# ---------------------------------------------------------------------------

def resolve_source(args: argparse.Namespace) -> Tuple[str, bool]:
    """Return (csv_path, is_temp). is_temp True if we fetched to a temp file."""
    local = args.csv or os.getenv("DHAN_SCRIPMASTER_CSV", "").strip()
    if local:
        if os.path.exists(local):
            print(f"[STEP] Using local CSV: {local}")
            return local, False
        raise FileNotFoundError(f"Specified CSV not found: {local}")

    url = args.url or os.getenv("DHAN_SCRIPMASTER_URL", "").strip() or DEFAULT_SCRIPMASTER_URL
    print(f"[STEP] Fetching scrip master: {url}")
    resp = requests.get(url, timeout=FETCH_TIMEOUT_SECONDS)
    if resp.status_code >= 300:
        raise SupabaseError(f"Fetch failed | status={resp.status_code} | url={url}")
    fd, tmp_path = tempfile.mkstemp(prefix="dhan_scripmaster_", suffix=".csv")
    with os.fdopen(fd, "wb") as f:
        f.write(resp.content)
    print(f"[OK] Fetched {len(resp.content)} bytes -> {tmp_path}")
    return tmp_path, True


# ---------------------------------------------------------------------------
# CSV read (unchanged parsing logic)
# ---------------------------------------------------------------------------

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
                if not key or key not in TARGET_TABLE_COLUMNS:
                    continue
                db_row[key] = normalize_value(raw_value)
            if db_row:
                rows.append(db_row)

    if not rows:
        raise RuntimeError("CSV read successfully but contained zero usable data rows.")

    return rows


# ---------------------------------------------------------------------------
# validation: contract-resolution gate (the "June contracts resolve" check)
# ---------------------------------------------------------------------------

def _latest_expiry(rows: List[Dict[str, Any]], underlying: str, instrument: str
                   ) -> Tuple[int, Optional[str]]:
    count = 0
    latest: Optional[str] = None
    for row in rows:
        if row.get("UNDERLYING_SYMBOL") == underlying and row.get("INSTRUMENT") == instrument:
            count += 1
            exp = row.get("SM_EXPIRY_DATE")
            if exp and (latest is None or exp > latest):
                latest = exp
    return count, latest


def summarize_and_validate(rows: List[Dict[str, Any]], force: bool) -> None:
    print(f"[INFO] Usable CSV rows loaded: {len(rows)}")

    current_month = date.today().strftime("%Y-%m")  # SM_EXPIRY_DATE is ISO 'YYYY-MM-DD...'
    failures: List[str] = []

    for underlying in ("NIFTY", "SENSEX"):
        for instrument in ("FUTIDX", "OPTIDX"):
            n, latest = _latest_expiry(rows, underlying, instrument)
            ok = bool(latest) and latest[:7] >= current_month
            tag = "OK " if ok else "STALE"
            print(f"[CHECK] {tag} {underlying:6s} {instrument:6s} rows={n:<6d} latest_expiry={latest}")
            # gate only on FUTIDX (the futures contract-resolution purpose);
            # OPTIDX is reported for context.
            if instrument == "FUTIDX" and not ok:
                failures.append(f"{underlying} FUTIDX latest_expiry={latest} < {current_month}")

    if failures:
        msg = "Contract-resolution gate FAILED: " + "; ".join(failures)
        if force:
            print(f"[WARN] {msg} -- proceeding due to --force")
        else:
            raise ValidationError(msg + "  (CSV is stale; refusing to load. Override with --force.)")


# ---------------------------------------------------------------------------
# staging load + atomic swap
# ---------------------------------------------------------------------------

def clear_staging() -> None:
    print(f"[STEP] Clearing {STAGING_TABLE} ...")
    url = f"{SUPABASE_URL}/rest/v1/{STAGING_TABLE}"
    resp = requests.delete(
        url, headers=get_headers(),
        params={"SECURITY_ID": "not.is.null"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if resp.status_code >= 300:
        raise SupabaseError(f"Staging clear failed | status={resp.status_code} | body={resp.text}")
    print("[OK] Staging cleared.")


def load_staging(rows: List[Dict[str, Any]]) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{STAGING_TABLE}"
    total = len(rows)
    inserted = 0
    chunk_no = 0
    total_chunks = math.ceil(total / CHUNK_SIZE)
    for batch in chunked(rows, CHUNK_SIZE):
        chunk_no += 1
        resp = requests.post(url, headers=get_headers(), json=batch, timeout=REQUEST_TIMEOUT_SECONDS)
        if resp.status_code >= 300:
            raise SupabaseError(
                f"Staging insert failed | chunk={chunk_no}/{total_chunks} | "
                f"status={resp.status_code} | body={resp.text}"
            )
        inserted += len(batch)
        print(f"[STAGE] chunk={chunk_no}/{total_chunks} | rows={inserted}/{total}")


def count_table(table: str) -> int:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    resp = requests.get(
        url, headers=get_headers(prefer="count=exact"),
        params={"select": "SECURITY_ID", "limit": "1"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if resp.status_code >= 300:
        raise SupabaseError(f"Count failed on {table} | status={resp.status_code} | body={resp.text}")
    # PostgREST returns total in Content-Range: 0-0/<count>
    cr = resp.headers.get("Content-Range", "")
    if "/" in cr:
        try:
            return int(cr.split("/")[-1])
        except ValueError:
            pass
    raise SupabaseError(f"Could not parse count for {table} from Content-Range={cr!r}")


def atomic_swap() -> int:
    print(f"[STEP] Calling RPC {SWAP_RPC}() (transactional delete+reload) ...")
    url = f"{SUPABASE_URL}/rest/v1/rpc/{SWAP_RPC}"
    resp = requests.post(url, headers=get_headers(prefer="return=representation"),
                         json={}, timeout=REQUEST_TIMEOUT_SECONDS)
    if resp.status_code >= 300:
        raise SupabaseError(f"Swap RPC failed | status={resp.status_code} | body={resp.text}")
    try:
        n = int(resp.json())
    except (ValueError, TypeError):
        n = -1
    print(f"[OK] Swap complete. RPC reported rows inserted = {n}")
    return n


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reload public.dhan_scripmaster (AWS, atomic).")
    p.add_argument("--apply", action="store_true",
                   help="Actually reload. Default is dry-run (read + validate + report only).")
    p.add_argument("--force", action="store_true",
                   help="Proceed even if the contract-resolution gate fails (stale CSV).")
    p.add_argument("--csv", default=None, help="Local CSV path override (skips fetch).")
    p.add_argument("--url", default=None, help="Fetch URL override.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    print_header()

    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)

    csv_path, is_temp = resolve_source(args)
    try:
        rows = read_csv_rows(csv_path)
        summarize_and_validate(rows, force=args.force)

        if not args.apply:
            print("[DRY-RUN] Validation passed. No writes performed. Re-run with --apply to reload.")
            return 0

        clear_staging()
        load_staging(rows)

        staged = count_table(STAGING_TABLE)
        if staged != len(rows):
            raise ValidationError(
                f"Staging count {staged} != loaded rows {len(rows)} -- aborting before swap.")
        print(f"[OK] Staging verified: {staged} rows.")

        n = atomic_swap()
        live = count_table(LIVE_TABLE)
        print(f"[VERIFY] live {LIVE_TABLE} now holds {live} rows.")
        if live != len(rows):
            print(f"[WARN] live count {live} != loaded {len(rows)} -- inspect manually.")
        print("[DONE] public.dhan_scripmaster reloaded atomically.")
        return 0
    finally:
        if is_temp and os.path.exists(csv_path):
            os.remove(csv_path)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise
