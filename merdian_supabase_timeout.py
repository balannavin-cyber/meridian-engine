"""
merdian_supabase_timeout.py — TD-062 step (2).

Wraps any Supabase (or other blocking I/O) call with a wall-clock timeout.
Prevents a stuck network call from hanging an entire MERDIAN task forever
(the dominant TD-062 hypothesis: Supabase calendar-gate calls hang on
network-unusual conditions and never return).

Usage:

    from merdian_supabase_timeout import call_with_timeout, SupabaseTimeout

    try:
        rows = call_with_timeout(
            supabase.table("trading_calendar").select("*").eq("date", today).execute,
            timeout_sec=10,
        )
    except SupabaseTimeout:
        # Failsafe: log and either bail OR fall back to a cached calendar
        log.error("calendar-gate Supabase call timed out")
        sys.exit(1)

Implementation note: thread.join with timeout does NOT actually kill the
underlying call. The thread is daemon, so it will be cleaned up when the
process eventually exits. The point of this helper is to PREVENT the host
script from hanging forever — the dangling thread is acceptable cost.

For a hard-kill timeout, use `subprocess.run(..., timeout=N)` to invoke
the Supabase call in a child process. That is invasive enough that we
recommend the watchdog (merdian_watchdog.py) as the hard-kill backstop
instead, and use this helper for soft timeouts inside scripts.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class SupabaseTimeout(Exception):
    """Raised when call_with_timeout exceeds its wall-clock budget."""


def call_with_timeout(
    fn: Callable[..., T],
    timeout_sec: float,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Run fn(*args, **kwargs) in a daemon thread; raise SupabaseTimeout if it
    does not complete within timeout_sec. Re-raises any exception fn raised.
    """
    result: list[Any] = [None]
    error: list[BaseException | None] = [None]

    def _worker() -> None:
        try:
            result[0] = fn(*args, **kwargs)
        except BaseException as e:  # noqa: BLE001 - re-raised in caller
            error[0] = e

    t = threading.Thread(
        target=_worker,
        daemon=True,
        name=f"timeout-{getattr(fn, '__name__', 'fn')}",
    )
    t.start()
    t.join(timeout=timeout_sec)

    if t.is_alive():
        raise SupabaseTimeout(
            f"call to {getattr(fn, '__name__', repr(fn))} "
            f"exceeded {timeout_sec}s wall clock"
        )
    if error[0] is not None:
        raise error[0]
    return result[0]  # type: ignore[return-value]
