"""
experiment_49_apr_only_ict_replication.py

EXPERIMENT 49 — Apr 2026 Out-of-Sample Replication of Exp 15

Question:
    Does the Exp 15 framework's edge (full-year +193.4% return, BEAR_OB 92% /
    BULL_OB 84% / MEDIUM 77%) hold in the most recent month (April 2026)?

Approach (per CLAUDE.md anti-pattern rule):
    Run experiment_15_pure_ict_compounding.py AS-IS, scoped to 2026-04-01 ..
    2026-04-30. Do NOT re-implement the methodology.

Two run modes:
    Mode A — Wrapper (preferred): import experiment_15_pure_ict_compounding as
             a module and override its date range constants. Fastest, zero
             chance of methodology drift.
    Mode B — Patch (fallback): if the existing script is not importable, this
             script prints exact line numbers / sed-style edits to apply, the
             user runs the original, then this script consumes the output for
             comparison.

Decision rule:
    PASS  : Apr WR within 5pp of full-year AND EV positive
    MARGINAL : WR within 10pp
    FAIL  : EV negative OR WR drops >10pp

Output:
    Apr-only run results + comparison table vs full-year baseline.

Author: Session 15 batch.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

# === Configuration ===
APR_START = "2026-04-01"
APR_END = "2026-04-30"

# Full-year baseline numbers from Exp 15 re-run (Session 10, 2026-04-27).
# Source: CURRENT.md / MERDIAN_Experiment_Compendium_v1.md "Exp 15 re-validation"
FULL_YEAR_BASELINE = {
    "BEAR_OB":   {"WR": 92.0, "N": 25,  "Total": 364273},
    "BULL_OB":   {"WR": 83.7, "N": 49,  "Total": 379016},
    "BULL_FVG":  {"WR": 50.3, "N": 155, "Total": 30153},
    "MEDIUM":    {"WR": 77.3, "N": 22,  "Total": 260993},
    "HIGH":      {"WR": 41.2, "N": 17,  "Total": 56421},
    "LOW":       {"WR": 62.1, "N": 190, "Total": 456028},
}


def find_existing_script() -> Path | None:
    """Search for experiment_15_pure_ict_compounding.py in common locations."""
    candidates = [
        Path.cwd() / "experiment_15_pure_ict_compounding.py",
        Path.cwd().parent / "experiment_15_pure_ict_compounding.py",
        # If run from MERDIAN root or research/ dir
        Path.cwd() / "research" / "experiment_15_pure_ict_compounding.py",
    ]
    # Walk up parents up to 3 levels looking for the file
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


def mode_b_instructions(script_path: Path | None):
    print("=" * 76)
    print("MODE B — MANUAL PATCH INSTRUCTIONS")
    print("=" * 76)
    if script_path is None:
        print("Could not find experiment_15_pure_ict_compounding.py.")
        print("Locate it manually in your repo, then apply the date scope:")
    else:
        print(f"Found: {script_path}")
        print()
        print("Apply the date scope:")
    print()
    print("  1. Open experiment_15_pure_ict_compounding.py")
    print("  2. Find the date range constants (typically near the top, may be named")
    print(f"     START_DATE, END_DATE, BACKTEST_START, etc.)")
    print(f"  3. Set them to: '{APR_START}' and '{APR_END}'")
    print("  4. Run the script normally, save the output to a file, e.g.:")
    print(f"       python experiment_15_pure_ict_compounding.py > exp49_apr_only.txt")
    print()
    print("  5. Run THIS script in compare-only mode against the saved output:")
    print(f"       python {Path(__file__).name} --compare exp49_apr_only.txt")
    print()
    print("(The compare mode parses the standard Exp 15 output table and prints the")
    print("delta vs the full-year baseline embedded in this script.)")


def parse_exp15_output(text: str) -> dict:
    """Parse the standard Exp 15 output. Tries to find lines like:
       BEAR_OB | 25 | 92.0% | ...
    or section headers labelled 'By pattern' / 'By MTF context' followed by tables.
    Returns dict[label] = {WR, N, Total} where label is BULL_OB, BEAR_OB, BULL_FVG,
    MEDIUM, HIGH, LOW.
    """
    out: dict[str, dict] = {}
    targets = ("BEAR_OB", "BULL_OB", "BULL_FVG", "MEDIUM", "HIGH", "LOW")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Try to find a target label and at least an N + WR
        for t in targets:
            if t in line.split():
                # naive parse: split by | or whitespace
                tokens = [x.strip() for x in line.replace("|", " ").split() if x.strip()]
                # Expect tokens that include t, then numbers
                try:
                    idx = tokens.index(t)
                    rest = tokens[idx + 1:]
                except ValueError:
                    continue
                # Find first int (N) and first percentage (WR)
                n = None
                wr = None
                total = None
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
                    # Try to grab a "₹+nnn" or signed integer for total
                    if total is None:
                        s = r.replace("₹", "").replace(",", "").replace("+", "")
                        try:
                            total = int(s)
                        except ValueError:
                            pass
                if n is not None and wr is not None:
                    out[t] = {"WR": wr, "N": n, "Total": total or 0}
                    break
    return out


def compare(apr_results: dict, baseline: dict):
    print("=" * 76)
    print("EXPERIMENT 49 — APR 2026 vs FULL-YEAR BASELINE")
    print("=" * 76)
    print(f"{'Bucket':<10} {'Apr N':>7} {'Apr WR':>8} {'FY WR':>8} "
          f"{'WR delta':>10} {'Apr Total':>12} {'Verdict':<14}")
    print("-" * 76)
    overall_verdict = "PASS"
    for label in ("BEAR_OB", "BULL_OB", "BULL_FVG", "MEDIUM", "HIGH", "LOW"):
        a = apr_results.get(label)
        b = baseline.get(label, {})
        if not a:
            print(f"{label:<10} {'-':>7} {'-':>8} {b.get('WR','-'):>8} "
                  f"{'-':>10} {'-':>12} {'NO DATA':<14}")
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
              f"{wr_delta:>+9.1f}pp {a['Total']:>+12,d} {verdict:<14}")
    print("-" * 76)
    print(f"OVERALL VERDICT: {overall_verdict}")
    print()
    print("Decision rule recap:")
    print("  PASS    : every bucket WR within 5pp of full-year AND positive total")
    print("  MARGINAL: any bucket within 10pp")
    print("  FAIL    : any bucket with WR drop >10pp OR negative total")
    print("=" * 76)


def try_mode_a():
    """Attempt to import experiment_15_pure_ict_compounding and rerun with Apr scope.
    Returns (success: bool, results: dict | None)."""
    script_path = find_existing_script()
    if script_path is None:
        return False, None
    sys.path.insert(0, str(script_path.parent))
    spec = importlib.util.spec_from_file_location("experiment_15_pure_ict_compounding",
                                                   script_path)
    if spec is None or spec.loader is None:
        return False, None
    print(f"[MODE A] importing {script_path}")
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"[MODE A] import failed: {e}")
        print(f"[MODE A] falling back to MODE B")
        return False, None
    # Try to find a date-range entry point
    candidates_attr = ["START_DATE", "BACKTEST_START", "DATE_FROM", "FROM_DATE"]
    end_attrs = ["END_DATE", "BACKTEST_END", "DATE_TO", "TO_DATE"]
    s_attr = next((a for a in candidates_attr if hasattr(mod, a)), None)
    e_attr = next((a for a in end_attrs if hasattr(mod, a)), None)
    if not (s_attr and e_attr):
        print("[MODE A] could not locate date constants on module. "
              "Looked for: " + ", ".join(candidates_attr + end_attrs))
        print("[MODE A] falling back to MODE B")
        return False, None
    print(f"[MODE A] overriding {s_attr}={APR_START!r}, {e_attr}={APR_END!r}")
    setattr(mod, s_attr, APR_START)
    setattr(mod, e_attr, APR_END)
    # Look for a main / run entry point
    entry = None
    for name in ("main", "run", "run_experiment"):
        if hasattr(mod, name) and callable(getattr(mod, name)):
            entry = getattr(mod, name)
            break
    if entry is None:
        print("[MODE A] no main/run entrypoint. Cannot drive Mode A.")
        return False, None
    print("[MODE A] invoking entry point ...")
    # Capture stdout
    import io
    import contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            entry()
    except SystemExit:
        pass
    except Exception as e:
        print(f"[MODE A] entry raised: {e}")
        return False, None
    output = buf.getvalue()
    # Echo it so the user sees the run
    print(output)
    parsed = parse_exp15_output(output)
    if not parsed:
        print("[MODE A] could not parse output; manual comparison may be needed.")
        return False, None
    return True, parsed


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

    print("=" * 76)
    print("EXPERIMENT 49 — APR 2026 OUT-OF-SAMPLE EXP 15 REPLICATION")
    print("=" * 76)
    print(f"Apr scope: {APR_START} .. {APR_END}")
    print()

    ok, results = try_mode_a()
    if ok and results:
        compare(results, FULL_YEAR_BASELINE)
    else:
        mode_b_instructions(find_existing_script())


if __name__ == "__main__":
    main()
