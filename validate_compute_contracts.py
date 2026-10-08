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
from pathlib import Path
from typing import Dict, Tuple

sys.path.insert(0, '/home/ssm-user/meridian-engine')
try:
    from telegram_utils import send_alert, send_critical, send_warning
except ImportError:
    def send_alert(*args, **kwargs): return False
    def send_critical(*args, **kwargs): return False
    def send_warning(*args, **kwargs): return False

# ---- S92-CONTRACT-GATE: trading-day gate + per-key send dedupe --------------------
# TD-S91-NEW-13. Both halves REUSE the helpers 6a5c0e2 added to
# monitor_orchestrator_health.py rather than re-implementing them (CLAUDE.md rule 18:
# never roll a new inline calendar gate).
#
# They are imported LAZILY, inside the functions below, for two reasons that are not
# style: monitor_orchestrator_health calls load_dotenv() and sys.path.insert() at
# MODULE scope, and an ImportError must not be able to stop this validator alerting.
#
# The crontab window gate the monitor needed is already supplied here by this script's
# own cron line (4,9,...,59 03-09 * * 1-5), so only the calendar gate and the dedupe
# are added. Nothing here changes which contracts are checked or their thresholds.

_DEDUPE_FALLBACK_MIN = 30  # used only if monitor_orchestrator_health.DEDUPE_MIN is unreadable
_STATE_PATH = Path(__file__).resolve().parent / 'logs' / 'contract_alert_state.json'


def _is_trading_day() -> bool:
    """6a5c0e2's gate helper, with the core gate as a second try.

    FAIL-OPEN, and the direction is deliberate: this gate only ever SUPPRESSES
    sends, so failing open keeps a live alert audible. Rule 18's warning that a
    gate over a wrong calendar is worse than no gate is about gates that suppress
    COMPUTE; this one suppresses only notification.
    """
    try:
        from monitor_orchestrator_health import _default_is_trading_day
        return _default_is_trading_day()
    except Exception as e:  # noqa: BLE001
        print(f'[GATE] monitor helper unavailable ({e}); trying the core gate directly')
    try:
        from core.trading_calendar_gate import is_trading_day_today
        return is_trading_day_today()
    except Exception as e:  # noqa: BLE001
        print(f'[GATE] calendar gate unavailable ({e}); failing open (treat as trading day)')
        return True


def _dedupe_min() -> int:
    try:
        from monitor_orchestrator_health import DEDUPE_MIN
        return int(DEDUPE_MIN)
    except Exception:  # noqa: BLE001
        return _DEDUPE_FALLBACK_MIN


def _load_state():
    """6a5c0e2's AlertState: per-key records, atomic write, fresh interpreter per run.

    Returns None if it cannot be loaded, and _send_deduped then sends WITHOUT dedupe
    rather than going quiet -- a broken state file must not silence the channel.
    """
    try:
        from monitor_orchestrator_health import AlertState
        return AlertState(_STATE_PATH).load()
    except Exception as e:  # noqa: BLE001
        print(f'[DEDUPE] state unavailable ({e}); sending without dedupe this run')
        return None


