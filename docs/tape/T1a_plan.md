# T1a plan — offline processor: raw segments → classified minutes → G3 report

Phase T1a of `claude/tape_design_v0.1.md`. Branch `tape/t1a-offline` from engine `main` `a269408`, worktree
`~/wt-tape-2`. Planned 2026-11-02 (after 15:45 IST), built in the same session after `/model` Sonnet.

The design doc `claude/tape_design_v0.1.md` is **not on this box** (`find /` finds no copy). §2.4's minute columns are
therefore taken from the prompt (`buy_qty, sell_qty, uncl_qty, gap_qty, trades, vwap, bid_qty_5, ask_qty_5, oi,
oi_delta, exch_ts_max`), not from the doc. If §2.4 differs, the CSV is the thing to change.

Scope: data quality only (completeness, classified share, rule mix, invariants). **No join with chain data, spot
outcomes, agreement, lead time or range-by-group** (pre-registration v0.2, hash `71950f92…4800`); guard
`proc-no-outcomes` enforces it.

---

## 0. What the T0 sources say (read before designing)

| Source | Fact this plan depends on |
|---|---|
| `serialize.py` `packet_record` | packet line = `{"k":"pkt","sym","role","recv_ns","recv_ist", …every Kite key verbatim}`; a Kite key that collides with ours is renamed `kite_<key>`. `exchange_timestamp` / `last_trade_time` are ISO strings with `+05:30` (epoch recovered first, TD-029-safe). |
| `serialize.py` `ctl_record` | `{"k":"ctl","ctl":<kind>,"recv_ns","recv_ist", …detail}`. Kinds: `connect` (`pid, process_start_ns, n_tokens, first`), `disconnect` (`code, reason`), `reconnect` (`attempt`), `error` (`code, reason`), `subscribe` (`tokens, reason, centre_strike, atm_strike`), `rotate` (`seg, prev_seg, process_start_ns`). |
| `recorder.py` `_ctl_all` / D-3 | connection-level ctl (`connect`, `disconnect`, `reconnect`, `error`) is written to **every** symbol's open segment; `subscribe` only to its own symbol's file. A new process writes `connect` with its own `process_start_ns`; every file opens with a `rotate`. |
| `recorder.py` `_record` | an unknown token is written under `_UNKNOWN/` with `sym=None, role=None`. Roles are `IDX`, `FUT`, `OPT`. |
| `recorder.py` `_flush_subs` | `session/<day>/subscriptions_<HHMMSS>.json` (`_2`, `_3` … on a same-second name clash) = `{"day","written_ist","n","tokens":[{token,sym,role,strike,opt_type,tradingsymbol,expiry,added_minute,reason}]}`; each file is the **cumulative** set (grow-only), so the latest file is a superset. |
| `recorder.py` `_stop` | `session/<day>/daily_report_<day>.json` then `session/<day>/MANIFEST.sha256` = `"<sha256>  <key>\n"` per uploaded key, sorted, latest row per key; the manifest does **not** list itself. |
| `uploader.py` `key_for` | key = `TAPE_KEY_PREFIX` + spool-relative path with `/`. Production prefix is empty, so `NIFTY/2026-11-02/seg_0915.ndjson.gz`. A rehearsal key starts `_rehearsal/` (never a production day). |
| `segments.py` names | segment of a record = floor(`recv_ns`, 5 min) (D-6, box clock, not exchange time). Closed name `seg_HHMM.ndjson.closed`, never replacing one: `seg_HHMM_c1…` (restart reopened and closed the same 5-minute slot). Gzip never overwrites: `seg_HHMM[_cN]_r1.ndjson.gz` … unless byte-identical. **Collision rule for this tool:** `seg_(\d{4})(?:_c(\d+))?(?:_r(\d+))?\.ndjson\.gz`, processed in order (HHMM, c, r); every variant is a distinct object and is read; duplicate lines across them are removed (§2.3). An `_r` file after an append-mode restart can be a **superset** of the earlier object, so duplicates are expected, not an error. |
| `segments.py` late records | a record whose segment is already closed goes into the open / next segment **with its own `recv_ns`**: a file can hold records older than its label. |
| `classify.py` | `classify(prev, pkt)` reads only `volume_traded`, `last_price`, `average_traded_price`, `depth.buy[0].price`, `depth.sell[0].price`. `prev is None` → no trade; `dv <= 0` → no trade ("a negative delta is a reset"); invalid quote → UNCL with its qty; `p>=ask` BUY, `p<=bid` SELL, mid rule, then tick test vs `prev.last_price`. `MinuteAccumulator` has no gap column, so T1a uses its own accumulator. |
| `tests/test_tape_t0.py` | `full_pkt(token, price, vol, day, hms, bid, ask)` / `idx_pkt` shapes; `g_classify_purity` scans **every** `merdian_compute/tape/*.py` for `FORBID_MODS = {time, random, socket, ssl, http, urllib, requests, asyncio, secrets, uuid}` and `.now/.utcnow/.today` calls — the new modules are inside that scan and must pass it. `g_no_db_no_dhan` already forbids `merdian_compute` imports in `services/tape_runner/`. |
| `tests/rehearsal/feed.py` | option/future packet: `tradable, mode, instrument_token, last_price, last_traded_quantity, average_traded_price, volume_traded, total_buy/sell_quantity, ohlc, change, last_trade_time, oi, oi_day_high/low, exchange_timestamp, depth{buy,sell}×5{quantity,price,orders}`; index packet has no volume/depth/oi. `rehearsal_seq` / `rehearsal_batch` ride along on rehearsal packets only. |
| `tests/tape_mutants.py` | mutant = one exact-string patch on a copied tree, must match exactly once ("MUTANT NOT APPLIED" is a FAIL), guard run with `--root`, control must PASS. T1a copies this harness shape. |
| `install.sh` step 3 | **`git archive HEAD services`** — ships *all* of `services/`. A `services/tape_offline/` would be installed onto the recorder box. See D-9. |
| `merdian_compute/__init__.py` | imports `cycle, gamma, pin, volatility` (stdlib-only, offline step 24 proves it), so `import merdian_compute.tape.replay` stays stdlib-only on Windows. |

