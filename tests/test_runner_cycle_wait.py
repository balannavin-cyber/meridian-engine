#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S98-B / ruling S98-E -- tests for the runner's cycle wait.

Target under test: run_merdian_shadow_runner_aws.py at the repo root -- the LIVE runner
with S98-B applied (S99 A3, sha256 188702c8...). Until S99 A4 this suite targeted the
S98 dry-run copy; a suite that still targeted that copy after apply would not be a
regression test. The runner is loaded from source with its collaborators stubbed
(below), never executed as a script.

What makes these tests rather than documentation (rule 0), stated per cell at the
bottom of each case: every cell names the value that would make it fail, and the
mutant run at the end proves two of them actually do. T2 and T3 are the cells that
carry the patch's whole claim, so mutant M deletes the `ts >= cycle_floor` filter and
asserts BOTH flip to failing. If a mutant run reports ALL PASS, this suite is
documentation and the exit code says so.

The module is imported with its collaborators stubbed in sys.modules BEFORE exec:
  * dotenv.load_dotenv -> no-op. The module calls load_dotenv() at import; the real
    one would read the engine environment file, which this suite must not touch.
  * core.supabase_client / core.execution_log / core.trading_calendar_gate and
    gamma_engine_retry_utils -> stubs. No network, no database, no credentials.
LOG_FILE is repointed at a temp file immediately after import: the module's real
LOG_FILE is /home/ssm-user/meridian-engine/shadow_runner.log, a production log.

No wall-clock sleeping. `fetch_cycle_run_ids`' sleep/clock defaults are rebound via
__defaults__ so main() -- which calls it with two arguments -- still exercises the
real function.

Run:  ( ulimit -v 700000; python3 tests/test_runner_cycle_wait.py )
"""
from __future__ import annotations

import ast
import importlib.util
import io
import re
import sys
import tempfile
import types
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNNER_UNDER_TEST = REPO / "run_merdian_shadow_runner_aws.py"

# The one substring mutant M removes. Kept here so the mutation is a single, asserted
# edit and not a regex over the whole file.
TS_FILTER_SNIPPET = ', "ts": f"gte.{floor_iso}"'

TS_FILTER_RE = re.compile(r"^gte\.\d{4}-\d\d-\d\dT\d\d:\d\d:00Z$")

PREV_TS = "2026-10-26T07:25:00+00:00"      # previous cycle
CUR_TS = "2026-10-26T07:30:00+00:00"       # this cycle
YEST_TS = "2026-10-23T10:10:00+00:00"      # Friday 15:40 IST, the last row of the week
NOW_IN_CYCLE = datetime(2026, 10, 26, 7, 32, 10, tzinfo=timezone.utc)   # 13:02 IST
NOW_PREOPEN = datetime(2026, 10, 26, 3, 0, 0, tzinfo=timezone.utc)      # 08:30 IST

FRONT_EXPIRY = "2026-10-29"
NEXT_EXPIRY = "2026-11-05"


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------
def _parse_ts(s: str) -> datetime:
    """Accept both the '+00:00' form the DB returns and the 'Z' form the code sends."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class FakeTime:
    """Virtual clock. sleep() advances it; nothing ever waits."""

    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


class FakeSB:
    """A select() that really filters, really orders and really limits.

    It has to: a mock returning a canned row would make T6 (front-expiry ordering)
    and T2/T3 (the ts filter) assert nothing at all -- they would pass against any
    filter string, including none.
    """

    def __init__(self, timeline: list[tuple[float, dict]], clock) -> None:
        self.timeline = timeline          # (available_at_seconds, row)
        self.clock = clock
        self.calls: list[dict] = []

    def select(self, table, columns="*", filters=None, limit=None, offset=None,
               order=None, ascending=True):
        f = dict(filters or {})
        self.calls.append({"table": table, "filters": f, "order": order,
                           "limit": limit})

        now = self.clock()
        rows = [r for (avail, r) in self.timeline if avail <= now]

        sym = f.get("symbol", "")
        if sym.startswith("eq."):
            rows = [r for r in rows if r["symbol"] == sym[3:]]
        elif sym:
            raise AssertionError(f"unexpected symbol filter {sym!r}")

        tsf = f.get("ts")
        if tsf is not None:
            if not tsf.startswith("gte."):
                raise AssertionError(f"unexpected ts filter {tsf!r}")
            bound = _parse_ts(tsf[4:])
            rows = [r for r in rows if _parse_ts(r["ts"]) >= bound]

        if order:
            # "ts.desc,expiry_date.asc" -- apply keys right-to-left on a stable sort.
            for part in reversed([p.strip() for p in order.split(",") if p.strip()]):
                col, _, direction = part.partition(".")
                rows = sorted(rows, key=lambda r: r[col],
                              reverse=(direction == "desc"))

        if limit is not None:
            rows = rows[:limit]
        return rows


