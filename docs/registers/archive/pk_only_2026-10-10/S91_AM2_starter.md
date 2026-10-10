# AM-2 (S91) starter — carry the post-close delta of AM-1, then resume the build

You are working on MERIDIAN, the operator's live, solo-built analytics engine for Indian index options (NIFTY, SENSEX). This is **Agentic MERIDIAN Session 2 (AM-2 = S91)**. AM-1 (S90) closed its documentation at `ba8bd33` and then **kept working for another ~24 hours**. Ten engine commits, three Marketview commits and four rulings landed after the close and are **not yet in `CURRENT.md`, `session_log.md`, `tech_debt.md` or the roadmap tracker**. Folding them in is task 1.

## Read first (project knowledge, before asking the operator anything)

1. `CLAUDE.md` (v1.62 + **rule 20**), `CURRENT.md`, `claude/agentic_layer_roadmap_S90.md` (§3 tracker, §11 risk classes incl. **S90-J**), `claude/rulings_s90.md`
2. `claude/ADR-031-spine-contracts-status-provenance-ledger.md`
3. This file, in full. Then `tests/replay/README.md` in the repo.

## Standing rules (unchanged unless stated)

- Never name the parity target's product in docs, prompts, commits or file names; say "the parity target".
- Never read or print `.env` or any credential. The operator loads it in a subshell: `set +u; ( set -a; . ./.env; set +a; <cmd> )`.
- Database read-only via `bin/roq.sh` (`merdian_ro`). **It reads SQL from stdin** (`bin/roq.sh <<'SQL' … SQL`); there is no `-c`. The SQL editor runs as postgres; gated multi-step writes go in ONE `DO` block with a read-back.
- Production changes only by push + `git pull --ff-only` from the operator's terminal. Never write under `~/meridian-engine`.
- **S90-J deploy windows (ruled):** LIVE/capture-path (ingest, runner, writers, crontab, live-table schema) weekdays **16:30 → 07:45 IST**, any time weekends/holidays, with green offline suite + written rollback. Everything else (RO/OFF/SC, Marketview via `/staging/`, docs, views, sidecars) **any time**.
- **Rule 20:** prose/UI/commit prefixes say MERIDIAN; identifiers keep `merdian`/`MERDIAN_` until an ADR renames them.
- Exact commands inline, each SQL in its own block. Large patches go as a **paste file** (gzip+base64, sha256 check, tree-hash check, time guard, offline suite, push, pull) sent with SendUserFile — the operator accepted this pattern.
- At a permission prompt the operator gives a bare option number. Session close is when the operator says so; do not remind. Never mention rest or ending the session.

## 1. What changed after the AM-1 close (fold into the registers)

### Engine commits (`ba8bd33..490b088`, all deployed, crontab = `docs/registers/aws_crontab.txt`)

| Commit | What | Class |
|---|---|---|
| `699398f` | MERDIAN → MERIDIAN in prose/titles/prefixes (89 files); CLAUDE.md rule 20 | docs |
| `16f1378` | **S90-J** ruling in `rulings_s90.md` + roadmap LIVE control; Marketview nginx `/staging/` block in `deploy/nginx/marketview.conf` | docs/SC |
| `47c795c`, `8f0007f` | **Tick freeze** `scripts/freeze_market_ticks.sh`, cron `*/5 3-10 * * 1-5`, to `~/merdian_fixtures/ticks/<IST date>/ticks_HHMM_HHMM.csv.gz`, 10-day retention (pg_cron jobid 46 prunes `market_ticks` > 1 h) | SC |
| `a80176e` | **Replay harness v0** (see §3) | OFF |
| `df80dec` | Chain provenance: `log_child_run` — each extra expiry leg gets its own `script_execution_log` row (was 52 % traced) | LIVE |
| `6d9f4f7` | **CAS close fix**: `capture_cas_close.py` picks the latest bar in a close slot (15:29/15:34), not `body[-1]` — Dhan now appends a call-time bar, so the job had REJECTED every session since **2026-08-24**. `--date` backfills no longer insert a `market_spot_snapshots` row stamped today | LIVE |
| `2e66d4f` | **Spot session end**: `data_contracts.session_end_ist` (spot = 15:15); runner judges freshness as of it after 15:15; replay re-pinned (exactly 8 cells MISSING→OK) | SC + DDL |
| `1708a1c` | **CAS reconciliation** `backfill_cas_close_from_daily.py --auto-correct`: corrects a 15:29 bar only when Dhan daily close **and** the 16:00 snapshot (`dhan_idx_i`) agree; cron `20 03 * * 1-5` (08:50 IST) over last 7 days → `logs/cas_recon.log` | LIVE |
| `490b088` | **EOD sweep on its own cursor row** (`JOB_NAME=equity_eod_aws DEFAULT_LIMIT_PER_RUN=50` on the 16:10 cron) + `S90_CURSOR_GUARD` log line | LIVE |