---

## 1. Decisions

**[D-1] Inputs.** `process_day.py <day_dir> --day YYYY-MM-DD --out <dir> [--verify-manifest]`. `<day_dir>` mirrors the
bucket: `<day_dir>/NIFTY/<day>/seg_*.ndjson.gz`, `<day_dir>/SENSEX/<day>/…`, `<day_dir>/session/<day>/…`. Read-only:
the tool never writes under `<day_dir>`; `--out` must not be inside it (refused). `_UNKNOWN/` is not read (packets
there have no instrument); if present, its file count is reported. Symbols are the directories present among
`NIFTY`, `SENSEX` (fixed list, so a stray directory is not read as a symbol).

**[D-2] Token map** = union of every `subscriptions_*.json`, files in name order; the first file that names a token
fixes its metadata. A token whose metadata differs in a later file is reported under `token_map_conflicts`
(never silently re-mapped). A packet whose token is not in the map is counted `unmapped_packets` and skipped.

**[D-3] Stream rebuild (per symbol, streaming).**
1. Files are listed and **sorted by (HHMM, c, r)** — never by directory listing order — and grouped by HHMM.
2. Each line is parsed once into a compact tuple (key, token, volume, ltp, atp, bid, ask, bid_qty_5, ask_qty_5, oi,
   exch_ts string, line digest); the dict is dropped. A torn / non-JSON line is counted `bad_lines`, never fatal.
3. Sort key = (`exchange_timestamp` epoch, `recv_ns`, line digest). **Deviation from the prompt's "file order"
   tie-break, with reason:** file order changes when files are shuffled or when a collision file holds the same packet,
   and `proc-order` requires identical output under shuffling. The line digest (sha256 of the raw line bytes) is a
   total, content-only order. A packet with no `exchange_timestamp` uses `recv_ns` for the first element and is counted.
4. **Reorder buffer with a watermark.** After each HHMM group is read, every buffered packet whose exchange epoch is
   < (group start − 600 s) is emitted in key order. 600 s = two segments: a late record is written at most into the
   next open segment (segments.py), so two segments is a margin, not a measurement. At end of input everything is
   emitted. A packet whose key is below the last key already emitted for its token is **late beyond the watermark**:
   counted, and dropped from the chain (its volume is not lost: `volume_traded` is cumulative, the next packet carries
   it). Memory = two-to-three segments of compact tuples per symbol (~175k × ~200 B ≈ 35 MB), not a day.
