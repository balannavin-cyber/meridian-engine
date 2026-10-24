# S99 reconciliation pass 2 — every open TD gets one home

Draft 2026-10-24 IST. **RULED 2026-10-24 (S99-C … S99-E, `rulings_s99.md`): Q1–Q6 adopted as mapped; Q7 option (a); Q8 rotations right after B1; S99-G: the PARK-ICT stream ranks after agentic.** **The five one-read items were read 2026-10-24 06:21–06:28 IST: 3 CLOSE (TD-S72-NEW-5, TD-S59-NEW-1, TD-S89-NEW-1), 2 KEEP under R22 (TD-S81-NEW-7, TD-S41-NEW-1). Final: CLOSE 46, CLOSE on Mon PASS 3, KEEP 154.** Not yet registered — the registers change in the merge commit (§4). Pass 1 (`claude/s98_reconciliation_table.md`, adopted as S98-A) covered the S97 TDs, the parity evaluation and the carried list. This pass covers every other open TD in `docs/registers/tech_debt.md`, so that after the ruling each open item lives in exactly one place: the tracker's single list (§2.2), a park with a named trigger, or closed.

**Sources read:** `tech_debt.md` at `2edd25f` (Local copy, LF blob `7fb246b32383d5f59993eaba53c74dd789cf10ed` = repo); `git log` since 2026-04-01 (669 lines, ends `2edd25f`); `claude/s98_reconciliation_table.md`; `claude/rulings_s98.md`; tracker `agentic_layer_roadmap_S90.md` v2.14; ADR-019 (port-not-retire); the register's own status-change footers (S55–S70 update log :7605–:7761, S90/S91 :7760, S95–S97 :284–:394).

**Count, and a correction (Rule 0).** The Active section holds **441 unique entries**; **364** read open — neither the heading nor the Status row carries CLOSED / RESOLVED / FIXED / SUPERSEDED / WITHDRAWN. My earlier S99 figure (247 open of 296) parsed only entries with a table Status row and missed the older formats; **364 is the figure**. Of the 364, **51 are already closed in substance** (a footer, a commit or a status row says so) and only the heading was never updated — that is why the open count looked so large.

Dispositions: **CLOSE** (evidence named) · **CLOSE on Mon PASS** (S98-B live read) · **CLOSE? (one read)** · **DUP** (duplicate of the named item; one home) · **OBSOLETE** (the thing it is about is retired by ruling) · **PARK-ICT** (signal / ICT stream) · **PARK-HIST** (history and backfill) · **PARK** (other, trigger named) · **PARK-AGENTIC** (agentic MERIDIAN on hold, operator 2026-10-24) · **KEEP** (into §2.2, by band).

## 1. Result

| Disposition | n | What the ruling does |
|---|---:|---|
| **CLOSE** | 43 | line in the S99 status-change paragraph (v5 Rule 3, no heading or body edits) |
| **CLOSE on Mon PASS** | 3 | closes with the S98-B live read after 15:45 IST 2026-10-26 |
| **CLOSE? (one read)** | 5 | closes if one named read confirms; else KEEP |
| **DUP** | 37 | footer `duplicate of X`; X carries the work |
| **OBSOLETE** | 15 | footer `OBSOLETE — <ruling that retired it>` |
| **PARK-ICT** | 68 | footer `PARKED — signal/ICT stream`; trigger: operator reopens the stream |
| **PARK-HIST** | 22 | footer `PARKED — history`; trigger: a study needs that window |
| **PARK** | 10 | footer `PARKED — trigger <named>` |
| **PARK-AGENTIC** | 9 | footer `PARKED — agentic on hold`; tracker stages marked ON HOLD |
| **KEEP** | 152 | one row in tracker §2.2, in band order |
| **Total** | **364** | |

KEEP by band:

| Band | n |
|---|---:|
| B1 · Capture and ledger integrity (S98 order 1: R1→R2/R21, R3, R4) | 18 |
| BS · Security and access — retail prerequisite | 13 |
| B2 · Closing session (S98 order 2: R5, R6, R20) | 1 |
| B3 · Reads before any TD (S98 order 3: R7, R8, R10, R18, R36) | 15 |
| B4 · Small fixes (S98 order 4: R9, R19, R22–R24, R34/R35) | 39 |
| B5 · Wording batch, operator yes, with manual v0.4 (S98 order 5) | 5 |
| B6 · Pre-registered improvements (S98 order 6: R12, R13) | 2 |
| BR · Rebuild source and deploy reproducibility — retail prerequisite | 8 |
| BO · Ops and monitoring | 10 |
| BD · Docs and process hygiene (one batch session) | 41 |

## 2. Rulings asked (by class; exceptions listed)

**Q1 — Close the 43 with evidence, the 3 on Monday's PASS, and the 5 after one read each.** *Recommended: yes.* Evidence is in the Note column of §3. The five reads: TD-S81-NEW-7 / TD-S41-NEW-1 (`trading_calendar` 2026-05-28 row exists, closed), TD-S72-NEW-5 (one feed-log read for the instrument-loader floor), TD-S59-NEW-1 (one directional day's breadth vs VRD A/D), TD-S89-NEW-1 (10-20: zero chain rows). **Judgment calls inside Q1, flagged:** TD-S80-NEW-11 and TD-S73-NEW-3 close because TD-S94-NEW-4 measured the retention directly; TD-S91-NEW-11 closes because rule 24 has held S92–S99; TD-080 closes into TD-S81-NEW-11 (the remaining 500/429 behaviour).

**Q2 — The 37 duplicates.** *Recommended: yes, as mapped.* Largest groups: `merdian_reference.json` version control (6 → TD-S76-NEW-16 / TD-S71-NEW-1), R4 Kite/Dhan token family (4 → TD-S97-NEW-5/-6), R5 close print (4), the PowerShell BOM / encoding rule (4 → TD-S80-NEW-4), R11 board consistency (3), R9 ICT writer (2), R41 one-cycle lag (2, re-measured Monday).

**Q3 — The 15 obsolete.** *Recommended: yes.* Grounds: Windows host retired (S70, "MERIDIAN is 100 % AWS") — 6; parity CLOSED (ADR-025 Amendment D) — 3; Breeze unused (TD-S90-NEW-10) — 2; superseded by P2/P5/P7 — 1; historical one-offs — 3.

**Q4 — The 68 signal / ICT items: park as one stream.** *Recommended: park, trigger "operator reopens the signal stream".* ADR-019 forbids retiring on an experiment verdict, so these are not marked obsolete. The signal path is dead (System Map §S76.A) and MERIDIAN has never placed an order (S87), so nothing parked here routes money today. R9 still untracks the ICT writer from the Health page. **Exception — ten S1s go into this park:** TD-S77-NEW-1, -10, -11; TD-S76-NEW-3, -4, -5, -7, -19, -20; TD-S74-NEW-2. Each is S1 *for the signal path*; confirm they may park with it.

**Q5 — The 22 history / backfill items: park.** *Recommended: park, trigger "a study needs that window".* Exception: **TD-S76-NEW-1 (S1)** — ~58 sessions of premium data lost with the Windows bridge; nothing recovers it now, so parking changes no outcome.

**Q6 — The 10 other parks.** *Recommended: yes, triggers as written.* Exception: **TD-S74-NEW-1 (S1)** is a pointer to a 59-finding audit; the trigger is "file each finding when its file is touched".

