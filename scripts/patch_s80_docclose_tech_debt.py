#!/usr/bin/env python3
"""patch_s80_docclose_tech_debt.py

S80 doc-close, file 1 of 10 -- docs/registers/tech_debt.md

FOUR substitutions, each count==1:
  1. Insert TD-S80-NEW-1..13 at the head of Active debt (12 filed, 1 withdrawn
     before filing -- ID retained per Rule 5).
  2. Annotate TD-S79-NEW-1 in place with the S80 measurement (Rule 8 lifecycle
     step 3: update when root cause is better understood). The S80 numbers make
     the entry's claim STRONGER, not merely confirmed -- the overstatement is
     time-varying and it HIDES an intraday effect.
  3. Remove TD-S79-NEW-12 from Active debt.
  4. Re-insert it at the head of Resolved (audit trail) with a closure block,
     in the TD-S79-NEW-14 form ("-- RESOLVED:" in the title).

Host-agnostic: target resolves from <this script>/../docs/registers/tech_debt.md.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchors, line-delta computed FROM the replacement text (never hardcoded),
_PRE_S80_DOCCLOSE backup, dry-run default (--apply).
"""
import argparse, pathlib, sys

DEFAULT_TARGET = pathlib.Path(__file__).resolve().parent.parent / "docs" / "registers" / "tech_debt.md"
MARKER = "TD-S80-NEW-1 "

# ── 1. new entries at the head of Active debt ───────────────────────────────

OLD_1 = r"""> Items below are illustrative seeds based on the project state I've read.
> Audit and adjust before committing — replace with the real current state.

### TD-S79-NEW-1 (S2 priority) — `GREATEST(dte, 1)` overstates σ on expiry day, so the moneyness band is widest on the day it most needs to bind
"""

