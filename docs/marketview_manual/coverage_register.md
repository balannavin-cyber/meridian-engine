# Marketview coverage register

**Version:** v0.1, inventory before prose.
**Board:** meridian-connect `804d684` according to CURRENT.md. The served bundle is `index-CadQe4qO.js` (704,746 B, read 2026-10-12 09:0x IST).
**Live pass 1:** 2026-10-12 09:00–09:12 IST, before the open. Both symbols. All six Board sub-tabs, Home, Context, Structure, Health, Settings and `/board/3d`. All 39 drawer registry entries were extracted from the bundle.
**Live pass 2 (market hours):** 2026-10-12 NIFTY 09:41 and SENSEX 09:40 IST. Covered the strip, Overview, Pin, Gamma (one row), OI and Flows. The pass-2 states are listed in the section at the end of this file.
**Pass 3 (after the close):** owed.
**Expiry-day read:** owed (NIFTY 2026-10-13 is dte 0).

**Legend**
- **Documented?**
  - **y** — the meaning is stated in a doc and/or the in-app drawer.
  - **d** — drawer only, no project doc.
  - **n** — neither a doc nor a drawer defines it.
- **Seen** is what pass 1 showed, with symbol (N = NIFTY, S = SENSEX) and time (IST). "—" means not seen in pass 1.
- **Drawer key** is the key in the bundle registry.

## A. Shell and navigation

| # | Surface | Tab / sub-tab | Source | Ruling / ADR | States | Doc? | Seen |
|---|---|---|---|---|---|---|---|
| A1 | Top nav: Home · Board · Context · Structure │ Health · Settings | all | — | PBD A.2; ADR-017 | active tab highlighted | y | both |
| A2 | NIFTY / SENSEX toggle (keys N / S) | all | — | PBD D.5 | NIFTY, SENSEX; switching keeps tab, resets zoom to Near spot | y | both |
| A3 | Board sub-tabs Overview · Pin · Gamma · OI · Flows · IV (keys 1–6) | Board | — | PBD A.5–A.6; S92 consequence (numbers removed) | selected tab = filled chip | y | all six, both |
| A4 | Zoom: Near spot `0` · All levels `L` · Full chain `F` · `+` / `−` | Board (not IV) | — | PBD D.2 | Near spot (default), All levels, Full chain, Custom | y | IV tab shows `+ −` without the three modes |
| A5 | Drawer (detail panel): tab · title · unit · source line · WHAT IT IS · HOW TO READ IT · COMPUTED · SCALE · CAVEAT · READ IT WITH | Board | bundle registry, 39 keys | PBD A.5 | open on selection; READ IT WITH chips jump | y | yes |
| A6 | Drawer source line: "sql/ file · COMMENT not live" / "‹view› · COMMENT live" / "derived" / view name | Board | registry `src` | PBD B conventions, E-12 | three forms | y | yes |
| A7 | Route `/board/overview` | — | — | — | **404** | n | 404 at 09:0x |
| A8 | Keyboard: `/` strike search, Space freeze, `?` key list, J/K | Board/Context | — | PBD D.6 | — | y | not tested |
| A9 | Hover caption (no tooltips; caption line reads the row) | Board | — | PBD D.3 | — | y | not tested |

## B. Header strip (cells S1–S10)

