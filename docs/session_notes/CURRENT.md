# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S83 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close** and **S87 at the S89 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S89 — 2026-10-03 (Saturday, out of hours), closed 2026-10-04.** Fourteen operator rulings, one
new ADR, two authored-not-applied DDL sets, a frontend deploy and a live security fix — and
**no production Python changed, no DDL applied, and the engine tree was not pulled.** Full
detail: `docs/research/capture_s89.md` §1–§6 and `docs/research/s89_rulings/rulings_s89.md`,
which is the single source for every ruling and is never restated.

**The session is 15 commits, `b31ca96..HEAD` — 8 pushed, 7 unpushed.** `64cd6d1` is
`origin/main`, a mid-session push point, **not** the session boundary; scoping the close to the
unpushed tail would have double-filed a TD and missed six commits (**§D.45.10**).

**What was established**

1. **ADR-030 FILED and ACCEPTED — per-cycle layer history (`gex_cycle_history`).** Deliberately
   short: it **points** at `ENH-133_schema_spec_S89.md` rather than restating the schema, and
   spends its words on **D1** (persist layer scalars per cycle — eleven of twelve parity views
   carry no history, so this changes what the read layer *is*) and **D2** (**outside `pg_cron`
   jobid 19, keep indefinitely**, ratifying the spec rather than setting a new value). **The DDL
   applies Mon 2026-10-05 ≥ 16:00 IST against it.** Decision Index row added, marker advanced
   **`ADR-030+` → `ADR-031+`**.
2. **ENH-98 L7/L8 designed, authored, measured pre-apply — and NOT built.** Two views
   (`v_gex_greeks_l2_strike` / `_net`), four constructs per L78-1, **analytic Black-Scholes, not
   a finite difference off the ENH-131 grid** — that grid sweeps **spot** at fixed σ and T, so it
   has no σ axis and no t axis (**§D.45.6**). Badged **PROVISIONAL — T1 pending 10-07** with a
   **pre-committed DROP** if 10-07 refuses. **Status unchanged, a sixth time: build NOT started.**
3. **`r` barely matters and `T` does — the opposite of the L3 result.** r across [0, 0.12] moves
   SENSEX dte-1 net ∂Δ/∂t by **0.22 %**; the T convention moves dte-2 net ∂Δ/∂t by a factor of
   **2.4**. dte 0 is skipped on this layer's **own** evidence, not inherited from S62: net ∂Δ/∂t
   −1,820 → −23,744 → **−156,855** Cr/day across dte 2/1/0.
4. **A live un-gated exposure found and closed.** `:80` was `default_server` with
   `root /var/www/marketview`, so **any Host but the canonical one** was served the whole SPA
   unauthenticated — measured at **651,242 B of `application/javascript`**. Now a pure redirector;
   `certbot renew --dry-run` **passes against the new config**. `:443` was never exposed.
5. **Forensics: the bundle reached scanners.** 31 un-gated asset serves, **23 external**, of which
   **15 from 14 IPs with no Referer** (DigitalOcean, Alibaba ranges). **`service_role` ×0, so no
   rotation** — but where RLS is off the GRANT alone is the boundary, and it has no watcher.
   **TD-S89-NEW-4** (SG port 80) and **TD-S89-NEW-5** (anon-grant audit) filed.
6. **L11 DECLINED-ON-EVIDENCE**, **D-5a pressure leg DECLINED-ON-EVIDENCE**, **TD-S86-NEW-9 ruled**
   (precondition gates offset/`r_eff` only, prospective from 10-07; A4 stands UNDECIDED).
7. **Marketview IV tab shipped** — `75a4015 → 6617ff6`, built and deployed, bundle verified
   byte-identical to `dist/`.

**Corrections I made to my own work inside the session** — recorded because they are the most
transferable output. **Three 200s that proved nothing** (every `:443` path returns the sign-in
page; a bogus asset returned the same page at the same size — and **“byte-identical” was itself wrong,
corrected to 8 differing bytes once `cmp` was actually run, §D.45.12). **A check that printed a verdict it never
computed** — `sudo diff` with process substitution cannot reach `/dev/fd`, and the `&&`/`||` chain
read non-execution as failure. **A grep that counted my own comment.** **"2,757 un-gated serves"
that is actually 4**, with 46 responses of 496 B left **unexplained rather than explained away**.
**A correction computed with the error it was correcting** (§D.45.9). All eleven in **§D.45**.

