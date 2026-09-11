#!/usr/bin/env python3
"""
S77 — F-68 remediation, operator decision D2.
ADR-004 Amendment C (§15): valid_from is the CONFIRMING BAR'S CLOSE.

Two files, seven edits:

  ict_primitives.py
    A1  Bar gains  ts_close: Optional[datetime] = None      (:62-70)
    A2  module-level _bar_close_ts(b) helper, before Primitive
    A3  BULL_FVG  valid_from=nxt.ts       -> _bar_close_ts(nxt)      (:192)
    A4  BEAR_FVG  valid_from=nxt.ts       -> _bar_close_ts(nxt)      (:214)
    A5  OB        valid_from=disp.event_ts-> _bar_close_ts(bars[disp_idx])  (:354)
    A6  detect_order_blocks docstring: stop asserting both readings at once

  build_ict_primitives.py
    B1  _reduce_ohlc sets ts_close = last bucket bar's ts + 1min      (:380-389)

DELIBERATELY NOT TOUCHED — Event.event_ts at ict_primitives.py :270, :529, :546.
detect_order_blocks keys bar_idx and fvg_by_ts on exact equality with
disp.event_ts (:323, :347). Re-anchoring events to close while `bars` stay
stamped at open makes BOTH lookups return None and OB detection silently emits
zero rows. Amendment C's event class stays unimplemented and is filed as a TD.

ts_close is last_bar.ts + 1min, NOT last_bar.ts. 1m bars are stamped at their
OPEN, so the bare ts would leave 59s of lookahead -- F-68 one order of
magnitude down, invisible for the same reason the original was.

Canon-v3: read_bytes, utf-8-sig, EOL measured not assumed, ALL count==1 anchors
evaluated before any write, ast.parse gate on both files, _PRE_S77 backups,
temp + os.replace, post-write verify from disk. Dry-run default.

    python3 patch_s77_f68_ts_close.py            # dry run
    python3 patch_s77_f68_ts_close.py --apply
    python3 patch_s77_f68_ts_close.py --smoke    # behavioural proof, post-apply
"""

import argparse
import ast
import hashlib
import os
import sys
import tempfile

F_DET = "ict_primitives.py"
F_BLD = "build_ict_primitives.py"

MARKER = "_bar_close_ts"

# ── A1 ───────────────────────────────────────────────────────────────────────
A1_OLD = '''    """OHLCV bar. ts is tz-aware. Volume is optional (NSE/BSE indices have no vol)."""
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0'''

A1_NEW = '''    """OHLCV bar. ts is tz-aware. Volume is optional (NSE/BSE indices have no vol)."""
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    # ADR-004 Amendment C (S77) / audit finding F-68: the instant this bar
    # CLOSED. ts is the bar's OPEN. Set by build_ict_primitives._reduce_ohlc
    # from the bucket's last 1m bar; None on raw 1m bars, where _bar_close_ts()
    # supplies ts + 1min. frozen=True, so a defaulted field is a compatible add
    # and every other construction site takes the default untouched.
    ts_close: Optional[datetime] = None'''

# ── A2 ───────────────────────────────────────────────────────────────────────
A2_OLD = '''@dataclass
class Primitive:
    """
    Maps to public.ict_primitives row (less id+created_at which are server-side).'''

A2_NEW = '''def _bar_close_ts(b: Bar) -> datetime:
    """
    The instant `b` closed. ADR-004 Amendment C (S15); audit finding F-68.

    Aggregated bars carry ts_close, set in build_ict_primitives._reduce_ohlc
    from the last 1m bar of the bucket. Raw 1m bars do not, and close one
    minute after their stamp.

    Bars are stamped at their OPEN, so using b.ts as a confirmation anchor is
    precisely the lookahead F-68 records: D ~ 6h15m, W ~ 5 days, H <= 59 min,
    M5 <= 5 min. Every formation-anchored outcome column inherited it.
    """
    return b.ts_close if b.ts_close is not None else b.ts + timedelta(minutes=1)


@dataclass
class Primitive:
    """
    Maps to public.ict_primitives row (less id+created_at which are server-side).'''

# ── A3 / A4 ──────────────────────────────────────────────────────────────────
A3_OLD = '''                    primitive_type="BULL_FVG",
                    direction="BULL",
                    source_bar_ts=mid.ts,
                    valid_from=nxt.ts,'''
A3_NEW = '''                    primitive_type="BULL_FVG",
                    direction="BULL",
                    source_bar_ts=mid.ts,
                    valid_from=_bar_close_ts(nxt),'''

A4_OLD = '''                    primitive_type="BEAR_FVG",
                    direction="BEAR",
                    source_bar_ts=mid.ts,
                    valid_from=nxt.ts,'''
