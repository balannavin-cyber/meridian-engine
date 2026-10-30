# S102 close inputs (Wed 2026-10-28 09:58 → Fri 10-30 11:05 IST)

> **Session closed at the operator's call, 10-30 11:05 IST** ("EOS document and carry forward"). The Doc Protocol v5
> doc-close runs at **S103 open** from this file (precedent S101-H). Rulings single source: `claude/rulings_s102.md`.
> Next: `claude/S103_session_prompt.md`.
>
> **Record limit, stated:** the session's working transcript before 10-30 09:46 IST was compacted. The 10-28 evidence below
> is what survives in the bundles' own commit messages and baselines (scratch `s102r48 / r40 / td8 / fut / argv / mk`) and
> the compaction summary. Operator-pasted 10-28 SQL outputs not quoted in a commit message are **not** retained here; where
> a figure matters for a doc-close row, re-read it rather than reconstruct it.

## 1. State at close

| Tree | State |
|---|---|
| **meridian-engine** `origin/main` | **`3abb83f`** (S101 doc-close, applied 10-28; four-way + Local PASS). **No S102 engine commit pushed.** |
| **meridian-connect** `origin/main` | **`30998f2`** (manual v0.5, pushed from the box). Chain since live `f964e40`: `27c0e17` (manual v0.4) → `2f60ffe`/`f27aae5` round 1 → `8326ed0` merge PR #1 → `56539fd`/`3b3b0d4` round 2 → `7cba2cd`/`1171975` Σdmp wording → `30998f2` manual v0.5. |
| **Marketview live** | **`30998f2`**, bundle `index-EtZmieBR.js`, promoted 10-30 11:01 IST; **live read PASS** 11:02. |
| **Marketview staging** | `30998f2` (same build, base `/staging/`). |
| **Rollback target** | `/var/www/marketview.bak-27c0e17` = `f964e40` JS (`index-BFOk56iL.js`) + manual v0.4 (`489a135e…`, copied in separately after `f964e40`); proven by `diff -rq` and the manual sha. Backups now: `.bak-27c0e17`, `.bak-f964e40`, `.bak-1aeb000` + `PRE_IV_20261004_0329`, `PRE_S89_20261003_1340`, `PRE_S81` (`.bak-3366bf1` removed, S100-L). |
| **Database** | 7 `_1pct` wrapper views live (`sql/2026-10-30_s102_gex_per_1pct_views.sql`, project copy `claude/2026-10-30_s102_gex_per_1pct_views.sql`); `v_market_ticks_eq_latest` live (applied 10-28, see §2.2). |
| **ACL baseline (new, 10-30 10:59)** | `relations 358 830967b5d158d971e09aa6b842b167d0` · `anon_public_privs 263 1f2383944b7812dd37299130ff34274a` · `anon_writable_objs 0` · `public_functions 41 ef1d66a16b1f17179f0f6fcbe2167d60` · `rls_policies 80 be718afbcc6537d31711f3923554ee56` · `default_privileges 27 9db86164a910289c334eb7691007cd58` · `schemas 10 2a88931808ed74928a291a548c3678ed` · `public_triggers 0` · `anon_role 1 c506ff143129b1a369c90214c9489eaa`. Replaces the S97 baseline in `docs/lovable_prompts/s92/README.md` (whose `rls_policies` S100-K had already moved). |
| **Project knowledge** | Re-uploaded 10-30 11:15 IST from engine `3abb83f` with `pk_extract_s100.py` (owed since the S101 doc-close — the project copies were still 10-24): `claude/CURRENT.md`, `claude/session_log.md`, `claude/tech_debt_LATEST.md`, `claude/merdian_reference_LATEST.json`, `claude/MERDIAN_Enhancement_Register_LATEST.md`, `claude/agentic_layer_roadmap_S90.md`, `claude/CLAUDE_history.md`, `CLAUDE.md` (v1.73). Not re-uploaded (repo only, size): Assumption Register, System Map, Deployment Topology. Next re-upload after the S102 doc-close commit. |
| **Box packages** | `markdown 3.10.3`, `mdx_truly_sane_lists 1.3` installed `pip3 --user --break-system-packages` (ssm-user) for `build_help_pack.py`. Rebuilding v0.4 under 3.10.3 reproduces the live v0.4 `manual.json` byte for byte. |

## 2. Evidence

### 2.1 Part A — S101 doc-close (10-28)

