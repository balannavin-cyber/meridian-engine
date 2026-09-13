# Forensic review of the base ICT experiments

**Date:** 2026-09-12 · **Session:** S77 follow-on · **Type:** read-only forensic audit
**Question:** how did Experiments 2 / 8 / 10 / 10c / 15 (Feb–Apr 2026) find large,
definite edges in base ICT structures that S77's clean cohort cannot reproduce?

**Nothing was re-run. No file was modified. No database write was issued.** Every
claim below is established by reading source and the published result registers.
All line numbers were re-verified against the files at the moment of citation.

---

## 0. Summary

The edge was produced by **a detector that conditions on bars later than the bar
it enters on**. The order-block rule declares a pattern at bar `j` only if the
close at bar `i+5` is at least 0.40 % away from the close at bar `i`, where
`j ≤ i`. The experiment then buys an ATM option **at bar `j`'s timestamp**. Every
trade in the cohort therefore begins at a price from which spot moves ≥ 0.40 %
in the trade's own direction within the next 5–10 minutes, **with certainty, by
construction**.

A 0.40 % NIFTY move is ~96 points. At ATM delta ≈ 0.50 that is ~48 points of
premium, against an ATM premium of ~55 (DTE = 0) to ~215 (DTE = 4+). The
arithmetic gives +87 % / +50 % / +33 % / +22 % across the DTE ladder. The
published figures are +121.4 % / — / +50.9 % / +49.3 %
(`merdian_all_experiment_results.md:84-87`). **The mechanism reproduces both the
magnitude and the DTE gradient of the headline result.** There is no residual
requiring a second explanation.

Five further mechanisms are present and are quantified in §3. The brief's
premise that "F-68 accounts for roughly +12 points" does not hold and is
addressed in §2.0.

---

## 1. What each base experiment actually measured

`experiment_2_options_pnl.py` **is present at repo root** — the brief's statement
that it was not visible in a listing is incorrect. It is 688 lines, last touched
in `c78b6ea` (2026-04-13).

### 1.1 Experiment 2 — `experiment_2_options_pnl.py`

| Property | Value | Citation |
|---|---|---|
| Data sources | `hist_spot_bars_1m`, `hist_option_bars_1m`, `instruments` — **the complete set** | `:133`, `:175`, `:391` |
| Patterns | `BEAR_OB`, `BULL_OB`, `JUDAS_BEAR`, `JUDAS_BULL` | `:62` |
| Pattern-set provenance | *"For the 4 proven patterns from Experiment 10/10b"* | `:6` |
| **Entry timestamp** | **`entry_ts = pat["bar"]["bar_ts"]` — the OB bar's own timestamp** | `:486` |
| Entry premium | nearest option bar close to `entry_ts`, ≤ 3 min gap, searched across ATM ± 3 strikes | `:203-235`, `:75` |
| **Exit rule** | **point lookup at `entry_ts + h`, same strike as entry** — no `max()`/`min()` over a window | `:510-514` |
| P&L | `(exit − entry) / entry × 100` | `:528`, `:92-93` |
| Filters | option close ≥ ₹5 (`:198`); entry + h ≤ 15:30 (`:507`); missing entry → `add_no_data` (`:499`); **missing exit → silently excluded from stats** (`:311`) |
| Subgroup cuts | pattern × {DTE(4), symbol(2), time-of-day(5)}, printed at **N ≥ 3** | `:603-649`, `:615/629/647` |

### 1.2 The order-block detector — `:253-272`

```
257    for i in range(n - 6):
258        future = bars[min(i+5, n-1)]["close"]
259        move   = pct(bars[i]["close"], future)
260        if move <= -min_move:                      # min_move = 0.40 (:82)
261            for j in range(i, max(i-6, -1), -1):
262                if bars[j]["close"] > bars[j]["open"] and j not in seen:
264                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BEAR_OB"))
```

The trigger is evaluated at bar `i` using `bars[i+5]`. The emitted bar is `j`,
found by searching **backward** from `i`. So `j ∈ [i−5, i]` and the confirming
evidence sits at `i+5`. **Lookahead = 5 to 10 one-minute bars**, and `:486` takes
the entry at `bars[j]`.

When `bars[i]` is itself the required candle colour, `j = i` and the guaranteed
forward move is exactly ≥ 0.40 %. When `j < i` the entry sits further back along
the same impulse, so the realised move is **larger**. The defect has no
compensating direction.

