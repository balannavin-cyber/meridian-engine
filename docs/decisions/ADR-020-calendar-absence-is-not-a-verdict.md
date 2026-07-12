# ADR-020 — Calendar absence is not a verdict: the gate must resolve missing rows through the rule engine, never fail open

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-07-12 |
| Session | Session 68 |
| Supersedes | Nothing. Refines the fail-open contract documented in `core/trading_calendar_gate.py` (S60, TD-S60-NEW-3) without reversing it. |
| Related ENH / TD / commits | ENH-116 (surfaced the bug); `f8e287b` (gate fix); TD-S60-NEW-2 (calendar-at-source fix, S60); TD-S60-NEW-3 (shared gate helper, S60); ADR-001 / C-09 (stable-lies pattern); ADR-018 D2 (recency-floor doctrine) |

---

## Context

Two shared-core modules, each internally coherent, each correctly implemented, each explicitly documented — and holding **opposite contracts about what a missing `trading_calendar` row means.**

**`core/trading_calendar_gate.py`** (S60, the shared holiday gate for ~6 live consumers) states in its own docstring:

> *FAIL-OPEN by contract: any error (no creds, network, non-200, **no row**, exception) returns True / allows the run. A gate can only ever SKIP a confirmed-closed day, never BLOCK a real session on a calendar hiccup.*

**`seed_trading_calendar.py`** (S55, the `30 02` cron that populates the table) states in its own docstring:

> *only OPEN days get a row (weekends and NSE holidays need none — **a missing row is correctly read as "closed"**, matching the module doctrine).*

Composed, these two doctrines produce: **every unseeded weekend and every NSE holiday reads as a TRADING DAY.** The seeder deliberately omits closed days *because it believes absence encodes closed*; the gate reads that same absence as *open*.

This was live from S60 until S68 — silently, because the failure is invisible on the days it matters least and the crons that consume the gate are mostly `* * 1-5` day-of-week-restricted, so weekends never bit. **Weekday NSE holidays would have.** The next one was 2026-09-14, beyond the seeder's 14-day horizon, i.e. guaranteed unseeded, i.e. guaranteed to read as open.

### How it surfaced

Not by audit. ENH-116 Objective 1 required a 15-session backfill of `compile_market_environment_local.py`. The backfill's day-list was built by filtering candidate dates through `is_trading_day()` — and the list came back containing **2026-07-04, 07-05, 06-27, 06-28 (Saturdays and Sundays)**. The compiler duly wrote ambient rows keyed to non-sessions.

The diagnostic tell was precise: `2026-06-26` (a closed Friday, NSE holiday) returned **False** correctly — because that date *had* a row (`is_open=false`, from an old bulk seed). Every date **without** a row returned True. Absence, not the data, was the discriminator.

### What this is an instance of

The house has seen this shape before. ADR-001 / C-09 is *"stable lies defeat duration gates"* — a stale reference silently invalidating correct downstream data. This is its structural cousin: **an absent reference silently inverting a correct downstream decision.** The gate was not broken. The seeder was not broken. The *contract between them* was never written down, so each module authored its own, and they disagreed.

---

## Decision

**Absence is not a verdict. A shared gate must resolve from the rule engine what it can compute, and fail open only on genuine error.**

Concretely, in `core/trading_calendar_gate.py::is_trading_day()`:

1. **A `trading_calendar` row, when present, remains authoritative.** Unchanged.
2. **A missing row is no longer an error.** It is routed to `_resolve_absent_day()`, which defers to the V18E rule engine `trading_calendar.get_session_config_for_date()` — *the same source of truth `seed_trading_calendar.py` already uses*. Weekend → closed. NSE holiday (from `trading_calendar.json`) → closed. **Muhurat / special session → OPEN.** Normal weekday → open.
3. **The fail-open contract is preserved exactly where it belongs.** Only a *successfully computed* `is_open=False` returns False. Any engine failure — missing/malformed `trading_calendar.json`, unparseable date, import error — falls back to `True`. Non-200, missing creds, and network errors are untouched and still fail open.
4. **The rule-engine import is lazy**, inside the function, so the gate keeps its documented self-sufficiency: if the engine ever breaks, importing the gate still works and every consumer degrades to the prior behaviour rather than failing to start.

**No dow-hardcoding.** A "weekend ⇒ closed" short-circuit in the gate was explicitly rejected — see Alternatives. Closure must remain a *computed statement*, never an inferred one, because Muhurat trading is a genuine session that falls on a weekend.