NEW_ENTRIES = r"""### TD-S80-NEW-1 (S2 priority) — the ingest discards the expiry ladder the vendor returns, so no multi-expiry IV exists at any timestamp and L9 has no live source

| Field | Value |
|---|---|
| **Priority** | **S2.** No data is wrong; a capability the vendor supplies for free has never been captured. It blocks a specced parity layer outright. **PARTIALLY REMEDIATED this session** — see Status. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `ingest_option_chain_local.py:325-366` · `option_chain_snapshots` |
| **Measured** | Across **every cycle the table has ever held** — 1,462 NIFTY + 1,461 SENSEX — `min_exp = avg_exp = max_exp = 1` and `cycles_multi_expiry = 0`. One expiry per cycle, always, ~400–470 strike rows. |
| **Mechanism, from source** | `dhan.get_expiry_list()` at `:327` returns the **whole ladder**. `:365` takes `future_expiries[0]` and discards the rest. `:374` already parameterises the chain call by expiry, so fetching more was never an integration problem. **No comment anywhere states why only one is taken.** |
| **What it blocks** | An IV term structure is ATM IV at two or more expiries **compared at one moment**. With one expiry per cycle there is nothing to compare, at any timestamp, ever. The parity spec's L9 names `option_chain_snapshots` as *"full expiry ladder per cycle"* — see **TD-S80-NEW-2**. |
| **What history can and cannot give** | `hist_option_greeks_1m` carries 2 expiries per minute with IV, but ends **2026-03-30**. `hist_option_bars_1m` carries **21 expiries** at day level with OI, but **no IV**, and ends 2026-05-07. **2026-03-30 → present has no multi-expiry IV source at all, and it cannot be backfilled.** Every day the ladder is not captured is permanently missing. |
| **Not a lost capability** | `historical_option_chain_snapshots` shows up to 3 expiries per cycle, but **every such cycle is 2026-04-16** — `breeze_backfill_s35`, which the parity spec §1.1 records as carrying no spot, no greeks and no bid/ask. The live ingest never captured a ladder in either relation. **No regression occurred; the capability never existed.** |
| **Proper fix** | Loop `select_expiries(sorted(future_expiries), depth)` instead of indexing `[0]`, with **one `run_id` per expiry** — `infer_expiry_date` raises on a multi-expiry run (TD-S79-NEW-12) and `build_gss_rows` stamps one expiry scalar per run, so a shared run_id would corrupt `dte` → `gex_strike_snapshots.dte` → ENH-120's σ silently. |
| **Cost to fix** | Code shipped this session. The remaining cost is the staged rollout and its rate-limit measurement — see Status. |
| **Cross-ref** | **ADR-025** (depth measured, not assumed) · **TD-S80-NEW-2** (the spec claim) · TD-S79-NEW-12 (the guard this required first) · **TD-080** (Dhan 429, S1-recurring — `core/dhan_client.py` has no proactive call spacing, all 429 handling is reactive) · `sql/2026-09-22_s80_*` |
| **Status** | **OPEN — code deployed INERT.** `EXPIRY_DEPTH = {"NIFTY": 1, "SENSEX": 1}` at commit `b094fa2`; the extra-expiry pass is behind `if _depth > 1` and does not execute. Stage 2 is `{"NIFTY": 2, "SENSEX": 2}` on a non-expiry day; stage 3 is NIFTY to 4 after a week of ENH-99 retry telemetry. **Closes only when depth is actually raised and verified**, not when the code landed. |

---

### TD-S80-NEW-2 (S2 priority) — three claims in the Hedgewall parity spec are refuted by measurement, and the spec is what sequences the remaining build

| Field | Value |
|---|---|
| **Priority** | **S2.** The spec is a source-resolution document used to order a multi-session programme. Three of its claims are wrong and one of them made a layer look like a 3-hour view when it is an ingest change. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `MERDIAN_Hedgewall_Parity_Spec.md` — §2 L4, L5, L9, L13 and §3's ordering |
| **(1) L9's live source is false** | *"Source, live \| `option_chain_snapshots` — full expiry ladder per cycle."* Measured one expiry per cycle across all 2,923 cycles (TD-S80-NEW-1). It was **never** true at any point in the system's history. |
| **(2) L4 still recommends a construction S79 rejected** | L4 says `argmax(oi)` and `argmax(gamma × oi)` *"differ and both are worth rendering."* S79 measured the gamma-weighted form collapsing to ATM at **−0.09σ / +0.19σ** and **REJECTED** it — it finds the money, not the wall. |
| **(3) L4 / L5 / L13 name columns that do not exist** | The spec uses `oi_total_calls` / `oi_total_puts`; `gex_strike_snapshots` carries **`oi_call` / `oi_put`** per ADR-015. A build following the spec literally fails with an undefined-column error. |
| **Consequence for §3's ordering** | L9 sits at **#2, 3 h, "cheapest real read on the list."** The real shape is an ingest change, a backfill that cannot happen, a live panel with zero history at launch, and a chart with a discontinuity at 2026-03-30 between a 2-point historical slope and a live multi-point one. **§3's effort figures were derived from source resolution, never from building anything**, and two are now measured wrong. |
| **Root cause** | All three are the same reflex — reasoning from a register or a row count when the source was available. **ADR-024 §A9 names it and attributes four of its own eight self-corrections to it.** ~400 rows per OCS cycle *looks* like a ladder if `expiry_date` is never counted. |
| **Proper fix** | Correct the three claims in place; re-derive §3's ordering from measured cost rather than inherited estimates, per **ADR-025's Consequences**. Record that the spec is S78-dated and decays. |
| **Cost to fix** | ~30 min of text. The ordering re-derivation is the judgement, not the typing. |
| **Cross-ref** | **ADR-025** (§ Spec corrections records all three) · TD-S80-NEW-1 · ADR-024 §A9 · ADR-015 (the real column names) · **TD-S79-NEW-22** (no acceptance criterion — now closed by ADR-025) |
| **Status** | **OPEN.** Recorded in ADR-025; the spec file itself is unedited. |

---

### TD-S80-NEW-3 (S3 priority) — `max_pain_in_pin_band` fires on two runs in five regardless of DTE, so it cannot discriminate and must not be read as a weaker form of coincidence

| Field | Value |
|---|---|
| **Priority** | **S3.** Display-layer only, on a parked extension. The hazard is a consumer treating the boolean as a signal. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `v_gex_pin_maxpain.max_pain_in_pin_band` (ENH-124) |
| **Measured** | Session-hours only, 11,795 runs. Band-membership rate runs **20.8 % – 42.1 %** across all ten symbol×DTE cells. Exact strike coincidence over the same cells runs **1.2 % – 13.9 %**. |
| **The discriminating case** | **NIFTY 6-DTE has the HIGHEST band rate in the sample (42.1 %) on a 2.9 % exact rate**, while NIFTY 0-DTE — the one genuinely elevated cell at **13.9 % exact** — has a *lower* band rate at 41.9 %. So the two quantities do not rank the same cells and the band boolean carries no information the exact test carries. |
| **Why that matters** | "Max pain and the pin on the same strike" was the reading ENH-123/124 were built for. A consumer reaching for a softer version of it would naturally reach for `in_band`, and would get a flag that is true two times in five whatever the market is doing. |
| **Proper fix** | Either drop the column, or document in the view comment that it is descriptive geometry and not a signal. **Do not widen it into a tolerance** — TD-S79-NEW-21's ruling applies, and ENH-124 deliberately ships a distance with no tolerance constant. |
| **Cost to fix** | ~10 min (one `COMMENT ON VIEW` amendment) or a column drop with a grant re-apply. |
| **Cross-ref** | ENH-124 · **TD-S79-NEW-21** (measure, then parameterise) · parity spec §5 + **ADR-009** (whether coincidence predicts anything is a pre-registered conjunction question, unanswered; ENH-97's chi-sq 1.56 / p≈0.30 on 1,968 signals is the standing warning) |
| **Status** | **OPEN.** |

---

### TD-S80-NEW-4 (S2 priority) — the documented commit-message pattern emits a BOM, and one shipped inside a commit subject this session

| Field | Value |
|---|---|
| **Priority** | **S2.** Cosmetic per commit, but it lands in every commit made by the documented method and it breaks any tooling that matches a commit subject by prefix. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | The commit-message temp-file pattern — `Out-File -Encoding utf8 -NoNewline` |
| **Symptom** | `git log --oneline -1` on `b094fa2` renders **`﻿S80 - TD-S79-NEW-12 guard...`** — U+FEFF before the first character. `43382ea` and `35b68f7` do not carry it, so this is new rather than long-standing. |
| **Root cause** | **Windows PowerShell 5.1's `utf8` encoding writes a BOM.** `-NoNewline` suppresses the trailing newline and has no effect on the byte-order mark. Only PowerShell 6+ offers `utf8NoBOM`. The working note records this pattern as the one that *"avoids BOM and heredoc issues"* — it avoids the heredoc issue only. |
| **Why it was not caught** | The pattern was adopted for a reason that is half-true, and a BOM is invisible in most terminals and in most diffs. It surfaced here only because the commit subject was read back deliberately. |
| **Deliberately not amended** | `b094fa2` is pushed and pulled and verified on both hosts. Force-pushing `main` to fix a subject-line character is a worse trade than carrying it, particularly given the register's own note that **tags must be re-verified after any amend cycle**. |
| **Proper fix** | Replace the pattern with `[System.IO.File]::WriteAllText($path, $msg, (New-Object System.Text.UTF8Encoding $false))` — used for `85dfad2`, which carries no BOM. Correct the working note, which currently states the opposite. |
| **Cost to fix** | ~5 min of text. |
| **Cross-ref** | commits `b094fa2` (with BOM) and `85dfad2` (without) · TD-S78-NEW-3 (the PK LF→CRLF round-trip — the same encoding-assumption family one tier over) |
| **Status** | **OPEN.** Method corrected in practice from `85dfad2`; the written rule still says the wrong thing. |

---

### TD-S80-NEW-5 (S2 priority) — ADR-025 was accepted and committed alone, so Rule 11.4's single-commit closure did not happen — in the session that wrote the acceptance criterion

| Field | Value |
|---|---|
| **Priority** | **S2.** The same defect class the Decision Index's ADR-024 row spent a paragraph documenting, repeated one ADR later. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `docs/decisions/ADR-025-parity-acceptance-criterion.md` · commit `b094fa2` |
| **Symptom** | Doc Protocol v4 **Rule 11.4** specifies a five-step order ending *"Single commit with all four files."* `b094fa2` carries the ADR plus unrelated code and **none** of: the Decision Index row (11.1), the CLAUDE.md governance footer (11.3), or an Assumption Register update (11.2). |
| **Aggravating** | ADR-024's Decision Index row carries a **READINESS CAVEAT** explicitly naming this failure — *"Rule 11.4 step 1 never ran"* — and was written six days earlier. The precedent was on the page and was not followed. |
| **Why it happened** | The ADR was drafted mid-session as the deliverable of an open decision (D0), then committed opportunistically with the code that was ready. Rule 11.4 is an ordering constraint and nothing enforces ordering. |
| **Proper fix** | Complete 11.1 / 11.2 / 11.3 in this doc-close. Then consider whether Rule 11.4 is enforceable at all without a check — **TD-S79-NEW-24**'s finding is the same shape: a footer need not cite its ADR id and 87 of 120 do not, so compliance cannot be counted. |
| **Cost to fix** | Closed by the S80 doc-close itself. The enforceability question is separate. |
| **Cross-ref** | **Doc Protocol v4 Rule 11.1–11.4** · Decision Index ADR-024 row (the caveat) · **TD-S79-NEW-24** (Rule 11.3 unenforced) · **TD-S79-NEW-25** (no PK manifest, so Rule 12 compliance is undetectable) |
| **Status** | **OPEN at filing; closes with this doc-close's Decision Index, CLAUDE.md and Assumption Register edits.** |

---

### TD-S80-NEW-6 — WITHDRAWN (2026-09-22, before filing) — "3,093 `run_id`s against 2,923 `(symbol, ts)` cycles, unexplained"

**WITHDRAWN before filing.** The claim was that `option_chain_snapshots` holds 170 more distinct `run_id`s than `(symbol, ts)` pairs while **no** `(symbol, ts)` carries more than one `run_id` — arithmetically impossible, so presented as an anomaly needing a cause.

There is no anomaly. **The two figures were measured three days apart.** The 2,923 count was taken on 2026-09-19; the 3,093 count on 2026-09-22. Monday 2026-09-21 was a trading day and wrote **exactly 85 runs per symbol = 170**. `null_ts`, `null_symbol` and `null_run` are all **0**, so the NULL-collapse hypothesis is dead too.

Filed as a withdrawal rather than deleted, because the error is worth keeping: **two measurements of a growing table were compared without reading their own dates.** Same family as the S78 precedent (TD-S78-NEW-7, withdrawn before filing on the same discipline). ID retained per Rule 5. Recorded also in **ADR-025 Amendment A** as an S80 self-correction.

---

### TD-S80-NEW-7 (S3 priority) — `gex_pin_maxpain_history` is a Rule 10 schema-affecting table with no ADR of its own

| Field | Value |
|---|---|
| **Priority** | **S3.** The table is registered in `sql/`, documented in its own header, and parked. What is missing is the decision record Rule 10 requires. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `public.gex_pin_maxpain_history` · `sql/2026-09-22_s80_gex_pin_maxpain_history.sql` |
| **Symptom** | Doc Protocol v4 **Rule 10** makes an ADR mandatory before code for *"anything adding/removing/restructuring a load-bearing table or its primary write contract."* The table was created, populated with 11,795 rows, and committed with no ADR. |
| **Is it load-bearing?** | Arguable and worth arguing in the ADR rather than asserting here. It has no live consumer and feeds no production path (ADR-025 D5 parks it as L19). But it holds a derived series a future session will reason from, and its write contract — one row per `(symbol, run_id, expiry_date)`, `ON CONFLICT DO NOTHING` — is what makes the backfill resumable. |
| **What the ADR has to settle** | Whether a materialised reproduction of a latest-run-scoped view is the right answer to ADR-021's consequence (the pin band is unreadable historically by construction), or whether the view should instead gain a parameterised scope. The second is the more general fix and was not considered at the time. |
| **Proper fix** | Draft the ADR. **ADR-025 does not cover this** — it rules on the parity programme's acceptance criterion, not on this table's design, and says so. |
| **Cost to fix** | ~0.5 session. |
| **Cross-ref** | **ADR-021** (why the history is unreadable from the view) · **ADR-025 D5** (parks it as L19) · ADR-015 (`gex_strike_snapshots`, the base) · TD-S80-NEW-8 |
| **Status** | **OPEN.** |

---

### TD-S80-NEW-8 (S3 priority) — the backfill driver hardcodes its date window, so the script that produced 11,795 rows cannot be re-run without a code edit

| Field | Value |
|---|---|
| **Priority** | **S3.** The data is complete and verified. This is re-runnability, not correctness. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `scripts/backfill_pin_maxpain.py` — `start = dt.date(2026, 5, 25); end = dt.date(2026, 9, 18)` |
| **Symptom** | The window is a module-level literal. Extending the series past 2026-09-18, or re-running a corrected window, requires editing the file. |
| **Why it was committed this way** | Deliberately. The committed copy is **byte-identical to the one that ran** — sha256 `453f1be8…` verified on both hosts before and after the git round trip. Parameterising it first would have made the committed artefact something other than the one that produced the data being reasoned from. **Fidelity beat tidiness.** |
| **Proper fix** | `argparse` for `--from` / `--to` / `--symbols`, defaulting to the stored max `ts` onward so an incremental top-up needs no arguments at all. |
| **Cost to fix** | ~20 min. |
| **Cross-ref** | `sql/2026-09-22_s80_backfill_pin_maxpain_runs.sql` (the RPC it drives) · TD-S80-NEW-7 |
| **Status** | **OPEN.** |

---

### TD-S80-NEW-9 (S3 priority) — the ingest day starts at 08:30, 08:35 or 08:40 IST and loses one or two cycles, and nothing records which

| Field | Value |
|---|---|
| **Priority** | **S3.** One or two cycles out of 87, pre-open, on a table with ~34k rows per symbol per day. Real but small. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `run_ingest.sh` crontab entries (hour 03 UTC) · `option_chain_snapshots` |
| **Measured** | First row per day, both symbols: 09-15 **08:35**, 09-16 **08:30**, 09-17 **08:35**, 09-18 **08:40**, 09-21 **08:40**. Run counts **86 / 87 / 86 / 85 / 85** against a crontab complement of **87** (twelve fires in hour 03, seventy-two across 04–09, three in hour 10). |
| **The pattern** | The day that started at 08:30 got all 87. The days that started at 08:40 got 85. So the losses are **the first one or two fires**, not scattered. |
| **Candidate cause, NOT established** | `overview.md` records the Dhan token refresh at **03:05 UTC = 08:35 IST**, which is *after* the 08:30 and 08:35 ingest fires. A stale-token failure on the earliest cycles would produce exactly this shape. **Unmeasured** — `script_execution_log` should say, and was not queried. |
| **Why it is worth an entry** | `merdian_daily_audit.py` thresholds on a day **total** (`option_chain_snapshots_min: 80_000`), so 85 cycles and 87 cycles both pass and the loss is invisible. The same shape as TD-S71-NEW-15: a total-row assertion with no per-cycle parity. |
| **Proper fix** | Query `script_execution_log` for the 03:00/03:05 UTC invocations across a week and read the `exit_reason`. If it is the token, either move the ingest's first fire after the refresh or make the refresh earlier — a one-line crontab change either way. |
| **Cost to fix** | ~20 min to measure; the remedy is one crontab line. |
| **Cross-ref** | `overview.md` token-flow timings · TD-S71-NEW-15 (total-count assertions with no per-symbol parity) · TD-080 (Dhan 429 — the other candidate) |
| **Status** | **OPEN — cause unmeasured, shape established.** |

---

### TD-S80-NEW-10 (S3 priority) — `v_max_pain_by_strike` emits no timestamp and takes an unbounded `max(ts)`, so it serves a plausible stale strike to Marketview if chain ingest stops

| Field | Value |
|---|---|
| **Priority** | **S3.** It renders on an operator page. It has not misled anyone on the evidence available, and the failure needs an ingest stall to fire. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `public.v_max_pain_by_strike` (S40, `sql/v_max_pain_by_strike.sql`) · Marketview Max Pain page |
| **Symptom** | `latest_ts` is `max(ts)` per symbol **with no recency floor**, and the view's output columns are `symbol, candidate_strike, total_pain, max_pain_strike, side` — **no `ts`, no `run_id`, no `expiry_date`**. If chain ingest stops, `max_ts` silently falls back to the last good cycle and the view returns a complete, well-formed max-pain strike from whenever that was. Nothing downstream can tell. |
| **Live instance of the shape** | At 2026-09-19 11:40 IST the newest `option_chain_snapshots` row was **2026-09-17 15:40 IST** — the view was serving a two-day-old strike, correctly, with no way to know. |
| **The same failure, already paid for** | This is `breadth_intraday_history` writing full 431-row days at `coverage_pct: 0` — a relation that fails silently in row count and loudly only in content nobody reads. It is also exactly what **ADR-023** exists to prevent: *"fails to absent, never to stale."* |
| **Second, latent defect** | `chain` groups by `(symbol, strike)` with **no expiry filter**, so a snapshot carrying two expiries would collapse into a per-strike `max()` mixture. **Not firing** — measured one expiry per cycle across all 2,923 cycles — but it becomes live the moment TD-S80-NEW-1's depth is raised, since the ladder then lands in the same table. |
| **Proper fix** | Add a recency floor per **ADR-023 D1** and emit `ts` so a consumer can see its own staleness; add the expiry filter **before** raising ingest depth. ENH-123's `v_gex_max_pain` already does all three and is the reference. |
| **Cost to fix** | ~30 min for the view, plus a Marketview change to surface the age. |
| **Cross-ref** | **ADR-023** D1/D3 · **ENH-123** (`v_gex_max_pain`, which carries `ts`, coverage and a probed freshness floor) · TD-S80-NEW-1 (raising depth arms the expiry defect) · ADR-021 (the sibling scoping fix) |
| **Status** | **OPEN.** The expiry half must be fixed **before** stage 2 of TD-S80-NEW-1. |

---

### TD-S80-NEW-11 (S3 priority) — `option_chain_snapshots` retention is 18 days, not the ~11 carried in the register

| Field | Value |
|---|---|
| **Priority** | **S3.** A figure correction. It matters because it was used to reason about what a layer could be built on. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `option_chain_snapshots` |
| **Measured** | `MIN(ts)::date` **2026-08-24**, `MAX(ts)::date` **2026-09-17**, `COUNT(DISTINCT ts::date)` = **18**. The register carried *"a ~11-day retention horizon."* |
| **Why the number moved** | Unestablished. The floor lands exactly on **2026-08-24**, which is also the boundary of the coverage gap carried as unverified since S79 — so 18 days may be a retention window, a start date, or both. The two readings are not distinguished by this measurement. |
| **What it does not rescue** | 18 days is still far short of anything historical. The claim that max pain offered *"full history rather than the 62-day IV window"* fails on this source either way — `gex_strike_snapshots` is the relation with history, which is why ENH-123 was built on it. |
| **Proper fix** | Establish whether the floor is pruning or a start date — `pg_cron` job list plus the earliest `created_at` will separate them — and correct the figure wherever it is carried. |
| **Cost to fix** | ~15 min. |
| **Cross-ref** | **ENH-123** (built on `gex_strike_snapshots` for this reason) · TD-S76-NEW-2 (jobid 19, currently DISABLED) · the unverified `option_chain_snapshots` / `gamma_metrics` coverage gap 2026-06-03 → 2026-08-24 |
| **Status** | **OPEN.** |

---

### TD-S80-NEW-12 (S2 priority) — the deploy-direction correction has been drafted and UNRATIFIED since S73, and S80 acted against the topology twice before reading it

| Field | Value |
|---|---|
| **Priority** | **S2.** Two production files were edited in the production tree because a correction that has existed since 2026-09-06 was not read. Nothing broke; the mechanism that exists to make it impossible was bypassed. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `MERDIAN_Deployment_Topology.md` **§S73.A / §S73.B** · **ADR-006** deploy-direction statement · Doc Protocol v4's matching line · **TD-S79-NEW-5** |
| **The correction already exists** | §S73.B tabulates it: `origin/main` **Transport → CANONICAL**, Local Windows **Producer → CONSUMER**, `~/meridian-engine` Consumer, `~/meridian-cc` *(did not exist)* → **Consumer, and producer on a branch**. Marked **UNRATIFIED** and carried for four sessions. Ratifying means amending **ADR-006 and the Doc Protocol line together**, since either alone leaves the pair inconsistent. |
| **The isolation mechanism, and what S80 actually did wrong** | §S73.A: `~/meridian-engine` is production — **53 crontab lines and 20 systemd units resolve inside it**; `~/meridian-cc` is the agent tree, referenced by **no** scheduler. *"Production is read-only-from-git by construction... stricter than ADR-006, not an exception to it — ADR-006 forbids direct edits on the box, and the second tree removes the opportunity."* **S80 ran both canon-v3 patch scripts against `~/meridian-engine`.** The defect is not "authored on EC2" — that is the designed route — it is **"authored in the production tree instead of `~/meridian-cc`."** |
| **Live practice already follows §S73.B** | `s80/srs-exploration` is authored and committed in `~/meridian-cc` and pushed from there — at S80 open it stood at `99efc53` while **Local's `origin/s80/srs-exploration` ref was two commits stale at `35b68f7`**. Local is demonstrably the consumer the table says it is. |
| **Why TD-S79-NEW-5's framing compounds it** | That entry counts "deploy-direction inversion" instances against a direction **the Topology already records as superseded**. Four to five recurrences of the same "violation" is evidence the rule is stale, not evidence of five lapses — and counting them is cheaper than ratifying, so it keeps happening. The instance count is not the finding; the unratified correction is. |
| **What Local-origin genuinely buys, and costs** | Buys: a pull-only production tree and a clean clone-from-origin disaster rebuild. Costs: authoring only at the Windows box; code written where it cannot be tested against the real environment; and the CRLF/LF split, which **C-15 of the Claude Code guardrails** already rules makes cross-tier byte and hash comparison invalid — `git hash-object` is the only valid instrument, and Doc Protocol v4's four-tier hash discipline is *"wrong as written."* |
| **Proper fix** | **Ratify §S73.B** — amend ADR-006's deploy-direction statement and the Doc Protocol line in one pass, per §S73.B's own instruction — and **retire TD-S79-NEW-5's instance counting** into this entry. Then state the tree rule explicitly where an agent will meet it: **work in `~/meridian-cc`, never in `~/meridian-engine`.** |
| **Cost to fix** | ~0.5 session. Zero to keep counting instances, which is why four sessions have. |
| **Cross-ref** | **Deployment Topology §S73.A / §S73.B** · **ADR-006** · **TD-S79-NEW-5** (retired into this entry) · **MERDIAN_ClaudeCode_Guardrails C-15** (cross-tier identity is `git hash-object`) · ADR-025 (the precedent — an unratified practice settled by ADR rather than by repeated filing) · `runbook_disaster_rebuild.md` |
| **Status** | **OPEN.** The S80 instance was reverted and redone through git before anything shipped; the ratification is still owed and is now four sessions old. |

---

### TD-S80-NEW-13 (S3 priority) — `CURRENT.md`'s S79 Ledger describes a follow-on commit as local-only and unpushed; its content is in `main`

| Field | Value |
|---|---|
| **Priority** | **S3.** Stale in the safe direction — it under-claims. But `CURRENT.md` is what the next session reads first, so a false statement there costs a verification pass. |
| **Filed** | 2026-09-22 (Session 80) |
| **Component** | `docs/session_notes/CURRENT.md` — S79 **Ledger** row |
| **Symptom** | The row reads *"A follow-on commit carries `merdian_reference.json`, TD-S79-NEW-23 and these ledger corrections; it is **local-only and unpushed**."* Measured at S80 open: `grep -c "TD-S79-NEW-23" docs/registers/tech_debt.md` = **1** on EC2, and `merdian_reference.json`'s `change_log[0]` reads **S79** on EC2. Local `main` == `origin/main` == `43382ea`. **The content is in `main` on every tree.** |
| **What I got wrong first** | I read the same row and concluded the commit was *missing* — a "phantom commit." That was worse than the row it was correcting: the content was present all along and one `grep` settled it. Recorded in **ADR-025 Amendment A** as an S80 self-correction. |
| **Root cause** | The row was written **during** the doc-close, describing a commit that had not yet been pushed at the moment of writing, and was never revisited after the push. The same shape as TD-S79-NEW-25's finding — a claim about a synchronisation state recorded at a point where it was true and never rechecked. |
| **Proper fix** | The S80 `CURRENT.md` rewrite drops the S79 block to predecessor position and this claim goes with it. Structurally: **a doc-close should not assert a push state it has not yet reached** — state it as owed, or write it after the push. |
| **Cost to fix** | Closed by the S80 `CURRENT.md` rewrite. The discipline point is the durable part. |
| **Cross-ref** | **TD-S79-NEW-25** (Rule 12 compliance undetectable without a manifest — same family) · TD-S73-NEW-8 (eight-fold duplication; a claim repeated in eight places goes stale in eight places) |
| **Status** | **OPEN at filing; closes with the S80 `CURRENT.md` rewrite.** |

---

"""

