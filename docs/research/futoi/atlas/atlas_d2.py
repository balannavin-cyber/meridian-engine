"""Study D2, band 0.15 %. READ-ONLY, no new database access.

Break rate by (wall-strike OI rising / falling) x (futures OI rising / falling),
put and call separately, on F and F1, with the rising-minus-falling difference
and a session-clustered percentile bootstrap interval.

TWO REGIMES, reported separately (operator ruling 2026-11-18):
  OPEN       approach minute before 09:45:59. A 30-minute pre-approach window
             would reach before the session start, so for these legs BOTH OI
             changes are measured from the PRIOR SESSION'S CLOSE to the
             approach minute:
               wall strike  oi_last (at the approach) - walls.csv call_oi/put_oi
                            (that strike's OI at the prior close, which is where
                            the wall was defined from in the first place)
               futures      F / F1 at the approach minute - F / F1 at the prior
                            session's 15:29:59
             NO NEW QUERY IS NEEDED: both prior-close values are already on
             disk, in walls.csv and futures_bars.csv respectively.
  INTRADAY   approach minute at or after 09:45:59, measured over the 30 minutes
             before the approach, as extracted.

Every table header states: approaches in the band, approaches carrying a
futures-OI value, and approaches dropped with the reason. Exploratory, no
verdict.
"""
import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_lib as L

HERE = os.path.dirname(os.path.abspath(__file__))
BAND = "0.15"
OPEN_CUTOFF = 9 * 60 + 45          # 09:45; approach minutes below this are OPEN
OUT = os.path.join(HERE, "futoi_atlas_d2_2026-11-18.md")
LINES = []
SIDE_OPT = {"call": "CE", "put": "PE"}


def f(s=""):
    LINES.append(s)


def load():
    D = L.load_all()
    sessions = D["sessions"]
    prior = {d: sessions[i - 1] for i, d in enumerate(sessions) if i}
    walls = {r["trade_date"]: r for r in
             csv.DictReader(open(os.path.join(HERE, "data", "walls.csv"), newline=""))}
    d2 = {}
    with open(os.path.join(HERE, "data", "d2_wall_oi_%s.csv" % BAND), newline="") as fh:
        for r in csv.DictReader(fh):
            d2[(r["trade_date"], r["option_type"])] = r
    rows = []
    with open(os.path.join(HERE, "data", "approaches_%s.csv" % BAND), newline="") as fh:
        appr = [r for r in csv.DictReader(fh) if r["approached"] == "True"]
    for r in appr:
        d = r["trade_date"]
        k = (d, SIDE_OPT[r["side"]])
        rec = {"trade_date": d, "side": r["side"], "wall": float(r["wall"]),
               "approach_min": int(r["approach_min"]),
               "outcome": r.get("outcome") or "",
               "edge": r["edge"] == "True", "expiry_flag": r["expiry_flag"],
               "joined": k in d2, "drop": ""}
        rec["regime"] = "OPEN" if rec["approach_min"] < OPEN_CUTOFF else "INTRADAY"
        if not rec["outcome"]:
            rec["drop"] = "no close-of-session outcome"
        if k not in d2:
            rec["drop"] = rec["drop"] or "no wall-strike OI row"
            rows.append(rec)
            continue
        w = d2[k]
        rec["bars"] = int(w["bars"])
        oi_at_approach = float(w["oi_last"])
        rec["break_rate"] = 1.0 if rec["outcome"] == "BREAK" else 0.0
        if rec["regime"] == "INTRADAY":
            rec["d_oi_wall"] = float(w["d_oi_wall_30"])
            for key in ("F", "F1"):
                a = L.series_at(D[key], d, rec["approach_min"] - 30)
                b = L.series_at(D[key], d, rec["approach_min"])
                rec["d" + key] = None if (a is None or b is None) else b - a
        else:
            wrow = walls.get(d)
            base = float(wrow["call_oi"] if r["side"] == "call" else wrow["put_oi"]) \
                if wrow else None
            rec["d_oi_wall"] = None if base is None else oi_at_approach - base
            p = prior.get(d)
            for key in ("F", "F1"):
                a = L.series_at(D[key], p, L.CLOSE_MIN) if p else None
                b = L.series_at(D[key], d, rec["approach_min"])
                rec["d" + key] = None if (a is None or b is None) else b - a
        if rec["d_oi_wall"] is None:
            rec["drop"] = rec["drop"] or "no prior-close OI at the wall strike"
        rows.append(rec)
    return rows


def rate(rows):
    v = [r["break_rate"] for r in rows]
    return (sum(v) / len(v)) if v else float("nan")


