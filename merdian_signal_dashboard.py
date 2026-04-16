#!/usr/bin/env python3
"""
merdian_signal_dashboard.py  --  MERDIAN Live Signal Dashboard
Port: 8766  |  Run: python merdian_signal_dashboard.py
"""

import os, json, math, traceback
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

IST      = ZoneInfo("Asia/Kolkata")
PORT     = 8766
SYMBOLS  = ["NIFTY", "SENSEX"]
LOT_SIZE = {"NIFTY": 65, "SENSEX": 20}

WIN_RATES = [
    ("BEAR_OB",   "MORNING (09:15-11:30)",    100.0, "TIER1", ""),
    ("BULL_OB",   "MORNING (09:15-11:30)",    100.0, "TIER1", ""),
    ("BULL_OB",   "DTE=0",                    100.0, "TIER1", "+107.4% exp"),
    ("BULL_OB",   "AFTERNOON (13:00-15:00)",  100.0, "TIER1", "+75.3% exp"),
    ("BULL_FVG",  "HIGH ctx + DTE=0",          87.5, "TIER1", "+58.9% exp"),
    ("JUDAS_BULL","confirm at T+15m",           83.3, "TIER2", ""),
    ("BEAR_OB",   "MOM_YES filter",             83.0, "TIER2", "+21.6pp lift"),
    ("BULL_OB",   "MOM_YES filter",             80.0, "TIER2", ""),
    ("JUDAS_BULL","unconfluenced",              69.0, "TIER3", ""),
    ("BULL_FVG",  "SHORT_GAMMA + BULLISH",      65.0, "TIER2", ""),
    ("BULL_FVG",  "NO confluence (ICT only)",   50.3, "TIER3", "MIN SIZE"),
    ("BEAR_OB",   "AFTERNOON 13:00-14:30",      17.0, "SKIP",  "HARD SKIP"),
]

# ---------------------------------------------------------------------------
# Session zone
# ---------------------------------------------------------------------------
def session_zone(t):
    m = t.hour * 60 + t.minute
    if m < 9*60+15:  return "PRE-MARKET", "#888"
    if m < 10*60:    return "OPEN", "#ffaa00"
    if m < 11*60+30: return "MORNING", "#00cc88"
    if m < 13*60:    return "MIDDAY", "#00aacc"
    if m < 14*60+30: return "AFTERNOON", "#ff8800"
    if m < 15*60:    return "PRE-CLOSE", "#ff5555"
    return "POWER HOUR — NO SIGNALS", "#ff3b5c"

# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------
def _q(fn):
    try: return fn()
    except: return None

def fetch_signal(sym):
    r = _q(lambda: sb.table("signal_snapshots")
        .select("ts,action,trade_allowed,confidence_score,spot,atm_strike,"
                "expiry_date,dte,atm_iv_avg,gamma_regime,breadth_regime,"
                "india_vix,ict_pattern,ict_tier,ict_mtf_context,"
                "ict_lots_t1,ict_lots_t2,ict_lots_t3")
        .eq("symbol", sym).order("ts", desc=True).limit(1).execute().data)
    return r[0] if r else None

def fetch_zone(sym):
    r = _q(lambda: sb.table("ict_zones")
        .select("pattern_type,ict_tier,mtf_context,zone_high,zone_low,"
                "opt_type,ict_lots_t1,ict_lots_t2,ict_lots_t3")
        .eq("symbol", sym).eq("trade_date", str(date.today()))
        .eq("status", "ACTIVE").order("detected_at_ts", desc=True).limit(1).execute().data)
    return r[0] if r else None

def fetch_capital(sym):
    r = _q(lambda: sb.table("capital_tracker")
        .select("capital,updated_at").eq("symbol", sym).limit(1).execute().data)
    return r[0] if r else None

def fetch_spot(sym):
    r = _q(lambda: sb.table("signal_snapshots")
        .select("spot,ts").eq("symbol", sym)
        .order("ts", desc=True).limit(1).execute().data)
    return r[0] if r else None

def fetch_premium(sym, strike, expiry, ot):
    r = _q(lambda: sb.table("option_chain_snapshots")
        .select("ltp,close").eq("symbol", sym).eq("strike", float(strike))
        .eq("expiry_date", str(expiry)).eq("option_type", ot)
        .order("ts", desc=True).limit(1).execute().data)
    if r:
        v = float(r[0].get("ltp") or r[0].get("close") or 0)
        return v if v > 0 else None
    return None

def fetch_breadth_history():
    """Fetch today's breadth time series from breadth_intraday_history."""
    today = str(date.today())
    r = _q(lambda: sb.table("breadth_intraday_history")
        .select("ts,advances,declines,breadth_score,coverage_pct")
        .eq("trade_date", today)
        .order("ts", desc=False)
        .limit(100)
        .execute().data)
    return r or []

def eff_cap(c):
    F, Z, X = 10_000, 2_500_000, 5_000_000
    if c < F: return F
    if c > X: return X
    if c > Z: return Z
    return c

def iv_premium(spot, iv_pct, dte):
    if not (spot and iv_pct and dte): return None
    return spot * (iv_pct/100) * math.sqrt(max(1,dte)/365) * 0.4

def inr(v):
    return "—" if v is None else f"\u20b9{v:,.0f}"

