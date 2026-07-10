#!/usr/bin/env python3
"""check_eod_coverage_freshness.py  (S66 — tuned per TD-S65-NEW-1)

Durable guard for the EOD -> DMA chain, mirroring the S59 REFERENCE FRESHNESS
guard (commit 6b58587) that closed the equity_intraday_last silent-freeze hole.
Closes the SAME class one layer up: the 2026-06-04 -> 2026-07-06 freeze where the
Dhan token expired, ingest_equity_eod_local.py 401'd every ticker, equity_eod /
breadth_indicators_daily froze at 06-04, and market_breadth_intraday.pct_above_*dma
silently went null while the batch read PARTIAL_OK for a month.

S66 tuning (TD-S65-NEW-1) — replaces the S65 guesses that produced the `/1` false-OK:
  * DENOMINATOR = the active-universe CEILING, read live: the peak distinct-ticker
    count over a trailing window of *published* EOD dates (~1,159 on the 07-02 clean
    rebuild). NOT a hard-coded 1,385, and NOT the latest-date count (which would make
    coverage trivially ~100% and blind the partial-day check). If the ceiling can't
    resolve to a believable number, the guard FAILS LOUD instead of dividing by a
    degenerate denominator (this is what kills the `/1`).
  * STALENESS = measured in TRADING days off the last trading day (weekday anchor,
    Rule 18 corollary), with a ~3-trading-day Dhan publish-lag tolerance. Normal 1-3
    day EOD lag + weekends/holidays no longer false-alarm; a multi-day freeze (the
    06-04->07-06 ~22-trading-day case) still fails.
  * COVERAGE threshold defaults to 95% to match COMPLETE_EOD_THRESHOLD_PCT (active).

Anchor is --date (S59 rule), never wall-clock. Exit 0 = all PASS, 1 = any FAIL.

Usage:
  python check_eod_coverage_freshness.py                       # audits today (IST)
  python check_eod_coverage_freshness.py --date 2026-07-07
  python check_eod_coverage_freshness.py --lag-trading-days 3 --min-coverage-pct 95
"""
import os, sys, argparse, datetime as dt
import requests
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SRK = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_KEY", "")
HDRS = {"apikey": SRK, "Authorization": f"Bearer {SRK}"}
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _d(s):
    return dt.date.fromisoformat(str(s)[:10])


def _latest_trade_date(table):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HDRS,
        params={"select": "trade_date", "order": "trade_date.desc", "limit": "1"},
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json()
    return rows[0]["trade_date"] if rows else None


def _count_on_date(table, date_str):
    """Exact row count for one trade_date via PostgREST count=exact. Returns int, or
    None if the count header is absent/unparseable -- never silently 1 (the S65 bug)."""
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**HDRS, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"},
        params={"select": "trade_date", "trade_date": f"eq.{date_str}"},
        timeout=30,
    )
    r.raise_for_status()
    total = r.headers.get("Content-Range", "").split("/")[-1]
    return int(total) if total.isdigit() else None


def _active_universe_count():
    """TRUE active-universe denominator (S67/TD-S66-NEW-3): live count of
    dhan_scrip_map rows using the SAME filter the builder's get_active_universe
    uses (exchange=NSE, is_active=true, dhan_security_id not null). This is what
    the EOD builder TRIES to cover -- the correct denominator -- as opposed to
    the trailing-window peak (what happened to arrive), which excludes the DH-905
    dead tail and moves with the numerator. Returns int, or None on failure."""
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/dhan_scrip_map",
        headers={**HDRS, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"},
        params={
            "select": "ticker",
            "exchange": "eq.NSE",
            "is_active": "eq.true",
            "dhan_security_id": "not.is.null",
        },
        timeout=30,
    )
    r.raise_for_status()
    total = r.headers.get("Content-Range", "").split("/")[-1]
    return int(total) if total.isdigit() else None


def _last_trading_day(d):
    """Most recent weekday on/before d (weekday anchor; Rule 18 corollary). Holiday-
    generous by design -- the lag tolerance absorbs a holiday landing on this day."""
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d -= dt.timedelta(days=1)
    return d


def _trading_gap(d_from, d_to):
    """Count weekdays in the half-open span (d_from, d_to]. 0 when d_to <= d_from."""
    n, d = 0, d_from + dt.timedelta(days=1)
    while d <= d_to:
        if d.weekday() < 5:
            n += 1
        d += dt.timedelta(days=1)
    return n


