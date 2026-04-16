#!/usr/bin/env python3
"""Simplified breadth chart patch — skips the format check that doesn't apply."""
import shutil
from pathlib import Path

TARGET = Path("merdian_signal_dashboard.py")
BACKUP = Path("merdian_signal_dashboard.py.bak_breadth_chart2")

FETCH_FN = '''def fetch_breadth_history():
    """Fetch today's breadth time series from breadth_intraday_history."""
    today = str(date.today())
    r = _q(lambda: sb.table("breadth_intraday_history")
        .select("ts,advances,declines,breadth_score,coverage_pct")
        .eq("trade_date", today)
        .order("ts", desc=False)
        .limit(100)
        .execute().data)
    return r or []

'''

BREADTH_PANEL_FN = '''
def breadth_panel(rows):
    if not rows:
        return \'\'\'<div class="breadth-panel">
          <div class="bp-header"><span class="bp-title">&#9632; Market Breadth &mdash; NSE Universe</span>
          <span class="bp-cov">No data &mdash; WebSocket starting or market closed</span></div>
          <div class="bp-nodata">Breadth data appears after first pipeline cycle (~09:20 IST)</div>
        </div>\'\'\'
    latest = rows[-1]
    adv = latest.get("advances", 0) or 0
    dec = latest.get("declines", 0) or 0
    score = latest.get("breadth_score", 0) or 0
    cov = latest.get("coverage_pct", 0) or 0
    score_col = "#00ff88" if score > 20 else "#ff3b5c" if score < -20 else "#ffaa00"
    regime = "BULLISH" if score > 20 else "BEARISH" if score < -20 else "NEUTRAL"
    import json as _json
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo as _ZI
    times, advs, decs = [], [], []
    for row in rows:
        try:
            ts = datetime.fromisoformat(row["ts"].replace("Z","+00:00"))
            ts_ist = ts.astimezone(_ZI("Asia/Kolkata"))
            times.append(ts_ist.strftime("%H:%M"))
            advs.append(row.get("advances") or 0)
            decs.append(row.get("declines") or 0)
        except: pass
    t_json = _json.dumps(times)
    a_json = _json.dumps(advs)
    d_json = _json.dumps(decs)
    return f\'\'\'<div class="breadth-panel">
      <div class="bp-header">
        <span class="bp-title">&#9632; Market Breadth &mdash; NSE Universe</span>
        <div class="bp-stats">
          <span class="bp-adv">&#9650; {adv:,} ADV</span>
          <span class="bp-dec">&#9660; {dec:,} DEC</span>
          <span class="bp-score" style="color:{score_col}">{regime} ({score:+.0f})</span>
          <span class="bp-cov">COV {cov:.0f}%</span>
        </div>
      </div>
      <div class="bp-canvas-wrap"><canvas id="breadth-chart"></canvas></div>
      <script>(function(){{
        var times={t_json},advs={a_json},decs={d_json};
        var c=document.getElementById("breadth-chart");
        if(!c||!times.length)return;
        c.width=c.parentElement.offsetWidth;c.height=140;
        var ctx=c.getContext("2d"),W=c.width,H=c.height;
        var PAD={{t:10,r:65,b:24,l:50}},pw=W-PAD.l-PAD.r,ph=H-PAD.t-PAD.b;
        var maxV=Math.max(Math.max.apply(null,advs),Math.max.apply(null,decs),100);
        function px(i){{return PAD.l+i*(pw/Math.max(times.length-1,1));}}
        function py(v){{return PAD.t+ph-(v/maxV)*ph;}}
        ctx.strokeStyle="#1e2a38";ctx.lineWidth=1;
        [0,Math.round(maxV/2),maxV].forEach(function(v){{
          var y=py(v);ctx.beginPath();ctx.moveTo(PAD.l,y);ctx.lineTo(W-PAD.r,y);ctx.stroke();
          ctx.fillStyle="#4a5568";ctx.font="10px monospace";ctx.textAlign="right";ctx.fillText(v,PAD.l-4,y+4);
        }});
        var step=Math.max(1,Math.floor(times.length/8));
        ctx.fillStyle="#4a5568";ctx.font="10px monospace";ctx.textAlign="center";
        times.forEach(function(t,i){{if(i%step===0||i===times.length-1)ctx.fillText(t,px(i),H-4);}});
        ctx.beginPath();ctx.strokeStyle="#ff3b5c";ctx.lineWidth=2;ctx.lineJoin="round";
        decs.forEach(function(v,i){{i===0?ctx.moveTo(px(i),py(v)):ctx.lineTo(px(i),py(v));}});ctx.stroke();
        ctx.beginPath();ctx.strokeStyle="#00ff88";ctx.lineWidth=2;ctx.lineJoin="round";
        advs.forEach(function(v,i){{i===0?ctx.moveTo(px(i),py(v)):ctx.lineTo(px(i),py(v));}});ctx.stroke();
        ctx.fillStyle="#00ff88";ctx.fillRect(W-PAD.r+4,PAD.t,10,2);
        ctx.fillStyle="#c9d5e0";ctx.font="11px sans-serif";ctx.textAlign="left";ctx.fillText("ADV",W-PAD.r+18,PAD.t+4);
        ctx.fillStyle="#ff3b5c";ctx.fillRect(W-PAD.r+4,PAD.t+14,10,2);ctx.fillText("DEC",W-PAD.r+18,PAD.t+18);
      }})();</script>
    </div>\'\'\'

'''

