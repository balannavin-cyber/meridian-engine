"""S90 / AM-1 replay harness — an in-memory stand-in for core.supabase_client.SupabaseClient.

Serves the frozen golden days (tests/golden/<day>_<SYMBOL>/inputs/*.csv.gz) through the same
select / count calls the live code makes, so production code runs unchanged against a past day,
offline, at any hour. Read-only by construction: there is no write method.

Supported filter grammar (what the S90 runner uses): eq. lte. gte. lt. gt. is.null — one per column,
as in the live client. Values come back as strings, timestamps in PostgREST's ISO form
(2026-10-01T03:30:07.358252+00:00), empty CSV cells as None.
"""
from __future__ import annotations

import bisect
import csv
import gzip
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# fixture file stem -> relation name
RELATIONS = {
    "ocs": "option_chain_snapshots",
    "gex_strike": "gex_strike_snapshots",
    "gamma_metrics": "gamma_metrics",
    "volatility": "volatility_snapshots",
    "spot": "market_spot_snapshots",
}
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}(:?\d{2})?|Z)$")


def _iso(v: str) -> str:
    """psql CSV timestamp -> PostgREST ISO form."""
    v = v.replace(" ", "T", 1)
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    m = re.search(r"([+-]\d{2})$", v)
    if m:
        v = v + ":00"
    # pad fractional seconds to 6 digits: psql trims trailing zeros ('.90388') and
    # datetime.fromisoformat before Python 3.11 rejects anything but 3 or 6 digits (S90, box = 3.10)
    v = re.sub(r"\.(\d{1,5})(?=[+-]\d{2}:\d{2}$)", lambda m: "." + m.group(1).ljust(6, "0"), v)
    return v


def _key(v: Optional[str]):
    """Sort/compare key: timestamps as datetimes, numbers as floats, else the string."""
    if v is None:
        return (0, "")
    if _TS.match(v):
        return (1, datetime.fromisoformat(_iso(v)))
    try:
        return (2, float(v))
    except ValueError:
        return (3, v)


class FixtureClient:
    def __init__(self, day_dirs: List[Path], extra_tables: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        self.tables: Dict[str, List[Dict[str, Any]]] = {}
        for d in day_dirs:
            for stem, rel in RELATIONS.items():
                f = Path(d) / "inputs" / f"{stem}.csv.gz"
                if not f.exists():
                    continue
                with gzip.open(f, "rt", newline="") as fh:
                    for row in csv.DictReader(io.StringIO(fh.read())):
                        clean = {k: (None if v == "" else (_iso(v) if _TS.match(v) else v)) for k, v in row.items()}
                        self.tables.setdefault(rel, []).append(clean)
        for name, rows in (extra_tables or {}).items():
            self.tables[name] = list(rows)
        self._sorted: Dict[tuple, tuple] = {}

    # ---------------------------------------------------------------- reads
    def _rows_sorted(self, table: str, col: str, eqs: tuple = ()):
        """Rows of `table` matching the eq-filters `eqs`, sorted on `col`, cached — the runner
        re-reads the same (relation, symbol) every cycle, so this turns scans into bisects."""
        k = (table, col, eqs)
        if k not in self._sorted:
            base = [r for r in self.tables.get(table, []) if all(self._match(r, c, s) for c, s in eqs)]
            rows = sorted(base, key=lambda r: _key(r.get(col)))
            self._sorted[k] = (rows, [_key(r.get(col)) for r in rows])
        return self._sorted[k]

    @staticmethod
    def _match(row: Dict[str, Any], col: str, spec: str) -> bool:
        op, _, val = spec.partition(".")
        v = row.get(col)
        if op == "is":
            return (v is None) if val == "null" else (str(v).lower() == val)
        if v is None:
            return False
        a, b = _key(v), _key(val)
        if a[0] != b[0]:  # mixed types: compare as strings (live Postgres would cast)
            a, b = (3, str(v)), (3, val)
        return {"eq": a == b, "lte": a <= b, "gte": a >= b, "lt": a < b, "gt": a > b}[op]

    def _filtered(self, table: str, filters: Dict[str, str], order: Optional[str], ascending: bool):
        filters = filters or {}
        if order:
            eqs = tuple(sorted((c, s) for c, s in filters.items() if c != order and s.startswith("eq.")))
            rows, keys = self._rows_sorted(table, order, eqs)
            lo, hi = 0, len(rows)
            spec = filters.get(order)
            if spec:  # range on the order column: bisect instead of scanning
                op, _, val = spec.partition(".")
                kv = _key(val)
                if op == "gte": lo = bisect.bisect_left(keys, kv)
                elif op == "gt": lo = bisect.bisect_right(keys, kv)
                elif op == "lte": hi = bisect.bisect_right(keys, kv)
                elif op == "lt": hi = bisect.bisect_left(keys, kv)
                elif op == "eq": lo, hi = bisect.bisect_left(keys, kv), bisect.bisect_right(keys, kv)
            cand = rows[lo:hi]
            rest = {c: s for c, s in filters.items() if c != order and (c, s) not in eqs}
        else:
            cand, rest = self.tables.get(table, []), filters
        out = [r for r in cand if all(self._match(r, c, s) for c, s in rest.items())]
        if order and not ascending:
            out = out[::-1]
        return out

    def select(self, table: str, columns: str = "*", filters: Optional[Dict[str, str]] = None,
               order: Optional[str] = None, ascending: bool = True, limit: Optional[int] = None,
               offset: int = 0, **_ignored) -> List[Dict[str, Any]]:
        out = self._filtered(table, filters or {}, order, ascending)
        out = out[offset:] if offset else out
        if limit is not None:
            out = out[:limit]
        if columns and columns != "*":
            cols = [c.strip() for c in columns.split(",")]
            out = [{c: r.get(c) for c in cols} for r in out]
        return [dict(r) for r in out]

    def count_exact(self, table: str, filters: Dict[str, str]) -> int:
        return len(self._filtered(table, filters or {}, None, True))
