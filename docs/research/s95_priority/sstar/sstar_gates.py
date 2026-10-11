"""S95 / S94-H -- S*, the re-priced zero-delta level: gate harness (pre-registered).

Independent implementation, written from the P6 design note section 5.2 formula, NOT translated from
the view SQL. It reads only CSV exports produced by `--emit-sql` + bin/roq.sh (merdian_ro, read-only).
No database connection, no network.

  python3 -I sstar_gates.py --emit-sql OUTDIR        write the export SQL files (arms from arms.csv)
  python3 -I sstar_gates.py --score DATADIR          score every gate + every mutant; exit 0 = APPLY
  python3 -I sstar_gates.py --selftest               synthetic checks of the formula pieces

Gates are defined in the pre-registration (sstar_prereg_2026-10-11.md); this file implements them and nothing else.
"""
import csv, math, os, sys, statistics
from collections import defaultdict
from datetime import datetime, date, time, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
IST = timezone(timedelta(hours=5, minutes=30))
YR = 365.0 * 86400.0
TOL_SIGMA = 0.25            # G4/G5: inherited from L3 Gate 5, not loosened
G1_REL_LEVEL = 1e-6         # G1: |dS*| <= 1e-6 * spot
G1_REL_NET = 1e-6           # G1: |d net_at_spot| <= 1e-6 * gross_at_spot (+ 1e-9 Cr)


# ---------------------------------------------------------------- parsing
def pts(s):
    """psql CSV timestamptz -> aware datetime. Accepts +00, +00:00, +05:30, fraction widths 0-6."""
    s = s.strip().replace(" ", "T", 1)
    for sign in "+-":
        k = s.rfind(sign)
        if k > 10:
            off = s[k + 1:]
            if ":" not in off:
                off = off[:2] + ":" + (off[2:] or "00")
            s = s[:k] + sign + off
            break
    if "." in s:
        head, rest = s.split(".", 1)
        k = max(rest.find("+"), rest.find("-"))
        frac, off = (rest[:k], rest[k:]) if k >= 0 else (rest, "")
        s = head + "." + (frac + "000000")[:6] + off
    return datetime.fromisoformat(s)


def fnum(x):
    return None if x in (None, "", "NULL") else float(x)


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def pcont(vals, p):
    """percentile_cont: linear interpolation at p*(n-1)."""
    v = sorted(vals)
    if not v:
        return None
    x = p * (len(v) - 1)
    lo = math.floor(x)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (x - lo)


def at1530(d):
    return datetime.combine(d, time(15, 30), tzinfo=IST)


