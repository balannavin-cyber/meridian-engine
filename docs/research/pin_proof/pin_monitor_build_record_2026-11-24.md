<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/pin_monitor_build_record_2026-11-24.md -->
# Pin monitor - build record and pre-data clarifications (MR-PIN3, Tue 2026-11-24)

Read with `pin_monitor_prereg_FROZEN_2026-11-24.md` (the frozen design; not edited) and `ruling_shadow_dropped_2026-11-23.md`. The full text of the clarifications is on the box in `~/meridian-cc/docs/research/pin_proof/monitor/build/DECISIONS.md` (to git with the monitor folder). Figures below are from Claude Code's build report pasted by the operator; no data row of any trading day was read in the build.

## Operator rulings and clarifications, all before any data read
- Waiver: the 08:30-15:40 IST no-box-work window was lifted for Tue 2026-11-24 only (market holiday).
- R1 Expiry: the pin, the nearest-to-spot strike and the band are taken on the **front expiry of the run** (earliest expiry present); the Board pin is joined on the same run and expiry. The frozen text did not fix this.
- R2 `hist_spot_bars_1m.bar_ts` is **true UTC** for rows from 2026-04 (Data Inventory section 12): the 15:29 IST bar is `<date> 09:59:00+00`. The runner stops unless the day's last bar label is 09:59 UTC.
- R3 The 15:29 bar is the **CAS settled close**, written by `capture_cas_close.py` on cron 16:20 IST (ADR-022). The daily run is refused before **16:30 IST** (replaces the frozen text's 15:40). The line records the read time. Limit: the 08:50 IST reconciliation next morning can correct that bar; the line keeps the evening value. The frozen text's "settlement price not held" was wrong in the cautious direction: this bar is the settled close of the index.
- R4 Pin Band: the frozen text named "the rule used in fix/followup"; that folder never recomputed a band. The band is recomputed per run from the live `v_gex_strike_pin_zone` definition (length 3523, md5 `89c9ac6aef9eb332ddd28f9062d0e21e`, pg 17.6), tau resolved as the view does (`COALESCE(get_parameter_num('pin.tau.'||symbol), 0.3)`), `tau_used` recorded.
- R5 `gex_cycle_history` added to the EXPLAIN gate's guarded tables (the build conditions omitted it).
- Implementation notes recorded by Claude Code and accepted: "pin outside band" share uses runs with both a band and a pin as denominator (runs with a band and no pin reported beside it); market hours 09:15-15:30 inclusive; clear lead = 5 % applied to the VS pin's own lead (replay v2 applied it to the own-solve lead, so the two shares are not comparable).

## Build state (box, `~/meridian-cc/docs/research/pin_proof/monitor/`, not yet in git)
- `PREREG.md` sha256 `38b366897edd8e06af542988055dc1319a65f36b9995074cc6bfd88ec2a69a22` (3,453 bytes; the frozen text without the PK header and provenance lines).
- Self-test 210 pass, 0 fail: three hand-computed synthetic days (42 fields each), 8 band walks, timestamp checks, seven mutation controls (all break at least one check), gate-detector checks, and a cross-check of the monitor's VS ranking against `fix/order_check_rev3/indep.py` on 11 groups (55 comparisons equal).
- EXPLAIN gate on the runner's own generated queries: PASS; index scans on `gex_strike_snapshots`, `gex_cycle_history`, `hist_spot_bars_1m`; Seq Scan only on `instruments`.
- `run_day.sh <date>` refuses: a date before 2026-11-25 or not a real date; a date already in the csv; before 16:30 IST of the date; a failing self-test. Each refusal was exercised. Day-folder `SHA256SUMS` is built and verified after the log is complete (verify shown to fail on an altered file, exit 4).
- `monitor/SHA256SUMS`: 41 files, all OK. No `pin_monitor.csv` exists. No commit. Secret sweep clean.

## Not done / open
- No plumbing dry run on real rows was made; the first contact of the parsers with real data is the first recorded day, Wed 2026-11-25, after 16:30 IST. The guards stop the run if a label or row shape is not as expected.
- The monitor folder is to be committed to git (branch off main, PR) before the first recorded day.
- Engine to be told: shadow dropped (ENH-149 text, STREAMS X10); monitor exists; scheduling it later would be an intake row.
