# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S79 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close, moved verbatim rather than retyped. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**Session 82 — 2026-09-24 (Thu).** Verification, not construction. Commits
`c831fdf` → `29bc83e` → `25f9d1b` + this doc-close, all pushed; **all three trees
level** and the post-15:45 batch complete.

**Shipped.** `core.trading_calendar_gate.previous_trading_day()` — resolves the
previous OPEN trading day from the **V18E rule engine**, not the database, so it is
offline by construction and the path an offline test exercises is the path cron runs;
returns `(date, provenance)` and the caller prints the provenance. `--date prev` and
`--resolve-only` on `eod_health_check.py`. `bin/eod_alert.sh` with its **own**
sentinel, deliberately not a reuse of `wsfeed_alert.sh`. A `sys.path` fix.

**The lead finding.** `scripts/eod_health_check.py` **has never been scheduled** — no
cron line, no unit, no timer — while its docstring asserts a 00:45 UTC run **twice**,
and that claimed runtime is the stated justification for `resolve_cron_log()`'s whole
design. ADR-025 D2 clause 2. Filed **TD-S82-NEW-3**, specced **ENH-129**.

**Filed:** TD-S82-NEW-1, -2, -3, -4; ENH-129 (PROPOSED).

**ENH-98 re-run — half-met, recorded against its own sentence.** ATM `delta_abserr`
0.046 → **0.0139** against a predicted *"well under 0.01"*. Gamma refusal not met
(NEAR 0.127 → 0.042). The residual ~12-pt offset is **neither futures basis nor
theoretical carry** — Pearson **−0.0655** over 59 cycles. SENSEX **void** at 0 DTE.
**Owed: a re-run with SENSEX at dte 1–2.**

**L9 stage 1 — half-verified.** SENSEX **PASS**: arm (b) 196/196, baseline picks
max-pain **71400 against 73800**. NIFTY **no-test by mechanism**: W2's 230 strikes
are a subset of W1's 268, **zero** W2-only, and at **zero** shared strikes does W2
win the baseline's `max()` (W1 peak OI 9.8× W2's). **NIFTY arm owed 2026-09-29.**

### Post-15:45 batch — ALL FOUR DONE
1. **Pull DONE** — `29bc83e` → `25f9d1b`, 2 files as previewed; import smoke
   `True ('2026-09-23', 'rule-engine')`, exit 0. No rollback needed.
2. **Live dry run DONE** — `--date 2026-09-23`, **EXIT 0**, VERDICT `[ OK ]`.
   `equity_intraday_last` reads `[ -- ] NOT AUDITABLE` and **will every night by
   design** (one-generation upsert table; `--date prev` is always back-dated).
3. **Crontab installed BY THE OPERATOR — 59 → 60**, 1 entry. A manual run of the exact
   cron line returned **`[ OK ]`, no alert files created**. First scheduled run
   **Friday 2026-09-25 00:45 UTC** (06:15 IST), auditing **Thu 2026-09-24**.
   `aws_crontab.txt` mirrored: 60 lines, `diff` empty, +1/0.

### NEXT SESSION PICKS UP

**Time-boxed — these expire or get harder if missed**
1. **Watch the first scheduled run: FRIDAY 2026-09-25 00:45 UTC** (06:15 IST),
   auditing Thu 2026-09-24. Confirm it fired at all, and that
   `[ -- ] NOT AUDITABLE` on `equity_intraday_last` is **not** mistaken for a
   failure — it will read that way every night by design.
2. **NIFTY L9 arm on 2026-09-29** (NIFTY at/near 0 DTE). TD-S80-NEW-1 stage 1 is
   **half-verified**, and the measured mechanism says the NIFTY arm **cannot** pass
   before then — W2 ⊂ W1 with W1 OI dominant at every shared strike.
3. **ENH-98 re-run with SENSEX at dte 1–2.** Today's SENSEX arm was void at 0 DTE, and
   dte 1–2 is exactly where `dte/365` and `exact/365` separate.
4. **The multi-DTE offset test was NOT run.** The ~12-pt ATM offset is constant on one
   session; whether it scales with DTE is unmeasured, and that is what would
   discriminate a `q > 0` dividend term from a fixed model offset.

**Decisions owed to the operator — none are mine to make**
5. **Token decision + Dhan API log review (TD-S81-NEW-1).** Rotation is **likely moot**
   — but that is **INFERRED** from two dates (token minted 09-23 08:35; S81 revoke
   2026-09-22 mid-session), **not measured**. The log review has not been done.
