# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S82 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, each moved verbatim rather than retyped. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**Session 83 — 2026-09-24 → 2026-09-25 (Thu–Fri).** Build. Three ADR-025 parity
layers authored, validated and deployed; **production Python unchanged**.

| Field | Value |
|---|---|
| **Shipped** | **ENH-130** `v_iv_term_structure` (L9, 17 cols) · **ENH-131** `v_gex_repriced_flip` (L3, 18 cols) · **ENH-132** `v_iv_surface` (L10, 21 cols). Applied by the operator in the Supabase editor. Anon path verified by `SET ROLE anon`, not by object existence. |
| **Parity count** | **BUILT STAYS 2 of 14.** ADR-025 D2 clauses 1/2/4 MET on all three; **clause 3 PENDING BY DECISION** under Amendment B1. Three ships that deliberately do not move the count — B1 working as written, not a lapse. |
| **The gate record** | **Three of ENH-131's five gates FAILED** and the full record lives in the view's own COMMENT. Gate 2 compared a heavily-cancelled net against 1 % where net/gross runs **0.0095–0.341**; Gate 3(ii) used a ±5 % window blind to a 2→1 crossing-count change; Gate 4's ±0.01 r band was **~19× narrower** than the dispersion it bounded. Gate 5 passed 5/5 on three out-of-sample arms. |
| **Four mis-specified gates, none loosened** | One shape: a threshold set before the quantity's scale was derived. Now a CLAUDE.md settled bullet. The builds shipped on separately pre-registered replacements, not on relaxed thresholds. |
| **Host change** | One `mv`: `/etc/logrotate.d/meridian.PRE_20260922` → `/root/`. **TD-S83-NEW-1 filed and CLOSED** on an **observed** clean run (`Finished Rotate log files.` 2026-09-25 00:00:03), not on the fix. |
| **Ledger** | TDs_NEW=7 (TD-S83-NEW-1..7), TDs_CLOSED=1. ADRs_NEW=0, ADRs_AMENDED=0, **no Decision Index row — stated as a decision**. Enhancement Register TRIGGERED, fifth consecutive session. |

**Three things this session got wrong and recorded rather than absorbed.** Five
figures in one COMMENT draft were wrong because they were read off rendered tables
instead of files, and the queries had never been saved to `.out`. A `journalctl`
read returning `No entries` was a **no-test**, not a clean result — the `sudo` read
returned two nights of logrotate failures. And **the capture file written to drive
this doc-close was itself wrong twice**: it predicted `[ -- ] NOT AUDITABLE` on a
check that printed `[ OK ]`, and it blamed ADR-015 for a column naming the ADR does
not use. All filed — §D.39, TD-S83-NEW-7.

**`equity_intraday_last` is auditable on the schedule, and the S82 claim that it
reads `[ -- ] NOT AUDITABLE` every night by design was wrong.** The mechanism is in
§D.39.4, read from `scripts/eod_health_check.py:367-419`: NOT AUDITABLE requires the
one-generation table to have moved **past** the audited date, and the 00:45 UTC slot
runs **before** that day's successor refresh. Do not repeat the "every night" claim.

## NEXT SESSION PICKS UP

1. **Capture depth — the one decision that blocks two layers.** SENSEX furthest
   listed expiry, NIFTY 5th leg, or formally record the ADR-025 **D3 deviation**.
   Recommendation on record: add current + next **monthly** expiries (4 legs) as its
   own measured ENH. Blocks L9 comparability and L10 depth; blocks neither build.
2. **Scrub the reference product name from existing registers** (the parity spec
   filename, ADR-025, older notes). New S83 lines already carry none.
3. **`authenticated` / `service_role` default grants on new views** — Supabase
   defaults gave both privileges on all three; flagged at deploy, not acted on.
4. **Send the vendor methodology question on Greeks/IV** (drafted, not sent) — one
   route to closing TD-S83-NEW-4 and TD-S83-NEW-5.
5. **2026-09-29 — NIFTY L9 stage-1 max-pain arm** (TD-S80-NEW-1).
6. **ENH-98 re-run with SENSEX at dte 1–2**; the multi-DTE offset test.
7. **Parity build order continues: L7/L8 (ENH-98) next.**
8. Everything under the S82 block's "Decisions owed" that S83 did not touch carries
   unchanged.

## Previous session S82


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
