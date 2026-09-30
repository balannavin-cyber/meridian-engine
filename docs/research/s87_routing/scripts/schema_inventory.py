#!/usr/bin/env python3
"""
WS3.1 phase A - schema inventory of Claude Code transcripts.
Measurement only. Emits key names, type/subtype values and counts.
The ONLY free text emitted is the first-60-char prefix of tool_result
error payloads (step 6), as explicitly permitted by the task spec.
No .env file is read or touched.
"""
import json
import os
import sys
import glob
import hashlib
from collections import Counter, defaultdict

PROJECT_DIRS = [
    "/home/ssm-user/.claude/projects/-home-ssm-user-meridian-engine/",
    "/home/ssm-user/.claude/projects/-home-ssm-user-meridian-cc/",
]
# S87_ROOTS (colon-separated) overrides the list above; absent, the list stands.
if os.environ.get("S87_ROOTS"):
    PROJECT_DIRS = [d if d.endswith("/") else d + "/"
                    for d in os.environ["S87_ROOTS"].split(":") if d]
# S87_OUTDIR redirects this run's report so a snapshot run does not overwrite the
# original. Needed because the phase B script must parse THIS run's report.
OUT_MD = os.path.join(os.environ.get("S87_OUTDIR", "/home/ssm-user/s87_measure"),
                      "schema_inventory.md")
S86_ROOT = "/home/ssm-user/s86_test/"

MARKER_SUBSTRINGS = ("compact", "summary", "context")

out = []


def w(s=""):
    out.append(s)


