"""Tape runner constants (phase T0). Env-var NAMES only; values are never read here."""
import os

# --- credentials: names only (values live in /etc/tape/*.env, readable by user tape) -------
ENV_API_KEY = "ZERODHA_API_KEY"            # /etc/tape/kite_api.env
ENV_ACCESS_TOKEN = "ZERODHA_ACCESS_TOKEN"  # /etc/tape/kite_token.env
ENV_AWS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION")  # /etc/tape/aws.env
ENV_REQUIRED = (ENV_API_KEY, ENV_ACCESS_TOKEN) + ENV_AWS

BUCKET = os.environ.get("TAPE_BUCKET", "meridian-tape-raw")

# --- rehearsal-only hooks (tests/rehearsal). BOTH UNSET IN PRODUCTION: the unit file sets neither,
# and with both empty the runner's keys and files are exactly what they were before the hooks. ---
KEY_PREFIX = os.environ.get("TAPE_KEY_PREFIX", "")            # e.g. "_rehearsal/20261101T070000Z/"
REHEARSAL_KEEP = os.environ.get("TAPE_REHEARSAL_KEEP", "")    # e.g. "/var/lib/tape/rehearsal_keep"
REHEARSAL_PREFIX_ROOT = "_rehearsal/"


def check_rehearsal_hooks(prefix, keep):
    """A prefix may only ever point under _rehearsal/ (production keys can never be moved by a stray
    variable), and the local keep copy exists only together with such a prefix."""
    if prefix and not (prefix.startswith(REHEARSAL_PREFIX_ROOT) and prefix.endswith("/")
                       and ".." not in prefix and len(prefix) > len(REHEARSAL_PREFIX_ROOT)):
        raise ValueError("TAPE_KEY_PREFIX must be empty or _rehearsal/<id>/")
    if keep and not prefix:
        raise ValueError("TAPE_REHEARSAL_KEEP requires TAPE_KEY_PREFIX")
ROOT = os.environ.get("TAPE_ROOT", "/var/lib/tape")

# --- universe -------------------------------------------------------------------------------
SYMBOLS = {
    "NIFTY": {"exchange": "NFO", "ltp_key": "NSE:NIFTY 50", "half_window": 20, "expected_index_token": 256265},
    "SENSEX": {"exchange": "BFO", "ltp_key": "BSE:SENSEX", "half_window": 15, "expected_index_token": 265},
}
GROW_THRESHOLD = 12        # listed strikes between ATM and window centre before the window grows
ATM_BAND = 3               # daily report: packets per minute at ATM +- 3 listed strikes

# --- timeline (IST, "HH:MM") ----------------------------------------------------------------
T_START = "08:50"          # a start before this exits 0 untouched: the 08:50 timer starts a fresh process (finding 4)
T_RESOLVE = "08:55"
T_RESOLVE_GIVEUP = "09:10"
T_OPTIONS = "09:00"
T_CLOSED_CHECK = "09:20"   # never declare CLOSED before 09:20 IST (review 2026-11-01, item 4)
CLOSED_CHECK_SETTLE_S = 60 # ... and only after the feed has been connected this long (late/boot starts)
T_SESSION_START = "09:15"
T_SESSION_END = "15:30"
T_STOP = "15:40"
DRAIN_SECONDS = 15 * 60    # 15:40 stop -> uploads drained until 15:55
RESOLVE_RETRY_S = 30
TOKEN_PROBE_AFTER_S = 60   # disconnected this long -> kite.profile() probe (review finding 3)
TOKEN_PROBE_EVERY_S = 60
TOKEN_FAIL_DRAIN_S = 60
TERM_DRAIN_S = 60          # SIGTERM: drain uploads this long, inside systemd TimeoutStopSec=90 (finding 6)
TOKEN_EXCEPTIONS = ("TokenException", "PermissionException")  # kiteconnect.exceptions class names

# --- silence watchdog (T0.1): no websocket frame of any kind (tick packet or 1-byte heartbeat) for
# SILENCE_S seconds, inside the recording window -> force-close the socket; the library reconnects. ---
SILENCE_S = 15             # seconds
SILENCE_MIN_S = 5          # hard floor: a mis-set SILENCE_S can never go below this
WD_BACKOFF_S = (1, 2, 4, 8, 15)   # seconds between watchdog attempts while the silence persists; last value repeats
WD_TRIP_LIST_CAP = 200     # trips kept in the daily report
LIB_RECONNECT = {"initialDelay": 1.0, "factor": 2.0, "maxDelay": 15, "jitter": 0}   # Twisted factory: 1,2,4,8,15,15 s

# --- special sessions (T0.1): dates that override the default window (Muhurat). IST, checked in. ---
SPECIAL_SESSIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "special_sessions.json")

# --- exit codes -----------------------------------------------------------------------------
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_SPOOL_CAP = 75
EXIT_TOKEN_FAIL = 78

# --- spool / segments / upload --------------------------------------------------------------
SPOOL_CAP_BYTES = 2 * 1024 ** 3
SEG_SECONDS = 300
GAP_SHORT_S = 10
GAP_LONG_S = 60
BACKOFF_CAP_S = 60