Commit **`3abb83f`** "MERIDIAN: [DOCS] S101 doc-close (Doc Protocol v5, run in S102): CURRENT / session_log / tech_debt
(5 closed, TD-S101-NEW-1..17) / AR D.55 / System Map + Topology S101 / CLAUDE.md v1.73 (rule 25) / tracker v2.18 /
reference v79" — box route, dry-run then apply PASS, four-way + Local PASS (operator-pasted, 10-28). Bundle
`s102_docclose.tgz`. The commit stated 1,042 insertions; actual 821 (§6 item 1).

### 2.2 Part B / Part C — 10-28 (six engine bundles built and tested; **none applied**)

B1 pin path across the NIFTY expiry roll, part 2: **PASS** (per the compaction summary; the pass line first assumed a
per-symbol carry — the writer carries per `(symbol, expiry_date)`, §6 item 2). **B2 R19 re-read: not done** (carried).

| Bundle | Change | Offline step | Measured basis (from the commit message) |
|---|---|---|---|
| `s102r48.tgz` | R48 `run_ingest.sh` reports the ingest rc on its END line (`rc=0; python3 … \|\| rc=$?`); R49 monitor comment (FAILED alarm reads exit_code alone) | 26 (`tests/test_run_ingest_rc.py`, mutant M1) | under `set -e` the END line never printed on failure |
| `s102r40.tgz` | R40 breadth-from-ticks keyset-reads `v_market_ticks_eq_latest` instead of paging every EQ tick | 20 (+B8–B10, M5–M7) | old read ~161,000 rows / ~162 calls / 140–176 s per run on a 1-min cron; 379 of 431 runs > 60 s on 10-26/27; view: 1,313 rows in 406.6 ms (EXPLAIN ANALYZE 10-28); view applied by the operator 10-28 (1,313 = 1,313 distinct = 1,313 raw; anon / authenticated no SELECT) |
| `s102td8.tgz` | TD-S77-NEW-8 `refresh_equity_intraday_last.py` ledger via `core.execution_log`; removes a stray `PYEOF` that broke import | 27 (E1–E7, M1–M4) | `enforce_orchestrator_timeout.py` stays hand-rolled (logs for a killed process) |
| `s102fut.tgz` | TD-S100-NEW-1 futures basis vs the index LTP from the same Dhan request (`IDX_I 13 / 51`) | 28 (F1–F5, M1–M3) | 10-26/27 15:30–15:40 rows off the chain close: NIFTY mean 23.6 (max 36.2), SENSEX 83.8 (max 125.2); intraday agree (NIFTY mean 2.7, SENSEX 2.4) |
| `s102argv.tgz` | futures writer captures only the symbol its cron line names | 28 (+F6, M4) | 10-27: 150 rows over 75 distinct minutes per symbol (both cron lines wrote both) |
| `s102mk.tgz` | TD-S91-NEW-18 / TD-S74-NEW-5 session markers read the CAS-settled close; markers cron 16:10 → 16:30 IST (`40 10` → `0 11` UTC) | 29 (C1–C5, M1–M3) | `MISSING_CLOSE_1530` every session 10-12..10-27 both symbols; CAS rows 10-22..10-27; 10-27 = 22749.75 / 73598.67 |

**Apply order is fixed** (each bundle's `baseline.txt` is the previous one's post state): **r48 → r40 → td8 → fut → argv →
mk**. Engine code: apply after 15:40 IST, push after 16:30 IST (S90-J); the offline suite (now 29 steps) out of hours, under
`ulimit -v`. `s102mk` needs the live crontab edited in the same change. Main is still `3abb83f`, so every baseline holds.

### 2.3 ADR-032 D1 — Γ in ₹ Cr per 1 % move (10-30), end to end

