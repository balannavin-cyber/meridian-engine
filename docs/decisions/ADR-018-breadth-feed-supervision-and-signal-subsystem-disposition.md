# ADR-018: Breadth-Feed Supervision Model & Signal-Subsystem Disposition

## Status

ACCEPTED — 2026-06-19 (Session 57)

Supersedes the implicit "breadth feed runs unsupervised in a `screen` session" arrangement that has been live since the AWS migration (S49). Cross-references ADR-006 (AWS migration scope: capture → AWS canonical, derived/signal → Local canonical with AWS shadow) and ENH-30 (the SMDM thesis this ADR retires).

## Context

Two findings in the S57 session forced a deployment-topology decision, which per Doc Protocol v4 Rule 10 mandates an ADR.

### Finding 1 — the breadth chain died silently and was running on the wrong host, unsupervised

The breadth chain is:

```
Zerodha  →  ws_feed_zerodha.py  →  market_ticks  →  ingest_breadth_from_ticks.py (AWS)
         →  breadth_intraday_history  →  market_breadth_intraday  →  weighted_constituent_breadth_snapshots (WCB)
```

S48–S56 documented this feed as running on **MALPHA** (`ubuntu@13.51.242.119`), the designated Zerodha Kite gateway. S56 (TD-S48-NEW-1) re-diagnosed the stall to a missing MALPHA feed but flagged a contradiction it could not reconcile: `market_ticks` empty from 06-09 yet breadth wrote non-zero coverage through 06-11.

S57 resolved the contradiction. `ws_feed_zerodha.py` was **not** absent — it was running on **AWS** (not MALPHA as documented), inside a detached `screen` session, since 2026-06-11. It was holding an **expired Zerodha token** and silently **403-looping** on every reconnect, writing zero-coverage rows into `breadth_intraday_history` while `market_breadth_intraday` and `weighted_constituent_breadth_snapshots` stayed dead. Nothing supervised the process; nothing alarmed on the 403 loop; the WCB consumer logged `SKIPPED_NO_INPUT` into the void.

In-session remediation (verified): Zerodha token refreshed on MALPHA → `kite.profile()` returned `OK: Navin Balan OV0782` → stale AWS process (PID 259620) `kill -9` → feed restarted clean ("Connected. Subscribing 2213 instruments… Feed live", zero 403s). This restored the live feed but did **not** address the structural defects that produced the 23-day silent outage: wrong host, no supervision, no reader-side staleness detection.

This is the third instance of the same class. S29 filed TD-NEW-K (silent exit on max-reconnect exhaustion), TD-NEW-L (no process supervision — no systemd/pm2 equivalent for `ws_feed` or `ingest_breadth`), and TD-NEW-M (no single-instance enforcement → duplicate PIDs when cron fires against a live manual process). The S57 incident is exactly the failure mode TD-NEW-L predicted.

### Finding 2 — the signal subsystem was orphaned by the S49 Local-disable

S49 intentionally disabled the Local Windows capture/compute layer and migrated capture + core compute to AWS. The migration scope (ADR-006) covered capture and core compute. It did **not** include the signal subsystem: `compute_smdm_local.py` (`smdm_snapshots`), `options_flow_snapshots`, `iv_context_snapshots`, and the shadow-v3 signal path. When Local was disabled, these four died with it and were never picked up on AWS — hence their stop dates (smdm/options_flow ~06-02, iv_context ~06-08) and their absence from AWS cron. They are **orphaned by partial migration**, not accidentally broken.

This forced a disposition decision on SMDM specifically. SMDM (`compute_smdm_local.py`, the Structural Manipulation Detection Module, per ENH-30) computes three theses: (A) manipulation-footprint, (B) a gamma-squeeze scalar, (C) flow-velocity, surfaced as STOP_HUNT / SQUEEZE narrative flags. Quant review against the evidence: Exp 9 returned a NEUTRAL verdict on SMDM edge; Thesis B duplicates what the gamma engine already computes better; the STOP_HUNT/SQUEEZE flags are narrative, not measurable. Theses A (manipulation-footprint, redefined) and C (flow-velocity) are the one defensible idea — they map to the SEBI-documented settlement-marking footprint and are computable from data already captured.

## Decision

### D1 — Breadth feed runs under `systemd` supervision on MALPHA (canonical host)

