# S74 — Doc-Close Capture (2026-09-07, Monday)

| Field | Value |
|---|---|
| Document | `docs/session_notes/capture_s74.md` |
| Type | **Doc-close capture.** Every subsequent S74 register update splices from this file, so no large body of text crosses the terminal twice. This is the single source for the S74 close. |
| Session shape | Mixed: two source-level fixes shipped and verified through the deployed path, one pre-registered study executed to a verdict, one repo-wide audit, one governance artefact brought under version control. |
| HEAD at open | `18b345e` |
| Commits | Three units of work across four commits: `7bb1779` (engine, **pushed**); `74fee89`, `584f854`, `3997582` (this clone, **unpushed**). Chain: `18b345e` → `7bb1779` → `74fee89` → `584f854` → `3997582`. |
| Verification standard | Every "shipped" claim below was verified **through the deployed path** — the live cron, the live systemd stop — not by manual invocation. Where a claim rests on a manual run it is marked as such. |
| Registers touched | **None.** This capture is written first, deliberately, before any register edit. |

---

## 0. TL;DR

Two source-level defects fixed and confirmed on live production paths. One pre-registered study run to a verdict: **PIN answered NO; ACCEL not answered, and recorded as inconclusive rather than accepted because its arm carries a design defect present in the pre-registration before measurement.** One repo-wide audit produced 59 findings. Five TDs to file — not sixty-nine; the audit is filed as a pointer, not enumerated.

The session's most consequential output is not a fix. It is that **two of the brief's own premises were measured and refuted**, and that five of my own claims were withdrawn on measurement (§5, `§D.32`). Both refutations trace to the same shape: a value derived once, carried forward as fact across sessions, and never re-measured.

---

## 1. Shipped

### 1.1 `KillSignal=SIGINT` on `merdian-wsfeed.service` — TD-S72-NEW-6 **CLOSED**

Unit-file splice with fail-loud assertions, `daemon-reload`, **no restart**, backup at `.PRE_S74`.

**Verified on the live 10:05 UTC stop, not by manual invocation:**

| | Before | After |
|---|---|---|
| Stop duration | ~90 s | `Stopping 10:05:01` → `Deactivated successfully 10:05:02` |
| Result | `failed (Result: timeout)` | `Result=success` |
| Exit | `code=killed signal=KILL` | `ExecMainStatus=0` |

The application log confirms the mechanism directly: `Received signal 2 -- clean shutdown requested`.

**The S72 handler was correct.** SIGTERM never reached it because Twisted installs its own SIGTERM handler; the process was therefore always SIGKILLed after the 90 s timeout. `SuccessExitStatus` was deliberately left **empty** — relabelling a genuine kill as success would have hidden the next real hang.

**Second-order consequence.** `OnFailure=` no longer fires on healthy shutdowns. The alert channel can distinguish good days from bad **for the first time**, which closes TD-S71-NEW-4's complaint that `systemctl is-active` can never answer feed health — the healthy path and the broken path no longer share a terminal state.

**Exposure recorded:** the unit file is **on-box and outside git**. Twenty units and three timers have no version control.

### 1.2 `premarket_ref` window re-anchored — `7bb1779`

`get_premarket_ref` windowed `[09:07:30, 09:08:30]`, then `[09:00, 09:08:59]`. The capture cron moved **09:08 → 09:11 on 2026-08-24**, so both windows closed *before* the only candidate row. `premarket_ref` was NULL and `capture_quality` read `MISSING` for **eleven sessions**.

Replaced with a single window `[09:00:00, 09:14:59]`, last row — **anchored on the market open, which is stable, not the auction close, which reformed twice in six weeks.** The upper bound cannot reach the ~09:16 `dhan_charts_intraday` rows that feed `open_0915`.

- **Regression gate:** 2026-08-21 reproduces exactly — `09:08:03.79091`, NIFTY `24284.05`, SENSEX `77702.18`.
- **Backfill:** ten sessions, 08-24 → 09-04, **20/20 rows**, `premarket_move_pct` populated.
- **Live:** written today by the `40 10` cron at `09:11:03` — NIFTY `23883.15`, SENSEX `76446.05`.

### 1.3 ADR-009 pre-registration — `74fee89`

`docs/research/adr009_prereg_gex_zone_utility_2026-09-07.md`, 539 lines. Ten pre-commitments, seven preconditions, **written and committed before any measurement**.

