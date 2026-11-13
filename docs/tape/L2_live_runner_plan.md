# Tape live L2, stage 2a of ruling R-D: the live runner, FILE-ONLY (plan)

Tue 2026-11-10, Opus. Base `a861d02` (tape/live-l0 head). **Plan only. Nothing is built until the operator approves.**
Inputs read: `docs/tape/L0_plan.md`, `docs/tape/L2_rebuild_scope_plan.md` (R-F step one, built; step two `extend_meta` held),
`services/tape_live/{writer,cli,wall_source,ddl}.py`, `tests/test_tape_live.py`, `tests/tape_live_mutants.py`,
`tests/run_offline.sh:215-222`, `sql/2026-11-06_tape_live_tables.sql`, `services/tape_db/{tape_schema,load_day}.py`,
`merdian_compute/tape/chain_events.py:1-104`, `bin/roq.sh` (psql pattern only, no `.env` read), spec v0.1 §8-§10.
Addendum folded in: **live_run_id is a rebuild epoch** (operator, same day), section 4.

## 0. Housekeeping

| Check | Result |
|---|---|
| Branch `tape/live-l2` from `a861d02` | **NOT DONE: `git checkout -b` was denied by the permission mode (twice).** The plan file sits in the `tape/live-l0` worktree, uncommitted. The operator creates the branch (or allows the command) before the build. |
| `git status` at start | clean, `tape/live-l0` at `a861d02` |
| Counts found | guards **14** (`GUARDS`, `test_tape_live.py:918-922`); mutants **28** (`tape_live_mutants.py:29-79`), controls 14; suite **42** steps, 41/42 = tape live (`run_offline.sh:219-220`) |
| Tools on this machine | `aws` CLI v2 present; **no `psql`** (the DB path is tested against a fake, see §9) |

## 1. Measurements that set the defaults (this machine, read-only on `C:\tape_data`)

**Segment upload lag.** File mtimes in `C:\tape_data\<day>\{NIFTY,SENSEX}\<day>\` minus the segment's 5-minute boundary
(HHMM + 5 min), 162 segments per day:

| day | min | median | p95 | max |
|---|---|---|---|---|
| 2026-11-04 | 1 s | 2 s | 5 s | 5 s |
| 2026-11-05 | 1 s | 2 s | 5 s | 5 s |
| 2026-11-06 | 1 s | 2 s | 5 s | **7 s** |

Subscriptions files: `subscriptions_HHMMSS.json` mtime = HHMMSS + 1-3 s (e.g. `143300` at 14:33:01).
**Assumption, stated:** these mtimes are the S3 `LastModified` values (whole seconds), as `aws s3 sync/cp` sets them on
download. Not proven here; `arrival_log.csv` measures it on day one.

**Chain run timing** (11-06 export): 87 runs per symbol; rows per run NIFTY 135-143, SENSEX 172-200; a run's `ts` sits
**5-21 s** after its 5-minute boundary (median 6 s). When a run becomes *readable* after its `ts` is unknown (spec §10
item 4). The runner measures it.

**Defaults derived from this:**
- **Wake lag 20 s** after each grid point: about 3 x the worst segment lag (7 s). Configurable `--lag`.
- **Chain wait.** At cycle T (09:20-15:30) the runner waits for each symbol's run with `floor5(ts) == T` (the run
  `wall_source.wall_row` picks for T). It polls every **15 s** up to **T + 120 s**, then proceeds with what it has. This keeps
  the label inside the spec's 1-2 minutes. Without the wait, a run at T+21 s is unreadable at T+20 s, and the wall for T would
  be the T-5 run. The live wall would then differ from replay for no reason.

## 2. Module layout (all in `services/tape_live/`, stdlib only, nothing outside imports it)

| File | Contents |
|---|---|
| `writer.py` (changed) | Epochs (section 4), per-row `as_of`, DB-shaped deltas. The intake and rebuild logic is unchanged. |
| `dbshape.py` (new, pure) | The DDL column order of the four tables, taken from `ddl.tables()` (never retyped), and the CSV-to-DB rename from `tape_schema.TABLES[...]["rename"]` + `trading_day`. Renders one row as the DB will hold it. Empty field = NULL, as `load_day.convert`. |
| `wall_source.py` (extended) | Stays the ONLY chain access (guard `live-no-outcomes` requires it). New: `SNAPSHOT_SQL` (the one SELECT), `psql_ts(s)` (strict `YYYY-MM-DD HH:MM:SS[.f]+00` to the export shape `YYYY-MM-DDTHH:MM:SS[.f]+00:00`, then `norm_snapshot_ts`), `rows_from_psql_csv(text)`, and `RunAccumulator` (dedupes on `(run_id, expiry_date, strike)`, counts `run_grew` and `row_changed`, builds runs via the one `build_runs`). |
| `live_sources.py` (new) | **The only `subprocess` code.** `ObjectSource` interface: `list(prefix) -> [ObjInfo(key, size, etag, last_modified)]`, `get(key, dest)`. `S3Source` uses `aws s3api list-objects-v2` / `aws s3api get-object`. `LocalDirSource` is for tests: a recorded day plus a visibility schedule, driven by the clock. `ChainSource` interface: `read_page(symbol, cursor, until_ts, limit) -> rows` (keyset, §6.1) and `count_upto(symbol, k_ts, until_ts)`. `PsqlChainSource` runs `psql` with the SQL on stdin. `LocalChainSource` reads the snapshot CSVs, with rows visible at `ts + delay`. The runner calls one injected `run(argv, env, stdin, timeout)`, so tests substitute a fake. |
| `live_runner.py` (new) | The loop. `RealClock` / `SimClock`. Journal (`arrival_log.csv`), `state.json`, heartbeat, kill switch, metrics, memory and disk caps. It knows only the two interfaces, never which source it has. |
| `cli.py` (changed) | New subcommand `live` (argument parsing, environment checks, and wiring for real or sim). `replay` uses the same epoch ids (section 4). |

Guard `live-isolated` stays true as written: stdlib + `merdian_compute.tape`/`services.tape_*` only, nothing in
`tape_runner`/`tape_scoring` mentions `tape_live`, and `services/tape_runner/install.sh` is not touched. Nothing under
`merdian_compute/`, `tape_offline`, `tape_scoring`, `tape_runner` changes.

## 3. The loop

```
start: environment checks (section 6), load state.json + journal if present (restart, section 5)
for t in grid  (each 5-min point from the first one >= start, through 15:45):
    sleep until t + lag      (in <= 5 s slices: kill switch and SIGTERM are seen while sleeping)
    if kill switch file exists or SIGTERM: heartbeat state=killed|stopped, exit 0
    list NIFTY/<day>/, SENSEX/<day>/, session/<day>/   (full prefix: keys late or _rN-variant sort before the last one)
    new objects = listed keys not in the journal; validated key regex; md5 == ETag after get (single-part PutObject)
    append each to arrival_log.csv (fsync) with at = t, cycle = t   <- the journal
    feed LiveDay in replay's order: subscriptions (sub_sort_key), then segments (symbol index, seg key, name)
    if GRID_FIRST <= t <= GRID_LAST: chain wait (section 1), walls = wall_row(runs, day, t)
    if t >= GRID_FIRST: d = ld.cycle(t, walls, as_of(t))
    write deltas, wall/label/state files atomically (tmp + os.replace), then state.json (committed cycle = t)
    live_metrics.csv row; heartbeat
    RSS > soft cap or free disk < floor: heartbeat state=memory_cap|disk_floor, exit 3
