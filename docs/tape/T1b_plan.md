# T1b plan — cycle aggregator, tape event candidates, merged chain events (offline, Local)

Phase T1b of `claude/tape_design_v0.1.md` (not in this repo; the prompt restates the parts used). Worktree
`C:\wt-tape-a`, branch `tape/t1b` from engine `main` `a1636b9`. Planned 2026-11-03 13:30 IST on Opus; built in the
same session after `/model` Sonnet.

**Pre-registration v0.2** (sha256 `71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800`) binds this phase:
no code joins tape rows with chain rows, spot or outcomes, and none computes agreement, lead time, coverage or
range-by-group. T1b is therefore **two halves that never meet**. The tape half emits strike-agnostic candidates at every
subscribed strike-leg. The chain half emits merged chain events. The hashed scoring SQL does the join later, keeps the
candidates at the wall / runner-up strike and labels them T1/T2/T3.

---

## 0. Housekeeping and what the sources say

| Check | Result |
|---|---|
| `git status --porcelain` | empty — **PASS** (`.env` is ignored by `.gitignore:21`, so nothing needs adding to `.git/info/exclude`) |
| `git rev-parse --short HEAD` | `a1636b9` — **PASS** |
| `git remote -v` | `origin https://github.com/balannavin-cyber/meridian-engine.git` (engine), `tape-staging https://github.com/balannavin-cyber/meridian-tape-staging.git` (staging) — **PASS** |

