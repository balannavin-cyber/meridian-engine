# parity_render_contract.md — what the database offers a renderer, and what it does not

**Session 84 · 2026-09-25 · measure-only**

## 0. Scope, method, and what this document is not

This is a **read contract**: for each of eighteen objects, what a front end can select, at what grain, with what state vocabulary, under what privilege, and from which committed DDL. It is written so that a rendering pass can be specified without re-deriving any of it, and so that the fields a renderer would *want* and cannot have are named rather than discovered late.

**It authorises nothing.** Per the S37 GEX-as-context-not-gate ruling every object below is display-only; none routes, gates, or carries a predictive claim. Naming a field here is not evidence it is useful.

**Method.** Every query ran through `bin/roq.sh` as `merdian_ro` — SELECT-only, `default_transaction_read_only=on`, 30 s `statement_timeout`. No DDL, no write, nothing under `~/meridian-engine`. Every result was written to `scratch/s84_contract/<name>.out` before being read into this document; each claim below cites that file. Counts and numbers are copied from those files, not from rendered tables in the session. **Nothing in this document is filed** — see §5.

**A caveat that bounds the whole document.** Section 1(c) samples were taken **after the close** (latest GEX run 09:50 UTC, latest chain 10:10 UTC, i.e. 15:20 and 15:40 IST). Freshness flags therefore read `false` across the board. That is the expected post-close state and **not** evidence of a stall; it does mean this document cannot speak to intraday freshness behaviour.

**Redaction.** The parity target's product name is not written here. The spec is cited as `docs/registers/MERDIAN_<REDACTED>_Parity_Spec.md`; matching in shell was done by a split pattern, and only counts were printed. The appendices were checked for the name and return **0** on all three files.

**Two clocks.** The GEX family is scoped to the latest `gex_strike_snapshots` run; the chain family (`v_gex_repriced_flip`, `v_iv_*`, `v_max_pain_by_strike`, `v_oi_rotation_since_open`) is scoped to the latest `option_chain_snapshots` ts. Today those differed by 20 minutes. **A renderer must not place a value from one family beside a value from the other without showing both timestamps** — this is the S81 lesson that a count taken at one moment cannot be compared with a count taken at another (`samples_01_04.out`, `samples_13_17.out`).

---

## Part 1 — the eighteen objects

Legend: **(a)** columns · **(b)** grain · **(c)** sample · **(d)** state vocabulary · **(e)** anon privileges · **(f)** DDL source + ENH.

Privileges are from `pg_class.relacl` via `aclexplode` (`acl.out`). Columns are `information_schema.columns` in ordinal order (`columns.out`, 291 rows).

---

### 1. `gamma_metrics` — table

**(f)** **No `CREATE TABLE` exists anywhere in `sql/`** (`sqlmap.out:1`). The only committed DDL touching it is a column-add migration, `sql/2026-05-30_gamma_metrics_s41_p0a_columns.sql`. ENH: pre-dates the register's GEX line; columns 26–27 are S41 P0.a.

> **Finding (P1) — ADR-025 D2 clause 4 gap.** The single most-read table in the parity set has no reproducible DDL under version control. Clause 4 exists because "a view living only in the database is one `DROP` from unrecoverable"; this is that condition on a *table*, and it is worse, because a table also holds the data.

**(b)** Grain `(symbol, ts)` — one row per symbol per compute cycle (~5 min). **Inferred from the data, not documented: the table carries no COMMENT** (`comments.out:1`).

**(a)** Per the brief, scoped to the three parity columns of the table's 27:

| pos | column | type | null |
|---|---|---|---|
| 6 | `net_gex` | numeric | YES |
| 8 | `flip_level` | numeric | YES |
| 15 | `regime` | text | YES |

Read-keys needed to address them: `ts` (2, timestamptz, NOT NULL), `symbol` (3, text, NOT NULL), `expiry_date` (4, date, NOT NULL), `spot` (5, numeric, NOT NULL), `dte` (25, integer). Units: `net_gex` is **Crore** (the `/1e7` of TD-NEW-3, S27).

**(c)** `samples_01_04.out:3-10` — 3 rows/symbol at latest ts:

| symbol | ts | regime | net_gex | flip_level | spot |
|---|---|---|---|---|---|
| NIFTY | 09:50:07 | SHORT_GAMMA | −1 378 169.40 | 23 228.65 | 23 128.10 |
| NIFTY | 09:45:06 | SHORT_GAMMA | −1 065 719.79 | 23 181.90 | 23 128.10 |
| NIFTY | 09:40:07 | SHORT_GAMMA | −1 733 609.13 | 23 189.63 | 23 107.85 |
| SENSEX | 09:50:07 | LONG_GAMMA | 7 266 392.51 | 71 103.43 | 73 881.44 |
| SENSEX | 09:45:06 | LONG_GAMMA | 7 296 021.83 | 71 103.25 | 73 881.44 |
| SENSEX | 09:40:07 | LONG_GAMMA | 7 200 878.16 | 71 103.69 | 73 824.12 |

**(d)** `regime` — observed over 2 days: `LONG_GAMMA` (293), `SHORT_GAMMA` (35), `NO_FLIP` (1) (`distinct_states.out:2-4`). **Emittable set is exactly these three and no more**, from `compute_gamma_metrics_local.py:547-550` (`determine_regime.out`):

```python
def determine_regime(net_gex, flip_level):
    if flip_level is None: return "NO_FLIP"
    return "LONG_GAMMA" if net_gex >= 0 else "SHORT_GAMMA"
```

Nothing unobserved. **The split is a hard sign test at `net_gex >= 0` with no dead zone** — see Part 3 §3.

**(e)** RLS **on**; anon `SELECT` only (`acl.out:4`).

---

### 2. `gex_strike_snapshots` — table

**(f)** `sql/2026-05-25_enh80_gex_strike_snapshots.sql:30` · **ENH-80** (ADR-014, superseded same session by ADR-015).

**(b)** *"Per-strike GEX time-series."* — live COMMENT, 97 chars (`comments.out:2`). Grain `(run_id, strike, expiry_date)`, per ADR-015.

**(a)** **Ordinal positions 9, 13, 14, 15 are absent** — dropped by the ADR-015 v2 migration.

| pos | column | type | null |
|---|---|---|---|
| 1 | `id` | uuid | NO |
| 2 | `run_id` | uuid | NO |
| 3 | `symbol` | text | NO |
| 4 | `ts` | timestamptz | NO |
| 5 | `expiry_date` | date | NO |
| 6 | `dte` | integer | NO |
| 7 | `strike` | numeric | NO |
| 8 | `spot` | numeric | NO |
| 10 | `oi_call` | bigint | YES |
| 11 | `oi_put` | bigint | YES |
| 12 | `gex_cr` | numeric | NO |
| 16 | `created_at` | timestamptz | NO |
| 17 | `gamma_call` | double precision | YES |
| 18 | `gamma_put` | double precision | YES |

> **Correction to CLAUDE.md.** The ADR-015 settled bullet lists the schema as `oi_total_calls` / `oi_total_puts`. **The live columns are `oi_call` / `oi_put`** (`columns.out`, pos 10–11). This is the drift already filed as TD-S83-NEW-7; it is confirmed here and remains uncorrected in CLAUDE.md. **A renderer that trusts the CLAUDE.md bullet will select a non-existent column.**

**(c)** `samples_01_04.out:14-21` (3 lowest strikes at latest ts). NIFTY 15000/16500/18000 all show `gex_cr = 0.0` with **`gamma_call` and `gamma_put` NULL**; SENSEX 68000/68100/68200 carry gamma ~4e-05/1e-05 and non-zero `gex_cr`. **A strike row existing does not mean it contributes** — see `n_strikes` vs `n_contributing` in §6.

**(d)** No status column.

**(e)** RLS **on**; anon `SELECT` only (`acl.out:5`).

---

### 3. `v_gex_strike_pin_zone` — view · **L2, one of the two BUILT layers**

**(f)** `sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql:26` · **ENH-81** (S69 perf rescope). An earlier body survives at `sql/2026-05-25_enh81_v_gex_strike_pin_zone.sql:18`; the S69 file is current.

**(b)** *"pin zone via prominence walk, SCOPED to latest run_id per symbol… τ_pin via `get_parameter_num`."* — live COMMENT, 206 chars (`comments.out:3`). Grain `(symbol)` — exactly one row per symbol.

**(a)** `run_id` uuid · `symbol` text · `expiry_date` date · `ts` timestamptz · `pin_lower` numeric · `pin_upper` numeric · `n_strikes` bigint · `total_pin_gex_cr` numeric · `peak_pin_gex_cr` numeric · `peak_pin_strike` numeric · `tau_used` numeric.

**(c)** `samples_01_04.out:24-27` — 1 row/symbol (the grain):

| symbol | pin_lower | pin_upper | n | peak strike | peak Cr | τ |
|---|---|---|---|---|---|---|
| NIFTY | 23 300 | 23 500 | 5 | 23 400 | 596 137.25 | 0.3 |
| SENSEX | 71 200 | 71 800 | 7 | 71 400 | 1 065 902.40 | 0.3 |

**(d)** No status column. `tau_used` is a surfaced parameter, not a state.

**(e)** RLS off; anon `SELECT` only (`acl.out:6`).

> **Utility, stated so it is not mistaken.** S74 answered PIN's predictive utility **NO** on the holdout (NIFTY mean −0.1996, CI [−0.2998, −0.0801], 19 of 21 sessions negative). The zone renders; it does not predict. Any label implying attraction contradicts the measurement.

---

### 4. `v_gex_repriced_flip` — view · **L3**

**(f)** `sql/2026-09-25_s83_v_gex_repriced_flip.sql:94` · **ENH-131** (S83, per ADR-025 Amendment B clause B7).

**(b)** *"One row per symbol at the LATEST `option_chain_snapshots` ts. Grain (symbol). Consumers MUST ORDER BY symbol — a view body carries no ordering guarantee. DISPLAY ONLY… it routes nothing, gates nothing, and makes NO PREDICTIVE CLAIM."* — live COMMENT, 6 997 chars (`comments.out:4`), the longest in the set. **It records its own failed gates**; a renderer surfacing this level should carry that, not hide it.

**(a)** `symbol` text · `ts` timestamptz · `spot` numeric · `front_expiry` date · `t_days` float8 · `r_sess` float8 · `r_p10` float8 · `r_p90` float8 · `n_r_rows` int · `atm_iv` numeric · `sigma_1d` float8 · `flip` float8 · `flip_direction` text · `flip_minus_spot` float8 · `flip_sigma` float8 · `n_cross_within_2sigma` int · `n_cross_full_grid` int · `status` text.

**(c)** `samples_01_04.out:30-33` — 1 row/symbol:

| symbol | ts | spot | flip | direction | flip−spot | flip_σ | x<2σ | x_grid | status |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY | 10:10:04 | 23 140.50 | 23 137.19 | neg→pos | −3.31 | −0.0278 | 1 | 1 | **OK** |
| SENSEX | 10:10:04 | 73 895.74 | *null* | *null* | *null* | *null* | 0 | 0 | **NO_CROSSING** |

**(d)** `status` observed `OK`, `NO_CROSSING` (1 each). **Emittable but unobserved today: `SKIPPED_EXPIRY`, `UNMEASURABLE_R`** (`emittable_literals.out:2`). `flip_direction` observed `neg->pos` and NULL; **unobserved: `pos->neg`**.

> **A renderer must handle all four `status` values and a NULL `flip`.** SENSEX is in that state right now — half the symbols. A component that assumes a flip level exists will render blank or crash on the live data of this session.

**(e)** RLS off; anon `SELECT` only (`acl.out:7`).

---

### 5. `v_gex_strike_walls` — view · **L4 + L5**

**(f)** `sql/2026-09-15_s79_v_gex_strike_walls.sql:47` · **ENH-120**.

**(b)** *"put/call wall as raw-OI argmax within a ±band*sigma moneyness window, scoped to the latest run per symbol (ADR-021, S72 FIX 2 lateral form)… Gamma-weighted argmax was tested and rejected (collapses to ATM). Sigma columns are the distance measure; raw strikes exist for labelling only."* — live COMMENT, 1 449 chars (`comments.out:5`). Grain `(run_id, symbol, expiry_date)`.

**(a)** `run_id` · `symbol` · `expiry_date` · `ts` · `dte` · `spot` · `sigma` · `band_used` · `atm_iv_used` · `atm_iv_ts` · `atm_iv_age_min` · `iv_floor_min_used` · `iv_fresh` bool · `put_wall` · `call_wall` · `put_wall_oi` bigint · `call_wall_oi` bigint · `put_wall_sigma` · `call_wall_sigma` · `corridor_width_sigma` · `corridor_state` text · `n_eligible_strikes` bigint.

**(c)** `samples_05_08.out:3-6`:

| symbol | put_wall | call_wall | put_oi | call_oi | width σ | state | σ | elig |
|---|---|---|---|---|---|---|---|---|
| NIFTY | 23 000 | 23 500 | 17 260 280 | 15 219 815 | 1.744 | INSIDE | 286.65 | 18 |
| SENSEX | 73 500 | 74 000 | 672 240 | 669 700 | 0.377 | INSIDE | 1 327.74 | 40 |

