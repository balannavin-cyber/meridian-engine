"""Tape live: render sql/2026-11-06_tape_live_tables.sql (docs/tape/L0_plan.md section 5). AUTHORED, NEVER APPLIED in L0.

PURE: stdlib + the column authority services/tape_db/tape_schema.py. The two copied tables take their data columns, types,
NOT NULLs, primary key and grain from tape_schema, found by the identity of the imported cycle / event column tuples, so no
column and no source table name is typed here. tests/test_tape_live.py (guard live-sql) asserts the committed file equals
render() and, separately, parses it.

  python -m services.tape_live.cli ddl --out sql/2026-11-06_tape_live_tables.sql
"""
from merdian_compute.tape import cycle, events
from services.tape_db import tape_schema as S

PROV = (("as_of", "timestamptz"), ("live_run_id", "uuid"), ("code_sha", "text"))
ROLES = ("tape_ro", "merdian_ro")

WALL = (("symbol", "text", True), ("trading_day", "date", True), ("expiry", "date", True), ("ts_ist", "timestamptz", True),
        ("chain_run_id", "text", True), ("chain_run_ts", "timestamptz", True), ("call_wall", "numeric", False),
        ("put_wall", "numeric", False), ("call_wall_oi_call", "bigint", False), ("put_wall_oi_put", "bigint", False))
LABEL = (("symbol", "text", True), ("trading_day", "date", True), ("ts_ist", "timestamptz", True), ("wall", "text", True),
         ("rule_version", "text", True), ("strike", "numeric", False), ("leg", "text", True), ("label", "text", True),
         ("partial", "boolean", True), ("reason", "text", True), ("flags", "jsonb", True))

PURPOSE = {
    "tape_live_cycle": "Provisional 5-minute strike-leg cycle rows, upserted every cycle; data columns, key and grain are those of "
                       "the offline cycle table, generated from services/tape_db/tape_schema.py.",
    "tape_live_events": "Provisional CONC / THIN event candidates up to the cycle; upserted, and deleted when a later cycle no "
                        "longer produces them; columns from services/tape_db/tape_schema.py.",
    "tape_live_wall": "The chain run used for each 5-minute grid point T (the latest run whose timestamp floored to the grid is "
                      "<= T), its front expiry, call wall (largest oi on the CE side) and put wall (largest on the PE side) "
                      "and those two OI values.",
    "tape_live_label": "As-seen label record per wall and grid point: insert-only, first label wins (ON CONFLICT DO NOTHING), "
                       "never recomputed; services/tape_live/verify_day.py compares it with the final rows after load.",
}


def q(s):
    return "'" + s.replace("'", "''") + "'"


def _src(cols):
    return [n for n, s in S.TABLES.items() if s["cols"] is cols][0]


def copied(cols):
    src = _src(cols)
    sp, types = S.spec(src), S.db_types(src)
    prov = dict(S.PROVENANCE)
    data = [c for c in S.db_columns(src) if c not in prov]
    nn = set(sp["not_null"])
    out = [(c, types[c], c in nn) for c in data] + [(c, t, True) for c, t in PROV]
    return out, sp["pk"], sp["unique"]


def tables():
    c_cols, c_pk, c_uq = copied(cycle.CYCLE_COLS)
    e_cols, e_pk, e_uq = copied(events.EVENT_COLS)
    prov = [(c, t, True) for c, t in PROV]
    return [
        ("tape_live_cycle", c_cols, c_pk, c_uq, ()),
        ("tape_live_events", e_cols, e_pk, e_uq, ()),
        ("tape_live_wall", list(WALL) + prov, ("symbol", "trading_day", "expiry", "ts_ist"), None, ()),
        ("tape_live_label", list(LABEL) + prov, ("symbol", "trading_day", "ts_ist", "wall", "rule_version"), None,
         ("CONSTRAINT tape_live_label_wall_ck CHECK (wall IN ('call', 'put'))",
          "CONSTRAINT tape_live_label_label_ck CHECK (label IN ('HIT', 'ABSORBED', 'THINNING', 'QUIET', 'NO_READ'))",
          "CONSTRAINT tape_live_label_leg_ck CHECK (leg IN ('CE', 'PE'))")),
    ]