| # | Surface | Tab | Source | Ruling / ADR | States | Doc? | Seen |
|---|---|---|---|---|---|---|---|
| B1 | SYMBOL · EXPIRY ("15 OCT / SENSEX · 3 DTE") | strip | `gamma_metrics.expiry_date`; `v_iv_term_structure.dte_sessions` leg 1 | PBD B.1 S1 | date · n DTE | y | N 13 OCT · 1 DTE; S 15 OCT · 3 DTE |
| B2 | SPOT + change line + sparkline | strip | `gamma_metrics.spot/ts`; prev close (PBD B.1a) | PBD B.1 S2, B.1a | value; ▲/▼ change; no change line while loading | y | N 22,509.8 ▼−10.7; S 73,181.3 ▲+708.9 |
| B3 | NET Γ + sub-line "short γ · −0.42 of gross · unit definition pending" + split bar | strip | `v_gex_abs_exposure.net_gex_cr / abs_gex_cr` | S94-F; E-D1 | long γ / short γ; net/gross; unit pending | y | N −13.9L Cr / −0.23; S −4.5L / −0.42 |
| B4 | FLIP + "carry unmeasurable" + track tick | strip | `v_gex_repriced_flip.flip / status` | ENH-131; ADR-025 B7 | value ±% · no flip in grid · skipped on expiry day · carry unmeasurable | y | "carry unmeasurable" both |
| B5 | CORRIDOR "72,000–74,000 / inside · 2.73 % wide" + track | strip | `v_gex_strike_walls.put_wall, call_wall, corridor_state` | ENH-120; MV-8 | inside · above call wall · below put wall · undefined | y | N "22,500–22,500 · above call wall · 0.00 % wide"; S inside |
| B6 | PIN (γ-conc) "72,000 / 10.9 % of gross · lead 5.1 pts · ≡ put OI wall" | strip | `v_gex_strike_rank` rank 1–2 | ENH-125; S92-F | value; "no run" | y | N "no run" during load → 22,400 |
| B7 | IV · VIX "16.5 · 14.38 / ◆VIX 0.00 · ±1,017 · ±1.39 %" | strip | `v_iv_term_structure` leg 1; `gamma_metrics.vix`, `.straddle_atm` | PBD B.1 S7 | value · ◆ change line | n ("◆VIX 0.00" undefined) | both read ◆VIX 0.00 |
| B8 | FUT · BASIS "futures from 09:30 / ▲+50.7 · 29 OCT" | strip | `index_futures_snapshots` | PBD B.1a S8 | "futures from 09:30", "futures stale", value | y | "futures from 09:30" both |
| B9 | OPEN · GAP "no pre-open print · prev 72,472" | strip | `market_spot_snapshots` pre-open 09:11, 09:16 bar | PBD B.1a S9 | "no pre-open print", "prev close missing", "final at 09:16", "gap filled" | y | N "prev close missing" during load → "no pre-open print · prev 22,520" |
| B10 | Clock chip "γ hh:mm · chain hh:mm" | strip | `v_gex_strike_walls.ts` vs `v_gex_repriced_flip.ts` | PBD B.1 S10, C.6; MV-2 | shown only when clocks differ > 1 cycle | y | not shown in pass 1 |
| B11 | The read (one sentence under the strip) | Board, Home | composed from strip values | PBD D.4 | states, never predicts | y | e.g. S "sits in a dampening pocket, 1.1 % under the call OI wall…" |

## C. Overview

| # | Surface | Source | Ruling | States | Doc? | Seen |
|---|---|---|---|---|---|---|
| C1 | Net Γ list row + drawer `net` | `v_gex_abs_exposure.net_gex_cr` | S94-F; E-D1 | — | y | both |
| C2 | Flip row + drawer `flip` | `v_gex_repriced_flip.flip` | ENH-131 | as B4 | y | carry unmeasurable |
| C3 | Corridor row + drawer `corridor` | `v_gex_strike_walls` | ENH-120 | as B5 | y | both |
| C4 | Pin (γ-conc) row + drawer `pin` | `v_gex_strike_rank` | ENH-125 | — | y | both |
| C5 | Priced move row "±1,017 / ±1.39 % to expiry" + drawer `priced` | `gamma_metrics.straddle_atm` | PBD B.2 (L16 stand-in, "not σ") | — | y | both |
| C6 | Spot row "Spot · board 09:00" + drawer `spot` | `gamma_metrics.spot` | — | — | y | both |
| C7 | Time to expiry row "3 sess" + drawer `dte` | `v_iv_term_structure.dte_sessions` | — | — | y | both |
| C8 | Ladder: diverging bars "← AMPLIFYING · DAMPENING →", NET γ readout column | `gex_strike_snapshots.gex_cr` | L1; S94-F | bar; `·` gap; empty row | y | both (S dense: level rows only) |
| C9 | γ terrain fill | `gex_strike_snapshots` | PBD C.2 (7 %/11 % alpha) | — | y | — |
| C10 | "γ CEILING / FLOOR · pending measurement" toggle (disabled) | none (E-3) | PBD A.6 | pending | y | every tab |
| C11 | Caption "Net gamma is … bars show signed γ per strike." | — | PBD D.3 | — | y | both |

## D. Pin

