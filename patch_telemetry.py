import sys

path = r'C:\GammaEnginePython\gamma_engine_telemetry_logger.py'
content = open(path, encoding='utf-8').read()
original_length = len(content)

# ── Change 1: add imports ──────────────────────────────────────────────────
ANCHOR1 = 'from gamma_engine_heartbeat import mark_component_error, mark_component_ok, mark_component_warn'
if ANCHOR1 not in content:
    print("FAIL: Change 1 anchor not found"); sys.exit(1)
content = content.replace(
    ANCHOR1,
    ANCHOR1 + '\nimport os\nfrom dotenv import load_dotenv',
    1
)
print("Change 1 applied")

# ── Change 2: insert freshness function before run_once ────────────────────
ANCHOR2 = 'def run_once('
if ANCHOR2 not in content:
    print("FAIL: Change 2 anchor not found"); sys.exit(1)

FRESHNESS_FN = '''
def check_table_freshness():
    """Query Supabase for latest ts on core tables. Returns freshness report."""
    try:
        load_dotenv(dotenv_path=BASE_DIR / ".env")
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not supabase_url or not supabase_key:
            return {"error": "Missing Supabase credentials"}
        import urllib.request
        headers = {
            "apikey": supabase_key,
            "Authorization": "Bearer " + supabase_key,
        }
        tables = {
            "signal_snapshots": "created_at",
            "market_state_snapshots": "ts",
            "gamma_metrics": "ts",
            "volatility_snapshots": "ts",
        }
        now_utc = datetime.now(timezone.utc)
        results = {}
        for table, ts_col in tables.items():
            url = (supabase_url + "/rest/v1/" + table
                   + "?select=" + ts_col
                   + "&order=" + ts_col + ".desc&limit=1")
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    if data and isinstance(data, list) and data[0].get(ts_col):
                        ts_str = data[0][ts_col]
                        ts_clean = ts_str[:26].replace(" ", "T").replace("Z", "+00:00")
                        if "+" not in ts_clean[10:]:
                            ts_clean += "+00:00"
                        ts = datetime.fromisoformat(ts_clean)
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        lag = int((now_utc - ts).total_seconds())
                        results[table] = {
                            "latest_ts": ts_str,
                            "lag_seconds": lag,
                            "stale": lag > 600,
                        }
                    else:
                        results[table] = {"latest_ts": None, "lag_seconds": None, "stale": True}
            except Exception as e:
                results[table] = {"error": str(e), "stale": True}
        any_stale = any(v.get("stale") for v in results.values())
        return {"tables": results, "any_stale": any_stale}
    except Exception as e:
        return {"error": str(e)}


'''

content = content.replace(ANCHOR2, FRESHNESS_FN + ANCHOR2, 1)
print("Change 2 applied")

# ── Change 3: call freshness inside run_once ───────────────────────────────
ANCHOR3 = '    persist_snapshot(snapshot, max_snapshots)\n\n    hb_status = "OK" if result["returncode"] == 0 else "ERROR"'
if ANCHOR3 not in content:
    print("FAIL: Change 3 anchor not found")
    # show what's around persist_snapshot to help debug
    idx = content.find('    persist_snapshot(snapshot, max_snapshots)')
    print("Context around persist_snapshot:")
    print(repr(content[idx:idx+120]))
    sys.exit(1)

content = content.replace(
    ANCHOR3,
    '''    persist_snapshot(snapshot, max_snapshots)

    freshness = check_table_freshness()
    snapshot["table_freshness"] = freshness

    hb_status = "OK" if result["returncode"] == 0 else "ERROR"
    if freshness.get("any_stale") and hb_status == "OK":
        hb_status = "WARN"''',
    1
)
print("Change 3 applied")

open(path, 'w', encoding='utf-8').write(content)
print("File written. Original length:", original_length, "New length:", len(content))
print("SUCCESS - all 3 changes applied")
