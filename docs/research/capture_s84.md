# capture_s84.md — Session 84 measurement capture

**Date:** 2026-09-25 (Fri — `scratch/s84_l78/z1_td_and_weekdays.out:23`)
**Scope of this file:** every number below is copied from a named scratch `.out` file, with `path:line` beside it. No number is from memory, and none is transcribed from a rendered table in the conversation. Where a figure was measured by the operator rather than by this tool, it is labelled **OPERATOR-MEASURED** and carries no `.out` citation, because none exists.

**Citation convention.** `path:line` refers to the line number *within the named `.out` file*, obtainable with `cat -n`. The two citation indexes are `scratch/s84_l78/z3_cite_item0.out` and `scratch/s84_l78/z4_cite_l78.out`.

---

## 0. Shape

Measure-only session to this point. **No production change. No DDL. No write of any kind to the database.** Every query issued by this tool ran through `bin/roq.sh` as `merdian_ro`, a SELECT-only login with `default_transaction_read_only=on` and a 30 s `statement_timeout`.

Nothing was created, edited or deleted under `~/meridian-engine` in any step of this session except a single read: `git -C ~/meridian-engine rev-parse HEAD`. All scratch artefacts live in the authoring tree, under `~/meridian-cc/scratch/s84_item0/` and `~/meridian-cc/scratch/s84_l78/`.

---

## 1. Item 0 — deployment identity and the three S83 views

### 1.1 Three-way hash

| tree | commit | source |
|---|---|---|
| authoring (`~/meridian-cc`) HEAD | `18c2fb8a4ce27e67027aa5ea16b508c24adbaeb3` | `scratch/s84_item0/a1_fetch_revparse.out:5` |
| `origin/main` | `18c2fb8a4ce27e67027aa5ea16b508c24adbaeb3` | `scratch/s84_item0/a1_fetch_revparse.out:6` |
| EC2 (`~/meridian-engine`) HEAD, **before the pull** | `bb374aee856af09725a05d8dd47cb08c202bcabb` | `scratch/s84_item0/a2_engine_head.out:1` |

EC2 was **behind, cleanly**: `git merge-base --is-ancestor <engineHEAD> origin/main` returned `rc=0` (`scratch/s84_item0/a3_ancestry_count.out:5`), and the gap was **1 commit** (`a3_ancestry_count.out:8`) touching **16 files** (`a4_diff_names.out:20`) of which **0 end in `.py`** (`a4_diff_names.out:22`; the explicit listing returned `(none)` at `a4_diff_names.out:25`). The 16 names are 13 docs plus the three S83 `sql/` files (`a4_diff_names.out:2-17`).

**The pull — operator-run; terminal output pasted in the session.** Performed at **16:51 IST on 2026-09-25**. The pasted output ends:

```
Fast-forward bb374ae..18c2fb8, 16 files
18c2fb8a4ce27e67027aa5ea16b508c24adbaeb3
```

A fast-forward over 16 files is exactly the shape the pre-pull measurement predicted (ancestor, 1 commit, 16 names), so the two readings corroborate. **This session holds no `.out` file for the post-pull EC2 HEAD**, because `~/meridian-engine` was placed off-limits after the single `rev-parse`; the alignment is recorded from the pasted terminal output, not from a command this tool ran. **Owed at next session open:** one line, `git -C ~/meridian-engine rev-parse HEAD`, to close the loop with a measurement of this tool's own.

### 1.2 `COMMENT ON VIEW` length and md5 — live vs the `sql/` file literal

Expected values were **computed from the `sql/` file literal**, not recalled (`scratch/s84_item0/c1_expected_from_files.out:1` states the derivation).

| view | expected len / md5 (from file) | live len / md5 | verdict |
|---|---|---|---|
| `v_gex_repriced_flip` | 6997 / `d12ef107140ca423c83e0275ced58b7a` — `c1_expected_from_files.out:3` | 6997 / `d12ef107140ca423c83e0275ced58b7a` — `c1_comments.out:4` | MATCH |
| `v_iv_surface` | 4709 / `adff5d5a7ab68f79c74ec36b052ea93d` — `c1_expected_from_files.out:4` | 4709 / `adff5d5a7ab68f79c74ec36b052ea93d` — `c1_comments.out:5` | MATCH |
| `v_iv_term_structure` | 4922 / `a8fa5b05a873b7ea697e4eba27ae8864` — `c1_expected_from_files.out:5` | 4922 / `a8fa5b05a873b7ea697e4eba27ae8864` — `c1_comments.out:6` | MATCH |

`v_iv_surface`'s comment is assembled from **49 adjacent concatenated string literals** (`c1_expected_from_files.out:4`, column `parts`); the other two are single literals (`:3`, `:5`). A first extraction that was not concat-aware read 93 chars and was corrected before any comparison was published — see §5.

### 1.3 Grants

`anon` holds **`SELECT` and nothing else** on all three views: `v_gex_repriced_flip` (`c2_grants.out:5`), `v_iv_surface` (`:10`), `v_iv_term_structure` (`:15`). This matches the `REVOKE ALL … FROM anon` + `GRANT SELECT … TO anon` pairs that ship live in each `sql/` file.

