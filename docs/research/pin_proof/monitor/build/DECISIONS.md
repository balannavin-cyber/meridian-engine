# Pin monitor — pre-data clarifications to the frozen PREREG

PREREG.md is frozen (sha256 `38b366897edd8e06af542988055dc1319a65f36b9995074cc6bfd88ec2a69a22`)
and is NOT edited. Everything below was ruled by the operator on 2026-11-24,
**before any data read**, and is recorded here instead.

## R1 — Expiry leg (the PREREG did not fix it)

A run holds both expiry legs (ADR-030: one row per `(symbol, expiry_date, ts)`,
both legs; `gex_cycle_history_pk (symbol, expiry_date, ts)`), and the VS rule
returns a `strike_rank = 1` for **each** leg — every CTE in
`sql/2026-11-23_s107_v_gex_strike_rank_gross.sql` is keyed
`(run_id, symbol, expiry_date)` (`:117`, `:128-130`, `:136`, `:163-166`), and its
KNOWN LIMITS say "A run and expiry with no rankable strike returns no row"
(`:48-49`). "Rank 1 of the rule" was therefore ambiguous.

**Ruled:** the **front expiry of the run** — `MIN(expiry_date)` present in that
run. P, N and the band are all taken on that leg; B is joined on
`(run_id, expiry_date)` of that same leg. `expiry_date` and `dte` are written
into the line so the leg is auditable.

## R2 — `hist_spot_bars_1m.bar_ts` is TRUE UTC (corrects my reading)

I had taken the IST-labelled-`+00` convention (Rule 16 / TD-029 / S61). That is
the **legacy** era. Operator correction: rows from 2026-04 carry **true UTC**
(`MERDIAN_Data_Inventory.md` §12; source `docs/research/s106/S105_live_reads_2026-11-04.md` §5),
which is consistent with the era table in `.claude/rules/python-writers.md`
(post-2026-04-07 ⇒ `astimezone(IST)`).

**So the 15:29 IST minute-start bar is `bar_ts = '<date> 09:59:00+00'`.** T3 and
T4 use that label; T4 additionally asserts the day's **last** label is
`09:59:00+00` and stops if it is not.

## R3 — The 15:29 bar is the CAS settled close, written at 16:20 IST

`capture_cas_close.py`, cron 16:20 IST (ADR-022; same S105 note line 55). My
earlier answer on availability was "unknown"; this settles it.

**So `run_day.sh` refuses before 16:30 IST of the date, not 15:40** (this
overrides the 15:40 figure in both the PREREG and the build conditions), and the
line records `close_read_at_ist`. **Stated limit:** a reconciliation at 08:50 IST
the next morning can correct that bar; the line keeps the value read on the
evening and is not revised.

## R4 — Pin Band: the PREREG names a rule that does not exist

The PREREG says the band is recomputed "by the rule used in `fix/followup`".
`fix/followup` never recomputed a band: `followup_b.py:109,123,128,135-138` only
**quotes** the live view's lines, and `sql/qP_day.sql.tpl:16` reads the view's own
`tau_used` from stored rows — which returned 0 rows on all ten symbol-days
(followup.md B3). There is no second tau rule to collide with.

**Ruled:** the band is recomputed per run by the **live `v_gex_strike_pin_zone`
definition** read this session via `pg_get_viewdef` —
`def_length 3523`, `def_md5 89c9ac6aef9eb332ddd28f9062d0e21e`, pg 17.6
(CLAUDE.md rule 25 identity read) — with tau resolved as the view resolves it,
`COALESCE(get_parameter_num('pin.tau.'||symbol), 0.3)`, and `tau_used` recorded.
The self-test carries a hand-computed band walk and a mutant that changes tau.

Reproduced from that definition, and **not** from any constant:
- `scoped` = **all** strikes of the run and leg — there is no 5 % filter on the band.
- `strike_step` = `min` positive consecutive strike difference **within that run
  and leg**, so a sparse run yields a larger step. A leg with fewer than two
  distinct strikes produces no `strike_step` row, the anchor join yields nothing,
  and the run therefore has **no band** at all.
- `peak` = `DISTINCT ON (run, symbol, expiry)` over `gex_cr > 0`, ordered
  `gex_cr DESC, abs(strike - spot)`.
- the walk admits a neighbour at `strike ± step` only while `gex_cr > 0 AND
  gex_cr >= tau * peak_gex_cr`; `direction` keeps it from turning back.
