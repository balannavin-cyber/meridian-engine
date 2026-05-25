#!/usr/bin/env python3
"""
s30_path1_live_cohort_pnl_v2.py — Path 1 v2 against option_chain_snapshots.

v1 fetched against hist_atm_option_bars_5m which ends 2026-03-30 — pre-dates the
8-week window entirely (0 enriched). v2 joins against option_chain_snapshots (live
per-strike capture, 1.36M rows 2026-04-13 → 2026-05-15) using the signal's own
atm_strike + expiry_date + option_type derived from action.

Join shape (per signal):
  entry: option_chain_snapshots
         WHERE symbol = sig.symbol
           AND strike = sig.atm_strike
           AND option_type = ('CE' if sig.action='BUY_CE' else 'PE')
           AND expiry_date = sig.expiry_date
           AND ts BETWEEN sig.ts - 3min AND sig.ts + 3min
         pick row with min |ts - sig.ts|
  exit: same query, ts window centered on sig.ts + 30min

Run:
    python s30_path1_live_cohort_pnl_v2.py
"""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv  # type: ignore
from supabase import Client, create_client  # type: ignore


IST_TZ = timezone(timedelta(hours=5, minutes=30))
EXIT_OFFSET_MIN = 30
MATCH_TOL_MIN = 3
WINDOW_WEEKS = 8

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


def _load_supabase() -> Client:
    load_dotenv(override=False)
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not url or not key:
        raise RuntimeError("SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


def fetch_signals(sb: Client) -> list[dict]:
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(weeks=WINDOW_WEEKS)).isoformat()
    print(f"[1/2] Fetching trade_allowed signals since {cutoff_iso}...")
    out, off = [], 0
    while True:
        resp = (sb.table("signal_snapshots")
                .select("id, ts, symbol, action, expiry_date, spot, atm_strike, dte, "
                        "ict_pattern, ict_tier, ict_mtf_context, ict_size_mult, "
                        "po3_session_bias, direction_bias, confidence_score, "
                        "gamma_regime, breadth_regime, vix_regime")
                .eq("trade_allowed", True)
                .in_("action", ["BUY_CE", "BUY_PE"])
                .gte("ts", cutoff_iso)
                .order("ts")
                .range(off, off + 999)
                .execute())
        rows = resp.data or []
        if not rows: break
        out.extend(rows)
        if len(rows) < 1000: break
        off += 1000
    print(f"      → {len(out)} actionable trade_allowed signals (BUY_CE/BUY_PE only)")
    return out


