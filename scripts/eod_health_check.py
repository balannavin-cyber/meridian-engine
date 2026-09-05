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

S72 additions (2026-09-05), each closing a filed defect:
  * TD-S71-NEW-15 -- PRIMARY INGESTION counted totals with NO per-symbol parity, so
    NIFTY vanishing for two sessions still reported [ OK ] on a healthy-looking total.
    The parity rule already existed in COMPUTE UNIVERSE; it is now applied to PRIMARY
    for every table that carries a symbol column.
  * TD-S72-NEW-10 -- CONTINUITY. A first->last range check cannot see a truncated tail
    or a halved count. 2026-07-31 wrote 302 breadth rows ending 08:42 UTC and 2026-08-17
    wrote 297 ending 08:39 -- both ~78% of a session, both stopping ~80 min early, both
    passing because min_rows was 60 against an observed norm of 379/390. Floors are now
    calibrated from a 45-day census and each table asserts its own expected TAIL time.
  * TD-S72-NEW-8 -- logrotate empties cron.log at 00:00 UTC; this check runs 00:45 UTC.
    The evidence is always in cron.log.1. Resolved by mtime/size, never by generation
    number (`notifempty` means a silent day produces no rotation, so .1 is not
    reliably yesterday).
  * TD-S72-NEW-9 -- the market_ticks WARN line pointed at logs/cron.log, which does not
    exist. The file is at repo root.
  * TD-S72-NEW-3 -- v_gex_strike_pin_zone / v_gex_strike_accel_zone were bounded in S72
    using a LITERAL symbol list. A third symbol would be silently absent from both views.
    Asserted here against COUNT(DISTINCT symbol) in gex_strike_snapshots.

Data ts is true-UTC (post-2026-04-07, CLAUDE Rule 20). Session runs ~03:00-10:00 UTC
(08:30-15:30 IST), extended to ~10:10 UTC for CAS-window tables (ADR-022). Reads
SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from .env, same raw-HTTP pattern as
ingest_option_chain_local.py.

Usage:
  python3 eod_health_check.py                 # check today's session (IST date)
  python3 eod_health_check.py --date 2026-06-23
  python3 eod_health_check.py --verbose
