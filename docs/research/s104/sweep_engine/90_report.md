# 90_report — ADR-032 independent sweep, Phase 1

Read-only. Nothing outside `scratch/s103_sweep/` was written. No git write verb, no deploy, no
crontab change, no `.env` read, no fixture-suite run. Only DB access was `bin/roq.sh` (`merdian_ro`,
SELECT only). Phase 1 was run blind to the files listed in `00_census.txt` §6.

**No fixes are proposed and no finding is ranked.** Order below follows prompt §4.

---

## 1. Coverage census — three lines

1. **`~/meridian-cc` @ 8f9d466** — 1,366 tracked files, 46,945,697 bytes, 0 modified-tracked,
   10,811 untracked (all under `scratch/` and `research/`; 1,674 of them hold a Γ-size token,
   1,673 inside `scratch/`).
2. **`~/meridian-connect` @ 6f14a92** — 129 tracked files, 2,319,294 bytes, 0 modified-tracked,
   0 untracked. Only the 21 `.jpg` were not read.
3. **`~/meridian-engine` @ 8f9d466** — 1,366 tracked files, 46,945,697 bytes, tracked content
   **byte-identical** to `meridian-cc`, so the sweep covers it; its 14 untracked files are all
   runtime logs/output and hold no executable Γ logic.

Every tracked text file of every extension in trees 1 and 2 was swept, plus 30 `.gz`
(decompressed) and 36 `.docx` (text-extracted). **15,218 classified hit rows across 890 files**
in `10_hits.tsv`. Method deviation: **`rg` is not installed on this box**; `git ls-files -z` +
Python `re` per line was used instead.

---

## 2. Counts by kind × use

```
                display       magnitude     pass-through  ratio         sign          unknown       TOTAL
copy-through    562           0             2965          130           0             0             3657
dead            585           7             0             384           20            1650          2646
doc             5362          28            0             135           50            0             5575
fixture         0             2             976           8             0             0             986
formula-copy    23            141           0             0             4             0             168
label           103           4             0             9             2             5             123
reader          0             0             1214          34            8             0             1256
test            57            12            0             16            1             514           600
threshold       0             36            0             2             97            0             135
writer          2             65            0             0             1             0             68
TOTAL           6694          295           5155          718           183           2169          15214
```

(The four `SUPPLEMENTARY PASS` rows added after this table was computed — `backfill_hist_greeks.py:56,164`
and `tests/test_dex_recompute.py:174,351` — bring the file total to 15,218; they are
`formula-copy`/`test` × `magnitude`.)

**35 of these rows are `HAND-REVIEWED`** (an explicit per-site override table); **62 are
`SUPPLEMENTARY PASS`** (found only after the main token list was shown to have gaps — §5); the
remaining ~15,121 are `rule-based`. The `source of classification` column says which, per row.
The rule-based classification of the 5,575 `doc` rows and the 986 `fixture` rows is coarse by
design: prompt §3 item 8 asks for documents to be **listed only**, and the fixture rows are data
values rather than code decisions.

**Known classifier defects, stated rather than hidden:**
- The `dead` test is a filename regex (`_PRE_|.pre_|_backup|_checkpoint|.phase_b|_PATCHED|_broken_window`).
  It wrongly caught `capture_spot_1m_v2.py` (2 rows, owner `AWS cron`) because an earlier version
  of the regex included `_v2\.py$`. Those two rows are Windows-path docstring lines and carry no
  Γ value. 103 distinct files are classified `dead`; all others spot-checked are genuine
  unscheduled copies.
- My first classifier run put `merdian_compute/gamma.py:54` — the canonical Γ formula — in
  `kind=doc`, and `Board.tsx:27` in `scale = n/a (not a size)`, because the `is_size` test was
  case-sensitive and required a Γ **name** on the line, which the formula line does not have.
  Both were fixed and re-run. I found this by spot-checking five known-important `file:line`
  keys against the output rather than by reading the counts, which looked plausible either way.

---

## 3. The unknown bucket — 2,169 rows, 4 questions

Grouped, because the rows within each group differ only by file and line and one question settles
the whole group.

