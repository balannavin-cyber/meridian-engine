#!/usr/bin/env python3
"""
patch_replay_signal.py
Replaces the replay_signal() function in run_validation_analysis.py
to exactly mirror the current build_trade_signal_local.py logic.

Changes applied:
  1. LONG_GAMMA -> DO_NOTHING (ENH-35: 47.7% accuracy, below random)
  2. NO_FLIP -> DO_NOTHING (ENH-35: 45-48% accuracy, below random)
  3. CONFLICT BUY_CE now trades (ENH-35: 67.9% accuracy)
  4. VIX gate removed
  5. Confidence threshold lowered to 40 (edge lives in 20-49 band)

Run from C:\\GammaEnginePython
"""

import os

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "run_validation_analysis.py")

NEW_FUNC = '''def replay_signal(row):
    """
    Replay MERDIAN signal logic against a hist_market_state row.
    Mirrors build_trade_signal_local.py exactly as of 2026-04-11.

    Changes from original:
      - LONG_GAMMA gated to DO_NOTHING (47.7% accuracy, below random)
      - NO_FLIP gated to DO_NOTHING (45-48% accuracy, below random)
      - CONFLICT BUY_CE now trades (67.9% accuracy at N=661)
      - VIX gate removed (HIGH_IV has more edge, not less)
      - Confidence threshold 60 -> 40 (edge lives in 20-49 band)

    Returns (action, confidence_score, trade_allowed, is_conflict).
    """
    gamma     = row.get("gamma_regime") or ""
    breadth   = row.get("breadth_regime") or ""
    momentum  = row.get("momentum_regime") or ""
    atm_iv    = float(row.get("atm_iv") or 0)
    flip_dist = float(row.get("flip_distance_pct") or 999)

    is_conflict = False

    # Gate 1: LONG_GAMMA -> DO_NOTHING
    # ENH-35: 47.7% accuracy at N=24,579 -- structurally below random
    if gamma == "LONG_GAMMA":
        return "DO_NOTHING", BASE_CONFIDENCE, False, False

    # Gate 2: NO_FLIP -> DO_NOTHING
    # ENH-35: 45-48% accuracy -- no institutional reference point
    if gamma == "NO_FLIP":
        return "DO_NOTHING", BASE_CONFIDENCE, False, False

    # Core action from breadth
    action = "DO_NOTHING"
    if breadth == "TRANSITION":
        action = "DO_NOTHING"
    elif breadth == "BEARISH":
        if momentum == "BULLISH":
            # CONFLICT BUY_PE -- below random (47-49%), keep as DO_NOTHING
            action = "DO_NOTHING"
        else:
            action = "BUY_PE"
    elif breadth == "BULLISH":
        if momentum == "BEARISH":
            # CONFLICT BUY_CE -- 67.9% accuracy, now trades
            is_conflict = True
            action = "BUY_CE"
        else:
            action = "BUY_CE"

    confidence = BASE_CONFIDENCE
    if action == "DO_NOTHING":
        return action, confidence, False, is_conflict

    # SHORT_GAMMA boost
    if gamma == "SHORT_GAMMA":
        confidence += SHORT_GAMMA_BOOST

    # Momentum alignment
    if action == "BUY_PE" and momentum == "BEARISH":
        confidence += MOMENTUM_ALIGNED_BOOST
    elif action == "BUY_CE" and momentum == "BULLISH":
        confidence += MOMENTUM_ALIGNED_BOOST
    elif action == "BUY_PE" and momentum == "BULLISH":
        confidence -= MOMENTUM_OPPOSING_CUT
    elif action == "BUY_CE" and momentum == "BEARISH":
        # CONFLICT case -- small penalty but still trades
        confidence -= 5

    # Flip distance
    if flip_dist < 0.2:
        confidence -= AT_FLIP_CUT
    elif flip_dist < 0.5:
        confidence -= NEAR_FLIP_CUT

    # VIX gate REMOVED (Experiment 5 + ENH-35)
    # HIGH_IV environments have more edge, not less

    confidence    = max(0, min(100, confidence))

    # Lowered threshold: edge lives in conf_20-49 band (ENH-35 Section 8)
    trade_allowed = confidence >= 40

    return action, confidence, trade_allowed, is_conflict

'''

def patch():
    with open(TARGET, "r", encoding="utf-8") as f:
        content = f.read()

    # Find start of replay_signal
    start_marker = "def replay_signal(row):"
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("ERROR: replay_signal not found")
        return

    # Find end of function -- next def at column 0
    search_from = start_idx + len(start_marker)
    end_idx = content.find("\ndef ", search_from)
    if end_idx == -1:
        print("ERROR: could not find end of replay_signal")
        return

    # Replace
    new_content = content[:start_idx] + NEW_FUNC + content[end_idx+1:]

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Patched replay_signal() successfully")
    print(f"Function spans lines {content[:start_idx].count(chr(10))+1} to "
          f"{content[:end_idx].count(chr(10))+1}")


if __name__ == "__main__":
    patch()
