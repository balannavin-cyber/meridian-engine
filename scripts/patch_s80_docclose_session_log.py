#!/usr/bin/env python3
"""patch_s80_docclose_session_log.py

S80 doc-close, file 6 of 10 -- docs/registers/session_log.md

ONE substitution, count==1: the S80 entry is prepended above the S79 entry.

FORM, taken from the file rather than assumed: newest-first, no header, one
long single-line paragraph per session, blank line between entries. The anchor
is the S79 entry's opening, so the insert lands at the top of the file without
depending on the file starting where it appears to.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchor, line delta computed FROM the replacement text, growth assertion,
_PRE_S80_DOCCLOSE backup, dry-run default (--apply).
"""
import argparse, pathlib, re, sys

DEFAULT_TARGET = (pathlib.Path(__file__).resolve().parent.parent
                  / "docs" / "registers" / "session_log.md")
MARKER = "Session 80 (Fri–Tue"

OLD = "2026-09-15→16 · `10a7ae5`"

ENTRY = (
    "2026-09-19→22 · `85dfad2` + `b094fa2` + this commit · Session 80 "
    "(Fri–Tue — the parity acceptance criterion, and the two off-spec layers that made "
    "the case for it) — **PASS. TWO VIEWS, ONE TABLE AND ONE PLPGSQL FUNCTION APPLIED TO THE "
    "LIVE DATABASE; TWO PRODUCTION PYTHON SCRIPTS PATCHED.** "

    "**(1) ADR-025 is the session's product, and the two layers built before it are the evidence "
    "for why it was needed.** The Hedgewall parity spec resolves fourteen layers to sources and "
    "orders them by value-per-hour, and never states what *\"parity achieved\"* means. S79 "
    "declined L3 on evidence — the first layer rejected rather than deferred — which "
    "exposed that a programme with no criterion can only terminate by exhausting its spec. "
    "TD-S79-NEW-22 filed it as D0 and required the ADR be drafted **before the next layer was "
    "built**; it was. **D1** parity is achieved when every one of the fourteen carries a "
    "**disposition**, not when all fourteen are built, so stopping early becomes a *result*. "
    "**D2** BUILT requires all four of: computes and has been read · run-scoped and "
    "EXPLAIN-verified per ADR-021 · **visible on an operator surface** · ENH entry with "
    "DDL committed under `sql/`. Each clause is earned from a specific failure rather than chosen "
    "for symmetry — clause 2 from the unscoped view that crossed the PostgREST 8 s ceiling at "
    "1.06M rows and silently emptied the Pine overlay for weeks, clause 3 because the spec's own "
    "§3 excludes *\"Marketview iteration cycles\"* from its effort numbers which is exactly "
    "how five invisible views accumulated, clause 4 because TD-S79-NEW-3 records `sql/` as a "
    "superseded rebuild source so a view living only in the database is one `DROP` from "
    "unrecoverable. **D3** Hedgewall binds, deviation needs a stated reason. **D4** "
    "DECLINED-ON-EVIDENCE completes a layer and stays distinct from the two BLOCKED classes; "
    "BLOCKED-ON-DATA is kept with zero members because §2.5's HIRO- and DIX-class walls have "
    "no Indian feed. **D5** an off-spec layer does not count toward parity. **The measured "
    "disposition is BUILT = 2 of 14** — L1 and L2, not the three or five a register count "
    "suggests — and the board reorders immediately to **rendering ENH-120 / ENH-121 / "
    "ENH-122**, which would be the first operator-surface change since ENH-81 at S37. "

    "**(2) ENH-123 / ENH-124 — built, measured, and parked as L19.** `v_gex_max_pain` computes "
    "max pain over `gex_strike_snapshots` scoped `(symbol, run_id, expiry_date)` and emits a clock "
    "— the S40 `v_max_pain_by_strike` emits **no timestamp at all** and takes an unbounded "
    "`max(ts)`, and was observed on 2026-09-19 at 11:40 IST serving a strike from 09-17 15:40 IST. "
    "**The equivalence gate PASSED and it is a real cross-check, not a tautology**: NIFTY "
    "**23,300** and SENSEX **74,400** from both views, from different base tables, different "
    "pivots, snapshots 20 minutes apart. **The freshness floor was proven CAN FIRE** under "
    "`BEGIN`/`ROLLBACK` — `stale_floor_min_used` tracked **30 → 20 → 99999** and "
    "`is_fresh` flipped **false → true at an unchanged age of 895.6 min** — which closes "
    "the TD-S79-NEW-2 ambiguity for this view; the parameter is deliberately left **unseeded**, "
    "because a seeded value equal to the COALESCE fallback makes a successful read and a NULL read "
    "indistinguishable, which is that TD's whole content. `v_gex_pin_maxpain` emits the pin ↔ "
    "max-pain distance in points, strike steps and **σ** — **and no verdict**: no "
    "tolerance constant appears in it and none may be added until the history supports one, per "
    "TD-S79-NEW-21's measure-then-parameterise ruling. **Neither is a parity layer**; max pain "
    "appears nowhere in the fourteen or the build order, and a session brief calling it *\"the next "
    "layer\"* went unchecked against the spec for four hours. "

    "**(3) The −0.4σ constant — 11,795 runs, and it is a genuinely new finding.** "
    "`gex_pin_maxpain_history` was built because `v_gex_strike_pin_zone` is latest-run scoped by "
    "ADR-021, so the pin band cannot be read historically from the view at all; the table "
    "materialises the same computation per run, gated by reproducing the live view on 2026-09-18 "
    "for both symbols with all four of `peak_pin_strike` / `pin_lower` / `pin_upper` / `n_strikes` "
    "identical, and backfilled **11,795 / 11,795 runs, zero failures**. Across it the gap is a "
    "**stable −0.4σ** — medians −0.32 to −0.66 across **both symbols, every "
    "DTE and every session hour**, never changing sign — so max pain sits systematically "
    "**below** peak gamma, closer to a constant of this market than to a varying relationship. "
    "Exact strike coincidence runs **1.2–5.4 %** everywhere **except NIFTY at 0 DTE, 13.9 %** "
    "(164 / 1,182), roughly 3× the next cell and ~13× a random landing, while **SENSEX at "
    "0 DTE is NOT elevated (3.4 %)** — so this is *NIFTY expiry day*, not expiry day "
    "generically, and grid granularity cannot account for it because the grid does not change with "
    "DTE. `max_pain_in_pin_band` is **non-selective** at 20.8–42.1 % and does **not** rank the "
    "same cells as exact coincidence (TD-S80-NEW-3). **Whether coincidence predicts anything is "
    "UNANSWERED by design** — a conjunction question governed by ADR-009 pre-registration, "
    "with ENH-97 standing as the warning at chi-sq 1.56, p ≈ 0.30 on 1,968 signals; n = 164 is "
    "enough to run it properly and not enough to run it casually. "

    "**(4) TD-S79-NEW-12 CLOSED, and the ordering was the point.** `infer_expiry_date()` now "
    "**raises** on more than one expiry instead of taking `min()` of a set it assumed was a "
    "singleton. It shipped **before** the ingest change, deliberately, because the guard converts "
    "silent corruption into a crash and must therefore exist before anything can raise capture "
    "depth. "

    "**(5) L9 ingest depth — measured on the vendor tier, and the selection rule matters more "
    "than the count.** Day-level `hist_option_bars_1m` holds **21** expiries; S78's per-minute 14 "
    "was a subsample. NIFTY: W1 67.8 % · current monthly 18.8 % · W2 5.2 % · **Dec "
    "quarterly 3.4 %** · **W3 0.47 %**. SENSEX: W1 **97.25 %** · W2 2.65 % · monthly "
    "0.089 %. Chronological `future_expiries[0:4]` yields 92.28 % on NIFTY **and no curve** — "
    "four points inside three weeks — because slicing takes the worthless expiry and misses "
    "the valuable one. Ruling: **NIFTY 4 selected (94.45 %), SENSEX 2 (99.90 %)**, the monthly "
    "identified as the last weekly of its calendar month. **The spec's claim that "
    "`option_chain_snapshots` carries the full ladder is false** — it holds **one expiry per "
    "cycle across all 2,923 cycles ever written**, with `ingest_option_chain_local.py:327` "
    "returning the ladder and `:365` discarding it uncommented; no regression occurred, the "
    "capability never existed. Shipped as **stage 0, depth 1, provably inert**: the extra pass is "
    "**appended** and guarded by `if _depth > 1:`, so W1's path is untouched and the stdout `Run "
    "ID:` contract and ENH-71's `record_write` stay bound to W1 alone. **Verified live the next "
    "morning, 2026-09-22 08:53 IST** — `grep -c \"S80 extra expiries\"` on `cron.log` = **0**, "
    "paired with a row-side count that *can* fail: `max_exp = 1` on both symbols at 3 runs each, "
    "first rows 08:40:06 / 08:40:05 IST. The zero alone would have been worthless, since it reads 0 "
    "just as readily on a day the ingest never ran. "

    "**(6) TD-S79-NEW-1 escalated by measurement.** The expiry-day σ overstatement from "
    "`GREATEST(dte,1)` is **time-varying, not a fixed bias** — 0.982 at 09:00 IST falling to "
    "0.203 at 15:00 IST — and it does not merely inflate, it **hides**: under day-σ the "
    "0-DTE gap looks flat across the session, under the correct σ it **more than doubles**. A "
    "caveat that changes a finding's shape is not a footnote. "

    "**(7) ADR-025 Amendment A, appended at doc-close, records a deviation against this ADR's own "
    "ruling.** Capture depth shipped as the module constant `EXPIRY_DEPTH`, not as the ruled "
    "`ingest.n_expiries.{symbol}` key, because a parameter read that **fails open** would raise "
    "depth silently on a cycle whose consumers assume one expiry — exactly what the same "
    "session's guard now crashes on. A constant is the right instrument for a safety interlock and "
    "a parameter for a tuning knob; the move is recorded as a **condition** (the guard running a "
    "full expiry cycle without firing), not a plan. **§A2 files five self-corrections in "
    "ADR-024 §A9 form.** Four are the reflex §A9 already named — *reasoning from the "
    "archive when the source was available* — and the first of them is **TD-S79-NEW-12's own "
    "shape committed hours after patching the guard for it**, taking the minimum of a `LIMIT 20` "
    "sample as the minimum of a set and reporting the day's first row as 09:00 when it is 08:40 "
    "IST. The others: a 3,093-vs-2,923 run-count *\"anomaly\"* that was two measurements three days "
    "apart (Monday wrote exactly 85 × 2 = 170 runs), a stale `CURRENT.md` sentence called a "
    "phantom commit, and a cross-tier `sha256` comparison that **C-15 explicitly names an invalid "
    "instrument** — `core.autocrlf=true` makes every text file differ Local↔EC2 by exactly "
    "its line count, and `git hash-object` is the correct one. **The fifth is different and worse:** "
    "a topology claim asserted without reading `MERDIAN_Deployment_Topology.md` — that "
    "`~/meridian-cc` would *\"re-invert the deploy direction\"*, when §S73.A establishes the "
    "agent tree for precisely the opposite reason — and the consequence was not theoretical: "
    "**both S80 patch scripts ran against `~/meridian-engine`, the production tree**, until the "
    "operator's instruction to read PK first corrected it. "

    "**Ledger.** TDs_NEW=13 filed + 1 WITHDRAWN (TD-S80-NEW-1..14; **-6 withdrawn before filing**, "
    "the run-count anomaly above; **-14 filed in the Rule 11 completion pass**). Count and split "
    "**derived from `tech_debt.md` headings, never incremented by hand**, per TD-S79-NEW-25. "
    "TDs_CLOSED=1 (TD-S79-NEW-12). ADRs_NEW=1 (ADR-025). ADRs_AMENDED=1 (ADR-025 Amendment A, same "
    "session). **Enhancement Register TRIGGERED — second consecutive**, ENH-123 / ENH-124 "
    "written as Part 4. **Deployment Topology deliberately NOT updated** — no host, cron line, "
    "systemd unit, token path or Local↔AWS boundary moved. **Carried unremediated:** the "
    "deploy-direction inversion, **fifth consecutive session unratified** and now with a measured "
    "cost; ADR-024's Rule 11.3 gap for a **second consecutive close** — no `## Governance "
    "language` section, no CLAUDE.md footer, parent Status still PROPOSED against Amendment A's "
    "ACCEPTED, and this pass wrote a footer for ADR-025 and deliberately none for ADR-024, which "
    "makes the omission more visible rather than less; and `gex_pin_maxpain_history`'s **owed Rule "
    "10 schema ADR (TD-S80-NEW-7)** — its DDL is committed, which discharges D2 clause 4 and "
    "**not** Rule 10, those being different obligations."
)