`merdian_ro` also holds `SELECT` on all three (`c2_grants.out:8`, `:13`, `:18`) — **but only `sql/2026-09-25_s83_v_iv_surface.sql:303` contains that `GRANT` statement.** The other two files do not. See §4.

### 1.4 The anon path — VERIFIED (operator-run in the Supabase editor; no `.out`, recorded as OPERATOR-MEASURED)

Run by the operator at **~10:52 IST on 2026-09-25**, in the Supabase SQL editor, as a single execution:

```sql
BEGIN;
SET LOCAL ROLE anon;
SELECT current_user AS role_now,
       (SELECT count(*) FROM public.v_iv_term_structure) AS l9,
       (SELECT count(*) FROM public.v_gex_repriced_flip) AS l3,
       (SELECT count(*) FROM public.v_iv_surface)        AS l10;
COMMIT;
```

Result: **`role_now = anon`, `l9 = 4`, `l3 = 2`, `l10 = 868`.** The acting role is carried by the same result set as the counts, which is what makes this evidence of a *path* rather than of three numbers.

**The control that makes it a test.** The identical query **without** the role switch returned **`role_now = postgres`** with the same counts. That is the load-bearing observation: it demonstrates the editor executes each run as a **new session**, so a `SET ROLE` issued in one run does not survive into the next. A two-run check — switch role in run 1, count in run 2 — would have reported `postgres` counts while appearing to test `anon`. This is the S83 no-test shape, and the single-run form is what escapes it.

**Sub-point, measured by this tool:** the same check **cannot be run through `bin/roq.sh`**. `merdian_ro` is not a member of `anon`, and the attempt returns `ERROR: permission denied to set role "anon"`, `rc=3` (`scratch/s84_l78/z2_anon_path.out:14-15`). The anon path is therefore verifiable **only** from the editor under the postgres role — which is why the evidence above is operator-measured and not an `.out` in this tree.

> **Note on a coincidence, stated so it is not mistaken for a second measurement.** The EXPLAIN plans run as `merdian_ro` carry top-level `actual rows` of 4, 2 and 868 (`c345_seqscan_counts.out:15-17`) — the same three integers. They agree because the views return the same rows to both roles, but **the anon evidence is the editor result above**, not the plan rows. The two are independent readings that happen to coincide.

What was additionally established about readability by this tool: RLS is **off** on all three views' base tables — `option_chain_snapshots`, `trading_calendar`, `index_futures_snapshots` all read `rls_on = f` with `0` policies (`scratch/s84_item0/b7_rls_live.out`), and a `LIMIT 1` probe returned `1` for each (`scratch/s84_item0/b8_readability_control.out`), satisfying the TD-S81-NEW-16 non-zero control.

### 1.5 EXPLAIN — index access and timings

**`Seq Scan` count = 0 on all three plans**: `c345_seqscan_counts.out:2`, `:3`, `:4`; a direct grep for any `Seq Scan` line returned `(no Seq Scan anywhere)` (`:7`).

| view | first (cold) run | rows |
|---|---|---|
| `v_iv_term_structure` | 15.149 ms — `c345_seqscan_counts.out:10` | 4 — `:15` |
| `v_gex_repriced_flip` | 269.899 ms — `:11` | 2 — `:16` |
| `v_iv_surface` | 27.238 ms — `:12` | 868 — `:17` |

**Cold/warm note.** The 15.149 ms first reading for `v_iv_term_structure` is a cold-cache figure. Three warm repeats returned **9.345 / 9.296 / 9.259 ms** (`c3b_repeat_variance.out:2-4`). The recorded L9 baseline is **10.228 ms** (`scratch/s84_l78/d2_l9_baseline.out`, from `scratch/s83_l9/21_v6.out:120`), and the `sql/` file states the expectation qualitatively as *"an execution time in single-digit ms"* (`sql/2026-09-24_s83_v_iv_term_structure.sql:254`). Warm, the view meets both; cold, it meets neither. **A single timing sample against this threshold would have produced a MISS that the warm repeats refute.**

### 1.6 L3 — `NO_CROSSING` on SENSEX is the designed path

Observed at the latest cycle: `NIFTY | OK` with flip `23053.6467696562` and `flip_sigma −0.0286995365484342` (`c6_status_and_skew.out:5`); `SENSEX | NO_CROSSING` with flip and `flip_sigma` both NULL, `n_r_rows = 79` (`c6_status_and_skew.out:6`).

The status is emitted at exactly one site:

> `WHEN n.s_star IS NULL          THEN 'NO_CROSSING'` — `sql/2026-09-25_s83_v_gex_repriced_flip.sql:354`, quoted at `scratch/s84_l78/s3a_no_crossing.out:2`

and named in the view comment:

> *"STATUS values are OK, SKIPPED_EXPIRY, UNMEASURABLE_R and NO_CROSSING; flip is NULL on all but OK."* — `sql/2026-09-25_s83_v_gex_repriced_flip.sql:366`, quoted at `scratch/s84_l78/s3a_no_crossing.out:3`

Precedence is `dte=0 → SKIPPED_EXPIRY`, then `n_r_rows < 6 → UNMEASURABLE_R`, then `NO_CROSSING`, else `OK` (`:352-356`). SENSEX carried `n_r_rows = 79` and a non-zero DTE, so it reached the third clause: **TotalGEX did not change sign anywhere in the ±10 % sweep** described at `:366`. The branch is reachable and fired — it is not a Rule 0 dead arm.