class FakeLedger:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.reason = None
        self.exit_code = None

    def complete(self, notes=None):
        self.reason = "SUCCESS"
        self.exit_code = 0

    def exit_with_reason(self, reason, exit_code=None, notes=None,
                         error_message=None):
        self.reason = reason
        self.exit_code = exit_code
        self.error_message = error_message


def _row(symbol: str, ts: str, expiry: str, run_id: str) -> dict:
    return {"symbol": symbol, "ts": ts, "expiry_date": expiry, "run_id": run_id}


# ---------------------------------------------------------------------------
# module loading
# ---------------------------------------------------------------------------
def _install_stubs() -> None:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *a, **k: False
    sys.modules["dotenv"] = dotenv

    core = types.ModuleType("core")
    core.__path__ = []
    sys.modules["core"] = core

    tcg = types.ModuleType("core.trading_calendar_gate")
    tcg.is_trading_day_today = lambda: True
    tcg.assert_trading_day_or_exit = lambda log=None: None
    sys.modules["core.trading_calendar_gate"] = tcg
    core.trading_calendar_gate = tcg

    el = types.ModuleType("core.execution_log")
    el.ExecutionLog = FakeLedger
    sys.modules["core.execution_log"] = el
    core.execution_log = el

    sc = types.ModuleType("core.supabase_client")

    class _SB:
        def __init__(self, *a, **k):
            raise AssertionError("the real SupabaseClient must never be constructed")

    sc.SupabaseClient = _SB
    sys.modules["core.supabase_client"] = sc
    core.supabase_client = sc

    reu = types.ModuleType("gamma_engine_retry_utils")

    # Mirrors the REAL signature (gamma_engine_retry_utils.py:10-19) exactly, including
    # the bare `*` -- every option is keyword-only there. A `lambda fn, *a, **k` stub
    # accepts any kwarg name and any positional, so a typo'd `attempt=` or a positional
    # `retry_call(fn, 3)` would pass every cell here and TypeError on the box at 09:15.
    # Declaring the names makes the suite fail where the box would.
    def _retry_call(fn, *, attempts=3, delay_seconds=5.0, backoff_multiplier=1.0,
                    retry_exceptions=(Exception,), retry_predicate=None,
                    label="operation"):
        return fn()

    reu.retry_call = _retry_call
    sys.modules["gamma_engine_retry_utils"] = reu


def _load(path: Path, name: str, source: str | None = None):
    """Import `path` (or `source` written beside it) as module `name`."""
    if source is not None:
        tmpdir = Path(tempfile.mkdtemp(prefix="s98b_mutant_"))
        path = tmpdir / f"{name}.py"
        path.write_text(source, encoding="utf-8")

    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)

    # Repoint the production log path before anything can call log_message.
    mod.LOG_FILE = str(Path(tempfile.gettempdir()) / f"{name}_test.log")
    return mod


def _bind_clock(mod, ft: FakeTime) -> None:
    """Rebind fetch_cycle_run_ids' sleep/clock defaults to the virtual clock.

    Defaults are evaluated at def time, so patching mod.time would not reach them.
    The length assert is what stops this from silently mis-binding if the signature
    ever changes.
    """
    d = mod.fetch_cycle_run_ids.__defaults__
    assert d is not None and len(d) == 2, (
        f"fetch_cycle_run_ids should have exactly 2 defaulted params "
        f"(sleep, clock); found {d!r}"
    )
    mod.fetch_cycle_run_ids.__defaults__ = (ft.sleep, ft.monotonic)


# ---------------------------------------------------------------------------
# cells
# ---------------------------------------------------------------------------
RESULTS: list[tuple[str, bool, str]] = []


def cell(name: str):
    def deco(fn):
        def run(mod):
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    fn(mod)
            except AssertionError as e:
                RESULTS.append((name, False, str(e)))
                return False
            except Exception as e:                            # noqa: BLE001
                RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
                return False
            RESULTS.append((name, True, ""))
            return True
        run.cell_name = name
        return run
    return deco