at 15:45 (after that cycle): final cycle ld.cycle(None, {}, as_of(last_t)), final files, runner_manifest.json, state=done, exit 0
```

- The order of `add_*` calls, `at`, the grid, and `last_t = max(15:30, latest at)` match `cli replay` (`cli.py:179-209`)
  exactly. This is what makes gate (a) a byte comparison.
- **Overrun.** If a cycle ends after the next grid point (for example a 239 s rebuild), the missed points are skipped,
  never back-filled (L0 O-2). They are counted in `missed_grid_points`, and their objects get `at` = the next cycle actually run.
- **Failures.** A failed `list` / `get` / `psql` is counted in the heartbeat `errors` and the metrics row. The cycle
  proceeds with what it has, and the call is retried at the next wake. The chain wait is the only repeated call within a
  cycle: at most 8 polls, 15 s apart, each bounded. There is no tight retry loop anywhere.
- **Day gate.** The gate is data presence, not the trading calendar. If no `session/<day>/subscriptions_*.json` is listed
  by 09:20 + lag, the runner writes heartbeat `state=no_session` and exits 0. A special session
  (`special.special_window(day)` is not None) is **refused** in 2a (exit 0, `state=special_session_unsupported`).
- **Downloaded objects** go to `<out>/<day>/raw/<SYM>/<day>/…` and `raw/session/<day>/…`, the `C:\tape_data\<day>`
  layout. So `cli replay --raw <that dir>` can be run on the box afterwards.

## 4. live_run_id = rebuild epoch (the addendum)

- **Definition.** `epoch[sym]` = the number of entries for `sym` in `LiveDay.rebuilds` (late segment, or a subscriptions
  change to that symbol's filtered map, per R-F). `live_run_id(sym) = uuid5(NAMESPACE_URL,
  "meridian-tape-live:<day>:<symbol>:<code_sha>:<epoch>")`. It is constant while cycles are added incrementally and new
  after each rebuild of that symbol. **The epoch is per symbol**, because R-F rebuilds per symbol. A NIFTY rebuild leaves
  SENSEX's id alone.
- **Re-emission.** In the cycle that follows a rebuild of `sym`, every cycle, events and wall row of `sym` is emitted under
  the new id. The diff compares the data line **and** the id, so every surviving key gets a `U` line with the new id and
  every vanished key a `D` line.
- **The newest-run filter (how 2b and the page read the three state tables).** For `tape_live_cycle`, `tape_live_events`
  and `tape_live_wall`, a reader keeps, per `(trading_day, symbol)`, only the rows whose `live_run_id` is that symbol's
  newest epoch. The PKs (DDL) do not contain `live_run_id`, so a re-emitted row overwrites its key on upsert. A key that
  vanished at a rebuild keeps its old-epoch row, and the filter hides it. The reference implementation is
  `writer.newest_epoch_view(rows)`, which the guards use; 2b and the page implement the same rule.
- **Labels are NOT subject to the newest-run filter.** A `tape_live_label` row is keyed by `(symbol, trading_day, ts_ist,
  wall, rule_version)`: day / symbol / T, plus the wall and the rule version, which is the DDL PK
  (`sql/2026-11-06_tape_live_tables.sql:156`). It is insert-only and first-wins (spec s3). Its `live_run_id` is
  provenance only (the epoch it was written in) and is never used to select it. A label written at 11:00 under epoch 0 is
  read after a 12:20 rebuild exactly as before.
- **`D` lines are file-only.** They are in the delta files so that the files reconstruct the exact state. **2b treats a
  `D` line as a no-op**: no `DELETE` is ever issued, so 2b stays an upsert-only writer. Correctness then rests on the
  newest-run filter. That holds only if a `D` line never occurs **within** an epoch, because a key that vanished
  without an epoch change would stay visible. Within an epoch, cycle-row keys cannot vanish: `build_cycle` emits every T
  from `first_T` per strike-leg, and strike-legs change only through the token map, which means a rebuild. Event keys
  can vanish within an epoch. A packet arriving one segment late (0.067 %, L0 §2) can change bin T after the event at T
  was emitted. **Default (Q-1 below): a cycle whose delta would hold a `D` line for `sym` without a rebuild bumps `sym`'s
  epoch, trigger `drop`, and re-emits.** Then "U-only + newest-run filter" equals "U and D applied" at every cycle.
  Phase B measures how often this happens on 11-04..11-06.
- **`as_of` per row** = the grid time (UTC) of the cycle that last changed the row's data or id. Rows are re-sent only when
  they change, as a DB upsert would. The final cycle stamps `as_of(last_t)`.
- **Files carry the DB rows exactly.** `cycles/<HHMM>_{cycle,events,wall}.csv` (deltas, `op` + the DDL columns) and
  `tape_live_{cycle,events,wall,label}.db.csv` (state). Their headers are the DDL columns of
  `sql/2026-11-06_tape_live_tables.sql` in order, `as_of, live_run_id, code_sha` last. A guard parses the SQL file
  and asserts each header against it. The L0-shaped `tape_live_cycle.csv` / `tape_live_events.csv` stay byte-equal to
  `cyc_<day>`, so the L0 gate is unchanged.
- **`cli replay` uses the same epoch ids.** The per-input-hash id (`cli.py:160-161`) is retired. `run_manifest.json`
  gains `epochs: {sym: [ids]}`; the single `live_run_id` key goes. This changes L0 semantics, as the addendum orders.
  `M-L-NONDETERMINISTIC` is re-anchored onto the epoch-id function (uuid4 there).
- **Guard `live-epoch`** (fixture `gen_live.build(root, epoch=True)`; the default fixture stays pinned by
  `DEFAULT_FIXTURE_CONTENT`). A late segment arrives, whose volume on other strikes removes a provisional CONC that
  had been emitted without it. Asserted:
  (0) **precondition**: the event is present in the state after the cycle before the rebuild, under epoch-0's id. If the
  fixture does not drop an event, the guard FAILS rather than passing vacuously;
  (1) the rebuild cycle's delta has a `D` line for that event and `U` lines for every surviving row of the symbol, with the
  epoch-1 id;
  (2) the state rebuilt from all delta files with `D` applied holds **no** row of that symbol with the epoch-0 id;
  (2b) the state rebuilt from **U lines only** (the 2b writer), then passed through `newest_epoch_view`, equals (2)
  at **every** cycle, not only the last;
  (3) the latest epoch's data columns equal the batch output for the day, byte for byte;
  (4) the other symbol's id is unchanged throughout;
  (5) for a cycle with no rebuild, the delta carries no row whose data is unchanged;
  (6) labels written before the rebuild are still present after it, with their original id, and `newest_epoch_view` is
  never applied to them.
- **Mutants:** `M-L-ID-EVERY-CYCLE` (the epoch counts cycles) is caught by (5) and (4). `M-L-OLD-ROWS-KEPT` (on a rebuild,
  the old state is merged under the new id) is caught by (3), because the dropped event survives. `M-L-ID-NOT-BUMPED` is
  caught by (1) and (2). `M-L-ID-GLOBAL` (one symbol's rebuild bumps both) is caught by (4). `M-L-LABELS-FILTERED`
  (the reference view filters labels too) is caught by (6). `M-L-DROP-NO-BUMP` (a within-epoch drop does not bump) is
  caught by (2b), on a second planted case: an event that vanishes with no rebuild.

## 5. Crash-safe restart

- The journal (`arrival_log.csv`) records each object with its `at` and `cycle`. `state.json` records the last committed
  cycle, `rebuilds`, `late`, `bad_files` and `epochs`.
- **Restart:** list everything in S3 (objects already cached with the same ETag are not re-downloaded). Then replay into a
  fresh `LiveDay`, without cycles, the journal entries with `cycle <= committed`, in journal order with their logged
  `at`. Call `_rebuild_dirty()` once. Restore `rebuilds/late/bad_files` from `state.json`: rebuilds during catch-up are
  recovery, not emitted epochs. Restore the emitted state from the delta files (`apply_deltas`), and walls and labels from
  their files. Journal entries with `cycle > committed` (a crash mid-cycle) are processed again in the first live cycle,
  so their rebuilds are counted. Objects not in the journal get `at` = the first cycle after the restart.
- Equivalence argument, to be checked by the guard and not asserted here: after catch-up, `subs`, `meta`, `known`, `last`
  and the carried replay match the uninterrupted run (L0's invariant: the carried state equals the batch state for the
  same packets). So the next cycle emits the same delta.
- **Guard `live-runner-restart`** (fixture, SimClock):
  A = an uninterrupted run;
  B = kill switch after 11:00, restart before 11:05;
  C = an exception injected after the journal append, before `state.json`, in cycle 12:10, then a restart;
  D = restart at 12:00 after missing 11:05-11:55;
  E = A run twice.
  Every output file of B, C and E is byte-identical to A's (heartbeat, `live_metrics.csv` and the log excluded, as they
  hold timings). For D, the final cycle and events (both shapes) equal A's; the labels equal A's except exactly the 11
  missed grid points × 2 symbols × 2 walls, which are absent.

## 6. Security (each constraint, how it is enforced, which guard fails)

1. **Read-only.** The only `aws` argv shapes are `["aws","s3api","list-objects-v2","--bucket",B,"--prefix",P,"--output",
   "json","--cli-read-timeout","10","--cli-connect-timeout","5"]` and `["aws","s3api","get-object","--bucket",B,"--key",K,
   <dest>, …timeouts]`. `K` comes from a strict key regex (`(NIFTY|SENSEX)/<day>/seg_\d{4}(_c\d+)?(_r\d+)?\.ndjson\.gz` |
   `session/<day>/subscriptions_\d{6}\.json`; anything else is logged as `ignored` and never fetched), and `<dest>` is
   built only from validated parts under the cache dir. The only `psql` argv is
   `["psql","-X","-q","--csv","-t","-v","ON_ERROR_STOP=1","-v","sym=…","-v","day=…","-v","until=…","-v","k_ts=…","-v","k_exp=…","-v","k_strike=…","-v","k_run=…","-f","-"]`,
   with the values regex-validated. SQL: `BEGIN TRANSACTION READ ONLY; SET LOCAL statement_timeout='8s';
   SET LOCAL TIME ZONE 'UTC'; SELECT run_id, symbol, ts, expiry_date, strike, oi_call, oi_put, gex_cr FROM
   public.gex_strike_snapshots WHERE symbol = :'sym' AND ts >= (:'day')::date AT TIME ZONE 'Asia/Kolkata' AND ts <
   ((:'day')::date + 1) AT TIME ZONE 'Asia/Kolkata' AND ts <= :'until'::timestamptz AND (ts, expiry_date, strike,
   run_id::text) > (:'k_ts'::timestamptz, :'k_exp'::date, :'k_strike'::numeric, :'k_run') ORDER BY ts, expiry_date,
   strike, run_id::text LIMIT 5000; COMMIT;` `PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=8000"`
   is the second belt, as in `roq.sh`.
   **Keyset paging (per symbol).** The cursor is the full sort tuple `(ts, expiry_date, strike, run_id)` of the **last**
   row returned. The table's unique key is `(run_id, strike, expiry_date)` (`compute_gamma_metrics_local.py:478`), so the
   tuple is unique and the order is total. A strict `>` against it therefore neither repeats a row (no overlap) nor
   skips one at a page boundary, including rows tied on `ts` across expiries and strikes. The initial cursor is the day
   start, with `k_exp = '0001-01-01'`, `k_strike = -1`, `k_run = ''`. A page shorter than 5000 ends the poll. A full
   page continues, up to 8 pages per poll (40k rows; a whole day is about 28k). The remainder waits for the next poll.
   `until` = now, or the sim clock. The cursor is persisted in `state.json`.
   **What keyset cannot see:** a row committed **after** the cursor has passed its key (a late commit with an earlier
   `ts`). Per symbol there is one writer at a 5-minute cadence and one upsert per run, so I do not expect it. The runner
   detects it anyway: each poll also runs one bounded `SELECT count(*)` over the same symbol/day with
   `ts <= k_ts`, and compares that with the rows it holds. A mismatch is counted (`chain_skipped`) and resets that
   symbol's cursor to the day start for the next poll (a bounded re-read, deduped on the unique key). A row changed in
   place (same key, new values) is invisible to both reads, and is stated as such (Q-3).
   **Start-up refusal:** one read query, `SELECT current_user, current_setting('transaction_read_only'),
   has_table_privilege('public.gex_strike_snapshots','INSERT,UPDATE,DELETE,TRUNCATE')`. If the role can write that table,
   or the session is not read-only, the runner exits 2. This enforces "merdian_ro-class" without naming any other role.
