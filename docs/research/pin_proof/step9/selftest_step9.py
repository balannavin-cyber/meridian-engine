"""Step 9 self-test (C5, A1.5). No database, no network, no files read.

Two invented runs with F1 to F7 worked by hand below, then the nine broken
versions C5 lists. Each broken version must make at least one of the hand-worked
assertions fail; a broken version that passes is itself a failure.

A1 adds: one invented run HAS a gex_cycle_history row (run A) and one has NONE
(run B), so C1a, C2 and C7 are exercised both ways.

Run with:  ulimit -v 700000 && python3 -B selftest_step9.py
Last line on success:  SELFTEST PASS -- 9 mutants
"""

from __future__ import annotations

import datetime as dt
import math
import sys

import step9_lib as L
import step9_pull as P


def close(a, b, tol=1e-12):
    assert a is not None and b is not None, "close() on None: %r %r" % (a, b)
    assert math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tol), \
        "expected %r, got %r" % (b, a)


# ---------------------------------------------------------------- run A
# NIFTY, spot 20000, strike step 50, the 5 % band is [19000, 21000].
# V1 strike rows (gex_strike_snapshots), gex_cr in Cr per 100 % move:
#   19900  +10   gamma_call 1e-4, gamma_put None
#   20000  -30   gamma_call 2e-4, gamma_put 2e-4
#   20100  +20   gamma_call None, gamma_put 1e-6
#   22000   -5   gamma_call 1e-4, gamma_put 1e-6      (far: 2000 > 1000)
# V1 by hand: net -5, sum abs 65, r 5/65, peak 20000 (abs 30),
#   largest positive 20100 (+20), top share 30/65, HHI 1425/4225.
# V2 map rows (gex_strike_v2): 19900 +12, 20000 -28, 20100 +20, 20200 +3,
#   and 22000 -1 with in_map FALSE (outside the map, excluded).
# V2 by hand: map sum 7, sum abs 63, peak 20000 (abs 28), largest positive
#   20100, HHI 1337/3969, run net_cr 7, run net_top_share 28/63.

def run_a():
    return {
        "run_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "symbol": "NIFTY",
        "expiry_date": "2026-11-27",
        "ts": dt.datetime(2026, 11, 25, 10, 30, 6),
        "spot": 20000.0,
        "v1_dte": 2, "v1_dte_n": 1,
        "v1_chain_status": "OK",
        "v1_strikes": [
            {"strike": 19900.0, "gex_cr": 10.0, "gamma_call": 1e-4, "gamma_put": None},
            {"strike": 20000.0, "gex_cr": -30.0, "gamma_call": 2e-4, "gamma_put": 2e-4},
            {"strike": 20100.0, "gex_cr": 20.0, "gamma_call": None, "gamma_put": 1e-6},
            {"strike": 22000.0, "gex_cr": -5.0, "gamma_call": 1e-4, "gamma_put": 1e-6},
        ],
        "v2_run": {"net_cr": 7.0, "net_top_share": 28.0 / 63.0, "dte": 2,
                   "spot": 20000.0, "ts": dt.datetime(2026, 11, 25, 10, 30, 6),
                   "symbol": "NIFTY", "expiry_date": "2026-11-27",
                   "rule_version": L.RULE_STAMP},
        "v2_strikes": [
            {"strike": 19900.0, "net_cr": 12.0, "in_map": True},
            {"strike": 20000.0, "net_cr": -28.0, "in_map": True},
            {"strike": 20100.0, "net_cr": 20.0, "in_map": True},
            {"strike": 20200.0, "net_cr": 3.0, "in_map": True},
            {"strike": 22000.0, "net_cr": -1.0, "in_map": False},
        ],
        "gch": {"net_gex": -5.0, "pin_leader_strike": 20000.0,
                "conc_top1_share": 30.0 / 65.0, "conc_hhi": 1425.0 / 4225.0},
        "gm": {"net_gex": -5.005},
    }


