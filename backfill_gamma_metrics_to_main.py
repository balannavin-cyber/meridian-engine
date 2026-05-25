#!/usr/bin/env python3
"""
backfill_gamma_metrics_to_main.py — full-year backfill into gamma_metrics.

Reads vendor historical 1m option/spot bars (hist_option_bars_1m + hist_spot_bars_1m),
computes gamma_metrics fields per 5-min cycle, writes to production gamma_metrics
table. Enables Phase 0b P5 PINNED test + future gamma-context Phase 0b dimensions
(P1 LONG_GAMMA, P3 flip_distance, ENH-80 per-strike GEX precursor) on full
14-month cohort instead of 5-week live-only window.

Sources (full year coverage verified S29):
  hist_option_bars_1m   — premium close + oi + volume per (instrument, strike,
                          option_type, expiry, bar_ts). bar_ts is IST-as-UTC
                          per TD-087. oi populated 99.9% (S29 verification).
  hist_spot_bars_1m     — spot close per (instrument, bar_ts).

Target:
  gamma_metrics         — production table. Mode gap-only by default preserves
                          existing 4,694 live-writer rows; backfill fills the
                          historical gap before 2026-03-08.

Reimplemented math (NOT imported from compute_gamma_metrics_local.py because
that module reads Dhan-pre-computed gamma from option_chain_snapshots; vendor
data has no gamma column — we compute via BS from premium close → inverse-IV
→ analytical gamma):

  Per strike:
    sigma  ← inverse-BS solve on premium close (brentq, same pattern as
              vol_analytics backfill S29)
    gamma  ← Black-Scholes gamma: φ(d1) / (S · σ · √T)
    sign   ← +1 for CE, -1 for PE (ADR-002 P5 convention, D.2 VALIDATED)
    base   ← gamma · oi · spot² / 1e7  (TD-NEW-3 Cr unit; commit 241f943)
    keep   ← reject if (|K-S|/S > 5%) AND (|gamma| > 5e-5)
              (TD-NEW-2 Part A sanity guard; commit 241f943)
    signed_gex_strike ← sign · base
  Aggregate:
    net_gex            ← Σ signed_gex_strike  (Crore)
    gamma_concentration ← max(|signed_gex_strike|) / Σ |signed_gex_strike|
                            (range 0..1; higher = more concentrated at one strike)
    flip_level         ← walk outward from ATM in both directions on cumulative
                          signed_gex; return zero-crossing nearest spot
                          (TD-NEW-2 Part B walk-from-ATM)
    flip_distance_pct  ← (spot - flip_level) / spot · 100  (canonical % unit)
    regime             ← LONG_GAMMA if net_gex > 0 AND flip_level computed
                         SHORT_GAMMA if net_gex < 0 AND flip_level computed
                         NO_FLIP otherwise

Fields left NULL in backfill (computed proprietary logic in live writer; not
critical for Phase 0b consumers):
  gamma_zone, straddle_atm, straddle_slope, expansion_probability

Parity discipline:
  Live writer compute_gamma_metrics_local.py is the canonical source of truth.
  This script reimplements the math against that spec. Drift risk codified
  as TD (queued for S30+) — any future patch to live writer's signed_gamma_exposure,
  compute_flip_level, or regime classification MUST be mirrored here.

Run:
    python backfill_gamma_metrics_to_main.py --start 2025-04-01 --end 2026-03-30 \\
        [--mode gap-only|overwrite] [--symbol NIFTY|SENSEX|both] [--dry-run]
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
import traceback
from collections import defaultdict
from datetime import datetime, date, time, timezone, timedelta
from typing import Iterator, Optional

from dotenv import load_dotenv  # type: ignore
from supabase import Client, create_client  # type: ignore
from scipy.optimize import brentq  # type: ignore
from scipy.stats import norm  # type: ignore

from core.execution_log import ExecutionLog  # type: ignore


SCRIPT_NAME = "backfill_gamma_metrics_to_main.py"

RISK_FREE_RATE = 0.065

SPOT_INSTRUMENT_ID = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# Strike step + range per symbol — wide enough to capture meaningful tail OI
# without inflating query size beyond practical limits.
STRIKE_STEP = {"NIFTY": 50, "SENSEX": 100}
ATM_PLUS_MINUS = 20  # NIFTY ±1000pt, SENSEX ±2000pt

# 5-min cycle grid
SESSION_START_IST = time(9, 15)
SESSION_END_IST   = time(15, 25)
CYCLE_INTERVAL_MIN = 5
IST_TZ_OFFSET = timedelta(hours=5, minutes=30)

# TD-NEW-2 Part A sanity guard thresholds (commit 241f943)
SANITY_GUARD_STRIKE_DIST_PCT = 0.05    # 5% strike distance from spot
SANITY_GUARD_GAMMA_MAX       = 5e-5    # 5× typical ATM gamma

# IV solver bounds — same as vol_analytics backfill
IV_SIGMA_MIN = 0.001
IV_SIGMA_MAX = 5.0


# ============================================================================
# Cross-Python stdlib compat (TD-NEW-13 / B22)
# ============================================================================

_MICROSECOND_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")


def _normalize_microseconds(ts_str: str) -> str:
    m = _MICROSECOND_RE.search(ts_str)
    if m is None: return ts_str
    frac, tz = m.group(1), (m.group(2) or "")
    if len(frac) == 6: return ts_str
    frac6 = frac.ljust(6, "0") if len(frac) < 6 else frac[:6]
    return _MICROSECOND_RE.sub(f".{frac6}{tz}", ts_str)


def _ts_from_str(ts_str: str) -> datetime:
    return datetime.fromisoformat(_normalize_microseconds(ts_str.replace("Z", "+00:00")))


# ============================================================================
# Cycle grid (IST-clock-as-UTC for reads; real UTC for writes)
# ============================================================================

def _iter_5min_boundaries(trade_date: date) -> Iterator[tuple[datetime, datetime]]:
    cur_ist = datetime.combine(trade_date, SESSION_START_IST)
    end_ist = datetime.combine(trade_date, SESSION_END_IST)
    step = timedelta(minutes=CYCLE_INTERVAL_MIN)
    while cur_ist <= end_ist:
        read_ts = cur_ist.replace(tzinfo=timezone.utc)
        write_ts = (cur_ist - IST_TZ_OFFSET).replace(tzinfo=timezone.utc)
        yield (read_ts, write_ts)
        cur_ist += step


def _ist_to_utc(d: date, t: time) -> datetime:
    return (datetime.combine(d, t) - IST_TZ_OFFSET).replace(tzinfo=timezone.utc)


# ============================================================================
# Black-Scholes pricing + IV inversion + gamma
# ============================================================================

def _bs_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0: return max(S - K, 0.0)
    sqT = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqT)
    d2 = d1 - sigma * sqT
    return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def _bs_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0: return max(K - S, 0.0)
    sqT = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqT)
    d2 = d1 - sigma * sqT
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def _bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes gamma: φ(d1) / (S · σ · √T). Same for CE/PE (sign applied later)."""
    if T <= 0 or sigma <= 0 or S <= 0: return 0.0
    sqT = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqT)
    return norm.pdf(d1) / (S * sigma * sqT)


