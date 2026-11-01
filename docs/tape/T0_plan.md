# T0 plan — tape raw-only runner + classification library

Phase **T0** of `claude/tape_design_v0.1.md`. Written Sun 2026-11-01 on branch `tape/t0-raw`, worktree `~/wt-tape-0`,
base `232a3bc`. **Authority, highest first:** this session's T0 prompt (incl. amendments A-1..A-3), then
`docs/tape/tape_preregistration_v0.1.md` (staging `c6c5cea`, sha256 `28637412…1e873`, operator-confirmed), then the
design doc. The design doc (`claude/tape_design_v0.1.md`) is **not on this box** (not in the clone, not on
`staging/main`), so it was not read; every pinned decision below comes from the prompt or the pre-registration. Where
the prompt leaves something open, the decision is marked **[D-n]** so the operator can overrule it before the build.

## 0. What §0.3 found (layout facts the plan depends on)

| Fact | Consequence |
|---|---|
| Engine is a flat repo of scripts; packages are `merdian_compute/` (pure, stdlib-only, 4 modules) and `core/`; **no `services/`** | `services/tape_runner/` is new. `services/__init__.py` is added so `python -m services.tape_runner` resolves |
| `pyproject.toml` packages **only** `merdian_compute` (retail installs it pinned by SHA) and lists no subpackages | `merdian_compute/tape/` is **not** shipped to retail by setuptools (a subpackage needs listing). Correct for T0: the tape library is not part of the retail contract (`docs/interfaces/retail_compute_contract.md`). `merdian_compute/__init__.py` is **not** edited, so steps 24/25 (import purity, contract) see no change |
| Tests are standalone scripts (no pytest on the box, none installed); `tests/run_offline.sh` = **30 steps**, each `python3 tests/X.py \| tail -1` + `${PIPESTATUS[0]}` check, rule-23 guard at the top | Tape tests follow the same idiom: stdlib-only scripts, last line is the verdict, mutants inside. Appended as **steps 31 and 32** after step 30's pair (TD-S93-NEW-1) |
| Python 3.12.3; `kiteconnect` **not installed** system-wide, `boto3` 1.34.46 system-wide; systemd 255. **Build correction 2:** the runner's venv already exists at `/var/lib/tape/venv` (user `tape`, Python 3.12, kiteconnect 5.2.2, boto3 1.43.123) | The unit runs `/var/lib/tape/venv/bin/python`; `install.sh` never creates or modifies a venv. Tests never import `kiteconnect` or `boto3` (fakes injected; real modules imported lazily in the live path only) |
| Box clock **`Etc/UTC`**, NTP synchronised; 1.8 GB RAM, 7.3 GB free on `/` | `kiteconnect` builds timestamps with naive `datetime.fromtimestamp` (box-local tz). See §2.3 for the fix; 2 GB spool cap fits on the disk |
| User `tape` exists (uid 995, nologin); `/etc/tape` and `/var/lib/tape` exist, mode 700, owned by `tape` | `install.sh` does not create the user; it creates `/var/lib/tape/{spool,state,manifest}` |
| Engine already has a Kite consumer: `ws_feed_zerodha.py` (`KiteTicker, KiteConnect`) | Not imported or reused: it carries `requests` and the engine's Supabase path. The tape runner shares no code with the engine |

Test runs use `( ulimit -v 2000000; … )` per this session's prompt. Run on a Sunday, so rule 23's hour window does not bind
(ruling S95-A); the `ulimit` clause does.

## 1. Module layout

```
merdian_compute/tape/__init__.py        docstring only; imports nothing
merdian_compute/tape/classify.py        PURE: classify(prev, pkt) -> Trade; MinuteAccumulator   (NOT imported by the runner)
services/__init__.py                    empty
services/tape_runner/__init__.py        empty
services/tape_runner/__main__.py        argv -> main(); os._exit(code) (twisted thread must not hold exit)
services/tape_runner/config.py          constants: windows, times, exit codes, S3 bucket/prefixes, cap; env-var NAMES
services/tape_runner/clock.py           Clock protocol: now_ns(); SystemClock; IST helpers (seg_start, minute_label)
services/tape_runner/instruments.py     resolve(kite, today) -> Universe; strike window + grow-only logic
services/tape_runner/serialize.py       packet/ctl -> ndjson line; datetime -> ISO-8601 +05:30
services/tape_runner/segments.py        SegmentWriter: per-symbol .part files, rotation on 5-min boundary, gzip on close
services/tape_runner/uploader.py        Uploader: queue -> md5 -> PutObject -> ETag check -> delete; backoff; manifest
services/tape_runner/stats.py           per-minute counters, gaps, reconnects, spool HWM, subs history; persisted state
services/tape_runner/recorder.py        Recorder: the timeline state machine; owns ticker callbacks; step(now)
services/tape_runner/smoke.py           --smoke path
services/tape_runner/tape-runner.service, tape-runner.timer, install.sh, requirements.txt
tests/test_tape_t0.py                   all 11 guards + fakes (FakeKite, FakeTicker, FakeS3, ManualClock)
tests/tape_mutants.py                   mutant harness: copy tree -> apply one patch -> run one guard -> must FAIL
docs/tape/T0_plan.md, docs/tape/T0_install.md
```