**(d)** `corridor_state` observed `INSIDE` only (2/2). **Emittable and unobserved: `ABOVE_CEILING`, `BELOW_FLOOR`, `UNDEFINED`** (`emittable_literals.out:3`). `iv_fresh` observed `true` only; `false` unobserved.

> **Three of four corridor states have never rendered.** A renderer cannot be styled against observed data alone here — `UNDEFINED` in particular must have a defined visual, and it is reachable.

**(e)** RLS off; anon `SELECT` only (`acl.out:8`).

---

### 6. `v_gex_abs_exposure` — view · **L6**

**(f)** `sql/2026-09-15_s79_v_gex_abs_exposure.sql:77` · **ENH-121**.

**(b)** **No COMMENT live** (`comments.out:6`). The file *contains* one at `:145-146`: *"sum(abs(gex_cr)) beside sum(gex_cr), scoped to the latest run per symbol… grain (run_id, symbol, expiry_date)."*

> **Finding (P2) — the S81 part-run shape, unremediated.** TD-S81-NEW-5 established that `COMMENT` and `GRANT` must ship as **live statements** in the `sql/` file, because a rebuild from a body-only file yields a view that is correct and undocumented. This file is worse than body-only: its `COMMENT` is a live statement that **was never executed**, and its `GRANT` is **commented out** at `:156-157` (`comment_grant_in_file.out`) while anon holds `SELECT` live. A rebuild from this file produces a view that is **anon-unreadable** — HTTP 200, zero rows, the TD-S37-03 silent-empty shape. Two more instances in §13 and §14.

**(a)** `run_id` · `symbol` · `expiry_date` · `ts` · `dte` · `spot` · `net_gex_cr` · `abs_gex_cr` · `n_strikes` bigint · `n_contributing` bigint.

**(c)** `samples_05_08.out:11-14`:

| symbol | net_gex_cr | abs_gex_cr | n_strikes | n_contributing |
|---|---|---|---|---|
| NIFTY | −1 378 169.40 | 7 638 401.97 | 138 | 113 |
| SENSEX | 7 266 392.51 | 8 558 328.50 | 137 | 127 |

**net/gross = 0.180 (NIFTY), 0.849 (SENSEX)** — a 4.7× spread, and the reason S83's 1 % net-vs-net gate was mis-specified. `n_contributing < n_strikes` on both: 25 NIFTY strikes and 10 SENSEX strikes are stored but contribute nothing.

**(d)** No status column.

**(e)** RLS off; anon `SELECT` only (`acl.out:9`).

> The file's own COMMENT warns that `net_gex_cr` **duplicates `gamma_metrics.net_gex` and is not an independent check** — both come from `signed_gamma_exposure()`, so any comparison passes by construction. A renderer must not present them as corroborating.

---

### 7. `v_gex_concentration` — view · **L12, HHI leg**

**(f)** `sql/2026-09-15_s79_v_gex_concentration.sql:185` · **ENH-122**.

**(b)** *"Herfindahl max/sum on the gamma book, three legs… Latest-run scoped, grain (run_id, symbol, expiry_date). THE SPLIT IS LOAD-BEARING: call and put concentration correlate 0.71–0.87 at 0 DTE but −0.00 to 0.15 away from it."* — live COMMENT, 1 951 chars (`comments.out:7`).

**(a)** `run_id` · `symbol` · `expiry_date` · `ts` · `dte` · `spot` · `dte_bucket` text · `hhi_net` numeric · `hhi_call` float8 · `hhi_put` float8 · `top_strike_net` numeric · `n_strikes` bigint · `n_contributing` bigint.

**(c)** `samples_05_08.out:19-22`:

| symbol | bucket | hhi_net | hhi_call | hhi_put | top strike |
|---|---|---|---|---|---|
| NIFTY | 3+ | 0.144258 | 0.141073 | 0.199908 | 23 000 |
| SENSEX | 3+ | 0.124546 | 0.127092 | 0.118564 | 71 400 |

**(d)** `dte_bucket` observed `3+` only. **Emittable and unobserved: `0`, `1-2`** (`emittable_literals.out:4`) — both symbols are ≥4 DTE today.

**(e)** RLS off; anon `SELECT` only (`acl.out:10`).

> **The COMMENT names the measure correctly — "max/sum" — and the column name does not.** `hhi_net` = 0.14425758917096207626 is **byte-identical** to rank-1 `share_of_abs` in §8 (`samples_05_08.out:19` vs `:29`). It is a dominance ratio, not a Herfindahl index. See Part 3 §4.

---

### 8. `v_gex_strike_rank` — view · **L12, ranked leg**

**(f)** `sql/2026-09-22_s81_v_gex_strike_rank.sql:131` · **ENH-125**.

**(b)** *"One row per contributing strike of the latest run per symbol… grain (run_id, symbol, expiry_date, strike). The siblings… are one row per RUN; this one is per STRIKE. Consumers MUST ORDER BY strike_rank."* — live COMMENT, 3 820 chars (`comments.out:8`).

**(a)** `run_id` · `symbol` · `expiry_date` · `ts` · `dte` · `spot` · `sigma` · `atm_iv_used` · `atm_iv_age_min` · `iv_fresh` bool · `strike_rank` bigint · `strike` · `gex_cr` · `abs_gex_cr` · `side` text · `share_of_abs` · `cum_share_of_abs` · `dist_sigma` · `n_ranked` bigint · `n_strikes` bigint.

**(c)** `samples_05_08.out:27-34` (rank ≤3):

| symbol | rank | strike | gex_cr | side | share | cum | dist σ |
|---|---|---|---|---|---|---|---|
| NIFTY | 1 | 23 000 | −1 101 897.45 | AMPLIFYING | 0.1443 | 0.1443 | −0.447 |
| NIFTY | 2 | 23 100 | −882 964.51 | AMPLIFYING | 0.1156 | 0.2599 | −0.098 |
| NIFTY | 3 | 23 400 | 596 137.25 | DAMPENING | 0.0780 | 0.3379 | 0.949 |
| SENSEX | 1 | 71 400 | 1 065 902.40 | DAMPENING | 0.1245 | 0.1245 | −1.869 |
| SENSEX | 2 | 71 200 | 1 064 124.57 | DAMPENING | 0.1243 | 0.2489 | −2.020 |
| SENSEX | 3 | 71 300 | 1 062 748.49 | DAMPENING | 0.1242 | 0.3731 | −1.944 |

**(d)** `side` observed `AMPLIFYING` (107), `DAMPENING` (133) — the complete emittable set (`emittable_literals.out:5`). Nothing unobserved. `iv_fresh` observed `true` only.

**(e)** RLS off; anon `SELECT` only (`acl.out:11`).

> **This view is named "pin conviction" in its COMMENT and exposes no conviction column.** SENSEX ranks 1–3 are separated by 0.03 % of share — a renderer showing "top strike" implies a decisiveness the numbers deny. See Part 3 §5.

---

### 9. `v_oi_rotation_since_open` — view · **L13, live leg**

**(f)** `sql/2026-09-22_s81_v_oi_rotation_since_open.sql:70` · **ENH-127**.

**(b)** *"L13 OI rotation since open, LIVE ONLY. One row per symbol per front-expiry strike, CE and PE side by side: open interest at the session anchor, at the latest snapshot, and the delta between them. Grain (symbol, expiry_date, strike). Historical rotation is OUT OF SCOPE."* — live COMMENT, 5 632 chars (`comments.out:9`).

**(a)** `symbol` · `expiry_date` · `dte` · `anchor_ts` · `latest_ts` · `strike` · `ce_oi_anchor_qty` · `ce_oi_latest_qty` · `ce_oi_delta_qty` · `ce_presence` text · `pe_oi_anchor_qty` · `pe_oi_latest_qty` · `pe_oi_delta_qty` · `pe_presence` text · `snapshot_age_min` · `stale_floor_min_used` · `is_fresh` bool.

**(c)** `samples_09_12.out:3-10` — top-3 by |Δ| per symbol. Anchor 03:45:05 UTC, latest 10:10:04, age 108.7 min, floor 30, `is_fresh = false`.

**(d)** `ce_presence`/`pe_presence` observed `BOTH` only (455 each). **Emittable and unobserved: `ANCHOR_ONLY`, `LATEST_ONLY`** (`emittable_literals.out:6`). `is_fresh` observed `false` only (455) — post-close.

**(e)** RLS off; anon `SELECT` only (`acl.out:12`).

#### Finding (P3) — the anchor is fabricated today, and this contradicts TD-S83-NEW-5

SENSEX 72300 CE reports Δ = **−48 767 480**. Chasing it: `oi = 48 768 100` with `ltp = 5464.15` held **frozen across every snapshot from 03:05 to 04:10 UTC**, then `ltp` corrected at 04:15 to 1537.35 and `oi` corrected at 04:20 **to 40** (`oi_anomaly.out`, `oi_anomaly2.out`).

**The anchor at 03:45 sits inside that stale window.** Every Δ derived from it on those strikes is an artefact of a vendor carrying a stale row, not rotation. Bounded: **4 SENSEX CE + 1 PE strikes exceed |Δ| > 1M, max 48 773 340; NIFTY's max is 3 683 095** — an order of magnitude apart, and NIFTY's figures are plausible (`oi_anomaly3.out`).

**This is also a correction to TD-S83-NEW-5**, which records SENSEX back-leg strikes **72100 / 72200 / 72300 / 72400 CE** reading `iv` **110.15 / 116.54 / 115.46 / 114.38** against an ATM of 13.0986 (ratios 8.41–8.90×) while holding **48 717 880 to 48 773 740** open interest, and which states in its title and its priority field that **"the open interest there is real"** and is "not a dead-strike artefact".

Three measurements contradict that on this session:

1. **The OI figures are the stale-window values.** TD-S83-NEW-5's 48 773 740 for 72400 CE is **byte-identical** to this view's `ce_oi_anchor_qty` for 72400 (`samples_09_12.out`). Its latest value is **400**.
2. **They correct within the session.** 72300 CE goes 48 768 100 → **40** at 04:20; 72400 CE goes 48 773 740 → **40** at 04:10 (`iv_stale_correction.out`).
3. **The `iv` anomaly and the OI anomaly are the same row, and share one cause.** On 72300 CE, while `ltp` is the stale 5464.15 the `iv` reads **119.30 and 121.04** — the TD's 110–117 band. At 04:15 `ltp` corrects to 1537.35 and `iv` **drops to 14.89** in the same row, before the OI corrects five minutes later (`iv_stale_correction.out`). 72400 CE, whose `ltp` was never stale, reads `iv` 14.11 throughout.

So the ~8× ATM implied volatility is not an unexplained property of the vendor's `iv`; it is **a stale `ltp` inverted into an implied vol** — the same feed defect as the S71 *"`ltp` is the last trade, not a price"* finding, which TD-S83-NEW-5 already cross-references as "a different column of the same feed". On this evidence it is not a different column; it is the same row.

**Bounds, stated.** Two strikes, one session, one symbol. I have not checked 72100/72200, other sessions, or NIFTY's two put exceptions. The mechanism is inferred from the timing coincidence of three columns correcting together, not from vendor documentation. **This is a §D candidate** — a register entry written from a measurement that a later measurement contradicts, which is the D.29/D.32 shape.

**Consequence for rendering.** Until resolved, **L13 must not be rendered on SENSEX without an outlier guard**; `is_fresh` does not catch this, because the *anchor* is stale while the *snapshot* is timely. Severity **S2**, not S1: L13 is display-only and no gate reads it.

---

### 10. `v_gex_net_gamma_river` — view · **L14**

**(f)** `sql/2026-09-22_s81_v_gex_net_gamma_river.sql:103` · **ENH-126**.

**(b)** *"One row per symbol per session, the settled daily net dealer gamma with its sign and the spot it was observed at. Grain (symbol, session_date)… session_rank 1 is the most recent session. SOURCE IS gamma_metrics ONLY, AND THAT IS A DECISION, NOT A CON[straint]…"* — live COMMENT, 4 743 chars (`comments.out:10`).

**(a)** `symbol` · `session_date` date · `ts` · `session_rank` bigint · `net_gex_cr` · `gamma_side` text · `spot` · `session_min_net_gex_cr` · `session_max_net_gex_cr` · `n_runs` bigint · `session_complete` bool · `expiry_date` date · `dte` int.

**(c)** `samples_09_12.out:15-22` (rank ≤3):

| symbol | date | rank | net_gex_cr | side | min | max | runs |
|---|---|---|---|---|---|---|---|
| NIFTY | 09-25 | 1 | −1 733 609.13 | AMPLIFYING | −1 733 609 | 1 294 505 | 82 |
| NIFTY | 09-24 | 2 | 1 051 483.99 | DAMPENING | −2 072 804 | 2 015 791 | 83 |
| SENSEX | 09-25 | 1 | 7 200 878.16 | DAMPENING | 7 200 878 | 16 818 087 | 81 |
| SENSEX | 09-24 | 2 | 1 116 952.35 | DAMPENING | −15 601 804 | 5 937 909 | 83 |

**(d)** `gamma_side` observed `AMPLIFYING` (34), `DAMPENING` (26) — complete set (`emittable_literals.out:7`). `session_complete` observed `true` (58), `false` (2).

