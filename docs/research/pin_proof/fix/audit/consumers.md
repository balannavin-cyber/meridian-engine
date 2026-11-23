<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/audit/consumers.md -->

# A1 — consumers of `gex_cr`, `gex_strike_snapshots` and their aggregates

Code read only; no database was queried for this file. Starting point
`docs/research/pin_proof/fix/stage0_code_read.md`. Trees: `~/meridian-engine`
(`sql/`, `merdian_compute/`, writers, runners) and `~/meridian-connect/src`.

Tags — **GROSS** = built from `abs(gex_cr)` or a sum of magnitudes; **NET** = built
from the signed value; **INTERPRETATION** = a label or decision about dealer
positioning laid on top of either.

---

## 0. The origin — where `gex_cr` is made

| file:line | computes | read next | tag |
|---|---|---|---|
| `merdian_compute/gamma.py:36-56` | `signed_gamma_exposure(row, spot)` = `gamma*oi*spot²/1e7`, **negated for PE** (`:55`); returns 0 when `gamma == 0 or oi <= 0 or spot <= 0` (`:42`); returns 0 for any strike >5 % from spot with `abs(gamma) > 5e-5` (`:50-52`, TD-NEW-2 deep-ITM guard) | everything below | **NET** |
| `merdian_compute/gamma.py:674-752` | `build_gss_rows` — per strike `gex_cr += signed_gamma_exposure` (`:722`); `gamma_call`/`gamma_put` first-write-wins, a vendor 0 stored as NULL (`:723-730`); drops strikes with no OI and no GEX (`:735-736`) | `gex_strike_snapshots` | **NET** |
| `compute_gamma_metrics_local.py:467-481` | `upsert_gex_strike_snapshots`, `on_conflict="run_id,strike,expiry_date"` (`:478`) | the table | — |

**The single fact that shapes everything downstream: `gex_cr` is a per-strike NET
(call contribution minus put contribution), so one number cannot be decomposed back
into the two legs.** Every GROSS consumer below rebuilds magnitude from
`abs(net)`, which is not the gross book.

## 1. Engine — Python, live path

| file:line | computes | read next | tag |
|---|---|---|---|
| `merdian_compute/gamma.py:160-161` | `compute_net_gex` = `sum(signed_gamma_exposure)` | `gamma_metrics.net_gex` | **NET** |
| `merdian_compute/gamma.py:164-172` | `build_strike_exposure_map` — strike → summed signed exposure | the four functions below | **NET** |
| `merdian_compute/gamma.py:174-190` | `compute_gamma_concentration` = `max(abs(v)) / sum(abs(v))` over the strike map | `gamma_metrics.gamma_concentration` | **GROSS** (magnitudes) |
| `merdian_compute/gamma.py:192-226`, `:227+` | `_flip_short_gamma_perstrike`, `compute_flip_level` — walks the signed map for the sign change | `gamma_metrics.flip_level`, `flip_distance`, `flip_distance_pct` | **NET** |
| `merdian_compute/gamma.py:535-562` | `compute_max_gamma_strike` = argmax over **positive** entries only (`:561-562`) | `gamma_metrics.max_gamma_strike` | **INTERPRETATION** (asserts positive = pin candidate) |
| `merdian_compute/gamma.py:425-430` | `determine_regime(net_gex, flip_level)` → regime label | `gamma_metrics.regime` | **INTERPRETATION** |
| `merdian_compute/gamma.py:431-440` | `determine_gamma_zone(flip_distance_pct)` | `gamma_metrics.gamma_zone` | **INTERPRETATION** |
| `compute_gamma_metrics_local.py:314-356` | `fetch_recent_max_gamma_strikes` — reads `gex_strike_snapshots` `select("ts,strike,gex_cr")` (`:335`) **filtered `.gt("gex_cr", 0)`** (`:338`), argmax per ts (`:355`) | `compute_pin_risk_score` → `gamma_metrics.pin_risk_score` | **INTERPRETATION** (positive-only = "PIN candidates", its own comment `:319-320`) |
| `compute_gamma_metrics_local.py:392`, `:423-441` | assembles the `gamma_metrics` payload: `net_gex`, `gamma_concentration`, `max_gamma_strike`, `pin_risk_score` | `gamma_metrics` table | mixed |
| `write_gex_cycle_history_local.py:144-160` | `fetch_rank_rows` — reads `v_gex_strike_rank` (`strike_rank, strike, gex_cr, share_of_abs, cum_share_of_abs, n_ranked, n_strikes`) | `merdian_compute/cycle.py` | **GROSS** (ranked on `abs`) |
| `merdian_compute/cycle.py:62-102` | `derive_rank_fields` — rank 1 → `pin_leader_strike`, `gamma_at_pin = gex_cr` (`:80-81`); `runnerup_share_ratio = s2/s1` (`:86-87`); `top5_share` (`:92-101`) | `gex_cycle_history` cols 17-21 | **GROSS** for the ranking, **NET** for the stored `gamma_at_pin` value |
| `write_gex_cycle_history_local.py:324-404` | `build_row` — 36 columns incl. `pin_state`, `conviction`, `conc_top1_share` (populated from `conc["hhi_net"]`, `:388`) | `gex_cycle_history` → `v_pin_board` → Board | **INTERPRETATION** |
| `generate_pine_overlay.py` (13 refs) | Pine overlay artefact carrying pin / accel positioning | TradingView overlay file | **INTERPRETATION** |
| `services/tape_scoring/score.py` (9 refs) | tape scoring reads gamma quantities | tape scoring output | **INTERPRETATION** |
| `compile_market_environment_local.py` (7 refs) | market-environment compile | downstream env record | **INTERPRETATION** |