2. **No secret anywhere.** One variable, `TAPE_LIVE_RO_DSN` (from the EnvironmentFile), is read once at start and parsed
   (`urllib.parse`) into `PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE/PGSSLMODE=require/PGCONNECT_TIMEOUT=5` **for the
   psql child env only**. It is then deleted from `os.environ`. Child envs are allowlists: psql gets `PATH`, `LANG`, `PG*`;
   aws gets `PATH`, `LANG`, `HOME`, `AWS_DEFAULT_REGION`, plus `AWS_SHARED_CREDENTIALS_FILE=/dev/null` and
   `AWS_CONFIG_FILE=/dev/null`, so only the instance role (IMDS) can sign. The runner **refuses to start** (exit 2) if
   `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` or `AWS_SESSION_TOKEN` is set. Child stderr is never logged raw. The log
   gets the return code, a category (`timeout`/`auth`/`connect`/`sql`/`other`) and at most 200 characters after a scrubber
   removes every credential value and anything JWT-shaped or URI-with-userinfo. Exception messages pass the same scrubber
   before the heartbeat. Nothing goes in argv, `/tmp` (PrivateTmp anyway) or the output dir.
3. merdian_ro-class DSN only. No roles, grants or DDL in this task. The guard patterns that detect other key kinds are
   built by string concatenation, so no new file carries the literal name.
