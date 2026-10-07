#!/usr/bin/env python3
"""Health monitor daemon for MERDIAN -- orchestrator liveness.

Scheduled: `*/1 * * * *` (every minute, 24x7) -> `logs/monitor.log`.

WHY THIS FILE WAS GATED (AM-2 / S91)
------------------------------------
The orchestrator it watches runs `*/5 03-09 * * 1-5` UTC, so for roughly 17 hours of
every day and all weekend "no orchestrator runs in the last 5 minutes" is the CORRECT
state of the system. The pre-S91 body sent a Telegram warning on that condition on every
one of those minutes:

    if not rows:
        self.log('WARNING', 'No orchestrator runs in last 5 minutes')
        send_warning('Orchestrator not firing', {'gap_minutes': 5})

Measured 2026-10-07: 366 of those lines in the live `logs/monitor.log`, ~1,000 sends a
night, and the operator's alert chat at 4.1k unread and muted. That is the real cost --
the 09:10 IST wsfeed outage alert (TD-S91-NEW-3) landed in a muted chat and was not seen.
An alert channel nobody can read is worse than no alert channel, because it still reports
as instrumented.

So: a send now requires BOTH gates, and the orchestrator's schedule is READ rather than
assumed.

  1. today is a trading day        -- core.trading_calendar_gate.is_trading_day_today
  2. now is inside the orchestrator's own window, + a start grace
                                   -- parsed from `crontab -l`, not hardcoded

Outside either gate: the check still runs and still logs; it does not send.

FLAPPING -- why there is ONE key and a HOLD-DOWN (operator ruling, 2026-10-07)
------------------------------------------------------------------------------
The gate alone was not enough, and this was found by replaying the real log rather than
by review. Today's observed sequence (tests/fixtures/monitor_conditions_2026-10-07.tsv,
947 minutes) changes condition on 119 adjacent minute pairs inside the band, so NOTHING
ever stayed active for 30 minutes and the re-notify dedupe engaged exactly zero times.
With two keys and an immediate RECOVERED that cost 148 sends for the day: 74 episodes,
each an alert plus a RECOVERED, in perfect symmetry.

Two changes, and each absorbs a different half of that:
  * ONE key (CONDITION_KEY) absorbs the NOT_FIRING <-> FAILED alternation -- 19 of the
    episodes, every one of which was a single not-firing minute immediately followed by
    a failed minute.
  * the HOLD-DOWN absorbs FAILED -> OK -> FAILED, which merging the keys cannot: an OK
    minute is a genuine clear, so without a hold-down it ends the episode and the next
    failed minute opens a new one. This was the larger half.
The two are not alternatives, and the split between them is measured, not estimated --
the test replays the fixture through BOTH and through one-key-alone as a control.

WHAT WOULD MAKE THIS GATE FAIL (Rule 0, stated before the code)
---------------------------------------------------------------
  * `in_alert_window` returning True off-session -> tests/test_monitor_orchestrator_gate.py
    scenario 1 counts 60 off-session sends against the pre-S91 replica and 0 against this
    code. A gate asserted only against its own code cannot fail for the reason it names,
    so the replica is what makes that cell a test.
  * a window parser that ignores its input -> scenario 7 parses the real crontab line AND
    a different one (`*/3 04-08`) and asserts DIFFERENT windows. A parser returning a
    constant passes the first and fails the second.
  * dedupe state that does not survive the process -> cron starts a NEW interpreter every
    minute, so every scenario constructs a NEW HealthMonitor per simulated tick and the
    state must come back off disk. In-memory dedupe would pass a single-process test and
    send 60 times in production.
  * a gate so tight it silences a real failure -> scenarios 2/3 assert sends DO happen
    in-session (1 across 29 min, 2 across 60 min at the 30-min re-notify), and the
    crontab-parse failure path falls back to DEFAULT_WINDOW loudly rather than to silence.
  * dedupe that collapses under flapping -> the fixture scenario replays 947 real observed
    minutes and asserts the send count against an INDEPENDENT episode model, with
    one-key-and-no-hold-down as the control. This is the cell the first version of this
    file lacked, which is why 40/40 passed over a design that still sent 148 times.
  * a hold-down fed by non-observations -> an UNKNOWN tick (probe unreadable) must not
    accrue, so 12 consecutive probe failures over an active alert assert 0 RECOVERED.

RESIDUAL RISK, stated rather than designed away
-----------------------------------------------
  * An orchestrator problem that starts and ends entirely outside 03:10-10:00 UTC is not
    alerted. Nothing is scheduled then, so there is nothing to alert about -- but if the
    orchestrator is ever moved to a wider window WITHOUT the crontab line changing (e.g.
    launched by hand, or by a systemd unit), this gate will not know. Measured 2026-10-07:
    it is cron-only, no systemd unit, and nothing spawns it as a subprocess.
  * If the orchestrator's crontab line is DELETED, the parse fails and the fallback window
    is used, so the monitor keeps alerting over the old window rather than going quiet.
    That is the intended direction of failure.
  * An alert still active when the window closes is dropped WITHOUT a RECOVERED message
    ([STATE_RESET]). Out of band the condition carries no information, so there is nothing
    to recover against; the next session re-evaluates from scratch.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import requests
from dotenv import load_dotenv

ENGINE_DIR = '/home/ssm-user/meridian-engine'
load_dotenv(f'{ENGINE_DIR}/.env')

sys.path.insert(0, ENGINE_DIR)
try:
    from telegram_utils import send_alert, send_critical, send_warning
except ImportError:
    def send_alert(*args, **kwargs): return False
    def send_critical(*args, **kwargs): return False
    def send_warning(*args, **kwargs): return False

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# ---- schedule / gating constants --------------------------------------------------
ORCHESTRATOR_SCRIPT = 'run_merdian_shadow_runner_aws.py'
LOOKBACK_MIN = 5    # the "no runs in last N minutes" probe window (unchanged)
GRACE_MIN = 10      # no "not firing" alert for N min after the window opens: at 03:00
                    # UTC the first cycle has not yet written a row, so the condition is
                    # true for a reason that is not a defect
DEDUPE_MIN = 30     # the same condition re-notifies at most this often
STATE_FILENAME = 'monitor_alert_state.json'

# ONE condition key. "not firing" and "failed" are the same fault with the same remedy
# and the same subject; keying them separately turned one flapping incident into two
# alternating alerts, which is what the 2026-10-07 replay measured (see §FLAPPING below).
# The variant travels in the message and the context, not in the key.
CONDITION_KEY = 'orchestrator_unhealthy'

# Consecutive CLEAR ticks required before RECOVERED is sent and the state dropped.
# Ten, by operator ruling, and the reason is the probe's own geometry: the monitor looks
# back LOOKBACK_MIN=5 minutes every 1 minute, so a SINGLE SUCCESSFUL cycle sitting in that
# look-back reads OK for up to 5 consecutive ticks. A 5-tick hold-down is therefore
# satisfiable by one good cycle between two failing ones, and cannot tell recovery from a
# single success; 10 ticks is two orchestrator cycles, which one success cannot span.
# (A MISSED cycle is not the hazard here -- it reads NOT_FIRING, which is unhealthy, not
# clear.)
HOLDDOWN_TICKS = 10


def _headers() -> dict[str, str]:
    return {
        'apikey': SUPABASE_SERVICE_ROLE_KEY or '',
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY or ""}',
        'Content-Type': 'application/json',
    }


def _hhmm(minute_of_day: int) -> str:
    return f'{minute_of_day // 60:02d}:{minute_of_day % 60:02d}'


class QueryFailed(Exception):
    """A non-200 from the ledger read. Logged, never alerted -- same as pre-S91."""


# ---- the orchestrator's window, read from the crontab -----------------------------
@dataclass(frozen=True)
class Window:
    """When the orchestrator is scheduled, in UTC minutes-of-day.

    `first_start_min` / `last_start_min` are the FIRST and LAST scheduled start, so the
    alertable band is [first + GRACE_MIN, last + step_min): one more cycle length at the
    end, because the last cycle's row is only visible after it runs.
    """
    first_start_min: int
    last_start_min: int
    step_min: int
    dows: frozenset        # isoweekday ints, Mon=1 .. Sun=7
    source: str

    @property
    def alert_from_min(self) -> int:
        return self.first_start_min + GRACE_MIN

    @property
    def alert_to_min(self) -> int:      # exclusive
        return self.last_start_min + self.step_min

    def describe(self) -> str:
        return (f'{_hhmm(self.alert_from_min)}-{_hhmm(self.alert_to_min)} UTC '
                f'dow {sorted(self.dows)} step {self.step_min}m [{self.source}]')


# Used only when the crontab cannot be parsed. Mirrors the line measured 2026-10-07:
#   */5 03-09 * * 1-5 ... run_merdian_shadow_runner_aws.py
DEFAULT_WINDOW = Window(
    first_start_min=3 * 60,
    last_start_min=9 * 60 + 55,
    step_min=5,
    dows=frozenset({1, 2, 3, 4, 5}),
    source='fallback:default',
)


def _expand_field(field: str, lo: int, hi: int) -> set[int]:
    """Expand one cron field. Supports `*`, `*/N`, `A`, `A-B`, `A-B/N` and comma lists.
    Anything else raises, so an unrecognised schedule falls back loudly."""
    out: set[int] = set()
    for part in field.split(','):
        step = 1
        if '/' in part:
            part, _, step_s = part.partition('/')
            step = int(step_s)
            if step <= 0:
                raise ValueError(f'bad step in {field!r}')
        if part == '*':
            a, b = lo, hi
        elif '-' in part:
            a_s, _, b_s = part.partition('-')
            a, b = int(a_s), int(b_s)
        else:
            a = b = int(part)
        if not (lo <= a <= hi and lo <= b <= hi and a <= b):
            raise ValueError(f'{part!r} out of range [{lo},{hi}] in {field!r}')
        out.update(range(a, b + 1, step))
    if not out:
        raise ValueError(f'empty field {field!r}')
    return out


def parse_orchestrator_window(crontab_text: str,
                              script: str = ORCHESTRATOR_SCRIPT) -> Window:
    """Derive the orchestrator's window from crontab text. Raises if it cannot."""
    for raw in crontab_text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or script not in line:
            continue
        fields = line.split(None, 5)
        if len(fields) < 6:
            continue
        minute_f, hour_f, dom_f, mon_f, dow_f = fields[:5]
        # A day-of-month or month restriction would make this window wrong on some days.
        # Refuse rather than ignore the field: the fallback is visible, a silently
        # dropped field is not.
        if dom_f != '*' or mon_f != '*':
            raise ValueError(f'unsupported dom/month fields {dom_f!r}/{mon_f!r}')
        minutes = sorted(_expand_field(minute_f, 0, 59))
        hours = sorted(_expand_field(hour_f, 0, 23))
        # cron day-of-week: 0 and 7 are both Sunday; isoweekday has Sunday as 7.
        dows = frozenset(7 if d == 0 else d for d in _expand_field(dow_f, 0, 7))
        step = min((b - a for a, b in zip(minutes, minutes[1:])), default=60)
        return Window(
            first_start_min=hours[0] * 60 + minutes[0],
            last_start_min=hours[-1] * 60 + minutes[-1],
            step_min=step,
            dows=dows,
            source='crontab',
        )
    raise ValueError(f'no enabled crontab line mentioning {script}')


