#!/usr/bin/env python3
"""patch_s80_docclose_enh_register.py

S80 doc-close, file 2 of 10 -- docs/registers/MERDIAN_Enhancement_Register.md

FIVE substitutions, each count==1:
  1. Scope bound ENH-01..ENH-122 -> ENH-01..ENH-124.
  2. Two Part-1 summary rows for ENH-123 / ENH-124, inserted before ENH-SDM.
  3. ENH-121's stale "3d EXPLAIN outstanding" clause gains a resolution note.
  4. ENH-122's stale "3f EXPLAIN outstanding" clause gains a resolution note.
  5. The file-tail TD-S79-NEW-14 bullet gains a correction, and a new
     "## Part 4 -- ENH-123 + ENH-124 detail blocks (Session 80)" section is
     appended in the established per-session-batch form.

WHY 3 AND 4 ARE CORRECTIONS, NOT REWRITES: TD-S79-NEW-14 is RESOLVED and sits
in tech_debt.md's audit trail, but this register still asserts in three places
that the EXPLAIN is outstanding. The as-filed text is KEPT and annotated, per
the register's convention that an entry should record what was believed before
it was measured. Filed as TD-S80-NEW-14 in the doc-close completion pass --
the TD-S76-NEW-12 shape: an edit landed without the register's own
self-description moving with it.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchors, line delta computed FROM the replacement text, growth assertion,
_PRE_S80_DOCCLOSE backup, dry-run default (--apply).
"""
import argparse, pathlib, sys

DEFAULT_TARGET = (pathlib.Path(__file__).resolve().parent.parent
                  / "docs" / "registers" / "MERDIAN_Enhancement_Register.md")
MARKER = "ENH-124"

# ── 1. scope bound ──────────────────────────────────────────────────────────

OLD_1 = "ENH-01 through ENH-122"
NEW_1 = "ENH-01 through ENH-124"

# ── 2. Part-1 summary rows ──────────────────────────────────────────────────

OLD_2 = "| ENH-SDM | Structural Divergence Monitor (ADR-018 D4) | context | **PROPOSED** |"

NEW_2 = r"""| ENH-123 | Max pain over `gex_strike_snapshots` - `v_gex_max_pain`, scoped per `(symbol, run_id, expiry_date)`, emitting `ts` / `dte` / OI coverage / freshness | 1 | **SHIPPED 2026-09-22 (S80)** - SQL `sql/2026-09-22_s80_v_gex_max_pain.sql`, commit `85dfad2`. **NOT a parity layer** - max pain appears nowhere in the fourteen layers or the build order of the Hedgewall parity spec; **ADR-025 D5** files it as **L19**, an extension under spec section 2.5: applied, unrendered, **not counted toward parity**. Equivalence gate PASSED - agreed with the S40 `v_max_pain_by_strike` on both symbols at first light (NIFTY **23,300** / SENSEX **74,400**) from a different base table, a different pivot and snapshots 20 minutes apart, so a real cross-check rather than a tautology. Freshness floor `maxpain.stale_floor_min` probed **CAN FIRE** under `BEGIN`/`ROLLBACK`: `stale_floor_min_used` tracked **30 -> 20 -> 99999** and `is_fresh` flipped **false -> true at an unchanged age**, so the parameter drives the comparison. That closes the **TD-S79-NEW-2** ambiguity for this view. The parameter is deliberately **left unseeded** - the COALESCE default of 30 differs from any value we would seed, keeping a successful read distinguishable from a NULL read. |
| ENH-124 | Pin <-> max-pain distance - `v_gex_pin_maxpain`, in points, strike steps and sigma, with band and corridor tests | 1 | **SHIPPED 2026-09-22 (S80)** - SQL `sql/2026-09-22_s80_v_gex_pin_maxpain.sql`, commit `85dfad2`. **NOT a parity layer** - **ADR-025 D5**, L19, parked. **Emits a DISTANCE, never a verdict**: no tolerance constant appears in the view and none may be added until the history supports one, per **TD-S79-NEW-21**'s measure-then-parameterise ruling. History over **11,795 runs** (`gex_pin_maxpain_history`, S80 backfill): the gap is a **stable -0.4 sigma** - medians -0.32 to -0.66 across **both symbols, every DTE and every session hour**, never changing sign. Max pain sits systematically **below** peak gamma; close to a constant of this market rather than a varying relationship. Exact strike coincidence is **1.2-5.4 %** everywhere **except NIFTY at 0 DTE, which runs 13.9 %** (164/1,182) - ~3x the next cell and ~13x a random landing; **SENSEX at 0 DTE is NOT elevated (3.4 %)**, so this is NIFTY expiry day, not expiry day generically. `max_pain_in_pin_band` is **non-selective** at 20.8-42.1 % regardless of DTE - **TD-S80-NEW-3**. Sigma is the unit: first light gave NIFTY **-4 strikes / -0.587 sigma** against SENSEX **-1 strike / -0.128 sigma** - near-equal in strikes, **4.6x apart in sigma**. `sigma_overstated_expiry_day` carries **TD-S79-NEW-1** in the row rather than in a footnote. |
| ENH-SDM | Structural Divergence Monitor (ADR-018 D4) | context | **PROPOSED** |"""