## 2. Engine — SQL views

| file:line | computes | read next | tag |
|---|---|---|---|
| `sql/2026-05-25_enh80_gex_strike_snapshots.sql` | the table DDL | all below | — |
| `sql/2026-09-15_s79_v_gex_abs_exposure.sql:138-139` | `sum(gex_cr) AS net_gex_cr`, `sum(abs(gex_cr)) AS abs_gex_cr` | Board Net Γ / Gross \|Γ\| tiles | **NET** + **GROSS** |
| `sql/2026-09-15_s79_v_gex_concentration.sql:270-278` | `hhi_net = max(abs(gex_cr))/sum(abs(gex_cr))`; `hhi_call`, `hhi_put`; `top_strike_net` = strike at `max(abs(gex_cr))` | Board top-strike share; `gex_cycle_history.conc_*` | **GROSS** |
| `sql/2026-09-22_s81_v_gex_strike_rank.sql:197-250` | ranks every `gex_cr <> 0` strike on `abs(gex_cr)`; `share_of_abs`, `cum_share_of_abs`, `side` (DAMPENING/AMPLIFYING, `:237-239`) | `write_gex_cycle_history_local.py`, Board ladder | **GROSS** rank, **INTERPRETATION** for `side` |
| `sql/2026-09-15_s79_v_gex_strike_walls.sql:150-164` | call/put wall = argmax **raw OI** inside ±1.5σ; **does not read `gex_cr`** | Board corridor; `gex_cycle_history.call_wall_strike`/`put_wall_strike` | **INTERPRETATION** (OI-based, listed because the Board shows it beside gamma) |
| `sql/2026-10-26_s101_v_gex_strike_pin_zone_live_captured.sql:74-124` | PIN BAND: peak at `max(gex_cr)` with `gex_cr > 0` (`:81`), walks neighbours while `gex_cr >= tau*peak` and `gex_cr > 0` (`:112`), `tau` default 0.3 (`:79`); emits `pin_lower`, `pin_upper` (`:118-119`) | `gex_pin_maxpain_history.pin_lower/pin_upper`; Board PIN BAND tile | **INTERPRETATION** (positive-only walk) |
| `sql/2026-10-26_s101_v_gex_strike_accel_zone_live_captured.sql` | the mirror accel zone | Board | **INTERPRETATION** |
| `sql/2026-09-22_s81_v_gex_net_gamma_river.sql:152` | `net_gex AS net_gex_cr` session series | Board river | **NET** |
| `sql/2026-10-09_s92_v_gex_strike_terrain.sql:76` | per-strike terrain surface | Board ladder / Lab3D | **NET** |
| `sql/2026-09-22_s80_v_gex_max_pain.sql`, `sql/2026-10-30_s103_v_gex_max_pain_latest_run_skip_scan.sql` | max pain (OI-based) joined to walls/corridor | Board | **INTERPRETATION** |
| `sql/2026-09-22_s80_v_gex_pin_maxpain.sql` | pin vs max-pain distance in points/strikes/σ | `gex_pin_maxpain_history` | **INTERPRETATION** |
| `sql/2026-10-30_s102_gex_per_1pct_views.sql:14,18-20,24,28-30` | `*_1pct` wrappers: `× 0.01` on `net_gex_cr`, `abs_gex_cr`, `gex_cr`, drift columns (ADR-032 D1) | every Board tile | unit wrapper, tag inherited |

## 3. Marketview (`~/meridian-connect/src`)

