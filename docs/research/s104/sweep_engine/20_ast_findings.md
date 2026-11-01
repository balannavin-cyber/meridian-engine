# 20_ast_findings — Python AST sweep (prompt §3 item 3)

Scope: every tracked `*.py` in `~/meridian-cc` (727 files). `~/meridian-connect` has none.
Method: `ast.parse` on `read_bytes().decode("utf-8-sig")` (CLAUDE.md python-writers rule — a BOM
breaks a bare `read_text` + `ast.parse`), then a NodeVisitor. Three files could not be parsed and
were covered by line-grep only; they are named below, because a parse failure that is not stated
is a silent hole in a "every .py was walked" claim.

Gamma-token test used inside the AST walk:
  `(?i)gex | gamma | _cr\b | _cr_ | zone_signed_mass | total_abs_mass`

## What this sweep CANNOT see (stated with the verdict, per CLAUDE.md)
- **(b)** fires only when the scale literal is a *direct* `BinOp` right operand inside a function
  that elsewhere mentions a Gamma token. A divisor held in a module constant
  (`DIV = 1e7; x = g*oi*s*s/DIV`) would NOT appear. Measured: no such form exists — every
  `/1e7` in the repo is a literal (checked by grepping `= *1e7` and `= *10_000_000` at module
  scope: 0 hits outside `NETGEX_MAX_CR`/`RAW_NET_GEX_THRESHOLD`, which are thresholds, not divisors).
- **(e)** fires only when the Gamma value is a *named function argument*. A threshold on a
  dict value (`row["net_gex"] > 1e9`) or a module constant is invisible to it — and that is
  exactly where the real magnitude thresholds turned out to live. They were found by the
  identifier census and the supplementary pass instead, and are in `50_outbound_and_constants.md`.
- **(d)** uses a 12-line lookback for the relation name. A `select("*")` more than 12 lines below
  its `.from()` would be missed. In TypeScript the same shape DID produce misses — see
  `90_report.md` §5.
- Nothing here sees runtime-constructed attribute access through `**kwargs`, `eval`, or a
  column list read from a file.


files parsed: 724 / 727; parse failures: 3

## PARSE FAILURES (not swept by AST; line-grep only)  (n=3)

| file | why | detail |
|---|---|---|
| backfill_spot_zerodha.py | decode | 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte |
| fix_breadth_inject.py | syntax | line 20: unterminated string literal (detected at line 20) |
| run_spot_timeline_capture.pre_tz_fix_backup.py | syntax | line 1: unterminated string literal (detected at line 1) |

## (b) scale BinOp (/1e7, *100, *0.01 ...) inside a Gamma-touching function  (n=230)

