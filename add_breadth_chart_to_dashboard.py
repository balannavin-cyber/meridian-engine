#!/usr/bin/env python3
"""
add_breadth_chart_to_dashboard.py
===================================
Adds a market breadth line chart to merdian_signal_dashboard.py.

Inserts:
1. fetch_breadth_history() after the other fetch functions
2. Breadth chart CSS in CSS block
3. Breadth chart HTML+JS in render() before </div> closing .main
"""
import shutil
from pathlib import Path

TARGET = Path("merdian_signal_dashboard.py")
BACKUP = Path("merdian_signal_dashboard.py.bak_breadth_chart")

# ── 1. New fetch function ─────────────────────────────────────────────────────

OLD_FETCH_ANCHOR = "def eff_cap(c):"

NEW_FETCH = '''def fetch_breadth_history():
    """Fetch today's breadth time series from breadth_intraday_history."""
    today = str(date.today())
    r = _q(lambda: sb.table("breadth_intraday_history")
        .select("ts,advances,declines,breadth_score,coverage_pct")
        .eq("trade_date", today)
        .order("ts", desc=False)
        .limit(100)
        .execute().data)
    return r or []

def eff_cap(c):'''

# ── 2. New CSS ────────────────────────────────────────────────────────────────

OLD_CSS_ANCHOR = ".footer{text-align:center;"

NEW_CSS = """.breadth-panel{background:#0d1117;border:1px solid #1e2a38;border-radius:4px;
  grid-column:1/-1;padding:16px 20px}
.bp-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.bp-title{font-size:11px;letter-spacing:2px;color:#64748b;text-transform:uppercase;font-weight:700}
.bp-stats{display:flex;gap:20px;font-family:'Space Mono',monospace;font-size:13px}
.bp-adv{color:#00ff88;font-weight:700}
.bp-dec{color:#ff3b5c;font-weight:700}
.bp-score{color:#ffaa00;font-weight:700}
.bp-cov{color:#64748b;font-size:11px}
.bp-canvas-wrap{position:relative;height:140px}
canvas#breadth-chart{width:100%;height:140px}
.bp-nodata{color:#64748b;font-size:12px;font-style:italic;text-align:center;padding:40px 0}
.footer{text-align:center;"""

# ── 3. New HTML in render() ───────────────────────────────────────────────────

OLD_RENDER_ANCHOR = "  {cards}\n  <div class=\"rules\">"

NEW_RENDER = """  {cards}
  {breadth_html}
  <div class="rules">"""

# Breadth HTML template (built in render())
BREADTH_PANEL_CODE = '''
def breadth_panel(rows):
    if not rows:
        return \'\'\'<div class="breadth-panel">
          <div class="bp-header"><span class="bp-title">Market Breadth &#8212; 1,385 Stocks (NSE)</span>
          <span class="bp-cov">No data &#8212; WebSocket starting or market closed</span></div>
          <div class="bp-nodata">Breadth data will appear after first pipeline cycle (~09:20 IST)</div>
        </div>\'\'\'

    latest = rows[-1]
    adv = latest.get("advances", 0) or 0
    dec = latest.get("declines", 0) or 0
    score = latest.get("breadth_score", 0) or 0
    cov = latest.get("coverage_pct", 0) or 0

    score_col = "#00ff88" if score > 20 else "#ff3b5c" if score < -20 else "#ffaa00"
    regime = "BULLISH" if score > 20 else "BEARISH" if score < -20 else "NEUTRAL"

    # Build data arrays for JS
    times = []
    advs  = []
    decs  = []
    for row in rows:
        try:
            from datetime import datetime, timezone
            from zoneinfo import ZoneInfo
            ts = datetime.fromisoformat(row["ts"].replace("Z","+00:00"))
            ts_ist = ts.astimezone(ZoneInfo("Asia/Kolkata"))
            times.append(ts_ist.strftime("%H:%M"))
            advs.append(row.get("advances") or 0)
            decs.append(row.get("declines") or 0)
        except:
            pass

    import json as _json
    t_json = _json.dumps(times)
    a_json = _json.dumps(advs)
    d_json = _json.dumps(decs)

    return f\'\'\'<div class="breadth-panel">
      <div class="bp-header">
        <span class="bp-title">&#9632; Market Breadth &#8212; NSE Universe</span>
        <div class="bp-stats">
          <span class="bp-adv">&#9650; {adv:,} ADV</span>
          <span class="bp-dec">&#9660; {dec:,} DEC</span>
          <span class="bp-score" style="color:{score_col}">{regime} ({score:+.0f})</span>
          <span class="bp-cov">COV {cov:.0f}%</span>
        </div>
      </div>
      <div class="bp-canvas-wrap">
        <canvas id="breadth-chart"></canvas>
      </div>
      <script>
      (function(){{
        var times={t_json},advs={a_json},decs={d_json};
        var c=document.getElementById("breadth-chart");
        if(!c||!times.length)return;
        c.width=c.parentElement.offsetWidth;c.height=140;
        var ctx=c.getContext("2d");
        var W=c.width,H=c.height,PAD={{t:10,r:60,b:24,l:50}};
        var pw=W-PAD.l-PAD.r,ph=H-PAD.t-PAD.b;
        var maxV=Math.max(Math.max.apply(null,advs),Math.max.apply(null,decs),100);
        function px(i){{return PAD.l+i*(pw/(times.length-1||1));}}
        function py(v){{return PAD.t+ph-(v/maxV)*ph;}}
        // Grid
        ctx.strokeStyle="#1e2a38";ctx.lineWidth=1;
        var steps=[0,Math.round(maxV/2),maxV];
        steps.forEach(function(v){{
          var y=py(v);
          ctx.beginPath();ctx.moveTo(PAD.l,y);ctx.lineTo(W-PAD.r,y);ctx.stroke();
          ctx.fillStyle="#4a5568";ctx.font="10px 'Space Mono',monospace";
          ctx.textAlign="right";ctx.fillText(v,PAD.l-4,y+4);
        }});
        // X axis labels — show every Nth
        var step=Math.max(1,Math.floor(times.length/8));
        ctx.fillStyle="#4a5568";ctx.font="10px 'Space Mono',monospace";ctx.textAlign="center";
        times.forEach(function(t,i){{
          if(i%step===0||i===times.length-1){{
            ctx.fillText(t,px(i),H-4);
          }}
        }});
        // Declines line (red)
        ctx.beginPath();ctx.strokeStyle="#ff3b5c";ctx.lineWidth=2;ctx.lineJoin="round";
        decs.forEach(function(v,i){{i===0?ctx.moveTo(px(i),py(v)):ctx.lineTo(px(i),py(v));}});
        ctx.stroke();
        // Advances line (green)
        ctx.beginPath();ctx.strokeStyle="#00ff88";ctx.lineWidth=2;ctx.lineJoin="round";
        advs.forEach(function(v,i){{i===0?ctx.moveTo(px(i),py(v)):ctx.lineTo(px(i),py(v));}});
        ctx.stroke();
        // Legend
        ctx.fillStyle="#00ff88";ctx.fillRect(W-PAD.r+4,PAD.t,10,2);
        ctx.fillStyle="#c9d5e0";ctx.font="10px 'Barlow Condensed',sans-serif";
        ctx.textAlign="left";ctx.fillText("ADV",W-PAD.r+18,PAD.t+4);
        ctx.fillStyle="#ff3b5c";ctx.fillRect(W-PAD.r+4,PAD.t+14,10,2);
        ctx.fillStyle="#c9d5e0";ctx.fillText("DEC",W-PAD.r+18,PAD.t+18);
      }})();
      </script>
    </div>\'\'\'
'''