# ---------------------------------------------------------------------------
# Build signal data dict
# ---------------------------------------------------------------------------
def build(sym):
    sig  = fetch_signal(sym)
    zone = fetch_zone(sym)
    cap  = fetch_capital(sym)
    spt  = fetch_spot(sym)

    d = {"symbol": sym, "lot_size": LOT_SIZE[sym]}
    d["spot"] = float(spt["spot"]) if spt else None

    cap_val = float(cap["capital"]) if cap else 200_000
    d["capital"]     = cap_val
    d["capital_eff"] = eff_cap(cap_val)

    if not sig:
        d.update(action="NO DATA", trade_allowed=False, confidence=0, ts="")
        return d

    action  = sig.get("action", "NO DATA")
    allowed = bool(sig.get("trade_allowed")) and action not in ("DO_NOTHING","NO DATA","ERROR")

    d.update(
        action       = action,
        trade_allowed= allowed,
        confidence   = sig.get("confidence_score", 0),
        ts           = sig.get("ts", ""),
        gamma        = sig.get("gamma_regime", ""),
        breadth      = sig.get("breadth_regime", ""),
        india_vix    = sig.get("india_vix"),
        dte          = sig.get("dte"),
        atm_strike   = sig.get("atm_strike"),
        expiry       = sig.get("expiry_date", ""),
        atm_iv       = sig.get("atm_iv_avg"),
        pattern      = sig.get("ict_pattern") or "NONE",
        tier         = sig.get("ict_tier")    or "NONE",
        mtf          = sig.get("ict_mtf_context") or "NONE",
        lots_t1      = sig.get("ict_lots_t1"),
        lots_t2      = sig.get("ict_lots_t2"),
        lots_t3      = sig.get("ict_lots_t3"),
    )

    if zone:
        d["pattern"]  = zone.get("pattern_type", d["pattern"])
        d["tier"]     = zone.get("ict_tier",     d["tier"])
        d["mtf"]      = zone.get("mtf_context",  d["mtf"])
        d["zone_high"]= zone.get("zone_high")
        d["zone_low"] = zone.get("zone_low")
        d["opt_type"] = zone.get("opt_type")
        d["lots_t1"]  = zone.get("ict_lots_t1") or d["lots_t1"]
        d["lots_t2"]  = zone.get("ict_lots_t2") or d["lots_t2"]
        d["lots_t3"]  = zone.get("ict_lots_t3") or d["lots_t3"]
    else:
        d["zone_high"] = d["zone_low"] = None
        d["opt_type"]  = "PE" if action=="BUY_PE" else "CE" if action=="BUY_CE" else None

    tier = d["tier"]
    d["active_lots"] = d.get({"TIER1":"lots_t1","TIER2":"lots_t2","TIER3":"lots_t3"}.get(tier,"lots_t3"))

    prem, psrc = None, "live"
    if d["atm_strike"] and d["expiry"] and d["opt_type"]:
        prem = fetch_premium(sym, d["atm_strike"], d["expiry"], d["opt_type"])
    if prem is None and d["spot"] and d["atm_iv"] and d["dte"]:
        prem = iv_premium(d["spot"], d["atm_iv"], d["dte"]); psrc = "IV est."
    d["premium"] = prem; d["premium_src"] = psrc

    lots = d["active_lots"]
    if prem and lots and prem > 0:
        lc = prem * LOT_SIZE[sym]
        d["lot_cost"] = lc
        d["deployed"]  = lc * lots
        d["alloc"]     = d["capital_eff"] * {"TIER1":.50,"TIER2":.40,"TIER3":.20}.get(tier,.20)
    else:
        d["lot_cost"] = d["deployed"] = d["alloc"] = None

    if d["ts"]:
        try:
            st = datetime.fromisoformat(d["ts"].replace("Z","+00:00"))
            d["exit_ts"] = (st + timedelta(minutes=30)).isoformat()
        except: d["exit_ts"] = None
    else: d["exit_ts"] = None

    return d

# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def tier_col(t):
    return {"TIER1":"#00ff88","TIER2":"#ffaa00","TIER3":"#888","SKIP":"#ff3b5c"}.get(t,"#555")

def pill(val):
    c = {"SHORT_GAMMA":"#00ff88","LONG_GAMMA":"#ff3b5c","NO_FLIP":"#888",
         "BULLISH":"#00ff88","BEARISH":"#ff3b5c","TRANSITION":"#ffaa00",
         "HIGH_IV":"#ff8800","NORMAL_IV":"#888","LOW_IV":"#00aacc"}.get(val,"#555")
    return f'<span class="pill" style="border-color:{c};color:{c}">{val}</span>'

def wr_for(tier, pat):
    m = {"TIER1":90.9,"TIER2":65.0,"TIER3":50.3,"SKIP":17.0}
    if pat=="BEAR_OB" and tier=="TIER1": return 94.4
    if pat=="BULL_OB" and tier=="TIER1": return 88.9
    if pat=="JUDAS_BULL": return 69.0
    if pat=="BULL_FVG" and tier=="TIER3": return 50.3
    return m.get(tier, 60.0)

def legend_rows(pat):
    if not pat or pat in ("NONE","NO DATA","ERROR"):
        return '<tr><td colspan="5" class="no-pat">No active ICT pattern this cycle</td></tr>'
    rows = [r for r in WIN_RATES if r[0]==pat]
    if not rows:
        return f'<tr><td colspan="5" class="no-pat">No WR data for {pat}</td></tr>'
    out = []
    for p,cond,wr,tier,note in rows:
        tc  = tier_col(tier)
        wrc = "wg" if wr>=80 else "wa" if wr>=60 else "wr" if wr>=30 else "ws"
        out.append(
            f'<tr><td class="lp">{p}</td><td>{cond}</td>'
            f'<td class="wc {wrc}">{wr:.0f}%</td>'
            f'<td><span class="pill sm" style="border-color:{tc};color:{tc}">{tier}</span></td>'
            f'<td class="nt">{note}</td></tr>'
        )
    return "\n".join(out)

