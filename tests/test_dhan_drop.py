#!/usr/bin/env python3
"""E1/E3 (engine lane e1-e3-e10) -- dhan_drop.py (the SSH-drop helper for the fresh Dhan token and
login status) and its wiring into refresh_dhan_token.py's success/failure branches -- offline, with
controls and mutants. No network, no real .env, no real SSH, no real Dhan login: every HTTP call, SSH
call and clock read is stubbed; refresh_dhan_token.py is loaded from source with its BASE_DIR pointed at
a throwaway temp directory (never the real repo .env or runtime/), and its `dhan_drop` collaborator is
replaced with a recording fake so this file never actually calls dhan_drop.py's own SSH path.

Rule 0 -- what each cell would catch:
  T1 the success path sends more than one ssh call, the wrong keys, a bad minted_at, or leaks the
     token into argv/stdout/stderr/log
  T2 a helper failure (ssh rc!=0, timeout, exception, unconfigured) changes the script's exit code or
     raises into the login, or the log carries more than name/bytes/reason
  T3 an empty token is still sent
  T4 an "other" first-attempt or retry failure, a Timeout/ConnectionError, or a require_env failure
     writes a dhan file, fails to write dhan_login_status=failed, or swallows the original exception
  T5 a rate-limited attempt (first or retry) still sends a drop or a status
  T7 the Invalid-TOTP-then-success path sends more than one drop, or the drop doesn't carry the
     second (post-retry) token
  T8 the content-safety property (<=8 lines, <=4096 bytes, printable ASCII, no "secret" key, no
     empty value, minted_at ends +05:30) is violated by anything the helper actually sends
Mutants M1-M6 each remove one guarantee; a mutant whose named cells all pass means those cells assert
nothing (Rule 0).
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile
import time as _real_time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DROP_PATH = REPO / "dhan_drop.py"
RDT_PATH = REPO / "refresh_dhan_token.py"

IST = timezone(timedelta(hours=5, minutes=30))
FIXED_NOW = datetime(2026, 11, 20, 10, 0, 0, tzinfo=IST)

SECRET_TOKEN = "TOK_SUPER_SECRET_ABC123"
RETRY_TOKEN = "TOK_SECOND_WINDOW_XYZ789"


# ---------------------------------------------------------------------------
# dhan_drop.py loader + fakes
# ---------------------------------------------------------------------------

class FakeCompleted:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def make_recording_run(returncode=0):
    calls = []

    def run(argv, input=None, timeout=None, capture_output=None):
        calls.append({"argv": argv, "input": input, "timeout": timeout})
        return FakeCompleted(returncode=returncode)

    run.calls = calls
    return run


def make_raising_run(exc):
    def run(*a, **k):
        raise exc
    return run


def load_dhan_drop(src_text, run_fn):
    mod = types.ModuleType("dhan_drop_under_test")
    mod.__file__ = str(DROP_PATH)
    exec(compile(src_text, str(DROP_PATH), "exec"), mod.__dict__)
    mod.subprocess = types.SimpleNamespace(run=run_fn)
    # Built from the EXEC'D MODULE'S OWN `IST`, not the test file's IST constant, so a
    # mutation to dhan_drop.py's own timezone offset (M5) actually changes what this
    # returns -- a fixed lambda over FIXED_NOW would bypass the mutation entirely and
    # make M5 unkillable regardless of what the mutant does (Rule 0).
    mod._now_ist = lambda: datetime(2026, 11, 20, 10, 0, 0, tzinfo=mod.IST)
    return mod


DROP_ENV = {
    "MERIDIAN_RETAIL_DROP_KEY": "/tmp/e1e3e10_fake_key",
    "MERIDIAN_RETAIL_DROP_KNOWN_HOSTS": "/tmp/e1e3e10_fake_known_hosts",
    "MERIDIAN_RETAIL_DROP_HOST": "203.0.113.5",
}


@contextlib.contextmanager
def drop_env_configured():
    old = {k: os.environ.get(k) for k in DROP_ENV}
    os.environ.update(DROP_ENV)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextlib.contextmanager
def drop_env_unconfigured():
    old = {k: os.environ.pop(k, None) for k in DROP_ENV}
    try:
        yield
    finally:
        for k, v in old.items():
            if v is not None:
                os.environ[k] = v


def capture_stdout(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*a, **k)
    return result, buf.getvalue()


# ---------------------------------------------------------------------------
# refresh_dhan_token.py loader + fakes
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


def resp(status_code=200, text="", json_data=None):
    return FakeResponse(status_code=status_code, json_data=json_data, text=text)


def ok_resp(token=SECRET_TOKEN, expiry="2026-11-21 06:00:00"):
    return resp(200, "", {"accessToken": token, "expiryTime": expiry})


def rate_limited_resp():
    return resp(429, "Token can be generated once every 2 minutes.", {})


def invalid_totp_resp():
    return resp(400, "Invalid TOTP supplied", {})


def other_fail_resp(text="Internal Server Error - unrelated outage"):
    return resp(500, text, {})


def make_post_sequence(items):
    calls = []
    it = iter(items)

    def post(url, params=None, timeout=None):
        calls.append(params)
        item = next(it)
        if isinstance(item, BaseException):
            raise item
        return item

    post.calls = calls
    return post


REQUIRED_ENV = {
    "DHAN_CLIENT_ID": "CLIENT9",
    "DHAN_PIN": "1234",
    "DHAN_TOTP_SEED": "JBSWY3DPEHPK3PXP",
    "SUPABASE_URL": "http://example.invalid",
    "SUPABASE_SERVICE_ROLE_KEY": "svc-key",
}


@contextlib.contextmanager
def rdt_env(missing=()):
    keys = set(REQUIRED_ENV)
    old = {k: os.environ.get(k) for k in keys}
    for k, v in REQUIRED_ENV.items():
        if k in missing:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def load_rdt(src_text, post_fn, drop_ok=True):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_rdt_"))
    (tmp_root / ".env").write_text("DHAN_API_TOKEN=OLD_TOKEN\nOTHER_KEY=unchanged\n", encoding="utf-8")
    fake_file = tmp_root / "refresh_dhan_token.py"
    mod = types.ModuleType("refresh_dhan_token_under_test")
    mod.__file__ = str(fake_file)
    exec(compile(src_text, str(fake_file), "exec"), mod.__dict__)
    mod.load_dotenv = lambda dotenv_path=None: None
    import requests as _real_requests
    fake_requests = types.SimpleNamespace(
        post=post_fn,
        patch=lambda *a, **k: FakeResponse(200),
        Timeout=_real_requests.exceptions.Timeout,
        ConnectionError=_real_requests.exceptions.ConnectionError,
    )
    mod.requests = fake_requests
    mod._now_ist = lambda: FIXED_NOW
    drop_calls = []
    status_calls = []
    fake_drop = types.SimpleNamespace()

    def _send_drop(token, expiry, client_id):
        drop_calls.append((token, expiry, client_id))
        return drop_ok

    def _send_status(ok):
        status_calls.append(ok)
        return True

    fake_drop.send_dhan_drop = _send_drop
    fake_drop.send_dhan_login_status = _send_status
    mod.dhan_drop = fake_drop
    return mod, tmp_root, drop_calls, status_calls


def run_main(mod):
    buf = io.StringIO()
    exc = None
    rc = None
    with contextlib.redirect_stdout(buf):
        try:
            rc = mod.main()
        except BaseException as e:
            exc = e
    return rc, exc, buf.getvalue()


@contextlib.contextmanager
def patched_sleep():
    calls = []
    old = _real_time.sleep
    _real_time.sleep = lambda s: calls.append(s)
    try:
        yield calls
    finally:
        _real_time.sleep = old


# ---------------------------------------------------------------------------
# T1-T3, T8: dhan_drop.py directly
# ---------------------------------------------------------------------------

def t1_success_path(src):
    run = make_recording_run(0)
    mod = load_dhan_drop(src, run)
    with drop_env_configured():
        ok, out = capture_stdout(mod.send_dhan_drop, SECRET_TOKEN, "2026-11-21 06:00:00", "CLIENT9")
    checks = [("send_dhan_drop returned True", ok is True),
              ("exactly one ssh call", len(run.calls) == 1)]
    if len(run.calls) == 1:
        call = run.calls[0]
        argv = [str(a) for a in call["argv"]]
        checks.append(("argv ends with put dhan", argv[-2:] == ["put", "dhan"]))
        checks.append(("-F /dev/null present", "-F" in argv and argv[argv.index("-F") + 1] == "/dev/null"))
        content = call["input"].decode("utf-8")
        lines = content.rstrip("\n").split("\n")
        checks.append(("exactly 5 keys", len(lines) == 5))
        keys = [l.split("=", 1)[0] for l in lines]
        checks.append(("keys are broker/access_token/expires/minted_at/client_id",
                        keys == ["broker", "access_token", "expires", "minted_at", "client_id"]))
        minted_line = next((l for l in lines if l.startswith("minted_at=")), "")
        checks.append(("minted_at matches +05:30 pattern",
                        bool(re.match(r"^minted_at=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+05:30$", minted_line))))
        checks.append(("token present in stdin content", SECRET_TOKEN in content))
        checks.append(("token absent from argv", SECRET_TOKEN not in " ".join(argv)))
    checks.append(("token absent from stdout/log", SECRET_TOKEN not in out))
    return checks


def t2_helper_failures(src):
    out_checks = []
    cases = [
        ("ssh rc 255", make_recording_run(255), None),
        ("ssh timeout", make_raising_run(TimeoutError("timed out")), None),
        ("ssh exception", make_raising_run(OSError("no route to host")), None),
        ("unconfigured", make_recording_run(0), "unconfigured"),
    ]
    for label, run_fn, mode in cases:
        mod = load_dhan_drop(src, run_fn)
        ctx = drop_env_unconfigured() if mode == "unconfigured" else drop_env_configured()
        with ctx:
            raised = False
            ok = None
            try:
                ok, out = capture_stdout(mod.send_dhan_drop, SECRET_TOKEN, "2026-11-21 06:00:00", "CLIENT9")
            except BaseException:
                raised = True
                out = ""
        out_checks.append((f"{label}: no exception escapes", not raised))
        out_checks.append((f"{label}: returns False", ok is False))
        out_checks.append((f"{label}: log has no secret value",
                            SECRET_TOKEN not in out))
        out_checks.append((f"{label}: log line is name/bytes/reason only",
                            bool(re.match(r"^DHAN DROP name=\S+ bytes=\d+ refused reason=\S+\s*$",
                                          out.strip().splitlines()[-1] if out.strip() else ""))))
    return out_checks


@contextlib.contextmanager
def dhan_drop_unimportable():
    """Forces `import dhan_drop` to raise ImportError at exec time, simulating a
    missing or broken helper module, without touching the real sys.modules entry
    for any other test in this process (restored in finally)."""
    sentinel = object()
    old = sys.modules.get("dhan_drop", sentinel)
    sys.modules["dhan_drop"] = None
    try:
        yield
    finally:
        if old is sentinel:
            sys.modules.pop("dhan_drop", None)
        else:
            sys.modules["dhan_drop"] = old


def t2b_dhan_drop_unimportable(src):
    """T2: a broken/unimportable dhan_drop must never stop the login -- the
    script's own `except Exception: dhan_drop = None` fallback, exercised for
    real (not faked out), must still let main() reach exit 0."""
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_rdt_nodrop_"))
    (tmp_root / ".env").write_text("DHAN_API_TOKEN=OLD_TOKEN\n", encoding="utf-8")
    fake_file = tmp_root / "refresh_dhan_token.py"
    mod = types.ModuleType("refresh_dhan_token_under_test_nodrop")
    mod.__file__ = str(fake_file)
    with dhan_drop_unimportable():
        exec(compile(src, str(fake_file), "exec"), mod.__dict__)
    mod.load_dotenv = lambda dotenv_path=None: None
    import requests as _real_requests
    mod.requests = types.SimpleNamespace(
        post=make_post_sequence([ok_resp()]),
        patch=lambda *a, **k: FakeResponse(200),
        Timeout=_real_requests.exceptions.Timeout,
        ConnectionError=_real_requests.exceptions.ConnectionError,
    )
    mod._now_ist = lambda: FIXED_NOW
    with rdt_env():
        rc, exc, out = run_main(mod)
    return [
        ("dhan_drop unimportable: module-level dhan_drop is None", getattr(mod, "dhan_drop", "missing") is None),
        ("dhan_drop unimportable: login still reaches exit 0", rc == 0),
        ("dhan_drop unimportable: no exception escapes", exc is None),
    ]


def t2d_internal_exception(src):
    """T2d: targets the outer try/except in send_dhan_drop AND send_dhan_login_status
    specifically, by forcing an exception from INSIDE the function body (not from
    _ssh_put, which has its own inner catch). Without this cell, narrowing either
    outer `except Exception` is invisible to every other T1/T3/T8/T2 cell, because
    none of them ever raises from inside that body (Rule 0).

    Each half also carries a CONTROL run (real clock, no injected exception) proving
    the happy path still sends exactly one ssh call -- so a FAIL on the exception half
    is known to come from the injected exception, not from some other misconfiguration
    (env vars, argv shape, ...) that would make the function fail regardless."""
    def raise_clock():
        raise ValueError("clock broken")

    checks = []

    # control: send_dhan_drop with a real clock still succeeds
    run_ctrl = make_recording_run(0)
    mod_ctrl = load_dhan_drop(src, run_ctrl)
    with drop_env_configured():
        ok_ctrl, _ = capture_stdout(mod_ctrl.send_dhan_drop, SECRET_TOKEN, "2026-11-21 06:00:00", "CLIENT9")
    checks.append(("send_dhan_drop: control (real clock) returns True", ok_ctrl is True))
    checks.append(("send_dhan_drop: control (real clock) makes exactly one ssh call", len(run_ctrl.calls) == 1))

    run = make_recording_run(0)
    mod = load_dhan_drop(src, run)
    mod._now_ist = raise_clock
    with drop_env_configured():
        raised = False
        ok = None
        try:
            ok, out = capture_stdout(mod.send_dhan_drop, SECRET_TOKEN, "2026-11-21 06:00:00", "CLIENT9")
        except BaseException:
            raised = True
    checks.append(("send_dhan_drop: internal exception does not escape", not raised))
    checks.append(("send_dhan_drop: internal exception returns False", ok is False))
    checks.append(("send_dhan_drop: internal exception makes no ssh call", len(run.calls) == 0))

    # control: send_dhan_login_status with a real clock still succeeds
    run2_ctrl = make_recording_run(0)
    mod2_ctrl = load_dhan_drop(src, run2_ctrl)
    with drop_env_configured():
        ok2_ctrl, _ = capture_stdout(mod2_ctrl.send_dhan_login_status, True)
    checks.append(("send_dhan_login_status: control (real clock) returns True", ok2_ctrl is True))
    checks.append(("send_dhan_login_status: control (real clock) makes exactly one ssh call",
                    len(run2_ctrl.calls) == 1))

    run2 = make_recording_run(0)
    mod2 = load_dhan_drop(src, run2)
    mod2._now_ist = raise_clock
    with drop_env_configured():
        raised2 = False
        ok2 = None
        try:
            ok2, out2 = capture_stdout(mod2.send_dhan_login_status, True)
        except BaseException:
            raised2 = True
    checks.append(("send_dhan_login_status: internal exception does not escape", not raised2))
    checks.append(("send_dhan_login_status: internal exception returns False", ok2 is False))
    checks.append(("send_dhan_login_status: internal exception makes no ssh call", len(run2.calls) == 0))

    return checks


def t3_empty_token(src):
    run = make_recording_run(0)
    mod = load_dhan_drop(src, run)
    with drop_env_configured():
        ok, out = capture_stdout(mod.send_dhan_drop, "", "2026-11-21 06:00:00", "CLIENT9")
    return [
        ("empty token returns False", ok is False),
        ("empty token makes no ssh call", len(run.calls) == 0),
    ]


def t3b_value_validation(src):
    """T3b: empty/whitespace-only client_id and an embedded newline in any single
    value (token, client_id, or expires) must refuse with no ssh call -- an
    embedded "\\n" would otherwise smuggle an extra key=value line onto the wire
    undetected by the per-line checks, which only run AFTER the (already-corrupted)
    content is joined. Each refusal cell also checks the captured output carries
    neither the injected payload nor the token, matching T1's "no leak" discipline."""
    checks = []
    injected_token = "TOK123\nINJECTED=evil"
    injected_client = "CLIENT9\nINJECTED=evil"
    injected_expires = "2026-11-21\nINJECTED=evil"

    def refusal_cell(label, token, expiry, client_id):
        run = make_recording_run(0)
        mod = load_dhan_drop(src, run)
        with drop_env_configured():
            ok, out = capture_stdout(mod.send_dhan_drop, token, expiry, client_id)
        checks.append((f"{label}: returns False", ok is False))
        checks.append((f"{label}: makes no ssh call", len(run.calls) == 0))
        checks.append((f"{label}: output carries no token", SECRET_TOKEN not in out and "TOK123" not in out))
        checks.append((f"{label}: output carries no injected payload", "INJECTED" not in out))

    refusal_cell("empty client_id", SECRET_TOKEN, "2026-11-21 06:00:00", "")
    refusal_cell("whitespace-only client_id", SECRET_TOKEN, "2026-11-21 06:00:00", "  ")
    refusal_cell("embedded newline in token", injected_token, "2026-11-21 06:00:00", "CLIENT9")
    refusal_cell("embedded newline in client_id", SECRET_TOKEN, "2026-11-21 06:00:00", injected_client)
    refusal_cell("embedded newline in expires", SECRET_TOKEN, injected_expires, "CLIENT9")

    # control: a plain, valid call still succeeds with exactly one ssh call -- proves
    # the refusal cells above fail for the injected content, not for some unrelated
    # reason (Rule 0; same discipline as T2d's control).
    run_ctrl = make_recording_run(0)
    mod_ctrl = load_dhan_drop(src, run_ctrl)
    with drop_env_configured():
        ok_ctrl, _ = capture_stdout(mod_ctrl.send_dhan_drop, SECRET_TOKEN, "2026-11-21 06:00:00", "CLIENT9")
    checks.append(("control: valid call returns True", ok_ctrl is True))
    checks.append(("control: valid call makes exactly one ssh call", len(run_ctrl.calls) == 1))

    return checks