# ── 4. Wire breadth_panel into render() ──────────────────────────────────────

OLD_RENDER_BUILD = "    cards = \"\\n\".join(card(sigs[s]) for s in SYMBOLS)"

NEW_RENDER_BUILD = '''    cards = "\\n".join(card(sigs[s]) for s in SYMBOLS)
    try:
        breadth_rows = fetch_breadth_history()
        breadth_html = breadth_panel(breadth_rows)
    except Exception:
        breadth_html = ""'''


def main():
    source = TARGET.read_text(encoding="utf-8")

    if "breadth_panel" in source:
        print("Breadth chart already applied.")
        return 0

    errors = []
    for name, anchor in [
        ("fetch_breadth_history anchor", OLD_FETCH_ANCHOR),
        ("CSS footer anchor", OLD_CSS_ANCHOR),
        ("render cards line", OLD_RENDER_BUILD),
    ]:
        if anchor not in source:
            errors.append(f"MISSING: {name}")

    if errors:
        print("ERROR: anchors not found:")
        for e in errors:
            print(f"  {e}")
        return 1

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    patched = source

    # 1. Add fetch function
    patched = patched.replace(OLD_FETCH_ANCHOR, NEW_FETCH, 1)

    # 2. Add CSS
    patched = patched.replace(OLD_CSS_ANCHOR, NEW_CSS, 1)

    # 3. Add breadth_panel function before render()
    patched = patched.replace(
        "def render():",
        BREADTH_PANEL_CODE + "\ndef render():",
        1
    )

    # 4. Wire into render() build section
    patched = patched.replace(OLD_RENDER_BUILD, NEW_RENDER_BUILD, 1)

    # 5. Add {breadth_html} into the HTML template
    patched = patched.replace(
        '  {cards}\n  <div class="rules">',
        '  {cards}\n  {breadth_html}\n  <div class="rules">',
        1
    )

    # 6. Add breadth_html to the format call in render
    patched = patched.replace(
        "cards=cards",
        "cards=cards, breadth_html=breadth_html",
        1
    )

    TARGET.write_text(patched, encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    checks = [
        ("fetch_breadth_history", "fetch_breadth_history" in result),
        ("breadth_panel function", "def breadth_panel" in result),
        ("canvas chart", "breadth-chart" in result),
        ("breadth_html in render", "breadth_html=breadth_html" in result),
        ("CSS panel", "breadth-panel" in result),
    ]
    all_ok = True
    for name, ok in checks:
        print(f"  {'OK' if ok else 'FAIL'}: {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\nOK: Breadth chart added to signal dashboard")
        return 0
    else:
        print("\nERROR: restoring")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