def _implied_vol(price: float, S: float, K: float, T: float, r: float, opt_type: str) -> Optional[float]:
    if T <= 0 or price <= 0: return None
    if opt_type == "CE":
        intrinsic = max(S - K * math.exp(-r * T), 0.0)
        pricer = _bs_call
    elif opt_type == "PE":
        intrinsic = max(K * math.exp(-r * T) - S, 0.0)
        pricer = _bs_put
    else:
        return None
    if price < intrinsic - 0.01: return None
    def f(sigma): return pricer(S, K, T, r, sigma) - price
    try:
        if f(IV_SIGMA_MIN) * f(IV_SIGMA_MAX) > 0: return None
        return float(brentq(f, IV_SIGMA_MIN, IV_SIGMA_MAX, xtol=1e-5, maxiter=100))
    except (ValueError, RuntimeError):
        return None


# ============================================================================
# Gamma metrics core compute (mirror of compute_gamma_metrics_local.py spec)
# ============================================================================

def _compute_signed_gex_per_strike(
    strike_rows: list[dict],
    spot: float,
) -> list[dict]:
    """
    Per-strike signed GEX with TD-NEW-2 Part A sanity guard and TD-NEW-3 /1e7 Cr.
    Input rows: [{strike, option_type, oi, premium, T}, ...]
    Output rows: [{strike, signed_gex_cr, gamma_raw, kept_or_rejected}, ...]
    """
    out = []
    for r in strike_rows:
        strike = r["strike"]; opt_type = r["option_type"]
        oi = r["oi"]; premium = r["premium"]; T = r["T"]
        if oi <= 0 or premium <= 0: continue
        sigma = _implied_vol(premium, spot, strike, T, RISK_FREE_RATE, opt_type)
        if sigma is None: continue
        gamma = _bs_gamma(spot, strike, T, RISK_FREE_RATE, sigma)
        # TD-NEW-2 Part A: reject deep-strike spurious gamma
        strike_dist_pct = abs(strike - spot) / spot
        if strike_dist_pct > SANITY_GUARD_STRIKE_DIST_PCT and abs(gamma) > SANITY_GUARD_GAMMA_MAX:
            continue
        sign = 1.0 if opt_type == "CE" else -1.0
        # TD-NEW-3: /1e7 Cr unit
        signed_gex_cr = sign * gamma * oi * (spot ** 2) / 1e7
        out.append({
            "strike": strike,
            "signed_gex_cr": signed_gex_cr,
            "abs_gex_cr": abs(signed_gex_cr),
            "gamma": gamma,
            "sigma": sigma,
            "option_type": opt_type,
            "oi": oi,
            "premium": premium,
        })
    return out


