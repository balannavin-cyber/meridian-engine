from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.supabase_client import SupabaseClient


UTC = timezone.utc
IST = timezone(timedelta(hours=5, minutes=30))

SYMBOLS = ["NIFTY", "SENSEX"]

MARKET_OPEN_IST = dt_time(hour=9, minute=15)
MARKET_CLOSE_IST = dt_time(hour=15, minute=30)

CHECKS = [
    {
        "label": "spot",
        "table": "market_spot_snapshots",
        "ts_column": "ts",
        "max_age_live_minutes": 3,
        "required_live": True,
    },
    {
        "label": "futures",
        "table": "index_futures_snapshots",
        "ts_column": "ts",
        "max_age_live_minutes": 3,
        "required_live": True,
    },
    {
        "label": "volatility",
        "table": "volatility_snapshots",
        "ts_column": "ts",
        "max_age_live_minutes": 8,
        "required_live": True,
    },
    {
        "label": "market_state",
        "table": "market_state_snapshots",
        "ts_column": "ts",
        "max_age_live_minutes": 8,
        "required_live": True,
    },
    {
        "label": "signal_state",
        "table": "signal_state_snapshots",
        "ts_column": "ts",
        "max_age_live_minutes": 8,
        "required_live": True,
    },
    {
        "label": "shadow_state_signal",
        "table": "shadow_state_signal_snapshots",
        "ts_column": "created_at",
        "max_age_live_minutes": 8,
        "required_live": True,
    },
    {
        "label": "shadow_state_outcome",
        "table": "shadow_state_signal_outcomes",
        "ts_column": "signal_ts",
        "max_age_live_minutes": 15,
        "required_live": False,
    },
]


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def ist_now() -> datetime:
    return datetime.now(tz=IST)


def parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(UTC)


def age_minutes(dt: datetime) -> float:
    return (utc_now() - dt).total_seconds() / 60.0


def is_weekday_ist(ref: datetime) -> bool:
    return ref.weekday() < 5


def session_open_dt_ist(ref: datetime) -> datetime:
    return ref.replace(
        hour=MARKET_OPEN_IST.hour,
        minute=MARKET_OPEN_IST.minute,
        second=0,
        microsecond=0,
    )


def session_close_dt_ist(ref: datetime) -> datetime:
    return ref.replace(
        hour=MARKET_CLOSE_IST.hour,
        minute=MARKET_CLOSE_IST.minute,
        second=0,
        microsecond=0,
    )


def get_market_phase(ref_ist: datetime) -> str:
    if not is_weekday_ist(ref_ist):
        return "OFFDAY"

    open_dt = session_open_dt_ist(ref_ist)
    close_dt = session_close_dt_ist(ref_ist)

    if ref_ist < open_dt:
        return "PREOPEN"

    if open_dt <= ref_ist <= close_dt:
        return "LIVE"

    return "POSTMARKET"


def today_close_utc(ref_ist: datetime) -> datetime:
    close_ist = session_close_dt_ist(ref_ist)
    return close_ist.astimezone(UTC)


def previous_trading_close_utc(ref_ist: datetime) -> datetime:
    probe = ref_ist

    if get_market_phase(ref_ist) == "LIVE":
        return today_close_utc(ref_ist)

    if get_market_phase(ref_ist) == "POSTMARKET":
        return today_close_utc(ref_ist)

    probe = probe - timedelta(days=1)
    while probe.weekday() >= 5:
        probe -= timedelta(days=1)

    return session_close_dt_ist(probe).astimezone(UTC)


def fetch_latest_row(
    sb: SupabaseClient,
    table: str,
    symbol: str,
    ts_column: str,
) -> Optional[Dict[str, Any]]:
    rows = sb.select(
        table=table,
        filters={"symbol": f"eq.{symbol}"},
        order=f"{ts_column}.desc",
        limit=1,
    )
    if not rows:
        return None
    return rows[0]


def fmt_dt(dt: Optional[datetime]) -> str:
    if dt is None:
        return "-"
    return dt.isoformat()


def fmt_age(age_mins: Optional[float]) -> str:
    if age_mins is None:
        return "-"
    return f"{age_mins:.2f}"