# ---------------------------------------------------------------- run B
# SENSEX, spot 80000, strike step 100, the 5 % band is [76000, 84000].
# Pre-open (09:10), chain check NOT_COMPUTED, NO gex_cycle_history row and NO
# gamma_metrics row.
#   79900    0   no gamma
#   80000  +40   gamma_call 3e-4, gamma_put None
#   90000  +10   gamma_call 6e-5, gamma_put 7e-5      (far: 10000 > 4000)
# V1 by hand: net 50, sum abs 50, r 1.0, peak 80000, largest positive 80000,
#   top share 0.8, HHI 1700/2500 = 0.68.
# V2 map: 80000 +41, 80100 0. run net_cr 41, net_top_share 1.0, HHI 1.0.

def run_b():
    return {
        "run_id": "bbbbbbbb-0000-0000-0000-000000000002",
        "symbol": "SENSEX",
        "expiry_date": "2026-09-18",
        "ts": dt.datetime(2026, 9, 15, 9, 10, 5),
        "spot": 80000.0,
        "v1_dte": 0, "v1_dte_n": 1,
        "v1_chain_status": "NOT_COMPUTED",
        "v1_strikes": [
            {"strike": 79900.0, "gex_cr": 0.0, "gamma_call": None, "gamma_put": None},
            {"strike": 80000.0, "gex_cr": 40.0, "gamma_call": 3e-4, "gamma_put": None},
            {"strike": 90000.0, "gex_cr": 10.0, "gamma_call": 6e-5, "gamma_put": 7e-5},
        ],
        "v2_run": {"net_cr": 41.0, "net_top_share": 1.0, "dte": 0,
                   "spot": 80000.0, "ts": dt.datetime(2026, 9, 15, 9, 10, 5),
                   "symbol": "SENSEX", "expiry_date": "2026-09-18",
                   "rule_version": L.RULE_STAMP},
        "v2_strikes": [
            {"strike": 80000.0, "net_cr": 41.0, "in_map": True},
            {"strike": 80100.0, "net_cr": 0.0, "in_map": True},
        ],
        "gch": None,
        "gm": None,
    }


# ---------------------------------------------------------------- the checks

def check_boundaries():
    """§3 boundaries and the §5 bin edges, stated as beliefs then tested."""
    assert L.classify_set(dt.datetime(2026, 11, 25, 9, 14, 59)) == "pre_open"
    assert L.classify_set(dt.datetime(2026, 11, 25, 9, 15, 0)) == "main"
    assert L.classify_set(dt.datetime(2026, 11, 25, 15, 30, 6)) == "main"
    assert L.classify_set(dt.datetime(2026, 11, 25, 15, 31, 0)) == "post_close"
    assert L.main_window(dt.datetime(2026, 11, 25, 10, 59, 59)) == "w1_0915_1059"
    assert L.main_window(dt.datetime(2026, 11, 25, 11, 0, 0)) == "w2_1100_1359"
    assert L.main_window(dt.datetime(2026, 11, 25, 14, 0, 0)) == "w3_1400_1530"
    assert L.is_0915(dt.datetime(2026, 11, 25, 9, 15, 6)) is True
    # A run with r exactly 1 % belongs to the 1-to-5 % bin, never the lower one.
    assert L.bin_r(0.01) == "1_to_5pct", L.bin_r(0.01)
    assert L.bin_r(0.009999) == "under_1pct"
    assert L.bin_r(0.05) == "5pct_or_more"
    assert L.bin_rel(0.01) == "1_to_10pct"
    assert L.bin_rel(0.50) == "50pct_or_more"
    assert L.dte_bucket(0) == "0" and L.dte_bucket(2) == "1_to_2" \
        and L.dte_bucket(3) == "3_or_more"
    # The one place a put side is negated.
    close(L.strike_net_from_legs(2e-4, 1_000_000, 1e-4, 500_000, 20000.0), 6000.0, 1e-9)


