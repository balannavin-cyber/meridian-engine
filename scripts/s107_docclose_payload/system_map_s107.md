
## §S107 — Session 107: the Board Pin moves to the gross pin; gamma V2 tables are built beside V1 and filled from history; `tape_w` can log in (2026-11-21 → 11-26)

Doc Protocol v5.1: a table of what changed, no narrative. Decision: `docs/decisions/ADR-033-gamma-v2-versioned-isolation.md`.
Detail: ENH-149, ENH-150; `tech_debt.md` S107 paragraph; `docs/registers/intake/I002.md`, `I003.md`;
`docs/research/s107/`. Recorded at the S107 doc-close (2026-11-26).

**§B — tables and views.**

| Component | Kind | Reads | Read by | State |
|---|---|---|---|---|
| `v_gex_strike_rank_gross` | view (revision 3) | `gex_strike_snapshots` | `v_gex_pin_gross`; the pin lane (`merdian_ro`); `p3b2` check V4 by formula | **LIVE 2026-11-23.** Strikes of the latest run within 5 % of spot ranked on gross exposure. ENH-149 |
| `v_gex_pin_gross` | view, owner rights, one row per symbol | `v_gex_strike_rank_gross` | **the Board Pin tile** (`authenticated`, `marketview_ro`) | **LIVE 2026-11-25.** Board roles hold no grant on the gross view underneath, by design. ENH-149 |
| `gex_strike_v2` | table (RLS on) | — | the pin lane (`merdian_ro`); `p3b2_sweep` | **CREATED 2026-11-25.** One row per run, expiry and strike under rule v1.2. 2,679,771 rows, 2026-05-25 → 2026-11-25, all stamped `v2-1.2-gss` (backfilled). **Nothing live writes it.** ENH-150 |
| `gex_run_v2` | table (RLS on) | — | as above | **CREATED 2026-11-25.** One row per run: net, top shares, gross band total, gross HHI, counts. 19,050 rows. ENH-150 |
| `p3b2_invariant_checks` | table (RLS on) | — | `merdian_ro` | **CREATED 2026-11-25.** One row per run and check (V0–V5) plus one per sweep call. 19,050 runs checked by hand; no failure. ENH-150 |
| `gex_cycle_history.pin_leader_strike` | column | — | the Board's "Net peak" line; `/tape` anchor | **Not redefined.** It is the net quantity, shown on the Board as "Net peak" from 2026-11-25 |
| `gex_strike_snapshots`, `gamma_metrics`, every V1 view | — | — | — | **Unchanged.** V1 is frozen and named legacy (ADR-033 D1) |

**§C — functions.**

| Component | Kind | State |
|---|---|---|
| `p3b2_sweep(p_now, p_window, p_min_age)` | plpgsql, SECURITY DEFINER; no EXECUTE for `anon` or `authenticated` | **CREATED 2026-11-25; no job.** Skips runs already checked. A run swept before its V2 rows exist is recorded as a V0 failure and not rechecked, so it must not be scheduled while the writer hook is off |
| `p3b_sweep` v1.2 (job 47) | — | **Unchanged.** Its check I2 is the reason V1 could not be corrected in place (ADR-033 §1) |

**§A — code.**

| Component | Kind | State |
|---|---|---|
| `merdian_compute/gamma_v2.py` | package module, standard library only, not exported, not in the retail contract | on `main` with this close; sha256 `ba611363…4e95`; rule v1.2 |
| `backfill_gamma_v2_from_gss.py` | one-off script (service key; dry run by default; refuses market hours and today) | run 2026-11-25/26 from `~/v2-backfill` on the production box |
| `gamma_v2_writer.py`, `scripts/gamma_v2_writer_hook_patch.py` | writer hook and its patcher | **authored, NOT APPLIED, NOT APPROVED** |
| `merdian_compute/gamma.py`, `compute_gamma_metrics_local.py` | V1 | **not edited** (no diff against `main` for either file in this close) |

**Roles.**

| Role | Change | State |
|---|---|---|
| `tape_w` | password set by `tape_w_password.py` on the box; login proved | **2026-11-24:** `PASS tape_w login ok` (statement timeout 15 s, idle-in-transaction 10 s, connection limit 2, PostgreSQL 17.6); V1–V5 read and passed; E-6 `as_of` comments applied. No grant changed |
| `merdian_ro` | SELECT on `gex_strike_v2`, `gex_run_v2`, `p3b2_invariant_checks`, `v_gex_strike_rank_gross`, `v_gex_pin_gross` | applied with each object |
| `service_role` | SELECT, INSERT, UPDATE on the two V2 tables and USAGE on their sequences, granted explicitly (default privileges in `public` were narrowed in S104); no DELETE | applied 2026-11-25 |

**Board (Marketview, `meridian-connect`).** Live `d7642c2` from 2026-11-25 about 18:08 IST: Pin = gross pin;
"Net peak" line; "legacy, unvalidated" and "experimental" labels; manual v0.6. The build it replaced is kept at
`/var/www/marketview.bak-90cb618`.

**Not changed by this section.** No V1 compute, no V1 view and no cron line changed. The signal path is recorded
as running with no consumer found (AR §D.61.3); nothing about it was changed.
