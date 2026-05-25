#!/usr/bin/env python3
"""
s30_target_days_audit.py — Per-setup audit on May 5, 6, 13, 14.

Operator flagged these days from charts as having clear ICT structure:
  - 2026-05-05/06: NIFTY OB → FVG stack, +300pt move
  - 2026-05-05/06: SENSEX similar structure
  - 2026-05-13/14: NIFTY OB → FVG stack
  - 2026-05-13/14: SENSEX big bullish move

Question: did MERDIAN see these setups, what direction did it suggest, was it
gated, and what would each have made at T+30m?

For each setup in the 4 days:
  - IST time, symbol, pattern, strike, spot
  - natural_action (BULL→CE, BEAR→PE) vs MERDIAN's actual action
  - trade_allowed, ict_tier, ict_mtf_context
  - gamma_regime, vix_regime, breadth_regime, direction_bias
  - T+30m P&L
  - key cautions/reasons

Run:
    python s30_target_days_audit.py
"""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta, date

from dotenv import load_dotenv  # type: ignore
from supabase import Client, create_client  # type: ignore


IST_TZ = timezone(timedelta(hours=5, minutes=30))
EXIT_OFFSET_MIN = 30
MATCH_TOL_MIN = 3

ARCHIVE_CUTOVER = datetime(2026, 5, 4, tzinfo=timezone.utc)
LIVE_TABLE = "option_chain_snapshots"
ARCHIVE_TABLE = "historical_option_chain_snapshots"

ICT_PATTERNS = ["BULL_OB", "BEAR_OB", "BULL_FVG", "BEAR_FVG"]
BULL_PATTERNS = {"BULL_OB", "BULL_FVG"}

TARGET_DAYS = [date(2026, 5, 5), date(2026, 5, 6), date(2026, 5, 13), date(2026, 5, 14)]

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


def fetch_ict_tagged_for_days(sb: Client, days: list[date]) -> list[dict]:
    # Convert IST dates to UTC range (IST date → UTC range covers 18:30 prev_day to 18:30 this_day)
    earliest = min(days)
    latest = max(days)
    lo_iso = datetime(earliest.year, earliest.month, earliest.day, 0, 0,
                       tzinfo=IST_TZ).astimezone(timezone.utc).isoformat()
    hi_iso = datetime(latest.year, latest.month, latest.day, 23, 59,
                       tzinfo=IST_TZ).astimezone(timezone.utc).isoformat()
    print(f"[1/2] Fetching ICT-tagged signals between {lo_iso} and {hi_iso} ...")
    out, off = [], 0
    while True:
        resp = (sb.table("signal_snapshots")
                .select("id, ts, symbol, action, trade_allowed, expiry_date, spot, "
                        "atm_strike, dte, ict_pattern, ict_tier, ict_mtf_context, "
                        "direction_bias, gamma_regime, breadth_regime, vix_regime, "
                        "po3_session_bias, reasons, cautions")
                .in_("ict_pattern", ICT_PATTERNS)
                .gte("ts", lo_iso).lte("ts", hi_iso)
                .order("ts").range(off, off + 999).execute())
        rows = resp.data or []
        if not rows: break
        out.extend(rows)
        if len(rows) < 1000: break
        off += 1000
    # Filter to exact target days in IST
    keep = []
    for r in out:
        try: ts = _ts_from_str(r["ts"])
        except (KeyError, ValueError): continue
        d = ts.astimezone(IST_TZ).date()
        if d in days: keep.append(r)
    print(f"      → {len(keep)} ICT-tagged cycles across target days\n")
    return keep


def dedupe_first_per_setup(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: x["ts"]):
        try: ts = _ts_from_str(r["ts"])
        except (KeyError, ValueError): continue
        if r.get("atm_strike") is None: continue
        td = ts.astimezone(IST_TZ).date()
        key = (r["symbol"], td, r["ict_pattern"], int(r["atm_strike"]))
        if key in seen: continue
        seen.add(key); out.append(r)
    return out


