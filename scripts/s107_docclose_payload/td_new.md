### TD-PIN2-NEW-1 (S3 priority) — where the stored gamma's precision comes from has not been read against `raw`

| Field | Value |
|---|---|
| **Priority** | **S3.** A precision question on a stored input; no figure is known to be wrong. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 4) |
| **Component** | `gex_strike_snapshots.gamma_call` / `gamma_put`; `option_chain_snapshots.raw` |
| **Measured** | Not measured. The pin lane's trace could not say whether the stored gamma carries the vendor's precision or a rounded one. |
| **Proper fix** | One read of `raw` against the stored columns on a sample of legs; record the result in the Data Inventory. |
| **Home** | Board-pin lane; engine-owned table. Source: `docs/research/pin_proof/MR_PIN2_close_inputs.md` §5 row 4; `docs/research/pin_proof/fix/proposal/trace.md`. |
| **Status** | **OPEN (VERIFY).** |

### TD-PIN2-NEW-2 (S3 priority) — the Board's "Gross |Gamma|" tile is the sum of absolute net exposure per strike, not gross exposure

| Field | Value |
|---|---|
| **Priority** | **S3.** The number is computed correctly; the label names a different quantity. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 5) |
| **Component** | Board (`meridian-connect`), the "Gross \|Gamma\|" tile; `v_gex_abs_exposure` |
| **Measured** | The tile shows Σ abs(net `gex_cr` per strike). Gross exposure is γ × (OI call + OI put) per strike, which the V1 tables do not store (`gex_run_v2.gross_band_cr` does, ADR-033). |
| **Proper fix** | The operator approves any relabel; a TD does not change Board wording. Decide with the Board's move to V2 figures by family (operator ruling 2026-11-26). |
| **Home** | Board-pin lane; Board is engine-owned. Source: `MR_PIN2_close_inputs.md` §5 row 5; `pin_fix_scope_DRAFT_2026-11-21.md` §6. |
| **Status** | **OPEN.** |

### TD-PIN2-NEW-3 (S3 priority) — "Top-strike share" on the Board is net-based (`hhi_net` → `conc_top1_share`)

| Field | Value |
|---|---|
| **Priority** | **S3.** Same class as TD-PIN2-NEW-2: a correct number under a name that does not say "net". |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 6) |
| **Component** | `v_gex_concentration.hhi_net`; `gex_cycle_history.conc_top1_share`; the Board's "Top-strike share" line |
| **Measured** | `hhi_net` feeds `conc_top1_share` and is the top strike's share of absolute **net** exposure. From 2026-11-25 the Pin tile above it shows a **gross** share over the 5 % band, so the two shares on the Board are on different bases (ADR-033 §4). |
| **Proper fix** | Label the basis on the Board, or move the line with the concentration family when the Board moves to V2 figures. |
| **Home** | Board-pin lane. Source: `MR_PIN2_close_inputs.md` §5 row 6. Cross-ref: the **NOTE — 2026-10-03** at the head of Active debt (`hhi_net` is a top-1 share, not a Herfindahl). |
| **Status** | **OPEN.** |

### TD-PIN2-NEW-4 (S3 priority) — `latest_gamma_walls` is a live view that no file in `sql/` creates

| Field | Value |
|---|---|
| **Priority** | **S3.** The live definition exists only in the database. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 7) |
| **Component** | `public.latest_gamma_walls` |
| **Measured** | Catalog read 2026-11-23: a view in `public`, owner `postgres`, ACL `authenticated=rm`, `service_role=arwdDxtm`, `merdian_ro=r`, no `anon`. Git names it only in `sql/2026-11-03_s104_anon_shrink_ROLLBACK.sql`, the Data Inventory and this file. It reads `option_chain_snapshots.gamma` per leg directly; no reader was found in the engine repo or the Board source (ADR-033 §5). |
| **Proper fix** | One `pg_get_viewdef('public.latest_gamma_walls'::regclass, true)` read, then a file under `sql/` (the S101 live-capture pattern); or drop it if the operator rules it unused. |
| **Home** | Engine. Source: `docs/registers/intake/I002.md` §4a. Same class as TD-S101-NEW-2. |
| **Status** | **OPEN.** |

### TD-PIN2-NEW-5 (S3 priority) — walls outside the corridor on about one run in four; frozen-OI runs; 2026-08-25 runs with no chain legs

