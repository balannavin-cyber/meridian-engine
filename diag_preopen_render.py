# Save as diag_preopen_render.py in C:\GammaEnginePython
import sys
sys.path.insert(0, r'C:\GammaEnginePython')
from merdian_live_dashboard import get_preopen_status, parse_ist_dt
import json

result = get_preopen_status()
print("get_preopen_status() returned:")
print(json.dumps(result, indent=2, default=str))
print()
print(f"captured: {result['captured']}")
print(f"count: {result['count']}")
print(f"rows: {result['rows']}")