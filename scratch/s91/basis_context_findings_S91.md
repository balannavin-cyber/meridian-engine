# S91 / AM-2 — why the orchestrator logged `exit_code != 0` on 2026-10-07

**Status: REPORT ONLY. No code was changed by this investigation.** For filing at the
doc-close. Read-only throughout: `logs/orchestrator.log` on the box, the repo sources, and
an operator-run `script_execution_log` query.

**Environment at the time of writing:** local `HEAD` = `origin/main` = engine tree `HEAD`
= **`6a5c0e2`**, 0 ahead / 0 behind — measured, so the CLAUDE.md rule 2 hash equality
holds. The two S91 fixes (`b48532e` marker `parse_ts`, `6a5c0e2` orchestrator monitor) are
pushed and on the box.

---

## 1. How the exit code is computed

`run_merdian_shadow_runner_aws.py`: `sys.exit(main())` at `:389`. `main()` returns
`_ledger_close(led, 1, "DATA_ERROR", error="failed steps: " + …)` at `:384` whenever
`execute_pipeline()` returns False. A step is False on subprocess `returncode != 0`
(`:165`), `TimeoutExpired` (`:174`) or any exception (`:177`).

**There is no partial-success grading: one failing step fails the whole cycle.** That
single fact is what turns a per-step defect into a non-zero orchestrator exit, and it is
why two unrelated step defects below produce one undifferentiated signal.

The `failed steps: …` list goes into the ledger's `error_message`, **not** into
`orchestrator.log` — so `grep "failed steps"` on the log returns 0 and tells you nothing.
The per-step `"{label} FAILED (exit code N)"` line is the log-side signal.

## 2. The day, measured

`logs/orchestrator.log` covers 2026-10-07 only and holds **84 cycles** — exactly the 84
starts of `*/5 03-09 * * 1-5`. **46 contract-met, 38 contract-not-met.** Three failing
steps, 55 step-failures, so some cycles failed on more than one.

| Step | n | first (UTC) | last (UTC) |
|---|---|---|---|
| `compute_basis_context NIFTY+SENSEX` | 21 | 03:01 | 09:26 |
| `write_gex_cycle_history SENSEX` | 20 | 03:05 | 09:40 |
| `write_gex_cycle_history NIFTY` | 14 | 03:30 | 09:00 |

### 2.1 `write_gex_cycle_history` — diagnosed, fixed, and NOT verifiable from this log

Captured stderr, verbatim:

```
File ".../write_gex_cycle_history_local.py", line 87, in _ist_date
  return datetime.fromisoformat(ts_iso.replace("Z", "+00:00")).astimezone(IST).date()
ValueError: Invalid isoformat string: '2026-10-07T09:35:06.36058+00:00'
```

A 5-digit fraction — **TD-S91-NEW-1** exactly, at line **87**, which is the *pre-fix* body.

| Fact | Value |
|---|---|
| Box pulled `67a91ce` (contains `bcadfa6`, the `_ist_date` fix) | **12:23:53 UTC** |
| `write_gex_cycle_history_local.py` mtime | **12:23:53 UTC** (matches the pull) |
| `_norm_frac` in the running file | present ×2; `_ist_date` now at line 101 |
| Last failure of this step | **09:40 UTC** |

All 34 failures **predate the deploy by ≥ 2 h 43 m**, and the orchestrator's last cycle of
the day (09:55 UTC) also predates it. So the fix is live with **zero cycles run against
it**; the first real test is the 03:00 UTC (08:30 IST) cycle on the next trading day.
**Today's log is evidence about the old artefact and cannot verify the new one.**

## 3. `compute_basis_context` — 21 failures = 12 + 9

Classified by each failure's **own** captured stdout, and independently confirmed by the
operator's `script_execution_log` read. The two agree.

