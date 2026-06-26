#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compute_structural_divergence_local.py  --  ENH-SDM P2 writer

Structural Divergence Monitor (ENH-SDM). OBSERVABILITY-FIRST / display-not-gate
(S37 doctrine): emits a per-symbol snapshot of gamma-centric structural primitives;
NOTHING routes on it. Signal/modes are gated on the forward cohort reaching usable N
(S58). `divergence_mode` is therefore held at "OBSERVE" here -- emitting a tradeable
mode pre-cohort would violate display-not-gate.

Reads gamma_metrics (latest + prior + session-open) for one symbol, computes the
CASE-2026-06-02 primitives, writes one row to structural_divergence_snapshots
(UPSERT on symbol,ts; ts aligned 1:1 with the gamma row).

Primitives & columns (sourced to CASE-2026-06-02):
  pin_risk_rate            (latest-prior) pin_risk_score normalised to per-30-min.
                           Case: >10 / 30-min = rehedge cascade.
  straddle_collapse_pct    collapse from the SESSION-OPEN straddle (cumulative-from-
                           anchor, per case -30%@10:30 / -82%@close semantics) --
                           NOT latest-vs-prior (that is gamma_metrics.straddle_velocity).
  gamma_concentration_delta latest - prior. Case: >0.5 localized, >0.6 high.
  regime_flip              "{prior}->{latest}" when regime changed this tick, else "NONE".
  three_wick_reversal      NULL -- DEFERRED to P3 (needs spot OHLC candles; outside the
                           P2 data scope of gamma_metrics latest+prior+spot).

Classifier fields (DERIVED definitions pending the un-committed spec -- ratify/re-map):
  phase        escalation ladder: FLIP > CASCADE > CONCENTRATED > STABLE.
  direction    dealer posture (NOT a price call, honest for display-not-gate):
               AMPLIFYING (SHORT_GAMMA) / DAMPENING (LONG_GAMMA) / TRANSITION (flip) /
               NEUTRAL (NO_FLIP / unknown).
  sdm_score    integer count of aligned conditions (0-4 now; 0-5 once three_wick lands).
               A COUNT, not a tuned weight -- deliberately honest for a monitor.
  divergence_mode  held "OBSERVE" at P2.

Governance: ADR-018 D2 recency-floor on the gamma read (self-flags STALE via
source_stale_floored rather than serving stale silently). ADR-006: AWS
orchestrator-integrated (called after market_state). ADR-008 _replay mirror exists.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from core.execution_log import ExecutionLog

IST = timezone(timedelta(hours=5, minutes=30))
BUILDER_VERSION = "ENH_SDM_P2_V1"

# CASE-2026-06-02 thresholds (documented; used for phase + sdm_score only)
PIN_RATE_CASCADE = 10.0     # pin_risk_rate > 10 per 30-min = rehedge cascade
GAMMA_CONC_LOCALIZED = 0.5  # > 0.5 localized supply
STRADDLE_COLLAPSE_SETUP = 25.0  # collapse % from open; > 25 = setup