**Registers touched:** `tech_debt.md` (**TD-S89-NEW-1…5**; 1–3 filed mid-session, 4–5 at the
close), `MERDIAN_Assumption_Register.md` (**§D.45, 13 rows, all REFUTED, eleven my own**),
`MERDIAN_Enhancement_Register.md` (ENH-98 S89 block, ENH-133 → ADR-030, **Part 5**; Part-1 count
**derived = 124** with the handle stated, against S88's unreproducible 122), Decision Index
(**+1 row, ADR-030**), `merdian_reference.json`, System Map **§S89**, Deployment Topology **§S89**,
`CASE-2026-09-22-anon-privilege-exposure` **§10**, `CLAUDE.md` footer. **One new ADR; no ADR
amended.**

## NEXT SESSION PICKS UP

**Dated, and the first two do not slip.**

1. **Mon 2026-10-05, ≥ 16:00 IST — APPLY the two authored DDL sets.** `gex_cycle_history`
   (ADR-030) + its `pin_state.*` param seed, and the ENH-98 L7/L8 views. Both carry their own
   verification sections; the L7/L8 views land **badged PROVISIONAL**.
2. **Tue 2026-10-06 — the NIFTY L9 stage-1 max-pain arm** (TD-S80-NEW-1, owed since S82, carried
   through S85–S88). Front expiry **measured** as 2026-10-06. **Pre-register that morning, before
   any read.**
3. **Wed 2026-10-07, 10:15:59 IST — the A4 re-run, SENSEX dte 1.** The arm T1 needs, now under the
   TD-S86-NEW-9 ruling. **If T1 refuses, the L7/L8 views are DROPped** — pre-committed, so it
   cannot be renegotiated into a caveat.
4. **ENH-133 Priority Tier — OPERATOR-TO-ASSIGN.** The comparator is now in the register: **all
   thirteen sibling parity ENHs, ENH-120…ENH-132, carry Tier 1.**

**Owed, undated:** the ADR-016 write-path reconciliation (**TD-S89-NEW-2**) · the `r_sess`/`r_eff`
definitional split (**TD-S89-NEW-3**) · **TD-S89-NEW-4**'s SG decision, **IMDSv2 query first** ·
**TD-S89-NEW-5**'s anon-grant audit, starting at the two `anon=rm` views · the ADR-029 §7(e)
multi-spelling sweep (**operator-authored list; I am not to generate it**) · sandbox enable via
operator-typed `/sandbox`.

**Not in the tree, and both are cited by things that are:** the parity **dovetail doc** and
`parity_target_render_study.md` live in project knowledge only. `rulings_s89.md` cites the latter's
§A1/§A2/§F.4. **The D-4/D-5 annotations therefore landed in `MERDIAN_Hedgewall_Parity_Spec.md`**,
by operator ruling, rather than in a file this repo cannot see.

## OPERATOR RULINGS, S89

**All rulings live in `docs/research/s89_rulings/rulings_s89.md`**, which is the single source.
This table points at it and does not restate the text — a ruling transcribed into a second place
is a ruling that can drift out of agreement with itself.

| # | Topic |
|---|---|
| **ADR-029 #13 / #14** | Sandbox enable deferred; install cost measured; network allowlist scoped. §7(e) deny-bypass confirmed on fresh ground, **one form only** |
| **TD-S86-NEW-9** | The ≥ 3×SE precondition gates **offset/`r_eff` only**; prospective from 10-07; A4 stands UNDECIDED |
| **D-1 … D-6** | Parity dovetail: adopt the §1.2 mapping; design re-approval with pin-state gated; ENH-133 into parity as a **complement** to ENH-134; **our measured bands only** |
| **D-4** | Flow-vs-book ΔOI folds into **ENH-98 L7/L8 scope** as a parity prerequisite, not a §2.5 extension |
| **D-5a / D-5b / D-5c** | Pressure ranking **DECLINED-ON-EVIDENCE**; time boost and conviction as **D3 deviations** |
| **E-D2 / E-D5 / E-D7 / E-D8** | Phase-1 board decisions; net-long-γ stored column **matched on both symbols** |
| **ENH-133 scope** | Five scope decisions; bound spec; **tier still to assign** |
| **L11** | **PENDING → DECLINED-ON-EVIDENCE** |
| **L78-1 / -2 / -3** | Compute **both** constructs under distinct names; standing book primary; one daily 10:15 reading, calendar decay |
| **CASE disposition** | **UPDATE** `CASE-2026-09-22`, do not open a new one |
| **Parity spec `:292`** | State the parsed sums and the missing day-length factor — **do not publish another rounded guess** |

## Previous session S88

**S88 — 2026-10-01 (Thursday, SENSEX expiry day), closed 2026-10-02.** One pre-registered test
passed three times; everything else measured was negative, a correction, or a refusal by design.
Full detail: `docs/research/capture_s88.md` §1–§6, with §5.7 correcting §5.3.

**What was established**

1. **L9 stage-1 max-pain, SENSEX arm: PASS ×3** (§1). Pre-registered before any OI or expiry data
   was read; instrument hash verified before each run. PASS at **12:45:07, 14:55:06, 15:30:06 IST**
   — arm A 0/0 both ways, arm B 197/197, no tie at minimum `total_pain` in any body. Mechanism:
   W2-only strikes 0 and all three `max_pain_strike` agreeing, so **all 197 differing rows differ
   in `total_pain` alone — the expiry mixture moved the magnitude and never the published level**,
   while shared strikes where W2 OI > W1 grew 6 → 12 → 16. **TD-S80-NEW-1 is NOT closed: the NIFTY
   arm is owed, next NIFTY expiry 2026-10-06 (measured).**
2. **The S82 instrument did not exist in the tree and was rebuilt** (§1.2), stated as rebuilt
   rather than implied continuous.
3. **Marketview header reads a close two sessions old during every session** (§3, **TD-S88-NEW-1**).
   Writer at **16:10 IST** (crontab line 24) + a newest-row reader with no date filter. NIFTY
   2026-10-01: **−1.2953 %** shown against a settled **−0.8775 %** — overstated **0.4178 pp, 48 %
   too large**; SENSEX only 0.0667 pp, and that is luck, not safety — the error is the gap between
   two consecutive closes and is **unbounded**. **Fix belongs in the read layer**; moving the cron
   cannot work, because no settled close exists before 16:00.
4. **`open_0915_spot` is the 09:16 bar's CLOSE**, not the 09:15 open (§3.3, D.44.5) — proven by
   comparison, 4/4, with `ohlc_open ≠ ohlc_close` on all 4 so the test was not vacuous.
5. **The all-layers reconstruction returned a NEGATIVE result** (§5). 90/90 spine cells and
   **540/540 layer cells** admitted on exact `ts` equality. **On the built layers, 2026-10-01 was
   not distinguishable from the other five SENSEX expiry days before 12:15** — below chance on
   SET A (34 vs 36), 5 above on SET B (38 vs 33). **08-27 scored highest in both** and its range is
   **rank 5 of 17, 44 % of 10-01's**.
6. **Eleven of twelve parity views carry no history** (D.44.3); L3 refuses wholesale on dte 0, L10
   **partially** (keeps `ce_iv`/`pe_iv`), L9 publishes throughout and was limited by chain depth —
   **and all of that was already documented at `MERDIAN_System_Map.md:1963-1976`** (§5.7).

**Corrections I made to my own work inside the session** — recorded because they are the session's
most transferable output: a **UTC/IST cast** that would have pinned every bucket to the same run
and looked plausible (D.44.4); a **register-contradiction claim** that was an omission, not a
conflict (§2.5 ii → §3.2, D.44.7); **"L10 is empty"**, too strong (§5.7, D.44.10); and a
**NIFTY/SENSEX number mix** in a TD row, rebuilt with the arithmetic asserted against the artefact.

**Registers touched:** `tech_debt.md` (TD-S88-NEW-1; update rows on TD-S81-NEW-16 and
TD-S80-NEW-1), `MERDIAN_Assumption_Register.md` (**§D.44, 10 rows, all REFUTED**),
`MERDIAN_Enhancement_Register.md` (**ENH-133…138, all PROPOSED**; Part 1 count recomputed
**116 → 122**, having drifted 4 since S81 despite the "derive, don't carry" rule),
`merdian_reference.json`, System Map §S88, `CLAUDE.md` footer. **No new ADR.**

## NEXT SESSION PICKS UP — as S88 left it (SUPERSEDED by the S89 list above)

**Dated, in order:**

1. **Sat 2026-10-03, out of market hours** — ADR-029 **#13/#14**: sandbox enable plus install and
   network-allowlist cost, and the Bash deny-bypass gap with the untested spellings enumerated first.
2. **TD-S86-NEW-9 — the owed operator ruling, BEFORE 2026-10-07.** §2.6's ≥ 3×SE precondition does
   not say whether it gates the gamma reading or only the offset reading, and on A4's data the two
   give **different T1 verdicts**. Must be ruled, pre-registered and dated before the next arm runs.
3. **Tue 2026-10-06 — the NIFTY L9 stage-1 arm** (TD-S80-NEW-1, owed since S82, carried through
   S85/S86/S87/S88). Front expiry **measured** as 2026-10-06. **Pre-register that morning, before
   any read**, by the §1.3 verdict order; the instrument is `scratch/s88_l9/l9_rebuilt_source.sql`
   with the scope CTE set to NIFTY and that day's W1.
4. **Optional, before 2026-10-06** — a pre-registered threshold for the fixed-strike OI tilt and/or
   `ratio_pct`, if either is to be tested rather than described. **Unstamped means not a test.**
5. **Wed 2026-10-07, 10:15:59 IST — A4 re-run**, SENSEX dte 1, gated on item 2.

**PARITY BUILD QUEUE — S88's stated priority, and it comes before the ENH queue.**

- **(a) TD-S88-NEW-1 repair.** A Lovable read-layer prompt was **drafted in chat 2026-10-01** and is
  not in the tree. **Precondition before it ships:** a **single-run anon check in the SQL editor**
  — one execution carrying `current_user` beside its rows — against `trading_calendar` and
  `market_spot_snapshots` (the **16:00–16:10 IST `dhan_idx_i`** rows). `merdian_ro` cannot run it
  (`permission denied to set role "anon"`), so it belongs to the editor under postgres.
- **(b) §H phased Lovable prompts for the board.** Design doc **§A–G APPROVED 2026-10-01 13:04 IST
  with four additions R1–R4**; the **§B.1a bindings are measured** (§2.2–§2.4). Note for whoever
  writes them: `basis_pct` is a **futures-calendar artefact** across days (§5.4) and `open_0915_spot`
  is the **09:16 close** (D.44.5) — both bindings must carry those qualifications.
- **(c) Snapshot export into the board canvas.**

**Build queue — nothing started, all operator-gated:** ENH-133…138 (Part 4 S88 footer).
**ENH-133 and ENH-134 are alternatives, not a sequence.** **ENH-135 revisits a deliberate S62
decision and is not a defect report.** **ENH-137 is shadow-only under ADR-029.**

**Rulings owed:**

- The **six ENH dispositions** (ENH-133…138).
- The **five candidate rule lines** in `docs/research/s88_rule_lines_PROPOSED.md` — **proposed, not
  applied, and deliberately NOT in `.claude/rules/`**.
- Whether **`open_0915_spot` taking the 09:16 close is intended**, and whether `gap_open_pct`
  should be recomputed off `raw->>'ohlc_open'`.
- **L11 — decline or pending.** The design doc now says **PENDING**; the disposition is unresolved. **[SUPERSEDED 2026-10-03 — RULED DECLINED-ON-EVIDENCE.** Absent from the parity target's terminal sample, composition-only, 0–10 scaling undisclosed; ADR-025 D3 + D4. Ruling: `docs/research/s89_rulings/rulings_s89.md` → "L11 (five-axis radar)"; ADR-025 `:91` and `:346` carry the stamp. **Annotated rather than rewritten, so the record of what S88 believed survives.]**
- **E-D1 … E-D8:** `gex_cr` unit · canonical max pain · theme · legacy pin · NET-LONG γ source ·
  signal row · ACCEL retirement · prototype corrections.
- **TD-S87-NEW-1** (parked, S3) · the **CLI unpin** · the **five documents carrying the copied
  "150k" figure**.

**Owed probe:** `scratch/s88_design/markers_check` — the anon-path read in one execution carrying
`current_user`, and `created_at` sampling on marker rows.

## OPERATOR RULINGS, S88

Recorded because each changed what was measured or what was written.

- **Parity board design doc §A–G APPROVED** 2026-10-01 13:04 IST, **with four additions R1–R4** —
  change marks on spot/VIX and the other levels; futures with basis and its change vs the previous
  session; the pre-open print; the gap up/down.
- **The tie clause gates BOTH arms, and all three bodies are counted**, evaluated before either
  arm is read — a tie can fake arm A *and* arm B. **P3 accepted** (independently derived leg 1).
  Both ruled **before** any OI or expiry data was read (§1.3).
- **Engine pull is operator-terminal only.** Nothing under `~/meridian-engine` runs from Claude
  Code, `git fetch` included. **Standing rule.**
- **Claude Code runs in a plain SSM shell, not tmux.** Resume with
  `cd /home/ssm-user/meridian-cc && claude --continue`.
- **§4.5's wording kept as written** (the quartile result stated with its caveats inline).
- **Price levels dropped from scoring; `d_oi_tilt` dropped from SET B** — both confounds named by
  the operator, both recorded in the output rather than silently applied.
- **Rule lines go to `docs/research/`, not `.claude/rules/`** — they are operator rules.

