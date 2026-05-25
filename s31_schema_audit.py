"""
s31_schema_audit.py — Step 1 of 14-month feature reconstruction.

For each candidate feature table, reports:
  - date range (min/max of timestamp column)
  - total row count
  - per-column NULL rate on a 200-row sample
  - coverage verdict (FULL / PARTIAL / RECENT_ONLY)

The goal: know which tables actually have 14 months of usable data
before designing the research dataset.

Usage:
    python s31_schema_audit.py
    python s31_schema_audit.py --tables hist_spot_bars_1m,gamma_metrics
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client


IST = timezone(timedelta(hours=5, minutes=30))
_MS_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")
SAMPLE_SIZE = 200
TARGET_MONTHS = 14


load_dotenv()
SB = create_client(
    os.getenv("SUPABASE_URL").strip(),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip(),
)


# ── Tables to audit ───────────────────────────────────────────────────
# Each entry: (table_name, candidate timestamp columns in priority order,
#              key feature columns to check NULL rate on)

TABLES = [
    # Spot history — foundational
    ("hist_spot_bars_1m",
     ["bar_ts", "trade_date"],
     ["open", "high", "low", "close", "instrument_id"]),
    ("hist_spot_bars_5m",
     ["bar_ts", "trade_date"],
     ["open", "high", "low", "close", "instrument_id"]),

    # Pattern detection (original experiment cohort)
    ("hist_pattern_signals",
     ["signal_ts", "ts", "bar_ts", "trade_date"],
     ["symbol", "pattern_type", "ret_30m", "tier", "mtf_context"]),

    # HTF zones (historical + live)
    ("hist_ict_htf_zones",
     ["valid_from", "trade_date", "created_at"],
     ["symbol", "pattern_type", "timeframe", "zone_low", "zone_high"]),
    ("ict_htf_zones",
     ["valid_from", "trade_date", "created_at"],
     ["symbol", "pattern_type", "timeframe", "zone_low", "zone_high",
      "valid_to", "status"]),

    # Intraday zones (live)
    ("ict_zones",
     ["detected_at_ts", "trade_date", "created_at"],
     ["symbol", "pattern_type", "direction", "zone_low", "zone_high",
      "ict_tier", "status"]),

    # Option price history
    ("hist_option_bars_1m",
     ["bar_ts", "trade_date"],
     ["open", "high", "low", "close", "instrument_id"]),

    # Greeks
    ("gamma_metrics",
     ["ts", "created_at"],
     ["symbol", "net_gex", "gamma_concentration", "flip_level",
      "flip_distance", "gamma_regime", "straddle_atm", "straddle_slope"]),

    # Volatility
    ("volatility_snapshots",
     ["ts", "created_at"],
     ["symbol", "atm_strike", "atm_call_iv", "atm_put_iv", "atm_iv_avg",
      "iv_skew", "india_vix", "vix_change", "vix_regime"]),

    # Options flow
    ("options_flow_snapshots",
     ["ts", "created_at"],
     ["symbol", "pcr_regime", "skew_regime", "flow_regime",
      "put_call_ratio", "chain_iv_skew",
      "ce_vol_oi_ratio", "pe_vol_oi_ratio"]),

    # Wider breadth
    ("wcb_snapshots",
     ["ts", "created_at"],
     ["symbol", "wcb_regime", "wcb_score", "wcb_alignment",
      "wcb_weight_coverage_pct"]),

    # Momentum
    ("momentum_snapshots",
     ["ts", "created_at"],
     ["symbol", "ret_5m", "ret_15m", "ret_30m", "ret_60m", "ret_session"]),

    # Composite
    ("market_state_snapshots",
     ["ts", "created_at"],
     ["symbol", "spot", "dte", "expiry_date",
      "gamma_features", "breadth_features", "volatility_features",
      "momentum_features"]),

    # Session state
    ("po3_session_state",
     ["trade_date", "created_at"],
     ["symbol", "po3_session_bias", "session_open"]),
    ("market_spot_session_markers",
     ["trade_date", "created_at"],
     ["symbol", "open_0915_ts", "open_0908_ts"]),

    # Signal output (downstream, for context not research input)
    ("signal_snapshots",
     ["ts", "created_at"],
     ["symbol", "spot", "action", "trade_allowed", "direction_bias",
      "ict_pattern", "po3_session_bias"]),
]


# ── Args ──────────────────────────────────────────────────────────────

p = argparse.ArgumentParser()
p.add_argument("--tables", help="comma-separated subset of table names")
args = p.parse_args()

if args.tables:
    requested = set(args.tables.split(","))
    TABLES = [t for t in TABLES if t[0] in requested]


# ── Helpers ───────────────────────────────────────────────────────────

def probe_columns(table):
    """Return list of column names present in this table (None if empty/missing)."""
    try:
        rows = SB.table(table).select("*").limit(1).execute().data
    except Exception as e:
        return None, str(e)
    if not rows:
        return [], None
    return list(rows[0].keys()), None


def first_present(candidates, columns):
    for c in candidates:
        if c in columns:
            return c
    return None


def fetch_min_max(table, ts_col):
    """Min and max of ts_col."""
    try:
        lo_r = (SB.table(table).select(ts_col)
                .order(ts_col, desc=False).limit(1).execute().data)
        hi_r = (SB.table(table).select(ts_col)
                .order(ts_col, desc=True).limit(1).execute().data)
    except Exception as e:
        return None, None, str(e)
    lo = lo_r[0][ts_col] if lo_r else None
    hi = hi_r[0][ts_col] if hi_r else None
    return lo, hi, None


def fetch_count(table):
    """Total row count via count='exact'. May be slow on huge tables."""
    try:
        r = SB.table(table).select("*", count="exact", head=True).execute()
        return r.count, None
    except Exception as e:
        return None, str(e)


def sample_rows(table, ts_col, n=SAMPLE_SIZE):
    """Fetch n recent rows for NULL-rate analysis."""
    try:
        rows = (SB.table(table).select("*")
                .order(ts_col, desc=True).limit(n).execute().data) or []
    except Exception as e:
        return [], str(e)
    return rows, None


def null_rates(rows, cols):
    """Compute NULL rate per column on rows."""
    if not rows:
        return {c: None for c in cols}
    n = len(rows)
    out = {}
    for c in cols:
        nulls = sum(1 for r in rows if r.get(c) is None or r.get(c) == "")
        out[c] = (nulls / n) * 100
    return out


def parse_date_loose(s):
    """Parse either an ISO timestamp or a YYYY-MM-DD date string."""
    if not s: return None
    s = str(s)
    try:
        if "T" in s or " " in s:
            s2 = s.replace(" ", "T").replace("Z", "+00:00")
            m = _MS_RE.search(s2)
            if m:
                frac, tz = m.group(1), (m.group(2) or "")
                if len(frac) != 6:
                    frac6 = frac.ljust(6, "0") if len(frac) < 6 else frac[:6]
                    s2 = _MS_RE.sub(f".{frac6}{tz}", s2)
            return datetime.fromisoformat(s2)
        return datetime.fromisoformat(s + "T00:00:00+00:00")
    except Exception:
        return None


def months_between(lo, hi):
    if lo is None or hi is None: return None
    return (hi.year - lo.year) * 12 + (hi.month - lo.month) + 1


def coverage_verdict(months, total_rows):
    if months is None or total_rows is None or total_rows == 0:
        return "EMPTY"
    if months >= TARGET_MONTHS - 1:  # 13 months counts as full
        return "FULL"
    if months >= 6:
        return "PARTIAL"
    return "RECENT_ONLY"


# ── Audit one table ──────────────────────────────────────────────────

def audit(table_name, ts_candidates, key_cols):
    print()
    print("=" * 90)
    print(f"  {table_name}")
    print("=" * 90)

    cols, err = probe_columns(table_name)
    if err:
        print(f"  ERROR probing: {err}")
        return {"table": table_name, "verdict": "ERROR", "error": err}
    if cols is None:
        print(f"  Table not found or empty.")
        return {"table": table_name, "verdict": "MISSING"}
    if not cols:
        print(f"  Table empty (no rows).")
        return {"table": table_name, "verdict": "EMPTY"}

    print(f"  Columns: {len(cols)}")
    ts_col = first_present(ts_candidates, cols)
    if ts_col is None:
        print(f"  No usable timestamp column from candidates {ts_candidates}")
        print(f"  Available columns: {cols[:20]}{' ...' if len(cols) > 20 else ''}")
        return {"table": table_name, "verdict": "NO_TS_COL", "columns": cols}
    print(f"  Using ts column: {ts_col}")

    lo, hi, err = fetch_min_max(table_name, ts_col)
    if err:
        print(f"  ERROR fetching min/max: {err}")
        return {"table": table_name, "verdict": "ERROR", "error": err}
    lo_dt = parse_date_loose(lo)
    hi_dt = parse_date_loose(hi)
    mo = months_between(lo_dt, hi_dt)
    print(f"  Date range: {str(lo_dt)[:10]} → {str(hi_dt)[:10]}  "
          f"({mo} months)")

    total, err = fetch_count(table_name)
    if err:
        print(f"  Count fetch error: {err}")
        total = None
    else:
        print(f"  Total rows: {total:>10,}")

    rows, err = sample_rows(table_name, ts_col, SAMPLE_SIZE)
    if err:
        print(f"  Sample fetch error: {err}")
    else:
        print(f"  Recent sample: {len(rows)} rows")
        if rows:
            # Filter key_cols to those present in this table
            present_keys = [c for c in key_cols if c in cols]
            missing_keys = [c for c in key_cols if c not in cols]
            if missing_keys:
                print(f"    (skipping non-existent columns: {missing_keys})")
            nr = null_rates(rows, present_keys)
            print(f"    NULL rates on recent {len(rows)}-row sample:")
            for k in present_keys:
                v = nr[k]
                flag = ""
                if v is not None and v >= 50:
                    flag = "  ⚠ MOSTLY NULL"
                elif v is not None and v >= 10:
                    flag = "  ⚠ partial"
                print(f"      {k:<30} {v:>5.1f}%  null{flag}")

    verdict = coverage_verdict(mo, total)
    print(f"  → VERDICT: {verdict}")
    return {
        "table": table_name,
        "verdict": verdict,
        "months": mo,
        "total_rows": total,
        "lo": str(lo_dt)[:10] if lo_dt else None,
        "hi": str(hi_dt)[:10] if hi_dt else None,
    }


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print("S31 SCHEMA AUDIT — Step 1 of 14-month feature reconstruction")
    print(f"Target coverage: ≥{TARGET_MONTHS} months")
    print(f"Tables to audit: {len(TABLES)}")

    results = []
    for table_name, ts_candidates, key_cols in TABLES:
        try:
            r = audit(table_name, ts_candidates, key_cols)
            results.append(r)
        except Exception as e:
            print(f"  UNHANDLED ERROR for {table_name}: {e}")
            results.append({"table": table_name, "verdict": "ERROR", "error": str(e)})

    # ── Summary ───────────────────────────────────────────────────────
    print()
    print("=" * 90)
    print("  SUMMARY")
    print("=" * 90)
    print(f"  {'Table':<30} {'Verdict':<14} {'Months':>6}  {'Rows':>10}  Range")
    print("  " + "-" * 86)
    for r in results:
        v = r["verdict"]
        mo = r.get("months")
        rows = r.get("total_rows")
        lo = r.get("lo", "")
        hi = r.get("hi", "")
        mo_s = f"{mo}" if mo is not None else "?"
        rows_s = f"{rows:,}" if rows is not None else "?"
        print(f"  {r['table']:<30} {v:<14} {mo_s:>6}  {rows_s:>10}  "
              f"{lo or '?'} → {hi or '?'}")
    print()

    # Verdict counts
    counts = Counter(r["verdict"] for r in results)
    print("  Verdict counts:")
    for v in ("FULL", "PARTIAL", "RECENT_ONLY", "EMPTY", "MISSING",
              "NO_TS_COL", "ERROR"):
        if counts.get(v):
            print(f"    {v}: {counts[v]}")
    print()

    print("  Next-step shape (decide together after reading):")
    full = [r["table"] for r in results if r["verdict"] == "FULL"]
    partial = [r["table"] for r in results if r["verdict"] == "PARTIAL"]
    skip = [r["table"] for r in results
            if r["verdict"] in ("RECENT_ONLY", "EMPTY", "MISSING", "NO_TS_COL")]
    print(f"    Reachable for 14-mo research:    {full}")
    print(f"    Usable with date filter:         {partial}")
    print(f"    Insufficient history (skip):     {skip}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
