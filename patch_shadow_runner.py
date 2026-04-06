import re
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "run_merdian_shadow_runner.py"

NEW_FUNC = '''
def write_cycle_status_to_supabase(cycle_ok: bool, breadth_coverage, per_symbol: dict, last_error: str = "") -> None:
    try:
        import json as _json
        supabase_url = os.environ.get("SUPABASE_URL", "").strip()
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not supabase_url or not supabase_key:
            return
        payload_value = _json.dumps({
            "cycle_ok": cycle_ok,
            "breadth_coverage": breadth_coverage,
            "per_symbol": per_symbol,
            "last_error": last_error,
            "cycle_time_ist": now_ist().strftime("%Y-%m-%d %H:%M:%S IST"),
        })
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }
        payload = {
            "config_key": "aws_shadow_cycle_status",
            "config_value": payload_value,
            "updated_at": "now()",
            "updated_by": "aws_shadow_runner",
        }
        requests.post(
            f"{supabase_url}/rest/v1/system_config",
            headers=headers,
            json=payload,
            timeout=10,
        )
    except Exception as e:
        log(f"WARNING: Failed to write cycle status to Supabase (non-fatal): {e}")

'''

content = TARGET.read_text(encoding="utf-8")

if "write_cycle_status_to_supabase" in content:
    print("Patch already applied.")
else:
    content = content.replace("def run_cycle() -> bool:", NEW_FUNC + "def run_cycle() -> bool:")

    old_end = '''    if overall_ok:
        log(f"END   AWS SHADOW CYCLE OK in {duration:.1f}s | {per_symbol}")
    else:
        log(f"END   AWS SHADOW CYCLE WITH FAILURES in {duration:.1f}s | {per_symbol}")

    return overall_ok'''

    new_end = '''    if overall_ok:
        log(f"END   AWS SHADOW CYCLE OK in {duration:.1f}s | {per_symbol}")
    else:
        log(f"END   AWS SHADOW CYCLE WITH FAILURES in {duration:.1f}s | {per_symbol}")

    write_cycle_status_to_supabase(
        cycle_ok=overall_ok,
        breadth_coverage=coverage_pct,
        per_symbol=per_symbol,
        last_error="" if overall_ok else f"Cycle failed. per_symbol={per_symbol}",
    )

    return overall_ok'''

    if old_end in content:
        content = content.replace(old_end, new_end)
        TARGET.write_text(content, encoding="utf-8")
        print("Patch applied successfully.")
    else:
        print("ERROR: Could not find insertion point.")
