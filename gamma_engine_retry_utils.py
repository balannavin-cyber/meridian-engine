from __future__ import annotations

import time
from typing import Callable, TypeVar


T = TypeVar("T")


def retry_call(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    delay_seconds: float = 5.0,
    backoff_multiplier: float = 1.0,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    label: str = "operation",
) -> T:
    last_exc = None
    current_delay = delay_seconds

    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except retry_exceptions as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            print(
                f"[retry_call] {label} failed on attempt {attempt}/{attempts} "
                f"with error: {exc}. Retrying in {current_delay:.1f}s..."
            )
            time.sleep(current_delay)
            current_delay *= backoff_multiplier if backoff_multiplier > 0 else 1.0

    if last_exc is not None:
        raise last_exc

    raise RuntimeError(f"{label} failed unexpectedly without captured exception")