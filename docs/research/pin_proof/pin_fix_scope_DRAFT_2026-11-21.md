<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/pin_fix_scope_DRAFT_2026-11-21.md -->
# Pin and gamma inputs: proposal to the engine lane

Session MR-PIN2, pin lane. Rewritten in place 2026-11-22 (12:05 IST; section 4 and the flip rows corrected 12:20 IST after the operator's note and a read of the registers). It replaces the 2026-11-21 scope, which planned a separate own-solve job and table (decisions D1–D7 of that version are superseded by sections 3 and 7 here; D3 "shadow first" and D4 "show the lead, no tie threshold" stand).

**This is a proposal, not an authorisation.** The view, grants, `merdian_compute`, the signal builder and the Board are engine-owned (Doc Protocol v5.1 Rule 12): the engine authors any `sql/` file or code change and the operator applies it. No identifier is minted here; items are `PROPOSED-ID`. Nothing below changes production code, SQL, stored rows, the Board, a signal gate or a threshold.

Engine-note terms (`claude/engine_note_pin_basis_and_vendor_greeks_2026-11-18.md` §6): **R1** = a both-sides leader beside the netted one; **G2** = one gamma per strike in compute; **G1** = own solve.

## 1. Evidence (pointers; figures live in the result records)

| What | Result | Record |
|---|---|---|
| Pin definition | Textbook pin = largest gamma × (call OI + put OI); ruled 2026-11-21 | `ruling_pin_definition_2026-11-21.md` |
| Pin construction, 53 unseen days | VS on the reference pin's strike on 99.65 % (NIFTY) and 98.88 % (SENSEX) of clear-lead market runs; the only construction that met the frozen rule | `pin_live_replay_v2_result_2026-11-21.md` |
| Expiry days, near-ties, SENSEX 19 Nov | VS holds day by day; on near-ties it is the reference's first or second strike on 99.8 % / 99.7 % | `pin_vs_followup_result_2026-11-22.md` |
| Net on one gamma, 58 days, 8,595 runs | Frozen rule BETTER on both symbols: per-strike net error about halved, largest-net strike right on 96–98 % of clear runs against 77–81 % | `gamma_pipeline_audit_result_2026-11-22.md` |
| Zero gammas | Filling zeros alone delivers −2 % to +7 % of that improvement and makes the total net worse; the fault is the two vendor gammas disagreeing | same, post-hoc section |
| By day | One-gamma net better than production on 52–58 of 58 days, by measure and symbol | same |

Limits that travel with the evidence: the reference shares the one-gamma structure and uses last-traded prices; NIFTY and SENSEX are the same days and vendor; 58 days are one period (2026-08-25 to 2026-11-20); the one-gamma net keeps a residual of about 0.04 against the reference in this sample, unattributed; seven days (NIFTY 10-09; SENSEX 10-27, 10-28, 10-29, 11-11, 11-17, 11-19) have production unusually close to the reference, with no cause established. No special handling of those days is proposed.

## 2. Four quantities that are each called a pin somewhere

| # | Quantity | Rule | Where it is today |
|---|---|---|---|
| a | **Gross pin** | largest gamma × (OIc + OIp) | Nowhere in production. Proposed (section 3). |
| b | **Net peak, either sign** | largest abs(call γ·OI − put γ·OI) | Board "Pin (γ-conc)", runner-up, lead (`v_gex_strike_rank`); `gex_cycle_history.pin_leader_strike`; `/tape` PIN anchor; "Top-strike share" (`v_gex_concentration.hhi_net`) |
| c | **Largest positive net strike** | largest net among strikes with net > 0 | Board "Net-long γ strike" (`gamma_metrics.max_gamma_strike`, Python); start of the Pin Band; input to `pin_risk_score` |
| d | **Pin Band** | walk out from (c) while net > 0 and ≥ tau × peak, tau 0.3 | Board "Pin band" (`v_gex_strike_pin_zone`) |

They can name different strikes. (b) is outside (d) whenever it is a net-negative strike. The Board's "Gross \|Γ\|" tile is the sum of abs(net per strike), which is not gross exposure. **The label "Pin Band" stays (operator, 2026-11-22).** The band rule is not changed by this proposal.

## 3. Proposed now: the gross pin as a shadow view (R1, with G2's gamma)

**Rule (VS), per symbol, expiry, strike and run.** `gamma_strike` = mean of `gamma_call` and `gamma_put` when both > 0; the one that is > 0 when the other is 0 or NULL; none when neither. `gross_cr` = `gamma_strike` × (OIc + OIp) × spot² / 1e7. Strike set: abs(K/S − 1) ≤ 0.05. Rank by `gross_cr`, then nearer to spot, then lower strike. Partitioned by run, symbol and expiry, so expiries are never mixed. `lead_rel` = (top − second)/top; it is not the Board's lead in share points.

**Draft:** `2026-11-21_pin_v_gex_strike_rank_gross_DRAFT.sql`, revision 2. Its SELECT ran read-only on 2026-11-22: no sequential scan, 2.93 s, strike order identical to the tested scorer on 51/51 and 84/84 strikes. Additive; rollback is `DROP VIEW`. Grant in shadow: `merdian_ro` only.

**Requested of the engine before it is created:** (1) add a column saying which legs supplied `gamma_strike` (both / call only / put only) and a per-run count of in-set strikes with OI and no gamma, so a strike is never silently dropped (this makes revision 3 and needs the order check re-run); (2) the `sql/` file with COMMENT and GRANT as live statements, md5 registration (Rule 25) and a `data_contracts` entry (ADR-031); (3) if it ever reaches the Board, a per-1 % wrapper (ADR-032 D1).

**Shadow, time-boxed, marks fixed now.** Ten trading days containing at least two expiry days per symbol. Each evening after 15:40 IST a read-only replay as `merdian_ro` records, per market run: the Board pin (b), VS, the reference pin, whether VS is inside the wall corridor and inside the Pin Band, and frozen-OI runs. Pass = the replay v2 rule on those days (≥ 95 % of clear-lead runs on the reference's strike pooled, and ≥ 90 % of days meeting 95 % clear-lead / 85 % all-valid, each symbol). The share of runs with VS outside the Pin Band is reported, not judged. A fail stops the proposal; marks are not adjusted.

**A Board switch is a separate decision** and needs, in the same change: a note to the order-flow lane first (STREAMS X1: `/tape` anchors on (b)); the H-C and P1d pre-registrations restated; `gex_cycle_history` pin-state history marked at the switch date; ADR-024 Amendment A, ENH-125/122 text, view comments and the manual corrected.

## 4. The net on one gamma (G2): evidence for the engine's greeks study (R9), not proposed for build

What the net feeds, read from source 2026-11-22 (`fix/proposal/trace.md`, sha256 `68e0714a…a423f7a1`):

| Reader | file:line | What the code does |
|---|---|---|
| `gamma_metrics.regime` → `gamma_regime` | `build_market_state_snapshot_local.py:190`; `build_trade_signal_local.py:605-611`, `:612-618` | `LONG_GAMMA` and `NO_FLIP` set `trade_allowed = False` in `signal_snapshots` |
| same | `build_trade_signal_local.py:601-604` | confidence +8.0 for `SHORT_GAMMA` with a directional bias |
| `gamma_metrics.gamma_concentration` | `build_trade_signal_local.py:622-626` | confidence +4.0 when ≥ 0.25 |
| `gamma_regime` | `build_shadow_signal_v3_local.py:233-236` | points; dormant since S49 (ADR-019 D1) |

`regime` is `determine_regime(net_gex, flip_level)` (`merdian_compute/gamma.py:425-430`); the builder runs every cycle from `run_merdian_shadow_runner_aws.py:444/:449`. No reader was found for `gamma_zone`, `flip_distance(_pct)`, `max_gamma_strike`, `pin_risk_score`, pin state, conviction, `v_gex_strike_rank` or the Pin Band in the signal path.

**Operator, 2026-11-22 12:03 IST: the `trade_allowed` path is a leftover from an early version of the system and is to be ignored for this work.** This proposal therefore does not treat the one-gamma net as a change to trading. One item for the engine to reconcile (label VERIFY): the registers still record that gate as current — ADR-007 ("LONG_GAMMA / NO_FLIP gates preserved"), `merdian_reference.json` (`build_trade_signal_local.py` ACTIVE, ENH-35), Assumption Register §D.2 ("binary regime is correct as a gate") — and the code still writes it each cycle. If nothing acts on `signal_snapshots.trade_allowed`, those entries are stale; if something does, the next paragraph matters more.

What the audit says about that input, for whoever uses it: production's total net disagrees in sign with the reference on 9.87 % (NIFTY) and 8.57 % (SENSEX) of runs with a clearly non-zero total and on 21.83 % / 16.51 % of all runs; on about a third of runs the total is under 5 % of gross, where either calculation's error is as large as the quantity. How often the regime label itself differs was not measured.

**The flip is two different things** (registers, not re-read from source here). `gamma_metrics.flip_level` is the engine's older level: two constructions pooled in one column (a cumulative crossing nearest spot on LONG cycles, a per-strike sign flip on SHORT cycles; TD-S79-NEW-17), with a discriminator column ruled at ADR-025 B7 and no behaviour change; it feeds `regime` and is not shown on the Board. The Board's Flip is `v_gex_repriced_flip.flip` (ENH-131, the "L3 repriced flip"): net gamma repriced across spot levels from the chain's implied vols with a carry rate from futures. It does not use the vendor's gamma. It does use the vendor's per-leg implied vol, which is where the engine note locates the call/put disagreement; whether that affects the repriced flip has not been examined.

**Requested of the engine (R9 study):** take the audit as the evidence for G2 against production; decide between G2 as a stopgap and G1 (own solve), which is the longer-term direction and does not depend on vendor gamma or its precision; any change to `gamma.py` by ADR with a dated break in `gex_cr` history; no regime rule, flip rule or threshold changed alongside.

## 5. Named work item: where five-decimal gamma comes from

Read 2026-11-22: ingest stores `float()` of the vendor's field with no rounding (`ingest_option_chain_local.py:174-180`, `:308`); `option_chain_snapshots.gamma` is unconstrained `numeric`; on the latest run no value has more than five decimals; the vendor sends a literal 0, never a null, on 31–32 % of in-the-money legs with OI (0 NULLs in 128 chain files); `gamma.py:725/:729` then stores that 0 as NULL in `gex_strike_snapshots`. The per-leg vendor object is kept in `option_chain_snapshots.raw`. So the five-decimal lattice arrives from the vendor as far as the code shows. Open: confirm against `raw` on a sample; ask the vendor why in-the-money legs return 0; size the effect on SENSEX, where 33–44 % of OI sits on legs with gamma below 0.00010. Widening a column would change nothing.

## 6. Board inventory

| Component (label) | Reads | Quantity | Under one gamma | Proposed |
|---|---|---|---|---|
| Pin (γ-conc), runner-up, lead | `v_gex_strike_rank` | b | strike changes on some runs | unchanged; gross pin shadows beside it |
| Top-strike share | `v_gex_concentration.hhi_net` | max abs(net) ÷ Σ abs(net); not a Herfindahl index | changes | unchanged; `gex_cycle_history.conc_top1_share` is filled from it (`write_gex_cycle_history_local.py:388`) |
| Pin band | `v_gex_strike_pin_zone` | d | start and extent change | label and rule unchanged |
| Net-long γ strike | `gamma_metrics.max_gamma_strike` | c, second implementation in Python | changes | unchanged |
| Net Γ / Gross \|Γ\| | `v_gex_abs_exposure_1pct` | Σ net / Σ abs(net) | change | unchanged; "Gross" is not gross exposure |
| Corridor, call and put OI wall | `v_gex_strike_walls` | raw OI inside ±1.5σ; σ from the newest `volatility_snapshots.atm_iv_avg` with no age bound (`:126-138`) | no change | unchanged |
| Flip | `v_gex_repriced_flip.flip` (ENH-131) | repriced from chain implied vols and futures carry; not `gamma_metrics.flip_level` | not from vendor gamma; effect of per-leg vol not examined | unchanged |
| Pin state, conviction | `gex_cycle_history` | from b | change | unchanged |
| Regime | no tile; the Board's "regime" string is the ambient one, sameness with `gamma_metrics.regime` NOT ESTABLISHED | | | |

Also for the board list: every tile's source note reads "COMMENT not live"; `public.latest_gamma_walls` has grants and no definition in `sql/`; the wall corridor leaves spot outside on about a quarter of runs (v5 study); frozen-OI runs move any pin on the days they occur (SENSEX 19 Nov: 17 of 75 runs).

## 7. Boundaries

Permitted on approval: the shadow view of section 3 (engine-authored, operator-applied), the evening read-only replay, the checks of section 5. Not authorised by this document: any change to `gamma.py`, the signal builder, a gate or threshold; a Board switch; rewriting stored rows; a Pin Band relabel or rule change. Engine box rules stand: 1,910 MB and no swap (out-of-memory hang 2026-11-21), no analysis 08:30–15:40 IST on trading days, `ulimit -v 700000`.

## 8. Open

- Which host runs the live signal path (the registers disagree; not read by this lane).
- Whether the leg gamma and its OI come from the same moment (`gamma_call`/`gamma_put` are first-write-wins; the chain files carry no per-leg time).
- Whether a different one-gamma rule beats the mean. Not tested, and not to be tuned in this lane.
- Layer 3: nothing here tests whether net gamma describes dealer positioning (Assumption Register §D.2, S94 rows).
