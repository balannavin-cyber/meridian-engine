"""Tape live L2 runner, Phase A: the sources (docs/tape/L2_live_runner_plan.md sections 2 and 6). READ ONLY.

The ONLY module that starts a process. Two interfaces, so the runner core never knows which it has:

  object source   list(prefix) -> [ObjInfo(key, size, etag, last_modified)],  get(key, dest)
  chain source    read_page(symbol, cursor, until, limit) -> [row dicts],  count_upto(symbol, cursor, until) -> int

  S3Source          the `aws` CLI, two argv shapes (list-objects-v2, get-object), fixed lists, never a shell. Credentials come only
                    from the instance role: the child environment is an allowlist and points the shared credential and config
                    files at the null device.
  PsqlChainSource   `psql`, one argv shape, the SQL on stdin, every value a -v variable. The connection fields reach the child
                    through its environment only; nothing is ever placed in an argument list.
  LocalDirSource    a recorded day replayed on a schedule (tests, rehearsal): same interface.

Every external call has a timeout. A failure raises SourceError carrying a category and nothing else: no child stderr, no argv and
no exception text is ever kept, so no secret can travel in an error. RUN is the single seam the tests replace.
"""
import hashlib
import json
import os
import shutil
import subprocess
import urllib.parse
from collections import namedtuple
from datetime import datetime, timezone

from services.tape_live import wall_source

LIST_TIMEOUT_S = 30
GET_TIMEOUT_S = 60
PSQL_TIMEOUT_S = 15
AWS_TIMEOUTS = ["--cli-read-timeout", "10", "--cli-connect-timeout", "5"]
PGOPTIONS = "-c default_transaction_read_only=on -c statement_timeout=8000"
SSL_MODES = ("require", "verify-ca", "verify-full")

ObjInfo = namedtuple("ObjInfo", "key size etag last_modified")


class SourceError(Exception):
    """A failed read. The category is the whole message."""

    def __init__(self, category):
        Exception.__init__(self, category)
        self.category = category


def default_run(argv, env, stdin, timeout):
    """-> (returncode, stdout, stderr). Never a shell; a timeout is rc 124, a missing program rc 127."""
    try:
        p = subprocess.run(argv, input=stdin, capture_output=True, timeout=timeout, env=env, shell=False, check=False)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, b"", b"timeout"
    except OSError:
        return 127, b"", b"exec"


RUN = default_run


def classify(rc, err, other):
    """A category from a return code and stderr; the text itself is dropped here."""
    low = (err or b"").decode("utf-8", "replace").lower()
    if rc == 124 or "timed out" in low or "timeout" in low:
        return "timeout"
    if "accessdenied" in low or "authentication" in low or "password" in low or "credentials" in low or "forbidden" in low:
        return "auth"
    if "could not connect" in low or "connection" in low or "endpoint" in low or "could not resolve" in low:
        return "connect"
    return other


def _call(argv, env, stdin, timeout, other):
    try:
        rc, out, err = RUN(argv, env, stdin, timeout)
    except Exception:  # noqa: BLE001 - any failure of the call is a category, never its text
        raise SourceError("other") from None
    if rc != 0:
        raise SourceError(classify(rc, err, other))
    return out


# ------------------------------------------------------------------------------------------- secrets and environments
def parse_dsn(dsn):
    """The database connection string -> the PG* fields of the child's environment. The error never carries the string."""
    try:
        u = urllib.parse.urlsplit(dsn)
        mode = (urllib.parse.parse_qs(u.query).get("sslmode") or ["require"])[0]
        if u.scheme not in ("postgres", "postgresql") or not u.hostname or not u.username or u.password is None \
                or mode not in SSL_MODES:
            raise ValueError("shape")
        return {"PGHOST": u.hostname, "PGPORT": str(u.port or 5432), "PGUSER": urllib.parse.unquote(u.username),
                "PGPASSWORD": urllib.parse.unquote(u.password),
                "PGDATABASE": u.path.lstrip("/") or "postgres", "PGSSLMODE": mode}
    except ValueError:
        raise ValueError("the database connection string is malformed") from None


def pg_env(base, parts):
    """The psql child environment: an allowlist from base, the connection fields, and the read-only session options."""
    env = dict((k, base[k]) for k in ("PATH", "LANG", "SystemRoot") if k in base)
    env.update(parts)
    env["PGOPTIONS"] = PGOPTIONS
    env["PGCONNECT_TIMEOUT"] = "5"
    env["PGAPPNAME"] = "tape-live-runner"
    return env


def aws_env(base):
    """The aws child environment: an allowlist, no key variables, credential and config files pointed at the null device."""
    env = dict((k, base[k]) for k in ("PATH", "LANG", "HOME", "USERPROFILE", "SystemRoot") if k in base)
    env["AWS_DEFAULT_REGION"] = base.get("AWS_DEFAULT_REGION", "eu-north-1")
    env["AWS_SHARED_CREDENTIALS_FILE"] = os.devnull
    env["AWS_CONFIG_FILE"] = os.devnull
    return env


def scrub(text, secrets=()):
    """text with every known secret value, any user:password@ URI, JWT-shaped or access-key-shaped run replaced; at most 200 chars."""
    import re
    j = "".join
    t = str(text)
    for s in secrets:
        if s:
            t = t.replace(s, "***")
    for rx in (j([r"[a-z][a-z0-9+.-]*", ":", "//", r"[^\s/:@]+:[^\s/@]+@"]),
               j(["ey", r"J[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"]),
               j([r"\b(AK", r"IA|AS", r"IA)[0-9A-Z]{16}\b"])):
        t = re.sub(rx, "***", t)
    return t[:200]


