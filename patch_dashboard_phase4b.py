#!/usr/bin/env python3
"""
patch_dashboard_phase4b.py
===========================
Patches merdian_signal_dashboard.py for Phase 4B:

1. Adds missing /log_trade POST endpoint (manual price entry — Phase 4A)
2. Adds missing /close_trade POST endpoint (manual exit — Phase 4A)
3. Adds /place_order POST endpoint (relays to AWS order placer — Phase 4B)
4. Adds /square_off POST endpoint (relays to AWS order placer — Phase 4B)
5. Adds PLACE ORDER button to signal card
6. Adds PLACE ORDER modal + JS

AWS order placer URL: configure AWS_ORDER_PLACER_URL in .env
    AWS_ORDER_PLACER_URL=http://13.63.27.85:8767

Safe: creates .bak_phase4b backup before patching.
Idempotent: checks for patch marker before applying.
"""
import shutil
from pathlib import Path

TARGET = Path("merdian_signal_dashboard.py")
BACKUP = Path("merdian_signal_dashboard.py.bak_phase4b")

# ── New Handler endpoints to insert ──────────────────────────────────────────
# Inserted into do_POST, before the final else clause

NEW_ENDPOINTS = '''\
        elif self.path.startswith("/log_trade"):
            # Phase 4A: manual trade log (entry price provided by operator)
            qs   = parse_qs(urlparse(self.path).query)
            sym  = (qs.get("symbol",      [None])[0] or "").upper()
            price = qs.get("entry_price", [None])[0]
            try:
                if not sym or not price:
                    raise ValueError("symbol and entry_price required")
                from merdian_trade_logger import (
                    fetch_latest_signal, get_active_lots, log_trade, LOT_SIZE
                )
                sig = fetch_latest_signal(sym)
                if not sig:
                    raise ValueError(f"No signal for {sym}")
                strike     = sig.get("atm_strike")
                expiry     = sig.get("expiry_date")
                option_type = "PE" if sig.get("action") == "BUY_PE" else "CE"
                lots       = get_active_lots(sig)
                sig_ts     = sig.get("ts", "")
                entry_price = float(price)
                trade_id, exit_ts = log_trade(
                    sym, strike, expiry, option_type, lots, entry_price, sig_ts
                )
                from zoneinfo import ZoneInfo as _ZI
                exit_ist = exit_ts.astimezone(_ZI("Asia/Kolkata")).strftime("%H:%M IST")
                body = json.dumps({"ok": True, "trade_id": trade_id, "exit_ts_ist": exit_ist}).encode()
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif self.path.startswith("/close_trade"):
            # Phase 4A: manual trade close (exit price provided by operator)
            qs   = parse_qs(urlparse(self.path).query)
            tid  = qs.get("trade_id",   [None])[0]
            price = qs.get("exit_price", [None])[0]
            try:
                if not tid or not price:
                    raise ValueError("trade_id and exit_price required")
                from merdian_trade_logger import close_trade as _close, LOT_SIZE
                pnl = _close(tid, float(price))
                pnl_str = f"INR {pnl:+,.0f}" if pnl is not None else "N/A"
                body = json.dumps({"ok": True, "pnl": pnl, "pnl_str": pnl_str}).encode()
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif self.path.startswith("/place_order"):
            # Phase 4B: automated order placement via AWS order placer
            import os as _os
            import requests as _req
            qs  = parse_qs(urlparse(self.path).query)
            sym = (qs.get("symbol", [None])[0] or "").upper()
            aws_url = _os.getenv("AWS_ORDER_PLACER_URL", "http://13.63.27.85:8767").rstrip("/")
            try:
                if not sym:
                    raise ValueError("symbol required")
                # Get latest signal to extract order params
                sig = fetch_signal(sym)
                if not sig:
                    raise ValueError(f"No signal for {sym}")
                action = sig.get("action", "DO_NOTHING")
                if action not in ("BUY_PE", "BUY_CE"):
                    raise ValueError(f"Signal is {action} — nothing to place")
                strike     = sig.get("atm_strike")
                expiry     = str(sig.get("expiry_date", ""))[:10]
                option_type = "PE" if action == "BUY_PE" else "CE"
                tier       = sig.get("ict_tier", "TIER3")
                lots_key   = {"TIER1": "ict_lots_t1", "TIER2": "ict_lots_t2"}.get(tier, "ict_lots_t3")
                lots       = sig.get(lots_key) or sig.get("ict_lots_t1") or 1
                signal_ts  = sig.get("ts", "")
                # Relay to AWS order placer
                relay_url = (
                    f"{aws_url}/place_order"
                    f"?symbol={sym}&strike={strike}&expiry_date={expiry}"
                    f"&option_type={option_type}&lots={lots}&signal_ts={signal_ts}"
                )
                r = _req.post(relay_url, timeout=60)
                result = r.json()
                body = json.dumps(result).encode()
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif self.path.startswith("/square_off"):
            # Phase 4B: automated square off via AWS order placer
            import os as _os
            import requests as _req
            qs           = parse_qs(urlparse(self.path).query)
            trade_log_id = qs.get("trade_log_id", [None])[0]
            aws_url      = _os.getenv("AWS_ORDER_PLACER_URL", "http://13.63.27.85:8767").rstrip("/")
            try:
                if not trade_log_id:
                    raise ValueError("trade_log_id required")
                relay_url = f"{aws_url}/square_off?trade_log_id={trade_log_id}"
                r = _req.post(relay_url, timeout=60)
                result = r.json()
                body = json.dumps(result).encode()
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

'''

