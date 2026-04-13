import sys

path = '/home/ssm-user/meridian-engine/build_shadow_signal_v3_local.py'
content = open(path, encoding='utf-8').read()

# Change 1: add india_vix read after vix_trend line
OLD1 = '    vix_trend = iv_context.get("vix_trend") if iv_context else None'
NEW1 = (
    '    vix_trend = iv_context.get("vix_trend") if iv_context else None\n'
    '    vol_features = market_state.get("volatility_features") or {}\n'
    '    india_vix = float(vol_features["india_vix"]) if vol_features.get("india_vix") is not None else None'
)
if OLD1 not in content:
    print("FAIL: Change 1 anchor not found")
    sys.exit(1)
content = content.replace(OLD1, NEW1, 1)
print("Change 1 applied - india_vix read from volatility_features")

# Change 2: add VIX penalty inside confidence block
# Insert after the iv_context_low_conf penalty block
OLD2 = '        confidence -= 3\n'
NEW2 = (
    '        confidence -= 3\n'
    '\n'
    '    # E-03: India VIX confidence penalty\n'
    '    if india_vix is not None and india_vix > 20:\n'
    '        confidence -= 8\n'
    '        cautions.append(f"India VIX elevated ({india_vix:.1f} > 20) — confidence penalised")\n'
)
if OLD2 not in content:
    print("FAIL: Change 2 anchor not found")
    # show context
    idx = content.find('confidence -= 3')
    print("Context:", repr(content[max(0,idx-100):idx+100]))
    sys.exit(1)
content = content.replace(OLD2, NEW2, 1)
print("Change 2 applied - VIX penalty block added")

# Change 3: add VIX panic gate after trade_allowed is set
OLD3 = '    if not trade_allowed and action != "DO_NOTHING":\n        cautions.append("Shadow confidence threshold not met for execution")'
NEW3 = (
    '    if not trade_allowed and action != "DO_NOTHING":\n'
    '        cautions.append("Shadow confidence threshold not met for execution")\n'
    '\n'
    '    # E-03: India VIX panic gate\n'
    '    if india_vix is not None and india_vix > 25:\n'
    '        trade_allowed = False\n'
    '        cautions.append(f"India VIX panic gate active ({india_vix:.1f} > 25) — trade blocked")'
)
if OLD3 not in content:
    print("FAIL: Change 3 anchor not found")
    idx = content.find('Shadow confidence threshold not met')
    print("Context:", repr(content[max(0,idx-100):idx+100]))
    sys.exit(1)
content = content.replace(OLD3, NEW3, 1)
print("Change 3 applied - VIX panic gate added")

open(path, 'w', encoding='utf-8').write(content)
print("SUCCESS - E-03 India VIX rules added to shadow signal builder")
print("New file length:", len(content))
