# S92 dev starter — written at the S91 / AM-2 close (2026-10-08)

> Read `CLAUDE.md` then `docs/session_notes/CURRENT.md` first. This file is the **ordered
> work list**, not a second copy of session state. Where it names a number, that number was
> measured at the S91 close and is cited to the file that holds it.

---

## 0. VERIFY FIRST — four things shipped at S91 and NONE of them is verified

This is the whole point of the section order. S91 deployed two fixes, inherited a third
deployed-but-unrun fix, and published a forecast. **A fix with no watcher has a half-life**,
and today is the first day any of it meets a live cycle. Do this before opening new work.

| When (IST) | Check | PASS looks like | Closes |
|---|---|---|---|
| **09:05–09:25** | `gex_cycle_history` front leg vs `gamma_metrics` | **77 of 77** cycles, not 64 | **TD-S91-NEW-1** |
| **after 15:30** | orchestrator contract-met rate for the day | **≈ 75 %** (63/84) against 54.8 % on 10-07 | the S91 forecast |
| **16:10** | `market_spot_session_markers` row for today, **written by cron** | a row exists, `capture_quality` not `MISSING` on the open leg | **TD-S91-NEW-2** site 2 on the live path |
| **end of day** | Telegram volume — **after unmuting the chat** | **≈ 14 in-session sends**, **zero** overnight | **TD-S91-NEW-12** |

**Three cautions, each of which has already cost something:**

1. **The 75 % is a PREDICTION, not a result.** It comes from a per-cycle overlap measured on
   10-07 (`scratch/s91/basis_context_findings_S91.md` §6.1): 38 failing cycles = 11 basis-only
   + 17 write_gex-only + 10 both, so 21 still fail and 17 go clean. **If the day does not land
   near 75 %, do not adjust the forecast — find out why.** Either `bcadfa6` is not doing on
   the box what it did offline, or a third cause exists that 10-07's log does not contain.
2. **Unmute the chat, or TD-S91-NEW-12 stays unproven.** The fix removes the flood; it cannot
   prove the channel is readable. The whole finding was that an instrumented, unreadable
   channel reports as healthy.
3. **TD-S91-NEW-1 has run against zero cycles.** Its fix was pulled at 12:23:53 UTC on 10-07
   and the last cycle of that day was 09:55 UTC, so **every one of its 34 logged failures
   predates the deploy**. 10-07's log is evidence about the old artefact and must not be cited
   as verification.

## 1. Two operator rulings owed

| Ruling | Why it is blocking | Source |
|---|---|---|
| **`SKIPPED_NO_INPUT` → exit 0** | **12 orchestrator cycles are marked failed every trading day by construction** — futures capture starts 09:30 IST, the orchestrator starts 08:30, and one failing step fails the whole cycle. The mechanism is fully settled; the fix is a ruling, not an investigation. It is the **largest single remaining contributor** to the non-zero rate, ahead of the 9 undiagnosed cycles. | **TD-S91-NEW-15** |
| **Doc Protocol v5** | Drafted at S90, still not ruled. The S90 close went out "hybrid" pending it. | `docs/operational/MERDIAN_Documentation_Protocol_v5_DRAFT.md` |

## 2. The basis discriminating read — one query, no fix

**TD-S91-NEW-6** is diagnosed to a code path and **open between two mechanisms**, and the
cheap read that separates them has not been run.

* Capture the **raw `ts` strings PostgREST returns** for the newest `index_futures_snapshots`
  row **per symbol**, across several cycles, and record the **fraction widths**. Also check
  whether the column is **nullable**.
* **Fraction hypothesis predicts widths in {1, 2, 4, 5}. NULL hypothesis predicts a null at
  `rows[0]`** (`order=ts.desc` is NULLS FIRST in PostgreSQL).
* **Do not** ship the padding and call the rate drop a diagnosis — a null-driven residue would
  look like an incomplete fix. Padding is correct on its own merits either way; it is simply
  not an answer to this question.
* The arithmetic that makes this necessary: observed 12.5 % matches the **single**-timestamp
  failure rate of 9.91 %, but the code path needs **both** symbols in one cycle, p = 0.98 %,
  **P(X ≥ 9) = 4.14 × 10⁻⁸**. The rate agreement is not evidence.

## 3. Dated and non-negotiable