### 1.7 L10 — `leg_skew_98` per leg

| symbol | leg | expiry | `leg_skew_98` | `leg_status` | source |
|---|---|---|---|---|---|
| NIFTY | 1 | 2026-09-29 | 2.6574111122367170 | OK | `c6_status_and_skew.out:13` |
| NIFTY | 2 | 2026-10-06 | 2.0855544627957945 | OK | `c6_status_and_skew.out:14` |
| SENSEX | 1 | 2026-10-01 | 1.6397155801306840 | OK | `c6_status_and_skew.out:15` |
| SENSEX | 2 | 2026-10-08 | 1.5054204791265535 | OK | `c6_status_and_skew.out:16` |

---

## 2. ENH-98 — instrument recovery and two arms

### 2.1 Instrument provenance

The S81 go/no-go query was **never saved as a file**. It exists only as a fenced block in `docs/session_notes/s81_docclose_notes.md:696-773` (78 body lines). Extracted verbatim to `scratch/s84_l78/s81_gonogo_query.sql`, its sha256 is

> `d5930ee55d608aadb53204950a1ec3ab9cb16def294cdc00c5b936253e24e912` — `scratch/s84_l78/s1j_paths_sha_lines.out:11`

and the file measures **78 lines** (`s1j_paths_sha_lines.out:8`). The matching variant is **LF line endings with a trailing newline**; LF-without-trailing-newline, CRLF-with and CRLF-without all differ (`scratch/s84_l78/s1h_sha_variants.out`).

The token `implied_pts` appears **in no file anywhere in the authoring tree** outside two registers; `git log -S` shows it entering only in the S82 doc-close commit (`scratch/s84_l78/s1c_full_sweep.out`). The column the instrument actually emits is `implied_spot_offset_pts`, computed from `implied_dspot`.

### 2.2 The two pinned arms

| file | sha256 | diff vs instrument |
|---|---|---|
| `s81_gonogo_query.sql` | `d5930ee55d608aad…e24e912` — `a_diff_sha.out:18` | — |
| `a0.sql` | `77533b1575ca16f769e79addc7489d669cf0a32af0008a47cff25ac7f6f92288` — `a_diff_sha.out:19` | one hunk, `4c4,5` — `a_diff_sha.out:2-6` |
| `a1.sql` | `cdee2acb583e01c88c44888a74092aad83d5a2d1c893a8a5b2f7f059552f328a` — `a_diff_sha.out:20` | one hunk, `4c4,5` — `a_diff_sha.out:10-14` |

The only edit is the window cap on line 4. The `latest` CTE (`max(ts) … GROUP BY symbol`, line 6) is untouched, so `max(ts)` over a window ending at the target **is** "latest ts ≤ target, per symbol".

Resolved cycles (`a_resolved_ts.out:4-7`): **A0 → 2026-09-24 14:10:07 IST** both symbols; **A1 → 2026-09-25 11:00:07 IST** both symbols. The 5-minute cadence means the A0 target of 14:12:59 resolves back to the 14:10 cycle.

### 2.3 A0 — reproduction of the S82 record: **12 / 12 MATCH**

Expected values were printed into the output file **before** the run (`a0_result.out:1-20`).

| symbol | conv | check | expected | observed | verdict |
|---|---|---|---|---|---|
| NIFTY | exact/365 | gamma_relerr ATM | 0.0251 (`a0_result.out:6`) | 0.0251 (`a0_result.out:31`) | MATCH |
| NIFTY | exact/365 | gamma_relerr NEAR | 0.0419 (`:6`) | 0.0419 (`:33`) | MATCH |
| NIFTY | dte/365 | gamma_relerr ATM | 0.0307 (`:7`) | 0.0307 (`:28`) | MATCH |
| NIFTY | dte/365 | gamma_relerr NEAR | 0.0438 (`:7`) | 0.0438 (`:30`) | MATCH |
| NIFTY | dte/252 | gamma_relerr ATM | 0.1336 (`:8`) | 0.1336 (`:25`) | MATCH |
| NIFTY | exact/365 | delta_abserr ATM | 0.0139 (`:9`) | 0.0139 (`:31`) | MATCH |
| NIFTY | dte/365 | delta_abserr ATM | 0.0140 (`:10`) | 0.0140 (`:28`) | MATCH |
| NIFTY | all | rows after band | 86 = 20/31/35 (`:11`) | 20 (`:31`) / 31 (`:33`) / 35 (`:32`) | MATCH |
| SENSEX | — | dte | 0 (`:14`) | 0 (`:34`) | MATCH |
| SENSEX | exact/365 | gamma_relerr ATM | 0.83 (`:15`) | 0.8336 (`:34`) | MATCH at printed precision |
| SENSEX | exact/365 | gamma_relerr NEAR / FAR | 0.99 / 1.07 (`:15`) | 0.9918 (`:36`) / 1.0732 (`:35`) | MATCH at printed precision |
| SENSEX | dte/365, dte/252 | rows | 0 (`:16`, `:17`) | absent from the 12-row result (`:37`) | MATCH |

