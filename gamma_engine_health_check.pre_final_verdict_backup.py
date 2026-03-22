from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from core.supabase_client import SupabaseClient

IST = timezone(timedelta(hours=5, minutes=30))

MAX_CYCLE_AGE_SECONDS = 420
MAX_SYMBOL_TS_GAP_SECONDS = 180
MAX_STAGE_LAG_SECONDS = 180

SESSION_START_HOUR = 9
SESSION_START_MINUTE = 15
SESSION_END_HOUR = 15
SESSION_END_MINUTE = 30

PIPELINE_TABLES = [
    "option_chain_snapshots",
    "gamma_metrics",
    "volatility_snapshots",
    "momentum_snapshots",
    "market_state_snapshots",
    "signal_snapshots",
]

PIPELINE_LABELS = {
    "option_chain_snapshots": "options",
    "gamma_metrics": "gamma",
    "volatility_snapshots": "volatility",
    "momentum_snapshots": "momentum",
    "market_state_snapshots": "market_state",
    "signal_snapshots": "signal",
}

STAGE_AGE_THRESHOLDS = {
    "option_chain_snapshots": MAX_CYCLE_AGE_SECONDS,
    "gamma_metrics": MAX_CYCLE_AGE_SECONDS,
    "volatility_snapshots": MAX_CYCLE_AGE_SECONDS,
    "momentum_snapshots": MAX_CYCLE_AGE_SECONDS,
    "market_state_snapshots": MAX_CYCLE_AGE_SECONDS,
    "signal_snapshots": MAX_CYCLE_AGE_SECONDS,
}

STATUS_RANK = {
    "OK": 0,
    "STALE": 1,
    "MISSING": 2,
    "UNKNOWN": 3,
}


def _parse_ts(ts):
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def _format_ist(ts):
    if ts is None:
        return "None"
    return ts.astimezone(IST).strftime("%H:%M:%S IST")


def _format_age_seconds(age_seconds: Optional[float]) -> str:
    if age_seconds is None:
        return "None"
    return f"{age_seconds:.0f}s"


def _get_latest_row(sb, table, symbol):
    rows = sb.select(
        table=table,
        filters={"symbol": f"eq.{symbol}"},
        order="ts.desc",
        limit=1,
    )
    if not rows:
        return None
    return rows[0]


def _latest_stage_rows(sb, symbol: str) -> Dict[str, Optional[dict]]:
    rows: Dict[str, Optional[dict]] = {}
    for table in PIPELINE_TABLES:
        rows[table] = _get_latest_row(sb, table, symbol)
    return rows


def _extract_stage_ts_map(stage_rows: Dict[str, Optional[dict]]) -> Dict[str, Optional[datetime]]:
    out: Dict[str, Optional[datetime]] = {}
    for table, row in stage_rows.items():
        out[table] = _parse_ts(row.get("ts")) if row else None
    return out


def _age_seconds(now_utc: datetime, ts: Optional[datetime]) -> Optional[float]:
    if ts is None:
        return None
    return (now_utc - ts).total_seconds()


