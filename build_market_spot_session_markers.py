from __future__ import annotations

import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client


IST = timezone(timedelta(hours=5, minutes=30))


def fail(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def ist_dt(d: date, hh: int, mm: int, ss: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, ss, tzinfo=IST)


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def load_supabase() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url:
        fail("Missing SUPABASE_URL in environment/.env")
    if not key:
        fail("Missing SUPABASE_SERVICE_ROLE_KEY in environment/.env")

    return create_client(url, key)


SUPABASE = load_supabase()


def select_rows(
    table_name: str,
    columns: str,
    *,
    filters_eq: dict[str, Any] | None = None,
    gte: tuple[str, Any] | None = None,
    lte: tuple[str, Any] | None = None,
    gt: tuple[str, Any] | None = None,
    lt: tuple[str, Any] | None = None,
    order_by: str | None = None,
    desc: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    query = SUPABASE.table(table_name).select(columns)

    if filters_eq:
        for k, v in filters_eq.items():
            query = query.eq(k, v)

    if gte:
        query = query.gte(gte[0], gte[1])

    if lte:
        query = query.lte(lte[0], lte[1])

    if gt:
        query = query.gt(gt[0], gt[1])

    if lt:
        query = query.lt(lt[0], lt[1])

    if order_by:
        query = query.order(order_by, desc=desc)

    if limit is not None:
        query = query.limit(limit)

    resp = query.execute()
    return getattr(resp, "data", None) or []


def latest_trade_date_from_spot() -> date:
    rows = select_rows(
        "market_spot_snapshots",
        "ts",
        order_by="ts",
        desc=True,
        limit=1,
    )
    if not rows:
        fail("No rows found in public.market_spot_snapshots")
    ts = parse_ts(rows[0]["ts"])
    if ts is None:
        fail("Could not parse latest ts from market_spot_snapshots")
    return ts.astimezone(IST).date()


def pick_first_row_in_window(symbol: str, start_ist: datetime, end_ist: datetime) -> dict[str, Any] | None:
    rows = select_rows(
        "market_spot_snapshots",
        "symbol, ts, spot, source_table, source_id, raw",
        filters_eq={"symbol": symbol},
        gte=("ts", utc_iso(start_ist)),
        lte=("ts", utc_iso(end_ist)),
        order_by="ts",
        desc=False,
        limit=1,
    )
    return rows[0] if rows else None


def pick_last_row_in_window(symbol: str, start_ist: datetime, end_ist: datetime) -> dict[str, Any] | None:
    rows = select_rows(
        "market_spot_snapshots",
        "symbol, ts, spot, source_table, source_id, raw",
        filters_eq={"symbol": symbol},
        gte=("ts", utc_iso(start_ist)),
        lte=("ts", utc_iso(end_ist)),
        order_by="ts",
        desc=True,
        limit=1,
    )
    return rows[0] if rows else None


def get_premarket_ref(symbol: str, trade_date: date) -> dict[str, Any] | None:
    exact = pick_first_row_in_window(
        symbol,
        ist_dt(trade_date, 9, 7, 30),
        ist_dt(trade_date, 9, 8, 30),
    )
    if exact:
        return exact

    return pick_last_row_in_window(
        symbol,
        ist_dt(trade_date, 9, 0, 0),
        ist_dt(trade_date, 9, 8, 59),
    )


def get_open_0915(symbol: str, trade_date: date) -> dict[str, Any] | None:
    return pick_first_row_in_window(
        symbol,
        ist_dt(trade_date, 9, 14, 30),
        ist_dt(trade_date, 9, 15, 59),
    )


def get_close_1530(symbol: str, trade_date: date) -> dict[str, Any] | None:
    return pick_last_row_in_window(
        symbol,
        ist_dt(trade_date, 15, 29, 0),
        ist_dt(trade_date, 15, 30, 59),
    )


def get_postmarket_ref(symbol: str, trade_date: date) -> dict[str, Any] | None:
    return pick_first_row_in_window(
        symbol,
        ist_dt(trade_date, 16, 0, 0),
        ist_dt(trade_date, 23, 59, 59),
    )


def get_prev_close_spot(symbol: str, trade_date: date) -> float | None:
    prev_day = trade_date - timedelta(days=1)

    post_row = get_postmarket_ref(symbol, prev_day)
    if post_row and to_float(post_row.get("spot")) is not None:
        return to_float(post_row.get("spot"))

    close_row = get_close_1530(symbol, prev_day)
    if close_row and to_float(close_row.get("spot")) is not None:
        return to_float(close_row.get("spot"))

    rows = select_rows(
        "market_spot_snapshots",
        "symbol, ts, spot",
        filters_eq={"symbol": symbol},
        gte=("ts", utc_iso(ist_dt(prev_day, 0, 0, 0))),
        lte=("ts", utc_iso(ist_dt(prev_day, 23, 59, 59))),
        order_by="ts",
        desc=True,
        limit=1,
    )
    if rows:
        return to_float(rows[0].get("spot"))

    return None


def compute_gap_open_pct(prev_close_spot: float | None, open_0915_spot: float | None) -> float | None:
    if prev_close_spot is None or open_0915_spot is None or prev_close_spot == 0:
        return None
    return ((open_0915_spot - prev_close_spot) / prev_close_spot) * 100.0


def compute_premarket_move_pct(prev_close_spot: float | None, premarket_ref_spot: float | None) -> float | None:
    if prev_close_spot is None or premarket_ref_spot is None or prev_close_spot == 0:
        return None
    return ((premarket_ref_spot - prev_close_spot) / prev_close_spot) * 100.0


def compute_postmarket_move_pct(close_1530_spot: float | None, postmarket_ref_spot: float | None) -> float | None:
    if close_1530_spot is None or postmarket_ref_spot is None or close_1530_spot == 0:
        return None
    return ((postmarket_ref_spot - close_1530_spot) / close_1530_spot) * 100.0


def derive_capture_quality(
    premarket: bool,
    open_0915: bool,
    close_1530: bool,
    postmarket: bool,
) -> str:
    if premarket and open_0915 and close_1530 and postmarket:
        return "COMPLETE"
    if open_0915 and not premarket and not close_1530 and not postmarket:
        return "PARTIAL_OPEN_ONLY"
    if premarket and not open_0915 and not close_1530 and not postmarket:
        return "PREMARKET_ONLY"
    if postmarket and not premarket and not open_0915 and not close_1530:
        return "POSTMARKET_ONLY"
    if premarket and open_0915 and close_1530 and not postmarket:
        return "MISSING_POSTMARKET"
    if premarket and open_0915 and not close_1530 and postmarket:
        return "MISSING_CLOSE_1530"
    if not premarket and open_0915 and close_1530 and postmarket:
        return "MISSING_PREMARKET"
    if not premarket and open_0915 and close_1530 and not postmarket:
        return "OPEN_CLOSE_ONLY"
    if premarket and open_0915 and not close_1530 and not postmarket:
        return "PREMARKET_AND_OPEN_ONLY"
    if premarket and not open_0915 and close_1530 and postmarket:
        return "MISSING_OPEN_0915"
    return "MISSING"


def build_row_for_symbol(symbol: str, trade_date: date) -> dict[str, Any]:
    pre = get_premarket_ref(symbol, trade_date)
    opn = get_open_0915(symbol, trade_date)
    cls = get_close_1530(symbol, trade_date)
    post = get_postmarket_ref(symbol, trade_date)
    prev_close_spot = get_prev_close_spot(symbol, trade_date)

    pre_spot = to_float(pre.get("spot")) if pre else None
    open_spot = to_float(opn.get("spot")) if opn else None
    close_spot = to_float(cls.get("spot")) if cls else None
    post_spot = to_float(post.get("spot")) if post else None

    capture_quality = derive_capture_quality(
        premarket=pre is not None,
        open_0915=opn is not None,
        close_1530=cls is not None,
        postmarket=post is not None,
    )

    notes_parts: list[str] = []

    if post is not None:
        post_ts_ist = parse_ts(post["ts"]).astimezone(IST)
        if post_ts_ist.time() != time(16, 0):
            notes_parts.append(
                f"Postmarket ref captured after 16:00 IST at {post_ts_ist.strftime('%H:%M:%S')}"
            )

    if pre is None:
        notes_parts.append("Premarket reference missing")
    if opn is None:
        notes_parts.append("09:15 open missing")
    if cls is None:
        notes_parts.append("15:30 close-side row missing")
    if post is None:
        notes_parts.append("Postmarket reference missing")
    if prev_close_spot is None:
        notes_parts.append("Previous close spot unavailable")

    return {
        "trade_date_ist": trade_date.isoformat(),
        "symbol": symbol,
        "prev_close_spot": prev_close_spot,
        "premarket_ref_ts": pre.get("ts") if pre else None,
        "premarket_ref_spot": pre_spot,
        "open_0915_ts": opn.get("ts") if opn else None,
        "open_0915_spot": open_spot,
        "close_1530_ts": cls.get("ts") if cls else None,
        "close_1530_spot": close_spot,
        "postmarket_ref_ts": post.get("ts") if post else None,
        "postmarket_ref_spot": post_spot,
        "gap_open_pct": compute_gap_open_pct(prev_close_spot, open_spot),
        "premarket_move_pct": compute_premarket_move_pct(prev_close_spot, pre_spot),
        "postmarket_move_pct": compute_postmarket_move_pct(close_spot, post_spot),
        "capture_quality": capture_quality,
        "notes": " | ".join(notes_parts) if notes_parts else None,
    }


def upsert_rows(rows: list[dict[str, Any]]) -> None:
    (
        SUPABASE
        .table("market_spot_session_markers")
        .upsert(rows, on_conflict="trade_date_ist,symbol")
        .execute()
    )


def _is_market_open_today() -> bool:
    """Holiday gate: check trading_calendar. Fail-open on any error."""
    try:
        import os as _os
        try:
            from dotenv import load_dotenv as _lde
            _lde()
        except ImportError:
            pass
        import requests as _req
        from datetime import datetime as _dt, timezone as _tz
        from zoneinfo import ZoneInfo as _ZI
        _url = _os.getenv("SUPABASE_URL", "").rstrip("/")
        _key = _os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not _url or not _key:
            return True  # can't check — allow run
        _today = _dt.now(_tz.utc).astimezone(_ZI("Asia/Kolkata")).date().isoformat()
        _r = _req.get(
            f"{_url}/rest/v1/trading_calendar",
            headers={"apikey": _key, "Authorization": f"Bearer {_key}"},
            params={"trade_date": f"eq.{_today}", "select": "is_open,open_time"},
            timeout=10,
        )
        if _r.status_code == 200:
            _rows = _r.json()
            if _rows:
                _row = _rows[0]
                return bool(_row.get("is_open", True)) and _row.get("open_time") is not None
        return True  # no row — allow run
    except Exception:
        return True  # error — allow run

def main() -> None:
    # ── Holiday gate ───────────────────────────────────────────────────────
    if not _is_market_open_today():
        print("[HOLIDAY GATE] Market closed — build_market_spot_session_markers exiting.")
        return
    # ────────────────────────────────────────────────────────────────────────

    if len(sys.argv) > 2:
        fail("Usage: python .\\build_market_spot_session_markers.py [YYYY-MM-DD]")

    if len(sys.argv) == 2:
        trade_date = date.fromisoformat(sys.argv[1])
    else:
        trade_date = latest_trade_date_from_spot()

    print("============================================================")
    print("MERDIAN - build_market_spot_session_markers.py")
    print("============================================================")
    print(f"Trade date (IST): {trade_date.isoformat()}")

    rows = []
    for symbol in ("NIFTY", "SENSEX"):
        row = build_row_for_symbol(symbol, trade_date)
        rows.append(row)
        print("------------------------------------------------------------")
        print(f"Symbol: {symbol}")
        print(f"Capture quality: {row['capture_quality']}")
        print(f"Prev close spot: {row['prev_close_spot']}")
        print(f"Premarket ref ts: {row['premarket_ref_ts']}")
        print(f"Open 0915 ts: {row['open_0915_ts']}")
        print(f"Close 1530 ts: {row['close_1530_ts']}")
        print(f"Postmarket ref ts: {row['postmarket_ref_ts']}")
        print(f"Gap open pct: {row['gap_open_pct']}")
        print(f"Notes: {row['notes']}")

    print("------------------------------------------------------------")
    print("Writing session-marker rows to Supabase...")
    upsert_rows(rows)
    print(f"Upserted rows: {len(rows)}")
    print("BUILD MARKET SPOT SESSION MARKERS COMPLETED")


if __name__ == "__main__":
    main()
