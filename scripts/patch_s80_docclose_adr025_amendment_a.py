#!/usr/bin/env python3
"""patch_s80_docclose_adr025_amendment_a.py

S80 doc-close, file 3 of 10 -- docs/decisions/ADR-025-parity-acceptance-criterion.md

FOUR substitutions, each count==1:
  1. Header table gains an "Amended" row above "Rule 10 class".
  2. The L9 `ingest.n_expiries.{symbol}` parameter bullet gains a pointer to A1.
  3. The L9 "Stage it" bullet gains a pointer to A1's finer staging.
  4. The file tail gains "## Amendment A" -- A1 shipped-vs-ruled, A2 self-
     corrections in ADR-024 section A9 form, A3 D2-clause-4 registration status.

WHY 2 AND 3 ARE POINTERS, NOT REWRITES: ADR-025 is Accepted. An accepted ADR's
body records what was decided; it is amended below, never edited in place. The
two bullets are the ones the implementation deviated from, so they carry a
pointer so a reader cannot reach them without reaching the deviation.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchors, line delta computed FROM the replacement text, growth assertion,
_PRE_S80_DOCCLOSE backup, dry-run default (--apply).
"""
import argparse, pathlib, sys

DEFAULT_TARGET = (pathlib.Path(__file__).resolve().parent.parent
                  / "docs" / "decisions" / "ADR-025-parity-acceptance-criterion.md")
MARKER = "## Amendment A"

# -- 1. header "Amended" row -------------------------------------------------

OLD_1 = "| Rule 10 class |"
NEW_1 = ("| Amended | **Amendment A**, 2026-09-22 (Session 80) "
         "— what shipped against what was ruled; session self-corrections; "
         "D2 clause 4 registration status. Body text above is unchanged. |\n"
         "| Rule 10 class |")

# -- 2. the parameter bullet -------------------------------------------------

OLD_2 = ("- The count is `ingest.n_expiries.{symbol}` in `merdian_parameters` per ADR-016. "
         "This is a **capture-depth config**, not an output threshold, so TD-S79-NEW-21's "
         "measure-before-parameterise rule does not bind it the same way.")

NEW_2 = OLD_2 + ("\n  - **Amendment A1 (2026-09-22): what shipped is a module-level constant, "
                 "not this parameter.** The deviation is deliberate and conditioned; see below.")

# -- 3. the staging bullet ---------------------------------------------------

OLD_3 = ("- **Stage it**: ship at W1+W2, watch ENH-99 retry telemetry for one week, "
         "then extend NIFTY to 4. TD-080 is S1-recurring across S22 / S28 / S29.")

NEW_3 = OLD_3 + ("\n  - **Amendment A1: the staging shipped finer than this.** A stage 0 at "
                 "depth 1 — provably inert — precedes W1+W2.")

# -- 4. Amendment A ----------------------------------------------------------

OLD_4 = ("- **jobid 19.** Re-enabling it caps L13's history at 14 days and deletes "
         "what L14 needs. Unresolved, TD-S76-NEW-2.")