def table(rows, regime, oi_key):
    band_rows = [r for r in rows if r["regime"] == regime]
    f("\n### D2 · band %s %% · %s · futures series %s   [exploratory]\n"
      % (BAND, regime, oi_key))
    usable = [r for r in band_rows
              if not r["drop"] and r.get(oi_key) is not None
              and r.get("d_oi_wall") is not None]
    dropped = {}
    for r in band_rows:
        why = r["drop"] or ("no %s value" % oi_key if r.get(oi_key) is None
                            else ("no wall-strike OI change"
                                  if r.get("d_oi_wall") is None else ""))
        if why:
            dropped[why] = dropped.get(why, 0) + 1
    f("| denominator | n |")
    f("|---|---|")
    f("| approaches in the band, %s | %d |" % (regime, len(band_rows)))
    f("| carrying a futures-OI value and a wall-OI change | %d |" % len(usable))
    for why in sorted(dropped, key=lambda x: -dropped[x]):
        f("| dropped — %s | %d |" % (why, dropped[why]))
    if regime == "INTRADAY":
        f("| legs with bars < 25 among those used | %d — flagged, kept |"
          % sum(1 for r in usable if r.get("bars", 99) < 25))
    f("")
    if regime == "OPEN":
        f("Both OI changes run from the **prior session's close** to the "
          "approach minute. No new query was needed.\n")
    else:
        f("Both OI changes run over the **30 minutes before** the approach "
          "minute.\n")
    for side in ("put", "call"):
        sr = [r for r in usable if r["side"] == side]
        f("\n**%s walls** — %d approaches over %d sessions.\n"
          % (side.capitalize(), len(sr), len({r["trade_date"] for r in sr})))
        if not sr:
            f("*No approaches in this cell.*")
            continue
        f("| wall-strike OI | %s | n approaches | n sessions | break rate |" % oi_key)
        f("|---|---|---|---|---|")
        for wname, wsel in (("rising", lambda r: r["d_oi_wall"] > 0),
                            ("falling", lambda r: r["d_oi_wall"] < 0)):
            for fname, fsel in (("rising", lambda r: r[oi_key] > 0),
                                ("falling", lambda r: r[oi_key] < 0)):
                cell = [r for r in sr if wsel(r) and fsel(r)]
                if not cell:
                    f("| %s | %s | 0 | 0 | — |" % (wname, fname))
                    continue
                f("| %s | %s | %d | %d | %.3f |"
                  % (wname, fname, len(cell),
                     len({r["trade_date"] for r in cell}), rate(cell)))
        rise = [r for r in sr if r["d_oi_wall"] > 0]
        fall = [r for r in sr if r["d_oi_wall"] < 0]
        if rise and fall:
            b = L.boot_diff(rise, fall, "break_rate")
            f("\nDifference, **wall-strike OI rising minus falling**: "
              "**%+.3f** 95%% CI [%+.3f, %+.3f] (%d resamples, seed %d, "
              "%d clusters). Levels %.3f (rising, n=%d) vs %.3f (falling, "
              "n=%d) — levels, not effects.\n"
              % (b["mean"], b["lo"], b["hi"], L.B_RESAMPLES, L.SEED,
                 b["n_sessions"], b["level_a"], b["n"], b["level_b"], b["n_b"]))
        else:
            f("\nDifference not computable: rising n=%d, falling n=%d.\n"
              % (len(rise), len(fall)))


def main():
    rows = load()
    f("# Atlas Study D2 — OI at the wall strike, band 0.15 %")
    f()
    f("Exploration. No verdict. Nothing here is a finding until confirmed once "
      "on unseen data.")
    f()
    f("D2 was absent from the main atlas document, which carries D1 only. This "
      "file adds it for band 0.15 % alone. The extraction ran **one query per "
      "approach leg** against `hist_option_bars_1m`, each scoped to one "
      "`trade_date`, one expiry, one strike, one option type and the window "
      "(approach_min − 30, approach_min]; `sql/extract_wall_oi_d2.sql`. "
      "79 legs queried, 0 failed, 0 timeouts.")
    f()
    f("Approaches before **09:45:59** are reported as **OPEN** and measured "
      "from the prior session's close, because a 30-minute pre-approach window "
      "would reach before the session start. Approaches at or after 09:45:59 "
      "are **INTRADAY**, measured over the 30 minutes before. The two are never "
      "pooled.")
    f()
    f("| Field | Value |")
    f("|---|---|")
    f("| Approach legs in the band | %d |" % len(rows))
    f("| OPEN (before 09:45:59) | %d |" % sum(1 for r in rows if r["regime"] == "OPEN"))
    f("| INTRADAY (09:45:59 or later) | %d |"
      % sum(1 for r in rows if r["regime"] == "INTRADAY"))
    f("| Legs with bars < 25 | %d — flagged, kept |"
      % sum(1 for r in rows if r.get("bars", 99) < 25))
    f("| Edge-flagged legs | %d |" % sum(1 for r in rows if r["edge"]))
    f("| Legs on an expiry-flagged session | %d |"
      % sum(1 for r in rows if r["expiry_flag"]))
    f("| Intervals | session-clustered percentile bootstrap, %d resamples, "
      "seed %d. **Descriptive** |" % (L.B_RESAMPLES, L.SEED))
    f()
    f("---")
    for regime in ("OPEN", "INTRADAY"):
        for oi in ("dF", "dF1"):
            table(rows, regime, oi)
    f()
    f("---")
    f()
    f("*Exploration. No verdict. Read-only; the only database access was the "
      "79-leg extraction. No new query was made for the OPEN regime.*")
    with open(OUT, "w") as fh:
        fh.write("\n".join(LINES) + "\n")
    with open(os.path.join(HERE, "data", "d2_rows_%s.csv" % BAND), "w", newline="") as fh:
        keys = sorted({k for r in rows for k in r})
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("legs: %d (OPEN %d, INTRADAY %d)"
          % (len(rows), sum(1 for r in rows if r["regime"] == "OPEN"),
             sum(1 for r in rows if r["regime"] == "INTRADAY")))
    print("wrote %s (%d lines)" % (OUT, len(LINES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
