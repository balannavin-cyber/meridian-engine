#!/usr/bin/env python3
"""
WS3.1 phase C - findings-document generator.

Every figure in the emitted document is parsed out of the frozen-snapshot
artefacts (or, for the live-drift paragraph only, out of the live phase B
report that the snapshot runs did not overwrite). Nothing is typed in and
nothing has a default: a pattern that does not match is a named, fatal error
and the document is not written.

A final assertion walks the rendered document and fails on any run of three or
more digits that the generator did not emit. That check is what makes "no
figure was typed" verifiable rather than asserted.

Inputs:
    $SNAP/schema_inventory.md, $SNAP/baseline_b.md, $SNAP/MANIFEST.sha256
        ($SNAP from /home/ssm-user/s87_measure/.snap_path)
    /home/ssm-user/s87_measure/baseline_b.md   (the LIVE run, for section 1)
    /home/ssm-user/s87_measure/gitC_result.json
        The operator's Block 4 observation, for section 6. Section 6 is rendered
        FROM this file; it is not typed into the document. A missing file is a
        named fatal error, not an empty table -- an unrun experiment must not be
        able to render as a run one.
Output:
    /home/ssm-user/meridian-cc/docs/research/s87_routing/WS3.1_baseline.md
    /home/ssm-user/meridian-cc/docs/research/s87_routing/scripts/*.py
"""
import os
import re
import sys
import json
import shutil
import hashlib

SNAP_PATH_FILE = "/home/ssm-user/s87_measure/.snap_path"
GITC_JSON = "/home/ssm-user/s87_measure/gitC_result.json"
LIVE_MD = "/home/ssm-user/s87_measure/baseline_b.md"
SRC_SCRIPTS = ["/home/ssm-user/s87_measure/schema_inventory.py",
               "/home/ssm-user/s87_measure/baseline_b.py"]
REPO_DIR = "/home/ssm-user/meridian-cc/docs/research/s87_routing"
DOC = os.path.join(REPO_DIR, "WS3.1_baseline.md")
SCRIPTS_DIR = os.path.join(REPO_DIR, "scripts")

ENGINE = "-home-ssm-user-meridian-engine"
CC = "-home-ssm-user-meridian-cc"

MISSING = []
ALLOWED_RUNS = set()

# Non-measurement digit runs the document is permitted to contain. Each one is
# a document identifier, not a figure, and each is listed here explicitly so
# the final assertion cannot be widened silently.
LITERAL_RUNS = {
    "029": "the ADR this baseline feeds (ADR-029)",
    "256": "part of the algorithm/filename token `sha256` (and `MANIFEST.sha256`); "
           "a hash-algorithm name, never a measurement",
}


def track(v):
    """Register every 3+ digit run in a value the generator emits."""
    s = v if isinstance(v, str) else str(v)
    for r in re.findall(r"\d{3,}", s):
        ALLOWED_RUNS.add(r)
    return v


def req(text, pattern, field, group=1, flags=0):
    """Parse one field. No default: a miss is recorded and is fatal."""
    m = re.search(pattern, text, flags)
    if not m:
        MISSING.append(field)
        return None
    return track(m.group(group))


def reqi(text, pattern, field, group=1):
    v = req(text, pattern, field, group)
    if v is None:
        return None
    n = int(v.replace(",", ""))
    track(n)
    return n


def reqf(text, pattern, field, group=1):
    v = req(text, pattern, field, group)
    return float(v) if v is not None else None


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(65536), b""):
            h.update(blk)
    return track(h.hexdigest())


def split_h2(text):
    """Split a report into {h2 heading: body}, bounded at the next h2."""
    out = {}
    parts = re.split(r"\n## ", "\n" + text)
    for ch in parts[1:]:
        head, _, body = ch.partition("\n")
        out[head.strip()] = body
    return out


def project_chunks(text, prefix):
    out = {}
    for head, body in split_h2(text).items():
        if head.startswith(prefix):
            m = re.match(r"%s\s*`([^`]+)`" % re.escape(prefix), head)
            if m:
                out[os.path.basename(m.group(1).rstrip("/"))] = body
    return out


def die_if_missing():
    if MISSING:
        sys.stderr.write("FATAL: %d field(s) could not be parsed; no document "
                         "written.\n" % len(MISSING))
        for f in MISSING:
            sys.stderr.write("  missing field: %s\n" % f)
        sys.exit(1)


def fatal(msg):
    sys.stderr.write("FATAL: %s\n" % msg)
    sys.exit(1)


