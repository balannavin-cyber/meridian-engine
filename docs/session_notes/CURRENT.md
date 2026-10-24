# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. **S95 moved at the S97 close**, asserted byte-identical at **4,816 B**, sha256 `f63116f5…` on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S97 — 2026-10-12 → 10-13, resumed 2026-10-22 → 10-23.** S96's owed list cleared; on resuming, alerting
found dark since 10-08 and, once lit, noisy — four fixes; the 10-21 outage diagnosed. This block points; the
detail lives in the files named. Rulings: `docs/research/s92_parity/rulings_s97.md` (S97-A…N, the single
source). **Progress lives in the tracker**, `docs/registers/agentic_layer_roadmap_S90.md` (v2.14). The
10-13 → 10-19 parity-target evaluation ran in separate chats and is documented there (project knowledge
`claude/parity_eval/`, final report `parity_target_final_report_2026-10-19.md`); **it is not triaged here** (NEXT 1).

**`origin/main` — all pushed.** Manual session `…856d9d2` · S97-I `44b8b96` · S97-J `d5167db` · TD-S97-NEW-20
`754ffad` · S97-N `74b45ce` · this close. Local = GitHub = EC2 at `74b45ce` before this close; **pull
`~/meridian-engine` to this close** (docs only). **meridian-connect LIVE `04fcd05`** (bundle `index-BrWRk1OP.js`:
S97-A wording + the `/manual` help route); backup `/var/www/marketview.bak-804d684`; `.bak-1deeb87` deleted.

**What was established**

1. **P7 DONE** — live read 2026-10-12 09:54–10:01 IST, L1–L4 equal on both symbols on matching runs. **P3 DONE** —
   P3b applied after the 10-12 close (**ENH-145** LIVE), Section A and B exact, sweeps 10-13 → 10-19 with 0 errors, 0 FAIL.
2. **DDL applied by the operator:** P3b; TD-S95-NEW-2 calendar backfill (S97-E); `idx_gss_ts`, ANALYZE and `ts`
   statistics 1000 (S97-F/G: the 10-09 estimate 1 → 17,381 against 19,198); Rule 13 rows for SENSEX 09-25 → 09-29
   (S97-H) and the 10-21 ledger (S97-M); the S90-H backups dropped (S97-L). ACL re-baselined 10-22 05:42 IST
   (`docs/lovable_prompts/s92/README.md`).
3. **Alerting.** Every `send_alert` sender was undelivered 10-08 → 10-22 (≥ 109 sends; Telegram rejects
   `parse_mode: 'plain'`) — `44b8b96`. The monitor read in-progress runs as FAILED (~44 % of minutes) — `d5167db`;
   its 5-min look-back raced the orchestrator's row creation — `754ffad`. The contract check's spot condition fired
   pre-open, after 15:15 and at 1 min on a 60–63 s writer — `74b45ce`. Each tested with controls; Local = GitHub = EC2.
4. **2026-10-21 lost to a lapsed Dhan Data API subscription** (renewed 10-22 ~05:06 IST): the market-data tables are a
   gap, and the orchestrator logged 83 SUCCESS cycles on 10-19's run_ids (**TD-S97-NEW-4, S1**). The Zerodha feed was
   down 10-14 / 10-15 / 10-19 on missed Kite refreshes (TD-S97-NEW-6).
5. **Board:** S97-A (drop "dealer", add the P2 tag) and the `/manual` help page, promoted together.

**Corrections to my own work:** Assumption Register **§D.51** (15 rows, all mine). The one to carry: a simulated
query must bound by the moment it runs, not only by its filter (D.51.12).

**No ADR filed or amended; rules 0–24 unchanged.** `CLAUDE.md` gains one anti-pattern line (the silent sender).
System Map §S97; Deployment Topology unchanged (no host or boundary change).

## NEXT SESSION PICKS UP

> **S99 (2026-10-24): the list below is superseded by tracker §2.2, the single list** (`docs/registers/agentic_layer_roadmap_S90.md`, v2.15). Item 1 done (S98-A + S99-C); item 3 deployed `2edd25f` (S98-B), live PASS read Mon 2026-10-26 after 15:45 IST. This block is rewritten at the S98 / S99 doc-close.

