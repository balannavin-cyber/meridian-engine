f = r'C:\GammaEnginePython\merdian_signal_dashboard.py'
c = open(f, encoding='utf-8').read()
c = c.replace('content="300"', 'content="60"')
open(f, 'w', encoding='utf-8').write(c)
print('Done' if 'content="60"' in c else 'Not found')