# ---------------------------------------------------------------- the model
def arm_inputs(chain, fut, cal, ts):
    """Everything the view derives from the snapshot at ts. chain: rows at that ts (all expiries)."""
    front = min(date.fromisoformat(r["expiry_date"]) for r in chain)
    rows = [r for r in chain if date.fromisoformat(r["expiry_date"]) == front]
    spot = max(float(r["spot"]) for r in rows)
    ts_date = ts.astimezone(IST).date()
    dte = (front - ts_date).days
    t_b = (at1530(front) - ts).total_seconds() / YR
    legs, n_oi, n_noiv, oi_noiv, oi_tot = [], 0, 0, 0.0, 0.0
    for r in rows:
        oi, iv, g, k = fnum(r["oi"]) or 0.0, fnum(r["iv"]), fnum(r["gamma"]), float(r["strike"])
        if oi > 0:
            n_oi += 1; oi_tot += oi
            if not (iv is not None and iv > 0):
                n_noiv += 1; oi_noiv += oi
        if oi > 0 and g is not None and g != 0 and iv is not None and iv > 0 \
                and not (abs(k - spot) / spot > 0.05 and abs(g) > 5e-5):
            legs.append((k, r["option_type"].upper(), iv / 100.0, oi))
    # r: session-median futures carry, 09:20 IST -> ts inclusive, front-month FUTURE, no look-ahead
    lo = datetime.combine(ts_date, time(9, 20), tzinfo=IST)
    win = [r for r in fut if lo <= pts(r["ts"]) <= ts
           and (fnum(r["futures_price"]) or 0) > 0 and (fnum(r["spot_price"]) or 0) > 0]
    fexp = [date.fromisoformat(r["expiry_date"]) for r in win if date.fromisoformat(r["expiry_date"]) >= ts_date]
    rr = []
    if fexp:
        fe = min(fexp)
        for r in win:
            if date.fromisoformat(r["expiry_date"]) != fe:
                continue
            ft = pts(r["ts"])
            if ft >= at1530(fe):
                continue
            tf = (at1530(fe) - ft).total_seconds() / YR
            rr.append(math.log(float(r["futures_price"]) / float(r["spot_price"])) / tf)
    r_sess = pcont(rr, 0.5); r10 = pcont(rr, 0.1); r90 = pcont(rr, 0.9)
    # house ATM grid, round half away from zero (Postgres numeric round)
    step = 50 if rows[0]["symbol"] == "NIFTY" else 100
    atm = math.floor(spot / step + 0.5) * step
    ce = [fnum(r["iv"]) for r in rows if float(r["strike"]) == atm and r["option_type"].upper() == "CE"]
    pe = [fnum(r["iv"]) for r in rows if float(r["strike"]) == atm and r["option_type"].upper() == "PE"]
    cev = max([v for v in ce if v is not None], default=None)
    pev = max([v for v in pe if v is not None], default=None)
    atm_iv = (cev + pev) / 2.0 if (cev and pev and cev > 0 and pev > 0) else None
    sig1d = spot * atm_iv / 100.0 * math.sqrt(1.0 / 365.0) if atm_iv else None
    # T conventions (L3, S83 H4/I8/J5): (a) dte/365, (b) exact secs/365d, (c) sessions/252
    sess = None
    if cal is not None:
        days = [ts_date + timedelta(days=i) for i in range(1, dte + 1)]
        if all(d.isoformat() in cal for d in days):
            sess = sum(1 for d in days if cal[d.isoformat()])
    T = {"a": dte / 365.0, "b": t_b, "c": (sess / 252.0 if sess is not None else None)}
    return dict(front=front, spot=spot, dte=dte, T=T, legs=legs, n_r=len(rr), r_sess=r_sess, r10=r10, r90=r90,
                atm_iv=atm_iv, sig1d=sig1d, n_oi=n_oi, n_noiv=n_noiv, oi_noiv=oi_noiv, oi_tot=oi_tot)


def curve(legs, spot, r, T, mutant=None):
    out = []
    for i in range(201):
        s = spot * (1.0 + (i - 100) * 0.001)
        net = gross = 0.0
        for k, typ, sig, oi in legs:
            d1 = (math.log(s / k) + (r + 0.5 * sig * sig) * T) / (sig * math.sqrt(T))
            if mutant == "M5_d1_negated":
                d1 = -d1                       # delta now DECREASES in S: G3 must catch it by construction
            dl = phi(d1) - (1.0 if typ == "PE" else 0.0)
            if mutant == "M1_pe_flip" and typ == "PE":
                dl = -dl                       # L3's CASE WHEN 'PE' THEN -1.0 copied
            x = dl * oi * (s * s if mutant == "M2_two_powers" else s) / 1e7
            net += x; gross += abs(x)
        out.append((i, s, net, gross))
    return out


def crossings(cv):
    xs = []
    for (i0, s0, g0, _), (i1, s1, g1, _) in zip(cv, cv[1:]):
        if (g0 < 0) != (g1 < 0) and g1 != g0:
            xs.append((s0 + (s1 - s0) * (0.0 - g0) / (g1 - g0), "neg->pos" if g0 < 0 else "pos->neg"))
    return xs


def level(inp, r, T, mutant=None):
    cv = curve(inp["legs"], inp["spot"], r, T, mutant)
    xs = crossings(cv)
    near = min(xs, key=lambda x: abs(x[0] - inp["spot"])) if xs else None
    return cv, xs, near


def view_row(inp, mutant=None):
    """What the view should publish for this arm (status precedence = ENH-131)."""
    refuse_dte0 = mutant != "M4_dte0_floored"
    if (inp["dte"] == 0 and refuse_dte0):
        return dict(status="SKIPPED_EXPIRY")
    if inp["n_r"] < 6 or inp["r_sess"] is None:
        return dict(status="UNMEASURABLE_R")
    T = inp["T"]["b"]
    if T <= 0:
        return dict(status="SKIPPED_EXPIRY")
    r = inp["r_sess"] * (100.0 if mutant == "M3_r_percent" else 1.0)
    cv, xs, near = level(inp, r, T, mutant)
    return dict(status="OK" if near else "NO_CROSSING", zero=near[0] if near else None,
                direction=near[1] if near else None, n_cross=len(xs),
                net=cv[100][2], gross=cv[100][3], n_used=len(inp["legs"]))


