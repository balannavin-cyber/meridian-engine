from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
TARGET_TABLE = "signal_outcome_audit_v2"


def print_banner(title: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "").strip()
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class SupabaseRestClient:
    def __init__(self) -> None:
        load_dotenv(ENV_FILE, override=True)
        self.base_url = get_env("SUPABASE_URL").rstrip("/")
        self.api_key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
            or os.getenv("SUPABASE_ANON_KEY", "").strip()
        )
        if not self.api_key:
            raise RuntimeError(
                "Missing SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY in .env"
            )

        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def select(
        self,
        table: str,
        select_cols: str = "*",
        filters: list[str] | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/{table}"
        params: dict[str, str] = {"select": select_cols}

        if filters:
            for f in filters:
                key, value = f.split("=", 1)
                params[key] = value

        if order:
            params["order"] = order

        if limit is not None:
            params["limit"] = str(limit)

        response = requests.get(url, headers=self.headers, params=params, timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Supabase SELECT failed | table={table} | "
                f"HTTP {response.status_code} | response={response.text}"
            )
        return response.json()

    def insert(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/{table}"
        headers = dict(self.headers)
        headers["Prefer"] = "return=representation"

        response = requests.post(url, headers=headers, json=rows, timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Supabase INSERT failed | table={table} | "
                f"HTTP {response.status_code} | response={response.text}"
            )
        return response.json()


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def dt_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def normalize_action(action: str | None) -> str:
    value = (action or "").strip().upper()
    if value in {"BUY_CE", "BUY_PE", "DO_NOTHING"}:
        return value
    return value or "UNKNOWN"


def direction_bias_from_action(action: str) -> str:
    if action == "BUY_CE":
        return "BULLISH"
    if action == "BUY_PE":
        return "BEARISH"
    return "NEUTRAL"


def compute_move(entry: float | None, outcome: float | None) -> float | None:
    if entry is None or outcome is None:
        return None
    return outcome - entry


def compute_return_pct(entry: float | None, outcome: float | None) -> float | None:
    if entry in (None, 0) or outcome is None:
        return None
    return ((outcome - entry) / entry) * 100.0


def label_for_action(action: str, move_points: float | None) -> str:
    if action == "DO_NOTHING":
        return "N/A"
    if move_points is None:
        return "PENDING"
    if action == "BUY_CE":
        return "WIN" if move_points > 0 else "LOSS" if move_points < 0 else "FLAT"
    if action == "BUY_PE":
        return "WIN" if move_points < 0 else "LOSS" if move_points > 0 else "FLAT"
    return "UNKNOWN"


def correct_direction(action: str, move_points: float | None) -> bool | None:
    if action == "DO_NOTHING" or move_points is None:
        return None
    if action == "BUY_CE":
        return move_points > 0
    if action == "BUY_PE":
        return move_points < 0
    return None


def get_eod_cutoff(signal_dt: datetime) -> datetime:
    return signal_dt.replace(hour=10, minute=0, second=0, microsecond=0)


def first_spot_at_or_after(
    client: SupabaseRestClient, symbol: str, target_dt: datetime
) -> tuple[datetime | None, float | None]:
    rows = client.select(
        table="market_spot_snapshots",
        select_cols="ts,spot",
        filters=[
            f"symbol=eq.{symbol}",
            f"ts=gte.{target_dt.isoformat()}",
        ],
        order="ts.asc",
        limit=1,
    )
    if not rows:
        return None, None
    row = rows[0]
    return parse_dt(row.get("ts")), to_float(row.get("spot"))


def spot_path_between(
    client: SupabaseRestClient, symbol: str, start_dt: datetime, end_dt: datetime
) -> list[dict[str, Any]]:
    return client.select(
        table="market_spot_snapshots",
        select_cols="ts,spot",
        filters=[
            f"symbol=eq.{symbol}",
            f"ts=gte.{start_dt.isoformat()}",
            f"ts=lte.{end_dt.isoformat()}",
        ],
        order="ts.asc",
        limit=5000,
    )


def compute_mfe_mae(
    action: str, entry_spot: float | None, path_rows: list[dict[str, Any]]
) -> tuple[float | None, float | None]:
    if action == "DO_NOTHING" or entry_spot is None or not path_rows:
        return None, None

    favorable_moves: list[float] = []
    adverse_moves: list[float] = []

    for row in path_rows:
        spot = to_float(row.get("spot"))
        if spot is None:
            continue

        raw_move = spot - entry_spot

        if action == "BUY_CE":
            favorable_moves.append(raw_move)
            adverse_moves.append(raw_move)
        elif action == "BUY_PE":
            favorable_moves.append(-raw_move)
            adverse_moves.append(-raw_move)

    if not favorable_moves or not adverse_moves:
        return None, None

    mfe = max(favorable_moves)
    mae = min(adverse_moves)
    return mfe, mae


def get_signal_action(signal_row: dict[str, Any]) -> str:
    candidates = [
        signal_row.get("action"),
        signal_row.get("signal_action"),
        signal_row.get("trade_signal"),
        signal_row.get("signal"),
        signal_row.get("decision"),
    ]
    for value in candidates:
        normalized = normalize_action(value)
        if normalized in {"BUY_CE", "BUY_PE", "DO_NOTHING"}:
            return normalized
    return "UNKNOWN"


def get_signal_confidence(signal_row: dict[str, Any]) -> float | None:
    candidates = [
        signal_row.get("confidence"),
        signal_row.get("confidence_score"),
        signal_row.get("composite_conviction"),
        signal_row.get("score"),
    ]
    for value in candidates:
        parsed = to_float(value)
        if parsed is not None:
            return parsed
    return None


def fetch_signals_to_audit(client: SupabaseRestClient, limit: int) -> list[dict[str, Any]]:
    existing = client.select(
        table=TARGET_TABLE,
        select_cols="signal_snapshot_id",
        order="signal_snapshot_id.desc",
        limit=100000,
    )
    existing_ids = {
        row["signal_snapshot_id"]
        for row in existing
        if row.get("signal_snapshot_id") is not None
    }

    signals = client.select(
        table="signal_snapshots",
        select_cols="*",
        order="ts.asc",
        limit=limit,
    )

    pending = []
    for row in signals:
        sid = row.get("id")
        if sid not in existing_ids:
            pending.append(row)

    return pending


def build_audit_row(client: SupabaseRestClient, signal_row: dict[str, Any]) -> dict[str, Any] | None:
    signal_id = signal_row.get("id")
    symbol = signal_row.get("symbol")
    signal_ts = parse_dt(signal_row.get("ts"))
    action = get_signal_action(signal_row)
    confidence = get_signal_confidence(signal_row)

    if signal_id is None or not symbol or signal_ts is None:
        return None

    entry_dt, entry_spot = first_spot_at_or_after(client, symbol, signal_ts)
    if entry_dt is None or entry_spot is None:
        return None

    dt15 = datetime.fromtimestamp(signal_ts.timestamp() + 15 * 60, tz=timezone.utc)
    dt30 = datetime.fromtimestamp(signal_ts.timestamp() + 30 * 60, tz=timezone.utc)
    dt60 = datetime.fromtimestamp(signal_ts.timestamp() + 60 * 60, tz=timezone.utc)
    dteod = get_eod_cutoff(signal_ts)

    h15_dt, h15_spot = first_spot_at_or_after(client, symbol, dt15)
    h30_dt, h30_spot = first_spot_at_or_after(client, symbol, dt30)
    h60_dt, h60_spot = first_spot_at_or_after(client, symbol, dt60)
    heod_dt, heod_spot = first_spot_at_or_after(client, symbol, dteod)

    move15 = compute_move(entry_spot, h15_spot)
    move30 = compute_move(entry_spot, h30_spot)
    move60 = compute_move(entry_spot, h60_spot)
    moveeod = compute_move(entry_spot, heod_spot)

    ret15 = compute_return_pct(entry_spot, h15_spot)
    ret30 = compute_return_pct(entry_spot, h30_spot)
    ret60 = compute_return_pct(entry_spot, h60_spot)
    reteod = compute_return_pct(entry_spot, heod_spot)

    path60 = spot_path_between(client, symbol, entry_dt, dt60)
    mfe60, mae60 = compute_mfe_mae(action, entry_spot, path60)

    raw = {
        "entry_spot_ts": dt_to_iso(entry_dt),
        "horizon_15m_ts": dt_to_iso(h15_dt),
        "horizon_30m_ts": dt_to_iso(h30_dt),
        "horizon_60m_ts": dt_to_iso(h60_dt),
        "horizon_eod_ts": dt_to_iso(heod_dt),
        "builder_ts_utc": utc_now_iso(),
        "source_signal_columns": sorted(list(signal_row.keys())),
    }

    return {
        "signal_snapshot_id": signal_id,
        "symbol": symbol,
        "signal_ts": signal_ts.isoformat(),
        "signal_action": action,
        "direction_bias": direction_bias_from_action(action),
        "confidence_score": confidence,
        "entry_spot": entry_spot,
        "outcome_15m_spot": h15_spot,
        "outcome_30m_spot": h30_spot,
        "outcome_60m_spot": h60_spot,
        "outcome_eod_spot": heod_spot,
        "return_15m_pct": ret15,
        "return_30m_pct": ret30,
        "return_60m_pct": ret60,
        "return_eod_pct": reteod,
        "move_15m_points": move15,
        "move_30m_points": move30,
        "move_60m_points": move60,
        "move_eod_points": moveeod,
        "mfe_points_60m": mfe60,
        "mae_points_60m": mae60,
        "correct_direction_15m": correct_direction(action, move15),
        "correct_direction_30m": correct_direction(action, move30),
        "correct_direction_60m": correct_direction(action, move60),
        "correct_direction_eod": correct_direction(action, moveeod),
        "outcome_label_15m": label_for_action(action, move15),
        "outcome_label_30m": label_for_action(action, move30),
        "outcome_label_60m": label_for_action(action, move60),
        "outcome_label_eod": label_for_action(action, moveeod),
        "evaluation_source": "market_spot_snapshots",
        "raw": raw,
    }


def main() -> None:
    print_banner("MERDIAN - Build Signal Outcome Audit V2")
    print(f"Target table: {TARGET_TABLE}")
    print(f"Started at UTC: {utc_now_iso()}")
    print("-" * 72)

    client = SupabaseRestClient()

    pending_signals = fetch_signals_to_audit(client, limit=5000)
    print(f"Pending signals to audit: {len(pending_signals)}")

    rows_to_insert: list[dict[str, Any]] = []
    skipped = 0

    for signal_row in pending_signals:
        try:
            built = build_audit_row(client, signal_row)
            if built is None:
                skipped += 1
                continue
            rows_to_insert.append(built)
        except Exception as exc:
            skipped += 1
            print(f"Skipped signal id={signal_row.get('id')} | reason={exc}")

    print(f"Rows prepared: {len(rows_to_insert)}")
    print(f"Skipped: {skipped}")
    print("-" * 72)

    if rows_to_insert:
        inserted = client.insert(TARGET_TABLE, rows_to_insert)
        print(f"Inserted rows: {len(inserted)}")
    else:
        print("No rows inserted.")

    print_banner("MERDIAN - Signal Outcome Audit V2 Completed")


if __name__ == "__main__":
    main()