| IST | UTC | stdout | ledger `exit_reason` |
|---|---|---|---|
| 08:31 | 03:01 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 08:36 | 03:06 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 08:41 | 03:11 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 08:46 | 03:16 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 08:51 | 03:21 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 08:59 | 03:29 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 09:01 | 03:31 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 09:06 | 03:36 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 09:11 | 03:41 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 09:16 | 03:46 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 09:21 | 03:51 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 09:26 | 03:56 | `Skipping` ×2 | `SKIPPED_NO_INPUT` |
| 09:41 | 04:11 | **banner only** | `DATA_ERROR`, `statuses=no_rows` |
| 10:26 | 04:56 | **banner only** | `DATA_ERROR`, `statuses=no_rows` |
| 10:56 | 05:26 | **banner only** | `DATA_ERROR`, `statuses=no_rows` |
| 11:02 | 05:32 | **banner only** | `DATA_ERROR`, `statuses=no_rows` |
| 13:02 | 07:32 | **banner only** | `DATA_ERROR`, `statuses=no_rows` |
| 13:46 | 08:16 | **banner only** | `DATA_ERROR`, `statuses=no_rows` |
| 14:26 | 08:56 | **banner only** | `DATA_ERROR`, `statuses=no_rows` |
| 14:32 | 09:02 | **banner only** | `DATA_ERROR`, `statuses=no_rows` |
| 14:56 | 09:26 | **banner only** | `DATA_ERROR`, `statuses=no_rows` |

**TD-S91-NEW-6 says "exits 1 every cycle". That is REFUTED: 21 of 84 = 25 %**, and it is
two distinct mechanisms, not one.

### 3.1 Why the 9 are silent

`compute_basis_context_local.py` has exactly one process exit (`sys.exit(main())`, `:299`),
and every `return 1` inside `main()` goes through `log.exit_with_reason(...)`, which writes
the reason and `error_message` to `script_execution_log` and **prints nothing**. Of the
per-symbol statuses, **`no_rows` is the only one set without a `print`** — `no_input`
prints `Skipping {symbol}: no recent index_futures_snapshots rows.`, and the fetch/compute
failures print `[ERR] …`. So "banner only" uniquely identifies `no_rows` for *both*
symbols, which is what the ledger independently says.

### 3.2 `no_rows` ⟺ `parse_ts` returned None — the exact path

`compute_for_symbol` returns `None` at only two places:

* `:164` — `if not rows: return None`. **Unreachable from `main()`**, which already does
  `if not rows: … no_input; continue` before calling it.
* `:168` — `if now_ts is None: return None`, where `now_ts = parse_ts(rows[0]["ts"])`.

Therefore, **with input present**:

> `per_symbol_status[symbol] == 'no_rows'` ⟺ `parse_ts(rows[0]["ts"])` returned `None`

with two sub-branches: a **falsy `ts`** (`:62`, `if not value`) or **`fromisoformat`
raising** (`:70`, `except Exception`).

And `DATA_ERROR` needs `out_rows` empty, so **both** symbols must land there: if NIFTY is
`no_rows` and SENSEX is `ok`, one row upserts and the cycle exits **0**.

### 3.3 `parse_ts` lacks the fraction padding — a SEVENTH TD-S91-NEW-2 site

`compute_basis_context_local.py:61-71`:

```python
def parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None
```

`grep -c "ljust(6\|_norm_frac\|_FRAC"` → **0**. Same shape as the two fixed in `bcadfa6`
and the one fixed in `b48532e`. **This file is on neither of TD-S91-NEW-2's lists** —
not among the six named sites, not among the "already safe, measured not assumed" set.
That is a gap in the register's own enumeration, which matters more than the site itself:
the list was presented as the result of a grep across every `.py` in
`docs/registers/aws_crontab.txt`, and this script is reached as an orchestrator **step**,
not as its own cron line.

### 3.4 The joint-probability result — the hypothesis is NOT confirmed as stated

Python 3.10's `fromisoformat` accepts fraction widths {0, 3, 6} only. Over uniform
microseconds, PostgREST having trimmed the trailing zeros:

| width | count | parses |
|---|---|---|
| 6 | 900,000 | yes |
| 5 | 90,000 | **NO** |
| 4 | 9,000 | **NO** |
| 3 | 900 | yes |
| 2 | 90 | **NO** |
| 1 | 9 | **NO** |
| 0 | 1 | yes |

**P(one timestamp unparseable) = 0.099099 = 9.91 %.** So "1 in 10" is right.

Cycles with futures input available = 84 − 12 = **72**. Observed `DATA_ERROR` = **9**
(12.5 %).

