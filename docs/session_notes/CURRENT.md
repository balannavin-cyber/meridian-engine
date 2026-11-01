# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. **S95 moved at the S97 close**, asserted byte-identical at **4,816 B**, sha256 `f63116f5…` on both sides. **S99 (its pointer block, 1,090 B, sha256 `56ab7a26…`) and S100 (7,695 B, sha256 `d11e991b…`) moved at the S101 close (run in S102)**, each asserted byte-identical on both sides. **S100 (its pointer block, 1,738 B, sha256 `e9003302…`) and S101 (5,674 B, sha256 `6a68012f…`) moved at the S102 close (run in S103)**, each asserted byte-identical on both sides. **S101 (its pointer block, 1,116 B, sha256 `7313f892…`) and S102 (7,511 B, sha256 `8c50b1b1…`) moved at the S103 close (run in S104)**, each asserted byte-identical on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S103 — Friday 2026-10-30 11:05 IST → Saturday 10-31 09:11 IST** (closed in S104, Sunday 2026-11-01). Friday applied the
S102 doc-close (`762e4d7`) and the six S102 engine bundles (`f63368a` → `b2a5ce6`, suite 29/29), took the twelve owed
rulings S103-A…L in one sitting, fixed the max-pain views' timeout (S103-F, `613c2cb`), gated the WCB writer to the 09:15
open (S103-D, `82c517d`), found and fixed the WCB basket's PostgREST `max-rows` truncation (S103-G, `608917e`), renamed
TMPV and LTM in our tables (S103-H, operator SQL), and ran three Marketview rounds (Health token threshold + 0-DTE skew,
the freeze button, the prev-close view `v_close_print`). Saturday unpublished the Lovable-hosted copy (S103-M), dropped
three duplicate `market_ticks` indexes, turned on OTM OI velocity with the prior-row read bounded to the IST session
(S103-N / S103-O, `c11b564`), wrote the ADR-032 §5 / §6 impact study and ruled D2–D5 in form (S103-P…T), and built
ADR-032 F0 (tag `adr032-pre`, K2 snapshot `4e14a1d`, K3 control totals) and S1 (the eight unit COMMENTs, `8b58e54`;
**live 2026-10-31 10:14 IST** after a re-apply in S104). This block points; the detail lives in the files named. Rulings:
`docs/research/s92_parity/rulings_s103.md` (S103-A…T, the addendum merged; the single source). Evidence and findings:
`docs/research/s103/S103_close_inputs.md`, `docs/research/s103/adr032_f0_k1_k3_records_2026-10-31.md`. **Progress lives
in the tracker**, `docs/registers/agentic_layer_roadmap_S90.md` (v2.20), and **its §2.2 is the single list** of open work.

**`origin/main` — `232a3bc` + this close.** Chain: `762e4d7` (S102 close) → `f63368a` … `b2a5ce6` (the six S102 bundles,
applied 10-30 after 15:40, suite 29/29) → `613c2cb` (S103-F; contract v2.2) → `82c517d` (S103-D) → `608917e` (S103-G) →
`c11b564` (S103-N / O; step 30; tag **`adr032-pre`** here) → `4e14a1d` (K2 snapshot) → `8b58e54` (S1 SQL) → `8f9d466`,
`2b69506`, `232a3bc` (S104 PK-prune archives, docs only). Offline suite **30 steps**. Crontab 70 lines, markers line
`0 11 * * 1-5` UTC (16:30 IST) read back. **Marketview live = staging = `6f14a92`** (bundle `index-BIJiXoC3.js`; chain
`30998f2` → `05f556c` round 1 → `2f3c2f0` round 2 → `6f14a92` round 3; rollback target `/var/www/marketview.bak-2f3c2f0`;
backups `.bak-2f3c2f0`, `.bak-05f556c`, `.bak-30998f2` + three `PRE_*`). Database: `v_gex_max_pain` / `v_gex_pin_maxpain`
on the skip-scan `latest_run` (3537 / `6eddea31…`, 3026 / `70d32c77…`); `v_close_print` (`92a4eac4…`); the three
`market_ticks` duplicate indexes dropped; the eight `ADR-032:` column COMMENTs; TMPV / LTM renamed in six tables.