@cell("T1 current-cycle run lands on the 3rd poll")
def t1(mod):
    ft = FakeTime()
    _bind_clock(mod, ft)
    timeline = [
        (0.0, _row("NIFTY", PREV_TS, FRONT_EXPIRY, "PREV-N")),
        (0.0, _row("SENSEX", PREV_TS, FRONT_EXPIRY, "PREV-S")),
        (10.0, _row("NIFTY", CUR_TS, FRONT_EXPIRY, "CUR-N")),
        (10.0, _row("SENSEX", CUR_TS, FRONT_EXPIRY, "CUR-S")),
    ]
    sb = FakeSB(timeline, ft.monotonic)
    got = mod.fetch_cycle_run_ids(sb, NOW_IN_CYCLE, sleep=ft.sleep,
                                  clock=ft.monotonic)
    assert got == {"NIFTY": "CUR-N", "SENSEX": "CUR-S"}, got
    assert ft.sleeps == [mod.POLL_S, mod.POLL_S], ft.sleeps
    assert ft.t == 10.0, ft.t
    # FAILS IF: the previous-cycle rows (available from t=0) were accepted -- then
    # got would be {PREV-N, PREV-S} and sleeps would be [].


@cell("T2 only previous-cycle run -> SKIPPED_NO_INPUT, pipeline not called")
def t2(mod):
    ft = FakeTime()
    _bind_clock(mod, ft)
    timeline = [
        (0.0, _row("NIFTY", PREV_TS, FRONT_EXPIRY, "PREV-N")),
        (0.0, _row("SENSEX", PREV_TS, FRONT_EXPIRY, "PREV-S")),
    ]
    sb = FakeSB(timeline, ft.monotonic)
    led, calls = _run_main(mod, sb, NOW_IN_CYCLE)
    rc = calls["rc"]
    assert rc == 1, f"exit code {rc}, expected 1"
    assert led.reason == "SKIPPED_NO_INPUT", f"ledger reason {led.reason!r}"
    assert calls["pipeline"] == [], f"pipeline was called: {calls['pipeline']}"
    assert len(ft.sleeps) == 24, f"{len(ft.sleeps)} polls-worth of sleep"
    assert ft.t == float(mod.CYCLE_WAIT_S), ft.t
    # S98-E.1: the reason cannot distinguish stale from absent, so the error text must.
    em = led.error_message or ""
    # The offset check is scoped to the FLOOR phrase only. A blanket `"+00:00" not in
    # em` would contradict the newest-ts asserts below: the probe echoes the DB's own
    # string, which legitimately carries +00:00, so the blanket form can never hold.
    assert "at or after 2026-10-26T07:30:00Z" in em, f"floor not in Z form: {em!r}"
    assert "at or after 2026-10-26T07:30:00+00:00" not in em, f"floor in offset form: {em!r}"
    assert "newest ts" in em, f"'newest ts' not in error_message: {em!r}"
    assert f"NIFTY={PREV_TS}" in em, f"newest NIFTY ts not named: {em!r}"
    assert f"SENSEX={PREV_TS}" in em, f"newest SENSEX ts not named: {em!r}"
    # FAILS IF: the ts filter is absent -- PREV-N/PREV-S qualify, run_ids is
    # non-empty, main computes them and returns 0. This is mutant M's cell.
    # ALSO FAILS IF: the reason reverts to STALE_INPUT (mutant R), or the newest-ts
    # probe is dropped -- then a stalled ingest and an absent one are the same row.