**[D-1] The runner imports nothing from `merdian_compute`.** The pure helpers it needs (segment start, strike window)
live in `services/tape_runner/`. This keeps "classify is not wired into the runner" checkable by one grep (§7 guard
`no-db-no-dhan` also asserts no `merdian_compute` import under `services/tape_runner/`).

## 2. Packet schema

### 2.1 Packet record (one ndjson line per Kite tick)

```json
{"k":"pkt","sym":"NIFTY","role":"OPT","recv_ns":1793598901234567890,"recv_ist":"2026-11-02T09:15:01.234567+05:30",
 "instrument_token":12345,"last_price":…,"last_traded_quantity":…,"average_traded_price":…,"volume_traded":…,
 "total_buy_quantity":…,"total_sell_quantity":…,"ohlc":{…},"oi":…,"oi_day_high":…,"oi_day_low":…,
 "last_trade_time":"2026-11-02T09:15:00+05:30","exchange_timestamp":"2026-11-02T09:15:01+05:30",
 "depth":{"buy":[{"price":…,"quantity":…,"orders":…}×5],"sell":[…×5]}, …every other key Kite supplied…}
```

- **[D-2] Every key the parser supplies is kept** (the prompt's list is the minimum; `mode`, `tradable`, `change` also
  ride along). Nothing is renamed, rounded or dropped. `sym`/`role` (`IDX|FUT|OPT`) are added from the resolved universe
  so a segment file is readable without the instrument dump; `recv_ist` is `recv_ns` rendered for humans.
- Index packets carry no `last_trade_time`, `depth`, `oi` (Kite sends a 32-byte full packet for indices); absent keys
  stay absent — never filled with 0 or null ("NULL is a gap, never a zero").
- The recorder stores packets as received. Quantity (Δ`volume_traded`) is the library's business, never the recorder's.

### 2.2 Control records (same stream, same files)

`{"k":"ctl","ctl":"connect|disconnect|reconnect|subscribe|error|rotate","recv_ns":…,"recv_ist":…, …detail}`

| ctl | When | Detail |
|---|---|---|
| `connect` | `on_connect` | `pid`, `process_start_ns`, `n_tokens` |
| `disconnect` | `on_close` | `code`, `reason` |
| `reconnect` | `on_reconnect` | `attempt` |
| `error` | `on_error`, `on_noreconnect`, writer/uploader faults | `code`, `reason` (no tokens, no keys, no URLs with query strings) |
| `subscribe` | every subscribe call | `tokens` added, `reason` (`index_future`, `open_window`, `grow`), `centre_strike`, `atm_strike` |
| `rotate` | first record of every segment file | `seg`, `prev_seg`, `process_start_ns` |