def _compute_flip_level_walk_from_atm(
    strike_gex: list[dict],
    spot: float,
) -> Optional[float]:
    """
    TD-NEW-2 Part B walk-from-ATM operational flip definition.
    Aggregate signed_gex per strike (CE + PE combined), walk outward from ATM
    in both directions on cumulative signed_gex, return zero-crossing nearest
    to spot. Returns the strike price at which cumulative GEX crosses zero,
    or None if no crossing found.
    """
    # Aggregate by strike (CE + PE combined per strike)
    by_strike: dict[float, float] = defaultdict(float)
    for r in strike_gex:
        by_strike[r["strike"]] += r["signed_gex_cr"]
    if not by_strike: return None
    strikes_sorted = sorted(by_strike.keys())
    # Find ATM index = closest strike to spot
    atm_idx = min(range(len(strikes_sorted)), key=lambda i: abs(strikes_sorted[i] - spot))
    # Cumulative GEX walk: start at ATM, walk both directions, look for sign-flip
    # in cumulative sum that crosses zero.
    # Walk UPWARD from ATM: cumulate signed_gex strike-by-strike. Note any zero-crossing.
    crossings = []
    # Upward walk
    cum = 0.0
    for i in range(atm_idx, len(strikes_sorted)):
        prev_cum = cum
        cum += by_strike[strikes_sorted[i]]
        if i > atm_idx and prev_cum * cum < 0:
            # Linear interpolation for the strike at crossing
            k_lo, k_hi = strikes_sorted[i - 1], strikes_sorted[i]
            if abs(cum - prev_cum) < 1e-9: crossing = (k_lo + k_hi) / 2
            else: crossing = k_lo - prev_cum * (k_hi - k_lo) / (cum - prev_cum)
            crossings.append(crossing)
            break
    # Downward walk
    cum = 0.0
    for i in range(atm_idx, -1, -1):
        prev_cum = cum
        cum += by_strike[strikes_sorted[i]]
        if i < atm_idx and prev_cum * cum < 0:
            k_hi, k_lo = strikes_sorted[i + 1], strikes_sorted[i]
            if abs(cum - prev_cum) < 1e-9: crossing = (k_lo + k_hi) / 2
            else: crossing = k_hi - prev_cum * (k_lo - k_hi) / (cum - prev_cum)
            crossings.append(crossing)
            break
    if not crossings: return None
    return min(crossings, key=lambda x: abs(x - spot))