def check_run_a():
    r = run_a()
    g = L.figures(r)
    close(g["F1"]["v1"], -5.0)
    close(g["F1"]["v2"], 7.0)
    close(g["F1"]["diff"], 12.0)
    close(g["F1"]["rel"], 12.0 / 5.0)
    assert g["F1"]["rel_bin"] == "50pct_or_more"
    assert g["F2"]["v1_sign"] == "negative" and g["F2"]["v2_sign"] == "positive"
    close(g["F2"]["v1_r"], 5.0 / 65.0)
    close(g["F2"]["v2_r"], 7.0 / 63.0)
    assert g["F2"]["v1_r_bin"] == "5pct_or_more"
    close(g["F3"]["v1_strike"], 20000.0)
    close(g["F3"]["v2_strike"], 20000.0)
    assert g["F3"]["same"] is True and g["F3"]["v1_ties"] == 1
    close(g["F3"]["steps"], 0.0)
    close(g["F3b"]["v1_strike"], 20100.0)
    close(g["F3b"]["v2_strike"], 20100.0)
    assert g["F3b"]["same"] is True and g["F3b"]["one_side_none"] is False
    close(g["F4"]["v1"], 30.0 / 65.0)
    close(g["F4"]["v2"], 28.0 / 63.0)
    close(g["F4"]["diff_pp"], (28.0 / 63.0 - 30.0 / 65.0) * 100.0)
    close(g["F5"]["v1"], 1425.0 / 4225.0)
    close(g["F5"]["v2"], 1337.0 / 3969.0)
    close(g["F5"]["diff"], 1337.0 / 3969.0 - 1425.0 / 4225.0)
    f6 = g["F6"]
    assert f6["n_union"] == 5, f6["n_union"]
    assert (f6["n_both"], f6["n_v1_only"], f6["n_v2_only"]) == (3, 1, 1), f6
    assert f6["n_sign_change"] == 2 and f6["n_sign_change_both_nonzero"] == 0
    assert f6["n_v1_zero_v2_nonzero"] == 1 and f6["n_v1_nonzero_v2_zero"] == 1
    close(f6["w_num"], 12.0)
    close(f6["w_den"], 65.0)
    close(f6["W"], 12.0 / 65.0)
    assert f6["W_bin"] == "10_to_50pct"
    f7 = g["F7"]
    assert f7["legs_with_gamma"] == 6, f7["legs_with_gamma"]
    assert f7["legs_removed"] == 1, f7["legs_removed"]
    close(f7["share_abs_at_removed"], 5.0 / 65.0)
    close(f7["f1_v1_in5"], 0.0)
    close(f7["f1_v2_in5"], 7.0)
    close(f7["f1_diff_in5"], 7.0)
    assert f7["f1_rel_in5"] is None          # V1 nets to zero inside the band
    close(f7["W_in5"], 7.0 / 60.0)
    assert g["C1a"] is True, g["C1a"]
    assert g["C1b"] is True, g["C1b"]
    assert g["C2"] is True, g["C2"]
    assert g["C3"] is True
    assert g["C6"]["ok"] is True, g["C6"]
    assert g["C7"]["top_share_equal"] is True and g["C7"]["hhi_equal"] is True
    s = g["strata"]
    assert s == {"symbol": "NIFTY", "set": "main", "window": "w1_0915_1059",
                 "dte": "1_to_2", "chain": "OK",
                 "schedule": "from_2026_10_26", "provenance": "period_1",
                 "day": "2026-11-25"}, s


