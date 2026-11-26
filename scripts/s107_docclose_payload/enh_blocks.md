### ENH-149 — Gross pin: `v_gex_strike_rank_gross` and the Board Pin on it through `v_gex_pin_gross` (LIVE 2026-11-23 / 2026-11-25, S107)

**Origin.** Board-pin lane, MR-PIN2 intake row 1 (`docs/registers/intake/I002.md`): the Board pin was rank 1 of
`v_gex_strike_rank` on `abs(gex_cr)`, a **net** quantity, and matched the gross-gamma strike on 15–36 % of runs
(AR §D.60.1). The id was allocated in I-002 (checked free against highest ENH-148); this block is its body.

**What is live.**

| Object | State | Record |
|---|---|---|
| `v_gex_strike_rank_gross` (revision 3) | **LIVE, applied by the operator 2026-11-23.** Ranks the strikes within 5 % of spot with gross exposure > 0 by `gross_cr` = `gamma_strike` × (OI call + OI put) × spot² / 1e7, where `gamma_strike` is the mean of the stored `gamma_call` and `gamma_put` when both are > 0 and the one that is > 0 otherwise; carries the legs-supplied column and a per-run count of in-set strikes with OI and no gamma. SELECT to `merdian_ro` only. | `sql/2026-11-23_s107_v_gex_strike_rank_gross.sql`; rule 25: length 5281, md5 `aa4946064341c1d1ae835819d8cba858`, PostgreSQL 17.6; plan 2.407 ms, no sequential scan (I-002 §3a). Pin lane order check on revision 3: PASS (`docs/research/pin_proof/order_check_rev3_prereg_FROZEN_2026-11-23.md`) |
| `v_gex_pin_gross` | **LIVE, applied by the operator 2026-11-25.** Owner-rights wrapper, one row per symbol: pin strike, pin share, legs, runner-up strike and share, lead in share points, counts. SELECT to `authenticated`, `marketview_ro`, `merdian_ro`; `anon` and PUBLIC revoked. No Crore column, so no `_1pct` form (ADR-032). | `sql/2026-11-25_s107_v_gex_pin_gross.sql`; rule 25: plain length 823, md5 `e622b8bb88f5850e777da33aeec68a9d`; pretty length 803, md5 `59d5f21b2d7768a042f69998eac6fb32`; PostgreSQL 17.6; plan 2.261 ms, index scans only; ACL read 2026-11-25 (`authenticated=rm`, `marketview_ro=r`, `merdian_ro=r`, `service_role` full, no `anon`); COMMENT applied |
| Board Pin tile | **LIVE 2026-11-25 about 18:08 IST**, Board `d7642c2` (pin switch `caecef8` + `cba0695`, labels `457fc99`, manual v0.6). The tile shows the gross pin's strike, share and lead. The earlier pin is shown as **"Net peak"** with pin state, held cycles and conviction beneath it; `gex_cycle_history.pin_leader_strike` is not redefined. Regime, expansion probability, pin score and the dealer-flow simulation are labelled "legacy, unvalidated"; the Flip "experimental". | Operator rulings 2026-11-25 09:23 (`docs/research/s107/rulings_s107.md`); read against SQL on staging and live: NIFTY 26,000, 10.03 %, lead 1.00; SENSEX 84,000, 8.14 %, lead 2.34. Rollback `/var/www/marketview.bak-90cb618` |

**Not done.** The ten-day shadow this entry was first scoped with was **dropped by the operator** on 2026-11-23
(`docs/research/pin_proof/ruling_shadow_dropped_2026-11-23.md`); a daily pin monitor (pin lane, forward only from
2026-11-25) replaces it. `data_contracts` rows: TD-S107-NEW-2. The order-flow note that STREAMS X1 required before
a switch was written after it (AR §D.62.4). **Owed at a later Board round, authored and not run:** the Pin detail
panel caveat, the "#2" label, manual v0.7 (TD-PIN3-NEW-3). **Correction lines owed by I-002 row 17** on ADR-024
Amendment A, ENH-125 and ENH-122: none of the three calls the net a gross pin, so none is wrong; each now describes
the quantity the Board shows as "Net peak", and this block is the cross-reference.

