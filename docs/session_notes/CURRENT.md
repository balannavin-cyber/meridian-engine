# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-04-25 (Saturday — Session 8) |
| **Concern** | Candidate B from Session 7's CURRENT.md — Experiment 17 backtest (BULL Zone Break-Below as Rejection Cascade). Plus filing TD-015..018 from 2026-04-24 backlog at session start. |
| **Type** | Research / experiment + register maintenance. |
| **Outcome** | DONE — Exp 17 ran to FAIL verdict with composition diagnostic. Two new TDs surfaced (TD-019 stale spot pipeline, TD-020 LONG_GAMMA-on-directional-day diagnosis required before ADR-002). Session 9 priority reshuffled. |
| **Git start → end** | `9e94824` → `b317458c5058222b9c88e285eb9639c4ad00aec3` |
| **Local + AWS hash match** | Local advancing; AWS still at `2c130bb` (no AWS-side commits — research session, no operational code changes). |
| **Files changed (code)** | `experiment_17_bull_zone_break_cascade.py` (new, ~280 lines) |
| **Files modified (docs)** | `tech_debt.md` (TD-015..020 filed), `CURRENT.md` (this rewrite), `MERDIAN_Experiment_Compendium_v1.md` (Exp 17 verdict block), `merdian_reference.json` (v10→v11), `session_log.md` (one-liner), `CLAUDE.md` (python path fix) |
| **Files added (tracked)** | `experiment_17_bull_zone_break_cascade.py` |
| **Files added (untracked, gitignored)** | `experiment_17_events.csv`, `experiment_17_baseline_buckets.csv` |
| **Tables changed** | None |
| **Cron added/changed** | None |
| **`docs_updated`** | YES |

### What today did, in 6 bullets

- **TD-015..018 filed at session open.** Spec from Session 7's CURRENT.md applied verbatim into `tech_debt.md` (preflight runbook gap, Dhan TOTP scheduled-vs-manual asymmetry, missing 1H ICT zone post-market cron, datetime.utcnow deprecation). Now properly tracked.
- **Experiment 17 ran end-to-end. FAIL on all four Pass criteria.** N=13 (target ≥30; underpowered). Mean T+EOD return on events +0.158% vs baseline -0.014% — direction OPPOSITE to hypothesis. Composition diagnostic shows 54% of events are 09:15 gap-down opens (Exp 21 territory), 31% are late-day breaks (degenerate T+EOD horizon), 31% have same-day zone creation. Only 2 of 13 events are clean intraday rejections; N=2 distinguishes nothing.
- **Look-ahead audit revealed all 13 zones retrospectively created.** 11 of 13 in single batch 2026-04-15 10:04 IST; 2 of 13 at 2026-04-11 19:19 IST. Live ICT zone tracking effectively did not exist in production before 2026-04-15. Exp 17 remains valid as a structural backtest because zones are geometrically deterministic from completed weekly candles, but no event in the sample was live-detectable. The 2026-04-24 cascade is plausibly MERDIAN's first-ever "live zone, live break-below" instance.
- **Stale spot bar pipeline discovered.** `hist_spot_bars_5m` last bar 2026-04-15 09:55 IST. 10-day gap, including the 2026-04-24 cascade event. Compounded by ~2.5 hour laptop-shutdown hole on 2026-04-24 11:30-14:00 IST. Filed as TD-019 (S2). Fix sequence: diagnose broken component first, repair, then Kite REST backfill via the repaired pipeline path.
- **LONG_GAMMA-on-directional-day concern surfaced.** Charts confirm 2026-04-24 was the strongest bearish intraday day of the recent month (NIFTY -1.6%, SENSEX -1.4%). CURRENT.md from Session 7 records BULL_FVG signals blocked by LONG_GAMMA gate. Whether BEAR signals were generated AND blocked is unknown; that question materially affects ADR-002's framing. Filed as TD-020 (S2). ADR-002 drafting paused until TD-020 resolves.
- **CLAUDE.md python path correction.** "Quick environment reference" listed Local Python as `Python312\python.exe` which doesn't exist on Navin's box. Bare `python` works. One-line fix in CLAUDE.md env table.

---

## This session

> Session 9. Pick ONE primary path from below at session start.

### Candidate A (recommended) -- TD-022 ICT detector silence diagnosis

| Field | Value |
|---|---|
| **Goal** | Diagnose why ICT pattern detector produced zero setups on 2026-04-24 despite the chart-visible W BULL_FVG break and -393pt cascade. Three sub-hypotheses to discriminate: (1) lookback/window mismatch -- detector requires status='ACTIVE' but the zone became BREACHED early in the day; (2) detector silently failing on TD-019 stale 5m bar feed; (3) pattern-coverage gap -- the cascade structure is not a pattern type the detector knows about. Code-reading + targeted replay. |
| **Type** | Code review + data replay. Read-only relative to production tables. |
| **Success criterion** | TD-022 marked diagnosed (one of 1/2/3 supported with evidence); ADR-002 disposition stated based on whether the silence is a bug or expected behaviour; if a code fix is required, scoped to a Session 10 successor ENH. |
| **Time budget** | ~25-40 exchanges. |