`ws_feed_zerodha.py` is re-homed to its documented canonical host **MALPHA** and supervised by a **`systemd` unit** (not `screen`, not bare `nohup`). The unit provides: `Restart=on-failure`, single-instance enforcement (closes TD-NEW-M), and journald capture of the 403/reconnect output that was previously discarded. The WCB cron argument defect is fixed in the same pass.

**Build state (corrected post-S57 against the git log).** The supervision scaffolding was already **built and committed in S56** — commits `afe8112` + `30cca59` + `b627914`: a wsfeed **preflight** (tolerates `.env` special chars — `set -u` dropped around `source`), a wsfeed **alert** script, and **5 `systemd` units under `deploy/systemd/`**, git-tracked for rebuild-safety. What S57 found is that these were **built but not yet enabled on MALPHA** — the feed was still running unsupervised in an AWS `screen` with an expired token. D1's remaining work is therefore **enable/cut over the existing S56 units onto MALPHA + verify** (single-instance, journald, `Restart=on-failure`, WCB cron arg), **not** build-from-scratch. The host decision (MALPHA, one host owns the Zerodha session) stands.

Rationale for MALPHA over AWS: MALPHA is the designated Zerodha gateway (Kite session lives there; token refresh happens there); running the feed on AWS while the token refreshes on MALPHA is precisely the split-brain that produced the 23-day expired-token loop. One host owns the Zerodha session end-to-end.

### D2 — Every reader of breadth (and divergence) snapshots applies a recency-floor guard

The `fetch_latest_row` no-recency-floor defect is the reason a 23-day-old dead feed read as "working." Any consumer of `market_breadth_intraday`, `weighted_constituent_breadth_snapshots`, or the new `structural_divergence_snapshots` (D4) **must** apply a recency floor on `fetch_latest_row` so that a silent upstream stop self-flags as STALE rather than serving the last good row indefinitely. This is **mandatory, not optional**, and is a hard precondition for D4 shipping.

### D3 — SMDM is retired as built (evidence-based retirement against ENH-30)

`compute_smdm_local.py` and `smdm_snapshots` are **RETIRED**, documented as an evidence-based retirement against ENH-30 (Exp 9 NEUTRAL verdict + redundant gamma-squeeze scalar — not an accidental orphan-drop). Specifically:

- STOP_HUNT / SQUEEZE pattern flags → **DROP** (narrative, not measurable).
- Gamma-squeeze scalar (Thesis B) → **DROP** (the gamma engine does this better).
- Manipulation-footprint (Thesis A, redefined) + flow-velocity (Thesis C) → **CARRY** into the new monitor (D4).

### D4 — SMDM's defensible idea is rebuilt as ENH-SDM, an AWS/orchestrator-integrated structural-divergence monitor

`compute_structural_divergence_local.py` → `structural_divergence_snapshots`, computing four primitives (breadth-divergence; OI-displacement vs drift; straddle velocity; settlement-window VWAP pressure), a phase classifier, and direction. Two operator-selectable modes: offensive (fade the engineered settlement reversal aligned with the smart-money options book) and defensive (stand aside).

Per ADR-006, this is **derived/signal layer**. Because Local is intentionally disabled and ENH-SDM is a **kept** subsystem (not an orphan), it lands on **AWS, orchestrator-integrated** — the same path core compute took — **not** re-enabled on Local. This is the deliberate inversion of the retired SMDM's placement: SMDM was a Local orphan; ENH-SDM is an AWS first-class subsystem. Edge must be proven out-of-sample, net of costs, on post-ban data, before any capital is routed (ADR-009 holdout discipline applies). ENH-SDM depends on the restored breadth chain (D1) and the freshness guard (D2).

## Alternatives considered

- **Keep the feed in `screen` and add a watchdog cron.** Rejected: a cron watchdog shares the same failure surface (it would also need the Zerodha session and could die with it — the S53 "watchdog and patient dying together" lesson). `systemd` supervision is host-native and does not share the application's failure chain.
- **Re-home the feed to AWS under systemd.** Rejected: keeps the Zerodha session split across two hosts (token on MALPHA, feed on AWS), which is the root of the expired-token loop. One host owns the session.
- **Port SMDM to AWS as-is.** Rejected: Exp 9 NEUTRAL — porting an unvalidated orphan spends migration effort on a subsystem with no demonstrated edge. Retire the build, keep only the defensible primitive.
- **Deprecate-and-document SMDM with no replacement.** Rejected on the manipulation-footprint primitive only — Thesis A maps to a real, SEBI-documented, capturable footprint; dropping it entirely discards the one measurable idea.

