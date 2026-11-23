<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/proposal/signal_path_status.md -->

# Status of the Buy CE / Buy PE signal path — what the repo's own documents and code say

Read-only. Code and documents read in `~/meridian-engine` only. No database. No git writes.
Everything below is quoted or counted; where the documents do not settle a question the line
reads **NOT ESTABLISHED**. Dates given are the document's own date or session number where it
carries one, and otherwise the file's last commit date (`git log -1 --format=%cs -- <file>`),
labelled as such.

---

## PART 1 — what the documents say

### 1.1 Statements about the signal builder, `signal_snapshots`, `trade_allowed`, the gates, the "signal engine" / "signal layer", `signal_v4`

Ordered newest first by the dated statement itself.

| # | Quote (verbatim) | file:line | date / session the document gives |
|---|---|---|---|
| a | `| `signal_snapshots` | `build_trade_signal_local.py` | outcome engine, analytics, shadow comparison, regret log builder, `merdian_signal_dashboard.py` | LIVE — primary decision record. ICT …` | `docs/registers/MERDIAN_System_Map.md:180` | System Map footer `:1516` dates the §S76 block **Session 76, 2026-09-09/10**; the row itself carries no date. File last commit **2026-11-21**. |
| b | `| `build_trade_signal_local.py` (Local) | … **ENH-88 deploy** …` | `docs/registers/MERDIAN_System_Map.md:255` | no date on the row |
| c | `## §S76 — Session 76: the ICT layer's three tables, and a signal path whose HTF attach has never worked (2026-09-09/10)` | `docs/registers/MERDIAN_System_Map.md:1399` | **Session 76, 2026-09-09/10** |
| d | `1. **The HTF zone attach on the live signal path has never returned a row.** Not a` | `docs/registers/MERDIAN_System_Map.md:1424` | Session 76, 2026-09-09/10 |
| e | `### S76.E — the sequencing lock: fixing §S76.A arms F-19 on the signal path` | `docs/registers/MERDIAN_System_Map.md:1496` | Session 76, 2026-09-09/10 |
| f | `| `signal_snapshots` | single_strike | `symbol` | `ts` | iv, spot | 2026-03-08T07:12:13.021899+00:00 | 2026-09-11T09:50:06.403106+00:00 |` | `docs/registers/MERDIAN_Data_Inventory.md:209` | header `:3` **Measured: 2026-09-14**. This is the first/last `ts` the relation held *at that measurement*, not a status. `gamma_metrics:183` and `gex_strike_snapshots:184` carry the same 2026-09-11 last value, so the figure is the measurement boundary, not a signal-specific fact. |
| g | `| `build_trade_signal_local.py` | Step 9 — production signals | Shadow signals |` (columns are **Local** \| **MERIDIAN AWS**) | `docs/registers/MERDIAN_Deployment_Topology.md:204`, under `## §4 — Both-environments scripts (Local + MERIDIAN AWS)` (`:187`) | row carries no date; document `Established 2026-05-09 (Session 23)` (`:11`). File last commit **2026-11-21**. |
| h | `| `merdian_trade_logger.py` | Phase 4A manual trade entry. Couples human button-press to signal_snapshots row. |` | `docs/registers/MERDIAN_Deployment_Topology.md:137`, under `## §2 — Local-only scripts` (`:122`) | row carries no date |
| i | `| `merdian_signal_dashboard.py` | Live signal table + Pine refresh + LOG TRADE button (V19, Phase 4A). |` | `docs/registers/MERDIAN_Deployment_Topology.md:135` | row carries no date |
| j | `Both readers in `build_trade_signal_local.py` carry the ADR-018 D2 recency floor (`MERDIAN_FLOW_RECENCY_FLOOR_MIN`, `MERDIAN_BASIS_RECENCY_FLOOR_MIN`, both 15-min default). Basis context is display-only into `signal_snapshots.raw` (context-not-ga…` | `docs/registers/MERDIAN_Deployment_Topology.md:924` | S61 (the surrounding block names S61); no explicit date on the line |
| k | `Executes the governance rule established in **ADR-018** ("orphaned signal subsystems are dispositioned explicitly — retire-with-evidence or port-to-AWS — never left silen…` | `docs/decisions/ADR-019-signal-orphan-final-disposition.md:7` | `## Status` / **ACCEPTED — 2026-06-22 (Session 58)** |
| l | `The S49 Local-disable migrated capture + core compute to AWS but **did not include the signal layer**. Five V17 (16E) shadow-batch subsystems died with Local: SMDM, mome…` | `docs/decisions/ADR-019-signal-orphan-final-disposition.md:11` | ACCEPTED 2026-06-22 (Session 58) |
| m | `…shadow-comparison harness kept (ADR-001 governance); rebuild vs signal_v4 at next signal change. Orphaned by S49 Local-disable, n…` | `docs/registers/merdian_reference.json:3086` (`shadow_signal_snapshots_v3`, `status`) | ADR-019 D1 → Session 58, 2026-06-22 |
| n | `**Signal orphans (ADR-019):** `shadow_signal_snapshots_v3` / `iv_context_snapshots` RETAINED-PENDING-REHOME; `options_flow_snapshots` RETAINED-DORMANT. None retired.` | `docs/registers/MERDIAN_System_Map.md:797` | ADR-019 → Session 58, 2026-06-22 |
| o | `S49 intentionally disabled the Local Windows capture/compute layer and migrated capture + core compute to AWS. The migration scope (ADR-006) co…` | `docs/decisions/ADR-018-breadth-feed-supervision-and-signal-subsystem-disposition.md:32` | ADR-018 (S57) |
| p | `| `basis_pct` > 0.5% adds caution flag (not a block) | V18G ENH-07 | **LIVE** | Wired in `build_trade_signal_local.py`. Does not affect `trade_allowed`. Diagnostic only. |` | `docs/registers/MERDIAN_Assumption_Register.md:133` | row dates itself only as **V18G ENH-07** |
| q | `| **D.13.4** | The MERIDIAN gate stack as deployed S29-close inverts the edge direction on three context dimensions for the live cohort: (a) gamma regime — LONG_GAMMA WR 55.1% mean +5.37% (gated as BLOCK) vs SHORT_GAMMA WR 73.3% mean +19.67% (gat…` | `docs/registers/MERDIAN_Assumption_Register.md:351` | **Session 30** (§ opened `:342` "Session 30") |
| r | `| **D.13.5** | OB attachment in the live signal-builder is broken. Of 4,882 spot-price touches inside BULL_OB zone boundaries over the 8-week cohort, only 26 (0.5%) were tagged `ict_pattern = BULL_OB` in `signal_snapshots`.` | `docs/registers/MERDIAN_Assumption_Register.md:352` | Session 30 |
| s | `| **D.9.1** | ENH-55 momentum opposition rule (ret_session opposed → BUY_CE/BUY_PE blocked) is the right calibration for the live signal cohort. | **REFUTED S26** …` | `docs/registers/MERDIAN_Assumption_Register.md:213` | **S26** |
| t | `| Breadth-momentum CONFLICT → unconditional DO_NOTHING | … | **SUPERSEDED by ADR-007 SRB-01** | V18F evidence: CONFLICT BUY_CE produces 58.7% WR (NIFTY) / 55.4% (combined).` | `docs/registers/MERDIAN_Assumption_Register.md:52` | ADR-007 → 2026-04-11/12 decided, 2026-05-09 documented |
| u | `status = ACTIVE  --  6 signal engine changes applied (ENH-35 2026-04-11): (1) CONFLICT BUY_CE now trades, (2) LONG_GAMMA gates to DO_NOTHING, (3) NO_FLIP gates to DO_NOTHING, (4) VIX gate removed from trade_allowed, (5) MIN_CONFIDENCE 60->40, (6) power hour gate after 15:00 IST.` | `docs/registers/merdian_reference.json:1239` (`files."build_trade_signal_local.py".status`) | dates itself **ENH-35 2026-04-11**; file carries `version = v84` |
| v | `status = LIVE` with `written_by = ['build_trade_signal_local.py']`, `read_by = ['outcome engine', 'analytics', 'shadow comparison', 'build_signal_regret_log_v1.py']`, `notes = po3_session_bias column added Session 13 (ENH-75).` | `docs/registers/merdian_reference.json:1235` (`tables.signal_snapshots`) | newest dated element in the entry is **Session 13 (ENH-75)** |
| w | `**Proposed gate.** `signal_snapshots` writer in `build_trade_signal_local.py` skips BEAR_FVG signals when a BEAR_OB has fired within the last 90 minutes for the same symbol.` | `docs/registers/MERDIAN_Enhancement_Register.md:502` | Enhancement Register `Last updated | 2026-07-04→07 (Session 65 …)` (`:12`) |
| x | `ENH-88 | … **COMPLETE (SHIPPED 2026-05-10 Session 26)** — `build_trade_signal_local.py` ENH88_LOOKBACK_MIN=90; commit `8407169`` | `docs/registers/MERDIAN_Enhancement_Register.md:124` | **2026-05-10, Session 26** |
| y | `**What customers receive:** action (BUY_PE / BUY_CE / DO_NOTHING), confidence_score, trade_allowed, gamma_regime, breadth_regime, momentum_alignment, reasons array.` (ENH signal-API proposal) | `docs/registers/MERDIAN_Enhancement_Register.md:931` | proposal, not a status; Register last updated Session 65 |
| z | `| **What is still wrong** | `vix_percentile` and `vix_percentile_regime` are written to `volatility_snapshots` and `signal_snapshots` every cycle and are surfaced by `measurement_health_snapshot_local.py`.` | `docs/registers/tech_debt.md`, entry **TD-S70-NEW-4**, row `**What is still wrong**` (at line 2635 on read, cited by entry ID per the newest-first-register rule) | tech_debt is prepend-ordered; file last commit **2026-11-21**; the entry is **S70** and does not date itself on this row |

