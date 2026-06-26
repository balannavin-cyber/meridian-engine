#!/usr/bin/env python3
"""
eod_health_check.py  --  MERDIAN end-of-day data integrity check.

Confirms, across the board, that PRIMARY INGESTION and the COMPUTE UNIVERSE
captured cleanly for a session. Designed to be run post-close (EOD) or in-session.

Encodes the lessons from S58/S59:
  * market_ticks is a ROLLING BUFFER (last ~10 min) -- it is EMPTY post-close BY DESIGN.
    We NEVER row-count it. Tick health is INFERRED from the breadth pipeline:
    if market_breadth_intraday has a full, fresh session, ticks demonstrably flowed.
    (Querying market_ticks by row count outside the live window is a false-alarm trap.)
  * Compute tables are checked PER SYMBOL with a PARITY check (NIFTY vs SENSEX),
    because a per-symbol silent drop (one symbol stops, the other keeps writing) is
    a known failure mode (Assumption Register D.24.4).
  * Dashboard render != DB freshness. This checks the DATABASE (source of truth),
    not the Marketview cards (which can lag independently -- the WCB render bug).

Data ts is true-UTC (post-2026-04-07, CLAUDE Rule 20). Session runs ~03:00-10:00 UTC
(08:30-15:30 IST). Reads SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from .env, same
raw-HTTP pattern as ingest_option_chain_local.py.

Usage:
  python3 eod_health_check.py                 # check today's session (IST date)
  python3 eod_health_check.py --date 2026-06-23
  python3 eod_health_check.py --verbose
Exit code: 0 = all OK, 1 = one or more WARN/FAIL.
"""
import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

# ---- session window (UTC) ---------------------------------------------------
SESSION_OPEN_UTC = "03:45"     # NSE 09:15 IST
SESSION_CLOSE_UTC = "10:00"    # NSE 15:30 IST
LAST_CYCLE_OK_UTC = "09:45"    # last derived cycle should land no earlier than this

# ---- tables -----------------------------------------------------------------
# Primary ingestion (raw capture). ts column + min expected rows for a full session.
PRIMARY = [
    # (table, ts_col, min_rows, cadence_note)
    ("market_spot_snapshots",   "ts", 300, "~1/min capture"),
    ("market_breadth_intraday", "ts",  60, "~5-min cycle; ALSO the tick-health proxy"),
    ("option_chain_snapshots",  "ts", 1000, "per-strike rows, high volume"),
    ("index_futures_snapshots", "ts", 150, "~1/min capture"),
]
# Compute universe -- checked PER SYMBOL with parity.
COMPUTE = [
    ("gamma_metrics",          "ts", "symbol",       60),
    ("market_state_snapshots", "ts", "symbol",       60),
    ("volatility_snapshots",   "ts", "symbol",       60),
    ("momentum_snapshots",     "ts", "symbol",       60),
    ("signal_snapshots",       "ts", "symbol",       60),
    ("weighted_constituent_breadth_snapshots", "ts", "index_symbol", 60),
]
SYMBOLS = ["NIFTY", "SENSEX"]
PARITY_TOL = 4          # allowed NIFTY-vs-SENSEX row-count gap
LAST_TS_TOL_MIN = 20    # how stale last_ts may be vs the expected last cycle

# ---- reference tables (refreshed ONCE pre-open, not row-counted in-session) --
# equity_intraday_last holds prev-day closes, refreshed ~03:35 UTC by
# refresh_equity_intraday_last.py. Freshness is measured on `ts` (upsert column),
# NEVER created_at (row-birth, never moves on upsert -- TD-S59-NEW-1).
REF_TABLE = "equity_intraday_last"
REF_TS = "ts"
REF_MIN_ROWS = 1200          # universe ~1385; ohlc() tail can drop a few dozen
REF_STALE_GRACE_HRS = 30     # ts may legitimately be the 03:35 UTC slot of --date
# market_spot_session_markers feeds Marketview's spot header (prev_close_spot ->
# client-side %-change). Stamped once daily ~16:10 IST by build_market_spot_session_markers.py
# (cron added S60). Freshness keyed on trade_date_ist; 2 rows/day = NIFTY+SENSEX (TD-S60-NEW-1).
MARKER_TABLE = "market_spot_session_markers"
MARKER_DATE_COL = "trade_date_ist"
MARKER_MIN_ROWS = 2