Exit code: 0 = all OK, 1 = one or more WARN/FAIL.
"""
import argparse
import glob
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
# Primary ingestion (raw capture).
#
# S72: entries gained `tail_utc` and `sym_col`.
#
#   min_rows -- calibrated 2026-09-05 from a 45-day observed census, NOT guessed.
#     market_spot_snapshots    observed 723   (~1.8/min x 2 symbols)   -> floor 600
#     market_breadth_intraday  observed 379 pre-CAS / 390 post-CAS     -> floor 350
#     option_chain_snapshots   observed 68738                          -> floor 50000
#     index_futures_snapshots  observed 302                            -> floor 250
#   The old breadth floor of 60 is why 302 and 297 both passed. A floor must sit just
#   under the observed norm, not at a value any partial session clears.
#
#   tail_utc -- the time the LAST row of a healthy session should land at or after.
#     This is the truncation detector. It is per-table because tables legitimately
#     stop at different times: the CAS-window extension (crontab `0,5,10 10`, live
#     2026-08-24, ADR-022) moved breadth and chain to ~10:10 while spot and futures
#     already ran to ~10:30. A single global close cannot express that.
#
#   sym_col -- column to split on for the PRIMARY parity check, or None for tables
#     that are market-wide by construction (breadth is not per-index).
PRIMARY = [
    # (table, ts_col, min_rows, tail_utc, sym_col, cadence_note)
    ("market_spot_snapshots",   "ts",   600, "10:20", "symbol", "~1/min capture"),
    ("market_breadth_intraday", "ts",   350, "09:55", None,     "~5-min cycle; ALSO the tick-health proxy"),
    ("option_chain_snapshots",  "ts", 50000, "10:00", "symbol", "per-strike rows, high volume"),
    ("index_futures_snapshots", "ts",   250, "10:20", "symbol", "~1/min capture"),
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
PARITY_TOL = 4          # allowed NIFTY-vs-SENSEX row-count gap (COMPUTE)
PRIMARY_PARITY_TOL_PCT = 10   # PRIMARY volumes differ legitimately by symbol
                              # (SENSEX chains are wider); assert PROPORTION, not count.
LAST_TS_TOL_MIN = 20    # how stale last_ts may be vs the expected last cycle

# ---- GEX view symbol coverage (TD-S72-NEW-3) --------------------------------
# S72 bounded v_gex_strike_pin_zone / v_gex_strike_accel_zone with a literal
# VALUES ('NIFTY'),('SENSEX') driver to replace a 1.32M-row DISTINCT ON scan
# (489.9ms -> 4.2ms). The cost is that a third symbol becomes silently invisible
# in both views -- no error, no empty result, just a correct-looking answer for
# two of three. This assertion is the guard that hazard requires.
GEX_TABLE = "gex_strike_snapshots"
GEX_VIEW_SYMBOLS = {"NIFTY", "SENSEX"}   # MUST match the VALUES list in both views

# ---- cron log resolution (TD-S72-NEW-8 / TD-S72-NEW-9) ----------------------
# /etc/logrotate.d/meridian: daily, rotate 7, compress, delaycompress, copytruncate.
# Rotation fires 00:00 UTC; this check runs 00:45 UTC; so cron.log is ALWAYS empty
# by the time anyone reads it and the session's record is in cron.log.1.
# `notifempty` means a silent day produces NO rotation, so generation number is not
# a reliable day offset -- resolve by mtime and size instead.
CRON_LOG_CANDIDATES = ["cron.log", "cron.log.1"]
CRON_LOG_GLOB = "cron.log.*"

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
RANK = [OK, WARN, FAIL]


def worse(*verdicts):
    """Return the most severe verdict. Replaces the repeated inline max(key=index)."""
    return max(verdicts, key=RANK.index)


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


def resolve_cron_log(repo_root=None):
    """TD-S72-NEW-8 / TD-S72-NEW-9 -- return (path, mtime_utc, size) for the cron log
    that actually holds a session's record, or (None, None, 0).

    Two defects are closed here. The path was documented as logs/cron.log and the file
    is at REPO ROOT. And logrotate (daily, copytruncate) empties cron.log at 00:00 UTC
    while this check runs at 00:45 UTC, so the live file is reliably a 0-byte decoy and
    the evidence sits in cron.log.1 -- 663,776 bytes of it on 2026-09-04, never read.

    Resolved by mtime and size rather than generation number: `notifempty` means a
    silent day produces no rotation at all, so .1 is NOT reliably yesterday.
    """
    root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    best = (None, None, 0)
    seen = set()
    cands = [os.path.join(root, c) for c in CRON_LOG_CANDIDATES]
    cands += sorted(glob.glob(os.path.join(root, CRON_LOG_GLOB)))
    for p in cands:
        if p in seen or not os.path.isfile(p):
            continue
        seen.add(p)
        try:
            st = os.stat(p)
        except OSError:
            continue
        if st.st_size <= 0:
            continue                      # the rotated-and-emptied decoy
        if best[1] is None or st.st_mtime > best[1].timestamp():
            best = (p, datetime.fromtimestamp(st.st_mtime, UTC), st.st_size)
    return best


def check_gex_symbol_coverage(url, headers):
    """TD-S72-NEW-3 -- the S72 GEX view fix bounded latest_run with a LITERAL symbol
    list. Assert the table has not outgrown it.

    Failure here is not cosmetic: a third symbol present in gex_strike_snapshots but
    absent from the views' VALUES driver produces a complete-looking result for the
    two it does know about. That is the silent-omission shape of TD-S71-NEW-14, and
    the whole reason the literal was accepted was that this assertion would exist.
    """
    try:
        r = requests.get(f"{url}/rest/v1/{GEX_TABLE}", headers=headers,
                         params=[("select", "symbol")], timeout=60)
        r.raise_for_status()
        found = {row["symbol"] for row in r.json() if row.get("symbol")}
    except Exception as e:
        return WARN, f"  {MARK[WARN]} {'gex view symbol coverage':<28} query error: {str(e)[:60]}"

    if not found:
        return WARN, (f"  {MARK[WARN]} {'gex view symbol coverage':<28} "
                      f"no symbols readable in {GEX_TABLE}")
    missing = found - GEX_VIEW_SYMBOLS
    if missing:
        return FAIL, (f"  {MARK[FAIL]} {'gex view symbol coverage':<28} "
                      f"{sorted(missing)} in {GEX_TABLE} but NOT in the pin/accel view "
                      f"VALUES list -- SILENTLY EXCLUDED (TD-S72-NEW-3)")
    absent = GEX_VIEW_SYMBOLS - found
    if absent:
        return WARN, (f"  {MARK[WARN]} {'gex view symbol coverage':<28} "
                      f"view lists {sorted(absent)} but no rows present in {GEX_TABLE}")
    return OK, (f"  {MARK[OK]} {'gex view symbol coverage':<28} "
                f"{sorted(found)} == view VALUES list")


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

    def verdict_tail(last_dt, tail_hhmm):
        """TD-S72-NEW-10 -- TRUNCATION detector, post-close only.

        verdict_ts() measures staleness against a single global expectation and is
        satisfied by any recent-enough row. It cannot see a session that started on
        time, ran normally, and then STOPPED EARLY -- which is exactly what happened
        on 2026-07-31 (last row 08:42 UTC) and 2026-08-17 (08:39). Both looked fine.

        This asserts the per-table tail directly. In-session it is meaningless and
        returns OK.
        """
        if in_session or last_dt is None or not tail_hhmm:
            return OK, ""
        expect = hhmm(tail_hhmm, day0)
        short_min = (expect - last_dt).total_seconds() / 60.0
        if short_min <= LAST_TS_TOL_MIN:
            return OK, ""
        v = FAIL if short_min > 60 else WARN
        return v, f"  !! TRUNCATED tail {last_dt:%H:%M} < expected {tail_hhmm} (-{short_min:.0f}m)"

    # ---- PRIMARY INGESTION --------------------------------------------------
    print("\nPRIMARY INGESTION  (per-symbol parity where the table carries a symbol)")
    print("-" * 74)
    breadth_ok = False
    breadth_rows = 0
    for table, tsc, minrows, tail_utc, symcol, note in PRIMARY:
        try:
            n = count_rows(url, headers, table, tsc, lo, hi)
            first = parse(edge_ts(url, headers, table, tsc, lo, hi, "asc"))
            last = parse(edge_ts(url, headers, table, tsc, lo, hi, "desc"))
            v = OK
            if n == 0:
                v = FAIL
            elif n < minrows:
                v = WARN
            v = v if v == FAIL else worse(v, verdict_ts(last))

            # TD-S72-NEW-10 -- truncated tail
            tv, tail_note = verdict_tail(last, tail_utc)
            v = worse(v, tv)

            # TD-S71-NEW-15 -- per-symbol parity on PRIMARY.
            # 2026-08-25: NIFTY vanished for two sessions and this block reported
            # [ OK ] 151 rows because it only ever counted the total. The rule below
            # is the same one COMPUTE UNIVERSE has always applied.
            #
            # Counts differ legitimately by symbol here (SENSEX option chains are
            # wider than NIFTY's), so the assertion is PROPORTIONAL, not a flat gap:
            # neither symbol may fall below PRIMARY_PARITY_TOL_PCT of the total.
            # The symbol query is wrapped: an unknown column degrades to a WARN
            # naming itself rather than failing the table. Verify against live schema
            # before trusting a WARN here -- S71 wrote four queries against invented
            # column names and this is the same exposure.
            parity_note = ""
            if symcol and n > 0:
                try:
                    per = {s: count_rows(url, headers, table, tsc, lo, hi, symcol, s)
                           for s in SYMBOLS}
                    tot = sum(per.values())
                    if tot == 0:
                        parity_note = f"  !! PARITY none of {SYMBOLS} matched on {symcol}"
                        v = worse(v, FAIL)
                    else:
                        floor = tot * PRIMARY_PARITY_TOL_PCT / 100.0
                        starved = [s for s, c in per.items() if c < floor]
                        cells = " ".join(f"{s}={per[s]}" for s in SYMBOLS)
                        if starved:
                            parity_note = (f"  !! PARITY {cells} -- {starved} below "
                                           f"{PRIMARY_PARITY_TOL_PCT}% of {tot}")
                            v = worse(v, FAIL)
                        elif args.verbose:
                            parity_note = f"  ({cells})"
                        if tot < n and args.verbose:
                            parity_note += f"  [{n - tot} rows outside {SYMBOLS}]"
                except Exception as e:
                    parity_note = (f"  !! PARITY unchecked -- '{symcol}' query failed "
                                   f"({str(e)[:40]}); VERIFY COLUMN AGAINST LIVE SCHEMA")
                    v = worse(v, WARN)

            if table == "market_breadth_intraday":
                breadth_ok, breadth_rows = (v == OK), n
            f = f"{first:%H:%M}" if first else "--:--"
            l = f"{last:%H:%M}" if last else "--:--"
            print(f"  {MARK[v]} {table:<28} {n:>7} rows  {f}->{l} UTC  ({note})"
                  f"{tail_note}{parity_note}")
            results.append(v)
        except Exception as e:
            print(f"  {MARK[FAIL]} {table:<28} query error: {str(e)[:60]}")
            results.append(FAIL)

    # market_ticks -- INFERRED, never row-counted
    #
    # TD-S72-NEW-8 / -9: on the unhealthy branch, resolve and NAME the cron log that
    # actually holds the session record. The old text said "cron.log" with no path;
    # the documented logs/cron.log does not exist; and by 00:45 UTC the live file has
    # been emptied by rotation. Investigations have therefore started from an empty
    # file every time.
    if breadth_ok:
        print(f"  {MARK[OK]} {'market_ticks':<28} INFERRED-OK  (rolling buffer; breadth pipeline "
              f"healthy @ {breadth_rows} rows -> ticks flowed)")
        results.append(OK)
    else:
        cpath, cmtime, csize = resolve_cron_log()
        if cpath:
            where = f"{cpath} ({csize:,} B, mtime {cmtime:%Y-%m-%d %H:%M} UTC)"
        else:
            where = "NO non-empty cron.log found -- check logrotate and repo root"
        print(f"  {MARK[WARN]} {'market_ticks':<28} SUSPECT  (breadth pipeline not healthy -- "
              f"verify tick capture in-session or in the log below, NOT a row count)")
        print(f"  {'':6} {'':<28} evidence: {where}")
        print(f"  {'':6} {'':<28} also: logs/ws_feed_zerodha.log[.1] -- check the "
              f"'Subscribing N instruments' line; N in the low single digits means the "
              f"instrument load failed open (TD-S72-NEW-5)")
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
                sv = sv if sv == FAIL else worse(sv, verdict_ts(last))
                line_v = worse(line_v, sv)
                l = f"{last:%H:%M}" if last else "--:--"
                cells.append(f"{s} {n:>3}@{l}")
            # parity
            gap = abs(counts[SYMBOLS[0]][0] - counts[SYMBOLS[1]][0])
            parity = "" if gap <= PARITY_TOL else f"  !! PARITY gap={gap}"
            if parity:
                line_v = worse(line_v, WARN)
            print(f"  {MARK[line_v]} {table:<42} {' | '.join(cells)}{parity}")
            results.append(line_v)
        except Exception as e:
            print(f"  {MARK[FAIL]} {table:<42} query error: {str(e)[:50]}")
            results.append(FAIL)

    # ---- DERIVED-VIEW INTEGRITY (S72) ---------------------------------------
    print("\nDERIVED-VIEW INTEGRITY")
    print("-" * 74)
    gv, gline = check_gex_symbol_coverage(url, headers)
    print(gline)
    results.append(gv)

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
    print(" NOTE: FAIL count is a SYMPTOM count, not a cause count. feed -> market_ticks")
    print("       -> market_breadth_intraday -> WCB is ONE chain; a single upstream break")
    print("       lights every line in it (observed 2026-08-25 and 2026-09-04).")
    return code


if __name__ == "__main__":
    sys.exit(main())
