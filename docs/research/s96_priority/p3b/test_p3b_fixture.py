"""P3b fixture test (S96-H): the SQL sweep against P3a on the six golden days, plus mutants and states.

Local Postgres 16 only (database p3b, loaded by fixture_load.sh). Never against live.
Expected values come from RUNNING P3a (tests/test_p3a_invariants.py) on the same files -- nothing is recalled.
Usage: ( ulimit -v 700000; python3 -I test_p3b_fixture.py <path to tests/> ) -> exit 0 = PASS
"""
import importlib.util, json, os, subprocess, sys

TESTS = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/GammaEnginePython/tests"
spec = importlib.util.spec_from_file_location("p3a", os.path.join(TESTS, "test_p3a_invariants.py"))
p3a = importlib.util.module_from_spec(spec); spec.loader.exec_module(p3a)


def sql(q):
    r = subprocess.run(["su", "postgres", "-c", "psql -X -q -t -A -F '|' -v ON_ERROR_STOP=1 -d p3b"],
                       input=q, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return [l.split("|") for l in r.stdout.strip().splitlines() if l]


def sweep_day(sym, day):
    return f"SELECT p3b_sweep('{day} 11:00+00', interval '8 hours', interval '3 minutes');"


DAYS = sorted(d for d in os.listdir(p3a.ROOT) if os.path.isdir(os.path.join(p3a.ROOT, d, "inputs")))
fails = []

# ---- T1: agreement with P3a, per day and per check -------------------------------------------------
sql("TRUNCATE p3b_invariant_checks;")
for d in DAYS:
    day, sym = d.split("_")
    n = int(sql(sweep_day(sym, day))[0][0])
    data = p3a.load(d)
    runs = {r["run_id"] for r in data["gex_strike"]}
    data["ocs"] = [r for r in data["ocs"] if r["run_id"] in runs]   # P3b checks gex runs only (I6 in P3a also sees chain-only runs)
    pf, info = p3a.check_day(data)
    pfc = {c: sum(1 for x in pf if x.startswith(c + " ")) for c in ("I1", "I2", "I3", "I4")}
    rows = sql(f"""SELECT check_id, sum(n_checked), coalesce(sum(n_fail),0),
                     count(*) FILTER (WHERE status='OK'), count(*) FILTER (WHERE status='FAIL'), count(*) FILTER (WHERE status='NOT_COMPUTED'),
                     count(*) FILTER (WHERE (detail->>'ascending_ok')::bool), count(*) FILTER (WHERE (detail->>'descending_ok')::bool),
                     count(DISTINCT run_id)
                   FROM p3b_invariant_checks WHERE kind='check' AND symbol='{sym}'
                     AND (ts AT TIME ZONE 'Asia/Kolkata')::date = '{day}' GROUP BY check_id ORDER BY check_id""")
    got = {r[0]: r[1:] for r in rows}
    exp = {
        "I1": (info["I1_checked"], pfc["I1"]), "I2": (info["I2_checked"], pfc["I2"]),
        "I3": (info["I3_checked"], pfc["I3"]), "I4": (info["I4_checked"], pfc["I4"]),
        "I5": (info["I5_flips"], None), "I6": (info["I6_checked"], info["I6_outside_spreads"]),
    }
    # the sweep is not per symbol (it takes every run in its window), so compare runs WITH rows for this symbol-day
    nr = int(got["I1"][7]) if "I1" in got else 0
    line = [f"{d}: runs with check rows {nr} (P3a runs {info['runs_gex']}; this sweep call took {n})"]
    if nr != info["runs_gex"]:
        fails.append(f"T1 {d}: {nr} runs checked, P3a has {info['runs_gex']}")
    for c, (e_n, e_f) in exp.items():
        g = got.get(c)
        g_n, g_f = (int(g[0]), int(g[1])) if g else (0, 0)
        ok = g_n == e_n and (e_f is None or g_f == e_f)
        line.append(f"{c} n {g_n}/{e_n} fail {g_f}/{e_f}{'' if ok else '  <-- MISMATCH'}")
        if not ok:
            fails.append(f"T1 {d} {c}: SQL n={g_n} fail={g_f} vs P3a n={e_n} fail={e_f}")
    g5 = got.get("I5")
    a, ds = (int(g5[5]), int(g5[6])) if g5 else (0, 0)
    ok5 = a == info["I5_ascending_ok"] and ds == info["I5_descending_ok"]
    line.append(f"I5 asc {a}/{info['I5_ascending_ok']} desc {ds}/{info['I5_descending_ok']}{'' if ok5 else '  <-- MISMATCH'}")
    if not ok5:
        fails.append(f"T1 {d} I5 asc/desc {a}/{ds} vs {info['I5_ascending_ok']}/{info['I5_descending_ok']}")
    print("  ".join(line[:1]) + "\n    " + "\n    ".join(line[1:]))

# ---- T2: P3a's four mutants, each on every day with gex rows, inside a rolled-back transaction --------
MUT = {
    "gex +0.05": ("UPDATE gex_strike_snapshots g SET gex_cr = gex_cr + 0.05 FROM tgt WHERE g.ctid = tgt.rid", ("I1", "I2")),
    "oi_call +1": ("UPDATE gex_strike_snapshots g SET oi_call = oi_call + 1 FROM tgt WHERE g.ctid = tgt.rid", ("I3",)),
    "concentration +0.01": ("UPDATE gamma_metrics m SET gamma_concentration = gamma_concentration + 0.01 FROM tgt "
                            "WHERE m.symbol = tgt.symbol AND m.expiry_date = tgt.expiry_date AND m.run_id = tgt.run_id "
                            "AND m.gamma_concentration IS NOT NULL", ("I4",)),
    "PE sign lost": ("UPDATE option_chain_snapshots o SET option_type = 'CE_FLIP' WHERE o.ctid = (SELECT o2.ctid FROM option_chain_snapshots o2, tgtpe t "
                     "WHERE o2.symbol = t.symbol AND o2.expiry_date = t.expiry_date AND o2.run_id = t.run_id AND o2.strike = t.strike "
                     "AND upper(o2.option_type) = 'PE' AND coalesce(o2.gamma,0) <> 0 LIMIT 1)", ("I2",)),
}
for d in DAYS:
    day, sym = d.split("_")
    dayf = f"symbol = '{sym}' AND (ts AT TIME ZONE 'Asia/Kolkata')::date = '{day}'"
    for name, (upd, must) in MUT.items():
        q = f"""BEGIN;
TRUNCATE p3b_invariant_checks;
CREATE TEMP TABLE tgt AS SELECT ctid AS rid, symbol, expiry_date, run_id, strike FROM gex_strike_snapshots WHERE {dayf} ORDER BY abs(gex_cr) DESC LIMIT 1;
CREATE TEMP TABLE tgtpe AS SELECT g.symbol, g.expiry_date, g.run_id, g.strike FROM gex_strike_snapshots g
  WHERE g.{dayf.replace('symbol', 'symbol', 1)} AND EXISTS (SELECT 1 FROM option_chain_snapshots o WHERE o.symbol = g.symbol AND o.expiry_date = g.expiry_date
  AND o.run_id = g.run_id AND o.strike = g.strike AND upper(o.option_type) = 'PE' AND coalesce(o.gamma,0) <> 0 AND coalesce(o.oi,0) > 0)
  ORDER BY abs(g.gex_cr) DESC LIMIT 1;
WITH u AS ({upd} RETURNING 1) SELECT 'changed', count(*) FROM u;
SELECT 'swept', {sweep_day(sym, day)[7:-1]};
SELECT 'fail', string_agg(DISTINCT c.check_id, ',') FROM p3b_invariant_checks c JOIN (SELECT run_id, expiry_date FROM tgt UNION SELECT run_id, expiry_date FROM tgtpe) t
  USING (run_id, expiry_date) WHERE c.status = 'FAIL';
SELECT 'fail_elsewhere', count(*) FROM p3b_invariant_checks c WHERE c.status = 'FAIL'
  AND (c.run_id, c.expiry_date) NOT IN (SELECT run_id, expiry_date FROM tgt UNION SELECT run_id, expiry_date FROM tgtpe);
ROLLBACK;"""
        out = {r[0]: r[1] for r in sql(q)}
        changed, caught = int(out["changed"]), set(filter(None, (out.get("fail") or "").split(",")))
        elsewhere = int(out["fail_elsewhere"])
        if changed == 0:
            status = "NOT APPLIED"; fails.append(f"T2 {d} {name}: mutant changed nothing")
        elif not caught & set(must):
            status = "NOT CAUGHT"; fails.append(f"T2 {d} {name}: no FAIL on {must}")
        elif elsewhere:
            status = f"CAUGHT but {elsewhere} FAIL rows on other runs"; fails.append(f"T2 {d} {name}: {elsewhere} stray FAIL rows")
        else:
            status = f"caught ({','.join(sorted(caught))})"
        print(f"  T2 {d} {name:22s} changed {changed}  {status}")

# ---- T3: states -------------------------------------------------------------------------------------
day, sym = "2026-10-01", "SENSEX"
# (a) no gamma_metrics row -> I1/I4 NOT_COMPUTED; I2/I3 still checked
out = sql(f"""BEGIN; TRUNCATE p3b_invariant_checks;
CREATE TEMP TABLE r1 AS SELECT symbol, expiry_date, run_id FROM gamma_metrics WHERE symbol='{sym}' AND (ts AT TIME ZONE 'Asia/Kolkata')::date='{day}' ORDER BY ts LIMIT 1;
DELETE FROM gamma_metrics m USING r1 WHERE m.symbol=r1.symbol AND m.expiry_date=r1.expiry_date AND m.run_id=r1.run_id;
SELECT p3b_sweep('{day} 11:00+00', interval '8 hours', interval '3 minutes');
SELECT string_agg(check_id||'='||status, ',' ORDER BY check_id) FROM p3b_invariant_checks c JOIN r1 USING (symbol, expiry_date, run_id);
SELECT count(*) FILTER (WHERE bid > 0 AND ask > 0) FROM option_chain_snapshots o JOIN r1 USING (symbol, expiry_date, run_id);
ROLLBACK;""")
st = out[1][0]
# I6's expected state is computed from the run's own quotes, not assumed: this run is the 09:00 pre-open (no bid/ask)
i6 = "INFO" if int(out[2][0]) > 0 else "NOT_COMPUTED"
exp_a = f"I1=NOT_COMPUTED,I2=OK,I3=OK,I4=NOT_COMPUTED,I5=NOT_COMPUTED,I6={i6}"
print(f"  T3a no gm row: {st}")
if st != exp_a: fails.append(f"T3a: {st} != {exp_a}")
# (b) min age: p_now 1 minute after the last run -> that run is not a candidate
out = sql(f"""BEGIN; TRUNCATE p3b_invariant_checks;
SELECT count(DISTINCT run_id) FROM gex_strike_snapshots WHERE symbol='{sym}' AND (ts AT TIME ZONE 'Asia/Kolkata')::date='{day}';
SELECT p3b_sweep((SELECT max(ts) FROM gex_strike_snapshots WHERE symbol='{sym}' AND (ts AT TIME ZONE 'Asia/Kolkata')::date='{day}') + interval '1 minute',
                 interval '8 hours', interval '3 minutes');
ROLLBACK;""")
tot, swept = int(out[0][0]), int(out[1][0])
print(f"  T3b min age: runs {tot}, swept {swept} (expect runs - 1)")
if swept != tot - 1: fails.append(f"T3b: swept {swept}, expected {tot - 1}")
# (c) idempotent: second sweep finds 0 runs, adds exactly one sweep row
out = sql(f"""BEGIN; TRUNCATE p3b_invariant_checks;
SELECT p3b_sweep('{day} 11:00+00', interval '8 hours', interval '3 minutes');
SELECT count(*) FROM p3b_invariant_checks;
SELECT p3b_sweep('{day} 11:00+00', interval '8 hours', interval '3 minutes');
SELECT count(*) FROM p3b_invariant_checks;
ROLLBACK;""")
r1n, c1, r2n, c2 = (int(x[0]) for x in out)
print(f"  T3c idempotent: first {r1n} runs/{c1} rows, second {r2n} runs/{c2} rows")
if not (r1n > 0 and r2n == 0 and c2 == c1 + 1): fails.append(f"T3c: {out}")
# (d) empty window -> SWEEP_OK with n_checked 0
out = sql("""BEGIN; TRUNCATE p3b_invariant_checks;
SELECT p3b_sweep('2026-10-03 11:00+00', interval '8 hours', interval '3 minutes');
SELECT kind||'/'||status||'/'||n_checked FROM p3b_invariant_checks; ROLLBACK;""")
print(f"  T3d empty window: returned {out[0][0]}, rows {[x[0] for x in out[1:]]}")
if not (out[0][0] == "0" and [x[0] for x in out[1:]] == ["sweep/SWEEP_OK/0"]): fails.append(f"T3d: {out}")
# (e) error path -> SWEEP_ERROR row, no check rows, returns -1
out = sql(f"""BEGIN; TRUNCATE p3b_invariant_checks;
ALTER TABLE gamma_metrics RENAME TO gamma_metrics_x;
SELECT p3b_sweep('{day} 11:00+00', interval '8 hours', interval '3 minutes');
SELECT kind||'/'||status FROM p3b_invariant_checks; ROLLBACK;""")
print(f"  T3e error path: returned {out[0][0]}, rows {[x[0] for x in out[1:]]}")
if not (out[0][0] == "-1" and [x[0] for x in out[1:]] == ["sweep/SWEEP_ERROR"]): fails.append(f"T3e: {out}")

print("P3B FIXTURE PASS" if not fails else "P3B FIXTURE FAIL\n  " + "\n  ".join(fails))
sys.exit(0 if not fails else 1)
