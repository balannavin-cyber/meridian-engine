import ast, hashlib, sys
p = 'run_equity_eod_until_done.py'; s = open(p).read()
MARK = 'S90_EOD_FULL_LAP'
if MARK in s:
    print('already patched'); sys.exit(0)
assert hashlib.sha256(s.encode()).hexdigest().startswith(sys.argv[1]), 'unexpected base version'
E = [
 ('    for run_no in range(1, MAX_RUNS + 1):\n',
  f'    # {MARK}: the cursor persists across days, so a sweep that stops when the cursor\n'
  '    # returns to 0 only covers [start_cursor, end). S90 measured 557 OK of 1,385 on\n'
  '    # 2026-10-05: 327 tickers unrefreshed since 09-25, the builder\'s 95 % gate never met.\n'
  '    # Now: one FULL lap -- continue past 0 and stop on returning to the start cursor.\n'
  '    start_cursor = None\n'
  '    wrapped = False\n\n'
  '    for run_no in range(1, MAX_RUNS + 1):\n'),
 ('        next_cursor = parse_value(ingest_output, "Next cursor")\n',
  '        next_cursor = parse_value(ingest_output, "Next cursor")\n'
  '        if start_cursor is None:\n'
  '            _c = parse_value(ingest_output, "Cursor")\n'
  '            start_cursor = int(_c) if _c is not None and _c.isdigit() else 0\n'),
 ('        if next_cursor == "0":\n'
  '            print("Stopping because cursor returned to 0 after progressing through the universe.")\n'
  '            break\n',
  '        if next_cursor == "0":\n'
  '            if not start_cursor:\n'
  '                print("Stopping because cursor returned to 0 after a full lap from 0.")\n'
  '                break\n'
  '            wrapped = True\n'
  f'            print(f"[{MARK}] cursor wrapped to 0; continuing to start cursor {{start_cursor}}")\n'
  '        elif wrapped and next_cursor.isdigit() and int(next_cursor) >= start_cursor:\n'
  f'            print(f"[{MARK}] full lap complete (back at cursor {{next_cursor}} >= start {{start_cursor}})")\n'
  '            break\n'),
]
for o, n in E:
    c = s.count(o)
    assert c == 1, f'anchor count {c}: {o[:60]!r}'
    s = s.replace(o, n)
ast.parse(s)
open(p, 'w').write(s)
print('patched', hashlib.sha256(s.encode()).hexdigest()[:12])