**Q7 — Agentic MERIDIAN on hold: which stages.** The 9 TDs here are the RAG items (TD-S85-NEW-1..3), the R1.6 replay harness (TD-S91-NEW-8..10), agent permissions and the no-tools arm (TD-S87-NEW-4, TD-S86-NEW-6), and the depth-aware health model the contract runner absorbs (TD-S82-NEW-3). The tracker needs one line on scope:
- **(a) Recommended:** **Stages 3, 3b, 4, 5, 6 ON HOLD.** Stage 0–2 items already running live stay running as maintenance (R0.3 provenance, R0.4 ENH-133, R1.2 contract runner in shadow, R1.5 SLO views, R2.1 golden days, R2.7 tick freeze) — a break in them is a TD in §2.2 — but **no new Stage 0–2 build**. §2.1 (P4 accruing, P8 gated) is not agentic and continues.
- (b) Everything in §3 ON HOLD, including the running Stage 0–2 jobs (would mean switching off R1.2's cron and the tick freeze).
- (c) Only Stages 5–6 (agents and the advisor) ON HOLD.

**Q8 — KEEP order for §2.2.** *Recommended:* B1 → **BS's two rotations** (TD-S81-NEW-1 Dhan token review, TD-S71-NEW-11 `.env` credentials — operator actions, no code) → B2 → B3 → B4 → B5 → B6, then BR and the rest of BS **before any retail build**, with BO and BD as one session each when the market is shut. **Conflict, stated:** S98-A's work order has no security band; putting the two S1 rotations second moves them ahead of R5. Alternative: leave them after B6 (no rotation is known to be urgent beyond the S81 exposure window).

**Retail prerequisites (for tracker §2.3):** R1–R5, R11 (from pass 1), every BS row, every BR row. Tagged `retail` in §3.

## 3. The table

### 3.1 CLOSE on Mon PASS (3)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S97-NEW-4 (:104) | S1 | a total ingest outage reads as a healthy day: the orchestrator re-runs the last existing run and logs SUCCE… | R1/R41 — S98-B deployed 2edd25f; close on Mon 10-26 live PASS |
| TD-S82-NEW-1 (:1460) | S2 | the shadow runner's cron hour range ends before the option-chain ingest's, and before its own docstring: th… | = R41/S98-B: runner closing cycles 15:30/35/40 added (crontab line 70); close on Mon PASS |
| TD-S82-NEW-2 (:1482) | S2 | the shadow runner selects the previous chain cycle, every fire, by a sub-second margin: every derived row i… | = R41/S98-B: runner waits for its own cycle; close on Mon PASS |

### 3.2 CLOSE (43)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S96-NEW-1 (:305) | S3 | the L7/L8 tile captions say "dealer", and the dealer side is regime-dependent | CLOSED in S97 footer (:286, S97-A, live 04fcd05); header not updated |
| TD-S96-NEW-4 (:338) | S3 | after 15:15 the DEX pair and the Δ pair read different clocks | RECORDED, no change (S97-C footer :290) — nothing owed |
| TD-S95-NEW-2 (:371) | S3 | `trading_calendar` holds no rows for past closed days, so a closed day before the S90 seeder change reads a… | CLOSED S97-E (footer :293) |
| TD-S94-NEW-4 (:430) | S2 | P4's forward accrual depends on chain rows still existing at scoring time, and their retention was not checked | X1 — measured intact 10-23 04:51 IST (no pruning since 08-24); P4 §3 binds future changes |
| TD-S93-NEW-2 (:452) | S3 | `.gitignore:43 *.csv` silently excludes the DEX expected table, so the offline recompute's record is local-… | RESOLVED by ruling S95-F (footer :382) |
| TD-S93-NEW-3 (:463) | S3 | P1 precondition §6.6 rests on an operator-reported editor message, with no artefact in the repo | outcome recorded in p1/README + result doc (status row) — nothing owed |
| TD-S92-NEW-5 (:507) | S3 | `trading_calendar` has no row for 2026-10-02, a holiday that `trading_calendar.json` lists | closed by S96-J backfill; confirmed S98-C 06:33 IST |
| TD-S91-NEW-13 (:536) | S2 | `validate_compute_contracts.py` will send ~168 Telegram messages on the next weekday holiday, and that is 2… | CLOSED S97 footer (:297, 10-20 log 84/84 holiday gate) |
| TD-S91-NEW-14 (:552) | S2 | `validate_compute_contracts.py:170` announces a cycle skip that never happens | FIXED 0965755 (status row) |
| TD-S91-NEW-15 (:565) | S2 | `SKIPPED_NO_INPUT` exits 1, so 12 orchestrator cycles are marked failed every trading day by construction | basis site verified 12/12 exit 0 (S92-B, e0b9d03); S98-E.1 keeps SKIPPED_NO_INPUT semantics |
| TD-S91-NEW-1 (:618) | S2 | the ENH-133 writer and reconciler crash on 1/2/4/5-digit microsecond fractions, and the lost cycles are unr… | VERIFIED 2026-10-09 78/78, 77/77 (status row) |
| TD-S91-NEW-7 (:707) | S2 | the offline fixture suite OOM-killed the box during pre-open and Session Manager became unreachable | FIX VERIFIED 2026-10-07, rule 23 codified |
| TD-S91-NEW-11 (:759) | S3 | two Claude Code sessions worked the same tree at once, and BOTH were rooted in the engine tree | ruled S91-B = CLAUDE.md rule 24; compliance held S92–S99 |
| TD-S90-NEW-2 (:822) | S2 | the deployed Marketview bundle is built from commits that exist only on the box | CLOSED 2026-10-07 (S90 footer :7760) |
| TD-S90-NEW-11 (:912) | S3 | two S90-H backup tables to drop after a clean week | CLOSED S97-L (footer :294) |
| TD-S86-NEW-9 (:1208) | S2 | `capture_s84.md` §2.6's ≥ 3×SE precondition does not say whether it gates the gamma reading or only the off… | RULED 2026-10-03 (fb92d63) |
| TD-S80-NEW-5 (:1946) | S2 | ADR-025 was accepted and committed alone, so Rule 11.4's single-commit closure did not happen — in the sess… | closed by the S80 doc-close (status row) |
| TD-S80-NEW-11 (:2024) | S3 | `option_chain_snapshots` retention is 18 days, not the ~11 carried in the register | retention superseded: TD-S94-NEW-4 measured no pruning since 08-24 |
| TD-S80-NEW-13 (:2060) | S3 | `CURRENT.md`'s S79 Ledger describes a follow-on commit as local-only and unpushed; its content is in `main` | closed by the S80 CURRENT.md rewrite (status row) |
| TD-S79-NEW-13 (:2370) | S3 | two views shipped this session each emit a "notable strike" and neither comment distinguishes it from the o… | COMMENT ON VIEW names the scalars apart (dc2e6b5, S81) |
| TD-S73-NEW-11 (:3478) | S3 | the Decision Index carries four stacked stale footers, none citing the session the file actually records | RESOLVED S73 (status row) |
| TD-S73-NEW-3 (:3523) | S3 | `option_chain_snapshots` retention horizon is misread as ingest failure; second instance of the TD-S72-NEW-… | retention misread class — superseded by TD-S94-NEW-4 measurement |
| TD-S70-NEW-7 (:4108) | S3 | the generated `merdian_ict_htf_zones.pine` is tracked in git and collides on every pull where both hosts ha… | untracked by fdc1ad6 (2026-09-05) |
| TD-S69-NEW-4 (:4189) | S2 | Local↔box `generate_pine_overlay.py` divergence: the box runs an older generator that emits 139 zones (stal… | CLOSED S70 75de1bb (footer :7717) |
| TD-S69-NEW-8 (:4250) | S2 | verify the widened daily OB/FVG lookback actually accumulates, and that the TD-070 dedup path holds (`a4bdb… | CLOSED S70 (footer :7733) |
| TD-S66-NEW-5 (:4313) | S2 | `equity_eod` frontier stuck at 07-06 even for tickers the Dhan API serves through 07-08 (recent-day writes… | REFRAMED NOT A BUG (S67); residual carried by TD-S90-NEW-14 |
| TD-S57-NEW-1 (:4550) | S2 | enable/cut over the S56-built `systemd` units onto MALPHA (ADR-018 D1) | CLOSED-VERIFIED S58 close (footer :7675) |
| TD-S57-NEW-2 (:4566) | S2 | breadth/divergence readers have no recency floor; a dead feed reads as "working" (ADR-018 D2) | CLOSED-VERIFIED S58 close (footer :7675, f922524) |
| TD-S55-NEW-1 (:4582) | S2 | volatility compute read-path queried dead table compute_volatility_metrics (S48 fixed the write, left the r… | filed+closed S55 (footer :7667) |
| TD-S54-NEW-1 (:4595) | S1 | SENSEX compute (volatility/gamma/market_state) silently under-writes ~½ of cycles | closed S55 (1889604; footer :7667) |
| TD-S54-NEW-3 (:4626) | S2 | postmarket 16:00 IST capture (capture_postmarket_1600.py) failing daily | closed S55 (5b92433; footer :7667) |
| TD-S54-NEW-4 (:4641) | S3 | preflight false-green: V18A-03 checks calendar-row-exists but not open_time IS NOT NULL | closed S55 (c2910e8 + eb052d0; footer :7667) |
| TD-S53-NEW-6 (:4671) | S2 | futures capture script SyntaxError (Windows-path backslash in f-string) keeps futures dark on AWS | parse-fixed S55 (66f8252), contract resolution S56 (8eae351) |
| TD-S48-NEW-1 (:4686) | S2 | Breadth table `market_breadth_intraday` stale 4h+ despite orchestrator OK | CLOSED-DECISION S57 (footer :7672) |
| TD-S41-NEW-2 (:4770) | S3 (re-rated) | Dhan token refresh suppressed across NSE holidays; cross-host single-point-of-failure where Local is sole r… | downgraded S55: AWS-primary refresh confirmed; residual staleness monitor → R4 |
| TD-S37-01 (:4981) | S3 | Hardcoded τ_pin = τ_accel = 0.3 in ENH-81 SQL views; formalize as `merdian_parameters` lookup when ENH-83 b… | closed S40 (6d07d24: view-tau runtime get_parameter) |
| TD-S36-NEW-4 (:5076) | S3 | `script_execution_log.duration_ms` is int4; orphan-recovery durations exceeding ~24 days overflow on PG write | resolved S55 (duration_ms bigint; footer :7667) |
| TD-NEW-H (:5403) | S2 | `backfill_volatility_snapshots.py` NULL `expiry_date` schema violation produces 7 daily pre-market CRASHes | superseded S55 (footer :7667) |
| TD-081 (:5654) | S2 | No data-freshness guard between primary ingestion and derived layers — signal builder produces signals on s… | closed downstream at S58 close (footer :7675) |
| TD-080 (:5671) | S2 | AWS Dhan token refresh failure mode (cross-script Dhan 401 outage on 2026-05-07; reframed Session 25; PROMO… | S1 RECURRING → ENH-99 capture-layer resilience SHIPPED S36 (e318ec2); residual 429 behaviour = TD-S81-NEW-11 |
| TD-019 (:6102) | — | `hist_spot_bars_5m` pipeline stale since 2026-04-15; blocks forward research validation | closed S9/S10 (e36a9ef "TD-019 docs -- closure") |
| TD-030 (:6336) | S2 | `build_ict_htf_zones.py` doesn't re-evaluate breach on existing active zones | closed S11 (9261ee2 "TD-030/031 closed") |
| TD-031 (:6353) | S2 | D BEAR_OB / D BEAR_FVG detection underactive in `build_ict_htf_zones.py` | closed S11 (9261ee2) |

### 3.3 CLOSE? (one read) (5)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S89-NEW-1 (:979) | S2 | the ingest ran 83 cycles on a closed day and recorded the previous session's last spot every time, producin… | **CLOSE (read 2026-10-24 IST):** 10-20 (Dussehra) IST day: option_chain_snapshots 0, gex_strike_snapshots 0, gamma_metrics 0 |
| TD-S81-NEW-7 (:1637) | S2 | the `trading_calendar` TABLE is missing the 2026-05-28 Bakri Id closure row that `trading_calendar.json` ca… | **KEEP → R22 (read 2026-10-24 IST):** 2026-05-28 has no trading_calendar row (read 2026-10-24); also missing 01-15, 01-26, 03-03; closed rows labelled "Normal trading day" 06-26, 09-14, 11-24; 03-31 and 04-14 share one name — one calendar-repair item under R22 (operator SQL) |
| TD-S72-NEW-5 (:3711) | S1 | the instrument loader failed open: an NFO timeout aborted the *breadth* load and the feed reported "Feed li… | **CLOSE (read 2026-10-24 IST):** ws_feed logs 10-16→10-23: every start EQ=1312/1313, 2131–2132 subscribed, no 3-instrument start; 10-15 and 10-19 = preflight token FAIL (R4), loader never ran |
| TD-S59-NEW-1 (:4482) | S1 | breadth read BULLISH 882/428 on a 0.37-A/D down day; root cause = frozen `equity_intraday_last` (missing AW… | **CLOSE (read 2026-10-24 IST):** cron line 22 `35 3 * * 1-5` present; equity_intraday_last newest 2026-10-23 03:35:08 UTC, 1312/1385 refreshed (= feed match) |
| TD-S41-NEW-1 (:4755) | S3 | `trading_calendar` table lacks NSE holiday pre-population; Bakri Id 2026-05-28 had no row at all | **KEEP → R22 (read 2026-10-24 IST):** same read: 05-28 absent → with TD-S81-NEW-7 under R22 |

### 3.4 DUP (37)

| TD | Sev | Title (register) | Duplicate of | Note |
|---|---|---|---|---|
| TD-S91-NEW-16 (:580) | S2 | the unidentified EOD cursor writer struck again, and this time it carried an expired Dhan token | TD-S90-NEW-14 | same unidentified EOD cursor writer |
| TD-S91-NEW-18 (:605) | S3 | `market_spot_session_markers` reads `MISSING_CLOSE_1530` every day, and the cause is structural | R5 | MISSING_CLOSE_1530 structural — the close print (R5) reads the 15:40 chain spot |
| TD-S91-NEW-3 (:649) | S2 | the Zerodha feed was down 09:10–09:36 IST on a token that had verified 50 minutes earlier, and the mechanis… | R4 | X1 — Zerodha feed down, cause unidentified → R4 probe |
| TD-S90-NEW-13 (:785) | S3 | SENSEX can settle after the 15:29 bar, and the live job reads only 15:29 | R5 | SENSEX settles after 15:29 → close print from the 15:40 chain (R5) |
| TD-S90-NEW-6 (:863) | S3 | the wall corridor can degenerate: put wall = call wall, put wall above spot | R11 | degenerate corridor |
| TD-S90-NEW-7 (:873) | S3 | one screen shows two runs: the signal stream and the board disagree on regime, and two ATM definitions coexist | R11 | two runs on one screen |
| TD-S89-NEW-2 (:962) | S2 | the ADR-016 parameter WRITE path does not exist: the ADR names a CLI that is absent, the register reads SHI… | TD-S90-NEW-8 | premise refuted (S90 footer); remaining half = TD-S90-NEW-8 |
| TD-S88-NEW-1 (:997) | S2 | the Marketview header computes its change against a close TWO SESSIONS old during every trading session, be… | R18 | header change vs a close two sessions old → R18 prev-close read |
| TD-S87-NEW-3 (:1026) | S3 | the engine `.gitignore` does not cover rotated logs, so `9` untracked `*.log.N[.gz]` files sit in `git stat… | TD-S83-NEW-6 | rotated logs not ignored |
| TD-S86-NEW-7 (:1175) | S3 | `merdian_reference.json` carries two version numbers that disagree: `_meta.version` reads v52 against a top… | TD-S76-NEW-16 | reference.json two version numbers |
| TD-S81-NEW-9 (:1671) | S3 | one client-side strike scalar renders under three different labels | R11 | one scalar, three labels |
| TD-S81-NEW-13 (:1735) | S3 | a crontab line runs `build_wcb_snapshot_local.py` with no symbol argument, every five minutes | TD-S97-NEW-8 | same stray WCB cron line (R21) |
| TD-S80-NEW-9 (:2006) | S3 | the ingest day starts at 08:30, 08:35 or 08:40 IST and loses one or two cycles, and nothing records which | R41 | first-cycle loss 08:30–08:40 — S98-B wait; re-measure Mon |
| TD-S79-NEW-3 (:2189) | S2 | `sql/` is a superseded rebuild source: the migrations directory holds the pre-S72 pin/accel definition, and… | TD-S81-NEW-5 | sql/ superseded rebuild source |
| TD-S79-NEW-23 (:2547) | S3 | `merdian_reference.json` carries two change logs four sessions apart, and three `_meta` fields disagree wit… | TD-S76-NEW-16 | reference.json two change logs |
| TD-S78-NEW-8 (:2746) | S3 | `gex_strike_snapshots.ts` lags `created_at` by exactly one 5-minute cycle, so every GEX row is one cycle st… | R41 | gss ts one cycle behind created_at — same mechanism as R41; doc half stands; re-measure Mon |
| TD-S77-NEW-5 (:2822) | S3 | the documented commit-message recipe emits a BOM, and ways-of-working records that exact incantation as the… | TD-S80-NEW-4 | BOM recipe |
| TD-S77-NEW-14 (:2948) | S2 | `build_ict_htf_zones.py`'s invoker is still unresolved, and the `host` evidence the S76 search was scoped o… | R9 | build_ict_htf_zones invoker unresolved → R9 retire/untrack the ICT writer |
| TD-S75-NEW-3 (:3376) | S3 | `net_gex` carries no per-1%-move normalisation, so every Crore figure in every register and dashboard is a… | R26 | net_gex no per-1 % normalisation → R26 √τ / unit label |
| TD-S74-NEW-3 (:3421) | S1 | F-01: the futures basis is computed against spot up to 25 minutes stale, and the failure inverts | R5 | basis vs stale spot → R5 TD half (basis from the displayed spot) |
| TD-S74-NEW-5 (:3449) | S2 | F-13's remaining half: `close_1530` is unobtainable, so `capture_quality` can never reach `COMPLETE` | R5 | close_1530 unobtainable → R5 close print from the 15:40 chain |
| TD-S72-NEW-11 (:3804) | S3 | `Out-File -Encoding utf8` writes a BOM on Windows PowerShell 5.1, contradicting the documented git workflow | TD-S80-NEW-4 | Out-File BOM |
| TD-S71-NEW-2 (:3890) | S3 | `merdian_reference.json`'s canonical freshness header is three sessions stale while its body is current | TD-S76-NEW-16 | reference.json freshness header |
| TD-S71-NEW-10 (:4014) | S3 | "ADR-006 COMPLETE" is overstated: a production token script is still operator-invoked on Local Windows | R4 | token script on Local → R4 / TD-S97-NEW-6 |
| TD-S69-NEW-6 (:4220) | S3 | the operator's 06:00 Zerodha token-rotation routine has no disk guard, no backup, no quoting and no post-wr… | R4 | 06:00 Zerodha token routine → R4 |
| TD-S61-NEW-3 (:4395) | S4 | `merdian_reference.json` vestigial `_meta` header stale (v38/S55) alongside the live top-level header; resy… | TD-S76-NEW-16 | reference.json _meta header (resynced) |
| TD-S60-NEW-3 (:4436) | S2 | no shared holiday-gate helper (~30 entrypoints each roll their own `is_open` check); BUILT `core/trading_ca… | TD-S90-NEW-3 | helper built + orchestrator cut over; residual inline gates |
| TD-S54-NEW-2 (:4612) | S3 | Marketview headline SPOT reads coarse option_chain_snapshots.spot, lags the fresh 1-min spot table | R38 | headline SPOT source → R38 / R5 spot label work |
| TD-S41-NEW-3 (:4786) | S3 | `merdian_reference.json` schema drift surfaced via 3-strike SQL guess pattern on `script_execution_log` + `… | TD-S71-NEW-1 | reference.json schema coverage |
| TD-S37-03 (:5011) | S3 | Lovable anon-key brittleness: RLS misconfiguration produces silent empty datasets, not auth errors | TD-S81-NEW-16 | RLS misconfig gives silent empty sets |
| TD-NEW-D (:5374) | S2 | `ws_feed_zerodha.py` log timestamps `[HH:MM:SS IST]` are actually UTC (cosmetic) | TD-S91-NEW-4 | ws_feed UTC under IST label |
| TD-NEW-7 (:5486) | S1 | MALPHA → MERIDIAN AWS Zerodha token propagation is manual `sed`; should be Supabase `system_config` automat… | R4 | Kite token propagation (reclassified S71) → R4 / TD-S97-NEW-6 |
| TD-001 (:5888) | S3 | `pull_token_from_supabase.py` deployed but not in `merdian_reference.json` Block 3 inventory until v18D audit | TD-S71-NEW-1 | reference.json inventory |
| TD-010 (:6017) | S4 | PowerShell 5.1 `Get-Content` defaults to cp1252 when reading UTF-8 files | TD-S80-NEW-4 | PowerShell encoding pitfalls (one Local-workflow rule) |
| TD-017 (:6066) | S3 | `build_ict_htf_zones.py --timeframe H` has no scheduled invocation | R9 | HTF zones H no invocation → R9 |
| TD-023 (:6217) | S3 | Uninstrumented data producers (anti-pattern, audit pending) | TD-S77-NEW-8 | uninstrumented producers |
| TD-026 (:6268) | S4 | PowerShell scripts must be ASCII-only (encoding pitfall) | TD-S80-NEW-4 | PowerShell ASCII-only |

### 3.5 OBSOLETE (15)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S81-NEW-14 (:1752) | S2 | the ENH-99 retry budget has never been exercised, and the ADR-025 stage-2 gate is meant to be decided on ex… | ADR-025 stage-2 gate — parity CLOSED (Amendment D); retry telemetry is R1.4 (agentic Stage 1) |
| TD-S80-NEW-2 (:1892) | S2 | three claims in the Hedgewall parity spec are refuted by measurement, and the spec is what sequences the re… | parity spec claims — parity CLOSED (ADR-025 Amendment D) |
| TD-S79-NEW-10 (:2316) | S3 | the S74 and S79 containment figures disagree 2–5× and cannot be reconciled, because the S74 study left no r… | S74/S79 containment figures — neither quotable, no consumer |
| TD-S79-NEW-22 (:2527) | S2 | there is no acceptance criterion for "parity achieved": fourteen layers are specced, three are built, and n… | "parity achieved" criterion — answered by ADR-025 Amendment D |
| TD-S76-NEW-14 (:3168) | S3 | Deployment Topology §7.2 listed 20 Windows tasks against 23 measured, with `State: Ready` on 18 of them | Topology §7.2 Windows task table — Windows host retired (S70: 100% AWS) |
| TD-S46-NEW-1 (:4705) | S2 | Breeze backfill mechanism for futures/ATM/IV/VIX snapshots (addresses TD-NEW-14 30+ day gaps) | Breeze backfill mechanism — Breeze unused (TD-S90-NEW-10) |
| TD-S38-NEW-1 (:4936) | S4 | `MERDIAN_Intraday_Supervisor_Start` multi-trigger XML settings quirk blocks `Set-ScheduledTask` settings up… | Windows Task Scheduler quirk — host retired |
| TD-S37-02 (:4997) | S3 | §F1 dealer-vs-positioning GEX split scaffolded via `v_oi_prev_close_snapshots` view; writer integration def… | §F1 dealer-vs-positioning split — superseded by P2 (REGIME-DEPENDENT) + P5/P7 |
| TD-S36-NEW-2 (:5042) | S3 | `MERDIAN_Dhan_Token_Refresh` Task Scheduler task not instrumented to `script_execution_log` | Windows token task instrumentation — host retired |
| TD-S36-NEW-3 (:5059) | S4 | `dhan_token_probe_log` forward-only from 2026-05-10 (pre-S29 token incidents invisible) | pre-S29 token incidents invisible — historical |
| TD-S35-NEW-3 (:5111) | S4 | SENSEX symbology on ICICI Breeze API: `stock_code="BSESEN"` not `"SENSEX"`, undocumented in Breeze public docs | Breeze SENSEX symbology — Breeze unused |
| TD-062 (:5863) | S2 | Saturday LastRun timestamps on 5 Task Scheduler tasks despite DoW=62 (Mon-Fri) trigger — stuck-process accu… | Windows Task Scheduler Saturday runs — host retired |
| TD-004 (:5932) | S4 | `BFO_CONTRACT_05062025.csv` permanent ingestion failure (malformed Date column header) | BFO contract CSV 2025-06 — one-off historical file |
| TD-006 (:5966) | S3 | `run_market_tape_1m.py` disabled due to DhanError 401 / Windows ACCESS_VIOLATION | run_market_tape_1m disabled (Windows ACCESS_VIOLATION) — host retired |
| TD-016 (:6049) | S3 | Dhan TOTP scheduled task fails with `Invalid TOTP`; manual run with same seed succeeds | Dhan TOTP Windows task — host retired |

### 3.6 KEEP (152)

**B1 · Capture and ledger integrity (S98 order 1: R1→R2/R21, R3, R4)** (18)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S97-NEW-3 (:94) | S2 | the monitor cannot see a hung orchestrator run | R3 — hung-run probe |
| TD-S97-NEW-5 (:116) | S2 | a lapsed Dhan Data API subscription is visible only in `cron.log` | R4 — 08:25 pre-open probe (Dhan) |
| TD-S97-NEW-6 (:127) | S2 | the Zerodha feed was down on 3 of the last 6 trading days; the daily manual Kite refresh is a single point… | R4 — Kite token; automated-login is an operator ruling |
| TD-S97-NEW-8 (:151) | S3 | a crontab line runs `build_wcb_snapshot_local.py` without its symbol argument every 5 minutes | R21 — stray no-arg WCB cron line (with R2) |
| TD-S97-NEW-9 (:161) | S3 | WCB reports "Writing … COMPLETED" on a no-tick day and no row appears | R2 — WCB false COMPLETED |
| TD-S97-NEW-10 (:171) | S3 | WCB wrote placeholder rows on the 2026-10-20 holiday | R2 — WCB holiday placeholder rows |
| TD-S90-NEW-14 (:797) | S2 | an unidentified off-box writer advances the shared `breadth_ingest_state` `equity_eod` cursor between our runs | off-box writer of equity_eod cursor (absorbs TD-S91-NEW-16) |
| TD-S86-NEW-2 (:1096) | S2 | `runbook_update_dhan_token.md` is unexecutable: it names a variable no production script reads, its rotatio… | runbook_update_dhan_token unexecutable → with R4 |
| TD-S86-NEW-3 (:1112) | S3 | `check_dhan.py` reads `DHAN_ACCESS_TOKEN`, which no script in the repository writes, so it reports `AUTH FA… | check_dhan.py reads an unwritten var → with R4 |
| TD-S81-NEW-11 (:1702) | S2 | a Dhan HTTP 500 on the W1 call silently drops an entire ingest cycle on both symbols | Dhan 500 on W1 drops a whole cycle |
| TD-S81-NEW-12 (:1717) | S2 | the shadow runner invokes `compute_basis_context` for a full hour each morning before its only input exists… | basis context runs an hour before its input (S91-NEW-15 made it exit 0; cron hour still wrong) |
| TD-S81-NEW-20 (:1852) | S3 | `DhanClient` reads the Dhan token at construction, so a rotation mid-cycle leaves a running process holding… | DhanClient holds token from construction |
| TD-S77-NEW-8 (:2863) | S2 | writers hand-roll `script_execution_log` inserts and bypass `ExecutionLog`; how many is unmeasured, and the… | hand-rolled exec-log inserts (ledger trust, R1 family) |
| TD-S74-NEW-4 (:3435) | S1 | F-04: the S59 breadth defect can recur — the guard went into the health check, not into either consumer | breadth guard in health check, not consumers (S59 class) |
| TD-S41-NEW-5 (:4801) | S2 | WCB writer 17% NIFTY active-weight degradation (pagination cap) + regime threshold disagreement Python 60/4… | WCB 17 % NIFTY weight degradation + threshold disagreement → with R2 |
| TD-NEW-C (:5357) | S2 | `ws_feed_zerodha.py` silent on Supabase 500 / token errors (extends TD-NEW-9) | ws_feed silent on 500 / token errors → with R4 |
| TD-NEW-9 (:5463) | S2 | `ws_feed_zerodha.py` silent on success; no INFO heartbeat for nominal operation | ws_feed no heartbeat → with R4 |
| TD-082 (:5637) | S3 | `ingest_option_chain_local.py` contract miscalibration: backfill spike of 482 writes vs expected 50 logged… | ingest write-contract too permissive (R1 family: contract counts its own writes) |

**BS · Security and access — retail prerequisite** (13)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S92-NEW-4 (:496) | S3 | the S92 views grant `authenticated` more than `SELECT`, through default privileges | X1 — authenticated grants > SELECT · `retail` |
| TD-S90-NEW-8 (:883) | S2 | Marketview Settings is read-only since S90-E; the authenticated write route, `changed_by` and `config_versi… | Settings authenticated write route — retail prerequisite · `retail` |
| TD-S90-NEW-10 (:903) | S3 | unused Breeze credentials remain in `.env` | unused Breeze creds in .env — operator action · `retail` |
| TD-S89-NEW-5 (:922) | S2 | the Marketview bundle reached internet scanners while `:80` served it un-gated, so every anon-readable rela… | anon MAINTAIN on six base tables — retail prerequisite · `retail` |
| TD-S89-NEW-4 (:941) | S3 | TCP 80 is still open to the world at the security group; the `:80` hardening makes the port answer only red… | TCP 80 open at the SG · `retail` |
| TD-S84-NEW-5 (:1303) | S3 | `anon` holds `MAINTAIN` beyond `SELECT` on three objects created before the S81 default-privileges fix | anon MAINTAIN on three objects · `retail` |
| TD-S81-NEW-1 (:1540) | S1 | the live Dhan broker token was readable by anyone holding the public anon key, for an unbounded period; rot… | S1 — Dhan token was anon-readable: rotation decision + log review owed — retail prerequisite · `retail` |
| TD-S81-NEW-2 (:1557) | S2 | anon SELECT is still far broader than the 23 relations the frontend consumes | anon SELECT far broader than the 23 relations used — retail prerequisite · `retail` |
| TD-S81-NEW-3 (:1572) | S2 | nothing asserts that the anon revoke is still in force; item 3 of the S81 fix is trusted rather than verified | no assertion the anon revoke holds · `retail` |
| TD-S81-NEW-16 (:1785) | S2 | `merdian_ro` reads zero rows, silently, from 57 RLS-enabled tables, and a FAIL was reported to the operator… | merdian_ro reads 0 rows from 57 RLS tables · `retail` |
| TD-S71-NEW-11 (:4029) | S1 | SECURITY: operator `.env` was printed in full to a session transcript; long-lived credentials require rotation | S1 — .env printed to transcript; rotation outstanding — retail prerequisite · `retail` |
| TD-S39-NEW-3 (:4891) | S3 | `.env` containing live MERIDIAN Supabase anon key committed to public GitHub repo `balannavin-cyber1/meridi… | anon key in public repo meridian-connect — retail prerequisite · `retail` |
| TD-S39-NEW-4 (:4906) | S4 | Orphan AWS Security Group `launch-wizard-2` not attached to any EC2 instance — cleanup pending | orphan security group · `retail` |

**B2 · Closing session (S98 order 2: R5, R6, R20)** (1)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S97-NEW-13 (:199) | S3 | 2026-10-21 one-minute spot is recoverable; the chain snapshots are not | R20 — re-scoped S98-D: board prev-close read (no write) |

**B3 · Reads before any TD (S98 order 3: R7, R8, R10, R18, R36)** (15)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S97-NEW-19 (:254) | S3 | transient "different run — not drawn" / "no chain" while the views were on the same run | R16 — tab not re-polling γ views (evidence 10-23) |
| TD-S95-NEW-1 (:359) | S2 | vendor OI on untraded legs is not a measurement, and every reader of OI levels takes it at face value | (a)(b) DONE, (c) guard S96-D; residual = OI readers take vendor OI at face value → with R7 OI read |
| TD-S84-NEW-4 (:1315) | S2 | the L13 rotation anchor is fabricated on stale vendor rows, and this contradicts TD-S83-NEW-5's "the open i… | L13 rotation anchor on stale vendor rows → with R7 OI read |
| TD-S83-NEW-2 (:1382) | S2 | `compute_volatility_metrics_local.py` averages a zero implied volatility into `atm_iv_avg` as though it wer… | zero IV averaged into atm_iv_avg |
| TD-S83-NEW-3 (:1396) | S3 | depth-2 capture intermittently lands a single expiry, so a cycle that should carry W1+W2 carries only W1 | depth-2 capture lands one expiry intermittently |
| TD-S83-NEW-4 (:1409) | S3 | far-wing OTM implied volatility reads *below* ATM on the NIFTY back leg, which no smile explains, and L10 p… | far-wing IV below ATM on NIFTY back leg |
| TD-S83-NEW-5 (:1422) | S3 | vendor implied volatility on high-open-interest near-money ITM strikes reads ~8x ATM, and the open interest… | ITM IV ~8× ATM (excluded by convention) |
| TD-S79-NEW-8 (:2278) | S2 | SENSEX has no gamma at all on ~30 % of its strikes, so every per-strike gamma layer on SENSEX is computed o… | SENSEX no γ on ~30 % strikes |
| TD-S79-NEW-15 (:2387) | S2 | the L3 flip gate is algebraically degenerate: "spot above the flip" and "TotalGEX(spot) > 0" are the same p… | L3 flip gate degenerate → with R10 |
| TD-S79-NEW-16 (:2408) | S3 | the repriced flip lands ~3× closer to spot than the published landmark, and the divergence survives the σ b… | repriced flip 3× closer than landmark → with R10 |
| TD-S79-NEW-17 (:2427) | S2 | the rebuilt cumulative crossing and the shipped `flip_level` are not the same construction and never produc… | cumulative crossing ≠ flip_level → with R10 |
| TD-S79-NEW-18 (:2447) | S2 | the SENSEX leg of the cumulative-gate result does not reproduce: 1.0 % against 34.3 %, and which measuremen… | SENSEX cumulative-gate 1.0 % vs 34.3 % → with R10 |
| TD-S75-NEW-1 (:3347) | S2 | `build_gss_rows` writes `gex_cr` through the deep-ITM filter while OI and gamma bypass it, so a stored row… | gex_cr through deep-ITM filter, OI/γ bypass |
| TD-S75-NEW-2 (:3362) | S2 | the deep-ITM gamma threshold is a bare constant, so it is ~3.2× stricter on SENSEX than on NIFTY | deep-ITM γ threshold bare constant (3.2× SENSEX) |
| TD-S71-NEW-13 (:4059) | S3 | VERIFY: deep-ITM option `ltp` prints below intrinsic value; anything computing extrinsic from `ltp` inherit… | deep-ITM ltp below intrinsic — verify |

**B4 · Small fixes (S98 order 4: R9, R19, R22–R24, R34/R35)** (39)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S97-NEW-11 (:180) | S3 | `breadth_indicators_daily` is missing 2026-10-08 and 10-15 while `equity_eod` has both | R19 — breadth_indicators_daily 10-08 / 10-15 |
| TD-S97-NEW-12 (:189) | S3 | EOD for 2026-10-19 and 10-21 not written; check the catch-up | R19 — EOD catch-up re-read |
| TD-S97-NEW-14 (:209) | S3 | `trading_calendar` 2026-09-14 is closed but labelled a normal trading day | R22 — 09-14 calendar label |
| TD-S97-NEW-15 (:218) | S3 | `data_contamination_ranges` has no symbol column | R23 — symbols column on data_contamination_ranges |
| TD-S97-NEW-16 (:227) | S3 | twelve Marketview backups on the box, no retention rule | R24 — Marketview backup retention |
| TD-S97-NEW-21 (:274) | S3 | the Health page reads CRITICAL every day and labels a subscription lapse TOKEN_EXPIRED | R9 — Health page CRITICAL; SUBSCRIPTION class |
| TD-S96-NEW-2 (:316) | S3 | the planner estimates 1 row for a day of `gex_strike_snapshots` selected by `ts` alone | X1 — MITIGATED S97-F/G; residual autoanalyze threshold |
| TD-S94-NEW-1 (:395) | S2 | `merdian_ro` read zero rows from `participant_oi_daily` and `data_contamination_ranges`, so Rule 13 checks… | X1 — merdian_ro visibility; with R23 |
| TD-S94-NEW-2 (:406) | S3 | `bin/roq.sh`'s write-verb guard refuses `COPY (SELECT …) TO STDOUT`, which is a read | X1 — roq.sh COPY guard |
| TD-S93-NEW-1 (:441) | S2 | `run_offline.sh`'s `PIPESTATUS` idiom is positional, so inserting any command between a pipeline and its te… | X1 — PIPESTATUS positional idiom in run_offline.sh (step 14 just added the same idiom) |
| TD-S91-NEW-2 (:634) | S3 | SEVEN more unpadded `fromisoformat` sites, one now fixed, and ~40 copies of the same padding with no shared… | X1 — 5 unpadded fromisoformat sites left; core/ts_parse.py built |
| TD-S91-NEW-4 (:664) | S3 | `ws_feed_zerodha.log` stamps UTC time under an "IST" label | ws_feed log UTC under IST label (same as TD-NEW-D) |
| TD-S91-NEW-5 (:675) | S2 | the `breadth_indicators_daily:ALL` contract allows 2 trading days behind against a settled lag of ~3, so it… | breadth_indicators_daily gate vs settled lag (with R19) |
| TD-S90-NEW-1 (:811) | S2 | `dhan_scrip_map` is never re-synced against the scrip master, so every NSE series change leaves a dead secu… | scrip-map re-sync (R1.10 design exists; small SC job) |
| TD-S90-NEW-3 (:833) | S3 | about 26 calendar gates are still inline copies, not `core/trading_calendar_gate.py` | ~26 inline calendar gates (absorbs TD-S60-NEW-3 residual); feeds R2 calendar-blind writers |
| TD-S90-NEW-5 (:853) | S3 | `v_gex_max_pain` fails intermittently at about anon's 3-second statement timeout | v_gex_max_pain ~3 s anon timeout |
| TD-S90-NEW-9 (:893) | S3 | every `roq.sh` connection warns of a collation version mismatch | roq.sh collation warning |
| TD-S83-NEW-6 (:1436) | S3 | `.gitignore` covers `*.log` but not rotated logs or `status.json`, so the widened logrotate scope produces… | .gitignore rotated logs + status.json (absorbs TD-S87-NEW-3) |
| TD-S81-NEW-4 (:1587) | S2 | `v_dealer_flow_sim` is the third ADR-021 sibling and was never scoped; it returns 57014 on any unfiltered read | v_dealer_flow_sim unscoped (57014) |
| TD-S81-NEW-6 (:1621) | S3 | `v_max_pain_by_strike.max_pain` has a non-deterministic tie-break | max_pain tie-break non-deterministic |
| TD-S79-NEW-6 (:2243) | S3 | three untracked scratch files sit in the production tree | scratch files in production tree |
| TD-S79-NEW-9 (:2298) | S2 | `pin_risk_score`'s proximity component is ABSENT, not depressed, so the score silently changes basis betwee… | pin_risk_score proximity ABSENT |
| TD-S79-NEW-21 (:2509) | S3 | `_FLIP_DOMINANCE_EPS_FRAC` is a hardcoded magic number on a live operator surface, and it is relative to th… | _FLIP_DOMINANCE_EPS_FRAC magic number |
| TD-S78-NEW-2 (:2645) | S3 | 67 backup artefacts are tracked in git with no retention rule, and `.gitignore` cannot remove them because… | 67 tracked backups |
| TD-S76-NEW-2 (:2993) | S1 | `pg_cron jobid 19` disabled as a stop-gap: `gamma_metrics` now grows past its 90-day window, and the stated… | pg_cron jobid 19 disabled — gamma_metrics past 90 d; reversal decision (ties P4 retention) |
| TD-S73-NEW-2 (:3507) | S3 | a literal Windows path exists as a directory on the Linux host and something writes into it daily | literal Windows path dir on Linux written daily |
| TD-S72-NEW-4 (:3697) | S3 | `gex_strike_snapshots` carries a duplicate index and a third that is redundant against the composite | gss duplicate index (re-observed S97) |
| TD-S71-NEW-3 (:3905) | S3 | the VIX history read has no `ORDER BY`; its correctness depends on unspecified row ordering | VIX history read no ORDER BY |
| TD-S71-NEW-5 (:3939) | S3 | `run_ingest.sh` `set -eo pipefail` makes its own `END … rc=` line unreachable on failure | run_ingest.sh END rc unreachable |
| TD-S71-NEW-8 (:3985) | S3 | `capture_premarket_0908.py` is an orphan whose filename encodes an instant that ceases to exist on 2026-09-07 | capture_premarket_0908 orphan |
| TD-S71-NEW-12 (:4045) | S3 | `.gitignore` `*_PRE_S*` silently swallows the crontab backups it was never written for | *_PRE_S* swallows crontab backups (seen S99 §D.53.2) |
| TD-S70-NEW-4 (:4091) | S2 | `india_vix_history` has no writer and has been frozen at 2026-03-11 for five months; `vix_percentile` is sc… | india_vix_history no writer (frozen 03-11) |
| TD-S69-NEW-3 (:4174) | S2 | `fetch_positioning_landscape` has no ADR-018 D2 recency floor; the ADR-021 speed fix converts a loud timeou… | fetch_positioning_landscape no recency floor |
| TD-S60-NEW-5 (:4466) | S2 | `core/config.py` hardcodes Windows `BASE_DIR = C:\GammaEnginePython`; loads `.env` from a path that doesn't… | core/config.py Windows BASE_DIR |
| TD-S38-NEW-2 (:4951) | S4 | Dead `TIMEOUT_LIVE_DEFAULT` + `TIMEOUT_SHADOW_DEFAULT` constants in `run_option_snapshot_intraday_runner.py` | dead timeout constants |
| TD-005 (:5949) | S3 | `option_execution_price_history` table marked DEPRECATED but not yet DROPPED | deprecated table not dropped |
| TD-007 (:5983) | S3 | `is_pre_market` column in `hist_spot_bars_1m` is vestigial | vestigial is_pre_market column |
| TD-009 (:6000) | S4 | `.bak` file debris in `docs/registers/` | .bak debris in docs/registers (with TD-S78-NEW-2) |
| TD-025 (:6251) | S4 | `build_spot_bars_mtf.py` re-aggregates full history every run (compute waste) | build_spot_bars_mtf full re-aggregation |

**B5 · Wording batch, operator yes, with manual v0.4 (S98 order 5)** (5)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S97-NEW-17 (:236) | S3 | the Hedge-per-1 % tile and drawer still make a dealer claim | R14 — dealer wording batch (absorbs manual F-1, F-7) |
| TD-S97-NEW-18 (:245) | S3 | the flow's own gap (ΔOI on unpriced legs) is not on the board | R15 — draw G25 gap |
| TD-S84-NEW-7 (:1279) | S2 | the UI labels `flip_distance_pct` as sigma, so a spot-to-flip distance is rendered as a volatility band | flip_distance_pct labelled σ → wording batch |
| TD-S84-NEW-6 (:1291) | S2 | two max pains over different substrates, agreeing on strike and disagreeing on everything else; which is ca… | two max pains; canonical choice is a ruling |
| TD-S39-NEW-5 (:4921) | S3 | Marketview "stale {N}s" badge contradicts 300s threshold setting — needs live-day verification | stale badge vs 300 s threshold |

**B6 · Pre-registered improvements (S98 order 6: R12, R13)** (2)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S80-NEW-1 (:1871) | S2 | the ingest discards the expiry ladder the vendor returns, so no multi-expiry IV exists at any timestamp and… | X1 — ingest discards expiry ladder (multi-expiry IV) |
| TD-S79-NEW-1 (:2152) | S2 | `GREATEST(dte, 1)` overstates σ on expiry day, so the moneyness band is widest on the day it most needs to… | GREATEST(dte,1) widens band on expiry day — re-sweep (pre-reg) |

**BR · Rebuild source and deploy reproducibility — retail prerequisite** (8)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S92-NEW-6 (:474) | S3 | the Marketview build box has no bun and Lovable updates only `bun.lock`, so a dependency change breaks the… | X1 — Marketview box build has no bun · `retail` |
| TD-S92-NEW-3 (:485) | S3 | `sql/2026-10-03_s89_v_gex_greeks_l2.sql` says its V2 probe is "committed with this file", and it is not in git | X1 — V2 probe not in git · `retail` |
| TD-S84-NEW-3 (:1327) | S2 | three views ship a `COMMENT ON VIEW` in `sql/` that was never executed live, and one ships its `GRANT` comm… | COMMENT/GRANT in sql/ never executed live · `retail` |
| TD-S84-NEW-2 (:1339) | S2 | `gamma_metrics` has no `CREATE TABLE` anywhere in `sql/`, an ADR-025 D2 clause 4 gap on the most-read objec… | gamma_metrics has no CREATE TABLE in sql/ · `retail` |
| TD-S84-NEW-1 (:1351) | S3 | the `sql/` file does not reproduce the live `merdian_ro` grant on two of the three S83 views, so a rebuild… | sql/ misses live merdian_ro grant · `retail` |
| TD-S81-NEW-5 (:1603) | S2 | `sql/` is not a true rebuild source, and the divergence runs in BOTH directions | sql/ not a rebuild source (both directions) — absorbs TD-S79-NEW-3 · `retail` |
| TD-S81-NEW-8 (:1654) | S3 | `~/redeploy_marketview.sh` builds from a stale May-27 clone, not the tree the live bundle comes from | redeploy_marketview.sh builds from a stale clone · `retail` |
| TD-S80-NEW-16 (:2107) | S3 | `/etc/logrotate.d/meridian` exists only on the box: third instance of on-box-only infrastructure after the… | logrotate config only on the box · `retail` |

**BO · Ops and monitoring** (10)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S80-NEW-15 (:2092) | S2 | ~1.76 GB of the 2.5 GB that filled the root volume is unattributed, so the resize is a delay of known lengt… | 1.76 GB unattributed on root volume |
| TD-S80-NEW-17 (:2122) | S3 | `merdian-wsfeed-start.timer` is `Persistent=false`, so a start missed while the host is wedged needs a human | wsfeed timer Persistent=false — decision owed |
| TD-S73-NEW-1 (:3492) | S2 | `shadow_runner.log` is a 262 MB live log at repo root, outside logrotate's scope, while its cron line's vis… | shadow_runner.log 262 MB outside logrotate |
| TD-S73-NEW-6 (:3567) | S2 | `eod_health_check.py` has no scheduled invoker; the fourth instance of the class, and TD-S72-NEW-7's premis… | eod_health_check no scheduled invoker |
| TD-S71-NEW-14 (:3840) | S1 | `dhan_scripmaster` has no scheduled reload, and futures contract resolution has no fallback: the table sile… | scripmaster reload: invoker reconciliation + duplicate invocation |
| TD-S69-NEW-2 (:4158) | S1 | `scripts/eod_health_check.py` returned `[OK]` on 2026-08-12 while pin/accel, the M5 detector and the GEX re… | eod_health_check false [OK] |
| TD-S53-NEW-5 (:4656) | S2 | S52 observability monitors report false state (both directions) + watchdog shares the patient's failure chain | monitors false state; watchdog shares the patient's chain |
| TD-NEW-B (:5340) | S1 | `pg_cron` job failures invisible by default — needs polling daemon or session-start gate | pg_cron failures invisible (P3b sweep is a pg_cron job) |
| TD-027 (:6285) | S4 | `merdian_pipeline_alert_daemon` scope drifted from name | alert daemon scope drift (S98-E.1 relies on it) |
| TD-028 (:6302) | S3 | `merdian_pm.py` silently fails on unknown process name | merdian_pm silent on unknown name |

**BD · Docs and process hygiene (one batch session)** (41)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S94-NEW-3 (:417) | S2 | an apply copied out of the terminal landed only Section 1 of the DEX view, the editor said Success, and the… | X1 — apply procedure; every apply ends with a verification SELECT (S95–S98 practice) → codify, then close |
| TD-S91-NEW-17 (:593) | S3 | `check_kite_auth.py` is cited by the Topology and a runbook and does not exist | check_kite_auth.py cited, absent → with R4 probe |
| TD-S87-NEW-2 (:1013) | S2 | `check_xrefs` cannot see `AC29-n` labels or `§5a`/`§5b` references, and its document map is hard-coded, so… | check_xrefs blind spots |
| TD-S87-NEW-5 (:1052) | S3 | `session_log.md` carried 11 entries against a documented "newest 10", so an earlier doc-close skipped the r… | session_log roll not detected |
| TD-S86-NEW-1 (:1080) | S2 | the S74 Doc Protocol v4 Rule 7 amendment never reached `MERDIAN_Documentation_Protocol_v4.md`, so two docum… | Doc Protocol Rule 7 in two documents |
| TD-S83-NEW-7 (:1448) | S3 | two register errata, one of which was itself misattributed in this session's own capture | CLAUDE.md erratum 1 unedited |
| TD-S81-NEW-15 (:1769) | S3 | the register says `merdian_order_placer.py` runs from an `@reboot` cron line; neither the line nor the proc… | register cites an @reboot order-placer line that does not exist |
| TD-S80-NEW-4 (:1928) | S2 | the documented commit-message pattern emits a BOM, and one shipped inside a commit subject this session | commit-message rule still emits BOM (practice is [IO.File]::WriteAllText) |
| TD-S80-NEW-7 (:1973) | S3 | `gex_pin_maxpain_history` is a Rule 10 schema-affecting table with no ADR of its own | gex_pin_maxpain_history has no ADR |
| TD-S80-NEW-12 (:2041) | S2 | the deploy-direction correction has been drafted and UNRATIFIED since S73, and S80 acted against the topolo… | deploy-direction correction unratified — box route ruled S99 → ratify |
| TD-S80-NEW-14 (:2077) | S3 | `tech_debt.md` closed TD-S79-NEW-14 and left three references to it stale one file over | missing sweep step on TD close |
| TD-S79-NEW-5 (:2225) | S2 | the deploy-direction inversion, third and fourth instances: two independent commits of identical content in… | deploy-direction inversion → box route ruled S99 |
| TD-S79-NEW-7 (:2259) | S3 | the S74 Doc Protocol amendment cites a rule number belonging to a different rule, and amends a rule the nam… | S74 amendment cites wrong rule |
| TD-S79-NEW-11 (:2335) | S3 | ADR-017 Principle 6 is right about the bug and wrong about the cause: it is a DTE difference, not a symbol… | ADR-017 P6 amendment owed |
| TD-S79-NEW-24 (:2567) | S3 | Doc Protocol v4 Rule 11.3's governance-footer obligation is unenforced, and compliance cannot be counted be… | Rule 11.3 footer unenforced |
| TD-S79-NEW-25 (:2587) | S2 | there is no project-knowledge manifest, so Rule 12 compliance is undetectable by construction | no project-knowledge manifest (PK at 1.92/2.00 MB) |
| TD-S79-NEW-26 (:2607) | S3 | Rule 12's re-upload list omits five of the documents the session-end checklist requires to be updated, so f… | Rule 12 re-upload list incomplete |
| TD-S78-NEW-1 (:2627) | S3 | the session-date convention is unspecified in Doc Protocol v4, and the only format v4 does specify cannot e… | session-date convention |
| TD-S78-NEW-3 (:2663) | S2 | project knowledge round-trips LF to CRLF, so the Rule 12 hash comparison cannot distinguish an identical fi… | PK CRLF round-trip (blob compare, as done S99) |
| TD-S77-NEW-4 (:2808) | S3 | `/patch_*.py` is gitignored, so not one patch script in MERIDIAN's history is in version control | patch scripts gitignored |
| TD-S77-NEW-7 (:2850) | S3 | `script_execution_log.host` is not evidence of which machine ran a script | script_execution_log.host not evidence |
| TD-S76-NEW-11 (:3126) | S3 | F-82: nine of eighteen `ADR-004` line citations in the S76 audit were wrong, in four distinct ways, and eve… | ADR line-citation class |
| TD-S76-NEW-12 (:3141) | S3 | Rule 7 splice-discipline defect in S75's own doc-close: the Topology splice anchored on the wrong footer an… | Rule 7 splice discipline |
| TD-S76-NEW-15 (:3182) | S3 | Doc Protocol v4 asserts `CURRENT.md` is mixed-EOL and must be edited in binary mode; measured, it is pure L… | Doc Protocol EOL claim |
| TD-S76-NEW-16 (:3199) | S2 | `merdian_reference.json`'s own version control is unreliable: two `change_log` arrays ten sessions apart, a… | reference.json version control (absorbs S86-NEW-7, S79-NEW-23, S71-NEW-2, S61-NEW-3) |
| TD-S76-NEW-21 (:3283) | S3 | ADR-004's Amendments A and B are absent from the Decision Index entirely, and Amendment C's new marker make… | ADR-004 amendments missing from Decision Index |
| TD-S76-NEW-22 (:3299) | S3 | Session Management Rule 5 specifies a twelve-field session-log block; the log abandoned it ~2026-04-07 and… | session-log twelve-field block abandoned → rule vs practice |
| TD-S76-NEW-23 (:3314) | S2 | the production checkout `~/meridian-engine` sat 22 commits behind `origin/main` at the S76 close, having ne… | no assertion engine tree == origin (four-way hash now done by hand at each commit) |
| TD-S75-NEW-4 (:3329) | S2 | ADR-002 v2's build sequence and the Enhancement Register use ENH-80..85 for different things; the register… | ENH-80..85 numbering collision |
| TD-S73-NEW-10 (:3464) | S3 | the System Map and Deployment Topology `## Update log` tables are frozen at Session 67 while both files rec… | System Map / Topology update logs frozen |
| TD-S73-NEW-7 (:3582) | S2 | the Claude Code permission model is verb-shaped, not effect-shaped, and the config itself is untracked | CC permission model verb-shaped, config untracked |
| TD-S73-NEW-9 (:3617) | S3 | approved diffs are not hunk-independent, and a partial application produced a quieter failure than the defe… | partial diff application |
| TD-S72-NEW-12 (:3815) | S2 | byte-size comparison across storage tiers is invalid under `core.autocrlf=true`; Doc Protocol v4's four-tie… | autocrlf byte-size comparison invalid (blob compare in use) |
| TD-S71-NEW-1 (:3874) | S2 | `merdian_reference.json` does not cover the files and tables the register's own read-rule points at | reference.json coverage |
| TD-S70-NEW-1 (:4074) | S2 | `CURRENT.md` is 661 KB of which 98% is superseded session blocks, and it is read second at every session open | CURRENT.md size |
| TD-S57-NEW-3 (:4535) | S3 | Enhancement Register has a dual structure with conflicting per-ENH status | Enhancement Register dual structure |
| TD-S46-NEW-2 (:4722) | S3 | S3 deployment automation wrapper scripts (reduce manual workflow) | S3 deploy wrapper scripts — superseded? box route via git |
| TD-015 (:6032) | S3 | `run_preflight.py` 4-stage preflight system is undocumented; reinvented as one-off | run_preflight.py undocumented |
| TD-021 (:6159) | S4 | Two undocumented operational conventions surfaced during Session 8 | two undocumented conventions (S8) |
| TD-037 (:6457) | S4 | Schema column-name inconsistency across timestamp-bearing tables | timestamp column naming |
| TD-053 (:6586) | S3 | CLAUDE.md Rule 16 needs era-aware addendum (post-04-07 era) | CLAUDE.md Rule 16 era addendum |

### 3.7 PARK (10)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S96-NEW-3 (:327) | S3 | the P5 strike join in the S96 flow views plans as a 437 × 437 nested loop | X1 watch — trigger: P3b sweep runtime > budget |
| TD-S90-NEW-4 (:843) | S3 | `market_ticks` is purged after every close by a job nobody has traced | purge named (jobid 46), ticks frozen; trigger: a tick-based replay needs >10 days |
| TD-S89-NEW-3 (:956) | S3 | `r_sess` (futures-implied carry) and ENH-98's `r_eff` disagree 2.7× on a same-named quantity, and the split… | r_sess vs r_eff — immaterial to L7/L8; trigger: any use of r_sess as a rate |
| TD-S87-NEW-1 (:1065) | S3 (re-rated) | `merdian-runbooks` routes 7 of its 9 runbook targets to files that do not exist, including *Emergency stop… | re-rated S3 and PARKED by operator (no orders ever); trigger: any order path |
| TD-S81-NEW-10 (:1686) | S3 | manual/diagnostic `option_chain_snapshots` readers are not expiry-scoped and predate depth 2 | ruled "do not fix now"; trigger: a manual reader used on depth-2 data |
| TD-S80-NEW-3 (:1911) | S3 | `max_pain_in_pin_band` fires on two runs in five regardless of DTE, so it cannot discriminate and must not… | max_pain_in_pin_band undiscriminating; trigger: any read of it |
| TD-S79-NEW-2 (:2172) | S3 | `wall.iv_floor_min` is unproven in both directions: the column computes, the floor has never bound | iv_floor_min never bound; trigger: band re-sweep |
| TD-S79-NEW-4 (:2208) | S3 | watch item: SENSEX call wall sat at 4.8× corridor asymmetry against a calibrated ~1.2× | watch only |
| TD-S79-NEW-19 (:2466) | S3 | OCS↔`gamma_metrics` join coverage begins 2026-08-26, not 2026-08-24: two dates are 100 % unjoinable, and a… | 08-24/25 unjoinable; trigger: a study sample starting 08-24 |
| TD-S74-NEW-1 (:3390) | S1 | the producer/consumer coupling audit: 59 findings, filed as a pointer, not enumerated | 59-finding coupling audit pointer; trigger: each finding filed on its own when touched |

### 3.8 PARK-HIST (22)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S81-NEW-19 (:1836) | S3 | 2026-08-17 is a partial compute day: both symbols stopped writing at ~14:10, uninvestigated | 08-17 partial compute day; trigger: a study uses 08-17 |
| TD-S80-NEW-8 (:1990) | S3 | the backfill driver hardcodes its date window, so the script that produced 11,795 rows cannot be re-run wit… | backfill driver hardcoded window; trigger: next backfill |
| TD-S78-NEW-4 (:2681) | S2 | `historical_option_chain_snapshots` contains three whole sessions written by a second producer carrying no… | second producer in historical chain |
| TD-S78-NEW-5 (:2699) | S3 | `historical_option_chain_snapshots.dte` is declared and never written | historical chain dte never written |
| TD-S78-NEW-6 (:2715) | S2 | `volatility_snapshots` silently switches expiry class mid-history, and no column marks the transition | volatility_snapshots expiry-class switch |
| TD-S76-NEW-1 (:2976) | S1 | the Windows host stopped executing on 2026-06-05, taking the option-chain archival bridge with it, and ~58… | Windows archival bridge lost ~58 sessions of premium data |
| TD-S73-NEW-4 (:3539) | S3 | the `option_chain_snapshots` row floor cites a provenance that could not have produced it | OCS row floor provenance |
| TD-S73-NEW-5 (:3553) | S2 | UNVERIFIED: 2026-06-03 → 2026-08-24 appears in neither option-chain table | 06-03 → 08-24 chain gap unverified; trigger: a study needs that window |
| TD-S72-NEW-10 (:3791) | S3 | `gex_strike_snapshots` grew ~92k rows on a Saturday with every capture cron scoped Mon–Fri | gss +92k rows on a Saturday |
| TD-S70-NEW-9 (:4141) | S3 | 2026-08-17 capture degraded before the token failure and is unexplained | 08-17 capture degraded (pair with TD-S81-NEW-19) |
| TD-S62-NEW-2 (:4354) | S3 | SENSEX historical `gamma_concentration` unfilled for 2026-01-19 (SSLError mid-solve during the full-window… | SENSEX 01-19 gamma_concentration resume |
| TD-NEW-14 (:4739) | S2 | Four ingestion tables empty for 30+ days: `iv_context_snapshots`, `hist_atm_option_bars_5m`, `index_futures… | four ingestion tables empty (iv_context, ATM bars, futures, vix daily) — check each against ADR-019 port list |
| TD-S36-NEW-1 (:5025) | S3 | `gamma_metrics` Apr-early-May 2026 row gap (residual from TD-S30-CANDIDATE-1 cleanup) | gamma_metrics Apr–May gap |
| TD-S35-NEW-1 (:5093) | S2 | `historical_option_chain_snapshots` strike-coverage structural limit on MERDIAN-ingest tier | historical chain strike coverage |
| TD-S34-NEW-4 (:5147) | S2 | `hist_option_bars_1m` post-2026-04-01 coverage gap (vendor → MERDIAN-ingest tier transition) | hist_option_bars_1m post-04-01 gap |
| TD-094 (:5590) | S2 | `hist_option_bars_1m.oi=0` across all rows from S22 Kite backfill (Kite `historical_data` API does not retu… | Kite backfill oi=0 |
| TD-087 (:5608) | S2 | `hist_option_bars_1m.bar_ts` IST-as-UTC defect (5h30m phantom offset; only on option bars, not spot bars) | hist_option_bars_1m bar_ts IST-as-UTC |
| TD-002 (:5905) | S2 | `breadth_regime` NULL before 2025-07-16 in `hist_market_state` | breadth_regime NULL before 2025-07-16 |
| TD-024 (:6234) | S4 | 19:01 IST writes to `market_spot_snapshots` (post-close anomaly, two cases) | 19:01 IST spot writes (two cases) |
| TD-029 (:6319) | S2 | `hist_spot_bars_1m` and `hist_spot_bars_5m` pre-04-07 era TZ-stamping bug | pre-04-07 TZ stamping |
| TD-034 (:6405) | S2 | `hist_atm_option_bars_5m` severely undersampled on expiry days (dte=0) | ATM bars undersampled dte 0 |
| TD-038 (:6474) | S3 | `hist_spot_bars_5m` has no `is_pre_market` column (schema assumption mismatch) | hist_spot_bars_5m no is_pre_market |

### 3.9 PARK-ICT (68)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S79-NEW-20 (:2486) | S2 | replay is pinned to production's legacy fallback branch: its `compute_flip_level` is that branch line-for-l… | replay pinned to legacy flip branch (signal replay) |
| TD-S77-NEW-1 (:2764) | S1 | ADR-004 Amendment C's event class is unimplemented; 78 % of `ict_primitive_outcomes` is still anchored at b… | ADR-004 Amendment C unimplemented |
| TD-S77-NEW-2 (:2780) | S2 | D and W have a measurement anchor but no entry anchor, so daily and weekly ICT are unmeasured on options | D/W ICT no entry anchor |
| TD-S77-NEW-3 (:2794) | S3 | a recompute whose `--end` lands mid-week rewrites the previous cohort's last W bucket; F-78 guards the star… | W bucket recompute |
| TD-S77-NEW-6 (:2836) | S3 | two snapshot tables exist in production and are in no register; they are the only surviving copy of the pre… | pre-fix ICT snapshot tables unregistered |
| TD-S77-NEW-9 (:2876) | S3 | TD-S76-NEW-18's 2-row gap did not reproduce, and its cause is now reachable only through the pre-fix snapshot | S76-NEW-18 gap |
| TD-S77-NEW-10 (:2890) | S1 | `assign_tier` is live on the signal path and carries mined thresholds; the S30 disable flag covers one of i… | assign_tier live on signal path |
| TD-S77-NEW-11 (:2904) | S1 | the BEAR_OB afternoon skip cites one time window and gates another, and the two available measurements of i… | BEAR_OB afternoon skip |
| TD-S77-NEW-12 (:2920) | S2 | two registers publish different headline numbers for Experiment 2, disagreeing on every row, and neither ci… | Exp 2 headline numbers |
| TD-S77-NEW-13 (:2934) | S2 | published experiment N is the pre-drop count; 55–65 % of each cohort was never scored, and the drop correla… | experiment N pre-drop |
| TD-S77-NEW-15 (:2962) | S2 | S31-C is unrun and the rebuilt cohort stops at 2026-06-04; `ict_primitives` still has no scheduled producer… | S31-C unrun |
| TD-S76-NEW-3 (:3010) | S1 | F-19 has three consumers, not two, and the third logs its own failure on every single cycle into a field no… | F-19 third consumer |
| TD-S76-NEW-4 (:3025) | S1 | F-68: `valid_from` is the confirming bar's OPEN, so every column of all 19,662 `ict_primitive_outcomes` row… | F-68 valid_from lookahead |
| TD-S76-NEW-5 (:3041) | S1 | F-64: `zone_high`/`zone_low` sit in the upsert conflict key, so a corrected bar mints a duplicate instead o… | F-64 zone key duplicates |
| TD-S76-NEW-6 (:3055) | S2 | S31-C never executed: the canon layer conforms to ADR-004, was backfilled once, and then stopped | S31-C never executed |
| TD-S76-NEW-7 (:3069) | S1 | F-60: the legacy `detect_daily_zones` is polarity-inverted, its own comment says the deviation is "tracked… | legacy detect_daily_zones inverted |
| TD-S76-NEW-8 (:3083) | S2 | `OB_MIN_MOVE_PCT = 0.40` is a volatility gate: hourly OB formation tracks monthly VIX and reaches zero in l… | OB_MIN_MOVE_PCT volatility gate |
| TD-S76-NEW-9 (:3097) | S2 | 1H structure detection is directionally asymmetric: BEAR_FVG is current, the other three primitives are mon… | 1H structure asymmetric |
| TD-S76-NEW-10 (:3112) | S2 | `expected_writes` is a floor, so both ICT writers log `contract_met=true` daily regardless of what they wrote | ICT writers contract_met floor |
| TD-S76-NEW-13 (:3155) | S2 | F-76: `merdian_reference.json` pins both ICT files at line counts four generations stale | reference.json pins ICT line counts |
| TD-S76-NEW-18 (:3235) | S3 | ADR-004 §10 asserts `ict_primitive_outcomes` is 1:1 with `ict_primitives` via FK CASCADE; the live tables d… | ADR-004 §10 1:1 claim |
| TD-S76-NEW-19 (:3252) | S1 | `build_trade_signal_local.py` selects `ict_tier` from `ict_htf_zones`, a column that is not on that table;… | build_trade_signal ict_tier column |
| TD-S76-NEW-20 (:3268) | S1 | fixing NEW-19 arms F-19 on the signal path: the `ict_tier` removal and the `valid_to` predicate must land i… | F-19 arming with NEW-19 |
| TD-S74-NEW-2 (:3404) | S1 | F-19: every D and W ICT zone is invisible to the signal path, while the chart renders them | F-19 D/W zones invisible to signal path |
| TD-S71-NEW-6 (:3953) | S3 | `SPOT_MAX_AGE_MIN` is weekend-blind and false-flags every Monday pre-market run, in the same file where the… | Pine generator SPOT_MAX_AGE weekend-blind |
| TD-S71-NEW-7 (:3969) | S2 | `generate_pine_overlay.py` has had no scheduled invoker since the S70 migration dropped the third `.bat` line | Pine generator no invoker |
| TD-S71-NEW-9 (:4000) | S3 | the Pine generator reports two different zone counts in one run | Pine generator two zone counts |
| TD-S70-NEW-8 (:4123) | S2 | the "`OB_MIN_MOVE_PCT = 0.40%` is empirically unreachable" finding was measured against the wrong quantity… | M5 detector writes nothing; claim withdrawn |
| TD-S69-NEW-5 (:4204) | S2 | the M5 ICT detector is an AWS orphan: `MERDIAN_ICT_EOD` has only ever run on Local Windows Task Scheduler,… | M5 ICT detector AWS orphan |
| TD-S40-NEW-3 (:4846) | S2 | TradingView Pine overlay extension for PIN + ACCEL zones — deferred pending full file review | Pine PIN + ACCEL overlay |
| TD-S39-NEW-2 (:4876) | S3 | Marketview hero chart label collision residual at dense ICT-zone band area near spot | hero chart ICT label collision |
| TD-S38-NEW-3 (:4966) | S3 | `ict_primitives × gamma_metrics` LATERAL joins need canonical helper view | ict_primitives × gamma LATERAL helper |
| TD-S35-NEW-4 (:5129) | S3 | `build_ict_primitives.py` writer is INSERT-only on `ict_primitive_outcomes`; schema column additions do not… | ict_primitive_outcomes INSERT-only |
| TD-S33-NEW-1 (:5167) | S3 | `hist_atm_option_bars_5m` reason-to-exist re-evaluation post-wick-experiment retirement | hist_atm_option_bars_5m reason to exist |
| TD-S33-NEW-2 (:5184) | S4 | v6 dead code in `compute_atm_pnl_and_dte` trailing for-loop + retired `_atm_anchor_at` / `_atm_future_at` h… | v6 dead code in compute_atm_pnl_and_dte |
| TD-S33-NEW-3 (:5201) | S2 | Post-v7 falsification audit needs re-scope | post-v7 falsification audit |
| TD-S33-NEW-4 (:5218) | S3 | D-TF horizon extension — `mfe_pct` + `time_to_mfe_min` columns may already answer "what horizon makes D-TF… | D-TF horizon |
| TD-S31B-NEW-1 (:5235) | S3 | Pine v6 visual MTF-breach overlay deferred (Task 5 descoped after 5-version iteration with 6 Pine v6 ergono… | Pine MTF-breach overlay |
| TD-S30-NEW-4 (:5266) | S2 | DTE=0 cohort behavior unknown — live cohort N too small for verdict | DTE=0 cohort |
| TD-S30-NEW-5 (:5283) | S2 | Gate stack inversion on three context dimensions (gamma / breadth / vix) — investigation queued | gate stack inversion |
| TD-S30-NEW-6 (:5300) | S3 | Replay infrastructure (`replay_build_trade_signal.py`) lacks ENH-88 — header line 15 attests S17 ENH was ad… | replay lacks ENH-88 |
| TD-S30-NEW-7 (:5317) | S3 | Hold-time bucket study scope — formal N≥100 per exit-bucket measurement on live cohort | hold-time bucket study |
| TD-098 (:5533) | S4 | Single-boundary replay momentum_regime classification differs from full-day orchestrator | replay momentum_regime |
| TD-096 (:5556) | S4 | Replay reconstructor skips boundary 15:30 because last `hist_spot_bars_1m` bar is at 15:29 IST | replay skips 15:30 |
| TD-095 (:5573) | S3 | `atm_iv_avg` unit ambiguity surfaces in `detect_ict_patterns_runner.py` Kelly sizing path | atm_iv_avg unit in Kelly sizing |
| TD-078 (:5698) | — | TD-070 closure verification incomplete — empirically multi-week BULL_OB lookback may not be firing as designed | BULL_OB multi-week lookback |
| TD-077 (:5704) | S4 | Wide FVG zones during volatile weeks lack outlier filter | wide FVG outlier filter |
| TD-076 (:5721) | S4 | SENSEX DTE gate persistent block on weekly expiry | SENSEX DTE gate on weekly expiry |
| TD-075 (:5738) | S3 | Confidence threshold 60 vs observed max 45 (gate never reached) | confidence threshold 60 vs 45 |
| TD-074 (:5755) | S3 | ENH-77 BULL_OB AFTERNOON NIFTY hard skip blocked the only TIER1 signal | BULL_OB afternoon skip |
| TD-073 (:5772) | S2 | Momentum direction lagged 700pt rally May 6 by ~60 min | momentum lag |
| TD-069 (:5790) | S2 | D timeframe doesn't generate OB/FVG even with real data (W and 1H do) | D timeframe OB/FVG |
| TD-067 (:5824) | S2 | Intraday backfill detector for Apr 1 → today historical pattern record | intraday backfill detector |
| TD-018 (:6083) | S4 | `build_ict_htf_zones.py:468` uses deprecated `datetime.utcnow()` | build_ict_htf_zones utcnow |
| TD-032 (:6370) | S2 | Dashboard execution panel ignores `direction_bias` / `action`, displays trades inconsistent with DB ground… | legacy dashboard execution panel |
| TD-033 (:6388) | S3 | Dashboard "SELL / BUY PE" label conflation | legacy dashboard SELL/BUY PE label |
| TD-035 (:6423) | S3 | `signal_snapshots.wcb_regime` is NULL on all rows but dashboard shows "BULLISH" | signal_snapshots.wcb_regime NULL |
| TD-036 (:6440) | S3 | `signal_snapshots.confidence_score` flat-lines for hours | confidence_score flat |
| TD-039 (:6491) | S2 | `hist_pattern_signals.ret_30m` stored as percentage points, not decimal fraction | ret_30m units |
| TD-049 (:6518) | S2 | D-OB detector uses non-standard ICT definition (D timeframe only) | D-OB non-standard |
| TD-050 (:6535) | S2 | D-zone non-FVG validity = 1 day (single-session expiry) | D-zone validity |
| TD-051 (:6552) | S3 | PDH/PDL `+/-20` band hardcoded, symbol-agnostic | PDH/PDL band |
| TD-052 (:6569) | S3 | Zone status workflow: write-once, never-recompute (historical builder only) | zone status write-once |
| TD-054 (:6603) | S2 | `ret_60m` column is uniformly 0 in `hist_pattern_signals` | ret_60m zero |
| TD-055 (:6621) | S3 | `ret_eod` column entirely absent from `hist_pattern_signals` | ret_eod absent |
| TD-056 (:6638) | S2 | Signal-detector bull-skew across BOTH code paths (5m batch AND 1m live) | signal bull-skew |
| TD-057 (:6655) | S3 | Exp 15 framework provenance gap (no findable execution audit trail) | Exp 15 provenance |
| TD-059 (:6673) | S2 | ENH-37 MTF context hierarchy inverted from claim (LOW outperforms HIGH on OB patterns) | ENH-37 MTF hierarchy |

### 3.10 PARK-AGENTIC (9)

| TD | Sev | Title (register) | Note |
|---|---|---|---|
| TD-S91-NEW-8 (:722) | S3 | the replay chain contract has no row band, so the harness cannot detect depth loss | R1.6 replay harness (Stage 1) |
| TD-S91-NEW-9 (:734) | S3 | the contract lookback bound is not floored to the cadence grid, so capture jitter moves the window edge | R1.6 harness lookback floor (Stage 1) |
| TD-S91-NEW-10 (:746) | S3 | a single dropped 5-minute cycle is undetectable by every check the contract runner has | R1.6 harness dropped-cycle blind spot (Stage 1); S98-B timeout now pages a 10-21-style outage |
| TD-S87-NEW-4 (:1039) | S3 | ruling #12's `git diff` and `git log` allow rules permit a file write, because both verbs accept `--output=… | ruling #12 git allow rules (agent permissions) |
| TD-S86-NEW-6 (:1161) | S3 | on the no-tools arm the model emitted invented tool calls with fabricated command output instead of answeri… | no-tools arm invented tool calls (caution, no fix owed) |
| TD-S85-NEW-1 (:1237) | S2 | `rag.corpus_snapshot` has no `completed_at`, so a half-built index is readable with no error and degrades A… | RAG corpus completed_at (ADR-026) |
| TD-S85-NEW-2 (:1251) | S3 | a bare `§7.2` is ambiguous corpus-wide: two documents have one, and the reading that looks obvious is the w… | corpus §7.2 ambiguity (RAG) |
| TD-S85-NEW-3 (:1265) | S2 | whether the first full index build fits G3a's 20-minute hard timeout is UNMEASURED, and ADR-026 provides no… | index build vs G3a timeout (RAG) |
| TD-S82-NEW-3 (:1503) | S2 | `eod_health_check` carries no model of capture depth ≥ 2, and the gap is the whole depth-aware change, not… | eod_health_check depth model → absorbed by R1.1/R1.2 contract runner (Stage 1) |

## 4. After the ruling (one commit, Doc Protocol v5)

1. Tracker: new **§2.2 "Open work — the single list"** (pass 1 rows R1–R46 + every KEEP here, by band, one row each pointing at its TD); **§2.3 "Retail (broker-connect)"** (R32 scoping, G1 regulatory open with counsel, G2–G4 as ruled 2026-10-24, prerequisite tags); §3 stages marked per Q7.
2. `tech_debt.md`: one S99 status-change paragraph (v5 Rule 3, no body edits) carrying every CLOSE / DUP / OBSOLETE / PARK line above.
3. `MERDIAN_OpenItems_Register_v7.md`: SUPERSEDED note → tracker §2.2. `CURRENT.md` NEXT → pointer to §2.2.
4. Commit pass 1 and pass 2 (and the S98 PK-only working docs) under `docs/research/s99/`.
