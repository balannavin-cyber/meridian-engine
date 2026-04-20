-- ============================================================================
-- MERDIAN Session 2 — script_execution_log
-- Created: 2026-04-20
-- Purpose: Write-contract enforcement. Every production script writes exactly
--          one row per invocation declaring its expected vs actual writes
--          and why it exited. Silent exits become queryable; contract
--          violations become alertable.
-- Refs:    ENH-71 (write-contract layer, programme Session 2)
-- ============================================================================

create table if not exists public.script_execution_log (
    id              uuid        primary key default gen_random_uuid(),

    -- Identity
    script_name     text        not null,              -- 'capture_spot_1m.py'
    invocation_id   uuid        not null unique,       -- one per process run
    host            text        default 'local',       -- 'local' | 'aws' | 'meridian_alpha'
    symbol          text,                              -- 'NIFTY' | 'SENSEX' | null
    trade_date      date        not null,              -- IST trade date at start

    -- Lifecycle
    started_at      timestamptz not null,
    finished_at     timestamptz,                       -- null while running
    duration_ms     integer,                           -- computed on finalize

    -- Outcome
    exit_code       integer,                           -- 0 | 1 | 2 ... | null while running
    exit_reason     text        not null,              -- closed set, see check constraint
    contract_met    boolean,                           -- null while running; true/false on finalize

    -- Write accounting
    expected_writes jsonb       not null default '{}', -- {"market_spot_snapshots": 2, "hist_spot_bars_1m": 2}
    actual_writes   jsonb       not null default '{}', -- matches expected shape; populated as script runs

    -- Observability
    notes           text,                              -- short one-liner context
    error_message   text,                              -- exception/stacktrace summary if CRASH
    git_sha         text,                              -- HEAD at time of run (best-effort)

    created_at      timestamptz not null default now(),

    -- Closed set of exit reasons. Extend here when adding a new class of exit.
    constraint chk_exit_reason_valid check (exit_reason in (
        'SUCCESS',              -- Normal completion, contract met
        'HOLIDAY_GATE',         -- Trading calendar says closed; expected behavior
        'OFF_HOURS',            -- Run attempted outside market hours; expected behavior
        'TOKEN_EXPIRED',        -- Upstream API auth failure (Dhan 401, etc)
        'DATA_ERROR',           -- Upstream returned malformed/unexpected data
        'SKIPPED_NO_INPUT',     -- Nothing to process (e.g. no option chain for symbol yet)
        'DEPENDENCY_MISSING',   -- Required prior-stage output absent (cascade detection)
        'CRASH',                -- Unhandled exception
        'TIMEOUT',              -- Hit a hard timeout boundary
        'RUNNING',              -- Still in flight; finalize() not yet called
        'DRY_RUN'               -- Intentional --dry-run invocation
    ))
);

-- ── Indexes ────────────────────────────────────────────────────────────────

-- Primary lookup: "show me the last N invocations of script X"
create index if not exists idx_sel_script_ts
    on public.script_execution_log (script_name, started_at desc);

-- Dashboard rollup: "any contract violations in the last 30 min?"
-- Partial index so it stays tiny even as the table grows.
create index if not exists idx_sel_contract_fail
    on public.script_execution_log (started_at desc)
    where contract_met = false;

-- Silent-exit auditor: "any HOLIDAY_GATE / TOKEN_EXPIRED on a trading day?"
create index if not exists idx_sel_nonsuccess_by_date
    on public.script_execution_log (trade_date, exit_reason)
    where exit_reason <> 'SUCCESS';

-- Per-symbol filter for multi-symbol scripts
create index if not exists idx_sel_symbol_ts
    on public.script_execution_log (symbol, started_at desc)
    where symbol is not null;

-- Invocation lookup by id (for preflight --invocation-id matching)
-- unique constraint on invocation_id already creates an index; no extra needed.

-- ── Documentation comments ─────────────────────────────────────────────────

comment on table public.script_execution_log is
  'Write-contract audit log. Every production script writes exactly one row '
  'per invocation via core.execution_log.ExecutionLog. ENH-71. Programme Session 2.';

comment on column public.script_execution_log.invocation_id is
  'Unique per process invocation. Used by preflight --invocation-id <uuid> '
  'to match a dry-run result to the launching preflight stage.';

comment on column public.script_execution_log.expected_writes is
  'JSON object {table_name: row_count_expected}. Declared at ExecutionLog '
  'construction. Drives contract_met computation at finalize.';

comment on column public.script_execution_log.actual_writes is
  'JSON object {table_name: row_count_actual}. Incremented via record_write() '
  'calls as the script progresses. Final value compared to expected_writes.';

comment on column public.script_execution_log.contract_met is
  'TRUE only when exit_code=0 AND for every key in expected_writes, '
  'actual_writes[key] >= expected_writes[key]. Allows actual > expected '
  '(over-delivery does not violate contract).';

comment on column public.script_execution_log.exit_reason is
  'Closed set. See check constraint for current values. A non-SUCCESS reason '
  'does not necessarily mean contract_met=false (HOLIDAY_GATE is a legitimate '
  'zero-write scenario with empty expected_writes).';

-- ── Rollup view (read-only, for dashboard/alerts) ──────────────────────────
-- Last 30 minutes of activity, per script, roll up: success ratio, last reason.
create or replace view public.v_script_execution_health_30m as
    select
        script_name,
        count(*)                                            as invocations,
        count(*) filter (where contract_met)                as successful,
        count(*) filter (where not contract_met)            as failed,
        count(*) filter (where contract_met is null)        as in_flight,
        round(
            100.0 * count(*) filter (where contract_met)
            / nullif(count(*) filter (where contract_met is not null), 0),
            1
        )                                                   as success_pct,
        max(started_at)                                     as last_run,
        (array_agg(exit_reason order by started_at desc))[1] as last_exit_reason
    from public.script_execution_log
    where started_at > now() - interval '30 minutes'
    group by script_name
    order by success_pct asc nulls last, last_run desc;

comment on view public.v_script_execution_health_30m is
  'Per-script rollup of last 30 minutes. Used by dashboard Pipeline Data '
  'Integrity card and alert daemon. ENH-71.';

-- ============================================================================
-- End migration.
-- ============================================================================