4. Stdlib only (`subprocess`, `urllib.parse`, `hashlib`, `signal`, `resource` imported under `try`). No network module is
   imported in runner code (`socket`, `http`, `urllib.request`, `ssl` banned by the guard). No widening of
   `live-isolated`.
5. Bounded queries and timeouts: as in item 1. Subprocess timeouts: list 30 s, get 60 s, psql 15 s. A timeout is a counted
   failure, retried at the next wake.
6. Isolation is unchanged (section 2).

## 7. Heartbeat, kill switch, exit, memory, metrics

- **`heartbeat.json`** is written atomically at start, at every state change and every cycle. Fields: `state` (`starting|
  waiting|cycling|done|killed|stopped|no_session|special_session_unsupported|memory_error|memory_cap|disk_floor|error`),
  `day`, `last_cycle`, `last_cycle_wall_s`, `lag_s` (wake minus grid point), `peak_rss_mb`, `rss_mb`,
  `errors{s3_list,s3_get,md5,db,chain_timeout,other}`, `last_error` (scrubbed), `pid`, `code_sha`, `updated_utc`.
- **Kill switch:** the file `<out>/KILL` (`--kill-file`) means exit 0 at the next check (each sleep slice and each wake),
  with `state=killed`. SIGTERM behaves the same, with `state=stopped`.
- **Self-exit** after the 15:45 cycle, with the final cycle (section 3).
- **Memory.** `MemoryError` anywhere: heartbeat `state=memory_error`, exit 3. RSS soft cap (`--rss-cap-mb`, default
  **600**, under `MemoryMax=700M`) is checked after each feed and each cycle (`/proc/self/status` VmRSS; peak from
  `ru_maxrss`; on Windows `cycle_day.peak_mb`). Over the cap: `state=memory_cap`, exit 3. `RLIMIT_AS` is **not** set by default:
  virtual size exceeds RSS, so it would raise spuriously at about 450 MB RSS. Measure on the box first (open item P-6).
  Unit: `MemorySwapMax=0`, so the runner never swap-thrashes.
- **Disk floor:** below 1 GB free at start, exit 2. Below 200 MB at a cycle, exit 3 (`state=disk_floor`).
- **`live_metrics.csv`**, one row per cycle: `day, T, wake_utc, cycle_end_utc, wall_s, cpu_self_s, cpu_children_s,
  peak_rss_mb, rss_mb, s3_list_s, s3_list_calls, s3_get_s, s3_gets, s3_bytes, db_s, db_calls, db_rows, chain_wait_s,
  ready_lag_s_NIFTY, ready_lag_s_SENSEX` (first poll time at which the run with `floor5(ts) == T` was readable, minus T;
  empty if not readable by the deadline), `rebuilds, rebuild_s, late_segments, missed_grid_points, run_grew, errors`.
- **`arrival_log.csv`**, one row per object or chain run first seen: `kind (segment|subscriptions|chain_run|ignored), key,
  size, etag, s3_last_modified` (or run ts), `first_seen_utc, at, cycle`.

## 8. systemd template and install note (files only; nothing installed, no box touched)

`docs/tape/L2_live_runner.service.template` and `.timer.template`. Dedicated user `tapelive` (no shell, no sudo, no
groups). `EnvironmentFile=/etc/tape-live/tape-live.env` (mode 600, owner `tapelive`, holding `TAPE_LIVE_RO_DSN` only).
`Environment=AWS_DEFAULT_REGION=eu-north-1`. Code at `/opt/tape-live/<sha>/`, extracted by `git archive` with a
`CODE_SHA` file (`code_sha` is NOT NULL; the runner reads git or that file and refuses if it has neither). `Nice=10`,
`CPUQuota=50%`, `MemoryMax=700M`, `MemorySwapMax=0`, `OOMPolicy=stop`, `OOMScoreAdjust=500` (if the box's global OOM
killer fires, it takes the runner before the engine), `NoNewPrivileges=yes`, `PrivateTmp=yes`,
`ProtectSystem=strict`, `ProtectHome=yes`, `ReadWritePaths=/var/lib/tape-live`, `PrivateDevices=yes`,
`ProtectKernelTunables/Modules/Logs=yes`, `ProtectControlGroups=yes`, `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`,
`CapabilityBoundingSet=`, `LockPersonality=yes`, `UMask=0077`, `Restart=on-failure`, `RestartSec=30`,
`RestartPreventExitStatus=2 3`, `StartLimitBurst=3`. Timer: `OnCalendar=Mon..Fri 08:50 Asia/Kolkata`. The timer is
**installed but NOT enabled**: the note copies the unit file and runs `systemctl daemon-reload` only. It never runs
`systemctl enable` or `start` on the timer. **The first run is a manual `sudo systemctl start tape-live.service`.** Enabling
the timer is a later, separate operator decision, and is written as such.
`docs/tape/L2_live_runner_install.md` gives the exact commands: user, dirs, env file, `git archive`, unit install. It also
gives the pre-checks `command -v aws psql`, `sudo -u tapelive aws sts get-caller-identity`,
`sudo -u tapelive aws s3api list-objects-v2 --bucket meridian-tape-raw --prefix session/<day>/ --max-items 5`, and the
runner's own `--check` (environment + start-up refusal query, no loop). Then a **recorded-day rehearsal outside market
hours** (spec §8.3): `cli live --day <past day> --clock sim` on the real S3 and DB sources, with visibility by
`LastModified` / `ts <= sim now`. After it, `cli replay --raw <out>/<day>/raw` and a byte comparison. Uninstall and
kill-switch commands are included. The note states it changes nothing on the box until the operator runs it.