### 1.3 The Judas detector — `:275-293`

```
284    rev = bars[15:45]
288    if pct(close15, min(b["low"] for b in rev)) <= -mv * 0.50:
289        out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BEAR"))
```

Entry is bar 14 (09:29 IST); the condition reads bars 15–44 — **the next 30
minutes**. The exit is `entry_ts + 30 min` = bar 44. **The selection window and
the holding period are the same 30 minutes.** The rule is close to "enter only
those trades that were profitable."

### 1.4 Experiment 10 — `experiment_10_ict_patterns.py` (the upstream selector)

Same OB rule (`:234-235`, identical `bars[min(i+5, n-1)]`). Outcome is **spot
direction only**: `measure()` compares `nearest_price(ts + h)` to
`entry_bar["close"]` (`:159-164`). Two additional lookahead sources:

- **`find_swings` is a symmetric 5-bar fractal** — `for i in range(lb, n-lb)`
  (`:177`), `all(bars[j]["high"] <= h for j in window if j != i)` (`:181`). A
  swing at index `k` is knowable only at `k+5`. `mss_bos` filters swings to
  `idx < i` (`:366-367`) but not to `idx + 5 < i`, so BOS/MSS and OTE consume
  swing levels confirmed up to 4 bars after the entry bar.
- **`breaker_blocks` enters at the violation bar** — the bar that closed through
  a prior OB, located by scanning the 30 bars *after* it (`:270-284`). This is
  the mirror position: entry **after** the displacement rather than before it.

### 1.5 Experiment 10c — `experiment_10c_mtf_pnl.py`

Identical OB detector (`:316-333`), identical ₹5 floor (`:80`, `:175`), identical
silent exclusion of unpriceable exits (`:483`). This is the script whose table
(`merdian_all_experiment_results.md:240-246`) publishes the `NoD` column
discussed in §2.4.

### 1.6 Experiment 8 — `experiment_8_sequence.py`

