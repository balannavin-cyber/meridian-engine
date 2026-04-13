"""
patch_healthmon_procs.py  --  Add process status panel to health monitor
"""
import sys, shutil
sys.path.insert(0, r'C:\GammaEnginePython')

TARGET = r'C:\GammaEnginePython\merdian_live_dashboard.py'

ANCHOR = '<div style="text-align:right;padding:4px 18px 10px;font-size:10px;color:#aaa">MERDIAN v2'

PROC_PANEL = '''<div class="card">
  <div class="ct">&#9881; MERDIAN Processes</div>
  <div style="padding:6px 0">
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <tr style="background:#1a1a2e">
        <th style="padding:6px 12px;text-align:left;color:#888">Process</th>
        <th style="padding:6px 12px;text-align:left;color:#888">Status</th>
        <th style="padding:6px 12px;text-align:right;color:#888">PID</th>
        <th style="padding:6px 12px;text-align:left;color:#888">Started</th>
        <th style="padding:6px 12px;text-align:left;color:#888">Port</th>
      </tr>
      {proc_rows}
    </table>
  </div>
</div>
'''

# Also need to add proc_rows generation to collect_data and build_html

src = open(TARGET, encoding='utf-8').read()

if 'MERDIAN Processes' in src:
    print('Already patched.')
    sys.exit(0)

if ANCHOR not in src:
    print('Anchor not found.')
    sys.exit(1)

# 1. Add proc_rows generation inside build_html (before the return f""")
# Find the f-string opening which is "return f\"\"\"" area
# Inject proc_rows generation before the HTML block

BUILD_ANCHOR = 'def build_html(data: Dict) -> str:'

PROC_BUILD = '''def _get_proc_rows() -> str:
    """Generate process status rows for health monitor panel."""
    try:
        import merdian_pm as _pm
        rows = _pm.status()
        html = []
        for r in rows:
            alive   = r['alive']
            st_col  = '#00cc66' if alive else '#cc3333'
            st_txt  = '&#10003; RUNNING' if alive else '&#10007; STOPPED'
            pid     = str(r['pid']) if r['pid'] else '&mdash;'
            started = r['started'] or '&mdash;'
            port    = str(r['port']) if r['port'] else '&mdash;'
            dupe    = f' <span style="color:#ffaa00">&#9888; dupe:{r["dupes"]}</span>' if r.get('dupes') else ''
            html.append(
                f'<tr style="border-top:1px solid #2a2a3e">'
                f'<td style="padding:6px 12px;color:#ccc">{r["desc"]}</td>'
                f'<td style="padding:6px 12px;color:{st_col}">{st_txt}{dupe}</td>'
                f'<td style="padding:6px 12px;text-align:right;color:#888;font-family:monospace">{pid}</td>'
                f'<td style="padding:6px 12px;color:#888">{started}</td>'
                f'<td style="padding:6px 12px;color:#888">{port}</td>'
                f'</tr>'
            )
        return ''.join(html)
    except Exception as e:
        return f'<tr><td colspan="5" style="padding:10px;color:#888">Process manager unavailable: {e}</td></tr>'

'''

new_src = src.replace(BUILD_ANCHOR, PROC_BUILD + BUILD_ANCHOR, 1)

# 2. Add {proc_rows} variable assignment inside build_html before the html f-string
# Inject right before the return f"""
RETURN_ANCHOR = '    return f"""'
PROC_VAR = '    proc_rows = _get_proc_rows()\n'

# Only replace first occurrence of return f""" inside build_html
new_src = new_src.replace(RETURN_ANCHOR, PROC_VAR + RETURN_ANCHOR, 1)

# 3. Inject the panel HTML before the footer div
PANEL_HTML = PROC_PANEL + ANCHOR
new_src = new_src.replace(ANCHOR, PANEL_HTML, 1)

shutil.copy2(TARGET, TARGET + '.bak_pm')
open(TARGET, 'w', encoding='utf-8').write(new_src)

# Verify
final = open(TARGET, encoding='utf-8').read()
checks = [
    ('_get_proc_rows defined',     '_get_proc_rows'),
    ('proc_rows assigned',         'proc_rows = _get_proc_rows'),
    ('panel in HTML',              'MERDIAN Processes'),
    ('proc_rows in template',      '{proc_rows}'),
]
print('Verification:')
for label, token in checks:
    sym = 'v' if token in final else 'X'
    print(f'  [{sym}] {label}')

print('\nDone. Restart health monitor to see process panel.')