def _classify_regime(net_gex: float, flip_level: Optional[float]) -> str:
    if flip_level is None: return "NO_FLIP"
    if net_gex > 0: return "LONG_GAMMA"
    if net_gex < 0: return "SHORT_GAMMA"
    return "NO_FLIP"


# ============================================================================
# Supabase I/O
# ============================================================================

def _load_supabase_client() -> Client:
    load_dotenv(override=False)
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not url or not key: raise RuntimeError("env vars required")
    return create_client(url, key)


def _fetch_day_spot_bars_1m(sb: Client, symbol: str, trade_date: date) -> dict[datetime, float]:
    """{bar_ts_ist_as_utc: spot_close}. Filtered to 5-min boundaries only.
    The 1m vendor data stamps bar_ts at HH:MM:59; we accept :59 or :00 and
    floor to :00 for key alignment. Network failures return empty dict (day
    will be skipped by caller); robust to ISP/DNS blips on multi-WAN networks."""
    instrument_id = SPOT_INSTRUMENT_ID[symbol]
    day_start = f"{trade_date.isoformat()}T09:15:00+00:00"
    day_end = f"{trade_date.isoformat()}T15:30:00+00:00"
    out: dict[datetime, float] = {}
    page_size = 1000
    offset = 0
    while True:
        try:
            resp = (sb.table("hist_spot_bars_1m")
                    .select("bar_ts, close")
                    .eq("instrument_id", instrument_id)
                    .gte("bar_ts", day_start).lte("bar_ts", day_end)
                    .range(offset, offset + page_size - 1).execute())
        except Exception as e:
            print(f"    [warn] spot fetch {trade_date} failed: {type(e).__name__}", file=sys.stderr)
            return {}
        rows = resp.data or []
        if not rows: break
        for r in rows:
            try: ts = _ts_from_str(r["bar_ts"])
            except (KeyError, ValueError): continue
            # Keep only 5-min boundary bars. The 1m vendor data stamps bar_ts
            # at the LAST second of the minute (HH:MM:59) per inspection
            # 2026-05-15; we accept both :00 and :59 to be robust to either
            # convention. Then floor to :00 for downstream key alignment.
            if ts.minute % 5 != 0 or ts.second not in (0, 59): continue
            ts = ts.replace(second=0, microsecond=0)
            if r.get("close") is None: continue
            try: out[ts] = float(r["close"])
            except (TypeError, ValueError): continue
        if len(rows) < page_size: break
        offset += page_size
    return out