**No MISS.** The S82 figures reproduce exactly from a query recovered out of a markdown fence.

### 2.4 A1 — new point, 2026-09-25 11:00:07 IST

No expected values exist for this cycle. NIFTY `dte = 4`; SENSEX `dte = 6` (`a1_result.out:7`, `:16`).

Rows valid → after the delta band (`a1_rows_band.out:17-24`): NIFTY ATM 18→18 (`:17`), NEAR 32→25 (`:19`), FAR 113→20 (`:18`), total 163→63 (`:20`); SENSEX ATM 30→30 (`:21`), NEAR 54→52 (`:23`), FAR 143→60 (`:22`), total 227→142 (`:24`).

| symbol | conv | gamma_relerr ATM/NEAR/FAR | delta_abserr ATM/NEAR/FAR | implied_pts ATM/NEAR/FAR | source lines |
|---|---|---|---|---|---|
| NIFTY | exact/365 | 0.0336 / 0.0324 / 0.0320 | 0.0141 / 0.0023 / 0.0055 | 9.8 / 1.6 / −28.8 | `a1_result.out:13,15,14` |
| NIFTY | dte/365 | 0.0522 / 0.0349 / 0.0517 | 0.0142 / 0.0062 / 0.0096 | 9.7 / −5.2 / −53.8 | `a1_result.out:10,12,11` |
| NIFTY | dte/252 | 0.1106 / 0.0511 / 0.0858 | 0.0194 / 0.0301 / 0.0244 | 10.0 / 52.2 / 151.9 | `a1_result.out:7,9,8` |
| SENSEX | exact/365 | 0.0204 / 0.0519 / 0.0543 | 0.0151 / 0.0075 / 0.0034 | 45.5 / 48.1 / 1.7 | `a1_result.out:22,24,23` |
| SENSEX | dte/365 | 0.0357 / 0.0518 / 0.0477 | 0.0155 / 0.0102 / 0.0063 | 45.6 / 46.3 / −33.8 | `a1_result.out:19,21,20` |
| SENSEX | dte/252 | 0.1275 / 0.0632 / 0.1101 | 0.0165 / 0.0333 / 0.0311 | 40.6 / 167.1 / 372.0 | `a1_result.out:16,18,17` |

ATM within-cycle spread of `implied_spot_offset_pts`, p10 / p50 / p90 and p10–p90 (`a1_atm_spread.out:7-12`): NIFTY exact/365 5.4 / 9.8 / 14.7, spread **9.3** (`:9`); NIFTY dte/365 1.7 / 9.7 / 18.3, spread **16.6** (`:8`); NIFTY dte/252 −13.3 / 10.0 / 33.2, spread **46.5** (`:7`); SENSEX exact/365 35.4 / 45.5 / 57.2, spread **21.8** (`:12`); SENSEX dte/365 28.0 / 45.6 / 66.5, spread **38.5** (`:11`); SENSEX dte/252 −56.1 / 40.6 / 135.2, spread **191.4** (`:10`).

### 2.5 `r_eff` — **INFORMATIONAL (T3)**

Scope: `exact/365` only, bucket `ATM` only. Definitions computed in SQL, not by typed arithmetic (`r_eff.out:9-12`): `T = median(secs_to_expiry)/(365×86400)`; `r_eff = median(implied_dspot)/(median(spot)×T)`; `SE(med) = 1.2533 × stddev_samp/√n`.

| arm | symbol | n | dte | spot | secs_to_expiry | T | median implied_pts | sd | SE(median) | r_eff | source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | NIFTY | 20 | 5 | 23074.45 | 436792.7 | 0.01385061 | 12.2 | 3.325 | 0.932 | 0.038125 | `r_eff.out:19` |
| A0 | SENSEX | 30 | 0 | 73663.58 | 4792.9 | 0.00015198 | 22.9 | 4216.600 | 964.843 | 2.045176 | `r_eff.out:20` |
| A1 | NIFTY | 18 | 4 | 23063.55 | 361792.5 | 0.01147236 | 9.8 | 3.686 | 1.089 | 0.037034 | `r_eff.out:28` |
| A1 | SENSEX | 30 | 6 | 73635.77 | 534592.4 | 0.01695181 | 45.5 | 8.979 | 2.054 | 0.036416 | `r_eff.out:29` |

`spot_min = spot_med = spot_max` on all four rows (`r_eff.out:19-20`, `:28-29`), so spot is constant within each cycle. The A0 SENSEX row is the `dte = 0` cycle: its `T` is ~91× smaller than the others and its `SE(median)` of 964.843 exceeds its own median of 22.9 — it is excluded from the three-point reading in §3(e), and it fails the §2.6 precondition.

Helper provenance: `a0_reff.sql` / `a1_reff.sql` reuse CTE chain lines 1–54 byte-identically from `a0.sql` / `a1.sql`, with the bucket `CASE` verbatim from `:57-59` and `implied_dspot` verbatim from `:66-67`; all six byte-compares pass (`scratch/s84_l78/reff_provenance.out`). Only the final `SELECT` differs.

### 2.6 Pre-registration as amended (for A2–A4)

