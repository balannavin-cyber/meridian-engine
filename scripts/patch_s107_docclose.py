#!/usr/bin/env python3
"""S107 engine doc-close: register edits (Doc Protocol v5.1 Rule 3, doc-close skill order).

Run from the repository root, in a worktree on branch engine/s107-close cut from origin/main.

    python scripts/patch_s107_docclose.py            # dry run: checks every anchor, writes nothing
    python scripts/patch_s107_docclose.py --apply    # writes

Every edit asserts its anchor occurs exactly once. Files are read and written as bytes; the end-of-line
style and the absence of a BOM are preserved. Nothing is written unless every edit of every file passed.
The payload texts are in scripts/s107_docclose_payload/.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:  # a Windows console may not be UTF-8; never let a print stop the run
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = Path.cwd()
if not (ROOT / "CLAUDE.md").exists() or not (ROOT / "docs" / "registers").is_dir():
    print("STOP: run this from the repository root")
    sys.exit(2)
PAY = Path(__file__).resolve().parent / "s107_docclose_payload"
APPLY = "--apply" in sys.argv


def die(msg: str) -> None:
    print("STOP:", msg)
    sys.exit(2)


def pay(name: str) -> str:
    p = PAY / name
    if not p.exists():
        die(f"payload file missing: {p}")
    t = p.read_bytes().decode("utf-8")
    if "\r" in t:
        die(f"payload has CR characters: {name}")
    return t


class Doc:
    """One file, held as LF text; written back with its original EOL."""

    def __init__(self, rel: str, must_exist: bool = True):
        self.rel = rel
        self.path = ROOT / rel
        self.new = not self.path.exists()
        if self.new and must_exist:
            die(f"file missing: {rel}")
        raw = b"" if self.new else self.path.read_bytes()
        if raw[:3] == b"\xef\xbb\xbf":
            die(f"unexpected BOM: {rel}")
        self.raw0 = raw
        self.crlf = raw.count(b"\r\n")
        lone_lf = raw.count(b"\n") - self.crlf
        if self.crlf and lone_lf:
            die(f"mixed line endings: {rel} (crlf={self.crlf}, lf={lone_lf})")
        self.text = raw.decode("utf-8").replace("\r\n", "\n")
        self.notes: list[str] = []

    def _one(self, anchor: str) -> None:
        n = self.text.count(anchor)
        if n != 1:
            die(f"{self.rel}: anchor occurs {n} times, expected 1: {anchor[:90]!r}")

    def replace(self, anchor: str, new: str, note: str) -> None:
        self._one(anchor)
        self.text = self.text.replace(anchor, new)
        self.notes.append(note)

    def before(self, anchor: str, ins: str, note: str) -> None:
        self._one(anchor)
        self.text = self.text.replace(anchor, ins + anchor)
        self.notes.append(note)

    def after(self, anchor: str, ins: str, note: str) -> None:
        self._one(anchor)
        self.text = self.text.replace(anchor, anchor + ins)
        self.notes.append(note)

    def append(self, ins: str, note: str) -> None:
        if not self.text.endswith("\n"):
            die(f"{self.rel}: does not end with a newline")
        self.text += ins
        self.notes.append(note)

    def absent(self, marker: str) -> None:
        if marker in self.text:
            die(f"{self.rel}: already contains {marker!r} (applied before?)")

    def out_bytes(self) -> bytes:
        t = self.text.replace("\n", "\r\n") if self.crlf else self.text
        return t.encode("utf-8")

    def report(self) -> None:
        b = self.out_bytes()
        l0, l1 = self.raw0.count(b"\n"), b.count(b"\n")
        print(f"  {self.rel}: {'NEW' if self.new else 'edit'}  lines {l0} -> {l1} ({l1 - l0:+d})  "
              f"bytes {len(self.raw0)} -> {len(b)} ({len(b) - len(self.raw0):+d})  "
              f"eol={'CRLF' if self.crlf else 'LF'}  sha256 {hashlib.sha256(b).hexdigest()[:16]}")
        for n in self.notes:
            print(f"      - {n}")


docs: list[Doc] = []


def open_doc(rel: str, must_exist: bool = True) -> Doc:
    d = Doc(rel, must_exist)
    docs.append(d)
    return d


# ---------------------------------------------------------------- 1. ADR-033 and the Decision Index
adr = open_doc("docs/decisions/ADR-033-gamma-v2-versioned-isolation.md")
adr.absent("## 9. State at the S107 close")
adr.replace(
    "| Status | **PROPOSED** (S107, Wed 2026-11-25).",
    "| Status | **PROPOSED; carried out in part on the operator's step-by-step approvals — see section 9** (S107, Wed 2026-11-25; section 9 added Thu 2026-11-26).",
    "status line points to section 9")
adr.append(pay("adr033_s9.md"), "section 9 appended")

di = open_doc("docs/decisions/MERDIAN_Decision_Index.md")
di.absent("| **ADR-033** |")
di.before("| **ADR-032** | 2026-10-30 (Session 102)", pay("di_row.md"), "Index row ADR-033 prepended")
di.replace("| ADR-033+ | Next-free | — | Available |\n", pay("di_row2.md"), "status table: ADR-033 row; next-free ADR-034+")
di.before("*MERIDIAN Decision Index — established Session 23, 2026-05-09.", pay("di_session.md"), "Session 107 paragraph")
di.replace(
    "Last maintenance: **Session 104, 2026-11-04 —",
    "Last maintenance: **Session 107, 2026-11-26 — ADRs_NEW=1 (ADR-033, PROPOSED, carried out in part) · ADRs_AMENDED=0 · one row added · next-free marker `ADR-033+` → `ADR-034+`.** Before that: **Session 104, 2026-11-04 —",
    "footer: last maintenance")

# ---------------------------------------------------------------- 2. tech_debt.md and its history
td = open_doc("docs/registers/tech_debt.md")
td.absent("### TD-S107-NEW-1 ")
td.before("### S106 status changes to existing entries (doc-close run for Session 106;",
          pay("td_new.md") + pay("td_status.md"), "30 open entries and the S107 status paragraph")
tdh = open_doc("docs/registers/tech_debt_history.md")
tdh.absent("### TD-PIN2-NEW-13 ")
tdh.append(pay("td_history_add.md"), "TD-PIN2-NEW-13 (closed at filing) appended")

# ---------------------------------------------------------------- 3. Assumption Register
ar = open_doc("docs/registers/MERDIAN_Assumption_Register.md")
ar.absent("## D.61 ")
ar.append(pay("ar_d61_d62.md"), "sections D.61 (3 rows) and D.62 (8 rows) appended")

# ---------------------------------------------------------------- 4. Enhancement Register
enh = open_doc("docs/registers/MERDIAN_Enhancement_Register.md")
enh.absent("### ENH-149 ")
enh.replace("ENH-01 through ENH-148 (ENH-148 minted at the S104 close",
            "ENH-01 through ENH-150 (ENH-149 allocated in intake I-002 and ENH-150 minted at the S107 close, both written 2026-11-26: the gross pin, LIVE, and gamma V2 beside V1, built and backfilled with its live writer not approved; ENH-148 minted at the S104 close",
            "scope line")
enh.before("| ENH-SDM | Structural Divergence Monitor (ADR-018 D4) |", pay("enh_rows.md"), "index rows ENH-149, ENH-150")
enh.before("*Part 13 (Sessions 98–103; written at the S103 close, 2026-11-01)", pay("enh_blocks.md"), "blocks ENH-149, ENH-150")
enh.append(pay("enh_part15.md"), "Part 15 footer")

# ---------------------------------------------------------------- 4b. System Map, Topology, Data Inventory, STREAMS, intake
sm = open_doc("docs/registers/MERDIAN_System_Map.md")
sm.absent("## §S107 ")
sm.append(pay("system_map_s107.md"), "section S107 appended")
tp = open_doc("docs/registers/MERDIAN_Deployment_Topology.md")
tp.absent("## §S107 ")
tp.append(pay("topology_s107.md"), "section S107 appended")
dinv = open_doc("docs/registers/MERDIAN_Data_Inventory.md")
dinv.absent("## 13. Hand-added at the S107 doc-close")
dinv.append(pay("data_inventory_13.md"), "section 13 appended")

st = open_doc("docs/registers/STREAMS.md")
st.absent("| X11 |")


def swap_row(doc: Doc, prefix: str, payload: str, note: str) -> None:
    lines = doc.text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(hits) != 1:
        die(f"{doc.rel}: {len(hits)} rows start with {prefix!r}, expected 1")
    new_rows = pay(payload).rstrip("\n").split("\n")
    lines[hits[0]:hits[0] + 1] = new_rows
    doc.text = "\n".join(lines)
    doc.notes.append(note)


swap_row(st, "| **Engine (hub)** |", "streams/lane_engine.md", "lane row: engine")
swap_row(st, "| **Order flow (tape)** |", "streams/lane_ofl.md", "lane row: order flow")
swap_row(st, "| **Retail** |", "streams/lane_retail.md", "lane row: retail")
swap_row(st, "| **Board pin** |", "streams/lane_pin.md", "lane row: Board pin")
swap_row(st, "| OFL | `tape_live_cycle/events/wall/label`", "streams/obj_ofl.md", "objects row: OFL")
swap_row(st, "| PIN | `v_gex_strike_rank`", "streams/obj_pin.md", "objects row: PIN")
swap_row(st, "| X1 | PIN → OFL |", "streams/x1.md", "X1 rewritten")
swap_row(st, "| X3 | Engine → OFL |", "streams/x3.md", "X3 updated")
swap_row(st, "| X10 | PIN → Engine |", "streams/x10.md", "X10 closed; X11, X12 added")
swap_row(st, "| R3 | Each lane's next close_inputs", "streams/r3.md", "R3 updated")
swap_row(st, "| R8 | PK Protocol v1 in force", "streams/r8.md", "R8 done; R9 added")
st.replace("**Status: v0.2, ruled 2026-11-21 (operator, \"as recommended\"; Doc Protocol v5.1 Rules 12–16).**",
           "**Status: v0.3 (rows updated at the S107 engine close, 2026-11-26); v0.2 ruled 2026-11-21 (operator, \"as recommended\"; Doc Protocol v5.1 Rules 12–16).**",
           "status line v0.3")

i2 = open_doc("docs/registers/intake/I002.md")
i2.absent("## 8. Closed out at the S107 doc-close")
i2.append(pay("i002_close.md"), "section 8 appended")
i3 = open_doc("docs/registers/intake/I003.md", must_exist=False)
if not i3.new:
    die("docs/registers/intake/I003.md already exists")
i3.text = pay("I003.md")
i3.notes.append("new file")

# ---------------------------------------------------------------- 5. CURRENT roll
cur = open_doc("docs/session_notes/CURRENT.md")
curh = open_doc("docs/registers/CURRENT_history.md")
cur.absent("**S107 — Saturday 2026-11-21")
PREV = "## Previous session S105\n"
cur._one(PREV)
cut = cur.text.index(PREV)
moved = cur.text[cut:]
if not moved.endswith("\n"):
    die("CURRENT.md: the S105 block does not end with a newline")
moved_b = moved.encode("utf-8")
moved_sha = hashlib.sha256(moved_b).hexdigest()
curh.append(
    "\n<!-- moved verbatim from CURRENT.md at the S107 doc-close (2026-11-26): the S105 block "
    f"({len(moved_b)} B, sha256 {moved_sha}) -->\n\n" + moved,
    f"S105 block appended verbatim ({len(moved_b)} B, sha256 {moved_sha[:12]}…)")
if not curh.text.endswith(moved):
    die("CURRENT_history.md: appended block is not byte-identical to what left CURRENT.md")
head = cur.text[:cut]
LAST = "## Last session\n"
if head.count(LAST) != 1:
    die("CURRENT.md: '## Last session' not found exactly once in the kept part")
i = head.index(LAST)
s106 = head[i:].replace(LAST, "## Previous session S106\n", 1)
note_s106 = ("> *The `NEXT SESSION PICKS UP` list inside this block is as written at the S106 close and is superseded "
             "by the S107 list above. Its item 1 (`tape_w`) is done (2026-11-24); item 3 is done (2026-11-23); "
             "item 9 is met for OFL9, MR-S13, PIN2 and PIN3; items 2, 4–8 and 10 are carried in the S107 list, item 8.*\n\n")
s106 = s106.replace("## Previous session S106\n\n", "## Previous session S106\n\n" + note_s106, 1)
if note_s106 not in s106:
    die("CURRENT.md: could not place the S106 note")
LANES = "## LANES (Doc Protocol v5.1 Rule 7"
if s106.count(LANES) != 1:
    die("CURRENT.md: the S106 part does not hold exactly one LANES section")
old_lanes = s106[s106.index(LANES):]
if old_lanes.count("\n## ") != 0:
    die("CURRENT.md: the old LANES section is not the last section of the S106 part")
s106 = s106[: s106.index(LANES)]
preamble = head[:i]
ROLL = "This file carries the current session and one predecessor, and nothing else."
if preamble.count(ROLL) != 1:
    die("CURRENT.md: preamble sentence not found exactly once")
preamble = preamble.replace(
    ROLL,
    f"**S105 ({len(moved_b)} B, sha256 `{moved_sha[:8]}…`) moved at the S107 close**, asserted byte-identical on both sides. " + ROLL)
cur.text = preamble + pay("current_s107.md") + s106
cur.notes.append("S107 block written; S106 demoted to Previous (its LANES table replaced by the S107 one, which sits above it); S105 moved to CURRENT_history.md")

# ---------------------------------------------------------------- 6. session_log
sl = open_doc("docs/session_notes/session_log.md")
slh = open_doc("docs/registers/session_log_history.md")
sl.absent("Session 107 —")
parts = sl.text.split("\n\n")
header, entries = parts[0], [p for p in parts[1:] if p.strip()]
if not header.startswith("**History.**"):
    die("session_log.md: unexpected header")
if len(entries) != 10:
    die(f"session_log.md: expected 10 entries, found {len(entries)}")
if not all(e[:4] == "2026" for e in entries):
    die("session_log.md: an entry does not start with a date")
oldest = entries[-1].rstrip("\n")
new_entry = pay("session_log_entry.md").strip("\n")
kept = [new_entry] + [e.rstrip("\n") for e in entries[:-1]]
sl.text = header + "\n\n" + "\n\n".join(kept) + "\n"
sl.notes.append("S107 entry added at the top; oldest entry rolled out (10 kept)")
if not slh.text.endswith("\n"):
    die("session_log_history.md: does not end with a newline")
slh.text = slh.text.rstrip("\n") + "\n\n" + oldest + "\n\n"
slh.notes.append(f"oldest entry appended verbatim (starts {oldest[:24]!r})")

# ---------------------------------------------------------------- 7. merdian_reference.json
rj = open_doc("docs/registers/merdian_reference.json")
rj.absent('"_s107_addendum"')
try:
    before = json.loads(rj.text)
except Exception as e:  # noqa: BLE001
    die(f"merdian_reference.json does not parse before the edit: {e}")
add = json.loads(pay("addendum.json"))
block = json.dumps(add, indent=2, ensure_ascii=False)
block = "\n".join(("  " + ln) if k else ln for k, ln in enumerate(block.split("\n")))
if not rj.text.endswith("\n  }\n}\n"):
    die("merdian_reference.json: unexpected tail")
rj.text = rj.text[: -len("\n}\n")] + ',\n  "_s107_addendum": ' + block + "\n}\n"
rj.notes.append("_s107_addendum added")
for key, old, new in (("version", "v84", "v85"),
                      ("last_updated_session", "Session 106", "Session 107"),
                      ("last_updated_date", "2026-11-21", "2026-11-26")):
    if before.get(key) != old:
        die(f"merdian_reference.json: {key} is {before.get(key)!r}, expected {old!r}")
    hits = [a for a in (f'"{key}": "{old}"',) if rj.text.count(a) == 1]
    if not hits:
        die(f'merdian_reference.json: "{key}": "{old}" does not occur exactly once')
    rj.text = rj.text.replace(hits[0], f'"{key}": "{new}"')
    rj.notes.append(f"{key} {old} -> {new}")
try:
    after = json.loads(rj.text)
except Exception as e:  # noqa: BLE001
    die(f"merdian_reference.json does not parse after the edit: {e}")
if after["_s107_addendum"] != add or after["version"] != "v85":
    die("merdian_reference.json: addendum or version did not land as written")
if set(after) - set(before) != {"_s107_addendum"}:
    die("merdian_reference.json: unexpected change in top-level keys")
for k in before:
    if k not in ("version", "last_updated_session", "last_updated_date") and before[k] != after[k]:
        die(f"merdian_reference.json: key {k} changed")

# ---------------------------------------------------------------- 7b. tracker
tr = open_doc("docs/registers/agentic_layer_roadmap_S90.md")
tr.absent("| v2.23 |")
tr.replace("**Status: v2.22 — LIVE TRACKER", "**Status: v2.23 — LIVE TRACKER", "status line v2.23")
tr.before("| v2.22 | 2026-11-21 | **S106 close", pay("tracker_row.md"), "changelog row v2.23")

# ---------------------------------------------------------------- 8. CLAUDE.md footer
cm = open_doc("CLAUDE.md")
cmh = open_doc("docs/registers/CLAUDE_history.md")
cm.absent("*CLAUDE.md v1.80 ")
lines = cm.text.rstrip("\n").split("\n")
footer = lines[-1]
if not footer.startswith("*CLAUDE.md v1.79 — 2026-11-21") or not footer.endswith("*"):
    die("CLAUDE.md: the last line is not the v1.79 footer")
if cmh.text.count(footer):
    die("CLAUDE_history.md already holds the v1.79 footer")
cmh.text = cmh.text.rstrip("\n") + "\n\n" + footer + "\n"
cmh.notes.append("v1.79 footer appended verbatim")
lines[-1] = pay("claude_footer.md").strip("\n")
cm.text = "\n".join(lines) + "\n"
cm.notes.append("footer v1.79 -> v1.80 (no rule changed)")

# ---------------------------------------------------------------- report and write
print(("APPLY" if APPLY else "DRY RUN (nothing is written)") + f" — {len(docs)} files")
for d in docs:
    d.report()
print(f"CURRENT roll: S105 block {len(moved_b)} B sha256 {moved_sha}")
if APPLY:
    for d in docs:
        d.path.parent.mkdir(parents=True, exist_ok=True)
        d.path.write_bytes(d.out_bytes())
    print("WRITTEN. Next: git status --porcelain, then stage by explicit path.")
else:
    print("ALL ANCHORS OK. Re-run with --apply to write.")
