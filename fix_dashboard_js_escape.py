"""
fix_dashboard_js_escape.py  --  Fix JS brace escaping in dashboard
===================================================================
The setCapital() JS block was inserted with unescaped curly braces
which Python's f-string interprets as format expressions.
Fix: replace the broken JS block with a properly escaped version.
"""

import os
import sys
import shutil

BASE   = r'C:\GammaEnginePython'
TARGET = os.path.join(BASE, 'merdian_signal_dashboard.py')
DRY    = '--dry-run' in sys.argv

# Broken block (what was inserted)
JS_OLD = """
// Capital setter
function setCapital(symbol) {
  const input  = document.getElementById('cap-input-' + symbol);
  const status = document.getElementById('cap-status-' + symbol);
  const disp   = document.getElementById('cap-display-' + symbol);
  const val    = parseFloat(input.value);
  if (!val || val < 200000) {
    status.textContent = 'Min ₹2,00,000';
    status.style.color = 'var(--red)';
    return;
  }
  status.textContent = 'Saving...';
  status.style.color = 'var(--muted)';
  fetch(`/set_capital?symbol=${symbol}&capital=${val}`, {method:'POST'})
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        const fmt = '₹' + Math.round(data.capital).toLocaleString('en-IN');
        status.textContent = '✓ Saved';
        status.style.color = 'var(--green)';
        if (disp) disp.textContent = fmt;
        setTimeout(() => { status.textContent = ''; }, 3000);
      } else {
        status.textContent = 'Error: ' + data.error;
        status.style.color = 'var(--red)';
      }
    })
    .catch(e => {
      status.textContent = 'Failed';
      status.style.color = 'var(--red)';
    });
}
</script>"""

# Fixed block — all JS {{ }} escaped for Python f-string
JS_NEW = """
// Capital setter
function setCapital(symbol) {{
  const input  = document.getElementById('cap-input-' + symbol);
  const status = document.getElementById('cap-status-' + symbol);
  const disp   = document.getElementById('cap-display-' + symbol);
  const val    = parseFloat(input.value);
  if (!val || val < 200000) {{
    status.textContent = 'Min \u20b92,00,000';
    status.style.color = 'var(--red)';
    return;
  }}
  status.textContent = 'Saving...';
  status.style.color = 'var(--muted)';
  fetch('/set_capital?symbol=' + symbol + '&capital=' + val, {{method:'POST'}})
    .then(r => r.json())
    .then(data => {{
      if (data.ok) {{
        const fmt = '\u20b9' + Math.round(data.capital).toLocaleString('en-IN');
        status.textContent = '\u2713 Saved';
        status.style.color = 'var(--green)';
        if (disp) disp.textContent = fmt;
        setTimeout(() => {{ status.textContent = ''; }}, 3000);
      }} else {{
        status.textContent = 'Error: ' + data.error;
        status.style.color = 'var(--red)';
      }}
    }})
    .catch(e => {{
      status.textContent = 'Failed';
      status.style.color = 'var(--red)';
    }});
}}
</script>"""

def main():
    print('fix_dashboard_js_escape.py')
    src = open(TARGET, encoding='utf-8').read()

    if JS_OLD not in src:
        print('[FAIL] Broken JS block not found — already fixed or different content.')
        sys.exit(1)
    print('[OK  ] Broken JS block found.')

    if DRY:
        print('[DRY ] No files written.')
        return

    shutil.copy2(TARGET, TARGET + '.bak3')
    new_src = src.replace(JS_OLD, JS_NEW, 1)
    open(TARGET, 'w', encoding='utf-8').write(new_src)

    # Verify
    final = open(TARGET, encoding='utf-8').read()
    ok = 'function setCapital(symbol) {{' in final and JS_OLD not in final
    print(f'[{"OK  " if ok else "FAIL"}] Fix applied.')
    print('\nRestart dashboard:')
    print('  python merdian_signal_dashboard.py')

if __name__ == '__main__':
    main()