| | p / cycle | expected over 72 | observed | P(X ≥ 9) |
|---|---|---|---|---|
| **one** symbol fails | 0.099099 | 7.14 | 9 | **0.282** — ordinary |
| **both** fail *(what §3.2 requires)* | 0.009821 | 0.71 | 9 | **4.14 × 10⁻⁸** |

The observed rate matches the **single**-timestamp rate almost exactly — but the code
requires **both** symbols to fail in the same cycle, and under independence that is
refuted at 4 × 10⁻⁸.

**So the padding defect is real and present, and its per-timestamp rate is the right
magnitude, yet that agreement is not evidence for it.** Accepting it would be fitting the
magnitude while ignoring a factor of 13 in the joint probability — the §0a.3 discipline
(compute the binomial tail before believing the cell) applied to a result that *favours*
the hypothesis rather than one that looks too good. One further claim is needed and is
**untested**: that the two symbols' newest timestamps are **correlated**.

### 3.5 Two correlation candidates, neither asserted

1. **A shared or vendor-derived `ts`.** If both rows carry one instant (a single vendor
   quote timestamp rather than two independent capture clocks) the joint rate collapses to
   the single rate and everything fits. `capture_index_futures_snapshot_local.py` runs as
   **two separate cron invocations** at the same `*/5` minute, so this needs checking, not
   assuming.
2. **NULL `ts`, with no fraction involved at all.** `order=ts.desc` in PostgreSQL is
   **NULLS FIRST** by default, so one NULL-`ts` row anywhere in the 30-minute window lands
   at `rows[0]` and `parse_ts` returns `None` via the `if not value` branch at `:62`. A
   vendor hiccup would hit both symbols in the same cycle — exactly the correlation the
   data demands. **The signature is identical to the fraction defect**: silent `no_rows`,
   both symbols, `DATA_ERROR`. Nothing observed so far distinguishes the two.

**Discriminating read (one query, no fix):** capture the raw `ts` strings PostgREST returns
for the newest `index_futures_snapshots` row per symbol across several cycles and record
the fraction widths, and check whether the column is nullable.
*The fraction hypothesis predicts widths in {1, 2, 4, 5}; the NULL hypothesis predicts a
null at `rows[0]`.*

Note for whoever fixes it: padding `parse_ts` is correct on its own merits regardless of
which mechanism dominates — it is the same defect as three already shipped — but it would
**not** touch the NULL branch. Shipping the padding and watching whether the
`DATA_ERROR` rate goes to ~0 is itself a discriminator, and a weaker one than the read
above, because a null-driven residue would look like an incomplete fix.

## 4. The 12 — `SKIPPED_NO_INPUT`, and whether exit 1 is deliberate

**Mechanism, fully determined.** Futures capture runs `*/5 04,05,06,07,08,09 * * 1-5` UTC
= **09:30 IST onward**; the orchestrator starts 03:00 UTC = **08:30 IST**. `LOOKBACK_MIN`
is 30, so for the first 12 cycles of every trading day there are no
`index_futures_snapshots` rows inside the window at all. Both symbols read `no_input`,
`out_rows` is empty, `all(s == "no_input")` holds, and the step returns
`SKIPPED_NO_INPUT` with `exit_code=1` — which fails the cycle (§1).

**Deliberate at the keystroke: yes.** `ExecutionLog.exit_with_reason`'s signature defaults
to `exit_code: int = 0`, and both call sites pass `1` **explicitly** —
`compute_basis_context_local.py`, and `run_merdian_shadow_runner_aws.py:364`. The same
orchestrator file uses **0** for `HOLIDAY_GATE` at `:347`, so the author is distinguishing
"market closed, nothing to do" from "input missing" on purpose.

**Deliberate as a system outcome: it does not look like it.** The consequence is **12
guaranteed non-zero orchestrator cycles every trading day, by construction**, and in both
the exit code and the ledger they are **indistinguishable from a real data error**. This
is the same class as the monitor flood recorded in
`scratch/s91/telegram_flood_findings_S91.md`: a daily structural false failure that trains
every reader and every downstream check to discount the signal. Note that
`monitor_orchestrator_health.py` alerts on `exit_code != 0`, so pre-S91 these 12 cycles
were a Telegram source too.

