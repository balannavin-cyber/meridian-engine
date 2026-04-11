#!/usr/bin/env python3
"""
patch_signal_ict.py
Adds ICT zone enrichment to build_trade_signal_local.py

Inserts before 'return out' at end of build_signal() function.
Reads active ict_zones and adds 4 new fields to signal output:
  ict_pattern, ict_tier, ict_size_mult, ict_mtf_context

Run from C:\\GammaEnginePython
"""
import os, shutil

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "build_trade_signal_local.py")

OLD = "    return out\n\n\ndef insert_signal"

NEW = '''    # ENH-37: Enrich signal with ICT pattern context
    # Reads active ict_zones written by detect_ict_patterns_runner.py
    # Adds: ict_pattern, ict_tier, ict_size_mult, ict_mtf_context
    try:
        from detect_ict_patterns import enrich_signal_with_ict
        from datetime import date as _date
        _today = str(_date.today())
        _ict_rows = (SUPABASE.table("ict_zones")
                     .select("id,pattern_type,direction,zone_high,zone_low,"
                             "status,ict_tier,ict_size_mult,mtf_context,detected_at_ts")
                     .eq("symbol", symbol)
                     .eq("trade_date", _today)
                     .eq("status", "ACTIVE")
                     .execute().data)
        out = enrich_signal_with_ict(out, _ict_rows, float(spot or 0))
    except Exception as _ict_err:
        # Non-blocking â€” ICT enrichment failure never halts signal
        out["ict_pattern"]     = "NONE"
        out["ict_tier"]        = "NONE"
        out["ict_size_mult"]   = 1.0
        out["ict_mtf_context"] = "NONE"

    return out
def insert_signal'''


def patch():
    if not os.path.exists(TARGET):
        print(f"ERROR: {TARGET} not found")
        return False

    shutil.copy2(TARGET, TARGET + ".ict.bak")

    with open(TARGET, "r", encoding="utf-8") as f:
        content = f.read()

    if "enrich_signal_with_ict" in content:
        print("Already patched")
        return True

    if OLD not in content:
        print("ERROR: insertion point not found")
        idx = content.find("return out")
        print(f"  'return out' found at index {idx}")
        print(f"  Context: {repr(content[idx:idx+60])}")
        return False

    content = content.replace(OLD, NEW)

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(content)

    # Verify
    with open(TARGET, "r", encoding="utf-8") as f:
        verify = f.read()

    if "enrich_signal_with_ict" in verify:
        print("Signal engine patched OK â€” ICT enrichment added")
        return True
    else:
        print("ERROR: verification failed")
        return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if patch() else 1)

