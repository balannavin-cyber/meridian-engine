from pathlib import Path

path = Path(__file__).resolve().parent / "run_merdian_shadow_runner.py"
content = path.read_text()

old = """    stale_ok, stale_msg, latest_ltp_ts = guard_ltp_staleness()
    if not stale_ok:
        log(f"GUARD 4 STOP: {stale_msg}")
        update_state(
            "ERROR",
            {
                "failed_guard": "staleness",
                "guard_message": stale_msg,
                "latest_equity_intraday_ts": latest_ltp_ts,
            },
        )
        return False"""

new = """    # Guard 4 (LTP staleness) skipped on AWS shadow.
    # AWS shadow does not maintain equity_intraday_last.
    # Local is the single source of LTP data — it writes to Supabase.
    latest_ltp_ts = None
    log("GUARD 4: LTP staleness check skipped on AWS shadow (Local is the LTP source)")"""

if old in content:
    content = content.replace(old, new)
    path.write_text(content)
    print("Guard 4 patch applied successfully.")
else:
    print("ERROR: pattern not found")