def table_sql(t, cols, pk, uq, checks):
    lines = ["    %-24s %s%s" % (c, ty, " NOT NULL" if nn else "") for c, ty, nn in cols]
    if pk:
        lines.append("    CONSTRAINT %s_pk PRIMARY KEY (%s)" % (t, ", ".join(pk)))
    if uq:
        lines.append("    CONSTRAINT %s_grain_uq UNIQUE NULLS NOT DISTINCT (%s)" % (t, ", ".join(uq)))
    lines += ["    " + c for c in checks]
    out = ["CREATE TABLE IF NOT EXISTS public.%s (" % t, ",\n".join(lines), ");",
           "CREATE INDEX IF NOT EXISTS ix_%s_trading_day ON public.%s (trading_day);" % (t, t)]
    out.append("COMMENT ON TABLE public.%s IS %s;" % (t, q(
        "Tape live flow-vs-book (docs/tape/tape_live_flow_vs_book_spec_v0.1.md). %s Writer: services/tape_live (W). "
        "Owner: operator. Tier: research. Rows are display only, never scored: no scoring SQL reads this relation and "
        "nothing in it is evidence under pre-registration v0.4. Provenance per row: as_of (writer clock, UTC), live_run_id, "
        "code_sha." % PURPOSE[t])))
    return "\n".join(out)


def access_sql(t):
    out = ["ALTER TABLE public.%s ENABLE ROW LEVEL SECURITY;" % t, "DO $p$ BEGIN"]
    for r in ROLES:
        out += ["  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = '%s' "
                "AND policyname = '%s_select') THEN" % (t, r),
                "    CREATE POLICY %s_select ON public.%s FOR SELECT TO %s USING (true);" % (r, t, r),
                "  END IF;"]
    out += ["END $p$;",
            "REVOKE ALL ON public.%s FROM anon, authenticated;" % t,
            "GRANT SELECT ON public.%s TO %s;" % (t, ", ".join(ROLES))]
    return "\n".join(out)


def render():
    parts = [
        "-- =====================================================================",
        "-- Tape live flow-vs-book: the four tape_live_* tables (docs/tape/L0_plan.md section 5; spec s3).",
        "-- AUTHORED, NOT APPLIED (L0). Rendered by services/tape_live/ddl.py from services/tape_db/tape_schema.py.",
        "-- Supabase SQL editor, postgres, ONE execution, in L2 only. Idempotent: IF NOT EXISTS everywhere, policies",
        "-- created only if absent, REVOKE / COMMENT re-runnable. Additive only. Display only, never scored.",
        "-- Readers: tape_ro (the /tape page path) and merdian_ro, SELECT only. No anon, no authenticated.",
        "-- =====================================================================",
        "",
        "BEGIN;",
        "",
        "DO $v$ BEGIN",
        "  IF current_setting('server_version_num')::int < 150000 THEN",
        "    RAISE EXCEPTION 'tape live: UNIQUE NULLS NOT DISTINCT needs PostgreSQL >= 15, server is %', "
        "current_setting('server_version');",
        "  END IF;",
    ]
    for r in ROLES:
        parts += ["  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '%s') THEN" % r,
                  "    RAISE EXCEPTION 'tape live: role %s does not exist; create it before this file';" % r,
                  "  END IF;"]
    parts += ["END $v$;", ""]
    for t, cols, pk, uq, checks in tables():
        parts += ["-- ---------------------------------------------------------------- %s" % t,
                  table_sql(t, cols, pk, uq, checks), "", access_sql(t), ""]
    parts += ["COMMIT;", ""]
    return "\n".join(parts)