**[D-3] Connection-level ctl records are written to every symbol's open segment**, so each file stands alone for gap
analysis; `subscribe` goes only to its own symbol's file. A `rotate` record opening each file also marks process
restarts (a new `process_start_ns` mid-day = a restart; the pre-registration's quarantine rule 4 needs that).

### 2.3 Timestamps

`recv_ns` = `time.time_ns()` (UTC epoch, box clock, chrony-synchronised). All rendered times are ISO-8601 with
`+05:30`. **`kiteconnect` builds `last_trade_time` / `exchange_timestamp` with naive `datetime.fromtimestamp(epoch)`,
i.e. in the box's local zone — `Etc/UTC` here.** Labelling that value `+05:30` would shift every timestamp by 5h30
(the TD-029 shape). The serializer therefore recovers the epoch exactly with `naive.timestamp()` (the inverse of
`fromtimestamp` in the same process zone) and renders `datetime.fromtimestamp(epoch, IST).isoformat()`. A test pins
it under `TZ=UTC` and `TZ=Asia/Kolkata` (same output both). The unit also sets `TZ=Asia/Kolkata` (belt and braces;
the serializer is correct without it).

## 3. Session timeline (IST; injected `Clock` everywhere)

| Time | Action | Failure |
|---|---|---|
| boot+60 s / install | `OnBootSec=60` start: before 08:50 → exit 0 with no Kite call (the token was read too early; the 08:50 trigger starts a fresh process); after 15:40 → re-ship the spool, exit 0; otherwise as below from that moment (review finding 4) | — |
| 08:50 | timer starts unit. `kite.profile()` | any exception → log `TOKEN_FAIL` (type only, never the message body if it could echo a token), heartbeat `state=TOKEN_FAIL`, **exit 78** |
| 08:55 | `kite.instruments("NFO")`, `("BFO")`; `kite.ltp(["NSE:NIFTY 50","BSE:SENSEX"])` for index tokens | exception → retry every 30 s until 09:10, then exit 1 (systemd restarts) |
| 08:55 | open the websocket; subscribe index + front future (`MODE_FULL`) | — |
| 09:00 | options window around ATM from `kite.ltp` — **gated, see [D-4]** | — |
| every minute | heartbeat; grow check; state snapshot | — |
| disconnected > 60 s | `kite.profile()` probe every 60 s, outside the recorder lock (review finding 3) | `TokenException`/`PermissionException` → close segments, drain ≤ 60 s, `TOKEN_FAIL`, **exit 1** (restart re-reads the token; 78 if still bad); any other error → keep running |
| ≥ 09:20 and feed connected ≥ 60 s | closed-day check — **see [D-4] as amended** | — |
| SIGTERM | close segments, drain ≤ 60 s, heartbeat `STOPPED`, exit 0, no daily report (review finding 6) | — |
| 15:40 | stop: close all segments, drain uploads (≤ 15 min), daily report, `MANIFEST.sha256`, exit 0 | uploads still failing at 15:55 → files stay in spool, report counts them `failed`, exit 0 (next start re-ships them) |

**Late start / restart.** The timeline is a state machine evaluated at `now`, so a restart at 11:00 runs every due step
at once (profile, resolve, connect, options) and records from there. A start after 15:40 recovers the spool (§4.4) and
exits 0 without connecting.

**Resolution.** For `NIFTY` (NFO) and `SENSEX` (BFO), filter `name == SYMBOL`:
options = `segment` `*-OPT` with the minimum `expiry ≥ today` (the front weekly — on expiry day that is today);
future = `segment` `*-FUT` with the minimum `expiry ≥ today`. Index tokens come from the `kite.ltp` response (expected
256265 / 265; a mismatch is logged, the response wins). Strikes are the sorted distinct strikes of the front expiry;
**windows count listed strikes, not points**, so 50/100-step grids need no constant.

**[D-4] Closed-day gate — AMENDED by the review of 2026-11-01 (commits `8ec2faf`, `57aae3d`).** The rule in force:
the check is due at **≥ 09:20 IST** and only once the feed has been **connected for ≥ 60 s**. **CLOSED** requires
(i) no index/future packet dated today, (ii) for **every** symbol both the **index and the future** witness present
and stale, and (iii) the **REST quote** confirming every index's last timestamp stale. A quote error, an incomplete
quote or a missing witness is **UNKNOWN → keep recording**; nothing closes on absence or on an error. Why: as first
built, the 08:55 subscribe-time snapshots alone (all stale) closed the day if no live tick arrived by 09:16, and
exit 0 is not restarted. The original text below is kept for the record and is superseded.

*Original D-4 (superseded):* **Two clarifications forced by the prompt itself.**
1. *Kite index packets carry no `last_trade_time`* (32-byte full index packet). The check reads the index packet's
   `exchange_timestamp`, falling back to `last_trade_time` if a future feed adds it, and the front future's
   `last_trade_time` as a second witness.
2. *The prompt subscribes options at 09:00 but checks at 09:16, and the `closed-day` guard requires a closed day to
   subscribe no options.* Resolution: the options window is subscribed at 09:00 **or later, at the first packet dated
   today** (index or future). Verdicts at 09:16:
   - a witness dated today → open (options already subscribed or subscribed now);
   - every witness present and dated before today → **CLOSED**: write `session/<date>/CLOSED` (JSON: witnesses, their
     timestamps), upload it, exit 0, options never subscribed;
   - no packet at all → ask `kite.quote(index)` for its `timestamp`/`last_trade_time`; stale → CLOSED; today → open;
     quote fails → **not closed**: subscribe options, keep recording, log `CLOSED_CHECK_UNKNOWN`.
   **Absence is not a verdict** (CLAUDE.md settled list): only a positively stale date closes the day; a feed outage
   on an open day must not stop the recorder with an exit 0 that systemd will not restart.

**Window and grow-only.** At open: ATM = listed strike nearest the index LTP; window = ATM ± 20 listed strikes (NIFTY),
± 15 (SENSEX), CE and PE → 82 + 62 option tokens + 4 index/future = 148 (Kite cap 3,000 per connection). Each minute,
ATM is recomputed from the latest index packet; when `|pos(ATM) − pos(centre)| > 12` the centre moves to ATM and
the new window's tokens not yet subscribed are added. **Never unsubscribe**, including on reconnect (the full set is
re-sent in `on_connect`). Every change uploads `session/<date>/subscriptions_<HHMMSS>.json`: every token with
`sym, role, strike, opt_type, tradingsymbol, expiry, added_minute (HH:MM IST), reason`, cumulative.
This is the pre-registration's "subscribed window at T".

## 4. Segments and upload

### 4.1 Keys (bucket `meridian-tape-raw`, A-1)

