#!/usr/bin/env python3
"""
patch_runner_ict.py
Adds ICT pattern detection step to run_option_snapshot_intraday_runner.py

Inserts after build_market_state_snapshot_local.py, before build_trade_signal_local.py.
Non-blocking — runner continues even if ICT detection fails.

Run from C:\\GammaEnginePython
"""
import os, shutil

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "run_option_snapshot_intraday_runner.py")

# The block to find
OLD = '''    run_with_fallbacks(
        "build_trade_signal_local.py",
        [[symbol]],
        timeout=TIMEOUT_SIGNAL,
        step_name=f"{symbol} build_trade_signal_live",
    )'''

# What to insert before it
NEW = '''    run_with_fallbacks(
        "detect_ict_patterns_runner.py",
        [[symbol]],
        timeout=60,
        step_name=f"{symbol} detect_ict_patterns",
        non_blocking=SHADOW_FAILURE_IS_NON_BLOCKING,
    )
    run_with_fallbacks(
        "build_trade_signal_local.py",
        [[symbol]],
        timeout=TIMEOUT_SIGNAL,
        step_name=f"{symbol} build_trade_signal_live",
    )'''

def patch():
    if not os.path.exists(TARGET):
        print(f"ERROR: {TARGET} not found")
        return False

    shutil.copy2(TARGET, TARGET + ".bak")

    with open(TARGET, "r", encoding="utf-8") as f:
        content = f.read()

    if "detect_ict_patterns_runner" in content:
        print("Already patched — skipping")
        return True

    if OLD not in content:
        print("ERROR: insertion point not found in runner")
        print("Check that build_trade_signal_local.py block exists unchanged")
        return False

    content = content.replace(OLD, NEW)

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(content)

    print("Runner patched — ICT detection step added")

    # Verify
    with open(TARGET, "r", encoding="utf-8") as f:
        verify = f.read()

    if "detect_ict_patterns_runner" in verify:
        print("Verified OK")
        return True
    else:
        print("ERROR: verification failed")
        return False

if __name__ == "__main__":
    ok = patch()
    import sys; sys.exit(0 if ok else 1)
