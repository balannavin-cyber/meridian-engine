#!/usr/bin/env python3
"""
enforce_orchestrator_timeout.py â€” Kill Hung Orchestrator Processes

Runs every 2 minutes. Checks for orchestrator processes running >10 minutes.
If found, kills with SIGTERM + logs to script_execution_log as timeout.

Prevents infinite hangs that block subsequent 5-minute cycles.

Crontab entry:
  */2 03-09 * * 1-5 cd /home/ssm-user/meridian-engine && source .env && python3 enforce_orchestrator_timeout.py >> logs/timeout_enforcer.log 2>&1
"""

import os
import sys
import subprocess
import json
import requests
from datetime import datetime, timedelta
import signal

sys.path.insert(0, '/home/ssm-user/meridian-engine')
try:
    from telegram_utils import send_alert, send_critical
except ImportError:
    def send_alert(*args, **kwargs): return False
    def send_critical(*args, **kwargs): return False

SUPABASE_URL = os.getenv('SUPABASE_URL')
SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
TIMEOUT_SECONDS = 600  # 10 minutes

if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    print("[FATAL] Supabase credentials not configured")
    sys.exit(1)

headers = {
    'apikey': SERVICE_ROLE_KEY,
    'Authorization': f'Bearer {SERVICE_ROLE_KEY}',
    'Content-Type': 'application/json'
}

class TimeoutEnforcer:
    def __init__(self):
        self.ts = datetime.utcnow()
    
    def log(self, msg: str):
        print(f"[{self.ts.strftime('%H:%M:%S')}] {msg}")
    
    def find_orchestrator_process(self):
        """Find run_merdian_shadow_runner_aws.py process."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'run_merdian_shadow_runner_aws.py'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                return [int(p) for p in pids if p.isdigit()]
            return []
        except Exception as e:
            self.log(f"Error finding process: {e}")
            return []
    
    def get_process_runtime(self, pid: int) -> int:
        """Get how many seconds a process has been running."""
        try:
            result = subprocess.run(
                ['ps', '-o', 'etime=', '-p', str(pid)],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return -1
            
            etime = result.stdout.strip()  # Format: HH:MM:SS or MM:SS or SSS
            parts = etime.split(':')
            
            if len(parts) == 3:
                hours, mins, secs = int(parts[0]), int(parts[1]), int(parts[2])
                return hours * 3600 + mins * 60 + secs
            elif len(parts) == 2:
                mins, secs = int(parts[0]), int(parts[1])
                return mins * 60 + secs
            else:
                return int(parts[0])
        except Exception as e:
            self.log(f"Error getting process runtime: {e}")
            return -1
    
    def kill_process(self, pid: int, runtime_secs: int):
        """Kill a process and log it."""
        try:
            self.log(f"Killing hung orchestrator PID {pid} (runtime: {runtime_secs}s)")
            os.kill(pid, signal.SIGTERM)
            
            # Record in script_execution_log
            self.log_timeout_kill(pid, runtime_secs)
            
            # Send alert
            send_critical(
                f"Orchestrator timeout â€” killed PID {pid}",
                context={
                    'runtime_seconds': runtime_secs,
                    'timeout_threshold': TIMEOUT_SECONDS,
                    'signal': 'SIGTERM'
                }
            )
            
            return True
        except Exception as e:
            self.log(f"Failed to kill process: {e}")
            return False
    
    def log_timeout_kill(self, pid: int, runtime_secs: int):
        """Log process kill to script_execution_log."""
        try:
            payload = {
                'script_name': 'run_merdian_shadow_runner_aws.py',
                'status': 'timeout_killed',
                'exit_code': -15,  # SIGTERM
                'duration_ms': runtime_secs * 1000,
                'started_at': (self.ts - timedelta(seconds=runtime_secs)).isoformat(),
                'finished_at': self.ts.isoformat(),
                'message': f'Process hung >10min (PID {pid}), killed by enforce_orchestrator_timeout.py'
            }
            
            url = f"{SUPABASE_URL}/rest/v1/script_execution_log"
            resp = requests.post(url, headers=headers, json=payload, timeout=5)
            
            if resp.status_code in [200, 201]:
                self.log("Logged timeout kill to script_execution_log")
            else:
                self.log(f"Failed to log: {resp.status_code}")
        except Exception as e:
            self.log(f"Error logging timeout kill: {e}")
    
    def run(self):
        """Check for hung processes and kill if necessary."""
        self.log("=== TIMEOUT ENFORCER START ===")
        
        pids = self.find_orchestrator_process()
        
        if not pids:
            self.log("No orchestrator processes found")
        else:
            for pid in pids:
                runtime = self.get_process_runtime(pid)
                
                if runtime > TIMEOUT_SECONDS:
                    self.log(f"HUNG PROCESS DETECTED: PID {pid}, runtime {runtime}s > {TIMEOUT_SECONDS}s")
                    self.kill_process(pid, runtime)
                else:
                    self.log(f"Process PID {pid} OK ({runtime}s)")
        
        self.log("=== TIMEOUT ENFORCER END ===")

if __name__ == '__main__':
    enforcer = TimeoutEnforcer()
    enforcer.run()