- band = `min(strike)`, `max(strike)`, `count(*)` of the walked rows.

## R5 — `gex_cycle_history` is guarded too (2026-11-24)

The build conditions named `gex_strike_snapshots`, `option_chain_snapshots` and
`hist_spot_bars_1m`. The daily run also reads **`gex_cycle_history`** (template
T2, the Board pin), and that read was gated only by the absence of the three
named tables from its plan — the gate said nothing about the table it actually
scans. `gex_cycle_history` is therefore added to `GUARDED` in
`pin_monitor_day.py`, so a plan that seq-scans it fails the gate like any other.
Its measured plan already uses `gex_cycle_history_pk`
(`symbol, expiry_date, ts`), so this tightens the gate without changing a query.

## Mutation controls — six, plus tau

(a) reference window `[14:35, 14:40)`; (b) close from the 15:28 bar; (c)
nearest-to-spot tie to the **higher** strike; (d) distance to spot at reference
instead of to the close; (e) `gross_cr > 0` dropped; (f) close label taken as
`15:29:00+00` instead of `09:59:00+00`; (g) tau changed from the resolved value.

## Implementation clarifications (mine, stated rather than silently taken)

1. **Market hours** are `09:15:00 <= t <= 15:30:00` IST, as this PREREG words it.
   The pin lane's frozen prereg v2 §5 used `09:15–15:29` for its own "market"
   segment. The figures are therefore not interchangeable with that study's.
2. **"Denominator = runs with a band"** read literally would put runs that have a
   band but no rankable pin into the denominator of an "outside the band" share,
   where the question cannot be answered. The share's denominator is runs with a
   band **and** a pin (`n_runs_band_and_pin`), and `n_runs_band_no_pin` is
   reported beside it so nothing is hidden.
3. **Medians.** `median_n_ranked` and `median_n_oi_no_gamma` are taken over all
   market-hours runs (a run with no rankable pin contributes 0).
   `median_share_one_leg` is taken over runs with `n_ranked > 0`, because the
   share has no denominator otherwise. Median = `statistics.median` (mean of the
   two middles on an even count).
4. **`peak` tie beyond the view's two keys.** The view's `ORDER BY` stops at
   `gex_cr DESC, abs(strike - spot)`; a remaining tie is unspecified in SQL. The
   recompute adds `strike` ascending as a third key so the result is
   deterministic. This decides nothing the view decides.
5. **The step used for distances** is the PREREG's (NIFTY 50, SENSEX 100), and the
   runner asserts it against `instruments.strike_step` rather than trusting the
   constant. The **band's** step stays the one derived per run, as the view derives it.
6. **`N` is taken over all listed strikes** of the reference run and leg, not only
   the in-band ones.

## 2026-11-26: Board pin switch recorded (MR-PIN4, on the operator's instruction)
- On Wed 2026-11-25 at about 18:08 IST the operator promoted Board `d7642c2`. From then on the Board tile labelled "Pin" shows the gross pin (`v_gex_pin_gross`), and the former Board pin is shown as "Net peak".
- The monitor's "B" (Board pin) is read from `gex_cycle_history.pin_leader_strike`. That column is unchanged, so from 2026-11-25 18:08 IST "B" is the Board's Net peak, not the tile labelled Pin. The tile labelled Pin follows the gross-pin rule, which is the monitor's "P" on the front expiry.
- Day 2026-11-25: its 14:30 IST reference run and all its market-hours runs were before the switch.
- No change to the monitor's design, code or columns. PREREG.md (frozen 2026-11-24) is not edited.
- build/out_explain_final.txt (the query-plan check output) is written only by ./run_day.sh --explain (pin_monitor_day.py:194, reached from :291), not by a dated day run. The evening routine is the plan check and then the day run, so this file changes each evening and its line in monitor/SHA256SUMS is re-hashed after the run. Found 2026-11-26 at the pre-run manifest check: the manifest and origin/main held 10469a3310f2b107447dd8a520bf93240b47326c1a97536d62d8f19f73061bc2 (the build of 2026-11-24); the box held 5320dd3ca2f23c7d21ff5455a0d39f1cb58ef69db9f96deb2f9700897a4bd803 after the plan check at 16:33 IST on 2026-11-25; after the plan check of 2026-11-26 it holds 915a4511ddf4afb70ba5a03fb2a8831744bde0db0e67f4199600fc1daf076ba1. The file holds query plans, not results. No code was changed.