def check_run_b():
    r = run_b()
    g = L.figures(r)
    close(g["F1"]["v1"], 50.0)
    close(g["F1"]["v2"], 41.0)
    close(g["F1"]["diff"], -9.0)
    close(g["F1"]["rel"], 9.0 / 50.0)
    assert g["F1"]["rel_bin"] == "10_to_50pct"
    close(g["F2"]["v1_r"], 1.0)
    close(g["F2"]["v2_r"], 1.0)
    close(g["F3"]["v1_strike"], 80000.0)
    assert g["F3"]["same"] is True
    close(g["F3b"]["v1_strike"], 80000.0)
    close(g["F3b"]["v2_strike"], 80000.0)
    close(g["F4"]["v1"], 0.8)
    close(g["F4"]["diff_pp"], 20.0)
    close(g["F5"]["v1"], 0.68)
    close(g["F5"]["v2"], 1.0)
    close(g["F5"]["diff"], 0.32)
    f6 = g["F6"]
    assert f6["n_union"] == 4, f6["n_union"]
    assert (f6["n_both"], f6["n_v1_only"], f6["n_v2_only"]) == (1, 2, 1), f6
    assert f6["n_sign_change"] == 1 and f6["n_v1_nonzero_v2_zero"] == 1
    close(f6["w_num"], 11.0)
    close(f6["w_den"], 50.0)
    close(f6["W"], 0.22)
    f7 = g["F7"]
    assert f7["legs_with_gamma"] == 3, f7["legs_with_gamma"]
    assert f7["legs_removed"] == 2, f7["legs_removed"]
    close(f7["share_abs_at_removed"], 0.2)
    close(f7["f1_v1_in5"], 40.0)
    close(f7["f1_v2_in5"], 41.0)
    close(f7["f1_rel_in5"], 1.0 / 40.0)
    close(f7["W_in5"], 1.0 / 40.0)
    # No gex_cycle_history row and no gamma_metrics row: the stored-value
    # controls abstain rather than pass.
    assert g["C1a"] is None and g["C2"] is None and g["C1b"] is None
    assert g["C7"]["top_share_equal"] is None and g["C7"]["hhi_equal"] is None
    assert g["C3"] is True and g["C6"]["ok"] is True
    s = g["strata"]
    assert s == {"symbol": "SENSEX", "set": "pre_open", "window": None,
                 "dte": "0", "chain": "NOT_COMPUTED",
                 "schedule": "before_2026_10_26", "provenance": "period_1",
                 "day": "2026-09-15"}, s


def check_summaries():
    recs = [L.figures(run_a()), L.figures(run_b())]
    by_symbol = L.summarise(recs, lambda r: r["strata"]["symbol"])
    assert set(by_symbol) == {"NIFTY", "SENSEX"}
    assert by_symbol["NIFTY"]["n_runs"] == 1
    close(by_symbol["NIFTY"]["F1_signed"]["median"], 12.0)
    close(by_symbol["SENSEX"]["F1_abs"]["median"], 9.0)
    t = by_symbol["NIFTY"]["F2_table"]
    assert t["negative"]["positive"] == 1
    d = L.day_level(recs)
    # Only run A is in the main set, and one run is fewer than 37.
    assert d["all_days"]["n_days"] == 1, d["all_days"]
    assert d["days_ge_37_main"]["n_days"] == 0
    assert d["short_days"] == [{"day": "2026-11-25", "symbol": "NIFTY",
                                "n_main": 1}], d["short_days"]
    close(L.quantile([1.0, 2.0, 3.0, 4.0], 0.5), 2.5)
    assert L.k_of_n(3, 7) == "3 of 7"


def check_population():
    """A1.1: the population, and the runs in one table only, listed by date."""
    v2 = [{"run_id": "r1", "symbol": "NIFTY", "day": "2026-08-27"},
          {"run_id": "r2", "symbol": "NIFTY", "day": "2026-08-27"},
          {"run_id": "r3", "symbol": "SENSEX", "day": "2026-08-28"}]
    v1 = [{"run_id": "r1", "symbol": "NIFTY", "day": "2026-08-27"},
          {"run_id": "r4", "symbol": "SENSEX", "day": "2026-08-28"}]
    p = L.population_split(v2, v1)
    assert p["n_v2_runs"] == 3 and p["n_v1_runs"] == 2, p
    assert p["n_both"] == 1 and p["population"] == ["r1"], p
    assert p["n_v2_only"] == 2 and p["n_v1_only"] == 1, p
    assert p["v2_only_by_date"] == {"2026-08-27": {"NIFTY": 1},
                                    "2026-08-28": {"SENSEX": 1}}, p
    assert p["v1_only_by_date"] == {"2026-08-28": {"SENSEX": 1}}, p


