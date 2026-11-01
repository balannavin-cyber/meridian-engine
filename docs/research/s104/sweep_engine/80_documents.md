# 80_documents — documents that state the Γ unit or a Γ magnitude (prompt §3 item 8: LIST ONLY)

Listed, not assessed. 5,575 of the 15,218 `10_hits.tsv` rows are `kind = doc`.
Phase-1 blind files are named in `00_census.txt` §6 and were **not** read.

## Governance / contract documents
| file | Γ-token lines | what it states |
|---|---|---|
| `CLAUDE.md` | (read at session start) | the ADR-032 D1 settled line; rules 0, 14, 20; the S28 `net_gex` "Crore range" line |
| `.claude/rules/data-access.md` | — | S62 `hist_gamma_metrics` raw-scale note; `gamma_concentration` scale-invariance |
| `.claude/rules/python-writers.md` | — | writer/patch discipline; no unit statement |
| `.claude/rules/sql-views.md` | not opened this session | path-scoped, loads on an `sql/` read |
| `docs/interfaces/retail_compute_contract.md` | — | §8 per-view table (cited by CLAUDE.md rule 25) |

## Registers
| file | Γ-token lines |
|---|---|
| `docs/registers/merdian_reference.json` | 170 |
| `docs/registers/tech_debt_history.md` | 144 |
| `docs/registers/CURRENT_history.md` | 133 — incl. `POST_S36_GAMMA_METRICS_UNIT = Cr_global` at `:974` |
| `docs/registers/MERDIAN_Enhancement_Register.md` | 117 |
| `docs/registers/MERDIAN_System_Map.md` | 100 |
| `docs/registers/tech_debt.md` | 87 |
| `docs/registers/MERDIAN_Assumption_Register.md` | 64 |
| `docs/registers/MERDIAN_Data_Inventory.md` | 42 |
| `docs/registers/CLAUDE_history.md`, `session_log_history.md`, `MERDIAN_Deployment_Topology.md`, `agentic_layer_roadmap_S90.md` | present, not counted individually |

## ADRs that define or constrain the Γ unit or its magnitude
| file | Γ-token lines | relevance |
|---|---|---|
| `docs/decisions/ADR-002-market-structure-philosophy.md` | 45 | proposes `local_gex_cluster_cr`, `total_gex_cr`, `gex_velocity`, `max_gamma_strike_delta` as `gamma_metrics` columns (`:261-262`); `local_gex_cluster_cr / total_gex_cr` ratio at `:355` |
| `docs/decisions/ADR-014-per-strike-gex-schema.md` | 42 | §2.3 the `gex_cr` sign convention; §2.5 the `sum == net_gex` invariant; `:179` rejects a stored `gex_per_oi` |
| `docs/decisions/ADR-015-per-strike-gex-schema-v2.md` | — | `:93` positioning-γ vs dealer-γ; `dealer_gex_cr_est` rejected |
| `docs/decisions/ADR-024-gex-zone-anchor.md` | 49 | zone anchoring |
| `docs/decisions/ADR-023-read-path-recency-floors.md` | — | `MERDIAN_GEX_RECENCY_FLOOR_MIN` (15 → amended 120) |
| `docs/decisions/ADR-032-gex-stored-unit.md` | — | **PHASE-1 BLIND, NOT READ** |
| `docs/decisions/MERDIAN_Decision_Index.md` | — | index row per ADR |

## Research documents stating a Γ magnitude or unit
`docs/research/parity_render_contract.md` (104) · `docs/research/data_inventory_2026-09-08.md` (51) ·
`docs/research/s72_gex_view_fix.sql` (48) · `docs/research/adr009_prereg_gex_zone_utility_2026-09-07.md` (43) ·
`docs/research/s100/r10/r10_curve_points.sql` (`:175` `total_gex → curve_gex_cr`) ·
`docs/research/s95_priority/sstar/sstar_gates.py` + `sstar_view_body.sql` ·
`docs/research/s96_priority/p3b/*` (the `abs(top1-conc) > 1e-6` invariant) ·
`docs/research/s96_priority/p7/p7a|p7b/*_body_cost.sql` · `docs/research/s92_parity/r24/*.json` (inventory/fixture/asof) ·
`docs/research/s93_priority/p6/P6_dex_design_note.md` · `docs/research/ict_structure_audit_2026-09-09.md` ·
`docs/research/s102/*` — **PHASE-1 BLIND, NOT READ**.

## Manuals / consumer-facing prose
`docs/marketview_manual/` (v0.5 per CLAUDE.md) · `docs/lovable_prompts/s102/*` — **BLIND, NOT READ** ·
`docs/lovable_prompts/s97/lovable_prompt_s97_dealer_wording.md`.

## Generated `.docx` masters — scanned, never opened as working documents
36 tracked `.docx`, text-extracted; 10 Γ-token hits total across all of them
(`GammaEngine_Master_V14/V15/V15_1`, `GammaEngine_SMDM_SupplementSpec_V7`, `MERDIAN_Master_V18*`).
CLAUDE.md names reading these at session start as an anti-pattern; they were scanned for tokens
only, to make the "every tracked file was walked" claim true, and nothing was read from them.