**What was established**

1. **ADR-032 D2–D5 ruled in form (S103-P…T), nothing built past S1.** D2 additive (new nullable per-1 % columns beside
   the old, written by the writer and every formula copy in one bundle; wrappers repointed; board unchanged); D3 a dated
   unit break everywhere, no conversion of history; D4 COMMENTs (**live**, S1); `hist_gamma_metrics.net_gex` is one scale
   throughout (≈ 1e7 × live; left and commented); Pine labels relabelled when that round is built; the legacy objects
   become one retirement TD (TD-S103-NEW-7) whose first step is to name the `service_role` PostgREST reader of
   `wcb_signal_validation_v2` / `latest_signal_snapshots` (632 / 490 / 236 and ~100 calls; flat across Saturday). **S2
   onward is held until after launch** (operator: ~10 days). Study `docs/research/s103/adr032_s5_s6_impact_study_S103.md`;
   fallback plan `docs/research/s103/adr032_fallback_plan_S103.md`; the two S104 read-only CC sweeps (engine box 28 min,
   retail box 6 min; `docs/research/s104/sweep_engine/`, `sweep_retail/`) found no magnitude reader and four scale
   conventions in the repo, a fourth `gamma_metrics.net_gex` writer that never fired (`insert_option_chain_batch`), a D1
   defect (`v_gex_greeks_l2_strike_1pct` converts 2 of 4 Γ columns, TD-S103-NEW-9), and that additive DB columns are
   invisible to every retail gate by construction. ADR-032 **Amendment A** records all of this.
2. **The WCB basket was truncated by PostgREST, not by the client's 5,000 cap (S103-G).** NIFTY priced 13 of 50 every cycle
   since 10-26 (the first 13 tickers alphabetically); the basket's 4,106-row history came back in `(ticker, trade_date)`
   order under `max-rows = 1,000`. Fixed `608917e` (bounded 30 d, ordered, paged; prior close rejected past 5 days).
   Every `limit > 1000` without paging is the same class (TD-S103-NEW-1). First full read Monday 2026-11-02 (50 of 50).
3. **Two NIFTY constituents sat unpriced for weeks under exchange renames (S103-H):** TATAMOTORS → TMPV, LTIM → LTM
   (LTIM's prior close dated 2026-03-27). Renamed by one fail-closed `DO` block across six tables (308 / 80 / 1 / 1 / 1 / 1
   rows); no code change. 77 of 1,385 universe symbols are not Zerodha EQ symbols (TD-S103-NEW-2); LTIM and TMPV both
   carry `weight_pct 1.1345` (TD-S103-NEW-3).
4. **`v_gex_max_pain` / `v_gex_pin_maxpain` timed out on a full index walk (S103-F):** `DISTINCT ON (symbol)` over
   2,207,583 rows, 17,562 ms against `authenticator`'s 8 s; rebuilt on the S79 / S72 skip-scan `latest_run`: 17,891 ms →
   81 ms, equality 271 = 271. TD-S90-NEW-5 CLOSED; TD-S101-NEW-1 closes on the first clean 14:00 cycle.
5. **Board rounds 1–3 (S103-A, -C, -I, -J).** Health token scored as the daily writers are (`statusFor(age, 1440)`); IV
   skew shows `SKIPPED_EXPIRY · front leg expires today` plus the next leg; an explicit `freeze` / `resume` button with a
   full-width "frozen since" strip (Space removed); `useOpenGap` reads the previous close from `v_close_print`
   (`close_rank` 1 = `dhan_idx_i` 16:00–16:10, 2 = `dhan_charts_historical` 15:29–15:31; 10-21 proved the fallback).
   Each round: guard → staging read → refusing promote with live ≡ named backup by `diff -rq`. S103-B (board-side leg roll
   after an expiry-day close) is ruled, not built — Tuesday 2026-11-03 after 15:40.