# ── PLACE ORDER button — injected into card trade-bar ────────────────────────
# Inserts before the existing LOG TRADE button

OLD_TRADE_BAR = (
    "        f'<div class=\"trade-bar\">' +\n"
    "          (f'<button class=\"log-btn\" onclick=\"showLogTrade(\\'{sym}\\')\">'\n"
    "           '&#128203; LOG TRADE</button>'\n"
    "           if action not in (\"DO_NOTHING\",\"NO DATA\",\"ERROR\") else '') +\n"
    "          f'<button class=\"close-btn\" onclick=\"showCloseForm(\\'{sym}\\')\">'\n"
    "          '&#10060; CLOSE</button></div>' +"
)

NEW_TRADE_BAR = (
    "        f'<div class=\"trade-bar\">' +\n"
    "          (f'<button class=\"place-btn\" onclick=\"showPlaceOrder(\\'{sym}\\')\">'\n"
    "           '&#9889; PLACE ORDER</button>'\n"
    "           if action not in (\"DO_NOTHING\",\"NO DATA\",\"ERROR\") else '') +\n"
    "          (f'<button class=\"log-btn\" onclick=\"showLogTrade(\\'{sym}\\')\">'\n"
    "           '&#128203; LOG MANUAL</button>'\n"
    "           if action not in (\"DO_NOTHING\",\"NO DATA\",\"ERROR\") else '') +\n"
    "          f'<button class=\"close-btn\" onclick=\"showCloseForm(\\'{sym}\\')\">'\n"
    "          '&#10060; SQUARE OFF</button></div>' +"
)

# ── CSS for PLACE ORDER button ────────────────────────────────────────────────

OLD_CSS_ANCHOR = ".log-btn{padding:6px 16px;background:#00ff88;"

NEW_CSS = """\
.place-btn{padding:6px 18px;background:#ffaa00;border:none;color:#080b0f;font-family:"Barlow Condensed",sans-serif;
  font-size:13px;font-weight:700;letter-spacing:1px;cursor:pointer;border-radius:2px;margin-right:4px}
.place-btn:hover{opacity:.85}
"""

# ── JS for PLACE ORDER modal ──────────────────────────────────────────────────

OLD_JS_ANCHOR = "function showLogTrade(sym){"

NEW_JS = """\
function showPlaceOrder(sym){
  document.getElementById('po-sym').value=sym;
  document.getElementById('po-sym-disp').textContent=sym;
  document.getElementById('po-msg').textContent='';
  document.getElementById('modal-place').classList.add('open');
}
function submitPlaceOrder(){
  var sym=document.getElementById('po-sym').value;
  var msg=document.getElementById('po-msg');
  msg.textContent='Placing order...';msg.style.color='#ffaa00';
  fetch('/place_order?symbol='+sym,{method:'POST'})
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.ok){
        msg.textContent='FILLED @ INR '+d.fill_price+' | Exit: '+d.exit_ts_ist;
        msg.style.color='#00ff88';
        setTimeout(function(){document.getElementById('modal-place').classList.remove('open');},3000);
      }else{msg.textContent='ERROR: '+d.error;msg.style.color='#ff3b5c';}
    }).catch(function(){msg.textContent='Request failed';msg.style.color='#ff3b5c';});
}
"""