| file:line | computes / reads | read next | tag |
|---|---|---|---|
| `src/lib/board.ts:127-143` | `gex_cr` at the strike nearest spot, from the latest `gex_strike_snapshots` run (direct table read) | Board strip | **NET** |
| `src/lib/board.ts:290-297` | `v_gex_strike_terrain…` — `gex_cr_1pct, gamma_call, gamma_put, oi_call, oi_put` per strike | ladder / terrain | **NET** (+ raw legs) |
| `src/lib/board.ts:353-359` | `v_gamma_metrics_1pct.net_gex_1pct` series | Net Γ sparkline | **NET** |
| `src/lib/board.ts:372-387` | `session_min/max/net_gex_cr_1pct` session band | Net Γ session band | **NET** |
| `src/lib/board.ts:453-459` | `v_gex_strike_rank` — `strike_rank, share_of_abs, cum_share_of_abs, gex_cr, side` | ladder, Pin tile | **GROSS** + **INTERPRETATION** (`side`) |
| `src/lib/board.ts:427-441` | `v_pin_board` — the stored pin row | Pin tab | **INTERPRETATION** |
| `src/components/board/LadderPanel.tsx:19,26,27` | tiles **Net Γ**, **Gross \|Γ\|** — "Sum of absolute dealer gamma across every strike" from `v_gex_abs_exposure_1pct.abs_gex_cr_1pct` | rendered | **GROSS** |
| `src/components/board/LadderPanel.tsx:22` | tile **Pin (γ-conc)** — `v_gex_strike_rank` rank 1, lead = (share₁−share₂)×100 | rendered | **GROSS** |
| `src/components/board/LadderPanel.tsx:25` | tile **Top-strike share** — `v_gex_concentration.hhi_net`; its own text says "This is max/sum, not a Σshare² index — never call it HHI" | rendered | **GROSS** |
| `src/components/board/LadderPanel.tsx:29` | tile **Net-long γ strike** — `gamma_metrics.max_gamma_strike` | rendered | **INTERPRETATION** |
| `src/pages/Board.tsx` (33 refs), `src/lib/queries.ts` (15), `src/marketview/ui.tsx` (13), `src/marketview/state.ts` (8), `src/pages/Home.tsx` (5), `src/lib/terrain.ts` (5), `src/lib/read.ts` (4), `src/components/board/SplitBar.tsx` (3), `src/pages/Lab3D.tsx` (2), `src/components/board/{StrikeLadder,PinFlowsBody}.tsx`, `src/components/AmbientTrajectory.tsx`, `src/marketview/sections.tsx` | render-layer readers of the above | screen | inherited |

**`src/lib/mockData.ts` (2 refs)** is fixture data, not a live consumer.

## 4. Referenced but **not defined in either tree**

- **`public.latest_gamma_walls`** — appears only in the S104 grant lists
  (`sql/2026-11-03_s104_anon_shrink_ROLLBACK.sql:102`); **no `CREATE` anywhere in
  `sql/`**. Stated plainly: its definition is not in the tree.
- **The Board tiles' own `src` field reads `"sql/ file · COMMENT not live"`** on every
  tile quoted above (`LadderPanel.tsx:19-29`), i.e. the UI itself records that the
  `COMMENT ON VIEW` documenting its source is absent from the database.
- Whether any `sql/` file **reproduces** the live view bodies is **not established**
  here (Rule 25); only `v_gex_strike_rank`, `v_pin_board` and `v_gex_concentration`
  have had their live length/md5 measured (Stage 0 item 4), with no file shown to
  reproduce them.

## 5. Not live — excluded from the list above, named so the exclusion is visible

Backfills, verifiers, replays, tests and research scripts that read the same
quantities: `backfill_s41_p0a_columns_30d.py` (48 refs),
`tests/test_merdian_compute_contract.py` (22), `verify_td_new_3_net_gex_unit.py` (17),
`s31_weekly_attribution_diagnostic.py` (17), `fill_gamma_concentration.py` (16),
`backfill_gamma_metrics_to_main.py` (16), `acceptance_enh133_local.py` (14),
`canonical_no_flip_pipeline_check.py` (13), `tests/test_p3a_invariants.py` (12),
`replay/replay_compute_gamma_metrics.py` (12), `backfill_gamma_metrics_broken_window.py` (9),
`validate_hist_greeks_flat_r.py` (8), `tests/test_dex_recompute.py` (8),
`backfill_hist_greeks.py` (8), `backfill_expiry_outcomes.py` (7),
`phase0b_p5_pinned_proxy_v2.py` (6), and the `sql/snapshots/` captures.

## 6. What a signal or trade decision reads

Traced from the tags above: the only `gex_cr`-derived values that leave the display
layer are **`gamma_metrics.regime`**, **`gamma_zone`**, **`flip_level`**,
**`max_gamma_strike`** and **`pin_risk_score`** (all written by
`compute_gamma_metrics_local.py:423-441`), plus **`gex_cycle_history.pin_state` /
`conviction`**. `v_gex_strike_rank`'s own COMMENT states the GEX layer is
"**Display-only per the S37 GEX-as-context-not-gate ruling; it routes nothing**"
(`sql/2026-09-22_s81_v_gex_strike_rank.sql:258`). Whether the five `gamma_metrics`
fields above gate anything is **not established by this read**.
