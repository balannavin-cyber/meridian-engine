# MERDIAN capture — Session 89 (2026-10-03, Saturday, out of hours)

> Session capture. Written before any register edit, so every later update splices from one
> verified source. **ADR-029 #13 and #14 are NOT restated here** — they live in
> `docs/research/s89_rulings/rulings_s89.md` (88 lines, sha256
> `4eb593a1be5c5a7a5fccc3d011d61a9324f4d65fe4b44ecd67bdc412b45e4ac3`), and this file points at
> that rather than duplicating them.
>
> **Provenance marking.** Sections marked **OPERATOR-MEASURED** were read in the Supabase SQL
> editor, which `merdian_ro` cannot substitute for. Everything else carries the `scratch/` path
> it was measured in.

---

## §1 pg_cron jobid 19 — retention

**OPERATOR-MEASURED (SQL editor).** **CONFIRMED DISABLED**: `active = false`; last run
2026-09-08 12:30 UTC, succeeded.

**The live job NAME is `cleanup_gamma_engine_daily`. The docs say `..._data`.**

**The correction surface is wider than the three places named.** Measured this session —
**10 live files** carry `cleanup_gamma_engine_data` (backups under `*_PRE_*` excluded, since
those are frozen by design):

| File | Note |
|---|---|
| `docs/registers/MERDIAN_Deployment_Topology.md` | two occurrences, incl. the §S75.1 deleter passage |
| `docs/registers/MERDIAN_System_Map.md` | the jobid-19 entry |
| `docs/registers/tech_debt.md` | a TD **Component** row |
| `docs/registers/CURRENT_history.md` | archived S-block — **frozen by convention; do NOT edit** |
| `docs/registers/session_log_history.md` | archived entry — **frozen by convention; do NOT edit** |
| `docs/research/README.md` | prose |
| `docs/research/data_inventory_2026-09-08.md` | function inventory list |
| `docs/research/build_readiness_2026-09-09.md` | the §4 passage named in the ruling |
| `docs/research/gamma_metrics_tail_probe.py` | three occurrences, in a docstring |
| `docs/session_notes/capture_s75.md` | three occurrences — **a dated capture; frozen** |

**Two of the three named targets could not be resolved in the tree, and that is stated rather
than guessed:**

- **"plan §3.4"** — no plan-named document exists under `docs/`. Likely the parity design doc
  (`claude/parity_board_design.md`, project knowledge, not in the repo). **Operator to confirm
  which file.**
- **"S89 starter §1"** — `docs/session_notes/S89_dev_starter.md` mentions the job name
  **0 times**, so there is nothing there to correct. Either a different starter is meant, or the
  intent is to *add* the correct name. **Operator to confirm.**

**A correction policy question this exposes, owed before any edit.** Five of the ten files are
**archives or dated captures** — `CURRENT_history.md`, `session_log_history.md`,
`capture_s75.md`, and arguably the two dated research files. The standing convention is that
archives are moved verbatim and dated captures are frozen. **Correcting a name inside a frozen
archive rewrites history; leaving it means the wrong name persists in the retrieval surface.**
Neither is obviously right and it is not a doc-close edit to decide.

## §2 Retention decision, and the export as a shield

**Operator ruled: (1) keep disabled.** The replay weeks were exported read-only as **the shield
against re-enable** — if the job is ever re-enabled, the exported window survives it.

| Field | Value |
|---|---|
| Scope | 8 trading days **2026-09-22 … 2026-10-01**, NIFTY + SENSEX |
| Tables | `option_chain_snapshots`, `gamma_metrics` |
| Files | **32** (one per symbol-day per table) |
| Rows | **1,106,285** — every line re-parsed as JSON on readback, **0 unparseable** |
| Bytes | **871,306,422** (~871 MB) |
| Manifest | `scratch/s89_export/manifest.tsv`, sha256 `5f25f7f69d89da98491ca9a9e6e867f4542504efc2a86fed04f1bf0384566ebb` |
| Location | `scratch/s89_export/` — **untracked, not committed** |
| Path | `bin/roq.sh` only, read-only throughout; no write path to the DB |

**TRIPWIRE, ruled:** assert **`jobid 19 active = false`** at each SQL-editor doc-close.
`merdian_ro` cannot read `cron.job`, so this assertion belongs to the editor under postgres and
**cannot be delegated to `roq.sh`**.

**Two method notes on the export, recorded because they bear on reuse:**

1. **`ts` handling verified, and TD-029 does NOT apply.** `option_chain_snapshots.ts` is a true
   `timestamptz`: raw `03:10:06+00 → 10:10:05+00` renders as **08:40:06 → 15:40:05 IST**, real
   session hours. Had it been IST mislabelled as UTC, conversion would have pushed the session
   to ~14:45–21:10. So `AT TIME ZONE 'Asia/Kolkata'` is correct here and
   `replace(tzinfo=None)` would be wrong.
