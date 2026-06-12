#!/usr/bin/env python3
"""Health monitor daemon for MERDIAN."""

import os
import sys
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('/home/ssm-user/meridian-engine/.env')

sys.path.insert(0, '/home/ssm-user/meridian-engine')
try:
    from telegram_utils import send_alert, send_critical, send_warning
except ImportError:
    def send_alert(*args, **kwargs): return False
    def send_critical(*args, **kwargs): return False
    def send_warning(*args, **kwargs): return False

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("[FATAL] SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
    sys.exit(1)

headers = {
    'apikey': SUPABASE_SERVICE_ROLE_KEY,
    'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
    'Content-Type': 'application/json'
}

class HealthMonitor:
    def __init__(self):
        self.ts = datetime.utcnow()
        self.alerts = []
    
    def log(self, level: str, msg: str):
        print(f"[{self.ts.strftime('%H:%M:%S')}] {level}: {msg}")
        self.alerts.append({'level': level, 'msg': msg})
    
    def check_orchestrator_failures(self):
        five_min_ago = (self.ts - timedelta(minutes=5)).isoformat()
        url = f"{SUPABASE_URL}/rest/v1/script_execution_log?script_name=eq.run_merdian_shadow_runner_aws.py&created_at=gt.{five_min_ago}&order=created_at.desc&limit=10"
        
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                self.log('ERROR', f'Supabase query failed: {resp.status_code}')
                return
            
            rows = resp.json()
            if not rows:
                self.log('WARNING', 'No orchestrator runs in last 5 minutes')
                send_warning('Orchestrator not firing', {'gap_minutes': 5})
                return
            
            for row in rows:
                if row.get('exit_code') != 0:
                    msg = f"Orchestrator FAILED: exit_code={row.get('exit_code')}, duration={row.get('duration_ms')}ms"
                    self.log('CRITICAL', msg)
                    send_critical(msg, context={
                        'exit_code': row.get('exit_code'),
                        'duration_ms': row.get('duration_ms'),
                        'created_at': row.get('created_at')
                    })
                    return
            
            self.log('INFO', f'Orchestrator OK ({len(rows)} runs in 5min)')
        
        except Exception as e:
            self.log('ERROR', f'Orchestrator check failed: {e}')
    
    def run(self):
        self.log('INFO', '=== HEALTH CHECK START ===')
        self.check_orchestrator_failures()
        self.log('INFO', '=== HEALTH CHECK END ===')
        return len([a for a in self.alerts if a['level'] in ['CRITICAL', 'ERROR']]) == 0

if __name__ == '__main__':
    monitor = HealthMonitor()
    success = monitor.run()
    sys.exit(0 if success else 1)
