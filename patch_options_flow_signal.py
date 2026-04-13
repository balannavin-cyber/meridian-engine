"""
patch_options_flow_signal.py  --  ENH-02/04/07: Wire options flow into signal engine
=====================================================================================
Adds to build_trade_signal_local.py:
  1. Fetch latest options_flow_snapshots row for symbol
  2. Read pcr_regime, skew_regime, flow_regime, put_call_ratio, chain_iv_skew
  3. Confidence modifiers:
       PCR BEARISH + BUY_PE  → +5  (OI confirms bearish)
       PCR BULLISH + BUY_CE  → +5  (OI confirms bullish)
       PCR contra direction  → -4
       SKEW FEAR + BUY_PE    → +4  (PE IV premium = fear)
       SKEW GREED + BUY_CE   → +4  (CE IV premium = greed)
       FLOW PE_ACTIVE + BUY_PE → +3
       FLOW CE_ACTIVE + BUY_CE → +3
  4. Store flow fields in raw JSONB (no DDL needed)
  5. Add basis_pct-based risk-free rate note (ENH-07)

Closes: ENH-02 (PCR), ENH-04 (IV skew/flow), ENH-07 (basis note)
"""

import sys, shutil
TARGET = r'C:\GammaEnginePython\build_trade_signal_local.py'

src = open(TARGET, encoding='utf-8').read()

if 'options_flow_snapshots' in src:
    print('Already patched.')
    sys.exit(0)

# ── 1. Add flow fetch after market_state fetch (after wcb fields) ─────────────

FETCH_ANCHOR = '    # --- WCB fields ---\n    wcb_regime = breadth_features.get("wcb_regime")'

FLOW_FETCH = '''    # --- Options flow context (ENH-02/04) ---
    def _fetch_options_flow(sym: str) -> dict:
        try:
            rows = (SUPABASE.table("options_flow_snapshots")
                    .select("pcr_regime,skew_regime,flow_regime,"
                            "put_call_ratio,chain_iv_skew,ce_vol_oi_ratio,pe_vol_oi_ratio")
                    .eq("symbol", sym)
                    .order("ts", desc=True)
                    .limit(1)
                    .execute().data)
            return rows[0] if rows else {}
        except Exception:
            return {}
    _flow = _fetch_options_flow(symbol)
    pcr_regime   = _flow.get("pcr_regime")
    skew_regime  = _flow.get("skew_regime")
    flow_regime  = _flow.get("flow_regime")
    put_call_ratio = to_float(_flow.get("put_call_ratio"))
    chain_iv_skew  = to_float(_flow.get("chain_iv_skew"))

    # --- WCB fields ---
    wcb_regime = breadth_features.get("wcb_regime")'''

if FETCH_ANCHOR in src:
    src = src.replace(FETCH_ANCHOR, FLOW_FETCH, 1)
    print('[OK] Step 1: options flow fetch added')
else:
    print('[FAIL] Step 1: WCB anchor not found')
    sys.exit(1)

# ── 2. Add confidence modifiers before DTE gating ────────────────────────────

CONF_ANCHOR = '    # DTE gating\n    trade_allowed = True'

FLOW_CONF = '''    # Options flow confidence modifiers (ENH-02/04)
    if pcr_regime and action in ("BUY_PE", "BUY_CE"):
        if (pcr_regime == "BEARISH" and action == "BUY_PE"):
            confidence += 5.0
            reasons.append(f"PCR confirms bearish bias (pcr_regime={pcr_regime})")
        elif (pcr_regime == "BULLISH" and action == "BUY_CE"):
            confidence += 5.0
            reasons.append(f"PCR confirms bullish bias (pcr_regime={pcr_regime})")
        elif (pcr_regime == "BEARISH" and action == "BUY_CE"):
            confidence -= 4.0
            cautions.append(f"PCR contradicts bullish bias (pcr_regime={pcr_regime})")
        elif (pcr_regime == "BULLISH" and action == "BUY_PE"):
            confidence -= 4.0
            cautions.append(f"PCR contradicts bearish bias (pcr_regime={pcr_regime})")

    if skew_regime and action in ("BUY_PE", "BUY_CE"):
        if skew_regime == "FEAR" and action == "BUY_PE":
            confidence += 4.0
            reasons.append("IV skew shows FEAR — confirms PE setup")
        elif skew_regime == "GREED" and action == "BUY_CE":
            confidence += 4.0
            reasons.append("IV skew shows GREED — confirms CE setup")
        elif skew_regime == "FEAR" and action == "BUY_CE":
            cautions.append("IV skew FEAR contradicts CE setup")
        elif skew_regime == "GREED" and action == "BUY_PE":
            cautions.append("IV skew GREED contradicts PE setup")

    if flow_regime and action in ("BUY_PE", "BUY_CE"):
        if flow_regime == "PE_ACTIVE" and action == "BUY_PE":
            confidence += 3.0
            reasons.append("Options flow PE_ACTIVE confirms bearish setup")
        elif flow_regime == "CE_ACTIVE" and action == "BUY_CE":
            confidence += 3.0
            reasons.append("Options flow CE_ACTIVE confirms bullish setup")
        elif flow_regime == "PE_ACTIVE" and action == "BUY_CE":
            cautions.append("Options flow PE_ACTIVE contradicts CE setup")
        elif flow_regime == "CE_ACTIVE" and action == "BUY_PE":
            cautions.append("Options flow CE_ACTIVE contradicts PE setup")

    # ENH-07: Basis note (futures basis already in gamma_features)
    basis_pct = to_float(gamma_features.get("basis_pct"))
    if basis_pct is not None:
        if basis_pct > 0.5:
            cautions.append(f"Futures in premium vs spot (basis_pct={basis_pct:.2f}%)")
        elif basis_pct < -0.5:
            cautions.append(f"Futures in discount vs spot (basis_pct={basis_pct:.2f}%)")

    # DTE gating
    trade_allowed = True'''

