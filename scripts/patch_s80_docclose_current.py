#!/usr/bin/env python3
"""patch_s80_docclose_current.py

S80 doc-close, file 5 of 10
  docs/session_notes/CURRENT.md  +  docs/registers/CURRENT_history.md

CURRENT.md is the ONE file in this set where a full rewrite is correct rather
than a splice: its own header declares it "Overwritten at the end of every
session to reflect what just happened". Doc Protocol v4 Rule 7's splice
amendment governs registers that accumulate; this file is declared living.

TWO FILES, ONE PASS -- because demoting S78 is a MOVE, not a delete:
  CURRENT.md      : S80 becomes "Last session"; S79 is re-emitted VERBATIM as
                    "Previous session S79"; S78 is removed.
  CURRENT_history : receives the S78 block VERBATIM.

NOTHING THAT ALREADY EXISTS IS RETYPED. The S79 and S78 blocks are extracted
from the live file and re-emitted byte-for-byte, so the demotion cannot
introduce transcription drift. Retyping them would be the one failure mode a
rewrite has that a splice does not.

HISTORY PLACEMENT IS DETECTED, NOT ASSUMED -- and it tests a LOCAL property.
The script parses session numbers out of CURRENT_history.md's H2 headings and
requires only what the insert actually depends on: the newest end descends
across the top 6, and 78 is above the first. It does NOT require whole-file
monotonicity. That was the first form of this check and it was wrong: 30
sessions of drifting heading wording ("## This session", "## Previous session",
"## This session block from Session 71") leave 43 of 73 H2s with no parseable
number and the older region unordered, so a global assertion fails on a file
that is fine for this purpose. Out-of-order pairs deeper in the file are
PRINTED, not fatal. It aborts only if the newest end itself is unreliable --
in which case positional insertion is the wrong mechanism, not a tunable one.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, structural
assertions in place of anchor counts (this is a rewrite), _PRE_S80_DOCCLOSE
backups on BOTH files, dry-run default (--apply).
"""
import argparse, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
# CURRENT.md lives in docs/session_notes/, NOT docs/registers/ -- its own header
# links history as ../registers/CURRENT_history.md, which only resolves from a
# sibling directory. The first version of this script had it wrong and aborted.
DEFAULT_TARGET = HERE / "docs" / "session_notes" / "CURRENT.md"
DEFAULT_HISTORY = HERE / "docs" / "registers" / "CURRENT_history.md"

MARKER = "Session 80"

H_LAST = "## Last session"
H_PREV78 = "## Previous session S78"
FOOTER_OLD = "*Session blocks S77 and earlier:"
FOOTER_NEW = ("*Session blocks S78 and earlier: "
              "[`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md).*")

HIST_SENTENCE_OLD = "Every session block before S78 lives in"
HIST_SENTENCE_NEW = "Every session block before S79 lives in"
SPLIT_NOTE_OLD = "Split at the S78 doc-close per **TD-S73-NEW-8**."
SPLIT_NOTE_NEW = ("Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history "
                  "at the S80 doc-close, moved verbatim rather than retyped.")

# -- the S80 block -----------------------------------------------------------

