#!/usr/bin/env python3
"""
WS3.1 phase B - baseline metrics over Claude Code transcripts.

Measurement only. Emits counts, key names, enum values and numeric totals.
The ONLY free text emitted from transcript data is the denial-prefix set in B4,
as explicitly permitted by the task spec. Synthetic fixture strings (written by
this script) are printed in the B0 control section; they are not transcript data.
No .env file is read or touched.

Outputs:
  /home/ssm-user/s87_measure/baseline_b.md
  /home/ssm-user/s87_measure/sessions.csv
Fixtures written to:
  /home/ssm-user/s87_measure/fixtures/
"""
import json
import os
import re
import sys
import csv
import glob
import hashlib
from collections import Counter, defaultdict

SCRATCH = "/home/ssm-user/s87_measure"
FIXTURES = os.path.join(SCRATCH, "fixtures")
MD = os.path.join(SCRATCH, "baseline_b.md")
CSV_PATH = os.path.join(SCRATCH, "sessions.csv")
PHASE_A_MD = os.path.join(SCRATCH, "schema_inventory.md")

PROJECT_DIRS = [
    "/home/ssm-user/.claude/projects/-home-ssm-user-meridian-engine/",
    "/home/ssm-user/.claude/projects/-home-ssm-user-meridian-cc/",
]
# S87_ROOTS (colon-separated) overrides the list above; absent, the list stands.
if os.environ.get("S87_ROOTS"):
    PROJECT_DIRS = [d if d.endswith("/") else d + "/"
                    for d in os.environ["S87_ROOTS"].split(":") if d]
# S87_OUTDIR redirects this run's outputs AND the phase A report it reads, so a
# snapshot run parses the snapshot's own phase A output rather than the original.
if os.environ.get("S87_OUTDIR"):
    _OD = os.environ["S87_OUTDIR"]
    MD = os.path.join(_OD, "baseline_b.md")
    CSV_PATH = os.path.join(_OD, "sessions.csv")
    PHASE_A_MD = os.path.join(_OD, "schema_inventory.md")
S86_ROOT = "/home/ssm-user/s86_test/"

FIELDS = ["input_tokens", "cache_creation_input_tokens",
          "cache_read_input_tokens", "output_tokens"]
FIELD_LABEL = {
    "input_tokens": "input",
    "cache_creation_input_tokens": "cache_creation_input",
    "cache_read_input_tokens": "cache_read_input",
    "output_tokens": "output",
}

# Phase A denial prefixes. B4 is permitted to print these and nothing else.
DENIAL_PREFIXES = (
    "The user doesn't want to proceed with this tool use",
    "Permission to use",
    "Permission for this tool use was denied",
    "<tool_use_error>File is in a directory that is denied",
)

MARKER_B5 = ("permission", "approv", "prompt")
# A key name shaped like a per-call APPROVAL record. Deliberately lexical, and
# labelled as such wherever its result is used.
APPROVAL_NAME_RE = re.compile(r"approv|allowed|granted|accepted|consent", re.I)
# A key name shaped like session-level MODE state rather than a per-call event.
MODE_NAME_RE = re.compile(r"mode$|mode[A-Z_]", re.I)

CONTENT_PATH_PREFIX = "$.message.content"

out = []


def w(s=""):
    out.append(s)


# ----------------------------------------------------------------------------
# shared primitives
# ----------------------------------------------------------------------------

def classify_command(cmd):
    """Leading-form classification of a Bash command string.

    Returns (form, is_bare_cd). The leading token decides.
    """
    if not isinstance(cmd, str):
        return "other", False
    s = cmd.lstrip()
    if re.match(r"^cd(\s|$)", s):
        amp = s.find("&&")
        semi = s.find(";")
        if amp == -1 and semi == -1:
            return "cd-compound", True          # bare cd, no separator
        if semi == -1 or (amp != -1 and amp < semi):
            return "cd-compound", False
        return "cd-semicolon", False
    if re.match(r"^git\s+-C(\s|$)", s):
        return "git -C", False
    if re.match(r"^git(\s|$)", s):
        return "bare git", False
    if re.match(r"^(python3?|py)(\s|$)", s) or "<<" in s.split("\n")[0]:
        return "python3/heredoc", False
    return "other", False


def usage_of(o):
    m = o.get("message")
    if not isinstance(m, dict):
        return None, None, None
    u = m.get("usage")
    if not isinstance(u, dict):
        return None, m.get("id"), m.get("model")
    return u, m.get("id"), m.get("model")


def num(u, k):
    v = u.get(k)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


def content_blocks(msg):
    if not isinstance(msg, dict):
        return []
    c = msg.get("content")
    return [b for b in c if isinstance(b, dict)] if isinstance(c, list) else []


def flatten_text(x):
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        parts = []
        for b in x:
            if isinstance(b, dict):
                parts.append(b["text"] if isinstance(b.get("text"), str)
                             else json.dumps(b, sort_keys=True))
            else:
                parts.append(str(b))
        return " ".join(parts)
    if isinstance(x, dict):
        return x["text"] if isinstance(x.get("text"), str) \
            else json.dumps(x, sort_keys=True)
    return str(x)


def walk_keys(obj, sink, skipped, in_schema=False, under_is=False):
    """Collect key names, skipping JSON-schema subtrees.

    Structural rule, applied to the PATH and never to a key name: a dict reached
    via a key named "properties" is a schema subtree when its parent dict also
    carries "type", or when it sits anywhere under a key named "input_schema".
    Everything below such a dict is skipped and counted.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if in_schema:
                skipped[0] += 1
            else:
                sink[k] += 1
            child_us = under_is or (k == "input_schema")
            child_schema = in_schema or (
                k == "properties" and ("type" in obj or under_is))
            walk_keys(v, sink, skipped, child_schema, child_us)
    elif isinstance(obj, list):
        for v in obj:
            walk_keys(v, sink, skipped, in_schema, under_is)


def walk_string_paths(obj, pattern, sink, excluded_counter, path="$"):
    """Record KEY PATHS (never values) whose string value matches pattern.

    Paths under $.message.content are conversation text; this project discusses
    "context window" constantly, so those matches are counted separately and
    kept out of the reported path table.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk_string_paths(v, pattern, sink, excluded_counter, path + "." + k)
    elif isinstance(obj, list):
        for v in obj:
            walk_string_paths(v, pattern, sink, excluded_counter, path + "[]")
    elif isinstance(obj, str):
        if pattern.search(obj):
            if path.startswith(CONTENT_PATH_PREFIX):
                excluded_counter[0] += 1
            else:
                sink[path] += 1


# ----------------------------------------------------------------------------
# core collector - used for BOTH fixtures and real projects
# ----------------------------------------------------------------------------