@cell("T3 08:30 IST with yesterday 15:40 newest -> SKIPPED_NO_INPUT")
def t3(mod):
    ft = FakeTime()
    _bind_clock(mod, ft)
    timeline = [
        (0.0, _row("NIFTY", YEST_TS, FRONT_EXPIRY, "YEST-N")),
        (0.0, _row("SENSEX", YEST_TS, FRONT_EXPIRY, "YEST-S")),
    ]
    sb = FakeSB(timeline, ft.monotonic)
    led, calls = _run_main(mod, sb, NOW_PREOPEN)
    assert calls["rc"] == 1, f"exit code {calls['rc']}, expected 1"
    assert led.reason == "SKIPPED_NO_INPUT", f"ledger reason {led.reason!r}"
    assert calls["pipeline"] == [], f"pipeline was called: {calls['pipeline']}"
    em = led.error_message or ""
    assert "at or after 2026-10-26T03:00:00Z" in em, f"floor not in Z form: {em!r}"
    assert "at or after 2026-10-26T03:00:00+00:00" not in em, f"floor in offset form: {em!r}"
    assert "newest ts" in em, f"'newest ts' not in error_message: {em!r}"
    # The whole point of the probe: the text names YESTERDAY, so the operator can
    # tell a dead feed from a late one without opening the ledger.
    assert f"NIFTY={YEST_TS}" in em, f"newest NIFTY ts not named: {em!r}"
    assert f"SENSEX={YEST_TS}" in em, f"newest SENSEX ts not named: {em!r}"
    # FAILS IF: the ts filter is absent -- yesterday's close is the newest row and
    # the whole pre-open compute chain runs on it. This is mutant M's second cell.


@cell("T4 one symbol only -> computes that symbol")
def t4(mod):
    ft = FakeTime()
    _bind_clock(mod, ft)
    timeline = [(0.0, _row("NIFTY", CUR_TS, FRONT_EXPIRY, "CUR-N"))]
    sb = FakeSB(timeline, ft.monotonic)
    led, calls = _run_main(mod, sb, NOW_IN_CYCLE)
    assert calls["rc"] == 0, f"exit code {calls['rc']}, expected 0"
    assert calls["pipeline"] == [{"NIFTY": "CUR-N"}], calls["pipeline"]
    assert led.reason == "SUCCESS", f"ledger reason {led.reason!r}"
    # The cost of the missing symbol, asserted rather than assumed: the cycle still
    # burns the FULL wait before giving up on SENSEX.
    assert len(ft.sleeps) == 24, f"{len(ft.sleeps)} sleeps"
    assert ft.t == float(mod.CYCLE_WAIT_S), ft.t
    # FAILS IF: a missing symbol aborted the cycle (pipeline == []) or the wait
    # short-circuited on the first symbol found (sleeps == []).


@cell("T5 cycle floor at 10:04:59 / 10:05:00 / 10:05:01")
def t5(mod):
    cases = [
        (datetime(2026, 10, 26, 10, 4, 59, tzinfo=timezone.utc),
         datetime(2026, 10, 26, 10, 0, 0, tzinfo=timezone.utc)),
        (datetime(2026, 10, 26, 10, 5, 0, tzinfo=timezone.utc),
         datetime(2026, 10, 26, 10, 5, 0, tzinfo=timezone.utc)),
        (datetime(2026, 10, 26, 10, 5, 1, tzinfo=timezone.utc),
         datetime(2026, 10, 26, 10, 5, 0, tzinfo=timezone.utc)),
    ]
    for now, want in cases:
        got = mod._cycle_floor(now)
        assert got == want, f"{now.isoformat()} -> {got.isoformat()}, want {want.isoformat()}"
    # Microsecond must be dropped too, or the Z string carries a sub-second it does
    # not print and the filter bound is subtly above the boundary row.
    odd = datetime(2026, 10, 26, 10, 5, 0, 500000, tzinfo=timezone.utc)
    assert mod._cycle_floor(odd).microsecond == 0, mod._cycle_floor(odd)
    # FAILS IF: the floor used round() or ceil -- 10:04:59 would read 10:05 and the
    # cycle would wait for a run that cannot exist yet.


@cell("T6 extra-expiry leg at the same ts -> front run_id")
def t6(mod):
    ft = FakeTime()
    _bind_clock(mod, ft)
    # Both legs share ONE ts (ingest sets snapshot_ts once) and differ only by
    # expiry_date, which is precisely the S81-FRONT-EXPIRY-RUNID case. The W2 leg is
    # listed FIRST so a mock that ignored `order` would hand back the wrong run_id.
    timeline = [
        (0.0, _row("NIFTY", CUR_TS, NEXT_EXPIRY, "CUR-N-W2")),
        (0.0, _row("NIFTY", CUR_TS, FRONT_EXPIRY, "CUR-N-W1")),
        (0.0, _row("SENSEX", CUR_TS, NEXT_EXPIRY, "CUR-S-W2")),
        (0.0, _row("SENSEX", CUR_TS, FRONT_EXPIRY, "CUR-S-W1")),
    ]
    sb = FakeSB(timeline, ft.monotonic)
    got = mod.fetch_cycle_run_ids(sb, NOW_IN_CYCLE, sleep=ft.sleep,
                                  clock=ft.monotonic)
    assert got == {"NIFTY": "CUR-N-W1", "SENSEX": "CUR-S-W1"}, got
    assert ft.sleeps == [], ft.sleeps
    # FAILS IF: order became "ts.desc" alone or "expiry_date.desc" -- the W2 leg's
    # run_id wins and every downstream compute runs on the back expiry.


