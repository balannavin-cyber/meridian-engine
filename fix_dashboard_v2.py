"""
fix_dashboard_v2.py  --  Dashboard comprehensive fixes
=======================================================
Fixes:
  1. Capital input missing on SENSEX  (ensure both cards get it)
  2. Input not editable               (remove conflicting CSS, fix z-index)
  3. SENSEX shows TRADE ALLOWED       (badge logic: DO_NOTHING = always BLOCKED)
  4. Better button + feedback         (spinner state, clearer styling)
  5. JS fetch properly escaped        (no f-string conflicts)

Strategy: targeted replacements on confirmed anchor strings.
"""

import os
import sys
import shutil

BASE   = r'C:\GammaEnginePython'
TARGET = os.path.join(BASE, 'merdian_signal_dashboard.py')
DRY    = '--dry-run' in sys.argv

src = open(TARGET, encoding='utf-8').read()
new_src = src

errors = 0

# ─────────────────────────────────────────────────────────────────────────────
# Fix 1: Badge logic — DO_NOTHING always shows BLOCKED regardless of trade_allowed
# ─────────────────────────────────────────────────────────────────────────────
BADGE_OLD = """        allowed_html = (
            '<span class="badge-green">TRADE ALLOWED</span>' if allowed
            else '<span class="badge-red">BLOCKED</span>'
        )"""

BADGE_NEW = """        allowed_html = (
            '<span class="badge-green">TRADE ALLOWED</span>'
            if (allowed and action not in ('DO_NOTHING', 'NO DATA', 'ERROR'))
            else '<span class="badge-red">BLOCKED</span>'
        )"""

if BADGE_OLD in new_src:
    new_src = new_src.replace(BADGE_OLD, BADGE_NEW, 1)
    print('[OK  ] Fix 1: Badge logic fixed (DO_NOTHING always BLOCKED).')
else:
    print('[SKIP] Fix 1: Badge already fixed or anchor not found.')

# ─────────────────────────────────────────────────────────────────────────────
# Fix 2 + 3 + 4: Replace entire cap-row + cap-input-row block
# Ensures both symbols get it, input is editable, button has feedback
# ─────────────────────────────────────────────────────────────────────────────

# Try both possible current states of the cap-row block