A4_NEW = '''                    primitive_type="BEAR_FVG",
                    direction="BEAR",
                    source_bar_ts=mid.ts,
                    valid_from=_bar_close_ts(nxt),'''

# ── A5 ───────────────────────────────────────────────────────────────────────
A5_OLD = '''            source_bar_ts=ob_bar.ts,
            valid_from=disp.event_ts,'''
A5_NEW = '''            source_bar_ts=ob_bar.ts,
            valid_from=_bar_close_ts(bars[disp_idx]),'''

# ── A6 ───────────────────────────────────────────────────────────────────────
A6_OLD = "    valid_from = displacement bar ts (OB is confirmed at displacement close)."
A6_NEW = '''    valid_from = the displacement bar's CLOSE (ADR-004 Amendment C; F-68).
    Formerly disp.event_ts, which is that bar's OPEN -- up to one full timeframe
    of lookahead. Events keep their bucket-start event_ts deliberately: it is the
    join key for bar_idx (:323) and fvg_by_ts (:347), and moving it empties this
    detector silently.'''

# ── B1 ───────────────────────────────────────────────────────────────────────
B1_OLD = '''    bucket_bars_sorted = sorted(bucket_bars, key=lambda x: x.ts)
    return Bar(
        ts=bucket_ts,
        open=bucket_bars_sorted[0].open,
        high=max(b.high for b in bucket_bars_sorted),
        low=min(b.low for b in bucket_bars_sorted),
        close=bucket_bars_sorted[-1].close,
    )'''

B1_NEW = '''    bucket_bars_sorted = sorted(bucket_bars, key=lambda x: x.ts)
    return Bar(
        ts=bucket_ts,
        open=bucket_bars_sorted[0].open,
        high=max(b.high for b in bucket_bars_sorted),
        low=min(b.low for b in bucket_bars_sorted),
        close=bucket_bars_sorted[-1].close,
        # ADR-004 Amendment C / F-68. The source 1m bar is stamped at its OPEN,
        # so the bucket closes one minute after the last bar's stamp. Using the
        # bare stamp would leave 59s of lookahead at every timeframe.
        ts_close=bucket_bars_sorted[-1].ts + timedelta(minutes=1),
    )'''

EDITS = {
    F_DET: [
        ("A1 Bar.ts_close field", A1_OLD, A1_NEW),
        ("A2 _bar_close_ts helper", A2_OLD, A2_NEW),
        ("A3 BULL_FVG valid_from", A3_OLD, A3_NEW),
        ("A4 BEAR_FVG valid_from", A4_OLD, A4_NEW),
        ("A5 OB valid_from", A5_OLD, A5_NEW),
        ("A6 OB docstring", A6_OLD, A6_NEW),
    ],
    F_BLD: [
        ("B1 _reduce_ohlc ts_close", B1_OLD, B1_NEW),
    ],
}


def _load(path):
    raw = open(path, "rb").read()
    return raw, raw.decode("utf-8-sig")


