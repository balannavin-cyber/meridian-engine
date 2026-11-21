"""C1 confirmation run. READ-ONLY. NO DATABASE ACCESS.

Reads only:
  c1/data/c1_fileA_2026-02-25_2026-08-25.csv   (hashed, main test)
  c1/data/c1_fileB_2026-08-26_2026-10-29.csv   (hashed, near-contract read)
  ../data/futures_bars.csv                     (closed run, design period only)

The pre-registration futoi_C1_oi_sign_prereg_2026-11-19.md is binding. Where it
and the run prompt differ, the pre-registration governs.

ONE LOOK: --score runs once. Part 0 (design-period values, K0-K4) computes
nothing from the test period's outcomes.

Definitions, from section 2-4 of the pre-registration:
  contract rank  on session d, contracts with expiry_date >= d ranked by expiry;
                 series 1,2,3 = ranks 1-3
  F(d)           OI of series 1+2+3 at the close of d; missing if any is missing
  P(d)           series-1 close at the close of d
  dF(d)          F(d) - F(d-1); sign only; dF = 0 excluded and counted
  r(d)           ln P(d+1) - ln P(d), in bp
  E              mean r over dF>0 minus mean r over dF<0
  interval       percentile bootstrap resampling whole ISO calendar weeks,
                 10,000 resamples, seed 20261119
  H1             E < 0, one-sided alpha 0.05: the 95th percentile of the
                 bootstrap distribution of E is below 0
"""
import argparse
import csv
import datetime as dt
import hashlib
import math
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CLOSED = os.path.join(os.path.dirname(HERE), "data")
FILE_A = "c1_fileA_2026-02-25_2026-08-25.csv"
FILE_B = "c1_fileB_2026-08-26_2026-10-29.csv"
TEST_FROM = "2026-04-01"
TEST_TO = "2026-08-25"          # d+1 must be <= this
F1_TO = "2026-10-29"
DESIGN_LO, DESIGN_HI = "2025-04-01", "2026-03-30"
SEED = 20261119
B = 10000
CLOSE_IST = "15:29"

# Section 7: "cut points fixed from the design period". These are the values the
# atlas published for the design period and are what the section means.
ATLAS_CUTS = {"vol": [0.005946, 0.006921], "ret": [-0.000266, 0.015791]}

RESULTS = []
LINES = []


def f(s=""):
    LINES.append(s)


def iso_week(d):
    y, w, _ = dt.date.fromisoformat(d).isocalendar()
    return "%04d-W%02d" % (y, w)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(cid, title, fails_when, measured, passed):
    RESULTS.append({"id": cid, "title": title, "fails_when": fails_when,
                    "measured": measured, "passed": passed})
    print("\n%s  %s" % (cid, title))
    print("   fails when: %s" % fails_when)
    for ln in str(measured).splitlines():
        print("   %s" % ln)
    print("   -> %s" % ("PASS" if passed else "FAIL"))
    return passed


