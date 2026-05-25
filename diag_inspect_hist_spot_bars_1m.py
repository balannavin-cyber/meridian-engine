"""
diag_inspect_hist_spot_bars_1m.py
Schema inspector. Writes findings to stdout AND to
C:\\GammaEnginePython\\diagnostics\\schema_hist_spot_bars_1m.txt so we can
read them back even if a PowerShell pipe truncates.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

# ---- Load .env ----
dotenv = Path(r"C:\GammaEnginePython\.env")
if dotenv.exists():
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

try:
    from supabase import create_client
except ImportError:
    sys.exit("supabase-py not installed")

url = os.environ.get("SUPABASE_URL")
key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
       or os.environ.get("SUPABASE_KEY"))
if not url or not key:
    sys.exit("SUPABASE_URL or key missing in env")

sb = create_client(url, key)

OUT = Path(r"C:\GammaEnginePython\diagnostics\schema_hist_spot_bars_1m.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)

lines: list[str] = []
def out(s: str = "") -> None:
    lines.append(s)
    print(s, flush=True)

out("=" * 60)
out("SCHEMA INSPECTION: hist_spot_bars_1m")
out("=" * 60)

# ---- 1. One sample row ----
out("\n[1] Sample row + column names")
out("-" * 60)
try:
    r = sb.table("hist_spot_bars_1m").select("*").limit(1).execute()
    if r.data:
        cols = sorted(r.data[0].keys())
        out(f"COLUMN COUNT : {len(cols)}")
        out(f"COLUMNS      : {cols}")
        out("")
        out("SAMPLE ROW VALUES:")
        for k in cols:
            out(f"  {k:30s} = {r.data[0][k]!r}")
    else:
        out("(table is empty)")
except Exception as e:
    out(f"ERROR fetching sample row: {e}")

# ---- 2. Find symbol-like column ----
out("\n[2] Symbol-like column probe")
out("-" * 60)
candidates = ["symbol", "instrument_id", "instrument_symbol", "ticker",
              "underlying", "name", "asset", "instrument"]
found = []
try:
    if r.data:
        actual_cols = set(r.data[0].keys())
        for c in candidates:
            if c in actual_cols:
                found.append(c)
        out(f"Candidate columns present: {found if found else '<none>'}")
except Exception as e:
    out(f"ERROR: {e}")

# ---- 3. Distinct values for the symbol-ish column (if found) ----
if found:
    sym_col = found[0]
    out(f"\n[3] Distinct values in '{sym_col}' (sampled from recent 5000 rows)")
    out("-" * 60)
    try:
        r = (sb.table("hist_spot_bars_1m")
             .select(f"{sym_col},trade_date")
             .order("trade_date", desc=True)
             .limit(5000)
             .execute())
        rows = r.data or []
        distinct = sorted({row[sym_col] for row in rows if row.get(sym_col) is not None})
        out(f"DISTINCT {sym_col} VALUES: {distinct}")
        out(f"(from {len(rows)} sampled rows)")
        if rows:
            out(f"trade_date range in sample: "
                f"{min(r['trade_date'] for r in rows)}  ->  "
                f"{max(r['trade_date'] for r in rows)}")
    except Exception as e:
        out(f"ERROR: {e}")

# ---- 4. Date column probe ----
out("\n[4] Date / timestamp columns")
out("-" * 60)
date_candidates = ["trade_date", "bar_ts", "ts", "date", "created_at", "updated_at"]
try:
    if r.data:
        present = [c for c in date_candidates if c in actual_cols]
        out(f"Present date/ts columns: {present}")
except Exception as e:
    out(f"ERROR: {e}")

# ---- 5. Total row count ----
out("\n[5] Approximate row count (head request)")
out("-" * 60)
try:
    r = (sb.table("hist_spot_bars_1m")
         .select("*", count="exact")
         .limit(1)
         .execute())
    out(f"EXACT ROW COUNT: {r.count}")
except Exception as e:
    out(f"ERROR: {e}")

OUT.write_text("\n".join(lines), encoding="utf-8")
out(f"\n[written to: {OUT}]")