---

## Evidence

**The bug, before the fix** (live probe, `core.trading_calendar_gate.is_trading_day`):

| Date | Row in `trading_calendar`? | Gate said | Truth |
|---|---|---|---|
| 2026-06-26 (Fri, NSE holiday) | yes, `is_open=false` | **False** ✓ | closed |
| 2026-06-27 (Sat) | **no row** | **True** ✗ | closed |
| 2026-06-28 (Sun) | **no row** | **True** ✗ | closed |
| 2026-07-04 (Sat) | **no row** | **True** ✗ | closed |
| 2026-07-05 (Sun) | **no row** | **True** ✗ | closed |
| 2026-07-11 (Sat) | **no row** | **True** ✗ | closed |
| 2026-07-10 (Fri) | yes, `is_open=true` | True ✓ | open |

Row-present dates were always right. Row-absent dates were always wrong. The `trading_calendar` table itself was **not** at fault — it held no weekend rows at all beyond one legacy 06-26 row, exactly as the seeder intends.

**The fix, verified across 10 scenarios** (fixture-tested pre-deploy, then live):

| Scenario | Result |
|---|---|
| No row + weekend | **False** (closed) — the fix |
| No row + NSE holiday | **False** (closed) — the fix |
| No row + Muhurat special session (a Sunday) | **True** (open) — a real session is never blocked |
| No row + normal weekday | True |
| No row + `trading_calendar.json` missing | **True** — fail-open contract holds |
| No row + rule-engine module absent | **True** — fail-open contract holds |
| DB row present (`is_open=true`) | True — row authoritative, engine not consulted |
| DB row present (`is_open=false`) | False — unchanged |
| HTTP 500 | True — unchanged |
| No creds | True — unchanged |

**Live after deploy (`f8e287b`, Local == origin == EC2):** `2026-07-04 False`, `2026-07-05 False`, `2026-07-11 False`, `2026-06-27 False`, `2026-06-28 False`, `2026-07-10 True`. First live holiday proof came on the S68 45-session backfill, which logged `2026-05-28: no row; rule engine says CLOSED (Bakri Eid)` — a weekday holiday correctly rejected, which is the case the old gate would have passed straight through.

**Blast radius, measured not assumed.** ~6 live consumers gate on this helper: `run_merdian_shadow_runner_aws.py` (orchestrator, `*/5` cron), `ingest_participant_positioning.py`, `accrue_expiry_outcomes.py`, `relate_ambient_to_open_local.py`, `compile_market_environment_local.py`, plus `assert_trading_day_or_exit()` callers. Data damage found and remediated: **14 phantom rows** in `market_environment_snapshots` keyed to weekend `as_of_date` or `for_session_date` (all `source=ambient_compiler_s62`, all from the S68 backfill itself — swept by a `extract(dow ...) in (0,6)` predicate, deleted, and the 3 genuinely-settled sessions that had been mis-routed to Saturdays recompiled to their correct next trading day). **Holiday-axis cross-check came back empty** — the compiler only began writing at S62 (mid-June), so of the 15 NSE-2026 holidays only 06-26 fell in its lifetime, and 06-26 had a row. That is timing luck, not a property of the old gate: had the compiler been running in May, 05-01 and 05-28 would both have produced phantoms.

---

## Alternatives considered

**A. Seed the closed days too** — change `seed_trading_calendar.py` to write weekends and holidays with `is_open=false`, leaving the gate's fail-open contract untouched. *Rejected as the primary fix* (though it remains a valid belt): it makes correctness a function of **seeding-horizon coverage**. The seeder's default window is 14 days; beyond that the table is empty and the gate is fail-open again. The very holiday that motivated this ADR (2026-09-14) sits outside that horizon. A fix that works only inside a 14-day window is not a fix, it is a deferral. It also leaves the *contract* unwritten — the two modules would still disagree in principle, and the next module to read the table would have to guess which doctrine it inherits.

**B. Hardcode `weekday >= 5 ⇒ closed` in the gate.** *Rejected outright.* This breaks the one case that matters most: **Muhurat trading** is a real, capital-at-risk session that falls on a weekend, and `trading_calendar.py` already models it (`special_sessions`, Rule 3, evaluated *before* the weekend rule). A dow short-circuit would block a live session — the exact failure the fail-open contract exists to prevent. Inferring closure from the calendar's shape rather than computing it is the same class of error as the bug being fixed.

