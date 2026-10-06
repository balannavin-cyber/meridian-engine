# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S90 / AM-1 (Agentic Meridian Session 1) — 2026-10-05 (Monday, live session) → 2026-10-06 05:20 IST.**
The first build session of the agentic layer: Stage 0 (spine) and the first Stage 1/2 harness
items, built beside the live system. **AM-n numbering starts here; S-numbers continue in parallel
(AM-1 = S90).** This block points and does not restate. Progress lives in **one** place, the
tracker `docs/research/s90_agentic/agentic_layer_roadmap_S90.md` (v2.7, §3 Status/Session
columns, each with linked evidence); rulings in `docs/research/s90_agentic/rulings_s90.md`
(S90-A…I); the decision in **ADR-031**. Closed **hybrid** by operator ruling: the protocol files
carry short pointer entries, and Doc Protocol v5 is drafted for ruling, not adopted.

**What was established**

1. **ADR-031 FILED and ACCEPTED (S90-C)** — the spine: data contracts with generated checks; one
   status enum (`OK/DEGRADED/STALE/MISSING/CLOSED/NOT_COMPUTED/UNKNOWN`) propagated down the
   lineage; provenance (**D3a: via `run_id` → ledger**, S90-I); rules read as-of, write path closed
   to anon (S90-E); closed days are rows; a new table states RLS in its own DDL and is checked
   after apply; `script_execution_log` is the one ledger and `merdian_ro` can read it.
2. **Production changed — 15 commits `38a0a84..ca79717`, all pushed, production fast-forwarded**
   (the last at **2026-10-06 04:53 IST, pre-market, by operator choice** over the after-16:00 rule):
   contract runner in shadow every 5 minutes writing `cycle_health` (R1.2); ENH-133
   `gex_cycle_history` applied, writer wired, reconciler scheduled (R0.4, ADR-030 front leg only
   per S90-B); the runner and every chain/gamma/vol/history writer write ledger rows carrying
   `run_id`/`product`/`status` (R0.7, R0.3); closed days written as rows and the chain ingest and
   spot capture moved onto the shared calendar gate (R0.8) — **R01-F5, a repeat of 10-02 on
   2026-10-20, closed before its date**; WCB reads live LTP (S90-G); the EOD sweep runs a full lap
   and stamps dates in IST, with a one-time +1 day migration of two tables (S90-H); six golden days
   frozen in `tests/golden/` (R2.1).
3. **Database, applied in the SQL editor** (files in `sql/`, prefix `2026-10-05_s90` /
   `2026-10-06_s90`): status enum, `data_contracts` (14), `product_lineage` (12), `cycle_health`;
   `update_parameter()` revoked from PUBLIC/anon/authenticated; `get_parameter_num(key, as_of)`;
   health views; ledger columns + `v_run_trace` + `v_provenance_coverage_daily`; `merdian_ro`
   read policies on `script_execution_log`, `merdian_parameters`, `dhan_scripmaster`; the
   dealer-flow sign fix (MV-1); DH-905 remap.
4. **Marketview live check found 12 items (MV-1…12); MV-1/2/3/5/9 fixed, MV-4 partly** —
   `docs/research/s90_agentic/marketview_live_check_S90.md`. The frontend fixes are deployed from
   `~/meridian-connect` **`265ceb0`, which is NOT in GitHub** (TD-S90-NEW-2).
5. **Twelve spine findings, R01-F1…F12** (`R0.1_spine_inventory_S90.md` §11): the orchestrator
   wrote no ledger row (F1, fixed); `equity_eod` / `breadth_indicators_daily` dates one day early
   since 2025-07 (F10, fixed); the EOD sweep covered only part of the universe each day (F11,
   fixed); **DH-905, S67's "structural" 97.83 % ceiling, was stale IDs from series changes** (F12,
   cured by hand: 28 remapped, 4 deactivated, 0 unmapped).

**Corrections to my own work — §D.46, 13 rows.** The one to carry: **the Supabase SQL editor does
not run a `BEGIN … temp table … COMMIT` script as one transaction in one session** — the DH-905
remap landed while the editor reported `42P01` (§D.46.8). Gated multi-step writes go in **one
`DO` block**.