| Object | Key |
|---|---|
| raw segment | `<SYMBOL>/<IST date>/seg_<HHMM>.ndjson.gz` |
| subscriptions | `session/<IST date>/subscriptions_<HHMMSS>.json` |
| closed marker | `session/<IST date>/CLOSED` |
| daily report | `session/<IST date>/daily_report_<IST date>.json` |
| manifest | `session/<IST date>/MANIFEST.sha256` (last object of the day) |

**[D-5]** Session objects live under `session/` so a `<SYMBOL>/` prefix holds only segments.

### 4.2 Rotation

A record's segment = `floor(recv_ns → IST, 5 min)`. **[D-6] Segment assignment uses the box receive clock, not
`exchange_timestamp`**: receive time is monotonic per process, present on every record (incl. ctl and index
packets), and makes "no packet lost or duplicated" provable; the exchange timestamp is kept verbatim in the record
for the library. "Exchange-aligned" = boundaries at IST :00/:05 (the IST offset is a whole number of 5-minute blocks
from UTC, so this is also UTC-aligned). Rotation fires on (a) the first record whose segment differs, or (b) the
main-loop tick crossing a boundary, so a quiet symbol's segment still closes on time. 09:19:59.9 → `seg_0915`,
09:20:00.0 → `seg_0920`.

Files: `spool/<SYMBOL>/<date>/seg_<HHMM>.ndjson.part` (plain, line-buffered, `flush()` each tick batch). On close
(**as amended, review finding 5**): `fsync`, atomic rename to `seg_<HHMM>.ndjson.closed` (never replacing one:
`_c1`, `_c2` …), enqueue; the **upload thread** gzips it — never the websocket thread. Gzip writes
`seg_<HHMM>.ndjson.gz` with **`mtime=0` and no filename in the header** (deterministic bytes, so a
re-upload after a crash is byte-identical and idempotent), `fsync`, delete `.part`, enqueue. Writing plain-then-gzip
means a crash loses at most the unflushed tail, never the whole segment (a killed gzip stream has no trailer).

### 4.3 Upload (A-3: write-only key)

One upload thread: take `.gz` (or session JSON) → stream md5 + sha256 → `put_object(Bucket, Key, Body=<file>,
ServerSideEncryption="AES256", ContentMD5=<b64 md5>)` → **delete local only if `ETag.strip('"') == md5_hex`**.
`ContentMD5` makes S3 reject a corrupted body itself; the ETag compare is the verification the prompt names
(single-part SSE-S3 ⇒ ETag = md5). Mismatch or exception → file kept, retried with exponential backoff
1, 2, 4 … 60 s (cap), attempts counted. No `HeadObject`/`GetObject` anywhere. Every success appends
`{key, bytes, md5, sha256, attempts, uploaded_ns}` to `manifest/<date>.ndjson` (local, kept); `MANIFEST.sha256` at
15:40 is `sha256sum` format (`<sha256>  <key>`) over the day's uploads incl. the daily report.

botocore config: `retries={"mode":"standard","max_attempts":3}`, connect 5 s, read 30 s; region from env.

### 4.4 Spool, cap, recovery

- **Cap 2 GB** over everything under `spool/` (tracked counter, re-walked each minute). Exceeded → ctl `error
  SPOOL_CAP`, flush and close open `.part` files **without deleting anything**, heartbeat `state=SPOOL_CAP`, **exit 75**
  (`RestartPreventExitStatus` holds 75). Nothing outside `/var/lib/tape` is touched.
- **Start-up recovery** (every start, any date): `.part` of a segment earlier than the current one → renamed to
  `.closed` + enqueued (gzipped by the upload thread); `.closed` → enqueued; `.part` of the current segment (restart
  inside a segment) → reopened in append mode, with a newline written first if it ends in a torn line (review
  finding 7); any `.gz` / session file present → enqueued.
- **Immutability (review finding 2):** the receive time is read inside the recorder lock; a closed segment is never
  reopened (a late record goes to the open/next segment with its own `recv_ns`; counted as `late_records_this_process`);
  a `.gz` is never overwritten — an existing file or an already-uploaded key (local manifest) gives
  `seg_<HHMM>_r1.ndjson.gz`; a byte-identical re-gzip after a crash reuses the existing file. A previous day's leftovers ship under their own date keys.
- At 1.8 GB RAM the writer holds no packet buffers beyond the file buffer; the upload thread streams from disk.

## 5. Heartbeat, state, daily report (A-2: no database)

- **Heartbeat** `/var/lib/tape/heartbeat.json`, atomic (`tmp` + `rename`) each minute: `ts_ist, state
  (WAITING|RECORDING|CLOSED|STOPPING|DONE|TOKEN_FAIL|SPOOL_CAP), pid, process_start_ist, connected, packets_last_min
  {sym}, last_packet_ist {sym}, n_subscribed, spool_bytes, upload_queue, uploads {ok,retried,failed}`. The same fields,
  compact, as one journald line per minute (`TAPE_HB …`).