**Instrument.** `scratch/s84_l78/s81_gonogo_query.sql` (sha256 `d5930ee55d608aad…`, `s1j_paths_sha_lines.out:11`), with **a one-line `ts` pin per arm** and no other edit — the `4c4,5` hunk shape already exercised at §2.2.

**T1 — the SOLE go/no-go.** Refuse if the `exact/365` `gamma_relerr` median exceeds **0.10 in BOTH ATM and NEAR**, evaluated at **SENSEX dte 1–2**.

| arm | date | SENSEX dte | NIFTY dte | role |
|---|---|---|---|---|
| A2 | Mon 2026-09-28 (`z1_td_and_weekdays.out:24`) | 3 | 1 | gradient point |
| A3 | Tue 2026-09-29 (`z1_td_and_weekdays.out:25`) | **2** | 0 — void, `SKIPPED_EXPIRY` | **T1 arm** |
| A4 | Wed 2026-09-30 | **1** | 6 — front rolls to 2026-10-06 | **T1 arm** |

The NIFTY legs on A3 and A4 are stated because they are not absent, only unusable or re-based: NIFTY front expiry is 2026-09-29 (`c6_status_and_skew.out:5`) and NIFTY leg 2 is 2026-10-06 (`c6_status_and_skew.out:14`), so Tue is NIFTY's own expiry day and Wed reads against the rolled front.

**T2 and T3 are INFORMATIONAL** and bear on the vendor's convention, not on the go/no-go. T2: offset scaling against `T`, cut at `sqrt(T_hi/T_lo)`. T3: `r_eff` constant within ±25 % — the §2.5 table is its first reading.

**Corrected precondition.** An arm counts only if its **ATM median offset ≥ 3 × SE(median)**; otherwise that arm is a **NO-TEST**. This replaces the across-cycle framing described at §3(c). Applied to the four readings already in hand — dividing the two cited figures in each `r_eff.out` row — A0 NIFTY 12.2 / 0.932 ≈ 13.1× (`r_eff.out:19`), A1 NIFTY 9.8 / 1.089 ≈ 9.0× (`:28`), A1 SENSEX 45.5 / 2.054 ≈ 22.2× (`:29`) all clear it, while **A0 SENSEX 22.9 / 964.843 ≈ 0.02× does not** (`:20`). The precondition independently reaches the same verdict on the `dte = 0` arm that §2.5 reaches on other grounds.

**Decision rule.**
- **T1 PASS** → propose a self-computed L7 / L8 built on the **ENH-131 repricer**: vendor IV, `r` = the L3 session-median futures carry, `T` = exact/365, and `dte 0 → SKIPPED_EXPIRY`.
- **T1 FAIL** → **no L7 / L8 view is proposed.** The refusal is the result, not a failure of the session.

**Decisions still owed after T1, none of them settled here.**
- **L78-1 — definition.** Textbook `∂delta/∂sigma` (vanna) and `∂delta/∂t` (charm), expressed in **δ-notional ₹ Cr**, against the parity target's `∂gamma` constructs. The two are not the same quantity and the choice must be recorded before either is built.
- **L78-2 — scope.** Standing book versus today's ΔOI.
- **L78-3 — charm time step.** Calendar **+24 h**, capped at the **15:30 expiry** with a named state; `dte 0` remains `SKIPPED_EXPIRY`.

### 2.7 The `TD-S83-NEW-5` contradiction — a §D candidate

**An anomalous derived value and an anomalous raw value on the same row are one defect, not two.** `TD-S83-NEW-5` recorded SENSEX back-leg strikes reading `iv` **110–117** against an ATM of 13.10 — roughly **8×** — while holding **48.7M** open interest, and concluded both that the implied volatility was an unexplained property of the vendor feed *and* that the open interest *"is real"*. Those were filed as two observations about two columns.

They are one row. On SENSEX **72300 CE**, `ltp` sits frozen at **5464.15** from **03:05 to 04:10 UTC**; while it is frozen the `iv` reads **119.30 and 121.04**. At **04:15** `ltp` corrects to 1537.35 and the `iv` **drops to 14.89 in the same row** — and only at **04:20** does `oi` fall **48,768,100 → 40**. **72400 CE, whose `ltp` was never stale, reads `iv` 14.11 throughout** (`scratch/s84_contract/iv_stale_correction.out`). So the 8× implied volatility is a stale `ltp` inverted into an implied vol, and the nine-figure open interest is that same stale row — the S71 *"`ltp` is the last trade, not a price"* finding, in the **same row**, not in a different column as `TD-S83-NEW-5` supposed.

**The candidate rule:** when two columns of one row are both anomalous, **check whether they correct together before filing them as two properties of the feed.** Here the correction order — `iv` at 04:15, `oi` at 04:20 — is itself the evidence that one upstream value drives both. Bounded and stated as such: **2 strikes, 1 session.** Filed as `TD-S84-NEW-4`; `TD-S83-NEW-5` carries the correction row.

---

## 3. §D rows to file