| Source | Fact this plan depends on |
|---|---|
| `minute.py` `COLS` | `tape_minute.csv` = `day, sym, role, opt_type, strike, expiry, token, tradingsymbol, minute, buy_qty, sell_qty, uncl_qty, gap_qty, trades, vwap, bid_qty_5, ask_qty_5, oi, oi_delta, exch_ts_max`. Sorted `(sym, role FUT<OPT, strike, opt_type, token, minute)`. Empty cell = None. |
| `minute.py` `MinuteBook.touch` | `bid_qty_5` / `ask_qty_5` / `oi` are **overwritten on every packet** (`r[7], r[8], r[9] = pk.bq, pk.aq, pk.oi`), so they are the **end-of-minute snapshot** (the minute's last chain packet), not a mean or max. T1a plan D-6: "Σ depth quantity over 5 levels at the minute's last packet". |
| `replay.py` `parse_line` / D-6 | `minute` = `exchange_timestamp[11:16]`, IST, the minute's **start** label: minute `09:17` holds packets 09:17:00–09:17:59. A row exists only for minutes in which the token had a chain packet. |
| `replay.py` `_META_FIELDS` | `build_token_map` keeps `token, sym, role, strike, opt_type, tradingsymbol, expiry` and **drops `added_minute`**. T1b reads `added_minute` itself from the `subscriptions_*.json` files. It applies the same rule: files in `sub_sort_key` order, and the first file that names a token fixes it. |
| `recorder.py` `_subscribe` | `added_minute = clk.ist_hm(now)`, box clock, `HH:MM`. Subscriptions are grow-only and every file is cumulative. |
| real day 1 (`C:\tape_data\out_2026-11-02`, read-only profile) | 56,798 minute rows. NIFTY: 83 tokens with rows, OPT expiry 2026-11-03, FUT 2026-11-23. SENSEX: 63 tokens, OPT 2026-11-05, FUT 2026-11-26. Minutes span 08:00–15:39. No IDX rows. `bid_qty_5` and `oi` are never empty. Session files are `subscriptions_085501.json` (4 tokens, 08:55) and `subscriptions_090000.json` (148 tokens). The session directory is `C:\tape_data\2026-11-02\session\2026-11-02\`, one level below the `--session` argument in the prompt. |
| `tests/test_tape_t1a.py` | Rule-23 guard: refuses an unlimited `RLIMIT_AS` where `resource` exists, and Mon–Fri 08:30–15:45 IST. `g_no_outcomes` text-scans **every** `services/tape_offline/*.py` for `gex_, strike_snapshots, supabase, outcome, agreement, lead_time, ret_30m, hist_, spot_bars, range_by_group, spot_outcome, postgrest`. `g_isolated` requires every import in those files to be stdlib or `merdian_compute.tape` / `services.tape_offline`. `u_windows_safe` forbids `resource` / `fcntl` / `os.fork` / `signal` and requires `encoding=` / `newline=` on text `open(`. |
| `tests/tape_t1a/gen_day.py` | The planted-truth pattern: the generator decides each quantity by construction and records it in a `truth` object, and the guards compare the outputs with that object. T1b copies the pattern. Its generators write `tape_minute.csv` and the chain CSV directly, without going through segments. |
| `tests/tape_t1a_mutants.py` | Mutant = one exact-string patch on a copied tree, which must match exactly once ("MUTANT NOT APPLIED" is a FAIL). The guard runs with `--root`, and the control must PASS. T1b copies this harness and adds `tests/tape_t1b` to `COPY`. |
| `merdian_compute/gamma.py` `build_gss_rows` | `gex_strike_snapshots` row = `run_id, symbol, ts, expiry_date, dte, strike, spot, gamma_call, gamma_put, oi_call, oi_put, gex_cr` (+ `id, created_at` live; `merdian_reference.json` → `tables.gex_strike_snapshots.columns_live_s75`). The column is **`expiry_date`**, not `expiry`. One run_id is single-expiry (`infer_expiry_date` raises otherwise). |
| `compute_gamma_metrics_local.py` `fetch_recent_max_gamma_strikes` / `upsert_gex_strike_snapshots` | Reads `gex_strike_snapshots` with `.select("ts,strike,gex_cr").eq("symbol", …)` and groups rows **by `ts`** into a cycle. Unique key `(run_id, strike, expiry_date)`. |
| `scripts/patch_s81_front_expiry_runid.py` | All expiries of one ingest share **one `ts`**, so the front expiry of a run is **min `expiry_date` at that `ts`** (`order=ts.desc,expiry_date.asc`). No `>= today` guard. No separate table is needed to resolve the front expiry. |
| `core/supabase_client.py` `SupabaseClient.select(table, columns, filters, limit, offset, order)` | Reads `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` through `core.config.get_settings()` (`python-dotenv`, `BASE_DIR/.env`). A filter value without an operator prefix gets `eq.`. A dict filter holds **one condition per column**, so `ts >= a AND ts < b` cannot be written as two keys (see D-14). `order` ending in `.asc` passes verbatim. |

---

## 1. Decisions

### Layout (one overrule)

**[D-1] Chain-side CLIs live in `services/tape_chain/`, not `services/tape_offline/`.** *Overrules the prompt's
`services/tape_offline/chain_events_day.py` / `export_chain.py`.* Reason: T1a's `g_no_outcomes` and `g_isolated` scan
**every** file in `services/tape_offline/`. A chain CLI there necessarily names `gex_strike_snapshots`, and the
exporter imports `core.supabase_client`. Step 33 would fail, or a passing T1a guard would have to be narrowed, which
weakens it. A separate package also makes the tape/chain split physical, and that is what `t1b-no-join` asserts.
`install.sh` archives only `services/__init__.py services/tape_runner`, so `services/tape_chain/` is not shipped
either (`t1b-isolated` re-asserts it).

| Half | Pure module | CLI |
|---|---|---|
| tape | `merdian_compute/tape/cycle.py`, `merdian_compute/tape/events.py` | `services/tape_offline/cycle_day.py` |
| chain | `merdian_compute/tape/chain_events.py` | `services/tape_chain/chain_events_day.py`, `services/tape_chain/export_chain.py` |

`merdian_compute/tape/__init__.py` imports nothing, so importing one half never loads the other.

**Naming hazards (from the guards, so the build does not trip them):** tape-side files must never contain `hist_`,
`gex`, `outcome`, `spot`, `lead_time`, `wall` or `leader`. Chain-side files must never contain `spot`, `buy_`, `sell_`,
`bid_qty`, `ask_qty` or `tape_minute`. `n_hist` is allowed (it is not followed by `_`), but the build calls it
`n_prior` to be safe.

### Tape half — cycle aggregator (`cycle.py`, pure)

**[D-2] Clock and bin membership.** The grid is T = 09:20, 09:25, …, 15:30 (75 bins). Bin T holds the minute rows with
label m, **T−5 ≤ m < T** (m = minute start, so this is the continuous interval [T−5:00, T:00)). *Deviation from the
literal (T−5, T]:* with minute-start labels, minute `T` holds packets from T:00 to T:59, which is after T. Putting it in
bin T would be lookahead (CLAUDE.md rule 0a). The only content that moves is a packet stamped exactly `T:00`, which goes
to bin T+5. The cycle row is therefore stamped T, and everything in it was known by T. Minutes < 09:15 and ≥ 15:30 are
**out of session**: they are reported, never binned, and never in `*_cum`. The chain run clock (`ts` of each run) is
reconciled in SQL.

**[D-3] Rows and window.** Key = (symbol, expiry, strike, leg, T), where leg ∈ {CE, PE, FUT}. FUT rows have an empty
strike. `token` and `tradingsymbol` are carried. If two tokens map to one key, that is an input error (exit 2).

- `first_seen_minute` = min(`added_minute` from the token map, first in-session minute row of the token). When a minute
  row precedes `added_minute` (exchange clock vs box clock), that is counted as `data_before_added`. A token with no
  `added_minute` uses its first row and is counted as `first_seen_fallback`.
- `first_seen_T` = the bin that contains `max(first_seen_minute, 09:15)`. Rows exist for every T from `first_seen_T` to
  15:30. **No row before `first_seen_T`, never a zero-filled one.**
- After `first_seen_T`, a bin with no minute rows is a real row with zero flows and `minutes_present_5 = 0`. The token
  was subscribed, so zero is measured, and `minutes_present_5` says how much was seen.
- A subscribed token with no minute rows all day has no cycle rows. It is listed in the report.

**[D-4] Columns** (`tape_strike_cycle.csv`). `symbol, expiry, strike, leg, token, tradingsymbol, T` (ISO
`YYYY-MM-DDTHH:MM:00+05:30`), then:

- `buy_5, sell_5, uncl_5, gap_5, trades_5` = sums over the bin.
- `buy_15, sell_15` / `buy_30, sell_30` = sums over the bins T, T−5, T−10 / … T−25 that exist for this key (same day,
  ≥ `first_seen_T`).
- `balance_5|15|30 = (buy − sell)/(buy + sell)`, empty when the denominator is 0.
- `resting_imb = (bid_qty_5 − ask_qty_5)/(bid_qty_5 + ask_qty_5)` at the **last minute row present in the bin**. Empty if
  no row is present, either value is empty, or the sum is 0. There is no carry from earlier bins.
- `classified_share_5 = (buy_5+sell_5)/(buy_5+sell_5+uncl_5)`, empty at 0.
- `buy_cum, sell_cum, uncl_cum, gap_cum` = Σ of bins ≤ T.
- `oi_last` = `oi` of the last minute row in the bin with a non-empty `oi`, empty if there is none.
  `oi_delta_5 = oi_last(T) − oi_last(T−5)`, empty if either is empty (NULL is a gap).
- `minutes_present_5` ∈ 0..5, `first_seen_T`.

**Omitted on purpose:** `dw_balance` and `signed_gex_cr` need per-strike γ / Δ from the chain run. They are computed
in the scoring SQL. Floats are written `%.6f`, ints plainly, None as empty.

**[D-5] Invariant (must be able to fail).** Per token: Σ over cycle rows of `buy_5+sell_5+uncl_5+gap_5` == Σ over
in-session `tape_minute` rows of `buy_qty+sell_qty+uncl_qty+gap_qty`. That Σ is computed in the CLI from the raw CSV
rows, independently of the aggregator. The same holds per category (buy, sell, uncl, gap) and in total. Also, in-session
+ out-of-session == the file total. A violation sets `invariant_ok=false` and exit 4, with outputs still written.

### Tape half — event candidates (`events.py`, pure)

**[D-6] CONC.** Applies per option strike-leg (CE/PE). FUT is not a strike-leg and gets no CONC or THIN.
`agg_5 = buy_5 + sell_5`. For bin T, the prior bins are this key's bins strictly before T (from `first_seen_T`), n of
them, with S = Σ agg and Q = Σ agg².

- `C(T)` holds iff n ≥ 12 and n·Q − S² > 0 (population variance > 0) and z ≥ 3.
- The test is decided **exactly in integers**: `d = n·agg − S ≥ 0` and `d² ≥ 9·(n·Q − S²)`. z is reported as a float:
  `z = d / sqrt(n·Q − S²)` (corrected at build: this plan first wrote an extra factor `n` under the root; the
  derivation is z = (agg − S/n)/(√(nQ−S²)/n) = d/√(nQ−S²), and `u-int-z` pins z = 3.0 exactly at the boundary).
- An event fires at T when `C(T−5)` and `C(T)` both hold and the key is **armed**. That disarms it. Any bin with
  `C = false` (including undefined z) re-arms it. Stamp = T (a bin end, so already a close).
- Carried: `z_1, z_2, n_prior_1, n_prior_2, agg_1, agg_2`. `side` = `buy` / `sell` / `flat` from the sign of
  `buy_5 − sell_5` in the second bin. `magnitude = z_2`.
- The second bin's prior bins **include the first burst bin**, as the spec ("strictly before T") requires. The generator
  computes the same thing independently with `statistics.pstdev`.

**[D-7] THIN.** Per option strike-leg, and per series `bid_qty_5` and `ask_qty_5` separately. Minutes with
09:15 ≤ m < 15:30 only (pre-open depth is the auction book).

- For minute m with value v present: the window is clock minutes [m−30, m−1] with a present value, w = their count, and
  med = `statistics.median` (mean of the two middle values when w is even).
- `C(m)` holds iff w ≥ 20 and v ≤ 0.5·med, compared exactly as `2·v ≤ med` (med is an integer or x.5, so this is exact
  in floats).
- An event fires at m when `C(m−1)` and `C(m)` hold, both minutes are present and adjacent, and the series is armed.
  That disarms it. A **present** minute with `C = false` re-arms it. An absent minute neither extends a run nor re-arms,
  so a persisting collapse with a hole yields one event.
- **Stamp = m+1:00.** *Deviation with reason:* depth is the end-of-minute snapshot (D-0), so it is known only at the
  close of minute m. Stamping m:00 would put the event up to 59 s before the data that made it (the F-68 shape,
  rule 0a). `detail_json` carries the minute label.
- Carried: `side` ∈ {bid, ask}, `magnitude = v / med`, and in detail `depth, depth_prev, median_30, n_window, minute`.
  The SQL decides which side is passive for a wall leg.

**[D-8] `tape_events.csv`.** Columns: `symbol, expiry, strike, leg, kind, ts_ist, side, magnitude, detail_json`.
`detail_json` = `json.dumps(sort_keys=True, separators=(",", ":"))` with floats rounded to 6 places. Written with
`csv.writer(lineterminator="\n")`, which quotes the JSON. Sorted `(symbol, expiry, strike, leg, kind, ts_ist, side)`.
Candidates exist only inside the key's window, by construction. The report gives counts per kind per symbol.

**[D-9] `cycle_day.py`.** `--in <out_dir with tape_minute.csv> --session <dir> --out <dir>`. `--session` may be the
directory that holds `subscriptions_*.json`, or its parent with a `<day>/` subdirectory (the real layout). The day comes
from the CSV's `day` column (exactly one value, else exit 2). The CLI streams the CSV (csv.reader) into per-token minute
lists. The real day 1 is ~57k rows, small, so a day is held per token, never as dicts of the whole file.

Outputs: `tape_strike_cycle.csv`, `tape_events.csv`, `cycle_report.json`, `cycle_report.txt` and `run_manifest.json`
(`inputs` = relative name, sha256 and bytes of the CSV and each subscriptions file; `code.git_sha` / `dirty`; `outputs`
= sha256 each; `args` = day only, no absolute paths). `--out` must not be inside `--in` or `--session`.

Peak working set goes to **stderr only** (outside the outputs, so determinism holds). On Windows it comes from
`ctypes` `GetProcessMemoryInfo`, and on Linux from `/proc/self/status` `VmHWM`. `resource` is not used
(`u_windows_safe`).

Exit codes: 0 = written; 2 = usage or input error; 4 = invariant violated (outputs still written).

### Chain half — merged chain events (`chain_events.py`, pure)

**[D-10] Runs.** The input rows are `run_id, symbol, ts, expiry_date, strike, oi_call, oi_put, gex_cr`.

- `ts` is parsed with `datetime.fromisoformat` (offset-aware). This is **true** timestamptz, so it is converted to IST
  with a fixed +05:30 offset. TD-029 applies to `hist_spot_bars_5m`, not here, and a unit test covers both `+00:00` and
  `+05:30` input.
- A run is (symbol, ts). Its **front expiry** is min `expiry_date` at that ts (S81 selector), and only the rows of the
  front expiry are used. Other expiries are counted `non_front_rows`.
- More than one `run_id` on one (symbol, ts, expiry) is counted `run_id_conflicts`, and the run is skipped.
- Scope: runs with `ts_ist ≥ 10:00:00`. Earlier runs are counted and kept in `chain_runs.csv` with `in_window=0`.
  Runs ≥ 15:30 are counted and reported, not dropped. The spec does not cut them, and the SQL can.
- Pairs are consecutive in-window runs of the **same front expiry**, so the first in-window run is a baseline and a
  front-expiry change restarts the chain.

**[D-11] Events between consecutive runs (prev, cur).** Ties in an argmax go to the lowest strike. Ties are counted
(`argmax_ties`) because a tie that flips between runs would create an event that is an artefact.

- **E1:** `leader = argmax |gex_cr|`. If it changes, K = new leader, with `prev_strike`, `prev_value` = prev leader's
  gex_cr in prev, and `new_value` = new leader's gex_cr in cur.
- **E2-call / E2-put:** `wall = argmax oi_call` / `oi_put`.
  - If the strike changes, K = new wall, `prev_value` = old wall's OI in prev, `new_value` = new wall's OI in cur.
  - Otherwise, if `100·|oi_cur − oi_prev| ≥ 5·oi_prev` with `oi_prev > 0` (exact integers, so 5.0 % fires and 4.9 %
    does not), K = the same strike and `prev_strike = K`.
- **E3:** `sign(Σ gex_cr)` ∈ {+1, −1}. A zero sum carries the previous sign. A change is **counted** per symbol. It is
  never a row.

**[D-12] Merge.** The key is (kind, K). An event whose `ts` is ≤ 900 s after the **last counted** event of its key is
merged into it (`merged_n += 1`) and does not count. Otherwise it is a new counted event with `merged_n = 1`. The anchor
is the counted event, not the last merged one, so 0 / 5 / 10 min → one event with `merged_n = 3`, and +16 min → a new
event.

Outputs:

- `chain_events.csv`: `symbol, expiry, kind, ts_ist, strike, prev_strike, prev_value, new_value, merged_n`, counted
  events only.
- `chain_runs.csv`: `symbol, expiry, ts_ist, run_id, n_strikes, leader_strike, call_wall, put_wall, net_sign,
  in_window`. The prompt's 8 columns plus `run_id` and `in_window`, so the SQL can reconcile.
- `chain_report.json/.txt`: per symbol, counted events per kind, E3 count, merged count, scope counters, and the
  feasibility comparison. v0.2 gives NIFTY 501 / 19 days ≈ 26.4 a day and SENSEX 548 / 19 ≈ 28.8. A day outside
  ×0.5–×2 of that is **flagged in the text**. That band is a reporting band, not a measured threshold and not a gate.
- `run_manifest.json`.

**[D-13] `chain_events_day.py`.** `--in C:\tape_data\chain_<day> --out <dir>`. It reads every
`gex_strike_snapshots_<SYMBOL>.csv` in `--in`, and verifies each `.sha256` sidecar first (mismatch → exit 3, nothing
written). The day comes from `--in`'s name (`chain_YYYY-MM-DD`) or `--day`. Exit 0 / 2 / 3.

**[D-14] `export_chain.py`** (written, **never run by me**). `--symbol NIFTY|SENSEX --day YYYY-MM-DD [--out-root
C:\tape_data]` writes `<out-root>\chain_<day>\gex_strike_snapshots_<SYMBOL>.csv` plus the `.sha256` sidecar
(`"<hex>  <name>\n"`).

- It uses `core.supabase_client.SupabaseClient().select("gex_strike_snapshots",
  columns="run_id,symbol,ts,expiry_date,strike,oi_call,oi_put,gex_cr", filters={"symbol": "eq.<SYM>",
  "ts": "gte.<day>T00:00:00+05:30"}, order="ts.asc,expiry_date.asc,strike.asc,run_id.asc", limit=1000,
  offset=k·1000)`.
- It pages until a batch has < 1000 rows (rule 15) or a batch reaches a row with `ts ≥ <day+1>T00:00:00+05:30`. The
  upper bound is client-side because the dict filter holds one condition per column. Rows past the bound are discarded
  and counted.
- `spot`, `dte` and `gamma_*` are **not selected**. The SQL reads γ from the database, and the export does not carry
  spot.
- It prints rows, runs and expiries, and the first and last `ts` (IST). It refuses an existing output file unless
  `--force`. It is the only network code in the phase, and only the operator runs it.

### Common

**[D-15] Determinism and Windows.** No clock, no randomness and no environment in any output. Sorted rows and keys,
`%.6f`, LF, UTF-8, `open(..., encoding="utf-8", newline="\n")`, `pathlib` / `os.path` only. The pure modules return
strings, and the CLIs write them.

---

## 2. Tests (tester-first: generators, guards and mutants are written before the modules)

**Generators** (ground truth by construction; nothing in them calls the code under test):

- `tests/tape_t1b/gen_cycle.py` writes `tape_minute.csv` plus `session/<day>/subscriptions_*.json` and records the
  truth. The planted cases are:
  - a strike subscribed at 10:03 (rows from bin 10:05 only);
  - a key with exactly 12 prior bins, then a 2-bin burst at a stated z (generator computes z with `statistics`);
  - a key with 11 prior bins, then a 2-bin burst (no event; caught by HIST-11);
  - a 1-bin burst (no event);
  - a burst over a constant history (std = 0, no event);
  - a 2-bin burst at 2 < z < 3 (no event; caught by THRESHOLD-2);
  - a 4-bin burst (one event);
  - depth collapses of 2 minutes at exactly 50 % (fires), 1 minute (no event) and 2 minutes at 51 % (no event);
  - a mean-trap window, where the outliers lift the mean so that v ≤ 50 % of the mean but > 50 % of the median
    (no event);
  - a 6-minute collapse with one absent minute (one event);
  - minutes with `gap_qty`, out-of-session minutes at 09:05 and 15:35, a FUT token, and a bin with no minute rows
    after `first_seen_T`.

  A `--full` knob makes a synthetic full day: 2 × (45 strikes × 2 legs + FUT), 09:00–15:40 every minute, about 70k rows.
- `tests/tape_t1b/gen_chain.py` writes `gex_strike_snapshots_<SYM>.csv` plus the sidecar, and an explicit expected
  event list written by hand per scenario. The planted cases are:
  - a leader step;
  - a call-wall move;
  - put-wall OI changes of +5.0 % (event) and +4.9 % (none);
  - three same-K E1s at +0 / +5 / +10 min (one event, `merged_n` 3) and one at +16 min (separate);
  - a second expiry on every ts with a different leader (ignored);
  - runs at 09:50 / 09:55 with a leader change (ignored);
  - an E3 sign flip (counted, no row);
  - a `+00:00`-stamped file.

`tests/test_tape_t1b.py` (`--root`, `--only`, the same rule-23 guard as T1a) and `tests/tape_t1b_mutants.py`
(`--repeat 5`, each mutant with its guard's control):

| Guard | Asserts | Mutants |
|---|---|---|
| `cyc-bins` | per-bin buy/sell/uncl/gap/trades == truth; 15/30 trailing sums == truth; `*_cum` == truth | M-T1B-BIN-OFF-BY-ONE (bin = [T, T+5)), M-T1B-CUM-RESET |
| `cyc-window` | no row before `first_seen_T` for the late strike; `minutes_present_5` == truth incl. the empty bin | M-T1B-ZERO-FILL |
| `cyc-invariant` | the run's invariant OK **and** per-token, per-category Σ == the generator's in-session Σ; in+out == total | M-T1B-DROPS-UNCL |
| `ev-conc-z` | event on the planted burst with z_1, z_2 == truth (6 dp); none on 1-bin, 11-prior, std-0, z<3 | M-T1B-Z-INCLUDES-CURRENT, M-T1B-Z-THRESHOLD-2, M-T1B-ONE-BIN-FIRES, M-T1B-HIST-11 |
| `ev-thin` | event on the 2-min 50 % collapse stamped minute+1; none on 1 min, 51 % or the mean trap | M-T1B-THIN-MEAN-NOT-MEDIAN, M-T1B-THIN-60PCT |
| `ev-onset` | the 4-bin burst → 1 CONC; the 6-min collapse with a hole → 1 THIN | M-T1B-REFIRE |
| `ch-e1-e2` | planted E1 / E2-call / E2-put(5.0 %) rows == expected; no 4.9 % row; nothing from pre-10:00 or the second expiry | M-T1B-E2-4PCT, M-T1B-ALL-EXPIRIES |
| `ch-merge` | the triple → one row `merged_n=3`; the +16 min → its own row | M-T1B-MERGE-20MIN, M-T1B-NO-MERGE |
| `ch-e3-count-only` | E3 count == truth; no row with kind E3 | M-T1B-E3-AS-EVENT |
| `t1b-no-join` | text + AST: tape files (`cycle.py`, `events.py`, `cycle_day.py`) never import `chain_events` / `services.tape_chain` and never name `gex`, `strike_snapshots`, `chain_events`, `oi_call`, `oi_put`, `wall`, `leader`; chain files never import `cycle` / `events` / `minute` / `replay` / `classify` / `services.tape_offline` and never name `tape_minute`, `tape_strike_cycle`, `bid_qty`, `ask_qty`, `buy_5`; neither half names `lead_time`, `\blead\b`, `coverage`, `agreement`, `straddle_atm`, `spot`, `outcome`, `ret_30m` | M-T1B-JOINS-CHAIN |
| `t1b-pure` | AST over the three pure modules: no `time / random / socket / ssl / http / urllib / requests / boto3 / kiteconnect / supabase / os / sys / subprocess / pathlib / io` import; no `.now / .utcnow / .today / .time / open / print` call | M-T1B-WALLCLOCK |
| `t1b-deterministic` | two runs of each CLI (two output dirs, two input copies) byte-identical; manifest output hashes == file sha256 | M-T1B-NONDETERMINISTIC |
| `t1b-isolated` | no `services/tape_runner/*.py` imports `tape_offline`, `tape_chain` or `merdian_compute`; `install.sh` archives only `services/__init__.py services/tape_runner`; every import in the T1b files is stdlib or `merdian_compute.tape` / `services.tape_*`, except `export_chain.py`, which may also import `core.supabase_client` | M-T1B-RUNNER-IMPORTS |
| `export-select-only` | AST of `export_chain.py`: no attribute call named `insert / upsert / update / delete / rpc / _request / execute / post / patch / put`; the only table-name literal is `gex_strike_snapshots`; `select` calls name it | M-T1B-EXPORT-UPSERT |

Units: `u-ts-ist` (`+00:00` and `+05:30` give the same IST), `u-session-dir` (both `--session` layouts),
`u-int-z` (the integer test agrees with float z away from the boundary and is exact at z = 3), and `u-windows-safe`
(the T1a rule applied to the T1b files).

All 20 mutants run ×5. Wiring: `tests/run_offline.sh` steps 35/36 (**34 → 36**), appended after step 34. On Windows the
two Python files are run directly. The T1a suite (steps 33/34) is re-run unchanged and must still pass, as the proof
that D-1 did not need a T1a guard edit.

**Rule 23 binds the timing.** The harness refuses Mon–Fri 08:30–15:45 IST. Planning finished at ~13:30 IST on a trading
day, so **no fixture run happens before 15:45 IST** today. The build can be written before then, and green is reported
only from runs after 15:45.

**Then the real day**: `cycle_day.py` on `C:\tape_data\out_2026-11-02` with `--session C:\tape_data\2026-11-02\session`.
I report data-quality counts only (rows, candidates per kind per symbol, invariant, out-of-session qty, wall time, peak
working set). I do not run `chain_events_day.py` or `export_chain.py` on real data.

---

## 3. Not in T1b

No tape↔chain join, no scoring, no T1/T2/T3 labelling, no γ / Δ, no spot, no outcomes. No database access by me, no
S3, no Dhan, no network, no recorder or retail box, no runner change. No order code. The real chain export is the
operator's.

---

## 4. As built (2026-11-03, same session, after `/model` Sonnet)

Departures from the text above, and facts the build established:

1. **Rule 23 and ruling R-1.** The plan said no fixture run before 15:45 IST. The operator ruled (R-1, 2026-11-03) that the
   08:30-15:45 refusal is a retail-box rule and Local may run now. **No override existed to use:** `tests/test_tape_t1a.py`
   `rule23()` has none and `tests/run_offline.sh` says "no override flag". `tests/test_tape_t1b.py` therefore carries its own,
   `TAPE_RULE23_OVERRIDE_R1=1`, which lifts only the time window, prints the ruling on its first line, and leaves the
   `ulimit -v` clause as T1a has it (a no-op on Windows, where `resource` does not exist). No T1a file was edited.
2. **Mutant harness is line-ending aware.** `services/tape_runner/recorder.py` is CRLF in a Windows checkout, so a `
` anchor
   matches 0 times; `tests/tape_t1b_mutants.py` converts the anchor to the file's own EOL. `tests/tape_t1a_mutants.py` has the
   same anchor for `M-T1A-RUNNER-IMPORTS` and was **not** touched or re-run here.
3. **Events read minute rows for THIN.** The prompt says events come "from the cycle rows"; THIN is per minute, so `build_cycle`
   returns each token's per-minute depth beside its bins and `events.candidates` uses both. Still one input file.
4. **`export_chain.py` uses `sys.path[:0] = [_ROOT]`**, not `sys.path.insert`, so that `export-select-only` can stay a strict
   name-based scan (`insert` is a forbidden call name) with no exemption.
5. **Generator self-check.** `gen_cycle.build` asserts that an independent reference (`statistics.pstdev` / `median`, exact
   `Fraction`s) finds exactly the hand-planted events, and that the 2<z<3 case really sits in [2, 3) at both bins, before any
   guard compares the code to it.
6. **Merge anchor is an interpretation.** "Within 15 minutes of the previous counted event" is read as 15 minutes from the
   FIRST counted event of that (kind, K) (D-12). With a 5-minute run cadence the same K cannot recur sooner than 10 minutes, so
   `merged_n` is at most 2 on real data; the 3-event test uses runs 2-4 minutes apart. The alternative reading (a chain: each
   merged event extends the window) would give different counts on real data. The scoring SQL's author should confirm which one
   v0.2 means.