**(e)** RLS off; anon `SELECT` only (`acl.out:13`).

> **The daily value is a single sample, not a session aggregate**, and the min/max columns prove it: SENSEX 09-24 closes at +1.1M inside a range of −15.6M to +5.9M. **A river rendered from `net_gex_cr` alone draws a line through one arbitrary point of each day's range.** The min/max columns exist precisely so a renderer can show the band; it should.

---

### 11. `v_iv_term_structure` — view · **L9**

**(f)** `sql/2026-09-24_s83_v_iv_term_structure.sql:69` · **ENH-130**.

**(b)** *"One row per (symbol, leg) at the LATEST ts per symbol. Grain (symbol, leg). Consumers MUST ORDER BY symbol, leg… DISPLAY ONLY… ATM IS THE HOUSE SPOT GRID, round(spot / step) * step."* — live COMMENT, 4 922 chars (`comments.out:11`).

**(a)** `symbol` · `ts` · `leg` bigint · `expiry_date` · `dte` int · `dte_sessions` bigint · `t_years` numeric · `atm_strike` · `ce_iv` · `pe_iv` · `atm_iv` · `parity_gap` · `spread_vs_front` · `fwd_vol_from_prev` · `is_back` bool · `term_slope` · `front_is_0dte` bool.

**(c)** `samples_09_12.out:27-32` — **2 legs per symbol** (the stage-1 W1+W2 capture depth):

| symbol | leg | expiry | dte | atm_iv | parity_gap | spread | fwd_vol | slope |
|---|---|---|---|---|---|---|---|---|
| NIFTY | 1 | 09-29 | 4 | 9.8407 | 2.5426 | 0.0000 | — | 0.5017 |
| NIFTY | 2 | 10-06 | 11 | 10.3424 | −1.0322 | 0.5017 | 10.6184 | 0.5017 |
| SENSEX | 1 | 10-01 | 6 | 11.4299 | 2.1755 | 0.0000 | — | −0.1373 |
| SENSEX | 2 | 10-08 | 13 | 11.2926 | 0.8975 | −0.1373 | 11.1736 | −0.1373 |

NIFTY in contango (+0.50), SENSEX in backwardation (−0.14).

**(d)** `is_back` observed `false` (2), `true` (2). `front_is_0dte` observed `false` (4); **`true` unobserved** — reachable on any expiry day. No text status column (`emittable_literals.out:8` is empty).

**(e)** RLS off; anon `SELECT` only (`acl.out:14`).

> **Two legs is the whole term structure available.** Capture depth shipped at stage 1 (W1+W2); depth 4 remains gated, and ADR-025 Amendment B3 records that the gate *cannot currently be read* because the telemetry it depends on counts an event that has never occurred. **A renderer must not draw a term-structure curve** — it has two points, and `fwd_vol_from_prev` is defined only on leg 2.

---

### 12. `v_iv_surface` — view · **L10**

**(f)** `sql/2026-09-25_s83_v_iv_surface.sql:77` · **ENH-132**.

**(b)** *"a strike by expiry mesh of implied volatility at the LATEST `option_chain_snapshots` ts per symbol, with a companion SKEW per leg. Grain (symbol, ts, expiry_date, strike). Consumers MUST ORDER BY symbol, leg, strike."* — live COMMENT, 4 709 chars (`comments.out:12`).

**(a)** `symbol` · `ts` · `expiry_date` · `leg` bigint · `dte` int · `spot` · `strike` · `moneyness_pct` · `side_used` text · `ce_iv` · `pe_iv` · `iv` · `parity_gap` · `oi_otm` · `iv_over_atm` · `quote_state` text · `leg_atm_strike` · `leg_atm_iv` · `leg_k98` · `leg_skew_98` · `leg_status` text.

**(c)** `samples_09_12.out:37-44` — 3 nearest-ATM per symbol. NIFTY ATM 23 150, `leg_atm_iv` 9.8407, `leg_k98` 22 700, `leg_skew_98` 1.9986. SENSEX ATM 73 900, `leg_atm_iv` 11.4299, `leg_k98` 72 400, `leg_skew_98` 1.3955.

**(d)** `quote_state` observed `OTM_QUOTED` (861), `OTM_ABSENT` (7). `leg_status` observed `OK` (868); **`SKIPPED_EXPIRY` unobserved** — emitted when `dte = 0` (`v_iv_surface.sql:187`), reachable every expiry day. `side_used` observed `CE` (497), `PE` (371) — complete set.

**(e)** RLS off; anon `SELECT` only (`acl.out:15`).

> `leg_skew_98` is a **server-side** skew the front end does not read; it computes its own from ATM CE/PE instead. See Part 2. Note also that the OTM publication convention is what keeps the P3 / TD-S83-NEW-5 stale-`ltp` rows off this surface — a property of the convention, not a fix.

---

### 13. `v_gex_max_pain` — view · **L19 (parked, off-spec)**

**(f)** `sql/2026-09-22_s80_v_gex_max_pain.sql:54` · **ENH-123**.

**(b)** **No COMMENT live** (`comments.out:13`), though the file ships one at `:125`. Grain from the body and data: `(symbol, run_id, expiry_date, candidate_strike)` — one row per candidate strike, **sourced from `gex_strike_snapshots`**.

**(a)** `symbol` · `run_id` · `ts` · `expiry_date` · `dte` · `candidate_strike` · `total_pain` · `max_pain_strike` · `max_pain_value` · `side` text · `n_strikes` bigint · `call_oi_coverage_pct` · `put_oi_coverage_pct` · `snapshot_age_min` · `stale_floor_min_used` · `is_fresh` bool.

**(c)** `samples_13_17.out:3-10` — 3 lowest-pain candidates per symbol. NIFTY max pain **23 250** (pain 40 137 719 250), 138 strikes, coverage 89.1 / 87.7 %. SENSEX max pain **71 200** (16 400 124 000), 137 strikes, coverage 79.6 / 78.1 %.

**(d)** `side` observed `MAX_PAIN` (2), `CE_SIDE` (188), `PE_SIDE` (85) — complete set (`emittable_literals.out:10`). `is_fresh` observed `false` only (275).

**(e)** RLS off; anon **`MAINTAIN` + `SELECT`** (`acl.out:16`).

> **Finding (P4) — a non-SELECT privilege on anon.** See §17 note. Also the second instance of the §6 COMMENT gap (`comment_grant_in_file.out`).

---

### 14. `v_gex_pin_maxpain` — view · **L19 (parked, off-spec)**

**(f)** `sql/2026-09-22_s80_v_gex_pin_maxpain.sql:72` · **ENH-124**.

**(b)** **No COMMENT live** (`comments.out:14`); file ships one at `:137`. Grain `(symbol)` — one row per symbol, joining §3 pin zone, §13 max pain and §5 walls (`v_gex_pin_maxpain.sql:63`).

**(a)** 30 columns — `symbol` · `run_id` · `ts` · `expiry_date` · `dte` · `spot` · `sigma` · `atm_iv_used` · `max_pain_strike` · `peak_pin_strike` · `pin_lower` · `pin_upper` · `strike_step` · `gap_points` · `gap_strikes` · `gap_sigma` · `max_pain_spot_sigma` · `peak_pin_spot_sigma` · `max_pain_in_pin_band` bool · `max_pain_in_corridor` bool · `corridor_state` text · `corridor_width_sigma` · `pin_n_strikes` bigint · `tau_used` · `chain_n_strikes` bigint · `call_oi_coverage_pct` · `put_oi_coverage_pct` · `sigma_overstated_expiry_day` bool · `snapshot_age_min` · `is_fresh` bool.

**(c)** `samples_13_17.out:14-17`:

| symbol | max pain | peak pin | gap pts | gap strikes | gap σ | in band | in corridor |
|---|---|---|---|---|---|---|---|
| NIFTY | 23 250 | 23 400 | −150 | −3 | −0.523 | **false** | **true** |
| SENSEX | 71 200 | 71 400 | −200 | −2 | −0.151 | **true** | **false** |

**The two booleans disagree in opposite directions on the two symbols** — a renderer must not collapse them into one "aligned" indicator.

**(d)** `corridor_state` observed `INSIDE` (2); the other three of §5's vocabulary unobserved. `sigma_overstated_expiry_day` observed `false`; `true` reachable at 0 DTE (it carries TD-S79-NEW-1 in the row). `max_pain_in_pin_band` / `max_pain_in_corridor` both observed `true` and `false`.

**(e)** RLS off; anon **`MAINTAIN` + `SELECT`** (`acl.out:17`).

> S80 measured the pin↔max-pain gap as a **stable −0.4σ** over 11 795 runs, never changing sign. Today: −0.523σ and −0.151σ. **Whether it predicts anything is UNANSWERED by design** (ADR-025 Amendment A); a renderer must not imply otherwise.

---

### 15. `v_max_pain_by_strike` — view

**(f)** `sql/2026-09-22_s81_v_max_pain_by_strike_latest_ts_retrofit.sql:121` · **ENH-128** (retroactive registration, S81). Two superseded bodies exist in `sql/`; **the retrofit file is current** — a rebuild from either of the others reintroduces a measured ~4-week clock to the PostgREST ceiling.

**(b)** *"max pain per candidate strike, scoped to the LATEST snapshot and its FRONT expiry. Grain (symbol, expiry_date, candidate_strike). THE EXPIRY FILTER IS THE FIX: the S40 baseline grouped by (symbol, strike) with no expiry in the grain, so a snapshot carrying two expiries collapsed into a per-strike max() MIXTURE of two different contracts."* — live COMMENT, 5 062 chars (`comments.out:15`).

**(a)** `symbol` · `candidate_strike` · `total_pain` · `max_pain_strike` · `side` text · `ts` · `expiry_date` · `dte` · `n_strikes` bigint · `snapshot_age_min` · `stale_floor_min_used` · `is_fresh` bool.

**(c)** `samples_13_17.out:21-28`. NIFTY max pain **23 250**, pain 38 139 112 250, **269 strikes**, ts **10:10:04**. SENSEX **71 200**, 15 036 832 000, **186 strikes**, ts 10:10:04.

**(d)** `side` observed `MAX_PAIN` (2), `CE_SIDE` (287), `PE_SIDE` (166) — complete set. `is_fresh` `false` only.

**(e)** RLS off; anon `SELECT` only (`acl.out:18`).

> **Finding (P5) — two max pains, and they are not interchangeable.** §13 and §15 both compute max pain and **agree on the strike** (23 250 / 71 200) while disagreeing on everything else: **138 vs 269 strikes** (NIFTY), **40.14bn vs 38.14bn** total pain, **09:50 vs 10:10** ts. They read different substrates — §13 the GEX run, §15 the raw chain.
>
> The agreement on strike is **not** corroboration; it is two estimators over overlapping data landing on the same grid point today. **A renderer must pick one and name it**, and must never show both numbers as though one validates the other. Which is canonical is a decision, not a measurement.

---

### 16. `v_dealer_flow_sim` — view

**(f)** `sql/2026-05-25_enh81_v_dealer_flow_sim.sql:30` · **ENH-81**.

**(b)** *"dealer flow projection at ±0.5%, ±1%, ±2% scenarios for latest run_id per symbol. First-order approximation per ADR-014 §2.3 sign convention."* — live COMMENT, 153 chars (`comments.out:16`). Grain `(run_id, scenario)` — six rows per symbol.

**(a)** `run_id` · `symbol` · `expiry_date` · `ts` · `scenario` text · `spot_pct` · `perturbed_spot` · `net_gex` · `flow_cr` · `direction` text · `crosses_flip` bool.

**(c)** `samples_13_17.out:33-46` — 6 rows/symbol. NIFTY (short γ): BUY on all three down scenarios, SELL on all three up, `crosses_flip` **true** on all three up. SENSEX (long γ): the mirror, `crosses_flip` false throughout.

**(d)** `direction` observed `BUY` (6), `SELL` (6) — complete set. `scenario` all six observed. `crosses_flip` `false` (9), `true` (3).

**(e)** RLS off; anon `SELECT` only (`acl.out:19`).

> `flow_cr` is **exactly linear** in `spot_pct` (NIFTY: 6 890.85 / 13 781.69 / 27 563.39 for 0.5/1/2 %) because `net_gex` is held constant across scenarios — visible in the sample, where all six rows carry the identical `net_gex`. **It is a first-order restatement of net gamma, not a simulation**; three scenarios per side convey no more than one. A renderer should present it as a slope, not a grid of six independent outcomes.

---

### 17. `v_participant_oi_latest` — view

**(f)** `sql/2026-07-02_enh115_participant_positioning.sql:58` · **ENH-115**.

**(b)** *"Freshness read for the ADR-018 recency guard: newest participant row per exchange. Consumers (ENH-116 Lens 3) compare trade_date to the trading calendar and flag, never silently tilt on a stale board."* — file `:55-57` (no live COMMENT, `comments.out:17`). Grain `(exchange)` via `DISTINCT ON`.

**(a)** Three columns only: `exchange` text · `trade_date` date · `created_at` timestamptz.

**(c)** `samples_13_17.out:51-53` — **one row total**: `NSE | 2026-09-24 | 2026-09-24 14:00:05`. No BSE row; consistent with participant-wise OI being NSE(NSCCL)-only.