# ---------------------------------------------------------------- gates
def score(datadir, mutant=None, verbose=True):
    arms = read(os.path.join(datadir, "arms_resolved.csv"))
    chain = defaultdict(list)
    for r in read(os.path.join(datadir, "chain.csv")):
        chain[r["arm"]].append(r)
    fut = defaultdict(list)
    for r in read(os.path.join(datadir, "futures.csv")):
        fut[r["arm"]].append(r)
    cal = {r["trade_date"]: r["is_open"] in ("t", "true", "True", "1") for r in read(os.path.join(datadir, "calendar.csv"))}
    sql = {}
    for fn in sorted(os.listdir(datadir)):
        if fn.startswith("view_asof_") and fn.endswith(".csv"):
            for r in read(os.path.join(datadir, fn)):
                sql[r["arm"]] = r
    res = dict(G1=[], G3=[], G4=[], G5=[], G2=[], unscorable=[], scorable=0)
    for a in arms:
        name, role = a["arm"], a["role"]
        if not a["ts"]:
            res["unscorable"].append(f"{name}: no chain snapshot in window"); continue
        ts = pts(a["ts"])
        inp = arm_inputs(chain[name], fut[name], cal, ts)
        vr = view_row(inp, mutant)
        q = sql.get(name)
        # ---- G1: independent recompute == the view body (as-of), every arm incl. the control
        if q is None:
            res["G1"].append(f"{name}: no view row")
        else:
            if q["status"] != vr["status"]:
                res["G1"].append(f"{name}: status view {q['status']} != recompute {vr['status']}")
            elif vr["status"] in ("OK", "NO_CROSSING"):
                if int(q["n_legs_used"]) != vr["n_used"]:
                    res["G1"].append(f"{name}: n_legs_used {q['n_legs_used']} != {vr['n_used']}")
                if int(q["n_dropped_no_iv"]) != inp["n_noiv"] or abs(float(q["oi_dropped_no_iv"]) - inp["oi_noiv"]) > 0.5:
                    res["G1"].append(f"{name}: dropped no-iv {q['n_dropped_no_iv']}/{q['oi_dropped_no_iv']} != {inp['n_noiv']}/{inp['oi_noiv']}")
                if int(q["n_cross_full_grid"]) != vr["n_cross"]:
                    res["G1"].append(f"{name}: n_cross {q['n_cross_full_grid']} != {vr['n_cross']}")
                tol_net = G1_REL_NET * max(vr["gross"], 1.0) + 1e-9
                if abs(float(q["net_dex_at_spot_cr"]) - vr["net"]) > tol_net:
                    res["G1"].append(f"{name}: net_at_spot {float(q['net_dex_at_spot_cr']):.6f} != {vr['net']:.6f}")
                if vr["status"] == "OK":
                    if abs(float(q["zero_delta"]) - vr["zero"]) > G1_REL_LEVEL * inp["spot"]:
                        res["G1"].append(f"{name}: S* {float(q['zero_delta']):.4f} != {vr['zero']:.4f}")
        if role == "control":
            if vr["status"] != "SKIPPED_EXPIRY":
                res["G1"].append(f"{name}: dte-0 control not refused ({vr['status']})")
            continue
        if vr["status"] not in ("OK", "NO_CROSSING") or inp["T"]["c"] is None:
            res["unscorable"].append(f"{name}: status {vr['status']}, T(c) {inp['T']['c']}")
            continue
        rmul = 100.0 if mutant == "M3_r_percent" else 1.0
        # ---- G3: structure, on every (r, T) variant: sum(delta*oi) strictly increasing; <=1 crossing, neg->pos
        variants = [(rn, rv * rmul, tn, tv) for rn, rv in (("p10", inp["r10"]), ("sess", inp["r_sess"]), ("p90", inp["r90"]))
                    for tn, tv in (("a", inp["T"]["a"]), ("b", inp["T"]["b"]), ("c", inp["T"]["c"]))]
        lv = {}
        for rn, rv, tn, tv in variants:
            cv, xs, near = level(inp, rv, tv, mutant)
            D = [c[2] * 1e7 / c[1] for c in cv]
            if any(D[j + 1] <= D[j] for j in range(len(D) - 1)):
                res["G3"].append(f"{name} r={rn} T={tn}: sum(delta*oi) not strictly increasing")
            if len(xs) > 1 or any(d != "neg->pos" for _, d in xs):
                res["G3"].append(f"{name} r={rn} T={tn}: crossings {[(round(x, 1), d) for x, d in xs]}")
            lv[(rn, tn)] = near[0] if near else None
        # G3 is structural and needs no level: it ran above on OK and NO_CROSSING arms alike.
        if vr["status"] != "OK" or inp["sig1d"] is None:
            res["unscorable"].append(f"{name}: G4/G5 need a level and sigma_1d -- status {vr['status']}, sigma_1d {inp['sig1d']}")
            continue
        res["scorable"] += 1
        tol = TOL_SIGMA * inp["sig1d"]
        # ---- G4: r band at T(b)
        g4 = [lv[(rn, "b")] for rn in ("p10", "sess", "p90")]
        if None in g4 or max(g4) - min(g4) > tol:
            res["G4"].append(f"{name}: S* over r band {['NONE' if v is None else round(v, 2) for v in g4]} spread vs tol {tol:.2f}")
        # ---- G5: L3 Gate 5 -- the full r band x three T conventions
        g5 = list(lv.values())
        if None in g5 or max(g5) - min(g5) > tol:
            sp = None if None in g5 else max(g5) - min(g5)
            res["G5"].append(f"{name}: 3x3 sweep spread {sp if sp is None else round(sp, 2)} vs tol {tol:.2f}")
        # ---- G2: descriptive only (never gates) -- repriced vs vendor-delta book at the observed spot
        vend = sum((fnum(r["delta"]) or 0.0) * (fnum(r["oi"]) or 0.0) * inp["spot"] / 1e7
                   for r in chain[name] if r["expiry_date"] == inp["front"].isoformat() and (fnum(r["oi"]) or 0) > 0)
        res["G2"].append(f"{name}: repriced net {vr['net']:,.1f} Cr (gross {vr['gross']:,.1f}) vs vendor-delta net {vend:,.1f}; "
                         f"S* {vr['zero']:,.1f} = spot {vr['zero'] - inp['spot']:+,.1f} ({(vr['zero'] - inp['spot']) / inp['sig1d']:+.2f} sigma); "
                         f"dropped no-iv {inp['n_noiv']} legs / {inp['oi_noiv']:,.0f} OI of {inp['oi_tot']:,.0f}")
    if verbose:
        print(f"== scorable arms: {res['scorable']}   unscorable: {len(res['unscorable'])}")
        for u in res["unscorable"]:
            print("   unscorable:", u)
        for g in ("G1", "G3", "G4", "G5"):
            print(f"== {g}: {'PASS' if not res[g] else f'FAIL ({len(res[g])})'}")
            for f in res[g][:12]:
                print("   ", f)
        print("== G2 (descriptive, never gates):")
        for x in res["G2"]:
            print("   ", x)
    return res