NEW_1 = OLD_1.replace(
    "### TD-S79-NEW-1 (S2 priority) —",
    NEW_ENTRIES + "### TD-S79-NEW-1 (S2 priority) —",
    1,
)

# ── 2. annotate TD-S79-NEW-1 in place ───────────────────────────────────────

OLD_2 = r"""| **Cross-ref** | ENH-120 · commit `10a7ae5` · CLAUDE.md settled entry on 0-DTE `net_gex` unreconstructibility. |
| **Status** | **OPEN.** |
"""

NEW_2 = r"""| **Cross-ref** | ENH-120 · commit `10a7ae5` · CLAUDE.md settled entry on 0-DTE `net_gex` unreconstructibility. |
| **MEASURED S80 — the overstatement is TIME-VARYING, and it HIDES an intraday effect** | The floor is not a constant scale error. σ_correct/σ_stated = `sqrt(mins_left/375)`, measured on 11,795 stored runs by IST hour: **0.982 at 09:00, 0.898 at 10:00, 0.804 at 11:00, 0.697 at 12:00, 0.570 at 13:00, 0.404 at 14:00, 0.203 at 15:00** — roughly **2 % at the open and ~5× by 15:00**. The consequence is worse than mis-scaling: under the shipped day-σ the 0-DTE pin↔max-pain gap looks **flat** through the session (median −0.398 → −0.224), while under correct remaining-time σ it **more than doubles** (−0.382 → −0.939). **The convention makes a widening gap look stable on the one day the layer matters most.** |
| **Second S80 note — dispersion, not the median** | 0-DTE carries the **tightest** IQR in the sample (NIFTY 0.199, SENSEX 0.254, against 0.32–0.41 elsewhere) while its median sits with every other cell at ≈ −0.32σ. That apparent convergence is at least partly this defect: an inflated denominator compresses the ratio toward zero. **It is not independent evidence of expiry-day convergence and must not be cited as such until σ is corrected.** |
| **Status** | **OPEN — and stronger than as filed.** The S80 measurement supplies the re-sweep's motivation: the chosen 1.5 band was calibrated under this floor, so re-deriving it under intraday σ may not return 1.5. |
"""

