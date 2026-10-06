"""S90_CHILD_RUN — offline test for core.execution_log.log_child_run (no network: requests is stubbed)."""
import sys; sys.path.insert(0, '.')
import core.execution_log as el

calls = []
class R:  # minimal response
    status_code = 201; text = ''
class Stub:
    @staticmethod
    def post(url, **kw): calls.append(('POST', kw['json'])); return R()
    @staticmethod
    def patch(url, **kw): calls.append(('PATCH', kw['json'], kw['params'])); return R()
el.requests = Stub
el._SUPABASE_URL, el._SUPABASE_KEY = 'https://example.invalid', 'k'

# 1. successful extra-expiry leg -> opening row + final row, both carrying the leg's run_id and product
el.log_child_run('ingest_option_chain_local.py', 'NIFTY', 'rid-2', 'option_chain_snapshots', 412, notes='extra expiry 2026-10-13')
(op, body), (op2, fin, prm) = calls[0], calls[1]
assert op == 'POST' and body['run_id'] == 'rid-2' and body['product'] == 'option_chain_snapshots:NIFTY' and body['kind'] == 'run', body
assert op2 == 'PATCH' and fin['exit_reason'] == 'SUCCESS' and fin['actual_writes'] == {'option_chain_snapshots': 412}, fin
assert fin['contract_met'] is True and fin['run_id'] == 'rid-2' and prm['invocation_id'] == f"eq.{body['invocation_id']}", fin
print('PASS success leg', fin['status'])

# 2. empty leg -> DATA_ERROR row, exit_code 1, error recorded
calls.clear()
el.log_child_run('ingest_option_chain_local.py', 'SENSEX', 'rid-3', 'option_chain_snapshots', 0, error='0 rows extracted')
fin = calls[1][1]
assert fin['exit_reason'] == 'DATA_ERROR' and fin['exit_code'] == 1 and fin['error_message'] == '0 rows extracted', fin
print('PASS empty leg', fin['status'])

# 3. ledger unreachable -> never raises
class Boom:
    @staticmethod
    def post(*a, **k): raise ConnectionError('down')
    patch = post
el.requests = Boom
el.log_child_run('ingest_option_chain_local.py', 'NIFTY', 'rid-4', 'option_chain_snapshots', 1)
print('PASS ledger down does not raise')

# 4. the ingest calls it for every captured and every empty extra leg
src = open('ingest_option_chain_local.py').read()
assert src.count('log_child_run("ingest_option_chain_local.py", symbol, _rid,') == 2
print('CHILD RUN ALL PASS')