| file | line | function | op | literal | lhs |
|---|---|---|---|---|---|
| accrue_expiry_outcomes.py | 143 | label_if_expiry | * | 100 | (settlement - open_pin) / open_pin |
| accrue_expiry_outcomes.py | 146 | label_if_expiry | * | 100 | (day_high - day_low) / open_spot |
| backfill_expiry_outcomes.py | 186 | label_expiry | * | 100 | (settlement - open_pin) / open_pin |
| backfill_expiry_outcomes.py | 193 | label_expiry | * | 100 | (day_high - day_low) / open_spot |
| backfill_gamma_metrics.py | 83 | signed_gex | / | 10000000.0 | gamma * oi * spot ** 2 |
| backfill_gamma_metrics.py | 154 | process_ts | * | 100 | flip_dist / spot |
| backfill_gamma_metrics_PRE_TD-NEW-3.py | 154 | process_ts | * | 100 | flip_dist / spot |
| backfill_gamma_metrics_broken_window.py | 217 | main | * | 100 | dpct or 0 |
| backfill_gamma_metrics_to_main.py | 224 | _compute_signed_gex_per_strike | / | 10000000.0 | sign * gamma * oi * spot ** 2 |
| backfill_gamma_metrics_to_main.py | 526 | _process_day | * | 100.0 | flip_distance / spot |
| backfill_s41_p0a_columns_30d.py | 109 | compute_pin_risk_score_backfill | / | 100.0 | float(expansion_probability) |
| backfill_shadow_sources_for_date_local.py | 269 | build_options_flow_row | * | 100.0 | gamma_concentration |
| build_hist_pattern_signals_5m.py | 327 | main | * | 100 | (pe_t30 - pe_now) / pe_now |
| build_hist_pattern_signals_5m.py | 332 | main | * | 100 | (ce_t30 - ce_now) / ce_now |
| build_hist_pattern_signals_5m.py | 408 | main | * | 100 | (ct - cn) / cn |
| build_hist_pattern_signals_5m.py | 459 | main | * | 100 | (pt - pn) / pn |
| build_momentum_features_local.phase_b_directional_logic_checkpoint.py | 540 | build_momentum_row | * | 100.0 | (straddle_price - session_vwap) / session_vwap |
| build_momentum_features_local.pre_phase_b_backup.py | 540 | build_momentum_row | * | 100.0 | (straddle_price - session_vwap) / session_vwap |
| build_momentum_features_local_backup_before_session_vwap_fix.py | 457 | build_momentum_row | * | 100.0 | (straddle_price - session_vwap) / session_vwap |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 212 | _classify_directional_edge_state | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 249 | _resolve_direction_bias | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 434 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 833 | _build_signal | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 161 | _resolve_direction_bias | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 338 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 647 | _build_signal | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 145 | _resolve_direction_bias | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 314 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 578 | _build_signal | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 212 | _classify_directional_edge_state | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 238 | _resolve_direction_bias | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 423 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 788 | _build_signal | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_conflict_logic_backup.py | 145 | _resolve_direction_bias | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_conflict_logic_backup.py | 314 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_conflict_logic_backup.py | 578 | _build_signal | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_directional_logic_backup.py | 244 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_insert_fix_backup.py | 145 | _resolve_direction_bias | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_insert_fix_backup.py | 314 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_insert_fix_backup.py | 578 | _build_signal | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_phase_b_backup.py | 218 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_premium_state_backup.py | 161 | _resolve_direction_bias | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_premium_state_backup.py | 338 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_premium_state_backup.py | 647 | _build_signal | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_signal_mode_backup.py | 212 | _classify_directional_edge_state | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_signal_mode_backup.py | 238 | _resolve_direction_bias | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_signal_mode_backup.py | 423 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local.pre_signal_mode_backup.py | 788 | _build_signal | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 212 | _classify_directional_edge_state | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 249 | _resolve_direction_bias | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 434 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 833 | _build_signal | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 212 | _classify_directional_edge_state | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 249 | _resolve_direction_bias | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 434 | _apply_gamma_context | * | 100.0 | abs(flip_distance) / abs(spot) |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 833 | _build_signal | * | 100.0 | abs(flip_distance) / abs(spot) |
| canonical_large_move_baseline.py | 205 | fetch_gamma_range | * | 1000 | page |
| canonical_large_move_baseline.py | 205 | fetch_gamma_range | * | 1000 | page |
| canonical_large_move_baseline.py | 453 | main | * | 100 | CI_LEVEL |
| canonical_large_move_profile.py | 246 | fetch_gamma_range | * | 1000 | page |
| canonical_large_move_profile.py | 246 | fetch_gamma_range | * | 1000 | page |
| canonical_large_move_profile.py | 521 | main | * | 100 | PCR_STRIKE_WINDOW_PCT |
| canonical_no_flip_pipeline_check.py | 85 | fetch_gamma_full | * | 1000 | page |
| canonical_no_flip_pipeline_check.py | 85 | fetch_gamma_full | * | 1000 | page |
| canonical_no_flip_pipeline_check.py | 129 | section_a_monthly_breakdown | * | 100 | monthly['n_no_flip'] / monthly['n_rows'] |
| canonical_no_flip_pipeline_check.py | 130 | section_a_monthly_breakdown | * | 100 | monthly['n_flip_null'] / monthly['n_rows'] |
| canonical_no_flip_pipeline_check.py | 250 | section_e_verdict | * | 100 | monthly['n_no_flip'] / monthly['n_rows'] |
| canonical_ob_gamma_scalar.py | 139 | fetch_gamma_metrics | * | 1000 | page |
| canonical_ob_gamma_scalar.py | 139 | fetch_gamma_metrics | * | 1000 | page |
| canonical_ob_gamma_scalar.py | 296 | run_for_symbol | * | 100 | summary['n_match'] / summary['n'] |
| canonical_ob_gamma_scalar.py | 297 | run_for_symbol | * | 100 | summary['n_wrong'] / summary['n'] |
| canonical_ob_gamma_scalar.py | 313 | run_for_symbol | * | 100 | summary_z['n_match'] / summary_z['n'] |
| canonical_ob_gamma_scalar.py | 314 | run_for_symbol | * | 100 | summary_z['n_wrong'] / summary_z['n'] |
| canonical_ob_gamma_zone.py | 204 | compute_gamma_zone | / | 10000000.0 | df['gamma'] * df['oi'] * spot ** 2 * 100.0 |
| canonical_ob_gamma_zone.py | 204 | compute_gamma_zone | * | 100.0 | df['gamma'] * df['oi'] * spot ** 2 |
| canonical_ob_gamma_zone.py | 393 | run_for_symbol | * | 100 | summary['n_match'] / summary['n'] |
| canonical_ob_gamma_zone.py | 394 | run_for_symbol | * | 100 | summary['n_wrong'] / summary['n'] |
| canonical_ob_gamma_zone.py | 420 | main | * | 100 | ZONE_MASS_THRESHOLD |
| canonical_ob_gamma_zone_bs.py | 323 | compute_zone_for_entry | / | 10000000.0 | sign * gamma * float(row['oi']) * spot ** 2 * 100.0 |
| canonical_ob_gamma_zone_bs.py | 323 | compute_zone_for_entry | * | 100.0 | sign * gamma * float(row['oi']) * spot ** 2 |
| canonical_ob_gamma_zone_bs.py | 488 | run_for_symbol | * | 100 | summary['n_match'] / summary['n'] |
| canonical_ob_gamma_zone_bs.py | 489 | run_for_symbol | * | 100 | summary['n_wrong'] / summary['n'] |
| canonical_ob_gamma_zone_bs.py | 531 | main | * | 100 | STRIKE_WINDOW_PCT |
| canonical_ob_gamma_zone_bs.py | 532 | main | * | 100 | ZONE_MASS_THRESHOLD |
| canonical_ob_pcr.py | 367 | main | * | 100 | STRIKE_WINDOW_PCT |
| compute_gamma_metrics_local_PRE_S37.py | 120 | signed_gamma_exposure | / | 10000000.0 | gamma * oi * spot ** 2 |
| compute_gamma_metrics_local_PRE_S37.py | 679 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| compute_gamma_metrics_local_PRE_S37_v2.py | 120 | signed_gamma_exposure | / | 10000000.0 | gamma * oi * spot ** 2 |
| compute_gamma_metrics_local_PRE_S37_v2.py | 679 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| compute_gamma_metrics_local_PRE_S41.py | 120 | signed_gamma_exposure | / | 10000000.0 | gamma * oi * spot ** 2 |
| compute_gamma_metrics_local_PRE_S41.py | 681 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 132 | signed_gamma_exposure | / | 10000000.0 | gamma * oi * spot ** 2 |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 825 | compute_pin_risk_score | / | 100.0 | float(expansion_probability) |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 885 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 120 | signed_gamma_exposure | / | 10000000.0 | gamma * oi * spot ** 2 |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 679 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 120 | signed_gamma_exposure | / | 10000000.0 | gamma * oi * spot ** 2 |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 679 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 612 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 679 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 120 | signed_gamma_exposure | / | 10000000.0 | gamma * oi * spot ** 2 |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 679 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| compute_structural_divergence_local.py | 304 | main | * | 100.0 | (straddle_open - straddle_now) / straddle_open |
| compute_volatility_metrics_local.py | 624 | main | * | 100.0 | vix_change_1d / prev_1d |
| docs/research/s94_priority/p1c/p1c_score.py | 57 | main | / | 100 | s0 * iv0 |
| docs/research/s95_priority/sstar/sstar_gates.py | 117 | arm_inputs | / | 100.0 | spot * atm_iv |
| docs/research/s95_priority/sstar/sstar_gates.py | 91 | arm_inputs | / | 100.0 | iv |
| docs/research/s95_priority/sstar/sstar_gates.py | 258 | score | / | 10000000.0 | (fnum(r['delta']) or 0.0) * (fnum(r['oi']) or 0.0) * inp['spot'] |
| docs/research/s95_priority/sstar/sstar_gates.py | 236 | score | * | 10000000.0 | c[2] |
| experiment_17_bear_ob_gamma_override.py | 207 | main | * | 100 | total_wins / total_n |
| experiment_17_bear_ob_gamma_override.py | 216 | main | * | 100 | lg.get('wins', 0) / lg_n |
| experiment_17_bear_ob_gamma_override.py | 220 | main | * | 100 | sg.get('wins', 0) / sg_n |
| experiment_17_bear_ob_gamma_override.py | 200 | main | * | 100 | wins / n |
| experiment_17_v2.py | 182 | main | * | 100 | total_wins / total_n |
| experiment_17_v2.py | 191 | main | * | 100 | lg.get('wins', 0) / lg_n |
| experiment_17_v2.py | 195 | main | * | 100 | sg.get('wins', 0) / sg_n |
| experiment_17_v2.py | 175 | main | * | 100 | wins / n |
| experiment_18_confluence_rerun.py | 371 | main | * | 100 | with_r.get('rejects', 0) / wn |
| experiment_18_confluence_rerun.py | 372 | main | * | 100 | without_r.get('rejects', 0) / won |
| experiment_18_confluence_rerun.py | 325 | main | * | 100 | breaks / n |
| experiment_18_confluence_rerun.py | 336 | main | * | 100 | g.get('breaks', 0) / gn |
| experiment_18_confluence_rerun.py | 343 | main | * | 100 | g.get('breaks', 0) / gn |
| experiment_18_confluence_rerun.py | 350 | main | * | 100 | g.get('breaks', 0) / gn |
| experiment_18_oi_ict_confluence.py | 429 | main | * | 100 | with_r.get('rejects', 0) / wn |
| experiment_18_oi_ict_confluence.py | 430 | main | * | 100 | without_r.get('rejects', 0) / wor |
| experiment_18_oi_ict_confluence.py | 374 | main | * | 100 | breaks / n |
| experiment_18_oi_ict_confluence.py | 387 | main | * | 100 | g.get('breaks', 0) / gn |
| experiment_18_oi_ict_confluence.py | 397 | main | * | 100 | g.get('breaks', 0) / gn |
| experiment_18_oi_ict_confluence.py | 407 | main | * | 100 | g.get('breaks', 0) / gn |
| experiment_23_sweep_reversal.py | 305 | main | * | 100 | wins / n |
| experiment_23_sweep_reversal.py | 223 | main | * | 100 | (pdl - sweep_low) / pdl |
| experiment_23_sweep_reversal.py | 268 | main | * | 100 | (sweep_high - pdh) / pdh |
| experiment_23_sweep_reversal.py | 324 | main | * | 100 | b['w'] / b['n'] |
| experiment_23_sweep_reversal.py | 336 | main | * | 100 | b['w'] / b['n'] |
| experiment_23_sweep_reversal.py | 346 | main | * | 100 | b['w'] / b['n'] |
| experiment_23_sweep_reversal.py | 305 | analyse_group | * | 100 | wins / n |
| experiment_23_sweep_reversal.py | 324 | analyse_group | * | 100 | b['w'] / b['n'] |
| experiment_23_sweep_reversal.py | 336 | analyse_group | * | 100 | b['w'] / b['n'] |
| experiment_23_sweep_reversal.py | 346 | analyse_group | * | 100 | b['w'] / b['n'] |
| experiment_23b_sweep_htf_confluence.py | 350 | main | * | 100 | wins / n |
| experiment_23b_sweep_htf_confluence.py | 377 | main | * | 100 | w / n |
| experiment_23b_sweep_htf_confluence.py | 247 | main | * | 100 | (pdl - sweep_low) / pdl |
| experiment_23b_sweep_htf_confluence.py | 304 | main | * | 100 | (sweep_high - pdh) / pdh |
| experiment_23c_sweep_quality.py | 533 | main | * | 100 | hw / len(high_q) |
| experiment_23c_sweep_quality.py | 486 | main | * | 100 | sw / len(sub) |
| experiment_23c_sweep_quality.py | 487 | main | * | 100 | sum((1 for s in sub if s['wick_quality'])) / len(sub) |
| experiment_23c_sweep_quality.py | 488 | main | * | 100 | sum((1 for s in sub if s['zone_age'] <= ZONE_AGE_MAX)) / len(sub) |
| experiment_23c_sweep_quality.py | 489 | main | * | 100 | sum((1 for s in sub if s['precise'])) / len(sub) |
| experiment_23c_sweep_quality.py | 490 | main | * | 100 | sum((1 for s in sub if s['displaced'])) / len(sub) |
| experiment_23c_sweep_quality.py | 554 | main | * | 100 | WICK_RATIO_MIN |
| experiment_23c_sweep_quality.py | 556 | main | * | 100 | PRECISION_MAX |
| experiment_23c_sweep_quality.py | 474 | main | * | 100 | wins / len(with_ret) |
| experiment_23c_sweep_quality.py | 350 | main | * | 100 | (pdl - sweep_low) / pdl |
| experiment_23c_sweep_quality.py | 433 | main | * | 100 | (sweep_high - pdh) / pdh |
| experiment_23c_sweep_quality.py | 513 | main | * | 100 | yw / len(yes) |
| experiment_23c_sweep_quality.py | 514 | main | * | 100 | sum((1 for s in no if s['win_30m'])) / len(no) |
| experiment_26_option_wick_reversal.py | 256 | main | * | 100 | PE_WICK_MIN |
| experiment_26_option_wick_reversal.py | 262 | main | * | 100 | PE_WICK_MIN |
| experiment_26_option_wick_reversal.py | 288 | main | * | 100 | CE_WICK_MIN |
| experiment_26_option_wick_reversal.py | 293 | main | * | 100 | CE_WICK_MIN |
| experiment_26_option_wick_reversal.py | 320 | main | * | 100 | PE_WICK_MIN |
| experiment_27_premium_ict.py | 221 | main | * | 100 | (pc - min_future) / pc |
| experiment_27_premium_ict.py | 377 | main | * | 100 | (cc - min(future_closes)) / cc |
| experiment_27_premium_ict.py | 267 | main | * | 100 | (pe_t30 - ret_pc) / ret_pc |
| experiment_27_premium_ict.py | 334 | main | * | 100 | (pe_t30 - pc) / pc |
| experiment_27_premium_ict.py | 405 | main | * | 100 | (ce_t30 - ret_cc) / ret_cc |
| experiment_27_premium_ict.py | 350 | main | * | 100 | (ph - pc) / ph |
| experiment_27_premium_ict.py | 322 | main | / | 100 | SWEEP_MIN_PCT |
| experiment_27b_premium_small_sweep.py | 241 | main | * | 100 | (pe_t30 - pc) / pc |
| experiment_27b_premium_small_sweep.py | 321 | main | * | 100 | (ce_t30 - cc) / cc |
| experiment_27b_premium_small_sweep.py | 265 | main | * | 100 | sweep_pct |
| experiment_27b_premium_small_sweep.py | 341 | main | * | 100 | sweep_pct |
| experiment_35b_po3_first_sweep_deep_drill.py | 278 | detect_events | * | 100 | (high - pdh) / pdh |
| experiment_35b_po3_first_sweep_deep_drill.py | 330 | detect_events | * | 100 | (pdl - low) / pdl |
| generate_pine_overlay.py | 334 | _pine_positioning_render | / | 1000 | pin['peak_gex_cr'] |
| generate_pine_overlay.py | 335 | _pine_positioning_render | / | 1000 | pin['total_gex_cr'] |
| generate_pine_overlay.py | 363 | _pine_positioning_render | / | 1000 | accel['trough_gex_cr'] |
| generate_pine_overlay.py | 364 | _pine_positioning_render | / | 1000 | accel['total_gex_cr'] |
| generate_pine_overlay_PRE_S37_ENH81_v2.py | 205 | _pine_positioning_render | / | 1000 | pin['peak_gex_cr'] |
| generate_pine_overlay_PRE_S37_ENH81_v2.py | 225 | _pine_positioning_render | / | 1000 | accel['trough_gex_cr'] |
| generate_pine_overlay_PRE_S41_BOXCOUNT.py | 220 | _pine_positioning_render | / | 1000 | pin['peak_gex_cr'] |
| generate_pine_overlay_PRE_S41_BOXCOUNT.py | 246 | _pine_positioning_render | / | 1000 | accel['trough_gex_cr'] |
| generate_pine_overlay_PRE_S41_COLOR.py | 220 | _pine_positioning_render | / | 1000 | pin['peak_gex_cr'] |
| generate_pine_overlay_PRE_S41_COLOR.py | 246 | _pine_positioning_render | / | 1000 | accel['trough_gex_cr'] |
| measure_rate_sensitivity.py | 107 | signed_gamma_exposure | / | 10000000.0 | gamma * oi * spot ** 2 |
| measure_rate_sensitivity.py | 286 | _measure_one | * | 100 | rb |
| merdian_compute/gamma.py | 54 | signed_gamma_exposure | / | 10000000.0 | gamma * oi * spot ** 2 |
| merdian_compute/gamma.py | 623 | compute_pin_risk_score | / | 100.0 | float(expansion_probability) |
| merdian_compute/gamma.py | 825 | compute_gamma_core | * | 100.0 | abs(flip_distance) / spot |
| merdian_live_dashboard.py | 411 | get_pipeline_stages | * | 100 | ret_s |
| merdian_live_dashboard_PRE_S25.py | 324 | get_pipeline_stages | * | 100 | ret_s |
| merdian_live_dashboard_PRE_S25b.py | 411 | get_pipeline_stages | * | 100 | ret_s |
| phase0b_p5_pinned_proxy.py | 220 | main | * | 100 | (xpf - epf) / epf |
| phase0b_p5_pinned_proxy.py | 253 | main | * | 100 | wins / n |
| phase0b_p5_pinned_proxy.py | 268 | main | * | 100 | wins / n |
| phase0b_p5_pinned_proxy_v2.py | 259 | main | * | 100 | (xpf - epf) / epf |
| phase0b_p5_pinned_proxy_v2.py | 290 | main | * | 100 | enr / sigs |
| phase0b_p5_pinned_proxy_v2.py | 305 | main | * | 100 | wins / n |
| phase0b_p5_pinned_proxy_v2.py | 320 | main | * | 100 | wins / n |
| premium_outcome_writer.py | 710 | evaluate_signal | * | 100 | entry_premium / entry_spot |
| replay/replay_compute_gamma_metrics.py | 88 | signed_gamma_exposure | / | 10000000.0 | gamma * oi * spot ** 2 |
| replay/replay_compute_gamma_metrics.py | 491 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 491 | compute_gamma_metrics | * | 100.0 | abs(flip_distance) / spot |
| run_validation_analysis.py | 501 | main | * | 100 | '-' |
| s30_path1_live_cohort_pnl.py | 202 | main | * | 100 | (xpf - epf) / epf |
| s30_path1_live_cohort_pnl.py | 257 | main | * | 100 | '=' |
| s30_path1_live_cohort_pnl.py | 259 | main | * | 100 | '=' |
| s30_path1_live_cohort_pnl.py | 336 | main | * | 100 | '=' |
| s30_path1_live_cohort_pnl.py | 244 | main | * | 100 | wins / n |
| s30_path1_live_cohort_pnl.py | 314 | main | * | 100 | cum_abs / abs_total |
| s30_path1_live_cohort_pnl.py | 313 | main | * | 100 | ab / abs_total |
| s30_target_days_audit.py | 276 | main | * | 100 | wins / len(sr) |
| s30_target_days_audit.py | 278 | main | * | 100 | blocked / len(sr) |
| s30_target_days_audit.py | 284 | main | * | 100 | wins / len(priced) |
| s30_target_days_audit.py | 241 | main | * | 100 | wins / len(priced) |
| s31_weekly_attribution_diagnostic.py | 441 | weekly_rollup | * | 100.0 | n_tag_bull / n_zt_bull |
| s31_weekly_attribution_diagnostic.py | 442 | weekly_rollup | * | 100.0 | n_tag_bear / n_zt_bear |
| s31_weekly_attribution_diagnostic.py | 435 | weekly_rollup | * | 100.0 | float(g[c].mean()) |
| s31_weekly_attribution_diagnostic.py | 477 | weekly_rollup | * | 100.0 | sig_reg_dist.get('LONG_GAMMA', 0.0) |
| s31_weekly_attribution_diagnostic.py | 478 | weekly_rollup | * | 100.0 | sig_reg_dist.get('SHORT_GAMMA', 0.0) |
| s31_weekly_attribution_diagnostic.py | 479 | weekly_rollup | * | 100.0 | sig_reg_dist.get('NO_FLIP', 0.0) |
| s31_weekly_attribution_diagnostic.py | 480 | weekly_rollup | * | 100.0 | reg_dist.get('LONG_GAMMA', 0.0) |
| s31_weekly_attribution_diagnostic.py | 481 | weekly_rollup | * | 100.0 | reg_dist.get('SHORT_GAMMA', 0.0) |
| s31_weekly_attribution_diagnostic.py | 482 | weekly_rollup | * | 100.0 | reg_dist.get('NO_FLIP', 0.0) |
| s31_weekly_attribution_diagnostic.py | 432 | weekly_rollup | * | 100.0 | v.mean() |
| s31_weekly_attribution_diagnostic.py | 465 | weekly_rollup | * | 100.0 | float(g['trade_allowed'].mean()) |
| scripts/eod_health_check.py | 550 | main | / | 100.0 | tot * PRIMARY_PARITY_TOL_PCT |
| tests/test_p3a_invariants.py | 38 | recompute | / | 10000000.0 | gamma * oi * spot * spot |
| verify_td_new_2_flip_level.py | 153 | verify_cycle | * | 100 | abs(dist_pts) / spot |
| verify_td_new_2_flip_level.py | 163 | verify_cycle | * | 100 | abs(delta) / live_flip |