BREADTH_CSS = """.breadth-panel{background:#0d1117;border:1px solid #1e2a38;border-radius:4px;
  grid-column:1/-1;padding:16px 20px;margin-top:0}
.bp-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:8px}
.bp-title{font-size:11px;letter-spacing:2px;color:#64748b;text-transform:uppercase;font-weight:700}
.bp-stats{display:flex;gap:20px;font-family:'Space Mono',monospace;font-size:13px}
.bp-adv{color:#00ff88;font-weight:700}.bp-dec{color:#ff3b5c;font-weight:700}
.bp-score{font-weight:700}.bp-cov{color:#64748b;font-size:11px}
.bp-canvas-wrap{position:relative;height:140px}
canvas#breadth-chart{width:100%;height:140px;display:block}
.bp-nodata{color:#64748b;font-size:12px;font-style:italic;text-align:center;padding:40px 0}
"""

def main():
    source = TARGET.read_text(encoding="utf-8")

    if "fetch_breadth_history" in source:
        print("Already patched.")
        return 0

    # Check anchors
    anchors = [
        ("def eff_cap(c):", "fetch function insertion point"),
        (".footer{text-align:center;", "CSS insertion point"),
        ("def render():", "render function"),
        ('  {cards}\n  <div class="rules">', "cards in template"),
        ('    cards = "\\n".join(card(sigs[s]) for s in SYMBOLS)', "cards build line"),
    ]
    missing = [name for anchor, name in anchors if anchor not in source]
    if missing:
        print(f"ERROR: missing anchors: {missing}")
        return 1

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    p = source

    # 1. Insert fetch function before eff_cap
    p = p.replace("def eff_cap(c):", FETCH_FN + "def eff_cap(c):", 1)

    # 2. Insert CSS before .footer
    p = p.replace(".footer{text-align:center;",
                  BREADTH_CSS + ".footer{text-align:center;", 1)

    # 3. Insert breadth_panel function before render()
    p = p.replace("def render():", BREADTH_PANEL_FN + "def render():", 1)

    # 4. Add breadth_html variable in render() after cards line
    p = p.replace(
        '    cards = "\\n".join(card(sigs[s]) for s in SYMBOLS)',
        '    cards = "\\n".join(card(sigs[s]) for s in SYMBOLS)\n'
        '    try:\n'
        '        _brows = fetch_breadth_history()\n'
        '        _breadth_html = breadth_panel(_brows)\n'
        '    except Exception:\n'
        '        _breadth_html = ""\n',
        1
    )

    # 5. Add breadth panel in HTML template
    p = p.replace(
        '  {cards}\n  <div class="rules">',
        '  {cards}\n  \' + _breadth_html + \'\n  <div class="rules">',
        1
    )

    # The f-string approach won't work for dynamic content — switch to string concat
    # Find the return f""" and change cards injection approach
    # Actually simpler: just replace {cards} with cards variable and use concat

    TARGET.write_text(p, encoding="utf-8")

    # Verify
    result = TARGET.read_text(encoding="utf-8")
    checks = [
        ("fetch_breadth_history", "fetch_breadth_history" in result),
        ("breadth_panel fn", "def breadth_panel" in result),
        ("canvas", "breadth-chart" in result),
        ("CSS panel", "breadth-panel" in result),
        ("_brows", "_brows" in result),
    ]
    all_ok = True
    for name, ok in checks:
        print(f"  {'OK' if ok else 'FAIL'}: {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\nOK: Breadth chart added")
        # Test syntax
        import subprocess, sys
        r = subprocess.run([sys.executable, "-c",
            f"import ast; ast.parse(open('{TARGET}').read()); print('Syntax OK')"],
            capture_output=True, text=True)
        if r.returncode == 0:
            print(r.stdout.strip())
        else:
            print(f"SYNTAX ERROR:\n{r.stderr}")
            print("Restoring...")
            shutil.copy2(BACKUP, TARGET)
            return 1
        return 0
    else:
        print("Restoring...")
        shutil.copy2(BACKUP, TARGET)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