| Field | Value |
|---|---|
| **Priority** | **S3.** Three observations from one study, none re-counted by the engine. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 8) |
| **Component** | `gex_strike_snapshots`; `v_gex_strike_walls`; `option_chain_snapshots` |
| **Measured** | As reported by the pin lane: (a) the OI walls fall outside the corridor on about one run in four; (b) on runs where OI has not updated, any pin moves with spot alone; (c) the runs of 2026-08-25 have no chain legs. Related, measured at the S107 backfill: on 2026-08-27 the OI totals do not change until the 09:20 run, and the 08:35–08:45 runs are identical in every figure (`docs/research/pin_proof/b2_backfill_check_result_2026-11-25.md`). |
| **Proper fix** | Re-run the count for (a); for (b) decide whether pre-open runs should be marked as carrying the previous session's OI; for (c) read the day. Split this entry if the three need different fixes. |
| **Home** | Board-pin lane; engine-owned tables. Source: `MR_PIN2_close_inputs.md` §5 row 8. |
| **Status** | **OPEN (VERIFY).** |

### TD-PIN2-NEW-6 (S4 priority) — one of the 21 live `v_gex_%` views carries no COMMENT: `v_gex_abs_exposure`

| Field | Value |
|---|---|
| **Priority** | **S4.** Documentation in the catalog. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 9) |
| **Component** | `public.v_gex_abs_exposure` |
| **Measured** | Catalog read 2026-11-23: 20 of the 21 live `v_gex_%` views carry a comment; `v_gex_abs_exposure` does not (all seven `_1pct` wrappers carry the 284-character comment). Views outside the `v_gex_%` pattern were not read. |
| **Proper fix** | A `COMMENT ON VIEW` stating the quantity and its basis (see TD-PIN2-NEW-2). A second read if the claim is meant to cover `v_pin_board` and the like. |
| **Home** | Engine. Source: `docs/registers/intake/I002.md` §4a. Same class as TD-S81-NEW-5. |
| **Status** | **OPEN.** |

### TD-PIN2-NEW-7 (S3 priority) — why the vendor returns zero gamma on in-the-money legs, and whether a leg's gamma and OI are the same moment, are both unknown

| Field | Value |
|---|---|
| **Priority** | **S3.** Both questions bound how far any per-strike gamma figure can be trusted; neither can be answered from our side. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 10) |
| **Component** | Vendor option-chain feed; `ingest_option_chain_local.py` |
| **Measured** | The gamma field is never missing; "0.0" is present on legs away from the money (AR §D.61.1). Cause not known. |
| **Proper fix** | A vendor ticket with three example legs. Feeds the greeks / forward study (STREAMS X2). |
| **Home** | Board-pin lane; engine-owned ingest. Source: `docs/research/pin_proof/gamma_pipeline_audit_result_2026-11-22.md` (limits). |
| **Status** | **OPEN (VERIFY).** |

### TD-PIN2-NEW-8 (S3 priority) — `eod_health_check` expects at least 60 signal rows a day; the reads show about 2

| Field | Value |
|---|---|
| **Priority** | **S3.** A check whose expectation no longer matches what the path produces either fails every day or is being ignored. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 12) |
| **Component** | `scripts/eod_health_check.py`; the signal path |
| **Measured** | As reported by the pin lane's status read (`docs/research/pin_proof/fix/proposal/signal_path_status.md`). Not re-read by the engine. |
| **Proper fix** | Read the check's result for the last five sessions; then either correct the expectation or record why the path writes so few rows. Decide together with TD-PIN2-NEW-10. |
| **Home** | Engine. Source: `MR_PIN2_close_inputs.md` §5 row 12. |
| **Status** | **OPEN (VERIFY).** |

### TD-PIN2-NEW-9 (S4 priority) — `merdian_order_placer.py` has no entry under `files` in `merdian_reference.json`

| Field | Value |
|---|---|
| **Priority** | **S4.** A lookup that the session-start rule says is authoritative returns nothing for a script that exists on the box. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 13) |
| **Component** | `docs/registers/merdian_reference.json` → `files` |
| **Measured** | Read at this close on `6a69dbe`: the name occurs in prose in six places and has no `files` key. Box reads of 2026-11-24/25: the script is present, not scheduled and not running. |
| **Proper fix** | Add the entry with its measured state (present, unscheduled, not running), or record it as retired if the operator rules so. |
| **Home** | Engine. Source: `MR_PIN2_close_inputs.md` §5 row 13. |
| **Status** | **OPEN.** |