5. **Duplicates**: a packet identical to the previously emitted packet of its token (same line digest) is counted
   `duplicate_packets` and skipped.
6. **Stale date**: a packet whose exchange date ≠ `--day` (yesterday's snapshot before the open) is counted
   `stale_date_packets` and never enters the chain.
7. **Volume regression**: within one day `volume_traded` is monotone; a packet whose volume is **below** its token's
   previous chain packet is a stale snapshot, counted `volume_regressions` and dropped from the chain (it does not
   become `prev`). **Overrules classify.py's "negative delta is a reset" only for the replay**: a mid-day reset would
   re-count the volume between the stale packet and the next one (100, 200, 150, 250 → +100 +100 = 200 counted for
   150 traded). classify.py is unchanged; the replay decides which packets reach it.

**[D-4] Gaps.** Gap events per symbol = `ctl` records of kind `disconnect`, `reconnect`, `connect` (deduplicated by
(kind, recv_ns), since collision files repeat them). A consecutive chain pair (prev, pkt) of a token is a **gap pair**
when a gap event's `recv_ns` lies in (min(prev.recv_ns, pkt.recv_ns), max(...)]. Its whole `dv` is `GAP_VOLUME`: never
classified, never dropped, rule `gap`; `pkt` becomes the new baseline (`prev`). `error` ctl records are reported, not
split on (an error that drops the socket also produces `disconnect`). A process restart (a new `process_start_ns` in
`rotate`/`connect`) always produces a `connect`, so it is a gap too. The first chain packet of a token (start of day,
or a token added by `grow`) is a **baseline**: its cumulative volume is reported as `baseline_qty` (volume before the
token was recorded, side unknown) and is outside the invariant.

**[D-5] Classification and rule.** `classify()` unchanged, called on minimal dicts holding exactly the five fields it
reads (parity with the full packet is a **test**, `u-classify-minimal-parity`, over generated real-shape packets — not
a comment). The rule is computed by `minute.rule_of(prev, pkt)` (`above_ask`, `below_bid`, `above_mid`, `below_mid`,
`tick_up`, `tick_down`, `tick_flat`, `no_quote`) and **checked at runtime**: the side the rule implies must equal
classify's side, else the run aborts (`RuleParityError`) — the rule column cannot silently drift from the side.
Every positive delta lands in exactly one of BUY / SELL / UNCL / GAP.

**[D-6] Minute rows** (`minute.py`, `MinuteBook`). Key = (token, minute), minute = `exchange_timestamp[11:16]` of the
later packet (IST, `+05:30` asserted). A row exists for every minute in which the token has a chain packet.
Columns: `day, sym, role, opt_type, strike, expiry, token, tradingsymbol, minute, buy_qty, sell_qty, uncl_qty,
gap_qty, trades, vwap, bid_qty_5, ask_qty_5, oi, oi_delta, exch_ts_max`. `trades` = non-gap deltas > 0; `vwap` over
non-gap deltas with D-7's price; `bid_qty_5` / `ask_qty_5` = Σ depth quantity over 5 levels at the minute's last
packet; `oi` = last; `oi_delta` = `oi` − previous row's `oi` for the token (empty on the first row or when either is
absent: NULL is a gap, never a zero). Rows held in memory (≈ tokens × minutes ≈ 80k, small), sorted (sym, role,
strike, opt_type, token, minute). Floats `%.6f`, empty for None, LF, UTF-8, header row.

**[D-7] Instrument groups** (per delta, at that moment): `FUT`; `ATM3_CE` / `ATM3_PE` = options within ±3 listed strikes
of ATM, ATM = subscribed strike nearest the symbol's latest index `last_price` in emission order (ties → lower
strike); `OTHER_CE` / `OTHER_PE`; `NO_ATM` for options before the first index packet (reported, counted in option
volume). Delta size distribution per group: exact histogram of `dv` (Counter), p50 / p99 / max (nearest-rank).