6. **OTM OI velocity was NULL in every production row because the prior-row read selected no `raw` (S103-N);** the read is
   now bounded to the IST session (S103-O), so `straddle_velocity` is NULL on a session's first cycle too. `c11b564`, step
   30 (14 cells, M1–M4, 0 surviving). First live read Monday.
7. **Process.** The S1 COMMENTs were applied 09:00, then removed by a superseded rollback block left in the chat and run
   after the apply (§D.57.13); re-applied in S104 from the committed file; **the only valid S1 rollback is Appendix A4 of
   `docs/research/s104/S104_session_prompt.md`** (restores the `gex_cr` sign note exactly). After every ADR-032 stage the
   K3 queries must return the F0 record's rows.

**Filed:** TD-S103-NEW-1…11 (-10 closed at filing: the study §4 and K2 md5s annotated with their `pg_get_viewdef` form).
**Closed:** TD-S102-NEW-1 (unpublished), TD-S102-NEW-6 (the two pre-rule backups rotated out), TD-S102-NEW-7 (three pairs
dropped), TD-S102-NEW-8 (one scale, commented), TD-S101-NEW-13 (live `05f556c`), TD-S90-NEW-5 (`613c2cb`).
**Enhancement Register:** ENH-146 / ENH-147 minted (post-parity Candidates A and B, PROPOSED, owed since the S89 close).

**Corrections to my own work:** Assumption Register **§D.57** (S103 + S104, 16 rows). The one to carry: a superseded
rollback block must not stay in the chat once replaced (D.57.13), and a PK doc is deleted only after its git copy is read
and found identical, not assumed (D.57.16).

**ADR-032 Amendment A (D2–D5 RULED in form; F0 + S1 LIVE; S2 held); CLAUDE.md v1.75 (settled line updated; rules 0–25
unchanged).** System Map §S103; Deployment Topology §S103.

**Project-knowledge prune (S104, 2026-10-31):** 186 → 149 docs. Every deleted doc is in git — the S100–S102 session
prompts at `docs/research/s100/`, `s101/`, `s102/` (`8f9d466`); the S98–S102 close inputs, rulings and working docs
already at `docs/research/s98/` … `s102/`, `s89_rulings/`, `s90_agentic/`, `s92_priority/`, `s96_priority/{p7,guard,p3b}/`,
`docs/lovable_prompts/s97/`, `docs/research/post_parity_candidates.md`; five PK-only parity docs archived at
`docs/registers/archive/pk_only_2026-10-31/` (`2b69506`) and twelve more at `docs/registers/archive/pk_only_2026-10-31b/`
(`232a3bc`), each folder with a verified `SHA256SUMS`. The audit with the per-doc rulings is
`docs/research/s104/pk_prune_audit_S104.md` (also in PK as `claude/pk_prune_audit_S104.md`). This close deletes the ten
DEFERRED S103 docs after it lands; their git homes are `docs/research/s103/`, `docs/lovable_prompts/s103/` and `sql/`.

## NEXT SESSION PICKS UP

1. **Monday 2026-11-02 live checks** (`docs/research/s103/S103_close_inputs.md` §5): END line rc on a failing ingest;
   breadth-from-ticks run time; the 09:05 refresh writes `NSE:LTM`'s prior close; futures rows one per symbol per minute
   with `raw.spot_source = dhan_ltp_idx_i_same_request`; markers `close_1530` from CAS at 16:30; the 09:10 WCB cycle
   `SKIPPED_NO_INPUT`, first row 09:16 with 50 of 50 priced; wsfeed subscribing `LTM` / `TMPV`; the 14:00 ENH-133 cycle
   clean; Health OVERALL green; `otm_oi_velocity` NULL on the first cycle, a number from the second, none spanning two IST
   dates (`straddle_velocity` the same); R16 live read; after 15:40 re-run the `pg_stat_statements` query and compare
   `calls` on `wcb_signal_validation_v2` / `latest_signal_snapshots` (a rise = live reader).