### TD-PIN2-NEW-10 (S3 priority) — the signal path still runs and nothing found acts on it; whether it should still run every cycle is undecided

| Field | Value |
|---|---|
| **Priority** | **S3.** A builder that runs every cycle for no consumer costs box time and keeps a gate looking current. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 14) |
| **Component** | `build_trade_signal_local.py`; `signal_snapshots.trade_allowed`; `build_shadow_signal_v3`; the alert daemon, signal dashboard, trade logger, order placer |
| **Measured** | Reads of 2026-11-24/25 (AR §D.61.3): the builder runs from the box crontab and writes `trade_allowed` each cycle; the alert daemon, dashboard, trade logger and order placer are on the box, unscheduled and not running; the alert daemon last ran 2026-06-11; all 19 Windows scheduled tasks are disabled. **Still unknown:** how `build_shadow_signal_v3` is scheduled, whether a `signal_v4` exists, and whether the builder should keep running. |
| **Proper fix** | The operator decides whether the builder keeps running. If not: remove its crontab line in an S90-J window and mark the consumers retired in the registers. |
| **Home** | Engine. Source: `MR_PIN2_close_inputs.md` §5 row 14; `docs/research/pin_proof/advisor_pack_flip_2026-11-25.md`. |
| **Status** | **OPEN (DECIDE).** |

### TD-PIN2-NEW-11 (S3 priority) — the Board's "regime" string and the two flips: which object each tile reads is not confirmed in one place

| Field | Value |
|---|---|
| **Priority** | **S3.** Two levels called "flip" exist; only one is shown, and the System Map does not say which. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2, intake I-002 row 15) |
| **Component** | Board; `v_gex_repriced_flip` (ENH-131); `gamma_metrics.flip_level`, `gamma_metrics.regime`; `gex_cycle_history.gamma_regime` |
| **Measured** | The Board Flip is `v_gex_repriced_flip.flip`; the engine's `flip_level` is not shown. Whether the Board's "regime" string is `gamma_metrics.regime` is not confirmed. The effect of the vendor's per-leg IV on the repriced flip is unmeasured. From 2026-11-25 the Board labels the Flip "experimental" and the regime "legacy, unvalidated". |
| **Proper fix** | One System Map row per Board tile naming its source column (the Board source search of 2026-11-24/25 in the advisor pack is the starting list). Feeds the greeks / forward study. |
| **Home** | Board-pin lane; Board is engine-owned. Source: `MR_PIN2_close_inputs.md` §5 row 15. See TD-PIN3-NEW-2. |
| **Status** | **OPEN (VERIFY).** |

### TD-PIN2-NEW-12 (S2 priority) — the production box has no swap and 1,910 MB; one stray process took 460 MB, and `ulimit -v` did not protect the box on 2026-11-21

| Field | Value |
|---|---|
| **Priority** | **S2.** The box runs capture, compute, the Board and the tape writer; a hang stops all four. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN2 intake I-002 row 16 and MR-OFL9 intake row 7) |
| **Component** | Production box `ip-172-31-35-90` (t3.small) |
| **Measured** | 2026-11-21: an out-of-memory hang during lane work; `ulimit -v` limits one shell's address space, not the box. 2026-11-24 (`ps`, `free -m`, pasted by the operator): 1,910 MB, no swap; a stray `claude --resume` (pid 960) held 460 MB; after it and a tmux session were killed, used 238 MB and available 1,474 MB. The tape 2b unit is ruled `MemoryMax=900M` (R8-J). No resize (operator, 2026-11-24). |
| **Proper fix** | Operator's call between: a memory budget per lane written into STREAMS X9 with a pre-check before any heavy job; a small swap file as a safety margin; or a resize. A standing check for stray interactive processes before market hours. |
| **Home** | Engine (Topology). Source: `MR_PIN2_close_inputs.md` §5 row 16; `claude/ofl/MR_OFL9_close_inputs.md` §1, §4 row 7. No duplicate among TD-S106-NEW-1…10 (checked at filing). |
| **Status** | **OPEN.** |

### TD-OFL9-NEW-1 (S3 priority) — a NUL byte crashes the tape code on Python 3.10

