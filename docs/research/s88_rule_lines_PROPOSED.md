# S88 — candidate rule lines, **PROPOSED ONLY**

| Field | Value |
|---|---|
| Document | `docs/research/s88_rule_lines_PROPOSED.md` |
| Status | **PROPOSED. Not applied. Not in force.** |
| Placement | **Deliberately NOT in `.claude/rules/`.** These are operator rules; the operator decides whether any becomes one, and where it lands. |
| Source | Session 88, 2026-10-01. Every line is generalised from something that **actually went wrong or was actually caught in that session**, with the evidence named. Nothing here is inferred from reasoning. |
| Count | **Five**, plus three runners-up recorded rather than padded into the five. |

---

## The five

### R1 — A latest-scoped view has no history. Parameterise its shipped body by one line; never reimplement it. And a parity test at its own `ts` is **not** the gate.

**Why.** Eleven of twelve per-cycle parity views return exactly **one** distinct `ts`
(`part5_depth.out`). The temptation is to rewrite the metric from base tables; that produces a
parity claim with nothing to defend it, which the standing rule already forbids. The one-line
`AND <alias>.ts <= :'AS_OF'::timestamptz` inside the `latest` CTE lateral worked on **all six**
bodies tried, diff **1 added / 0 removed** each.

**The gate is four things, not one.** Parity sha equal at the view's own `ts`; a **control** at a
different AS_OF proving the parameter is not inert; the returned `ts` compared **by column name**;
and a **wall-clock scan** of the body. The fourth is load-bearing and non-obvious: **a same-`ts`
parity test cannot detect a `now()`-dependence — it passes today and is wrong on every past day.**
Scan for `now()`, `current_date`, `current_timestamp`, `localtimestamp`, `clock_timestamp`,
`statement_timestamp`, `transaction_timestamp`, `timeofday`, `CURRENT_TIME` **and** for
non-builtin function names, since a UDF can hide one.

**Evidence.** `part5_parityC.out` — all six ADMITTED on the computed conditions; 0 wall-clock hits;
0 non-builtin functions.

---

### R2 — A timestamp string handed to a cast must carry its offset. `to_char(ts AT TIME ZONE …)` + `::timestamptz` is a silent shift.

**Why.** The `roq.sh` session timezone is **UTC**. An IST wall-clock string with no offset,
`'2026-10-01 11:30:07.908159'::timestamptz`, reads as **11:30 UTC = 17:00 IST** — later than every
run that day. **Every bucket in a 90-cell grid would have pinned the same last run, and the grid
would have looked plausible and internally consistent.** Pass `ts::text`, which carries `+00`.

**The tell that it worked.** All 540 layer cells matched on **exact `ts` equality**; under the bug
every one would have mismatched. That check is worth keeping for its own sake.

**Evidence.** D.44.4; `capture_s88.md` §5.2.

---

### R3 — Price levels are not comparable across days at different index levels. Score scale-free levels and within-day changes.

**Why.** SENSEX traded ~77k on 2026-08-27 and ~72k on 2026-10-01. Any cross-day ranking of `spot`,
straddle **points**, a flip **level** or basis **points** ranks by date, not by behaviour — the
latest day lands at the extreme in **every** bucket by construction, and the resulting score looks
like a finding.

**Form.** Two sets: scale-free levels (ratios, percentages, concentrations), and deltas against
that day's own first bucket. Each with its own stated chance line. **Exclude the first bucket from
the delta set** — every delta is 0 there and all days tie.

**Evidence.** `part5_extremes.out:17-21`; caught by the operator before scoring, not after.

---

### R4 — A window re-anchored to a moving reference cannot be differenced across time.

**Why.** "Three strikes below spot" at 11:30 and at 12:15 are **different strike sets** whenever
spot moves, so their difference mixes OI change with price movement and cannot be read as either.
Fix the set at the anchor, carry it to the later time, and check that every strike in it is present
at **both** ends before differencing.

**Scope.** A re-anchored **level** at one moment is fine. It is the **difference** that is invalid.
Both halves matter: S88 kept the tilt level in the cross-day set and dropped its delta.

**Evidence.** `_p7_fixed_strikes.sql`, `part4_fixed.out:40-45` (`min_n_matched_in_any_set = 3`,
`ladder_strikes_1130 == strikes_matched_whole` on all six days); `part5_extremes.out:22-26`.

---

### R5 — Before claiming a register contradicts itself, check whether it is merely silent.

**Why.** S88 read `aws_cron`'s single `40 10 * * 1-5` entry, found the S60 `change_log` describing
a *different* job at that schedule, and wrote into the capture that **the register disagreed with
itself**. `crontab -l` then showed **two separate cron lines** sharing the schedule, and the
inventory had simply **omitted** one. **An omission is not a conflict**, and the difference matters:
a conflict needs adjudication, an omission needs a line added.

**Form.** When two register statements appear to disagree, establish the ground truth from the
system before writing the disagreement down. If the ground truth is outside the session's scope,
**say the question is open** rather than naming a contradiction.

**Evidence.** `capture_s88.md` §2.5 (ii) → §3.2; D.44.7.

---

## Runners-up — recorded, not padded into the five

- **Verdict lines are COMPUTED, never fixed echo text.** The first draft of the parity record
  printed `NO HITS`, `ADMITTED` and `MATCH` as literal strings inside the reporting block — **they
  would have printed unchanged even if every check had failed.** Rewritten so each is derived: the
  hit count comes from the grep and `NO HITS` prints only on the `-eq 0` branch; `ts` is selected
  **by column name** and compared in the shell; and the verdict is computed from all three
  conditions, with the else-branch naming which one failed. **This is Rule 0 applied to the report
  rather than to the check** — a check that can fail is still worthless if its output cannot.
  *Not promoted into the five only because CLAUDE.md Rule 0 already states the principle; this is
  the reporting-layer corollary and may belong as a clause under it rather than as its own rule.*
- **A nearest-cycle or "latest ≤ AS_OF" lookup with no same-day bound is a CORRECTNESS defect, not
  just a cost one.** Unbounded, it silently returns the **previous day's** cycle for any bucket
  that has none of its own — and the result is a plausible number in the wrong row. The guard is
  therefore **same-IST-date AND ≤ 360 s of the bucket target, else STALE with the returned `ts`
  recorded and the metric left EMPTY — never filled**. S88 ran that guard on all four feeds and on
  every layer cell: 90/90 and 540/540 admitted, 0 STALE, with the layer side additionally gated on
  exact `ts` equality against the spine. *Secondary evidence, cost:* bounding the four laterals
  took the plan from `6,972,256` to `757,332` and removed the one `Seq Scan`. *Not promoted because
  it reads as query hygiene until the correctness half is stated — which is precisely the reason it
  is recorded here rather than dropped.*
- **RLS on with zero policies is unreadable by every non-bypass role, `anon` included.** A zero from
  such a table is never "empty", and a blanket `merdian_ro` policy would not fix it. Three tables
  measured in this state against `reltuples` of 10,930 / 1,630 / 33 (D.44.6). *Not promoted because
  TD-S81-NEW-16 already owns the family; this is an update row on it, not a new rule.*

---

*Proposed at the S88 doc-close, 2026-10-02. **None of these is in force.** Three of the five
(R2, R3, R5) and the first two runners-up describe mistakes **I made in this session**, four of
them caught by the operator; R1 and R4 describe methods that worked and are worth fixing in place.
If any is adopted, the operator decides its wording and its location.*