DDL applied in the editor: `sql/2026-10-06_s90_spot_session_end.sql` (column + COMMENT + 2-row gated update; read back by `merdian_ro`). Data writes: 58 CAS close bars backfilled into `hist_spot_bars_1m` (08-24 → 10-05) + 10-06 live; 3 SENSEX bars corrected by hand (08-24, 09-23, **10-05 −70.24**) where daily = 16:00 snapshot.

### Marketview (`~/meridian-connect`, origin `balannavin-cyber1/meridian-connect`, deploy key `github-meridian-connect`)

`eda1ca0` Router basename (enables `/staging/`); `c53dbea` headline = live 1-min spot with its time, board stamped "as of" its γ run; `255cca0` Board overview Spot item labelled `board hh:mm`, change from the γ-run spot. **Live = staging = `255cca0`**, verified both symbols. Staging build: `npx vite build --base=/staging/ --outDir /tmp/mv-staging-build --emptyOutDir` → rsync to `/var/www/marketview-staging/`. Promote: `npm run build && sudo rsync -a --delete dist/ /var/www/marketview/ && sudo systemctl reload nginx`.

### Rulings made after the close (record in `rulings_s90.md`)

1. **Rename scope:** prose + UI only (rule 20).
2. **S90-J:** deploy window by risk class (above).
3. **Spot contract session end:** per-product `session_end_ist`, not a wider SLA.
4. **CAS reconciliation:** auto-correct only when two independent sources agree; otherwise report.

### Findings to file (tech_debt, next free id after TD-S90-NEW-11)

- **CAS close dark 08-24 → 10-06**: `hist_spot_bars_1m` closed every session on the frozen 15:14 value; daily/weekly closes for those sessions changed when backfilled. Downstream **`build_ict_htf_zones.py` needs a re-run** on corrected closes (confirm where it runs — CLAUDE.md lists it as Local, and Local tasks are disabled per ADR-006). Fixed by `6d9f4f7`/`1708a1c`; close the item once the first scheduled recon is clean.
- **SENSEX can settle after the 15:29 bar** (10-05). The live job reads only 15:29; the 08:50 recon is the safety net. The S71 "flat bar = settled at frozen price" rule held 55/58, not universally.
- **Gap prev-close is NOT affected**: `build_market_spot_session_markers.get_prev_close_spot` reads the first row ≥16:00 (the `dhan_idx_i` snapshot), which equalled the settled close on every day checked.
- **Unidentified off-box EOD cursor writer** (sibling of the S67 "untraced writer" that S68 closed as "manual sweeps" — that closure is now doubtful): 2026-10-06 16:31–17:28 IST it advanced the shared `breadth_ingest_state` `equity_eod` row between our runs; 9 batches (~450 tickers) skipped; it created no `equity_eod` rows and left `cursor 750 PARTIAL_OK`. Ruled out: this box (ps, user/root crontab, timers, bash history, syslog, `/home` logs), MALPHA (crontab, timers, code), Windows tasks, this cloud workspace. **Isolated** by `490b088`; **identify** via Supabase → Logs → API Gateway, 11:00–12:00 UTC 10-06, POSTs to `breadth_ingest_state` (box IP `13.63.27.85`). If the old `equity_eod` row's `updated_at` moves again, that timestamp narrows the log search to one minute.
- **DH-905 remaps verified**: after a clean catch-up lap on `equity_eod_aws` (28 runs, guard 0), 10-01 coverage **1,379 / 1,381 = 99.86 %**; all seven remapped tickers have data. Remaining: ANZEN (InvIT, trades sporadically — fine), **ROADSTAR** (never any EOD row; Kite `ohlc()` also empty — deactivate via R1.10).
- **`capture_cas_close.py` cron is 16:20 IST** (docstring said 15:50; corrected in `6d9f4f7`). It runs after the 16:10 markers builder.
- **Postgres collation version mismatch** warning on every `roq.sh` read (153.120 vs 153.121). Supabase-side; low severity.
- **Replay finding closed** by ruling 3 (spot MISSING 15:20/15:25).
- TD-S90-NEW-2 (Marketview push) effectively closed — deploy key works.

## 2. Verify first (live evidence from today, 2026-10-07)

| When (IST) | Check | Expect |
|---|---|---|
| after 08:50 | `tail -n 15 logs/cas_recon.log` | first scheduled recon: 10-06 SENSEX flat bar MATCH or CORRECTED; `left=0` |
| after 09:30 | `v_provenance_coverage_daily` for today | chain traced_pct **100** (df80dec); gamma/vol/gch 100 |
| 15:20, 15:25 | `cycle_health` spot rows | OK with `checks.judged_at_session_end = '15:15'` |
| after 16:10 | `grep -c S90_CURSOR_GUARD logs/eod.log`; `breadth_ingest_state` | 0; `equity_eod_aws` returns to 0; old `equity_eod` row still 17:28 (or a new timestamp → the stray writer) |
| after 16:10 | EOD coverage query (active universe = `dhan_scrip_map` NSE, active, id not null) | ~99.86 %; 10-05 published |
| 10:15:59 | A4 re-run (carried) | — |