| Field | Value |
|---|---|
| **Priority** | **S3.** The production box runs Python 3.10.12. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-OFL9, intake I-003) |
| **Component** | `services/tape_live/` (order-flow lane code, branch `tape/live-l2`) |
| **Measured** | Reported in the MR-OFL9 close inputs as a one-line candidate; the file and input are in the lane's CC report, not in this register. |
| **Proper fix** | The order-flow lane reproduces it, fixes it and adds a guard. |
| **Home** | Order-flow lane. Source: `claude/ofl/MR_OFL9_close_inputs.md` §4. |
| **Status** | **OPEN (VERIFY).** |

### TD-OFL9-NEW-2 (S3 priority) — the 35 tape guards use 631 MB RSS against `ulimit -v 700000`

| Field | Value |
|---|---|
| **Priority** | **S3.** 69 MB of headroom under the limit every lane runs under on the box. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-OFL9, intake I-003) |
| **Component** | The tape guard suite; CLAUDE.md rule 23 |
| **Measured** | 631 MB RSS, as reported. Box suite at `d1f9ba2`: exit 0, 35/35 guards, 194/194 ×5 plus 1 skipped, elapsed `9:53:39` as printed. |
| **Proper fix** | Split the guard run, or lower its peak; do not raise the limit (see TD-PIN2-NEW-12). |
| **Home** | Order-flow lane. Source: `claude/ofl/MR_OFL9_close_inputs.md` §1, §4. |
| **Status** | **OPEN (VERIFY).** |

### TD-OFL9-NEW-3 (S3 priority) — the `_*.py` rule in `.gitignore` swallows `services/tape_live/__init__.py`

| Field | Value |
|---|---|
| **Priority** | **S3.** A package's `__init__.py` is silently left out of a commit. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-OFL9, intake I-003) |
| **Component** | Root `.gitignore` line 107 (`_*.py`) |
| **Measured** | Same rule and same effect as **TD-S101-NEW-6** (`merdian_compute/__init__.py`); this is its second occurrence. In S107 a third rule of the same file, `/apply_*.py`, dropped the V2 writer-hook patcher from commit `a9b38bc` (it was renamed `scripts/gamma_v2_writer_hook_patch.py`). |
| **Proper fix** | The fix named in TD-S101-NEW-6 (narrow the pattern, or negate `__init__.py`). Close both together. |
| **Home** | Engine (`.gitignore` is engine-owned). Source: `claude/ofl/MR_OFL9_close_inputs.md` §4. |
| **Status** | **OPEN — duplicate in cause of TD-S101-NEW-6; kept as the lane's data point.** |

### TD-OFL9-NEW-4 (S4 priority) — the default of `--rss-cap-mb` in the tape live runner

| Field | Value |
|---|---|
| **Priority** | **S4.** The installed 2b unit passes `--rss-cap-mb 800` explicitly. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-OFL9, intake I-003) |
| **Component** | `services/tape_live` `cli live` |
| **Measured** | Listed by the lane as a candidate without a figure. |
| **Proper fix** | The lane states the default and whether it is safe on a 1,910 MB box. |
| **Home** | Order-flow lane. Source: `claude/ofl/MR_OFL9_close_inputs.md` §4. |
| **Status** | **OPEN (VERIFY).** |

### TD-OFL9-NEW-5 (S3 priority) — a `TypeError` at line 3452 of a tape file named only in the lane's CC report

| Field | Value |
|---|---|
| **Priority** | **S3.** Unlocated: the close inputs did not retain the file name. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-OFL9, intake I-003) |
| **Component** | Order-flow lane code (file not recorded) |
| **Measured** | Not measured here. |
| **Proper fix** | MR-OFL10 names the file from its CC report, then fixes or closes this. |
| **Home** | Order-flow lane. Source: `claude/ofl/MR_OFL9_close_inputs.md` §4. |
| **Status** | **OPEN (VERIFY).** |

### TD-OFL9-NEW-6 (S4 priority) — the live-2b-stop header comment counts the wrong number of items

| Field | Value |
|---|---|
| **Priority** | **S4.** A comment. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-OFL9, intake I-003) |
| **Component** | Order-flow lane code |
| **Measured** | As reported. |
| **Proper fix** | Correct the comment in a commit after the first live 2b day (a doc commit moves the code pin). |
| **Home** | Order-flow lane. Source: `claude/ofl/MR_OFL9_close_inputs.md` §4. |
| **Status** | **OPEN.** |

### TD-OFL9-NEW-7 (S3 priority) — the tape install note has no steps for installing or checking the 2b unit

