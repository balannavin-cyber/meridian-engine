"""
patch_dashboard_capital.py  --  Add capital input to signal dashboard
=====================================================================
Adds to merdian_signal_dashboard.py:
  [A] POST /set_capital endpoint in the HTTP handler
  [B] Capital input + SET button inside each signal card
  [C] JS fetch() to submit without full page reload
  [D] CSS for the input/button

Run:      python patch_dashboard_capital.py
Dry-run:  python patch_dashboard_capital.py --dry-run
"""

import os
import sys
import shutil

BASE   = r'C:\GammaEnginePython'
TARGET = os.path.join(BASE, 'merdian_signal_dashboard.py')
DRY    = '--dry-run' in sys.argv

# ── [A] Add POST handler inside Handler class ─────────────────────────────────

HANDLER_GET = '    def do_GET(self):'

HANDLER_POST = '''    def do_POST(self):
        """Handle capital update: POST /set_capital?symbol=NIFTY&capital=500000"""
        if self.path.startswith('/set_capital'):
            from urllib.parse import urlparse, parse_qs
            import json as _json
            qs     = parse_qs(urlparse(self.path).query)
            symbol = qs.get('symbol', [None])[0]
            cap    = qs.get('capital', [None])[0]
            if symbol and cap:
                try:
                    cap_val  = float(cap)
                    from datetime import datetime, timezone as _tz
                    now_ts   = datetime.now(_tz.utc).isoformat()
                    result   = (sb.table('capital_tracker')
                                .update({'capital': cap_val, 'updated_at': now_ts})
                                .eq('symbol', symbol.upper())
                                .execute())
                    body = _json.dumps({'ok': True, 'symbol': symbol, 'capital': cap_val}).encode()
                except Exception as e:
                    body = _json.dumps({'ok': False, 'error': str(e)}).encode()
            else:
                body = _json.dumps({'ok': False, 'error': 'missing symbol or capital'}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):'''

# ── [B] Capital input inside signal_card — replace cap-row ───────────────────

CAP_ROW_OLD = """          <div class="cap-row">
            <span class="lbl">Capital</span>
            <span class="val">{inr_fmt(cap)}</span>
            <span class="sep">│</span>
            <span class="lbl">Effective sizing</span>
            <span class="val">{inr_fmt(cap_eff)}</span>
          </div>"""

CAP_ROW_NEW = """          <div class="cap-row">
            <span class="lbl">Capital</span>
            <span class="val" id="cap-display-{sym}">{inr_fmt(cap)}</span>
            <span class="sep">│</span>
            <span class="lbl">Effective sizing</span>
            <span class="val">{inr_fmt(cap_eff)}</span>
          </div>
          <div class="cap-input-row">
            <span class="lbl">Set capital</span>
            <input class="cap-input" id="cap-input-{sym}" type="number"
                   value="{int(cap)}" min="200000" step="100000"
                   placeholder="INR amount"/>
            <button class="cap-btn" onclick="setCapital('{sym}')">SET</button>
            <span class="cap-status" id="cap-status-{sym}"></span>
          </div>"""

# ── [C] JS — add setCapital() before closing </script> ───────────────────────

JS_ANCHOR = '</script>'

JS_ADDITION = """
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

# ── [D] CSS ───────────────────────────────────────────────────────────────────

CSS_ANCHOR = '  /* ── Active legend (per card) ── */'

CSS_ADDITION = """  /* ── Capital input row ── */
  .cap-input-row {{ display:flex; align-items:center; gap:8px; padding:8px 16px;
                    border-bottom:1px solid var(--border); flex-wrap:wrap; }}
  .cap-input {{ background:var(--bg3); border:1px solid var(--border); color:var(--text);
                font-family:var(--mono); font-size:13px; padding:4px 8px;
                border-radius:2px; width:130px; }}
  .cap-input:focus {{ outline:none; border-color:var(--cyan); }}
  .cap-btn {{ padding:4px 14px; background:transparent; border:1px solid var(--cyan);
              color:var(--cyan); font-family:var(--sans); font-size:12px; font-weight:700;
              letter-spacing:1px; cursor:pointer; border-radius:2px; }}
  .cap-btn:hover {{ background:rgba(0,204,255,0.1); }}
  .cap-status {{ font-size:12px; font-family:var(--mono); }}

  /* ── Active legend (per card) ── */"""

# ─────────────────────────────────────────────────────────────────────────────

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def p_ok(msg):   print(f'  [OK  ] {msg}')
def p_skip(msg): print(f'  [SKIP] {msg}')
def p_dry(msg):  print(f'  [DRY ] {msg}')
def p_fail(msg): print(f'  [FAIL] {msg}')

def main():
    print('=' * 60)
    print('patch_dashboard_capital.py  --  Capital input on dashboard')
    print('DRY RUN' if DRY else 'LIVE')
    print('=' * 60)

    if not os.path.exists(TARGET):
        print(f'[ERROR] Not found: {TARGET}')
        sys.exit(1)

    src = read_file(TARGET)

    if 'setCapital' in src:
        p_skip('Already patched.')
        return

    print('\nPre-flight:')
    errors = 0
    for label, anchor in [
        ('[A] do_GET handler',    HANDLER_GET),
        ('[B] cap-row div',       'class="cap-row"'),
        ('[C] closing </script>', JS_ANCHOR),
        ('[D] CSS anchor',        CSS_ANCHOR),
    ]:
        if anchor in src:
            p_ok(f'Found: {label}')
        else:
            p_fail(f'NOT found: {label}')
            errors += 1

    if errors:
        print(f'\n[ABORT] {errors} anchor(s) missing.')
        sys.exit(1)

    new_src = src

    # [A] Insert POST handler before GET handler
    new_src = new_src.replace(HANDLER_GET, HANDLER_POST, 1)
    p_ok('[A] POST /set_capital handler added.')

    # [B] Replace cap-row with cap-row + input row
    new_src = new_src.replace(CAP_ROW_OLD, CAP_ROW_NEW, 1)
    p_ok('[B] Capital input + SET button added to card.')

    # [C] Add JS before </script>
    new_src = new_src.replace(JS_ANCHOR, JS_ADDITION, 1)
    p_ok('[C] setCapital() JS function added.')

    # [D] Add CSS
    new_src = new_src.replace(CSS_ANCHOR, CSS_ADDITION, 1)
    p_ok('[D] CSS added.')

    if DRY:
        p_dry('No files written.')
        return

    shutil.copy2(TARGET, TARGET + '.bak2')
    write_file(TARGET, new_src)

    final = read_file(TARGET)
    print('\nVerification:')
    for label, token in [
        ('do_POST handler present',   'def do_POST(self):'),
        ('POST /set_capital route',   '/set_capital'),
        ('cap-input-row in HTML',     'cap-input-row'),
        ('setCapital JS function',    'function setCapital(symbol)'),
        ('cap-btn CSS class',         '.cap-btn'),
    ]:
        sym = 'v' if token in final else 'X'
        print(f'  [{sym}] {label}')

    print('\n' + '=' * 60)
    print('Done. Restart dashboard:')
    print('  python merdian_signal_dashboard.py')
    print('\nEach card now has a capital input field + SET button.')
    print('Updates instantly — no page reload required.')
    print('=' * 60)

if __name__ == '__main__':
    main()
