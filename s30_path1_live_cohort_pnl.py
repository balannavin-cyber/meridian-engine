#!/usr/bin/env python3
"""
s30_path1_live_cohort_pnl.py — Path 1 answer to "where does MERDIAN actually stand".

Computes T+30m option P&L on every `trade_allowed=TRUE AND action IN ('BUY_CE','BUY_PE')`
signal from `signal_snapshots` over the last 8 weeks, joined to `hist_atm_option_bars_5m`
for entry/exit LTP. Reports by ICT structure, by day, with concentration check.

This is the LIVE cohort answer — directly addresses operator's S30 strategic-fork
Option 3: "is the median-negative property real on the live signal cohort, or an
artifact of the 5m-batch hist_pattern_signals cohort that Phase 0b tested?"

Constraints honored:
  - 30m exit (Exp 8/14b/15 sweet spot, Settled in CLAUDE.md)
  - hist_atm_option_bars_5m current-week ATM (matches Exp 41 finding: current-week PE
    beats next-week PE for PDH DTE<3, Settled in CLAUDE.md)
  - Live cohort = signal_snapshots (not hist_pattern_signals — distinction per S16 B11)

Run:
    python s30_path1_live_cohort_pnl.py
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, date, timezone, timedelta

from dotenv import load_dotenv  # type: ignore
from supabase import Client, create_client  # type: ignore


SPOT_INSTRUMENT_ID = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}
INSTRUMENT_TO_SYMBOL = {v: k for k, v in SPOT_INSTRUMENT_ID.items()}
IST_TZ = timezone(timedelta(hours=5, minutes=30))
EXIT_OFFSET_MIN = 30
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


def _floor_5min(ts: datetime) -> datetime:
    return ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)


def _load_supabase() -> Client:
    load_dotenv(override=False)
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not url or not key:
        raise RuntimeError("SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


def _paginated(qb, page=1000):
    out, off = [], 0
    while True:
        resp = qb.range(off, off + page - 1).execute()
        rows = resp.data or []
        if not rows: break
        out.extend(rows)
        if len(rows) < page: break
        off += page
    return out


def fetch_signals(sb: Client) -> list[dict]:
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(weeks=WINDOW_WEEKS)).isoformat()
    print(f"[1/2] Fetching trade_allowed signals since {cutoff_iso}...")
    q = (sb.table("signal_snapshots")
         .select("id, ts, symbol, action, expiry_date, spot, dte, "
                 "ict_pattern, ict_tier, ict_mtf_context, ict_size_mult, "
                 "po3_session_bias, direction_bias, confidence_score, "
                 "gamma_regime, breadth_regime, vix_regime")
         .eq("trade_allowed", True)
         .in_("action", ["BUY_CE", "BUY_PE"])
         .gte("ts", cutoff_iso)
         .order("ts"))
    rows = _paginated(q)
    print(f"      → {len(rows)} actionable trade_allowed signals (BUY_CE/BUY_PE only)")
    return rows


def fetch_atm_options(sb: Client, since_iso: str) -> dict[tuple[str, datetime], dict]:
    """{(symbol, bar_ts_as_stored): row}. Caller is responsible for current-week selection."""
    print(f"[2/2] Fetching hist_atm_option_bars_5m since {since_iso}...")
    # Window: 1 day before earliest signal → 1 day after latest signal (cover 30-min exit)
    q = (sb.table("hist_atm_option_bars_5m")
         .select("instrument_id, bar_ts, expiry_date, atm_strike, ce_close, pe_close")
         .gte("bar_ts", since_iso))
    rows = _paginated(q)
    grouped: dict[tuple[str, datetime], list[dict]] = defaultdict(list)
    for r in rows:
        sym = INSTRUMENT_TO_SYMBOL.get(r.get("instrument_id"))
        if sym is None: continue
        try: bts = _ts_from_str(r["bar_ts"])
        except (KeyError, ValueError): continue
        grouped[(sym, bts)].append(r)
    # Pick current-week (smallest expiry >= trade_date) per (sym, bar_ts)
    out: dict[tuple[str, datetime], dict] = {}
    for key, cands in grouped.items():
        sym, bts = key
        trade_date = bts.date()
        eligible = []
        for c in cands:
            try: exp = date.fromisoformat(str(c["expiry_date"]))
            except (KeyError, ValueError, TypeError): continue
            if exp >= trade_date:
                eligible.append((exp, c))
        if eligible:
            eligible.sort(key=lambda x: x[0])
            out[key] = eligible[0][1]
    print(f"      → {len(out)} ATM bar entries (current-week selection)")
    return out


def main() -> int:
    sb = _load_supabase()
    signals = fetch_signals(sb)
    if not signals:
        print("\n*** No actionable trade_allowed signals in 8-week window ***")
        return 0

    earliest_sig = min(_ts_from_str(s["ts"]) for s in signals)
    since_iso = (earliest_sig - timedelta(days=1)).isoformat()
    atm = fetch_atm_options(sb, since_iso)

    # Match signal ts → ATM bar.
    # signal_snapshots.ts is real UTC (post-04-07 era for the 8-week window).
    # hist_atm_option_bars_5m.bar_ts convention: try real-UTC match first, then IST-as-UTC.
    enriched = []
    skipped_no_entry = skipped_no_exit = skipped_zero_price = 0
    convention_real_utc_hits = convention_ist_labeled_hits = 0

    for sig in signals:
        try: sig_ts = _ts_from_str(sig["ts"])
        except (KeyError, ValueError): continue
        sym = sig["symbol"]
        act = sig["action"]

        entry_bts_real = _floor_5min(sig_ts)
        exit_bts_real = entry_bts_real + timedelta(minutes=EXIT_OFFSET_MIN)

        # Try real-UTC convention first
        entry_bar = atm.get((sym, entry_bts_real))
        exit_bar = atm.get((sym, exit_bts_real))
        if entry_bar and exit_bar:
            convention_real_utc_hits += 1
        else:
            # Try IST-labeled-as-UTC convention (legacy): the stored bar_ts equals
            # signal_ts converted to IST clock-time, then labeled UTC.
            sig_ts_ist = sig_ts.astimezone(IST_TZ).replace(tzinfo=timezone.utc)
            entry_bts_ist = _floor_5min(sig_ts_ist)
            exit_bts_ist = entry_bts_ist + timedelta(minutes=EXIT_OFFSET_MIN)
            entry_bar2 = atm.get((sym, entry_bts_ist))
            exit_bar2 = atm.get((sym, exit_bts_ist))
            if entry_bar2 and exit_bar2:
                entry_bar, exit_bar = entry_bar2, exit_bar2
                convention_ist_labeled_hits += 1

        if entry_bar is None:
            skipped_no_entry += 1
            continue
        if exit_bar is None:
            skipped_no_exit += 1
            continue

        if act == "BUY_CE":
            ep, xp = entry_bar.get("ce_close"), exit_bar.get("ce_close")
        else:  # BUY_PE
            ep, xp = entry_bar.get("pe_close"), exit_bar.get("pe_close")
        if ep is None or xp is None:
            skipped_zero_price += 1
            continue
        try:
            epf, xpf = float(ep), float(xp)
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
            "entry_strike": entry_bar.get("atm_strike"),
            "expiry": entry_bar.get("expiry_date"),
            "entry_ltp": epf,
            "exit_ltp": xpf,
            "pnl_pct": pnl_pct,
            "pnl_abs": xpf - epf,
            "win": pnl_pct > 0,
            "gamma_regime": sig.get("gamma_regime"),
            "po3_session_bias": sig.get("po3_session_bias"),
            "ict_mult": float(sig.get("ict_size_mult") or 1.0),
        })

    print(f"\nMatched {len(enriched)}/{len(signals)} signals to entry+exit LTP")
    print(f"  Convention match: real-UTC {convention_real_utc_hits} | IST-labeled-UTC {convention_ist_labeled_hits}")
    print(f"  Skipped: no_entry={skipped_no_entry}, no_exit={skipped_no_exit}, zero_price={skipped_zero_price}\n")

    if not enriched:
        print("*** No enriched signals — option data unavailable for any signal ***")
        return 1

    def stats(rows: list[dict]) -> dict:
        n = len(rows)
        if n == 0: return {"n": 0}
        pnls = sorted(s["pnl_pct"] for s in rows)
        wins = sum(1 for s in rows if s["win"])
        return {
            "n": n, "wins": wins, "wr": wins / n * 100,
            "mean": sum(pnls) / n,
            "median": pnls[n // 2],
            "min": pnls[0], "max": pnls[-1],
        }

    def fmt(s: dict, label: str, width: int = 36) -> str:
        if s["n"] == 0:
            return f"{label:<{width}} (no rows)"
        return (f"{label:<{width}} N={s['n']:>3} WR={s['wr']:>5.1f}% "
                f"Mean={s['mean']:>+7.2f}% Med={s['median']:>+7.2f}% "
                f"Range=[{s['min']:>+7.1f}%, {s['max']:>+7.1f}%]")

    print("=" * 100)
    print(f"PATH 1 — LIVE COHORT P&L (8 weeks, T+30m exit, current-week ATM)")
    print("=" * 100)
    print(f"\nUniverse: {len(enriched)} enriched signals\n")

    # ICT vs no-ICT split
    ict_rows = [s for s in enriched if s["has_ict"]]
    no_ict_rows = [s for s in enriched if not s["has_ict"]]
    print("--- ICT-tagged vs no-ICT (the headline) ---")
    print(fmt(stats(ict_rows),    "ICT-tagged (live edge cohort)"))
    print(fmt(stats(no_ict_rows), "no-ICT (NONE/null pattern)"))
    print()

    # Per ICT-structure breakdown
    print("--- Per ICT structure (pattern × action × tier × context) ---")
    by_struct: dict[tuple, list] = defaultdict(list)
    for s in ict_rows:
        by_struct[(s["symbol"], s["ict_pattern"], s["action"], s["ict_tier"], s["ict_mtf_context"])].append(s)
    for k in sorted(by_struct, key=lambda x: -len(by_struct[x])):
        sym, pat, act, tier, ctx = k
        label = f"{sym} {pat} {act} {tier}/{ctx}"
        print(fmt(stats(by_struct[k]), label, width=42))
    print()

    # Per-symbol
    print("--- Per symbol ---")
    for sym in ("NIFTY", "SENSEX"):
        s_rows = [s for s in enriched if s["symbol"] == sym]
        print(fmt(stats(s_rows), sym, width=20))
    print()

    # Per-day (concentration check)
    print("--- Per trading day (concentration check) ---")
    by_day = defaultdict(list)
    for s in enriched:
        by_day[s["trade_date"]].append(s)
    for d in sorted(by_day):
        st = stats(by_day[d])
        day_pnl_total = sum(s["pnl_pct"] for s in by_day[d])
        print(f"{d}  N={st['n']:>3} WR={st['wr']:>5.1f}% Mean={st['mean']:>+7.2f}% "
              f"Total={day_pnl_total:>+8.2f}pp")
    print()

    # Concentration: top-day share of total absolute P&L (in pct-pts)
    total_pp = sum(s["pnl_pct"] for s in enriched)
    abs_total = sum(abs(s["pnl_pct"]) for s in enriched)
    print(f"Aggregate signal P&L (sum of per-signal pct returns): {total_pp:+.2f}pp")
    if abs_total > 0:
        day_totals = [(d, sum(s["pnl_pct"] for s in r), sum(abs(s["pnl_pct"]) for s in r))
                      for d, r in by_day.items()]
        day_totals.sort(key=lambda x: -x[2])
        print(f"Top 3 days by absolute contribution to aggregate:")
        cum_abs = 0
        for d, signed, ab in day_totals[:3]:
            cum_abs += ab
            print(f"  {d}  signed={signed:>+8.2f}pp  |signed|={ab:>7.2f}pp  "
                  f"({ab/abs_total*100:>4.1f}% of |aggregate|)")
        print(f"  Top-3 cumulative |share|: {cum_abs/abs_total*100:.1f}% — "
              f"{'CONCENTRATED' if cum_abs/abs_total > 0.6 else 'distributed'}")
    print()

    # Kelly sizing applied (operator's actual exposure)
    print("--- With Kelly tier sizing applied (sum of pnl_pct × ict_size_mult) ---")
    kelly_total = sum(s["pnl_pct"] * s["ict_mult"] for s in enriched)
    kelly_ict_total = sum(s["pnl_pct"] * s["ict_mult"] for s in ict_rows)
    print(f"  Whole cohort (Kelly-weighted):  {kelly_total:+.2f}pp  (vs unweighted {total_pp:+.2f}pp)")
    print(f"  ICT-only (Kelly-weighted):      {kelly_ict_total:+.2f}pp")
    print()

    # Verdict / framing per ADR-009 §S29 sub-rule
    print("--- ADR-009 §S29 sub-rule check on LIVE cohort ---")
    ict_st = stats(ict_rows)
    no_ict_st = stats(no_ict_rows)
    if ict_st["n"] > 0:
        ict_median_neg = ict_st["median"] <= 0
        print(f"  ICT cohort median: {ict_st['median']:+.2f}%  → "
              f"{'NEGATIVE (D.12.2 + D.12.6 confirmed on LIVE cohort)' if ict_median_neg else 'POSITIVE (live cohort survives where 5m-batch cohort fails)'}")
    if no_ict_st["n"] > 0:
        print(f"  no-ICT cohort median: {no_ict_st['median']:+.2f}%")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