# One real fixture record of b2_expected_2026-08-27.json, copied field for field
# so the B2 limits are exercised on the magnitudes they will meet.
B2_ROW = {
    "symbol": "NIFTY", "n": 105, "n_map": 105, "n_band": 48, "n_both": 32,
    "n_call": 53, "n_put": 20, "s_oic": 192949575.0, "s_oip": 107363815.0,
    "r_n_map": 105, "r_n_zero": 0,
    "s_net": 3166083.032738026, "s_gross": 12280242.900559064,
    "s_gamma": 0.025075, "sk_net": 78391262667.6704,
    "sk_gross": 297912189768.3501,
    "r_net_cr": 3166083.032738026, "r_gross_band_cr": 12201089.748829918,
    "r_net_top_share": 0.14436676128698694,
    "r_gross_top_share": 0.16045003086928541,
    "r_gross_hhi": 0.08399730454755562,
    "rv_strike": "v2-1.2-gss", "rv_run": "v2-1.2-gss",
}


def got_row():
    """The database row C4 compares against the fixture. A separate function so
    the additional mutant can remove a field from the DATABASE side only."""
    return dict(B2_ROW)


def check_c4():
    """C4 (stop): the known day against the fixture, within the B2 limits."""
    exp = {"X": dict(B2_ROW)}
    ok = L.c4_compare(exp, {"X": got_row()})
    assert ok["ok"] is True and ok["n_fails"] == 0, ok
    assert ok["n_expected"] == 1 and ok["n_compared"] == 1 and ok["n_missing"] == 0

    def broken(**over):
        g = dict(B2_ROW)
        g.update(over)
        return L.c4_compare(exp, {"X": g})

    # A count off by one, a stamp off, and a share off by 1e-8 must all fail:
    # the share limit is 1e-9 ABSOLUTE with zero relative allowance.
    assert broken(n_band=47)["ok"] is False
    assert broken(rv_run="v2-1.1")["ok"] is False
    assert broken(r_net_top_share=B2_ROW["r_net_top_share"] + 1e-8)["ok"] is False
    # And a difference inside the limit must pass, or the check is a wall.
    assert broken(r_net_top_share=B2_ROW["r_net_top_share"] + 1e-12)["ok"] is True
    # A field the fixture holds but the database row does not, and a field
    # present as None, are both failures recorded as "field missing" -- a
    # comparison that reads nothing must not pass.
    for field in ("n_band", "s_net", "r_gross_hhi", "rv_run"):
        g = dict(B2_ROW)
        del g[field]
        r = L.c4_compare(exp, {"X": g})
        assert r["ok"] is False, (field, r)
        assert any(f[2] == field and f[3] == "field missing" for f in r["fails"]), \
            (field, r["fails"])
        r2 = L.c4_compare(exp, {"X": dict(B2_ROW, **{field: None})})
        assert r2["ok"] is False, (field, r2)
        assert any(f[2] == field and f[3] == "field missing" for f in r2["fails"]), \
            (field, r2["fails"])
    # A fixture run absent from the database is a failure and is listed.
    m = L.c4_compare(exp, {})
    assert m["ok"] is False and m["n_missing"] == 1 and m["missing"] == ["X"], m
    # A run in the database that the fixture does not hold is listed, not compared.
    e = L.c4_compare(exp, {"X": got_row(), "Y": got_row()})
    assert e["ok"] is True and e["extra_in_db"] == ["Y"], e


def check_pull_guards():
    """The pull's own two guards: the deadline clock and the rule-version split."""
    # 2026-11-24 is a Tuesday, 2026-11-27 a Friday, 2026-11-28 a Saturday.
    assert P.in_closed_window(dt.datetime(2026, 11, 24, 8, 16, tzinfo=P.IST)) is True
    assert P.in_closed_window(dt.datetime(2026, 11, 28, 8, 16, tzinfo=P.IST)) is False
    assert P.in_closed_window(dt.datetime(2026, 11, 27, 20, 0, tzinfo=P.IST)) is False
    assert P.in_closed_window(dt.datetime(2026, 11, 24, 8, 14, tzinfo=P.IST)) is False
    assert P.in_closed_window(dt.datetime(2026, 11, 24, 15, 40, tzinfo=P.IST)) is False

    # A gex_run_v2 run carrying another rule_version lands in not_stamp and
    # NOT in the population.
    q2 = {"keep": {"rv_run": L.RULE_STAMP}, "drop": {"rv_run": "v2-1.1-chain"},
          "none": {"rv_run": None}}
    stamped, not_stamp = P.partition_v2_runs(q2, "NIFTY", "2026-08-27")
    assert [r["run_id"] for r in stamped] == ["keep"], stamped
    assert sorted(r["run_id"] for r in not_stamp) == ["drop", "none"], not_stamp
    assert {r["rv_run"] for r in not_stamp} == {"v2-1.1-chain", None}


