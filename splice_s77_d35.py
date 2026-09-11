#!/usr/bin/env python3
"""
S77 doc-close splice — MERDIAN_Assumption_Register.md §D.35 rows 18..27.

Canon-v3 discipline:
  read_bytes -> utf-8-sig decode -> EOL measured, not assumed
  ALL count==1 anchor assertions evaluated BEFORE any write
  baseline sha256 + byte size asserted before any write
  _PRE_S77 backup, temp file + os.replace, post-write verify from disk

Dry-run by default. --apply to write.

Run from the repo root (~/meridian-cc):
    python3 splice_s77_d35.py
    python3 splice_s77_d35.py --apply
"""

import argparse
import hashlib
import os
import sys
import tempfile

REL = "docs/registers/MERDIAN_Assumption_Register.md"

BASELINE_SHA = "a6f087faee0db0b2a8760ca099145ba96f4336ba287daa3371ec73abc5cc7dc7"
BASELINE_BYTES = 260542
BASELINE_LINES = 870

IDEMPOTENCY_MARKER = "**D.35.27**"

# ─────────────────────────────────────────────────────────────────────────────
# Edit 1 — section header. Count moves 17 -> 27; scope widens to S76-S77.
# "operator" is dropped from the header because seven of the new rows are not
# operator claims; the attribution line below carries the per-range detail.
# ─────────────────────────────────────────────────────────────────────────────
E1_OLD = (
    "### D.35 — Session 76: seventeen operator claims withdrawn on measurement, "
    "and the absence-claim error that produced four of them (2026-09-09/10)"
)
E1_NEW = (
    "### D.35 — Sessions 76-77: twenty-seven claims withdrawn on measurement, "
    "and the absence-claim error that produced four of them (2026-09-09/11)"
)

# ─────────────────────────────────────────────────────────────────────────────
# Edit 2 — attribution. The existing sentence asserts every row is an operator
# claim from S76. That becomes false at row .20 and would be a stale assertion
# of exactly the class TD-S76-NEW-13..17 records.
# ─────────────────────────────────────────────────────────────────────────────
E2_OLD = (
    "**Attribution.** Every row in this section is an **operator** claim, held during S76 "
    "and withdrawn within the same session. **[measured here]** — a query or file read "
    "performed in S76, cited inline."
)
E2_NEW = (
    "**Attribution.** Rows **D.35.1-.19** are **operator** claims, held during S76 and "
    "withdrawn within S76 or at its close. Rows **D.35.20-.27** were added in **S77**: "
    "**D.35.21** is a premise carried in the S76 brief; the remaining seven are **Claude's "
    "own**, each raised and withdrawn inside S77. **[measured here]** — a query or file read "
    "performed in-session, cited inline."
)

# ─────────────────────────────────────────────────────────────────────────────
# Edit 3 — the ten new rows, inserted after the D.35.17 row and before the
# section-finding paragraph.
# ─────────────────────────────────────────────────────────────────────────────
E3_ANCHOR = (
    "\n\n**The section's finding — D.35.1 through D.35.4 are one error, not four.**"
)