- **State** `/var/lib/tape/state/<date>.json`, rewritten each minute: the counters below, so a mid-day restart resumes
  the day's report instead of starting a second one. Each process start is appended to `restarts` (with the previous
  process's last state) — the pre-registration quarantines a day restarted for a token failure.
- **Daily report** `daily_report_<date>.json`, per symbol: `packets`; packets per minute for `IDX`, `FUT`, and
  `ATM±3` (CE+PE at the 7 strikes around that minute's ATM); `feed_gaps_gt10s` and `feed_gaps_gt60s` (intervals with no
  packet of any instrument of the symbol, 09:15–15:30, measured on `recv_ns`; the 60 s list is separate); `reconnects`;
  `uploads {ok, retried, failed}`; `spool_high_water_bytes`; `subscribed_count` over time (minute → count);
  `last_packet_ist`; **`clock_skew` (build correction 3)**: per symbol the median, max and min of
  (`recv_ns` − `exchange_timestamp`) in seconds, computed from the *serialised* `+05:30` string (i.e. after the
  UTC→IST conversion), over packets whose exchange date is the session date (older snapshot packets are counted
  as `stale_excluded`); `verdict` = `FAIL` if the median is negative or above 3 s, `NOT_EXERCISED` if no same-day
  packet exists. The smoke test prints the same section and exits 3 with a banner on `FAIL`; plus day-level `restarts`, `closed`, `classified=null` (T0 does not classify).
  Completeness % (pre-registration rule 4) is **derivable** from the per-minute counts; T0 does not compute verdicts.

## 6. Failure behaviour

| Failure | Behaviour | Exit / restart |
|---|---|---|
| token invalid at start | `TOKEN_FAIL` | 78, no restart |
| token dies mid-session (WS 403) | after 60 s disconnected, `profile()` probe (no lock); token error → ctl `error TOKEN_FAIL`, segments closed, uploads drained ≤ 60 s, heartbeat `TOKEN_FAIL` | **1** → restart re-reads `kite_token.env`; profile fails → 78 |
| SIGTERM (`systemctl stop`, shutdown) | segments closed, uploads drained ≤ 60 s (inside `TimeoutStopSec=90`), heartbeat `STOPPED` | 0, no restart |
| crash mid-line (SIGKILL/OOM) | next start reopens the current `.part`, repairs the torn line, ships earlier ones | systemd restart |
| WS drop | ctl `disconnect`, `reconnect`; recording continues after reconnect; gap visible in report | none |
| S3 down | files accumulate in spool, retried with backoff | 75 at 2 GB |
| instrument dump fails | retry 30 s until 09:10 | 1 → restart |
| unhandled exception in writer/main loop | ctl `error`, flush `.part` files | 1 → restart (RestartSec 10) |
| box reboot mid-session | timer `OnBootSec=60` starts the unit 60 s after boot; it records from then (state file resumes the day); recovery ships leftovers | — |
| unit started after 15:40 | recovery uploads only | 0 |

The runner never places, modifies or queries orders: the only Kite calls are `profile`, `instruments`, `ltp`,
`quote`, and the ticker. A static guard (`no-db-no-dhan`, extended) asserts no `place_order|modify_order|cancel_order`
string appears under `services/tape_runner/`.

## 7. Classification library (`merdian_compute/tape/classify.py`)

Pure functions over packet dicts (the recorded schema). Stdlib only, no clock, no randomness, no I/O.

`classify(prev, pkt) -> Trade(qty:int, side:"BUY"|"SELL"|"UNCL"|None, price:float|None)`:
1. `prev is None` → baseline: `qty=0, side=None` (never a trade).
2. `dv = pkt.volume_traded − prev.volume_traded`; `dv ≤ 0` → `qty=0, side=None` (no trade; a negative delta is a
   reset and the next delta is measured from this packet).
3. Quote **at the previous packet**: `bid = prev.depth.buy[0].price`, `ask = prev.depth.sell[0].price`,
   `p = pkt.last_price`. Valid quote: `0 < bid ≤ ask`. Then: `p ≥ ask` → BUY; `p ≤ bid` → SELL; `bid < p < ask`:
   `p > mid` → BUY, `p < mid` → SELL, `p == mid` → tick test vs `prev.last_price` (`>` BUY, `<` SELL, `==` UNCL).
4. Anything else (no depth, a zero side, crossed quote) → **UNCL, with its quantity** — counted, never dropped.

`MinuteAccumulator`: `add(minute_label, trade)`; per minute `buy_qty, sell_qty, uncl_qty, trades (packets with dv>0),
vwap`. **Invariant asserted in tests:** `buy+sell+uncl == Σ dv>0` exactly. vwap of a delta uses the
average-traded-price identity `(atp·vol − atp_prev·vol_prev)/dv` when both ATPs are present and the result is
positive, else `last_price` — **[D-7]**, a refinement the prompt does not forbid; the guard tests the classification
and conservation, not vwap.

