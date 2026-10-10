# P4 — Does the sign of net ∂Δ/∂t at 10:15 on dte-1 sessions predict the 10:15 → close direction? Pre-registration

| Field | Value |
|---|---|
| **Status** | **PRE-REGISTERED, ACCRUING.** Committed before any replay is run and before any outcome is read. Its `git hash-object` is recorded in the result doc. **It is not scored until §6's sample target is met.** |
| **Track item** | Roadmap §2.1 **P4** (rulings **S94-A** order 2nd; **S94 re-anchor (option A, 2026-10-10 09:16 IST)**: dte 1, forward accrual) |
| **Risk class** | **RO**. Reads through `bin/roq.sh`; writes nothing to the database. |
| **Gates** | **P8** stays gated on this item. If P4 does not show predictive value, P8 is **DECLINED-ON-EVIDENCE** (roadmap decision point). |

## 1. Why dte 1, not expiry day (as the roadmap first wrote it)

Two facts measured in S94, Part 0:

1. **Data.** ∂Δ/∂t is computed analytically (ENH-98 spec §2: ∂Δ/∂t = −n(d1)·dd1/dT), and that needs σ.
   `gex_strike_snapshots` (from 2026-05-25) has no IV and no delta. Only `option_chain_snapshots`
   carries IV and delta, and it starts on **2026-08-24 10:00 UTC**. The roadmap's 05-25 start is not
   reachable.
2. **Method.** The L7/L8 layer **skips dte 0** by design (ENH-98 §5; `sql/2026-10-03_s89_v_gex_greeks_l2.sql:123`,
   *"On dte 0 the four value columns are NULL"*). The 1/(2T) term diverges, and the measured
   error band degrades 7–20× at dte 0. The layer publishes at dte 1.

So the test is re-anchored to **dte 1** and accrues forward. This is the operator's choice
(option A). The alternatives were a dte-0 intraday-T method (B, which would reverse ENH-98 §5) and
recording P4 as BLOCKED (C).

## 2. Definitions (fixed at commit)

- **Eligible session (per symbol):** an open trading day on or after **2026-08-24** where the front
  expiry, i.e. the nearest `expiry_date` on or after the session date, has **dte = 1** under the
  view's own definition (IST date difference, `sql/…_v_gex_greeks_l2.sql:255`), **and** an
  `option_chain_snapshots` run exists with `ts` in **[10:15, 10:45) IST**.
- **The 10:15 run:** the first such run with `ts` ≥ 10:15:00 IST.
- **Predictor:** `net_delta_drift_time_cr_per_day` for the front expiry at the 10:15 run, from the
  **replay** in §3. Only its **sign** is used. `status` must be the view's OK value. Any other
  status makes the session ineligible, decided before the outcome is read, and counted.
- **Outcome:** `sign(S_close − S_1015)`, where S_1015 is the first deduplicated `market_spot_snapshots`
  minute at or after the 10:15 run's `ts`, and S_close is the **last deduplicated minute before
  15:15 IST**. The closing auction is excluded (ADR-022), the same convention as P1. A zero move
  makes the session ineligible, decided at scoring and counted.
- **Agreement:** predictor sign = outcome sign.

## 3. The replay (an implementation committed **before** it is run)

`p4/p4_replay.sql` is the body of `public.v_gex_greeks_l2_net` (and its strike CTEs) **with only
the `latest` CTE replaced** by a CTE selecting the §2 10:15 run for each eligible session.
Nothing else in the body may differ. A diff against the view file must show **only** that CTE.

**Parity control (Rule 0: a parity claim is asserted only by a test that compares the two).**
Before any eligible session is replayed, run the replay against the **current latest run** for each
symbol and compare every column with the live view **at the same `ts`**. Fetch `ts` alongside the
values, per the settled latest-run-scoping rule. Exact equality on both symbols is required.
**Any difference stops P4**, and the cause is diagnosed before any scoring.

**Precondition: retention.** The replay needs `option_chain_snapshots` rows for every eligible
session. `pg_cron` jobid 19 does not prune them today (R1.9: retention off). If any retention change
is proposed before P4 is scored, it must preserve these rows, or P4's sample is lost.

## 4. Degeneracy gate (fixed at commit; evaluated before the test)

ENH-98 §6 records net ∂Δ/∂t `net_over_gross` at **−0.957 to −1.000 on 7 of 8 measured arms**.
The predictor may therefore be almost always negative. A near-constant sign cannot predict
direction; it only restates the base rate of down moves.

**If one sign accounts for ≥ 90 % of eligible sessions (pooled), P4 ends DECLINED-ON-EVIDENCE:
"predictor non-discriminating"**, and the base rate of the outcome is reported descriptively.
This gate is evaluated on predictor values alone, before agreement is computed. 90 % is set from
use, not from data: below 10 % minority, a sign that flips once in ten sessions cannot carry a
decision at n = 40.

## 5. Test (fixed at commit)

- **Primary:** pooled across NIFTY and SENSEX, exact **two-sided** binomial test of the agreement
  count against p = 0.5, α = 0.05. Two-sided because P2 left the dealer reading of the sign
  REGIME-DEPENDENT, so the mapping from sign to direction cannot be assumed in advance. If the
  result is significant, the direction of agreement found is reported as the mapping, and it is
  a mapping **found, not predicted**.
- **Verdict:** significant → **PREDICTIVE (indicative)**, and P8 proceeds to its own ruling
  (amending L78-3). Not significant → **NOT PREDICTIVE**, so **P8 is DECLINED-ON-EVIDENCE**, and
  ∂Δ/∂σ / ∂Δ/∂t stay display-only.
- **Reported descriptively, no verdict:** per-symbol agreement; the T-convention check (the sign
  under exact/365 vs dte/365 vs dte/252 for each session; ENH-98 §3 measured the sign stable
  across conventions on the SENSEX dte-1 arm); the |net_over_gross| distribution.

## 6. Sample and when it is scored

- **Target: n = 20 eligible sessions per symbol (40 pooled).** At α = 0.05 two-sided, that needs
  ≥ 27 or ≤ 13 agreements of 40 (exact binomial). n ≈ 7 per symbol may already exist since
  2026-08-24. The rest accrue at about one per symbol per expiry week. **Estimated scoring:
  ~13 weeks out.** This is an estimate; the count is made at scoring time.
- **Nothing is scored, and no replay is run for outcome, before the target is met.** The replay
  and its parity control run **once**, at scoring.
- **Holidays and missed runs** reduce the count; they are never back-filled with another time of day.

## 7. Limits

- **Indicative only.** n = 40 detects only a large effect, and sessions within a symbol share regimes.
- **The positioning sign, not a dealer sign** (P2: REGIME-DEPENDENT). P4 tests whether a number
  predicts, not why.
- **dte 1 is where the T-convention matters most** for γ (ENH-98 §7; S86 observation (b)). The sign is
  reported under all three conventions, but only exact/365 (the view's) decides.