| n | group | the question that would settle it |
|---|---|---|
| **1,650** | `kind=dead` — in an unscheduled `_PRE_*` / `.pre_*` / `_backup` / `_checkpoint` / `.phase_b*` / `_PATCHED` full-file copy of a live writer (1,272 in backup `.py`, 376 in `sql/` apply files, 2 misclassified — see §2) | **Are these retained as reviewable history, or are any of them a revival candidate?** CLAUDE.md rule 4 requires full-file promotion, so each is a complete runnable file; `compute_gamma_metrics_local_PRE_S41_FIX1.py` alone contributes 154 rows and contains its own `/1e7`. If they are history, their scale is a historical fact and needs nothing. If any could be promoted, each carries an independent scale-A formula copy. |
| **514** | `kind=test` — a `1e-6` / `1e-9` tolerance or a `SELECT *` inside a test, a `docs/research/**` probe, or an `sql/` verification block, where the line itself names no Γ quantity (286 in `docs/`, 228 in `tests/`) | **Is the tolerance a statement about the Γ unit, or only about float equality?** Every one I read was float-equality (e.g. `abs(top1 - conc) > 1e-6` on a ratio). But a tolerance absolute in scale-A crore (`tests/test_p3a_invariants.py:67` `<= 0.01 Cr`, `tests/test_dex_recompute.py:175` `TOL_CR = 1e-6`) **is** a unit statement, and I cannot tell the two apart from the line alone for the remaining ~500. |
| **5** | `kind=label` — `.pine` input-widget `step=0.01`: `MERDIAN_ICT_Primitives_canonical.pine:67`, `…_v2.pine:67`, `…_v4.pine:67`, `merdian_ict_overlay.pine:45`, `merdian_ict_overlay.pine:50` | **None — settled on reading.** These are ICT fair-value-gap thresholds in **percent of price** (`fvgMinM5 = input.float(0.08, …, step=0.01)`), matched only because `0.01` is in the token list. They are not Γ. Listed because the prompt asks for every unclassified hit. |
| **0** | — | there is no residual group |

---

## 4. Every place a Γ size is read under a name I did not expect

The prompt's §2 token list does not contain any of the following. Each is a real Γ size
(`γ·OI·S²`-derived) reached under a different name. Nine sites, grouped by the mechanism.

### 4.1 Renamed at a Python boundary — the rename defeats a search by column name
`generate_pine_overlay.py` (**AWS cron 10:52 UTC**):
```
:235   "total_gex_cr": float(r["total_pin_gex_cr"])      # v_gex_strike_pin_zone
:236   "peak_gex_cr":  float(r["peak_pin_gex_cr"])
:257   "total_gex_cr": float(r["total_accel_gex_cr"])    # v_gex_strike_accel_zone — SAME dict key
:258   "trough_gex_cr": float(r["trough_gex_cr"])
…
:334   f"peak +{pin['peak_gex_cr']/1000:.0f}K Cr"
:335   f"zone +{pin['total_gex_cr']/1000:.0f}K Cr"
:363   f"trough {accel['trough_gex_cr']/1000:.0f}K Cr"
:364   f"zone {accel['total_gex_cr']/1000:.0f}K Cr"
```
`git grep peak_pin_gex_cr` reaches `:236` and never reaches `:334`. The PIN and ACCEL sides also
share the key `total_gex_cr`, so the name is ambiguous within the file. Names introduced:
**`total_gex_cr`**, **`peak_gex_cr`**.

### 4.2 Aliased in the board — a scale-B value under scale A's name
`~/meridian-connect/src/lib/queries.ts`:
```
:43    return data ? { ...(data as any), net_gex: (data as any).net_gex_1pct } : data;
:210   return (data ?? []).map((r: any) => ({ ...r, gex_cr: r.gex_cr_1pct }));
:392   return (data ?? []).map((r: any) => ({ ...r, net_gex: r.net_gex_1pct }));
```
So in `src/marketview/*` the names **`net_gex`** and **`gex_cr`** carry per-1 % values, while in
`src/lib/board.ts:137` the name `gex_cr` carries the raw per-100 % value read straight from
`gex_strike_snapshots`. One field name, two scales, one application. (The one consumer of the
scale-A side, `src/lib/read.ts:29`, uses it for sign only, so it is correct today.)
Downstream names: **`netDealerGamma`**, **`peakGammaCr`**, **`dampenTotal`**, **`amplifyTotal`**
(`src/marketview/state.ts:47,60-68`).