def _send_deduped(state, key: str, sender, message: str, context: dict) -> bool:
    """30-minute dedupe around ONE send site, keyed PER CONTRACT.

    PER-KEY, not one merged key, and that differs from 6a5c0e2 on purpose. The
    monitor merged its two conditions because they were one fault with one remedy
    flapping between two names at a */1 cadence. These four sites are different
    contracts with different remedies -- a stale chain and a duplicate run_id are
    not one incident -- and this script runs */5, so merging would hide whichever
    arrived second. No hold-down either: there is no RECOVERED message here to
    manufacture, which is what the hold-down existed to prevent.

    State is recorded on ATTEMPT, matching _emit's behaviour in the monitor: a
    delivery failure is logged, not retried into a loop.
    """
    now = datetime.utcnow()
    if state is None:
        return bool(sender(message, context=context))

    rec = state.data.get(key)
    if rec is not None:
        try:
            age_min = (now - datetime.fromisoformat(rec['last_sent'])).total_seconds() / 60.0
        except Exception:  # noqa: BLE001
            age_min = None  # corrupt record: treat as new, never suppress forever
        if age_min is not None and age_min < _dedupe_min():
            print(f'[DEDUPE] {key} suppressed: last sent {age_min:.0f}m ago, '
                  f're-notify at {_dedupe_min()}m')
            return False

    first_seen = (rec or {}).get('first_seen') or now.isoformat()
    sends = int((rec or {}).get('sends', 0)) + 1
    state.data[key] = {'first_seen': first_seen, 'last_sent': now.isoformat(),
                       'sends': sends, 'clear_streak': 0, 'variant': None}
    ctx = dict(context, first_seen=first_seen, sends=sends)
    if sends > 1:
        message = f'{message} (still failing)'
    ok = bool(sender(message, context=ctx))
    print(f'[SENT] {key}: {message} (delivered={ok})')
    return ok


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
        self.state = _load_state()   # S92: None is tolerated, see _send_deduped
    
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
                _send_deduped(self.state, 'contract_option_chain_stale',
                              send_warning, msg, {'threshold_min': 5})
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
                _send_deduped(self.state, 'contract_spot_stale', send_warning, msg,
                              {'threshold_min': 1, 'table': 'market_spot_snapshots'})
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
                _send_deduped(self.state, 'contract_duplicate_run_id', send_critical, msg, {
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
            # S92: TD-S91-NEW-14. The old text read 'skipping this cycle'. This
            # script skips NOTHING. It exits non-zero into
            # `>> logs/contract_check.log 2>&1`, and the orchestrator's cron line
            # (*/5 03-09 * * 1-5) is independent of this one
            # (4,9,...,59 03-09 * * 1-5), so the compute cycle runs regardless.
            #
            # 'no scheduled consumer' is the MEASURED form, and the enumeration
            # behind it is in scratch/s92/patch_s92_contract_gate_dedupe.py: the
            # orchestrator's step list (execute_pipeline, :230-287), shell
            # wrappers, systemd units, every crontab on the box and the log file
            # itself were all walked, not just the crontab. What that cannot see
            # is a dynamically constructed invocation.
            #
            # NO skip control was added, deliberately -- making the claim true is
            # a design change (a computed verdict needs a named, scheduled
            # consumer) and needs its own ruling. Do not do both halves silently.
            _send_deduped(
                self.state, 'contract_violations_summary',
                lambda m, context: send_alert(m, level='WARNING', context=context),
                'Compute contracts violated; the compute cycle runs anyway '
                '(advisory check -- no scheduled consumer reads its exit code)',
                {'num_violations': len(self.violations)},
            )
            return False
        
        self.log('INFO', '=== ALL CONTRACTS PASSED ===')
        return True

if __name__ == '__main__':
    # S92: trading-day gate (TD-S91-NEW-13). Cron already scopes this script to
    # weekday 03-09 UTC, so the remaining flood window is a weekday HOLIDAY:
    # 84 runs x 2 surviving sends (run() short-circuits on the first failure)
    # = ~168 messages, next due Tue 2026-10-20. On a non-trading day there is
    # nothing to validate and nothing to report, so exit 0 before any check.
    if not _is_trading_day():
        print('[HOLIDAY GATE] Not a trading day -- no contract checks, no alerts.')
        sys.exit(0)

    validator = ContractValidator()
    try:
        success = validator.run()
    finally:
        # Save the dedupe record even if run() RAISED. Without the finally, an
        # exception after a send loses last_sent, and the next */5 run re-sends
        # the same condition immediately -- which is the flood this TD is about,
        # arriving by the one path the dedupe would not cover. A raise still
        # propagates: the exit status below is not reached.
        if validator.state is not None:
            validator.state.save()

    # Exit 0 if contracts pass, 1 if violated.
    # TD-S91-NEW-14: no scheduled consumer reads this exit code -- the
    # orchestrator's cron line is independent of this script's. It is advisory,
    # and the alert text now says so.
    sys.exit(0 if success else 1)
