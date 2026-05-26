# ADR-016 — Parameter Calibration Pattern

**Status:** PROPOSED → ACCEPTED on ENH-83 v0 clean deployment.
**Date:** 2026-05-25 (S37)
**Related:** ENH-83 (Calibration Console), ENH-81 (consumer), ADR-009 (calibration discipline)

## Context

S37 surfaced ENH-81's τ threshold as a tunable parameter — and immediately raised the question of where it should live. Today, MERDIAN has at least 8 clusters of magic-number heuristics scattered across code: `OTM_OI_VELOCITY_THRESHOLD=0.10`, `expansion_probability` weights, `gamma_zone` boundaries, TD-NEW-2 deep-ITM gamma threshold, Pine overlay proximity tiers, daily-audit thresholds, ENH-99 audit thresholds, and now ENH-81's τ. Every one of these will drift across regimes. Embedding them in code means a redeploy per tuning iteration. Env vars work but have no audit trail.

ADR-009 made calibration discipline a first-class architectural concern. This ADR operationalizes it: every tunable scalar/array becomes a row in a parameters table; every change is an event with a mandatory rationale; consumers read via a single helper.

## Decision

### Storage — temporal-immutable single table

```sql
CREATE TABLE merdian_parameters (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key           text NOT NULL,                -- e.g. 'pin_zone.tau.NIFTY'
  value         jsonb NOT NULL,                -- number, string, bool, or array
  value_type    text NOT NULL CHECK (value_type IN ('number','string','bool','array')),
  category      text NOT NULL,                -- 'pin_zone' | 'gamma_regime' | ...
  description   text,
  min_value     numeric,                       -- bound check (numeric type only)
  max_value     numeric,
  valid_from    timestamptz NOT NULL DEFAULT now(),
  valid_to      timestamptz,                   -- NULL = currently active
  changed_by    text NOT NULL,                -- 'operator' | 'backtest:exp_42' | 'system'
  change_reason text NOT NULL CHECK (length(change_reason) > 0),
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_params_active ON merdian_parameters(key) WHERE valid_to IS NULL;
CREATE INDEX idx_params_category ON merdian_parameters(category, valid_from DESC);
```

Updates are INSERT + UPDATE-old-row-`valid_to`, never UPDATE-in-place. Active value per key = the row where `valid_to IS NULL`. The check constraint on `change_reason` enforces non-empty rationale at the database layer; no helper can bypass it.

### Key naming convention — dot-hierarchical

`<category>.<param>.<symbol|scope>`. Examples:
- `pin_zone.tau.NIFTY`
- `pin_zone.tau.SENSEX`
- `gamma_regime.high_gamma_threshold_pct`
- `audit.spot_bars_per_symbol_min`
- `otm_oi.velocity_threshold`

Scope segment optional when global.

### Read API — `core/parameters.py`

```python
from core.parameters import get_param, get_all_params

tau = get_param('pin_zone.tau.NIFTY', default=0.3)
all_pin = get_all_params(category='pin_zone')  # → dict[key, value]
```

Per-process cache, TTL configurable (default 300s). Long-running services (`ws_feed_zerodha.py`, scheduler-spawned scripts) re-poll on TTL expiry. Short-lived scripts (`compute_gamma_metrics_local.py`) cache for the lifetime of the invocation.

### Write API — CLI only in v0

`merdian_calibrate.py` (ENH-83). No web UI in v0; layer 3 dashboard will hook into the same table when built.

### What lives in this table

Anything that meets all three:
1. Numeric/categorical scalar or short array consumed by code.
2. Plausibly tunable across regimes / months / vendors.
3. Not a credential, schema definition, or runtime path.

Initial migration scope (ENH-83 v0 bootstrap): pin/accel τ only. Other parameters migrate opportunistically as their consumers get touched. Aggressive forced migration risks introducing regressions in untouched code paths.

### Out of scope

- Schema-level configuration (DDL changes) — stays in migrations.
- Credentials, API keys — stay in `.env`.
- Feature flags (boolean enable/disable of code paths) — could live here in v1; v0 keeps env-var flags as-is (e.g. `MERDIAN_ENH55_ENABLED`).

## Verification

ADR-016 transitions PROPOSED → ACCEPTED when ENH-83 v0 ships cleanly (table created, helper module shipped, CLI working, ENH-81 reading τ from this layer in production).
