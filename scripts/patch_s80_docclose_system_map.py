#!/usr/bin/env python3
"""patch_s80_docclose_system_map.py

S80 doc-close, file 7 of 10 -- docs/registers/MERDIAN_System_Map.md

ONE substitution, count==1: a new "## §S80" section is appended at the file
tail, anchored on the §S79 footer's closing clause.

SCOPE. This section covers the S80 DATABASE AND SCRIPT work only -- two views,
a table, a plpgsql function, two patched Python scripts. None of it moved a
cron line, a systemd unit, a token path or a Local<->AWS boundary.

That does NOT mean the session changed no topology. The 2026-09-22 disk-full
access lockout resized the root volume 8 GiB gp2 -> 30 GiB gp3, widened the
logrotate scope, discharged the S71 kernel risk and required the feed to be
started by hand. **Deployment Topology DOES carry a §S80** for exactly that.
An earlier draft of this section asserted the opposite, on the §S79 precedent,
and was corrected before it was applied -- the claim was true of the work in
front of it and false of the session.

NOT FIXED HERE, as in S74 and S76: the `## Update log` table remains frozen at
Session 67 (TD-S73-NEW-10). Recorded, not repaired -- repairing it is a
separate sourced edit across six sessions of entries.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchor, line delta computed FROM the replacement text, growth assertion,
_PRE_S80_DOCCLOSE backup, dry-run default (--apply).
"""
import argparse, pathlib, sys

DEFAULT_TARGET = (pathlib.Path(__file__).resolve().parent.parent
                  / "docs" / "registers" / "MERDIAN_System_Map.md")
MARKER = "## §S80"

OLD = ("**CODE CHANGED (SQL only); no Python production change; no irreversible "
       "database operation.**) Previous: Session 78, 2026-09-14 (§S78).*")