**Status.** **LIVE.** Pin Band, pin state and conviction remain on the net quantity; whether they follow the gross pin
is open and outside this entry (operator ruling 2026-11-26: no Pin Band rebuild, no label changes).

### ENH-150 — Gamma V2 beside V1: `merdian_compute/gamma_v2.py`, `gex_strike_v2`, `gex_run_v2`, `p3b2` (BUILT and BACKFILLED 2026-11-25/26; live writer NOT APPROVED; minted S107 close)

**Origin.** ADR-033 (versioned isolation, operator rulings R1–R6 of 2026-11-25). V1 is frozen and named legacy; V2
computes one gamma per strike (rule v1.2) into new tables and never into a V1 column. Minted here (checked free
against highest ENH-149).

**State.**

| Part | State | Record |
|---|---|---|
| Rule v1.2 and `merdian_compute/gamma_v2.py` | Built; standard library only; not exported from the package; not part of the retail contract. Self-test: 28 mutants caught. Independent check by the pin lane: **PASS** at three commits (486 chain runs and 313 stored-row runs, 0 mismatches). | ADR-033 §3, §6; `tests/test_gamma_v2_selftest.py`; `docs/research/pin_proof/v2_rule_conformance_result_v12_2026-11-25.md`; sha256 `ba611363f28ed8c3d89ccc3c3f0bfb99c87fb077d16c081f36d40f298bac4e95` |
| Tables `gex_strike_v2`, `gex_run_v2`; `p3b2_invariant_checks`, `p3b2_sweep` | **APPLIED by the operator 2026-11-25 about 19:15 IST** in one transaction. RLS on; SELECT for `merdian_ro`; SELECT, INSERT, UPDATE for `service_role`; nothing for `anon` or `authenticated`. **No job scheduled.** | `sql/2026-11-25_s107_stepA_apply_ALL.sql` (md5 `8a42bfd34edf2cee7d5e92f6bc475374`) |
| Backfill from stored `gex_strike_snapshots` | **DONE 2026-11-25/26:** 19,050 runs, 2,679,771 strike rows, 2026-05-25 → 2026-11-25, 0 input errors, stamp `v2-1.2-gss`; V2 counts equal the stored V1 counts per symbol; a dry rerun reports every run already written. One-day check by the pin lane (B2): PASS, 156 of 156 fixture runs. | `backfill_gamma_v2_from_gss.py`; `docs/research/s107/engine_to_pin_LATEST.md`; `docs/research/pin_proof/b2_backfill_check_result_2026-11-25.md` |
| `p3b2` sweep over the history (by hand) | V0, V2, V3, V4 OK on 19,050 runs; V1 (recompute from the chain) OK on 10,067 and NOT_COMPUTED on 8,983 where no chain rows are stored; no failure. | as above, §3 |
| Live writer hook | **Authored, NOT APPROVED.** `gamma_v2_writer.py`, off unless `MERDIAN_GAMMA_V2=1`; `scripts/gamma_v2_writer_hook_patch.py` (three insertions in `compute_gamma_metrics_local.py`). | ADR-033 §4, §8 |
| `p3b2` job; the seven `v_gex2_*` views; any Board tile on V2 | **Not approved; views not authored.** | ADR-033 §8, §9 |

**Gate before the hook is put up for approval** (operator ruling 2026-11-26 05:45 IST), each with evidence: V1 output
byte-identical with V2 enabled on a golden-day replay; both versions carry run and expiry identity; no shared view
changes its source version; the V1 checks still work; `p3b2` catches planted faults in the database, not only in the
Python self-test; an interrupted V2 write recovers and a second `--apply` over written days is idempotent (both
unexercised); a V2 failure cannot stop V1 (tested); rollback stops V2 being read without deleting either history.

**Board.** Operator ruling 2026-11-26: the Board moves to V2 **by family in one release** (net gamma, strike
exposure, concentration, Net peak, net river), each figure checked on staging against a database read; not tile by
tile. Nothing is approved.

**Next.** The pin lane's pre-registered comparison of V1 against V2 on the stored history (its step 9), then the
operator's decision.

**Status.** **BUILT and BACKFILLED; live writer, job, views and Board tiles NOT APPROVED.**

