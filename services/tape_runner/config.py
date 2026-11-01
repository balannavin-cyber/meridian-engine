"""Tape runner constants (phase T0). Env-var NAMES only; values are never read here."""
import os

# --- credentials: names only (values live in /etc/tape/*.env, readable by user tape) -------
ENV_API_KEY = "ZERODHA_API_KEY"            # /etc/tape/kite_api.env
ENV_ACCESS_TOKEN = "ZERODHA_ACCESS_TOKEN"  # /etc/tape/kite_token.env
ENV_AWS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION")  # /etc/tape/aws.env
ENV_REQUIRED = (ENV_API_KEY, ENV_ACCESS_TOKEN) + ENV_AWS

BUCKET = os.environ.get("TAPE_BUCKET", "meridian-tape-raw")
ROOT = os.environ.get("TAPE_ROOT", "/var/lib/tape")

# --- universe -------------------------------------------------------------------------------
SYMBOLS = {
    "NIFTY": {"exchange": "NFO", "ltp_key": "NSE:NIFTY 50", "half_window": 20, "expected_index_token": 256265},
    "SENSEX": {"exchange": "BFO", "ltp_key": "BSE:SENSEX", "half_window": 15, "expected_index_token": 265},
}
GROW_THRESHOLD = 12        # listed strikes between ATM and window centre before the window grows
ATM_BAND = 3               # daily report: packets per minute at ATM +- 3 listed strikes

# --- timeline (IST, "HH:MM") ----------------------------------------------------------------
T_RESOLVE = "08:55"
T_RESOLVE_GIVEUP = "09:10"
T_OPTIONS = "09:00"
T_CLOSED_CHECK = "09:20"   # never declare CLOSED before 09:20 IST (review 2026-11-01, item 4)
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
