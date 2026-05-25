"""
s31_no_gate_pnl_test.py — counterfactual P&L if all gates unplugged.

Question: For every signal_snapshots row in last 8 weeks, what would
total P&L have been if MERDIAN had executed every directional signal
without any gate intervention?

Data sources (LIVE-CAPTURED ONLY, NO BACKFILL DEPENDENCY):
  - signal_snapshots: cycle-by-cycle production output. Reads:
      ts, symbol, direction_bias, atm_strike, expiry_date,
      action, trade_allowed
    Does NOT read: ict_pattern, ict_tier, ict_size_mult, ict_mtf_context
    (the fields the S31 backfill touched).
  - option_chain_snapshots + historical_option_chain_snapshots:
    live Dhan captures, never backfilled.
  - instruments: lot_size lookup.

Methodology:
  - Cohort: all signal_snapshots in window, both symbols
  - Natural action: BUY_CE if direction_bias=BULLISH, BUY_PE if BEARISH,
    NO-TRADE if NEUTRAL/UNKNOWN
  - Dedup: first per (symbol, IST date, direction_bias, atm_strike)
  - Entry: chain snapshot ±3min of signal_ts
  - Exit:  chain snapshot ±3min of signal_ts + 30min
  - pnl_pct = (xpf - epf) / epf * 100
  - pnl_abs = (xpf - epf) * lot_size  (₹ for 1 lot)

Output buckets (no other slicing):
  1. ALL SETUPS — every directional signal, gates ignored
  2. MERDIAN TRADED — subset where trade_allowed=true AND action != DO_NOTHING
                      AND action matches natural-action direction
  3. MERDIAN BLOCKED — complement of (2): counterfactual P&L of blocks
  4. Per symbol breakdown of (1)

No transaction costs modeled. No slippage. 1 lot per setup. 30-min hold.

Usage:
    python s31_no_gate_pnl_test.py
    python s31_no_gate_pnl_test.py --start-date 2026-03-23 --end-date 2026-05-15
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client


IST = timezone(timedelta(hours=5, minutes=30))
EXIT_OFFSET_MIN = 30
MATCH_TOL_MIN = 3
ARCHIVE_CUTOVER = datetime(2026, 5, 4, tzinfo=timezone.utc)
LIVE_TABLE = "option_chain_snapshots"
ARCHIVE_TABLE = "historical_option_chain_snapshots"

_MS_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")


# ── Args ──────────────────────────────────────────────────────────────

p = argparse.ArgumentParser()
p.add_argument("--start-date", default="2026-03-23")
p.add_argument("--end-date", default="2026-05-15")
p.add_argument("--symbols", default="NIFTY,SENSEX")
args = p.parse_args()

SYMBOLS = [s.strip().upper() for s in args.symbols.split(",")]


# ── Supabase ──────────────────────────────────────────────────────────

load_dotenv()
SB = create_client(
    os.getenv("SUPABASE_URL").strip(),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip(),
)


# ── Helpers ──────────────────────────────────────────────────────────

def _norm_us(s):
    m = _MS_RE.search(s)
    if not m:
        return s
    frac, tz = m.group(1), (m.group(2) or "")
    if len(frac) == 6:
        return s
    frac6 = frac.ljust(6, "0") if len(frac) < 6 else frac[:6]
    return _MS_RE.sub(f".{frac6}{tz}", s)


def parse_ts(s):
    if not s:
        return None
    s = _norm_us(s.replace(" ", "T").replace("Z", "+00:00"))
    if s.endswith("+00"):
        s = s[:-3] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def ist_date(ts_str):
    dt = parse_ts(ts_str)
    return dt.astimezone(IST).date().isoformat() if dt else ""


def wilson_ci(wins, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - spread) / denom * 100,
            (centre + spread) / denom * 100)


# ── Lot size lookup ──────────────────────────────────────────────────

def fetch_lot_sizes():
    rows = (SB.table("instruments")
            .select("symbol,lot_size")
            .in_("symbol", SYMBOLS)
            .execute().data)
    return {r["symbol"]: int(r["lot_size"]) for r in rows}


# ── Cohort fetch ─────────────────────────────────────────────────────

def fetch_signals():
    out, page = [], 0
    PAGE = 1000
    cols = ("id,ts,symbol,direction_bias,atm_strike,expiry_date,"
            "action,trade_allowed")
    while True:
        rows = (SB.table("signal_snapshots")
                .select(cols)
                .in_("symbol", SYMBOLS)
                .gte("ts", f"{args.start_date}T00:00:00+00:00")
                .lte("ts", f"{args.end_date}T23:59:59+00:00")
                .order("ts")
                .range(page * PAGE, (page + 1) * PAGE - 1)
                .execute().data)
        if not rows:
            break
        out.extend(rows)
        if len(rows) < PAGE:
            break
        page += 1
    return out


def derive_natural_action(direction_bias):
    db = (direction_bias or "").upper()
    if db == "BULLISH":
        return "BUY_CE"
    if db == "BEARISH":
        return "BUY_PE"
    return None  # NEUTRAL/UNKNOWN/etc — no directional signal at all


def dedupe(rows):
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: x.get("ts") or ""):
        if r.get("atm_strike") is None or not r.get("expiry_date"):
            continue
        natural = derive_natural_action(r.get("direction_bias"))
        if natural is None:
            continue
        d = ist_date(r["ts"])
        key = (r["symbol"], d, r["direction_bias"], int(r["atm_strike"]))
        if key in seen:
            continue
        seen.add(key)
        r["_natural_action"] = natural
        out.append(r)
    return out


# ── Pricing ──────────────────────────────────────────────────────────

def _fetch_chain(table, sym, strike, opt_type, expiry, target_ts):
    lo = (target_ts - timedelta(minutes=MATCH_TOL_MIN)).isoformat()
    hi = (target_ts + timedelta(minutes=MATCH_TOL_MIN)).isoformat()
    try:
        rows = (SB.table(table)
                .select("ts,ltp")
                .eq("symbol", sym).eq("strike", strike)
                .eq("option_type", opt_type).eq("expiry_date", expiry)
                .gte("ts", lo).lte("ts", hi)
                .order("ts").range(0, 99).execute().data)
    except Exception:
        return None
    if not rows:
        return None
    best, best_d = None, None
    for r in rows:
        rts = parse_ts(r["ts"])
        if rts is None:
            continue
        d = abs((rts - target_ts).total_seconds())
        if best_d is None or d < best_d:
            best_d, best = d, r
    return best


_CONVENTION = [None]


def fetch_chain_smart(sym, strike, opt_type, expiry, target_ts):
    primary = ARCHIVE_TABLE if target_ts < ARCHIVE_CUTOVER else LIVE_TABLE
    fb = LIVE_TABLE if primary == ARCHIVE_TABLE else ARCHIVE_TABLE
    r = _fetch_chain(primary, sym, strike, opt_type, expiry, target_ts)
    if r:
        return r
    return _fetch_chain(fb, sym, strike, opt_type, expiry, target_ts)


def price_setup(sig, lot_sizes):
    sig_ts = parse_ts(sig["ts"])
    if sig_ts is None:
        return None
    natural = sig["_natural_action"]
    sym = sig["symbol"]
    strike = int(sig["atm_strike"])
    expiry = str(sig["expiry_date"])

    # Convention detection
    if _CONVENTION[0]:
        ot = ("CE" if natural == "BUY_CE" else "PE") if _CONVENTION[0] == "CE/PE" \
             else ("CALL" if natural == "BUY_CE" else "PUT")
        cands = [ot]
    else:
        cands = ["CE" if natural == "BUY_CE" else "PE",
                 "CALL" if natural == "BUY_CE" else "PUT"]

    eb = None
    chosen = None
    for ot in cands:
        r = fetch_chain_smart(sym, strike, ot, expiry, sig_ts)
        if r:
            eb = r
            chosen = ot
            if _CONVENTION[0] is None:
                _CONVENTION[0] = "CE/PE" if ot in ("CE", "PE") else "CALL/PUT"
            break
    if eb is None:
        return None

    xb = fetch_chain_smart(sym, strike, chosen, expiry,
                           sig_ts + timedelta(minutes=EXIT_OFFSET_MIN))
    if xb is None:
        return None

    try:
        epf, xpf = float(eb["ltp"]), float(xb["ltp"])
    except (TypeError, ValueError):
        return None
    if epf <= 0:
        return None

    lot = lot_sizes.get(sym, 1)
    return {
        "pnl_pct": (xpf - epf) / epf * 100,
        "pnl_abs": (xpf - epf) * lot,
        "win": xpf > epf,
        "entry_px": epf,
        "exit_px": xpf,
    }


# ── Summary ──────────────────────────────────────────────────────────

def summarize(group, label):
    n = len(group)
    if n == 0:
        return f"{label:<35} N=  0  (no priced setups)"
    wins = sum(1 for g in group if g["win"])
    wr = wins / n * 100
    lo, hi = wilson_ci(wins, n)
    pnls_pct = sorted(g["pnl_pct"] for g in group)
    pnls_abs = sorted(g["pnl_abs"] for g in group)
    sum_pct = sum(pnls_pct)
    sum_abs = sum(pnls_abs)
    mean_pct = sum_pct / n
    median_pct = pnls_pct[n // 2]
    return (f"{label:<35} N={n:>4}  Wins={wins:>4}  WR={wr:>5.1f}% "
            f"[{lo:>5.1f}-{hi:>5.1f}]  "
            f"SumPct={sum_pct:>+9.1f}%  SumAbs=Rs.{sum_abs:>+11,.0f}  "
            f"Mean={mean_pct:>+6.2f}%  Med={median_pct:>+6.2f}%")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print(f"S31 no-gate counterfactual P&L test")
    print(f"Cohort: {args.start_date} -> {args.end_date}  symbols={SYMBOLS}")
    print(f"Assumptions: 1 lot per setup, 30-min hold, no costs/slippage")
    print(f"Data source: signal_snapshots (live), "
          f"option_chain_snapshots + historical_option_chain_snapshots (live)")
    print(f"NOT used: ict_pattern/ict_tier/ict_size_mult/ict_mtf_context "
          f"(backfilled fields excluded)")
    print()

    lot_sizes = fetch_lot_sizes()
    print(f"Lot sizes: {lot_sizes}")
    print()

    print(f"Fetching signal_snapshots ...", end=" ", flush=True)
    raw = fetch_signals()
    print(f"{len(raw):,}")

    print(f"After dedup (first per symbol-IST_date-direction-strike, "
          f"NEUTRAL excluded) ...", end=" ", flush=True)
    deduped = dedupe(raw)
    print(f"{len(deduped):,}")
    print()

    print(f"Pricing {len(deduped):,} setups ...")
    enriched = []
    for i, sig in enumerate(deduped, 1):
        if i % 100 == 0:
            print(f"  ... {i:,}/{len(deduped):,}  priced={len(enriched):,}",
                  flush=True)
        p_ = price_setup(sig, lot_sizes)
        if p_ is None:
            continue
        e = dict(sig)
        e.update(p_)
        enriched.append(e)
    print(f"  Priced {len(enriched):,}/{len(deduped):,}")
    print()

    if not enriched:
        print("No priced setups. Abort.")
        return 1

    # ── Bucket: MERDIAN traded vs blocked ────────────────────────────
    traded = []
    blocked = []
    for e in enriched:
        natural = e["_natural_action"]
        merdian_traded = (
            bool(e.get("trade_allowed"))
            and (e.get("action") or "").upper() == natural
        )
        if merdian_traded:
            traded.append(e)
        else:
            blocked.append(e)

    # ── Output ───────────────────────────────────────────────────────
    print("=" * 140)
    print(f"RESULT — counterfactual P&L over {args.start_date} to {args.end_date}")
    print("=" * 140)
    print()
    print(summarize(enriched, "ALL setups (no-gate counterfactual)"))
    print(summarize(traded,   "MERDIAN actually traded"))
    print(summarize(blocked,  "MERDIAN blocked (gates fired)"))
    print()

    print("Per symbol — no-gate counterfactual:")
    by_sym = defaultdict(list)
    for e in enriched:
        by_sym[e["symbol"]].append(e)
    for sym in sorted(by_sym):
        print(summarize(by_sym[sym], f"  {sym}"))
    print()

    print("Per symbol — MERDIAN traded subset:")
    by_sym_t = defaultdict(list)
    for e in traded:
        by_sym_t[e["symbol"]].append(e)
    for sym in sorted(by_sym_t):
        print(summarize(by_sym_t[sym], f"  {sym}"))
    print()

    print("Per symbol — MERDIAN blocked subset:")
    by_sym_b = defaultdict(list)
    for e in blocked:
        by_sym_b[e["symbol"]].append(e)
    for sym in sorted(by_sym_b):
        print(summarize(by_sym_b[sym], f"  {sym}"))
    print()

    # ── The single headline number ───────────────────────────────────
    sum_all_abs = sum(e["pnl_abs"] for e in enriched)
    sum_traded_abs = sum(e["pnl_abs"] for e in traded)
    sum_blocked_abs = sum(e["pnl_abs"] for e in blocked)
    print("=" * 140)
    print(f"HEADLINE — total P&L in Rupees, 1 lot per setup, 30-min hold:")
    print(f"  All gates unplugged (every directional signal executed): "
          f"Rs.{sum_all_abs:>+14,.0f}")
    print(f"  MERDIAN actually traded:                                 "
          f"Rs.{sum_traded_abs:>+14,.0f}")
    print(f"  Counterfactual P&L of blocked trades (gate cost/savings):"
          f"Rs.{sum_blocked_abs:>+14,.0f}")
    print("=" * 140)
    return 0


if __name__ == "__main__":
    sys.exit(main())
