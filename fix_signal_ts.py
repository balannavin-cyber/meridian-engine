f = r'C:\GammaEnginePython\merdian_signal_dashboard.py'
c = open(f, encoding='utf-8').read()

# Replace the sig_ts assignment to convert UTC -> IST
old = '    exit_ts = d.get("exit_ts",""); sig_ts = d.get("ts","")'
new = '''    exit_ts = d.get("exit_ts",""); _ts_raw = d.get("ts","")
    # Convert UTC timestamp to IST for display
    try:
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        _ts_dt = datetime.fromisoformat(_ts_raw.replace("Z","+00:00"))
        sig_ts = _ts_dt.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%dT%H:%M:%S+05:30")
    except Exception:
        sig_ts = _ts_raw'''

if old in c:
    open(f, 'w', encoding='utf-8').write(c.replace(old, new, 1))
    print('Fixed -- sig_ts now converts UTC to IST')
    # Verify
    final = open(f, encoding='utf-8').read()
    print('Verified:', 'Asia/Kolkata' in final)
else:
    print('Anchor not found')
