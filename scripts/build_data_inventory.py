#!/usr/bin/env python3
"""build_data_inventory.py -- measure, from the live database, which market-data
layers are computable for each symbol on each trading day, and write the result to
docs/registers/MERDIAN_Data_Inventory.md.

WHY THIS EXISTS
---------------
The extent of MERDIAN's option history has been re-derived from scratch at least a
dozen times across 70+ sessions, each time from whichever table that session's brief
happened to name, producing a different answer each time. S75 measured it correctly
(docs/research/data_inventory_2026-09-08.md) but that is a dated research file that
nothing points at and nothing regenerates. This script replaces re-derivation with a
re-run: the register has a fixed path, carries its own measurement date, and is
reproduced by running this file with no arguments.

ACCESS PATH
-----------
This box has no psql binary, no psycopg2/psycopg/asyncpg/pg8000/sqlalchemy, and no
Postgres password. The only route to the database is PostgREST as the service role,
using SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY read from .env inside this process.

CREDENTIAL DISCIPLINE
---------------------
  * Credentials are read into a module-local header dict. They are never printed,
    never logged, never placed in a query string, and never interpolated into any
    URL that is emitted to stdout or to the register.
  * Every HTTP call goes through _get(), which catches BaseException and re-raises
    a bare Probe carrying only a status code or an exception CLASS NAME, with
    `from None` so no chained traceback can render the frame holding the headers.
  * READ-ONLY. Only HTTP GET. This script never writes to the database and never
    calls an RPC.

METHOD RULES -- these are why the measurement is trustworthy. They are not optional.
------------------------------------------------------------------------------------
  1. count=exact always. `count=planned` on a not.is.null filter over an all-NULL
     column returns a planner floor of 1, which is not a row. Reporting that 1 would
     be a false positive. Where exact is impossible the cell says so; no planned
     figure is ever presented as a count.
  2. A 57014 / HTTP 500 is NEVER recorded as an absence. Any failing probe is
     retried, then decomposed to a finer scope, and only a REAL EMPTY LIST
     (HTTP 200 with a literal empty JSON array) counts as absence. Anything that
     never resolves is appended to UNRESOLVED. The script asserts UNRESOLVED is
     empty before it writes anything, and prints it either way.
  3. Every zero cell is an HTTP 200 with a literal empty array from a day-scoped
     limit=1 probe. Those confirmations are counted and the count is printed.
  4. Ranges are probed one month before each discovered minimum and one month after
     each discovered maximum, so a real edge outside the window appears rather than
     being excluded by construction.
  5. The relation list is discovered from the live catalog (the PostgREST OpenAPI
     document, generated from pg_catalog). It is never taken from
     merdian_reference.json, from any register, or from a hardcoded list.
  6. A relation that cannot produce a REAL EMPTY LIST cannot satisfy rule 3, and is
     excluded from the source set as UNMEASURABLE BY THIS METHOD -- by measurement,
     not by name and not by catalog category. Each source is probed on a window it
     certainly holds no rows in; a relation that must scan its whole extent to prove
     absence times out instead of returning []. Such a relation does not fail once,
     it fails once per empty day: resolve_presence would exhaust the 1/2/4/8 ladder
     on every one and append an UNRESOLVED entry, after the sweep has already run.
     The exclusion is recorded with its timings and does NOT block the write -- it is
     a measured property of the relation, stated. It does mean the register says
     NOTHING about that relation, neither presence nor absence.

A NOTE ON CALENDAR-DAY WINDOWS
------------------------------
Timestamp columns are filtered with a UTC calendar-day window [D, D+1). An IST
trading session (09:15-15:30 IST = 03:45-10:00 UTC) falls strictly inside one UTC
calendar day, and so does a session stored under the legacy IST-clock-labelled-UTC
convention (TD-029 / CLAUDE.md Rules 16 and 20, hours 09-15). Both conventions are
therefore contained by the same window and no session is split across two cells.

IDEMPOTENCE
-----------
Takes no arguments. NOT RESUMABLE -- an interrupted run re-measures from zero. There
is no checkpoint. This docstring previously claimed a date-keyed one; no such code
existed, and the claim was removed rather than implemented (S78, after a killed run
lost ~500 measured cells). Budget the full run -- 26,172 requests, 0:52:36 -- before
starting, and run it detached. The register carries one internally consistent
measurement date because the whole sweep happens in a single pass, not because any
state is carried between runs.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import requests
from dotenv import dotenv_values

# ---------------------------------------------------------------- configuration

ENV_PATH = "/home/ssm-user/meridian-engine/.env"
REPO = Path(__file__).resolve().parent.parent
OUT_PATH = REPO / "docs" / "registers" / "MERDIAN_Data_Inventory.md"
LOG_DIR = REPO / "logs"

SYMBOLS = ("NIFTY", "SENSEX")
PAD_DAYS = 31                 # method rule 4: probe a month beyond each discovered edge
WORKERS = 4                   # modest; these are reads against a shared production DB
RETRIES = 2                   # same-scope retries before decomposing to a finer scope
HTTP_TIMEOUT = 45
# Base backoff for the bounds ladder, doubled per attempt. Longer than the 0.6s used
# inside resolve_presence because the failure being waited out here is a statement
# timeout on an ordered scan, not a transient: retrying it immediately re-enters the
# same contention. Worst case per column-direction is RETRIES+1 attempts and 4.5s.
BOUNDS_BACKOFF = 1.5
# Method rule 6. A window no MERDIAN relation can hold rows in, used to ask each
# source whether it is CAPABLE of returning a real empty list at all.
ABSENCE_PROBE_DATE = "2099-01-01"
# Density is a supplementary number over cells already proven present, so its cost
# is bounded rather than retried to exhaustion. See sweep_density().
DENSITY_ATTEMPTS = 2
DENSITY_MAX_UNPROVEN = 200
# The breaker above trips on FAILURES. It does nothing about counts that succeed
# SLOWLY, which is the likelier overrun: count=exact is strictly heavier than
# limit=1 (it counts every matching row instead of stopping at the first), and a
# day of hist_option_bars_1m is six figures of rows. Without a clock the density
# phase has no upper bound at all. 39m of measured phases + this = under an hour.
DENSITY_TIME_BUDGET_S = 1200

# A relation is too large to enumerate row-by-row for the expiry-class analysis.
EXPIRY_ANALYSIS_MAX_ROWS = 200_000

# The last trusted measurement of this question, quoted as prior art for a cross-check
# and NEVER used as an input to anything measured here. Transcribed verbatim from
# docs/research/data_inventory_2026-09-08.md, section 6, table "Totals, 2025-04-01 to
# 2026-09-08". If that file is superseded, update this block and say so in the commit.
PRIOR = {
    "date":   "2026-09-08",
    "window": "2025-04-01..2026-09-08",
    "days":   {"NIFTY": 356, "SENSEX": 355},
    "now":    {"NIFTY": 299, "SENSEX": 299},
    "after":  {"NIFTY": 0,   "SENSEX": 0},
    "not":    {"NIFTY": 57,  "SENSEX": 56},
}

NUMERIC_FORMATS = {
    "numeric", "double precision", "real", "integer", "bigint", "smallint",
    "double", "float", "float4", "float8", "int2", "int4", "int8",
}

# Column-name classifiers. Every one of these is reproduced verbatim in the register
# so a reader can see exactly how a relation became a candidate.
#
# ANCHORING. Relation.match() uses re.search, NOT re.match. re.match anchors at
# position 0, which silently turned the two "_ANY" patterns into PREFIX tests:
# `atm_strike`, `n_strikes` and `ce_strike` never matched, so the single_strike kind
# was never assigned to anything and every such relation was mislabelled spot_only.
# The exact patterns all carry their own ^...$, so search and match are identical
# for them; only the _ANY patterns change behaviour.
RE_STRIKE_DIM = re.compile(r"^strike$")
RE_STRIKE_ANY = re.compile(r"(^|_)strikes?($|_)")
RE_GAMMA = re.compile(r"^(ce_|pe_)?gamma(_call|_put)?$")
RE_IV = re.compile(r"^(ce_|pe_)?(iv|atm_iv|atm_call_iv|atm_put_iv|implied_vol_atm)$")
RE_OI = re.compile(r"^(ce_|pe_)?(oi|oi_call|oi_put|open_interest|prev_close_oi)$")
RE_SPOT = re.compile(r"^spot(_close)?$")
RE_GREEK_ANY = re.compile(r"^(ce_|pe_)?(gamma|delta|theta|vega|rho)(_call|_put)?$")
RE_VOL_ANY = re.compile(r"(^iv$|^iv_|_iv$|implied_vol|^vega$|volatility)")
RE_PROVENANCE = re.compile(r"^(source|provenance|origin|written_by|producer|"
                           r"ingest_source|data_source|run_type|source_table)$")

# Ordered candidates for a relation's scoping column. discover_bounds() walks this
# list until one yields BOTH bounds. hist_option_greeks_1m.bar_ts returns 57014 on an
# ordered scan while its trade_date does not (S75 §3.0); with no fallback that
# relation -- the only gamma source for 2025-04..2026-03 -- drops out silently.
TIME_COL_PREFERENCE = ("ts", "bar_ts", "trade_date", "as_of_date", "for_session_date",
                       "session_date", "prev_close_ts", "created_at")
DATE_ONLY_COLS = {"trade_date", "as_of_date", "for_session_date", "session_date",
                  "expiry_date"}

# ------------------------------------------------------------------ credentials

_v = dotenv_values(ENV_PATH)
_URL = (_v.get("SUPABASE_URL") or "").rstrip("/")
_KEY = _v.get("SUPABASE_SERVICE_ROLE_KEY") or ""
if not _URL or not _KEY:
    print(f"FATAL: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in {ENV_PATH}",
          file=sys.stderr)
    raise SystemExit(2)
_H = {"apikey": _KEY, "Authorization": f"Bearer {_KEY}"}
del _v, _KEY


class Probe(Exception):
    """Carries a status code or an exception class name. Never a header, never a URL."""


_session_local = threading.local()


def _sess() -> requests.Session:
    s = getattr(_session_local, "s", None)
    if s is None:
        s = requests.Session()
        _session_local.s = s
    return s


def _get(path, params=None, prefer=None, timeout=HTTP_TIMEOUT):
    """Single choke point for every request. Nothing inside can raise outward."""
    h = dict(_H)
    if prefer:
        h["Prefer"] = prefer
    try:
        r = _sess().get(f"{_URL}/rest/v1/{path}", headers=h, params=params, timeout=timeout)
    except BaseException as exc:            # noqa: BLE001 - deliberate: swallow the frame
        raise Probe(f"transport {type(exc).__name__}") from None
    if r.status_code not in (200, 206):
        raise Probe(f"HTTP {r.status_code}") from None
    return r


# ------------------------------------------------------------------- run state

LOG_FH = None
_log_lock = threading.Lock()
_stat_lock = threading.Lock()

UNRESOLVED: list[dict] = []        # method rule 2 -- must be empty before any write
EMPTY_LIST_CONFIRMATIONS = 0       # method rule 3 -- counted, then printed
REQUESTS_MADE = 0

# Every source that leaves the layer sweep without being measured, and why. A source
# can exit that loop for two very different reasons, and conflating them is how the
# first live run produced a register-shaped hole: an EMPTY relation is a measurement
# (every scoping column returned a real empty list, so it can serve no day), whereas
# an UNMEASURED one is an absence of measurement (its bounds never resolved, so its
# days were never probed and its cells read as absent when nothing ever looked).
# Both are logged loudly and both are rendered in section 4. Neither is a bare
# `continue`.
DROPPED_SOURCES: list[dict] = []


def log(msg):
    line = f"[{dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S')}] {msg}"
    with _log_lock:
        print(line, flush=True)
        if LOG_FH:
            LOG_FH.write(line + "\n")
            LOG_FH.flush()


def note_unresolved(what, scope, reason):
    with _stat_lock:
        UNRESOLVED.append({"what": what, "scope": scope, "reason": reason})
    log(f"  UNRESOLVED  {what}  scope={scope}  reason={reason}")


def note_dropped(src, kind, reason):
    """Record a source leaving the layer sweep. `kind` is 'empty' or 'unmeasured'."""
    with _stat_lock:
        DROPPED_SOURCES.append({"name": src.name, "kind": kind, "reason": reason,
                                "layers": sorted(src.layers)})
    label = "EMPTY   " if kind == "empty" else "DROPPED "
    log(f"  {label} {src.name}  layers={','.join(sorted(src.layers)) or '-'}  {reason}")


def bump_requests(n=1):
    global REQUESTS_MADE
    with _stat_lock:
        REQUESTS_MADE += n


def bump_empty():
    global EMPTY_LIST_CONFIRMATIONS
    with _stat_lock:
        EMPTY_LIST_CONFIRMATIONS += 1


# ------------------------------------------------------------- probe primitives

def rows_exist(relation, params, timeout=HTTP_TIMEOUT):
    """True if >=1 row; False ONLY on a real empty list. Raises Probe otherwise.

    A False from this function is always an HTTP 200 carrying a literal empty JSON
    array -- never an error, never a planner estimate. That is method rule 3.
    """
    bump_requests()
    r = _get(relation, params + [("limit", "1")], timeout=timeout)
    data = r.json()
    if not isinstance(data, list):
        raise Probe("non-list body")
    if data:
        return True
    bump_empty()
    return False


def exact_count(relation, params, timeout=HTTP_TIMEOUT):
    """count=exact only. Returns int, or raises Probe. Never falls back to planned."""
    bump_requests()
    r = _get(relation, params + [("select", "*"), ("limit", "0")],
             prefer="count=exact", timeout=timeout)
    tail = (r.headers.get("Content-Range") or "").split("/")[-1]
    if not tail.isdigit():
        raise Probe("count=exact returned no integer")
    return int(tail)


def day_windows(day: dt.date, parts: int, time_col: str, date_only: bool):
    """Split one calendar day into `parts` filter windows on `time_col`."""
    if date_only:
        # A date column has no sub-day structure; it cannot be decomposed further.
        return [[(time_col, f"eq.{day.isoformat()}")]] if parts == 1 else None
    if parts == 1:
        nxt = day + dt.timedelta(days=1)
        return [[(time_col, f"gte.{day.isoformat()}"), (time_col, f"lt.{nxt.isoformat()}")]]
    out, step = [], 24 // parts
    for i in range(parts):
        lo = dt.datetime.combine(day, dt.time(i * step)).isoformat()
        hi_h = (i + 1) * step
        hi = (dt.datetime.combine(day, dt.time(0)) + dt.timedelta(hours=hi_h)).isoformat()
        out.append([(time_col, f"gte.{lo}"), (time_col, f"lt.{hi}")])
    return out


def resolve_presence(relation, base_params, day, time_col, date_only, what):
    """Answer 'does any row match, on this day' with escalation.

    Ladder: same scope RETRIES times -> halves -> quarters -> eighths. Only a real
    empty list on EVERY sub-window counts as absence. Exhausting the ladder appends
    to UNRESOLVED and returns None, which the caller must not treat as False.
    """
    for parts in (1, 2, 4, 8):
        wins = day_windows(day, parts, time_col, date_only)
        if wins is None:
            break
        last = None
        try:
            any_hit = False
            for w in wins:
                ok = None
                for _ in range(RETRIES + 1):
                    try:
                        ok = rows_exist(relation, base_params + w)
                        break
                    except Probe as e:
                        last = str(e)
                        time.sleep(0.6)
                if ok is None:
                    raise Probe(last or "exhausted retries")
                if ok:
                    any_hit = True
                    break
            return any_hit
        except Probe as e:
            last = str(e)
            continue
    note_unresolved(what, f"{relation} {day.isoformat()}", last or "unknown")
    return None


# --------------------------------------------------------------------- catalog

@dataclass
class Relation:
    name: str
    cols: dict                      # col -> {"type":..., "format":...}

    def numeric(self, col):
        meta = self.cols.get(col) or {}
        return (meta.get("format") or meta.get("type") or "") in NUMERIC_FORMATS

    def match(self, rx, numeric_only=True):
        # re.search, deliberately: re.match anchors at position 0 and would turn the
        # "_ANY" patterns into prefix tests. See the ANCHORING note above.
        return sorted(c for c in self.cols
                      if rx.search(c) and (not numeric_only or self.numeric(c)))

    @property
    def has_strike_dim(self):
        return bool(self.match(RE_STRIKE_DIM))

    @property
    def gamma_cols(self):
        return self.match(RE_GAMMA)

    @property
    def iv_cols(self):
        return self.match(RE_IV)

    @property
    def oi_cols(self):
        return self.match(RE_OI)

    @property
    def spot_cols(self):
        return self.match(RE_SPOT)

    @property
    def provenance_cols(self):
        return self.match(RE_PROVENANCE, numeric_only=False)

    @property
    def sym_mode(self):
        if "symbol" in self.cols:
            return "symbol"
        if "instrument_id" in self.cols:
            return "instrument_id"
        return None

    @property
    def time_col(self):
        for c in TIME_COL_PREFERENCE:
            if c in self.cols:
                return c
        return None

    @property
    def time_cols(self):
        """Every usable scoping column, in preference order, for bounds fallback."""
        return [c for c in TIME_COL_PREFERENCE if c in self.cols]


def fetch_catalog():
    log("catalog: GET /rest/v1/  (OpenAPI, generated from the live pg_catalog)")
    bump_requests()
    doc = _get("", timeout=120).json()
    defs = doc.get("definitions", {})
    rels = {}
    for name, d in defs.items():
        props = d.get("properties", {}) or {}
        rels[name] = Relation(name, {c: (m or {}) for c, m in props.items()})
    log(f"catalog: {len(rels)} relations in schema public")
    return rels


# ------------------------------------------------------------------ candidates

@dataclass
class Source:
    rel: Relation
    kind: str                       # 'per_strike' | 'single_strike' | 'spot_only'
    time_col: str
    date_only: bool
    sym_mode: str
    tmin: str | None = None
    tmax: str | None = None
    bounds_col: str | None = None   # the column that actually yielded the bounds
    bounds_note: str = ""           # why, when it was not the first choice
    is_empty: bool = False          # relation holds no rows -- a real answer, not a failure
    layers: dict = field(default_factory=dict)   # layer -> [cols]

    @property
    def name(self):
        return self.rel.name


def is_candidate(r: Relation):
    """Brief: every relation carrying a strike dimension OR a volatility/greek/oi column."""
    if r.match(RE_STRIKE_ANY, numeric_only=False):
        return True
    if r.match(RE_GREEK_ANY):
        return True
    if r.match(RE_VOL_ANY, numeric_only=False):
        return True
    if r.match(RE_OI):
        return True
    return False


def build_sources(rels):
    """Sources that can actually SERVE a layer for a (symbol, day) cell."""
    out = []
    for r in rels.values():
        sym, tcol = r.sym_mode, r.time_col
        if not sym or not tcol:
            continue
        layers = {}
        if r.has_strike_dim:
            kind = "per_strike"
        elif r.match(RE_STRIKE_ANY, numeric_only=False):
            kind = "single_strike"
        else:
            kind = "spot_only"

        # gamma / iv / oi are MEASURED wherever a strike of any kind carries them,
        # per_strike and single_strike alike. classify() then admits only per_strike
        # sources to the verdict (one ATM strike is not a chain), and the register
        # reports the single-strike availability separately.
        #
        # Assigning these only under `has_strike_dim` -- as this did -- left the
        # single-strike layers never measured, which made classify()'s gamma_ss /
        # iv_ss / oi_ss fields permanently empty. They would have rendered as "no ATM
        # gamma on any day" when the truth was that nothing ever looked. A zero that
        # was never measured is the defect this register exists to prevent.
        #
        # spot_only relations are excluded: an aggregate gamma with no strike
        # dimension at all is not a per-strike quantity under any reading.
        if kind in ("per_strike", "single_strike"):
            if r.gamma_cols:
                layers["gamma"] = r.gamma_cols
            if r.iv_cols:
                layers["iv"] = r.iv_cols
            if r.oi_cols:
                layers["oi"] = r.oi_cols

        if r.spot_cols:
            layers["spot"] = r.spot_cols
        elif kind == "spot_only":
            close_like = [c for c in ("close", "ltp") if c in r.cols and r.numeric(c)]
            if close_like and "option_type" not in r.cols:
                layers["spot"] = close_like
        if not layers:
            continue
        out.append(Source(r, kind, tcol, tcol in DATE_ONLY_COLS, sym, layers=layers))
    return sorted(out, key=lambda s: s.name)


def sym_filter(src: Source, symbol, instrument_ids):
    if src.sym_mode == "symbol":
        return [("symbol", f"eq.{symbol}")]
    iid = instrument_ids.get(symbol)
    return [("instrument_id", f"eq.{iid}")] if iid else None


def probe_absence(src: Source):
    """Can this source produce a REAL EMPTY LIST? Method rule 6.

    Rule 3 requires every zero cell to be an HTTP 200 carrying a literal empty array.
    A relation that cannot produce one, on a scope it genuinely holds no rows in,
    cannot satisfy that rule -- and the failure is not local. resolve_presence would
    exhaust the 1/2/4/8 ladder on EVERY empty day and append one UNRESOLVED entry per
    day across the whole padded window. Such a relation does not fail once; it fails
    once per day, after the sweep has already run.

    Measured 2026-09-13: v_oi_prev_close_snapshots and latest_option_chain_run both
    time out here (HTTP 500 at ~8.3s) while the other 31 sources answer in 0.3-3.9s.
    Both are cheap when a row matches and can exit early, and time out when they must
    scan their whole extent to prove that nothing matches. Note that
    latest_option_chain_snapshots ANSWERS in 0.4s while latest_option_chain_run does
    not: this is a measured property of a relation, not a property of views.

    Returns (verdict, evidence):
      "CAN"          -- some time column returned a real empty list
      "CANNOT"       -- every time column failed; UNMEASURABLE BY THIS METHOD
      "INCONCLUSIVE" -- the probe window unexpectedly held rows, so this test cannot
                        speak for that column. Treated as CAN by the caller:
                        exclusion is the destructive act, and it is not taken on an
                        inconclusive measurement.
    """
    notes, saw_rows = [], False
    for tcol in src.rel.time_cols:
        if tcol in DATE_ONLY_COLS:
            params = [("select", tcol), (tcol, f"eq.{ABSENCE_PROBE_DATE}")]
        else:
            nxt = (dt.date.fromisoformat(ABSENCE_PROBE_DATE)
                   + dt.timedelta(days=1)).isoformat()
            params = [("select", tcol), (tcol, f"gte.{ABSENCE_PROBE_DATE}"),
                      (tcol, f"lt.{nxt}")]
        outcome = None
        for attempt in range(RETRIES + 1):
            t0 = time.monotonic()
            try:
                bump_requests()
                rows = _get(src.name, params + [("limit", "1")]).json()
            except Probe as e:
                notes.append(f"`{tcol}`: {e} after {time.monotonic() - t0:.1f}s")
                if attempt < RETRIES:
                    time.sleep(BOUNDS_BACKOFF * (2 ** attempt))
                continue
            el = time.monotonic() - t0
            if isinstance(rows, list) and not rows:
                bump_empty()
                return "CAN", f"`{tcol}` returned a real empty list in {el:.1f}s"
            outcome = "rows"
            notes.append(f"`{tcol}` unexpectedly held rows in the probe window")
            break
        if outcome == "rows":
            saw_rows = True
    if saw_rows:
        return "INCONCLUSIVE", "; ".join(notes)
    return "CANNOT", "; ".join(notes) or "no usable time column"


def discover_bounds(src: Source):
    """True min/max of the source's scoping column, walking the preference list.

    Three outcomes, kept distinct because conflating them loses relations silently:

      * BOUNDED  -- a column yielded both edges. `bounds_col` records which one, and
        `bounds_note` records the failures walked past to reach it. Both are rendered
        in section 4, so the claim that the column is reported is checkable.
      * EMPTY    -- every column probed returned a REAL EMPTY LIST. The relation holds
        no rows. That is a measurement, not a failure, so it is NOT unresolved.
      * FAILED   -- a column raised and no later column bounded the relation. Recorded
        in UNRESOLVED, which blocks the write.

    An ordered scan can exceed the statement timeout on a column with no usable index
    at the relation's size: hist_option_greeks_1m.bar_ts does this while its
    trade_date does not. A column that returns no rows must also keep the walk going,
    or a relation with an empty `ts` and a populated `trade_date` drops out with
    bounds that look identical to a failure.

    EACH ORDERED SCAN IS RETRIED. Without this, one transient 500 condemns a column,
    and if every column is condemned the relation leaves the run entirely -- not just
    from section 4, but from the layer sweep, because source_window() then returns
    (None, None). The first live run lost historical_option_chain_snapshots that way,
    taking 2026-03-16..2026-06-03 out of the measurement with no cell marked absent.
    A single attempt is not a measurement of a relation's bounds; it is a sample of
    the database's mood.
    """
    failures, empties = [], []
    for tcol in src.rel.time_cols:
        lo = hi = None
        failed = False
        for direction in ("asc", "desc"):
            rows, last = None, None
            for attempt in range(RETRIES + 1):
                try:
                    bump_requests()
                    r = _get(src.name, [("select", tcol), ("order", f"{tcol}.{direction}"),
                                        ("limit", "1")])
                    body = r.json()
                    if not isinstance(body, list):
                        raise Probe("non-list body") from None
                    rows = body
                    break
                except Probe as e:
                    last = str(e)
                    if attempt < RETRIES:
                        time.sleep(BOUNDS_BACKOFF * (2 ** attempt))
            if rows is None:
                failures.append(f"`{tcol}`.{direction}: {last} "
                                f"(unresolved after {RETRIES + 1} attempts)")
                failed = True
                break
            if not rows:
                bump_empty()
            val = rows[0][tcol] if rows else None
            if direction == "asc":
                lo = val
            else:
                hi = val
        if failed:
            continue
        if lo is None or hi is None:
            empties.append(tcol)         # real empty list -- keep walking
            continue
        src.time_col, src.date_only = tcol, tcol in DATE_ONLY_COLS
        src.tmin, src.tmax, src.bounds_col = lo, hi, tcol
        if failures:
            src.bounds_note = f"fell back to `{tcol}` after " + "; ".join(failures)
        return src

    if empties and not failures:
        src.is_empty = True
        src.bounds_col = empties[0]
        src.bounds_note = ("relation holds no rows; probed "
                           + ", ".join(f"`{c}`" for c in empties)
                           + " and each returned a real empty list")
        return src

    src.tmin = src.tmax = None
    src.bounds_note = "; ".join(failures) or "no usable time column"
    note_unresolved(f"bounds({src.name})", "all time columns", src.bounds_note)
    return src


# ----------------------------------------------------------------- the sweeps

def weekdays(lo: dt.date, hi: dt.date):
    d, out = lo, []
    while d <= hi:
        if d.weekday() < 5:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def sweep_trading_days(rels, instrument_ids, lo, hi):
    """Denominator: a day is a trading day for a symbol if hist_spot_bars_1m has a row.

    This is the only relation spanning the full window for both symbols. Its limits
    are stated in the register's final section rather than papered over.
    """
    rel = rels["hist_spot_bars_1m"]
    days = weekdays(lo, hi)
    log(f"denominator: probing {len(days)} weekdays x {len(SYMBOLS)} symbols "
        f"against hist_spot_bars_1m")
    result = {s: set() for s in SYMBOLS}

    def one(args):
        sym, day = args
        iid = instrument_ids.get(sym)
        base = [("select", "trade_date"), ("instrument_id", f"eq.{iid}")]
        got = resolve_presence("hist_spot_bars_1m", base, day, "trade_date", True,
                               f"trading_day({sym})")
        return sym, day, got

    jobs = [(s, d) for s in SYMBOLS for d in days]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for i, (sym, day, got) in enumerate(ex.map(one, jobs), 1):
            if got:
                result[sym].add(day)
            if i % 200 == 0:
                log(f"  denominator {i}/{len(jobs)}")
    for s in SYMBOLS:
        log(f"  {s}: {len(result[s])} trading days")
    return result


def sweep_layers(sources, instrument_ids, trading_days, global_lo, global_hi):
    """For each source x symbol x day: which of gamma / iv / oi / spot are present.

    An existence probe runs first. When a day has no rows at all, every layer on that
    source is absent for that day and the per-layer probes are skipped -- that is an
    inference from a real empty list, not from an error.
    """
    # (sym, day) -> layer -> {relation: kind}. The kind is carried because a
    # single-strike relation's atm_iv must NOT be allowed to make a day computable:
    # one ATM strike is not a chain.
    avail = defaultdict(lambda: defaultdict(dict))
    jobs = []
    for src in sources:
        if src.is_empty:
            note_dropped(src, "empty",
                         "relation holds no rows; it can serve no day, so no cell is "
                         "missing on its account")
            continue
        lo, hi = source_window(src, global_lo, global_hi)
        if lo is None:
            # Two distinct reasons, and the second one is NOT otherwise recorded.
            if not src.tmin or not src.tmax:
                why = src.bounds_note or "no usable time column"
                reason = f"bounds never resolved ({why}); its days were never probed"
            else:
                # Bounds came back, but not as dates. discover_bounds() succeeded, so
                # nothing has been appended to UNRESOLVED and without this the source
                # would vanish with the run still exiting 0. Method rule 2: a scope
                # that never resolved is unresolved, whatever resolved it.
                reason = (f"bounds resolved to tmin={src.tmin!r} tmax={src.tmax!r}, "
                          "which do not parse as dates; its days were never probed")
                note_unresolved(f"window({src.name})", "source_window", reason)
            note_dropped(src, "unmeasured", reason)
            continue
        for sym in SYMBOLS:
            sf = sym_filter(src, sym, instrument_ids)
            if sf is None:
                continue
            for day in weekdays(lo, hi):
                jobs.append((src, sym, day, sf))
    log(f"layers: {len(jobs)} (source x symbol x day) cells across "
        f"{len(sources)} sources")

    def one(job):
        src, sym, day, sf = job
        found = set()
        exists = resolve_presence(src.name, [("select", src.time_col)] + sf, day,
                                  src.time_col, src.date_only, f"exists({src.name},{sym})")
        if exists is None or exists is False:
            return sym, day, src, found
        for layer, cols in src.layers.items():
            for col in cols:
                got = resolve_presence(src.name, [("select", col), (col, "not.is.null")] + sf,
                                       day, src.time_col, src.date_only,
                                       f"{layer}({src.name},{sym})")
                if got:
                    found.add(layer)
                    break
        return sym, day, src, found

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for sym, day, src, found in ex.map(one, jobs):
            for layer in found:
                avail[(sym, day)][layer][src.name] = src.kind
            done += 1
            if done % 500 == 0:
                log(f"  layers {done}/{len(jobs)}  requests={REQUESTS_MADE}")
    return avail


def eq_literal(v):
    """Render a sampled value as a PostgREST `eq.` operand.

    Floats reach us through JSON, so an integral strike arrives as 24000.0 and
    str() would emit `eq.24000.0`. That is a different literal from the 24000 the
    column renders, and a probe that misses for that reason is indistinguishable
    from genuinely absent correspondence -- it would read as a broken join rather
    than a broken query.
    """
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    return str(v)


def join_key(a: Source, b: Source):
    """The column set on which two per-strike relations could be joined row-to-row.

    Returns None unless BOTH carry every element: an instrument identifier, a
    TIMESTAMP, an expiry, a strike and an option type. Anything less is not a row
    correspondence -- it is an aggregation, and joining on it would silently pair a
    gamma from one contract with an OI from another.

    Two constraints that are easy to get wrong:

    * The key's time column is chosen from the columns the two relations SHARE, not
      from either source's `time_col`. `time_col` is the scoping column chosen for
      day windows and it moves when discover_bounds() falls back -- greeks scopes on
      `trade_date` because its `bar_ts` cannot be ordered, while bars scopes on
      `bar_ts`. Comparing those two fields would reject exactly the greeks/bars pair
      that the 2025-04..2026-03 window depends on, and the whole year would report
      NOT COMPUTABLE for a reason that has nothing to do with the data.
    * A date-only column is refused as the join time. Joining on `trade_date` pairs
      every contract-minute of one relation with every contract-minute of the other
      across a whole session, which is a cross product, not a correspondence.
    """
    if a.kind != "per_strike" or b.kind != "per_strike":
        return None
    if a.sym_mode != b.sym_mode:
        return None
    shared_ts = [c for c in TIME_COL_PREFERENCE
                 if c in a.rel.cols and c in b.rel.cols and c not in DATE_ONLY_COLS]
    if not shared_ts:
        return None
    key = [a.sym_mode, shared_ts[0], "expiry_date", "strike", "option_type"]
    if all(c in a.rel.cols and c in b.rel.cols for c in key):
        return key
    return None


def measure_key_correspondence(a: Source, b: Source, key, symbol, days,
                               instrument_ids, sample_days=3, sample_rows=20):
    """Sample real key tuples from `a` and probe `b` for the same tuple.

    This is a MEASUREMENT, not an assumption. Two relations sharing five column
    names prove nothing about whether a given contract-minute in one exists in the
    other. Nothing downstream is allowed to join a pair whose correspondence has not
    been measured here, and a pair that does not reach a perfect hit rate on the
    sample is reported with its rate and NOT used.
    """
    sfa = sym_filter(a, symbol, instrument_ids)
    sfb = sym_filter(b, symbol, instrument_ids)
    if sfa is None or sfb is None or not key:
        return None
    hits = total = errors = skipped_null = 0
    probed_days = []
    for day in days[:sample_days]:
        win = day_windows(day, 1, a.time_col, a.date_only)[0]
        try:
            bump_requests()
            r = _get(a.name, [("select", ",".join(key))] + sfa + win
                     + [("limit", str(sample_rows))])
            rows = r.json()
        except Probe:
            errors += 1
            continue
        if not rows:
            bump_empty()
            continue
        probed_days.append(day.isoformat())
        for row in rows:
            flt, usable = [], True
            for c in key:
                v = row.get(c)
                if v is None:
                    usable = False
                    break
                flt.append((c, f"eq.{eq_literal(v)}"))
            if not usable:
                skipped_null += 1
                continue
            total += 1
            probe = None
            for _ in range(RETRIES + 1):
                try:
                    probe = rows_exist(b.name, [("select", key[0])] + flt)
                    break
                except Probe:
                    time.sleep(0.4)
            if probe is None:
                # A failed check is NOT removed from the denominator. Subtracting it
                # would let 10 hits and 10 timeouts report 100% and HOLDS -- a 57014
                # counted as corroboration, which is method rule 2 inverted.
                errors += 1
            elif probe:
                hits += 1
    if total == 0:
        return None
    return {"a": a.name, "b": b.name, "symbol": symbol, "key": key,
            "hits": hits, "sampled": total, "errors": errors,
            "skipped_null": skipped_null, "rate": hits / total,
            "days": probed_days,
            # A pair qualifies only on a perfect hit rate with NO unresolved probe.
            "holds": (errors == 0 and hits == total)}


def sweep_correspondence(sources, avail, instrument_ids):
    """Measure correspondence for every pair that could supply gamma-plus-OI by join.

    A pair is only considered when, on at least one measured day, one side actually
    carried gamma (or iv) and the other actually carried OI -- so this never probes
    combinations the data does not present.
    """
    per_strike = [s for s in sources if s.kind == "per_strike" and not s.is_empty]
    want = {}
    for (sym, day), cell in avail.items():
        gs = {r for r, k in cell.get("gamma", {}).items() if k == "per_strike"}
        ivs = {r for r, k in cell.get("iv", {}).items() if k == "per_strike"}
        os_ = {r for r, k in cell.get("oi", {}).items() if k == "per_strike"}
        for left in (gs | ivs):
            for right in os_:
                if left != right:
                    want.setdefault((left, right, sym), []).append(day)
    log(f"correspondence: {len(want)} (gamma-side, oi-side, symbol) pairs present in data")
    out = {}
    by_name = {s.name: s for s in per_strike}
    for (ln, rn, sym), days in sorted(want.items()):
        a, b = by_name.get(ln), by_name.get(rn)
        if not a or not b:
            continue
        key = join_key(a, b)
        if key is None:
            out[(ln, rn, sym)] = {"a": ln, "b": rn, "symbol": sym, "key": None,
                                  "holds": False, "reason": "no shared row-level key"}
            continue
        m = measure_key_correspondence(a, b, key, sym, sorted(days), instrument_ids)
        if m is None:
            out[(ln, rn, sym)] = {"a": ln, "b": rn, "symbol": sym, "key": key,
                                  "holds": False, "reason": "no sampleable rows"}
        else:
            out[(ln, rn, sym)] = m
            log(f"  {ln} -> {rn} [{sym}]: {m['hits']}/{m['sampled']} "
                f"({m['rate']:.1%}) errors={m['errors']} "
                f"{'HOLDS' if m['holds'] else 'DOES NOT HOLD'}")
    return out


def source_window(src: Source, global_lo, global_hi):
    """Method rule 4: one month either side of the discovered bounds."""
    if not src.tmin or not src.tmax:
        return None, None
    try:
        lo = dt.date.fromisoformat(str(src.tmin)[:10]) - dt.timedelta(days=PAD_DAYS)
        hi = dt.date.fromisoformat(str(src.tmax)[:10]) + dt.timedelta(days=PAD_DAYS)
    except ValueError:
        return None, None
    return max(lo, global_lo), min(hi, global_hi)


def classify(avail, trading_days, correspondence):
    """Two verdicts per cell, because the answer depends on whether a join is allowed.

      same_relation -- gamma and OI carried by ONE relation, in the same row.
      joined        -- gamma on one per-strike relation, OI on another, where the
                       row-level key correspondence between that ordered pair was
                       MEASURED to hold in sweep_correspondence().

    The distinction is load-bearing, not cosmetic. For 2025-04..2026-03 the gamma
    lives in hist_option_greeks_1m and the OI in hist_option_bars_1m, and NEITHER
    relation carries both -- so same_relation reports NOT COMPUTABLE for that whole
    window while joined reports it computable. Reporting only same_relation would
    invert the headline; reporting only joined would hide that the day depends on a
    join holding. Both are rendered.

    Within each verdict:
      NOW              -- per-strike gamma and OI available, plus a spot.
      AFTER DERIVATION -- no gamma, but per-strike iv and OI, so Black-Scholes can
                          supply the gamma. Requires a spot too.
      NOT COMPUTABLE   -- neither.
    """
    verdicts = {}
    holds = {(c["a"], c["b"], c["symbol"]) for c in correspondence.values()
             if c.get("holds")}
    for sym in SYMBOLS:
        for day in sorted(trading_days[sym]):
            cell = avail.get((sym, day), {})

            # Only a per_strike relation can serve gamma / iv / oi for a GEX. A
            # single_strike relation holds one distinguished strike (atm_strike,
            # ce_strike) and its atm_iv is not a chain; counting it would promote
            # days that cannot actually be computed. Spot accepts any kind.
            def ps(layer):
                return {r for r, k in cell.get(layer, {}).items() if k == "per_strike"}

            g, iv, oi = ps("gamma"), ps("iv"), ps("oi")
            spot = set(cell.get("spot", {}))

            # same_relation: one relation carries gamma AND oi in the same row.
            same_now = sorted(g & oi)
            same_later = sorted((iv & oi) - set(same_now))

            # joined: gamma on one relation, oi on another, where the row-level key
            # correspondence between that ordered pair was MEASURED to hold.
            join_now = sorted({f"{a}+{b}" for a in g for b in oi
                               if a != b and (a, b, sym) in holds})
            join_later = sorted({f"{a}+{b}" for a in iv for b in oi
                                 if a != b and (a, b, sym) in holds})

            def verdict(now_srcs, later_srcs):
                if now_srcs and spot:
                    return "COMPUTABLE NOW", now_srcs
                if later_srcs and spot:
                    return "COMPUTABLE AFTER DERIVATION", later_srcs
                return "NOT COMPUTABLE", []

            v_same, s_same = verdict(same_now, same_later)
            v_join, s_join = verdict(same_now + join_now, same_later + join_later)

            verdicts[(sym, day)] = {
                "verdict": v_join, "sources": s_join,
                "verdict_same": v_same, "sources_same": s_same,
                "gamma": sorted(g), "iv": sorted(iv), "oi": sorted(oi),
                "spot": sorted(spot),
                "gamma_ss": sorted(set(cell.get("gamma", {})) - g),
                "iv_ss": sorted(set(cell.get("iv", {})) - iv),
                "oi_ss": sorted(set(cell.get("oi", {})) - oi),
            }
    return verdicts


def sweep_density(avail, sources, instrument_ids):
    """How MUCH, not just whether. Row count per (symbol, day, relation).

    Counted per RELATION-day, not per layer-day: gamma, iv and oi on one relation
    live in the same rows, so counting once per relation is the same number three
    times otherwise. Only cells the layer sweep already found PRESENT are counted --
    this adds no new presence probe and asks no question that was not already
    answered.

    A failed count is NOT an unresolved presence probe and MUST NOT be treated as
    one. The layer sweep already established that rows exist on that day; a
    count=exact that times out leaves us not knowing HOW MANY, which is a missing
    number, not a missing fact. Recording it in UNRESOLVED would block the write
    over a supplementary measurement and would also state something false -- that
    presence is in doubt. It is reported as an unproven count instead, and the
    tally is printed and rendered.
    """
    by_name = {s.name: s for s in sources}
    jobs = []
    for (sym, day), cell in avail.items():
        rels_here = set()
        for layer_map in cell.values():
            rels_here.update(layer_map)
        for rn in rels_here:
            src = by_name.get(rn)
            if src:
                jobs.append((sym, day, src))
    log(f"density: count=exact on {len(jobs)} (symbol, day, relation) cells already "
        f"measured present")

    # Two attempts, not RETRIES+1, and a circuit breaker. count=exact on a day of
    # hist_option_bars_1m counts six figures of rows and can exceed the statement
    # timeout; at 8s per failed attempt an unbounded ladder over thousands of cells
    # is a multi-hour tail on a SUPPLEMENTARY number. Bounding it is what keeps this
    # register re-runnable, which is the property the whole file is for. If counts
    # are failing systematically the breaker trips, the remaining cells are skipped,
    # and the register says so rather than silently costing an hour.
    state = {"unproven": 0, "skipped": 0, "tripped": False, "expired": False}
    lk = threading.Lock()
    deadline = time.monotonic() + DENSITY_TIME_BUDGET_S

    def one(job):
        sym, day, src = job
        if not state["expired"] and time.monotonic() > deadline:
            with lk:
                if not state["expired"]:
                    state["expired"] = True
                    log(f"  density TIME BUDGET spent ({DENSITY_TIME_BUDGET_S}s); "
                        "skipping the rest. Presence in §6 is unaffected -- only the "
                        "row numbers are.")
        if state["tripped"] or state["expired"]:
            with lk:
                state["skipped"] += 1
            return sym, day, src.name, None
        sf = sym_filter(src, sym, instrument_ids)
        if sf is None:
            return sym, day, src.name, None
        win = day_windows(day, 1, src.time_col, src.date_only)[0]
        for attempt in range(DENSITY_ATTEMPTS):
            try:
                return sym, day, src.name, exact_count(src.name, sf + win)
            except Probe:
                if attempt + 1 < DENSITY_ATTEMPTS:
                    time.sleep(0.4)
        with lk:
            state["unproven"] += 1
            if state["unproven"] >= DENSITY_MAX_UNPROVEN and not state["tripped"]:
                state["tripped"] = True
                log(f"  density CIRCUIT BREAKER: {state['unproven']} counts failed; "
                    "skipping the rest. Presence in §6 is unaffected -- only the "
                    "row numbers are.")
        return sym, day, src.name, None

    out, done = defaultdict(dict), 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for sym, day, rn, n in ex.map(one, jobs):
            if n is not None:
                out[(sym, day)][rn] = n
            done += 1
            if done % 1000 == 0:
                log(f"  density {done}/{len(jobs)}  requests={REQUESTS_MADE}  "
                    f"unproven={state['unproven']}  skipped={state['skipped']}")
    counted = sum(len(v) for v in out.values())
    why = ("time budget" if state["expired"] else
           "failure breaker" if state["tripped"] else "none")
    log(f"density: {counted} counted, {state['unproven']} unproven, "
        f"{state['skipped']} skipped (stop reason: {why}) "
        f"(presence already established for all of them; only the number is missing)")
    return {"counts": dict(out), "unproven": state["unproven"],
            "skipped": state["skipped"], "tripped": state["tripped"],
            "expired": state["expired"], "stop_reason": why,
            "budget_s": DENSITY_TIME_BUDGET_S,
            "cells": len(jobs), "counted": counted}


def sweep_provenance(rels, trading_days):
    """Group by the provenance column and PROVE the grouping is complete.

    PostgREST has no GROUP BY and no DISTINCT. So: discover the values present in a
    scope by repeatedly asking for one row NOT IN the values already seen, until that
    returns a real empty list; count=exact each value; then count the residual
    (not.in + is.null). If the parts do not sum to the scope total, a value was
    missed and the cell says so rather than presenting a tidy table.
    """
    all_days = sorted(set().union(*[trading_days[s] for s in SYMBOLS]))
    if not all_days:
        return {}
    out = {}
    targets = [(r, c) for r in rels.values() for c in r.provenance_cols if r.time_col]
    log(f"provenance: {len(targets)} (relation, column) pairs carry a provenance column")
    for rel, col in sorted(targets, key=lambda t: (t[0].name, t[1])):
        tcol, date_only = rel.time_col, rel.time_col in DATE_ONLY_COLS
        per_day, closes, breaks = {}, 0, 0
        try:
            total_all = exact_count(rel.name, [])
        except Probe as e:
            out[(rel.name, col)] = {"error": str(e)}
            continue
        if total_all == 0:
            out[(rel.name, col)] = {"total": 0, "days": {}, "closes": 0, "breaks": 0}
            continue
        for day in all_days:
            wins = day_windows(day, 1, tcol, date_only)
            scope = wins[0]
            try:
                total = exact_count(rel.name, scope)
            except Probe:
                continue
            if total == 0:
                continue
            seen = []
            for _ in range(12):
                flt = list(scope) + [("select", col)]
                if seen:
                    flt.append((col, "not.in.(" + ",".join(f'"{v}"' for v in seen) + ")"))
                try:
                    bump_requests()
                    r = _get(rel.name, flt + [("limit", "1")])
                    rows = r.json()
                except Probe:
                    break
                if not rows:
                    bump_empty()
                    break
                val = rows[0].get(col)
                if val is None:
                    break
                seen.append(str(val))
            parts, ssum = {}, 0
            ok = True
            for v in seen:
                try:
                    n = exact_count(rel.name, scope + [(col, f"eq.{v}")])
                except Probe:
                    ok = False
                    break
                parts[v] = n
                ssum += n
            if ok:
                try:
                    nnull = exact_count(rel.name, scope + [(col, "is.null")])
                    ssum += nnull
                except Probe:
                    ok = False
                    nnull = None
            if not ok:
                continue
            if nnull:
                parts["<NULL>"] = nnull
            closed = (ssum == total)
            closes += closed
            breaks += (not closed)
            per_day[day.isoformat()] = {"total": total, "parts": parts, "closes": closed}
        out[(rel.name, col)] = {"total": total_all, "days": per_day,
                                "closes": closes, "breaks": breaks}
        vals = Counter()
        for d in per_day.values():
            for k, n in d["parts"].items():
                vals[k] += n
        log(f"  {rel.name}.{col}: {len(per_day)} days measured, "
            f"values={dict(vals)}, closes={closes} breaks={breaks}")
    return out


def sweep_never_written(sources, rels, global_lo, global_hi):
    """Which declared columns are never populated. Schema presence is not population.

    Ladder: unfiltered -> per month -> per day. A column is reported NEVER WRITTEN
    only when every probed scope returned a real empty list AND those scopes cover
    the relation's full measured range. A column that cannot be resolved that way is
    reported as UNPROVEN, never as absent.
    """
    out = {}
    rel_names = sorted({s.name for s in sources})
    log(f"never-written: {len(rel_names)} candidate relations")
    for name in rel_names:
        rel = rels[name]
        src = next(s for s in sources if s.name == name)
        res = {}
        for col in sorted(rel.cols):
            try:
                if rows_exist(name, [("select", col), (col, "not.is.null")]):
                    res[col] = ("WRITTEN", "unfiltered")
                else:
                    res[col] = ("NEVER WRITTEN", "unfiltered, whole relation")
                continue
            except Probe:
                pass
            lo, hi = source_window(src, global_lo, global_hi)
            if lo is None or src.date_only:
                res[col] = ("UNPROVEN", "unfiltered probe failed; no decomposable range")
                continue
            months, hit, failed = month_windows(lo, hi, src.time_col), False, False
            for w in months:
                try:
                    if rows_exist(name, [("select", col), (col, "not.is.null")] + w):
                        hit = True
                        break
                except Probe:
                    failed = True
                    break
            if hit:
                res[col] = ("WRITTEN", "month decomposition")
            elif not failed:
                res[col] = ("NEVER WRITTEN",
                            f"month decomposition, {len(months)} months covering "
                            f"{lo.isoformat()}..{hi.isoformat()}")
            else:
                res[col] = ("UNPROVEN", "month decomposition hit an unresolvable scope")
        never = [c for c, (v, _) in res.items() if v == "NEVER WRITTEN"]
        unproven = [c for c, (v, _) in res.items() if v == "UNPROVEN"]
        out[name] = res
        if never or unproven:
            log(f"  {name}: never_written={never} unproven={unproven}")
    return out


def month_windows(lo: dt.date, hi: dt.date, time_col):
    out, cur = [], dt.date(lo.year, lo.month, 1)
    while cur <= hi:
        nxt = dt.date(cur.year + (cur.month == 12), (cur.month % 12) + 1, 1)
        out.append([(time_col, f"gte.{cur.isoformat()}"), (time_col, f"lt.{nxt.isoformat()}")])
        cur = nxt
    return out


def sweep_expiry_class(rels, trading_days):
    """Relations holding ONE expiry per timestamp, and whether the expiry class moves.

    Establishes single-expiry-ness by counting the rows sharing one timestamp, then
    walks the full history recording the expiry_type values seen per symbol per day.
    A relation that silently switches class is a relation whose consumers are reading
    a different instrument than they were yesterday, with nothing marking the change.
    """
    out = {}
    cands = [r for r in rels.values()
             if "expiry_type" in r.cols and "symbol" in r.cols and r.time_col == "ts"]
    log(f"expiry-class: {len(cands)} relations carry (symbol, ts, expiry_type)")
    for rel in sorted(cands, key=lambda r: r.name):
        try:
            total = exact_count(rel.name, [])
        except Probe as e:
            out[rel.name] = {"error": str(e)}
            continue
        if total == 0 or total > EXPIRY_ANALYSIS_MAX_ROWS:
            if total == 0:
                why = "empty"
            else:
                why = f"over the {EXPIRY_ANALYSIS_MAX_ROWS:,}-row enumeration cap"
            out[rel.name] = {"skipped": f"{total:,} rows ({why})"}
            continue
        single = {}
        for sym in SYMBOLS:
            try:
                bump_requests()
                r = _get(rel.name, [("select", "ts"), ("symbol", f"eq.{sym}"),
                                    ("order", "ts.desc"), ("limit", "1")])
                rows = r.json()
                if not rows:
                    continue
                single[sym] = exact_count(rel.name, [("symbol", f"eq.{sym}"),
                                                     ("ts", f"eq.{rows[0]['ts']}")])
            except Probe as e:
                single[sym] = f"unresolved: {e}"
        per_day = {s: {} for s in SYMBOLS}
        for sym in SYMBOLS:
            days = sorted(trading_days[sym])
            if not days:
                continue
            for w in month_windows(days[0], days[-1], "ts"):
                off = 0
                while True:
                    try:
                        bump_requests()
                        r = _get(rel.name, [("select", "ts,expiry_type,expiry_date"),
                                            ("symbol", f"eq.{sym}"), ("order", "ts.asc"),
                                            ("limit", "1000"), ("offset", str(off))] + w)
                        rows = r.json()
                    except Probe:
                        break
                    if not rows:
                        bump_empty()
                        break
                    for row in rows:
                        d = str(row["ts"])[:10]
                        per_day[sym].setdefault(d, Counter())[str(row["expiry_type"])] += 1
                    if len(rows) < 1000:
                        break
                    off += 1000
        transitions = {}
        for sym in SYMBOLS:
            prev, tr = None, []
            for d in sorted(per_day[sym]):
                cur = frozenset(per_day[sym][d])
                if prev is not None and cur != prev:
                    tr.append((d, sorted(prev), sorted(cur)))
                prev = cur
            transitions[sym] = tr
        out[rel.name] = {"total": total, "rows_per_ts": single,
                         "per_day": {s: {d: dict(c) for d, c in per_day[s].items()}
                                     for s in SYMBOLS},
                         "transitions": transitions}
        for sym in SYMBOLS:
            log(f"  {rel.name} {sym}: {len(per_day[sym])} days, "
                f"{len(transitions[sym])} expiry-class transitions")
    return out


# ------------------------------------------------------------------- rendering

def md_escape(s):
    return str(s).replace("|", "\\|")


def month_key(d: dt.date):
    return f"{d.year:04d}-{d.month:02d}"


# ---- S78: resolved / scoping rows appended to the §11 table.
# Held as data rather than inline A(...) calls so the identical strings
# could be spliced into the already-rendered register without divergence.
# A regeneration reproduces them from here.
S78_RESOLVED_ROWS = (
    '| vendor greeks, 2025-04 → 2026-03 | **RESOLVED 2026-09-14, do not re-derive** — the chain was purchased from **GFDL** (Global Financial Datafeeds); delivery schema is nine columns (`Ticker, Date, Time, Open, High, Low, Close, Volume, Open Interest`) measured uniform across all 175,304 rows of `GFDLNFO_BACKADJUSTED_01042025.csv`. No IV and no greeks were delivered | `hist_option_bars_1m` greek columns are declared and never written (S75, 289 weekdays; S78 re-verified all six plus five Heston params). `hist_option_greeks_1m` iv and gamma are MERDIAN-solved via `backfill_hist_greeks.py` at a chosen `r_used`, not vendor-supplied. `delta`/`theta`/`vega` for that era do not exist and cannot be recovered from this vendor. Closes **TD-S35-NEW-2**; confirms **TD-S58-NEW-1** from the file side |',
    "| the vendor file's location | the CSV is **not** on the AWS box — `find /home/ssm-user -iname 'GFDL*'` returns nothing. It reached S78 via chat upload from the operator's local machine | the schema above is established from the file and cannot be re-verified from AWS. Record where the raw delivery lives before the next session needs it |",
    '| supersession | `docs/research/data_inventory_2026-09-08.md` (S75) and `iv_availability_2026-09-08.md` (S75) are superseded by this register, which regenerates | both remain in git; both come out of the project-knowledge upload set (S78) |',
)


def render(ctx):
    """Build the register. Every number carries the parameterised query that made it."""
    L = []
    A = L.append
    today = ctx["today"]

    A("# MERDIAN Data Inventory")
    A("")
    A(f"**Measured:** {today}  ·  **Regenerate:** `scripts/build_data_inventory.py` "
      "(no arguments)")
    A("")
    A("> **Use this register instead of re-deriving.** The extent of MERDIAN's option")
    A("> history has been re-derived from scratch at least a dozen times across 70+")
    A("> sessions, each time from whichever table that session's brief named, producing")
    A("> a different answer each time. If this file looks stale, **re-run the script** —")
    A("> do not measure one table and generalise from it.")
    A("")
    A(f"Measured against the live database. Nothing here is taken from "
      "`merdian_reference.json`, from any register, or from a table name.")
    A("")
    A("---")
    A("")

    # ---- 1 method
    A("## 1. Method, and the access path")
    A("")
    A("This box has no `psql`, no `psycopg2`/`psycopg`/`asyncpg`/`pg8000`/`sqlalchemy`,")
    A("and no Postgres password. The only route is PostgREST as the service role.")
    A("The script is READ-ONLY: HTTP GET only, no RPC, no write.")
    A("")
    A("Six rules govern every number below.")
    A("")
    A("1. **`count=exact` always.** `count=planned` on a `not.is.null` filter over an")
    A("   all-NULL column returns a planner floor of **1**, which is not a row.")
    A("   No planned figure appears anywhere in this register.")
    A("2. **A `57014` is never an absence.** Every failing probe is retried, then")
    A("   decomposed (day → halves → quarters → eighths). Only an HTTP 200 carrying a")
    A("   literal empty JSON array counts as absence. Anything unresolved is listed in")
    A("   §10 and the script refuses to write while §10 is non-empty.")
    A("3. **Every zero cell is a real empty list** from a day-scoped `limit=1` probe.")
    A(f"   **{ctx['empty_confirmations']:,}** such confirmations were counted on this run.")
    A("4. **Ranges are probed one month beyond each discovered edge**, so a real edge")
    A("   outside the window appears rather than being excluded by construction.")
    A("5. **The relation list comes from the live catalog** — the PostgREST OpenAPI")
    A("   document, generated from `pg_catalog`.")
    A("6. **A relation that cannot produce a real empty list is excluded**, as")
    A("   UNMEASURABLE BY THIS METHOD — by measurement, never by name and never by")
    A("   catalog category. Each source is probed on a window it certainly holds no")
    A("   rows in; one that must scan its whole extent to prove absence times out")
    A("   instead of returning `[]`, and so can never satisfy rule 3 on an empty day.")
    A("   The exclusions and their timings are in §4b. This does **not** block the")
    A("   write — but it does mean the register says **nothing** about those")
    A("   relations, neither presence nor absence.")
    A("")
    A("```")
    A("GET /rest/v1/                                    -- the relation list")
    A("GET /rest/v1/<rel>?select=*&limit=0              Prefer: count=exact")
    A("GET /rest/v1/<rel>?select=<col>&<col>=not.is.null&<scope>&limit=1")
    A("```")
    A("")
    A("**Calendar-day windows.** Timestamp columns are filtered `[D, D+1)` in UTC. An")
    A("IST session (09:15–15:30 IST = 03:45–10:00 UTC) falls strictly inside one UTC")
    A("calendar day, and so does a session stored under the legacy IST-clock-as-UTC")
    A("convention (Rules 16/20, hours 09–15). Both are contained by the same window,")
    A("so no session is split across two cells.")
    A("")
    A(f"Requests issued this run: **{ctx['requests']:,}**. "
      f"Wall time: **{ctx['elapsed']}**.")
    A("")

    # ---- 2 relations
    rels = ctx["rels"]
    A(f"## 2. Every relation in schema `public` — {len(rels)}")
    A("")
    A("The catalog does **not** distinguish tables from views; PostgREST's OpenAPI")
    A("document exposes both identically and the catalog view that would separate them")
    A("is not reachable on this access path. That limit is recorded in §10, not guessed.")
    A("")
    A("```")
    for i in range(0, len(sorted(rels)), 3):
        A("  " + "  ".join(f"{n:<44}" for n in sorted(rels)[i:i + 3]).rstrip())
    A("```")
    A("")

    # ---- 3 classifier
    A("## 3. How a relation became a candidate")
    A("")
    A("Membership was decided by reading each relation's column list out of the live")
    A("catalog, never from its name. A relation is a **candidate** if it carries a")
    A("strike dimension or a volatility/greek/OI column:")
    A("")
    A("```")
    A(f"strike (any)  {RE_STRIKE_ANY.pattern}")
    A(f"strike (dim)  {RE_STRIKE_DIM.pattern}      <- the row is KEYED by strike")
    A(f"greek         {RE_GREEK_ANY.pattern}")
    A(f"volatility    {RE_VOL_ANY.pattern}")
    A(f"open interest {RE_OI.pattern}")
    A(f"gamma         {RE_GAMMA.pattern}")
    A(f"iv            {RE_IV.pattern}")
    A(f"spot          {RE_SPOT.pattern}")
    A(f"provenance    {RE_PROVENANCE.pattern}")
    A("```")
    A("")
    A("For the gamma / iv / oi / spot **layers** a name match is not sufficient — the")
    A("column must also carry a numeric type in the catalog. That is what keeps")
    A("`iv_regime` (a text label) from being counted as an implied volatility.")
    A("")
    A("**A strike dimension is not the same as a strike column.** A relation with")
    A("`strike` is keyed by strike and can serve a per-strike layer. A relation with")
    A("only `atm_strike` / `ce_strike` / `pe_strike` holds **one distinguished strike**")
    A("per row and cannot. Both are listed; only the first can make a day COMPUTABLE.")
    A("")
    srcs = ctx["sources"]
    A(f"**{ctx['n_candidates']}** relations are candidates. **{len(srcs)}** of them can")
    A("actually serve a layer for a (symbol, day) cell — the rest lack a symbol")
    A("identifier, a usable time column, or a numeric layer column.")
    A("")

    # ---- 4 sources and bounds
    A("## 4. Candidate sources and their measured bounds")
    A("")
    A("Bounds are read from the relation's scoping column. Where the first-choice")
    A("column could not answer — an ordered scan can exceed the statement timeout on a")
    A("column with no usable index at that relation's size — the walk falls through to")
    A("the next column, and **the column that actually answered is named below**.")
    A("")
    A("| relation | kind | symbol via | bounds col | layers served | min | max |")
    A("|---|---|---|---|---|---|---|")
    for s in srcs:
        if s.is_empty:
            lo = hi = "*empty relation*"
        else:
            lo = md_escape(s.tmin or "*unresolved*")
            hi = md_escape(s.tmax or "*unresolved*")
        A(f"| `{s.name}` | {s.kind} | `{s.sym_mode}` | "
          f"`{s.bounds_col or s.time_col}` | "
          f"{', '.join(sorted(s.layers)) or '—'} | {lo} | {hi} |")
    A("")
    notes = [s for s in srcs if s.bounds_note]
    if notes:
        A("Relations whose bounds did not come from the first-choice column, or which")
        A("hold no rows at all:")
        A("")
        A("| relation | note |")
        A("|---|---|")
        for s in notes:
            A(f"| `{s.name}` | {md_escape(s.bounds_note)} |")
        A("")
    A("An **empty relation** above is a measurement, not a failure: every scoping")
    A("column probed returned a real empty list. Such relations are excluded from the")
    A("day sweep because they can serve no day, and they are not listed in §10.")
    A("")
    A("Query, per relation and direction:")
    A("```")
    A("GET /<rel>?select=<time_col>&order=<time_col>.asc|desc&limit=1")
    A("```")
    A("")

    # ---- 4b sources that never reached the day sweep
    A("### 4b. Sources that did not reach the day sweep")
    A("")
    dropped = ctx["dropped"]
    if not dropped:
        A("None. Every candidate source above was swept over its own padded window.")
        A("")
    else:
        A("A source can leave the sweep for three reasons, and they mean different")
        A("things. Most consequential first, in this list and in the table:")
        A("")
        A("- **unmeasured** — its bounds never resolved, so its days were never probed.")
        A("  Its layers are **absent from every cell in §6**, and that absence is a hole")
        A("  in the method, not a property of the data. Any such row is also in §10 and")
        A("  therefore blocked this register from being written at all — if you are")
        A("  reading one here, read §10 before trusting §6.")
        A("- **unmeasurable by this method** — the relation cannot produce a real empty")
        A("  list (rule 6), so rule 3 cannot be satisfied for it on any day it holds no")
        A("  rows. Excluded by rule, with the measured timings below. This does **not**")
        A("  block the write: it is a measured property of the relation, stated, not a")
        A("  probe that went missing. What it does mean is that **this register says")
        A("  nothing about that relation** — neither presence nor absence. Do not read")
        A("  the exclusion as emptiness.")
        A("- **empty** — every scoping column returned a real empty list. The relation")
        A("  holds no rows, so it can serve no day. A *measurement*; no cell below is")
        A("  missing on its account.")
        A("")
        A("| relation | why | layers it would have served | detail |")
        A("|---|---|---|---|")
        _rank = {"unmeasured": 0, "unmeasurable": 1, "empty": 2}
        for d in sorted(dropped, key=lambda x: (_rank.get(x["kind"], 9), x["name"])):
            A(f"| `{d['name']}` | **{d['kind']}** | "
              f"{', '.join(d['layers']) or '—'} | {md_escape(d['reason'])} |")
        A("")
        # The check that makes an exclusion safe to read: does any layer rest SOLELY
        # on a source that left the sweep? If so, every cell reporting that layer
        # absent in §6 is unproven, and saying so is the whole point of this section.
        gone = {d["name"] for d in dropped if d["kind"] in ("unmeasured", "unmeasurable")}
        lost = set()
        for d in dropped:
            if d["kind"] in ("unmeasured", "unmeasurable"):
                lost.update(d["layers"])
        kept = set()
        for s in srcs:
            if s.name not in gone and not s.is_empty:
                kept.update(s.layers)
        orphaned = sorted(lost - kept)
        if orphaned:
            A(f"**Layers served ONLY by excluded sources: "
              f"{', '.join('`' + x + '`' for x in orphaned)}.** Every cell reporting one")
            A("of these absent in §6 is unproven for that layer — nothing looked.")
        else:
            A("Every layer an excluded source would have served is also served by at")
            A("least one source that was swept, so **no layer in §6 rests solely on an")
            A("exclusion**.")
        A("")

    # ---- 5 identifiers
    A("## 5. Identifier resolution")
    A("")
    A("Several relations identify the underlying by `instrument_id uuid` rather than by")
    A("a symbol string. `public.instruments` resolves it.")
    A("")
    A("| symbol | exchange | strike_step | lot_size |")
    A("|---|---|---:|---:|")
    for row in ctx["instruments_rows"]:
        A(f"| {row.get('symbol')} | {row.get('exchange')} | {row.get('strike_step')} | "
          f"{row.get('lot_size')} |")
    A("")
    A("```")
    A("GET /instruments?select=*")
    A("```")
    A("")
    A("The UUID values themselves are deliberately not printed here; re-read them from")
    A("`instruments` rather than pasting them into a script.")
    A("")

    # ---- 6 the answer
    A("## 6. What is computable, per symbol per trading day")
    A("")
    A("**Denominator.** A day counts as a trading day for a symbol when")
    A("`hist_spot_bars_1m` holds at least one row for that symbol on that date — the")
    A("only relation spanning the full window for both symbols. Its limits are in §10.")
    A("")
    A("**The three states.**")
    A("")
    A("- **COMPUTABLE NOW** — per-strike gamma *and* the open interest to pair with it")
    A("  are available on that day, and a spot is available.")
    A("- **COMPUTABLE AFTER DERIVATION** — no gamma, but per-strike **iv** and OI are")
    A("  available, so Black-Scholes can supply the gamma.")
    A("- **NOT COMPUTABLE** — neither.")
    A("")
    A("**Two verdicts, because the answer depends on whether a join is allowed.**")
    A("")
    A("| verdict | means |")
    A("|---|---|")
    A("| `same-relation` | one relation carries gamma **and** OI in the same row |")
    A("| `joined` | gamma on one per-strike relation, OI on another, where the "
      "row-level key correspondence between that pair was **measured** to hold (§6.1) |")
    A("")
    A("This is load-bearing, not cosmetic, and the reason is measured rather than")
    A("assumed. Counting days on which each per-strike relation actually supplied each")
    A("layer, across every day where the two verdicts disagree:")
    A("")
    v0 = ctx["verdicts"]
    split = [(s, d, c) for (s, d), c in v0.items() if c["verdict"] != c["verdict_same"]]
    if split:
        gsrc, osrc, isrc = Counter(), Counter(), Counter()
        for _s, _d, c in split:
            gsrc.update(c["gamma"])
            osrc.update(c["oi"])
            isrc.update(c["iv"])
        lo_d = min(d for _s, d, _c in split)
        hi_d = max(d for _s, d, _c in split)
        A(f"- **{len(split)}** (symbol, day) cells are classified differently by the two")
        A(f"  verdicts, spanning {lo_d.isoformat()} … {hi_d.isoformat()}.")
        A("- On those days, per-strike **gamma** was supplied by: "
          + (", ".join(f"`{r}` ({n}d)" for r, n in gsrc.most_common()) or "nothing") + ".")
        A("- per-strike **OI** by: "
          + (", ".join(f"`{r}` ({n}d)" for r, n in osrc.most_common()) or "nothing") + ".")
        A("- per-strike **iv** by: "
          + (", ".join(f"`{r}` ({n}d)" for r, n in isrc.most_common()) or "nothing") + ".")
        both = sorted(set(gsrc) & set(osrc))
        A(f"- relations supplying **both** gamma and OI on any of those days: "
          + (", ".join(f"`{r}`" for r in both) if both else "**none** — which is exactly "
             "why `same-relation` cannot resolve them and a measured join can."))
    else:
        A("- **No cell is classified differently by the two verdicts on this run.** Every")
        A("  day that is computable is computable from a single relation, so nothing")
        A("  below depends on a join holding.")
    A("")
    A("Quoting only `same-relation` would invert the headline wherever that split is")
    A("non-empty; quoting only `joined` would hide that those days depend on a join.")
    A("Both are below. **`joined` is the operative answer**, and it is only ever granted")
    A("on a pair whose correspondence was measured in §6.1.")
    A("")
    v = ctx["verdicts"]
    months = sorted({month_key(d) for (_s, d) in v})
    A("| month | symbol | trading days | NOW (joined) | AFTER-DERIV (joined) | "
      "NOT (joined) | NOW (same-rel) | serving |")
    A("|---|---|---:|---:|---:|---:|---:|---|")
    for m in months:
        for sym in SYMBOLS:
            cells = [c for (s, d), c in v.items() if s == sym and month_key(d) == m]
            if not cells:
                continue
            now = sum(c["verdict"] == "COMPUTABLE NOW" for c in cells)
            aft = sum(c["verdict"] == "COMPUTABLE AFTER DERIVATION" for c in cells)
            nots = sum(c["verdict"] == "NOT COMPUTABLE" for c in cells)
            now_s = sum(c["verdict_same"] == "COMPUTABLE NOW" for c in cells)
            srcct = Counter()
            for c in cells:
                for r in c["sources"]:
                    srcct[r] += 1
            names = ", ".join(f"`{r}` ({n}d)" for r, n in srcct.most_common()) or "—"
            A(f"| {m} | {sym} | {len(cells)} | {now} | {aft} | {nots} | {now_s} | "
              f"{names} |")
    A("")
    A("A serving entry of the form `A+B` is a joined pair: gamma from `A`, OI from `B`.")
    A("")

    # ---- 6.1 correspondence
    A("### 6.1 The key correspondence that licenses every join")
    A("")
    A("Two relations sharing five column names prove nothing about whether a given")
    A("contract-minute in one exists in the other. So each ordered pair was measured:")
    A("real key tuples were sampled from the gamma side and each was probed for in the")
    A("OI side. **A pair is used only at a perfect hit rate with zero unresolved")
    A("probes**; anything less is reported with its rate and not used.")
    A("")
    A("An unresolved probe is counted in the denominator, never subtracted from it.")
    A("Subtracting would let 10 hits and 10 timeouts report 100% — a `57014` counted as")
    A("corroboration, which is method rule 2 running backwards.")
    A("")
    A("The join's time column is taken from the columns the two relations **share**,")
    A("not from either one's scoping column, and a date-only column is refused: joining")
    A("on `trade_date` pairs every contract-minute of one side with every")
    A("contract-minute of the other across a whole session, which is a cross product.")
    A("")
    A("```")
    A("GET /<gamma_rel>?select=<key cols>&<symbol>&<day>&limit=<n>       -- sample")
    A("GET /<oi_rel>?select=<k0>&<k0>=eq.<v0>&<k1>=eq.<v1>&...&limit=1   -- probe")
    A("```")
    A("")
    corr = ctx["correspondence"]
    if corr:
        A("| gamma side | OI side | symbol | key | sampled | hits | errors | rate | used |")
        A("|---|---|---|---|---:|---:|---:|---:|---|")
        for k in sorted(corr):
            c = corr[k]
            key = ", ".join(f"`{x}`" for x in c["key"]) if c.get("key") else "—"
            if "sampled" in c:
                A(f"| `{c['a']}` | `{c['b']}` | {c['symbol']} | {key} | "
                  f"{c['sampled']} | {c['hits']} | {c.get('errors', 0)} | "
                  f"{c['rate']:.1%} | {'**yes**' if c['holds'] else 'no'} |")
            else:
                A(f"| `{c['a']}` | `{c['b']}` | {c['symbol']} | {key} | — | — | — | — | "
                  f"no — {c.get('reason', '')} |")
    else:
        A("No pair of per-strike relations presented a gamma side and an OI side on the")
        A("same day, so no join was measured and `joined` equals `same-relation`")
        A("everywhere above.")
    A("")
    A("Query, per source per symbol per day:")
    A("```")
    A("GET /<rel>?select=<time_col>&<symbol filter>&<day window>&limit=1      -- exists?")
    A("GET /<rel>?select=<col>&<col>=not.is.null&<symbol filter>&<day window>&limit=1")
    A("     <symbol filter> = symbol=eq.<SYM>   or   instrument_id=eq.<uuid>")
    A("     <day window>    = <tcol>=gte.<D>&<tcol>=lt.<D+1>   or   <tcol>=eq.<D>")
    A("```")
    A("")
    A("### Totals")
    A("")
    A("| | " + " | ".join(SYMBOLS) + " |")
    A("|---|" + "---:|" * len(SYMBOLS))
    for label, pred in (
            ("trading days measured", lambda c: True),
            ("COMPUTABLE NOW (joined)", lambda c: c["verdict"] == "COMPUTABLE NOW"),
            ("COMPUTABLE AFTER DERIVATION (joined)",
             lambda c: c["verdict"] == "COMPUTABLE AFTER DERIVATION"),
            ("NOT COMPUTABLE (joined)", lambda c: c["verdict"] == "NOT COMPUTABLE"),
            ("COMPUTABLE NOW (same-relation only)",
             lambda c: c["verdict_same"] == "COMPUTABLE NOW"),
            ("NOT COMPUTABLE (same-relation only)",
             lambda c: c["verdict_same"] == "NOT COMPUTABLE")):
        vals = [sum(pred(c) for (s, _d), c in v.items() if s == sym) for sym in SYMBOLS]
        A(f"| {label} | " + " | ".join(f"{x:,}" for x in vals) + " |")
    A("")

    # ---- cross-check against the last trusted measurement
    A("### Cross-check against the S75 sweep")
    A("")
    A(f"`docs/research/data_inventory_2026-09-08.md` §6 measured this question on")
    A(f"{PRIOR['date']} over {PRIOR['window']}. Those figures are quoted as prior art")
    A("and are **not** an input to anything above. This run's totals are recomputed")
    A("over that same window so the two are comparable.")
    A("")
    p_lo, p_hi = (dt.date.fromisoformat(x) for x in PRIOR["window"].split(".."))
    hdr = ["", *(f"{s} S75" for s in SYMBOLS), *(f"{s} now" for s in SYMBOLS), "delta"]
    A("| " + " | ".join(hdr) + " |")
    A("|---|" + "---:|" * (2 * len(SYMBOLS)) + "---|")
    for label, key, pred in (
            ("trading days", "days", lambda c: True),
            ("COMPUTABLE NOW", "now", lambda c: c["verdict"] == "COMPUTABLE NOW"),
            ("COMPUTABLE AFTER DERIVATION", "after",
             lambda c: c["verdict"] == "COMPUTABLE AFTER DERIVATION"),
            ("NOT COMPUTABLE", "not", lambda c: c["verdict"] == "NOT COMPUTABLE")):
        mine = [sum(pred(c) for (s, d), c in v.items() if s == sym and p_lo <= d <= p_hi)
                for sym in SYMBOLS]
        theirs = [PRIOR[key][sym] for sym in SYMBOLS]
        delta = ", ".join(f"{s} {m - t:+d}" for s, m, t in zip(SYMBOLS, mine, theirs))
        A(f"| {label} | " + " | ".join(str(x) for x in theirs) + " | "
          + " | ".join(str(x) for x in mine) + f" | {delta} |")
    A("")
    A("A non-zero delta is not automatically an error — the database has moved since")
    A("that date, and this run's classifier differs in ways §6 and §6.1 state")
    A("explicitly. But **a delta with no explanation is not a result.** Read §4 and")
    A("§6.1 before quoting any number that disagrees with the row above.")
    A("")
    A("### Layer availability, counted independently of the verdict")
    A("")
    A("A day can have OI without gamma, or spot without either. These columns count")
    A("days on which **any** relation supplied that layer, so they do not sum to the")
    A("verdict above and are not meant to.")
    A("")
    A("**Per-strike** columns count relations keyed by `strike` — a chain.")
    A("**ATM-only** columns count `single_strike` relations, which hold one")
    A("distinguished strike (`atm_strike`, `ce_strike`) per row. ATM-only availability")
    A("is **measured and reported but never admitted to the verdict**: one strike is")
    A("not a chain, and a GEX cannot be computed from it. It is here because \"is there")
    A("ATM gamma on a day the chain has none\" is a real question with a real answer.")
    A("")
    A("| symbol | days | gamma (per-strike) | iv (per-strike) | oi (per-strike) | "
      "gamma (ATM-only) | iv (ATM-only) | oi (ATM-only) | spot |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for sym in SYMBOLS:
        cells = [c for (s, _d), c in v.items() if s == sym]
        keys = ("gamma", "iv", "oi", "gamma_ss", "iv_ss", "oi_ss", "spot")
        A(f"| {sym} | {len(cells)} | " + " | ".join(
            str(sum(bool(c[k]) for c in cells)) for k in keys) + " |")
    A("")
    ss_only = {}
    for sym in SYMBOLS:
        n = sum(1 for (s, _d), c in v.items()
                if s == sym and c["gamma_ss"] and not c["gamma"])
        ss_only[sym] = n
    if any(ss_only.values()):
        A("Days carrying **ATM gamma but no per-strike gamma** — computable as a single")
        A("strike, not as a chain: "
          + ", ".join(f"{s} **{n}**" for s, n in ss_only.items()) + ".")
    else:
        A("No day carries ATM gamma without also carrying per-strike gamma.")
    A("")
    A("### Days NOT COMPUTABLE, enumerated")
    A("")
    A("Listed under the **joined** verdict. The `same-relation`-only count is given")
    A("beside it, and where the two differ the difference is the set of days that exist")
    A("solely because a measured join licenses them — those days are enumerated")
    A("separately, because a reader who intends to compute without joining needs to")
    A("know which days they lose.")
    A("")
    for sym in SYMBOLS:
        bad = sorted(d for (s, d), c in v.items()
                     if s == sym and c["verdict"] == "NOT COMPUTABLE")
        bad_same = sorted(d for (s, d), c in v.items()
                          if s == sym and c["verdict_same"] == "NOT COMPUTABLE")
        only_join = sorted(set(bad_same) - set(bad))
        A(f"**{sym} — {len(bad)} days NOT COMPUTABLE (joined); "
          f"{len(bad_same)} (same-relation only).**")
        A("")
        A("```")
        for i in range(0, len(bad), 8):
            A("  " + "  ".join(d.isoformat() for d in bad[i:i + 8]))
        if not bad:
            A("  (none)")
        A("```")
        A("")
        if only_join:
            A(f"Of those, **{len(only_join)} days are computable ONLY via a measured")
            A("join** — they are NOT COMPUTABLE if you restrict yourself to a single")
            A("relation:")
            A("")
            A("```")
            for i in range(0, len(only_join), 8):
                A("  " + "  ".join(d.isoformat() for d in only_join[i:i + 8]))
            A("```")
            A("")

    # ---- 6.2 density
    A("### 6.2 How much — row counts, not just presence")
    A("")
    A("Presence is a yes/no. It does not distinguish a session with a full chain")
    A("from one with four rows scraped after a restart, and a register that only")
    A("says *yes* invites exactly that mistake. So every cell the sweep found")
    A("**present** was then counted with `count=exact` on the same day scope.")
    A("")
    A("Counted per **relation-day**, not per layer-day: gamma, iv and oi on one")
    A("relation live in the same rows, so a per-layer count would be the same number")
    A("repeated. No new presence probe was issued — this only puts a number on cells")
    A("already known to be non-empty.")
    A("")
    den = ctx["density"]
    if not den or not den.get("counts"):
        A("*No density was measured on this run.*")
        A("")
    else:
        A(f"**{den['cells']:,}** (symbol, day, relation) cells were eligible. "
          f"**{den['counted']:,}** returned a count; **{den['unproven']:,}** failed; "
          f"**{den.get('skipped', 0):,}** were skipped.")
        A("")
        if den.get("expired") or den.get("tripped"):
            if den.get("expired"):
                A(f"> **Density stopped on its time budget** of "
                  f"{den.get('budget_s', 0)}s. Counting is bounded deliberately: the")
                A("> register is only useful if it is cheap enough to re-run, and a")
                A("> supplementary number is not worth an unbounded tail.")
            else:
                A(f"> **The density failure breaker tripped** after "
                  f"{den['unproven']:,} counts failed.")
            A(f"> The remaining **{den.get('skipped', 0):,}** cells were not counted.")
            A("> **§6 presence is unaffected** — every verdict there rests on probes")
            A("> that resolved. What is missing is row numbers, and the table below")
            A("> is partial. Re-run to extend it, or raise the budget.")
            A("")
        A("An unproven count is **not** an unresolved presence probe and is not in")
        A("§10. The sweep already established that rows exist on that day; a")
        A("`count=exact` that times out leaves the *number* missing, not the *fact*.")
        A("Recording it as unresolved would block this register over a supplementary")
        A("measurement and would also assert something false — that presence is in")
        A("doubt. It is not.")
        A("")
        A("```")
        A("GET /<rel>?select=*&limit=0&<symbol filter>&<day window>   Prefer: count=exact")
        A("```")
        A("")
        # Aggregate per (symbol, month, relation): a per-day table would be ~8k rows.
        agg = defaultdict(list)
        for (sym, day), per_rel in den["counts"].items():
            for rn, n in per_rel.items():
                agg[(sym, month_key(day), rn)].append(n)
        A("| symbol | month | relation | days | total rows | median/day | min | max |")
        A("|---|---|---|---:|---:|---:|---:|---:|")
        for (sym, mo, rn) in sorted(agg):
            v = sorted(agg[(sym, mo, rn)])
            med = v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) // 2
            A(f"| {sym} | {mo} | `{rn}` | {len(v)} | {sum(v):,} | {med:,} | "
              f"{v[0]:,} | {v[-1]:,} |")
        A("")
        A("**Read the `min` column.** A month whose median is a full chain but whose")
        A("minimum is single digits contains a day that is present-but-hollow. Those")
        A("days pass every presence test in §6 and will not support a GEX.")
        A("")

    # ---- 7/8/9 deliberately not measured here
    A("## 7–9. Deliberately not measured by this register")
    A("")
    A("Three sweeps that earlier drafts of this script ran are **not** run, and their")
    A("absence is a scoping decision, not an omission.")
    A("")
    A("| question | why not here | where it was answered |")
    A("|---|---|---|")
    A("| **§7** Which rows came from a producer other than the primary ingest? | "
      "36 `(relation, column)` pairs at ~13 min each — **over seven hours**. The "
      "three that completed were `eq_macro_data`, `eq_price_daily` and "
      "`eq_price_daily_backup_20260618`: equity tables and a dated backup, none of "
      "which this register makes a claim about. | Directly, per relation, when a "
      "specific producer question arises. |")
    A("| **§8** Which declared columns are never written? | Probes every column of "
      "every candidate relation; schema hygiene, not data extent. | S62 established "
      "`hist_gamma_metrics.gamma_concentration` was the single empty column by "
      "direct query. |")
    A("| **§9** Does a single-expiry relation silently change expiry class? | Row "
      "enumeration under a 200k cap; an instrument-identity question, not an "
      "availability one. | S33 measured the NSE/BSE weekday swap directly from "
      "`hist_atm_option_bars_5m.expiry_date`. |")
    A("")
    A("Each is a real question with a real answer, and each was answered this session")
    A("by a handful of direct queries in minutes. **They are not this question.** If")
    A("they are wanted continuously they get their own script, on their own cadence.")
    A("")
    A("The functions remain in the file, unreferenced, so that script can lift them")
    A("rather than rewrite them: `sweep_provenance()`, `sweep_never_written()`,")
    A("`sweep_expiry_class()`.")
    A("")
    A("> **Why this matters more than the three sweeps did.** A register that")
    A("> regenerates in under an hour gets re-run. One that takes eight hours never")
    A("> does — and then the extent question gets re-derived from scratch by the next")
    A("> session that needs it, which is the exact failure this file was built to")
    A("> end. Scope is what keeps it runnable.")
    A("")

    # ---- 10 unresolved + limits
    A("## 10. Unresolved probes")
    A("")
    if ctx["unresolved"]:
        A("**The script wrote this register with unresolved probes outstanding, which it")
        A("is not supposed to do. Treat every number above as provisional.**")
        A("")
        A("| what | scope | reason |")
        A("|---|---|---|")
        for u in ctx["unresolved"]:
            A(f"| {u['what']} | {u['scope']} | {u['reason']} |")
    else:
        A("**None.** Every probe in this run resolved to a value or to a real empty")
        A("list. The script asserts this before writing and refuses to write otherwise.")
    A("")
    A("## 11. What this method could NOT measure")
    A("")
    A("No proxy is substituted for any of these. They are absent, not estimated.")
    A("")
    A("| item | why | what was done instead |")
    A("|---|---|---|")
    A("| `pg_total_relation_size` per relation | needs SQL against `pg_class`/"
      "`pg_namespace`; PostgREST exposes only `public` tables, no RPC wraps it, and "
      "there is no psql or DB password | omitted; no size figure appears in this "
      "register |")
    A("| tables vs views | the OpenAPI document renders both identically and the "
      "catalog view that separates them is unreachable | §2 says \"relations\" "
      "throughout and never claims a relation is a table |")
    A("| exact row counts on the largest relations | `count=exact` exceeds the "
      "statement timeout on multi-million-row relations | presence/absence measured "
      "per-day, where exact answers are available; no planned figure is reported |")
    A("| distinct strike counts | PostgREST has no `DISTINCT`, and materialising a "
      "month of strikes from a 54.8M-row relation is not viable through it | absent "
      "rather than estimated |")
    A("| whether a weekday with no `hist_spot_bars_1m` row is a market holiday or a "
      "data gap | the denominator is defined by the presence of spot bars and cannot "
      "distinguish the two | such days are excluded from the denominator entirely, so "
      "they inflate neither the numerator nor the total |")
    A("| whether a relation's rows are *correct* | this register measures presence and "
      "non-nullness only | nothing here should be read as a statement about accuracy |")
    A("| implied volatility on the ATM bar relations | `hist_atm_option_bars_5m` and "
      "`_15m` carry OHLC-shaped IV (`ce_iv_open/high/low/close`), which `RE_IV`'s "
      "terminal anchor does not match — a bar-aggregate IV is not the point-in-time "
      "IV the other relations hold | those relations report **no iv layer**. This is a "
      "scoping decision, stated here rather than left as an unexplained blank; their "
      "gamma, OI and spot are measured normally |")
    for _row in S78_RESOLVED_ROWS:
        A(_row)
    A("")
    A("---")
    A("")
    A(f"*Generated by `scripts/build_data_inventory.py` on {today}. "
      f"{ctx['requests']:,} requests, {ctx['empty_confirmations']:,} empty-list "
      f"confirmations, {len(ctx['unresolved'])} unresolved.*")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------ main

def main():
    global LOG_FH
    t0 = time.monotonic()
    today = dt.date.today().isoformat()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"data_inventory_{today}.log"
    LOG_FH = log_path.open("a", encoding="utf-8")
    log("=" * 78)
    log(f"build_data_inventory.py  measuring {today}")
    log(f"log:      {log_path}")
    log(f"register: {OUT_PATH}")
    log(f"pid:      {os.getpid()}")
    log("=" * 78)

    rels = fetch_catalog()

    bump_requests()
    instruments_rows = _get("instruments", [("select", "*")]).json()
    instrument_ids = {r["symbol"]: r["id"] for r in instruments_rows if r.get("symbol")}
    log(f"instruments: {len(instruments_rows)} rows, "
        f"symbols resolved: {sorted(instrument_ids)}")

    candidates = [r for r in rels.values() if is_candidate(r)]
    sources = build_sources(rels)
    sources = [s for s in sources if is_candidate(s.rel)]
    log(f"candidates: {len(candidates)}; layer-serving sources: {len(sources)}")

    # Method rule 6, BEFORE bounds. Two reasons for the ordering. It costs nothing to
    # skip bounds discovery on a source that will be excluded anyway; and a source
    # that fails BOTH is UNMEASURABLE (a stated property) rather than FAILED (a
    # missing probe that blocks the write) -- running bounds first would file it as
    # the second before the first was known.
    log(f"absence probe: can each source produce a real empty list? "
        f"(method rule 6, {len(sources)} sources, 1 request each)")
    keep = []
    for i, s in enumerate(sources, 1):
        verdict, evidence = probe_absence(s)
        if verdict == "CANNOT":
            note_dropped(s, "unmeasurable",
                         "cannot produce a real empty list, so method rule 3 cannot be "
                         "satisfied on any day it holds no rows: " + evidence)
        else:
            keep.append(s)
            if verdict == "INCONCLUSIVE":
                log(f"  INCONCLUSIVE {s.name}: {evidence} -- KEPT; exclusion is not "
                    "taken on an inconclusive measurement")
        if i % 10 == 0:
            log(f"  absence {i}/{len(sources)}  requests={REQUESTS_MADE}")
    log(f"absence probe: {len(keep)} measurable, "
        f"{len(sources) - len(keep)} UNMEASURABLE BY THIS METHOD")
    sources = keep

    # SERIAL, deliberately. This phase is two requests per time column per source --
    # of the order of a hundred requests in total -- so concurrency buys no useful
    # wall-clock. What it does buy is WORKERS simultaneous ORDERED SCANS against
    # multi-million-row relations, which is precisely the shape that exceeds the
    # statement timeout. The first live run lost two relations to HTTP 500 here while
    # the same relations resolved cleanly, moments earlier, in a serial smoke test.
    # The cost of that is not local: a source with no bounds is dropped from the layer
    # sweep entirely, so the loss shows up as a hole rather than as an absence.
    log(f"bounds: discovering min/max per source, SERIALLY ({len(sources)} sources)")
    for i, s in enumerate(sources, 1):
        discover_bounds(s)
        if i % 10 == 0:
            log(f"  bounds {i}/{len(sources)}  requests={REQUESTS_MADE}")

    stamps = [s.tmin for s in sources if s.tmin] + [s.tmax for s in sources if s.tmax]
    dates = []
    for s in stamps:
        try:
            dates.append(dt.date.fromisoformat(str(s)[:10]))
        except ValueError:
            pass
    if not dates:
        log("FATAL: no usable bounds discovered on any source")
        return 3
    global_lo = min(dates) - dt.timedelta(days=PAD_DAYS)
    global_hi = min(max(dates) + dt.timedelta(days=PAD_DAYS), dt.date.today())
    log(f"global window (padded {PAD_DAYS}d each side): {global_lo} .. {global_hi}")

    trading_days = sweep_trading_days(rels, instrument_ids, global_lo, global_hi)
    avail = sweep_layers(sources, instrument_ids, trading_days, global_lo, global_hi)
    correspondence = sweep_correspondence(sources, avail, instrument_ids)
    verdicts = classify(avail, trading_days, correspondence)
    density = sweep_density(avail, sources, instrument_ids)

    # sweep_provenance / sweep_never_written / sweep_expiry_class are DELIBERATELY
    # NOT CALLED. They answer real questions -- who wrote these rows, which declared
    # columns are never populated, does a single-expiry relation silently change
    # class -- but none of them is THIS question, which is what per-strike gamma /
    # iv / oi / spot exists per symbol per day and how much of it.
    #
    # They are also what made this register unrunnable. sweep_provenance alone is 36
    # (relation, column) pairs at ~13 min each -- over seven hours -- and the three
    # pairs that completed on the 2026-09-14 run were eq_macro_data, eq_price_daily
    # and eq_price_daily_backup_20260618: equity tables and a dated backup, none of
    # which this register makes any claim about.
    #
    # A register that regenerates in 40 minutes gets re-run. One that takes eight
    # hours never does, and then the extent question is re-derived from scratch
    # again -- which is the exact failure this file exists to end. The functions are
    # kept, unreferenced, so a future script can lift them; §7-§9 of the register
    # say plainly what was not measured here and where it was measured instead.
    provenance = never_written = expiry_class = None

    elapsed = dt.timedelta(seconds=int(time.monotonic() - t0))
    log("-" * 78)
    log(f"requests={REQUESTS_MADE:,}  empty_list_confirmations="
        f"{EMPTY_LIST_CONFIRMATIONS:,}  unresolved={len(UNRESOLVED)}")
    _kinds = Counter(d["kind"] for d in DROPPED_SOURCES)
    log(f"dropped sources: {len(DROPPED_SOURCES)} "
        f"(unmeasured={_kinds['unmeasured']} blocks the write, "
        f"unmeasurable={_kinds['unmeasurable']} excluded by rule 6, "
        f"empty={_kinds['empty']} measured)")
    if DROPPED_SOURCES:
        log(f"DROPPED = {json.dumps(DROPPED_SOURCES, indent=2)}")
    log(f"UNRESOLVED = {json.dumps(UNRESOLVED, indent=2) if UNRESOLVED else '[]'}")

    # Method rule 2. The assertion is the point; it is checked before any write.
    if UNRESOLVED:
        log("REFUSING TO WRITE: unresolved probes outstanding. "
            "Nothing was written to the register.")
        log(f"elapsed {elapsed}")
        return 4

    ctx = {
        "today": today, "rels": rels, "sources": sources,
        "n_candidates": len(candidates), "instruments_rows": instruments_rows,
        "verdicts": verdicts, "provenance": provenance,
        "correspondence": correspondence, "dropped": DROPPED_SOURCES,
        "density": density,
        "never_written": never_written, "expiry_class": expiry_class,
        "unresolved": UNRESOLVED, "requests": REQUESTS_MADE,
        "empty_confirmations": EMPTY_LIST_CONFIRMATIONS, "elapsed": str(elapsed),
    }
    body = render(ctx)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".md.tmp")
    tmp.write_bytes(body.encode("utf-8"))
    os.replace(tmp, OUT_PATH)

    rows = sum(1 for ln in body.splitlines() if ln.startswith("|"))
    log(f"wrote {OUT_PATH}  bytes={len(body.encode('utf-8')):,}  table_rows={rows:,}")
    log(f"elapsed {elapsed}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Probe as e:
        print(f"FATAL probe failure: {e}", file=sys.stderr)
        raise SystemExit(2) from None