**Registers touched:** `tech_debt.md` (**TD-S90-NEW-1…11** + S90 status footer on six existing
TDs), Assumption Register **§D.46**, Decision Index (**+ADR-031**, marker → `ADR-032+`),
Enhancement Register (ENH-133 row, change log, Part 6 footer), System Map **§S90**, Deployment
Topology **§S90**, `merdian_reference.json` **v68**, `CLAUDE.md` **v1.62**, ADR-030 S90
annotation, `CURRENT_history.md` (S88 moved). **Doc Protocol v5 DRAFT** at
`docs/operational/MERDIAN_Documentation_Protocol_v5_DRAFT.md`.

## NEXT SESSION PICKS UP

**Dated, today first.**

1. **Tue 2026-10-06, 09:30 IST — the first live day of everything above.** Runbook
   `docs/research/s90_agentic/runbook_2026-10-06_1600.md` §5 (it says 10-07: the deploy moved
   forward, so it applies **today**). ENH-133 first rows (G1–G3, A(c)–A(e), R1–R6); WCB moving on
   live ticks (S90-G); `v_provenance_coverage_daily` 100 % and `v_run_trace` for the latest cycle
   (R0.3 / R0.7 exits); runner statuses in `cycle_health` (R1.2, the sample week starts).
2. **Tue 2026-10-06, 16:10 IST — EOD run:** coverage should sit near 100 % of the active universe
   now that DH-905 is cured; `breadth_indicators_daily` complete for 10-06 by next morning.
3. **Tue 2026-10-06 — NIFTY L9 stage-1 max-pain arm** (TD-S80-NEW-1), pre-registered before any
   read — carried from S89.
4. **Wed 2026-10-07, 10:15:59 IST — A4 re-run, SENSEX dte 1** — carried from S89. **The ENH-98
   L7/L8 views were NOT applied in S90** (S90-A scoped the apply to ENH-133), so the
   pre-committed DROP has nothing to drop until they are.
5. **~Tue 2026-10-13 — drop the S90-H backup tables** after a clean week (TD-S90-NEW-11).
6. **Tue 2026-10-20 (holiday) — the first live test of R0.8:** no chain rows written,
   `cycle_health` CLOSED (TD-S89-NEW-1 closes on it).

**Undated — the tracker is the list** (roadmap §3). Next by its order: R1.10 scrip-map sync ·
push Marketview (deploy key) · R0.6 authenticated Settings write + `config_version` · R1.7 status
on Home (needs the browser read-path decision) · R0.7 fold the ADR-029 file ledger · the ~26
other inline calendar gates · R1.6 against the fixture files · R2.1 diff in the deploy path ·
**Doc Protocol v5 ruling** · ENH-133 tier (still operator-to-assign). S89's undated list stands
below.

## OPERATOR RULINGS, S90

**All rulings live in `docs/research/s90_agentic/rulings_s90.md`**, the single source.

| # | Topic |
|---|---|
| **S90-A / S90-F** | ENH-133 applied 10-05; writer wired the same night (F amends A) |
| **S90-B** | ADR-030 D1: front leg (W1) only until a W2 compute path is ruled |
| **S90-C** | ADR-031 accepted (roadmap A-8) |
| **S90-D** | Stages 0–2 inside parity scope (A-5); parity closes at the Stage 2 exit |
| **S90-E** | `update_parameter()` revoked from PUBLIC/anon/authenticated; Settings read-only |
| **S90-G** | WCB: fix the writer (live LTP over the prior close, no stale fallback) |
| **S90-H** | EOD dates: IST ingest + one-time +1 day migration |
| **S90-I** | ADR-031 D3a: provenance via `run_id` → ledger |
| **Close mode** | Hybrid close (2026-10-06 05:21 IST): the tracker holds progress; protocol files point; Doc Protocol v5 drafted, not ruled |

## Previous session S89

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

## NEXT SESSION PICKS UP — as S89 left it (SUPERSEDED by the S90 list above)

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