### 4.3 A Γ size computed in SQL under a name with no `gex_cr` or `net_gex` in it
`v_gex_repriced_flip` (live view, md5 `58ad6ba8f366c52a8e71b4ac1ea66864`):
```
exp(…)/(gr.s_grid * l.sigma * sqrt(e.t_years)) * l.oi * power(gr.s_grid, 2) / 10000000  AS total_gex
```
A full Black–Scholes γ recomputed on the ENH-131 spot grid, scaled to **scale A**, published as
**`total_gex`**. Name: **`total_gex`**. Also `docs/research/s100/r10/r10_curve_points.sql:175`
re-aliases that same quantity as **`curve_gex_cr`**.

`v_gex_greeks_l2_strike` (md5 `66cfb53bd8fb63a445977d236b9d62d6`) builds
`leg_gex_drift_iv` / `leg_gex_drift_time` as `u_gex_drift_* * oi * power(spot,2) / 10000000`
(Γ-type, S²) **in the same SELECT list** as `leg_delta_drift_*` = `… * oi * spot / 10000000`
(Δ-type, S¹). This is the mixing site prompt §2 asks for.

### 4.4 A Γ size in a golden query under two unexpected names, at a fourth scale
`tests/golden/2026-10-01_SENSEX/queries/ladder_replay_1001.sql:8,63,72-74`:
```
--  gamma_load(strike) = sum over CE+PE of gamma * oi * lot * spot^2 * 0.01 / 1e7
       sum(gex_abs)  AS gamma_load,
       gamma_load / nullif(max(gamma_load) OVER (PARTITION BY ts), 0) AS pct_of_leader,
```
Names: **`gamma_load`**, **`gex_abs`**. Scale: per-1 % **and** multiplied by `lot`, which no live
Γ path applies. Four conventions now exist in the repo (raw, /1e7, /1e7×100, /1e7×0.01×lot).

### 4.5 A module constant hiding the divisor
`backfill_hist_greeks.py:56` `CR_SCALE = 1e7` → `:164` `gamma * oi * (spot ** 2) / CR_SCALE`, and
`tests/test_dex_recompute.py:174` `CR = 1e7` → `:351` `gamma * oi * (spot ** 2) / CR`. Both are
Γ formula copies that the AST rule (scoped to literal `BinOp` operands) cannot see. The second
means **suite step 11 recomputes the gamma formula, not only the delta one its name implies.**
Names: **`CR_SCALE`**, **`CR`**.

### 4.6 A Γ size × 100 — a scale that is neither A nor B
`canonical_ob_gamma_zone.py:204` and `canonical_ob_gamma_zone_bs.py:323`:
`gamma * oi * spot**2 * 100.0 / 1e7`. Effectively `γ·OI·S²/1e5`. Unscheduled. Flagged because the
discrepancy against `gex_cr` is exactly 100 — the same factor as the unit change, inverted.

### 4.7 Magnitude thresholds under names with no `gex_cr`/`net_gex`
`NETGEX_MAX_CR` / `NETGEX_MIN_CR` (`backfill_gamma_metrics_broken_window.py:71,72`),
`RAW_NET_GEX_THRESHOLD` (`phase0b_p5_pinned_proxy_v2.py:78`),
`netgex_in_cr_range` (`:122` of the former), `op_sane` (`verify_td_new_3_net_gex_unit.py:124`),
`GAMMA_UNIT_BOUNDARY` (`s31_weekly_attribution_diagnostic.py:94`, a **date**).
All uppercase, so the lower-case `net_gex` token in the §2 list does not match them; they were
found by the identifier census.

