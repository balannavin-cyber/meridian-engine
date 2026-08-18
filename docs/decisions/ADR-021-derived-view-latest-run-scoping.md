# ADR-021 — Derived per-strike views are scoped to the latest run: a view that recomputes all history to serve one row is a latent timeout, not a performance nicety

| Field | Value |
|---|---|
| Status | **Accepted** |
| Date decided | 2026-08-13 |
| Date documented | 2026-08-13 (S69 interim capture) · formalised S70 from capture v2 |
| Session | Session 69 |
| Supersedes | The unscoped v1 definitions of `v_gex_strike_pin_zone` / `v_gex_strike_accel_zone` shipped under ENH-81 (2026-05-25, S37). ADR-015 (`gex_strike_snapshots` schema) is **unchanged** — this ADR touches the read path only. |
| Related ENH / TD / ADR / commits | ENH-81 (Positioning Landscape views) · ENH-80 (per-strike GEX writer) · ADR-015 (per-strike GEX schema v2) · ADR-018 D2 (recency floors) · TD-S37-01 (τ hardcode, still OPEN) · TD-S69-NEW-3 (`fetch_positioning_landscape` freshness floor) · migration `sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql`, committed **`4326f25`** |
| Rule 10 class | **Schema-affecting / core-table read-path change.** Mandatory ADR. |

---

## Context

`v_gex_strike_pin_zone` and `v_gex_strike_accel_zone` were built in S37 (ENH-81, 2026-05-25) over `gex_strike_snapshots`. Each view computes, in a chain of CTEs: `strike_step` inference, `peak` / `trough` detection, and a **recursive `walk`** outward from the extremum until the τ-fraction threshold is crossed — and it does all of that **for every snapshot row in the table**.

There is exactly one consumer: `generate_pine_overlay.py::fetch_positioning_landscape()`, which reads the view and immediately applies `ORDER BY ts DESC LIMIT 1`. Every pin/accel zone the view computed for every historical snapshot is discarded on arrival.

At build time the table held ~45K rows and the cost was invisible. By 2026-08-12 `gex_strike_snapshots` held **1.06M rows across 250+ sessions**, the recursive walk crossed the PostgREST 8-second statement ceiling, and the view began returning `57014` (statement timeout). `fetch_positioning_landscape()` failed; the Pine generator emitted an overlay with no PIN and no ACCEL boxes; and nothing anywhere alerted, because the writer was healthy, the table was fresh, and `eod_health_check.py` does not look at these views (TD-S69-NEW-2).

The operator's report was *"no pin/accel zones on TradingView for days."* The failure had been progressive for weeks — there was no single day it broke, only the day it finally crossed 8s on every call.

## Decision

**A derived view whose only consumer reads the newest row must be scoped to the newest run inside the view itself. Scoping is part of the view's contract, not an optimisation applied later by the caller.**

Concretely, both views gain two leading CTEs:

```sql
latest_run AS (
  SELECT DISTINCT ON (symbol) symbol, ts, run_id
  FROM gex_strike_snapshots
  ORDER BY symbol, ts DESC
),
scoped AS (
  SELECT g.*
  FROM gex_strike_snapshots g
  JOIN latest_run l USING (symbol)
  WHERE g.ts = l.ts
)
```

and every downstream CTE (`strike_step`, `peak`, `trough`, the recursive `walk`) reads `scoped` instead of the base table. The per-call working set drops from 1.06M rows to **~80 strikes per symbol**.

A supporting index is part of the decision, not a separate tuning step:

```sql
CREATE INDEX IF NOT EXISTS ix_gex_strike_snap_sym_ts
  ON gex_strike_snapshots (symbol, ts DESC);
```

**Output for the latest snapshot is byte-identical.** What the views stop doing is computing pin/accel zones for historical snapshots that no consumer has ever read.

Applied to Supabase mid-session 2026-08-13 via `sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql`; the migration was committed to git at session close (**`4326f25`**), so the live database and the repo agree.

## Evidence

| Item | Before | After |
|---|---|---|
| Rows entering the recursive walk | 1,060,000+ (all history, 250+ sessions) | ~80 per symbol (current snapshot) |
| View response | `57014` statement timeout (>8s PostgREST ceiling) | returns immediately |
| NIFTY | no rows (timeout) | PIN 24,450–24,700 · ACCEL 24,200–24,350 |
| SENSEX | no rows (timeout) | PIN 78,100–78,700 · ACCEL 77,400–77,800 |
| Pine overlay | pin/accel boxes absent | pin/accel boxes present |

