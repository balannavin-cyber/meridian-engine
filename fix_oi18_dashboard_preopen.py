"""
OI-18 fix: merdian_live_dashboard.get_preopen_status() false-negative.

Resume prompt framed this as a capture_spot_1m writer bug ("doesn't
set is_pre_market=true"). SQL evidence contradicts: pre-open bars
(09:05, 09:14 IST) are written correctly to hist_spot_bars_1m.
Real root cause is in the dashboard's query.

Two bugs in get_preopen_status():

1. order=ts.asc&limit=10 returns the 10 OLDEST rows in
   market_spot_snapshots (table is append-only and grows forever),
   not today's rows. Loop filters them against "today"; finds zero
   matches after day one. Permanent NOT CAPTURED after first
   operational day.

2. Time window `dt.hour == 9 and dt.minute < 9` covers 09:00-09:08
   only. Actual live capture produces bars at 09:05 and 09:14 IST
   per merdian_start / MERDIAN_PreOpen / MERDIAN_Spot_1M schedule.
   The 09:14 bar is outside the window even when rows are correct.

Fix: query today's rows directly with a ts lower-bound filter;
widen window to 09:00-09:14 inclusive (pre-open window closes
09:15 at market open).

No writer change. No consumer change. Column is_pre_market stays
dead for now; separate ENH to be filed for column cleanup if
desired.
"""
import ast
import sys
from pathlib import Path

TARGET = Path(r"C:\GammaEnginePython\merdian_live_dashboard.py")

OLD_FUNC = '''def get_preopen_status() -> Dict:
    rows = sb_get("market_spot_snapshots", "select=ts,spot,symbol&order=ts.asc&limit=10")
    today = now_ist().strftime("%Y-%m-%d")
    captured = []
    for row in rows:
        dt = parse_ist_dt(row.get("ts", ""))
        if dt and dt.strftime("%Y-%m-%d") == today and dt.hour == 9 and dt.minute < 9:
            captured.append({
                "ts": dt.strftime("%H:%M:%S"),
                "spot": row.get("spot"),
                "symbol": row.get("symbol"),
            })
    return {"captured": len(captured) > 0, "count": len(captured), "rows": captured[:3]}'''

NEW_FUNC = '''def get_preopen_status() -> Dict:
    # OI-18 fix 2026-04-22: prior query `order=ts.asc&limit=10`
    # returned the 10 oldest rows in market_spot_snapshots (table
    # grows forever) and always failed the today-filter after day
    # one. Also the old window was hour==9 and minute<9 which
    # missed the 09:14 bar. Pre-open is 09:00 up to but not
    # including 09:15 (market open). Query today's rows directly
    # using an IST start-of-day lower bound rendered as UTC ISO.
    today_ist = now_ist().replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_ist.astimezone(timezone.utc).isoformat()
    rows = sb_get(
        "market_spot_snapshots",
        f"select=ts,spot,symbol&ts=gte.{today_start_utc}&order=ts.asc&limit=200",
    )
    today_str = now_ist().strftime("%Y-%m-%d")
    captured = []
    for row in rows:
        dt = parse_ist_dt(row.get("ts", ""))
        if (
            dt
            and dt.strftime("%Y-%m-%d") == today_str
            and dt.hour == 9
            and dt.minute < 15
        ):
            captured.append({
                "ts": dt.strftime("%H:%M:%S"),
                "spot": row.get("spot"),
                "symbol": row.get("symbol"),
            })
    return {"captured": len(captured) > 0, "count": len(captured), "rows": captured[:6]}'''


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    if OLD_FUNC not in src:
        print("ERROR: get_preopen_status() not found verbatim. Aborting.")
        return 2

    if src.count(OLD_FUNC) != 1:
        print(f"ERROR: function body found {src.count(OLD_FUNC)} times, expected 1.")
        return 3

    new_src = src.replace(OLD_FUNC, NEW_FUNC)

    # Dashboard imports `timezone` already via `from datetime import ...`?
    # Check. If not, the replacement adds a NameError.
    if "timezone" not in new_src.split("def get_preopen_status")[0]:
        print("WARN: `timezone` symbol not visible in module scope before "
              "get_preopen_status. Patch will NameError at runtime. "
              "Manual import add required.")
        # Do NOT auto-add imports - too risky. Report and abort.
        return 4

    # V18H governance: ast.parse() validation.
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"SYNTAX ERROR: {e}")
        return 5

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"OK: {TARGET} patched. OI-18 closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())