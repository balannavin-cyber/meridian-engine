import argparse, sys
from collections import Counter
import measure_rate_sensitivity as m

R = m.R_FLAT

def regime_sign(net_gex, flip, eps=2.5e5):  # ENH-07A-P2 rescore v1
    # sign-based: when no flip crossing is found but net_gex is decisively
    # non-zero, classify by sign (matches how the live engine reads regime).
    if flip is not None:
        return 'LONG_GAMMA' if net_gex >= 0 else 'SHORT_GAMMA'
    if net_gex >= eps:  return 'LONG_GAMMA'
    if net_gex <= -eps: return 'SHORT_GAMMA'
    return 'NO_FLIP'


def bget(table, params, cap_pages=4, page=1000):
    """Bounded reader — never pages the whole table. cap_pages*page row ceiling."""
    base, h = m._cfg()
    import requests
    from urllib.parse import urlencode
    out, off, pages = [], 0, 0
    while pages < cap_pages:
        p = dict(params, limit=str(page), offset=str(off))
        r = requests.get(f"{base}/rest/v1/{table}?{urlencode(p)}", headers=h, timeout=90)
        if r.status_code >= 400:
            raise RuntimeError(f"{table} {r.status_code}: {r.text[:120]}")
        b = r.json()
        out.extend(b)
        if len(b) < page:
            break
        off += page; pages += 1
    return out


def recon_at(iid, raw_bts):
    s = bget("hist_spot_bars_1m", {"select": "close", "instrument_id": f"eq.{iid}",
                                   "bar_ts": f"eq.{raw_bts}"}, cap_pages=1)
    if not s:
        return None
    spot = float(s[0]["close"])
    o = bget("hist_option_bars_1m", {"select": "strike,option_type,close,oi,expiry_date",
             "instrument_id": f"eq.{iid}", "bar_ts": f"eq.{raw_bts}", "order": "expiry_date.asc"}, cap_pages=2)
    if not o:
        return None
    from datetime import datetime
    d = m.parse_ts(raw_bts).date().isoformat()
    exps = [r["expiry_date"] for r in o if r.get("expiry_date") and r["expiry_date"] >= d]
    if not exps:
        return None
    expiry = min(exps)
    chain = [r for r in o if r.get("expiry_date") == expiry and float(r.get("close") or 0) > 0]
    if len(chain) < 6:
        return None
    T = (datetime.fromisoformat(expiry).date() - datetime.fromisoformat(d).date()).days / 365.0
    if T <= 0:
        return None
    built = []
    for r in chain:
        K = float(r["strike"]); P = float(r["close"]); ot = str(r["option_type"]); oi = float(r.get("oi") or 0)
        iv = m.implied_vol(P, spot, K, T, R, ot)
        if iv is None:
            continue
        built.append({"strike": K, "otype": ot, "oi": oi, "g": m.bs_gamma(spot, K, T, R, iv)})
    if len(built) < 6:
        return None
    sm = m.build_strike_map(built, spot, "g")
    ng = sum(sm.values()); flip = m.compute_flip_level(sm, spot)
    return spot, ng, flip, m.regime(ng, flip)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2025-09-19")  # a date the rate-probe already showed clean
    ap.add_argument("--tol-min", type=float, default=3.0)
    args = ap.parse_args()
    d = args.date
    iid = m.nifty_iid()

    live = bget("gamma_metrics", {"select": "*", "symbol": "eq.NIFTY",
                "and": f"(ts.gte.{d}T00:00:00,ts.lte.{d}T23:59:59)", "order": "ts.asc"}, cap_pages=2)
    if not live:
        print(f"No live gamma_metrics NIFTY on {d}."); return 1
    cols = list(live[0].keys())
    reg_c = next((c for c in cols if {str(r[c]).upper() for r in live if r.get(c)} &
                  {"LONG_GAMMA","SHORT_GAMMA","NO_FLIP","PINNED"}), None)
    ng_c = "net_gex" if "net_gex" in cols else None
    print(f"cols: regime={reg_c} net_gex={ng_c}")
    if not reg_c or not ng_c:
        print("col detect failed:", cols); return 1

    medh = sorted(m.parse_ts(r["ts"]).hour for r in live)[len(live)//2]
    is_utc = medh < 9
    print(f"live median hour={medh} -> {'UTC(+330)' if is_utc else 'IST-as-UTC'}")

    tl = bget("hist_spot_bars_1m", {"select": "bar_ts", "instrument_id": f"eq.{iid}",
              "trade_date": f"eq.{d}", "order": "bar_ts.asc"}, cap_pages=2)
    tl = [(m.parse_ts(r["bar_ts"]).hour*60 + m.parse_ts(r["bar_ts"]).minute, r["bar_ts"]) for r in tl]
    if not tl:
        print(f"no hist spot timeline {d}"); return 1

    n=reg_ok=sgn_ok=0; lmix=Counter(); rows=[]; ratios=[] ; reg2_ok=0
    for lr in live:
        dt = m.parse_ts(lr["ts"]); tmin = dt.hour*60+dt.minute + (330 if is_utc else 0)
        cand = min(tl, key=lambda x: abs(x[0]-tmin))
        if abs(cand[0]-tmin) > args.tol_min:
            continue
        rc = recon_at(iid, cand[1])
        if rc is None:
            continue
        spot, rng, rflip, rreg = rc
        lng = float(lr[ng_c]) if lr.get(ng_c) is not None else None
        lreg = str(lr[reg_c]).upper() if lr.get(reg_c) else "?"
        lmix[lreg]+=1; n+=1
        rm = lreg==rreg; sm_ok = lng is not None and (lng>=0)==(rng>=0)
        reg_ok+=rm; sgn_ok+=sm_ok
        rreg2 = regime_sign(rng, rflip)  # ENH-07A-P2 rescore v1
        reg2_ok += (lreg == rreg2)
        if lng not in (None,0): ratios.append(rng/lng)
        rows.append(f"{cand[1][:16]:>16} {spot:>8.0f} {lng or 0:>11.0f} {rng:>11.0f} {lreg:>11} {rreg:>11} {'OK' if rm else 'XX':>4} {'.' if sm_ok else 'SGN':>4}")

    print(f"\n{'hist_bar':>16} {'spot':>8} {'live_ngex':>11} {'recon_ngex':>11} {'live_reg':>11} {'recon_reg':>11} {'REG':>4} {'SGN':>4}")
    print("-"*92)
    for r in rows: print(r)
    print("="*60)
    print(f"matched cycles : {n}")
    if n:
        print(f"regime match   : {reg_ok}/{n} ({100*reg_ok/n:.0f}%)")
        print(f"regime (sign)  : {reg2_ok}/{n} ({100*reg2_ok/n:.0f}%)  " + "# ENH-07A-P2 rescore v1")
        print(f"net_gex sign   : {sgn_ok}/{n} ({100*sgn_ok/n:.0f}%)")
        if ratios:
            ratios.sort(); print(f"recon/live ngex: median {ratios[len(ratios)//2]:.2f}")
        print(f"live mix       : {dict(lmix)}")
        print("VERDICT:", "PASS >=85% regime" if reg_ok/n>=0.85 else "REVIEW <85%")
    print("="*60)
    return 0


if __name__ == "__main__":
    sys.exit(main())