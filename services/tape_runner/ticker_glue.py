"""Production-only glue between the recorder and kiteconnect / Twisted (never imported by the offline tests
with the real classes). ``make_watched_ticker_class`` takes the base class and ``call_from_thread`` as
arguments so the tests can pass stubs; ``__main__`` passes ``KiteTicker`` and ``reactor.callFromThread``.

Two things the stock KiteTicker 5.2.2 does not give us:
- a way to drop the socket from another thread (``force_reconnect``): the library's own ping loop never sends
  a ping, so its pong check can never fire and a silently dead peer is found only by TCP timers;
- a reconnect delay of 1, 2, 4, 8, 15, 15 ... s (Twisted ReconnectingClientFactory: initialDelay=1, factor=2,
  maxDelay=15, jitter=0). The factory only exists after ``connect()``, so it is tuned there.
"""
from . import config


def make_watched_ticker_class(base, call_from_thread):
    class WatchedTicker(base):
        def connect(self, *args, **kwargs):
            out = super().connect(*args, **kwargs)
            f = self.factory
            for name, value in config.LIB_RECONNECT.items():
                setattr(f, name, value)
            return out

        def force_reconnect(self):
            """Abort the socket from the reactor thread. clientConnectionLost -> retry() is the library's own
            reconnect path; nothing else reconnects."""
            ws = self.factory.ws
            call_from_thread(ws.dropConnection, abort=True)

    return WatchedTicker
