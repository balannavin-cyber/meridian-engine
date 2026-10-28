# S101 close inputs (Sun 2026-10-25 20:41 → Wed 10-28 09:58 IST; Parts A + C2–C7 DEPLOYED 10-26 17:08 IST, LIVE-VERIFIED 10-27)

> **Session closed at the operator's call, 10-28 09:58 IST.** The Doc Protocol v5 doc-close runs at **S102 open** from this file
> (precedent: S98 + S99 closed in S100, `3ad5c81`). Rulings single source: `claude/rulings_s101.md`. Next: `claude/S102_session_prompt.md`.

## 1. State

- **`origin/main` = `~/meridian-engine` = `~/meridian-cc` = Local = `4a1d8e1`** (four-way PASS 10-26 17:12 IST: blob digest
  of the 17 changed files `a3398d5655e4d620` on GitHub, `~/meridian-engine`, `~/meridian-cc`; Local `git diff --stat 4a1d8e1` = 0).
  Fast-forward `7b91d1a → 4a1d8e1`, pushed from `~/meridian-cc` as `4a1d8e1:main` after an is-ancestor check.
  Chain: `7b91d1a` → `11f2cbe` A2–A7 → `4ed5671` C2 → `50bef37` C3 → `a0b6115` C4 → `e0fb11d` C5 → `02a06ec` C6 → `4a1d8e1` C7.
- **Rollback: not needed** — the live read of 10-27 (§2) found no fault. It stays written (guarded refusing block, not run):
  in `~/meridian-cc`, `git checkout main && git pull --ff-only && git revert --no-edit 7b91d1a..4a1d8e1 && git push origin main`,
  then `git pull --ff-only` in `~/meridian-engine`.
- Bundles (`s3://meridian-engine-deploy/s101/`): `s101_bundle.tgz` (A), `s101b.tgz` (C2–C5), `s101c.tgz` (C6),
  `s101d.tgz` (C7), `s101_deploy_check.py` (`540495da…6f5b`).
- Backups: A `*_PRE_S101` (gitignored); C2–C7 `scratch/s101/<cN>/backup/` in `~/meridian-cc`.
- MR-S2 told (10-26 17:43 IST): main = `4a1d8e1` exactly, no later commits, deploy-check result + compared fields, no rollback.

## 2. Evidence (box, operator-pasted; board reads by Claude in the operator's Chrome)