**[D-8] G3 report.** Per symbol × hour bucket (`pre_0915`, `09:15-10:00`, `10:00-11:00`, … `15:00-15:30`, `post_1530`)
× group: BUY, SELL, UNCL, GAP quantities; **classified share** = (B+S)/(B+S+U) and, separately, (B+S)/(B+S+U+G);
rule mix (qty and count); delta-size distribution. **Invariant (must be able to fail):** per token,
Σ over **written CSV rows** of (buy+sell+uncl+gap) == `vol_last − vol_baseline` from the replay state (telescoping;
computed independently of the per-delta accumulator, so a delta that is dropped, double-counted or lost between book and
CSV breaks it), and the same in total. A failed invariant makes the verdict `INVALID` and the exit code 4.
**Verdict per symbol**, option volume only (all CE/PE groups, NO_ATM included), volume-weighted, GAP excluded:
`PASS` if share(09:15–10:00) ≥ 0.50 **and** share(10:00–15:30) ≥ 0.70; `FAIL` otherwise; `NOT EVALUATED` if either
window has fewer than **200 non-gap option deltas** (count-based, so it is unit-free; 200 is a floor below which a share
is noise, not a measured threshold, and is stated as such). Also: tokens subscribed with no packets, gap events and gap
pairs per symbol, process restarts, `error` ctl list, all skip counters of D-3, and a copy of selected
`daily_report` fields (`closed`, `restarts`, `reconnects`, `feed_gaps_gt60s`). `g3_report.txt` is a fixed-width
rendering of the same JSON (headline verdicts first).

**[D-9] Not shipped, not imported.** `install.sh` step 3 narrows `git archive HEAD services` to
`git archive HEAD services/__init__.py services/tape_runner` so `services/tape_offline/` never reaches
`/var/lib/tape/app`. This changes nothing the runner imports (it imports only `services.tape_runner.*`). The change
lands at the operator's next install; this session does not run `install.sh` and does not touch `/var/lib/tape`.

**[D-10] Determinism.** No clock, no randomness, no environment in outputs. Sorted keys, `json.dumps(sort_keys=True,
indent=1, ensure_ascii=False)`, floats rounded to 6 places before dumping, `newline="\n"`, UTF-8. `run_manifest.json` =
`{inputs: [{path (relative, '/'), sha256, bytes}], code: {git_sha, dirty}, outputs: {name: sha256}, args}`; `args`
holds the day and flags but **not** absolute paths (so the same day processed from two directories gives the same
manifest). `git_sha` from `git rev-parse` in the CLI (I/O allowed there), `"unknown"` if git is absent.

**[D-11] `--verify-manifest`.** Parse `session/<day>/MANIFEST.sha256`; for every key under `NIFTY/`, `SENSEX/`,
`session/` require the file to exist and its sha256 to match; keys under other prefixes (`_UNKNOWN/`) are listed as
`out_of_scope` and not verified; input files absent from the manifest are listed `unlisted` (failure). Any mismatch /
missing / unlisted → message, **no outputs written, exit 3**. Without the flag the sha256s are still computed (needed for
`run_manifest`), and a missing manifest is reported, not fatal.

**[D-12] Layout and purity.** Pure: `merdian_compute/tape/replay.py` (file-name parsing, compact packet, reorder buffer,
chain, gap test) and `merdian_compute/tape/minute.py` (`rule_of`, `MinuteBook`, groups, histograms, G3 aggregation,
verdict, CSV/JSON/text **rendering to strings**). No file I/O, no clock, no randomness; the CLI feeds lines in and
writes the strings out. CLI `services/tape_offline/process_day.py` (+ `__init__.py`): argparse, gzip reading,
sha256, output writing (`open(..., "w", encoding="utf-8", newline="\n")`), progress line to stderr every 100k packets.
Stdlib only; `os.path` / `pathlib` only, no `resource`, no `fcntl`, no POSIX calls. Python ≥ 3.10.

**[D-13] Exit codes.** 0 = outputs written (verdicts may be FAIL / NOT EVALUATED — a verdict is a finding, not a tool
failure); 2 = usage / input layout error; 3 = manifest verification failed; 4 = invariant violated (outputs are still
written, verdict `INVALID`, so the evidence is inspectable).