**`signal_v4`.** The only occurrences found are `docs/session_notes/session_log_prepend_20260421.md:84`
(`OI-23 — MERDIAN_SIGNAL_V4 docstring/code drift`), `docs/registers/MERDIAN_Enhancement_Register.md:1722`
(`infer_direction_bias_v4(momentum_direction)` … `under V4`) and ADR-019 D1's "rebuild it against
`signal_v4` at the next signal-architecture change". **No document states that `signal_v4` exists as a
built artefact.** NOT ESTABLISHED.

**"MERIDIAN is no longer a Buy CE / Buy PE generator" / "is more than".** No such statement was found
in `docs/` or `CLAUDE.md` in `~/meridian-engine`. **NOT ESTABLISHED.**

### 1.2 Any amendment, supersession or narrowing of ADR-007

`docs/decisions/ADR-007-v18f-ict-pivot.md:5` reads `| **Status** | Accepted (retroactive) |`. The file
contains no Amendment section. `docs/decisions/MERDIAN_Decision_Index.md` carries `[SUPERSEDED by …]`
annotations on exactly two rows — `:58` ADR-014 and `:65` ADR-002 — and **not on the ADR-007 row
(`:64`)**. The Index's own rule (`:172`) is *"Prepend-only. Do not edit existing rows except to add
`[SUPERSEDED by ADR-NNN]` annotations."*