### 1.4 Coupling audit — `584f854` + `3997582`

`docs/audits/coupling_audit_2026-09-07.md`, 739 lines. **59 findings** — 13 BROKEN, 26 AT-RISK, 20 write-only/no-writer. Ten items verified **NOT** broken. Six scope limits stated.

### 1.5 `.claude/settings.json` brought under version control

Tracked. Deny 25 → 30, ask 16 → 19, allow 0. Verified live in `/permissions`.

- **New denies:** `set -a`, `source *.env*`, `. ./.env*`, `grep*.env*`, `env`
- **New asks:** `git switch`, `git restore`, `git add`

Closes TD-S73-NEW-7's structural finding — the only governance artefact outside version control is now inside it. **Staged, uncommitted.**

---

## 2. The question — PIN answered, ACCEL not

All **seven preconditions passed**, including the equivalence gate at **zero rows on both arms**, so the reconstruction is the shipped walk.

### PIN — verdict **NO**

NIFTY holdout: mean **−0.1996**, 95% CI **[−0.2998, −0.0801]**, **19 of 21** sessions negative. **Both verdict clauses fire.** SENSEX reproduces the sign.

Price spends **significantly less** time in the real prior-session pin zone than in spot-matched zones borrowed from unrelated sessions.

The calibration arm read **+0.0800** mean — but its **median was −0.0848 with 23 of 39 negative**, so there was never a broad calibration effect to lose.

### ACCEL — **inconclusive, not accepted**

NIFTY survived the rule: mean **+0.1911**, CI **[+0.0130, +0.4162]**. Recorded as inconclusive on four grounds:

1. **N=11** after undefined-ratio exclusions, against ADR-009's own **N<30 "meaningless to split"** tier.
2. The CI lower bound is **+0.013** and **one of eleven points carries it**.
3. **SENSEX contradicts.**
4. The **~50% exclusion is outcome-dependent** — the surviving sessions are those where price traversed the band, which is close to selecting on the outcome.

**That is a design defect in the ACCEL arm, present in the pre-registration before measurement.**

**Nothing shipped on either.** Bears on **ADR-023 D1 Decision B**.

---

## 3. Placement, not staleness

Spot is inside the pin zone **at the moment the zone is computed** on only **15/67 NIFTY (22%)** and **13/67 SENSEX**; mean distance **0.70% / 0.79%**.

**Overnight gaps are not the explanation.** In **16 of 21** NIFTY holdout sessions price never entered the buffered zone at all — the real distribution is **bimodal, not shifted**.

The containment statistic is measuring **whether the zone landed on spot** more than whether spot was held.

Whether zones would show attraction *conditional on price being near them* is a different question **this design cannot answer**, and proposing it now would be post-hoc reframing. Recorded, not pursued.

---

## 4. Refutations of the session brief — both measured

1. **The six-file Priority 1 pre-open list was one-of-six live.** Only `trading_calendar.py`; the other five are orphans. It **missed `build_market_spot_session_markers.py`** — the file that was actually broken. That list came from an **S71 grep** and propagated untested through S72, S73 and the S74 brief.
2. **`gex_strike_snapshots` holds 67 eligible sessions, not the 250+ in the brief.** 1,412,989 rows across 69 GEX dates; `min(ts) = 2026-05-25`.

---

## 5. `§D.32` — my own claims withdrawn on measurement (five rows, all mine)

| ID | Claim withdrawn | What settled it |
|---|---|---|
| **D.32.1** | The six-file pre-open list was a live-invocation measurement | It was never an invocation measurement — a grep result carried as fact across four sessions. **D.31.1's shape at deployment scale.** |
| **D.32.2** | `git log -S` dates the deployment | It dates a register's **transcription**, not the deployment. The register recorded the cron move at `279fab1` (2026-09-05); the data puts it at **2026-08-24**. Ten sessions' error. The `dhan_idx_i` timestamps dated it, not git. |
| **D.32.3** | A relayed transcript evidences file state | It does not — `repr()` included. I refused a splice over a two-space indent **the transport had eaten**; `ast.parse` and an indent census showed the file was clean. **Third instance in three sessions** (D.30.9 → D.31.2 → this), and it recurred **four times today**. Only reading from disk settles it. |
| **D.32.4** | N=72 eligible sessions | Taken from `count(distinct ts::date)` on **one** table when the study needed **two**. The eligible figure is **67**. Same class as the "250+" I refuted six hours earlier. |
| **D.32.5** | close-1530 is "the same shape as the pre-open bug, opposite end of the day" | Measurement refuted it. The pre-open row **existed** and the window missed it; the close-1530 row **does not exist at all**. The audit then found **three independent causes** where I had one. |