**C. Make the gate fail closed on a missing row.** *Rejected.* This inverts the contract in the wrong direction and re-introduces the risk the S60 author correctly guarded against: a calendar hiccup (network blip, bad deploy, empty table after a rebuild) would silently **block a live trading session**, which is unrecoverable data loss. Missing a session is strictly worse than running on a closed one. The asymmetry is real and the original contract was right about it.

**D. Eager (module-level) import of the rule engine in the gate.** *Rejected.* The gate's docstring makes a deliberate point of being self-sufficient — no `core.config`, no `SupabaseClient`, own `load_dotenv()` — precisely because a heavyweight import chain once made it a silent no-op on AWS (TD-S60-NEW-5). A top-level `from trading_calendar import ...` would make every consumer's *import* of the gate depend on the engine loading cleanly. Lazy + exception-wrapped keeps the blast radius at zero.

---

## Consequences

**Positive.**
- Absence stops being ambiguous. There is now exactly one answer to "what does a missing row mean?", and it is computed, not assumed.
- Horizon-independent: correctness no longer depends on how far ahead the seeder has run.
- Muhurat and all future special sessions are handled by construction, because the gate now inherits the rule engine's full semantics rather than a subset.
- The two modules can no longer disagree — they read the same authority.
- ~6 live consumers are, for the first time since S60, actually holiday-gated.

**Negative / accepted costs.**
- The rule engine is now on the gate's hot path for the missing-row case (a JSON read per call, on a file pinned off `__file__`). Acceptable: the gate is called at process start, not per-tick, and the engine is small.
- `trading_calendar.json` becomes load-bearing for a second consumer. If it drifts (as it did at S60 — 2 entries, one misdated), both the seeder and the gate inherit the drift. **Mitigation:** the fail-open wrapper means drift degrades to the *old* behaviour rather than to a hard block, and the S60 fix already established the 15-holiday NSE-2026 list as canonical with a documented regeneration source.

**Mitigations shipped in the same commit.**
- Every engine failure path returns True with a logged reason (`no row and rule engine unavailable (<err>); failing open`).
- Every computed closure logs its reason (`no row; rule engine says CLOSED (Weekend)` / `(Bakri Eid)`), so the decision is auditable in the consumer's own log rather than being silent.

---

## Relationship to other documents

- **ADR-001 / C-09** — same family. ADR-001 is *a stale reference silently invalidating correct data*; this is *an absent reference silently inverting a correct decision*. Both are trust-anchor failures where no component is individually broken.
- **ADR-018 D2** (recency-floor doctrine) — the same instinct one layer up: a reader must not silently treat a degraded upstream as authoritative. D2 says *stale → flag, don't tilt*. ADR-020 says *absent → compute, don't assume*.
- **ADR-006** (AWS migration scope) — the gate exists because ~30 bespoke inline holiday checks were consolidated; this ADR governs the semantics of that consolidation.
- **TD-S60-NEW-2 / TD-S60-NEW-3** — the S60 work that created both the calendar-at-source fix and the shared gate. This ADR closes the contract gap those two left open between them.
- **`MERDIAN_Assumption_Register.md`** — new assumption §D.26 (calendar-absence semantics) filed at this close.

---

## Governance language (one-line compressed form for CLAUDE.md settled-decisions)

**Absence is not a verdict.** A shared gate must resolve a missing `trading_calendar` row through the V18E rule engine (`trading_calendar.get_session_config_for_date`) — never default to allow, never hardcode dow. Fail-open is preserved for *genuine errors* only; a computed closure returns False. Two modules may not each author their own contract for what "no row" means. (ADR-020, S68, `f8e287b`.)

---

## Open follow-ups

1. **Optional belt (Alternative A, not rejected as a belt):** extend `seed_trading_calendar.py` to also write closed days with `is_open=false`, so the table is self-describing for any future consumer that reads it directly without going through the gate. Not required for correctness now that the gate computes; purely defensive. **P3.**
2. **~28 remaining bespoke inline gates** still to migrate onto `core/trading_calendar_gate.py` (the S60 backlog). Each one that remains is a module that does *not* inherit this ADR. **P2 — and the count is now a correctness statement, not just tidiness.**
3. **`notes: "Normal trading day"` on the 06-26 `is_open=false` row** — a cosmetic mislabel in the seeder's row construction, harmless but a smell. **P4.**

---

*ADR-020 — 2026-07-12 — Session 68 — Two correct modules, one unwritten contract, six ungated consumers. The gate was never broken; the boundary between it and the seeder was. Fixed by making the gate compute what it had been guessing.*
