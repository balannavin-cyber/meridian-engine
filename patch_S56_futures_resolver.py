#!/usr/bin/env python3
"""
S56 patch: capture_index_futures_snapshot_local.py resolver
Repoint futures contract resolution from fragile DISPLAY_NAME substring + alias/reject
blocklist to EXACT UNDERLYING_SYMBOL match. Fixes NIFTY -> NIFTYNXT50 misresolution.
Canon-v3: read_bytes/decode utf-8-sig, EOL detect, ast.parse, _PRE_S56 backup,
idempotency marker, dry-run default (--apply to write).
"""
import argparse, ast, os, sys, datetime

TARGET = "capture_index_futures_snapshot_local.py"
MARKER = "# [S56-RESOLVER-EXACT-UNDERLYING]"

OLD_QUERY = """                "select": (
                    '"SECURITY_ID","DISPLAY_NAME","INSTRUMENT_TYPE","SM_EXPIRY_DATE","SEGMENT","EXCH_ID"'
                ),
                '"DISPLAY_NAME"': f"ilike.*{alias}*",
                '"INSTRUMENT_TYPE"': "ilike.*FUT*",
                '"SM_EXPIRY_DATE"': f"gte.{today}",
                "order": '"SM_EXPIRY_DATE".asc',
                "limit": "20","""

NEW_QUERY = """                "select": (
                    '"SECURITY_ID","DISPLAY_NAME","INSTRUMENT","INSTRUMENT_TYPE","UNDERLYING_SYMBOL","SM_EXPIRY_DATE","SEGMENT","EXCH_ID"'
                ),  # [S56-RESOLVER-EXACT-UNDERLYING]
                '"UNDERLYING_SYMBOL"': f"eq.{symbol}",
                '"INSTRUMENT"': "eq.FUTIDX",
                '"SM_EXPIRY_DATE"': f"gte.{today}",
                "order": '"SM_EXPIRY_DATE".asc',
                "limit": "20","""

OLD_LOADER = '''    aliases = FUTURES_SYMBOLS[symbol]["aliases"]
    all_rows: List[Dict[str, Any]] = []
    for alias in aliases:
        rows = supabase_get(
            "dhan_scripmaster",
            {'''

NEW_LOADER = '''    all_rows: List[Dict[str, Any]] = []
    if True:  # exact UNDERLYING_SYMBOL match: one query per symbol, no alias loop
        rows = supabase_get(
            "dhan_scripmaster",
            {'''

OLD_VALIDATOR = '''def is_valid_contract_match(symbol: str, row: Dict[str, Any]) -> bool:
    display_name = str(row.get("DISPLAY_NAME") or "").upper()
    instrument_type = str(row.get("INSTRUMENT_TYPE") or "").upper()
    if "FUT" not in instrument_type:
        return False
    aliases = [a.upper() for a in FUTURES_SYMBOLS[symbol]["aliases"]]
    if not any(alias in display_name for alias in aliases):
        return False
    reject_terms = [x.upper() for x in FUTURES_SYMBOLS[symbol]["reject_if_display_contains"]]
    if any(term in display_name for term in reject_terms):
        return False
    return True'''

NEW_VALIDATOR = '''def is_valid_contract_match(symbol: str, row: Dict[str, Any]) -> bool:
    # [S56-RESOLVER-EXACT-UNDERLYING] exact UNDERLYING_SYMBOL + INSTRUMENT
    underlying = str(row.get("UNDERLYING_SYMBOL") or "").upper()
    instrument = str(row.get("INSTRUMENT") or "").upper()
    if underlying != symbol.upper():
        return False
    if instrument != "FUTIDX":
        return False
    return True'''


def detect_eol(b):
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    return "\r\n" if crlf > lf else "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(TARGET):
        print("[ERROR] " + TARGET + " not found in cwd")
        return 1

    raw = open(TARGET, "rb").read()
    text = raw.decode("utf-8-sig")
    eol = detect_eol(raw)

    if MARKER in text:
        print("[SKIP] marker present; already patched. No change.")
        return 0

    edits = [
        ("query filter", OLD_QUERY, NEW_QUERY),
        ("loader alias loop", OLD_LOADER, NEW_LOADER),
        ("validator", OLD_VALIDATOR, NEW_VALIDATOR),
    ]
    new_text = text
    for name, old, new in edits:
        n = new_text.count(old)
        if n != 1:
            print("[ERROR] block '" + name + "' matched " + str(n) + " times (need 1). Abort, no write.")
            return 1
        new_text = new_text.replace(old, new)
        print("[OK] matched + staged: " + name)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print("[ERROR] patched text fails ast.parse: " + str(e))
        return 1
    print("[OK] ast.parse clean")

    if not args.apply:
        print("[DRY-RUN] 3/3 blocks matched, AST valid. No write. Re-run with --apply.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET + "_PRE_S56_" + ts
    open(backup, "wb").write(raw)
    print("[BACKUP] " + backup)

    out_bytes = new_text.encode("utf-8")
    open(TARGET, "wb").write(out_bytes)
    print("[WROTE] " + TARGET)
    return 0


if __name__ == "__main__":
    sys.exit(main())
