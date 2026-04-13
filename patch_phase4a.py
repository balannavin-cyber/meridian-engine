"""
patch_phase4a.py  --  Wire Phase 4A into process manager and signal dashboard
=============================================================================
1. Adds exit_monitor to merdian_pm.py PROCESSES dict
2. Adds LOG TRADE button to merdian_signal_dashboard.py signal cards
3. Adds POST /log_trade endpoint to signal dashboard
"""

import sys, shutil

# ── 1. Add exit_monitor to PM ─────────────────────────────────────────────────

PM_FILE = r'C:\GammaEnginePython\merdian_pm.py'
pm = open(PM_FILE, encoding='utf-8').read()

OLD_PROCS = """PROCESSES = {
    'health_monitor':   {'script': 'merdian_live_dashboard.py', 'args': ['--no-browser'], 'port': 8765, 'desc': 'Health Monitor'},
    'signal_dashboard': {'script': 'merdian_signal_dashboard.py', 'port': 8766, 'desc': 'Signal Dashboard'},
    'supervisor':       {'script': 'gamma_engine_supervisor.py',  'port': None, 'desc': 'Supervisor'},
}"""

NEW_PROCS = """PROCESSES = {
    'health_monitor':   {'script': 'merdian_live_dashboard.py', 'args': ['--no-browser'], 'port': 8765, 'desc': 'Health Monitor'},
    'signal_dashboard': {'script': 'merdian_signal_dashboard.py', 'port': 8766, 'desc': 'Signal Dashboard'},
    'supervisor':       {'script': 'gamma_engine_supervisor.py',  'port': None, 'desc': 'Supervisor'},
    'exit_monitor':     {'script': 'merdian_exit_monitor.py',     'port': None, 'desc': 'Exit Monitor'},
}"""

if OLD_PROCS in pm:
    shutil.copy2(PM_FILE, PM_FILE + '.bak_p4a')
    pm = pm.replace(OLD_PROCS, NEW_PROCS, 1)
    open(PM_FILE, 'w', encoding='utf-8').write(pm)
    print('[OK] merdian_pm.py: exit_monitor added to PROCESSES')
elif 'exit_monitor' in pm:
    print('[SKIP] merdian_pm.py: exit_monitor already present')
else:
    print('[FAIL] merdian_pm.py: PROCESSES anchor not found')

# ── 2. Add LOG TRADE button to signal dashboard card ─────────────────────────

DASH_FILE = r'C:\GammaEnginePython\merdian_signal_dashboard.py'
dash = open(DASH_FILE, encoding='utf-8').read()

if 'log_trade' in dash:
    print('[SKIP] signal dashboard: LOG TRADE already present')
