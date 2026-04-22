## 2026-04-17/18 — Research + Infrastructure — MTF OHLCV Build + Experiments 17-27b

**Goal:** Build 5m/15m OHLCV infrastructure and run experiment series to validate/reject LONG_GAMMA gate, breadth gate, momentum gate, and sweep reversal signal.
**Session type:** architecture + research

**Completed:**
  - Zerodha token refreshed, Dhan token refreshed, 36 ICT zones built, Pine Script updated to v7
  - Fixed IndentationError in `run_option_snapshot_intraday_runner.py` (breadth block at wrong indent from force_wire_breadth.py patch)
  - Live NIFTY trade: BUY_CE manual ICT sweep reversal — PDL sweep below 24,136 → rejection off W PDH 24,054-24,094 → +25%
  - Built `hist_spot_bars_5m` (41,248 rows) and `hist_spot_bars_15m` (14,072 rows) from 1m aggregation
  - Built `hist_atm_option_bars_5m` (27,082 rows) and `hist_atm_option_bars_15m` (9,601 rows) with PE/CE OHLC + wick metrics pre-computed
  - Built `hist_pattern_signals` (6,318 rows) — backfilled on 5m bars with option premium outcomes
  - Confirmed: all ICT pattern detection must operate on 5m bars. 1m = execution granularity only.
  - Exp 17: LONG_GAMMA blocks BEAR_OB correctly (54.6% WR) — gate confirmed
  - Exp 18: OI walls and ICT zones are independent (+4.5pp lift = noise) — OI synthesis REJECTED
  - Exp 19 (5m): No LONG_GAMMA asymmetry — BULL_OB 50.5% vs BEAR_OB 49.7% — symmetric gate correct
  - Exp 20 (5m): Momentum alignment +22.6pp lift — ALIGNED 60.9% vs OPPOSED 38.3% — confirmed as hard gate
  - Exp 23/23b/23c: Sweep reversal 17-19% WR with no quality filter rescue — discretionary only, ENH-54 REJECTED
  - Exp 25 (5m): Breadth 1.0pp spread across regimes — breadth is noise — ENH-43 remove hard gate
  - Exp 26: Option wick 1.7pp lift — no edge. SHORT_GAMMA PE wick 76.9% (N=13) — monitor only
  - Exp 27: ICT in premium space — 37K signals, too loose, no broad edge
  - Exp 27b: Small PE premium sweep <1% = 64.5% WR (N=107) — ENH-45 PROPOSED
  - ENH register updated to v6, Open Items register updated to v7
  - All committed: 4392610 → 2dac848 → d9e8293

**Open after session:**
  - C-08: `latest_market_breadth_intraday` is VIEW not TABLE — upsert silently fails — breadth stale
  - OI-11: Remove breadth hard gate from signal engine (ENH-43) — build pending
  - OI-12: Add momentum opposition hard block to signal engine (ENH-44) — build pending
  - OI-13: Patch script syntax validation standard — document in Change Protocol
  - OI-14: Shadow gate sessions 9 and 10 (Apr 14/15) — verify pass/fail
  - OI-15: Premium sweep monitoring — log live PE sweeps <1%, target 50 before building ENH-45
  - AWS Shadow Runner: FAILED since Apr 15 — 87h+ stale — needs investigation

**Files changed:**
  build_spot_bars_mtf.py, build_atm_option_bars_mtf.py, build_hist_pattern_signals.py,
  build_hist_pattern_signals_5m.py, fix_atm_option_build.py, fix_expiry_lookup.py,
  fix_runner_indent.py, experiment_17_v2.py, experiment_18_confluence_rerun.py,
  experiment_19_gamma_asymmetry.py, experiment_20_25_momentum_breadth.py,
  experiment_23_sweep_reversal.py, experiment_23b_sweep_htf_confluence.py,
  experiment_23c_sweep_quality.py, experiment_26_option_wick_reversal.py,
  experiment_27_premium_ict.py, experiment_27b_premium_small_sweep.py,
  run_option_snapshot_intraday_runner.py (indent fix),
  MERDIAN_Enhancement_Register_v6.md, MERDIAN_OpenItems_Register_v7.md

**Schema changes:**
  - NEW: hist_spot_bars_5m (41,248 rows)
  - NEW: hist_spot_bars_15m (14,072 rows)
  - NEW: hist_atm_option_bars_5m (27,082 rows) — PE/CE OHLC + wick metrics + IV OHLC
  - NEW: hist_atm_option_bars_15m (9,601 rows)
  - NEW: hist_pattern_signals (6,318 rows) — pattern signal store with option P&L outcomes

**Open items closed:** none

**Open items added:** OI-11, OI-12, OI-13, OI-14, OI-15, C-08

**Proposals rejected:** ENH-54 (sweep reversal signal), OI wall synthesis, LONG_GAMMA asymmetric gate

**Git commit hash:** d9e8293

**Next session goal:** Implement OI-11 + OI-12 together — remove breadth hard gate and add momentum opposition block in build_signal_v3.py, then shadow test for 5 sessions.

**docs_updated:** yes