| # | Surface | Source | Ruling | States | Doc? | Seen |
|---|---|---|---|---|---|---|
| D1 | Header "pin state · previous session 2026-10-09 · front leg" | `v_pin_board` | S92-D; S90-B | previous session / today | d | both |
| D2 | PIN (γ-conc) + drawer `p_pin` | `v_gex_strike_rank` rank 1 | S74; P1 (S94-D) | — | y | N 22,400 10.0 %; S 72,000 10.9 % |
| D3 | PIN STATE "LOCKED · held 28 cycles · 140 min · session … · live · unreconciled" + drawer `p_state` | `v_pin_board` via `core/pin_state.py` | ENH-133; ADR-030; D-6 | NO PIN · SHIFTING · STABLE · LOCKED; live/reconciled | y | N STABLE; S LOCKED; both "unreconciled" for 10-09 |
| D4 | CONVICTION "0.65 · stage 1 · no band (D-6)" + drawer `p_conv` | `gex_cycle_history.conviction` | S92-F; D-5b/c; D-6 | number only | y | N 0.22; S 0.65 |
| D5 | RUNNER-UP "#2/#1 = 0.48" + drawer `p_runner` | `v_gex_strike_rank` rank 2 | D-5a declined | — | y | both |
| D6 | LEAD "5.1 pts" + drawer `p_lead` | rank shares | D-6 | number, no word | y | both |
| D7 | LEADER TODAY "15 changes … 74 cycles · 09:20–15:40" + drawer `p_today` | `v_pin_board.pin_leader_strike` | S90-B | — | y | both (shows 10-09 under "today") |
| D8 | CONCENTRATION (HHI) "0.031 · top-5 share 28.0 %" + drawer `p_hhi` | `gex_cycle_history.conc_hhi`, `top5_share` | ENH-133 | — | y | N 0.047; S 0.031 |
| D9 | PIN BAND "22,600–22,900 · τ-weighted zone (ENH-81)" + drawer `p_band` | `v_gex_strike_pin_zone` | S74 | range; single strike | y | N 22,600–22,900; S "74,000" |
| D10 | PIN DISTANCE "−0.49 % below spot" + drawer `p_dist` | derived | E-2 | — | y | both |
| D11 | LEGACY PIN-RISK SCORE "29/100 · number only · no band (E-D4)" + drawer `p_legacy` | `gamma_metrics.pin_risk_score` | E-D4; L-7 | — | y | N 29; S 31 |
| D12 | Share ladder "SHARE OF GROSS \|γ\| →", RANK · SHARE readouts, "γ-CONC #1", "#2" | `v_gex_strike_rank` | PBD B.3 | top 10 full; rank > 10 faint | y | both |

## E. Gamma

| # | Surface | Source | Ruling | States | Doc? | Seen |
|---|---|---|---|---|---|---|
| E1 | Top-strike share "10.9 % · 3+ DTE bucket · at 72,000" + drawer `g_top` (call/put split block) | `v_gex_concentration.hhi_net/_call/_put` | E-5; "never call it HHI" | dte bucket 0 / 1-2 / 3+ | y | S 10.9 % (calls 9.7, puts 12.9) |
| E2 | Gross \|Γ\| "10.5L Cr" + drawer `g_gross` | `v_gex_abs_exposure.abs_gex_cr` | E-D1 | — | y | S |
| E3 | Net Γ "amplifying · Σ crosses zero 3×" + drawer `g_net` | `v_gex_abs_exposure.net_gex_cr` | S94-F (P2 sentence lives here) | — | y | S |
| E4 | Contributing strikes "161 / 170 · 95 % of stored" + drawer `g_contrib` | `n_contributing / n_strikes` | — | — | y | S |
| E5 | Net-long γ strike "74,000 · +1.12 % from spot · not "near spot"" + drawer `g_netlong` | `gamma_metrics.max_gamma_strike` | ADR-024 Amend A; E-D5 | — | y | S |
| E6 | Net Γ today sparkline "6 runs · 08:30–09:00" + drawer `g_spark` | `gamma_metrics` today | ADR-017 P5 (≥ 3 runs) | hidden < 3 runs | y | S, 6 pre-open runs |
| E7 | Ladder: cumulative Σγ white dots ("cumulative Σγ from top") | GSS | PBD A.6 | — | y | S |
| E8 | GAMMA RIVER "settled net γ per session · history, not today's read · 30 sessions" | `v_gex_net_gamma_river` | ENH-126; ADR-020 | ● settled · ○ incomplete · grey min–max bar · spot line · "0" under a 0-DTE day · dashed break = no data | y | S |
| E9 | "3D ›" link (river, OI, IV) | `/board/3d` | S92-J | — | y | yes |

