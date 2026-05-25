#!/usr/bin/env python3
"""
fix_enh86_winrate_redesign_v1.py
Patch merdian_signal_dashboard.py to implement ENH-86 v1:
  Add EV and N columns to the WIN RATE legend table.

Scope (v1):
  - Extend WIN_RATES tuples from 5 fields to 7 (add ev, n).
  - Update legend_rows() to emit two new <td> cells per row.
  - Update legend table header in card() to add <th>EV</th> and <th>N</th>.
  - Add two NEW rows at top of WIN_RATES for live E4/E5 edges.

Deferred to v2:
  - BLOCKED/ALLOWED visual prominence redesign.
  - SIGNAL QUALITY block in card body.

Idempotency guard: aborts if "ENH-86" marker already present.
Rule 5: ast.parse() validation before write.
Encoding: utf-8-sig read, utf-8 write, CRLF auto-detect.

Run from C:\\GammaEnginePython:
  python fix_enh86_winrate_redesign_v1.py [--dry-run]
"""
import ast
import pathlib
import sys

TARGET = pathlib.Path(r"C:\GammaEnginePython\merdian_signal_dashboard.py")

# ─────────────────────────────────────────────────────────────────────────────
# Anchor 1: existing WIN_RATES list (entire block, including closing bracket)
# ─────────────────────────────────────────────────────────────────────────────
ANCHOR1 = '''WIN_RATES = [
    ("BEAR_OB",   "MORNING (09:15-11:30)",    100.0, "TIER1", ""),
    ("BULL_OB",   "MORNING (09:15-11:30)",    100.0, "TIER1", ""),
    ("BULL_OB",   "DTE=0",                    100.0, "TIER1", "+107.4% exp"),
    ("BULL_OB",   "AFTERNOON (13:00-15:00)",  100.0, "TIER1", "+75.3% exp"),
    ("BULL_FVG",  "HIGH ctx + DTE=0",          87.5, "TIER1", "+58.9% exp"),
    ("JUDAS_BULL","confirm at T+15m",           83.3, "TIER2", ""),
    ("BEAR_OB",   "MOM_YES filter",             83.0, "TIER2", "+21.6pp lift"),
    ("BULL_OB",   "MOM_YES filter",             80.0, "TIER2", ""),
    ("JUDAS_BULL","unconfluenced",              69.0, "TIER3", ""),
    ("BULL_FVG",  "SHORT_GAMMA + BULLISH",      65.0, "TIER2", ""),
    ("BULL_FVG",  "NO confluence (ICT only)",   50.3, "TIER3", "MIN SIZE"),
    ("BEAR_OB",   "AFTERNOON 13:00-14:30",      17.0, "SKIP",  "HARD SKIP"),
]'''

REPLACE1 = '''# ENH-86 v1: extended to 7-tuples (pat, cond, wr, tier, note, ev, n).
# `ev` is a string (units vary: "+pts" for live edges from Exp 41B,
# "+x.x%" for option-return expectancy from Exp 2/8). None where the
# compendium does not give a clean source number.
# `n` is sample size (int) or None where unclear.
# Source experiments cited inline. Update when experiments rerun.
WIN_RATES = [
    # E4/E5 LIVE edges — Exp 41B (point-EV, corrected scale)
    ("BEAR_OB",   "MIDDAY + PO3_BEARISH (LIVE)",   88.2, "TIER1", "ENH-76",       "+116.5pts", 17),
    ("BULL_OB",   "AFT + PO3_BULL SENSEX (LIVE)",  73.7, "TIER1", "ENH-77",       "+35.5pts",  19),
    # Established static rules — Exp 2/6/8 (option-return EV)
    ("BEAR_OB",   "MORNING (09:15-11:30)",    100.0, "TIER1", "Exp 8",         "+81.2%",   9),
    ("BULL_OB",   "MORNING (09:15-11:30)",    100.0, "TIER1", "",              None,       None),
    ("BULL_OB",   "DTE=0",                    100.0, "TIER1", "Exp 2 \\u00a73", "+121.4%",  20),
    ("BULL_OB",   "AFTERNOON (13:00-15:00)",  100.0, "TIER1", "ENH-40",        "+75.3%",   None),
    ("BULL_FVG",  "HIGH ctx + DTE=0",          87.5, "TIER1", "Exp 6",         "+58.9%",   12),
    ("JUDAS_BULL","confirm at T+15m",          83.3, "TIER2", "Exp 2c v2",     None,       None),
    ("BEAR_OB",   "MOM_YES filter",             83.0, "TIER2", "Exp 8",         "+56.1%",  23),
    ("BULL_OB",   "MOM_YES filter",             80.0, "TIER2", "Exp 8 lift",    "+64.9%",  None),
    ("JUDAS_BULL","unconfluenced",              69.0, "TIER3", "",              None,       None),
    ("BULL_FVG",  "SHORT_GAMMA + BULLISH",      65.0, "TIER2", "",              None,       None),
    ("BULL_FVG",  "NO confluence (ICT only)",   50.3, "TIER3", "MIN SIZE",      None,       None),
    ("BEAR_OB",   "AFTERNOON 13:00-14:30",      17.0, "SKIP",  "HARD SKIP",     "-24.7%",   None),
]'''