| Field | Value |
|---|---|
| **Priority** | **S3.** The first live 2b day (earliest Mon 2026-11-30) installs a unit the note does not cover. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-OFL9, intake I-003) |
| **Component** | The tape install note §11; `docs/tape/L2_live_runner_2b.service.template` |
| **Measured** | The note has no 2b install, `cli live --check` or `cli db-literal-check` step. |
| **Proper fix** | Add them after the first live 2b day, from the commands actually run. |
| **Home** | Order-flow lane. Source: `claude/ofl/MR_OFL9_close_inputs.md` §2, §4. |
| **Status** | **OPEN.** |

### TD-OFL9-NEW-8 (S4 priority) — the comment at `ddl.py:81`

| Field | Value |
|---|---|
| **Priority** | **S4.** A comment, held deliberately. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-OFL9, intake I-003) |
| **Component** | `services/tape_live` `ddl.py:81` |
| **Measured** | As reported. |
| **Proper fix** | Change it in a commit after the first live 2b day. |
| **Home** | Order-flow lane. Source: `claude/ofl/MR_OFL9_close_inputs.md` §2, §4. |
| **Status** | **OPEN.** |

### TD-PIN3-NEW-1 (S3 priority) — the stored gamma runs per day are not a fixed set, and three of their features are unexplained

| Field | Value |
|---|---|
| **Priority** | **S3.** Any study or check that assumes a fixed number of runs a day is wrong on most days. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN3, intake I-003) |
| **Component** | `gex_strike_snapshots`; `gex_run_v2`; the runner's schedule |
| **Measured** | Full stored history, 2026-05-25 → 2026-11-25 (Data Inventory §13): 161 of 247 day-symbols do not have 83 runs; every day from 2026-10-26 has 87 per symbol; a run between 15:21 and 15:39 IST exists on 75 of 123 NIFTY days and 74 of 124 SENSEX days. On 2026-08-27 the eight runs before 09:15 carry the previous session's OI until the 09:20 run. **Unexplained:** why days differ by one or two runs (81, 82, 84), often on one symbol only; why the schedule changed on 2026-10-26; and nine weekdays with no run at all (2026-05-28, 06-03, 06-04, 06-08, 09-14, 10-20, 10-21, 11-10, 11-24), not checked against the exchange holiday list. |
| **Proper fix** | Read the runner's crontab history for 2026-10-26; check the nine dates against `trading_calendar`; decide whether pre-open runs should carry a marker. Studies select runs by clock time, not by count (pin lane, step 9). |
| **Home** | Board-pin lane; engine-owned tables. Source: `docs/research/s107/engine_to_pin_LATEST.md` §4, §6; `docs/research/pin_proof/b2_backfill_check_result_2026-11-25.md`. |
| **Status** | **OPEN (VERIFY).** |

### TD-PIN3-NEW-2 (S3 priority) — the Board Flip drops every leg whose vendor gamma is zero, with its open interest, and has no value on expiry day

| Field | Value |
|---|---|
| **Priority** | **S3.** The one flip the Board shows is not independent of the vendor-gamma gap the V2 work exists to remove. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN3, intake I-003) |
| **Component** | `v_gex_repriced_flip` (ENH-131) |
| **Measured** | The view filters legs with `gamma IS NOT NULL AND gamma <> 0`. The effect on the level is unmeasured. No value at dte 0. Labelled "experimental" on the Board from 2026-11-25. |
| **Proper fix** | The flip replacement study, parked by the operator (ruling R6, 2026-11-25) until the V2 build is done. ENH-135 is the dte-0 mode. |
| **Home** | Board-pin lane; engine-owned view. Source: `docs/research/pin_proof/advisor_pack_flip_2026-11-25.md` §3; ADR-033 §4. |
| **Status** | **OPEN.** |

### TD-PIN3-NEW-3 (S3 priority) — the Pin detail panel quotes a result measured on the earlier net pin, and the "#2" rule and two labels are not in the manual

| Field | Value |
|---|---|
| **Priority** | **S3.** A reader of the panel takes the n = 85 result as a statement about the pin now shown. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-PIN3, intake I-003) |
| **Component** | Board Pin detail panel; `docs/marketview_manual/marketview_user_manual.md` |
| **Measured** | The panel quotes P1 (n = 85) without saying it was measured on the net pin. The rule beside the "#2" net-rank readout and the lines for the two new labels are not in manual v0.6. The panel text was not re-read at this close. |
| **Proper fix** | Authored, not run: `docs/lovable_prompts/s107/lovable_prompt_board_pin_round2_2026-11-25.md` (the caveat first, then the "#2" label), with its own guard and promote and the proxy build settings; manual v0.7 carries the label lines. |
| **Home** | Engine (Board). Source: `docs/research/pin_proof/MR_PIN3_close_inputs.md` §5 row 7. |
| **Status** | **OPEN.** |