def walk_keys(obj, sink):
    """Recursively collect every dict key name."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            sink[k] += 1
            walk_keys(v, sink)
    elif isinstance(obj, list):
        for v in obj:
            walk_keys(v, sink)


def content_blocks(msg):
    if not isinstance(msg, dict):
        return []
    c = msg.get("content")
    if isinstance(c, list):
        return [b for b in c if isinstance(b, dict)]
    return []


def flatten_text(x):
    """Reduce an arbitrary tool_result content payload to a single string."""
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        parts = []
        for b in x:
            if isinstance(b, dict):
                if isinstance(b.get("text"), str):
                    parts.append(b["text"])
                else:
                    parts.append(json.dumps(b, sort_keys=True))
            else:
                parts.append(str(b))
        return " ".join(parts)
    if isinstance(x, dict):
        if isinstance(x.get("text"), str):
            return x["text"]
        return json.dumps(x, sort_keys=True)
    return str(x)


def inventory_project(pdir):
    files = sorted(glob.glob(os.path.join(pdir, "**", "*.jsonl"), recursive=True))
    total_bytes = sum(os.path.getsize(f) for f in files)
    total_lines = 0
    parse_fail = 0

    type_counts = Counter()
    type_keys = defaultdict(set)
    assistant_msg_keys = set()
    assistant_usage_keys = set()
    subtype_by_type = defaultdict(Counter)

    all_key_names = Counter()

    asst_lines = 0
    msg_ids = Counter()
    id_req_pairs = set()
    usage_by_id = defaultdict(set)      # message.id -> set of canonical usage json
    usage_lines_by_id = Counter()

    tool_use_counts = Counter()
    err_prefixes = Counter()
    tool_result_total = 0
    tool_result_err = 0

    timestamps = []
    session_ids = set()

    for f in files:
        with open(f, "r", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                total_lines += 1
                try:
                    o = json.loads(line)
                except Exception:
                    parse_fail += 1
                    continue
                if not isinstance(o, dict):
                    parse_fail += 1
                    continue

                walk_keys(o, all_key_names)

                t = o.get("type")
                tname = t if isinstance(t, str) else "<non-str:%s>" % type(t).__name__
                type_counts[tname] += 1
                type_keys[tname].update(k for k in o.keys())

                st = o.get("subtype")
                if isinstance(st, str):
                    subtype_by_type[tname][st] += 1

                ts = o.get("timestamp")
                if isinstance(ts, str):
                    timestamps.append(ts)
                sid = o.get("sessionId") or o.get("session_id")
                if isinstance(sid, str):
                    session_ids.add(sid)

                msg = o.get("message")

                if tname == "assistant":
                    asst_lines += 1
                    if isinstance(msg, dict):
                        assistant_msg_keys.update(msg.keys())
                        u = msg.get("usage")
                        if isinstance(u, dict):
                            assistant_usage_keys.update(u.keys())
                        mid = msg.get("id")
                        if isinstance(mid, str):
                            msg_ids[mid] += 1
                            id_req_pairs.add((mid, o.get("requestId")))
                            if isinstance(u, dict):
                                usage_by_id[mid].add(
                                    json.dumps(u, sort_keys=True, default=str))
                                usage_lines_by_id[mid] += 1

                # tool_use / tool_result scan over assistant + user content blocks
                for b in content_blocks(msg):
                    bt = b.get("type")
                    if bt == "tool_use":
                        nm = b.get("name")
                        tool_use_counts[nm if isinstance(nm, str) else "<unnamed>"] += 1
                    elif bt == "tool_result":
                        tool_result_total += 1
                        if b.get("is_error") is True:
                            tool_result_err += 1
                            txt = flatten_text(b.get("content"))
                            txt = " ".join(txt.split())
                            err_prefixes[txt[:60]] += 1

    return dict(
        pdir=pdir, files=files, total_bytes=total_bytes, total_lines=total_lines,
        parse_fail=parse_fail, type_counts=type_counts, type_keys=type_keys,
        subtype_by_type=subtype_by_type,
        assistant_msg_keys=assistant_msg_keys,
        assistant_usage_keys=assistant_usage_keys,
        all_key_names=all_key_names, asst_lines=asst_lines, msg_ids=msg_ids,
        id_req_pairs=id_req_pairs, usage_by_id=usage_by_id,
        usage_lines_by_id=usage_lines_by_id,
        tool_use_counts=tool_use_counts, err_prefixes=err_prefixes,
        tool_result_total=tool_result_total, tool_result_err=tool_result_err,
        timestamps=timestamps, session_ids=session_ids,
    )


def render_project(r):
    w("## Project dir: `%s`" % r["pdir"])
    w()
    w("### 1. Files / bytes / lines / parse failures")
    w()
    w("| metric | value |")
    w("|---|---|")
    w("| JSONL files (recursive) | %d |" % len(r["files"]))
    w("| total bytes | %d |" % r["total_bytes"])
    w("| total non-blank lines | %d |" % r["total_lines"])
    w("| JSON parse failures | %d |" % r["parse_fail"])
    w()

    w("### 2. Top-level `type` counts")
    w()
    w("| type | count |")
    w("|---|---|")
    for k, v in r["type_counts"].most_common():
        w("| `%s` | %d |" % (k, v))
    w()

    w("### 3. Key sets per type")
    w()
    for k, _ in r["type_counts"].most_common():
        keys = sorted(r["type_keys"][k])
        w("- **`%s`** (%d lines) top-level keys: %s" %
          (k, r["type_counts"][k], ", ".join("`%s`" % x for x in keys)))
        if r["subtype_by_type"].get(k):
            w("  - `subtype` values: %s" % ", ".join(
                "`%s`=%d" % (s, c) for s, c in r["subtype_by_type"][k].most_common()))
    w()
    w("- **assistant `message` keys**: %s" %
      ", ".join("`%s`" % x for x in sorted(r["assistant_msg_keys"])))
    w("- **assistant `message.usage` keys**: %s" %
      ", ".join("`%s`" % x for x in sorted(r["assistant_usage_keys"])))
    w()

    w("### 4. Duplication check (assistant lines)")
    w()
    n_ids = len(r["msg_ids"])
    n_pairs = len(r["id_req_pairs"])
    dup_ids = {k: v for k, v in r["msg_ids"].items() if v > 1}
    w("| metric | value |")
    w("|---|---|")
    w("| assistant lines | %d |" % r["asst_lines"])
    w("| unique `message.id` | %d |" % n_ids)
    w("| unique (`message.id`, `requestId`) | %d |" % n_pairs)
    w("| `message.id` values appearing on >1 line | %d |" % len(dup_ids))
    if dup_ids:
        w("| max lines sharing one `message.id` | %d |" % max(dup_ids.values()))
        w("| assistant lines belonging to a repeated id | %d |" % sum(dup_ids.values()))
    w()
    # usage identity across repeated ids
    same = 0
    diff = 0
    for mid, cnt in dup_ids.items():
        variants = r["usage_by_id"].get(mid, set())
        if len(variants) <= 1:
            same += 1
        else:
            diff += 1
    if not dup_ids:
        w("**Usage repetition verdict:** no `message.id` appears on more than one "
          "assistant line, so no usage block is repeated. Summing `usage` over "
          "assistant lines cannot double-count via repeated ids in this corpus.")
    else:
        w("**Usage repetition verdict:** of the %d repeated `message.id` values, "
          "**%d have a byte-identical `usage` object on every line that shares the id** "
          "and **%d differ across lines**. Where usage is identical and repeated, a naive "
          "per-line sum of `usage` over-counts those tokens; a token sum must be taken "
          "over unique `message.id` (or unique (`message.id`,`requestId`)), not per line."
          % (len(dup_ids), same, diff))
    w()

    w("### 5. Keys / type / subtype values matching compact|summary|context")
    w()
    w("Key names (any nesting depth), name and occurrence count:")
    w()
    hits = [(k, v) for k, v in r["all_key_names"].items()
            if any(m in k.lower() for m in MARKER_SUBSTRINGS)]
    hits.sort(key=lambda x: (-x[1], x[0]))
    if hits:
        w("| key name | occurrences |")
        w("|---|---|")
        for k, v in hits:
            w("| `%s` | %d |" % (k, v))
    else:
        w("_none_")
    w()
    w("`type` / `subtype` values matching:")
    w()
    tv = [(k, v) for k, v in r["type_counts"].items()
          if any(m in k.lower() for m in MARKER_SUBSTRINGS)]
    sv = []
    for t, c in r["subtype_by_type"].items():
        for s, n in c.items():
            if any(m in s.lower() for m in MARKER_SUBSTRINGS):
                sv.append(("%s/%s" % (t, s), n))
    if tv or sv:
        w("| field | value | count |")
        w("|---|---|---|")
        for k, v in sorted(tv, key=lambda x: -x[1]):
            w("| `type` | `%s` | %d |" % (k, v))
        for k, v in sorted(sv, key=lambda x: -x[1]):
            w("| `type`/`subtype` | `%s` | %d |" % (k, v))
    else:
        w("_none_")
    w()

    w("### 6. Tool use and tool_result errors")
    w()
    w("| tool name | tool_use blocks |")
    w("|---|---|")
    for k, v in r["tool_use_counts"].most_common():
        w("| `%s` | %d |" % (k, v))
    w("| **total** | **%d** |" % sum(r["tool_use_counts"].values()))
    w()
    w("tool_result blocks: %d total, %d with `is_error=true` (%.1f%%)." % (
        r["tool_result_total"], r["tool_result_err"],
        (100.0 * r["tool_result_err"] / r["tool_result_total"])
        if r["tool_result_total"] else 0.0))
    w()
    w("Top 15 distinct first-60-char error prefixes:")
    w()
    if r["err_prefixes"]:
        w("| count | prefix (first 60 chars) |")
        w("|---|---|")
        for k, v in r["err_prefixes"].most_common(15):
            w("| %d | `%s` |" % (v, k.replace("|", "\\|").replace("`", "'")))
        w()
        w("(distinct error prefixes total: %d)" % len(r["err_prefixes"]))
    else:
        w("_no tool_result blocks with is_error=true_")
    w()

    w("### 7. Timestamps and sessions")
    w()
    ts = sorted(r["timestamps"])
    w("| metric | value |")
    w("|---|---|")
    w("| lines carrying a `timestamp` | %d |" % len(ts))
    w("| earliest timestamp | %s |" % (ts[0] if ts else "n/a"))
    w("| latest timestamp | %s |" % (ts[-1] if ts else "n/a"))
    w("| distinct `sessionId`/`session_id` values | %d |" % len(r["session_ids"]))
    w()


def inventory_s86():
    files = sorted(glob.glob(os.path.join(S86_ROOT, "**", "*.json"), recursive=True))
    w("## s86_test result JSONs")
    w()
    w("Root: `%s` — %d `.json` files, %d bytes total." %
      (S86_ROOT, len(files), sum(os.path.getsize(f) for f in files)))
    w()
    topkeys = Counter()
    usage_keys = Counter()
    modelusage_outer = Counter()
    modelusage_inner = Counter()
    fail = 0
    fail_names = []
    nfiles_ok = 0
    per_subdir = Counter()
    for f in files:
        per_subdir[os.path.dirname(f)] += 1
        try:
            o = json.load(open(f, "r", errors="replace"))
        except Exception as e:
            fail += 1
            fail_names.append((f, "parse error: " + type(e).__name__))
            continue
        if not isinstance(o, dict):
            fail += 1
            fail_names.append((f, "top-level JSON is a %s, not an object" % type(o).__name__))
            continue
        nfiles_ok += 1
        for k in o.keys():
            topkeys[k] += 1
        u = o.get("usage")
        if isinstance(u, dict):
            for k in u.keys():
                usage_keys[k] += 1
        mu = o.get("modelUsage")
        if isinstance(mu, dict):
            for k, v in mu.items():
                modelusage_outer[k] += 1
                if isinstance(v, dict):
                    for ik in v.keys():
                        modelusage_inner[ik] += 1
    w("| metric | value |")
    w("|---|---|")
    w("| files parsed OK | %d |" % nfiles_ok)
    w("| parse failures / non-object | %d |" % fail)
    w()
    if fail_names:
        w("Files not counted as result objects:")
        w()
        for fn, why in fail_names:
            w("- `%s` — %s" % (fn, why))
        w()
    w("Files per sub-directory:")
    w()
    w("| dir | files |")
    w("|---|---|")
    for k, v in sorted(per_subdir.items()):
        w("| `%s` | %d |" % (k, v))
    w()
    w("### Top-level key set")
    w()
    w("| key | files containing it |")
    w("|---|---|")
    for k, v in sorted(topkeys.items(), key=lambda x: (-x[1], x[0])):
        w("| `%s` | %d |" % (k, v))
    w()
    w("### Keys under `usage`")
    w()
    w("| key | files |")
    w("|---|---|")
    for k, v in sorted(usage_keys.items(), key=lambda x: (-x[1], x[0])):
        w("| `%s` | %d |" % (k, v))
    w()
    w("### Keys under `modelUsage`")
    w()
    w("`modelUsage` is keyed by model id; the inner objects carry the per-model counters.")
    w()
    w("| modelUsage outer key (model id) | files |")
    w("|---|---|")
    for k, v in sorted(modelusage_outer.items(), key=lambda x: (-x[1], x[0])):
        w("| `%s` | %d |" % (k, v))
    w()
    w("| modelUsage inner key | occurrences |")
    w("|---|---|")
    for k, v in sorted(modelusage_inner.items(), key=lambda x: (-x[1], x[0])):
        w("| `%s` | %d |" % (k, v))
    w()


def main():
    me = os.path.abspath(__file__)
    digest = hashlib.sha256(open(me, "rb").read()).hexdigest()
    w("# WS3.1 phase A — schema inventory of Claude Code transcripts")
    w()
    w("Measurement only. No ADR text, no interpretation beyond what the counts state.")
    w()
    w("- script: `%s`" % me)
    w("- `sha256sum`: `%s  %s`" % (digest, me))
    w("- generated by: `python3 %s`" % me)
    w()
    w("---")
    w()
    results = []
    for p in PROJECT_DIRS:
        if not os.path.isdir(p):
            w("## Project dir: `%s`" % p)
            w()
            w("_directory does not exist_")
            w()
            continue
        r = inventory_project(p)
        results.append(r)
        render_project(r)
        w("---")
        w()
    inventory_s86()
    w("---")
    w()
    w("_End of inventory._")

    dest = OUT_MD
    with open(dest, "w") as fh:
        fh.write("\n".join(out) + "\n")
    sys.stderr.write("wrote %s (%d bytes)\n" % (dest, os.path.getsize(dest)))


if __name__ == "__main__":
    main()
