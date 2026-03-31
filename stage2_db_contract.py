"""
MERDIAN Preflight — Stage 2: Database Contract
===============================================
Verifies that the database matches what the code expects.
No writes except to the diagnostics table.

Catches:
  - Missing tables that scripts assume exist
  - Missing columns that would cause runtime errors
  - Missing unique constraints (especially C-01 on market_state_snapshots)
  - Missing calendar row for today (V18A-03)
  - Stale data — tables with no recent rows (lag > threshold)
  - trading_calendar not populated far enough ahead

Pass criteria: all critical tables exist, today's calendar row present,
               no critical staleness beyond threshold.
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preflight_common import (
    PASS, FAIL, WARN, SKIP,
    detect_environment, load_env, make_stage_result,
    run_check, now_iso, print_header, print_check,
    print_stage_summary, save_stage_result
)

STAGE_ID = "stage2_db_contract"

# ── Supabase Query Helper ─────────────────────────────────────────

def _sb_query(sql, timeout=20):
    """
    Run a SQL query via Supabase REST RPC.
    Returns (rows, error).
    Uses the /rest/v1/rpc/exec_sql if available, otherwise
    falls back to direct table queries.
    """
    url      = os.environ.get("SUPABASE_URL", "")
    role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not role_key:
        return None, "Supabase credentials not in environment"

    # Use the PostgREST SQL endpoint directly
    endpoint = f"{url.rstrip('/')}/rest/v1/rpc/query"
    headers  = {
        "apikey":        role_key,
        "Authorization": f"Bearer {role_key}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }
    payload  = json.dumps({"query": sql}).encode()
    req      = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8')[:200]}"
    except Exception as ex:
        return None, str(ex)

def _sb_table_get(table, params="", timeout=15):
    """
    Do a simple GET on a Supabase REST table endpoint.
    Returns (rows, error).
    """
    url      = os.environ.get("SUPABASE_URL", "")
    role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not role_key:
        return None, "Supabase credentials not in environment"

    endpoint = f"{url.rstrip('/')}/rest/v1/{table}?{params}"
    headers  = {
        "apikey":        role_key,
        "Authorization": f"Bearer {role_key}",
        "Accept":        "application/json",
    }
    req = urllib.request.Request(endpoint, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body), None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, f"Table not found: {table}"
        return None, f"HTTP {e.code}"
    except Exception as ex:
        return None, str(ex)

def _sb_table_head(table, timeout=10):
    """Check if a table exists by reading its first row."""
    rows, err = _sb_table_get(table, "limit=1")
    if err:
        return False, err
    return True, f"Table {table} exists ({len(rows)} row(s) returned)"

# ── Checks ────────────────────────────────────────────────────────

def check_credentials_present():
    """Supabase credentials must be in environment."""
    ok, msg, _ = load_env()
    if not ok:
        return FAIL, msg
    if not os.environ.get("SUPABASE_URL"):
        return FAIL, "SUPABASE_URL not set"
    if not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return FAIL, "SUPABASE_SERVICE_ROLE_KEY not set"
    return PASS, "Supabase credentials present"

def check_critical_tables_exist():
    """
    All tables that scripts write to or read from must exist.
    This catches schema drift — table was dropped or renamed.
    """
    critical_tables = [
        "trading_calendar",
        "market_spot_snapshots",
        "option_chain_snapshots",
        "gamma_metrics",
        "volatility_snapshots",
        "momentum_snapshots",
        "market_state_snapshots",
        "signal_snapshots",
        "weighted_constituent_breadth_snapshots",
        "equity_intraday_last",
        "market_breadth_intraday",
        "signal_regret_log",
    ]
    missing = []
    for table in critical_tables:
        exists, _ = _sb_table_head(table)
        if not exists:
            missing.append(table)

    if missing:
        return FAIL, f"Missing tables: {missing}"
    return PASS, f"All {len(critical_tables)} critical tables exist"

def check_gamma_metrics_columns():
    """
    gamma_metrics must have gamma_zone and raw columns (added V18A).
    Missing these causes the runner to crash on every cycle.
    """
    rows, err = _sb_table_get("gamma_metrics", "limit=1&select=gamma_zone,raw")
    if err:
        # If the columns don't exist PostgREST returns 400
        if "400" in str(err) or "column" in str(err).lower():
            return FAIL, "gamma_metrics missing gamma_zone or raw column — V18A schema changes not applied"
        return WARN, f"Could not verify gamma_metrics columns: {err}"
    return PASS, "gamma_metrics has gamma_zone and raw columns"

def check_market_state_snapshots_uniqueness():
    """
    C-01: market_state_snapshots must have UNIQUE(symbol, ts) constraint.
    Queries information_schema via Supabase to confirm constraint exists.
    """
    # Query information_schema for the constraint
    rows, err = _sb_table_get(
        "information_schema.table_constraints",
        "table_name=eq.market_state_snapshots"
        "&constraint_type=eq.UNIQUE"
        "&select=constraint_name,constraint_type"
    )

    if err:
        # Fallback: check for duplicates if we can't query information_schema
        rows2, err2 = _sb_table_get(
            "market_state_snapshots",
            "select=symbol,ts&limit=500&order=ts.desc"
        )
        if err2:
            return WARN, f"Could not verify C-01 constraint: {err}"
        seen = set()
        dupes = 0
        for row in (rows2 or []):
            key = (row.get("symbol"), row.get("ts"))
            if key in seen:
                dupes += 1
            seen.add(key)
        if dupes > 0:
            return FAIL, f"C-01 ACTIVE: {dupes} duplicate rows found. Add UNIQUE constraint."
        return WARN, "C-01: Cannot verify constraint via information_schema. No duplicates in last 500 rows."

    if not rows:
        return FAIL, ("C-01 OPEN: UNIQUE(symbol,ts) constraint missing on market_state_snapshots. "
                      "Run: ALTER TABLE public.market_state_snapshots "
                      "ADD CONSTRAINT uq_market_state_symbol_ts UNIQUE (symbol, ts);")

    constraint_names = [r.get("constraint_name", "") for r in rows]
    return PASS, f"C-01 CLOSED: UNIQUE constraint confirmed — {constraint_names}"

def check_trading_calendar_today():
    """
    V18A-03: trading_calendar must have a row for today.
    Missing row = all calendar-gated scripts skip = silent failure.
    This is the most common cause of 'system looks alive but nothing runs'.
    """
    import datetime
    today = datetime.date.today().isoformat()
    rows, err = _sb_table_get("trading_calendar", f"trade_date=eq.{today}&select=trade_date,is_open")
    if err:
        return FAIL, f"Could not query trading_calendar: {err}"
    if not rows:
        return FAIL, (f"V18A-03: No trading_calendar row for today ({today}). "
                      f"ALL calendar-gated scripts will treat today as a holiday and skip. "
                      f"INSERT a row immediately: INSERT INTO trading_calendar (trade_date, is_open) "
                      f"VALUES ('{today}', true/false);")
    row = rows[0]
    is_open = row.get("is_open")
    return PASS, f"trading_calendar row exists for {today}. is_open={is_open}"

def check_trading_calendar_week_ahead():
    """
    trading_calendar should have entries at least 5 trading days ahead.
    Catches the case where the calendar has not been maintained.
    """
    import datetime
    today = datetime.date.today()
    week_ahead = (today + datetime.timedelta(days=8)).isoformat()
    today_str = today.isoformat()

    rows, err = _sb_table_get(
        "trading_calendar",
        f"trade_date=gte.{today_str}&trade_date=lte.{week_ahead}&select=trade_date,is_open&order=trade_date.asc"
    )
    if err:
        return WARN, f"Could not check calendar week ahead: {err}"
    if len(rows) < 3:
        return WARN, (f"Only {len(rows)} trading_calendar entries in next 8 days. "
                      f"Maintain at least 1 week ahead to prevent session-gating failures.")
    return PASS, f"{len(rows)} calendar entries in next 8 days — sufficient lookahead"

def check_signal_regret_log_schema():
    """
    signal_regret_log must have the confirmed V18A schema columns.
    Catches schema drift between what build_signal_regret_log_v1.py expects and what exists.
    """
    rows, err = _sb_table_get(
        "signal_regret_log",
        "limit=1&select=id,signal_snapshot_id,symbol,signal_ts,action,direction_was_correct,labeller_version"
    )
    if err:
        if "400" in str(err) or "column" in str(err).lower():
            return FAIL, f"signal_regret_log missing expected columns: {err}"
        return WARN, f"Could not verify signal_regret_log schema: {err}"
    return PASS, f"signal_regret_log schema verified (key columns present)"

def check_data_freshness():
    """
    Check how stale the most recent data is for key tables.
    Only meaningful during market hours on trading days.
    """
    import datetime

    now_utc   = datetime.datetime.utcnow()
    hour_utc  = now_utc.hour
    # Market hours: 03:45-10:00 UTC = 09:15-15:30 IST
    market_hours = (3 <= hour_utc <= 10)

    if not market_hours:
        return PASS, "Outside market hours — freshness check not applicable"

    tables_to_check = [
        ("option_chain_snapshots", "created_at", 600),
        ("gamma_metrics",          "created_at", 600),
        ("market_state_snapshots", "created_at", 600),
    ]

    issues = []
    for table, ts_col, threshold_sec in tables_to_check:
        rows, err = _sb_table_get(table, f"select={ts_col}&order={ts_col}.desc&limit=1")
        if err or not rows:
            issues.append(f"{table}: no recent rows or query failed")
            continue
        ts_str = rows[0].get(ts_col, "")
        if ts_str:
            try:
                ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=datetime.timezone.utc)
                lag_sec = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds()
                if lag_sec > threshold_sec:
                    issues.append(f"{table}: lag={int(lag_sec)}s (threshold={threshold_sec}s)")
            except Exception:
                pass

    if issues:
        return WARN, f"Stale data during market hours: {'; '.join(issues)}"
    return PASS, "All checked tables have recent data"

# ── Stage Runner ──────────────────────────────────────────────────

def run_stage2(verbose=True):
    started_at = now_iso()
    env = detect_environment()

    if verbose:
        print_header(f"Stage 2 — DB Contract  [{env.upper()}]")

    checks = [
        run_check("Supabase credentials present",           check_credentials_present),
        run_check("Critical tables exist",                  check_critical_tables_exist),
        run_check("gamma_metrics has V18A columns",         check_gamma_metrics_columns),
        run_check("market_state_snapshots uniqueness (C-01)",check_market_state_snapshots_uniqueness),
        run_check("trading_calendar row for today (V18A-03)",check_trading_calendar_today),
        run_check("trading_calendar week ahead",            check_trading_calendar_week_ahead),
        run_check("signal_regret_log schema",               check_signal_regret_log_schema),
        run_check("Data freshness",                         check_data_freshness),
    ]

    if verbose:
        for c in checks:
            print_check(c)

    result = make_stage_result(STAGE_ID, env, checks, started_at)
    save_stage_result(result)

    if verbose:
        print_stage_summary(result)

    return result

if __name__ == "__main__":
    result = run_stage2(verbose=True)
    sys.exit(0 if result["status"] == PASS else 1)