## F. OI

| # | Surface | Source | Ruling | States | Doc? | Seen |
|---|---|---|---|---|---|---|
| F1 | Max pain "γ clock · pain minimum" + drawer `oi_max` | `v_gex_max_pain` at ladder run_id | ENH-123; E-D2 / P5 (canonical undecided) | — | y | N 22,500; S 72,500 |
| F2 | Distance to max pain "below spot −0.93 %" + drawer `oi_dist` | derived | — | above / below spot | y | both |
| F3 | Call OI wall "calls · right wing" + drawer `oi_callwall` | `v_gex_strike_walls.call_wall` | ENH-120; S94-D (P1 line) | — | y | both |
| F4 | Put OI wall "puts · left wing" + drawer `oi_putwall` | `.put_wall` | as F3 | — | y | both |
| F5 | Total OI "226.5L · calls +86.1L · puts +140.4L" + drawer `oi_total` | Σ oi_call + oi_put | — | — | y | both |
| F6 | ΔOI net row + drawer `oi_delta` | `v_oi_rotation_since_open` | S92-G; ENH-127 | value · "ΔOI · no 09:15 anchor yet" · n/c per strike | y | N "no 09:15 anchor yet" |
| F7 | "ΔOI · n/a (SENSEX · TD-S84-NEW-4)" | none (withheld) | S92-H (standing D3) | fixed string | y | S |
| F8 | Butterfly "← PUT OI · CALL OI →", TOTAL OI readouts | GSS `oi_call/oi_put` | PBD B.5 | — | y | both |
| F9 | Max-pain ink rule + "pain valley" curve | `v_gex_max_pain` | PBD B.5 | — | y | both |
| F10 | ΔOI ticks "ΔOI rose" (cool) / "ΔOI fell" (warm) | `v_oi_rotation_since_open` | S92-G | tick · n/c | y | legend only (N) |

## G. Flows

