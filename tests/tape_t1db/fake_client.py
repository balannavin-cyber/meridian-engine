"""Fakes for tape T1-db tests (docs/tape/T1_db_plan.md section 2). No network, no .env, no core.* import.

FakeClient records every call as (op, table, filters, n_rows, rows) and holds rows per table in memory; count_exact and
select answer from what it holds. Filters understood: {"col": "eq.<v>"} only (all the loader sends).
FakeLedger mirrors the ExecutionLog surface the loader uses.
"""


def _match(row, filters):
    for k, v in (filters or {}).items():
        if not v.startswith("eq."):
            raise AssertionError("FakeClient: unsupported filter %r=%r" % (k, v))
        if str(row.get(k)) != v[3:]:
            return False
    return True


class FakeClient:
    def __init__(self, preseed=None, drop_one_row_of=None):
        self.calls = []
        self.tables = {t: [dict(r) for r in rows] for t, rows in (preseed or {}).items()}
        self.drop_one_row_of = drop_one_row_of
        self._dropped = False

    # writes
    def insert(self, table, rows):
        rows = [dict(r) for r in (rows if isinstance(rows, list) else [rows])]
        self.calls.append(("insert", table, None, len(rows), rows))
        if self.drop_one_row_of == table and not self._dropped and rows:
            rows = rows[1:]
            self._dropped = True
        self.tables.setdefault(table, []).extend(rows)
        return None

    def upsert(self, table, rows, on_conflict=None):
        rows = rows if isinstance(rows, list) else [rows]
        self.calls.append(("upsert", table, None, len(rows), rows))
        self.tables.setdefault(table, []).extend(dict(r) for r in rows)
        return None

    def delete(self, table, filters=None):
        self.calls.append(("delete", table, dict(filters or {}), 0, None))
        keep = [r for r in self.tables.get(table, []) if not _match(r, filters)]
        self.tables[table] = keep
        return None

    # reads
    def select(self, table, columns="*", filters=None, limit=None, offset=None, order=None, ascending=True):
        self.calls.append(("select", table, dict(filters or {}), 0, None))
        rows = [r for r in self.tables.get(table, []) if _match(r, filters)]
        if order:
            rows = sorted(rows, key=lambda r: str(r.get(order)), reverse=not ascending)
        rows = rows[(offset or 0):]
        if limit is not None:
            rows = rows[:limit]
        cols = None if columns == "*" else [c.strip() for c in columns.split(",")]
        return [dict(r) if cols is None else {c: r.get(c) for c in cols} for r in rows]

    def count_exact(self, table, filters):
        self.calls.append(("count", table, dict(filters or {}), 0, None))
        return sum(1 for r in self.tables.get(table, []) if _match(r, filters))

    # views on the record
    def writes(self):
        return [c for c in self.calls if c[0] in ("insert", "upsert", "delete")]

    def inserted(self, table):
        return [r for c in self.calls if c[0] == "insert" and c[1] == table for r in c[4]]


class FakeLedger:
    instances = []

    def __init__(self, **kw):
        self.kw = kw
        self.writes = {}
        self.final = []
        FakeLedger.instances.append(self)

    def record_write(self, table, n):
        self.writes[table] = self.writes.get(table, 0) + int(n)

    def complete(self, notes=None):
        self.final.append(("complete", "SUCCESS", 0, notes))
        return 0

    def exit_with_reason(self, reason, exit_code=0, notes=None, error_message=None):
        self.final.append(("exit_with_reason", reason, exit_code, notes))
        return exit_code
