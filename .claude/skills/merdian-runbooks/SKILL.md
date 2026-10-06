---
name: merdian-runbooks
description: Find and follow the MERIDIAN runbook for a recurring operation - token rotation, runner restart, backfill, hash mismatch, DhanError 401, calendar rows, emergency stop, disk-full lockout. Use when the user asks how to perform an operational procedure, or when a runner, token or feed needs recovery.
---

# MERIDIAN runbooks

Relocated verbatim from `CLAUDE.md` at Session 86 (ADR-028).

| I need to… | Runbook |
|---|---|
| Rotate the Dhan access token | `docs/runbooks/runbook_update_dhan_token.md` |
| Update the Kite broker flow | `docs/runbooks/runbook_update_kite_flow.md` |
| Verify Kite auth before market open | `docs/runbooks/runbook_update_kite_flow.md` Step 3 — runs `/home/ssm-user/meridian-engine/check_kite_auth.py` (persisted Session 10) |
| Restart a stuck runner (Local) | `docs/runbooks/runbook_restart_runner_local.md` |
| Restart a stuck runner (AWS) | `docs/runbooks/runbook_restart_runner_aws.md` |
| Backfill a missing trading day | `docs/runbooks/runbook_backfill_missing_day.md` |
| Resolve Local↔AWS hash mismatch | `docs/runbooks/runbook_resolve_hash_mismatch.md` |
| Recover from DhanError 401 | `docs/runbooks/runbook_recover_dhan_401.md` |
| Add a row to trading_calendar | `docs/runbooks/runbook_add_calendar_row.md` |
| Emergency stop live trading | `docs/runbooks/runbook_emergency_stop.md` |
