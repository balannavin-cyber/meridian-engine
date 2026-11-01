# 50_outbound_and_constants — outbound text and numeric literals (prompt §3 item 6)

## 1. Consumer-facing artefacts that PRINT a Γ magnitude

Exactly one live scheduled producer prints a Γ size to a human-facing artefact.

### `generate_pine_overlay.py` — AWS cron `52 10 * * 1-5` (10:52 UTC = 16:22 IST)

Reads the two **unwrapped scale-A** views and renames their columns at the boundary:

| line | code | effect |
|---|---|---|
| `:225` | `sb.table("v_gex_strike_pin_zone").select(…)` | source, scale A, **no `_1pct` wrapper exists** |
| `:235` | `"total_gex_cr": float(r["total_pin_gex_cr"])` | **rename** `total_pin_gex_cr` → `total_gex_cr` |
| `:236` | `"peak_gex_cr":  float(r["peak_pin_gex_cr"])` | **rename** `peak_pin_gex_cr` → `peak_gex_cr` |
| `:247` | `sb.table("v_gex_strike_accel_zone").select("… trough_gex_cr …")` | source, scale A, no wrapper |
| `:257` | `"total_gex_cr":  float(r["total_accel_gex_cr"])` | **rename** → `total_gex_cr` (**same dict key as the pin side**) |
| `:258` | `"trough_gex_cr": float(r["trough_gex_cr"])` | kept |
| `:334` | `peak_str = f"peak +{pin['peak_gex_cr']/1000:.0f}K Cr"` | **`/1000` + hardcoded unit word `K Cr`** |
| `:335` | `zone_str = f"zone +{pin['total_gex_cr']/1000:.0f}K Cr"` | same |
| `:363` | `trough_str = f"trough {accel['trough_gex_cr']/1000:.0f}K Cr"` | same |
| `:364` | `zone_str   = f"zone {accel['total_gex_cr']/1000:.0f}K Cr"` | same |

Three things about this site:
1. **The rename defeats the obvious search.** `git grep peak_pin_gex_cr` never reaches `:334`.
   Anyone auditing by column name finds the read at `:236` and misses the render 98 lines later.
2. **`/1000` with a literal `K Cr` word is a hardcoded magnitude assumption.** It is the only
   place in the system that assumes a Γ size is in the thousands-of-crore range.
3. **No test renders this file.** It is absent from all 30 steps of `tests/run_offline.sh`.

The `// ENH-81 positioning as-of <ts>` stamp in the emitted Pine is the fail-soft surface CLAUDE.md
already names as a settled lesson; the four strings above sit inside `_pine_positioning_render`.

### Everything else outbound — measured, and it is text, not magnitudes

**Telegram: 0 sends carry a Γ magnitude.** The 14 tracked `.py` files holding the token `telegram`
were each grepped for `gex|gamma`; 8 matched, and in every one the match is a **regime word or a
status word**, never a number:
- `gamma_engine_alert_check.py:123` `f"GAMMA ENGINE ALERT: {status}"`, `:145` `GAMMA ENGINE STATUS: {status}`
- `merdian_pipeline_alert_daemon.py:346,368,385,386` — selects `gamma_regime`, appends `f"gamma={gamma}"`
- `fix_enh46a_signal_alerts.py:139,161,178,179` — same, in the patch script for the above
- `run_option_snapshot_intraday_runner.py`, `run_merdian_shadow_runner.py` — step names only
  (`f"{symbol} compute_gamma_metrics"`), `TIMEOUT_GAMMA = 240` (seconds)
- `validate_compute_contracts.py:264` — a REST URL with `select=run_id,created_at`
- `preflight_common.py`, `docs/research/s97_ops/patches/apply_tg_fix_s97.py` — no Γ value

Positive control for that zero: the token `telegram` hits in 14 tracked `.py` files, so the grep
reaches the senders; and the same grep DID return the `gamma=` and `GAMMA ENGINE ALERT` lines, so
the Γ pattern fires inside them. The zero is "no magnitude", not "no match".

**Pine source files: 0 Γ magnitudes.** 4 tracked `.pine` files; their `gex|gamma|Cr` hits are
1, 1, 3 and 5. Read: all are input-label text and the `step=0.01` of a float input widget
(`MERDIAN_ICT_Primitives_canonical*.pine:67`, `merdian_ict_overlay.pine:45,50`) — ICT detection
thresholds in **percent of price**, unrelated to Γ. The generated overlay is written by
`generate_pine_overlay.py` above and is not tracked.

