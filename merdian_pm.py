"""
merdian_pm.py  --  MERDIAN Process Manager (core library)
==========================================================
Tracks PIDs in runtime/merdian_pids.json.
Starts processes as background (no terminal window).
Logs to logs/pm_<name>.log.

Rules:
  - One instance per named process. Rejects duplicate starts.
  - stop() kills registered + any unregistered instances of same script.
  - stop_all() is always safe — cleans dead entries too.
  - Port conflict checked before starting dashboards.
"""

import os, sys, json, time, socket, subprocess, psutil
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

IST      = ZoneInfo("Asia/Kolkata")
BASE     = Path(r'C:\GammaEnginePython')
RUNTIME  = BASE / 'runtime'
LOGS     = BASE / 'logs'
PID_FILE = RUNTIME / 'merdian_pids.json'
PYTHON   = Path(sys.executable)

RUNTIME.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

PROCESSES = {
    'health_monitor':   {'script': 'merdian_live_dashboard.py', 'args': ['--no-browser'], 'port': 8765, 'desc': 'Health Monitor'},
    'signal_dashboard': {'script': 'merdian_signal_dashboard.py', 'port': 8766, 'desc': 'Signal Dashboard'},
    'supervisor':       {'script': 'gamma_engine_supervisor.py',  'port': None, 'desc': 'Supervisor'},
    'exit_monitor':     {'script': 'merdian_exit_monitor.py',     'port': None, 'desc': 'Exit Monitor'},
    'pipeline_alert':   {'script': 'merdian_pipeline_alert_daemon.py', 'port': None, 'desc': 'Pipeline Alert Daemon (ENH-73)'},
}

# ── Registry ──────────────────────────────────────────────────────────────────

def load_reg():
    try:
        if PID_FILE.exists():
            return json.loads(PID_FILE.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}

def save_reg(reg):
    PID_FILE.write_text(json.dumps(reg, indent=2), encoding='utf-8')

def register(name, pid, script):
    reg = load_reg()
    reg[name] = {'pid': pid, 'script': script, 'started': datetime.now(timezone.utc).isoformat()}
    save_reg(reg)

def unregister(name):
    reg = load_reg(); reg.pop(name, None); save_reg(reg)

# ── Checks ────────────────────────────────────────────────────────────────────

def is_alive(pid):
    try:
        p = psutil.Process(pid)
        return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False

def port_in_use(port):
    try:
        with socket.socket() as s:
            s.settimeout(1)
            return s.connect_ex(('localhost', port)) == 0
    except Exception:
        return False

def find_pids(script):
    found = []
    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            if script in ' '.join(p.info['cmdline'] or []):
                found.append(p.info['pid'])
        except Exception:
            pass
    return found

# ── Start / stop ──────────────────────────────────────────────────────────────

def start(name, force=False):
    if name not in PROCESSES:
        return False, f"Unknown: {name}"

    cfg = PROCESSES[name]
    script = cfg['script']
    port   = cfg.get('port')

    # Registry check
    reg = load_reg()
    if name in reg:
        pid = reg[name]['pid']
        if is_alive(pid):
            if not force:
                return False, f"Already running (PID {pid})"
            stop(name)
        else:
            unregister(name)

    # Unregistered duplicates
    existing = find_pids(script)
    if existing:
        if not force:
            return False, f"Unregistered instance(s): PIDs {existing}. Use force=True."
        for pid in existing:
            try: psutil.Process(pid).kill()
            except Exception: pass
        time.sleep(0.5)

    # Port conflict
    if port and port_in_use(port):
        return False, f"Port {port} in use"

    script_path = BASE / script
    if not script_path.exists():
        return False, f"Script not found: {script_path}"

    log_file = LOGS / f'pm_{name}.log'
    CREATE_NO_WINDOW = 0x08000000
    DETACHED_PROCESS = 0x00000008

    _log_header = f"\n{'='*50}\nStarted {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}\n{'='*50}\n"
    _lf = open(str(log_file), 'a', encoding='utf-8')
    _lf.write(_log_header)
    _lf.flush()

    proc = subprocess.Popen(
        [str(PYTHON), '-u', str(script_path)] + cfg.get('args', []),
        cwd=str(BASE),
        stdout=_lf,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )
    time.sleep(1.5)

    if not is_alive(proc.pid):
        return False, f"Died immediately — check logs/pm_{name}.log"

    register(name, proc.pid, script)
    return True, f"Started PID {proc.pid} → logs/pm_{name}.log"


def stop(name):
    reg = load_reg()
    pids = set()
    if name in reg:
        pids.add(reg[name]['pid'])
    if name in PROCESSES:
        pids.update(find_pids(PROCESSES[name]['script']))

    if not pids:
        unregister(name)
        return True, "Not running"

    killed = []
    for pid in pids:
        try:
            p = psutil.Process(pid)
            p.terminate()
            try: p.wait(timeout=3)
            except psutil.TimeoutExpired: p.kill()
            killed.append(pid)
        except Exception:
            killed.append(pid)

    unregister(name)
    return True, f"Killed PIDs {killed}"


def stop_all():
    results = []
    for name in PROCESSES:
        ok, msg = stop(name)
        results.append((name, msg))
    reg = load_reg()
    for name in list(reg):
        if not is_alive(reg[name]['pid']):
            unregister(name)
    return results

# ── Status ────────────────────────────────────────────────────────────────────

def status():
    reg = load_reg()
    now = datetime.now(timezone.utc)
    rows = []
    for name, cfg in PROCESSES.items():
        e = {'name': name, 'desc': cfg['desc'], 'script': cfg['script'],
             'port': cfg.get('port'), 'alive': False, 'pid': None,
             'uptime': None, 'started': None, 'port_ok': None, 'dupes': []}
        if name in reg:
            pid = reg[name]['pid']
            e['pid'] = pid
            e['alive'] = is_alive(pid)
            try:
                st   = datetime.fromisoformat(reg[name]['started'])
                secs = int((now - st).total_seconds())
                h, r = divmod(secs, 3600); m, s = divmod(r, 60)
                e['uptime']  = f"{h}h {m:02d}m {s:02d}s"
                e['started'] = st.astimezone(IST).strftime('%H:%M:%S IST')
            except Exception:
                pass
        all_pids = find_pids(cfg['script'])
        e['dupes'] = [p for p in all_pids if p != e['pid']]
        if cfg.get('port'):
            e['port_ok'] = port_in_use(cfg['port'])
        rows.append(e)
    return rows

def print_status():
    rows = status()
    now  = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')
    print(f"\n  MERDIAN Process Status  —  {now}")
    print(f"  {'='*70}")
    print(f"  {'Name':<20} {'Status':<12} {'PID':>7}  {'Started':<14} {'Port':<6}")
    print(f"  {'-'*70}")
    for r in rows:
        st  = '✓ RUNNING' if r['alive'] else '✗ STOPPED'
        pid = str(r['pid']) if r['pid'] else '—'
        stt = r['started'] or '—'
        prt = str(r['port']) if r['port'] else '—'
        print(f"  {r['name']:<20} {st:<12} {pid:>7}  {stt:<14} {prt:<6}")
        if r['dupes']:
            print(f"  {'':20} ⚠ DUPLICATE PIDs: {r['dupes']}")
    print(f"  {'='*70}")
    print(f"  Registry: {PID_FILE}\n")