# ---------------------------------------------------------------------------
# Signal card
# ---------------------------------------------------------------------------
def card(d):
    if d.get("error"):
        return f'<div class="card err-card"><b>{d["symbol"]}</b><br>{d["error"]}</div>'

    sym     = d["symbol"]
    action  = d.get("action","NO DATA")
    allowed = d.get("trade_allowed", False)
    pat     = d.get("pattern","NONE")
    tier    = d.get("tier","NONE")
    wr      = wr_for(tier, pat)
    mtf     = d.get("mtf","NONE")
    conf    = d.get("confidence",0)
    spot    = d.get("spot")
    vix     = d.get("india_vix")
    gamma   = d.get("gamma","")
    breadth = d.get("breadth","")
    cap     = d.get("capital", 200_000)
    cap_eff = d.get("capital_eff", 200_000)

    # action style
    if action=="BUY_PE":   col,arrow,lbl = "#ff3b5c","▼","SELL / BUY PE"
    elif action=="BUY_CE": col,arrow,lbl = "#00ff88","▲","BUY CE"
    else:                  col,arrow,lbl = "#555","—",action

    badge = ('<span class="bg">TRADE ALLOWED</span>' if allowed
             else '<span class="br">BLOCKED</span>')

    wrcls = "wg" if wr>=80 else "wa" if wr>=60 else "ws" if wr<30 else "wm"

    # zone band
    zh, zl = d.get("zone_high"), d.get("zone_low")
    zone_html = (f'<div class="row"><span class="lb">ICT Zone</span>'
                 f'<span class="vl zb">{zl:,.0f} \u2013 {zh:,.0f}</span></div>'
                 if zh and zl else "")

    # lots
    lots_html = ""
    if d.get("active_lots") and action not in ("DO_NOTHING","NO DATA","ERROR"):
        l1 = d.get("lots_t1","—"); l2 = d.get("lots_t2","—"); l3 = d.get("lots_t3","—")
        lots_html = (
            f'<div class="lg">'
            f'<div class="lc t1"><div class="lt">TIER1 50%</div><div class="lv">{l1 or "—"}</div><div class="ls">lots</div></div>'
            f'<div class="lc t2"><div class="lt">TIER2 40%</div><div class="lv">{l2 or "—"}</div><div class="ls">lots</div></div>'
            f'<div class="lc t3"><div class="lt">TIER3 20%</div><div class="lv">{l3 or "—"}</div><div class="ls">lots</div></div>'
            f'</div>'
        )

    # execution
    exec_html = ""
    atm_stk = d.get("atm_strike"); expiry = d.get("expiry",""); ot = d.get("opt_type","")
    dte = d.get("dte"); iv = d.get("atm_iv"); prem = d.get("premium")
    lc  = d.get("lot_cost"); dep = d.get("deployed"); alloc = d.get("alloc")
    psrc = d.get("premium_src","")
    if action not in ("DO_NOTHING","NO DATA","ERROR") and atm_stk and ot:
        exec_html = (
            f'<div class="eb"><div class="et">EXECUTION</div>'
            f'<div class="eg">'
            f'<div class="ei"><span class="lb">Strike</span><span class="vl sk">{int(atm_stk):,} {ot}</span></div>'
            f'<div class="ei"><span class="lb">Expiry</span><span class="vl">{expiry}</span></div>'
            f'<div class="ei"><span class="lb">DTE</span><span class="vl dv">{dte if dte is not None else "—"}</span></div>'
            f'<div class="ei"><span class="lb">ATM IV</span><span class="vl">{f"{iv:.1f}%" if iv else "—"}</span></div>'
            f'<div class="ei"><span class="lb">Premium ({psrc})</span><span class="vl pm">{inr(prem)}</span></div>'
            f'<div class="ei"><span class="lb">Lot cost ({LOT_SIZE[sym]}u)</span><span class="vl pm">{inr(lc)}</span></div>'
            f'</div>'
            + (f'<div class="dr"><span class="lb">Allocation</span><span class="vl">{inr(alloc)}</span></div>' if alloc else '')
            + (f'<div class="dr hi"><span class="lb">Deployed ({d["active_lots"]} lots)</span><span class="vl dh">{inr(dep)}</span></div>' if dep else '')
            + '</div>'
        )

    # exit
    exit_html = ""
    exit_ts = d.get("exit_ts",""); _ts_raw = d.get("ts","")
    # Convert UTC timestamp to IST for display
    try:
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        _ts_dt = datetime.fromisoformat(_ts_raw.replace("Z","+00:00"))
        sig_ts = _ts_dt.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%dT%H:%M:%S+05:30")
    except Exception:
        sig_ts = _ts_raw
    if exit_ts and allowed:
        exit_html = (
            f'<div class="xb"><div class="xt">EXIT SIGNAL \u2014 T+30m FIXED</div>'
            f'<div class="xr"><span class="lb">Signal at</span><span class="vl">{sig_ts[11:16]} IST</span></div>'
            f'<div class="xr"><span class="lb">EXIT AT</span><span class="vl xtm">{exit_ts[11:16]} IST</span></div>'
            f'<div class="cd" id="cd-{sym}" data-exit="{exit_ts}">--:--</div></div>'
        )

    cap_int = int(cap) if cap else 200000

    return (
        f'<div class="card">'
        f'<div class="ch"><span class="sy">{sym}</span>'
        f'<span class="sl">{f"{spot:,.1f}" if spot else "—"}</span>'
        f'<span class="vx">VIX {f"{vix:.1f}" if vix else "—"}</span>'
        f'{badge}</div>'
        f'<div class="ar" style="color:{col}"><span class="aw">{arrow}</span>'
        f'<span class="al">{lbl}</span><span class="cf">CONF {conf:.0f}</span></div>'
        f'<div class="ir">'
        f'<div class="ii"><div class="il">ICT PATTERN</div><div class="iv">{pat}</div></div>'
        f'<div class="ii"><div class="il">TIER</div><div class="iv" style="color:{tier_col(tier)}">{tier}</div></div>'
        f'<div class="ii"><div class="il">WIN RATE</div><div class="iv {wrcls}">{wr:.0f}%</div></div>'
        f'<div class="ii"><div class="il">MTF</div><div class="iv">{mtf}</div></div>'
        f'</div>'
        f'{zone_html}{lots_html}{exec_html}{exit_html}'
        f'<div class="wd"><div class="wt">WIN RATE \u2014 {pat}</div>'
        f'<table class="wt2"><thead><tr><th>Pattern</th><th>Condition</th><th>WR</th><th>Tier</th><th>Note</th></tr></thead>'
        f'<tbody>{legend_rows(pat)}</tbody></table></div>'
        f'<div class="rw">{pill(gamma)} {pill(breadth)}</div>'
        f'<div class="cpr">'
        f'<span class="lb">Capital</span>'
        f'<span class="vl" id="cdp-{sym}">{inr(cap)}</span>'
        f'<span class="sp">|</span>'
        f'<span class="lb">Eff. sizing</span>'
        f'<span class="vl">{inr(cap_eff)}</span>'
        f'</div>'
        f'<div class="csr">'
        f'<span class="csl">Set capital ({sym})</span>'
        f'<input class="csi" id="csi-{sym}" type="number" value="{cap_int}" min="10000" step="50000">'
        f'<button class="csb" id="csb-{sym}" onclick="setCap(\'{sym}\')">SET</button>'
        f'<span class="csm" id="csm-{sym}"></span>'
        f'</div>'
        f'<div class="trade-bar">' +
          (f'<button class="place-btn" onclick="showPlaceOrder(\'{sym}\')">'
           '&#9889; PLACE ORDER</button>'
           if action not in ("DO_NOTHING","NO DATA","ERROR") else '') +
          (f'<button class="log-btn" onclick="showLogTrade(\'{sym}\')">'
           '&#128203; LOG MANUAL</button>'
           if action not in ("DO_NOTHING","NO DATA","ERROR") else '') +
          f'<button class="close-btn" onclick="showCloseForm(\'{sym}\')">'
          '&#10060; SQUARE OFF</button></div>' +
          f'<div class="st">Signal: {sig_ts[11:16]} IST</div>'
        f'</div>'
    )