6. **ADR-020 amendment for Muhurat (TD-S82-NEW-4).** The engine is deliberately
   unfixed: reordering Rule 1 / Rule 3 changes a decision the ADR recorded, so it
   needs an amendment, not a patch. Note the fix alone is not sufficient — every
   consumer is `dow=1-5`, so a cron change is also required.
7. **`compute_basis_context` cron decision (TD-S81-NEW-12).**
8. **Delete the "illustrative seeds" template note** at the head of Active debt —
   proposed and annotated this session, **not applied** (`c521b2f`, 2026-04-22).

**Carried, not started**
9. **TD-S81-NEW-20 NOT APPLIED** — `DhanClient` still reads the token at construction,
   so a mid-cycle rotation still leaves a running process holding an invalidated
   token. This is the mechanism behind the 08:35 401s.
10. **ENH-129 is DESIGNED, NOT BUILT** — the seven depth checks, the crontab-derived
    expected set, the **anon revoke check** (which needs an anon-key probe, not
    `merdian_ro`) and the **RLS control** all exist only as a specification. The
    scheduled check now running at 00:45 UTC is the *old* body.
11. **Parity build order: L9 → L3 → L7/L8.**
12. **Refresh "Invalid TOTP" on 09-17 and 09-24 (both Thursdays) — cause unexplained;
    clock excluded** (chrony 0.9 µs offset, `NTPSynchronized=yes`, 30 s TOTP windows).
    Both failures took the retry path 30 s apart and both windows were rejected. **The
    next failed refresh is unpredictable**, and because a token outlives its printed
    expiry (§D.38.1) a failed refresh is not itself an outage — which is precisely why
    it has gone uninvestigated.
13. **PK size check after upload** — do not project a byte total; read PK's own
    reported size. Its counter read **1,796,444** for a set whose git bytes sum to
    ~3.9 MB, so PK does not count raw bytes.

## Previous session S81