NEW_4 = OLD_4 + r"""

---

## Amendment A — 2026-09-22 (Session 80)

*Appended at S80 doc-close. The body above is the decision as accepted on 2026-09-21 and is
not edited. This amendment records where the implementation departed from it, what the session
got wrong, and which of D2 clause 4's obligations are now discharged.*

### A1 — Capture depth shipped as a constant, not a parameter

The L9 ruling places the count in `merdian_parameters` as `ingest.n_expiries.{symbol}`, per
ADR-016. What shipped in `ingest_option_chain_local.py` (commit `b094fa2`) is a module-level
constant:

```python
EXPIRY_DEPTH = {"NIFTY": 1, "SENSEX": 1}
```

with the extra-expiry pass **appended** before the completion print and guarded by `if _depth > 1:`.

**Why, stated rather than assumed.** A database-read parameter introduces a read path, and a read
path can fail. ADR-023's obligation is that a read fails to *absent*, never to stale — but a
capture-depth read that failed **open** would raise depth silently on a cycle whose downstream
consumers assume one expiry, which is precisely the corruption TD-S79-NEW-12's guard now crashes
on. At depth 1 the constant makes stage 0 inert **by inspection**: the extra pass is unreachable,
W1's path is untouched, and the stdout `Run ID:` contract and ENH-71's `record_write` stay bound
to W1 alone. A constant is the right instrument for a safety interlock; a parameter is the right
instrument for a tuning knob. This is one of the former until the guard has proven itself.

**Actual staging**, finer than the bullet above describes:

| stage | depth | gate |
|---|---|---|
| **0 — shipped S80** | NIFTY 1 · SENSEX 1 | Inert by construction. Verification owed: `grep -c "S80 extra expiries"` on `cron.log` must be **0**, and the day's runs must show `max_exp = 1` at 2–3 runs per symbol. |
| 1 | NIFTY 2 · SENSEX 2 | A non-expiry day, **after** TD-S80-NEW-10's missing expiry filter is fixed. Not before: a second expiry entering `option_chain_snapshots` arms the per-strike `max()` mixture in the S40 `v_max_pain_by_strike`. |
| 2 | NIFTY 4 by the **selection** rule · SENSEX 2 | One week of clean ENH-99 retry telemetry. TD-080 is S1-recurring across S22 / S28 / S29. |

**The parameter is not abandoned; it is conditioned.** It becomes the correct instrument at stage 2,
when depth is a tuning decision rather than an interlock. Recorded as a condition and not a plan:
move the depth to `ingest.n_expiries.{symbol}` once TD-S79-NEW-12's guard has run in production
across a full expiry cycle without firing.

### A2 — Self-corrections, Session 80

In the form of ADR-024 §A9, and for the same reason: an error corrected inside a session leaves no
trace unless it is written down, and the pattern across them is worth more than any one of them.

1. **`[0]` on an unordered set — TD-S79-NEW-12's own shape, hours after patching the guard for it.**
   Claimed the day's first `option_chain_snapshots` row was 09:00 IST; it is **08:30–08:40 IST**.
   The claim came from `ORDER BY ts ASC LIMIT 5` over an arbitrary `LIMIT 20` backfill subset —
   the minimum of a sample read as the minimum of the set. The guard shipped that same morning
   exists to crash on exactly this class of reasoning.

2. **Two measurements three days apart, called an anomaly.** Reported 3,093 against 2,923 `run_id`s
   as unexplained. Monday 2026-09-21 wrote 85 × 2 = 170 runs; 2,923 + 170 = 3,093 exactly. It had
   already been drafted as TD-S80-NEW-6 before the arithmetic was done, and was withdrawn before
   filing — later than it should have been caught, earlier than the register.

3. **Called a stale sentence a phantom commit.** Asserted that `CURRENT.md` referenced a follow-on
   commit that did not exist. On EC2, `grep -c "TD-S79-NEW-23"` = 1 and `change_log[0]` = S79: the
   commit is present and one sentence describing it is stale. Downgraded to **TD-S80-NEW-13**.

4. **Used `sha256` across tiers, which C-15 names an invalid instrument.** Compared file hashes
   Local against EC2 to test identity. `core.autocrlf=true` makes every text file differ across
   those tiers by exactly its line count; the cross-tier instrument is **`git hash-object`**.
   C-15 states this in `MERDIAN_ClaudeCode_Guardrails.md`, which had already been read.

5. **Had §S73.A backwards, and patched production because of it.** Argued against `~/meridian-cc`
   on the grounds that *"CC lives on EC2, so using it re-inverts the deploy direction."* §S73.A
   establishes the agent tree for precisely the opposite reason — so agent work happens on EC2
   **without touching production**. The consequence was not theoretical: both S80 patch scripts
   ran against `~/meridian-engine`, the production tree. Corrected on the operator's instruction
   to read PK first.

**The pattern.** 1 through 4 are one reflex, and it is the reflex ADR-024 §A9 already named:
*reasoning from the archive when the source was available* — a sample for a set, a stale figure
for a current one, a memory of a file for the file. 5 is a different and worse failure: asserting
a topology claim without reading the topology document, then acting on it. Reading PK before
asserting is the remedy for all five, and it is cheap in every one of these cases.

### A3 — D2 clause 4 registration, status at doc-close

Of the six objects the *Consequences* section lists:

- `v_gex_max_pain`, `v_gex_pin_maxpain`, `gex_pin_maxpain_history`,
  `backfill_pin_maxpain_runs(text, timestamptz, timestamptz, integer)` — **DDL committed under
  `sql/` at `85dfad2`.** Register entries land in this doc-close, Enhancement Register Part 4.
- `backfill_pin_maxpain(text, date)` — **dropped**, as ruled. It computed before `ON CONFLICT`
  could discard, and timed out; a second callable path into one table is a hazard, not a spare.
- `scripts/backfill_pin_maxpain.py` — **committed at `85dfad2`**, byte-identical to the run that
  produced the 11,795 rows (`sha256 453f1be8…`). It hardcodes the window 2026-05-25 → 2026-09-18,
  so re-running it extends nothing; extending the history means editing the window.

**Clause 4 is discharged for all six. Rule 10 is not.** `gex_pin_maxpain_history` is a new table
and still owes its own schema ADR — **TD-S80-NEW-7**. Committing DDL and ratifying a schema are
different obligations, and only the first has been met.

*Amendment A — Session 80 doc-close, 2026-09-22. No decision in the body above is reversed,
narrowed or extended by this amendment.*"""

SUBS = [
    ("1. header Amended row", OLD_1, NEW_1),
    ("2. n_expiries parameter bullet pointer", OLD_2, NEW_2),
    ("3. staging bullet pointer", OLD_3, NEW_3),
    ("4. Amendment A appended", OLD_4, NEW_4),
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

    # Amendment A structure: one section heading, three subsections, once each
    for head in ("## Amendment A — 2026-09-22 (Session 80)",
                 "### A1 — Capture depth shipped as a constant, not a parameter",
                 "### A2 — Self-corrections, Session 80",
                 "### A3 — D2 clause 4 registration, status at doc-close"):
        c = patched.count(head)
        print(f"heading present {c}x: {head[:48]}")
        if c != 1:
            print(f"ABORT: heading must appear exactly once: {head}", file=sys.stderr)
            return 1

    # the body above must be untouched: its decision headings survive unchanged
    for d in ("### D1 — Scope", "### D2 — Evidence bar", "### D3 — Reference",
              "### D4 — Declining", "### D5 — Off-spec layers"):
        if patched.count(d) != 1:
            print(f"ABORT: body decision heading disturbed: {d}", file=sys.stderr)
            return 1
    print("D1..D5 body headings intact, one each")

    # the five self-corrections must all be present
    if patched.count("**The pattern.**") != 1:
        print("ABORT: A2 pattern paragraph missing.", file=sys.stderr)
        return 1
    for n in range(1, 6):
        if f"\n{n}. **" not in patched[patched.index("### A2"):]:
            print(f"ABORT: A2 self-correction {n} missing.", file=sys.stderr)
            return 1
    print("A2 carries 5 numbered self-corrections + pattern paragraph")

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
