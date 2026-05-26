# ADR-015 — Per-Strike GEX Schema v2

**Status:** ACCEPTED  
**Date:** 2026-05-25 (S37)  
**Supersedes:** ADR-014  
**Deciders:** Navin  
**Related:** ENH-80, ENH-81, ENH-82

---

## Context

ADR-014 v1 ACCEPTED earlier in S37 specified `gex_strike_snapshots` with a single `gamma` column and four derived columns: `is_local_max`, `is_flip_zone`, `is_pin_candidate_bool`. First live-fire cycle (144 NIFTY strikes + 261 SENSEX strikes) passed falsification (`SUM(gex_cr) == net_gex` to machine epsilon) but surfaced a noise problem in `is_local_max` — 39% fire rate on NIFTY, 20% on SENSEX. The booleans were correct per spec; the spec itself was misdesigned.

Three observations forced the redesign:

1. **`is_local_max` and `is_flip_zone` are functions of `gex_cr` over the `(run_id, expiry_date)` row group.** Storing a derivation as a column freezes one consumer's definition at write time. Every downstream consumer (TradingView overlay, Positioning Landscape, Pin Risk scoring) wants its own peakiness criterion — top-K, prominence-thresholded, k-neighbor window. None of them should depend on a single canonical choice.
2. **IV skew is real and load-bearing for ENH-82.** A single `gamma` column folds CE-gamma and PE-gamma at the same strike, discarding the skew differential that distinguishes a put-pinned strike from a call-pinned strike. The storage cost of splitting is one float per row; the signal preserved is the IV surface shape at strike resolution.
3. **Reference operator dashboards confirm both.** The architecture this project benchmarks against renders Positioning Landscape as a continuous area chart (no markers), shows OI-Change GEX side-by-side with classic GEX, and computes pin scores as time-series — none of which depend on a stored boolean.

## Decision

Replace ADR-014's `gex_strike_snapshots` schema with the minimum-sufficient-statistic shape:

```
gex_strike_snapshots:
  id                 uuid PRIMARY KEY
  run_id             uuid NOT NULL
  symbol             text NOT NULL
  ts                 timestamptz NOT NULL
  expiry_date        date
  dte                int
  strike             numeric NOT NULL
  spot               numeric NOT NULL
  gamma_call         double precision
  gamma_put          double precision
  oi_call            bigint NOT NULL DEFAULT 0
  oi_put             bigint NOT NULL DEFAULT 0
  gex_cr             numeric NOT NULL
  created_at         timestamptz NOT NULL DEFAULT now()

UNIQUE (run_id, strike, expiry_date)
INDEXES: (symbol, ts), (symbol, expiry_date, ts), (run_id), (symbol, ts, strike)
```

### Changes from ADR-014

| ADR-014 (v1)              | ADR-015 (v2)            | Reason                                     |
|---------------------------|-------------------------|--------------------------------------------|
| `gamma`                   | `gamma_call`, `gamma_put` | Preserve IV skew at strike resolution    |
| `is_local_max`            | dropped                 | Derivation, not data. Consumer-defined.    |
| `is_flip_zone`            | dropped                 | Derivation, not data. Consumer-defined.    |
| `is_pin_candidate_bool`   | dropped                 | ENH-82 writes its own scores table         |

### Sign convention (unchanged from ADR-014 §2.3)

Positive `gex_cr` = dampening (positioning gamma long at this strike). Negative = amplifying. The CE-positive / PE-negative convention is **positioning gamma**, not **dealer gamma**. They coincide under the standard "dealers short calls and long puts" stylized fact, which breaks during heavy put-buying regimes. See §future-work.

### Falsification rule (unchanged from ADR-014 §2.5)

`SUM(gex_cr) GROUP BY (run_id, symbol)` MUST equal `gamma_metrics.net_gex` for the same `(run_id, symbol)` within ±0.01 Cr. Live-fire verification: NIFTY abs_diff = 9.8e-11 Cr, SENSEX abs_diff = 1.2e-14 Cr (both within machine epsilon).

## Migration

1. TRUNCATE `gex_strike_snapshots` (405 rows from S37 first-fire; no consumers wired).
2. DROP `gamma`, `is_local_max`, `is_flip_zone`, `is_pin_candidate_bool`.
3. ADD `gamma_call double precision`, `gamma_put double precision`.
4. Restore writer from `_PRE_S37.py` backup, apply `patch_s37_enh80_writer_v2.py`.
5. Smoke-fire NIFTY + SENSEX, re-run §2.5 falsification.

Migration is destructive (TRUNCATE) but safe — no downstream code reads `gex_strike_snapshots` yet.

## Consequences

### Positive
- Storage layer is minimum-sufficient. Right by construction.
- ENH-81 Positioning Landscape: renders as continuous curve over `gex_cr`; peakiness defined by consumer.
- ENH-82 Pin Risk Score: calibrates its own threshold over its own peak definition; no dependency on a stored boolean that wasn't designed for it.
- IV skew preserved for free.
- OI-Change GEX (the dealer-flow proxy visible in reference dashboards) becomes a query-time view over `option_chain_snapshots` — no new writer needed (see `v_oi_prev_close_snapshots`).

### Negative
- Consumers must compute peak/flip semantics at query time. Marginal SQL cost.
- ENH-82 spec changes: pin candidates become a TOP-K or prominence-thresholded function over `gex_cr` rather than `AND is_local_max`. Cleaner anyway.

### Neutral
- Schema is slightly wider (one extra gamma column).

## Future work

### F1 — Positioning vs Dealer GEX split (deferred)

The current `gex_cr` is **positioning gamma**, not **dealer gamma**. The literature conflates these constantly. Building a separate `dealer_gex_cr_est` would require side-attribution assumptions (signed volume, OI delta direction, prior session positioning) that nobody can verify against ground truth on Indian indices (NSE/BSE don't publish dealer-level data).

**OI-Change GEX** is the practical dealer-flow proxy used by working operators. It's computed at query time over `option_chain_snapshots` history — no schema change required. See `v_oi_prev_close_snapshots` view.

Deferred to post-ENH-82. Revisit only if ENH-82 calibration surfaces a sign-convention failure mode that traces back to the positioning-vs-dealer distinction.

### F2 — Peak / flip / pin-zone views

Three derivation views to be filed under ENH-81 scope (not S37):
- `v_gex_strike_local_max` — neighbor-comparison and prominence-thresholded variants
- `v_gex_strike_flip_zone` — sign-change with consumer-chosen zero-handling
- `v_gex_strike_pin_zone` — contiguous \|gex_cr\| > τ partitioned by sign

Each consumer (overlay, dashboard, alert) picks its own variant. No storage change.

### F3 — Dealer Flow Simulator

Reference dashboards show "if spot ±0.5/1%" projected dealer-flow values. Implementable as a parameterized view over `gex_strike_snapshots` — query-time perturbation, no storage. Filed under ENH-81.

## Verification gates

ADR-015 transitions PROPOSED → ACCEPTED on first clean live-fire cycle with §2.5 falsification pass on the v2 schema. Promotes to IMPLEMENTED after 5 trading sessions of continuous run without falsification regression.

## References

- ADR-014 (SUPERSEDED) — original v1 schema spec
- ENH-80 — per-strike GEX writer
- ENH-81 — Positioning Landscape (downstream consumer)
- ENH-82 — Pin Risk Score (downstream consumer)
- S37 session log — live-fire verification results