| # | Surface | Source | Ruling | States | Doc? | Seen |
|---|---|---|---|---|---|---|
| G1 | Bordered badge "flow-vs-book shown on unclassified ΔOI; classification (D-4) not built" | fixed | S96-A D3; S96-I | fixed | y | both |
| G2 | HEDGE FLOW VS SPOT MOVE chart (±0.5/1/2 %, SELL/BUY) | `v_dealer_flow_sim.flow_cr` | MV-1; PBD F6 | — | y | both |
| G3 | "L3 flip not available." | `v_gex_repriced_flip` | MV-12 | flip dashed line / not available | n (string) | both |
| G4 | HEDGE PER 1 % "BUY 4,459 / −1 %: SELL · +1 %: BUY" + drawer `f_hedge` | `v_dealer_flow_sim` | MV-1 | — | y | N 13,886; S 4,459 |
| G5 | ∂Δ/∂t · PER DAY tile + drawer `f_ddt` | `v_gex_greeks_l2_net…time…`; `v_delta_drift_flow_vs_book` | S96-F/G; TD-S96-NEW-1 (caption) | value · "unmeasurable r" · SKIPPED_EXPIRY | y | "unmeasurable r" both |
| G6 | ∂Δ/∂σ · PER VOL PT tile + drawer `f_ddiv` | `…iv_cr_per_volpt` | as G5 | as G5 | y | "unmeasurable r" both |
| G7 | ∂Δ tile sub-line / absent line | `v_delta_drift_flow_vs_book` `*_pre`, `*_flow`, `anchor_ts` | S96-C/G | "from x at pre-open OI · ±y since hh:mm" · "flow · loading" · "no flow on expiry day" · "no flow before 09:15" · "flow · different run — not drawn" | y | "no flow before 09:15" |
| G8 | ∂Δ tile bricks (each tile its own scale) | as G7 | S96-C | solid held · light added · dashed outline removed | y | not drawn (pre-open) |
| G9 | ∂Γ/∂t · PER DAY tile "net / gross — read together" + drawer `f_gdt` | `v_gex_greeks_l2_net` + gross | L7/L8 spec §6 | value · unmeasurable r | y | "unmeasurable r" |
| G10 | ∂Γ/∂σ · PER VOL PT tile + drawer `f_gdiv` | as G9 | as G9 | as G9 | y | "unmeasurable r" |
| G11 | "bar = \|net\| ÷ gross" (γ-pair bar) | as G9 | — | — | d | yes |
| G12 | EXPIRY LEG "15 OCT · chain 09:05" + drawer `f_leg` | `v_gex_greeks_l2_net` | — | OK · SKIPPED_EXPIRY · UNMEASURABLE_R · NO_LEGS | y | both |
| G13 | NET DEX · OI PROXY "−3,200 Cr · gap 19,980 of 2,45,42,240 qty" + drawer `f_dex_net` | `v_dex_standing_book.leg_net_dex_cr`, `leg_gap_oi_qty` | S94-G/H/I; ENH-140 | value + gap | y | N −8,289; S −3,200 (10-09 settled) |
| G14 | CALL DEX tile + drawer `f_dex_call` | `.leg_call_dex_cr` | as G13 | — | y | N +87,880; S +19,138 |
| G15 | PUT DEX tile + drawer `f_dex_put` | `.leg_put_dex_cr` | as G13 | — | y | N −96,170; S −22,338 |
| G16 | DEX sub-line "calls +, puts − · front leg 15 OCT · 6 cal d · settled 15:10" | `v_dex_standing_book` | ENH-140 | — | d | both ("6 cal d" / "4 cal d" = days from the 10-09 settled run) |
| G17 | DEX flow line | `v_dex_flow_vs_book` | S96-C | as G7 minus the expiry string | y | "no flow before 09:15" |
| G18 | DEX bricks (one scale across the three tiles) | `v_dex_flow_vs_book` | S96-C | held / added / removed; `·` gap; zero crossing | y | not drawn |
| G19 | DEX gap caption "N qty of ΔOI has no published delta and is not counted; this does not say who bought or wrote." (+ no-anchor sentence) | `leg_gap_d_oi_qty`, `leg_no_anchor_oi_qty` | S96-C; DEXb §4c | shown / omitted when null | y | not drawn |
| G20 | Flow-vs-book chip on Net DEX | `flow_book_badge`, `flow_book_abstain_code` | S96-B/D/E | "flow since hh:mm · same sign as book" · "… · against book" · no-badge lines UNTRADED / ZERO_NET / DELTA_SET · PRE_OPEN draws nothing | y | not drawn |
| G21 | ZERO-Δ LEVEL · S* tile + drawer `f_dex_zero` | `v_dex_repriced_zero.zero_delta, status` | ENH-141; S94-H | value · "r unmeasurable" · not computed on expiry day | y | "r unmeasurable" both |
| G22 | S* dotted ladder rule | as G21 | ENH-141 | — | y | not drawn |
| G23 | Flows ladder "← NEGATIVE · POSITIVE →", CR, layer note "bars · ∂Δ/∂t · 15 OCT leg · chain 09:05" | layer view | DEXb §4g | per layer; `·`; empty track | y | both |
| G24 | Flows ladder layer selector (DEX net/call/put, ∂Δ/∂t, ∂Δ/∂σ, ∂Γ/∂t, ∂Γ/∂σ) | — | — | — | y | selector not exercised |
| G25 | Ladder caption gap sentence (∂Δ layers) "… has no priced greek and is not counted…" | `v_delta_drift_flow_vs_book` gap | DD §4.3 | shown / omitted | y | not drawn |
| G26 | L7/L8 captions "Dealer delta-notional drifts…" / "A +1 IV point moves dealer delta-notional…" | fixed | **TD-S96-NEW-1 (under review)** | — | y | not seen in pass 1 (r unmeasurable) |
| G27 | Flows read sentence "For a +1 % move dealers would buy about ₹… Cr…" | `v_dealer_flow_sim` | MV-1; P2 | — | n | both |

## H. IV

