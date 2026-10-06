import ast, hashlib, sys
p = 'ingest_equity_eod_local.py'; s = open(p).read()
MARK = 'S90_EOD_IST_DATE'
if MARK in s:
    print('already patched'); sys.exit(0)
assert hashlib.sha256(s.encode()).hexdigest().startswith('aa461b6673c8'), 'unexpected base version'
E = [
 ('UTC = timezone.utc\n',
  'UTC = timezone.utc\n'
  f'# {MARK} (ruling S90-H, R01-F10): Dhan stamps a daily candle at 00:00 IST, which is\n'
  '# 18:30 UTC the PREVIOUS day. Converting with tz=UTC dated every row one day early\n'
  '# (0 Fridays in equity_eod since 2025-07). The trade date is the IST calendar date.\n'
  'IST = timezone(timedelta(hours=5, minutes=30))\n'),
 ('            trade_date = datetime.fromtimestamp(int(ts_arr[i]), tz=UTC).date().isoformat()\n',
  '            trade_date = datetime.fromtimestamp(int(ts_arr[i]), tz=IST).date().isoformat()\n'),
]
for o, n in E:
    c = s.count(o)
    assert c == 1, f'anchor count {c}: {o[:60]!r}'
    s = s.replace(o, n)
ast.parse(s)
open(p, 'w').write(s)
print('patched', hashlib.sha256(s.encode()).hexdigest()[:12])