def fetch_chain_row_at(sb: Client, symbol: str, strike: int, option_type: str,
                       expiry_date: str, target_ts: datetime) -> dict | None:
    """Fetch the option_chain_snapshots row closest to target_ts within ±MATCH_TOL_MIN."""
    lo = (target_ts - timedelta(minutes=MATCH_TOL_MIN)).isoformat()
    hi = (target_ts + timedelta(minutes=MATCH_TOL_MIN)).isoformat()
    resp = (sb.table("option_chain_snapshots")
            .select("ts, symbol, strike, option_type, expiry_date, ltp")
            .eq("symbol", symbol)
            .eq("strike", strike)
            .eq("option_type", option_type)
            .eq("expiry_date", expiry_date)
            .gte("ts", lo).lte("ts", hi)
            .order("ts")
            .range(0, 99)
            .execute())
    rows = resp.data or []
    if not rows: return None
    # Pick closest by |ts - target|
    best = None; best_delta = None
    for r in rows:
        try: rts = _ts_from_str(r["ts"])
        except (KeyError, ValueError): continue
        delta = abs((rts - target_ts).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta; best = r
    return best


def main() -> int:
    sb = _load_supabase()
    signals = fetch_signals(sb)
    if not signals:
        print("\n*** No actionable trade_allowed signals in 8-week window ***")
        return 0

    print(f"[2/2] Per-signal join to option_chain_snapshots...")
    enriched = []
    skipped_no_entry = skipped_no_exit = skipped_no_strike = skipped_zero_price = 0
    pre_coverage = 0  # signals before option_chain_snapshots coverage starts

    # Probe option_type convention on first eligible signal (avoid blind 0-hit join)
    option_type_convention = None  # 'CE/PE' or 'CALL/PUT'

    for i, sig in enumerate(signals, 1):
        if i % 10 == 0:
            print(f"      ...processed {i}/{len(signals)}")
        try: sig_ts = _ts_from_str(sig["ts"])
        except (KeyError, ValueError): continue
        sym = sig["symbol"]
        act = sig["action"]
        strike = sig.get("atm_strike")
        if strike is None:
            skipped_no_strike += 1
            continue
        expiry = sig.get("expiry_date")
        if not expiry:
            skipped_no_strike += 1
            continue

        # Try CE/PE first, fall back to CALL/PUT for first signal only
        candidates = [("CE" if act == "BUY_CE" else "PE",)]
        if option_type_convention is None:
            candidates.append(("CALL" if act == "BUY_CE" else "PUT",))
        elif option_type_convention == "CALL/PUT":
            candidates = [("CALL" if act == "BUY_CE" else "PUT",)]

        entry_bar = None; convention_used = None
        for (ot,) in candidates:
            entry_bar = fetch_chain_row_at(sb, sym, int(strike), ot, str(expiry), sig_ts)
            if entry_bar:
                convention_used = "CE/PE" if ot in ("CE", "PE") else "CALL/PUT"
                if option_type_convention is None:
                    option_type_convention = convention_used
                    print(f"      [probe] option_type convention = {convention_used}")
                break

        if entry_bar is None:
            # If we never matched at all and convention still unknown, this may be
            # pre-coverage. option_chain_snapshots starts 2026-04-13.
            if sig_ts < datetime(2026, 4, 13, tzinfo=timezone.utc):
                pre_coverage += 1
            else:
                skipped_no_entry += 1
            continue

        # Use confirmed convention for exit
        ot_final = ("CE" if act == "BUY_CE" else "PE") if option_type_convention == "CE/PE" else ("CALL" if act == "BUY_CE" else "PUT")
        exit_bar = fetch_chain_row_at(sb, sym, int(strike), ot_final, str(expiry),
                                       sig_ts + timedelta(minutes=EXIT_OFFSET_MIN))
        if exit_bar is None:
            skipped_no_exit += 1
            continue

        ep_raw, xp_raw = entry_bar.get("ltp"), exit_bar.get("ltp")
        if ep_raw is None or xp_raw is None:
            skipped_zero_price += 1
            continue
        try:
            epf, xpf = float(ep_raw), float(xp_raw)
        except (TypeError, ValueError):
            skipped_zero_price += 1
            continue
        if epf <= 0:
            skipped_zero_price += 1
            continue

        pnl_pct = (xpf - epf) / epf * 100
        ict_pat = sig.get("ict_pattern") or "NULL"
        ict_tier_v = sig.get("ict_tier") or "NULL"
        ict_ctx_v = sig.get("ict_mtf_context") or "NULL"
        has_ict = ict_pat not in ("NONE", "NULL")

        enriched.append({
            "id": sig["id"],
            "ts": sig_ts,
            "trade_date": sig_ts.astimezone(IST_TZ).date(),
            "symbol": sym,
            "action": act,
            "ict_pattern": ict_pat,
            "ict_tier": ict_tier_v,
            "ict_mtf_context": ict_ctx_v,
            "has_ict": has_ict,
            "strike": strike,
            "expiry": expiry,
            "entry_ltp": epf,
            "exit_ltp": xpf,
            "pnl_pct": pnl_pct,
            "pnl_abs": xpf - epf,
            "win": pnl_pct > 0,
            "ict_mult": float(sig.get("ict_size_mult") or 1.0),
        })

    print(f"\nMatched {len(enriched)}/{len(signals)} signals to entry+exit LTP")
    print(f"  Skipped: pre_coverage={pre_coverage}, no_entry={skipped_no_entry}, "
          f"no_exit={skipped_no_exit}, no_strike={skipped_no_strike}, "
          f"zero_price={skipped_zero_price}\n")

    if not enriched:
        print("*** No enriched signals — investigate option_chain_snapshots coverage ***")
        return 1

    def stats(rows):
        n = len(rows)
        if n == 0: return {"n": 0}
        pnls = sorted(s["pnl_pct"] for s in rows)
        wins = sum(1 for s in rows if s["win"])
        return {"n": n, "wins": wins, "wr": wins / n * 100,
                "mean": sum(pnls) / n, "median": pnls[n // 2],
                "min": pnls[0], "max": pnls[-1]}

    def fmt(s, label, width=42):
        if s["n"] == 0: return f"{label:<{width}} (no rows)"
        return (f"{label:<{width}} N={s['n']:>3} WR={s['wr']:>5.1f}% "
                f"Mean={s['mean']:>+7.2f}% Med={s['median']:>+7.2f}% "
                f"Range=[{s['min']:>+7.1f}%, {s['max']:>+7.1f}%]")

    print("=" * 100)
    print(f"PATH 1 v2 — LIVE COHORT P&L (8 weeks, T+30m exit, ATM strike, sig-expiry)")
    print("=" * 100)
    print(f"\nUniverse: {len(enriched)} enriched signals\n")

    ict_rows = [s for s in enriched if s["has_ict"]]
    no_ict_rows = [s for s in enriched if not s["has_ict"]]
    print("--- ICT-tagged vs no-ICT (the headline) ---")
    print(fmt(stats(ict_rows),    "ICT-tagged (live edge cohort)"))
    print(fmt(stats(no_ict_rows), "no-ICT (NONE/null pattern)"))
    print()

    print("--- Per ICT structure (pattern × action × tier × context) ---")
    by_struct = defaultdict(list)
    for s in ict_rows:
        by_struct[(s["symbol"], s["ict_pattern"], s["action"], s["ict_tier"], s["ict_mtf_context"])].append(s)
    for k in sorted(by_struct, key=lambda x: -len(by_struct[x])):
        sym, pat, act, tier, ctx = k
        print(fmt(stats(by_struct[k]), f"{sym} {pat} {act} {tier}/{ctx}"))
    print()

    print("--- Per symbol ---")
    for sym in ("NIFTY", "SENSEX"):
        print(fmt(stats([s for s in enriched if s["symbol"] == sym]), sym))
    print()

    print("--- Per trading day ---")
    by_day = defaultdict(list)
    for s in enriched:
        by_day[s["trade_date"]].append(s)
    for d in sorted(by_day):
        st = stats(by_day[d])
        day_total = sum(s["pnl_pct"] for s in by_day[d])
        print(f"{d}  N={st['n']:>3} WR={st['wr']:>5.1f}% Mean={st['mean']:>+7.2f}% "
              f"Med={st['median']:>+7.2f}% Total={day_total:>+8.2f}pp")
    print()

    total_pp = sum(s["pnl_pct"] for s in enriched)
    abs_total = sum(abs(s["pnl_pct"]) for s in enriched)
    print(f"Aggregate signal P&L (sum of per-signal pct returns): {total_pp:+.2f}pp")
    if abs_total > 0:
        day_totals = [(d, sum(s["pnl_pct"] for s in r), sum(abs(s["pnl_pct"]) for s in r))
                      for d, r in by_day.items()]
        day_totals.sort(key=lambda x: -x[2])
        print(f"Top 3 days by absolute contribution:")
        cum_abs = 0
        for d, signed, ab in day_totals[:3]:
            cum_abs += ab
            pct = ab / abs_total * 100
            print(f"  {d}  signed={signed:>+8.2f}pp  |signed|={ab:>7.2f}pp  ({pct:>5.1f}% of |total|)")
        print(f"  Top-3 cumulative |share|: {cum_abs/abs_total*100:.1f}% — "
              f"{'CONCENTRATED' if cum_abs/abs_total > 0.6 else 'distributed'}")
    print()

    print("--- With Kelly tier sizing (sum of pnl_pct × ict_size_mult) ---")
    kelly_total = sum(s["pnl_pct"] * s["ict_mult"] for s in enriched)
    kelly_ict_total = sum(s["pnl_pct"] * s["ict_mult"] for s in ict_rows)
    print(f"  Whole cohort (Kelly-weighted):  {kelly_total:+.2f}pp  (vs unweighted {total_pp:+.2f}pp)")
    print(f"  ICT-only (Kelly-weighted):      {kelly_ict_total:+.2f}pp")
    print()

    print("--- ADR-009 §S29 sub-rule check on LIVE cohort ---")
    ict_st = stats(ict_rows)
    no_ict_st = stats(no_ict_rows)
    if ict_st["n"] > 0:
        ict_med_neg = ict_st["median"] <= 0
        verdict = ("NEGATIVE → D.12.2 + D.12.6 confirmed on LIVE cohort"
                   if ict_med_neg else "POSITIVE → live cohort survives where 5m-batch fails")
        print(f"  ICT cohort median: {ict_st['median']:+.2f}%  → {verdict}")
    if no_ict_st["n"] > 0:
        no_ict_med_neg = no_ict_st["median"] <= 0
        verdict2 = "NEGATIVE" if no_ict_med_neg else "POSITIVE"
        print(f"  no-ICT cohort median: {no_ict_st['median']:+.2f}%  → {verdict2}")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