| Field | Value |
|---|---|
| **Date** | 2026-09-22 → 2026-09-23 (Session 81 — **three parity layers shipped, a max-pain view repaired twice, capture depth doubled and verified, and a live broker token found readable by a public key.**) Three new SQL views, two changes to one existing view, two comment-only changes, two production selectors re-pointed, one module constant raised, a schema-wide privilege change, and a new read-only database role. |
| **Shape** | A build session interrupted twice by things that were already true and unnoticed — a credential exposure dating to at least S40, and a cron-hour mismatch that has failed twelve cycles every trading morning for an unknown length of time. **The rendering the board was reordered to at S80 did not happen, by decision**: ADR-025 Amendment B defers it until every layer carries a disposition. **Six instrumentation errors were made and corrected in-session, all mine, all the same shape.** |
| **(1) HEADLINE — ADR-025 Amendment B, and it is a REVERSAL** | **B1** rendering is deferred until every one of the fourteen layers carries a disposition — reversing S80's *"the board reorders immediately"*, which is **left in place and annotated** rather than deleted. Consequence: **D2 clause 3 is suspended, so BUILT stays 2 of 14 BY DECISION** and six computed views sit PENDING on clause 3 alone. **Written so a later reader cannot mistake a deliberate hold for the exact lapse clause 3 exists to prevent** — only the written trigger distinguishes them. **B2** the deferral covers new parity *presentation* and **does not block repairs to shipped surfaces** (the `useIvSmile` expiry collision was fixed and deployed under it). **B3** the remaining build is **days, not weeks** — spec §3 ≈ 5 working days, a **floor**. **B7** rules L3's three open decisions, standing since S79. **So the BLOCKED-ON-DECISION class is now EMPTY and every layer is BUILT or PENDING** — which is precisely the dispositional coverage B1 names as the rendering trigger. |
| **(2) Capture depth stage 1 — deployed and VERIFIED** | `EXPIRY_DEPTH = {"NIFTY": 2, "SENSEX": 2}` (`8d51cce`), first live cycle 08:30 IST 2026-09-23. **Verified 09:14 IST through `bin/roq.sh`, all four checks PASS on both symbols**: A depth landed (2 expiries / 2 run_ids), **B gamma on FRONT expiry** (NIFTY `2026-09-29` dte 6 · SENSEX `2026-09-24` dte 1), C one gamma row per cycle, D options flow on front expiry. **B could have failed**: W2 (`2026-10-06` dte 13 / `2026-10-01` dte 8) was live in the table at the same `ts`, and the pre-`89ad2bb` selector would have returned it. **That fix was the precondition** — two selectors ordered by `created_at.desc`, which returns W2 because W1 and the extra pass share one `ts` but not `created_at`; at depth 2 gamma, volatility and options flow would all have followed W2 **silently**, since each `run_id` is still single-expiry and TD-S79-NEW-12's guard never raises. **ADR-025 A1's stdout `Run ID:` precondition is true and guards nothing here** — the runner re-queries the table (B5). |
| **(3) The max-pain clock is REMOVED, not deferred** | `v_max_pain_by_strike.latest_ts` full-index-scanned **all 1,336,714 rows at 3,260 ms**; the whole view was 3,396 ms cold and, at ~68k rows/day with pg_cron jobid 19 disabled, **~28 days from the PostgREST 8 s ceiling** — after which the live Max Pain page empties silently, the ADR-021 failure mode. **A warm cache is much faster, so it would have presented INTERMITTENTLY first.** After the S72 FIX 2 skip-scan retrofit: **140.9 ms whole view, 0.18 ms `latest_ts`, 0 disk reads.** **The residual is a different quantity** — the `pain` CTE's strike × strike product, **O(strikes²), bounded by chain width and independent of table growth** — which the live re-measurement at **161.5 ms on a wider chain** confirms rather than contradicts. Equivalence: same-statement `EXCEPT` both ways, **run twice, zero rows both times**. |
| **(4) A live broker token was readable by anyone holding the public anon key** | Measured before remediation: **211** public relations where `anon` held privileges beyond SELECT · **100+** tables with RLS **off** and anon INSERT/UPDATE/DELETE · **`system_config` anon-readable including the live Dhan token.** Root cause: **S39 fixed thirteen objects and never touched the mechanism**, so every object created afterwards came up with ALL again — `v_max_pain_by_strike` (S40) at all seven privileges is the proof. **D.21.1 read *remediated* for 42 sessions while regressing.** Closed at the mechanism this time with **`ALTER DEFAULT PRIVILEGES`**, the one step S39 omitted. **D.21.2's trust model was sound and its precondition was never measured** — "RLS + GRANT is the boundary" is false wherever RLS is off. Filed as **`CASE-2026-09-22-anon-privilege-exposure.md`**; **the token-rotation decision and an API log review are still OWED.** |
| **(5) A read-only DB path — and its first real use produced a FAIL that was not real** | New role `merdian_ro` (**0 of 233** relations carry any write privilege — measured) plus `bin/roq.sh`, so the session runs its own verification queries instead of handing SQL over. **It reads 0 rows, silently, from 57 RLS-enabled tables**, because `rolbypassrls=false` and this project's policies are written `TO anon`. **It bit immediately**: the 08:53 stage-1 run reported `B → FAIL, gm=NULL` while `compute_gamma_metrics … OK` stood in the runner log — **a FAIL reported against a rollback trigger, caused by the reader.** **The six commissioning checks could not have caught it** — none reads an RLS-enabled relation. TD-S81-NEW-16. |
| **(6) Three views shipped, and one registered 41 sessions late** | **ENH-125** `v_gex_strike_rank` (L12 ranked leg) · **ENH-126** `v_gex_net_gamma_river` (L14) · **ENH-127** `v_oi_rotation_since_open` (L13 live leg) — all EXPLAIN-verified, all with `COMMENT` and `GRANT` as **live statements** so `sql/` matches the database. **ENH-128 registers `v_max_pain_by_strike` retroactively**: live on Marketview since S40 with **no register entry and no DDL in `sql/` at all** — `git log --all` for that path is empty and the register's own S40 footer claim of *"1 new SQL file"* is false. **The clearest instance of ADR-025 D2 clause 4's "one DROP from unrecoverable" the project has found.** **ENH-98 moves PROPOSED → IN BUILD** (L7/L8 are the Phase-1 consumer its deferral required) **with the build gate explicitly NOT met** — the go/no-go was inconclusive on a self-contaminated sample. |
| **Two things that were already broken and are not new** | **TD-S81-NEW-12** — the shadow runner invokes `compute_basis_context` for a **full hour every trading morning before its only input exists** (runner `*/5 03-09` against futures capture `*/5 04-09`), so twelve cycles a day exit 1 and **pin the runner's contract signal to FAIL**. Confirmed by prediction: it recovered **unaided at 04:01 UTC**, the cron-hour boundary and nowhere else. **No data is lost** — ADR-018 D2's floor blanks the stale context, which is recorded as a *validation* of ADR-023. **TD-S81-NEW-14** — the ENH-99 retry budget **has never been exercised**: the predicate retries only 429, `429` has **zero** occurrences in any retained log, and the classes that do occur (**502 ×12, 401 ×9, 500 ×2**) all fail fast. **So the ADR-025 stage-2 gate, which is decided on a week of that telemetry, cannot fire.** |
| **Six instrumentation errors, all mine, all one shape** | An `awk` filter's silence reported as a property of the script · a truncated log window read as a full day · a `grep` returning 0 whether or not the thing happened · a `tail -16` that cut off a START line and produced "NIFTY only" · a retry-label pattern **structurally incapable** of matching a W1 failure, which became "W1 never affected" **in a rollback assessment** · and a whole-file regex that would have replaced a wrong ID count (86) with a **different** wrong one (213). **Each was caught by a measurement; none by care.** A seventh, in this doc-close: **TD-S81-NEW-18 was filed this morning claiming a register entry was absent when it exists** — caught only because acting on it required opening the file. It is recorded with both the symptom as filed and as measured, not rewritten. |
| **Carry, unremediated** | **The deploy-direction inversion — SIXTH consecutive session unratified.** All S81 work was authored in `~/meridian-cc` and reached production by `git pull --ff-only`, so practice followed the corrected direction again while the written rule still says otherwise. **Seven ADRs have a file on disk and no Decision Index row** (ADR-003/-005/-006/-009/-010/-016/-019), all sitting in the *reserved IDs* table — the index cannot distinguish accepted-but-unindexed from genuinely pending. **ADR-024's Rule 11.3 carry is itself STALE**: it records "no `## Governance language` section in the ADR file" and **ADR-024 has one at line 645**. **TD-S79-NEW-6** — three untracked scratch files still in the production tree. **TD-S73-NEW-8** — `CLAUDE.md` is 317 KB against a 150 KB ceiling, and this close added to it. |
| **Ledger** | **TDs_NEW=20** (TD-S81-NEW-1..20 — **1×S1, 10×S2, 9×S3**; **derived from `tech_debt.md` headings, never incremented by hand**, and to be re-derived at read time rather than trusted from here). **TDs_CLOSED=3** — TD-S80-NEW-18 (disk guard, first scheduled run **observed**, not inferred), TD-S80-NEW-10 (**both** halves, the freshness half verified from the live view's 12 columns rather than from the notes), TD-S79-NEW-12's heading/Status contradiction. Two S81 entries closed same-session: **-17** (the max-pain clock) and **-18**. **ADRs_NEW=0. ADRs_AMENDED=1** — ADR-025 Amendment B, seven clauses, **the first amendment in this project that reverses part of its parent's Consequences**. **Enhancement Register TRIGGERED — third consecutive.** **Decision Index: first CASE row ever**, flagged as a convention extension rather than slipped in. **System Map §S81 and Deployment Topology §S81 both written**; the Local↔AWS boundary did not move. **Assumption Register: no new §D section, deliberately** — two existing rows amended instead. |
| **Project knowledge — S81 RE-UPLOAD COMPLETE** | **Completed and verified 2026-09-23**: all **13 files** live, each replaced its predecessor, **no duplicates**, content confirmed as S81 (`merdian_reference.json` **v59 / Session 81**; `CURRENT.md` leading with S81 and Amendment B). **Rule 12 discharged for this session — git and project knowledge are level.** **HEADROOM IS THE NEXT PROBLEM: 1.79 MB of a 2.00 MB cap, i.e. roughly ONE session left, and S82 must decide what comes out.** **The decision is effectively about two files**: `tech_debt.md` (**1.01 MB**) and `session_log.md` (**663 KB**) are together ~1.67 MB of that 1.79. Everything else is noise by comparison. **The remedy already has two precedents in this project** — `CLAUDE.md` → `CLAUDE_history.md` (S74) and `CURRENT.md` → `CURRENT_history.md` (S78), both splitting the archive half to **git-only** and keeping the working half in project knowledge. `tech_debt.md`'s **Resolved (audit trail)** section and `session_log.md`'s older entries are the same shape. **This is TD-S73-NEW-8 arriving at the storage cap rather than at the context ceiling**, and it will force itself next session whether or not it is planned. |
| **Next session** | **1. Rotate the Dhan token, or decide not to** — the one item with an unbounded exposure window, blocked on nobody (TD-S81-NEW-1). **2. The standing anon check** (TD-S81-NEW-3): clause 3 of the S81 fix is currently *trusted* rather than *verified*, which is the state D.21.1 was in for 42 sessions. **3. L9 stage-1's two-armed multi-expiry test** on `v_max_pain_by_strike` — and **do not lose the second arm**: the captured baseline must **DIFFER**, or the first arm passes even if the filter does nothing. |

---

