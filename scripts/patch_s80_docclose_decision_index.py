#!/usr/bin/env python3
"""patch_s80_docclose_decision_index.py

S80 doc-close, file 4 of 10 -- docs/decisions/MERDIAN_Decision_Index.md

FOUR substitutions, each count==1:
  1. ADR-025 Index row prepended above the ADR-024 row (Rule 11.1, newest-first).
  2. Reserved table: `ADR-025+ | Next-free` replaced by a consumed ADR-025 row
     plus `ADR-026+ | Next-free`. This is the S74-identified hazard -- a
     next-free marker naming a consumed ID -- and it does not recur here.
  3. Session 80 footer paragraph inserted above the establishment footer.
  4. Establishment footer restamped IN PLACE (TD-S73-NEW-11: restamp, never
     stack). S79's record is preserved as "Prior maintenance", and the
     parenthesis it opens is closed by the existing text, so nesting stays
     balanced -- the S80 stamp deliberately opens none of its own.

NOT REPAIRED HERE, DELIBERATELY: ADR-024's readiness caveat. No `## Governance
language` section, no CLAUDE.md footer, parent Status still PROPOSED against
Amendment A's ACCEPTED. S79 ruled this one operator decision; composing 024's
footer is authoring its governing sentence, not transcribing it. The S80 footer
records it unrepaired for a second session rather than papering over it.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore (this file is CRLF), BOM
preserved, count==1 anchors, line delta computed FROM the replacement text,
growth assertion, _PRE_S80_DOCCLOSE backup, dry-run default (--apply).
"""
import argparse, pathlib, sys

DEFAULT_TARGET = (pathlib.Path(__file__).resolve().parent.parent
                  / "docs" / "decisions" / "MERDIAN_Decision_Index.md")
MARKER = "| **ADR-025** |"

# -- 1. ADR-025 Index row ----------------------------------------------------

OLD_1 = "| **ADR-024** | 2026-09-15"