def fetch_chain_row_from_table(sb, table, symbol, strike, option_type, expiry_date, target_ts):
    lo = (target_ts - timedelta(minutes=MATCH_TOL_MIN)).isoformat()
    hi = (target_ts + timedelta(minutes=MATCH_TOL_MIN)).isoformat()
    try:
        resp = (sb.table(table).select("ts, ltp")
                .eq("symbol", symbol).eq("strike", strike)
                .eq("option_type", option_type).eq("expiry_date", expiry_date)
                .gte("ts", lo).lte("ts", hi).order("ts").range(0, 99).execute())
    except Exception:
        return None
    rows = resp.data or []
    if not rows: return None
    best, best_d = None, None
    for r in rows:
        try: rts = _ts_from_str(r["ts"])
        except (KeyError, ValueError): continue
        d = abs((rts - target_ts).total_seconds())
        if best_d is None or d < best_d: best_d, best = d, r
    return best


def fetch_chain_row_smart(sb, symbol, strike, option_type, expiry_date, target_ts):
    primary = ARCHIVE_TABLE if target_ts < ARCHIVE_CUTOVER else LIVE_TABLE
    fb = LIVE_TABLE if primary == ARCHIVE_TABLE else ARCHIVE_TABLE
    r = fetch_chain_row_from_table(sb, primary, symbol, strike, option_type, expiry_date, target_ts)
    if r: return r
    return fetch_chain_row_from_table(sb, fb, symbol, strike, option_type, expiry_date, target_ts)


def price_setups(sb, deduped):
    print(f"[2/2] Pricing {len(deduped)} setups...")
    enriched = []
    convention = None
    for sig in deduped:
        try: sig_ts = _ts_from_str(sig["ts"])
        except (KeyError, ValueError): continue
        sym, pat = sig["symbol"], sig["ict_pattern"]
        natural = "BUY_CE" if pat in BULL_PATTERNS else "BUY_PE"
        strike, expiry = sig.get("atm_strike"), sig.get("expiry_date")
        if strike is None or not expiry:
            sig["pnl_pct"] = None; sig["natural_action"] = natural
            enriched.append(sig); continue
        cands = [("CE" if natural == "BUY_CE" else "PE",)]
        if convention is None:
            cands.append(("CALL" if natural == "BUY_CE" else "PUT",))
        elif convention == "CALL/PUT":
            cands = [("CALL" if natural == "BUY_CE" else "PUT",)]
        eb = None
        for (ot,) in cands:
            eb = fetch_chain_row_smart(sb, sym, int(strike), ot, str(expiry), sig_ts)
            if eb:
                if convention is None:
                    convention = "CE/PE" if ot in ("CE", "PE") else "CALL/PUT"
                break
        if eb is None:
            sig["pnl_pct"] = None; sig["natural_action"] = natural
            enriched.append(sig); continue
        ot_f = ("CE" if natural == "BUY_CE" else "PE") if convention == "CE/PE" else ("CALL" if natural == "BUY_CE" else "PUT")
        xb = fetch_chain_row_smart(sb, sym, int(strike), ot_f, str(expiry),
                                    sig_ts + timedelta(minutes=EXIT_OFFSET_MIN))
        if xb is None:
            sig["pnl_pct"] = None; sig["natural_action"] = natural
            enriched.append(sig); continue
        ep, xp = eb.get("ltp"), xb.get("ltp")
        if ep is None or xp is None:
            sig["pnl_pct"] = None; sig["natural_action"] = natural
            enriched.append(sig); continue
        try: epf, xpf = float(ep), float(xp)
        except (TypeError, ValueError):
            sig["pnl_pct"] = None; sig["natural_action"] = natural
            enriched.append(sig); continue
        if epf <= 0:
            sig["pnl_pct"] = None; sig["natural_action"] = natural
            enriched.append(sig); continue
        sig["natural_action"] = natural
        sig["pnl_pct"] = (xpf - epf) / epf * 100
        sig["was_blocked"] = not (sig.get("trade_allowed") and sig.get("action") == natural)
        enriched.append(sig)
    return enriched


