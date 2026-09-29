"""S85 measure-only: map Claude Code transcripts to MERDIAN sessions by content.

Read-only. Scans ~/.claude/projects/*/*.jsonl and reports, per file:
slug, id prefix, bytes, line count, first/last entry timestamp, and counts of
session markers (S75..S89 / "Session NN") so files can be attributed to
sessions independently of mtime.
"""
import collections
import glob
import json
import os
import re

MARKER_BARE = re.compile(r"\bS(7[5-9]|8[0-9])\b")
MARKER_LONG = re.compile(r"Session (7[5-9]|8[0-9])\b")

rows = []
for d in sorted(glob.glob("/home/ssm-user/.claude/projects/*/")):
    slug = os.path.basename(d.rstrip("/"))
    for f in sorted(glob.glob(d + "*.jsonl")):
        first = last = None
        n = 0
        hits = collections.Counter()
        kinds = collections.Counter()
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    n += 1
                    try:
                        o = json.loads(line)
                    except Exception:
                        o = {}
                    ts = o.get("timestamp")
                    if ts:
                        if first is None:
                            first = ts
                        last = ts
                    if o.get("type"):
                        kinds[o["type"]] += 1
                    for m in MARKER_BARE.findall(line):
                        hits["S" + m] += 1
                    for m in MARKER_LONG.findall(line):
                        hits["S" + m] += 1
        except Exception as e:  # pragma: no cover - diagnostic only
            first = "ERR " + str(e)
        top = ", ".join(f"{k}:{v}" for k, v in hits.most_common(4))
        rows.append(
            (slug, os.path.basename(f)[:8], os.path.getsize(f), n,
             (first or "")[:16], (last or "")[:16], top, dict(kinds))
        )

rows.sort(key=lambda r: (r[4] or ""))
hdr = (f"{'slug':24} {'file':9} {'bytes':>9} {'lines':>6} "
       f"{'first_ts':17} {'last_ts':17} session-marker counts")
print(hdr)
print("-" * len(hdr))
for r in rows:
    print(f"{r[0][-24:]:24} {r[1]:9} {r[2]:>9} {r[3]:>6} {r[4]:17} {r[5]:17} {r[6]}")

print()
print("TOTAL files:", len(rows),
      " bytes:", sum(r[2] for r in rows),
      " lines:", sum(r[3] for r in rows))
print("entry types seen:", dict(collections.Counter(
    k for r in rows for k in r[7])))
