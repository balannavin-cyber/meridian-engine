"""S85 measure-only: inventory the MERDIAN docs corpus AT HEAD.

Reads blobs with `git -C <repo> show HEAD:<path>` so the measurement is of the
commit, not the working tree. For each file: bytes, lines, and counts of
entry-ID patterns split into (a) IDs that anchor a markdown heading -- these
are candidate RAG chunk boundaries -- and (b) total mentions anywhere.

Files with zero heading-anchored IDs are flagged NO-ENTRY-ID-STRUCTURE.
"""
import re
import subprocess
import sys

REPO = "/home/ssm-user/meridian-cc"

PATTERNS = {
    "TD": re.compile(r"\bTD-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\b"),
    "ADR": re.compile(r"\bADR-\d{3}\b"),
    "SD": re.compile(r"§D\.\d+(?:\.\d+)?"),
    "ENH": re.compile(r"\bENH-\d+[A-Za-z]?\b"),
    "CASE": re.compile(r"\bCASE-\d{4}-\d{2}-\d{2}-[a-z0-9-]+\b"),
}
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")
# A bolded register row such as "- **TD-S84-NEW-1** ..." also anchors an entry.
BOLD_ROW = re.compile(r"^\s*[-*|]\s*\*\*")


def git(args):
    return subprocess.run(["git", "-C", REPO] + args,
                          capture_output=True, check=True).stdout


def main():
    names = git(["ls-tree", "-r", "--name-only", "HEAD"]).decode().splitlines()
    targets = [n for n in names
               if n.startswith("docs/") or n == "CLAUDE.md"]
    targets.sort(key=lambda n: (n != "CLAUDE.md", n))

    rows = []
    for path in targets:
        raw = git(["show", f"HEAD:{path}"])
        nbytes = len(raw)
        binary = b"\x00" in raw[:8192]
        if binary:
            rows.append((path, nbytes, None, {}, {}, True))
            continue
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        head_ids = {k: 0 for k in PATTERNS}
        all_ids = {k: 0 for k in PATTERNS}
        for ln in lines:
            is_anchor = bool(HEADING.match(ln)) or bool(BOLD_ROW.match(ln))
            for key, rx in PATTERNS.items():
                hits = rx.findall(ln)
                if hits:
                    all_ids[key] += len(hits)
                    if is_anchor:
                        head_ids[key] += len(hits)
        rows.append((path, nbytes, len(lines), head_ids, all_ids, False))

    w = max(len(r[0]) for r in rows)
    hdr = (f"{'path':{w}} {'bytes':>9} {'lines':>7} "
           f"{'TD':>5} {'ADR':>4} {'§D':>4} {'ENH':>4} {'CASE':>4}   flag")
    print(hdr)
    print("-" * len(hdr))
    tot_b = tot_l = 0
    flagged = []
    agg_head = {k: 0 for k in PATTERNS}
    agg_all = {k: 0 for k in PATTERNS}
    for path, nb, nl, hi, ai, binary in rows:
        tot_b += nb
        if binary:
            print(f"{path:{w}} {nb:>9} {'--':>7} "
                  f"{'--':>5} {'--':>4} {'--':>4} {'--':>4} {'--':>4}   BINARY")
            continue
        tot_l += nl
        for k in PATTERNS:
            agg_head[k] += hi[k]
            agg_all[k] += ai[k]
        flag = ""
        if sum(hi.values()) == 0:
            flag = "NO-ENTRY-ID-STRUCTURE"
            flagged.append((path, nb, nl, sum(ai.values())))
        print(f"{path:{w}} {nb:>9} {nl:>7} "
              f"{hi['TD']:>5} {hi['ADR']:>4} {hi['SD']:>4} "
              f"{hi['ENH']:>4} {hi['CASE']:>4}   {flag}")

    print()
    print(f"FILES: {len(rows)}   BYTES: {tot_b}   LINES: {tot_l}")
    print("heading-anchored ID totals:", agg_head)
    print("all-mention ID totals     :", agg_all)
    print()
    print(f"FLAGGED (no heading-anchored entry ID): {len(flagged)}")
    for path, nb, nl, mentions in flagged:
        print(f"  {path}  ({nb} B, {nl} L, {mentions} inline ID mentions)")


if __name__ == "__main__":
    sys.exit(main())
