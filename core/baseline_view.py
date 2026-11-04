"""Read-only view of a revision (core lot v0.33, D-B-129): the person who chooses a revision sees the WHOLE site as it
was at that moment -- every tab, every Space -- and every export carries that revision (core/stamp.py).

How: the router (core/router.py) gives the handlers of a GET request a connection to a working copy of the revision
instead of the live database; any other method is refused (lecture seule), except the few routes of FREE (leave the
view, settings of the person, session). Nothing in the handlers changes.
- cache   data/baselines_work/cache/<rev>_<code version>.sqlite: the .gz checked (SHA-256), unpacked once, and brought to
          the schema of the running code (migrations), so a revision taken with an older code still opens;
- work    data/baselines_work/<rev>_u<user id>.sqlite: a copy per person (what a GET handler might write stays there),
          deleted when the person leaves the view and at start-up.
- rights  ALWAYS the current ones: before every request the accounts, the memberships and the personal settings
          (export right) of the live database are copied into the working copy -- a person removed from a Space since
          the revision no longer sees it there either.
"""
import gzip
import re
import shutil
import sqlite3
import threading
from pathlib import Path

from . import APP_VERSION, baselines, db, modules, prefs
from .errors import ApiError

WORK = "baselines_work"
FREE = re.compile(r"/api/(me|me/prefs|me/password|logout|login|about|baselines(/.*)?|new/seen|privacy/event)")
READ_ONLY = ("LECTURE_SEULE: vous consultez la révision {} : tout le site est en lecture seule. Correctif : « Revenir à "
             "la base courante » dans le bandeau, puis refaites votre action.")
LIVE_TABLES = ("users", "memberships", "user_prefs")
_locks = {}
_guard = threading.Lock()


def _lock(key):
    with _guard:
        return _locks.setdefault(key, threading.Lock())


def work_dir(data_dir):
    path = Path(data_dir) / WORK
    (path / "cache").mkdir(parents=True, exist_ok=True)
    return path


def active(conn, user, data_dir):
    """The revision the person is viewing, or None."""
    if user is None or not data_dir:
        return None
    text = prefs.get(conn, user["id"]).get("baseline_view") or ""
    return baselines.find(data_dir, text) if text else None


def _cache(data_dir, rec):
    path = work_dir(data_dir) / "cache" / "{}_{}.sqlite".format(rec["label"], APP_VERSION)
    if path.exists():
        return path
    with _lock(str(path)):
        if path.exists():
            return path
        src = baselines.data_file(data_dir, rec)
        if not src.exists() or baselines._sha(src) != rec["sha256"]:
            raise ApiError(409, "Révision {} : fichier de données absent ou modifié (empreinte SHA-256 différente). "
                                "Correctif : un administrateur lance « Vérifier » et prévient l'IT.".format(rec["label"]))
        tmp = path.with_suffix(".part")
        with gzip.open(src, "rb") as g, open(tmp, "wb") as f:
            shutil.copyfileobj(g, f)
        conn = sqlite3.connect(str(tmp))
        try:  # schema of the running code (CREATE IF NOT EXISTS + pending migrations), like a return to a point
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.executescript(db.SCHEMA)
            extra = modules.registered_schema()
            if extra.strip():
                conn.executescript(extra)
            conn.commit()
            db.apply_migrations(conn, modules.registered_migrations())
            conn.commit()
        finally:
            conn.close()
        tmp.replace(path)
        for old in path.parent.glob(rec["label"] + "_*.sqlite"):
            if old != path:
                old.unlink()
    return path


def _columns(conn, schema, table):
    return [r[1] for r in conn.execute('PRAGMA {}.table_info("{}")'.format(schema, table))]


def _sync(conn):
    """Current accounts, memberships and personal settings into the working copy."""
    conn.execute("ATTACH DATABASE ? AS live", (str(db._db_path),))
    try:
        for table in LIVE_TABLES:
            cols = [c for c in _columns(conn, "main", table) if c in set(_columns(conn, "live", table))]
            if not cols:
                continue
            names = ", ".join('"{}"'.format(c) for c in cols)
            conn.execute('DELETE FROM main."{}"'.format(table))
            where = " WHERE project_id IN (SELECT id FROM main.projects)" if table == "memberships" else ""
            conn.execute('INSERT INTO main."{0}" ({1}) SELECT {1} FROM live."{0}"{2}'.format(table, names, where))
        conn.commit()
    finally:
        conn.execute("DETACH DATABASE live")


def open_copy(data_dir, rec, user_id):
    """A connection to the person's working copy of the revision, with the current rights."""
    cache = _cache(data_dir, rec)
    path = work_dir(data_dir) / "{}_u{}.sqlite".format(rec["label"], int(user_id))
    with _lock(str(path)):
        if not path.exists() or path.stat().st_mtime < cache.stat().st_mtime:
            shutil.copyfile(cache, path)
        conn = sqlite3.connect(str(path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = OFF")  # a frozen copy: nothing cascades
        conn.execute("PRAGMA busy_timeout = 10000")
        _sync(conn)
    return conn


def drop_copies(data_dir, user_id=None):
    """Delete the working copies (of one person, or all of them at start-up)."""
    base = work_dir(data_dir)
    pattern = "*_u{}.sqlite".format(int(user_id)) if user_id is not None else "*_u*.sqlite"
    for path in base.glob(pattern):
        try:
            path.unlink()
        except OSError:
            pass


def guard(method, path, rec):
    """The router's rule: in a revision, only reading -- or leaving it."""
    if rec is not None and method != "GET" and not FREE.fullmatch(path):
        raise ApiError(409, READ_ONLY.format(rec["label"]))
    return rec is not None and not FREE.fullmatch(path)
