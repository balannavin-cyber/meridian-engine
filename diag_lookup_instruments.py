"""
diag_lookup_instruments.py

Find the instrument_id -> symbol mapping. Looks for a table named
'instruments', 'spot_instruments', etc., and reverses the lookup. Falls
back to inferring from price magnitude if no instruments table exists.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

dotenv = Path(r"C:\GammaEnginePython\.env")
if dotenv.exists():
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from supabase import create_client
sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"],
)

OUT = Path(r"C:\GammaEnginePython\diagnostics\instrument_id_map.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
buf: list[str] = []
def out(s: str = "") -> None:
    buf.append(s); print(s, flush=True)

UUIDS = [
    "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
    "9992f600-51b3-4009-b487-f878692a0bc5",
]

# ---- 1. Try common instruments-table names ----
out("[1] Probing instruments-table candidates")
out("-" * 60)
candidate_tables = [
    "instruments", "spot_instruments", "instrument", "symbols",
    "underlyings", "instrument_master",
]
hit_table = None
for t in candidate_tables:
    try:
        r = sb.table(t).select("*").limit(1).execute()
        out(f"  FOUND TABLE: {t} (sample row keys: {sorted(r.data[0].keys()) if r.data else '<empty>'})")
        if not hit_table:
            hit_table = t
    except Exception as e:
        msg = str(e)[:80]
        out(f"  {t:30s} -> not found ({msg})")

# ---- 2. If we found an instruments table, look up our UUIDs ----
if hit_table:
    out(f"\n[2] Looking up UUIDs in '{hit_table}'")
    out("-" * 60)
    for u in UUIDS:
        try:
            r = sb.table(hit_table).select("*").eq("id", u).execute()
            if r.data:
                out(f"\n  {u}:")
                for k, v in r.data[0].items():
                    out(f"    {k:30s} = {v!r}")
            else:
                out(f"\n  {u}: <not found by id, trying instrument_id column>")
                r2 = sb.table(hit_table).select("*").eq("instrument_id", u).execute()
                if r2.data:
                    for k, v in r2.data[0].items():
                        out(f"    {k:30s} = {v!r}")
                else:
                    out(f"    <not found in {hit_table} under id or instrument_id>")
        except Exception as e:
            out(f"  {u}: lookup failed: {e}")

# ---- 3. Fallback: infer from price magnitude ----
out("\n[3] Price-magnitude fingerprint (sanity, regardless of table found)")
out("-" * 60)
out("(NIFTY trades ~22,000-25,000; SENSEX ~75,000-82,000 currently)")
for u in UUIDS:
    try:
        r = (sb.table("hist_spot_bars_1m")
             .select("close,trade_date")
             .eq("instrument_id", u)
             .order("trade_date", desc=True)
             .limit(5)
             .execute())
        if r.data:
            samples = [(row["trade_date"], row["close"]) for row in r.data]
            avg_close = sum(s[1] for s in samples) / len(samples)
            label = "NIFTY" if avg_close < 50000 else "SENSEX"
            out(f"  {u} -> avg recent close {avg_close:,.1f} -> {label}")
            for d, c in samples:
                out(f"      {d}  close={c:,.2f}")
    except Exception as e:
        out(f"  {u}: {e}")

OUT.write_text("\n".join(buf), encoding="utf-8")
out(f"\n[written to: {OUT}]")
