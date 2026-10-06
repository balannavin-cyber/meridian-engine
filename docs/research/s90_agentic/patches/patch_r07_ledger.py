"""S90 R0.7 (ADR-031 D7): ledger columns run_id / product / status / kind via ExecutionLog,
and run_id + product on the writers that know them. Canon-v3: base-hash pinned per file,
count==1 anchors, idempotency marker, ast gate. Dry-run default; --apply writes."""
import ast, hashlib, sys
APPLY = "--apply" in sys.argv
MARK = "S90_R07_LEDGER"
FILES = {
 "core/execution_log.py": ("896a258df403", [
  ('        dry_run: bool = False,\n        notes: Optional[str] = None,\n    ):\n',
   '        dry_run: bool = False,\n        notes: Optional[str] = None,\n'
   f'        run_id: Optional[str] = None,            # {MARK}\n'
   '        product_relation: Optional[str] = None,  # e.g. "gamma_metrics"; product = relation:symbol\n'
   '    ):\n'),
  ('        self.notes = notes\n\n        self.host = _detect_host()\n',
   '        self.notes = notes\n'
   '        self.run_id = run_id\n'
   '        self.product_relation = product_relation\n\n'
   '        self.host = _detect_host()\n'),
  ('    def complete(self, notes: Optional[str] = None) -> int:\n',
   '    def set_run_id(self, run_id: Optional[str]) -> None:\n'
   f'        """{MARK}: attach the cycle run_id once known (best-effort, like set_symbol)."""\n'
   '        if self._finalised or not run_id:\n'
   '            return\n'
   '        self.run_id = str(run_id)\n'
   '        if not _SUPABASE_URL or not _SUPABASE_KEY:\n'
   '            return\n'
   '        try:\n'
   '            r = requests.patch(\n'
   '                f"{_SUPABASE_URL}/rest/v1/script_execution_log",\n'
   '                headers=self._headers,\n'
   '                params={"invocation_id": f"eq.{self.invocation_id}"},\n'
   '                json={"run_id": self.run_id},\n'
   '                timeout=10,\n'
   '            )\n'
   '            if r.status_code >= 300:\n'
   '                self._warn(f"set_run_id PATCH failed: status={r.status_code} body={r.text[:200]}")\n'
   '        except Exception as e:\n'
   '            self._warn(f"set_run_id PATCH exception: {e}")\n\n'
   '    @property\n'
   '    def product(self) -> Optional[str]:\n'
   '        if not self.product_relation:\n'
   '            return None\n'
   '        return f"{self.product_relation}:{self.symbol}" if self.symbol else self.product_relation\n\n'
   '    def complete(self, notes: Optional[str] = None) -> int:\n'),
  ('            "git_sha": self.git_sha or None,\n            "notes": self.notes,\n        }\n',
   '            "git_sha": self.git_sha or None,\n            "notes": self.notes,\n'
   f'            "kind": "run",              # {MARK}\n'
   '            "run_id": self.run_id,\n'
   '            "product": self.product,\n'
   '        }\n'),
  ('            "contract_met": contract_met,\n        }\n        if notes is not None:\n',
   '            "contract_met": contract_met,\n'
   f'            "status": _ledger_status(exit_reason, contract_met),  # {MARK}\n'
   '            "run_id": self.run_id,\n'
   '            "product": self.product,\n'
   '        }\n        if notes is not None:\n'),
  ('def _today_ist() -> date:\n',
   f'def _ledger_status(exit_reason: str, contract_met: Optional[bool]) -> Optional[str]:\n'
   f'    """{MARK}: ADR-031 D2 status of the run\'s product, from its exit."""\n'
   '    if exit_reason == "SUCCESS":\n'
   '        return "OK" if contract_met else "DEGRADED"\n'
   '    if exit_reason in ("HOLIDAY_GATE", "OFF_HOURS"):\n'
   '        return "CLOSED"\n'
   '    if exit_reason in ("SKIPPED_NO_INPUT", "DATA_ERROR", "TOKEN_EXPIRED", "DEPENDENCY_MISSING", "TIMEOUT"):\n'
   '        return "MISSING"\n'
   '    if exit_reason == "CRASH":\n'
   '        return "UNKNOWN"\n'
   '    return None  # RUNNING, DRY_RUN\n\n\n'
   'def _today_ist() -> date:\n'),
 ]),
 "ingest_option_chain_local.py": ("a5166de05864", [
  ('        notes=f"mode={mode} floor={EXPECTED_FLOOR[mode]}",\n    )\n',
   '        notes=f"mode={mode} floor={EXPECTED_FLOOR[mode]}",\n'
   f'        product_relation="option_chain_snapshots",  # {MARK}\n'
   '    )\n'),
  ('    snapshot_ts = utc_now_iso()\n    run_id = str(uuid.uuid4())\n',
   '    snapshot_ts = utc_now_iso()\n    run_id = str(uuid.uuid4())\n'
   f'    log.set_run_id(run_id)  # {MARK}: front-expiry run; extra expiries keep their own run_ids\n'),
 ]),
 "compute_gamma_metrics_local.py": ("494d3b0cf330", [
  ('        notes=f"run_id={run_id} run_type={run_type}",\n    )\n',
   '        notes=f"run_id={run_id} run_type={run_type}",\n'
   f'        run_id=run_id, product_relation="gamma_metrics",  # {MARK}\n'
   '    )\n'),
 ]),
 "write_gex_cycle_history_local.py": ("668dc735aeb2", [
  ('        notes=f"run_id={run_id} legs={n_expected}",\n    )\n',
   '        notes=f"run_id={run_id} legs={n_expected}",\n'
   f'        run_id=run_id, product_relation="gex_cycle_history",  # {MARK}\n'
   '    )\n'),
  ('        log = ExecutionLog(script_name=WRITER, expected_writes={TARGET_TABLE: 0},\n                           notes=f"run_id={run_id}")\n',
   '        log = ExecutionLog(script_name=WRITER, expected_writes={TARGET_TABLE: 0},\n                           notes=f"run_id={run_id}",\n'
   f'                           run_id=run_id, product_relation="gex_cycle_history")  # {MARK}\n'),
 ]),
 "compute_volatility_metrics_local.py": ("c171f3593f2d", [
  ('        script_name="compute_volatility_metrics_local.py",\n        expected_writes={TARGET_TABLE: 1},\n        symbol=None,\n        notes=f"run_id={run_id}",\n    )\n',
   '        script_name="compute_volatility_metrics_local.py",\n        expected_writes={TARGET_TABLE: 1},\n        symbol=None,\n        notes=f"run_id={run_id}",\n'
   f'        run_id=run_id, product_relation="volatility_snapshots",  # {MARK}\n'
   '    )\n'),
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
            print(f"{path}: anchor count {c} - ABORT:\n{o[:80]!r}"); ok = False; break
        s = s.replace(o, n)
    if not ok:
        break
    ast.parse(s)
    if APPLY:
        open(path, "w").write(s)
    print(f"{path}: {'APPLIED' if APPLY else 'dry-run OK'} -> {hashlib.sha256(s.encode()).hexdigest()[:12]}")
sys.exit(0 if ok else 1)