| Commit | Step | PASS |
|---|---|---|
| `11f2cbe` | A1 purity map | script `b51b630b…`, table `33bc6a8b…`; 29/33 pure; selftest 10 controls + 8 mutants |
| | A2 extract | dry-run = POST = applied tree; 3 M + 7 new paths |
| | A3a AST | 29/29 + 10/10 moved defs identical; 36 + 37 kept statements identical; mutants 5/5 |
| | A3b golden replay | 486/486, before = after `81f5508d…`; divisor mutant 486/486 |
| | A3c suite | 25 steps OFFLINE PASS, 1m58.6s |
| | A4 / A5 | step 24 control + M1–M6 each on its own wire; step 25 26 signatures, 313×11 = production, pin 291, M1–M5 |
| | A6 / A7 | contract v1 at POST; wheel = 3 package files, imports with writers and `core` unreachable |
| `4ed5671` | C2 `compute_gamma_core` | structure PASS; mutants 7/7; error paths identical; golden replay `7b91d1a` vs C2 486/486 `81f5508d…`; core mutant 477/486; purity 30/35; suite 25 PASS |
| `50bef37` | C3 `derive_atm_iv` | structure PASS; mutants 7/7; writer replay 486 + 9 error inputs identical `946dd84c…`; avg mutant 486/486; step 25 ATM IV 313×5 = production; purity 38/44; suite 25 PASS |
| `a0b6115` | C4 pin path | structure PASS; mutants 9/9; 1,577 cases before = after; cores = wrappers; mutants 182 / 5 / 258; step 25 ladder + carry + fail-open; purity 41/48; suite 25 PASS |
| `e0fb11d` | C5 contract v2 | at POST; suite 25 PASS |
| `02a06ec` | C6 register live `v_gex_strike_pin_zone`; contract v2.1 | body reproduces 3523 / `89c9ac6aef9eb332ddd28f9062d0e21e`; mutant differs; GitHub = POST |
| `4a1d8e1` | C7 register live `v_gex_strike_accel_zone` | body reproduces 3547 / `87a0691ef33ef5e08cbf315fd6511064`; mutant differs; GitHub = POST |
| deploy | DEP-1 (10-26 17:06) | `~/meridian-cc` at `4a1d8e1` clean; `~/meridian-engine` at `7b91d1a` clean; suite on tip 25 steps OFFLINE PASS |
| deploy | DEP-2 (17:08) | origin/main `7b91d1a` → `4a1d8e1`, fast-forward verified first |
| deploy | DEP-3 (17:09) | read-only check: new code recomputes the 15:40 cycle = the pre-deploy cron rows — NIFTY 18/18 fields, 144 strikes, ATM IV OK; SENSEX 18/18, 182 strikes, ATM IV OK; VIX 17.15 vs 17.16 (not compared); mutant FAIL on `net_gex` + `gss_rows` |
| deploy | DEP-4 (17:11–17:12) | four-way PASS (§1) |
| **live** | **10-27 08:30 cycle — first unattended run of `4a1d8e1`** | 33 ledger rows 08:30–08:33, all `exit 0`; `compute_gamma_metrics_local.py` NIFTY/SENSEX SUCCESS (08:30:28 / :35), `compute_volatility_metrics_local.py` SUCCESS (08:30:42 / :50), `write_gex_cycle_history_local.py` SUCCESS (08:30:59 / 08:31:20), runner SUCCESS; gamma rows written 12–17 s after ts (NIFTY SHORT_GAMMA −297,599.7, SENSEX SHORT_GAMMA −198,526.2), vol rows 28–34 s (ATM 22750 / 27.05; 73600 / 21.99); `gex_cycle_history` PRE_TICK, `NULL / NULL`, `null input: held_for_cycles` (as designed) |
| **live** | **10-27 09:10–09:30 pin path** (first production run of `derive_core` / `held_for_cycles_next` / `trading_days_between`) | carry-forward in session: NIFTY 22500 held 1 → 2, reset to 1 on 23000 at 09:30; SENSEX 72500 1 → 2, reset to 1 on 75000; across sessions: first OPEN row looked back past PRE_TICK / FROZEN to 10-26 15:40 (leader differed on both → 1); ladder SHIFTING at held 1–2, reason NULL (10-26 NIFTY held 3 also SHIFTING → stable_held_for > 3); PRE_TICK / FROZEN rows NULL held with reason; conviction non-NULL every row (NIFTY expiry day, T = 0 → boost at floor); writers 14/14/14 runs + runner 7, **0 non-zero** → **rollback not needed** |
| — | 10-27 08:20 refresh / 09:09 probe | refresh: operator-reported `DHAN TOKEN REFRESH SUCCESS`; probe `[PROBE] 2026-10-27 09:09 IST` — Dhan option chain (expiry list) OK, Dhan LTP OK, Dhan intraday OK, Kite token (profile) OK, Kite user verified; NIFTY pre-open 22702.90 vs 10-26 close 22753.20 (information only) → **PASS** |
| — | **board in-session reads 10-27 10:19–10:22 IST** (bundle `index-BFOk56iL.js` = S100-S `f964e40`) | **S100-N PASS both symbols**: Context SPOT change = Board — NIFTY −9.1 (−0.04 %) both (22,744.1 − prev 22,753.2 = −9.1); SENSEX −254.69 (−0.35 %) vs −254.7 (−0.35 %). **S100-Q.1 PASS both**: NIFTY sentence "amplifying pocket (local γ) … Net gamma is long, 0.06 of gross" = NET Γ tile +8.4L Cr long γ 0.06 (nearest strike 22,750 −1.1L, amplifying); SENSEX "dampening pocket (local γ) … long, 0.04" = tile +63,839 Cr long γ 0.04. **S100-M (a) fleet PASS, OVERALL FAIL as expected-stated**: fleet 14/14 all current, OVERALL **DEGRADED** — cause read from the bundle: token tile is green only if token age < 30 **minutes** (`Tf` = ms / 6e4), token 2.5 h old → amber → OVERALL amber (§5 finding). |
| — | **board close reads 10-27 15:48–15:50 IST** (in place of 10-26) | **S100-S strip PASS both**: `Closed · showing the 27 Oct session · next open 28 Oct`. **S100-R PASS in full, both**: `SPOT · CLOSE` — NIFTY 22,749.8 (−3.5, −0.02 %), SENSEX 73,598.7 (−8.1, −0.01 %) = the 15:40 chain spot (operator SQL on `gamma_metrics`, ts 10:10:05 UTC: NIFTY 22749.75, SENSEX 73598.67; the 15:35 rows identical). **FUT·BASIS sub-line**: NIFTY `vs spot 22,760.8 @ 15:40` (close 22,749.75, Δ 11.05), SENSEX `vs spot 73,556.3 @ 15:40` (close 73,598.67, Δ 42.37) → the futures row still carries a non-close spot at 15:40 = **TD-S100-NEW-1 re-measured on both symbols** (S100 Part C predicted this). NIFTY expiry-day close state: §5 finding. |
| — | **R19 read 10-27 17:52 IST** (open) | `eod.log` last block: candidates 10-23 (1,375 / 1,381, 99.57 %) back to 10-09, `Selected rebuild trade date: 2026-10-23`, `rows upserted 1375`, `gap dates filled : none` — builder correct on its input. SQL: universe 1,381; `equity_eod` has **0 rows for 10-26 and 10-27** (`expected_rows` NULL), so no breadth rows. 10-27 is outside today's window by design (T−1). 10-26 is inside it: either Dhan publish lag (S65 settled, 1–3 days, self-heals) or today's sweep did not run / failed — log lines carry no date. Discriminating read (17:54 IST): `eod.log` mtime 2026-10-27 11:35:42 (box clock, UTC = 17:05 IST, after the 16:10 cron); last `Date window: 2026-03-20 -> 2026-10-26`; last two runs `Candles upserted 4526 · Failures 0 · Status OK`, no `DH-901` → today's sweep ran clean over a window that includes 10-26, and Dhan returned no 10-26 candle → **Dhan publish lag (S65 class), not a fault. R19 builder PASS on its input; 10-26 / 10-27 breadth owed to the 10-28 run.** One earlier run in the log has `Failures 1 · PARTIAL_OK` on a `DH-905` (bad parameters, one security) — not a token failure. |
| — | **board pre-open read 10-28 09:09 IST** (first pre-open read of S100-S) | **S100-S pre-open strip PASS both**: `Pre-open · figures are from the pre-open chain until the first 1-min bar at 09:16`. **Expiry roll PASS (NIFTY)**: front leg `03 NOV · 4 DTE` (expired 27 OCT leg gone; the 10-27 post-close −1.00-of-gross state cleared by the 08:30 run); spot change vs the 10-27 close: NIFTY 22,665.5 −84.3 (= 22,665.5 − 22,749.8), SENSEX 73,175.8 −422.9 (= 73,175.8 − 73,598.7) → prev close = the S100-R close. FUT·BASIS pre-open: `futures from 09:30`, last row `27 OCT · vs spot 22,749.8 @ 16:00` (the 16:00 futures row carries the close, as S100 predicted). OPEN·GAP `no pre-open print` at 09:09. FLIP `carry unmeasurable` both. |
| — | 10-28 09:09 probe | `[PROBE] 2026-10-28 09:09 IST` — Dhan option chain OK, Dhan LTP OK, Dhan intraday OK, Kite token OK, Kite user verified; NIFTY pre-open 22678.00 vs 10-27 close 22749.75 (= the S100-R close) → **PASS** |
| — | 10-28 pin path across the NIFTY expiry roll — part 1 (rows to 09:15) | 10-27 last OPEN rows: leader 22750, held 7 → 8 → 9, STABLE (first STABLE seen; ladder reached it at held ≥ 7 on expiry day), conviction 3.67. 10-28 08:30–09:10: `expiry_date 2026-11-03`, leader 23000, `PRE_TICK`, held NULL, pin_state NULL; 09:15 `FROZEN` same. `dte = 6` = calendar days 10-28 → 11-03 (the column is calendar, the board's `4 sess` is sessions). Conviction non-NULL on pre-OPEN rows (0.4965–0.5651). First OPEN row owed (expected held 1: leader 23000 ≠ 10-27 last OPEN leader 22750). |
| — | live view checks + O1 + accel (10-26 04:48–10:16) | `v_max_pain_by_strike` = retrofit (4,028 / `3d0ed5cb…`); pin zone and accel zone matched no file → C6 / C7 |
| — | B1 10-26 08:20 refresh / 09:09 probe / `27c0e17` | refresh SUCCESS (expiry 10-27 08:20); probe all OK → **TD-S97-NEW-5 closes**; manual.json `489a135e…` confirmed |
| — | WCB (S99-H) 10-26 | morning skips `0 SKIPPED_NO_INPUT`, no Friday-ts row, first row 09:11 (pre-open ticks); closing rows ts 15:40:06 both symbols → **S99-H PASS in full**; confirms TD-S97-NEW-8, -9, -10 |
| — | P4 capture 10-26 | NIFTY dte-1 session banked (first run 10:15:06) |
| — | Part C (a) 10-26 | γ median lag 12.6 / 20.3 s; 0 later-date rows; 3 closing rows / symbol; runner 87/87; cycle wait 87 lines, 0 missing; 1 non-zero = 14:00 ENH-133 `57014` (ruled §4 item 6) |
| — | Part C (b) 10-26 | wsfeed started 03:40:01–03:40:03 UTC by its timer, no restarts, `sudo` alert journal empty → **TD-S80-NEW-17 closes**; `dhan_token_probe_log` 3 rows all 200 (07:50 IST pull + 2 probes; Supabase token written 07:50 by `local_token_refresh`, inferred = BS-1 manual refresh) |
| — | still owed | R19 re-read 10-28 after 16:10 IST: `breadth_indicators_daily` gains 10-26 and 10-27 (rows = universe tickers with an `equity_eod` close that date, ≥ 95 %), `gap dates filled : none` |

## 3. Next (carried to S102)

1. S101 doc-close (Doc Protocol v5) from this file — S102 Part A.
2. 10-28 pin path part 2: first OPEN NIFTY row after the expiry roll (expected held 1; leader 23000 ≠ 22750).
3. R19 re-read 10-28 after 16:10 IST (10-27 + gap-filled 10-26).

## 4. Rulings (S101)

1. Core split — YES (10-25 21:31 IST) → C2.
2. Deploy timing — Part C reads first on unchanged writers; deploy from 16:30 IST Monday. Done 10-26 17:08.
3. Board-core gaps — C3 (ATM IV), C4 (pin path), contract updated (C5); one commit per item, branch only.
4. File the §5 findings as TDs at the close.
5. O1 (10-26 10:10 IST): file a TD, commit the live pin-zone definition to `sql/`, correct contract §8 → C6; sibling → C7.
6. **R1 TDs (10-26 17:23 IST): close TD-S97-NEW-4, TD-S82-NEW-1, TD-S82-NEW-2** on the R1 evidence; the one non-zero
   runner exit (14:00, ENH-133 `57014`) is a different class and is **filed as a new TD**. Both at the doc-close.
7. **Schedule the 10-27 close reads, keep the Chrome tab open** (10-27 10:27 IST) — done 15:48; R19 scheduled 16:45.
8. **EOS (10-28 09:58 IST):** close S101 now; doc-close and carried reads move to S102.

**TDs closing on S101 evidence:** TD-S97-NEW-4, TD-S82-NEW-1, TD-S82-NEW-2 (ruled), TD-S97-NEW-5 (09:09 probe),
TD-S80-NEW-17 (wsfeed self-start); TD-S97-NEW-8/-9/-10 live-confirmed. TD-S100-NEW-1 stays OPEN, re-measured 10-27.

## 5. Findings to file (TDs, at the close)

- **ENH-133 writer `57014` statement timeout** (ruled new TD, §4 item 6; 10-26 14:00 NIFTY): `build_row` retries 57014
  three times and lost the cycle; `held_for_cycles` one low from 14:05; unrecoverable (ADR-030 D2). Diagnose which view read
  timed out (rank / concentration / max pain / pin-maxpain / walls / repriced flip) and apply ADR-021 A1 there.
- **Unregistered live change to `v_gex_strike_pin_zone` and `v_gex_strike_accel_zone`**: walk on
  `COALESCE(<pin|accel>.tau, 0.3)`, `tau_used` never NULL, LATERAL skip-scan over hard-coded `VALUES ('NIFTY'),('SENSEX')`.
  Most likely S80, DDL never registered (ADR-025 D2 class). Registered by C6 / C7. Follow-up: a standing md5 check of every
  live view against a registered list (O1 table as seed).
- **otm_oi_velocity is NULL in every production row** (0 / 313). Live defect.
- **fetch_recent_max_gamma_strikes and fetch_prior_gamma_metrics have no date bound**. Rule: by design or defect.
- **Volatility writer `dte` uses the wall clock** — TD-NEW-4 class.
- **Gamma math drift**: `backfill_gamma_metrics_to_main.py`, `measure_rate_sensitivity.py`, `replay/replay_compute_gamma_metrics.py`;
  volatility: `replay/replay_compute_volatility_metrics.py`. These can now import `merdian_compute`.
- **`.gitignore:107 _*.py` matches every `__init__.py`**.
- **Interpreter**: ≥ 3.12 compensated `sum()` moves `net_gex` / concentration in the last bits.
- **Retail gaps still open** (contract §9).
- **Superseded view files in `sql/`**: `v_max_pain_by_strike` (2 of 3), pin zone (3 older), accel zone (3 older).
- **Security: port 22 open to 0.0.0.0/0** on `i-0878c118835386ec2` — narrow; operator action; tracker §2.2 BS.
- **Local trailed `main`**: before the S101 pull, Local was at `b29f320` (S100). Make "Local HEAD" an explicit four-way line.
- **WCB publishes from pre-open ticks** (first row 09:11): design question for a ruling, not a defect.
- **Unprivileged journal reads look clean**: every runbook / prompt alert read must use `sudo journalctl`.
- **Health OVERALL reads DEGRADED all session on a healthy fleet** (10-27 10:20, fleet 14/14): the token tile is green only
  for token age < 30 min (`index-BFOk56iL.js`: `Tf(ts) = (now − ts) / 6e4`, green iff `http_status == 200 && age < 30`);
  the token refreshes once a day, so OVERALL is amber from ~30 min after the refresh until the next one. S100-M (a)'s
  "OVERALL green unless a tracked writer is stale" cannot hold. Fix in meridian-connect (threshold on the token's validity
  window, e.g. < 24 h, or expiry-based); board change needs the operator's yes.
- **Context IV SKEW blank for NIFTY on expiry day** (10-27 10:20, front leg 0 DTE): card shows `—` after > 10 s; SENSEX
  (2 DTE) shows `+2.0 vol pts @ K98 72,000 · front leg · from view`. Likely `leg_skew_98` has no 0-DTE front row, or the
  card does not fall back to the next leg. S100-P class; read the view on the next NIFTY expiry before ruling.
- **Home first paint** read `prev close missing` / PIN `no run` / OI `no max pain` before data loaded (10:19), then filled —
  TD-S100-NEW-2 (loading rendered as values), extends it to Home; no new TD.
- **NIFTY board after the close on expiry day shows the expired leg's last-cycle gamma** (10-27 15:49): NET Γ
  **−2,007.6L Cr, short γ, −1.00 of gross** (in session 10:19: +8.4L, +0.06); PIN 22,750 **99.0 % of gross**, lead 98.5 pts;
  corridor `22,750–22,750 · 0.00 % wide · below put wall`; IV `—`; priced move `no run`; sentence "Net gamma is short,
  -1.00 of gross". The 15:40 run on the expiring leg is at T ≈ 0, so ATM gamma dominates (22,750 −1,987.8L of the total)
  — a mathematically expected blow-up, but the board presents it as the day's closing structure, and it stays up overnight
  until the next pre-open. Rule: after the expiry-day close, does the board roll to the next leg (or label the expired-leg
  state)? Check the stored 15:40 rows before ruling. Not caused by S101 (gamma math byte-identical, DEP-3).
- **`eod.log` lines carry no timestamps**: the builder / ingest summaries cannot be tied to a run date from the log, so
  "did today's run happen" needs the file mtime (R19 read 10-27). Add a dated header line per run.
- **One ticker returns `DH-905` (bad parameters) on the EOD historical call**: a run in `eod.log` ends `PARTIAL_OK`,
  `Failures 1`. Identify the security id from the failure sample; likely a stale or malformed `dhan_scrip_map` row.

## 6. Assumption Register §D.55 (corrections to my own work, S101)

1. A1 script written under `/home/claude` while the clone was under `/root`.
2. Purity analyser first pass: `except … as` names, local imports flagged wholesale, calendar module judged by package name.
3. Extractor first dry-run carried a `# ---` banner into the package.
4. A replay sha256 measured on 3.13 written into doc / commit drafts as if absolute; interpreter-dependent.
5. Step 25 timestamp parser read offset digits as fraction; first pin-risk exclusion rule assumed an in-day window.
6. Rehearsal stopped before `git add`; the `_*.py` ignore rule first met on the box (B6).
7. B4 `grep -i fail` matched a pass line.
8. **The purity map committed in `11f2cbe` could not run on its own tree**; fixed in C2.
9. Step 25 C4 expected value written from intuition; M9 first "caught" for the stale error — re-checked.
10. C3 test tree first built on `11f2cbe` instead of on C2.
11. A C4 mutant did not parse; a C4 mutant label misdescribed its edit.
12. `rm -rf scratch` on my clone deleted tracked files; restored. Clone only.
13. A multi-destination `cp` left `s101_replace.py` out of the C3 bundle directory.
14. **Pin-zone marker check (04:53 IST) declared the s69 file live.** Rule taken: identify a live view by full
    `pg_get_viewdef` md5 against a file that reproduces it, never by markers.
15. C6's first rehearsal: the mutant's anchor also matched the header comment; the NOT-APPLIED guard failed it as designed.
16. WCB first-row expectation "≥ 09:15" written from assumption, not from the writer's guard.
17. **The deploy check's first box run failed `ModuleNotFoundError`** (script dir, not cwd, on `sys.path`); fixed by
    `PYTHONPATH=$PWD`; the crashed "mutant exit=1" was flagged as not a mutant result.
18. Local's four-way leg was first run from `Downloads`; the Topology names `C:\GammaEnginePython\`.
19. **The wsfeed alert read was given without `sudo`**, so its `-- No entries --` could not fail. Re-read with `sudo`.
20. The probe-log query named a `created_at` column the table does not have (`ts`).
21. The first wsfeed start read used `head -6`, which showed only the 03:00/03:05 retry ticks.
22. 10-27 pin read: expected `gate = OPEN` from the first cycle ≥ 09:15; the 09:15 cycle is FROZEN on both symbols (book not
    yet moved — existing session-gate behaviour, untouched by S101); OPEN from 09:20.
23. 10-27 board read: opened the board in the built-in browser (its own profile, no sign-in) when the operator's signed-in
    Chrome was the intended browser; switched to Chrome.
24. **R19 PASS line expected `selected_rebuild_trade_date: 2026-10-27` on 10-27**; the ingest window is T−1
    (`compute_date_window()`, S65 settled), so a same-day EOD date can never be built — I read the builder but not the
    ingest's window before writing the expected value. The grep also could not date its own lines.
25. 10-28 pin SQL PASS line: said `dte` = 4 trading sessions and listed them wrongly (10-28, 10-29, 10-30, 11-03 —
    dropped 11-02, kept today); the column is calendar days (6). Expected value not computed from the writer before stating it.
