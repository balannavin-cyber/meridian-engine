# `docs/research/`

Measurement artefacts and one-off research outputs. Documents here record what was
measured and how; they are not runbooks and they do not carry recommendations.

## Scripts

### `gamma_metrics_tail_probe.py`

Records the tail of `gamma_metrics` — `min(ts)`, `max(ts)`, total row count, per-day
counts for the first 10 calendar days, and the oldest row's age in days — appending one
dated block to `docs/research/gamma_metrics_tail_<YYYY-MM-DD>.md`.

```bash
python3 /home/ssm-user/meridian-cc/docs/research/gamma_metrics_tail_probe.py
```

Read-only, no arguments, safe to run at any time. Appends rather than overwrites, so
re-running on the same day adds a second block instead of replacing the first. Exits
non-zero and writes nothing if any probe fails to resolve — a timeout is never recorded
as a count.

**Not scheduled, deliberately.** It is a watchdog, not an investigation. `gamma_metrics`
is a 90-day rolling window trimmed by **pg_cron jobid 19** (`30 12 * * *`, calling
`public.cleanup_gamma_engine_data()`), which is why no code in `meridian-engine` and no
scheduling surface on the AWS host appears to delete anything — the deleter is inside the
database. The retention predicate is `created_at`, **not** `ts`, and the two diverge by up
to a day.

Run it when a document's `gamma_metrics` row counts fail to reproduce, or after a Supabase
migration, to detect the rule changing. Read through `ts` the oldest-row age oscillates
between about 90 and 91 days — dropping when the 12:30 UTC job runs, climbing again at
midnight. A sustained climb past that band, or a total row count that stops growing on a
trading day, is the signal. See `capture_s75.md` §1 and §5.

## Documents

| file | what it measures |
|---|---|
| `data_inventory_2026-09-08.md` | every relation in schema `public`; which months can support a per-strike GEX for NIFTY and SENSEX, and from which tables |
| `flip_audit_2026-09-08.md` | `gamma_metrics.flip_level` — construction, population and stability, consumers and liveness, price behaviour at the level |
| `iv_availability_2026-09-08.md` | exact column lists for four tables; non-null coverage per month per symbol for 31 iv / straddle / volatility columns |
| `adr009_prereg_gex_zone_utility_2026-09-07.md` | pre-registration for the PIN/ACCEL zone utility study |
| `adr003_phase1_*.md` | ADR-003 phase 1 zone respect rate and availability |
| `s72_gex_view_fix.sql` | the ADR-021 scoping fix for the pin/accel views |