## 9. Gates (tests first; each must be seen failing before it passes)

New guards are folded into `tests/test_tape_live.py` (**14 → 21 in Phase A, → 23 in Phase B**; `live-epoch` and
`live-dbshape` are Phase B). Step 41 changes its label only.

| Guard | What it asserts | What makes it fail (Rule 0) |
|---|---|---|
| `live-runner-equal` (a) | Fixture: runner (LocalDirSource + LocalChainSource + SimClock) vs `cli replay`, clean / late / out-of-order (the existing `--arrival` maps): every file of the replay out dir byte-equal except `run_manifest.json`, whose `rebuilds, late_segments, bad_files, token_map_conflicts, label_counts, epochs` are compared. Plus a psql-path variant: the fake `run` serves the export rows in psql text form (converted test-side, independently of `wall_source.psql_ts`), and the output must be equal again. | A different feed order, a missing chain wait, a different `at` or `as_of`, a psql shaping bug. Before the build: no runner exists (FAIL by ImportError) |
| `live-runner-readonly` (b) | AST of `live_sources.py`, `live_runner.py`, `cli.py`, `wall_source.py`: no string constant equal to an S3 write verb (`cp sync mv rm put put-object delete-object delete-objects copy-object upload-part create-multipart-upload`); no SQL write keyword (`INSERT UPDATE DELETE COPY CREATE ALTER DROP TRUNCATE GRANT REVOKE MERGE CALL`, word-bounded, case-insensitive) in any non-docstring constant; no `shell=` other than absent or `False`; no `os.system` / `os.popen`; every `subprocess.run` has `timeout=`; no f-string, `%` or `.format` whose operand names match `pass|pwd|secret|token|dsn|key`. Runtime: a recorded fake `run` over a sim day; every argv matches one of the 3 allowed shapes, and no element holds any credential value. | A mutant adds `cp`, `INSERT`, `shell=True`, or the DSN in argv |
| `live-runner-secrets` (c) | Scan of every new and changed file in the commit (code, docs, templates, tests) for URI-with-userinfo, `password=`, JWT shape, `AKIA…`, secret-key names, and the service-key role name (pattern built by concatenation). Runtime: a fake `psql` writes the test password into stderr and raises; the heartbeat, metrics, log, exceptions and arrival log do not contain it; the aws child env has no `PG*`; the psql child env has no `AWS_*`; the DSN variable is gone from `os.environ`; the runner refuses on `AWS_ACCESS_KEY_ID`. | Raw stderr logged; the DSN left in env; keys accepted |
| `live-runner-bounded-sql` (d) | Every SQL string in `services/tape_live`: an explicit column list (no `*`), equal to `chain_events`' 8 input columns; `symbol =`, both day bounds, `until`, the keyset predicate; `LIMIT n` with n ≤ 5000; `SET LOCAL statement_timeout='8s'` and `READ ONLY`; PGOPTIONS carries both; the psql timeout ≤ 15 s. The count query has the same bounds. The keyset tuple in `WHERE` equals the `ORDER BY` tuple, column for column. | A mutant drops LIMIT, a bound or the timeout, selects `*`, or orders by a different tuple than it compares |
| `live-runner-keyset` (d) | An in-memory fake table, which applies tuple order, strict `>`, `LIMIT` and `until` itself (written in the test, not taken from `wall_source`), serves pages through the fake `run`. The page size is forced to 7 so boundaries fall inside `ts` ties. Rows cover 2 runs sharing a `ts` across two expiries, equal strikes across expiries, and runs landing between polls. Asserted: the concatenation of all pages equals the full ordered set exactly (no duplicate, no gap); the cursor equals the last row returned; a page shorter than the limit ends the poll; a poll stops after 8 pages and the next poll resumes at the cursor. A planted late commit below the cursor makes the count check fire once, resets the cursor, and the row is recovered with no duplicate. | `>=` (overlap gives duplicates), cursor on `ts` only (skips the tie remainder at a page boundary), cursor from the first row, the count check removed |
| `live-runner-lifecycle` (e) | Heartbeat after every cycle with the fields above; the kill file at 10:02 gives exit 0 `killed` and no cycle after 10:00; a sim run ends at 15:45 with `done` and no wake after; injected `MemoryError` gives exit 3 `memory_error`; injected RSS over the cap gives exit 3 `memory_cap`; an S3 list that fails once gives `errors.s3_list == 1`, the cycle still runs, the next wake recovers, and list calls == wakes × 3 (no tight loop); the chain wait polls at most 8 times; a run delayed past the deadline gives the older run's id in the wall row and an empty `ready_lag_s`. | Kill ignored, runs past 15:45, exit 0 on MemoryError, retry loop |
| `live-runner-restart` (e) | Section 5 A-E | The journal is ignored on restart, epochs are not restored, or catch-up rebuilds are counted |
| `live-epoch` | Section 4 (0)-(5) | Section 4 mutants |
| `live-dbshape` | Each `.db.csv` / delta header equals the DDL column list parsed from the SQL file; `trading_day`, renames and `code_sha` are present; empty = NULL | Header drift from the DDL |