# ---------------------------------------------------------------------------
# Full page
# ---------------------------------------------------------------------------
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#080b0f;color:#c9d5e0;font-family:'Barlow Condensed',sans-serif;font-size:14px}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:10px 20px;
  background:#0d1117;border-bottom:1px solid #1e2a38;position:sticky;top:0;z-index:10}
.logo{font-family:'Space Mono',monospace;font-size:13px;font-weight:700;letter-spacing:4px;color:#00ccff}
.clk{font-family:'Space Mono',monospace;font-size:20px}
.dt{font-size:12px;color:#64748b;margin-left:10px}
.zb{padding:4px 14px;border-radius:2px;font-weight:700;font-size:12px;letter-spacing:2px;border:1px solid}
.rb{padding:6px 16px;background:transparent;border:1px solid #1e2a38;color:#64748b;
  cursor:pointer;font-size:12px;letter-spacing:1px;border-radius:2px}
.rb:hover{border-color:#00ccff;color:#00ccff}
.main{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px 20px;max-width:1400px;margin:0 auto}
.card{background:#0d1117;border:1px solid #1e2a38;border-radius:4px;overflow:hidden}
.err-card{padding:20px;color:#ff3b5c;font-family:'Space Mono',monospace;font-size:12px}
.ch{display:flex;align-items:center;gap:12px;padding:12px 16px;background:#111820;border-bottom:1px solid #1e2a38}
.sy{font-family:'Space Mono',monospace;font-size:18px;font-weight:700;letter-spacing:3px;color:#00ccff}
.sl{font-family:'Space Mono',monospace;font-size:20px;font-weight:700;margin-left:4px}
.vx{font-size:12px;color:#64748b;margin-left:auto}
.bg{padding:3px 10px;background:rgba(0,255,136,.12);border:1px solid #00ff88;color:#00ff88;
  font-size:11px;font-weight:700;letter-spacing:1px;border-radius:2px}
.br{padding:3px 10px;background:rgba(255,59,92,.12);border:1px solid #ff3b5c;color:#ff3b5c;
  font-size:11px;font-weight:700;letter-spacing:1px;border-radius:2px}
.ar{display:flex;align-items:baseline;gap:16px;padding:16px 16px 8px;border-bottom:1px solid #1e2a38}
.aw{font-size:36px;font-weight:700;line-height:1}
.al{font-family:'Space Mono',monospace;font-size:28px;font-weight:700}
.cf{font-size:13px;color:#64748b;margin-left:auto;font-family:'Space Mono',monospace}
.ir{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid #1e2a38}
.ii{padding:10px 12px;border-right:1px solid #1e2a38}
.ii:last-child{border-right:none}
.il{font-size:10px;color:#64748b;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px}
.iv{font-family:'Space Mono',monospace;font-size:14px;font-weight:700}
.wg{color:#00ff88}.wa{color:#ffaa00}.wm{color:#64748b}.ws{color:#ff3b5c}
.row{display:flex;justify-content:space-between;padding:6px 16px;border-bottom:1px solid #1e2a38}
.lb{color:#64748b;font-size:12px}.vl{font-family:'Space Mono',monospace;font-size:13px}
.zb2{color:#ffaa00;letter-spacing:1px}
.lg{display:grid;grid-template-columns:repeat(3,1fr);border-bottom:1px solid #1e2a38}
.lc{padding:12px;text-align:center;border-right:1px solid #1e2a38}
.lc:last-child{border-right:none}
.t1{background:rgba(0,255,136,.04)}.t2{background:rgba(255,170,0,.04)}.t3{background:rgba(100,116,139,.04)}
.lt{font-size:10px;color:#64748b;letter-spacing:1px;margin-bottom:6px}
.lv{font-family:'Space Mono',monospace;font-size:28px;font-weight:700}
.ls{font-size:10px;color:#64748b;margin-top:2px}
.eb{padding:12px 16px;border-bottom:1px solid #1e2a38;background:rgba(0,204,255,.03)}
.et{font-size:10px;letter-spacing:2px;color:#00ccff;text-transform:uppercase;margin-bottom:10px;font-weight:700}
.eg{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.ei{display:flex;flex-direction:column;gap:2px}
.sk{color:#ffaa00;font-size:15px}.pm{color:#00ccff}.dv{color:#ffaa00}
.dr{display:flex;justify-content:space-between;margin-top:8px;padding-top:8px;border-top:1px solid #1e2a38}
.hi .dh{color:#00ff88;font-size:15px}
.xb{padding:12px 16px;border-bottom:1px solid #1e2a38;background:rgba(255,170,0,.04)}
.xt{font-size:10px;letter-spacing:2px;color:#ffaa00;text-transform:uppercase;margin-bottom:8px;font-weight:700}
.xr{display:flex;justify-content:space-between;margin-bottom:4px}
.xtm{color:#ffaa00;font-size:14px}
.cd{font-family:'Space Mono',monospace;font-size:28px;font-weight:700;color:#ffaa00;
  text-align:center;padding:10px 0 4px;letter-spacing:4px}
.cd.done{color:#ff3b5c;animation:pu 1s infinite}
@keyframes pu{0%,100%{opacity:1}50%{opacity:.4}}
.wd{border-bottom:1px solid #1e2a38}
.wt{padding:8px 16px 6px;font-size:10px;letter-spacing:2px;color:#64748b;text-transform:uppercase;font-weight:700}
.wt2{width:100%;border-collapse:collapse}
.wt2 th{padding:6px 12px;background:#111820;font-size:10px;letter-spacing:1px;color:#64748b;
  text-align:left;text-transform:uppercase;border-bottom:1px solid #1e2a38}
.wt2 td{padding:6px 12px;border-bottom:1px solid #1e2a38;vertical-align:middle;font-size:12px}
.wt2 tr:last-child td{border-bottom:none}
.lp{font-family:'Space Mono',monospace;font-size:12px;color:#ffaa00}
.wc{font-family:'Space Mono',monospace;font-size:14px;font-weight:700}
.nt{font-size:11px;color:#64748b}
.no-pat{color:#64748b;font-style:italic;text-align:center;padding:12px!important}
.pill{padding:3px 8px;border:1px solid;border-radius:2px;font-size:11px;font-weight:600;letter-spacing:1px}
.pill.sm{font-size:10px;padding:2px 6px}
.rw{display:flex;gap:6px;padding:8px 16px;border-bottom:1px solid #1e2a38;flex-wrap:wrap}
.cpr{display:flex;align-items:center;gap:8px;padding:8px 16px;
  font-size:12px;border-bottom:1px solid #1e2a38}
.sp{color:#1e2a38}
.csr{display:flex;align-items:center;gap:10px;padding:10px 16px;
  border-bottom:1px solid #1e2a38;background:rgba(0,204,255,.04);flex-wrap:wrap}
.csl{font-size:11px;color:#00ccff;letter-spacing:1px;text-transform:uppercase;
  font-weight:700;white-space:nowrap}
.csi{background:#080b0f;border:2px solid #00ccff;color:#c9d5e0;
  font-family:'Space Mono',monospace;font-size:15px;font-weight:700;
  padding:6px 10px;border-radius:2px;width:160px;cursor:text}
.csi:focus{outline:none;border-color:#00ff88;box-shadow:0 0 0 2px rgba(0,255,136,.2)}
.csb{padding:6px 20px;background:#00ccff;border:none;color:#080b0f;
  font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;
  letter-spacing:2px;cursor:pointer;border-radius:2px}
.csb:hover{background:#00aadd}
.csb:disabled{opacity:.4;cursor:not-allowed}
.csm{font-size:13px;font-family:'Space Mono',monospace;font-weight:700}
.csm.ok{color:#00ff88}.csm.err{color:#ff3b5c}
.trade-bar{display:flex;gap:8px;padding:8px 16px;border-bottom:1px solid #1e2a38;flex-wrap:wrap}
.place-btn{padding:6px 18px;background:#ffaa00;border:none;color:#080b0f;font-family:"Barlow Condensed",sans-serif;
  font-size:13px;font-weight:700;letter-spacing:1px;cursor:pointer;border-radius:2px;margin-right:4px}
.place-btn:hover{opacity:.85}
.log-btn{padding:6px 16px;background:#00ff88;border:none;color:#080b0f;font-family:"Barlow Condensed",sans-serif;
  font-size:13px;font-weight:700;letter-spacing:1px;cursor:pointer;border-radius:2px}
.log-btn:hover{opacity:.85}
.close-btn{padding:6px 16px;background:transparent;border:1px solid #ff3b5c;color:#ff3b5c;
  font-family:"Barlow Condensed",sans-serif;font-size:13px;font-weight:700;cursor:pointer;border-radius:2px}
.close-btn:hover{background:rgba(255,59,92,.1)}
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(0,0,0,.7);z-index:100;align-items:center;justify-content:center}
.modal.open{display:flex}
.modal-box{background:#0d1117;border:1px solid #00ccff;border-radius:4px;padding:24px;
  min-width:320px;max-width:500px}
.modal-title{font-size:14px;font-weight:700;letter-spacing:2px;color:#00ccff;margin-bottom:16px}
.modal-row{display:flex;flex-direction:column;gap:4px;margin-bottom:12px}
.modal-lbl{font-size:11px;color:#64748b;letter-spacing:1px;text-transform:uppercase}
.modal-inp{background:#080b0f;border:1px solid #1e2a38;color:#c9d5e0;padding:8px;
  border-radius:2px;font-family:"Space Mono",monospace;font-size:14px}
.modal-inp:focus{outline:none;border-color:#00ccff}
.modal-actions{display:flex;gap:8px;margin-top:16px}
.modal-ok{flex:1;padding:8px;background:#00ccff;border:none;color:#080b0f;
  font-weight:700;cursor:pointer;border-radius:2px}
.modal-cancel{padding:8px 16px;background:transparent;border:1px solid #64748b;
  color:#64748b;cursor:pointer;border-radius:2px}
.modal-msg{margin-top:8px;font-size:12px;font-family:"Space Mono",monospace}
.st{padding:6px 16px;font-size:11px;color:#64748b;font-family:'Space Mono',monospace}
.rules{background:rgba(255,59,92,.08);border:1px solid rgba(255,59,92,.25);
  border-radius:4px;padding:10px 16px;grid-column:1/-1;display:flex;gap:24px;flex-wrap:wrap}
.ri{font-size:12px}
.rl{color:#ff3b5c;font-weight:700;margin-right:6px}
.breadth-panel{background:#0d1117;border:1px solid #1e2a38;border-radius:4px;
  grid-column:1/-1;padding:16px 20px;margin-top:0}
.bp-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:8px}
.bp-title{font-size:11px;letter-spacing:2px;color:#64748b;text-transform:uppercase;font-weight:700}
.bp-stats{display:flex;gap:20px;font-family:'Space Mono',monospace;font-size:13px}
.bp-adv{color:#00ff88;font-weight:700}.bp-dec{color:#ff3b5c;font-weight:700}
.bp-score{font-weight:700}.bp-cov{color:#64748b;font-size:11px}
.bp-canvas-wrap{position:relative;height:140px}
canvas#breadth-chart{width:100%;height:140px;display:block}
.bp-nodata{color:#64748b;font-size:12px;font-style:italic;text-align:center;padding:40px 0}
.footer{text-align:center;padding:16px;font-size:11px;color:#4a5568;
  font-family:'Space Mono',monospace;letter-spacing:1px}
"""

JS = """
function updateClock(){
  var n=new Date(),i=new Date(n.toLocaleString("en-US",{timeZone:"Asia/Kolkata"}));
  var p=function(x){return String(x).padStart(2,"0")};
  document.querySelector(".clk").textContent=p(i.getHours())+":"+p(i.getMinutes())+":"+p(i.getSeconds())+" IST";
}
setInterval(updateClock,1000);

function updateCountdowns(){
  document.querySelectorAll(".cd[data-exit]").forEach(function(el){
    var d=Math.floor((new Date(el.dataset.exit)-new Date())/1000);
    if(d<=0){el.textContent="EXIT NOW";el.classList.add("done");}
    else{var m=Math.floor(d/60),s=d%60;
      el.textContent=String(m).padStart(2,"0")+":"+String(s).padStart(2,"0");
      el.classList.remove("done");}
  });
}
updateCountdowns();setInterval(updateCountdowns,1000);

function showPlaceOrder(sym){
  document.getElementById('po-sym').value=sym;
  document.getElementById('po-sym-disp').textContent=sym;
  document.getElementById('po-msg').textContent='';
  document.getElementById('modal-place').classList.add('open');
}
function submitPlaceOrder(){
  var sym=document.getElementById('po-sym').value;
  var msg=document.getElementById('po-msg');
  msg.textContent='Placing order...';msg.style.color='#ffaa00';
  fetch('/place_order?symbol='+sym,{method:'POST'})
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.ok){
        msg.textContent='FILLED @ INR '+d.fill_price+' | Exit: '+d.exit_ts_ist;
        msg.style.color='#00ff88';
        setTimeout(function(){document.getElementById('modal-place').classList.remove('open');},3000);
      }else{msg.textContent='ERROR: '+d.error;msg.style.color='#ff3b5c';}
    }).catch(function(){msg.textContent='Request failed';msg.style.color='#ff3b5c';});
}
function showLogTrade(sym){
  document.getElementById('lt-sym').value=sym;
  document.getElementById('lt-price').value='';
  document.getElementById('lt-msg').textContent='';
  document.getElementById('modal-log').classList.add('open');
  setTimeout(function(){document.getElementById('lt-price').focus();},100);
}
function submitLogTrade(){
  var sym=document.getElementById('lt-sym').value;
  var price=parseFloat(document.getElementById('lt-price').value);
  var msg=document.getElementById('lt-msg');
  if(!price||price<=0){msg.textContent='Enter a valid premium price';msg.style.color='#ff3b5c';return;}
  msg.textContent='Logging...';msg.style.color='#64748b';
  fetch('/log_trade?symbol='+sym+'&entry_price='+price,{method:'POST'})
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.ok){msg.textContent='Logged! Exit at '+d.exit_ts_ist;msg.style.color='#00ff88';
        setTimeout(function(){document.getElementById('modal-log').classList.remove('open');},2000);}
      else{msg.textContent='Error: '+d.error;msg.style.color='#ff3b5c';}
    }).catch(function(){msg.textContent='Failed';msg.style.color='#ff3b5c';});
}
function showCloseForm(sym){
  document.getElementById('cl-sym').value=sym;
  document.getElementById('cl-id').value='';
  document.getElementById('cl-price').value='';
  document.getElementById('cl-msg').textContent='';
  document.getElementById('modal-close').classList.add('open');
  setTimeout(function(){document.getElementById('cl-id').focus();},100);
}
function submitClose(){
  var sym=document.getElementById('cl-sym').value;
  var tid=document.getElementById('cl-id').value.trim();
  var price=parseFloat(document.getElementById('cl-price').value);
  var msg=document.getElementById('cl-msg');
  if(!tid){msg.textContent='Enter trade ID';msg.style.color='#ff3b5c';return;}
  if(!price||price<=0){msg.textContent='Enter exit price';msg.style.color='#ff3b5c';return;}
  msg.textContent='Closing...';msg.style.color='#64748b';
  fetch('/close_trade?trade_id='+tid+'&exit_price='+price,{method:'POST'})
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.ok){msg.textContent='Closed! PnL: '+d.pnl_str;msg.style.color='#00ff88';
        setTimeout(function(){document.getElementById('modal-close').classList.remove('open');},2000);}
      else{msg.textContent='Error: '+d.error;msg.style.color='#ff3b5c';}
    }).catch(function(){msg.textContent='Failed';msg.style.color='#ff3b5c';});
}
function closeModal(id){document.getElementById(id).classList.remove('open');}
function setCap(sym){
  var inp=document.getElementById("csi-"+sym);
  var msg=document.getElementById("csm-"+sym);
  var disp=document.getElementById("cdp-"+sym);
  var btn=document.getElementById("csb-"+sym);
  var val=parseFloat(inp.value);
  if(!val||val<10000){msg.textContent="Min 10,000";msg.className="csm err";return;}
  btn.textContent="...";btn.disabled=true;msg.textContent="";msg.className="csm";
  fetch("/set_capital?symbol="+sym+"&capital="+val,{method:"POST"})
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.ok){
        msg.textContent="Saved";msg.className="csm ok";
        if(disp)disp.textContent="\u20b9"+Math.round(d.capital).toLocaleString("en-IN");
        setTimeout(function(){msg.textContent="";msg.className="csm";},3000);
      }else{msg.textContent="Error: "+d.error;msg.className="csm err";}
      btn.textContent="SET";btn.disabled=false;
    })
    .catch(function(){msg.textContent="Failed";msg.className="csm err";btn.textContent="SET";btn.disabled=false;});
}
"""


def breadth_panel(rows):
    if not rows:
        return '''<div class="breadth-panel">
          <div class="bp-header"><span class="bp-title">&#9632; Market Breadth &mdash; NSE Universe</span>
          <span class="bp-cov">No data &mdash; WebSocket starting or market closed</span></div>
          <div class="bp-nodata">Breadth data appears after first pipeline cycle (~09:20 IST)</div>
        </div>'''
    latest = rows[-1]
    adv = latest.get("advances", 0) or 0
    dec = latest.get("declines", 0) or 0
    score = latest.get("breadth_score", 0) or 0
    cov = latest.get("coverage_pct", 0) or 0
    score_col = "#00ff88" if score > 20 else "#ff3b5c" if score < -20 else "#ffaa00"
    regime = "BULLISH" if score > 20 else "BEARISH" if score < -20 else "NEUTRAL"
    import json as _json
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo as _ZI
    times, advs, decs = [], [], []
    for row in rows:
        try:
            ts = datetime.fromisoformat(row["ts"].replace("Z","+00:00"))
            ts_ist = ts.astimezone(_ZI("Asia/Kolkata"))
            times.append(ts_ist.strftime("%H:%M"))
            advs.append(row.get("advances") or 0)
            decs.append(row.get("declines") or 0)
        except: pass
    t_json = _json.dumps(times)
    a_json = _json.dumps(advs)
    d_json = _json.dumps(decs)
    return f'''<div class="breadth-panel">
      <div class="bp-header">
        <span class="bp-title">&#9632; Market Breadth &mdash; NSE Universe</span>
        <div class="bp-stats">
          <span class="bp-adv">&#9650; {adv:,} ADV</span>
          <span class="bp-dec">&#9660; {dec:,} DEC</span>
          <span class="bp-score" style="color:{score_col}">{regime} ({score:+.0f})</span>
          <span class="bp-cov">COV {cov:.0f}%</span>
        </div>
      </div>
      <div class="bp-canvas-wrap"><canvas id="breadth-chart"></canvas></div>
      <script>(function(){{
        var times={t_json},advs={a_json},decs={d_json};
        var c=document.getElementById("breadth-chart");
        if(!c||!times.length)return;
        c.width=c.parentElement.offsetWidth;c.height=140;
        var ctx=c.getContext("2d"),W=c.width,H=c.height;
        var PAD={{t:10,r:65,b:24,l:50}},pw=W-PAD.l-PAD.r,ph=H-PAD.t-PAD.b;
        var maxV=Math.max(Math.max.apply(null,advs),Math.max.apply(null,decs),100);
        function px(i){{return PAD.l+i*(pw/Math.max(times.length-1,1));}}
        function py(v){{return PAD.t+ph-(v/maxV)*ph;}}
        ctx.strokeStyle="#1e2a38";ctx.lineWidth=1;
        [0,Math.round(maxV/2),maxV].forEach(function(v){{
          var y=py(v);ctx.beginPath();ctx.moveTo(PAD.l,y);ctx.lineTo(W-PAD.r,y);ctx.stroke();
          ctx.fillStyle="#4a5568";ctx.font="10px monospace";ctx.textAlign="right";ctx.fillText(v,PAD.l-4,y+4);
        }});
        var step=Math.max(1,Math.floor(times.length/8));
        ctx.fillStyle="#4a5568";ctx.font="10px monospace";ctx.textAlign="center";
        times.forEach(function(t,i){{if(i%step===0||i===times.length-1)ctx.fillText(t,px(i),H-4);}});
        ctx.beginPath();ctx.strokeStyle="#ff3b5c";ctx.lineWidth=2;ctx.lineJoin="round";
        decs.forEach(function(v,i){{i===0?ctx.moveTo(px(i),py(v)):ctx.lineTo(px(i),py(v));}});ctx.stroke();
        ctx.beginPath();ctx.strokeStyle="#00ff88";ctx.lineWidth=2;ctx.lineJoin="round";
        advs.forEach(function(v,i){{i===0?ctx.moveTo(px(i),py(v)):ctx.lineTo(px(i),py(v));}});ctx.stroke();
        ctx.fillStyle="#00ff88";ctx.fillRect(W-PAD.r+4,PAD.t,10,2);
        ctx.fillStyle="#c9d5e0";ctx.font="11px sans-serif";ctx.textAlign="left";ctx.fillText("ADV",W-PAD.r+18,PAD.t+4);
        ctx.fillStyle="#ff3b5c";ctx.fillRect(W-PAD.r+4,PAD.t+14,10,2);ctx.fillText("DEC",W-PAD.r+18,PAD.t+18);
      }})();</script>
    </div>'''

def render():
    now  = datetime.now(tz=timezone.utc).astimezone(IST)
    zlbl, zcol = session_zone(now)

    sigs = {}
    for s in SYMBOLS:
        try:    sigs[s] = build(s)
        except Exception as e: sigs[s] = {"symbol":s,"error":str(e)}

    cards = "\n".join(card(sigs[s]) for s in SYMBOLS)
    try:
        _brows = fetch_breadth_history()
        _breadth_html = breadth_panel(_brows)
    except Exception:
        _breadth_html = ""


    _page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="60">
<title>MERDIAN SIGNAL</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Barlow+Condensed:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="topbar">
  <div class="logo">MERDIAN &middot; SIGNAL</div>
  <div style="display:flex;align-items:center;gap:10px">
    <div class="clk">{now.strftime("%H:%M:%S IST")}</div>
    <div class="dt">{now.strftime("%a %d %b %Y")}</div>
  </div>
  <div class="zb" style="color:{zcol};border-color:{zcol}">{zlbl}</div>
  <button class="rb" onclick="location.reload()">&#8635; REFRESH</button>
</div>
<div class="main">
  {cards}
  %%BREADTH_PANEL%%
  <div class="rules">
    <div class="ri"><span class="rl">HARD SKIP</span>BEAR_OB 13:00&ndash;14:30 IST &middot; 17% WR</div>
    <div class="ri"><span class="rl">NO SIGNAL</span>After 15:00 IST &middot; Power hour</div>
    <div class="ri"><span class="rl">EXIT RULE</span>T+30m fixed &middot; All patterns &middot; All tiers</div>
    <div class="ri"><span class="rl">NEAR EXPIRY</span>BEAR_OB DTE=0/1 &middot; Combined structure</div>
  </div>
</div>
<div class="footer">MERDIAN &middot; git cfba66e &middot; Kelly C (Half Kelly) &middot; Port {PORT}</div>
<!-- Phase 4B: Place Order Modal -->
<div class="modal" id="modal-place">
  <div class="modal-box">
    <div class="modal-title">&#9889; PLACE ORDER — DHAN AUTO</div>
    <input type="hidden" id="po-sym">
    <div class="modal-row">
      <span class="modal-lbl">Symbol</span>
      <span style="font-family:monospace;color:#ffaa00;font-size:18px;font-weight:700" id="po-sym-disp"></span>
    </div>
    <div style="padding:8px 0;font-size:12px;color:#64748b">
      Market order will be placed at current ATM strike, tier lots, intraday.<br>
      T+30m exit alert will fire automatically.
    </div>
    <div class="modal-msg" id="po-msg"></div>
    <div class="modal-actions">
      <button class="modal-ok" style="background:#ffaa00" onclick="submitPlaceOrder()">CONFIRM PLACE ORDER</button>
      <button class="modal-cancel" onclick="closeModal('modal-place')">Cancel</button>
    </div>
  </div>
</div>

<!-- Phase 4A: Log Trade Modal -->
<div class="modal" id="modal-log">
  <div class="modal-box">
    <div class="modal-title">&#128203; LOG TRADE</div>
    <input type="hidden" id="lt-sym">
    <div class="modal-row">
      <span class="modal-lbl">Symbol</span>
      <span style="font-family:monospace;color:#00ccff" id="lt-sym-disp"></span>
    </div>
    <div class="modal-row">
      <label class="modal-lbl" for="lt-price">Premium paid per unit (INR)</label>
      <input class="modal-inp" id="lt-price" type="number" min="0.5" step="0.5" placeholder="e.g. 85.50">
    </div>
    <div class="modal-msg" id="lt-msg"></div>
    <div class="modal-actions">
      <button class="modal-ok" onclick="submitLogTrade()">LOG TRADE</button>
      <button class="modal-cancel" onclick="closeModal('modal-log')">Cancel</button>
    </div>
  </div>
</div>
<!-- Phase 4A: Close Trade Modal -->
<div class="modal" id="modal-close">
  <div class="modal-box">
    <div class="modal-title">&#10060; CLOSE TRADE</div>
    <input type="hidden" id="cl-sym">
    <div class="modal-row">
      <label class="modal-lbl" for="cl-id">Trade ID (first 8 chars)</label>
      <input class="modal-inp" id="cl-id" type="text" placeholder="e.g. a1b2c3d4">
    </div>
    <div class="modal-row">
      <label class="modal-lbl" for="cl-price">Exit price per unit (INR)</label>
      <input class="modal-inp" id="cl-price" type="number" min="0" step="0.5" placeholder="e.g. 120.00">
    </div>
    <div class="modal-msg" id="cl-msg"></div>
    <div class="modal-actions">
      <button class="modal-ok" onclick="submitClose()">CLOSE &amp; LOG PnL</button>
      <button class="modal-cancel" onclick="closeModal('modal-close')">Cancel</button>
    </div>
  </div>
</div>
<script>{JS}</script>
</body>
</html>"""

    _page = _page.replace("%%BREADTH_PANEL%%", _breadth_html)
    return _page

# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.startswith("/set_capital"):
            qs  = parse_qs(urlparse(self.path).query)
            sym = qs.get("symbol",[None])[0]
            cap = qs.get("capital",[None])[0]
            try:
                if not sym or not cap: raise ValueError("missing params")
                v  = float(cap)
                ts = datetime.now(timezone.utc).isoformat()
                sb.table("capital_tracker").update({"capital":v,"updated_at":ts}).eq("symbol",sym.upper()).execute()
                body = json.dumps({"ok":True,"symbol":sym,"capital":v}).encode()
            except Exception as e:
                body = json.dumps({"ok":False,"error":str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",len(body))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/log_trade"):
            # Phase 4A: manual trade log (entry price provided by operator)
            qs   = parse_qs(urlparse(self.path).query)
            sym  = (qs.get("symbol",      [None])[0] or "").upper()
            price = qs.get("entry_price", [None])[0]
            try:
                if not sym or not price:
                    raise ValueError("symbol and entry_price required")
                from merdian_trade_logger import (
                    fetch_latest_signal, get_active_lots, log_trade, LOT_SIZE
                )
                sig = fetch_latest_signal(sym)
                if not sig:
                    raise ValueError(f"No signal for {sym}")
                strike     = sig.get("atm_strike")
                expiry     = sig.get("expiry_date")
                option_type = "PE" if sig.get("action") == "BUY_PE" else "CE"
                lots       = get_active_lots(sig)
                sig_ts     = sig.get("ts", "")
                entry_price = float(price)
                trade_id, exit_ts = log_trade(
                    sym, strike, expiry, option_type, lots, entry_price, sig_ts
                )
                from zoneinfo import ZoneInfo as _ZI
                exit_ist = exit_ts.astimezone(_ZI("Asia/Kolkata")).strftime("%H:%M IST")
                body = json.dumps({"ok": True, "trade_id": trade_id, "exit_ts_ist": exit_ist}).encode()
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif self.path.startswith("/close_trade"):
            # Phase 4A: manual trade close (exit price provided by operator)
            qs   = parse_qs(urlparse(self.path).query)
            tid  = qs.get("trade_id",   [None])[0]
            price = qs.get("exit_price", [None])[0]
            try:
                if not tid or not price:
                    raise ValueError("trade_id and exit_price required")
                from merdian_trade_logger import close_trade as _close, LOT_SIZE
                pnl = _close(tid, float(price))
                pnl_str = f"INR {pnl:+,.0f}" if pnl is not None else "N/A"
                body = json.dumps({"ok": True, "pnl": pnl, "pnl_str": pnl_str}).encode()
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif self.path.startswith("/place_order"):
            # Phase 4B: automated order placement via AWS order placer
            import os as _os
            import requests as _req
            qs  = parse_qs(urlparse(self.path).query)
            sym = (qs.get("symbol", [None])[0] or "").upper()
            aws_url = _os.getenv("AWS_ORDER_PLACER_URL", "http://13.63.27.85:8767").rstrip("/")
            try:
                if not sym:
                    raise ValueError("symbol required")
                # Get latest signal to extract order params
                sig = fetch_signal(sym)
                if not sig:
                    raise ValueError(f"No signal for {sym}")
                action = sig.get("action", "DO_NOTHING")
                if action not in ("BUY_PE", "BUY_CE"):
                    raise ValueError(f"Signal is {action} — nothing to place")
                strike     = sig.get("atm_strike")
                expiry     = str(sig.get("expiry_date", ""))[:10]
                option_type = "PE" if action == "BUY_PE" else "CE"
                tier       = sig.get("ict_tier", "TIER3")
                lots_key   = {"TIER1": "ict_lots_t1", "TIER2": "ict_lots_t2"}.get(tier, "ict_lots_t3")
                lots       = sig.get(lots_key) or sig.get("ict_lots_t1") or 1
                signal_ts  = sig.get("ts", "")
                # Relay to AWS order placer
                relay_url = (
                    f"{aws_url}/place_order"
                    f"?symbol={sym}&strike={strike}&expiry_date={expiry}"
                    f"&option_type={option_type}&lots={lots}&signal_ts={signal_ts}"
                )
                r = _req.post(relay_url, timeout=60)
                result = r.json()
                body = json.dumps(result).encode()
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif self.path.startswith("/square_off"):
            # Phase 4B: automated square off via AWS order placer
            import os as _os
            import requests as _req
            qs           = parse_qs(urlparse(self.path).query)
            trade_log_id = qs.get("trade_log_id", [None])[0]
            aws_url      = _os.getenv("AWS_ORDER_PLACER_URL", "http://13.63.27.85:8767").rstrip("/")
            try:
                if not trade_log_id:
                    raise ValueError("trade_log_id required")
                relay_url = f"{aws_url}/square_off?trade_log_id={trade_log_id}"
                r = _req.post(relay_url, timeout=60)
                result = r.json()
                body = json.dumps(result).encode()
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404); self.end_headers()

    def do_GET(self):
        try:
            html = render()
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",len(body))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            err = f"<pre>{traceback.format_exc()}</pre>".encode()
            self.send_response(500)
            self.send_header("Content-Type","text/html")
            self.end_headers()
            self.wfile.write(err)

    def log_message(self, *a): pass

def main():
    svr = HTTPServer(("0.0.0.0", PORT), Handler)
    now = datetime.now(tz=timezone.utc).astimezone(IST)
    print(f"[{now.strftime('%H:%M:%S IST')}] MERDIAN Signal Dashboard  http://localhost:{PORT}")
    try: svr.serve_forever()
    except KeyboardInterrupt: print("\nStopped.")

if __name__ == "__main__":
    main()

