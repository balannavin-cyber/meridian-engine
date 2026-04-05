"""
backfill_gamma_metrics.py

Computes gamma metrics (GEX, regime, flip level) for historical dates
using hist_option_bars_1m + hist_spot_bars_1m.

Writes to hist_gamma_metrics (separate from live gamma_metrics).

Usage:
    python backfill_gamma_metrics.py 2025-10-15
    python backfill_gamma_metrics.py 2025-10-15 NIFTY
"""
from __future__ import annotations
import json, math, os, sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
RISK_FREE_RATE = 0.065
IST = timezone(timedelta(hours=5, minutes=30))

def sb_headers():
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"}

def sb_get(path, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{path}{'?' + params if params else ''}"
    r = requests.get(url, headers=sb_headers(), timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"GET {path} failed {r.status_code}: {r.text[:200]}")
    return r.json()

def sb_upsert(table, rows):
    if not rows: return 0
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    h = {**sb_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"}
    inserted = 0
    for i in range(0, len(rows), 500):
        batch = rows[i:i+500]
        r = requests.post(url, headers=h, json=batch, timeout=60)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"UPSERT {table} failed {r.status_code}: {r.text[:200]}")
        inserted += len(batch)
    return inserted

# Black-Scholes pure Python
def norm_cdf(x): return 0.5 * math.erfc(-x / math.sqrt(2))
def norm_pdf(x): return math.exp(-0.5*x*x) / math.sqrt(2*math.pi)

def bs_price(S, K, T, r, sigma, opt):
    if T <= 1e-6 or sigma <= 1e-6:
        return max(S-K,0) if opt=="CE" else max(K-S,0)
    d1 = (math.log(S/K)+(r+0.5*sigma**2)*T)/(sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)
    if opt=="CE": return S*norm_cdf(d1)-K*math.exp(-r*T)*norm_cdf(d2)
    return K*math.exp(-r*T)*norm_cdf(-d2)-S*norm_cdf(-d1)

def bs_gamma_greek(S, K, T, r, sigma):
    if T<=1e-6 or sigma<=1e-6: return 0.0
    d1=(math.log(S/K)+(r+0.5*sigma**2)*T)/(sigma*math.sqrt(T))
    return norm_pdf(d1)/(S*sigma*math.sqrt(T))

def implied_vol(S, K, T, r, price, opt):
    if T<=1e-6: return None
    intrinsic=max(S-K,0) if opt=="CE" else max(K-S,0)
    if price<=intrinsic+0.01: return None
    lo,hi=0.001,10.0
    for _ in range(100):
        mid=(lo+hi)/2
        p=bs_price(S,K,T,r,mid,opt)
        if abs(p-price)<0.001: return mid
        if p<price: lo=mid
        else: hi=mid
    return (lo+hi)/2

def signed_gex(gamma, oi, spot, opt):
    base=gamma*oi*(spot**2)
    return -base if opt=="PE" else base

def compute_flip_level(rows, spot):
    strike_gex={}
    for r in rows:
        s=float(r["strike"])
        strike_gex[s]=strike_gex.get(s,0)+r["_gex"]
    strikes=sorted(strike_gex)
    if not strikes: return None
    cum=0.0; prev=None
    for s in strikes:
        prev_cum=cum; cum+=strike_gex[s]
        if prev is not None and prev_cum*cum<0:
            return prev+(s-prev)*abs(prev_cum)/(abs(prev_cum)+abs(cum))
        prev=s
    return None

def gamma_zone(pct):
    if pct is None: return "NO_FLIP"
    if pct<0.5: return "HIGH_GAMMA"
    if pct<1.5: return "MID_GAMMA"
    return "LOW_GAMMA"

def determine_regime(net_gex, flip_level):
    if flip_level is None: return "NO_FLIP"
    return "LONG_GAMMA" if net_gex>=0 else "SHORT_GAMMA"

def get_instrument_id(symbol):
    rows=sb_get("instruments",f"symbol=eq.{symbol}&select=id")
    if not rows: raise RuntimeError(f"Instrument not found: {symbol}")
    return rows[0]["id"]

def get_spot_map(instrument_id, trade_date):
    rows=sb_get("hist_spot_bars_1m",
                f"instrument_id=eq.{instrument_id}&trade_date=eq.{trade_date}&select=bar_ts,close&limit=1000")
    return {r["bar_ts"]:float(r["close"]) for r in rows if r.get("close")}

def get_option_bars(instrument_id, trade_date):
    all_rows=[]; offset=0
    while True:
        rows=sb_get("hist_option_bars_1m",
                    f"instrument_id=eq.{instrument_id}&trade_date=eq.{trade_date}"
                    f"&select=bar_ts,strike,option_type,close,oi,expiry_date&limit=1000&offset={offset}")
        all_rows.extend(rows)
        if len(rows)<1000: break
        offset+=1000
    return all_rows

def already_done(symbol, trade_date):
    rows=sb_get("hist_gamma_metrics",f"symbol=eq.{symbol}&trade_date=eq.{trade_date}&select=id&limit=1")
    return len(rows)>0

def process_ts(ts, spot, option_rows, expiry_date, symbol, instrument_id, trade_date):
    bar_dt=datetime.fromisoformat(ts.replace("Z","+00:00"))
    exp_dt=datetime.strptime(expiry_date,"%Y-%m-%d").replace(hour=15,minute=30,tzinfo=timezone.utc)
    T=max((exp_dt-bar_dt).total_seconds()/(365.25*24*3600),1e-6)
    enriched=[]
    for row in option_rows:
        price=float(row.get("close") or 0); strike=float(row.get("strike") or 0)
        oi=float(row.get("oi") or 0); opt=str(row.get("option_type","")).upper()
        if price<=0 or strike<=0 or oi<=0: continue
        iv=implied_vol(spot,strike,T,RISK_FREE_RATE,price,opt)
        if iv is None or iv<=0: continue
        g=bs_gamma_greek(spot,strike,T,RISK_FREE_RATE,iv)
        gex=signed_gex(g,oi,spot,opt)
        enriched.append({**row,"_gamma":g,"_iv":iv,"_gex":gex})
    if not enriched: return None
    net_gex=sum(r["_gex"] for r in enriched)
    flip_level=compute_flip_level(enriched,spot)
    flip_dist=abs(spot-flip_level) if flip_level else None
    flip_pct=(flip_dist/spot*100) if flip_dist else None
    regime=determine_regime(net_gex,flip_level)
    gz=gamma_zone(flip_pct)
    atm=round(spot/50)*50
    calls=[r for r in enriched if float(r["strike"])==atm and r["option_type"]=="CE"]
    puts=[r for r in enriched if float(r["strike"])==atm and r["option_type"]=="PE"]
    slope=None
    if calls and puts: slope=calls[0]["_iv"]-puts[0]["_iv"]
    return {
        "instrument_id":instrument_id,"symbol":symbol,"bar_ts":ts,
        "trade_date":trade_date,"spot":spot,
        "net_gex":round(net_gex,2),
        "flip_level":round(flip_level,2) if flip_level else None,
        "flip_distance":round(flip_dist,2) if flip_dist else None,
        "flip_distance_pct":round(flip_pct,4) if flip_pct else None,
        "straddle_slope":round(slope,6) if slope else None,
        "regime":regime,"gamma_zone":gz,
    }

def run(trade_date, symbol):
    print(f"{'='*72}\nBACKFILL GAMMA METRICS — {symbol} — {trade_date}\n{'='*72}")
    if already_done(symbol,trade_date):
        print("Already done. Skipping."); return 0
    iid=get_instrument_id(symbol)
    spot_map=get_spot_map(iid,trade_date)
    print(f"Spot timestamps: {len(spot_map)}")
    if not spot_map: print("No spot data. Skipping."); return 1
    bars=get_option_bars(iid,trade_date)
    print(f"Option rows: {len(bars)}")
    if not bars: print("No option data. Skipping."); return 1
    expiries=sorted(set(r["expiry_date"] for r in bars if r.get("expiry_date")))
    upcoming=[e for e in expiries if date.fromisoformat(e)>=date.fromisoformat(trade_date)]
    if not upcoming: print("No upcoming expiry. Skipping."); return 1
    expiry=upcoming[0]; print(f"Using expiry: {expiry}")
    near=[r for r in bars if r.get("expiry_date")==expiry]
    ts_groups={}
    for r in near: ts_groups.setdefault(r["bar_ts"],[]).append(r)
    print(f"Timestamps: {len(ts_groups)}")
    out=[]; skipped=0
    for ts,rows in sorted(ts_groups.items()):
        spot=spot_map.get(ts)
        if not spot: skipped+=1; continue
        res=process_ts(ts,spot,rows,expiry,symbol,iid,trade_date)
        if res: out.append(res)
        else: skipped+=1
    print(f"Computed: {len(out)} | Skipped: {skipped}")
    if not out: print("No rows."); return 1
    inserted=sb_upsert("hist_gamma_metrics",out)
    print(f"Upserted: {inserted} rows\nBACKFILL GAMMA METRICS COMPLETE")
    return 0

def main():
    if len(sys.argv)<2:
        print("Usage: python backfill_gamma_metrics.py YYYY-MM-DD [NIFTY|SENSEX]"); return 1
    trade_date=sys.argv[1]
    symbols=["NIFTY","SENSEX"] if len(sys.argv)<3 else [sys.argv[2].upper()]
    return max(run(trade_date,s) for s in symbols)

if __name__=="__main__":
    raise SystemExit(main())
