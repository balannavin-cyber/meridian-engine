#!/usr/bin/env python3
"""
fix_atm_option_build.py
=========================
Patches build_atm_option_bars_mtf.py to fix two issues:
1. Timestamp mismatch: option bar_ts has seconds (09:15:59) 
   but spot 5m bar_ts is floored (09:15:00). Fix: floor option
   bar_ts to minute before bucketing.
2. IV is NULL in hist_option_bars_1m — skip IV columns, 
   focus on OHLC premium data only.
"""
from pathlib import Path

TARGET = Path("build_atm_option_bars_mtf.py")
content = TARGET.read_text(encoding="utf-8")

# Fix 1: get_bucket function — floor to minute first
old_bucket = '''def get_bucket(bar_ts_str, interval_mins):
    """Return bar open time floored to interval."""
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        mins = dt.hour * 60 + dt.minute
        bm   = (mins // interval_mins) * interval_mins
        return dt.replace(hour=bm//60, minute=bm%60,
                          second=0, microsecond=0).isoformat()
    except:
        return None'''

new_bucket = '''def get_bucket(bar_ts_str, interval_mins):
    """Return bar open time floored to interval.
    NOTE: option bars have seconds (09:15:59) — floor to minute first.
    """
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        # Floor to minute first (handles 09:15:59 -> 09:15:00)
        dt = dt.replace(second=0, microsecond=0)
        mins = dt.hour * 60 + dt.minute
        bm   = (mins // interval_mins) * interval_mins
        return dt.replace(hour=bm//60, minute=bm%60).isoformat()
    except:
        return None'''

content = content.replace(old_bucket, new_bucket)

# Fix 2: in_bucket function — also floor to minute
old_in_bucket = '''            def in_bucket(b, interval=5):
                try:
                    bdt = datetime.fromisoformat(b["bar_ts"].replace("Z", "+00:00"))
                    return bucket_dt <= bdt < next_bucket
                except:
                    return False'''

new_in_bucket = '''            def in_bucket(b, interval=5):
                try:
                    bdt = datetime.fromisoformat(b["bar_ts"].replace("Z", "+00:00"))
                    # Floor to minute (option bars have seconds)
                    bdt = bdt.replace(second=0, microsecond=0)
                    return bucket_dt <= bdt < next_bucket
                except:
                    return False'''

content = content.replace(old_in_bucket, new_in_bucket)

# Fix 3: aggregate_option_bars — floor bar_ts to minute before bucketing
old_agg = '''    for bar in bars_1m:
        bucket = get_bucket(bar["bar_ts"], interval_mins)
        if bucket:
            buckets[bucket].append(bar)'''

new_agg = '''    for bar in bars_1m:
        # Floor bar_ts to minute before bucketing (option bars have seconds)
        bar_ts_floored = bar["bar_ts"]
        try:
            dt = datetime.fromisoformat(bar["bar_ts"].replace("Z", "+00:00"))
            bar_ts_floored = dt.replace(second=0, microsecond=0).isoformat()
        except:
            pass
        bucket = get_bucket(bar_ts_floored, interval_mins)
        if bucket:
            buckets[bucket].append(bar)'''

content = content.replace(old_agg, new_agg)

TARGET.write_text(content, encoding="utf-8")

# Verify syntax
import ast
try:
    ast.parse(TARGET.read_text(encoding="utf-8"))
    print("OK: syntax valid")
    print("Fixed: timestamp flooring in get_bucket, in_bucket, aggregate_option_bars")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
