# MERDIAN Runbooks

**Purpose:** Step-by-step procedures for recurring operations. Claude consults these before asking Navin how to do something.

> **Rule for Claude:** Before asking "how do I do X?" — search this directory. If a runbook exists, follow it. If it doesn't, ask Navin **once**, then immediately write the procedure as a new runbook using `RUNBOOK_TEMPLATE.md`. Next session, read it instead of asking.

---

## Index

| Operation | Runbook | Last verified | Frequency |
|---|---|---|---|
| Rotate Dhan access token | `runbook_update_dhan_token.md` | *(fill in)* | Daily (expires overnight) |
| Update Kite broker flow | `runbook_update_kite_flow.md` | *(fill in)* | *(fill in)* |
| Restart a stuck runner (Local) | `runbook_restart_runner_local.md` | — | As needed |
| Restart a stuck runner (AWS) | `runbook_restart_runner_aws.md` | — | As needed |
| Backfill a missing trading day | `runbook_backfill_missing_day.md` | — | As needed |
| Add a new row to trading_calendar | `runbook_add_calendar_row.md` | — | Weekly (at least 1wk ahead) |
| Rotate Supabase credentials | `runbook_rotate_supabase_creds.md` | — | Quarterly |
| Recover from DhanError 401 | `runbook_recover_dhan_401.md` | — | As needed |
| Resolve Local↔AWS hash mismatch | `runbook_resolve_hash_mismatch.md` | — | As needed |
| Emergency stop live trading | `runbook_emergency_stop.md` | — | Only in emergency |

---

## When to add a new runbook

Add a runbook the **second** time an operation is done by hand. The first time is exploration; the second time is a pattern worth capturing.

Signals that an operation needs a runbook:
- You've explained it to Claude more than once
- It has a specific sequence of steps (not just "edit file X")
- It involves touching credentials, schedulers, or live systems
- Getting it wrong has real consequences

---

## What a runbook is NOT

- Not a full architecture explanation — that lives in ADRs or masters
- Not a one-time script — those are code, live in `*.py`
- Not a debug narrative — those live in session notes

A runbook is: "Do these N steps in order. Expect this outcome. If it fails, check these things."

---

*MERDIAN Runbooks index. Update the table above whenever a runbook is added, verified, or deprecated.*