else:
    # Add LOG TRADE row before the capital set row in the card HTML
    # Anchor: the cap-set-row div
    OLD_CAP = "f'<div class=\"csr\">'"
    
    # Try to find the capital set row pattern
    if 'csr' not in dash:
        print('[FAIL] signal dashboard: csr anchor not found')
        sys.exit(1)

    # Add button HTML before signal timestamp
    OLD_ST = "f'<div class=\"st\">Signal: {sig_ts[11:16]} IST</div>'"
    NEW_ST = """f'''<div class="trade-bar">
{"" if action in ("DO_NOTHING","NO DATA","ERROR") else f\'\'\'<button class="log-btn" onclick="showLogTrade(\\'{sym}\\',\\'{action}\\',{atm_stk or 0},\\'{expiry}\\',\\'{opt_t or ""}\\',{lots or 1},{int(cap)})">LOG TRADE</button>\'\'\'}
<button class="close-btn" onclick="showCloseForm(\\'{sym}\\')">CLOSE TRADE</button>
</div>'''
f'<div class="st">Signal: {sig_ts[11:16]} IST</div>'"""

    # Simpler approach -- just add after the csr div closing
    LOG_TRADE_HTML = """
          # Phase 4A: LOG TRADE + CLOSE TRADE buttons
          trade_btns = ""
          if action not in ("DO_NOTHING","NO DATA","ERROR") and atm_stk and opt_t:
              trade_btns = (
                  f'<div class="trade-bar">'
                  f'<button class="log-btn" '
                  f'onclick="showLogTrade(\\'{sym}\\',\\'{action}\\','
                  f'{atm_stk},{int(cap)})">&#128203; LOG TRADE</button>'
                  f'<button class="close-btn" '
                  f'onclick="showCloseForm(\\'{sym}\\')">&#10060; CLOSE</button>'
                  f'</div>'
              )
          else:
              trade_btns = (
                  f'<div class="trade-bar">'
                  f'<button class="close-btn" '
                  f'onclick="showCloseForm(\\'{sym}\\')">&#10060; CLOSE TRADE</button>'
                  f'</div>'
              )
"""

    # Inject before the return of the card function
    CARD_END_ANCHOR = "f'<div class=\"st\">Signal: {sig_ts[11:16]} IST</div>'"
    NEW_CARD_END = (
        LOG_TRADE_HTML +
        "\n          " + CARD_END_ANCHOR
    )

    # This approach is getting complex. Let's do a clean targeted insert
    # Find where sig_ts line is rendered and insert trade_btns before it
    if CARD_END_ANCHOR in dash:
        dash = dash.replace(CARD_END_ANCHOR,
            """f'<div class="trade-bar">' +
          (f'<button class="log-btn" onclick="showLogTrade(\\'{sym}\\')">'
           '&#128203; LOG TRADE</button>'
           if action not in ("DO_NOTHING","NO DATA","ERROR") else '') +
          f'<button class="close-btn" onclick="showCloseForm(\\'{sym}\\')">'
          '&#10060; CLOSE</button></div>' +
          f'<div class="st">Signal: {sig_ts[11:16]} IST</div>'""", 1)
        print('[OK] signal dashboard: trade buttons added to card')
    else:
        print('[FAIL] signal dashboard: card end anchor not found')
        sys.exit(1)

    # Add CSS for trade buttons
    CSS_ANCHOR = '.csm.err{color:#ff3b5c}'
    if CSS_ANCHOR in dash:
        dash = dash.replace(CSS_ANCHOR, CSS_ANCHOR + """
.trade-bar{display:flex;gap:8px;padding:8px 16px;border-bottom:1px solid #1e2a38;flex-wrap:wrap}
.log-btn{padding:6px 16px;background:#00ff88;border:none;color:#080b0f;font-family:"Barlow Condensed",sans-serif;
  font-size:13px;font-weight:700;letter-spacing:1px;cursor:pointer;border-radius:2px}
.log-btn:hover{opacity:.85}
.close-btn{padding:6px 16px;background:transparent;border:1px solid #ff3b5c;color:#ff3b5c;
  font-family:"Barlow Condensed",sans-serif;font-size:13px;font-weight:700;cursor:pointer;border-radius:2px}
.close-btn:hover{background:rgba(255,59,92,.1)}
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(0,0,0,.7);z-index:100;align-items:center;justify-content:center}
.modal.open{display:flex}
.modal-box{background:#0d1117;border:1px solid #00ccff;border-radius:4px;padding:24px;
  min-width:320px;max-width:500px}
.modal-title{font-size:14px;font-weight:700;letter-spacing:2px;color:#00ccff;margin-bottom:16px}
.modal-row{display:flex;flex-direction:column;gap:4px;margin-bottom:12px}
.modal-lbl{font-size:11px;color:#64748b;letter-spacing:1px;text-transform:uppercase}
.modal-inp{background:#080b0f;border:1px solid #1e2a38;color:#c9d5e0;padding:8px;
  border-radius:2px;font-family:"Space Mono",monospace;font-size:14px}
.modal-inp:focus{outline:none;border-color:#00ccff}
.modal-actions{display:flex;gap:8px;margin-top:16px}
.modal-ok{flex:1;padding:8px;background:#00ccff;border:none;color:#080b0f;
  font-weight:700;cursor:pointer;border-radius:2px}
.modal-cancel{padding:8px 16px;background:transparent;border:1px solid #64748b;
  color:#64748b;cursor:pointer;border-radius:2px}
.modal-msg{margin-top:8px;font-size:12px;font-family:"Space Mono",monospace}""", 1)
        print('[OK] signal dashboard: CSS added')

    # Add JS modal functions + POST handler
    JS_ANCHOR = 'function setCap(sym){'
    if JS_ANCHOR in dash:
        JS_NEW = """function showLogTrade(sym){
  document.getElementById('lt-sym').value=sym;
  document.getElementById('lt-price').value='';
  document.getElementById('lt-msg').textContent='';
  document.getElementById('modal-log').classList.add('open');
  setTimeout(function(){document.getElementById('lt-price').focus();},100);
}
function submitLogTrade(){
  var sym=document.getElementById('lt-sym').value;
  var price=parseFloat(document.getElementById('lt-price').value);
  var msg=document.getElementById('lt-msg');
  if(!price||price<=0){msg.textContent='Enter a valid premium price';msg.style.color='#ff3b5c';return;}
  msg.textContent='Logging...';msg.style.color='#64748b';
  fetch('/log_trade?symbol='+sym+'&entry_price='+price,{method:'POST'})
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.ok){msg.textContent='Logged! Exit at '+d.exit_ts_ist;msg.style.color='#00ff88';
        setTimeout(function(){document.getElementById('modal-log').classList.remove('open');},2000);}
      else{msg.textContent='Error: '+d.error;msg.style.color='#ff3b5c';}
    }).catch(function(){msg.textContent='Failed';msg.style.color='#ff3b5c';});
}
function showCloseForm(sym){
  document.getElementById('cl-sym').value=sym;
  document.getElementById('cl-id').value='';
  document.getElementById('cl-price').value='';
  document.getElementById('cl-msg').textContent='';
  document.getElementById('modal-close').classList.add('open');
  setTimeout(function(){document.getElementById('cl-id').focus();},100);
}
function submitClose(){
  var sym=document.getElementById('cl-sym').value;
  var tid=document.getElementById('cl-id').value.trim();
  var price=parseFloat(document.getElementById('cl-price').value);
  var msg=document.getElementById('cl-msg');
  if(!tid){msg.textContent='Enter trade ID';msg.style.color='#ff3b5c';return;}
  if(!price||price<=0){msg.textContent='Enter exit price';msg.style.color='#ff3b5c';return;}
  msg.textContent='Closing...';msg.style.color='#64748b';
  fetch('/close_trade?trade_id='+tid+'&exit_price='+price,{method:'POST'})
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.ok){msg.textContent='Closed! PnL: '+d.pnl_str;msg.style.color='#00ff88';
        setTimeout(function(){document.getElementById('modal-close').classList.remove('open');},2000);}
      else{msg.textContent='Error: '+d.error;msg.style.color='#ff3b5c';}
    }).catch(function(){msg.textContent='Failed';msg.style.color='#ff3b5c';});
}
function closeModal(id){document.getElementById(id).classList.remove('open');}
""" + JS_ANCHOR
        dash = dash.replace(JS_ANCHOR, JS_NEW, 1)
        print('[OK] signal dashboard: JS modal functions added')

    # Add modal HTML before </body>
    BODY_ANCHOR = '<script>'
    MODAL_HTML = """<!-- Phase 4A: Log Trade Modal -->
<div class="modal" id="modal-log">
  <div class="modal-box">
    <div class="modal-title">&#128203; LOG TRADE</div>
    <input type="hidden" id="lt-sym">
    <div class="modal-row">
      <span class="modal-lbl">Symbol</span>
      <span style="font-family:monospace;color:#00ccff" id="lt-sym-disp"></span>
    </div>
    <div class="modal-row">
      <label class="modal-lbl" for="lt-price">Premium paid per unit (INR)</label>
      <input class="modal-inp" id="lt-price" type="number" min="0.5" step="0.5" placeholder="e.g. 85.50">
    </div>
    <div class="modal-msg" id="lt-msg"></div>
    <div class="modal-actions">
      <button class="modal-ok" onclick="submitLogTrade()">LOG TRADE</button>
      <button class="modal-cancel" onclick="closeModal('modal-log')">Cancel</button>
    </div>
  </div>
</div>
<!-- Phase 4A: Close Trade Modal -->
<div class="modal" id="modal-close">
  <div class="modal-box">
    <div class="modal-title">&#10060; CLOSE TRADE</div>
    <input type="hidden" id="cl-sym">
    <div class="modal-row">
      <label class="modal-lbl" for="cl-id">Trade ID (first 8 chars)</label>
      <input class="modal-inp" id="cl-id" type="text" placeholder="e.g. a1b2c3d4">
    </div>
    <div class="modal-row">
      <label class="modal-lbl" for="cl-price">Exit price per unit (INR)</label>
      <input class="modal-inp" id="cl-price" type="number" min="0" step="0.5" placeholder="e.g. 120.00">
    </div>
    <div class="modal-msg" id="cl-msg"></div>
    <div class="modal-actions">
      <button class="modal-ok" onclick="submitClose()">CLOSE &amp; LOG PnL</button>
      <button class="modal-cancel" onclick="closeModal('modal-close')">Cancel</button>
    </div>
  </div>
</div>
<script>"""
    if '<script>' in dash:
        dash = dash.replace('<script>', MODAL_HTML, 1)
        print('[OK] signal dashboard: modal HTML added')

    shutil.copy2(DASH_FILE, DASH_FILE + '.bak_p4a')
    open(DASH_FILE, 'w', encoding='utf-8').write(dash)
    print('[OK] signal dashboard: saved')