| Step | Evidence |
|---|---|
| Inventory | `claude/gex_unit_inventory_S102.md` v2 (fresh-look re-check; v1 had three wrong entries, §6 item 7) |
| Views | 7 wrappers applied; T1 (7/7 incl. ∂Γ rerun 10:22: `bad`/`same_as_x1`/`same_as_x01`/`null_mismatch` 0, `n_rows` 4–1,856), T2, T3, T4, T5 (anon, one execution) PASS |
| Round 1 | board, 7 files, 41 replacements (`claude/lovable_prompt_s102_gamma_per_1pct.md`); guard `mv_lovable_guard_s102.sh` PASS; staging vs SQL at 09:30 both symbols PASS |
| Round 2 | legacy, 2 files (`src/lib/queries.ts`, `src/marketview/sections.tsx`), 10 replacements (`claude/lovable_prompt_s102b_legacy_per_1pct.md`); guard `mv_lovable_guard_s102b.sh` sha256 `00767d959b36406dcc8ee12b4337e2fe4d9ef167b7c34076c06ff0d6dd7bab80` PASS at `3b3b0d4` and `1171975`; staging vs SQL: NIFTY (ts 04:40:06 UTC) Net Γ 1,569.67, Σdmp 35,741.83 / Σamp −34,172.16, pk 6,446.75 @ 23000, 104 strikes, intraday max 10,159.25; SENSEX (04:40:07) −256.05, 4,309.87 / −4,565.93, pk 525.42 @ 75000, 163 strikes, intraday 117.30 / −579.16; ∂Γ SENSEX chain 10:15 −101.77 / 652.95, −12.64 / 506.65 = staging −102 / 653, −13 / 507 — **all PASS** |
| Manual | v0.5: 18 anchored edits on engine `3abb83f` source (`0f103a58…` → `e4872ab6…`), built on the box by `s102_manual_v05.sh` (`2fa161d3…`), `manual.json` `ede04e14d990bf54e8eaf24f60e062c1ec423e6c6204591b0bbfea4f0d7c4481`; commit `30998f2`; staging read: hash match, `v0.5 (draft)`, 16 × "per 1 % move", "unit definition pending" only in the two historical notes |
| Promote | 11:01 IST, refusing block (HEAD, clean tree, live ≡ backup, manual hash, `/assets/` root) → `LIVE = 30998f2 · assets/index-EtZmieBR.js · rollback /var/www/marketview.bak-27c0e17` |
| Live read 11:02 (SENSEX, chain 11:00) | board Net Γ `+595 Cr · long γ · 0.06 of gross · ₹ Cr per 1 % move`; Hedge per 1 % SELL 595 (= −Net Γ × 1 %); ∂Γ −20 / 678, −92 / 567; legacy NET Γ +594.78 with `₹ Cr per 1 % move`; Σdmp line with unit; manual v0.5 hash; 0 "unit pending" — **PASS** |

## 3. Next (carried to S103)

