# S89 — operator rulings

Single source for S89 operator rulings, in the shape of `docs/research/s87_routing/rulings_s87.md`.
**A ruling transcribed into a second place is a ruling that can drift out of agreement with
itself**, so nothing here is restated into ADR-029, `CURRENT.md` or the S89 starter — those
point at this file.

---

## ADR-029 #13 — sandbox enable, install cost, network-allowlist scope

**#13 RULED 2026-10-03 (out of hours, as deferred).** Sandbox ENABLE DEFERRED to a focused
pass; not enabled this session. Install cost MEASURED: bubblewrap 0.6.1-1ubuntu0.3 + socat
1.7.4.1-3ubuntu4 — 2 packages, no new transitive deps (libc6/libcap2/libselinux1/libssl3/
libwrap0 already satisfied), ~395 KB download (46,314 + 349,118 B), ~1.48 MB on disk
(129 + 1,349 KB), standard jammy repos, no third-party. Network-allowlist scope RULED:
Supabase + GitHub + package registries only; Dhan / Kite / Breeze / Telegram EXCLUDED by
design — the agent never touches broker/token hosts (Guardrails), so the exclusion is a
boundary, not an omission. When enabled it is via the built-in `/sandbox` (operator-typed),
NOT a hand-written `settings.local.json`, so CA-trust / proxy wiring is not skipped.

## ADR-029 #14 — §7(e) deny-bypass, confirmed on fresh ground