### TD-S107-NEW-1 (S2 priority) — a Board guard and promote script written for one round omitted the proxy build settings; staging showed an empty Board and a promote would have emptied live

| Field | Value |
|---|---|
| **Priority** | **S2.** One command from blanking the live Board; caught by the operator looking at staging. |
| **Filed** | 2026-11-26 (Session 107 doc-close) |
| **Component** | `docs/lovable_prompts/s107/mv_lovable_guard_s107_pin.sh`, `mv_promote_s107_pin.sh`; CLAUDE.md rule 26 |
| **Measured** | 2026-11-25 ~17:55 IST: the first versions built without `VITE_SUPABASE_URL=https://marketview.meridianalpha.in VITE_SUPABASE_ANON_KEY=proxy`, required for every Board build since 2026-11-03. Staging showed "no run" on every tile. Revision 2 (in git with this close) sets both, and audits the bundle: project ref absent, no JWT string, own domain present. The first audit was too broad (it matched `*.supabase.co` in library text) and was narrowed. A retention step that would have deleted five backups was disabled. |
| **Proper fix** | One parametrised guard and one promote script for every Board round, with the build settings and the bundle audit in one place, instead of a hand-written pair per round. |
| **Home** | Engine. Source: AR §D.62.3; `docs/research/pin_proof/MR_PIN3_close_inputs.md` §5 row 11. |
| **Status** | **OPEN** — the S107 pair is corrected; the structural fix is owed. |

### TD-S107-NEW-2 (S3 priority) — no `data_contracts` row for the two V2 tables or the two gross-pin views

| Field | Value |
|---|---|
| **Priority** | **S3.** ADR-031: every data product has a contract; these four have none, so no generated check watches them. |
| **Filed** | 2026-11-26 (Session 107 doc-close) |
| **Component** | `data_contracts`; `gex_strike_v2`, `gex_run_v2`, `v_gex_strike_rank_gross`, `v_gex_pin_gross` (and `v_gex_strike_rank`, which had no row on 2026-11-07) |
| **Measured** | Not written: I-002 §4a records what was read of the table (one row per `'<relation>:<scope>'`, 20 columns; existing rows are base tables only). The rows for `gex_strike_snapshots` are the template and were not read out in full. |
| **Proper fix** | Two reads (I-002 §7), then the engine authors the INSERTs and the `product_lineage` edges; the operator applies. |
| **Home** | Engine. Source: `docs/registers/intake/I002.md` §3 item 3, §4a, §7. |
| **Status** | **OPEN.** |

### TD-S107-NEW-3 (S3 priority) — PUBLIC holds grants on `cron`, `net` and `pg_stat_statements` objects in the engine database

| Field | Value |
|---|---|
| **Priority** | **S3 (security).** No exposed path was shown; the grants are wider than anything needs. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-OFL9 intake rows 1 and 2) |
| **Component** | Supabase engine project `kilmcowcikwdhvdxwofi`: `cron.job`, `cron.job_run_details`, `extensions.pg_stat_statements`, `net._http_response`, `net.http_request_queue` |
| **Measured** | Privilege read 2026-11-24 (grantor `supabase_admin`): PUBLIC has SELECT on `cron.job`; SELECT and DELETE on `cron.job_run_details`; SELECT on `pg_stat_statements` and `_info`; all privileges on the two `net` tables and `rwU` on the `net` sequence; USAGE on schema `net`. The `net` tables have RLS off; the `cron` tables have RLS on. |
| **Proper fix** | Operator's decision whether to revoke. Before that: whether a revoke survives a platform upgrade is not known (read after a revoke on a non-production project, or ask the vendor). |
| **Home** | Engine. Source: `claude/ofl/MR_OFL9_close_inputs.md` §3, §4 rows 1–2; AR §D.62.6. |
| **Status** | **OPEN (DECIDE, then VERIFY).** |

### TD-S107-NEW-4 (S3 priority) — on the Windows machine `refresh_dhan_token.py` fails with a vendor message that the refresh method changed

