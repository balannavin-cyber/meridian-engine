# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S96 — 2026-10-11 → 10-12 (Sunday evening into Monday pre-open).** P7 built and put on the live
board in full; P3b designed, built and tested; D-4 declined. This block points; the detail lives
in the files named. Rulings: `docs/research/s92_parity/rulings_s96.md` (S96-A…J, the single
source). **Progress lives in the tracker**, `docs/registers/agentic_layer_roadmap_S90.md` (v2.13).

**`origin/main` — all pushed, last `8de45b9` before this close.** P7a `36af1e9` / `fb3efb0` /
`eb8f1d6` · guard survey `345d1b2` / `4729893` · M-P7 result `7faa9fb` · S96-D `c1b7a3c` / `f044116`
· S96-E `d252cd5` / `9321c57` · badge round `821f984` / `e3b4dd9` · S96-F `f684f10` / `fa12709` /
`b3c5066` · S96-G `2fa5bab` / `334ba38` · P7b round `74baad5` / `d306bcf` · P3b `df84404` /
`c549dfa` / `324f85c` · S96-H/I/J `5b425ea` · TD-S95-NEW-2 SQL `8de45b9` · this close. **Production
tree `~/meridian-engine`: pull to this close owed** (S96 carries docs, tests and sql only).
**meridian-connect LIVE `804d684`** (`858cb46` → `62f5c55` DEX bricks → `c81b700` badge →
`804d684` Δ bricks); backups `/var/www/marketview.bak-858cb46`, `.bak-62f5c55`, `.bak-c81b700`.

**What was established**

1. **P7 BUILT AND LIVE; DONE on the first market-hours read** (S96-I). DEX flow since the
   pre-open beside the book (`v_dex_flow_vs_book`, **ENH-143**) as bricks; the untraded-leg guard
   (S96-D, TD-S95-NEW-1 (c)); the SAME / OPPOSITE badge after M-P7 scored BUILD (S96-E); the
   L7/L8 per-leg base (`v_gex_greeks_l2_leg`, S96-F, bit-for-bit with S89); ∂Δ/∂σ and ∂Δ/∂t flow
   (`v_delta_drift_flow_vs_book`, **ENH-144**, S96-G) as bricks on the two Δ tiles. First flow on
   the 10-09 front leg: NIFTY iv +1,761.07 / t −1,919.44; SENSEX +729.56 / −795.65 Cr.
2. **D-4 DECLINED-ON-EVIDENCE** (S96-I). The ΔOI × premium four-case stays off the track (10-09
   triage); the badge reads *"flow-vs-book shown on unclassified ΔOI; classification (D-4) not
   built"* as a permanent ADR-025 D3 deviation.
3. **P3b BUILT and tested; apply owed** (S96-H, **ENH-145**). `public.p3b_sweep()` under
   `pg_cron`, shadow only, P3a's checks. Fixture PASS against P3a on six golden days (0 mismatches,
   24/24 mutants); real volume on 10-09 1,902 ms with I1–I4 n_fail 0 on 154 runs. It took three
   revisions to run at real volume (§D.50.8).
4. **TD-S95-NEW-2 SQL prepared** (S96-J): 14 closed days, three sources agreeing; apply after a close.

**Corrections to my own work:** Assumption Register **§D.50**. The one to carry: a fixture day is
too small to show a planner's estimate — T4 at real volume caught two failures the fixture could not.

**DDL applied this session:** `v_dex_flow_vs_book` (and its S96-D / S96-E body replacements),
`v_gex_greeks_l2_leg` + `v_gex_greeks_l2_strike` body re-point, `v_delta_drift_flow_vs_book` — each
batch ending in its own verification SELECT. **No ADR filed or amended; rules 0–24 unchanged.**

## NEXT SESSION PICKS UP

1. **Pull the production tree** — `~/meridian-engine`, `git pull --ff-only` to this close.
2. **P7 live read, in market hours (~09:30 IST)** — `docs/research/s96_priority/p7/live_read_pack_2026-10-12.md`:
   L1–L4 through `roq.sh` while Claude reads the board in Chrome. PASS → roadmap P7 **DONE**.
