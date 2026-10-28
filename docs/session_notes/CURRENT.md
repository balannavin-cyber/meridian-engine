# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. **S95 moved at the S97 close**, asserted byte-identical at **4,816 B**, sha256 `f63116f5…` on both sides. **S99 (its pointer block, 1,090 B, sha256 `56ab7a26…`) and S100 (7,695 B, sha256 `d11e991b…`) moved at the S101 close (run in S102)**, each asserted byte-identical on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S101 — Sunday 2026-10-25 20:41 IST → Wednesday 10-28 09:58 IST** (closed in S102 Part A). The engine's pure compute
became an importable package for retail (Part A, C2–C7), deployed Monday 10-26 17:08 IST and read live on 10-27; Monday's
Part C reads closed the S98-B and B1 TDs. This block points; the detail lives in the files named. Rulings:
`docs/research/s92_parity/rulings_s101.md` (S101-A…H; the single source). Evidence and findings:
`docs/research/s101/S101_close_inputs.md`. **Progress lives in the tracker**, `docs/registers/agentic_layer_roadmap_S90.md`
(v2.18), and **its §2.2 is the single list** of open work.

**`origin/main` — all pushed.** `11f2cbe` (A2–A7) · `4ed5671` (C2) · `50bef37` (C3) · `a0b6115` (C4) · `e0fb11d` (C5) ·
`02a06ec` (C6) · `4a1d8e1` (C7) · this close. Fast-forward `7b91d1a → 4a1d8e1` 10-26 17:08 IST; four-way PASS 17:12
(`origin/main` = `~/meridian-engine` = `~/meridian-cc` = Local); rollback written, not needed (10-27 read, 0 non-zero
exits). Retail (MR-S2) pins `merdian_compute` at `4a1d8e1`. Offline suite **25 steps**. Crontab unchanged (70 lines).
Marketview unchanged (live `f964e40`).

**What was established**

1. **`merdian_compute/` (S101-A, S101-C).** The pure compute surface — `gamma` (with the composed cycle
   `compute_gamma_core`), `volatility` (`derive_atm_iv`), `pin` (`derive_core`), `cycle` (`held_for_cycles_next`,
   `trading_days_between`) — stdlib only, packaged by `pyproject.toml`. The writers import every name back, so production
   runs the code retail runs. Proofs per commit: AST equality, golden replay 486/486 before = after, error-path replays,
   mutants (`S101_close_inputs.md` §2).
2. **Offline suite 23 → 25 steps:** 24 import purity (no environment, no supabase / requests / dotenv / core, no socket);
   25 the contract against production golden rows.
3. **Contract `docs/interfaces/retail_compute_contract.md` v2.1:** composed calls, ATM IV, the pin path, the full view
   closure (§8) with live `pg_get_viewdef` md5s; what retail must not import (§1); not covered (§9); interpreter (§10).
4. **Two live views registered (S101-E).** `v_gex_strike_pin_zone` (C6) and `v_gex_strike_accel_zone` (C7) matched no
   file in `sql/` — an unregistered S80-class change; the live definitions are now in `sql/` and reproduce length and md5.
5. **Deployed 10-26 17:08 IST (S101-B).** A read-only recompute of the 15:40 cycle equalled the cron rows (18/18 fields,
   both symbols); the first unattended run, 10-27 08:30, had 0 non-zero exits; the pin path ran live (carry, reset,
   look-back across sessions); the NIFTY expiry roll read on 10-28 to 09:15.
6. **Part C, 10-26.** S98-B / S99-H PASS in full; the 08:20 refresh and the 09:09 probe clean; the wsfeed self-started.
   TD-S97-NEW-4, TD-S82-NEW-1, -2 closed (S101-F); TD-S97-NEW-5 and TD-S80-NEW-17 closed. **Board 10-27:** S100-N, Q.1,
   R and S PASS; Health OVERALL DEGRADED on a healthy fleet (the 30-minute token tile). **R19:** the builder is correct on
   its input; 10-26 / 10-27 breadth owed to the 10-28 run (Dhan publish lag).

**Filed:** TD-S101-NEW-1…17 — the ENH-133 writer's `57014` timeout (first); the unregistered view change and a standing
md5 check; `otm_oi_velocity` NULL in every row; two unbounded prior-row reads; gamma / volatility math re-implemented
outside the package; `.gitignore` `_*.py`; the ≥ 3.12 `sum()`; retail gaps (contract §9); superseded view files; port 22;
Local HEAD in the four-way; `sudo` journal reads; Health OVERALL; Context IV skew at 0 DTE; the NIFTY board after an
expiry-day close; `eod.log` dates; one `DH-905` ticker. TD-S100-NEW-1 re-measured 10-27, open.