**Not verified:** whether `exit_code=1` on `SKIPPED_NO_INPUT` is the house convention at
every call site in the repo. The survey was started and not finished.

## 5. The selection / tolerance logic (`compute_for_symbol:163-217`)

| Constant | Value | Role |
|---|---|---|
| `LOOKBACK_MIN` | 30 | fetch `ts >= now-30m`, `order=ts.desc`, `limit=200` |
| `WINDOW_MIN` | 15 (`MERDIAN_BASIS_VELOCITY_WINDOW_MIN`) | `target_ts = now_ts - 15m` |
| `MIN_GAP_MIN` | 5 (`MERDIAN_BASIS_MIN_GAP_MIN`) | candidates closer than 5m to `now` rejected |

`now_row = rows[0]` (newest). The prev-row search (`:181-191`) walks `rows[1:]`, skips
anything within `MIN_GAP`, and keeps the row minimising `|r_ts - target_ts|` —
**nearest-wins with NO maximum distance**. A 29-minute-old row is accepted if it is the
only candidate; `window_min` stores the **actual** gap rather than the target, so the
written row is self-describing on this point.

**The asymmetry that matters: `prev_row is None` is not a failure.** `basis_velocity_pp`
and `spot_delta` stay `None`, `classify` returns `None`, and the row is still emitted with
`context_label` NULL. So the tolerance half **fails soft to a NULL label** while the only
hard failure in the function is the unparseable newest `ts`. Any consumer reading
`context_label` must treat NULL as "not measured", not as NEUTRAL (the ADR-018 D2 /
"NULL is a gap, never a zero" shape).

Minor fragility, noted in passing and not a defect today: `prev_ts_sel` (`:191`) is bound
only inside the loop and read only under the `if prev_row is not None` guard (`:195-202`).
Correct as written; an `UnboundLocalError` the moment that guard is moved or widened.

## 6. Method, and what it cannot see

* `orchestrator.log` captures a failing step's **stdout at DEBUG and stderr at ERROR**
  (`:161-168`), which is why §2.1 has a traceback and §3 has silence — the silence is
  itself the measurement.
* Log stamps are ISO with microsecond fractions (`[2026-10-07T03:00:07.018712+00:00]`);
  IST conversions above are +05:30 applied to those.
* Error text was redacted for URLs / JWT-shaped strings before anything was printed
  (Rule 19), and no environment value was read or emitted.