3. **After a close (≥ 15:40 IST), two operator applies in the SQL editor**, each ending in its own SELECT:
   - **P3b** `sql/2026-10-12_s96_p3b_invariant_checks.sql` — Section A (A-V must equal its stated
     row), then Section B (rolled back; must equal T4c's 12 rows). Then read the first cron sweep's
     rows. **P3b → DONE** on all three.
   - **TD-S95-NEW-2** `sql/2026-10-12_s96_td_s95_new_2_calendar_backfill.sql` — verification 14 / 14 / 0.
4. **ACL fingerprint re-baseline after the P3b apply** — it adds a table, a sequence, a function and
   a policy. Current baseline (S96, 06:15 / 06:30 IST): `relations 350 ccc3895d…`,
   `anon_public_privs 256 f19b614e…`, `anon_writable_objs 0`, `public_functions 40 5d8cd7f8…`,
   `rls_policies 28 d16e21d6…` (`docs/lovable_prompts/s92/README.md`).
5. **Checks owed:** Telegram with the chat unmuted (TD-S91-NEW-12) · the 3D view after a full
   session, then delete `/var/www/marketview.bak-1deeb87` · **Tue 10-13** drop the S90-H backups
   (TD-S90-NEW-11) · **Tue 10-20** live-day half of TD-S91-NEW-13.
6. **Open for the operator:** TD-S96-NEW-1 (the "Dealer" wording on the L7/L8 captions — a
   wording yes is needed) · TD-S95-NEW-1 (a)/(b).
7. **Filed this session:** TD-S96-NEW-1…4.
8. **Carried:** TD-S94-NEW-1…4 · TD-S93-NEW-1 / -3 · TD-S91-NEW-2 sites 1, 3, 4, 5, 6 ·
   TD-S91-NEW-3 · TD-S80-NEW-1 · TD-S92-NEW-3…6 · P4 accruing (n = 20 per symbol, about
   mid-January 2027) · P8 gated on P4.

## OPERATOR RULINGS, S96

**All rulings live in `docs/research/s92_parity/rulings_s96.md`**, the single source.

| # | Topic |
|---|---|
| **S96-A** | P7 design D1–D7 (split P7a / P7b; badge amended, not retired) |
| **S96-B** | M-P7 verdict cut (20 sessions; abstain share ≤ 1/2) |
| **S96-C** | P7a board form: bricks; the pre-open value from the database |
| **S96-D** | Untraded-leg guard G1–G3 (S2 share ≥ 2 %) |
| **S96-E** | M-P7 badge columns B1–B3 |
| **S96-F** | P7b per-leg base of L7/L8, gate C5 |
| **S96-G** | P7b flow view `v_delta_drift_flow_vs_book` |
| **S96-H** | P3b sidecar H1–H8 |
| **S96-I** | D-4 DECLINED-ON-EVIDENCE; P7 closes on the live read |
| **S96-J** | TD-S95-NEW-2 backfill: SQL now, apply after a close |

## Previous session S95

**S95 — 2026-10-11 (Sunday, out of hours).** DEX and S\* on the live board; P3a run and wired
in; S\* pre-registered, gated, applied; P5 measured, ruled and applied; five owed rulings made.
This block points; the detail lives in the files named. Rulings:
`docs/research/s92_parity/rulings_s95.md` (S95-A…G, the single source). **First close on Doc
Protocol v5** (S95-E). **Progress lives in the tracker**, now `docs/registers/agentic_layer_roadmap_S90.md`
(v2.12; the old path is a pointer stub).

**`origin/main` — all pushed.** `882df80` P3a · `90c8c50` / `7566e8c` S\* · `21d3142` / `47989ed`
P5 · this close. **Production tree `~/meridian-engine` at `1390584`; pull owed** before Monday's
preflight (S95 carries docs, tests and sql only). **meridian-connect LIVE `858cb46`** (DEX
`d1912d2` → `392256a`; S\* `103f663` / `1c5a047`; sub-line `719e85c` / `858cb46`); backups
`/var/www/marketview.bak-13b1410`, `.bak-392256a`.

**What was established**

1. **P6 DONE.** The DEX book is on the Flows tab with the P2 phrase, every leg total beside its
   gap, and the dte-0 note (ENH-140 board read). **S\*** `v_dex_repriced_zero` (**ENH-141**) was
   pre-registered (`7bfafb49`), scored **APPLY** (G1 on 11 arms; G3/G4/G5 on 7 of 10; the widest
   G5 spread 0.239 σ₁d, 95 % of tolerance, on 1-dte SENSEX), applied, and shown as a tile plus a
   dotted ladder rule. Staging review caught the tile measuring from the chain spot while the
   header shows another clock's spot; fixed to *"above chain spot …"* before promote.
2. **P3a DONE** — PASS on the six golden days under `ulimit -v 700000` (run of record on the
   box, S95-A), wired as `run_offline.sh` step 12/12; its PE-sign mutant was a silent no-op until
   fixed (`882df80`). P3b needs approval.
3. **P5 DONE** — `v_oi_since_preopen` (**ENH-142**), ruling **S95-B**. On NIFTY the pre-open row
   is the 15:40 close on every leg (26/26 changeovers); on SENSEX BSE revises 23–41 % of legs
   overnight. Section 4 PASS; 4d reproduced probe 1 (472 / 0 / 0 and 390 / 102 / 8,420).
4. **Vendor OI on untraded legs is not a measurement** (TD-S95-NEW-1): SENSEX 09-25 / 09-28 /
   09-29, legs with volume 0 held 33–94 % of front OI and 73–98 % of DEX gross.
5. **Rulings S95-C…G** applied at this close: ADR-015 Amendment A; parity is not reopened by a
   break; Doc Protocol v5 adopted; generated-CSV policy (TD-S93-NEW-2 resolved); P8 → dte 1.

**Corrections to my own work:** Assumption Register **§D.49** (11 rows, 9 mine). The one to
carry: a check is tested at real volume, not only on local fixtures (D.49.7).

**DDL applied:** `v_dex_repriced_zero`, `v_oi_since_preopen` (each batch ending in its own
verification SELECT). **ADR-015 amended; rules 0–24 stand, rule 23's text carries S95-A.**

## NEXT SESSION PICKS UP — as S95 left it (SUPERSEDED by the S96 list above)

1. **Pull the production tree** — `~/meridian-engine`, `git pull --ff-only`, before Monday's preflight.
2. **First live session with DEX and S\* on the board:** read both tiles against SQL during
   market hours (the S95 reads were on a closed weekend).
3. **ACL fingerprint re-baseline** before the next Lovable round — `v_oi_since_preopen` was
   created after the 13:18 snapshot (`relations 346 06c07d80…`).
4. **P7, the flow leg** — unblocked (P5 and P6 live); a design note first. **P3b** needs approval.
5. **Checks owed:** Telegram with the chat unmuted (TD-S91-NEW-12) · the 3D view after a full
   session, then delete `/var/www/marketview.bak-1deeb87` · **Tue 10-13** drop the S90-H backups
   (TD-S90-NEW-11) · **Tue 10-20** live-day half of TD-S91-NEW-13 (the calendar half is done).
6. **Filed this session:** TD-S95-NEW-1 (untraded-leg vendor OI), -2 (`trading_calendar` holds
   no rows for past closed days).
7. **Carried:** TD-S94-NEW-1…4 · TD-S93-NEW-1 / -3 · TD-S91-NEW-2 sites 1, 3, 4, 5, 6 ·
   TD-S91-NEW-3 · TD-S80-NEW-1 · TD-S92-NEW-3…6 · the stale PK draft
   `claude/P2_dealer_side_design_2026-10-10_DRAFT.md` and the duplicate PK `CLAUDE_history.md`
   (operator's call).

## OPERATOR RULINGS, S95

**All rulings live in `docs/research/s92_parity/rulings_s95.md`**, the single source.

| # | Topic |
|---|---|
| **S95-A** | Rule 23's hours bind trading days only; `ulimit -v` always |
| **S95-B** | P5: the pre-open row is the baseline; a view; front expiry |
| **S95-C** | ADR-015's gloss corrected by amendment, English only |
| **S95-D** | A break in a BUILT layer is maintenance; parity is not reopened |
| **S95-E** | Doc Protocol v5 adopted |
| **S95-F** | Generated CSVs: committed result inputs by negation line; bulk exports local by sha256 |
| **S95-G** | P8 re-scoped to dte 1; P4 gate unchanged |