S80_BLOCK = r"""| Field | Value |
|---|---|
| **Date** | 2026-09-19 → 2026-09-22 (Session 80 — **the parity acceptance criterion, and the two off-spec layers that made the case for it.**) Two views, one table and one plpgsql function applied to the live database; two production Python scripts patched. |
| **Shape** | A session that built something well, measured that it was not on the spec, and then wrote the rule that gives *"not on the spec"* any content at all. **ADR-025 is the product. ENH-123 / ENH-124 are the evidence for it**, and they are parked rather than counted. |
| **(1) HEADLINE — ADR-025, the parity acceptance criterion** | **D1** parity is achieved when every one of the fourteen layers carries a **disposition**, not when all fourteen are built — so stopping early is a *result*. **D2** BUILT requires all four of: computes and has been read · run-scoped and EXPLAIN-verified per ADR-021 · **visible on an operator surface** · ENH entry with DDL committed under `sql/`. **D3** Hedgewall binds, deviation needs a stated reason. **D4** DECLINED-ON-EVIDENCE completes a layer; BLOCKED-ON-DATA is kept with zero members because §2.5's walls are real. **D5** off-spec layers file to §2.5 as **L19** and do not count. **Measured: BUILT = 2 of 14** (L1, L2) — not the three or five a register count suggests. **Five views compute and none renders**, so the board reorders to **rendering ENH-120 / 121 / 122**, not to building L9 or L12. |
| **(2) ENH-123 / ENH-124 — built, and off-spec** | **`v_gex_max_pain`** over `gex_strike_snapshots`, scoped `(symbol, run_id, expiry_date)`, with a clock. Equivalence gate **PASSED and it is a real cross-check** — agreed with the S40 `v_max_pain_by_strike` on both symbols (NIFTY **23,300** / SENSEX **74,400**) from a different base table, a different pivot, snapshots 20 minutes apart. Freshness floor probed **CAN FIRE** under `BEGIN`/`ROLLBACK`: **30 → 20 → 99999** and `is_fresh` flipped **at an unchanged age**. **`v_gex_pin_maxpain`** emits a distance in points, strike steps and **σ** — and **no verdict**: no tolerance constant appears in it, per TD-S79-NEW-21's measure-then-parameterise ruling. |
| **(3) The −0.4σ constant — 11,795 runs** | Medians **−0.32 to −0.66 across both symbols, every DTE and every session hour**, never changing sign: max pain sits systematically **below** peak gamma. Exact strike coincidence **1.2–5.4 %** everywhere **except NIFTY at 0 DTE, 13.9 %** (164 / 1,182) — ~3× the next cell, ~13× a random landing — while **SENSEX at 0 DTE is NOT elevated (3.4 %)**, so this is *NIFTY expiry day*, not expiry day generically. `max_pain_in_pin_band` is **non-selective** at 20.8–42.1 % and does **not** rank the same cells as exact coincidence — **TD-S80-NEW-3**. **Whether coincidence predicts anything is UNANSWERED by design**: that is ADR-009 pre-registration territory, and **ENH-97** (chi-sq 1.56, p ≈ 0.30 on 1,968 signals) is the standing warning. n = 164 is enough to run it properly and not enough to run it casually. |
| **(4) TD-S79-NEW-12 CLOSED — and the ordering was the point** | `infer_expiry_date()` now **raises** on more than one expiry instead of taking `min()` of a set it assumed was a singleton. Shipped **before** the ingest-depth change, deliberately: the guard converts silent corruption into a crash, so it must exist before anything can raise depth. |
| **(5) L9 ingest depth — measured, and staged at zero** | Day-level `hist_option_bars_1m` holds **21** expiries; S78's per-minute 14 was a subsample. **NIFTY** W1 67.8 % · current monthly 18.8 % · W2 5.2 % · **Dec quarterly 3.4 %** · **W3 0.47 %**. **SENSEX** W1 **97.25 %** · W2 2.65 % · monthly 0.089 %. **The selection rule matters more than the count** — chronological `[0:4]` takes W3 and misses the December quarterly, yielding 92.28 % and no curve. Ruling: NIFTY **4 selected** (94.45 %), SENSEX **2** (99.90 %). **Shipped as stage 0, depth 1, provably inert** — the extra pass is appended and guarded by `if _depth > 1:`, so W1's path is untouched and the `Run ID:` stdout contract stays bound to it. **Capture depth shipped as a constant, not the ruled parameter** — ADR-025 Amendment A §A1 carries the reason and the condition for moving it. |
| **(6) TD-S79-NEW-1 escalated by measurement** | The expiry-day σ overstatement is **time-varying**, not a fixed bias: **0.982 at 09:00 IST falling to 0.203 at 15:00 IST**. It does not merely inflate — it **hides** an intraday effect. Under day-σ the 0-DTE gap looks flat across the session; under the correct σ it **more than doubles**. A caveat that changes a finding's sign is not a footnote. |
| **Carry, unremediated** | **The deploy-direction inversion — fifth consecutive session unratified**, and S80 is the session that priced it: Amendment A §A2 item 5 is a reader acting on the uncorrected §S73.B, and the cost was **both patch scripts run against `~/meridian-engine`, the production tree**, before the operator's instruction to read PK corrected it. **ADR-024's Rule 11.3 gap — second consecutive close**: no `## Governance language` section, no CLAUDE.md footer, parent Status still PROPOSED against Amendment A's ACCEPTED. **`gex_pin_maxpain_history` owes a Rule 10 schema ADR — TD-S80-NEW-7**; its DDL is committed, which discharges D2 clause 4 and *not* Rule 10. **TD-S79-NEW-6** — three untracked scratch files still in the production tree. |
| **Verification — stage 0 OBSERVED INERT, 2026-09-22 08:53 IST** | `grep -c "S80 extra expiries" /home/ssm-user/meridian-engine/cron.log` = **0**, and the day's cycles carry **`max_exp = 1` on both symbols at 3 runs each**, first rows **08:40:06 IST (NIFTY) / 08:40:05 IST (SENSEX)**, six `INGEST OPTION CHAIN COMPLETED` lines. **The zero alone would not have shown this** — it returns 0 just as readily on a day the ingest never ran, which is the CANNOT-FIRE shape — so it is paired with a row-side count that **can** fail, and the pair is the evidence. The same reading independently confirms the day's first OCS row at **08:40 IST**, which is the figure ADR-025 Amendment A §A2 item 1 records getting wrong from a `LIMIT 20` sample. |
| **Ledger** | **TDs_NEW=13 filed + 1 WITHDRAWN** (TD-S80-NEW-1..14; **-6 withdrawn before filing** — a 3,093-vs-2,923 run-count "anomaly" that was two measurements three days apart, Monday having written exactly 85 × 2 = 170 runs. **-14 filed in the Rule 11 completion pass, after this block was written**). **Count and split are derived from `tech_debt.md` headings, never incremented by hand** — the method TD-S79-NEW-25 exists to enforce, and it is to be re-derived at commit time, not trusted from here. **TDs_CLOSED=1** (TD-S79-NEW-12). **ADRs_NEW=1** (ADR-025). **ADRs_AMENDED=1** (ADR-025 Amendment A, same session). **Enhancement Register TRIGGERED — second consecutive**, ENH-123 / ENH-124 written as Part 4. **Deployment Topology NOT updated** — nothing moved host, cron line, systemd unit, token path or Local↔AWS boundary. |
| **Next session** | **Render ENH-120 / ENH-121 / ENH-122.** That is the board move D2 clause 3 forces, and it is the first operator-surface change since ENH-81 at S37. Then **stage 1** of ingest depth (both symbols to 2) on a **non-expiry day**, after TD-S80-NEW-10's missing expiry filter is fixed. Then the Rule 12 project-knowledge re-upload. |"""


