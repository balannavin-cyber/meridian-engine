#!/usr/bin/env python3
"""Apply breadth universe patch to ws_feed_zerodha.py using line-based replacement."""
import shutil
from pathlib import Path

TARGET = Path("ws_feed_zerodha.py")
BACKUP = Path("ws_feed_zerodha.py.bak_breadth")

BREADTH_LOADER = '''
def load_breadth_universe(kite) -> dict:
    """
    Load NSE EQ breadth universe from Supabase and match to Zerodha instrument tokens.
    Returns: {instrument_token: {symbol, instrument_type, tradingsymbol}}
    """
    import requests as _req
    log.info("Loading NSE EQ breadth universe from Supabase...")

    # Fetch breadth symbols from Supabase
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        url = f"{SUPABASE_URL}/rest/v1/breadth_universe_members"
        params = {"select": "symbol,exchange", "is_active": "eq.true", "active": "eq.true", "limit": "2000"}
        r = _req.get(url, headers=headers, params=params, timeout=15)
        if r.status_code != 200:
            log.warning(f"  Breadth universe fetch failed: {r.status_code}")
            return {}
        members = r.json()
        breadth_symbols = {row["symbol"] for row in members if row.get("exchange") == "NSE"}
        log.info(f"  Breadth universe: {len(breadth_symbols)} NSE symbols")
    except Exception as e:
        log.warning(f"  Breadth universe fetch error: {e}")
        return {}

    # Download NSE EQ instruments from Zerodha
    try:
        nse = kite.instruments("NSE")
        log.info(f"  NSE instruments downloaded: {len(nse)} rows")
    except Exception as e:
        log.warning(f"  NSE instruments download failed: {e}")
        return {}

    # Match symbols
    breadth_instruments = {}
    for inst in nse:
        sym = inst.get("tradingsymbol", "")
        if sym not in breadth_symbols:
            continue
        if inst.get("instrument_type") != "EQ":
            continue
        token = inst.get("instrument_token")
        if not token:
            continue
        breadth_instruments[token] = {
            "exchange":        "NSE",
            "symbol":          sym,
            "instrument_type": "EQ",
            "tradingsymbol":   sym,
            "expiry_date":     None,
            "strike":          None,
        }

    log.info(f"  Breadth matched: {len(breadth_instruments)}/{len(breadth_symbols)} symbols")
    return breadth_instruments

'''

NEW_TRIM_BLOCK = '''    # Load breadth universe (NSE EQ stocks)
    breadth = load_breadth_universe(kite)
    instruments.update(breadth)
    log.info(f"  After breadth: {len(instruments)} total instruments")

    # Trim to Zerodha 3000 limit — priority: spots > futures > EQ breadth > options
    if len(instruments) > 3000:
        log.warning(f"  {len(instruments)} > 3000 limit — trimming options to fit")
        opts  = {t: v for t, v in instruments.items() if v["instrument_type"] in ("CE", "PE")}
        futs  = {t: v for t, v in instruments.items() if v["instrument_type"] == "FUT"}
        spots = {t: v for t, v in instruments.items() if v["instrument_type"] == "SPOT"}
        eq    = {t: v for t, v in instruments.items() if v["instrument_type"] == "EQ"}
        max_opts = max(0, 3000 - len(spots) - len(futs) - len(eq))
        opt_items = sorted(opts.items(), key=lambda x: x[1].get("strike") or 0)
        instruments = {**spots, **futs, **eq, **dict(opt_items[:max_opts])}
        log.info(f"  After trim: {len(instruments)} "
                 f"(spots={len(spots)}, fut={len(futs)}, eq={len(eq)}, opts={min(max_opts,len(opts))})")
    return instruments
'''


def main():
    source = TARGET.read_text(encoding="utf-8")

    if "load_breadth_universe" in source:
        print("Already patched.")
        return 0

    lines = source.splitlines(keepends=True)

    # Find the trim block: starts at "if len(instruments) > 3000:"
    # ends at "return instruments" (first one after that)
    trim_start = None
    trim_end = None
    for i, line in enumerate(lines):
        if trim_start is None and "if len(instruments) > 3000:" in line:
            trim_start = i
        if trim_start is not None and line.strip() == "return instruments":
            trim_end = i + 1
            break

    if trim_start is None or trim_end is None:
        print(f"ERROR: could not find trim block (start={trim_start}, end={trim_end})")
        return 1

    print(f"Found trim block at lines {trim_start+1}–{trim_end}")

    # Find insertion point for breadth loader — before "# ── Tick processor"
    insert_at = None
    for i, line in enumerate(lines):
        if "Tick processor" in line or "class TickProcessor" in line:
            insert_at = i
            break

    if insert_at is None:
        print("ERROR: TickProcessor anchor not found")
        return 1

    print(f"Inserting breadth loader before line {insert_at+1}")

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    # Build new file:
    # 1. Everything up to trim block
    # 2. New trim block (with breadth call)
    # 3. Everything between trim block end and TickProcessor
    # 4. Breadth loader function
    # 5. TickProcessor onwards

    new_lines = (
        lines[:trim_start] +
        [NEW_TRIM_BLOCK] +
        lines[trim_end:insert_at] +
        [BREADTH_LOADER] +
        lines[insert_at:]
    )

    TARGET.write_text("".join(new_lines), encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    checks = [
        ("breadth loader", "load_breadth_universe" in result),
        ("breadth call in load_instruments", "breadth = load_breadth_universe(kite)" in result),
        ("EQ priority in trim", "eq    = {t:" in result or "eq = {t:" in result),
        ("3000 limit preserved", "3000" in result),
    ]
    all_ok = True
    for name, ok in checks:
        print(f"  {'OK' if ok else 'FAIL'}: {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\nOK: ws_feed_zerodha.py patched with breadth universe")
        return 0
    else:
        print("\nERROR: restoring backup")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