---

## 2. Tests (tester-first)

`tests/tape_t1a/gen_day.py` — synthetic segment-day generator. Writes the real layout (gzip mtime=0) and computes
**ground truth itself** (it decides each delta's side by construction: it sets the next price above the ask / below
the bid / at mid with tick etc., and records the side, gap and quantity it planted). Planted features: a burst
spanning a segment boundary; a disconnect → reconnect with a volume jump; a stale-date packet; a stale volume
regression; a `_r1` collision file holding duplicates of the original plus new packets; a duplicated packet line; a
token listed in two subscription files; every rule branch; a token subscribed with no packets; a mid-day `grow` token.
Scale knob for the 4-million-packet performance day.

`tests/test_tape_t1a.py` (guards, `--root`, `--only`, own rule-23 guard: refuses unlimited `ulimit -v` and
Mon–Fri 08:30–15:45 IST, exit 2) and `tests/tape_t1a_mutants.py` (copy of the T0 harness shape, `--repeat 5`).

| Guard | Asserts | Mutants |
|---|---|---|
| `proc-planted-sides` | BUY/SELL/UNCL per (token, minute) == generator truth | M-T1A-SIDES-SWAPPED, M-T1A-UNCL-DROPPED |
| `proc-invariant` | the run's own invariant passes **and** per-token B+S+U+G and per-category totals == generator truth (the bare sum is invariant under relabelling, so the category check is what catches a relabel) | M-T1A-GAP-AS-CLASSIFIED |
| `proc-gap` | the reconnect delta is `gap_qty`, not BUY/SELL/UNCL; baseline packet is not a trade | M-T1A-NO-GAP-SPLIT |
| `proc-boundary` | the boundary burst classified identically to the same burst written into one segment | M-T1A-SEGMENT-RESET |
| `proc-order` | shuffled file order (directory and argument), shuffled lines within a segment → byte-identical outputs | M-T1A-ORDER-BY-FILE |
| `proc-deterministic` | two runs (two output dirs, two input copies) → byte-identical outputs and `run_manifest` hashes | M-T1A-NONDETERMINISTIC |
| `proc-g3-verdict` | planted 80 % / 40 % / empty days → PASS / FAIL / NOT EVALUATED | M-T1A-G3-THRESHOLD-OFF |
| `proc-manifest` | `--verify-manifest` exits 3 and writes nothing on one flipped byte; exits 0 on the clean copy | M-T1A-MANIFEST-IGNORED |
| `proc-pure` | AST: no `time`/`random`/network/`boto3`/`kiteconnect` import, no `.now/.utcnow/.today/open(` call in `minute.py` / `replay.py` | M-T1A-WALLCLOCK |
| `proc-no-outcomes` | text scan of the tool files for chain/outcome identifiers (`gex_`, `strike_snapshots`, `outcome`, `agreement`, `lead_time`, `supabase`, `spot_bars`, …) | M-T1A-JOINS-CHAIN |
| `proc-isolated` | no `services/tape_runner/*.py` imports `tape_offline` / `merdian_compute`; `install.sh` archives only `services/__init__.py services/tape_runner`; every import in the tool is stdlib or `merdian_compute.tape` (AST vs `sys.stdlib_module_names`) | M-T1A-RUNNER-IMPORTS |

Units: `u-classify-minimal-parity` (D-5), `u-rule-parity-abort` (a deliberately inconsistent rule raises),
`u-segment-name-order`, `u-windows-safe` (AST: no `resource`/`fcntl`/`os.fork`/`signal`; every `open(` for text
passes `encoding=` and, when writing, `newline=`).

Wired as steps 33–34 of `tests/run_offline.sh` (32 → 34), appended after step 32, never inside a pair. Performance
check (report only, no gate): a generated 4,000,000-packet day under `ulimit -v 2000000`, wall time and peak RSS via
`/usr/bin/time -v`.

---

## 3. Not in T1a

No S3, no network, no database, no runner change except D-9's archive narrowing, no scoring, no chain/outcome joins.
The real 2026-11-02 day is not on this box; it is processed by the operator on Local.