| Date | Item |
|---|---|
| **before Tue 2026-10-20** | **`validate_compute_contracts.py`** (**TD-S91-NEW-13**) — ~168 Telegram messages on a weekday holiday, and 10-20 is the next one. Same fix shape as `6a5c0e2`: calendar gate + 30-min dedupe. **TD-S91-NEW-14** travels with it — `:170` announces a cycle skip that never happens, so gating the volume alone leaves every surviving message asserting a control that does not exist. The file has a **UTF-8 BOM** and pre-existing mojibake; read/write bytes per `.claude/rules/python-writers.md`. |
| **~Tue 2026-10-13** | Drop the S90-H backup tables after a clean week (**TD-S90-NEW-11**). |
| **Tue 2026-10-20** | First live test of **R0.8**: no chain rows written, `cycle_health` **CLOSED** (**TD-S89-NEW-1** closes on it). Note the ordering — TD-S91-NEW-13 must land **before** this date, or the holiday that tests R0.8 also floods the alert channel. |

## 4. Built-design, not built

* **08:40 IST Zerodha early-mode preflight** (**TD-S91-NEW-3**). Design agreed; **not built**.
  It must **exercise** the token, not check its presence — a presence check cannot fail for the
  reason the 09:10–09:36 outage names. Note the incident's own lesson first: the alert **fired**
  and was lost to a muted chat, so this guard is no longer the *first* thing owed on that entry.

## 5. Open work, roughly in the order the roadmap has it

1. **Stage B** of the agentic layer.
2. **R1.10 scrip-map sync (ROADSTAR)**.
3. **`build_ict_htf_zones` re-run**.
4. **Marketview Pin / Flows — a parallel session**, by operator intent; not folded into this one.
5. **NIFTY L9 stage-1 max-pain arm** (**TD-S80-NEW-1**) — owed since S82, carried through
   S85–S91. **Pre-register before any read.**
6. **Remaining TD-S91-NEW-2 sites: 1, 3, 4, 5, 6, 7**, and the shared `core/` timestamp helper,
   which is the actual fix rather than the seventh patch.
   **Any re-sweep must walk the orchestrator's step list as well as `aws_crontab.txt`** — site 7
   (`compute_basis_context_local.py:61`) was invisible to the original grep for exactly that
   reason, and that scope gap is more transferable than the site.
7. **ENH-98** — T1 is cleared and the build is still not started. Open: **NIFTY `r_eff` 3.08 %**
   against **T3's definition**, which ties into the `r_sess`/`r_eff` split (**TD-S89-NEW-3**).
   The L7/L8 views were **never created**, so the S89 pre-committed DROP is moot, not discharged.

## 6. Carried unresolved, with a named next step each

| Item | Next step |
|---|---|
| **TD-S91-NEW-16** — the stray `equity_eod` cursor writer recurred 10-07 17:28 IST (cursor 750 → 950) and its requests failed Dhan auth **401 / DH-901** | Search **API Gateway logs for 11:57–11:59 UTC** to attribute the caller. The 401 is a sharper handle than S90 had: the host holds credentials that **used to work**, so it is one of ours and has not been re-provisioned. Re-run the elimination rather than inheriting S90's. |
| **TD-S91-NEW-17** — `check_kite_auth.py` is cited by the Topology and a runbook and **does not exist** | Correct both to `bin/wsfeed_preflight.sh`, and say in the same sentence what that script does and does not exercise. |
| **TD-S91-NEW-18** — `MISSING_CLOSE_1530` every day; no spot rows 15:25–16:00 IST | Choose between extending spot capture to 15:25–15:40 (ADR-022 D1 deliberately did **not**) or re-anchoring `get_close_1530` onto the CAS close already captured. **(b) reads an existing source**, but changes what the column means — say so. **Do not widen the window until the source is chosen.** |
| **TD-S91-NEW-7** — PID 403716 unattributed | A kill and a clean exit cannot both describe one process. Left as unexplained rather than explained away. |
| **TD-S91-NEW-5** — `breadth_indicators_daily:ALL` gate stands **failed, deliberately** | Re-derive `freshness_sla_min` from the **measured** Dhan EOD lag and write the derivation beside the number. **Do not widen the row to make a day pass.** |

## 7. Two habits this session paid for twice

Recorded here because the S92 session will be tempted by both.

1. **Replay before estimating, when a replay exists.** The monitor fix was nearly shipped
   half-done on an estimate of "≈14 sends" for one key alone; it measures **93**. The estimate
   happened to equal what the *combined* fix delivers, so it would have read as confirmation.
   **§D.47.3.**
2. **A relayed constraint is a hypothesis, not a measurement.** An advisory "`merdian_ro` is
   RLS-blind to `script_execution_log`" was accepted untested and promoted into a filed
   contradiction against `CURRENT.md`; both were wrong and the contradiction was withdrawn.
   The cost of testing it was one correctly-formed command. **§D.47.2.**
