#!/usr/bin/env python3
"""
s30_gate_audit_and_ob_attachment.py — two investigations in one script.

PART A — Gate audit on the 209 blocked pure-ICT setups (from v5):
  For each gate dimension (gamma_regime, vix_regime, breadth_regime, wcb_regime,
  direction_bias, po3_session_bias, dte, ict_mtf_context, ict_tier), compute
  WR + mean P&L grouped by gate value. Identify which specific gate values
  systematically block winners vs losers.

PART B — OB attachment investigation on ict_htf_zones BEAR_OB + BULL_OB:
  For every BEAR_OB and BULL_OB zone in the 8-week window, find signal_snapshots
  rows where spot was inside [zone_low, zone_high]. Check what ict_pattern was
  tagged at those touches. If touches exist with ict_pattern != BEAR_OB/BULL_OB,
  the attachment is broken at the signal-builder, not the detector.

Run:
    python s30_gate_audit_and_ob_attachment.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
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
OB_PATTERNS = ["BULL_OB", "BEAR_OB"]

GATE_COLUMNS = [
    "gamma_regime", "vix_regime", "breadth_regime", "wcb_regime",
    "direction_bias", "po3_session_bias", "ict_tier", "ict_mtf_context",
]

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


def _paginate(qb, page=1000):
    out, off = [], 0
    while True:
        resp = qb.range(off, off + page - 1).execute()
        rows = resp.data or []
        if not rows: break
        out.extend(rows)
        if len(rows) < page: break
        off += page
    return out


def fetch_ict_tagged(sb: Client) -> list[dict]:
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(weeks=WINDOW_WEEKS)).isoformat()
    print(f"[A1] Fetching all ICT-tagged signals since {cutoff_iso} (incl. gate columns)...")
    cols = ("id, ts, symbol, action, trade_allowed, expiry_date, "
            "spot, atm_strike, dte, ict_pattern, ict_tier, "
            "ict_mtf_context, direction_bias, gamma_regime, breadth_regime, "
            "vix_regime, wcb_regime, po3_session_bias, reasons, cautions")
    rows = _paginate(
        sb.table("signal_snapshots").select(cols)
          .in_("ict_pattern", ICT_PATTERNS)
          .gte("ts", cutoff_iso).order("ts"))
    print(f"      → {len(rows)} cycles\n")
    return rows


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
        resp = (sb.table(table)
                .select("ts, ltp")
                .eq("symbol", symbol).eq("strike", strike)
                .eq("option_type", option_type).eq("expiry_date", expiry_date)
                .gte("ts", lo).lte("ts", hi)
                .order("ts").range(0, 99).execute())
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


def price_setups(sb: Client, deduped: list[dict]) -> list[dict]:
    print(f"[A2] Pricing {len(deduped)} setups...")
    enriched = []
    convention = None
    for i, sig in enumerate(deduped, 1):
        if i % 30 == 0: print(f"      ...processed {i}/{len(deduped)}")
        try: sig_ts = _ts_from_str(sig["ts"])
        except (KeyError, ValueError): continue
        sym, pat = sig["symbol"], sig["ict_pattern"]
        natural = "BUY_CE" if pat in BULL_PATTERNS else "BUY_PE"
        strike, expiry = sig.get("atm_strike"), sig.get("expiry_date")
        if strike is None or not expiry: continue
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
        if eb is None: continue
        ot_f = ("CE" if natural == "BUY_CE" else "PE") if convention == "CE/PE" else ("CALL" if natural == "BUY_CE" else "PUT")
        xb = fetch_chain_row_smart(sb, sym, int(strike), ot_f, str(expiry),
                                    sig_ts + timedelta(minutes=EXIT_OFFSET_MIN))
        if xb is None: continue
        ep, xp = eb.get("ltp"), xb.get("ltp")
        if ep is None or xp is None: continue
        try: epf, xpf = float(ep), float(xp)
        except (TypeError, ValueError): continue
        if epf <= 0: continue
        e = dict(sig)
        e["pnl_pct"] = (xpf - epf) / epf * 100
        e["win"] = e["pnl_pct"] > 0
        e["natural_action"] = natural
        e["was_blocked"] = not (sig.get("trade_allowed") and sig.get("action") == natural)
        enriched.append(e)
    print(f"      → enriched {len(enriched)}/{len(deduped)}\n")
    return enriched


def stats(rows):
    n = len(rows)
    if n == 0: return None
    pnls = sorted(r["pnl_pct"] for r in rows)
    wins = sum(1 for r in rows if r["win"])
    return {"n": n, "wr": wins/n*100, "mean": sum(pnls)/n, "median": pnls[n//2]}


def part_a_gate_audit(enriched: list[dict]):
    print("=" * 100)
    print("PART A — GATE AUDIT (which specific gates blocked the winners?)")
    print("=" * 100)

    blocked = [e for e in enriched if e["was_blocked"]]
    allowed = [e for e in enriched if not e["was_blocked"]]
    sb_ = stats(blocked); sa_ = stats(allowed); sall = stats(enriched)
    print(f"\nCohort split:")
    if sb_:
        print(f"  Blocked or misaligned (gate stack rejected/flipped): N={sb_['n']:>3} "
              f"WR={sb_['wr']:>5.1f}% Mean={sb_['mean']:>+7.2f}% Med={sb_['median']:>+7.2f}%")
    if sa_:
        print(f"  Allowed + aligned (gate stack let through):        N={sa_['n']:>3} "
              f"WR={sa_['wr']:>5.1f}% Mean={sa_['mean']:>+7.2f}% Med={sa_['median']:>+7.2f}%")
    if sall:
        print(f"  ALL (pure-ICT regardless of gates):                 N={sall['n']:>3} "
              f"WR={sall['wr']:>5.1f}% Mean={sall['mean']:>+7.2f}% Med={sall['median']:>+7.2f}%")
    print()

    # ─── Per-gate dimension analysis ───
    print("[A.1] Per-gate dimension: WR/P&L conditional on gate value")
    print("      Test: does this gate's value-buckets separate winners from losers?\n")
    for col in GATE_COLUMNS:
        print(f"  Gate: {col}")
        by_val = defaultdict(list)
        for e in enriched:
            v = e.get(col)
            by_val[str(v) if v is not None else "NULL"].append(e)
        rows = []
        for v, items in by_val.items():
            s = stats(items)
            if s is None or s["n"] < 5: continue
            rows.append((v, s))
        if not rows:
            print(f"     (insufficient distinct values with N>=5)")
            continue
        rows.sort(key=lambda x: -x[1]["wr"])
        for v, s in rows:
            tag = ""
            if s["wr"] > 70 and s["median"] > 2:
                tag = "  ← HIGH-EDGE bucket"
            elif s["wr"] < 45 or s["median"] < -1:
                tag = "  ← LOW-EDGE bucket"
            print(f"     {col}={v:<14} N={s['n']:>3} WR={s['wr']:>5.1f}% "
                  f"Mean={s['mean']:>+7.2f}% Med={s['median']:>+7.2f}%{tag}")
        # Note if best-bucket is one that the gate would BLOCK
        if rows:
            best_v, best_s = rows[0]
            worst_v, worst_s = rows[-1]
            delta_wr = best_s["wr"] - worst_s["wr"]
            delta_mean = best_s["mean"] - worst_s["mean"]
            if delta_wr >= 15 or delta_mean >= 4:
                print(f"     >>> Spread: best={best_v} ({best_s['wr']:.1f}%) vs "
                      f"worst={worst_v} ({worst_s['wr']:.1f}%)  ΔWR={delta_wr:+.1f}pp ΔMean={delta_mean:+.2f}pp")
            else:
                print(f"     >>> Flat across values (ΔWR={delta_wr:+.1f}pp ΔMean={delta_mean:+.2f}pp) — gate adds no info")
        print()

    # ─── Reasons JSONB rollup ───
    print("[A.2] Most frequent 'reasons' JSON entries on BLOCKED setups (top 20)")
    reasons_counter = Counter()
    for e in blocked:
        rs = e.get("reasons")
        if rs is None: continue
        if isinstance(rs, list):
            for x in rs: reasons_counter[str(x)] += 1
        elif isinstance(rs, dict):
            for k, v in rs.items(): reasons_counter[f"{k}={v}"] += 1
        else:
            reasons_counter[str(rs)] += 1
    if reasons_counter:
        for reason, n in reasons_counter.most_common(20):
            print(f"     {n:>3}×  {reason[:120]}")
    else:
        print("     (no reasons captured — column may be empty or in unexpected format)")
    print()

    # ─── Cautions JSONB rollup ───
    print("[A.3] Most frequent 'cautions' JSON entries on BLOCKED setups (top 20)")
    cautions_counter = Counter()
    for e in blocked:
        cs = e.get("cautions")
        if cs is None: continue
        if isinstance(cs, list):
            for x in cs: cautions_counter[str(x)] += 1
        elif isinstance(cs, dict):
            for k, v in cs.items(): cautions_counter[f"{k}={v}"] += 1
        else:
            cautions_counter[str(cs)] += 1
    if cautions_counter:
        for c, n in cautions_counter.most_common(20):
            print(f"     {n:>3}×  {c[:120]}")
    else:
        print("     (no cautions captured)")
    print()


def part_b_ob_attachment(sb: Client):
    print("=" * 100)
    print("PART B — OB ATTACHMENT INVESTIGATION (detector firing but signal-builder dropping?)")
    print("=" * 100)

    eight_weeks_ago = (datetime.now(timezone.utc) - timedelta(weeks=WINDOW_WEEKS)).date().isoformat()
    print(f"\n[B.1] Fetching ict_htf_zones BEAR_OB + BULL_OB zones active in 8wk window...")
    # Pull all OB zones with valid_to in window OR valid_to NULL (still active) OR source_bar_date in window
    zones = []
    for pat in OB_PATTERNS:
        resp = (sb.table("ict_htf_zones")
                .select("id, symbol, pattern_type, timeframe, status, "
                        "zone_low, zone_high, zone_mid, valid_from, valid_to, source_bar_date")
                .eq("pattern_type", pat)
                .gte("source_bar_date", eight_weeks_ago)
                .execute())
        zones.extend(resp.data or [])
    print(f"      → {len(zones)} OB zones found\n")
    if not zones:
        print("     (no OB zones in 8-week window — investigate ict_htf_zones writer)")
        return

    print("[B.2] Per zone: how many signal_snapshots rows had spot inside zone?  "
          "And what ict_pattern was tagged?\n")
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(weeks=WINDOW_WEEKS)).isoformat()
    rows_data = []  # (zone, n_touches, pattern_counter)

    for z in zones:
        zlo, zhi = float(z["zone_low"]), float(z["zone_high"])
        valid_from = z["valid_from"]
        valid_to = z["valid_to"] or datetime.now(timezone.utc).isoformat()
        # Bound to 8-week window
        v_lo = max(valid_from, cutoff_iso)
        try:
            resp = (sb.table("signal_snapshots")
                    .select("ts, ict_pattern, spot, action, trade_allowed")
                    .eq("symbol", z["symbol"])
                    .gte("spot", zlo).lte("spot", zhi)
                    .gte("ts", v_lo).lte("ts", valid_to)
                    .order("ts").range(0, 4999).execute())
        except Exception as e:
            print(f"      [error] zone {z['id'][:8]}... {e}")
            continue
        touches = resp.data or []
        pat_counter = Counter()
        for t in touches:
            p = t.get("ict_pattern") or "NULL"
            pat_counter[p] += 1
        rows_data.append((z, len(touches), pat_counter))

    # Sort by touches desc
    rows_data.sort(key=lambda x: -x[1])
    print(f"  {'Zone':<10} {'Sym':<7} {'Type':<9} {'TF':<3} {'Status':<10} "
          f"{'Lo-Hi':<25} {'Touches':<8} ict_pattern distribution")
    print("  " + "-" * 100)
    for z, n_touches, pat_counter in rows_data:
        zid = (z["id"] or "")[:8]
        rng = f"{z['zone_low']:.0f}-{z['zone_high']:.0f}"
        if n_touches == 0:
            dist = "(no spot rows in zone+window)"
        else:
            dist = ", ".join(f"{p}={n}" for p, n in pat_counter.most_common())
        print(f"  {zid:<10} {z['symbol']:<7} {z['pattern_type']:<9} {z['timeframe']:<3} "
              f"{z['status']:<10} {rng:<25} {n_touches:<8} {dist}")
    print()

    # ─── Aggregate: across all OB zone touches, what was the ict_pattern attached? ───
    print("[B.3] Aggregate: across ALL OB zone touches, ict_pattern distribution\n")
    for pat in OB_PATTERNS:
        agg = Counter()
        total_touches = 0
        for z, n_touches, pc in rows_data:
            if z["pattern_type"] != pat: continue
            total_touches += n_touches
            agg.update(pc)
        print(f"  {pat} zones — total touches across all zones: {total_touches}")
        if total_touches == 0:
            print(f"    (no signal_snapshots rows had spot inside any {pat} zone)")
        else:
            for tagged_pat, n in agg.most_common():
                pct = n / total_touches * 100
                arrow = "  ← CORRECT" if tagged_pat == pat else ""
                print(f"    tagged as {tagged_pat:<12} N={n:>4} ({pct:>5.1f}%){arrow}")
        print()


def main() -> int:
    sb = _load_supabase()
    raw = fetch_ict_tagged(sb)
    if not raw:
        print("\n*** No ICT-tagged signals ***"); return 0
    deduped = dedupe_first_per_setup(raw)
    print(f"      → {len(deduped)} unique setups after dedup\n")
    enriched = price_setups(sb, deduped)

    if enriched:
        part_a_gate_audit(enriched)
    part_b_ob_attachment(sb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