1. **First concern — reconcile the three streams into one ranked table** (operator, 2026-10-23 03:27 IST): S97's open
   TDs; the parity-target evaluation's MERIDIAN-side findings (`claude/parity_eval/parity_target_final_report_2026-10-19.md`
   — named so far: the board never shows the official 15:30 close and labels frozen values "LIVE", likely one cause with
   the 15:15 spot stop; NIFTY / SENSEX flip offsets); the tracker's open items (P4, P8) and the carried TDs. Each row:
   source, overlap, kind (TD / ENH / ruling), roadmap item touched, recommendation. **Findings enter a register only by
   that ruling**; the ruled table updates the tracker. Session prompt: `claude/S98_session_prompt.md`.
2. **Live confirmations owed for 2026-10-23**, the first day on `754ffad` / `74b45ce`: no "not firing" / RECOVERED pairs
   on healthy cycles; no spot alarm at 08:34 or 15:19 IST; `[CLEAR] contract_spot_stale` on the first passing check;
   `equity_eod` / `breadth_indicators_daily` for 10-21 after the 16:10 IST EOD (TD-S97-NEW-12).
3. **TD-S97-NEW-4 (S1)** — the runner refuses stale run_ids; the contract counts its own writes. Capture path: S90-J
   window, replay check, written rollback.
4. **Small owed:** wire `tests/test_contract_check_s97.py` into `tests/run_offline.sh`; commit the S97 applied SQL
   (index, statistics, two Rule 13 rows, drops) to `sql/`, checked against the catalog; manual v0.4 re-stamp (board
   bundle one behind; the §3.5 caption shot); commit the help-round record from project knowledge to `docs/lovable_prompts/s97/`.
5. **Open for the operator:** TD-S97-NEW-6 (Kite refresh) · -13 (10-21 spot and close backfill) · -15 (symbol column) ·
   -16 (backup retention) · -17 (Hedge-tile wording) · -18 (flow gap on the board).
6. **Filed this session:** TD-S97-NEW-1…21 (1, 2, 7 and 20 fixed in session).
7. **Carried:** TD-S96-NEW-2 (mitigated), -3 · TD-S94-NEW-1…4 · TD-S93-NEW-1 / -3 · TD-S91-NEW-2 sites 1, 3, 4, 5, 6 ·
   TD-S91-NEW-3 · TD-S80-NEW-1 · TD-S92-NEW-3…6 · P4 accruing (n = 20 per symbol, about mid-January 2027) · P8 gated on P4.

## OPERATOR RULINGS, S97

**All rulings live in `docs/research/s92_parity/rulings_s97.md`**, the single source.

| # | Topic |
|---|---|
| **S97-A** | "Dealer" wording on the ∂Δ/∂t, ∂Δ/∂σ surfaces: drop it, add the P2 tag |
| **S97-B** | Planner estimate on `gex_strike_snapshots`: measure first |
| **S97-C** | After-15:15 clock split: recorded, no change |
| **S97-D** | Untraded-leg survey (a) first, then rule on (b) |
| **S97-E** | Calendar backfill as written; a TD for 09-14 |
| **S97-F** | `idx_gss_ts` plus ANALYZE |
| **S97-G** | `ts` statistics target 1000 |
| **S97-H** | Rule 13 range, SENSEX 2026-09-25 → 09-29 |
| **S97-I** | Telegram: drop `parse_mode`, log refusals |
| **S97-J** | Monitor: an in-progress row is not a failure |
| **S97-K** | Contract check: let it run, measure later |
| **S97-L** | Drop the S90-H backups |
| **S97-M** | 10-21: Rule 13 for the ledger only; market data a gap |
| **S97-N** | Contract check spot: 09:15–15:15 IST, 3 min, clear on pass |

## Previous session S96

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

## NEXT SESSION PICKS UP — as S96 left it (SUPERSEDED by the S97 list above)

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