**CSV writers: 56 tracked `.py` use `csv.writer`/`DictWriter`/`to_csv`; 5 of those also mention
`gex_cr|net_gex`.** All five are research/diagnostic scripts, none scheduled:
`canonical_no_flip_pipeline_check.py`, `canonical_ob_gamma_scalar.py`, `canonical_ob_gamma_zone.py`,
`canonical_ob_gamma_zone_bs.py`, `s31_weekly_attribution_diagnostic.py`.

**`scripts/eod_health_check.py`** (AWS cron `45 0 * * 2-6`) touches `GEX_TABLE` at `:301,309,320,332`
— presence and row-count checks only (`"{GEX_TABLE} is empty"`, `"view lists {absent} but no rows
present"`). No magnitude. Its one scale literal is `:550` `tot * PRIMARY_PARITY_TOL_PCT / 100.0`,
a percentage of a row count, not of a Γ value.

## 2. Every numeric literal compared with, scaled against, or used as a tolerance for a Γ size

Grouped by what the number MEANS. "Scale" is the stored scale the literal assumes.

### (a) The unit divisor — scale A's definition. 9 sites.

| file:line | form | scheduled? |
|---|---|---|
| `merdian_compute/gamma.py:54` | `gamma * oi * (spot ** 2) / 1e7` | **YES** — orchestrator, every 5 min |
| `backfill_gamma_metrics.py:83` | `gamma * oi * spot ** 2 / 10000000.0` | no |
| `backfill_gamma_metrics_to_main.py:224` | `sign * gamma * oi * spot ** 2 / 10000000.0` | no |
| `backfill_hist_greeks.py:56` + `:164` | `CR_SCALE = 1e7`; `gamma * oi * (spot ** 2) / CR_SCALE` | no — **module constant, invisible to the AST literal rule** |
| `replay/replay_compute_gamma_metrics.py:88` | `gamma * oi * spot ** 2 / 10000000.0` | no (ADR-008 replay) |
| `measure_rate_sensitivity.py:107` | `gamma * oi * spot ** 2 / 10000000.0` | no |
| `tests/test_p3a_invariants.py:38` | `gamma * oi * spot * spot / 1e7` | **YES** — suite step 12 |
| `tests/test_dex_recompute.py:174` + `:351` | `CR = 1e7`; `gamma * oi * (spot ** 2) / CR` | **YES** — suite step 11, also module constant |
| **DB** `v_gex_greeks_l2_strike` | `u_gex_drift_* * oi * power(spot,2) / 10000000` | **YES** — live view |
| **DB** `v_gex_repriced_flip` | BS γ `… * oi * power(s_grid,2) / 10000000` → `total_gex` | **YES** — live view |

Plus the 10 `compute_gamma_metrics_local_PRE_*` / `replay_*_PRE_*` backup copies (unscheduled).

### (b) A DIFFERENT scale — `/1e7` with an extra `× 100`. 2 sites, neither A nor B.

| file:line | form |
|---|---|
| `canonical_ob_gamma_zone.py:204` | `df['gamma'] * df['oi'] * spot ** 2 * 100.0 / 10000000.0` |
| `canonical_ob_gamma_zone_bs.py:323` | `sign * gamma * float(row['oi']) * spot ** 2 * 100.0 / 10000000.0` |

These are **100× scale A**, i.e. `γ·OI·S²/1e5`. Neither scheduled. Flagged because a reader
comparing their output to `gex_cr` would be off by exactly 100 — the same factor the unit change
introduces, in the opposite direction.

### (c) A FOURTH scale — per-1 % with a LOT multiplier. 1 site, in a golden fixture.

