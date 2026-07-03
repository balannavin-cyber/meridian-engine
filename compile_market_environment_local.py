#!/usr/bin/env python3
"""
compile_market_environment_local.py  —  ENH-116 Ambient Environment Intelligence
Post-market compiler (build-sequence step 2).  "Compute at rest, relate at open."

Runs AFTER settlement.  For each symbol it derives the settled ambient state from
now-complete data and writes ONE market_environment_snapshots row keyed to the NEXT
session.  Display-not-gate (ADR-002 v2 D.19.3); touches no live routing.

SCOPE THIS FILE (per ENH-116 build-step 2):
  Lens 1 (gamma-positioning)  — LIVE, from live `gamma_metrics`.
  Lens 2 (breadth-trajectory) — LIVE, from `market_breadth_intraday` + WCB.
  Lens 3 (participant)        — writes NULL.  Wire once the ENH-115
                                `participant_oi_daily` / `fii_dii_cash_daily`
                                column schema is confirmed (not guessed).
  Lens 4 (macro)              — writes NULL until a feed is chosen.

HOUSE-INTEGRATION VERIFY-POINTS (2) — diff against compute_gamma_metrics_local.py
before first run; these are mirrored from the doc'd canonical pattern, not a file
I could read at author time:
  [VP-1] `from core.execution_log import ExecutionLog` open/record_write/complete/
         exit_with_reason signature.
  [VP-2] `from core.trading_calendar_gate import ...` gate function names.
Also confirm the two DATA verify-points marked [VD-1] (WCB index_symbol values) and
[VD-2] (breadth active universe filter) against the live tables.

Idempotent: UPSERT on (symbol, for_session_date, source).
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
REST = f"{SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}
PAGE = 1000  # Supabase hard cap (Rule 15)

SYMBOLS = ["NIFTY", "SENSEX"]
SOURCE = "ambient_compiler_s62"      # spec constant; bump to *_s64 if you want build-provenance
LOOKBACK_DAYS = 30                    # calendar days pulled to build ~20 trading-day series

# [VD-1] confirm the exact index_symbol literals in weighted_constituent_breadth_snapshots
WCB_INDEX_SYMBOL = {"NIFTY": "NIFTY", "SENSEX": "SENSEX"}


def now_ist():
    return datetime.now(IST)


def log(msg):
    print(f"[{now_ist().isoformat()}] {msg}", flush=True)


# ---------------------------------------------------------------- PostgREST I/O
def _get(path, params):
    """params is a LIST OF TUPLES (never a dict — Python drops duplicate keys; S63)."""
    rows, offset = [], 0
    while True:
        page_params = list(params) + [("limit", str(PAGE)), ("offset", str(offset))]
        r = requests.get(f"{REST}/{path}", headers=HEADERS, params=page_params, timeout=60)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < PAGE:
            return rows
        offset += PAGE


def _upsert(table, row):
    r = requests.post(
        f"{REST}/{table}",
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
        params=[("on_conflict", "symbol,for_session_date,source")],
        data=json.dumps(row),
        timeout=60,
    )
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"upsert {table} -> {r.status_code}: {r.text[:300]}")


# ---------------------------------------------------------------- date helpers
def _ist_date(ts_iso):
    """PostgREST timestamptz (real UTC) -> IST calendar date."""
    s = ts_iso.replace("Z", "+00:00")
    # normalise fractional seconds / short offsets defensively
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST).date()


def _daily_last(rows, ts_key):
    """Collapse an intraday series to one row per IST date: the last (max ts) row."""
    by_date = {}
    for row in rows:
        ts = row.get(ts_key)
        if not ts:
            continue
        d = _ist_date(ts)
        cur = by_date.get(d)
        if cur is None or row[ts_key] > cur[ts_key]:
            by_date[d] = row
    return [by_date[d] for d in sorted(by_date)]  # oldest -> newest


def _slope_per_step(vals):
    """OLS slope (units per session) over a clean numeric series; None if <2 points."""
    xs = [i for i, v in enumerate(vals) if v is not None]
    ys = [v for v in vals if v is not None]
    n = len(ys)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- fetchers
def fetch_gamma_daily(symbol, since_iso):
    rows = _get("gamma_metrics", [
        ("symbol", f"eq.{symbol}"),
        ("ts", f"gte.{since_iso}"),
        ("select", "ts,spot,net_gex,gamma_concentration,regime,max_gamma_strike"),
        ("order", "ts.asc"),
    ])
    return _daily_last(rows, "ts")


def fetch_breadth_daily(since_iso):
    # [VD-2] market_breadth_intraday is market-wide (universe_id keyed), not per index.
    # Guard against 9999 test-pollution; take last clean row per IST date.
    rows = _get("market_breadth_intraday", [
        ("ts", f"gte.{since_iso}"),
        ("select", "ts,universe_count,pct_above_20dma,breadth_score,advances,declines"),
        ("order", "ts.asc"),
    ])
    rows = [r for r in rows if (r.get("universe_count") or 0) < 5000]
    return _daily_last(rows, "ts")


def fetch_wcb_daily(symbol, since_iso):
    rows = _get("weighted_constituent_breadth_snapshots", [
        ("index_symbol", f"eq.{WCB_INDEX_SYMBOL[symbol]}"),
        ("ts", f"gte.{since_iso}"),
        ("select", "ts,wcb_score"),
        ("order", "ts.asc"),
    ])
    return _daily_last(rows, "ts")


# ---------------------------------------------------------------- lenses
def lens1_gamma(gamma_daily):
    """Gamma-positioning: persistence / max-γ drift / concentration trend / regime."""
    last20 = gamma_daily[-20:]
    last5 = gamma_daily[-5:]

    persistence = None
    if last20:
        longs = sum(1 for r in last20 if (r.get("regime") == "LONG_GAMMA"))
        persistence = round(longs / len(last20), 4)

    drift = _slope_per_step([_f(r.get("max_gamma_strike")) for r in last5])
    conc = _slope_per_step([_f(r.get("gamma_concentration")) for r in last5])

    net_gex_regime = None
    if gamma_daily:
        reg = gamma_daily[-1].get("regime")
        net_gex_regime = {"LONG_GAMMA": "POSITIVE_γ",
                          "SHORT_GAMMA": "NEGATIVE_γ",
                          "NO_FLIP": "MIXED"}.get(reg, "MIXED")

    return {
        "gex_regime_persistence_20d": persistence,
        "max_gamma_strike_drift_5d": round(drift, 4) if drift is not None else None,
        "concentration_trend_5d": round(conc, 6) if conc is not None else None,
        "net_gex_regime": net_gex_regime,
    }


def lens2_breadth(breadth_daily, wcb_daily, gamma_daily):
    """Breadth-trajectory + price-vs-breadth divergence (the top-tier tell)."""
    wcb_slope = _slope_per_step([_f(r.get("wcb_score")) for r in wcb_daily[-5:]])
    pct20_slope = _slope_per_step([_f(r.get("pct_above_20dma")) for r in breadth_daily[-5:]])

    # price 5d slope from daily EOD spot (gamma_metrics.spot); breadth proxy = wcb_score
    price_slope = _slope_per_step([_f(r.get("spot")) for r in gamma_daily[-5:]])
    breadth_slope = wcb_slope if wcb_slope is not None else (
        _slope_per_step([_f(r.get("breadth_score")) for r in breadth_daily[-5:]]))

    div = "NEUTRAL"
    if price_slope is not None and breadth_slope is not None:
        p_up, p_dn = price_slope > 0, price_slope < 0
        b_up, b_dn = breadth_slope > 0, breadth_slope < 0
        if (p_up and b_up) or (p_dn and b_dn):
            div = "CONFIRM"
        elif p_up and b_dn:
            div = "BEARISH_DIV"       # price up, breadth deteriorating
        elif p_dn and b_up:
            div = "BULLISH_DIV"       # price down, breadth improving

    return {
        "wcb_slope_5d": round(wcb_slope, 6) if wcb_slope is not None else None,
        "pct_above_20dma_slope_5d": round(pct20_slope, 6) if pct20_slope is not None else None,
        "price_vs_breadth_div": div,
    }


def reconcile(l1, l2):
    """First-pass reconciliation (v1, tunable — display-not-gate).

    With only L1+L2 active: divergence is driven by price-vs-breadth; regime maps
    gamma sign x breadth direction to the ADR-002 ambient enum. L3/L4 will refine
    alignment once wired. This mapping is the tunable core of the product.
    """
    div = l2["price_vs_breadth_div"]
    reg = l1["net_gex_regime"]

    lens_alignment = "DIVERGENT" if div in ("BEARISH_DIV", "BULLISH_DIV") else "ALIGNED"

    if div == "BEARISH_DIV":
        ambient = "DISTRIBUTION"
    elif div == "BULLISH_DIV":
        ambient = "ACCUMULATION"
    elif reg == "POSITIVE_γ":
        ambient = "RANGE"           # long-γ cage + breadth confirming = range/coil
    elif reg == "NEGATIVE_γ":
        ambient = "UNSTABLE"        # short-γ + aligned trend = expansion-prone
    else:
        ambient = "RANGE"

    note = (f"{ambient} · lenses {lens_alignment} · gamma {reg or 'n/a'} · "
            f"breadth {div} · (L3/L4 pending)")
    return {"ambient_regime": ambient, "lens_alignment": lens_alignment,
            "session_prior": note}


# ---------------------------------------------------------------- lens 3 (participant)
def fetch_participant_nse(as_of):
    """NSE participant-wise OI, last ~2 weeks of sessions (participant OI is NSE-only,
    S63; BSE stub dropped). Recency-guarded by lens3_participant, not here."""
    lo = (as_of - timedelta(days=14)).isoformat()
    return _get("participant_oi_daily", [
        ("exchange", "eq.NSE"),
        ("trade_date", f"gte.{lo}"), ("trade_date", f"lte.{as_of.isoformat()}"),
        ("select", "trade_date,participant,fut_idx_long,fut_idx_short,"
                   "opt_idx_call_long,opt_idx_put_long,opt_idx_call_short,opt_idx_put_short"),
        ("order", "trade_date.asc"),
    ])


def lens3_participant(part_rows, as_of):
    """Lens 3 (participant positioning) from NSE participant_oi_daily.

    ADR-018 D2 recency guard — MANDATED by the ENH-115 DDL ("compare trade_date to the
    trading calendar and flag, never silently tilt on a stale board"): if the freshest
    board is older than the settled session, return NULLs + STALE rather than tilting.

    v1 formulas (tunable, display-not-gate):
      cycle_oi_call_put_asym    = (call_oi - put_oi)/(call_oi + put_oi) from the TOTAL
                                  index-option board. +ve = call-side (ceiling) building.
      fii_index_fut_ls_delta_5d = FII (fut_idx_long - fut_idx_short) net change over the
                                  last ~5 sessions. +ve = FII adding net index-fut longs.
      pro_options_imbalance     = Pro normalized (net-call - net-put) in [-1,1].
                                  +ve = Pro leaning call-long / put-short.
    """
    null3 = {"cycle_oi_call_put_asym": None,
             "fii_index_fut_ls_delta_5d": None,
             "pro_options_imbalance": None}
    if not part_rows:
        return {**null3, "_note": "no participant board"}

    dates = sorted({r["trade_date"] for r in part_rows})
    latest = dates[-1]
    if latest != as_of.isoformat():          # ADR-018 D2: stale -> do not tilt
        return {**null3, "_note": f"STALE participant board (latest {latest})"}

    def row(part, d):
        return next((r for r in part_rows
                     if r["participant"] == part and r["trade_date"] == d), None)

    tot = row("TOTAL", latest)
    asym = None
    if tot:
        c = _f(tot.get("opt_idx_call_long")) or 0.0
        p = _f(tot.get("opt_idx_put_long")) or 0.0
        if (c + p) > 0:
            asym = round((c - p) / (c + p), 4)

    def fii_net(d):
        r = row("FII", d)
        if not r:
            return None
        l, s = _f(r.get("fut_idx_long")), _f(r.get("fut_idx_short"))
        return None if (l is None or s is None) else (l - s)
    ref = dates[-6] if len(dates) >= 6 else dates[0]      # ~5 sessions back
    n_now, n_ref = fii_net(latest), fii_net(ref)
    fii_delta = round(n_now - n_ref, 1) if (n_now is not None and n_ref is not None) else None

    pro = row("Pro", latest)
    pro_imb = None
    if pro:
        ncall = (_f(pro.get("opt_idx_call_long")) or 0) - (_f(pro.get("opt_idx_call_short")) or 0)
        nput = (_f(pro.get("opt_idx_put_long")) or 0) - (_f(pro.get("opt_idx_put_short")) or 0)
        denom = abs(ncall) + abs(nput)
        if denom > 0:
            pro_imb = round((ncall - nput) / denom, 4)

    return {"cycle_oi_call_put_asym": asym,
            "fii_index_fut_ls_delta_5d": fii_delta,
            "pro_options_imbalance": pro_imb,
            "_note": f"fresh ({latest})"}


# ---------------------------------------------------------------- main
def compile_symbol(symbol, as_of_date, for_session_date, since_iso, l3):
    gamma_daily = fetch_gamma_daily(symbol, since_iso)
    breadth_daily = fetch_breadth_daily(since_iso)
    wcb_daily = fetch_wcb_daily(symbol, since_iso)

    if not gamma_daily:
        log(f"{symbol}: no gamma_metrics in window — SKIP")
        return None

    l1 = lens1_gamma(gamma_daily)
    l2 = lens2_breadth(breadth_daily, wcb_daily, gamma_daily)
    rec = reconcile(l1, l2)

    row = {
        "symbol": symbol,
        "as_of_date": as_of_date.isoformat(),
        "for_session_date": for_session_date.isoformat(),
        **l1, **l2,
        # Lens 3 (participant, NSE) — recency-guarded (ADR-018 D2)
        "cycle_oi_call_put_asym": l3.get("cycle_oi_call_put_asym"),
        "fii_index_fut_ls_delta_5d": l3.get("fii_index_fut_ls_delta_5d"),
        "pro_options_imbalance": l3.get("pro_options_imbalance"),
        # Lens 4 (macro) — NULL until feed chosen
        "usdinr_trend_5d": None, "crude_trend_5d": None,
        "gold_trend_5d": None, "macro_tilt": None,
        **rec,
        "regime_conditional_note": None,   # Phase-B fills later
        "source": SOURCE,
    }
    _upsert("market_environment_snapshots", row)
    log(f"{symbol}: {rec['ambient_regime']} / {rec['lens_alignment']} "
        f"(persist={l1['gex_regime_persistence_20d']} div={l2['price_vs_breadth_div']} "
        f"asym={l3.get('cycle_oi_call_put_asym')}) -> for {for_session_date}")
    return row


def next_trading_day(d, is_trading_day):
    n = d + timedelta(days=1)
    for _ in range(10):
        if is_trading_day(n.isoformat()):
            return n
        n += timedelta(days=1)
    return d + timedelta(days=1)  # fallback


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", help="settled session date YYYY-MM-DD (default: today IST)")
    ap.add_argument("--dry-run", action="store_true", help="compute + print, no write")
    args = ap.parse_args()

    if not SUPABASE_URL or not SERVICE_KEY:
        log("FATAL: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not in env")
        return 2

    # [VP-2] trading-day gate — canonical shared gate (S60)
    from core.trading_calendar_gate import is_trading_day, assert_trading_day_or_exit

    as_of = (datetime.fromisoformat(args.as_of).date()
             if args.as_of else now_ist().date())

    if not args.as_of:
        # only compile on a settled trading day when run unattended
        assert_trading_day_or_exit(log=log)
    elif not is_trading_day(as_of.isoformat()):
        log(f"{as_of} is not a trading day — nothing to compile")
        return 0

    for_session = next_trading_day(as_of, is_trading_day)
    since_iso = (datetime.combine(as_of, datetime.min.time(), tzinfo=IST)
                 - timedelta(days=LOOKBACK_DAYS)).astimezone(UTC).isoformat()

    log(f"compile as_of={as_of} for_session={for_session} since={since_iso}")

    # Lens 3 participant board is market-wide (NSE) — computed once, applied to both symbols
    l3 = lens3_participant(fetch_participant_nse(as_of), as_of)
    log(f"participant (NSE): {l3.get('_note')}")

    # ---- dry-run: pure compute + print, no instrumentation, no writes ----
    if args.dry_run:
        for sym in SYMBOLS:
            gd = fetch_gamma_daily(sym, since_iso)
            if not gd:
                log(f"[dry] {sym}: no gamma_metrics in window")
                continue
            l1 = lens1_gamma(gd)
            l2 = lens2_breadth(fetch_breadth_daily(since_iso),
                               fetch_wcb_daily(sym, since_iso), gd)
            l3v = {k: v for k, v in l3.items() if not k.startswith("_")}
            log(f"[dry] {sym}: {json.dumps({**l1, **l2, **l3v, **reconcile(l1, l2)})}")
        return 0

    # ---- real run: ENH-72 ExecutionLog (row INSERTs at construction) ----
    # API per ENH-72 ship notes: ExecutionLog(...) opens the RUNNING row; methods
    # record_write(table, n) / complete(notes) / exit_with_reason(reason, exit_code,
    # notes, error_message). ExecutionLog is best-effort by contract ("must never
    # break the calling script"), so a residual constructor-kwarg mismatch warns and
    # proceeds uninstrumented rather than aborting the write. Confirm the exact kwargs
    # against an ENH-72 writer (e.g. compute_gamma_metrics_local.py) to firm this up.
    from core.execution_log import ExecutionLog
    try:
        xlog = ExecutionLog(
            script_name="compile_market_environment_local",
            symbol=None,
            expected_writes={"market_environment_snapshots": len(SYMBOLS)},
        )
    except Exception as e:
        log(f"WARN ExecutionLog construction failed ({e}) — proceeding uninstrumented")
        xlog = None

    def _rec(n=1):
        if xlog is not None:
            try:
                xlog.record_write("market_environment_snapshots", n)
            except Exception:
                pass

    try:
        written = 0
        for sym in SYMBOLS:
            if compile_symbol(sym, as_of, for_session, since_iso, l3):
                _rec(1)
                written += 1
        if xlog is not None:
            try:
                xlog.complete(notes=f"wrote {written}/{len(SYMBOLS)}")
            except Exception:
                pass
        log(f"DONE wrote={written}/{len(SYMBOLS)}")
        return 0
    except Exception as e:
        if xlog is not None:
            try:
                xlog.exit_with_reason("DATA_ERROR", exit_code=1, notes=str(e),
                                      error_message=str(e))
            except Exception:
                pass
        log(f"FAILED: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