def t8_content_property(src):
    run = make_recording_run(0)
    mod = load_dhan_drop(src, run)
    checks = []
    cases = [
        (SECRET_TOKEN, "2026-11-21 06:00:00", "CLIENT9"),
        (SECRET_TOKEN, "", "CLIENT9"),             # empty expiry -> unknown
        (SECRET_TOKEN, "2026-11-21 06:00:00", "C"),
    ]
    for token, expiry, client_id in cases:
        run.calls.clear()
        with drop_env_configured():
            mod.send_dhan_drop(token, expiry, client_id)
        if not run.calls:
            checks.append((f"content property ({expiry!r}): a call was made", False))
            continue
        content = run.calls[-1]["input"].decode("utf-8")
        lines = content.rstrip("\n").split("\n")
        checks.append((f"content property ({expiry!r}): <=8 lines", len(lines) <= 8))
        checks.append((f"content property ({expiry!r}): <=4096 bytes", len(content.encode("utf-8")) <= 4096))
        checks.append((f"content property ({expiry!r}): printable ASCII + LF only",
                        all(0x20 <= ord(c) <= 0x7E for c in content if c != "\n")))
        checks.append((f"content property ({expiry!r}): no CR", "\r" not in content))
        checks.append((f"content property ({expiry!r}): no blank line", "" not in lines))
        checks.append((f"content property ({expiry!r}): no empty value",
                        all(l.split("=", 1)[1] != "" for l in lines)))
        checks.append((f"content property ({expiry!r}): no key contains secret",
                        all("secret" not in l.split("=", 1)[0].lower() for l in lines)))
        expires_line = next((l for l in lines if l.startswith("expires=")), "")
        if expiry == "":
            checks.append(("empty expiryTime becomes unknown", expires_line == "expires=unknown"))
    return checks


