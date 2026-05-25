#!/usr/bin/env python3
"""
s30_path1_live_cohort_pnl_v4.py — Path 1 v4 with persistence × P&L diagnostic.

Q5 from S30 — "even if MERDIAN signal didn't sustain, what was the P&L if held
to T+30m anyway?" The answer determines whether early flips are informative or
noise:
  - If flipped-early signals show WORSE P&L → flip is informative; exit early.
  - If flipped-early signals show SIMILAR/BETTER P&L → flip is noise; hold to
    30m as Exp 15 recommends.

v4 adds:
  - Per-signal `held_cycles_30m` count (same as L4 query): how many of the next
    6 5-min cycles maintained (symbol, action, trade_allowed=TRUE)
  - P&L breakdown by persistence band:
      flipped < 10m (held 0-1)
      flipped 10-20m (held 2-3)
      held ≥ 20m (held 4-5)
      held full 30m (held 6+)

Same data path as v3: archive + live option_chain routing.

Run:
    python s30_path1_live_cohort_pnl_v4.py
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
    print(f"[1/3] Fetching trade_allowed signals since {cutoff_iso}...")
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
    print(f"      → {len(out)} actionable trade_allowed signals")
    return out


def fetch_persistence(sb: Client, entries: list[dict]) -> dict[int, int]:
    """For each entry, count how many of the next 6 cycles (30m) maintained
    (symbol, action, trade_allowed=TRUE). Returns {entry_id: held_cycles}."""
    print(f"[2/3] Computing per-signal persistence (next-30m hold count)...")
    out = {}
    for i, e in enumerate(entries, 1):
        if i % 20 == 0:
            print(f"      ...processed {i}/{len(entries)}")
        try: e_ts = _ts_from_str(e["ts"])
        except (KeyError, ValueError): continue
        end_iso = (e_ts + timedelta(minutes=30)).isoformat()
        try:
            resp = (sb.table("signal_snapshots")
                    .select("id", count="exact")
                    .eq("symbol", e["symbol"])
                    .eq("action", e["action"])
                    .eq("trade_allowed", True)
                    .gt("ts", e["ts"])
                    .lte("ts", end_iso)
                    .execute())
            out[e["id"]] = resp.count if resp.count is not None else len(resp.data or [])
        except Exception:
            out[e["id"]] = 0
    return out


def fetch_chain_row_from_table(sb: Client, table: str, symbol: str, strike: int,
                                option_type: str, expiry_date: str,
                                target_ts: datetime) -> dict | None:
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


def fetch_chain_row_smart(sb: Client, symbol: str, strike: int, option_type: str,
                          expiry_date: str, target_ts: datetime) -> dict | None:
    primary = ARCHIVE_TABLE if target_ts < ARCHIVE_CUTOVER else LIVE_TABLE
    fallback = LIVE_TABLE if primary == ARCHIVE_TABLE else ARCHIVE_TABLE
    row = fetch_chain_row_from_table(sb, primary, symbol, strike, option_type, expiry_date, target_ts)
    if row: return row
    return fetch_chain_row_from_table(sb, fallback, symbol, strike, option_type, expiry_date, target_ts)


def persistence_band(held: int) -> str:
    if held <= 1: return "A_flipped_<10m"
    if held <= 3: return "B_flipped_10-20m"
    if held <= 5: return "C_held_20-30m"
    return "D_held_full_30m+"


def main() -> int:
    sb = _load_supabase()
    signals = fetch_signals(sb)
    if not signals:
        print("\n*** No signals ***"); return 0

    persistence = fetch_persistence(sb, signals)
    print(f"      → persistence counts collected for {len(persistence)} entries\n")

    print(f"[3/3] Per-signal join (archive + live routing)...")
    enriched = []
    skipped_no_entry = skipped_no_exit = skipped_no_strike = skipped_zero_price = 0
    option_type_convention = None

    for i, sig in enumerate(signals, 1):
        if i % 10 == 0:
            print(f"      ...processed {i}/{len(signals)}")
        try: sig_ts = _ts_from_str(sig["ts"])
        except (KeyError, ValueError): continue
        sym = sig["symbol"]; act = sig["action"]
        strike = sig.get("atm_strike")
        if strike is None: skipped_no_strike += 1; continue
        expiry = sig.get("expiry_date")
        if not expiry: skipped_no_strike += 1; continue

        candidates = [("CE" if act == "BUY_CE" else "PE",)]
        if option_type_convention is None:
            candidates.append(("CALL" if act == "BUY_CE" else "PUT",))
        elif option_type_convention == "CALL/PUT":
            candidates = [("CALL" if act == "BUY_CE" else "PUT",)]

        entry_bar = None
        for (ot,) in candidates:
            entry_bar = fetch_chain_row_smart(sb, sym, int(strike), ot, str(expiry), sig_ts)
            if entry_bar:
                conv = "CE/PE" if ot in ("CE", "PE") else "CALL/PUT"
                if option_type_convention is None: option_type_convention = conv
                break
        if entry_bar is None: skipped_no_entry += 1; continue

        ot_final = ("CE" if act == "BUY_CE" else "PE") if option_type_convention == "CE/PE" else ("CALL" if act == "BUY_CE" else "PUT")
        exit_bar = fetch_chain_row_smart(sb, sym, int(strike), ot_final, str(expiry),
                                          sig_ts + timedelta(minutes=EXIT_OFFSET_MIN))
        if exit_bar is None: skipped_no_exit += 1; continue

        ep_raw, xp_raw = entry_bar.get("ltp"), exit_bar.get("ltp")
        if ep_raw is None or xp_raw is None: skipped_zero_price += 1; continue
        try: epf, xpf = float(ep_raw), float(xp_raw)
        except (TypeError, ValueError): skipped_zero_price += 1; continue
        if epf <= 0: skipped_zero_price += 1; continue

        pnl_pct = (xpf - epf) / epf * 100
        ict_pat = sig.get("ict_pattern") or "NULL"
        has_ict = ict_pat not in ("NONE", "NULL")
        held = persistence.get(sig["id"], 0)

        enriched.append({
            "id": sig["id"], "ts": sig_ts,
            "trade_date": sig_ts.astimezone(IST_TZ).date(),
            "symbol": sym, "action": act, "dte": sig.get("dte"),
            "ict_pattern": ict_pat, "has_ict": has_ict,
            "strike": strike, "entry_ltp": epf, "exit_ltp": xpf,
            "pnl_pct": pnl_pct, "win": pnl_pct > 0,
            "held_cycles_30m": held,
            "band": persistence_band(held),
            "ict_mult": float(sig.get("ict_size_mult") or 1.0),
        })

    print(f"\nMatched {len(enriched)}/{len(signals)} signals")
    print(f"  Skipped: no_entry={skipped_no_entry}, no_exit={skipped_no_exit}, "
          f"no_strike={skipped_no_strike}, zero_price={skipped_zero_price}\n")

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
    print("PATH 1 v4 — PERSISTENCE × P&L (Q5 — did flipping signals lose if held on?)")
    print("=" * 100)

    # ─── HEADLINE: P&L by persistence band ───
    print(f"\n[1] P&L at T+30m, grouped by MERDIAN signal persistence")
    print(f"    (the question: if MERDIAN flips early, what would have happened if you held anyway?)\n")
    print(f"{'Band':<22} {'(meaning)':<32} N    WR     Mean      Median")
    print("-" * 95)
    band_labels = {
        "A_flipped_<10m":   "(flipped <10m)",
        "B_flipped_10-20m": "(flipped 10-20m)",
        "C_held_20-30m":    "(held 20-30m)",
        "D_held_full_30m+": "(held full 30m+)",
    }
    for band in ("A_flipped_<10m", "B_flipped_10-20m", "C_held_20-30m", "D_held_full_30m+"):
        rows = [s for s in enriched if s["band"] == band]
        s = stats(rows)
        if s["n"] == 0:
            print(f"{band:<22} {band_labels[band]:<32} (no signals in band)")
        else:
            print(f"{band:<22} {band_labels[band]:<32} {s['n']:>3} {s['wr']:>5.1f}% "
                  f"{s['mean']:>+7.2f}%  {s['median']:>+7.2f}%")

    # ─── Interpretive table ───
    print(f"\n[2] Per-band trade-list (so you can eyeball outliers)")
    for band in ("A_flipped_<10m", "B_flipped_10-20m", "C_held_20-30m", "D_held_full_30m+"):
        rows = [s for s in enriched if s["band"] == band]
        if not rows: continue
        print(f"\n  {band} {band_labels[band]} — N={len(rows)}")
        for r in sorted(rows, key=lambda x: -abs(x["pnl_pct"]))[:8]:
            ict_tag = r["ict_pattern"] if r["has_ict"] else "no-ICT"
            print(f"    {r['trade_date']} {r['symbol']:<6} {r['action']:<7} "
                  f"strike={r['strike']:<6} ict={ict_tag:<10} "
                  f"held={r['held_cycles_30m']}cyc  pnl={r['pnl_pct']:>+7.2f}%")

    # ─── Cross-cut: ICT-tagged within each band ───
    print(f"\n[3] ICT-tagged subset only — does the +59pp aggregate hold up if flips excluded?")
    for band in ("A_flipped_<10m", "B_flipped_10-20m", "C_held_20-30m", "D_held_full_30m+"):
        rows = [s for s in enriched if s["band"] == band and s["has_ict"]]
        s = stats(rows)
        if s["n"] == 0: continue
        print(f"  {band:<22} {band_labels[band]:<22} N={s['n']:>3} WR={s['wr']:>5.1f}% "
              f"Mean={s['mean']:>+7.2f}%  Median={s['median']:>+7.2f}%")

    # ─── Verdict logic ───
    print(f"\n[4] Verdict — is MERDIAN's flip informative or noise?")
    flipped_rows = [s for s in enriched if s["band"] in ("A_flipped_<10m", "B_flipped_10-20m")]
    held_rows = [s for s in enriched if s["band"] in ("C_held_20-30m", "D_held_full_30m+")]
    fs, hs = stats(flipped_rows), stats(held_rows)
    if fs["n"] > 0 and hs["n"] > 0:
        print(f"  Flipped-early (<20m):  N={fs['n']} WR={fs['wr']:.1f}% Mean={fs['mean']:+.2f}% Med={fs['median']:+.2f}%")
        print(f"  Held longer (≥20m):    N={hs['n']} WR={hs['wr']:.1f}% Mean={hs['mean']:+.2f}% Med={hs['median']:+.2f}%")
        wr_delta = hs["wr"] - fs["wr"]
        mean_delta = hs["mean"] - fs["mean"]
        print(f"  Held - Flipped delta:  WR {wr_delta:+.1f}pp  Mean {mean_delta:+.2f}pp")
        if abs(mean_delta) < 3.0 and abs(wr_delta) < 10.0:
            print(f"  → FLIP IS NOISE (held vs flipped P&L similar; both small Δ)")
            print(f"    Operational: hold to T+30m regardless of mid-window flips per Exp 15 sweet spot.")
        elif mean_delta > 3.0 or wr_delta > 10.0:
            print(f"  → FLIP IS INFORMATIVE (held outperforms flipped substantially)")
            print(f"    Operational: exit early when MERDIAN flips; flipping captures real signal degradation.")
        elif mean_delta < -3.0 or wr_delta < -10.0:
            print(f"  → FLIP IS INVERSE-INFORMATIVE (flipped outperforms held)")
            print(f"    Operational: counter-intuitive — flipping correlates with subsequent recovery (mean-reversion?).")
        else:
            print(f"  → INCONCLUSIVE (N too small or noisy)")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