def split_current(norm: str) -> tuple[str, str, str, str]:
    """header, s79_body, s78_body, (validated) -- all verbatim from the live file."""
    for needle in (H_LAST, H_PREV78, FOOTER_OLD):
        if norm.count(needle) != 1:
            raise SystemExit(f"ABORT: expected exactly one '{needle}' in CURRENT.md, "
                             f"found {norm.count(needle)}.")
    i_last = norm.index(H_LAST)
    i_78 = norm.index(H_PREV78)
    i_foot = norm.index(FOOTER_OLD)
    if not (i_last < i_78 < i_foot):
        raise SystemExit("ABORT: CURRENT.md sections are not in the expected order.")

    header = norm[:i_last]
    s79 = norm[i_last + len(H_LAST):i_78]
    s78 = norm[i_78 + len(H_PREV78):i_foot]

    # drop the trailing '---' separator each section carries; re-added on emit
    s79 = s79.rstrip()
    if s79.endswith("---"):
        s79 = s79[:-3].rstrip()
    s78 = s78.rstrip()
    if s78.endswith("---"):
        s78 = s78[:-3].rstrip()
    return header, s79.strip("\n"), s78.strip("\n"), ""


def history_headings(htext: str) -> list[tuple[str, int]]:
    out = []
    for line in htext.split("\n"):
        if line.startswith("## "):
            m = re.search(r"\bS(\d{1,3})\b", line)
            if m:
                out.append((line.strip(), int(m.group(1))))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write; default is dry-run")
    ap.add_argument("--target", default=str(DEFAULT_TARGET))
    ap.add_argument("--history", default=str(DEFAULT_HISTORY))
    args = ap.parse_args()

    target = pathlib.Path(args.target)
    history = pathlib.Path(args.history)
    print(f"target : {target}")
    print(f"history: {history}")
    for p in (target, history):
        if not p.is_file():
            print(f"ABORT: not found: {p}", file=sys.stderr)
            return 1

    raw = target.read_bytes()
    text = raw.decode("utf-8-sig")
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    crlf = text.count("\r\n")
    lf_only = text.count("\n") - crlf
    eol = "\r\n" if crlf > lf_only else "\n"
    print(f"CURRENT baseline: {text.count(chr(10))} newlines, {len(raw)} bytes")
    print(f"CURRENT EOL: CRLF={crlf} LF={lf_only} -> {'CRLF' if crlf > lf_only else 'LF'}; BOM={had_bom}")

    hraw = history.read_bytes()
    htext = hraw.decode("utf-8-sig")
    h_bom = hraw.startswith(b"\xef\xbb\xbf")
    h_crlf = htext.count("\r\n")
    h_lf = htext.count("\n") - h_crlf
    h_eol = "\r\n" if h_crlf > h_lf else "\n"
    print(f"HISTORY baseline: {htext.count(chr(10))} newlines, {len(hraw)} bytes; "
          f"EOL={'CRLF' if h_crlf > h_lf else 'LF'}; BOM={h_bom}")

    if MARKER in text and H_PREV78 not in text:
        print("IDEMPOTENT: S80 already current and S78 already demoted. Nothing to do.")
        return 0

    norm = text.replace("\r\n", "\n")
    hnorm = htext.replace("\r\n", "\n")

    header, s79_body, s78_body, _ = split_current(norm)
    print(f"extracted S79 block: {len(s79_body)} bytes, {s79_body.count(chr(10)) + 1} lines")
    print(f"extracted S78 block: {len(s78_body)} bytes, {s78_body.count(chr(10)) + 1} lines")

    if "Session 79" not in s79_body:
        print("ABORT: extracted S79 block does not mention Session 79.", file=sys.stderr)
        return 1
    if "MERDIAN_Data_Inventory.md" not in s78_body:
        print("ABORT: extracted S78 block does not carry its headline artefact.", file=sys.stderr)
        return 1
    print("extracted blocks identified by their own content")

    # ---- history order: detected from the file, not assumed -----------------
    heads = history_headings(hnorm)
    if len(heads) < 5:
        print(f"ABORT: only {len(heads)} parseable session headings in history; "
              f"order cannot be inferred. Headings seen: {[h[0] for h in heads]}",
              file=sys.stderr)
        return 1
    nums = [n for _, n in heads]
    print(f"history headings: {len(heads)} parseable  first={heads[0][0]!r}  "
          f"last={heads[-1][0]!r}")

    # Placement depends on a LOCAL property, not a global one: this file has
    # accumulated 30 sessions of drifting heading wording ("## This session",
    # "## Previous session", "## This session block from Session 71"), so many
    # H2s carry no parseable session number and the older region is not ordered.
    # What the insert actually relies on is that the NEWEST end is reliable.
    TOP = 6
    top = nums[:TOP]
    print(f"top {len(top)} parsed session numbers: {top}")
    if not all(a > b for a, b in zip(top, top[1:])):
        print(f"ABORT: the newest end is not descending ({top}); the file has no "
              f"reliable newest block and positional insertion is the wrong "
              f"mechanism here.", file=sys.stderr)
        return 1
    if not 78 > nums[0]:
        print(f"ABORT: S78 is not newer than the first block (S{nums[0]}).", file=sys.stderr)
        return 1
    if 78 in nums:
        print("ABORT: history already carries an S78 block.", file=sys.stderr)
        return 1
    print(f"newest end NEWEST-FIRST and descending across {len(top)}; "
          f"78 > {nums[0]} -- S78 belongs at the top")

    # Reported, not fatal: the older region's disorder does not bear on placement.
    ooo = [(heads[i][0], heads[i + 1][0])
           for i in range(len(nums) - 1) if nums[i] <= nums[i + 1]]
    print(f"out-of-order pairs deeper in the file: {len(ooo)} (informational)")
    for a, b in ooo[:5]:
        print(f"    {a!r} then {b!r}")

    s78_section = f"{H_PREV78}\n\n{s78_body}\n\n---\n"

    i = hnorm.index("\n" + heads[0][0])
    h_patched = hnorm[:i + 1] + s78_section + "\n" + hnorm[i + 1:]
    print(f"S78 prepended above {heads[0][0]}")

    # ---- new CURRENT.md ----------------------------------------------------
    new_header = header
    for old, new in ((HIST_SENTENCE_OLD, HIST_SENTENCE_NEW),
                     (SPLIT_NOTE_OLD, SPLIT_NOTE_NEW)):
        if new_header.count(old) != 1:
            print(f"ABORT: header anchor count != 1 for {old!r}", file=sys.stderr)
            return 1
        new_header = new_header.replace(old, new, 1)
    print("header history sentence + split note updated")

    patched = (new_header
               + H_LAST + "\n\n" + S80_BLOCK + "\n\n---\n\n"
               + "## Previous session S79" + "\n\n" + s79_body + "\n\n---\n\n"
               + FOOTER_NEW + "\n")

    # ---- structural assertions on the rewrite ------------------------------
    checks = [
        ("Last session heading", patched.count(H_LAST), 1),
        ("Previous session S79 heading", patched.count("## Previous session S79"), 1),
        ("Previous session S78 heading removed", patched.count(H_PREV78), 0),
        ("S80 block present", patched.count("Session 80 — **the parity acceptance"), 1),
        ("footer restamped", patched.count(FOOTER_NEW), 1),
        ("old footer gone", patched.count(FOOTER_OLD), 0),
        ("S78 artefact gone from CURRENT", patched.count("MERDIAN_Data_Inventory.md"), 0),
    ]
    ok = True
    for label, got_v, want in checks:
        flag = "OK " if got_v == want else "FAIL"
        print(f"  [{flag}] {label}: {got_v} (want {want})")
        ok = ok and got_v == want
    if not ok:
        print("ABORT: structural assertions failed.", file=sys.stderr)
        return 1

    # S79 survives byte-for-byte
    if s79_body not in patched:
        print("ABORT: S79 block was not re-emitted verbatim.", file=sys.stderr)
        return 1
    if s78_body not in h_patched:
        print("ABORT: S78 block was not moved verbatim into history.", file=sys.stderr)
        return 1
    print("S79 re-emitted verbatim; S78 moved verbatim -- neither retyped")

    # the move conserves lines: history gains exactly what CURRENT loses
    cur_delta = patched.count("\n") - norm.count("\n")
    hist_delta = h_patched.count("\n") - hnorm.count("\n")
    s78_lines = s78_section.count("\n")
    print(f"CURRENT line delta {cur_delta:+d}; HISTORY line delta {hist_delta:+d} "
          f"(S78 section is {s78_lines} lines)")
    if hist_delta != s78_lines + 1:
        print(f"ABORT: history grew by {hist_delta}, expected {s78_lines + 1}.", file=sys.stderr)
        return 1

    if not args.apply:
        print("\nDRY RUN -- no write. Re-run with --apply.")
        return 0

    for p, data in ((target, raw), (history, hraw)):
        b = p.with_name(p.name + "_PRE_S80_DOCCLOSE")
        b.write_bytes(data)
        print(f"backup: {b}")

    out = patched.replace("\n", eol) if eol != "\n" else patched
    target.write_bytes((b"\xef\xbb\xbf" if had_bom else b"") + out.encode("utf-8"))
    print(f"WROTE {target}")

    hout = h_patched.replace("\n", h_eol) if h_eol != "\n" else h_patched
    history.write_bytes((b"\xef\xbb\xbf" if h_bom else b"") + hout.encode("utf-8"))
    print(f"WROTE {history}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