# ---------------------------------------------------------------------------
# T4, T5, T7: refresh_dhan_token.py integration (dhan_drop faked)
# ---------------------------------------------------------------------------

def t4_failure_branches(src):
    checks = []

    # other first-attempt failure (:184-186)
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, make_post_sequence([other_fail_resp()]))
        rc, exc, out = run_main(mod)
    checks.append(("other first-attempt failure: original exception raised", isinstance(exc, RuntimeError)))
    checks.append(("other first-attempt failure: exit code unaffected (no rc)", rc is None))
    checks.append(("other first-attempt failure: no dhan drop", drop_calls == []))
    checks.append(("other first-attempt failure: exactly one failed status", status_calls == [False]))

    # other retry failure (:174-175), via Invalid TOTP then a different error
    with patched_sleep(), rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(
            src, make_post_sequence([invalid_totp_resp(), other_fail_resp("broker outage")]))
        rc, exc, out = run_main(mod)
    checks.append(("other retry failure: original exception raised", isinstance(exc, RuntimeError)))
    checks.append(("other retry failure: no dhan drop", drop_calls == []))
    checks.append(("other retry failure: exactly one failed status", status_calls == [False]))

    # requests.Timeout on first attempt (non-RuntimeError)
    import requests as _real_requests
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(
            src, make_post_sequence([_real_requests.exceptions.Timeout("conn timed out")]))
        rc, exc, out = run_main(mod)
    checks.append(("requests.Timeout: original exception raised",
                    isinstance(exc, _real_requests.exceptions.Timeout)))
    checks.append(("requests.Timeout: no dhan drop", drop_calls == []))
    checks.append(("requests.Timeout: exactly one failed status", status_calls == [False]))

    # ConnectionError on first attempt
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(
            src, make_post_sequence([_real_requests.exceptions.ConnectionError("refused")]))
        rc, exc, out = run_main(mod)
    checks.append(("requests.ConnectionError: original exception raised",
                    isinstance(exc, _real_requests.exceptions.ConnectionError)))
    checks.append(("requests.ConnectionError: no dhan drop", drop_calls == []))
    checks.append(("requests.ConnectionError: exactly one failed status", status_calls == [False]))

    # require_env failure (missing DHAN_PIN)
    with rdt_env(missing={"DHAN_PIN"}):
        mod, tmp, drop_calls, status_calls = load_rdt(src, make_post_sequence([]))
        rc, exc, out = run_main(mod)
    checks.append(("require_env failure: original RuntimeError raised", isinstance(exc, RuntimeError)))
    checks.append(("require_env failure: no dhan drop", drop_calls == []))
    checks.append(("require_env failure: exactly one failed status", status_calls == [False]))

    # 200 response with no accessToken: request_dhan_token's own
    # "if not access_token: raise RuntimeError(...)" check, via the normal
    # RuntimeError else-branch -- confirmed to already exist by reading the source;
    # this cell is the measurement, not just the reading.
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(
            src, make_post_sequence([resp(200, "", {"expiryTime": "2026-11-21 06:00:00"})]))
        rc, exc, out = run_main(mod)
    checks.append(("missing accessToken: original RuntimeError raised", isinstance(exc, RuntimeError)))
    checks.append(("missing accessToken: message names accessToken",
                    exc is not None and "accessToken" in str(exc)))
    checks.append(("missing accessToken: no dhan drop", drop_calls == []))
    checks.append(("missing accessToken: exactly one failed status", status_calls == [False]))

    # HTTPError raised directly by the transport (non-RuntimeError) -- same broad
    # except Exception path as Timeout/ConnectionError above, different subtype.
    http_error = _real_requests.exceptions.HTTPError("502 Bad Gateway")
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, make_post_sequence([http_error]))
        rc, exc, out = run_main(mod)
    checks.append(("requests.HTTPError: original exception raised", isinstance(exc, _real_requests.exceptions.HTTPError)))
    checks.append(("requests.HTTPError: no dhan drop", drop_calls == []))
    checks.append(("requests.HTTPError: exactly one failed status", status_calls == [False]))

    # resp.json() raises ValueError (malformed JSON body) -- non-RuntimeError, must
    # not be swallowed by the inner "except RuntimeError as e:" and must reach the
    # broad outer handler.
    class _RaisingJSONResponse(FakeResponse):
        def json(self):
            raise ValueError("Expecting value: line 1 column 1 (char 0)")

    def _json_decode_error_post(url, params=None, timeout=None):
        return _RaisingJSONResponse(200, {}, "")

    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, _json_decode_error_post)
        rc, exc, out = run_main(mod)
    checks.append(("JSON decode ValueError: original exception raised", isinstance(exc, ValueError)))
    checks.append(("JSON decode ValueError: not mistaken for RuntimeError", not isinstance(exc, RuntimeError)))
    checks.append(("JSON decode ValueError: no dhan drop", drop_calls == []))
    checks.append(("JSON decode ValueError: exactly one failed status", status_calls == [False]))

    return checks