MUTANTS = {  # each must make its named gate FAIL on >= 1 arm
    "M1_pe_flip": ("G1",),           # G3 CANNOT catch it on a call-heavy book (measured S95 local test)
    "M5_d1_negated": ("G3",),
    "M2_two_powers": ("G1",),
    "M3_r_percent": ("G1", "G4"),
    "M4_dte0_floored": ("G1",),
}


def emit_sql(outdir):
    """Write the read-only export SQL (run each through bin/roq.sh). Arms come from arms.csv only."""
    os.makedirs(outdir, exist_ok=True)
    arms = read(os.environ.get("SSTAR_ARMS") or os.path.join(HERE, "arms.csv"))
    vals = ",\n  ".join(f"('{a['arm']}', '{a['symbol']}', timestamp '{a['label_ist']}', '{a['role']}')" for a in arms)
    resolved = f"""WITH arms(arm, symbol, label, role) AS (VALUES
  {vals}
), res AS (
  -- arm ts = the FIRST chain snapshot in [label, label + 5 min) IST: the cycle the label names
  SELECT a.arm, a.symbol, a.role, a.label, t.ts
    FROM arms a
    LEFT JOIN LATERAL (
      SELECT o.ts FROM option_chain_snapshots o
       WHERE o.symbol = a.symbol
         AND o.ts >= (a.label AT TIME ZONE 'Asia/Kolkata')
         AND o.ts <  ((a.label + interval '5 minutes') AT TIME ZONE 'Asia/Kolkata')
       ORDER BY o.ts ASC LIMIT 1) t ON true
)"""
    q = {
        "01_arms_resolved.sql": resolved + "\nSELECT arm, symbol, role, ts FROM res ORDER BY label, symbol;\n",
        "02_chain.sql": resolved + """
SELECT r.arm, o.symbol, o.ts, o.expiry_date, o.strike, o.option_type, o.iv, o.oi, o.gamma, o.delta, o.spot
  FROM res r JOIN option_chain_snapshots o ON o.symbol = r.symbol AND o.ts = r.ts
 ORDER BY r.arm, o.expiry_date, o.strike, o.option_type;
""",
        "03_futures.sql": resolved + """
SELECT r.arm, i.ts, i.expiry_date, i.futures_price, i.spot_price
  FROM res r JOIN index_futures_snapshots i
    ON i.symbol = r.symbol
   AND i.ts >= (((r.ts AT TIME ZONE 'Asia/Kolkata')::date + time '09:20') AT TIME ZONE 'Asia/Kolkata')
   AND i.ts <= r.ts
 ORDER BY r.arm, i.ts;
""",
        "04_calendar.sql": f"""SELECT trade_date, is_open FROM trading_calendar
 WHERE trade_date BETWEEN date '{min(a['label_ist'][:10] for a in arms)}'
                      AND date '{max(a['label_ist'][:10] for a in arms)}' + 40
 ORDER BY trade_date;
""",
    }
    body = open(os.path.join(HERE, "sstar_view_body.sql")).read()
    sel = body[body.index("WITH RECURSIVE"):].rstrip().rstrip(";")
    assert sel.count("-- @ASOF@") == 1
    # the as-of form of the body: ONE added predicate in `latest` (the ENH-134 / S88 pattern), nothing else
    for n, a in enumerate(arms, 1):
        q[f"10_view_asof_{n:02d}.sql"] = "-- arm: " + a["arm"] + "\n" + \
            f"WITH res AS (SELECT o.ts FROM option_chain_snapshots o WHERE o.symbol = '{a['symbol']}' " \
            f"AND o.ts >= (timestamp '{a['label_ist']}' AT TIME ZONE 'Asia/Kolkata') " \
            f"AND o.ts < ((timestamp '{a['label_ist']}' + interval '5 minutes') AT TIME ZONE 'Asia/Kolkata') " \
            f"ORDER BY o.ts ASC LIMIT 1)\n" \
            f"SELECT '{a['arm']}' AS arm, v.* FROM (\n" + \
            sel.replace("-- @ASOF@ (gate harness only; inert comment in the view)",
                        "AND o.ts <= (SELECT ts FROM res)") + \
            f"\n) v WHERE v.symbol = '{a['symbol']}';\n"
    for fn, text in q.items():
        with open(os.path.join(outdir, fn), "w") as f:
            f.write("\\pset format csv\n" + text)
    print(f"wrote {len(q)} SQL files to {outdir}")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--emit-sql":
        emit_sql(sys.argv[2]); return 0
    if len(sys.argv) >= 3 and sys.argv[1] == "--score":
        res = score(sys.argv[2])
        ok = all(not res[g] for g in ("G1", "G3", "G4", "G5")) and res["scorable"] >= 6
        print("== mutants:")
        caught_all = True
        for m, gates in MUTANTS.items():
            r = score(sys.argv[2], mutant=m, verbose=False)
            for g in gates:
                c = bool(r[g])
                caught_all &= c
                print(f"   {m:<18} {g}: {'caught' if c else 'NOT CAUGHT'}")
        if res["scorable"] < 6:
            print(f"== INSUFFICIENT: {res['scorable']} scorable arms < 6")
        verdict = "APPLY" if ok and caught_all else "DO NOT APPLY"
        print(f"S* GATES {'PASS' if ok else 'FAIL'}   mutants {'all caught' if caught_all else 'NOT all caught'}   -> {verdict}")
        return 0 if verdict == "APPLY" else 1
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        assert abs(phi(0) - 0.5) < 1e-15 and abs(phi(1) - 0.841344746068543) < 1e-15
        assert abs(phi(-3) - 0.0013498980316301) < 1e-15
        assert pcont([1, 2, 3, 4], 0.5) == 2.5 and abs(pcont([1, 2, 3, 4], 0.1) - 1.3) < 1e-12
        assert pts("2026-10-09 06:25:12.5+00").tzinfo is not None
        print("SELFTEST PASS"); return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())
