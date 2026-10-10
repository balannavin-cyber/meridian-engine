"""P1c — gamma regime -> realised range. Scorer, pre-registered with
docs/research/s94_priority/P1c_regime_range_prereg_2026-10-10.md.

Usage: python3 -I p1c_score.py <P1 part2_extract json> <p1c_regime csv>
Standard library only. Exits non-zero on any failed assertion.
"""
import csv, json, math, random, sys

SEED, B = 20261010, 10_000
N_EXPECT = {"NIFTY": 85, "SENSEX": 84}          # P1 Part 1b, asserted by P1's own scorer
CAL_EXPECT = {"NIFTY": 56, "SENSEX": 56}
MIN_GROUP = 8                                    # §5: below this a group mean is not tested
SIG_TOL = 1e-3   # §3: P1 exports sigma_d round(,2) (~3e-5 rel) and iv0 to 0.01 (~5e-4 rel); a wrong formula is >=20%
PRIMARY = "NIFTY"


def hms(s):
    """HH:MM:SS of a timestamp or a bare time. P1 exports ats_ist time-only ('09:15:35');
    the session date is matched by the (symbol, session_date) join key, so the time is what is compared."""
    t = str(s).replace("T", " ").split(" ")[-1]
    return t.split(".")[0][:8]


def boot_ci(a, b, rng, lo=2.5, hi=97.5):
    """Percentile CI of mean(a) - mean(b), resampling within each group."""
    diffs = []
    for _ in range(B):
        ra = [a[rng.randrange(len(a))] for _ in a]
        rb = [b[rng.randrange(len(b))] for _ in b]
        diffs.append(sum(ra) / len(ra) - sum(rb) / len(rb))
    diffs.sort()
    return diffs[int(B * lo / 100)], diffs[min(B - 1, int(B * hi / 100))]


def mean(x):
    return sum(x) / len(x) if x else float("nan")


def main(p1_json, regime_csv):
    p1 = [r for r in json.load(open(p1_json, encoding="utf-8")) if r["anchor"] == "t0"]
    reg = {(r["symbol"], r["session_date"]): r for r in csv.DictReader(open(regime_csv, encoding="utf-8"))}

    sess = {}
    for sym in N_EXPECT:
        rows = sorted((r for r in p1 if r["symbol"] == sym), key=lambda r: r["session_date"])
        assert len(rows) == N_EXPECT[sym], f"{sym}: P1 t0 sessions {len(rows)} != {N_EXPECT[sym]}"
        cal = [r for r in rows if int(r["sess_ix"]) <= int(r["n_cal"])]
        assert len(cal) == CAL_EXPECT[sym], f"{sym}: calibration {len(cal)} != {CAL_EXPECT[sym]}"
        out = []
        for r in rows:
            k = (sym, r["session_date"])
            assert k in reg, f"{k}: no predictor row"
            g = reg[k]
            assert len(hms(r["ats_ist"])) == 8 and hms(g["t0_ist"]) == hms(r["ats_ist"]), f"{k}: t0 {g['t0_ist']} != P1 {r['ats_ist']}"
            assert r["sigma_d"] is not None and r["hi"] is not None and r["lo"] is not None, f"{k}: missing sigma_d/hi/lo"
            s0, iv0, sd = float(r["s0"]), float(r["iv0"]), float(r["sigma_d"])
            exp_sd = s0 * iv0 / 100 * math.sqrt(1 / 252)
            assert abs(sd - exp_sd) <= SIG_TOL * exp_sd, f"{k}: sigma_d {sd} != s0*iv0/100*sqrt(1/252) {exp_sd}"
            rng_sig = (float(r["hi"]) - float(r["lo"])) / sd
            out.append({"date": r["session_date"], "cal": int(r["sess_ix"]) <= int(r["n_cal"]),
                        "net": float(g["net_gex_cr"]), "hhi": float(g["hhi"]), "dte": int(r["dte"]),
                        "y": rng_sig})
        sess[sym] = out

    rng = random.Random(SEED)
    print(f"# P1c — γ regime → realised range\n\nseed {SEED} · {B} resamples · 95% percentile · outcome = (hi − lo)/sigma_d from P1's extract\n")
    verdict = None
    for sym in N_EXPECT:
        rows = sess[sym]
        med = sorted(r["hhi"] for r in rows if r["cal"])
        m = len(med); hhi_med = (med[m // 2] if m % 2 else (med[m // 2 - 1] + med[m // 2]) / 2)
        for r in rows:
            r["pp"] = r["net"] > 0 and r["hhi"] >= hhi_med
        tag = "PRIMARY" if sym == PRIMARY else "descriptive"
        print(f"## {sym} — {tag}\n\nHHI calibration median {hhi_med:.6f}\n")
        print("| half | n pinned-positive | n other | mean range σ (PP) | mean range σ (other) | e = other − PP | 95% CI |")
        print("|---|---:|---:|---:|---:|---:|---|")
        res = {}
        for half, flag in (("cal", True), ("hold", False)):
            pp = [r["y"] for r in rows if r["cal"] == flag and r["pp"]]
            ot = [r["y"] for r in rows if r["cal"] == flag and not r["pp"]]
            e = mean(ot) - mean(pp)
            ci = boot_ci(ot, pp, rng) if half == "hold" and len(pp) >= MIN_GROUP and len(ot) >= MIN_GROUP else None
            res[half] = (len(pp), len(ot), e, ci)
            cis = f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci else ("—" if half == "cal" else "not tested (group < 8)")
            print(f"| {half} | {len(pp)} | {len(ot)} | {mean(pp):.3f} | {mean(ot):.3f} | {e:.3f} | {cis} |")
        # descriptive strata
        print("\nDescriptive (all sessions): mean range σ by net γ sign and by DTE bucket")
        for lab, f in (("net γ > 0", lambda r: r["net"] > 0), ("net γ ≤ 0", lambda r: r["net"] <= 0),
                       ("DTE 0", lambda r: r["dte"] == 0), ("DTE 1", lambda r: r["dte"] == 1),
                       ("DTE 2–3", lambda r: 2 <= r["dte"] <= 3), ("DTE 4+", lambda r: r["dte"] >= 4)):
            ys = [r["y"] for r in rows if f(r)]
            print(f"- {lab}: n {len(ys)}, mean {mean(ys):.3f}")
        print()
        if sym == PRIMARY:
            npp, not_, eh, ci = res["hold"]
            ec = res["cal"][2]
            if ci is None:
                verdict = "INCONCLUSIVE (a holdout group has fewer than 8 sessions)"
            elif ec > 0 and ci[0] > 0 and eh >= 0.5 * ec:
                verdict = "YES — pinned-positive sessions show a smaller realised range (in σ) than other sessions"
            else:
                why = []
                if not ec > 0: why.append("calibration effect not positive")
                if not ci[0] > 0: why.append("holdout 95% CI includes 0")
                if not eh >= 0.5 * ec: why.append("holdout < half calibration")
                verdict = "NO — " + "; ".join(why)
    print(f"**Verdict (§5, {PRIMARY} only): {verdict}**")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
