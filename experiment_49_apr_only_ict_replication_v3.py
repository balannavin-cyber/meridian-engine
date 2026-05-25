"""
experiment_49_apr_only_ict_replication_v3.py

EXPERIMENT 49 v3 — Apr 2026 Out-of-Sample Replication of Exp 15

v3 changes vs v2:
    Extended date detection. v2 only matched ISO date string literals like
    `"2025-04-01"`. v3 also matches:
        - datetime(2025, 4, 1)        -> replaces year/month/day args
        - date(2025, 4, 1)            -> same
        - pd.Timestamp("2025-04-01")  -> already covered by ISO string
        - Timestamp("2025-04-01")     -> same
        - datetime.date(2025, 4, 1)   -> same as date(...)
    Reports all matches found before patching so user can verify.

Decision rule:
    PASS  : Apr WR within 5pp of full-year AND positive total
    MARGINAL : within 10pp
    FAIL  : WR drop >10pp OR negative total

Author: Session 15 batch v2.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from datetime import date as date_t
from pathlib import Path

APR_START = "2026-04-01"
APR_END = "2026-04-30"

FULL_YEAR_BASELINE = {
    "BEAR_OB":   {"WR": 92.0, "N": 25,  "Total": 364273},
    "BULL_OB":   {"WR": 83.7, "N": 49,  "Total": 379016},
    "BULL_FVG":  {"WR": 50.3, "N": 155, "Total": 30153},
    "MEDIUM":    {"WR": 77.3, "N": 22,  "Total": 260993},
    "HIGH":      {"WR": 41.2, "N": 17,  "Total": 56421},
    "LOW":       {"WR": 62.1, "N": 190, "Total": 456028},
}

# Quoted ISO date: '2025-04-01' or "2025-04-01"
ISO_RE = re.compile(r"""(['"])(\d{4})-(\d{2})-(\d{2})\1""")

# Constructor form: datetime(2025, 4, 1) or date(2025, 4, 1) or
# datetime.date(2025, 4, 1).  Allows whitespace/optional comma+more args.
CONSTRUCTOR_RE = re.compile(
    r"""\b(?:datetime\.date|datetime|date)\s*\(\s*(\d{4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)"""
)


def find_existing_script() -> Path | None:
    candidates = [Path.cwd() / "experiment_15_pure_ict_compounding.py"]
    p = Path.cwd()
    for _ in range(4):
        c = p / "experiment_15_pure_ict_compounding.py"
        if c.exists():
            candidates.append(c)
        p = p.parent
    for c in candidates:
        if c.exists():
            return c.resolve()
    return None


def find_all_dates(src: str):
    """Return list of (kind, match_obj_or_string, date_t) tuples sorted by date."""
    found = []
    for m in ISO_RE.finditer(src):
        try:
            d = date_t(int(m.group(2)), int(m.group(3)), int(m.group(4)))
            found.append(("iso", m, d))
        except ValueError:
            pass
    for m in CONSTRUCTOR_RE.finditer(src):
        try:
            d = date_t(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            found.append(("ctor", m, d))
        except ValueError:
            pass
    found.sort(key=lambda x: x[2])
    return found


def patch_source(src: str, target_start: str, target_end: str):
    found = find_all_dates(src)
    if len(found) < 2:
        return src, []
    # Earliest = lowest date, latest = highest date
    earliest_kind, earliest_m, earliest_d = found[0]
    latest_kind, latest_m, latest_d = found[-1]
    ts_year, ts_mon, ts_day = (int(x) for x in target_start.split("-"))
    te_year, te_mon, te_day = (int(x) for x in target_end.split("-"))

    # Build replacement strings per kind. Replace span by exact match.
    # Use (start, end, replacement) tuples then apply right-to-left.
    edits = []
    if earliest_kind == "iso":
        edits.append((earliest_m.start(), earliest_m.end(),
                      f"{earliest_m.group(1)}{target_start}{earliest_m.group(1)}"))
    else:  # ctor
        edits.append((earliest_m.start(), earliest_m.end(),
                      f"datetime({ts_year}, {ts_mon}, {ts_day})"))
    if latest_kind == "iso":
        edits.append((latest_m.start(), latest_m.end(),
                      f"{latest_m.group(1)}{target_end}{latest_m.group(1)}"))
    else:
        edits.append((latest_m.start(), latest_m.end(),
                      f"datetime({te_year}, {te_mon}, {te_day})"))
    edits.sort(key=lambda x: x[0], reverse=True)
    patched = src
    for st, en, rep in edits:
        patched = patched[:st] + rep + patched[en:]
    info = {
        "all_dates": [(k, m.group(0), d) for k, m, d in found],
        "earliest": (earliest_kind, earliest_m.group(0), earliest_d),
        "latest": (latest_kind, latest_m.group(0), latest_d),
        "edits": edits,
    }
    return patched, info


def parse_exp15_output(text: str) -> dict:
    out: dict[str, dict] = {}
    targets = ("BEAR_OB", "BULL_OB", "BULL_FVG", "MEDIUM", "HIGH", "LOW")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for t in targets:
            if t in line.split():
                tokens = [x.strip() for x in line.replace("|", " ").split() if x.strip()]
                try:
                    idx = tokens.index(t)
                    rest = tokens[idx + 1:]
                except ValueError:
                    continue
                n = wr = total = None
                for r in rest:
                    if n is None and r.isdigit():
                        n = int(r); continue
                    if wr is None and r.endswith("%"):
                        try:
                            wr = float(r.rstrip("%"))
                        except ValueError:
                            pass
                        continue
                    if total is None:
                        s = r.replace("\u20b9", "").replace(",", "").replace("+", "")
                        try:
                            total = int(s)
                        except ValueError:
                            pass
                if n is not None and wr is not None:
                    out[t] = {"WR": wr, "N": n, "Total": total or 0}
                    break
    return out


def compare(apr_results: dict, baseline: dict):
    print("=" * 78)
    print("EXP 49 — APR 2026 vs FULL-YEAR BASELINE")
    print("=" * 78)
    print(f"{'Bucket':<10} {'Apr N':>7} {'Apr WR':>8} {'FY WR':>8} "
          f"{'WR delta':>10} {'Apr Total':>14} {'Verdict':<14}")
    print("-" * 78)
    overall = "PASS"
    for label in ("BEAR_OB", "BULL_OB", "BULL_FVG", "MEDIUM", "HIGH", "LOW"):
        a = apr_results.get(label)
        b = baseline.get(label, {})
        if not a:
            print(f"{label:<10} {'-':>7} {'-':>8} {b.get('WR','-'):>8} "
                  f"{'-':>10} {'-':>14} {'NO DATA':<14}")
            continue
        wr_d = a["WR"] - b["WR"]
        v = "PASS"
        if a["Total"] < 0:
            v = "FAIL (EV-)"; overall = "FAIL"
        elif abs(wr_d) > 10:
            v = "FAIL (>10pp)"; overall = "FAIL"
        elif abs(wr_d) > 5:
            v = "MARGINAL"
            if overall == "PASS":
                overall = "MARGINAL"
        print(f"{label:<10} {a['N']:>7} {a['WR']:>7.1f}% {b['WR']:>7.1f}% "
              f"{wr_d:>+9.1f}pp {a['Total']:>+14,d} {v:<14}")
    print("-" * 78)
    print(f"OVERALL VERDICT: {overall}")
    print()


def run_patched(script_path: Path, target_start: str, target_end: str):
    src = script_path.read_text(encoding="utf-8")
    patched, info = patch_source(src, target_start, target_end)
    if not info:
        print(f"[FATAL] Found <2 date references (ISO strings or constructors) in")
        print(f"        {script_path}")
        print("        Manually inspect the script's backtest range and use:")
        print(f"        python {Path(__file__).name} --compare exp49_apr.txt")
        return None
    print(f"[INFO] All date references found in source ({len(info['all_dates'])}):")
    for kind, lit, d in info["all_dates"]:
        print(f"    [{kind}] {lit!r:>40}  -> {d}")
    print()
    print(f"[INFO] Earliest -> Apr_start: {info['earliest'][1]!r}  =>  Apr {target_start}")
    print(f"[INFO] Latest   -> Apr_end:   {info['latest'][1]!r}  =>  Apr {target_end}")
    span = (info["latest"][2] - info["earliest"][2]).days
    if span < 90:
        print(f"[WARN] earliest..latest span only {span} days. "
              f"Likely NOT a backtest range -- could be expiry refs etc.")
        print(f"[WARN] Output may be wrong. Check manually.")
    print()
    tmpdir = Path(tempfile.mkdtemp(prefix="exp49v3_"))
    tmpfile = tmpdir / "experiment_15_patched.py"
    tmpfile.write_bytes(patched.encode("utf-8"))
    print(f"[INFO] patched script: {tmpfile}")
    print(f"[INFO] running: python {tmpfile.name}")
    print("-" * 78)
    try:
        result = subprocess.run(
            [sys.executable, str(tmpfile)],
            cwd=str(script_path.parent),
            capture_output=True, text=True, timeout=900,
        )
    except subprocess.TimeoutExpired:
        print("[FATAL] timed out (15 min).")
        return None
    if result.returncode != 0:
        print(f"[FATAL] patched script exited {result.returncode}")
        print("--- STDOUT ---"); print(result.stdout)
        print("--- STDERR ---"); print(result.stderr)
        return None
    print(result.stdout)
    return result.stdout


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--compare":
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            text = f.read()
        parsed = parse_exp15_output(text)
        if not parsed:
            print("[FATAL] could not parse Exp 15 output. Inspect file format.")
            sys.exit(2)
        compare(parsed, FULL_YEAR_BASELINE)
        return

    print("=" * 78)
    print("EXPERIMENT 49 v3 — APR 2026 OUT-OF-SAMPLE EXP 15 REPLICATION")
    print("=" * 78)
    print(f"Apr scope: {APR_START} .. {APR_END}")
    print()

    sp = find_existing_script()
    if sp is None:
        print("[FATAL] could not find experiment_15_pure_ict_compounding.py")
        sys.exit(1)
    print(f"[INFO] using: {sp}")
    print()

    out = run_patched(sp, APR_START, APR_END)
    if out is None:
        print("[INFO] If you want to manually patch:")
        print(f"  1. Edit {sp}")
        print(f"  2. Set start to '{APR_START}', end to '{APR_END}'")
        print(f"  3. python experiment_15_pure_ict_compounding.py > exp49_apr.txt")
        print(f"  4. python {Path(__file__).name} --compare exp49_apr.txt")
        sys.exit(1)
    parsed = parse_exp15_output(out)
    if not parsed:
        print("[WARN] couldn't auto-parse output. Run --compare manually.")
        return
    compare(parsed, FULL_YEAR_BASELINE)


if __name__ == "__main__":
    main()