def load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class SupabaseRestClient:
    def __init__(self, url: str, service_role_key: str) -> None:
        self.base_url = url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def select(
        self,
        table: str,
        filters: Optional[Dict[str, str]] = None,
        order: str = "ts.desc",
        limit: int = 1,
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{table}"
        params: Dict[str, str] = {"select": "*", "order": order, "limit": str(limit)}
        if filters:
            params.update(filters)
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected response for table={table}: {data}")
        return data

    def upsert(self, table: str, payload: Dict[str, Any], on_conflict: str) -> Dict[str, Any]:
        url = f"{self.base_url}/{table}"
        headers = dict(self.headers)
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        response = requests.post(
            f"{url}?on_conflict={on_conflict}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json()
        return rows[0] if rows else {}


def first_row_or_none(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return rows[0] if rows else None


def recency_stale(row: Optional[Dict[str, Any]], floor_env_var: str,
                  default_floor_min: float) -> bool:
    """ADR-018 D2 / TD-S57-NEW-2: is the latest row older than the recency floor?
    Mirrors build_market_state_snapshot_local._apply_recency_floor's age test, but
    for a display-not-gate monitor we FLAG staleness (source_stale_floored) rather
    than nulling the row -- the snapshot is still emitted, explicitly marked stale,
    so a silently-stopped upstream self-flags instead of serving a stale value
    indefinitely. Unparseable/absent ts -> not flagged (cannot age-check)."""
    if not row:
        return False
    row_ts = parse_ts(row.get("ts"))
    if row_ts is None:
        return False
    try:
        floor_min = float(os.getenv(floor_env_var, str(default_floor_min)))
    except ValueError:
        floor_min = float(default_floor_min)
    age_min = (datetime.now(timezone.utc) - row_ts).total_seconds() / 60.0
    if age_min > floor_min:
        print("[recency-floor] STALE gamma_metrics: latest row age %.1fmin > floor %.0fmin"
              % (age_min, floor_min), file=sys.stderr, flush=True)
        return True
    return False


def session_open_straddle(client: SupabaseRestClient, symbol: str,
                          latest_ts: datetime) -> Optional[float]:
    """First gamma_metrics row of the latest row's IST session day -> its straddle_atm.
    Anchor for cumulative straddle_collapse_pct."""
    ist_day = latest_ts.astimezone(IST).date()
    day_start_ist = datetime(ist_day.year, ist_day.month, ist_day.day, 0, 0, 0, tzinfo=IST)
    day_start_utc = day_start_ist.astimezone(timezone.utc).isoformat()
    try:
        rows = client.select(
            "gamma_metrics",
            filters={"symbol": f"eq.{symbol}", "ts": f"gte.{day_start_utc}"},
            order="ts.asc",
            limit=1,
        )
    except Exception:
        return None
    row = first_row_or_none(rows)
    return to_float(row.get("straddle_atm")) if row else None


def classify_phase(pin_rate: Optional[float], gamma_conc: Optional[float],
                   regime_flip: str) -> str:
    if regime_flip and regime_flip != "NONE":
        return "FLIP"
    if pin_rate is not None and pin_rate > PIN_RATE_CASCADE:
        return "CASCADE"
    if gamma_conc is not None and gamma_conc > GAMMA_CONC_LOCALIZED:
        return "CONCENTRATED"
    return "STABLE"


def classify_direction(regime_now: Optional[str], regime_flip: str) -> str:
    if regime_flip and regime_flip != "NONE":
        return "TRANSITION"
    if not regime_now:
        return "NEUTRAL"
    r = regime_now.upper()
    if "SHORT" in r:
        return "AMPLIFYING"
    if "LONG" in r:
        return "DAMPENING"
    return "NEUTRAL"


def compute_sdm_score(pin_rate: Optional[float], gamma_conc: Optional[float],
                      collapse_pct: Optional[float], regime_flip: str) -> int:
    score = 0
    if pin_rate is not None and pin_rate > PIN_RATE_CASCADE:
        score += 1
    if gamma_conc is not None and gamma_conc > GAMMA_CONC_LOCALIZED:
        score += 1
    if collapse_pct is not None and collapse_pct > STRADDLE_COLLAPSE_SETUP:
        score += 1
    if regime_flip and regime_flip != "NONE":
        score += 1
    return score


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ENH-SDM structural divergence writer")
    ap.add_argument("symbol", help="NIFTY | SENSEX")
    return ap.parse_args()


def main() -> int:
    load_environment()
    args = parse_args()
    symbol = args.symbol.strip().upper()

    log = ExecutionLog(
        script_name="compute_structural_divergence_local.py",
        expected_writes={"structural_divergence_snapshots": 1},
        symbol=symbol,
        notes="ENH-SDM gamma-centric observability; display-not-gate",
    )

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )
    if not supabase_url:
        return log.exit_with_reason("DEPENDENCY_MISSING", exit_code=1,
                                    error_message="SUPABASE_URL missing from environment")
    if not supabase_key:
        return log.exit_with_reason("DEPENDENCY_MISSING", exit_code=1,
                                    error_message="SUPABASE service key missing from environment")

    try:
        client = SupabaseRestClient(supabase_url, supabase_key)
    except Exception as e:
        return log.exit_with_reason("DEPENDENCY_MISSING", exit_code=1,
                                    error_message=f"SupabaseRestClient init failed: {e}")

    # gamma_metrics is the REQUIRED upstream: latest + prior in one read.
    try:
        gamma_rows = client.select(
            "gamma_metrics",
            filters={"symbol": f"eq.{symbol}"},
            order="ts.desc",
            limit=2,
        )
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=f"gamma_metrics fetch failed: {e}")

    latest = first_row_or_none(gamma_rows)
    if not latest:
        return log.exit_with_reason(
            "SKIPPED_NO_INPUT", exit_code=1,
            error_message=f"No gamma_metrics row for {symbol}. "
                          "Upstream compute_gamma_metrics has not produced output.")
    prior = gamma_rows[1] if len(gamma_rows) > 1 else None

    latest_ts = parse_ts(latest.get("ts"))
    prior_ts = parse_ts(prior.get("ts")) if prior else None

    # ADR-018 D2: flag (do not null) a stale gamma read.
    source_stale_floored = recency_stale(latest, "MERDIAN_SDM_RECENCY_FLOOR_MIN", 15)

    # ---- primitives ----------------------------------------------------------
    pin_now = to_float(latest.get("pin_risk_score"))
    pin_prior = to_float(prior.get("pin_risk_score")) if prior else None
    pin_risk_rate = None
    if pin_now is not None and pin_prior is not None and latest_ts and prior_ts:
        gap_min = (latest_ts - prior_ts).total_seconds() / 60.0
        if gap_min > 0:
            pin_risk_rate = (pin_now - pin_prior) / gap_min * 30.0  # per-30-min

    conc_now = to_float(latest.get("gamma_concentration"))
    conc_prior = to_float(prior.get("gamma_concentration")) if prior else None
    gamma_concentration_delta = (
        conc_now - conc_prior if conc_now is not None and conc_prior is not None else None
    )

    straddle_now = to_float(latest.get("straddle_atm"))
    straddle_open = session_open_straddle(client, symbol, latest_ts) if latest_ts else None
    straddle_collapse_pct = None
    if straddle_open is not None and straddle_open > 0 and straddle_now is not None:
        straddle_collapse_pct = (straddle_open - straddle_now) / straddle_open * 100.0

    regime_now = latest.get("regime")
    regime_prior = prior.get("regime") if prior else None
    if prior and regime_now and regime_prior and regime_now != regime_prior:
        regime_flip = f"{regime_prior}->{regime_now}"
    else:
        regime_flip = "NONE"

    phase = classify_phase(pin_risk_rate, conc_now, regime_flip)
    direction = classify_direction(regime_now, regime_flip)
    sdm_score = compute_sdm_score(pin_risk_rate, conc_now, straddle_collapse_pct, regime_flip)

    payload = {
        "ts": latest.get("ts"),
        "symbol": symbol,
        "run_id": latest.get("run_id"),
        "expiry_date": latest.get("expiry_date"),
        "dte": latest.get("dte"),
        "spot": to_float(latest.get("spot")),
        "pin_risk_score": pin_now,
        "pin_risk_rate": pin_risk_rate,
        "straddle_atm": straddle_now,
        "straddle_collapse_pct": straddle_collapse_pct,
        "gamma_concentration": conc_now,
        "gamma_concentration_delta": gamma_concentration_delta,
        "net_gex": to_float(latest.get("net_gex")),
        "regime": regime_now,
        "regime_flip": regime_flip,
        "three_wick_reversal": None,   # DEFERRED P3 -- needs spot OHLC
        "phase": phase,
        "direction": direction,
        "divergence_mode": "OBSERVE",  # display-not-gate; modes gated on forward N
        "sdm_score": sdm_score,
        "source_stale_floored": source_stale_floored,
        "raw": {
            "builder": "compute_structural_divergence_local.py",
            "builder_version": BUILDER_VERSION,
            "gamma_source_table": "gamma_metrics",
            "gamma_latest_ts": latest.get("ts"),
            "gamma_prior_ts": prior.get("ts") if prior else None,
            "gamma_run_id": latest.get("run_id"),
            "pin_rate_gap_min": (
                (latest_ts - prior_ts).total_seconds() / 60.0
                if latest_ts and prior_ts else None
            ),
            "straddle_open_anchor": straddle_open,
            "thresholds": {
                "pin_rate_cascade": PIN_RATE_CASCADE,
                "gamma_conc_localized": GAMMA_CONC_LOCALIZED,
                "straddle_collapse_setup": STRADDLE_COLLAPSE_SETUP,
            },
            "three_wick_status": "DEFERRED_P3_needs_OHLC",
            "display_not_gate": True,
            "source_stale_floored": source_stale_floored,
            "built_at_utc": utc_now_iso(),
        },
    }

    try:
        upserted = client.upsert(
            "structural_divergence_snapshots", payload, on_conflict="symbol,ts")
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=f"structural_divergence_snapshots upsert failed: {e}")

    log.record_write("structural_divergence_snapshots", 1)

    print("=" * 72)
    print("MERDIAN - compute_structural_divergence (ENH-SDM P2, display-not-gate)")
    print("=" * 72)
    print(f"Symbol:                {symbol}")
    print(f"Snapshot TS:           {upserted.get('ts')}")
    print(f"phase / direction:     {phase} / {direction}")
    print(f"sdm_score:             {sdm_score} (of 4; +three_wick at P3)")
    print(f"pin_risk_rate /30m:    {pin_risk_rate}")
    print(f"straddle_collapse_pct: {straddle_collapse_pct}")
    print(f"gamma_conc / delta:    {conc_now} / {gamma_concentration_delta}")
    print(f"regime_flip:           {regime_flip}")
    print(f"source_stale_floored:  {source_stale_floored}")
    return log.complete()


if __name__ == "__main__":
    raise SystemExit(main())
