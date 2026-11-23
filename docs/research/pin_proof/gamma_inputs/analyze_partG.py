import json
from collections import Counter, defaultdict
G1=[];G2=[]
for l in open('_partG_raw.txt'):
    l=l.rstrip('\n')
    if not l: continue
    sym,day,tag,payload=l.split('|',3)
    (G1 if tag=='G1' else G2).append(json.loads(payload))
print("=== G1 exact-minute coverage in historical_index_futures_1m ===")
print("sym|minutes|exact_hit|exact_miss|miss_but_nearest_hit|nearest_off_sec_nonzero")
for sym in ("NIFTY","SENSEX"):
    v=[r for r in G1 if r['sym']==sym]
    hit=sum(1 for r in v if r['exact_hit']); miss=len(v)-hit
    mn=sum(1 for r in v if not r['exact_hit'] and r.get('nearest_off_sec') is not None)
    onz=sum(1 for r in v if r.get('nearest_off_sec') not in (None,0,0.0))
    print(f"{sym}|{len(v)}|{hit}|{miss}|{mn}|{onz}")
print()
print("=== G2 whole-day presence (tells 'no rows at the minute' from 'no rows at all') ===")
print("sym|days|days_with_rows|days_zero_rows|total_rows|days_any_null_expiry|days_any_null_ltp")
for sym in ("NIFTY","SENSEX"):
    v=[r for r in G2 if r['sym']==sym]
    wr=[r for r in v if r['rows_in_day']>0]
    print(f"{sym}|{len(v)}|{len(wr)}|{len(v)-len(wr)}|{sum(r['rows_in_day'] for r in v)}|"
          f"{sum(1 for r in wr if r['rows_null_expiry']>0)}|{sum(1 for r in wr if r['rows_null_ltp']>0)}")
print()
print("=== per-day detail ===")
print("sym|day|rows_in_day|distinct_expiries|min_expiry|null_expiry|null_ltp|first_clock|last_clock")
for r in G2:
    print(f"{r['sym']}|{r['d']}|{r['rows_in_day']}|{r['distinct_expiries']}|{r['min_expiry']}|"
          f"{r['rows_null_expiry']}|{r['rows_null_ltp']}|{r['first_clock']}|{r['last_clock']}")
print()
print("=== sample G1 rows with a hit ===")
for r in [x for x in G1 if x['exact_hit']][:6]:
    print(f"  {r['sym']} {r['d']} {r['tname']} exp={r['nearest_expiry']} ltp={r['nearest_ltp']} "
          f"stored_basis={r['nearest_stored_basis']} src={r['nearest_source']} off={r['nearest_off_sec']}")