## (c) column names built at run time near a Gamma token  (n=385)

| file | line | form | text |
|---|---|---|---|
| accrue_expiry_outcomes.py | 111 | f-string | log(f"{symbol}: no gamma_metrics for {as_of} — SKIP") |
| backfill_gamma_metrics.py | 90 | dynamic-get | strike_gex[s]=strike_gex.get(s,0)+r["_gex"] |
| backfill_gamma_metrics.py | 133 | f-string | rows=sb_get("hist_gamma_metrics",f"symbol=eq.{symbol}&trade_date=eq.{trade_date}&select=id&limit=1") |
| backfill_gamma_metrics.py | 174 | f-string | print(f"{'='*72}\nBACKFILL GAMMA METRICS — {symbol} — {trade_date}\n{'='*72}") |
| backfill_gamma_metrics.py | 202 | f-string | print(f"Upserted: {inserted} rows\nBACKFILL GAMMA METRICS COMPLETE") |
| backfill_gamma_metrics_PRE_TD-NEW-3.py | 90 | dynamic-get | strike_gex[s]=strike_gex.get(s,0)+r["_gex"] |
| backfill_gamma_metrics_PRE_TD-NEW-3.py | 133 | f-string | rows=sb_get("hist_gamma_metrics",f"symbol=eq.{symbol}&trade_date=eq.{trade_date}&select=id&limit=1") |
| backfill_gamma_metrics_PRE_TD-NEW-3.py | 174 | f-string | print(f"{'='*72}\nBACKFILL GAMMA METRICS — {symbol} — {trade_date}\n{'='*72}") |
| backfill_gamma_metrics_PRE_TD-NEW-3.py | 202 | f-string | print(f"Upserted: {inserted} rows\nBACKFILL GAMMA METRICS COMPLETE") |
| backfill_gamma_metrics_broken_window.py | 197 | f-string | print(f"{'#':>5} {'ts':<26} {'sym':<6} {'spot':>10} {'flip':>10} {'Δ%':>8} {'net_gex_Cr':>14} {'regime':<8} gates") |
| backfill_hist_greeks.py | 336 | f-string | print(f"{d}: no live gamma_metrics"); continue |
| backfill_market_state.py | 215 | f-string | print(f"Gamma rows: {len(gamma_rows)}") |
| backfill_s41_p0a_columns_30d.py | 193 | f-string | print(f"Reading gex_strike_snapshots: ts >= {window_start_iso}, gex_cr > 0, symbol in {symbols}") |
| backfill_s41_p0a_columns_30d.py | 207 | f-string | print(f"  {sym}: {len(rows)} positive-GEX rows fetched") |
| backfill_s41_p0a_columns_30d.py | 224 | f-string | print(f"[DRY-RUN] Would UPDATE {len(pin_strikes)} gamma_metrics rows with max_gamma_strike") |
| backfill_s41_p0a_columns_30d.py | 227 | f-string | print(f"  {sym} {ts} -> max_gamma_strike={strike}") |
| backfill_s41_p0a_columns_30d.py | 333 | f-string | print(f"[DRY-RUN] Would UPDATE gamma_metrics.vix across ~{len(bars)} 5-min windows") |
| backfill_s41_p0a_columns_30d.py | 361 | f-string | print(f"[APPLY] Phase B complete: {updates} gamma_metrics rows updated, {errors} bar errors") |
| backfill_s41_p0a_columns_30d.py | 383 | f-string | print(f"Reading gamma_metrics rows: ts >= {window_start_iso}, symbol in {symbols}") |
| backfill_s41_p0a_columns_30d.py | 396 | f-string | print(f"  {sym}: {len(rows)} gamma_metrics rows") |
| backfill_s41_p0a_columns_30d.py | 458 | f-string | print(f"Recomputing pin_risk_score for {len(gm_rows)} gamma_metrics rows...") |
| backfill_s41_p0a_columns_30d.py | 521 | f-string | print(f"[DRY-RUN] Would UPDATE {updates_planned} gamma_metrics rows with pin_risk_score") |
| backfill_s41_p0a_columns_30d.py | 538 | f-string | print(f"[WARN] gex_strike_snapshots floor detection failed: {e}") |
| backfill_s41_p0a_columns_30d.py | 568 | f-string | print(f"gex_strike_snapshots earliest ts: {gss_floor.isoformat()}") |
| batch_backfill_gamma.py | 58 | f-string | rows = sb_get("hist_gamma_metrics", f"symbol=eq.{symbol}&select=trade_date&limit=5000") |
| build_market_state_snapshot_local.phase_b_directional_logic_checkpoint.py | 72 | f-string | raise RuntimeError(f"No gamma_metrics row found for symbol={symbol}") |
| build_market_state_snapshot_local.pre_phase_b_backup.py | 57 | f-string | raise RuntimeError(f"No gamma_metrics row found for symbol={symbol}") |
| build_market_state_snapshot_local.pre_vix_enrichment_backup.py | 325 | f-string | raise RuntimeError(f"No gamma row found for symbol={symbol}") |
| build_market_state_snapshot_local.pre_vix_enrichment_backup.py | 528 | f-string | print(f"Gamma source table:       {gamma_table}") |
| build_market_state_snapshot_local.py | 362 | f-string | error_message=f"gamma_metrics fetch failed: {e}", |
| build_market_state_snapshot_local.py | 369 | f-string | error_message=f"No gamma_metrics row found for {symbol}. " |
| build_market_state_snapshot_local.py | 467 | f-string | print(f"Gamma regime:             {gamma_features.get('gamma_regime')}") |
| build_market_state_snapshot_local.py | 468 | f-string | print(f"Flip distance pct:        {gamma_features.get('flip_distance_pct')}") |
| build_market_state_snapshot_local.py | 469 | f-string | print(f"Flip distance points:     {gamma_features.get('flip_distance_points')}") |
| build_market_state_snapshot_local_PRE_WCB_BACKUP.py | 72 | f-string | raise RuntimeError(f"No gamma_metrics row found for symbol={symbol}") |
| build_market_state_snapshot_local_PRE_WCB_SCHEMA_FIX.py | 364 | f-string | raise RuntimeError(f"No gamma row found for symbol={symbol}") |
| build_market_state_snapshot_local_PRE_WCB_SCHEMA_FIX.py | 571 | f-string | print(f"Gamma source table:       {gamma_table}") |
| build_momentum_features_local.phase_b_directional_logic_checkpoint.py | 509 | f-string | raise RuntimeError(f"No gamma_metrics row found for {symbol}") |
| build_momentum_features_local.phase_b_directional_logic_checkpoint.py | 514 | f-string | raise RuntimeError(f"Gamma row missing expiry_date/spot for {symbol}: {gamma_row}") |
| build_momentum_features_local.pre_phase_b_backup.py | 509 | f-string | raise RuntimeError(f"No gamma_metrics row found for {symbol}") |
| build_momentum_features_local.pre_phase_b_backup.py | 514 | f-string | raise RuntimeError(f"Gamma row missing expiry_date/spot for {symbol}: {gamma_row}") |
| build_momentum_features_local_backup_before_session_vwap_fix.py | 431 | f-string | raise RuntimeError(f"No gamma_metrics row found for {symbol}") |
| build_momentum_features_local_backup_before_session_vwap_fix.py | 436 | f-string | raise RuntimeError(f"Gamma row missing expiry_date/spot for {symbol}: {gamma_row}") |
| build_shadow_signal_v3_local.py | 206 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_shadow_state_signal_local.py | 58 | f-string | rationale_parts.append(f"gamma_bias={gamma_bias or 'UNKNOWN'}") |
| build_shadow_state_signal_local.py | 229 | f-string | print(f"gamma_bias:              {shadow_row['gamma_bias']}") |
| build_shadow_state_signal_local.py | 230 | f-string | print(f"gamma_zone:              {shadow_row['gamma_zone']}") |
| build_signal_state_snapshot_local.py | 318 | f-string | print(f"gamma_bias:            {gamma_bias}") |
| build_signal_state_snapshot_local.py | 319 | f-string | print(f"gamma_zone:            {gamma_zone}") |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 725 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 554 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 500 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 688 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.pre_conflict_logic_backup.py | 500 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.pre_directional_logic_backup.py | 413 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.pre_insert_fix_backup.py | 500 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.pre_phase_b_backup.py | 367 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.pre_premium_state_backup.py | 554 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.pre_signal_mode_backup.py | 688 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.py | 559 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local.py | 1345 | f-string | print(f"gamma_regime={row.get('gamma_regime')}") |
| build_trade_signal_local_PRE_S26_ENH55DISABLE.py | 491 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local_PRE_S26_ENH55DISABLE.py | 1207 | f-string | print(f"gamma_regime={row.get('gamma_regime')}") |
| build_trade_signal_local_PRE_S26_ENH88.py | 440 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local_PRE_S26_ENH88.py | 1119 | f-string | print(f"gamma_regime={row.get('gamma_regime')}") |
| build_trade_signal_local_PRE_S30.py | 498 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local_PRE_S30.py | 1214 | f-string | print(f"gamma_regime={row.get('gamma_regime')}") |
| build_trade_signal_local_PRE_S31B.py | 513 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local_PRE_S31B.py | 1239 | f-string | print(f"gamma_regime={row.get('gamma_regime')}") |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 725 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 725 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| canonical_large_move_baseline.py | 434 | f-string | print(f"  gamma_metrics for window: {len(gamma)} rows") |
| canonical_large_move_baseline.py | 436 | dynamic-get | baseline = attach_snapshot_features(sb, baseline, inst_ids.get(sym), gamma, sym) |
| canonical_large_move_baseline.py | 524 | f-string | print_test(buf, f"LONG_GAMMA -> SHORT_GAMMA flip ({direction})", res, fmt="{:.3f}") |
| canonical_large_move_profile.py | 551 | f-string | print(f"  gamma_metrics for window: {len(gamma)} rows") |
| canonical_large_move_profile.py | 553 | dynamic-get | ev = attach_snapshot_features(sb, ev, sym, inst_ids.get(sym), gamma) |
| canonical_no_flip_falsify.py | 310 | f-string | detail_files = sorted(OUT_DIR.glob(f"ob_gamma_scalar_detail_*_{run_tag}.csv")) |
| canonical_no_flip_falsify.py | 312 | f-string | sys.exit(f"ERROR: no detail CSVs for run {run_tag}; run canonical_ob_gamma_scalar.py first") |
| canonical_no_flip_pipeline_check.py | 76 | f-string | print(f"  [{symbol}] fetching gamma_metrics ...", end="", flush=True) |
| canonical_no_flip_pipeline_check.py | 142 | f-string | emit(buf, f"  log10 median \|net_gex\| range across months: [{log_min:.1f}, {log_max:.1f}]") |
| canonical_no_flip_pipeline_check.py | 271 | f-string | emit(buf, f"  \|net_gex\| median: pre {pre_mag:.2e}      -> post {post_mag:.2e}      " |
| canonical_ob_gamma_scalar.py | 130 | f-string | print(f"  [{symbol}] fetching gamma_metrics {start_ist.date()}..{end_ist.date()}", |
| canonical_ob_gamma_scalar.py | 270 | f-string | print(f"  gamma_metrics range : {gamma['ist'].min()} -> {gamma['ist'].max()}") |
| canonical_ob_gamma_scalar.py | 272 | f-string | print(f"  regime distribution in raw gamma : {regime_counts}") |
| canonical_ob_gamma_scalar.py | 282 | f-string | entries.to_csv(OUT_DIR / f"ob_gamma_scalar_detail_{symbol}_{run_tag}.csv", index=False) |
| canonical_ob_gamma_scalar.py | 328 | f-string | summary.to_csv(OUT_DIR / f"ob_gamma_scalar_summary_{symbol}_{run_tag}.csv", index=False) |
| canonical_ob_gamma_scalar.py | 370 | f-string | print(f"canonical_ob_gamma_scalar  run={run_tag}  tier={args.tier}  mode={args.mode}") |
| canonical_ob_gamma_scalar.py | 373 | f-string | print(f"  gamma lookback = {GAMMA_LOOKBACK_MIN}min before entry_ts") |
| canonical_ob_gamma_scalar.py | 389 | f-string | combined.to_csv(OUT_DIR / f"ob_gamma_scalar_combined_{run_tag}.csv", index=False) |
| canonical_ob_gamma_scalar.py | 392 | f-string | print(f"OB x GAMMA REGIME (LONG / SHORT / NO_FLIP)  tier={args.tier}, mode={args.mode}") |
| canonical_ob_gamma_scalar.py | 400 | f-string | print(f"OB x GAMMA INTENSITY (HIGH / MID / LOW)  tier={args.tier}, mode={args.mode}") |
| canonical_ob_gamma_zone.py | 357 | f-string | print(f"  computing gamma zones for {len(entries)} entries ...", end="", flush=True) |
| canonical_ob_gamma_zone.py | 379 | f-string | entries.to_csv(OUT_DIR / f"ob_gamma_zone_detail_{symbol}_{run_tag}.csv", index=False) |
| canonical_ob_gamma_zone.py | 383 | f-string | print(f"  entries with valid gamma zone state: {len(valid)} / {len(entries)}") |
| canonical_ob_gamma_zone.py | 398 | f-string | summary.to_csv(OUT_DIR / f"ob_gamma_zone_summary_{symbol}_{run_tag}.csv", index=False) |
| canonical_ob_gamma_zone.py | 418 | f-string | print(f"canonical_ob_gamma_zone  run={run_tag}  tier={args.tier}  mode={args.mode}") |
| canonical_ob_gamma_zone.py | 420 | f-string | print(f"  zone def      = top {int(ZONE_MASS_THRESHOLD*100)}% of \|net signed GEX\| per strike") |
| canonical_ob_gamma_zone.py | 438 | f-string | combined.to_csv(OUT_DIR / f"ob_gamma_zone_combined_{run_tag}.csv", index=False) |
| canonical_ob_gamma_zone.py | 441 | f-string | print(f"OB x GAMMA-ZONE PRECISION MATRIX  (tier={args.tier}, mode={args.mode})") |
| canonical_ob_gamma_zone_bs.py | 450 | f-string | print(f"  computing per-strike gamma zones for {len(entries)} entries ...", end="", flush=True) |
| canonical_ob_gamma_zone_bs.py | 475 | f-string | entries.to_csv(OUT_DIR / f"ob_gamma_zone_bs_detail_{symbol}_{run_tag}.csv", index=False) |
| canonical_ob_gamma_zone_bs.py | 493 | f-string | summary.to_csv(OUT_DIR / f"ob_gamma_zone_bs_summary_{symbol}_{run_tag}.csv", index=False) |
| canonical_ob_gamma_zone_bs.py | 528 | f-string | print(f"canonical_ob_gamma_zone_bs  run={run_tag}  tier={args.tier}  mode={args.mode}") |
| canonical_ob_gamma_zone_bs.py | 532 | f-string | print(f"  zone threshold   = top {int(ZONE_MASS_THRESHOLD*100)}% of \|net signed GEX\| mass") |
| canonical_ob_gamma_zone_bs.py | 549 | f-string | combined.to_csv(OUT_DIR / f"ob_gamma_zone_bs_combined_{run_tag}.csv", index=False) |
| canonical_ob_gamma_zone_bs.py | 552 | f-string | print(f"OB x GAMMA ZONE (BS-DERIVED)  tier={args.tier}  mode={args.mode}") |
| compile_market_environment_local.py | 318 | f-string | note = (f"{ambient} · lenses {lens_alignment} · gamma {reg or 'n/a'} · " |
| compile_market_environment_local.py | 341 | f-string | note = (f"{ambient} · lenses {lens_alignment} · gamma {reg or 'n/a'} · " |
| compile_market_environment_local.py | 473 | f-string | log(f"{symbol}: no gamma_metrics in window — SKIP") |
| compile_market_environment_local.py | 508 | f-string | f"(persist={l1['gex_regime_persistence_20d']} div={l2['price_vs_breadth_div']} " |
| compile_market_environment_local.py | 565 | f-string | log(f"[dry] {sym}: no gamma_metrics in window") |
| compute_gamma_metrics_local.py | 599 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local.py | 616 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local.py | 630 | f-string | error_message=f"upsert_gex_strike_snapshots failed: {e}", |
| compute_gamma_metrics_local.py | 633 | f-string | print(f"gex_strike_snapshots_rows_written={gss_n}") |
| compute_gamma_metrics_local.py | 642 | f-string | print(f"net_gex={result.net_gex}") |
| compute_gamma_metrics_local.py | 643 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| compute_gamma_metrics_local.py | 647 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| compute_gamma_metrics_local.py | 657 | f-string | print(f"max_gamma_strike={result.max_gamma_strike}") |
| compute_gamma_metrics_local_PRE_S37.py | 263 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| compute_gamma_metrics_local_PRE_S37.py | 907 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_S37.py | 924 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_S37.py | 938 | f-string | print(f"net_gex={result.net_gex}") |
| compute_gamma_metrics_local_PRE_S37.py | 939 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| compute_gamma_metrics_local_PRE_S37.py | 943 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| compute_gamma_metrics_local_PRE_S37_v2.py | 263 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| compute_gamma_metrics_local_PRE_S37_v2.py | 907 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_S37_v2.py | 924 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_S37_v2.py | 938 | f-string | print(f"net_gex={result.net_gex}") |
| compute_gamma_metrics_local_PRE_S37_v2.py | 939 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| compute_gamma_metrics_local_PRE_S37_v2.py | 943 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| compute_gamma_metrics_local_PRE_S41.py | 265 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| compute_gamma_metrics_local_PRE_S41.py | 1022 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_S41.py | 1039 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_S41.py | 1053 | f-string | error_message=f"upsert_gex_strike_snapshots failed: {e}", |
| compute_gamma_metrics_local_PRE_S41.py | 1056 | f-string | print(f"gex_strike_snapshots_rows_written={gss_n}") |
| compute_gamma_metrics_local_PRE_S41.py | 1065 | f-string | print(f"net_gex={result.net_gex}") |
| compute_gamma_metrics_local_PRE_S41.py | 1066 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| compute_gamma_metrics_local_PRE_S41.py | 1070 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 281 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 1251 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 1268 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 1282 | f-string | error_message=f"upsert_gex_strike_snapshots failed: {e}", |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 1285 | f-string | print(f"gex_strike_snapshots_rows_written={gss_n}") |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 1294 | f-string | print(f"net_gex={result.net_gex}") |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 1295 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 1299 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 1309 | f-string | print(f"max_gamma_strike={result.max_gamma_strike}") |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 263 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 869 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 886 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 900 | f-string | print(f"net_gex={result.net_gex}") |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 901 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 905 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 263 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 897 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 914 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 928 | f-string | print(f"net_gex={result.net_gex}") |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 929 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 933 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 253 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 802 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 819 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 833 | f-string | print(f"net_gex={result.net_gex}") |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 834 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 838 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 263 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 869 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 886 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 900 | f-string | print(f"net_gex={result.net_gex}") |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 901 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 905 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 263 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 879 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 896 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 910 | f-string | print(f"net_gex={result.net_gex}") |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 911 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 915 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| compute_structural_divergence_local.py | 269 | f-string | error_message=f"gamma_metrics fetch failed: {e}") |
| compute_structural_divergence_local.py | 275 | f-string | error_message=f"No gamma_metrics row for {symbol}. " |
| compute_structural_divergence_local.py | 381 | f-string | print(f"gamma_conc / delta:    {conc_now} / {gamma_concentration_delta}") |
| detect_structural_manipulation.py | 605 | f-string | f"STOP HUNT RISK -- breadth collapsed {breadth_score_change:.1f}pts vs LONG_GAMMA" |
| detect_structural_manipulation.py | 638 | f-string | print(f"  [{symbol}] No gamma_metrics row -- skipping") |
| detect_structural_manipulation.py | 773 | f-string | print(f"symbol={symbol}  run_type={run_type}  run_id={run_id or 'from gamma_metrics'}") |
| detect_structural_manipulation.py | 783 | f-string | print(f"gamma_pinning={row['gamma_pinning']}") |
| diag_td056_raw_vs_tiered_counts.py | 83 | f-string | f"C:\\GammaEnginePython\\ ({e})") |
| docs/research/gamma_metrics_tail_probe.py | 136 | f-string | out = OUT_DIR / f"gamma_metrics_tail_{now.date().isoformat()}.md" |
| docs/research/s90_agentic/patches/patch_r07_ledger.py | 83 | f-string | f'        run_id=run_id, product_relation="gamma_metrics",  # {MARK}\n' |
| docs/research/s90_agentic/patches/patch_r07_ledger.py | 89 | f-string | f'        run_id=run_id, product_relation="gex_cycle_history",  # {MARK}\n' |
| docs/research/s90_agentic/patches/patch_r07_ledger.py | 93 | f-string | f'                           run_id=run_id, product_relation="gex_cycle_history")  # {MARK}\n'), |
| docs/research/s90_agentic/patches/s90_enh133_wire.py | 38 | f-string | f'    # {MARK}: after gamma AND volatility (v_gex_strike_rank / v_gex_strike_walls read\n' |
| docs/research/s90_agentic/patches/s90_enh133_wire.py | 44 | f-string | '                f"write_gex_cycle_history {symbol}",\n' |
| docs/research/s95_priority/sstar/sstar_gates.py | 218 | f-string | res["G1"].append(f"{name}: net_at_spot {float(q['net_dex_at_spot_cr']):.6f} != {vr['net']:.6f}") |
| docs/research/s96_priority/p3b/test_p3b_fixture.py | 53 | f-string | line = [f"{d}: runs with check rows {nr} (P3a runs {info['runs_gex']}; this sweep call took {n})"] |
| docs/research/s96_priority/p3b/test_p3b_fixture.py | 55 | f-string | fails.append(f"T1 {d}: {nr} runs checked, P3a has {info['runs_gex']}") |
| experiment_11_12_regime_intersection.py | 507 | f-string | by_pat_gamma[f"{pat_name}\|{gamma_r}"].add_no_data() |
| experiment_11_12_regime_intersection.py | 510 | f-string | by_pat_combo[f"{pat_name}\|{gamma_r}\|{bread_r}\|{mom_r}"].add_no_data() |
| experiment_11_12_regime_intersection.py | 512 | f-string | by_phase_gamma[f"{phase}\|{gamma_r}"].add_no_data() |
| experiment_11_12_regime_intersection.py | 529 | f-string | by_pat_gamma[f"{pat_name}\|{gamma_r}"].add(pnl_dict) |
| experiment_11_12_regime_intersection.py | 532 | f-string | by_pat_combo[f"{pat_name}\|{gamma_r}\|{bread_r}\|{mom_r}"].add(pnl_dict) |
| experiment_11_12_regime_intersection.py | 534 | f-string | by_phase_gamma[f"{phase}\|{gamma_r}"].add(pnl_dict) |
| experiment_17_bear_ob_gamma_override.py | 222 | f-string | log(f"  SHORT_GAMMA BEAR_OB MORNING: {sg_wr:.1f}% WR (N={sg_n})") |
| experiment_17_bear_ob_gamma_override.py | 223 | f-string | log(f"  LONG_GAMMA  BEAR_OB MORNING: {lg_wr:.1f}% WR (N={lg_n})") |
| experiment_17_bear_ob_gamma_override.py | 230 | f-string | log(f"  STRONG EDGE CONFIRMED: {lg_wr:.1f}% WR under LONG_GAMMA") |
| experiment_17_bear_ob_gamma_override.py | 234 | f-string | log(f"  MODERATE EDGE: {lg_wr:.1f}% WR under LONG_GAMMA") |
| experiment_17_bear_ob_gamma_override.py | 237 | f-string | log(f"  WEAK/NO EDGE: {lg_wr:.1f}% WR under LONG_GAMMA") |
| experiment_17_v2.py | 197 | f-string | log(f"  SHORT_GAMMA BEAR_OB MORNING: {sg_wr:.1f}% WR (N={sg_n})") |
| experiment_17_v2.py | 198 | f-string | log(f"  LONG_GAMMA  BEAR_OB MORNING: {lg_wr:.1f}% WR (N={lg_n})") |
| experiment_17_v2.py | 208 | f-string | log(f"  STRONG EDGE: {lg_wr:.1f}% WR under LONG_GAMMA (N={lg_n})") |
| experiment_17_v2.py | 212 | f-string | log(f"  MODERATE EDGE: {lg_wr:.1f}% WR under LONG_GAMMA (N={lg_n})") |
| experiment_17_v2.py | 215 | f-string | log(f"  WEAK/NO EDGE: {lg_wr:.1f}% WR under LONG_GAMMA (N={lg_n})") |
| experiment_18_confluence_rerun.py | 333 | dynamic-get | g = b["gamma"].get(regime, {}) |
| experiment_18_oi_ict_confluence.py | 383 | dynamic-get | g = b["gamma"].get(regime, {}) |
| experiment_19_gamma_asymmetry.py | 113 | dynamic-get | b = by_gamma.get(regime, {"w":0,"n":0,"ret":0}) |
| experiment_19_gamma_asymmetry.py | 184 | f-string | log(f"    SHORT_GAMMA: {sg_wr:.1f}% (N={sg['n']})") |
| experiment_19_gamma_asymmetry.py | 185 | f-string | log(f"    LONG_GAMMA:  {lg_wr:.1f}% (N={lg['n']})") |
| experiment_19_gamma_asymmetry.py | 199 | f-string | log(f"\n  BEAR_OB under LONG_GAMMA: {bear_lg_wr:.1f}% WR (N={bear_lg['n']})") |
| experiment_19_gamma_asymmetry.py | 200 | f-string | log(f"  BULL_OB under LONG_GAMMA: {bo_lg_wr:.1f}% WR (N={bo_lg['n']})") |
| experiment_19_gamma_asymmetry.py | 207 | f-string | log(f"    BULL_OB LONG_GAMMA = {bo_lg_wr:.1f}% WR -> ALLOW BUY_CE") |
| experiment_19_gamma_asymmetry.py | 208 | f-string | log(f"    BEAR_OB LONG_GAMMA = {bear_lg_wr:.1f}% WR -> KEEP BLOCKING BUY_PE") |
| experiment_19_gamma_asymmetry.py | 214 | f-string | log(f"    BULL_OB LONG_GAMMA = {bo_lg_wr:.1f}% -> consider allowing BUY_CE") |
| experiment_19_gamma_asymmetry.py | 215 | f-string | log(f"    BEAR_OB LONG_GAMMA = {bear_lg_wr:.1f}% -> borderline on blocking") |
| experiment_19_gamma_asymmetry.py | 221 | f-string | log(f"  NO ASYMMETRY: BULL_OB also weak under LONG_GAMMA ({bo_lg_wr:.1f}%)") |
| experiment_23_sweep_reversal.py | 322 | dynamic-get | b = by_gamma.get(g, {"w":0,"n":0}) |
| experiment_26_option_wick_reversal.py | 280 | dynamic-get | b = by_gamma_pe.get(regime, {"w":0,"n":0}) |
| fill_gamma_concentration.py | 80 | f-string | {"select": "bar_ts,net_gex", "symbol": f"eq.{symbol}", |
| fill_gamma_concentration.py | 83 | f-string | print(f"{symbol}: no hist_gamma_metrics rows on {day}"); return 1 |
| fill_gamma_concentration.py | 85 | f-string | print(f"{symbol}: validating reconstruction vs existing net_gex on {day} " |
| fill_gamma_concentration.py | 113 | f-string | print(f"  net_gex sign   : {sgn}/{n} ({100*sgn/n:.0f}%)") |
| fill_gamma_concentration.py | 132 | f-string | {"select": "bar_ts,trade_date,gamma_concentration", "symbol": f"eq.{symbol}", |
| fill_gamma_concentration.py | 136 | f-string | print(f"{symbol}: no hist_gamma_metrics rows in {d_from}..{d_to}"); return 1 |
| fill_gamma_concentration.py | 182 | f-string | {"select": "bar_ts,trade_date,gamma_concentration", "symbol": f"eq.{symbol}", |
| fill_gamma_concentration.py | 186 | f-string | print(f"{symbol}: no hist_gamma_metrics rows in {d_from}..{d_to}"); return 1 |
| fill_gamma_concentration.py | 268 | f-string | {"select": "bar_ts,trade_date,gamma_concentration", "symbol": f"eq.{symbol}", |
| fix_capture_spot_holiday_gate.py | 63 | f-string | print(f"ERROR: {TARGET} not found. Run from C:\\GammaEnginePython\\") |
| fix_enh35_unclobber_direction_bias.py | 85 | f-string | f"ERROR: LONG_GAMMA target found {src.count(OLD_LONG_GAMMA)} times " |
| fix_enh35_unclobber_direction_bias.py | 121 | f-string | print(f"  LONG_GAMMA branch: clobber removed = {NEW_LONG_GAMMA[:40].strip()!r}...") |
| fix_enh46a_signal_alerts.py | 179 | f-string | regime_bits.append(f"gamma={gamma}") |
| fix_merdian_start_calendar.py | 137 | f-string | print(f"ERROR: {TARGET} not found. Run from C:\\GammaEnginePython\\") |
| fix_merdian_start_calendar_v2.py | 103 | f-string | print(f"ERROR: {TARGET} not found. Run from C:\\GammaEnginePython\\") |
| fix_set_symbol.py | 79 | f-string | print(f"[ERROR] {TARGET} not found. Run from C:\\GammaEnginePython", file=sys.stderr) |
| fix_td_new_12_shadow_flag.py | 94 | f-string | sys.exit(f"FATAL: {TARGET} not found. Run from C:\\GammaEnginePython\\.") |
| fix_td_new_12_shadow_flag.py | 178 | f-string | print(f"  5. Confirm script_execution_log row for #4 shows actual_writes: {{gamma_metrics_shadow: 1}}") |
| gamma_engine_alert_check.py | 123 | f-string | f"GAMMA ENGINE ALERT: {status}", |
| gamma_engine_alert_check.py | 145 | f-string | print(f"GAMMA ENGINE STATUS: {status}") |
| gamma_engine_health_check.phase_c_final_verdict_checkpoint.py | 249 | f-string | f"gamma={stage_statuses.get('gamma_metrics', 'UNKNOWN'):7} \| " |
| gamma_engine_health_check.phase_c_lag_summary_checkpoint.py | 249 | f-string | f"gamma={stage_statuses.get('gamma_metrics', 'UNKNOWN'):7} \| " |
| gamma_engine_health_check.phase_c_summary_checkpoint.py | 242 | f-string | f"gamma={stage_statuses.get('gamma_metrics', 'UNKNOWN'):7} \| " |
| gamma_engine_health_check.pre_final_verdict_backup.py | 249 | f-string | f"gamma={stage_statuses.get('gamma_metrics', 'UNKNOWN'):7} \| " |
| gamma_engine_health_check.pre_lag_summary_backup.py | 242 | f-string | f"gamma={stage_statuses.get('gamma_metrics', 'UNKNOWN'):7} \| " |
| gamma_engine_health_check.pre_phase_c_backup.py | 90 | f-string | print(f"GAMMA ENGINE STATUS: {status}") |
| gamma_engine_health_check.py | 267 | f-string | f"gamma={stage_statuses.get('gamma_metrics', 'UNKNOWN'):7} \| " |
| generate_pine_overlay.py | 334 | f-string | peak_str = f"peak +{pin['peak_gex_cr']/1000:.0f}K Cr" |
| generate_pine_overlay.py | 335 | f-string | zone_str = f"zone +{pin['total_gex_cr']/1000:.0f}K Cr" |
| generate_pine_overlay.py | 363 | f-string | trough_str = f"trough {accel['trough_gex_cr']/1000:.0f}K Cr" |
| generate_pine_overlay.py | 364 | f-string | zone_str   = f"zone {accel['total_gex_cr']/1000:.0f}K Cr" |
| generate_pine_overlay_PRE_S37_ENH81_v2.py | 205 | f-string | peak_str = f"+{pin['peak_gex_cr']/1000:.0f}K Cr" |
| generate_pine_overlay_PRE_S37_ENH81_v2.py | 225 | f-string | trough_str = f"{accel['trough_gex_cr']/1000:.0f}K Cr" |
| generate_pine_overlay_PRE_S41_BOXCOUNT.py | 220 | f-string | peak_str = f"+{pin['peak_gex_cr']/1000:.0f}K Cr" |
| generate_pine_overlay_PRE_S41_BOXCOUNT.py | 246 | f-string | trough_str = f"{accel['trough_gex_cr']/1000:.0f}K Cr" |
| generate_pine_overlay_PRE_S41_COLOR.py | 220 | f-string | peak_str = f"+{pin['peak_gex_cr']/1000:.0f}K Cr" |
| generate_pine_overlay_PRE_S41_COLOR.py | 246 | f-string | trough_str = f"{accel['trough_gex_cr']/1000:.0f}K Cr" |
| ingest_participant_positioning.py | 200 | f-string | print(f"  parsed -> date={cdate} fii_net={crow['fii_net_cr']} " |
| ingest_participant_positioning.py | 201 | f-string | f"dii_net={crow['dii_net_cr']}") |
| ingest_participant_positioning.py | 226 | f-string | f"(fii_net={crow['fii_net_cr']} dii_net={crow['dii_net_cr']})") |
| inspect_option_chain_snapshot_gaps_local.py | 96 | f-string | raise RuntimeError(f"No gamma_metrics row found for {symbol}") |
| inspect_signal_freshness_local.py | 72 | f-string | f"Timestamp mismatch too large for gamma vs option chain: {gamma_vs_chain:.2f}s (> {MAX_FEATURE_MISMATCH_SECONDS}s)" |
| inspect_signal_freshness_local.py | 77 | f-string | f"Timestamp mismatch too large for volatility vs gamma: {vol_vs_gamma:.2f}s (> {MAX_FEATURE_MISMATCH_SECONDS}s)" |
| inspect_signal_freshness_local.py | 91 | f-string | print(f"Gamma Engine - Signal Freshness Inspection - {symbol}") |
| inspect_signal_freshness_local.py | 98 | f-string | print(f"Latest gamma ts:         {gamma_ts}") |
| inspect_signal_freshness_local.py | 108 | f-string | print(f"Gamma vs chain (s):      {gamma_vs_chain:.2f}" if gamma_vs_chain is not None else "Gamma vs chain (s):      None") |
| inspect_signal_freshness_local.py | 109 | f-string | print(f"Vol vs gamma (s):        {vol_vs_gamma:.2f}" if vol_vs_gamma is not None else "Vol vs gamma (s):        None") |
| inspect_signal_freshness_local.py | 124 | f-string | print(f"Latest gamma run_id:     {gamma_row.get('run_id')}") |
| measure_rate_sensitivity.py | 309 | f-string | hdr = f"{'date':>11} {'spot':>8} {'F':>8} {'r_basis':>8} {'ngex@6.5':>10} {'ngex@rb':>10} {'flip@6.5':>9} {'flip@rb':>9} {'reg@6.5':>11} {'reg@rb':>11} {'FLIP?':>6}" |
| measure_rate_sensitivity.py | 339 | f-string | print(f"net_gex sign flips    : {sign_flips}  ({100*sign_flips/cohorts:.1f}%)") |
| merdian_compute/gamma.py | 170 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| merdian_live_dashboard.py | 379 | f-string | rows = sb_get("gamma_metrics", f"select=ts,regime,flip_level&symbol=eq.{symbol}&order=ts.desc&limit=1") |
| merdian_live_dashboard.py | 416 | f-string | rows = sb_get("market_state_snapshots", f"select=ts,gamma_features,wcb_features&symbol=eq.{symbol}&order=ts.desc&limit=1") |
| merdian_live_dashboard.py | 432 | f-string | "value": f"γ:{gamma_r} WCB:{wcb_r}", |
| merdian_live_dashboard_PRE_S25.py | 292 | f-string | rows = sb_get("gamma_metrics", f"select=ts,regime,flip_level&symbol=eq.{symbol}&order=ts.desc&limit=1") |
| merdian_live_dashboard_PRE_S25.py | 329 | f-string | rows = sb_get("market_state_snapshots", f"select=ts,gamma_features,wcb_features&symbol=eq.{symbol}&order=ts.desc&limit=1") |
| merdian_live_dashboard_PRE_S25.py | 345 | f-string | "value": f"γ:{gamma_r} WCB:{wcb_r}", |
| merdian_live_dashboard_PRE_S25b.py | 379 | f-string | rows = sb_get("gamma_metrics", f"select=ts,regime,flip_level&symbol=eq.{symbol}&order=ts.desc&limit=1") |
| merdian_live_dashboard_PRE_S25b.py | 416 | f-string | rows = sb_get("market_state_snapshots", f"select=ts,gamma_features,wcb_features&symbol=eq.{symbol}&order=ts.desc&limit=1") |
| merdian_live_dashboard_PRE_S25b.py | 432 | f-string | "value": f"γ:{gamma_r} WCB:{wcb_r}", |
| merdian_pipeline_alert_daemon.py | 386 | f-string | regime_bits.append(f"gamma={gamma}") |
| merdian_signal_dashboard.py | 404 | f-string | f'<div class="rw">{pill(gamma)} {pill(breadth)}</div>' |
| patch_dashboard_phase4b.py | 245 | f-string | print(f"ERROR: {TARGET} not found. Run from C:\\GammaEnginePython\\") |
| patch_s36_enh99_v3.py | 134 | f-string | result["reason"] = f"REGEX MATCHED {len(matches)} times (expected 1)" |
| phase0b_p5_pinned_proxy.py | 137 | f-string | print(f"      → {len(out)} gamma_metrics rows") |
| phase0b_p5_pinned_proxy.py | 190 | f-string | print(f"\nGamma concentration P75 thresholds: NIFTY={gc_p75.get('NIFTY', 0):.4f}, SENSEX={gc_p75.get('SENSEX', 0):.4f}") |
| phase0b_p5_pinned_proxy.py | 191 | f-string | print(f"PROXY-PINNED criteria: gamma_concentration >= P75 AND \|flip_distance_pct\| < {PROXY_FLIP_DIST_MAX_PCT}% AND regime != NO_FLIP\n") |
| phase0b_p5_pinned_proxy.py | 240 | f-string | print(f"Processed: {len(enriched)} signals (skipped: {skipped_no_prices} no-prices, {skipped_no_gm} no-gamma_metrics)\n") |
| phase0b_p5_pinned_proxy_v2.py | 166 | f-string | print(f"      → {len(out)} gamma_metrics rows (CR-clean)") |
| phase0b_p5_pinned_proxy_v2.py | 221 | f-string | print(f"\nGamma concentration P75 thresholds: NIFTY={gc_p75.get('NIFTY', 0):.4f}, SENSEX={gc_p75.get('SENSEX', 0):.4f}") |
| phase0b_p5_pinned_proxy_v2.py | 222 | f-string | print(f"PROXY-PINNED criteria: gamma_concentration >= P75 AND \|flip_distance_pct\| < {PROXY_FLIP_DIST_MAX_PCT}% AND regime != NO_FLIP\n") |
| phase0b_p5_pinned_proxy_v2.py | 280 | f-string | print(f"Processed: {len(enriched)} signals (skipped: {skipped_no_prices} no-prices, {skipped_no_gm} no-gamma_metrics)\n") |
| reconstruct_shadow_for_date_local.py | 240 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| reconstruct_shadow_for_date_local.py | 472 | f-string | print(f"gamma_regime={row['gamma_regime']}") |
| reconstruct_shadow_for_date_local_v2.py | 258 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| reconstruct_shadow_for_date_local_v2.py | 506 | f-string | print(f"gamma_regime={row['gamma_regime']}") |
| reconstruct_shadow_for_date_local_v3.py | 263 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| reconstruct_shadow_for_date_local_v3.py | 555 | f-string | print(f"gamma_regime={row['gamma_regime']}") |
| relate_ambient_to_open_local.py | 98 | f-string | log(f"{symbol}: no opening gamma cycle for {for_session} — run after the open. SKIP") |
| replay/replay_build_market_state_snapshot.py | 351 | f-string | return log.exit_with_reason("DATA_ERROR", 1, error_message=f"gamma_metrics_replay fetch failed: {e}") |
| replay/replay_build_market_state_snapshot.py | 356 | f-string | error_message=f"No gamma_metrics_replay row for {symbol} at/before {replay_ts_iso}. " |
| replay/replay_build_market_state_snapshot.py | 414 | f-string | print(f"gamma_regime={payload['gamma_features'].get('gamma_regime')}") |
| replay/replay_build_market_state_snapshot.py | 415 | f-string | print(f"flip_distance_pct={payload['gamma_features'].get('flip_distance_pct')}") |
| replay/replay_build_trade_signal.py | 332 | f-string | reasons.append(f"Gamma regime is {gamma_regime}") |
| replay/replay_build_trade_signal.py | 822 | f-string | print(f"gamma_regime={row.get('gamma_regime')}") |
| replay/replay_compute_gamma_metrics.py | 219 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| replay/replay_compute_gamma_metrics.py | 639 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| replay/replay_compute_gamma_metrics.py | 650 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| replay/replay_compute_gamma_metrics.py | 664 | f-string | print(f"net_gex={result.net_gex}") |
| replay/replay_compute_gamma_metrics.py | 665 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| replay/replay_compute_gamma_metrics.py | 668 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 219 | dynamic-get | strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot) |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 639 | f-string | error_message=f"compute_gamma_metrics failed: {e}", |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 650 | f-string | error_message=f"upsert_gamma_metrics failed: {e}", |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 664 | f-string | print(f"net_gex={result.net_gex}") |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 665 | f-string | print(f"gamma_concentration={result.gamma_concentration}") |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 668 | f-string | print(f"gamma_zone={result.gamma_zone}") |
| run_merdian_shadow_runner_aws.py | 367 | f-string | f"compute_gamma_metrics {symbol}", |
| run_merdian_shadow_runner_aws.py | 383 | f-string | f"write_gex_cycle_history {symbol}", |
| run_merdian_state_stack_once.py | 60 | f-string | f"{supabase_url.rstrip('/')}/rest/v1/gamma_metrics" |
| run_merdian_state_stack_once.py | 76 | f-string | f"Failed to fetch latest gamma run_id for {symbol} \| " |
| run_merdian_state_stack_once.py | 82 | f-string | raise RuntimeError(f"No gamma_metrics row found for symbol={symbol}") |
| run_merdian_state_stack_once.py | 86 | f-string | raise RuntimeError(f"Latest gamma_metrics row missing run_id for symbol={symbol}") |
| run_merdian_state_stack_once.py | 109 | f-string | print(f"NIFTY: latest gamma run_id = {nifty_run_id}") |
| run_merdian_state_stack_once.py | 110 | f-string | print(f"SENSEX: latest gamma run_id = {sensex_run_id}") |
| run_option_snapshot_intraday_runner.py | 447 | f-string | step_name=f"{symbol} compute_gamma_metrics", |
| run_option_snapshot_intraday_runner_backup_before_breadth_fix.py | 151 | f-string | log(f"ERROR: gamma metrics failed for {symbol}, skipping downstream steps") |
| run_option_snapshot_intraday_runner_before_signal_step.py | 163 | f-string | log(f"ERROR: gamma metrics failed for {symbol}, skipping downstream steps") |
| run_validation_analysis.py | 411 | f-string | gb_key = f"{row.get('gamma_regime','?')}\|{row.get('breadth_regime','?')}" |
| run_validation_analysis.py | 427 | f-string | gb_key   = f"{row.get('gamma_regime','?')}\|{row.get('breadth_regime','?')}" |
| s30_target_days_audit.py | 247 | f-string | f"{'Natural':<8} {'MERDIAN':<10} {'Allow':<5} {'Dir':<8} {'Gamma':<13} " |
| s30_target_days_audit.py | 260 | f-string | f"{(s.get('gamma_regime','—') or '—'):<13} " |
| s31_p1_long_gamma_audit.py | 333 | f-string | print(f"{'Pattern':<10} {'GammaRegime':<14} {'N':>5} {'WR%':>7} " |
| s31_p1_long_gamma_audit.py | 403 | f-string | print(f"    LONG_GAMMA:  N={lg_s['n']:>4}  WR={lg_s['wr']:>5.1f}% " |
| s31_p1_long_gamma_audit.py | 406 | f-string | print(f"    SHORT_GAMMA: N={sg_s['n']:>4}  WR={sg_s['wr']:>5.1f}% " |
| s31_weekly_attribution_diagnostic.py | 720 | f-string | print(f"  → {len(gamma_rows)} gamma_metrics rows in {time.time() - t0:.1f}s") |
| scripts/build_data_inventory.py | 916 | f-string | log(f"correspondence: {len(want)} (gamma-side, oi-side, symbol) pairs present in data") |
| scripts/build_data_inventory.py | 1469 | f-string | A(f"gamma         {RE_GAMMA.pattern}") |
| scripts/eod_health_check.py | 301 | f-string | rt = requests.get(f"{url}/rest/v1/{GEX_TABLE}", headers=h, |
| scripts/eod_health_check.py | 309 | f-string | rs = requests.get(f"{url}/rest/v1/{GEX_TABLE}", headers=h, |
| scripts/eod_health_check.py | 316 | f-string | return WARN, f"  {MARK[WARN]} {'gex view symbol coverage':<28} query error: {str(e)[:60]}" |
| scripts/eod_health_check.py | 319 | f-string | return WARN, (f"  {MARK[WARN]} {'gex view symbol coverage':<28} " |
| scripts/eod_health_check.py | 320 | f-string | f"{GEX_TABLE} is empty") |
| scripts/eod_health_check.py | 327 | f-string | return FAIL, (f"  {MARK[FAIL]} {'gex view symbol coverage':<28} " |
| scripts/eod_health_check.py | 331 | f-string | return WARN, (f"  {MARK[WARN]} {'gex view symbol coverage':<28} " |
| scripts/eod_health_check.py | 332 | f-string | f"view lists {absent} but no rows present in {GEX_TABLE}  [{cells}]") |
| scripts/eod_health_check.py | 333 | f-string | return OK, (f"  {MARK[OK]} {'gex view symbol coverage':<28} " |
| stage2_db_contract.py | 135 | f-string | return WARN, f"Could not verify gamma_metrics columns: {err}" |
| tests/replay/test_replay_seeded.py | 276 | f-string | f"final {final[GAMMA]}/{final[GEX]} own {own[GAMMA][0]}/{own[GEX][0]} gamma_age={detail[GAMMA].get('age_min')}") |
| tests/replay/test_replay_seeded.py | 322 | f-string | f"final {final[GAMMA]}/{final[GEX]} own {own[GAMMA][0]}/{own[GEX][0]}") |
| tests/replay/test_replay_seeded.py | 345 | f-string | own[GEX][0] == "DEGRADED", f"{own[GEX][0]} rows={detail[GEX].get('rows_at_newest')}") |
| tests/test_dex_recompute.py | 479 | f-string | notes.append(f"loaded {len(ocs)} chain rows, {len(gss)} gex_strike rows, " |
| tests/test_dex_recompute.py | 515 | f-string | failures.append(f"A1: fixture gex_strike holds no rows for run_id {run_id}") |
| tests/test_dex_recompute.py | 519 | dynamic-get | got = gex.get(k) |
| tests/test_dex_recompute.py | 528 | f-string | failures.append(f"A1: {missing} strikes in gex_strike are absent from the chain " |
| tests/test_dex_recompute.py | 531 | f-string | failures.append(f"A1: gex_cr rebuild differs by {worst:.3e} Cr at strike " |
| tests/test_dex_recompute.py | 532 | f-string | f"{worst_k} (tolerance {TOL_CR:.0e}) -- the /1e7 scaling, the oi " |
| tests/test_dex_recompute.py | 538 | f-string | notes.append(f"A1 gex_cr rebuild matches production on {n_cmp} strikes " |
| tests/test_dex_recompute.py | 659 | f-string | observations.append(f"sum(net_dex_cr) {sum_net:.2f} Cr differs from the leg total by " |
| tests/test_dex_recompute.py | 683 | f-string | "" if d["call_dex_cr"] is None else f"{d['call_dex_cr']:.10f}", |
| tests/test_dex_recompute.py | 684 | f-string | "" if d["put_dex_cr"] is None else f"{d['put_dex_cr']:.10f}", |
| tests/test_dex_recompute.py | 685 | f-string | "" if d["net_dex_cr"] is None else f"{d['net_dex_cr']:.10f}", |
| tests/test_gamma_prior_row.py | 230 | f-string | print(f"GAMMA PRIOR ROW PASS ({len(base)} cells, {len(MUTANTS)} mutants, 0 surviving)") |
| tests/test_merdian_compute_contract.py | 166 | f-string | errs.append(f"GammaMetricsResult fields {list(G.GammaMetricsResult.__dataclass_fields__)}") |
| tests/test_merdian_compute_contract.py | 250 | f-string | errs.append(f"{day.name} row {i}: {len(recent)} priors with a non-empty max_gamma_strike, want 5") |
| tests/test_p3a_invariants.py | 44 | f-string | return {k: rd(os.path.join(d, f"{k}.csv.gz")) for k in ("gamma_metrics", "gex_strike", "ocs")} |
| tests/test_p3a_invariants.py | 68 | f-string | fails.append(f"I1 {key}: sum gex {tot:.4f} != net_gex {float(g['net_gex']):.4f}") |
| tests/test_p3a_invariants.py | 75 | f-string | fails.append(f"I4 {key}: top1 {top1:.6f} != gamma_concentration {float(g['gamma_concentration']):.6f}") |
| tests/test_p3a_invariants.py | 171 | f-string | print(f"== {day}  gex rows {len(data['gex_strike'])}  " + "  ".join(f"{k}={v}" for k, v in sorted(info.items()))) |
| validate_compute_contracts.py | 264 | f-string | url = f"{SUPABASE_URL}/rest/v1/gamma_metrics?order=created_at.desc&limit=2&select=run_id,created_at" |
| validate_hist_greeks_flat_r.py | 83 | f-string | print(f"No live gamma_metrics NIFTY on {d}."); return 1 |
| validate_hist_greeks_flat_r.py | 88 | f-string | print(f"cols: regime={reg_c} net_gex={ng_c}") |
| validate_hist_greeks_flat_r.py | 122 | f-string | print(f"\n{'hist_bar':>16} {'spot':>8} {'live_ngex':>11} {'recon_ngex':>11} {'live_reg':>11} {'recon_reg':>11} {'REG':>4} {'SGN':>4}") |
| validate_hist_greeks_flat_r.py | 130 | f-string | print(f"net_gex sign   : {sgn_ok}/{n} ({100*sgn_ok/n:.0f}%)") |
| validate_hist_greeks_flat_r.py | 132 | f-string | ratios.sort(); print(f"recon/live ngex: median {ratios[len(ratios)//2]:.2f}") |
| verify_td_new_2_flip_level.py | 150 | f-string | print(f"PATCHED net_gex:    {net_gex:,.0f}") |
| verify_td_new_3_net_gex_unit.py | 107 | f-string | print(f"LIVE net_gex:    {live_ng:,.0f}  (raw rupees, pre-TD-NEW-3)") |
| verify_td_new_3_net_gex_unit.py | 112 | f-string | print(f"PATCHED net_gex: {patched_ng:,.2f}  (Crore, post-TD-NEW-3)") |
| verify_td_new_3_net_gex_unit.py | 125 | f-string | print(f"Operationally sane (100 < \|net_gex\| < 1M Cr): {'YES' if op_sane else 'NO'}") |
| write_gex_cycle_history_local.py | 421 | f-string | error_message=f"no gamma_metrics rows for run_id={run_id}") |

## (e) function taking a Gamma-named arg and comparing it to a numeric literal  (n=158)

| file | line | function | gamma args | compare |
|---|---|---|---|---|
| backfill_gamma_metrics.py | 109 | determine_regime | net_gex | net_gex >= 0 |
| backfill_gamma_metrics_PRE_TD-NEW-3.py | 109 | determine_regime | net_gex | net_gex >= 0 |
| backfill_gamma_metrics_to_main.py | 290 | _classify_regime | net_gex | net_gex > 0 |
| backfill_gamma_metrics_to_main.py | 291 | _classify_regime | net_gex | net_gex < 0 |
| backfill_hist_greeks.py | 161 | signed_gex_vec | gamma | gamma != 0.0 |
| backfill_hist_greeks.py | 202 | regime_sign | net_gex | net_gex >= 0 |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 209 | _classify_directional_edge_state | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 255 | _resolve_direction_bias | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 330 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 332 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 407 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 444 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 447 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 465 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_complete_checkpoint.py | 468 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 167 | _resolve_direction_bias | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 234 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 236 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 311 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 348 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 351 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 369 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_conflict_logic_checkpoint.py | 372 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 151 | _resolve_direction_bias | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 210 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 212 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 287 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 324 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 327 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 345 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_directional_logic_checkpoint.py | 348 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 209 | _classify_directional_edge_state | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 244 | _resolve_direction_bias | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 319 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 321 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 396 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 433 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 436 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 454 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.phase_b_premium_edge_checkpoint.py | 457 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_conflict_logic_backup.py | 151 | _resolve_direction_bias | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.pre_conflict_logic_backup.py | 210 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_conflict_logic_backup.py | 212 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_conflict_logic_backup.py | 287 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_conflict_logic_backup.py | 324 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_conflict_logic_backup.py | 327 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_conflict_logic_backup.py | 345 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_conflict_logic_backup.py | 348 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_directional_logic_backup.py | 140 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_directional_logic_backup.py | 142 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_directional_logic_backup.py | 217 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_directional_logic_backup.py | 254 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_directional_logic_backup.py | 257 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_directional_logic_backup.py | 275 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_directional_logic_backup.py | 278 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_insert_fix_backup.py | 151 | _resolve_direction_bias | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.pre_insert_fix_backup.py | 210 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_insert_fix_backup.py | 212 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_insert_fix_backup.py | 287 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_insert_fix_backup.py | 324 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_insert_fix_backup.py | 327 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_insert_fix_backup.py | 345 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_insert_fix_backup.py | 348 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_phase_b_backup.py | 114 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_phase_b_backup.py | 116 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_phase_b_backup.py | 191 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_phase_b_backup.py | 228 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_phase_b_backup.py | 231 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_phase_b_backup.py | 249 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_phase_b_backup.py | 252 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_premium_state_backup.py | 167 | _resolve_direction_bias | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.pre_premium_state_backup.py | 234 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_premium_state_backup.py | 236 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_premium_state_backup.py | 311 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_premium_state_backup.py | 348 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_premium_state_backup.py | 351 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_premium_state_backup.py | 369 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_premium_state_backup.py | 372 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_signal_mode_backup.py | 209 | _classify_directional_edge_state | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.pre_signal_mode_backup.py | 244 | _resolve_direction_bias | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local.pre_signal_mode_backup.py | 319 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_signal_mode_backup.py | 321 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_signal_mode_backup.py | 396 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local.pre_signal_mode_backup.py | 433 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_signal_mode_backup.py | 436 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local.pre_signal_mode_backup.py | 454 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local.pre_signal_mode_backup.py | 457 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 209 | _classify_directional_edge_state | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 255 | _resolve_direction_bias | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 330 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 332 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 407 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 444 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 447 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 465 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local_PRE_WCB_BACKUP.py | 468 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 209 | _classify_directional_edge_state | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 255 | _resolve_direction_bias | gamma_regime,gamma_concentration | gamma_concentration >= 0.22 |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 330 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 332 | _base_confidence | gamma_regime,gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 407 | _apply_structure_penalties | gamma_concentration | gamma_concentration < 0.05 |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 444 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 447 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 465 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration >= 0.2 |
| build_trade_signal_local_PRE_WCB_MEASUREMENT.py | 468 | _apply_gamma_context | gamma_regime,gamma_concentration | gamma_concentration < 0.08 |
| compute_gamma_metrics_local_PRE_S37.py | 449 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| compute_gamma_metrics_local_PRE_S37.py | 447 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| compute_gamma_metrics_local_PRE_S37.py | 451 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| compute_gamma_metrics_local_PRE_S37.py | 470 | determine_regime | net_gex | net_gex >= 0 |
| compute_gamma_metrics_local_PRE_S37_v2.py | 449 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| compute_gamma_metrics_local_PRE_S37_v2.py | 447 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| compute_gamma_metrics_local_PRE_S37_v2.py | 451 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| compute_gamma_metrics_local_PRE_S37_v2.py | 470 | determine_regime | net_gex | net_gex >= 0 |
| compute_gamma_metrics_local_PRE_S41.py | 451 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| compute_gamma_metrics_local_PRE_S41.py | 449 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| compute_gamma_metrics_local_PRE_S41.py | 453 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| compute_gamma_metrics_local_PRE_S41.py | 472 | determine_regime | net_gex | net_gex >= 0 |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 467 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 465 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 469 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 488 | determine_regime | net_gex | net_gex >= 0 |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 449 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 447 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 451 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| compute_gamma_metrics_local_PRE_TD-NEW-12.py | 470 | determine_regime | net_gex | net_gex >= 0 |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 449 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 447 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 451 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| compute_gamma_metrics_local_PRE_TD-NEW-13.py | 470 | determine_regime | net_gex | net_gex >= 0 |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 382 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 380 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 384 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| compute_gamma_metrics_local_PRE_TD-NEW-2.py | 403 | determine_regime | net_gex | net_gex >= 0 |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 449 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 447 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 451 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| compute_gamma_metrics_local_PRE_TD-NEW-3.py | 470 | determine_regime | net_gex | net_gex >= 0 |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 449 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 447 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 451 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| compute_gamma_metrics_local_PRE_TD-NEW-4.py | 470 | determine_regime | net_gex | net_gex >= 0 |
| measure_rate_sensitivity.py | 103 | signed_gamma_exposure | gamma | gamma == 0.0 |
| measure_rate_sensitivity.py | 105 | signed_gamma_exposure | gamma | abs(gamma) > 5e-05 |
| measure_rate_sensitivity.py | 155 | regime | net_gex | net_gex >= 0 |
| merdian_compute/gamma.py | 407 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| merdian_compute/gamma.py | 405 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| merdian_compute/gamma.py | 409 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| merdian_compute/gamma.py | 428 | determine_regime | net_gex | net_gex >= 0 |
| replay/replay_compute_gamma_metrics.py | 327 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| replay/replay_compute_gamma_metrics.py | 326 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| replay/replay_compute_gamma_metrics.py | 329 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| replay/replay_compute_gamma_metrics.py | 346 | determine_regime | net_gex | net_gex >= 0 |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 327 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.25 |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 326 | compute_expansion_probability | gamma_concentration,net_gex | net_gex < 0 |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 329 | compute_expansion_probability | gamma_concentration,net_gex | gamma_concentration >= 0.15 |
| replay/replay_compute_gamma_metrics_PRE_TD-NEW-3.py | 346 | determine_regime | net_gex | net_gex >= 0 |
| tests/test_p3a_invariants.py | 36 | recompute | gamma | abs(gamma) > 5e-05 |
| validate_hist_greeks_flat_r.py | 11 | regime_sign | net_gex | net_gex >= 0 |

## (d) select('*') / SELECT * with a Gamma token within 12 lines above  (n=80)

| file | line | text | ctx |
|---|---|---|---|
| compute_gamma_metrics_local_PRE_S41.py | 156 | query = SUPABASE.table("option_chain_snapshots").select("*").eq("run_id", run_id) | GAMMA-CTX |
| compute_gamma_metrics_local_PRE_S41_FIX1.py | 172 | query = SUPABASE.table("option_chain_snapshots").select("*").eq("run_id", run_id) | GAMMA-CTX |
| docs/research/s87_routing/scripts/phase_c.py | 236 | c7_skipped = reqi(bas, r"C7 schema subtree skipped.*?schema-key occurrences " | GAMMA-CTX |
| fix_td_new_12_shadow_flag.py | 174 | print(f"       SQL: SELECT * FROM gamma_metrics WHERE run_id = '<run_id>';") | GAMMA-CTX |
| fix_td_new_12_shadow_flag.py | 177 | print(f"       SQL: SELECT * FROM gamma_metrics_shadow WHERE run_id = '<run_id>';") | GAMMA-CTX |
| patch_s36_enh99.py | 241 | # Regex pattern matching Dhan retry_call sites only (anchored on lambda: dhan.*) | GAMMA-CTX |
| s31_weekly_attribution_diagnostic.py | 607 | resp = client.table(table).select('*').limit(1).execute() | GAMMA-CTX |
| scripts/build_data_inventory.py | 1479 | A("**A strike dimension is not the same as a strike column.** A relation with") | GAMMA-CTX |
| scripts/build_data_inventory.py | 1614 | A("**The three states.**") | GAMMA-CTX |
| scripts/build_data_inventory.py | 1622 | A("**Two verdicts, because the answer depends on whether a join is allowed.**") | GAMMA-CTX |
| scripts/build_data_inventory.py | 1657 | A("- **No cell is classified differently by the two verdicts on this run.** Every") | GAMMA-CTX |
| scripts/build_data_inventory.py | 1873 | A("*No density was measured on this run.*") | GAMMA-CTX |
| scripts/build_data_inventory.py | 1918 | A("**Read the `min` column.** A month whose median is a full chain but whose") | GAMMA-CTX |
| scripts/build_data_inventory.py | 1947 | A("by a handful of direct queries in minutes. **They are not this question.** If") | GAMMA-CTX |
| scripts/build_data_inventory.py | 2014 | f"confirmations, {len(ctx['unresolved'])} unresolved.*") | GAMMA-CTX |
| scripts/eod_health_check.py | 154 | CRON_LOG_GLOB = "cron.log.*" | GAMMA-CTX |
| scripts/patch_s80_docclose_adr025_amendment_a.py | 153 | **Clause 4 is discharged for all six. Rule 10 is not.** `gex_pin_maxpain_history` is a new table | GAMMA-CTX |
| scripts/patch_s80_docclose_adr025_amendment_a.py | 158 | narrowed or extended by this amendment.*""" | GAMMA-CTX |
| scripts/patch_s80_docclose_assumption_register.py | 56 | **What is recorded here about the documentation half, because it exists in no single entry:** the archive reflex is now on its **third consecutive session**, and the arithmetic across them is the find | GAMMA-CTX |
| scripts/patch_s80_docclose_assumption_register.py | 58 | **The fifth S80 self-correction is a different and worse shape, and is named separately so it is not absorbed into the pattern above.** A topology claim — that `~/meridian-cc` would *"re-invert the de | GAMMA-CTX |
| scripts/patch_s80_docclose_assumption_register.py | 60 | **One standing assumption is escalated by measurement without needing a row of its own.** **TD-S79-NEW-1** recorded that `GREATEST(dte,1)` overstates σ on expiry day. S80 measures that the overstateme | GAMMA-CTX |
| scripts/patch_s80_docclose_current.py | 65 | \| **Date** \| 2026-09-19 → 2026-09-22 (Session 80 — **the parity acceptance criterion, and the two off-spec layers that made the case for it.**) Two views, one table and one plpgsql function applied to | GAMMA-CTX |
| scripts/patch_s80_docclose_decision_index.py | 37 | NEW_1 = r"""\| **ADR-025** \| 2026-09-21 · **AMENDMENT A 2026-09-22, same session** \| Parity acceptance criterion — what it means for a Hedgewall-parity layer to be achieved, and when the programme is c | GAMMA-CTX |
| scripts/patch_s80_docclose_decision_index.py | 44 | NEW_2 = r"""\| ADR-025 \| Parity acceptance criterion — when a Hedgewall-parity layer counts as achieved, and when the programme is complete \| Navin / Claude \| **ACCEPTED S80 2026-09-21 — full row above | GAMMA-CTX |
| scripts/patch_s80_docclose_decision_index.py | 51 | NEW_3 = r"""*Session 80 (2026-09-19→22): **ADRs_NEW=1 — ADR-025. ADRs_AMENDED=1 — ADR-025 Amendment A, same session.** **CODE CHANGED this session** — two views, one table and one plpgsql function app | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 102 | **What it is.** Total writer pain at each candidate strike over `gex_strike_snapshots`, the argmin, | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 105 | **Why a second max-pain view exists.** `v_max_pain_by_strike` shipped at **S40 (2026-05-29)** and | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 109 | 1. **Base and history.** ENH-123 reads `gex_strike_snapshots` — 1.58M rows, no retention policy. | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 114 | 2. **Expiry scoping.** ENH-123 groups by `(symbol, run_id, expiry_date)`. The S40 view groups by | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 118 | 3. **A clock.** ENH-123 emits `ts`, `run_id`, `expiry_date`, `dte`, OI coverage and `is_fresh`. The | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 137 | **Cross-ref.** `sql/2026-09-22_s80_v_gex_max_pain.sql` · ADR-025 D5 · ADR-015 (`oi_call` / `oi_put`) | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 143 | **What it is.** ENH-123's max pain joined to ENH-81's pin zone and ENH-120's walls **on the same | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 147 | **It emits a distance and not a verdict, deliberately.** The reading the brief asked for — *"when max | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 151 | constant appears in this view and none may be added until the history supports one.** | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 158 | - **Exact coincidence is rare and concentrated.** 1.2–5.4 % everywhere **except NIFTY at 0 DTE, | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 164 | - **`max_pain_in_pin_band` is not a weaker form of coincidence.** NIFTY 6-DTE carries the *highest* | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 167 | - **No intraday drift.** Flat 09:00–15:00 on both symbols, which retired a worry that the one-run- | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 181 | **Substrate built for it.** `gex_pin_maxpain_history` (table) and `backfill_pin_maxpain_runs()` | GAMMA-CTX |
| scripts/patch_s80_docclose_enh_register.py | 190 | **Cross-ref.** `sql/2026-09-22_s80_v_gex_pin_maxpain.sql` · `sql/2026-09-22_s80_gex_pin_maxpain_history.sql` | GAMMA-CTX |
| scripts/patch_s80_docclose_session_log.py | 73 | "**(3) The −0.4σ constant — 11,795 runs, and it is a genuinely new finding.** " | GAMMA-CTX |
| scripts/patch_s80_docclose_session_log.py | 92 | "**(4) TD-S79-NEW-12 CLOSED, and the ordering was the point.** `infer_expiry_date()` now " | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 57 | \| `v_gex_pin_maxpain` \| **ENH-124.** ENH-123's max pain joined to ENH-81's pin zone and ENH-120's walls **on the same run**, emitting the distance in `gap_points`, `gap_strikes` and **`gap_sigma`**, p | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 66 | **Why the table exists at all.** `v_gex_strike_pin_zone` is **latest-run scoped by ADR-021** — its recursive walk crossed the PostgREST 8 s ceiling at 1.06M rows — so the pin band and `peak_pin_strike | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 70 | **A superseded sibling was DROPPED, not kept as a spare.** `backfill_pin_maxpain(text, date)` computed before `ON CONFLICT` could discard and timed out. A second callable path into one table is a haza | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 72 | **Rule 10 is NOT discharged for the table.** Its DDL is committed, which satisfies ADR-025 D2 clause 4; a new table is schema-affecting and still owes its own ADR — **TD-S80-NEW-7**. Committing DDL an | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 79 | \| `ingest_option_chain_local.py` \| Module-level `EXPIRY_DEPTH = {"NIFTY": 1, "SENSEX": 1}` and `select_expiries()`, plus an **appended** extra-expiry pass before the completion print, guarded by `if _ | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 81 | **The spec claim this refutes.** `option_chain_snapshots` holds **one expiry per cycle across all 2,923 cycles ever written** (`min = avg = max = 1`, `cycles_multi_expiry = 0`). `ingest_option_chain_l | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 83 | **Depth measured on the vendor tier, not assumed.** Day-level `hist_option_bars_1m` holds **21** expiries; S78's per-minute 14 was a subsample. NIFTY: W1 67.8 % · current monthly 18.8 % · W2 5.2 % · * | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 89 | \| `scripts/backfill_pin_maxpain.py` \| Drives `backfill_pin_maxpain_runs()` in 20-run chunks with retry. **Byte-identical to the run that produced the 11,795 rows** (`sha256 453f1be8…`). \| **No.** One- | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 95 | **Stage 0's inertness is observed, not inferred.** 2026-09-22 08:53 IST: `grep -c "S80 extra expiries"` on `cron.log` = **0**, paired with a row-side count that *can* fail — `max_exp = 1` on both symb | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 97 | **The −0.4σ gap is a finding, not a feature of the build.** Across 11,795 runs the pin↔max-pain gap holds medians **−0.32 to −0.66σ across both symbols, every DTE and every session hour**, never chang | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 99 | **Whether that coincidence predicts anything is UNANSWERED by design.** It is a conjunction question governed by parity-spec §5 and **ADR-009** — pre-registration, target and success criterion written | GAMMA-CTX |
| scripts/patch_s80_docclose_system_map.py | 101 | **No consumer reads either new view.** Neither Marketview nor the Pine overlay was wired this session, so the ADR-023 recency-floor obligation on the *consumer* side is undischarged for them — as it s | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 44 | \| **Mechanism, from source** \| `dhan.get_expiry_list()` at `:327` returns the **whole ladder**. `:365` takes `future_expiries[0]` and discards the rest. `:374` already parameterises the chain call by  | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 46 | \| **What history can and cannot give** \| `hist_option_greeks_1m` carries 2 expiries per minute with IV, but ends **2026-03-30**. `hist_option_bars_1m` carries **21 expiries** at day level with OI, but | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 47 | \| **Not a lost capability** \| `historical_option_chain_snapshots` shows up to 3 expiries per cycle, but **every such cycle is 2026-04-16** — `breeze_backfill_s35`, which the parity spec §1.1 records a | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 51 | \| **Status** \| **OPEN — code deployed INERT.** `EXPIRY_DEPTH = {"NIFTY": 1, "SENSEX": 1}` at commit `b094fa2`; the extra-expiry pass is behind `if _depth > 1` and does not execute. Stage 2 is `{"NIFTY | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 66 | \| **Root cause** \| All three are the same reflex — reasoning from a register or a row count when the source was available. **ADR-024 §A9 names it and attributes four of its own eight self-corrections  | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 70 | \| **Status** \| **OPEN.** Recorded in ADR-025; the spec file itself is unedited. \| | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 87 | \| **Status** \| **OPEN.** \| | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 132 | Filed as a withdrawal rather than deleted, because the error is worth keeping: **two measurements of a growing table were compared without reading their own dates.** Same family as the S78 precedent ( | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 149 | \| **Status** \| **OPEN.** \| | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 201 | \| **Status** \| **OPEN.** The expiry half must be fixed **before** stage 2 of TD-S80-NEW-1. \| | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 218 | \| **Status** \| **OPEN.** \| | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 269 | \| **Status** \| **OPEN.** \| | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 273 | \| **MEASURED S80 — the overstatement is TIME-VARYING, and it HIDES an intraday effect** \| The floor is not a constant scale error. σ_correct/σ_stated = `sqrt(mins_left/375)`, measured on 11,795 stored | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 274 | \| **Second S80 note — dispersion, not the median** \| 0-DTE carries the **tightest** IQR in the sample (NIFTY 0.199, SENSEX 0.254, against 0.32–0.41 elsewhere) while its median sits with every other ce | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 275 | \| **Status** \| **OPEN — and stronger than as filed.** The S80 measurement supplies the re-sweep's motivation: the chosen 1.5 band was calibrated under this floor, so re-deriving it under intraday σ ma | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 311 | \| **Priority** \| **S3 as filed.** It became a **blocker** at S80 — see *Why it was resolved now*. \| | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 316 | \| **CAN FIRE — proven, not asserted** \| `scripts/probe_s80_expiry_guards.py` loads the function **out of the source file by AST** and executes it in isolation — no module import, so no credentials, no | GAMMA-CTX |
| scripts/patch_s80_docclose_tech_debt.py | 317 | \| **Why it was resolved now, and why the order mattered** \| The S80 ingest change makes `option_chain_snapshots` able to hold more than one expiry per cycle. Before it, the invariant that saved this c | GAMMA-CTX |
| scripts/patch_s80_docclose_topology.py | 122 | **New exposure, and it is the third instance of one shape.** `/etc/logrotate.d/meridian` **lives only on the box**. §S68 brought the crontab under version control at `docs/registers/aws_crontab.txt` f | GAMMA-CTX |
| scripts/patch_s80_tech_debt_close_s69_new_1.py | 65 | **Why the S71 resolution lapsed, which is the part worth carrying forward.** It rested on §S71.4's measurement of **~17 MB/day ≈ 100 days headroom**, and on §S73.E's reading that free space was *risin | GAMMA-CTX |
| scripts/patch_s80_tech_debt_close_s69_new_1.py | 69 | **What remains open after this closure.** The resize bought a known interval, not an answer: **~1.76 GB of the 2.5 GB that filled the volume is still unattributed** (**TD-S80-NEW-15**), so 24 GB at th | GAMMA-CTX |
| scripts/patch_s80_tech_debt_close_s69_new_1.py | 71 | **Cross-ref.** Deployment Topology §S69 (the 2026-08-12 incident that filed this), §S71.4 and §S73.E (the superseded readings), §S80 (the closure) · Assumption Register **D.37.1–.10** · TD-S80-NEW-15, | GAMMA-CTX |
| scripts/patch_s80_tech_debt_incident.py | 59 | \| **Root cause** \| **Not established.** The leading candidate was recorded as *"~/.local 872 MB + ~/.claude 102 MB + ~/.cache 57 MB ≈ 1.0 GB, all Claude Code"*. **Measured, that attribution is wrong o | GAMMA-CTX |
| scripts/patch_s80_tech_debt_incident.py | 64 | \| **Status** \| **OPEN.** Note that **78 MB of the measured Claude Code footprint is `~/.claude/projects/-home-ssm-user-meridian-cc`** — agent transcripts, which grow every session including this one.  | GAMMA-CTX |
| scripts/patches/patch_s39_enh83_view_tau_rewrite.py | 230 | print("  3. Smoke-probe: SELECT * FROM v_gex_strike_pin_zone LIMIT 5;") | GAMMA-CTX |
| splice_s77_d35.py | 83 | r"""\| **D.35.26** \| *"`host DEFAULT 'local'::text` means the 59 `local` rows may be omission, so nothing follows about where the builder ran."* \| **REFUTED — this is the withdrawal being withdrawn** * | GAMMA-CTX |
| splice_s77_d35.py | 84 | r"""\| **D.35.27** \| *"Querying `script_execution_log` for `expected_writes IS NULL` will enumerate the writers that bypass `ExecutionLog`."* \| **REFUTED — the instrument** *[agent]* \| `expected_writes | GAMMA-CTX |

### (d) select('*') with NO gamma context within 12 lines: n=217 (listed in companion file)

### (a) string/attribute/name hits: n=4984 (volume; see 10_hits.tsv for line-level)