# Postgres strips TRAILING zeros from the fractional second, so the pull meets
# 0 to 6 fraction digits. These go through the SAME parse path the pull uses
# (step9_pull.parse_ist), which is the seam attempt A2-1 crashed on.
PARSE_CASES = (
    ("2026-08-27T14:40:06", 0),
    ("2026-08-27T14:40:06.5", 500000),
    ("2026-08-27T14:40:06.50", 500000),
    ("2026-08-27T14:40:06.505", 505000),
    ("2026-08-27T14:40:06.5050", 505000),
    ("2026-08-27T14:40:06.50508", 505080),     # the value that crashed A2-1
    ("2026-08-27T14:40:06.505080", 505080),
    ("2026-08-27 14:40:06.50508", 505080),     # space form, same instant
)


def check_parse_seam():
    """A2.4: the database-text seam. Any exception counts as a failure, so a
    parser that does not pad (ValueError on 3.10) is caught here as surely as
    one that pads on the left (wrong microsecond)."""
    for s, us in PARSE_CASES:
        try:
            got = P.parse_ist(s)
        except Exception as e:                      # noqa: BLE001 - see docstring
            raise AssertionError("parse_ist(%r) raised %r" % (s, e))
        assert got.microsecond == us, (s, got.microsecond, us)
        assert (got.year, got.month, got.day) == (2026, 8, 27), (s, got)
        assert (got.hour, got.minute, got.second) == (14, 40, 6), (s, got)
    # The parsed value is what §3's set and window are derived from.
    assert L.classify_set(P.parse_ist("2026-08-27T14:40:06.50508")) == "main"
    assert L.main_window(P.parse_ist("2026-08-27T14:40:06.50508")) == "w3_1400_1530"
    assert L.classify_set(P.parse_ist("2026-08-27T09:14:59.9")) == "pre_open"
    assert L.classify_set(P.parse_ist("2026-08-27T15:30:06.5")) == "main"


def run_checks():
    check_boundaries()
    check_run_a()
    check_run_b()
    check_summaries()
    check_population()
    check_c4()
    check_pull_guards()
    check_parse_seam()


# ---------------------------------------------------------------- the mutants

def _mut_f1_swapped():
    orig = L.f1
    def broken(run):
        out = orig(run)
        out["v1"], out["v2"] = out["v2"], out["v1"]
        out["diff"] = -out["diff"]
        return out
    L.f1 = broken


def _mut_put_not_negated():
    L.strike_net_from_legs = lambda gc, oc, gp, op, s: (
        float(gc) * float(oc) + float(gp) * float(op)) * float(s) ** 2 / 1e7


def _mut_peak_no_abs():
    L.v1_peak = lambda strikes, spot: L._peak(
        [{"strike": s["strike"], "k": float(s["gex_cr"])} for s in strikes],
        "k", spot)


def _mut_positive_uses_abs():
    L.v1_largest_positive = lambda strikes, spot: L._peak(
        [{"strike": s["strike"], "k": abs(float(s["gex_cr"]))} for s in strikes],
        "k", spot, positive_only=True)


def _mut_union_drops_v2_only():
    orig = L._union
    def broken(run, within_5pct=False):
        a, b, keys = orig(run, within_5pct)
        return a, b, [k for k in keys if k in a]
    L._union = broken


def _mut_preopen_in_main():
    orig = L.classify_set
    L.classify_set = lambda ts: "main" if orig(ts) == "pre_open" else orig(ts)


def _mut_1530_to_post_close():
    orig = L.classify_set
    def broken(ts):
        if L.minute_of_day(ts) >= L.MAIN_CLOSE:
            return "post_close"
        return orig(ts)
    L.classify_set = broken


def _mut_not_computed_as_ok():
    L.chain_stratum = lambda status: "OK"


