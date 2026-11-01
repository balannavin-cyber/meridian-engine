"""Per-symbol 5-minute segment files (amendment A-1).

spool/<SYMBOL>/<IST date>/seg_<HHMM>.ndjson.part  -- plain, line per record, flushed each tick
  on close -> seg_<HHMM>.ndjson.gz (gzip mtime=0, no filename: deterministic bytes, so a re-upload
  after a crash is byte-identical), fsync, .part removed, path handed to ``on_closed``.

A record's segment is floor(recv_ns -> IST, 5 min) (plan D-6: the box receive clock). Rotation
fires on the first record of a different segment, or on ``tick(now)`` crossing a boundary so a
quiet symbol's file still closes on time. Every opened file starts with a ``rotate`` ctl record.
The upload key is the path relative to the spool root (minus ``.part``, plus ``.gz``).
"""
import gzip
import os
import shutil

from . import clock as clk
from .serialize import ctl_record, dumps

PART = ".ndjson.part"
GZ = ".ndjson.gz"


def gzip_file(src, dst):
    """Deterministic gzip of src into dst (via dst.tmp + rename); returns dst."""
    tmp = dst + ".tmp"
    with open(src, "rb") as fin, open(tmp, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as gz:
            shutil.copyfileobj(fin, gz, 1024 * 1024)
        raw.flush()
        os.fsync(raw.fileno())
    os.replace(tmp, dst)
    return dst


class _Open:
    __slots__ = ("seg_ns", "fh", "path")

    def __init__(self, seg_ns, fh, path):
        self.seg_ns = seg_ns
        self.fh = fh
        self.path = path


class SegmentWriter:
    def __init__(self, spool_dir, symbols, on_closed, process_start_ns=0, on_bytes=None):
        self.spool = spool_dir
        self.symbols = list(symbols)
        self.on_closed = on_closed
        self.process_start_ns = process_start_ns
        self.on_bytes = on_bytes or (lambda n: None)
        self._open = {}
        self._last_seg = {}

    # -- paths -------------------------------------------------------------------------
    def part_path(self, sym, seg_ns):
        d = os.path.join(self.spool, sym, clk.ist_date(seg_ns))
        return os.path.join(d, "seg_" + clk.seg_label(seg_ns) + PART)

    @staticmethod
    def _needs_rotate(cur_seg_ns, seg_ns):
        return cur_seg_ns != seg_ns

    # -- writing -----------------------------------------------------------------------
    def _line(self, cur, rec):
        data = dumps(rec) + "\n"
        cur.fh.write(data)
        self.on_bytes(len(data))

    def _ensure(self, sym, seg_ns, now_ns):
        cur = self._open.get(sym)
        if cur is not None and self._needs_rotate(cur.seg_ns, seg_ns):
            self.close(sym)
            cur = None
        if cur is None:
            path = self.part_path(sym, seg_ns)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            fh = open(path, "a", encoding="utf-8")
            cur = _Open(seg_ns, fh, path)
            self._open[sym] = cur
            prev = self._last_seg.get(sym)
            self._line(cur, ctl_record(
                "rotate", now_ns, seg=clk.seg_label(seg_ns),
                prev_seg=clk.seg_label(prev) if prev is not None else None,
                process_start_ns=self.process_start_ns))
        return cur

    def write(self, sym, rec, recv_ns):
        cur = self._ensure(sym, clk.seg_start_ns(recv_ns), recv_ns)
        self._line(cur, rec)

    def write_all(self, rec, recv_ns):
        for sym in self.symbols:
            self.write(sym, rec, recv_ns)

    def tick(self, now_ns):
        seg = clk.seg_start_ns(now_ns)
        for sym in list(self._open):
            if self._needs_rotate(self._open[sym].seg_ns, seg):
                self.close(sym)

    def flush(self):
        for cur in self._open.values():
            cur.fh.flush()

    def close(self, sym):
        cur = self._open.pop(sym, None)
        if cur is None:
            return None
        cur.fh.flush()
        os.fsync(cur.fh.fileno())
        cur.fh.close()
        self._last_seg[sym] = cur.seg_ns
        gz = gzip_file(cur.path, cur.path[: -len(PART)] + GZ)
        os.unlink(cur.path)
        self.on_closed(gz)
        return gz

    def close_all(self):
        for sym in list(self._open):
            self.close(sym)

    def abort_close(self):
        """Spool cap: flush and close .part files WITHOUT gzip and without deleting anything."""
        for sym in list(self._open):
            cur = self._open.pop(sym)
            try:
                cur.fh.flush()
                os.fsync(cur.fh.fileno())
            finally:
                cur.fh.close()

    # -- recovery ----------------------------------------------------------------------
    def recover(self, now_ns):
        """Start-up: .part of an earlier segment -> gzip; .part of the current segment is left for
        append. Returns every finished file (.gz and session objects) to enqueue."""
        cur_seg_paths = {self.part_path(s, clk.seg_start_ns(now_ns)) for s in self.symbols}
        ready = []
        for dirpath, _dirs, files in os.walk(self.spool):
            for name in sorted(files):
                path = os.path.join(dirpath, name)
                if name.endswith(".tmp"):
                    continue
                if name.endswith(PART):
                    if path in cur_seg_paths:
                        continue
                    ready.append(gzip_file(path, path[: -len(PART)] + GZ))
                    os.unlink(path)
                else:
                    ready.append(path)
        return sorted(set(ready))


def spool_bytes(spool_dir):
    total = 0
    for dirpath, _dirs, files in os.walk(spool_dir):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total
