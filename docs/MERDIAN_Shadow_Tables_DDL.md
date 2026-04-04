# MERDIAN Shadow Tables — DDL Reference
**Captured:** 2026-04-04 (V18C session)  
**Source:** Supabase `information_schema.columns` live query  
**Closes:** D-09 / E-06 from Open Items Register v3  
**Total shadow tables:** 13

---

## Table Inventory

| Table | Purpose | Generation |
|---|---|---|
| `shadow_signal_snapshots` | Legacy shadow signals (pre-v3) | Retired |
| `shadow_signal_snapshots_v3` | Current live shadow signal output | Automated runner |
| `shadow_outcomes_v1` | First outcome measurement schema | Superseded by v2 |
| `shadow_outcomes_v2` | Current outcome measurement | Active |
| `shadow_replay_v1` | Replay runs against historical data | Manual tooling |
| `shadow_reconstruction_v1` | Reconstruction pass v1 | Superseded |
| `shadow_reconstruction_v2` | Reconstruction pass v2 | Superseded |
| `shadow_reconstruction_v3` | Current reconstruction — includes coverage status + SMDM | Active |
| `shadow_signal_outcomes` | WCB shadow policy outcome comparison | Active |
| `shadow_signal_validation_v1` | Signal validation layer | Active |
| `shadow_state_signal_outcomes` | State-level signal outcome tracking | Active |
| `shadow_state_signal_snapshots` | State-level shadow snapshots | Active |
| `shadow_vs_live_evaluation` | Direct shadow vs live comparison | Active |

---

## shadow_outcomes_v1

| Column | Type | Nullable |
|---|---|---|
| id | uuid | NO |
| symbol | text | NO |
| ts | timestamptz | NO |
| shadow_action | text | YES |
| shadow_confidence | numeric | YES |
| live_action | text | YES |
| live_confidence | numeric | YES |
| entry_spot | numeric | YES |
| spot_5m | numeric | YES |
| spot_15m | numeric | YES |
| spot_30m | numeric | YES |
| spot_60m | numeric | YES |
| ret_5m | numeric | YES |
| ret_15m | numeric | YES |
| ret_30m | numeric | YES |
| ret_60m | numeric | YES |
| outcome_5m | text | YES |
| outcome_15m | text | YES |
| outcome_30m | text | YES |
| outcome_60m | text | YES |
| created_at | timestamptz | YES |

---

## shadow_outcomes_v2

Adds horizon availability flags and evaluation status vs v1.

| Column | Type | Nullable |
|---|---|---|
| id | uuid | NO |
| symbol | text | NO |
| ts | timestamptz | NO |
| shadow_action | text | YES |
| shadow_confidence | numeric | YES |
| live_action | text | YES |
| live_confidence | numeric | YES |
| shadow_created_at | timestamptz | YES |
| entry_spot | numeric | YES |
| spot_5m | numeric | YES |
| spot_15m | numeric | YES |
| spot_30m | numeric | YES |
| spot_60m | numeric | YES |
| ret_5m | numeric | YES |
| ret_15m | numeric | YES |
| ret_30m | numeric | YES |
| ret_60m | numeric | YES |
| outcome_5m | text | YES |
| outcome_15m | text | YES |
| outcome_30m | text | YES |
| outcome_60m | text | YES |
| horizon_5m_available | boolean | YES |
| horizon_15m_available | boolean | YES |
| horizon_30m_available | boolean | YES |
| horizon_60m_available | boolean | YES |
| evaluation_status | text | YES |
| created_at | timestamptz | YES |

---

## shadow_replay_v1

Same structure as shadow_outcomes_v2 plus `replay_date` and `source_shadow_created_at`.

| Column | Type | Nullable |
|---|---|---|
| id | uuid | NO |
| replay_date | date | NO |
| symbol | text | NO |
| ts | timestamptz | NO |
| shadow_action | text | YES |
| shadow_confidence | numeric | YES |
| live_action | text | YES |
| live_confidence | numeric | YES |
| entry_spot | numeric | YES |
| spot_5m/15m/30m/60m | numeric | YES |
| ret_5m/15m/30m/60m | numeric | YES |
| outcome_5m/15m/30m/60m | text | YES |
| horizon_5m/15m/30m/60m_available | boolean | YES |
| evaluation_status | text | YES |
| source_shadow_created_at | timestamptz | YES |
| created_at | timestamptz | YES |

---

## shadow_reconstruction_v1

| Column | Type | Nullable |
|---|---|---|
| id | uuid | NO |
| reconstruction_date | date | NO |
| symbol | text | NO |
| ts | timestamptz | NO |
| action | text | YES |
| trade_allowed | boolean | YES |
| confidence_score | numeric | YES |
| direction_bias | text | YES |
| momentum_regime_v2 | text | YES |
| ret_session | numeric | YES |
| pcr_regime | text | YES |
| flow_regime | text | YES |
| skew_regime | text | YES |
| put_call_ratio | numeric | YES |
| pe_vol_oi_ratio | numeric | YES |
| chain_iv_skew | numeric | YES |
| iv_rank | numeric | YES |
| iv_regime | text | YES |
| vix_trend | text | YES |
| iv_context_low_conf | boolean | YES |
| smdm_squeeze_active | boolean | YES |
| smdm_pattern | text | YES |
| smdm_score | integer | YES |
| gamma_regime | text | YES |
| breadth_regime | text | YES |
| source_market_state_ts | timestamptz | YES |
| source_momentum_ts | timestamptz | YES |
| source_options_flow_ts | timestamptz | YES |
| source_iv_context_ts | timestamptz | YES |
| source_smdm_ts | timestamptz | YES |
| reasons | jsonb | YES |
| cautions | jsonb | YES |
| created_at | timestamptz | YES |