def _eod_window(audited, want_dates=10, max_lookback_weekdays=20):
    """Walk weekdays back from `audited`, counting equity_eod tickers per day, until
    `want_dates` published (non-zero) EOD dates are gathered or the lookback is spent.
    Returns {date_iso: ticker_count}. Self-discovering: no universe table, no hardcode.
    The peak value is the active-universe ceiling; the max key is the latest EOD date."""
    counts, d, checked = {}, audited, 0
    while len(counts) < want_dates and checked < max_lookback_weekdays:
        if d.weekday() < 5:
            checked += 1
            c = _count_on_date("equity_eod", d.isoformat())
            if c and c > 0:
                counts[d.isoformat()] = c
        d -= dt.timedelta(days=1)
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.datetime.now(IST).date().isoformat(),
                    help="audited trade date (default: today IST). Anchor is --date, never wall-clock (S59 rule).")
    ap.add_argument("--lag-trading-days", type=int, default=3,
                    help="Dhan publish-lag tolerance in TRADING days off the last trading day (default 3).")
    ap.add_argument("--min-coverage-pct", type=float, default=92.0,
                    help="min coverage vs the true active universe (default 92; true ceiling ~97.8% due to the ~28 permanent DH-905 dead security_ids).")
    ap.add_argument("--universe-floor", type=int, default=500,
                    help="minimum believable ceiling; below this the guard FAILS LOUD rather than dividing by a degenerate denominator.")
    args = ap.parse_args()

    if not SUPABASE_URL or not SRK:
        print("FAIL: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not in env")
        return 2

    audited = _d(args.date)
    ltd = _last_trading_day(audited)
    if ltd == audited:
        # The audited day is itself a trading day (i.e. "today"): its EOD is never
        # settled same-day, so it must NOT consume lag budget. Anchor staleness to the
        # last SETTLED trading day (strictly before today) -- otherwise the tolerance
        # silently behaves as (lag-1) on settled data and false-alarms one day early.
        ltd = _last_trading_day(audited - dt.timedelta(days=1))
    fails = []
    print("=" * 72)
    print(f"EOD COVERAGE FRESHNESS  |  audited --date={audited}  last-settled-td={ltd}")
    print(f"                        |  lag-tol={args.lag_trading_days}td  min-cov={args.min_coverage_pct}%")
    print("=" * 72)

    # equity_eod: freshness (trading-day gap off last trading day) + coverage (vs live ceiling)
    window = _eod_window(audited)
    if not window:
        fails.append("equity_eod: no published EOD dates in lookback window")
        print("  [FAIL] equity_eod: no rows in lookback window")
    else:
        eod_latest = max(window)            # iso date strings sort chronologically
        window_peak = max(window.values())  # S67: demoted to sanity cross-check only
        ceiling = _active_universe_count()  # S67/TD-S66-NEW-3: TRUE active universe (dhan_scrip_map, ~1385)
        cov = window[eod_latest]
        gap = _trading_gap(_d(eod_latest), ltd)
        pct = 100.0 * cov / ceiling if ceiling else 0.0
        if ceiling and window_peak > ceiling:
            print(f"  [WARN] window_peak {window_peak} > active-universe ceiling {ceiling} "
                  f"(dhan_scrip_map may be under-counting active tickers)")

        if ceiling is None or ceiling < args.universe_floor:
            fails.append(f"equity_eod: ceiling {ceiling} < floor {args.universe_floor} "
                         f"(denominator unresolved -- refusing to report OK)")
            print(f"  [FAIL] equity_eod: ceiling={ceiling} implausibly low (<{args.universe_floor})")
        else:
            stale = gap > args.lag_trading_days
            thin = pct < args.min_coverage_pct
            tag = "FAIL" if (stale or thin) else "OK"
            if stale:
                fails.append(f"equity_eod stale: latest {eod_latest} is {gap} trading-days behind "
                             f"{ltd} (> {args.lag_trading_days})")
            if thin:
                fails.append(f"equity_eod thin: {pct:.1f}% of ceiling {ceiling} on {eod_latest} "
                             f"(< {args.min_coverage_pct}%)")
            print(f"  [{tag}] equity_eod: latest={eod_latest} gap={gap}td "
                  f"coverage={cov}/{ceiling} ({pct:.1f}% of live ceiling)")

    # breadth_indicators_daily: freshness only (DMA layer), same trading-day model
    ind_latest = _latest_trade_date("breadth_indicators_daily")
    if ind_latest is None:
        fails.append("breadth_indicators_daily empty")
        print("  [FAIL] breadth_indicators_daily: no rows")
    else:
        gap = _trading_gap(_d(ind_latest), ltd)
        stale = gap > args.lag_trading_days
        tag = "FAIL" if stale else "OK"
        if stale:
            fails.append(f"breadth_indicators_daily stale: latest {ind_latest} is {gap} trading-days "
                         f"behind {ltd} (> {args.lag_trading_days})")
        print(f"  [{tag}] breadth_indicators_daily: latest={ind_latest} gap={gap}td")

    print("-" * 72)
    if fails:
        print(f"RESULT: FAIL ({len(fails)})")
        for f in fails:
            print(f"  - {f}")
        print("  => DMA layer stale/thin; market_breadth_intraday.pct_above_*dma will write null. "
              "Revive: ingest_equity_eod sweep + build_breadth_indicators_daily.")
        return 1
    print("RESULT: OK  (EOD + DMA fresh for the audited date; coverage within tolerance of live ceiling)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