**(d)** `exchange` observed `NSE` only. The base table's CHECK admits `BSE` — structurally emittable, and **it will not appear**, because no BSE participant-OI report exists.

**(e)** RLS off; anon **`MAINTAIN` + `SELECT`** (`acl.out:20`).

> **This view carries no OI.** It is a freshness probe — date and nothing else. **A renderer cannot build a participant tilt from it**; that requires `participant_oi_daily`, which is outside this contract's eighteen. Its one value to a renderer is the staleness badge: today's row is dated **09-24**, one session back.

---

### 18. `merdian_parameters` — table · **merdian_ro-blind**

**(f)** `sql/2026-05-26_enh83_merdian_parameters.sql:22` · **ENH-83** (ADR-016).

**(b)** *"Temporal-immutable parameter store per ADR-016. Append-only writes; the active row per key is the one with valid_to IS NULL."* — live COMMENT, 186 chars (`comments.out:18`).

**(a)** `id` uuid · `key` text · `value_text` · `value_num` numeric · `value_bool` bool · `value_jsonb` jsonb · `value_type` text · `category` text · `description` text · `min_value` · `max_value` · `valid_from` · `valid_to` · `changed_by` text · `change_reason` text · `created_at`.

**(c)** **merdian_ro-blind (TD-S81-NEW-16) — sample owed from the editor.** The bounded probe returned **0** (`rls_blindness.out:5`) against 1 for every other probed relation. RLS is on and no policy admits `merdian_ro`. **This is not "empty"** — the front end reads this table successfully through `anon`, so rows exist.

**(d)** `value_type` and `category` domains: **owed**, same reason.

**Keys — owed, with two file-derived lower bounds** (neither is the live set):
- Seeded in `sql/2026-05-26_enh83_merdian_parameters.sql`: `capital.default_inr`, `capital.kelly_multiplier`, `capital.max_position_inr`, `ict.zone.dwm_breach_only`, `ict.zone.h_valid_days`, `retest.tolerance_pct`, `sl.buffer_pct` (`param_keys_from_file.out`).
- Referenced by the views above via `get_parameter_num`: `pin.tau.<symbol>`, `accel.tau.<symbol>`, `wall.band.<symbol>`, `wall.iv_floor_min`, `maxpain.stale_floor_min`, `rotation.stale_floor_min` (`param_keys_referenced.out`).

The union is **at least 13 keys** and the live count is unverified. CLAUDE.md records 11 active rows at S39, which is already inconsistent with this union — another reason to measure rather than assume.

**(e)** RLS **on**; anon `SELECT` only (`acl.out:21`).

---

## Part 2 — the front end

### 2.1 Which tree is live

Two clones of `balannavin-cyber1/meridian-connect` exist on this host. **`/home/ssm-user/meridian-connect` is the live source**, established by byte identity, not by mtime:

```
56ad2b217bf2a4d392fc28ceea0b16f1  /var/www/marketview/assets/index-DLdbWkEE.js
56ad2b217bf2a4d392fc28ceea0b16f1  /home/ssm-user/meridian-connect/dist/assets/index-DLdbWkEE.js
```

`/home/ssm-user/merdian-marketview` is a **stale May clone** (HEAD `14b63f3`, `queries.ts` 389 lines, dist filename `index-Dlk1UqD3.js` which is not what is served). The live HEAD is `a408fb4 "Fixed IV smile expiry collision"` — the commit the brief's collision class refers to.

> **Finding (P6).** The brief pointed at the stale tree first. Reading `merdian-marketview/src/lib/queries.ts` would have produced a contract against 389 lines of superseded code. Two clones of one repo, one live, distinguishable only by hashing the built bundle.

### 2.2 `src/lib/queries.ts`

**Reproduced verbatim as Appendix A**, because the design pass cannot see `meridian-connect` — it is not in project knowledge. `src/marketview/state.ts` and the cited `sections.tsx` ranges are **Appendix B**. Both were copied from disk, not transcribed, and checked for the parity target's product name: **0 occurrences in all three files.**

**Every exported query, its object, and its columns:**

| # | hook | object | columns read | order / filter |
|---|---|---|---|---|
| 1 | `useSpotMarker` | `market_spot_session_markers` | `*` | `symbol`, `trade_date_ist` desc, limit 1 |
| 2 | `useGammaLatest` | `gamma_metrics` | `*` | `symbol`, `ts` desc, limit 1 |
| 3 | `useGammaSeries` | `gamma_metrics` | `ts, spot, straddle_atm` | `symbol`, `ts` desc, limit 60 |
| 4 | `useStraddleIntraday` | `gamma_metrics` | `ts, straddle_atm` | `symbol`, `ts >= now−8d` asc |
| 5 | `useLatestSignal` | `signal_snapshots` | `*` | `symbol`, `entry_quality ∉ {SKIP, NO_TRADE}`, limit 1 |
| 6 | `useTodaysSignals` | `signal_snapshots` | `ts, action, atm_strike, spot, entry_quality, trade_allowed` | `symbol`, today, limit 20 |
| 7 | `useGexStrikes` | `gex_strike_snapshots` | `run_id, ts` then `strike, gex_cr, oi_call, oi_put, spot` | latest run by `(symbol, expiry)`, fallback `symbol` |
| 8 | `usePinZone` | `v_gex_strike_pin_zone` | `*` | `symbol`, `expiry_date`, `ts` desc, limit 1 |
| 9 | `useAccelZone` | `v_gex_strike_accel_zone` | `*` | `symbol`, `expiry_date`, `ts` desc, limit 1 |
| 10 | `useIctZones` | `ict_zones` | `*` | `symbol`, `detected_at_ts` desc, limit 40 |
| 11 | `useDealerFlow` | `v_dealer_flow_sim` | `run_id, ts` then `*` | latest run, `spot_pct` asc |
| 12 | `useAmbient` | `market_environment_snapshots` | `*` | `symbol`, `as_of_date` desc, limit 1 |
| 13 | `useExpiryBaseRates` | `v_expiry_base_rates` | `*` | `ambient_regime`, `lens_alignment` |
| 14 | `useExpiryOutcomes` | `expiry_outcomes` | `*` | `symbol`, `expiry_date` desc, limit 20 |
| 15 | `useGammaToday` | `gamma_metrics` | `ts, spot, pin_risk_score, straddle_atm, expansion_probability, net_gex` | `symbol`, `ts >= 03:45 UTC` asc |
| 16 | `useIvSmile` | **`option_chain_snapshots`** | `ts, expiry_date, strike, option_type, iv` | `symbol`, `strike ∈ [atm±5·step]`, `ts` desc, limit 2000 |
| 17 | `useMaxPainByStrike` | `v_max_pain_by_strike` | `candidate_strike, total_pain, max_pain_strike, side` | `symbol`, `candidate_strike` asc |
| 18 | `useBreadthIntraday` | `market_breadth_intraday` | `*` | `ts` desc, limit 1 |
| 19 | `useWcbLatest` | `weighted_constituent_breadth_snapshots` | `ts, wcb_score, wcb_regime, weighted_advances_pct, weighted_pct_above_10dma, weighted_pct_above_20dma, weighted_pct_above_40dma, active_weight_pct` | `index_symbol`, `ts` desc, limit 1 |
| 20 | `useAmbientSeries` | `market_environment_snapshots` | 16 named columns | `symbol`, `as_of_date` asc, limit 40 |
| 21 | `useParameters` | `merdian_parameters` | `*` | `valid_to IS NULL`, by `category`, `key` |
| 22 | `useParameterAudit` | `v_merdian_parameter_audit` | `*` | `created_at` desc, limit 50 |
| — | `updateParameter` | RPC `update_parameter` | — | write path, ADR-016 contract |

### 2.3 Column-existence check — **zero missing**

Every column named above was checked against `information_schema.columns`: **38 of 38 resolve, 0 missing** (`frontend_cols.out`, 38 rows, `grep -c MISSING` = 0).

> **The `useIvSmile` expiry-collision class is a value-level bug, not a column-name bug**, and it is fixed. `useIvSmile` reads the raw chain and does its own front-expiry selection client-side (Appendix A, `queries.ts:416-425`): take `maxTs`, then the lexicographically smallest `expiry_date` among rows at that ts. Before `a408fb4` it did not, and a snapshot carrying two expiries blended two contracts into one smile — the same defect class the §15 COMMENT records for `v_max_pain_by_strike`'s S40 baseline. **No column-name instances of the class remain.**

### 2.4 Positioning page components

`src/pages/Positioning.tsx` is 23 lines and composes six sections, all from `src/marketview/sections.tsx`, all fed by one hook `useMvData(symbol)` in `src/marketview/state.ts`:

| # | component | file | reads (via `useMvData`) |
|---|---|---|---|
| 1 | `SnapshotStrip` | `sections.tsx:28` | `gamma_metrics` (net_gex, pin_risk_score, vix, dte), `gex_strike_snapshots` (derived max γ), `v_max_pain_by_strike`, `market_spot_session_markers` |
| 2 | `KeyParametersSection` | `sections.tsx:62` | `gamma_metrics` (regime, gamma_zone, net_gex, flip_level, flip_distance_pct), `v_gex_strike_pin_zone`, `v_gex_strike_accel_zone`, derived Σdampen/Σamplify |
| 3 | `PositioningSection` | `sections.tsx:101` | `gex_strike_snapshots` (hero chart bars), pin + accel zones, flip level |
| 4 | `NetDealerGammaSection` | `sections.tsx:130` | `gamma_metrics` today series (`ts, net_gex`) |
| 5 | `PinRiskRowSection` | `sections.tsx:206` | `gamma_metrics` (pin_risk_score, expansion_probability, straddle_atm) + straddle buckets |
| 6 | `PinRiskTimelineSection` | `sections.tsx:276` | `gamma_metrics` today series (pin_risk_score, spot) |

Page-level: `PageTitle` (`marketview/ui.tsx`), `HeroChart` / `Gauge` / `StraddleIntradayChart` / `PinRiskTimeline` primitives (`components/primitives/`).

### 2.5 The finding that matters most

**The Positioning page reads four objects of the eighteen** — `gamma_metrics`, `gex_strike_snapshots`, `v_gex_strike_pin_zone`, `v_dealer_flow_sim` (plus `v_gex_strike_accel_zone` and `v_max_pain_by_strike`, outside Positioning). **Twelve of the eighteen have no consumer anywhere in the front end:**

`v_gex_repriced_flip` · `v_gex_strike_walls` · `v_gex_abs_exposure` · `v_gex_concentration` · `v_gex_strike_rank` · `v_oi_rotation_since_open` · `v_gex_net_gamma_river` · `v_iv_term_structure` · `v_iv_surface` · `v_gex_max_pain` · `v_gex_pin_maxpain` · `v_participant_oi_latest`

This is **ADR-025 D2 clause 3 measured from the consumer side**, and it corroborates BUILT = 2 of 14 independently of the register.

**Worse: the front end recomputes, client-side, quantities these views already expose** —

| front-end derivation | `state.ts` | server-side equivalent it does not read |
|---|---|---|
| `maxGammaStrike` = argmax of positive `gex_cr` | `:56-58` | `gamma_metrics.max_gamma_strike`; `v_gex_strike_rank` rank 1 |
| `strongestAmplifyStrike` = argmin | `:57-59` | `v_gex_strike_rank` (side = AMPLIFYING) |
| `dampenTotal` / `amplifyTotal` | `:60-61` | `v_gex_abs_exposure.abs_gex_cr` / `net_gex_cr` |
| `ivSkewPct` = (atmPe/atmCe − 1)·100 | `:73-74` | `v_iv_surface.leg_skew_98` |
| `gammaPainGap` = \|maxγ − maxPain\| | `:94` | `v_gex_pin_maxpain.gap_points` / `gap_sigma` |

Each is a second implementation of a rule that already has a committed, commented, gated one. **ADR-024 Amendment A ruled that the max-positive-GEX strike is the "max net-long-gamma strike" and must never be labelled "near spot"; `SnapshotStrip` labels it `MAX γ` with a subtitle of its percentage distance from spot** (Appendix B, `sections.tsx:35-36`) — the presentation Amendment A exists to prevent.

---

## Part 3 — the gap list

Seven concepts the design brief names. Each was probed against **every column of every relation in `public`** by regex (`gap_probe.out`), not against the eighteen alone.

### 1. Canonical sigma-to-expiry — **NO CANONICAL FIELD; four definitions, two conventions**

Not absent — *unreconciled*. `gap_probe.out:2` finds four: `v_gex_strike_walls.sigma`, `v_gex_strike_rank.sigma`, `v_gex_pin_maxpain.sigma`, `v_gex_repriced_flip.sigma_1d`.

- **Walls** (`v_gex_strike_walls.sql:127`) and **rank** (`v_gex_strike_rank.sql:185`) are textually identical: `spot * atm_iv/100 * sqrt(GREATEST(dte,1)/252.0)` — **252 trading-day year, horizon = to expiry**.
- **pin_maxpain** does not compute one; it inherits `w.sigma` from walls (`v_gex_pin_maxpain.sql:105`). Same definition.
- **repriced_flip** computes `spot * atm_iv/100 * sqrt(1.0/365.0)` (`:251-252`) — **365 calendar-day year, horizon = one day**. A different quantity under a near-identical name.

