from datetime import datetime, timezone
from core.supabase_client import SupabaseClient

MAX_SIGNAL_LAG_SECONDS = 420
MAX_STATE_LAG_SECONDS = 420
MAX_FEATURE_MISMATCH_SECONDS = 180


def _parse_ts(ts):
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def _seconds_between(a, b):
    if not a or not b:
        return None
    return abs((a - b).total_seconds())


def _get_latest_row(sb, table, symbol, order="ts.desc"):
    rows = sb.select(
        table=table,
        filters={"symbol": f"eq.{symbol}"},
        order=order,
        limit=1,
    )
    if not rows:
        return None
    return rows[0]


def inspect_symbol(symbol: str):
    sb = SupabaseClient()

    option_row = _get_latest_row(sb, "option_chain_snapshots", symbol)
    gamma_row = _get_latest_row(sb, "gamma_metrics", symbol)
    vol_row = _get_latest_row(sb, "volatility_snapshots", symbol)
    momentum_row = _get_latest_row(sb, "momentum_snapshots", symbol)
    state_row = _get_latest_row(sb, "market_state_snapshots", symbol)
    signal_row = _get_latest_row(sb, "signal_snapshots", symbol)

    now = datetime.now(timezone.utc)

    option_ts = _parse_ts(option_row["ts"]) if option_row else None
    gamma_ts = _parse_ts(gamma_row["ts"]) if gamma_row else None
    vol_ts = _parse_ts(vol_row["ts"]) if vol_row else None
    momentum_ts = _parse_ts(momentum_row["ts"]) if momentum_row else None
    state_ts = _parse_ts(state_row["ts"]) if state_row else None
    signal_ts = _parse_ts(signal_row["ts"]) if signal_row else None

    signal_lag = _seconds_between(now, signal_ts)
    state_lag = _seconds_between(now, state_ts)

    gamma_vs_chain = _seconds_between(gamma_ts, option_ts)
    vol_vs_gamma = _seconds_between(vol_ts, gamma_ts)
    momentum_vs_state = _seconds_between(momentum_ts, state_ts)
    signal_vs_state = _seconds_between(signal_ts, state_ts)

    problems = []

    if signal_lag is not None and signal_lag > MAX_SIGNAL_LAG_SECONDS:
        problems.append(f"Latest signal is stale by {signal_lag:.2f}s (> {MAX_SIGNAL_LAG_SECONDS}s)")

    if state_lag is not None and state_lag > MAX_STATE_LAG_SECONDS:
        problems.append(f"Latest market state is stale by {state_lag:.2f}s (> {MAX_STATE_LAG_SECONDS}s)")

    if gamma_vs_chain is not None and gamma_vs_chain > MAX_FEATURE_MISMATCH_SECONDS:
        problems.append(
            f"Timestamp mismatch too large for gamma vs option chain: {gamma_vs_chain:.2f}s (> {MAX_FEATURE_MISMATCH_SECONDS}s)"
        )

    if vol_vs_gamma is not None and vol_vs_gamma > MAX_FEATURE_MISMATCH_SECONDS:
        problems.append(
            f"Timestamp mismatch too large for volatility vs gamma: {vol_vs_gamma:.2f}s (> {MAX_FEATURE_MISMATCH_SECONDS}s)"
        )

    if momentum_vs_state is not None and momentum_vs_state > MAX_FEATURE_MISMATCH_SECONDS:
        problems.append(
            f"Timestamp mismatch too large for momentum vs market state: {momentum_vs_state:.2f}s (> {MAX_FEATURE_MISMATCH_SECONDS}s)"
        )

    if signal_vs_state is not None and signal_vs_state > MAX_FEATURE_MISMATCH_SECONDS:
        problems.append(
            f"Timestamp mismatch too large for signal vs market state: {signal_vs_state:.2f}s (> {MAX_FEATURE_MISMATCH_SECONDS}s)"
        )

    print("========================================================================")
    print(f"Gamma Engine - Signal Freshness Inspection - {symbol}")
    print("========================================================================")

    print(f"Now UTC:                 {now.isoformat()}")
    print("------------------------------------------------------------------------")

    print(f"Latest option chain ts:  {option_ts}")
    print(f"Latest gamma ts:         {gamma_ts}")
    print(f"Latest volatility ts:    {vol_ts}")
    print(f"Latest momentum ts:      {momentum_ts}")
    print(f"Latest market state ts:  {state_ts}")
    print(f"Latest signal ts:        {signal_ts}")

    print("------------------------------------------------------------------------")

    print(f"Signal lag vs now (s):   {signal_lag:.2f}" if signal_lag is not None else "Signal lag vs now (s):   None")
    print(f"State lag vs now (s):    {state_lag:.2f}" if state_lag is not None else "State lag vs now (s):    None")
    print(f"Gamma vs chain (s):      {gamma_vs_chain:.2f}" if gamma_vs_chain is not None else "Gamma vs chain (s):      None")
    print(f"Vol vs gamma (s):        {vol_vs_gamma:.2f}" if vol_vs_gamma is not None else "Vol vs gamma (s):        None")
    print(f"Momentum vs state (s):   {momentum_vs_state:.2f}" if momentum_vs_state is not None else "Momentum vs state (s):   None")
    print(f"Signal vs state (s):     {signal_vs_state:.2f}" if signal_vs_state is not None else "Signal vs state (s):     None")

    print("------------------------------------------------------------------------")

    if signal_row:
        print(f"Latest action:           {signal_row.get('action')}")
        print(f"Confidence score:        {signal_row.get('confidence_score')}")
        print(f"Trade allowed:           {signal_row.get('trade_allowed')}")

    if option_row:
        print(f"Latest option run_id:    {option_row.get('run_id')}")

    if gamma_row:
        print(f"Latest gamma run_id:     {gamma_row.get('run_id')}")

    if vol_row:
        print(f"Latest vol source_run_id:{vol_row.get('source_run_id')}")

    print("------------------------------------------------------------------------")

    if problems:
        print("STATUS: FAIL")
        print("Problems detected:")
        for p in problems:
            print(f"- {p}")
    else:
        print("STATUS: PASS")

    print("========================================================================")
    print()


def main():
    inspect_symbol("NIFTY")
    inspect_symbol("SENSEX")


if __name__ == "__main__":
    main()