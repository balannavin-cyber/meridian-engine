"""
OI-22 fix: split Dhan auth failure from transient network/timeout failures.

Root cause: AUTH_FAILURE_PATTERNS included "accessToken" which is a
common substring in diagnostic output during transient timeouts. Any
network timeout that logged request headers or token-handling traces
tripped OPTION_AUTH_BREAK with misleading 'authentication failure'
Telegram wording.

Fix:
  1. Remove "accessToken" from AUTH_FAILURE_PATTERNS (too loose).
  2. Add TRANSIENT_FAILURE_PATTERNS + _is_transient_failure().
  3. Check transient BEFORE auth; route to separate alert.
  4. Retighten auth wording to 'Dhan 401 / token invalid'.
"""
import ast
import sys
from pathlib import Path

TARGET = Path(r"C:\GammaEnginePython\run_option_snapshot_intraday_runner.py")

OLD_PATTERNS = '''# V18A-02: Auth failure patterns that trigger circuit-breaker
AUTH_FAILURE_PATTERNS = [
    "401",
    "Authentication Failed",
    "Client ID or Token invalid",
    "accessToken",
]'''

NEW_PATTERNS = '''# V18A-02 / OI-22: Auth failure = 401/token invalid ONLY.
# "accessToken" substring removed 2026-04-22 -- matched transient
# timeout traces that printed request headers, producing false
# OPTION_AUTH_BREAK alerts on pure network failures.
AUTH_FAILURE_PATTERNS = [
    "401",
    "Authentication Failed",
    "Client ID or Token invalid",
]

# OI-22: Transient network/timeout patterns -- distinct from auth.
# Issue a DIFFERENT alert so operator does not waste a token refresh
# on a problem that resolves on next cycle.
TRANSIENT_FAILURE_PATTERNS = [
    "ReadTimeout",
    "ConnectTimeout",
    "ConnectionError",
    "Max retries exceeded",
    "HTTPSConnectionPool",
    "Read timed out",
    "Connection aborted",
]'''

OLD_FUNC = '''def _is_auth_failure(text: str) -> bool:
    """Return True if text contains a Dhan 401 authentication failure pattern."""
    return any(pattern in text for pattern in AUTH_FAILURE_PATTERNS)'''

NEW_FUNC = '''def _is_auth_failure(text: str) -> bool:
    """Return True if text contains a Dhan 401 authentication failure pattern."""
    return any(pattern in text for pattern in AUTH_FAILURE_PATTERNS)


def _is_transient_failure(text: str) -> bool:
    """OI-22: Return True if text looks like a transient network/timeout
    failure as opposed to auth. Checked BEFORE auth so ambiguous traces
    that mention both are classified as transient (refresh will not help)."""
    return any(pattern in text for pattern in TRANSIENT_FAILURE_PATTERNS)'''

OLD_DISPATCH = '''    if _is_auth_failure(ingest_out):
        msg = (
            f"OPTION_AUTH_BREAK [{symbol}] \u2014 ingest_option_chain returned a Dhan "
            f"authentication failure (401 / token invalid). "
            f"Halting downstream pipeline (gamma / volatility / state / signal) "
            f"for this symbol this cycle. "
            f"Run refresh_dhan_token.py to restore. "
            f"runner alive != system valid."
        )
        log(f"CIRCUIT-BREAKER: {msg}")
        _send_circuit_breaker_alert(msg)
        log(f"========== LIVE PIPELINE HALTED [{symbol}] \u2014 auth failure ==========")
        return  # do NOT proceed to gamma / state / signal'''

NEW_DISPATCH = '''    # OI-22: transient check FIRST -- network/timeout errors must not
    # trigger an auth refresh. They self-resolve on next cycle.
    if _is_transient_failure(ingest_out):
        msg = (
            f"OPTION_TRANSIENT_FAIL [{symbol}] \u2014 ingest_option_chain hit a "
            f"network/timeout error (not auth). "
            f"Halting downstream pipeline this cycle; expect auto-recovery next cycle. "
            f"Do NOT refresh token. If this persists >3 cycles, investigate Dhan upstream."
        )
        log(f"CIRCUIT-BREAKER (transient): {msg}")
        _send_circuit_breaker_alert(msg)
        log(f"========== LIVE PIPELINE HALTED [{symbol}] \u2014 transient failure ==========")
        return

    if _is_auth_failure(ingest_out):
        msg = (
            f"OPTION_AUTH_BREAK [{symbol}] \u2014 ingest_option_chain returned Dhan 401 / "
            f"token invalid. "
            f"Halting downstream pipeline (gamma / volatility / state / signal) "
            f"for this symbol this cycle. "
            f"Run refresh_dhan_token.py to restore. "
            f"runner alive != system valid."
        )
        log(f"CIRCUIT-BREAKER: {msg}")
        _send_circuit_breaker_alert(msg)
        log(f"========== LIVE PIPELINE HALTED [{symbol}] \u2014 auth failure ==========")
        return  # do NOT proceed to gamma / state / signal'''


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    for label, old in [("PATTERNS", OLD_PATTERNS), ("FUNC", OLD_FUNC), ("DISPATCH", OLD_DISPATCH)]:
        if old not in src:
            print(f"ERROR: {label} block not found verbatim. Aborting, no file written.")
            return 2

    new_src = src.replace(OLD_PATTERNS, NEW_PATTERNS) \
                 .replace(OLD_FUNC, NEW_FUNC) \
                 .replace(OLD_DISPATCH, NEW_DISPATCH)

    # V18H governance: patch scripts MUST ast.parse() validate before writing.
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"SYNTAX ERROR in generated source: {e}")
        print("Aborting, no file written.")
        return 3

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"OK: {TARGET} patched. OI-22 closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())