The diagnostic tell that separated this from every other candidate cause: **the writer was healthy and the table was fresh.** `gex_strike_snapshots` had current rows for both symbols; only the *derived* read path was failing. A `57014` from a view over a healthy table is a cost-growth signature, and cost growth in a view with a recursive CTE over an unscoped base table is arithmetic, not mystery.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| **Raise the PostgREST statement timeout** | **Rejected.** Buys months, not a fix. The table grows every 5-minute cycle; the same wall returns at a larger row count, and a raised ceiling also lengthens every *other* pathological query before it fails. Treating a growth curve with a constant is the ADR-001 stable-lie shape. |
| **Push the `LIMIT 1` down into the caller's query / materialise in Python** | **Rejected.** The caller already does `ORDER BY ts DESC LIMIT 1`; PostgREST cannot push that predicate through a recursive CTE, so the whole walk still executes server-side. It also leaves the trap armed for the next consumer of the view. |
| **Materialised view refreshed on the GEX writer's cadence** | **Rejected for now.** Adds a refresh dependency and a staleness surface (a `REFRESH` that silently stops is precisely the S67 frozen-table failure class) to solve a problem that a `DISTINCT ON` CTE solves with no new moving part. Revisit only if the scoped view itself becomes slow. |
| **Retention / pruning on `gex_strike_snapshots`** | **Rejected as the fix; retained as separate debt.** The historical series is a research asset (ADR-015 exists to keep it). Deleting data to make a read path fast is solving the wrong problem — though disk pressure makes retention a legitimate *independent* item (TD-S69-NEW-1). |
| **Compute pin/accel in Python in the generator, drop the views** | **Rejected.** The views are the shared contract; Marketview and the Pine generator both descend from them. Moving the logic into one consumer forks the definition. |

## Consequences

**Positive**
- Both views return in well under the PostgREST ceiling and are no longer growth-coupled to table size.
- The failure mode is closed at the layer that caused it, so any future consumer inherits the fix.
- The `(symbol, ts DESC)` index also serves every other latest-snapshot read of `gex_strike_snapshots`.

**Negative**
- Pin/accel zones are no longer computable *through these views* for historical snapshots. Any future historical pin/accel study must parameterise the scope (a function taking `ts`, or a separate `_hist` view) rather than selecting a past `ts` out of the live view.
- The views now encode an assumption — "newest per symbol" — that is invisible to a reader of the output. Recorded in the System Map view definitions so it is not rediscovered by surprise.

**Mitigations**
- System Map §S69 carries the scoped definition and the historical-scope caveat.
- The `latest_run` CTE keys on `(symbol, ts)`, not a global max, so an asymmetric writer (NIFTY written, SENSEX lagging) still serves each symbol its own newest snapshot rather than blanking the lagging one.

## Relationship to other documents

- **ADR-015** — schema unchanged; this is a read-path decision over that schema.
- **ADR-018 D2** — the recency-floor doctrine. The scoping fix makes the views fast but does **not** make them fresh; a stalled GEX writer would now serve a stale snapshot *quickly*. The matching D2 floor on `fetch_positioning_landscape()` is filed as **TD-S69-NEW-3** and is the necessary companion to this ADR.
- **TD-S37-01** — τ_pin / τ_accel are still **hardcoded `0.3`** inside the walk. ENH-83's `get_parameter_num('pin.tau.'||symbol)` value is *selected into the output* but not *used by the walk*; the closure patch `patch_s39_enh83_view_tau_rewrite.py` has never run. This migration deliberately did **not** fold that in — one change per migration — and the debt survives the rewrite unchanged.
- **ADR-001** — the stable-lie principle. A view that returns a timeout is loud; a view that returns stale-but-plausible zones is the failure this ADR must not create. Hence the TD-S69-NEW-3 pairing.

## Governance language

> **A derived view is scoped to the run its consumer actually reads (ADR-021, S69).** `v_gex_strike_pin_zone` / `v_gex_strike_accel_zone` resolve `latest_run` (`DISTINCT ON (symbol) … ORDER BY symbol, ts DESC`) first and every downstream CTE reads that scope — not the base table. A recursive walk over 1.06M rows to return one row is a latent `57014`, and it fires as a *silent* feature loss, not an error. Raising the statement timeout is rejected: it treats a growth curve with a constant. Scoping is the view's contract; freshness is a separate guard (ADR-018 D2).

## Open follow-ups

1. **TD-S69-NEW-3** — add the ADR-018 D2 recency floor to `fetch_positioning_landscape()` (`ts >= today`), matching the floor S69 added to `fetch_intraday_zones`. Until then the generator will emit stale pin/accel silently if the GEX writer stalls. Lands in the same pass that resolves the canonical Pine host (TD-S69-NEW-4).
2. **TD-S37-01** — run the τ-parameterisation closure so the walk uses `get_parameter_num`, not literal `0.3`. Now cheap to do: the scoped views are small enough to test end-to-end in seconds.
3. **TD-S69-NEW-2** — extend `eod_health_check.py` to assert that `v_gex_strike_pin_zone` / `v_gex_strike_accel_zone` **return rows**. This defect ran for weeks under a green health check, and the assertion must be "rows came back", not "the table has data".
4. Audit the remaining views over `gex_strike_snapshots` for the same unscoped-recursion shape before they cross the same ceiling.

---

*ADR-021 — 2026-08-13 — Session 69 — the fix was four lines of SQL; the finding was that a healthy writer plus a fresh table plus a silent consumer is a shape that hides a total feature loss for weeks. Cost growth in a derived view is arithmetic — it should be a design-time check, not an incident.*