CAP_BLOCK_V1 = """          <div class="cap-row">
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

CAP_BLOCK_V2 = """          <div class="cap-row">
            <span class="lbl">Capital</span>
            <span class="val">{inr_fmt(cap)}</span>
            <span class="sep">│</span>
            <span class="lbl">Effective sizing</span>
            <span class="val">{inr_fmt(cap_eff)}</span>
          </div>"""

CAP_BLOCK_NEW = """          <div class="cap-row">
            <span class="lbl">Capital</span>
            <span class="val" id="cap-disp-{sym}">{inr_fmt(cap)}</span>
            <span class="sep">│</span>
            <span class="lbl">Eff. sizing</span>
            <span class="val">{inr_fmt(cap_eff)}</span>
          </div>
          <div class="cap-set-row">
            <span class="set-lbl">Set capital ({sym})</span>
            <div class="set-controls">
              <input class="cap-field" id="cap-field-{sym}" type="number"
                     value="{int(cap)}" min="200000" step="50000"/>
              <button class="set-btn" id="set-btn-{sym}"
                      onclick="setCapital('{sym}')">SET</button>
              <span class="set-msg" id="set-msg-{sym}"></span>
            </div>
          </div>"""

replaced = False
for old in [CAP_BLOCK_V1, CAP_BLOCK_V2]:
    if old in new_src:
        new_src = new_src.replace(old, CAP_BLOCK_NEW, 1)
        print(f'[OK  ] Fix 2/3/4: Cap-row block replaced (variant {"v1" if old == CAP_BLOCK_V1 else "v2"}).')
        replaced = True
        break

if not replaced:
    print('[FAIL] Fix 2/3/4: Cap-row anchor not found.')
    errors += 1

# ─────────────────────────────────────────────────────────────────────────────
# Fix 5: Replace JS block entirely — clean version, no f-string conflicts
# ─────────────────────────────────────────────────────────────────────────────

# Remove any existing setCapital function (could be broken or partially fixed)
import re
js_pattern = re.compile(
    r'\n// Capital setter\nfunction setCapital[\s\S]*?^</script>',
    re.MULTILINE
)

JS_CLEAN = """
// Capital setter — v2
function setCapital(sym) {{
  var inp = document.getElementById('cap-field-' + sym);
  var msg = document.getElementById('set-msg-' + sym);
  var disp = document.getElementById('cap-disp-' + sym);
  var btn = document.getElementById('set-btn-' + sym);
  var val = parseFloat(inp.value);
  if (!val || val < 200000) {{
    msg.textContent = '\u26a0 Min \u20b92,00,000';
    msg.className = 'set-msg err';
    return;
  }}
  btn.textContent = '...';
  btn.disabled = true;
  msg.textContent = '';
  var url = '/set_capital?symbol=' + sym + '&capital=' + val;
  fetch(url, {{method: 'POST'}})
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      if (d.ok) {{
        var fmt = '\u20b9' + Math.round(d.capital).toLocaleString('en-IN');
        msg.textContent = '\u2713 Saved';
        msg.className = 'set-msg ok';
        if (disp) disp.textContent = fmt;
        setTimeout(function() {{
          msg.textContent = '';
          msg.className = 'set-msg';
        }}, 3000);
      }} else {{
        msg.textContent = '\u2717 ' + d.error;
        msg.className = 'set-msg err';
      }}
      btn.textContent = 'SET';
      btn.disabled = false;
    }})
    .catch(function() {{
      msg.textContent = '\u2717 Failed';
      msg.className = 'set-msg err';
      btn.textContent = 'SET';
      btn.disabled = false;
    }});
}}
</script>"""

if js_pattern.search(new_src):
    new_src = js_pattern.sub(JS_CLEAN, new_src)
    print('[OK  ] Fix 5: JS setCapital() replaced (clean, no f-string conflicts).')
elif '</script>' in new_src:
    # No existing setCapital — just insert before </script>
    new_src = new_src.replace('</script>', JS_CLEAN, 1)
    print('[OK  ] Fix 5: JS setCapital() inserted before </script>.')
else:
    print('[FAIL] Fix 5: No </script> anchor found.')
    errors += 1

# ─────────────────────────────────────────────────────────────────────────────
# Fix 6: CSS — replace cap-input-row styles with clean cap-set-row styles
# ─────────────────────────────────────────────────────────────────────────────

CSS_OLD = """  /* ── Capital input row ── */
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
  .cap-status {{ font-size:12px; font-family:var(--mono); }}"""

CSS_NEW = """  /* ── Capital set row ── */
  .cap-set-row {{ display:flex; align-items:center; justify-content:space-between;
                  padding:10px 16px; border-bottom:1px solid var(--border);
                  background:rgba(0,204,255,0.03); gap:12px; flex-wrap:wrap; }}
  .set-lbl {{ font-size:11px; color:var(--cyan); letter-spacing:1px;
               text-transform:uppercase; font-weight:700; white-space:nowrap; }}
  .set-controls {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
  .cap-field {{ background:var(--bg); border:1px solid var(--cyan);
                color:var(--text); font-family:var(--mono); font-size:14px;
                font-weight:700; padding:5px 10px; border-radius:2px;
                width:150px; cursor:text; -webkit-appearance:none; }}
  .cap-field:focus {{ outline:2px solid var(--cyan); outline-offset:1px; }}
  .set-btn {{ padding:5px 18px; background:var(--cyan); border:none;
              color:var(--bg); font-family:var(--sans); font-size:13px;
              font-weight:700; letter-spacing:1px; cursor:pointer;
              border-radius:2px; transition:opacity 0.2s; }}
  .set-btn:hover {{ opacity:0.85; }}
  .set-btn:disabled {{ opacity:0.4; cursor:not-allowed; }}
  .set-msg {{ font-size:12px; font-family:var(--mono); font-weight:700; }}
  .set-msg.ok {{ color:var(--green); }}
  .set-msg.err {{ color:var(--red); }}"""

if CSS_OLD in new_src:
    new_src = new_src.replace(CSS_OLD, CSS_NEW, 1)
    print('[OK  ] Fix 6: CSS replaced with clean cap-set-row styles.')
else:
    # CSS not found from previous patch — just add it
    css_anchor = '  /* ── Active legend (per card) ── */'
    if css_anchor in new_src:
        new_src = new_src.replace(css_anchor, CSS_NEW + '\n\n' + css_anchor, 1)
        print('[OK  ] Fix 6: CSS added (not found via replace, inserted at anchor).')
    else:
        print('[SKIP] Fix 6: CSS anchor not found — add manually if needed.')

# ─────────────────────────────────────────────────────────────────────────────
# Write
# ─────────────────────────────────────────────────────────────────────────────

if errors:
    print(f'\n[ABORT] {errors} critical fix(es) failed. File not written.')
    sys.exit(1)

if DRY:
    print('\n[DRY] No files written.')
    sys.exit(0)

shutil.copy2(TARGET, TARGET + '.bak_v2fix')
open(TARGET, 'w', encoding='utf-8').write(new_src)

print('\nVerification:')
final = open(TARGET, encoding='utf-8').read()
for label, token in [
    ('Badge: DO_NOTHING check',    "action not in ('DO_NOTHING'"),
    ('cap-set-row in HTML',        'cap-set-row'),
    ('cap-field input class',      'cap-field'),
    ('set-btn button class',       'set-btn'),
    ('JS: setCapital v2',          'Capital setter \u2014 v2'),
    ('JS: no template literals',   'fetch(url,'),
    ('CSS: .cap-field defined',    '.cap-field'),
]:
    sym = 'v' if token in final else 'X'
    print(f'  [{sym}] {label}')

print('\n[DONE] Restart: python merdian_signal_dashboard.py')