@cell("T7 ts filter is the Z form, no '+' (URL-safe)")
def t7(mod):
    ft = FakeTime()
    _bind_clock(mod, ft)
    timeline = [
        (0.0, _row("NIFTY", CUR_TS, FRONT_EXPIRY, "CUR-N")),
        (0.0, _row("SENSEX", CUR_TS, FRONT_EXPIRY, "CUR-S")),
    ]
    sb = FakeSB(timeline, ft.monotonic)
    mod.fetch_cycle_run_ids(sb, NOW_IN_CYCLE, sleep=ft.sleep, clock=ft.monotonic)
    assert sb.calls, "no select call was captured"
    for c in sb.calls:
        tsf = c["filters"].get("ts")
        assert tsf is not None, f"call has no ts filter: {c['filters']}"
        assert TS_FILTER_RE.match(tsf), f"ts filter {tsf!r} does not match {TS_FILTER_RE.pattern}"
        assert "+" not in tsf, f"ts filter contains '+': {tsf!r}"
        assert tsf.endswith("Z"), f"ts filter does not end in Z: {tsf!r}"
        assert c["order"] == "ts.desc,expiry_date.asc", c["order"]
        assert c["limit"] == 1, c["limit"]
    # A '+00:00' offset survives requests' own encoding, but decodes to a SPACE in any
    # layer that builds the query string by hand -- and a mocked select cannot see
    # that. This cell is the only place the wire format is checked.
    # FAILS IF: floor_iso reverts to isoformat() -- '...+00:00' fails the regex.


@cell("T8 cycle floor is carried into the filter bound")
def t8(mod):
    ft = FakeTime()
    _bind_clock(mod, ft)
    sb = FakeSB([], ft.monotonic)
    mod.fetch_cycle_run_ids(sb, NOW_IN_CYCLE, sleep=ft.sleep, clock=ft.monotonic)
    bound = sb.calls[0]["filters"]["ts"][4:]
    assert _parse_ts(bound) == mod._cycle_floor(NOW_IN_CYCLE), (
        f"filter bound {bound} != floor {mod._cycle_floor(NOW_IN_CYCLE).isoformat()}"
    )
    # FAILS IF: the filter were built from now_utc instead of the floor -- the bound
    # would read 07:32:10 and the 07:30 run of its own cycle would be excluded.