ROWS = "\n".join([
    # ---- rescued from /tmp/s76_docclose_state.md, authored S76/S77 -----------
    r"""| **D.35.18** | *"228 EXPIRED rows in `ict_zones` contradict F-17 — nothing is ever retired."* | **REFUTED** *[measured here]* | F-17 claims the expiry gate cannot fire **under the live schedule**. Rows expired under an **earlier** schedule are fully consistent with that. The refuted sentence — *"nothing is ever retired"* — is **not one F-17 makes**. Discriminator for the open half: `max(updated_at)` on the EXPIRED population. | A corollary the reader authored, attributed to the finding, and then refuted. **Same shape as D.35.17.** Recorded in System Map **§S76.C** as a **gap in F-17, not a refutation of it**; F-17 not edited. |""",
    r"""| **D.35.19** | *"TD-S73-NEW-11 is live — the Decision Index carries four stacked stale footers."* | **REFUTED** *[measured here]* | **TD-S73-NEW-11 was RESOLVED at S73** — its own session footer records the fix (*"four stacked footers citing S62, S43, S59 and S39 collapsed to one"*) and S74's establishment clause re-asserts it. Measured at file 8: **exactly one** establishment footer; the seven paragraphs above it are per-session Rule 10 assessments, which is the file's running-record convention and not a stack. | Second instance in two days of D.35.18's class, and **the more costly direction**: .18 attacked a finding that was intact; this one preserved a defect already three sessions dead. A superseded-marker would have asserted a defect that no longer existed. **Control that worked:** the file-8 script gated on the establishment-footer count and would have aborted had the premise been true — **the premise check, not the anchor check, is what caught it**. |""",
    # ---- S77 ----------------------------------------------------------------
    r"""| **D.35.20** | *"`build_ict_htf_zones.py` is a step inside a longer chain, which is what spreads its start times across three hours."* | **REFUTED** *[agent]* | LATERAL join of every run since 2026-08-01 against the preceding 15 minutes of `script_execution_log`: **17 of 30 runs have no predecessor at all**, and those that do name a **different** script each time — `build_market_state_snapshot`, `ingest_breadth_from_ticks`, `compute_gamma_metrics`, `backfill_cas_close`, `build_trade_signal` — at gaps from **1.4 s to 10 m 34 s**. | Ambient cron traffic read as succession. The builder is not chained, and the start-time drift is still unexplained. |""",
    r"""| **D.35.21** | *"It runs once daily, host=aws"* — the S76 brief's characterisation | **REFUTED on both clauses** *[measured here]* | **Not once daily:** doubles on 2026-08-12 (03:28:25 and 03:31:04), 08-27 (03:28 and 04:00) and 08-31 (00:49 and 02:43); **23 runs across 06-02 → 06-04** at `c21e7c3`; and **three empty weekdays** — 09-07, 09-08, 09-10. **Not host=aws:** since 2026-06-05 the split is **13 `aws` / 59 `local`**. | The invoker search was **scoped on a property true of 18% of the population**, and the other 82% carried a label pointing at a host already believed dark, so it was never followed. **Fourth instance of the D.35.1-.4 class** — an absence claim over a set that could not have held the answer. |""",
    r"""| **D.35.22** | *"A LATERAL join against all other scripts will name the parent."* | **REFUTED — the instrument** *[agent]* | The predicate carried `s.script_name <> 'build_ict_htf_zones.py'`, which **excluded the only repeated adjacency in the data**: the **2,318 ms** run of 2026-08-12 03:31:04, beginning **2.6 s** after the 155,994 ms run that preceded it finished. The builder succeeding itself was unfindable by construction. | **CLAUDE.md Rule 0, clause 1.** A query written to find a parent made the self-invocation invisible. Written in the same hour Rule 0 was being cited as the session's method. |""",
    r"""| **D.35.23** | *"A systemd timer carrying `RandomizedDelaySec` explains the drift."* | **REFUTED** *[agent]* | `grep RandomizedDelaySec` across `/etc/systemd/system/`: **no unit carries it**. `systemctl list-timers --all` shows **17 timers, two of them MERDIAN**, both wsfeed, both fixed `OnCalendar` (`03:40:00 UTC` start, `10:05:00 UTC` stop). | Hypothesis dead. One real gain: **`~/.config/systemd/user/` does not exist**, so the earlier `systemctl --user` DBus failure concealed nothing — **user timers are eliminated, not unchecked**, which is a distinction the S76 elimination set never drew. |""",
    r"""| **D.35.24** | *"`MERDIAN_HOST=local` is set in `.env`, and `source .env` on every cron line is what supplies the override."* | **REFUTED, and the first refutation was itself defective** *[agent]* | `grep -c '^MERDIAN_HOST=' .env` → **0**; but that anchor is pinned to line start on a **sourced** file and cannot match the `export MERDIAN_HOST=...` form, which is the likelier shape. Unanchored `grep -c 'MERDIAN_HOST' .env` → **0** as well. The real mechanism is `ingest_breadth_from_ticks.py:64`: a **hardcoded `"host": "local"` literal** inside a hand-rolled `sb.table("script_execution_log").insert(...)` at `:60` that never touches `ExecutionLog`. | Inference placed the override in a file, then the confirming check was written so it could not have found the likely form — **two failures on one claim**, the second of the Rule 0 clause-1 class. Counts only were run against `.env`; **no content was read** (Rule 19). |""",
    r"""| **D.35.25** | *"`host` is not a machine — it is a launcher fingerprint."* | **PARTIALLY REFUTED** *[agent]* | Generalised column-wide from a single writer. True of **hand-rolled** inserts (`ingest_breadth_from_ticks.py:64`; `merdian_pipeline_alert_daemon` logging `host='Navin'`, a string `_detect_host()` cannot produce). **False of `ExecutionLog` writers**, which carry `_detect_host()` output — and `build_ict_htf_zones.py` has instantiated `ExecutionLog` since `46dbdc1`, **2026-04-28**, covering all 72 runs. | **`host` has three producers** — `_detect_host()`, a hand-typed literal, and the schema default `'local'::text` — so the column is sound only where the writing path is known. Any register conclusion drawn from it is unsound until the writer is identified. |""",
    r"""| **D.35.26** | *"`host DEFAULT 'local'::text` means the 59 `local` rows may be omission, so nothing follows about where the builder ran."* | **REFUTED — this is the withdrawal being withdrawn** *[measured here]* | `_payload_common()` (`core/execution_log.py:262`) includes `"host": self.host`, and `_insert_opening_row()` sends it on the **opening** row. **The schema default cannot fire for an `ExecutionLog` writer.** So the 59 `local` rows are `_detect_host()` output: `os.name == 'nt'`, or a `MERDIAN_HOST` override in the launching environment. Corroborating: **five commits appear under both labels** (`6d07d24`, `1d0a337`, `c21e7c3`, `60642fc`, `9f1e41c`), so the `local` writer tracks origin commit-for-commit; runtime is **bimodal with no overlap** (`local` 59-112 s, `aws` 120-173 s) on the same sha; and two `local` rows carry `git_sha = NULL` via `self.git_sha or None`, consistent with a checkout without `.git` or `git` off PATH. | **TD-S76-NEW-1 is neither confirmed nor refuted, and that is the finding.** Its measurement — 23 tasks Disabled, no `python`/`pythonw` process — is sound **for 2026-09-10** and **silent on 2026-06-05 → 08-27**, the interval holding 59 `local` runs on a five-a-week cadence. **OPEN.** Bears on TD-S73-NEW-5 and the archiver's *what broke first*, and promotes audit could-not-settle row 1 (the `build_ict_primitives.py` md5) from housekeeping to dispositive. |""",
    r"""| **D.35.27** | *"Querying `script_execution_log` for `expected_writes IS NULL` will enumerate the writers that bypass `ExecutionLog`."* | **REFUTED — the instrument** *[agent]* | `expected_writes` is **`NOT NULL DEFAULT '{}'::jsonb`** (`information_schema.columns`). The predicate is unsatisfiable. The query returned **no rows** against a population **known** to contain at least one bypassing writer (`ingest_breadth_from_ticks.py`, 29,440 runs). | **CLAUDE.md Rule 0, clause 1 — second instance this session, in my own instrument.** *No rows returned* measured nothing and would have been filed as a clean result. **The audit-coverage question it was written to answer is still open:** how many writers bypass `ExecutionLog`, and therefore carry no `expected_writes` contract, no `contract_met`, and no `exit_reason`, is unmeasured. |""",
])

