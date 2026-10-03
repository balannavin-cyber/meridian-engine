# Post-parity candidates

> **New file, S89 (2026-10-03).** Created because no such register existed and one was
> needed: the operator parked a piece of work that is **outside the parity fourteen** and
> asked for it noted rather than built.
>
> **What belongs here.** Anything that files to the parity spec **§2.5 as an extension**
> under **ADR-025 D5** — *"a layer outside the fourteen does not count toward parity"* — plus
> refinements to a **shipped** layer that go beyond its current scope. Parity dispositions
> themselves live in **ADR-025**, not here; this file never changes one.
>
> **A row here is a candidate, not a commitment.** Nothing in this file is proposed,
> scheduled, or authorised. A candidate that is to be built gets an ENH entry first.

---

| # | Candidate | Origin | Status |
|---|---|---|---|
| PPC-1 | **L13 refinement: prev-close-anchored ΔOI** | S89, 2026-10-03 | **CANDIDATE — parked by the operator, do NOT build** |

---

## PPC-1 — L13 refinement: prev-close-anchored ΔOI

**What it would be.** A ΔOI baseline anchored at the **previous session's close** rather than
at the current session's open, so OI change can be classified against price change across the
overnight boundary (long buildup / short buildup / short covering / long unwinding).

**Why it came up.** Ruling **D-4** (2026-10-03) folds the today's-flow-vs-standing-book ΔOI
classification into **ENH-98 / L7/L8** scope as a parity prerequisite, and D-4's baseline is
*previous close*.

**Why it is a separate candidate rather than part of L7/L8.** The shipped L13 view
`v_oi_rotation_since_open` anchors at the **first snapshot at or after 09:15 IST on the
session date**, in the **front expiry only** — *since open*, by construction and by name. A
previous-close baseline is **beyond what L13 currently does**, so building it is a change to
L13's scope, not a detail of L7/L8's.

**Operator disposition, 2026-10-03.** *"Park the prev-close OI / L13 work. It's outside the
L7/L8 brief and beyond even current L13."* Noted as a candidate; **not built**.

**One measured fact, recorded so it is not re-measured.** `v_oi_prev_close_snapshots` exists
as a view and **executes in 25 117 ms** on a full sequential scan (`EXPLAIN (ANALYZE)` as
`merdian_ro`, 2026-10-03) — roughly **3×** the PostgREST 8 s ceiling. That reproduces, with a
number, the **S78** exclusion of this relation as *unmeasurable by that method*. Whoever picks
this up should treat that view as unusable as a read path and start from the question of
whether the anchor can be resolved by an index seek instead; **that question was not
investigated** this session, because the work was parked before it was asked.

**Cross-references.** ADR-025 D5 · ruling D-4 in `docs/research/s89_rulings/rulings_s89.md` ·
`sql/2026-09-22_s81_v_oi_rotation_since_open.sql` · `sql/2026-05-25_v_oi_prev_close_snapshots.sql`
· `docs/research/s89_rulings/ENH-98_L78_design_spec_S89.md` §11.
