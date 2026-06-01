# ENH-113 — Capture/Derived Split Execution - Phase 2 (Local → AWS Migration)

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Filed | 2026-06-01 (S42) |
| Authority | ADR-006 (AWS migration scope: capture/derived split with four-stage decomposition) |
| Phase | Phase 2 (post-token-refresh, S42+) |
| Priority | **P0 — blocking ADR-006 execution** |
| Related | ADR-006, TD-S41-NEW-2, ENH-72 (ExecutionLog contract) |

---

## Objective

Execute ADR-006 **Phase 2: Local writer disposal**. Migrate all Local capture-stage writers to AWS, eliminating laptop-dependency for market data ingest.

**Target writers (currently Local + AWS dual-write):**
1. `ingest_market_spot_snapshots.py` (post-market 16:00 IST)
2. `ingest_option_chain_snapshots.py` (intraday 5-min cycle)
3. `capture_india_vix.py` (intraday)
4. `ingest_breadth_intraday_local.py` (intraday)
5. `build_ict_htf_zones.py` (intraday rebuild)

**Success criteria:**
- All five writers run on AWS only (Local tasks disabled)
- Zero gap in `market_spot_snapshots`, `option_chain_snapshots` post-cutover
- All writers report SUCCESS in `script_execution_log`
- No Mode B 401 token errors
- Operator can manually run Local fallback if AWS writer fails

---

## Scope

**Phase 2.a — Pre-migration validation (S42):**
- Audit current Local task implementations
- Identify AWS-incompatible code paths (e.g., file system access, hardcoded paths)
- Plan environment variable / credential management for AWS

**Phase 2.b — AWS deployment (S42–S43):**
- Copy scripts to AWS `/home/ssm-user/meridian-engine/`
- Create AWS cron dispatcher for each writer at current Local schedule
- Verify cron entries fire successfully (manual test)

**Phase 2.c — Parallel testing (S43, 5 trading days):**
- Both Local and AWS writers fire simultaneously
- Monitor for collisions, token failures, data gaps
- Pass criteria: zero gaps, zero 401 errors, all writes succeed

**Phase 2.d — Cutover (S43–S44):**
- Disable all Local capture tasks (keep Local as manual fallback)
- Verify AWS continues alone for 1 trading day
- Commit: "ENH-113 Phase 2 CUTOVER: capture writers moved to AWS (ADR-006 Phase 2 complete)"

**Phase 2.e — Derived-layer confirmation (S44):**
- Verify all downstream consumers (gamma_metrics, volatility, etc.) process AWS capture data correctly
- No regression in derived signal quality

---

## Deliverables

1. **Phase 2 Runbook** (`docs/runbooks/runbook_enh113_phase2_capture_migration.md`)
   - Writer-by-writer migration steps
   - Cron entry templates
   - Rollback procedures
   - Monitoring checklists

2. **Audit Report** (documentation in CURRENT.md)
   - AWS-incompatible code paths flagged
   - Credential management plan documented
   - Risk assessment per writer

3. **Cron Config** (staged in `/home/ssm-user/meridian-engine/.cron_config`)
   - All five writers' cron entries
   - Schedule alignment with current Local Task Scheduler

---

## Timeline

| Sub-phase | Effort | Duration |
|---|---|---|
| **2.a** Pre-migration audit | 1–2 hrs | S42 |
| **2.b** AWS deployment | 1–2 hrs | S42–S43 |
| **2.c** Parallel testing | Observation | 5 trading days (S43) |
| **2.d** Cutover | 30 min | S43–S44 |
| **2.e** Derived validation | 1 hr | S44 |

**Critical path:** ~6–7 days (1 day audit/deploy + 5 trading day test)

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| AWS writer fails, data gap | 5-day parallel test detects gaps before cutover |
| Token staleness on AWS pull | TD-S41-NEW-2 staleness check fails loudly + Health Dashboard alert |
| Local writer still needed | Local tasks remain as manual fallback; operator can run `python ingest_*.py` if AWS fails |
| Credential exposure on AWS | Plan: move to Secrets Manager (deferred to Phase 3) |

---

## Success Metrics

- ✅ Zero data gaps in any capture table post-cutover
- ✅ All five writers report SUCCESS daily for 5 trading days during parallel phase
- ✅ Token age < 1h at each pull time (03:05 UTC)
- ✅ Derived consumers (gamma_metrics, volatility) process capture data without regression
- ✅ Operator confidence: can manually refresh Local writer if AWS fails

---

## Notes

**Why Phase 2 after token refresh (Phase 1.c)?**
Token refresh is the foundational move (removes laptop dependency for credentials). Once token refresh is AWS-canonical + verified, moving other capture writers becomes straightforward (no special credential handling per writer needed).

**Why 5-day parallel test?**
Market data ingest is the bedrock of all downstream signal computation. Five clean trading days eliminates holiday edge cases (weekends, Indian holidays) and proves reliability across normal market conditions.

**Relationship to ADR-006:**
ADR-006 Phases 1–2 move the **Capture** stage to AWS. Phases 3–4 address shadow validation + operator tooling (separate, lower urgency).

---

*ENH-113 filed 2026-06-01 (S42 Phase 1.c). Proposed for immediate action (S42–S44 timeline).*