@cell("T9 every _ledger_close reason is in the real VALID_EXIT_REASONS")
def t9(mod):
    """Cross-check the runner's reason strings against the ledger's own closed set.

    By AST, never by import: core/execution_log.py:84 calls load_dotenv() at module
    scope, so importing it -- by file path or otherwise -- reads an environment file.
    Reading its SOURCE gets the authoritative value with no side effect at all, and
    needs no stubbing of third-party modules, so it cannot be defeated by a future
    module-level statement in that file.

    The set is the real one: VALID_EXIT_REASONS at core/execution_log.py:91-103, which
    its own comment says mirrors the CHECK constraint in
    20260420_script_execution_log.sql. An invalid reason is NOT loud at runtime --
    exit_with_reason (:283-291) silently coerces it to CRASH and forces exit_code >= 1 --
    so a stalled ingest would file as a runner crash. This cell is the only thing in
    the suite that can see that, because FakeLedger accepts any string.
    """
    EXEC_LOG = REPO / "core" / "execution_log.py"
    assert EXEC_LOG.is_file(), f"not found: {EXEC_LOG}"
    el_tree = ast.parse(EXEC_LOG.read_bytes().decode("utf-8-sig"))

    valid: set | None = None
    for node in el_tree.body:
        tgts = ([node.target] if isinstance(node, ast.AnnAssign)
                else node.targets if isinstance(node, ast.Assign) else [])
        if not any(isinstance(t, ast.Name) and t.id == "VALID_EXIT_REASONS"
                   for t in tgts):
            continue
        v = node.value
        # frozenset({...}) / set({...}) -- unwrap the single-arg call to its literal.
        if (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                and v.func.id in ("frozenset", "set") and len(v.args) == 1):
            v = v.args[0]
        valid = set(ast.literal_eval(v))
    assert valid, f"could not lift VALID_EXIT_REASONS from {EXEC_LOG}"
    # If the lift silently produced the wrong object, the membership test below would
    # pass or fail for the wrong reason. Pin two members that must be there.
    assert {"SUCCESS", "SKIPPED_NO_INPUT"} <= valid, sorted(valid)

    # Reasons from the module UNDER TEST -- mod.__file__, so a mutant is read as
    # itself and not as the clean dry-run copy.
    mod_tree = ast.parse(Path(mod.__file__).read_bytes().decode("utf-8-sig"))
    reasons: list[str] = []
    for n in ast.walk(mod_tree):
        if not isinstance(n, ast.Call):
            continue
        fname = (n.func.id if isinstance(n.func, ast.Name)
                 else getattr(n.func, "attr", None))
        if fname != "_ledger_close":
            continue
        if (len(n.args) >= 3 and isinstance(n.args[2], ast.Constant)
                and isinstance(n.args[2].value, str)):
            reasons.append(n.args[2].value)

    # Vacuity guard: a broken walk finds nothing and the membership test below is then
    # trivially true. The patched file has five _ledger_close calls.
    assert len(reasons) >= 4, f"only {len(reasons)} reason literals found: {reasons}"
    assert "SKIPPED_NO_INPUT" in reasons, f"timeout reason not among {reasons}"

    bad = sorted({r for r in reasons if r not in valid})
    assert not bad, (f"reason(s) absent from VALID_EXIT_REASONS: {bad}; "
                     f"found={sorted(set(reasons))}; valid={sorted(valid)}")
    # FAILS IF: any _ledger_close reason is not in the ledger's closed set -- which is
    # exactly mutant R (STALE_INPUT), and exactly the defect that reached review by
    # hand last round rather than by a check.


CELLS = [t1, t2, t3, t4, t5, t6, t7, t8, t9]

# Each mutant names the substring it deletes or rewrites and the cells that MUST flip
# to failing. A cell with no mutant that kills it is documentation; T7 in particular
# was added on operator instruction, so mutant Z exists to prove it can fire at all.
T2_NAME = "T2 only previous-cycle run -> SKIPPED_NO_INPUT, pipeline not called"
T3_NAME = "T3 08:30 IST with yesterday 15:40 newest -> SKIPPED_NO_INPUT"
T7_NAME = "T7 ts filter is the Z form, no '+' (URL-safe)"
T9_NAME = "T9 every _ledger_close reason is in the real VALID_EXIT_REASONS"

MUTANTS = [
    {
        "id": "M",
        "what": "ts >= cycle_floor filter DELETED",
        "old": TS_FILTER_SNIPPET,
        "new": "",
        "must_fail": [T2_NAME, T3_NAME],
    },
    {
        "id": "R",
        "what": 'timeout reason reverted to STALE_INPUT (not in VALID_EXIT_REASONS)',
        "old": 'led, 1, "SKIPPED_NO_INPUT"',
        "new": 'led, 1, "STALE_INPUT"',
        # T2/T3 pin the reason STRING; T9 pins it against the ledger's closed set.
        # Both matter: the string cells would still pass if SKIPPED_NO_INPUT were
        # later removed from VALID_EXIT_REASONS, and T9 would still pass if the
        # runner swapped to any other valid-but-wrong reason.
        "must_fail": [T2_NAME, T3_NAME, T9_NAME],
    },
    {
        "id": "Z",
        "what": 'floor_iso reverted to isoformat() ("+00:00" on the wire)',
        "old": '_cycle_floor(now_utc).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")',
        "new": "_cycle_floor(now_utc).isoformat()",
        "must_fail": [T7_NAME, T2_NAME, T3_NAME],
    },
]