1. **S102 doc-close** (Doc Protocol v5) from this file — S103 Part A. Files to land in the engine repo with it:
   ADR-032 → `docs/decisions/ADR-032-gex-stored-unit.md` + Decision Index row; `sql/2026-10-30_s102_gex_per_1pct_views.sql`;
   `docs/research/s102/gex_unit_inventory_S102.md`; `docs/lovable_prompts/s102/` (both prompts, both guards, round records
   from §2.3, `s102_manual_v05.sh`); the ACL baseline in `docs/lovable_prompts/s92/README.md`; the engine manual source
   `docs/marketview_manual/marketview_user_manual.md` at **v0.5** (`e4872ab6…`, apply the same 18 edits — the box script's
   `edits_man.py` is the edit list) so the engine source equals the live pack again; CLAUDE.md settled line (ADR-032
   governance language: *"Γ sizes on the board are ₹ Cr per 1 % move, made by the `_1pct` wrapper views; stored columns
   remain γ·OI·S²/1e7 until ADR-032 D2 is ruled."*).
2. **The six 10-28 engine bundles**, in the §2.2 order, after 15:40 IST / push after 16:30 IST; re-run the offline suite
   (29 steps) out of hours under `ulimit -v`; markers crontab edit with `s102mk`.
3. **B2 R19 re-read** (carried from S101): `breadth_indicators_daily` gains 10-26 / 10-27 (and later dates).
4. **Manual follow-ups**: `board_bundle` stamp → `index-EtZmieBR.js` (`build_help_pack.py` `BOARD`); option B (new
   screenshots on the per-1 % scale).
5. **ADR-032 §5 impact study and §6 roadmap** before any D2–D5 ruling.

## 4. Rulings owed (raise each with a recommendation before building)

From S101 §5 / S102 prompt: Health OVERALL token threshold; NIFTY board after the expiry-day close; Context IV skew on a
0-DTE front leg; WCB from pre-open ticks; `held_for_cycles` across an expiry roll on the same strike. From S102 10-28 (per
the compaction summary; re-state each from the code before asking): rulings 1–5 as raised that day, R16 freeze fix,
R20 (a/b), TD-S97-NEW-4(b). New at S102: **the Lovable-hosted public copy** (§5 first row) — unpublish or keep;
**manual option B** timing; **ADR-032 D2–D5** after the study.

## 5. Findings to file (TDs, at the close)

- **Lovable-hosted public copy** `https://meridian-welcomer.lovable.app/` serves whatever `main` holds each time Publish is
  clicked — outside staging, the guard, promote and the box's access setup. Publish was clicked 10-30 ~09:55 IST at
  `3b3b0d4` (unreviewed at the time). Reads only anon views; recommendation: unpublish unless used.
- **Help pack `board_bundle` stamp stale**: `index-BFOk56iL.js` in `manual.json`; live is `index-EtZmieBR.js`.
- **Manual screenshots on the old scale** (21 shots) — v0.5 text says so; option B owed.
- **Engine manual source behind the live pack** until the S103 doc-close lands v0.5 in `docs/marketview_manual/`.
- **Two writers raced one change** (10-30 10:47): the Σdmp fix was applied by Lovable *and* committed on the box; the box
  push was rejected (`fetch first`) and the box commit dropped by a refusing reset. Rule for the prompts README: one
  writer per change — either Lovable or the box, never both.
- **Live tree carried a file copied in outside a build** (manual v0.4 into `/var/www/marketview/help/` after `f964e40`),
  so a `.bak-<sha>` name cannot be trusted without `diff -rq`. Promote block now checks live ≡ named backup.
- **`NarrativeModal.tsx`** (unused, no importer) renders `netDealerGamma` with a bare "Cr" — dead code; delete or label.
- **`market_ticks` duplicate indexes** (measured 10-28; figures not retained — re-read `pg_indexes` before filing).
- ADR-032 §5 open questions stay open: `hist_gamma_metrics`' unit, pre-TD-NEW-3 `gamma_metrics` rows, the OI unit of
  `backfill_gamma_metrics_to_main.py`'s source, in-place conversion cost vs a dated break.

## 6. Assumption Register §D.56 (corrections to my own work, S102)

1. The doc-close commit message stated 1,042 insertions; actual 821.
2. Pin PASS line assumed a per-symbol carry; the writer carries per `(symbol, expiry_date)`.
3. R20 query denominator excluded 10-21; fixed by reading `trading_calendar`.
4. A query named `trade_date` where the table has `trade_date_ist`.
5. Round-1 Lovable prompt: fingerprint counts stated 12 / 16 before computing; computed 13 / 15.
6. Doc-close TD history anchor matched 3 times; caught by the count == 1 assert, fixed with a heading-line regex.
7. **GEX unit inventory v1 listed three non-Γ-size surfaces** (Pin rank values, local-γ pocket, Γ at pin) as rescale
   targets; found by an independent re-check against the code; v2 corrected (§6 of the inventory).
8. Outside review found gaps in the D1 SQL tests (no anon read, no dedupe in T2, T3 label, missing ₹, caveat wording); fixed
   before apply.
9. Round 1 landed on `lovable-sync`, not `main`; merged PR #1 with a merge commit.
10. **Round-2 Σdmp wording revised after the operator had already pasted the first prompt**, so staging carried the older
    wording and needed an extra round (and produced the two-writer race, §5).
11. The pinned ∂Γ query assumed `v_gex_greeks_l2_net_1pct` keeps history; it holds only the latest chain, so it returned no
    rows. I then guessed IST storage — also wrong; one unpinned read settled it.
12. **Promote block set `PREV=27c0e17` from the round-1 guard comment without reading live first**; I then said the name
    was wrong (live JS = `f964e40`) before diffing; the diff showed live = `f964e40` JS + manual v0.4 = the `27c0e17` tree.
    Two unverified claims in a row about the rollback target.
13. **The rollback command was printed in the same message as the promote, outside a refusing block**; the operator
    pasted it and live reverted for ~1 min (10-30 ~11:00). Violates the standing rule. Rollback text now only inside a
    refusing block, and never in the same paste-ready message as the forward step.
14. Gave a GitHub web-UI upload step and "upload the guard" (already on the box) to an operator working by command.
15. Stated the manual hash expectation before checking the box's markdown version (3.10.3 vs my 3.11); verified equal
    afterwards.
16. Recorded "So lets go" as ruling A without an explicit A (stated as such in `rulings_s102.md` S102-E).
