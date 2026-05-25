"""
experiment_49_apr_only_ict_replication_v2.py

EXPERIMENT 49 v2 — Apr 2026 Out-of-Sample Replication of Exp 15

v2 changes vs v1:
    - Mode A no longer relies on named constants (START_DATE etc.). Instead,
      reads experiment_15_pure_ict_compounding.py as text, finds all ISO date
      string literals via regex, takes earliest + latest as the implied
      backtest range, replaces them with 2026-04-01 and 2026-04-30, writes a
      patched copy to a temp file, and runs that via subprocess.
    - Prints exactly what was replaced before running, so you can sanity-check.
    - If only one date or none is found, falls back to the same Mode B
      instructions as v1.
    - --compare mode unchanged: parse a saved Exp 15 output file and diff vs
      the embedded full-year baseline.

Decision rule:
    PASS  : Apr WR within 5pp of full-year AND positive total
    MARGINAL : within 10pp
    FAIL  : WR drop >10pp OR negative total

Author: Session 15 batch.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
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

DATE_LITERAL_RE = re.compile(r"""(['"])(\d{4}-\d{2}-\d{2})\1""")


def find_existing_script() -> Path | None:
    candidates = [
        Path.cwd() / "experiment_15_pure_ict_compounding.py",
        Path.cwd().parent / "experiment_15_pure_ict_compounding.py",
        Path.cwd() / "research" / "experiment_15_pure_ict_compounding.py",
    ]
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


def patch_source(src: str, target_start: str, target_end: str):
    """Find all ISO date string literals, replace earliest with target_start
    and latest with target_end. Returns (patched_src, [(old_start, new_start),
    (old_end, new_end)] or [] if not enough dates found)."""
    matches = DATE_LITERAL_RE.findall(src)
    dates = sorted(set(d for _, d in matches))
    if len(dates) < 2:
        return src, []
    earliest, latest = dates[0], dates[-1]
    # Replace each occurrence inside its quote
    def replace_quoted(text: str, old: str, new: str) -> str:
        pat = re.compile(rf"""(['"])({re.escape(old)})\1""")
        return pat.sub(rf"\1{new}\1", text)
    patched = replace_quoted(src, earliest, target_start)
    patched = replace_quoted(patched, latest, target_end)
    return patched, [(earliest, target_start), (latest, target_end), ("all_dates_found", dates)]


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
                        n = int(r)
                        continue
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
    print("EXPERIMENT 49 — APR 2026 vs FULL-YEAR BASELINE")
    print("=" * 78)
    print(f"{'Bucket':<10} {'Apr N':>7} {'Apr WR':>8} {'FY WR':>8} "
          f"{'WR delta':>10} {'Apr Total':>14} {'Verdict':<14}")
    print("-" * 78)
    overall_verdict = "PASS"
    for label in ("BEAR_OB", "BULL_OB", "BULL_FVG", "MEDIUM", "HIGH", "LOW"):
        a = apr_results.get(label)
        b = baseline.get(label, {})
        if not a:
            print(f"{label:<10} {'-':>7} {'-':>8} {b.get('WR','-'):>8} "
                  f"{'-':>10} {'-':>14} {'NO DATA':<14}")
            continue
        wr_delta = a["WR"] - b["WR"]
        verdict = "PASS"
        if a["Total"] < 0:
            verdict = "FAIL (EV-)"
            overall_verdict = "FAIL"
        elif abs(wr_delta) > 10:
            verdict = "FAIL (>10pp)"
            overall_verdict = "FAIL"
        elif abs(wr_delta) > 5:
            verdict = "MARGINAL"
            if overall_verdict == "PASS":
                overall_verdict = "MARGINAL"
        print(f"{label:<10} {a['N']:>7} {a['WR']:>7.1f}% {b['WR']:>7.1f}% "
              f"{wr_delta:>+9.1f}pp {a['Total']:>+14,d} {verdict:<14}")
    print("-" * 78)
    print(f"OVERALL VERDICT: {overall_verdict}")
    print()


def run_patched_script(script_path: Path, target_start: str, target_end: str) -> str | None:
    src = script_path.read_text(encoding="utf-8")
    patched, info = patch_source(src, target_start, target_end)
    if not info:
        print(f"[FATAL] Found <2 ISO date literals in {script_path.name}.")
        print(f"  Cannot infer backtest range.")
        return None

    (old_s, new_s), (old_e, new_e), _, *rest = info
    all_dates = info[2][1] if len(info) > 2 else []
    print(f"[INFO] All ISO date literals found: {all_dates}")
    print(f"[INFO] Earliest -> Apr_start: {old_s!r} -> {new_s!r}")
    print(f"[INFO] Latest   -> Apr_end:   {old_e!r} -> {new_e!r}")
    print()

    # Sanity check: dates should span a meaningful backtest window (>= 6 months)
    from datetime import datetime
    try:
        d_old_s = datetime.strptime(old_s, "%Y-%m-%d").date()
        d_old_e = datetime.strptime(old_e, "%Y-%m-%d").date()
        span_days = (d_old_e - d_old_s).days
        if span_days < 90:
            print(f"[WARN] earliest..latest span only {span_days} days. "
                  f"This may not be a backtest range (could be expiry calendar refs).")
            print("[WARN] If wrong dates were patched, the run will fail or produce "
                  "garbage — check Apr-only output against baseline carefully.")
            print()
    except ValueError:
        pass

    tmpdir = Path(tempfile.mkdtemp(prefix="exp49_"))
    tmpfile = tmpdir / "experiment_15_pure_ict_compounding_apr.py"
    tmpfile.write_bytes(patched.encode("utf-8"))
    print(f"[INFO] patched script written to: {tmpfile}")
    print(f"[INFO] running: python {tmpfile.name}")
    print("-" * 78)

    # Run it. Set cwd to original script's directory so any relative imports work.
    try:
        result = subprocess.run(
            [sys.executable, str(tmpfile)],
            cwd=str(script_path.parent),
            capture_output=True,
            text=True,
            timeout=900,  # 15 min
        )
    except subprocess.TimeoutExpired:
        print("[FATAL] patched script timed out after 15 min.")
        return None

    if result.returncode != 0:
        print(f"[FATAL] patched script exited {result.returncode}")
        print("--- STDOUT ---")
        print(result.stdout)
        print("--- STDERR ---")
        print(result.stderr)
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
    print("EXPERIMENT 49 v2 — APR 2026 OUT-OF-SAMPLE EXP 15 REPLICATION")
    print("=" * 78)
    print(f"Apr scope: {APR_START} .. {APR_END}")
    print()

    script_path = find_existing_script()
    if script_path is None:
        print("[FATAL] could not find experiment_15_pure_ict_compounding.py.")
        print("Place this script in same directory and rerun, or run with --compare:")
        print(f"  python {Path(__file__).name} --compare <output_file.txt>")
        sys.exit(1)

    print(f"[INFO] using existing script: {script_path}")
    print()

    output = run_patched_script(script_path, APR_START, APR_END)
    if output is None:
        print()
        print("[INFO] If the patched run failed and you want to manually patch instead:")
        print(f"  1. Open {script_path}")
        print(f"  2. Find the backtest start/end date strings and set them to:")
        print(f"     start = '{APR_START}', end = '{APR_END}'")
        print(f"  3. Run: python experiment_15_pure_ict_compounding.py > exp49_apr.txt")
        print(f"  4. Compare: python {Path(__file__).name} --compare exp49_apr.txt")
        sys.exit(1)

    parsed = parse_exp15_output(output)
    if not parsed:
        print("[WARN] could not auto-parse Apr-only output table. Output above is")
        print("       still valid; run --compare manually if you save it to a file.")
        return
    compare(parsed, FULL_YEAR_BASELINE)


if __name__ == "__main__":
    main()
