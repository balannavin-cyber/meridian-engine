<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/pin_monitor_prereg_FROZEN_2026-11-24.md -->
# Pin monitor - daily measurement discipline, pre-registration (FROZEN 2026-11-24 08:59 IST on the operator's "Draft approved")

Written Tue 2026-11-24, MR-PIN3. Replaces the dropped ten-day shadow (`ruling_shadow_dropped_2026-11-23.md`). Operator rulings 2026-11-24: pin time 14:30 IST; forward only, no back-fill; scope both parts and the review threshold "as recommended"; first recorded day Wed 2026-11-25 (24 Nov is a market holiday). No outcome figure had been read at freeze.

Operator-only. Read-only. Nothing here authorises a Board change, and no figure here is a verdict on the pin before the review rule below says a review is due.

## What is recorded: one line per symbol (NIFTY, SENSEX) per trading day
Pin = the VS gross pin (rank 1 of the rule in `sql/2026-11-23_s107_v_gex_strike_rank_gross.sql`: one gamma per strike, 5 % band, gross_cr > 0, tie-break nearer to spot then lower strike), recomputed per run from `gex_strike_snapshots`. The view holds only the latest run and is not the source.

Part 1 - is it computed, and how does it sit beside the Board (no outcome data):
- runs in market hours (09:15-15:30 IST); runs with a rankable pin (count and share)
- median over runs of: ranked strikes; share of ranked strikes with one-leg gamma; strikes with OI and no gamma
- share of runs with a clear lead (definition unchanged from `pin_live_replay_prereg_v2_FROZEN_2026-11-21.md`)
- number of times the pin strike changed between consecutive runs
- share of runs where pin = Board pin (`gex_cycle_history.pin_leader_strike`); denominator = runs with both
- share of runs where the pin is outside the Pin Band (band recomputed per run by the rule used in `fix/followup`; denominator = runs with a band)

Part 2 - where did price finish relative to the pin (outcome; descriptive):
- Reference run: the first run with ts in [14:30:00, 14:35:00) IST. No such run = the day's Part 2 fields are blank and the day is counted as "no reference run".
- Three strikes taken at that run: P = VS pin; B = Board pin of that run; N = the listed strike nearest that run's spot (tie: lower).
- Close = close of the 15:29 one-minute spot bar (minute-start label, `hist_spot_bars_1m`). The exchange settlement price is not used (not held); stated limit on expiry days.
- For each of P, B, N: distance = abs(close - strike) in index points, and in strike steps (NIFTY 50, SENSEX 100). Also dte and an expiry-day flag.
- Also recorded: spot at the reference run, and abs(close - spot at reference) so a quiet afternoon is visible.

## Review rule (fixed now)
- Weekly: the table is read as it stands. No verdict.
- First review at 20 recorded trading days per symbol, then every 20. At a review, per symbol, over days with a reference run: median distance of P, of B and of N; the count of days P is strictly nearer the close than N, than B (denominators stated); the same on expiry days alone.
- "Review due - pin not shown to add anything" if, on either symbol, P is strictly nearer than N on fewer than half of the days. That flag starts a discussion; it changes nothing by itself. Twenty days is a small sample (about four expiry days per symbol); no claim of statistical significance is made at the first review.
- Part 1 stop conditions, any day: a market-hours run with a chain and no rankable pin; or the day's line cannot be produced. These are reported the same evening.

## Rule 0 and limits
- N is the control: a pin that merely sits at spot scores the same as N and so cannot look good.
- P and N will often be the same strike near expiry; days where P = N are counted and shown, and count as "not strictly nearer".
- The 14:30 choice and the 15:29 close are fixed here and are not tuned later. A different pin time is a new pre-registration.
- Days already used by earlier studies are not recorded; the first recorded day is Wed 2026-11-25.
- A self-test on a synthetic day (hand-computed line) with mutation controls runs before the first live day and is re-run whenever the script changes.

## How it runs
After 15:40 IST, on the box in `~/meridian-cc`, through `bin/roq.sh` as `merdian_ro`; catalog first, plain EXPLAIN gate, one symbol-day per query, 5 s sleeps, stop at the first error or any query over 10 s; `ulimit -v 700000`, `python3 -B`. Output: `docs/research/pin_proof/monitor/pin_monitor.csv` (one line per symbol-day, appended), the day's raw reads in `monitor/<date>/` with `SHA256SUMS`; committed by branch and PR. If the routine proves useful, scheduling it is an engine intake row; until then the operator pastes the evening prompt.
