"""Step 9: the pull. One read-only pass over the stored history.

Design: PREREG.md as amended by PREREG_A1.md, both in this folder.
Every figure is computed by step9_lib.figures_from_agg; this file's only job is
to produce the aggregate record per run, in SQL, and to run the stops.

Query discipline (task condition 4), enforced here and not merely described:
  - one symbol-day per query, split in two by clock time if the day would
    return more than 100 rows;
  - aggregation inside the query, at most 100 rows back per statement;
  - 5 s sleep between queries;
  - stop the whole pull at the first error or any query over 10 s; no retries.

Usage:
    ulimit -v 700000 && python3 -B step9_pull.py
    ulimit -v 700000 && python3 -B step9_pull.py --explain    # plans only, no rows
    ulimit -v 700000 && python3 -B step9_pull.py --plan       # the symbol-day list

Ends with exactly one of:
    PULL FINISHED runs=<n>
    PULL STOPPED <reason>
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

import step9_lib as L

HERE = Path(__file__).resolve().parent
ROQ = HERE.parents[3] / "bin" / "roq.sh"
SQLDIR = HERE / "sql"
RUNLOG = HERE / "run.log"
PERRUN = HERE / "per_run.jsonl"
PLANJSON = HERE / "plan.json"
POPJSON = HERE / "population.json"
C4JSON = HERE / "c4_result.json"
EXPLAIN_OUT = HERE / "explain.txt"
FIXTURE = HERE / "b2_expected_2026-08-27.json"

SYMBOLS = ("NIFTY", "SENSEX")
DAY_FROM = dt.date(2026, 5, 25)       # PREREG §2
DAY_TO = dt.date(2026, 11, 25)        # PREREG §2, inclusive
C4_DAY = "2026-08-27"                 # PREREG §6 C4, the known day
MAX_ROWS = 100
SLEEP_S = 5.0
MAX_Q_S = 10.0
EXPLAIN_DAY = "2026-08-27"
EXPLAIN_SYM = "NIFTY"
GUARDED = ("gex_strike_snapshots", "gex_strike_v2", "gex_run_v2",
           "gex_cycle_history", "gamma_metrics", "p3b2_invariant_checks")
MAX_SCAN_ROWS = 20000


class Stop(Exception):
    pass


# ------------------------------------------------- the deadline guard (cond. 1)
# IST is a fixed +05:30 offset with no DST, so this needs no tz database.
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
DEADLINE_FROM = dt.time(8, 15)
DEADLINE_TO = dt.time(15, 40)


def in_closed_window(now_ist: dt.datetime) -> bool:
    """True when no query may run: Mon-Fri and 08:15 <= t < 15:40 IST.

    Pure, so the self-test can exercise it: a Tuesday 08:16 is closed, a
    Saturday 08:16 is not, a Friday 20:00 is not.
    """
    return (now_ist.weekday() < 5
            and DEADLINE_FROM <= now_ist.time() < DEADLINE_TO)


def deadline_guard(now_ist: dt.datetime | None = None) -> None:
    """Called before EVERY query and before the pull starts. The pull stops
    itself; it is not left to an operator or a watcher to kill it."""
    if in_closed_window(now_ist or dt.datetime.now(IST)):
        raise Stop("deadline 08:15 IST")


def log(msg: str) -> None:
    line = "%s  %s" % (dt.datetime.now().isoformat(timespec="seconds"), msg)
    with RUNLOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


# ---------------------------------------------------------------- SQL templates

def _ist(day: str, clock: str) -> str:
    return "%s %s+05:30" % (day, clock)


def bounds(day: str, half: int | None):
    """The symbol-day window, or its first/second half by clock time."""
    nxt = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
    if half is None:
        return _ist(day, "00:00:00"), _ist(nxt, "00:00:00")
    if half == 0:
        return _ist(day, "00:00:00"), _ist(day, "12:00:00")
    return _ist(day, "12:00:00"), _ist(nxt, "00:00:00")


PLAN_SQL = """
SELECT row_to_json(t)::text AS j FROM (
  SELECT (ts AT TIME ZONE 'Asia/Kolkata')::date::text AS day,
         '{sym}' AS symbol, count(*) AS n_runs
  FROM public.gex_run_v2
  WHERE symbol = '{sym}'
    AND ts >= '{t0}'::timestamptz AND ts < '{t1}'::timestamptz
    AND rule_version = '{stamp}'
  GROUP BY 1 ORDER BY 1
) t;
"""

Q1_SQL = """
WITH g AS (
  SELECT run_id, strike, gex_cr, spot, dte, ts, symbol, expiry_date,
         gamma_call, gamma_put
  FROM public.gex_strike_snapshots
  WHERE symbol = '{sym}'
    AND ts >= '{t0}'::timestamptz AND ts < '{t1}'::timestamptz
), ag AS (
  SELECT run_id,
    count(*) AS v1_n,
    sum(gex_cr) AS v1_net,
    sum(abs(gex_cr)) AS v1_abs,
    sum(gex_cr * gex_cr) AS v1_sq,
    max(abs(gex_cr)) AS v1_maxabs,
    min(dte) AS v1_dte, count(DISTINCT dte) AS v1_dte_n,
    min(symbol) AS v1_symbol, count(DISTINCT symbol) AS v1_symbol_n,
    min(expiry_date)::text AS v1_expiry_date, count(DISTINCT expiry_date) AS v1_expiry_n,
    min(ts) AS v1_ts, count(DISTINCT ts) AS v1_ts_n,
    min(ts AT TIME ZONE 'Asia/Kolkata') AS v1_ts_ist,
    min(spot) AS v1_spot, count(DISTINCT spot) AS v1_spot_n,
    coalesce(sum(gex_cr) FILTER (WHERE abs(strike - spot) <= 0.05 * spot), 0) AS v1_net_in5,
    coalesce(sum(abs(gex_cr)) FILTER (WHERE abs(strike - spot) <= 0.05 * spot), 0) AS v1_abs_in5,
    count(*) FILTER (WHERE gamma_call IS NOT NULL)
      + count(*) FILTER (WHERE gamma_put IS NOT NULL) AS legs_with_gamma,
    count(*) FILTER (WHERE gamma_call > 5e-5 AND abs(strike - spot) > 0.05 * spot)
      + count(*) FILTER (WHERE gamma_put > 5e-5 AND abs(strike - spot) > 0.05 * spot) AS legs_removed,
    coalesce(sum(abs(gex_cr)) FILTER (
        WHERE abs(strike - spot) > 0.05 * spot
          AND (gamma_call > 5e-5 OR gamma_put > 5e-5)), 0) AS v1_abs_at_removed
  FROM g GROUP BY run_id
), rk AS (
  SELECT run_id, strike, gex_cr,
    row_number() OVER (PARTITION BY run_id
        ORDER BY abs(gex_cr) DESC, abs(strike - spot), strike) AS rn_abs,
    rank() OVER (PARTITION BY run_id ORDER BY abs(gex_cr) DESC) AS rk_abs,
    row_number() OVER (PARTITION BY run_id
        ORDER BY gex_cr DESC, abs(strike - spot), strike) AS rn_pos,
    rank() OVER (PARTITION BY run_id ORDER BY gex_cr DESC) AS rk_pos
  FROM g
), pk AS (
  SELECT run_id, strike AS v1_peak_strike FROM rk WHERE rn_abs = 1
), pkt AS (
  SELECT run_id, count(*) AS v1_peak_ties FROM rk WHERE rk_abs = 1 GROUP BY run_id
), ps AS (
  SELECT run_id, strike AS v1_pos_strike FROM rk WHERE rn_pos = 1 AND gex_cr > 0
), pst AS (
  SELECT run_id, count(*) AS v1_pos_ties FROM rk
  WHERE rk_pos = 1 AND gex_cr > 0 GROUP BY run_id
)
SELECT row_to_json(t)::text AS j FROM (
  SELECT ag.run_id, ag.v1_n, ag.v1_net, ag.v1_abs, ag.v1_sq, ag.v1_maxabs,
         ag.v1_dte, ag.v1_dte_n, ag.v1_symbol, ag.v1_symbol_n,
         ag.v1_expiry_date, ag.v1_expiry_n, ag.v1_ts, ag.v1_ts_n, ag.v1_ts_ist,
         ag.v1_spot, ag.v1_spot_n, ag.v1_net_in5, ag.v1_abs_in5,
         ag.legs_with_gamma, ag.legs_removed, ag.v1_abs_at_removed,
         pk.v1_peak_strike, coalesce(pkt.v1_peak_ties, 0) AS v1_peak_ties,
         ps.v1_pos_strike, coalesce(pst.v1_pos_ties, 0) AS v1_pos_ties
  FROM ag
  LEFT JOIN pk ON pk.run_id = ag.run_id
  LEFT JOIN pkt ON pkt.run_id = ag.run_id
  LEFT JOIN ps ON ps.run_id = ag.run_id
  LEFT JOIN pst ON pst.run_id = ag.run_id
) t;
"""

Q2_SQL = """
WITH r AS (
  SELECT run_id, symbol, ts, expiry_date, dte, spot, net_cr, net_top_share,
         gross_band_cr, gross_top_share, gross_hhi, n_map, n_zero, n_dup_legs,
         rule_version
  FROM public.gex_run_v2
  WHERE symbol = '{sym}'
    AND ts >= '{t0}'::timestamptz AND ts < '{t1}'::timestamptz
), v AS (
  SELECT run_id, strike, net_cr, gross_cr, spot, in_map, in_band, gamma_strike,
         gamma_legs, oi_call, oi_put, symbol, expiry_date, ts, rule_version
  FROM public.gex_strike_v2
  WHERE symbol = '{sym}'
    AND ts >= '{t0}'::timestamptz AND ts < '{t1}'::timestamptz
), va AS (
  SELECT run_id,
    count(*) AS v2_n_map,
    sum(net_cr) AS v2_strike_sum,
    sum(abs(net_cr)) AS v2_abs,
    sum(net_cr * net_cr) AS v2_sq,
    max(abs(net_cr)) AS v2_maxabs,
    coalesce(sum(net_cr) FILTER (WHERE abs(strike - spot) <= 0.05 * spot), 0) AS v2_net_in5
  FROM v WHERE in_map GROUP BY run_id
), vall AS (
  SELECT run_id,
    count(*) AS n,
    count(*) FILTER (WHERE in_map) AS n_map,
    count(*) FILTER (WHERE in_band) AS n_band,
    count(*) FILTER (WHERE gamma_legs = 'both') AS n_both,
    count(*) FILTER (WHERE gamma_legs = 'call_only') AS n_call,
    count(*) FILTER (WHERE gamma_legs = 'put_only') AS n_put,
    sum(oi_call) AS s_oic, sum(oi_put) AS s_oip,
    sum(net_cr) AS s_net, sum(gross_cr) AS s_gross,
    sum(gamma_strike) AS s_gamma,
    sum(strike * net_cr) AS sk_net, sum(strike * gross_cr) AS sk_gross,
    min(symbol) AS v2_symbol, count(DISTINCT symbol) AS v2_symbol_n,
    min(expiry_date)::text AS v2_expiry_date, count(DISTINCT expiry_date) AS v2_expiry_n,
    min(ts) AS v2_ts, count(DISTINCT ts) AS v2_ts_n,
    min(rule_version) AS rv_strike, count(DISTINCT rule_version) AS rv_strike_n
  FROM v GROUP BY run_id
), rk AS (
  SELECT run_id, strike, net_cr,
    row_number() OVER (PARTITION BY run_id
        ORDER BY abs(net_cr) DESC, abs(strike - spot), strike) AS rn_abs,
    rank() OVER (PARTITION BY run_id ORDER BY abs(net_cr) DESC) AS rk_abs,
    row_number() OVER (PARTITION BY run_id
        ORDER BY net_cr DESC, abs(strike - spot), strike) AS rn_pos,
    rank() OVER (PARTITION BY run_id ORDER BY net_cr DESC) AS rk_pos
  FROM v WHERE in_map
), pk AS (
  SELECT run_id, strike AS v2_peak_strike FROM rk WHERE rn_abs = 1
), pkt AS (
  SELECT run_id, count(*) AS v2_peak_ties FROM rk WHERE rk_abs = 1 GROUP BY run_id
), ps AS (
  SELECT run_id, strike AS v2_pos_strike FROM rk WHERE rn_pos = 1 AND net_cr > 0
), pst AS (
  SELECT run_id, count(*) AS v2_pos_ties FROM rk
  WHERE rk_pos = 1 AND net_cr > 0 GROUP BY run_id
)
SELECT row_to_json(t)::text AS j FROM (
  SELECT r.run_id, r.symbol, r.ts AS r_ts,
         (r.ts AT TIME ZONE 'Asia/Kolkata') AS r_ts_ist,
         r.expiry_date::text AS r_expiry_date, r.dte AS r_dte, r.spot,
         r.net_cr AS r_net_cr, r.net_top_share AS r_net_top_share,
         r.gross_band_cr AS r_gross_band_cr,
         r.gross_top_share AS r_gross_top_share, r.gross_hhi AS r_gross_hhi,
         r.n_map AS r_n_map, r.n_zero AS r_n_zero, r.n_dup_legs,
         r.rule_version AS rv_run,
         va.v2_n_map, va.v2_strike_sum, va.v2_abs, va.v2_sq, va.v2_maxabs,
         va.v2_net_in5,
         vall.n, vall.n_map, vall.n_band, vall.n_both, vall.n_call, vall.n_put,
         vall.s_oic, vall.s_oip, vall.s_net, vall.s_gross, vall.s_gamma,
         vall.sk_net, vall.sk_gross,
         vall.v2_symbol, vall.v2_symbol_n, vall.v2_expiry_date,
         vall.v2_expiry_n, vall.v2_ts, vall.v2_ts_n,
         vall.rv_strike, vall.rv_strike_n,
         pk.v2_peak_strike, coalesce(pkt.v2_peak_ties, 0) AS v2_peak_ties,
         ps.v2_pos_strike, coalesce(pst.v2_pos_ties, 0) AS v2_pos_ties
  FROM r
  LEFT JOIN va ON va.run_id = r.run_id
  LEFT JOIN vall ON vall.run_id = r.run_id
  LEFT JOIN pk ON pk.run_id = r.run_id
  LEFT JOIN pkt ON pkt.run_id = r.run_id
  LEFT JOIN ps ON ps.run_id = r.run_id
  LEFT JOIN pst ON pst.run_id = r.run_id
) t;
"""

Q3_SQL = """
WITH a AS (
  SELECT run_id, strike, gex_cr::double precision AS x, spot
  FROM public.gex_strike_snapshots
  WHERE symbol = '{sym}'
    AND ts >= '{t0}'::timestamptz AND ts < '{t1}'::timestamptz
), b AS (
  SELECT run_id, strike, net_cr AS y, spot
  FROM public.gex_strike_v2
  WHERE symbol = '{sym}'
    AND ts >= '{t0}'::timestamptz AND ts < '{t1}'::timestamptz
    AND in_map
), u AS (
  SELECT coalesce(a.run_id, b.run_id) AS run_id,
         coalesce(a.strike, b.strike) AS strike,
         coalesce(a.spot, b.spot) AS spot,
         a.x AS x, b.y AS y,
         coalesce(a.x, 0::double precision) AS xv,
         coalesce(b.y, 0::double precision) AS yv
  FROM a FULL OUTER JOIN b ON a.run_id = b.run_id AND a.strike = b.strike
)
SELECT row_to_json(t)::text AS j FROM (
  SELECT run_id,
    count(*) AS x_n_union,
    count(*) FILTER (WHERE x IS NOT NULL AND y IS NOT NULL) AS x_n_both,
    count(*) FILTER (WHERE y IS NULL) AS x_n_v1_only,
    count(*) FILTER (WHERE x IS NULL) AS x_n_v2_only,
    count(*) FILTER (WHERE sign(xv) <> sign(yv)) AS x_n_sign,
    count(*) FILTER (WHERE xv <> 0 AND yv <> 0 AND sign(xv) <> sign(yv)) AS x_n_sign_nz,
    count(*) FILTER (WHERE xv = 0 AND yv <> 0) AS x_n_v1z_v2nz,
    count(*) FILTER (WHERE xv <> 0 AND yv = 0) AS x_n_v1nz_v2z,
    sum(abs(yv - xv)) AS x_w_num,
    sum(abs(xv)) AS x_w_den,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot) AS x5_n_union,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot
                       AND x IS NOT NULL AND y IS NOT NULL) AS x5_n_both,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot AND y IS NULL) AS x5_n_v1_only,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot AND x IS NULL) AS x5_n_v2_only,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot
                       AND sign(xv) <> sign(yv)) AS x5_n_sign,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot
                       AND xv <> 0 AND yv <> 0 AND sign(xv) <> sign(yv)) AS x5_n_sign_nz,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot
                       AND xv = 0 AND yv <> 0) AS x5_n_v1z_v2nz,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot
                       AND xv <> 0 AND yv = 0) AS x5_n_v1nz_v2z,
    coalesce(sum(abs(yv - xv)) FILTER (
        WHERE abs(strike - spot) <= 0.05 * spot), 0) AS x5_w_num,
    coalesce(sum(abs(xv)) FILTER (
        WHERE abs(strike - spot) <= 0.05 * spot), 0) AS x5_w_den
  FROM u GROUP BY run_id
) t;
"""

Q4_SQL = """
SELECT row_to_json(t)::text AS j FROM (
  SELECT r.run_id,
         h.net_gex AS gch_net_gex,
         h.pin_leader_strike AS gch_pin_leader_strike,
         h.conc_top1_share AS gch_conc_top1_share,
         h.conc_hhi AS gch_conc_hhi,
         h.dte AS gch_dte,
         m.net_gex AS gm_net_gex,
         p.status AS v1_chain_status
  FROM public.gex_run_v2 r
  LEFT JOIN public.gex_cycle_history h
         ON h.run_id = r.run_id AND h.symbol = r.symbol
  LEFT JOIN public.gamma_metrics m
         ON m.run_id = r.run_id
  LEFT JOIN public.p3b2_invariant_checks p
         ON p.kind = 'check' AND p.check_id = 'V1'
        AND p.symbol = r.symbol AND p.expiry_date = r.expiry_date
        AND p.run_id = r.run_id
  WHERE r.symbol = '{sym}'
    AND r.ts >= '{t0}'::timestamptz AND r.ts < '{t1}'::timestamptz
) t;
"""

TEMPLATES = (("Q1_v1", Q1_SQL), ("Q2_v2", Q2_SQL), ("Q3_cross", Q3_SQL),
             ("Q4_aux", Q4_SQL))


def render(tmpl: str, sym: str, t0: str, t1: str) -> str:
    return tmpl.format(sym=sym, t0=t0, t1=t1, stamp=L.RULE_STAMP)


# ---------------------------------------------------------------- the reader

STATS = {"queries": 0, "seconds": 0.0, "slowest": 0.0, "slowest_label": ""}


def roq(sql: str, label: str, expect_rows: bool = True):
    """One statement through bin/roq.sh. Every stop of condition 4 lives here,
    and the deadline guard is read before the query is sent, not after."""
    deadline_guard()
    path = SQLDIR / ("pull_%s.sql" % label)
    path.write_text(sql, encoding="utf-8")
    t0 = time.monotonic()
    p = subprocess.run([str(ROQ), str(path)], capture_output=True, text=True)
    el = time.monotonic() - t0
    STATS["queries"] += 1
    STATS["seconds"] += el
    if el > STATS["slowest"]:
        STATS["slowest"], STATS["slowest_label"] = el, label
    if p.returncode != 0:
        raise Stop("query %s exited %d: %s" % (label, p.returncode,
                                               p.stderr.strip()[:300]))
    if p.stderr.strip():
        raise Stop("query %s wrote to stderr: %s" % (label, p.stderr.strip()[:300]))
    if el > MAX_Q_S:
        raise Stop("query %s took %.2fs, over the %.0fs limit" % (label, el, MAX_Q_S))
    rows = []
    for line in p.stdout.splitlines():
        s = line.strip()
        if s.startswith("{") and s.endswith("}"):
            rows.append(json.loads(s))
    if expect_rows and len(rows) > MAX_ROWS:
        raise Stop("query %s returned %d rows, over the %d-row limit"
                   % (label, len(rows), MAX_ROWS))
    return rows, el


def pause():
    time.sleep(SLEEP_S)


# ---------------------------------------------------------------- EXPLAIN gate

def seq_scan_offenders(plan: str):
    return [l.strip() for l in plan.splitlines()
            if "Seq Scan" in l and any(g in l for g in GUARDED)]


def big_scan_offenders(plan: str):
    out = []
    for line in plan.splitlines():
        if "rows=" not in line or "Scan" not in line:
            continue
        if not any(g in line for g in GUARDED):
            continue
        try:
            n = int(line.split("rows=")[1].split()[0].rstrip(")"))
        except (IndexError, ValueError):
            continue
        if n > MAX_SCAN_ROWS:
            out.append("%d rows: %s" % (n, line.strip()))
    return out


def explain_gate() -> int:
    """Plain EXPLAIN on every template, including the plan template. Reads no
    rows. Writes explain.txt and prints PASS or the failing node."""
    t0, t1 = bounds(EXPLAIN_DAY, None)
    m0 = "%s-01 00:00:00+05:30" % EXPLAIN_DAY[:7]
    m1 = "%s-01 00:00:00+05:30" % "2026-09"
    items = [("PLAN", render(PLAN_SQL, EXPLAIN_SYM, m0, m1))]
    items += [(name, render(t, EXPLAIN_SYM, t0, t1)) for name, t in TEMPLATES]
    text, bad = [], []
    for name, sql in items:
        deadline_guard()
        path = SQLDIR / ("explain_%s.sql" % name)
        path.write_text("EXPLAIN " + sql.strip().rstrip(";") + ";\n", encoding="utf-8")
        p = subprocess.run([str(ROQ), str(path)], capture_output=True, text=True)
        text.append("### %s  (rc=%d)" % (name, p.returncode))
        text.append(p.stdout.rstrip())
        if p.stderr.strip():
            text.append("STDERR: " + p.stderr.strip())
            bad.append("%s: stderr %s" % (name, p.stderr.strip()[:200]))
        if p.returncode != 0:
            bad.append("%s: rc=%d" % (name, p.returncode))
        for off in seq_scan_offenders(p.stdout):
            bad.append("%s: SEQ SCAN %s" % (name, off))
        for off in big_scan_offenders(p.stdout):
            bad.append("%s: SCAN ESTIMATE %s" % (name, off))
        time.sleep(SLEEP_S)
    EXPLAIN_OUT.write_text("\n".join(text) + "\n", encoding="utf-8")
    if bad:
        print("EXPLAIN GATE: FAIL")
        for b in bad[:20]:
            print("  " + b)
        return 2
    print("EXPLAIN GATE: PASS -- no Seq Scan of a guarded relation and no scan "
          "estimate over %d rows, over %d templates" % (MAX_SCAN_ROWS, len(items)))
    return 0


# ---------------------------------------------------------------- the plan

def month_windows(d0: dt.date, d1: dt.date):
    cur = dt.date(d0.year, d0.month, 1)
    while cur <= d1:
        nxt = dt.date(cur.year + (cur.month == 12), (cur.month % 12) + 1, 1)
        yield (_ist(cur.isoformat(), "00:00:00"), _ist(nxt.isoformat(), "00:00:00"))
        cur = nxt


def build_plan():
    """One statement per symbol-month: the run count per symbol-day."""
    plan = []
    for sym in SYMBOLS:
        for t0, t1 in month_windows(DAY_FROM, DAY_TO):
            rows, _ = roq(render(PLAN_SQL, sym, t0, t1), "plan_%s_%s" % (sym, t0[:7]))
            for r in rows:
                if DAY_FROM.isoformat() <= r["day"] <= DAY_TO.isoformat():
                    plan.append({"symbol": sym, "day": r["day"],
                                 "n_runs": int(r["n_runs"])})
            pause()
    # 2026-08-27 first, so C4 -- a stop -- is reached early; then by date.
    plan.sort(key=lambda p: (p["day"] != C4_DAY, p["day"], p["symbol"]))
    return plan


def halves_for(n_runs: int):
    return [None] if n_runs <= MAX_ROWS else [0, 1]


# ---------------------------------------------------------------- assembly

def parse_ist(s: str) -> dt.datetime:
    """A Postgres-rendered naive timestamp into a datetime (A2.3).

    The column is already `ts AT TIME ZONE 'Asia/Kolkata'`, so the value carries
    no offset. Postgres strips TRAILING zeros from the fractional second, so
    '.50508' means 505080 microseconds -- the pad is on the RIGHT. A left pad
    would read it as 50508 us, 0.45 s early, and Python 3.10's fromisoformat
    accepts only 0, 3 or 6 fraction digits, which is what crashed attempt
    A2-1 on '2026-08-27T14:40:06.50508'.

    Conversion only: it cannot change a figure's arithmetic, a stop's test, a
    set, a window or a stratum -- it decides which datetime the string denotes,
    and nothing else.
    """
    s = s.strip().replace(" ", "T")
    if "." in s:
        head, rest = s.split(".", 1)
        i = 0
        while i < len(rest) and rest[i].isdigit():
            i += 1
        frac, tail = rest[:i], rest[i:]
        s = head + "." + (frac[:6].ljust(6, "0") if frac else "000000") + tail
    return dt.datetime.fromisoformat(s)


def build_agg(q1: dict, q2: dict, q3: dict, q4: dict) -> dict:
    gch = None
    if any(q4.get(k) is not None for k in
           ("gch_net_gex", "gch_pin_leader_strike", "gch_conc_top1_share",
            "gch_conc_hhi")):
        gch = {"net_gex": q4.get("gch_net_gex"),
               "pin_leader_strike": q4.get("gch_pin_leader_strike"),
               "conc_top1_share": q4.get("gch_conc_top1_share"),
               "conc_hhi": q4.get("gch_conc_hhi")}
    gm = None if q4.get("gm_net_gex") is None else {"net_gex": q4["gm_net_gex"]}
    a = dict(q1)
    a.update(q2)
    a.update(q3)
    a["ts"] = parse_ist(q1["v1_ts_ist"])
    a["expiry_date"] = q1["v1_expiry_date"]
    a["spot"] = q2["spot"]
    a["r_symbol"] = q2["symbol"]
    a["r_rule_version"] = q2["rv_run"]
    a["gch"] = gch
    a["gm"] = gm
    a["v1_chain_status"] = q4.get("v1_chain_status")
    return a


B2_FIELDS = ("symbol", "n", "n_map", "n_band", "n_both", "n_call", "n_put",
             "s_oic", "s_oip", "s_net", "s_gross", "s_gamma", "sk_net",
             "sk_gross", "r_net_cr", "r_net_top_share", "r_gross_band_cr",
             "r_gross_top_share", "r_gross_hhi", "r_n_map", "r_n_zero",
             "rv_strike", "rv_run")


def b2_row(q2: dict) -> dict:
    return {k: q2.get(k) for k in B2_FIELDS}


def partition_v2_runs(q2: dict, sym: str, day: str):
    """A1.1: split the day's gex_run_v2 rows into the STAMPED population and
    the runs carrying another rule_version. Pure, so the self-test can show
    that a differently stamped run lands in not_stamp and not in v2_runs."""
    stamped, not_stamp = [], []
    for rid, r in sorted(q2.items()):
        rec = {"run_id": rid, "symbol": sym, "day": day,
               "rv_run": r.get("rv_run")}
        (stamped if r.get("rv_run") == L.RULE_STAMP else not_stamp).append(rec)
    return stamped, not_stamp


# ---------------------------------------------------------------- the pull

def pull_symbol_day(sym: str, day: str, n_runs: int, out, state):
    for half in halves_for(n_runs):
        t0, t1 = bounds(day, half)
        tag = "%s_%s%s" % (sym, day, "" if half is None else "_h%d" % half)
        res = {}
        for name, tmpl in TEMPLATES:
            rows, _ = roq(render(tmpl, sym, t0, t1), "%s_%s" % (name, tag))
            res[name] = {r["run_id"]: r for r in rows}
            pause()
        q1, q2, q3, q4 = (res["Q1_v1"], res["Q2_v2"], res["Q3_cross"], res["Q4_aux"])

        # A1.1: the population is the STAMPED runs; a gex_run_v2 run carrying
        # another rule_version is counted and listed by date, never silently
        # skipped.
        stamped, not_stamp = partition_v2_runs(q2, sym, day)
        state["v2_runs"].extend(stamped)
        state["not_stamp"].extend(not_stamp)
        for rid in q1:
            state["v1_runs"].append({"run_id": rid, "symbol": sym, "day": day})

        for rid in sorted(set(q1) & set(q2)):
            if rid not in q3:
                raise Stop("run %s has no cross row (Q3) -- %s" % (rid, tag))
            if q2[rid].get("rv_run") != L.RULE_STAMP:
                continue   # counted above as not_stamp (A1.1)
            a = build_agg(q1[rid], q2[rid], q3[rid], q4.get(rid, {}))
            rec = L.figures_from_agg(a)
            rec["v1_n"] = a["v1_n"]
            rec["v2_n_map"] = a["v2_n_map"]
            rec["v1_spot_n"] = a["v1_spot_n"]
            rec["gch_present"] = a["gch"] is not None
            rec["gm_present"] = a["gm"] is not None
            rec["half"] = half
            if not rec["C3"]:
                raise Stop("C3 failed on run %s (%s): net_cr %r vs sum %r"
                           % (rid, tag, a["r_net_cr"], a["v2_strike_sum"]))
            if not rec["C6"]["ok"]:
                raise Stop("C6 failed on run %s (%s): %r" % (rid, tag, rec["C6"]))
            out.write(json.dumps(rec, default=str) + "\n")
            state["n"] += 1
            if day == C4_DAY:
                state["c4_got"][rid] = b2_row(q2[rid])
        out.flush()


def run_c4(state):
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    res = L.c4_compare(expected, state["c4_got"])
    C4JSON.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    log("C4: expected=%d compared=%d missing=%d fail_runs=%d ok=%s"
        % (res["n_expected"], res["n_compared"], res["n_missing"],
           res["n_fail_runs"], res["ok"]))
    if not res["ok"]:
        for f in res["fails"][:10]:
            log("C4 fail: %r" % (f,))
        raise Stop("C4 failed on the known day %s: %d failures over %d runs"
                   % (C4_DAY, res["n_fails"], res["n_fail_runs"]))


def main(argv) -> int:
    if argv and argv[0] == "--explain":
        return explain_gate()
    if argv and argv[0] == "--plan":
        plan = build_plan()
        PLANJSON.write_text(json.dumps(plan, indent=1), encoding="utf-8")
        print("symbol-days: %d   runs: %d   queries: %d"
              % (len(plan), sum(p["n_runs"] for p in plan),
                 sum(len(halves_for(p["n_runs"])) * len(TEMPLATES) for p in plan)))
        return 0
    if argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    if PERRUN.exists():
        print("PULL STOPPED per_run.jsonl already exists -- the one look is used")
        return 2

    state = {"n": 0, "v1_runs": [], "v2_runs": [], "not_stamp": [],
             "c4_got": {}, "c4_done": False}
    t_start = time.monotonic()
    try:
        deadline_guard()      # refuse to START inside the closed window
    except Stop as e:
        print("PULL STOPPED %s" % e)
        return 3
    log("pull start -- design PREREG.md + PREREG_A1.md, read-only, merdian_ro")
    try:
        plan = (json.loads(PLANJSON.read_text(encoding="utf-8"))
                if PLANJSON.exists() else build_plan())
        PLANJSON.write_text(json.dumps(plan, indent=1), encoding="utf-8")
        log("plan: %d symbol-days, %d runs, %d queries"
            % (len(plan), sum(p["n_runs"] for p in plan),
               sum(len(halves_for(p["n_runs"])) * len(TEMPLATES) for p in plan)))
        with PERRUN.open("w", encoding="utf-8") as out:
            for i, p in enumerate(plan, 1):
                pull_symbol_day(p["symbol"], p["day"], p["n_runs"], out, state)
                log("[%d/%d] %s %s n_runs=%d written=%d queries=%d"
                    % (i, len(plan), p["day"], p["symbol"], p["n_runs"],
                       state["n"], STATS["queries"]))
                if (not state["c4_done"] and p["day"] == C4_DAY
                        and not any(q["day"] == C4_DAY for q in plan[i:])):
                    run_c4(state)
                    state["c4_done"] = True
        if not state["c4_done"]:
            raise Stop("the known day %s was not in the plan, so C4 never ran"
                       % C4_DAY)
        pop = L.population_split(state["v2_runs"], state["v1_runs"])
        ns_by_date: dict = {}
        for r in state["not_stamp"]:
            ns_by_date.setdefault(r["day"], {}).setdefault(r["symbol"], 0)
            ns_by_date[r["day"]][r["symbol"]] += 1
        pop["n_not_stamp"] = len(state["not_stamp"])
        pop["not_stamp_by_date"] = ns_by_date
        pop["not_stamp"] = sorted(state["not_stamp"],
                                  key=lambda r: (r["day"], r["symbol"], r["run_id"]))
        pop["not_stamp_rule_versions"] = sorted(
            {str(r.get("rv_run")) for r in state["not_stamp"]})
        pop["n_not_stamp_on_c4_day"] = sum(
            ns_by_date.get(C4_DAY, {}).values())
        POPJSON.write_text(json.dumps(pop, indent=1), encoding="utf-8")
        log("population: both=%d v2_only=%d v1_only=%d not_stamp=%d "
            "not_stamp_on_%s=%d"
            % (pop["n_both"], pop["n_v2_only"], pop["n_v1_only"],
               pop["n_not_stamp"], C4_DAY, pop["n_not_stamp_on_c4_day"]))
        log("queries=%d elapsed=%.0fs slowest=%.2fs (%s)"
            % (STATS["queries"], time.monotonic() - t_start,
               STATS["slowest"], STATS["slowest_label"]))
        log("PULL FINISHED runs=%d" % state["n"])
        print("PULL FINISHED runs=%d" % state["n"])
        return 0
    except Stop as e:
        log("queries=%d elapsed=%.0fs slowest=%.2fs (%s)"
            % (STATS["queries"], time.monotonic() - t_start,
               STATS["slowest"], STATS["slowest_label"]))
        log("PULL STOPPED %s" % e)
        print("PULL STOPPED %s" % e)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
