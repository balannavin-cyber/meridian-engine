f = r'C:\GammaEnginePython\build_trade_signal_local.py'
c = open(f, encoding='utf-8').read()

# Find the last occurrence of ict_lots_t3 = None (in except block)
anchor = 'ict_lots_t3"]     = None'
idx = c.rfind(anchor)
print(f'Last ict_lots_t3=None at index: {idx}')

# Find end of that line
end = c.find('\n', idx) + 1
print(f'Inserting ENH-06 block after index: {end}')
print(f'Context: {repr(c[idx:end+5])}')

ENH06 = '''
    # ENH-06: Pre-trade cost filter
    # Validates lot sizing against current capital at signal time.
    try:
        from merdian_utils import (
            effective_sizing_capital, estimate_lot_cost,
            LOT_SIZES, KELLY_FRACTIONS_C as _KF
        )
        _cap_rows = (SUPABASE.table("capital_tracker")
                     .select("capital")
                     .eq("symbol", symbol)
                     .limit(1)
                     .execute().data)
        _raw_capital = float(_cap_rows[0]["capital"]) if _cap_rows else 200_000
        _eff_capital = effective_sizing_capital(_raw_capital)
        _tier        = out.get("ict_tier", "NONE")
        _kelly_frac  = _KF.get(_tier, 0.20)
        _allocated   = _eff_capital * _kelly_frac
        _lot_cost    = estimate_lot_cost(
            symbol,
            float(spot or 0),
            float(atm_iv_avg or 16.0),
            float(dte or 2),
        )
        _active_lots = out.get("ict_lots_t1") or out.get("ict_lots_t2") or out.get("ict_lots_t3")
        _capital_ok  = True
        if _active_lots and _lot_cost and _lot_cost > 0:
            _deployed = _active_lots * _lot_cost
            if _deployed > _allocated * 1.10:
                _tier_key = {"TIER1": "ict_lots_t1", "TIER2": "ict_lots_t2", "TIER3": "ict_lots_t3"}.get(_tier)
                if _tier_key:
                    out[_tier_key] = 1
                cautions.append(
                    f"ENH-06: {_active_lots} lots (INR {_deployed:,.0f}) "
                    f"exceeds allocation (INR {_allocated:,.0f}) -- reduced to 1 lot"
                )
                _capital_ok = False
            else:
                reasons.append(
                    f"ENH-06: Capital OK -- {_active_lots} lots x "
                    f"INR {_lot_cost:,.0f} = INR {_deployed:,.0f}"
                )
        if _raw_capital < 50_000:
            cautions.append(f"ENH-06: Low capital INR {_raw_capital:,.0f} -- minimum sizing")
        if "raw" not in out:
            out["raw"] = {}
        out["raw"].update({
            "enh06_capital_raw": _raw_capital,
            "enh06_capital_eff": _eff_capital,
            "enh06_allocated":   _allocated,
            "enh06_lot_cost":    _lot_cost,
            "enh06_capital_ok":  _capital_ok,
        })
    except Exception as _e06:
        cautions.append(f"ENH-06: Capital check skipped ({_e06})")
'''

if idx == -1:
    print('Anchor not found')
else:
    new_c = c[:end] + ENH06 + c[end:]
    import shutil
    shutil.copy2(f, f + '.bak_enh06')
    open(f, 'w', encoding='utf-8').write(new_c)
    final = open(f, encoding='utf-8').read()
    print('Verification:')
    for label, token in [
        ('ENH-06 marker',    'ENH-06: Pre-trade cost filter'),
        ('capital fetch',    'capital_tracker'),
        ('lot cost check',   'estimate_lot_cost'),
        ('over-alloc',       'exceeds allocation'),
        ('raw output',       'enh06_capital_ok'),
    ]:
        print(f'  [{"v" if token in final else "X"}] {label}')
    print('Done.')