2. **Rule 15's `page_size = 1000` binds the PostgREST path, not this one.** `bin/roq.sh` is
   `psql`, which streams and has no 1000-row cap; the real constraint is the **30 s
   `statement_timeout`**. A full 85k-row day runs in **10.5 s**, so no pagination was needed.
   Paginating to 1000-row pages would have meant 85 round trips per day for no correctness gain.

## §3 Density reconciliation — two operator claims retracted, and my measurement stands

**Operator retraction.** Native per-symbol density is **74–87 distinct `ts`/day at a true
5-minute cadence**. The **"172" target** and the **"thinned = 2, not 1"** claim were **both
artifacts of an unfiltered, both-symbols count**: 172 ≈ **86 + 86 pooled**, and the thinned
threshold of 2 is **1 per symbol**. The documented **"one 15:30 row per day" STANDS.**

**What this resolves.** S89's export flagged that *no* day reached 172 and that every day sat at
74–87, and could not say whether that meant the target was wrong or every day was thinned. It
was the target — pooled against a per-symbol measurement. **The per-symbol figures were correct
and no day in the window is thinned.** Cadence was measured, not inferred: modal gap between
consecutive distinct `ts` is **4.99–5.01 min on all nine days**, and an 08:35–15:40 window at
5 min is 85 runs.

**On "one 15:30 row per day" — consistent with what was measured, but not independently
re-verified here.** At a 5-minute cadence exactly one run lands in each slot per symbol, so a
single 15:30 row per symbol-day follows. Note the *last* row of each day is **15:40**, not 15:30
(`gamma_metrics` 15:20:07 on 2026-10-01), so the claim is about the 15:30 slot being unique, not
about it being terminal. Stated this way because the two readings are easy to conflate.

## §4 2026-10-02 — excluded, frozen-market run → **TD-S89-NEW-1**

**Excluded from the export.** The day looks complete and is not: ~143k `option_chain_snapshots`
rows across **83 distinct `ts`** spanning 08:50–15:40, which passes every density check.

**What gives it away:** `distinct_spot_values = 1` for **both** symbols — NIFTY pinned at
**22421.95**, SENSEX at **71909.7**, `spot_range 0.00`. Control, 2026-10-01: **78** distinct spot
values, ranges 402.10 / 1212.60. **Row count alone could not tell these apart**, and a replay
built on it would have been built on a frozen book.

Those frozen values are exactly 2026-10-01's **16:00:04** post-close prints — i.e. the ingest ran
83 times on 10-02 and re-recorded the previous session's last-known spot each time.

**Two corroborating facts:** `gamma_metrics` has **no rows at all** for 10-02 — so the gamma gate
held while the ingest gate did not — and **10-02 is absent from `trading_calendar`**, which is
the Rule 18 / ADR-020 fail-open shape: a missing calendar row lets part of the chain run on a
closed day.

**TD-S89-NEW-1 — assigned, not yet filed.** To be written at the S89 close from this section.

## §5 Doc-close obligations — what splices where

Every edit below splices from this file. **No register has been touched this session.**

| Destination | Splice source | Notes |
|---|---|---|
| `tech_debt.md` | §4 | **TD-S89-NEW-1** — the 10-02 frozen-market run and the ingest-gate fail-open. Cite by entry ID + row name, never by line |
| `docs/research/s89_rulings/rulings_s89.md` | — | **Already written.** ADR-029 #13/#14 live there as the single source; do **not** restate them elsewhere |
| `MERDIAN_System_Map.md` · `MERDIAN_Deployment_Topology.md` · `tech_debt.md` | §1 | The job-name correction `..._data` → `..._daily`, **in live files only** |
| `CURRENT_history.md` · `session_log_history.md` · `capture_s75.md` | §1 | **BLOCKED on the policy question in §1** — these are archives/frozen captures |
| `merdian_reference.json` | §1, §2 | Job name; and the retention tripwire as a standing assertion |
| `CURRENT.md` · `session_log.md` | §1–§4 | S89 block and the one-line entry, at the close |
| `S89_dev_starter.md` | §1 | Only if the operator confirms the job name belongs in it — it is absent today |

**Owed decisions, none of them mine:** which file "plan §3.4" is; whether "S89 starter §1" means
add-or-correct; and the frozen-archive correction policy. **Owed work:** the §7(e)
multi-spelling sweep (operator-authored list), the sandbox enable via operator-typed `/sandbox`
plus `apt-get install bubblewrap socat`, and post-sandbox verification — all three carried in
`rulings_s89.md`.

---

*Capture — Session 89, 2026-10-03, out of hours. Read-only throughout: `bin/roq.sh` for the
database, `crontab -l` and greps for the host, and one operator-approved `/bin/cat` against a
non-secret canary. No production code, no DDL, no engine pull, no register edits. The export is
untracked and stays that way.*