`tests/golden/2026-10-01_SENSEX/queries/ladder_replay_1001.sql:8` (comment) and `:63,72,73,74`:
```
--   gamma_load(strike) = sum over CE+PE of gamma * oi * lot * spot^2 * 0.01 / 1e7   (MERDIAN units;
--   pct_of_leader      = gamma_load / leader gamma_load
         sum(gex_abs)                       AS gamma_load,
         row_number() OVER (… ORDER BY gamma_load DESC)  AS rk,
         gamma_load / nullif(max(gamma_load) OVER (PARTITION BY ts), 0) AS pct_of_leader,
```
Already carries `× 0.01` **and** an explicit `lot` factor that no live Γ path applies
(CLAUDE.md's ENH-140 note records that `oi` is a quantity with the lot already inside it). Names
used: **`gamma_load`** and **`gex_abs`** — neither in the prompt's §2 token list.

### (d) Magnitude thresholds ON a Γ size. 6 sites. None scheduled; none tested.

| file:line | literal | test | meaning under scale A | what a 100× unit change does |
|---|---|---|---|---|
| `backfill_gamma_metrics_broken_window.py:71,72,122` | `NETGEX_MIN_CR = 100`, `NETGEX_MAX_CR = 1_000_000` | `100 < abs(ng) < 1e6` | plausible-Cr band | real band becomes 1…10,000; the floor rejects most rows |
| `verify_td_new_3_net_gex_unit.py:124,125` | `100`, `1_000_000` | `op_sane = 100 < abs_ng < 1_000_000` | the same band, printed as the verdict | same |
| `phase0b_p5_pinned_proxy_v2.py:75,78,154` | `RAW_NET_GEX_THRESHOLD = 1e9` | `abs(float(ng)) > 1e9` | detects **pre-TD-NEW-3 raw-rupee** rows | still separates raw from scaled, but the margin shrinks 100× |
| `s31_weekly_attribution_diagnostic.py:94` | `GAMMA_UNIT_BOUNDARY = datetime(2026,4,1)` | a **date**, not a number | straddles the raw→Cr era change | a third era would need a second boundary |
| `canonical_no_flip_pipeline_check.py:139,271` | `log10`, `%.2e` | reports `log10 median \|net_gex\|` | a scale **detector** by design | the reported value shifts by exactly −2 |
| **DB** `compute_options_regime(net_gex)` | `±0.0005` | `net_gex > 0.0005 → LONG_GAMMA` | dead-band far below the data | behaviour unchanged; the band's real width moves 100× |

### (e) Display divisors / magnitude-branching formatters. 4 sites, all unit-word-changing.

| file:line | literal | effect |
|---|---|---|
| `generate_pine_overlay.py:334,335,363,364` | `/1000` + `"K Cr"` | §1 above |
| `connect/src/pages/Board.tsx:27` (`crLakh`) | `1e5` | `"…L Cr"` vs `"… Cr"` — **the unit word itself** |
| `connect/src/pages/Board.tsx:197` (`lad`) | `1e5` | `"…L"` vs plain |
| `connect/src/components/board/GammaRiver.tsx:7` (`lak`) | `1e5` | `"…L"` vs plain, on `net_gex_cr_1pct` |

### (f) Literals that are NOT about the Γ unit — recorded so they are not mistaken for it

- `merdian_compute/gamma.py:51` `abs(gamma) > 5e-5` — a **per-option γ** sanity bound
  (TD-NEW-2 deep-ITM guard), not a Γ size. Mirrored at `backfill_gamma_metrics_to_main.py:104`
  (`SANITY_GUARD_GAMMA_MAX = 5e-5`), `measure_rate_sensitivity.py:105`,
  `tests/test_p3a_invariants.py:36`, `backfill_hist_greeks.py` (`ITM_GAMMA`).
- `merdian_compute/gamma.py:189` `_FLIP_DOMINANCE_EPS_FRAC = 0.01` — a **fraction** of the
  strike-map maximum. Scale-invariant. Covered by suite step 25 mutant M2.
- `merdian_compute/gamma.py:407,409` `gamma_concentration >= 0.25 / 0.15` — a dimensionless
  Herfindahl top-1 share. Scale-invariant.
- `merdian_compute/gamma.py:405,428` `net_gex < 0`, `net_gex >= 0` — pure **sign**. Every
  `net_gex`-vs-literal comparison the AST sweep found in a live path is against `0`.
- `merdian_compute/gamma.py:623,825` `/100.0`, `*100.0` — on `expansion_probability` and
  `flip_distance/spot`, i.e. percent conversions on non-Γ quantities.
- `canonical_ob_gamma_zone*.py` `ZONE_MASS_THRESHOLD = 0.50` — a **share of total |mass|**.
  Scale-invariant, though the mass it is a share of is at the odd scale of (b).
- `tests/test_dex_recompute.py:175` `TOL_CR = 1e-6` and the `1e-6`/`1e-9` bands across
  `sql/2026-10-1*`, `docs/research/s96_priority/p3b/*` — **recompute tolerances**, absolute in
  scale-A crore. They tighten relatively by 100× if the quantity shrinks; none is a unit statement.
- `measurement_health_snapshot_local.py:257` `limit=100000` — a page size.
- `fii_dii_cash_daily.{fii,dii}_{buy,sell,net}_cr` — ₹ crore of **cash flow**. Ends `_cr`,
  is not a Γ size, must not be touched. Same for every `*_dex_cr`, `*_flow_cr`, `*_iv_*_cr`,
  `*_t_*_cr` column (Δ-notional, `oi·S/1e7`, already true ₹ Cr per CLAUDE.md ADR-032 D1).