**(a) The S83 L9 and L3 anon checks were no-tests; L10 was valid.**
*Source: operator's account of S83, corroborated S84 by the control described at §1.4.* The Supabase SQL editor opens a **new session per run**, so a `SET ROLE anon` issued in one run does not persist into the next; a subsequent `SELECT count(*)` executes as the editor's own role and verifies nothing about the anon path. **Rule:** the check must run as one statement batch in a single run — `BEGIN; SET LOCAL ROLE anon; <reads>; COMMIT;` — and must `SELECT current_user` **alongside** the counts, so the acting role is evidenced by the same result set that carries the numbers. A count without the role beside it is not evidence of a path.
**Status:** the anon path for all three S83 views was **verified S84 in the editor**, in the single-run form, returning `role_now = anon` with `l9 = 4`, `l3 = 2`, `l10 = 868` — §1.4. **`roq.sh` cannot run this check**: `merdian_ro` is not a member of `anon` (`scratch/s84_l78/z2_anon_path.out:14`), so the editor under the postgres role is the only path for it.

**(b) The S82 "well under 0.01" delta prediction was mis-specified.**
`implied_spot_offset_pts` is **delta-inverted by construction**:

> `(f2.v_delta - (CASE WHEN f2.option_type='CE' THEN f2.n_d1 ELSE f2.n_d1-1 END)) / NULLIF(f2.bs_gamma_spot,0) AS implied_dspot` — `docs/session_notes/s81_docclose_notes.md:760-761`, quoted at `scratch/s84_l78/s1i_gonogo_numbered.out`

Rearranged, `(v_delta − bs_delta) = bs_gamma_spot × implied_dspot` **identically, per row**. `delta_abserr` is `abs(v_delta − bs_delta)` (same file, `:756-757`). So the delta error is not an independent quantity that can be driven below a threshold while a spot offset persists — it is `gamma × offset` by algebra. A prediction that `delta_abserr` would fall "well under 0.01" while the ~12-point offset remained was **asserting something the formulation forbids**, since ATM gamma is fixed by the chain. *(Caveat stated rather than glossed: the identity is per-row; the reported medians of the two quantities are taken independently, so they are near-proportional, not exactly so.)*

**(c) The T2 precondition used across-cycle spread where the across-strike SE of the median applies.**
The register characterises `implied_pts` as *"near-constant 11.3–13.1"* — a band over **59 cycles** (`docs/registers/MERDIAN_Assumption_Register.md:950`). The quantity that governs whether a single cycle's median is resolved is the **across-strike** standard error of the median **within** that cycle, which measures **0.932** pts (A0 NIFTY, `r_eff.out:19`), **1.089** (A1 NIFTY, `:28`) and **2.054** (A1 SENSEX, `:29`). These are different statistics over different populations, and substituting one for the other is the easy-to-reason-about quantity standing in for the one that binds. The corrected form is pre-registered at §2.6.

**(d) The RLS-blind-list premise was wrong.**
There is **no RLS-blind list in `bin/roq.sh`** — a grep for `rls|blind|row.level|skip_?list|exclude` across its 231 lines returns nothing (`scratch/s84_item0/b1_rls_blindlist.out`). Blindness is a **property of the role**, recorded in **TD-S81-NEW-16**: `merdian_ro` has `rolbypassrls = false` and the policies are written `TO anon`, so it reads zero rows silently from the RLS set (TD-S81-NEW-16, *Mechanism* row). None of the three views' base tables is in that set — measured live, RLS off with zero policies on `option_chain_snapshots`, `trading_calendar` and `index_futures_snapshots` (`scratch/s84_item0/b7_rls_live.out`). **A premise naming a list should be checked against the file before it is used to declare a test void.**

**(e) The S82 "neither basis nor carry" residual is now measured as a near-constant effective rate.**
Excluding the `dte = 0` SENSEX point, `r_eff` across three points reads **0.036416** (`r_eff.out:29`), **0.037034** (`:28`) and **0.038125** (`:19`) — a band of **3.64 % to 3.81 %**, spanning two symbols and two days. The instrument's own hardcoded rate is **0.065** (`docs/session_notes/s81_docclose_notes.md:732` and `:742`). D.38.3 refuted futures basis and theoretical carry as the explanation of the offset (`docs/registers/MERDIAN_Assumption_Register.md:950`); what remains is consistent with a **rate-convention** difference rather than a spot effect. **Three points is three points** — this is filed as an observation with its n stated, not as a conclusion. T3 at §2.6 is the pre-registered test of it.

**(f) A line citation is stable only into a file that will not be edited above the cited line.** The test is not whether the citation crosses files — it is whether anything will be inserted *above* the target. Filing `TD-S84-NEW-1` shifted every line below it by **+16** and invalidated three citations inside the entry itself: `tech_debt.md:312` → 328, `:314` → 330, `:3706` → 3722 (`scratch/s84_l78/td11_verify.out`, `td12_citation_fix.out`). **Registers that prepend new entries file newest-first, so every line number in them decays on the next filing.** `tech_debt.md` is one; any register with the same newest-first convention is another. **They are cited by entry ID plus row name — from any file, including this capture** — e.g. *"TD-S81-NEW-5, Bears on ADR-025 row"*, which survives every future insertion. By the same test, **`sql/` files, ADR files and `scratch/` evidence keep their line numbers**: they are appended to, corrected in place, or frozen, and are not edited above a cited line. That is why `ADR-025-parity-acceptance-criterion.md:45`, `sql/…_v_iv_surface.sql:303` and every `scratch/*.out:N` in this file remain valid. And note what does **not** rescue this: a dry run. The cited numbers were correct at compose time and became wrong only on write, so the check that catches it must run **after** the edit, against the written file.

