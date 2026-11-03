"""Tape T1-db: the one definition of the sidecar tables (docs/tape/T1_db_plan.md section 1.1).

Column NAMES for the CSV-sourced tables are taken from the T1a / T1b tuples by import, never retyped. This module adds
only: renames (CSV name -> DB name), added columns, the provenance block, and a type for every DB column. The loader
builds rows from it; tests/test_tape_t1db.py asserts the migration SQL equals it.

Pre-registration v0.2 (sha256 71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800): tape-side and
chain-side relations are separate. Nothing here relates one to the other.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from merdian_compute.tape import chain_events, cycle, events, minute  # noqa: E402

PREREG_SHA = "71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800"
SOURCE = "tape_offline_v1"
WRITER = "services/tape_db/load_day.py"

PROVENANCE = (("run_id", "uuid"), ("code_sha", "text"), ("source", "text"), ("config_version", "text"),
              ("loaded_at", "timestamptz"))
PROVENANCE_NOT_NULL = ("run_id", "code_sha", "source", "loaded_at")


def _t(**kw):
    return kw


# Per CSV-sourced table: csv (file name), cols (the imported tuple), rename, added, types (DB name -> type),
# not_null, pk, unique (NULLS NOT DISTINCT), symbol_col.
TABLES = {
    "tape_minute": _t(
        csv="tape_minute.csv", src="out", cols=minute.COLS,
        rename={"day": "trading_day", "sym": "symbol", "token": "instrument_token", "minute": "minute_ist"},
        added=(),
        types={"trading_day": "date", "symbol": "text", "role": "text", "opt_type": "text", "strike": "numeric",
               "expiry": "date", "instrument_token": "bigint", "tradingsymbol": "text", "minute_ist": "timestamptz",
               "buy_qty": "bigint", "sell_qty": "bigint", "uncl_qty": "bigint", "gap_qty": "bigint",
               "trades": "bigint", "vwap": "double precision", "bid_qty_5": "bigint", "ask_qty_5": "bigint",
               "oi": "bigint", "oi_delta": "bigint", "exch_ts_max": "timestamptz"},
        not_null=("symbol", "trading_day", "instrument_token", "minute_ist", "role"),
        pk=("symbol", "trading_day", "instrument_token", "minute_ist"), unique=None),
    "tape_strike_cycle": _t(
        csv="tape_strike_cycle.csv", src="cyc", cols=cycle.CYCLE_COLS,
        rename={"token": "instrument_token", "T": "ts_ist", "first_seen_T": "first_seen_ts_ist"},
        added=("trading_day",),
        types={"trading_day": "date", "symbol": "text", "expiry": "date", "strike": "numeric", "leg": "text",
               "instrument_token": "bigint", "tradingsymbol": "text", "ts_ist": "timestamptz",
               "buy_5": "bigint", "sell_5": "bigint", "uncl_5": "bigint", "gap_5": "bigint", "trades_5": "bigint",
               "buy_15": "bigint", "sell_15": "bigint", "buy_30": "bigint", "sell_30": "bigint",
               "balance_5": "double precision", "balance_15": "double precision", "balance_30": "double precision",
               "resting_imb": "double precision", "classified_share_5": "double precision",
               "buy_cum": "bigint", "sell_cum": "bigint", "uncl_cum": "bigint", "gap_cum": "bigint",
               "oi_last": "bigint", "oi_delta_5": "bigint", "minutes_present_5": "integer",
               "first_seen_ts_ist": "timestamptz"},
        not_null=("symbol", "trading_day", "instrument_token", "ts_ist", "leg"),
        pk=("symbol", "trading_day", "instrument_token", "ts_ist"),
        unique=("symbol", "trading_day", "expiry", "strike", "leg", "ts_ist")),
    "tape_events": _t(
        csv="tape_events.csv", src="cyc", cols=events.EVENT_COLS,
        rename={"detail_json": "detail"},
        added=("trading_day",),
        types={"trading_day": "date", "symbol": "text", "expiry": "date", "strike": "numeric", "leg": "text",
               "kind": "text", "ts_ist": "timestamptz", "side": "text", "magnitude": "double precision",
               "detail": "jsonb"},
        not_null=("symbol", "trading_day", "leg", "kind", "ts_ist", "side"),
        pk=None, unique=("symbol", "trading_day", "expiry", "strike", "leg", "kind", "ts_ist", "side")),
    "tape_chain_events": _t(
        csv="chain_events.csv", src="chain", cols=chain_events.EVENT_COLS,
        rename={}, added=("trading_day",),
        types={"trading_day": "date", "symbol": "text", "expiry": "date", "kind": "text", "ts_ist": "timestamptz",
               "strike": "numeric", "prev_strike": "numeric", "prev_value": "double precision",
               "new_value": "double precision", "merged_n": "integer"},
        not_null=("symbol", "trading_day", "expiry", "kind", "ts_ist", "strike"),
        pk=("symbol", "trading_day", "expiry", "kind", "ts_ist", "strike"), unique=None),
    "tape_chain_runs": _t(
        csv="chain_runs.csv", src="chain", cols=chain_events.RUN_COLS,
        rename={"run_id": "chain_run_id"}, added=("trading_day",),
        types={"trading_day": "date", "symbol": "text", "expiry": "date", "ts_ist": "timestamptz",
               "chain_run_id": "text", "n_strikes": "integer", "leader_strike": "numeric", "call_wall": "numeric",
               "put_wall": "numeric", "net_sign": "smallint", "in_window": "boolean"},
        not_null=("symbol", "trading_day", "expiry", "ts_ist"),
        pk=("symbol", "trading_day", "expiry", "ts_ist"), unique=None),
}

# tape_daily_report is not CSV-sourced; every column and its source is in docs/tape/T1_db_plan.md section 1.1.
DAILY = _t(
    types={"symbol": "text", "trading_day": "date", "completeness_pct": "double precision",
           "gaps_gt_10s": "integer", "gaps_gt_60s": "integer", "packets": "bigint", "segments": "integer",
           "uploads_ok": "integer", "uploads_retried": "integer", "uploads_failed": "integer",
           "skew_median_s": "double precision", "connects": "integer", "reconnects": "integer",
           "disconnects": "integer", "watchdog_trips": "integer", "frame_errors": "integer", "g3_verdict": "text",
           "classified_share_early": "double precision", "classified_share_late": "double precision",
           "report": "jsonb", "g3": "jsonb"},
    not_null=("symbol", "trading_day"), pk=("symbol", "trading_day"), unique=None,
    owed=("completeness_pct", "connects", "watchdog_trips", "frame_errors"))

ORDER = ("tape_minute", "tape_strike_cycle", "tape_events", "tape_chain_runs", "tape_chain_events", "tape_daily_report")
TAPE_TABLES = frozenset(ORDER)


def db_columns(table):
    """Ordered DB columns (data columns, then provenance) for one table."""
    if table == "tape_daily_report":
        data = list(DAILY["types"])
    else:
        t = TABLES[table]
        data = list(t["added"]) + [t["rename"].get(c, c) for c in t["cols"]]
    return data + [p for p, _ in PROVENANCE]


def db_types(table):
    types = dict(DAILY["types"] if table == "tape_daily_report" else TABLES[table]["types"])
    types.update(dict(PROVENANCE))
    return types


def spec(table):
    return DAILY if table == "tape_daily_report" else TABLES[table]
