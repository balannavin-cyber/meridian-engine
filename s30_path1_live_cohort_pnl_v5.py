#!/usr/bin/env python3
"""
s30_path1_live_cohort_pnl_v5.py — Compendium replication on live cohort (all gates unplugged).

Question: take every ICT-tagged cycle from signal_snapshots over the last 8 weeks,
ignore trade_allowed / action / all gates, derive trade direction from pattern type,
compute T+30m P&L. Does the Compendium edge (BEAR_OB ~92%, BULL_OB ~84%, MEDIUM
~77%) replicate on this cohort?

Design:
  - Source: signal_snapshots WHERE ict_pattern IN (BULL_OB, BEAR_OB, BULL_FVG, BEAR_FVG)
    AND ts >= NOW() - 8 weeks. No trade_allowed filter, no action filter.
  - Direction: BULL_* → BUY_CE, BEAR_* → BUY_PE (Compendium canon, not MERDIAN's action)
  - Strike: signal.atm_strike (live engine's preferred ATM)
  - Expiry: signal.expiry_date
  - Dedup: first cycle per (symbol, trade_date_IST, ict_pattern, atm_strike) =
    Compendium "rejection bar entry" semantics
  - P&L: T+30m from option_chain_snapshots (live) + historical_option_chain_snapshots (archive)

Run:
    python s30_path1_live_cohort_pnl_v5.py
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

ARCHIVE_CUTOVER = datetime(2026, 5, 4, tzinfo=timezone.utc)
LIVE_TABLE = "option_chain_snapshots"
ARCHIVE_TABLE = "historical_option_chain_snapshots"

ICT_PATTERNS = ["BULL_OB", "BEAR_OB", "BULL_FVG", "BEAR_FVG"]
BULL_PATTERNS = {"BULL_OB", "BULL_FVG"}

# Compendium settled numbers per CLAUDE.md
COMPENDIUM_REFERENCE = {
    "BEAR_OB": ("92%", "Settled: BEAR_OB ~92% WR (Compendium replicate)"),
    "BULL_OB": ("84%", "Settled: BULL_OB ~84% WR (Compendium replicate)"),
    "BULL_FVG": ("50%", "Settled: BULL_FVG coin flip (CI [42.5, 58.1])"),
    "BEAR_FVG": ("46%", "Settled: BEAR_FVG anti-cluster -16.5pp"),
}

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


def fetch_ict_tagged(sb: Client) -> list[dict]:
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(weeks=WINDOW_WEEKS)).isoformat()
    print(f"[1/2] Fetching all ICT-tagged signals since {cutoff_iso} (NO gate filters)...")
    out, off = [], 0
    while True:
        resp = (sb.table("signal_snapshots")
                .select("id, ts, symbol, action, trade_allowed, expiry_date, "
                        "spot, atm_strike, dte, ict_pattern, ict_tier, "
                        "ict_mtf_context, ict_size_mult, direction_bias, "
                        "gamma_regime, breadth_regime, vix_regime, "
                        "po3_session_bias")
                .in_("ict_pattern", ICT_PATTERNS)
                .gte("ts", cutoff_iso)
                .order("ts")
                .range(off, off + 999)
                .execute())
        rows = resp.data or []
        if not rows: break
        out.extend(rows)
        if len(rows) < 1000: break
        off += 1000
    print(f"      → {len(out)} ICT-tagged cycles (pre-dedup)")
    return out


def dedupe_first_per_setup(rows: list[dict]) -> list[dict]:
    """First cycle per (symbol, trade_date_IST, ict_pattern, atm_strike) — Compendium rejection-bar."""
    seen = set()
    out = []
    for r in sorted(rows, key=lambda x: x["ts"]):
        try: ts = _ts_from_str(r["ts"])
        except (KeyError, ValueError): continue
        if r.get("atm_strike") is None: continue
        trade_date = ts.astimezone(IST_TZ).date()
        key = (r["symbol"], trade_date, r["ict_pattern"], int(r["atm_strike"]))
        if key in seen: continue
        seen.add(key)
        out.append(r)
    return out


def fetch_chain_row_from_table(sb, table, symbol, strike, option_type, expiry_date, target_ts):
    lo = (target_ts - timedelta(minutes=MATCH_TOL_MIN)).isoformat()
    hi = (target_ts + timedelta(minutes=MATCH_TOL_MIN)).isoformat()
    try:
        resp = (sb.table(table)
                .select("ts, symbol, strike, option_type, expiry_date, ltp")
                .eq("symbol", symbol).eq("strike", strike)
                .eq("option_type", option_type).eq("expiry_date", expiry_date)
                .gte("ts", lo).lte("ts", hi)
                .order("ts").range(0, 99).execute())
    except Exception:
        return None
    rows = resp.data or []
    if not rows: return None
    best = None; best_delta = None
    for r in rows:
        try: rts = _ts_from_str(r["ts"])
        except (KeyError, ValueError): continue
        delta = abs((rts - target_ts).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta; best = r
    return best


def fetch_chain_row_smart(sb, symbol, strike, option_type, expiry_date, target_ts):
    primary = ARCHIVE_TABLE if target_ts < ARCHIVE_CUTOVER else LIVE_TABLE
    fallback = LIVE_TABLE if primary == ARCHIVE_TABLE else ARCHIVE_TABLE
    row = fetch_chain_row_from_table(sb, primary, symbol, strike, option_type, expiry_date, target_ts)
    if row: return row
    return fetch_chain_row_from_table(sb, fallback, symbol, strike, option_type, expiry_date, target_ts)


def main() -> int:
    sb = _load_supabase()
    raw = fetch_ict_tagged(sb)
    if not raw:
        print("\n*** No ICT-tagged signals ***"); return 0

    deduped = dedupe_first_per_setup(raw)
    print(f"      → {len(deduped)} unique setups after dedup-by-day-strike")
    print(f"      → compression ratio: {len(raw)/max(len(deduped),1):.1f}x (cycles per setup)\n")

    # Distribution by pattern × symbol before chain pricing
    print("Pre-price cohort distribution (pattern × symbol):")
    by_pat_sym = defaultdict(int)
    for r in deduped:
        by_pat_sym[(r["ict_pattern"], r["symbol"])] += 1
    for (pat, sym), n in sorted(by_pat_sym.items()):
        print(f"  {pat:<10} {sym:<8} N={n:>3}")
    print()

    print(f"[2/2] Pricing each setup (entry @ ts + exit @ ts+30m, chain routing)...")
    enriched = []
    skipped_no_strike = skipped_no_entry = skipped_no_exit = skipped_zero_price = 0
    option_type_convention = None

    for i, sig in enumerate(deduped, 1):
        if i % 20 == 0:
            print(f"      ...processed {i}/{len(deduped)}")
        try: sig_ts = _ts_from_str(sig["ts"])
        except (KeyError, ValueError): continue
        sym = sig["symbol"]
        pat = sig["ict_pattern"]
        # Compendium-canonical direction
        natural_action = "BUY_CE" if pat in BULL_PATTERNS else "BUY_PE"
        strike = sig.get("atm_strike")
        expiry = sig.get("expiry_date")
        if strike is None or not expiry:
            skipped_no_strike += 1; continue

        candidates = [("CE" if natural_action == "BUY_CE" else "PE",)]
        if option_type_convention is None:
            candidates.append(("CALL" if natural_action == "BUY_CE" else "PUT",))
        elif option_type_convention == "CALL/PUT":
            candidates = [("CALL" if natural_action == "BUY_CE" else "PUT",)]

        entry_bar = None
        for (ot,) in candidates:
            entry_bar = fetch_chain_row_smart(sb, sym, int(strike), ot, str(expiry), sig_ts)
            if entry_bar:
                conv = "CE/PE" if ot in ("CE", "PE") else "CALL/PUT"
                if option_type_convention is None: option_type_convention = conv
                break
        if entry_bar is None: skipped_no_entry += 1; continue

        ot_final = ("CE" if natural_action == "BUY_CE" else "PE") if option_type_convention == "CE/PE" else ("CALL" if natural_action == "BUY_CE" else "PUT")
        exit_bar = fetch_chain_row_smart(sb, sym, int(strike), ot_final, str(expiry),
                                          sig_ts + timedelta(minutes=EXIT_OFFSET_MIN))
        if exit_bar is None: skipped_no_exit += 1; continue

        ep_raw, xp_raw = entry_bar.get("ltp"), exit_bar.get("ltp")
        if ep_raw is None or xp_raw is None: skipped_zero_price += 1; continue
        try: epf, xpf = float(ep_raw), float(xp_raw)
        except (TypeError, ValueError): skipped_zero_price += 1; continue
        if epf <= 0: skipped_zero_price += 1; continue

        pnl_pct = (xpf - epf) / epf * 100
        enriched.append({
            "id": sig["id"], "ts": sig_ts,
            "trade_date": sig_ts.astimezone(IST_TZ).date(),
            "symbol": sym, "ict_pattern": pat,
            "natural_action": natural_action,
            "merdian_action": sig.get("action"),
            "merdian_trade_allowed": sig.get("trade_allowed"),
            "ict_tier": sig.get("ict_tier") or "NULL",
            "ict_mtf_context": sig.get("ict_mtf_context") or "NULL",
            "dte": sig.get("dte"),
            "strike": strike, "entry_ltp": epf, "exit_ltp": xpf,
            "pnl_pct": pnl_pct, "win": pnl_pct > 0,
        })

    print(f"\nMatched {len(enriched)}/{len(deduped)} setups to entry+exit LTP")
    print(f"  Skipped: no_strike={skipped_no_strike}, no_entry={skipped_no_entry}, "
          f"no_exit={skipped_no_exit}, zero_price={skipped_zero_price}\n")

    if not enriched:
        print("*** No enriched ***"); return 1

    def stats(rows):
        n = len(rows)
        if n == 0: return {"n": 0}
        pnls = sorted(s["pnl_pct"] for s in rows)
        wins = sum(1 for s in rows if s["win"])
        return {"n": n, "wins": wins, "wr": wins / n * 100,
                "mean": sum(pnls) / n, "median": pnls[n // 2],
                "min": pnls[0], "max": pnls[-1]}

    def fmt(s, label, width=32):
        if s["n"] == 0: return f"{label:<{width}} (no rows)"
        return (f"{label:<{width}} N={s['n']:>3} WR={s['wr']:>5.1f}% "
                f"Mean={s['mean']:>+7.2f}% Med={s['median']:>+7.2f}% "
                f"Range=[{s['min']:>+7.1f}%, {s['max']:>+7.1f}%]")

    print("=" * 100)
    print(f"PATH 1 v5 — PURE ICT, ALL GATES UNPLUGGED, COMPENDIUM REPLICATION (8 weeks live)")
    print("=" * 100)
    print(f"\nUniverse: {len(enriched)} setups\n")

    # ─── Pattern × symbol (the headline) ───
    print("[1] Per pattern × symbol (the headline)")
    print(f"    Compendium settled numbers in parentheses for comparison\n")
    for pat in ICT_PATTERNS:
        ref_wr, _ = COMPENDIUM_REFERENCE.get(pat, ("?", ""))
        print(f"  {pat}  (Compendium: {ref_wr})")
        for sym in ("NIFTY", "SENSEX"):
            rows = [s for s in enriched if s["ict_pattern"] == pat and s["symbol"] == sym]
            s = stats(rows)
            print("   ", fmt(s, f"{sym}", width=12))
        all_rows = [s for s in enriched if s["ict_pattern"] == pat]
        s = stats(all_rows)
        print("   ", fmt(s, "BOTH", width=12))
        print()

    # ─── Per tier ───
    print("[2] Per ICT tier × pattern (does Tier discrimination work?)")
    by_tier = defaultdict(list)
    for s in enriched:
        by_tier[(s["ict_pattern"], s["ict_tier"])].append(s)
    for (pat, tier), rows in sorted(by_tier.items()):
        if len(rows) < 3: continue
        st = stats(rows)
        print(f"  {pat:<10} tier={tier:<6} N={st['n']:>3} WR={st['wr']:>5.1f}% "
              f"Mean={st['mean']:>+7.2f}% Med={st['median']:>+7.2f}%")
    print()

    # ─── Per MTF context ───
    print("[3] Per MTF context × pattern (Compendium claim: MEDIUM ~77% beats HIGH/LOW)")
    by_ctx = defaultdict(list)
    for s in enriched:
        by_ctx[(s["ict_pattern"], s["ict_mtf_context"])].append(s)
    for (pat, ctx), rows in sorted(by_ctx.items()):
        if len(rows) < 3: continue
        st = stats(rows)
        print(f"  {pat:<10} ctx={ctx:<10} N={st['n']:>3} WR={st['wr']:>5.1f}% "
              f"Mean={st['mean']:>+7.2f}% Med={st['median']:>+7.2f}%")
    print()

    # ─── MERDIAN-allowed vs MERDIAN-blocked split within the same cohort ───
    print("[4] Compendium pure-ICT view: did MERDIAN's gates ADD value or DESTROY it?")
    merdian_allowed = [s for s in enriched if s["merdian_trade_allowed"]
                       and s["merdian_action"] == s["natural_action"]]
    merdian_blocked = [s for s in enriched if not (s["merdian_trade_allowed"]
                                                    and s["merdian_action"] == s["natural_action"])]
    print(fmt(stats(merdian_allowed), "MERDIAN allowed+aligned (gates ON)"))
    print(fmt(stats(merdian_blocked), "MERDIAN blocked or misaligned"))
    print(fmt(stats(enriched), "ALL pure-ICT (gates OFF — Compendium spec)"))
    print()

    # ─── Per-day for outlier inspection ───
    print("[5] Per trading day (concentration check)")
    by_day = defaultdict(list)
    for s in enriched:
        by_day[s["trade_date"]].append(s)
    for d in sorted(by_day):
        st = stats(by_day[d])
        print(f"  {d}  N={st['n']:>3} WR={st['wr']:>5.1f}% "
              f"Mean={st['mean']:>+7.2f}% Med={st['median']:>+7.2f}%")
    print()

    # ─── Aggregate Compendium comparison ───
    print("[6] Aggregate Compendium comparison")
    total_pp = sum(s["pnl_pct"] for s in enriched)
    print(f"  Pooled per-trade total: {total_pp:+.2f}pp across N={len(enriched)} setups")
    print(f"  Mean per-trade: {total_pp/len(enriched):+.3f}%")
    print(f"  Compendium settled: pooled +193.4% return (multi-month, different cohort)")
    print(f"  Cohort-size honesty check: 8 weeks << year; concentration likely high")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