---

## 4. TDs filed this session

> **ALL SEVEN FILED AND COMMITTED.** `TD-S84-NEW-1` was filed and committed at **`35c3fea`**. `TD-S84-NEW-2` … `TD-S84-NEW-7` were filed from `parity_render_contract.md` **§5 (P1–P7)** and committed at **`6c0730c`**, together with the two appended rows described below. Entries are addressed **by ID only**: `tech_debt.md` files newest-first, so every line number in it decays on the next filing — §3(f). *(An earlier draft of this section recorded `TD-S84-NEW-1` at "line 67 as of this write"; that note is removed, because filing NEW-2…NEW-7 above it moved the entry — the decay §3(f) predicts.)*

| proposal | filed as | sev | subject |
|---|---|---|---|
| **P1** | `TD-S84-NEW-2` | S2 | `gamma_metrics` has no `CREATE TABLE` anywhere in `sql/` — an ADR-025 D2 clause 4 gap on the most-read object |
| **P2** | `TD-S84-NEW-3` | S2 | three views ship a `COMMENT ON VIEW` in `sql/` that never ran live; one ships its `GRANT` commented out |
| **P3** | `TD-S84-NEW-4` | S2 | the L13 rotation anchor is fabricated on stale vendor rows, and contradicts `TD-S83-NEW-5` |
| **P4** | `TD-S84-NEW-5` | S3 | `anon` holds `MAINTAIN` beyond `SELECT` on three objects created before the S81 default-privileges fix |
| **P5** | `TD-S84-NEW-6` | S2 | two max pains over different substrates; which is canonical is undecided |
| **P6** | **NOT FILED** | — | folded into **`TD-S81-NEW-8`** as an **S84 update** row |
| **P7** | `TD-S84-NEW-7` | S2 | the UI labels `flip_distance_pct` as sigma |

**P6 was declined, not forgotten.** `TD-S81-NEW-8` already records the same two `meridian-connect` clones, the same stale `14b63f3`, the same md5-identity method and the same S72 flat-namespace root cause. Filing a second entry on one root cause was declined; P6's one new measurement went into that entry instead — live HEAD **`7b60d01` → `a408fb4`**, served bundle now **`index-DLdbWkEE.js`**, stale clone still `14b63f3`, **the finding stands and the hash evidence is superseded**.

**`TD-S83-NEW-5` gains an S84 correction row**, appended above its `Status` with its existing text untouched: its *"the open interest there is real"* does not hold on SENSEX 72300 / 72400 CE. The measurement is at **§2.7**; the entry that supersedes it is `TD-S84-NEW-4`.

> *Method note, because the first attempt was wrong.* An earlier sort ranked entries by the **NEW-number** rather than by session (`sort -u -t- -k4 -n`), which put TD-S81-NEW-20 above TD-S83-NEW-7 and hid the entire S83 block. The corrected measurement sorts by session prefix first (`sort -V` on the `S<n>` field) — `scratch/s84_l78/z6_td_latest.out`. This is the §5 class of error: a wrong assertion, not a wrong artefact.

**Filed as `TD-S84-NEW-1` (S3, OPEN): the `sql/` file does not reproduce the live `merdian_ro` grant on two of the three S83 views.** The entry lives in `docs/registers/tech_debt.md`, addressed by its ID; the evidence it cites is below.

- **Measured:** `merdian_ro` holds `SELECT` live on all three views (`scratch/s84_item0/c2_grants.out:8`, `:13`, `:18`). Only `sql/2026-09-25_s83_v_iv_surface.sql:303` carries a `GRANT SELECT … TO merdian_ro` statement (`scratch/s84_l78/c2_expected_from_files.out`). `sql/2026-09-24_s83_v_iv_term_structure.sql` and `sql/2026-09-25_s83_v_gex_repriced_flip.sql` do not.
- **Consequence:** a rebuild of either view from its `sql/` file yields an object that is correct in body, correctly granted to `anon`, and **unreadable by the verification role** — so the next session's `roq.sh` check returns zero rows, silently, and looks like an empty view.
- **Shape:** this is **TD-S81-NEW-5's failure aimed at `merdian_ro` instead of `anon`** — the S81 rule that `COMMENT` and `GRANT` ship as live statements in the `sql/` file, observed to have been applied to one of three files.
- **Cross-ref:** ADR-025 D2 clause 4 · TD-S81-NEW-5 · TD-S81-NEW-16.

---

## 5. Errata — corrections to my own output, recorded rather than re-fitted

