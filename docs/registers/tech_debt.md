# MERIDIAN Technical Debt Register

**Purpose:** A single living markdown file for *known broken-ish things* that aren't blocking but shouldn't be forgotten. This file fills the gap between:

- **C-N (critical)** in `merdian_reference.json` → must fix before next live session
- **ENH-N (enhancement)** in `Enhancement_Register.md` → forward-looking proposal, may never be built
- **Session-local tasks** in `session_log.md` → don't persist past today
- **Tech debt (this file)** → persistent, known, has a workaround, will be paid down when convenient

If an item doesn't fit those four buckets, it doesn't get tracked.

---

## How to use this file

1. **Add an item** when you discover a real issue mid-session that has a workaround and isn't blocking. Use the template below.
2. **Update an item** when the workaround changes, severity changes, or you learn more about root cause.
3. **Close an item** when fixed — move it to the `# Resolved (audit trail)` section at the bottom with the closing commit hash. Never delete.
4. **Promote** to C-N if it becomes blocking, or to ENH-N if it grows into a real enhancement.

---

## Severity scale

| Sev | Meaning | Response time |
|---|---|---|
| **S1** | Production-impacting workaround in place. Fix this sprint. | Within 5 sessions |
| **S2** | Non-blocking but degrades a real user-facing or research workflow. | Within 15 sessions |
| **S3** | Cosmetic, performance-tolerable, or affects only edge cases. | When convenient |
| **S4** | Anti-pattern flagged for future refactor. No active impact. | Aspirational |

---

## Item template

```markdown
### TD-<NNN> — <one-line title>

| | |
|---|---|
| **Severity** | S1 / S2 / S3 / S4 |
| **Discovered** | YYYY-MM-DD (session/appendix ref) |
| **Component** | <file path or table or system area> |
| **Symptom** | What you observe when this hits |
| **Root cause** | What we believe causes it (or "unknown") |
| **Workaround** | What is currently being done to live with it |
| **Proper fix** | What the real fix looks like |
| **Cost to fix** | <est sessions or hours> |
| **Blocked by** | <ENH-N, TD-N, or "nothing"> |
| **Owner check-in** | <date when last reviewed> |
```

---

## Active debt

> Items below are illustrative seeds based on the project state I've read.
> Audit and adjust before committing — replace with the real current state.
>
> **S82 PROPOSAL, NOT APPLIED — this note is a template artefact and is now false.**
> `git log -S` traces it to **`c521b2f`, *"v3 routine outputs for 2026-04-22 Session 5
> closeout"*** — it has stood at the head of Active debt since **2026-04-22**, across
> ~77 sessions, while every entry below it became a measured item. It is left in place
> rather than deleted because removing a header is an operator call, not a doc-close
> edit. **Recommend deletion next session.**

**NOTE — 2026-10-03 (D-5a).** C1/C2 pressure proxies tested and declined. proximity-|netΓ| and OI-magnet (oi_call+oi_put)·Gaussian; top-5 gamma-inversion at chance over 12 NIFTY γ-runs; OI-magnet undefined at dte=0. Pointer: `docs/research/s89_rulings/pressure_leg_decline_S89.md`. Do not re-litigate without a newly disclosed formula or ENH-133 history enabling a materially different key.

**NOTE — 2026-10-03.** `v_gex_concentration.hhi_net` is the **top-1 gamma share, NOT a Herfindahl** — byte-identical to `v_gex_strike_rank` rank-1 `share_of_abs` and to `gamma_metrics.gamma_concentration` (0.0942 on 10-01); true HHI Σshare² ≈ 0.0464. The live board's 'HHI' label and D-6's ~0.10 / ~0.25 bands are therefore on **top-1 share**. `hhi_call` / `hhi_put` semantics **unverified**. Verify call/put and correct the board label before any Herfindahl claim.
**FIX (phase-2 Pin tab):** the board's 'HHI' label should display the true `conc_hhi` (Σs²); keep top-1 share as a separate **'lead-strike share'** line. **ENH-133 now stores both.**

**SPLIT — 2026-10-24 (ruling S100-A, `docs/research/s92_parity/rulings_s100.md`).** This file holds the **open** entries:
every entry that is a row of tracker §2.2 (`docs/registers/agentic_layer_roadmap_S90.md`, the single list), the three
that close on the Monday S98-B read, and the four "pass-2 misses" named below. **Every other entry** — closed, resolved,
duplicate, obsolete, parked (signal / ICT, history, trigger-named, agentic) and the `## Resolved (audit trail)` section —
moved **verbatim** to `docs/registers/tech_debt_history.md`; its disposition is in the status paragraphs below. From
now on, "close an item" (step 3 above) means: move its block to the end of `tech_debt_history.md`'s entries, unedited, in
the doc-close that closes it, with one line in that close's status paragraph.

### TD-S99-NEW-1 (S3 priority) — an AWS access key ID is committed in the public repository

| Field | Value |
|---|---|
| **Priority** | **S3 (security).** The key ID alone does not authenticate; with the secret key it would. The repo is public. |
| **Filed** | 2026-10-24 (Session 99; filed at the S98 + S99 doc-close, Session 100) |
| **Component** | `docs/runbooks/runbook_aws_cli_file_operations.md` (lines 9 and 49) · `docs/registers/session_log_history.md` (line 76) — positions as at `3706435` |
| **Measured** | Scan 2026-10-24 of the tree and its history for `AKIA…` key IDs, secret-key shapes, `.env` content and JWTs: **three occurrences of one key ID** (the operator's IAM user) in the two files named; **no secret key, no `.env`, no JWT** in the tree or its history. Re-counted at the S100 doc-close build on a clone at `3706435`: 2 + 1. |
| **Proper fix** | (a) Redact the ID in both files going forward (a docs commit). (b) **The operator's call:** rotate the key (makes the committed ID inert), or rewrite history to remove it, or both. Rotation is the cheaper and sufficient choice if the key is still in use. |
| **Home** | Tracker §2.2 band BS. |
| **Status** | **OPEN.** |

### TD-S100-NEW-1 (S3 priority) — the futures rows keep the 15:15 spot through the closing window, so the stored basis is wrong at 15:30–15:40

| Field | Value |
|---|---|
| **Priority** | **S3.** The board's FUT · BASIS tile shows the stored basis; at 15:30–15:40 it is measured against a spot ~15 min old. |
| **Filed** | 2026-10-24 (Session 100; exposed by the S100-S sub-line `vs spot X @ hh:mm`) |
| **Component** | `index_futures_snapshots.spot_price` (the futures writer) · Marketview FUT · BASIS tile |
| **Measured** | 2026-10-23 NIFTY: the 15:30–15:40 futures rows carry spot 22,516.4 (the held 15:15 print) while the chain rows of the same cycles carry the 22,600.0 close; stored basis +63.7…+72.6 against ≈ −20…−11 on the chain's spot. The index is held at source 15:15–15:29 and the close prints at 15:30. |
| **Proper fix** | The futures writer takes the spot from the same cycle's chain run (or the 15:30 close once printed), not its own index fetch, in the closing window; an offline test with a held-spot fixture and a mutant. |
| **Home** | Tracker §2.2 band B2 (with R5). |
| **Status** | **OPEN.** |

### TD-S100-NEW-2 (S3 priority) — Marketview renders loading states as values

| Field | Value |
|---|---|
| **Priority** | **S3.** A reader cannot tell "not loaded yet" from "zero" or "nothing wrong". |
| **Filed** | 2026-10-24 (Session 100; staging reads in Chrome) |
| **Component** | `meridian-connect`: Health error panels; the legacy pages' header strip |
| **Measured** | While its query is in flight the Health error panel shows "no errors"; the legacy strip shows `0 (0.00%)` and `iv not populated`. |
| **Proper fix** | A loading state (`—` or a skeleton) distinct from an empty result, per panel; board wording needs the operator's yes. |
| **Home** | Tracker §2.2 band B5. |
| **Status** | **OPEN.** |

### TD-S100-NEW-3 (S4 priority) — `NarrativeModal` and `AmbientTrajectory` are imported nowhere

| Field | Value |
|---|---|
| **Priority** | **S4.** Dead code that carries board wording; an edit there (S100-R D6 / D7) changes nothing a reader sees. |
| **Filed** | 2026-10-24 (Session 100; found applying S100-R) |
| **Component** | `meridian-connect` `NarrativeModal.tsx`, `AmbientTrajectory.tsx` |
| **Measured** | Found applying S100-R (`1aeb000`): neither component is imported anywhere in `src/`; D6 / D7 corrected in source only. |
| **Proper fix** | Delete both, or wire them in by an operator ruling; until then they are not cited as board text. |
| **Home** | Tracker §2.2 band B5. |
| **Status** | **OPEN.** |

### TD-S100-NEW-4 (S4 priority) — documents still cite the bare-IP board URL, which no longer serves the board

| Field | Value |
|---|---|
| **Priority** | **S4.** A reader following an old document reaches nothing; the live board is `https://marketview.meridianalpha.in` behind oauth2. |
| **Filed** | 2026-10-24 (Session 100) |
| **Component** | `http://13.63.27.85/…` board URLs in `docs/registers/MERDIAN_Enhancement_Register.md` (ENH-110), `docs/research/s86_split/split_plan.md` and other older documents (Deployment Topology §S89 records the change) |
| **Proper fix** | One doc pass replacing board URLs with the hostname (the IP stays where it means the host: Dhan whitelist, SSH). |
| **Home** | Tracker §2.2 band BD. |
| **Status** | **OPEN.** |

### TD-S100-NEW-5 (S4 priority) — `backfill_cas_close_from_daily.py` logs a Dhan plan lapse as `DATA_ERROR`

| Field | Value |
|---|---|
| **Priority** | **S4.** The same mislabel S100-M (b) fixed in the live writers, left in the 08:50 reconciler. |
| **Filed** | 2026-10-24 (Session 100) |
| **Component** | `backfill_cas_close_from_daily.py` (`exit_with_reason("DATA_ERROR", …)` sites) |
| **Measured** | Code read on `08b25a8` (2026-10-25): four `exit_with_reason("DATA_ERROR", …)` sites and no 806 / DH-902 test; `capture_cas_close.py` maps the lapse to `SUBSCRIPTION_LAPSED` since `418a75b`. |
| **Proper fix** | Reuse `_DHAN_SUBSCRIPTION_RE` before the `DATA_ERROR` exit; a cell and a mutant in `tests/test_subscription_lapsed.py`. |
| **Home** | Tracker §2.2 band B4. |
| **Status** | **OPEN.** |

### TD-S101-NEW-1 (S2 priority) — the ENH-133 writer loses a cycle when a view read times out (`57014`) on all three attempts

| Field | Value |
|---|---|
| **Priority** | **S2.** A lost `gex_cycle_history` row is unrecoverable (ADR-030 D2), and the pin path counts from it: `held_for_cycles` stays one low for as long as the leader holds. |
| **Filed** | 2026-10-26 (Session 101; Part C (a) read; ruled a new TD, S101-F — a different class from TD-S97-NEW-4) |
| **Component** | `write_gex_cycle_history_local.py` — the `S90_ENH133_WIRE` retry around `build_row` (3 attempts, 3 s apart, `57014` only; then `exit_with_reason("DATA_ERROR", …)`) and the view reads inside `build_row` |
| **Measured** | 2026-10-26 14:00 IST, NIFTY: `build_row` hit `57014` on all three attempts and lost the cycle — the one non-zero exit in the Part C (a) read (runner 87/87); `held_for_cycles` one low from 14:05. Which view read timed out is not yet known. |
| **Proper fix** | Identify the read (rank / concentration / max pain / pin-maxpain / walls / repriced flip) from the ledger error text or a timed replay of `build_row`, and apply ADR-021 A1 (scope the read) there; a check that the read finishes under the timeout, and a cell that a forced `57014` on every attempt still exits non-zero. |
| **Home** | Tracker §2.2 band B1. |
| **Status** | **OPEN.** |

### TD-S101-NEW-2 (S2 priority) — two live views ran a definition no file in `sql/` reproduced, and nothing checks live views against the registered files

| Field | Value |
|---|---|
| **Priority** | **S2.** A rebuild from `sql/` would have silently reverted the live pin and accel zones (ADR-025 D2 class), and the next unregistered change would go unseen the same way. |
| **Filed** | 2026-10-26 (Session 101; the MR-S1 O1 read; ruling S101-E) |
| **Component** | `v_gex_strike_pin_zone`, `v_gex_strike_accel_zone`; `sql/`; contract §8 |
| **Measured** | The live definitions walk on `COALESCE(<pin\|accel>.tau, 0.3)`, `tau_used` is never NULL, and `latest_run` is a LATERAL skip-scan over hard-coded `VALUES ('NIFTY'),('SENSEX')` — no file in `sql/` matched. Most likely S80, DDL never registered. Registered: C6 `02a06ec` (`sql/2026-10-26_s101_v_gex_strike_pin_zone_live_captured.sql`, 3523 / `89c9ac6aef9eb332ddd28f9062d0e21e`) and C7 `4a1d8e1` (`sql/2026-10-26_s101_v_gex_strike_accel_zone_live_captured.sql`, 3547 / `87a0691ef33ef5e08cbf315fd6511064`); each body reproduces the live length and md5, and a mutant differs. |
| **Proper fix** | Done for these two (C6, C7). Open: a standing check — the md5 of every live view's `pg_get_viewdef` against a registered list (seed: the MR-S1 O1 table and contract §8), run read-only on a schedule or at each doc-close; a mismatch names the view. |
| **Home** | Tracker §2.2 band B4. |
| **Status** | **OPEN** — registration DONE (C6, C7); the standing check OPEN. |

### TD-S101-NEW-3 (S2 priority) — `otm_oi_velocity` is NULL in every production `gamma_metrics` row

| Field | Value |
|---|---|
| **Priority** | **S2.** A published column that never carries a value; a reader cannot tell "no velocity" from "never computed". |
| **Filed** | 2026-10-26 (Session 101; the step 25 contract read) |
| **Component** | `merdian_compute/gamma.py` `compute_otm_oi_velocity`; `compute_gamma_metrics_local.py` `fetch_prior_gamma_metrics`, `upsert_gamma_metrics` |
| **Measured** | 0 of 313 production golden rows carry a value. **Code read on `4a1d8e1` (mechanism, not yet confirmed on data):** `compute_otm_oi_velocity` takes the prior run's OTM OI from `prior_row["raw"]["otm_oi_snapshot"]`; `upsert_gamma_metrics` writes that snapshot into `raw`, but `fetch_prior_gamma_metrics` selects only `straddle_atm,ts`, so `prior_row` has no `raw` and the function returns None on every run. |
| **Proper fix** | Confirm on data (`raw->>'otm_oi_snapshot'` non-NULL on stored rows); then select `raw` (or the snapshot alone) in the prior read, with a golden-day replay showing the column populated from the second cycle and a mutant. A behaviour change to a published column: replay before deploy. |
| **Home** | Tracker §2.2 band B3. |
| **Status** | **OPEN.** |

### TD-S101-NEW-4 (S3 priority) — `fetch_recent_max_gamma_strikes` and `fetch_prior_gamma_metrics` have no date bound

| Field | Value |
|---|---|
| **Priority** | **S3.** Whether the first cycle of a session should compare with the previous session is a design question no document answers. |
| **Filed** | 2026-10-26 (Session 101; read while packaging C2) |
| **Component** | `compute_gamma_metrics_local.py` — `fetch_prior_gamma_metrics` (straddle velocity), `fetch_recent_max_gamma_strikes` (the pin's sustained-time factor, last `n = 5` cycles) |
| **Measured** | Code read on `4a1d8e1`: both read the newest rows with `ts < current_ts` and no lower bound, so the first cycles of a session compare with the previous session's last cycles. |
| **Proper fix** | Rule: by design or defect. If defect, a session floor on both reads, with a golden-day replay of the first cycles before vs after. |
| **Home** | Tracker §2.2 band B3. |
| **Status** | **OPEN** — ruling owed. |

### TD-S101-NEW-5 (S3 priority) — the gamma and volatility math is still re-implemented outside `merdian_compute`

| Field | Value |
|---|---|
| **Priority** | **S3.** Drift risk: a fix in the package does not reach these copies, and a study run through them can disagree with production. |
| **Filed** | 2026-10-26 (Session 101; contract §9 item 4) |
| **Component** | Gamma: `backfill_gamma_metrics_to_main.py`, `measure_rate_sensitivity.py`, `replay/replay_compute_gamma_metrics.py`. Volatility: `replay/replay_compute_volatility_metrics.py`. |
| **Measured** | Recorded in S101, not changed; each re-implements math the writers now import from `merdian_compute`. |
| **Proper fix** | Each imports from `merdian_compute`; per file, a replay before vs after (equal) and a mutant in the package that moves its output. |
| **Home** | Tracker §2.2 band B4. |
| **Status** | **OPEN.** |

### TD-S101-NEW-6 (S3 priority) — `.gitignore:107` `_*.py` matches every `__init__.py`

| Field | Value |
|---|---|
| **Priority** | **S3.** A new package's `__init__.py` is silently left out of a commit; the S101 rehearsal stopped before `git add`, so the rule was first met on the box (§D.55.6). |
| **Filed** | 2026-10-26 (Session 101) |
| **Component** | `.gitignore` line 107 (`_*.py`, under `# S61 cleanup`) |
| **Measured** | `git check-ignore --no-index -v merdian_compute/__init__.py` → `.gitignore:107:_*.py` (re-read at the S101 doc-close build on `4a1d8e1`). |
| **Proper fix** | Narrow the pattern to what S61 meant (or add `!__init__.py`); `git check-ignore` on every tracked `__init__.py` returns nothing, and on one S61 target still returns the rule. |
| **Home** | Tracker §2.2 band BD. |
| **Status** | **OPEN.** |

### TD-S101-NEW-7 (S4 priority) — from Python 3.12, `sum()` over floats is compensated, so `net_gex` and concentration move in the last bits

| Field | Value |
|---|---|
| **Priority** | **S4.** About 1e-15 relative; no board figure changes, but a bit-for-bit parity claim between production and retail fails on ≥ 3.12. |
| **Filed** | 2026-10-26 (Session 101; contract §10) |
| **Component** | `merdian_compute.gamma` (float sums in `net_gex`, `gamma_concentration`); production runs Python 3.10 |
| **Measured** | 474 of 486 golden runs differ in the last one or two bits on ≥ 3.12; step 25 compares at 1e-9 and passes on both (contract §10). |
| **Proper fix** | Retail pins 3.10 or 3.11 (contract §10), or both sides move to `math.fsum` — a behaviour change, replay first. |
| **Home** | Tracker §2.2 band BR. |
| **Status** | **OPEN.** |

### TD-S101-NEW-8 (S3 priority) — retail cannot reproduce every board input from `merdian_compute` alone (contract §9)

| Field | Value |
|---|---|
| **Priority** | **S3.** Stated in the contract so retail does not assume it; each gap is a retail build item or a scope ruling. |
| **Filed** | 2026-10-26 (Session 101; contract §9) |
| **Component** | `docs/interfaces/retail_compute_contract.md` §9 items 1–3 |
| **Measured** | Not packaged: the session gate and reconciler; the VIX fields of `volatility_snapshots` (history-dependent, still in the writer); `index_futures_snapshots` for the repriced flip, the `merdian_parameters` rows with a `get_parameter_num` SQL function, and a `trading_calendar` for the calendar predicate. |
| **Proper fix** | Per item: package it, specify it for retail to re-create, or rule it out of retail scope; contract §9 updated as each is settled. |
| **Home** | Tracker §2.2 band BR. |
| **Status** | **OPEN.** |

### TD-S101-NEW-9 (S4 priority) — superseded view files stay in `sql/` beside the registered one

| Field | Value |
|---|---|
| **Priority** | **S4.** A reader picking "the newest file" or a marker match gets a definition that is not live (the §D.55.14 failure). |
| **Filed** | 2026-10-26 (Session 101; the O1 read) |
| **Component** | `sql/` — `v_max_pain_by_strike` (2 of its 3 files superseded), `v_gex_strike_pin_zone` (3 older files), `v_gex_strike_accel_zone` (3 older files) |
| **Measured** | O1 read 10-26: the live definition is reproduced by one file per view (contract §8); the others are older. |
| **Proper fix** | A header line in each superseded file naming the registered one, or a move to an archive folder; the standing md5 check (TD-S101-NEW-2) names the live file. |
| **Home** | Tracker §2.2 band BD. |
| **Status** | **OPEN.** |

### TD-S101-NEW-10 (S2 priority) — port 22 is open to 0.0.0.0/0 on the production box

| Field | Value |
|---|---|
| **Priority** | **S2 (security).** SSH reachable from any address; operator access is through SSM. |
| **Filed** | 2026-10-26 (Session 101) |
| **Component** | The security group attached to `i-0878c118835386ec2` |
| **Measured** | Inbound 22 from `0.0.0.0/0` (S101 read). |
| **Proper fix** | Narrow (operator IP, or remove if SSM covers every use); read the attached security group by the IMDSv2 query first (S39, as TD-S89-NEW-4). Operator action. |
| **Home** | Tracker §2.2 band BS. |
| **Status** | **OPEN** — operator action. |

### TD-S101-NEW-11 (S3 priority) — the four-way check had no Local HEAD line, and Local trailed `main` by a session

| Field | Value |
|---|---|
| **Priority** | **S3.** Rule 2's preflight compares Local with AWS; a Local tree a session behind passes any check that does not name its HEAD. |
| **Filed** | 2026-10-26 (Session 101) |
| **Component** | The four-way check (box route, S99-A); Local tree `C:\GammaEnginePython\` |
| **Measured** | Before the S101 pull, Local was at `b29f320` (S100) while `main` was `7b91d1a`. |
| **Proper fix** | The four-way check states "Local HEAD = `<sha>`" (`git rev-parse HEAD` in `C:\GammaEnginePython\`) as its own line, with `git diff --stat <sha>` = 0. |
| **Home** | Tracker §2.2 band BD. |
| **Status** | **OPEN.** |

### TD-S101-NEW-12 (S3 priority) — unprivileged `journalctl` reads of the alert units look clean

| Field | Value |
|---|---|
| **Priority** | **S3.** A read that returns `-- No entries --` for lack of permission is a check that cannot fail (Rule 0). |
| **Filed** | 2026-10-26 (Session 101; §D.55.19) |
| **Component** | Runbooks and session prompts that read the alert journal |
| **Measured** | The S101 wsfeed alert read without `sudo` returned `-- No entries --`; re-read with `sudo`. |
| **Proper fix** | Every runbook / prompt alert read uses `sudo journalctl`; a grep of `docs/runbooks/` for a bare `journalctl` returns nothing. |
| **Home** | Tracker §2.2 band BD. |
| **Status** | **OPEN.** |

### TD-S101-NEW-13 (S3 priority) — Health OVERALL reads DEGRADED all session on a healthy fleet

| Field | Value |
|---|---|
| **Priority** | **S3.** A health summary that is amber every day carries no signal; S100-M (a)'s "OVERALL green unless a tracked writer is stale" cannot hold. |
| **Filed** | 2026-10-27 (Session 101; board read 10:20 IST) |
| **Component** | `meridian-connect` Health page (live bundle `index-BFOk56iL.js`): the token tile is green iff `http_status == 200 && age < 30`, age in minutes (`Tf(ts) = (now − ts) / 6e4`) |
| **Measured** | 2026-10-27 10:20 IST: fleet 14/14 current, OVERALL DEGRADED; token 2.5 h old → amber. The token refreshes once a day, so OVERALL is amber from ~30 min after the refresh until the next one. |
| **Proper fix** | A threshold on the token's validity window (e.g. < 24 h) or expiry-based, in meridian-connect; a board change needs the operator's yes. |
| **Home** | Tracker §2.2 band B5 (ruling row). |
| **Status** | **OPEN** — ruling owed. |

### TD-S101-NEW-14 (S3 priority) — Context IV SKEW is blank for NIFTY on expiry day

| Field | Value |
|---|---|
| **Priority** | **S3.** The card shows nothing on the day the front leg matters most. |
| **Filed** | 2026-10-27 (Session 101; board read 10:20 IST) |
| **Component** | `meridian-connect` Context IV-skew card; view `leg_skew_98` (S100-P class) |
| **Measured** | 2026-10-27 10:20 IST (NIFTY front leg 0 DTE): `—` after > 10 s; SENSEX (2 DTE) showed `+2.0 vol pts @ K98 72,000 · front leg · from view`. Likely the view has no 0-DTE front row, or the card does not fall back to the next leg — not yet read. |
| **Proper fix** | Read the view on the next NIFTY expiry before ruling; then fall back to the next leg, or label the 0-DTE state. A board change needs the operator's yes. |
| **Home** | Tracker §2.2 band B5 (ruling row). |
| **Status** | **OPEN** — ruling owed. |

### TD-S101-NEW-15 (S3 priority) — after the expiry-day close, the NIFTY board shows the expired leg's last-cycle gamma as the day's closing structure, overnight

| Field | Value |
|---|---|
| **Priority** | **S3.** Arithmetically expected at T ≈ 0, but presented as the closing structure until the next pre-open. |
| **Filed** | 2026-10-27 (Session 101; board close read 15:49 IST) |
| **Component** | Marketview Board (NIFTY) after the 15:40 cycle on expiry day; the stored 15:40 rows of the expiring leg |
| **Measured** | 2026-10-27 15:49 IST: NET Γ −2,007.6L Cr, short γ, −1.00 of gross (in session 10:19: +8.4L, +0.06); PIN 22,750 at 99.0 % of gross, lead 98.5 pts; corridor `22,750–22,750 · 0.00 % wide · below put wall`; IV `—`; priced move `no run`. The 15:40 run on the expiring leg is at T ≈ 0, so ATM gamma dominates (22,750 −1,987.8L of the total). Cleared by the 10-28 08:30 run. Not caused by S101 (gamma math byte-identical, DEP-3). |
| **Proper fix** | Rule: after the expiry-day close the board rolls to the next leg, or labels the expired-leg state. Check the stored 15:40 rows before ruling. |
| **Home** | Tracker §2.2 band B2 (ruling row). |
| **Status** | **OPEN** — ruling owed. |

### TD-S101-NEW-16 (S4 priority) — `eod.log` lines carry no timestamps

| Field | Value |
|---|---|
| **Priority** | **S4.** "Did today's run happen" needs the file's mtime; a grep cannot date its own lines (§D.55.24). |
| **Filed** | 2026-10-27 (Session 101; the R19 read) |
| **Component** | The EOD ingest and the daily breadth builder's summaries in `eod.log` |
| **Measured** | 2026-10-27 17:52 IST: the builder / ingest summaries could not be tied to a run date; the discriminating read was the mtime (2026-10-27 11:35:42 box clock, UTC). |
| **Proper fix** | One dated header line per run (IST date and time, run id). |
| **Home** | Tracker §2.2 band B4. |
| **Status** | **OPEN.** |

### TD-S101-NEW-17 (S4 priority) — one ticker returns `DH-905` (bad parameters) on the EOD historical call

| Field | Value |
|---|---|
| **Priority** | **S4.** One security short in a run; not a token failure. |
| **Filed** | 2026-10-27 (Session 101; the R19 read) |
| **Component** | The EOD historical ingest; `dhan_scrip_map` |
| **Measured** | One run in `eod.log` ends `PARTIAL_OK`, `Failures 1`, on a `DH-905` for one security. |
| **Proper fix** | Identify the security id from the failure sample; likely a stale or malformed `dhan_scrip_map` row (TD-S90-NEW-1 class); remap or deactivate. |
| **Home** | Tracker §2.2 band B4. |
| **Status** | **OPEN.** |

### S101 status changes to existing entries (doc-close run in Session 102; v5 Rule 3: one paragraph, no body edits)

Rulings S101-A…H (`docs/research/s92_parity/rulings_s101.md`). Ledger: `TDs_NEW=17` (TD-S101-NEW-1…17) ·
`TDs_CLOSED=5` (below; blocks moved to the end of `tech_debt_history.md`'s entries, unedited).
**TD-S97-NEW-4, TD-S82-NEW-1, TD-S82-NEW-2 → CLOSED** (S101-F, 10-26 17:23 IST) on the Part C (a) read of 2026-10-26: γ
median lag 12.6 / 20.3 s; 0 later-date rows; 3 closing rows per symbol; runner 87/87; one `[CYCLE WAIT]` line per cycle,
0 missing. The day's one non-zero exit (14:00, the ENH-133 writer's `57014`) is a different class: TD-S101-NEW-1.
TD-S97-NEW-4's part (b) (`actual_writes {}`), open at the S100 close, is not covered by that read; it rides with the
tracker §2.2 B1 ledger row. **TD-S97-NEW-5 → CLOSED** on the 10-26 09:09 probe (all OK; `418a75b` labels a lapse).
**TD-S80-NEW-17 → CLOSED:** on 10-26 the wsfeed started 03:40:01–03:40:03 UTC by its timer, no restarts, the `sudo` alert
journal empty. **TD-S97-NEW-8, -9, -10** (closed S100) confirmed live 10-26: S99-H PASS in full. **TD-S100-NEW-1 → OPEN,
re-measured 2026-10-27** (board FUT · BASIS sub-line against the S100-R close, 15:40): NIFTY `vs spot 22,760.8 @ 15:40`
against the close 22,749.75 (Δ 11.05); SENSEX `vs spot 73,556.3 @ 15:40` against 73,598.67 (Δ 42.37) — the futures rows
still carry a non-close spot at 15:40 on both symbols; on 10-28 pre-open the 16:00 row carried the close (22,749.8), as
S100 predicted. **TD-S100-NEW-2:** extends to Home — first paint 10-27 10:19 read `prev close missing` / PIN `no run` / OI
`no max pain` before the data loaded; no new TD. **TD-S83-NEW-2:** S101's finding "the volatility writer's `dte` uses the
wall clock" (contract §9 item 2, "filed S101") is this entry's defect 2, still present at
`compute_volatility_metrics_local.py:557–558` on `4a1d8e1`; not re-filed. **Not a TD:** WCB publishing from pre-open
ticks (first row 09:11 on 10-26) is a design question — a tracker §2.2 ruling row. **Tracker rows:** R1 + R41 DONE; R2 +
R21 live check PASS; R4's two TDs closed; R19 builder PASS on its input (10-26 / 10-27 owed to the 10-28 run).

### S100 status changes to existing entries (v5 Rule 3: one paragraph, no body edits)

Rulings S100-C…S, Q.1 (`docs/research/s92_parity/rulings_s100.md`). Ledger: `TDs_NEW=6` (TD-S100-NEW-1…6; -6 filed
closed) · `TDs_CLOSED=19` (below; blocks moved to the end of `tech_debt_history.md`'s entries, unedited).
**TD-S97-NEW-3 → CLOSED** `3070682`: an unfinished ledger row started > 6 min ago today → CRITICAL under its own key;
offline step 16. **TD-S81-NEW-11 → CLOSED** `f213d22`: the chain ingest retries a Dhan 5xx twice; step 21.
**TD-S90-NEW-14 → CLOSED** by S100-H: the 12 active `pg_cron` jobs calling the retired Edge Functions are inactive
(`cron.alter_job(active := false)`; the `equity_eod` cursor writer was jobid 37); deleting the three functions and the
`x-cron-secret` is a later ruling (tracker §2.2 BS1); a 15-character prefix of that secret reached the chat in a log read
and is treated as disclosed. **TD-S97-NEW-14, TD-S81-NEW-7, TD-S41-NEW-1 → CLOSED** by the R22 operator SQL (verification
15 / 15 / 0 / 12; record in `sql/`); 2026-11-08 stays closed (S100-O). **TD-S97-NEW-11 → CLOSED** `9c5f50c`: the daily
breadth builder fills a complete EOD date a later date overtook; 10-08 1,377 and 10-15 1,373 rows backfilled; no October
date short; step 22. **TD-S97-NEW-12 → CLOSED:** 10-21 written. **TD-S81-NEW-12 → CLOSED:** `compute_basis_context_local.py`
exits 0 since S92-B. **TD-S97-NEW-15 → CLOSED** by S100-J: `data_contamination_ranges.symbols text[]` with its CHECK;
`SENSEX-CHAIN-OI-VOL0-2026-09-25` = `{SENSEX}`, the other three NULL; the Rule 13 test is in `CLAUDE.md`.
**TD-S94-NEW-1 and TD-S81-NEW-16 → CLOSED** by S100-K: `merdian_ro_select` on the 51 public RLS tables no SELECT / ALL
policy reached (56 such policies after; the DO block's audit assert 0; probes 0 → 1000 rows) — the one catalog test both
entries name; a guard for tables created later is not built. **TD-S97-NEW-16 → CLOSED** by S100-L: newest 3 `.bak-<sha>`
plus every `PRE_*`; the rule is in the promote step of `docs/lovable_prompts/s92/README.md`. **TD-S97-NEW-21 → CLOSED:**
(a) Health untracks `build_ict_htf_zones.py`, live `1072593` (TD-S77-NEW-14 / TD-017 stay in the ICT stream); (b)
`SUBSCRIPTION_LAPSED`, `418a75b` (chain, spot 1m, CAS close, probe, `core.execution_log` 11 → 12, the daemon's alert
set); (c) OVERALL CRITICAL display only. The 10-21 counts were 360 / 174 / 1 over the session (the entry's 286 / 126 was a
24 h window); the reconciler's own mislabel is TD-S100-NEW-5. **TD-S82-NEW-4 → CLOSED as decided** (S100-O): Muhurat is
not captured; ADR-020 amended; the engine and gate docstrings corrected in this close. **TD-S80-NEW-19 → CLOSED,
superseded by v5 Rule 3** (S100-O); its one legacy instance, TD-S70-NEW-5 in the history file, recorded.
**TD-S76-NEW-17 → CLOSED** (S100-O): ADR-004 §15 already carries the measured, dated counts (19,573 / 19,571, 2026-09-10)
and not 19,432 (read on `08b25a8`); a dated note added. **TD-S90-NEW-12 → CLOSED** on the reconciliation read: capture
SUCCESS every trading day 10-07 → 10-23 except the holiday 10-20 and the lapse 10-21; `corrected = 0` on every counted
day; 10-21 filled 10-22 (S98-D). **TD-S97-NEW-17 → CLOSED** by S100-R B (D1–D7, live `1aeb000`; D6 / D7 are in unimported
components, TD-S100-NEW-3). **Fix deployed, closes on the Monday 2026-10-26 read:** **TD-S97-NEW-5** (the 09:09 probe pages
a lapse; `418a75b` labels it) · **TD-S80-NEW-17** (`merdian-wsfeed-retry.timer`, `9e24792`). **Part done:**
**TD-S97-NEW-6** — the feed restarts on its own; the daily manual Kite refresh stays a single point (operator decision).
**TD-S81-NEW-1** — (a) unanswerable: the log window is 7 days, so the old token is treated as disclosed; (b) stays with
BS-1. **Tracker rows, not TDs:** R3, R4, R9, R19, R22, R23, R24, R34 / R35, R14 / R33 DONE; R40 DONE with the overlap
deferred (S100-I); R42 DONE `b29f320`; **R43 / R44 OBSOLETE** (S100-D: the alert daemon's last heartbeat 2026-06-11, the
daily audit's last row 2026-06-07; a BO row replaces them); R5 label part and R17 step 1 DONE; R7, R8, R10, R18 read
(`docs/research/s100/B3_reads_2026-10-24.md`). **Notes:** R7 — on expiry eve the 15:40 snapshot is not the exchange's
final EOD OI (10-13 pre-open differs by up to −7.36 % on the expiring legs; pre-open-anchored readers unaffected);
10-12 has no `dhan_idx_i` pre-open row 09:00–09:15.

### S98 + S99 status changes to existing entries (doc-close run in Session 100; v5 Rule 3: one paragraph, no body edits)

Rulings S98-A…E.1 and S99-A…I; this close's own S100-A (split) and S100-B (R38–R49 homed in §2.2). Ledger:
`TDs_NEW=1` (TD-S99-NEW-1) · `TDs_CLOSED=3` (TD-S97-NEW-8, -9, -10).
**TD-S97-NEW-4 → ROOT CAUSE FOUND, FIX (a) DEPLOYED `2edd25f`.** R1a: the first cycle of each session wrote the previous
session's 15:40 γ row — 39 rows per symbol since 08-24, stamped 15:40 IST and written at the next 08:30 / 08:40 (39 of 41
days; control 0 same-day). R41: every γ cycle computed the previous chain run (2026-10-23: 76/76 rows per symbol,
`created_at − ts` 303–318 s). S98-B: the runner waits up to 120 s for its own cycle's run and exits 1
`SKIPPED_NO_INPUT` without one; closing cycles 15:30 / 15:35 / 15:40 IST (crontab line 69). Closes, with TD-S82-NEW-1 and
-2, on the Monday 2026-10-26 live PASS. Part (b) (`actual_writes {}`) stays open. **TD-S97-NEW-8, -9, -10 → CLOSED** by
`3706435` (S99-H) and S99-I: the mechanism, measured 2026-10-24, was the first cycle upserting onto the previous session's
last breadth `ts` (the 10-20 rows were written 10-21 08:31 IST); the writer now writes nothing on a stale `ts` or no priced
constituent; the no-symbol cron line is removed; the 12 zero rows are deleted (`zero_rows_left 0`). Residual for the Monday
read: no row on Friday's 15:24 `ts` at 08:31; a real row at 15:40. Blocks moved to `tech_debt_history.md`.
**TD-S97-NEW-2, -7, -20 → confirmed live 2026-10-23:** monitor 0 "not firing", 0 RECOVERED, 422 "Orchestrator OK";
contract check no `[SENT]` for spot all day and one `[CLEAR] contract_spot_stale … episode since 2026-10-09T03:04:03 closed`.
**TD-S97-NEW-12 → 10-21 written** (read 2026-10-23 17:02 IST); `breadth_indicators_daily` 31 rows short of `equity_eod`
for that date — re-read after the next EOD before any backfill (tracker §2.2 R19). **TD-S97-NEW-13 → RE-SCOPED** (S98-D
amended, no write): the 10-21 close exists (`dhan_charts_historical`, 15:29 IST, NIFTY 22811.35 / SENSEX 73709.69, written
10-22 08:50 IST by `backfill_cas_close_from_daily.py --auto-correct`); the defect is the board's client-side prev-close
read in `meridian-connect`, not data (§2.2 R20). **TD-S97-NEW-6 / TD-S80-NEW-17 → evidence:** the wsfeed preflight on 10-15
and 10-19 tried three times in ~23 s (03:40:03–03:40:26 UTC) and never again that session (§2.2 R4). **TD-S94-NEW-4** (closed
in the S99 paragraph) — measured 2026-10-23 04:51 IST: `option_chain_snapshots` starts 2026-08-24 10:00:05 UTC, its first
row, so nothing has been pruned. **TD-S92-NEW-5** (closed in the S99 paragraph) — confirmed S98-C: the 10-02 row reads
`false / Mahatma Gandhi Jayanti`, written by the S96-J backfill; the Rule 13 range `HOLIDAY-FROZEN-CHAIN-2026-10-02` was
inserted (registry 4, new 1). **TD-S89-NEW-1's Corroboration row** ("`gamma_metrics` has no rows at all for 10-02") —
superseded by R1a: two FULL rows stamped 10-02 15:40 IST were written 10-05 08:40 IST by the first-cycle reuse.
**S98 rows R38–R49 (S100-B):** R38–R44 are tracker §2.2 rows already; **R48** (`run_ingest.sh` `set -e` makes `rc=$?`
unreachable) and **R49** (the monitor alarms on `exit_code` alone, so any skip that exits 1 pages CRITICAL) added to §2.2
B1; **R45** closed inside `2edd25f` (the runner's docstring schedule); **R46** recorded, no TD (one missing symbol costs
the full 120 s; 120 + ~132 s < 300 s); **R47** verified 2026-10-23 18:05 IST (`chk_exit_reason_valid` and
`VALID_EXIT_REASONS` both list the same 11 members; one constraint references `exit_reason`). **Pass-2 misses (found at the
split, S100):** **TD-S82-NEW-4** (Status "OPEN — engine unfixed by decision"; its heading quotes "CLOSED"),
**TD-S80-NEW-19** (Status "OPEN — part (b) is the item"; its heading quotes "RESOLVED"), **TD-S76-NEW-17** (Status
"PARTIALLY RESOLVED"), **TD-S90-NEW-12** (Status "FIXED, NOT CLOSED") — pass 2's open test excluded any entry whose
heading or Status carried a closing word, so these four were neither counted nor homed; they stay in this file and are
one §2.2 B4 row ("Pass-2 misses") until a disposition is ruled.

### S99 status changes to existing entries (v5 Rule 3: one paragraph per class, no body edits)

Ruled S99-C / S99-D / S99-G (`docs/research/s92_parity/rulings_s99.md`); the reasoning per entry is in `docs/research/s99/reconciliation_pass2.md` §3. **Every open entry not named below is a row in tracker §2.2** (`docs/registers/agentic_layer_roadmap_S90.md`), the single list; the entry here keeps its text. Ledger: `TDs_NEW=0` · `TDs_CLOSED=46`.

**CLOSED (46):** **TD-S96-NEW-1** — CLOSED in S97 footer (`2edd25f`:286, S97-A, live 04fcd05); header not updated · **TD-S96-NEW-4** — RECORDED, no change (S97-C footer :290) — nothing owed · **TD-S95-NEW-2** — CLOSED S97-E (footer, `2edd25f`:293) · **TD-S94-NEW-4** — X1 — measured intact 10-23 04:51 IST (no pruning since 08-24); P4 §3 binds future changes · **TD-S93-NEW-2** — RESOLVED by ruling S95-F (footer, `2edd25f`:382) · **TD-S93-NEW-3** — outcome recorded in p1/README + result doc (status row) — nothing owed · **TD-S92-NEW-5** — closed by S96-J backfill; confirmed S98-C 06:33 IST · **TD-S91-NEW-13** — CLOSED S97 footer (`2edd25f`:297, 10-20 log 84/84 holiday gate) · **TD-S91-NEW-14** — FIXED 0965755 (status row) · **TD-S91-NEW-15** — basis site verified 12/12 exit 0 (S92-B, e0b9d03); S98-E.1 keeps SKIPPED_NO_INPUT semantics · **TD-S91-NEW-1** — VERIFIED 2026-10-09 78/78, 77/77 (status row) · **TD-S91-NEW-7** — FIX VERIFIED 2026-10-07, rule 23 codified · **TD-S91-NEW-11** — ruled S91-B = CLAUDE.md rule 24; compliance held S92–S99 · **TD-S90-NEW-2** — CLOSED 2026-10-07 (S90 footer :7760) · **TD-S90-NEW-11** — CLOSED S97-L (footer, `2edd25f`:294) · **TD-S89-NEW-1** — MITIGATED S90; its close test (10-20 with no chain rows) passed per TD-S91-NEW-13 log — residual = R37 (done S98-C) · **TD-S86-NEW-9** — RULED 2026-10-03 (fb92d63) · **TD-S80-NEW-5** — closed by the S80 doc-close (status row) · **TD-S80-NEW-11** — retention superseded: TD-S94-NEW-4 measured no pruning since 08-24 · **TD-S80-NEW-13** — closed by the S80 CURRENT.md rewrite (status row) · **TD-S79-NEW-13** — COMMENT ON VIEW names the scalars apart (dc2e6b5, S81) · **TD-S73-NEW-11** — RESOLVED S73 (status row) · **TD-S73-NEW-3** — retention misread class — superseded by TD-S94-NEW-4 measurement · **TD-S72-NEW-5** — fix 866face deployed S72; floor verification owed since 09-07 — confirm with one log read · **TD-S70-NEW-7** — untracked by fdc1ad6 (2026-09-05) · **TD-S69-NEW-4** — CLOSED S70 75de1bb (footer, `2edd25f`:7717) · **TD-S69-NEW-8** — CLOSED S70 (footer, `2edd25f`:7733) · **TD-S66-NEW-5** — REFRAMED NOT A BUG (S67); residual carried by TD-S90-NEW-14 · **TD-S59-NEW-1** — FIX APPLIED + GUARDED 06-24; live-verify owed since June — breadth on R5/R11 reads since; confirm with one directional-day read · **TD-S57-NEW-1** — CLOSED-VERIFIED S58 close (footer, `2edd25f`:7675) · **TD-S57-NEW-2** — CLOSED-VERIFIED S58 close (footer, `2edd25f`:7675, f922524) · **TD-S55-NEW-1** — filed+closed S55 (footer, `2edd25f`:7667) · **TD-S54-NEW-1** — closed S55 (1889604; footer :7667) · **TD-S54-NEW-3** — closed S55 (5b92433; footer :7667) · **TD-S54-NEW-4** — closed S55 (c2910e8 + eb052d0; footer :7667) · **TD-S53-NEW-6** — parse-fixed S55 (66f8252), contract resolution S56 (8eae351) · **TD-S48-NEW-1** — CLOSED-DECISION S57 (footer, `2edd25f`:7672) · **TD-S41-NEW-2** — downgraded S55: AWS-primary refresh confirmed; residual staleness monitor → R4 · **TD-S37-01** — closed S40 (6d07d24: view-tau runtime get_parameter) · **TD-S36-NEW-4** — resolved S55 (duration_ms bigint; footer :7667) · **TD-NEW-H** — superseded S55 (footer, `2edd25f`:7667) · **TD-081** — closed downstream at S58 close (footer, `2edd25f`:7675) · **TD-080** — S1 RECURRING → ENH-99 capture-layer resilience SHIPPED S36 (e318ec2); residual 429 behaviour = TD-S81-NEW-11 · **TD-019** — closed S9/S10 (e36a9ef "TD-019 docs -- closure") · **TD-030** — closed S11 (9261ee2 "TD-030/031 closed") · **TD-031** — closed S11 (9261ee2).

**CLOSE on the S98-B live PASS, 2026-10-26 (3):** **TD-S97-NEW-4** · **TD-S82-NEW-1** · **TD-S82-NEW-2** — S98-B deployed `2edd25f`, crontab line 70 added 2026-10-23.

**DUPLICATE — the named item carries the work (37):** **TD-S91-NEW-16** → TD-S90-NEW-14 · **TD-S91-NEW-18** → R5 · **TD-S91-NEW-3** → R4 · **TD-S90-NEW-13** → R5 · **TD-S90-NEW-6** → R11 · **TD-S90-NEW-7** → R11 · **TD-S89-NEW-2** → TD-S90-NEW-8 · **TD-S88-NEW-1** → R18 · **TD-S87-NEW-3** → TD-S83-NEW-6 · **TD-S86-NEW-7** → TD-S76-NEW-16 · **TD-S81-NEW-9** → R11 · **TD-S81-NEW-13** → TD-S97-NEW-8 · **TD-S80-NEW-9** → R41 · **TD-S79-NEW-3** → TD-S81-NEW-5 · **TD-S79-NEW-23** → TD-S76-NEW-16 · **TD-S78-NEW-8** → R41 · **TD-S77-NEW-5** → TD-S80-NEW-4 · **TD-S77-NEW-14** → R9 · **TD-S75-NEW-3** → R26 · **TD-S74-NEW-3** → R5 · **TD-S74-NEW-5** → R5 · **TD-S72-NEW-11** → TD-S80-NEW-4 · **TD-S71-NEW-2** → TD-S76-NEW-16 · **TD-S71-NEW-10** → R4 · **TD-S69-NEW-6** → R4 · **TD-S61-NEW-3** → TD-S76-NEW-16 · **TD-S60-NEW-3** → TD-S90-NEW-3 · **TD-S54-NEW-2** → R38 · **TD-S41-NEW-3** → TD-S71-NEW-1 · **TD-S37-03** → TD-S81-NEW-16 · **TD-NEW-D** → TD-S91-NEW-4 · **TD-NEW-7** → R4 · **TD-001** → TD-S71-NEW-1 · **TD-010** → TD-S80-NEW-4 · **TD-017** → R9 · **TD-023** → TD-S77-NEW-8 · **TD-026** → TD-S80-NEW-4. (R-numbers are pass 1 rows, homed in tracker §2.2.)

**OBSOLETE (15):** **TD-S81-NEW-14** — ADR-025 stage-2 gate — parity CLOSED (Amendment D); retry telemetry is R1.4 (agentic Stage 1) · **TD-S80-NEW-2** — parity spec claims — parity CLOSED (ADR-025 Amendment D) · **TD-S79-NEW-10** — S74/S79 containment figures — neither quotable, no consumer · **TD-S79-NEW-22** — "parity achieved" criterion — answered by ADR-025 Amendment D · **TD-S76-NEW-14** — Topology §7.2 Windows task table — Windows host retired (S70: 100% AWS) · **TD-S46-NEW-1** — Breeze backfill mechanism — Breeze unused (TD-S90-NEW-10) · **TD-S38-NEW-1** — Windows Task Scheduler quirk — host retired · **TD-S37-02** — §F1 dealer-vs-positioning split — superseded by P2 (REGIME-DEPENDENT) + P5/P7 · **TD-S36-NEW-2** — Windows token task instrumentation — host retired · **TD-S36-NEW-3** — pre-S29 token incidents invisible — historical · **TD-S35-NEW-3** — Breeze SENSEX symbology — Breeze unused · **TD-062** — Windows Task Scheduler Saturday runs — host retired · **TD-004** — BFO contract CSV 2025-06 — one-off historical file · **TD-006** — run_market_tape_1m disabled (Windows ACCESS_VIOLATION) — host retired · **TD-016** — Dhan TOTP Windows task — host retired.

**PARKED — signal / ICT stream (68; trigger: after agentic, when the operator reopens the signal stream, S99-G; ADR-019 rules out retiring on a verdict):** TD-S79-NEW-20 · TD-S77-NEW-1 · TD-S77-NEW-2 · TD-S77-NEW-3 · TD-S77-NEW-6 · TD-S77-NEW-9 · TD-S77-NEW-10 · TD-S77-NEW-11 · TD-S77-NEW-12 · TD-S77-NEW-13 · TD-S77-NEW-15 · TD-S76-NEW-3 · TD-S76-NEW-4 · TD-S76-NEW-5 · TD-S76-NEW-6 · TD-S76-NEW-7 · TD-S76-NEW-8 · TD-S76-NEW-9 · TD-S76-NEW-10 · TD-S76-NEW-13 · TD-S76-NEW-18 · TD-S76-NEW-19 · TD-S76-NEW-20 · TD-S74-NEW-2 · TD-S71-NEW-6 · TD-S71-NEW-7 · TD-S71-NEW-9 · TD-S70-NEW-8 · TD-S69-NEW-5 · TD-S40-NEW-3 · TD-S39-NEW-2 · TD-S38-NEW-3 · TD-S35-NEW-4 · TD-S33-NEW-1 · TD-S33-NEW-2 · TD-S33-NEW-3 · TD-S33-NEW-4 · TD-S31B-NEW-1 · TD-S30-NEW-4 · TD-S30-NEW-5 · TD-S30-NEW-6 · TD-S30-NEW-7 · TD-098 · TD-096 · TD-095 · TD-078 · TD-077 · TD-076 · TD-075 · TD-074 · TD-073 · TD-069 · TD-067 · TD-018 · TD-032 · TD-033 · TD-035 · TD-036 · TD-039 · TD-049 · TD-050 · TD-051 · TD-052 · TD-054 · TD-055 · TD-056 · TD-057 · TD-059.

**PARKED — history and backfill (22; trigger: a study needs that window):** TD-S81-NEW-19 · TD-S80-NEW-8 · TD-S78-NEW-4 · TD-S78-NEW-5 · TD-S78-NEW-6 · TD-S76-NEW-1 · TD-S73-NEW-4 · TD-S73-NEW-5 · TD-S72-NEW-10 · TD-S70-NEW-9 · TD-S62-NEW-2 · TD-NEW-14 · TD-S36-NEW-1 · TD-S35-NEW-1 · TD-S34-NEW-4 · TD-094 · TD-087 · TD-002 · TD-024 · TD-029 · TD-034 · TD-038.

**PARKED — trigger named (10):** **TD-S96-NEW-3** — X1 watch — trigger: P3b sweep runtime > budget · **TD-S90-NEW-4** — purge named (jobid 46), ticks frozen; trigger: a tick-based replay needs >10 days · **TD-S89-NEW-3** — r_sess vs r_eff — immaterial to L7/L8; trigger: any use of r_sess as a rate · **TD-S87-NEW-1** — re-rated S3 and PARKED by operator (no orders ever); trigger: any order path · **TD-S81-NEW-10** — ruled "do not fix now"; trigger: a manual reader used on depth-2 data · **TD-S80-NEW-3** — max_pain_in_pin_band undiscriminating; trigger: any read of it · **TD-S79-NEW-2** — iv_floor_min never bound; trigger: band re-sweep · **TD-S79-NEW-4** — watch only · **TD-S79-NEW-19** — 08-24/25 unjoinable; trigger: a study sample starting 08-24 · **TD-S74-NEW-1** — 59-finding coupling audit pointer; trigger: each finding filed on its own when touched.

**PARKED — agentic MERIDIAN on hold (9, S99-D):** TD-S91-NEW-8 · TD-S91-NEW-9 · TD-S91-NEW-10 · TD-S87-NEW-4 · TD-S86-NEW-6 · TD-S85-NEW-1 · TD-S85-NEW-2 · TD-S85-NEW-3 · TD-S82-NEW-3.


### S97 status changes to existing entries (v5 Rule 3: one paragraph, no body edits)

**TD-S96-NEW-1 → CLOSED** (S97-A): the "dealer" wording is gone from the ∂Δ/∂t and ∂Δ/∂σ captions and drawers, live in
`04fcd05` (bundle `index-BrWRk1OP.js`), staging and live reads PASS (`docs/lovable_prompts/s97/lovable_prompt_s97_dealer_wording.md`).
**TD-S96-NEW-2 → MITIGATED** (S97-F / S97-G): `idx_gss_ts` plus `ts` statistics target 1000 take the 10-09 day estimate
from 1 to 17,381 against 19,198 actual; residual — windows past the latest ANALYZE (autoanalyze ~every 10 trading days),
a per-table autoanalyze threshold is the candidate; P3b keeps `enable_nestloop = off`. **TD-S96-NEW-4 → RECORDED, no
change** (S97-C). **TD-S95-NEW-1 → (a) and (b) DONE** (S97-D / S97-H): three affected sessions in 34, one Rule 13 row
`SENSEX-CHAIN-OI-VOL0-2026-09-25`; (c) stands as S96-D; the table's missing symbol column is TD-S97-NEW-15.
**TD-S95-NEW-2 → CLOSED** (S97-E): 13 rows inserted, verification 14 / 14 / 0; 2026-09-14's odd label → TD-S97-NEW-14.
**TD-S90-NEW-11 → CLOSED** (S97-L): both S90-H backups dropped, `backups_left 0`, live tables unchanged, 46 MB freed.
**TD-S91-NEW-12 → CLOSED**: the in-band gating held live (2026-10-12: 14 sends, all in band, 190 / 156 gated off-band;
0 sends on the 10-20 holiday), and the unmute check, which could not pass while TD-S97-NEW-1 stood, passed once it was
fixed — delivered monitor alerts reached the operator on 2026-10-22. **TD-S91-NEW-13 → CLOSED**: the live-day half read
2026-10-22 05:39 IST — the 2026-10-20 (Dussehra) contract-check log (`logs/contract_check.log.2.gz` after the 10-22
00:00 UTC rotation) holds 84 lines, all `[HOLIDAY GATE] Not a trading day -- no contract checks, no alerts.`, 0 `[SENT]`;
84 = the cron's 12 checks an hour × 7 hours. **TD-S72-NEW-4 → re-observed 2026-10-12**: `idx_gss_symbol_ts` (24 MB) and
`ix_gex_strike_snap_sym_ts` (18 MB) are still both `(symbol, ts DESC)`; `idx_gss_ts (ts)` was added by S97-F.
**TD-S90-NEW-4** — the frozen-tick directories under `~/merdian_fixtures/ticks/` were the decisive evidence for
TD-S97-NEW-6.

### S96 status changes to existing entries (v5 Rule 3: one paragraph, no body edits)

**TD-S95-NEW-1** — part (c) is addressed for the badge only: `v_dex_flow_vs_book` carries `untraded_guard`, and the
badge abstains when legs with volume 0, oi > 0 and `oi_change = oi` hold ≥ 2 % of front DEX gross (ruling S96-D,
`docs/research/s96_priority/guard/guard_survey_result_2026-10-11.md`); readers of OI levels are unchanged, and (a) / (b)
remain the operator's call. **TD-S95-NEW-2** — the backfill SQL is prepared (`sql/2026-10-12_s96_td_s95_new_2_calendar_backfill.sql`,
`8de45b9`; 14 dates from the rule engine, `trading_calendar.json` and the NSE list; dry run 14 / 14 / 0) and is applied by
the operator after a close (ruling S96-J). **TD-S94-NEW-3** — every S96 apply ended its batch with its own verification
SELECT. **TD-S92-NEW-6 / Lovable** — no new instance.

### S95 status changes to existing entries (v5 Rule 3: one paragraph, no body edits)

**TD-S93-NEW-2 → RESOLVED by ruling S95-F** (2026-10-11): a CSV that is an input to, or the
expected value of, a committed result is committed through its own negation line; bulk exports
stay local, pinned by sha256. The DEX expected table's negation line is added at this close
(`.gitignore`). **TD-S91-NEW-13** — the calendar half is done: `trading_calendar` holds
2026-10-20 `is_open = false` (Dussehra, S90 belt; S95 probe 3); the live-day half (validator
silent, no chain rows, `cycle_health` CLOSED) waits for 10-20. **TD-S94-NEW-4** — chain retention
measured: the oldest `option_chain_snapshots` row is **2026-08-24 15:30 IST** on both symbols,
and 08-24 / 08-25 hold one 15:30 row each (S\* availability probe; P5 probe 1). **TD-S94-NEW-3**
— both S95 applies ended their batch with a verification SELECT and both passed in one
execution (`v_dex_repriced_zero`, `v_oi_since_preopen`).

### TD-S97-NEW-6 (S2 priority) — the Zerodha feed was down on 3 of the last 6 trading days; the daily manual Kite refresh is a single point of failure

| Field | Value |
|---|---|
| **Priority** | **S2.** Each miss costs a full session of `market_ticks`, intraday breadth and WCB. |
| **Filed** | 2026-10-22 (Session 97) |
| **Component** | `core/refresh_kite_token.py` on MALPHA (interactive browser login, operator ~06:00 IST) → 03:00 UTC sync → `merdian-wsfeed` preflight 09:10 IST |
| **Measured** | Frozen ticks `~/merdian_fixtures/ticks/`: 10-13 **272 MB**, **10-14 388 KB**, **10-15 388 KB**, 10-16 247 MB, **10-19 388 KB**, 10-20 (holiday) 428 KB, 10-21 260 MB. Telegram preflight alerts received 10-15 and 10-19 ("Zerodha token invalid. Feed NOT started"). `eod_health_check` FAIL for 10-19: `market_breadth_intraday` 0 rows, `weighted_constituent_breadth_snapshots` 0, `market_ticks` SUSPECT (everything γ-side OK). WCB has no rows on 10-14 / 10-15 / 10-19. |
| **Proper fix** | Operator decision: an earlier reminder, a second person, or an automated Kite login path (Kite's terms permitting). At minimum a 08:45 IST check that the synced token validates, paging if not. |
| **Status** | **OPEN — operator decision.** |

### TD-S97-NEW-13 (S3 priority) — 2026-10-21 one-minute spot is recoverable; the chain snapshots are not

| Field | Value |
|---|---|
| **Filed** | 2026-10-22 (Session 97) |
| **Measured** | Dhan `charts/intraday` NIFTY 1-min for 2026-10-21 09:15–09:20 returned candles (05:07 IST 10-22). Option-chain snapshots have no historical endpoint. |
| **Also measured** | Board 2026-10-22 10:03 IST, both symbols: OPEN · GAP tile reads **"prev close missing"** — the 10-21 16:00 close capture failed (`MARKET CLOSE CAPTURE FAILED`, Dhan 806), so today's gap has no reference. |
| **Proper fix** | Operator decision: backfill `market_spot_snapshots` for 10-21 from 1-min candles, tagged as backfilled (source column), **and the 10-21 close** (from Dhan's daily candle) so the gap tile resolves; or leave the gap. |
| **Status** | **OPEN — operator decision.** |

### TD-S97-NEW-18 (S3 priority) — the flow's own gap (ΔOI on unpriced legs) is not on the board

| Field | Value |
|---|---|
| **Filed** | 2026-10-12 (Session 97, P7 live read) |
| **Measured** | Every "since 08:30" figure excludes ΔOI on unpriced legs; the tiles show only the **book** gap. `leg_gap_d_oi_qty`: DEX flow 09:55 NIFTY 17,095 / SENSEX 800; Δ flow 09:55 2,73,390 / 1,02,420, 10:00 40,560 / 1,62,880. |
| **Proper fix** | Show it beside the flow figure (gaps-beside-totals rule); wording for the operator's yes. |
| **Status** | **OPEN.** |

### TD-S97-NEW-19 (S3 priority) — transient "different run — not drawn" / "no chain" while the views were on the same run

| Field | Value |
|---|---|
| **Filed** | 2026-10-12 (Session 97, P7 live read) |
| **Measured** | SENSEX 09:56 and 10:00 IST: the board withheld the flow although `v_delta_drift_flow_vs_book` `ts` equalled the book's; cleared by the next run. Errs safe (nothing wrong drawn). Mechanism (separate polling of two views) **unproven**. |
| **Status** | **OPEN.** |

### TD-S96-NEW-2 (S3 priority) — the planner estimates 1 row for a day of `gex_strike_snapshots` selected by `ts` alone

| Field | Value |
|---|---|
| **Priority** | **S3.** Worked around where it bit (P3b); other day-range readers are unmeasured. |
| **Filed** | 2026-10-12 (Session 96) |
| **Component** | `public.gex_strike_snapshots` — no index leads on `ts`; `ix_gex_strike_snap_sym_ts (symbol, ts DESC)` is used for a ts-only predicate |
| **Measured** | `WHERE ts >= '2026-10-09 03:30+00' AND ts < '2026-10-09 10:30+00'`: estimated **rows=1**, actual **19,198** (154 runs after GROUP BY), 38 ms. Downstream, every CTE inherited the estimate, so P3b's sweep body joined strikes × chain legs as a nested loop with a join filter and hit `roq.sh`'s 30 s timeout twice. With nested loops off (function-scoped `SET enable_nestloop = off`, P3b rev 3) the whole day runs in 1,902 ms. `docs/research/s96_priority/p3b/P3b_invariant_sidecar_design_note_2026-10-12.md` §6. |
| **Proper fix** | Measure first: `pg_stats` for `gex_strike_snapshots.ts`, then an `ANALYZE`, a ts-leading index, or extended statistics — an operator DDL decision. Then re-measure P3b without the SET clause and list the other views that select a day by `ts` alone. |
| **Status** | **OPEN.** |

### TD-S95-NEW-1 (S2 priority) — vendor OI on untraded legs is not a measurement, and every reader of OI levels takes it at face value

| Field | Value |
|---|---|
| **Priority** | **S2.** On three SENSEX sessions it dominated the front book: every OI-level reader (DEX book, GEX, max pain, the walls) read mostly vendor artefact for the whole day. Display-only consumers (S37), so no gate traded on it. |
| **Filed** | 2026-10-11 (Session 95) |
| **Component** | `option_chain_snapshots.oi` as delivered by the vendor · every reader of OI levels: `v_dex_standing_book` (ENH-140), `gex_strike_snapshots` / the GEX views, max pain, L13 levels |
| **Measured** | Drill `docs/research/s95_priority/p5/p5_drill.sql`: deep in-the-money SENSEX calls (68,200–71,800, spot ~73,000) with **volume 0, a frozen LTP and `oi_change = oi` on every row**. 71,800 CE read **48,846,820** all of 2026-09-25 afternoon, **120** at the 09-28 pre-open and **20** at its first trade (09:55, volume 20). 68,200 / 69,300 / 69,400 CE read 0 on 09-25, ~1.84 million through 09-28 and 09-29, 0 on 09-30. Survey `p5_untraded.sql` over 22 symbol-sessions (2026-09-24 → 10-09): on **SENSEX 09-25 / 09-28 / 09-29** legs with no volume held **94.4 / 85.5 / 33.3 %** of front OI and **98.2 / 95.6 / 72.9 %** of DEX gross; every other symbol-session ≤ 0.16 % of OI and ≤ 0.50 % of DEX gross. **No untraded leg changed OI between 09:15 and the close on any of the 22.** OI cannot change without a trade, so on these legs the value is not OI. |
| **Consequence** | Within-session deltas (L13, `v_oi_since_preopen`) are unaffected from 09:15 on; **levels** are inflated for the whole session. A DEX or GEX reading on those three days is not evidence of anything. The S\* out-of-sample SENSEX arms read 0.03 % (10-07) and 0.50 % (10-09); the L3 SENSEX arms (09-22, 09-23) predate the survey and were not measured. |
| **Proper fix** | Operator call, not taken here: **(a)** measure over the whole retention window (from 2026-08-24) how often it occurs and on which strikes; **(b)** decide whether a `data_contamination_ranges` row (Rule 13) covers SENSEX OI levels on 09-25 / 09-28 / 09-29; **(c)** decide whether readers of OI levels flag or exclude legs with volume 0 at the latest snapshot. Any filter is a definition change to live views and needs its own ruling. |
| **Status** | **OPEN.** Recorded in the `v_oi_since_preopen` COMMENT. |

### TD-S94-NEW-2 (S3 priority) — `bin/roq.sh`'s write-verb guard refuses `COPY (SELECT …) TO STDOUT`, which is a read

| Field | Value |
|---|---|
| **Priority** | **S3.** Nothing was written and nothing was read before the refusal. The cost is a workaround everyone has to know. |
| **Filed** | 2026-10-10 (Session 94) |
| **Component** | `bin/roq.sh` (the verb guard) · `docs/research/s94_priority/p2/part1_extract.sql` (refused) vs `part1_extract_v2.sql` (works) |
| **Measured** | P2's first extract used `COPY (…) TO STDOUT WITH CSV HEADER` and was refused by the guard. The working form is psql's own CSV mode: `\set QUIET on` then `\pset format csv` before the `SELECT`. **Without `\set QUIET on`, psql writes `Output format is csv.` into the output file.** Used for P2, P1c and the P6 4i exports. |
| **Proper fix** | Either allow the exact form `COPY ( … ) TO STDOUT` in the guard (it cannot write to the database or the server's disk), or document the `\set QUIET on` / `\pset format csv` idiom in `roq.sh`'s usage text. The second is cheaper and does not widen a guard. |
| **Status** | **OPEN.** |

### TD-S94-NEW-3 (S2 priority) — an apply copied out of the terminal landed only Section 1 of the DEX view, the editor said Success, and the file's own anon check passed over it

| Field | Value |
|---|---|
| **Priority** | **S2.** Caught the same morning, before any consumer read the view, and fixed. S2 because the failure was silent at every step a person would look at — the editor said `Success. No rows returned` and check 4a passed — and because it is the S79 part-run shape (TD-S81-NEW-5) arriving by a new route. |
| **Filed** | 2026-10-10 (Session 94) |
| **Component** | the apply procedure for `sql/` view files run in the Supabase SQL editor; `sql/2026-10-09_s93_v_dex_standing_book.sql` Sections 1–3 |
| **Measured** | The operator copied lines 1–428 from terminal output (`sed -n '1,428p'`) into the editor and ran them once. Afterwards: `CREATE VIEW` present; `obj_description` **NULL**; `relacl` `{postgres=arwdDxtm, anon=rm, authenticated=rm, service_role=arwdDxtm}` — Supabase's defaults, so **neither the REVOKE nor either GRANT ran**. Check **4a passed** on that state (anon SELECT came from the default grant). It surfaced at **4b**, when `bin/roq.sh` (`merdian_ro`) was refused the view. Sections 2–3 were then printed as five lines with their lengths (45 / **7,812** / 66 / 51 / 57 chars), re-run with a trailing verification `SELECT` in the same execution, and landed: 7807 / `a560c0db…`, `anon=r`, `merdian_ro=r`. |
| **Root cause** | **Not established.** The leading hypothesis is that the COMMENT, a single **7,812-character line**, truncated or broke the terminal copy, so the paste ended at or before it — but the first paste was not captured, so this is not measured. What **is** measured: the editor reports success for whatever it was given, and 4a cannot tell a full apply from a partial one when the default grant already gives anon SELECT. |
| **Workaround** | Run the remaining sections again with a verification `SELECT` (COMMENT length/md5 and `relacl`) at the **end of the same batch**, so the result grid shows what that execution did. Repeating Sections 2–3 is harmless. |
| **Proper fix** | (1) Every `sql/` view file ends Section 3 with that verification `SELECT`, so the apply execution itself reports COMMENT and ACL. (2) Write long COMMENT literals as adjacent string constants split across lines (PostgreSQL concatenates constants separated by whitespace that contains a newline), so no line is thousands of characters long. (3) The anon-path check (4a's shape) also asserts `has_table_privilege('authenticated', …) = false` or reads `relacl`, so it fails on the default grant. |
| **Status** | **OPEN** — the instance is fixed (ENH-140 LIVE); the procedure is not. |

### TD-S93-NEW-1 (S2 priority) — `run_offline.sh`'s `PIPESTATUS` idiom is positional, so inserting any command between a pipeline and its test silently disables that step's check

| Field | Value |
|---|---|
| **Priority** | **S2.** Nothing is wrong today — all 11 steps are checked. The debt is that the suite's correctness depends on an invisible adjacency rule, and breaking it produces a step that always passes. A test that cannot fail is the CLAUDE.md rule 0 shape, arrived at by an edit rather than by a design. |
| **Filed** | 2026-10-09 (Session 93) |
| **Component** | `tests/run_offline.sh` — all 11 step lines, each of the form `… \| tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] \|\| rc=1` |
| **Measured** | `PIPESTATUS` is reset by the next command. Demonstrated 2026-10-09: with an `echo` inserted between the pipeline and the test, a step exiting 2 yielded **`rc=0`** — the failure vanished. With no command in between (the file as committed) the same step yields `rc=1`, and exit 1 → `rc=1`, exit 0 → `rc=0`. The mutant control on step 11 (a stub exiting 2) printed `OFFLINE FAIL`, suite exit 1, so **the file is correct as it stands**; this entry is about how easily it stops being correct. `set -uo pipefail` is set (line 8) but does not help, because no step reads `$?`. |
| **Proper fix** | Capture in the same statement, so the value cannot be clobbered by an intervening line: `… \| tail -1; s=${PIPESTATUS[0]}; [ "$s" -eq 0 ] \|\| rc=1`. Eleven mechanical edits. A `step()` shell function taking a label and a command would be better still and is a larger change. |
| **Status** | **OPEN — NOT FIXED.** Found while wiring step 11; deliberately not changed in the same commit, because rewriting all eleven step lines is a separate edit from adding one. |

### TD-S92-NEW-6 (S3 priority) — the Marketview build box has no bun and Lovable updates only `bun.lock`, so a dependency change breaks the install — and the guards hide why

| Field | Value |
|---|---|
| **Priority** | **S3.** Nothing reached live: the guard stops before building. The cost is a silent stop that reads like success. |
| **Filed** | 2026-10-09 (Session 92, post-close) |
| **Component** | box `~/meridian-connect`; install line of `docs/lovable_prompts/s92/mv_lovable_guard.sh` (v2) and `mv_lovable_guard_lab3d.sh`: `if [ -f bun.lock ] && command -v bun …; else npm ci --silent; fi` |
| **Measured** | First S92-J guard run (`origin/main` `f732233`) printed `guard passed` and then **nothing** — no FAIL line, no build. `command -v bun` → none. `npm ci` without `--silent` failed: `package.json` named the four 3D packages, `package-lock.json` did not. That lock file was an **untracked** local file dated 2026-10-05, never in git; Lovable had updated `package.json` + `bun.lock` only. Unblocked by asking Lovable to commit `package-lock.json` (`b6ffec1`) and moving the untracked copy to `~/package-lock.json.oct05.bak`; the re-run passed. |
| **Proper fix** | (1) Drop `--silent` from both guards' install and print `FAIL: install` on a non-zero exit — a check that stops must say why (CLAUDE.md rule 0). (2) Every Lovable prompt that adds a package says "update package-lock.json too". (3) Decide once whether the box builds with bun or npm. |
| **Status** | **OPEN.** |

### TD-S92-NEW-3 (S3 priority) — `sql/2026-10-03_s89_v_gex_greeks_l2.sql` says its V2 probe is "committed with this file", and it is not in git

| Field | Value |
|---|---|
| **Priority** | **S3.** The view and its live COMMENT are correct; what is missing is the query that reproduces one verification bar. |
| **Filed** | 2026-10-09 (Session 92) |
| **Component** | `sql/2026-10-03_s89_v_gex_greeks_l2.sql:559` cites `scratch/s89_l78/p8_ctl.sql` |
| **Measured** | `git ls-files \| grep -c p8_ctl` → **0**; `scratch/s89_l78/` does not exist in the repository. |
| **Proper fix** | Recover the probe from the S89 working tree if it survives and commit it beside the SQL file; otherwise re-author it from the V2 text and say so in the file. |
| **Status** | **OPEN.** |

### TD-S92-NEW-4 (S3 priority) — the S92 views grant `authenticated` more than `SELECT`, through default privileges

| Field | Value |
|---|---|
| **Priority** | **S3.** No surface signs in as `authenticated`; the Marketview path is `anon`, which holds `SELECT` only on these views. |
| **Filed** | 2026-10-09 (Session 92) |
| **Component** | `v_pin_board` (`sql/2026-10-08_s92_v_pin_board.sql`), `v_gex_greeks_l2_strike`, `v_gex_greeks_l2_net` |
| **Measured** | The S92 ACL read showed `authenticated=rm` on the new views. The SQL files `REVOKE ALL … FROM anon` and grant `anon` / `merdian_ro` `SELECT`; they do not touch `authenticated`, so the role inherits Supabase's default privileges — the CASE-2026-09-22 mechanism, on a role the S81 fix did not sweep. |
| **Proper fix** | Fold into the **TD-S89-NEW-5** audit: decide whether `authenticated` should hold anything on `public` views, then add `REVOKE ALL … FROM authenticated` to the three files and apply. Cross-ref the provisional **P4** (anon `MAINTAIN` on three older views). |
| **Status** | **OPEN.** |

### TD-S91-NEW-17 (S3 priority) — `check_kite_auth.py` is cited by the Topology and a runbook and does not exist

| Field | Value |
|---|---|
| **Priority** | **S3.** A documentation defect, but of the kind that sends the next incident response to a file that is not there. |
| **Filed** | 2026-10-07 (Session 91 / AM-2) |
| **Component** | `MERDIAN_Deployment_Topology.md` · the Zerodha/Kite runbook · the script that does not exist |
| **Evidence** | Both documents name **`check_kite_auth.py`** as the Zerodha auth check. There is **no such file** in the repo or on the box. The check that actually exists and actually runs is **`bin/wsfeed_preflight.sh`**. |
| **Why it surfaced now** | Found while tracing **TD-S91-NEW-3**, where the question *"what verified the token at 06:1x and what rejected it at 09:10"* had to be answered against the real artefact. A cited-but-absent script costs exactly the minutes an outage does not have. |
| **Proper fix** | Correct both documents to `bin/wsfeed_preflight.sh`, and state in the same sentence what that script does and does not exercise — **TD-S91-NEW-3**'s proposed 08:40 guard exists because a presence check cannot fail for the reason the incident named. |
| **Status** | **OPEN.** |

### TD-S91-NEW-2 (S3 priority) — SEVEN more unpadded `fromisoformat` sites, one now fixed, and ~40 copies of the same padding with no shared helper

| Field | Value |
|---|---|
| **Priority** | **S3.** Each site is latent until a trimmed fraction reaches it; **TD-S91-NEW-1** is what one of them looks like when it fires. |
| **Filed** | 2026-10-07 (Session 91 / AM-2) |
| **Component** | the scheduled writers listed below · `core/`, the helper that does not exist |
| **Evidence — in priority order** | Grepped across every `.py` named in `docs/registers/aws_crontab.txt`. **1. `backfill_cas_close_from_daily.py:193`** — feeds the CAS reconciliation (**TD-S90-NEW-12**, *Fixed by* row). **2. ~~`build_market_spot_session_markers.py:33`~~ — FIXED `b48532e`** (see the row below). **3. `generate_pine_overlay.py:278, 473, 495`** — three sites. **4. `refresh_health_dashboard.py:40`**. **5. `refresh_dhan_token.py:120`**. **6. `detect_ict_patterns_runner.py:228`** (`r["bar_ts"]`, exposed-probable). **7. `compute_basis_context_local.py:61`** — added 2026-10-07, see below. Sites 1 and 2 first, by the operator's ordering. |
| **Site 2 FIXED — `b48532e`** | `build_market_spot_session_markers.py` `parse_ts` now applies the same `_FRAC` / `_norm_frac` padding as `bcadfa6`, with the `except → None` deliberately kept (callers test for None on a NULL `ts`). **This site had already fired**: 2026-10-05 and 2026-10-06 wrote **no** `market_spot_session_markers` rows at all, because `latest_trade_date_from_spot` got `None` and `fail("Could not parse latest ts…")` exited 1. **Both dates backfilled.** Test `tests/test_marker_ts_parse.py`, `run_offline.sh` **step 8/9**: pre-fix **11 FAIL** with the failing widths exactly `[1,2,4,5]`, post-fix ALL PASS. The test asserts the **exact microsecond** (`.6` → 600000 µs), so a *stripping* fix fails it — padding and stripping are not interchangeable. |
| **Site 7 added — and why the original grep could not see it** | `compute_basis_context_local.py:61` carries the same unpadded body (`grep -c "ljust(6\|_norm_frac\|_FRAC"` = **0**). It is on **neither** of this entry's original lists — not the six sites, not the "already safe" set — because **the grep was scoped to scripts named in `aws_crontab.txt`, and this one is reached as an orchestrator _step_, not as its own cron line.** That is the transferable defect: the enumeration's scope, not the site. **Any re-sweep must walk the orchestrator's step list as well as the crontab.** It is a *candidate* mechanism for **TD-S91-NEW-6**'s 9 `DATA_ERROR` cycles and **not** established as the cause there — see that entry's joint-probability row. |
| **Already safe, measured not assumed** | `check_contracts_shadow.py` pads via its own `_FRAC`; `compile_market_environment_local.py` pads to 6 with a strip fallback. **Not exposed:** `accrue_expiry_outcomes.py`, `ingest_participant_positioning.py`, `relate_ambient_to_open_local.py` — all parse date-only CLI arguments. |
| **The structural half** | `grep -rn "ljust(6"` finds **~40 independent copies** of this padding across the repo and **`core/` holds none** — the only `fromisoformat` in `core/` is `core/trading_calendar_gate.py`, on a date-only string. Both fixes in **TD-S91-NEW-1** say in their own docstrings that one shared `core/` helper is the right fix and is deliberately not that change, so the duplication is on the record rather than quietly added to. |
| **Proper fix** | One `core/` timestamp helper, then retire the copies site by site. |
| **Status** | **OPEN — 2 of 7 fixed and the shared helper BUILT (S92).** Site 2 `b48532e` (S91); **site 7 `bd91d27`** adopts **`core/ts_parse.py` (`f60708d`)**, the shared parser lifted verbatim from the four live copies (41 asserted cells, `tests/run_offline.sh` step 10/10, `0eceee1`). **Sites 1, 3, 4, 5, 6 open** — each is now an adoption of `core.ts_parse.parse_pg_ts`, not a new fix. *(Was: 1 of 7 fixed; the shared helper not built.)* |

### TD-S91-NEW-4 (S3 priority) — `ws_feed_zerodha.log` stamps UTC time under an "IST" label

| Field | Value |
|---|---|
| **Priority** | **S3.** Cosmetic until someone correlates the log against a real clock — which is exactly what **TD-S91-NEW-3** required. |
| **Filed** | 2026-10-07 (Session 91 / AM-2) |
| **Component** | `ws_feed_zerodha.py` logging format · `ws_feed_zerodha.log` |
| **Evidence** | Log lines carry a UTC timestamp with the literal label `IST`: a 5 h 30 m error. Found while timing the 09:10–09:36 outage, where it cost real minutes deciding which clock a line was in. |
| **Proper fix** | Either stamp IST and keep the label, or stamp UTC and label it UTC. **A label that disagrees with its value is worse than no label**, because nothing signals the error. |
| **Status** | **OPEN.** |

### TD-S91-NEW-5 (S2 priority) — the `breadth_indicators_daily:ALL` contract allows 2 trading days behind against a settled lag of ~3, so it read MISSING all day

| Field | Value |
|---|---|
| **Priority** | **S2.** It took **WCB to STALE by lineage on both symbols** for the whole session, so a mis-specified gate degraded a live product. |
| **Filed** | 2026-10-07 (Session 91 / AM-2) |
| **Component** | `data_contracts` row `breadth_indicators_daily:ALL` (`freshness_sla_min` 2880 = 2 trading days) · `check_contracts_shadow.py` daily branch · `weighted_constituent_breadth_snapshots:NIFTY` / `:SENSEX` via `product_lineage` |
| **Evidence** | 2026-10-07: newest `trade_date` **2026-10-01**, so the daily freshness check read **MISSING** on every cycle and both WCB products inherited **STALE**. The Dhan EOD publication lag is **~3 trading days**, settled in **S65/S67** — so the contract's 2-day allowance sits **below the lag it is measuring** and cannot pass on a healthy day. |
| **This is a mis-specified gate and is recorded as one** | Per the settled rule — derive a gate's threshold from the quantity's scale **before** measuring, and a mis-specified gate is recorded as mis-specified and **never loosened in place**. The 2880 came from the S90 seed, not from the measured lag. **Do not widen the row to make today pass.** |
| **Proper fix** | Re-derive `freshness_sla_min` from the **measured** distribution of the Dhan EOD lag, write the derivation beside the number, then change the contract. **Today's 16:10 EOD run is the evidence point** for that measurement. |
| **Status** | **OPEN — gate stands failed, deliberately.** |

### TD-S90-NEW-1 (S2 priority) — `dhan_scrip_map` is never re-synced against the scrip master, so every NSE series change leaves a dead security ID behind

| Field | Value |
|---|---|
| **Priority** | **S2.** Each dead ID is a ticker silently missing from EOD and breadth; S67 read the tail as a structural 97.83 % ceiling. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Component** | `dhan_scrip_map` · `dhan_scripmaster` (reloaded 1st/15th by `reload_dhan_scripmaster.py` → `swap_dhan_scripmaster()`) · `ingest_equity_eod_local.py` |
| **Evidence** | 32 active NSE rows pointed at IDs absent from the master on every exchange and segment; 28 had a replacement ID for the same company (mostly series moves into BE/T), 4 had none. Cured by hand 2026-10-05/06: 0 unmapped. `docs/research/s90_agentic/DH-905_scrip_map_remap_S90.md`, `sql/2026-10-06_s90_dh905_scrip_map_remap.sql`, §D.46.9. |
| **Proper fix** | Roadmap **R1.10**: after each reload, match each active NSE map row to the master by symbol (segment E, any series); remap on one unambiguous match; write a `gap` ledger row (ADR-031 D7) on zero or several; contract check "active map IDs absent from master = 0". |
| **Status** | **OPEN — mitigated by hand; recurs with the next series change.** |

### TD-S90-NEW-3 (S3 priority) — about 26 calendar gates are still inline copies, not `core/trading_calendar_gate.py`

| Field | Value |
|---|---|
| **Priority** | **S3.** The two capture-path gates that read "no row" as open are routed (`ca79717`) and closed days are now rows, so the dated risk (2026-10-20) is covered. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Component** | inline gates across the scheduled scripts (S68 counted ~28; 2 routed in S90) |
| **Proper fix** | ADR-031 D5.3 / roadmap R0.8: route each onto the shared gate, one per change, with the absent-row and gate-failure cases tested as in `docs/research/s90_agentic/patches/patch_r08_gates.py`. |
| **Status** | **OPEN.** |

### TD-S90-NEW-5 (S3 priority) — `v_gex_max_pain` fails intermittently at about anon's 3-second statement timeout

| Field | Value |
|---|---|
| **Priority** | **S3.** One failed read per occurrence; the board shows "no max pain" for that cycle. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Evidence** | One HTTP 500 after 3,282 ms (retry 200 at 1,283 ms); `anon` `statement_timeout = 3s` (MV-6, R0.1 P4). Not reproduced at 15:10 (888 ms). Cause **probable, not proven** — the PostgREST error body was not captured. |
| **Proper fix** | Capture the error body; then index, simplify, or cache per run. |
| **Status** | **OPEN.** |

### TD-S90-NEW-8 (S2 priority) — Marketview Settings is read-only since S90-E; the authenticated write route, `changed_by` and `config_version` are owed

| Field | Value |
|---|---|
| **Priority** | **S2.** Parameters now change only through the SQL editor; `core/pin_state.py` reads eight keys seeded on 2026-10-05. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Component** | `update_parameter()` (EXECUTE revoked from PUBLIC/anon/authenticated, `sql/2026-10-05_s90_apply_S90E_r05_r11.sql`) · `meridian-connect` `src/pages/Settings.tsx` |
| **Proper fix** | ADR-031 D4.3/D4.4 and D3: a write route behind the sign-in that passes the signed-in identity as `p_changed_by`, re-granted only to it; `config_version` stamped on computed rows (roadmap R0.6). |
| **Status** | **OPEN.** Supersedes the write-path half of TD-S89-NEW-2. |

### TD-S90-NEW-9 (S3 priority) — every `roq.sh` connection warns of a collation version mismatch

| Field | Value |
|---|---|
| **Priority** | **S3.** Warning only. A mismatch can mean text indexes sort differently from the OS library. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Evidence** | Database created with collation 153.120, OS provides 153.121 (every `bin/roq.sh` run, S90). |
| **Proper fix** | Supabase-side: reindex check, then `ALTER DATABASE postgres REFRESH COLLATION VERSION` as postgres. Not runnable from `merdian_ro`. |
| **Status** | **OPEN.** |

### TD-S90-NEW-10 (S3 priority) — unused Breeze credentials remain in `.env`

| Field | Value |
|---|---|
| **Priority** | **S3.** No code path uses Breeze (operator, 2026-10-05); the keys are credential surface only, and Rule 19 records both Breeze keys among those exposed in S71. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Proper fix** | Operator removes the Breeze lines from `.env` on the box and revokes the keys at the broker. Note: `.env` line 21 contains `$4`, so `set -u` breaks sourcing — use `set +u` around it. |
| **Status** | **OPEN — operator action.** |

### TD-S89-NEW-5 (S2 priority) — the Marketview bundle reached internet scanners while `:80` served it un-gated, so every anon-readable relation rested on RLS + GRANT alone, unwitnessed

| Field | Value |
|---|---|
| **Priority** | **S2.** Nothing is broken and **no credential needs rotating** — `service_role` appears **0** times in the bundle. The server-side exposure is **closed** (S89 `:80` hardening). What this records is that the `anon` boundary was load-bearing in public for at least two weeks with no audit of what was read through it. |
| **Filed** | 2026-10-04 (Session 89) |
| **Component** | `/var/www/marketview/assets/*.js` · `/var/log/nginx/marketview.access.log*` · Supabase `anon` role · `v_gex_max_pain`, `v_gex_pin_maxpain` (the two `anon=rm` views) |
| **How it was measured** | **Full method and the figure table are in `CASE-2026-09-22-anon-privilege-exposure` §10.2–§10.3; they are cited, not restated here**, so the two cannot drift apart. In outline: the access log **cannot** answer "which Host?" (default `combined` omits it, and `:80`/`:443` share one file), so **response size discriminates** — and the sign-in page's size is **`8484 + len(path)`** (§10.2), which is why equal size does **not** imply equal content. |
| **The headline, separated rather than totalled** | **31** un-gated asset serves, **23 external**, of which **16 from ONE IP** (operator's browser, raw-IP `Referer`) and **15 from 14 distinct IPs with NO Referer**. Per-IP detail and the 4 external `index.html` serves: **§10.3**. The separation matters more than the total — a single total would read as 31 unknown parties. |
| **A first-pass figure of mine that was WRONG, recorded because the correction is the useful part** | My first classification reported **2,757** "un-gated index.html hits". That filter caught 46 responses of **200 / 496 B**, which is **neither** `index.html` (878 B) **nor** the sign-in page (8,485 B). **496 B could not be reproduced** — oauth2-proxy returns 403 / 8,485 B on both paths probed. The confirmed un-gated HTML serves are **4**, not 2,757, and **the 496 B responses remain unidentified.** No explanation is offered, because inventing one to make the data fit is the named anti-pattern. |
| **What the bundle contains — presence only, no values read** | `supabase.co` ×2 · `supabase` ×72 · `anon` ×4 · `eyJ` ×2 (two JWTs) · **`service_role` ×0.** |
| **Why this is NOT a rotation incident** | The Supabase **anon key is designed to be public**, and **D.21.2 records that trust model as VALIDATED**. `service_role` is absent. Proposing a rotation would be the wrong fix — the same shape as CASE-2026-09-22's *"supply the key, never restore the grant"*. |
| **Why it is nevertheless S2** | **TD-S81-NEW-2 established that where RLS is OFF, the GRANT alone is the boundary** — there is no policy to filter, and ~100 tables are in that state. This TD records that the key to that boundary demonstrably left the building, so the GRANT's correctness is now the only control — **and it has no watcher.** CASE-2026-09-22 §7(e) already owes a standing `relations_with_anon_non_select = 0` check that does not exist. |
| **Where to start** | The two views measured at **`anon=rm`** rather than `anon=r` — **`v_gex_max_pain`** and **`v_gex_pin_maxpain`** (S89, from `pg_class.relacl`; the other ten board views read `anon=r`). They carry **MAINTAIN**, the CASE-2026-09-22 default-privileges shape, and are the only known live instances. **`information_schema.role_table_grants` CANNOT see this** — run as `merdian_ro` it omits `anon`'s grants entirely and returns a clean-looking list. **Use `pg_class.relacl`.** |
| **Proper fix** | (1) audit every anon-readable relation against what the frontend actually reads (CASE §7(c), TD-S81-NEW-2); (2) **`ALTER DEFAULT PRIVILEGES`, not `REVOKE` alone** — `REVOKE` alone reproduces S39; (3) the standing check from CASE §7(e). |
| **Not this TD's job** | Closing TCP 80 at the security group — that is **TD-S89-NEW-4**. |
| **Cross-ref** | **CASE-2026-09-22-anon-privilege-exposure** §7, §10 (the S89 forensic addendum) · **TD-S81-NEW-1 / -2 / -3** · **D.21.1 / D.21.2** · **TD-S89-NEW-4** · `docs/runbooks/runbook_nginx_port80_hardening.md`. |
| **Status** | **OPEN.** |

### TD-S89-NEW-4 (S3 priority) — TCP 80 is still open to the world at the security group; the `:80` hardening makes the port answer only redirects, it does not close the port

| Field | Value |
|---|---|
| **Priority** | **S3.** The exposure it guarded is already closed in nginx — `:80` serves no docroot and 301s everything to the gated host. This is the remaining belt: the port is reachable from `0.0.0.0/0` and need not be. |
| **Filed** | 2026-10-04 (Session 89) |
| **Component** | AWS security group on `i-0878c118835386ec2` (attached SG measured `launch-wizard-1` at S39) · `/etc/nginx/sites-available/marketview` · `deploy/nginx/` |
| **Why the port cannot simply be shut** | **Let's Encrypt validates HTTP-01 over port 80.** Renewal here uses the **certbot nginx plugin** — `/etc/letsencrypt/renewal/marketview.meridianalpha.in.conf` reads `authenticator = nginx`, `installer = nginx`, with **no `webroot_path`** — and `snap.certbot.renew.timer` fires daily. Closing 80 outright breaks renewal unless the challenge moves to **DNS-01** first. **That decision is what this TD carries; it is not a one-line SG edit.** |
| **MANDATORY PRECONDITION on any SG edit** | **Run the IMDSv2 attached-SG query from the running instance FIRST:** `TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600") && curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/security-groups`. **This is a settled decision, not advice** — S39 lost hours to SG edits applied to the orphan `launch-wizard-2` while the attached group was `launch-wizard-1`; Console naming and operator memory were both wrong. |
| **What S89 did instead** | nginx `:80` rewritten to a pure redirector — no `root`, no `index`, no SPA fallback; `location / { return 301 https://marketview.meridianalpha.in$request_uri; }`. Verified **301** for raw-IP and unknown-Host (both previously **200**, the asset at 651,242 B), `:443` **unchanged at 200 / 8,485 B**, and **`certbot renew --dry-run` succeeded against the new config**. |
| **What this does NOT undo** | Assets already fetched carry `Cache-Control: public, immutable, max-age=2592000` — **30 days**. **Closing a hole revokes nothing already served**; what was served is **TD-S89-NEW-5**. |
| **Proper fix** | Decide whether 80 stays open for ACME or renewal moves to DNS-01; if it is to be closed, **IMDSv2 query first**, then the SG rule, then **re-run `certbot renew --dry-run` as the proof**. |
| **Cross-ref** | **TD-S89-NEW-5** · **TD-S39-NEW-4** (the orphan `launch-wizard-2`, still owed deletion) · `docs/runbooks/runbook_nginx_port80_hardening.md` · `deploy/nginx/` · ADR-030 is unrelated and is not cited here. |
| **Status** | **OPEN.** |

### TD-S87-NEW-2 (S2 priority) — `check_xrefs` cannot see `AC29-n` labels or `§5a`/`§5b` references, and its document map is hard-coded, so every new ADR needs a patched private copy

| Field | Value |
|---|---|
| **Priority** | **S2.** It is the only cross-reference checker this project has, it is the gate every ADR is cleared through, and it is **silent** on two label families that ADR-029 uses throughout. A checker that reports `ALL CROSS-REFERENCES RESOLVE` while never having looked at a class of reference is worse than no checker, because the clean verdict is taken as coverage. |
| **Filed** | 2026-10-01 (Session 87) |
| **Component** | `check_xrefs` (canonical copy) · the S87 working copy `scratchpad/check_xrefs_with029.py` · its `REAL` map (line 33) and `PATTERNS` list (lines 64–71). |
| **Measured — three distinct gaps** | **(a) `AC29-n` is invisible.** The `PATTERNS` list carries eight kinds — `section`, `decision`, `guard`, `test`, `arm`, `vcheck`, `crit`, `step` — and **none matches `AC29-1`**. Demonstrated rather than reasoned: `scan.py`'s *"AC29 PREFIX — visibility to each check_xrefs token pattern"* block prints **`no match`** for all eight. ADR-029's acceptance criteria are therefore unchecked for collision and for resolution. **(b) `§5a` / `§5b` do not match.** The section pattern is `§\s*(\d+(?:\.\d+)?)\b`; there is **no word boundary between `5` and `a`** because both are word characters, so a letter-suffixed section reference never matches. `WS3.1_baseline.md` §5a is cited in ADR-029 and in the Decision Index, and the checker has never resolved it. **(c) The document map is hard-coded.** `REAL` is a literal dict of four ADR paths, so adding ADR-029 required editing a **private copy under `scratchpad/`** — which is what S87 did, twice (once for the path, once at the `git mv`). |
| **Consequence** | The gate's clean verdict covers only the label families someone remembered to add. Worse, because the map is hard-coded and the working copy lives outside the repository, **the copy that was actually run at S87 is not in version control** — the next session will either patch another copy or run a stale one, and nothing in the repo records which. This is Rule 0 at the level of the verifier: state what the check cannot see, in the same breath as the verdict. The S87 ADR-029 filing commit reports *437 references, 0 collisions* and that figure **excludes every `AC29-n` and every letter-suffixed section**. |
| **Proper fix** | **(1)** Add an `("crit29", re.compile(r"\b(AC\d{2}-\d+)\b"))` pattern, or generalise `crit`, and add a letter suffix to the section pattern (`§\s*(\d+(?:\.\d+)?[a-z]?)`), each with a **negative control** proving it fires on a seeded bad reference. **(2)** Replace the hard-coded `REAL` map with a glob over `docs/decisions/ADR-*.md` plus any draft paths passed as arguments, so a new ADR needs no code edit. **(3)** **Commit the script into the repository** — `docs/research/s87_routing/scripts/` or a `bin/` home — so the thing that gates the ADRs is itself versioned. Until (3) lands, every run is of an unversioned artefact. |
| **Cross-ref** | `TD-S87-NEW-1` (same class — a verifier that passes while blind to what it does not enumerate) · ADR-029 (the document whose labels it cannot see) · core `CLAUDE.md` **Rule 0** and the settled decision *"A verification method can only find what it enumerates."* |
| **Status** | **OPEN.** |

### TD-S87-NEW-5 (S3 priority) — `session_log.md` carried 11 entries against a documented "newest 10", so an earlier doc-close skipped the roll and nothing detected it for a whole session

| Field | Value |
|---|---|
| **Priority** | **S3.** The register was over-length, not wrong — no entry was lost and the overflow file is intact. It is filed because it is a **missed step in the close procedure that no check looked for**, and the close procedure is the thing S87 just rebuilt. |
| **Filed** | 2026-10-01 (Session 87) |
| **Component** | `docs/session_notes/session_log.md` (the newest-10 window) · `docs/registers/session_log_history.md` (the overflow) · the doc-close register order. |
| **Measured from git, not recalled** | `git show 707276a^:docs/session_notes/session_log.md` carries **11** entries matching `^2026-`; `git show 707276a:…` carries **10**. So the file was one over its documented window when S87 opened, and S87's own roll brought it back. The off-by-one means **exactly one** earlier close appended its entry and did not roll. |
| **Consequence** | Small in itself, and that is the point: nothing in the repository asserts the window, so the only reason it was found is that a later close happened to look. A register with a documented length and no length check will drift by one per skipped close, and each individual drift is too small to notice. |
| **Why it is now less likely, and why that is not a fix** | The populated `doc-close` skill (`be9c3d4`) makes the roll **step 6 of an explicit ordered procedure** — *"append the one-line entry, then roll the file to the newest 10 entries"* — where before it was one checklist line among eight with no order and no body. That raises the chance the step is performed; it **does not detect** a skip. **The actual fix is a check**: assert `grep -c '^2026-' session_log.md <= 10` at close, with a negative control on a deliberately over-length copy. Recorded as owed rather than claimed as closed by the skill. |
| **Cross-ref** | `TD-S86-NEW-8` (**RESOLVED S87** — the skill that now carries the register order) · `TD-S73-NEW-8` (the newest-10 split itself, SUPERSEDED BY ADR-028) · the settled decision *"A verification method can only find what it enumerates."* |
| **Status** | **OPEN.** |

### TD-S86-NEW-1 (S2 priority) — the S74 Doc Protocol v4 Rule 7 amendment never reached `MERDIAN_Documentation_Protocol_v4.md`, so two documents define Rule 7 differently and the protocol serves the unamended text

| Field | Value |
|---|---|
| **Priority** | **S2.** Not a runtime defect, but it governs how every register edit is made, and the file that core `CLAUDE.md`'s source-of-truth map sends a reader to still carries the superseded rule. A reader who follows the map correctly gets the wrong instruction. |
| **Filed** | 2026-09-30 (Session 86) |
| **Component** | `docs/registers/CLAUDE_history.md` § Footers → **`CLAUDE.md` v1.51 footer (Session 74, 2026-09-07)** · `docs/operational/MERDIAN_Documentation_Protocol_v4.md:393` · `docs/decisions/MERDIAN_Decision_Index.md` S74 maintenance footer · Doc Protocol v4 Rule 3 / Rule 11 (unchanged by the amendment, per its own scope clause). |
| **Measured** | **Source 1 — the `CLAUDE.md` v1.51 footer, now in `CLAUDE_history.md`, states the amendment:** *"One standing rule amended — **Doc Protocol v4 Rule 7: register updates are applied as byte-level splices with fail-loud assertions, not full-file rewrites** (recorded as a protocol amendment, **not** an ADR; the full-rewrite rule exists for verification, `git diff` verifies better than a byte count, and on a 662 KB file through…"* **Source 2 — `docs/operational/MERDIAN_Documentation_Protocol_v4.md:393`, the owning protocol, still reads:** *"## Rule 7 — `CURRENT.md` is the live session resume (UNCHANGED FROM v3)"* — and its own v3→v4 change table lists *"**Rule 7** — `CURRENT.md` is the live session resume \| UNCHANGED"*. **`grep -rc "splice" docs/operational/` returns 0 for all 8 files**, so the amendment's content appears nowhere in the operational layer. |
| **Consequence** | Rule 7 names two different rules in two live documents, each internally coherent — the **ADR-020 contract-collision shape**, where nothing in either file looks wrong. The amendment *is* recorded in the Decision Index's S74 maintenance footer (*"**DECIDED — register updates are applied as byte-level splices with fail-loud assertions, not full-file rewrites.**"*), which is why this is a documentation defect rather than a lost rule. But core `CLAUDE.md`'s source-of-truth map routes *"When do I write an appendix vs a session note?"* to the Documentation Protocol, not to the Decision Index — so the reader who uses the map as designed reads the unamended Rule 7 and never learns a splice discipline exists. |
| **Second-order — the prediction has now EXECUTED, so this is no longer conditional** | The draft of this entry read *"this is the mechanism ADR-028 D3 would make worse … After D3, loaded context contains neither the amendment nor a pointer to it."* **ADR-028 D10** (the renumbered D3) shipped at `76ad9a3`. The amendment's only statement inside `CLAUDE.md` was the v1.51 **version footer**, and the footers are now in the unloaded `CLAUDE_history.md`. **Loaded context now contains neither the amendment nor a pointer to it** — stated as measured fact rather than as a risk. |
| **Proper fix** | Apply the amendment to `MERDIAN_Documentation_Protocol_v4.md` as its own numbered clause — **not** by overwriting Rule 7, since Rule 7's existing subject (`CURRENT.md` as live session resume) is load-bearing and was never superseded. Either add **Rule 7.1** for the splice discipline, or renumber the amendment to a free Rule number and correct the three documents that cite it as "Rule 7". Record which was chosen; the Decision Index row is the authority for the content and needs no change. |
| **Why a TD and not a silent fix at doc-close** | The amendment as recorded mis-numbers itself: it claims a Rule number whose subject it does not replace. Choosing between *renumber the amendment* and *add a sub-rule* alters a recorded decision (Decision Index S74), so it is an operator ruling, not a doc-close edit. Same reasoning as TD-S82-NEW-4 deferring the `trading_calendar` engine reorder to an ADR-020 amendment. |
| **How found** | The S86 footer-only audit (`~/s86_test/s86_split/footer_only_audit.md`, finding **F1**). The amendment classified DUPLICATE on the Decision Index quote; the protocol was then read to confirm where the rule lives, and did not carry it. |
| **Cross-ref** | ADR-020 (absence/contract collision between two coherent modules) · TD-S73-NEW-8 (the 662 KB file the amendment's rationale cites) · **ADR-028 D10** (removed the last loaded mention) · core `CLAUDE.md` settled decision on citation decay, §D.40.6 (same shape at rule granularity). |
| **Status** | **OPEN.** |

### TD-S86-NEW-2 (S2 priority) — `runbook_update_dhan_token.md` is unexecutable: it names a variable no production script reads, its rotation step is unfilled, and its Supabase SQL uses three column/key names that do not exist

| Field | Value |
|---|---|
| **Priority** | **S2.** The runbook covers a **daily** credential rotation and is the documented recovery for `DhanError 401`, a live-trading outage class with its own runbook cross-reference. Followed verbatim it cannot rotate the token. |
| **Filed** | 2026-09-30 (Session 86) |
| **Component** | `docs/runbooks/runbook_update_dhan_token.md` (lines 3, 13, 15, 37, 44–47, 55, 62, 70–72, 93, 98, 101, 131, 142) · `refresh_dhan_token.py` · `refresh_dhan_token_aws.py` · `pull_token_from_supabase.py` · `dhan_token_refresh_lib.py` · Supabase `system_config`. |
| **Measured — defect 1, wrong variable name.** | The runbook names `DHAN_ACCESS_TOKEN` at **lines 37, 55, 72, 101, 109, 131**. `grep -rln "DHAN_ACCESS_TOKEN" --include=*.py --include=*.sh --include=*.bat .` returns **exactly one file: `check_dhan.py`** (itself defective — TD-S86-NEW-3). `grep -rln "DHAN_API_TOKEN" --include=*.py .` returns **26 files**, including every element of the token path — `refresh_dhan_token.py`, `refresh_dhan_token_aws.py`, `pull_token_from_supabase.py`, `sync_token_to_aws.py`, `core/config.py`, `preflight_common.py`, `stage0_env_contract.py`. The **`CLAUDE.md` v1.45 footer (Session 67, now in `CLAUDE_history.md` § Footers)** states the canonical name independently: *"`ingest_equity_eod_local.py` reads `DHAN_API_TOKEN` as a module-level global at import (L18)"*. **The canonical name is `DHAN_API_TOKEN`; the runbook uses `DHAN_ACCESS_TOKEN` throughout.** |
| **Measured — defect 2, the rotation step is unfilled.** | **Line 44: `### 2. Generate a fresh token` → `⚠ NAVIN: FILL — document the exact steps`**, followed by three guesses *"(a) Log into Dhan web portal … (b) Run an automated TOTP-based refresh script … (c) Call a token-refresh endpoint"*. Step 2 is the only step that actually rotates anything. **The answer is (b) and is in the code**: `grep -rln "TOTP\|totp\|pyotp" --include=*.py .` returns `dhan_token_refresh_lib.py`, `refresh_dhan_token.py`, `refresh_dhan_token_aws.py`, `fix_oi21_token_refresh_hardening.py`. The runbook asks the operator for something the repository already answers — the inverse of core `CLAUDE.md` **Rule 11**. **7 `NAVIN: FILL` markers and 11 `⚠` markers remain**, including **line 15 `Last verified: ⚠ NAVIN: FILL`** and **line 142 change-history row `⚠ \| First real use — fill the ⚠ placeholders`**, so by its own record the runbook has never been used. Created **2026-04-22**; unfilled for ~5 months and ~65 sessions, against core `CLAUDE.md`'s standing rule that a `⚠ NAVIN: FILL` marker is filled **in the same session** the detail is needed. |
| **Measured — defect 3, the Supabase SQL cannot run.** | Lines 70–72: `UPDATE system_config SET value = '<new token>', updated_at = now() WHERE key = 'DHAN_ACCESS_TOKEN';` — carrying its own `⚠ NAVIN: confirm exact key name`. Real columns, from `grep -rn "config_key\|config_value" --include=*.py .`: **`config_key`** (`refresh_dhan_token.py:222`, `refresh_dhan_token_aws.py:79`, `run_merdian_shadow_runner.py:543` `on_conflict`), **`config_value`** (`pull_token_from_supabase.py:198` `rows[0].get("config_value")`, `refresh_dhan_token.py:217`), plus `updated_at`, `updated_by` (`pull_token_from_supabase.py:178`). The real row key is **`dhan_api_token`**, lowercase — `refresh_dhan_token.py:222` `?config_key=eq.dhan_api_token`, and `pull_token_from_supabase.py:194` errors with *"No dhan_api_token row found in system_config"*. **All three identifiers in the runbook's SQL are wrong**: `key`→`config_key`, `value`→`config_value`, `'DHAN_ACCESS_TOKEN'`→`'dhan_api_token'`. |
| **Consequence** | Defect 3 fails loudly (`column "value" … does not exist`), which is the benign case. **Defect 1 is the dangerous one**: Step 1's diagnostic and the Verification block both read `os.getenv('DHAN_ACCESS_TOKEN')`, which resolves to `None`, so `dhanhq(cid, None).get_fund_limits()` fails **whatever the real token's state**. An operator following Step 1 during a genuine incident concludes *"token has expired, proceed"* — per line 40's own decision rule — **on a healthy token**, and rotates a working credential mid-session. It is the mirror of **Rule 0**: not a check that cannot fail, a check that **cannot pass**. Line 101's AWS-vs-Local triage instruction inherits the same wrong name and so cannot discriminate either. |
| **Proper fix** | One pass over the runbook: replace `DHAN_ACCESS_TOKEN` with `DHAN_API_TOKEN` at all 6 sites; rewrite Step 4's SQL against `config_key` / `config_value` / `'dhan_api_token'`; fill Step 2 from `refresh_dhan_token.py` + `dhan_token_refresh_lib.py` (option (b), TOTP self-mint) rather than asking the operator; fill Step 6's two preflight commands from `preflight_common.py` / `stage1_auth_smoke.py`; set `Last verified`. Then re-read core `CLAUDE.md`'s rule that a `⚠` marker is discharged in-session and decide whether the other runbooks carry the same rot. |
| **Sibling sweep owed (B18 discipline)** | Per **B18**, now in `docs/registers/CLAUDE_history.md` § Footers → `CLAUDE.md` v1.30 footer (Session 40) — *"whenever an anti-pattern bug is fixed in one production code path, immediately `grep -rn` for the same shape"* — the `⚠ NAVIN: FILL` count across **all** of `docs/runbooks/` has **not** been measured here and is owed with the fix. Scoped out of this entry deliberately rather than guessed. |
| **Cross-ref** | TD-S86-NEW-3 (`check_dhan.py`, same wrong variable) · core `CLAUDE.md` Rule 11 (do not ask the operator for what the repo records) · Rule 0 (a check that cannot fail for the reason it names) · **B18** in `CLAUDE_history.md` v1.30 footer (N silent siblings) · `runbook_recover_dhan_401.md` (cites this runbook). |
| **Status** | **OPEN.** |

### TD-S86-NEW-3 (S3 priority) — `check_dhan.py` reads `DHAN_ACCESS_TOKEN`, which no script in the repository writes, so it reports `AUTH FAILED` on a healthy token and prints a length of 0

| Field | Value |
|---|---|
| **Priority** | **S3.** A diagnostic, not a writer — nothing downstream consumes it, and a correct sibling exists. It is S3 rather than S4 because its output is *confidently wrong in the alarming direction* and it is reached from a live incident runbook. |
| **Filed** | 2026-09-30 (Session 86) |
| **Component** | `check_dhan.py:6, 9, 10, 11, 18` · `check_token.py` (the correct-form sibling) · `docs/runbooks/runbook_update_dhan_token.md` (propagates the same name). |
| **Measured** | `check_dhan.py:6` — `tok = os.environ.get("DHAN_ACCESS_TOKEN", "")`. `grep -rln "DHAN_ACCESS_TOKEN" --include=*.py --include=*.sh --include=*.bat .` returns **`check_dhan.py` and nothing else** — so no script in the repository *writes* or otherwise references that name, in any language. The 26 files that read the token read **`DHAN_API_TOKEN`**, including the writer path (`refresh_dhan_token.py`, `refresh_dhan_token_aws.py`, `pull_token_from_supabase.py`, `sync_token_to_aws.py`). A sibling diagnostic, **`check_token.py`, uses `DHAN_API_TOKEN`** and is presumably the one that works. **Whether `.env` happens to define `DHAN_ACCESS_TOKEN` as well is `OPERATOR TO VERIFY` — not checked from the agent session, per Rule 19.** Rule 19 form to run in your own shell after sourcing `.env`: `[ -n "$DHAN_ACCESS_TOKEN" ] && echo set \|\| echo unset`. If it prints `unset`, the consequence below holds as written; if `set`, the file is a second, silently-diverging copy of the credential and the finding becomes more serious, not less. |
| **Consequence** | With the variable absent, `tok` is `""`, so line 9 prints `DHAN_ACCESS_TOKEN length: 0`, lines 10–11 print empty slices, and line 18's `dhanhq(cid, "")` makes the API call with an empty token — `AUTH FAILED` on **every** run, including when the real token is healthy. The script cannot distinguish an expired token from its own misconfiguration, and it is reachable from `runbook_update_dhan_token.md` Step 1, which reads the same wrong name inline. **Do not run it to confirm this**: if `.env` *does* carry the name, lines 10–11 print the first 10 and last 8 characters of a live broker token to the transcript — the Rule 19 exposure class, from a script whose purpose is diagnosis. |
| **Proper fix** | Either change line 6 to `DHAN_API_TOKEN` and keep one diagnostic, or delete `check_dhan.py` in favour of `check_token.py`. Prefer deletion: two near-identically-named diagnostics in a 658-file flat root is the discoverability hazard recorded for `build_ict_htf_zones.py`'s **eight variants** — now in `docs/registers/CLAUDE_history.md` § Session 72 engineering discoveries. Whichever is kept, **drop the first-10/last-8 prints** — a length and a boolean are sufficient for the diagnosis and carry no exposure. |
| **Why this is not merely cosmetic** | It is core `CLAUDE.md` **Rule 0** inverted. Rule 0 asks whether a check can fail for the reason it names; this check can only ever fail, and for a reason unrelated to the thing it claims to measure. It has presumably read `AUTH FAILED` since it was written (`check_dhan.py` mtime 2026-06-16) and nobody noticed, because a token diagnostic reporting failure looks like it is doing its job. |
| **Cross-ref** | TD-S86-NEW-2 (the runbook carrying the same name at 6 sites) · Rule 0 · Rule 19 (why this was not run) · TD-S86-NEW-4 (`check_dhan.py` also carries a UTF-8 BOM, so it is in that entry's affected set). |
| **Status** | **OPEN.** |

### TD-S84-NEW-7 (S2 priority) — the UI labels `flip_distance_pct` as sigma, so a spot-to-flip distance is rendered as a volatility band

| Field | Value |
|---|---|
| **Priority** | **S2.** Display-only, but it mislabels one quantity as another on the operator's primary surface, and the two are unrelated. |
| **Filed** | 2026-09-25 (Session 84) |
| **Component** | `meridian-connect/src/marketview/state.ts` · `sections.tsx` · `gamma_metrics.flip_distance_pct` · `v_gex_strike_walls.sigma` · `v_gex_strike_rank.sigma` · `v_gex_pin_maxpain.sigma` · `v_gex_repriced_flip.sigma_1d` |
| **Measured** | **Four sigma definitions exist and none is canonical** (`scratch/s84_contract/gap_probe.out:3`). Walls and rank are textually identical, `spot * atm_iv/100 * sqrt(GREATEST(dte,1)/252.0)` — 252-day year, horizon to expiry; `v_gex_pin_maxpain` inherits walls; `v_gex_repriced_flip` computes `spot * atm_iv/100 * sqrt(1.0/365.0)` — 365-day year, one-day horizon, **a different quantity under a near-identical name**. **None of the four is in `gamma_metrics`.** The front end therefore fabricates one: `state.ts:44` sets `sigmaPct = gamma_metrics.flip_distance_pct` and renders it as **"Spot Context ±X%"** with a `σ lo–hi` subtitle, and elsewhere as **"Σ to expiry"** and **"σ-band to expiry"**. Contract Part 3 §1 and Appendix B. |
| **Consequence** | The operator reads a **distance from spot to the flip level** under a volatility label. The to-expiry definition is also duplicated across two files rather than sourced once, so the two can drift silently, and `GREATEST(dte,1)` overstates sigma at 0 DTE. |
| **Cross-ref** | contract Part 3 §1 · Appendix B · **TD-S79-NEW-1** (`v_gex_pin_maxpain.sigma_overstated_expiry_day`, the self-flag) · ADR-017 (console design). |
| **Status** | **OPEN.** |

### TD-S84-NEW-6 (S2 priority) — two max pains over different substrates, agreeing on strike and disagreeing on everything else; which is canonical is undecided

| Field | Value |
|---|---|
| **Priority** | **S2.** Both are live and anon-readable, and a renderer showing both invites reading the agreement as corroboration when it is not. |
| **Filed** | 2026-09-25 (Session 84) |
| **Component** | `v_gex_max_pain` (GEX-run substrate) · `v_max_pain_by_strike` (raw-chain substrate) |
| **Measured** | `samples_13_17.out:4-9` — `v_gex_max_pain`, NIFTY max pain **23 250**, total pain **40 137 719 250**, **138** strikes, coverage 89.1 / 87.7 %, ts **09:50:07**; SENSEX **71 200**, 137 strikes. `samples_13_17.out:22-27` — `v_max_pain_by_strike`, NIFTY **23 250**, **38 139 112 250**, **269** strikes, ts **10:10:04**; SENSEX **71 200**, 15 036 832 000, 186 strikes. **Same strike on both symbols; different strike count, different total, different ts.** Contract §13 and §15. |
| **Consequence** | Agreement on strike is **not** corroboration — it is two estimators over overlapping data landing on the same grid point on one session. A renderer must pick one and name it, and must never show both as though one validated the other. |
| **Cross-ref** | contract §13 · §15 · **ENH-128** (retroactive registration of `v_max_pain_by_strike`, S81) · **TD-S80-NEW-10** (same view — its missing timestamp and unbounded `max(ts)`, RESOLVED S81 by the `latest_ts` retrofit; the `ts` this entry compares is that retrofit's output). |
| **Status** | **OPEN — the canonical choice is a decision, not a measurement.** |

### TD-S84-NEW-5 (S3 priority) — `anon` holds `MAINTAIN` beyond `SELECT` on three objects created before the S81 default-privileges fix

| Field | Value |
|---|---|
| **Priority** | **S3.** `MAINTAIN` does not permit reads beyond `SELECT` or any write of row data, and all three objects are display-only. Filed because it is the S39 residual shape the S81 fix was meant to end, surviving on objects the fix did not sweep. |
| **Filed** | 2026-09-25 (Session 84) |
| **Component** | `v_gex_max_pain` · `v_gex_pin_maxpain` · `v_participant_oi_latest` · `anon` role · S81 `ALTER DEFAULT PRIVILEGES` |
| **Measured** | `scratch/s84_contract/acl.out` shows `MAINTAIN,SELECT` for `anon` on **`v_gex_max_pain`** (`:15`), **`v_gex_pin_maxpain`** (`:16`) and **`v_participant_oi_latest`** (`:19`); every other object in the eighteen reads `SELECT` only. Contract §13, §14, §17. |
| **Consequence** | S81 fixed the **mechanism** (`ALTER DEFAULT PRIVILEGES`) and did not sweep objects that already existed, so pre-S81 objects still carry the old grants. This is the exact failure S81 recorded: fixing every instance does not fix the mechanism, and fixing the mechanism does not sweep the instances. |
| **Cross-ref** | contract §13 · §14 · §17 · **TD-S81-NEW-1** / **-2** / **-3** (the anon privilege exposure and its `ALTER DEFAULT PRIVILEGES` remedy) · **D.21.1** (Lovable auto-grant safety, REFUTED) · `CASE-2026-09-22-anon-privilege-exposure`. |
| **Status** | **OPEN.** |

### TD-S84-NEW-4 (S2 priority) — the L13 rotation anchor is fabricated on stale vendor rows, and this contradicts TD-S83-NEW-5's "the open interest there is real"

| Field | Value |
|---|---|
| **Priority** | **S2**, not S1: `v_oi_rotation_since_open` is display-only and **no gate reads L13**. S2 because the view currently emits a nine-figure rotation that is an artefact, and because it overturns a finding recorded in the previous session. |
| **Filed** | 2026-09-25 (Session 84) |
| **Component** | `v_oi_rotation_since_open` (ENH-127, L13) · `option_chain_snapshots.oi` / `.ltp` / `.iv` · **TD-S83-NEW-5** |
| **Measured** | SENSEX **72300 CE** reports Δ = **−48 767 480**. The anchor row carries `oi = 48 768 100` with `ltp = 5464.15` **frozen across every snapshot 03:05–04:10 UTC**; `ltp` corrects at **04:15** to 1537.35 and `oi` corrects at **04:20** to **40** (`oi_anomaly.out`, `oi_anomaly2.out`, `iv_stale_correction.out`). The 03:45 anchor sits **inside** that stale window. On the same row, while `ltp` is stale the `iv` reads **119.30 and 121.04**; at 04:15 it **drops to 14.89** — before the OI corrects five minutes later. **72400 CE, whose `ltp` was never stale, reads `iv` 14.11 throughout** (`iv_stale_correction.out`). TD-S83-NEW-5's **48 773 740** for 72400 CE is **byte-identical** to this view's `ce_oi_anchor_qty`; its latest value is **400** (`samples_09_12.out`). Bounded: **4 SENSEX CE + 1 PE** strikes exceed |Δ| > 1M, max **48 773 340**, against a NIFTY max of **3 683 095** (`oi_anomaly3.out`). Contract §9. |
| **Consequence** | Every Δ derived from those strikes is an artefact of a vendor carrying a stale row, not rotation. And the ~8× ATM implied volatility TD-S83-NEW-5 recorded is **not** an unexplained vendor property — it is a stale `ltp` inverted into an implied vol, the S71 *"`ltp` is the last trade, not a price"* finding **in the same row**, not in a different column as that entry supposed. The contradiction is bounded: **2 strikes, 1 session.** |
| **Cross-ref** | contract §9 · **TD-S83-NEW-5** (corrected here; a correction row is appended to it) · **TD-S83-NEW-4** (same feed, opposite direction) · CLAUDE.md *"`ltp` is the last trade, not a price"* (S71) · **ENH-127**. |
| **Status** | **OPEN.** |

### TD-S84-NEW-3 (S2 priority) — three views ship a `COMMENT ON VIEW` in `sql/` that was never executed live, and one ships its `GRANT` commented out: TD-S81-NEW-5 is not remediated

| Field | Value |
|---|---|
| **Priority** | **S2.** A rebuild from these files yields views that are correct in body and undocumented, and for one of them anon-unreadable — the silent-empty shape arriving from the artefact that exists to make rebuilds safe. |
| **Filed** | 2026-09-25 (Session 84) |
| **Component** | `sql/2026-09-15_s79_v_gex_abs_exposure.sql` · `sql/2026-09-22_s80_v_gex_max_pain.sql` · `sql/2026-09-22_s80_v_gex_pin_maxpain.sql` · **TD-S81-NEW-5** |
| **Measured** | **No live COMMENT** on `v_gex_abs_exposure` (`comments.out:8` — `(NO COMMENT)`), `v_gex_max_pain` (`comments.out:15`) or `v_gex_pin_maxpain` (`comments.out:16`), while each `sql/` file **ships one as a live statement** (`:145-146`, `:125`, `:137` respectively). `v_gex_abs_exposure` additionally has its **`GRANT` commented out** at `:156-157` while `anon` holds `SELECT` live (`comment_grant_in_file.out`). Contract §6, §13, §14. |
| **Consequence** | TD-S81-NEW-5 established the rule — *"`sql/` files ship COMMENT and GRANT as live statements, never as commentary"* — and recorded a **part-run apply** as the root cause. That entry's own residual is unclosed and the same shape is present on three further objects. A rebuild of `v_gex_abs_exposure` from its file produces a view at HTTP 200 with zero rows for anon. |
| **Cross-ref** | contract §6 · §13 · §14 · **TD-S81-NEW-5** (the rule, and its unclosed residual) · **TD-S84-NEW-2** (the same clause-4 family, on a table) · **TD-S37-03** (silent empty datasets, not auth errors) · **ADR-025 D2 clause 4**. |
| **Status** | **OPEN.** |

### TD-S84-NEW-2 (S2 priority) — `gamma_metrics` has no `CREATE TABLE` anywhere in `sql/`, an ADR-025 D2 clause 4 gap on the most-read object in the parity set

| Field | Value |
|---|---|
| **Priority** | **S2.** The table is live and healthy; the exposure is that it is **not reproducible from the repo**, and it holds data as well as structure. |
| **Filed** | 2026-09-25 (Session 84) |
| **Component** | `gamma_metrics` table · `sql/` · `sql/2026-05-30_gamma_metrics_s41_p0a_columns.sql` · **ADR-025 D2 clause 4** |
| **Measured** | **No `CREATE TABLE` for `gamma_metrics` exists anywhere under `sql/`** (`scratch/s84_contract/sqlmap.out:1` — the row is present with an empty DDL column). The only committed DDL touching it is a **column-add migration**, `sql/2026-05-30_gamma_metrics_s41_p0a_columns.sql`. The table also **carries no COMMENT** (`comments.out:3` — `(NO COMMENT)`), so its grain `(symbol, ts)` is inferred from the data rather than documented. Contract §1. |
| **Consequence** | ADR-025 D2 clause 4 exists because *"a view living only in the live database is one `DROP` from unrecoverable, and cannot be rebuilt from the repo"*. This is that condition on a **table**, and it is worse than the view case: a table also holds the data, so the loss is not recoverable by re-running a body. |
| **Cross-ref** | contract §1 · **ADR-025 D2 clause 4** · **TD-S79-NEW-3** (`sql/` is a superseded rebuild source) · **TD-S84-NEW-1** and **TD-S84-NEW-3** (the same clause-4 family, on views). |
| **Status** | **OPEN.** |

### TD-S84-NEW-1 (S3 priority) — the `sql/` file does not reproduce the live `merdian_ro` grant on two of the three S83 views, so a rebuild from `sql/` yields a view the verification role reads as EMPTY

| Field | Value |
|---|---|
| **Priority** | **S3.** Real but latent. All three views are live, granted and readable today, so nothing in production is degraded; the defect fires only when a view is rebuilt from its `sql/` file. Not S2 because no consumer is affected now; not S4 because the failure it produces is a silent empty read **inside the verification path itself**, which is the class most likely to make a later session confidently wrong. |
| **Filed** | 2026-09-25 (Session 84) |
| **Component** | `sql/2026-09-24_s83_v_iv_term_structure.sql` · `sql/2026-09-25_s83_v_gex_repriced_flip.sql` · `sql/2026-09-25_s83_v_iv_surface.sql:303` · `merdian_ro` role · `bin/roq.sh` |
| **Measured** | `merdian_ro` holds `SELECT` **live** on all three views — `v_gex_repriced_flip`, `v_iv_surface`, `v_iv_term_structure` (`scratch/s84_item0/c2_grants.out:8`, `:13`, `:18`). Only **one** of the three `sql/` files carries the statement that produces it: `sql/2026-09-25_s83_v_iv_surface.sql:303`, `GRANT SELECT ON public.v_iv_surface TO merdian_ro;` (`scratch/s84_l78/c2_expected_from_files.out`). The other two carry a `REVOKE ALL … FROM anon` + `GRANT SELECT … TO anon` pair and **no `merdian_ro` grant at all**. |
| **Consequence of a rebuild** | A view correct in body, correctly granted to `anon`, and **unreadable by the verification role**. `bin/roq.sh` then returns **zero rows, silently**, and a silent zero is indistinguishable from a genuinely empty view — the **TD-S37-03** shape (*"RLS misconfiguration produces silent empty datasets, not auth errors"* — TD-S37-03 heading, this file), reached here by a missing grant rather than by a policy. The reading would be a property of the reader. |
| **Shape** | **TD-S81-NEW-5's failure aimed at `merdian_ro` instead of `anon`.** That entry's proper fix states the rule generally: **"`sql/` files ship COMMENT and GRANT as live statements, never as commentary"** (TD-S81-NEW-5, *Proper fix* row, this file). The rule was applied to the `anon` grant on all three files and to the `merdian_ro` grant on **one of three**. |
| **Why the existing check does not catch it** | ADR-025 D2 clause 4 reads *"It has an ENH register entry and its DDL is committed under `sql/`"* (`docs/decisions/ADR-025-parity-acceptance-criterion.md:45`), and its stated rationale is recoverability — *"a view living only in the live database is one `DROP` from unrecoverable, and cannot be rebuilt from the repo"* (`:51`). TD-S81-NEW-5 records the consequence in terms: the clause *"is met **in letter** while `sql/` is not a rebuild source. The clause tests for a file, not for fidelity"* (TD-S81-NEW-5, *Bears on ADR-025* row, this file). A file-existence test passes on all three files here; only comparing each file's grant statements against `pg_class.relacl` separates them. |
| **Cost to fix** | **~10 min ESTIMATE, not measured.** One `GRANT SELECT ON public.<view> TO merdian_ro;` appended to the grant block of each of the two files, matching the placement already used at `sql/2026-09-25_s83_v_iv_surface.sql:303`. **No DDL against the live database** — the live grants are already correct; only the rebuild sources are short. Operator to confirm before scheduling against it. |
| **Blocked by** | nothing. |
| **Cross-ref** | **TD-S81-NEW-5** (the rule this misses, and its original shape) · **TD-S81-NEW-16** (`merdian_ro` silent-zero — why an unreadable view is dangerous rather than merely inconvenient) · **TD-S37-03** (silent empty datasets, not auth errors) · **ADR-025 D2 clause 4** · **CLAUDE.md Rule 0** · `docs/research/capture_s84.md` §1.3 and §4. |
| **Status** | **OPEN.** |

### TD-S83-NEW-2 (S2 priority) — `compute_volatility_metrics_local.py` averages a zero implied volatility into `atm_iv_avg` as though it were a real volatility, and derives `dte` from the wall clock rather than from the row it is describing

| Field | Value |
|---|---|
| **Priority** | **S2.** Two independent defects in one writer, both silent, both reaching a published column. |
| **Filed** | 2026-09-25 (Session 83) |
| **Component** | `compute_volatility_metrics_local.py` — `:670-686` (null guard), `:686` (`atm_iv_avg`), `:689-690` (`dte`) |
| **Defect 1 — zero is averaged, not abstained** | The guard at `:670-686` tests for `None` and **not** for zero. Measured S83 on the live chain: `iv IS NULL` occurs on **0 of 1,752** legs at the latest cycle while `iv = 0` occurs on **20 to 134 legs per side per leg** — the feed encodes absence as zero. The one state the guard tests never occurs; the state that does occur passes into `(atm_call_iv + atm_put_iv) / 2.0`. A `grep -c` for any zero guard in the file returns **0**. |
| **Defect 2 — `dte` from the wall clock** | `:689-690` reads `today = datetime.now().date()` then `dte = (expiry_date - today).days`. This is the **TD-NEW-4 shape** (verified: that entry is *"`compute_gamma_metrics_local.py` `dte` payload derived from `date.today()` not `result.ts.date()`"*, **RESOLVED Session 28**, commit `72622a9`): correct on a live run because the row is seconds old, **systematically wrong on any backfill or replay**, where it stamps the run date instead of the row date. |
| **Blast radius** | `volatility_snapshots.atm_iv_avg` and every consumer of it. **Not yet enumerated.** |
| **Why it surfaced now** | The L9 and L10 views (ENH-130/132) adopt `NULLIF(iv, 0)` and anchor `dte` on `ts`; both are recorded in their COMMENTs as **deliberate deviations from this house file**, which is what made the house behaviour legible. |
| **Cross-ref** | **ENH-130** / **ENH-132** COMMENTs · **TD-NEW-4** (the `dte` precedent, fixed in the gamma writer at S28) · **D.11.2** (verified: *"The `dte` payload field is derived from `result.ts.date()` (the cycle's actual timestamp)"* — this file never adopted that rule). |
| **Status** | **OPEN — measured, no fix applied.** |

### TD-S83-NEW-3 (S3 priority) — depth-2 capture intermittently lands a single expiry, so a cycle that should carry W1+W2 carries only W1

| Field | Value |
|---|---|
| **Priority** | **S3.** Handled correctly downstream, so this is a capture-completeness item, not a correctness one. |
| **Filed** | 2026-09-25 (Session 83) |
| **Component** | `ingest_option_chain_local.py` extra-expiry pass — verified line anchors: `:539` the `S80 extra expiries (depth=...)` banner, `:570` and `:584` `_failed.append(_ed)`, `:582` `except Exception as _e:`, `:586-587` the `captured=/failed=/rows=` summary. |
| **Measured** | **3 of 341** stage-1 cycles carried one expiry rather than two, including **2026-09-24 08:45** — roughly once per hundred cycles. Not hypothetical, not frequent. |
| **Downstream behaviour is already correct** | The L9 view yields **one row** with `term_slope` NULL and `is_back` true on that single leg, and does **not** reach back to an earlier `ts` for a second leg — that would compute a slope between two market moments and present it as one observation (ADR-023 D1: fail to absent, never to stale). The defect is bounded at capture. |
| **Not yet established** | Whether the three share a cause. The per-expiry `except` at `:582` appends to `_failed` and the loop continues, so a failure is printed in the `:586-587` summary and not raised. **Whether `main()` (`:594`, invoked by `sys.exit(main())` at `:642`) returns 0 when `_failed` is non-empty is NOT YET TRACED** — it is the obvious next read, and the entry does not assume it. The three instances have also not been matched to their log lines. |
| **Cross-ref** | **ENH-130** (the single-leg path and its measurement) · **TD-S82-NEW-3** (`eod_health_check` has no expected-set and so cannot see this either). |
| **Status** | **OPEN — measured, cause not established.** |

### TD-S83-NEW-4 (S3 priority) — far-wing OTM implied volatility reads *below* ATM on the NIFTY back leg, which no smile explains, and L10 publishes it unfiltered

| Field | Value |
|---|---|
| **Priority** | **S3.** Display-only surface; no gate consumes it. |
| **Filed** | 2026-09-25 (Session 83) |
| **Component** | source feed `option_chain_snapshots.iv` · surfaced by `v_iv_surface` (ENH-132) |
| **Measured, latest cycle** | NIFTY back leg, strikes below −5 % of spot: **OTM-side median iv 3.4940** against an ATM of **11.7904**. A volatility smile is convex — the wings sit *above* the money, not at 30 % of it. The same bucket shows **42.7 % of legs absent** (`iv = 0`), so the surviving quotes are a thin and possibly non-random sample. |
| **Why it is published rather than filtered** | L10 applies **no moneyness cut and no interpolation**. Filtering would hide a feed defect behind a smooth surface; `quote_state`, `oi_otm` and `iv_over_atm` are published so the row stays inspectable. |
| **Not established** | Whether these are stale prints on untraded strikes, a vendor model artefact, or a scale issue at the wing. **No hypothesis has been tested.** |
| **Cross-ref** | **TD-S83-NEW-5** (same feed, opposite failure: iv far *above* ATM on ITM strikes) · **ENH-132** COMMENT · the vendor methodology question drafted this session and not sent. |
| **Status** | **OPEN — measured, unexplained.** |

### TD-S83-NEW-5 (S3 priority) — vendor implied volatility on high-open-interest near-money ITM strikes reads ~8x ATM, and the open interest there is real

| Field | Value |
|---|---|
| **Priority** | **S3.** Excluded from the published surface by construction, but recorded because the OI is not a dead-strike artefact. |
| **Filed** | 2026-09-25 (Session 83) |
| **Component** | source feed `option_chain_snapshots.iv` · surfaced by `v_iv_surface` (ENH-132) |
| **Measured, latest cycle, SENSEX back leg** | Strikes **72100 / 72200 / 72300 / 72400 CE**, **1.60 % to 2.01 % in the money**, read **iv 110.15 / 116.54 / 115.46 / 114.38** against an ATM of **13.0986** — ratios **8.41x to 8.90x** — while holding **48,717,880 to 48,773,740** open interest. One adjacent-strike jump of **92.14 vol points**. |
| **Why it does not reach the published `iv`** | All **20** of the worst outliers by `iv / atm_iv` sit on the **ITM side**, and L10 publishes the **OTM** side, so the convention excludes every one. **14 of the 20 carry `oi = 0`**; these four and two NIFTY puts are the exceptions that do not. |
| **Why it is filed anyway** | The exclusion is a property of the convention, not evidence the values are harmless. Any future consumer reading the ITM side — a synthetic forward, a put-call parity check, an ITM-anchored fit — inherits them. |
| **Cross-ref** | **TD-S83-NEW-4** (same feed, opposite direction) · **ENH-132** COMMENT · CLAUDE.md *"`ltp` is the last trade, not a price"* (the adjacent S71 finding, a different column of the same feed). |
| **S84 correction** | Contradicted on 2 strikes / 1 session: the 48.7M OI and the iv 110–121 on SENSEX 72300/72400 CE are one stale vendor row (ltp frozen 5464.15, 03:05–04:10 UTC); iv 121.04 → 14.89 when ltp corrects at 04:15, OI 48,768,100 → 40 at 04:20. The 'OI is real' claim does not hold on these strikes. See TD-S84-NEW-4 and parity_render_contract.md §9 (iv_stale_correction.out). |
| **Status** | **OPEN — measured, unexplained, excluded by convention rather than by fix.** |

### TD-S83-NEW-6 (S3 priority) — `.gitignore` covers `*.log` but not rotated logs or `status.json`, so the widened logrotate scope produces untracked files the repo does not describe

| Field | Value |
|---|---|
| **Priority** | **S3.** Hygiene; no data at risk. |
| **Filed** | 2026-09-25 (Session 83) |
| **Component** | `.gitignore:33` (`*.log`) |
| **Measured** | `.gitignore` matches **0** patterns for `*.log.[0-9]*` and **0** for `status.json`. The S80 logrotate widening produces `*.log.1`, `*.log.2.gz` and similar in the repo root, none of which `*.log` matches. |
| **Correction to a prior entry** | **TD-S79-NEW-6 treated `status.json` as scratch output. It is not** — it is a live cron output written into the repo root. The distinction changes the remedy: scratch is ignored, a live output belongs either in `logs/` or in `.gitignore` deliberately, with the choice recorded. |
| **Cross-ref** | **TD-S79-NEW-6** (corrected here) · **TD-S73-NEW-1** / **TD-S80-NEW-16** (logrotate scope and config custody). |
| **Status** | **OPEN.** |

### TD-S83-NEW-7 (S3 priority) — two register errata, one of which was itself misattributed in this session's own capture

| Field | Value |
|---|---|
| **Priority** | **S3.** Documentation accuracy. |
| **Filed** | 2026-09-25 (Session 83) |
| **Erratum 1 — and a correction to the capture that reported it** | `capture_s83.md` §5(h) states *"ADR-015 names `oi_total_calls/puts`"*. **Verified at write time, that attribution is wrong.** `docs/decisions/ADR-015-per-strike-gex-schema-v2.md:37` reads **`oi_call`**, and the file contains **0** occurrences of `oi_total_calls`. **The ADR is correct.** The wrong naming lives in **`CLAUDE.md`'s ADR-015 settled bullet**, whose schema line lists `oi_total_calls, oi_total_puts`. Live columns on `gex_strike_snapshots`, read from `pg_attribute`: **`oi_call` (attnum 10), `oi_put` (attnum 11)**. The defect is a summary that drifted from the decision it summarises — the opposite attribution to the capture's, and a sharper instance of the same class. |
| **Erratum 2** | `CURRENT.md:5` reads *"Every session block before S79 lives in CURRENT_history.md"*. Blocks through S81 have since been moved. Corrected to **before S81** in this close (step 1.10). |
| **Why filed rather than only fixed** | Erratum 1 is fixed only when someone edits that bullet; this close does not, because rewriting a settled-decision bullet is an operator call. The row records the drift and names the correct source. |
| **Cross-ref** | **ADR-015** · **ENH-131** (which reads these columns correctly, by measurement rather than from the bullet) · **TD-S76-NEW-15** class: *a standing document describing behaviour it does not produce*. |
| **Status** | **OPEN (erratum 1, `CLAUDE.md` bullet unedited)** · **erratum 2 applied in this close.** |

### TD-S81-NEW-1 (S1 priority) — the live Dhan broker token was readable by anyone holding the public anon key, for an unbounded period; rotation decision and log review are owed

| Field | Value |
|---|---|
| **Priority** | **S1.** A live broker credential was world-readable to any holder of a key that is public by design. The grant is closed; the disclosure question is not. |
| **Filed** | 2026-09-23 (Session 81) |
| **Component** | `public.system_config` (`config_key='dhan_api_token'`) · `public.dhan_auth_tokens` · Supabase anon role · `CASE-2026-09-22-anon-privilege-exposure.md` |
| **Measured, before remediation** | **211** public relations where anon held privileges beyond SELECT; 100+ tables with RLS **off** and anon INSERT/UPDATE/DELETE; 11 auto-updatable views (writes pass through to base tables). `system_config` was anon-readable **including `config_value`**, which is where `pull_token_from_supabase.py:176` shows the operational token actually lives — `dhan_auth_tokens` is referenced by no `.py` in the tree. |
| **Why the key being public is not a mitigation** | The anon key inlines into the Marketview bundle at build time and sits in the public `meridian-connect` repo (**D.21.2**). It is public **by design**. The security boundary was supposed to be the RLS-policy + GRANT pair — and with RLS **off** there is no policy, so the GRANT alone was the boundary, and the GRANT was ALL. |
| **Fixed at the mechanism, not the instances** | Operator applied, verified in-database: (1) `REVOKE ALL ON system_config, dhan_auth_tokens FROM anon, authenticated`; (2) `REVOKE INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER ON ALL TABLES IN SCHEMA public`; (3) **`ALTER DEFAULT PRIVILEGES`** for the same set. **(3) is the one that matters** — S39 fixed the objects that existed then, and every object created afterwards came up with ALL again. Verified through the real anon path: `system_config` → **401**, `dhan_auth_tokens` → **401**, `POST {}` → 401/42501, 22 of 23 frontend relations → 206 with healthy counts, Marketview unaffected. |
| **What is still OWED, and this is the item** | **(a)** Supabase API log review for anon reads of `system_config` and anon writes across the exposure window — which opens **no later than S40** for `v_max_pain_by_strike` and plausibly at project creation for the RLS-off tables. **(b)** **The Dhan token rotation decision. Treat the token as potentially disclosed until (a) says otherwise.** |
| **Expected behaviour change, and the wrong fix for it** | A script with an empty `SUPABASE_SERVICE_ROLE_KEY` no longer degrades silently to anon — it now **fails loudly**. Rarely-run backfill / `canonical_*` scripts will surface first. **The fix when that happens is to supply the key, never to restore the grant.** |
| **Cost to fix** | (a) ~1 h of log review. (b) an operator decision plus a rotation run. |
| **Blocked by** | nothing. |
| **Cross-ref** | **`CASE-2026-09-22-anon-privilege-exposure.md`** (the incident) · **D.21.1** (reopened as a live regression, then closed at the mechanism) · **D.21.2** (trust model corrected) · TD-S81-NEW-2 / -3 (the other two residuals) · TD-080 · `pull_token_from_supabase.py:160/176`. |
| **Status** | **OPEN — the grant is closed; (a) and (b) are the item.** |

### TD-S81-NEW-2 (S2 priority) — anon SELECT is still far broader than the 23 relations the frontend consumes

| Field | Value |
|---|---|
| **Priority** | **S2.** Least-privilege is not yet reached; the write surface is closed but the read surface is not scoped. |
| **Filed** | 2026-09-23 (Session 81) |
| **Component** | Supabase anon role · `public` schema · Marketview `src/lib/queries.ts` |
| **Symptom** | The S81 revoke removed every non-SELECT privilege. **SELECT was left broad.** `capital_tracker`, `app_settings` and others remain anon-readable and are consumed by nothing. |
| **Proper fix** | Enumerate the frontend's actual relations (**23**, measured this session), then `REVOKE SELECT ON ALL TABLES` and re-grant only those. Do it as one reviewable script, not incrementally. |
| **Do not do this blind** | A too-tight grant empties a Marketview panel at HTTP 200 with no error — the **TD-S37-03** silent-empty-dataset shape. Verify each of the 23 through the anon path after the change, not just the count. |
| **Cost to fix** | ~1 h including verification. |
| **Blocked by** | nothing, but sequence it after TD-S81-NEW-3 so the standing check can witness it. |
| **Cross-ref** | **`CASE-2026-09-22-anon-privilege-exposure.md`** item (c) · D.21.1 · TD-S37-03 · TD-S81-NEW-1. |
| **Status** | **OPEN.** |

### TD-S81-NEW-3 (S2 priority) — nothing asserts that the anon revoke is still in force; item 3 of the S81 fix is trusted rather than verified

| Field | Value |
|---|---|
| **Priority** | **S2.** This is the watcher for an S1 fix. Without it the `ALTER DEFAULT PRIVILEGES` is a belief. |
| **Filed** | 2026-09-23 (Session 81) |
| **Component** | `bin/disk_guard.sh` (S81, has a proven Telegram path) or `scripts/eod_health_check.py` |
| **Symptom** | The mechanism fix is a one-time DDL. If a future migration, a Lovable scaffold, or a manual grant re-opens the write surface, **nothing fires.** |
| **Root cause, and it is the recurring one** | *A resolved item has no watcher.* **D.21.1 was recorded remediated at S39 and silently regressed for every object created afterwards** — `v_max_pain_by_strike` (S40) measured at all seven privileges this session is the proof. Identical shape to TD-S69-NEW-1, whose premise lapsed unwatched (**D.37.8**), and to TD-S80-NEW-18, which this session closed by building exactly such a check. |
| **Proper fix** | A daily query asserting `relations_with_anon_non_select = 0`, wired into the existing alert transport. **It must be a live check, not a review item.** |
| **Cost to fix** | ~45 min. The transport exists and is proven on three branches. |
| **Blocked by** | nothing. |
| **Cross-ref** | **`CASE-2026-09-22-anon-privilege-exposure.md`** item (e) · D.21.1 · **D.37.8** · TD-S80-NEW-18 (the same remedy, built this session) · TD-S69-NEW-1. |
| **Status** | **OPEN.** |

### TD-S81-NEW-4 (S2 priority) — `v_dealer_flow_sim` is the third ADR-021 sibling and was never scoped; it returns 57014 on any unfiltered read

| Field | Value |
|---|---|
| **Priority** | **S2.** Live on an operator page, and it already fails — the frontend escapes it only by accident of call shape. |
| **Filed** | 2026-09-23 (Session 81) |
| **Component** | `public.v_dealer_flow_sim` (ENH-81, S37) · Marketview `useDealerFlow` |
| **Symptom** | Measured this session: **HTTP 500 / `57014` on an unfiltered read**; **200 in 0.44 s** when filtered by symbol, which is how `useDealerFlow` happens to call it. **Pre-existing — not caused by the S81 anon revoke**, which is what the probe was actually testing when it surfaced. |
| **Root cause** | **ADR-021** scoped `v_gex_strike_pin_zone` and `v_gex_strike_accel_zone` at S69 and left this one unbounded. Same cost shape: work proportional to table size behind a consumer that reads one run. |
| **Why it matters despite the frontend escaping it** | The escape is a property of the *caller*, not the view. Any new consumer that reads it unfiltered — including a diagnostic — gets a timeout, and **ADR-021's whole finding is that a cost curve crossing a ceiling is silent until it isn't.** |
| **Proper fix** | The same `latest_run` + `scoped` CTE pair ADR-021 applied to its two siblings. Ship `COMMENT` and `GRANT` as live statements per the S81 rule. |
| **Cost to fix** | ~1 h including EXPLAIN and an equivalence gate. |
| **Blocked by** | nothing. |
| **Cross-ref** | **ADR-021** · ENH-81 (S37) · TD-S81-NEW-17 (the same shape, fixed this session on the max-pain view) · `CASE-2026-09-22-anon-privilege-exposure.md` (where it surfaced). |
| **Status** | **OPEN.** |

### TD-S81-NEW-5 (S2 priority) — `sql/` is not a true rebuild source, and the divergence runs in BOTH directions

| Field | Value |
|---|---|
| **Priority** | **S2.** A rebuild from `sql/` would produce views that are correct in body, better documented than live, and **anon-inaccessible.** |
| **Filed** | 2026-09-23 (Session 81) |
| **Component** | `sql/2026-09-15_s79_v_gex_strike_walls.sql` · `…_v_gex_abs_exposure.sql` · `…_v_gex_concentration.sql` |
| **Measured, all three S79 views** | view bodies: present in `sql/`, present in DB, **semantic MATCH 3/3**. `COMMENT ON VIEW`: present in `sql/` 3/3, **ABSENT in DB 3/3** at S81 open. `GRANT SELECT` to anon: **COMMENTED OUT in `sql/` 3/3**, **PRESENT in DB 3/3**. |
| **Consequence of a rebuild** | Three panels at **HTTP 200 with zero rows** — the **TD-S37-03** silent-empty-dataset shape, from the artefact that exists to make rebuilds safe. |
| **Root cause** | The S79 apply ran Section 1 per view and **never ran the COMMENT statements.** This is **wider than TD-S79-NEW-13**, which assumed the sentence was unwritten rather than the file part-run. |
| **Bears on ADR-025** | D2 clause 4 (*"DDL committed under `sql/`"*) is met **in letter** while `sql/` is not a rebuild source. The clause tests for a file, not for fidelity. |
| **Residual after S81** | `v_gex_abs_exposure`'s S79 comment (`sql/2026-09-15_s79_v_gex_abs_exposure.sql:145-146`) is **still unapplied**, and the grants half is **unfixed on all three by instruction.** Four objects shipped this session (ENH-125/126/127 and the max-pain fix) **do** carry COMMENT and GRANT as live statements — that is the pattern to generalise. |
| **Proper fix** | Uncomment the GRANTs in the three S79 files, apply the missing COMMENTs, and adopt the S81 rule generally: **`sql/` files ship COMMENT and GRANT as live statements, never as commentary.** Then a rebuild-from-`sql/` drill, because that is the only check that can fail for the right reason. |
| **Cost to fix** | ~1 h for the three files; the drill is the real cost and the real value. |
| **Blocked by** | nothing. |
| **Cross-ref** | **ADR-025 D2 clause 4** · TD-S79-NEW-3 (`sql/` as superseded rebuild source) · TD-S79-NEW-13 (narrower framing, superseded here) · TD-S37-03 · ENH-126's grant miss, which is this shape **observed rather than described** (the view was live and anon-unreadable until the GRANT was re-run). |
| **Status** | **OPEN.** |

### TD-S81-NEW-6 (S3 priority) — `v_max_pain_by_strike.max_pain` has a non-deterministic tie-break

| Field | Value |
|---|---|
| **Priority** | **S3.** Latent, not live — ties in real OI-weighted pain are near-impossible. |
| **Filed** | 2026-09-23 (Session 81) |
| **Component** | `public.v_max_pain_by_strike` |
| **Symptom** | `row_number() OVER (PARTITION BY symbol, expiry_date ORDER BY total_pain)` with **no tie-break column**, so equal `total_pain` yields an arbitrary winner. **ENH-123 orders by `(total_pain, candidate_strike)`** and is the reference. |
| **Why it was not fixed with the rest** | Present in the S40 baseline and **carried unchanged through both S81 changes by instruction.** One line, but outside the approved scope, and a semantic change to a view the frozen Marketview reads. **One change, one reason.** |
| **Why it is recorded at all** | The S81 fix registered this object's DDL for the first time ever. **Shipping known non-determinism inside a first-ever canonical DDL without writing it down is how defects become invisible.** |
| **Proper fix** | Add `, candidate_strike` to the `ORDER BY`. |
| **Cost to fix** | One line, plus an equivalence gate against the current body. |
| **Blocked by** | nothing. |
| **Cross-ref** | ENH-123 (`v_gex_max_pain`, the correct ordering) · TD-S80-NEW-10 (closed this session) · `sql/2026-09-22_s81_v_max_pain_by_strike_CAPTURED_BASELINE.sql`. |
| **Status** | **OPEN.** |

### TD-S81-NEW-8 (S3 priority) — `~/redeploy_marketview.sh` builds from a stale May-27 clone, not the tree the live bundle comes from

| Field | Value |
|---|---|
| **Priority** | **S3.** Not live — the script was not used for the S81 deploy — but it is a loaded gun for whoever runs it next. |
| **Filed** | 2026-09-23 (Session 81) |
| **Component** | `~/redeploy_marketview.sh` · `~/merdian-marketview` (stale) · `~/meridian-connect` (canonical) |
| **Measured** | The script's `SRC_DIR` is `~/merdian-marketview`, a **May-27 clone at `14b63f3`**. The live `/var/www/marketview` is **md5-identical to `~/meridian-connect/dist`** (`7b60d01`, Jul-12). The Enhancement Register S40 footer **already names `~/meridian-connect` canonical.** |
| **Corroboration** | The script also does `chown www-data`; the live tree is `ssm-user`-owned and works — **further evidence the Jul-12 deploy did not use this script either.** |
| **Root cause** | **The S72 flat-namespace shape**: two similarly-named trees, one live, and a filename that cannot tell you which. |
| **Proper fix** | Point `SRC_DIR` at `~/meridian-connect`, or delete the script. Deleting is defensible — the S81 deploy was done by hand and documented. |
| **Cost to fix** | ~10 min. |
| **Blocked by** | nothing. |
| **Cross-ref** | S72 flat-namespace finding · Enhancement Register S40 footer · Deployment Topology §S81 (Marketview deploy path). |
| **S84 update** | Live HEAD has moved **`7b60d01` → `a408fb4`**; the served bundle is now **`index-DLdbWkEE.js`**, md5 **`56ad2b21…`**, matching `/home/ssm-user/meridian-connect/dist`. The stale clone is **still at `14b63f3`**. **The finding stands; the hash evidence above is superseded.** (`parity_render_contract.md` §2.1.) |
| **Status** | **OPEN.** |

### TD-S81-NEW-15 (S3 priority) — the register says `merdian_order_placer.py` runs from an `@reboot` cron line; neither the line nor the process exists

| Field | Value |
|---|---|
| **Priority** | **S3.** Nothing is broken. A register entry describes a process that is not running. |
| **Filed** | 2026-09-23 (Session 81) |
| **Measured 2026-09-23** | `crontab -l \| grep -c '@reboot'` = **0** — no `@reboot` line of any kind. `ps -eo pid,etimes,cmd` shows **no placer process**; the only long-lived Python is `ws_feed_zerodha.py`, which holds no Dhan token. **No systemd unit hosts it** — the only MERIDIAN unit is `merdian-wsfeed.service`. |
| **Where the stale claim lives** | CLAUDE.md's S28 settled-decisions bullet (*"Phase 4B Order Placer … `@reboot` cron"*) and Deployment Topology §3 / §7.1 / §8.2, written at the same time. **It was true when written.** |
| **Root cause** | The recurring decay shape: **a register entry written from a live observation has no watcher, and nothing fires when its premise expires** (TD-S69-NEW-1, **D.37.8**). Four of five carried items at S71 described a system measurement did not find. |
| **Proper fix** | Determine whether the placer was **deliberately retired**, **silently lost** (the S53 crontab-reinstall shape, where a dropped line caused a 28 h blackout), or **moved** to an uncatalogued launch path. **Do not re-add the line before answering that** — the order placer is the one component in MERIDIAN that can transact. |
| **Bears on TD-S81-NEW-20** | A daemon that caches the Dhan token at import (`merdian_order_placer.py:60`) and runs indefinitely is **the worst case in the B18 family** — it would hold an invalidated token from the first rotation after boot until restarted. Not live, so not exposed today; **if revived, the at-use token read must land with it.** |
| **Cost to fix** | ~30 min to determine; the decision is the operator's. |
| **Blocked by** | nothing. |
| **Cross-ref** | CLAUDE.md S28 bullet · Deployment Topology §3 / §7.1 / §8.2 · TD-S69-NEW-1 · **D.37.8** · S53 crontab-reinstall shape · **TD-S81-NEW-20**. |
| **Status** | **OPEN.** |

### TD-S81-NEW-20 (S3 priority) — `DhanClient` reads the Dhan token at construction, so a rotation mid-cycle leaves a running process holding an invalidated token

| Field | Value |
|---|---|
| **Priority** | **S3.** Correct by construction regardless of whether it caused the observed 401s; the observed cost so far is one lost SENSEX cycle and one W2 snapshot. |
| **Filed** | 2026-09-23 (Session 81) |
| **Component** | `core/dhan_client.py:27-36, :44` · `ingest_option_chain_local.py:378` |
| **Symptom** | `DhanClient.__init__` captures `self.settings.dhan_access_token` into `self.headers` and `_post` reuses it for the life of the client. All three public methods route through that one `_post`. **Anti-pattern B24**: `.env` edits do not propagate to running processes. |
| **Observed, 2026-09-23** | Two `401 / 808 Authentication Failed` inside the `03:05:01Z–03:05:12Z` cycle: **SENSEX on its W1 call — losing the whole cycle** — and NIFTY on its W2 call. **W1 was affected, contrary to an earlier S81 report** whose grep pattern required a date in the retry label and so was structurally incapable of matching a W1 failure. |
| **Mechanism UNCONFIRMED, deliberately** | The hypothesis is that the 03:05 token refresh rotates mid-cycle. `cron.log` shows `DHAN TOKEN REFRESH SUCCESS` positioned between the cycle STARTs and the 401s — **but position in a shared append-mode log is not event order**: three processes append to it and the refresh's banners carry **no timestamp of their own**, so a block-buffered flush at exit would place them identically. **The check that would settle it:** a timestamped token-write record compared against that window — `dhan_token_probe_log` is the natural source and **`merdian_ro` is blind to it** (TD-S81-NEW-16), so it needs a policy or an operator run. |
| **The fix does not depend on the mechanism** | **Reading a credential at use rather than at import is correct regardless.** A process holding a credential across an interval in which another process can rotate it is a defect by construction, visible in source, independent of the 401's provenance. **So this is not blocked on a check that cannot currently be run.** |
| **Proper fix — written up in full, NOT applied** | One edit in `core/dhan_client.py` (not the ingest): a `_current_dhan_token(fallback)` helper mirroring S67's `ingest_equity_eod_local.py:109-119`, plus a per-request header build in `_post`. **Two facts make it non-obvious and a naive fix would change nothing:** `get_settings()` is **not cached** (`core/config.py:40`), and `core/config.py:10-14` hardcodes a Windows `BASE_DIR` so its `load_dotenv` **never fires on AWS** (TD-S60-NEW-5) — therefore `os.getenv` at use returns the **same stale value** as at import. **`load_dotenv(override=True)` is the load-bearing part, and `override=True` is not optional.** Three anchors, a verification that must be run against the unpatched file first (where it must FAIL), a negative control, and a pre-registered N=10-trading-day acceptance test are all recorded in the S81 notes. |
| **Blast radius, measured** | `DhanClient()` is constructed in three files — `ingest_option_chain_local.py:378`, `test_core_layer.py:35`, and a dead `.BEFORE_BATCH_FIX` backup. **Two live call sites.** |
| **TWO LIVE SIBLINGS needing separate smaller changes (B18)** | **`capture_spot_1m_v2.py`** (import-time token at `:84`, runs `*/1` in hour 03 — every minute through the rotation) and **`compute_gamma_metrics_local.py`** (`os.getenv` in-function at `:734` but **never re-reads `.env`, so still stale within the process** — precisely the trap the two facts above describe, already in the codebase). Eleven scripts capture the token at import; exactly one (`ingest_equity_eod_local.py`, S67) reads at use. The rest are unscheduled — **filed so a reviver knows, not patched.** |
| **Cost to fix** | ~1 h for `core/dhan_client.py` including the failing-first test; ~30 min each for the two siblings. |
| **Blocked by** | an operator instruction to apply. |
| **Cross-ref** | **B24** · **B18** · TD-S66-NEW-1 / S67 `_current_dhan_token()` · **TD-S60-NEW-5** (the Windows `BASE_DIR`) · **TD-S81-NEW-14** (the retry predicate that fails fast on these 401s) · **TD-S81-NEW-15** (the placer, worst case if revived) · TD-080. |
| **Status** | **OPEN — proposal written and reviewed, not applied.** |

### TD-S80-NEW-1 (S2 priority) — the ingest discards the expiry ladder the vendor returns, so no multi-expiry IV exists at any timestamp and L9 has no live source

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
| **Stage numbering — CORRECTED S81** | This row previously read *"stage 2 is `{2,2}`; stage 3 is NIFTY to 4"*, which is **off by one against ADR-025 Amendment A1**, whose wording is *"a stage 0 at depth 1 — provably inert — precedes W1+W2"*. The canonical numbering is **stage 0 = depth 1 (inert) · stage 1 = W1+W2 · stage 2 = NIFTY 4**. `ingest_option_chain_local.py:57-59` carried the identical off-by-one and was corrected in the same anchor at `8d51cce`. **The code comment mattered more than this row** — it is what an implementer reads when choosing a value. |
| **S88 - stage-1 two-armed test: SENSEX arm PASSED x3, NIFTY arm STILL OWED** | Pre-registered before any OI or expiry data was read (`scratch/s88_l9/prereg.out`, sha `5d20b95b...40071994bf`); instrument `scratch/s88_l9/l9_sensex.sql` sha `9311db91...68b8f0b0ce` verified before each run. **PASS at 12:45:07, 14:55:06 and 15:30:06 IST on 2026-10-01** (SENSEX dte 0): arm A 0/0 both ways, arm B 197/197, no tie at minimum `total_pain` in any of the three bodies. Mechanism: W2-only strikes 0 and all three `max_pain_strike` values agreeing, so **all 197 differing rows differ in `total_pain` alone - the mixture moved the magnitude and never the published level**. Shared strikes where W2 OI > W1 grew 6 -> 12 -> 16 while arm B stayed saturated at 197. **This does NOT close this entry: the NIFTY arm remains owed, next NIFTY expiry 2026-10-06** (measured, `scratch/s88_design/nifty_front_expiry.out:5,13,21`). Detail `docs/research/capture_s88.md` §1. |
| **Status** | **OPEN — STAGE 1 DEPLOYED AND VERIFIED 2026-09-23.** `EXPIRY_DEPTH = {"NIFTY": 2, "SENSEX": 2}` at `8d51cce`, first live cycle the 08:30 IST ingest of 2026-09-23. Verified at 09:14 IST through `bin/roq.sh`, **all four checks PASS on both symbols**: A depth landed (2 expiries / 2 run_ids), **B gamma on FRONT expiry** (NIFTY `2026-09-29` dte 6, SENSEX `2026-09-24` dte 1), C one gamma row per cycle, D options flow on front expiry. **B is the load-bearing check and it could have failed**: W2 (`2026-10-06` dte 13 / `2026-10-01` dte 8) was live in the table at the same `ts`, and the pre-`89ad2bb` selector would have returned it. **Remains OPEN for stage 2 (NIFTY 4)**, which is gated on a week of ENH-99 retry telemetry — and **TD-S81-NEW-14 shows that telemetry cannot presently record the failures actually occurring**, so the gate needs re-definition before it can be read. |

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

### TD-S80-NEW-14 (S3 priority) — `tech_debt.md` closed TD-S79-NEW-14 and left three references to it stale one file over

| Field | Value |
|---|---|
| **Priority** | **S3.** No behaviour depends on it. It is filed because it is the third instance of a shape this register keeps recording. |
| **Discovered** | Session 80 (2026-09-22), while writing ENH-123/124 into the Enhancement Register. |
| **Component** | `docs/registers/MERDIAN_Enhancement_Register.md` |
| **Symptom** | Three places still assert the EXPLAIN is outstanding — ENH-121's *"3d EXPLAIN outstanding - TD-S79-NEW-14"*, ENH-122's *"3f EXPLAIN outstanding"*, and a file-tail bullet — while `tech_debt.md` records TD-S79-NEW-14 **RESOLVED at S79** on an `Index Only Scan` with no base-table scan. |
| **Root cause** | S79 closed the item in one register and did not sweep the others. **This is the TD-S76-NEW-12 shape:** an edit landing without the register's own self-description moving with it. S76 recorded three instances in one close and called it *"a pattern, not three accidents"*. |
| **Proper fix** | Applied at this doc-close as **annotation, not rewrite** — the as-filed text is kept and a CORRECTION note appended, per the register's convention that an entry records what was believed before it was measured. The residual is that the convention **has no sweep step**: nothing looks for other files asserting a closed item is open. |
| **Cost to fix** | Minutes for the instance; the sweep step is a protocol question. |
| **Blocked by** | nothing. |
| **Cross-ref** | TD-S76-NEW-12 · TD-S76-NEW-13..17 (the same class) · TD-S79-NEW-14 (RESOLVED S79, transcript-only evidence) · TD-S80-NEW-19 (the same shape inside a single entry). |
| **Status** | **OPEN.** Instance annotated at the S80 doc-close; the missing sweep step is the real item. |

### TD-S80-NEW-15 (S2 priority) — ~1.76 GB of the 2.5 GB that filled the root volume is unattributed, so the resize is a delay of known length rather than a fix

| Field | Value |
|---|---|
| **Priority** | **S2.** The volume is at 20% and the immediate risk is gone. The item is that **nobody can say what fills it**, and 24 GB at the measured rate is about five months. |
| **Discovered** | Session 80 (2026-09-22), after the disk-full access lockout. |
| **Component** | `i-0878c118835386ec2` root volume `vol-09b957d7f294beba0` · `~/.local` · `~/.claude` · `/var/lib` · `/var/log` |
| **Symptom** | Growth measured **4.9 GB at S73 (2026-09-06) → 7.6 GB ceiling (2026-09-22)** — ~2.5 GB in sixteen days, **~150 MB/day**. |
| **Root cause** | **Not established.** The leading candidate was recorded as *"~/.local 872 MB + ~/.claude 102 MB + ~/.cache 57 MB ≈ 1.0 GB, all Claude Code"*. **Measured, that attribution is wrong on two of three terms** — `.local/share/claude` 636 M + `.claude` 102 M = **738 MB is Claude Code**; `.local/lib/python3.10` **236 M is pip user site-packages** (the engine's own dependencies) and `.cache/pip` **57 M is pip's HTTP cache**. At ~46 MB/day that is **under a third** of the rate, leaving **~1.76 GB unexplained**. The reboot returned ~1.5 GB, which points at **deleted-but-still-open files**; `lsof +L1` after the restart is empty, so it cannot be attributed retroactively. |
| **Proper fix** | `du -x` on `/var/lib`, `/var/log` and both repo trees, and an `lsof +L1` **before** the next restart rather than after. Then decide whether 30 GiB is the right size or the growth is the defect. |
| **Cost to fix** | ~30 min of measurement; the remedy depends on what it finds. |
| **Blocked by** | nothing. |
| **Cross-ref** | Deployment Topology §S80.7 · Assumption Register **D.37.7** (the corrected attribution) and **D.37.8** (why §S71.4's headroom estimate lapsed) · TD-S69-NEW-1 (the ceiling item, closed by the resize) · TD-S73-NEW-1 (`shadow_runner.log`, closed by the logrotate widening) · TD-S73-NEW-2 (the `C:\GammaEnginePython\heartbeats/` writer, still unidentified). |
| **Status** | **OPEN.** Note that **78 MB of the measured Claude Code footprint is `~/.claude/projects/-home-ssm-user-meridian-cc`** — agent transcripts, which grow every session including this one. The agent tree is not free. |

### TD-S80-NEW-16 (S3 priority) — `/etc/logrotate.d/meridian` exists only on the box: third instance of on-box-only infrastructure after the crontab and the systemd units

| Field | Value |
|---|---|
| **Priority** | **S3.** Nothing breaks. A disaster rebuild silently loses log rotation, which is how the volume filled in the first place. |
| **Discovered** | Session 80 (2026-09-22), on widening the rotation scope. |
| **Component** | `/etc/logrotate.d/meridian` on `i-0878c118835386ec2` |
| **Symptom** | The config was edited this session — scope widened from `cron.log` + `logs/*.log` to `/home/ssm-user/meridian-engine/*.log` + `logs/*.log`, which is what finally caught a **313,728,377-byte** `shadow_runner.log`. The edit has **no diff, no review and no presence in a fresh clone**, and its backup `.PRE_20260922` sits beside it on the same volume. |
| **Root cause** | Same as the crontab before S68 and the systemd units still: infrastructure that lives only where it runs. **§S68 solved this for the crontab** by committing `docs/registers/aws_crontab.txt`; **§S74.B recorded the identical gap for twenty systemd units and three timers** and it was never closed. |
| **Proper fix** | Copy the live file to `docs/registers/logrotate_meridian.conf` and commit it, per the S68 precedent — noting §S68 needed a `.gitignore` negation to land `aws_crontab.txt`, so check `git check-ignore -v` rather than trusting an empty `git status`. Close the systemd half in the same pass or it becomes a fourth instance. |
| **Cost to fix** | Minutes. |
| **Blocked by** | nothing. |
| **Cross-ref** | Deployment Topology §S68 (the crontab precedent) · §S74.B (the systemd units, open) · §S80.6 · TD-S72-NEW-14 (no canonical tracked crontab source) · TD-S73-NEW-1 (CLOSED by this session's widening). |
| **Status** | **OPEN.** |

### TD-S79-NEW-1 (S2 priority) — `GREATEST(dte, 1)` overstates σ on expiry day, so the moneyness band is widest on the day it most needs to bind

| Field | Value |
|---|---|
| **Priority** | **S2.** Behavioural, on a live operator surface, and loosest in exactly the wrong direction. Not data loss, so not S1. |
| **Filed** | 2026-09-15 (Session 79) |
| **Component** | `sql/2026-09-15_s79_v_gex_strike_walls.sql` · view `v_gex_strike_walls` |
| **Symptom** | NIFTY was `dte=0` at the 09:50:05 gate run with ~5.5 h of session remaining. σ is `spot × atm_iv/100 × sqrt(GREATEST(dte,1)/252)`, so the floor substituted **a full trading day for a fraction of one**, giving σ = 245.2 where true remaining-time σ is materially smaller. |
| **Consequence** | band = 1.5σ is therefore **widest on expiry day** — the day on which stale far-OTM round-strike OI is most able to win an unbounded argmax. That contamination is the *only* thing the band exists to remove, so the control is loosest precisely where it is load-bearing. |
| **NOT a defect against its own calibration** | The 1.5σ sweep carried the same floor, so the view reproduces what was measured and the equivalence gate passed honestly. The corollary **is** the finding: the floor's effect is **baked into the 1.5** rather than separately visible, and re-deriving the band under a corrected σ would not necessarily yield 1.5. |
| **What it does NOT inherit** | This layer is raw-OI and touches gamma **nowhere**, so it does not inherit the 0-DTE gamma singularity that makes expiry-day flat-vol `net_gex` numerically unreconstructible (S62 settled entry). The OI wall is well-defined at `dte=0`; only the σ *scale* is wrong. |
| **Proper fix** | Replace the day floor with intraday remaining-time (fraction of session remaining at `ts`), then **re-run the 1.0 / 1.5 / 2.0 / 3.0 / unbounded sweep under the corrected σ**. The chosen band may move. |
| **Cost to fix** | ~1 session. The σ change is minutes; the re-sweep is the work, and it is an ADR-009 recalibration — SQL to `docs/research/` first. |
| **Cross-ref** | ENH-120 · commit `10a7ae5` · CLAUDE.md settled entry on 0-DTE `net_gex` unreconstructibility. |
| **MEASURED S80 — the overstatement is TIME-VARYING, and it HIDES an intraday effect** | The floor is not a constant scale error. σ_correct/σ_stated = `sqrt(mins_left/375)`, measured on 11,795 stored runs by IST hour: **0.982 at 09:00, 0.898 at 10:00, 0.804 at 11:00, 0.697 at 12:00, 0.570 at 13:00, 0.404 at 14:00, 0.203 at 15:00** — roughly **2 % at the open and ~5× by 15:00**. The consequence is worse than mis-scaling: under the shipped day-σ the 0-DTE pin↔max-pain gap looks **flat** through the session (median −0.398 → −0.224), while under correct remaining-time σ it **more than doubles** (−0.382 → −0.939). **The convention makes a widening gap look stable on the one day the layer matters most.** |
| **Second S80 note — dispersion, not the median** | 0-DTE carries the **tightest** IQR in the sample (NIFTY 0.199, SENSEX 0.254, against 0.32–0.41 elsewhere) while its median sits with every other cell at ≈ −0.32σ. That apparent convergence is at least partly this defect: an inflated denominator compresses the ratio toward zero. **It is not independent evidence of expiry-day convergence and must not be cited as such until σ is corrected.** |
| **Status** | **OPEN — and stronger than as filed.** The S80 measurement supplies the re-sweep's motivation: the chosen 1.5 band was calibrated under this floor, so re-deriving it under intraday σ may not return 1.5. |

---

### TD-S79-NEW-5 (S2 priority) — the deploy-direction inversion, third and fourth instances: two independent commits of identical content in two trees requiring a rebase, then a commit originated on EC2 and pushed to `main`

| Field | Value |
|---|---|
| **Priority** | **S2.** Recurring, and each instance costs a reconciliation. Unratified across four sessions. |
| **Filed** | 2026-09-15 (Session 79) |
| **Component** | `/home/ssm-user/meridian-cc` · `/home/ssm-user/meridian-engine` · ADR-006 · Doc Protocol v4 deploy line |
| **Symptom** | The S79 SQL was committed in `meridian-cc` (`10a7ae5`), then **copied and committed again** in `meridian-engine` (`dd0978f`) — identical content, identical message, different SHA and different parent. The canonical vector is **commit → push → pull**. Resolution required `git pull --rebase`, which reported `skipped previously applied commit dd0978f` and dropped the duplicate; both trees and `origin/main` then landed on `10a7ae5` with linear history. |
| **A measurement taken and not carried into the conclusion** | After both trees were committed, Claude measured the blob identity — `cdc3d35` on both sides — and then, in the same message, predicted the divergence would cause an **add/add conflict that stops the pull**, recommending `git reset --hard origin/main` as the remedy. Both were wrong: git conflicts on add/add only when contents **differ**, so identical blobs merge silently. The disproof was sitting in the measurement taken three lines earlier. Corrected the following turn, and the actual reconciliation (`git pull --rebase`) reported `skipped previously applied commit dd0978f` exactly as the corrected reading predicted. **Attribution note:** the operator offered to record this as an operator-side error; the transcript shows the prediction and the `reset --hard` recommendation were both Claude's, and the register keeps the accurate attribution. The lesson is unchanged and is the one worth keeping — *a measurement taken and not carried into the conclusion is the same as a measurement not taken.* |
| **Fourth instance — 2026-09-16, the S79 doc-close completion pass** | `1b317c0` (Decision Index + Assumption Register + System Map, the Rule 11 completion) was **authored in `/home/ssm-user/meridian-engine` on EC2**, pushed to `origin/main`, and Local took it by `git pull --ff-only`. **Cost this time: none** — no duplicate commit, no rebase, linear history, three refs level, all three files sha256-matching across trees. **That is exactly why it is worth recording.** The third instance was expensive and therefore visible; the fourth was clean and therefore invisible, which is how an unratified practice becomes the de-facto convention without anyone deciding it. Instances 3 and 4 are **not the same defect** — 3 is a duplicate-commit reconciliation, 4 is the direction itself — and only 4 is the one the ratification question is actually about. |
| **Standing status** | **UNRATIFIED across S73, S74, S79 and the S79 doc-close completion pass.** The open question is whether EC2 trees may originate commits at all, or only receive them — and the fourth instance sharpens it, because a clean EC2-origin push costs nothing and so supplies no pressure to decide. **A practice that works is ratified by default unless someone writes it down.** |
| **Proper fix** | Ratify or reject the inversion, amending **ADR-006 and the Doc Protocol deploy line together** — they must not disagree, which is the ADR-020 contract-collision lesson applied to process rather than code. |
| **Cost to fix** | ~1 session (one ADR amendment + one protocol line + a sweep for contradicting prose). |
| **Cross-ref** | ADR-006 · ADR-020 (two modules each authoring the same contract) · S73/S74 doc-close footers. |
| **Status** | **OPEN.** |

---

### TD-S79-NEW-6 (S3 priority) — three untracked scratch files sit in the production tree

| Field | Value |
|---|---|
| **Priority** | **S3.** Hygiene. They are untracked, so they ship nowhere and break nothing. |
| **Filed** | 2026-09-15 (Session 79) |
| **Component** | `/home/ssm-user/meridian-engine` working tree |
| **Symptom** | `git status` reports `rate_sens.out`, `s6_greeks.json`, `status.json` as untracked. All three **predate Session 79** and were not created by it. |
| **Why it matters at all** | The repo root is already a flat namespace of 501 `.py` files in which production and scratch are indistinguishable by name (S72 finding). Loose untracked output files add to the same ambiguity, and untracked scratch in a production tree is one `git add .` away from being committed. |
| **Proper fix** | Identify each file's producer, then either `.gitignore` it by name or move it under a scratch directory. Do **not** blanket-ignore the extensions — TD-S68 records a `.gitignore` pattern (`*.txt`) silently swallowing a committed-by-intent manifest with no untracked listing at all. |
| **Cost to fix** | ~15 min. |
| **Cross-ref** | S72 flat-namespace finding · TD-S78-NEW-2 (tracked backup artefacts, the mirror problem) · `git check-ignore -v` is the only reliable tell. |
| **Status** | **OPEN.** |

---

### TD-S79-NEW-7 (S3 priority) — the S74 Doc Protocol amendment cites a rule number belonging to a different rule, and amends a rule the named document does not contain

| Field | Value |
|---|---|
| **Priority** | **S3.** Record-keeping, not behaviour — the amendment's substance is sound and is being followed. But the citation is unusable, and a literal application lands on the wrong rule. |
| **Filed** | 2026-09-15 (Session 79) |
| **Component** | `CLAUDE.md:982` (v1.51 / Session 74 footer) · `docs/operational/MERDIAN_Documentation_Protocol_v4.md:53`, `:393` |
| **Symptom** | `CLAUDE.md:982` records: *"One standing rule amended — **Doc Protocol v4 Rule 7: register updates are applied as byte-level splices with fail-loud assertions, not full-file rewrites**."* But v4 `:53` (the preserved-unchanged rule index) and `:393` (the rule's own heading) **both** define Rule 7 as *"`CURRENT.md` is the live session resume (UNCHANGED FROM v3)"*. |
| **Worse** | **v4 contains no full-file-rewrite rule at all.** Grepping `rewrite\|rewritten\|byte size\|line count` across the document returns nothing in its rule set, and the rule index runs Rule 0–8 with none concerning rewrite-versus-splice. The amendment therefore names a rule that is about something else **and** amends a rule that does not exist in the document it names. |
| **Also unsourced** | The S79 filing brief instructed *"Doc Protocol v4 applies: full-file rewrites."* That premise is sourced to nothing — v4 is silent on the question. The **only** recorded guidance on rewrite-versus-splice anywhere in the corpus is the S74 amendment itself, which is why its citation being broken matters more than it would for a rule with an independent home. |
| **Consequence** | Anyone applying "Rule 7 as amended" literally gets `CURRENT.md`'s rule and no guidance on registers. The splice discipline survives only because the amendment quotes its own substance in full alongside the wrong number — i.e. it is self-describing by accident, not by citation. |
| **Root cause** | The amendment was recorded in a session footer rather than in the protocol it amends, so nothing forced a check against the target document's rule numbering. Same shape as TD-S79-NEW-3 one level up: a correction shipped to the narrative layer instead of the layer it governs. |
| **Proper fix** | Either renumber the amendment against whichever v4 rule it actually modifies, or — more likely correct — **record it as a NEW v4 rule with its own number**, added to the rule index at `:40–56`, since no existing rule covers the ground. Then correct the `CLAUDE.md:982` citation in place. Do not restamp the substance; it is sound and is what S79 followed. |
| **Cost to fix** | ~20 min (one protocol rule + one index row + one footer citation correction). |
| **Cross-ref** | `CLAUDE.md:982` · v4 `:53` / `:393` · TD-S73-NEW-8 (the file-size problem the amendment exists to mitigate) · S78 precedent — *"a protocol amendment recorded in the register that implements it, not an ADR"* (CLAUDE.md:377), which is the same recording pattern and carries the same citation risk. |
| **Status** | **OPEN.** |

---

### TD-S79-NEW-8 (S2 priority) — SENSEX has no gamma at all on ~30 % of its strikes, so every per-strike gamma layer on SENSEX is computed over ~70 % of the chain

| Field | Value |
|---|---|
| **Priority** | **S2.** Not data loss and nothing is presently mis-stated, but every gamma-derived surface on SENSEX is computed over a partial chain and none of them says so. |
| **Filed** | 2026-09-15 (Session 79) |
| **Component** | `gex_strike_snapshots` · `compute_gamma_metrics_local.py` (`signed_gamma_exposure`, `build_gss_rows`) · consumers `v_gex_strike_pin_zone`, `v_gex_strike_accel_zone`, `gamma_concentration`, `pin_risk_score` |
| **Symptom** | `gex_cr = 0` has **two** paths — the deep-ITM guard (which requires `|gamma| > 5e-5`, i.e. gamma **present and large**) and a zero-gamma branch. Splitting them on the zeroed rows: NIFTY **64,183 zeroed = 10.8 %**, of which **≤ 8,940 (1.5 %)** is the guard and **≥ 55,243 (9.3 %)** has no gamma. SENSEX **323,550 = 35.1 %**, of which **≤ 47,878 (5.2 %)** is the guard and **≥ 275,672 (29.9 %)** has no gamma. |
| **Correction (S79, same session) — the 35.1 % headline blends two effects** | Contribution rate rises steeply with DTE on **both** symbols — NIFTY **65.8 → 94.3 → 97.0 %**, SENSEX **45.2 → 63.8 → 77.6 %** across the 0 / 1–2 / 3+ buckets — and the symbol gap persists at **every** bucket. The genuine **coverage** gap is therefore **~20 points**, measured at **3+ DTE where the DTE effect is smallest** (97.0 vs 77.6). The pooled 35.1 % **conflates coverage with expiry-day gamma collapse** and overstates the coverage component. The guard-vs-no-gamma split above is unaffected; only the headline magnitude is. |
| **The split is corroborated, not assumed** | The guard bounds match **TD-S75-NEW-1's independently-taken monthly counts** almost exactly — SENSEX Jun–Sep sums to **46,724** against a bound of **47,878**. S75's counts were right. ADR-024 v2's headline "35 % guard" conflated the two zero-paths and **inflated the guard ~7×**; that figure is withdrawn in ADR-024 §A3. |
| **Why this is the finding and not the guard** | A filtering question is about rows you have and chose to exclude. This is about rows where **the input was never there**. The two are indistinguishable in `gex_cr` and were in fact confused for a full ADR revision. |
| **Consequence** | Every per-strike gamma layer on SENSEX — pin zone, accel zone, `gamma_concentration`, `pin_risk_score`, and anything downstream of them — is computed over **~70 % of the chain**, and no column, comment or panel records that. NIFTY's 9.3 % is the same defect at a third the magnitude. **ENH-120's OI walls are unaffected**: they are raw-OI and read `oi_call`/`oi_put`, which are populated independently of gamma. |
| **Cause unknown** | Candidates, **none tested**: vendor greeks absent on illiquid strikes; the writer's zero-noise drop (`build_gss_rows` skips rows with no OI either side **and** no GEX contribution); upstream chain gaps. **Do not pick one without measuring** — the guard/no-gamma conflation this entry corrects is exactly what happens when a plausible cause is adopted without a split. |
| **Proper fix** | Attribute the ≥ 275,672 SENSEX rows to a cause **before** deciding whether this is a defect at all. If it is vendor coverage on illiquid strikes it may be correct behaviour that merely needs recording; if it is the zero-noise drop it is a writer bug. The attribution is the work. |
| **Cost to fix** | ~half a session to attribute; unknown to remediate, because the remedy depends on the cause. |
| **Cross-ref** | ADR-024 §A3 · TD-S75-NEW-1 (the monthly counts that corroborate the split) · TD-S75-NEW-2 (cross-symbol replication defect, stays S2 and is a separate question) · ADR-015. |
| **Status** | **OPEN.** |

---

### TD-S79-NEW-9 (S2 priority) — `pin_risk_score`'s proximity component is ABSENT, not depressed, so the score silently changes basis between cycles

| Field | Value |
|---|---|
| **Priority** | **S2.** First consequence in ADR-024 touching a **scalar consumers read** rather than a band they draw. Two cycles can report the same `pin_risk_score` computed over different weight totals, and the stored value does not distinguish them. |
| **Filed** | 2026-09-15 (Session 79) |
| **Component** | `compute_gamma_metrics_local.py:876-877` (factor), `:901-902` (append + weight), `:899-911` (assembly + renormalisation) — **all line citations verified against source 2026-09-15** |
| **Mechanism** | `spot_proximity_factor = max(0.0, 1.0 − (|spot − max_gamma_strike| / strike_step) / 3.0)` — linear decay to **zero at 3 strike-steps**. Weight **0.30** at `:902`. The component is appended only under `if spot_proximity_factor is not None` at `:901`, and the score renormalises over **available** weights at `:899-911`. |
| **The distinction that makes this S2** | A factor of **0.0 is not None**, so a zeroed factor is still appended and still drags the score down across the full 1.00 weight. The component **drops** — and the score renormalises over the remaining 0.70 — only when `max_gamma_strike` or `strike_step` is None. **Both regimes occur, and the stored scalar cannot be told apart between them.** A score of 40 computed over 1.00 weight and a score of 40 computed over 0.70 weight mean different things. |
| **Measured, recomputed independently rather than quoted** | At S74's measured mean anchor distances: NIFTY 0.70 % × 24,000 = 168 pts ÷ step 50 = **3.36 steps** → `max(0, 1 − 3.36/3)` = **0**. SENSEX 0.79 % × 81,000 = 640 pts ÷ step 100 = **6.4 steps** → **0**. The factor is **zero on both symbols at typical anchor distances**, and ADR-024 §A2 finds the anchor structurally sits ~half an expected move **above** spot — so this is most cycles, not an edge case. |
| **Consequence** | `pin_risk_score` is a 0–100 scalar rendered to the operator with no basis annotation. Its proximity input is dead at typical distances, and whether it is dead-as-zero or dead-as-absent depends on a nullability that nothing surfaces. |
| **Proper fix** | Persist which components contributed (a small JSON or a bitmask alongside the score), **or** hold the basis fixed by always appending proximity with an explicit sentinel. Do not "fix" the decay constant without first deciding what the score is supposed to mean at 3+ steps — that is a design question, not a tuning one. |
| **Cost to fix** | ~1 session including the design decision; ~20 min for the instrumentation alone. |
| **Cross-ref** | ADR-024 §A7, §A2 · ADR-017 (the score is an operator-console surface) · TD-S79-NEW-11 (same family: a console reading the wrong scale). |
| **Status** | **OPEN.** |

---

### TD-S79-NEW-11 (S3 priority) — ADR-017 Principle 6 is right about the bug and wrong about the cause: it is a DTE difference, not a symbol difference

| Field | Value |
|---|---|
| **Priority** | **S3.** The principle's conclusion (differentiated rendering is needed) is correct, so nothing downstream is wrong today. Its stated **reason** is wrong, and anyone implementing from the reason will key the salience function on the wrong variable. |
| **Filed** | 2026-09-15 (Session 79) |
| **Component** | `docs/decisions/ADR-017-operator-console-design-principles.md` Principle 6 |
| **What P6 says** | Its worked example — NIFTY max γ **+0.15 %** vs SENSEX **+0.6 %** *"on the same day"* — reads as a **symbol** difference requiring symbol-differentiated rendering. |
| **What it is** | A **DTE** difference, measured on a day when the two symbols were at different DTEs. Over ~5,670 runs per symbol, expressed in σ (`σ = spot × atm_iv/100 × sqrt(GREATEST(dte,1)/252)`): 0-DTE **0.359 NIFTY / 0.342 SENSEX**; 1–2 DTE **0.587 / 0.586**; 3+ DTE 0.500 / 0.410. The 1–2 DTE pair agrees within **0.001σ** and the 0-DTE pair within **0.017σ** — **at spot levels 3.2× apart.** |
| **Why percent manufactured the finding** | In percent the spread across DTE is **2.8× and monotone**, which looks like a real and orderly effect. In σ it is **1.6× and non-monotone**, with IQRs of 0.20–0.41σ, comfortably inside half an expected move. The symbol asymmetry was percent-scale noise. |
| **The method note worth keeping** | **A board read in percent will keep manufacturing findings of this shape.** S75 said so before the σ work confirmed it, and ADR-024 §A4 withdrew an entire T3 finding for the same reason. |
| **Proper fix** | Amend ADR-017 P6: keep the conclusion, replace the cause, and specify that the salience function keys on **DTE and distance-in-σ**, never on symbol. A symbol-keyed implementation would be correct on the example day and wrong on every day where the two symbols share a DTE. |
| **Cost to fix** | ~20 min (one principle amendment). |
| **Cross-ref** | ADR-024 §A4 · ADR-017 P6 · TD-S79-NEW-9 (the other console-scale item) · ENH-120 (ships σ columns alongside points for exactly this reason). |
| **Status** | **OPEN — P6 amendment owed.** |

---

### TD-S79-NEW-15 (S2 priority) — the L3 flip gate is algebraically degenerate: "spot above the flip" and "TotalGEX(spot) > 0" are the same proposition, so the gate cannot fail for the reason it names

| Field | Value |
|---|---|
| **Priority** | **S2.** The gate PASSED (89.4 % / 90.4 % against an 80 % threshold) and that pass is input to a pending build decision. A check that cannot fail for the reason it names is not a check (**Rule 0 clause 0**) — the decision would rest on evidence the measurement did not produce. Nothing is shipped, which is why S2 and not S1. |
| **Filed** | 2026-09-16 (Session 79) |
| **Component** | S79 L3 measurement (scratchpad `l3_repriced_flip.py`, `l3_tautology.py`). **No production component — nothing was built or committed.** |
| **Symptom** | The gate asks whether `net_gex > 0` coincides with spot **above** the repriced flip. The repriced flip is *defined* as the zero of `TotalGEX(P)`, and `TotalGEX(P)` is monotone through that zero across the sample. So `(spot > flip)` and `(TotalGEX(spot) > 0)` are **the same statement**. Measured directly: identical on **42/42 NIFTY (100 %)** and **41/42 SENSEX (97.6 %)**. |
| **What the gate actually measured** | Whether **BS-repriced gamma from OCS `iv` reproduces the sign of vendor Dhan gamma** in `gamma_metrics.net_gex`. That reconstruction-fidelity check, evaluated at `P = spot`, scores **87.5 % NIFTY / 88.2 % SENSEX**. The gate scored **89.4 % / 90.4 %** — *at its own ceiling*, which is the signature of the degeneracy, not a coincidence. Residual disagreement concentrates at DTE=0 (84.0 % / 79.1 % vs 90.9 % / 96.5 % at DTE 1–2), consistent with the settled S62 finding that 0-DTE flat-vol reconstruction is numerically singular. |
| **The comparison that does survive, corrected** | The shipped `flip_level` fails the same gate, but **not at the 1.8 % / 1.0 % the S79 brief quoted.** Full window `ts >= 2026-05-25`: **NIFTY 20.8 % (n=5096), SENSEX 25.1 % (n=5149)**, against independence baselines of **28.8 % / 40.3 %**. The **1.8 % is NIFTY's 2026-06 value, misreported in the brief as the window value**; the series is non-stationary and rises monotonically. |
| **Caveat — the 20.8 % / 25.1 % pool two different constructions (added S79 after the source read)** | `gamma_metrics.flip_level` is **not one construction**. LONG cycles emit a cumulative-crossing nearest spot (`compute_gamma_metrics_local.py:392-436`); SHORT cycles emit a **per-strike sign-flip** nearest spot (`:303-335`) that never forms a cumulative sum at all — see TD-S79-NEW-17. The full-window figures above **pool both**, at roughly **NIFTY 74.5 % LONG / 25.5 % SHORT** and **SENSEX 63.1 % / 36.9 %**. They are therefore a property of the **column**, not of either construction, and a per-regime split is required before either can be characterised. **This does not disturb the finding that the shipped flip fails the gate** — it disturbs any attempt to attribute that failure to a particular construction, including the monthly trend below. |
| **Monthly trend (shipped flip, agreement vs independence baseline)** | NIFTY — 06: **1.8 %** vs 8.2 (Δ−6.4, n=716) · 07: 12.8 vs 31.2 (Δ−18.4, n=1844) · 08: 29.7 vs 31.4 (Δ−1.7, n=1709) · 09: 36.5 vs 38.5 (Δ−2.0, n=827). SENSEX — 06: **0.4 %** vs 33.3 (Δ−32.9, n=732) · 07: 19.8 vs 44.8 (Δ−25.0, n=1888) · 08: 35.2 vs 37.2 (Δ−2.0, n=1707) · 09: 38.3 vs 44.4 (Δ−6.1, n=822). |
| **Uninformative ≠ anti-correlated** | In 2026-06/07 the shipped flip sat **far below** independence — it carried *negative* information about the `net_gex` sign. In 2026-08/09 it sits **within 2.0 pp** (NIFTY) and 2.0–6.1 pp (SENSEX) of independence — it carries **essentially none**. Both fail. They are different diagnoses with different causes, and the register must not pool them into one number. |
| **What the L3 pass does NOT establish** | That the flip level has **market meaning** — that price behaves differently above it than below it. No forward-outcome measurement was taken, and **the gate as specified cannot take one.** Any build decision citing 89.4 % / 90.4 % as evidence of predictive value is citing it for something it did not measure. |
| **What would make a real check fire** | An **outcome** test: realised volatility, or absolute forward return over a fixed horizon, conditioned on which side of the flip spot sits — pre-registered per ADR-009, with the failing result stated before measuring. A real defect (the flip is not a regime boundary) produces no separation between the two conditions. |
| **Cost to fix** | Gate redesign ~0.5 session; the outcome study is separate and ADR-009-governed. |
| **Cross-ref** | **Rule 0 clause 0** (the governing rule — clean instance) · ADR-009 · S37 GEX-as-context-not-gate · S62 (0-DTE singularity) · TD-S79-NEW-16 · TD-S79-NEW-17 (the construction conflation) · TD-S79-NEW-18. |
| **Status** | **OPEN.** |

---

### TD-S79-NEW-16 (S3 priority) — the repriced flip lands ~3× closer to spot than the published landmark, and the divergence survives the σ bias that would explain it away

| Field | Value |
|---|---|
| **Priority** | **S3.** Both figures are measured and neither is known wrong. The divergence is **unexplained** and bears on whether either construction locates a real level. No behaviour depends on it today. |
| **Filed** | 2026-09-16 (Session 79) |
| **Component** | S79 L3 measurement vs the S79 cumulative-construction measurement. No production component. |
| **Symptom** | Distance from spot in σ (`spot × atm_iv/100 × sqrt(GREATEST(dte,1)/252)`): repriced flip **median 0.135σ NIFTY (n=161) / 0.126σ SENSEX (n=179)**. Hedgewall's published worked example sits at **0.54σ**. The repriced flip is roughly **3–4× closer to spot**. In price terms: median **0.16 % of spot (NIFTY) / 0.11 % (SENSEX)**, p90 0.45 % / 0.48 %. |
| **The bias that would explain it away, measured rather than assumed** | σ here uses `GREATEST(dte,1)` — the exact form **TD-S79-NEW-1** records as *overstating* σ on expiry day. An overstated σ **understates** the σ-distance, and DTE=0 is a third of the sample, so the headline is biased **in this finding's own favour**. Split by bucket: NIFTY DTE=0 **0.066σ** (n=50), 1–2 **0.258σ** (n=44), 3+ **0.135σ** (n=67); SENSEX **0.056** (n=67) / **0.171** (n=57) / **0.188σ** (n=55). **Excluding DTE=0: NIFTY 0.182σ (n=111), SENSEX 0.171σ (n=112).** The gap to 0.54σ narrows from ~4× to ~3× and **does not close.** |
| **CAVEAT — the 0.50–0.75σ comparator is WITHDRAWN, not caveated** | The brief also cited a **0.50–0.75σ modal bin** for the cumulative construction's nearest crossings on both symbols. That figure is **not used here**: it comes from the same measurement whose SENSEX leg does not reproduce (**TD-S79-NEW-18**), and that construction's crossing is structurally just above spot by arithmetic (call-OI heaviness 0.34 % below spot, 99.5 % above), so its σ position is an artefact rather than an independent reading. **This entry stands against Hedgewall's 0.54σ alone, and is weaker for it.** |
| **Secondary evidence, same family** | Between consecutive runs the flip moves **1.66× as much as spot** on NIFTY (median abs Δflip 0.112 % vs abs Δspot 0.068 %) and ~1:1 on SENSEX (0.077 % vs 0.081 %). A level sitting 0.11–0.16 % from spot and moving at least as fast as spot **changes the regime call on small moves**; it is not a slow-moving reference. |
| **What is NOT claimed** | That the repriced flip is wrong. **Ladder sensitivity was tested and is negligible** — agreement 88.3 % at every one of ±5 / ±10 / ±20 % and 30 / 60 / 120 levels (NIFTY); median flip shift vs base ≤ 0.03 % of spot; crossing availability **100 %** on both symbols; multi-crossing 0.0 % / 0.6 %. The construction is stable and well-posed. It lands somewhere other than the landmark. |
| **Proper fix** | Reconcile the σ definition against Hedgewall's *before* treating 0.54σ as a target, and measure this flip's distance distribution against a **forward-outcome** test rather than against another construction's number. |
| **Cost to fix** | ~0.5 session to reconcile σ; the outcome test is TD-S79-NEW-15's. |
| **Cross-ref** | TD-S79-NEW-15 · **TD-S79-NEW-1** (the σ form; bias quantified above) · TD-S79-NEW-18 (why the 0.50–0.75σ comparator is withdrawn) · ENH-120 (ships σ columns) · ADR-024 §A4. |
| **Status** | **OPEN.** |

---

### TD-S79-NEW-17 (S2 priority) — the rebuilt cumulative crossing and the shipped `flip_level` are not the same construction and never produce the same level: 0/97 and 0/105 exact matches

| Field | Value |
|---|---|
| **Priority** | **S2.** Two quantities were treated as one in the brief that framed a replacement decision. Every measurement taken against the reconstruction was therefore **not** a measurement of the column proposed for replacement. Nothing is shipped or broken, which is why S2 and not S1. |
| **Filed** | 2026-09-16 (Session 79) |
| **Component** | `gamma_metrics.flip_level` (shipped) vs a rebuilt `cumsum(gex_cr)` sign-change over `gex_strike_snapshots`. |
| **Symptom** | The S79 brief states that *"the shipped `flip_level` and the rebuilt cumulative-crossing version **both** compute where a running total of `gex_cr` across strikes changes sign"*, and measured the rebuilt one over `gex_strike_snapshots`. **They are not the same construction.** That conclusion rests on the code read recorded in **Mechanism** below — **not** on the exact-match count, which is demoted here from headline evidence. **The count, and why it cannot carry the claim:** comparing the shipped column against the rebuilt crossing on the same runs returned **0/97 NIFTY and 0/105 SENSEX exact matches**. That comparison was **operator-designed in premise** — the brief's assertion that the two were one construction is what made equality the test — and was implemented this session. **It is not clean.** The rebuilt side emitted the **strike itself**, un-interpolated and therefore always on the 50 / 100-point grid; the shipped side emits a **linearly interpolated price between bracketing strikes**, which is almost never on the grid; and the two were compared at a **1e-6 tolerance**. The count would be ≈0 even if the selection rule were byte-identical, so **it cannot support the claim it was originally carrying.** A clean re-measurement compares the chosen *interval*, or matches interpolation on both sides, or allows one strike-spacing of tolerance. |
| **Why this matters more than a discrepancy** | The brief's evidence for replacing the shipped `flip_level` was produced by measuring the **reconstruction**. Because the two are not the same level, **that evidence does not describe the shipped column.** The case for replacement has to be re-made against `gamma_metrics.flip_level` directly — which TD-S79-NEW-15 now does, and which yields 20.8 % / 25.1 % full-window rather than 1.8 % / 1.0 %. |
| **Mechanism** | **Read this session — `compute_gamma_metrics_local.py:338`.** With `spot` supplied (production always supplies it — **verified, all three live callers do**, see TD-S79-NEW-20) the function builds a cumulative sum of per-strike gamma from the **minimum strike upward**, then branches on regime. **`net_gex >= 0` (LONG):** walk **outward from the ATM index in both directions** — `atm_idx` at `:399`, the descending loop `:402-416`, the ascending loop `:418-432` — take the first cumulative sign change found in each, interpolate linearly between the bracketing strikes (`strike_prev + frac * (strike_curr - strike_prev)`), and return **`min(candidates, key=lambda x: abs(x - spot))` at `:436`** — the crossing **nearest spot**, not the first crossing. **`net_gex < 0` (SHORT):** the cumulative array is **abandoned entirely** at `:389-390` for `_flip_short_gamma_perstrike(strikes, strike_map, spot)` — **read this session at `:303-335`**, and it computes a **different quantity**, not a variant of the same one. It **never sums anything**: it takes the **raw per-strike signed GEX**, discards every strike below a relative noise floor at `:316-317` (see TD-S79-NEW-21), and finds where **individual strikes flip sign** — the pit-to-wall boundary named in its docstring at `:309` — where LONG finds where the **running cumulative total** crosses zero. It is also the **more exhaustive** of the two: it collects **all** crossings at `:321-332` and only then takes nearest-spot at `:335`, whereas LONG **breaks at the first crossing in each direction** and chooses among at most two. **LONG can therefore structurally miss a nearer crossing lying beyond a farther one; SHORT cannot.** (TD-S62-NEW / S63.) **`spot` absent or non-positive:** legacy fallback at `:365-384` — the bottom-up walk returning the **first cumulative sign change in either direction**; the naive construction, and per TD-S79-NEW-20 **unreachable in production**. **UNREAD: nothing remains.** Both markers carried by prior revisions — the LONG `return` past `:424` and `_flip_short_gamma_perstrike`'s body — are **lifted**. Every branch of the shipped construction has been read from source and is cited above. |
| **The shipped `flip_level` is THREE constructions, not one** | The column is a **regime-dependent union** of quantities that share a name, a unit and a column: LONG cycles emit a **cumulative-crossing nearest spot** (`:392-436`); SHORT cycles emit a **per-strike sign-flip nearest spot** (`:303-335`); the fallback's **first cumulative crossing in either direction** (`:365-384`) is unreachable in production. **Every S79 flip measurement pooled the first two.** On the session's regime split — **NIFTY ≈ 74.5 % LONG / 25.5 % SHORT, SENSEX 63.1 % / 36.9 %** full-window (figures as measured earlier this session; **not re-derived in this pass**) — roughly a quarter of NIFTY rows and over a third of SENSEX rows are the *other* construction. Any statistic over the column is therefore a **blend**, and a blend is a property of neither construction. TD-S79-NEW-15 carries the consequence for its own figures. |
| **Correction — "low-to-high" (mine)** | The fallback was described in the prior revision of this row, and in TD-S79-NEW-20, as returning the *"first **low-to-high** crossing"*. **Wrong.** `:378` tests `(cum_prev < 0.0 < cum_curr) or (cum_prev > 0.0 > cum_curr)` — the first crossing in **either** direction; replay's copy at `:251` is identical. The phrase originated in the S79 filing brief and propagated unchecked into both entries. Corrected in both, 2026-09-16. It does not disturb this entry's conclusion — the constructions still differ — but a reader reasoning from the wrong fallback rule would mis-predict which level it returns on a `+→−` crossing. |
| **Secondary** | The rebuilt construction produces **no crossing at all on 27 % (NIFTY) / 22 % (SENSEX)** of sampled runs, so it is not a drop-in substitute regardless. Sanity that does hold: `sign(sum gex_cr) == sign(net_gex)` at **99.0 % / 100 %** — the ADR-015 identity is intact and `net_gex` is not implicated. |
| **Proper fix** | **First clause — DONE (S79, 2026-09-16):** `compute_flip_level` was read; what the shipped column computes is recorded in **Mechanism** above. **Second clause — OUTSTANDING:** re-label any prior S79 finding that measured the reconstruction so it does not read as a finding about the shipped column. |
| **Cost to fix** | ~20 min to read the function and correct the labels; longer if prior register entries need amending. |
| **Cross-ref** | TD-S79-NEW-15 (the corrected shipped-column figures) · TD-S79-NEW-18 · **TD-S79-NEW-20** (replay pinned to the fallback branch read here; shares the "low-to-high" correction and carries the verified call-site set) · ADR-015 (the identity that holds). |
| **Status** | **OPEN.** |

---

### TD-S79-NEW-18 (S2 priority) — the SENSEX leg of the cumulative-gate result does not reproduce: 1.0 % against 34.3 %, and which measurement is wrong is UNRESOLVED

| Field | Value |
|---|---|
| **Priority** | **S2.** An unreconciled 34× divergence in the evidence base for a pending decision. **Filed as unresolved — neither figure is adopted.** |
| **Filed** | 2026-09-16 (Session 79) |
| **Component** | Rebuilt `cumsum(gex_cr)` crossing over `gex_strike_snapshots`, SENSEX. |
| **Figure 1 — operator-side, SQL written in-session, full population, NOT independently reproduced** | `ts >= 2026-05-25`: net GEX positive **99.0 %**, spot below flip **98.0 %**, agreement **1.0 %**. |
| **Figure 2 — this session, independent code path, sampled** | n=105 runs across the same window: `sum(gex_cr) > 0` **80.0 %**, spot below flip **45.7 %** (spot *above* 54.3 %), agreement **34.3 %**. Apart from Figure 1 by **34× on agreement and 52 pp on spot-vs-flip**. |
| **NIFTY reproduces; SENSEX does not** | On NIFTY the same sampled code path returns net>0 **99.0 %**, spot>flip **4.1 %**, agreement **3.1 %** — Figure 1's NIFTY sibling (99.9 % / 1.9 % / 1.8 %) in both shape and magnitude. **The divergence is SENSEX-specific**, which is itself the strongest clue. |
| **The two figures are NOT of equal standing** | Figure 1 is full-population and therefore not sampling-limited. Figure 2 is an independent implementation and therefore does not inherit Figure 1's assumptions. But Figure 1 was produced in-session and **has not been independently reproduced**, and it is Figure 1's **SENSEX leg specifically that fails to reproduce while its NIFTY leg does.** That asymmetry is evidence about where to look. It is not sufficient to declare a winner, and adopting either now would resolve the disagreement by preference rather than by evidence. |
| **Live mechanism, named not adopted** | **TD-S79-NEW-8** records that **SENSEX has no gamma at all on ~30 % of its strikes**. A cumulative walk over a chain with a third of its rungs missing is exactly the construction that would become unstable, and would do so on SENSEX only. This is a **candidate explanation, not a finding** — it has not been tested against either figure. |
| **The re-run that settles it** | Recompute the rebuilt crossing over the **full** `gex_strike_snapshots` SENSEX population for `ts >= 2026-05-25` in a **single** code path, emitting per-run: `sum(gex_cr)`, the crossing strike, `spot`, crossing-count, and **strike-coverage** (`count(gex_cr IS NOT NULL) / count(*)`). Stratify agreement by coverage decile. If TD-S79-NEW-8 is the mechanism, agreement moves with coverage; if it does not, the divergence is in the crossing rule and one of the two implementations is wrong. |
| **Cost to fix** | ~0.5 session for the re-run; remediation unknown until it lands. |
| **Cross-ref** | **TD-S79-NEW-8** (the ~30 % missing SENSEX gamma) · TD-S79-NEW-17 (the construction is not the shipped column either way) · TD-S79-NEW-15 · ADR-015. |
| **Status** | **OPEN — UNRESOLVED. Both figures recorded; neither adopted pending the named re-run.** |

---

### TD-S79-NEW-21 (S3 priority) — `_FLIP_DOMINANCE_EPS_FRAC` is a hardcoded magic number on a live operator surface, and it is relative to the run, so the strikes it discards move with the data

| Field | Value |
|---|---|
| **Priority** | **S3.** The constant is shipped and the SHORT-regime flip has been operator-facing since S63, so this is not hypothetical — but nothing is measurably wrong. **How much it discards has not been measured**, which is precisely why it is filed rather than acted on. S3, not S2, because the defect is governance and unmeasured reach, not a known error. |
| **Filed** | 2026-09-16 (Session 79) |
| **Component** | `compute_gamma_metrics_local.py:300` (`_FLIP_DOMINANCE_EPS_FRAC = 0.01`), applied at `:316-317` inside `_flip_short_gamma_perstrike` (`:303-335`). Reaches `gamma_metrics.flip_level` on every `net_gex < 0` cycle, and through it the Marketview positioning read and the Pine overlay. |
| **Symptom** | `eps = _FLIP_DOMINANCE_EPS_FRAC * max_abs`, and `:317` **discards every strike whose `abs(value)` falls below `eps`** before the sign-flip walk runs. The surviving list is what the crossing search sees. The constant is **not in `merdian_parameters`**, carries **no `// swap for ENH-83 lookup` marker** of the kind the τ constants were given, and appears in no register. It is exactly the class **ADR-016 was written for** and **ENH-83 built the parameter table to hold**. |
| **Why the relative form matters more than the value** | The floor is **1 % of the largest absolute per-strike GEX in that run**, not an absolute quantity. So **the threshold moves with the data**: a run dominated by one large strike sets a high floor and discards much of the chain; a flat run sets a low floor and discards little. The number of strikes removed is therefore **regime-dependent and uncontrolled**, and two cycles hours apart can search very different candidate sets while reporting the same column. This is the **ADR-016 §regime-conditional-threshold** shape — the reason S37 refused derived booleans at the write layer. |
| **Interaction with TD-S79-NEW-8** | SENSEX already has **no gamma at all on ~30 % of its strikes**. A relative floor applied on top of that operates over an already-truncated chain, so the two truncations compose. Neither entry has measured the combined effect. |
| **What is claimed, and what is NOT** | **Claimed:** the constant exists at `:300`, is applied as described at `:316-317`, is absent from `merdian_parameters`, and is relative rather than absolute. All read from source. **Not claimed:** that it discards too much, too little, or that any shipped flip is wrong because of it. **No measurement of its reach was taken** — the drop count per cycle, and whether the discarded strikes ever bracket a crossing that would have been nearest spot, are both unknown. |
| **Proper fix** | **Measure first, parameterise second.** (a) Instrument one window: strikes in, strikes surviving `:317`, and whether the returned crossing would change at eps ∈ {0, 0.005, 0.01, 0.02}. A real defect shows the flip moving materially at plausible eps; if it does not move, the constant is inert and the finding is governance-only. (b) Then move it into `merdian_parameters` per ADR-016 with a non-empty `change_reason`, and leave the marker at the call site. **Do not tune it before (a)** — adjusting a threshold until output looks right is the failure Rule 0 clause 3 names. |
| **Cost to fix** | ~30 min for (a); ~20 min for (b) once the parameter table row exists. |
| **Cross-ref** | **ADR-016** (parameter calibration pattern; the class this belongs to) · **ENH-83** (`merdian_parameters`, SHIPPED S39 — the table it should live in) · TD-S79-NEW-17 (the SHORT branch this constant gates) · TD-S79-NEW-8 (SENSEX's ~30 % gamma-less strikes, which compose with this truncation) · TD-S62-NEW / S63 (the regression that introduced the branch). |
| **Status** | **OPEN — filed from a source read; reach unmeasured.** |

---

### TD-S79-NEW-24 (S3 priority) — Doc Protocol v4 Rule 11.3's governance-footer obligation is unenforced, and compliance cannot be counted because a footer is not required to cite its ADR

| Field | Value |
|---|---|
| **Priority** | **S3.** Nothing running is affected. It is filed because Rule 11.3 is a *gate* — *"ADRs without a clean one-line governance footer are not ready for acceptance"* — and a gate nobody can evaluate is not a gate. |
| **Filed** | 2026-09-16 (Session 79, doc-close completion pass) |
| **Component** | `docs/operational/MERDIAN_Documentation_Protocol_v4.md` §11.3 and the *Index health checks* section of `docs/decisions/MERDIAN_Decision_Index.md` (third bullet: *"Verify the CLAUDE.md 'Things that are settled' footer contains a one-liner for every ADR in this index"*). |
| **Symptom** | **One confirmed non-compliant ADR, five suspected, and no way to tell the two apart.** Confirmed from the ADR side: **ADR-024** has no `## Governance language` section at all — zero hits for *"governance"* across all 35,064 bytes, parent and Amendment alike — so no footer could be written for it without authoring the decision's governing sentence, and it was left unwritten this pass for that reason. Suspected from the `CLAUDE.md` side: **ADR-007, ADR-011, ADR-021, ADR-022 and ADR-024** hold Index rows and have **no bullet naming them** anywhere in the settled-decisions block. |
| **Why the suspected five cannot be promoted to confirmed** | **A governance footer is not required to cite its own ADR id, and most do not.** Measured over the `## Things that are settled — DO NOT REOPEN` block (`CLAUDE.md:239–379`): **120 bullets, of which only 33 name any `ADR-NNN` — 87 name none.** So *"no bullet names ADR-NNN"* and *"ADR-NNN has no footer"* are **different propositions**, and a `grep` over ids cannot separate them: a footer stating the decision in its own words is fully compliant and invisible to the search. Settling the five requires reading each unnamed bullet against each ADR's Decision section — 87 comparisons, not a script. **This entry therefore asserts only what was measured**, per the D.35.1–.4 absence-claim rule: a zero from a name search is evidence about names, not about presence. |
| **A boundary claim made this session and WITHDRAWN on measurement** | The Decision Index S79 footer and the S79 close both record that the check *"has no checkable answer"* because `CLAUDE.md`'s settled content splits across two regions **both carrying ✅-bulleted lines of the same kind**. **That is false, and it is Claude's own claim.** Measured: `- ✅ **` occurs **100 times inside `:239–379` and 0 times below it** — the marker discriminates the regions cleanly. (The block also holds **20 non-✅ bullets**, so the marker is a reliable *boundary* and not a reliable *definition*.) The region boundary is therefore **not** the obstacle; the citation convention one level down is. **The Decision Index footer and CLAUDE.md are left uncorrected in this pass** — correcting a claim in the register that records it is a separate, sourced edit, and this row is where the correction lives until then. |
| **Root cause** | Rule 11.3 specifies *where the text comes from* (the ADR's Governance-language section) and *where it goes* (the settled-decisions list), but never specifies **the form of the landed line** — specifically, whether it must carry the id that makes it traceable back to its ADR. Without that, the linkage Rule 11 exists to create is one-directional: you can go from an ADR to its footer by writing one, but not from a footer back to its ADR, and so not from the Index to a compliance answer. The health check's third leg has, on the evidence of the S74 and S76 footers, **never been run** — both report only the rows/links leg. |
| **Workaround** | Treat an ADR's own `## Governance language` section — present or absent — as the checkable half of the obligation. It is the only half with an unambiguous test today, it is the half §11.3 actually gates on, and it is file-local. |
| **Proper fix — ordered, and the order is the point** | **(1) Fix the form, not the boundary.** Amend §11.3 to require the landed line to cite its ADR id (`ADR-NNN`), which is what makes the reverse check mechanisable at all; the `- ✅ **` marker is already a clean region discriminator and needs no decision. **(2) Then count.** With ids mandatory the reverse check is a few lines over the Index's ids and belongs in the Index health-check cadence — but it can only bind **going forward**, because retrofitting ids to 87 uncited bullets is the step-3 work, not a precondition for it. **(3) Then adjudicate the five**, by reading, ADR-007 first — and where the ADR has no Governance-language section (ADR-024), the outcome is an **acceptance decision, not a documentation task**. **Do not write a single footer before step 1**: doing so makes compliance the exception rather than the norm, which is the argument that kept ADR-024's footer unwritten this pass. |
| **Cost to fix** | ~15 minutes for step 1. ~0.5 session for step 2. Step 3 is ~87 bullet-to-ADR comparisons and should be scoped to the five suspected ADRs rather than run exhaustively. |
| **Blocked by** | Nothing for steps 1–2. Step 3 is blocked per-ADR on whether that ADR has a Governance-language section; for **ADR-024** it is blocked on the same single operator decision as its parent Status block (write the line and move `:5` to ACCEPTED, or demote Amendment A to PROPOSED). |
| **Cross-ref** | **Doc Protocol v4 §11.3 / §11.4** (the gate and the four-step order) · **ADR-024** (the one confirmed instance, from the ADR side) · ADR-007 / ADR-011 / ADR-021 / ADR-022 (suspected, unresolved by name search) · **TD-S79-NEW-26** (Rule 12's list — the sibling defect: a rule whose text and whose practice disagree) · **TD-S79-NEW-7** (the S74 amendment citing a rule number belonging to a different rule — the same family) · **D.35.1–.4** (the absence-claim insufficiency this row's own withdrawn claim instances) · Decision Index **S79 footer**, which carries the superseded boundary framing. |
| **Status** | **OPEN.** Measured during the S79 Rule 11 completion pass and filed in the same pass rather than carried forward — the exposure being recorded is precisely that findings living only in a transcript do not survive it. |

---

### TD-S79-NEW-25 (S2 priority) — there is no project-knowledge manifest, so Rule 12 compliance is undetectable by construction

| Field | Value |
|---|---|
| **Priority** | **S2.** It does not break a running system; it makes a known, recurring, *silent* failure mode impossible to detect — and that failure mode has already cost one full session's close (S69 → S70). Filed above the two protocol-text items because those are wrong *text*, and this is an absent *mechanism*. |
| **Filed** | 2026-09-16 (Session 79, doc-close completion pass) |
| **Component** | The Claude.ai project-knowledge upload set · `CLAUDE.md` Rule 12 · Doc Protocol v4 Rule 3 (final checklist line) and the *Cross-layer sync* section. |
| **Symptom** | The upload set — **~66 files, 5.5 MB, measured at the S78 close** — is maintained **by hand in a web UI with no on-disk record of its membership**. No session can enumerate what is supposed to be uploaded, diff the repo against it, or detect that a file changed in git and never reached project knowledge. The check that would catch the failure **cannot be written**, because its expected set does not exist anywhere a script can read. |
| **The failure mode this makes invisible** | A committed-but-unuploaded doc-close silently becomes the next session's baseline. **Recorded as D.28.9**: the S69 twelve-file close was committed (`8bc25b6`, `155430e`) and tagged, and was never re-uploaded; at S70 open, project knowledge still held the pre-S69 state — `CLAUDE.md` at 1,019 lines against 1,054 on disk. It was caught by a **byte-level hash check improvised at session open**, not by anything in the process. **D.28.9 records the instance; the mechanism has never been written down**, which is what this entry supplies. |
| **Live instance at filing time** | This very pass. `1b317c0` changed the **Decision Index, Assumption Register and System Map** — and **none of the three appears on Rule 12's re-upload list** (see TD-S79-NEW-26), so nothing in the protocol would prompt their upload. Until they land, the next session reads a Decision Index without ADR-024's row and a `§D.33.8` that still reads as an unqualified refutation. |
| **Root cause** | Project knowledge is a UI-side store with no API surface used by this project, so membership was never expressed as data. The Cross-layer sync section correctly states that git and project knowledge *"drift independently"* — and then leaves the reconciliation entirely to operator memory. |
| **Workaround** | Byte-level verification of a handful of files at session open, improvised per session (the S70 and S72 pattern). It works, it does not scale past the files someone thinks to check, and it runs **after** the damage rather than before. |
| **Proper fix** | **A one-line-per-file manifest committed to the repo** — e.g. `docs/registers/pk_manifest.md`, each line a repo-relative path plus the reason the file is in the set (S78's governing principle: *git is the archive, project knowledge is the retrieval surface* — a file belongs in PK only if it is read at session start or searched during a session). That single artefact converts Rule 12 from *remembered* to *checkable*: a doc-close can then diff `git diff --name-only <last-close>..HEAD` against the manifest and **print the exact upload list**, and a session open can verify the set rather than a guess. **The manifest does not automate the upload** — it makes the omission visible, which is the whole defect. |
| **Cost to fix** | ~0.5 session to enumerate the current set from the UI and commit it; near-zero to maintain, one line per added file. |
| **Blocked by** | Nothing technical. It needs one pass over the UI to read the membership out, which only the operator can do. |
| **Cross-ref** | **D.28.9** (the S70 instance, and the byte-check that caught it) · **CLAUDE.md Rule 12** · **Doc Protocol v4 Rule 3** final line and *Cross-layer sync* · **TD-S79-NEW-26** (the list Rule 12 does carry is itself wrong) · **TD-S73-NEW-8** (the duplication this set is large because of; S78's `CURRENT.md` split was partial remediation) · S78 close, where the 66-file / 5.5 MB / 92 % figures were measured. |
| **Status** | **OPEN.** |

---

### TD-S79-NEW-26 (S3 priority) — Rule 12's re-upload list omits five of the documents the session-end checklist requires to be updated, so following the rule literally leaves the reference layer stale

| Field | Value |
|---|---|
| **Priority** | **S3.** The practice is better than the rule, so the damage is bounded — but the rule is what an agent reads, and an agent following it literally under-uploads. |
| **Filed** | 2026-09-16 (Session 79, doc-close completion pass) |
| **Component** | `CLAUDE.md` Rule 12 and the *What Claude must do at session end* checklist · `docs/operational/MERDIAN_Documentation_Protocol_v4.md` Rule 3. |
| **Symptom** | Rule 12 names **six files plus a glob** — `CURRENT.md`, `session_log.md`, `merdian_reference.json`, `tech_debt.md`, `MERDIAN_Enhancement_Register.md`, `CLAUDE.md`, and *"any `docs/operational/*` file"*. It omits **ADRs**, **`MERDIAN_System_Map.md`**, **`MERDIAN_Deployment_Topology.md`**, **`MERDIAN_Assumption_Register.md`** and **`MERDIAN_Decision_Index.md`** — all five of which live in `docs/registers/` or `docs/decisions/` and are therefore outside the glob too. |
| **Why this is a contradiction inside the protocol, not merely an omission** | Doc Protocol v4 **Rule 3's session-end checklist** explicitly requires updating the System Map, the Deployment Topology, the Decision Index and the Assumption Register, and requires prepending a Decision Index row for every new ADR — and then closes with *"Re-upload modified files to Claude.ai project knowledge (per CLAUDE.md Rule 12)."* **Rule 3 defers the list to Rule 12, and Rule 12's list omits the very files Rule 3 has just mandated changes to.** The two rules compose into a gap, each being individually coherent — which is **ADR-020's contract-collision shape** applied to process rather than code. |
| **Demonstrated this pass** | `1b317c0` modified exactly three files, **all five-omitted-class**: Decision Index, Assumption Register, System Map. A session executing Rule 12 to the letter would have uploaded **nothing**. |
| **Root cause** | Rule 12 was written (S6→S7, 2026-04-22) before the six reference indexes existed — they arrive with Doc Protocol **v4 Rule 9**, a year of sessions later. Rule 3 was extended to cover them; Rule 12 was not, and nothing forced the two to move together. |
| **Workaround** | Upload what the session actually modified, not what Rule 12 lists — which is what recent doc-closes have done, on the evidence of their footers. The practice is correct and undocumented; the documentation is incorrect and authoritative. |
| **Proper fix** | Amend Rule 12's list to *"every file modified this session under `docs/`, plus `CLAUDE.md`"* — a rule stated over the **modified set** rather than an enumerated list cannot go stale as new documents are added, which is the defect that produced this entry. Amend **Rule 12 and Doc Protocol v4 Rule 3's final line together**, per the ADR-020 lesson that two documents must not separately author the same contract. **This is a protocol amendment, not an ADR** — the same classification as the S74 Rule 7 amendment and S78's method rule 6. |
| **Cost to fix** | ~15 minutes of text, plus the sweep for prose elsewhere that repeats the six-file list (the `CLAUDE.md` session-end checklist repeats it verbatim and must move in the same edit). |
| **Blocked by** | Nothing. Note that **TD-S79-NEW-25 is the more valuable of the pair** — correcting this list makes the rule right, but still leaves compliance unmeasurable without a manifest. |
| **Cross-ref** | **TD-S79-NEW-25** (no manifest — the mechanism half of the same problem) · **TD-S79-NEW-24** (Rule 11.3 unenforced — a rule whose compliance cannot be evaluated) · **TD-S79-NEW-7** (the S74 amendment citing a rule number belonging to a different rule) · **ADR-020** (two modules each authoring the same contract) · **Doc Protocol v4** Rule 3, Rule 9, Rule 12, *Cross-layer sync* · **D.28.9**. |
| **Status** | **OPEN.** |

---

### TD-S78-NEW-1 (S3 priority) — the session-date convention is unspecified in Doc Protocol v4, and the only format v4 does specify cannot express a multi-day session

| Field | Value |
|---|---|
| **Priority** | **S3.** Record-keeping, not behaviour. It makes cross-register joins on session date unreliable and every instance looks individually reasonable. |
| **Filed** | 2026-09-14 (Session 78) |
| **Component** | `docs/operational/MERDIAN_Documentation_Protocol_v4.md` · `CURRENT.md` · `merdian_reference.json` · `tech_debt.md` |
| **Symptom** | S77 ran across three days and is recorded three different ways: `CURRENT.md` **`2026-09-11 → 2026-09-13`**, `merdian_reference.json` **`2026-09-11/13`**, `tech_debt.md:4925` **`S77 (2026-09-11)`**. Two of the three cannot be parsed as the format v4 specifies. |
| **Evidence (verified S78)** | v4 specifies bare `YYYY-MM-DD` in four places and nowhere else: `:107` (`session_log` line format), `:329` and `:343` (`CASE-YYYY-MM-DD-<topic>.md`), `:553` (the `CURRENT.md` block's Date field). **No span format is specified anywhere in the document.** |
| **Correction to the filing brief** | The brief also cited `ADR-004:3` as a third rendering of the S77 span. It is not — that line reads *"Amendment C (2026-09-10)"*, which is Amendment C's **authoring** date in S76. The citation is withdrawn; the finding stands on the other three. |
| **Root cause** | A multi-day session was not anticipated when the format was written. Each author then invented a rendering, and each is locally defensible. |
| **Proper fix** | Amend Doc Protocol v4 to specify a span form (e.g. `YYYY-MM-DD..YYYY-MM-DD`) and state which date is canonical for sorting. **Fix by amending v4, not by restamping existing files** — restamping would edit history to match a rule that did not exist when it was written. |
| **Cost to fix** | ~20 min (one protocol amendment + one settled-decision line). |
| **Cross-ref** | Doc Protocol v4 `:107` / `:329` / `:343` / `:553`. |
| **Status** | **OPEN.** |

---

### TD-S78-NEW-2 (S3 priority) — 67 backup artefacts are tracked in git with no retention rule, and `.gitignore` cannot remove them because it does not untrack

| Field | Value |
|---|---|
| **Priority** | **S3.** Hygiene. This entry shrank under measurement twice and the final version is housekeeping, not exposure. |
| **Filed** | 2026-09-14 (Session 78) |
| **Component** | repo root (65 files) · `sql/` (2 files) · `.gitignore:101`, `:103`, `:108` |
| **Measured (S78)** | `git ls-files` matching `_PRE_S` / `.PRE_S` / `.pre_`: **67** — **65 in the repo root, 2 under `sql/`**. Widening to include `_PATCHED` and `.bak` gives **80**. Uppercase `_PRE_S<N>` spans **S15 → S42**. **18** are lowercase `.pre_*` forms matching no ignore pattern at all. |
| **The actual mechanism** | **`.gitignore` does not untrack files that are already tracked.** These 67 were committed before the ignore rules existed, so `*_PRE_S*` is simply irrelevant to them. Demonstrated within this session: the two backups S78 created (`build_data_inventory.py_PRE_S78`, `MERDIAN_Data_Inventory.md_PRE_S78`) are correctly ignored by `:108`, while 67 historical ones remain in the tree. The fix is therefore `git rm --cached`, **not** a new pattern. |
| **Claim REFUTED** | The brief asserted an asymmetry whereby `_PRE_S` is ignored and `.PRE_S` is not. **`.gitignore:108` is `*_PRE_S*` with no extension anchor** and correctly ignores every form, including a `.md`: all four S77 backups on disk (`CLAUDE.md_PRE_S77`, `build_ict_primitives.py_PRE_S77`, `ict_primitives.py_PRE_S77`, `ict_primitives.py_PRE_S77_postpatch`) are untracked. `:103` (`*_PRE_S*.py`) is redundant against `:108`. `:101` names `run_option_snapshot_intraday_runner_PRE_S44.py`, which is **not present**. |
| **Also** | `ict_primitives.py_PRE_S77_postpatch` (mode 600) is an S77 verification artefact with no cleanup step — see TD-S77-NEW-4. |
| **Proper fix** | Decide a retention rule (how many backups, for how long), record the naming convention, `git rm --cached` the tracked set, and delete the redundant `:103` and the stale `:101`. |
| **Cost to fix** | ~30 min. |
| **Cross-ref** | **TD-S77-NEW-4** (patch scripts gitignored). |
| **Status** | **OPEN.** |

---

### TD-S78-NEW-3 (S2 priority) — project knowledge round-trips LF to CRLF, so the Rule 12 hash comparison cannot distinguish an identical file from a missing upload

| Field | Value |
|---|---|
| **Priority** | **S2.** Rule 12 requires git and project knowledge to be treated as two destinations both required for session close. The obvious way to verify the second one reports the wrong answer with total confidence. |
| **Filed** | 2026-09-14 (Session 78) |
| **Component** | Claude.ai project-knowledge upload path · CLAUDE.md Rule 12 · Doc Protocol v4 hash discipline |
| **Symptom** | A byte or hash comparison between the working tree and the project-knowledge copy **always** differs, whether or not the upload is current. Every such comparison is therefore uninformative, and a genuinely stale upload is indistinguishable from a fresh one. |
| **Measured (S78)** | The project-knowledge byte count equals `disk_bytes + line_count` **exactly** for every file whose working tree is clean — `CURRENT.md` 749,576 + 3,076 = 752,652; `session_log.md` 630,386 + 1,182 = 631,568; `tech_debt.md` 793,911 + 4,926 = 798,837; `data_inventory_2026-09-08.md` 81,354 + 1,170 = 82,524; `iv_availability_2026-09-08.md` 19,820 + 419 = 20,239. **Five files, five exact matches**: one `\r` added per line. The tree carries **zero** CRLF. The only two that did not match (`CLAUDE.md`, `merdian_reference.json`) are exactly the two marked ` M` in `git status` — i.e. genuinely diverged. |
| **Consequence 1** | Hash comparison must normalise `\r\n` → `\n` on **both** sides before comparing. Un-normalised, it is not a check (CLAUDE.md Rule 0). |
| **Consequence 2** | Any splice anchor **spanning a newline** that is built from a project-knowledge copy will fail `count == 1` against the tree, and reads as *"the file changed underneath me"* rather than *"my anchor has the wrong line endings"*. Add the boundary to the anchor rule: **a project-knowledge file copy is rendered output for line-ending purposes**, the same way console output is (S71). |
| **Same class as** | **TD-S76-NEW-23** — the obvious check reporting the wrong thing with total confidence. Also the S72 cross-tier finding: byte size is valid only within one storage tier. |
| **Proper fix** | Normalise before hashing, both sides; state the tier whenever a byte baseline is quoted. |
| **Cost to fix** | ~15 min (one rule amendment). |
| **Status** | **OPEN.** |

---

### TD-S77-NEW-4 (S3 priority) — `/patch_*.py` is gitignored, so not one patch script in MERIDIAN's history is in version control

| Field | Value |
|---|---|
| **Priority** | **S3.** Unrecoverable for everything already written, and the registers describe what each patch did. The exposure is that a transformation is not the same artefact as a description of it. |
| **Filed** | 2026-09-11 (Session 77) |
| **Component** | `.gitignore:71` — `/patch_*.py` |
| **Symptom** | `patch_s36_enh99_v3.py`, `patch_s37_enh80_writer_v2.py`, `patch_s40_enh83_view_tau_rewrite.py`, `patch_s41_*` are all referenced by registers and **none is recoverable**. The registers say what each did; the transformation is gone. |
| **Where it matters and where it does not** | Tolerable for view DDL, which the view definition itself records. **Not** tolerable for a change whose output is an irreversible DELETE plus recompute — there the patch script is the only statement of what was done to the data. |
| **Action taken S77** | `patch_s77_f68_ts_close.py` was committed via `git add -f` as a named exception (`87ac537`), with the exception recorded in the commit subject. |
| **Proper fix** | A negation rule (`!/patch_s*.py`, or a `patches/` directory outside the pattern) rather than per-file `git add -f` — the force flag hides the problem for the next file, which is the S68 `.gitignore` finding verbatim. |
| **Cross-ref** | S68 settled decision (*`git status` clean ≠ file tracked*; fix with a negation rule, not `git add -f`) · **TD-S77-NEW-6**. |
| **Status** | **OPEN.** |

### TD-S77-NEW-7 (S3 priority) — `script_execution_log.host` is not evidence of which machine ran a script

| Field | Value |
|---|---|
| **Priority** | **S3.** No production impact. It invalidates a class of register conclusion, which is why it is filed rather than left as a note. |
| **Filed** | 2026-09-11 (Session 77) |
| **Component** | `script_execution_log.host` · `core/execution_log.py:125-138` (`_detect_host()`) · `ingest_breadth_from_ticks.py:60-64` (hand-typed literal) · the column's own `DEFAULT 'local'::text` |
| **Symptom** | Three independent producers write the column, and **which one wrote a given row is not recoverable from the row**. `merdian_pipeline_alert_daemon` logs `host='Navin'`, a string `_detect_host()` cannot produce. `ingest_breadth_from_ticks.py` writes a hardcoded `"local"` from a `*/1` cron **on the AWS box**. |
| **Consequence** | Any register conclusion drawn from the column is unsound until the writing path is identified. Where the writer is an `ExecutionLog` instance the label **is** `_detect_host()` output and the column is usable — that exception is what makes the blanket rule wrong in both directions. |
| **Proper fix** | Either a `host_source` discriminator column, or route every writer through `ExecutionLog` (**TD-S77-NEW-8**). |
| **Cross-ref** | Deployment Topology **§S76.E as amended S77** · **TD-S77-NEW-8** · **TD-S77-NEW-14** · Assumption Register **D.35.25**, **D.35.26**. |
| **Status** | **OPEN.** |

### TD-S77-NEW-8 (S2 priority) — writers hand-roll `script_execution_log` inserts and bypass `ExecutionLog`; how many is unmeasured, and the query written to count them could not have found any

| Field | Value |
|---|---|
| **Priority** | **S2.** Audit coverage of the writer fleet is unknown. Every bypassing writer is invisible to `expected_writes`, `contract_met` and `exit_reason` — i.e. to CLAUDE.md Rule 0's entire mechanism. |
| **Filed** | 2026-09-11 (Session 77) |
| **Component** | `ingest_breadth_from_ticks.py:60-64` (the one known instance, **29,440 rows**) · `script_execution_log` · `core/execution_log.py` |
| **Symptom** | The bypassing writer supplies its own `insert({...})` with a hand-typed `host`, and carries **no `expected_writes` contract, no `contract_met`, no `exit_reason`**. It is a `*/1` cron on the AWS box (crontab lines 12 and 46). |
| **The instrument failed, and that is the entry** | The query written to enumerate such writers keyed on `expected_writes IS NULL`. The column is **`NOT NULL DEFAULT '{}'::jsonb`**, so the predicate is unsatisfiable: it returned **no rows** against a population **known** to contain at least one. *No rows returned* measured nothing and would have been filed as a clean result. |
| **Proper fix** | Enumerate on `expected_writes = '{}'::jsonb` (or on the absence of an opening `RUNNING` row), then port each bypassing writer onto `ExecutionLog`. |
| **Cross-ref** | CLAUDE.md **Rule 0 clause 1** (this is an instance, in the instrument) · Assumption Register **D.35.27** · **TD-S77-NEW-7** · **TD-S76-NEW-10**. |
| **Status** | **OPEN — the coverage question is unmeasured, not answered.** |

### TD-S76-NEW-2 (S1 priority) — `pg_cron jobid 19` disabled as a stop-gap: `gamma_metrics` now grows past its 90-day window, and the stated prerequisite named the wrong table (corrected S79)

| Field | Value |
|---|---|
| **Priority** | **S1.** A deliberate, reversible change to live retention with **no scheduled review**. The failure mode is forgetting: unbounded growth on two tables against a Supabase ceiling nobody is watching. |
| **Filed** | 2026-09-10 (Session 76) |
| **Component** | `pg_cron jobid 19` — `30 12 * * *`, `select public.cleanup_gamma_engine_daily();` **Name corrected S89 (2026-10-03): the live job is `..._daily`; this read `..._data`.** |
| **Action taken** | Operator, 2026-09-09 ~10:10 UTC: `SELECT cron.alter_job(19, active := false);`. Verified `active=false`, with `schedule` and `command` **both intact** — the job is paused, not edited. |
| **Why** | It was deleting `option_chain_snapshots` on a 90-day horizon while its archiver had been dark since 2026-06-05 (**TD-S76-NEW-1**). Stopping it stops the ongoing half of that loss. |
| **What is now unbounded** | Four deletes are suspended: `option_chain_snapshots` 90-day, its 14-day thinning, `raw_ingest_log` 14-day, `gamma_metrics` 90-day. **`gamma_metrics` will grow past 90 days** — `docs/research/gamma_metrics_tail_probe.py` (Topology §S75.4) will read that correctly as a retention-rule change rather than a fault. **`raw_ingest_log`'s growth rate has never been measured**, so its trajectory is unknown, not merely unbounded. |
| **Reversal** | `SELECT cron.alter_job(19, active := true);` — to be run **once the archiver has a scheduled invoker on a live host**, not before. |
| **Proper fix** | This entry closes when jobid 19 is re-enabled behind a working archiver. Measuring `raw_ingest_log`'s daily growth is a prerequisite, not a follow-up: re-enabling without it means the horizon was never chosen on evidence. |
| **Amended (S79, 2026-09-15)** | **The prerequisite named the wrong table.** `raw_ingest_log` growth — this entry's stated blocker — was measured 2026-09-15 at **152 rows/day, flat across all 15 days, ~55k/year**. It is a non-issue. The prerequisite was therefore satisfied against a table that was never the risk, and **the real question has not been asked.** The growth risk is **`option_chain_snapshots` at ~68,000 rows/day** — roughly 450× `raw_ingest_log`. Note the shape: the measurement the entry demanded was taken, returned a reassuring number, and the reassurance was about the wrong object. A prerequisite that names its table wrongly cannot fail for the reason it exists (CLAUDE.md Rule 0). |
| **Corrected prerequisite** | Before re-enabling, **every shipped panel's window must be named, and must fit inside 90 days for `gamma_metrics` and 14 days for full-cadence `option_chain_snapshots`.** jobid 19 thins OCS beyond 14 days to **one 10:00 UTC row per day**, so any OI-rotation history crossing that boundary collapses to a single point per day. That will present to whoever sees it first as a **rendering bug**, not as a retention decision — the degradation is invisible in the artefact that degrades, which is the ADR-023 shape. |
| **Cross-ref** | TD-S76-NEW-1 · Deployment Topology §S76.C · §S75.1 (jobid 19's discovery) · TD-S69-NEW-1 (the storage-ceiling item this feeds). |
| **Status** | **OPEN — deliberate hold, reversal pending.** |

### TD-S76-NEW-11 (S3 priority) — F-82: nine of eighteen `ADR-004` line citations in the S76 audit were wrong, in four distinct ways, and every quote was correct

| Field | Value |
|---|---|
| **Priority** | **S3.** Repaired in the same session it was found. Filed for the **class**, which is not repaired. |
| **Filed** | 2026-09-10 (Session 76) |
| **Component** | `docs/research/ict_structure_audit_2026-09-09.md` · `docs/decisions/ADR-004-ict-primitive-canon.md` |
| **Measured** | An exhaustive `ADR-004:(\d+)` sweep found **18 distinct cited lines, 9 wrong**. Four kinds: **off-by-one** (`:59`→`:60`, `:86`→`:87`, `:541`→`:540`); **a blank line** (`:130`→`:128`, `:145`→`:140`); **the wrong element of the right section** (`:87`→`:91`, `:113`→`:106-111`, `:133`→`:132`, `:578`→`:576`, `:369`→`:368`, `:136-138`→`:135-137`); and **the wrong file** — `ADR-004:383` is `ict_primitives.py:383`; the ADR's `timeframe` CHECK is `ADR-004:501`. ADR-004 has one commit (`37f3259`) and has never been amended, so none of it is source drift. |
| **Why it survived** | **Every quoted string was correct, and every wrong number landed on plausible nearby text.** A reader checking the quote finds it; a reader following the number finds something that reads like support. Neither check can detect the error. |
| **How it was found** | Not by reading. By writing an assertion — `count("ADR-004:87") == 3` — which returned 5, of which two were citations nobody had checked in the four sessions the document has existed. |
| **The class, unrepaired** | A line citation into a file the citing document does not control is **unverifiable at read time and silently rots on any edit of the target**. This is also why ADR-004 Amendment C was appended rather than inserted: an inline insertion would have shifted 19 of the 21 surviving citations. |
| **Proper fix** | Cite by **section and quote**, not by line, wherever the target is a file the citing document does not own. Retrofitting existing citations is a sweep nobody has scoped. |
| **Cross-ref** | ADR-004 Amendment C (§15) · CLAUDE.md **Rule 0** (same failure class: a check that cannot discriminate) · TD-S76-NEW-12. |
| **Status** | **OPEN as a class; the nine instances are repaired.** |

### TD-S76-NEW-12 (S3 priority) — Rule 7 splice-discipline defect in S75's own doc-close: the Topology splice anchored on the wrong footer and wrote none of its own

| Field | Value |
|---|---|
| **Priority** | **S3.** Navigational only. Filed because it is a defect in the splice discipline itself, found while using that discipline. |
| **Filed** | 2026-09-10 (Session 76) |
| **Component** | `docs/registers/MERDIAN_Deployment_Topology.md` — §S75 |
| **What happened** | S75's Topology splice anchored on the **§S73 footer** instead of the file end, so §S75 landed *between* §S73 and §S74. It also **wrote no footer of its own**, which is why the last footer in the file read *"Session 74"* while §S75 sat above it. Section order is now **S72 → S73 → S75 → S74 → S76**. |
| **How it was found** | While writing §S76.A and looking for the correct append point — not by any check. Nothing in the Rule 7 discipline asserts on document ordering or on footer-per-session. |
| **Not fixed** | Deliberately. Reordering §S75 is a large splice unrelated to anything else S76 touched, and doing it inside an unrelated doc-close is the kind of scope drift the discipline exists to prevent. §S76 appended at the true file end and carries its own footer reading `Previous: Session 75`. |
| **Proper fix** | Move §S75 between §S74 and §S76 and give it a footer, in a splice that does nothing else. Separately: the Rule 7 checklist should assert **one footer per session** and **append-at-file-end** — both are cheap post-conditions and neither exists. |
| **Cross-ref** | Doc Protocol v4 **Rule 7** (as amended S74) · Topology §S75, §S76 · TD-S73-NEW-10 (the `## Update log` tables frozen at S67 — the same document, a different decay). |
| **Status** | **OPEN — recorded, not fixed.** |

### TD-S76-NEW-15 (S3 priority) — Doc Protocol v4 asserts `CURRENT.md` is mixed-EOL and must be edited in binary mode; measured, it is pure LF, and `CLAUDE.md` already says so

| Field | Value |
|---|---|
| **Priority** | **S3.** No data is at risk and no edit has been corrupted by it. It is filed because the stale assertion lives in the document a session brief reaches for first, and it already propagated once — into the S76 brief for this doc-close. |
| **Filed** | 2026-09-10 (Session 76) |
| **Component** | `docs/operational/MERDIAN_Documentation_Protocol_v4.md` (the mixed-EOL rule) · `CLAUDE.md` (anti-pattern list, S75 correction) · `docs/session_notes/CURRENT.md` (the subject) |
| **What Doc Protocol v4 asserts** | That `CURRENT.md` carries **mixed CRLF/LF** line endings and must therefore be edited in binary mode with the mix preserved. |
| **Measured, 2026-09-10, before splicing the file** | **0 CRLF · 3,038 bare LF · 0 lone CR · no BOM.** `git check-attr` returns `text: unspecified, eol: unspecified`; `git ls-files --eol` returns **`i/lf w/lf`**. The file is **pure LF** in the index and in the working tree. |
| **`CLAUDE.md` already carries the correction** | Its anti-pattern list records, verbatim: *"The counts in this note are stale — corrected S75 2026-09-09: `CURRENT.md` was 317 CRLF / 2,596 LF when this was written and measures **0 CRLF / 3,038 bare LF** now; it has been normalised since. The rule stands and is why the S75 splices normalised nothing — **but check the file, not this number**."* The S75 figures match today's measurement **exactly**, so the file has not moved since. |
| **The defect is the disagreement, not either statement** | Doc Protocol v4's rule was true when written. `CLAUDE.md` recorded its expiry at S75. **Doc Protocol v4 was never updated**, so two governance files now disagree about the same file's byte-level state, and the **older one is the one a session brief reaches for first** — which is exactly what happened here. |
| **It has already propagated once** | The S76 brief for doc-close file 3 of 10 opened with *"CRITICAL: Doc Protocol v4 records CURRENT.md as having MIXED CRLF/LF endings"* and instructed a binary-mode splice on that basis. The instruction was harmless — no-normalisation is the correct treatment for pure-LF and for mixed alike — but the premise was wrong, and it was wrong because the newer record was not consulted. |
| **Same class as two items filed the same session** | **TD-S76-NEW-13** (F-76: `merdian_reference.json` pins line counts four generations stale) and **TD-S76-NEW-14** (Topology §7.2 lists 20 tasks against 23 measured). All three are a body document asserting a state that a newer record already contradicts, with nothing at the stale site pointing forward. |
| **Proper fix** | A one-line **superseded-marker at the Doc Protocol rule**, pointing at `CLAUDE.md`'s anti-pattern entry — the same treatment applied to `ADR-004:60` and to Topology §1/§7.2 this session. **`docs/operational/MERDIAN_Documentation_Protocol_v4.md` is not among the ten files in this doc-close**, so this is deferred to whenever it is next touched. The rule's *substance* needs no change: measure the file, normalise nothing. Only its factual claim about `CURRENT.md` is stale. |
| **Cross-ref** | `CLAUDE.md` anti-pattern list (S75 correction) · TD-S76-NEW-13 · TD-S76-NEW-14 · TD-S73-NEW-10 (frozen `## Update log` tables — the same decay in a different register). |
| **Status** | **OPEN — deferred to the next Doc Protocol touch.** |

### TD-S76-NEW-16 (S2 priority) — `merdian_reference.json`'s own version control is unreliable: two `change_log` arrays ten sessions apart, and two version counters, one of which no session bumps

| Field | Value |
|---|---|
| **Priority** | **S2.** The file is the inventory a session is told to consult first. When its own provenance is ambiguous, every value it reports inherits that ambiguity — and the stale counter is the one a reader reaches for, which has already happened once. |
| **Filed** | 2026-09-10 (Session 76) |
| **Component** | `docs/registers/merdian_reference.json` — `_meta.change_log` vs top-level `change_log`; `_meta.version` vs top-level `version` / `last_updated_session` / `last_updated_date` |
| **Two `change_log` arrays** | `_meta.change_log` (indent 4, entries at 6) newest entry **S66**. Top-level `change_log` (indent 2, entries at 4) newest entry **S76** after this session. **Ten sessions diverged.** Nothing in the file says which is canonical, and neither array references the other. |
| **Two version counters** | `_meta.version` = **v52**. Top-level `version` = **v54** after this session. |
| **S75 bumped the nested counter and left the top-level stamp behind** | Commit **`1832b3a`** states *"merdian_reference.json — four live column lists, version v51 -> v52"*. That is `_meta.version`. The top-level `last_updated_session` stayed at **"Session 74"** and `last_updated_date` at **2026-09-07**, so **the file recorded edits it did not admit to**: it was modified at S75 while continuing to state it was last updated at S74. |
| **S76 widened the divergence rather than resolving it** | This session bumped the **top-level** stamp (v53 → v54, Session 74 → 76, 2026-09-07 → 2026-09-10) and deliberately left `_meta` untouched, because reconciling two counters is a decision about which is canonical, not a splice. The gap is now v52 vs v54 and S66 vs S76. **Recorded as widened, not as fixed.** |
| **It has already misled once** | The **S76 session brief for this file cited "v52"** — the nested, stale counter — when the live top-level value was v53. The stale value is the one a reader reaches for, which is the whole hazard. |
| **Same class as three items filed the same session** | **TD-S76-NEW-13** (line counts four generations stale), **TD-S76-NEW-14** (Topology §7.2, 20 tasks against 23), **TD-S76-NEW-15** (Doc Protocol v4 vs `CLAUDE.md` on `CURRENT.md`'s line endings). All four are **a value asserted in one place and contradicted in another, with nothing connecting them**. |
| **Proper fix** | A decision, then a patch. Decide which `change_log` and which counter are canonical; delete or explicitly mark the other as historical; and add a doc-close post-condition asserting that the stamp a session writes matches the session it ran in. The last part is cheap and is the piece that would have caught S75. |
| **Cross-ref** | TD-S76-NEW-13 · TD-S76-NEW-14 · TD-S76-NEW-15 · TD-S71-NEW-1 · TD-S71-NEW-2 (the same file's stale freshness header) · TD-S73-NEW-10. |
| **Status** | **OPEN — divergence widened at S76 and recorded as such.** |

### TD-S76-NEW-21 (S3 priority) — ADR-004's Amendments A and B are absent from the Decision Index entirely, and Amendment C's new marker makes the file read as though they never happened

| Field | Value |
|---|---|
| **Priority** | **S3.** Nothing is broken in code and no decision is misrecorded in the ADR itself. The hazard is navigational: the Index is the file CLAUDE.md Rule 0 names for the session-start *"have we decided this already?"* scan, and it now presents an incomplete amendment history as a complete one. |
| **Filed** | 2026-09-11 (Session 76, from file 8's premise check) |
| **Component** | `docs/decisions/MERDIAN_Decision_Index.md` — the ADR-004 row's Date cell · `docs/decisions/ADR-004-ict-primitive-canon.md` (Amendments A, B, C) · Doc Protocol v4 **Rule 11.1** |
| **Measured 2026-09-11** | Grep for `Amendment A` and `Amendment B` across the whole Decision Index: **zero hits each**. ADR-004's amendments appear as **no row, no Date-cell marker, and no session-footer mention**. The convention exists and three other ADRs follow it — ADR-023 and ADR-022 carry `· **AMENDED S71 2026-08-29**`, ADR-021 `· **AMENDED S72 2026-09-05**`, all in the Date cell. |
| **How it surfaced** | Not by audit. The S76 doc-close was instructed to *read how the file handles prior amendments, since ADR-004 already carries A and B, and follow that rather than inventing a form*. The premise check that question forced returned a third answer neither branch anticipated: **there is no prior handling to follow, because there is none recorded.** |
| **What Amendment C did about it** | Followed the convention the **other** ADRs establish — a Date-cell marker on the parent row, substance in the S76 session footer. That is correct in form and it has a side effect worth stating plainly: **C's marker is now the first and only ADR-004 amendment the Index records**, so a reader scanning the row sees one amendment where there are three. |
| **Why it is not repaired in the same pass** | Dating A and B requires reading them out of `ADR-004-ict-primitive-canon.md` and establishing which session accepted each — a **sourced edit**, not a byte-level splice against text already on screen. Doing it inside a doc-close splice would have meant inventing two dates or transcribing them unverified, which is the class this session filed five instances of (**TD-S76-NEW-13..17**). |
| **The general shape** | **Rule 11.1 is enforced for ADRs and unenforced for amendments.** A new ADR mechanically prepends a row and the reverse check verifies row-for-file. An *amendment* has no such mechanism: it depends on whoever writes the session footer noticing. A and B were missed for months by exactly that gap, and nothing in the index-health check would ever have caught it — the checks verify rows against files, and an amendment is neither. |
| **Proper fix** | Two parts. (1) Read A and B out of ADR-004 §§ and date them from their accepting sessions; add both to the ADR-004 Date cell **ahead of C, in chronological order**. (2) Extend the `## Index health checks` list with a fourth check — *every amendment recorded in an ADR file has a Date-cell marker in its parent row* — since the existing three cannot see this class at all. |
| **Cross-ref** | ADR-004 **Amendment C** (§15) · Doc Protocol v4 **Rule 11.1** · Decision Index S76 session footer (where the defect is narrated) · **TD-S73-NEW-11** (the same file, resolved at S73 — and carried forward as live into this session's brief, which is the §D.35 row this defect was found alongside) · **TD-S76-NEW-13..17** (the transcribe-without-a-source class this fix must avoid). |
| **Status** | **OPEN — recorded, deliberately not repaired.** |

### TD-S76-NEW-22 (S3 priority) — Session Management Rule 5 specifies a twelve-field session-log block; the log abandoned it ~2026-04-07 and 65 entries since are one-line prose, with the rule never amended

| Field | Value |
|---|---|
| **Priority** | **S3.** Nothing breaks. The cost is that a session instructed to *"write the session_log entry in the Rule 5 format"* — as this one was — either forks the file or has to stop and ask, and the second outcome is only available if somebody measures the file first. |
| **Filed** | 2026-09-11 (Session 76, while writing the S76 log entry) |
| **Component** | `docs/operational/MERDIAN_Session_Management_v1.md` **Rule 5** · `docs/session_notes/session_log.md` |
| **Measured 2026-09-11** | Rule 5 prescribes a twelve-field block — heading, `Goal`, `Session type`, `Completed`, `Open after session`, `Files changed`, `Schema changes`, `Open items closed`, `Open items added`, `Git commit hash`, `Next session goal`, `docs_updated`. In the log: **19** entries in that form, all of them old, the newest dated **2026-04-07** (line 1017); **65** entries in one-line prose form, newest-first, everything since. The file is prepend-only, so the two formats are stacked with the abandoned one at the bottom. |
| **What the prose form carries that Rule 5 does not** | Commit chain with push/host-parity state, ADR and TD ledger counts inline, refuted-claim accounting, and the explicit *not-done* tail. **The practice is richer than the rule, not sloppier than it** — which is why it displaced the rule and why the fix is to amend Rule 5, not to restore the block. |
| **Why it matters more than a style note** | Rule 5's `docs_updated` field exists to make documentation debt visible — *"three consecutive `no` entries = explicit debt"*. That mechanism has not run for 65 sessions, and the **project-knowledge re-upload gap (CLAUDE.md Rule 12, the S70 finding)** is exactly the debt it was built to surface. The prose entries do carry a *not-done* clause, but nothing counts consecutive omissions. |
| **The general shape** | **A standing rule that describes a practice which stopped is indistinguishable, to a reader, from a rule that is being followed.** Third instance filed this session: **TD-S76-NEW-15** (Doc Protocol asserts `CURRENT.md` is mixed-EOL; measured pure LF) and **TD-S76-NEW-21** (Rule 11.1 unenforced for amendments) are the same defect in different documents. None was found by audit; each surfaced when a session tried to *follow* the rule. |
| **Proper fix** | Amend Rule 5 to specify the prose-line form actually in use — date · commit chain with parity state · session number and type · findings · ledger (`ADRs_NEW` / `ADRs_AMENDED` / `TDs_NEW` / `TDs_CLOSED`) · not-done tail — and **carry `docs_updated`'s consecutive-`no` mechanism forward into it**, since that is the one field the prose form dropped without replacing. Do **not** restore the twelve-field block: 65 entries would have to be rewritten or the file forks. |
| **Cross-ref** | **TD-S76-NEW-15** · **TD-S76-NEW-21** (the same class, this session) · CLAUDE.md **Rule 12** and the S70 project-knowledge finding (the debt `docs_updated` was meant to surface) · `docs/session_notes/session_log.md` line 1017 (the last Rule 5 entry). |
| **Status** | **OPEN.** |

### TD-S76-NEW-23 (S2 priority) — the production checkout `~/meridian-engine` sat 22 commits behind `origin/main` at the S76 close, having never received S75 at all

| Field | Value |
|---|---|
| **Priority** | **S2.** No production risk *this time* — neither S75 nor S76 changed code — but that is a property of two particular sessions, not of the mechanism. The same gap across a session that ships a writer patch means the box runs code the repo says was fixed. |
| **Filed** | 2026-09-11 (Session 76 close), **deliberately before the remediating pull**, because the evidence is the checkout's HEAD and the fix overwrites it. |
| **Component** | `/home/ssm-user/meridian-engine` (production checkout) · `origin/main` · Doc Protocol v4 **Rule 3** session-close steps |
| **Measured 2026-09-11, before any fetch or merge against that tree** | `~/meridian-engine` HEAD = **`83818e6`** — the **S74** doc-close, 2026-09-07. `origin/main` = **`c74440e`**. Gap = **22 commits**: the whole S75 session (13 doc-close commits + 9 research commits) and both S76 commits. `git merge-base --is-ancestor` confirms fast-forward, so nothing diverged — the pull was simply never run. Three untracked files present (`rate_sens.out`, `s6_greeks.json`, `status.json`); none collides with the incoming set. |
| **What was stale on the box, and for how long** | Every document: `CLAUDE.md`, `CURRENT.md`, `tech_debt.md`, `merdian_reference.json`, the System Map, the Topology, the Assumption Register, the Decision Index. **S74-era since 2026-09-07 — three sessions.** That box is where production runs and where an agent told to "read the repo" lands, so the contract governing its work was two doc-closes out of date while reading as current. |
| **Why it was invisible** | **Nothing asserts that the two checkouts agree.** Rule 3 lists the EC2 fast-forward as a close step; it was not performed at S75, and no check anywhere compares `~/meridian-cc` HEAD, `origin/main` and `~/meridian-engine` HEAD. A missed step that leaves no trace is indistinguishable from a step that ran. The box's own `git rev-list --count HEAD..origin/main` **returns 0**, because its `origin/main` ref is itself stale — **the most obvious check reports "up to date" on a three-session-stale tree.** |
| **The general shape** | **Same as the S70 project-knowledge finding, one tier over.** There it was git → project knowledge; here it is git → EC2. Both are cases where a doc-close was committed, pushed, verified, and still did not arrive, because *pushing* and *arriving* are separate acts and only the first leaves a record. **A destination that is never asserted is a destination that silently stops receiving.** |
| **Proper fix** | (1) The pull itself — `git fetch origin` then `git merge --ff-only origin/main`, never a bare `git pull`, which can create a merge commit on a production checkout. (2) **Add a three-way hash assertion to the Rule 3 close checklist**: `~/meridian-cc` HEAD == `origin/main` == `~/meridian-engine` HEAD, plus a tree-hash comparison, so a stale destination **fails loudly** rather than silently. Compare hashes, never byte sizes — **D.30.4** (`core.autocrlf` makes size a per-tier quantity; it is unset on this box, which is exactly why the trap is invisible here and bites on Windows). (3) Extend the same assertion to the project-knowledge destination if any mechanical check is possible there; if none is, record that it is operator-attested and cannot be verified, rather than leaving it looking checked. |
| **Cross-ref** | **TD-S70-NEW-*** / the S70 project-knowledge finding (the same shape, other tier) · CLAUDE.md **Rule 12** · Doc Protocol v4 **Rule 3** · **D.30.4** (hashes not byte sizes across tiers) · ADR-006 (deploy direction) and the **deploy-direction inversion**, UNRATIFIED for a third session — which is the decision this checklist item has to be written against. |
| **Status** | **OPEN — pull executed at the S76 close; the missing ASSERTION is what this entry tracks.** |

### TD-S75-NEW-4 (S2 priority) — ADR-002 v2's build sequence and the Enhancement Register use ENH-80..85 for different things; the register is authoritative by precedent, and the propagation TD that would have fixed the documents was never filed

| Field | Value |
|---|---|
| **Priority** | **S2.** Nothing is broken in code. The hazard is that a reader follows ADR-002 v2's sequence, looks up a slot number in the Enhancement Register, and edits the wrong entry. That is not hypothetical — see the near-miss below. |
| **Filed** | 2026-09-09 (Session 75) |
| **Component** | `docs/registers/MERDIAN_Enhancement_Register.md` · ADR-002 v2's build-sequence line, reproduced verbatim in `CLAUDE.md` as `Phase 0 → ENH-80 → ENH-84 → ENH-81 → Exp 23 → ENH-82 → buyer-polarity gates → ENH-85 → ENH-83`. |
| **The collision** | ADR-002 v2 (S27) used **ENH-80 through ENH-85** as *plan slot numbers*. The Enhancement Register had independently assigned, or later assigned, some of those identifiers to unrelated work. The two documents now disagree about what four of the six numbers mean. |
| **Which numbering is authoritative — answered, not open** | **The Enhancement Register**, by precedent set at S28 and applied twice. Register update log 2026-05-13 (L2428): *"+ENH-97, +ENH-98 (S28 P2 — formal Enhancement Register filing of S27 verbally-NEW entries; **renumbered from 'ENH-84'/'ENH-85' due to slot collision per Doc Protocol v2 Rule 5**)"*. The ENH-98 status row (L131) repeats it: *"renumbered from S27 verbally-NEW 'ENH-85' due to slot collision"*. Rule 5's ENH clause — *"Monotonic integers… Pick next-free. IDs permanent."* — makes the register's assignment permanent and the plan's slot number the one that must move. |
| **What was renumbered, and what was not** | **Renumbered at S28:** ADR-002 v2's "ENH-84" (vol_analytics + RR ratio, P7) → **ENH-97**; its "ENH-85" (vanna/charm, P8) → **ENH-98**. Both collided with already-SHIPPED register entries (ENH-84 = REFRESH ZONES dashboard button, SHIPPED S14; ENH-85 = PO3 Session Direction Lock). **Not renumbered:** ADR-002 v2's **"ENH-82"** (Pin Risk Score continuous) and **"ENH-83"** (DTE force multiplier). At S28 neither had collided yet — ENH-82 was a reserved slot and ENH-83 was free. |
| **Why ENH-83 is now a live collision** | The register subsequently consumed ENH-83 for different work: **`ENH-83 \| Calibration console (SHIPPED S39)`** (L3595). Nobody re-ran the S28 renumbering check when that assignment was made, so a slot that was merely *pending* a collision became one, silently, at S39. |
| **Current register state, measured** | **ENH-82** — no status-table row and no detail block; the register's own Scope line (L10) records it among *"reserved/unused slots ENH-82/94 per ADR-002 v2 build sequence"*. `/usr/bin/grep -n "Pin Risk"` over the register returns **zero** entries. **ENH-83** — exactly one row, the Calibration console, SHIPPED S39. So under register numbering, ADR-002 v2's ENH-82 has never been opened and its ENH-83 does not exist at all. |
| **The propagation TD was queued and never filed** | The ENH-97 history block states *"Cross-doc rename propagation queued as **TD-NEW-15**"*. Measured **immediately before this entry was filed**, `/usr/bin/grep -c "TD-NEW-15" docs/registers/tech_debt.md` returned **0** while `CURRENT.md` returned **11** (this entry's own two references are now the only ones in this file, so the count no longer reproduces — it is recorded here as of 2026-09-09 pre-filing). It was carried across sessions in the live-state file and never entered the register that owns it. That is why `CLAUDE.md`'s ADR-002 v2 sequence still reads `ENH-84 … ENH-82 … ENH-85 … ENH-83` with the pre-renumbering identifiers. |
| **Workaround** | Before acting on any ENH identifier taken from ADR-002 v2's sequence, resolve it against the Enhancement Register first. Two of the six (84, 85) are known-renumbered to 97/98; one (83) points at unrelated shipped work; one (82) points at nothing. |
| **Proper fix** | Two parts, and they are separable. **(a)** Renumber ADR-002 v2's remaining plan slots to next-free register IDs and update the sequence line in ADR-002 v2 and in `CLAUDE.md` — the S28 precedent applied to the two slots it did not reach. **(b)** File the cross-doc propagation work that TD-NEW-15 was supposed to carry, or record explicitly that it is abandoned. Neither is decided here. |
| **Cross-ref** | Doc Protocol v4 Rule 5 (ENH IDs) · Enhancement Register L10, L131, L2428, L3039, L3595 · ADR-002 v2 build sequence · Assumption Register **§D.33.15** (the near-miss this collision produced). |
| **Status** | **OPEN.** |

### TD-S75-NEW-1 (S2 priority) — `build_gss_rows` writes `gex_cr` through the deep-ITM filter while OI and gamma bypass it, so a stored row can disagree with its own recomputation

| Field | Value |
|---|---|
| **Priority** | **S2.** No signal or gate reads `gex_cr` (per `flip_audit_2026-09-08.md` §PART C, the live consumers of the GEX surface are display-only), so nothing trades on it. It matters because ADR-015 §F2 invites read-time recomputation, and a consumer that accepts that invitation gets a different answer from the stored column. |
| **Filed** | 2026-09-09 (Session 75) |
| **Component** | `compute_gamma_metrics_local.py` — `build_gss_rows` (L1113) and `signed_gamma_exposure` (L114–133). |
| **Mechanism — verified in source** | `build_gss_rows` iterates `option_rows_raw`, i.e. **pre-filter**, deliberately, so `oi_call`/`oi_put` reflect full-chain OI (its own docstring says so). It accumulates `oi_call`/`oi_put` from raw `oi` and sets `gamma_call`/`gamma_put` from `gamma_raw` whenever `gamma_raw != 0.0`. But `gex_cr` accumulates `signed_gamma_exposure(row, spot)`, which returns `0.0` for any strike more than 5% from spot whose `\|gamma\| > 5e-5` (the TD-NEW-2 Part A guard, L128–130). **The three columns therefore disagree about which rows count.** |
| **Measured extent** | Rows with `gex_cr = 0` while `gamma_call` or `gamma_put` is populated — the signature of the guard firing — counted with `count=exact` on `gex_strike_snapshots`: **June NIFTY 1,394 / SENSEX 15,720; July 3,082 / 18,688; August 906 / 11,529; 2026-09-01..08 230 / 787.** SENSEX carries roughly an order of magnitude more than NIFTY in every month, which is TD-S75-NEW-2. |
| **A supplied example that did not survive measurement** | This entry was drafted from a report that SENSEX 2026-09-04 carried "748 of 10,530 rows with populated OI **and gamma** at `gex_cr = 0`". Measured: total 10,530 and `gex_cr = 0` on **748** both confirm, and all 748 have `oi_call > 0` or `oi_put > 0` — but **zero of them have `gamma_call` or `gamma_put` populated**. Those 748 are the `gamma == 0.0` branch of `signed_gamma_exposure`, not the deep-ITM guard. NIFTY that day: **zero** rows at `gex_cr = 0`. The guard-firing signature is real and is the figure in the row above; 2026-09-04 SENSEX simply is not an instance of it. |
| **Why the ADR-014 §2.5 falsification rule cannot see it** | That rule checks `sum(gex_cr)` across per-strike rows against `net_gex` in `gamma_metrics`. Both sides are computed from `signed_gamma_exposure`, so both carry the filter identically and the check passes by construction. It is a self-consistency test, not an independent one. |
| **Proper fix** | Not decided here. Either the three columns are made to agree about the filter, or ADR-015 §F2's recomputation contract is amended to state which rows a recomputation must exclude. It is an ADR-015 question, not a code change. |
| **Cross-ref** | ADR-015 §F2 · ADR-014 §2.5 · TD-S75-NEW-2 (the symbol-blind threshold that drives the NIFTY/SENSEX asymmetry) · `docs/research/flip_audit_2026-09-08.md`. |
| **Status** | **OPEN.** |

### TD-S75-NEW-2 (S2 priority) — the deep-ITM gamma threshold is a bare constant, so it is ~3.2× stricter on SENSEX than on NIFTY

| Field | Value |
|---|---|
| **Priority** | **S2.** It biases the primary arm and any ADR-009 cross-symbol replication differently, which is exactly the axis a replication check is supposed to hold fixed. |
| **Filed** | 2026-09-09 (Session 75) |
| **Component** | `compute_gamma_metrics_local.py::signed_gamma_exposure`, L128–130. |
| **Mechanism — verified in source** | The guard is `if strike > 0 and abs(strike - spot) / spot > 0.05: if abs(gamma) > 5e-5: return 0.0`. Both constants are bare literals. **There is no `symbol` argument to the function and no symbol conditioning anywhere in it** — the row dict is not consulted for symbol. The moneyness leg (`0.05`) is scale-free; the gamma leg (`5e-5`) is not, because gamma scales inversely with the underlying's level. |
| **Measured consequence** | Spot is ~24,300 (NIFTY) against ~77,000 (SENSEX), a ratio of ~3.2. The guard-firing counts in TD-S75-NEW-1 run roughly 10× higher on SENSEX in every month measured. The comment in the source justifies `5e-5` as "~5x typical ATM gamma", a calibration that can only hold for one of the two symbols. |
| **Why it matters beyond magnitude** | ADR-009's replication design treats the second symbol as an independent check on the first. If the two arms are filtered at different effective strictness, a divergence between them is not evidence about the market. |
| **Proper fix** | Not decided here. Either the threshold becomes symbol-relative (a function of spot, or an ADR-016 `merdian_parameters` lookup keyed by symbol), or the ADR that introduced it records that it is symbol-blind and that cross-symbol comparisons inherit the asymmetry. |
| **Cross-ref** | TD-NEW-2 Part A (which introduced the guard, S27) · TD-S75-NEW-1 · ADR-009 · ADR-016 (the parameter-table pattern this would use). |
| **Status** | **OPEN.** |

### TD-S74-NEW-4 (S1 priority) — F-04: the S59 breadth defect can recur — the guard went into the health check, not into either consumer

| Field | Value |
|---|---|
| **Priority** | **S1.** The exact failure that produced BULLISH breadth on a 0.37 A/D down day is reachable again, by the same mechanism, in two live consumers. |
| **Discovered** | Session 74 (2026-09-07), coupling audit finding F-04. |
| **Component** | `build_wcb_snapshot_local.py:94-99` · `ingest_breadth_from_ticks.py:160-162` · `equity_intraday_last` |
| **Symptom** | Both consumers read `equity_intraday_last` **unbounded**. If the 09:05 refresh fails, both silently use the previous session's baseline and every downstream breadth read is computed against a stale reference price — the S59 shape verbatim, which is itself the C-09 / ADR-001 shape. |
| **Where the guard actually went** | S59 added a REFERENCE FRESHNESS check to `scripts/eod_health_check.py` (commit `6b58587`). That check runs **after the fact**, on a schedule that S73 established has no verified invoker, and it does not gate either consumer. The guard was placed in the observer, not in the path. |
| **Why that is not sufficient** | A health check reports a stale baseline the next time it runs. The consumers use it immediately. Between those two events the system emits confident, wrong breadth — and ADR-001's stable-lie rule says a component must refuse to produce a value it cannot stand behind, not produce one and let a downstream observer flag it later. |
| **Proper fix** | Move the freshness assertion into both consumers, reading `ts` (never `created_at`, per §D.25.1) with an explicit floor, and **fail to absent**. Keep the health-check version — it is a useful second line — but it is not the fix. |
| **Cross-ref** | TD-S59-NEW-1 / §D.25.1 (`ts` not `created_at`) · §D.25.2 (the frozen baseline) · ADR-001 · ADR-023 · TD-S74-NEW-1. |
| **Status** | **OPEN.** |

### TD-S73-NEW-10 (S3 priority) — the System Map and Deployment Topology `## Update log` tables are frozen at Session 67 while both files record through Session 72

| Field | Value |
|---|---|
| **Priority** | **S3.** Neither file is wrong; the table whose job is recording updates is five sessions behind the updates sitting below it. A reader trusting it dates the file to 2026-07-10. |
| **Discovered** | Session 73 (2026-09-06), surveying both files' section format before appending §S73. |
| **Component** | `docs/registers/MERDIAN_System_Map.md:560` · `docs/registers/MERDIAN_Deployment_Topology.md:848` |
| **Symptom** | Both files carry a dedicated `## Update log` section — a `\| Date \| Session \| Event \|` table — closed by a footer reading *"Last updated Session 67, 2026-07-10"*. Both files contain §S68, §S69, §S70, §S71 and §S72 sections below that point. |
| **Root cause** | Two update-log conventions coexist and only one is maintained. Sessions 68–72 each appended a **per-section closing footer** (`*System Map updated Session N, …*`) and left the document-level table alone. The per-section footers are current; the table is not. |
| **Residual** | §S71 has **no closing footer in either file**, so even the maintained convention has a gap — consistent with §S71 being misplaced: the section order runs §S68 → §S69 → **§S71 → §S70** → §S72 in both files, identically. |
| **Proper fix** | Decide which convention is canonical and retire the other. If the table stays, backfill S68–S73 and add it to the doc-close checklist; if the per-section footers stay, delete the table rather than leaving a stale one. **Do not maintain both.** |
| **Cross-ref** | TD-S73-NEW-11 (same class, Decision Index) · Doc Protocol v4 Rule 3 (session-end checklist). |
| **Status** | **OPEN.** |

### TD-S73-NEW-1 (S2 priority) — `shadow_runner.log` is a 262 MB live log at repo root, outside logrotate's scope, while its cron line's visible redirect target is covered

| Field | Value |
|---|---|
| **Priority** | **S2.** 274,528,648 bytes — 64% of the 411 MB `~/meridian-engine` tree — on a 7.6 G volume at 65%. Unbounded because nothing rotates it. S29's breadth cascade came from disk pressure. |
| **Discovered** | Session 73 (2026-09-06), enumerating the ~270 MB unaccounted for between the tree size and its directories. |
| **Component** | `~/meridian-engine/shadow_runner.log` · `run_merdian_shadow_runner_aws.py` · `/etc/logrotate.d/meridian` |
| **Symptom** | `stat`: 274,528,648 bytes, mtime `2026-09-04 09:56:23 UTC` — the last trading day. Live, not residue. |
| **Root cause** | `/etc/logrotate.d/meridian` covers exactly two paths: `/home/ssm-user/meridian-engine/cron.log` and `/home/ssm-user/meridian-engine/logs/*.log`. This file is at repo root and matches neither. S71 installed that config scoped to what S71 was looking at. |
| **Why it stayed invisible** | The crontab line (`*/5 03-09 * * 1-5 … run_merdian_shadow_runner_aws.py >> logs/orchestrator.log 2>&1`) redirects to a path that **is** covered. An audit reading the crontab sees a correctly-rotated target; the real writer is an internal logging handler pointed at a hardcoded repo-root path. **The visible channel is the decoy.** C-17 shape. |
| **Not established** | Growth rate. 274 MB accumulated over an unknown period, and EBS free went 2.7 G → 2.8 G across the ten days since S71 — which is not what an unrotated grower does. Severity above is from the absence of rotation, not from a measured trajectory. |
| **Proper fix** | Extend `/etc/logrotate.d/meridian` to cover repo-root `*.log`, or repoint the writer into `logs/`. Prefer the second — one log location is the durable answer. Measure the rate first. |
| **Cross-ref** | TD-S69-NEW-1 (EBS, resolved by measurement S71) · TD-S73-NEW-6 (same class: a scheduling/plumbing fact no register held). |
| **Status** | **OPEN.** |

### TD-S73-NEW-2 (S3 priority) — a literal Windows path exists as a directory on the Linux host and something writes into it daily

| Field | Value |
|---|---|
| **Priority** | **S3.** 4.6 MB, contained, no downstream consumer identified. Matters because it means a config value still carries its Windows form on EC2 and nothing detects that. |
| **Discovered** | Session 73 (2026-09-06), `du -sh */` in `~/meridian-engine`. |
| **Component** | `~/meridian-engine/C:\GammaEnginePython\heartbeats/` — a directory whose *name is the Windows path string* |
| **Symptom** | Directory created `Jun 9 13:32`, containing one file: `MERDIAN_Spot_1M.log`, 4,737,896 bytes, mtime `2026-09-04 09:59 UTC` — three minutes after `shadow_runner.log`, on the last trading day. Live. |
| **Root cause** | **Unidentified.** The structure implies something took the string `C:\GammaEnginePython\heartbeats` as a directory, created it, and joined a filename with `/`. That means the path arrives as a *value* — from config or environment — not from source, since the only two cron-scheduled scripts mentioning `GammaEnginePython` (`capture_spot_1m_v2.py:50-51`, `generate_pine_overlay.py:14`) mention it **only in comments**, as Windows Task Scheduler setup notes. |
| **Refuted in-session** | "`capture_spot_1m_v2.py` and `generate_pine_overlay.py` write here" — filed from `grep -l`, refuted by reading the lines. `grep -l` establishes mention, not authorship. |
| **Constraint on investigation** | The likely source is `.env`, which cannot be read (CLAUDE.md Rule 19). Probe the *code* for the variable name, never its value. |
| **Wider surface** | 135 root `.py` files mention `GammaEnginePython`. On this evidence most are comments and Task Scheduler notes; the count is not a defect count. |
| **Proper fix** | Identify the writer, then point the heartbeat path at a platform-appropriate location. Do not delete the directory before the writer is known — that only relocates the ignorance. |
| **Cross-ref** | TD-S73-NEW-1 (both are repo-root writers no register describes). |
| **Status** | **OPEN.** |

### TD-S73-NEW-6 (S2 priority) — `eod_health_check.py` has no scheduled invoker; the fourth instance of the class, and TD-S72-NEW-7's premise was inferred from it

| Field | Value |
|---|---|
| **Priority** | **S2.** A health check nobody runs is not a health check. It also invalidates a stated root cause in an S72 item. |
| **Discovered** | Session 73 (2026-09-06), checking the check's own schedule before changing its verdict logic. |
| **Component** | `scripts/eod_health_check.py` · `crontab -l` · `/etc/systemd/system/` |
| **Measured** | `crontab -l \| grep -n 'eod_health'` → no match, grep exit 1, against `crontab -l \| wc -l` = **53** (unchanged since S72 close). `grep -rn 'eod_health_check' /etc/systemd/system/` → no match. 20 units, 3 timers (`merdian-wsfeed-start`, `merdian-wsfeed-stop`, `snap.certbot.renew`), none referencing it. |
| **Consequence for TD-S72-NEW-7** | That item was written around the check running at **00:45 UTC** against a `cron.log` that logrotate empties at 00:00. Nothing schedules it at 00:45. The number came from the file's own comment at lines 127–128 — an assumption about invocation, not a fact of the deployment. The `resolve_cron_log()` fix by mtime remains correct and is *more* correct for an operator-invoked script that can run at any hour; **the recorded reason needs amending, not the code.** |
| **Second consequence** | An operator-invoked check has no fixed relationship to the 03:35 UTC `refresh_equity_intraday_last` cron. The pre-03:35 false positive is therefore not an edge case — it fires on any morning run. |
| **Scope of the negative** | Established for the `ssm-user` crontab and `/etc/systemd/system/` only. **Not checked:** `/etc/cron.d/` drop-ins, other users' crontabs, `/usr/lib/systemd/system/`, user units under `~/.config/systemd/user/`. |
| **Method note** | The first attempt used `grep 'eod\|scripts/'` and `grep -i 'health'` — substring guesses that could only support "no line contains these substrings," not "not scheduled." The stronger claim required the direct grep and the systemd sweep. Recorded because the weaker method produced the same empty result and would have been read as proof. |
| **Cross-ref** | TD-S71-NEW-14 (unscheduled-invoker reconciliation) · TD-S72-NEW-7 (premise amended) · guardrails C-19 (systemd is a second scheduling surface). |
| **Status** | **OPEN.** Fourth instance after the Pine generator, the dropped `.bat` line, and `reload_dhan_scripmaster.py`. |

### TD-S73-NEW-7 (S2 priority) — the Claude Code permission model is verb-shaped, not effect-shaped, and the config itself is untracked

| Field | Value |
|---|---|
| **Priority** | **S2.** The permission file is the sole enforcement layer — no managed policy exists above it on Max tier — and three independent gaps were found in one session of ordinary use. |
| **Discovered** | Session 73 (2026-09-06), during the first Claude Code work session. |
| **Component** | `~/meridian-cc/.claude/settings.json` · `MERDIAN_ClaudeCode_Guardrails.md` §1 |
| **Gap 1 — synonyms defeat the deny list** | `Bash(git checkout *)` is denied. `git switch -c` performs the identical operation and is **unlisted**, so it fell through to a generic approval prompt. `git restore` likewise covers the destructive half of `checkout` — including `git restore .`, the working-tree discard the S71 `.pine` workaround used six times. `git add` is unlisted entirely, though P-8 forbids `git add -A`/`git add .` in prose. |
| **Gap 2 — `Read` deny does not cover every reader** | `Read(.env)` **does** block `cat`, `head`, `tail`, `sed` and Bash redirection targets (these are the file commands Claude Code recognises in Bash). It does **not** cover `grep`, `awk`, `less`, `od`, `xxd`, `strings`, or any Python that opens the file itself — and `grep` is auto-approved as a built-in read-only command, so `grep KEY .env` would not even prompt. This is the S71 exposure's uncovered sibling. |
| **Gap 3 — mode is switchable with no disk trace** | Auto mode was active for part of this session; neither party chose it deliberately. It is offered as option 2 or 3 on nearly every permission prompt, leaves nothing in `settings.local.json`, and is visible only in the status bar and in retrospective `Allowed by auto mode classifier` lines. `ask` rules still fire in auto mode, so the load-bearing `Bash(python3 *)` guard held — but everything outside the named 25/16 was approved by a classifier. |
| **Structural finding** | The config is **untracked** (`?? .claude/`). It is the only governance artefact in the repo not under version control: no diff, no review, absent from a fresh clone. The recorded counts **deny 25 / ask 16 / allow 0** are therefore the sole tamper check. |
| **Also** | Empty `allow` produces prompt volume high enough that approval fatigue becomes the failure mode — the same shape as the item this session's code fix addressed. |
| **Proper fix** | Add `Bash(git switch *)`, `Bash(git restore *)`, `Bash(git add *)` (ask), `Bash(grep*.env*)` (deny); track `.claude/settings.json` in git; re-record the counts. Amend guardrails §1, whose stated crontab deny/allow pair was already found unachievable in this session (deny precedes allow with no exceptions — moved to `ask`). |
| **Cross-ref** | Guardrails §1, §10 · TD-S71-NEW-11 (S71 `.env` exposure) · P-4, P-8. |
| **Resolution — S74 (structural finding CLOSED, Gap 3 remains)** | `.claude/settings.json` is now **tracked in git** — the only governance artefact in the repo outside version control is inside it. Counts re-recorded and verified live in `/permissions`: **deny 25 → 30, ask 16 → 19, allow 0** (still empty). **New denies** closing Gap 2: `set -a`, `source *.env*`, `. ./.env*`, `grep*.env*`, `env`. **New asks** closing Gap 1: `git switch`, `git restore`, `git add`. |
| **Residual — Gap 3 is not closeable in config** | Auto mode remains switchable with no disk trace: offered on nearly every prompt, absent from `settings.local.json`, visible only in the status bar and in retrospective `Allowed by auto mode classifier` lines. No setting suppresses it. Recorded, not fixed. |
| **Residual — the deny list is one-sided** | The new `.env` denies bind the **agent**, not the operator shell in the same terminal. During this session's doc-close an operator-run `set -a; . ./.env; set +a` exported every credential into the shell environment — the exact operation denied to the agent one line above. **No secret was printed**; the shell was replaced with `exec bash -l`. Second instance of this asymmetry after S73's operator-side `git checkout` exposure. Recorded as **§D.32.6**. |
| **Status** | **RESOLVED-IN-PART S74** — structural finding (untracked config) CLOSED; Gaps 1 and 2 CLOSED by rule additions; **Gap 3 (mode switchable, no disk trace) OPEN**, and the sibling-clone / permission-file asymmetry OPEN per §D.32.6. `.claude/settings.json` **staged, uncommitted** at capture. |

### TD-S73-NEW-9 (S3 priority) — approved diffs are not hunk-independent, and a partial application produced a quieter failure than the defect it was fixing

| Field | Value |
|---|---|
| **Priority** | **S3.** Process, not code. Caught before commit; would have shipped a false pass. |
| **Discovered** | Session 73 (2026-09-06), applying the TD-S72-NEW-9 fix through Claude Code. |
| **Component** | Deploy discipline · `MERDIAN_ClaudeCode_Guardrails.md` · Doc Protocol v4 |
| **What happened** | A four-hunk diff was approved as a whole and applied hunk-by-hunk with a prompt each. One hunk (the `main()` aggregation consuming the new `NA` verdict) was rejected on operator instruction, on the mistaken belief that a fifth prompt indicated scope creep. It did not: one hunk had legitimately split into two Edit calls because its two regions were non-contiguous and each needed a unique anchor. |
| **The resulting state** | `NA` was defined and returnable, but `main()` still counted only `FAIL` and `WARN`. A back-dated run would have returned `NA`, found `nfail == nwarn == 0`, and printed **"clean session — capture + compute complete and symmetric", exit 0**. The old behaviour was loud and wrong; the intermediate state was **quiet and wrong** — strictly worse, and the exact stable-lie shape ADR-001 exists for. |
| **Root cause** | Hunks are **not independent** when one introduces a value another must consume. Nothing in the guardrails or Doc Protocol names partial application as a failure mode; both assume a diff is applied or not applied. |
| **Contributing** | The operator was asked to approve prompts whose diff bodies were not visible in the relayed transcript. The correct instruction was "show me the hunk," not "reject it." |
| **Proper fix** | State producer/consumer coupling when proposing a multi-hunk diff, and verify all hunks landed (`git diff` against the proposal) before running or committing. Add to guardrails §4. |
| **Cross-ref** | ADR-001 (stable lies) · guardrails C-17 · TD-S72-NEW-9. |
| **Status** | **OPEN.** |

### TD-S72-NEW-4 (S3 priority) — `gex_strike_snapshots` carries a duplicate index and a third that is redundant against the composite

| Field | Value |
|---|---|
| **Priority** | **S3.** Write amplification and space only; no correctness impact. |
| **Discovered** | Session 72 (2026-09-05), `pg_indexes` while diagnosing the 57014. |
| **Component** | `gex_strike_snapshots` |
| **Symptom** | `idx_gss_symbol_ts` and `ix_gex_strike_snap_sym_ts` are **byte-identical** — both `btree (symbol, ts DESC)`, two names for one index built by different sessions. Both are additionally redundant against `idx_gss_symbol_ts_strike` = `btree (symbol, ts DESC, strike)`, of which `(symbol, ts DESC)` is a leading prefix. Three indexes, one access path. |
| **Cost** | Two unnecessary index writes per row on an append-only table taking ~28k rows/day, plus space. |
| **Constraint on the fix** | The TD-S72-NEW-2 lateral currently plans against `ix_gex_strike_snap_sym_ts` **specifically**. Whichever index survives must cover `(symbol, ts DESC)`. Re-run `EXPLAIN` after any drop — do not assume the planner falls through to the composite. |
| **Bloat theory refuted** | `last_autovacuum = null` looked alarming and means nothing here: 13,506 dead tuples against 1,317,355 live is 1% on an append-only table that has never crossed autovacuum's threshold. Raised in-session and abandoned. Stale planner statistics (`last_autoanalyze` 7 days old) remain a live secondary candidate. |
| **Proper fix** | Measure `pg_relation_size` on all three, drop the two redundant, verify the plan is unchanged. Production DDL — own change, own verification pass. |
| **Status** | **OPEN.** |

### TD-S72-NEW-12 (S2 priority) — byte-size comparison across storage tiers is invalid under `core.autocrlf=true`; Doc Protocol v4's four-tier hash discipline needs correcting

| Field | Value |
|---|---|
| **Priority** | **S2.** Produced **two false alarms in one session**, one of which briefly blocked ADR-023 D1. |
| **Discovered** | Session 72 (2026-09-05), twice. |
| **Component** | Doc Protocol v4 hash verification · session-open baseline procedure |
| **Instance 1** | PK-mounted `ADR-022` (13,868) and `ADR-023` (12,586) were compared against expected 17,157 / 17,095 and reported as pre-amendment. **The retrieval index held the amended text all along.** The filesystem mount and the retrieval index are distinct stores — D.29.10 exactly, committed while reading the session brief that opens with it. |
| **Instance 2** | `ws_feed_zerodha.py` measured 18,289 on Local and 17,812 on EC2 with `git status` clean on both — reported as a divergence. It is `core.autocrlf=true`: `git ls-files --eol` returns `i/lf w/crlf`, the gap is exactly 477 lines × one `\r`, and all three `git hash-object` values match at `f84368e9...`. |
| **Rule** | Byte size is a valid identity check **only within one storage tier**. Cross-tier comparison must use `git hash-object` or a hash taken after EOL normalisation. Under `autocrlf=true` every text file will disagree by line count between Local and EC2, permanently and correctly. |
| **Proper fix** | Amend Doc Protocol v4's verification procedure; state the rule in CLAUDE.md. Session-open baselines quoted in bytes must specify which tier they were measured on. |
| **Cross-ref** | D.29.10 · Doc Protocol v4 Rule on four-tier verification. |
| **Status** | **OPEN.** |

### TD-S71-NEW-14 (S1 priority) — `dhan_scripmaster` has no scheduled reload, and futures contract resolution has no fallback: the table silently expires at every roll

| Field | Value |
|---|---|
| **Priority** | **S1 at discovery.** Four symbol-sessions of primary ingestion lost, unrecoverable. Cron fix applied same session; the class remains. |
| **Discovered** | Session 71 (2026-08-29), from `eod_health_check --date 2026-08-28` reporting `index_futures_snapshots 0 rows`. |
| **Component** | `dhan_scripmaster` · `capture_index_futures_snapshot_local.py` (S56 resolver) · `reload_dhan_scripmaster.py` |
| **Symptom** | `[WARN] Could not resolve contract for NIFTY: No non-expired valid futures contract found in dhan_scripmaster` — both symbols, `rc=1`. |
| **Root cause** | The resolver filters `INSTRUMENT = 'FUTIDX'`, `UNDERLYING_SYMBOL = <symbol>`, `SM_EXPIRY_DATE >= today`, and takes the nearest. `dhan_scripmaster` held only NIFTY to **2026-08-25** and SENSEX to **2026-08-27** — every contract expired. **Neither `reload_dhan_scripmaster.py` nor `reload_dhan_scripmaster_from_csv.py` was in any crontab.** The table had been reloaded by hand, and the 2026-08-27 roll is the first that was missed. |
| **Measured loss — per symbol, not per session** | Row counts decoded as one symbol dropping out the session after **its own** contract expired: 08-24 NIFTY 151 + SENSEX 151 · 08-25 both 151 · **08-26 SENSEX only** · **08-27 SENSEX only** · **08-28 neither**. So the loss is **four symbol-sessions**: NIFTY 08-26/27/28 and SENSEX 08-28 — not the single session the FAIL implied. |
| **Not backfillable** | The script captures a live Dhan LTP; there is no historical equivalent. `hist_future_bars_1m` has no rows since 08-25, so no reconstruction path. The expired August `SECURITY_ID`s were replaced by the reload swap. **`basis_context_snapshots` and every ENH-07 derivative carry a permanent NIFTY gap across 08-26→08-28.** |
| **Fix applied** | `reload_dhan_scripmaster.py --apply` run 2026-08-29: 197,254 rows staged and swapped through the transactional `swap_dhan_scripmaster()` RPC (staging + RPC swap, so the live table is never empty mid-reload). NIFTY FUTIDX now 2026-09-29→11-23, SENSEX 2026-09-24→11-26. Both captures resolve the September contract and write. Crontab 46 → **52 lines**, new entry `30 01 1,15 * * … reload_dhan_scripmaster.py --apply >> logs/scripmaster.log`. Twice monthly so one failed run is not a month of exposure; the loader is idempotent and its contract gate aborts before any write if NIFTY/SENSEX FUTIDX validation fails. |
| **Residual — the class, not the instance** | This is the **third** unscheduled-invoker finding in Session 71, after the Pine generator (TD-S71-NEW-7) and the S70 migration's dropped third `.bat` line. All three produced a plausible empty or stale result rather than an error. **Proper fix: a standing reconciliation of every production script at repo root against the crontab, listing those with neither a cron entry nor a documented manual trigger.** |
| **Also observed, filed here** | `capture_index_futures_snapshot_local.py` **ignores its symbol argument** — invoked with `NIFTY` it resolves and writes both symbols. The paired NIFTY/SENSEX crontab lines therefore duplicate every call. Harmless but wasteful; the pair should collapse to one line. |
| **Cross-ref** | TD-S71-NEW-15 (the health check that passed it) · TD-S69-NEW-2 · TD-S71-NEW-7 · ENH-07 (basis). |
| **Status** | **OPEN** — cron fix applied; the unscheduled-invoker reconciliation and the duplicate-invocation cleanup remain. |

### TD-S71-NEW-1 (S2 priority) — `merdian_reference.json` does not cover the files and tables the register's own read-rule points at

| Field | Value |
|---|---|
| **Priority** | **S2.** Not a runtime defect. It silently invalidates a governance rule that sessions rely on. |
| **Discovered** | Session 71 (2026-08-22), at session open, probing the registry for the files S71's own priorities 1–3 would touch. |
| **Component** | `docs/registers/merdian_reference.json` → `files` (129 entries) and `tables` (50 entries) |
| **Symptom** | Absent from `files`: `pull_token_from_supabase.py`, `capture_cas_close.py`, `backfill_cas_close_from_daily.py`, `capture_spot_1m_v2.py`, `eod_health_check.py`, `refresh_equity_intraday_last.py`, `wsfeed_preflight.sh`. Absent from `tables`: `system_config`, `script_execution_log`, `hist_spot_bars_1m`, `india_vix_history`, `india_vix_daily`, `vix_percentile_reference`. |
| **Root cause** | New artefacts are recorded in session-scoped addenda (`_s70_addendum.new_scripts`) rather than promoted into `files`/`tables`. The addendum is a changelog; the map never absorbs it. |
| **Why it matters** | CLAUDE.md forbids asking the operator for file locations *on the grounds that* `files.<filename>` holds them. The rule rests on coverage the registry does not have, so the failure mode is a session that either guesses a path or burns a round trip asking for one the rule says not to ask for. |
| **Proper fix** | Promote every `_s7N_addendum.new_scripts` entry into `files` at doc-close, and add the six tables. Then add a coverage assertion: every `.py` at repo root must appear in `files`. |
| **Cost to fix** | ~45 min for the backfill; the assertion is ~15 min. |
| **Blocked by** | nothing. |
| **Cross-ref** | TD-S71-NEW-2 (same file, header freshness) · TD-S61-NEW-3 (vestigial `_meta`). |
| **Status** | **OPEN.** |

### TD-S71-NEW-3 (S3 priority) — the VIX history read has no `ORDER BY`; its correctness depends on unspecified row ordering

| Field | Value |
|---|---|
| **Priority** | **S3.** Currently benign. It is correct by accident, not by construction. |
| **Discovered** | Session 71 (2026-08-24), by the TD-S70-NEW-5 instrumentation on its first live run. |
| **Component** | `compute_volatility_metrics_local.py::load_vix_history_rows()` |
| **Symptom** | `sb.select(table=…, limit=5000)` with **no order clause**, against a PostgREST hard cap of 1,000 rows. `india_vix_history` holds 1,782, so 782 are silently dropped. Measured: the retained 1,000 are the **newest** (`range=2022-02-28..2026-03-11`), so `compute_vix_percentile`'s `eligible[-252:]` is correctly anchored at the table's tail **today**. |
| **Root cause** | Physical row order happens to be insertion order and the read happens to return the tail. Nothing guarantees it. |
| **Why it matters** | A rewrite, `VACUUM FULL`, or a bulk backfill of the 2019–2022 range could shift which 1,000 rows come back. If the retained set moved toward the old end, the 252-day percentile window would move with it silently. |
| **Proper fix** | Add an explicit descending order on the date column and cap the fetch at what the computation needs (252 rows suffices). Requires reading `core/supabase_client.py::select()`'s signature first — not guessed. |
| **Cost to fix** | ~20 min. |
| **Blocked by** | nothing. |
| **Cross-ref** | TD-S70-NEW-4 (the frozen writer) · TD-S70-NEW-5 (RESOLVED, spawned this). |
| **Status** | **OPEN.** |

### TD-S71-NEW-5 (S3 priority) — `run_ingest.sh` `set -eo pipefail` makes its own `END … rc=` line unreachable on failure

| Field | Value |
|---|---|
| **Priority** | **S3.** Small, and it degrades exactly the log an outage reconstruction reaches for. |
| **Discovered** | Session 71 (2026-08-24), reading the wrapper during the ADR-022 D1 audit. |
| **Component** | `run_ingest.sh` |
| **Symptom** | `set -eo pipefail` terminates the script the moment `ingest_option_chain_local.py` exits non-zero, so `rc=$?` and the `[run_ingest.sh] … END symbol=… rc=…` line never execute. Successful runs log START **and** END; failed runs log START and stop. |
| **Why it matters** | In `cron.log` a crash and a hang are **indistinguishable** — both look like a START with no END. `run_ingest.sh` is invoked by six crontab lines, so this is the dominant shape in that file. |
| **Proper fix** | Capture `rc` with the errexit trap disabled around the call (`set +e; python3 …; rc=$?; set -e`) so the END line always writes, then exit `$rc`. |
| **Cost to fix** | ~10 min. |
| **Blocked by** | nothing. |
| **Status** | **OPEN.** |

### TD-S71-NEW-8 (S3 priority) — `capture_premarket_0908.py` is an orphan whose filename encodes an instant that ceases to exist on 2026-09-07

| Field | Value |
|---|---|
| **Priority** | **S3.** Dead code, but dead code that looks authoritative. |
| **Discovered** | Session 71 (2026-08-24), grepping for pre-open anchors ahead of the dated audit. |
| **Component** | `capture_premarket_0908.py` |
| **Symptom** | A 33-line wrapper that shells out to `capture_market_spot_snapshot_local.py`. **Nothing invokes it** — the crontab calls the target directly (now `41 3`). Its filename asserts a 09:08 pre-open instant that the 2026-09-07 restructure replaces with a randomised 09:08–09:10 close. |
| **Why it matters** | A future session grepping for the pre-open path finds a file named for the exact instant and may treat it as the live entrypoint. |
| **Proper fix** | Delete, or move to an `archive/` path with a header noting its supersession. |
| **Cost to fix** | ~5 min. |
| **Blocked by** | nothing. |
| **Cross-ref** | The 2026-09-07 dated audit — seven other live files still anchor on the pre-open instant, including `build_momentum_features_local.py`, which is **ENH-119's own input**. |
| **Status** | **OPEN.** |

### TD-S71-NEW-11 (S1 priority) — SECURITY: operator `.env` was printed in full to a session transcript; long-lived credentials require rotation

| Field | Value |
|---|---|
| **Priority** | **S1.** Live credential exposure. Several of the exposed secrets do not expire. |
| **Discovered** | Session 71 (2026-08-24), immediately, by the assistant that caused it. |
| **Component** | `bin/wsfeed_preflight.sh` · `.env` on MERIDIAN AWS |
| **Symptom** | The assistant instructed `bash -x bin/wsfeed_preflight.sh`. Line 4 of that script is `. ./.env`, and `-x` traces sourcing **variable by variable**. The full environment printed to the transcript. |
| **Exposed, by remaining exposure life** | `DHAN_TOTP_SEED` + `DHAN_PIN` (standing 2FA bypass, indefinite — worst item) · `SUPABASE_SERVICE_ROLE_KEY` (RLS bypass, `exp` 2036) · `BREEZE_API_KEY` / `BREEZE_API_SECRET` (SEBI-whitelisted IP) · `ZERODHA_API_KEY` · `TELEGRAM_BOT_TOKEN` · `DHAN_API_TOKEN` and `ZERODHA_ACCESS_TOKEN` (roll at the next daily refresh, lowest concern). |
| **Root cause** | The assistant had the script's contents on screen when it composed the command. The trace was the entire point of `-x`; the consequence was foreseeable and not checked. |
| **Correct form of the same diagnostic** | Run the Python check alone with the environment already loaded, or wrap the sourcing block in `set +x` / `set -x`. Both yield the identical result — which was `rc=0`. |
| **Proper fix** | Operator-owned rotation in the order above. |
| **Prevention shipped** | New CLAUDE.md non-negotiable: never `bash -x`, `set -x`, `cat`, or `grep` against `.env` or any script that sources it. Existence checks use `[ -n "$VAR" ] && echo set`. |
| **Blocked by** | nothing. |
| **Status** | **OPEN — rotation outstanding.** |

### TD-S71-NEW-12 (S3 priority) — `.gitignore` `*_PRE_S*` silently swallows the crontab backups it was never written for

| Field | Value |
|---|---|
| **Priority** | **S3.** The backup exists; it just isn't durable. |
| **Discovered** | Session 71 (2026-08-24), when the new crontab backup did not appear as untracked. |
| **Component** | `.gitignore:108` (`*_PRE_S*`) · `docs/registers/aws_crontab_PRE_S71_*.txt` |
| **Symptom** | `git check-ignore -v` → `.gitignore:108:*_PRE_S*`. The rule was written for `_PRE_S<N>.py` code backups and also matches the crontab backup, which therefore lives only on the box's EBS volume. |
| **Why it matters** | That volume is the subject of TD-S69-NEW-1. A rollback artefact for a 46-line production crontab should not be single-copy on the machine it protects. |
| **Proper fix** | Name crontab snapshots outside the pattern (e.g. `aws_crontab_S71_20260824.txt`) so they commit, or add a negation for `docs/registers/aws_crontab_*`. |
| **Cost to fix** | ~5 min. |
| **Blocked by** | nothing. |
| **Status** | **OPEN.** |

### TD-S71-NEW-13 (S3 priority) — VERIFY: deep-ITM option `ltp` prints below intrinsic value; anything computing extrinsic from `ltp` inherits it

| Field | Value |
|---|---|
| **Priority** | **S3** pending measurement — could rise if any live consumer derives extrinsic or moneyness from `ltp`. |
| **Discovered** | Session 71 (2026-08-27), from an operator screenshot of the Dhan positions view on SENSEX expiry morning. **Not yet verified against MERIDIAN data.** |
| **Component** | `option_chain_snapshots.ltp` · any consumer computing extrinsic, moneyness, or synthetic spot |
| **Symptom** | At SENSEX 77,456.27, the 78200 PUT printed `707.65` against intrinsic 744, and the 78500 PUT `1,002.85` against intrinsic 1,044 — both ~40 points **below intrinsic**, which is not an executable price. The ITM calls at the same instant carried normal positive extrinsic (77000C 506.95 vs 456 intrinsic). |
| **Probable cause** | Stale last-traded prints on thin far-ITM BSE weekly strikes. `ltp` is the last trade, not a live quote; `bid`/`ask` would be current. Asymmetric here because the put side was the illiquid one. |
| **Why it matters** | A negative computed extrinsic is a silent nonsense value. If it flows into any tier, ranking, or context field it will bias toward the least liquid strikes. |
| **Proper fix** | First **measure**: `select count(*) from option_chain_snapshots where option_type='PE' and ltp < (strike - spot) and strike > spot` (and the CE mirror), by symbol and moneyness bucket, SQL committed to `docs/research/` per ADR-009. Then decide whether to prefer mid-of-`bid`/`ask` for far-ITM strikes. |
| **Cost to fix** | ~30 min to measure; fix scoped after. |
| **Blocked by** | nothing. |
| **Status** | **OPEN — unverified.** |

### TD-S70-NEW-1 (S2 priority) — `CURRENT.md` is 661 KB of which 98% is superseded session blocks, and it is read second at every session open

| Field | Value |
|---|---|
| **Priority** | **S2.** Not a runtime defect; a per-session cost paid forever. |
| **Discovered** | Session 70 (2026-08-22), when the PK viewer refused to render the file. |
| **Component** | `docs/session_notes/CURRENT.md` |
| **Symptom** | 684 KB / 2,890 lines. **45 `## Previous session` blocks.** The portion matching the file's actual job — Last session + This session — is **~11 KB**; the other **~650 KB** is an archive duplicating `session_log.md`. The file exceeds the render threshold in both the project-knowledge viewer and the chat file pane, so it cannot be skimmed by eye. |
| **Root cause** | The file's own header states *"Living file. Overwritten at the end of every session."* It has not been overwritten — each close prepends a new block and demotes the old one, so it is append-only in practice. Doc Protocol v4 Rule 7 describes it as the live session resume and does not specify a retention bound. |
| **Cost of leaving it** | CLAUDE.md's reading order sends every session to `CURRENT.md` second, before `tech_debt.md` and the System Map. Every session therefore pays context on ~650 KB of superseded state. That is the real cost, ahead of the render problem. |
| **Proper fix** | Retain **Last session + This session**, plus at most one Previous for continuity. Everything older already lives in `session_log.md`, the archive of record. Expected result ~20 KB. **Two preconditions:** (a) verify each dropped block's content is genuinely represented in `session_log.md` — the log entry is one dense line where the CURRENT block is a table, so the *format* differs even where content does not, and any detail the log dropped must move first; (b) add a retention bound to Doc Protocol v4 Rule 7, or it silently re-accretes. |
| **Data-integrity note** | The blocks are **not sequential** — S64 is missing between S65 and S63, and the tail stops at S51 while the file contains 45 blocks. Some are duplicated or out of order. An archive nobody can open is an archive nobody audits. |
| **Cost to fix** | ~1 session (the `session_log.md` coverage check is the work; the truncation is minutes). |
| **Blocked by** | nothing. |
| **Cross-ref** | Doc Protocol v4 Rule 7 · `session_log.md` as archive of record. |
| **Status** | **OPEN.** |

### TD-S70-NEW-4 (S2 priority) — `india_vix_history` has no writer and has been frozen at 2026-03-11 for five months; `vix_percentile` is scored against a stale reference distribution

| Field | Value |
|---|---|
| **Priority** | **S2 — downgraded from S1 on evidence.** Not a gating defect; see below. |
| **Discovered** | Session 70 (2026-08-22), during the ingestion-health sweep. |
| **Component** | `india_vix_history` · `india_vix_daily` (**0 rows**) · `vix_percentile_reference` (**0 rows**) · `compute_volatility_metrics_local.py::load_vix_history_rows` |
| **Symptom** | `india_vix_history` holds 1,782 rows, newest `2026-03-11`. A `grep` for writers returns only `fetch_india_vix.py` (live NSE `allIndices` scrape, returns the current value) and readers — **nothing writes the history table.** It was loaded once and abandoned. `compute_vix_percentile()` therefore ranks today's VIX against a distribution ending in March. |
| **Why it is NOT S1** | `build_trade_signal_local.py:462` reads `prefer(vol_features["vix_regime"], vol_features["vix_context_regime"])`. `prefer()` returns the first non-`None`/non-empty value; `vix_regime` is computed directly from the live NSE value via fixed bands and is always populated. **`vix_context_regime` is therefore unreachable on the gating path**, and no signal decision has been made on the stale distribution. The operator's own observation — that Marketview's VIX matches TradingView — is correct and was the tell. |
| **What is still wrong** | `vix_percentile` and `vix_percentile_regime` are written to `volatility_snapshots` and `signal_snapshots` every cycle and are surfaced by `measurement_health_snapshot_local.py`. A plausible, well-formed, wrong column sitting in a research table is how a cohort gets quietly poisoned later. |
| **Proper fix** | ENH-118 P0 (India VIX writer) is the right home. Minimal form: a ~20-line `capture_india_vix_eod.py` writing `(trade_date, vix_value)` after close on the AWS crontab, plus a 2026-03-11→present backfill (Kite `historical_data` on the INDIA VIX instrument token is the likely source; NSE `allIndices` is spot-only). **Open design question: rolling 252-day window or all-history for the percentile reference** — all-history means the 2020 and 2026-03 spikes permanently compress today's percentile. Operator's call; it changes the writer's retention behaviour. |
| **Schema note** | The column is `vix_value`, not `vix_close`. `extract_history_vix()` tries eight name variants, which is itself how a wrong-schema assumption still resolved. |
| **Cost to fix** | ~1 session including backfill. |
| **Blocked by** | the rolling-vs-all-history decision. |
| **Cross-ref** | ENH-118 P0 · TD-S70-NEW-5 (the mechanism that hid it) · Assumption Register D.28.5. |
| **Status** | **OPEN.** |

### TD-S69-NEW-2 (S1 priority) — `scripts/eod_health_check.py` returned `[OK]` on 2026-08-12 while pin/accel, the M5 detector and the GEX read path were all broken: it asserts on none of them

| Field | Value |
|---|---|
| **Priority** | **S1.** This is why a total loss of pin/accel zones ran for weeks and was found by staring at TradingView rather than by an alert. |
| **Discovered** | Session 69 (2026-08-12). |
| **Component** | `scripts/eod_health_check.py` |
| **Symptom** | Clean `[OK]` for the 08-12 session while `v_gex_strike_pin_zone` / `v_gex_strike_accel_zone` were returning `57014`, `ict_zones` was 53 trading days stale, and the Pine overlay had been rendering without positioning zones for weeks. |
| **Root cause** | The check covers base-table freshness for the tables it knows about and explicitly disclaims the rest ("a green DB here does not vouch for Marketview render"). **It does not look at derived surfaces at all**, and it does not look at `ict_zones`. Writer-state and read-path-state are independent facts (Assumption Register D.27.5). |
| **Proper fix** | Extend to assert: (a) freshness on `ict_zones`; (b) freshness on `gex_strike_snapshots`; (c) **non-empty return** from `v_gex_strike_pin_zone` and `v_gex_strike_accel_zone` — the assertion must be "rows came back", not "the table has data", because the whole failure mode was a healthy table behind a timing-out view; (d) disk headroom on the box (TD-S69-NEW-1). |
| **Workaround** | None. The gap is the defect. |
| **Cost to fix** | ~0.5 session. |
| **Blocked by** | nothing. |
| **Cross-ref** | ADR-021 open follow-up 3 · Assumption Register D.27.5 · §D.18.2 (instrument the failure before extending the layer). |
| **Status** | **OPEN — P1 into S70.** |

### TD-S69-NEW-3 (S2 priority) — `fetch_positioning_landscape` has no ADR-018 D2 recency floor; the ADR-021 speed fix converts a loud timeout into a silent stale read

| Field | Value |
|---|---|
| **Priority** | **S2 — latent, but created by a fix.** |
| **Discovered** | Session 69 (2026-08-13), immediately after applying the ADR-021 migration. |
| **Component** | `generate_pine_overlay.py::fetch_positioning_landscape()` |
| **Symptom** | None yet — latent. If the GEX writer stalls, the generator will emit **stale pin/accel zones, returned instantly**, instead of failing loud. |
| **Root cause** | S69 added a recency floor to `fetch_intraday_zones` (this is what made the Local generator's 106–110 zone count honest) but **not** to `fetch_positioning_landscape`. Before ADR-021 a stalled writer produced a `57014` timeout — loud. After ADR-021 the same stall produces plausible, fast, wrong output. |
| **Proper fix** | Add the same `ts >= today` guard, per ADR-018 D2. Generalise the rule: **every latency fix on a read path ships with its recency floor** — speed without a freshness floor manufactures exactly the ADR-001 stable lie the system exists to refuse. |
| **Cost to fix** | ~15 min, same file, same Canon-v3 patch pass as the time-anchor fix. |
| **Blocked by** | nothing. |
| **Cross-ref** | ADR-021 open follow-up 1 · ADR-018 D2 · ADR-001 · Assumption Register D.27.8. |
| **Status** | **OPEN — do it in the same pass that commits the S69 Pine patch.** |

### TD-S60-NEW-5 (S2 priority) — `core/config.py` hardcodes Windows `BASE_DIR = C:\GammaEnginePython`; loads `.env` from a path that doesn't exist on AWS; FILED

| | |
|---|---|
| **Severity** | S2 (latent portability landmine; masked today because callers self-load or export env, but any clean `core.config`-routed invocation on AWS raises). |
| **Discovered** | 2026-06-26 (Session 60, during the TD-S60-NEW-3 helper smoke-test) |
| **Component** | `core/config.py` — `BASE_DIR = Path(r"C:\GammaEnginePython")`; `ENV_FILE = BASE_DIR / ".env"`; `load_dotenv(ENV_FILE)` is a no-op on AWS. |
| **Symptom** | `get_settings()` raises `Missing required environment variable: SUPABASE_URL` on a clean AWS invocation (proven: the v1 gate via `SupabaseClient` fail-opened F/F/F because `get_settings()` found no creds). Every `core.config`/`SupabaseClient`-routed script on AWS is silently dependent on env being loaded by some other prior `load_dotenv()`. |
| **Root cause** | Hardcoded Windows path in `core/config.py`. |
| **Workaround** | Scripts self-load `.env` (`load_dotenv()`) or rely on exported env; the S60 gate helper deliberately bypasses `core.config` for exactly this reason. |
| **Proper fix** | Derive `BASE_DIR` from `__file__` (repo root relative to `core/`), not a hardcoded OS path. |
| **Cost to fix** | ~30 min, but it's load-bearing (used everywhere) so it needs a careful test pass — not a Friday change. |
| **Blocked by** | nothing. |
| **Related** | TD-S60-NEW-3 (surfaced it; the gate helper bypasses core.config because of it). |


### TD-S57-NEW-3 (S3 priority) — Enhancement Register has a dual structure with conflicting per-ENH status

| Field | Value |
|---|---|
| **Severity** | S3 |
| **Filed** | 2026-06-19 (Session 57) |
| **Component** | `docs/registers/MERDIAN_Enhancement_Register.md` (+ stale duplicate `MERDIAN_Enhancement_Register_v5.md`) |
| **Symptom** | The register layers a newer Part 1–6 structure on top of a legacy Tier/Summary-Table structure that was never reconciled, so the same ENH can carry two different statuses. Surfaced S57: ENH-02 (PCR) and ENH-07 (basis rate) read **COMPLETE** in Part 1 but **IN PROGRESS** in their Part 4 detail blocks and the legacy "Full Register" tables. The Part 4 detail is authoritative (ENH-02 writer built-but-orphaned by the S49 Local-disable; ENH-07 unbuilt) — the `v7=COMPLETE` flags were a stale bulk-flip. Corrected ENH-02/07 to IN PROGRESS this session, but the structural duplication remains. |
| **Root cause** | The v7 unified rewrite + subsequent per-session appends left the legacy `## Summary Table` (~L956) + `## Summary Table — Full Register` (~L1407) + Tier 1–4 sections alongside the canonical Part 1 status summary; no single source of truth for status. Plus `MERDIAN_Enhancement_Register_v5.md` (max ENH-42, no last-updated) is a stale duplicate file that should not exist. |
| **Workaround** | Treat Part 1 + Part 4 as authoritative; ignore the legacy tables. |
| **Proper fix** | Collapse to a single status source (Part 1 ↔ Part 4 cross-checked), delete the legacy `Summary Table` / `Full Register` / Tier tables (or mark them ARCHIVE-only), and delete the stale `MERDIAN_Enhancement_Register_v5.md`. Bigger than an inline edit — a dedicated register-reconciliation pass. |
| **Cost to fix** | ~0.5–1 session (status reconciliation audit across ~114 ENHs + table removal + duplicate-file delete). |
| **Blocked by** | Nothing. |
| **Related** | Surfaced during the S57 ENH-02/07 fold + ENH-115/ENH-SDM filing. |

### TD-S53-NEW-5 (S2 priority) — S52 observability monitors report false state (both directions) + watchdog shares the patient's failure chain
> **UPDATED Session 55 (2026-06-17); env-independence half ALREADY satisfied, 2 logic bugs remain, OPEN.** All monitors load env via load_dotenv() (absolute-path), NOT the source .env chain. Remaining: (a) 999-on-empty clamp in refresh_health_dashboard.py get_minutes_old (returns 999 on any exception incl empty ts, false STALE); (b) monitor_orchestrator_health.py + refresh_health_dashboard.py query a script_execution_log row the orchestrator NEVER writes, permanent false no-orchestrator. A/B (decide rested): (A) self-instrument orchestrator with per-cycle ExecutionLog row (schema-safe, duration_ms=bigint) vs (B) repoint monitors at volatility_snapshots.ts. Fold Dhan-token 26h staleness monitor here.

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-12 (Session 53) |
| **Component** | refresh_health_dashboard.py (999 age-clamp), monitor_orchestrator_health.py (false-negative orchestrator check), all four S52 monitors (shared `source .env` chain) |
| **Symptom** | Monitors report unreliable state in both directions: refresh_health_dashboard.py clamps age to 999 and reports STALE on tables that are actually fresh; monitor_orchestrator_health.py reports 'no orchestrator in last 5 min' (false-negative) after a confirmed run. Architecturally, all four monitors load env via the same `cd … && source .env` chain as the capture layer, so in S53 they died together with what they were supposed to watch (watchdog + patient). |
| **Root cause** | 999 age-clamp logic + an over-strict/incorrect freshness window in the orchestrator check; plus a design flaw — monitors must not share the env-loading failure chain of the systems they monitor. |
| **Workaround** | Do NOT trust the monitor labels — verify health via cron.log + Supabase row freshness directly. (The S53 SHELL fix resurrected the monitors, but their false-state logic is unfixed.) |
| **Proper fix** | Fix the 999 age-clamp and the orchestrator-freshness window; re-architect monitor env-loading to be independent of the `source .env` chain they watch (e.g. bash-shebang self-sourcing or absolute-path env injection). |
| **Cost to fix** | 1 session (monitor logic fixes + watchdog independence) |
| **Blocked by** | Nothing |

### TD-S46-NEW-2 — S3 deployment automation wrapper scripts (reduce manual workflow)

| Field | Value |
|---|---|
| **Severity** | S3 |
| **Filed** | 2026-06-06 (Session 46) |
| **Symptom** | AWS S3 deployment requires manual 6-step workflow (Local upload, AWS pull, verification); multiple commands to remember; non-idempotent if interrupted mid-cycle; no audit trail in log output |
| **Root cause** | S3 transfer vector is recent (S46); no wrapper automation exists; manual `aws s3 cp` commands require full context awareness + error handling |
| **Workaround** | Follow `MERDIAN_AWS_S3_Deployment_Mechanism_S46.md` documented workflow; `git pull` on AWS for code files; S3 only for non-git binary/vendor files or out-of-band backfill scripts |
| **Proper fix** | Create two idempotent wrapper scripts: **(1) `deploy_to_aws.ps1` (Local Windows)** — uploads core/ + orchestrator to S3, verifies S3 checksums, SSH signals AWS pull (single atomic operation, safe-to-retry). **(2) `pull_from_s3.sh` (AWS EC2 bash)** — pulls core/ + orchestrator from S3, verifies checksums, makes executable, restarts systemd/cron if needed (single atomic operation, safe-to-retry). Both should log start/end timestamps + action counts to `shadow_runner.log` for audit. Estimated 60-90 min total. |
| **Cost to fix** | 1 session (build + test on live EC2) |
| **Blocked by** | Nothing |
| **Related** | MERDIAN_AWS_S3_Deployment_Mechanism_S46.md (documentation); ADR-006 AWS migration scope (deployment layer); ENH-113 Phase 2.c AWS shadow runner |
| **Owner check-in** | 2026-06-06 (S46 filed as convenience enhancement) |

---

### TD-S41-NEW-5 — WCB writer 17% NIFTY active-weight degradation (pagination cap) + regime threshold disagreement Python 60/40 vs SQL 62.5/37.5

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-01 (Session 41) |
| **Symptom** | Two sub-findings discovered during Health dashboard build + WCB instrumentation work: **Sub-A** WCB writer (`build_wcb_snapshot_local.py`) shows 17% active-weight degradation on NIFTY — `coverage` reads 83.2% vs expected 100%. Root cause: `fetch_daily_breadth_rows()` paginates 50 tickers × ~150 history rows per ticker > 5000 PostgREST default limit; the trailing 11 tickers' history rows fall off the page. 11 missing constituents: SBIN, SBILIFE, SHRIRAMFIN, SUNPHARMA, TATACONSUM, TATASTEEL, TECHM, TITAN, ULTRACEMCO, WIPRO, TCS. RELIANCE shows `trade_date=2026-04-06` stale because its history rows are at the page boundary. SENSEX unaffected (30-ticker basket × ~150 rows = 4500 < 5000 limit). **Sub-B** Regime threshold disagreement between `classify_wcb_regime()` Python (`bullish ≥ 60`, `bearish ≤ 40`, else `transition`) and `compute_breadth_regime()` SQL function (`bullish ≥ 62.5`, `bearish ≤ 37.5`, else `transition`). Both produce `TRANSITION` today (51.5 falls in both ranges) but boundary cases (60-62.5 or 37.5-40) would disagree. |
| **Workaround** | Sub-A: live WCB scores reading slightly under-weighted; NIFTY shows TRANSITION 51.5/100 today, but with 17% missing weight the true score could be 50-65 range. Not actionable from operator-side. Sub-B: rely on Python writer's classification as canonical (it's what populates `weighted_constituent_breadth_snapshots.regime`); SQL function is unused downstream. |
| **Root cause** | Sub-A: `fetch_daily_breadth_rows()` uses default PostgREST pagination (1000 rows per page) and 5000 row hard cap; with 50 tickers × ~150 history rows = 7,500 expected rows, the call returns 5000 → trailing tickers fall off. Sub-B: Python and SQL functions were written at different sessions and drifted; no enforcement mechanism for parity. |
| **Proper fix** | **Sub-A** add `gte('trade_date', N_days_ago)` server-side filter where N=20 (typical lookback) to reduce per-ticker row count from ~150 to ~20; 50 × 20 = 1,000 rows fits in single page. Alternative is explicit pagination with `range(0, 9999).limit(10000)`. **Sub-B** Path A align Python to SQL 62.5/37.5 thresholds (fast closure, ~5 min); Path B align SQL to Python 60/40 (depends on whether SQL function is consumed anywhere — `pg_proc` audit didn't find consumers); Path C call SQL function from Python directly (cleanest, single source of truth). Path A is fastest; Path C is most durable. |
| **Impact** | Sub-A: WCB card reads slightly under-weighted on NIFTY; coverage shows 83.2% which is the symptom. Sub-B: boundary-case regime classifications could flip across Python/SQL boundary. |
| **Related** | `build_wcb_snapshot_local.py` (Sub-A target), `classify_wcb_regime()` Python helper (Sub-B target), `compute_breadth_regime()` SQL function (Sub-B target — verify consumers via `pg_proc` query before deleting), `weighted_constituent_breadth_snapshots.regime` column (final destination), `fetch_daily_breadth_rows()` (Sub-A root). |

---

### TD-S39-NEW-3 — `.env` containing live MERIDIAN Supabase anon key committed to public GitHub repo `balannavin-cyber1/meridian-connect` by Lovable

| | |
|---|---|
| **Severity** | S3 (hygiene — anon key is public-by-design and ships in browser bundle anyway; threat model bounded by RLS policies which post-S39 grant anon SELECT-only; not an active vulnerability but bad practice) |
| **Filed** | 2026-05-27 (Session 39 — surfaced during Lovable Turn 3 commit `6b95ded Added Supabase client init` review on github.com/balannavin-cyber1/meridian-connect/blob/main/.env) |
| **Symptom** | Lovable Turn 3 committed `.env` to repo root containing `VITE_SUPABASE_URL=https://kilmcowcikwdhvdxwofi.supabase.co` + `VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (full anon JWT) without prompting and without adding to `.gitignore`. Repo is public on GitHub. Any visitor to repo URL can read both values. |
| **Workaround in place** | (a) Anon key is public-by-design — it ships in the React bundle inlined at Vite build time via `import.meta.env.VITE_SUPABASE_URL/ANON_KEY` and is therefore visible to anyone who opens DevTools on the deployed dashboard; making the key visible on GitHub adds no incremental exposure. (b) Post-S39 RLS remediation grants anon SELECT only — worst-case exploitation is reading the data already visible to anyone with the dashboard URL. (c) `.env.local` placed on AWS at `/home/ssm-user/merdian-marketview/.env.local` (chmod 600, gitignored) ensures Vite picks up correct keys regardless of what's in committed `.env`. |
| **Root cause** | Lovable's auto-commit of `.env` is default behavior when it detects env-var usage in code — it doesn't gitignore env files by default. Differs from standard Vite scaffold which gitignores `.env*.local` patterns by default. |
| **Proper fix** | Operator local action: `cd <local clone> && git rm --cached .env && echo '.env' >> .gitignore && git commit -m "chore: gitignore .env, remove committed env file" && git push`. Lovable can update `.gitignore` (already attempted in Turn 5 polish — `e59c0ef Added env files to .gitignore` landed) but Lovable's git environment can't issue `git rm --cached` for already-committed files; operator workstation needed for the removal commit. ~5 min operator action. |
| **Impact if not fixed** | None operational. Hygiene-only — future security audit might flag, and key rotation costs +1 step (must also update committed `.env` if not yet removed from git history). Filed at S3 because trust model is sound but practice is sloppy. |
| **Related** | TD-S39-NEW-1 (Lovable auto-grant exposure — same family of Lovable-platform-trust issue), §D.21.2 Assumption Register S39 (anon-key-in-public-repo trust model VALIDATED — exposure is acceptable given RLS boundary, just bad practice), Lovable's gitignore commit `e59c0ef` from Turn 5 (committed gitignore additions but didn't remove already-committed `.env`). |

---

### TD-S39-NEW-4 — Orphan AWS Security Group `launch-wizard-2` not attached to any EC2 instance — cleanup pending

| | |
|---|---|
| **Severity** | S4 (cosmetic — no operational impact; orphan SG visible in AWS console but unattached) |
| **Filed** | 2026-05-27 (Session 39 — surfaced during AWS networking debug arc when operator was editing wrong SG for hours) |
| **Symptom** | AWS Security Group `launch-wizard-2` exists in eu-north-1 console alongside `launch-wizard-1` (which IS attached to MERIDIAN EC2 `i-0878c118835386ec2`). Operator spent hours editing `launch-wizard-2` inbound rules expecting `13.63.27.85:80` to become reachable from external networks; no effect because launch-wizard-2 was orphan/unattached. Resolution via IMDSv2 token query `curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/security-groups` returned `launch-wizard-1` confirming the attached SG; adding TCP 80 from 0.0.0.0/0 to launch-wizard-1 instantly resolved the connectivity issue. |
| **Workaround in place** | Operator now editing correct SG `launch-wizard-1`. `launch-wizard-2` remains orphan in console but unattached so its rules have no effect on any instance. |
| **Root cause** | AWS launch-wizard flow creates a new SG per wizard run if operator selects "Create security group" instead of "Select existing"; multiple wizard runs over time leave behind orphan SGs with `launch-wizard-N` naming pattern, visually indistinguishable from active SGs in the console list. |
| **Proper fix** | Delete `launch-wizard-2` from AWS EC2 Security Groups console (verify zero attachments first via `aws ec2 describe-instances --filters Name=instance.group-id,Values=<sg-id>`). ~2 min operator action. |
| **Impact if not fixed** | Cosmetic. Risk is recurrence of S39's debug pattern — future SG edits to launch-wizard-2 will have no effect and waste time. The IMDSv2 token query is now in operator memory as canonical attached-SG check so recurrence risk is bounded. |
| **Related** | §D.21.3 Assumption Register S39 (nginx default :80 inbound is sufficient for SG without verifying which SG is attached — REFUTED), ENH-110 Phase 1 AWS hosting infrastructure S39, MERDIAN_Deployment_Topology §1 (will gain note about IMDSv2 attached-SG verification pattern at S40 doc maintenance pass). |

---

### TD-S39-NEW-5 — Marketview "stale {N}s" badge contradicts 300s threshold setting — needs live-day verification

| | |
|---|---|
| **Severity** | S3 (verification-pending — could be legitimate genuine staleness post-market or display threshold not applying; impacts only operator's trust in freshness indicator) |
| **Filed** | 2026-05-27 (Session 39 — operator-visible during browser verification of Marketview at 03:36 IST post-market on a post-market data point) |
| **Symptom** | Marketview header strip shows badge "stale 612s" / "stale 314s" / "stale 295s" across multiple post-market browser refreshes on NIFTY view despite Lovable Turn 5 polish setting stale threshold from 60s → 300s and switching the canonical freshness clock from `market_state_ts` to `signal_snapshots.ts`. If signal_snapshots.ts genuinely is 10+ minutes stale post-market (market closes 15:30 IST, browser refresh at 15:35-15:55+ IST IST during S39), the badge is correctly firing as genuine staleness. If the 300s threshold is not actually applying (Lovable's change didn't reach this code path), the badge is firing spuriously at 5-10 min post-cycle window. Browser console + Network tab during operator session did not surface a clear answer. |
| **Workaround in place** | Operator-visible but not blocking — operator can interpret the badge as "data is N seconds stale, judge whether N is acceptable for current use case" without trusting the threshold semantics. |
| **Root cause** | Unknown without live-day verification. Three hypotheses: (a) threshold change applied but signal_snapshots.ts is genuinely 5-10 min stale during late-day windows because intraday cycles fire on 5-min cadence — within 300s threshold for the most-recent-cycle window but spilling over between cycles (legitimate); (b) Lovable's threshold change applied to wrong code path and the original 60s threshold still drives the badge logic; (c) threshold change applied but uses `Date.now()` vs `signal_snapshots.ts` in wrong direction (sign-flip) so it shows stale-when-fresh. Need live-day Network tab + JS console inspection to discriminate. |
| **Proper fix** | (a) S40+ live-day verification during 10:00-15:30 IST trading hours when cycles are firing every 5 min — observe whether badge stays under 300s during active cycles vs fires only after market close; (b) if badge stays under 300s during trading hours → label as legitimate post-market staleness, possibly update wording to "post-cycle Ns" or hide entirely outside market hours; (c) if badge fires spuriously during trading hours → Lovable Turn 7 prompt for debug + fix. ~15 min live-day observation + 0-15 min Lovable prompt. |
| **Impact if not fixed** | Operator-visible noise without operational impact during trading hours (operator interprets badge value not threshold semantics). Filed at S3 because reliable freshness indicator is a Phase 2 confluence-decision-quality property — operator needs to trust the badge for ENH-110 Phase 2 confluence detection rollout. |
| **Related** | ENH-110 Phase 1 Lovable Turn 5 polish prompt S39 (stale threshold 60s→300s + canonical clock signal_snapshots.ts), ADR-017 Operator Console Design Principles P5 motion-replaces-timestamps (badge is the motion-replacement-for-timestamp pattern; needs to be reliable to satisfy principle), Marketview surface at http://13.63.27.85/marketview. |

---

### TD-S38-NEW-2 — Dead `TIMEOUT_LIVE_DEFAULT` + `TIMEOUT_SHADOW_DEFAULT` constants in `run_option_snapshot_intraday_runner.py`

| | |
|---|---|
| **Severity** | S4 |
| **Filed** | 2026-05-26 (Session 38 — surfaced during P6 read of runner source for Intraday_Session_Start migration decision) |
| **Symptom** | `run_option_snapshot_intraday_runner.py` lines 30-31 declare module-level constants `TIMEOUT_LIVE_DEFAULT = 240` and `TIMEOUT_SHADOW_DEFAULT = 180`; these constants are **never referenced anywhere in the file**. `grep -n TIMEOUT_LIVE_DEFAULT run_option_snapshot_intraday_runner.py` returns only the declaration line. |
| **Workaround in place** | None needed — dead constants have zero runtime impact. They appear to be leftover from an earlier iteration where per-step timeouts were computed from these defaults; the current code uses explicit per-step timeouts `TIMEOUT_BREADTH=300 / TIMEOUT_WCB=180 / TIMEOUT_INGEST=240 / TIMEOUT_ARCHIVE=180 / TIMEOUT_GAMMA=240 / TIMEOUT_VOL=240 / TIMEOUT_MOMENTUM=240 / TIMEOUT_STATE=240 / TIMEOUT_SIGNAL=240 / TIMEOUT_SHADOW_SIGNAL=180` instead. |
| **Root cause** | Refactor leftover — likely from a transition where timeouts were per-pipeline (live vs shadow) to per-step. The defaults survived the refactor unreferenced. |
| **Proper fix** | Either (a) delete the 2 dead lines, or (b) wire them to per-step timeouts that share the same value (e.g. `TIMEOUT_INGEST = TIMEOUT_LIVE_DEFAULT`) so the relationship is explicit. ~5 min in next writer refactor. |
| **Impact if not fixed** | None operational. Cosmetic code hygiene. Discovery cost is in the wasted grep when future Claude reads the file expecting these constants to drive behavior. |
| **Related** | TD-061 (RESOLVED-FINAL S38 — TD-S38-NEW-2 surfaced during the runner source read that informed Intraday_Session_Start migration option A vs B decision), `run_option_snapshot_intraday_runner.py` is the 5-min intraday cycle orchestrator (heartbeat of live pipeline). |

---

### TD-NEW-B — `pg_cron` job failures invisible by default — needs polling daemon or session-start gate

| | |
|---|---|
| **Severity** | S1 (root cause of the 14+ day silent failure that escalated into the 2026-05-14 breadth cascade; without telemetry the next pg_cron failure class will also escalate silently before operator-visible symptoms surface) |
| **Discovered** | 2026-05-14 (Session 29 firefighting — surfaced during TD-NEW-A diagnosis when `cron.job_run_details` revealed 10 consecutive `delete-old-market-ticks` failures going back to at least 2026-04-30) |
| **Component** | `cron.job_run_details` Supabase system table records every cron run with `status` and `return_message`, but no MERIDIAN telemetry polls it. New cron jobs (jobid 46 `prune-market-ticks` from TD-NEW-A fix) introduce the same blind spot until polling is implemented. |
| **Symptom** | Pg_cron job fails every weekday for weeks; downstream consumer eventually breaks; root cause invisible until cascade. Example: `delete-old-market-ticks` failed 14+ weekdays before 2026-05-14 breadth outage. |
| **Root cause** | No telemetry layer for `cron.job_run_details`. `merdian_pipeline_alert_daemon.py` (Local) polls Supabase tables but does not query the `cron` schema. Telegram alert daemon doesn't subscribe to cron-failure events. |
| **Workaround** | Manual session-start checklist SQL (per CLAUDE.md B26 + Topology §6.11): `SELECT jobname, status, return_message, start_time FROM cron.job_run_details d JOIN cron.job j USING (jobid) WHERE start_time > now() - interval '7 days' AND status != 'succeeded' ORDER BY start_time DESC;` Empty result = healthy. Any rows = investigate. Operator session-start ritual addition. |
| **Proper fix** | Either (a) extension of `merdian_pipeline_alert_daemon.py` to query `cron.job_run_details` every N minutes and Telegram-alert on any `status != 'succeeded'` row in last 24h, or (b) dashboard widget on `merdian_live_dashboard.py` surfacing recent cron failures. Approach (a) closes the failure class more aggressively; (b) requires operator to look at dashboard. Recommend (a). |
| **Cost to fix** | 1-2 sessions (Telegram daemon extension or dashboard widget; needs decision on alert deduplication policy). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-14 |

---

### TD-NEW-C — `ws_feed_zerodha.py` silent on Supabase 500 / token errors (extends TD-NEW-9)

| | |
|---|---|
| **Severity** | S2 (extends TD-NEW-9 — when WS feed reconnect-loops because Supabase rejects writes with 500 statement_timeout, the script silently retries indefinitely; no Telegram alert; operator has to grep logs to discover. Today on 2026-05-14 6+ hours of silent retries before manual log tail revealed `Supabase write error 500: ... statement timeout`) |
| **Discovered** | 2026-05-14 (Session 29 firefighting — `tail -f logs/ws_feed.log` revealed silent reconnect loop after restart with new token; the error class was distinct from TD-NEW-9's silent-on-success class but shared the same script and same "operator must manually grep logs" workaround) |
| **Component** | `ws_feed_zerodha.py` running on MERIDIAN AWS — error logging is `print()` to log file only; no Telegram alert path; no escalation when retry count exceeds threshold |
| **Symptom** | Feeder receives ticks, attempts INSERT to `market_ticks`, Supabase returns 500 with statement_timeout, feeder retries indefinitely. No alert. Logs show repeated `Supabase write error 500: {...}` lines. Operator only finds out via downstream breadth-cascade symptoms hours later. |
| **Root cause** | No Telegram alert wiring in `ws_feed_zerodha.py`. The `import telegram_utils; telegram_utils.send_alert(...)` pattern used by other MERIDIAN scripts is not present. |
| **Workaround** | Operator session-start session-start log tail: `tail -n 50 logs/ws_feed.log` looking for `error` / `500` / `timeout` substrings. |
| **Proper fix** | Bundle with TD-NEW-9 (silent-on-success heartbeat). Same touch point — add: (a) every N=1000 ticks log `[HEARTBEAT] N ticks processed, last_ts=X, latency=Yms`; (b) on any non-200 Supabase response, log error + send Telegram alert (dedupe by 5-min window); (c) on N=3 consecutive Supabase errors in 60s, escalate Telegram alert priority. |
| **Cost to fix** | <1 session if merged with TD-NEW-9 (~45 min). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-14 |

---

### TD-NEW-9 — `ws_feed_zerodha.py` silent on success; no INFO heartbeat for nominal operation

| | |
|---|---|
| **Severity** | S2 (operational hygiene — when WS feed appears stuck, operator cannot distinguish "stuck/dead" from "running fine but silent on success" without grep'ing for new ticks landing in `market_ticks` table; cost is investigation time, not signal quality). |
| **Discovered** | 2026-05-13 (Session 28 — S28 drift period included a ~5 min WS feed outage triage where operator suspected stuck process; root cause was Zerodha-side connectivity which resolved via reconnect after 60s cycles, but script-side logs were silent making the diagnosis slower than necessary). |
| **Component** | `ws_feed_zerodha.py` running on MERIDIAN AWS — currently logs only on errors, reconnects, and structural events. No periodic heartbeat or per-N-tick INFO line. |
| **Symptom** | `tail -f logs/ws_feed.log` shows no output during nominal operation. Operator cannot confirm liveness without cross-checking `market_ticks` table writes (DB-side proxy). When MERDIAN_WS_Stop pkill fires at 15:32 IST, log just stops mid-silence; no "shutting down" or "tick count summary" line. |
| **Root cause** | Original `ws_feed_zerodha.py` design optimized for low log volume; no heartbeat-style instrumentation. Standard pattern across other long-running MERIDIAN scripts is per-cycle INFO line on `script_execution_log` table, but WS feed runs continuously not in cycles. |
| **Workaround** | Cross-check `SELECT MAX(ts) FROM market_ticks WHERE symbol='NIFTY'` to confirm liveness. Costs ~15-30 seconds during a triage. |
| **Proper fix** | Add per-N-tick INFO heartbeat (e.g., every 1000 ticks log `[HEARTBEAT] N ticks processed, last tick TIMESTAMP, latency Xms`). Plus shutdown handler: on SIGTERM/SIGINT log final summary before exit. Plus periodic (every 60s) liveness line even if 0 ticks processed in window — distinguishes "alive but idle" from "dead". |
| **Cost to fix** | <1 session (~30-45 min — ws_feed_zerodha.py is the touch point; tests local before AWS git pull). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-13 |

---

### TD-082 — `ingest_option_chain_local.py` contract miscalibration: backfill spike of 482 writes vs expected 50 logged as success (write-contract too permissive)

| | |
|---|---|
| **Severity** | S3 (degrades audit signal but doesn't break the pipeline; backfill-style spikes blur the line between "real run wrote 50 rows successfully" and "10x burst-write somehow" — both green) |
| **Discovered** | 2026-05-07 (Session 22 — surfaced during ingest_option_chain failure pattern audit; one row in `script_execution_log` showed 482 actual_writes for `option_chain_snapshots` where typical run writes ~50) |
| **Component** | `ingest_option_chain_local.py::_write_exec_log()` and the `contract_met` predicate |
| **Symptom** | One run on 2026-05-07 logged 482 rows written to option_chain_snapshots, compared to typical 50 per run. `contract_met=true` because predicate is `actual_writes >= 1`. The 482-row write was likely a multi-cycle accumulation from a partially-stuck process or coalesced retry, not a single intended cycle. |
| **Root cause hypothesis** | Either (a) script had a stuck cycle that buffered N cycles' worth of writes, or (b) write-batching accumulated mid-outage and flushed at recovery. Not yet diagnosed. |
| **Workaround** | None. Audit treats >300-row writes as anomaly worth investigating but doesn't fail the contract. |
| **Proper fix** | Tighten contract: `contract_met = (actual_writes >= 30 and actual_writes <= 100)` for option_chain_snapshots — outside that band is contract violation regardless of direction (zero rows = bad ingest, 500 rows = stuck or stale buffer). |
| **Cost to fix** | ~3 exchanges (read script, identify write path, tighten predicate, verify on backfill day). |
| **Blocked by** | TD-080 (Dhan outage diagnosis — same script, same module). |
| **Owner check-in** | 2026-05-07 |

---

### TD-005 — `option_execution_price_history` table marked DEPRECATED but not yet DROPPED

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | merdian_reference.json (E-06) |
| **Component** | `public.option_execution_price_history` |
| **Symptom** | Table exists in DB, takes up space, no writers, one stale reader pending migration |
| **Root cause** | `build_option_execution_outcomes_v1.py` migration pending |
| **Workaround** | Mark DEPRECATED in JSON, no new writes |
| **Proper fix** | Complete the outcome engine migration (E-06), then `DROP TABLE` |
| **Cost to fix** | 2 sessions |
| **Blocked by** | E-06 migration |
| **Owner check-in** | 2026-04-19 |

---

### TD-007 — `is_pre_market` column in `hist_spot_bars_1m` is vestigial

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-22 (OI-18 investigation during Session 5 — see `session_log.md` 2026-04-22 entry) |
| **Component** | `public.hist_spot_bars_1m` column + all producers and consumers (20+ files) |
| **Symptom** | Column is always written `false` by every producer (`capture_spot_1m.py`, `backfill_spot_zerodha.py`, all backfill and MTF builders). Every consumer filters `.eq("is_pre_market", False)` — the filter drops zero rows because no producer ever writes `True`. Dead code path masquerading as a semantic filter. |
| **Root cause** | Column was added with intent to mark pre-open (09:00–09:14 IST) bars so they could be excluded from analytics. Writer-side implementation was never completed; consumers were written defensively with the filter assumption. Nobody noticed because the filter is functionally a no-op. |
| **Workaround** | None needed — column works, just adds no value. Pre-open bars ARE being captured and used in analytics today; the filter is decorative. |
| **Proper fix** | Two mutually exclusive paths:<br>  (a) Make the column honest — writer computes `is_pre_market = (IST time of bar_ts between 09:00:00 and 09:14:59)`. All consumers accept the new filter semantics. Requires one-time backfill to retag historical pre-open rows from `False` to `True`. Multi-file, ~20 consumer files to review.<br>  (b) Drop the column + drop all `.eq("is_pre_market", False)` filters from consumers. Schema-breaking but simpler. ~1 session. |
| **Cost to fix** | 2–3 sessions for (a), 1 session for (b) |
| **Blocked by** | Decision: is the pre-open exclusion semantics actually wanted, or is it a bug-shaped assumption that no one actually depends on? If wanted → (a). If not → (b). |
| **Owner check-in** | 2026-04-22 |

---

### TD-009 — `.bak` file debris in `docs/registers/`

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-22 (V19A Block 11.4) |
| **Component** | `docs/registers/` directory |
| **Symptom** | Six intermediate `.bak` files left over from the 2026-04-19/20 register unification work: `MERDIAN_Enhancement_Register_v7.md.bak` (35 KB), `_v7.md.bak_v8_20260419_112002` (29 KB), `_v7.md.pre_enh5954.bak` (40 KB), `_v7.md.pre_enh6364.bak` (41 KB), `_v7.md.pre_enh64_close.bak` (45 KB), `_v7.md.pre_enh65.bak` (45 KB). Total ~235 KB. Also present: 5 `merdian_reference.json.bak_*` files totaling ~415 KB. No operational value post-unification. |
| **Root cause** | Safety-backup pattern during `fix_enh*.py` patch runs created these incidentally. Never cleaned up after the patches landed. `.gitignore` now prevents new `.bak` files being tracked (commit `bca369d`), but existing files on disk remain. |
| **Workaround** | Ignore. Not tracked in git anymore. Disk cost trivial. |
| **Proper fix** | Move to `docs/registers/archive/` for audit trail, or delete outright. Archive is the safer default — disk is cheap, audit trail is valuable. |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-22 |

---

### TD-015 — `run_preflight.py` 4-stage preflight system is undocumented; reinvented as one-off

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-24 (Session 7 close + Friday post-market work, morning preflight) |
| **Component** | `run_preflight.py`, runbook coverage, CLAUDE.md "Common operations" table |
| **Symptom** | A canonical 4-stage preflight (env / auth / db / runner_drystart) exists at `run_preflight.py` but is referenced by no runbook, not in CLAUDE.md's operations table, and not surfaced in `merdian_reference.json` operations index. On 2026-04-24 morning the chat re-invented it as `preflight_20260424.py` (now an untracked file in working tree, gitignored as `preflight_*.py` scratch). Future sessions will re-invent it again unless the canonical path is surfaced. |
| **Root cause** | Documentation gap. `run_preflight.py` predates the runbook layer (Rule 11, 2026-04-22); never retroactively given a runbook entry. Tribal knowledge that didn't survive the Session 6 -> 7 chat boundary. |
| **Workaround** | Operator memory. One-off `preflight_20260424.py` written for today, never run again; not committed. |
| **Proper fix** | (a) Create `docs/runbooks/runbook_run_preflight.md` from `RUNBOOK_TEMPLATE.md` documenting the four stages, expected exit codes, when to run each, and the standard "all-PASS = green to start day" criterion. (b) Add row to CLAUDE.md "Common operations" table. (c) Delete `preflight_20260424.py` from working tree. (d) Confirm `merdian_reference.json` has a `files.run_preflight.py` entry; add if missing. |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-24 |

---

### TD-021 -- Two undocumented operational conventions surfaced during Session 8

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-25 (Session 8) |
| **Component** | `.gitignore`, `merdian_pm.py`, `merdian_start.py` |
| **Symptom** | Two small things that bit operations during this session and will bite again unless documented. (a) `.gitignore` line 78 `/experiment_*.py` blocks default-add of new experiment scripts at repo root; convention is to force-add experiments worth keeping reproducible (precedent: `experiment_15.py`, `experiment_15b.py`, `experiment_17_bull_zone_break_cascade.py`). The convention is undocumented anywhere. Cost when missed: one extra commit and a confused user. (b) Adding a new managed process requires two parallel edits -- `merdian_pm.py` PROCESSES dict AND `merdian_start.py` hardcoded list at line 150. ENH-73 deployment hit this exactly: pm_stop killed the process correctly (saw it in PROCESSES) but pm_start didn't launch it (start.py's loop didn't include it). |
| **Root cause** | Both are missing-documentation issues, not bugs. (a) gitignore convention only became apparent when a new experiment was force-added; no comment in `.gitignore` flags it. (b) Schema duplication between `merdian_pm.PROCESSES` and `merdian_start.py`'s hardcoded loop. Originally fine when there were 3 processes; now there are 5 and the redundancy has cost. |
| **Workaround** | Operator memory + this register entry. |
| **Proper fix** | (a) Add a one-line comment above `.gitignore:78` reading something like `# experiment_*.py is default-ignored to keep scratch out of git. Force-add (git add -f) for experiments worth retaining. Precedent: experiment_15.py, experiment_15b.py, experiment_17_bull_zone_break_cascade.py.` (b) Refactor `merdian_start.py` line 150 to iterate over `pm.PROCESSES.keys()` directly, eliminating the second list. ~5 line change. After this, adding a process anywhere requires only one edit. |
| **Cost to fix** | <1 session -- bundle into a future OPS commit. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-25 |

---

### TD-025 — `build_spot_bars_mtf.py` re-aggregates full history every run (compute waste)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — observed during TD-019 patch design) |
| **Component** | `build_spot_bars_mtf.py` |
| **Symptom** | Each invocation reloads ALL 1m bars (~210k rows across NIFTY+SENSEX = ~282 trading days × 75 bars × 2 instruments) and re-aggregates the entire history into 5m + 15m, even when only the last day's worth of new data needs producing. At 116s/run × 252 trading days/year × 2 outputs = ~16 hours/year of wasted compute. Idempotent upserts on the unique index mean it's not incorrect, just wasteful. |
| **Root cause** | Original design as a manual on-demand full-history rebuild tool (TD-019 closure context). Was never re-architected after being scheduled as a daily task. |
| **Workaround** | None needed — daily 116s runtime is comfortably within Task Scheduler's 30-min `ExecutionTimeLimit`. |
| **Proper fix** | Parameterise on a date window. Default to "since `MAX(bar_ts)` in `hist_spot_bars_5m`" or "today's `trade_date` only". Full rebuild remains available via `--full` flag for backfills (so the TD-019 backfill recipe is preserved). Reduces typical run from ~116s to <10s. |
| **Cost to fix** | <1 session. |
| **Blocked by** | nothing. Defer until other priorities clear. |
| **Owner check-in** | 2026-04-26 |

---

### TD-027 — `merdian_pipeline_alert_daemon` scope drifted from name

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — Item 4 of TD-022 follow-up parking lot) |
| **Component** | `merdian_pipeline_alert_daemon.py`, ENH-73 + ENH-46-A |
| **Symptom** | The daemon's name and ENH-73 description suggest broad "pipeline alerting." Initial implementation alerted only on infrastructure failures from `script_execution_log`. ENH-46-A extended it to also alert on tradable signals (signal_snapshots). The file now does two distinct jobs but is named for one. |
| **Root cause** | ENH-73 was scoped narrowly during Session 8 deployment (infrastructure visibility); name and description used the broader "pipeline" term that implied wider scope. Documentation drift between intent and implementation, not a bug. ENH-46-A absorbed the gap rather than splitting into a new daemon. |
| **Workaround** | None needed; the daemon does what it does correctly post-ENH-46-A. This TD is about clarity going forward. |
| **Proper fix** | Two paths, mutually exclusive: (a) **Rename narrowly**: rename to `merdian_infra_alert_daemon.py`, keep ENH-73 narrow, treat ENH-46-A as a separate daemon `merdian_signal_alert_daemon.py`. Cleaner separation of concerns, requires file rename + Task Scheduler / pm.PROCESSES + state.json migration. (b) **Embrace the broad name**: keep the file name; document the multi-mode behaviour in the daemon docstring and ENH-73 description; accept a kitchen-sink. Recommendation: (b) for now, revisit if scope balloons further (e.g. third alerting domain added later). |
| **Cost to fix** | <1 session. Not urgent. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-028 — `merdian_pm.py` silently fails on unknown process name

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-26 (Session 9 — ENH-46-A daemon restart) |
| **Component** | `merdian_pm.py`, `start()` and `status()` functions |
| **Symptom** | Calling `python merdian_pm.py stop merdian_pipeline_alert_daemon` (full script filename instead of registry key `pipeline_alert`) returned no output and took no action. Calling `python merdian_pm.py status` also returned no output (whether the registry was empty or the function silently no-op'd is unclear). Net effect: operator believed the daemon had been stopped/restarted when in fact it had not, leading to ~10 minutes of confusion (PID 24968 still running with old code while operator thought new code was loaded). The pm tool's `start()` returns `False, f"Unknown: {name}"` on miss — but only the print path was checked; the actual return path was not surfaced, so the user saw nothing. |
| **Root cause** | Two issues entangled: (1) `start()` and `stop()` print the result tuple via wrappers in some code paths but not others — when called via `python merdian_pm.py <cmd> <name>` from CLI, the bool/msg tuple is returned but not echoed. (2) `status` likely outputs only when there are processes to report, suppressing the "no processes registered" case entirely. Either should fail loudly. |
| **Workaround** | Use the actual registry keys (`pipeline_alert`, `health_monitor`, `signal_dashboard`, `supervisor`, `exit_monitor`) not the script filenames. For start/restart, fall back to direct `Start-Process` PowerShell launch (used in Session 9 to relaunch the alert daemon after `merdian_pm.py start pipeline_alert` produced no output). |
| **Proper fix** | Three changes: (a) print the `(ok, msg)` tuple unconditionally at the top of every CLI handler. (b) emit `[OK] No matching processes` (or similar) from `status` when registry is empty. (c) consider raising on unknown process name (rather than `return False, "Unknown: ..."`) so silent-fail can't happen. <1 session. Bundle with TD-021 fix on the `merdian_start.py` dual-list issue (same file family, related cleanup). |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-037 — Schema column-name inconsistency across timestamp-bearing tables

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-27 (Session 10 extension, surfaced by repeated SQL errors during Exp 33 development) |
| **Component** | Database schema across multiple tables |
| **Symptom** | Three different timestamp column conventions across canonical tables: `signal_snapshots` uses `ts`, `hist_spot_bars_1m` uses `bar_ts`, `ict_zones` uses both `detected_at_ts` and `session_bar_ts`, `option_chain_snapshots` uses `ts`, `market_spot_snapshots` uses `ts`, `hist_atm_option_bars_5m` uses `bar_ts`, `script_execution_log` uses `started_at` and `finished_at`. Ad-hoc queries error out frequently with "column ts does not exist" or similar; consumes time iterating through column-discovery queries. |
| **Impact** | Friction on ad-hoc queries during live diagnostics. Real cost: during Session 10 extension, 4 query iterations were needed before getting to working SQL for `hist_spot_bars_1m` — adds up to ~10 minutes of iteration time when troubleshooting under market hours. Also makes Claude/AI sessions less efficient because column names can't be predicted from one table to another. |
| **Workaround** | Always run column-discovery query first when querying a new table: `SELECT column_name FROM information_schema.columns WHERE table_name='X'`. Document common patterns in a Session 11+ schema reference card. |
| **Proper fix** | Aspirational schema-hygiene refactor — standardise on `bar_ts` for time-series bar data, `ts` for snapshot/event data, `created_at`/`updated_at` as sidecars. Would require migrations and code refactors across all readers. Not worth scheduling unless an unrelated migration is happening. |
| **Cost to fix** | ~3-5 sessions for schema migration + reader updates. Cost-benefit not favourable for now. |
| **Blocked by** | nothing — but not a priority |
| **Owner check-in** | 2026-04-27 |

---

### TD-053 — CLAUDE.md Rule 16 needs era-aware addendum (post-04-07 era)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced via ADR-003 Phase 1 v2 + Exp 44 + `diagnostic_bar_coverage_audit_v2.py`; consolidates "TD-NEW-RULE16-ERA-AWARE") |
| **Component** | `CLAUDE.md` Rule 16 (TZ handling guidance for `bar_ts`); affects every repo script that applies the rule |
| **Symptom** | Rule 16 says: apply `replace(tzinfo=None)` to bar_ts and filter to in-session 09:15-15:30. This is correct for pre-04-07 era (bars stored as IST-labelled-as-UTC, the "TD-029 era"). Post-04-07 era stores bars as true UTC. Applying Rule 16 verbatim post-04-07 produces a UTC clock-time and filtering to 09:15-15:30 IST drops most of the day (~9 bars vs ~76 bars per session). Hits any script analysing post-04-07 data with verbatim Rule 16. |
| **Root cause** | Rule 16 was written when only the pre-04-07 era existed. Post-04-07 era introduced 2026-04-07 was not retroactively documented in Rule 16. **Related:** TD-029 (the underlying TZ-stamping bug that created the era boundary). |
| **Workaround** | Era-aware: pre-04-07 use `replace(tzinfo=None)`; post-04-07 use `astimezone(IST_TZ)`. Verified in `diagnostic_bar_coverage_audit_v3.py` which avoids the issue entirely by filtering on `trade_date` column instead of bar_ts time. |
| **Proper fix** | Edit `CLAUDE.md` Rule 16 to add era boundary at 2026-04-07 with code snippet for both eras. Audit all repo scripts that apply Rule 16 verbatim and patch them. Affected scripts identified in Session 15: ADR-003 Phase 1 (v1, v2 INVALID), `experiment_44_inverted_hammer_cascade.py` (verdict survives caveat re-evaluation but v2 re-run cleaner). |
| **Cost to fix** | <1 session for CLAUDE.md edit; ~1 session for repo audit + patches. |
| **Blocked by** | nothing — operator can edit CLAUDE.md anytime; audit can run any session |
| **Owner check-in** | 2026-05-02 |

---