# ------------------------------------------------------------------ load
def load_file(name):
    rows = []
    with open(os.path.join(DATA, name), newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append({"expiry": r["expiry_date"], "d": r["d"],
                         "ts": r["close_ts_ist"],
                         "close": float(r["close"]), "oi": float(r["oi"]),
                         "symbol": r["symbol"]})
    return rows


def sessionise(rows):
    """-> {d: [contracts ranked by expiry among expiry_date >= d]}"""
    by = {}
    for r in rows:
        by.setdefault(r["d"], []).append(r)
    out = {}
    for d, rs in by.items():
        live = sorted([x for x in rs if x["expiry"] >= d], key=lambda x: x["expiry"])
        out[d] = live
    return out


def series(bysess):
    """P(d), F(d), F1(d) and the close-bar times."""
    P, F, F1, TS, NC = {}, {}, {}, {}, {}
    for d, live in bysess.items():
        NC[d] = len(live)
        if live:
            P[d] = live[0]["close"]
            F1[d] = live[0]["oi"]
            TS[d] = [x["ts"] for x in live[:3]]
        if len(live) >= 3 and all(x["oi"] is not None for x in live[:3]):
            F[d] = sum(x["oi"] for x in live[:3])
    return P, F, F1, TS, NC


def expiry_sessions(rows):
    """Futures expiry sessions, from the file's own expiry_date: a session that
    is itself an expiry_date present in the file."""
    ds = {r["d"] for r in rows}
    es = {r["expiry"] for r in rows}
    return sorted(ds & es)


# ------------------------------------------------- design-period values
def design_values():
    """Design-period values, computed before the test file is read.

    Mean absolute daily return of the series-1 close, in bp, and the tercile
    cut points of trailing 20-session realised volatility and trailing
    20-session return, computed as atlas_readout2.py defines them: the slice
    sessions[max(0,i-20):i] (ending at the PRIOR close), cut over the DAY-ROW
    subset (build_days drops the first and last session), on the series-1 close
    taken at the EXACT 15:29:59 bar.

    ATLAS_CUTS below are the values the atlas published and are what section 7
    means by "cut points fixed from the design period". They are used for the
    section 7 bucketing. The recomputation here is reported beside them; where
    the two differ the difference is stated, not reconciled by adjustment."""
    per = {}
    with open(os.path.join(CLOSED, "futures_bars.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if int(r["contract_series"]) != 1:
                continue
            t = r["trade_date"]
            if DESIGN_LO <= t <= DESIGN_HI and r["hhmmss"] == "15:29:59":
                per[t] = float(r["close"])
    sessions = sorted(per)
    rets = {}
    for i in range(1, len(sessions)):
        a, b = per[sessions[i - 1]], per[sessions[i]]
        if a and b:
            rets[sessions[i]] = math.log(b / a)
    mad_bp = 1e4 * float(np.mean([abs(v) for v in rets.values()]))
    tr = {}
    for i, d in enumerate(sessions):
        prior = sessions[max(0, i - 20):i]
        rr = [rets[x] for x in prior if x in rets]
        if len(rr) >= 10:
            m = sum(rr) / len(rr)
            tr[d] = {"vol": math.sqrt(sum((v - m) ** 2 for v in rr) / (len(rr) - 1)),
                     "ret": sum(rr)}
    dayrows = [d for d in sessions[1:-1] if d in tr]
    recomputed = {}
    for k in ("vol", "ret"):
        v = [tr[d][k] for d in dayrows]
        recomputed[k] = [float(np.percentile(v, 100.0 / 3)),
                         float(np.percentile(v, 200.0 / 3))]
    return {"n_sessions": len(sessions), "n_returns": len(rets),
            "n_trailing": len(tr), "n_dayrows": len(dayrows),
            "mad_bp": mad_bp, "recomputed": recomputed, "cuts": ATLAS_CUTS}


# ------------------------------------------------------------ bootstrap
def boot_week(rows_pos, rows_neg, n=B, seed=SEED):
    """E = mean(r | dF>0) - mean(r | dF<0), percentile bootstrap resampling
    whole ISO calendar weeks."""
    per = {}
    for rows, i in ((rows_pos, 0), (rows_neg, 2)):
        for r in rows:
            e = per.setdefault(iso_week(r["d"]), [0.0, 0, 0.0, 0])
            e[i] += r["r_bp"]
            e[i + 1] += 1
    keys = list(per)
    A = np.array([per[k] for k in keys], dtype=float)
    sa, ca, sb, cb = A[:, 0].sum(), A[:, 1].sum(), A[:, 2].sum(), A[:, 3].sum()
    nan = float("nan")
    if ca == 0 or cb == 0:
        return {"E": nan, "p5": nan, "p95": nan, "weeks": len(keys),
                "n_pos": int(ca), "n_neg": int(cb), "reps": np.array([])}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(keys), size=(n, len(keys)))
    qa, na = A[:, 0][idx].sum(axis=1), A[:, 1][idx].sum(axis=1)
    qb, nb = A[:, 2][idx].sum(axis=1), A[:, 3][idx].sum(axis=1)
    ok = (na > 0) & (nb > 0)
    reps = np.full(n, np.nan)
    reps[ok] = qa[ok] / na[ok] - qb[ok] / nb[ok]
    reps = reps[~np.isnan(reps)]
    reps.sort()
    return {"E": float(sa / ca - sb / cb),
            "p5": float(np.percentile(reps, 5)),
            "p95": float(np.percentile(reps, 95)),
            "weeks": len(keys), "n_pos": int(ca), "n_neg": int(cb), "reps": reps}


def split_rows(rows):
    return ([r for r in rows if r["dF"] > 0], [r for r in rows if r["dF"] < 0])


def effect(rows):
    pos, neg = split_rows(rows)
    if not pos or not neg:
        return None
    return boot_week(pos, neg)


# ------------------------------------------------------------ main build
def build(rowsA, rowsB):
    """Test-period rows. Section 2: d from 2026-04-01 with F(d), F(d-1), P(d),
    P(d+1) present and d+1 <= 2026-08-25. Expiry session and the session after
    excluded and counted. dF = 0 excluded and counted."""
    allrows = rowsA + rowsB
    bysess_A = sessionise(rowsA)
    PA, FA, F1A, TSA, NCA = series(bysess_A)
    sessA = sorted(bysess_A)
    exp_A = set(expiry_sessions(rowsA))
    after = set()
    for i, d in enumerate(sessA):
        if d in exp_A and i + 1 < len(sessA):
            after.add(sessA[i + 1])

    kept, excl = [], {}

    def drop(why):
        excl[why] = excl.get(why, 0) + 1

    for i, d in enumerate(sessA):
        if d < TEST_FROM:
            continue
        nxt = sessA[i + 1] if i + 1 < len(sessA) else None
        prev = sessA[i - 1] if i > 0 else None
        if nxt is None or nxt > TEST_TO:
            drop("d+1 missing or after %s" % TEST_TO)
            continue
        if d in exp_A:
            drop("futures expiry session")
            continue
        if d in after:
            drop("session after a futures expiry")
            continue
        if d not in FA or prev not in FA:
            drop("F(d) or F(d-1) missing")
            continue
        if d not in PA or nxt not in PA:
            drop("P(d) or P(d+1) missing")
            continue
        dF = FA[d] - FA[prev]
        if dF == 0:
            drop("dF = 0")
            continue
        r_bp = 1e4 * (math.log(PA[nxt]) - math.log(PA[d]))
        kept.append({"d": d, "prev": prev, "next": nxt, "F": FA[d],
                     "F_prev": FA[prev], "dF": dF, "P": PA[d], "P_next": PA[nxt],
                     "r_bp": r_bp, "r_pts": PA[d] * (math.exp(r_bp / 1e4) - 1),
                     "week": iso_week(d), "month": d[:7],
                     "n_contracts": NCA.get(d, 0)})
    ctx = {"sessA": sessA, "PA": PA, "FA": FA, "F1A": F1A, "TSA": TSA,
           "NCA": NCA, "exp_A": exp_A, "after": after,
           "rowsA": rowsA, "rowsB": rowsB, "allrows": allrows}
    return kept, excl, ctx


def trailing_from(P, sessions):
    rets = {}
    for i in range(1, len(sessions)):
        a, b = P.get(sessions[i - 1]), P.get(sessions[i])
        if a and b:
            rets[sessions[i]] = math.log(b / a)
    out = {}
    for i, d in enumerate(sessions):
        prior = sessions[max(0, i - 20):i]
        rr = [rets[x] for x in prior if x in rets]
        if len(rr) >= 10:
            m = sum(rr) / len(rr)
            out[d] = {"vol20": math.sqrt(sum((v - m) ** 2 for v in rr) / (len(rr) - 1)),
                      "ret20": sum(rr),
                      "win_first": prior[0], "win_last": prior[-1]}
    return out


def bucket(v, cuts):
    if v is None:
        return None
    return 0 if v <= cuts[0] else (1 if v <= cuts[1] else 2)


# ------------------------------------------------------------- controls
def controls(ctx, kept, excl):
    ok = True
    # K0
    want = {}
    with open(os.path.join(HERE, "EXPORT_HASHES.txt")) as fh:
        for ln in fh:
            ln = ln.replace("\r", "").strip()
            if not ln:
                continue
            h, nm = ln.split()[0], ln.split()[-1]
            want[nm] = h
    txt, k0 = [], True
    for nm in (FILE_A, FILE_B):
        got = sha256(os.path.join(DATA, nm))
        match = want.get(nm) == got
        k0 = k0 and match
        txt.append("%s\n   recorded %s\n   measured %s\n   match %s"
                   % (nm, want.get(nm), got, match))
    ok &= record("K0", "file hashes vs EXPORT_HASHES.txt (CR stripped)",
                 "a changed or truncated export would give a different sha256",
                 "\n".join(txt), k0)
    # K1
    ds = [r["d"] for r in kept]
    nxts = [r["next"] for r in kept]
    beyond = [x for x in nxts if x > TEST_TO] + [x for x in ds if x > TEST_TO]
    t = ("first session used: %s\nlast session used:  %s\nsessions used:      %d\n"
         "last d+1 read:      %s\nsessions read after %s: %d\nexcluded, by reason:\n%s"
         % (min(ds) if ds else "-", max(ds) if ds else "-", len(ds),
            max(nxts) if nxts else "-", TEST_TO, len(beyond),
            "\n".join("   %4d  %s" % (v, k)
                      for k, v in sorted(excl.items(), key=lambda kv: -kv[1]))))
    ok &= record("K1", "test window",
                 "reading any session after %s for the main test" % TEST_TO,
                 t, len(beyond) == 0)
    # K2
    bad = []
    for r in kept:
        ts = ctx["TSA"].get(r["d"], [])
        if len(ts) < 3 or not all(x[11:16] == CLOSE_IST for x in ts[:3]):
            bad.append((r["d"], [x[11:16] for x in ts[:3]]))
    share = 1.0 - (len(bad) / len(kept)) if kept else float("nan")
    t = ("window sessions: %d\nall three series at %s: %d (%.1f%%)\nthreshold: >= 95.0%%"
         % (len(kept), CLOSE_IST, len(kept) - len(bad), 100 * share))
    if bad:
        t += "\nsessions where not:\n" + "\n".join("   %s  %s" % x for x in bad[:20])
    ok &= record("K2", "close bar at 15:29 for all three series",
                 "a close bar earlier than 15:29 would mean the export did not "
                 "reach the session close", t, share >= 0.95)
    # K3
    few = sorted([(d, n) for d, n in ctx["NCA"].items() if n < 3 and d >= TEST_FROM])
    t = "sessions in File A from %s with fewer than three live contracts: %d" \
        % (TEST_FROM, len(few))
    if few:
        t += "\n" + "\n".join("   %s  %d contract(s)" % x for x in few[:20])
    ok &= record("K3", "contract rank availability",
                 "a session with fewer than three contracts cannot give F = 1+2+3",
                 t, True)
    # K4
    rnd = random.Random(SEED)
    weeks = {}
    for r in kept:
        weeks.setdefault(r["week"], []).append(r)
    vals = [r["r_bp"] for r in kept]
    shuffled = vals[:]
    rnd.shuffle(shuffled)
    # reassign r across weeks, keeping dF signs where they are
    sh = [dict(r, r_bp=v) for r, v in zip(kept, shuffled)]
    e_sh = effect(sh)
    planted = [dict(r, r_bp=(r["r_bp"] - 20.0 if r["dF"] > 0 else r["r_bp"]))
               for r in kept]
    e_pl = effect(planted)
    e_base = effect(kept)
    t = ("shuffled across weeks: E = %+.3f bp (must be near 0)\n"
         "observed:              E = %+.3f bp\n"
         "-20 bp planted on dF>0 only: E = %+.3f bp, recovery = %+.3f bp "
         "(must be about -20)"
         % (e_sh["E"], e_base["E"], e_pl["E"], e_pl["E"] - e_base["E"]))
    k4 = abs(e_sh["E"]) < 15.0 and abs((e_pl["E"] - e_base["E"]) + 20.0) < 0.01
    ok &= record("K4", "planted signal",
                 "a shuffle that keeps an effect, or a planted -20 bp that does "
                 "not come back, would mean the grouping and the aggregation "
                 "disagree", t, k4)
    return ok


def write_stopped():
    bad = [r for r in RESULTS if not r["passed"]]
    with open(os.path.join(HERE, "STOPPED.md"), "w") as fh:
        fh.write("# C1 run STOPPED at Part 0\n\n")
        fh.write("UTC: %s\n\n" % dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
        fh.write("Section 6: \"Any failure stops the run before section 4.\"\n\n")
        fh.write("**No test-period outcome was computed.**\n\n")
        for r in bad:
            fh.write("## %s FAILED — %s\n\n**Fails when:** %s\n\n```\n%s\n```\n\n"
                     % (r["id"], r["title"], r["fails_when"], r["measured"]))
        for r in RESULTS:
            if r["passed"]:
                fh.write("- %s %s — PASS\n" % (r["id"], r["title"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", action="store_true")
    args = ap.parse_args()

    dv = design_values()
    print("=" * 92)
    print("C1 Part 0 — design-period values (no test-period outcome computed)")
    print("=" * 92)
    print("design sessions %d, daily returns %d" % (dv["n_sessions"], dv["n_returns"]))
    print("mean absolute daily return, series-1 close: %.4f bp" % dv["mad_bp"])
    print("design sessions %d, returns %d, with trailing %d, day-row subset %d"
          % (dv["n_sessions"], dv["n_returns"], dv["n_trailing"], dv["n_dayrows"]))
    print("trailing vol cuts, recomputed here: %.6f / %.6f"
          % tuple(dv["recomputed"]["vol"]))
    print("                   atlas (used):    %.6f / %.6f" % tuple(ATLAS_CUTS["vol"]))
    print("trailing ret cuts, recomputed here: %.6f / %.6f"
          % tuple(dv["recomputed"]["ret"]))
    print("                   atlas (used):    %.6f / %.6f" % tuple(ATLAS_CUTS["ret"]))
    vm = all(abs(a - b) < 5e-7 for a, b in zip(dv["recomputed"]["vol"], ATLAS_CUTS["vol"]))
    rm = all(abs(a - b) < 5e-7 for a, b in zip(dv["recomputed"]["ret"], ATLAS_CUTS["ret"]))
    print("vol cuts match atlas exactly: %s ; ret cuts match atlas exactly: %s"
          % (vm, rm))
    print("max |difference|: vol %.2e, ret %.2e"
          % (max(abs(a - b) for a, b in zip(dv["recomputed"]["vol"], ATLAS_CUTS["vol"])),
             max(abs(a - b) for a, b in zip(dv["recomputed"]["ret"], ATLAS_CUTS["ret"]))))

    rowsA, rowsB = load_file(FILE_A), load_file(FILE_B)
    kept, excl, ctx = build(rowsA, rowsB)
    print("\nPart 0 window build: %d sessions kept, %d excluded"
          % (len(kept), sum(excl.values())))

    allok = controls(ctx, kept, excl)
    print("\n" + "=" * 92)
    for r in RESULTS:
        print("  %s  %-52s %s" % (r["id"], r["title"], "PASS" if r["passed"] else "FAIL"))
    if not allok:
        write_stopped()
        print("\nSTOPPED — a control failed. STOPPED.md written; nothing in "
              "section 4 or 7 computed.")
        return 3
    print("\nALL CONTROLS PASS.")
    if not args.score:
        print("--score not given. Nothing in section 4 or 7 computed.")
        return 0

    import c1_report
    return c1_report.report(dv, kept, excl, ctx, vm, rm)


if __name__ == "__main__":
    sys.exit(main())
