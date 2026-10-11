#!/usr/bin/env python3
"""S96-E check 4i -- the M-P7 scorer's badge state for one replayed cycle, using the scorer's OWN
state() and sgn(), lifted from mp7_score.py by its syntax tree (mp7_score.py runs on import, so it
is not imported; nothing is re-typed). Reads only ~/mp7_out. No database.
Run: python3 -I mp7_state_at.py SYMBOL DATE HH:MM:SS [OUT]
"""
import ast, csv, os, sys
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sym, day, t = sys.argv[1:4]
OUT = sys.argv[4] if len(sys.argv) > 4 else os.path.expanduser('~/mp7_out')
tree = ast.parse(open(os.path.join(HERE, 'mp7_score.py')).read())
fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('sgn', 'state')]
assert sorted(f.name for f in fns) == ['sgn', 'state'], 'scorer functions not found'
ns = {'D': D}
exec(compile(ast.Module(body=fns, type_ignores=[]), 'mp7_score.py', 'exec'), ns)
with open(os.path.join(OUT, 'cycles', f'{day}.csv'), newline='') as f:
    rows = [r for r in csv.DictReader(f) if r['symbol'] == sym and r['cycle_ist'] == t]
assert len(rows) == 1, f'{len(rows)} rows for {sym} {day} {t}'
r = rows[0]
st, fv = ns['state'](r)
bc, fc = D(r['book_call']), D(r['flow_call'])
print(f'{sym} {day} {t} state={st} flow_net_v={fc + D(r["flow_put_v"])} flow_net_p={fc + D(r["flow_put_p"])} '
      f'book_net_v={bc + D(r["book_put_v"])} book_net_p={bc + D(r["book_put_p"])}')