def _fetch_day_option_bars_1m(
    sb: Client, symbol: str, trade_date: date,
    strike_lo: int, strike_hi: int,
) -> dict[tuple[datetime, float, str], dict]:
    """
    {(bar_ts_ist_as_utc_floored_to_5min, strike, option_type): {oi, close, expiry_date}}.

    Per-cycle exact bar_ts equality query. IN-list and BETWEEN range queries
    both time out on hist_option_bars_1m (54.8M rows) — Postgres planner falls
    back to scan when multiple bar_ts values are mixed with strike-range +
    trade_date filters (verified S29). Per-cycle .eq() lets the planner do a
    clean index seek per cycle. Cost: 75 queries per (symbol, day).

    The 1m vendor data stamps bar_ts at HH:MM:59 (last second of minute);
    timestamps emitted here use :59 to match.
    """
    grouped: dict[tuple[datetime, float, str], list[dict]] = defaultdict(list)
    cur = datetime.combine(trade_date, SESSION_START_IST)
    end = datetime.combine(trade_date, SESSION_END_IST)
    while cur <= end:
        boundary_ts = cur.replace(second=59, tzinfo=timezone.utc).isoformat()
        try:
            resp = (sb.table("hist_option_bars_1m")
                    .select("bar_ts, strike, option_type, close, oi, expiry_date")
                    .eq("trade_date", trade_date.isoformat())
                    .eq("bar_ts", boundary_ts)
                    .gte("strike", strike_lo).lte("strike", strike_hi)
                    .execute())
        except Exception as e:
            # Statement timeout on a single cycle: skip that cycle, continue.
            print(f"    [warn] cycle {boundary_ts} fetch failed: {type(e).__name__}", file=sys.stderr)
            cur += timedelta(minutes=CYCLE_INTERVAL_MIN)
            continue
        rows = resp.data or []
        for r in rows:
            try: ts = _ts_from_str(r["bar_ts"])
            except (KeyError, ValueError): continue
            ts = ts.replace(second=0, microsecond=0)
            try:
                strike = float(r["strike"])
                ot = r["option_type"]
                if ot not in ("CE", "PE"): continue
            except (KeyError, ValueError, TypeError): continue
            grouped[(ts, strike, ot)].append(r)
        cur += timedelta(minutes=CYCLE_INTERVAL_MIN)

    # Pick current-week expiry per key
    out: dict[tuple[datetime, float, str], dict] = {}
    for key, candidates in grouped.items():
        eligible = []
        for c in candidates:
            try:
                exp = date.fromisoformat(str(c["expiry_date"]))
            except (KeyError, ValueError, TypeError): continue
            if exp >= trade_date: eligible.append((exp, c))
        if not eligible: continue
        eligible.sort(key=lambda x: x[0])
        chosen = eligible[0][1]
        if chosen.get("close") is None or chosen.get("oi") is None: continue
        try:
            out[key] = {
                "premium": float(chosen["close"]),
                "oi": int(chosen["oi"]),
                "expiry_date": date.fromisoformat(str(chosen["expiry_date"])),
            }
        except (TypeError, ValueError, KeyError):
            continue
    return out


def _fetch_existing_gamma_metrics_keys(sb: Client, start_utc: datetime, end_utc: datetime) -> set[tuple[str, str]]:
    existing: set[tuple[str, str]] = set()
    page_size = 1000; offset = 0
    while True:
        resp = (sb.table("gamma_metrics").select("symbol, ts")
                .gte("ts", start_utc.isoformat()).lte("ts", end_utc.isoformat())
                .range(offset, offset + page_size - 1).execute())
        rows = resp.data or []
        if not rows: break
        for r in rows:
            existing.add((r["symbol"], r["ts"]))
        if len(rows) < page_size: break
        offset += page_size
    return existing


def _batch_upsert_gamma_metrics(sb: Client, payloads: list[dict]) -> int:
    if not payloads: return 0
    resp = (sb.table("gamma_metrics")
            .upsert(payloads, on_conflict="symbol,ts").execute())
    return len(resp.data or [])


# ============================================================================
# Per-day processing
# ============================================================================