def _mut_boundary_into_lower_bin():
    def broken(x, bins):
        if x is None:
            return None
        for name, upper in bins:
            if upper is None or x <= upper:
                return name
        return bins[-1][0]
    L.bin_value = broken


MUTANTS = [
    ("M1 V1 and V2 swapped", _mut_f1_swapped),
    ("M2 the put side not negated", _mut_put_not_negated),
    ("M3 abs left off the peak", _mut_peak_no_abs),
    ("M4 abs wrongly applied to the positive-strike figure", _mut_positive_uses_abs),
    ("M5 a V2-only strike dropped from the union", _mut_union_drops_v2_only),
    ("M6 a pre-open run counted in the main set", _mut_preopen_in_main),
    ("M7 a 15:30 run sent to post-close", _mut_1530_to_post_close),
    ("M8 a NOT_COMPUTED run put in the OK stratum", _mut_not_computed_as_ok),
    ("M9 a run with r exactly 1 % put in the lower bin", _mut_boundary_into_lower_bin),
]

_WATCHED = ("f1", "strike_net_from_legs", "v1_peak", "v1_largest_positive",
            "_union", "classify_set", "chain_stratum", "bin_value")


def _mut_c4_got_missing_field():
    """ADDITIONAL (not one of design C5's nine): remove a field from the
    database row only. c4_compare must report it rather than skip it."""
    globals()["got_row"] = lambda: {k: v for k, v in B2_ROW.items()
                                    if k != "s_gross"}


def _mut_parse_pads_left():
    """ADDITIONAL: the plausible wrong fix -- pad the fraction on the LEFT, so
    '.50508' reads as 50508 us instead of 505080."""
    def broken(s):
        s = s.strip().replace(" ", "T")
        if "." in s:
            head, frac = s.split(".", 1)
            s = head + "." + frac[:6].rjust(6, "0")
        return dt.datetime.fromisoformat(s)
    P.parse_ist = broken


def _mut_parse_no_pad():
    """ADDITIONAL: no pad at all -- what crashed attempt A2-1."""
    P.parse_ist = lambda s: dt.datetime.fromisoformat(s.strip().replace(" ", "T"))


# (name, apply, the module the mutant patches, the attribute to restore)
ADDITIONAL_MUTANTS = [
    ("M10 a field removed from the database row (additional)",
     _mut_c4_got_missing_field, sys.modules[__name__], "got_row"),
    ("M11 the timestamp fraction padded on the LEFT (additional)",
     _mut_parse_pads_left, P, "parse_ist"),
    ("M12 the timestamp fraction not padded at all (additional)",
     _mut_parse_no_pad, P, "parse_ist"),
]


def main() -> int:
    run_checks()
    print("clean run: both invented runs match their hand-worked figures")
    saved = {n: getattr(L, n) for n in _WATCHED}
    caught = 0
    for name, apply_mutant in MUTANTS:
        apply_mutant()
        try:
            run_checks()
        except AssertionError:
            caught += 1
            print("caught: %s" % name)
        else:
            print("NOT CAUGHT: %s" % name)
        finally:
            for n, v in saved.items():
                setattr(L, n, v)
    run_checks()   # the restore is complete

    extra_caught = 0
    for name, apply_mutant, mod, attr in ADDITIONAL_MUTANTS:
        keep = getattr(mod, attr)
        apply_mutant()
        try:
            run_checks()
        except AssertionError:
            extra_caught += 1
            print("caught: %s" % name)
        else:
            print("NOT CAUGHT: %s" % name)
        finally:
            setattr(mod, attr, keep)
    run_checks()   # the restore is complete

    if caught != len(MUTANTS) or extra_caught != len(ADDITIONAL_MUTANTS):
        print("SELFTEST FAIL -- %d of %d required, %d of %d additional"
              % (caught, len(MUTANTS), extra_caught, len(ADDITIONAL_MUTANTS)))
        return 1
    print("additional mutants: %d of %d caught"
          % (extra_caught, len(ADDITIONAL_MUTANTS)))
    print("SELFTEST PASS -- 9 mutants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