# ------------------------------------------------------------------------------------------- object sources
class LocalDirSource:
    """A recorded day, each file visible from vis[key] (epoch seconds; absent = always). clock.now() is the simulated time."""

    def __init__(self, raw, day, vis, clock):
        self.raw, self.day, self.vis, self.clock = raw, day, dict(vis), clock
        self._etag = {}

    def _path(self, key):
        return os.path.join(self.raw, *key.split("/"))

    def list(self, prefix):
        d = self._path(prefix.rstrip("/"))
        if not os.path.isdir(d):
            return []
        now, out = self.clock.now(), []
        for n in sorted(os.listdir(d)):
            key = prefix + n
            v = self.vis.get(key, 0.0)
            if v > now or not os.path.isfile(os.path.join(d, n)):
                continue
            if key not in self._etag:
                with open(os.path.join(d, n), "rb") as fh:
                    self._etag[key] = hashlib.md5(fh.read()).hexdigest()
            out.append(ObjInfo(key, os.path.getsize(os.path.join(d, n)), self._etag[key],
                               datetime.fromtimestamp(v, timezone.utc).isoformat()))
        return out

    def get(self, key, dest):
        if self.vis.get(key, 0.0) > self.clock.now() or not os.path.isfile(self._path(key)):
            raise SourceError("other")
        if os.path.exists(dest):
            os.remove(dest)
        try:
            os.link(self._path(key), dest)           # same volume: no second copy of a recorded day; the source is never opened for write
        except OSError:
            shutil.copyfile(self._path(key), dest)


class S3Source:
    """The bucket through the aws CLI (read verbs only). filter_future (simulated clock only) hides objects whose LastModified is
    after the simulated now, so a rehearsal against recorded objects sees them in their original order."""

    def __init__(self, bucket, base_env=None, clock=None, filter_future=False):
        self.bucket, self.clock, self.filter_future = bucket, clock, filter_future
        self.env = aws_env(os.environ if base_env is None else base_env)

    def list(self, prefix):
        argv = ["aws", "s3api", "list-objects-v2", "--bucket", self.bucket, "--prefix", prefix, "--output", "json"] + AWS_TIMEOUTS
        out = _call(argv, self.env, None, LIST_TIMEOUT_S, "other")
        try:
            doc = json.loads(out.decode("utf-8")) if out.strip() else {}
            items = doc.get("Contents") or []
            res = [ObjInfo(c["Key"], int(c["Size"]), str(c["ETag"]).strip('"'), str(c["LastModified"])) for c in items]
        except (ValueError, KeyError, TypeError, AttributeError):
            raise SourceError("other") from None
        if self.filter_future:
            now = self.clock.now()
            res = [o for o in res if datetime.fromisoformat(o.last_modified).timestamp() <= now]
        return res

    def get(self, key, dest):
        argv = ["aws", "s3api", "get-object", "--bucket", self.bucket, "--key", key] + AWS_TIMEOUTS + [dest]
        _call(argv, self.env, None, GET_TIMEOUT_S, "other")


# ------------------------------------------------------------------------------------------- chain source
class PsqlChainSource:
    """The snapshot queries of wall_source through psql. parts: the PG* fields from parse_dsn."""

    def __init__(self, parts, day, base_env=None):
        self.day = day
        self.env = pg_env(os.environ if base_env is None else base_env, parts)

    def _psql(self, sql, variables):
        argv = ["psql", "-X", "-q", "-t", "--csv", "-v", "ON_ERROR_STOP=1"]
        for name, value in variables:
            argv += ["-v", "%s=%s" % (name, value)]
        argv += ["-f", "-"]
        return _call(argv, self.env, sql.encode("utf-8"), PSQL_TIMEOUT_S, "sql").decode("utf-8", "replace")

    @staticmethod
    def _vars(sym, cursor, until, day=None):
        import re
        iso = datetime.fromtimestamp(until, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        vs = [("sym", sym), ("day", day), ("until", iso), ("k_ts", cursor[0]), ("k_exp", cursor[1]), ("k_strike", cursor[2]),
              ("k_run", cursor[3])]
        ok = (re.match(r"^[A-Z]{3,12}$", sym), re.match(r"^\d{4}-\d{2}-\d{2}$", day or ""),
              re.match(r"^\d{4}-\d{2}-\d{2}T[0-9:.]+[+-]\d{2}:\d{2}$", cursor[0]), re.match(r"^\d{4}-\d{2}-\d{2}$", cursor[1]),
              re.match(r"^-?[0-9.]+$", cursor[2]), re.match(r"^[0-9a-fA-F-]*$", cursor[3]))
        if not all(ok):
            raise SourceError("other")
        return vs

    def read_page(self, sym, cursor, until, limit):
        if limit != wall_source.PAGE_LIMIT:
            raise SourceError("other")
        out = self._psql(wall_source.SNAPSHOT_SQL, self._vars(sym, cursor, until, self.day))
        try:
            return wall_source.rows_from_psql_csv(out)
        except ValueError:
            raise SourceError("other") from None

    def count_upto(self, sym, cursor, until):
        out = self._psql(wall_source.COUNT_SQL, self._vars(sym, cursor, until, self.day))
        try:
            return int(out.strip())
        except ValueError:
            raise SourceError("other") from None

    def check(self):
        """-> (role name, default_transaction_read_only, can the role write the table: 't' / 'f')."""
        out = self._psql(wall_source.CHECK_SQL, [("privs", wall_source.WRITE_PRIVS_PROBE)])
        rows = [r for r in out.splitlines() if r.strip()]
        parts = rows[0].split(",") if rows else []
        if len(parts) != 3:
            raise SourceError("other")
        return parts[0], parts[1], parts[2]