Minute labels are supplied by the caller (from `exchange_timestamp`), so the library never reads a clock.

## 8. Tests and mutants

Two files, stdlib only, run offline with no network and no credentials. `FakeKite` (profile / instruments / ltp /
quote), `FakeTicker` (records subscribe / set_mode calls; the test fires `on_connect`, `on_ticks`, `on_close`,
`on_reconnect`), `FakeS3` (returns the true md5 as ETag, or a corrupted one, or raises), `ManualClock`. The
`Recorder` is driven synchronously: `step(now)` and `uploader.process_once()` — no threads, no sleeps in tests.

`tests/test_tape_t0.py [--root DIR] [--only GUARD]` runs the guards against the tree at `DIR` (default: repo);
last line `TAPE T0 PASS (11/11)` or `FAIL`. `tests/tape_mutants.py [--repeat N]` copies the tree to a temp dir,
applies **one** exact-string patch (asserting it matched exactly once — `MUTANT NOT APPLIED` is a FAIL, the S95
lesson), runs the named guard with `--root`, and requires FAIL; the control (unpatched copy) must PASS. `--repeat 5`
prints the 5/5 lines for the evidence.

| Guard | What makes it fail (Rule 0 sentence) | Mutant(s) — the patch |
|---|---|---|
| `classify-synthetic` | seeded streams (5 seeds) with planted sides: < 80 % of volume correct, or buy+sell+uncl ≠ Σ deltas, or a first packet producing qty>0 | **M-T0-MID-RULE-FLIPPED** (`p > mid → SELL`, `p < mid → BUY`); **M-T0-UNCL-DROPPED** (accumulator skips UNCL qty) |
| `classify-purity` | AST scan of `merdian_compute/tape/`: an import of `time`, `random`, `socket`, `ssl`, `http`, `urllib`, `requests`, `asyncio`, `secrets`, `uuid`, or a call `.now(` / `.utcnow(` / `.today(` | **M-T0-WALLCLOCK** (`import time` + `time.time()` in classify) |
| `segments-rotate` | packet at 09:19:59.9 not in `seg_0915`, or 09:20:00.0 not in `seg_0920`; across 10,000 packets over 4 boundaries, the multiset of packet ids read back from the gz files ≠ the ids sent | **M-T0-NO-ROTATE** (rotation check disabled → one file) |
| `upload-verify` | local file gone without an ETag==md5 PutObject; a corrupted ETag leaves no file or no retry | **M-T0-DELETE-BEFORE-UPLOAD** (unlink before put); **M-T0-ETAG-IGNORED** (compare removed) |
| `subs-grow-only` | after a > 12-strike move, an original-window token missing from the ticker's subscribed set, any `unsubscribe` call, or `subscriptions_*.json` lacking an `added_minute` for each token | **M-T0-SHRINK-SUBS** (grow replaces the set and unsubscribes the old window) |
| `ctl-records` | forced `on_close` + `on_reconnect` not yielding `disconnect` and `reconnect` records, or packets after reconnect not recorded | **M-T0-DROP-CTL** (ctl writes for disconnect/reconnect removed) |
| `spool-cap` | 50 MB cap + always-failing S3: exit ≠ 75, or any spool file deleted | **M-T0-CAP-DISABLED** (cap check returns False) |
| `token-fail` | failing `profile()` exits ≠ 78, or the unit file's `RestartPreventExitStatus=` line lacks the token `78` | **M-T0-RESTART-ON-78** (unit line becomes `RestartPreventExitStatus=75`) |
| `closed-day` | stale-dated index/future packets: no `CLOSED` object uploaded, exit ≠ 0, or any option token subscribed | **M-T0-NO-CLOSED-CHECK** (closed check returns open) |
| `fence` | unit file missing any of: `User=tape`, the three `EnvironmentFile`s, `MemoryMax=400M`, `CPUWeight=20`, `Nice=10`, `LimitAS=2000000000`, `WorkingDirectory=/var/lib/tape`, `Restart=on-failure`, `RestartSec=10`, `RestartPreventExitStatus=78 75`, `ReadWritePaths=/var/lib/tape`, `ProtectSystem=strict`, `NoNewPrivileges=true` | **M-T0-NO-MEMORYMAX** (line deleted) |
| `no-db-no-dhan` | under `services/tape_runner/`: import of `supabase`, `psycopg`/`psycopg2`, `dhanhq`/`dhan*`, `requests`, `merdian_compute`, `core`, `dotenv`; a `postgres://`/`postgresql://`/`supabase.co` string; `place_order`/`modify_order`/`cancel_order` | **M-T0-IMPORTS-DHAN** (`import dhanhq` added to `recorder.py`) |