# ── PLACE ORDER modal HTML ────────────────────────────────────────────────────

OLD_MODAL_ANCHOR = "<!-- Phase 4A: Log Trade Modal -->"

NEW_MODAL = """\
<!-- Phase 4B: Place Order Modal -->
<div class="modal" id="modal-place">
  <div class="modal-box">
    <div class="modal-title">&#9889; PLACE ORDER — DHAN AUTO</div>
    <input type="hidden" id="po-sym">
    <div class="modal-row">
      <span class="modal-lbl">Symbol</span>
      <span style="font-family:monospace;color:#ffaa00;font-size:18px;font-weight:700" id="po-sym-disp"></span>
    </div>
    <div style="padding:8px 0;font-size:12px;color:#64748b">
      Market order will be placed at current ATM strike, tier lots, intraday.<br>
      T+30m exit alert will fire automatically.
    </div>
    <div class="modal-msg" id="po-msg"></div>
    <div class="modal-actions">
      <button class="modal-ok" style="background:#ffaa00" onclick="submitPlaceOrder()">CONFIRM PLACE ORDER</button>
      <button class="modal-cancel" onclick="closeModal('modal-place')">Cancel</button>
    </div>
  </div>
</div>
"""

# ── Handler anchor — insert new endpoints before the final else ───────────────

OLD_HANDLER_ANCHOR = "        else:\n            self.send_response(404); self.end_headers()"
NEW_HANDLER = NEW_ENDPOINTS + "        else:\n            self.send_response(404); self.end_headers()"


def main():
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found. Run from C:\\GammaEnginePython\\")
        return 1

    source = TARGET.read_text(encoding="utf-8")

    if "Phase 4B" in source and "place_order" in source and "square_off" in source:
        print("Patch already applied — no changes made.")
        return 0

    # Check anchors
    errors = []
    for name, anchor in [
        ("Handler anchor", OLD_HANDLER_ANCHOR),
        ("Trade bar",      OLD_TRADE_BAR),
        ("CSS anchor",     OLD_CSS_ANCHOR),
        ("JS anchor",      OLD_JS_ANCHOR),
        ("Modal anchor",   OLD_MODAL_ANCHOR),
    ]:
        if anchor not in source:
            errors.append(f"  MISSING: {name}")

    if errors:
        print("ERROR: Some anchors not found:")
        for e in errors:
            print(e)
        print("File may have changed. Review manually.")
        return 1

    # Backup
    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    # Apply patches in order
    patched = source

    # 1. Handler endpoints
    patched = patched.replace(OLD_HANDLER_ANCHOR, NEW_HANDLER, 1)

    # 2. Trade bar buttons
    patched = patched.replace(OLD_TRADE_BAR, NEW_TRADE_BAR, 1)

    # 3. CSS
    patched = patched.replace(OLD_CSS_ANCHOR, NEW_CSS + OLD_CSS_ANCHOR, 1)

    # 4. JS
    patched = patched.replace(OLD_JS_ANCHOR, NEW_JS + OLD_JS_ANCHOR, 1)

    # 5. Modal HTML
    patched = patched.replace(OLD_MODAL_ANCHOR, NEW_MODAL + "\n" + OLD_MODAL_ANCHOR, 1)

    TARGET.write_text(patched, encoding="utf-8")

    # Verify
    result = TARGET.read_text(encoding="utf-8")
    checks = [
        ("place_order endpoint",  "/place_order" in result),
        ("square_off endpoint",   "/square_off"  in result),
        ("log_trade endpoint",    "/log_trade"   in result),
        ("close_trade endpoint",  "/close_trade" in result),
        ("PLACE ORDER button",    "place-btn"    in result),
        ("PLACE ORDER modal",     "modal-place"  in result),
    ]

    all_ok = True
    for name, ok in checks:
        status = "OK" if ok else "MISSING"
        print(f"  {status}: {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print(f"\nPatched: {TARGET}")
        print("\nAlso add to .env:")
        print("  AWS_ORDER_PLACER_URL=http://13.63.27.85:8767")
        return 0
    else:
        print("\nERROR: Verification failed — restoring backup.")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