def _report(path, raw):
    crlf = raw.count(b"\r\n")
    print(f"  {path}")
    print(f"    bytes {len(raw)}  lines {raw.count(chr(10).encode())}  "
          f"CRLF {crlf}  BOM {raw.startswith(chr(0xfeff).encode('utf-8'))}")
    print(f"    sha256 {hashlib.sha256(raw).hexdigest()}")
    return crlf


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="behavioural proof only; runs against current files")
    args = ap.parse_args()

    if args.smoke:
        return smoke()

    fail, projected = [], {}

    print("== baseline ==")
    for path in (F_DET, F_BLD):
        if not os.path.isfile(path):
            print(f"ABORT: missing {path}", file=sys.stderr)
            return 2
        raw, text = _load(path)
        crlf = _report(path, raw)
        if crlf:
            fail.append(f"{path}: {crlf} CRLF; this patch assumes LF")
        if MARKER in text and path == F_DET:
            print(f"\nALREADY APPLIED: {MARKER} present in {path}. Nothing to do.")
            return 0

    # timedelta must already be imported in both files
    for path in (F_DET, F_BLD):
        _, text = _load(path)
        if "timedelta" not in text:
            fail.append(f"{path}: 'timedelta' not imported; B1/A2 would NameError")

    print("\n== anchors (count==1 required, all checked before any write) ==")
    for path, edits in EDITS.items():
        raw, text = _load(path)
        out = text
        for name, old, new in edits:
            n = text.count(old)
            print(f"  {'OK ' if n == 1 else 'BAD'}  {path}  {name}: {n}")
            if n != 1:
                fail.append(f"{path} {name}: expected 1 match, found {n}")
            else:
                out = out.replace(old, new, 1)
        projected[path] = (raw, out)

    if fail:
        print("\nABORT — nothing written:", file=sys.stderr)
        for f in fail:
            print(f"  - {f}", file=sys.stderr)
        print("\nSuspect the assertion before the edit. Anchors in this script are"
              "\ntranscript-derived; re-derive from disk, do not widen to force a match.",
              file=sys.stderr)
        return 1

    print("\n== ast.parse gate ==")
    for path, (raw, out) in projected.items():
        try:
            ast.parse(out, filename=path)
            print(f"  OK   {path}")
        except SyntaxError as e:
            print(f"  BAD  {path}: {e}", file=sys.stderr)
            return 1

    print("\n== projected ==")
    for path, (raw, out) in projected.items():
        nb = out.encode("utf-8")
        print(f"  {path}: {len(raw)} -> {len(nb)} ({len(nb)-len(raw):+d} bytes), "
              f"lines {raw.count(chr(10).encode())} -> {nb.count(chr(10).encode())}, "
              f"CRLF {nb.count(chr(13).encode()+chr(10).encode())}")
        print(f"    sha256 {hashlib.sha256(nb).hexdigest()}")

    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply, then --smoke.")
        return 0

    for path, (raw, out) in projected.items():
        bak = path + "_PRE_S77"
        if not os.path.exists(bak):
            open(bak, "wb").write(raw)
            print(f"\nbackup {bak}")
        nb = out.encode("utf-8")
        d = os.path.dirname(os.path.abspath(path))
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(nb)
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    print("\n== verified from disk ==")
    ok = True
    for path, (_raw, out) in projected.items():
        v = open(path, "rb").read()
        match = v == out.encode("utf-8")
        ok &= match
        _report(path, v)
        print(f"    match {'OK' if match else 'MISMATCH'}")
    print("\nNow run:  python3 patch_s77_f68_ts_close.py --smoke")
    return 0 if ok else 1


def smoke() -> int:
    """Behavioural proof. Parsing only proves it compiles."""
    from datetime import datetime, timedelta, timezone
    sys.path.insert(0, os.getcwd())
    import ict_primitives as ip
    import build_ict_primitives as bip

    base = datetime(2026, 4, 6, 3, 45, tzinfo=timezone.utc)
    bars = [ip.Bar(ts=base + timedelta(minutes=i), open=100.0 + i, high=101.0 + i,
                   low=99.0 + i, close=100.5 + i) for i in range(120)]

    print("== smoke ==")
    fails = []

    for tf, width in (("M5", 5), ("H", 60)):
        agg = bip.aggregate(bars, tf)
        if not agg:
            fails.append(f"{tf}: aggregate returned nothing")
            continue
        b = agg[0]
        got = b.ts_close
        want = b.ts + timedelta(minutes=width)
        status = "OK " if got == want else "BAD"
        if got != want:
            fails.append(f"{tf}: ts_close {got} != ts+{width}min {want}")
        print(f"  {status} {tf}: ts={b.ts.time()} ts_close={got.time() if got else None} "
              f"(expected {want.time()})")

    raw1m = ip.Bar(ts=base, open=1.0, high=1.0, low=1.0, close=1.0)
    got = ip._bar_close_ts(raw1m)
    want = base + timedelta(minutes=1)
    print(f"  {'OK ' if got == want else 'BAD'} raw 1m fallback: {got.time()} "
          f"(expected {want.time()})")
    if got != want:
        fails.append("raw 1m fallback wrong")

    # The assertion that actually proves F-68 is closed: every emitted FVG must
    # be anchored at its confirming bar's close, never its open.
    agg = bip.aggregate(bars, "M5")
    fvgs = ip.detect_fvgs(agg, "NIFTY", "M5")
    print(f"  -- detect_fvgs emitted {len(fvgs)} primitive(s) on synthetic bars")
    by_ts = {b.ts: b for b in agg}
    for p in fvgs:
        nxt_ts = datetime.fromisoformat(p.metadata["bar_plus_1_ts"])
        nxt = by_ts.get(nxt_ts)
        if nxt is None:
            fails.append(f"FVG {p.source_bar_ts}: bar_plus_1 not in aggregate")
            continue
        if p.valid_from == nxt.ts:
            fails.append(f"FVG {p.source_bar_ts}: valid_from is the OPEN — F-68 LIVE")
        elif p.valid_from != nxt.ts_close:
            fails.append(f"FVG {p.source_bar_ts}: valid_from {p.valid_from} "
                         f"!= confirming close {nxt.ts_close}")

    if fails:
        print("\nSMOKE FAILED:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\nSMOKE PASS — aggregated ts_close correct at M5 and H, raw-1m fallback "
          "correct, every emitted FVG anchored at its confirming bar's close.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