**Mutants** (to `tests/tape_live_mutants.py`, each ×5 with its guard's control), by phase (section 12):
- **Phase A (19):** `M-R-S3-WRITE`, `M-R-SQL-WRITE`, `M-R-SHELL-TRUE`, `M-R-CRED-IN-ARGV`, `M-R-STDERR-RAW`,
  `M-R-DSN-LEFT-IN-ENV`, `M-R-NO-LIMIT`, `M-R-NO-TIMEOUT`, `M-R-SELECT-STAR`, `M-R-SUBS-AFTER-SEGS`, `M-R-NO-CHAIN-WAIT`,
  `M-R-KILL-IGNORED`, `M-R-NO-SELF-EXIT`, `M-R-TIGHT-RETRY`, `M-R-MEMERR-EXIT-0`, `M-R-RESTART-IGNORES-JOURNAL`,
  `M-R-KEYSET-GE`, `M-R-KEYSET-TS-ONLY`, `M-R-NO-COUNT-CHECK`. Mutants 28 → **47**; guards 14 → **21** (`live-runner-equal`,
  `-readonly`, `-secrets`, `-bounded-sql`, `-keyset`, `-lifecycle`, `-restart`).
- **Phase B (7):** `M-L-ID-EVERY-CYCLE`, `M-L-OLD-ROWS-KEPT`, `M-L-ID-NOT-BUMPED`, `M-L-ID-GLOBAL`, `M-L-LABELS-FILTERED`,
  `M-L-DROP-NO-BUMP`, `M-R-DBSHAPE-DROPS-ASOF`. Mutants 47 → **54**; guards 21 → **23** (`live-epoch`, `live-dbshape`).
  `M-L-NONDETERMINISTIC` is re-anchored onto the epoch-id function.
Steps 41/42 change their labels only, in each phase. The suite stays at **42 steps**.

**Real-day gate (a)**, `tests/tape_live_runner_equal.py --data C:\tape_data` (not a `run_offline.sh` step; Tee-Object
logs): for 11-04, 11-05 and 11-06, × clean / late (`NIFTY/seg_1100` at 11:10) / out-of-order (`NIFTY/seg_1200` at
12:20). It runs `cli replay` and the runner sim and compares every file byte for byte. It also compares the L0-shaped
cycle/events against `cyc_<day>`, and the latest epoch's DB-shaped data columns against the batch rendered through
`dbshape`. Each run takes roughly 20-30 min on this machine, with **at most 3 processes in parallel** (L0's 450 MB peak;
the L0 three-day run was stopped for low memory). Per Q-2, Phase A runs 5 of these (11-06 × 3 variants + 11-04 clean +
11-05 clean, about 1 h), and Phase B runs the full 18 (about 3 h). In Phase A the DB-shaped comparison is absent (dbshape
is Phase B), and `live_run_id` is stripped as section 12 states.

**Pins** hash decompressed content, never gzip bytes (`a861d02`). **Clean export:** the new guards and mutants also run on
`git archive HEAD` extracted to a scratch dir (`--root`), not only in the working tree. The known Windows failures (steps
2, 8, 10, 11, 25, 26, 31, 32, 34) are compared against a clean export of `a861d02`.

## 10. Open items (my default, applied unless you rule otherwise)

- **P-1 Branch.** `git checkout -b tape/live-l2 a861d02` was denied. **You run it, or allow it.**
- **P-2 `as_of` = the cycle's grid time (UTC), not the writer's wall clock.** The DDL comment says "writer clock". L0 already
  uses simulated cycle time. Grid time keeps gate (a) and the restart test byte-exact. The real clock goes in
  `live_metrics.csv`. If you want the wall clock in the DB, those two gates compare with `as_of` stripped.
- **P-3 `cli replay`'s live_run_id becomes the epoch id** (section 4), and its per-cycle deltas become DB-shaped. Both
  change L0 output formats. The L0 byte gate (cycle/events state vs `cyc_<day>`) is unaffected.
- **P-4 Epoch per symbol**, counted from `LiveDay.rebuilds` (pre-09:20 rebuilds included; nothing has been emitted then,
  so it is harmless).
- **P-5 Chain-run completeness.** I assume one upsert per run per symbol (`compute_gamma_metrics_local.py:467-479`, a single
  `upsert(rows)`). A run that gains rows after it was read is caught by the keyset count check (§6.1, `chain_skipped`)
  only if the new rows sort below the cursor. Rows that sort above it are simply read at the next poll, and the
  accumulator counts `run_grew`. The label already written stays, and verify reports `chain_run_differs`.
- **P-6 Memory.** RSS soft cap 600 MB + `MemoryError`, `RLIMIT_AS` off. L0 measured 450.8 MB peak **on Windows**. The
  t3.small figure comes from the rehearsal.
- **P-7 Unverified until the box:** whether the instance role can list and get `meridian-tape-raw` (the tape runner uses
  an AWS key, `T0_install.md:87-88`); whether `merdian_ro` can read `gex_strike_snapshots` (`scoring_plan.md:273`); the
  psql output shape (ISO datestyle, `TimeZone UTC`, `…+00`); `aws`/`psql` versions; Python 3.10. If the DB read fails,
  walls are absent and labels are NO_READ "wall unknown". This is counted, not fatal.
- **P-8 Rule 23.** Today is a weekday. The fixture guards run under `TAPE_RULE23_OVERRIDE_R1=1` (ruling R-1, Local) or
  after 15:45. The `ulimit -v` half cannot be enforced on Windows.
- **P-9** No RLIMIT, no IP allowlist in the unit: S3 endpoint IPs vary, and IMDS (169.254.169.254) is needed for role
  credentials.

- **Q-1 (from the D-line no-op rule) Within-epoch event drops bump the epoch** (trigger `drop`, re-emit), so U-only
  plus the newest-run filter is exact. The alternative is that 2b issues `DELETE`s, which you have just ruled out. Phase B
  counts how often it happens on 11-04..11-06. L0 saw no label differences, but event drops have not been counted.
- **Q-2 RULED (operator, 2026-11-10): real-day gate per phase.** The Phase A gate is **5 runs**: 2026-11-06 × {clean,
  late, out-of-order}, plus 2026-11-04 clean and 2026-11-05 clean, with at most 3 processes in parallel. The full
  **18-run matrix** (3 days × 3 variants) is the **Phase B gate only**.
- **Q-3 A row changed in place** (same unique key, new values, e.g. a re-run of the GEX writer for an old run) is
  invisible to keyset and to the count check. It is not expected (the run_id is new per compute), and it is stated, not
  guarded.

## 12. Build phases

**Phase A: runner, sources, lifecycle, restart, security (gates a-e).**
- New: `live_sources.py`, `live_runner.py`, `cli live`. In `wall_source.py`: `SNAPSHOT_SQL`, the count query,
  `psql_ts`, `rows_from_psql_csv`, the keyset accumulator. Plus `docs/tape/L2_live_runner_install.md` and the two unit
  templates.
- `writer.py` and `cli replay` are **unchanged** in Phase A. The runner writes exactly `cli replay`'s files, with an
  interim id: `live_run_id = uuid5("meridian-tape-live-runner:<day>:<code_sha>")`, constant for the day. It cannot
  reproduce replay's per-input-hash id, because the inputs are not known at start.
- Gate (a) in Phase A: every file byte-equal to `cli replay`'s **except the `live_run_id` column** of
  `tape_live_wall.csv` / `tape_live_label.csv`. Those two are compared with exactly that one column removed, and the
  removal is asserted to drop exactly one column. That is a stated, temporary deviation, closed in Phase B.
- `state.json` holds the committed cycle, the keyset cursors, `rebuilds/late/bad_files`. The restart guard covers A-E of
  section 5.
- Guards 14 → 21, mutants 28 → 47, each guard seen failing first. Clean-export run. The real-day gate is **5 runs**
  (Q-2): 11-06 clean / late / out-of-order, 11-04 clean, 11-05 clean, at most 3 in parallel.
- Commit by explicit path. **Push to `tape-staging tape/live-l2` only. Then STOP and report** (deviations, guards
  failing-then-passing, mutant counts, three-day numbers, what was not tested). Phase B starts on your go-ahead.

**Phase B: epoch, dbshape, replay changes.**
- `writer.py`: epochs per symbol (section 4), including the `drop` trigger if Q-1 stands, per-row `as_of`, DB-shaped
  deltas, `newest_epoch_view`. New `dbshape.py`. `cli replay` moves to epoch ids and DB-shaped deltas (P-3). The
  runner's interim id is removed, and `state.json` gains `epochs`.
- Gate (a) becomes fully byte-equal, with no column stripped. Plus `live-epoch` and `live-dbshape`. Guards 21 → 23,
  mutants 47 → 54. The real-day gate is the **full 18-run matrix** (Q-2): 3 days × {clean, late, out-of-order}, at most 3
  in parallel. It also checks U-only + newest-run filter == D-applied at every cycle, and counts `drop` epochs per day.
- Commit, push to `tape-staging tape/live-l2`, and report.

## 13. Not in 2a

No DB write, no S3 write, no page, no install, no box. R-F step two stays held. No change to `merdian_compute/`,
`tape_offline`, `tape_scoring`, `tape_runner`. No push except `tape-staging tape/live-l2`.

## 14. Phase A deviations (recorded at the end of the Phase A build; each with its reason)

Each: what differs from the approved plan, and why.

1. **Chain cursor is not persisted in `state.json`.** The plan sketched a persisted keyset cursor. On restart the runner re-reads
   each symbol's chain from the day start; rows are deduplicated on the unique key (run_id, expiry, strike), so the result is the
   same, at the cost of re-reading ~1 day of runs. Why: a persisted cursor can hide a commit below it; re-reading removes that case
   and keeps `state.json` small. Covered by `live-runner-restart` (B, C, E byte-identical).
2. **The runner calls private `LiveDay` helpers** (`_rebuild_dirty`, and `writer._keyed/_ckey/_ekey`) in restart. Why: `writer.py`
   was to stay unchanged in Phase A, and restoring emitted state from committed delta files needs them. To be replaced by public
   entry points in Phase B.
3. **Hard-linked segment cache in `LocalDirSource`** (`os.link`, copy fallback). Why: the day dirs are 616 MB each and C: had
   under 0.5 GB free at one point. Safe only if nothing writes through the link; verified by the before/after sha256 manifest of
   C:\tape_data (500 files, identical). Production uses `S3Source`, which downloads real files.
4. **`--disk-floor-mb` flag** (default 1024.0 MB = the production floor; stop floor = floor/5). Why: the Windows test box had less
   than 1 GB free; tests and the real-day gate pass 20. The install note and the unit do not pass it.
5. **Reworded error string in `cli.py`** ("do not exist" -> "are not present"). Why: the bounded-SQL/write-word scan matched
   `DO` in the old text.
6. **`cli.code_info` pinned in the test process (`TEST_SHA`).** Why: mutant copies and `git archive` exports have no `.git`.
   The real-day gate does not pin it (real git sha).
7. **Interim `live_run_id`** = uuid5 of (day, code sha), constant per day; the equality gate strips exactly that column of the wall
   and label CSVs. Why: the rebuild epoch is Phase B. Closed in Phase B.
8. **Heartbeat `last_error` is scrubbed** with the known secrets plus the generic patterns, and errors carry a category only (never
   stderr, argv or exception text). Not in the plan's text; added from security rule 2.
9. **Availability margin +2 s** in the local schedule (visibility = cli availability minute*60 + 2 s). Why: the simulated clock
   must show an object strictly after the grid point the batch path assigns it.
10. **Keyset `>`/`<=` in the SQL string has no mutant** (only `live-runner-bounded-sql` pattern). Listed under not-tested.
11. **The x5 mutant matrix was run by the operator outside the session** (`python tests/tape_live_mutants.py --repeat 5`, log
    `_l2_logs/mutants_x5_full.log`: 47/47 caught x5, 21/21 controls x5, EXIT=0). Why: two in-session attempts were killed by the
    host for low memory at rep 3 (same point both times), so the matrix could not be completed inside the session.

## 15. Phase B rulings and deviations (recorded during the Phase B build; each with its reason)

1. **Ruling R6-H, newest-epoch rule (approved by the operator, 2026-11-13, with the tie rule).** Per (trading_day, symbol), the newest epoch is the live_run_id of the row with the latest
   as_of across tape_live_cycle, tape_live_events and tape_live_wall taken together; only rows with that id are kept, in all three
   tables; tape_live_label is exempt. Reason: a per-table rule keeps a vanished row when the newest epoch has no row in that table
   (planted case: SENSEX's only event, CONC 10:45, vanishes in the 10:50 rebuild; the per-table view kept it at all 57 cycles
   10:50-15:30, `_l2_logs/phaseB_red_newest_per_table.log`, `phaseB_red_newest_detail.log`). Implemented in
   `writer.newest_epoch_view(tables)`; the guard's reference (`newest_view` in tests/test_tape_live.py) is written independently.
   Tie rule (same ruling): per (trading_day, symbol), every row at the latest as_of across the three tables carries one
   live_run_id; asserted in live-epoch (U-only and D-applied state, every cycle, plus a planted tie that must be detected).
2. **Restart: as_of moves for rows emitted in missed cycles.** After a restart that skipped grid points, a row whose uninterrupted
   as_of is a missed cycle is re-sent at the first post-restart cycle (12:00 in case D), with that as_of. So restart finals are no
   longer byte-equal to the uninterrupted run in as_of (case D only; B, C and E stay byte-identical). live-runner-restart D asserts
   exactly that rule (only rows whose uninterrupted as_of is a missed point may move, and only to 12:00), equal epochs, an
   epoch_log equal except the one bump of the default day (NIFTY subscriptions: 695 uninterrupted, 720 restarted; its reemit_rows
   may differ), and tape_live_label.db.csv with exactly the missed points' rows absent.
3. **M-L-NONDETERMINISTIC re-anchored** from cli.py's input-hash id (retired, P-3) to `writer.epoch_id`; the mutated id is now
   random per call (before: once per replay). Still caught by live-deterministic.
4. **Two mutants beyond the plan's seven:** M-L-NEWEST-PER-TABLE (restores per-table resolution; live-epoch) and
   M-L-TIE-NOT-ASSERTED (removes the tie assertion; live-epoch, by the planted tie). With the two dbshape mutants
   (M-R-DBSHAPE-UTC-DATE, M-R-DBSHAPE-ASOF-WALLCLOCK) the count is **58 mutants over 23 guards** (plan section 9 said 54).
5. **DB-shaped files are added beside the L0 files** (operator ruling): `cycles/<HHMM>_{cycle,events,wall}.db.csv` and
   `tape_live_{cycle,events,wall,label}.db.csv`; the L0 files are unchanged, so the cyc_<day> byte gate and apply_deltas hold.
6. **`drop` bumps are recorded in `epoch_log`, never in `rebuilds`** (live-rebuild-scope and live-equal-offline assert the exact
   rebuild list). run_manifest.json carries `epochs` and `epoch_log`; its `live_run_id` key is gone (no reader of it exists).
7. **Phase A deviation 2 closed:** the runner restarts through public `LiveDay.restore()` and `rebuild_dirty()`.
8. **Fixture re-derivation:** the first SENSEX plant (bursts at 10:00 / 10:10) produced no event, because cycle bins start at
   09:20 and bin 10:15 had 11 bins of history (< MIN_PRIOR 12); the guard's precondition caught it
   (`_l2_logs/phaseB_red_precondition_sx1015.log`). Moved by hand to 10:30 / 10:40 (16 and 17 bins).
9. **Phase A defect found in Phase B: live_metrics.csv missed late-segment rebuilds.** `_cycle` took the rebuild counter and
   timer after the intake had been fed, and a late segment rebuilds inside the feed, so `rebuilds` read 0 at such a cycle and
   `rebuild_s` left the rebuild out (subscriptions rebuilds, done at the start of `cycle()`, were counted). The Phase A 727 s
   cycles therefore cannot be split by these columns. Fixed: the counter is taken before the intake and feed; the timer starts
   before the feed and this cycle's `chain_wait_s` (stats reset per cycle) is subtracted, so `rebuild_s` = feed + `cycle()`
   and does not double-count the S3 and chain-wait columns (a deviation from "timer before the intake", for that reason).
   live-runner-lifecycle asserts per cycle that `rebuilds` equals the manifest's rebuilds at that grid point and `rebuild_s` > 0
   there (red `_l2_logs/phaseB_red_metrics_rebuilds.log`, green `phaseB_green_metrics_rebuilds.log`); mutant
   M-R-METRICS-SNAPSHOT-LATE restores the old order. **59 mutants over 23 guards.**
10. **Ruling Q-1 (operator, 2026-11-13): accepted as built, with a measured upsert-cost gate before stage 2b.** A within-epoch
    drop bumps the symbol's epoch (trigger `drop`) and re-emits every cycle, events and wall row of that symbol under the new
    id, as section 4 states. The real-day gate measured volume only, not DB write time. 2026-11-06 clean had 25 bumps: 24 `drop`
    (NIFTY 8, SENSEX 16) plus 1 `subscriptions` (SENSEX 14:35, 7,044 rows re-sent). Total re-sent 104,822 rows over a base of
    15,525 (14,262 cycle + 1,263 event rows); largest single re-emit 8,796 (SENSEX `drop` 15:35). Totals re-sent on the other
    runs: 2026-11-04 24,996 (clean, late; ooo 27,884), 2026-11-05 74,631 (clean, late; ooo 77,555), 2026-11-06 late 104,822,
    2026-11-06 ooo 107,770. A `D` line (op `D` in `cycles/<HHMM>_{cycle,events,wall}.db.csv`) records that a key present in the
    previous cycle's state is absent from this one; the delta files carry it so that applying U and D in order reconstructs the
    exact state (`writer.apply_db_deltas`, used by restart). It never becomes a statement: section 4, "**2b treats a `D` line as
    a no-op**: no `DELETE` is ever issued, so 2b stays an upsert-only writer." The vanished key's old-epoch row stays in the
    table and the newest-epoch rule (item 1) hides it. The gate before 2b is the upsert time of a re-emit of about 9,000 rows.
11. **Merge of the Phase A fixes into the Phase B tree (2026-11-13).** `821f36a`, `d170a38` and `88912ef` (tape-staging
    `tape/live-l2-fix`) were brought in by a per-file three-way `git merge-file` (base `670ea84`, ours = the Phase B working
    file, theirs = `88912ef`), not by cherry-pick; the three commits are linear on `670ea84`, so the result equals cherry-picking
    them in order. `live_sources.py`, `L2_live_runner_install.md` and `L2_live_runner.service.template`, which Phase B had not
    changed, were taken whole from `88912ef`. Nothing was committed during the merge; Phase B was backed up first.
12. **Three conflicts, all summary text, none in `services/` or `merdian_compute/`.** `tests/test_tape_live.py`
    (`g_runner_equal`): every S3 / fake-timestamp check of the fix kept, with Phase B's summary line. `tests/tape_live_mutants.py`:
    the docstring count set to 61/61 and 23/23. `tests/run_offline.sh`: step 41/42 labels set to 23 guards and 61 x5, and the
    step comment above them (not a conflict hunk) updated to the same counts.
13. **Mutant count 61, not 60.** 47 (Phase A) + 12 (Phase B: the seven of section 9, M-L-NEWEST-PER-TABLE, M-L-TIE-NOT-ASSERTED,
    the two dbshape mutants of item 4, M-R-METRICS-SNAPSHOT-LATE) + 2 (fix branch: M-R-FAKE-TS-UNPADDED, M-R-S3-LM-NOT-NORMALISED)
    = **61 mutants over 23 guards**. The 60 in the merge instruction omitted 821f36a's mutant. The counts in items 4 and 9 are
    the counts at the time they were written. Phase B's count text had also drifted before the merge (docstring 59,
    `run_offline.sh` 56 x5); both now read 61.
14. **Real-day gate is 9 gate invocations; the "18" was an arithmetic slip** (accepted by the operator, 2026-11-11: "Matrix is
    9 runs, accepted."). The figure came from the planning message "3 days x 3 arrival variants = 18"; sections 9, 10 (Q-2) and
    12 enumerate the matrix as 3 days × {clean, late, out-of-order}, which is 9. The 9 were run by the operator outside the
    session, all `GATE ... PASS`, EXIT=0 (`_l2_logs/merge_real_*_20261113_*.log`). Each invocation
    (`tests/tape_live_runner_equal.py --day D --variant V`) runs `cli replay` and then the runner one after the other, so two
    side by side is two processes, within the "at most 3 processes in parallel" of sections 9 and 12. The x5 mutant matrix was
    also run by the operator outside the session, alone (61/61 caught x5, 23/23 controls x5), as in Phase A (section 14 item 11).
15. **One memory-floor slip.** The LF-export job of the merge check (guards and 33 mutants on the export) started at 1,051 MB
    free, under the 1,200 MB floor the operator set for it; the reading was printed in the same command as the run instead of
    being checked first. The job completed and passed; it was not re-run.