def _run_main(mod, sb, now_utc):
    """Call the module's real main() with its collaborators recorded."""
    calls = {"pipeline": []}

    mod.SupabaseClient = lambda *a, **k: sb
    mod.is_trading_day_today = lambda: True

    def fake_pipeline(run_ids):
        calls["pipeline"].append(dict(run_ids))
        return True

    mod.execute_pipeline = fake_pipeline

    led_box = {}
    real_open = mod._ledger_open

    def fake_open():
        led = FakeLedger(script_name="test")
        led_box["led"] = led
        return led

    mod._ledger_open = fake_open

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now_utc if tz else now_utc.replace(tzinfo=None)

    real_dt = mod.datetime
    mod.datetime = _FrozenDatetime
    try:
        calls["rc"] = mod.main()
    finally:
        mod.datetime = real_dt
        mod._ledger_open = real_open
    return led_box.get("led"), calls


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def main() -> int:
    if not RUNNER_UNDER_TEST.is_file():
        print(f"ABORT: runner not found: {RUNNER_UNDER_TEST}")
        print("Expected the S98-B runner at the repo root (S99 A3).")
        return 2

    # A must_fail name that matches no cell makes the mutant loop run ZERO cells and
    # report 0 survivors -- a green mutant that tested nothing. Renaming a cell is
    # exactly how that happens, so this is checked before anything runs.
    known = {c.cell_name for c in CELLS}
    bad = [(spec["id"], n) for spec in MUTANTS
           for n in spec["must_fail"] if n not in known]
    if bad:
        print("ABORT: must_fail names match no cell (a rename, probably):")
        for mid, n in bad:
            print(f"  mutant {mid}: {n!r}")
        print(f"  known cells: {sorted(known)}")
        return 2

    _install_stubs()

    print("=== S98-B runner cycle wait ===")
    print(f"under test : {RUNNER_UNDER_TEST}")
    src = RUNNER_UNDER_TEST.read_bytes().decode("utf-8-sig")
    print(f"bytes      : {len(src)}   marker S98_CYCLE_WAIT: {'S98_CYCLE_WAIT' in src}")
    print()

    mod = _load(RUNNER_UNDER_TEST, "s98b_patched")
    print(f"CYCLE_WAIT_S={mod.CYCLE_WAIT_S}  POLL_S={mod.POLL_S}  "
          f"SYMBOLS={mod.SYMBOLS}")
    print(f"expected max polls = {mod.CYCLE_WAIT_S // mod.POLL_S + 1}, "
          f"max sleeps = {mod.CYCLE_WAIT_S // mod.POLL_S}")
    print()

    print("--- patched module ---")
    for c in CELLS:
        ok = c(mod)
        print(f"  [{'PASS' if ok else 'FAIL'}] {c.cell_name}")
    patched_fails = [(n, m) for (n, ok, m) in RESULTS if not ok]

    # --- mutants -----------------------------------------------------------
    mutant_survivors: list[str] = []
    n_mutant_cells = 0
    for spec in MUTANTS:
        print()
        print(f"--- mutant {spec['id']}: {spec['what']} ---")
        n_snip = src.count(spec["old"])
        print(f"  snippet count = {n_snip} (must be 1)")
        if n_snip != 1:
            print("  ABORT: cannot build the mutant; the snippet is not unique.")
            return 2
        mutant_src = src.replace(spec["old"], spec["new"], 1)
        assert mutant_src != src

        RESULTS.clear()
        mut = _load(RUNNER_UNDER_TEST, f"s98b_mutant_{spec['id']}", source=mutant_src)
        for c in CELLS:
            if c.cell_name not in spec["must_fail"]:
                continue
            n_mutant_cells += 1
            ok = c(mut)
            verdict = "FAIL (correct)" if not ok else "PASS (WRONG)"
            print(f"  [{verdict}] {c.cell_name}")
        mutant_survivors += [f"{spec['id']}: {n}"
                             for (n, ok, _m) in RESULTS if ok]

    # --- verdict -----------------------------------------------------------
    print()
    print("--- verdict (computed) ---")
    print(f"  patched cells run      : {len(CELLS)}")
    print(f"  patched cells failing  : {len(patched_fails)}")
    print(f"  mutants run            : {len(MUTANTS)}")
    print(f"  mutant cells run       : {n_mutant_cells}")
    print(f"  mutant cells surviving : {len(mutant_survivors)} (must be 0)")

    if patched_fails:
        print()
        print("FAILING CELLS (patched):")
        for n, m in patched_fails:
            print(f"  - {n}")
            print(f"      {m}")
    if mutant_survivors:
        print()
        print("MUTANT SURVIVED -- these cells cannot detect a missing ts filter,")
        print("so they assert nothing about the patch's central claim:")
        for n in mutant_survivors:
            print(f"  - {n}")

    if patched_fails or mutant_survivors:
        return 1

    print()
    print("RUNNER CYCLE WAIT ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