# ─────────────────────────────────────────────────────────────────────────────
# Edit 4 — new S77 update-log paragraph. The S76 paragraph is left VERBATIM:
# "17 rows" was true of what S76 did, and rewriting a dated record to match a
# later total would falsify it. Each paragraph is session-scoped, so the two
# do not contradict.
# ─────────────────────────────────────────────────────────────────────────────
E4_ANCHOR = (
    "D.35.16 bears on any future comparison of MERDIAN's OB definition to a "
    "third-party indicator."
)

E4_ADD = (
    "\n\n**Update log — Session 77 (2026-09-11):** §D.35 **extended 17 → 27 rows**; the S76 "
    "paragraph above is left verbatim because *17 rows* is a true record of what S76 filed. "
    "**D.35.18 and .19** were authored at the S76 doc-close, carried only in "
    "`/tmp/s76_docclose_state.md`, and are filed here for the first time — they were recorded "
    "**nowhere else**, and `/tmp` does not survive a reboot. **D.35.20-.27 are S77**, and "
    "**seven of the eight are Claude's own claims**, each raised and withdrawn inside the "
    "session. **Two classes:** **.20, .24, .25 and .26** are one shape — a claim settled "
    "against an object *adjacent* to the claim rather than the claim's own object, which is "
    "the D.35.1-.4 insufficiency arriving from a new direction; **.22 and .27** are a second "
    "— **CLAUDE.md Rule 0 clause 1, in instruments written during the session that was citing "
    "Rule 0 as its method**. **.21 refutes the S76 brief on both clauses** and explains why "
    "the invoker search was mis-scoped. **.26 leaves TD-S76-NEW-1 OPEN** rather than refuted, "
    "and is the row most likely to matter: it reopens *what broke first* for the archiver "
    "(TD-S73-NEW-5) and promotes the `build_ict_primitives.py` md5 from a slip to a "
    "discriminator. **Still unmeasured, and named here so it is not mistaken for answered:** "
    "the count of writers that bypass `ExecutionLog` (.27), and the identity of the "
    "`build_ict_htf_zones.py` invoker, which remains **UNRESOLVED** with the watcher armed and "
    "never yet fired."
)