Three consequences: the to-expiry definition is **duplicated in two files** rather than sourced once, so they can drift silently; `GREATEST(dte,1)` **overstates sigma at 0 DTE**, self-flagged by `v_gex_pin_maxpain.sigma_overstated_expiry_day` (TD-S79-NEW-1); and **none of the four is in `gamma_metrics`**, the only GEX object the front end reads.

**So the front end fabricates one.** `state.ts:44` sets `sigmaPct = gamma_metrics.flip_distance_pct` — the distance from spot to the flip level — and renders it as `±X%` under the label **"Spot Context"** with a subtitle `σ <lo>–<hi>` (Appendix B, `sections.tsx:83-84`), and as **"Σ to expiry"** and **"σ-band to expiry"** on the hero chart (`sections.tsx:121`, `:105`). **Flip distance is not a volatility sigma.** This is the gap's operative cost: a renderer, denied the real quantity, invented a plausible-looking one and labelled it with the real one's name — **finding P7**.

### 2. Gamma ceiling / floor — **STATES EXIST, LEVELS DO NOT**

`gap_probe.out:5` returns only freshness floors (`stale_floor_min_used`, `iv_floor_min_used`) — unrelated. **No column named for a gamma ceiling or floor exists in any relation.**

But `v_gex_strike_walls.corridor_state` **emits `ABOVE_CEILING` and `BELOW_FLOOR`** (`emittable_literals.out:3`). So the system classifies spot against a ceiling and a floor it never names as fields. The nearest available levels are `call_wall` / `put_wall`, which the COMMENT explicitly says "exist for labelling only", with `put_wall_sigma` / `call_wall_sigma` as the real measures. A renderer wanting explicit ceiling/floor levels must either adopt the walls as such — a decision, not a read — or wait for a field. **Neither state has ever been observed** (§5(d)).

### 3. Neutral regime band — **DOES NOT EXIST, AND CANNOT**

`gap_probe.out:6`: **no column anywhere** matches neutral/regime-band. Confirmed at the writer: `determine_regime` is a hard sign test at `net_gex >= 0` with no dead zone (`determine_regime.out`). A net GEX of +1 Cr and one of +7 266 392 Cr both return `LONG_GAMMA`; today NIFTY sits at −1.38M and SENSEX at +7.27M, and the regime label alone distinguishes them not at all from a marginal case. **A renderer cannot show a neutral band because no threshold exists to show.** Introducing one is a writer change and an ADR, not a query.

### 4. True HHI — **NOT PRESENT; the columns are dominance ratios**

`gap_probe.out:8` finds `hhi_net`, `hhi_call`, `hhi_put`. **None is a Herfindahl index.** The view's own COMMENT says so — *"Herfindahl max/sum"* — and the data proves it: `hhi_net` = **0.14425758917096207626** is byte-identical to rank-1 `share_of_abs` in `v_gex_strike_rank` (`samples_05_08.out:19` vs `:29`). That is max/sum, not Σ(shareᵢ²).

The two answer different questions. Max/sum says *how large is the biggest strike*; Σ(share²) says *how concentrated is the whole book*. A book with one 14 % strike and 112 tiny ones, and a book with seven 14 % strikes, score **identically** on max/sum and far apart on a true HHI. SENSEX's top three strikes are within 0.03 % of each other — exactly the shape max/sum cannot see. **The name asserts a statistic the column does not compute**, and a renderer labelling it "HHI" would publish that error. Σ(share²) is derivable from `v_gex_strike_rank.share_of_abs` in the read layer.

### 5. Conviction / margin — **NOT PRESENT IN THE GEX LAYER**

`gap_probe.out:4` returns hits only in unrelated relations — `eq_paper_trades.conviction_score`, `eq_watchlist.conviction_score`, `signal_state_snapshots.composite_conviction`, `dhan_scripmaster.*MARGIN*`. **No conviction or margin column exists in any of the eighteen**, though `v_gex_strike_rank`'s COMMENT calls it *"L12 pin conviction"*.

The available proxies are `share_of_abs`, `cum_share_of_abs` and the rank order. The margin between rank 1 and rank 2 — the natural conviction measure — is **not a column**; it is derivable. On today's data it is decisive for NIFTY (0.1443 vs 0.1156, a 25 % relative gap) and **near-zero for SENSEX** (0.12455 vs 0.12434, 0.17 %). **A renderer showing a "top strike" without that margin implies a confidence the SENSEX data does not support.**

### 6. Previous-close ΔOI — **RELATION EXISTS; NOT WIRED, AND HISTORICALLY UNMEASURABLE**

`gap_probe.out:7` finds exactly one: `v_oi_prev_close_snapshots.prev_close_oi`, from `sql/2026-05-25_v_oi_prev_close_snapshots.sql` — shipped at S37 as *"a scaffold for future writer integration"* and never integrated.

**A bounded probe returned 1 row** (`prev_close_probe.out`), so the relation is not wholly unreadable. That refines rather than contradicts S78, whose exclusion was specific: the relation could not prove a window **empty** without scanning its whole extent, timing out at ~8.3 s per empty day. **A `LIMIT 1` on a populated window is the cheap case; the S78 exclusion stands for the case it was about.**

Meanwhile L13 (§9) measures rotation **since the session open**, not since the previous close — a different quantity that omits the overnight move entirely, which on a gap day is where the rotation is. **The two are not substitutes**, and the previous-close leg is unbuilt.

### 7. L7 (vanna) and L8 (charm) — **ABSENT ENTIRELY; gated on one pre-registered test**

`gap_probe.out:3` and `:9`: **`*** NO COLUMN ANYWHERE ***`** for both, across every relation in `public`. No table, no view, no scaffold.

**What they need is smaller than it looks.** Per-strike vanna and charm are Black-Scholes second-order Greeks on each strike of the **front chain**: they need that strike's IV, the spot, `r` and `T`, all of which `option_chain_snapshots` and the ENH-131 repricer already supply. **They do not need a term structure, and they are not blocked on capture depth** — the two-leg limit at §11 constrains L9, not L7/L8.

**Status.** ADR-025 Amendment B4 moved both from BLOCKED-ON-DECISION to **PENDING**, the ENH-98 deferral lifted. The go/no-go is **no longer inconclusive**: S84 reproduced the S82 record at **12/12 MATCH** (arm A0, `docs/research/capture_s84.md` §2.3) and added a new point **A1 at 2026-09-25 11:00:07 IST** (§2.4). What remains is a single pre-registered test:

> **T1 — the SOLE go/no-go.** Refuse if the `exact/365` `gamma_relerr` median exceeds **0.10 in BOTH ATM and NEAR**, evaluated at **SENSEX dte 1–2** — arms **A3 (Tue 2026-09-29, dte 2)** and **A4 (Wed 2026-09-30, dte 1)** (`capture_s84.md` §2.6).

On T1 PASS, a self-computed L7/L8 is proposed on the ENH-131 repricer (vendor IV, `r` = the L3 session-median futures carry, `T` = exact/365, `dte 0 → SKIPPED_EXPIRY`). **On T1 FAIL, no L7/L8 view is proposed, and the refusal is the result.**

**So the gap is real but narrow: the view is absent, and the build is gated on T1 alone.** That is a materially better position than the other six items, five of which are naming, wiring or derivation problems nobody has scheduled.

---

## 4. Summary — what a renderer can and cannot have

**Can render today, from data with a committed source and a single grain:** net GEX and regime (§1), per-strike gamma (§2), pin zone (§3), walls and corridor (§5), gross-vs-net exposure (§6), concentration (§7), the ranked strike ladder (§8), the 30-session river with its intraday band (§10), a two-point IV term comparison (§11), the IV surface and per-leg skew (§12), max pain (§13/§15, **after choosing one**), the pin↔max-pain gap (§14), the dealer-flow slope (§16).

**Cannot render, and the reason:**

| want | status |
|---|---|
| canonical σ-to-expiry | four definitions, two conventions, none in the table the UI reads (§3.1) |
| gamma ceiling / floor levels | states emit, levels are unnamed (§3.2) |
| neutral regime band | no threshold exists in the writer (§3.3) |
| true HHI | columns are max/sum; derivable, not stored (§3.4) |
| conviction / margin | not a column; derivable from rank shares (§3.5) |
| previous-close ΔOI | scaffold only, unwired; L13 measures since-open instead (§3.6) |
| vanna / charm | absent; build gated on T1 at SENSEX dte 1–2, 09-29/09-30 (§3.7) |
| participant tilt | §17 carries a date and no OI |
| L13 on SENSEX | anchor demonstrably fabricated today (§9) |

**Two hard constraints on any rendering pass:**

1. **Never place a GEX-family value beside a chain-family value without both timestamps.** They differed by 20 minutes today.
2. **Every state vocabulary has unobserved-but-reachable values.** `corridor_state` has shown 1 of 4; `status` on §4 has shown 2 of 4; `leg_status` 1 of 2; `presence` 1 of 3; `dte_bucket` 1 of 3. **Styling against today's data alone will produce undefined rendering on an ordinary future session** — most of these appear on expiry days.

---

## 5. Proposed TDs (not filed; numbers assigned at filing)

**Nothing in this document was filed.** `TD-S84-NEW-1` is already taken — it was filed in `tech_debt.md` by the parallel S84 window, for the `merdian_ro` grant missing from two of three S83 `sql/` files — so these carry provisional labels **P1–P7** and take their numbers at filing time, from whatever the register's next free value then is.

| ref | sev | item |
|---|---|---|
| **P1** | S2 | `gamma_metrics` has **no `CREATE TABLE` in `sql/`** — ADR-025 D2 clause 4 gap on the most-read table in the set (§1) |
| **P2** | S2 | **Three views ship a `COMMENT ON VIEW` in `sql/` that never ran live** — `v_gex_abs_exposure` (:145), `v_gex_max_pain` (:125), `v_gex_pin_maxpain` (:137). `v_gex_abs_exposure` additionally has its `GRANT` **commented out** (:156-157) while anon holds SELECT live, so a rebuild from it yields an anon-unreadable view. **TD-S81-NEW-5 is not remediated** (§6, §13, §14) |
| **P3** | **S2** | **L13 anchor fabricated, and TD-S83-NEW-5 contradicted.** SENSEX 72300 CE Δ = −48 767 480 from a stale anchor; `oi`/`ltp`/`iv` all correct together at 04:15–04:20 UTC, `iv` 121.04 → 14.89. The S83 claim that this OI "is real" and that the ~8× ATM `iv` is a vendor property is contradicted on 2 strikes / 1 session — both are one stale `ltp`. **Cross-ref TD-S83-NEW-5; §D candidate.** S2 not S1: display-only, no gate reads L13 (§9) |
| **P4** | S3 | **anon holds `MAINTAIN` beyond SELECT** on `v_gex_max_pain`, `v_gex_pin_maxpain`, `v_participant_oi_latest` — objects created before the S81 `ALTER DEFAULT PRIVILEGES` fix. S81 fixed the mechanism going forward and did not sweep existing objects (§13, §14, §17) |
| **P5** | S2 | **Two max pains** (§13 GEX-run / §15 chain) agreeing on strike and disagreeing on strike count, total, and ts. Which is canonical is undecided (§15) |
| **P6** | S3 | **Two clones of `meridian-connect`**, one live, distinguishable only by hashing the served bundle. The stale one is 4 months old and would have produced a wrong contract (§2.1) |
| **P7** | S2 | **UI labels `flip_distance_pct` as σ** — "Spot Context ±X%", "σ-band to expiry", "Σ to expiry". Consequence of §3.1 |
| TD-S83-NEW-7 | — | **confirmed, still open.** CLAUDE.md's ADR-015 bullet names `oi_total_calls`/`oi_total_puts`; live columns are `oi_call`/`oi_put` (§2) |

## 6. Owed

1. **`merdian_parameters` sample, key list, and `value_type`/`category` domains** — merdian_ro-blind (TD-S81-NEW-16); owed from the Supabase editor. File-derived lower bound is 13 keys; CLAUDE.md says 11 active at S39. Neither is verified.
2. **`v_gex_repriced_flip` `pos->neg`, `SKIPPED_EXPIRY`, `UNMEASURABLE_R`**; `corridor_state` `ABOVE_CEILING`/`BELOW_FLOOR`/`UNDEFINED`; `leg_status` `SKIPPED_EXPIRY`; `presence` `ANCHOR_ONLY`/`LATEST_ONLY`; `dte_bucket` `0`/`1-2`; `front_is_0dte` true — **all reachable, none observed.** An expiry-day capture would observe most of them in one session.
3. **Intraday freshness behaviour** — every `is_fresh` here reads post-close.
4. **Whether §9's stale anchor recurs on roll-adjacent sessions**, and whether 72100/72200 CE and the two NIFTY put exceptions in TD-S83-NEW-5 share the cause — two strikes, one session measured.

---