### Candidate B — TD-019 Step 1: diagnose stale spot pipeline (do not backfill yet)

| Field | Value |
|---|---|
| **Goal** | Step 1 of TD-019's three-step fix: identify which component broke and when. Check `MERDIAN_Spot_1M` Task Scheduler history, `script_execution_log` for last SUCCESS rows on `capture_spot_1m.py` and `build_spot_bars_mtf.py`, recent log files. Do NOT attempt repair or backfill in this session — that's Session 10/11. |
| **Type** | Diagnostic. No code change. |
| **Success criterion** | TD-019 updated with root cause; repair plan written; backfill SQL/script outline drafted (not run). |
| **Time budget** | ~15-25 exchanges. |

### Candidate C — Original Candidate A from Session 7's CURRENT.md (ADR-002 phase-4a-posture)

| Field | Value |
|---|---|
| **Goal** | Originally recommended for Session 8 but deferred. Now BLOCKED on TD-020 — ADR-002 cannot ratify until LONG_GAMMA gate behaviour on 2026-04-24 is understood. Do NOT pick this candidate before TD-020 is resolved. Listed here as a placeholder to make the dependency explicit. |
| **Type** | Governance documentation. |
| **Success criterion** | Blocked. |
| **Time budget** | N/A this session. |

### Candidate D — Kite token propagation automation (C-10) — deferred

| Field | Value |
|---|---|
| **Goal** | Originally Candidate C from Session 7's CURRENT.md. Still valid work but lower priority than TD-020. Deferred to Session 10+. |
| **Type** | Operational automation. |
| **Time budget** | N/A this session. |

### DO_NOT_REOPEN

- All items from Session 7's CURRENT.md DO_NOT_REOPEN list (capital ceiling, strategy choice, T+30m exit, 5m vs 1m for ICT, OI-* namespace, ENH-72, V19A/B/C as per-session, em-dashes in commits, PS 5.1 Get-Content, `python -c` for multi-line replace in PS, breadth cascade root cause, contamination registry approach, 1H ICT pre-market silence, Kite "AUTH FAILED then AUTH OK")
- **NEW: Experiment 17 hypothesis as written** — closed FAIL 2026-04-25. Structural backtest is valid; data does not support bearish cascade. Do not re-litigate the question. Exp 17b is a different experiment (composition-cleaned + D-zone universe), not a re-run.
- **NEW: 02-06-2025 events as outliers** — they are NOT outliers. They are the cleanest tests in the Exp 17 sample and they reject the hypothesis with conviction. Do not strip them in any future analysis.
- **NEW: ADR-002 unconditional ratification** — pending TD-020 disposition. If TD-020 lands as sub-hypothesis (c), ADR-002 ratifies as drafted. If (a) or (b), ADR-002 needs language acknowledging the gate's behaviour on directional days and the local-vs-net concern.

- **NEW: TD-020 LONG_GAMMA gate question** -- closed 2026-04-25 in Session 8 extended diagnosis. Gate was not the cause of trade absence on 2026-04-24; ICT detector produced zero signals all day. Do not re-open the gate-blocking framing -- the real question is now TD-022.
- **NEW: ADR-002 ratification dependency** -- now BLOCKED on TD-022, not TD-020. If TD-022 finds the silence is intentional, ADR-002 ratifies with that framing. If TD-022 finds a detector bug or a TD-019 dependency, ADR-002 waits for the fix.

### Watch-outs for Candidate A (TD-022 diagnosis)

- The diagnosis is read-only. Resist any urge to also fix what gets diagnosed in the same session — split into Session 10 successor.
- 2026-04-24 spot 5m bars are missing (TD-019); use options snapshots and tick data instead. Sufficient for GEX time series and signal-generation introspection.
- ADR-002 is in-flight; do not draft its content this session — only state which way TD-020 unblocks it.

### Watch-outs for Candidate B (TD-019 diagnosis)

- Step 1 only. Do not repair, do not backfill. Backfill before diagnosis = repeat-failure risk.
- `script_execution_log` is the cleanest single source for finding the last SUCCESS row of each producer.

---

## New TDs to file at Session 9 start

None. TD-019 and TD-020 already filed in Session 8 close batch.

---

## Live state snapshot (at Session 9 start)

