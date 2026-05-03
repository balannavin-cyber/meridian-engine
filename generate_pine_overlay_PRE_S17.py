#!/usr/bin/env python3
"""
generate_pine_overlay.py  --  MERDIAN ICT HTF Zones Pine Generator

ENH-46-D (Session 11 extension). Generates Pine v6 overlay from ict_htf_zones.

Session 11 update: proximity tier system.
  Tier 1 (T1) -- D zones always + W zones within 2% of current spot.
                  Full opacity, thick border, label shown.
  Tier 2 (T2) -- W zones 2-5% from spot. Medium opacity, thinner border.
  Tier 3 (T3) -- W zones >5% from spot. Near-invisible ghost, no label.

Usage:
    cd C:\\GammaEnginePython
    python generate_pine_overlay.py

Also importable:
    from generate_pine_overlay import generate_pine_content
"""

import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

MONTH_ABBR = ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"]

SYMBOLS = ["NIFTY", "SENSEX"]
TIER1_PCT = 2.0
TIER2_PCT = 5.0

# ENH-46-D entry-band: for these pattern types the resistance entry is at
# zone_high (bear_side=true). All others are support entries (zone_low).
BEAR_SIDE_PATTERNS = {"BEAR_OB", "BEAR_FVG", "PDH"}

SHOW_FLAG_MAP = {
    "PDH":      "show_pdh_pdl",
    "PDL":      "show_pdh_pdl",
    "BULL_OB":  "show_ob",
    "BEAR_OB":  "show_ob",
    "BULL_FVG": "show_fvg",
    "BEAR_FVG": "show_fvg",
}


def weekdays_since(source_date_str, today=None):
    if today is None:
        today = date.today()
    try:
        d = date.fromisoformat(str(source_date_str))
    except Exception:
        return 30
    if d >= today:
        return 5
    count = 0
    current = d
    while current < today:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return max(5, count)


def zone_label(timeframe, pattern_type, source_bar_date):
    try:
        d = date.fromisoformat(str(source_bar_date))
        date_str = f"{MONTH_ABBR[d.month - 1]}-{d.day:02d}"
    except Exception:
        date_str = "??-??"
    return f"{timeframe} {pattern_type} {date_str}"


def get_tier(zone_low, zone_high, current_spot, timeframe):
    if timeframe == "D":
        return 1
    zone_mid = (float(zone_low) + float(zone_high)) / 2
    if current_spot and current_spot > 0:
        distance_pct = abs(zone_mid - current_spot) / current_spot * 100
        if distance_pct <= TIER1_PCT:
            return 1
        elif distance_pct <= TIER2_PCT:
            return 2
        else:
            return 3
    return 2


def pine_color_vars(timeframe, pattern_type, tier):
    if pattern_type in ("BULL_OB",):
        family = "bull_ob"
    elif pattern_type in ("BULL_FVG",):
        family = "bull_fvg"
    elif pattern_type == "BEAR_OB":
        family = "bear_ob"
    elif pattern_type == "BEAR_FVG":
        family = "bear_fvg"
    elif pattern_type == "PDH":
        family = "pdh_d" if timeframe == "D" else "pdh_w"
    elif pattern_type == "PDL":
        family = "pdl_d" if timeframe == "D" else "pdl_w"
    else:
        family = "pdh_w"
    return (f"c_{family}_t{tier}", f"c_{family}_t{tier}_l")


def fetch_current_spot(sb, symbol):
    try:
        rows = sb.table("signal_snapshots").select("spot").eq(
            "symbol", symbol
        ).order("ts", desc=True).limit(1).execute().data
        if rows:
            return float(rows[0]["spot"])
    except Exception:
        pass
    return None