1. **Weekday names in the session starter were wrong.** Measured: **2026-09-29 is a Tuesday** and **2026-09-30 is a Wednesday** (`scratch/s84_l78/z1_td_and_weekdays.out:25` and the following line); 2026-09-25 is Friday (`:23`) and 2026-09-28 is Monday (`:24`). The starter named different days.
2. **I wrote the capture path as `docs/session_notes/` when the convention is `docs/research/`.** The S83 precedent is `docs/research/capture_s83.md` (`scratch/s84_item0/a4_diff_names.out:12`). This file is at `docs/research/capture_s84.md`.
3. **A comment-extraction parser that was not concat-aware** read `v_iv_surface`'s comment as 93 chars against a live 4709 and would have been published as file-vs-live drift. The artefact was correct; the assertion was wrong. Corrected before comparison (`scratch/s84_item0/c1b_surface_comment_probe.out`, then `c1_expected_from_files.out:4` showing `parts = 49`).
4. **A byte-compare of the bucket expression was aimed at the wrong lines** (helper `31-33` instead of `30-32`), reporting a spurious difference. Corrected in `scratch/s84_l78/a1_bucket_verify.out`.
5. **A "confirmation" that echoed typed numbers was replaced by one derived from the files.** Bucket-count agreement between the instrument and the helper is now established by extracting both sides with `awk` from `a1_result.out` and `a1_rows_band.out` and `diff`-ing them — `IDENTICAL` on all six cells (`scratch/s84_l78/a1_bucket_verify.out`).
6. **A timing MISS was avoided only by repeating the measurement.** One cold sample read 15.149 ms against a single-digit-ms expectation; three warm repeats read 9.259–9.345 ms (§1.5). Reporting the first sample alone would have been a wrong claim, not a wrong check.
7. **A first draft of this file recorded the anon path as unverified.** It was verified — by the operator, in the editor, in the single-run form (§1.4). The draft generalised from *"this tool cannot run the check"* to *"the check was not run"*, which does not follow.
8. **A TD-number sort ranked by NEW-number instead of by session**, reporting TD-S81-NEW-20 as the highest entry and hiding TD-S83-NEW-1…7 entirely. Corrected at §4. The proposed `TD-S84-NEW-1` is unaffected, but the stated ceiling it sat above was wrong by two sessions.
9. **Intra-file line citations went stale the moment the entry was inserted.** The new block cited `tech_debt.md:312`, `:314` and `:3706`; the insertion landed at the top of Active debt, **above all three**, shifting them by exactly **+16** to 328, 330 and 3722. Renumbering would re-break on the next TD filed — and every TD is filed at the top — so they were replaced with **stable entry+row references** (*"TD-S81-NEW-5, Proper fix row, this file"*, and so on). Second write, **+64 bytes, 0 lines changed**, residual count of the three stale citations **0** (`scratch/s84_l78/td12_citation_fix.out`). **The dry run could not have caught this**: the numbers were correct when composed and wrong only after the write.
10. **§3(f) caught a live instance in this very file.** §3(d) cited `tech_debt.md:490` for TD-S81-NEW-16's *Mechanism* row. After filing NEW-1…NEW-7 above it, line 490 resolves to **`TD-S81-NEW-11`'s heading** — a different entry that reads plausibly — while the real row sits at 580. **A stale line citation that lands on other valid content is worse than one that lands on nothing**, because nothing signals the error. Replaced with the ID+row address §3(f) prescribes.

---

## 6. Open

| item | when | note |
|---|---|---|
| **A2** | Mon **2026-09-28** (`z1_td_and_weekdays.out:24`) | gradient point — NIFTY dte 1 / SENSEX dte 3; not a T1 arm |
| **A3** | Tue **2026-09-29** (`z1_td_and_weekdays.out:25`) | **T1 arm, SENSEX dte 2** — the first of the dte 1–2 pair; NIFTY dte 0 and void. Also carries **the NIFTY L9 max-pain arm owed from S82**: TD-S80-NEW-1 stage 1 is half-verified with the NIFTY arm outstanding |
| **A4** | Wed **2026-09-30** | **T1 arm, SENSEX dte 1**; NIFTY dte 6 against the rolled front |
| **T1 verdict** | after A3 + A4 | not reachable on the current n; rule and thresholds pre-registered at §2.6 |
| **Decisions L78-1 / L78-2 / L78-3** | after T1 | blocked on the verdict; scope stated at §2.6 |
| **EC2 HEAD re-read** | next session open | one line, to close §1.1 with a measurement by this tool |
| **`TD-S84-NEW-1` … `NEW-7`** | **DONE this session** | **FILED AND COMMITTED.** NEW-1 at **`35c3fea`**; NEW-2…NEW-7 at **`6c0730c`**, with the `TD-S83-NEW-5` correction row and the `TD-S81-NEW-8` S84 update row |
| **`parity_render_contract.md`** | **DONE this session** | committed **`f1b6778`** and pushed; its 39 citation offsets fixed at **`6c0730c`** |
| **EC2 `~/meridian-engine`** | pull at doc-close | at **`18c2fb8`** against an `origin/main` of **`6c0730c`** — measured **3 commits, 3 files, 0 `.py`, 0 non-`docs/`**, so the gap is **docs-only** and carries no runtime change |
| **Design pass A–C** | after the project-knowledge upload | blocked on it; nothing in A–C is startable from the repo alone |

---

*capture_s84.md — Session 84, 2026-09-25. Measure-only. Every figure carries its `path:line`, except those labelled OPERATOR-MEASURED, which carry the operator's run instead. One item is recorded as **not measured by this tool**: the post-pull EC2 HEAD (§1.1, corroborated by pasted terminal output). `TD-S84-NEW-1` is **FILED** (§4, §6). Citations into newest-first registers use entry+row addresses, not line numbers — §3(f).*