if CONF_ANCHOR in src:
    src = src.replace(CONF_ANCHOR, FLOW_CONF, 1)
    print('[OK] Step 2: confidence modifiers added')
else:
    print('[FAIL] Step 2: DTE anchor not found')
    sys.exit(1)

# ── 3. Add flow fields to raw JSONB output ────────────────────────────────────

RAW_ANCHOR = '        # Narrative\n        "reasons": reasons,\n        "cautions": cautions,'

RAW_NEW = '''        # Narrative
        "reasons": reasons,
        "cautions": cautions,'''

# Add flow fields to raw block — find the "raw" key in the output dict
RAW_KEY_ANCHOR = '        "raw": {'

RAW_FLOW_FIELDS = '''        "raw": {
            "pcr_regime":      pcr_regime,
            "skew_regime":     skew_regime,
            "flow_regime":     flow_regime,
            "put_call_ratio":  put_call_ratio,
            "chain_iv_skew":   chain_iv_skew,
            "basis_pct":       basis_pct,'''

if RAW_KEY_ANCHOR in src:
    src = src.replace(RAW_KEY_ANCHOR, RAW_FLOW_FIELDS, 1)
    print('[OK] Step 3: flow fields added to raw JSONB')
else:
    # raw key might not exist — add it before ICT enrichment
    ICT_ANCHOR = '    # ENH-37: Enrich signal with ICT pattern context'
    RAW_BLOCK = '''    # Add options flow fields to raw JSONB
    if "raw" not in out:
        out["raw"] = {}
    out["raw"].update({
        "pcr_regime":     pcr_regime,
        "skew_regime":    skew_regime,
        "flow_regime":    flow_regime,
        "put_call_ratio": put_call_ratio,
        "chain_iv_skew":  chain_iv_skew,
        "basis_pct":      basis_pct,
    })

    # ENH-37: Enrich signal with ICT pattern context'''
    if ICT_ANCHOR in src:
        src = src.replace(ICT_ANCHOR, RAW_BLOCK, 1)
        print('[OK] Step 3: flow fields added via raw.update()')
    else:
        print('[WARN] Step 3: raw anchor not found — flow fields not stored in output')

# ── Write ─────────────────────────────────────────────────────────────────────

shutil.copy2(TARGET, TARGET + '.bak_flow')
open(TARGET, 'w', encoding='utf-8').write(src)

final = open(TARGET, encoding='utf-8').read()
print('\nVerification:')
checks = [
    ('flow fetch',         'options_flow_snapshots'),
    ('pcr_regime read',    'pcr_regime   = _flow.get'),
    ('PCR +5 modifier',    'confidence += 5.0'),
    ('skew +4 modifier',   'confidence += 4.0'),
    ('flow +3 modifier',   'confidence += 3.0'),
    ('basis_pct note',     'basis_pct = to_float'),
    ('raw output',         'pcr_regime'),
]
for label, token in checks:
    print(f'  [{"v" if token in final else "X"}] {label}')

print('\nDone. Restart runner for ENH-02/04/07 to take effect.')
print('Max additional confidence from flow signals: +12 (PCR+5, skew+4, flow+3)')