# ── 3. remove TD-S79-NEW-12 from Active debt ────────────────────────────────

OLD_3 = r"""### TD-S79-NEW-12 (S3 priority) — `infer_expiry_date` returns `expiries[0]` from an unordered PostgREST result rather than `min()`

| Field | Value |
|---|---|
| **Priority** | **S3.** Wrong by construction, correct in practice, and the thing making it correct is a data property nothing asserts. |
| **Filed** | 2026-09-15 (Session 79) |
| **Component** | `compute_gamma_metrics_local.py:245-247` — **verified against source 2026-09-15** |
"""

NEW_3 = r"""### TD-S79-NEW-12 — RESOLVED S80. See **Resolved (audit trail)**.

| Field | Value |
|---|---|
| **Priority** | **S3.** Wrong by construction, correct in practice, and the thing making it correct is a data property nothing asserts. |
| **Filed** | 2026-09-15 (Session 79) · **RESOLVED 2026-09-22 (Session 80), commit `b094fa2`** |
| **Component** | `compute_gamma_metrics_local.py:245-247` — **verified against source 2026-09-15** |
"""

# ── 4. closure block at the head of Resolved (audit trail) ──────────────────

OLD_4 = r"""## Resolved (audit trail)

### TD-S79-NEW-14 (S2 priority) — RESOLVED: the skip scan is confirmed on all three views; no base-table scan, and planning exceeds execution
"""

