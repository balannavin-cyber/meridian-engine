import ast, hashlib, sys
p = 'seed_trading_calendar.py'; s = open(p).read()
MARK = 'S90_SEED_CLOSED_DAYS'
if MARK in s:
    print('already patched'); sys.exit(0)
assert hashlib.sha256(s.encode()).hexdigest().startswith('deac6fe9f661'), 'unexpected base version'
E = [
 ('    rows = []\n    skipped = []\n',
  '    rows = []\n    skipped = []\n'
  f'    closed_rows = []  # {MARK} (ADR-020 belt, ADR-031 D5, R0.8)\n'),
 ('        if not cfg.is_open:\n            skipped.append((date_str, cfg.notes))\n            continue\n',
  '        if not cfg.is_open:\n            skipped.append((date_str, cfg.notes))\n'
  f'            # {MARK}: a closed day is written as a row, never left absent -- absence\n'
  '            # read as OPEN by inline gates is what ran the 2026-10-02 frozen ingest.\n'
  '            closed_rows.append({"trade_date": date_str, "is_open": False, "open_time": None,\n'
  '                                "holiday_name": cfg.notes, "notes": f"closed (seeder, {cfg.notes})"})\n'
  '            continue\n'),
 ('    if not rows:\n        print("[OK] nothing to seed (all days in window are closed).")\n        return 0\n\n',
  '    if closed_rows:\n'
  f'        # {MARK}: ignore-duplicates, so an existing row (an operator-set special\n'
  '        # session, or a belt row) is never overwritten by this pass.\n'
  '        cresp = requests.post(\n'
  '            f"{supabase_url}/rest/v1/{TABLE}?on_conflict=trade_date",\n'
  '            headers={"apikey": service_key, "Authorization": f"Bearer {service_key}",\n'
  '                     "Content-Type": "application/json",\n'
  '                     "Prefer": "resolution=ignore-duplicates,return=representation"},\n'
  '            data=json.dumps(closed_rows), timeout=30)\n'
  '        if cresp.status_code not in (200, 201):\n'
  '            print(f"[ERROR] closed-day insert failed: HTTP {cresp.status_code} | {cresp.text[:500]}",\n'
  '                  file=sys.stderr)\n'
  '            return 1\n'
  '        cw = cresp.json() if cresp.text else []\n'
  '        print(f"[OK] closed days: {len(cw) if isinstance(cw, list) else 0} new of {len(closed_rows)} "\n'
  '              f"(existing rows left untouched).")\n\n'
  '    if not rows:\n        print("[OK] nothing to seed (all days in window are closed).")\n        return 0\n\n'),
]
for o, n in E:
    c = s.count(o)
    assert c == 1, f'anchor count {c}: {o[:60]!r}'
    s = s.replace(o, n)
ast.parse(s)
open(p, 'w').write(s)
print('patched', hashlib.sha256(s.encode()).hexdigest()[:12])