| Component | State |
|---|---|
| **Live trading** | Phase 4A — manual execution. 2026-04-24 was the strongest bearish day of the recent month; LONG_GAMMA gate blocked all BULL_FVG TIER2 signals. Whether BEAR signals were also generated/blocked is the TD-020 question. |
| **Shadow gate** | All 10 sessions PASSED (closed 2026-04-15) — corrupted breadth caveat. ADR-002 BLOCKED on TD-020 disposition. |
| **Breadth pipeline** | FIXED and verified in production 2026-04-24 09:31 IST. Independent of TD-019 spot pipeline staleness. |
| **Spot bar pipeline (`hist_spot_bars_5m`)** | STALE since 2026-04-15. 10-day gap. TD-019 OPEN. |
| **Local env** | Windows Task Scheduler. PS 5.1 with UTF-8 profile. Git CRLF auto-conversion (cosmetic). |
| **AWS env** | MERDIAN AWS `i-0878c118835386ec2` (eu-north-1). 11 cron jobs total. Shadow runner FAILED since 2026-04-15 (pre-existing). |
| **MeridianAlpha AWS** | `13.51.242.119`. C-10 OPEN. |
| **Local git HEAD** | `b317458c5058222b9c88e285eb9639c4ad00aec3` (in sync with origin/main) |
| **Last canary tag** | none — no live canary in Session 8 |
| **Open C-N (critical)** | C-10 HIGH OPEN (Kite token propagation manual) |
| **Open TD S1** | none |
| **Open TD S2** | TD-002 (breadth_regime backfill), TD-019 (spot pipeline stale), TD-022 (ICT detector silent on cascade days) |
| **Open TD S3** | TD-001, TD-004, TD-005, TD-006, TD-007, TD-015, TD-016, TD-017 |
| **Open TD S4** | TD-009, TD-010, TD-018, TD-021 |
| **Closed in Session 7** | C-09, TD-014 |
| **Closed in Session 8** | TD-020 (LONG_GAMMA gate question diagnosed -- not the cause; gate had no signals to filter; replaced by TD-022) |
| **Open from Session 7** | ADR-002 phase-4a-posture (NOW BLOCKED on TD-022) |
| **Active research backlog** | Exp 17 closed FAIL. Exp 17b proposed (composition-cleaned). Exp 18-23 in Compendium backlog. |
| **Active ENH in flight** | none |
| **Data contamination** | `BREADTH-STALE-REF-2026-03-27` registered. 27-day window 2026-03-27 → 2026-04-23. |

---

## Mid-session checkpoints

> Per Session Management Rule 1: every ~20 exchanges, write 5 bullets here. Do not wait until session end.

### Checkpoint 1 (~20 exchanges)
- Fixed:
- Confirmed:
- Open:
- Changed:
- Next:

### Checkpoint 2 (~40 exchanges)
- Fixed:
- Confirmed:
- Open:
- Changed:
- Next:

---

## Session-end checklist (before commit)

```
[ ] CURRENT.md updated — "Last session" reflects THIS session, "This session" reset for next
[ ] session_log.md appended (one line)
[ ] merdian_reference.json updated for any file/table/item status change
[ ] tech_debt.md updated if any TD added, mitigated, or closed
[ ] Enhancement Register updated if architectural thinking happened
[ ] Local + AWS hash match confirmed if code changed
[ ] All commits prefixed: MERDIAN: [ENV|DATA|SIGNAL|OPS|RESEARCH] <scope> -- <intent>
[ ] Re-upload to project knowledge any of CURRENT.md / session_log.md / merdian_reference.json / tech_debt.md / Enhancement_Register / CLAUDE.md / docs/operational/* that changed (Rule 12)
[ ] Phase boundary check: any Master/Appendix .docx generation triggered? (rare)
[ ] Runbook review: any operation explained for 2nd time? Create runbook from RUNBOOK_TEMPLATE.md
[ ] data_contamination_ranges review: new contamination this session? INSERT row (Rule 13)
```

---

## TD-022 starter approach (Candidate A first step)

```sql
-- 1. Net GEX time series for 2026-04-24, both indices
SELECT
    (ts AT TIME ZONE 'Asia/Kolkata')::timestamp AS ts_ist,
    symbol,
    net_gex,
    gamma_regime,
    source_ts
FROM public.options_flow_snapshots
WHERE ts >= '2026-04-24 09:00:00+05:30'
  AND ts < '2026-04-24 16:00:00+05:30'
ORDER BY symbol, ts;

-- 2. All signals generated 2026-04-24, every direction and tier
SELECT
    (created_at AT TIME ZONE 'Asia/Kolkata')::timestamp AS created_ist,
    symbol, direction, pattern_type, tier,
    gate_disposition, gate_reason
FROM public.trade_signals  -- adjust table name if different
WHERE created_at >= '2026-04-24 09:00:00+05:30'
  AND created_at < '2026-04-24 16:00:00+05:30'
ORDER BY created_at;

-- 3. Source-ts freshness check on gamma block during 2026-04-24
SELECT
    (ts AT TIME ZONE 'Asia/Kolkata')::timestamp AS ts_ist,
    symbol,
    source_ts,
    EXTRACT(EPOCH FROM (ts - source_ts)) AS staleness_secs
FROM public.options_flow_snapshots
WHERE ts >= '2026-04-24 09:00:00+05:30'
  AND ts < '2026-04-24 16:00:00+05:30'
ORDER BY staleness_secs DESC
LIMIT 10;
```

If sub-hypothesis (a) — local-vs-net divergence — is suspected, the local GEX query is more involved and will be drafted in-session.

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-04-25 (end of Session 8 — Exp 17 FAIL, TD-019 + TD-020 filed, Session 9 priority reshuffled to LONG_GAMMA diagnosis primary).*