# ─────────────────────────────────────────────────────────────────────────────
# Anchor 2: existing legend_rows() function body
# Replaces the 5-tuple unpack and emits 2 new <td> cells per row.
# Header (5 -> 7 columns) is updated in anchor 3.
# ─────────────────────────────────────────────────────────────────────────────
ANCHOR2 = '''def legend_rows(pat):
    if not pat or pat in ("NONE","NO DATA","ERROR"):
        return '<tr><td colspan="5" class="no-pat">No active ICT pattern this cycle</td></tr>'
    rows = [r for r in WIN_RATES if r[0]==pat]
    if not rows:
        return f'<tr><td colspan="5" class="no-pat">No WR data for {pat}</td></tr>'
    out = []
    for p,cond,wr,tier,note in rows:
        tc  = tier_col(tier)
        wrc = "wg" if wr>=80 else "wa" if wr>=60 else "wr" if wr>=30 else "ws"
        out.append(
            f'<tr><td class="lp">{p}</td><td>{cond}</td>'
            f'<td class="wc {wrc}">{wr:.0f}%</td>'
            f'<td><span class="pill sm" style="border-color:{tc};color:{tc}">{tier}</span></td>'
            f'<td class="nt">{note}</td></tr>'
        )
    return "\\n".join(out)'''

REPLACE2 = '''def legend_rows(pat):
    # ENH-86 v1: colspan and unpack updated for 7-col table (added EV, N).
    if not pat or pat in ("NONE","NO DATA","ERROR"):
        return '<tr><td colspan="7" class="no-pat">No active ICT pattern this cycle</td></tr>'
    rows = [r for r in WIN_RATES if r[0]==pat]
    if not rows:
        return f'<tr><td colspan="7" class="no-pat">No WR data for {pat}</td></tr>'
    out = []
    for p,cond,wr,tier,note,ev,n in rows:
        tc  = tier_col(tier)
        wrc = "wg" if wr>=80 else "wa" if wr>=60 else "wr" if wr>=30 else "ws"
        ev_cell = ev if ev else "\\u2014"
        n_cell  = str(n) if n is not None else "\\u2014"
        out.append(
            f'<tr><td class="lp">{p}</td><td>{cond}</td>'
            f'<td class="wc {wrc}">{wr:.0f}%</td>'
            f'<td class="wc">{ev_cell}</td>'
            f'<td class="nt">{n_cell}</td>'
            f'<td><span class="pill sm" style="border-color:{tc};color:{tc}">{tier}</span></td>'
            f'<td class="nt">{note}</td></tr>'
        )
    return "\\n".join(out)'''

# ─────────────────────────────────────────────────────────────────────────────
# Anchor 3: <thead> in card() WIN RATE table — add EV and N columns
# Inside an f-string: must match exact whitespace/quoting.
# ─────────────────────────────────────────────────────────────────────────────
ANCHOR3 = '<table class="wt2"><thead><tr><th>Pattern</th><th>Condition</th><th>WR</th><th>Tier</th><th>Note</th></tr></thead>'
REPLACE3 = '<table class="wt2"><thead><tr><th>Pattern</th><th>Condition</th><th>WR</th><th>EV</th><th>N</th><th>Tier</th><th>Note</th></tr></thead>'


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 1

    src = TARGET.read_bytes().decode("utf-8-sig")
    eol = "\r\n" if "\r\n" in src else "\n"
    print(f"Line ending detected: {'CRLF' if eol == chr(13)+chr(10) else 'LF'}")

    if "ENH-86" in src:
        print("ERROR: ENH-86 marker already present -- aborting (idempotent guard).")
        return 1

    # Normalise our anchors and replacements to the file's EOL
    a1 = ANCHOR1.replace("\n", eol)
    r1 = REPLACE1.replace("\n", eol)
    a2 = ANCHOR2.replace("\n", eol)
    r2 = REPLACE2.replace("\n", eol)
    # ANCHOR3/REPLACE3 are single-line, no eol normalisation needed

    for label, anchor in [("anchor1 (WIN_RATES)", a1),
                          ("anchor2 (legend_rows)", a2),
                          ("anchor3 (legend thead)", ANCHOR3)]:
        c = src.count(anchor)
        if c == 0:
            print(f"ERROR: {label} not found", file=sys.stderr)
            print(f"  First 200 chars of expected anchor:\n  {anchor[:200]!r}",
                  file=sys.stderr)
            return 1
        if c != 1:
            print(f"ERROR: {label} found {c} times (expected 1)", file=sys.stderr)
            return 1

    patched = src.replace(a1, r1)
    patched = patched.replace(a2, r2)
    patched = patched.replace(ANCHOR3, REPLACE3)

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"ERROR: ast.parse failed after patch: {e}", file=sys.stderr)
        return 1

    print("ast.parse: PASS")

    if dry_run:
        print("[DRY-RUN] No file written.")
        print("\nAnchor 1 (WIN_RATES) -> 7-tuple form, +2 new LIVE rows at top")
        print("Anchor 2 (legend_rows) -> 7-tuple unpack, emits EV + N <td> cells")
        print("Anchor 3 (legend thead) -> 5 cols -> 7 cols (added EV, N)")
        return 0

    TARGET.write_bytes(patched.encode("utf-8"))
    print(f"ENH-86 v1 patch applied to: {TARGET.name}")
    print(f"  WIN_RATES extended to 7-tuples + 2 new LIVE rows")
    print(f"  legend_rows() emits EV and N <td> cells")
    print(f"  legend table header now has 7 columns (Pattern|Condition|WR|EV|N|Tier|Note)")
    print(f"  Idempotency key: 'ENH-86'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
