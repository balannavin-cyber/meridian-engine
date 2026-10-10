# CC prompt — 06-Oct SENSEX trade replay against MERDIAN state

Read-only research task. Follow CLAUDE.md. Use `bin/roq.sh` (merdian_ro) only; no writes to any table and no commits. Put all artefacts in `scratch/s91_1006/`.

## Goal
Rebuild, cycle by cycle, what MERDIAN knew on **Tue 2026-10-06, SENSEX, front expiry 2026-10-08 (2DTE)**, 09:15–15:30 IST. Put the operator's paper trades on that timeline, with premiums, and say what the system was showing at each decision.

## Step 0 — schema and clocks first (data-access rules)
- Pull `information_schema.columns` for every relation below before writing any SQL. Do not assume column names.
- `ts` columns are real UTC, so convert with `AT TIME ZONE 'Asia/Kolkata'`. State the clock of each source in the report.
- Front expiry = 2026-10-08. Session gate: drop the 02-Oct-style frozen-spot rows if any appear.

## Step 1 — sources, all filtered to 06-Oct SENSEX
| Source | What to take |
|---|---|
| `gex_cycle_history` (ENH-133; first live cycle was 06-Oct 09:15) | every column, every cycle: pin strike, pin_state, held_for, conc/HHI, runner-up and margin, top-5 shares, net γ, flip |
| `gamma_metrics` | per run: spot, net_gex, flip_level, regime, run_id, ts |
| `gex_strike_snapshots` | per run, per strike: signed net γ. Derive the largest +γ and −γ strike near spot and the dampening/amplifying boundary |
| `option_chain_snapshots` (front expiry, FULL cycles) | per cycle, per strike: CE/PE ltp, **bid, ask**, OI, iv, delta, gamma. Derive the **put OI wall and call OI wall** each cycle the way `v_gex_strike_walls` does (read its definition with `pg_get_viewdef` and replicate it exactly). Derive the ATM straddle (priced move) |
| `v_gex_repriced_flip` definition | replicate per cycle if it can be done from OCS; otherwise state that it can't |
| `signal_snapshots` | per cycle: action, regime, entry_quality, trade_allowed, flip |
| `market_spot_snapshots` | 1-min spot for the high/low path and the 15:15–15:30 auction window |
| `weighted_constituent_breadth_snapshots` | per cycle; flag frozen inputs (MV-9) |

Also reuse `scratch/s89_1001/ladder_replay_1001.sql`, parameterised for 2026-10-06 / expiry 2026-10-08, to get the same per-cycle columns as the 10-01 reference: leader, L/S, runner-up %, HHI, script flip, flow Δ vs book Δ, and CE write / CE cover / PE write / PE long build / PE unwind. Keep its definitions and name them as the script's.

## Step 2 — the trades (Sensibull paper, 5 lots = qty 100, lot 20)
Carried in from 05-Oct: **long 71500 PE @208.20, short 71900 PE @270.10.**

Fills on 06-Oct (avg price; times NOT known unless given below):
| Leg | Action | Price |
|---|---|---|
| 71900 PE | buy to close | ≈167.85 |
| 71500 PE | sell to close | ≈34.45 |
| 72200 PE | sell, then buy back | net +100.75/unit (entry and exit unknown) |
| 72400 PE | sell, then buy back | net +26.15/unit (entry and exit unknown) |
| 73000 CE | sell (open, held) | 191.00, "early in the day" |
| 73000 PE | sell (open, held) | 377.90, late |
| 72600 PE | buy (open, held) | 210.80, ~15:12 |
| 73300 CE | buy (open, held) | 174.10, ~15:12 |
| Close marks | | 72600 PE 175.15 · 73000 CE 329.30 · 73000 PE 330.00 · 73300 CE 195.10; SENSEX close 73,067.81 |

**Timing the fills:** for every leg with a known price, list each cycle where that price falls inside [bid, ask] (or within ±2 % of ltp where bid/ask is missing), and give the most likely fill window. Flag where it's ambiguous. Don't guess the 72200/72400 entries; list the cycles where a sell-then-cover could have produced those per-unit gains, and mark them as candidates only.

## Step 3 — the timeline the operator asked for
One table per 5-minute cycle: IST · spot · Δ · net γ and sign · flip and spot−flip · put OI wall · call OI wall · pin strike / pin_state / held_for · HHI · runner-up % · straddle ±% · flow vs book · CE write/cover · PE write/unwind · signal action · **the operator's open book and its MTM at that cycle** (from bid/ask mid) · a marker where a trade happened.

Then answer, with times and numbers:
1. When did the **put OI wall** move 72,100 → … → 72,500? Did the flip move with it? Which came first, the wall or spot?
2. Where was the dampening band (first +γ strike above spot, largest +γ strike) at the 73000 CE fill window, and did it hold or get pushed up through the day?
3. What did flow vs book and the CE/PE classes say in the hour after the 73000 CE sale? Was call writing or covering dominant?
4. When was the first cycle a disciplined operator should have cut the 73000 CE? Test both triggers: (a) put wall prints a new high after the sale, (b) CE mid ≥ 1.5 × 191. Give the time and the cost at each.
5. Pin and HHI through the day: did anything settle, and where?
6. Regime: when did net γ change sign, and where was spot relative to the flip at each change?
7. The closing window 15:15–15:30: the 1-min spot path and what it did to the marks.

## Step 4 — counterfactuals (same prices, bid/ask mid)
- A. Close the 71900/71500 spread **together** at the 71900 PE fill cycle, versus what was done.
- B. Same day without the 73000 CE (and so without the 73000 PE repair), wings unchanged.
- C. 73000 CE cut at trigger 4a, then at 4b.
- D. Put spreads rolled one strike under the put wall at each wall step, 5 lots, 200-point width, held to the close.
Report each as rupee P&L at the 15:30 marks, and say clearly that these are mid-price estimates.

## Step 5 — also record
- Which Marketview fixes (MV-1…MV-5, MV-9) were live during the 06-Oct session. Take this from deploy/git times, so we know what the operator's screen got wrong while he traded.
- Any gaps: missing cycles, ATM_ONLY rows, stale ltp (the 10-01 stale-ltp/iv defect), `gex_cycle_history` gate=false rows.

## Output
- `scratch/s91_1006/replay_1006.csv`, one row per cycle with all of the above.
- `scratch/s91_1006/replay_1006.sql` (sha256 in the report).
- `scratch/s91_1006/report_1006.md`, in the structure of `ref_2026-10-01_SENSEX_0DTE.md`: why the day matters, method/definitions, phases, the answers to Step 3, the counterfactual table, limits.
- Print the report to the terminal at the end so it can be pasted back.

Limits to state: n = 1, thresholds chosen after looking, nothing here is a rule.
