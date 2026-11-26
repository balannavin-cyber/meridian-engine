"""Step 9: the summary. Reads per_run.jsonl and writes RESULT.md.

No database. No interpretation, no adjectives, no verdict -- the figures and the
counts, in the order PREREG.md §5 and the task's P5 set out. Every exposure is
crore per 100 % move, the stored unit (ADR-032); every count is k of n.

Usage: ulimit -v 700000 && python3 -B step9_summary.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

import step9_lib as L

HERE = Path(__file__).resolve().parent
PERRUN = HERE / "per_run.jsonl"
POPJSON = HERE / "population.json"
C4JSON = HERE / "c4_result.json"
RESULT = HERE / "RESULT.md"
CODEHASH = HERE / "CODE_SHA256SUMS"
C4_DAY = "2026-08-27"
UNVOUCHED_DATES = ("2026-05-25", "2026-05-26", "2026-06-01")

W = []


def w(s: str = "") -> None:
    W.append(s)


def num(x, fmt="%.6g"):
    return "-" if x is None else fmt % float(x)


def kn(k, n):
    return "%d of %d" % (k, n)


def load():
    recs = []
    with PERRUN.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- sections

def sec_header(recs):
    now = subprocess.run(["date"], capture_output=True, text=True,
                         env={"TZ": "Asia/Kolkata", "PATH": "/usr/bin:/bin"})
    w("# Step 9: old against new gamma figures on stored history -- RESULT")
    w()
    w("Date line (Asia/Kolkata): `%s`" % now.stdout.strip())
    w()
    w("Design: `PREREG.md` as amended by `PREREG_A1.md`. Read-only, through")
    w("`bin/roq.sh` as `merdian_ro`. One look: this is it.")
    w()
    w("Unit for every exposure below: **crore per 100 % move**, the stored unit")
    w("(ADR-032). The Board's per-1 % figure is 0.01 times it. Shares and HHI have")
    w("no unit. Every count is k of n.")
    w()
    w("## Code hashes")
    w()
    w("```")
    if CODEHASH.exists():
        w(CODEHASH.read_text(encoding="utf-8").rstrip())
    else:
        for f in ("step9_lib.py", "selftest_step9.py", "step9_pull.py",
                  "step9_summary.py", "PREREG.md", "PREREG_A1.md"):
            p = HERE / f
            if p.exists():
                w("%s  %s" % (sha(p), f))
    w("```")
    w()
    w("Runs in `per_run.jsonl`: **%d**." % len(recs))
    w()


def sec_population(recs):
    w("## Population (A1.1)")
    w()
    if not POPJSON.exists():
        w("`population.json` absent.")
        w()
        return
    p = json.loads(POPJSON.read_text(encoding="utf-8"))
    w("| quantity | count |")
    w("|---|---|")
    w("| `gex_run_v2` runs with stamp `%s` | %d |" % (L.RULE_STAMP, p["n_v2_runs"]))
    w("| runs with rows in `gex_strike_snapshots` | %d |" % p["n_v1_runs"])
    w("| **in both (the population)** | **%d** |" % p["n_both"])
    w("| in `gex_run_v2` only | %d |" % p["n_v2_only"])
    w("| in `gex_strike_snapshots` only | %d |" % p["n_v1_only"])
    w("| `gex_run_v2` runs carrying another `rule_version` | %d |"
      % p.get("n_not_stamp", 0))
    w("| of those, on %s | %d |" % (C4_DAY, p.get("n_not_stamp_on_c4_day", 0)))
    w()
    for key, title in (("v2_only_by_date", "In `gex_run_v2` only, by date"),
                       ("v1_only_by_date",
                        "In `gex_strike_snapshots` only, by date"),
                       ("not_stamp_by_date",
                        "Carrying another `rule_version`, by date")):
        d = p.get(key) or {}
        w("### %s" % title)
        w()
        if not d:
            w("None.")
        else:
            w("| date | symbol | runs |")
            w("|---|---|---|")
            for day in sorted(d):
                for sym in sorted(d[day]):
                    w("| %s | %s | %d |" % (day, sym, d[day][sym]))
        w()
    rv = p.get("not_stamp_rule_versions") or []
    if rv:
        w("Other `rule_version` values seen: %s." % ", ".join("`%s`" % v for v in rv))
        w()


def sec_controls(recs):
    n = len(recs)
    w("## Controls")
    w()
    w("A1.3: C1a, C1b, C2 and C7 are **reported**, none is a stop. C3, C4 and C6")
    w("are **stops** -- the pull ends at the first failure, so a finished pull")
    w("means every run passed them.")
    w()

    def tri(key):
        ok = sum(1 for r in recs if r.get(key) is True)
        bad = sum(1 for r in recs if r.get(key) is False)
        na = sum(1 for r in recs if r.get(key) is None)
        return ok, bad, na

    w("| control | pass | fail | abstained (no row to compare) | denominator |")
    w("|---|---|---|---|---|")
    for key, label in (("C1a", "C1a: V1 net vs `gex_cycle_history.net_gex` (+/-0.01 Cr)"),
                       ("C1b", "C1b: V1 net vs `gamma_metrics.net_gex` (+/-0.01 Cr)"),
                       ("C2", "C2: V1 net peak vs `pin_leader_strike`")):
        ok, bad, na = tri(key)
        w("| %s | %s | %s | %s | %d |"
          % (label, kn(ok, n - na) if n - na else "0 of 0", bad, na, n))
    t_ok = sum(1 for r in recs if r["C7"]["top_share_equal"] is True)
    t_bad = sum(1 for r in recs if r["C7"]["top_share_equal"] is False)
    t_na = sum(1 for r in recs if r["C7"]["top_share_equal"] is None)
    h_ok = sum(1 for r in recs if r["C7"]["hhi_equal"] is True)
    h_bad = sum(1 for r in recs if r["C7"]["hhi_equal"] is False)
    h_na = sum(1 for r in recs if r["C7"]["hhi_equal"] is None)
    w("| C7 top share vs `conc_top1_share` (abs diff <= 1e-6) | %s | %d | %d | %d |"
      % (kn(t_ok, n - t_na) if n - t_na else "0 of 0", t_bad, t_na, n))
    w("| C7 HHI vs `conc_hhi` (abs diff <= 1e-6) | %s | %d | %d | %d |"
      % (kn(h_ok, n - h_na) if n - h_na else "0 of 0", h_bad, h_na, n))
    w("| C3 (stop): run `net_cr` vs sum of `net_cr(K)` | %s | %d | 0 | %d |"
      % (kn(sum(1 for r in recs if r["C3"]), n),
         sum(1 for r in recs if not r["C3"]), n))
    w("| C6 (stop): run identity, and dte single and equal | %s | %d | 0 | %d |"
      % (kn(sum(1 for r in recs if r["C6"]["ok"]), n),
         sum(1 for r in recs if not r["C6"]["ok"]), n))
    w()
    td = [r["C7"]["top_share_diff"] for r in recs
          if r["C7"]["top_share_diff"] is not None]
    hd = [r["C7"]["hhi_diff"] for r in recs if r["C7"]["hhi_diff"] is not None]
    w("C7 differences (V1 computed from the strike rows minus the stored column):")
    w()
    w("| quantity | n | median | max abs |")
    w("|---|---|---|---|")
    for label, vals in (("top share", td), ("HHI", hd)):
        w("| %s | %d | %s | %s |"
          % (label, len(vals), num(L.quantile(vals, 0.5)),
             num(max((abs(v) for v in vals), default=None))))
    w()
    if C4JSON.exists():
        c4 = json.loads(C4JSON.read_text(encoding="utf-8"))
        w("C4 (stop), the known day %s against `b2_expected_2026-08-27.json`"
          % C4_DAY)
        w("(sha256 `d99aa037...7dffa`), within the B2 limits of")
        w("`v2_check_v12/b2_compare.py`:")
        w()
        w("| quantity | value |")
        w("|---|---|")
        w("| fixture runs | %d |" % c4["n_expected"])
        w("| compared | %s |" % kn(c4["n_compared"], c4["n_expected"]))
        w("| missing from the database | %d |" % c4["n_missing"])
        w("| runs with a failing field | %d |" % c4["n_fail_runs"])
        w("| failing fields | %d |" % c4["n_fails"])
        w("| runs in the database not in the fixture (listed, not compared) | %d |"
          % len(c4.get("extra_in_db", [])))
        w()
    else:
        w("`c4_result.json` absent.")
        w()


def sec_provenance(recs):
    w("## Provenance (PREREG.md §5, inputs from PROVENANCE.md)")
    w()
    w("One writer period. The engine compared the row-building code of")
    w("`gex_strike_snapshots` as syntax trees at every commit that touched the")
    w("writer from 2026-05-25 to 2026-11-25 and found no change; the pin lane")
    w("checked it independently from the public repository (114 logged HEADs, 8")
    w("versions of the writer file, 8 functions identical as syntax trees in all 8).")
    w()
    ok = sum(1 for r in recs if r["strata"]["chain"] == "OK")
    nc = len(recs) - ok
    w("| period | runs | chain check OK | NOT_COMPUTED |")
    w("|---|---|---|---|")
    w("| period_1 (2026-05-25 to 2026-11-25) | %d | %s | %s |"
      % (len(recs), kn(ok, len(recs)), kn(nc, len(recs))))
    w()
    w("### Stated limit, not a stratum: dates holding a logged run whose HEAD is "
      "not vouched")
    w()
    w("Six of 19,608 logged writer runs sit at a HEAD that could not be vouched:")
    w("five at `a5163c4` on 2026-05-25 and 2026-05-26 (that commit does not descend")
    w("from `a776d8a`, which introduced the writer) and one with a blank HEAD on")
    w("2026-06-01. All six on the Windows host. A logged HEAD says nothing about")
    w("uncommitted edits in the working tree that day; the log holds 19,608 writer")
    w("runs against 19,050 stored runs and the reason for the 558 extra is not")
    w("known; the log does not tie a logged run to a `run_id`.")
    w()
    w("| date | symbol | runs | chain OK | NOT_COMPUTED |")
    w("|---|---|---|---|---|")
    for day in UNVOUCHED_DATES:
        for sym in ("NIFTY", "SENSEX"):
            rows = [r for r in recs
                    if r["strata"]["day"] == day and r["symbol"] == sym]
            if not rows:
                w("| %s | %s | 0 | 0 of 0 | 0 of 0 |" % (day, sym))
                continue
            o = sum(1 for r in rows if r["strata"]["chain"] == "OK")
            w("| %s | %s | %d | %s | %s |"
              % (day, sym, len(rows), kn(o, len(rows)),
                 kn(len(rows) - o, len(rows))))
    w()


def _cell_table(title, cells):
    w("### %s" % title)
    w()
    w("| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | "
      "F1 diff max | F1 abs median | W median | W max |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for key, c in cells.items():
        w("| %s | %d | %d | %s | %s | %s | %s | %s | %s | %s |"
          % (key, c["n_runs"], c["n_days"],
             num(c["F1_signed"]["median"]), num(c["F1_signed"]["p90"]),
             num(c["F1_signed"]["p99"]), num(c["F1_signed"]["max"]),
             num(c["F1_abs"]["median"]), num(c["W"]["median"]),
             num(c["W"]["max"])))
    w()
    w("| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | "
      "F3 same | F3b same | F3b one side none |")
    w("|---|---|---|---|---|---|---|---|---|")
    for key, c in cells.items():
        b = c["F1_rel_bins"]
        w("| %s | %s | %s | %s | %s | %s | %s | %s | %s |"
          % (key, b["under_1pct"], b["1_to_10pct"], b["10_to_50pct"],
             b["50pct_or_more"], c["F1_v1_zero"], c["F3_same"],
             c["F3b_same"], c["F3b_one_side_none"]))
    w()
    w("| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | "
      "F5 diff max abs | F6 sign-change runs | F6 V2-only runs | "
      "F7 runs with a removal | F7 legs removed / legs with gamma |")
    w("|---|---|---|---|---|---|---|---|---|")
    for key, c in cells.items():
        w("| %s | %s | %s | %s | %s | %s | %s | %s | %d / %d |"
          % (key, num(c["F4_signed"]["median"]), num(c["F4_abs"]["max"]),
             num(c["F5_signed"]["median"]), num(c["F5_abs"]["max"]),
             c["F6_sign_change_runs"], c["F6_v2_only_runs"],
             c["F7_runs_with_removal"], c["F7_legs_removed"],
             c["F7_legs_with_gamma"]))
    w()


def sec_figures(recs):
    w("## Figures of section 4, as amended by A1")
    w()
    w("F1 net exposure, F2 sign of net, F3 net peak strike, F3b largest positive")
    w("net strike, F4 net top share, F5 net HHI, F6 strike level and W, F7 the")
    w("guard beyond 5 %. V1 from the stored strike rows of")
    w("`gex_strike_snapshots` (A1.2); V2 from `gex_strike_v2` and `gex_run_v2`.")
    w("Differences are V2 minus V1.")
    w()
    strata_keys = (
        ("symbol", lambda r: r["strata"]["symbol"]),
        ("set", lambda r: r["strata"]["set"]),
        ("main-set window", lambda r: r["strata"]["window"] or "(not main)"),
        ("dte", lambda r: r["strata"]["dte"]),
        ("V1 chain-check status", lambda r: r["strata"]["chain"]),
        ("schedule period", lambda r: r["strata"]["schedule"]),
        ("provenance period", lambda r: r["strata"]["provenance"]),
        ("symbol x set x dte",
         lambda r: "%s | %s | %s" % (r["strata"]["symbol"], r["strata"]["set"],
                                     r["strata"]["dte"])),
    )
    _cell_table("All runs", {"all": L.cell(recs)})
    for title, key in strata_keys:
        _cell_table("By %s" % title, L.summarise(recs, key))

    main = [r for r in recs if r["strata"]["set"] == "main"]
    if main:
        _cell_table("The 09:15 run, on its own line (also kept in the main set)",
                    L.summarise([r for r in main if r["is_0915"]],
                                lambda r: r["strata"]["symbol"]))

    w("### F2, the 3 x 3 sign table (V1 sign down, V2 sign across)")
    w()
    for sym, c in L.summarise(recs, lambda r: r["strata"]["symbol"]).items():
        t = c["F2_table"]
        w("%s:" % sym)
        w()
        w("| V1 \\ V2 | negative | zero | positive |")
        w("|---|---|---|---|")
        for a in ("negative", "zero", "positive"):
            w("| %s | %d | %d | %d |"
              % (a, t[a]["negative"], t[a]["zero"], t[a]["positive"]))
        w()
    w("### F2, r by fixed bin (r = abs(net) / sum of abs strike net)")
    w()
    w("| symbol | side | r <1% | 1-5% | >=5% | none (sum 0) |")
    w("|---|---|---|---|---|---|")
    for sym in sorted({r["symbol"] for r in recs}):
        rows = [r for r in recs if r["symbol"] == sym]
        for side in ("v1_r_bin", "v2_r_bin"):
            c = {b: sum(1 for r in rows if r["F2"][side] == b)
                 for b in ("under_1pct", "1_to_5pct", "5pct_or_more")}
            none = sum(1 for r in rows if r["F2"][side] is None)
            w("| %s | %s | %s | %s | %s | %s |"
              % (sym, "V1" if side == "v1_r_bin" else "V2",
                 kn(c["under_1pct"], len(rows)), kn(c["1_to_5pct"], len(rows)),
                 kn(c["5pct_or_more"], len(rows)), kn(none, len(rows))))
    w()
    w("### F6 strike-level counts, summed over runs")
    w()
    tot = {k: sum(r["F6"][k] for r in recs) for k in
           ("n_union", "n_both", "n_v1_only", "n_v2_only", "n_sign_change",
            "n_sign_change_both_nonzero", "n_v1_zero_v2_nonzero",
            "n_v1_nonzero_v2_zero")}
    w("| quantity | strikes |")
    w("|---|---|")
    for k, v in tot.items():
        w("| %s | %d |" % (k, v))
    w()
    w("### F7, the guard beyond 5 %")
    w()
    legs = sum(r["F7"]["legs_with_gamma"] for r in recs)
    rm = sum(r["F7"]["legs_removed"] for r in recs)
    sh = [r["F7"]["share_abs_at_removed"] for r in recs
          if r["F7"]["share_abs_at_removed"] is not None]
    r5 = [r["F7"]["f1_rel_in5"] for r in recs if r["F7"]["f1_rel_in5"] is not None]
    w5 = [r["F7"]["W_in5"] for r in recs if r["F7"]["W_in5"] is not None]
    w("| quantity | value |")
    w("|---|---|")
    w("| legs removed, of legs with a stored gamma | %s |" % kn(rm, legs))
    w("| runs with at least one leg removed | %s |"
      % kn(sum(1 for r in recs if r["F7"]["legs_removed"] > 0), len(recs)))
    w("| share of the run's sum of abs `gex_cr` at strikes where a leg was "
      "removed: median | %s |" % num(L.quantile(sh, 0.5)))
    w("| the same, maximum | %s |" % num(max(sh) if sh else None))
    w("| F1 relative change over strikes within 5 %% only: median | %s |"
      % num(L.quantile(r5, 0.5)))
    w("| W over strikes within 5 %% only: median | %s |"
      % num(L.quantile(w5, 0.5)))
    w()


def sec_days(recs):
    d = L.day_level(recs)
    w("## Day level (PREREG.md §5, ruling 4)")
    w()
    w("| scope | days | median over days of the day's median F1 relative change "
      "| maximum over days |")
    w("|---|---|---|---|")
    for label, key in (("all days", "all_days"),
                       ("days with >= 37 main-set runs", "days_ge_37_main")):
        v = d[key]
        w("| %s | %d | %s | %s |"
          % (label, v["n_days"], num(v["median_over_days"]),
             num(v["max_over_days"])))
    w()
    w("### The 10 days with the largest median F1 relative change "
      "(description only)")
    w()
    w("| date | symbol | main-set runs | median F1 relative change |")
    w("|---|---|---|---|")
    for v in d["top10_days_by_median_F1_rel"]:
        w("| %s | %s | %d | %s |"
          % (v["day"], v["symbol"], v["n_main"], num(v["median_F1_rel"])))
    w()
    w("### Days with fewer than 37 main-set runs")
    w()
    if not d["short_days"]:
        w("None.")
    else:
        w("| date | symbol | main-set runs |")
        w("|---|---|---|")
        for v in d["short_days"]:
            w("| %s | %s | %d |" % (v["day"], v["symbol"], v["n_main"]))
    w()


def main() -> int:
    recs = load()
    sec_header(recs)
    sec_population(recs)
    sec_controls(recs)
    sec_provenance(recs)
    sec_figures(recs)
    sec_days(recs)
    RESULT.write_text("\n".join(W) + "\n", encoding="utf-8")
    print("RESULT.md written: %d lines, %d runs"
          % (len(W) + 1, len(recs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