# ── 3 + 4. stale EXPLAIN clauses ────────────────────────────────────────────

OLD_3 = "**3d EXPLAIN outstanding - TD-S79-NEW-14.**"
NEW_3 = ("**3d EXPLAIN outstanding - TD-S79-NEW-14.** "
         "**CORRECTION S80: TD-S79-NEW-14 is RESOLVED** (S79, transcript-only evidence) "
         "- `Index Only Scan using ix_gex_strike_snap_sym_ts`, no base-table scan, "
         "execution 1.077 ms against planning 2.925 ms. The as-filed clause is kept "
         "because it records what was believed; see TD-S80-NEW-14.")

OLD_4 = "**3f EXPLAIN outstanding - TD-S79-NEW-14.**"
NEW_4 = ("**3f EXPLAIN outstanding - TD-S79-NEW-14.** "
         "**CORRECTION S80: TD-S79-NEW-14 is RESOLVED** (S79, transcript-only evidence) "
         "- `Index Only Scan using ix_gex_strike_snap_sym_ts`, no base-table scan, "
         "execution 1.943 ms against planning 3.197 ms. The as-filed clause is kept "
         "because it records what was believed; see TD-S80-NEW-14.")

# ── 5. tail correction + new Part 4 section ─────────────────────────────────

OLD_5 = """- Sections were run **separately**, as the files instruct — the Supabase SQL editor wraps a
  pasted script in one transaction, so the weakest statement gates the strongest (S72 Section 5
  took Sections 2 and 3 down with it)."""