NEW_1 = r"""| **ADR-025** | 2026-09-21 · **AMENDMENT A 2026-09-22, same session** | Parity acceptance criterion — what it means for a Hedgewall-parity layer to be achieved, and when the programme is complete | **D1 — parity is achieved when every one of the fourteen layers carries a recorded disposition, not when all fourteen are built.** Dispositions: BUILT · PENDING · BLOCKED-ON-DECISION · BLOCKED-ON-DATA · DECLINED-ON-EVIDENCE. This makes stopping early a *result*. **D2 — a layer is BUILT only when all four hold:** it computes against the live database and its output has been read; it is run-scoped and EXPLAIN-verified per ADR-021; **it is visible on at least one operator surface** (Marketview or the Pine overlay); and it has an ENH register entry with its DDL committed under `sql/`. **Agreement with the reference is NOT required for BUILT** — that is a separate, optional, per-layer validation applied only where the reference publishes a comparable number. **D3 — Hedgewall binds**; deviation requires a stated reason recorded in the layer's ENH entry, and optionsflow.in is a second observation, never the binding target without such a note. **D4 — DECLINED-ON-EVIDENCE is a completed disposition, not a hole** (L3 carries seven register entries — more work than most built layers), and stays **distinct** from the two BLOCKED classes; **BLOCKED-ON-DATA is retained with zero members** among the fourteen because §2.5's walls are real. **D5 — a layer outside the fourteen does not count toward parity**; ENH-123 / ENH-124 file as **L19** under §2.5 and are **parked** — applied, granted, unrendered, uncounted. **Measured disposition at S80: BUILT = 2 of 14** (L1, L2). Not three, and not five. **Amendment A (2026-09-22)** records the constant-over-parameter deviation in ingest capture depth, five session self-corrections in ADR-024 §A9 form, and D2-clause-4 registration status for all six S80 production objects. | **Without a criterion, adding a layer and reporting progress is unfalsifiable.** The spec resolves fourteen layers to sources and orders them by value-per-hour, and never states what *"parity achieved"* means. S79 declined **L3** on evidence — the first layer rejected rather than deferred — which exposed the gap: with no criterion, the programme terminates only when the spec is exhausted. **TD-S79-NEW-22 filed it as D0 and required the ADR be drafted before the next layer was built.** S80 made it concrete three ways. **(i) Two more layers were built that are not among the fourteen** — max pain appears nowhere in the fourteen or in the ten-row build order. **(ii) Three spec claims were refuted by measurement:** L9's *"full expiry ladder per cycle"* is false — `option_chain_snapshots` holds **one expiry per cycle across all 2,923 cycles ever written** (`min = avg = max = 1`), with `ingest_option_chain_local.py:327` returning the ladder the vendor sends and `:365` discarding it uncommented; L4's gamma-weighted argmax was **rejected**, not deferred, having collapsed to ATM at −0.09σ / +0.19σ (it finds the money, not the wall); and L4 / L5 / L13 name columns that do not exist (`oi_total_calls` against ADR-015's `oi_call`). **(iii) Five views now compute and none renders** — S79's deferral of presentation *"until the full board is understood"* has run to five layers, and no operator surface has changed since ENH-81 at S37. **Each D2 clause is earned from a specific failure, not chosen for symmetry:** clause 2 from the unscoped view that crossed the PostgREST 8 s ceiling at 1.06M rows and silently emptied the Pine overlay for weeks (ADR-021); clause 3 because the spec's own §3 excludes *"Marketview iteration cycles"* from its effort numbers, which is precisely how five computed-but-invisible views accumulated; clause 4 because TD-S79-NEW-3 records `sql/` as a superseded rebuild source, so a view living only in the live database is one `DROP` from unrecoverable. **The board reorders immediately** — the next work is rendering ENH-120 / ENH-121 / ENH-122, not building L9 or L12. | **Parity = all fourteen BUILT** (rejected — makes declining a layer read as incompleteness, so the programme can end only by exhausting the spec, and L3 has already demonstrated a layer can be correctly refused); **counting off-spec layers toward parity** (rejected — unfalsifiable by construction, since a layer can always be added and progress reported against it); **collapsing DECLINED-ON-EVIDENCE into the BLOCKED classes** (rejected — a judgement that a layer should not be displayed is not a missing input nor an unmade decision, and merging them hides which ones are fixable); **dropping BLOCKED-ON-DATA for having zero members** (rejected — §2.5's HIRO-class order flow, which *"no layer in this document closes"*, and DIX-class dark-pool positioning have no Indian equivalent feed, and the category must exist for them); **requiring agreement with Hedgewall's published numbers for BUILT** (rejected — the reference does not publish a comparable number for every layer, and a criterion that cannot be evaluated on most of its domain is not a criterion); **spec §3's effort estimates as the ordering** (rejected — derived from source resolution without building anything, and two are now measured wrong: L9 is not *"3 h, cheapest real read on the list"*, and L4/L5 shipped at ENH-120 without the second variant the spec calls for). | [ADR-025-parity-acceptance-criterion.md](./ADR-025-parity-acceptance-criterion.md) |
| **ADR-024** | 2026-09-15"""

# -- 2. reserved table next-free marker --------------------------------------

OLD_2 = "| ADR-025+ | Next-free | — | Available |"

NEW_2 = r"""| ADR-025 | Parity acceptance criterion — when a Hedgewall-parity layer counts as achieved, and when the programme is complete | Navin / Claude | **ACCEPTED S80 2026-09-21 — full row above in Index.** Filed by **TD-S79-NEW-22 (D0)**, whose *Proper fix* clause required the ADR be drafted **before the next layer was built**; it was. **AMENDED at the S80 doc-close (Amendment A, 2026-09-22)** — records that ingest capture depth shipped as the module-level constant `EXPIRY_DEPTH` rather than the ruled `ingest.n_expiries.{symbol}` key, with the reason and the condition for moving it; files five session self-corrections in ADR-024 §A9 form; and discharges **D2 clause 4 for all six S80 production objects** while leaving `gex_pin_maxpain_history`'s Rule 10 schema ADR **owed** (TD-S80-NEW-7). Committing DDL and ratifying a schema are different obligations, and only the first is met. |
| ADR-026+ | Next-free | — | Available |"""