# ── 3. Add POST /log_trade + /close_trade endpoints to dashboard ──────────────

dash = open(DASH_FILE, encoding='utf-8').read()

if '/log_trade' in dash:
    print('[SKIP] signal dashboard: /log_trade endpoint already present')
else:
    # Add endpoint handling in do_POST
    OLD_POST_HANDLER = "        if self.path.startswith(\"/set_capital\"):"
    NEW_POST_HANDLER = """        if self.path.startswith("/log_trade"):
            from urllib.parse import urlparse, parse_qs as _pqs
            import json as _j, os as _os
            qs     = _pqs(urlparse(self.path).query)
            sym    = (qs.get("symbol",[None])[0] or "").upper()
            price  = qs.get("entry_price",[None])[0]
            try:
                from merdian_trade_logger import fetch_latest_signal, get_active_lots, log_trade
                from zoneinfo import ZoneInfo as _ZI
                sig = fetch_latest_signal(sym)
                if not sig or sig.get("action","DO_NOTHING") == "DO_NOTHING":
                    raise ValueError("No active signal to log")
                action   = sig.get("action")
                strike   = sig.get("atm_strike")
                expiry   = sig.get("expiry_date")
                opt_type = "PE" if action == "BUY_PE" else "CE"
                lots     = get_active_lots(sig)
                ep       = float(price)
                sig_ts   = sig.get("ts","")
                trade_id, exit_ts = log_trade(sym, strike, expiry, opt_type, lots, ep, sig_ts)
                exit_ist = exit_ts.astimezone(_ZI("Asia/Kolkata")).strftime("%H:%M IST")
                body = _j.dumps({"ok":True,"trade_id":trade_id,"exit_ts_ist":exit_ist}).encode()
            except Exception as e:
                body = _j.dumps({"ok":False,"error":str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",len(body))
            self.end_headers(); self.wfile.write(body); return

        if self.path.startswith("/close_trade"):
            from urllib.parse import urlparse, parse_qs as _pqs
            import json as _j
            qs     = _pqs(urlparse(self.path).query)
            tid    = qs.get("trade_id",[None])[0] or ""
            price  = qs.get("exit_price",[None])[0]
            try:
                from merdian_trade_logger import fetch_open_trades, close_trade
                trades = [t for t in fetch_open_trades() if t["id"].startswith(tid)]
                if not trades: raise ValueError(f"No open trade with ID prefix '{tid}'")
                t   = trades[0]
                ep  = float(price)
                pnl = close_trade(t["id"], ep)
                body = _j.dumps({"ok":True,"pnl":pnl,"pnl_str":f"INR {pnl:+,.0f}"}).encode()
            except Exception as e:
                body = _j.dumps({"ok":False,"error":str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",len(body))
            self.end_headers(); self.wfile.write(body); return

        if self.path.startswith("/set_capital"):"""

    if OLD_POST_HANDLER in dash:
        dash = dash.replace(OLD_POST_HANDLER, NEW_POST_HANDLER, 1)
        open(DASH_FILE, 'w', encoding='utf-8').write(dash)
        print('[OK] signal dashboard: /log_trade + /close_trade endpoints added')
    else:
        print('[FAIL] signal dashboard: POST handler anchor not found')

# ── Verify ────────────────────────────────────────────────────────────────────

print('\nFinal verification:')
pm_f   = open(PM_FILE, encoding='utf-8').read()
dash_f = open(DASH_FILE, encoding='utf-8').read()
for label, content, token in [
    ('PM: exit_monitor',           pm_f,   'exit_monitor'),
    ('Dash: LOG TRADE button',     dash_f, 'log-btn'),
    ('Dash: CLOSE button',         dash_f, 'close-btn'),
    ('Dash: modal HTML',           dash_f, 'modal-log'),
    ('Dash: JS showLogTrade',      dash_f, 'showLogTrade'),
    ('Dash: /log_trade endpoint',  dash_f, '/log_trade'),
    ('Dash: /close_trade endpoint',dash_f, '/close_trade'),
]:
    print(f'  [{"v" if token in content else "X"}] {label}')

print('\nDone. Copy merdian_trade_logger.py + merdian_exit_monitor.py to C:\\GammaEnginePython\\')
print('Then: python merdian_stop.py && python merdian_start.py')