def session_aware_status(
    latest_ts: Optional[datetime],
    age_mins: Optional[float],
    max_age_live_minutes: int,
    market_phase: str,
    required_live: bool,
    baseline_close_utc: datetime,
) -> str:
    if latest_ts is None:
        if market_phase == "LIVE" and required_live:
            return "MISSING"
        return "IDLE_OK"

    if market_phase == "LIVE":
        if age_mins is None:
            return "MISSING"
        if age_mins <= max_age_live_minutes:
            return "OK"
        return "STALE"

    # PREOPEN / POSTMARKET / OFFDAY
    if latest_ts <= baseline_close_utc:
        return "POSTMARKET_OK"

    # A row newer than prior close exists, which is also acceptable.
    return "POSTMARKET_OK"


def evaluate_check(
    sb: SupabaseClient,
    symbol: str,
    check: Dict[str, Any],
    market_phase: str,
    baseline_close_utc: datetime,
) -> Dict[str, Any]:
    row = fetch_latest_row(
        sb=sb,
        table=check["table"],
        symbol=symbol,
        ts_column=check["ts_column"],
    )

    ts_value = None if row is None else row.get(check["ts_column"])
    parsed = parse_ts(ts_value)
    age_mins = None if parsed is None else age_minutes(parsed)

    status = session_aware_status(
        latest_ts=parsed,
        age_mins=age_mins,
        max_age_live_minutes=check["max_age_live_minutes"],
        market_phase=market_phase,
        required_live=check["required_live"],
        baseline_close_utc=baseline_close_utc,
    )

    return {
        "symbol": symbol,
        "label": check["label"],
        "table": check["table"],
        "ts_column": check["ts_column"],
        "max_age_live_minutes": check["max_age_live_minutes"],
        "required_live": check["required_live"],
        "latest_ts": parsed,
        "age_minutes": age_mins,
        "status": status,
    }


def print_section_header(title: str) -> None:
    print("=" * 104)
    print(title)
    print("=" * 104)


def print_symbol_block(symbol: str, results: List[Dict[str, Any]]) -> None:
    print("-" * 104)
    print(f"SYMBOL: {symbol}")
    print("-" * 104)
    print(
        f"{'CHECK':<24}"
        f"{'STATUS':<18}"
        f"{'AGE_MIN':<12}"
        f"{'LIVE_MAX':<10}"
        f"{'LATEST_TS_UTC'}"
    )
    print("-" * 104)

    for r in results:
        print(
            f"{r['label']:<24}"
            f"{r['status']:<18}"
            f"{fmt_age(r['age_minutes']):<12}"
            f"{str(r['max_age_live_minutes']):<10}"
            f"{fmt_dt(r['latest_ts'])}"
        )

    print()


def overall_verdict(all_results: List[Dict[str, Any]], market_phase: str) -> Tuple[str, int, int]:
    bad = [r for r in all_results if r["status"] in {"STALE", "MISSING"}]
    missing = [r for r in all_results if r["status"] == "MISSING"]

    if market_phase == "LIVE":
        if not bad:
            return "HEALTHY_LIVE", 0, 0
        if missing:
            return "DEGRADED_MISSING_DATA", len(bad), len(missing)
        return "DEGRADED_STALE_DATA", len(bad), 0

    # PREOPEN / POSTMARKET / OFFDAY
    if not bad:
        return "HEALTHY_POSTMARKET", 0, 0

    if missing:
        return "DEGRADED_MISSING_DATA", len(bad), len(missing)

    return "DEGRADED_POSTMARKET", len(bad), 0


def print_failed_checks(all_results: List[Dict[str, Any]]) -> None:
    failed = [r for r in all_results if r["status"] in {"STALE", "MISSING"}]
    if not failed:
        return

    print()
    print("FAILED CHECKS")
    print("-" * 104)
    for r in failed:
        print(
            f"{r['symbol']} | {r['label']} | {r['status']} | "
            f"age={fmt_age(r['age_minutes'])} min | "
            f"latest_ts={fmt_dt(r['latest_ts'])}"
        )