**Corrections to my own work:** Assumption Register **§D.55** (S101, 25 rows). The one to carry: a live view is identified
by full `pg_get_viewdef` md5 against a file that reproduces it, never by markers (D.55.14; `CLAUDE.md` rule 25).

**Security:** port 22 is open to 0.0.0.0/0 on the box (TD-S101-NEW-10, operator action); TD-S99-NEW-1 and BS-1 stand.

**No ADR filed or amended; rule 25 added (`CLAUDE.md` v1.73).** System Map §S101; Deployment Topology §S101.

## NEXT SESSION PICKS UP

1. **Carried live reads (S102 Part B):** the NIFTY pin path across the expiry roll, part 2 (the first OPEN row of 10-28:
   held 1, leader 23000 ≠ 22750); R19 re-read after the first EOD run on or after 10-28 16:10 IST (10-26 and 10-27
   breadth, expected = actual, `eod_pct` ≥ 95).
2. **Rulings owed (S101 §5), each raised with a recommendation before building:** Health OVERALL token threshold; the
   NIFTY board after the expiry-day close; Context IV skew on a 0-DTE front leg; WCB from pre-open ticks;
   `held_for_cycles` across an expiry roll on the same strike (tracker §2.2 rows).
3. **Then tracker §2.2 in its order:** B1 (R48 / R49, the ledger row, the R40 overlap) → BS-1 → B2 (R5 close print, R20;
   TD-S100-NEW-1 first) → B3 (R16 + R36) → B4 → B5 (R15, R11 + R39) → B6 (R12 with S100-Q step 2, R13); BR and the rest
   of BS before any retail build.

## OPERATOR RULINGS, S101

**All rulings live in `docs/research/s92_parity/rulings_s101.md`**, the single source.

| # | Topic |
|---|---|
| **S101-A** | Core split: package the composed gamma cycle (C2) |
| **S101-B** | Deploy after the Part C reads; fast-forward, read-only check, written rollback |
| **S101-C** | Board-core gaps: ATM IV (C3), the pin path (C4), contract (C5) |
| **S101-D** | File the S101 findings as TDs at the close |
| **S101-E** | Register the live pin / accel zone views (C6, C7); live views by md5 |
| **S101-F** | Close TD-S97-NEW-4, TD-S82-NEW-1, -2; the `57014` exit a new TD |
| **S101-G** | Schedule the 10-27 close reads and R19 |
| **S101-H** | Close S101; the doc-close runs in S102 |

## Previous session S100

**S100 — Saturday 2026-10-24 07:39 IST → Sunday 10-25** (doc-close `7b91d1a`). S98 + S99 closed (`3ad5c81`); the weekend
list built — monitoring and a pre-open probe, three writers taught to stop, the Rule 13 symbol scope, the board's closing
session (Marketview `f964e40`). The full block is in `docs/registers/CURRENT_history.md`.

## OPERATOR RULINGS, S100

**All rulings live in `docs/research/s92_parity/rulings_s100.md`**, the single source.

| # | Topic |
|---|---|
| **S100-A** | `tech_debt.md` split: open entries / history |
| **S100-B** | R38–R49 homed in tracker §2.2, no TDs |
| **S100-C** | Monitor window = union of runner lines, contiguous only |
| **S100-D** | Alert daemon and daily audit recorded dead; design later |
| **S100-E** | One broker-access probe at 09:09 IST |
| **S100-F** | wsfeed retry timer plus deduped alert |
| **S100-G** | Dhan token refresh at 08:20 IST |
| **S100-H** | Deactivate the 12 Edge Function cron jobs |
| **S100-I** | Breadth-from-ticks: no ticks → no row, exit 0 |
| **S100-J** | `data_contamination_ranges.symbols text[]` |
| **S100-K** | `merdian_ro_select` on the 51 RLS tables |
| **S100-L** | Marketview backups: newest 3 plus named `PRE_*` |
| **S100-M** | Health untracks the ICT writer; `SUBSCRIPTION_LAPSED`; CRITICAL display only |
| **S100-N** | Legacy pages: Board's previous close and spot |
| **S100-O** | Pass-2 misses: Muhurat not captured; v5 Rule 3; ADR-004 erratum |
| **S100-P** | Context IV skew = the view's skew |
| **S100-Q / Q.1** | Pocket word local, net γ beside it; then R12 |
| **S100-R** | Spot label, dealer wording D1–D7, Γ kept |
| **S100-S** | Session-state strip, stale window to 15:45, basis names its spot |