**Also record — four wrong assertions caught by fail-loud aborts before writing:** a whole-file vs function-body count; a `count(distinct diff)` grid test that conflated grid spacing with strike coverage; and two others. **Each aborted cleanly.**

**The recurring shape:** encoding an expectation about a system's *shape* rather than the *property the downstream step needs*.

---

## 6. TDs to file — five, not sixty-nine

### TD-S74-NEW-1 (S1) — the coupling audit, as a pointer

Filed as a pointer to `docs/audits/coupling_audit_2026-09-07.md`. **59 findings, not enumerated in `tech_debt.md`.** Needs **de-duplication by root cause and ordering by consequence** before any of it is actionable.

### TD-S74-NEW-2 (S1) — F-19: D/W zones invisible to the signal path

ADR-005 writes D/W zones with `valid_to = NULL`. `detect_ict_patterns_runner.py:268` filters `.gte("valid_to", trade_date)`. **PostgREST `gte` does not match NULL, so every daily and weekly zone is invisible to the signal path.** Only 1H survives.

`generate_pine_overlay.py:552-556` reads the same table with **no validity filter**, so the chart renders zones the signal engine cannot see. **Two consumers of one table disagree about which rows exist.**

### TD-S74-NEW-3 (S1) — F-01: futures basis against stale spot

`capture_index_futures_snapshot_local.py:144-152` computes `basis` from an **unbounded** `order=ts.desc&limit=1` read of `market_spot_snapshots`. The spot writer stops at **15:15** by its own guard; this consumer fires at **15:30 / 15:35 / 15:40** and again at **16:00**. Three rows per symbol per day carry a basis against spot **up to 25 minutes stale**.

**The failure inverts** — it finds something and is wrong, rather than finding nothing. No recency floor, contra ADR-023. This is **ADR-021 §A1.8's unscoped-read audit, still open**.

### TD-S74-NEW-4 (S1) — F-04: the S59 breadth defect can recur

`build_wcb_snapshot_local.py:94-99` and `ingest_breadth_from_ticks.py:160-162` both read `equity_intraday_last` **unbounded**. The freshness guard added after S59 went into `scripts/eod_health_check.py` and **never into either consumer**. If the 09:05 refresh fails, both silently use the previous session's baseline — **the exact S59 shape**.

### TD-S74-NEW-5 (S2) — F-13's remaining half: `close_1530` unobtainable

Three independent causes:

1. No producer writes a `ts` in the **15:29–15:31** window since S70 moved `MARKET_CLOSE_GUARD` to **15:15**.
2. `capture_cas_close.py:366` stamps `ts` with its **run time**, keeping the bar time only in `raw.bar_ts_ist`.
3. The marker job runs at **16:10**, ten minutes **before** the CAS capture at **16:20**.

**Consequence:** `derive_capture_quality` can never return `COMPLETE`, so the field moves from `MISSING` to `MISSING_CLOSE_1530` and stops. **A quality scale whose top value is unreachable cannot signal.**

**Blocked on** an ADR-022 decision about what "the close" means post-CAS **across every consumer**.

---

## 7. Decisions

### 7.1 Doc Protocol amendment — **DECIDED, not deferred**

**Splice with fail-loud assertions, not full-file rewrite.** Amends **Doc Protocol v4 Rule 7**.

**Rationale:** the full-rewrite rule exists for *verification*; `git diff` verifies better than a byte count; and on a **662 KB** file through an agent a full rewrite **is** the truncation risk TD-S73-NEW-8 records.

**Evidence:** three clean aborts in S73 and **four more today**, two of which caught **wrong assertions** rather than wrong edits.

### 7.2 Deploy-direction inversion — still **UNRATIFIED**

Now with **two further instances**: both S74 code commits went **EC2 → main directly, no branch**.

Ratifying means amending **ADR-006's deploy-direction statement and the Doc Protocol line together**. Not done here.

---

## 8. `CLAUDE.md` size

