#!/usr/bin/env python3
"""Gate 2 extension (S87 WS2.3): every .claude/skills/*/SKILL.md must have a real body.

WHY THIS EXISTS. ADR-028's original gate 2 checked that each emitted skill carried a
`name:` key. A 448-byte file with correct frontmatter and an empty body passes that,
so a skill that relocated zero lines was indistinguishable from one that relocated all
of them (TD-S86-NEW-8). This gate tests the CONTENT, not the envelope.

WHAT WOULD MAKE IT FAIL (Rule 0). A SKILL.md whose text after the YAML frontmatter is
shorter than THRESHOLD bytes. The negative control below is the old 95-byte doc-close
shell: if this script does not FAIL on that blob, the gate proves nothing and must not
be trusted. The caller asserts the DIRECTION; this script never inverts an exit code
for convenience.

THE QUANTITY IS THE BODY, NOT THE FILE. The old shell was 448 B total but only 95 B
body -- 79 % of it was the frontmatter `description:`. A gate on total bytes would be
measuring the description, which is the same mistake in a new unit.

THRESHOLD DERIVATION, recorded because a round number with no derivation is the S83
defect. 500 B = half the smallest REAL skill body at the time the gate was written
(`merdian-runbooks`, 1026 B), floored to 100 B. Derived from the quantity's scale
BEFORE the new doc-close body existed, so the bar was not fitted to it.

SCOPE. `.claude/skills/*/SKILL.md` only. It is deliberately NOT applied to
`.claude/rules/*.md`: `pine.md` is 454 B total and would fail, and a gate silently
inherited by rules would fire on a file nobody is fixing.

USAGE
  check_skill_bodies.py                      gate the working tree
  check_skill_bodies.py --ref <git-ref>      gate every skill in that ref
  check_skill_bodies.py --blob <ref>:<path>  gate ONE blob (the negative control)
  check_skill_bodies.py --headings <path>    print a skill's headings (WS2.4 read)

Exit 0 = PASS (every skill at or above the bar), 1 = FAIL, 2 = harness error.
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/ssm-user/meridian-cc")
THRESHOLD = 500
SMALLEST_REAL_AT_WRITE = 1026   # merdian-runbooks body, S87; the derivation's input


def git(*a):
    r = subprocess.run(["git", "-C", str(REPO), *a], capture_output=True)
    if r.returncode != 0:
        print(f"HARNESS ERROR: git {' '.join(a)}: {r.stderr.decode()[:200]}")
        sys.exit(2)
    return r.stdout


def body_bytes(raw: bytes) -> int:
    """Bytes after the YAML frontmatter, stripped. No frontmatter -> the whole file."""
    parts = raw.split(b"---", 2)
    return len((parts[2] if len(parts) > 2 else raw).strip())


def headings(raw: bytes, limit: int):
    out = []
    for line in raw.decode("utf-8", "replace").splitlines():
        s = line.strip()
        if s.startswith("#") or (s[:2].rstrip(".").isdigit() and s.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."))):
            out.append(s)
        if len(out) >= limit:
            break
    return out


ap = argparse.ArgumentParser()
g = ap.add_mutually_exclusive_group()
g.add_argument("--ref", help="gate every skill in this git ref")
g.add_argument("--blob", help="gate one blob, as <ref>:<path>")
g.add_argument("--headings", help="print this skill's headings instead of gating")
ap.add_argument("--limit", type=int, default=8)
args = ap.parse_args()

if args.headings:
    p = Path(args.headings)
    raw = p.read_bytes() if p.is_absolute() else (REPO / args.headings).read_bytes()
    print(f"headings of {args.headings} (body {body_bytes(raw)} B, max {args.limit} lines)")
    for h in headings(raw, args.limit):
        print(f"  {h}")
    sys.exit(0)

rows = []
if args.blob:
    ref, _, path = args.blob.partition(":")
    rows.append((args.blob, body_bytes(git("show", args.blob))))
    label = f"blob {args.blob}"
elif args.ref:
    names = [n for n in git("ls-tree", "-r", "--name-only", args.ref).decode().splitlines()
             if n.startswith(".claude/skills/") and n.endswith("/SKILL.md")]
    if not names:
        print(f"HARNESS ERROR: no .claude/skills/*/SKILL.md in {args.ref} -- a gate over "
              f"an empty set passes vacuously and would prove nothing")
        sys.exit(2)
    rows = [(n, body_bytes(git("show", f"{args.ref}:{n}"))) for n in sorted(names)]
    label = f"ref {args.ref}"
else:
    paths = sorted((REPO / ".claude/skills").glob("*/SKILL.md"))
    if not paths:
        print("HARNESS ERROR: no .claude/skills/*/SKILL.md in the working tree")
        sys.exit(2)
    rows = [(str(p.relative_to(REPO)), body_bytes(p.read_bytes())) for p in paths]
    label = "working tree"

print(f"gate 2 — SKILL.md body >= {THRESHOLD} B   ({label})")
print(f"  threshold = half the smallest real skill body at write time "
      f"({SMALLEST_REAL_AT_WRITE} B), floored to 100")
fails = 0
for name, n in rows:
    ok = n >= THRESHOLD
    fails += not ok
    extra = "" if ok else (f"   ({THRESHOLD / n:.1f}x under)" if n else "   (empty body)")
    print(f"  {'PASS' if ok else 'FAIL'}  {n:6d} B body  {name}{extra}")

print(f"{len(rows)} skill(s) checked, {fails} below the bar -> "
      f"{'PASS' if fails == 0 else 'FAIL'}")
sys.exit(0 if fails == 0 else 1)
