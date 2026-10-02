# S89 — development starter

| Field | Value |
|---|---|
| Document | `docs/session_notes/S89_dev_starter.md` |
| Written | S88 doc-close, 2026-10-02 |
| Read order | **`CLAUDE.md` → `CURRENT.md` → this file.** A dated worklist, not a substitute for either. |
| Resume | **Claude Code runs in a plain SSM shell, not tmux.** `cd /home/ssm-user/meridian-cc && claude --continue` |
| §0 provenance | **No S88 starter exists in the tree** (checked: no `docs/session_notes/S88*`, no `*starter*` file), so §0 is the operator's supplied text, not carried verbatim from a predecessor. |

---

## 0. Standing rules

These hold for the whole session, regardless of what the worklist says.

- **Never name the parity target's product** anywhere — chat, docs, prompts, commits, file names.
  Say **"the parity target"**.
- **Never read or print `.env` or any credential.**
- **Production `~/meridian-engine` changes only via push + `git pull --ff-only` after 16:00 IST,
  from the operator's own terminal. Never write under `~/meridian-engine`.** Pull pre-checks:
  tracked-modified **0**; gap `.py` ∩ scheduled scripts **empty**; **three-way sha**.
- **DB read-only via `bin/roq.sh`**; in market hours **bounded probes only**.
- **At a permission prompt the operator gives ONE thing:** a bare option number, or one paste-able
  block.
- **Session close is when the operator says so:** never remind, never suggest pausing.
- **Read the docs before asking the operator to check anything.**
- **Stage by explicit path**; commits prefixed **`MERDIAN: [OPS]`**.

---

## 1. Dated — these do not move

| When | What | Gate / note |
|---|---|---|
| **Sat 2026-10-03**, out of market hours | **ADR-029 #13/#14.** Sandbox enable, plus its install and network-allowlist cost. The Bash deny-bypass gap with the **untested spellings enumerated first**. | Out of hours deliberately. Enumerate before testing, or the gap is measured against an unknown denominator. |
| **Before Tue 2026-10-06** *(optional)* | A **pre-registered threshold** for the fixed-strike OI tilt and/or `ratio_pct`, if either is to be **tested** rather than described. | **Unstamped means not a test.** S88's versions are exploratory and say so. |
| **Tue 2026-10-06** | **The NIFTY L9 stage-1 arm** — TD-S80-NEW-1's owed half. | Front expiry **measured** as 2026-10-06 (`scratch/s88_design/nifty_front_expiry.out:5,13,21`); `trading_calendar` has it open, non-special. **Pre-register that morning, before any read.** Instrument: `scratch/s88_l9/l9_rebuilt_source.sql`, scope CTE → NIFTY + that day's W1. Verdict order from `capture_s88.md` §1.3 **unchanged**, tie clause and P3 included. |
| **Before Wed 2026-10-07** | **TD-S86-NEW-9 — the owed operator ruling.** Does §2.6's ≥ 3×SE precondition gate the gamma reading or only the offset reading? | On A4's data the two give **different T1 verdicts**. Must be **ruled, pre-registered and dated before the arm runs**, or the arm is measured under two live readings at once. |
| **Wed 2026-10-07, 10:15:59 IST** | **A4 re-run**, SENSEX dte 1. | Gated on the ruling above. Prior expectation already on record: on the precondition gradient (6.41× → 3.79× → 1.18×) this arm is **more likely than not another NO-TEST**. |

**Carry-forward note.** The NIFTY L9 arm has been owed since **S82** and carried through S85, S86,
S87 and S88. Named here rather than carried silently for a fifth time.

---

## 2. Parity build queue — S88's stated priority, ahead of the ENH queue

- **(a) TD-S88-NEW-1 repair.** A Lovable **read-layer** prompt was **drafted in chat 2026-10-01**
  and is **not in the tree**. **Precondition before it ships:** a **single-run anon check in the
  Supabase SQL editor** — one execution carrying `current_user` beside its rows — against
  `trading_calendar` and `market_spot_snapshots` (the **16:00–16:10 IST `dhan_idx_i`** rows).
  `merdian_ro` cannot run it (`permission denied to set role "anon"`), so it belongs to the editor
  under postgres. **The fix is in the read layer, not the writer's schedule** — moving the 16:10
  cron earlier cannot work, because no settled close exists before 16:00.