### 4.8 Three display formatters that change the UNIT WORD at a magnitude
`crLakh` (`src/pages/Board.tsx:27`), `lad` (`src/pages/Board.tsx:197`),
`lak` (`src/components/board/GammaRiver.tsx:7`) — all three branch at `|v| >= 1e5` and emit
`"…L Cr"` / `"…L"` above it, plain `" Cr"` / plain below. Names: **`crLakh`**, **`lad`**, **`lak`**,
**`fmtCr`** (`Board.tsx:444`, = `crLakh`). None contains a Γ token; `lad` and `lak` were missed
entirely by the main sweep (§5).

### 4.9 The inverse case — a name that LOOKS like a Γ size and is NOT
`latest_net_gamma_by_strike.net_gamma` = `gamma_call - gamma_put`, with **no OI, no S², no /1e7**
(full body in `40_db_findings.md` §6). Bare per-option γ. It propagates to
`latest_atm_neighborhood`, `latest_gamma_walls`, `latest_top_gamma_strikes` as `net_gamma` and
`abs_net_gamma`. `net_gamma` **is** in the prompt's §2 list as a Γ-size carrier; here it is not
one, and rescaling it would introduce an error rather than remove one. Same shape:
`expiry_outcomes.gex_regime_persistence`, `market_environment_snapshots.gex_regime_persistence_20d`
(ratios) and `…net_gex_regime` (a `text` regime word); and every `*_dex_cr` / `*_flow_cr` /
`*_iv_*_cr` / `*_t_*_cr` column (Δ-notional, `oi·S/1e7`), plus
`fii_dii_cash_daily.{fii,dii}_{buy,sell,net}_cr` (₹ crore of cash flow).

---

## 5. What I could not check, and why

### 5.1 Permissions — two whole classes of reader are invisible to this sweep
| target | error | consequence |
|---|---|---|
| `pg_stat_statements` | `relation "pg_stat_statements" does not exist` — the **extension IS installed** (`pg_extension` lists it); the relation is simply not granted to `merdian_ro` | **Prompt §3 item 5(f) is unanswerable.** Any reader that exists only as query traffic — a PostgREST client, a Lovable preview, a hand-run editor query, an external job — is not in this report. Every reader named here came from a repo or the catalog. |
| `cron.job` | `permission denied for schema cron` | Cannot list `pg_cron` jobs or confirm CLAUDE.md's jobid-19 tripwire. A zero from this role would be the reader, not the state. |

Neither was worked around. `bin/roq.sh` is not a substitute for the editor under `postgres`.

### 5.2 My own pattern set had gaps — measured, not assumed
I checked the sweep against itself: of 40 hand-curated `file:line` sites, **5 matched no sweep
row**. Running that check is the only reason I know the following, and I would not have known it
from the hit counts. Three distinct gaps, and a supplementary pass recovered **62 rows**:

| gap | why the main sweep could not fire | what it hid |
|---|---|---|
| **i. magnitude/tolerance literals absent from the token list** — the list had `1e7`, `10_000_000`, `0.01` but not `1e5`, `1e6`, `1e9`, `1e-6`, `1e-9`, `1_000_000` | a line holding only `Math.abs(v) >= 1e5` carries no listed token | `Board.tsx:197` (`lad`), **`GammaRiver.tsx:7` (`lak`) — a live Board component, missed entirely**, `test_p3a_invariants.py:86`, `verify_td_new_3_net_gex_unit.py:124` |
| **ii. the sweep is line-scoped; a multi-line call is invisible** | `.select("*")` sits one line below its `.from("v_gex_…")` | **4 of the 5 `select("*")` calls over a Γ relation**: `queries.ts:36,223,243,289`. The Python AST pass had a 12-line lookback for this; **TypeScript had no equivalent** |
| **iii. an AST rule scoped to literal operands cannot fire on a named constant** | `/ CR_SCALE` is a `Name`, not a `Constant` | 2 more Γ formula copies: `backfill_hist_greeks.py:164`, `tests/test_dex_recompute.py:351` |

