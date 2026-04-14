#!/usr/bin/env python3
"""
fix_order_placer_scrip.py
==========================
Fixes find_security() in merdian_order_placer.py.

Problems found from scrip master inspection:
  1. SEM_SEGMENT is 'D' not 'NSE_FNO'/'BSE_FNO'
  2. SM_SYMBOL_NAME is blank for options — must match via SEM_TRADING_SYMBOL prefix
  3. All rows loaded into memory — OOM on t3.micro (now t3.small but still wasteful)

Fix: stream CSV row by row, match on:
  - SEM_EXM_EXCH_ID: NSE (NIFTY) or BSE (SENSEX)
  - SEM_SEGMENT: D
  - SEM_INSTRUMENT_NAME: OPTIDX
  - SEM_TRADING_SYMBOL starts with: NIFTY- or SENSEX-
  - SEM_EXPIRY_DATE[:10] == expiry_date
  - int(float(SEM_STRIKE_PRICE)) == strike
  - SEM_OPTION_TYPE == CE/PE
"""
import shutil
from pathlib import Path

TARGET = Path("merdian_order_placer.py")
BACKUP = Path("merdian_order_placer.py.bak_scrip_fix")

OLD_EXCHANGE_SEGMENT = '''\
# Dhan exchange segment by symbol
EXCHANGE_SEGMENT = {
    "NIFTY":  "NSE_FNO",
    "SENSEX": "BSE_FNO",
}

# Dhan symbol name in scrip master
SCRIP_SYMBOL = {
    "NIFTY":  "NIFTY",
    "SENSEX": "SENSEX",
}'''

NEW_EXCHANGE_SEGMENT = '''\
# Dhan exchange ID and segment by symbol (from scrip master inspection)
# Segment is 'D' for derivatives. Exchange is NSE/BSE.
EXCHANGE_ID = {
    "NIFTY":  "NSE",
    "SENSEX": "BSE",
}

# Trading symbol prefix in SEM_TRADING_SYMBOL column
TRADING_SYMBOL_PREFIX = {
    "NIFTY":  "NIFTY-",
    "SENSEX": "SENSEX-",
}

# Keep for backward compat with place_order payload
EXCHANGE_SEGMENT = {
    "NIFTY":  "NSE_FNO",
    "SENSEX": "BSE_FNO",
}'''

OLD_LOAD_FN = '''\
def load_scrip_master(force: bool = False) -> list[dict]:
    """Download and cache Dhan scrip master. Returns list of rows."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    if not force and not _scrip_is_stale():
        log(f"Scrip master cache hit: {SCRIP_CACHE}")
        with SCRIP_CACHE.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    log("Downloading Dhan scrip master...")
    r = requests.get(DHAN_SCRIP_URL, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Scrip master download failed: {r.status_code}")

    SCRIP_CACHE.write_bytes(r.content)
    log(f"Scrip master cached: {SCRIP_CACHE} ({len(r.content):,} bytes)")

    content = r.content.decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(content)))'''

NEW_LOAD_FN = '''\
def load_scrip_master(force: bool = False) -> list[dict]:
    """Download and cache Dhan scrip master. Streams to disk — does NOT load into memory."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    if not force and not _scrip_is_stale():
        log(f"Scrip master cache hit: {SCRIP_CACHE}")
        return []  # streaming used in find_security — no need to return rows

    log("Downloading Dhan scrip master (streaming)...")
    r = requests.get(DHAN_SCRIP_URL, timeout=60, stream=True)
    if r.status_code != 200:
        raise RuntimeError(f"Scrip master download failed: {r.status_code}")

    size = 0
    with SCRIP_CACHE.open("wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
            size += len(chunk)

    log(f"Scrip master cached: {SCRIP_CACHE} ({size:,} bytes)")
    return []'''