def _read_crontab() -> str:
    try:
        r = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
        return r.stdout if r.returncode == 0 else ''
    except Exception as e:                                    # noqa: BLE001
        print(f'[WINDOW] crontab -l failed ({e})')
        return ''


def resolve_window(crontab_text: Optional[str] = None) -> Window:
    """Parse the live crontab; on any failure fall back to DEFAULT_WINDOW, loudly."""
    text = _read_crontab() if crontab_text is None else crontab_text
    try:
        return parse_orchestrator_window(text)
    except Exception as e:                                    # noqa: BLE001
        print(f'[WINDOW] could not read the orchestrator schedule ({e}); '
              f'falling back to {DEFAULT_WINDOW.describe()}')
        return DEFAULT_WINDOW


def in_alert_window(now_utc: datetime, window: Window) -> tuple[bool, str]:
    """Is `now_utc` inside the alertable band? Returns (ok, human reason)."""
    mod = now_utc.hour * 60 + now_utc.minute
    dow = now_utc.isoweekday()
    if dow not in window.dows:
        return False, (f'dow {dow} not in the orchestrator schedule '
                       f'{sorted(window.dows)} [{window.source}]')
    if mod < window.alert_from_min:
        return False, (f'{_hhmm(mod)} UTC is before the window start + {GRACE_MIN}m grace '
                       f'({_hhmm(window.alert_from_min)}) [{window.source}]')
    if mod >= window.alert_to_min:
        return False, (f'{_hhmm(mod)} UTC is after the last cycle + {window.step_min}m '
                       f'({_hhmm(window.alert_to_min)}) [{window.source}]')
    return True, f'inside {window.describe()}'