def generate_pine_content(sb):
    rows = sb.table("ict_htf_zones").select(
        "symbol, timeframe, pattern_type, zone_low, zone_high, source_bar_date, valid_from"
    ).eq("status", "ACTIVE").order("symbol").order("timeframe").order(
        "pattern_type"
    ).order("source_bar_date").execute().data

    today = date.today()
    generated_at = today.isoformat()
    spots = {sym: fetch_current_spot(sb, sym) for sym in SYMBOLS}

    by_symbol = {s: [] for s in SYMBOLS}
    for row in rows:
        sym = row.get("symbol", "").upper()
        if sym in by_symbol:
            by_symbol[sym].append(row)

    def render_symbol_block(sym, zones):
        if not zones:
            return f"// {sym}: no active zones\n"
        spot = spots.get(sym)
        t1 = sum(1 for z in zones if get_tier(z["zone_low"], z["zone_high"], spot, z["timeframe"]) == 1)
        t2 = sum(1 for z in zones if get_tier(z["zone_low"], z["zone_high"], spot, z["timeframe"]) == 2)
        t3 = sum(1 for z in zones if get_tier(z["zone_low"], z["zone_high"], spot, z["timeframe"]) == 3)
        lines = [
            f"// =====================================================",
            f"// {sym} -- {len(zones)} zones  T1:{t1} T2:{t2} T3:{t3}  spot={spot:.1f}" if spot else f"// {sym} -- {len(zones)} zones",
            f"// =====================================================",
            f"if is_{sym.lower()}",
        ]
        for z in zones:
            tf = z.get("timeframe", "?")
            pt = z.get("pattern_type", "?")
            zlo = float(z.get("zone_low", 0))
            zhi = float(z.get("zone_high", 0))
            src = z.get("source_bar_date", "")
            tier = get_tier(zlo, zhi, spot, tf)
            bg, line_col = pine_color_vars(tf, pt, tier)
            look_back = weekdays_since(src, today)
            lbl = zone_label(tf, pt, src) if tier < 3 else ""
            bear_side = "true" if pt in BEAR_SIDE_PATTERNS else "false"
            tf_flag   = "show_d" if tf == "D" else ("show_h" if tf == "H" else "show_w")
            type_flag = SHOW_FLAG_MAP.get(pt, "show_ob")
            show_flag = f"{type_flag} and {tf_flag}"
            lines.append(
                f"    draw_zone({zlo:.2f}, {zhi:.2f}, {bg}, {line_col}, "
                f"\"{lbl}\", {look_back}, {bear_side}, {show_flag})"
            )
        return "\n".join(lines) + "\n"

    nifty_block  = render_symbol_block("NIFTY",  by_symbol["NIFTY"])
    sensex_block = render_symbol_block("SENSEX", by_symbol["SENSEX"])
    n_nifty  = len(by_symbol["NIFTY"])
    n_sensex = len(by_symbol["SENSEX"])

    pine = f"""\
// MERDIAN ICT HTF Zones -- PROXIMITY TIER SYSTEM
// AUTO-GENERATED {generated_at} -- DO NOT EDIT MANUALLY
// T1=D zones always + W within 2% | T2=W 2-5% | T3=W >5% ghost no-label
// Total: {n_nifty + n_sensex} zones (NIFTY {n_nifty} + SENSEX {n_sensex})

//@version=6
indicator("MERDIAN ICT HTF Zones ({generated_at})", overlay=true, max_boxes_count=250, max_lines_count=250, max_labels_count=250)

// ── Color legend ─────────────────────────────────────────────────────────────
// BULL_OB   solid green   (high reliability, Exp 35C validated ~88% WR)
// BULL_FVG  lime green    (lower reliability than OB, gap-fill bias)
// BEAR_OB   dark crimson  (high reliability, Exp 35C validated ~88% WR)
// BEAR_FVG  salmon/rose   (lower reliability than OB, gap-fill bias)
// PDH/PDL   yellow (D) / orange (W)

// ── T1: full opacity (D zones always + W within 2% of spot) ──────────────────
c_bull_ob_t1    = color.new(#1B8C3E,  45)   // solid green
c_bull_fvg_t1   = color.new(#7EC85A,  50)   // lime green
c_bear_ob_t1    = color.new(#8B0000,  40)   // dark crimson
c_bear_fvg_t1   = color.new(#E05555,  52)   // salmon red
c_pdh_d_t1      = color.new(color.yellow, 52)
c_pdl_d_t1      = color.new(color.yellow, 52)
c_pdh_w_t1      = color.new(color.orange, 62)
c_pdl_w_t1      = color.new(color.orange, 62)
c_bull_ob_t1_l  = color.new(#1B8C3E,   5)
c_bull_fvg_t1_l = color.new(#7EC85A,   8)
c_bear_ob_t1_l  = color.new(#8B0000,   5)
c_bear_fvg_t1_l = color.new(#E05555,   8)
c_pdh_d_t1_l    = color.new(color.yellow,  8)
c_pdl_d_t1_l    = color.new(color.yellow,  8)
c_pdh_w_t1_l    = color.new(color.orange, 18)
c_pdl_w_t1_l    = color.new(color.orange, 18)

// ── T2: medium opacity (W zones 2-5% from spot) ──────────────────────────────
c_bull_ob_t2    = color.new(#1B8C3E,  72)
c_bull_fvg_t2   = color.new(#7EC85A,  75)
c_bear_ob_t2    = color.new(#8B0000,  68)
c_bear_fvg_t2   = color.new(#E05555,  72)
c_pdh_d_t2      = color.new(color.yellow, 80)
c_pdl_d_t2      = color.new(color.yellow, 80)
c_pdh_w_t2      = color.new(color.orange, 84)
c_pdl_w_t2      = color.new(color.orange, 84)
c_bull_ob_t2_l  = color.new(#1B8C3E,  35)
c_bull_fvg_t2_l = color.new(#7EC85A,  40)
c_bear_ob_t2_l  = color.new(#8B0000,  30)
c_bear_fvg_t2_l = color.new(#E05555,  38)
c_pdh_d_t2_l    = color.new(color.yellow, 42)
c_pdl_d_t2_l    = color.new(color.yellow, 42)
c_pdh_w_t2_l    = color.new(color.orange, 52)
c_pdl_w_t2_l    = color.new(color.orange, 52)

// ── T3: ghost (>5% from spot, no labels) ─────────────────────────────────────
c_bull_ob_t3    = color.new(#1B8C3E,  93)
c_bull_fvg_t3   = color.new(#7EC85A,  93)
c_bear_ob_t3    = color.new(#8B0000,  91)
c_bear_fvg_t3   = color.new(#E05555,  92)
c_pdh_d_t3      = color.new(color.yellow, 93)
c_pdl_d_t3      = color.new(color.yellow, 93)
c_pdh_w_t3      = color.new(color.orange, 94)
c_pdl_w_t3      = color.new(color.orange, 94)
c_bull_ob_t3_l  = color.new(#1B8C3E,  78)
c_bull_fvg_t3_l = color.new(#7EC85A,  78)
c_bear_ob_t3_l  = color.new(#8B0000,  75)
c_bear_fvg_t3_l = color.new(#E05555,  78)
c_pdh_d_t3_l    = color.new(color.yellow, 78)
c_pdl_d_t3_l    = color.new(color.yellow, 78)
c_pdh_w_t3_l    = color.new(color.orange, 80)
c_pdl_w_t3_l    = color.new(color.orange, 80)

// ── SYMBOL DETECTION (must precede draw_zone) ────────────────────────────────
is_nifty  = str.contains(syminfo.ticker, "NIFTY")  and not str.contains(syminfo.ticker, "BANK")
is_sensex = str.contains(syminfo.ticker, "SENSEX") or  str.contains(syminfo.ticker, "BSE")

// ── SETTINGS TOGGLES ─────────────────────────────────────────────────────────
show_w       = input.bool(true,  "Show Weekly zones",  group="Zone Filters")
show_d       = input.bool(true,  "Show Daily zones",   group="Zone Filters")
show_h       = input.bool(false, "Show Hourly zones",  group="Zone Filters", tooltip="Hourly zones not yet generated -- placeholder")
show_ob      = input.bool(true,  "Show Order Blocks",  group="Zone Filters")
show_fvg     = input.bool(true,  "Show FVGs",          group="Zone Filters")
show_pdh_pdl = input.bool(true,  "Show PDH / PDL",     group="Zone Filters")

// ── HELPER ───────────────────────────────────────────────────────────────────
// bear_side=true  -> BEAR_OB/PDH: entry at zone top, clip bottom
// bear_side=false -> BULL_OB/PDL: entry at zone bottom, clip top
// math.max(0, ...) guards against negative bar indices on daily charts
//   where look_back (trading days since zone formation) > bar_index.
draw_zone(float zlow, float zhigh, color bg, color line_col, string lbl, int look_back, bool bear_side, bool show) =>
    if barstate.islast and show
        float cap   = is_nifty ? 80.0 : 250.0
        float rng   = zhigh - zlow
        float dl    = bear_side ? math.max(zlow, zhigh - cap) : zlow
        float dh    = bear_side ? zhigh : math.min(zhigh, zlow + cap)
        bool  wide  = rng > cap
        int   lft   = math.max(0, bar_index - look_back)
        var box   bx = na
        var label lb = na
        var line  rl = na
        box.delete(bx)
        label.delete(lb)
        line.delete(rl)
        bx := box.new(lft, dh, bar_index + 30, dl, bgcolor=bg, border_color=line_col, border_width=1, extend=extend.right)
        if lbl != ""
            lb := label.new(bar_index + 30, (dh + dl) / 2, text=lbl, color=color.new(color.black, 100), textcolor=line_col, style=label.style_label_left, size=size.small)
        if wide
            float ry    = bear_side ? zlow : zhigh
            string rlbl = lbl != "" ? lbl + " (far edge)" : "far edge"
            rl := line.new(lft, ry, bar_index + 30, ry, color=color.new(line_col, 50), width=1, style=line.style_dashed, extend=extend.right)
            label.new(bar_index + 30, ry, text=rlbl, color=color.new(color.black, 100), textcolor=color.new(line_col, 30), style=label.style_label_left, size=size.tiny)

{nifty_block}
{sensex_block}
// ── HEADER ───────────────────────────────────────────────────────────────────
if barstate.islast
    var label hdr = na
    label.delete(hdr)
    sym_str = is_nifty ? "NIFTY" : (is_sensex ? "SENSEX" : "OTHER")
    n_zones = is_nifty ? {n_nifty} : (is_sensex ? {n_sensex} : 0)
    hdr := label.new(x=bar_index, y=high * 1.001, text="MERDIAN HTF | " + sym_str + " | " + str.tostring(n_zones) + " zones | entry-band | {generated_at}", color=color.new(color.black, 80), textcolor=color.white, style=label.style_label_down, size=size.small)
"""
    return pine


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.stderr.write("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set\n")
        return 1
    sb = create_client(url, key)
    content = generate_pine_content(sb)
    out = "merdian_ict_htf_zones.pine"
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    lines = [l for l in content.splitlines() if l.strip().startswith("draw_zone")]
    print(f"Written: {out}  ({len(lines)} zones rendered with proximity tiers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
