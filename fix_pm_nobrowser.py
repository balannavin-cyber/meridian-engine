# Fix merdian_pm.py to pass --no-browser to health monitor
f = r'C:\GammaEnginePython\merdian_pm.py'
c = open(f, encoding='utf-8').read()
old = "    [str(PYTHON), str(script_path)],"
new = "    [str(PYTHON), str(script_path)] + cfg.get('args', []),"
if old in c:
    # Also update PROCESSES dict to add args for health_monitor
    old2 = "'health_monitor':   {'script': 'merdian_live_dashboard.py',   'port': 8765, 'desc': 'Health Monitor'},"
    new2 = "'health_monitor':   {'script': 'merdian_live_dashboard.py', 'args': ['--no-browser'], 'port': 8765, 'desc': 'Health Monitor'},"
    c = c.replace(old, new, 1)
    if old2 in c:
        c = c.replace(old2, new2, 1)
        open(f, 'w', encoding='utf-8').write(c)
        print('Fixed -- no-browser arg added')
    else:
        # Try partial match
        c = c.replace(old, new, 1)
        c = c.replace("'merdian_live_dashboard.py',   'port': 8765",
                      "'merdian_live_dashboard.py', 'args': ['--no-browser'], 'port': 8765", 1)
        open(f, 'w', encoding='utf-8').write(c)
        print('Fixed (partial match)')
else:
    print('Anchor not found: ' + old)