| # | Surface | Source | Ruling | States | Doc? | Seen |
|---|---|---|---|---|---|---|
| H1 | "chain clock · 12 Oct 09:05 IST" | `v_iv_term_structure.ts` | PBD C.7 | — | y | both |
| H2 | Term structure "front vs back · 2 legs captured" + "BACKWARDATION · slope −2.44 vol pts" | `v_iv_term_structure.term_slope, is_back` | PBD B.7 (no Normal/Flat/Inverted word) | BACKWARDATION · (contango word unobserved) | n (PBD forbids a regime word) | both "BACKWARDATION" |
| H3 | W1 · FRONT card: ATM IV, ATM strike, CE / PE IV | leg 1 | ENH-130 | — | y | both |
| H4 | W2 · BACK card | leg 2 | ENH-130 | — | y | both |
| H5 | SPREAD VS FRONT | `spread_vs_front` | — | — | y | both |
| H6 | FWD VOL FROM PREV (blank on W1) | `fwd_vol_from_prev` | defined on leg 2 only | blank / value | y | both |
| H7 | "data quality · CE−PE parity gap +3.35 vol pts" | `parity_gap` | — | — | y | both |
| H8 | IV smile chart, W1 front / W2 back toggle, ◀ + − ▶ full | `v_iv_surface` | ENH-132 | — | y | both |
| H9 | Smile marks: ● PE side (grey) · ● CE side (light) · ◯ ATM · ┆ K98 (server skew strike) · ▏ OTM absent | `side_used, quote_state, leg_k98` | PBD A.6 | OTM_QUOTED / OTM_ABSENT | y | both |
| H10 | "skew 98 +2.71 vol pts @ 71,200" | `leg_skew_98, leg_k98` | — | value · "skipped · expiry day" | y | both |
| H11 | "zero-OI (quoted) excluded · 30 strikes" | — | — | — | n | both |
| H12 | "skew from view · not recomputed" | — | parity contract (client recompute retired) | — | y | both |
| H13 | IV tab drawers | — | — | **no IV keys in the drawer registry** | n | — |

## I. Visual grammar (cross-tab)

| # | Surface | Ruling | States | Doc? | Seen |
|---|---|---|---|---|---|
| I1 | Hue: cool = positive sign; warm = negative sign | PBD C.2 | — | y | yes |
| I2 | Greys: calls light, puts mid | PBD C.2 | — | y | OI, IV |
| I3 | Pale gold = selection / active zoom only | PBD C.2 | — | y | yes |
| I4 | Stale strip (alert red), never inside a chart | PBD C.2; ADR-017 P3 | — | y | not seen |
| I5 | Spot rule: solid ink 2 px with glow + SPOT pill | PBD C.4 | — | y | yes |
| I6 | Flip rule: dashed 1 px + FLIP pill | PBD C.4 | drawn / absent | y | absent (carry unmeasurable) |
| I7 | OI wall rules: solid 1 px + CALL / PUT OI WALL pills | PBD C.4 | — | y | yes |
| I8 | Dotted rules: γ-CONC, NET-LONG γ, K98, S* | PBD C.4; ENH-141 | — | y | γ-CONC, NET-LONG γ |
| I9 | Max-pain rule (ink) | PBD C.4 proposes dash-dot; the drawer says "ink rule" | — | y | yes |
| I10 | Coincidence pill "≡" (e.g. "PUT OI WALL ≡ γ-CONC", "CALL OI WALL ≡ PUT OI WALL") | PBD C.4 (S81) | — | y | both |
| I11 | Left gutter: priced-move bracket | PBD A.5 | — | y | yes |
| I12 | Right gutter: pin band | PBD A.5 | — | y | yes |
| I13 | Bricks: solid / light / dashed outline | S96-C | — | y | not drawn |
| I14 | `·` gap marker (never 0) | NULL-is-a-gap; PBD C.6 | — | y | — |
| I15 | Dashed break in a series = no data | ADR-020; PBD C.6 | — | y | river legend |
| I16 | Named-absence chip (dashed outline, plain words) | PBD C.6 | — | y | e.g. "pending measurement" |
| I17 | Number formats: L Cr, Indian grouping, true minus | PBD C.7 | — | y | yes |
| I18 | Uppercase Γ in titles ("Net Γ", "Gross \|Γ\|", "∂Γ/∂t") | S92 consequence (γ where CSS uppercased) | — | finding | yes |

## J. 3D route (`/board/3d`)