NEW = OLD + r"""

---

## §S80 — Session 80: two max-pain layers, a history table built because a view cannot be read backwards, and the criterion that files both as off-spec (2026-09-19/22)

**Two views, one table and one plpgsql function applied to the live database; two production Python scripts patched.** No cron line, no systemd unit, no token path and no Local↔AWS boundary moved by **this** work — the two patched scripts run exactly where they already ran.

**That is a statement about the build, not about the session.** Later the same morning the **2026-09-22 disk-full access lockout** resized the root volume **8 GiB gp2 → 30 GiB gp3**, widened the logrotate scope, discharged the kernel risk carried since S71, and left the feed needing a manual start. **Deployment Topology therefore carries a full §S80**, and this section is the database half only. An earlier draft of this paragraph asserted the Topology carried no §S80 — true of the work in front of it, false of the session — and was corrected before it was applied.

**Both new views are off-spec and parked.** Max pain appears nowhere in the fourteen Hedgewall parity layers or the ten-row build order. **ADR-025 D5** files them as **L19** under spec §2.5: applied, granted, **unrendered, and not counted toward parity**. They are recorded here because D2 clause 4 binds every production object regardless of parity status, not because they advance the programme.

### S80.A — two new views

Both are siblings of the ENH-81 / ENH-120-122 family and share the construction: latest-run scoping per **ADR-021**, `get_parameter_num` wiring per **ADR-016**, and the `(run_id, symbol, expiry_date)` grain.

| View | What it is | Source file | Notes |
|---|---|---|---|
| `v_gex_max_pain` | **ENH-123.** Total writer pain at each candidate strike over `gex_strike_snapshots`, the argmin, and a `PE_SIDE` / `CE_SIDE` / `MAX_PAIN` side label — scoped `(symbol, run_id, expiry_date)` and emitting `ts`, `dte`, OI coverage and `is_fresh`. | `sql/2026-09-22_s80_v_gex_max_pain.sql` | **A second max-pain view now exists and the S40 `v_max_pain_by_strike` is NOT replaced** — both are live. Four measured differences motivate it: (1) **base and history** — `gex_strike_snapshots` (1.58M rows, no retention policy) against `option_chain_snapshots`, whose S40-view coverage measures **18 distinct days**, not the ~11 previously carried (**TD-S80-NEW-11**); (2) **expiry scoping** — the S40 view groups by `(symbol, strike)` with **no expiry filter**, so a two-expiry snapshot would collapse into a per-strike `max()` mixture. **Latent, not firing** — one expiry per cycle across all 2,923 cycles — but it **arms the moment ingest depth rises** (**TD-S80-NEW-10**); (3) **a clock** — the S40 view emits **no timestamp at all** and takes an unbounded `max(ts)`, so it serves a complete, plausible, stale strike if chain ingest stops. Observed live: at 2026-09-19 11:40 IST it was serving a strike from **2026-09-17 15:40 IST**; (4) a **deterministic tie-break** where the S40 view's bare `row_number()` leaves ties to plan order. **Equivalence gate PASSED and it is a real cross-check, not a tautology** — NIFTY **23,300** / SENSEX **74,400** from both views, different base tables, different pivots, snapshots 20 minutes apart. **Freshness floor proven CAN FIRE** under `BEGIN`/`ROLLBACK`: `stale_floor_min_used` tracked **30 → 20 → 99999** and `is_fresh` flipped **false → true at an unchanged age of 895.6 min**, which closes the **TD-S79-NEW-2** ambiguity *for this view*. The parameter `maxpain.stale_floor_min` is deliberately **left unseeded** — a seeded value equal to the COALESCE fallback of 30 makes a successful read and a NULL read indistinguishable, which is that TD's whole content. |
| `v_gex_pin_maxpain` | **ENH-124.** ENH-123's max pain joined to ENH-81's pin zone and ENH-120's walls **on the same run**, emitting the distance in `gap_points`, `gap_strikes` and **`gap_sigma`**, plus `max_pain_in_pin_band`, `max_pain_in_corridor` and `sigma_overstated_expiry_day`. | `sql/2026-09-22_s80_v_gex_pin_maxpain.sql` | **It emits a distance and never a verdict, deliberately.** The reading a brief asked for — *"when max pain and the pin land on the same strike, that is the strongest picture the screen can show"* — requires a tolerance, and **TD-S79-NEW-21** binds: measure first, then parameterise, because parameterising an unmeasured constant relocates it rather than calibrating it. **No tolerance constant appears in this view and none may be added until the history supports one.** `sigma_overstated_expiry_day` is a **column, not a footnote**, so **TD-S79-NEW-1** travels with the row rather than relying on a reader remembering the entry. |

### S80.B — a new table and a new function, because a scoped view cannot be read backwards

| Object | What it is | Source file |
|---|---|---|
| `gex_pin_maxpain_history` | 16 columns, `UNIQUE (symbol, run_id, expiry_date)`, **11,795 rows** covering 2026-05-25 → 2026-09-18. | `sql/2026-09-22_s80_gex_pin_maxpain_history.sql` |
| `backfill_pin_maxpain_runs(text, timestamptz, timestamptz, integer DEFAULT 20)` | Chunked populator reproducing `v_gex_strike_pin_zone`'s recursive τ walk **exactly** — `gex_cr > 0`, `abs(strike - spot)` tie-break, τ from `get_parameter_num('pin.tau.'||symbol)` falling back to 0.3, and `peak_pin_strike` as the argmax **within the walk rows**, not within the band. | `sql/2026-09-22_s80_backfill_pin_maxpain_runs.sql` |

**Why the table exists at all.** `v_gex_strike_pin_zone` is **latest-run scoped by ADR-021** — its recursive walk crossed the PostgREST 8 s ceiling at 1.06M rows — so the pin band and `peak_pin_strike` **cannot be read historically from the view under any predicate**. This is the caveat §S69 warned would have to be paid eventually: *"historical pin/accel study is no longer possible by selecting a past `ts` out of the live view — it needs a parameterised function or a separate `_hist` view."* S80 paid it with the function plus the table.

**Gate:** reproduced the live view on 2026-09-18 for both symbols with all four of `peak_pin_strike` / `pin_lower` / `pin_upper` / `n_strikes` identical, then backfilled **11,795 / 11,795 runs, zero failures**.

**A superseded sibling was DROPPED, not kept as a spare.** `backfill_pin_maxpain(text, date)` computed before `ON CONFLICT` could discard and timed out. A second callable path into one table is a hazard, not redundancy — **ADR-025 *Consequences*** rules it dropped, and it was.

**Rule 10 is NOT discharged for the table.** Its DDL is committed, which satisfies ADR-025 D2 clause 4; a new table is schema-affecting and still owes its own ADR — **TD-S80-NEW-7**. Committing DDL and ratifying a schema are different obligations.

### S80.C — two production scripts patched

| Script | Change | Notes |
|---|---|---|
| `compute_gamma_metrics_local.py` | `infer_expiry_date()` now **raises** when option rows carry more than one expiry, instead of returning `min()` of a set it assumed was a singleton. Closes **TD-S79-NEW-12**. | The single-expiry invariant previously held only as a **property of the data**, never as a statement in the code. The guard converts silent corruption into a crash — which is why it shipped **before** the ingest change below, and not after. |
| `ingest_option_chain_local.py` | Module-level `EXPIRY_DEPTH = {"NIFTY": 1, "SENSEX": 1}` and `select_expiries()`, plus an **appended** extra-expiry pass before the completion print, guarded by `if _depth > 1:`. | **Stage 0 is inert by construction and was then observed inert.** W1's path is untouched; the stdout `Run ID:` contract and ENH-71's `record_write` stay bound to W1 alone. **Capture depth shipped as a constant, not as the `ingest.n_expiries.{symbol}` parameter ADR-025 ruled** — a parameter read that fails *open* would raise depth silently on a cycle whose consumers assume one expiry, which is exactly what the guard above now crashes on. Reason and the condition for moving it are in **ADR-025 Amendment A §A1**. |

**The spec claim this refutes.** `option_chain_snapshots` holds **one expiry per cycle across all 2,923 cycles ever written** (`min = avg = max = 1`, `cycles_multi_expiry = 0`). `ingest_option_chain_local.py:327` returns the full ladder the vendor sends and **`:365` discards it, uncommented**. The parity spec's *"full expiry ladder per cycle"* was never true — **no regression occurred; the capability never existed.**

**Depth measured on the vendor tier, not assumed.** Day-level `hist_option_bars_1m` holds **21** expiries; S78's per-minute 14 was a subsample. NIFTY: W1 67.8 % · current monthly 18.8 % · W2 5.2 % · **Dec quarterly 3.4 %** · **W3 0.47 %**. SENSEX: W1 **97.25 %** · W2 2.65 % · monthly 0.089 %. **The selection rule matters more than the count** — chronological `[0:4]` yields 92.28 % on NIFTY *and no curve*, four points inside three weeks, because slicing takes W3 and misses the December quarterly.

### S80.D — three new scripts committed

| Script | Purpose | Scheduled? |
|---|---|---|
| `scripts/backfill_pin_maxpain.py` | Drives `backfill_pin_maxpain_runs()` in 20-run chunks with retry. **Byte-identical to the run that produced the 11,795 rows** (`sha256 453f1be8…`). | **No.** One-shot. It **hardcodes the window 2026-05-25 → 2026-09-18**, so re-running it extends nothing — extending the history means editing the window. |
| `scripts/probe_s80_expiry_guards.py` | AST-loads both patched guards and asserts 14 properties of them without importing the modules. | **No.** Run after touching either guard. |
| `scripts/patch_s80_td_s79_new_12_infer_expiry.py`, `scripts/patch_s80_adr025_expiry_depth.py` | The two canon-v3 patch scripts, kept on disk for the evidence trail with their `_PRE_S80` backups. | **No.** Single-use. |

### S80.E — recorded rather than asserted

**Stage 0's inertness is observed, not inferred.** 2026-09-22 08:53 IST: `grep -c "S80 extra expiries"` on `cron.log` = **0**, paired with a row-side count that *can* fail — `max_exp = 1` on both symbols at **3 runs each**, first rows **08:40:06 / 08:40:05 IST**, six `INGEST OPTION CHAIN COMPLETED` lines. **The zero alone would have been worthless**: it reads 0 just as readily on a day the ingest never ran, which is the CANNOT-FIRE shape this house treats as a non-check.

**The −0.4σ gap is a finding, not a feature of the build.** Across 11,795 runs the pin↔max-pain gap holds medians **−0.32 to −0.66σ across both symbols, every DTE and every session hour**, never changing sign — max pain sits systematically **below** peak gamma. Exact strike coincidence runs **1.2–5.4 %** everywhere **except NIFTY at 0 DTE, 13.9 %** (164 / 1,182), while **SENSEX at 0 DTE is NOT elevated (3.4 %)** — so this is *NIFTY expiry day*, not expiry day generically, and grid granularity cannot explain it because the grid does not change with DTE. `max_pain_in_pin_band` is **non-selective** at 20.8–42.1 % and does **not** rank the same cells as exact coincidence (**TD-S80-NEW-3**).

**Whether that coincidence predicts anything is UNANSWERED by design.** It is a conjunction question governed by parity-spec §5 and **ADR-009** — pre-registration, target and success criterion written before the first query. **ENH-97** is the standing warning: chi-sq 1.56, p ≈ 0.30 on 1,968 signals, with a salvage test that failed on power. n = 164 is enough to run it properly and not enough to run it casually.

**No consumer reads either new view.** Neither Marketview nor the Pine overlay was wired this session, so the ADR-023 recency-floor obligation on the *consumer* side is undischarged for them — as it still is for ENH-120/121/122. Under ADR-025 D2 clause 3 that is precisely why **BUILT = 2 of 14** and why the next board move is rendering rather than building.

**The `## Update log` table remains frozen at Session 67** — TD-S73-NEW-10, recorded by S73, S74 and S76 and **not fixed here either**. Repairing it means sourcing six sessions of entries, which is a separate edit.

*System Map updated Session 80, 2026-09-19/22 (§S80 — `v_gex_max_pain` (ENH-123) and `v_gex_pin_maxpain` (ENH-124) applied to the live database, both **off-spec and parked as L19 per ADR-025 D5**, neither counted toward parity; `gex_pin_maxpain_history` + `backfill_pin_maxpain_runs()` built because ADR-021's latest-run scoping makes the pin band unreadable historically from the view — the caveat §S69 recorded, now paid — gated by exact reproduction of the live view on 2026-09-18 and backfilled 11,795/11,795 with zero failures; superseded `backfill_pin_maxpain(text, date)` **dropped** rather than kept as a spare; `compute_gamma_metrics_local.py`'s `infer_expiry_date()` now raises on multi-expiry input, closing TD-S79-NEW-12, shipped **before** the ingest change because it converts silent corruption into a crash; `ingest_option_chain_local.py` gains an appended, `if _depth > 1:`-guarded capture-depth scaffold at **stage 0, depth 1**, observed inert at 08:53 IST the following morning by a paired check rather than by a grep that cannot fail; the spec's *"full expiry ladder per cycle"* refuted at **one expiry across all 2,923 cycles ever written**, with `:327` returning the ladder and `:365` discarding it; and the **−0.4σ** pin↔max-pain constant recorded over 11,795 runs with its one elevated cell isolated to NIFTY 0 DTE. `gex_pin_maxpain_history` **still owes its Rule 10 schema ADR — TD-S80-NEW-7**; committing DDL satisfies ADR-025 D2 clause 4 and not Rule 10. **NO cron, systemd unit, token path or Local↔AWS boundary changed by this work** — but the session did change topology: the **2026-09-22 disk-full access lockout** resized the root volume **8 GiB gp2 → 30 GiB gp3**, widened the logrotate scope, discharged the S71 kernel risk and left the feed needing a manual start, so **Deployment Topology carries a full §S80** and this section is the database half only. The `## Update log` table remains frozen at Session 67 — TD-S73-NEW-10, still not fixed here.) Previous: Session 79, 2026-09-15/16 (§S79).*"""


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

    n = norm.count(OLD)
    print(f"[S79 footer tail] anchor count == {n} (must be 1)")
    if n != 1:
        print("ABORT: anchor not unique.", file=sys.stderr)
        return 1

    patched = norm.replace(OLD, NEW, 1)

    expected = NEW.count("\n") - OLD.count("\n")
    got = patched.count("\n") - norm.count("\n")
    print(f"line delta expected {expected}, got {got}")
    if expected != got:
        print("ABORT: line delta mismatch.", file=sys.stderr)
        return 1

    if len(patched) <= len(norm):
        print("ABORT: file did not grow.", file=sys.stderr)
        return 1
    print(f"byte delta (normalised): +{len(patched) - len(norm)}")

    checks = [
        ("S80 section heading", patched.count("## §S80 — Session 80:"), 1),
        ("S80.A", patched.count("### S80.A"), 1),
        ("S80.B", patched.count("### S80.B"), 1),
        ("S80.C", patched.count("### S80.C"), 1),
        ("S80.D", patched.count("### S80.D"), 1),
        ("S80.E", patched.count("### S80.E"), 1),
        ("S80 footer", patched.count("*System Map updated Session 80"), 1),
        ("S79 section intact", patched.count("## §S79 — Session 79:"), 1),
        ("S79 footer intact", patched.count("*System Map updated Session 79"), 1),
    ]
    ok = True
    for label, got_v, want in checks:
        flag = "OK " if got_v == want else "FAIL"
        print(f"  [{flag}] {label}: {got_v} (want {want})")
        ok = ok and got_v == want
    if not ok:
        print("ABORT: structural assertions failed.", file=sys.stderr)
        return 1

    # the S80 section must be LAST -- this file is append-ordered by session
    tail = patched.rstrip()
    if not tail.endswith("Previous: Session 79, 2026-09-15/16 (§S79).*"):
        print("ABORT: S80 section is not at the file tail.", file=sys.stderr)
        return 1
    print("S80 section is last in the file")

    # ENH-123 / ENH-124 each named once in the new section's view table
    for eid in ("ENH-123", "ENH-124"):
        c = patched.count(f"**{eid}.**")
        print(f"{eid} view-table entry: {c} (want 1)")
        if c != 1:
            print(f"ABORT: {eid} view-table entry not unique.", file=sys.stderr)
            return 1

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