def _next_5min_boundary_ist(now_ist):
    floored_minute = (now_ist.minute // 5) * 5
    floored = now_ist.replace(minute=floored_minute, second=0, microsecond=0)
    if floored <= now_ist:
        floored = floored + timedelta(minutes=5)
    return floored


def _session_bounds_ist(now_ist: datetime):
    session_start = now_ist.replace(
        hour=SESSION_START_HOUR,
        minute=SESSION_START_MINUTE,
        second=0,
        microsecond=0,
    )
    session_end = now_ist.replace(
        hour=SESSION_END_HOUR,
        minute=SESSION_END_MINUTE,
        second=0,
        microsecond=0,
    )
    return session_start, session_end


def _session_mode(now_ist: datetime) -> str:
    session_start, session_end = _session_bounds_ist(now_ist)
    if now_ist < session_start:
        return "PREMARKET"
    if now_ist <= session_end:
        return "LIVE"
    return "POSTMARKET"


def _stage_status(
    now_utc: datetime,
    table: str,
    ts: Optional[datetime],
    session_mode: str,
) -> str:
    if ts is None:
        return "MISSING"

    if session_mode != "LIVE":
        return "OK"

    age = _age_seconds(now_utc, ts)
    threshold = STAGE_AGE_THRESHOLDS[table]
    if age is not None and age > threshold:
        return "STALE"

    return "OK"


def _stage_status_map(
    now_utc: datetime,
    stage_ts: Dict[str, Optional[datetime]],
    session_mode: str,
) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for table in PIPELINE_TABLES:
        out[table] = _stage_status(now_utc, table, stage_ts.get(table), session_mode)
    return out


def _pipeline_problems_for_symbol(
    now_utc: datetime,
    symbol: str,
    stage_ts: Dict[str, Optional[datetime]],
    stage_statuses: Dict[str, str],
    session_mode: str,
) -> List[str]:
    problems: List[str] = []

    for table in PIPELINE_TABLES:
        status = stage_statuses.get(table)
        if status == "MISSING":
            problems.append(f"{symbol}: missing {PIPELINE_LABELS[table]} stage")
        elif status == "STALE":
            age = _age_seconds(now_utc, stage_ts.get(table))
            if age is not None:
                problems.append(f"{symbol}: stale {PIPELINE_LABELS[table]} stage ({age:.0f}s)")

    previous_ts: Optional[datetime] = None
    previous_label: Optional[str] = None

    for table in PIPELINE_TABLES:
        current_ts = stage_ts.get(table)
        current_label = PIPELINE_LABELS[table]

        if previous_ts is not None and current_ts is not None:
            lag = abs((current_ts - previous_ts).total_seconds())
            if lag > MAX_STAGE_LAG_SECONDS:
                problems.append(
                    f"{symbol}: stage lag too large {previous_label}->{current_label} ({lag:.0f}s)"
                )

        if current_ts is not None:
            previous_ts = current_ts
            previous_label = current_label

    return problems


def _cross_symbol_problems(
    nifty_signal_ts: Optional[datetime],
    sensex_signal_ts: Optional[datetime],
    session_mode: str,
) -> List[str]:
    problems: List[str] = []

    if nifty_signal_ts is None:
        problems.append("NIFTY missing signal")
    if sensex_signal_ts is None:
        problems.append("SENSEX missing signal")

    if problems:
        return problems

    if session_mode == "LIVE":
        gap = abs((nifty_signal_ts - sensex_signal_ts).total_seconds())
        if gap > MAX_SYMBOL_TS_GAP_SECONDS:
            problems.append(f"NIFTY/SENSEX signal gap too large ({gap:.0f}s)")

    return problems


def _overall_status(all_problems: List[str], session_mode: str) -> str:
    if not all_problems:
        if session_mode == "POSTMARKET":
            return "CLOSED_OK"
        if session_mode == "PREMARKET":
            return "STANDBY"
        return "HEALTHY"

    severe = [p for p in all_problems if "missing" in p.lower()]
    if severe:
        return "DOWN"

    return "ATTENTION"


def _summary_line(symbol: str, stage_statuses: Dict[str, str], session_mode: str) -> str:
    return (
        f"{symbol:6} | "
        f"options={stage_statuses.get('option_chain_snapshots', 'UNKNOWN'):7} | "
        f"gamma={stage_statuses.get('gamma_metrics', 'UNKNOWN'):7} | "
        f"vol={stage_statuses.get('volatility_snapshots', 'UNKNOWN'):7} | "
        f"mom={stage_statuses.get('momentum_snapshots', 'UNKNOWN'):7} | "
        f"state={stage_statuses.get('market_state_snapshots', 'UNKNOWN'):7} | "
        f"signal={stage_statuses.get('signal_snapshots', 'UNKNOWN'):7} | "
        f"mode={session_mode}"
    )


def _worst_stage_status(stage_statuses: Dict[str, str]) -> str:
    worst = "OK"
    worst_rank = STATUS_RANK["OK"]

    for table in PIPELINE_TABLES:
        status = stage_statuses.get(table, "UNKNOWN")
        rank = STATUS_RANK.get(status, STATUS_RANK["UNKNOWN"])
        if rank > worst_rank:
            worst = status
            worst_rank = rank

    return worst


def _signal_gap_seconds(
    nifty_signal_ts: Optional[datetime],
    sensex_signal_ts: Optional[datetime],
) -> Optional[float]:
    if nifty_signal_ts is None or sensex_signal_ts is None:
        return None
    return abs((nifty_signal_ts - sensex_signal_ts).total_seconds())


def _last_completed_cycle_age_seconds(
    now_utc: datetime,
    nifty_signal_ts: Optional[datetime],
    sensex_signal_ts: Optional[datetime],
) -> Optional[float]:
    if nifty_signal_ts is None and sensex_signal_ts is None:
        return None

    latest_ts = None
    if nifty_signal_ts is not None and sensex_signal_ts is not None:
        latest_ts = max(nifty_signal_ts, sensex_signal_ts)
    elif nifty_signal_ts is not None:
        latest_ts = nifty_signal_ts
    else:
        latest_ts = sensex_signal_ts

    return _age_seconds(now_utc, latest_ts)


def _print_symbol_block(
    now_utc: datetime,
    symbol: str,
    stage_ts: Dict[str, Optional[datetime]],
    stage_statuses: Dict[str, str],
) -> None:
    print("-" * 72)
    print(f"{symbol} PIPELINE")
    print("-" * 72)

    for table in PIPELINE_TABLES:
        ts = stage_ts.get(table)
        age = _age_seconds(now_utc, ts)
        label = PIPELINE_LABELS[table]
        status = stage_statuses.get(table, "UNKNOWN")
        print(
            f"{label:12} status={status:>7}   ts={_format_ist(ts):>12}   age={_format_age_seconds(age):>6}"
        )


def main():
    sb = SupabaseClient()
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(IST)

    session_start_ist, session_end_ist = _session_bounds_ist(now_ist)
    session_mode = _session_mode(now_ist)

    nifty_rows = _latest_stage_rows(sb, "NIFTY")
    sensex_rows = _latest_stage_rows(sb, "SENSEX")

    nifty_ts = _extract_stage_ts_map(nifty_rows)
    sensex_ts = _extract_stage_ts_map(sensex_rows)

    nifty_stage_statuses = _stage_status_map(now_utc, nifty_ts, session_mode)
    sensex_stage_statuses = _stage_status_map(now_utc, sensex_ts, session_mode)

    nifty_problems = _pipeline_problems_for_symbol(
        now_utc, "NIFTY", nifty_ts, nifty_stage_statuses, session_mode
    )
    sensex_problems = _pipeline_problems_for_symbol(
        now_utc, "SENSEX", sensex_ts, sensex_stage_statuses, session_mode
    )
    cross_problems = _cross_symbol_problems(
        nifty_ts.get("signal_snapshots"),
        sensex_ts.get("signal_snapshots"),
        session_mode,
    )

    all_problems = nifty_problems + sensex_problems + cross_problems
    status = _overall_status(all_problems, session_mode)
    next_cycle_ist = _next_5min_boundary_ist(now_ist)

    signal_gap = _signal_gap_seconds(
        nifty_ts.get("signal_snapshots"),
        sensex_ts.get("signal_snapshots"),
    )
    last_cycle_age = _last_completed_cycle_age_seconds(
        now_utc,
        nifty_ts.get("signal_snapshots"),
        sensex_ts.get("signal_snapshots"),
    )
    worst_stage_nifty = _worst_stage_status(nifty_stage_statuses)
    worst_stage_sensex = _worst_stage_status(sensex_stage_statuses)

    print("=" * 72)
    print("GAMMA ENGINE HEALTH CHECK")
    print("=" * 72)
    print(f"Now:                 {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"Session mode:        {session_mode}")
    print(f"Session start:       {session_start_ist.strftime('%H:%M:%S IST')}")
    print(f"Session end:         {session_end_ist.strftime('%H:%M:%S IST')}")
    print(f"Overall status:      {status}")
    print(f"Next expected cycle: {next_cycle_ist.strftime('%H:%M:%S IST')}")

    print("-" * 72)
    print("Live-cycle lag summary:")
    print(f"Last completed cycle age: {_format_age_seconds(last_cycle_age)}")
    print(f"NIFTY/SENSEX signal gap:  {_format_age_seconds(signal_gap)}")
    print(f"NIFTY worst stage status: {worst_stage_nifty}")
    print(f"SENSEX worst stage status:{worst_stage_sensex}")

    print("-" * 72)
    print("Quick summary:")
    print(_summary_line("NIFTY", nifty_stage_statuses, session_mode))
    print(_summary_line("SENSEX", sensex_stage_statuses, session_mode))

    _print_symbol_block(now_utc, "NIFTY", nifty_ts, nifty_stage_statuses)
    _print_symbol_block(now_utc, "SENSEX", sensex_ts, sensex_stage_statuses)

    print("-" * 72)
    print("Pipeline order:")
    print("options -> gamma -> volatility -> momentum -> market_state -> signal")

    if all_problems:
        print("-" * 72)
        print("Notes:")
        for problem in all_problems:
            print(f"- {problem}")


if __name__ == "__main__":
    main()