NEW_4 = r"""## Resolved (audit trail)

### TD-S79-NEW-12 (S3 priority) — RESOLVED: `min()` plus a raise that states the single-expiry invariant, shipped as a prerequisite rather than a tidy-up

| Field | Value |
|---|---|
| **Priority** | **S3 as filed.** It became a **blocker** at S80 — see *Why it was resolved now*. |
| **Filed** | 2026-09-15 (Session 79) |
| **Resolved** | 2026-09-22 (Session 80), commit **`b094fa2`** |
| **Component** | `compute_gamma_metrics_local.py` `infer_expiry_date()` |
| **Fix applied** | `expiries` becomes a **set**; empty returns `None`; **more than one expiry raises `RuntimeError`** naming the count and the sorted expiries; otherwise returns `min(expiries)`. Applied by `scripts/patch_s80_td_s79_new_12_infer_expiry.py` (canon-v3 — count==1 anchor, line delta 11 computed from the replacement text, `ast.parse` gate, `_PRE_S80` backup, dry-run first). |
| **CAN FIRE — proven, not asserted** | `scripts/probe_s80_expiry_guards.py` loads the function **out of the source file by AST** and executes it in isolation — no module import, so no credentials, no network, no Supabase client, and the text on disk is what is tested. Four cases pass on Local (CRLF) and again on EC2 (LF) after the pull: single expiry → `2026-09-22`; empty → `None`; repeated same expiry → `2026-09-22`; **two expiries → raises.** Exit 0. |
| **Why it was resolved now, and why the order mattered** | The S80 ingest change makes `option_chain_snapshots` able to hold more than one expiry per cycle. Before it, the invariant that saved this code was *"the ingest only ever fetches one expiry"*; after it, the invariant is *"the ingest assigns a distinct `run_id` per expiry"* — **weaker, and a coding slip re-introduces the defect silently.** `fetch_option_chain_rows` filters on `run_id` and symbol with **no expiry filter**, so a multi-expiry run would aggregate `net_gex` / `flip_level` / `max_gamma_strike` / `pin_risk_score` across chains and `build_gss_rows` would stamp one arbitrary `expiry_date` and `dte` across all of `gex_strike_snapshots`. Every S79 and S80 view reads that table by `(run_id, expiry_date)`. **This guard converts that from silent corruption into a crash, and it shipped first.** |
| **`min()` is currently unreachable, deliberately** | With the raise in place, `min()` can only ever act on a one-element set. Both halves were filed for and both are in, but **only the raise is live behaviour** — `min()` is insurance for a future where the assertion is deliberately relaxed. Recorded so a later session does not read `min()` as validated. |
| **Invariant still holds in the data** | Re-measured at S80 on `run_id` directly, not on `(symbol, ts)`: **3,093 runs, `max_exp = 1`, `multi_expiry_runs = 0`.** So the guard cannot fire spuriously on existing data. |
| **Discharges** | **ADR-024 §A10 item 3.** |
| **Cross-ref** | **TD-S80-NEW-1** (the ingest change this gated) · ENH-120 (the σ consumer at the end of the blast radius) · Rule 15 (the PostgREST-shape family) · `scripts/probe_s80_expiry_guards.py` |
| **Status** | **CLOSED 2026-09-22 (S80, `b094fa2`).** |

---

### TD-S79-NEW-14 (S2 priority) — RESOLVED: the skip scan is confirmed on all three views; no base-table scan, and planning exceeds execution
"""

