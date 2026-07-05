# Health board — add the ambient writers to the tracked registry — Lovable prompt

**Paste into the `meridian-connect` Lovable project.** One change to the **Health** page. Read-only.

## Context

The Health page's "Writer Freshness — Last Success Per Script" board tracks a curated set of writers
(the Cadence / Host columns and the "N / N tracked" count come from that list, not purely from the
`script_execution_log` freshness data). Three new writers — the ENH-116 ambient loop — now log to
`script_execution_log` (via `v_script_execution_health_30m`, which groups by `script_name`), but they
don't appear on the board because they aren't in the tracked registry. Add them.

## What to add

Append these three entries to the tracked-writers list/registry that drives the Health board (same
place the existing entries like `compute_gamma_metrics_local.py` and `ingest_participant_positioning.py`
are declared). Match the shape of the existing entries — `script_name`, expected `cadence`, `host`:

| script_name                          | cadence | host | notes |
|--------------------------------------|---------|------|-------|
| `compile_market_environment_local.py`| 24h     | aws  | evening compiler, cron 16:00 UTC Mon–Fri |
| `relate_ambient_to_open_local.py`    | 24h     | aws  | pre-market reconciler, cron 03:55 UTC Mon–Fri |
| `accrue_expiry_outcomes.py`          | 24h     | aws  | forward-accrual labeler, cron 16:15 UTC Mon–Fri (heartbeats daily; only writes on expiry days) |

All three are daily cron writers on AWS, so the freshness check should treat "healthy" as a successful
run within ~24h (same as the existing 24h-cadence entries like `build_ict_htf_zones.py` /
`local_token_refresh`). Nothing else about the board changes — they'll read RED until their first cron
run logs, then flip green.

One display note for `accrue_expiry_outcomes.py`: it runs daily but only *writes rows* on expiry days;
on non-expiry days it logs a successful zero-write heartbeat. So judge its freshness on **last run**
(last `script_execution_log` row), not last write — otherwise it would look stale between expiries.

## Constraint

Read-only, existing data. This adds three registry entries and nothing else.

Deploy unchanged: `cd ~/meridian-connect && git pull && npm install && npm run build && sudo rsync -av --delete dist/ /var/www/marketview/ && sudo systemctl reload nginx`.