Gap iii also broke a claim I had already written: I asserted in `20_ast_findings.md` that no
module-constant divisor existed, then ran the grep that would show one and it returned two. Both
the claim and its correction are in that file. The general shape is CLAUDE.md rule 0's: three of
my own checks could not fail for the reason they named.

**Residual risk, stated:** gaps i and ii are now covered for the patterns I thought of after the
fact. I have no way to bound what a fourth gap of the same kind would hide, because the only
instrument that found the first three was comparing the sweep against a hand-built list — and
that list was built from the same reading that produced the sweep.

### 5.3 File types and content I did not read
- **21 `.jpg`** in `meridian-connect` — binary images, not read.
- **`.gz` bodies** — the 30 `.gz` were decompressed and their **headers** swept, but the data rows
  were not entered as hit rows (up to 542 matching lines per file of golden-day exports). The Γ
  **values** inside them are reported in `70_tests_and_fixtures.md` §3 by column and file instead.
- **36 `.docx`** — text-extracted and token-scanned only (10 hits total), never read as documents;
  CLAUDE.md names reading them at session start as an anti-pattern.
- **The 15 Phase-1 blind files** (`00_census.txt` §6). For two of them — the applied
  `COMMENT` statements and the pre-change definition snapshot — the facts were recovered
  independently from the live catalog, so nothing in this report depends on them. For the ADR
  itself and the S102 research and Lovable prompts, **this sweep says nothing**.

### 5.4 Things that are structurally beyond a static sweep
- **Dynamic column names.** The AST pass (c) flagged 385 f-string / `getattr` / `.get(var)` /
  concatenation sites near a Γ token. I read the ones in scheduled files; a column name assembled
  from data at runtime cannot be resolved statically, and I did not execute anything.
- **The Local Windows tree.** CLAUDE.md names Local as PRIMARY LIVE with Task Scheduler, at
  `C:\GammaEnginePython`. This box is the AWS SHADOW. I read the 31 tracked `.ps1`/`.bat` files,
  but **I cannot see which Windows scheduled tasks are actually enabled**, so the `owner` column
  is accurate for AWS cron and the orchestrator and is an inference for Local.
- **Whether `tests/run_offline.sh` passes today.** Not run (prompt §1; CLAUDE.md rule 23).
  Everything in `70_tests_and_fixtures.md` is read from source.
- **Browser-side behaviour.** The board was read as source; no page was loaded, so I cannot say
  which components actually render on a live session versus being reachable-but-unrendered. The
  dead/mock calls in `30_ts_findings.md` §7 rest on import graphs, not on runtime.

---

## 6. Output files and their sha256
```
a079bb13bd274e8eb49d3af04a91aadfd098dfa8687038435e686b4faae1e6fe  00_census.txt
c41763f50fa637324da117559ddcb20eff9c56bfd494595894e87a3b10ba94be  00_census_raw.txt
8d6ed56d52042a130a72f161191ef34a45d287ea90a4b82687b1452212e07b28  10_hits.tsv
569289a2606cc248f6065709e76548ac2dbbc8ca8e0a4a92d0bd0f5ab0ba4077  20_ast_findings.md
e5dd4080c1c1b8b4dfc667757dc7fc3f4626fe69a12225b8c26f994cb6fe75d3  30_ts_findings.md
4f7b7a39de88f986656c0895a78c3c6efa09bea0a3666abb34de24360060abf5  40_db_findings.md
2efd3732e469a5de498952ebfcd2e26dd9264e56bc1caa9304edbd6961cc134f  41_db_raw.txt
8667e7e295af7550d3cedd5f5cc5bd420ce4f9d331e24cd8e6999f0f8a1209fd  50_outbound_and_constants.md
aecbf0d9b72bb1c7e86f70d5051ecfac580c43fbf2a0b38bb31d80cfe7c15b0a  70_tests_and_fixtures.md
19824a8aa940d8797eb26d762530101555c1410242b61852456ce4e28b1e6a77  80_documents.md
```

`90_report.md` is not in its own list. Its hash, computed after the block above was written:

```
526b25bfcb8b3992bda7bbb7af7d429c00045faeb9cc5fbc6c69c0317da57d82  90_report.md
```