OLD_FIND_FN = '''\
def find_security(
    symbol: str,
    strike: int,
    expiry_date: str,
    option_type: str,
) -> dict:
    """
    Find Dhan security_id and trading_symbol for an options contract.

    Args:
        symbol:      'NIFTY' or 'SENSEX'
        strike:      e.g. 23800
        expiry_date: 'YYYY-MM-DD'
        option_type: 'CE' or 'PE'

    Returns:
        {'security_id': '...', 'trading_symbol': '...', 'lot_size': int}

    Raises:
        RuntimeError if not found.
    """
    symbol      = symbol.upper()
    option_type = option_type.upper()
    segment     = EXCHANGE_SEGMENT[symbol]
    scrip_sym   = SCRIP_SYMBOL[symbol]

    rows = load_scrip_master()

    matches = []
    for row in rows:
        # Filter by segment, symbol name, instrument type, option type
        if row.get("SEM_SEGMENT", "").strip() != segment:
            continue
        if row.get("SM_SYMBOL_NAME", "").strip().upper() != scrip_sym:
            continue
        if row.get("SEM_INSTRUMENT_NAME", "").strip() != "OPTIDX":
            continue
        if row.get("SEM_OPTION_TYPE", "").strip().upper() != option_type:
            continue

        # Match expiry date (stored as YYYY-MM-DD in scrip master)
        row_expiry = row.get("SEM_EXPIRY_DATE", "").strip()[:10]
        if row_expiry != expiry_date:
            continue

        # Match strike (stored as float e.g. "23800.0")
        try:
            row_strike = int(float(row.get("SEM_STRIKE_PRICE", "0")))
        except (ValueError, TypeError):
            continue
        if row_strike != int(strike):
            continue

        matches.append(row)

    if not matches:
        raise RuntimeError(
            f"Security not found: {symbol} {strike} {option_type} expiry={expiry_date}. "
            f"Check scrip master or expiry date format."
        )

    row = matches[0]
    security_id    = row.get("SEM_SMST_SECURITY_ID", "").strip()
    trading_symbol = row.get("SEM_TRADING_SYMBOL", "").strip()

    try:
        lot_size = int(float(row.get("SEM_LOT_UNITS", LOT_SIZE.get(symbol, 75))))
    except (ValueError, TypeError):
        lot_size = LOT_SIZE.get(symbol, 75)

    log(f"Found: {trading_symbol} | security_id={security_id} | lot_size={lot_size}")
    return {
        "security_id":    security_id,
        "trading_symbol": trading_symbol,
        "lot_size":       lot_size,
    }'''

NEW_FIND_FN = '''\
def find_security(
    symbol: str,
    strike: int,
    expiry_date: str,
    option_type: str,
) -> dict:
    """
    Find Dhan security_id and trading_symbol for an options contract.
    Streams the CSV row by row — no full load into memory.

    Scrip master format (verified 2026-04-14):
      SEM_EXM_EXCH_ID: NSE | BSE
      SEM_SEGMENT:     D  (derivatives)
      SEM_INSTRUMENT_NAME: OPTIDX
      SEM_TRADING_SYMBOL:  NIFTY-Apr2026-23800-CE
      SEM_EXPIRY_DATE:     2026-04-17 14:30:00  (includes time)
      SEM_STRIKE_PRICE:    23800.00000
      SEM_OPTION_TYPE:     CE | PE
      SM_SYMBOL_NAME:      blank for options

    Args:
        symbol:      'NIFTY' or 'SENSEX'
        strike:      e.g. 23800
        expiry_date: 'YYYY-MM-DD'
        option_type: 'CE' or 'PE'

    Returns:
        {'security_id': '...', 'trading_symbol': '...', 'lot_size': int}
    """
    symbol      = symbol.upper()
    option_type = option_type.upper()
    exch_id     = EXCHANGE_ID[symbol]
    sym_prefix  = TRADING_SYMBOL_PREFIX[symbol]
    target_strike = int(strike)

    # Ensure cache exists
    load_scrip_master()

    if not SCRIP_CACHE.exists():
        raise RuntimeError("Scrip master cache not found. Run load_scrip_master() first.")

    log(f"Searching scrip master: {symbol} {strike} {option_type} expiry={expiry_date}")

    with SCRIP_CACHE.open(encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Exchange filter
            if row.get("SEM_EXM_EXCH_ID", "").strip() != exch_id:
                continue
            # Segment must be D (derivatives)
            if row.get("SEM_SEGMENT", "").strip() != "D":
                continue
            # Instrument type
            if row.get("SEM_INSTRUMENT_NAME", "").strip() != "OPTIDX":
                continue
            # Option type
            if row.get("SEM_OPTION_TYPE", "").strip().upper() != option_type:
                continue
            # Symbol prefix in trading symbol
            ts = row.get("SEM_TRADING_SYMBOL", "").strip()
            if not ts.startswith(sym_prefix):
                continue
            # Expiry date (stored as 'YYYY-MM-DD HH:MM:SS')
            row_expiry = row.get("SEM_EXPIRY_DATE", "").strip()[:10]
            if row_expiry != expiry_date:
                continue
            # Strike price
            try:
                row_strike = int(float(row.get("SEM_STRIKE_PRICE", "0")))
            except (ValueError, TypeError):
                continue
            if row_strike != target_strike:
                continue

            # Match found
            security_id = row.get("SEM_SMST_SECURITY_ID", "").strip()
            try:
                lot_size = int(float(row.get("SEM_LOT_UNITS", LOT_SIZE.get(symbol, 75))))
            except (ValueError, TypeError):
                lot_size = LOT_SIZE.get(symbol, 75)

            log(f"Found: {ts} | security_id={security_id} | lot_size={lot_size}")
            return {
                "security_id":    security_id,
                "trading_symbol": ts,
                "lot_size":       lot_size,
            }

    raise RuntimeError(
        f"Security not found: {symbol} {strike} {option_type} expiry={expiry_date}. "
        f"Checked scrip master: {SCRIP_CACHE}. "
        f"Verify expiry date format (YYYY-MM-DD) and that contract is in scrip master."
    )'''

