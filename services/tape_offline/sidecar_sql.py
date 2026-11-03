#!/usr/bin/env python3
"""Tape T1-db: render the sidecar migration from tape_schema (docs/tape/T1_db_plan.md sections 1.1-1.2).

  python services/tape_offline/sidecar_sql.py > sql/2026-11-03_tape_t1db_sidecar.sql

Deterministic. tests/test_tape_t1db.py asserts the committed file equals this output AND, separately, parses the
committed file and compares its columns and access statements with tape_schema (the parse is the guard; the equality
only proves the file was not hand-edited).
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.tape_offline import tape_schema as S  # noqa: E402

SIDE = {"tape_minute": "tape", "tape_strike_cycle": "tape", "tape_events": "tape", "tape_daily_report": "tape",
        "tape_chain_runs": "chain", "tape_chain_events": "chain"}
OWED_NOTE = {
    "completeness_pct": "OWED: pre-registration rule 4 defines completeness; that definition is not in the repo, so T1-db stores NULL rather than invent one.",
    "connects": "OWED: the T0 runner daily report does not write a connect count (T0.1). NULL, never 0.",
    "watchdog_trips": "OWED until T0.1: not in the T0 runner daily report. NULL, never 0.",
    "frame_errors": "OWED until T0.1: not in the T0 runner daily report. NULL, never 0.",
}


def q(s):
    return "'" + s.replace("'", "''") + "'"


def table_sql(t):
    sp = S.spec(t)
    cols = S.db_columns(t)
    types = S.db_types(t)
    nn = set(sp["not_null"]) | set(S.PROVENANCE_NOT_NULL)
    lines = []
    for c in cols:
        lines.append("    %-24s %s%s" % (c, types[c], " NOT NULL" if c in nn else ""))
    if sp["pk"]:
        lines.append("    CONSTRAINT %s_pk PRIMARY KEY (%s)" % (t, ", ".join(sp["pk"])))
    if sp["unique"]:
        lines.append("    CONSTRAINT %s_grain_uq UNIQUE NULLS NOT DISTINCT (%s)" % (t, ", ".join(sp["unique"])))
    out = ["CREATE TABLE IF NOT EXISTS public.%s (" % t, ",\n".join(lines), ");",
           "CREATE INDEX IF NOT EXISTS ix_%s_trading_day ON public.%s (trading_day);" % (t, t)]
    side = SIDE[t]
    other = "chain-side (tape_chain_*)" if side == "tape" else "tape-side (tape_minute, tape_strike_cycle, tape_events, tape_daily_report)"
    src = ("tape T1a/T1b offline output %s" % sp["csv"]) if t != "tape_daily_report" else \
        "runner daily_report_<day>.json + T1a g3_report.json"
    out.append("COMMENT ON TABLE public.%s IS %s;" % (t, q(
        "Tape T1-db sidecar, %s side. Source: %s. Writer: %s (offline, one load per trading day; --replace deletes "
        "the day first). Owner: operator. Tier: research (3). Pre-registration v0.2 sha256 %s: this relation is "
        "never combined with the %s relations by any view, function, trigger or loader step; the later, hashed "
        "scoring SQL is the only place the two sides meet. Provenance per row: run_id (= script_execution_log.run_id "
        "of the load), code_sha (git rev-parse HEAD at load), source, config_version (OWED, NULL), loaded_at (UTC). "
        "Plan: docs/tape/T1_db_plan.md." % (side, src, S.WRITER, S.PREREG_SHA, other))))
    out.append("COMMENT ON COLUMN public.%s.config_version IS %s;" % (
        t, q("OWED: no tape config version exists yet; NULL until one is defined. Never a placeholder.")))
    if t == "tape_daily_report":
        for c in S.DAILY["owed"]:
            out.append("COMMENT ON COLUMN public.%s.%s IS %s;" % (t, c, q(OWED_NOTE[c])))
    if t == "tape_chain_runs":
        out.append("COMMENT ON COLUMN public.tape_chain_runs.chain_run_id IS %s;" % q(
            "chain_runs.csv run_id (the chain / gamma run), renamed so it cannot be read as the load's provenance run_id."))
    if t == "tape_minute":
        out.append("COMMENT ON COLUMN public.tape_minute.minute_ist IS %s;" % q(
            "tape_minute.csv minute (HH:MM, IST) on trading_day, stored as <day>T<HH:MM>:00+05:30."))
    if sp["unique"] and not sp["pk"]:
        out.append("COMMENT ON CONSTRAINT %s_grain_uq ON public.%s IS %s;" % (t, t, q(
            "Grain. No PRIMARY KEY: FUT rows carry NULL strike and expiry, so no NOT NULL natural key exists. "
            "NULLS NOT DISTINCT makes two FUT rows at one grain a violation.")))
    elif sp["unique"]:
        out.append("COMMENT ON CONSTRAINT %s_grain_uq ON public.%s IS %s;" % (t, t, q(
            "Plan grain kept as a constraint (FUT rows have NULL strike / expiry, so it cannot be the PK). Also "
            "asserts no two instrument tokens map to one strike-leg on a day.")))
    return "\n".join(out)


def access_sql(t):
    return "\n".join([
        "ALTER TABLE public.%s ENABLE ROW LEVEL SECURITY;" % t,
        "DO $p$ BEGIN",
        "  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = '%s' "
        "AND policyname = 'merdian_ro_select') THEN" % t,
        "    CREATE POLICY merdian_ro_select ON public.%s FOR SELECT TO merdian_ro USING (true);" % t,
        "  END IF;",
        "END $p$;",
        "REVOKE ALL ON public.%s FROM anon, authenticated;" % t,
        "GRANT SELECT ON public.%s TO merdian_ro;" % t,
    ])


def render():
    parts = [
        "-- =====================================================================",
        "-- Tape T1-db: sidecar tables (docs/tape/T1_db_plan.md sections 1.1-1.2).",
        "-- AUTHORED, NOT APPLIED. Rendered by services/tape_offline/sidecar_sql.py from tape_schema.py.",
        "-- Supabase SQL editor, postgres, ONE execution. Idempotent: IF NOT EXISTS everywhere, policies",
        "-- created only if absent, REVOKE/GRANT/COMMENT re-runnable. Additive only.",
        "-- When the editor offers to enable RLS: the DDL already enables it WITH a merdian_ro policy",
        "-- (ADR-031 D6) - either answer leaves the same end state (S90 precedent).",
        "-- Pre-registration v0.2 sha256 %s." % S.PREREG_SHA,
        "-- Post-apply check: services/tape_offline/check_tape_access.sql.",
        "-- =====================================================================",
        "",
        "BEGIN;",
        "",
        "DO $v$ BEGIN",
        "  IF current_setting('server_version_num')::int < 150000 THEN",
        "    RAISE EXCEPTION 'tape T1-db: UNIQUE NULLS NOT DISTINCT needs PostgreSQL >= 15, server is %', "
        "current_setting('server_version');",
        "  END IF;",
        "END $v$;",
        "",
    ]
    for t in S.ORDER:
        parts += ["-- ---------------------------------------------------------------- %s" % t, table_sql(t), "",
                  access_sql(t), ""]
    parts += ["COMMIT;", ""]
    return "\n".join(parts)


PRIVS = "SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER"


def render_access_check():
    """services/tape_offline/check_tape_access.sql: one execution, acting role carried in the same result set (S84)."""
    sel = []
    for t in S.ORDER:
        sel.append("""SELECT '{t}' AS relation,
       current_user::text AS role_now,
       (SELECT count(*) FROM public.{t}) AS rows_readable_by_ro,
       c.relrowsecurity AS rls,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = '{t}') AS policies,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = '{t}'
           AND p.cmd = 'SELECT' AND p.roles = '{{merdian_ro}}'::name[] AND p.qual = 'true') AS ro_select_policies,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_has_select,
       has_table_privilege('anon', c.oid, '{privs}') AS anon_any,
       has_table_privilege('authenticated', c.oid, '{privs}') AS authenticated_any
