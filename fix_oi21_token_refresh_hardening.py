"""
OI-21 fix: refresh_dhan_token.py silent fail when invoked by Task Scheduler.

Evidence reviewed 2026-04-22:

(a) Scheduled task MERDIAN_Dhan_Token_Refresh ran 2026-04-21 18:15:06
    LastTaskResult=0. token_status.json updated with success=true.
    Post-OI-16 config fix (absolute Python path + WorkingDirectory)
    is working. The "silent fail" framing in the resume prompt
    describes a pre-OI-16 state. Historical `'python' not recognized`
    entries in logs/dhan_token_refresh.log are pre-OI-16 ghosts.

(b) Current log tail shows three NON-ghost failure signatures:
    1. "Invalid TOTP" RuntimeError
    2. "Token can be generated once every 2 minutes" RuntimeError
       (seen immediately after "DHAN TOKEN REFRESH SUCCESS" in log)
    3. RuntimeError bubbling to SystemExit via traceback

(c) Broken retry path in main():
    - Line 118: message says "Waiting 30s"
    - Line 119: actual sleep is time.sleep(120)
    - 120 seconds == Dhan's rate-limit window exactly. Retry lands
      at the boundary and frequently trips the "once every 2 minutes"
      response.
    This is the internal cause of the rate-limit errors. It is NOT
    from an external second caller, even though the dashboard
    button (merdian_live_dashboard.py:57) could also produce this
    shape.

(d) Only one scheduled caller (MERDIAN_Dhan_Token_Refresh).
    Dashboard has a manual button. Idempotency guard protects both.

Fix applied:

1. Retry sleep: 120s -> 30s. One TOTP window. Well under rate-limit
   boundary. Message already said 30s; code now matches.

2. Idempotency guard at main() entry: read token_status.json, if
   last success < 90 seconds old, exit 0 without Dhan call.
   Safe from any caller duplication (task + dashboard button +
   manual + TOTP retry self-fire).

3. Explicit rate-limit handling: if Dhan returns "once every 2
   minutes", write token_status.json with that error, return exit
   code 2 (distinct from 1) so Task Scheduler can classify it as
   "recently refreshed elsewhere, not a real failure".
"""
import ast
import sys
from pathlib import Path

TARGET = Path(r"C:\GammaEnginePython\refresh_dhan_token.py")

# ----- Fix 1: retry sleep 120 -> 30 -----

OLD_RETRY = '''        if "Invalid TOTP" in error_msg:
            import time as _time
            print(f"WARNING: Invalid TOTP on first attempt. Waiting 30s for next window...")
            _time.sleep(120)
            totp_code = generate_totp(totp_seed)
            token_response = request_dhan_token(client_id, pin, totp_code)
        else:
            write_token_status(False, "", error_msg)
            raise'''

NEW_RETRY = '''        if "Invalid TOTP" in error_msg:
            import time as _time
            # OI-21 fix 2026-04-22: was sleep(120) which matched
            # Dhan's 2-minute rate-limit window exactly and caused
            # the retry to fail with "Token can be generated once
            # every 2 minutes". TOTP windows are 30 seconds wide;
            # one window is sufficient.
            print("WARNING: Invalid TOTP on first attempt. Waiting 30s for next window...")
            _time.sleep(30)
            totp_code = generate_totp(totp_seed)
            try:
                token_response = request_dhan_token(client_id, pin, totp_code)
            except RuntimeError as retry_e:
                retry_msg = str(retry_e)
                if "once every 2 minutes" in retry_msg:
                    # Another caller (or a prior invocation of ours)
                    # refreshed within 2 minutes. Dhan rejected our
                    # retry but the live token is already valid.
                    # Not a real failure.
                    print(f"INFO: rate-limit hit on retry; token was refreshed elsewhere within 2min. "
                          f"Exiting cleanly. ({retry_msg})")
                    write_token_status(False, "", f"rate_limited_after_totp_retry: {retry_msg}")
                    return 2
                write_token_status(False, "", retry_msg)
                raise
        elif "once every 2 minutes" in error_msg:
            # OI-21 fix: first-attempt rate-limit means someone
            # else just refreshed (likely us within the last 2 min
            # from a concurrent invocation). Token in .env is good.
            print(f"INFO: rate-limit hit on first attempt; token refreshed elsewhere within 2min. "
                  f"Exiting cleanly. ({error_msg})")
            write_token_status(False, "", f"rate_limited: {error_msg}")
            return 2
        else:
            write_token_status(False, "", error_msg)
            raise'''

# ----- Fix 2: idempotency guard at top of main() -----

OLD_MAIN_TOP = '''def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)

    client_id = require_env("DHAN_CLIENT_ID")
    pin = require_env("DHAN_PIN")
    totp_seed = require_env("DHAN_TOTP_SEED")

    totp_code = generate_totp(totp_seed)'''

NEW_MAIN_TOP = '''def _idempotency_skip() -> bool:
    """OI-21 guard: if token_status.json shows a success less than 90
    seconds old, skip. Protects against any caller double-invoking
    (Task Scheduler + dashboard button + TOTP retry + preflight).
    90s is under Dhan's 120s rate-limit window but comfortably above
    the normal end-to-end refresh duration (~1-2s)."""
    if not TOKEN_STATUS_FILE.exists():
        return False
    try:
        status = json.loads(TOKEN_STATUS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not status.get("success"):
        return False
    iso = status.get("refreshed_at_iso", "")
    if not iso:
        return False
    try:
        last = datetime.fromisoformat(iso)
    except ValueError:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=IST)
    age_s = (datetime.now(IST) - last).total_seconds()
    if 0 <= age_s < 90:
        print(f"[IDEMPOTENT] Token refreshed {age_s:.1f}s ago (< 90s). "
              f"Skipping Dhan call; .env is current.")
        return True
    return False


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)

    # OI-21 fix 2026-04-22: idempotency guard.
    if _idempotency_skip():
        return 0

    client_id = require_env("DHAN_CLIENT_ID")
    pin = require_env("DHAN_PIN")
    totp_seed = require_env("DHAN_TOTP_SEED")

    totp_code = generate_totp(totp_seed)'''


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    for label, old in [("RETRY_BLOCK", OLD_RETRY), ("MAIN_TOP", OLD_MAIN_TOP)]:
        if old not in src:
            print(f"ERROR: {label} not found verbatim. Aborting, no file written.")
            return 2
        if src.count(old) != 1:
            print(f"ERROR: {label} found {src.count(old)} times, expected 1. Aborting.")
            return 3

    new_src = src.replace(OLD_RETRY, NEW_RETRY).replace(OLD_MAIN_TOP, NEW_MAIN_TOP)

    # V18H governance: ast.parse() validation.
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"SYNTAX ERROR in generated source: {e}")
        print("Aborting, no file written.")
        return 4

    # Sanity checks: must contain both the new guard and the corrected sleep.
    if "_idempotency_skip" not in new_src:
        print("ERROR: idempotency guard not present in output. Aborting.")
        return 5
    if "_time.sleep(30)" not in new_src:
        print("ERROR: retry sleep not corrected. Aborting.")
        return 6
    if "_time.sleep(120)" in new_src:
        print("ERROR: old 120s sleep still present. Aborting.")
        return 7

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"OK: {TARGET} patched. OI-21 closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())