ADR-007 is narrowed in one direction by a later dated statement that does not use the word supersede:
`docs/registers/MERDIAN_Assumption_Register.md:213` (**D.9.1, REFUTED S26**) and `:351` (**D.13.4,
Session 30**), the latter stating the LONG_GAMMA block inverts the edge direction on the live cohort.
Whether those refutations amend ADR-007 is **NOT ESTABLISHED** — no document says so.

### 1.3 The System Map's sections, as written

`docs/registers/MERDIAN_System_Map.md:57` (file inventory row):

> `build_trade_signal_local.py` … `signal_snapshots` … "ACTIVE — 6 ENH-35 changes applied (ADR-007 codification) + 4 ICT columns"

`docs/registers/MERDIAN_System_Map.md:180` (table inventory row):

> `| `signal_snapshots` | `build_trade_signal_local.py` | outcome engine, analytics, shadow comparison, regret log builder, `merdian_signal_dashboard.py` | LIVE — primary decision record. ICT …`

`docs/registers/MERDIAN_System_Map.md:255` (change row):

> `| `build_trade_signal_local.py` (Local) | Two patches in same file this session. **ENH-88 deploy** (`patch_s26_enh88_deploy.py`): adds `ENH88_LOOKBACK_MIN: int = 90` + `_has_recent_bull_ob(`…`

`docs/registers/MERDIAN_System_Map.md:599` (replay row):

> `| `replay_build_trade_signal.py` | Mirror of `build_trade_signal_local.py`; ALL gates preserved exactly (ENH-53/55/76/77/78, DTE, VIX-elevated, power-hour using `replay_ts.astimezone(IST).h`…

`docs/registers/MERDIAN_System_Map.md:797`:

> `**Signal orphans (ADR-019):** `shadow_signal_snapshots_v3` / `iv_context_snapshots` RETAINED-PENDING-REHOME; `options_flow_snapshots` RETAINED-DORMANT. None retired.`

§S76 (`:1399`–`:1516`) is the newest System Map section that addresses the signal path; its heading and
footer are quoted at 1.1 c and 1.1 a. No §S77–§S106 section of the System Map mentions
`build_trade_signal_local.py` or `signal_snapshots`.

### 1.4 The NEWEST dated statement on whether the path is live / legacy / shadow-only / display-only

Two statements are in conflict, and neither is dated later than the other in its own text. Both are
listed, as instructed.

1. **"LIVE — primary decision record"** — `docs/registers/MERDIAN_System_Map.md:180`. The System Map's
   newest dated signal-path content is **Session 76, 2026-09-09/10** (`:1399`, `:1516`); this row itself
   carries no date. File last commit 2026-11-21.
2. **"Shadow signals" on AWS / "Step 9 — production signals" on Local** —
   `docs/registers/MERDIAN_Deployment_Topology.md:204`, §4. Row carries no date; document established
   2026-05-09 (Session 23); file last commit 2026-11-21. The same document records at `:11` that Local
   is the other column, and ADR-019 (`:11` of that ADR, 2026-06-22) states the S49 Local-disable
   **"did not include the signal layer"**.

Statement 2 is contradicted by the code as it stands on this box: `build_trade_signal_local.py` accepts
a single positional symbol argument and no shadow flag (`:1258`, `:1265`), and inserts into the live
relation (`:1253` `SUPABASE.table("signal_snapshots").insert(row).execute()`), while the AWS crontab
runs it through `run_merdian_shadow_runner_aws.py` (lines 13 and 69). **Reported as found; not
reconciled here.**

A third, narrower reading is `docs/registers/MERDIAN_Enhancement_Register.md:931`, which describes a
*proposed* external signal API — a proposal, not a status.

**CURRENT.md.** `docs/session_notes/CURRENT.md`'s newest block is **S106, Thursday 2026-11-05 →
Saturday 2026-11-21**. Its only occurrence of "signal" is line 123, about the tape flow. It says
**nothing** about the Buy CE / Buy PE signal path. So the newest *session-state* document is silent:
**NOT ESTABLISHED** from CURRENT.md.

### 1.5 The Decision Index ADR-007 row vs "LONG_GAMMA / NO_FLIP gates preserved"

The row, verbatim (`docs/decisions/MERDIAN_Decision_Index.md:64`, truncated at the Evidence column):

> `| **ADR-007** | 2026-04-11/12 (decided) · 2026-05-09 (documented) | V18F ICT signal architecture pivot | ICT pattern detection becomes primary signal trigger; Kelly tier sizing replaces uniform confidence-based sizing; LONG_GAMMA / NO_FLIP gates preserved; CONFLICT terminal rule lifted; VIX>20 gate removed; MIN_CONFIDENCE 60→40; confidence-score becomes adjustment layer; T+30m exit confirmed. | Exp 15: pure ICT 86–94% standalone WR on OB patterns. Exp 17/19: LONG_GAMMA symmetric block correct (47.7% WR — below rand…`

**It does not differ.** The phrase *"LONG_GAMMA / NO_FLIP gates preserved"* appears in the row verbatim,
and the row carries no `[SUPERSEDED …]` annotation. The Index's maintenance line (`:172`) reads
`Last maintenance: **Session 104, 2026-11-04 — ADRs_NEW=0 · ADRs_AMENDED=0 · no row added…**`, and
`git log -1 --format=%cs` on the file returns **2026-11-04**.

---

## PART 2 — the code

### 2.1 Readers of `signal_snapshots`

Production-path files only. Excluded by the task's conditions: `scratch/`, `docs/`, `tests/`,
`replay/` and backfills; also excluded are the one-off `fix_*.py` / `s30_*.py` / `s31_*.py`
patch-and-diagnostic scripts, the `*.phase_*_checkpoint.py` / `*_BACKUP.py` frozen copies, and
`sql/` DDL (the `GRANT` in `sql/2026-11-03_s104_marketview_ro_role.sql:23` is noted at 2.3).

| file:line | what it reads | what it does with `trade_allowed` / `action` / `confidence` |
|---|---|---|
| `merdian_pipeline_alert_daemon.py:343-355` | `id,ts,symbol,action,trade_allowed,confidence_score,direction_bias,gamma_regime,breadth_regime,spot,atm_strike,dte,expiry_date` | Filters `.in_("action", list(SIGNAL_ALERT_ACTIONS))` and `.eq("trade_allowed", True)` (`:350-351`); the docstring `:336-337` says *"with action!=DO_NOTHING AND trade_allowed=true"*. Sends a Telegram alert. Also `:190` reads `MAX(ts)` for the watermark. |
| `merdian_trade_logger.py:49-57` | `ts,action,trade_allowed,atm_strike,expiry_date,dte,atm_iv_avg,spot,ict_tier,ict_lots_t1,ict_lots_t2,ict_lots_t3,confidence_score` | `:171-174` gates on `action == "DO_NOTHING"` only; `:182` `opt_type = "PE" if action == "BUY_PE" else "CE"`; `:66-69` `get_active_lots` sizes from `ict_tier` → `ict_lots_t1/t2/t3`; `:185` reads `confidence_score` for display (`:190`). **`trade_allowed` is selected and never read after selection** — reported as found. Writes `trade_log` (`entry_mode "MANUAL"`, `:90`) + `exit_alerts`. |
| `merdian_signal_dashboard.py:75`, `:97` | latest `signal_snapshots` row(s) | `:190` comment: *"on BUY_PE signals. signal_snapshots.action is the source of truth."* Renders the live signal table; carries the LOG TRADE button per Topology `:135`. |
| `merdian_live_dashboard.py:437` | `created_at,action,confidence_score,trade_allowed,ict_pattern,ict_tier,ict_size_mult,ict_mtf_context` (`limit=1`) | Display only — renders the latest row. |
| `generate_pine_overlay.py:539-543` | `spot` only | Fallback spot anchor. `:455-467` records *"S69-HARDENING: spot anchor moved off signal_snapshots … signal_snapshots is retained as a logged fallback so the generator degrades rather than hard-fails."* Does not read action/trade_allowed/confidence. |
| `scripts/eod_health_check.py:129` | row count + `ts` per `symbol` | `("signal_snapshots", "ts", "symbol", 60)` in the `COMPUTE` universe — a per-symbol daily-count and parity check (`PARITY_TOL = 4`, `:133`). Does not read action/trade_allowed/confidence. |
| `merdian_daily_audit.py:94`, `:380-386` | row count | `"signal_snapshots_min": 140` (`:94`); `:380` *"Audit market_state_snapshots and signal_snapshots."* Count only. |
| `gamma_engine_health_check.py:27,36,45,271,398-414` | latest `ts` per symbol | Stage freshness/lag; `:36` maps it to stage name `"signal"`. Count/timestamp only. |
| `gamma_engine_alert_check.py:48` | latest row | `_get_latest_row(sb, "signal_snapshots", symbol)`. |
| `inspect_signal_freshness_local.py:43` | latest row | `_get_latest_row(sb, "signal_snapshots", symbol)`. |
| `premium_outcome_writer.py:838-861` | rows with `{"action": "neq.DO_NOTHING"}` | Uses `action` as the inclusion filter only; builds `signal_premium_outcomes` rows (`:539`). Does **not** filter on `trade_allowed`. |
| `build_signal_outcomes_local.py:10` | `SOURCE_TABLE = "signal_snapshots"` | Outcome labelling. |
| `label_signal_outcomes_local.py:111` | `table="signal_snapshots"` | Outcome labelling. |
| `build_signal_regret_log_v1.py:88-100` | full rows via REST | Writes `signal_regret_log`. |
| `build_signal_market_path_audit_v1.py:167` | `table="signal_snapshots"` | Market-path audit rows. |
| `build_signal_outcome_audit_local.py:289` | `table="signal_snapshots"` | Outcome audit. |
| `build_option_atm_snapshots_v1.py:14` | `select=id,symbol,signal_ts,spot_price&order=id.asc` | ATM snapshot build. |
| `build_option_execution_snapshots_v1.py:155` | `table="signal_snapshots"` | Execution snapshots. |
| `build_option_execution_outcomes_v1.py:193` | `table="signal_snapshots"` | Execution outcomes. |
| `ingest_option_execution_price_history_v1.py:172` | `table="signal_snapshots"` | Price-history ingest. |
| `build_shadow_signal_v3_local.py:382` | `fetch_latest_row("signal_snapshots", symbol)` | Shadow-vs-live comparison input. |
| `evaluate_shadow_vs_live.py:68` | `"signal_snapshots"` | Shadow-vs-live evaluation. |
| `gamma_engine_telemetry_logger.py:420` | `"signal_snapshots": "created_at"` | Telemetry timestamp-column map. |
| `stage2_db_contract.py:114` | name in the contract list | Pre-write contract check; imported only by `run_preflight.py`. |
| `build_trade_signal_local.py:409` | its own table, `BULL_OB` lookback | ENH-88 helper `:390` *"True if any BULL_OB signal_snapshots row exists for `symbol`"*. This is the writer reading itself. |

### 2.2 Which of those are scheduled

Measured on this box: `crontab -l` (AWS, 2026-11-22) and `systemctl list-units --type=service --all`.

**Scheduled:**

| file | schedule |
|---|---|
| `build_trade_signal_local.py` (writer; self-reader at `:409`) | crontab line 13 `*/5 03-09 * * 1-5` and line 69 `0,5,10 10 * * 1-5`, both `python3 run_merdian_shadow_runner_aws.py`, which invokes `["python3", "build_trade_signal_local.py", "NIFTY"]` and `… "SENSEX"` (`run_merdian_shadow_runner_aws.py:444`, `:449`) |
| `generate_pine_overlay.py` | crontab line 55 `52 10 * * 1-5` |
| `scripts/eod_health_check.py` | crontab line 62 `45 0 * * 2-6 … --date prev` |

**Not scheduled on this box** — absent from `crontab -l`, no systemd unit, and not present in `ps`:
`merdian_pipeline_alert_daemon.py`, `merdian_trade_logger.py`, `merdian_signal_dashboard.py`,
`merdian_live_dashboard.py`, `merdian_daily_audit.py`, `gamma_engine_health_check.py`,
`gamma_engine_alert_check.py`, `inspect_signal_freshness_local.py`, `premium_outcome_writer.py`,
`build_signal_outcomes_local.py`, `label_signal_outcomes_local.py`, `build_signal_regret_log_v1.py`,
`build_signal_market_path_audit_v1.py`, `build_signal_outcome_audit_local.py`,
`build_option_atm_snapshots_v1.py`, `build_option_execution_snapshots_v1.py`,
`build_option_execution_outcomes_v1.py`, `ingest_option_execution_price_history_v1.py`,
`build_shadow_signal_v3_local.py`, `evaluate_shadow_vs_live.py`,
`gamma_engine_telemetry_logger.py`, `stage2_db_contract.py` / `run_preflight.py`.

Two documented claims conflict with that measurement and are reported as found:

- `docs/registers/merdian_reference.json:1725` gives `merdian_pipeline_alert_daemon.py` status
  `RUNNING (PID 19636 as of 2026-04-26 14:17 IST)` and `docs/registers/MERDIAN_Deployment_Topology.md:134`
  reads `Currently running PID 19636`. No such process is running now, and the daemon is not in cron
  or systemd.
- `docs/registers/MERDIAN_Deployment_Topology.md:137`, `:135` place `merdian_trade_logger.py` and
  `merdian_signal_dashboard.py` under `## §2 — Local-only scripts` (`:122`). **Whether the Local
  Windows Task Scheduler currently runs them is NOT ESTABLISHED** — the Local scheduler cannot be read
  from this box.

Two expectations about the same relation also disagree with each other, independent of scheduling:
`scripts/eod_health_check.py:129` expects **≥ 60 rows per symbol per day**, while
`generate_pine_overlay.py:458-459` records *"build_trade_signal_local.py records ~2 invocations on a
live day against ~300 for every other cycle script, because the signal engine gates hard."* Reported
as found; not reconciled here.

### 2.3 Does any code path place or size an order from `signal_snapshots`?

**Sizing: yes.** `merdian_trade_logger.py:66-69` (`get_active_lots`) takes `ict_tier` and
`ict_lots_t1/t2/t3` straight from the `signal_snapshots` row (`:49-57`) and writes `lots` into
`trade_log` (`:87`). It is an operator-invoked CLI / `POST /log_trade` endpoint (`:8`, `:11-13`),
`entry_mode "MANUAL"` (`:90`), and it is **not scheduled** (2.2).

**Placing: yes, but not from `signal_snapshots`.** `merdian_order_placer.py` is the only order path:

> `Places and squares off NSE/BSE options orders via Dhan Trading API.` (`:5`)
> `POST /place_order?symbol=NIFTY&trade_log_id=<uuid>` (`:16`)

It keys on `trade_log_id`, not on a `signal_snapshots` row, and the string `signal_snapshots` does not
occur in it. It is an HTTP server on port 8767 (`:22`, `:65`) and is **absent from `crontab -l`, from
systemd, and from `ps`**; it is also **not present in `docs/registers/merdian_reference.json` `files`**.

So the chain from a signal to a placed order is:
`signal_snapshots` → (operator button / CLI) `merdian_trade_logger.py` → `trade_log` →
(operator button) `merdian_order_placer.py` → Dhan. **No scheduled process traverses it**, and
**no code path reads `signal_snapshots` and places an order without an operator step** on the
evidence read here.

`sql/2026-11-03_s104_marketview_ro_role.sql:23` grants `SELECT` on `public.signal_snapshots` to the
Marketview read-only role. What the Board does with it is **NOT ESTABLISHED** — `~/meridian-connect`
was out of scope for this task.

---

## NOT ESTABLISHED — collected

1. Whether `signal_v4` exists as a built artefact.
2. Any statement that MERIDIAN is no longer, or is more than, a Buy CE / Buy PE generator.
3. Whether the S26/S30 refutations (D.9.1, D.13.4) amend ADR-007 — no document says so, and the
   Decision Index carries no `[SUPERSEDED]` annotation on the ADR-007 row.
4. Which of "LIVE — primary decision record" (System Map `:180`) and "Shadow signals" on AWS
   (Topology `:204`) is current — neither statement is dated later than the other.
5. Whether the Local Windows Task Scheduler still runs `merdian_signal_dashboard.py`,
   `merdian_trade_logger.py` or `build_trade_signal_local.py` on Local.
6. What the Marketview Board does with its `SELECT` grant on `signal_snapshots`.
7. Whether `signal_snapshots` currently receives rows — no database read was permitted in this task.