def main():
    if not os.path.exists(SNAP_PATH_FILE):
        fatal("missing field: snapshot path file %s" % SNAP_PATH_FILE)
    snap = open(SNAP_PATH_FILE).read().strip()
    for f in ("schema_inventory.md", "baseline_b.md", "MANIFEST.sha256"):
        if not os.path.exists(os.path.join(snap, f)):
            fatal("missing field: %s/%s" % (snap, f))
    if not os.path.exists(LIVE_MD):
        fatal("missing field: live phase B report %s" % LIVE_MD)
    if not os.path.exists(GITC_JSON):
        fatal("missing field: Block 4 operator result %s" % GITC_JSON)

    inv = open(os.path.join(snap, "schema_inventory.md")).read()
    bas = open(os.path.join(snap, "baseline_b.md")).read()
    live = open(LIVE_MD).read()
    man_path = os.path.join(snap, "MANIFEST.sha256")
    man = open(man_path).read()

    # ---- Block 4: the operator's observation, parsed not transcribed --------
    # Each key is "<row number> <command>"; the value is the observation. Both
    # halves are split out of the key rather than restated, so the rendered
    # table cannot disagree with the file it came from.
    try:
        gitc = json.load(open(GITC_JSON))
    except ValueError as e:
        fatal("Block 4 result file is not valid JSON: %s" % e)
    for k in ("observed", "cwd", "reps_per_command", "session", "results"):
        if k not in gitc:
            fatal("missing field: gitC_result.json key '%s'" % k)
    gc_obs = track(gitc["observed"])
    gc_cwd = track(gitc["cwd"])
    gc_reps = track(gitc["reps_per_command"])
    gc_sess = track(gitc["session"])
    gc_rows = []
    for key, verdict in gitc["results"].items():
        m = re.match(r"^(\d+)\s+(.+)$", key)
        if not m:
            fatal("Block 4 result key is not '<n> <command>': %r" % key)
        gc_rows.append((track(m.group(1)), track(m.group(2)), track(verdict)))
    if not gc_rows:
        fatal("Block 4 result file carries no command rows")
    # The classification the prose below asserts, derived from the commands
    # themselves rather than from the order the file happens to list them.
    gc_bare = [r for r in gc_rows if " -C " not in r[1]]
    gc_dashC = [r for r in gc_rows if " -C " in r[1]]
    if not gc_bare or not gc_dashC:
        fatal("Block 4 result file lacks both a bare and a -C form; the "
              "comparison section 6 renders would have nothing to compare")
    gc_cwd_rows = [r for r in gc_dashC if gc_cwd in r[1]]

    # ---------------- provenance ----------------
    snap_name = track(os.path.basename(snap.rstrip("/")))
    track(snap)
    stamp = req(snap_name, r"^snap_(\d{8}T\d{6}Z)$", "snapshot UTC stamp in dir name")
    man_sha = sha256_file(man_path)
    man_lines = track(len([l for l in man.splitlines() if l.strip()]))
    man_jsonl = track(len([l for l in man.splitlines()
                           if l.strip().endswith(".jsonl")]))
    script_sha = {os.path.basename(p): sha256_file(p) for p in SRC_SCRIPTS}

    inv_c = project_chunks(inv, "Project dir:")
    bas_c = project_chunks(bas, "Project:")
    live_c = project_chunks(live, "Project:")
    for k in (ENGINE, CC):
        if k not in inv_c:
            MISSING.append("schema_inventory chunk for %s" % k)
        if k not in bas_c:
            MISSING.append("snapshot baseline_b chunk for %s" % k)
    if ENGINE not in live_c:
        MISSING.append("live baseline_b chunk for %s" % ENGINE)
    die_if_missing()

    # ------- section 1: the LIVE run's failed cross-check, parsed from the
    #         live report, which the snapshot runs did not overwrite -------
    le = live_c[ENGINE]
    live_ours = reqi(le, r"\| deduped responses \(this script\) \| (\d+) \|",
                     "live engine deduped responses")
    live_pa = reqi(le, r"\| phase A unique `message\.id` \(parsed\) \| (\d+) \|",
                   "live engine phase-A unique ids")
    live_delta = req(le, r"\| delta \| ([+-]\d+) \|", "live engine cross-check delta")
    live_verdict = req(le, r"\| verdict \| \*\*(\w+)\*\* \|",
                       "live engine cross-check verdict")
    die_if_missing()
    if live_verdict != "MISMATCH":
        fatal("live engine cross-check verdict is %r, expected MISMATCH; section 1 "
              "describes a failure that this report does not contain."
              % live_verdict)

    # ---------------- controls ----------------
    ctrl = {}
    for cid, label in (("C1", r"C1 dedup"),
                       ("C2", r"C2 streaming"),
                       ("C3", r"C3 cd regex"),
                       ("C4", r"C4 conservation \(fixture only\)"),
                       ("C5", r"C5 negative control \(cross-check can fail\)"),
                       ("C6", r"C6 phase A reference parsed"),
                       ("C7", r"C7 schema subtree skipped"),
                       ("C8", r"C8 real approval key survives")):
        pat = r"\| (%s) \| \*\*(PASS|FAIL)\*\*" % label
        ctrl[cid] = (req(bas, pat, "control %s label" % cid, 1),
                     req(bas, pat, "control %s verdict" % cid, 2))
    c5_blind = req(bas, r"(cannot detect a lost duplicate line, only a lost id)",
                   "C5 blind-spot sentence")
    c7_skipped = reqi(bas, r"C7 schema subtree skipped.*?schema-key occurrences "
                           r"skipped: (\d+)", "C7 skipped count")
    c1_dedup = reqi(bas, r"C1 dedup.*?deduped input sum=(\d+)", "C1 deduped sum")
    c1_perline = reqi(bas, r"C1 dedup.*?a per-line sum would be (\d+)",
                      "C1 per-line contrast")
    c2_perline = reqi(bas, r"C2 streaming.*?per-line sum=(\d+)",
                      "C2 per-line contrast")

    # ---------------- per project ----------------
    P = {}
    for key in (ENGINE, CC):
        i, b = inv_c[key], bas_c[key]
        d = {}
        d["files"] = reqi(i, r"\| JSONL files \(recursive\) \| (\d+) \|",
                          "%s jsonl files" % key)
        d["bytes"] = reqi(i, r"\| total bytes \| (\d+) \|", "%s total bytes" % key)
        d["lines"] = reqi(i, r"\| total non-blank lines \| (\d+) \|",
                          "%s total lines" % key)
        d["parse_fail"] = reqi(i, r"\| JSON parse failures \| (\d+) \|",
                               "%s parse failures" % key)
        d["sessions"] = reqi(
            i, r"\| distinct `sessionId`/`session_id` values \| (\d+) \|",
            "%s distinct sessions" % key)
        d["first_ts"] = req(i, r"\| earliest timestamp \| (\S+) \|",
                            "%s earliest ts" % key)
        d["last_ts"] = req(i, r"\| latest timestamp \| (\S+) \|",
                           "%s latest ts" % key)
        d["unique_ids"] = reqi(i, r"\| unique `message\.id` \| (\d+) \|",
                               "%s unique message.id" % key)

        d["asst_lines"] = reqi(b, r"\| assistant lines \| (\d+) \|",
                               "%s assistant lines" % key)
        d["deduped"] = reqi(b, r"\| deduped API responses \| (\d+) \|",
                            "%s deduped responses" % key)
        d["noid"] = reqi(b, r"\| assistant lines with `usage` but \*\*no\*\* "
                            r"`message\.id` \| (\d+) \|", "%s no-id lines" % key)
        d["delta"] = req(b, r"\| delta \| ([+-]\d+) \|", "%s snapshot delta" % key)
        d["verdict"] = req(b, r"\| verdict \| \*\*(\w+)\*\* \|",
                           "%s snapshot verdict" % key)
        d["sessions_with_resp"] = track(len(re.findall(
            r"\n\| `[0-9a-f-]{36}` \| \d+ \| \d+/\d+ \|", b)))
        if d["sessions_with_resp"] == 0:
            MISSING.append("%s per-session table rows" % key)

        for f, lab in (("input", "input"), ("cc", "cache_creation_input"),
                       ("cr", "cache_read_input"), ("out", "output")):
            d[f] = reqi(b, r"\| %s \| (\d+) \| \d+ \| [+-]\d+ \|" % lab,
                        "%s B1 %s primary" % (key, lab))
            d[f + "_sens"] = reqi(b, r"\| %s \| \d+ \| (\d+) \| [+-]\d+ \|" % lab,
                                  "%s B1 %s sensitivity" % (key, lab))
        d["all4"] = reqi(b, r"\| \*\*all four\*\* \| \*\*(\d+)\*\*",
                         "%s B1 all-four primary" % key)
        d["all4_sens"] = reqi(b, r"\| \*\*all four\*\* \| \*\*\d+\*\* \| \*\*(\d+)\*\*",
                              "%s B1 all-four sensitivity" % key)
        d["all4_pct"] = req(b, r"\| \*\*all four\*\*.*?\| \*\*([+-][\d.]+%)\*\* \|",
                            "%s B1 all-four pct gap" % key)

        d["reread"] = req(b, r"\| pooled re-read share \(token-weighted\) \| "
                             r"([\d.]+) \|", "%s pooled re-read" % key)
        d["ccshare"] = req(b, r"\| pooled cache_creation share \(token-weighted\) \| "
                              r"([\d.]+) \|", "%s pooled cc share" % key)
        d["den"] = reqi(b, r"\| denominator \(prompt tokens\) \| (\d+) \|",
                        "%s prompt-token denominator" % key)
        d["peak"] = reqi(b, r"\| max context peak over all sessions \| (\d+) \|",
                         "%s max peak" % key)
        d["thr200"] = req(b, r"\| sessions with peak > ([\d,]+) \| \d+ \|",
                          "%s first peak threshold label" % key)
        d["gt200"] = reqi(b, r"\| sessions with peak > %s \| (\d+) \|"
                          % re.escape(d["thr200"] or ""), "%s sessions>t1" % key)
        d["thr500"] = req(b, r"\| sessions with peak > ([\d,]+) \| \d+ \|\n"
                             r"\| sessions with peak > [\d,]+ \| \d+ \|",
                          "%s second peak threshold label" % key)
        d["gt500"] = reqi(b, r"\| sessions with peak > %s \| (\d+) \|"
                          % re.escape(d["thr500"] or ""), "%s sessions>t2" % key)
        d["compact"] = reqi(b, r"\| total `system/compact_boundary` lines \| (\d+) \|",
                            "%s compact_boundary total" % key)

        d["forms"] = {}
        for form in ("cd-compound", "cd-semicolon", "git -C", "bare git",
                     "python3/heredoc", "other"):
            m = re.search(r"\| %s \| (\d+) \| (\d+) \| ([\d.]+%%|-) \|"
                          % re.escape(form), b)
            if not m:
                MISSING.append("%s B4 row %s" % (key, form))
                continue
            d["forms"][form] = tuple(track(m.group(g)) for g in (1, 2, 3))
        m = re.search(r"\| \*\*total\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| "
                      r"\*\*([\d.]+%)\*\*", b)
        if not m:
            MISSING.append("%s B4 total row" % key)
        else:
            d["forms_total"] = tuple(track(m.group(g)) for g in (1, 2, 3))

        for nm, pat in (("ev", r"\| marker events"),
                        ("ln", r"\| distinct marker lines, keyed by \(file, line "
                               r"number\)")):
            cols = [r"(\d+)", r"(\d+)", r"(\d+)"]
            full = pat + r" \| " + r" \| ".join(cols) + r" \|"
            for g, suf in ((1, "hits"), (2, "other"), (3, "total")):
                d[nm + "_" + suf] = reqi(b, full, "%s %s %s" % (key, nm, suf), g)
        P[key] = d
    die_if_missing()

    # engine-only: the hit line and its margin
    eb = bas_c[ENGINE]
    hm = re.search(r"\| `([^`]+\.jsonl:\d+)` \| ([^|]+?) \| (\d+) \| ([+-]\d+) \| "
                   r"([+-][\d.]+%) \|", eb)
    if not hm:
        MISSING.append("engine hit-line margin row")
        die_if_missing()
    hit_file = track(hm.group(1))
    hit_markers = track(hm.group(2).strip())
    hit_ctx = reqi(eb, r"\| `%s` \| [^|]+ \| (\d+) \|" % re.escape(hit_file),
                   "engine hit-line context")
    hit_marg = track(hm.group(4))
    hit_pct = track(hm.group(5))
    hit_marg_plus = track(int(hm.group(4)) + 1)
    marked_by = req(eb, r"\*\*S86 context-limit event MARKED by: (.*?)\*\*",
                    "engine MARKED-by line")
    cc_notobs = req(bas_c[CC], r"(context-limit hits without compaction are NOT "
                               r"observable by this metric)", "cc not-observable line")
    bar = req(eb, r"deduped response is \*\*>= ([\d,]+)\*\*", "pre-registered bar")

    # ---------------- B5 ----------------
    b5 = split_h2(bas).get("B5 — prompt observability")
    if b5 is None:
        fatal("missing field: B5 section")
    b5_verdict = req(b5, r"(\*\*APPROVED prompts (?:not observable|MAY be "
                         r"observable)\.?\*\*[^\n]*)", "B5 verdict line")
    b5_skipped = reqi(b5, r"subtree[^:]*: \*\*(\d+)\*\* across both projects",
                      "B5 schema-skip total")
    b5_skip_eng = reqi(b5, r"%s=(\d+)" % re.escape(ENGINE), "B5 schema-skip engine")
    b5_skip_cc = reqi(b5, r"%s=(\d+)" % re.escape(CC), "B5 schema-skip cc")
    b5_keys = reqi(b5, r"\| matching keys found, across both projects \| (\d+) \|",
                   "B5 matching key count")
    # per-project B5 sub-blocks
    b5_sub = {}
    blocks = re.split(r"\n\*\*`([^`]+)`\*\*\n", b5)
    for j in range(1, len(blocks) - 1, 2):
        b5_sub[os.path.basename(blocks[j].rstrip("/"))] = blocks[j + 1]
    for k in (ENGINE, CC):
        if k not in b5_sub:
            MISSING.append("B5 sub-block for %s" % k)
    die_if_missing()
    DEN = {}
    for k in (ENGINE, CC):
        s = b5_sub[k]
        DEN[k] = dict(
            den=reqi(s, r"\((\d+) denied", "%s denied tool_results" % k),
            notden=reqi(s, r"denied, (\d+) not denied", "%s non-denied tool_results" % k),
            only_den=req(s, r"\| denied only \| (.+?) \|", "%s denied-only keys" % k),
            only_all=req(s, r"\| not-denied only \| (.+?) \|",
                         "%s not-denied-only keys" % k))

    # ---------------- B6 ----------------
    b6 = split_h2(bas).get("B6 — S86 harness result objects")
    if b6 is None:
        fatal("missing field: B6 section")
    arms = {}
    for m in re.finditer(r"\| `(\w+)` \| (\d+) \| (\d+) \| ([\d.]+) \| \d+ \| "
                         r"\d+ \| \d+ \| \d+ \| \d+ \|", b6):
        arms[m.group(1)] = dict(n=track(m.group(2)), err=track(m.group(3)),
                                cost=track(m.group(4)))
    if not arms:
        MISSING.append("B6 arm rows")
    b6_n = req(b6, r"\| \*\*total\*\* \| \*\*(\d+)\*\*", "B6 total results")
    b6_cost = req(b6, r"\| \*\*total\*\* \| \*\*\d+\*\* \| \*\*\d+\*\* \| "
                      r"\*\*([\d.]+)\*\*", "B6 total cost")
    b6_x1 = req(b6, r"sum of `total_cost_usd` = ([\d.]+)", "B6 cross-check tcu")
    b6_x2 = req(b6, r"sum of `modelUsage\.costUSD` = ([\d.]+)", "B6 cross-check cost")
    b6_diff = req(b6, r"\(difference ([\d.-]+)\)", "B6 cross-check difference")
    b6_model = req(b6, r"\| \*\*all arms\*\* \| `([^`]+)` \|", "B6 model id")
    die_if_missing()

    E, C = P[ENGINE], P[CC]
    lpr_e = track("%.3f" % (E["asst_lines"] / float(E["deduped"])))
    lpr_c = track("%.3f" % (C["asst_lines"] / float(C["deduped"])))
    den_tot = track(DEN[ENGINE]["den"] + DEN[CC]["den"])
    notden_tot = track(DEN[ENGINE]["notden"] + DEN[CC]["notden"])
    hits_tot = track(E["ln_hits"] + C["ln_hits"])
    for r_ in LITERAL_RUNS:
        ALLOWED_RUNS.add(r_)

    # ---------------- section 8 rows ----------------
    DROWS = [
        ("D1", "The B5 verdict was written in advance — a fixed paragraph naming "
               "keys before the script had read any data.",
         "review", "Review, before the first run.",
         "Verdict computed from the keys actually found, plus a non-lexical "
         "key-set differential; the interpretive sentence kept but demoted and "
         "labelled \"author's reading\"."),
        ("D2", "The conservation check could not fail on real data: the total and "
               "the per-session sums came from the same loop.",
         "review", "Review.",
         "Kept as fixture control C4; the real-data check replaced by the phase-A "
         "cross-check, with C5 proving that one can fail."),
        ("D3", "The context-limit string scan read conversation text, in a project "
               "that discusses context windows constantly.",
         "review", "Review.",
         "Paths under `$.message.content` excluded structurally, their match count "
         "reported as one number, and the remaining text-bearing paths named as "
         "still in scope."),
        ("D4", "The corpus was live and grew during measurement.",
         "instrument", "**Instrument** — the phase-A cross-check, on its first real run.",
         "Frozen sha-manifested snapshot, verified before and after the runs."),
        ("D5", "A lexical name test produced a false candidate, `allowedPrompts`, "
               "from a deprecated JSON-schema property.",
         "instrument", "**Instrument** — the verdict refused to conclude and named "
         "the candidate for inspection.",
         "Structural schema-subtree skip, with C7 and C8 proving it removes the "
         "schema key and keeps a real one."),
        ("D6", "Marker *events* were reported as marker *lines*, so one line "
               "carrying three markers counted three times.",
         "instrument", "**Instrument** — the table showed three rows at one timestamp.",
         "Both units reported, keyed by (file, line number); a line is a hit when "
         "any of its markers meets the reading."),
        ("D7", "The nearest-preceding-response carry crossed file boundaries, so a "
               "marker on a file's first lines could inherit another session's "
               "context and be pushed over the bar.",
         "review", "Review of the patch, before it ran.",
         "Carry reset at every file boundary, plus a session guard at render; no "
         "row in the final table was affected."),
    ]
    n_review = track(sum(1 for r_ in DROWS if r_[2] == "review"))
    n_instr = track(sum(1 for r_ in DROWS if r_[2] == "instrument"))
    n_drows = track(len(DROWS))
    review_ids = ", ".join(r_[0] for r_ in DROWS if r_[2] == "review")
    instr_ids = ", ".join(r_[0] for r_ in DROWS if r_[2] == "instrument")

    # ---------------- render ----------------
    L = []
    a = L.append
    a("# WS3.1 — routing baseline: what Claude Code transcripts can and cannot measure")
    a("")
    a("Measurement record for WS3.1. Every figure below is parsed from the frozen "
      "snapshot artefacts by the generator in `scripts/phase_c.py`; no number was "
      "typed. The generator exits non-zero naming any field it cannot parse rather "
      "than printing a default, and a closing assertion fails on any run of three or "
      "more digits in this document that the generator did not emit.")
    a("")
    a("**Status: measurement only.** Nothing here is a decision. Section 7 states "
      "requirements this baseline implies for ADR-029; they are labelled derived "
      "requirements and they authorise nothing.")
    a("")

    # ---- 1
    a("## 1. Provenance")
    a("")
    a("| item | value |")
    a("|---|---|")
    a("| snapshot | `%s` |" % snap)
    a("| snapshot taken (UTC) | `%s` |" % stamp)
    a("| `MANIFEST.sha256` sha256 | `%s` |" % man_sha)
    a("| manifest entries | %d |" % man_lines)
    a("| `.jsonl` files under manifest | %d |" % man_jsonl)
    a("| `schema_inventory.py` sha256 | `%s` |" % script_sha["schema_inventory.py"])
    a("| `baseline_b.py` sha256 | `%s` |" % script_sha["baseline_b.py"])
    a("")
    a("**Metrics come from a frozen copy, not from the live directories, and the "
      "reason is a measured failure.** The first phase B run measured the live "
      "corpus. Its cross-check against phase A **failed on `%s`**: phase B counted "
      "%d deduped responses against phase A's %d, a delta of **%s**, verdict "
      "**%s**. This session writes to that directory, so it grew between the two "
      "runs. The cross-check is what caught it — nothing else in the instrument "
      "would have noticed, and every token total would have inherited the "
      "disagreement. After freezing, the same check reads delta %s / %s on `%s` and "
      "%s / %s on `%s`. The manifest verified `OK` before the runs and again after "
      "them."
      % (ENGINE, live_ours, live_pa, live_delta, live_verdict,
         E["delta"], E["verdict"], ENGINE, C["delta"], C["verdict"], CC))
    a("")

    # ---- 2
    a("## 2. Instrument and controls")
    a("")
    a("All eight controls run on synthetic fixtures the instrument writes itself, "
      "before any metric is computed. A failure suppresses the metrics rather than "
      "annotating them.")
    a("")
    a("| control | verdict | what it proves |")
    a("|---|---|---|")
    a("| %s | **%s** | Lines sharing a `message.id` collapse to one response: the "
      "deduped input sum is %d where a per-line sum would report %d. |"
      % (ctrl["C1"][0], ctrl["C1"][1], c1_dedup, c1_perline))
    a("| %s | **%s** | Streaming lines carry growing `output_tokens`; the "
      "last-line-in-file-order rule reports the final value, not the per-line sum "
      "of %d. |" % (ctrl["C2"][0], ctrl["C2"][1], c2_perline))
    a("| %s | **%s** | The Bash-form classifier keys on the leading token: a quoted "
      "`cd` inside an `echo` is not a `cd` form, and `git -C` is not one either. |"
      % (ctrl["C3"][0], ctrl["C3"][1]))
    a("| %s | **%s** | Per-session token sums add up to the project total, field by "
      "field. Fixture only — see the note below. |" % (ctrl["C4"][0], ctrl["C4"][1]))
    a("| %s | **%s** | The phase-A cross-check *can* fail: dropping one id from a "
      "fixture makes it report MISMATCH. |" % (ctrl["C5"][0], ctrl["C5"][1]))
    a("| %s | **%s** | The phase-A reference was parsed from phase A's own report, "
      "not typed into the instrument. |" % (ctrl["C6"][0], ctrl["C6"][1]))
    a("| %s | **%s** | A key buried in a JSON-schema subtree does not reach the "
      "observability test: %d schema-key occurrence(s) skipped in the fixture. |"
      % (ctrl["C7"][0], ctrl["C7"][1], c7_skipped))
    a("| %s | **%s** | The schema skip does not blind the test: a real top-level "
      "`approvalGranted` key on a user line still becomes a candidate. |"
      % (ctrl["C8"][0], ctrl["C8"][1]))
    a("")
    a("**C4 is a fixture control only.** On real data the project total and the "
      "per-session sums are computed in the same loop, so the identity cannot fail "
      "and asserting it would prove nothing. The real-data check is the phase-A "
      "cross-check instead, and C5 exists to show that one can fail.")
    a("")
    a("**C5's reported blind spot, stated because the control reports it itself:** "
      "the cross-check %s. Two runs disagreeing only in how many lines a response "
      "was split across still agree on the id count and read MATCH." % c5_blind)
    a("")

    # ---- 3
    a("## 3. Baseline")
    a("")
    a("| measure | `%s` | `%s` |" % (ENGINE, CC))
    a("|---|---|---|")
    a("| `.jsonl` files | %d | %d |" % (E["files"], C["files"]))
    a("| bytes | %d | %d |" % (E["bytes"], C["bytes"]))
    a("| non-blank lines | %d | %d |" % (E["lines"], C["lines"]))
    a("| JSON parse failures | %d | %d |" % (E["parse_fail"], C["parse_fail"]))
    a("| window, first to last timestamp | %s → %s | %s → %s |"
      % (E["first_ts"], E["last_ts"], C["first_ts"], C["last_ts"]))
    a("| distinct `sessionId` values | %d | %d |" % (E["sessions"], C["sessions"]))
    a("| sessions carrying at least one response | %d | %d |"
      % (E["sessions_with_resp"], C["sessions_with_resp"]))
    a("| assistant lines | %d | %d |" % (E["asst_lines"], C["asst_lines"]))
    a("| deduped API responses | %d | %d |" % (E["deduped"], C["deduped"]))
    a("| lines per response (computed) | %s | %s |" % (lpr_e, lpr_c))
    a("| responses lacking a `message.id` | %d | %d |" % (E["noid"], C["noid"]))
    a("| input tokens | %d | %d |" % (E["input"], C["input"]))
    a("| cache_creation input tokens | %d | %d |" % (E["cc"], C["cc"]))
    a("| cache_read input tokens | %d | %d |" % (E["cr"], C["cr"]))
    a("| output tokens | %d | %d |" % (E["out"], C["out"]))
    a("| all four, primary rule | %d | %d |" % (E["all4"], C["all4"]))
    a("| all four, sensitivity rule (per-field max) | %d | %d |"
      % (E["all4_sens"], C["all4_sens"]))
    a("| primary-vs-sensitivity gap | %s | %s |" % (E["all4_pct"], C["all4_pct"]))
    a("| pooled re-read share — **PROXY** | %s | %s |" % (E["reread"], C["reread"]))
    a("| pooled cache-creation share | %s | %s |" % (E["ccshare"], C["ccshare"]))
    a("| prompt-token denominator | %d | %d |" % (E["den"], C["den"]))
    a("| max context peak | %d | %d |" % (E["peak"], C["peak"]))
    a("| sessions with peak > %s | %d | %d |" % (E["thr200"], E["gt200"], C["gt200"]))
    a("| sessions with peak > %s | %d | %d |" % (E["thr500"], E["gt500"], C["gt500"]))
    a("| `compact_boundary` lines | %d | %d |" % (E["compact"], C["compact"]))
    a("")
    a("The **primary-vs-sensitivity gap is %s on `%s` and %s on `%s`** — the "
      "per-field maximum across lines sharing an id and the last line in file order "
      "agree on every field in both corpora. The choice of dedup *rule* is therefore "
      "not load-bearing here; the choice to dedup **at all** is. At %s and %s lines "
      "per response, a per-line sum would inflate every token figure."
      % (E["all4_pct"], ENGINE, C["all4_pct"], CC, lpr_e, lpr_c))
    a("")
    a("**Re-read share is labelled a PROXY and must stay labelled.** It is "
      "`cache_read / (input + cache_creation + cache_read)` — the share of prompt "
      "tokens served from cache. It cannot distinguish a cache hit on material the "
      "model used from a hit on material it ignored, and a TTL expiry is "
      "indistinguishable from genuinely new context. It is not a measure of how much "
      "context was re-read.")
    a("")
    # Negative control for the closing assertion. S87_NEGCTL=1 appends a figure
    # the generator never emitted; the assertion must catch it and write nothing.
    if os.environ.get("S87_NEGCTL") == "1":
        a("Typed figure 48213.")
        a("")
    a("### Bash calls by leading form")
    a("")
    a("| form | `%s` calls / denials / rate | `%s` calls / denials / rate |"
      % (ENGINE, CC))
    a("|---|---|---|")
    for form in ("cd-compound", "cd-semicolon", "git -C", "bare git",
                 "python3/heredoc", "other"):
        e, c = E["forms"][form], C["forms"][form]
        a("| `%s` | %s / %s / %s | %s / %s / %s |"
          % (form, e[0], e[1], e[2], c[0], c[1], c[2]))
    a("| **total** | **%s / %s / %s** | **%s / %s / %s** |"
      % (E["forms_total"][0], E["forms_total"][1], E["forms_total"][2],
         C["forms_total"][0], C["forms_total"][1], C["forms_total"][2]))
    a("")
    a("A denial is a joined `tool_result` with `is_error=true` whose text opens with "
      "a permission-refusal prefix. Denial rates differ by form — `git -C` reads %s "
      "on `%s` and %s on `%s`, against `cd-compound`'s %s and %s — but these are "
      "observational rates over unequal populations, not an experiment, and by 5a a "
      "denial rate is not a prompt rate. Section 6 is the experiment."
      % (E["forms"]["git -C"][2], ENGINE, C["forms"]["git -C"][2], CC,
         E["forms"]["cd-compound"][2], C["forms"]["cd-compound"][2]))
    a("")

    # ---- 4
    a("## 4. S86 harness results")
    a("")
    a("| arm | results | `is_error` | sum `total_cost_usd` |")
    a("|---|---|---|---|")
    for arm in sorted(arms):
        a("| `%s` | %s | %s | %s |"
          % (arm, arms[arm]["n"], arms[arm]["err"], arms[arm]["cost"]))
    a("| **total** | **%s** | | **%s** |" % (b6_n, b6_cost))
    a("")
    a("Cross-check: sum of `total_cost_usd` = %s, sum of `modelUsage.costUSD` = %s, "
      "**difference %s**, all on model `%s`. **Costs are read from the tool's own "
      "fields; no price is applied anywhere in this instrument.** `num_turns` is "
      "carried as informational only — it counts harness turns, which is not a unit "
      "of work and is not comparable across arms."
      % (b6_x1, b6_x2, b6_diff, b6_model))
    a("")

    # ---- 5
    a("## 5. Observability findings")
    a("")
    a("### 5a. Approved permission prompts are NOT observable")
    a("")
    a("Computed verdict, verbatim from the instrument:")
    a("")
    a("> %s" % b5_verdict)
    a("")
    a("Evidence, in the order it was obtained:")
    a("")
    a("- **The lexical test alone was not enough.** A first run flagged "
      "`allowedPrompts` as a candidate. Inspection disposed of it: both occurrences "
      "sit on `attachment` lines at `$.attachment.entries[0].input_schema."
      "properties.allowedPrompts`, are a tool's *parameter schema* rather than a "
      "record of any event, and the schema's own description reads \"Deprecated: no "
      "longer used.\"")
    a("- **The fix is structural, not a name exclusion.** Key collection skips any "
      "path running through a JSON-schema subtree — a dict reached via `properties` "
      "whose parent carries `type`, or anything under `input_schema`. **%d key "
      "occurrences were skipped** (`%s` %d, `%s` %d). No key name is special-cased, "
      "and C7 and C8 show the rule removes the schema key while keeping a real one."
      % (b5_skipped, ENGINE, b5_skip_eng, CC, b5_skip_cc))
    a("- **A non-lexical test agrees.** Comparing the key sets of lines carrying a "
      "denied `tool_result` against lines carrying a non-denied one: on `%s` the "
      "denied-only keys are %s and the not-denied-only keys are %s; on `%s` they are "
      "%s and %s. Nothing appears on the allowed side and nowhere else."
      % (ENGINE, DEN[ENGINE]["only_den"], DEN[ENGINE]["only_all"],
         CC, DEN[CC]["only_den"], DEN[CC]["only_all"]))
    a("- **Denials are the only prompt signal, so the denial count has no "
      "denominator.** Across both corpora %d denied and %d non-denied `tool_result`s "
      "were joined (`%s`: %d / %d; `%s`: %d / %d). An approved prompt and a call that "
      "never prompted are byte-indistinguishable, so no approval rate, prompt rate "
      "or approval-to-denial ratio can be computed from these transcripts at all."
      % (den_tot, notden_tot, ENGINE, DEN[ENGINE]["den"], DEN[ENGINE]["notden"],
         CC, DEN[CC]["den"], DEN[CC]["notden"]))
    a("- %d key names matching `permission` / `approv` / `prompt` survive the schema "
      "skip across both projects, and none is a per-call permission outcome."
      % b5_keys)
    a("")
    a("### 5b. Context-limit hits")
    a("")
    a("Pre-registered reading, fixed before the markers were read: an event is a "
      "context-limit hit only if the context of its nearest preceding deduped "
      "response is **>= %s**, or its `error` type/code names *context* or *length*. "
      "A **line** counts as a hit when any of its markers meets that reading. "
      "Everything else is an other API event." % bar)
    a("")
    a("| corpus | marker events (hit / other / total) | distinct marker lines "
      "(hit / other / total) |")
    a("|---|---|---|")
    a("| `%s` | %d / %d / %d | %d / %d / %d |"
      % (ENGINE, E["ev_hits"], E["ev_other"], E["ev_total"],
         E["ln_hits"], E["ln_other"], E["ln_total"]))
    a("| `%s` | %d / %d / %d | %d / %d / %d |"
      % (CC, C["ev_hits"], C["ev_other"], C["ev_total"],
         C["ln_hits"], C["ln_other"], C["ln_total"]))
    a("")
    a("**`%s`: %d hit line.** `%s`, markers %s, preceding context %d — a margin of "
      "**%s tokens, %s** over the bar. The hit fired on the **size arm only**: the "
      "error code names neither context nor length, so had the bar been set %d "
      "tokens higher this line would read as an other API event. One line, one arm, "
      "a %s margin."
      % (ENGINE, E["ln_hits"], hit_file, hit_markers, hit_ctx, hit_marg, hit_pct,
         hit_marg_plus, hit_pct))
    a("")
    a("**`%s`: not observable.** The instrument's own line: *%s*" % (CC, cc_notobs))
    a("")
    a("**Corroboration, recorded outside the rule.** The same session carries a "
      "`compact_boundary` after the error. That is consistent with a context-limit "
      "event and is **not** part of the pre-registered reading, so it adds no hit; "
      "the field-level marker summary reads `%s`. It is written down here so a later "
      "reader can see what was available and what was counted." % marked_by)
    a("")
    a("**This is not linked to the S86 event on record.** The hit line is a "
      "context-limit-shaped event found in the snapshot by the stated rule. No "
      "attempt was made to match it to the S86 incident, and none should be read "
      "into it.")
    a("")

    # ---- 6
    bare_no = all(r[2].lower().startswith("no prompt") for r in gc_bare)
    dashc_yes = all(r[2].upper().startswith("PROMPT") for r in gc_dashC)
    cwd_yes = bool(gc_cwd_rows) and all(r[2].upper().startswith("PROMPT")
                                        for r in gc_cwd_rows)

    a("## 6. RUN — Block 4, the `git -C` prompt experiment")
    a("")
    a("**RUN. Operator-observed, %s.** The question is narrow: **does `-C` break "
      "the built-in read-only no-prompt match?** A bare read-only `git` invocation "
      "is matched as read-only and does not prompt; whether the same command with a "
      "`-C <path>` prefix is still matched was unknown, and 5a establishes that the "
      "transcripts cannot answer it — approvals leave no record, so a low denial "
      "rate is equally consistent with \"never prompted\" and with \"prompted and "
      "approved every time\". This is **not** a `git -C` versus `cd` comparison."
      % gc_obs)
    a("")
    a("Session and cadence, as observed: **%s**. Working directory `%s`; "
      "**n=%s per command**." % (gc_sess, gc_cwd, gc_reps))
    a("")
    a("| # | command | prompted? |")
    a("|---|---|---|")
    for num, cmd, verdict in gc_rows:
        tag = "" if " -C " in cmd else " — bare control"
        a("| %s | `%s`%s | %s |" % (num, cmd, tag, verdict))
    a("")
    if bare_no and dashc_yes and cwd_yes:
        a("**The `-C` form broke the built-in no-prompt match — even when `-C` named "
          "the working directory the session was already in** (row %s, `%s`, which "
          "changes nothing about which directory git reads and still prompted, while "
          "the bare forms did not): the prefix itself is what falls outside the "
          "match, not the directory it points at. **n=%s per command** in a single "
          "session, so this is an existence result and not a rate."
          % (gc_cwd_rows[0][0], gc_cwd, gc_reps))
    else:
        a("**The observed pattern does not separate the forms**, so no such finding "
          "is stated: bare forms all-no-prompt is `%s`, `-C` forms all-prompted is "
          "`%s`, and the cwd-naming `-C` row prompted is `%s`. Read the table."
          % (bare_no, dashc_yes, cwd_yes))
    a("")
    a("Every cell above is read from `gitC_result.json`, the operator's own record. "
      "The generator **aborts** if that file is absent, so an unrun experiment "
      "cannot render as a run one with an empty column.")
    a("")

    # ---- 7
    a("## 7. Derived requirements for ADR-029")
    a("")
    a("**Derived requirements, not decisions.** Each follows from a measurement "
      "above. None is adopted here; ADR-029 decides.")
    a("")
    a("| # | requirement | the measurement it follows from |")
    a("|---|---|---|")
    a("| R1 | Permission prompts must be logged going forward, at the point the "
      "prompt is raised and resolved. | 5a: approvals are byte-invisible, so no "
      "retrospective analysis of prompting can ever be run on transcripts. |")
    a("| R2 | Context-limit events must be logged going forward, with the context "
      "size at the moment of the failure. | 5b: both corpora together yield %d hit "
      "line, identified by a margin of %s tokens on a single arm. |"
      % (hits_tot, hit_marg))
    a("| R3 | Any token figure must be deduplicated by `message.id`. | Section 3: "
      "%s and %s assistant lines per response; a per-line sum inflates every "
      "field. |" % (lpr_e, lpr_c))
    a("| R4 | Any live corpus is measured from a sha-manifested snapshot, verified "
      "before and after the run. | Section 1: the live run failed its cross-check by "
      "%s responses because the corpus grew mid-measurement. |" % live_delta)
    a("")

    # ---- 8
    a("## 8. Instrument defects caught during WS3.1")
    a("")
    a("For the Assumption Register at doc-close. Every row is a defect in the "
      "*instrument*, not in the system it measures.")
    a("")
    a("| # | defect | how it was caught | fix |")
    a("|---|---|---|---|")
    for did, defect, _kind, caught, fix in DROWS:
        a("| %s | %s | %s | %s |" % (did, defect, caught, fix))
    a("")
    a("Of %d defects, **%d were caught by review** (%s) and **%d by running an "
      "instrument** (%s)." % (n_drows, n_review, review_ids, n_instr, instr_ids))
    a("")
    a("Two patterns are worth separating, because they need different remedies. "
      "**D2, D3 and D7 are checks that could not fail for the reason they named** — "
      "D2 could not fail at all, D3 measured the wrong text, and D7 would have "
      "measured the wrong session. Those are fixed by changing what the check reads. "
      "**D1 is not that.** Its check ran correctly; the conclusion had simply been "
      "written before any measurement existed to support it, so the output would "
      "have been the same whatever the data said. That is fixed by computing the "
      "verdict, which is what turned D5 from a silent pass into a named candidate "
      "for inspection.")
    a("")
    a("---")
    a("")
    a("*Generated by `scripts/phase_c.py` from `%s`. Instruments copied to "
      "`scripts/`; no transcript, snapshot or report file is committed.*" % snap_name)
    a("")

    die_if_missing()
    doc = "\n".join(L)

    # ---------------- closing assertion: nothing was typed ----------------
    untracked = {}
    for m in re.finditer(r"\d{3,}", doc):
        r_ = m.group(0)
        if r_ not in ALLOWED_RUNS:
            untracked.setdefault(r_, 0)
            untracked[r_] += 1
    if untracked:
        sys.stderr.write("FATAL: %d untracked digit run(s) in the rendered "
                         "document; no document written.\n" % len(untracked))
        for r_, n in sorted(untracked.items(), key=lambda x: -x[1]):
            sys.stderr.write("  untracked digit run: %s (x%d)\n" % (r_, n))
        sys.exit(1)

    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    for p in SRC_SCRIPTS + [os.path.abspath(__file__)]:
        dst = os.path.join(SCRIPTS_DIR, os.path.basename(p))
        shutil.copy2(p, dst)
        src_h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        dst_h = hashlib.sha256(open(dst, "rb").read()).hexdigest()
        if src_h != dst_h:
            fatal("sha256 mismatch after copy: %s (%s != %s)" % (dst, src_h, dst_h))

    with open(DOC, "w") as fh:
        fh.write(doc)
    sys.stderr.write("wrote %s (%d bytes)\n" % (DOC, os.path.getsize(DOC)))
    sys.stderr.write("digit-run assertion: %d distinct runs in doc, all tracked\n"
                     % len(set(re.findall(r"\d{3,}", doc))))
    for p in SRC_SCRIPTS + [os.path.abspath(__file__)]:
        dst = os.path.join(SCRIPTS_DIR, os.path.basename(p))
        sys.stderr.write("copy sha OK  %-22s %s\n"
                         % (os.path.basename(p),
                            hashlib.sha256(open(dst, "rb").read()).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
