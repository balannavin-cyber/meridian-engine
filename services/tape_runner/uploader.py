"""Upload queue (amendment A-3: the key is write-only, no HeadObject/GetObject anywhere).

take file -> stream md5 + sha256 -> put_object(ContentMD5, SSE-S3) -> delete local ONLY if the
response ETag equals the local md5 hex. Mismatch or exception -> file kept, retried with
exponential backoff 1, 2, 4 ... 60 s, attempts counted. Each success is appended to
manifest/<date>.ndjson (local, kept). The key is the path relative to the spool root.
"""
import base64
import hashlib
import json
import os
import threading

from . import config
from .clock import NS


def file_digests(path):
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            md5.update(chunk)
            sha.update(chunk)
            size += len(chunk)
    return md5, sha.hexdigest(), size


class Uploader:
    def __init__(self, s3, bucket, spool_dir, manifest_dir, log=None):
        self.s3 = s3
        self.bucket = bucket
        self.spool = spool_dir
        self.manifest_dir = manifest_dir
        self.log = log or (lambda msg: None)
        self._lock = threading.RLock()
        self._q = {}  # path -> {"attempts": n, "next_ns": t}
        self.counts = {}  # key prefix -> {"ok", "retried", "failed_attempts"}
        self.uploaded_keys = set()  # every key in the local manifests: never written to again
        if os.path.isdir(manifest_dir):
            for name in os.listdir(manifest_dir):
                if name.endswith(".ndjson"):
                    for row in self.manifest_lines(name[: -len(".ndjson")]):
                        self.uploaded_keys.add(row["key"])

    def key_for(self, path):
        return os.path.relpath(path, self.spool).replace(os.sep, "/")

    def _c(self, key):
        return self.counts.setdefault(key.split("/", 1)[0], {"ok": 0, "retried": 0, "failed_attempts": 0})

    def enqueue(self, path):
        with self._lock:
            self._q.setdefault(path, {"attempts": 0, "next_ns": 0})

    def pending(self):
        with self._lock:
            return sorted(self._q)

    def process_once(self, now_ns):
        """Attempt every due file once. Returns the number uploaded."""
        done = 0
        with self._lock:  # snapshot only: the writer thread may enqueue while an upload runs
            due = sorted(p for p, st in self._q.items() if st["next_ns"] <= now_ns)
        for path in due:
            if self._upload(path, now_ns):
                done += 1
        return done

    def _upload(self, path, now_ns):
        st = self._q[path]
        key = self.key_for(path)
        st["attempts"] += 1
        try:
            md5, sha_hex, size = file_digests(path)
            md5_hex = md5.hexdigest()
            with open(path, "rb") as body:
                resp = self.s3.put_object(
                    Bucket=self.bucket, Key=key, Body=body, ServerSideEncryption="AES256",
                    ContentMD5=base64.b64encode(md5.digest()).decode("ascii"))
            etag = str((resp or {}).get("ETag", "")).strip('"')
            if etag == md5_hex:
                self._record(key, size, md5_hex, sha_hex, st["attempts"], now_ns)
                self.uploaded_keys.add(key)
                os.unlink(path)
                c = self._c(key)
                c["ok"] += 1
                if st["attempts"] > 1:
                    c["retried"] += 1
                with self._lock:
                    del self._q[path]
                return True
            reason = "ETAG_MISMATCH"
        except Exception as exc:  # noqa: BLE001 -- any failure keeps the file
            reason = type(exc).__name__
        self._c(key)["failed_attempts"] += 1
        delay = min(config.BACKOFF_CAP_S, 2 ** (st["attempts"] - 1))
        st["next_ns"] = now_ns + delay * NS
        self.log("UPLOAD_RETRY key=%s attempt=%d reason=%s next_in=%ss" % (key, st["attempts"], reason, delay))
        return False

    def _record(self, key, size, md5_hex, sha_hex, attempts, now_ns):
        os.makedirs(self.manifest_dir, exist_ok=True)
        day = key.split("/")[1] if key.count("/") >= 2 else "undated"
        line = json.dumps({"key": key, "bytes": size, "md5": md5_hex, "sha256": sha_hex,
                           "attempts": attempts, "uploaded_ns": now_ns}, separators=(",", ":"))
        with open(os.path.join(self.manifest_dir, day + ".ndjson"), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def manifest_lines(self, day):
        path = os.path.join(self.manifest_dir, day + ".ndjson")
        if not os.path.exists(path):
            return []
        out = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    out.append(json.loads(line))
        return out

    def is_taken(self, path):
        return self.key_for(path) in self.uploaded_keys

    def failed_by_prefix(self):
        out = {}
        for p in self.pending():
            k = self.key_for(p).split("/", 1)[0]
            out[k] = out.get(k, 0) + 1
        return out

    # -- production thread -------------------------------------------------------------
    def run(self, clock, stop_event, period_s=0.5):
        while not stop_event.is_set():
            try:
                self.process_once(clock.now_ns())
            except Exception as exc:  # noqa: BLE001
                self.log("UPLOADER_ERROR %s" % type(exc).__name__)
            stop_event.wait(period_s)
