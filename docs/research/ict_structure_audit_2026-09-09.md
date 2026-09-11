# ICT structure audit — writers, consumers, and four filed defects

**Date:** 2026-09-09 · **Mode:** read-only. No code changed, no production script run, no RPC
invoked, no `.env` read by any means — so this audit has **no database access** and every claim
below is from the repository at `~/meridian-cc`.

Every claim cites `file:line`. Every absence claim names the object searched. A comment,
docstring or register entry is treated as evidence of *intent*, never of behaviour — only the
code path counts.

---

## 0. What this audit could not read, and why

Two files in scope are blocked from Bash by the permission contract in
`.claude/settings.json`:

| file | rule | effect |
|---|---|---|
| `build_ict_htf_zones.py` | `Bash(*build_ict_htf_zones*)` (deny #21) | substring match, no verb discrimination — blocks `wc`, `ls`, `grep`, and any python invocation whose command line contains the name |
| `capture_cas_close.py` | `Bash(*capture_cas_close*)` (deny #22) | same |

Both rules are **Bash-scoped**. The only `Read(...)` denies in the list are `Read(.env)` and
`Read(//home/ssm-user/**/.env)`. Before the rules were identified, the builder's header
(lines 1–120) was read with the Read tool; nothing further was read from either file by that
route, and **the question of whether the Read tool is sanctioned for them is left to the
operator, not assumed here.**

**Consequence:** every item below that requires the body of those two files is marked
**HALTED**, not answered by inference. Lines from those files that appear below arrived
incidentally in the output of legitimate repo-wide searches that did not name them; they are
cited as such and no follow-up read was attempted.

Halted items: **Q1.1, Q1.2, Q1.3, Q1.5 (builder half), Q1.6 (builder half), F-20 (CAS half)**.

---

## Q1 — Conformance of the writers

### Q1.1 · ADR-005 conformance of `build_ict_htf_zones.py` — **HALTED**

> **→ CLOSED under operator read-grant, 2026-09-09. Answer: "Post-authorisation: HALTED items
> closed" § A1.1.** The HALTED reasoning below stands as written at the time.

ADR-005 states the target rules at `docs/decisions/ADR-005-zone-validity-model.md:35-38`:

| pattern | timeframe | `valid_to` rule | ADR line |
|---|---|---|---|
| OB / FVG | 1H | price-breach **or** `source_bar_date + 7 days`, whichever first | :35 |
| OB / FVG | D | price-breach only — `valid_to = NULL` | :36 |
| OB / FVG | W | price-breach only — `valid_to = NULL` | :37 |
| PDH / PDL | D | date-expire next session | :38 |

Implementation action 2 at `ADR-005:87-89` restates it as the code change owed.

**Cannot be verified.** Confirming it requires reading every `valid_to` assignment in
`build_ict_htf_zones.py`, which is Bash-denied. **What would settle it:** a `valid_to` grep of
that one file, or operator authorisation to use the Read tool on it.

What is visible without reading it — from a repo-wide `ict_htf_zones` search that did not name
the file — is that the writer has an `expire_old_zones` path at `build_ict_htf_zones.py:842`
issuing an `update` at `:861`, and `recheck_breached_zones` at `:747` issuing updates at `:779`
and `:789`. Whether either is timeframe-gated per `ADR-005:89` ("do not call date-expiry path"
for D/W) is exactly what cannot be read.

### Q1.2 · Is `recheck_breached_zones()` invoked every run, and is it the only D/W status path — **HALTED**

> **→ CLOSED under operator read-grant, 2026-09-09. Answer: § A1.2.**

Same blocker. The function is defined at `build_ict_htf_zones.py:747` and `main()` at `:878`;
tracing the `--timeframe` branches through `main()` requires the file body.

Partial, from `run_ict_htf_zones_daily.py:66-67` (readable): the wrapper invokes the builder
twice per run —

```
66    rc_wd   = run_step("WD",   ["build_ict_htf_zones.py", "--timeframe", "both"])
67    rc_h    = run_step("H",    ["build_ict_htf_zones.py", "--timeframe", "H"])
```

so `--timeframe both` and `--timeframe H` are the two argument values actually used in
production. **Which timeframes each value builds is inside the denied file.** A third value
`--timeframe D` and a bare no-argument form are documented at `build_ict_htf_zones.py:24-26`
(docstring, read before the rules were identified) — docstring, therefore not evidence of
behaviour.

### Q1.3 · Evidence that ADR-005 Implementation action 3 (the D/W backfill) ran — **NOT FOUND**

> **→ PARTIALLY ANSWERED under operator read-grant, 2026-09-09: § A1.3. The builder turns out to
> self-heal legacy rows inside its lookback window, which changes what the backfill was for. The
> DB query below remains the only dispositive check for rows OUTSIDE that window.**

`ADR-005:91` describes it: *"Backfill pass. Scan all historical D/W OB/FVG zones currently
`EXPIRED` on date…"*.

Searched, and the object searched is named in each case:

- `/usr/bin/grep -rn` for `ict_htf_zones` across all `*.py`, `*.sql`, `*.sh` in `~/meridian-cc`
  — **no file whose name or content indicates a D/W un-expiry backfill.** The only backfill-
  shaped writer touching this table family is `build_ict_htf_zones_historical.py`, which writes
  a *different* table, `hist_ict_htf_zones` (`:477`, `:511`, `:526-530`).
- `docs/decisions/ADR-005-zone-validity-model.md` itself contains no completion note against
  action 3.

**Stated as an absence, not a conclusion:** no artefact in `~/meridian-cc` records that action 3
ran. It may have run as an ad-hoc SQL statement in the Supabase editor, which would leave no
repo trace. **What would settle it:** `SELECT count(*) FROM ict_htf_zones WHERE timeframe IN
('D','W') AND status='EXPIRED' AND valid_to IS NOT NULL` — a non-zero result means unbreached
D/W zones are still date-expired and the backfill did not run or did not complete.

### Q1.4 · Which file the live import resolves to, and variant reachability — **ANSWERED**

`detect_ict_patterns_runner.py:56` — line number confirmed **unmoved** from the S74 audit:

```
56  from build_ict_htf_zones import detect_1h_zones, upsert_zones
```

This is a bare module import. Python resolves it via `sys.path` to `build_ict_htf_zones.py` in
the working directory. **No variant is reachable through it.**

Eleven non-canonical siblings exist (`ls ~/meridian-cc`): `_PATCHED`, `_PATCHED_TD070V2`,
`_PATCHED_TD071`, `_PRE_S15`, `_PRE_S21`, `_PRE_S21_TD071`, `_PRE_S26_TD079`, `_PRE_TD070V2`,
plus `_historical` and `_historical_PRE_S15`.

Repo-wide `/usr/bin/grep -rn "import build_ict\|from build_ict" --include='*.py'` returns **nine
import sites, and every one imports the bare module name**. None names a variant:

| importer | line | live? |
|---|---|---|
| `detect_ict_patterns_runner.py` | :56 | **yes** — crontab lines 32/33 |
| `detect_ict_patterns_runner_PRE_S31C.py` | :56 | no — itself a variant |
| `detect_ict_patterns_runner_PRE_S17_TD060.py` | :56 | no — itself a variant |
| `experiment_15_pure_ict_compounding.py` | :67 | no |
| `experiment_15_pure_ict_compounding_PRE_S17.py` | :67 | no |
| `experiment_15_smoke.py` | :67 | no |
| `experiment_15_with_csv_dump.py` | :44 | no |
| `experiment_15b_kelly_sizing.py` | :64 | no |
| `patch_kelly_sizing.py` | :101 | no — the string is a patch *anchor*, not an import |

**No variant of `build_ict_htf_zones` is reachable from any entrypoint in this repository.**

### Q1.5 · ADR-004 §5.1 vs the OB detection actually implemented — **ANSWERED for the detector, HALTED for the builder**

> **→ BUILDER HALF CLOSED under operator read-grant, 2026-09-09. Answer: § A1.5.** The register
> claim quoted at the end of this section is **confirmed verbatim by the code**, and the code
> deviates on a further point the register does not record. The detector half below is unchanged.

Canon, `docs/decisions/ADR-004-ict-primitive-canon.md:79-87`:

> A BULL_OB is the last DOWN-close candle immediately preceding a bullish displacement that
> creates a bullish FVG. […] 1. For each bar `i`, check whether a displacement occurred at bar
> `i+1` or within bars `[i+1, i+N]` where N is the displacement window (canonically N=3).
> 2. **A displacement is confirmed only if it creates an FVG** (see §5.2) within the same N-bar
> window. […] 6. The candidate becomes a confirmed OB once the displacement bar closes and the
> FVG is verified.

Implemented, `detect_ict_patterns.py:363-395` (`detect_obs`). Differences, named, not graded:

| # | canon | `detect_obs` | site |
|---|---|---|---|
| **D1** | displacement window `[i+1, i+N]`, N = 3 | a **5-bar close-to-close move**: `mv = pct(bars[i].close, bars[min(i+5, n-1)].close)` | `:378` |
| **D2** | displacement confirmed **only if it creates an FVG** | **no FVG check of any kind.** `detect_obs` neither calls `detect_fvg` (defined `:399`) nor tests for a gap; qualification is a percentage move against `OB_MIN_MOVE_PCT = 0.40` (`:42`) alone | `:380`, `:388` |
| **D3** | the OB is the candle *immediately preceding* the displacement | a **6-bar backward search** from `i` for the last opposite-close candle: `for j in range(i, max(i - 6, -1), -1)` | `:381-386`, `:389-394` |
| **D4** | no dedup rule in canon | a module-local `seen` set forbids one bar being claimed by two OBs | `:374`, `:383`, `:391` |

**Direction mapping matches canon.** `mv >= +threshold` (bullish impulse) → last down-close
candle → `BULL_OB` (`:388-394`); `mv <= -threshold` → last up-close → `BEAR_OB` (`:380-386`).
Note the docstring at `:369-371` labels these the opposite way round ("A bearish OB (BULL_OB) =
bearish candle before bullish impulse") — the prose is confusing, **the code is canon-correct on
direction.**

The builder's own OB detection (`detect_weekly_zones` `:271`, `detect_daily_zones` `:408`,
`detect_daily_zones_history` `:548`) is **HALTED**. `ADR-004:14` records the expected deviation
in prose — *"`detect_daily_zones` tags the prior day's own body as the order block whenever the
day moved ≥0.4%"* — but that is a register claim, not a code reading, and this audit does not
promote it to a finding.

### Q1.6 · TD-051's ±10/±20 PDH/PDL buffer — **PARTIAL**

> **→ CLOSED under operator read-grant, 2026-09-09. Answer: § A1.6. TD-051's ±10/±20 is
> confirmed, at three sites, not two.**

- **`detect_ict_patterns.py` handles no PDH/PDL at all.** `/usr/bin/grep -c "PDH\|PDL"` over
  that file returns **0**. The buffer cannot be in the detector layer because the concept is not
  in the detector layer.
- The only `±20` reference in the non-variant tree is
  `build_ict_htf_zones_historical.py:57`, and it is a **docstring describing a superseded
  state**: *"D-zone single-day validity for non-FVG, fixed +/-20 PDH/PDL band"*. Docstring,
  therefore not evidence of current behaviour, and in the historical builder, not the live one.
- The live builder's PDH/PDL construction sites are visible only as line numbers from a
  repo-wide search: `build_ict_htf_zones.py:293` (`direction: -1`, PDH), `:305`
  (`direction: +1`, PDL), `:689`/`:736`/`:740` (proximity filter — "keep nearest 2 above + 2
  below current price"), `:943`. **Whether `zone_high`/`zone_low` for a PDH/PDL carry a ±N band
  is inside the denied file.** What would settle it: reading `:280-310` of that file.

### Q1.7 · Do the `build_ict_primitives*` variants instantiate `ExecutionLog` — **ANSWERED: none does**

`/usr/bin/grep -c "ExecutionLog"` over each of the **19** files (`build_ict_primitives.py` plus
18 variants — `_PRE_S32`, `_PRE_S32_v2..v5`, `_PRE_S33_v6`, `_PRE_S33_v7`, `_PRE_S35`,
`_PRE_S35_v8p1`, `_PRE_S35_v8p2`, `_PRE_S35_v9`, `S32_PATCHED`, `S32_PATCHED_v2..v5`,
`S33_PATCHED_v6`, `S33_PATCHED_v7`) returns **0 for all 19, including the canonical file.**

**Therefore their absence from `script_execution_log` carries no information about whether they
run.** A script that never instantiates `ExecutionLog` cannot appear in that table whether it
runs hourly or has never been executed. Any inference of the form "it is not in
`script_execution_log`, so it is not running" is unavailable for this entire family.

---

## Q2 — The four filed defects at current line numbers

### Line-number drift against the S74 coupling audit (2026-09-07)

| S74 cited | current | moved? |
|---|---|---|
| `detect_ict_patterns_runner.py:56` (import) | `:56` | no |
| runner `~:261-270` (validity filter) | function at `:259`, filter block `:262-269` | no (within band) |
| runner `~:387` (`expire_prior_session_zones`) | `:387` | no |
| runner `~:479` (`now.hour == 9`) | `:479`, call at `:480` | no |
| runner `~:210-219` (bar read) | function `:206-235`; the read is `:210-219` | no |
| `detect_ict_patterns.py:60` (`POWER_HOUR`) | `:60` | no |
| detector `~:509` (comparison) | `:509` | no |
| detector `~:179-184` (sibling conversion) | conversion is `:179-186`, function `:173-195` | no (band slightly wider than cited) |
| `generate_pine_overlay.py:~182` | `ict_zones` read at `:180-187` | no |
| `generate_pine_overlay.py:~552` | `:552` | no |
| `merdian_daily_audit.py:~616` | `:616` | no |
| `build_trade_signal_local.py:~975` | comment `:975`, **query `:980-985`** | no (the query is 5 lines below the cited anchor) |

**No cited line has moved materially.** The only refinement is `build_trade_signal_local.py`,
where `:975` is the comment header and the executing query begins `:980`.

### F-19 · The `.gte("valid_to")` filter — **PRESENT AS FILED, and wider than filed**

`detect_ict_patterns_runner.py:259-269`:

```
262        sb.table("ict_htf_zones")
263        .select("id, symbol, timeframe, pattern_type, direction, "
264                "zone_high, zone_low, status")
265        .eq("symbol", symbol)
266        .eq("status", "ACTIVE")
267        .lte("valid_from", str(trade_date))
268        .gte("valid_to", str(trade_date))
```

Under ADR-005, D and W OB/FVG zones carry `valid_to = NULL` (`ADR-005:36-37`). A PostgREST
`gte` comparison against NULL is not true, so **every D and W zone written to the ADR-005 rule
is invisible to this query.**

**Every consumer of `ict_htf_zones`, classified by validity predicate:**

| consumer | file:line | predicate | which rows it can see |
|---|---|---|---|
| runner — HTF zone load | `detect_ict_patterns_runner.py:262-268` | `status=ACTIVE` **+ `valid_from<=td`** **+ `valid_to>=td`** | ACTIVE rows with a **non-NULL** `valid_to` covering today. **D/W per ADR-005 excluded.** |
| daily audit — "active for today" | `merdian_daily_audit.py:616-619` | `status=ACTIVE` **+ `valid_to>=audit_date`** | **same exclusion.** Not filed in F-19; found here. |
| runner — 1H rebuild check | `detect_ict_patterns_runner.py:133-138` | `symbol` + `timeframe='H'` + `created_at>=hour_start` | 1H rows only; validity not consulted |
| Pine overlay | `generate_pine_overlay.py:552-556` | `status=ACTIVE` **only** | **all** ACTIVE rows, including `valid_to = NULL` |
| trade signal — HTF attach | `build_trade_signal_local.py:980-985` | `symbol` + `status=ACTIVE` **only** | **Corrected 2026-09-10: none.** The predicate is permissive and *would* admit all ACTIVE rows including `valid_to = NULL` — but the `select` also names **`ict_tier`, which is not a column of `ict_htf_zones`** (16 cols; it is on `ict_zones`, 30), so the call raises **`42703`** and falls into the handler at `:1014`. Measured: `htf_failed=true` on **504 of 504** cycles across two days. This consumer sees **no rows at all**, and the exclusion is one step earlier than F-19. See **TD-S76-NEW-19**, and **TD-S76-NEW-20** for why the fix is not a one-word deletion. |
| replay reader | `replay/replay_detect_ict_patterns_runner.py:142` | replay-date scoped; not a live path | — |

**The split is 2–2 among live consumers by predicate — but only three of the four reads reach the database.** (Corrected 2026-09-10: the trade-signal consumer's `select` raises `42703` before its permissive predicate is ever applied, so it is permissive *in intent* and empty *in effect* — TD-S76-NEW-19.) The runner and the daily audit apply
`gte("valid_to")` and cannot see ADR-005-compliant D/W zones; the Pine overlay and the trade
signal apply no validity predicate and can. So the chart renders zones the signal path cannot
see, *and* the daily audit's `ict_htf_zones / active for today` check
(`merdian_daily_audit.py:623/630/636`) is measuring the same restricted population — it can
report FAIL or a low count while D/W zones exist and are ACTIVE.

**Verdict: present as filed, plus one consumer (`merdian_daily_audit.py`) not named in the
original filing.**

### F-17 · The `now.hour == 9` gate — **PRESENT AS FILED**

```
detect_ict_patterns_runner.py:432    now        = now_ist()
detect_ict_patterns_runner.py:479    if now.hour == 9 and now.minute < 20:
detect_ict_patterns_runner.py:480        expire_prior_session_zones(sb, symbol, trade_date)
```

`now_ist()` is defined `:98-99` as `datetime.now(tz=timezone.utc).astimezone(IST)`, so
`now.hour` is an **IST** hour. The live schedule (crontab lines 32/33) fires the runner at
**10:20 and 10:22 UTC = 15:50 and 15:52 IST**, so `now.hour` is **15** on every live
invocation. **The gate cannot fire under the live schedule.**

**Is `expire_prior_session_zones` the only writer of `EXPIRED` for `ict_zones`?** Yes, within
the non-variant tree. Method: `/usr/bin/grep -rl '"ict_zones"'` over `*.py` excluding
`_PRE_*`/`_PATCHED*`/`fix_*`/`patch_*`/`diag*`/`experiment_*`/`s3[0-9]_*` yields four files
containing the string `EXPIRED`; three are non-writes —

- `build_trade_signal_local.py:975` — a comment
- `merdian_live_dashboard.py:171` — a UI colour label
- `s31_ict_pattern_backfill.py:16` — a docstring

— leaving `detect_ict_patterns_runner.py:388` (docstring) and `:392` (the `update`) as the sole
write site.

**Consequence:** the only path that transitions `ict_zones` rows to `EXPIRED` is gated behind a
condition the live schedule never satisfies.

### F-18 · `POWER_HOUR` compared without IST conversion — **PRESENT AS FILED**

```
detect_ict_patterns.py:60     POWER_HOUR    = dtime(15, 0)   # no new signals after this
detect_ict_patterns.py:509            if bar.bar_ts.time() >= POWER_HOUR:
```

`POWER_HOUR` is an **IST** wall-clock constant, sibling to `OPEN_START`/`SESSION_END` at
`:55-59`. `bar.bar_ts` is a UTC timestamptz from `hist_spot_bars_1m` — established by the
correct sibling in the same file, `time_zone_label` at `:173-195`, whose S10 fix comment at
`:174-179` states the problem explicitly and whose conversion at `:179-186` does
`ts.astimezone(ZoneInfo("Asia/Kolkata"))` **before** comparing against the same constant family.

`:509` performs **no such conversion**. The session 09:15–15:30 IST is 03:45–10:00 UTC, so
`bar.bar_ts.time()` never reaches 15:00 and the gate never evaluates true. **The power-hour
suppression is inert: no bar is skipped by it.**

This is the mirror image of the S10 bug the sibling function was fixed for — there, everything
fell through to `"OTHER"`; here, everything passes the gate.

### F-20 · The bar read vs the 15:29 CAS upsert — **PARTIAL, CAS half HALTED**

> **→ CLOSED under operator read-grant, 2026-09-09. Answer: § A-F20.** The CAS bar *is* in the
> PDH/PDL derivation, and closing the chain surfaced a new defect (F-64) that only becomes
> visible once both halves are read together.

**Runner half, readable.** `load_today_spot_bars` at `:206-235` reads `hist_spot_bars_1m`
filtered `instrument_id`, `trade_date`, `is_pre_market = False`, ordered by `bar_ts`
(`:211-218`) — the whole session, no time ceiling.

`load_prior_session_hl` at `:238-256` derives the prior session's high/low as
`max(float(r["high"]))` / `min(float(r["low"]))` over **all** non-pre-market bars of the most
recent populated prior date, walking back up to 5 days for weekends and holidays (`:242-243`).

**So the runner's PDH/PDL are derived in-memory from `hist_spot_bars_1m` and are used for sweep
detection only.** They are not written to `ict_htf_zones`; the runner's only writes are to
`ict_zones` (`:347`, `:370`, `:391`).

**Where these become the next session's PDH/PDL zones is in `build_ict_htf_zones.py`** —
`:293` and `:305` set PDH and PDL direction — which is Bash-denied. **HALTED.**

**The CAS half is HALTED.** `capture_cas_close.py` is denied by `Bash(*capture_cas_close*)`.
Two of its lines surfaced incidentally in a repo-wide `ict_htf_zones` search that did not name
it: `:24` — *"weekly ICT zone built by build_ict_htf_zones.py inherits that error"* — and
`:61` — *"from 2026-08-03 forward is recoverable. Re-run build_ict_htf_zones.py"*. Both are
docstring prose, so they establish the author's belief that CAS closes propagate into ICT
zones; they do **not** establish the code path, and no follow-up read was attempted.

**What would settle F-20:** reading the upsert target and `bar_ts` slot in
`capture_cas_close.py`, and the daily high/low derivation in
`build_ict_htf_zones.py::detect_daily_zones` (`:408-547`).

---

## The `expected_writes` question — **ANSWERED**

`build_ict_htf_zones.py:891-892` (visible via repo-wide search):

```
891        script_name="build_ict_htf_zones.py",
892        expected_writes={} if args.dry_run else {"ict_htf_zones": 1},
```

`core/execution_log.py:297-303`:

```
297    def _compute_contract_met(self, exit_code: int) -> bool:
298        if exit_code != 0:
299            return False
300        for table, n_expected in self.expected.items():
301            if self.actual.get(table, 0) < n_expected:
302                return False
303        return True
```

The comparison is `actual < expected` — **a floor, not an equality**. With `expected = 1` and
`actual = 163`, `163 < 1` is False, so `contract_met = True`.

**`contract_met` can be False for this script in exactly two ways:** a non-zero exit code
(`:298`), or `actual_writes["ict_htf_zones"] == 0`. Writing 1 zone and writing 163 are
indistinguishable to the contract. It is a liveness check, not a volume check — and
`core/execution_log.py:320-333` documents that as the intended semantics.

For contrast, `detect_ict_patterns_runner.py:682` declares `expected_writes={"ict_zones": 0}`,
described at `:26-30` as *"a FLOOR of 0"* — an explicit acknowledgement of the same semantics.

---

## The 160 → 2 collapse — **LOCATED, not fully quantified**

The measured facts given: the builder writes **160–164** zones per run; the runner logs
`htf=1..3` on the same days. Both exit SUCCESS with `contract_met=true`.

The collapse is at **`detect_ict_patterns_runner.py:262-268`**, and it is the F-19 filter. Two
predicates each remove a population:

1. `.gte("valid_to", str(trade_date))` — removes every row with `valid_to = NULL`, which under
   `ADR-005:36-37` is **all D and W OB/FVG zones**.
2. `.lte("valid_from", str(trade_date))` + `.eq("status", "ACTIVE")` — removes future-dated and
   non-ACTIVE rows.

**What cannot be settled from the repo:** the split of the 160–164 written rows across
timeframe and `valid_to` nullity, which decides how much of the collapse is (1) versus (2).
**What would settle it:** `SELECT timeframe, valid_to IS NULL AS vt_null, status, count(*) FROM
ict_htf_zones WHERE symbol='NIFTY' GROUP BY 1,2,3` — one query, no writes.

---

## The runner's `active=0` in its notes — **ANSWERED**

`active` is the count returned by `load_active_htf_zones` — the F-19 query at
`detect_ict_patterns_runner.py:262-268`. It is **not** a count of zones written.

`hourly_written` is a different quantity from a different code path: `:575-580`, where
`should_rebuild_1h_zones` (`:102-146`) gates a call to `detect_1h_zones` and `upsert_zones`,
and the return value is the number of 1H rows **just upserted**.

So `active=0` alongside `hourly_written=2..3` is consistent and not a contradiction: the 1H
zones were written in this cycle, and the *load* that produced `active` ran earlier in `main()`
against the previous state — and, being subject to the `gte("valid_to")` filter, would in any
case exclude any zone written with `valid_to = NULL`.

**What cannot be settled from the repo:** whether the 1H zones this run wrote carry a non-NULL
`valid_to` (ADR-005 says they should, `:35`) and would therefore have been visible had the load
run after the write. That depends on the builder's 1H `valid_to` assignment — denied file.

---

## Q3 — Every reader and writer of the three tables

Enumeration method: `/usr/bin/grep -rn` over `*.py`, `*.sql`, `*.sh` in `~/meridian-cc`,
excluding `*_PRE_*`, `*_PATCHED*`, `fix_*`, `patch_*`, `diag*`, `experiment_*` unless reachable
from a live entrypoint. **`/usr/bin/grep` was used throughout** — the shell `grep` function
filters recursive results (§D.34.1).

Liveness basis: the 37-line crontab (only lines 32/33 are ICT), `/etc/systemd/system/*`, and
call-chains from those.

### `ict_htf_zones`

| file:line | role | live? | how established |
|---|---|---|---|
| `build_ict_htf_zones.py:825` (upsert), `:779`/`:789` (recheck update), `:861` (expire update) | **writer** | **yes** | 231 runs in `script_execution_log`; invoked by `run_ict_htf_zones_daily.py:66-67`, whose own invoker is not on this host |
| `detect_ict_patterns_runner.py:262` | reader | **yes** | crontab 32/33 |
| `detect_ict_patterns_runner.py:133` | reader (1H rebuild gate) | **yes** | same |
| `detect_ict_patterns_runner.py:56` → `upsert_zones` at `:580` | **writer** (1H) | **yes** | same |
| `generate_pine_overlay.py:552` | reader | **yes** | `run_ict_htf_zones_daily.py:68` chains it as step 3 |
| `merdian_daily_audit.py:589`, `:616` | reader | **not on the 37-line crontab** | absent from `crontab -l`; no systemd unit |
| `build_trade_signal_local.py:980` | reader | **yes** | orchestrator child (`run_merdian_shadow_runner_aws.py`) |
| `merdian_signal_dashboard.py:1017` | **invokes the writer** | operator-triggered | ENH-84 REFRESH ZONES button; HTTP handler, not scheduled |
| `replay/replay_detect_ict_patterns_runner.py:142` | reader | no | replay sandbox, ADR-008 |
| `check_ict_zones.py:8`, `check_htf_zones.py:8`, `check_schema.py:7` | reader | no | ad-hoc probes, on no surface |
| `s31_*.py`, `s30_gate_audit_and_ob_attachment.py:308` | reader | no | session-scoped research |
| `build_ict_htf_zones_historical.py:477` | writer of **`hist_ict_htf_zones`** | no | different table |

### `ict_zones` (M5)

| file:line | role | live? |
|---|---|---|
| `detect_ict_patterns_runner.py:347`, `:370`, `:391` | **writer** (insert / mark broken / expire) | **yes** — crontab 32/33 |
| `detect_ict_patterns_runner.py:289` | reader | **yes** |
| `generate_pine_overlay.py:152`, `:180` | reader | **yes** — chained at `run_ict_htf_zones_daily.py:68` |
| `build_trade_signal_local.py:923` | reader | **yes** — orchestrator child |
| `merdian_daily_audit.py:420`, `:450` | reader | not on the crontab |
| `merdian_signal_dashboard.py:84`, `merdian_live_dashboard.py:647-648` | reader | operator-facing HTTP, not scheduled |
| `scripts/smoke/smoke_probe_marketview_surfaces.py:59`, `:74` | reader | smoke probe, not scheduled |

### `ict_primitives` / `ict_primitive_outcomes`

| file:line | role | live? |
|---|---|---|
| `build_ict_primitives.py:1743`, `:1804`, `:1832` (`ict_primitives`); `:1873`, `:1942` (`ict_primitive_outcomes`) | **writer** | **not on any surface found** — absent from the 37-line crontab, from `/etc/systemd/system/*`, and from the orchestrator child list. **And it instantiates no `ExecutionLog` (Q1.7), so `script_execution_log` cannot confirm or deny that it runs.** |
| `ict_primitives.py:11`, `:59`, `:381` | library — dataclasses and the D-period PDH/PDL helper | imported, not an entrypoint |

**No reader of `ict_primitives` was found** in the non-variant tree by the search above. The
table is written (by a script of unknown liveness) and, as far as this repository shows, read by
nothing. Stated as an absence over the object searched, not as a claim that no consumer exists —
the Marketview frontend lives in a separate repository (`~/meridian-connect`) and was not
searched for this audit.

---

## Findings table

| # | finding | status | evidence |
|---|---|---|---|
| 1 | Runner's HTF load excludes every `valid_to IS NULL` zone — i.e. all ADR-005-compliant D/W zones | **present as filed** | `detect_ict_patterns_runner.py:268` vs `ADR-005:36-37` |
| 2 | `merdian_daily_audit.py` shares the same defect; **not in the original filing** | **new** | `merdian_daily_audit.py:619` |
| 3 | Pine overlay and trade signal apply **no** validity predicate — chart and signal path disagree about which rows exist | **present as filed** | `generate_pine_overlay.py:552-556`; `build_trade_signal_local.py:980-985` |
| 4 | `expire_prior_session_zones` is gated on IST hour 9; cron fires at 15:50/15:52 IST | **present as filed** | `:432`, `:479-480`, `:98-99` |
| 5 | It is the **only** writer of `EXPIRED` for `ict_zones` | **confirmed** | `:392`; three other `EXPIRED` occurrences are comment/label/docstring |
| 6 | `POWER_HOUR` compared against un-converted UTC `bar_ts`; gate is inert | **present as filed** | `detect_ict_patterns.py:60`, `:509` vs correct sibling `:173-195` |
| 7 | `expected_writes={"ict_htf_zones": 1}` is a floor; 1 and 163 are indistinguishable | **confirmed** | `:892`, `core/execution_log.py:297-303` |
| 8 | `contract_met` can be False only on non-zero exit or zero writes | **confirmed** | `core/execution_log.py:298-302` |
| 9 | `active=0` with `hourly_written=2..3` is consistent — different code paths | **explained** | `:262-268` vs `:575-580` |
| 10 | `detect_obs` deviates from ADR-004 §5.1 on four named points, chiefly **no FVG confirmation** | **confirmed** | `detect_ict_patterns.py:378-394` vs `ADR-004:82-87` |
| 11 | No `build_ict_htf_zones` variant is reachable from any entrypoint | **confirmed** | nine import sites, all bare-module |
| 12 | **None** of the 19 `build_ict_primitives*` files instantiates `ExecutionLog` | **confirmed** | `grep -c` over all 19 |
| 13 | `run_ict_htf_zones_daily.py` is the chained invoker of the builder (×2) + Pine | **confirmed** | `:66-68` |
| 14 | No repo artefact records ADR-005 action 3 (D/W backfill) running | **absence, object named** | searched `ict_htf_zones` repo-wide; ADR-005 itself |

---

## What this audit could not settle, and what would settle it

| # | question | blocked by | what would settle it |
|---|---|---|---|
| 1 | Does the builder implement ADR-005's three `valid_to` rules? (Q1.1) | `Bash(*build_ict_htf_zones*)` | a `valid_to` grep of that file, or operator authorisation for the Read tool |
| 2 | Is `recheck_breached_zones()` called on every run, and is it the only D/W status path? (Q1.2) | same | reading `main()` `:878-1024` and the `--timeframe` branches |
| 3 | Which timeframes does each `--timeframe` value build? (Q1.2) | same | same. Only `both` and `H` are used in production (`run_ict_htf_zones_daily.py:66-67`) |
| 4 | Does the builder's OB detection deviate from ADR-004 §5.1? (Q1.5) | same | reading `:271-547` |
| 5 | Do live PDH/PDL zones carry a ±N band? (Q1.6) | same | reading `:280-310` |
| 6 | Which daily high/low becomes the next session's PDH/PDL zone? (F-20) | same + `Bash(*capture_cas_close*)` | reading `detect_daily_zones` `:408-547` and the CAS upsert target |
| 7 | Did ADR-005 action 3 run? (Q1.3) | no repo trace | `SELECT count(*) FROM ict_htf_zones WHERE timeframe IN ('D','W') AND status='EXPIRED' AND valid_to IS NOT NULL` |
| 8 | How does 160–164 split by timeframe and `valid_to` nullity? | no DB access this session | `SELECT timeframe, valid_to IS NULL, status, count(*) FROM ict_htf_zones GROUP BY 1,2,3` |
| 9 | Do 1H zones written this run carry non-NULL `valid_to`? | denied file + no DB access | the same query, restricted to `timeframe='H'` |
| 10 | What invokes `run_ict_htf_zones_daily.py`? | invoker not on this host | Windows Task Scheduler export from Local (`MERDIAN_ICT_HTF_Zones_0845`, named at `run_ict_htf_zones_daily.py:64`) |
| 11 | Does `build_ict_primitives.py` run at all? | no `ExecutionLog`, no surface | process listing or an added `ExecutionLog`; **`script_execution_log` cannot answer it** |
| 12 | Does anything read `ict_primitives`? | `~/meridian-connect` not searched | grep that repository |

---

# Post-authorisation: HALTED items closed

**Date:** 2026-09-09 · **Basis:** operator read-grant, this session only, read-only, Read tool
only, scoped to `build_ict_htf_zones.py` and `capture_cas_close.py`. The `Bash(*build_ict_htf_zones*)`
and `Bash(*capture_cas_close*)` denies were honoured — neither filename appears on any command
line, and no alias, variable or wrapper was constructed. No other denied file was read and no
other rule was routed around.

Both files were read **in full** (1,216 and 462 lines). Everything below is a code reading. The
sections above are unchanged except for a pointer line under each HALTED marker.

---

## A1.1 · ADR-005 conformance — **CONFORMS on all three rules, with two carve-outs and one dead constant**

Every `valid_to` assignment in the file. There are **twenty**, and they fall into four groups.

| site | tf · pattern | `valid_to` | ADR-005 rule | verdict |
|---|---|---|---|---|
| `:333`, `:352` | W BULL_OB / BEAR_OB | `None` | `:37` price-breach only | ✅ |
| `:374`, `:393` | W BULL_FVG / BEAR_FVG | `None` | `:37` | ✅ |
| `:472`, `:486` | D BULL_OB / BEAR_OB | `None` | `:36` price-breach only | ✅ |
| `:522`, `:539` | D BULL_FVG / BEAR_FVG | `None` | `:36` | ✅ |
| `:610`, `:624`, `:651`, `:667` | D OB/FVG, history sweep (S69) | `None` | `:36` | ✅ |
| `:1115`, `:1130` | 1H BULL_OB / BEAR_OB | `str(trade_date + timedelta(days=7))` | `:35` breach **or** 7 days | ✅ |
| `:1152`, `:1170` | 1H BULL_FVG / BEAR_FVG | `str(trade_date + timedelta(days=7))` | `:35` | ✅ |
| `:440`, `:452` | D PDH / PDL | `str(target_date)` — same-day | `:38` date-expire next session | ✅ |
| `:297`, `:309` | **W PDH / PDL** | `str(curr["week_end"])` — Friday of the current week | **ADR-005 is silent** | carve-out |
| `:1188`, `:1200` | **1H PDH / PDL** | `str(trade_date)` — same-day | **ADR-005 is silent** | carve-out |

**Verdict: the builder implements all three ADR-005 rules correctly.** Each `None` carries an
inline `# ADR-005 / TD-079` marker naming the rule it satisfies. The 1H seven-day fallback is the
literal `:35` rule.

Two populations ADR-005 does not legislate: `ADR-005:38` specifies date-expiry for PDH/PDL at
**D only**. The builder also emits PDH/PDL at **W** (week-end expiry) and at **H** (same-day
expiry). Both are deliberate authored blocks, not drift — see **§A** below.

**Dead constant (F-63).** `D_FVG_VALID_DAYS = 5` (`:75`) is consumed at exactly one place,
`:508`:

```
508        d_fvg_valid_to = str(target_date + timedelta(days=D_FVG_VALID_DAYS))
```

`d_fvg_valid_to` is **never referenced again**. Both D-FVG zone dicts written below it set
`valid_to: None` (`:522`, `:539`). The comment two lines above at `:498` — *"D-FVG zones get a
longer validity window than D-OB (5 days vs 1)"* — and the file header at `:37` both describe the
pre-ADR-005 behaviour. **No behavioural defect:** `None` is the ADR-005-correct value and the
five-day window is what ADR-005 replaced. It is dead code plus two stale comments.
`EXPIRY_WD` (`:70`), `prev_move` (`:318`, `:1103`) and `direction` (`:706`) are likewise assigned
and never read.

---

## A1.2 · `recheck_breached_zones()` invocation and the `--timeframe` branches

### What each `--timeframe` value builds — `:899-901`

```
899    do_weekly   = args.timeframe in ("W", "both")
900    do_daily    = args.timeframe in ("D", "both")
901    do_1h       = args.timeframe == "H"
```

| value | weekly | daily | 1H | recheck | expire |
|---|---|---|---|---|---|
| `W` | ✔ | — | — | ✔ | ✔ |
| `D` | — | ✔ | — | ✔ | ✔ |
| **`both`** (default) | ✔ | ✔ | **—** | ✔ | ✔ |
| **`H`** | — | — | ✔ | **✗** | **✗** |

**`both` means W+D. It does not include H.** The docstring (`:26`) and the argparse help
(`:882`, *"both=W+D"*) both say so, and the code agrees. This is why production needs two
invocations (`run_ict_htf_zones_daily.py:66-67`).

### Invocation — `:995`, exactly once per symbol, but not on every run

```
995        recheck_breached_zones(sb, symbol, daily_ohlcv, str(target_date), dry_run)
999        expire_old_zones(sb, symbol, target_date, dry_run)
```

Both sit at the bottom of the `for symbol in ["NIFTY", "SENSEX"]` body. The 1H branch above them
ends in an unconditional `continue`:

```
915        if do_1h:
...
919            n = upsert_zones(sb, h_zones, dry_run)
...
923            continue
```

**F-61 — `--timeframe H` runs never call `recheck_breached_zones()` or `expire_old_zones()`.**
They write 1H zones and jump to the next symbol. In production this is benign but load-bearing:
the `both` run at step 1 does the status maintenance for *all* timeframes, and the `H` run at
step 2 does none. If the ordering in `run_ict_htf_zones_daily.py:66-67` were ever reversed, or
the `both` step were to fail while the `H` step succeeded, no zone of any timeframe would be
breach-tested or expired that day — and both scripts would still exit SUCCESS, because
`expected_writes={"ict_htf_zones": 1}` is a floor (existing audit, *The `expected_writes`
question*).

### Is it the only D/W status path — **yes, within this file, and this file is the only D/W writer**

Three status-writing paths exist for `ict_htf_zones`:

| path | line | sets | scope |
|---|---|---|---|
| `upsert_zones` | `:825-829` | `ACTIVE` (from the zone dicts) | whatever was detected |
| `recheck_breached_zones` | `:779-784`, `:789-794` | `BREACHED` | `.eq("symbol")` + `.eq("status","ACTIVE")` + `.eq("pattern_type", …)` — **not timeframe-scoped** |
| `expire_old_zones` | `:861-870` | `EXPIRED` | `.in_("timeframe", ["W","D","H"])` + `.lt("valid_to", today)` |

The runner's imported `upsert_zones` (existing audit, `detect_ict_patterns_runner.py:580`) writes
1H rows only. So for D/W:

- `ACTIVE → BREACHED` — **only** `recheck_breached_zones`, once per day, evaluated against
  `daily_ohlcv[last]["close"]` (`:768`), i.e. the most recent daily **close**, not an intraday
  extreme.
- `→ EXPIRED` — `expire_old_zones`, which **cannot match a D/W OB/FVG** because
  `.lt("valid_to", …)` is never true against NULL. See **§C**.
- `BREACHED → ACTIVE` — re-detection. `upsert_zones` sends `"status": "ACTIVE"` in the payload
  with `Prefer: resolution=merge-duplicates`, so an upsert whose six-column conflict key matches
  an existing row **rewrites that row's status and `valid_to`**.

**Therefore a D/W OB/FVG has exactly two reachable states, ACTIVE and BREACHED**, and the state
is recomputed from scratch against the prior close on every `both` run. That is self-consistent
by design (`main()` orders detect → upsert → recheck → expire, per TD-030/TD-071 at `:925-928`
and `:993-998`), but it means a zone breached intraday and recovered by the close is resurrected
to ACTIVE the next morning.

**F-65 — the S59 daily-PDL exemption is undone by `recheck_breached_zones` on the same run,
conditionally.** `main():978-985` deliberately *skips* `filter_breached_zones` for daily PDH/PDL,
for a reason stated in the code: on the pre-open run `current_spot` is the prior-day **close**,
which on a down day sits inside the new PDL band built from the prior-day **low**, so the filter
would falsely drop it. Twenty lines later `recheck_breached_zones` runs against the *same*
`current_spot` with the exact complementary predicate:

| | keeps / marks | condition |
|---|---|---|
| `filter_breached_zones` PDL (`:727`) | keep | `current_spot > zone_high` |
| `recheck_breached_zones` PDL (`:778-784`) | mark BREACHED | `zone_high >= current_spot` |

With `zone_high = prior_low + 10` (`:449`), the PDL that S59 preserved is marked BREACHED
whenever `prior_close <= prior_low + 10` — a session closing within 10 index points of its low,
which is precisely the down-day-closing-on-the-low case S59 names. The zone is written ACTIVE at
`:988` and flipped to BREACHED at `:995` in the same run. Narrow, but it fires exactly where the
fix was aimed.

---

## A1.3 · ADR-005 action 3 (the D/W backfill) — partial, and the framing changes

Still **no repo artefact** records the backfill running; that finding is unchanged. But reading
the builder changes what the backfill was *for*:

**The daily run self-heals legacy D/W rows inside its own lookback window.** `upsert_zones`
(`:825-829`) conflicts on `(symbol, timeframe, pattern_type, source_bar_date, zone_high,
zone_low)` and merges duplicates, and the payload always carries `"status": "ACTIVE"` and, for
D/W OB/FVG, `"valid_to": None`. A legacy row that is `EXPIRED` with a non-NULL `valid_to` is
therefore **rewritten to ACTIVE / NULL** the next time the same zone is re-detected — and the
S69 history sweep (`:966-968`) re-emits up to `DAILY_LOOKBACK = 60` sessions of D OB/FVG on every
run, while `detect_weekly_zones` walks `WEEKLY_LOOKBACK = 52` weeks (`:940-941`).

So:

- D OB/FVG inside the last **60 sessions** and W OB/FVG inside the last **52 weeks** are
  ADR-005-conformant regardless of whether action 3 ever ran.
- Rows **outside** those windows can only have been fixed by action 3. Nothing in the builder
  reaches them.

`Q1.3`'s proposed query is still the dispositive test, and it is now sharper — restrict it to
rows the sweep cannot reach:

```sql
SELECT timeframe, count(*)
FROM   ict_htf_zones
WHERE  timeframe IN ('D','W')
  AND  pattern_type NOT IN ('PDH','PDL')
  AND  status = 'EXPIRED'
  AND  valid_to IS NOT NULL
  AND  source_bar_date < current_date - INTERVAL '52 weeks'
GROUP  BY 1;
```

A non-zero result is unambiguous: action 3 did not run, or did not complete.

---

## A1.5 · Builder OB detection vs ADR-004 §5.1 — **the register claim is confirmed, and understates it**

This was flagged as the most important question in the audit. The answer:

> **No `fix_*` patch has corrected `detect_daily_zones`. The live file still tags the prior day's
> own body as the order block on a ≥0.4% move — and the S69 patch, the most recent edit to that
> region, deliberately propagated the rule to 59 more sessions.**

The builder contains **three** OB detectors and they implement **three different rules**, none of
which matches ADR-004 §5.1.

### 1 · `detect_daily_zones` `:457-489` — the qualifying bar *is* the zone

```
461        prior_move = pct(prior["open"], prior["close"])
463        if prior_move >= OB_MIN_MOVE_PCT:
467                "pattern_type": "BULL_OB",
469                "zone_high":    max(prior["open"], prior["close"]),
470                "zone_low":     min(prior["open"], prior["close"]),
```

The move is measured on `prior` and the zone is `prior`'s own body. There is no search for a
preceding candle, no separate displacement bar, no FVG test. The code says so itself at
`:457-460`:

> `# NOTE: D-OB definition uses the prior bar itself as the OB (non-standard`
> `# ICT). Flagged S2.a during code review; intentionally NOT changed in`
> `# this patch. Tracked separately as TD candidate.`

**F-60 — and the candle polarity is inverted relative to canon.** `prior_move >= +0.40` means the
prior day closed **up**; that bullish candle's body becomes the `BULL_OB`. ADR-004:79-80 defines
a BULL_OB as *"the last DOWN-close candle immediately preceding a bullish displacement"*.
Symmetrically at `:477-489`, a **bearish** candle becomes the `BEAR_OB` where canon requires the
last up-close candle. This is a stronger deviation than the register records — the register says
the OB is the wrong *bar*; the code shows it is also the wrong *sign of bar*. The zone is a
momentum-continuation body, not an order block.

For contrast, `detect_ict_patterns.py::detect_obs` (existing audit, Q1.5 detector half) **does**
search backward for the last opposite-close candle. So the M5 detector and the D builder disagree
on candle polarity, and they write into the same conceptual `pattern_type`.

### 2 · `detect_daily_zones_history` `:588-627` (S69) — same rule, 60× the volume

Identical body test (`:599`, `:601`, `:615`) and identical zone construction (`:607-608`,
`:621-622`), applied across `DAILY_LOOKBACK = 60` sessions. The docstring states the propagation
was deliberate (`:564-570`):

> `same prior-bar-as-OB definition (the`
> `non-standard-ICT S2.a deviation is preserved on purpose), same`
> `FVG_D_MIN_PCT gap test […] Only the number of sessions`
> `evaluated changes, so the Exp 15 cohort behind WR_BY_PATTERN stays`
> `valid (ADR-009 cohort-translation).`

The reasoning is sound on its own terms — holding the rule fixed is what preserved the cohort
(CLAUDE.md, *"widen the window OR change the rule, never both"*). The consequence is that the
non-canonical rule is now the **dominant** population in `ict_htf_zones` by row count.

### 3 · `detect_weekly_zones` `:322-355` — 8-week unbreached-anchor (TD-070)

Closest to canon on structure: `_find_unbreached_anchor` (`:182-239`) walks back up to 8 weeks
for the most recent **opposing**-direction bar not breached by any intervening bar, and the zone
is that anchor's body. Polarity is canon-correct. Still no FVG confirmation, and the anchor may
be up to 8 bars back where canon says *immediately preceding*.

### 4 · `detect_1h_zones` `:1106-1133` — nearest to canon

```
1106        if curr_move >= OB_MIN_MOVE_PCT and prev["close"] < prev["open"]:
```

Last opposite-close candle immediately preceding the impulse — canon-shaped. Still no FVG
confirmation, and the displacement window is exactly one bar, not `[i+1, i+N]` with N=3.

### Consolidated against ADR-004 §5.1

| canon requirement (`ADR-004:79-87`) | `detect_daily_zones` | `detect_weekly_zones` | `detect_1h_zones` | `detect_obs` (M5) |
|---|---|---|---|---|
| OB is the candle **immediately preceding** the displacement | **the displacement candle itself** | anchor up to 8 bars back | ✅ `prev` | 6-bar backward search |
| OB candle closes **opposite** to the impulse | **❌ same direction** | ✅ | ✅ | ✅ |
| Displacement confirmed **only if it creates an FVG** | ❌ none | ❌ none | ❌ none | ❌ none |
| Displacement window `[i+1, i+N]`, N=3 | window 0 | window 1 | window 1 | 5-bar close-to-close |
| Threshold | `OB_MIN_MOVE_PCT = 0.40` (`:66`) | same | same | same (`detect_ict_patterns.py:42`) |

**No OB detector anywhere in MERDIAN applies the FVG confirmation that ADR-004 §5.1 step 2 makes
the defining test.** That is now established across all four implementations, not three.

---

## A1.6 · PDH/PDL bands — TD-051 confirmed, at three sites

| tf | site | derived from | band |
|---|---|---|---|
| W | `:294-295`, `:306-307` | prior **week** high / low | `± 20` |
| D | `:437-438`, `:449-450` | prior **day** high / low | `± 10` |
| H | `:1185-1186`, `:1197-1198` | **current session's** running high / low | `± 10` |

`zone_high = level + N`, `zone_low = level − N`. TD-051's "±10/±20" is confirmed: **±10 daily,
±20 weekly**, plus a third ±10 site at 1H that TD-051 does not mention.

**All three are absolute index points, symbol-independent.** The band is therefore ~3.3× tighter
in relative terms on SENSEX than on NIFTY:

| | NIFTY ≈ 24,000 | SENSEX ≈ 80,000 |
|---|---|---|
| ±10 band | ±0.042% | ±0.0125% |
| ±20 band | ±0.083% | ±0.025% |

The `:294` comment calls ±20 a *"small buffer"*. No constant governs either value — both are
literals at four sites.

---

## A-F20 · The CAS bar → next session's PDH/PDL — chain closed end to end

### CAS half — upsert target and `bar_ts` slot

`capture_cas_close.py` writes **two** tables:

| target | line | method | conflict key |
|---|---|---|---|
| `market_spot_snapshots` | `:404` | `sb_insert` — plain POST | — |
| `hist_spot_bars_1m` | `:437-438` | `sb_upsert`, `Prefer: resolution=merge-duplicates` | **`instrument_id,bar_ts`** |

The `bar_ts` slot is **canonicalised, not taken from the vendor** (`:420-424`):

```
420        bar_ts_utc = (
421            datetime.combine(trade_day, datetime.min.time(), IST)
422            .replace(hour=CAS_CLOSE_BAR[0], minute=CAS_CLOSE_BAR[1])
423            .astimezone(timezone.utc).isoformat()
424        )
```

`CAS_CLOSE_BAR = (15, 29)` (`:109`). Acceptance is wider than storage: `CAS_CLOSE_BAR_SLOTS =
{(15,29), (15,34)}` (`:115`) is what the Guard-2 assertion tests (`:314`), and a bar arriving at
15:34 is **stored at 15:29** with the true vendor slot preserved in
`market_spot_snapshots.raw.bar_slot_ist` (`:394`). The rationale is at `:414-419` and matches the
CLAUDE.md settled entry — *"tolerance belongs at the boundary; canonicalisation belongs at the
write"*. The row carries `"is_pre_market": False` (`:433`).

### Builder half — which daily high/low becomes the PDH/PDL

`load_daily_ohlcv` (`:120-145`) reads `hist_spot_bars_1m` with exactly these filters (`:127-130`):
`instrument_id`, `is_pre_market = False`, `trade_date` between bounds. Ordering is `bar_ts`
(`fetch_paginated` default, `:97`/`:100`). It then aggregates (`:135-143`):

```
140            "high":  max(float(b["high"]) for b in bars),
141            "low":   min(float(b["low"])  for b in bars),
142            "close": float(bars[-1]["close"]),
```

`detect_daily_zones` takes `prior = daily_ohlcv[prior_dates[-1]]` (`:424-425`) and builds
`PDH = prior["high"] ± 10` (`:437-438`), `PDL = prior["low"] ± 10` (`:449-450`).

**So the chain closes:** the CAS 15:29 bar carries `is_pre_market = False` and a `trade_date`,
therefore it is inside `load_daily_ohlcv`'s filter; it sorts last by `bar_ts`, therefore
`bars[-1]["close"]` **is** the settled close; and its `high`/`low` participate in the daily
`max`/`min`. **The next session's PDH/PDL are built from a prior-day high/low that includes the
auction bar.**

Two consequences worth naming:

1. On an up-settle the 15:29 bar's `high` **is** the settled close (`capture_cas_close.py:16-18`
   documents the shape: open = frozen value, high = close = settled). If the settled close
   exceeds the continuous-session high, **the PDH is set by the auction equilibrium price rather
   than by any traded high.** The band is ±10 points and the observed CAS moves were ~20 points
   (`:17-18`), so this is inside the magnitude that matters.
2. `groupby(rows, key=trade_date)` at `:135` requires rows contiguous by `trade_date`. They are,
   because the sort key is `bar_ts` and it is monotonic with `trade_date`. **No defect here** —
   checked because `groupby` on unsorted input silently fragments groups.

### F-64 — the CAS correction **duplicates** D/W OB zones instead of replacing them

`capture_cas_close.py:59-62` instructs the operator to re-run the builder after a backfill:

> `Historical windows are served fine by /charts/intraday, so every session`
> `from 2026-08-03 forward is recoverable. Re-run build_ict_htf_zones.py`
> `afterwards -- the daily closes will have changed.`

That instruction is correct about the need and wrong about the effect. The upsert conflict key
(`:827-828`) is:

```
symbol, timeframe, pattern_type, source_bar_date, zone_high, zone_low
```

**`zone_high` and `zone_low` are in the key, and for an OB they are the bar's body —
`max/min(open, close)`.** Changing the day's close by ~20 points changes the body bound, which
changes the conflict key, which makes the re-run **insert a new row** rather than update the old
one. The pre-CAS twin, built on the frozen 15:14 close, survives with:

- `status = 'ACTIVE'` — set at write time and never revisited unless price breaches it;
- `valid_to = NULL` — so `expire_old_zones` can never match it (§C);
- a `source_bar_date` identical to its corrected sibling.

**Both rows are then ACTIVE, ~20 points apart, for the same session, indefinitely.** The same
applies to any FVG whose gap edge came from a CAS-affected high. Every session from **2026-08-03**
forward is exposed, for both symbols, on every D and W OB/FVG the sweep re-detects.

The discriminating query — no writes:

```sql
SELECT symbol, timeframe, pattern_type, source_bar_date, count(*), 
       min(zone_high), max(zone_high)
FROM   ict_htf_zones
WHERE  timeframe IN ('D','W')
  AND  pattern_type NOT IN ('PDH','PDL')
  AND  source_bar_date >= '2026-08-03'
GROUP  BY 1,2,3,4
HAVING count(*) > 1
ORDER  BY 4 DESC;
```

Any group of 2 with a `zone_high` spread in the ~10-30 point range is a CAS twin pair.

---

## A · PDH/PDL at D, H and W — deliberate, three different levels, two labels

**All three are authored blocks with their own section comments. None is a pass artefact.**

| tf | site | comment at site | the level it actually represents | validity |
|---|---|---|---|---|
| W | `:288-312` | `# ── Prior Week High / Low (liquidity levels) ──` | prior **week**'s high / low | Mon→Fri of the current week |
| D | `:431-455` | `# ── Prior Day High / Low ──` | prior **day**'s high / low | the target session only |
| H | `:1175-1203` | `# Session high/low as liquidity reference` | **today's own running high / low**, over completed hours only | the target session only |

**Why there is no `PWH`/`PWL` pattern_type: the weekly builder reuses the `PDH`/`PDL` labels for
prior-week levels.** The comment at `:288` names them "Prior Week High / Low" while `:292` writes
`"pattern_type": "PDH"`. The 1H pair is a third thing again — not a "prior" level at all, but the
current session's high-water mark, recomputed on every rebuild.

**F-66 — three semantics, two labels.** Any consumer that branches on `pattern_type` without also
reading `timeframe` conflates prior-day, prior-week and current-session-high. Both breach
functions in this file do exactly that:

```
718        elif pattern == "PDH":            # filter_breached_zones
788        for pattern in ("BEAR_OB", "BEAR_FVG", "PDH"):   # recheck_breached_zones
```

Neither filters on `timeframe`. For the *direction* semantics (PDH = resistance, PDL = support)
that is correct and intended. But it means the 1H "PDH" — today's own high — is breach-tested
against today's close, so it is marked BREACHED on any session that closes at its high.

**F-67 — the 1H PDH/PDL population grows within a session.** `session_high` (`:1177`) rises as
the day progresses, and `zone_high`/`zone_low` are in the upsert conflict key. Each 1H rebuild at
a new high therefore **inserts a new row** rather than updating the previous one. This is the
mechanism behind multiple H `PDH` rows carrying the same `source_bar_date`.

Minor, non-defect: the `src_date` used by the 1H PDH/PDL block at `:1189`/`:1201` is a leaked
loop variable from `:1100`. It is always `str(trade_date)` and the early return at `:1089-1090`
guarantees the loop ran at least once, so there is no `UnboundLocalError` path. Noted only
because it is not obvious from the block itself.

---

## B · Why `detect_1h_zones` produces no OB/FVG

`hourly_written = 2..3` decomposes cleanly:

- **The 2 is structural.** The session PDH + PDL block at `:1176-1203` is guarded only by
  `if completed:` and emits both rows unconditionally. Once `len(completed) >= 2` clears the
  early return at `:1089-1090`, **two rows are guaranteed**, independent of any pattern.
- **The 3rd, when it appears, is exactly one OB or FVG.**

So `hourly_written` is a floor of 2 that says nothing about structure. Three reasons the OB/FVG
contribution is ~0:

**1 · The 0.40% threshold, applied to a single hourly body.** `OB_MIN_MOVE_PCT = 0.40` (`:66`) is
the *same* constant the M5 detector uses, and S69 measured it empirically unreachable there
(30-session maxima NIFTY 0.366% / SENSEX 0.369%). At 1H the test is `pct(curr["open"],
curr["close"]) >= 0.40` — a single hour's open-to-close body, **and** it is conjoined with an
opposite-close predecessor (`:1106`, `:1121`). Two conditions, one of them calibrated for a
different bar size. This is the dominant cause.

**2 · The FVG test is near-unsatisfiable inside a continuously-traded session.** `:1141` requires
`two_prev["high"] < curr["low"]` — hour *i−2*'s high strictly **below** hour *i*'s low, with the
gap ≥ `FVG_MIN_PCT = 0.15%`. Because trading is continuous, hours *i−2*, *i−1*, *i* form an
unbroken price path; a true non-overlap between the outer two requires a monotone two-hour run
that never retraces into the earlier hour's range. Rare by construction, not by calibration.

**3 · The sample per run is 5 OB checks and 4 FVG checks.** `completed` excludes the current
incomplete hour (`:1084-1087`, against **wall-clock** `datetime.now(IST)`, not `target_date`).
The runner fires at 15:50 IST → `current_hour = 15:00` → completed hours are 09:00…14:00 = **6
bars** → `for i in range(1, 6)` = 5 iterations, of which only 4 satisfy `i >= 2` for the FVG
branch. The 09:00 bucket holds only 09:15–09:59, and the 15:00 hour is never evaluated at all,
so the session's last 30 minutes never enter a completed 1H bar under the live schedule.

**Also note the 08:45 IST `--timeframe H` call contributes nothing.** `detect_1h_zones` fetches
`.eq("trade_date", str(trade_date))` (`:1075`) for *today*; pre-market there are no rows, so
`:1079-1080` returns `[]`. Only the runner's in-process call at 15:50 IST produces the 2–3.

**One check before treating "none since 2026-06-03 / 2026-05-20" as settled.** 1H OB/FVG carry
`valid_to = trade_date + 7 days` and `expire_old_zones` includes `H` (§C), so **every 1H OB/FVG
is EXPIRED by construction eight days after it is written**. A query scoped to `status='ACTIVE'`
would return "none" on a healthy system. The two different per-symbol dates suggest a query on
`source_bar_date`/`created_at` rather than status, in which case the threshold explanation stands
— but the dispositive form is:

```sql
SELECT symbol, max(source_bar_date)
FROM   ict_htf_zones
WHERE  timeframe = 'H' AND pattern_type NOT IN ('PDH','PDL')
GROUP  BY 1;
```

with **no** `status` predicate.

---

## C · Is `expire_old_zones` timeframe-gated — **yes, and the docstring is wrong**

```
861        sb.table("ict_htf_zones").update({
862            "status": "EXPIRED",
863            "updated_at": datetime.utcnow().isoformat()
864        }).eq("symbol", symbol).lt(
865            "valid_to", str(today)
866        ).in_(
867            "timeframe", ["W", "D", "H"]
868        ).neq(
869            "status", "EXPIRED"
870        ).execute()
871        log(f"  Expired old W/D/H {symbol} zones before {today}")
```

**Gated to `["W", "D", "H"]` — every timeframe the table uses.** As a filter it is a no-op; the
real gate is `.lt("valid_to", today)`.

**F-62 — the docstring contradicts the code.** `:848-852` states:

> `- Restricted to W and D timeframes. H (intraday) zones use 1-day`
> `  validity (valid_to = trade_date); their expiry basis is unclear`
> `  and intentionally not handled here. See TD-050.`

`H` is in the list. The log line at `:871` says "W/D/H", so the log agrees with the code and only
the docstring is stale — a TD-071-era comment that survived a later widening.

This produces exactly the distribution observed:

| rows | `valid_to` | reached by `.lt(valid_to, today)`? | terminal state |
|---|---|---|---|
| **1H OB/FVG** (`:1115`, `:1130`, `:1152`, `:1170`) | `trade_date + 7d` | ✅ on day 8 | **EXPIRED — all of them, always** |
| 1H PDH/PDL (`:1188`, `:1200`) | `trade_date` | ✅ next day | EXPIRED |
| **D/W OB/FVG** (10 sites, §A1.1) | **NULL** | ❌ — `lt` against NULL is never true | **never EXPIRED by this path** |
| D PDH/PDL (`:440`, `:452`) | `target_date` | ✅ next day | EXPIRED |
| W PDH/PDL (`:297`, `:309`) | week-end Friday | ✅ following Monday | EXPIRED |

**"1H rows all carry a 7-day span and all are EXPIRED; D/W carry NULL" is confirmed for OB/FVG.**
One discrepancy to resolve rather than assume: the code gives **1H PDH/PDL a 1-day span**, not a
7-day one (`valid_to = valid_to = str(trade_date)`, `:1094` → `:1188`/`:1200`). If the sample
showed a uniform 7-day span across *all* H rows, the query was almost certainly scoped to OB/FVG
pattern types. `SELECT pattern_type, valid_to - valid_from, count(*) FROM ict_htf_zones WHERE
timeframe='H' GROUP BY 1,2;` separates the two populations.

`.neq("status", "EXPIRED")` (`:868-869`) is the TD-071 idempotency guard; it is otherwise
status-agnostic, so BREACHED rows past `valid_to` do transition to EXPIRED as TD-071 intended.

---

## New findings raised by the authorised reads

> **Numbering — corrected in Part 2, 2026-09-09.** These eight were first filed as **F-21…F-28**,
> which **collided with the S74 coupling audit** (`docs/audits/coupling_audit_2026-09-07.md`), a
> document this audit cites by finding-ID at `:113`, `:213`, `:233`, `:272`, `:300`, `:393`, `:410`.
> That audit's series runs **F-01…F-59** — its own F-21 is the Pine positioning floor
> (`coupling_audit_2026-09-07.md:592`) and its F-25 the three checks that cannot express failure in
> an exit code (`:600`); F-22, F-26 and F-27 are also occupied (`:593`, `:594`, `:600`). This
> document's eight are therefore renumbered **F-60…F-67**, continuing the S74 series rather than
> restarting it. **All 17 occurrences were rewritten** — 8 in-place definition labels, 8
> summary-table rows, and 1 forward cross-reference at `:323`. New findings continue at **F-68**.
>
> *The brief asked for "four internal cross-references" to be fixed. Measured, there is **one**
> (`:323`, inside the F-20 section, pointing at what is now F-64); the other 16 occurrences are
> definition sites and summary rows. Recorded rather than rounded up.*

| # | finding | severity note | evidence |
|---|---|---|---|
| **F-60** | D-OB candle polarity is **inverted** vs ADR-004 — a bullish candle's body becomes the BULL_OB. Register records the wrong-bar deviation; not the wrong-sign one | the largest population in the table | `:461-489`, `:599-627` vs `ADR-004:79-80` |
| **F-61** | `--timeframe H` skips **both** `recheck_breached_zones` and `expire_old_zones` via the `continue` | benign under current ordering; single point of failure | `:915-923`, `:995`, `:999` |
| **F-62** | `expire_old_zones` docstring claims W/D-only; code includes H | doc drift, no behavioural effect | `:848-852` vs `:866-867`, `:871` |
| **F-63** | `d_fvg_valid_to` computed and never used; `D_FVG_VALID_DAYS` dead; `:498` comment stale post-ADR-005 | dead code + misleading comment | `:75`, `:498`, `:508`, `:522`, `:539` |
| **F-64** | CAS close correction changes OB body bounds → changes the upsert conflict key → **duplicate** D/W zones from 2026-08-03; the stale twin stays ACTIVE with `valid_to = NULL` and is unexpirable | the sharpest of the new findings | `capture_cas_close.py:59-62`, `:420-424`; builder `:827-828`, `:469-470`, `:866-867` |
| **F-65** | S59's daily-PDL exemption is re-breached by `recheck_breached_zones` on the same run when `prior_close <= prior_low + 10` | conditional; fires on the exact case S59 targets | `:978-985` vs `:778-784`, `:449` |
| **F-66** | W and H PDH/PDL are different levels under the same two labels; no `PWH`/`PWL` exists because W reuses `PDH`/`PDL` | consumer-facing ambiguity | `:288-312`, `:431-455`, `:1175-1203` |
| **F-67** | 1H PDH/PDL accumulate within a session — the running session high/low is in the conflict key, so each rebuild inserts rather than updates | row growth, not correctness | `:1177-1178`, `:827-828` |

## Rows of "What this audit could not settle" now closed

| row | question | status after the grant |
|---|---|---|
| 1 | Builder's three `valid_to` rules? | **closed** — §A1.1, conforms |
| 2 | Is `recheck_breached_zones` called every run, only D/W status path? | **closed** — §A1.2, every W/D run, not on `H` runs; yes |
| 3 | Which timeframes does each `--timeframe` value build? | **closed** — §A1.2 table |
| 4 | Builder OB vs ADR-004 §5.1? | **closed** — §A1.5, deviates on 3 of 4 requirements, plus polarity |
| 5 | Do PDH/PDL carry a ±N band? | **closed** — §A1.6, ±20 W / ±10 D / ±10 H |
| 6 | Which daily high/low becomes the PDH/PDL; CAS target and slot? | **closed** — §A-F20 |
| 7 | Did ADR-005 action 3 run? | **narrowed** — §A1.3; query restricted to pre-lookback rows |
| 8 | 160–164 split by timeframe / `valid_to` nullity? | **still open** — needs DB |
| 9 | Do 1H zones carry non-NULL `valid_to`? | **closed** — §A1.1: yes, `trade_date + 7d`; OB/FVG only |
| 10 | What invokes `run_ict_htf_zones_daily.py`? | **still open** — off-host |
| 11 | Does `build_ict_primitives.py` run? | **still open** |
| 12 | Does anything read `ict_primitives`? | **still open** — `~/meridian-connect` unsearched |

Rows 8, 10, 11 and 12 are unaffected by this grant: none is answerable from these two files.

---

# Part 2: the canon layer

**Date:** 2026-09-09 · **Mode:** read-only. No code changed, no production script run, no RPC
invoked, no `.env` read by any means. **No database access** — every claim below is from the
repository at `~/meridian-cc` plus `~/meridian-connect`, and nothing here is evidence about live
row contents.

The two Bash denies that halted Part 1 (`Bash(*build_ict_htf_zones*)`, `Bash(*capture_cas_close*)`)
were re-read from `.claude/settings.json` at the start of this part and honoured: neither filename
appears on any command line below, and no alias, variable or wrapper was constructed. **Neither
file is needed for Part 2** — this part is about a different writer entirely.

Finding IDs continue the S74 coupling-audit series. Part 1's eight are now **F-60…F-67**; Part 2
opens at **F-68**.

---

## Q1 — Which variant wrote the 2025-04 → 2026-05 population

**Answer: `build_ict_primitives.py` (repo root, 90,301 bytes, 2,152 lines), uniquely.** The
identification does not rest on inference — one of the three proposed evidence axes is dispositive
on its own, and one of the three is **unusable in this repository**.

### The axis that does not work here — and why the brief's premise is wrong

`mtime` ordering is **inert**. All 19 variants carry the same mtime to the millisecond:

```
90301  2026-09-05 12:49:24.506601100  build_ict_primitives.py
45128  2026-09-05 12:49:24.507601104  build_ict_primitives_PRE_S32.py
…
75820  2026-09-05 12:49:24.509601112  build_ict_primitives_S33_PATCHED_v7.py
```

That is checkout time for this clone, not authorship time. **Filesystem timestamps in
`~/meridian-cc` date the clone, not the work** — the same class of error as S74 §D.32's `git log -S`
dating a register's transcription rather than a deployment. Git is no better here: every one of the
19 arrived in exactly two bulk commits on **2026-05-25** — `bc1cb85` (production files) and
`3c4c3ce` (`_PRE_`/`_PATCHED` snapshots) — and `git log --follow build_ict_primitives.py` returns
**one commit, never amended since**. So git dates the transcription too.

### The axis that is dispositive — the outcomes column set

The brief names the discriminator correctly. Counting the literal column keys in each variant's
`upsert_outcomes()` insert dict:

| variant (distinct content) | bytes | lines | outcomes cols | `mfe_pct` | `atm_pnl_30m_pct` | `option_pnl_30m` | `option_pnl_source` | `sl_level` |
|---|---|---|---|---|---|---|---|---|
| `_PRE_S32` | 45,128 | 1,140 | **17** | – | – | – | – | – |
| `_PRE_S32_v2` = `_S32_PATCHED` | 55,771 | | 26 | ✓ | ✓ | – | – | – |
| `_PRE_S32_v3` = `_S32_PATCHED_v2` | 56,247 | | 26 | ✓ | ✓ | – | – | – |
| `_PRE_S32_v4` = `_S32_PATCHED_v3` | 57,036 | | 26 | ✓ | ✓ | – | – | – |
| `_PRE_S32_v5` = `_S32_PATCHED_v4` | 60,694 | | 26 | ✓ | ✓ | – | – | – |
| `_PRE_S33_v6` = `_S32_PATCHED_v5` | 61,887 | | 26 | ✓ | ✓ | – | – | – |
| `_PRE_S33_v7` = `_S33_PATCHED_v6` | 67,001 | | 31 | ✓ | ✓ | ✓ | – | – |
| `_PRE_S35` = `_S33_PATCHED_v7` | 75,820 | | 31 | ✓ | ✓ | ✓ | – | – |
| `_PRE_S35_v8p1` | 84,872 | | 32 | ✓ | ✓ | ✓ | ✓ | – |
| `_PRE_S35_v8p2` | 86,604 | | 32 | ✓ | ✓ | ✓ | ✓ | – |
| `_PRE_S35_v9` | 86,864 | | 32 | ✓ | ✓ | ✓ | ✓ | – |
| **`build_ict_primitives.py`** | **90,301** | **2,152** | **37** | ✓ | ✓ | ✓ | ✓ | **✓** |

37 explicit keys plus the server-side `computed_at` default = **the 38-column schema in the brief**.
**No other variant reaches it**; the next-highest is 32. The `sl_*` block (`sl_level`,
`sl_buffer_pct`, `sl_triggered_ts`, `sl_exit_prem`, `pnl_with_sl_pct`) exists in exactly one file:
`build_ict_primitives.py:1925-1933`, written by the ADR-012 v9 patch at `:133-136`, `:513-523`,
`:1137-1181`. `grep 'ADR-012 (S35) v9'` returns 5 hits in the live file and **0** in `_PRE_S35_v9`.

The 19 files hold **12 distinct contents** (md5): each `X_PATCHED_vN` is byte-identical to the
`_PRE_` snapshot taken one step later — the patched-copy deploy pattern from S15, working exactly as
designed. The version chain is strictly nested and monotone in size, confirmed independently by the
`ENH-1NN (SNN) vN` markers: `_PRE_S32` carries none, `_PRE_S32_v3` carries v2, and each successor
carries all of its predecessor's markers plus one.

### The axis that does *not* discriminate — the `primitive_type` set

The brief proposes the emitted `primitive_type` set as evidence. **It cannot discriminate**, because
no variant contains those literals at all. All 14 values (`BULL_OB`, `BEAR_OB`, `BULL_FVG`,
`BEAR_FVG`, `DISPLACEMENT_UP`, `DISPLACEMENT_DOWN`, `SWEEP_HIGH`, `SWEEP_LOW`, `PDH`, `PDL`, `PWH`,
`PWL`, `PMH`, `PML`) are produced by the **detector library**, which every variant imports rather
than embeds — `build_ict_primitives.py:59-77`. `grep -oE '"(BULL_OB|SWEEP_HIGH|PMH|…)"'` over the
live writer returns **zero matches**; the strings live in `ict_primitives.py:189`, `:211`, `:264`,
`:344`, `:410-414`, `:527`, `:542`. Every variant would emit the same set. The observed set does
confirm that **all five wave-1 detectors ran** with `--tfs W,D,H,M5` and `--symbol NIFTY,SENSEX` —
`PMH`/`PML` in particular require `"W" in tfs` (`build_ict_primitives.py:1982-1985`) — but it says
nothing about which writer file ran.

### Which detector library that writer bound to

`build_ict_primitives.py:60-77` prefers `core.ict_primitives` and falls back to a sibling import.
**`core/ict_primitives.py` does not exist** — `core/` holds eight modules (`__init__.py`,
`bs_engine`, `config`, `dhan_client`, `execution_log`, `parameters`, `supabase_client`,
`trading_calendar_gate`) and none is the detector. `ModuleNotFoundError` subclasses `ImportError`,
so the `except` fires and the import resolves to **root `ict_primitives.py` (639 lines)**.
`merdian_reference.json` independently gives that file's `local_path` as
`C:\GammaEnginePython\ict_primitives.py` — repo root on Windows too, not `core/`. So the Q2 reading
below is of the file that actually binds, on both hosts.

### Liveness — unchanged and now stronger

`build_ict_primitives.py` has **no invoker anywhere in either repository**. Searched across `*.py`,
`*.sh`, `*.bat`, `*.ps1`, `*.service`, `*.timer` in `~/meridian-cc`: five hits, all
docstring/comment references (`fill_2026_04_16_breeze.py:87`, `:182`; `ict_primitives.py:15`;
`ict_primitives_PRE_S31B_SWEEP_DEDUP.py:15`; `audit_s32_enh100_falsification.py:76`). Systemd on
this host carries **no MERDIAN unit except the wsfeed family** (`merdian-wsfeed.service`,
`-start.timer`, `-stop.service`, `-stop.timer`, `-alert.service`). And the register agrees in its
own words — `merdian_reference.json` → `files["build_ict_primitives.py"].called_by` =
`["operator (one-shot backfill); future Task Scheduler entry for ongoing emission TBD"]`.

**Uniquely identified.** The one residual: this establishes which *file in this repository* matches
the schema, not that the operator ran that file rather than a Windows-side copy that has since
diverged. What would settle that: an md5 of `C:\GammaEnginePython\build_ict_primitives.py` against
`102ad3b3565b4effe229b90c2a59ef7e`.

---

## Q2 — Is it canon

**Scored on the same four axes as the legacy builder. The canon layer conforms on all four.** This
is the load-bearing result of Part 2: it decides that the corrective path is **"finish S31-C"**, not
"the canon layer is not canon either".

### Order Block — ADR-004 §5.1, `ict_primitives.py:285-367`

| axis | ADR-004 §5.1 | `detect_order_blocks` | verdict |
|---|---|---|---|
| **OB immediately preceding the displacement** | steps 1, 5: displacement in `[i+1, i+N]`; if several candidates, take the **most recent** (closest to impulse start) | `start = max(0, disp_idx - lookback)` (`:328`); `for j in range(disp_idx - 1, start - 1, -1)` (`:331`) — walks **backward, most-recent-first**, `break`s on first qualifier (`:337-338`) | **CONFORMS.** Backward-from-displacement over `[disp-N, disp-1]` is the same set as forward `[i+1, i+N]` |
| **OB candle closes OPPOSITE the impulse** | *"A BULL_OB is the last DOWN-close candle … The OB is opposing direction to the impulse"* (`ADR-004:79`); steps 3-4 | `target_dir = "BEAR" if disp.direction == "BULL" else "BULL"` (`:327`); `if _bar_direction(b) != target_dir: continue` (`:333-334`); then `ob_type = "BULL_OB" if disp.direction == "BULL"` (`:344`) | **CONFORMS — and is the exact inverse of F-60.** The legacy builder makes a *bullish* candle the BULL_OB; here a BULL_OB is built from a **BEAR** candle preceding a bullish displacement |
| **Displacement confirmed only if it creates an FVG** | step 2; validity: *"A canonical OB requires a confirmed FVG in the impulse leg. If no FVG forms, the candle is not an OB regardless of subsequent move"* (`ADR-004:91`) | OB iteration is over `tf_displacements` only (`:315`, `:322`), and `detect_displacements` returns nothing without an FVG: `fvg = fvg_by_ts.get(b.ts); if fvg is None: continue` (`:257-259`) plus a direction-match guard (`:262-263`) | **CONFORMS, and is stricter than the ADR** — see difference D1 |
| **Window `[i+1, i+N]`, N=3** | step 1 "canonically N=3"; §5.1 table + §11: W/D/H = 3, **M5 = 6** | `lookback = DISPLACEMENT_WINDOW_BARS[tf]` (`:305`) = `{"W":3,"D":3,"H":3,"M5":6}` (`:45`) | **CONFORMS.** M5=6 is the ADR's own value, not a deviation |

Two further §5.1 requirements, both met: **body-only zone bounds** — `zone_low = min(open, close)`,
`zone_high = max(open, close)` (`:345-346`), with `wick_low`/`wick_high` pushed to metadata
(`:359-360`), exactly as `ADR-004:94-97` requires; and the **doji guard**
`if _body_pct(b) < min_body: continue` (`:335-336`) against `OB_MIN_BODY_PCT` (`:43`) whose values
`{W:0.5, D:0.3, H:0.2, M5:0.1}` match `ADR-004:106-111` verbatim.

**Named differences (not deviations from a verdict — differences from the ADR text):**

- **D1 — same-bar FVG, not same-window FVG.** `ADR-004:83` says a displacement is confirmed if it
  creates an FVG *"within the same N-bar window"*, and `:379` says *"the bar (or the 3-bar window
  centered on it)"*. The code requires the FVG's middle bar to **be** the displacement bar:
  `fvg_by_ts = {f.source_bar_ts: f …}` then `fvg_by_ts.get(b.ts)` (`:250-257`). **Stricter than
  canon.** Effect: fewer displacements, therefore fewer OBs, never more.
- **D2 — one OB per candle, not one per displacement.** `seen_ob_ts` (`:313`, `:340-342`) drops the
  second and later displacements that resolve to an already-emitted OB candle. The ADR does not
  address the case. Effect: an OB retested by two separate impulses is one row, not two.
- **D3 — `valid_from` is the displacement bar's *open*, not its close.** `valid_from=disp.event_ts`
  (`:354`). `ADR-004:87` says *"The candidate becomes a confirmed OB once the displacement bar
  closes"*; the §4 field list at `ADR-004:60` said `valid_from` is *"when the primitive becomes
  consumable (typically source_bar_ts + 1 TF)"*. The ADR was internally inconsistent here and the
  code took the second reading. **This is the sharpest finding of Part 2 — filed as F-68**, because
  every outcome column is anchored on it. **The inconsistency is resolved by ADR-004 Amendment C
  (`ADR-004` §15, 2026-09-10) — `:87` governs; `:60` is superseded in place and now reads as such
  from its first word, so the superseded wording is quoted above from §15 rather than cited to
  `:60`.** See also *Operator decisions* → D1.

### Fair Value Gap — ADR-004 §5.2, `ict_primitives.py:158-224`

**Conforms on every stated rule.** Geometry: `prev.high < nxt.low` → zone `[prev.high, nxt.low]`
(`:182-183`); `prev.low > nxt.high` → zone `[nxt.high, prev.low]` (`:204-205`) — matches
`ADR-004:126-127` and the `:135-137` zone-bound block exactly. Displacement-bar direction gate:
`mid.close > mid.open` / `mid.close < mid.open` (`:182`, `:204`) — matches `ADR-004:132`. Gap
measure: `gap_pct = (zone_high - zone_low) / mid.open * 100` (`:184`, `:206`) with
`ref = mid.open if mid.open else 1.0` (`:179`) — matches `ADR-004:128` including the
`reference_price = bar[i].open` choice. Threshold `FVG_MIN_PCT` (`:46`) `{W:0.8, D:0.4, H:0.2,
M5:0.08}` — matches `ADR-004:576` (§11 summary row; the same values appear
in §5.2's own table at `:146-151`).

Two differences: **the `elif` at `:204`** makes BULL and BEAR mutually exclusive per window (they
cannot both hold geometrically, so this is free); and **`valid_from = nxt.ts`** (`:192`, `:214`) —
bar `i+1`'s bucket **start**, while the zone's upper bound *is* `nxt.low`, which is not known until
`i+1` closes. Same defect as D3, and on FVGs it is unambiguous rather than arguable, because the
zone literally consumes data from after the anchor. **F-68.**

The `PARTIALLY_FILLED` status of `ADR-004:140` is never emitted — the detector returns every FVG as
`ACTIVE` (`Primitive.status` default, `:91`) and nothing downstream transitions it. Fill state is
carried instead by `ict_primitive_outcomes.retest_status`. Structural, not a defect.

### Sweep — ADR-004 §7.1, `ict_primitives.py:459-556`

**Conforms on the detection rule.** `bar.high > level AND bar.close < level` with
`depth_pct = (high - level)/level*100 >= SWEEP_MIN_DEPTH_PCT` (`:504-506`), mirrored for the low
side (`:513-515`); thresholds `{W:0.2, D:0.1, H:0.05, M5:0.025}` (`:47`) match `ADR-004:360-365`.
Level routing via `_HIGH_SIDE_LEVEL_TYPES` / `_LOW_SIDE_LEVEL_TYPES` (`:54-55`) covers the ADR's
`BSL/PDH/PWH/EQH` and `SSL/PDL/PWL/EQL` sets.

**Named differences:**

- **D4 — the swept level never becomes `SWEPT`.** `ADR-004:368` states *"The swept level (in
  metadata) gets its status updated to SWEPT."* No code path does this: the detector is pure
  (`:14-16`), the candidate filter is `lv.status == "ACTIVE"` (`:491`) against objects that were
  constructed `ACTIVE` moments earlier in the same process, and `valid_to` is documented as staying
  NULL (`:390-391`). Every level ever emitted in the window remains a sweep candidate for every
  subsequent M5 bar in the window. **Bounded in practice** — the close-back-inside test
  (`b.close < lv.level` for a high sweep) requires the level to sit inside that bar's wick, so a
  distant stale level cannot fire. The residual effect is that a level already swept months earlier
  can be swept again, and `swept_level_type`/`_price` report the deepest such level rather than the
  freshest. **F-74.**
- **D5 — sweep direction is a convention the ADR does not state.** `SWEEP_HIGH → direction='BEAR'`,
  `SWEEP_LOW → 'BULL'` (`:528`, `:545`), justified in the docstring as mean-reversion bias
  (`:480-482`). §7.1 assigns no direction. Consequential because `compute_atm_pnl_and_dte` buys
  **PE on every SWEEP_HIGH** and CE on every SWEEP_LOW (`:1023`).
- **D6 — sweeps exist only at M5, and only when D or W is requested.** `compute_levels_and_sweeps`
  is called under `if any(tf in ("D","W") for tf in tfs)` (`build_ict_primitives.py:1982`) and
  always emits at `"M5"` (`:463-464`). `--tfs H` alone produces no levels and no sweeps.

### Prior-period levels — ADR-004 §6.1, `ict_primitives.py:374-452`

Conforms: `level` set, `zone_low`/`zone_high` left NULL (`:439`, `:449`), RTH filter on D only
(`:398-401`), `valid_from` = current period's first bar (`:428`) — and here **no lookahead**, since
the prior period's high/low are fully known at that instant. One consumer-facing ambiguity:
`PMH`/`PML` are stored with `timeframe='W'` and the real period only in `metadata.period`
(`:415-416`, `:440`), so `ict_primitives` carries **three level semantics under two timeframe
labels** — the canon-layer analogue of F-66. Deliberate per `ict_primitives.py:383` (the
`ADR-004:501` timeframe CHECK enum has no `'M'`), but it means `WHERE timeframe='W'` mixes weekly and monthly levels. **F-79.**

### Verdict

**The canon layer is canon.** On the four axes that convicted the legacy builder, the detector
conforms on all four, and on the polarity axis it is the exact inverse of the legacy defect. The
defects found here are **anchoring and bookkeeping defects in the writer**, not detection defects in
the detector — which is a materially different remediation. The corrective path is **finish
S31-C**: the detector and its parameter tables can stand.

---

## Q3 — Can it be re-run over the gap

### Arguments — `build_ict_primitives.py:2080-2099`

```
--symbol   default "NIFTY,SENSEX"
--mode     {backfill, live}   default backfill
--start    YYYY-MM-DD  (parsed .replace(tzinfo=UTC) → UTC midnight)   required in backfill
--end      YYYY-MM-DD  (UTC midnight, EXCLUSIVE)                      required in backfill
--tfs      default "W,D,H,M5"
--skip-outcomes
--dry-run
--log
--smoke
```

**There is no `--from-date`.** The pair is `--start` / `--end`, both mandatory in backfill mode
(`:2109-2114`). `--dry-run` exists and suppresses both write paths (`:1797-1799`, `:1936-1938`) —
note it is **opt-out**, i.e. a bare invocation writes, which is the inverted convention S72 recorded
across ~60 root scripts.

### Tables read

| table | site | role |
|---|---|---|
| `hist_spot_bars_1m` | `:260` | **backfill** bar source, `instrument_id`-keyed, era-normalised at `:222-234` |
| `market_spot_snapshots` | `:300` | **live** bar source — see the warning below |
| `ict_primitives` | `:1743`, `:1832` | natural-key pre-check, id resolution |
| `ict_primitive_outcomes` | `:1873` | existing-outcome pre-check |
| `hist_atm_option_bars_5m` | `:1219` | expiry calendar, vendor tier |
| `historical_option_chain_snapshots` | `:1352` | chain premium, post-2026-04-01 tier; distinct expiries via RPC `get_hocs_distinct_expiries` at `:1247` |
| `hist_option_bars_1m` | `:1561` | chain premium, pre-2026-04-01 tier |

**`--mode live` is not a gap-fill path.** It reads `market_spot_snapshots.spot` and constructs
degenerate bars with `open=high=low=close=spot` (`:314-317`). Every wick-dependent rule — the FVG
geometry, the sweep test, MFE/MAE — is meaningless on those. A gap re-run must use
`--mode backfill`, which the brief's premise (`hist_spot_bars_1m` current and complete) supports.

### Outcomes: same pass

Same pass, same process, unless `--skip-outcomes`. `run_pipeline_for_symbol` (`:1952-2015`) runs
detect → upsert primitives → prefetch ATM calendar → `compute_outcomes` → `upsert_outcomes` in one
sequence. There is **no separate outcomes script**; the six `audit_s3*_falsification*.py` files
(Q5) read outcomes back, they do not write them.

### Idempotency — yes for a clean-window re-run, with one real duplication risk

Both writers are **INSERT-only with a pre-check skip**, not upserts, and neither deletes:

- Primitives: `fetch_existing_natural_keys` (`:1735-1764`) loads the natural keys already present in
  `[start, end)`, and `upsert_primitives_and_events` (`:1783-1785`) skips any match, plus an
  in-batch `seen_in_batch` guard. Write is `.insert(batch)` (`:1804`).
- Outcomes: `upsert_outcomes` (`:1868-1885`) loads existing `primitive_id`s and skips them. Write is
  `.insert(batch)` (`:1942`).

So a re-run over **2026-05-23 → today does not duplicate** and does not touch the existing
19,432 rows. Two consequences follow, both important:

1. **Re-running never recomputes.** An existing outcomes row is skipped, not updated. This is
   TD-S35-NEW-4 exactly. If any fix from Q4 lands, the existing population must be `DELETE`d before
   recompute — the writer offers no path to correct a row in place.
2. **F-78 — the duplication risk is at the window boundary, not in the overlap.** The D and W
   aggregated bar takes its `open` and its `ts` from *the first 1m bar inside the fetched window*
   (`:415`, `:423`), and an OB's zone bounds are that bar's body. A `--start` that falls mid-week
   therefore yields a **different `source_bar_ts` and different zone bounds for the same real-world
   weekly primitive**, hence a different natural key (`:1687-1692`), hence a duplicate row that the
   pre-check cannot see. This is the same conflict-key shape as F-64. **Mitigation: start the window
   on an ISO-week Monday.** The detectors also need lookback — W needs ≥3 weekly bars for a
   displacement window and 8 weeks for the retest timeout (`:116-121`), and PDH/PDL need a prior
   period — so the window must begin well before the gap regardless. **2026-03-30 (a Monday) is the
   concrete recommendation**, giving ~8 weeks of context and landing on a week boundary.

### The option-premium gap 2026-06-04 → 2026-08-23 — what it does

**It does not skip, and it does not fail. It silently nulls, and it silently writes one wrong
number.** Three distinct behaviours, in order of how they fire:

1. **Wrong expiry, not `None` — F-73.** `_load_expiry_calendar` (`:1189-1265`) unions vendor
   expiries with `get_hocs_distinct_expiries(symbol)`. If HOCS holds no rows across the gap, it
   contributes no expiries in that range, and `_nearest_weekly_expiry` (`:1268-1295`) — a
   `bisect`-style *first expiry ≥ anchor date* — returns the first expiry **after** the gap. So a
   July anchor is assigned a late-August expiry. The consequence is not a skip: line `:1026` writes
   `dte_at_formation = (expiry - valid_from.date()).days` **before** the premium check at `:1031`,
   so the row is persisted with a plausible-looking DTE of ~50 on a weekly cycle. That is exactly
   the S68 "one column varies while its neighbours are frozen" tell, inverted.
2. **Anchor premium missing → every option column NULL.** `premium_t0 is None or == 0` → `return out`
   (`:1031-1032` formation, `:1111-1112` retest). Formation keeps only `dte_at_formation`; retest
   keeps nothing.
3. **A horizon premium missing → that one column NULL, row retained.** `continue` at `:1042-1043`
   and `:1123-1124`. So a row can carry `atm_pnl_5m_pct` and not `atm_pnl_60m_pct`.

There is **no forward tolerance** in the premium reader: `_chain_premium_at` (`:1403-1420`) is an
exact minute-floored dict lookup. A single missing 5-minute HOCS cycle nulls that horizon.

**F-72 — and the spot-anchored SL columns are collateral.** The entire ADR-012 block sits *after*
the `premium_t0` early return (`:1137-1181` vs `:1111-1112`). `sl_level` and `sl_buffer_pct` are pure
functions of `zone_low`/`zone_high` and a constant (`:1142`, `:1145`) and need no option data at all
— yet across the premium gap they will be **NULL**. A doctrine that ADR-012 defines as
*spot*-anchored is, in this implementation, unobtainable without the option chain.

**One forward-looking hazard for any re-run that crosses 2026-08-03 (ADR-022 / CAS).** Two hard-coded
close instants are now inside the auction window: `_eod_ts` returns **15:30 IST** for every spot EOD
column (`:537-541`), and the option EOD horizon reads **15:25 IST** (`:1129`, `:1491`). Continuous
F&O trading now ends 15:15, the index plateaus at its 15:14 value through ~15:28, and the settled
close lands in the 15:29 bar (S70). So `forward_eod_pct` / `retest_fwd_eod_pct` will read the
plateau, and `option_pnl_eod` — and therefore `pnl_with_sl_pct` in the no-trigger case (`:1178-1179`)
— will be priced at 15:25, mid-auction. **A re-run over 2026-08-03 → today produces EOD columns that
are wrong in a way nothing in the pipeline reports.** The D and W bar `close` inherits the same
exposure through `_rth_filter`'s 15:30 bound (`:336`).

---

## Q4 — The outcomes compute path

All of it is in `build_ict_primitives.py`. The concern in the brief is correct to raise: **21 of 21
positive is what this implementation predicts, for a reason that is visible in the code.**

### `respected` — F-71

```
657   # Respect: signed move after retest aligns with primitive direction
658   fwd30 = out.get("retest_fwd_30m_pct")
659   if fwd30 is not None:
660       out["respected"] = (
661           (fwd30 > 0 and primitive.direction == "BULL")
662           or (fwd30 < 0 and primitive.direction == "BEAR")
663       )
```

It is **the sign of the 30-minute spot return after the retest**. `ADR-004:540` defines it as
*"did price react at the zone (rejection candle within zone on first retest)"* — a candle-shape test
on the retest bar. No rejection-candle logic exists anywhere in either file. Three further
properties: it is **NULL for every level primitive** (`compute_retest_outcomes_level`, `:668-717`,
never sets it), **NULL for every event** (events take the formation path only, `:1663-1678`), and
**NULL whenever `retest_fwd_30m_pct` is missing** — so `respected = false` and `respected IS NULL`
mean different things and neither means "price did not react".

### `atm_pnl_30m_pct` / `atm_pnl_60m_pct` — point-in-time, held strike, formation-anchored

`compute_atm_pnl_and_dte` (`:980-1045`), the ENH-106 v7 architecture per ADR-011:

- **Entry basis** — `anchor_5m = _floor_5m(primitive.valid_from)` (`:1012`), i.e. the 5-minute
  boundary **at or before** `valid_from`; `premium_t0 = _chain_premium_at(…, anchor_5m)` (`:1029`).
- **Strike selection** — manual, from spot: `strike = round(spot / grid) * grid` with
  `grid = {NIFTY: 50, SENSEX: 100}` (`:1016`, `:129`). The vendor's pre-picked `atm_strike` is **not**
  used; `_atm_strike_for` (`:797`) is explicitly dead. **Held constant across all horizons.**
- **Leg** — `opt_type = "CE" if direction == "BULL" else "PE"` (`:1023`). For events this means a PE
  on every `SWEEP_HIGH` and `DISPLACEMENT_DOWN`.
- **Expiry** — `_nearest_weekly_expiry` over an empirical calendar (`:1019`), which correctly handles
  the 2025-09-01 NIFTY/SENSEX weekday swap and holiday-shifted weeks without a DOW rule.
- **Formula** — `(future_premium - premium_t0) / premium_t0 * 100` at `+5/+15/+30/+60` minutes
  (`:1038-1044`). **Point-in-time close-to-close. Not MFE-based** — MFE lives separately in
  `mfe_pct`/`time_to_mfe_min` (`:732-794`) and is **spot**, never premium.

`compute_retest_atm_pnl` (`:1070-1181`) is the same architecture anchored at
`_floor_5m(first_retest_ts)`, writing `option_pnl_5m/15m/30m/60m/eod`, and it is the cohort the
brief is asking about.

### `option_pnl_source` — F-70

`_source_tier` (`:1298-1304`) is a pure function of one timestamp:
`"vendor_hist_1m"` if `ts < 2026-04-01T00:00Z` else `"merdian_hist_5m"` — i.e. the vendor
`hist_option_bars_1m` chain (dense, full chain, `close`) versus MERDIAN-ingest
`historical_option_chain_snapshots` (~5-min point-in-time, **`ltp`**, ATM±N capture window per
TD-S35-NEW-1).

**But one column carries two different anchors' provenance.** `compute_outcomes` applies the
formation dict at `:1647` and the retest dict at `:1658`; both set `option_pnl_source` (`:1035`,
`:1115`), so **the retest value overwrites the formation value**. Therefore: for a `RETESTED` row the
tag describes the retest anchor and says nothing about the tier behind `atm_pnl_*`; for any other row
it describes the formation anchor. Where formation is pre-boundary and the retest post-boundary, the
`atm_pnl_*` columns are **actively mis-tagged**. A consumer cannot disambiguate without also reading
`retest_status`.

The `ltp` half of that distinction matters on its own: CLAUDE.md already records that *"`ltp` is the
last trade, not a price"* and that anything computing value from it inherits stale prints biased
toward the least liquid strikes. Every `merdian_hist_5m`-tagged P&L number is an `ltp`-to-`ltp` ratio.

### `sl_level` / `pnl_with_sl_pct` — spot-anchored per ADR-012, and correctly so

`:1137-1181`. `BULL → sl_level = zone_low × (1 − 0.005)`, trigger `close < sl_level`;
`BEAR → sl_level = zone_high × (1 + 0.005)`, trigger `close > sl_level` (`:1141-1146`). The walk is
over **5-minute aggregated spot bars** (`:1153`), from the bar after the retest through the 15:25 IST
EOD bucket (`:1158-1165`), first close-through wins. `sl_buffer_pct` is persisted per row (`:1148`).
That is ADR-012 §3 implemented exactly — **spot-anchored, 5m-close-through, not premium-based** —
and the doctrine was decided 2026-05-24 with the outcomes computed 2026-05-25, so the ordering holds.
`pnl_with_sl_pct` prices the exit from the chain at the trigger bar (`:1169-1173`), and degenerates
to `option_pnl_eod` when no trigger fires (`:1178-1179`). Two audit-honest details worth keeping:
when the SL fires but the exit cannot be priced, `sl_triggered_ts` is written while `sl_exit_prem`
and `pnl_with_sl_pct` stay NULL (`:1174-1175`) — deliberate, and commented as such; and level
primitives are skipped by design (`:1139`), so `sl_*` is NULL on every PDH/PDL/PWH/PWL/PMH/PML.

### Why 21 of 21 is what this code predicts — F-68

**Correction — 2026-09-09, operator-measured. Read this before the section it heads.**

The column carrying the 21-of-21 is `atm_pnl_60m_pct`. It is written by
`compute_atm_pnl_and_dte`, which anchors at `_floor_5m(primitive.valid_from)`
(`build_ict_primitives.py:1012`) and never reads `first_retest_ts`: it is
**formation-anchored**. The retest-anchored columns are `option_pnl_*`, written by a
different function — `compute_retest_atm_pnl`, anchored at `_floor_5m(first_retest_ts)`
(`:1096`). Two code paths, two column families, and the 21-of-21 belongs to the first.

**F-68 alone accounts for the 21-of-21. F-69 was never needed to explain it.** The F-69
half of this section reasons from the retest walk to that P&L; that inference is wrong and
is withdrawn. The F-69 verdict cell in the findings table carried the same error and is
corrected there. What survives is F-69 as a statement about the *retest* cohort — a
different cohort, measured on its own terms under **Closed by operator query** below, where
it shows **10 positive / 8 negative** at H and no edge.

The F-68 half that follows is unaffected, and is now the whole subject of this section.

**F-68 — `valid_from` is the displacement bar's open, and the retest walk starts there.**

`detect_order_blocks` sets `valid_from = disp.event_ts` (`ict_primitives.py:354`), and
`disp.event_ts` is the **aggregated bar's bucket-start timestamp**, because `aggregate` stamps a D
bar with `day_bars[0].ts` (`build_ict_primitives.py:415`) — the day's first 1m bar, ~09:15 IST — and
an H bar with the UTC hour start (`:357`). `valid_from` is never adjusted afterwards: it is assigned
once in the detector and consumed verbatim by every outcome function (`:562`, `:601`, `:612`,
`:682`, `:688`, `:747`, `:1012`, `:1026`, `:1496`, `:1703`).

So for a **D** order block, `valid_from` is **09:15 IST on the displacement day** — while
`ADR-004:87` says the OB is confirmed *"once the displacement bar closes"*, i.e. 15:30 that day.
**Six hours fifteen minutes of lookahead.** For **W**, `valid_from` is Monday 09:15 and confirmation
is Friday 15:30 — **a full week**. For **H**, up to 59 minutes. FVGs carry the same defect and more
plainly: `valid_from = nxt.ts` (`ict_primitives.py:192`, `:214`) is bar `i+1`'s *open*, while the
zone's own boundary is `nxt.low` — a value that does not exist until that bar closes.

**F-69 — the consequence for the retest cohort, which is a different cohort.**

`compute_retest_outcomes_zone` begins its walk at `the first 1m bar at or after valid_from`
(`:609-614`), requires one bar fully outside the zone (`:628`), and then takes **the first bar that
re-enters** as `first_retest_ts` (`:632`). Since the walk opens at the displacement bar's *start*,
the first re-entry can — and for the earliest qualifying bar, preferentially will — fall **inside the
displacement bar itself**, before it closed and before the primitive existed.

Concretely, for a D `BULL_OB`: the zone is the prior bearish day's body; the walk opens at 09:15 on a
day that will close ≥ +1.0% with an FVG; price dips into the zone during that morning; that dip is
recorded as the retest; `compute_retest_atm_pnl` buys an ATM **CE** there and marks it out at
+30/+60 minutes and at EOD. **That is an ATM call bought at an intraday low of a day already known to
close as a large up-day.** A cohort selected that way does not need an edge to print 21 of 21
positive with several above +100%; at the low DTE that `_nearest_weekly_expiry` selects, ATM gamma
supplies the magnitudes.

The same reading explains the *shape* of the brief's observation — not merely positive, but
**uniformly** positive and large — which unconditional directional edge does not usually produce.

**This is not settled by code reading, and must not be reported as if it were.** What settles it is a
single query, and it needs no premium data:

```sql
-- Does the retest anchor precede the bar that confirmed the primitive?
SELECT p.symbol, p.timeframe, p.primitive_type,
       p.valid_from, o.first_retest_ts,
       o.first_retest_ts < (date_trunc('day', p.valid_from AT TIME ZONE 'Asia/Kolkata')
                            + interval '15 hours 30 minutes') AS retest_before_D_confirm
FROM ict_primitive_outcomes o
JOIN ict_primitives p ON p.id = o.primitive_id
WHERE p.primitive_type IN ('BULL_OB','BEAR_OB')
  AND p.timeframe IN ('H','D')
  AND o.retest_status = 'RETESTED';
```

**This query no longer tests what it was written to test**, and the two lines that used to
follow it read as live instruction for a question it cannot reach. It was written to ask whether
the 21-of-21 cohort was anchored before confirmation. That cohort is `atm_pnl_60m_pct`,
formation-anchored, and never passes through `first_retest_ts` at all.

What the query does measure is the contamination rate of the **retest** cohort — for `D`, rows
whose `first_retest_ts` precedes 15:30 IST of `valid_from`'s date; for `H`, `first_retest_ts <
valid_from + interval '1 hour'`. On that reading it was worth running, and it has been run: the
OB results are at **F-69** under *Closed by operator query* below, and the FVG contamination
figures recorded there extend the same test to the zone cohort.

A second, independent check on cohort composition — the survivorship channel:

```sql
SELECT p.timeframe, o.option_pnl_source,
       count(*)                          AS retested,
       count(o.option_pnl_30m)           AS with_30m,
       count(o.option_pnl_eod)           AS with_eod
FROM ict_primitive_outcomes o
JOIN ict_primitives p ON p.id = o.primitive_id
WHERE p.primitive_type IN ('BULL_OB','BEAR_OB') AND p.timeframe IN ('H','D')
  AND o.retest_status = 'RETESTED'
GROUP BY 1, 2;
```

Because a missing premium nulls the column rather than the row (`:1123-1124`), any reported win rate
is conditioned on premium availability. On the `merdian_hist_5m` tier this is **not random**:
TD-S35-NEW-1 records that HOCS captures ATM±N strikes per cycle, so a **held** strike drops out of
capture precisely when spot travels far from it — and for a losing directional trade the held leg is
the one going far OTM. On the `vendor_hist_1m` tier the chain is dense and the mechanism should not
apply, which is why the split by `option_pnl_source` is the discriminating cut.

---

## Q5 — Reader sweep, redone

### Exclusion set

**Part 1:** `*_PRE_*`, `*_PATCHED*`, `fix_*`, `patch_*`, `diag*`, `experiment_*` — *"unless
reachable from a live entrypoint"*; file types `*.py`, `*.sql`, `*.sh`; scope `~/meridian-cc`.

**Part 2: none.** Every file of every type under `~/meridian-cc` except `.git/`, plus every file of
every type under `~/meridian-connect` except `.git/` and its `.env` (excluded by construction — the
directories and root files were named individually rather than globbed, so no command line contained
that filename).

### Result — `~/meridian-cc`

`/usr/bin/grep -rIl "ict_primitive" . --exclude-dir=.git` → **50 files**. Removing the 19 builder
variants, the 2 detector-library copies, and the 15 docs/registers leaves **14** non-variant code
files. Of those, the roles are:

| file | role | live? |
|---|---|---|
| `audit_s32_enh100_falsification.py:139-150`, `:405` | **reader** — `ict_primitive_outcomes` with `select("*,ict_primitives!inner(…)")` | no — not on the crontab, no systemd unit |
| `audit_s32_enh100_falsification_v2.py` … `_v5.py` (4 files) | **readers**, same shape (`_v5.py:319-328`, `:357`) | no |
| `audit_s33_enh103_falsification.py:99-112`, `:216` | **reader**, same shape | no |
| `fill_2026_04_16_breeze.py:87`, `:182` | comment only — *"same canonical strike grids as build_ict_primitives.py"* | n/a |
| `MERDIAN_ICT_Primitives_canonical{,_v2,_v4}.pine:5` | comment only — *"Python parity counterpart: core/ict_primitives.py"* | n/a |

**Part 1's claim is withdrawn.** It stated: *"No reader of `ict_primitives` was found in the
non-variant tree by the search above."* Six readers exist. **The stated method was not the problem** —
replaying Part 1's own documented command finds all six:

```
$ /usr/bin/grep -rn --include='*.py' --include='*.sql' --include='*.sh' \
    -E "ict_primitives|ict_primitive_outcomes" . --exclude-dir=.git | grep -v '^\./\(build_\)\?ict_primitives'
  7 ./audit_s32_enh100_falsification.py
  5 ./audit_s33_enh103_falsification.py
  5 ./audit_s32_enh100_falsification_v5.py   (+ _v4, _v3, _v2)
  2 ./fill_2026_04_16_breeze.py
```

None of these matches any excluded pattern. **The omission was in execution, not in the method** —
recorded as such rather than attributed to the exclusion set. The corrected statement: the table is
written by an unscheduled writer and read by **six unscheduled audit scripts**; it has no live
consumer.

The three `.pine` files also correct a Part-1-adjacent assumption: they name their Python counterpart
as `core/ict_primitives.py`, a path that does not exist in either repository (Q1).

### Result — `~/meridian-connect`, all of it

Repository at `/home/ssm-user/meridian-connect`, 90 tracked files (70 `.tsx`, 6 `.ts`, 4 `.json`,
plus config), with an untracked built `dist/` (676 K). Searched `src/`, `dist/`, `.lovable/`,
`index.html`, `package.json`, `package-lock.json`, `bun.lock`, `vite.config.ts`, `components.json`,
`tsconfig.json`, `eslint.config.js`, `bunfig.toml` — all extensions, source and built bundle:

**`ict_primitive` → zero hits.** Not in source, not in the minified bundle.

This closes row 12 of Part 1's "could not settle" table, and it closes it in the direction Part 1
suspected but could not assert. **The frontend does read the legacy tables**, which is the useful
contrast:

| site | table |
|---|---|
| `src/lib/queries.ts:259` | `.from("ict_zones")` |
| `src/marketview/sections.tsx:399` | `z.ict_tier ?? z.tier` |
| `src/pages/Health.tsx:35`, `:42` | writer-freshness rows for `detect_ict_patterns_runner.py`, `build_ict_htf_zones.py` |
| `src/pages/Settings.tsx:427` | *"rebuild ICT zones … refreshes ict_zones table"* |
| `dist/assets/index-dwQ-izwF.js` | the same strings, compiled |

So the operator console is wired to the **legacy** zone tables and to the health of the **legacy**
writers. The canon table has no consumer in any repository, on any surface — which is the concrete
content of "S31-C was never finished".

---

## Q6 — The second ICT task

**`merdian_eod_ict.bat` is not in this repository, and no copy of it exists here.** Searched:
`find -iname "*eod_ict*" -o -iname "*ict_eod*"` → **empty**. The repository contains 31 `.bat`/`.ps1`
files; none is it. `grep -rIn "merdian_eod_ict"` matches **only prose**, in two session notes.

Nothing was inferred from the filename. What the repository *does* contain is two independent prose
records of its contents, and both of its plausible callees:

- **`docs/session_notes/CURRENT.md:125`** — *"The migration replaced `merdian_eod_ict.bat` (**3
  lines: NIFTY, SENSEX, Pine**) with **two** crontab lines … the dropped third line went
  unnoticed."* The consequence recorded there is concrete and dated: the EC2 `.pine` was stamped
  2026-08-18 with 104 zones and PIN 24350–24600 from six-day-old gamma positioning, against a Local
  regeneration at 2026-08-24 with 106 zones.
- **`docs/session_notes/S69_incident_carryforward.md:102`** — the task is *"`MERDIAN_ICT_EOD` (M5
  detector), **15:35 IST**, Local Task Scheduler"*, firing inside the 15:15–15:40 CAS window.
  **`:112`** names the callee: *"runner `detect_ict_patterns_runner.py` present, last modified
  2026-05-17"*, `State: Ready`, `LastTaskResult: 0`, **writing nothing** since 2026-06-02.
  **`:150`** records the `.bat` itself as *"untracked"* — which is why it is absent here.

Both named callees exist in this repository and were read:

- **`detect_ict_patterns_runner.py`** — the M5 detector. Per Part 1 it writes `ict_zones` at `:347`,
  `:370`, `:391`, reads `ict_htf_zones` at `:133`/`:262`, and writes 1H zones through the
  `upsert_zones` import at `:56`/`:580`. On **this** host it is scheduled (crontab lines 32/33, per
  Part 1); the Windows 15:35 task is a second, independent invocation of the same script.
- **`generate_pine_overlay.py`** — reads `ict_zones` (`:152`, `:180`) and `ict_htf_zones` (`:552`)
  and emits the overlay.

**What the `.bat` does, stated at the strength the evidence supports:** two register entries written
in different sessions independently describe a three-line file invoking the M5 detector for NIFTY,
then for SENSEX, then the Pine generator. Per this audit's own standing rule, **a register entry is
evidence of intent, never of behaviour** — so the argv, the Python interpreter used, any redirection,
and whether the Pine step passes arguments are all **unestablished**.

**What would settle it:** the file itself from `C:\GammaEnginePython\merdian_eod_ict.bat`, or a
`schtasks /query /tn "\MERDIAN_ICT_EOD" /xml` export from the Windows host — the latter also settling
the trigger time against the CAS window.

**One precision point that the two tasks make easy to conflate.** `run_ict_htf_zones_daily.py:66-68`
— the callee of the *other* ICT task, `MERDIAN_ICT_HTF_Zones_0845` — is **also** three steps ending
in Pine:

```
66    rc_wd   = run_step("WD",   ["build_ict_htf_zones.py", "--timeframe", "both"])
67    rc_h    = run_step("H",    ["build_ict_htf_zones.py", "--timeframe", "H"])
68    rc_pine = run_step("PINE", ["generate_pine_overlay.py"])
```

So `CURRENT.md:125`'s *"the Pine generator has had no scheduled invoker since S70"* is **EC2-scoped**.
On Windows the 08:45 task still chains it at `:68`. The two three-step jobs are distinct, both end in
Pine, and only the EOD one lost its Pine step in the crontab migration.

---

## Closed by operator query — 2026-09-09

Two Part 2 questions were settled by queries the operator ran against the live database. This
section is the evidence; the findings table below carries the resulting verdicts. **No database
access was available to this audit** — the results below are transcribed from the operator, and are
recorded at the strength that transcription supports.

### F-69 — retest anchored before confirmation · **CONFIRMED at H**

Both symbols, all OB rows carrying a `first_retest_ts`. H test: `first_retest_ts < valid_from +
1 hour`. D test: `first_retest_ts < 15:30 IST of valid_from`'s date. These are the two tests the
Q4 SQL specifies.

| symbol | tf | type | retested | anchored before confirmation | share |
|---|---|---|---|---|---|
| NIFTY | H | BULL_OB | 9 | 5 | 56% |
| SENSEX | H | BULL_OB | 8 | 5 | 63% |
| NIFTY | H | BEAR_OB | 4 | 2 | 50% |
| SENSEX | H | BEAR_OB | 6 | 3 | 50% |
| **H subtotal** | | | **27** | **15** | **56%** |
| NIFTY | D | BEAR_OB | 1 | 1 | — |
| SENSEX | D | BULL_OB | 4 | 1 | — |
| NIFTY | D | BULL_OB | 2 | 0 | — |
| SENSEX | D | BEAR_OB | 1 | 0 | — |
| **D subtotal** | | | **8** | **2** | **25%** |
| **total** | | | **35** | **17** | **49%** |

**The mechanism fires.** F-68's anchoring defect is not theoretical: 17 retests are demonstrably
recorded at an instant before the bar that confirmed the primitive existed. That is the claim F-69
made and could not settle by code reading, and it is now settled at H.

**Four qualifications, each of which the numbers force and none of which the verdict should absorb:**

1. **The magnitude ordering is the inverse of the prediction.** F-69 reasoned from window width —
   D carries ≈6h15m of lookahead, H at most 59 minutes — and therefore predicted the defect would
   bite hardest at D. It bites at **H (56%)** and barely at **D (25%)**. The code reading got the
   mechanism right and the ordering backwards. The explanation is not established here and is not
   guessed at; what is recorded is that window width alone does not predict the rate.
2. **D is below any tier that supports a contrast.** N=8 retested rows across both symbols and both
   directions. ADR-009's own graduated-strictness scale puts N<30 in the *low-N calibration-only*
   tier, and every D cell here is N≤4. "Materially weaker at D" is a fair description of the
   observation and is **not** a finding — 2 of 8 and 15 of 27 are not separable at these counts.
3. **Withdrawn — the two counts are from different cohorts.** This point read *"17 < 21, so F-69
   cannot be the whole explanation of the 21-of-21 cohort"*, and the Q4 SQL framed its test the
   same way. The comparison is void: the 21 are `atm_pnl_60m_pct` rows (formation-anchored,
   `compute_atm_pnl_and_dte`, `build_ict_primitives.py:1012`); the 17 are retests feeding
   `option_pnl_*` (`compute_retest_atm_pnl`, `:1096`). F-68 alone accounts for the 21-of-21, so
   there is no residual of 4 rows owed an account, and the survivorship channel is not implicated
   by this arithmetic. It stays open on its own terms.
4. **The retest cohort has now been measured, and it shows no edge.** Operator query, 2026-09-09,
   dense vendor tier: the retest-anchored cohort at H is **10 positive / 8 negative**. Separately,
   FVG contamination — `first_retest_ts` earlier than the confirming bar's close — measured across
   both symbols and every cell: **M5 827 of 1387 (63%), H 251 of 307 (81%), D 70 of 91 (80%)**. The
   M5→H→D hit-rate gradient reported in the session brief (55 / 66 / 80%) tracks that contamination
   rate, which makes the gradient an artefact of F-68 rather than an edge. These figures are
   operator-transcribed on the same terms as the table above, and are recorded at that strength.

**One arithmetic note on the transmitted summary.** The operator's covering line read *"10 of 17
hourly, 2 of 8 daily"*. The daily figure matches the per-cell rows (8 retested, 2 before). The
hourly figure does not: 10 of 17 is the **BULL_OB half alone** (9+8 retested, 5+5 before); the H
BEAR_OB half adds 10 retested and 5 before, giving **15 of 27** across all H. The per-cell numbers
are taken as primary and the totals recomputed from them. Recorded rather than silently corrected,
because the two framings differ by 5 rows on the finding's headline count.

### F-73 — expiry fails forward across the chain gap · **CONFIRMED**

Three facts, all operator-verified:

- **`historical_option_chain_snapshots` ends at 2026-06-03** — NIFTY's last row 06-02, SENSEX's
  06-03 — with **zero rows 2026-06-04 → 2026-08-23**. This is the condition F-73 requires: the
  union calendar in `_load_expiry_calendar` (`:1189-1265`) contributes no HOCS expiry inside the
  gap, so `_nearest_weekly_expiry` (`:1268-1295`) returns the first expiry *after* it and `:1026`
  persists the resulting DTE before the premium guard at `:1031` can null the row.
- **The bare `option_chain_snapshots` table holds nothing before 2026-08-24.** The 14-day thinning
  preserved only `hour=10 minute=0` UTC; the derivatives-window cron extension landed 2026-08-24
  (`gex_strike_snapshots` last cycle 09:55 on 08-21, 10:10 on 08-24), so before that date **no
  preservable row existed and each aged day was deleted whole**. The live table is therefore not a
  recovery source for the gap either — the data is gone, not merely unarchived.
- **`pg_cron` jobid 19 was disabled by the operator on 2026-09-09** (`active=false`, schedule and
  command left intact), stopping further loss from 08-24 forward.

**What this does not establish.** That the thinning job is the *cause* of the HOCS gap. HOCS is
populated by `archive_option_chain_history.py`, a separate `run_id`-scoped bridge that reads the
bare table at `:81` and inserts into HOCS at `:144`, invoked per cycle by
`run_option_snapshot_intraday_runner.py:437-440`. HOCS
stopping on 06-03 and the live table being thinned are two facts about two different tables written
by two different paths; the first is an archival-bridge outage, and its cause is not established
here.

---

## New findings — Part 2 (F-68 …)

| # | finding | severity note | evidence |
|---|---|---|---|
| **F-68** | **`valid_from` is the confirming bar's OPEN, not its close** — OB `valid_from = disp.event_ts`, FVG `valid_from = nxt.ts`, both bucket-start timestamps. Lookahead: **D ≈ 6h15m, W ≈ 5 days, H ≤ 59 min**. On FVGs the zone boundary (`nxt.low`) is literally a value from after the anchor | the sharpest finding of Part 2 — every outcome column is anchored on it, and it **alone** accounts for the 21-of-21 `atm_pnl_60m_pct` cohort, which is formation-anchored (`compute_atm_pnl_and_dte`, `:1012`) and does not touch F-69's retest path | `ict_primitives.py:354`, `:192`, `:214`; `build_ict_primitives.py:415`, `:357`, `:423` vs `ADR-004:87` |
| **F-69** | **CONFIRMED at H — the retest walk opens at that same pre-confirmation instant**, so `first_retest_ts` falls inside the unconfirmed displacement bar. Operator-run query, both symbols, all OB rows carrying a `first_retest_ts`: **17 of 35 retests are anchored before the bar that confirmed the primitive** — **15 of 27 at H** (56%), **2 of 8 at D** (25%). The mechanism fires. Qualification carried below: the magnitude ordering is the **inverse** of what the code predicted. **The 21-of-21 comparison originally carried here is withdrawn** — that cohort is `atm_pnl_60m_pct`, formation-anchored, and belongs to F-68, not to this finding | **CONFIRMED as a mechanism at H. Not an explanation of the 21-of-21 P&L** — that cohort is formation-anchored and belongs to F-68. The retest cohort this finding does govern measures **10 positive / 8 negative** at H on the dense vendor tier — no edge; FVG contamination measures **M5 63% / H 81% / D 80%** (operator, 2026-09-09). See the corrected closure note under Q4 | `build_ict_primitives.py:609-614`, `:628`, `:632`; `:1096`, `:1109`; operator query 2026-09-09 |
| **F-70** | **`option_pnl_source` carries two anchors' provenance in one column** — formation writes it, retest overwrites it. Where formation is pre-2026-04-01 and retest post-, the `atm_pnl_*` columns are actively mis-tagged | consumer cannot disambiguate without `retest_status` | `:1035`, `:1115`, `:1647` then `:1658`; `:1298-1304` |
| **F-71** | **`respected` is a 30-minute signed-return test**, not the ADR's rejection-candle test; NULL for every level primitive and every event; `false` and `NULL` are different and neither means "no reaction" | a boolean whose name does not describe what it measures | `:657-663` vs `ADR-004:540`; `:668-717`; `:1663-1678` |
| **F-72** | **ADR-012 SL columns are hostage to the option chain.** The whole SL block sits after the `premium_t0 is None → return` guard, so `sl_level`/`sl_buffer_pct` — pure functions of the zone and a constant — are NULL whenever premium is missing | a *spot*-anchored doctrine made unobtainable without option data | `:1111-1112` vs `:1137-1148` |
| **F-73** | **CONFIRMED — `_nearest_weekly_expiry` fails forward across a chain-data gap**, returning the first expiry *after* it rather than None; `dte_at_formation` is written at `:1026` **before** the premium guard, so the row persists with a plausible-looking wrong DTE. The gap is real and measured: `historical_option_chain_snapshots` **ends at 2026-06-03** (NIFTY 06-02, SENSEX 06-03) with **zero rows 2026-06-04 → 2026-08-23**. Every post-06-03 anchor therefore draws its expiry from the first vendor/HOCS expiry after the gap | silent wrong value, not a null | `:1268-1295`, `:1026`, `:1189-1265`; operator query 2026-09-09 |
| **F-74** | **Swept levels never transition to `SWEPT`**, contrary to `ADR-004:368`; every level emitted in the window stays a candidate for every later M5 bar. Bounded by the close-back-inside test, but a level swept months earlier can be swept again and the reported level is the deepest, not the freshest | bounded; affects `swept_level_*` metadata fidelity | `ict_primitives.py:489-492`, `:390-391` vs `ADR-004:368` |
| **F-75** | **M5 and H aggregation apply no RTH filter; D and W do.** M5/H OB/FVG/sweep detection ingests whatever out-of-session rows `hist_spot_bars_1m` carries | conditional on the source table; check named below | `build_ict_primitives.py:396-408` vs `:409-424`, `:329-338` |
| **F-76** | **Register decay, measurable to the line.** `merdian_reference.json` pins `build_ict_primitives.py` at **1,140 lines** — exactly `_PRE_S32.py` — and `ict_primitives.py` at **613 lines** — exactly `_PRE_S31B_SWEEP_DEDUP.py`, the pre-patch state, while the *same entry's prose* says the dedup was applied. Live: **2,152** and **639** | the register describes the S31-B system; the code is four generations past it | `merdian_reference.json` files entries vs `wc -l` |
| **F-77** | `run_pipeline_for_symbol` returns the **skip count** under the key `"events"`, and `main()` accumulates only `primitives`/`outcomes` — so the run summary silently omits events and never reports skips | low; cosmetic but it is the only console evidence a run leaves | `:2011-2015`, `:2133`, `:2142-2147` |
| **F-78** | **W/D natural keys are unstable at window boundaries.** The aggregated bar's `open` and `ts` come from the first 1m bar *inside the fetched window*, and an OB's zone is that bar's body — so a `--start` mid-week yields a different natural key for the same weekly primitive and the pre-check cannot see the duplicate. Same conflict-key shape as F-64 | governs how any gap re-run must be windowed | `:415`, `:423`, `:1687-1692` |
| **F-79** | **PMH/PML stored as `timeframe='W'`** with the real period only in `metadata.period` — three level semantics under two labels, so `WHERE timeframe='W'` mixes weekly and monthly. Deliberate per `ict_primitives.py:383` (the `ADR-004:501` timeframe CHECK enum has no `'M'`) | consumer-facing; canon-layer analogue of F-66 | `ict_primitives.py:415-416`, `:440`; `build_ict_primitives.py:1985` |
| **F-80** | **The first H bucket of each session is a 15-minute bar.** `_bucket_to_h` floors to the UTC hour; IST 09:15 = 03:45 UTC, so bucket 03:00 holds 09:15–09:29 only. `DISPLACEMENT_MIN_PCT['H'] = 0.4%` and `OB_MIN_BODY_PCT['H'] = 0.2%` are calibrated for 60-minute bars and applied to it | structurally suppresses first-hour H displacements; ADR-004 Amendment B's Pine-parity claim unverified here | `build_ict_primitives.py:353-359`, `:406-408`; `ict_primitives.py:44`, `:43` |
| **F-81** | **The Pine comment asserts a parity that was never true.** `MERDIAN_ICT_Primitives_canonical_v4.pine:137-138` reads *"Pine fires detection one bar AFTER formation (when next bar closes), which matches the Python convention of `valid_from = bar[i+1].ts`."* The first clause is **correct**: every detector is fetched under `lookahead=barmerge.lookahead_off` (`:227-244`), and `detect_bull_fvg` reads `nxtLow = low` from the *current* bar (`:147`), so it cannot evaluate until that bar closes. The second clause is **false** — `bar[i+1].ts` in Python is that bar's **open**. Pine's own `formed_time` (`:150`, `time[1]`) is the mid bar and is passed as `box.new(left=…)` (`:275`), a choice about where to draw back to, not a claim about consumability. **The overlay and the writer differ by one full bar, and the comment records them as agreeing** | **this is how F-68 survived a human checking the chart.** The chart was right; the writer was wrong; the only artefact that compared them said they matched. Same comment verbatim at `_canonical.pine:132-133` and `_v2.pine:132-133`, so the assertion has been carried unexamined across three generations | `MERDIAN_ICT_Primitives_canonical_v4.pine:137-138`, `:143-150`, `:227-244`, `:275`; `MERDIAN_ICT_Primitives_canonical.pine:132-133`; `MERDIAN_ICT_Primitives_canonical_v2.pine:132-133` |
| **F-82** | **This document's own `ADR-004:NN` citations are unreliable — 9 of 18 distinct line references were wrong.** Audited exhaustively 2026-09-10, after the F-68 work forced two of them open and a post-condition written for that repair surfaced a third. Four error kinds: **off-by-one** (`:59`→`:60`, `:86`→`:87`, `:541`→`:540`); **pointing at a blank line** (`:130`→`:128`, `:145`→`:140`); **pointing at the wrong element of the right section** (`:87`→`:91`, `:113`→`:106-111`, `:133`→`:132`, `:578`→`:576`, `:369`→`:368`, `:136-138`→`:135-137`); and **wrong file** — `ADR-004:383` is `ict_primitives.py:383`, and the ADR's `timeframe` CHECK is `ADR-004:501`. ADR-004 has one commit (`37f3259`) and has never been amended, so none of it is source drift. **All 9 are repaired** in this pass | **the quoted text was correct every time; only the pointers were wrong**, which is exactly why it survived — quote-checking finds the text, and following the number lands on something plausible nearby. The class matters beyond this document: a line citation into a file the citing document does not control is unverifiable at read time and silently rots on any edit. **F-81 is the same failure one level up** — a comment asserting a correspondence that was never checked | exhaustive `ADR-004:(\d+)` sweep of this document against `ADR-004-ict-primitive-canon.md`, 2026-09-10; `git log` on the ADR |

---

## Withdrawn from Part 1

| claim | as written | corrected |
|---|---|---|
| readers of `ict_primitives` | *"No reader of `ict_primitives` was found in the non-variant tree by the search above"* (`:474-478`) | **Six readers** — `audit_s32_enh100_falsification{,_v2,_v3,_v4,_v5}.py` and `audit_s33_enh103_falsification.py`. Replaying Part 1's own documented command finds all six; **the exclusion set does not explain the omission.** Execution error, not method error |

Part 1's framing of that claim as *"an absence over the object searched, not a claim that no consumer
exists"* was the right hedge and is what makes the correction cheap — but the object searched did
contain them.

---

## What Part 2 could not settle, and what would settle it

| # | question | blocked by | what would settle it |
|---|---|---|---|
| 1 | Did the operator run *this* file, or a since-diverged Windows copy? (Q1) | off-host | md5 of `C:\GammaEnginePython\build_ict_primitives.py` vs `102ad3b3565b4effe229b90c2a59ef7e` |
| 2 | Is the option-P&L cohort survivorship-filtered by tier? (Q4) | no DB access | the `count(*)` vs `count(option_pnl_30m)` split by `option_pnl_source` in Q4 |
| 3 | Does `hist_spot_bars_1m` carry out-of-session rows, making **F-75** material? | no DB access | `SELECT count(*) FROM hist_spot_bars_1m WHERE (bar_ts AT TIME ZONE 'Asia/Kolkata')::time NOT BETWEEN '09:15' AND '15:30'` — era-aware per Rule 20 |
| 4 | What does `merdian_eod_ict.bat` actually invoke? (Q6) | file is untracked and Windows-side | the file, or `schtasks /query /tn "\MERDIAN_ICT_EOD" /xml` |
| 5 | Is the Pine parity claim of ADR-004 Amendment B true given **F-80**? | requires reading the three `.pine` files against TradingView session-alignment behaviour | a bar-boundary comparison on one session |
| 6 | Does `ict_primitives` hold duplicate W/D rows from an earlier boundary-straddling run? (**F-78**) | no DB access | `SELECT symbol, timeframe, primitive_type, date_trunc('week', source_bar_ts), count(*) FROM ict_primitives WHERE timeframe IN ('W','D') GROUP BY 1,2,3,4 HAVING count(*) > 1` |

**Two rows removed, both answered by operator-run queries on 2026-09-09** — the former row 2
(**F-69**, retest anchoring) and the former row 4 (**F-73**, the HOCS gap). Their closure evidence is
recorded in the **Closed by operator query** section above; the surviving rows are renumbered 1-6
and their content is unchanged.

Rows 8, 10 and 11 of Part 1's table are unchanged. **Row 12 is now closed**: nothing in
`~/meridian-connect` reads `ict_primitives`, on any surface, in source or in the built bundle.

---

## Operator decisions — 2026-09-09

Recorded as **operator decisions**, not audit findings. Both were taken on the Part 2 evidence
above; both bind the remediation. The audit's role here is to record them and their stated
grounds, not to re-derive them.

### D1 · `valid_from` is the confirming bar's CLOSE — `ADR-004:87` governs, `:60` superseded

The ADR contradicts itself. `:87`, step 6 of the §5.1 detection algorithm, is normative:
*"The candidate becomes a confirmed OB once the displacement bar closes and the FVG is verified."*
`:60`, in the §4 field list, is loose prose: *"`valid_from` — when the primitive becomes consumable
(typically `source_bar_ts` + 1 TF)"*.

**Decision: `:87` wins. `valid_from` is the confirming bar's close.** `:60` is superseded as
loose prose, on the ground that it does not survive the OB case at all — `source_bar_ts` is the *OB
candle*, and the confirming displacement can be up to `DISPLACEMENT_WINDOW_BARS` later: 3 bars at
W/D/H, 6 at M5 (`ict_primitives.py:45`, `ADR-004:83`). "`source_bar_ts` + 1 TF" names the wrong bar
whenever the OB is not immediately adjacent to its impulse, and the hedge "typically" concedes it.

Only the writer reads `:60`'s way. `ADR-004:71` (Amendment A) defines formation-anchored
outcomes as *"forward returns from the bar that confirmed the primitive"*, and a forward return
from a bar starts at its close; `ADR-004:129` confirms an FVG on a quantity computed from bar
`i+1`'s low/high, which do not exist until it closes. Those are ADR text and they bind.

The Pine files also emit at the confirming bar's close, and that is **corroboration, not
authority** — it is code being used to read the ADR, Amendment B's parity claim is itself
unverified (**F-80**), and **F-81** records that the Pine comment asserting parity with the
writer asserted something that was never true. The schema settles nothing either way
(`valid_from TIMESTAMPTZ NOT NULL`, no CHECK, `ADR-004:506`), which is why 6h15m of lookahead
persisted without complaint.

**Consequence for ADR-004 — discharged.** `ADR-004` **Amendment C** (2026-09-10, §15) carries
this decision into the ADR itself. `:60` is superseded in place: rewritten to read as superseded
from its first word, with its original wording retained after it for the record and explicitly
demoted from being a statement of the rule. Amendment C was **appended** as §15 rather than
inserted inline, because an inline insertion would have shifted every ADR line number below it
and silently broken the 21 line citations this document makes into that file — the failure class
filed here as **F-82**. Amendment C records that no code implements the new reading and that the
existing 19,432-row cohort was built under the superseded one.

### D2 · Remediation is Option 2 — carry `ts_close` on `Bar`

**Decision: add `ts_close: Optional[datetime] = None` to `Bar` (`ict_primitives.py:62-70`), set it
in `_reduce_ohlc` (`build_ict_primitives.py:380-389`) from the last bar of the bucket, and consume
it at the three detector assignment sites (`ict_primitives.py:192`, `:214`, `:354`).**

The value already exists and is already discarded. `_reduce_ohlc` sorts the bucket and reads
`bucket_bars_sorted[-1].close` for the price, then returns a `Bar` stamped with `bucket_ts` — the
bucket *start*. The last bar's timestamp is computed on the line above and thrown away, because
`Bar` has no field to hold it.

**Option 1 — a per-TF constant offset — was rejected as silently wrong at D and W.** It is exact at
M5 and H, where the bucket key is clock-floored and the close is `+5min` / `+60min`. At D and W the
bucket key is `day_bars[0].ts` / `wk_bars[0].ts` (`:415`, `:423`) and session length is not
constant: a fixed 6h15m / 5-day offset assumes every session and every week runs full. The operator
ground for rejection was the shape rather than the case — *a constant assuming full-length sessions,
in a week that found CAS re-timing (ADR-022) and 08:40 truncations*. This system has produced that
failure repeatedly; **Guard 3 built from two samples** and **`OB_MIN_MOVE_PCT` measured on
single-bar bodies against a five-bar definition** are the same error, and both are already settled
entries in CLAUDE.md.

**Option 3 — a second `confirmed_at` column — was rejected** for storing two temporal semantics on
one table permanently, in order to preserve a cohort that F-68 has already invalidated. ADR-015's
governance is the precedent: derivations belong in the read layer, and a column kept only for
backward comparison with measurements now known to be contaminated is not a derivation worth
storing.

**Blast radius, from the code:** `Bar` is `frozen=True`, so a defaulted field is a compatible add;
every other construction site — both fetch layers and both smoke tests — takes the default
untouched. `_reduce_ohlc` needs a fallback to `ts + 1min` for raw 1m source bars, whose `ts_close`
is `None`. Detector purity under `ADR-004:§9` is preserved: no I/O is added. **The natural key is
not affected** — `_natural_key` (`:1687-1692`) carries `source_bar_ts`, never `valid_from`, which is
also precisely why a re-run without a `DELETE` would skip every existing row rather than correct it.

**Not yet implemented.** No code changed in this session.

---

## What this changes about the corrective path

Part 1 established that the **legacy** builder's D-OB detection is non-canonical and
polarity-inverted with no FVG confirmation. Part 2 establishes that the **canon** layer's detector
conforms to ADR-004 §5.1 on all four axes, §5.2 in full, and §7.1 on the detection rule. The two
halves therefore point in different directions:

- The **detector** can stand. The parameter tables can stand. "Finish S31-C" is the right frame.
- The **writer's anchoring** cannot stand as-is. F-68 puts lookahead into every formation
  column and into the retest anchor; F-69 makes the retest cohort selection non-random, at a
  measured contamination rate of 63% / 81% / 80% across M5 / H / D. The retest cohort itself
  measures 10 positive / 8 negative at H, so the selection is contaminated without being
  flattering. **Every WR and P&L figure derived from `ict_primitive_outcomes` — including the
  S31-B holdout result and the S33 ENH-106 v7 cohort — inherits it.**
- The fix is decided: **Option 2**, carry `ts_close` on `Bar`. See *Operator decisions* → **D2**.
- Because the writer is **INSERT-only**, none of that is fixable in place. Any correction is a
  `DELETE` plus full recompute. **The cost is not the ~35 minutes previously recorded here
  without qualification.** S35's 2107s (35.1 min, 19,571 outcomes, NIFTY 1,028 + SENSEX 1,745
  tuples) does verify, and `git log` shows both files unchanged since `bc1cb85` — but that run
  was **v8.2**. The ADR-012 **v9** SL block has never run over the full window; CLAUDE.md
  records only an n=5 single-cell validation for it, with the full recompute explicitly
  deferred. The v9 delta is bounded and small — one cached M5 aggregation per symbol
  (`:1153-1156`), a bar walk per retested primitive, and one `_chain_premium_at` lookup on
  trigger, which is cache-only with no DB fallback (`:1403-1420`) and hits because the prefetch
  loads a contiguous range per tuple (`:1557-1570`). **The unbounded term is the tuple set.**
  It is enumerated at `_floor_5m(p.valid_from)` (`:1496`), with the strike taken from spot at
  that anchor and the expiry from `_nearest_weekly_expiry(anchor)` (`:1014`, `:1019`). Moving
  the anchor to the confirming bar's close re-picks strikes and expiries, so the tuple count —
  and with it the dominant per-tuple query cost — changes by an amount this audit cannot
  predict. **Budget ~35 minutes as a floor, not an estimate, and measure the tuple count on
  the first run.**
- And the table has **no consumer anywhere**. Nothing on any live surface reads it, so nothing
  currently trades on the defect. That is the one comfortable fact in Part 2, and it is also the
  measure of how far S31-C is from finished.

---

**Not committed**, per instruction.