def collect(files):
    """Walk jsonl files in the given (already ordered) list.

    Dedup key: message.id when present, else a synthetic per-line key.
    Primary rule: LAST line in file order wins, per id.
    Sensitivity rule: per-field MAX across lines sharing the id.
    """
    recs = {}            # key -> record dict
    order = 0
    no_id_with_usage = 0
    asst_lines = 0
    asst_lines_with_usage = 0
    asst_ids_any = set()          # message.id on ANY assistant line (phase A's rule)
    lines_per_id = Counter()

    compact_boundary = Counter()   # session -> n
    session_first_ts = {}
    session_last_ts = {}

    tool_use = {}        # tool_use_id -> (tool_name, command, session)
    tool_res = {}        # tool_use_id -> (is_error, text)
    tool_res_parent_keys = {}   # tool_use_id -> frozenset of parent line top-level keys
    all_keys = Counter()
    schema_keys_skipped = [0]
    marker_events = []
    last_resp_key = [None]
    type_counts = Counter()
    subtype_counts = Counter()
    ctx_paths = Counter()
    ctx_excluded = [0]
    ctx_re = re.compile(
        r"context[ _\-]?(limit|window|low|exceed|overflow|full)|"
        r"exceed.{0,20}context|too (long|large).{0,20}context|"
        r"prompt is too long|max_tokens|output limit", re.I)

    stop_reasons = Counter()
    stop_reasons_by_session = defaultdict(Counter)
    api_error_lines = Counter()
    truncated_lines = Counter()
    error_key_lines = Counter()

    for fpath in files:
        # A marker on a file's first lines must not inherit the previous file's
        # response: that is a different session, and its context could wrongly
        # push the event over the pre-registered bar.
        last_resp_key[0] = None
        with open(fpath, "r", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if not isinstance(o, dict):
                    continue
                order += 1
                walk_keys(o, all_keys, schema_keys_skipped)
                t = o.get("type")
                type_counts[t if isinstance(t, str) else "<non-str>"] += 1
                st = o.get("subtype")
                if isinstance(st, str):
                    subtype_counts["%s/%s" % (t, st)] += 1

                sid = o.get("sessionId") or o.get("session_id") or "<none>"
                ts = o.get("timestamp")
                if isinstance(ts, str):
                    if sid not in session_first_ts or ts < session_first_ts[sid]:
                        session_first_ts[sid] = ts
                    if sid not in session_last_ts or ts > session_last_ts[sid]:
                        session_last_ts[sid] = ts

                if t == "system" and st == "compact_boundary":
                    compact_boundary[sid] += 1
                    marker_events.append(dict(
                        session=sid, ts=ts, marker="compact_boundary", src=(fpath, lineno),
                        err=None, prev_key=last_resp_key[0]))

                walk_string_paths(o, ctx_re, ctx_paths, ctx_excluded)

                msg = o.get("message")

                if t == "assistant":
                    asst_lines += 1
                    u, mid, model = usage_of(o)
                    if isinstance(mid, str) and mid:
                        asst_ids_any.add(mid)
                    if isinstance(msg, dict):
                        sr = msg.get("stop_reason")
                        if isinstance(sr, str):
                            stop_reasons[sr] += 1
                            stop_reasons_by_session[sid][sr] += 1
                        elif sr is None and "stop_reason" in msg:
                            stop_reasons["<null>"] += 1
                            stop_reasons_by_session[sid]["<null>"] += 1
                    if o.get("isApiErrorMessage") is True:
                        api_error_lines[sid] += 1
                        marker_events.append(dict(
                            session=sid, ts=ts, marker="isApiErrorMessage", src=(fpath, lineno),
                            err=o.get("error"), prev_key=last_resp_key[0]))
                    if o.get("truncatedAfterOutput"):
                        truncated_lines[sid] += 1
                        marker_events.append(dict(
                            session=sid, ts=ts, marker="truncatedAfterOutput", src=(fpath, lineno),
                            err=o.get("error"), prev_key=last_resp_key[0]))
                    if o.get("error") not in (None, "", {}, [], False):
                        error_key_lines[sid] += 1
                        marker_events.append(dict(
                            session=sid, ts=ts, marker="error", src=(fpath, lineno),
                            err=o.get("error"), prev_key=last_resp_key[0]))

                    if u is not None:
                        asst_lines_with_usage += 1
                        if isinstance(mid, str) and mid:
                            key = ("id", mid)
                        else:
                            key = ("noid", fpath, order)
                            no_id_with_usage += 1
                        lines_per_id[key] += 1
                        last_resp_key[0] = key
                        r = recs.get(key)
                        if r is None:
                            r = {
                                "session": sid, "model": model, "order": order,
                                "sidechain": bool(o.get("isSidechain")),
                                "agent": o.get("agentId"),
                                "primary": {f: num(u, f) for f in FIELDS},
                                "maxv": {f: num(u, f) for f in FIELDS},
                                "lines": 1,
                                "ts": ts if isinstance(ts, str) else None,
                            }
                            recs[key] = r
                        else:
                            r["lines"] += 1
                            if order >= r["order"]:
                                r["order"] = order
                                r["session"] = sid
                                r["model"] = model
                                r["sidechain"] = bool(o.get("isSidechain"))
                                r["agent"] = o.get("agentId")
                                if isinstance(ts, str):
                                    r["ts"] = ts
                                for f in FIELDS:
                                    r["primary"][f] = num(u, f)
                            for f in FIELDS:
                                if num(u, f) > r["maxv"][f]:
                                    r["maxv"][f] = num(u, f)

                # tool_use / tool_result index
                for b in content_blocks(msg):
                    bt = b.get("type")
                    if bt == "tool_use":
                        tool_use[b.get("id")] = (
                            b.get("name"),
                            (b.get("input") or {}).get("command")
                            if isinstance(b.get("input"), dict) else None,
                            sid)
                    elif bt == "tool_result":
                        tuid = b.get("tool_use_id")
                        tool_res[tuid] = (b.get("is_error") is True,
                                          flatten_text(b.get("content")))
                        tool_res_parent_keys[tuid] = frozenset(o.keys())

    return dict(
        recs=recs, no_id_with_usage=no_id_with_usage, asst_lines=asst_lines,
        asst_lines_with_usage=asst_lines_with_usage, lines_per_id=lines_per_id,
        asst_ids_any=asst_ids_any,
        compact_boundary=compact_boundary,
        session_first_ts=session_first_ts, session_last_ts=session_last_ts,
        tool_use=tool_use, tool_res=tool_res,
        tool_res_parent_keys=tool_res_parent_keys, all_keys=all_keys,
        type_counts=type_counts, subtype_counts=subtype_counts,
        ctx_paths=ctx_paths, ctx_excluded=ctx_excluded[0],
        schema_keys_skipped=schema_keys_skipped[0], marker_events=marker_events,
        stop_reasons=stop_reasons,
        stop_reasons_by_session=stop_reasons_by_session,
        api_error_lines=api_error_lines, truncated_lines=truncated_lines,
        error_key_lines=error_key_lines,
    )


CTX_CODE_RE = re.compile(r"context|length", re.I)


def render_err(err):
    """Return (display, code). `code` is the only thing the pre-registered
    reading is allowed to look at. Anything else is redacted to a length."""
    if err is None:
        return "-", None
    if isinstance(err, str):
        if len(err) <= 40 and " " not in err:
            return "`%s`" % err, err
        return "<redacted, %d chars>" % len(err), None
    if isinstance(err, dict):
        cands = []
        for k in ("type", "code"):
            cands.append((k, err.get(k)))
        sub = err.get("error")
        if isinstance(sub, dict):
            for k in ("type", "code"):
                cands.append(("error." + k, sub.get(k)))
        for k, v in cands:
            if isinstance(v, str) and v:
                return "`%s=%s`" % (k, v), v
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return "`%s=%s`" % (k, v), str(v)
        return ("<redacted, %d chars>"
                % len(json.dumps(err, sort_keys=True, default=str)), None)
    return ("<redacted, %d chars>"
            % len(json.dumps(err, sort_keys=True, default=str)), None)


def n_noid_records(recs):
    return sum(1 for k in recs if k[0] == "noid")


# ----------------------------------------------------------------------------
# phase A reference numbers - PARSED, never typed in
# ----------------------------------------------------------------------------

def parse_phase_a_unique_ids(path):
    """Return {project_dir: unique_message_id_count} parsed from phase A's report.

    The numbers are NOT written into this script; they are read from the
    artefact phase A produced, so this check is against an independent run.
    """
    if not os.path.exists(path):
        return None, "phase A report not found at %s" % path
    txt = open(path, "r", errors="replace").read()
    out_map = {}
    chunks = txt.split("## Project dir: ")
    for ch in chunks[1:]:
        m_dir = re.match(r"`([^`]+)`", ch.strip())
        if not m_dir:
            continue
        pdir = m_dir.group(1)
        m_n = re.search(r"\|\s*unique\s*`message\.id`\s*\|\s*(\d+)\s*\|", ch)
        if m_n:
            out_map[pdir] = int(m_n.group(1))
    if not out_map:
        return None, "no `unique message.id` rows found in %s" % path
    return out_map, "parsed %d project(s) from %s" % (len(out_map), path)


def crosscheck_against_phase_a(recs, asst_ids_any, phase_a_n):
    """deduped responses - no-id records  ==  phase A's unique message.id count."""
    deduped = len(recs)
    noid = n_noid_records(recs)
    ours = deduped - noid
    ok = (ours == phase_a_n)
    detail = ("deduped responses=%d, no-id records=%d, ids with usage=%d, "
              "phase A unique message.id=%d, delta=%+d; "
              "diagnostic: distinct message.id on ANY assistant line (phase A's "
              "rule, usage or not)=%d"
              % (deduped, noid, ours, phase_a_n, ours - phase_a_n, len(asst_ids_any)))
    return ok, detail, ours, noid, deduped


# ----------------------------------------------------------------------------
# B0 controls
# ----------------------------------------------------------------------------

def _fx_line(sid, mid, inp, cc, cr, outp, model="fixture-model",
             ts="2026-01-01T00:00:00.000Z"):
    return json.dumps({
        "type": "assistant", "sessionId": sid, "timestamp": ts,
        "requestId": "req_" + mid,
        "message": {"id": mid, "role": "assistant", "model": model,
                    "content": [], "stop_reason": "end_turn",
                    "usage": {"input_tokens": inp,
                              "cache_creation_input_tokens": cc,
                              "cache_read_input_tokens": cr,
                              "output_tokens": outp}}})


def write_fixtures():
    os.makedirs(FIXTURES, exist_ok=True)

    # C1: same id, identical usage, 3 lines
    p1 = os.path.join(FIXTURES, "c1_dedup.jsonl")
    with open(p1, "w") as fh:
        for _ in range(3):
            fh.write(_fx_line("S_C1", "msg_c1", 100, 0, 0, 7) + "\n")

    # C2: same id, output 5 / 40 / 40 in file order
    p2 = os.path.join(FIXTURES, "c2_stream.jsonl")
    with open(p2, "w") as fh:
        for o in (5, 40, 40):
            fh.write(_fx_line("S_C2", "msg_c2", 10, 0, 0, o) + "\n")

    # C4: two sessions, several ids, for conservation
    p4 = os.path.join(FIXTURES, "c4_conserve.jsonl")
    with open(p4, "w") as fh:
        fh.write(_fx_line("S_A", "m1", 11, 22, 33, 44) + "\n")
        fh.write(_fx_line("S_A", "m1", 11, 22, 33, 44) + "\n")
        fh.write(_fx_line("S_A", "m2", 1, 2, 3, 4) + "\n")
        fh.write(_fx_line("S_B", "m3", 5, 6, 7, 8) + "\n")
        # an assistant line carrying usage but NO message.id
        fh.write(json.dumps({
            "type": "assistant", "sessionId": "S_B",
            "timestamp": "2026-01-01T00:00:00.000Z",
            "message": {"role": "assistant", "model": "fixture-model",
                        "content": [], "usage": {"input_tokens": 9,
                                                 "cache_creation_input_tokens": 0,
                                                 "cache_read_input_tokens": 0,
                                                 "output_tokens": 1}}}) + "\n")

    # C5 negative control for the phase-A cross-check.
    # FULL: 4 distinct ids over 6 lines (n1 appears on 3 lines -> the dedup path
    # is genuinely exercised). SHORT_A drops the sole line carrying n_solo, so
    # the deduped id count falls to 3 while the reference stays 4 -> MISMATCH.
    # SHORT_B drops one DUPLICATE line of n1, which leaves the id count at 4 ->
    # the check still passes, which is the check's known blind spot.
    p5f = os.path.join(FIXTURES, "c5_negctl_full.jsonl")
    p5a = os.path.join(FIXTURES, "c5_negctl_short_dropped_id.jsonl")
    p5b = os.path.join(FIXTURES, "c5_negctl_short_dropped_dup.jsonl")
    full = [
        _fx_line("S_N", "n1", 1, 0, 0, 1),
        _fx_line("S_N", "n1", 1, 0, 0, 2),
        _fx_line("S_N", "n1", 1, 0, 0, 3),
        _fx_line("S_N", "n2", 1, 0, 0, 1),
        _fx_line("S_N", "n3", 1, 0, 0, 1),
        _fx_line("S_N", "n_solo", 1, 0, 0, 1),
    ]
    with open(p5f, "w") as fh:
        fh.write("\n".join(full) + "\n")
    with open(p5a, "w") as fh:                       # drop the n_solo line
        fh.write("\n".join(full[:-1]) + "\n")
    with open(p5b, "w") as fh:                       # drop one duplicate n1 line
        fh.write("\n".join(full[1:]) + "\n")
    # C7: a JSON-schema subtree. approvedX must NOT reach the B5 candidate list.
    p7 = os.path.join(FIXTURES, "c7_schema_subtree.jsonl")
    with open(p7, "w") as fh:
        fh.write(json.dumps({"attachment": {"entries": [
            {"input_schema": {"type": "object",
                              "properties": {"approvedX": {}}}}]}}) + "\n")

    # C8: a top-level DATA key on a user line. It must survive the schema skip.
    p8 = os.path.join(FIXTURES, "c8_real_approval_key.jsonl")
    with open(p8, "w") as fh:
        fh.write(json.dumps({"type": "user", "sessionId": "S_C8",
                             "timestamp": "2026-01-01T00:00:00.000Z",
                             "message": {"role": "user", "content": []},
                             "approvalGranted": True}) + "\n")
    return p1, p2, p4, p5f, p5a, p5b, p7, p8


C3_CASES = [
    ("cd /x && ls", "cd-compound"),
    ("  cd x; ls", "cd-semicolon"),
    ("git -C /x status", "git -C"),
    ("echo 'cd a && b'", "other"),
]


def run_controls(phase_a_map, phase_a_note):
    p1, p2, p4, p5f, p5a, p5b, p7, p8 = write_fixtures()
    results = []

    # ---- C1 dedup ----
    c = collect([p1])
    c1_primary = sum(r["primary"]["input_tokens"] for r in c["recs"].values())
    c1_perline = 100 * 3
    c1_ok = (c1_primary == 100 and c1_primary != c1_perline and len(c["recs"]) == 1)
    results.append(("C1 dedup", c1_ok,
                    "3 lines share msg_c1 (input=100 each). deduped records=%d, "
                    "deduped input sum=%d (a per-line sum would be %d)."
                    % (len(c["recs"]), c1_primary, c1_perline)))

    # ---- C2 streaming ----
    c = collect([p2])
    rec = list(c["recs"].values())[0]
    c2_primary = rec["primary"]["output_tokens"]
    c2_max = rec["maxv"]["output_tokens"]
    c2_perline = 5 + 40 + 40
    c2_ok = (c2_primary == 40 and c2_primary != c2_perline and c2_max == 40)
    results.append(("C2 streaming", c2_ok,
                    "3 lines share msg_c2 (output 5/40/40). last-line-in-file-order "
                    "primary=%d, sensitivity max=%d, per-line sum=%d and is NOT reported."
                    % (c2_primary, c2_max, c2_perline)))

    # ---- C3 cd regex ----
    c3_detail = []
    c3_ok = True
    for cmd, want in C3_CASES:
        got, _bare = classify_command(cmd)
        ok = (got == want)
        c3_ok = c3_ok and ok
        c3_detail.append("%s input=%r -> %s (expected %s)"
                         % ("PASS" if ok else "FAIL", cmd, got, want))
    results.append(("C3 cd regex", c3_ok, " ; ".join(c3_detail)))

    # ---- C4 conservation, on the fixture only ----
    c = collect([p4])
    per_sess = defaultdict(lambda: dict((f, 0) for f in FIELDS))
    tot = dict((f, 0) for f in FIELDS)
    for r in c["recs"].values():
        for f in FIELDS:
            per_sess[r["session"]][f] += r["primary"][f]
            tot[f] += r["primary"][f]
    c4_ok = True
    parts = []
    for f in FIELDS:
        s = sum(per_sess[k][f] for k in per_sess)
        ok = (s == tot[f])
        c4_ok = c4_ok and ok
        parts.append("%s total=%d sum(sessions)=%d %s"
                     % (FIELD_LABEL[f], tot[f], s, "OK" if ok else "MISMATCH"))
    parts.append("usage-bearing lines with no message.id retained: %d"
                 % c["no_id_with_usage"])
    results.append(("C4 conservation (fixture only)", c4_ok, " ; ".join(parts)))

    # ---- C5 negative control for the phase-A cross-check ----
    cf = collect([p5f])
    ref = len(cf["recs"]) - n_noid_records(cf["recs"])          # = 4, computed
    ca = collect([p5a])
    ok_a, det_a, ours_a, _, _ = crosscheck_against_phase_a(
        ca["recs"], ca["asst_ids_any"], ref)
    cb = collect([p5b])
    ok_b, det_b, ours_b, _, _ = crosscheck_against_phase_a(
        cb["recs"], cb["asst_ids_any"], ref)
    # The control PASSES only if the check FAILS on the dropped-id fixture.
    c5_ok = (ok_a is False and ours_a == ref - 1)
    results.append((
        "C5 negative control (cross-check can fail)", c5_ok,
        "reference computed from the full fixture = %d distinct ids over %d lines. "
        "Dropping the sole line of id n_solo gives %d -> check reports %s "
        "(required: MISMATCH). Blind spot, reported not asserted: dropping one "
        "DUPLICATE line of id n1 gives %d -> check reports %s, so this cross-check "
        "cannot detect a lost duplicate line, only a lost id."
        % (ref, len(cf["lines_per_id"]) and sum(cf["lines_per_id"].values()),
           ours_a, "MISMATCH" if not ok_a else "MATCH",
           ours_b, "MATCH" if ok_b else "MISMATCH")))

    # ---- C7 the schema skip works ----
    c7 = collect([p7])
    c7_cand = [k for k in c7["all_keys"]
               if any(m in k.lower() for m in MARKER_B5)
               and APPROVAL_NAME_RE.search(k)]
    c7_ok = ("approvedX" not in c7["all_keys"] and not c7_cand
             and c7["schema_keys_skipped"] >= 1)
    results.append(("C7 schema subtree skipped", c7_ok,
                    "fixture nests approvedX under input_schema.properties. "
                    "approvedX in collected keys: %s ; B5 candidates from this "
                    "fixture: %s ; schema-key occurrences skipped: %d"
                    % ("approvedX" in c7["all_keys"], c7_cand or "none",
                       c7["schema_keys_skipped"])))

    # ---- C8 the skip does not blind the test ----
    c8 = collect([p8])
    c8_cand = [k for k in c8["all_keys"]
               if any(m in k.lower() for m in MARKER_B5)
               and APPROVAL_NAME_RE.search(k)]
    c8_ok = ("approvalGranted" in c8["all_keys"]
             and "approvalGranted" in c8_cand
             and c8["schema_keys_skipped"] == 0)
    results.append(("C8 real approval key survives", c8_ok,
                    "fixture puts approvalGranted at the top level of a user "
                    "line. collected: %s ; B5 candidates: %s ; schema-key "
                    "occurrences skipped: %d"
                    % ("approvalGranted" in c8["all_keys"], c8_cand or "none",
                       c8["schema_keys_skipped"])))

    # ---- C6 phase A reference availability ----
    results.append(("C6 phase A reference parsed", phase_a_map is not None,
                    phase_a_note + ("; values: " + ", ".join(
                        "%s=%d" % (os.path.basename(k.rstrip('/')), v)
                        for k, v in sorted(phase_a_map.items()))
                        if phase_a_map else "")))
    return results


# ----------------------------------------------------------------------------
# rendering
# ----------------------------------------------------------------------------

def pct(a, b):
    return (100.0 * (a - b) / b) if b else 0.0


def render_project(name, pdir, c, csv_rows, phase_a_map):
    recs = c["recs"]
    w("## Project: `%s`" % pdir)
    w()

    # ---- independent cross-check against phase A (replaces the real-data C4) ----
    w("### Cross-check against phase A (independent)")
    w()
    w("The conservation identity cannot fail on real data — the project total and the "
      "per-session sums come from the same loop, so it is an arithmetic tautology. It "
      "is kept as a fixture control (C4) only. The real-data check is instead against "
      "phase A's independently produced count, parsed from `schema_inventory.md`: "
      "**deduped responses − no-id records must equal phase A's unique `message.id`**.")
    w()
    pa = (phase_a_map or {}).get(pdir)
    if pa is None:
        w("**No phase A reference for this project dir — metrics are not reported.**")
        w()
        return False
    ok, detail, ours, noid, deduped = crosscheck_against_phase_a(
        recs, c["asst_ids_any"], pa)
    w("| quantity | value |")
    w("|---|---|")
    w("| deduped responses (this script) | %d |" % deduped)
    w("| of which carry no `message.id` | %d |" % noid)
    w("| deduped responses − no-id records | %d |" % ours)
    w("| phase A unique `message.id` (parsed) | %d |" % pa)
    w("| delta | %+d |" % (ours - pa))
    w("| distinct `message.id` on ANY assistant line (diagnostic) | %d |" %
      len(c["asst_ids_any"]))
    w("| verdict | **%s** |" % ("MATCH" if ok else "MISMATCH"))
    w()
    if not ok:
        w("**CROSS-CHECK FAILED — metrics for this project are not reported.** "
          "A non-zero delta means this script and phase A disagree about how many "
          "API responses the corpus contains; every token total below would inherit "
          "that disagreement. The diagnostic row separates the two candidate causes: "
          "if it equals phase A's number but the deduped-minus-no-id figure does not, "
          "the gap is assistant lines that carry a `message.id` but no `usage` object.")
        w()
        return False
    w()

    # per-session / project totals (single pass, reused below)
    per_sess = defaultdict(lambda: dict((f, 0) for f in FIELDS))
    tot = dict((f, 0) for f in FIELDS)
    for r in recs.values():
        for f in FIELDS:
            per_sess[r["session"]][f] += r["primary"][f]
            tot[f] += r["primary"][f]

    # ---- B1 ----
    w("### B1 — tokens, deduped by `message.id`")
    w()
    w("Primary rule: the **last line in file order** per `message.id`. "
      "Sensitivity rule: the **per-field maximum** across lines sharing the id.")
    w()
    w("| metric | value |")
    w("|---|---|")
    w("| assistant lines | %d |" % c["asst_lines"])
    w("| assistant lines carrying a `usage` object | %d |" % c["asst_lines_with_usage"])
    w("| deduped API responses | %d |" % len(recs))
    w("| assistant lines with `usage` but **no** `message.id` | %d |" % c["no_id_with_usage"])
    w("| ids appearing on >1 line | %d |" %
      sum(1 for v in c["lines_per_id"].values() if v > 1))
    w()
    if c["no_id_with_usage"]:
        w("The %d usage-bearing lines without a `message.id` are **retained**, each as "
          "its own response record. They cannot be deduped and they are not dropped; "
          "they are counted in every total below."
          % c["no_id_with_usage"])
    else:
        w("No usage-bearing assistant line lacks a `message.id`, so nothing was "
          "retained under the synthetic-key path and no total depends on it.")
    w()
    maxtot = dict((f, 0) for f in FIELDS)
    for r in recs.values():
        for f in FIELDS:
            maxtot[f] += r["maxv"][f]
    w("| field | primary (last-line) | sensitivity (per-field max) | diff | % diff |")
    w("|---|---|---|---|---|")
    for f in FIELDS:
        w("| %s | %d | %d | %+d | %+.4f%% |" %
          (FIELD_LABEL[f], tot[f], maxtot[f], maxtot[f] - tot[f],
           pct(maxtot[f], tot[f])))
    gp = sum(tot[f] for f in FIELDS)
    gm = sum(maxtot[f] for f in FIELDS)
    w("| **all four** | **%d** | **%d** | **%+d** | **%+.4f%%** |" %
      (gp, gm, gm - gp, pct(gm, gp)))
    w()

    sessions = sorted(per_sess.keys())
    w("### B1/B2/B3 per session")
    w()
    w("| session | responses | main/side | models | first ts | last ts | input | "
      "cache_creation | cache_read | output | re-read share | cc share | "
      "context peak | compact_boundary |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    pooled_num = 0
    pooled_den = 0
    pooled_cc = 0
    by_session_recs = defaultdict(list)
    for r in recs.values():
        by_session_recs[r["session"]].append(r)
    for sid in sessions:
        rs = by_session_recs[sid]
        main = sum(1 for r in rs if not r["sidechain"])
        side = sum(1 for r in rs if r["sidechain"])
        models = sorted(set(r["model"] for r in rs if r["model"]))
        cr = sum(r["primary"]["cache_read_input_tokens"] for r in rs)
        cc = sum(r["primary"]["cache_creation_input_tokens"] for r in rs)
        ip = sum(r["primary"]["input_tokens"] for r in rs)
        op = sum(r["primary"]["output_tokens"] for r in rs)
        den = ip + cc + cr
        peak = max((r["primary"]["input_tokens"] +
                    r["primary"]["cache_creation_input_tokens"] +
                    r["primary"]["cache_read_input_tokens"]) for r in rs) if rs else 0
        pooled_num += cr
        pooled_den += den
        pooled_cc += cc
        w("| `%s` | %d | %d/%d | %s | %s | %s | %d | %d | %d | %d | %.4f | %.4f | %d | %d |"
          % (sid, len(rs), main, side, ", ".join(models) or "-",
             c["session_first_ts"].get(sid, "-"), c["session_last_ts"].get(sid, "-"),
             ip, cc, cr, op,
             (cr / den) if den else 0.0, (cc / den) if den else 0.0,
             peak, c["compact_boundary"].get(sid, 0)))
        csv_rows.append(dict(
            project=name, session_id=sid, responses=len(rs),
            responses_main=main, responses_sidechain=side,
            models="|".join(models), first_ts=c["session_first_ts"].get(sid, ""),
            last_ts=c["session_last_ts"].get(sid, ""),
            input_tokens=ip, cache_creation_input_tokens=cc,
            cache_read_input_tokens=cr, output_tokens=op,
            reread_share_proxy=round((cr / den) if den else 0.0, 6),
            cache_creation_share=round((cc / den) if den else 0.0, 6),
            context_peak=peak,
            compact_boundary=c["compact_boundary"].get(sid, 0)))
    w()

    # ---- B2 ----
    w("### B2 — re-read share (PROXY)")
    w()
    w("Definition, per response: `cache_read / (input + cache_creation + cache_read)`. "
      "This is a **proxy**. It measures the share of prompt tokens served from cache, "
      "which is not the same quantity as \"how much of the context was re-read\": it "
      "cannot distinguish a cache hit on material the model used from a cache hit on "
      "material it ignored, and a cache miss caused by a TTL expiry looks identical to "
      "genuinely new context.")
    w()
    w("| metric | value |")
    w("|---|---|")
    w("| pooled re-read share (token-weighted) | %.4f |" %
      ((pooled_num / pooled_den) if pooled_den else 0.0))
    w("| pooled cache_creation share (token-weighted) | %.4f |" %
      ((pooled_cc / pooled_den) if pooled_den else 0.0))
    w("| pooled uncached-input share | %.4f |" %
      (((pooled_den - pooled_num - pooled_cc) / pooled_den) if pooled_den else 0.0))
    w("| denominator (prompt tokens) | %d |" % pooled_den)
    w()
    shares = []
    for r in recs.values():
        d = (r["primary"]["input_tokens"] +
             r["primary"]["cache_creation_input_tokens"] +
             r["primary"]["cache_read_input_tokens"])
        if d:
            shares.append(r["primary"]["cache_read_input_tokens"] / d)
    shares.sort()
    if shares:
        def q(p):
            return shares[min(len(shares) - 1, int(p * len(shares)))]
        w("Per-response (unweighted) distribution of the proxy, n=%d: "
          "p10=%.4f p25=%.4f p50=%.4f p75=%.4f p90=%.4f" %
          (len(shares), q(.10), q(.25), q(.50), q(.75), q(.90)))
        w()

    # ---- B3 ----
    w("### B3 — context peak and the compaction positive control")
    w()
    peaks = []
    for sid in sessions:
        rs = by_session_recs[sid]
        peaks.append((max((r["primary"]["input_tokens"] +
                           r["primary"]["cache_creation_input_tokens"] +
                           r["primary"]["cache_read_input_tokens"]) for r in rs), sid))
    peaks.sort(reverse=True)
    w("| metric | value |")
    w("|---|---|")
    w("| max context peak over all sessions | %d |" % (peaks[0][0] if peaks else 0))
    w("| session holding it | `%s` |" % (peaks[0][1] if peaks else "-"))
    w("| sessions with peak > 200,000 | %d |" % sum(1 for p, _ in peaks if p > 200000))
    w("| sessions with peak > 500,000 | %d |" % sum(1 for p, _ in peaks if p > 500000))
    w("| sessions with peak > 900,000 | %d |" % sum(1 for p, _ in peaks if p > 900000))
    w("| total `system/compact_boundary` lines | %d |" % sum(c["compact_boundary"].values()))
    w("| sessions with >=1 compact_boundary | %d |" %
      sum(1 for v in c["compact_boundary"].values() if v))
    w()

    # ---- positive control, with a COMPUTED verdict ----
    w("**Positive control — the S86 context-limit event "
      "(sessions dated 2026-09-29 / 2026-09-30):**")
    w()
    target = [sid for sid in sessions
              if (c["session_last_ts"].get(sid, "")[:10] in ("2026-09-29", "2026-09-30")
                  or c["session_first_ts"].get(sid, "")[:10] in ("2026-09-29", "2026-09-30"))]
    if not target:
        w("No session in this project carries a 2026-09-29 or 2026-09-30 timestamp; "
          "the positive control cannot be evaluated here.")
        w()
    else:
        w("| session | first ts | last ts | responses | context peak | compact_boundary | "
          "isApiErrorMessage | truncatedAfterOutput | `error` key |")
        w("|---|---|---|---|---|---|---|---|---|")
        marks = Counter()
        for sid in target:
            rs = by_session_recs[sid]
            pk = max((r["primary"]["input_tokens"] +
                      r["primary"]["cache_creation_input_tokens"] +
                      r["primary"]["cache_read_input_tokens"]) for r in rs) if rs else 0
            cb = c["compact_boundary"].get(sid, 0)
            ae = c["api_error_lines"].get(sid, 0)
            tr = c["truncated_lines"].get(sid, 0)
            ek = c["error_key_lines"].get(sid, 0)
            marks["compact_boundary"] += cb
            marks["isApiErrorMessage"] += ae
            marks["truncatedAfterOutput"] += tr
            marks["error-key"] += ek
            marks["stop_reason=max_tokens"] += \
                c["stop_reasons_by_session"].get(sid, Counter()).get("max_tokens", 0)
            w("| `%s` | %s | %s | %d | %d | %d | %d | %d | %d |" %
              (sid, c["session_first_ts"].get(sid, "-"),
               c["session_last_ts"].get(sid, "-"), len(rs), pk, cb, ae, tr, ek))
        w()
        w("`stop_reason` values seen in those sessions (enum values, not text):")
        w()
        agg = Counter()
        for sid in target:
            agg.update(c["stop_reasons_by_session"].get(sid, Counter()))
        w("| stop_reason | count |")
        w("|---|---|")
        for k, v in agg.most_common():
            w("| `%s` | %d |" % (k, v))
        w()
        # ---- marker disambiguation, target sessions only ----
        w("**Pre-registered reading, stated before the table:** an event counts "
          "as a *context-limit hit* only if the context of its nearest preceding "
          "deduped response is **>= 900,000**, OR its `error` type/code names "
          "*context* or *length*. Every other marker is reported as an "
          "**other API event**. `prev context` is the response immediately "
          "before the marker line, within the same file and the same session; "
          "where no such response exists it reads `none` and the size test "
          "cannot fire.")
        w()
        tset = set(target)
        evs = [e for e in c["marker_events"] if e["session"] in tset]
        hits = 0
        others = 0
        by_line = {}
        line_order = []
        if evs:
            w("| file:line | session | timestamp | marker | prev context | error value |")
            w("|---|---|---|---|---|---|")
            for e in evs:
                pr = recs.get(e["prev_key"]) if e["prev_key"] else None
                if pr is not None and pr["session"] != e["session"]:
                    pr = None
                ctx = (pr["primary"]["input_tokens"] +
                       pr["primary"]["cache_creation_input_tokens"] +
                       pr["primary"]["cache_read_input_tokens"]) if pr else None
                disp, code = render_err(e["err"])
                is_hit = ((ctx is not None and ctx >= 900000)
                          or (code is not None and CTX_CODE_RE.search(code)))
                if is_hit:
                    hits += 1
                else:
                    others += 1
                src = e["src"]
                if src not in by_line:
                    by_line[src] = dict(hit=False, ctx=ctx, session=e["session"],
                                        ts=e["ts"], markers=[], size_arm=False)
                    line_order.append(src)
                bl = by_line[src]
                bl["hit"] = bl["hit"] or is_hit
                bl["markers"].append(e["marker"])
                if ctx is not None and ctx >= 900000:
                    bl["size_arm"] = True
                w("| `%s:%d` | `%s` | %s | %s | %s | %s |" %
                  (os.path.basename(src[0]), src[1], e["session"], e["ts"] or "-",
                   e["marker"], ("%d" % ctx) if ctx is not None else "none", disp))
            w()
        else:
            w("_no marker events in the target sessions_")
            w()
        hit_lines = [k for k in line_order if by_line[k]["hit"]]
        other_lines = [k for k in line_order if not by_line[k]["hit"]]
        w("A **line** counts as a context-limit hit when ANY of its markers meets "
          "the pre-registered reading. The reading, the 900,000 bar and the "
          "type/code pattern are unchanged.")
        w()
        w("Under the pre-registered reading, counted BOTH ways:")
        w()
        w("| unit | context-limit hits | other API events | total |")
        w("|---|---|---|---|")
        w("| marker events | %d | %d | %d |" % (hits, others, len(evs)))
        w("| distinct marker lines, keyed by (file, line number) | %d | %d | %d |"
          % (len(hit_lines), len(other_lines), len(by_line)))
        w()
        if hit_lines:
            w("Margin over the 900,000 bar, for each hit line:")
            w()
            w("| file:line | markers on that line | prev context | margin (tokens) | margin (%) |")
            w("|---|---|---|---|---|")
            for k in hit_lines:
                bl = by_line[k]
                if bl["size_arm"] and bl["ctx"] is not None:
                    marg = bl["ctx"] - 900000
                    w("| `%s:%d` | %s | %d | %+d | %+.4f%% |" %
                      (os.path.basename(k[0]), k[1], ", ".join(bl["markers"]),
                       bl["ctx"], marg, 100.0 * marg / 900000))
                else:
                    w("| `%s:%d` | %s | %s | n/a — hit on the type/code arm, not "
                      "the size arm | n/a |" %
                      (os.path.basename(k[0]), k[1], ", ".join(bl["markers"]),
                       ("%d" % bl["ctx"]) if bl["ctx"] is not None else "none"))
            w()
        hot = [k for k in ("compact_boundary", "isApiErrorMessage",
                           "truncatedAfterOutput", "error-key",
                           "stop_reason=max_tokens") if marks[k] > 0]
        if hot:
            w("**S86 context-limit event MARKED by: %s**" %
              ", ".join("%s (%d)" % (k, marks[k]) for k in hot))
        else:
            w("context-limit hits without compaction are NOT observable by this metric")
        w()

    w("String values matching a context-limit pattern — **key paths and counts only, "
      "never values**. Paths under `%s` are conversation text and are excluded, because "
      "this project discusses context windows constantly; their match count is reported "
      "as a single number instead." % CONTENT_PATH_PREFIX)
    w()
    w("Excluded matches under `%s`: **%d**." % (CONTENT_PATH_PREFIX, c["ctx_excluded"]))
    w()
    w("Other text-bearing paths (for example `$.rendered`, `$.toolUseResult`, "
      "`$.lastPrompt`) are **not** excluded, so some of the rows below may still be "
      "conversation text rather than a harness field.")
    w()
    if c["ctx_paths"]:
        w("| key path | matches |")
        w("|---|---|")
        for k, v in c["ctx_paths"].most_common(20):
            w("| `%s` | %d |" % (k, v))
        w()
        w("(distinct non-content paths matching: %d)" % len(c["ctx_paths"]))
        w()
    else:
        w("_no string value outside `%s` matches the context-limit pattern_"
          % CONTENT_PATH_PREFIX)
        w()

    # ---- B4 ----
    w("### B4 — Bash command forms and denials")
    w()
    forms = Counter()
    denials = Counter()
    errs_not_denial = Counter()
    unjoined = Counter()
    bare_cd = 0
    for tuid, (tname, cmd, sid) in c["tool_use"].items():
        if tname != "Bash":
            continue
        form, isbare = classify_command(cmd)
        if isbare:
            bare_cd += 1
        forms[form] += 1
        tr = c["tool_res"].get(tuid)
        if tr is None:
            unjoined[form] += 1
            continue
        is_err, txt = tr
        if is_err:
            t = " ".join(txt.split())
            if any(t.startswith(p) for p in DENIAL_PREFIXES):
                denials[form] += 1
            else:
                errs_not_denial[form] += 1
    w("Denial is defined as a joined `tool_result` with `is_error=true` whose text "
      "begins with one of these prefixes — the only transcript text this report prints:")
    w()
    for p in DENIAL_PREFIXES:
        w("- `%s`" % p)
    w()
    w("| leading form | Bash calls | denials | denial rate | errors that are not denials | "
      "no joined tool_result |")
    w("|---|---|---|---|---|---|")
    for f in ["cd-compound", "cd-semicolon", "git -C", "bare git",
              "python3/heredoc", "other"]:
        n = forms.get(f, 0)
        d = denials.get(f, 0)
        w("| %s | %d | %d | %s | %d | %d |" %
          (f, n, d, ("%.1f%%" % (100.0 * d / n)) if n else "-",
           errs_not_denial.get(f, 0), unjoined.get(f, 0)))
    tn = sum(forms.values())
    td = sum(denials.values())
    w("| **total** | **%d** | **%d** | **%s** | **%d** | **%d** |" %
      (tn, td, ("%.1f%%" % (100.0 * td / tn)) if tn else "-",
       sum(errs_not_denial.values()), sum(unjoined.values())))
    w()
    w("Note: `cd-compound` includes %d bare `cd` invocations carrying no `&&` and no "
      "`;`; they are counted there because no separator distinguishes them." % bare_cd)
    w()
    return True


def render_b5(projects):
    w("## B5 — prompt observability")
    w()
    w("Key names at any nesting depth, and `type`/`subtype` values, containing "
      "`permission`, `approv` or `prompt`. Names and counts only.")
    w()
    found_all = {}
    approval_named_all = {}
    only_denied_all = {}
    only_allowed_all = {}

    for name, pdir, c in projects:
        w("**`%s`**" % pdir)
        w()
        hits = [(k, v) for k, v in c["all_keys"].items()
                if any(m in k.lower() for m in MARKER_B5)]
        hits.sort(key=lambda x: (-x[1], x[0]))
        found_all[pdir] = [k for k, _ in hits]
        w("| key name | occurrences | name matches an approval-record shape |")
        w("|---|---|---|")
        for k, v in hits:
            w("| `%s` | %d | %s |" %
              (k, v, "yes" if APPROVAL_NAME_RE.search(k) else "no"))
        w()
        approval_named_all[pdir] = [k for k, _ in hits if APPROVAL_NAME_RE.search(k)]

        tv = [(k, v) for k, v in c["type_counts"].items()
              if any(m in k.lower() for m in MARKER_B5)]
        sv = [(k, v) for k, v in c["subtype_counts"].items()
              if any(m in k.lower() for m in MARKER_B5)]
        if tv or sv:
            w("| field | value | count | matches approval shape |")
            w("|---|---|---|---|")
            for k, v in sorted(tv, key=lambda x: -x[1]):
                w("| `type` | `%s` | %d | %s |" %
                  (k, v, "yes" if APPROVAL_NAME_RE.search(k) else "no"))
            for k, v in sorted(sv, key=lambda x: -x[1]):
                w("| `type`/`subtype` | `%s` | %d | %s |" %
                  (k, v, "yes" if APPROVAL_NAME_RE.search(k) else "no"))
        else:
            w("_no `type` or `subtype` value matches_")
        w()

        # Non-lexical test: do lines carrying a DENIED tool_result differ, in their
        # key set, from lines carrying a non-denied one? If approval were recorded,
        # a key would appear on the allowed side and nowhere else.
        denied_keys = set()
        allowed_keys = set()
        n_den = n_all = 0
        for tuid, (is_err, txt) in c["tool_res"].items():
            pk = c["tool_res_parent_keys"].get(tuid)
            if pk is None:
                continue
            t = " ".join(txt.split())
            if is_err and any(t.startswith(p) for p in DENIAL_PREFIXES):
                denied_keys |= set(pk)
                n_den += 1
            else:
                allowed_keys |= set(pk)
                n_all += 1
        only_den = sorted(denied_keys - allowed_keys)
        only_all = sorted(allowed_keys - denied_keys)
        only_denied_all[pdir] = only_den
        only_allowed_all[pdir] = only_all
        w("Key-set differential on the lines carrying the `tool_result` "
          "(%d denied, %d not denied):" % (n_den, n_all))
        w()
        w("| side | keys present on that side and on no line of the other |")
        w("|---|---|")
        w("| denied only | %s |" %
          (", ".join("`%s`" % k for k in only_den) if only_den else "_none_"))
        w("| not-denied only | %s |" %
          (", ".join("`%s`" % k for k in only_all) if only_all else "_none_"))
        w()

    # ---- computed verdict ----
    any_approval_key = sorted(set(
        k for v in approval_named_all.values() for k in v))
    any_allowed_only_approval = sorted(set(
        k for v in only_allowed_all.values() for k in v
        if APPROVAL_NAME_RE.search(k)))

    w("### B5 verdict (computed from the keys found above)")
    w()
    tot_skipped = sum(c["schema_keys_skipped"] for _, _, c in projects)
    w("Key occurrences skipped because their PATH runs through a JSON-schema "
      "subtree (a dict reached via `properties` whose parent carries `type`, or "
      "anything under `input_schema`): **%d** across both projects (%s). "
      "No key name is special-cased; the rule is structural." %
      (tot_skipped, ", ".join("%s=%d" % (n, c["schema_keys_skipped"])
                              for n, _, c in projects)))
    w()
    w("| test | result |")
    w("|---|---|")
    w("| matching keys found, across both projects | %d |" %
      len(set(k for v in found_all.values() for k in v)))
    w("| of those, whose NAME is shaped like a per-call approval record | %s |" %
      (", ".join("`%s`" % k for k in any_approval_key) if any_approval_key else "none"))
    w("| keys appearing only on not-denied `tool_result` lines and shaped like approval | %s |" %
      (", ".join("`%s`" % k for k in any_allowed_only_approval)
       if any_allowed_only_approval else "none"))
    w()
    if not any_approval_key and not any_allowed_only_approval:
        w("**APPROVED prompts not observable.** No key found by either test records a "
          "per-call approval: no matching key name is shaped like one, and no key "
          "appears on not-denied `tool_result` lines that is absent from denied ones.")
    else:
        w("**APPROVED prompts MAY be observable** — the tests above found "
          "candidate key(s): %s. Each must be inspected before it is relied on." %
          ", ".join("`%s`" % k for k in sorted(set(any_approval_key +
                                                   any_allowed_only_approval))))
    w()
    w("*Author's reading of the listed keys* (interpretation, not measurement): the "
      "matching names divide into session-level mode state and user-turn identifiers, "
      "neither of which is a per-call permission outcome; denials are recoverable from "
      "the `tool_result` error text, so denial counts have no approval denominator. "
      "This reading is offered separately from the computed verdict above and should "
      "be checked against the key tables rather than taken from this sentence.")
    w()


def render_b6():
    w("## B6 — S86 harness result objects")
    w()
    files = sorted(glob.glob(os.path.join(S86_ROOT, "**", "*.json"), recursive=True))
    by_arm = defaultdict(lambda: dict(
        n=0, cost=0.0, usage=Counter(), modelcost=defaultdict(float),
        turns=0, errors=0))
    ufields = ["input_tokens", "cache_creation_input_tokens",
               "cache_read_input_tokens", "output_tokens"]
    total_objs = 0
    for f in files:
        try:
            o = json.load(open(f, "r", errors="replace"))
        except Exception:
            continue
        if not isinstance(o, dict) or "usage" not in o or "modelUsage" not in o:
            continue
        total_objs += 1
        arm = os.path.basename(os.path.dirname(f))
        a = by_arm[arm]
        a["n"] += 1
        tc = o.get("total_cost_usd")
        if isinstance(tc, (int, float)):
            a["cost"] += tc
        u = o.get("usage") or {}
        for k in ufields:
            v = u.get(k)
            if isinstance(v, (int, float)):
                a["usage"][k] += v
        mu = o.get("modelUsage") or {}
        for m, mv in mu.items():
            if isinstance(mv, dict) and isinstance(mv.get("costUSD"), (int, float)):
                a["modelcost"][m] += mv["costUSD"]
        nt = o.get("num_turns")
        if isinstance(nt, int):
            a["turns"] += nt
        if o.get("is_error") is True:
            a["errors"] += 1

    w("Result objects matched (carrying both `usage` and `modelUsage`): **%d**."
      % total_objs)
    w()
    w("| arm | results | is_error | sum total_cost_usd | input | cache_creation | "
      "cache_read | output | num_turns (informational) |")
    w("|---|---|---|---|---|---|---|---|---|")
    tot = dict(n=0, cost=0.0, usage=Counter(), turns=0, errors=0)
    for arm in sorted(by_arm):
        a = by_arm[arm]
        w("| `%s` | %d | %d | %.6f | %d | %d | %d | %d | %d |" %
          (arm, a["n"], a["errors"], a["cost"],
           a["usage"]["input_tokens"], a["usage"]["cache_creation_input_tokens"],
           a["usage"]["cache_read_input_tokens"], a["usage"]["output_tokens"],
           a["turns"]))
        tot["n"] += a["n"]
        tot["cost"] += a["cost"]
        tot["turns"] += a["turns"]
        tot["errors"] += a["errors"]
        for k in ufields:
            tot["usage"][k] += a["usage"][k]
    w("| **total** | **%d** | **%d** | **%.6f** | **%d** | **%d** | **%d** | **%d** | **%d** |"
      % (tot["n"], tot["errors"], tot["cost"],
         tot["usage"]["input_tokens"], tot["usage"]["cache_creation_input_tokens"],
         tot["usage"]["cache_read_input_tokens"], tot["usage"]["output_tokens"],
         tot["turns"]))
    w()
    w("`num_turns` is carried as **informational only** (ADR-028 D7 note): it counts "
      "harness turns, which is not a unit of work and is not comparable across arms.")
    w()
    w("`modelUsage.costUSD` by model and arm — taken verbatim from the tool's own "
      "fields; this script applies no price:")
    w()
    w("| arm | model | sum costUSD |")
    w("|---|---|---|")
    grand = defaultdict(float)
    for arm in sorted(by_arm):
        for m in sorted(by_arm[arm]["modelcost"]):
            v = by_arm[arm]["modelcost"][m]
            grand[m] += v
            w("| `%s` | `%s` | %.6f |" % (arm, m, v))
    for m in sorted(grand):
        w("| **all arms** | `%s` | **%.6f** |" % (m, grand[m]))
    w()
    w("Cross-check: sum of `total_cost_usd` = %.6f, sum of `modelUsage.costUSD` = %.6f "
      "(difference %.6f)." %
      (tot["cost"], sum(grand.values()), tot["cost"] - sum(grand.values())))
    w()


# ----------------------------------------------------------------------------
def main():
    me = os.path.abspath(__file__)
    digest = hashlib.sha256(open(me, "rb").read()).hexdigest()

    w("# WS3.1 phase B — baseline metrics")
    w()
    w("Measurement only. No thresholds are applied; this is a baseline. No ADR text.")
    w()
    w("- script: `%s`" % me)
    w("- `sha256sum`: `%s  %s`" % (digest, me))
    w("- fixtures: `%s`" % FIXTURES)
    w("- sessions CSV: `%s`" % CSV_PATH)
    w("- phase A reference parsed from: `%s`" % PHASE_A_MD)
    w()
    w("---")
    w()
    w("## B0 — controls")
    w()
    w("Controls run first, on synthetic fixtures this script writes. If any control "
      "fails, no metric below it is reported.")
    w()
    phase_a_map, phase_a_note = parse_phase_a_unique_ids(PHASE_A_MD)
    controls = run_controls(phase_a_map, phase_a_note)
    w("| control | result | evidence |")
    w("|---|---|---|")
    for nm, ok, detail in controls:
        w("| %s | **%s** | %s |" % (nm, "PASS" if ok else "FAIL",
                                    str(detail).replace("|", "\\|")))
    w()
    if not all(ok for _, ok, _ in controls):
        failed = [nm for nm, ok, _ in controls if not ok]
        w("**Control(s) failed: %s. Metrics are not reported.**" % ", ".join(failed))
        with open(MD, "w") as fh:
            fh.write("\n".join(out) + "\n")
        for nm, ok, _ in controls:
            sys.stderr.write("%s: %s\n" % (nm, "PASS" if ok else "FAIL"))
        sys.stderr.write("CONTROLS FAILED (%s) - metrics suppressed\n" % ", ".join(failed))
        return 1
    w("All controls PASS. Metrics follow.")
    w()
    w("---")
    w()

    csv_rows = []
    projects = []
    suppressed = []
    for pdir in PROJECT_DIRS:
        name = os.path.basename(pdir.rstrip("/"))
        files = sorted(glob.glob(os.path.join(pdir, "**", "*.jsonl"), recursive=True))
        c = collect(files)
        projects.append((name, pdir, c))
        okp = render_project(name, pdir, c, csv_rows, phase_a_map)
        if not okp:
            suppressed.append(name)
        w("---")
        w()

    render_b5(projects)
    w("---")
    w()
    render_b6()
    w("---")
    w()
    if suppressed:
        w("**Metrics suppressed for: %s** (cross-check against phase A failed)."
          % ", ".join(suppressed))
        w()
    w("_End of baseline._")

    with open(MD, "w") as fh:
        fh.write("\n".join(out) + "\n")

    cols = ["project", "session_id", "responses", "responses_main",
            "responses_sidechain", "models", "first_ts", "last_ts",
            "input_tokens", "cache_creation_input_tokens",
            "cache_read_input_tokens", "output_tokens",
            "reread_share_proxy", "cache_creation_share",
            "context_peak", "compact_boundary"]
    with open(CSV_PATH, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=cols)
        wr.writeheader()
        for r in csv_rows:
            wr.writerow(r)

    for nm, ok, _ in controls:
        sys.stderr.write("%s: %s\n" % (nm, "PASS" if ok else "FAIL"))
    sys.stderr.write("wrote %s (%d bytes)\n" % (MD, os.path.getsize(MD)))
    sys.stderr.write("wrote %s (%d rows)\n" % (CSV_PATH, len(csv_rows)))
    return 2 if suppressed else 0


if __name__ == "__main__":
    sys.exit(main())