Identical OB detector (`:334-335`). Its time buckets are
`09:15-10:00 / 10:00-11:30 / 11:30-13:30 / 13:30-15:30` (`:93-96`) — **different
from Experiment 2's** `09:15-09:45 / 09:45-11:00 / 11:00-13:00 / 13:00-14:30 /
14:30-15:30` (`experiment_2_options_pnl.py:117-123`). This divergence is what
makes the production skip rule unsound (§4.2).

Exp 8's sequence features are genuinely backward-looking — `bars[n-3:n]` and
`bars[max(0,n-5):n+1]` (`detect_ict_patterns.py:228-253`). **The features are
clean; the outcomes they were scored against are not.**

### 1.7 Experiment 15 — `experiment_15_pure_ict_compounding.py`

Materially more careful, and it is worth saying so: it steps bar by bar
(`:414`), passes only `bars[start:pat_idx+1]` to the detector (`:431`), and
builds HTF zones from `bars[:pat_idx]` with the comment *"only completed bars —
no lookahead"* (`:425`). **No future bar reaches the detector.**

It nonetheless **backdates the entry**. It imports the production `ICTDetector`,
which returns the OB bar index (`detect_ict_patterns.py:385`, `:506`), and takes
`entry_ts = pattern.bar_ts` (`:510`), pricing entry at that timestamp (`:466`)
and exit at `pattern.bar_ts + 30 min` (`:483`). With an 11-bar window, `detect_obs`
can only emit `j` at window index ≤ 4, i.e. **absolute index `pat_idx−10` to
`pat_idx−6`**. So the trade is entered 6–10 minutes before the information that
justified it existed, and the confirming displacement lies inside the holding
period. Same economic contamination, arrived at by a different route.

Two further defects specific to Exp 15: `get_option_price_at` returns only a
price and not the strike it came from (`:155`), so entry and exit premiums may be
drawn from **different strikes** within ATM ± 3; and the ₹5 floor is present
(`:85`).

---

## 2. Mechanisms, ranked

### 2.0 H1 (F-68 inherited) is refuted, and the brief's arithmetic premise with it

`experiment_2_options_pnl.py` references exactly three tables — `:133`, `:175`,
`:391` — and none is `ict_primitives` / `ict_primitive_outcomes`. None of the
five base scripts contains the string `ict_primitive`. The primitive layer
postdates them: `ict_primitives.py` at `bc1cb85` (2026-05-25) against
`experiment_10_ict_patterns.py` at `c78b6ea` (2026-04-13).

*Rule 0 check on this absence:* the set searched is the file's complete
`.table(` call set plus a repo-wide string match, both of which would contain
the reference if it existed. The absence is dispositive.

**Consequence for the brief.** F-68 is not a component of Exp 2's +41.9 % — it is
a different defect in a later artefact. S77's +12.80 % contaminated control is
therefore not a partial explanation to be topped up; it is not a comparator at
all. The two are the same *family* (entry anchored earlier than the confirming
evidence) at very different *magnitudes*: F-68 mis-anchors by **one bar of an
already-confirmed displacement**; M1 below mis-anchors by **the whole
displacement**. Nothing needs to account for "the rest."

### 2.1 M1 — the displacement is the selection criterion *(dominant)*

`experiment_2_options_pnl.py:257-264` + `:486`;
`experiment_10_ict_patterns.py:234-235`;
`experiment_8_sequence.py:334-335`;
`experiment_10c_mtf_pnl.py:316-333`;
`detect_ict_patterns.py:378-385` + `experiment_15_pure_ict_compounding.py:510`.

**Discriminating evidence — Experiment 0, on the same data.**
`merdian_all_experiment_results.md:14-15` reports T+30m direction at **49.7 % UP
/ 50.3 % DOWN** and *"Large moves >0.5% at T+30m: **1.3 % of all bars**"*
(`:17`). The unconditional rate of a large favourable move is ≈ 0.65 % per
direction. Exp 2's detector achieves a ≥ 0.40 % favourable move on **100 %** of
its cohort within 5–10 minutes. The only thing separating the two figures is that
Exp 2's condition is evaluated on bars that come after the entry.

**Discriminating evidence — the mirror inversion.** `BOS_BULL` and `BOS_BEAR` are
the two branches of one symmetric detector (`experiment_10_ict_patterns.py:380-386`)
and fire near-equally often — 1717 vs 1667. Their outcomes do not mirror the
detector; they mirror the *option leg*
(`merdian_all_experiment_results.md:70-79`):

| | N | WR | T+30m Exp |
|---|---|---|---|
| BOS_BULL | 1717 | 93.5 % | +33.3 % |
| BOS_BEAR | 1667 | 19.7 % | −5.9 % |
| BULL_FVG | 269 | 83.8 % | +34.1 % |
| BEAR_FVG | 225 | 11.5 % | −30.7 % |
| **BEAR_BREAKER** | **46** | **0.0 %** | **−45.6 %** |

**`BEAR_BREAKER` wins 0 of 46.** Under a fair coin that is `P = 1.42 × 10⁻¹⁴`.
No signal, however anti-predictive, produces exactly zero wins in 46 independent
trades; an outcome *determined by the selection rule* does. And the mechanism is
visible in the detector: the breaker enters at the bar that closed through the
OB (`:270-284`) — the far end of the same displacement the OB entered at the near
end. **One axis explains both extremes.** Entry before the required move:
84–94 % WR. Entry after it: 0–27 %.

Binomial tails on the headline claims, against Exp 0's own base rate:

| Claim | Source | P under null |
|---|---|---|
| Exp 10 BEAR_OB 92.6 % of 68 (spot) | `results:216` | 5.4 × 10⁻¹⁴ |
| Exp 2 BULL_OB 88.9 % of 81 | `compendium:1253` | 8.4 × 10⁻¹⁴ |
| Exp 10c BOS_BULL 93.5 % of 654 scored | `results:78` | 2.2 × 10⁻¹³¹ |
| Exp 10c BOS_BEAR 19.7 % of 654 scored | `results:79` | 6.9 × 10⁻⁵⁹ |

### 2.2 M2 — Judas: selection window ≡ holding period

`experiment_2_options_pnl.py:284-289`. 30 bars. Accounts for JUDAS_BULL +15.2 % /
JUDAS_BEAR +11.6 % (`compendium:1255-1256`). Lower than the OB figures because
a 50 %-retracement threshold is a weaker constraint in premium terms than a
fixed 0.40 % displacement.

### 2.3 M3 — the pattern set was selected on the cohort it was then scored on

`experiment_2_options_pnl.py:6` — *"For the 4 proven patterns from Experiment
10/10b."* Exp 10 ran the same detectors over the same Apr 2025 – Mar 2026 window
and scored them on spot direction; its four winners became Exp 2's universe.
**No holdout separates the selection from the validation.** Exp 2's headline is,
structurally, a re-report of the winners of a prior pass over identical data.

This also explains the register's shape: `merdian_all_experiment_results.md:70-79`
carries ten patterns under the heading "EXPERIMENT 2" while the surviving script
handles four (`:62`). The ten-pattern table is the pre-narrowing run.

### 2.4 M4 — left-tail truncation, on two channels, one of them uncounted

`MIN_OPTION_PRICE = 5.0` (`:73`) is applied when the lookup is built (`:198`), so
any option bar priced under ₹5 is **absent from the data structure entirely**.

- **Channel A — entry missing.** Counted as `add_no_data` (`:499`), surfaced as
  `NoD`.
- **Channel B — exit missing.** `pnl_dict[h] = None` (`:526`); `PnlBucket.add`
  appends only non-`None` values (`:311`). The trade **increments `n_patterns`
  but never enters the P&L statistics**. An exit goes missing precisely when the
  option decayed below ₹5 — that is, when the trade was a near-total loss.

Channel B removes the worst outcomes and leaves no trace in the reported
pattern count. Its magnitude is visible in the one place the registers published
`NoD` (`merdian_all_experiment_results.md:240-246`):

| Pattern | N reported | NoD | actually scored | dropped |
|---|---|---|---|---|
| BULL_OB | 101 | 66 | 35 | **65 %** |
| BEAR_OB | 68 | 39 | 29 | **57 %** |
| BULL_FVG | 269 | 149 | 120 | **55 %** |
| BOS_BULL | 1717 | 1063 | 654 | **62 %** |
| JUDAS_BULL | 32 | 13 | 19 | 41 % |

**The N carried into the compendium is the pre-drop pattern count, not the
scored count.** `compendium:1253` cites BULL_OB N = 81; the script prints both
`Patterns:` and `N scored` (`:343-345`, `:355`) and the larger number was
transcribed. Any power or confidence statement built on those N values is
overstated by a factor of roughly two to three.

### 2.5 M5 — post-hoc subgroup mining, at N ≥ 3

`experiment_2_options_pnl.py:615`, `:629`, `:647` print any cell with
`n_patterns >= 3`. Across 4 patterns × (4 DTE + 2 symbols + 5 time buckets) the
script emits on the order of 40 cells from ~144 OB trades. The compendium then
reports the maxima as findings: `BULL_OB|DTE=0 100 % WR N=13` (`:1259`),
`BEAR_OB|MORNING 100 % WR` (`:1264`), `BULL_OB|AFTERNOON 100 % WR` (`:1266`).

`compendium:1287` then makes this explicit: **TIER1 is defined as "100 % WR
setups."** The tier structure is the argmax of a set of small, noisy,
multiply-tested cells, with no correction and no holdout — and it is the input to
Kelly sizing (`merdian_utils.py:194-196`).

`compendium:1266` reads the adjacent cells `BULL_OB|AFTERNOON 100 %` against
`BEAR_OB|AFTERNOON 17 %` as *"asymmetric: afternoon kills bear, supercharges
bull."* That is a causal story fitted to two small cells of a mined grid — the
pattern CLAUDE.md's anti-pattern list names as *"inventing an explanation to make
data points fit."*

### 2.6 M6 — "Expectancy" is algebraically the mean

`:324-325`: `wr = len(winners)/n`, `avg_w = sum(winners)/len(winners)`,
`exp = wr*avg_w + (1-wr)*avg_l`. Substituting, `wr*avg_w = sum(winners)/n` and
`(1-wr)*avg_l = sum(losers)/n`, so **`expectancy ≡ avg`**, exactly. The column
carries no information beyond the mean it sits next to, yet the ship criterion
is stated on it — *"Expectancy > 5 % at T+30m = tradeable edge after costs"*
(`:678`, `:559`). No risk adjustment was ever applied.

### 2.7 Minor contributors, named for completeness

- **Strike chosen by data availability.** `:216-231` scans ATM ± 3 and keeps the
  strike whose bar is **nearest in time**, not nearest in moneyness. Direction of
  bias is not determined; it adds variance and makes "ATM" a misnomer for part of
  the cohort.
- **Entry premium may post-date the entry.** `:224` considers `idx-1` and `idx`
  with `idx = bisect_left`, so the entry price can come from up to 3 minutes
  *after* `entry_ts`. This works **against** the measured edge and is not a
  contributor.
- **Expiry index built from 12 sampled dates.** `merdian_utils.py:110-115`;
  `nearest_expiry_db` falls back to the last known expiry when the date is past
  all of them (`:166-170`). Both are marked `DEPRECATED 2026-04-21 (OI-26)`
  (`:103`, `:159`). DTE labels — and therefore every DTE subgroup in §2.5 — may
  be misassigned near the sampling boundaries.

---

## 3. Quantitative account of +41.9 %

**Assumptions, stated before the number** (per Rule 0, clause 3): NIFTY spot
≈ 24,000 over the window; ATM delta ≈ 0.50; ATM weekly premiums ≈ ₹55 (DTE 0),
₹95 (DTE 1), ₹145 (DTE 2–3), ₹215 (DTE 4+). A 0.40 % move is 96 points → ~48
points of premium.

| Bucket | premium | 48 / premium | published |
|---|---|---|---|
| DTE = 0 | 55 | **+87.3 %** | +121.4 % (`results:84`) · +107.4 % (`compendium:1259`) |
| DTE = 1 | 95 | +50.5 % | — |
| DTE = 2–3 | 145 | **+33.1 %** | +50.9 % (`results:86`) |
| DTE = 4+ | 215 | **+22.3 %** | +49.3 % (`results:87`) |
| cohort blend | | **≈ +40 %** | **+41.9 %** (`compendium:1253`) |

**M1 alone accounts for the whole of +41.9 %.** The blended estimate lands within
two points of the published headline, and the monotone DTE gradient — steepest at
expiry, flattest at DTE 4+ — falls straight out of the premium denominator. It
requires no behavioural claim. `compendium:1259` attributes DTE = 0's figure to
*"gamma explosion on expiry day"*; the same number is produced by dividing a
fixed point-gain by a smaller premium.

Published values run above the arithmetic, which is expected and has three
identified sources, all in the same direction: the realised move exceeds 0.40 %
whenever `j < i`; gamma convexity adds to a pure-delta estimate; and M4 removes
the left tail.

**Apportionment.** M1 is dominant and sufficient. M4 is real but bounded — it
truncates outcomes below roughly −90 % and, on the `NoD` evidence, is large in
*sample* terms (55–65 % unscored) while modest in *mean* terms. M3 and M5 do not
inflate the pooled +41.9 % at all; they inflate the **subgroup** claims, which is
where they did the damage (§4). M6 mislabels the statistic without changing it.

**One cell the mechanism does not explain.** `BEAR_OB|DTE=0` is published at
+7.3 % / 66.7 % WR (`compendium:1261`) where the arithmetic predicts the *largest*
figure of the ladder. `results:85` gives +72.5 % for the same cell. The two
registers disagree by 65 points on one cell, and neither is reconcilable with the
other under any reading. Recorded as unsettled (§5.2).

---

## 4. What is unsafe, and what reached production

### 4.1 Unsafe by construction

Every TIER1 and TIER2 entry at `compendium:1287-1303` derives from the
experiments above. TIER1 is *defined* as the 100 %-WR cells (`:1287`), which is
M5 stated as a policy. The SKIP list (`:1313-1322`) inherits the same defect with
its sign flipped — `BEAR_FVG | HIGH context −40.2 %` and `BEAR_OB | AFTERNOON
−24.7 %` are M1-mirror artefacts (§2.1), not measured aversions.

The registers also disagree with each other on Exp 2's own headline:

| | compendium | all_experiment_results |
|---|---|---|
| BULL_OB | N=81, 88.9 %, +41.9 % (`:1253`) | N=101, 93.5 %, +70.0 % (`:71`) |
| BEAR_OB | N=63, 73.0 %, +34.9 % (`:1254`) | N=68, 75.9 %, +43.2 % (`:70`) |
| BULL_OB DTE=0 | N=13, +107.4 % (`:1259`) | N=20, +121.4 % (`:84`) |

Two files carry different numbers under one experiment name. Neither cites a run
log. This is independent of the contamination and unresolved by it.

### 4.2 What reached production — and one rule that is wrong twice over

**`assign_tier` is live**, at `detect_ict_patterns.py:264-314`, consumed by
`build_trade_signal_local.py:923-931` via `enrich_signal_with_ict`. It carries
the experiment findings as executable policy, including `SKIP` (`:293`, `:296`),
`TIER1` (`:298`, `:306`), and a size multiplier of 1.5× on TIER1 (`:526-527`).

**The BEAR_OB afternoon hard skip gates on a window it was never measured on.**

- `MERDIAN_Signal_RuleBook_v1.1.md:59` and `:63` specify **13:00–14:30**, at
  17 % WR / −24.7 %.
- `detect_ict_patterns.py:291` cites those same numbers — *"−24.7 % exp, 17 % WR"*
  — attributing them to **Exp 8**.
- **Exp 8 did not measure that cell.** Its afternoon bucket is **13:30–15:30**
  (`experiment_8_sequence.py:96`) and its published result for it is **−2.5 %
  expectancy, 55 % WR** (`compendium:1132`). The −24.7 % / 17 % figures come from
  Exp 2's 13:00–14:30 bucket (`experiment_2_options_pnl.py:122`; `compendium:1265`).
- Production gates on `AFTNOON_START = 13:30` through `SESSION_END = 15:30`
  (`detect_ict_patterns.py:58`, `:192`).

So the live skip window **omits 13:00–13:30**, which is the half the cited
measurement covers, and **adds 14:30–15:30**, which Exp 2 measured as a separate
`POWER_HOUR` bucket (`experiment_2_options_pnl.py:123`) and never included in the
−24.7 % figure. The two available measurements of "afternoon BEAR_OB" differ by a
factor of ten (−24.7 % vs −2.5 %) and the rule cites the stronger one while
gating on the other's window. `BULL_OB → TIER1` on `MORNING`/`AFTNOON`
(`:306`) inherits the same boundary mismatch.

**Partial mitigation exists and is incomplete.** The S30 patch forces
`ict_size_mult = 1.0` when `MERDIAN_TIER_MULT_DISABLE=1`
(`build_trade_signal_local.py:112`, `:958-959`). It does **not** touch:

1. `_kelly_frac = _KF.get(_tier, 0.20)` (`:1035`) → `KELLY_FRACTIONS_C = {TIER1:
   0.50, TIER2: 0.40, TIER3: 0.20}` (`merdian_utils.py:194`). Capital allocation
   still keys off the contaminated tier.
2. `tier == "SKIP"` (`detect_ict_patterns.py:528`), which zeroes the signal
   outright. A mined-cell SKIP is not reversible by a sizing flag.

The flag's default is `"0"` — **off** (`build_trade_signal_local.py:112`). CLAUDE.md
records `MERDIAN_TIER_MULT_DISABLE=1` being written to `.env` at S30; that was not
verified here (Rule 19 — `.env` was not read). See §5.1.

**Not contaminated:** `compute_sequence_features`
(`detect_ict_patterns.py:214-261`) reads only `bars[n-3:n]` and
`bars[max(0,n-5):n+1]`. And production does **not** inherit the backdated entry —
the runner writes zones and `build_trade_signal_local.py:923` attaches an ACTIVE
zone to a signal computed at the **current** cycle timestamp. Production trades
the retest, not bar `j`. **The production defect is the thresholds, not the
anchor.**

### 4.3 Independent corroboration already in the record

`compendium:1016` — Exp 15's `BULL_FVG`: **N = 155, 50.3 % WR, +₹296 avg.**
Against Exp 10c's `BULL_FVG`: **83.8 % WR, +34.1 %** (`results:72`). Same pattern,
same period, same option leg. The difference is that Exp 15 backdates the entry
by **1 bar** while Exp 10c's detector sees the whole session. The pattern with
the smallest lookahead reads as a coin flip; the same pattern with the detector
unconstrained reads as an edge.

Inside Exp 15 the gradient holds: `BULL_FVG` (1-bar backdate) 50.3 % against
`BEAR_OB` 94.4 % and `BULL_OB` 86.4 % (`compendium:1014-1016`), which are
backdated 6–10 bars. **Win rate tracks lookahead depth, not ICT canon** — canon
gives no reason to expect OB to beat FVG by 40 points.

And this is consistent with S77's clean cohort: FVG `respected` 23–46 %, H
OB+FVG +0.76 % at 52 % WR. Exp 15's 50.3 % was the closest the base series ever
came to the clean answer, and it was read at the time as *"BULL_FVG needs MERDIAN
context"* (`compendium:1050`) rather than as the control it actually was.

---

## 5. Unsettled, with the evidence that would settle each

**5.1 — Is `MERDIAN_TIER_MULT_DISABLE` actually set in the live `.env`?**
Not checked; Rule 19 forbids reading `.env`. *Discriminator:* the Rule 19-safe
form `grep -c '^MERDIAN_TIER_MULT_DISABLE=1' .env`, or —
better, since it tests the live effect rather than the file —
`SELECT count(*) FROM signal_snapshots WHERE raw->>'tier_mult_disabled' = 'true'
AND ts > now() - interval '30 days'` against the same window's total. The flag
writes that marker at `build_trade_signal_local.py:961-962`. **This is the one
open question with live capital exposure.**

**5.2 — Which register's Exp 2 numbers are real?**
`compendium:1253-1261` and `results:70-87` disagree on N, WR and expectancy for
every row, and on `BEAR_OB|DTE=0` by 65 points. *Discriminator:* the run log.
`CLAUDE.md` Rule 21 mandates `Tee-Object` for long runs; a
`experiment_2_options_pnl_*.log` would carry both `Patterns:`/`No data:`
(`:343-345`) and per-horizon `N scored` (`:355`), settling the transcription
question and §2.4's magnitude in one read. Not searched for here.

**5.3 — How much does M4 (the ₹5 floor) contribute in *mean* terms?**
The `NoD` column bounds the *sample* loss at 55–65 % but says nothing about the
mean shift, because Channel B exclusions are invisible in it. *Discriminator:*
re-run with `MIN_OPTION_PRICE = 0.05` and the anchor held at bar `j`, then diff
the per-pattern means. Deliberately not done — re-running reproduces M1 silently,
which is the brief's constraint. It is a cheap and safe measurement **only after**
the anchor is corrected.

**5.4 — What drives the systematic bull/bear asymmetry in the non-OB families?**
BOS, FVG and Breaker each invert on the option leg while their detectors are
symmetric (§2.1). M1 explains Breaker cleanly (entry after the displacement) and
BOS partially (the swing-fractal lookahead at
`experiment_10_ict_patterns.py:177-181` is direction-conditional through the
`lsl > psl` term). It does not obviously explain BULL_FVG 83.8 % vs BEAR_FVG
11.5 % on a 1-bar-symmetric detector. *Discriminator:* for the BEAR_FVG cohort,
tabulate spot return at T+30m separately from option return. If spot is near
50/50 while options are 11.5 %, the mechanism is on the premium side (put skew,
IV behaviour on up-moves, the ₹5 floor biting harder on PE); if spot is also
~11 %, it is a further selection defect in `fvg()`.

**5.5 — Does anything else in production consume a mined tier?**
`assign_tier` and `KELLY_FRACTIONS_C` were traced. `ict_htf_zones.ict_tier` is
also read (`build_trade_signal_local.py:982`, `:1008`) and written by a different
builder, not audited here. *Discriminator:* `grep -rn "ict_tier\|htf_tier"` across
the live writer set, then check each consumer for a gating rather than
observational use.

**5.6 — Which of the ten patterns in `results:70-79` came from which script?**
The surviving `experiment_2_options_pnl.py` handles four (`:62`). The ten-pattern
table is attributed to "EXPERIMENT 2" but must predate the narrowing recorded at
`:6`. *Discriminator:* `git log -p --follow` on the file across `c78b6ea`, or the
run log per 5.2. Only one commit touches the file, so the pre-narrowing version
may not be in history at all — in which case the table's provenance is
unrecoverable and should be marked so.

---

## 6. The finding in one line

**The base ICT experiments did not measure whether an order block predicts a
move. They measured what an option is worth when you buy it immediately before a
move the selection rule already required to have happened** — and the 0.40 %
displacement threshold, divided by the ATM premium at each DTE, reproduces the
published numbers to within two points.

---

*Read-only audit. No file modified, no experiment re-run, no database write.
Line numbers verified against files as cited, 2026-09-12.*