- **(b) §H phased Lovable prompts for the board.** Design doc **§A–G APPROVED 2026-10-01 13:04 IST
  with four additions R1–R4**; **§B.1a bindings are measured** (`capture_s88.md` §2.2–§2.4). Two
  qualifications must travel with the bindings, or the board will state things that are not true:
  **`basis_pct` is a futures-calendar artefact across days** (the futures leg is the October monthly
  while the option front expiry is weekly — §5.4), and **`open_0915_spot` is the 09:16 bar's
  close**, not the 09:15 open (D.44.5), so `gap_open_pct` is computed off that close.
- **(c) Snapshot export into the board canvas.**

---

## 3. Build queue — ENH-133…138, all PROPOSED, none started

Dispositions owed before any work. Three constraints already in the register:

- **ENH-133 and ENH-134 are alternatives, not a sequence.** A history table makes as-of functions
  unnecessary for new data but not for the existing window; as-of functions need no migration but
  re-derive on every read.
- **ENH-135 revisits a deliberate S62 decision and is not a defect report.** L3's dte-0 refusal is
  sourced at `.claude/rules/sql-views.md:20`; the per-view behaviour was already documented at
  `MERDIAN_System_Map.md:1963-1976`. L10 already keeps `ce_iv`/`pe_iv`.
- **ENH-137 is shadow-only under ADR-029.** Nothing gears down to it. TC1 v1's shadow **failed
  6/10 against a 10/10 bar** — the standing reason not to route work to a new agent on expectation.

---

## 4. Rulings owed

- **The six ENH dispositions** (ENH-133…138).
- **The five candidate rule lines** — `docs/research/s88_rule_lines_PROPOSED.md`. **Proposed, not
  applied, and deliberately not in `.claude/rules/`.**
- **Is `open_0915_spot` taking the 09:16 close intended?** And should `gap_open_pct` be recomputed
  off `raw->>'ohlc_open'`?
- **L11 — decline or pending.** The design doc now says **PENDING**; the disposition is unresolved.
- **E-D1 … E-D8:** `gex_cr` unit · canonical max pain · theme · legacy pin · NET-LONG γ source ·
  signal row · ACCEL retirement · prototype corrections.
- **TD-S87-NEW-1** (parked at S3 — MERDIAN has never placed an order).
- **The CLI unpin.** `2.1.277` was pinned for the ADR-028 comparison and both arms are graded, so
  the reason has expired; unpinning re-exposes the `stable`-channel side effect.
- **The five documents carrying the copied "150k" figure** (ADR-028 §6 item 3).

---

## 5. Owed probes and measurements

- **`scratch/s88_design/markers_check`** — the anon-path read in **one execution** carrying
  `current_user`, plus **`created_at` sampling** on marker rows across several sessions.
  `created_at` is the writer's own clock and the only in-database evidence of when a row landed; it
  would convert TD-S88-NEW-1 from a derivation into an observation.
- **`v_iv_surface` `ce_iv` / `pe_iv` on an expiry cohort.** S88 took only `leg_skew_98`, which is
  withheld at dte 0, and recorded "L10 is empty" — too strong (§5.7, D.44.10). The raw per-side IV
  was available on all 90 cells and was never fetched.
- **TD-S86-NEW-7's sibling.** `_meta.change_log` is stale at **S66** against the canonical
  top-level log at **S88** — the same two-copies shape the entry records for the version fields,
  which names only the version field. Found at the S88 close, **not** filed as a new TD.

---

## 6. What S88 established, so it is not re-derived

1. **L9 stage-1 SENSEX arm PASS ×3**; TD-S80-NEW-1 **not closed**, NIFTY arm owed.
2. **Negative result:** on the built layers, 2026-10-01 was **not** distinguishable from the other
   five SENSEX expiry days before 12:15. **Do not re-run that grid expecting a different answer**
   without new data or a pre-registered hypothesis.
3. **11 of 12 parity views carry no history.** Any historical layer question needs ENH-133 or
   ENH-134 first.
4. **L3 refuses on dte 0 wholesale, L10 partially, L9 not at all** — all three **already
   documented** at `MERDIAN_System_Map.md:1963-1976`.
5. **The as-of parameterisation works and is gated** — pattern and gate in R1 of the rule-lines doc.

---

*Written at the S88 doc-close, 2026-10-02. **Nothing in this file authorises a build.** §2 and §3
are operator-gated; §1's dates are set by the market calendar and the ADR-029 deferrals. §0 holds
regardless of anything below it.*
