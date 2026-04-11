#!/usr/bin/env python3
"""
patch_dashboard_ict_step4.py
Adds ICT zones data fetch to merdian_live_dashboard.py (Change 4).
Inserts before 'pipeline_rows = ""' in build_html().
Run from C:\\GammaEnginePython
"""
import os, shutil

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "merdian_live_dashboard.py")

OLD = '    pipeline_rows = ""'

NEW = '''\
    # ENH-37: ICT zones data fetch
    import datetime as _dt
    _today = str(_dt.date.today())
    _ict_q = ("select=pattern_type,ict_tier,ict_mtf_context,"
              "ict_size_mult,zone_high,zone_low,detected_at_ts"
              "&status=eq.ACTIVE&order=detected_at_ts.desc&limit=5"
              "&trade_date=eq." + _today)
    ict_rows_nifty  = sb_get("ict_zones", _ict_q + "&symbol=eq.NIFTY")
    ict_rows_sensex = sb_get("ict_zones", _ict_q + "&symbol=eq.SENSEX")

    def _ict_row_html(r, sym):
        pat  = r.get("pattern_type", "?")
        tier = r.get("ict_tier", "?")
        mtf  = r.get("ict_mtf_context", "?")
        mult = float(r.get("ict_size_mult") or 1.0)
        zhi  = float(r.get("zone_high", 0))
        zlo  = float(r.get("zone_low", 0))
        col     = "#1a7a1a" if "BULL" in pat else "#8b0000"
        mtf_col = {"VERY_HIGH": "#7700cc", "HIGH": "#005599",
                   "MEDIUM": "#886600", "LOW": "#888"}.get(mtf, "#888")
        return (
            f"<tr>"
            f"<td style='font-size:11px'>{sym}</td>"
            f"<td style='font-size:11px;color:{col}'><strong>{pat}</strong></td>"
            f"<td style='font-size:11px'>{tier}</td>"
            f"<td style='font-size:11px;color:{mtf_col}'>{mtf}</td>"
            f"<td style='font-size:11px'>{zlo:,.0f}\u2013{zhi:,.0f}</td>"
            f"<td style='font-size:11px'>{mult}x</td>"
            f"</tr>"
        )

    ict_all = ([(r, "NIFTY")  for r in (ict_rows_nifty  or [])] +
               [(r, "SENSEX") for r in (ict_rows_sensex or [])])
    if ict_all:
        ict_zones_html = (
            "<table style='width:100%;font-size:12px'>"
            "<tr><th>Sym</th><th>Pattern</th><th>Tier</th>"
            "<th>MTF</th><th>Zone</th><th>Size</th></tr>"
            + "".join(_ict_row_html(r, s) for r, s in ict_all)
            + "</table>"
        )
    else:
        ict_zones_html = (
            "<div style='color:#888;font-size:12px;padding:8px'>"
            "No active ICT zones today</div>"
        )

    pipeline_rows = ""'''


def patch():
    if not os.path.exists(TARGET):
        print(f"ERROR: {TARGET} not found")
        return False

    with open(TARGET, "r", encoding="utf-8") as f:
        content = f.read()

    if "ict_rows_nifty" in content:
        print("Already patched")
        return True

    if OLD not in content:
        print(f"ERROR: insertion point not found")
        return False

    shutil.copy2(TARGET, TARGET + ".step4.bak")
    content = content.replace(OLD, NEW, 1)

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(content)

    # Verify
    with open(TARGET, "r", encoding="utf-8") as f:
        verify = f.read()

    if "ict_rows_nifty" in verify and "ict_zones_html" in verify:
        print("PATCHED OK — ICT zones data fetch added")
        return True
    else:
        print("ERROR: verification failed")
        return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if patch() else 1)