**#14 RULED 2026-10-03.** §7(e) deny-bypass CONFIRMED on fresh ground via canary
(`~/s89_canary/c.txt`, non-secret, `.env`-style denies mirrored). CONTROL bare `cat` → HELD
(hard-denied). `/bin/cat` → deny RULE did not match (no hard block); fell to the default
approval prompt; sentinel printed on approval → DENY-BYPASSED (default-ask held). The hard
block contributed nothing on this form; a session in auto/bypass mode or with an allow rule
on the verb would have read the file unimpeded. FIX = the OS sandbox (#13); verification
DEFERRED with the enable. ENUMERATION: the full multi-spelling sweep was NOT performed — the
catalog could not be produced under this session's safety constraints and no operator-authored
manifest was supplied, so only the one already-documented form was tested. The "enumerate
untested spellings first" clause is discharged FOR THAT ONE FORM ONLY; the broader sweep
remains owed and must come from an operator-authored or reference list. Log:
`~/s89_canary/presandbox_20261003_0120.log` (2,337 B). Settings restored from `.bak_s89`,
sha `c7f99908…`, deny count back to 22.

## TD-S86-NEW-9 — RULED 2026-10-03 (pre-registered before the 2026-10-07 10:15:59 IST arm)

The §2.6 ≥ 3×SE precondition gates the OFFSET / r_eff reading ONLY. The gamma reading (T1's gamma_relerr test) is gated independently by its own precondition — ATM rows ≥ 10 (§2.8) — as §2.10 established by precedent (E1's gamma refusal fired while its offset was a NO-TEST at 0.49×). Reading 2.

Ruled on the design's structure, independent of any arm's outcome: ≥ 3×SE is defined on the offset median and its SE — a dispersion guard on the offset statistic — and does not bear on the gamma relative error, which has its own sample-size guard.

APPLICATION — PROSPECTIVE, from the 2026-10-07 dte-1 arm onward. A4's ratified UNDECIDED (§2.11) STANDS as the historical record and is NOT retroactively flipped: the ambiguity surfaced after A4 was measured, so A4 is not re-scored under a rule adopted later. The 10-07 arm is the first measured under the fixed interpretation.

Effect on 10-07: the arm's gamma counts if ATM rows ≥ 10, regardless of the offset ratio; T1 is decided on gamma_relerr (refuse only if exact/365 ATM and NEAR are both > 0.10).

## D-1 — RULED 2026-10-03 (parity dovetail)

Adopt the §1.2 mapping. Target-read elements enter parity ONLY as (a) definition detail for a layer already among the fourteen (L1/L2/L3–L5/L6/L12/L13 and the L7/L8 scope), binding under ADR-025 D3, or (b) presentation inside the approved board. Everything else — daily close card, realised/implied ratio, "selling blocked" gate, MTF leverage — files to spec §2.5 as a post-parity extension (ADR-025 D5).

## D-2 — RULED 2026-10-03 (design re-approval; A–G approved 2026-10-01)

Adopt now: the ordered read (§1.3 — regime → edges → pin → concentration → flow-vs-book → trigger → clock caveats) for the read slot (design D.4); the ladder's leader-relative bar mode and LONG/SHORT net-Γ tag (A.5); the "put wall ≈ flip" relationship row (no new compute). Adopt in principle but GATED, rendering progressively: the pin-state block (NO PIN/SHIFTING/STABLE/LOCKED, "held for", time boost) — state machine gated on ENH-133 (D-3), σ-distance gated on canonical σ (E-2), time boost gated on D-5 (else a stated D3 deviation). The read stays descriptive, ends in a structure reading, carries no band word without a measured band (D-6 / E-4; ADR-017 P1).

## D-3 — RULED 2026-10-03

Pull ENH-133 (per-cycle aggregates: one row per run/symbol/expiry + pin state, written by the existing compute chain) into parity scope ahead of §H phase 2. ENH-133 and ENH-134 are COMPLEMENTS, not alternatives: ENH-134 (as-of functions) covers the already-stored window, committed with part5_parityC.out as its test; ENH-133 accumulates forward. Obligations: (i) ENH-133's table sits OUTSIDE pg_cron jobid 19's targets with its own stated retention; (ii) a new table owes its own schema ADR before any DDL (TD-S80-NEW-7 precedent) — the ENH-133 schema proposal is the next artefact, not an immediate table. Dual-purpose: the aggregates double as post-parity Q1 replay test data, and Candidate A writes into the same table.

## D-6 — RULED 2026-10-03 (parity dovetail; band policy)

Our measured bands only (ADR-016). The parity target's thresholds NEVER become the band that drives a state word. Until a band is measured on our own data, the value renders as a number alone (gap E-4) and the detail SCALE slot names the calibration gap. The target's thresholds are shown as labelled "reference" ONLY where he published a concrete number (e.g. HHI ≈0.10 / ≈0.25, as a faint reference mark tagged "reference"), and omitted everywhere else. A reference mark never drives a word and is drawn visually distinct from any measured band.

## E-D2 / E-D5 / E-D7 / E-D8 — RULED 2026-10-03 (parity board, phase-1 decisions)

- **E-D2 (canonical max pain, OI tab):** adopt `v_gex_max_pain` on the γ clock (same run as walls and pin); it also feeds the max-pain valley its candidate rows on that clock. NOT the chain-clock `v_max_pain_by_strike` (would mix clocks on the tab). Carried caveat: L19 off-spec (D5), COMMENT not live (E-12) → renders from the `sql/`-file text, flagged.
- **E-D5 (net-long-γ strike, Gamma tab):** MEASURED 2026-10-03 — stored `gamma_metrics.max_gamma_strike` EQUALS the positive-`gex_cr` argmax on both symbols (NIFTY 22700, SENSEX 72000, matches=t). Ruling: use the stored column.
- **E-D7 (ACCEL zone):** retire from Marketview; the gamma terrain shows amplifying pockets directly (E-15).
- **E-D8 (prototype corrections):** max pain drawn in ink (`--rule`, dash-dot), not gold — gold is reserved for selection (one-meaning-per-hue); and the selected-row label switches to `--ink-2` to clear the 4.24:1 contrast failure (WCAG 4.5).

## D-4 / D-5a / D-5b / D-5c — RULED 2026-10-03 (parity dovetail; flow-vs-book, pressure leg, time boost, conviction)

**D-4 — Flow-vs-book folds into ENH-98 (L7/L8) scope.**
The today's-flow-vs-standing-book ΔOI classification (long buildup / short buildup / short covering / long unwinding, from OI change vs price change since previous close; delta-summed; SAME/OPPOSITE-sign badge vs the L13 standing book) is a PARITY PREREQUISITE for L7/L8, not a §2.5 extension — the parity target's vanna/charm reprice today's classified OI only (#596). Standard taxonomy; no D3 deviation. L7/L8 BUILT-vs-BLOCKED disposition remains gated on the 10-07 A4 re-run.

**D-5a — Pressure ranking (ENH-125): DECLINED-ON-EVIDENCE (ADR-025 D4).**
Formula undisclosed (#558). Proximity-weighted |netΓ| and an OI-magnet (oi_call+oi_put)·Gaussian tested read-only over the last 15 NIFTY γ-runs (3 dte-0 days NO-TEST; 12 testable). The defining property — a top-5 ranking that inverts the gamma order — is not reproducible: ρ_top5 mean −0.008 (c=0.75) / −0.083 (c=1.0), range −0.70..+0.80, 6/12 negative = chance. OI-magnet is undefined at dte=0 (σ_T→0). No defensible deviation proxy. Ladder keeps the net-Γ LONG/SHORT sign tag; no pressure-rank ordering ships. Pin location served by the γ-clock max-pain (E-D2). Evidence: `docs/research/s89_rulings/pressure_leg_decline_S89.md`.
**Correction 2026-10-03: strictly-negative ρ_top5 is 6/12 at c=1.0 and 5/12 at c=0.75 (the 6th at c=0.75 is a float-zero, ρ=−1.4×10⁻¹⁷ on 09-21). The decline stands — mean ρ≈0 at both c (−0.0083 / −0.0833); 5/12 strengthens it. Detail: pressure_leg_decline_S89.md §4.**

**D-5b — Time boost (L2): D3 deviation.**
boost(T) = 2.53 · T^(−0.5), T in trading days to expiry, cap 3.70, floor T = 0.47. Reproduces the two disclosed anchors (1.13× at 5 DTE, 3.70× at the 1DTE close) under charm ∝ 1/√T. Not validatable against our data (his boost unobserved); stated as ours.

**D-5c — Conviction (ENH-122): D3 deviation, two-stage.**
Stage 1 (now): (leader − runner-up margin) · boost(T). Stage 2: multiply by the 30-session HHI percentile once ENH-133 history exists.

## ENH-133 — per-cycle layer-history table: scope RULED 2026-10-03

Bound spec: **`docs/research/s89_rulings/ENH-133_schema_spec_S89.md`**. Authored, unapplied DDL:
**`sql/2026-10-03_s89_gex_cycle_history.sql`**. Proposed table name `gex_cycle_history`.

**The five scope decisions.**

1. **ENH-133 and ENH-134 are COMPLEMENTS, not alternatives** (D-3). 133 accumulates forward;
   134's as-of functions cover the already-stored window. Neither replaces the other.
2. **Grain:** one row per `(symbol, expiry_date, ts)` at the 5-minute γ cadence, both expiry
   legs, `run_id` stored not keyed. The key is a timestamp rather than a cycle ordinal, so a
   future **1-minute pass (Candidate A)** writes into the same table unchanged.
3. **Session gate = `distinct_spot > 1`, write-and-flag.** The row is written even when the
   gate is false; the default history read filters `is_trading_session = true`. Row counts and
   distinct-`ts` counts cannot do this job — 2026-10-02 passes both (TD-S89-NEW-1).
4. **Retention: keep indefinitely, explicitly OUTSIDE `pg_cron` jobid 19.** Stated in the DDL
   `COMMENT ON TABLE`, the spec and the registers; a future retention job must name this table
   to touch it.
5. **`pin_state` and `held_for_cycles` are STORED carry-forward**, not re-derived on read —
   `held_for_cycles` counts only `is_trading_session = true` rows, so a holiday or frozen gap
   does not increment it.

**The pin-leader binding.** `pin_leader_strike` = `v_gex_strike_rank.strike` at
`strike_rank = 1` (gamma concentration), `gamma_at_pin` = its `gex_cr`.
`runnerup_share_ratio` = `share_of_abs(rank 2) / share_of_abs(rank 1)` — near 1 = not locked.
`conviction` = `(1 − runnerup_share_ratio) · boost(T)` (D-5b / D-5c), with **T in TRADING days:
`gamma_metrics.dte` is CALENDAR days (measured) and must be converted, never fed to `boost()`
directly.** `conc_top1_share` carries `v_gex_concentration.hhi_net` under an **honest name** —
it is the top-1 strike share, proven byte-identical to the rank-1 `share_of_abs` and to
`gamma_metrics.gamma_concentration`, and **not** a Herfindahl (true Σs² is ~half). It is never
named `hhi_*` in this table.

**Five scalars the ruling named exist in NO relation** and are writer-derived, not selected:
runner-up strike, runner-up margin, gamma at pin, top-5 share, per-rank shares.
**`merdian_parameters` is EMPTY (0 rows, measured)**, so seeding the `pin_state.*` dot-keys is
part of the writer deliverable, and a missing key leaves `pin_state` NULL with a reason —
never a substituted default (ADR-020).

**No DDL was applied and no writer was written.** The schema ADR is the next artefact
(TD-S80-NEW-7 precedent); the spec is its input.

## L11 (five-axis radar) — DECLINED-ON-EVIDENCE (2026-10-03)

Absent from the parity target's terminal sample (`parity_target_render_study.md` §A2 — the terminal sample — not one of the 49 live values),
landing-page illustration only (`parity_target_render_study.md` §A1), 0–10 per-axis scaling and axis feeds undisclosed
(`parity_target_render_study.md` §F.4); composition-only, no new signal, three of five
inputs unbuilt/gated. **ADR-025 D3** (reference doesn't render it) + **D4** (decline is a
completed disposition, distinct from BLOCKED). **L11: PENDING → DECLINED-ON-EVIDENCE.**

---

## Session facts behind the #14 ruling, recorded once

Measured, not recalled. Evidence is the log named above.

| Fact | Value |
|---|---|
| Canary | `~/s89_canary/c.txt`, 24 B, prefix `CANARY-`, random hex, non-secret, nothing sourced |
| Denies added | 4, mirroring the `.env` verb+glob style: `Read(~/s89_canary/c.txt)`, `Edit(~/s89_canary/c.txt)`, `Bash(cat *s89_canary/c.txt*)`, `Bash(grep *s89_canary/c.txt*)` |
| Deny count | 22 → 26 during the run, **22 after restore** (computed, not eyeballed) |
| Backup | `~/.claude/settings.json.bak_s89`, 1,635 B; the four older `.bak` files untouched |
| Restore proof | `diff` empty; both files sha256 `c7f99908a6e058c27960c398e1889c44b4800f56d83db33e1a01e7395c84aefb` |
| Cleanup | `c.txt` removed and its absence tested; the log kept |
| End state | Sandbox **not** enabled, no `sandbox` block written, no `settings.local.json`, `bwrap`/`socat` still absent |

**Why the CONTROL run exists, since it was not asked for.** Without a run of the *denied*
spelling, a bypass reading on `/bin/cat` could not be distinguished from "the settings were
never reloaded into this session". The control came back hard-denied, which is what makes the
`/bin/cat` result a measurement rather than a coincidence.

**A correction, recorded because it bears on how any future canary run must be read.** My first
classification of the `/bin/cat` result was *"BYPASS — executed with NO prompt"*, and that was
wrong. **I cannot observe whether a command prompted**: the tool result carries the command's
output and nothing about the approval path, so the prompt and the operator's approval were
invisible to me. I had no basis for the "no prompt" half and should have said the prompt state
was unobservable rather than asserting it. The operator supplied the correct reading, which the
ruling above uses. **Consequence for the owed sweep: each form's verdict must come from the
operator, or be inferred only from the sentinel's absence — never from my asserting that
nothing prompted.**

---

## Still owed after these rulings

1. **The multi-spelling enumeration sweep** — explicitly *not* discharged by #14 beyond the one
   form. Needs an **operator-authored or reference list**; I am not to generate or extend it.
2. **Sandbox enable, via operator-typed `/sandbox`** — plus the package install (`sudo apt-get
   install bubblewrap socat`), neither of which ran. `/sandbox` is a built-in CLI command and
   cannot be invoked by me.
3. **Post-sandbox verification of the §7(e) form** — deferred with the enable. Expected
   post-state: HELD.
4. **Where these rulings are reflected at the S89 doc-close** — ADR-029's §7 row (e) currently
   reads *"Measured on one form only"*, which this run does **not** contradict: the canary is a
   second instance of the same single form, not a second form. Whether row (e) gains a
   confirmation note is an amendment decision, not a doc-close edit.

---

*S89 rulings, recorded 2026-10-03. Every ruling here is the operator's text verbatim. Nothing here
authorises a build, an install, or a sandbox enable.*