*Method note. Six of this document's claims began as inferences and were changed by measurement before being written: `v_participant_oi_latest` appeared to have no `sql/` source (a case-sensitive grep missed lowercase DDL); `merdian-marketview` appeared to be the live tree (mtime said one thing, the bundle hash another); `v_oi_prev_close_snapshots` was expected to be unreadable and returns a row under a bounded probe; the sigma gap was expected to be an absence and is a reconciliation failure; the expiry-collision class was expected to yield missing column names and yields none; and the `count(*)` probe that would have scanned `option_chain_snapshots` was replaced with a bounded one before it ran. A seventh was corrected after review: §3.7 originally asserted that vanna and charm were blocked behind capture depth and required a term structure, and that their go/no-go was inconclusive — all three were wrong, and the correct position is a single pre-registered test at §2.6 of the S84 capture.*

---

## Appendix A — `meridian-connect/src/lib/queries.ts`, verbatim

Copied from disk at `/home/ssm-user/meridian-connect/src/lib/queries.ts` (621 lines), HEAD `a408fb4`. Not transcribed. Line numbers in the body refer to this file.

```typescript
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "./supabase";

export type Symbol = "NIFTY" | "SENSEX";

const MV_STALE = 30_000;
const SETTINGS_STALE = 5 * 60_000;

// ---------- Marketview ----------

export function useSpotMarker(symbol: Symbol) {
  return useQuery({
    queryKey: ["spotMarker", symbol],
    staleTime: MV_STALE,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("market_spot_session_markers")
        .select("*")
        .eq("symbol", symbol)
        .order("trade_date_ist", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return data;
    },
  });
}

export function useGammaLatest(symbol: Symbol) {
  return useQuery({
    queryKey: ["gammaLatest", symbol],
    staleTime: MV_STALE,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("gamma_metrics")
        .select("*")
        .eq("symbol", symbol)
        .order("ts", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return data;
    },
  });
}

export function useGammaSeries(symbol: Symbol, limit = 60) {
  return useQuery({
    queryKey: ["gammaSeries", symbol, limit],
    staleTime: MV_STALE,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("gamma_metrics")
        .select("ts, spot, straddle_atm")
        .eq("symbol", symbol)
        .order("ts", { ascending: false })
        .limit(limit);
      if (error) throw error;
      return (data ?? []).slice().reverse();
    },
  });
}

// Intraday straddle: today's series + per-bucket 5-day average.
// Buckets are 5-minute intervals of IST minutes-of-day (e.g. 555 = 09:15).
export type StraddleBucket = { bucket: number; today: number | null; avg: number | null };
export function useStraddleIntraday(symbol: Symbol) {
  return useQuery({
    queryKey: ["straddleIntraday", symbol],
    staleTime: MV_STALE,
    queryFn: async (): Promise<{ buckets: StraddleBucket[]; daysUsed: number }> => {
      const since = new Date(Date.now() - 8 * 24 * 60 * 60 * 1000);
      const { data, error } = await supabase
        .from("gamma_metrics")
        .select("ts, straddle_atm")
        .eq("symbol", symbol)
        .gte("ts", since.toISOString())
        .order("ts", { ascending: true });
      if (error) throw error;
      const rows = (data ?? []).filter((r: any) => r.straddle_atm != null);

      const istParts = (iso: string) => {
        const t = new Date(iso).getTime() + 5.5 * 60 * 60 * 1000;
        const d = new Date(t);
        const dateKey = d.getUTCFullYear() * 10000 + (d.getUTCMonth() + 1) * 100 + d.getUTCDate();
        const minOfDay = d.getUTCHours() * 60 + d.getUTCMinutes();
        return { dateKey, minOfDay };
      };
      const todayKey = (() => {
        const t = Date.now() + 5.5 * 60 * 60 * 1000;
        const d = new Date(t);
        return d.getUTCFullYear() * 10000 + (d.getUTCMonth() + 1) * 100 + d.getUTCDate();
      })();

      const BUCKET = 5;
      const todayMap = new Map<number, number>();
      const histAgg = new Map<number, { sum: number; n: number; days: Set<number> }>();
      for (const r of rows as any[]) {
        const { dateKey, minOfDay } = istParts(r.ts);
        if (minOfDay < 555 || minOfDay > 930) continue;
        const bucket = Math.floor(minOfDay / BUCKET) * BUCKET;
        const v = Number(r.straddle_atm);
        if (dateKey === todayKey) {
          todayMap.set(bucket, v);
        } else {
          const a = histAgg.get(bucket) ?? { sum: 0, n: 0, days: new Set<number>() };
          a.sum += v;
          a.n += 1;
          a.days.add(dateKey);
          histAgg.set(bucket, a);
        }
      }

      const allBuckets = new Set<number>([...todayMap.keys(), ...histAgg.keys()]);
      const buckets: StraddleBucket[] = Array.from(allBuckets)
        .sort((a, b) => a - b)
        .map((bucket) => {
          const a = histAgg.get(bucket);
          return {
            bucket,
            today: todayMap.has(bucket) ? todayMap.get(bucket)! : null,
            avg: a && a.n > 0 ? a.sum / a.n : null,
          };
        });

      const daysUsed = new Set<number>();
      histAgg.forEach((a) => a.days.forEach((d) => daysUsed.add(d)));
      return { buckets, daysUsed: daysUsed.size };
    },
  });
}

export function useLatestSignal(symbol: Symbol) {
  return useQuery({
    queryKey: ["signalLatest", symbol],
    staleTime: MV_STALE,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("signal_snapshots")
        .select("*")
        .eq("symbol", symbol)
        .neq("entry_quality", "SKIP")
        .neq("entry_quality", "NO_TRADE")
        .order("ts", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return data;
    },
  });
}

export function useTodaysSignals(symbol: Symbol) {
  return useQuery({
    queryKey: ["signalsToday", symbol],
    staleTime: MV_STALE,
    queryFn: async () => {
      const since = new Date();
      since.setHours(0, 0, 0, 0);
      const { data, error } = await supabase
        .from("signal_snapshots")
        .select("ts, action, atm_strike, spot, entry_quality, trade_allowed")
        .eq("symbol", symbol)
        .gte("ts", since.toISOString())
        .order("ts", { ascending: false })
        .limit(20);
      if (error) throw error;
      return data ?? [];
    },
  });
}

export function useGexStrikes(symbol: Symbol, expiry: string | null | undefined) {
  return useQuery({
    queryKey: ["gexStrikes", symbol, expiry],
    staleTime: MV_STALE,
    queryFn: async () => {
      // Find the latest run for this symbol — try expiry filter first, then fall back to symbol-only.
      let latest: { run_id: string } | null = null;
      if (expiry) {
        const { data } = await supabase
          .from("gex_strike_snapshots")
          .select("run_id, ts")
          .eq("symbol", symbol)
          .eq("expiry_date", expiry)
          .order("ts", { ascending: false })
          .limit(1)
          .maybeSingle();
        latest = (data as any) ?? null;
      }
      if (!latest) {
        const { data } = await supabase
          .from("gex_strike_snapshots")
          .select("run_id, ts")
          .eq("symbol", symbol)
          .order("ts", { ascending: false })
          .limit(1)
          .maybeSingle();
        latest = (data as any) ?? null;
      }
      if (!latest) return [];
      const { data, error } = await supabase
        .from("gex_strike_snapshots")
        .select("strike, gex_cr, oi_call, oi_put, spot")
        .eq("run_id", latest.run_id)
        .order("strike", { ascending: true });
      if (error) throw error;
      return data ?? [];
    },
  });
}

export function usePinZone(symbol: Symbol, expiry: string | null | undefined) {
  return useQuery({
    queryKey: ["pinZone", symbol, expiry],
    enabled: !!expiry,
    staleTime: MV_STALE,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("v_gex_strike_pin_zone")
        .select("*")
        .eq("symbol", symbol)
        .eq("expiry_date", expiry!)
        .order("ts", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return data;
    },
  });
}

export function useAccelZone(symbol: Symbol, expiry: string | null | undefined) {
  return useQuery({
    queryKey: ["accelZone", symbol, expiry],
    enabled: !!expiry,
    staleTime: MV_STALE,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("v_gex_strike_accel_zone")
        .select("*")
        .eq("symbol", symbol)
        .eq("expiry_date", expiry!)
        .order("ts", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return data;
    },
  });
}

export function useIctZones(symbol: Symbol) {
  return useQuery({
    queryKey: ["ictZones", symbol],
    staleTime: MV_STALE,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("ict_zones")
        .select("*")
        .eq("symbol", symbol)
        .order("detected_at_ts", { ascending: false })
        .limit(40);
      if (error) throw error;
      return data ?? [];
    },
  });
}

export function useDealerFlow(symbol: Symbol, expiry: string | null | undefined) {
  return useQuery({
    queryKey: ["dealerFlow", symbol, expiry],
    enabled: !!expiry,
    staleTime: MV_STALE,
    queryFn: async () => {
      const { data: latest } = await supabase
        .from("v_dealer_flow_sim")
        .select("run_id, ts")
        .eq("symbol", symbol)
        .eq("expiry_date", expiry!)
        .order("ts", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (!latest) return [];
      const { data, error } = await supabase
        .from("v_dealer_flow_sim")
        .select("*")
        .eq("run_id", latest.run_id)
        .order("spot_pct", { ascending: true });
      if (error) throw error;
      return data ?? [];
    },
  });
}

export function useRefetchMarketview() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({
      predicate: (q) => {
        const k = q.queryKey[0];
        return [
          "spotMarker", "gammaLatest", "gammaSeries", "gammaToday",
          "signalLatest", "signalsToday", "gexStrikes", "pinZone", "accelZone",
          "ictZones", "dealerFlow", "straddleIntraday", "maxPainByStrike",
          "breadthIntraday", "wcbLatest", "ivSmile",
          "ambient", "expiryBaseRates", "expiryOutcomes",
        ].includes(k as string);
      },
    });
  };
}

// Latest ambient regime snapshot — ordered by as_of_date so backfills can't
// surface a stale row with a newer created_at than the true latest session.
export function useAmbient(symbol: Symbol) {
  return useQuery({
    queryKey: ["ambient", symbol],
    staleTime: MV_STALE,
    retry: false,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("market_environment_snapshots")
        .select("*")
        .eq("symbol", symbol)
        .order("as_of_date", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) return null;
      return data;
    },
  });
}

// Historical base rates for (ambient_regime, lens_alignment) pin/break outcomes
export function useExpiryBaseRates(ambientRegime: string | null | undefined, lensAlignment: string | null | undefined) {
  return useQuery({
    queryKey: ["expiryBaseRates", ambientRegime, lensAlignment],
    enabled: !!ambientRegime && !!lensAlignment,
    staleTime: 5 * 60_000,
    retry: false,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("v_expiry_base_rates")
        .select("*")
        .eq("ambient_regime", ambientRegime!)
        .eq("lens_alignment", lensAlignment!);
      if (error) return null;
      return data ?? [];
    },
  });
}

// Recent expiry outcomes (chronological journal)
export function useExpiryOutcomes(symbol: Symbol, limit = 20) {
  return useQuery({
    queryKey: ["expiryOutcomes", symbol, limit],
    staleTime: 5 * 60_000,
    retry: false,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("expiry_outcomes")
        .select("*")
        .eq("symbol", symbol)
        .order("expiry_date", { ascending: false })
        .limit(limit);
      if (error) return null;
      return data ?? [];
    },
  });
}


// Today's gamma_metrics rows (for Pin Risk Timeline + ATM straddle today series)
export function useGammaToday(symbol: Symbol) {
  return useQuery({
    queryKey: ["gammaToday", symbol],
    staleTime: MV_STALE,
    queryFn: async () => {
      const startIst = new Date();
      startIst.setUTCHours(3, 45, 0, 0); // 09:15 IST = 03:45 UTC
      const { data, error } = await supabase
        .from("gamma_metrics")
        .select("ts, spot, pin_risk_score, straddle_atm, expansion_probability, net_gex")
        .eq("symbol", symbol)
        .gte("ts", startIst.toISOString())
        .order("ts", { ascending: true });
      if (error) return [];
      return data ?? [];
    },
  });
}

// IV smile from option_chain_snapshots (long format: one row per (strike, option_type))
export function useIvSmile(symbol: Symbol, spot: number | null | undefined, step: number) {
  return useQuery({
    queryKey: ["ivSmile", symbol, spot, step],
    enabled: !!spot && spot > 0,
    staleTime: MV_STALE,
    retry: false,
    queryFn: async () => {
      const atm = Math.round((spot as number) / step) * step;
      const lo = atm - step * 5;
      const hi = atm + step * 5;
      const { data, error } = await supabase
        .from("option_chain_snapshots")
        .select("ts, expiry_date, strike, option_type, iv")
        .eq("symbol", symbol)
        .gte("strike", lo)
        .lte("strike", hi)
        .order("ts", { ascending: false })
        .limit(2000);
      if (error) return null;
      const rows = (data ?? []) as any[];
      if (!rows.length) return null;
      // Filter to most recent ts + front expiry only
      const maxTs = rows[0].ts;
      const maxTsRows = rows.filter((r) => r.ts === maxTs);
      const frontExpiry = maxTsRows
        .map((r) => r.expiry_date)
        .filter((d): d is string => !!d)
        .sort((a, b) => a.localeCompare(b))[0];
      const latest = frontExpiry
        ? maxTsRows.filter((r) => r.expiry_date === frontExpiry)
        : maxTsRows;
      // Average CE+PE IV per strike for the smile curve
      const byStrike = new Map<number, { ce: number | null; pe: number | null }>();
      for (const r of latest) {
        const entry = byStrike.get(r.strike) ?? { ce: null, pe: null };
        if (r.option_type === "CE") entry.ce = r.iv;
        else if (r.option_type === "PE") entry.pe = r.iv;
        byStrike.set(r.strike, entry);
      }
      const points: { strike: number; iv: number }[] = [];
      let atmCe: number | null = null;
      let atmPe: number | null = null;
      Array.from(byStrike.entries())
        .sort((a, b) => a[0] - b[0])
        .forEach(([strike, v]) => {
          const ivs = [v.ce, v.pe].filter((x): x is number => x != null && x > 0);
          if (ivs.length) points.push({ strike, iv: ivs.reduce((a, b) => a + b, 0) / ivs.length });
          if (strike === atm) {
            atmCe = v.ce && v.ce > 0 ? v.ce : null;
            atmPe = v.pe && v.pe > 0 ? v.pe : null;
          }
        });
      return { atm, points, atmCe: atmCe as number | null, atmPe: atmPe as number | null };
    },
  });
}

// Max pain (defensive: view may not exist yet)
export function useMaxPainByStrike(symbol: Symbol) {
  return useQuery({
    queryKey: ["maxPainByStrike", symbol],
    staleTime: 60_000,
    retry: false,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("v_max_pain_by_strike")
        .select("candidate_strike, total_pain, max_pain_strike, side")
        .eq("symbol", symbol)
        .order("candidate_strike", { ascending: true });
      if (error) return null;
      return data;
    },
  });
}

// Market breadth (defensive: table may not exist)
export function useBreadthIntraday(symbol: Symbol) {
  return useQuery({
    queryKey: ["breadthIntraday", symbol],
    staleTime: 60_000,
    retry: false,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("market_breadth_intraday")
        .select("*")
        .order("ts", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) return null;
      return data;
    },
  });
}

// Weighted Constituent Breadth (separate table; symbol column is index_symbol)
export function useWcbLatest(symbol: Symbol) {
  return useQuery({
    queryKey: ["wcbLatest", symbol],
    staleTime: MV_STALE,
    retry: false,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("weighted_constituent_breadth_snapshots")
        .select(
          "ts, wcb_score, wcb_regime, weighted_advances_pct, weighted_pct_above_10dma, weighted_pct_above_20dma, weighted_pct_above_40dma, active_weight_pct",
        )
        .eq("index_symbol", symbol)
        .order("ts", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) return null;
      return data;
    },
  });
}


// Settled ambient trajectory series (up to ~40 sessions) — read-only.
export type AmbientSeriesRow = {
  as_of_date: string;
  eod_spot: number | null;
  front_expiry: string | null;
  cycle_oi_call_put_asym: number | null;
  gex_regime_persistence_20d: number | null;
  max_gamma_strike_drift_5d: number | null;
  concentration_trend_5d: number | null;
  net_gex_regime: string | null;
  wcb_slope_5d: number | null;
  pct_above_20dma_slope_5d: number | null;
  price_vs_breadth_div: string | null;
  ambient_regime: string | null;
  lens_alignment: string | null;
  session_prior: string | null;
  regime_conditional_note: string | null;
};

export function useAmbientSeries(symbol: Symbol, limit = 40) {
  return useQuery({
    queryKey: ["ambientSeries", symbol, limit],
    staleTime: MV_STALE,
    retry: false,
    queryFn: async (): Promise<AmbientSeriesRow[]> => {
      const { data, error } = await supabase
        .from("market_environment_snapshots")
        .select(
          "as_of_date, eod_spot, front_expiry, cycle_oi_call_put_asym, gex_regime_persistence_20d, max_gamma_strike_drift_5d, concentration_trend_5d, net_gex_regime, wcb_slope_5d, pct_above_20dma_slope_5d, price_vs_breadth_div, ambient_regime, lens_alignment, session_prior, regime_conditional_note",
        )
        .eq("symbol", symbol)
        .order("as_of_date", { ascending: true })
        .limit(limit);
      if (error) return [];
      return (data ?? []) as AmbientSeriesRow[];
    },
  });
}


// ---------- Settings ----------

export type Parameter = {
  id: string;
  key: string;
  value_text: string | null;
  value_num: number | null;
  value_bool: boolean | null;
  value_jsonb: any;
  value_type: "numeric" | "text" | "boolean" | "jsonb";
  category: string;
  description: string | null;
  min_value: number | null;
  max_value: number | null;
  valid_from: string;
  valid_to: string | null;
  changed_by: string | null;
  change_reason: string | null;
};

export function useParameters() {
  return useQuery({
    queryKey: ["parameters"],
    staleTime: SETTINGS_STALE,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("merdian_parameters")
        .select("*")
        .is("valid_to", null)
        .order("category", { ascending: true })
        .order("key", { ascending: true });
      if (error) throw error;
      return (data ?? []) as Parameter[];
    },
  });
}

export function useParameterAudit() {
  return useQuery({
    queryKey: ["parameterAudit"],
    staleTime: SETTINGS_STALE,
    queryFn: async () => {
      const { data, error } = await supabase
        .from("v_merdian_parameter_audit")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(50);
      if (error) throw error;
      return data ?? [];
    },
  });
}

export async function updateParameter(
  key: string,
  changeReason: string,
  value: number | string | boolean,
  valueType: Parameter["value_type"],
) {
  const args: Record<string, any> = {
    p_key: key,
    p_change_reason: changeReason,
  };
  if (valueType === "numeric") args.p_value_num = Number(value);
  else if (valueType === "boolean") args.p_value_bool = Boolean(value);
  else args.p_value_text = String(value);
  const { data, error } = await supabase.rpc("update_parameter", args);
  if (error) throw error;
  return data;
}
```