def _process_day(
    sb: Client, symbol: str, trade_date: date,
    mode: str, dry_run: bool,
    existing_keys: set[tuple[str, str]],
) -> dict:
    counters = {
        "cycles": 0, "written": 0, "skipped_existing": 0,
        "skipped_no_spot": 0, "skipped_no_options": 0,
        "skipped_compute_failed": 0,
    }
    spot_bars = _fetch_day_spot_bars_1m(sb, symbol, trade_date)
    if not spot_bars:
        counters["skipped_no_spot"] = 75
        return counters

    # ATM strike resolution from a midday spot reading (proxy for day-level ATM band)
    midday_key = next((k for k in sorted(spot_bars.keys()) if k.time() >= time(12, 0)),
                     sorted(spot_bars.keys())[len(spot_bars) // 2])
    midday_spot = spot_bars[midday_key]
    step = STRIKE_STEP[symbol]
    atm_mid = round(midday_spot / step) * step
    strike_lo = int(atm_mid - ATM_PLUS_MINUS * step)
    strike_hi = int(atm_mid + ATM_PLUS_MINUS * step)

    option_bars = _fetch_day_option_bars_1m(sb, symbol, trade_date, strike_lo, strike_hi)
    if not option_bars:
        counters["skipped_no_options"] = 75
        return counters

    pending_payloads: list[dict] = []
    for read_ts, write_ts in _iter_5min_boundaries(trade_date):
        counters["cycles"] += 1

        spot = spot_bars.get(read_ts)
        if spot is None:
            # Fallback to nearest within ±5 min
            for offset_min in (-1, 1, -2, 2, -5, 5):
                alt = read_ts + timedelta(minutes=offset_min)
                if alt in spot_bars: spot = spot_bars[alt]; break
        if spot is None:
            counters["skipped_no_spot"] += 1
            continue

        # Find expiry: pull from any option bar at this cycle
        cycle_strikes = [k for k in option_bars.keys() if k[0] == read_ts]
        if not cycle_strikes:
            counters["skipped_no_options"] += 1
            continue
        expiry = option_bars[cycle_strikes[0]]["expiry_date"]
        dte_days = (expiry - trade_date).days
        if dte_days < 0:
            counters["skipped_compute_failed"] += 1
            continue
        T = max(dte_days, 0.5) / 365.0

        # Build strike rows for this cycle
        strike_rows = []
        for (ts, strike, ot), v in option_bars.items():
            if ts != read_ts: continue
            strike_rows.append({
                "strike": strike, "option_type": ot,
                "oi": v["oi"], "premium": v["premium"], "T": T,
            })
        if not strike_rows:
            counters["skipped_no_options"] += 1
            continue

        # Core compute
        strike_gex = _compute_signed_gex_per_strike(strike_rows, spot)
        if not strike_gex:
            counters["skipped_compute_failed"] += 1
            continue

        net_gex = sum(r["signed_gex_cr"] for r in strike_gex)
        total_abs = sum(r["abs_gex_cr"] for r in strike_gex)
        max_abs = max(r["abs_gex_cr"] for r in strike_gex) if strike_gex else 0
        gamma_concentration = (max_abs / total_abs) if total_abs > 0 else 0.0

        flip_level = _compute_flip_level_walk_from_atm(strike_gex, spot)
        if flip_level is not None:
            flip_distance = spot - flip_level
            flip_distance_pct = flip_distance / spot * 100.0
        else:
            flip_distance = None
            flip_distance_pct = None

        regime = _classify_regime(net_gex, flip_level)

        ts_str = write_ts.isoformat()
        key = (symbol, ts_str)
        if mode == "gap-only" and key in existing_keys:
            counters["skipped_existing"] += 1
            continue

        payload = {
            "symbol": symbol,
            "ts": ts_str,
            "expiry_date": expiry.isoformat(),
            "spot": spot,
            "net_gex": net_gex,
            "gamma_concentration": gamma_concentration,
            "flip_level": flip_level,
            "flip_distance": flip_distance,
            "flip_distance_pct": flip_distance_pct,
            "regime": regime,
            "raw": {
                "backfill_session": "S29",
                "backfill_script": SCRIPT_NAME,
                "iv_method": "inverse_BS_brentq",
                "gamma_method": "analytical_BS",
                "td_new_2_part_a_applied": True,
                "td_new_2_part_b_applied": True,
                "td_new_3_cr_unit_applied": True,
                "strike_range": [strike_lo, strike_hi],
                "n_strikes_kept": len(strike_gex),
                "r": RISK_FREE_RATE,
                "dte_days": dte_days,
            },
        }

        if dry_run:
            counters["written"] += 1
            continue
        pending_payloads.append(payload)

    if pending_payloads and not dry_run:
        n = _batch_upsert_gamma_metrics(sb, pending_payloads)
        counters["written"] += n

    return counters


# ============================================================================
# Main
# ============================================================================

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Backfill gamma_metrics from hist_option_bars_1m + hist_spot_bars_1m"
    )
    p.add_argument("--start", required=True, type=date.fromisoformat)
    p.add_argument("--end", required=True, type=date.fromisoformat)
    p.add_argument("--mode", default="gap-only", choices=["gap-only", "overwrite"])
    p.add_argument("--symbol", default="both", choices=["NIFTY", "SENSEX", "both"])
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.end < args.start:
        print(f"[ERROR] --end {args.end} < --start {args.start}", file=sys.stderr)
        return 2

    symbols = ["NIFTY", "SENSEX"] if args.symbol == "both" else [args.symbol]
    sb = _load_supabase_client()
    start_utc = _ist_to_utc(args.start, SESSION_START_IST)
    end_utc = _ist_to_utc(args.end, SESSION_END_IST)
    n_days = (args.end - args.start).days + 1
    estimated = n_days * 75 * len(symbols)
    expected_writes = {} if args.dry_run else {"gamma_metrics": estimated}
    log = ExecutionLog(
        script_name=SCRIPT_NAME,
        symbol=None if len(symbols) > 1 else symbols[0],
        expected_writes=expected_writes,
    )
    try:
        existing_keys: set[tuple[str, str]] = set()
        if args.mode == "gap-only":
            print("Pre-fetching existing gamma_metrics keys for gap-only mode...")
            existing_keys = _fetch_existing_gamma_metrics_keys(sb, start_utc, end_utc)
            print(f"  → {len(existing_keys)} existing keys (will be skipped)")

        totals = {"cycles": 0, "written": 0, "skipped_existing": 0,
                  "skipped_no_spot": 0, "skipped_no_options": 0,
                  "skipped_compute_failed": 0}
        current = args.start
        day_count = 0
        # Rotate Supabase client every CLIENT_ROTATE_DAYS to avoid HTTP/2
        # stream limit (~20K per connection). Per-cycle bar_ts queries ≈
        # 150 queries per day across both symbols; 10 days = ~1,500 queries
        # comfortably under cap.
        CLIENT_ROTATE_DAYS = 10
        days_since_rotate = 0
        while current <= args.end:
            if current.weekday() < 5:
                for sym in symbols:
                    counters = _process_day(sb, sym, current, args.mode, args.dry_run, existing_keys)
                    for k in totals: totals[k] += counters[k]
                    if not args.dry_run and counters["written"] > 0:
                        log.record_write("gamma_metrics", counters["written"])
                day_count += 1
                days_since_rotate += 1
                if day_count % 20 == 0:
                    print(f"  Progress: {current.isoformat()} | totals written={totals['written']}")
                if days_since_rotate >= CLIENT_ROTATE_DAYS:
                    sb = _load_supabase_client()
                    days_since_rotate = 0
            current += timedelta(days=1)

        notes = (f"mode={args.mode} symbols={','.join(symbols)} "
                 f"range={args.start}..{args.end} cycles={totals['cycles']} "
                 f"written={totals['written']} skipped_existing={totals['skipped_existing']} "
                 f"skipped_no_spot={totals['skipped_no_spot']} "
                 f"skipped_no_options={totals['skipped_no_options']} "
                 f"skipped_compute_failed={totals['skipped_compute_failed']}")
        if args.dry_run:
            log.exit_with_reason("DRY_RUN", exit_code=0, notes=notes)
        else:
            log.complete(notes=notes)
        print(notes)
        return 0
    except Exception:
        tb = traceback.format_exc()
        log.exit_with_reason("CRASH", exit_code=2, notes=f"unhandled in {SCRIPT_NAME}", error_message=tb[:4000])
        print(tb, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
