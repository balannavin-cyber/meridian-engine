import backfill_hist_greeks as b

iid = b.iid_for("NIFTY"); d = "2025-11-25"
live = b.get("gamma_metrics", {"select": "ts,net_gex,regime", "symbol": "eq.NIFTY",
       "and": f"(ts.gte.{d}T00:00:00,ts.lte.{d}T23:59:59)", "order": "ts.asc"})
medh = sorted(b.parse_ts(r["ts"]).hour for r in live)[len(live)//2]; is_utc = medh < 9
scache = b.spot_map_for_date(iid, d)
tl = sorted((b.parse_ts(k).hour*60 + b.parse_ts(k).minute, k) for k in scache.keys())

print(f"{'ist':>6} {'live_ng':>10} {'recon_ng':>10} {'ratio':>6} {'live_reg':>11} {'sgn':>4}")
print("-"*56)
for lr in live:
    dt = b.parse_ts(lr["ts"]); tmin = dt.hour*60+dt.minute + (330 if is_utc else 0)
    cand = min(tl, key=lambda x: abs(x[0]-tmin))
    if abs(cand[0]-tmin) > 3: continue
    _, sm, spot = b.solve_bar(iid, cand[1], d, spot_cache=scache)
    if sm is None: continue
    rng = sum(sm.values()); lng = float(lr["net_gex"])
    ist = f"{cand[0]//60:02d}:{cand[0]%60:02d}"
    ratio = rng/lng if lng else 0
    sgn = "." if (lng>=0)==(rng>=0) else "XX"
    print(f"{ist:>6} {lng:>10.0f} {rng:>10.0f} {ratio:>6.2f} {str(lr['regime']):>11} {sgn:>4}")