FROM pg_class c WHERE c.oid = 'public.{t}'::regclass""".format(t=t, privs=PRIVS))
    body = "\nUNION ALL\n".join(sel)
    return "\n".join([
        "-- Tape T1-db post-apply access check (docs/tape/T1_db_plan.md section 1.2).",
        "-- Rendered by services/tape_offline/sidecar_sql.py. Supabase SQL editor, postgres, ONE execution:",
        "-- the role switch and the reads must share one execution (the editor opens a new session per run, S84).",
        "-- Fails LOUDLY (permission denied) if merdian_ro cannot read a table. A 0 row count is not a failure",
        "-- before the first load: the read proves privilege, not data. role_now must read merdian_ro or every",
        "-- PASS below is void. One line per table, ending ACCESS PASS / ACCESS FAIL (<reasons>).",
        "BEGIN;",
        "SET LOCAL ROLE merdian_ro;",
        "SELECT relation || ' ' || CASE WHEN role_now = 'merdian_ro' AND rls AND policies = 1 AND ro_select_policies = 1",
        "         AND ro_has_select AND NOT anon_any AND NOT authenticated_any THEN 'ACCESS PASS'",
        "       ELSE 'ACCESS FAIL (' || concat_ws(', ',",
        "         CASE WHEN role_now <> 'merdian_ro' THEN 'role_now=' || role_now END,",
        "         CASE WHEN NOT rls THEN 'rls off' END,",
        "         CASE WHEN policies <> 1 THEN 'policies=' || policies END,",
        "         CASE WHEN ro_select_policies <> 1 THEN 'no single merdian_ro SELECT USING (true) policy' END,",
        "         CASE WHEN NOT ro_has_select THEN 'merdian_ro lacks SELECT' END,",
        "         CASE WHEN anon_any THEN 'anon has a privilege' END,",
        "         CASE WHEN authenticated_any THEN 'authenticated has a privilege' END) || ')' END AS verdict,",
        "       role_now, rows_readable_by_ro, rls, policies, ro_select_policies, ro_has_select, anon_any, authenticated_any",
        "FROM (",
        body,
        ") x",
        "ORDER BY relation;",
        "COMMIT;",
        "",
    ])


if __name__ == "__main__":
    sys.stdout.reconfigure(newline="\n")
    if sys.argv[1:] == ["--access-check"]:
        sys.stdout.write(render_access_check())
    else:
        sys.stdout.write(render())