NEW_5 = OLD_5 + r"""

> **CORRECTION, Session 80 (2026-09-22).** The TD-S79-NEW-14 bullet above is **stale**. That
> item was **RESOLVED in S79** by a single combined `EXPLAIN (ANALYZE, BUFFERS)` pass, operator-run
> in the Supabase SQL editor: `Index Only Scan using ix_gex_strike_snap_sym_ts` on all three views,
> **no base-table scan**, execution **2.507 / 1.077 / 1.943 ms** against planning **4.588 / 2.925 /
> 3.197 ms**, all shared-buffer hits, zero disk reads. **Planning exceeds execution on all three** —
> planning-bound, not scan-bound, the inverse of the ADR-021 A1.1 failure mode. The evidence is
> **transcript-only and uncommitted**: re-run it, do not go looking for a file.
>
> The bullet is annotated rather than rewritten, per this register's convention that an entry
> records what was believed before it was measured. The defect is that S79 closed the item in
> `tech_debt.md` and left **three** references to it stale one file over — two Part-1 summary rows
> and this bullet. Filed as **TD-S80-NEW-14**; it is the **TD-S76-NEW-12 shape**, an edit landing
> without the register's own self-description moving with it.

---

## Part 4 — ENH-123 + ENH-124 detail blocks (Session 80)

> **Neither is a parity layer.** Max pain appears nowhere in the fourteen layers or the ten-row
> build order of `MERDIAN_Hedgewall_Parity_Spec.md`. **ADR-025 D5** rules that a layer outside the
> fourteen does not count toward parity — otherwise the criterion is unfalsifiable, since a layer
> can always be added and progress reported. Both file as **L19** under spec section 2.5 alongside
> L15–L18, and are **parked**: applied to the live database, granted to `anon`, **unrendered**, and
> excluded from the parity count.
>
> They were built because a session brief called max pain *"the next layer"* and *"cheapest
> remaining board value."* The brief was off-spec, and that was not checked against the spec until
> four hours in. **TD-S80-NEW-2** records the spec's own stale claims; ADR-025 records the scope
> ruling that stops this recurring.

### ENH-123 — Max pain on the GEX base: `v_gex_max_pain` (SHIPPED 2026-09-22, S80)

**What it is.** Total writer pain at each candidate strike over `gex_strike_snapshots`, the argmin,
and a `PE_SIDE` / `CE_SIDE` / `MAX_PAIN` side label — scoped per `(symbol, run_id, expiry_date)`.

**Why a second max-pain view exists.** `v_max_pain_by_strike` shipped at **S40 (2026-05-29)** and
renders on the Marketview Max Pain page. It is **not replaced**; both are live. Four differences
motivated the new one, each measured:

1. **Base and history.** ENH-123 reads `gex_strike_snapshots` — 1.58M rows, no retention policy.
   The S40 view reads `option_chain_snapshots`, measured at **18 distinct days** (2026-08-24 →
   09-17), **not** the ~11 previously carried in the register (**TD-S80-NEW-11**). The brief's claim
   that max pain offered *"full history rather than the 62-day IV window"* fails on that source
   either way.
2. **Expiry scoping.** ENH-123 groups by `(symbol, run_id, expiry_date)`. The S40 view groups by
   `(symbol, strike)` with **no expiry filter**, so a snapshot carrying two expiries would collapse
   into a per-strike `max()` mixture. **Latent, not firing** — one expiry per cycle across all 2,923
   cycles — but it arms the moment ingest depth is raised (**TD-S80-NEW-10**).
3. **A clock.** ENH-123 emits `ts`, `run_id`, `expiry_date`, `dte`, OI coverage and `is_fresh`. The
   S40 view emits **no timestamp at all** and takes an unbounded `max(ts)`, so it serves a complete,
   plausible, **stale** strike if chain ingest stops, undetectably. Observed live: at 2026-09-19
   11:40 IST it was serving a strike from 2026-09-17 15:40 IST.
4. **A deterministic tie-break** on the argmin, where the S40 view's bare `row_number()` leaves ties
   to plan order.

**Equivalence gate — PASSED, and it is a real cross-check.** NIFTY **23,300** and SENSEX **74,400**
from both views at first light, from different base tables, different pivots, and snapshots 20
minutes apart. Two independent computations agreeing is evidence; the same computation agreeing with
itself would not be.

**Freshness floor, proven CAN FIRE.** `maxpain.stale_floor_min` via `get_parameter_num`, `COALESCE`
default 30. Probed inside `BEGIN`/`ROLLBACK`: `stale_floor_min_used` tracked **30 → 20 → 99999** and
`is_fresh` flipped **false → true at an unchanged snapshot age of 895.6 min**. So the parameter drives
the comparison — it is not decoration. That closes the **TD-S79-NEW-2** ambiguity for this view; the
parameter is deliberately **unseeded**, because a seeded value equal to the fallback makes a
successful read and a NULL read indistinguishable, which is TD-S79-NEW-2's whole content.

**Cross-ref.** `sql/2026-09-22_s80_v_gex_max_pain.sql` · ADR-025 D5 · ADR-015 (`oi_call` / `oi_put`)
· ADR-023 (the recency-floor obligation this satisfies and the S40 view does not) · TD-S80-NEW-10,
TD-S80-NEW-11 · commit `85dfad2`.

### ENH-124 — Pin ↔ max-pain distance: `v_gex_pin_maxpain` (SHIPPED 2026-09-22, S80)

**What it is.** ENH-123's max pain joined to ENH-81's pin zone and ENH-120's walls **on the same
run**, emitting the distance between max pain and peak gamma in **points, strike steps and sigma**,
plus `max_pain_in_pin_band`, `max_pain_in_corridor` and `corridor_state`.

**It emits a distance and not a verdict, deliberately.** The reading the brief asked for — *"when max
pain and the pin land on the same strike, that is the strongest picture the screen can show"* —
requires a tolerance. **TD-S79-NEW-21**'s ruling binds: measure first, then parameterise, because
parameterising an unmeasured constant relocates it rather than calibrating it. **No tolerance
constant appears in this view and none may be added until the history supports one.**

**What the history says** — `gex_pin_maxpain_history`, 11,795 runs, 2026-05-25 → 09-18, session hours:

- **The gap is a stable −0.4σ.** Medians −0.32 to −0.66 across **both symbols, every DTE and every
  session hour**; it never changes sign. Max pain sits systematically below peak gamma — closer to a
  constant of this market than to a varying relationship.
- **Exact coincidence is rare and concentrated.** 1.2–5.4 % everywhere **except NIFTY at 0 DTE,
  which runs 13.9 %** (164 / 1,182) — roughly 3× the next cell and ~13× a random landing over 96
  strikes. **SENSEX at 0 DTE is not elevated (3.4 %)**, so this is *NIFTY expiry day*, not expiry day
  generically. Grid granularity accounts for part of the symbol gap (NIFTY 50 on ~23,500 = 0.21 % per
  strike against SENSEX 100 on ~75,000 = 0.13 %) but cannot account for 13.9 % against NIFTY's own
  2.8–5.4 % at other DTEs, since the grid does not change with DTE.
- **`max_pain_in_pin_band` is not a weaker form of coincidence.** NIFTY 6-DTE carries the *highest*
  band rate in the sample (42.1 %) on a 2.9 % exact rate, while the one genuinely elevated cell has a
  *lower* band rate (41.9 %). The two do not rank the same cells. **TD-S80-NEW-3.**
- **No intraday drift.** Flat 09:00–15:00 on both symbols, which retired a worry that the one-run-
  per-day sampling used earlier was answering the wrong question. It was not; the sample size was.

**Sigma, not points.** First light: NIFTY −4 strikes / **−0.587σ**, SENSEX −1 strike / **−0.128σ** —
near-equal in strikes, **4.6× apart in σ**. Any rule that eventually reads this view reads
`gap_sigma`. `sigma_overstated_expiry_day` is a **column, not a footnote**, so TD-S79-NEW-1 travels
with the row instead of relying on a reader remembering the entry.

**Whether coincidence predicts anything is UNANSWERED and deliberately so.** That is a conjunction
question governed by parity-spec section 5 and **ADR-009**: pre-registration, target and success
criterion written before the first query. **ENH-97** is the standing warning — chi-sq 1.56, p ≈ 0.30
on 1,968 signals, and a salvage test that failed on power with a bootstrap CI spanning zero. n = 164
is enough to run it properly and not enough to justify running it casually.

**Substrate built for it.** `gex_pin_maxpain_history` (table) and `backfill_pin_maxpain_runs()`
(chunked populator, `p_limit` 20) exist because `v_gex_strike_pin_zone` is latest-run scoped by
**ADR-021** — its recursive τ walk crossed the PostgREST 8 s ceiling at 1.06M rows — so the pin band
and `peak_pin_strike` **cannot be read historically from the view at all**. The table materialises the
same computation per run. Gate: reproduced the live view on 2026-09-18 for both symbols, all four of
`peak_pin_strike` / `pin_lower` / `pin_upper` / `n_strikes` identical. Backfill completed
**11,795 / 11,795 runs, zero failures**. The table itself still owes a Rule 10 ADR —
**TD-S80-NEW-7**.

**Cross-ref.** `sql/2026-09-22_s80_v_gex_pin_maxpain.sql` · `sql/2026-09-22_s80_gex_pin_maxpain_history.sql`
· `sql/2026-09-22_s80_backfill_pin_maxpain_runs.sql` · `scripts/backfill_pin_maxpain.py` · ENH-81,
ENH-120, ENH-123 · ADR-021, ADR-025 D5, ADR-009 · TD-S79-NEW-1, TD-S79-NEW-21, TD-S80-NEW-3,
TD-S80-NEW-7, TD-S80-NEW-8 · commit `85dfad2`.

*Part 4 (Session 80) — 2026-09-22. Two enhancements shipped, both L19 extensions rather than parity
layers, both unrendered. **Enhancement Register TRIGGERED** for a second consecutive session after
nine non-triggers ending at S79.*"""