## Consequences

- A 23-day-class silent breadth outage becomes self-flagging: `systemd` restarts + journald captures the failure, and the recency-floor guard surfaces STALE to any reader within one cycle.
- TD-NEW-L (no supervision) and TD-NEW-M (no single-instance enforcement) are closeable once the S56-built `systemd` units are **enabled on MALPHA** (the units already exist in `deploy/systemd/`; the gap is cutover, not authoring). TD-NEW-K (silent reconnect-exhaustion exit) is mitigated by `Restart=on-failure`.
- The signal-subsystem orphan question is half-resolved: SMDM is decided (retire→rebuild). `options_flow_snapshots`, `iv_context_snapshots`, and shadow-v3 remain open dispositions (port-to-AWS vs deprecate-and-document) and carry forward.
- ENH-SDM cannot ship until D1 + D2 are live; it is gated, not immediate.

## Governance

Breadth and any breadth-dependent signal feed run under host-native process supervision (`systemd`) on the single host that owns their broker session; unsupervised `screen`/`nohup` deployment of a long-running feed is prohibited going forward. Every reader of a freshness-sensitive snapshot table applies a recency floor so an upstream stop self-flags. Orphaned signal subsystems are dispositioned explicitly — retire-with-evidence or port-to-AWS — never left silently dead. Retirement of a subsystem with a validation history (e.g. ENH-30/SMDM) is recorded as evidence-based retirement, citing the experiment verdict, not as an undocumented drop.

## S58 Corrections (2026-06-22) — applied after live verification + unit-file read

These correct two errors in the original D1/D4 text above. The original text is **preserved unchanged** for the record; this section is authoritative where they conflict.

**D1 host — MALPHA → MERDIAN AWS (corrected).** D1 said re-home the feed to MALPHA. The S56 `systemd` unit files (read at S58) declare `User=ssm-user`, `WorkingDirectory=/home/ssm-user/meridian-engine`, `ExecStart=/usr/bin/python3 /home/ssm-user/meridian-engine/ws_feed_zerodha.py`, `EnvironmentFile=/home/ssm-user/meridian-engine/.env` — i.e. they supervise the feed on **MERDIAN AWS**, where the repo, the units, and the running feed all are. MALPHA hosts no Meridian code (it is the token gateway only, per the Deployment Topology). D1's "MALPHA" was an over-rotation on a memory note. **Corrected: feed supervised on MERDIAN AWS; MALPHA stays the Zerodha token source feeding the AWS `.env`.** Verified live on the 2026-06-22 open (timer 03:40 UTC, single PID, preflight OK, 2213 instruments, zero 403s). D2 recency-floor also verified live (closes TD-081). Both close TD-S57-NEW-1 / TD-S57-NEW-2 on verification.

**D4 primitives — breadth/OI/VWAP → gamma-centric (corrected) + observability-first reframe.** D4 listed ENH-SDM's primitives as breadth-divergence / OI-displacement / straddle / settlement-window VWAP. That list matches neither the validated case nor the retired SMDM code. The signal with a documented edge is **CASE-2026-06-02** (+71% short-covering trade), whose four measured conditions are all gamma-centric and all from `gamma_metrics`: **pin-risk rate, straddle-collapse velocity, gamma-concentration, net_gex/regime-flip**, with a three-red-wick spot reversal trigger. **Corrected: ENH-SDM primitives are the gamma-centric set, sourced to CASE-2026-06-02.** breadth/OI/VWAP are deferred as candidate secondary primitives. Reviewing the retired `compute_smdm_local.py` confirmed D3 was right to drop the narrative scoring (SQUEEZE/STOP_HUNT/GAMMA_PINNING); only `compute_straddle_velocity` is salvageable; `otm_oi_velocity` was never built. **Reframe (per ADR-009 + S37):** a single case justifies *measuring* these conditions, not *acting* on them. ENH-SDM ships **observability-first (display-not-gate)**; the backward frequency study to size a cohort is blocked (purchased chain has 0% Greeks — TD-S58-NEW-1, N~8), so the cohort accrues forward and signal/modes are gated on N. P1 schema (`structural_divergence_snapshots` + `_replay`) deployed S58.

See also ADR-019 (signal-orphan port-not-retire), which refines this ADR's disposition governance: retire only on evidence a capability has no value, never on an experiment verdict.