def t5_rate_limited(src):
    checks = []

    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, make_post_sequence([rate_limited_resp()]))
        rc, exc, out = run_main(mod)
    checks.append(("rate-limited first attempt: exit 2", rc == 2 and exc is None))
    checks.append(("rate-limited first attempt: no drop", drop_calls == []))
    checks.append(("rate-limited first attempt: no status", status_calls == []))

    with patched_sleep(), rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(
            src, make_post_sequence([invalid_totp_resp(), rate_limited_resp()]))
        rc, exc, out = run_main(mod)
    checks.append(("rate-limited on retry: exit 2", rc == 2 and exc is None))
    checks.append(("rate-limited on retry: no drop", drop_calls == []))
    checks.append(("rate-limited on retry: no status", status_calls == []))

    return checks


def t7_totp_retry_success(src):
    with patched_sleep() as sleeps, rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(
            src, make_post_sequence([invalid_totp_resp(), ok_resp(token=RETRY_TOKEN)]))
        rc, exc, out = run_main(mod)
    post_calls = mod.requests.post.calls if hasattr(mod.requests.post, "calls") else None
    return [
        ("totp retry: no exception", exc is None),
        ("totp retry: exit 0", rc == 0),
        ("totp retry: exactly two requests", True),  # structural: post consumed exactly 2 items, else StopIteration
        ("totp retry: 30s sleep patched (no real sleep)", sleeps == [30]),
        ("totp retry: exactly one dhan drop", len(drop_calls) == 1),
        ("totp retry: drop carries the second (retry) token",
         len(drop_calls) == 1 and drop_calls[0][0] == RETRY_TOKEN),
        ("totp retry: exactly one ok status", status_calls == [True]),
    ]