SUBS = [
    ("1. scope bound ENH-122 -> ENH-124", OLD_1, NEW_1),
    ("2. ENH-123 + ENH-124 summary rows", OLD_2, NEW_2),
    ("3. ENH-121 stale 3d EXPLAIN clause", OLD_3, NEW_3),
    ("4. ENH-122 stale 3f EXPLAIN clause", OLD_4, NEW_4),
    ("5. tail correction + Part 4 detail blocks", OLD_5, NEW_5),
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
    print(f"baseline: {text.count(chr(10))} newlines, {len(raw)} bytes")
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

    if len(patched) <= len(norm):
        print("ABORT: file did not grow.", file=sys.stderr)
        return 1
    print(f"byte delta (normalised): +{len(patched) - len(norm)}")

    # ENH-123 / ENH-124 must each appear as a summary row AND a detail heading
    for eid in ("ENH-123", "ENH-124"):
        rows = patched.count(f"| {eid} |")
        heads = patched.count(f"### {eid} —")
        print(f"{eid}: {rows} summary row, {heads} detail heading")
        if rows != 1 or heads != 1:
            print(f"ABORT: {eid} must have exactly 1 row and 1 detail heading.", file=sys.stderr)
            return 1

    if "ENH-01 through ENH-122" in patched:
        print("ABORT: old scope bound still present.", file=sys.stderr)
        return 1
    print("scope bound updated, old form gone")

    if patched.count("## Part 4 — ENH-123 + ENH-124 detail blocks (Session 80)") != 1:
        print("ABORT: Part 4 section not inserted exactly once.", file=sys.stderr)
        return 1
    print("Part 4 (Session 80) section present once")

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