## 3. The test harness — how to pick it up

Everything below runs **offline** (no DB, no network, any hour) unless marked.

- **One command:** `bash tests/run_offline.sh` → 6 suites, ~35 s, exits non-zero on any failure:
  1. `tests/test_check_contracts_shadow.py` — contract-runner unit tests (incl. session-end clamp)
  2. `tests/replay/test_replay_seeded.py` — seeded defects on golden day 10-01 SENSEX: frozen chain → STALE + lineage; dropped gamma → MISSING; second expiry → DEGRADED; closed day → CLOSED; clean → OK
  3. `tests/replay/replay_contracts.py --check` — production `check_contracts_shadow.evaluate()` at every 5-min cycle of 6 golden days vs pinned `tests/replay/expected/*.statuses.csv` (combined sha256 now **`abdd2b16…`**, re-pinned at `2e66d4f`)
  4. `tests/test_execution_log_child.py` — `log_child_run`
  5. `tests/test_cas_close_slot_pick.py` — vendor-shape fixture from 2026-10-06 (fails 2/6 on the old code: that is the control)
  6. `tests/test_cas_recon_autocorrect.py` — two-source rule + guarded PATCH
- **Golden days:** `tests/golden/<date>_<SYMBOL>/inputs/*.csv.gz` — 2026-08-27 NIFTY/SENSEX, 2026-09-29 NIFTY, 2026-10-01 SENSEX, 2026-10-02 NIFTY/SENSEX (holiday). Front expiry only, so `fixture_scope()` scores the chain at 1 expiry with no row band. Served by `tests/replay/fixture_client.FixtureClient` (PostgREST-like `select`/`count_exact`; pads fractional seconds for the box's **Python 3.10**).
- **Re-pinning is a decision, not a fix:** `replay_contracts.py --pin` only after reading the summary; the commit must state which cells changed and why (see `2e66d4f`: exactly 8).
- **Rule 0 for every new test:** run it against the previous code and show it fails (the CAS slot-pick test is the template).
- **Tick freeze (box):** `~/merdian_fixtures/ticks/<IST date>/`, one gzip per 5 min, `.last_end` state, 10-day retention. These are the raw material for tick-level golden days; **nothing consumes them yet**.

### Threads to resume in the harness

1. **R2.1 → deploy path (SC):** run `tests/run_offline.sh` inside every paste file (already done by habit) and make it a hard gate in a deploy script; record evidence in the tracker.
2. **R1.6:** seeded defects still cover only chain/gamma/spot on one day. Add: a truncated-tail day (08-20 shape), a depth-1 chain, a dropped-cycle day; then the spot session-end clamp on a golden day (feed dies 15:09 → MISSING).
3. **Golden day #7 from frozen ticks:** pick a day inside the 10-day retention, freeze `market_ticks` + spot + chain for it, and add the WCB/breadth products (out of replay scope today).
4. **CAS close on golden days:** add `hist_spot_bars_1m` 15:29 bars to fixtures so a future vendor-shape change is caught offline.
5. **R2.6 (LIVE, later):** compute writers join the replay only once their reads take `as_of`; until then the harness scores data products, not compute.

## 4. Open rulings / carried items

- **Doc Protocol v5** (`claude/MERDIAN_Documentation_Protocol_v5_DRAFT.md`): drafted, not adopted — put to the operator.
- **`MARKET_CLOSE_GUARD` vs the SEBI CAS circular:** reports (Reuters, 2026-10-06) say CAS is to be suspended **for derivatives settlement only** (back to last-30-min VWAP, ~end-October, one year), cash auction kept. If the circular instead restores continuous cash trading to 15:30, update `capture_spot_1m_v2.MARKET_CLOSE_GUARD` (LIVE) and `data_contracts.session_end_ist` (one UPDATE).
- **R1.10:** scrip-map sync after each scripmaster reload + daily "active map IDs absent from master = 0"; deactivate ROADSTAR.
- Roadmap tracker: R1.6 / R2.1 / tick freeze / replay harness / S90-J rows need evidence-linked updates.
- Carried from AM-1: NIFTY L9 max-pain arm; drop S90-H backups ~10-13; **10-20 holiday R0.8 live test**; Lovable publish URL privacy (operator).

## Out of scope unless the operator raises it

Agents, MCP, Kite redundancy, global context sources, historic-data purchase.