## Appendix B — `state.ts` in full, and the cited `sections.tsx` ranges

### B.1 `meridian-connect/src/marketview/state.ts` (108 lines, complete)

```typescript
import { useMemo } from "react";
import {
  useSpotMarker, useGammaLatest, useGammaToday, useLatestSignal, useTodaysSignals,
  useGexStrikes, usePinZone, useAccelZone, useIctZones, useStraddleIntraday,
  useMaxPainByStrike, useBreadthIntraday, useWcbLatest, useIvSmile,
  type Symbol as MSymbol,
} from "@/lib/queries";
import { spotFromMarker, formatDTE } from "./ui";

export type MvState = ReturnType<typeof useMvData>;

/**
 * Central data hook: aggregates every query & derived scalar the terminal needs.
 * Every page consumes this via `useMvData(symbol)`.
 */
export function useMvData(symbol: MSymbol) {
  const marker = useSpotMarker(symbol);
  const gamma = useGammaLatest(symbol);
  const gammaToday = useGammaToday(symbol);
  const signal = useLatestSignal(symbol);
  const signals = useTodaysSignals(symbol);
  const expiry = (gamma.data?.expiry_date ?? gamma.data?.expiry) as string | undefined;
  const strikes = useGexStrikes(symbol, expiry);
  const pin = usePinZone(symbol, expiry);
  const accel = useAccelZone(symbol, expiry);
  const zones = useIctZones(symbol);
  const straddle = useStraddleIntraday(symbol);
  const maxPain = useMaxPainByStrike(symbol);
  const breadth = useBreadthIntraday(symbol);
  const wcb = useWcbLatest(symbol);

  const strikeStep = symbol === "NIFTY" ? 50 : 100;
  const g = gamma.data ?? ({} as any);
  const spot = (g.spot ?? spotFromMarker(marker.data) ?? 0) as number;
  const prevClose = (marker.data?.prev_close_spot ?? null) as number | null;
  const changeAbs = prevClose && spot ? spot - prevClose : 0;
  const changePct = prevClose && spot ? ((spot - prevClose) / prevClose) * 100 : 0;

  const regime = (g.regime ?? null) as string | null;
  const gammaZone = (g.gamma_zone ?? null) as string | null;
  const netDealerGamma = (g.net_gex ?? null) as number | null;
  const sigmaPct = (g.flip_distance_pct ?? null) as number | null;
  const flipLevel = (g.flip_level ?? null) as number | null;
  const pinRiskScore = (g.pin_risk_score ?? null) as number | null;
  const expansionProb = (g.expansion_probability ?? null) as number | null;
  const pinProbability = expansionProb != null ? Math.max(0, Math.min(100, 100 - expansionProb)) : null;
  const atmStraddle = (g.straddle_atm ?? null) as number | null;
  const vix = (g.vix ?? null) as number | null;
  const dteDays = (g.dte ?? null) as number | null;

  const strikeAgg = useMemo(() => {
    const rows = (strikes.data ?? []) as any[];
    if (!rows.length) return { maxGammaStrike: null as number | null, peakGammaCr: null as number | null, strongestAmplifyStrike: null as number | null, dampenTotal: null as number | null, amplifyTotal: null as number | null };
    const pos = rows.filter((s) => (s.gex_cr ?? 0) > 0);
    const neg = rows.filter((s) => (s.gex_cr ?? 0) < 0);
    const maxRow = pos.length ? pos.reduce((m, s) => (s.gex_cr > m.gex_cr ? s : m)) : null;
    const minRow = neg.length ? neg.reduce((m, s) => (s.gex_cr < m.gex_cr ? s : m)) : null;
    const dampenTotal = pos.reduce((a, s) => a + (s.gex_cr ?? 0), 0);
    const amplifyTotal = neg.reduce((a, s) => a + (s.gex_cr ?? 0), 0);
    return {
      maxGammaStrike: maxRow?.strike ?? null,
      peakGammaCr: maxRow?.gex_cr ?? null,
      strongestAmplifyStrike: minRow?.strike ?? null,
      dampenTotal: pos.length ? dampenTotal : null,
      amplifyTotal: neg.length ? amplifyTotal : null,
    };
  }, [strikes.data]);
  const { maxGammaStrike, peakGammaCr, strongestAmplifyStrike, dampenTotal, amplifyTotal } = strikeAgg;

  const ivSmile = useIvSmile(symbol, spot, strikeStep);
  const ivSkewPct = ivSmile.data && ivSmile.data.atmCe && ivSmile.data.atmPe
    ? (ivSmile.data.atmPe / ivSmile.data.atmCe - 1) * 100 : null;

  // Latest activity ts (drives staleness ticker in shell)
  const latestActivityTs = (signal.data?.ts ?? g.ts ?? null) as string | null;
  const signalTs = latestActivityTs ? new Date(latestActivityTs).getTime() : null;

  const dte = formatDTE(expiry, dteDays);

  const zonesNearSpot = useMemo(() => {
    if (!spot) return [];
    return (zones.data ?? [])
      .map((z: any) => {
        const lo = z.zone_low ?? z.range_low;
        const hi = z.zone_high ?? z.range_high;
        return { z, lo, hi, mid: lo != null && hi != null ? (lo + hi) / 2 : null };
      })
      .filter((r) => r.mid != null)
      .sort((a, b) => Math.abs((a.mid as number) - spot) - Math.abs((b.mid as number) - spot))
      .slice(0, 10);
  }, [zones.data, spot]);

  const maxPainStrike = maxPain.data?.[0]?.max_pain_strike ?? null;
  const painSpotDistPct = maxPainStrike && spot ? ((spot - maxPainStrike) / maxPainStrike) * 100 : null;
  const gammaPainGap = maxPainStrike && maxGammaStrike ? Math.abs(maxGammaStrike - maxPainStrike) : null;

  return {
    symbol, strikeStep, expiry, dte, spot, prevClose, changeAbs, changePct,
    regime, gammaZone, netDealerGamma, sigmaPct, flipLevel,
    pinRiskScore, expansionProb, pinProbability, atmStraddle, vix,
    maxGammaStrike, peakGammaCr, strongestAmplifyStrike, dampenTotal, amplifyTotal,
    ivSmile, ivSkewPct, zonesNearSpot, maxPainStrike, painSpotDistPct, gammaPainGap,
    latestActivityTs, signalTs,
    // raw queries
    marker, gamma, gammaToday, signal, signals, strikes, pin, accel, zones,
    straddle, maxPain, breadth, wcb,
  };
}
```

### B.2 `meridian-connect/src/marketview/sections.tsx` lines 28–135

`SnapshotStrip` (:28), `KeyParametersSection` (:62), `PositioningSection` (:101), opening of `NetDealerGammaSection` (:130).

