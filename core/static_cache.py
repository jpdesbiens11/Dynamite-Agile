"""Static files of the interface, lean on the wire (0.60.31, D-O-039).

Before: every page load downloaded the ~140 files of the interface again (~1.5 MB): « Cache-Control: no-cache » asks
the browser to revalidate, but without a validator the server could only send the whole file back.
Now, for each file under static/:
  - an ETag (hash of the content): the browser asks « If-None-Match » and gets « 304 Not Modified », a few bytes;
  - a gzip copy for the text types (JS, CSS, SVG, HTML, JSON…), sent to every browser that accepts it (~3 times
    smaller), with « Vary: Accept-Encoding ».
Both are computed once and kept in memory, keyed by path and checked against the file's size and modification time on
every request (an update or an edited file is picked up at once, no restart). Standard library only.
"""
import gzip
import hashlib
import threading

COMPRESSIBLE = {".js", ".css", ".svg", ".html", ".json", ".md", ".txt", ".csv", ".xml", ".map", ".mjs"}
MIN_GZIP = 1024              # smaller files gain nothing worth the CPU
MAX_CACHED = 8 * 1024 * 1024  # a larger file is served as it is, never kept in memory

_lock = threading.Lock()
_cache = {}


class Entry:
    __slots__ = ("stamp", "raw", "gz", "etag")

    def __init__(self, stamp, raw, gz, etag):
        self.stamp, self.raw, self.gz, self.etag = stamp, raw, gz, etag


def get(target):
    """Entry of a file: .raw, .gz (bytes or None), .etag (strong, quoted)."""
    st = target.stat()
    stamp = (st.st_size, st.st_mtime_ns)
    key = str(target)
    with _lock:
        entry = _cache.get(key)
    if entry is not None and entry.stamp == stamp:
        return entry
    raw = target.read_bytes()
    gz = None
    if target.suffix.lower() in COMPRESSIBLE and len(raw) >= MIN_GZIP:
        packed = gzip.compress(raw, compresslevel=6, mtime=0)
        gz = packed if len(packed) < len(raw) * 0.9 else None
    entry = Entry(stamp, raw, gz, '"' + hashlib.sha256(raw).hexdigest()[:20] + '"')
    if len(raw) <= MAX_CACHED:
        with _lock:
            _cache[key] = entry
    return entry


def gzip_etag(etag):
    return etag[:-1] + '-gz"'


def not_modified(entry, if_none_match):
    """True when the browser already holds this file (If-None-Match, either representation, weak or strong)."""
    if not if_none_match:
        return False
    if if_none_match.strip() == "*":
        return True
    tags = {t.strip().removeprefix("W/") for t in if_none_match.split(",")}
    return entry.etag in tags or gzip_etag(entry.etag) in tags


def accepts_gzip(accept_encoding):
    for part in (accept_encoding or "").lower().split(","):
        name, _, params = part.strip().partition(";")
        if name.strip() in ("gzip", "*"):
            q = params.replace(" ", "")
            return not (q.startswith("q=0") and q.strip("q=0.") == "")
    return False