def _default_is_trading_day() -> bool:
    """Shared gate (CLAUDE.md rule 18 -- never roll a new inline copy). Fail-open, which
    is that module's own contract: a calendar hiccup must not silence a live alert."""
    try:
        from core.trading_calendar_gate import is_trading_day_today
        return is_trading_day_today()
    except Exception as e:                                    # noqa: BLE001
        print(f'[GATE] calendar gate unavailable ({e}); failing open (treat as trading day)')
        return True


def _default_send(level: str, message: str, context: dict[str, Any]) -> bool:
    if level == 'CRITICAL':
        return send_critical(message, context=context)
    if level == 'WARNING':
        return send_warning(message, context=context)
    return send_alert(message, level=level, context=context)


# ---- dedupe state -----------------------------------------------------------------
class AlertState:
    """Per-condition alert state, persisted because cron gives each tick a fresh process.

    Shape: {"<condition key>": {"first_seen": iso, "last_sent": iso, "sends": int}}.
    A key present means the condition is currently active; absent means clear.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.data: dict[str, dict[str, Any]] = {}

    def load(self) -> 'AlertState':
        try:
            loaded = json.loads(self.path.read_text())
            self.data = loaded if isinstance(loaded, dict) else {}
        except FileNotFoundError:
            self.data = {}
        except Exception as e:                                # noqa: BLE001
            print(f'[STATE] unreadable ({e}); starting from empty')
            self.data = {}
        return self

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + '.tmp')
            tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True))
            tmp.replace(self.path)                            # atomic for a 1-min cron
        except Exception as e:                                # noqa: BLE001
            print(f'[STATE] could not be written ({e}); dedupe will restart next tick')

    def keys(self) -> list[str]:
        return list(self.data.keys())

    def clear_all(self) -> int:
        n = len(self.data)
        self.data = {}
        return n


# ---- the monitor ------------------------------------------------------------------
class HealthMonitor:
    """Every collaborator is injectable so the gate can be tested without a clock, a
    calendar, a database or a Telegram token."""

    def __init__(self,
                 now_utc: Optional[datetime] = None,
                 send: Optional[Callable[[str, str, dict], bool]] = None,
                 is_trading_day: Optional[Callable[[], bool]] = None,
                 window: Optional[Window] = None,
                 state_path: Optional[Path | str] = None,
                 fetch_rows: Optional[Callable[[], list]] = None):
        self.now = now_utc or datetime.now(timezone.utc)
        self.ts = self.now                                    # log() format, unchanged
        self._send = send if send is not None else _default_send
        self._is_trading_day = is_trading_day if is_trading_day is not None else _default_is_trading_day
        self.window = window if window is not None else resolve_window()
        self.state_path = Path(state_path) if state_path is not None else (
            Path(__file__).resolve().parent / 'logs' / STATE_FILENAME)
        self._fetch_rows = fetch_rows if fetch_rows is not None else self._fetch_rows_http
        self.alerts: list[dict[str, str]] = []
        self.sent: list[tuple[str, str]] = []                 # (level, message) actually sent

    def log(self, level: str, msg: str) -> None:
        print(f"[{self.ts.strftime('%H:%M:%S')}] {level}: {msg}")
        self.alerts.append({'level': level, 'msg': msg})

    # ---- the probe ----------------------------------------------------------------
    def _fetch_rows_http(self) -> list:
        # Naive-UTC isoformat, byte-identical to the pre-S91 query: changing the filter's
        # shape is not part of this fix.
        since = (self.now.replace(tzinfo=None) - timedelta(minutes=LOOKBACK_MIN)).isoformat()
        url = (f'{SUPABASE_URL}/rest/v1/script_execution_log'
               f'?script_name=eq.{ORCHESTRATOR_SCRIPT}&created_at=gt.{since}'
               f'&order=created_at.desc&limit=10')
        resp = requests.get(url, headers=_headers(), timeout=5)
        if resp.status_code != 200:
            raise QueryFailed(str(resp.status_code))
        return resp.json()

    def check_orchestrator_failures(self) -> tuple[dict[str, tuple[str, str, dict]], bool]:
        """Observe conditions; do not send. Returns (conditions, probe_ok).

        Splitting observation from notification is what lets the gate sit in one place
        instead of beside every send -- the pre-S91 shape had the send inline, which is
        why adding a second condition would have meant a second ungated send.

        `probe_ok` is False when the ledger could not be READ. That is a third state,
        UNKNOWN, and it is deliberately not collapsed into either of the other two: an
        empty condition dict from a successful read means "healthy", while an empty dict
        from a failed read means "no information". Treating the second as healthy would
        let 10 consecutive query failures accrue a full hold-down and emit a RECOVERED for
        a condition nobody observed clearing (operator ruling, 2026-10-07).
        """
        conditions: dict[str, tuple[str, str, dict]] = {}
        try:
            rows = self._fetch_rows()
        except QueryFailed as e:
            # Logged, not alerted -- unchanged from pre-S91. A flaky ledger read is not
            # an orchestrator defect, and making it one adds a third flood source.
            self.log('ERROR', f'Supabase query failed: {e}')
            return conditions, False
        except Exception as e:                                # noqa: BLE001
            self.log('ERROR', f'Orchestrator check failed: {e}')
            return conditions, False

        if not rows:
            self.log('WARNING', 'No orchestrator runs in last 5 minutes')
            conditions[CONDITION_KEY] = (
                'WARNING', 'Orchestrator not firing',
                {'variant': 'not_firing', 'gap_minutes': LOOKBACK_MIN})
            return conditions, True

        for row in rows:
            if row.get('exit_code') != 0:
                msg = (f"Orchestrator FAILED: exit_code={row.get('exit_code')}, "
                       f"duration={row.get('duration_ms')}ms")
                self.log('CRITICAL', msg)
                conditions[CONDITION_KEY] = ('CRITICAL', msg, {
                    'variant': 'failed',
                    'exit_code': row.get('exit_code'),
                    'duration_ms': row.get('duration_ms'),
                    'created_at': row.get('created_at'),
                })
                return conditions, True

        self.log('INFO', f'Orchestrator OK ({len(rows)} runs in 5min)')
        return conditions, True

    # ---- gating -------------------------------------------------------------------
    def gate(self) -> tuple[bool, str]:
        """Window first (free), calendar second (a network read). On a closed weekend
        night this never touches the network."""
        ok, reason = in_alert_window(self.now, self.window)
        if not ok:
            return False, reason
        try:
            if not self._is_trading_day():
                return False, 'trading_calendar says today is not a trading day'
        except Exception as e:                                # noqa: BLE001
            self.log('WARNING', f'calendar gate raised ({e}); failing open')
        return True, reason

    # ---- notification -------------------------------------------------------------
    def _emit(self, level: str, message: str, context: dict[str, Any]) -> None:
        ok = self._send(level, message, context)
        self.sent.append((level, message))
        self.log('INFO', f'[SENT] {level}: {message} (delivered={bool(ok)})')

    def _maybe_send(self, state: AlertState, key: str,
                    level: str, message: str, context: dict[str, Any]) -> None:
        rec = state.data.get(key)
        now_iso = self.now.isoformat()
        fresh = {'first_seen': now_iso, 'last_sent': now_iso, 'sends': 1,
                 'clear_streak': 0, 'variant': context.get('variant')}
        if rec is None:
            state.data[key] = fresh
            self._emit(level, message, dict(context, first_seen=now_iso))
            return
        try:
            last_sent = datetime.fromisoformat(rec['last_sent'])
            first_seen = datetime.fromisoformat(rec['first_seen'])
        except Exception:                                     # noqa: BLE001
            # Corrupt record: treat as new rather than suppress forever.
            state.data[key] = fresh
            self._emit(level, message, dict(context, first_seen=now_iso))
            return

        # The condition is active again, so any accumulated hold-down is void. This is
        # the clause that absorbs a flap: a variant change, or a clear shorter than the
        # hold-down, costs a log line and nothing else.
        streak = int(rec.get('clear_streak', 0))
        if streak:
            self.log('INFO', f'[HOLDDOWN_RESET] {key} re-asserted after {streak} clear '
                             f'tick(s); RECOVERED not sent')
        rec['clear_streak'] = 0
        prev_variant = rec.get('variant')
        rec['variant'] = context.get('variant')
        if prev_variant != rec['variant']:
            self.log('INFO', f'[VARIANT] {key} {prev_variant} -> {rec["variant"]} '
                             '(same condition, no new alert)')

        age_min = (self.now - last_sent).total_seconds() / 60.0
        if age_min >= DEDUPE_MIN:
            rec['last_sent'] = now_iso
            rec['sends'] = int(rec.get('sends', 1)) + 1
            active_min = int((self.now - first_seen).total_seconds() / 60.0)
            self._emit(level, f'{message} (still failing)',
                       dict(context, active_for_min=active_min, sends=rec['sends']))
        else:
            self.log('INFO', f'[DEDUPE] {key} suppressed: last sent {age_min:.0f}m ago, '
                             f're-notify at {DEDUPE_MIN}m')

    def _tick_clear(self, state: AlertState, key: str) -> None:
        """The condition was NOT observed this tick. Count toward the hold-down; send
        RECOVERED only once HOLDDOWN_TICKS consecutive clear ticks have accrued."""
        rec = state.data.get(key)
        if rec is None:
            return
        streak = int(rec.get('clear_streak', 0)) + 1
        rec['clear_streak'] = streak
        if streak >= HOLDDOWN_TICKS:
            self._send_recovered(state, key, streak)
        else:
            self.log('INFO', f'[HOLDDOWN] {key} clear {streak}/{HOLDDOWN_TICKS} tick(s); '
                             'RECOVERED withheld')

    def _send_recovered(self, state: AlertState, key: str, clear_ticks: int = 0) -> None:
        rec = state.data.pop(key, {}) or {}
        try:
            active_min = int((self.now - datetime.fromisoformat(rec['first_seen'])).total_seconds() / 60.0)
        except Exception:                                     # noqa: BLE001
            active_min = -1
        self._emit('INFO', f'RECOVERED: {key}', {
            'active_for_min': active_min,
            'alerts_sent': rec.get('sends', 0),
            'clear_ticks': clear_ticks,
            'last_variant': rec.get('variant'),
        })

    # ---- entrypoint ---------------------------------------------------------------
    def run(self) -> bool:
        self.log('INFO', '=== HEALTH CHECK START ===')
        conditions, probe_ok = self.check_orchestrator_failures()
        state = AlertState(self.state_path).load()
        gated, reason = self.gate()

        if not gated:
            self.log('INFO', f'[GATED] logging only, no sends: {reason}')
            dropped = state.clear_all()
            if dropped:
                self.log('INFO', f'[STATE_RESET] dropped {dropped} active alert(s) with no '
                                 'RECOVERED: out of band the condition carries no information')
                state.save()
        elif not probe_ok:
            # UNKNOWN: the ledger could not be read, so this minute is evidence of
            # nothing. No alert, and critically NO hold-down progress -- counting it as
            # a clear tick would let a run of query failures emit a RECOVERED for a
            # condition that was never observed clearing.
            self.log('INFO', '[UNKNOWN] probe unreadable this tick: no send, and no '
                             'hold-down progress')
        else:
            for key, (level, message, context) in sorted(conditions.items()):
                self._maybe_send(state, key, level, message, context)
            for key in sorted(set(state.keys()) - set(conditions)):
                self._tick_clear(state, key)
            state.save()

        self.log('INFO', '=== HEALTH CHECK END ===')
        return len([a for a in self.alerts if a['level'] in ['CRITICAL', 'ERROR']]) == 0


def main() -> int:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print('[FATAL] SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set')
        return 1
    return 0 if HealthMonitor().run() else 1


if __name__ == '__main__':
    sys.exit(main())
