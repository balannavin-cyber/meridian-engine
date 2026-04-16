#!/usr/bin/env python3
"""Fix breadth universe fetch in ws_feed_zerodha.py to paginate past 1000 row limit."""
import shutil
from pathlib import Path

TARGET = Path("ws_feed_zerodha.py")
BACKUP = Path("ws_feed_zerodha.py.bak_breadth_limit")

OLD = '''        params = {"select": "symbol,exchange", "is_active": "eq.true", "active": "eq.true", "limit": "2000"}
        r = _req.get(url, headers=headers, params=params, timeout=15)
        if r.status_code != 200:
            log.warning(f"  Breadth universe fetch failed: {r.status_code}")
            return {}
        members = r.json()
        breadth_symbols = {row["symbol"] for row in members if row.get("exchange") == "NSE"}
        log.info(f"  Breadth universe: {len(breadth_symbols)} NSE symbols")'''

NEW = '''        # Paginate to get all members past Supabase 1000-row limit
        members = []
        page_size = 1000
        offset = 0
        while True:
            params = {
                "select": "symbol,exchange",
                "is_active": "eq.true",
                "active": "eq.true",
                "limit": str(page_size),
                "offset": str(offset),
            }
            r = _req.get(url, headers=headers, params=params, timeout=15)
            if r.status_code != 200:
                log.warning(f"  Breadth universe fetch failed: {r.status_code}")
                break
            page = r.json()
            if not page:
                break
            members.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        breadth_symbols = {row["symbol"] for row in members if row.get("exchange") == "NSE"}
        log.info(f"  Breadth universe: {len(breadth_symbols)} NSE symbols")'''


def main():
    source = TARGET.read_text(encoding="utf-8")

    if "offset" in source and "breadth_symbols" in source:
        print("Pagination already applied.")
        return 0

    if OLD not in source:
        print("ERROR: anchor not found")
        for i, line in enumerate(source.splitlines(), 1):
            if "breadth_universe_members" in line or "limit.*2000" in line:
                print(f"  Line {i}: {line.strip()}")
        return 1

    shutil.copy2(TARGET, BACKUP)
    patched = source.replace(OLD, NEW, 1)
    TARGET.write_text(patched, encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if "offset" in result and "breadth_symbols" in result:
        print("OK: breadth fetch now paginates — will get all 1,385 stocks")
        return 0
    else:
        print("ERROR: restoring")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