| # | Surface | Source | Ruling | States | Doc? | Seen |
|---|---|---|---|---|---|---|
| J1 | Modes: 1 γ terrain · 2 IV fence · 3 Pain bowl | `v_gex_strike_terrain` (+ others) | S92-J | — | partial (only terrain named in S92-J) | N γ terrain |
| J2 | Session span "14 sessions · 22 Sept → 12 Oct", "12 Oct · partial" | — | — | partial | n | N |
| J3 | Legend and footnote ("Height = \|net γ\| per strike at each session's settled run (≤ 15:15 IST…)… Holes are missing strikes, never zero.") | — | S92-J | — | y | N |
| J4 | Controls: reset view R · 2D twin Esc · drag / scroll / pinch; "peak \|γ\| … unit pending" | — | — | — | n | N |

## K. Other pages

| # | Surface | Page | Source | Ruling | States | Doc? | Seen |
|---|---|---|---|---|---|---|---|
| K1 | Masthead "NIFTY · 13 OCT · 1 SESSION LEFT / 22,623.9 / γ run 09:05 / +103.5 · +0.46 %" | Home | `gamma_metrics` | PBD A.4 | — | y | N 09:11 |
| K2 | Read sentence | Home | — | PBD D.4 | — | y | N |
| K3 | Six question cards 1–6 with pictures | Home | as each tab | PBD A.4, B.8 | — | y | N |
| K4 | Context line "CONTEXT · DAILY · trend up · aligned · as of 09 Oct ›" | Home | `market_environment_snapshots` | PBD A.4 | — | partial | N |
| K5 | Legacy header strip: LIVE pill · SPOT · NET Γ (full-digit Cr) · MAX Γ · MAX PAIN · PIN SCORE · VIX · EXPIRY "1d 0h" | Context, Structure | `useMvData` (old) | parity contract §2.4 | — | y (contract) | N |
| K6 | WCB "— /100 · coverage 0.0 % · as of 09/10 15:40" | Context | `weighted_constituent_breadth_snapshots` | S90-G | — | y | N |
| K7 | MARKET BREADTH "61 % adv · A/D 1.56 · ↑772 / 494↓" | Context | `market_breadth_intraday` | — | — | n | N |
| K8 | INDIA VIX | Context | — | — | — | n | N |
| K9 | IV SKEW "iv not populated" → "−29.9 % CE · ATM 22,600 · CE 19.8 / PE 13.9" | Context | client recompute (`ivSkewPct`) | parity contract P-list | loading / value | y | N |
| K10 | ICT ZONES — NEAREST TO SPOT, 10 of 40 (tier chip SKIP / TIER2, pattern, src date, range, ±% from mid) | Structure | `ict_zones` | PBD A.8; L-9; E-11 | — | partial | N |
| K11 | TODAY'S SIGNALS — STREAM (time, strike, grade "D", action BUY_PE) | Structure | `signal_snapshots` | S90 ("D" not established) | — | n | N rows 08:30–09:00 |
| K12 | SYSTEM STATUS: OVERALL, WRITER FLEET, TOKEN STATUS | Health | health views | ADR-017 P2; MV-4 | CRITICAL / … | partial | N "CRITICAL", 9/15 |
| K13 | WRITER FRESHNESS table + "outside trading hours — staleness expected" | Health | `script_execution_log` | MV-4 | — | partial | 15 rows |
| K14 | ERROR RATE — LAST 24H; TOP ERRORS | Health | — | — | — | n | "no errors" |
| K15 | Settings sections: Calibration · Capital & sizing · Display · Connections · Manual actions · About | Settings | — | S90-E (read-only) | — | partial | N |
| K16 | Parameter tables (key · value · last changed · reason) + "view full audit log →" | Settings | `merdian_parameters`, `v_merdian_parameter_audit` | ADR-016; ENH-83 | — | y | N |

## Pass 2 observations (2026-10-12 · NIFTY 09:41 · SENSEX 09:40 IST)

States first seen in this pass:

| Row | State seen |
|---|---|
| B2 | "SPOT · LIVE 09:41 · … · board 09:35 @ 22,538.4" — live tick and board spot shown side by side |
| B3 | NIFTY "+9.2L Cr · long γ · 0.10 of gross"; SENSEX "+5,444 Cr · long γ · 0.00 of gross" |
| B4 | still "carry unmeasurable" on both (F-16) |
| B5 | NIFTY "22,500–22,600 · inside · 0.44 % wide" |
| B8 | "22,570 · +56.3 · ▼−18.3 · 27 OCT" |
| B9 | "▲+0.50 % · pre-open 22,593 · final 22,633 · prev 22,520 · gap filled" |
| B10 | CLOCKS shown: NIFTY "γ 09:35 · chain 09:40 · 5 min apart"; SENSEX "γ 09:30 · chain 09:40 · 10 min apart" |
| D1 | "pin state · this session · front leg" |
| D3 | NIFTY "SHIFTING · held 3 cycles · 15 min · live · unreconciled" |
| D7 | "1 change · 22,500 → 22,700 · 4 cycles · 09:20–09:35" |
| E1 | dte bucket "1-2" (NIFTY) |
| F6 | "C +798.9L · P +361.9L · since 09:15 · chain 09:40" |
| G4 | long-γ hedge: NIFTY "SELL 9,201"; SENSEX "SELL 54" |
| G5–G7 | ∂Δ tiles "unmeasurable r" + "flow · different run — not drawn" (F-16) |
| G13–G17 | drawn: "settled 09:40"; NIFTY "from −15,119 Cr at pre-open OI · +1,829 Cr since 08:30"; SENSEX "from −7,740 · +2,163 since 08:30"; book = pre-open + flow checked (±1 Cr) |
| G18 | bricks drawn (solid / light / dashed outline), SENSEX screenshot |
| G19 | caption shown: NIFTY "28,080 qty of ΔOI has no published delta…"; SENSEX "20 qty…"; no-anchor sentence absent (qty 0) |
| G20 | chip "flow since 08:30 · against book" on both symbols |
| G21 | S* still "r unmeasurable" |
| G23 | note "bars · Net DEX · held / added / removed since 08:30 · settled 09:40" |
| A8 | keys `2`, `3`, `4` switch sub-tabs (verified) |

Screenshots were saved on the operator's machine by the Chrome extension, under `/tmp/claude-chrome-screenshots-4Oopfm/`:

| File | Shows |
|---|---|
| `screenshot-1791778230578-0.jpg` | SENSEX strip + Overview, 09:40 |
| `screenshot-1791778247675-1.jpg` | SENSEX Flows hedge chart + ∂ tiles, 09:40 |
| `screenshot-1791778262692-2.jpg` | SENSEX Flows DEX tiles, chip and bricks ladder, 09:40 |

## Capture pass (2026-10-12, 09:52–10:21 IST)

States first seen in this pass:

| Row | State seen |
|---|---|
| B4 / C2 | Flip has a value: NIFTY "22,497 · −0.08 % from spot" (09:52); "22,453 · −0.15 %" with the ladder pill "SPOT ≡ FLIP" (10:15) |
| B5 | "below put wall" (NIFTY 10:15) |
| B6 / F1 | SENSEX "no run" on PIN, Max pain and Distance to max pain (09:55; F-20) |
| G5–G8 | ∂Δ values and bricks drawn: NIFTY ∂Δ/∂t −39,393 = −25,475 − 13,918; ∂Δ/∂σ +5,210 = 3,232 + 1,978 (chain 09:50) |
| G9–G10 | ∂Γ/∂t −4.7L / 40.5L, ratio −0.12; ∂Γ/∂σ +60,256 / 5.3L, ratio 0.11 |
| G21–G22 | S* "22,533 · +12 pts · +0.06σ above chain spot 22,520.8 · chain 09:50 (book settled 09:50)"; dotted rule drawn |
| G3 | Hedge chart note "Dashed = L3 repriced flip at its distance from spot." (replaces "L3 flip not available.") |
| G26 | Live caption still reads "Dealer delta-notional drifts …"; S97-A rewording is at staging `c0aad8d` |
| I4 | Red stale strip "chain data 12 min old · gamma run 17 min old · Health ›" (F-18) |
| A9 | Hover caption "22,500 · −2.8L Cr · +0.06 % · PUT OI WALL" (verified) |
| K12 | Health at 10:20: CRITICAL, "11/15 · 4 stale" |
| K16 | Settings shows edit pencils on every row (F-17) |

The help pack carries 21 screenshots, listed in `build_help_pack.py` under `SHOTS`. The Health and Settings captures are kept out of the pack because the repo may be public.
