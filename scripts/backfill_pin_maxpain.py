import os, sys, time, datetime as dt, urllib.request, json
URL = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/rpc/backfill_pin_maxpain_runs"
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}

PAGE_LIMIT = 20
MAX_CALLS = 30

def call(sym, ts_from, ts_to):
    body = json.dumps({"p_symbol": sym, "p_ts_from": ts_from, "p_ts_to": ts_to,
                       "p_limit": PAGE_LIMIT}).encode()
    req = urllib.request.Request(URL, data=body, headers=H, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())

start = dt.date(2026, 5, 25); end = dt.date(2026, 9, 18)
days = [start + dt.timedelta(d) for d in range((end - start).days + 1)]
days = [d for d in days if d.weekday() < 5]
print(f"{len(days)} weekdays x 2 symbols", flush=True)
for d in reversed(days):
    ts_from = dt.datetime.combine(d - dt.timedelta(days=1), dt.time(18, 30), dt.timezone.utc).isoformat()
    ts_to = dt.datetime.combine(d, dt.time(18, 30), dt.timezone.utc).isoformat()
    for sym in ("NIFTY", "SENSEX"):
        total = 0; calls = 0
        for page in range(1, MAX_CALLS + 1):
            n = None
            for attempt in (1, 2, 3):
                try:
                    t0 = time.time(); n = call(sym, ts_from, ts_to); el = time.time() - t0
                    print(f"{d} {sym} call{page} inserted={n} {el:.1f}s", flush=True); break
                except Exception as e:
                    _read = getattr(e, "read", None)
                    try:
                        body = _read().decode("utf-8", "replace").strip() if _read else ""
                    except Exception:
                        body = ""
                    print(f"{d} {sym} attempt{attempt} FAIL {type(e).__name__}: {e}"
                          + (f" | {body}" if body else ""), flush=True)
                    time.sleep(5 * attempt)
            else:
                print(f"{d} {sym} GAVE UP", flush=True)
                break
            calls += 1
            if not isinstance(n, int):
                print(f"{d} {sym} call{page} UNEXPECTED RETURN {type(n).__name__}={n!r} -- stopping symbol-day", flush=True)
                break
            total += n
            if n == 0:
                break
            time.sleep(0.3)
        else:
            print(f"{d} {sym} HIT CALL CAP {MAX_CALLS} -- may be incomplete", flush=True)
        print(f"{d} {sym} TOTAL inserted={total} calls={calls}", flush=True)
        time.sleep(0.3)
print("done", flush=True)
