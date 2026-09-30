---
paths:
  - "**/*.py"
  - "patch_*.py"
  - "scripts/**/*.py"
---

# Python writers and patch scripts

Relocated verbatim from `CLAUDE.md` at Session 86 (ADR-028). Rule text is
unchanged; only its location moved.

- ❌ Building patch anchors from PowerShell/terminal console output. Console rendering collapses blank lines; multi-line anchors spanning them fail `count==0`. Use a `repr()` dump of the on-disk bytes. (Session 71.)
- ❌ Reading a Python source file with `Path.read_text(encoding='utf-8')` then calling `ast.parse()` on it when the file has a UTF-8 BOM — `ast.parse` rejects U+FEFF with `invalid non-printable character`. Always use `read_bytes() + decode('utf-8-sig')` in patch scripts. (Session 11 extension — v1 of F3 patch caught this correctly and aborted.)
- ❌ Writing a patched file back with `Path.write_text(text, encoding=...)` on Windows when the original file has LF line endings — `write_text` translates `\n → \r\n` on output, silently converting the file to CRLF and producing a noisy `git diff` showing every line modified. Always use `write_bytes(text.encode(enc))` for symmetric byte handling. v3 of F3 patch is the canonical pattern. (Session 11 extension.)
- ❌ Writing a multi-file patch script whose idempotency gate is written per file-entry and omitted for some of them. The ungated entries fall through to the anchor check, which cannot find text its own successful edit removed — so a re-run reports **ABORT on a document that is correct**, and that abort is indistinguishable from a real one. Session 80: `patch_s80_claude_md.py` gated CLAUDE.md, CURRENT.md and session_log.md but not the Decision Index; `patch_s80_correct_td_s69_new_1_status.py` gated the Deployment Topology but not the Assumption Register. **Both documents were correct**, and the verification sweep that found them produced two wrong diagnoses in succession before the files themselves were read — first that `anchor count == 0` was a pass, then that it proved the edit never landed. Only the content settles it. **Every file-entry gets its own gate, and the script's closing summary is computed from the per-file results — never a literal.** Same session, same class: `patch_s80_correct_topology_not_updated.py` printed *"All three files clean. Re-run with --apply."* immediately after all three files printed *Skipping*, because that line was a constant and not a computation. A summary that cannot report failure is the CAN FIRE / CANNOT FIRE rule applied to a patch script's own stdout. (Session 80, doc-close verification sweep.)
- ✅ **A green run against the wrong artefact proves nothing, and looks identical to success.** Session 71 produced five: box tests against unpushed code (twice), a commit of a patch script whose apply step never ran (`git add` on an unmodified file is a silent no-op), a stale patch file on disk re-running old anchors, and a `2>&1 | grep` that swallowed a traceback. **Gate every deploy on an artefact identity check** — byte count, hash, or an idempotency marker — not on the command having exited zero.
- ✅ **A recency floor is calibrated against the CONSUMER's cadence, never the writer's.** ADR-023 D1's 15-minute default was derived from the GEX writer's 5-minute cycle. The floor binds `generate_pine_overlay.py`, which runs pre-market or post-close — shipping 15 would have made pin/accel permanently absent. This is the same error shape as Guard 3 (two samples generalised to a rule) and `OB_MIN_MOVE_PCT` (single-bar body measured against a 5-bar definition): **the easy-to-reason-about quantity substituted for the one that actually binds.**
**Bug B6 → Rule 26:** Patch scripts MUST be line-ending agnostic. After three sessions of patches, files accumulate mixed line endings — Session 14 found `build_trade_signal_local.py` with 1039 CRLF + 87 bare-LF lines. Single-EOL `replace()` fails when the anchor crosses a mixed-EOL boundary. Canonical pattern:

```python
src_raw = TARGET.read_bytes().decode("utf-8-sig")
crlf = src_raw.count("\r\n")
bare_lf = src_raw.count("\n") - crlf
write_eol = "\r\n" if crlf >= bare_lf else "\n"

# Match in LF-space (anchors are LF in patch source)
src_lf = src_raw.replace("\r\n", "\n")
patched_lf = src_lf.replace(OLD, NEW)

# Restore predominant EOL on write
patched_out = patched_lf.replace("\n", write_eol) if write_eol == "\r\n" else patched_lf
TARGET.write_bytes(patched_out.encode("utf-8"))
```

