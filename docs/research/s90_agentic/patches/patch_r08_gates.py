"""S90 R0.8 (ADR-020, ADR-031 D5.3): route the chain-ingest and spot-capture holiday checks
through core.trading_calendar_gate, so an absent trading_calendar row is resolved by the rule
engine instead of read as OPEN. Fail-open preserved. Apply AFTER patch_r07_ledger.py
(ingest base = the R0.7-patched file). Dry-run default; --apply writes."""
import ast, hashlib, sys
APPLY = "--apply" in sys.argv
MARK = "S90_R08_GATE"
FILES = {
 "ingest_option_chain_local.py": ("67e1c0e5c434", [
  ('    today_str = str(datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Kolkata")).date())\n'
   '    if not SUPABASE_URL or not SUPABASE_KEY:\n        return (False, today_str)\n',
   '    today_str = str(datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Kolkata")).date())\n'
   f'    # {MARK}: delegate to the shared gate (ADR-020). The inline copy below read an\n'
   '    # ABSENT row as open, which ran the 2026-10-02 frozen ingest. Kept only as a fallback.\n'
   '    try:\n'
   '        from core.trading_calendar_gate import is_trading_day\n'
   '        return (not is_trading_day(today_str), today_str)\n'
   '    except Exception as e:  # fail-open, as before\n'
   '        print(f"  [WARN] shared calendar gate unavailable ({e}); inline check", file=sys.stderr)\n'
   '    if not SUPABASE_URL or not SUPABASE_KEY:\n        return (False, today_str)\n'),
 ]),
 "capture_spot_1m_v2.py": ("ebbf75385f01", [
  ('    try:\n        r = requests.get(\n            f"{SUPABASE_URL}/rest/v1/trading_calendar",\n            headers=sb_headers(),\n',
   f'    # {MARK}: delegate to the shared gate (ADR-020); absence is resolved by the rule\n'
   '    # engine, not allowed through. Errors fall back to the inline read (fail-open).\n'
   '    try:\n'
   '        from core.trading_calendar_gate import is_trading_day\n'
   '        return is_trading_day(today_str)\n'
   '    except Exception as e:\n'
   '        print(f"  [WARN] shared calendar gate unavailable ({e}); inline check")\n'
   '    try:\n        r = requests.get(\n            f"{SUPABASE_URL}/rest/v1/trading_calendar",\n            headers=sb_headers(),\n'),
 ]),
}
ok = True
for path, (base, edits) in FILES.items():
    raw = open(path, "rb").read(); s = raw.decode("utf-8")
    if MARK in s:
        print(f"{path}: already patched"); continue
    h = hashlib.sha256(raw).hexdigest()
    if not h.startswith(base):
        print(f"{path}: base {h[:12]} != expected {base} - ABORT"); ok = False; break
    for o, n in edits:
        c = s.count(o)
        if c != 1:
            print(f"{path}: anchor count {c} - ABORT:\n{o[:90]!r}"); ok = False; break
        s = s.replace(o, n)
    if not ok:
        break
    ast.parse(s)
    if APPLY:
        open(path, "w").write(s)
    print(f"{path}: {'APPLIED' if APPLY else 'dry-run OK'} -> {hashlib.sha256(s.encode()).hexdigest()[:12]}")
sys.exit(0 if ok else 1)