# Also fix _test_mode to use a valid future expiry for testing
OLD_TEST = '''\
    if SUPABASE:
        rows = (SUPABASE.table("signal_snapshots")
                .select("symbol,atm_strike,expiry_date,dte")
                .eq("symbol", "NIFTY")
                .order("ts", desc=True)
                .limit(1)
                .execute().data)
        if rows:
            sig = rows[0]
            strike = int(sig["atm_strike"])
            expiry = sig["expiry_date"][:10]
            log(f"Testing with live signal: NIFTY {strike} CE expiry={expiry}")
            result = find_security("NIFTY", strike, expiry, "CE")
            log(f"Result: {result}")
        else:
            log("No signal found — testing with placeholder")
    else:
        log("Supabase not available — skipping signal fetch")'''

NEW_TEST = '''\
    # Find first available NIFTY option in scrip master for test
    load_scrip_master()
    test_row = None
    if SCRIP_CACHE.exists():
        import csv as _csv
        with SCRIP_CACHE.open(encoding="utf-8", errors="replace") as f:
            for row in _csv.DictReader(f):
                if (row.get("SEM_EXM_EXCH_ID","").strip() == "NSE"
                        and row.get("SEM_SEGMENT","").strip() == "D"
                        and row.get("SEM_INSTRUMENT_NAME","").strip() == "OPTIDX"
                        and row.get("SEM_TRADING_SYMBOL","").startswith("NIFTY-")
                        and row.get("SEM_OPTION_TYPE","").strip() == "CE"):
                    test_row = row
                    break

    if test_row:
        strike = int(float(test_row["SEM_STRIKE_PRICE"]))
        expiry = test_row["SEM_EXPIRY_DATE"].strip()[:10]
        log(f"Testing with first available NIFTY CE: strike={strike} expiry={expiry}")
        result = find_security("NIFTY", strike, expiry, "CE")
        log(f"Result: {result}")

        # Also test SENSEX
        with SCRIP_CACHE.open(encoding="utf-8", errors="replace") as f:
            for row in _csv.DictReader(f):
                if (row.get("SEM_EXM_EXCH_ID","").strip() == "BSE"
                        and row.get("SEM_SEGMENT","").strip() == "D"
                        and row.get("SEM_INSTRUMENT_NAME","").strip() == "OPTIDX"
                        and row.get("SEM_TRADING_SYMBOL","").startswith("SENSEX-")
                        and row.get("SEM_OPTION_TYPE","").strip() == "CE"):
                    s_strike = int(float(row["SEM_STRIKE_PRICE"]))
                    s_expiry = row["SEM_EXPIRY_DATE"].strip()[:10]
                    log(f"Testing SENSEX CE: strike={s_strike} expiry={s_expiry}")
                    s_result = find_security("SENSEX", s_strike, s_expiry, "CE")
                    log(f"SENSEX Result: {s_result}")
                    break
    else:
        log("No NIFTY options found in scrip master")'''


def main():
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found.")
        return 1

    source = TARGET.read_text(encoding="utf-8")

    if "SEM_SEGMENT.*D.*derivatives" in source or "Streams the CSV row by row" in source:
        print("Fix already applied.")
        return 0

    errors = []
    for name, anchor in [
        ("EXCHANGE_SEGMENT block", OLD_EXCHANGE_SEGMENT),
        ("load_scrip_master",      OLD_LOAD_FN),
        ("find_security",          OLD_FIND_FN),
        ("_test_mode body",        OLD_TEST),
    ]:
        if anchor not in source:
            errors.append(f"  MISSING anchor: {name}")

    if errors:
        print("ERROR: Anchors not found:")
        for e in errors:
            print(e)
        return 1

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    patched = source
    patched = patched.replace(OLD_EXCHANGE_SEGMENT, NEW_EXCHANGE_SEGMENT, 1)
    patched = patched.replace(OLD_LOAD_FN,          NEW_LOAD_FN,          1)
    patched = patched.replace(OLD_FIND_FN,          NEW_FIND_FN,          1)
    patched = patched.replace(OLD_TEST,             NEW_TEST,             1)

    TARGET.write_text(patched, encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    checks = [
        ("streaming CSV",     "Streams the CSV row by row" in result),
        ("EXCHANGE_ID dict",  "EXCHANGE_ID" in result),
        ("segment D filter",  'strip() != "D"' in result),
        ("sym prefix filter", "sym_prefix" in result),
    ]
    all_ok = True
    for name, ok in checks:
        print(f"  {'OK' if ok else 'FAIL'}: {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print(f"\nPatched: {TARGET}")
        print("Now commit, push, pull on AWS, and re-run:")
        print("  python3 merdian_order_placer.py --test")
    else:
        print("\nERROR: Restoring backup.")
        shutil.copy2(BACKUP, TARGET)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