EDITS = [
    ("E1 section header 17 -> 27", E1_OLD, E1_NEW),
    ("E2 attribution scope", E2_OLD, E2_NEW),
    ("E3 insert rows .18-.27", E3_ANCHOR, "\n" + ROWS + E3_ANCHOR),
    ("E4 S77 update log", E4_ANCHOR, E4_ANCHOR + E4_ADD),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write; default is dry-run")
    ap.add_argument("--path", default=REL)
    args = ap.parse_args()

    path = args.path
    if not os.path.isfile(path):
        print(f"ABORT: not found: {path}", file=sys.stderr)
        return 2

    raw = open(path, "rb").read()
    sha_before = hashlib.sha256(raw).hexdigest()

    crlf = raw.count(b"\r\n")
    bare_lf = raw.count(b"\n") - crlf
    bom = raw.startswith(b"\xef\xbb\xbf")
    print("── baseline ──────────────────────────────────────────────")
    print(f"path   : {path}")
    print(f"bytes  : {len(raw)}   (expected {BASELINE_BYTES})")
    print(f"lines  : {raw.count(chr(10).encode())}   (expected {BASELINE_LINES})")
    print(f"EOL    : CRLF={crlf}  bare LF={bare_lf}  BOM={bom}")
    print(f"sha256 : {sha_before}")
    print(f"         expected {BASELINE_SHA}")

    # ── pre-conditions, ALL evaluated before any write ────────────────────
    fail = []
    if sha_before != BASELINE_SHA:
        fail.append("baseline sha256 mismatch — file changed since the S76 close")
    if len(raw) != BASELINE_BYTES:
        fail.append(f"baseline byte size mismatch: {len(raw)} != {BASELINE_BYTES}")
    if crlf != 0:
        fail.append(f"expected pure LF, measured {crlf} CRLF — re-measure before splicing")
    if bom:
        fail.append("unexpected BOM")

    text = raw.decode("utf-8-sig")

    if IDEMPOTENCY_MARKER in text:
        print(f"\nALREADY APPLIED: {IDEMPOTENCY_MARKER} present. Nothing to do.")
        return 0

    print("\n── anchors (count==1 required) ───────────────────────────")
    for name, old, _new in EDITS:
        n = text.count(old)
        print(f"{'OK ' if n == 1 else 'BAD'}  {name}: {n} match(es)")
        if n != 1:
            fail.append(f"{name}: expected exactly 1 match, found {n}")

    if fail:
        print("\nABORT — no write attempted:", file=sys.stderr)
        for f in fail:
            print(f"  - {f}", file=sys.stderr)
        print("\nSuspect the assertion before the edit.", file=sys.stderr)
        return 1

    out = text
    for _name, old, new in EDITS:
        out = out.replace(old, new, 1)

    new_raw = out.encode("utf-8")
    print("\n── projected ─────────────────────────────────────────────")
    print(f"bytes  : {len(raw)} -> {len(new_raw)}  ({len(new_raw) - len(raw):+d})")
    print(f"lines  : {raw.count(chr(10).encode())} -> {new_raw.count(chr(10).encode())} "
          f"({new_raw.count(chr(10).encode()) - raw.count(chr(10).encode()):+d})")
    print(f"CRLF   : {new_raw.count(chr(13).encode() + chr(10).encode())} (must be 0)")
    print(f"sha256 : {hashlib.sha256(new_raw).hexdigest()}")

    # ── post-conditions on the projected content ──────────────────────────
    post = []
    for n in range(18, 28):
        if f"**D.35.{n}**" not in out:
            post.append(f"row D.35.{n} absent from result")
    if out.count("### D.35 — Sessions 76-77: twenty-seven claims withdrawn") != 1:
        post.append("header not rewritten exactly once")
    if out.count("**Update log — Session 76 (2026-09-10):**") != 1:
        post.append("S76 update log no longer present exactly once")
    if out.count("**Update log — Session 77 (2026-09-11):**") != 1:
        post.append("S77 update log not added exactly once")
    if new_raw.count(b"\r\n") != 0:
        post.append("CRLF introduced")
    if post:
        print("\nABORT — post-conditions failed on projected content:", file=sys.stderr)
        for p in post:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("post-conditions: OK (10 rows present, header 1x, S76 log 1x, S77 log 1x, 0 CRLF)")

    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply.")
        return 0

    backup = path + "_PRE_S77"
    if not os.path.exists(backup):
        with open(backup, "wb") as fh:
            fh.write(raw)
        print(f"\nbackup : {backup}")
    else:
        print(f"\nbackup : {backup} already exists, left alone")

    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(new_raw)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

    verify = open(path, "rb").read()
    print("── verified from disk ────────────────────────────────────")
    print(f"bytes  : {len(verify)}")
    print(f"lines  : {verify.count(chr(10).encode())}")
    print(f"CRLF   : {verify.count(chr(13).encode() + chr(10).encode())}")
    print(f"sha256 : {hashlib.sha256(verify).hexdigest()}")
    ok = verify == new_raw
    print(f"match  : {'OK' if ok else 'MISMATCH — investigate immediately'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
