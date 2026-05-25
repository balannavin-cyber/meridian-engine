#!/usr/bin/env python3
"""
fix_td038_exit_at_ist_display.py

TD-038: dashboard EXIT AT label shows UTC, not IST.

Background:
  In merdian_signal_dashboard.py card(), the existing code converts
  `_ts_raw` (UTC) to IST via fromisoformat + astimezone, producing
  `sig_ts` in IST. The "Signal at" label uses `sig_ts[11:16]` correctly.

  But `exit_ts` is computed elsewhere (in build()) as:
      exit_ts = (st + timedelta(minutes=30)).isoformat()
  where `st` is UTC. So `exit_ts` is a UTC isoformat string. The
  "EXIT AT" label slices `exit_ts[11:16]` — that's UTC hours/minutes,
  not IST. Off by 5h30m on the displayed exit time.

  Note: the COUNTDOWN element uses `data-exit="{exit_ts}"` and
  `new Date(exit_ts)` in JS, which handles UTC->local correctly via
  the browser. So the live countdown digits are correct. ONLY the
  static label is wrong. Operator could trust wrong number.

Fix:
  Convert exit_ts to IST the same way sig_ts is converted, just before
  the exit_html block uses it. One small block in the exit_html section.

Idempotency: aborts if "TD-038" marker present.
Rule 5: ast.parse() before write.
Encoding: utf-8-sig read, utf-8 write, line-ending agnostic.
"""
import ast
import pathlib
import sys

TARGET = pathlib.Path(r"C:\GammaEnginePython\merdian_signal_dashboard.py")

# Anchor (LF form). The exit_html assignment uses exit_ts[11:16] for the
# EXIT AT label, but exit_ts is a UTC isoformat string at that point.
ANCHOR = (
    '    if exit_ts and allowed:\n'
    '        exit_html = (\n'
    '            f\'<div class="xb"><div class="xt">EXIT SIGNAL \\u2014 T+30m FIXED</div>\'\n'
    '            f\'<div class="xr"><span class="lb">Signal at</span><span class="vl">{sig_ts[11:16]} IST</span></div>\'\n'
    '            f\'<div class="xr"><span class="lb">EXIT AT</span><span class="vl xtm">{exit_ts[11:16]} IST</span></div>\'\n'
    '            f\'<div class="cd" id="cd-{sym}" data-exit="{exit_ts}">--:--</div></div>\'\n'
    '        )'
)

REPLACE = (
    '    # TD-038 fix: convert UTC exit_ts to IST for the static label.\n'
    '    # exit_ts is a UTC isoformat string from build() (st + 30min where\n'
    '    # st is UTC). The countdown JS handles UTC->local via Date(), but\n'
    '    # the static "EXIT AT hh:mm IST" label was slicing UTC hh:mm.\n'
    '    # Mirror the same conversion already applied to sig_ts above.\n'
    '    try:\n'
    '        from datetime import datetime as _dt38\n'
    '        from zoneinfo import ZoneInfo as _ZI38\n'
    '        _exit_dt = _dt38.fromisoformat((exit_ts or "").replace("Z","+00:00"))\n'
    '        exit_ts_ist = _exit_dt.astimezone(_ZI38("Asia/Kolkata")).strftime("%Y-%m-%dT%H:%M:%S+05:30")\n'
    '    except Exception:\n'
    '        exit_ts_ist = exit_ts or ""\n'
    '    if exit_ts and allowed:\n'
    '        exit_html = (\n'
    '            f\'<div class="xb"><div class="xt">EXIT SIGNAL \\u2014 T+30m FIXED</div>\'\n'
    '            f\'<div class="xr"><span class="lb">Signal at</span><span class="vl">{sig_ts[11:16]} IST</span></div>\'\n'
    '            f\'<div class="xr"><span class="lb">EXIT AT</span><span class="vl xtm">{exit_ts_ist[11:16]} IST</span></div>\'\n'
    '            f\'<div class="cd" id="cd-{sym}" data-exit="{exit_ts}">--:--</div></div>\'\n'
    '        )'
)


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 1

    src_raw = TARGET.read_bytes().decode("utf-8-sig")

    crlf = src_raw.count("\r\n")
    bare_lf = src_raw.count("\n") - crlf
    write_eol = "\r\n" if crlf >= bare_lf else "\n"
    print(f"Line endings: CRLF={crlf} bare-LF={bare_lf} -> write {('CRLF' if write_eol == chr(13)+chr(10) else 'LF')}")

    if "TD-038" in src_raw:
        print("ERROR: TD-038 marker already present — aborting (idempotent guard).")
        return 1

    src_lf = src_raw.replace("\r\n", "\n")

    c = src_lf.count(ANCHOR)
    if c == 0:
        print("ERROR: anchor not found", file=sys.stderr)
        print(f"  First 120 chars of expected anchor: {ANCHOR[:120]!r}", file=sys.stderr)
        return 1
    if c != 1:
        print(f"ERROR: anchor found {c} times (expected 1)", file=sys.stderr)
        return 1
    print("anchor: matched once OK")

    patched_lf = src_lf.replace(ANCHOR, REPLACE)

    try:
        ast.parse(patched_lf)
    except SyntaxError as e:
        print(f"ERROR: ast.parse failed: {e}", file=sys.stderr)
        return 1

    print("ast.parse: PASS")

    if write_eol == "\r\n":
        patched_out = patched_lf.replace("\n", "\r\n")
    else:
        patched_out = patched_lf

    if dry_run:
        print("[DRY-RUN] No file written.")
        print("\nWould add IST conversion for exit_ts before the exit_html block.")
        print("Would change exit_ts[11:16] -> exit_ts_ist[11:16] in EXIT AT label only.")
        print("Countdown JS data-exit unchanged (Date() handles UTC->local correctly).")
        return 0

    TARGET.write_bytes(patched_out.encode("utf-8"))
    print(f"TD-038 patch applied to: {TARGET.name}")
    print("  Static EXIT AT label now displays IST (matches Signal at).")
    print("  Countdown JS unchanged.")
    print("  Idempotency key: 'TD-038'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