OK, WARN, FAIL = "OK", "WARN", "FAIL"
MARK = {OK: "[ OK ]", WARN: "[WARN]", FAIL: "[FAIL]"}


def cfg():
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        sys.exit("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set (source .env).")
    return url, {"apikey": key, "Authorization": f"Bearer {key}"}


def q(url, headers, table, params, count=False, timeout=60):
    h = dict(headers)
    if count:
        h["Prefer"] = "count=exact"
        params = dict(params, select="count")
    r = requests.get(f"{url}/rest/v1/{table}", headers=h, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def count_rows(url, headers, table, ts_col, lo, hi, sym_col=None, sym=None):
    qs = [(ts_col, f"gte.{lo}"), (ts_col, f"lt.{hi}")]
    if sym_col and sym:
        qs.append((sym_col, f"eq.{sym}"))
    h = dict(headers); h["Prefer"] = "count=exact"
    r = requests.get(f"{url}/rest/v1/{table}", headers=h,
                     params=qs + [("select", "count")], timeout=60)
    r.raise_for_status()
    data = r.json()
    return int(data[0]["count"]) if data else 0


def edge_ts(url, headers, table, ts_col, lo, hi, order, sym_col=None, sym=None):
    qs = [(ts_col, f"gte.{lo}"), (ts_col, f"lt.{hi}"),
          ("select", ts_col), ("order", f"{ts_col}.{order}"), ("limit", "1")]
    if sym_col and sym:
        qs.append((sym_col, f"eq.{sym}"))
    r = requests.get(f"{url}/rest/v1/{table}", headers=headers, params=qs, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data[0][ts_col] if data and data[0].get(ts_col) else None


def parse(ts):
    # py3.10 fromisoformat (EC2 default) only accepts 3 or 6 fractional-second digits and
    # RAISES on others; Postgres trims trailing zeros (e.g. .68213 = 5 digits). Normalize the
    # fractional part to exactly 6 digits so all microsecond widths parse on 3.10 and 3.12.
    if not ts:
        return None
    s = str(ts).replace("Z", "+00:00")
    m = re.match(r"^(.*\.)(\d+)([+\-].*)?$", s)
    if m:
        frac = (m.group(2) + "000000")[:6]
        s = m.group(1) + frac + (m.group(3) or "")
    try:
        dt = datetime.fromisoformat(s)
        return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


def hhmm(s, day):
    h, m = s.split(":")
    return day.replace(hour=int(h), minute=int(m), second=0, microsecond=0)


def check_marker_freshness(url, headers, sess_date, day0, verbose=False):
    """REFERENCE FRESHNESS -- was market_spot_session_markers stamped FOR sess_date?
    Marketview's spot header reads the newest trade_date_ist row and derives %-change
    from its prev_close_spot; a frozen newest = phantom %-change on the decision surface
    (TD-S60-NEW-1: writer unscheduled after the AWS-only migration, last wrote 2026-06-04,
    header showed +4.34% off a 21-day-stale baseline). Keyed on trade_date_ist (a date);
    a healthy trading day writes 2 rows (NIFTY+SENSEX).
    """
    table, col = MARKER_TABLE, MARKER_DATE_COL
    try:
        newest = edge_ts(url, headers, table, col, "1970-01-01", "2999-01-01", "desc")
        lo = sess_date.isoformat()
        hi = (sess_date + timedelta(days=1)).isoformat()
        n_today = count_rows(url, headers, table, col, lo, hi)
    except Exception as e:
        return FAIL, f"  {MARK[FAIL]} {table:<28} query error: {str(e)[:60]}"
    if newest is None:
        v, detail = FAIL, "no rows -- table empty or unreadable"
    elif n_today < 1:
        # not stamped for the audited day -> Marketview header reads a stale baseline
        v, detail = FAIL, (f"NOT written for {sess_date} -- newest {str(newest)[:10]} "
                           f"-- STALE HEADER BASELINE (TD-S60-NEW-1)")
    elif n_today < MARKER_MIN_ROWS:
        v, detail = WARN, (f"written for {sess_date} but only {n_today} row(s) "
                           f"(< {MARKER_MIN_ROWS} = NIFTY+SENSEX)")
    else:
        v, detail = OK, f"written for {sess_date}, {n_today} rows"
    return v, f"  {MARK[v]} {table:<28} {detail}"


def check_reference_freshness(url, headers, sess_date, day0, verbose=False):
    """REFERENCE FRESHNESS -- was equity_intraday_last refreshed FOR sess_date?

    Returns (verdict, printable_line). Anchored to the audited date, not wall-clock,
    so a stale-baseline day FAILs even when audited weeks later (the check that would
    have fired on 2026-05-21 for TD-S59-NEW-1). Measures `ts`, not created_at.
    """
    table, tsc = REF_TABLE, REF_TS
    try:
        # global newest ts (NOT date-bounded -- a frozen table's newest sits in the past)
        newest = parse(edge_ts(url, headers, table, tsc, "1970-01-01",
                               "2999-01-01", "desc"))
        # rows whose ts falls on the audited session day
        lo = sess_date.isoformat()
        hi = (sess_date + timedelta(days=1)).isoformat()
        n_today = count_rows(url, headers, table, tsc, lo, hi)
    except Exception as e:
        return FAIL, f"  {MARK[FAIL]} {table:<28} query error: {str(e)[:60]}"

    refreshed_for_date = n_today >= 1
    if newest is None:
        v = FAIL
        detail = "no readable ts -- table empty or unreadable"
    elif not refreshed_for_date:
        # not refreshed on the audited day -> stale baseline (the C-09 / TD-S59-NEW-1 mode)
        age_h = (day0 - newest).total_seconds() / 3600.0
        v = FAIL
        detail = (f"NOT refreshed for {sess_date} -- newest ts {newest:%Y-%m-%d %H:%M} UTC "
                  f"({age_h:.0f} h before session) -- STALE BASELINE (TD-S59-NEW-1)")
    elif n_today < REF_MIN_ROWS:
        v = WARN
        detail = (f"refreshed {newest:%H:%M} UTC but only {n_today} rows "
                  f"(< {REF_MIN_ROWS}) -- ohlc() coverage tail")
    else:
        v = OK
        detail = f"refreshed {newest:%Y-%m-%d %H:%M} UTC, {n_today} rows on {sess_date}"
    return v, f"  {MARK[v]} {table:<28} {detail}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="session date YYYY-MM-DD (IST); default = today IST")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    url, headers = cfg()

    now_utc = datetime.now(UTC)
    sess_date = (datetime.strptime(args.date, "%Y-%m-%d").date()
                 if args.date else datetime.now(IST).date())
    lo = sess_date.isoformat()
    hi = (sess_date + timedelta(days=1)).isoformat()
    day0 = datetime(sess_date.year, sess_date.month, sess_date.day, tzinfo=UTC)
    close_utc = hhmm(SESSION_CLOSE_UTC, day0)
    last_ok_utc = hhmm(LAST_CYCLE_OK_UTC, day0)

    in_session = (hhmm(SESSION_OPEN_UTC, day0) <= now_utc <= close_utc
                  and now_utc.date() == sess_date)
    # expected newest cycle
    expected_last = (now_utc - timedelta(minutes=10)) if in_session else close_utc

    print("=" * 74)
    print(f" MERDIAN EOD HEALTH CHECK  --  session {lo}  ({'IN-SESSION' if in_session else 'POST-CLOSE'})")
    print(f" now {now_utc:%Y-%m-%d %H:%M} UTC  |  ts basis: true-UTC  |  source: DATABASE (not dashboard)")
    print("=" * 74)

    results = []  # (verdict, line)

    def verdict_ts(last_dt):
        # A missing last_ts when the row COUNT is healthy is "can't confirm recency" = WARN,
        # never FAIL -- a complete count with an unreadable edge ts is not a data fault.
        if last_dt is None:
            return WARN
        age = (expected_last - last_dt).total_seconds() / 60.0
        return OK if age <= LAST_TS_TOL_MIN else (WARN if age <= 60 else FAIL)

    # ---- PRIMARY INGESTION --------------------------------------------------
    print("\nPRIMARY INGESTION")
    print("-" * 74)
    breadth_ok = False
    breadth_rows = 0
    for table, tsc, minrows, note in PRIMARY:
        try:
            n = count_rows(url, headers, table, tsc, lo, hi)
            first = parse(edge_ts(url, headers, table, tsc, lo, hi, "asc"))
            last = parse(edge_ts(url, headers, table, tsc, lo, hi, "desc"))
            v = OK
            if n == 0:
                v = FAIL
            elif n < minrows:
                v = WARN
            v = v if v == FAIL else max([v, verdict_ts(last)], key=lambda x: [OK, WARN, FAIL].index(x))
            if table == "market_breadth_intraday":
                breadth_ok, breadth_rows = (v == OK), n
            f = f"{first:%H:%M}" if first else "--:--"
            l = f"{last:%H:%M}" if last else "--:--"
            print(f"  {MARK[v]} {table:<28} {n:>7} rows  {f}->{l} UTC  ({note})")
            results.append(v)
        except Exception as e:
            print(f"  {MARK[FAIL]} {table:<28} query error: {str(e)[:60]}")
            results.append(FAIL)

    # market_ticks -- INFERRED, never row-counted
    if breadth_ok:
        print(f"  {MARK[OK]} {'market_ticks':<28} INFERRED-OK  (rolling buffer; breadth pipeline "
              f"healthy @ {breadth_rows} rows -> ticks flowed)")
        results.append(OK)
    else:
        print(f"  {MARK[WARN]} {'market_ticks':<28} SUSPECT  (breadth pipeline not healthy -- "
              f"verify tick capture via cron.log / in-session, NOT a row count)")
        results.append(WARN)

    # ---- COMPUTE UNIVERSE (per symbol + parity) -----------------------------
    print("\nCOMPUTE UNIVERSE  (per symbol; parity = |NIFTY-SENSEX| <= %d)" % PARITY_TOL)
    print("-" * 74)
    for table, tsc, symcol, minrows in COMPUTE:
        counts = {}
        try:
            for s in SYMBOLS:
                n = count_rows(url, headers, table, tsc, lo, hi, symcol, s)
                last = parse(edge_ts(url, headers, table, tsc, lo, hi, "desc", symcol, s))
                counts[s] = (n, last)
            # per-symbol verdicts
            line_v = OK
            cells = []
            for s in SYMBOLS:
                n, last = counts[s]
                sv = OK
                if n == 0:
                    sv = FAIL
                elif n < minrows:
                    sv = WARN
                sv = sv if sv == FAIL else max([sv, verdict_ts(last)],
                                               key=lambda x: [OK, WARN, FAIL].index(x))
                line_v = max([line_v, sv], key=lambda x: [OK, WARN, FAIL].index(x))
                l = f"{last:%H:%M}" if last else "--:--"
                cells.append(f"{s} {n:>3}@{l}")
            # parity
            gap = abs(counts[SYMBOLS[0]][0] - counts[SYMBOLS[1]][0])
            parity = "" if gap <= PARITY_TOL else f"  !! PARITY gap={gap}"
            if parity:
                line_v = max([line_v, WARN], key=lambda x: [OK, WARN, FAIL].index(x))
            print(f"  {MARK[line_v]} {table:<42} {' | '.join(cells)}{parity}")
            results.append(line_v)
        except Exception as e:
            print(f"  {MARK[FAIL]} {table:<42} query error: {str(e)[:50]}")
            results.append(FAIL)

    # ---- REFERENCE FRESHNESS (prev-close baseline; not row-counted in-session) --
    print("\nREFERENCE FRESHNESS  (prev-close baseline -- refreshed once pre-open)")
    print("-" * 74)
    rv, rline = check_reference_freshness(url, headers, sess_date, day0, args.verbose)
    print(rline)
    results.append(rv)
    mv, mline = check_marker_freshness(url, headers, sess_date, day0, args.verbose)
    print(mline)
    results.append(mv)

    # ---- VERDICT ------------------------------------------------------------
    print("\n" + "=" * 74)
    nfail = results.count(FAIL)
    nwarn = results.count(WARN)
    if nfail:
        overall = f"{MARK[FAIL]} {nfail} FAIL, {nwarn} WARN -- investigate above"
        code = 1
    elif nwarn:
        overall = f"{MARK[WARN]} {nwarn} WARN -- review above (often benign: low-volume / boundary)"
        code = 1
    else:
        overall = f"{MARK[OK]} clean session -- capture + compute complete and symmetric"
        code = 0
    print(" VERDICT: " + overall)
    print("=" * 74)
    print(" NOTE: this checks the DATABASE. Dashboard cards can lag independently")
    print("       (WCB render bug); a green DB here does not vouch for Marketview render.")
    return code


if __name__ == "__main__":
    sys.exit(main())