* **Per-cycle overlap: computed, see §6.1.** (This bullet previously read "not computed —
  at most 21"; the bound was right and the figure is now measured at exactly 21.)
* **Cannot see:** whether any of these steps is also invoked outside the orchestrator;
  only the orchestrator's own log was read.

### 6.1 Per-cycle overlap between the two step families

Cycles delimited by `Shadow Runner starting`; 84 cycles parsed, verdicts 46 met / 38 not
met, and **38 cycles carry ≥ 1 step failure** — so the verdict line and the step failures
agree, with no cycle failing for a reason outside these two families.

| | cycles |
|---|---|
| `compute_basis_context` only | **11** |
| `write_gex_cycle_history` only | **17** |
| **both (the overlap)** | **10** |
| some other step only | 0 |
| **total failing cycles** | **38** |

Cycles touched by `compute_basis_context` = **21**; by `write_gex_cycle_history` = **27**.
Two independent reconciliations hold: the basis step runs once per cycle, so 21 cycles =
21 step-failures; and the 34 `write_gex` step-failures over 27 cycles means **7 cycles had
both the NIFTY and the SENSEX leg fail** (34 − 27), which matches the per-cycle step sets.

Decomposing the 21 basis cycles by their own exit reason:

| basis exit reason | + `write_gex` | basis only | total |
|---|---|---|---|
| `SKIPPED_NO_INPUT` (structural, pre-09:30 IST) | 7 | 5 | **12** |
| `DATA_ERROR` (`no_rows`, undiagnosed) | 3 | 6 | **9** |
| **TOTAL** | **10** | **11** | **21** |

The 12/9 split recovered here from the per-cycle grouping is the same 12/9 as §3, derived
a different way — the §3 split came from each failure's own stdout, this one from cycle
membership. They agree.

**Layered forecast.** Each layer is the measured consequence of removing one cause; none
is a projection beyond the data.

| | contract-met | rate |
|---|---|---|
| today, as observed | 46 / 84 | 54.8 % |
| + ENH-133 fix (deployed 12:23:53 UTC, **unverified**) | 63 / 84 | **75.0 %** — 17 cycles clean |
| + pre-09:30 `SKIPPED_NO_INPUT` no longer failing a cycle | 75 / 84 | 89.3 % — 12 more |
| + the 9 `DATA_ERROR` `no_rows` cycles diagnosed | 84 / 84 | 100.0 % |

So the answer to the question §6 previously left open: **21 of the 38 failing cycles will
still fail with the ENH-133 fix in place, and 17 become clean.** The at-most-21 bound was
correct and is now exact, because every basis failure fell in a distinct cycle.

The second row is the one to watch on the next trading day, and it is a **prediction, not
a result** — if the first cycles after 03:00 UTC do not land near 75 %, either the ENH-133
fix is not doing what `bcadfa6` was measured to do, or a third cause is present that this
day's log does not contain.

Note what the layering also shows: **the structural `SKIPPED_NO_INPUT` is the single
largest remaining contributor at 12 cycles**, larger than the undiagnosed `DATA_ERROR` at
9 — so the cheapest remaining win is the one that is fully understood (§4), not the one
that needs more investigation (§3.5).

## 7. Corrections to my own work in this investigation

Recorded because they are the transferable part.

1. **An inference from absent prints, wrong.** I eliminated every silent `return 1` path
   except `DEPENDENCY_MISSING` and reported that as the likely cause. I had **missed that
   the `no_rows` branch sets its status with no `print`** — so the elimination was
   incomplete and pointed at the wrong reason. The operator's `DATA_ERROR` timestamps are
   what made it resolvable; the log alone, as I read it, did not.
2. **An advisory claim acted on without a test, then promoted to a register finding.**
   The *"`merdian_ro` is RLS-blind to `script_execution_log`"* claim came from a **relayed
   operator instruction, not from my own inference** — but accepting it, abandoning the
   read, and then **filing a contradiction against `CURRENT.md` §S90 item 3** on that basis
   were all mine. **The claim is wrong:** `merdian_ro` **can** read the table and
   `CURRENT.md` is correct. **The contradiction item is withdrawn.**

   Two faults worth separating, because they have different fixes. (a) My own earlier
   `bin/roq.sh` call failed with `cannot read SQL file` because **it reads SQL on stdin and
   I passed it as an argument** — a usage error of mine, which then made the relayed claim
   look corroborated. (b) A relayed constraint is a **hypothesis with a credible source**,
   not a measurement; the cost of testing it was one correctly-formed command.
   **Nothing becomes a register finding on authority alone — the evidence bar is the same
   whoever states it.**
3. **An estimate offered where a replay was available** (cross-reference,
   `telegram_flood_findings_S91.md`): I estimated one-key-alone at "≈14 sends"; the replay
   measured **93**, a 6.6× error, because merging keys does nothing for
   `FAILED → OK → FAILED`.

## 8. Owed at the doc-close

1. **Correct TD-S91-NEW-6**: not "every cycle" — 21 of 84 (25 %), and it is **two**
   mechanisms: 12 × `SKIPPED_NO_INPUT` (structural, pre-09:30 IST) + 9 × `DATA_ERROR`
   (`no_rows`, undiagnosed between two candidates).
2. **Add `compute_basis_context_local.py:61` to TD-S91-NEW-2** as a seventh site, and note
   that the entry's grep was scoped to cron-line scripts and so cannot see orchestrator
   **steps**.
3. **New TD** for the 12-cycle structural `SKIPPED_NO_INPUT` exit 1 — the daily false
   failure, and the fact that it is indistinguishable from a real error.
4. **TD-S91-NEW-1 status**: fix deployed `12:23:53 UTC` 2026-10-07, **unverified by any
   live cycle**; first test is the next trading day's 03:00 UTC cycle.
5. The three items already listed in `scratch/s91/telegram_flood_findings_S91.md` §5.