def print_stack_alignment(all_results: List[Dict[str, Any]]) -> None:
    print()
    print_section_header("STACK ALIGNMENT NOTES")

    by_symbol: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in all_results:
        by_symbol.setdefault(row["symbol"], {})[row["label"]] = row

    for symbol in SYMBOLS:
        items = by_symbol.get(symbol, {})
        spot = items.get("spot")
        futures = items.get("futures")
        volatility = items.get("volatility")
        market_state = items.get("market_state")
        signal_state = items.get("signal_state")
        shadow_state_signal = items.get("shadow_state_signal")
        shadow_state_outcome = items.get("shadow_state_outcome")

        print(f"{symbol}:")

        if spot and futures and spot["latest_ts"] and futures["latest_ts"]:
            diff = abs((spot["latest_ts"] - futures["latest_ts"]).total_seconds()) / 60.0
            print(f"  spot_vs_futures_gap_min: {diff:.2f}")
        else:
            print("  spot_vs_futures_gap_min: -")

        if spot and market_state and spot["latest_ts"] and market_state["latest_ts"]:
            diff = abs((spot["latest_ts"] - market_state["latest_ts"]).total_seconds()) / 60.0
            print(f"  spot_vs_market_state_gap_min: {diff:.2f}")
        else:
            print("  spot_vs_market_state_gap_min: -")

        if market_state and signal_state and market_state["latest_ts"] and signal_state["latest_ts"]:
            diff = abs((market_state["latest_ts"] - signal_state["latest_ts"]).total_seconds()) / 60.0
            print(f"  market_state_vs_signal_state_gap_min: {diff:.2f}")
        else:
            print("  market_state_vs_signal_state_gap_min: -")

        if signal_state and shadow_state_signal and signal_state["latest_ts"] and shadow_state_signal["latest_ts"]:
            diff = abs((signal_state["latest_ts"] - shadow_state_signal["latest_ts"]).total_seconds()) / 60.0
            print(f"  signal_state_vs_shadow_signal_gap_min: {diff:.2f}")
        else:
            print("  signal_state_vs_shadow_signal_gap_min: -")

        if shadow_state_signal and shadow_state_outcome and shadow_state_signal["latest_ts"] and shadow_state_outcome["latest_ts"]:
            diff = abs((shadow_state_signal["latest_ts"] - shadow_state_outcome["latest_ts"]).total_seconds()) / 60.0
            print(f"  shadow_signal_vs_shadow_outcome_gap_min: {diff:.2f}")
        else:
            print("  shadow_signal_vs_shadow_outcome_gap_min: -")

        print()


def main() -> None:
    sb = SupabaseClient()

    now_utc = utc_now()
    now_ist = ist_now()
    market_phase = get_market_phase(now_ist)

    if market_phase == "LIVE":
        baseline_close = today_close_utc(now_ist)
    else:
        baseline_close = previous_trading_close_utc(now_ist)

    print_section_header("MERDIAN - LOCAL HEALTH CHECK")
    print(f"UTC now:                  {now_utc.isoformat()}")
    print(f"IST now:                  {now_ist.isoformat()}")
    print(f"Market phase:             {market_phase}")
    print(f"Baseline close UTC:       {baseline_close.isoformat()}")
    print()

    all_results: List[Dict[str, Any]] = []

    for symbol in SYMBOLS:
        symbol_results: List[Dict[str, Any]] = []

        for check in CHECKS:
            result = evaluate_check(
                sb=sb,
                symbol=symbol,
                check=check,
                market_phase=market_phase,
                baseline_close_utc=baseline_close,
            )
            symbol_results.append(result)
            all_results.append(result)

        print_symbol_block(symbol, symbol_results)

    verdict, bad_count, missing_count = overall_verdict(all_results, market_phase)

    print_section_header("OVERALL VERDICT")
    print(f"VERDICT:                  {verdict}")
    print(f"BAD CHECKS:               {bad_count}")
    print(f"MISSING CHECKS:           {missing_count}")

    print_failed_checks(all_results)
    print_stack_alignment(all_results)


if __name__ == "__main__":
    main()