---

## shadow_reconstruction_v2

Same columns as v1. Captured in prior query — schema identical to v1.

---

## shadow_reconstruction_v3

Adds coverage status fields and source age fields vs v1/v2. **Current active version.**

| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | uuid | NO | |
| reconstruction_date | date | NO | |
| symbol | text | NO | |
| ts | timestamptz | NO | |
| coverage_status | text | NO | New in v3 |
| core_coverage_ok | boolean | NO | New in v3 |
| smdm_available | boolean | NO | New in v3 |
| action | text | YES | |
| trade_allowed | boolean | YES | |
| confidence_score | numeric | YES | |
| direction_bias | text | YES | |
| momentum_regime_v2 | text | YES | |
| ret_session | numeric | YES | |
| pcr_regime | text | YES | |
| flow_regime | text | YES | |
| skew_regime | text | YES | |
| put_call_ratio | numeric | YES | |
| pe_vol_oi_ratio | numeric | YES | |
| chain_iv_skew | numeric | YES | |
| iv_rank | numeric | YES | |
| iv_regime | text | YES | |
| vix_trend | text | YES | |
| iv_context_low_conf | boolean | YES | |
| smdm_squeeze_active | boolean | YES | |
| smdm_pattern | text | YES | |
| smdm_score | integer | YES | |
| gamma_regime | text | YES | |
| breadth_regime | text | YES | |
| source_market_state_ts | timestamptz | YES | |
| source_momentum_ts | timestamptz | YES | |
| source_options_flow_ts | timestamptz | YES | |
| source_iv_context_ts | timestamptz | YES | |
| source_smdm_ts | timestamptz | YES | |
| source_momentum_age_min | numeric | YES | New in v3 |
| source_options_flow_age_min | numeric | YES | New in v3 |
| source_iv_context_age_min | numeric | YES | New in v3 |
| source_smdm_age_min | numeric | YES | New in v3 |
| reasons | jsonb | YES | |
| cautions | jsonb | YES | |
| created_at | timestamptz | YES | |

---

## shadow_signal_outcomes

WCB shadow policy outcome comparison table. Compares baseline vs shadow action.

| Column | Type | Nullable |
|---|---|---|
| id | bigint | NO |
| created_at | timestamptz | NO |
| shadow_signal_id | bigint | NO |
| shadow_policy_version | text | NO |
| signal_ts | timestamptz | NO |
| symbol | text | NO |
| baseline_action | text | YES |
| baseline_trade_allowed | boolean | YES |
| baseline_direction_bias | text | YES |
| baseline_entry_quality | text | YES |
| baseline_confidence_score | numeric | YES |
| shadow_action | text | NO |
| shadow_trade_allowed | boolean | NO |
| shadow_direction_bias | text | YES |
| shadow_entry_quality | text | YES |
| shadow_confidence_score | numeric | YES |
| shadow_delta_confidence | numeric | YES |
| shadow_decision_changed | boolean | YES |
| breadth_wcb_relationship | text | YES |
| wcb_regime | text | YES |
| wcb_score | numeric | YES |
| wcb_alignment | text | YES |
| wcb_weight_coverage_pct | numeric | YES |
| entry_spot | numeric | YES |
| entry_reference_price | numeric | YES |
| outcome_15m_spot | numeric | YES |
| outcome_30m_spot | numeric | YES |
| outcome_60m_spot | numeric | YES |
| outcome_eod_spot | numeric | YES |
| move_15m_points | numeric | YES |
| move_30m_points | numeric | YES |
| move_60m_points | numeric | YES |

---

## Notes

- `shadow_signal_snapshots` (without v3 suffix) is the legacy table — superseded by `shadow_signal_snapshots_v3`
- `shadow_reconstruction_v3` is the current active reconstruction tool — v1 and v2 are superseded
- `shadow_outcomes_v2` is the current active outcome table — v1 is superseded
- `shadow_signal_validation_v1`, `shadow_state_signal_outcomes`, `shadow_state_signal_snapshots`, `shadow_vs_live_evaluation` — DDLs not yet captured (returned no rows in information_schema query — likely empty tables or views). Capture on next session.

---

## Shadow Gate Status — 2026-04-04

| Session | Rows | Valid |
|---|---|---|
| 2026-04-02 | 243 | ✅ |
| 2026-04-01 | 214 | ✅ |
| 2026-03-25 | 299 | ✅ |
| 2026-03-23 | 236 | ✅ |
| 2026-03-27 | 5 | ❌ partial |
| 2026-03-24 | 34 | ❌ partial |
| 2026-03-21 | 2 | ❌ partial |
| 2026-03-20 | 7 | ❌ partial |

**Valid full sessions: 4 of 10 required. Gate opens after ~6 more clean sessions (~2 weeks).**
