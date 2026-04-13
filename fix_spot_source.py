f = r'C:\GammaEnginePython\merdian_signal_dashboard.py'
c = open(f, encoding='utf-8').read()
old = 'sb.table("market_spot_snapshots")'
new = 'sb.table("signal_snapshots")'
if old in c:
    open(f, 'w', encoding='utf-8').write(c.replace(old, new, 1))
    print('Fixed — restart dashboard')
else:
    print('Not found')