This pattern also normalises mixed line endings as a side effect — file becomes uniformly EOL-consistent post-patch.
**Bug B7 → Rule 27:** Before writing endpoint code that references module-level attributes (`sys.executable`, `os.path`, etc.), grep imports in target file at module level. Imports inside functions don't expose those names to top-level / endpoint scope. Session 14 ENH-84 endpoint used `sys.executable` but `merdian_signal_dashboard.py` only had `import sys as _sys` deep inside `build()` — endpoint scope had no `sys` reference. Hotfix replaced with literal `"python"`.

```bash
# Quick check before referencing module attributes in patches:
grep -n "^import\|^from " target_file.py
```
**Bug B8 → Rule 20:** Rule 16 (`hist_spot_bars_5m.bar_ts` use `replace(tzinfo=None)` instead of `astimezone(IST)`) is **era-conditional, not universal**. The era boundary is **2026-04-07**.

| Era | Storage convention | Correct handling |
|---|---|---|
| **Pre-04-07** (legacy ingest) | Bars stored as IST clock-time labelled `+00:00` (TD-029 root cause) | `bar_ts.replace(tzinfo=None)` then filter by `09:15 ≤ time ≤ 15:30` (Rule 16 verbatim) |
| **Post-04-07** (current writer) | Bars stored as true UTC | `bar_ts.astimezone(IST_TZ)` then filter by `09:15 ≤ time ≤ 15:30` |

Applying Rule 16 verbatim to post-04-07 data drops most of the day. Concretely: `replace(tzinfo=None)` on a UTC-stored bar produces a UTC clock-time. Filtering UTC clock-time to 09:15-15:30 IST keeps only bars in the UTC 09:15-10:00 window (= IST 14:45-15:30, the last 45 min of session) → ~9 of ~76 in-session bars per day = **27.5% bar coverage** false alarm.

**Canonical era-aware helper** (use this in any script that needs in-session 5m bars across the era boundary):

```python
from datetime import time, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
ERA_BOUNDARY = "2026-04-07"  # exclusive: dates < this use Rule 16; >= this use astimezone

def in_session_filter(bar_ts, trade_date_str):
    """Returns True if bar is inside 09:15-15:30 IST, era-aware."""
    if trade_date_str < ERA_BOUNDARY:
        clock = bar_ts.replace(tzinfo=None).time()  # Rule 16 (legacy)
    else:
        clock = bar_ts.astimezone(IST).time()       # Post-04-07 (true UTC)
    return time(9, 15) <= clock <= time(15, 30)
```
- **`equity_intraday_last` freshness is measured on `ts`, never `created_at` (S59).** The table is upsert-written by `refresh_equity_intraday_last.py`; `ts` moves on every upsert, `created_at` is row-birth and static. Every breadth-reference freshness check (incl. the `eod_health_check` REFERENCE FRESHNESS guard, commit `6b58587`) reads `ts`. Anchoring on `created_at` false-alarms STALE forever. Codified §D.25.1.
- **Daily ICT PDH/PDL are written unconditionally; weekly PDH/PDL stay proximity-filtered (S59, commit `2b40a4b`).** `detect_daily_zones` emits exactly one PDH + one PDL per run, so filtering the fresh pair against the prior-day CLOSE (the pre-open `current_spot`) wrongly dropped down-day PDLs as "already breached"; the daily block no longer calls `filter_breached_zones`. Weekly keeps the filter — `detect_weekly_zones` loops the lookback and emits many PDH/PDL needing the nearest-2 prune. `build_ict_htf_zones.py` is a **Local** Task-Scheduler job, not AWS.
- **Every signal-feeding reader carries the ADR-018 D2 recency floor — re-audited S61.** Two more floorless readers surfaced and were fixed: `_fetch_options_flow` (ENH-02/04 ±3/4/5 modifiers had run off a ~24-day-stale `options_flow_snapshots` row since S49 — TD-S61-NEW-1, `MERDIAN_FLOW_RECENCY_FLOOR_MIN`=15) and the new `_fetch_basis_context` (`MERDIAN_BASIS_RECENCY_FLOOR_MIN`=15). Basis context is display-only (context-not-gate per S37) — surfaced into `signal_snapshots.raw`, no confidence modifier.
