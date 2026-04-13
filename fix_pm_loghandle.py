f = r'C:\GammaEnginePython\merdian_pm.py'
c = open(f, encoding='utf-8').read()

# Find the Popen block and fix the stdout to use a fresh open after header write
old = "        stdout=open(log_file, 'a', encoding='utf-8'),"
new = "        stdout=open(str(log_file), 'a', encoding='utf-8'),"

if old in c:
    # The real fix: store log_file handle separately
    old2 = """    with open(log_file, 'a', encoding='utf-8') as lf:
        lf.write(f"\\n{'='*50}\\nStarted {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}\\n{'='*50}\\n")

    proc = subprocess.Popen(
        [str(PYTHON), '-u', str(script_path)] + cfg.get('args', []),
        cwd=str(BASE),
        stdout=open(log_file, 'a', encoding='utf-8'),
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )"""
    new2 = """    _log_header = f"\\n{'='*50}\\nStarted {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}\\n{'='*50}\\n"
    _lf = open(str(log_file), 'a', encoding='utf-8')
    _lf.write(_log_header)
    _lf.flush()

    proc = subprocess.Popen(
        [str(PYTHON), '-u', str(script_path)] + cfg.get('args', []),
        cwd=str(BASE),
        stdout=_lf,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )"""
    if old2 in c:
        c = c.replace(old2, new2, 1)
        open(f, 'w', encoding='utf-8').write(c)
        print('Fixed: single file handle now passed to Popen')
    else:
        print('old2 anchor not found - check merdian_pm.py manually')
else:
    print('old anchor not found')
