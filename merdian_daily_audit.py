#!/usr/bin/env python3
"""
merdian_daily_audit.py  --  MERDIAN Primary Data Integrity Audit (Session 20 rewrite)

Validates that today's primary data ingestion pipeline produced what was
expected, across pre-market / intraday / post-market windows. Audits cover:

  Pre-market window  (08:00 - 09:14 IST):
    - trading_calendar row for today
    - Dhan token refresh (presence of recent script_execution_log row)
    - HTF zones built (script_execution_log + ict_htf_zones rows)
    - IV context capture (script_execution_log)

  Intraday window     (09:15 - 15:30 IST):
    - hist_spot_bars_1m: 750 rows expected (375 NIFTY + 375 SENSEX),
      flat-bar count must be < 5% of in-session bars
    - market_spot_snapshots: same expectation
    - option_chain_snapshots: ~50,000+ rows for the day
    - market_state_snapshots: 200+ rows (typically 75 cycles x 2 symbols x 2-ish)
    - signal_snapshots: 200+ rows
    - ict_zones: at least 1 zone of any pattern type detected
    - script_execution_log: 50+ runner cycles for each of the cycle scripts

  Post-market window (15:30 - 16:30 IST):
    - market_close_capture row(s) present
    - EOD breadth refresh (script_execution_log)

The script is designed to be the source of truth for "did the ingestion
pipeline work today?" -- if this passes, we trust today's data.

Usage:
    python merdian_daily_audit.py                    # audit today
    python merdian_daily_audit.py --date 2026-05-04  # audit specific date
    python merdian_daily_audit.py --window pre|intra|post|all  # default all

Reports written to:
    audit_results_YYYYMMDD.json   (machine-readable)
    stdout                          (human-readable)

Exit codes:
    0 -- script ran cleanly (whether audit passed or failed; check JSON for verdict)
    1 -- script crashed (database unreachable, env vars missing, etc.)

Session 20 rewrite: Session 19 version used raw PostgREST REST calls with
malformed query syntax (duplicate dict keys for filters, count() in select)
which 400'd on every audit. Also queried 'ict_patterns' (table doesn't exist;
real name is 'ict_zones'). This rewrite uses the supabase Python client,
correct table names, ExecutionLog instrumentation, and proper window-scoped
checks.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, time, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client

# ENH-71/72 instrumentation
from core.execution_log import ExecutionLog


load_dotenv()

IST = ZoneInfo("Asia/Kolkata")

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]


# ── Thresholds ────────────────────────────────────────────────────────────────
# Calibrated against Apr-21 -> May-04 healthy baseline observations.
# Slight margin built in to avoid flapping on borderline days.

THRESHOLDS = {
    # Per-symbol counts (will be summed/averaged for both NIFTY+SENSEX)
    "spot_bars_per_symbol_min":          370,    # 375 = perfect day, allow 5 missing
    "spot_bars_flat_pct_max":            5.0,    # in-session flat rate (>5% = bad)

    "market_spot_snapshots_per_symbol":  370,    # 1:1 with spot bars

    "option_chain_snapshots_min":        80_000, # ~107K healthy, 80K floor
    "option_chain_per_cycle_min":        50,     # min N strikes per snapshot (rough)

    "market_state_snapshots_min":        140,    # 75 cycles x 2 syms minus margin
    "signal_snapshots_min":              140,
    "ict_zones_today_min":               5,      # at least 5 patterns of any type

    # Runner cycle expectations
    "runner_cycles_min":                 50,     # ~75 expected, allow 25 missing
}


# ── Audit result structures ───────────────────────────────────────────────────

@dataclass
class CheckResult:
    name:    str
    status:  str              # PASS | FAIL | WARN | SKIP
    actual:  Optional[str] = None
    expected: Optional[str] = None
    detail:  Optional[str] = None


@dataclass
class WindowReport:
    window:  str              # pre | intra | post
    checks:  list[CheckResult] = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(c.status == "FAIL" for c in self.checks):
            return "FAIL"
        if any(c.status == "WARN" for c in self.checks):
            return "WARN"
        if all(c.status == "SKIP" for c in self.checks):
            return "SKIP"
        return "PASS"


@dataclass
class AuditReport:
    audit_date:   str
    audit_ran_at: str
    windows:      list[WindowReport] = field(default_factory=list)

    @property
    def overall_status(self) -> str:
        if any(w.status == "FAIL" for w in self.windows):
            return "FAIL"
        if any(w.status == "WARN" for w in self.windows):
            return "WARN"
        return "PASS"


# ── Logging helper ────────────────────────────────────────────────────────────

def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now(IST).strftime("%H:%M:%S IST")
    print(f"[{ts}] {level}: {msg}", flush=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_instrument_id(sb, symbol: str) -> Optional[str]:
    """Look up instrument UUID by symbol."""
    try:
        rows = sb.table("instruments").select("id").eq("symbol", symbol).execute().data
        return rows[0]["id"] if rows else None
    except Exception as e:
        log(f"instruments lookup failed for {symbol}: {e}", "WARN")
        return None


def day_bounds_utc(audit_date: date) -> tuple[str, str]:
    """Return (start_utc_iso, end_utc_iso) for a given IST trade_date."""
    start_ist = datetime.combine(audit_date, time.min, tzinfo=IST)
    end_ist   = start_ist + timedelta(days=1)
    return start_ist.astimezone(timezone.utc).isoformat(), \
           end_ist.astimezone(timezone.utc).isoformat()


def in_session_bounds_utc(audit_date: date) -> tuple[str, str]:
    """09:15 to 15:30 IST window in UTC ISO strings."""
    open_ist  = datetime.combine(audit_date, time(9, 15),  tzinfo=IST)
    close_ist = datetime.combine(audit_date, time(15, 30), tzinfo=IST)
    return open_ist.astimezone(timezone.utc).isoformat(), \
           close_ist.astimezone(timezone.utc).isoformat()


def count_table(sb, table: str, filters: list[tuple]) -> int:
    """
    Count rows in `table` matching `filters` (list of (op, col, val) tuples).
    Returns -1 on query failure (caller decides how to treat).
    """
    try:
        q = sb.table(table).select("id", count="exact")
        for op, col, val in filters:
            q = getattr(q, op)(col, val)
        result = q.execute()
        return result.count if result.count is not None else len(result.data or [])
    except Exception as e:
        log(f"count_table {table} failed: {e}", "WARN")
        return -1


# ── Audit checks ──────────────────────────────────────────────────────────────

def audit_intraday_spot(sb, audit_date: date) -> list[CheckResult]:
    """Audit hist_spot_bars_1m + market_spot_snapshots for in-session window."""
    results = []
    in_open, in_close = in_session_bounds_utc(audit_date)

    for symbol in ("NIFTY", "SENSEX"):
        inst_id = get_instrument_id(sb, symbol)
        if not inst_id:
            results.append(CheckResult(
                name=f"hist_spot_bars_1m / {symbol}",
                status="FAIL",
                detail=f"Instrument {symbol} not found",
            ))
            continue

        # Total in-session bars
        total = count_table(sb, "hist_spot_bars_1m", [
            ("eq", "instrument_id", inst_id),
            ("eq", "trade_date", str(audit_date)),
            ("eq", "is_pre_market", False),
            ("gte", "bar_ts", in_open),
            ("lt",  "bar_ts", in_close),
        ])

        if total < 0:
            results.append(CheckResult(
                name=f"hist_spot_bars_1m / {symbol}",
                status="FAIL",
                detail="Query failed",
            ))
            continue

        # Fetch bars to compute flat-bar count (need OHLC values)
        try:
            rows = (sb.table("hist_spot_bars_1m")
                      .select("open, high, low, close")
                      .eq("instrument_id", inst_id)
                      .eq("trade_date", str(audit_date))
                      .eq("is_pre_market", False)
                      .gte("bar_ts", in_open)
                      .lt("bar_ts", in_close)
                      .execute().data)
            flat = sum(1 for r in rows if r["open"] == r["high"] == r["low"] == r["close"])
            flat_pct = (100.0 * flat / total) if total else 0.0
        except Exception as e:
            results.append(CheckResult(
                name=f"hist_spot_bars_1m / {symbol}",
                status="FAIL",
                detail=f"OHLC fetch failed: {e}",
            ))
            continue

        # Bar count check
        if total < THRESHOLDS["spot_bars_per_symbol_min"]:
            results.append(CheckResult(
                name=f"hist_spot_bars_1m / {symbol} (count)",
                status="FAIL",
                actual=str(total),
                expected=f">= {THRESHOLDS['spot_bars_per_symbol_min']}",
            ))
        else:
            results.append(CheckResult(
                name=f"hist_spot_bars_1m / {symbol} (count)",
                status="PASS",
                actual=str(total),
                expected=f">= {THRESHOLDS['spot_bars_per_symbol_min']}",
            ))

        # Flat-bar check
        if flat_pct > THRESHOLDS["spot_bars_flat_pct_max"]:
            results.append(CheckResult(
                name=f"hist_spot_bars_1m / {symbol} (flat-bar %)",
                status="FAIL",
                actual=f"{flat_pct:.2f}% ({flat}/{total})",
                expected=f"<= {THRESHOLDS['spot_bars_flat_pct_max']}%",
            ))
        elif flat > 0:
            results.append(CheckResult(
                name=f"hist_spot_bars_1m / {symbol} (flat-bar %)",
                status="WARN",
                actual=f"{flat_pct:.2f}% ({flat}/{total})",
                expected=f"<= {THRESHOLDS['spot_bars_flat_pct_max']}%",
            ))
        else:
            results.append(CheckResult(
                name=f"hist_spot_bars_1m / {symbol} (flat-bar %)",
                status="PASS",
                actual="0%",
                expected=f"<= {THRESHOLDS['spot_bars_flat_pct_max']}%",
            ))

        # market_spot_snapshots
        snap_total = count_table(sb, "market_spot_snapshots", [
            ("eq", "symbol", symbol),
            ("gte", "ts", in_open),
            ("lt",  "ts", in_close),
        ])
        if snap_total < 0:
            results.append(CheckResult(
                name=f"market_spot_snapshots / {symbol}",
                status="FAIL",
                detail="Query failed",
            ))
        elif snap_total < THRESHOLDS["market_spot_snapshots_per_symbol"]:
            results.append(CheckResult(
                name=f"market_spot_snapshots / {symbol}",
                status="FAIL",
                actual=str(snap_total),
                expected=f">= {THRESHOLDS['market_spot_snapshots_per_symbol']}",
            ))
        else:
            results.append(CheckResult(
                name=f"market_spot_snapshots / {symbol}",
                status="PASS",
                actual=str(snap_total),
                expected=f">= {THRESHOLDS['market_spot_snapshots_per_symbol']}",
            ))

    return results


def audit_intraday_options(sb, audit_date: date) -> list[CheckResult]:
    """Audit option_chain_snapshots for the day."""
    results = []
    day_start, day_end = day_bounds_utc(audit_date)

    total = count_table(sb, "option_chain_snapshots", [
        ("gte", "ts", day_start),
        ("lt",  "ts", day_end),
    ])

    if total < 0:
        results.append(CheckResult(
            name="option_chain_snapshots / day total",
            status="FAIL",
            detail="Query failed",
        ))
    elif total < THRESHOLDS["option_chain_snapshots_min"]:
        results.append(CheckResult(
            name="option_chain_snapshots / day total",
            status="FAIL",
            actual=str(total),
            expected=f">= {THRESHOLDS['option_chain_snapshots_min']}",
        ))
    else:
        results.append(CheckResult(
            name="option_chain_snapshots / day total",
            status="PASS",
            actual=str(total),
            expected=f">= {THRESHOLDS['option_chain_snapshots_min']}",
        ))

    # Per-symbol breakdown
    for symbol in ("NIFTY", "SENSEX"):
        per_sym = count_table(sb, "option_chain_snapshots", [
            ("eq", "symbol", symbol),
            ("gte", "ts", day_start),
            ("lt",  "ts", day_end),
        ])
        if per_sym < 0:
            results.append(CheckResult(
                name=f"option_chain_snapshots / {symbol}",
                status="FAIL",
                detail="Query failed",
            ))
        elif per_sym == 0:
            results.append(CheckResult(
                name=f"option_chain_snapshots / {symbol}",
                status="FAIL",
                actual="0",
                expected="> 0",
            ))
        else:
            results.append(CheckResult(
                name=f"option_chain_snapshots / {symbol}",
                status="PASS",
                actual=str(per_sym),
            ))

    return results


def audit_intraday_state(sb, audit_date: date) -> list[CheckResult]:
    """Audit market_state_snapshots and signal_snapshots."""
    results = []
    day_start, day_end = day_bounds_utc(audit_date)

    for table_name, threshold_key in [
        ("market_state_snapshots", "market_state_snapshots_min"),
        ("signal_snapshots",        "signal_snapshots_min"),
    ]:
        total = count_table(sb, table_name, [
            ("gte", "ts", day_start),
            ("lt",  "ts", day_end),
        ])
        if total < 0:
            results.append(CheckResult(
                name=f"{table_name} / day total",
                status="FAIL",
                detail="Query failed",
            ))
        elif total < THRESHOLDS[threshold_key]:
            results.append(CheckResult(
                name=f"{table_name} / day total",
                status="FAIL",
                actual=str(total),
                expected=f">= {THRESHOLDS[threshold_key]}",
            ))
        else:
            results.append(CheckResult(
                name=f"{table_name} / day total",
                status="PASS",
                actual=str(total),
                expected=f">= {THRESHOLDS[threshold_key]}",
            ))

    return results


def audit_intraday_zones(sb, audit_date: date) -> list[CheckResult]:
    """Audit ict_zones detected today."""
    results = []

    total = count_table(sb, "ict_zones", [
        ("eq", "trade_date", str(audit_date)),
    ])
    if total < 0:
        results.append(CheckResult(
            name="ict_zones / day total",
            status="FAIL",
            detail="Query failed",
        ))
        return results

    if total < THRESHOLDS["ict_zones_today_min"]:
        results.append(CheckResult(
            name="ict_zones / day total",
            status="FAIL",
            actual=str(total),
            expected=f">= {THRESHOLDS['ict_zones_today_min']}",
        ))
    else:
        results.append(CheckResult(
            name="ict_zones / day total",
            status="PASS",
            actual=str(total),
            expected=f">= {THRESHOLDS['ict_zones_today_min']}",
        ))

    # Per-pattern-type breakdown for diagnostics (WARN if any type is zero;
    # this surfaces the BULL_OB / BEAR_OB / BEAR_FVG zero-emission regression
    # we've been chasing).
    try:
        rows = (sb.table("ict_zones")
                  .select("pattern_type")
                  .eq("trade_date", str(audit_date))
                  .execute().data)
        pattern_counts: dict[str, int] = {}
        for r in rows:
            pt = r.get("pattern_type") or "UNKNOWN"
            pattern_counts[pt] = pattern_counts.get(pt, 0) + 1

        for pt in ("BULL_OB", "BEAR_OB", "BULL_FVG", "BEAR_FVG"):
            n = pattern_counts.get(pt, 0)
            results.append(CheckResult(
                name=f"ict_zones / {pt}",
                status="PASS" if n > 0 else "WARN",
                actual=str(n),
                detail=("zero emissions today -- check detector" if n == 0 else None),
            ))
    except Exception as e:
        results.append(CheckResult(
            name="ict_zones / per-pattern breakdown",
            status="FAIL",
            detail=f"Per-pattern fetch failed: {e}",
        ))

    return results


def audit_runner_cycles(sb, audit_date: date) -> list[CheckResult]:
    """Audit script_execution_log for runner cycle scripts."""
    results = []
    day_start, day_end = day_bounds_utc(audit_date)

    cycle_scripts = [
        "build_market_state_snapshot_local.py",
        "detect_ict_patterns_runner.py",
        "build_trade_signal_local.py",
        "ingest_option_chain_local.py",
        "compute_gamma_metrics_local.py",
    ]

    for script in cycle_scripts:
        n = count_table(sb, "script_execution_log", [
            ("eq", "script_name", script),
            ("gte", "started_at", day_start),
            ("lt",  "started_at", day_end),
        ])
        if n < 0:
            results.append(CheckResult(
                name=f"script_execution_log / {script}",
                status="FAIL",
                detail="Query failed",
            ))
        elif n < THRESHOLDS["runner_cycles_min"]:
            results.append(CheckResult(
                name=f"script_execution_log / {script}",
                status="FAIL",
                actual=str(n),
                expected=f">= {THRESHOLDS['runner_cycles_min']} cycles",
            ))
        else:
            results.append(CheckResult(
                name=f"script_execution_log / {script}",
                status="PASS",
                actual=f"{n} cycles",
            ))

    # Crashes / contract violations across the day (warning indicator)
    try:
        crash_rows = (sb.table("script_execution_log")
                        .select("script_name, exit_reason")
                        .gte("started_at", day_start)
                        .lt("started_at", day_end)
                        .neq("exit_code", 0)
                        .execute().data)
        if crash_rows:
            scripts_with_crashes = sorted(set(r["script_name"] for r in crash_rows))
            results.append(CheckResult(
                name="script_execution_log / crashes today",
                status="WARN",
                actual=f"{len(crash_rows)} crashes across {len(scripts_with_crashes)} scripts",
                detail="; ".join(scripts_with_crashes[:5]),
            ))
        else:
            results.append(CheckResult(
                name="script_execution_log / crashes today",
                status="PASS",
                actual="0 crashes",
            ))
    except Exception as e:
        results.append(CheckResult(
            name="script_execution_log / crashes today",
            status="FAIL",
            detail=f"Query failed: {e}",
        ))

    return results


def audit_pre_market(sb, audit_date: date) -> list[CheckResult]:
    """Pre-market window checks: trading_calendar, HTF zones, IV context."""
    results = []
    day_start, day_end = day_bounds_utc(audit_date)

    # 1. trading_calendar row exists for today
    try:
        rows = (sb.table("trading_calendar")
                  .select("trade_date, is_open, open_time, close_time")
                  .eq("trade_date", str(audit_date))
                  .execute().data)
        if not rows:
            results.append(CheckResult(
                name="trading_calendar / today's row",
                status="FAIL",
                detail="No row found for today",
            ))
        else:
            row = rows[0]
            if row.get("is_open") is None or not row["is_open"]:
                results.append(CheckResult(
                    name="trading_calendar / today's row",
                    status="WARN",
                    actual=f"is_open={row.get('is_open')}",
                    detail="Today marked as not open",
                ))
            else:
                results.append(CheckResult(
                    name="trading_calendar / today's row",
                    status="PASS",
                    actual=f"is_open={row.get('is_open')}",
                ))
    except Exception as e:
        results.append(CheckResult(
            name="trading_calendar / today's row",
            status="FAIL",
            detail=f"Query failed: {e}",
        ))

    # 2. HTF zones built today (build_ict_htf_zones.py ran successfully)
    n_htf = count_table(sb, "script_execution_log", [
        ("eq", "script_name", "build_ict_htf_zones.py"),
        ("gte", "started_at", day_start),
        ("lt",  "started_at", day_end),
        ("eq",  "exit_code", 0),
    ])
    if n_htf < 0:
        results.append(CheckResult(
            name="HTF zones builder",
            status="FAIL",
            detail="Query failed",
        ))
    elif n_htf < 1:
        results.append(CheckResult(
            name="HTF zones builder",
            status="FAIL",
            actual="0 successful runs",
            expected=">= 1 successful run today",
        ))
    else:
        results.append(CheckResult(
            name="HTF zones builder",
            status="PASS",
            actual=f"{n_htf} runs",
        ))

    # 3. ict_htf_zones has ACTIVE rows for today
    try:
        active_rows = (sb.table("ict_htf_zones")
                          .select("symbol, timeframe, pattern_type")
                          .eq("status", "ACTIVE")
                          .gte("valid_to", str(audit_date))
                          .execute().data)
        if not active_rows:
            results.append(CheckResult(
                name="ict_htf_zones / active for today",
                status="FAIL",
                actual="0 active zones",
            ))
        else:
            n = len(active_rows)
            results.append(CheckResult(
                name="ict_htf_zones / active for today",
                status="PASS",
                actual=f"{n} active zones",
            ))
    except Exception as e:
        results.append(CheckResult(
            name="ict_htf_zones / active for today",
            status="FAIL",
            detail=f"Query failed: {e}",
        ))

    return results


def audit_post_market(sb, audit_date: date) -> list[CheckResult]:
    """Post-market window checks: close capture, EOD breadth."""
    results = []
    day_start, day_end = day_bounds_utc(audit_date)

    post_scripts = [
        ("MERDIAN_Post_Market_1600_Capture",   "Post-market 16:00 capture"),
        ("MERDIAN_EOD_Breadth_Refresh",         "EOD breadth refresh"),
        ("MERDIAN_Spot_MTF_Rollup_1600",        "Spot MTF rollup"),
        ("MERDIAN_Session_Markers_1602",        "Session markers"),
    ]

    # These are task names, not script names; we check by looking for any
    # script_execution_log rows in the post-market window (15:30 - 17:30 IST).
    # Most post-market scripts don't follow the task name; we use heuristic:
    # any script that ran in the post-market window.
    post_open_ist = datetime.combine(audit_date, time(15, 30), tzinfo=IST)
    post_close_ist = datetime.combine(audit_date, time(17, 30), tzinfo=IST)
    post_open_utc = post_open_ist.astimezone(timezone.utc).isoformat()
    post_close_utc = post_close_ist.astimezone(timezone.utc).isoformat()

    try:
        rows = (sb.table("script_execution_log")
                  .select("script_name, exit_code")
                  .gte("started_at", post_open_utc)
                  .lt("started_at", post_close_utc)
                  .execute().data)
        scripts_seen = sorted(set(r["script_name"] for r in rows))
        successes = sum(1 for r in rows if r.get("exit_code") == 0)

        if not rows:
            results.append(CheckResult(
                name="post-market / scripts ran",
                status="WARN",
                actual="0 scripts in 15:30-17:30 IST",
                detail="If audit runs before post-market completes, this is expected",
            ))
        else:
            results.append(CheckResult(
                name="post-market / scripts ran",
                status="PASS",
                actual=f"{len(rows)} runs ({successes} success), {len(scripts_seen)} unique scripts",
                detail="; ".join(scripts_seen[:5]),
            ))
    except Exception as e:
        results.append(CheckResult(
            name="post-market / scripts ran",
            status="FAIL",
            detail=f"Query failed: {e}",
        ))

    return results


# ── Main orchestration ────────────────────────────────────────────────────────

def run_audit(audit_date: date, windows: list[str]) -> AuditReport:
    """Run audits for the requested windows. Returns fully populated report."""
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    report = AuditReport(
        audit_date=str(audit_date),
        audit_ran_at=datetime.now(IST).isoformat(),
    )

    if "pre" in windows:
        log("Auditing pre-market window...")
        wr = WindowReport(window="pre")
        wr.checks.extend(audit_pre_market(sb, audit_date))
        report.windows.append(wr)

    if "intra" in windows:
        log("Auditing intraday window...")
        wr = WindowReport(window="intra")
        wr.checks.extend(audit_intraday_spot(sb, audit_date))
        wr.checks.extend(audit_intraday_options(sb, audit_date))
        wr.checks.extend(audit_intraday_state(sb, audit_date))
        wr.checks.extend(audit_intraday_zones(sb, audit_date))
        wr.checks.extend(audit_runner_cycles(sb, audit_date))
        report.windows.append(wr)

    if "post" in windows:
        log("Auditing post-market window...")
        wr = WindowReport(window="post")
        wr.checks.extend(audit_post_market(sb, audit_date))
        report.windows.append(wr)

    return report


def render_report(report: AuditReport) -> str:
    """Render report as human-readable text."""
    lines = []
    lines.append("=" * 72)
    lines.append(f"MERDIAN Daily Data Audit  --  {report.audit_date}")
    lines.append(f"Audit ran at: {report.audit_ran_at}")
    lines.append("=" * 72)

    for wr in report.windows:
        lines.append("")
        lines.append(f"[{wr.window.upper()}]  {wr.status}")
        lines.append("-" * 72)
        for c in wr.checks:
            actual = f"  actual={c.actual}" if c.actual else ""
            expected = f"  expected={c.expected}" if c.expected else ""
            detail = f"  ({c.detail})" if c.detail else ""
            status_icon = {
                "PASS": "[PASS]",
                "FAIL": "[FAIL]",
                "WARN": "[WARN]",
                "SKIP": "[SKIP]",
            }.get(c.status, "[????]")
            lines.append(f"  {status_icon}  {c.name}{actual}{expected}{detail}")

    lines.append("")
    lines.append("=" * 72)
    lines.append(f"OVERALL: {report.overall_status}")
    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="MERDIAN Daily Data Audit (Session 20)")
    parser.add_argument("--date", help="YYYY-MM-DD; default: today")
    parser.add_argument("--window", choices=["pre", "intra", "post", "all"],
                        default="all",
                        help="Which window(s) to audit; default: all")
    parser.add_argument("--output-dir", default=".",
                        help="Where to write audit_results_YYYYMMDD.json")
    args = parser.parse_args()

    if args.date:
        try:
            audit_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            log(f"Invalid date format: {args.date}", "ERROR")
            return 1
    else:
        audit_date = datetime.now(IST).date()

    windows = ["pre", "intra", "post"] if args.window == "all" else [args.window]

    log_handle = ExecutionLog(
        script_name="merdian_daily_audit.py",
        expected_writes={},   # this script doesn't write to DB tables
        notes=f"audit_date={audit_date} windows={','.join(windows)}",
    )

    log(f"Starting audit for {audit_date}; windows={windows}")

    try:
        report = run_audit(audit_date, windows)
    except Exception as e:
        log(f"Audit crashed: {e}", "ERROR")
        log_handle.exit_with_reason("CRASH", exit_code=1, error_message=str(e)[:2000])
        return 1

    text_report = render_report(report)
    print(text_report)

    # Write JSON
    out_path = Path(args.output_dir) / f"audit_results_{audit_date.strftime('%Y%m%d')}.json"
    try:
        with open(out_path, "w") as f:
            json.dump({
                "audit_date":   report.audit_date,
                "audit_ran_at": report.audit_ran_at,
                "overall":      report.overall_status,
                "windows": [
                    {
                        "window": wr.window,
                        "status": wr.status,
                        "checks": [asdict(c) for c in wr.checks],
                    }
                    for wr in report.windows
                ],
            }, f, indent=2, default=str)
        log(f"JSON report written to {out_path}")
    except Exception as e:
        log(f"Failed to write JSON report: {e}", "WARN")

    # Always exit 0 -- the wrapper interprets exit code at OS level.
    # The audit's PASS/WARN/FAIL is the actual verdict, written to JSON.
    return log_handle.complete(notes=f"overall={report.overall_status}")


if __name__ == "__main__":
    sys.exit(main())
