"""
premium_outcome_writer.py
=========================
MERDIAN — Signal Premium Outcome Writer

For every BUY_CE / BUY_PE signal in signal_snapshots that does not yet
have a row in signal_premium_outcomes, this script:

  1. Finds the ATM option contract at signal time
  2. Looks up LTP at T+15m, T+30m, T+60m, EOD from option_chain_snapshots
  3. Computes premium moves, capture thresholds, IV change, outcome label
  4. If hist_option_bars_1m is populated for the signal date, computes
     path-dependent fields (MFE, MAE, time_to_mfe, drawdown_before_profit)
  5. Writes one row to signal_premium_outcomes per signal

Safe to run repeatedly — skips signals already evaluated.
Designed to run on a schedule (e.g. every 5 minutes during market hours,
once EOD after close).

Usage:
    python premium_outcome_writer.py              # process all pending
    python premium_outcome_writer.py --backfill   # force reprocess all
    python premium_outcome_writer.py --symbol NIFTY
    python premium_outcome_writer.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from core.config import get_settings
from core.supabase_client import SupabaseClient

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(get_settings().logs_dir) / "premium_outcome_writer.log",
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger("outcome_writer")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 29)
SESSION_MINUTES = 375

HORIZON_MINUTES = [15, 30, 60]

# Outcome label thresholds (points)
WIN_LARGE_THRESHOLD  = 75.0
WIN_MEDIUM_THRESHOLD = 25.0
LOSS_LARGE_THRESHOLD = -25.0

# IV crush: direction correct but IV contraction ate premium
IV_CRUSH_THRESHOLD = -2.0   # IV dropped more than 2 percentage points

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_float(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def to_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def to_ts(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def add_minutes(ts: datetime, minutes: int) -> datetime:
    return ts + timedelta(minutes=minutes)


def dte_bucket(dte: int | None) -> str:
    if dte is None:
        return "UNKNOWN"
    if dte == 0:
        return "ZERO_DTE"
    if dte == 1:
        return "ONE_DTE"
    if dte <= 6:
        return "WEEKLY"
    return "MONTHLY"


def intraday_bucket(t: time) -> str:
    if t < time(10, 0):
        return "OPEN"
    if t < time(12, 0):
        return "MID_MORNING"
    if t < time(14, 0):
        return "POST_LUNCH"
    return "CLOSE"


def session_pct_elapsed(t: time) -> float:
    open_mins = SESSION_OPEN.hour * 60 + SESSION_OPEN.minute
    close_mins = SESSION_CLOSE.hour * 60 + SESSION_CLOSE.minute
    cur_mins = t.hour * 60 + t.minute
    elapsed = max(0, cur_mins - open_mins)
    total = close_mins - open_mins
    return round(min(100.0, (elapsed / total) * 100), 2)


def straddle_slope_label(slope: float | None) -> str | None:
    if slope is None:
        return None
    if slope > 0:
        return "EXPANDING"
    if slope < 0:
        return "COMPRESSING"
    return "FLAT"


def confidence_decile(score: float | None) -> int | None:
    if score is None:
        return None
    return min(10, max(1, int(score / 10) + 1))


def classify_outcome(move_eod: float | None, move_60m: float | None) -> str | None:
    """Classify the trade outcome based on best available horizon."""
    move = move_eod if move_eod is not None else move_60m
    if move is None:
        return None
    if move >= WIN_LARGE_THRESHOLD:
        return "WIN_LARGE"
    if move >= WIN_MEDIUM_THRESHOLD:
        return "WIN_MEDIUM"
    if move >= 0:
        return "WIN_SMALL"
    if move >= LOSS_LARGE_THRESHOLD:
        return "LOSS_SMALL"
    return "LOSS_LARGE"


def classify_failure(
    move_eod: float | None,
    move_60m: float | None,
    iv_change: float | None,
    direction_correct: bool | None,
    mfe: float | None,
) -> str | None:
    """Classify why a losing trade failed."""
    best_move = move_eod if move_eod is not None else move_60m
    if best_move is None:
        return None
    if best_move >= 0:
        return None  # winner, no failure mode

    # Direction was right but IV crushed premium
    if direction_correct and iv_change is not None and iv_change < IV_CRUSH_THRESHOLD:
        return "IV_CRUSH"

    # Premium went up then reversed
    if mfe is not None and mfe > 10 and best_move < -5:
        return "MOVED_THEN_REVERSED"

    # Never moved
    if mfe is not None and mfe < 5:
        return "NEVER_MOVED"

    # Slow decay
    if mfe is not None and 0 < mfe < 15:
        return "THETA_DECAY"

    return "NEVER_MOVED"


# ---------------------------------------------------------------------------
# Chain data lookup
# ---------------------------------------------------------------------------

class ChainLookup:
    """
    Looks up option LTP from option_chain_snapshots for a given
    symbol, strike, option_type around a target timestamp.
    Uses nearest available snapshot within a tolerance window.
    """

    TOLERANCE_MINUTES = 8   # accept snapshots within 8 minutes of target

    def __init__(self, client: SupabaseClient):
        self.client = client

    def get_ltp(
        self,
        symbol: str,
        strike: float,
        option_type: str,
        expiry_date: date,
        target_ts: datetime,
    ) -> float | None:
        """Find LTP nearest to target_ts within tolerance."""
        window_start = (target_ts - timedelta(minutes=self.TOLERANCE_MINUTES)).isoformat()
        window_end   = (target_ts + timedelta(minutes=self.TOLERANCE_MINUTES)).isoformat()

        rows = self.client.select(
            "option_chain_snapshots",
            columns="ltp,iv,created_at",
            filters={
                "symbol": symbol,
                "strike": float(strike),
                "option_type": option_type,
                "expiry_date": expiry_date.isoformat(),
                "created_at": f"gte.{window_start}",
            },
        )

        # Filter upper bound manually (Supabase REST can only apply one range filter)
        rows = [
            r for r in rows
            if r.get("created_at", "") <= window_end
        ]

        if not rows:
            return None

        # Sort by proximity to target
        def proximity(r: dict) -> float:
            ts = to_ts(r.get("created_at"))
            if ts is None:
                return 9999
            return abs((ts - target_ts).total_seconds())

        rows.sort(key=proximity)
        return to_float(rows[0].get("ltp"))

    def get_ltp_and_iv(
        self,
        symbol: str,
        strike: float,
        option_type: str,
        expiry_date: date,
        target_ts: datetime,
    ) -> tuple[float | None, float | None]:
        """Find LTP and IV nearest to target_ts."""
        window_start = (target_ts - timedelta(minutes=self.TOLERANCE_MINUTES)).isoformat()
        window_end   = (target_ts + timedelta(minutes=self.TOLERANCE_MINUTES)).isoformat()

        rows = self.client.select(
            "option_chain_snapshots",
            columns="ltp,iv,created_at",
            filters={
                "symbol": symbol,
                "strike": float(strike),
                "option_type": option_type,
                "expiry_date": expiry_date.isoformat(),
                "created_at": f"gte.{window_start}",
            },
        )

        rows = [r for r in rows if r.get("created_at", "") <= window_end]
        if not rows:
            return None, None

        def proximity(r: dict) -> float:
            ts = to_ts(r.get("created_at"))
            return abs((ts - target_ts).total_seconds()) if ts else 9999

        rows.sort(key=proximity)
        best = rows[0]
        return to_float(best.get("ltp")), to_float(best.get("iv"))

    def get_spot_at(
        self,
        symbol: str,
        target_ts: datetime,
    ) -> float | None:
        """Get spot price nearest to target_ts from option_chain_snapshots."""
        window_start = (target_ts - timedelta(minutes=self.TOLERANCE_MINUTES)).isoformat()
        window_end   = (target_ts + timedelta(minutes=self.TOLERANCE_MINUTES)).isoformat()

        rows = self.client.select(
            "option_chain_snapshots",
            columns="spot,created_at",
            filters={
                "symbol": symbol,
                "created_at": f"gte.{window_start}",
            },
        )
        rows = [r for r in rows if r.get("created_at", "") <= window_end and r.get("spot")]
        if not rows:
            return None

        def proximity(r: dict) -> float:
            ts = to_ts(r.get("created_at"))
            return abs((ts - target_ts).total_seconds()) if ts else 9999

        rows.sort(key=proximity)
        return to_float(rows[0].get("spot"))


# ---------------------------------------------------------------------------
# Historical bar path data lookup (hist_option_bars_1m)
# ---------------------------------------------------------------------------

class HistBarLookup:
    """
    Computes path-dependent metrics from hist_option_bars_1m.
    Returns None for all fields if hist data not available for the date.
    """

    def __init__(self, client: SupabaseClient):
        self.client = client

    def is_available(self, symbol: str, trade_date: date) -> bool:
        rows = self.client.select(
            "hist_option_bars_1m",
            columns="id",
            filters={"trade_date": trade_date.isoformat()},
            limit=1,
        )
        return len(rows) > 0

    def get_session_bars(
        self,
        symbol: str,
        strike: float,
        option_type: str,
        expiry_date: date,
        trade_date: date,
        entry_ts: datetime,
    ) -> list[dict]:
        """Fetch all 1m bars from entry_ts to session close."""
        rows = self.client.select(
            "hist_option_bars_1m",
            columns="bar_ts,open,high,low,close,volume",
            filters={
                "trade_date": trade_date.isoformat(),
                "expiry_date": expiry_date.isoformat(),
                "strike": float(strike),
                "option_type": option_type,
                "bar_ts": f"gte.{entry_ts.isoformat()}",
                "is_pre_market": "eq.false",
            },
        )
        return sorted(rows, key=lambda r: r.get("bar_ts", ""))

    def compute_path_metrics(
        self,
        bars: list[dict],
        entry_premium: float,
    ) -> dict[str, Any]:
        """
        Compute MFE, MAE, time_to_mfe, drawdown_before_profit,
        first_adverse_move from intrabar path.
        """
        if not bars or entry_premium <= 0:
            return {}

        closes = [to_float(b.get("close")) for b in bars]
        closes = [c for c in closes if c is not None]
        if not closes:
            return {}

        moves = [c - entry_premium for c in closes]

        mfe = max(moves)
        mae = min(moves)

        # Time to MFE
        mfe_idx = moves.index(mfe)
        time_to_mfe = mfe_idx + 1  # minutes from entry (1-indexed)

        # MFE to close giveback
        final_move = moves[-1]
        if mfe > 0:
            giveback_pct = round((mfe - final_move) / mfe * 100, 2)
        else:
            giveback_pct = None

        # First adverse move (first bar that goes negative)
        first_adverse = None
        for m in moves:
            if m < 0:
                first_adverse = abs(m)
                break

        # Drawdown before first profit
        drawdown_before_profit = None
        seen_profit = False
        running_min = 0.0
        for m in moves:
            if m > 0:
                seen_profit = True
                break
            running_min = min(running_min, m)
        if not seen_profit and running_min < 0:
            drawdown_before_profit = abs(running_min)
        elif seen_profit:
            drawdown_before_profit = abs(running_min) if running_min < 0 else 0.0

        return {
            "mfe_session_pts": round(mfe, 2),
            "mae_session_pts": round(mae, 2),
            "time_to_mfe_mins": time_to_mfe,
            "mfe_to_close_giveback_pct": giveback_pct,
            "first_adverse_move_pts": round(first_adverse, 2) if first_adverse else 0.0,
            "drawdown_before_profit_pts": round(drawdown_before_profit, 2) if drawdown_before_profit is not None else None,
        }


# ---------------------------------------------------------------------------
# IV percentile lookup
# ---------------------------------------------------------------------------

def compute_iv_percentile(
    client: SupabaseClient,
    symbol: str,
    expiry_date: date,
    current_iv: float,
    signal_ts: datetime,
    lookback_days: int = 30,
) -> float | None:
    """
    Compute where current_iv sits in the distribution of ATM IVs
    over the prior lookback_days.
    """
    since = (signal_ts - timedelta(days=lookback_days)).isoformat()
    rows = client.select(
        "volatility_snapshots",
        columns="atm_iv_avg",
        filters={
            "symbol": symbol,
            "ts": f"gte.{since}",
        },
    )
    ivs = [to_float(r.get("atm_iv_avg")) for r in rows]
    ivs = [v for v in ivs if v is not None]
    if not ivs:
        return None
    below = sum(1 for v in ivs if v <= current_iv)
    return round((below / len(ivs)) * 100, 1)


# ---------------------------------------------------------------------------
# Signal clustering
# ---------------------------------------------------------------------------

def get_clustering_metrics(
    client: SupabaseClient,
    symbol: str,
    action: str,
    signal_ts: datetime,
) -> tuple[float | None, int]:
    """
    Returns (mins_since_prior_signal, consecutive_same_direction).
    """
    lookback = (signal_ts - timedelta(hours=4)).isoformat()

    rows = client.select(
        "signal_snapshots",
        columns="ts,action",
        filters={
            "symbol": symbol,
            "action": action,
            "ts": f"gte.{lookback}",
        },
        order="ts",
        ascending=False,
    )

    # Exclude the current signal itself
    prior = [
        r for r in rows
        if to_ts(r.get("ts")) is not None
        and to_ts(r.get("ts")) < signal_ts
    ]

    if not prior:
        return None, 1

    most_recent_ts = to_ts(prior[0].get("ts"))
    mins_since = (signal_ts - most_recent_ts).total_seconds() / 60 if most_recent_ts else None

    # Count consecutive
    consecutive = 1
    for r in prior:
        if r.get("action") == action:
            consecutive += 1
        else:
            break

    return (round(mins_since, 1) if mins_since else None), consecutive


# ---------------------------------------------------------------------------
# Core: evaluate one signal
# ---------------------------------------------------------------------------

def evaluate_signal(
    signal: dict,
    chain: ChainLookup,
    hist: HistBarLookup,
    client: SupabaseClient,
    dry_run: bool = False,
) -> dict | None:
    """
    Build a signal_premium_outcomes row for one signal_snapshots row.
    Returns None if insufficient data to evaluate.
    """
    sig_id   = signal.get("id")
    symbol   = signal.get("symbol", "")
    action   = signal.get("action", "")
    sig_ts   = to_ts(signal.get("ts"))

    if sig_ts is None:
        log.warning(f"Signal {sig_id}: unparseable ts, skipping")
        return None

    # Determine option_type from action
    if action == "BUY_CE":
        option_type = "CE"
    elif action == "BUY_PE":
        option_type = "PE"
    else:
        return None  # DO_NOTHING — no premium to track

    strike      = to_float(signal.get("atm_strike"))
    expiry_date = to_date(signal.get("expiry_date"))
    entry_spot  = to_float(signal.get("spot"))
    entry_iv    = to_float(signal.get("atm_iv_avg")) or to_float(
        signal.get("atm_call_iv") if option_type == "CE" else signal.get("atm_put_iv")
    )
    dte         = signal.get("dte")
    trade_date  = sig_ts.date()

    if strike is None or expiry_date is None:
        log.warning(f"Signal {sig_id}: missing strike or expiry_date, skipping")
        return None

    log.info(f"Evaluating signal {sig_id} | {symbol} {action} {strike}{option_type} "
             f"expiry={expiry_date} ts={sig_ts.isoformat()}")

    # ------------------------------------------------------------------
    # Entry premium
    # ------------------------------------------------------------------
    entry_premium, entry_iv_chain = chain.get_ltp_and_iv(
        symbol, strike, option_type, expiry_date, sig_ts
    )
    if entry_iv is None:
        entry_iv = entry_iv_chain

    if entry_premium is None:
        log.warning(f"Signal {sig_id}: no chain data at entry time, skipping")
        return None

    # ------------------------------------------------------------------
    # Horizon LTPs
    # ------------------------------------------------------------------
    horizon_ltps: dict[int, float | None] = {}
    for mins in HORIZON_MINUTES:
        target_ts = add_minutes(sig_ts, mins)
        # Don't look past session close
        if target_ts.time() > SESSION_CLOSE:
            horizon_ltps[mins] = None
            continue
        horizon_ltps[mins] = chain.get_ltp(
            symbol, strike, option_type, expiry_date, target_ts
        )

    # EOD — look for last snapshot before session close
    eod_ts = sig_ts.replace(hour=15, minute=29, second=0, microsecond=0)
    if eod_ts > sig_ts:
        premium_eod, iv_eod = chain.get_ltp_and_iv(
            symbol, strike, option_type, expiry_date, eod_ts
        )
    else:
        premium_eod, iv_eod = None, None

    # ------------------------------------------------------------------
    # Premium moves
    # ------------------------------------------------------------------
    def move(ltp: float | None) -> float | None:
        return round(ltp - entry_premium, 2) if ltp is not None else None

    move_15m  = move(horizon_ltps.get(15))
    move_30m  = move(horizon_ltps.get(30))
    move_60m  = move(horizon_ltps.get(60))
    move_eod  = move(premium_eod)

    best_move = next((m for m in [move_eod, move_60m, move_30m, move_15m] if m is not None), None)

    # ------------------------------------------------------------------
    # Capture thresholds
    # ------------------------------------------------------------------
    mfe_proxy = max((m for m in [move_15m, move_30m, move_60m, move_eod] if m is not None), default=None)

    captured_25  = mfe_proxy is not None and mfe_proxy >= 25
    captured_50  = mfe_proxy is not None and mfe_proxy >= 50
    captured_75  = mfe_proxy is not None and mfe_proxy >= 75
    captured_100 = mfe_proxy is not None and mfe_proxy >= 100

    # ------------------------------------------------------------------
    # IV change
    # ------------------------------------------------------------------
    iv_change = None
    iv_crushed = None
    if entry_iv is not None and iv_eod is not None:
        iv_change = round(iv_eod - entry_iv, 4)

    # ------------------------------------------------------------------
    # Spot moves for direction correctness
    # ------------------------------------------------------------------
    spot_15m = chain.get_spot_at(symbol, add_minutes(sig_ts, 15))
    spot_60m = chain.get_spot_at(symbol, add_minutes(sig_ts, 60))

    spot_move_15m = round(spot_15m - entry_spot, 2) if spot_15m and entry_spot else None
    spot_move_60m = round(spot_60m - entry_spot, 2) if spot_60m and entry_spot else None

    # Direction correct: spot moved in the direction of the trade
    if spot_move_60m is not None:
        if option_type == "CE":
            direction_correct = spot_move_60m > 0
        else:
            direction_correct = spot_move_60m < 0
    else:
        direction_correct = None

    # IV crush: direction was right but premium still lost
    if iv_change is not None and direction_correct:
        iv_crushed = iv_change < IV_CRUSH_THRESHOLD and best_move is not None and best_move < 0

    # ------------------------------------------------------------------
    # Outcome classification
    # ------------------------------------------------------------------
    outcome_label = classify_outcome(move_eod, move_60m)
    failure_mode  = classify_failure(move_eod, move_60m, iv_change, direction_correct, mfe_proxy)

    # ------------------------------------------------------------------
    # Session timing
    # ------------------------------------------------------------------
    sig_time    = sig_ts.astimezone(timezone.utc).time()
    day_of_week = sig_ts.isoweekday()  # 1=Mon, 7=Sun

    # ------------------------------------------------------------------
    # IV percentile
    # ------------------------------------------------------------------
    iv_percentile = None
    if entry_iv is not None:
        iv_percentile = compute_iv_percentile(client, symbol, expiry_date, entry_iv, sig_ts)

    # ------------------------------------------------------------------
    # Signal clustering
    # ------------------------------------------------------------------
    mins_since_prior, consecutive = get_clustering_metrics(client, symbol, action, sig_ts)

    # ------------------------------------------------------------------
    # Path metrics from hist_option_bars_1m
    # ------------------------------------------------------------------
    path_metrics: dict[str, Any] = {}
    path_available = False

    if hist.is_available(symbol, trade_date):
        bars = hist.get_session_bars(
            symbol, strike, option_type, expiry_date, trade_date, sig_ts
        )
        if bars:
            path_metrics = hist.compute_path_metrics(bars, entry_premium)
            path_available = True
            log.info(f"Signal {sig_id}: path metrics computed from {len(bars)} hist bars")

    # ------------------------------------------------------------------
    # Assemble output row
    # ------------------------------------------------------------------
    dte_val = signal.get("dte")
    if dte_val is None and expiry_date:
        dte_val = (expiry_date - trade_date).days

    premium_as_pct = round((entry_premium / entry_spot) * 100, 4) if entry_spot and entry_spot > 0 else None

    row = {
        # Identity
        "signal_snapshot_id": sig_id,
        "symbol": symbol,
        "signal_ts": sig_ts.isoformat(),
        "action": action,
        "trade_allowed": signal.get("trade_allowed"),

        # Entry context
        "entry_spot": entry_spot,
        "entry_strike": strike,
        "option_type": option_type,
        "expiry_date": expiry_date.isoformat() if expiry_date else None,
        "dte_at_entry": dte_val,
        "dte_bucket": dte_bucket(dte_val),
        "entry_premium": entry_premium,
        "entry_iv": entry_iv,
        "entry_iv_percentile": iv_percentile,
        "entry_quality": signal.get("entry_quality"),
        "premium_as_pct_spot": premium_as_pct,

        # Conditions
        "gamma_regime": signal.get("gamma_regime"),
        "breadth_regime": signal.get("breadth_regime"),
        "breadth_score": to_float(signal.get("breadth_score")),
        "confidence_score": to_float(signal.get("confidence_score")),
        "confidence_decile": confidence_decile(to_float(signal.get("confidence_score"))),
        "flip_distance": to_float(signal.get("flip_distance")),
        "flip_distance_pct": to_float(signal.get("flip_distance_pct")),
        "volatility_regime": signal.get("volatility_regime"),
        "india_vix": to_float(signal.get("india_vix")),
        "vix_regime": signal.get("vix_regime"),
        "straddle_atm": to_float(signal.get("straddle_atm")),
        "straddle_slope": straddle_slope_label(to_float(signal.get("straddle_slope"))),
        "wcb_regime": signal.get("wcb_regime"),
        "wcb_score": to_float(signal.get("wcb_score")),

        # Session timing
        "time_of_day": sig_time.isoformat(),
        "intraday_bucket": intraday_bucket(sig_time),
        "day_of_week": day_of_week,
        "session_pct_elapsed": session_pct_elapsed(sig_time),

        # Clustering
        "mins_since_prior_signal": mins_since_prior,
        "consecutive_same_direction": consecutive,

        # Premium at horizons
        "premium_15m": horizon_ltps.get(15),
        "premium_30m": horizon_ltps.get(30),
        "premium_60m": horizon_ltps.get(60),
        "premium_eod": premium_eod,

        # Moves
        "move_15m_pts": move_15m,
        "move_30m_pts": move_30m,
        "move_60m_pts": move_60m,
        "move_eod_pts": move_eod,

        # Path (from hist bars if available, else None)
        "mfe_session_pts":            path_metrics.get("mfe_session_pts"),
        "mae_session_pts":            path_metrics.get("mae_session_pts"),
        "time_to_mfe_mins":           path_metrics.get("time_to_mfe_mins"),
        "mfe_to_close_giveback_pct":  path_metrics.get("mfe_to_close_giveback_pct"),
        "drawdown_before_profit_pts": path_metrics.get("drawdown_before_profit_pts"),
        "first_adverse_move_pts":     path_metrics.get("first_adverse_move_pts"),

        # Thresholds
        "captured_25pts":  captured_25,
        "captured_50pts":  captured_50,
        "captured_75pts":  captured_75,
        "captured_100pts": captured_100,

        # IV behaviour
        "iv_at_exit":            iv_eod,
        "iv_change_during_trade": iv_change,
        "iv_crushed":            iv_crushed,

        # Spot
        "spot_move_15m_pts": spot_move_15m,
        "spot_move_60m_pts": spot_move_60m,
        "direction_correct": direction_correct,

        # Classification
        "outcome_label": outcome_label,
        "failure_mode":  failure_mode,

        # SMDM reserved (null until Track 2)
        "smdm_squeeze_score":   None,
        "smdm_squeeze_alert":   None,
        "smdm_signal_suppressed": None,
        "smdm_pattern_flags":   None,
        "smdm_otm_bleed_pct":   None,
        "smdm_straddle_velocity": None,
        "smdm_otm_oi_velocity": None,

        # Squeeze riding reserved
        "was_squeeze_day":          None,
        "otm_premium_pre_squeeze":  None,
        "otm_premium_at_squeeze":   None,
        "squeeze_magnitude_pts":    None,

        # Provenance
        "data_source": "LIVE" if trade_date >= date.today() - timedelta(days=7) else "BACKFILL_CHAIN",
        "evaluation_version": "v1",
        "path_data_available": path_available,
    }

    return row


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def get_pending_signals(
    client: SupabaseClient,
    symbol: str | None = None,
    backfill: bool = False,
) -> list[dict]:
    """
    Fetch signal_snapshots rows that need outcome evaluation.
    Excludes DO_NOTHING. Excludes already-evaluated unless backfill=True.
    """
    if backfill:
        # All BUY signals
        rows = client.select(
            "signal_snapshots",
            filters={"action": "neq.DO_NOTHING"},
            order="ts",
            ascending=True,
        )
    else:
        # Only signals not yet in signal_premium_outcomes
        # Strategy: fetch all evaluated IDs, exclude them
        evaluated = client.select(
            "signal_premium_outcomes",
            columns="signal_snapshot_id,symbol",
        )
        evaluated_ids = {
            (r["signal_snapshot_id"], r["symbol"])
            for r in evaluated
        }

        all_signals = client.select(
            "signal_snapshots",
            filters={"action": "neq.DO_NOTHING"},
            order="ts",
            ascending=True,
        )
        rows = [
            r for r in all_signals
            if (r["id"], r["symbol"]) not in evaluated_ids
        ]

    if symbol:
        rows = [r for r in rows if r.get("symbol", "").upper() == symbol.upper()]

    # Only BUY_CE / BUY_PE
    rows = [r for r in rows if r.get("action") in ("BUY_CE", "BUY_PE")]

    return rows


def run(
    symbol: str | None = None,
    backfill: bool = False,
    dry_run: bool = False,
) -> None:
    client  = SupabaseClient()
    chain   = ChainLookup(client)
    hist    = HistBarLookup(client)

    pending = get_pending_signals(client, symbol, backfill)
    log.info(f"Pending signals to evaluate: {len(pending)}")

    evaluated = 0
    skipped   = 0
    failed    = 0

    for signal in pending:
        try:
            row = evaluate_signal(signal, chain, hist, client, dry_run)

            if row is None:
                skipped += 1
                continue

            if dry_run:
                log.info(f"  DRY RUN | signal={signal['id']} | "
                         f"entry={row.get('entry_premium')} | "
                         f"move_eod={row.get('move_eod_pts')} | "
                         f"outcome={row.get('outcome_label')}")
                evaluated += 1
                continue

            if backfill:
                client.upsert(
                    "signal_premium_outcomes",
                    row,
                    on_conflict="signal_snapshot_id,symbol",
                )
            else:
                client.insert("signal_premium_outcomes", row)

            evaluated += 1
            log.info(f"  Written | signal={signal['id']} | "
                     f"entry={row.get('entry_premium')} | "
                     f"move_eod={row.get('move_eod_pts')} | "
                     f"outcome={row.get('outcome_label')}")

        except Exception as exc:
            log.error(f"Signal {signal.get('id')}: error — {exc}", exc_info=True)
            failed += 1

    log.info("=" * 50)
    log.info(f"OUTCOME WRITER SUMMARY")
    log.info(f"  Evaluated : {evaluated}")
    log.info(f"  Skipped   : {skipped}  (no chain data at entry)")
    log.info(f"  Failed    : {failed}")
    log.info("=" * 50)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MERDIAN premium outcome writer"
    )
    parser.add_argument("--symbol", default=None, help="NIFTY or SENSEX only")
    parser.add_argument("--backfill", action="store_true",
                        help="Reprocess all signals (upsert)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute but do not write to Supabase")
    args = parser.parse_args()

    run(
        symbol=args.symbol,
        backfill=args.backfill,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