2. **Tuesday 2026-11-03:** read the expiry-day branch of S103-C before 15:30; build S103-B (board leg roll) after 15:40.
3. **Tracker §2.2 remainder in its order:** B2 R5 / R38 live reads; BS-1 credential rotations and port 22 (operator);
   B3 chain data correctness; TD-S101-NEW-4's other half (`recent_max_strikes` unbounded); manual option B timing (owed).
4. **ADR-032 build only after launch:** S2a–S2c per `docs/research/s103/adr032_fallback_plan_S103.md`; after each stage
   re-run the K3 queries (S104 prompt Appendix A5) against the F0 record; rule the emergency lever then (proposed: valid
   only at S2b–S2c; from S3 the recovery is the SQL wrapper revert); the dated unit-break row is written at S2c.

## OPERATOR RULINGS, S103

**All rulings live in `docs/research/s92_parity/rulings_s103.md`**, the single source.

| # | Topic |
|---|---|
| **S103-A** | Health OVERALL token threshold: scored as the daily writers (LIVE `05f556c`) |
| **S103-B** | NIFTY board after the expiry-day close: board-side roll to the next leg (ruled, not built) |
| **S103-C** | Context IV skew on a 0-DTE front leg: `SKIPPED_EXPIRY` + the next leg (LIVE `05f556c`) |
| **S103-D** | WCB writer: no row before the 09:15 IST open (`82c517d`) |
| **S103-E / K** | `held_for_cycles` resets on an expiry roll: the design, recorded |
| **S103-F** | `v_gex_max_pain` / `v_gex_pin_maxpain` on the skip-scan `latest_run` (`613c2cb`) |
| **S103-G** | WCB basket bounded, ordered, paged; prior close under a 5-day floor (`608917e`) |
| **S103-H** | TMPV and LTM renamed in our tables (operator SQL) |
| **S103-I** | R16 freeze button + strip (LIVE `2f3c2f0`); R36 closed as read |
| **S103-J** | R20 (a): `v_close_print` + `useOpenGap` (LIVE `6f14a92`) |
| **S103-L** | TD-S97-NEW-4 (b) closed as by design |
| **S103-M** | Lovable-hosted public copy: unpublished (404) |
| **S103-N / O** | OTM OI velocity on; prior-row read bounded to the IST session (`c11b564`) |
| **S103-P…T** | ADR-032 D2 additive · D3 dated break · D4 COMMENTs · Pine labels · legacy objects one retirement TD (S103-T amended: name the `service_role` reader first) |

## Previous session S102

**S102 — Wednesday 2026-10-28 09:58 IST → Friday 10-30 11:05 IST** (doc-close `762e4d7`, run in S103). Every Γ size on
the board was 100 × its "₹ Cr" label; fixed in the database in one morning (ADR-032 D1, seven `_1pct` wrapper views, two
Lovable rounds, manual v0.5, live `30998f2`); six engine bundles built 10-28 and applied in S103. The full block is in
`docs/registers/CURRENT_history.md`.

## OPERATOR RULINGS, S102

**All rulings live in `docs/research/s92_parity/rulings_s102.md`**, the single source.

| # | Topic |
|---|---|
| **S102-A** | Γ size: display-only rescale first (× 0.01 to ₹ Cr per 1 % move) |
| **S102-B** | ADR-032: D1 display now; D2–D5 after the impact study and roadmap |
| **S102-C** | D1 board wording table W approved; √τ (R26) not taken |
| **S102-D** | Legacy pages rescale, not retire |
| **S102-E** | Manual: text restated now (A), new screenshots later (B) |
| **S102-F** | Close S102; the doc-close runs in S103 |