**421,684 bytes — 2.8× the 150k ceiling.**

| Component | Bytes |
|---|---|
| Rules / decisions | 226,393 |
| History | 195,291 |
| Footers (28) | — |

**Moving history alone leaves 226k — still over.**

The larger cost is the **eight-fold duplication** of every session's findings across `CLAUDE.md`, `CURRENT.md`, `session_log.md`, `tech_debt.md`, System Map, Deployment Topology, Assumption Register and Decision Index.

---

## 9. Watch items

- **`status.json` at repo root** is a live cron output **in no register**. Its writer, `refresh_health_dashboard.py`, reports `STALE` against a five-minute-old table via a **naive/aware `TypeError` caught by a bare `except` returning sentinel `999`**.
- **`rate_sens.out`** is a dead `nohup` artefact.
- **`merdian_reference.json`** records `gex_strike_snapshots` with `oi_total_calls` / `oi_total_puts` against live **`oi_call` / `oi_put`**, and **omits `id`, `dte`, `created_at`**.
- **Three on-disk definitions of the GEX zone views exist**; only `docs/research/s72_gex_view_fix.sql` matches what P1 proved deployed.
- **Five weekday marker rows wholly missing:** 07-31, 08-04, 08-07, 08-17, 08-20.
- **`reload_dhan_scripmaster.py` fires on the 1st and 15th regardless of weekday** — **third instance** of a writer running on a closed market, after TD-S72-NEW-10 and the 2026-06-26 holiday GEX rows.

---

## 10. Git state at capture

| Item | State |
|---|---|
| `7bb1779` | engine, **pushed** |
| `74fee89` | this clone, **unpushed** |
| `584f854` | this clone, **unpushed** |
| `3997582` | this clone, **unpushed** |
| `.claude/settings.json` | **staged, uncommitted** |
| Working tree | clean apart from the staged `.claude/settings.json` |
| Branch | `main` (both code commits went EC2 → main directly — see §7.2) |

---

## 11. Doc-close obligations — what splices where

Every edit below **splices from this file**. No content is to be re-derived at edit time.

| Destination | Splice source | Notes |
|---|---|---|
| `session_log.md` | §0, §1, §10 | One-line-per-session entry, newest-first prepend |
| `CURRENT.md` | §0, §1, §2, §6, §11 | S74 "Last session" block prepended; S73 demoted by header rename only, content verbatim |
| `tech_debt.md` | §6 | **Five** TD-S74-NEW blocks. TD-S72-NEW-6 closure block from §1.1. TD-S73-NEW-7 closure from §1.5. TD-S71-NEW-4 closure from §1.1 second-order |
| `MERDIAN_Assumption_Register.md` | §5 | New **§D.32**, five rows, all self-scored |
| `MERDIAN_Decision_Index.md` | §7.1 | Doc Protocol v4 Rule 7 amendment row. **No new ADR this session.** §7.2 remains unratified — do **not** record it as decided |
| `CLAUDE.md` | §1, §2, §3, §4, §7.1 | Settled-decision bullets. **See §8 — the file is 2.8× its ceiling; adding to it without addressing that is the known cost** |
| `MERDIAN_Deployment_Topology.md` | §1.1, §9 | `KillSignal=SIGINT`; the twenty-units/three-timers exposure; `reload_dhan_scripmaster.py` weekday defect |
| `MERDIAN_System_Map.md` | §1.2, §6, §9 | `premarket_ref` window; the three GEX view definitions; `merdian_reference.json` schema drift |
| `merdian_reference.json` | §1, §9, §10 | Version bump + change_log. **Correct the `gex_strike_snapshots` column list per §9** |
| Enhancement Register | — | **Not triggered.** No enhancement work this session |

**Ordering note.** §6's TD-S74-NEW-1 is a *pointer*. Do not expand the 59 audit findings into `tech_debt.md`; de-duplicate by root cause first, per its own text.

---

*Doc-close capture — Session 74, 2026-09-07. Written before any register edit, deliberately, so that every subsequent update splices from one verified source rather than re-deriving from the terminal. Nothing in this file has been applied to a register. The two shipped fixes were verified through the deployed path — the live 10:05 UTC systemd stop and the live `40 10` cron — not by manual invocation. PIN is answered NO; ACCEL is not answered, and its arm carries a design defect that predates its measurement.*