NEW = ENTRY + "\n\n" + OLD


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

    entry_re = re.compile(r"^20\d\d-\d\d-\d\d", re.M)
    before = len(entry_re.findall(norm))
    print(f"entries before: {before}")

    n = norm.count(OLD)
    print(f"[S79 entry opening] anchor count == {n} (must be 1)")
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
    print(f"byte delta (normalised): +{len(patched) - len(norm)}  "
          f"(S80 entry is {len(ENTRY)} chars)")

    after = len(entry_re.findall(patched))
    print(f"entries after: {after} (must be before + 1)")
    if after != before + 1:
        print("ABORT: entry count did not advance by exactly 1.", file=sys.stderr)
        return 1

    # newest-first: the file must now OPEN with the S80 entry
    if not patched.startswith("2026-09-19→22 · `85dfad2`"):
        print("ABORT: S80 entry is not at the top of the file.", file=sys.stderr)
        return 1
    if patched.count(MARKER) != 1:
        print("ABORT: S80 entry must appear exactly once.", file=sys.stderr)
        return 1
    print("S80 entry is first; S79 entry immediately follows")

    # the entry is one single-line paragraph, as every other entry is
    first_line = patched.split("\n", 1)[0]
    print(f"S80 entry occupies 1 line, {len(first_line)} chars")
    if "\n" in ENTRY:
        print("ABORT: S80 entry contains a newline; entries are single-line.", file=sys.stderr)
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