# ---------------------------------------------------------------------------
# Mutants
# ---------------------------------------------------------------------------

def read_src(path):
    return path.read_text(encoding="utf-8")


def report(label, checks):
    ok = True
    for name, passed in checks:
        print(f"  {'PASS' if passed else 'FAIL'} {label}: {name}")
        ok &= bool(passed)
    return ok


def main():
    drop_src = read_src(DROP_PATH)
    rdt_src = read_src(RDT_PATH)
    ok = True

    ok &= report("T1", t1_success_path(drop_src))
    ok &= report("T2", t2_helper_failures(drop_src))
    ok &= report("T2b", t2b_dhan_drop_unimportable(rdt_src))
    ok &= report("T2d", t2d_internal_exception(drop_src))
    ok &= report("T3", t3_empty_token(drop_src))
    ok &= report("T3b", t3b_value_validation(drop_src))
    ok &= report("T8", t8_content_property(drop_src))
    ok &= report("T4", t4_failure_branches(rdt_src))
    ok &= report("T5", t5_rate_limited(rdt_src))
    ok &= report("T7", t7_totp_retry_success(rdt_src))

    # ---- mutants -----------------------------------------------------
    # Every mutant is built by mutate(): asserts the anchor occurs EXACTLY ONCE in the
    # real source before replacing (an anchor shifted by a later indentation change must
    # be a loud FAIL here, never a silent no-op that `msrc == original` catches late), and
    # asserts the mutated text actually differs from the original.
    mutants = []
    anchor_failures = []

    def mutate(label, src, old, new, kind):
        n = src.count(old)
        if n != 1:
            anchor_failures.append(label)
            print(f"  FAIL mutant anchor: {label} anchor found {n} times (need exactly 1)")
            return
        msrc = src.replace(old, new, 1)
        if msrc == src:
            anchor_failures.append(label)
            print(f"  FAIL mutant anchor: {label} mutation produced no textual change")
            return
        mutants.append((label, msrc, kind))

    # M1: helper exception escapes into the login (remove the outer try/except in send_dhan_drop)
    mutate(
        "M1 helper exception escapes into the login", drop_src,
        "    except Exception:\n"
        "        try:\n"
        "            _log(\"dhan\", b\"\", False, \"exception\")\n"
        "        except Exception:\n"
        "            pass\n"
        "        return False\n",
        "    except ZeroDivisionError:\n"
        "        return False\n",
        "drop",
    )

    # M2: token placed in argv instead of stdin
    mutate(
        "M2 token placed in argv", drop_src,
        '"put", name,\n            ],', '"put", name, content,\n            ],',
        "drop",
    )

    # M3: drop written on rate-limit (first attempt). This branch sits inside the outer
    # try added for the broad non-RuntimeError except, so it is at 16 spaces, not 12 --
    # mutate()'s count==1 assertion is what would catch a future indentation drift here.
    mutate(
        "M3 drop written on rate-limit", rdt_src,
        '                write_token_status(False, "", f"rate_limited: {error_msg}")\n'
        '                return 2',
        '                write_token_status(False, "", f"rate_limited: {error_msg}")\n'
        '                _send_dhan_drop(access_token if "access_token" in dir() else "LEAK", "", client_id)\n'
        '                return 2',
        "rdt",
    )

    # M4: ok written when the dhan drop failed (unconditional status write)
    mutate(
        "M4 ok written when the dhan drop failed", rdt_src,
        '    if _send_dhan_drop(access_token, expiry_time, client_id):\n'
        '        _send_dhan_login_status(True)\n',
        '    _send_dhan_drop(access_token, expiry_time, client_id)\n'
        '    _send_dhan_login_status(True)\n',
        "rdt_success_drop_fails",
    )

    # M5: time offset not +05:30 (dhan_drop IST mis-set)
    mutate(
        "M5 time offset not +05:30", drop_src,
        "IST = timezone(timedelta(hours=5, minutes=30))",
        "IST = timezone(timedelta(hours=5, minutes=0))",
        "drop",
    )

    # M6: -F /dev/null removed from the ssh argv
    mutate(
        "M6 -F /dev/null removed", drop_src,
        '"-F", "/dev/null",\n                "-i"', '"-i"',
        "drop",
    )

    # M7: the empty-client_id check removed
    mutate(
        "M7 empty-client_id check removed", drop_src,
        '        client = (client_id or "").strip()\n'
        '        if not client:\n'
        '            _log("dhan", b"", False, "empty_client_id")\n'
        '            return False\n',
        '        client = (client_id or "").strip()\n',
        "drop",
    )

    # M8: the embedded-newline check removed
    mutate(
        "M8 embedded-newline check removed", drop_src,
        '        # Reject an embedded newline in any single value BEFORE joining -- a value\n'
        '        # carrying its own "\\n" would otherwise smuggle an extra key=value line onto\n'
        '        # the wire that never passed the per-line checks below (secret-key, length).\n'
        '        if any("\\n" in v for v in values.values()):\n'
        '            _log("dhan", b"", False, "embedded_newline")\n'
        '            return False\n',
        '',
        "drop",
    )

    if anchor_failures:
        ok = False

    killed = 0
    not_applied = 0
    surviving = []
    for label, msrc, kind in mutants:
        if msrc == drop_src or msrc == rdt_src:
            not_applied += 1
            print(f"  MUTANT NOT APPLIED: {label}")
            continue
        try:
            if kind == "drop":
                cells = (t1_success_path(msrc) + t3_empty_token(msrc) + t3b_value_validation(msrc)
                         + t8_content_property(msrc) + t2d_internal_exception(msrc))
            elif kind == "rdt":
                cells = t5_rate_limited(msrc)
            elif kind == "rdt_success_drop_fails":
                run = make_recording_run(0)
                with rdt_env():
                    mod, tmp, drop_calls, status_calls = load_rdt(msrc, make_post_sequence([ok_resp()]), drop_ok=False)
                    rc, exc, out = run_main(mod)
                cells = [("ok status not written when drop failed", status_calls == [])]
            else:
                cells = []
        except BaseException as e:
            cells = [("mutant raised instead of behaving differently", False)]
        caught = any(not passed for _, passed in cells)
        if caught:
            killed += 1
            print(f"  CAUGHT: {label}")
        else:
            surviving.append(label)
            print(f"  SURVIVED (BAD): {label}")

    print(f"cells: drop_src/rdt_src loaded; mutants {len(mutants)}, not applied {not_applied}, "
          f"killed {killed}, surviving {len(surviving)} (must be 0)")
    ok &= (len(surviving) == 0) and (not_applied == 0)

    print(f"DHAN DROP {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
