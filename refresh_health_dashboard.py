#!/usr/bin/env python3
"""Live dashboard refresh."""

import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('/home/ssm-user/meridian-engine/.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("[FATAL] Supabase credentials not configured")
    exit(1)

headers = {
    'apikey': SUPABASE_SERVICE_ROLE_KEY,
    'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
    'Content-Type': 'application/json'
}

class DashboardRefresh:
    def __init__(self):
        self.ts = datetime.utcnow()
        self.health = {
            'timestamp': self.ts.isoformat(),
            'orchestrator': None,
            'captures': {},
            'tables': {},
        }
    
    def log(self, msg: str):
        print(f"[{self.ts.strftime('%H:%M:%S')}] {msg}")
    
    def get_minutes_old(self, ts_str: str) -> int:
        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            delta = self.ts - ts
            return int(delta.total_seconds() / 60)
        except:
            return 999
    
    def refresh_orchestrator_status(self):
        try:
            url = f"{SUPABASE_URL}/rest/v1/script_execution_log?script_name=eq.run_merdian_shadow_runner_aws.py&order=created_at.desc&limit=1"
            resp = requests.get(url, headers=headers, timeout=5)
            
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    row = rows[0]
                    self.health['orchestrator'] = {
                        'status': 'OK' if row.get('exit_code') == 0 else 'FAILED',
                        'exit_code': row.get('exit_code'),
                        'duration_ms': row.get('duration_ms'),
                        'created_at': row.get('created_at'),
                        'minutes_old': self.get_minutes_old(row.get('created_at', ''))
                    }
                    self.log(f"Orchestrator: {self.health['orchestrator']['status']} ({self.health['orchestrator']['minutes_old']}m ago)")
        except Exception as e:
            self.log(f"Orchestrator refresh failed: {e}")
    
    def refresh_table_freshness(self):
        tables = [
            ('option_chain_snapshots', 'ts'),
            ('market_spot_snapshots', 'ts'),
            ('gamma_metrics', 'created_at'),
        ]
        
        for table, ts_col in tables:
            try:
                url = f"{SUPABASE_URL}/rest/v1/{table}?order={ts_col}.desc&limit=1&select={ts_col}"
                resp = requests.get(url, headers=headers, timeout=5)
                
                if resp.status_code == 200:
                    rows = resp.json()
                    if rows:
                        row_ts = rows[0].get(ts_col, '')
                        minutes_old = self.get_minutes_old(row_ts)
                        self.health['tables'][table] = {
                            'latest_ts': row_ts,
                            'minutes_old': minutes_old,
                            'status': 'FRESH' if minutes_old < 5 else 'STALE'
                        }
                        self.log(f"{table}: {minutes_old}m old")
            except Exception as e:
                self.log(f"Table freshness check failed for {table}: {e}")
    
    def write_health_json(self):
        try:
            path = '/home/ssm-user/meridian-engine/status.json'
            with open(path, 'w') as f:
                json.dump(self.health, f, indent=2)
            self.log(f"Wrote health snapshot")
        except Exception as e:
            self.log(f"Failed to write health.json: {e}")
    
    def run(self):
        self.log("=== DASHBOARD REFRESH START ===")
        self.refresh_orchestrator_status()
        self.refresh_table_freshness()
        self.write_health_json()
        self.log("=== DASHBOARD REFRESH END ===")

if __name__ == '__main__':
    refresher = DashboardRefresh()
    refresher.run()
