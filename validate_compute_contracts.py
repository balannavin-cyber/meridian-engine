#!/usr/bin/env python3
"""
validate_compute_contracts.py â€” Pre-compute Data Contract Validation

Runs immediately before orchestrator. Validates that input data exists and is fresh.
If contracts are violated, alerts operator and skips compute cycle.

Contracts:
  1. option_chain_snapshots: >=1 row from NIFTY or SENSEX in last 5 min
  2. market_spot_snapshots: >=1 row in last 1 min
  3. gamma_metrics: if previous run exists, no duplicate run_ids

Crontab entry (runs at 03:59, 04:04, 04:09 ... 09:59 UTC, 1 min before orchestrator):
  4,9,14,19,24,29,34,39,44,49,54,59 03-09 * * 1-5 ... validate_compute_contracts.py >> logs/contract_check.log 2>&1
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from typing import Dict, Tuple

sys.path.insert(0, '/home/ssm-user/meridian-engine')
try:
    from telegram_utils import send_alert, send_critical, send_warning
except ImportError:
    def send_alert(*args, **kwargs): return False
    def send_critical(*args, **kwargs): return False
    def send_warning(*args, **kwargs): return False

SUPABASE_URL = os.getenv('SUPABASE_URL')
SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    print("[FATAL] Supabase credentials not configured")
    sys.exit(1)

headers = {
    'apikey': SERVICE_ROLE_KEY,
    'Authorization': f'Bearer {SERVICE_ROLE_KEY}',
    'Content-Type': 'application/json'
}

class ContractValidator:
    def __init__(self):
        self.ts = datetime.utcnow()
        self.violations = []
        self.passed = []
    
    def log(self, level: str, msg: str):
        print(f"[{self.ts.strftime('%H:%M:%S')}] {level}: {msg}")
    
    def check_option_chain_fresh(self) -> bool:
        """Verify option_chain data exists and is <5 min old."""
        five_min_ago = (self.ts - timedelta(minutes=5)).isoformat()
        
        url = f"{SUPABASE_URL}/rest/v1/option_chain_snapshots?ts=gt.{five_min_ago}&limit=1&select=ts,symbol"
        
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                msg = f"Contract VIOLATED: option_chain_snapshots query failed ({resp.status_code})"
                self.log('ERROR', msg)
                self.violations.append(msg)
                return False
            
            rows = resp.json()
            if not rows:
                msg = "Contract VIOLATED: no option_chain data in last 5 minutes"
                self.log('WARNING', msg)
                self.violations.append(msg)
                send_warning(msg, context={'threshold_min': 5})
                return False
            
            self.log('INFO', f'Contract OK: option_chain fresh ({rows[0]["symbol"]})')
            self.passed.append('option_chain_fresh')
            return True
        
        except Exception as e:
            msg = f"Contract check failed: {e}"
            self.log('ERROR', msg)
            self.violations.append(msg)
            return False
    
    def check_spot_fresh(self) -> bool:
        """Verify spot data exists and is <1 min old."""
        one_min_ago = (self.ts - timedelta(minutes=1)).isoformat()
        
        url = f"{SUPABASE_URL}/rest/v1/market_spot_snapshots?ts=gt.{one_min_ago}&limit=1&select=ts,spot"
        
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                msg = f"Contract VIOLATED: spot query failed ({resp.status_code})"
                self.log('ERROR', msg)
                self.violations.append(msg)
                return False
            
            rows = resp.json()
            if not rows:
                msg = "Contract VIOLATED: no spot data in last 1 minute"
                self.log('WARNING', msg)
                self.violations.append(msg)
                send_warning(msg, context={'threshold_min': 1, 'table': 'market_spot_snapshots'})
                return False
            
            self.log('INFO', f'Contract OK: spot fresh (â‚¹{rows[0]["spot"]})')
            self.passed.append('spot_fresh')
            return True
        
        except Exception as e:
            msg = f"Spot check failed: {e}"
            self.log('ERROR', msg)
            self.violations.append(msg)
            return False
    
    def check_no_duplicate_runs(self) -> bool:
        """Verify last orchestrator run_id is not being reused."""
        try:
            # Get last 2 orchestrator runs
            url = f"{SUPABASE_URL}/rest/v1/gamma_metrics?order=created_at.desc&limit=2&select=run_id,created_at"
            resp = requests.get(url, headers=headers, timeout=5)
            
            if resp.status_code != 200:
                self.log('WARNING', 'Could not check for duplicate runs')
                return True  # Don't block on this
            
            rows = resp.json()
            if len(rows) < 2:
                self.log('INFO', 'Contract OK: first run or no previous data')
                self.passed.append('no_duplicate_runs')
                return True
            
            # Check if last two have same run_id
            if rows[0]['run_id'] == rows[1]['run_id']:
                msg = f"Contract VIOLATED: duplicate run_id {rows[0]['run_id'][:12]}... detected"
                self.log('ERROR', msg)
                self.violations.append(msg)
                send_critical(msg, context={
                    'last_run_id': rows[0]['run_id'],
                    'last_created_at': rows[0]['created_at'],
                    'prev_created_at': rows[1]['created_at']
                })
                return False
            
            self.log('INFO', 'Contract OK: no duplicate run_ids')
            self.passed.append('no_duplicate_runs')
            return True
        
        except Exception as e:
            self.log('WARNING', f'Duplicate run check failed: {e}')
            return True  # Don't block on this
    
    def run(self) -> bool:
        """Run all contract checks. Return True if all pass, False if any fail."""
        self.log('INFO', '=== CONTRACT VALIDATION START ===')
        
        all_pass = (
            self.check_option_chain_fresh() and
            self.check_spot_fresh() and
            self.check_no_duplicate_runs()
        )
        
        self.log('INFO', f'Passed: {", ".join(self.passed)}')
        
        if self.violations:
            self.log('ERROR', f'VIOLATIONS: {len(self.violations)} contract(s) violated')
            for v in self.violations:
                self.log('ERROR', f'  - {v}')
            send_alert(
                'Compute contracts violated â€” skipping this cycle',
                level='WARNING',
                context={'num_violations': len(self.violations)}
            )
            return False
        
        self.log('INFO', '=== ALL CONTRACTS PASSED ===')
        return True

if __name__ == '__main__':
    validator = ContractValidator()
    success = validator.run()
    
    # Exit 0 if contracts pass, 1 if violated
    sys.exit(0 if success else 1)