| Field | Value |
|---|---|
| **Priority** | **S3.** The Windows machine generates nothing (Topology §S76.A); the production mint runs on the box at 08:20 IST. The failure matters only if the Windows path is still a fallback. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-S13 intake row 1) |
| **Component** | `refresh_dhan_token.py` on Local Windows |
| **Measured** | 2026-11-23, the operator's paste in the retail chat: a vendor message beginning "We have changed the way dhan token is refreshed - the old way isn't working". The rest of the output is not in any record. |
| **Proper fix** | Read the full output on Local; then either fix the Windows path or record it as retired. Resolve together with CURRENT item "Topology L414" (the second 09:05 schedule). |
| **Home** | Engine. Source: `claude/retail/MR_S13_close_inputs.md` §8 row 1. |
| **Status** | **OPEN (VERIFY).** |

### TD-S107-NEW-5 (S3 priority) — a manual Dhan re-mint after 08:45 IST leaves the retail side on a dead token until its next adopter window

| Field | Value |
|---|---|
| **Priority** | **S3.** Reasoned from the adopter windows, not measured. |
| **Filed** | 2026-11-26 (Session 107 doc-close; origin MR-S13 intake row 2) |
| **Component** | `bin/dhan_login.sh` (E10); the retail adopter windows (06:15 IST Kite, 08:15 IST Dhan, as stated by the retail lane) |
| **Measured** | Not measured. A new mint invalidates the previous token; the retail adopter has already taken the earlier one. |
| **Proper fix** | Confirm on one controlled re-mint outside market hours; then one line in the operations notes saying when a manual re-mint is safe and what to run on the retail box after one. |
| **Home** | Engine. Source: `claude/retail/MR_S13_close_inputs.md` §8 row 2. |
| **Status** | **OPEN (VERIFY).** |

### TD-S107-NEW-6 (S3 priority) — which host and which code version wrote each day's gamma rows is not recorded in any register

| Field | Value |
|---|---|
| **Priority** | **S3.** The pin lane's comparison of V1 against V2 needs it to say whether 8,983 unchecked runs were written by the same code as checked ones. |
| **Filed** | 2026-11-26 (Session 107 doc-close) |
| **Component** | `script_execution_log` (`host`, `git_sha`); Topology (the Local → box cut-over of the gamma writer) |
| **Measured** | In git the row-building code is identical at all ten commits that touched the writer between 2026-05-25 and 2026-11-25 (syntax-tree comparison of eight functions; AR §D.62.5). Not established: what production ran on each date, and the date the production writer moved from the Windows machine to the box. |
| **Proper fix** | One read of `script_execution_log` grouped by `host` and `git_sha` (the statement is in `docs/research/s107/engine_to_pin_LATEST.md` §1.4); record the cut-over date in the Topology. |
| **Home** | Engine. |
| **Status** | **OPEN** — the read is asked of the operator. |

### TD-S107-NEW-7 (S3 priority) — legacy gamma functions are executable by `anon`, `authenticated` and `merdian_ro`, and one SECURITY DEFINER path fills `gamma_metrics` with no caller in the repo

| Field | Value |
|---|---|
| **Priority** | **S3.** Hygiene, not an exposure: the roles hold no INSERT or DELETE on the tables and the functions run with the caller's rights. |
| **Filed** | 2026-11-26 (Session 107 doc-close) |
| **Component** | `backfill_pin_maxpain_runs`, `cleanup_gamma_engine_data`, `compute_gamma_*_for_run`; `insert_option_chain_batch` (SECURITY DEFINER); `insert_option_chain_run` |
| **Measured** | Reads of 2026-11-25, recorded in ADR-033 §5: EXECUTE on the first group is open to the three roles. `insert_option_chain_batch` is callable by `service_role` and fills `gamma_metrics` through `compute_gamma_metrics_for_run`; no caller in the engine repo; the `gamma_metrics` rows of 2026-11-23 all carry the Python builder version. `insert_option_chain_run` is dead (it writes columns that do not exist). |
| **Proper fix** | Revoke EXECUTE from the three roles on the first group; decide whether the two `insert_option_chain_*` functions are dropped. Authored by the engine, applied by the operator, with a privilege read before and after. |
| **Home** | Engine. Source: `docs/decisions/ADR-033-gamma-v2-versioned-isolation.md` §5. |
| **Status** | **OPEN.** |