# -- 3. Session 80 footer ----------------------------------------------------

OLD_3 = "*MERDIAN Decision Index — established Session 23, 2026-05-09."

NEW_3 = r"""*Session 80 (2026-09-19→22): **ADRs_NEW=1 — ADR-025. ADRs_AMENDED=1 — ADR-025 Amendment A, same session.** **CODE CHANGED this session** — two views, one table and one plpgsql function applied to the live database (ENH-123 `v_gex_max_pain`, ENH-124 `v_gex_pin_maxpain`, `gex_pin_maxpain_history`, `backfill_pin_maxpain_runs`), and two production Python scripts patched (`compute_gamma_metrics_local.py`'s single-expiry guard closing TD-S79-NEW-12, and `ingest_option_chain_local.py`'s capture-depth scaffold). **Rule 10 assessment.** The two views are **additive derived read paths over an existing table** and file as ENH-123 / ENH-124 on the S79 precedent, not as ADRs. **`gex_pin_maxpain_history` is a new table and DOES reach Rule 10's bar — its ADR is OWED, not written, and is filed as TD-S80-NEW-7 rather than claimed as satisfied by ADR-025.** What ADR-025 rules is none of those objects; it is the **programme** they belong to. With no acceptance criterion, this session built two layers that are not in the spec and would have reported progress for them — **which is the argument for the ADR, written from the inside.** **The uncomfortable number is the point: BUILT = 2 of 14.** ENH-120 / ENH-121 / ENH-122 compute and do not render, so they are PENDING under D2 clause 3, and the board reorders to **rendering** rather than building. **Amendment A records a deviation against this ADR's own ruling**, which is why it is an amendment and not a footnote: capture depth shipped as the constant `EXPIRY_DEPTH`, not as `ingest.n_expiries.{symbol}`, because a parameter read that **fails open** would raise expiry depth silently on a cycle whose downstream consumers assume one expiry — exactly the corruption the same session's TD-S79-NEW-12 guard now crashes on. **A constant is the right instrument for a safety interlock and a parameter for a tuning knob**; the move to the parameter is recorded as a **condition** — the guard running a full expiry cycle in production without firing — and not as a plan. **§A2 files five self-corrections in ADR-024 §A9 form.** Four are the reflex §A9 already named — *reasoning from the archive when the source was available* — and one of those is **TD-S79-NEW-12's own shape committed hours after patching the guard for it**, taking the minimum of a `LIMIT 20` sample as the minimum of a set. **The fifth is different and worse, and is named as such:** a topology claim asserted without reading `MERDIAN_Deployment_Topology.md`, which put **both S80 patch scripts into `~/meridian-engine`, the production tree**, until the operator's instruction to read PK corrected it. **Rule 11.1 reverse check — RUN, because this pass adds a row and consumes an ID.** **`ADR-025+` is advanced to `ADR-026+`** in the reserved table; the S74 defect of a next-free marker naming a consumed ID **does not recur**. **ADR-024's readiness caveat is UNREPAIRED for a second consecutive session** — no `## Governance language` section, no CLAUDE.md settled-decisions footer, and the parent Status block at `:5` still reading PROPOSED against Amendment A's ACCEPTED at `:320`. **This pass wrote a CLAUDE.md governance footer for ADR-025 and deliberately wrote none for ADR-024**, because composing 024's is **authoring its governing sentence**, which is the operator decision S79 identified and left open. Writing 025's makes 024's absence **more** visible, not less, which is the correct direction for a gap that has now survived two closes. **TD-S79-NEW-24 stands unmeasured this pass** — the health check's third leg still cannot be counted, because a governance footer need not cite its own ADR id and only **33 of 120** bullets do. **ADR-010** rowless with two files on disk and **ADR-019** surviving only as a malformed **7-field row in the 4-column reserved table** both remain **CONFIRMED and open**; ADR-003/005/006/009/016 are absent from the Index and correctly present as Reserved. **Enhancement Register TRIGGERED — second consecutive**, ENH-123 and ENH-124 written as Part 4, after nine non-triggers ending at S79. **Deployment Topology deliberately NOT updated** — no host, cron line, systemd unit, token path or Local↔AWS boundary moved, and the two patched scripts run exactly where they already ran. **The deploy-direction inversion remains UNRATIFIED for a fifth consecutive session, and S80 is the session that measures what leaving it costs:** §A2's fifth self-correction is precisely a reader acting on the uncorrected §S73.B, and the cost was two patch scripts run against production.*

*MERDIAN Decision Index — established Session 23, 2026-05-09."""

