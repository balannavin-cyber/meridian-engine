#!/usr/bin/env python3
"""
patch_dashboard_ict.py
Adds ICT zone display to merdian_live_dashboard.py

Three changes:
  1. Expand signal_snapshots query to fetch ICT fields
  2. Update signal stage value to show ICT context
  3. Add ICT zones card below pipeline table

Run from C:\\GammaEnginePython
"""
import os, shutil

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "merdian_live_dashboard.py")


def patch():
    if not os.path.exists(TARGET):
        print(f"ERROR: {TARGET} not found")
        return False

    shutil.copy2(TARGET, TARGET + ".ict.bak")

    with open(TARGET, "r", encoding="utf-8") as f:
        content = f.read()

    if "ict_pattern" in content:
        print("Already patched")
        return True

    changes = 0

    # ── Change 1: Expand signal query to include ICT fields ───────────
    old1 = ('rows = sb_get("signal_snapshots", '
            'f"select=created_at,action,confidence_score,trade_allowed'
            '&symbol=eq.{symbol}&order=created_at.desc&limit=1")')
    new1 = ('rows = sb_get("signal_snapshots", '
            'f"select=created_at,action,confidence_score,trade_allowed,'
            'ict_pattern,ict_tier,ict_size_mult,ict_mtf_context'
            '&symbol=eq.{symbol}&order=created_at.desc&limit=1")')

    if old1 in content:
        content = content.replace(old1, new1)
        changes += 1
        print("Change 1 applied: expanded signal query")
    else:
        print("WARNING: Change 1 insertion point not found")

    # ── Change 2: Update signal stage value to show ICT context ───────
    old2 = ('            stages.append({"name": "Signal", "ts": dt.strftime("%H:%M:%S") if dt else "?",\n'
            '                           "value": f"{action} | conf {conf} | {\'✓\' if allowed else \'✗\'}",\n'
            '                           "lag": lag, "ok": lag is not None and lag < 600,\n'
            '                           "action": action, "allowed": allowed})')
    new2 = ('            ict_pat  = rows[0].get("ict_pattern", "NONE") or "NONE"\n'
            '            ict_tier = rows[0].get("ict_tier", "NONE") or "NONE"\n'
            '            ict_mtf  = rows[0].get("ict_mtf_context", "NONE") or "NONE"\n'
            '            ict_mult = rows[0].get("ict_size_mult", 1.0) or 1.0\n'
            '            ict_str  = f" | ICT:{ict_pat}({ict_tier})[{ict_mtf}]x{ict_mult}" if ict_pat != "NONE" else ""\n'
            '            stages.append({"name": "Signal", "ts": dt.strftime("%H:%M:%S") if dt else "?",\n'
            '                           "value": f"{action} | conf {conf} | {\'✓\' if allowed else \'✗\'}{ict_str}",\n'
            '                           "lag": lag, "ok": lag is not None and lag < 600,\n'
            '                           "action": action, "allowed": allowed,\n'
            '                           "ict_pattern": ict_pat, "ict_tier": ict_tier,\n'
            '                           "ict_mtf": ict_mtf, "ict_mult": ict_mult})')

    if old2 in content:
        content = content.replace(old2, new2)
        changes += 1
        print("Change 2 applied: signal stage shows ICT context")
    else:
        # Try without escape issues — find approximate location
        old2b = '"value": f"{action} | conf {conf}'
        if old2b in content:
            print("WARNING: Change 2 partial match — applying targeted fix")
            content = content.replace(
                '                           "value": f"{action} | conf {conf} | {\'✓\' if allowed else \'✗\'}",',
                '                           "value": f"{action} | conf {conf} | {\'✓\' if allowed else \'✗\'} | ICT:{rows[0].get(\'ict_pattern\',\'NONE\')}[{rows[0].get(\'ict_mtf_context\',\'?\') }]",',
            )
            changes += 1
        else:
            print("WARNING: Change 2 insertion point not found")

    # ── Change 3: Add ICT zones card after pipeline table ─────────────
    old3 = '<div class="g2">'
    new3 = '''<div class="card" style="margin-bottom:12px">
  <div class="ct">ICT Pattern Zones</div>
  <div class="cb" id="ict-zones-block">
    {ict_zones_html}
  </div>
</div>

<div class="g2">'''

    if old3 in content and '{ict_zones_html}' not in content:
        content = content.replace(old3, new3, 1)
        changes += 1
        print("Change 3 applied: ICT zones card added")
    else:
        print("WARNING: Change 3 insertion point not found or already present")

    # ── Change 4: Build ict_zones_html in collect_data or build_html ──
    # Find where build_html formats pipeline_rows and add ict_zones_html
    old4 = '    pipeline_rows = "\\n".join('
    if old4 not in content:
        old4 = '    pipeline_rows = "\n".join('

    new4_prefix = '''    # ICT zones block
    ict_rows_nifty  = sb_get("ict_zones",
        "select=pattern_type,ict_tier,ict_mtf_context,ict_size_mult,"
        "zone_high,zone_low,status,detected_at_ts"
        f"&symbol=eq.NIFTY&trade_date=eq.{__import__('datetime').date.today()}"
        "&status=eq.ACTIVE&order=detected_at_ts.desc&limit=5")
    ict_rows_sensex = sb_get("ict_zones",
        "select=pattern_type,ict_tier,ict_mtf_context,ict_size_mult,"
        "zone_high,zone_low,status,detected_at_ts"
        f"&symbol=eq.SENSEX&trade_date=eq.{__import__('datetime').date.today()}"
        "&status=eq.ACTIVE&order=detected_at_ts.desc&limit=5")

    def _ict_row_html(r, sym):
        pat  = r.get("pattern_type","?")
        tier = r.get("ict_tier","?")
        mtf  = r.get("ict_mtf_context","?")
        mult = r.get("ict_size_mult", 1.0)
        zhi  = float(r.get("zone_high",0))
        zlo  = float(r.get("zone_low",0))
        col  = "#1a7a1a" if "BULL" in pat else "#8b0000"
        mtf_col = {"VERY_HIGH":"#7700cc","HIGH":"#005599","MEDIUM":"#886600","LOW":"#888"}.get(mtf,"#888")
        return (f'<tr><td style="font-size:11px">{sym}</td>'
                f'<td style="font-size:11px;color:{col}"><strong>{pat}</strong></td>'
                f'<td style="font-size:11px">{tier}</td>'
                f'<td style="font-size:11px;color:{mtf_col}">{mtf}</td>'
                f'<td style="font-size:11px">{zlo:,.0f}–{zhi:,.0f}</td>'
                f'<td style="font-size:11px">{mult}x</td></tr>')

    ict_all = ([(r,"NIFTY") for r in (ict_rows_nifty or [])] +
               [(r,"SENSEX") for r in (ict_rows_sensex or [])])
    if ict_all:
        ict_zones_html = ('<table style="width:100%;font-size:12px">'
            '<tr><th>Sym</th><th>Pattern</th><th>Tier</th>'
            '<th>MTF</th><th>Zone</th><th>Size</th></tr>'
            + "".join(_ict_row_html(r,s) for r,s in ict_all)
            + '</table>')
    else:
        ict_zones_html = '<div style="color:#888;font-size:12px;padding:8px">No active ICT zones today</div>'

    '''

    if old4 in content:
        content = content.replace(old4, new4_prefix + old4, 1)
        changes += 1
        print("Change 4 applied: ICT zones data fetch added")
    else:
        print("WARNING: Change 4 insertion point not found — skipping")

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n{changes}/4 changes applied")
    if changes >= 3:
        print("Dashboard ICT wiring complete")
        return True
    else:
        print("Some changes missing — manual review needed")
        return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if patch() else 1)
