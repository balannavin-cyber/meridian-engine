"""Per-symbol 5-minute segment files (amendment A-1).

spool/<SYMBOL>/<IST date>/seg_<HHMM>.ndjson.part  -- plain, line per record, flushed each tick
  on close -> seg_<HHMM>.ndjson.gz (gzip mtime=0, no filename: deterministic bytes, so a re-upload
  after a crash is byte-identical), fsync, .part removed, path handed to ``on_closed``.

A record's segment is floor(recv_ns -> IST, 5 min) (plan D-6: the box receive clock). Rotation
fires on the first record of a different segment, or on ``tick(now)`` crossing a boundary so a
quiet symbol's file still closes on time. Every opened file starts with a ``rotate`` ctl record.
The upload key is the path relative to the spool root (minus ``.part``, plus ``.gz``).

Immutability (review 2026-11-01, finding 2):
- a segment this writer has closed is NEVER reopened. A record that arrives late (its recv time is
  in a segment already closed, or older than the open one) is written to the current open segment,
  or to the segment after the last closed one; it keeps its own ``recv_ns``, so nothing is lost and
  replay can re-sort by it;
- a finished ``.gz`` is NEVER overwritten. If ``seg_HHMM.ndjson.gz`` already exists locally, or its
  key is already uploaded (``taken``), the file is written as ``seg_HHMM_r1.ndjson.gz`` (r2, ...).
  The one exception is a byte-identical file (a crash between gzip and the .part removal re-gzips
  the same .part): that is the same object, not a new one.
"""
import gzip
import hashlib
import os
import shutil

from . import clock as clk
from .serialize import ctl_record, dumps

PART = ".ndjson.part"
GZ = ".ndjson.gz"


def _seg_ns():
    from . import config
    return config.SEG_SECONDS * clk.NS


def _gzip_into(src, path):
    with open(src, "rb") as fin, open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as gz:
            shutil.copyfileobj(fin, gz, 1024 * 1024)
        raw.flush()
        os.fsync(raw.fileno())


def gzip_file(src, dst):
    """Deterministic gzip of src into dst (via dst.tmp + rename); returns dst."""
    tmp = dst + ".tmp"
    _gzip_into(src, tmp)
    os.replace(tmp, dst)
    return dst


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def finish_part(part, taken=None):
    """Gzip a closed .part into a NEW .gz (never overwriting one) and remove the .part.
    Returns the .gz path to upload."""
    taken = taken or (lambda path: False)
    base = part[: -len(PART)]
    tmp = base + GZ + ".tmp"
    _gzip_into(part, tmp)
    new_md5 = _md5(tmp)
    n = 0
    dst = base + GZ
    while os.path.exists(dst) or taken(dst):
        if os.path.exists(dst) and _md5(dst) == new_md5:   # same bytes: a re-gzip after a crash
            os.unlink(tmp)
            os.unlink(part)
            return dst
        n += 1
        dst = "%s_r%d%s" % (base, n, GZ)
    os.replace(tmp, dst)
    os.unlink(part)
    return dst


class _Open:
    __slots__ = ("seg_ns", "fh", "path")

    def __init__(self, seg_ns, fh, path):
        self.seg_ns = seg_ns
        self.fh = fh
        self.path = path


class SegmentWriter:
    def __init__(self, spool_dir, symbols, on_closed, process_start_ns=0, on_bytes=None, taken=None):
        self.spool = spool_dir
        self.symbols = list(symbols)
        self.on_closed = on_closed
        self.process_start_ns = process_start_ns
        self.on_bytes = on_bytes or (lambda n: None)
        self.taken = taken or (lambda path: False)
        self._open = {}
        self._last_seg = {}       # sym -> seg_ns of the last segment closed by this writer
        self.late_records = 0

    # -- paths -------------------------------------------------------------------------
    def part_path(self, sym, seg_ns):
        d = os.path.join(self.spool, sym, clk.ist_date(seg_ns))
        return os.path.join(d, "seg_" + clk.seg_label(seg_ns) + PART)

    @staticmethod
    def _needs_rotate(cur_seg_ns, seg_ns):
        return cur_seg_ns != seg_ns

    def _target(self, sym, seg_ns):
        """Never reopen a closed segment: a record whose segment is at or before the last closed
        one goes to the segment after it."""
        last = self._last_seg.get(sym)
        if last is not None and seg_ns <= last:
            self.late_records += 1
            return last + _seg_ns()
        return seg_ns

    # -- writing -----------------------------------------------------------------------
    def _line(self, cur, rec):
        data = dumps(rec) + "\n"
        cur.fh.write(data)
        self.on_bytes(len(data))

    def _ensure(self, sym, seg_ns, now_ns):
        cur = self._open.get(sym)
        if cur is not None and seg_ns < cur.seg_ns:
            self.late_records += 1
            return cur                       # late record: stays in the newer open segment
        seg_ns = self._target(sym, seg_ns)
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
            if seg > self._open[sym].seg_ns and self._needs_rotate(self._open[sym].seg_ns, seg):
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
        last = self._last_seg.get(sym)
        self._last_seg[sym] = cur.seg_ns if last is None else max(last, cur.seg_ns)
        gz = finish_part(cur.path, self.taken)
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
        """Start-up: .part of an earlier segment -> gzip (never overwriting a .gz); .part of the
        current segment is left for append. Returns every finished file (.gz and session objects)
        to enqueue."""
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
                    ready.append(finish_part(path, self.taken))
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