def main() -> int:
    sb = _load_supabase()
    raw = fetch_ict_tagged_for_days(sb, TARGET_DAYS)
    if not raw:
        print("\n*** No ICT-tagged signals in target days ***"); return 0
    deduped = dedupe_first_per_setup(raw)
    print(f"      → {len(deduped)} unique setups after dedup\n")
    enriched = price_setups(sb, deduped)
    n_priced = sum(1 for s in enriched if s.get("pnl_pct") is not None)
    print(f"      → {n_priced}/{len(enriched)} priced\n")

    print("=" * 110)
    print("TARGET DAYS AUDIT — May 5, 6, 13, 14 — per-setup detail (chart-cross-reference)")
    print("=" * 110)

    by_day = defaultdict(list)
    for s in enriched:
        try: ts = _ts_from_str(s["ts"])
        except (KeyError, ValueError): continue
        d = ts.astimezone(IST_TZ).date()
        by_day[d].append((ts, s))

    for d in sorted(by_day):
        print(f"\n=== {d} (IST) ===")
        rows = sorted(by_day[d], key=lambda x: x[0])
        # Per-symbol rollup line first
        for sym in ("NIFTY", "SENSEX"):
            sym_rows = [(t, s) for t, s in rows if s["symbol"] == sym]
            if not sym_rows: continue
            priced = [s for _, s in sym_rows if s.get("pnl_pct") is not None]
            if priced:
                wins = sum(1 for s in priced if s["pnl_pct"] > 0)
                mean = sum(s["pnl_pct"] for s in priced) / len(priced)
                pooled = sum(s["pnl_pct"] for s in priced)
                blocked = sum(1 for s in priced if s.get("was_blocked"))
                print(f"  {sym}: N={len(sym_rows)} setups ({len(priced)} priced), "
                      f"WR={wins/len(priced)*100:.1f}%, mean={mean:+.2f}%, pooled={pooled:+.2f}pp, "
                      f"blocked-by-gates={blocked}/{len(priced)}")
            else:
                print(f"  {sym}: N={len(sym_rows)} setups (none priced)")
        # Per-setup detail
        print(f"  {'IST_time':<8} {'Sym':<7} {'Pattern':<9} {'Strike':<6} {'Spot':<8} "
              f"{'Natural':<8} {'MERDIAN':<10} {'Allow':<5} {'Dir':<8} {'Gamma':<13} "
              f"{'VIX':<8} {'Breadth':<8} {'P&L%':<8}")
        print("  " + "-" * 108)
        for ts, s in rows:
            t = ts.astimezone(IST_TZ).strftime("%H:%M")
            pnl = f"{s['pnl_pct']:>+.2f}" if s.get("pnl_pct") is not None else "  N/A"
            allow_str = "Y" if s.get("trade_allowed") else "N"
            merdian_act = s.get("action") or "—"
            blocked_mark = "*" if s.get("was_blocked") else " "
            print(f"  {t:<8} {s['symbol']:<7} {s['ict_pattern']:<9} "
                  f"{str(s.get('atm_strike','')):<6} {str(s.get('spot','')):<8} "
                  f"{s.get('natural_action','—'):<8} {merdian_act:<10}{blocked_mark} {allow_str:<4} "
                  f"{(s.get('direction_bias','—') or '—'):<8} "
                  f"{(s.get('gamma_regime','—') or '—'):<13} "
                  f"{(s.get('vix_regime','—') or '—'):<8} "
                  f"{(s.get('breadth_regime','—') or '—'):<8} {pnl:<8}")

    # ─── Cross-day rollup ───
    print("\n" + "=" * 110)
    print("CROSS-DAY ROLLUP (4 target days)")
    print("=" * 110)
    priced = [s for s in enriched if s.get("pnl_pct") is not None]
    for sym in ("NIFTY", "SENSEX"):
        sr = [s for s in priced if s["symbol"] == sym]
        if not sr: continue
        wins = sum(1 for s in sr if s["pnl_pct"] > 0)
        mean = sum(s["pnl_pct"] for s in sr) / len(sr)
        pooled = sum(s["pnl_pct"] for s in sr)
        blocked = sum(1 for s in sr if s.get("was_blocked"))
        print(f"  {sym} (4 days): N={len(sr)}, WR={wins/len(sr)*100:.1f}%, "
              f"mean={mean:+.2f}%, pooled={pooled:+.2f}pp, "
              f"blocked-by-gates={blocked}/{len(sr)} ({blocked/len(sr)*100:.0f}%)")
    if priced:
        wins = sum(1 for s in priced if s["pnl_pct"] > 0)
        mean = sum(s["pnl_pct"] for s in priced) / len(priced)
        pooled = sum(s["pnl_pct"] for s in priced)
        blocked = sum(1 for s in priced if s.get("was_blocked"))
        print(f"  TOTAL (4 days): N={len(priced)}, WR={wins/len(priced)*100:.1f}%, "
              f"mean={mean:+.2f}%, pooled={pooled:+.2f}pp, blocked={blocked}/{len(priced)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
