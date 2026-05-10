# diag_preopen_render_v3.py
import sys
sys.path.insert(0, r'C:\GammaEnginePython')
from merdian_live_dashboard import sb_get
from urllib.parse import quote

# Method A: original (suspected broken) — raw + sign
rows_a = sb_get("market_spot_snapshots",
    "select=ts,spot,symbol&ts=gte.2026-05-08T00:00:00%2B00:00&order=ts.asc&limit=5")
print(f"Method A (URL-encoded +): {len(rows_a)} rows")
for r in rows_a:
    print(f"  {r}")

# Method B: Z suffix instead of +00:00
rows_b = sb_get("market_spot_snapshots",
    "select=ts,spot,symbol&ts=gte.2026-05-08T00:00:00Z&order=ts.asc&limit=5")
print(f"\nMethod B (Z suffix): {len(rows_b)} rows")
for r in rows_b:
    print(f"  {r}")

# Method C: original broken (raw +)
rows_c = sb_get("market_spot_snapshots",
    "select=ts,spot,symbol&ts=gte.2026-05-08T00:00:00+00:00&order=ts.asc&limit=5")
print(f"\nMethod C (raw +): {len(rows_c)} rows")
for r in rows_c:
    print(f"  {r}")