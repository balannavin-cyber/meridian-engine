# S91 / AM-2 — Telegram alert-gating findings on the S52 monitor set

**Status: REPORT ONLY. Neither script in §2 or §3 was edited this session.** For filing as
TD entries at the doc-close. Measured 2026-10-07 on `i-0878c118835386ec2` from
`~/meridian-cc` (rule 24); every number below is either a crontab line, a `grep -n` line
number, or arithmetic over those two, and where a figure is derived rather than observed
it says so.

Raised by the operator's FIX B brief (Rule 22: when a defect is found in one component,
audit the parallel components written in the same pass). The S52 observability set is four
scripts deployed together — `monitor_orchestrator_health.py`,
`refresh_health_dashboard.py`, `validate_compute_contracts.py`,
`enforce_orchestrator_timeout.py` — so the question is which of the other three carry the
same ungated-send shape.

## 0. What was fixed, for contrast

`monitor_orchestrator_health.py` (**fixed this session, uncommitted**) sent
`'Orchestrator not firing'` on every one of its `*/1 * * * *` ticks while the orchestrator
it watches runs only `*/5 03-09 * * 1-5` UTC. Measured: **366** such lines in the live
`logs/monitor.log`, operator chat **4.1k unread and muted**, and the 09:10 IST wsfeed alert
(**TD-S91-NEW-3**) missed in that muted chat. Now gated on trading day AND the
orchestrator's own crontab window + a 10-min start grace, with a 30-min re-notify and one
RECOVERED on clear.

## 1. Scheduling and delivery — measured, not assumed

| Script | Schedule (`crontab -l`) | systemd unit | Spawned by the orchestrator | Telegram sends |
|---|---|---|---|---|
| `monitor_orchestrator_health.py` | `*/1 * * * *` — **24x7** | none | no | 2 sites (now gated) |
| `refresh_health_dashboard.py` | `*/1 * * * *` — **24x7** | none | no | **none** |
| `validate_compute_contracts.py` | `4,9,…,59 03-09 * * 1-5` | none | no | **4 sites** |
| `enforce_orchestrator_timeout.py` | `*/2 03-09 * * 1-5` | none | no | 1 site |

Method and what it cannot see: `crontab -l` for the current user; `systemctl
list-units --all` + `list-timers --all` + `ls /etc/systemd/system/` (the only MERDIAN units
are the four `merdian-wsfeed*` ones); `grep -n` across every `*.py` in the repo for the
three script names, which found **no call site** — so none is launched as a subprocess by
`run_merdian_shadow_runner_aws.py` or anything else in the tree. **This method cannot see**
another crontab under a different user, a hand-run invocation, or a scheduler off this box.

`refresh_health_dashboard.py` has **no `telegram_utils` import and no send** — it is a
quiet writer, and is listed only so the enumeration is complete rather than selective.

## 2. FINDING 1 — `validate_compute_contracts.py` floods on a holiday inside its window

**This is the one that matters, and it has a date.**

Four send sites, none gated on the trading calendar and none deduped:

| Line | Call | Condition |
|---|---|---|
| `:72` | `send_warning` | no `option_chain_snapshots` row in the last 5 min |
| `:104` | `send_warning` | no `market_spot_snapshots` row in the last 1 min |
| `:139` | `send_critical` | duplicate `run_id` in `gamma_metrics` |
| `:170` | `send_alert` | the `run()` summary, once per run with any violation |

The script has **no trading-day gate** (`grep -n` for `trading_calendar` / `is_trading_day`
/ `HOLIDAY` returns nothing) and **no dedupe state**. Its cron window is already
weekday-and-hours scoped, so unlike the monitor it does **not** flood overnight or at
weekends — the exposure is a **holiday that falls on a weekday**.

Arithmetic, stated as arithmetic:

* 12 runs/hour × 7 hours (03–09 UTC) = **84 runs** on a weekday.
* On a holiday the chain ingest and spot capture are gated (R0.8, S90), so
  `check_option_chain_fresh` fails first. `run()` composes the checks with
  `a() and b() and c()`, which **short-circuits**, so `:104` and `:139` never run.
* That leaves `:72` + `:170` = **2 sends per run → ~168 Telegram messages** across the
  window.

**Next occurrence: Tuesday 2026-10-20**, already on the `CURRENT.md` list as the first live
test of R0.8. The now-fixed monitor will be silent that day; this script will not be.

Two further notes:

* **In-window persistence also floods**, because there is no dedupe: a condition that
  lasts an hour sends 2 messages per 5 minutes = **24/hour**. **Derived from the cadence,
  not observed** — I did **not** verify whether these sites fired during the 09:10–09:36
  IST wsfeed outage on 2026-10-07, and should not be read as saying they did. That outage
  hit `market_ticks`/breadth; whether it reached `option_chain_snapshots` is unchecked.
* `:170`'s message reads *"Compute contracts violated — skipping this cycle"*. The script
  **does not skip anything** — it exits non-zero and the orchestrator's own cron line is
  independent of it (`*/5` vs `4,9,…`), so no cycle is skipped by this exit. That is a
  separate (and more serious) finding than the flood: the alert text asserts a control
  that does not exist. Worth its own TD row.

**Proposed fix, not applied:** the same two-gate shape as the monitor — trading day via
`core.trading_calendar_gate.is_trading_day_today` (rule 18: import it, never re-roll it),
plus a 30-min dedupe per condition key in a `logs/` state file. The window gate is already
supplied by cron here, so only the calendar gate and the dedupe are needed.

## 3. FINDING 2 — `enforce_orchestrator_timeout.py` is NOT a flood source

Recorded because the honest answer to the Rule 22 question is "one of the two, not both",
and lumping them would have overstated it.

Its **single** send (`:106`, `send_critical`) sits inside `kill_process()` and fires only
after `os.kill(pid, SIGTERM)` has actually been issued against a process measured at
>600 s. On a holiday the orchestrator carries the shared gate
(`run_merdian_shadow_runner_aws.py:46` imports it; `:345` exits via `HOLIDAY_GATE`), so it
exits in seconds, nothing hangs, no kill happens and no message is sent.

What it **does** share with the others: no trading-day gate of its own, and no dedupe. That
is a lower-severity shape here because the send is conditioned on a rare, real, destructive
event — a repeated kill alert is arguably correct behaviour, not noise. **No change
proposed.** If it is ever touched, the thing to preserve is that the send stays conditioned
on the kill rather than on the detection.

## 4. For whoever patches §2

Both files in §1's bottom two rows carry a **UTF-8 BOM** (`bom=True`, pure LF, measured).
Per `.claude/rules/python-writers.md`: read with `read_bytes().decode('utf-8-sig')` and
write with `write_bytes(...)`, or `ast.parse` will reject U+FEFF and a `write_text` will
not round-trip the BOM.

Both also contain **pre-existing mojibake** from an earlier encoding mishap — `â€”` where
an em dash belongs, in docstrings and in the `:170` message string. It is in the committed
file, it is not introduced by this session, and it should be fixed deliberately with the
BOM handling above rather than incidentally.

## 5. Owed at the doc-close

1. TD row for §2 (holiday flood, ~168 sends on 2026-10-20) — the dated one.
2. TD row for §2's `:170` message asserting a cycle-skip that does not happen.
3. TD row for the `monitor_orchestrator_health.py` flood itself (fixed, uncommitted) —
   there is currently **no** TD covering it; it was raised in the operator's brief, not
   from the register.
4. §3 recorded as audited-and-cleared, so the next Rule 22 pass does not re-derive it.