```tsx
export function SnapshotStrip({ s }: { s: MvState }) {
  const cells: Array<{ label: string; value: React.ReactNode; sub?: React.ReactNode; color?: string }> = [
    { label: "SPOT", value: s.spot ? fmtNum(s.spot) : "—",
      sub: <span style={{ color: s.changePct >= 0 ? MV.green : MV.red }}>{fmtSigned(s.changeAbs)} ({fmtPct(s.changePct)})</span> },
    { label: "NET γ", value: s.netDealerGamma != null ? `${fmtSigned(s.netDealerGamma)} Cr` : "—",
      color: (s.netDealerGamma ?? 0) >= 0 ? MV.green : MV.red },
    { label: "MAX γ", value: s.maxGammaStrike != null ? fmtNum(s.maxGammaStrike, { maximumFractionDigits: 0 }) : "—",
      sub: s.maxGammaStrike && s.spot ? `${fmtPct(((s.maxGammaStrike - s.spot) / s.spot) * 100, 1)}` : undefined },
    { label: "MAX PAIN", value: s.maxPainStrike != null ? fmtNum(s.maxPainStrike, { maximumFractionDigits: 0 }) : "—",
      sub: s.painSpotDistPct != null ? fmtPct(s.painSpotDistPct, 1) : undefined },
    { label: "PIN SCORE", value: s.pinRiskScore != null ? `${Math.round(s.pinRiskScore)}/100` : "—",
      color: (s.pinRiskScore ?? 0) >= 75 ? MV.purple : MV.mid },
    { label: "VIX", value: s.vix != null ? s.vix.toFixed(2) : "—" },
    { label: "EXPIRY", value: s.expiry ? new Date(s.expiry).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }) : "—",
      sub: s.dte },
  ];
  return (
    <div className="flex flex-wrap items-stretch gap-x-6 gap-y-2 rounded-lg px-4 py-2.5"
      style={{ background: MV.card, border: `1px solid ${MV.border}` }}>
      <div className="flex items-center pr-2"><LiveTag /></div>
      {cells.map((c) => (
        <div key={c.label} className="flex flex-col">
          <span className="text-[9px] font-semibold uppercase tracking-[0.1em]" style={{ color: MV.weak }}>{c.label}</span>
          <span className="text-[14px] font-bold tabular-nums leading-tight" style={{ color: c.color ?? MV.strong, fontFamily: MV.mono }}>{c.value}</span>
          {c.sub != null && <span className="text-[10px]" style={{ color: MV.weak, fontFamily: MV.mono }}>{c.sub}</span>}
        </div>
      ))}
    </div>
  );
}

/* --------------------------------------------------------- */
/* Key parameters strip (positioning summary tiles).         */
/* --------------------------------------------------------- */
export function KeyParametersSection({ s }: { s: MvState }) {
  const regimeMapped = s.regime ? REGIME_DISPLAY[s.regime] : null;
  const regimePill = regimeMapped
    ? { text: regimeMapped.label, bg: regimeMapped.bg, fg: regimeMapped.fg, sub: s.gammaZone ? `${regimeMapped.desc} · ${s.gammaZone}` : regimeMapped.desc }
    : s.regime ? { text: s.regime, bg: MV.blueBg, fg: MV.blue, sub: s.gammaZone ?? "" } : null;

  return (
    <div>
      <SectionLabel>Key Parameters</SectionLabel>
      <div className="flex flex-wrap gap-3">
        <Tile label="Regime" value="" pill={regimePill} sub={regimePill?.sub} badge={<LiveTag />} />
        <Tile label="Net Dealer γ"
          value={s.netDealerGamma != null ? `${fmtSigned(s.netDealerGamma)} Cr` : "—"}
          valueColor={(s.netDealerGamma ?? 0) >= 0 ? MV.green : MV.red}
          badge={<LiveTag />}
          sub={s.dampenTotal != null || s.amplifyTotal != null
            ? `Σdmp ${fmtNum(s.dampenTotal)}k · Σamp ${fmtNum(s.amplifyTotal)}` : "no flow breakdown"} />
        <Tile label="Spot Context"
          value={s.sigmaPct != null ? `±${s.sigmaPct.toFixed(2)}%` : "—"}
          sub={s.sigmaPct != null && s.spot ? `σ ${fmtNum(s.spot * (1 - s.sigmaPct / 100), { maximumFractionDigits: 0 })}–${fmtNum(s.spot * (1 + s.sigmaPct / 100), { maximumFractionDigits: 0 })} · ${s.dte}` : s.dte} />
        <Tile label="Flip Level" value={s.flipLevel != null ? fmtNum(s.flipLevel) : "—"}
          sub={s.flipLevel != null && s.spot ? `${fmtPct(((s.flipLevel - s.spot) / s.spot) * 100)} from spot` : "no flip in window"} />
        <Tile label="Max γ Strike" value={s.maxGammaStrike != null ? fmtNum(s.maxGammaStrike) : "—"}
          sub={s.maxGammaStrike && s.spot
            ? `${fmtPct(((s.maxGammaStrike - s.spot) / s.spot) * 100)} from spot${s.peakGammaCr != null ? ` · pk ${fmtSigned(s.peakGammaCr)} Cr` : ""}` : "—"} />
        <Tile label="Pin Zone"
          value={s.pin.data ? `${fmtNum(s.pin.data.pin_lower, { maximumFractionDigits: 0 })}–${fmtNum(s.pin.data.pin_upper, { maximumFractionDigits: 0 })}` : "—"}
          sub={s.pin.data ? `pk ${fmtNum(s.pin.data.peak_pin_strike ?? s.pin.data.pin_strike, { maximumFractionDigits: 0 })}${s.pin.data.n_strikes != null ? ` · n=${s.pin.data.n_strikes}` : ""}${s.pin.data.tau_used != null ? ` · τ${s.pin.data.tau_used}` : ""}` : "—"} />
        <Tile label="Accel Zone"
          value={s.accel.data ? `${fmtNum(s.accel.data.accel_lower, { maximumFractionDigits: 0 })}–${fmtNum(s.accel.data.accel_upper, { maximumFractionDigits: 0 })}` : "—"}
          sub={s.accel.data ? "active in window" : "none in window"} />
      </div>
    </div>
  );
}

/* --------------------------------------------------------- */
/* Positioning landscape hero chart.                          */
/* --------------------------------------------------------- */
export function PositioningSection({ s }: { s: MvState }) {
  const [resetKey, setResetKey] = useState(0);
  return (
    <div>
      <SectionLabel>Positioning Landscape — Dealer γ by Strike</SectionLabel>
      <Card title="Dealer γ by Strike"
        subtitle={`dampening (long γ) vs amplifying (short γ) · σ-band to expiry · ${s.strikes.data?.length ?? 0} strikes`}>
        <div className="mb-3 flex flex-wrap gap-x-6 gap-y-1 text-[11px]" style={{ fontFamily: MV.mono }}>
          <Scalar label="net γ in window" value={s.netDealerGamma != null ? `${fmtSigned(s.netDealerGamma)} Cr` : "—"} color={(s.netDealerGamma ?? 0) >= 0 ? MV.green : MV.red} />
          <Scalar label="Σ dampen" value={s.dampenTotal != null ? `${fmtSigned(s.dampenTotal)} Cr` : "—"} color={MV.green} />
          <Scalar label="Σ amplify" value={s.amplifyTotal != null ? `${fmtSigned(s.amplifyTotal)} Cr` : "—"} color={MV.red} />
          <Scalar label="strongest dampen" value={fmtNum(s.maxGammaStrike, { maximumFractionDigits: 0 })} />
          <Scalar label="strongest amplify" value={s.strongestAmplifyStrike != null ? fmtNum(s.strongestAmplifyStrike, { maximumFractionDigits: 0 }) : "—"} color={MV.red} />
          <Scalar label="Σ to expiry" value={s.sigmaPct != null ? fmtPct(s.sigmaPct) : "—"} color={MV.blue} />
        </div>
        <HeroChart spot={s.spot} bars={(s.strikes.data ?? []) as any} pin={s.pin.data as any} accel={s.accel.data as any}
          step={s.strikeStep} resetKey={resetKey} sigmaPct={s.sigmaPct} maxGammaStrike={s.maxGammaStrike} flipLevel={s.flipLevel} />
        <div className="mt-1 flex items-center justify-between">
          <div className="text-[9px]" style={{ color: MV.weak }}>scroll to zoom · drag to pan</div>
          <button onClick={() => setResetKey((k) => k + 1)} className="text-[10px] underline" style={{ color: MV.weak }}>reset view</button>
        </div>
      </Card>
    </div>
  );
}

/* --------------------------------------------------------- */
/* Net dealer γ — direction + intraday line.                  */
/* --------------------------------------------------------- */
export function NetDealerGammaSection({ s }: { s: MvState }) {
  const rows = (s.gammaToday.data ?? []) as Array<{ ts: string; net_gex: number | null }>;
  const dir = useMemo(() => netGammaDirection(rows), [rows]);
  const dirColor = dir === "Rising" ? MV.green : dir === "Falling" ? MV.red : MV.weak;
  const dirIcon = dir === "Rising" ? "↑" : dir === "Falling" ? "↓" : "→";
  return (
```

### B.3 `meridian-connect/src/marketview/sections.tsx` lines 206–294

`PinRiskRowSection` (:206), `PinRiskTimelineSection` (:276).

```tsx
export function PinRiskRowSection({ s }: { s: MvState }) {
  return (
    <div>
      <SectionLabel>Pin Risk & ATM</SectionLabel>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <div className="text-[10px] font-semibold uppercase tracking-[0.1em]" style={{ color: MV.weak }}>Pin Risk Score</div>
          <div className="mt-1 text-[30px] font-bold leading-none" style={{ color: MV.purple, fontFamily: MV.mono }}>
            {s.pinRiskScore != null ? Math.round(s.pinRiskScore) : "—"}
            <span className="text-[14px]" style={{ color: MV.weak }}>{s.pinRiskScore != null ? " /100" : ""}</span>
          </div>
          <div className="mt-2 text-[11px]" style={{ color: MV.weak, fontFamily: MV.mono }}>
            {s.pinRiskScore != null
              ? s.pinRiskScore >= 75 ? "strong pin · 75 threshold exceeded"
                : s.pinRiskScore >= 50 ? "moderate pin" : "weak pin"
              : "no pin-risk data"}
          </div>
          <div className="mt-3"><Gauge value={s.pinRiskScore ?? 0} color={MV.purple} /></div>
          <div className="mt-1.5 flex justify-between text-[9px]" style={{ color: MV.weak, fontFamily: MV.mono }}>
            <span>0</span><span>25 weak</span><span>50</span><span>75 strong</span><span>100</span>
          </div>
        </Card>
        <Card>
          <div className="text-[10px] font-semibold uppercase tracking-[0.1em]" style={{ color: MV.weak }}>Pin Probability</div>
          {s.pinProbability != null ? (<>
            <div className="mt-1 text-[30px] font-bold leading-none" style={{ color: MV.purple, fontFamily: MV.mono }}>
              {s.pinProbability.toFixed(1)}%
            </div>
            <div className="mt-2 text-[11px]" style={{ color: MV.weak, fontFamily: MV.mono }}>
              complement of expansion ({s.expansionProb != null ? s.expansionProb.toFixed(1) + "%" : "—"})
              {s.maxGammaStrike != null ? ` · near ${fmtNum(s.maxGammaStrike, { maximumFractionDigits: 0 })}` : ""}
            </div>
            <div className="mt-3"><Gauge value={s.pinProbability} color={MV.purple} /></div>
          </>) : <Unavailable label="expansion_probability not exposed" />}
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.1em]" style={{ color: MV.weak }}>ATM Straddle</div>
              <div className="mt-1 text-[30px] font-bold leading-none" style={{ fontFamily: MV.mono }}>
                ₹{s.atmStraddle != null ? Math.round(s.atmStraddle) : "—"}
                <span className="ml-1 text-[12px] font-normal" style={{ color: MV.weak }}>today</span>
              </div>
            </div>
            {(() => {
              const last = [...(s.straddle.data?.buckets ?? [])].reverse().find((b) => b.today != null);
              const avg = last ? s.straddle.data!.buckets.find((b) => b.bucket === last.bucket)?.avg ?? null : null;
              if (last?.today == null || avg == null) return null;
              const diffPct = ((last.today - avg) / avg) * 100;
              return (
                <div className="text-[11px] font-medium" style={{ color: diffPct >= 0 ? MV.green : MV.red, fontFamily: MV.mono }}>
                  {fmtPct(diffPct, 1)} vs avg
                </div>
              );
            })()}
          </div>
          <div className="mt-3">
            <StraddleIntradayChart buckets={s.straddle.data?.buckets ?? []} />
          </div>
          <div className="mt-1 flex justify-between text-[9px]" style={{ color: MV.weak, fontFamily: MV.mono }}>
            <span>09:15 intraday</span>
            <span>{s.straddle.data?.daysUsed ?? 5}d avg</span>
          </div>
        </Card>
      </div>
    </div>
  );
}

/* --------------------------------------------------------- */
export function PinRiskTimelineSection({ s }: { s: MvState }) {
  return (
    <div>
      <SectionLabel>Pin Risk Timeline</SectionLabel>
      <Card title="Pin Risk Timeline"
        subtitle="intraday pin-score (purple, L axis) vs spot (blue, R axis) · today's session">
        <PinRiskTimeline rows={(s.gammaToday.data ?? []) as any} />
        <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[10px]" style={{ color: MV.weak, fontFamily: MV.mono }}>
          <span><span style={{ color: MV.purple }}>●</span> pin score {s.pinRiskScore != null ? Math.round(s.pinRiskScore) : "—"} / 100</span>
          <span><span style={{ color: MV.blueLine }}>—</span> spot {fmtNum(s.spot, { maximumFractionDigits: 0 })}</span>
          <span>{(s.gammaToday.data ?? []).length} samples</span>
        </div>
      </Card>
    </div>
  );
}

/* --------------------------------------------------------- */
export function BreadthVolSection({ s }: { s: MvState }) {
```