SUBS = [
    ("1. TD-S80-NEW-1..13 at head of Active debt", OLD_1, NEW_1),
    ("2. TD-S79-NEW-1 S80 annotation", OLD_2, NEW_2),
    ("3. TD-S79-NEW-12 header -> resolved pointer", OLD_3, NEW_3),
    ("4. TD-S79-NEW-12 closure block in Resolved", OLD_4, NEW_4),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write; default is dry-run")
    ap.add_argument("--target", default=str(DEFAULT_TARGET))
    args = ap.parse_args()

    target = pathlib.Path(args.target)
    print(f"target: {target}")
    if not target.is_file():
        print("ABORT: target not found.", file=sys.stderr)
        return 1

    raw = target.read_bytes()
    text = raw.decode("utf-8-sig")
    had_bom = raw.startswith(b"\xef\xbb\xbf")

    crlf = text.count("\r\n")
    lf_only = text.count("\n") - crlf
    eol = "\r\n" if crlf > lf_only else "\n"
    base_lines = text.count("\n")
    base_bytes = len(raw)
    print(f"baseline: {base_lines} newlines, {base_bytes} bytes")
    print(f"EOL: CRLF={crlf} LF={lf_only} -> {'CRLF' if crlf > lf_only else 'LF'}; BOM={had_bom}")

    if MARKER in text:
        print("IDEMPOTENT: marker already present. Nothing to do.")
        return 0

    norm = text.replace("\r\n", "\n")
    patched = norm
    expected = 0

    for label, old, new in SUBS:
        n = patched.count(old)
        print(f"[{label}] anchor count == {n} (must be 1)")
        if n != 1:
            print(f"ABORT: anchor not unique for {label}.", file=sys.stderr)
            return 1
        patched = patched.replace(old, new, 1)
        expected += new.count("\n") - old.count("\n")

    got = patched.count("\n") - norm.count("\n")
    print(f"line delta expected {expected}, got {got}")
    if expected != got:
        print("ABORT: line delta mismatch.", file=sys.stderr)
        return 1

    # every substitution here adds text; none may shrink the file
    if len(patched) <= len(norm):
        print("ABORT: file did not grow.", file=sys.stderr)
        return 1
    print(f"byte delta (normalised): +{len(patched) - len(norm)}")

    for tid in [f"TD-S80-NEW-{i}" for i in range(1, 14)]:
        c = patched.count(f"### {tid} ")
        if c != 1:
            print(f"ABORT: {tid} heading count == {c}, must be 1.", file=sys.stderr)
            return 1
    print("13 TD-S80-NEW headings present, one each")

    if patched.count("### TD-S79-NEW-12") != 2:
        print("ABORT: TD-S79-NEW-12 must appear as exactly 2 headings "
              "(active pointer + resolved block).", file=sys.stderr)
        return 1
    print("TD-S79-NEW-12 present as pointer + closure block")

    if not args.apply:
        print("\nDRY RUN -- no write. Re-run with --apply.")
        return 0

    backup = target.with_name(target.name + "_PRE_S80_DOCCLOSE")
    backup.write_bytes(raw)
    print(f"backup: {backup}")

    out = patched.replace("\n", eol) if eol != "\n" else patched
    target.write_bytes((b"\xef\xbb\xbf" if had_bom else b"") + out.encode("utf-8"))
    print(f"WROTE {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