# -- 4. maintenance stamp, restamped IN PLACE --------------------------------

OLD_4 = "Last maintenance: Session 79 (2026-09-15/16"

NEW_4 = ("Last maintenance: Session 80, 2026-09-19→22 — **ADRs_NEW=1** (ADR-025, decided 09-21 "
         "and documented same session) · **ADRs_AMENDED=1** (ADR-025 Amendment A, appended at "
         "this doc-close). **Next-free marker advanced `ADR-025+` → `ADR-026+`**, 025 being "
         "consumed by this pass and 026 genuinely free. **ADR-024's Rule 11.3 gap is UNREPAIRED "
         "for a second consecutive session** and is recorded rather than papered over — this "
         "pass wrote a CLAUDE.md footer for ADR-025 and none for ADR-024, which makes the "
         "omission more visible, not less. **TD-S73-NEW-11 verified before writing:** exactly "
         "one establishment footer, and this clause is restamped **in place**, not stacked. "
         "Full record in the Session 80 footer above. Prior maintenance: Session 79 (2026-09-15/16")

SUBS = [
    ("1. ADR-025 Index row prepended", OLD_1, NEW_1),
    ("2. reserved table 025 consumed, 026 next-free", OLD_2, NEW_2),
    ("3. Session 80 footer", OLD_3, NEW_3),
    ("4. maintenance stamp restamped in place", OLD_4, NEW_4),
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
    rows_before = norm.count("| **ADR-")
    print(f"Index bold-ID rows before: {rows_before}")

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

    rows_after = patched.count("| **ADR-")
    print(f"Index bold-ID rows after: {rows_after} (must be before + 1)")
    if rows_after != rows_before + 1:
        print("ABORT: Index row count did not advance by exactly 1.", file=sys.stderr)
        return 1

    if patched.count(MARKER) != 1:
        print("ABORT: ADR-025 Index row must appear exactly once.", file=sys.stderr)
        return 1
    if patched.count("| **ADR-024** | 2026-09-15") != 1:
        print("ABORT: ADR-024 row disturbed.", file=sys.stderr)
        return 1
    print("ADR-025 row present once; ADR-024 row intact")

    if "| ADR-025+ | Next-free" in patched:
        print("ABORT: consumed next-free marker still present.", file=sys.stderr)
        return 1
    if patched.count("| ADR-026+ | Next-free | — | Available |") != 1:
        print("ABORT: ADR-026+ next-free marker not set exactly once.", file=sys.stderr)
        return 1
    print("next-free marker advanced 025 -> 026, consumed form gone")

    # TD-S73-NEW-11: exactly one establishment footer, restamped not stacked
    est = patched.count("*MERDIAN Decision Index — established Session 23, 2026-05-09.")
    print(f"establishment footers: {est} (must be 1)")
    if est != 1:
        print("ABORT: establishment footer stacked or lost.", file=sys.stderr)
        return 1
    if patched.count("Last maintenance: Session 80") != 1:
        print("ABORT: maintenance stamp not restamped exactly once.", file=sys.stderr)
        return 1
    if patched.count("Prior maintenance: Session 79 (2026-09-15/16") != 1:
        print("ABORT: S79 maintenance record not preserved.", file=sys.stderr)
        return 1
    print("maintenance stamp restamped in place; S79 record preserved")

    if patched.count("*Session 80 (2026-09-19→22):") != 1:
        print("ABORT: S80 session footer not inserted exactly once.", file=sys.stderr)
        return 1
    print("Session 80 footer present once")

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