Plus non-guard unit checks inside the same file (count toward its cells, not the 11): timestamp rendering under two
`TZ`s; deterministic gzip bytes; resolution picks the front expiry and future; state round-trip across a simulated
restart; daily-report gap lists (one 12 s and one 75 s planted gap).

**Engine suite wiring.** `tests/run_offline.sh`: header and every `N/30` label → `N/32`; append after step 30:
`31/32 tape T0 guards (11)` → `python3 tests/test_tape_t0.py`, and `32/32 tape T0 mutants (14, each must be
caught)` → `python3 tests/tape_mutants.py`. Both pure Python, no fixtures, no golden day (rule-23 class of steps 8–10).
Steps before → after: **30 → 32**.

## 9. Fencing and install

`tape-runner.service` (exactly the prompt's directives, plus hardening that does not contradict them):

```
[Unit] Description=MERIDIAN tape raw recorder (T0)  After=network-online.target  Wants=network-online.target
[Service] Type=simple  User=tape  Group=tape
EnvironmentFile=/etc/tape/kite_api.env  EnvironmentFile=/etc/tape/kite_token.env  EnvironmentFile=/etc/tape/aws.env
Environment=TZ=Asia/Kolkata PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/var/lib/tape PYTHONPATH=/var/lib/tape/app/current
ExecStart=/var/lib/tape/venv/bin/python -m services.tape_runner
WorkingDirectory=/var/lib/tape  MemoryMax=400M  CPUWeight=20  Nice=10  LimitAS=2000000000
Restart=on-failure  RestartSec=10  RestartPreventExitStatus=78 75
ReadWritePaths=/var/lib/tape  ProtectSystem=strict  NoNewPrivileges=true  PrivateTmp=true  ProtectHome=true
```

(`EnvironmentFile=` is one path per line; the `fence` guard checks all three.) No `[Install]` section — the unit is
timer-driven only. `tape-runner.timer`: `OnCalendar=Mon..Fri *-*-* 08:50:00 Asia/Kolkata`, `Persistent=true`,
`[Install] WantedBy=timers.target`.

**Env-var names [D-8]** (values never read by this session, never printed by the runner): `ZERODHA_API_KEY`
(kite_api.env), `ZERODHA_ACCESS_TOKEN` (kite_token.env) — **build correction 1**, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_DEFAULT_REGION` (aws.env), optional `TAPE_BUCKET` (default `meridian-tape-raw`). If the operator's files use other
names, `config.py` is the one place to change. `T0_install.md` gives a names-only check
(`sudo sed -n 's/=.*//p' /etc/tape/*.env`) — it prints names, never values (rule 19).

**Daily token.** `kite_token.env` must hold a token valid for the day **before 08:50**. Refreshing it is out of T0's
scope (no runbook exists on this box); a stale token is caught as `TOKEN_FAIL` / exit 78 and is visible in the heartbeat.

`install.sh` (operator runs `sudo bash services/tape_runner/install.sh` from `~/meridian-tape-dev` after the merge):
1. **Refuses** Mon–Fri 08:30–15:45 IST (starts nothing during market hours) and refuses unless run as root.
2. Checks `id tape`, the three `/etc/tape/*.env` files exist (existence only).
3. Copies `services/` (only, committed content via `git archive HEAD`) into `/var/lib/tape/app/<sha12>/` (root-owned,
   0755), points `/var/lib/tape/app/current` at it (**build correction 2: no `/opt` path**).
4. Checks — does not create or modify — `/var/lib/tape/venv`: imports `kiteconnect`, `boto3` as user `tape` and
   requires the versions pinned in `requirements.txt` (`kiteconnect==5.2.2`, `boto3==1.43.123`, the installed ones).
5. Creates `/var/lib/tape/{spool,state,manifest}` owned `tape:tape`, mode 700.
6. Installs the unit + timer to `/etc/systemd/system/`, `daemon-reload`, `systemd-analyze verify`, `enable` +
   `start` **the timer only**; prints `systemctl list-timers tape-runner.timer`. Never starts the service.

**Smoke test** (`--smoke`): env-var names present → `profile()` → resolve → print subscription list size → one 60 s
websocket connection with the packet count → exit 0 if connect + subscribe succeeded (0 packets on a weekend is a
PASS). Writes nothing to the spool or S3. Run under the same fence with
`sudo systemd-run --uid=tape --gid=tape -p EnvironmentFile=… (×3) -p Environment=PYTHONPATH=/var/lib/tape/app/current
--pipe --wait /var/lib/tape/venv/bin/python -m services.tape_runner --smoke`.

## 10. Build order (Sonnet session)

1. `kiteconnect` source (read in place from `/var/lib/tape/venv`, 5.2.2; `pip` is not on the box) to confirm callback names,
   `MODE_FULL`, the packet dict keys and the `fromtimestamp` use before the fakes are written. Not installed into the repo.
2. Tests first: `tests/test_tape_t0.py` with fakes, all guards, against stub modules → every guard FAILs (the
   must-fail run is recorded).
3. Library, then serialize/clock/segments/uploader/stats/instruments/recorder/smoke, unit + timer + install.sh.
4. Guards PASS; `tests/tape_mutants.py` → 14/14 caught (DROP-CTL split into its disconnect and reconnect halves); `--repeat 5` → 5/5 for every row.
5. Wire steps 31–32; full suite `( ulimit -v 2000000; bash tests/run_offline.sh )`, last line recorded.
6. `bash -n install.sh`; `systemd-analyze verify` on the unit files with paths rewritten to a temp dir (no install).
7. `docs/tape/T0_install.md`; commit on `tape/t0-raw`; push to `staging` only.

## 11. Open points for the operator (none blocks the build)

- **[D-4]** closed-day gate semantics (options at first today-dated packet ≥ 09:00; no-packet ⇒ quote, unknown ⇒ not closed).
- **[D-8]** env-var names inside `/etc/tape/*.env`.
- S3 bucket region (taken from `AWS_DEFAULT_REGION`).
- The design doc is not on the box; if it pins anything above differently, this plan follows the prompt and the
  pre-registration, and the difference should be recorded as a slip.

## 12. Build corrections applied (operator, 2026-11-01, before the build)

1. Credential names `ZERODHA_API_KEY` (`/etc/tape/kite_api.env`) and `ZERODHA_ACCESS_TOKEN` (`/etc/tape/kite_token.env`);
   AWS names unchanged. Single place: `services/tape_runner/config.py`.
2. No `/opt` path. The venv is the existing `/var/lib/tape/venv`; the code is installed to `/var/lib/tape/app/<sha12>`
   (root-owned) with `current` pointing at it. `requirements.txt` pins the **installed** versions (kiteconnect 5.2.2,
   boto3 1.43.123), not the 5.0.1 / 1.34.46 this plan first named.
3. Clock-skew section in the daily report and the smoke test (§5). Rule 0 sentence: a naive timestamp read in the wrong
   zone gives a median of ±19,800 s, which is outside [0, 3] — the unit checks `u_report_gaps_and_skew` and
   `u_smoke_skew_fails_loudly` construct exactly that case and assert FAIL / exit 3.

D-4 and D-6 accepted as written. One refinement of D-4: CLOSED needs at least one witness and every present witness
stale (not "all four present"), so a closed day with a missing future snapshot still closes.

## 13. Review fixes (fresh-eyes review, 2026-11-01; one commit each, test + mutant caught 5/5)

| Commit | Fix | Guard | Mutants |
|---|---|---|---|
| `8ec2faf` | (a) `--smoke` makes one real `PutObject` to `_smoke/<UTC>.txt` (real bucket, region from `AWS_DEFAULT_REGION`, ContentMD5 + SSE-S3) and compares ETag with md5; FAIL → exit 5. (c) closed-day rule: ≥ 09:20, index AND future witnesses stale for every symbol, REST quote confirms; otherwise keep recording | `smoke-s3`, `closed-day` | SMOKE-ETAG-IGNORED, SMOKE-NO-PUT, CLOSED-BEFORE-0920, CLOSED-ON-SNAPSHOT, CLOSED-ONE-WITNESS |
| `940ea64` | finding 2: receive time inside the lock; never reopen a closed segment; never overwrite a `.gz` (`_r1`) | `segment-race` | TIME-BEFORE-LOCK, REOPEN-CLOSED, GZ-OVERWRITE |
| `c045695` | finding 3: mid-session token death → probe after 60 s disconnected → close, drain ≤ 60 s, `TOKEN_FAIL`, exit 1 | `token-midsession` | NO-TOKEN-PROBE, PROBE-UNDER-LOCK |
| `5dc221c` | finding 6: SIGTERM → close, drain ≤ 60 s, exit 0 | `sigterm` | NO-SIGTERM-HANDLER, TERM-NO-CLOSE |
| `f5e08b3` | finding 7: newline repair when a `.part` is reopened | `torn-line` | NO-NEWLINE-REPAIR |
| `527565f` | finding 4: `OnBootSec=60`; a start before 08:50 exits 0 untouched | `boot-start` | NO-ONBOOT, EARLY-START-RUNS |
| `c8767fd` | finding 5: gzip on the upload thread (`.closed` hand-off, never replaced) | `gzip-offthread` | GZIP-ON-WS-THREAD, CLOSED-OVERWRITE |
| `57aae3d` | finding 4 follow-up: the closed check waits for 60 s of connected feed (late/boot/install starts) | `closed-day` | CLOSED-NO-SETTLE |

Region (review item 1): no defect — the S3 client takes `AWS_DEFAULT_REGION` (`__main__._s3`); no region literal in the
runner. Not done (operator decision): finding 8 (retries re-hash the file each attempt; the spool cap stops the day).
Counts: guards 11 → 18, mutants 14 → 32, controls 18/18, each 5/5.
