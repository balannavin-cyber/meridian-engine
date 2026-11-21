#!/usr/bin/env python3
"""E10 (engine lane e1-e3-e10) -- refresh_dhan_token.py's 300s login-attempt spacing guard
(D2) -- offline, with controls and mutants. No network, no real .env, no real Dhan login:
the script is loaded from source with its BASE_DIR pointed at a throwaway temp directory
(never the real repo .env or runtime/), requests.post is a recording fake, and the clock the
guard reads is stubbed via _now_ist.

Rule 0 -- what each cell would catch:
  T6  a stamp under 300s old does not refuse, or refuses without saying how long is left;
      a stamp at/over 300s old still refuses; a missing stamp refuses; the stamp is not
      written before the first request or before the 30s TOTP retry; a crash mid-request
      loses the stamp; an unwritable logs/ blocks the request instead of failing open; a
      naive (tz-less) stamp crashes the run instead of being treated as no-stamp
  T9  the guard or the helper writes anything outside logs/dhan_login_attempt.stamp (the
      pre-existing .env rewrite and runtime/token_status.json write are expected; nothing
      ELSE should appear)
  T10 the guard silently swallows the pre-existing 90s idempotency skip instead of running
      before it and simply not blocking when no stamp exists
Mutants M1-M2 each remove one guarantee; a mutant whose named cells all pass means those
cells assert nothing.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import time as _real_time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

RDT_PATH = REPO / "refresh_dhan_token.py"

IST = timezone(timedelta(hours=5, minutes=30))
FIXED_NOW = datetime(2026, 11, 20, 10, 0, 0, tzinfo=IST)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


def ok_resp(token="TOK_GUARD_123", expiry="2026-11-21 06:00:00"):
    return FakeResponse(200, {"accessToken": token, "expiryTime": expiry})


def invalid_totp_resp():
    return FakeResponse(400, {}, "Invalid TOTP supplied")


def make_recording_post(responses):
    """responses: a single FakeResponse (reused every call) or a list consumed in order."""
    calls = []
    if isinstance(responses, list):
        it = iter(responses)

        def post(url, params=None, timeout=None):
            calls.append(params)
            return next(it)
    else:
        def post(url, params=None, timeout=None):
            calls.append(params)
            return responses

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
def rdt_env():
    import os
    old = {k: os.environ.get(k) for k in REQUIRED_ENV}
    os.environ.update(REQUIRED_ENV)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def load_rdt(src_text, post_fn, base_dir, now=FIXED_NOW):
    tmp_root = base_dir
    env_path = tmp_root / ".env"
    if not env_path.exists():
        env_path.write_text("DHAN_API_TOKEN=OLD_TOKEN\nKEEP=1\n", encoding="utf-8")
    fake_file = tmp_root / "refresh_dhan_token.py"
    mod = types.ModuleType("refresh_dhan_token_under_test_guard")
    mod.__file__ = str(fake_file)
    exec(compile(src_text, str(fake_file), "exec"), mod.__dict__)
    mod.load_dotenv = lambda dotenv_path=None: None
    import requests as _real_requests
    mod.requests = types.SimpleNamespace(
        post=post_fn,
        patch=lambda *a, **k: FakeResponse(200),
        Timeout=_real_requests.exceptions.Timeout,
        ConnectionError=_real_requests.exceptions.ConnectionError,
    )
    if now is not None:
        mod._now_ist = lambda: now
    drop_calls = []
    status_calls = []
    fake_drop = types.SimpleNamespace()

    def _send_drop(token, expiry, client_id):
        drop_calls.append((token, expiry, client_id))
        return True

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


def stamp_path_for(tmp_root):
    return tmp_root / "logs" / "dhan_login_attempt.stamp"


def write_stamp(tmp_root, text):
    p = stamp_path_for(tmp_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# T6
# ---------------------------------------------------------------------------

def t6_refuses_recent_stamp(src):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_a_"))
    write_stamp(tmp_root, (FIXED_NOW - timedelta(seconds=100)).isoformat(timespec="seconds"))
    post_fn = make_recording_post(ok_resp())
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("100s-old stamp: exit 3", rc == 3 and exc is None),
        ("100s-old stamp: zero requests made", len(post_fn.calls) == 0),
        ("100s-old stamp: message states 200s remaining", "200s remaining" in out),
    ]


def t6_allows_old_stamp(src):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_b_"))
    write_stamp(tmp_root, (FIXED_NOW - timedelta(seconds=301)).isoformat(timespec="seconds"))
    post_fn = make_recording_post(ok_resp())
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("301s-old stamp: not refused", rc == 0 and exc is None),
        ("301s-old stamp: exactly one request made", len(post_fn.calls) == 1),
    ]


def t6_boundary_299_refused(src):
    """The guard's condition is `0 <= age_s < LOGIN_ATTEMPT_SPACING_S` -- strictly
    less than. A stamp exactly 299s old (one second inside the window) must refuse."""
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_i_"))
    write_stamp(tmp_root, (FIXED_NOW - timedelta(seconds=299)).isoformat(timespec="seconds"))
    post_fn = make_recording_post(ok_resp())
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("299s-old stamp: refused (exit 3)", rc == 3 and exc is None),
        ("299s-old stamp: zero requests made", len(post_fn.calls) == 0),
    ]


def t6_boundary_300_allowed(src):
    """A stamp exactly 300s old (at the threshold, not inside it) must be allowed --
    the boundary is strict-less-than, not less-than-or-equal."""
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_j_"))
    write_stamp(tmp_root, (FIXED_NOW - timedelta(seconds=300)).isoformat(timespec="seconds"))
    post_fn = make_recording_post(ok_resp())
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("300s-old stamp (at threshold): not refused", rc == 0 and exc is None),
        ("300s-old stamp (at threshold): exactly one request made", len(post_fn.calls) == 1),
    ]


def t6_future_dated_stamp_not_refused(src):
    """A stamp dated in the FUTURE (age_s negative -- clock skew, or a hand-edited
    file) must not refuse. The guard's `0 <= age_s < SPACING` lower bound is what
    makes this true; dropping it would make a negative age_s satisfy a bare
    `age_s < SPACING` and refuse a login that was never actually recent."""
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_k_"))
    write_stamp(tmp_root, (FIXED_NOW + timedelta(seconds=50)).isoformat(timespec="seconds"))
    post_fn = make_recording_post(ok_resp())
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("future-dated stamp: not refused", rc == 0 and exc is None),
        ("future-dated stamp: exactly one request made", len(post_fn.calls) == 1),
    ]


def t6_allows_missing_stamp(src):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_c_"))
    post_fn = make_recording_post(ok_resp())
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("no stamp: not refused", rc == 0 and exc is None),
        ("no stamp: exactly one request made", len(post_fn.calls) == 1),
        ("no stamp: a stamp file now exists", stamp_path_for(tmp_root).exists()),
    ]


def t6_stamp_written_before_each_request(src):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_d_"))
    stamp_path = stamp_path_for(tmp_root)
    snapshots = []

    def post(url, params=None, timeout=None):
        snapshots.append(stamp_path.read_text(encoding="utf-8") if stamp_path.exists() else None)
        return invalid_totp_resp() if len(snapshots) == 1 else ok_resp()

    post.calls = snapshots
    with patched_sleep(), rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post, tmp_root)
        clock = {"n": 0}

        def advancing_now():
            clock["n"] += 1
            return FIXED_NOW + timedelta(seconds=clock["n"])

        mod._now_ist = advancing_now
        rc, exc, out = run_main(mod)
    checks = [
        ("exactly two requests made (first + retry)", len(snapshots) == 2),
        ("run succeeds", rc == 0 and exc is None),
    ]
    if len(snapshots) == 2:
        checks.append(("stamp present before the first request", snapshots[0] is not None))
        checks.append(("stamp present before the retry request", snapshots[1] is not None))
        checks.append(("stamp was rewritten for the retry (differs from the first)",
                        snapshots[0] != snapshots[1]))
    return checks


def t6_crash_after_stamp_leaves_stamp(src):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_e_"))
    stamp_path = stamp_path_for(tmp_root)

    def post(url, params=None, timeout=None):
        raise RuntimeError("simulated crash mid-request")

    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("crash mid-request: stamp file still exists", stamp_path.exists()),
        ("crash mid-request: original exception propagated", isinstance(exc, RuntimeError)),
    ]


def t6_stamp_write_failure_fails_open(src):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_f_"))
    # logs/ as a FILE, not a directory -- mkdir(parents=True, exist_ok=True) raises
    # FileExistsError (an OSError) rather than silently succeeding.
    (tmp_root / "logs").write_text("not a directory", encoding="utf-8")
    post_fn = make_recording_post(ok_resp())
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("unwritable logs/: request still sent", len(post_fn.calls) == 1),
        ("unwritable logs/: login still succeeds", rc == 0 and exc is None),
        ("unwritable logs/: a WARNING names the stamp path", "WARNING" in out and "stamp" in out.lower()),
    ]


def t6_naive_timestamp_does_not_crash(src):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_g_"))
    write_stamp(tmp_root, "2026-11-20T09:58:20")  # naive -- no tz offset
    post_fn = make_recording_post(ok_resp())
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("naive-timestamp stamp: no exception", exc is None),
        ("naive-timestamp stamp: treated as no-stamp, run proceeds", rc == 0),
        ("naive-timestamp stamp: exactly one request made", len(post_fn.calls) == 1),
    ]


def t6_garbage_stamp_does_not_crash(src):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_h_"))
    write_stamp(tmp_root, "not a timestamp at all")
    post_fn = make_recording_post(ok_resp())
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("garbage stamp: no exception", exc is None),
        ("garbage stamp: treated as no-stamp, run proceeds", rc == 0),
        ("garbage stamp: exactly one request made", len(post_fn.calls) == 1),
    ]


# ---------------------------------------------------------------------------
# T9
# ---------------------------------------------------------------------------

def t9_footprint(src):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_t9_"))
    (tmp_root / ".env").write_text("DHAN_API_TOKEN=OLD_TOKEN\nKEEP=1\n", encoding="utf-8")
    before = {p.relative_to(tmp_root).as_posix() for p in tmp_root.rglob("*") if p.is_file()}
    env_before = (tmp_root / ".env").read_text(encoding="utf-8")
    post_fn = make_recording_post(ok_resp(token="TOK_T9", expiry="2026-11-21 06:00:00"))
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    after = {p.relative_to(tmp_root).as_posix() for p in tmp_root.rglob("*") if p.is_file()}
    new_files = after - before
    env_after = (tmp_root / ".env").read_text(encoding="utf-8")
    return [
        ("success run: exit 0", rc == 0 and exc is None),
        ("only new files are the stamp and token_status.json",
         new_files == {"logs/dhan_login_attempt.stamp", "runtime/token_status.json"}),
        (".env rewritten in place with the new token", "DHAN_API_TOKEN=TOK_T9" in env_after),
        (".env still carries the unrelated KEEP line", "KEEP=1" in env_after),
        (".env content actually changed", env_before != env_after),
    ]


# ---------------------------------------------------------------------------
# T10
# ---------------------------------------------------------------------------

def t10_idempotency_still_works(src):
    tmp_root = Path(tempfile.mkdtemp(prefix="e1e3e10_guard_t10_"))
    runtime_dir = tmp_root / "runtime"
    runtime_dir.mkdir(parents=True)
    # _idempotency_skip() is pre-existing, unmodified code (D2 note) that reads the REAL
    # wall clock via datetime.now(IST), not the stubbed _now_ist() the guard uses -- so
    # the planted "recent" timestamp must be recent against the real clock, not FIXED_NOW.
    recent_iso = (datetime.now(IST) - timedelta(seconds=30)).isoformat()
    payload = {
        "success": True,
        "refreshed_at_ist": "2026-11-20 09:59:30 IST",
        "refreshed_at_iso": recent_iso,
        "expiry_time": "2026-11-21 06:00:00",
        "error": "",
    }
    (runtime_dir / "token_status.json").write_text(json.dumps(payload), encoding="utf-8")
    post_fn = make_recording_post(ok_resp())
    assert not stamp_path_for(tmp_root).exists(), "precondition: no stamp before the run"
    with rdt_env():
        mod, tmp, drop_calls, status_calls = load_rdt(src, post_fn, tmp_root)
        rc, exc, out = run_main(mod)
    return [
        ("idempotency skip: exit 0", rc == 0 and exc is None),
        ("idempotency skip: zero Dhan requests made", len(post_fn.calls) == 0),
        ("idempotency skip: zero drop/status calls", drop_calls == [] and status_calls == []),
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
    rdt_src = read_src(RDT_PATH)
    ok = True

    ok &= report("T6", t6_refuses_recent_stamp(rdt_src))
    ok &= report("T6", t6_allows_old_stamp(rdt_src))
    ok &= report("T6", t6_boundary_299_refused(rdt_src))
    ok &= report("T6", t6_boundary_300_allowed(rdt_src))
    ok &= report("T6", t6_future_dated_stamp_not_refused(rdt_src))
    ok &= report("T6", t6_allows_missing_stamp(rdt_src))
    ok &= report("T6", t6_stamp_written_before_each_request(rdt_src))
    ok &= report("T6", t6_crash_after_stamp_leaves_stamp(rdt_src))
    ok &= report("T6", t6_stamp_write_failure_fails_open(rdt_src))
    ok &= report("T6", t6_naive_timestamp_does_not_crash(rdt_src))
    ok &= report("T6", t6_garbage_stamp_does_not_crash(rdt_src))
    ok &= report("T9", t9_footprint(rdt_src))
    ok &= report("T10", t10_idempotency_still_works(rdt_src))

    # ---- mutants -----------------------------------------------------
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

    # M1: 300 changed to a smaller value
    mutate(
        "M1 threshold changed to a smaller value", rdt_src,
        "LOGIN_ATTEMPT_SPACING_S = 300",
        "LOGIN_ATTEMPT_SPACING_S = 10",
        "threshold",
    )

    # M2: stamp written after the request instead of before
    mutate(
        "M2 stamp written after the request instead of before", rdt_src,
        'def request_dhan_token(client_id: str, pin: str, totp_code: str) -> Dict:\n'
        '    _write_login_attempt_stamp()\n'
        '    resp = requests.post(\n'
        '        TOKEN_URL,\n'
        '        params={\n'
        '            "dhanClientId": client_id,\n'
        '            "pin": pin,\n'
        '            "totp": totp_code,\n'
        '        },\n'
        '        timeout=30,\n'
        '    )\n',
        'def request_dhan_token(client_id: str, pin: str, totp_code: str) -> Dict:\n'
        '    resp = requests.post(\n'
        '        TOKEN_URL,\n'
        '        params={\n'
        '            "dhanClientId": client_id,\n'
        '            "pin": pin,\n'
        '            "totp": totp_code,\n'
        '        },\n'
        '        timeout=30,\n'
        '    )\n'
        '    _write_login_attempt_stamp()\n',
        "order",
    )

    # M3: the stamp write no longer fails open -- a logs/ that cannot be written
    # raises instead of being swallowed.
    mutate(
        "M3 stamp write no longer fails open (except OSError removed)", rdt_src,
        '    except OSError:\n'
        '        print(f"WARNING: could not write login attempt stamp at {LOGIN_ATTEMPT_STAMP}; proceeding anyway.")\n',
        '    except KeyError:\n'
        '        print(f"WARNING: could not write login attempt stamp at {LOGIN_ATTEMPT_STAMP}; proceeding anyway.")\n',
        "fails_open",
    )

    # M4: TypeError dropped from the guard's except -- a naive-timestamp stamp
    # crashes the run instead of being treated as no-stamp.
    mutate(
        "M4 TypeError dropped from the guard's except", rdt_src,
        "    except (OSError, ValueError, TypeError):\n",
        "    except (OSError, ValueError):\n",
        "guard_typeerror",
    )

    # M5: ValueError dropped from the guard's except -- a garbage stamp crashes
    # the run instead of being treated as no-stamp.
    mutate(
        "M5 ValueError dropped from the guard's except", rdt_src,
        "    except (OSError, ValueError, TypeError):\n",
        "    except (OSError, TypeError):\n",
        "guard_valueerror",
    )

    # M6: the guard's refusal exit code silently becomes success.
    mutate(
        "M6 guard refusal return 3 -> return 0", rdt_src,
        '              f"{remaining}s remaining before the next attempt is allowed.")\n'
        '        return 3\n',
        '              f"{remaining}s remaining before the next attempt is allowed.")\n'
        '        return 0\n',
        "refusal_rc",
    )

    # M7: threshold widened 300 -> 600 (the other direction from M1).
    mutate(
        "M7 threshold widened 300 -> 600", rdt_src,
        "LOGIN_ATTEMPT_SPACING_S = 300",
        "LOGIN_ATTEMPT_SPACING_S = 600",
        "threshold_large",
    )

    # M8: boundary strict-less-than widened to <= -- a stamp exactly at the
    # threshold (300s old) now refuses when it should not.
    mutate(
        "M8 boundary < widened to <=", rdt_src,
        "if 0 <= age_s < LOGIN_ATTEMPT_SPACING_S:",
        "if 0 <= age_s <= LOGIN_ATTEMPT_SPACING_S:",
        "boundary_le",
    )

    # M9: the `0 <=` lower bound dropped -- a future-dated stamp (negative age_s)
    # now satisfies a bare `age_s < SPACING` and incorrectly refuses.
    mutate(
        "M9 lower bound 0 <= dropped", rdt_src,
        "if 0 <= age_s < LOGIN_ATTEMPT_SPACING_S:",
        "if age_s < LOGIN_ATTEMPT_SPACING_S:",
        "lower_bound",
    )

    if anchor_failures:
        ok = False

    killed = 0
    surviving = []
    for label, msrc, kind in mutants:
        try:
            if kind == "threshold":
                cells = t6_refuses_recent_stamp(msrc) + t6_allows_old_stamp(msrc)
            elif kind == "order":
                cells = t6_crash_after_stamp_leaves_stamp(msrc) + t6_stamp_written_before_each_request(msrc)
            elif kind == "fails_open":
                cells = t6_stamp_write_failure_fails_open(msrc)
            elif kind == "guard_typeerror":
                cells = t6_naive_timestamp_does_not_crash(msrc)
            elif kind == "guard_valueerror":
                cells = t6_garbage_stamp_does_not_crash(msrc)
            elif kind == "refusal_rc":
                cells = t6_refuses_recent_stamp(msrc)
            elif kind == "threshold_large":
                cells = t6_boundary_300_allowed(msrc) + t6_boundary_299_refused(msrc)
            elif kind == "boundary_le":
                cells = t6_boundary_300_allowed(msrc)
            elif kind == "lower_bound":
                cells = t6_future_dated_stamp_not_refused(msrc)
            else:
                cells = []
        except BaseException:
            cells = [("mutant raised instead of behaving differently", False)]
        caught = any(not passed for _, passed in cells)
        if caught:
            killed += 1
            print(f"  CAUGHT: {label}")
        else:
            surviving.append(label)
            print(f"  SURVIVED (BAD): {label}")

    print(f"mutants {len(mutants)}, anchor failures {len(anchor_failures)}, "
          f"killed {killed}, surviving {len(surviving)} (must be 0)")
    ok &= (len(surviving) == 0) and (len(anchor_failures) == 0)

    print(f"DHAN LOGIN GUARD {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
