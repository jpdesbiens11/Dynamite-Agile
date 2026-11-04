"""Révisions de référence revX.XX (core lot v0.33, D-B-129): frozen, numbered and dated copies of the WHOLE database,
kept forever, used as reference points for the design reviews of the project and to prove what left the
platform for a customer at a given date.

Numbering « revX.XX »: a number with two decimals, compared as a number (rev1.05 < rev1.10 < rev2.00). Typed by hand
« rev1.1 » means rev1.10 (decision of the user, 2026-10-09). The automatic number is the next whole one (rev1.10 ->
rev2.00; the first one is rev1.00). A number is always strictly greater than every number ever issued -- the
high-water mark lives in data/baselines/counter.json and in the record files, so it never goes back, not even after
a return of the whole site to a restore point (the registry is made of files, not of database rows).

On disk, in data/baselines/ (never in git; it travels with « Site complet »):
  rev1.10.sqlite.gz   the database at that moment (SQLite backup API, open sessions removed, compacted, gzip)
  rev1.10.json        its record: number, title, reason, who, when, sizes, SHA-256 of the .gz, row counts per table,
                      attachments referenced, and the hash of the previous record (a chain: one edited file shows)
  counter.json        the highest number ever issued
  extracts.jsonl      the register of extractions (core/stamp.py), one line per export, chained the same way
The attachments are not copied: they are content-addressed and never deleted but with their Space, whose deletion
keeps its own « avant suppression » backup; the record lists how many there are and their total size.
"""
import datetime as dt
import gzip
import hashlib
import json
import re
import shutil
import sqlite3
import threading
from pathlib import Path

from . import APP_VERSION, audit, db, permissions
from .errors import ApiError

FOLDER = "baselines"
NUM_RE = re.compile(r"^\s*(?:rev\s*)?(\d{1,4})(?:[.,](\d{1,2}))?\s*$", re.IGNORECASE)
LABEL_RE = re.compile(r"^rev\d{1,4}\.\d{2}$")
SKIP_TABLES = ("sessions", "sqlite_sequence")
_lock = threading.Lock()


def folder(data_dir):
    path = Path(data_dir) / FOLDER
    path.mkdir(parents=True, exist_ok=True)
    return path


# --------------------------------------------------------------------------
# Numbers
# --------------------------------------------------------------------------
def parse(text):
    """'rev1.1' / '1.10' / 'REV 2' / 'rev1,05' -> hundredths (110, 110, 200, 105). One decimal = tens (D-B-129)."""
    m = NUM_RE.match(str(text or ""))
    if not m:
        raise ApiError(400, "Numéro « {} » refusé. Correctif : revX.XX, par exemple rev2.00 ou rev1.15 (rev1.1 = rev1.10)."
                       .format(str(text or "")[:20]))
    whole, dec = int(m.group(1)), m.group(2) or "0"
    value = whole * 100 + (int(dec) * 10 if len(dec) == 1 else int(dec))
    if value <= 0:
        raise ApiError(400, "rev0.00 refusé. Correctif : un numéro plus grand que zéro, par exemple rev1.00.")
    return value


def label(value):
    return "rev{}.{:02d}".format(value // 100, value % 100)


def next_auto(high):
    return (high // 100 + 1) * 100 if high else 100


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_hash(record):
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Registry (files)
# --------------------------------------------------------------------------
def records(data_dir):
    out = []
    for path in folder(data_dir).glob("rev*.json"):
        try:
            rec = json.loads(path.read_text("utf-8"))
        except ValueError:
            continue
        if LABEL_RE.match(str(rec.get("label", ""))) and rec.get("label") == path.stem:
            out.append(rec)
    return sorted(out, key=lambda r: r["number"])


def find(data_dir, text):
    text = str(text or "").strip()
    if not LABEL_RE.match(text):
        return None
    return next((r for r in records(data_dir) if r["label"] == text), None)


def high_water(data_dir):
    nums = [r["number"] for r in records(data_dir)]
    try:
        nums.append(int(json.loads((folder(data_dir) / "counter.json").read_text("utf-8"))["high_water"]))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return max(nums) if nums else 0


def data_file(data_dir, rec):
    return folder(data_dir) / (rec["label"] + ".sqlite.gz")


def _snapshot(tmp):
    """Exact copy of the live database into `tmp`; sessions removed, compacted. -> (counts, spaces, attachments)."""
    src = sqlite3.connect(str(db._db_path), timeout=10)
    try:
        out = sqlite3.connect(str(tmp))
        try:
            src.backup(out)
            out.execute("PRAGMA journal_mode=DELETE")
            out.execute("DELETE FROM sessions")
            out.commit()
            tables = [r[0] for r in out.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
            counts = {t: out.execute('SELECT COUNT(*) FROM "{}"'.format(t)).fetchone()[0]
                      for t in tables if t not in SKIP_TABLES}
            spaces = [{"key": r[0], "name": r[1]} for r in out.execute("SELECT key, name FROM projects ORDER BY key")]
            att = out.execute("SELECT COUNT(*), COALESCE(SUM(size), 0) FROM attachments").fetchone() \
                if "attachments" in tables else (0, 0)
            out.execute("VACUUM")
        finally:
            out.close()
    finally:
        src.close()
    return counts, spaces, {"count": att[0], "bytes": att[1]}


def create(data_dir, number_text, title, note, user):
    """Freeze the whole database as a new revision; returns its record. Refused if the number does not go up."""
    title = str(title or "").strip()
    if not title:
        raise ApiError(400, "Titre obligatoire. Correctif : nommez la revue, ex. « Revue de conception PDR — BM3 ».")
    if len(title) > 160 or len(str(note or "")) > 2000:
        raise ApiError(400, "Titre : 160 caractères au plus ; motif : 2000 au plus.")
    base = folder(data_dir)
    with _lock:
        high = high_water(data_dir)
        value = parse(number_text) if str(number_text or "").strip() else next_auto(high)
        if value <= high:
            raise ApiError(409, "{} refusé : la dernière révision est {} et un numéro ne revient jamais en arrière. "
                                "Correctif : {} ou plus (automatique : {}).".format(label(value), label(high),
                                                                                 label(high + 1), label(next_auto(high))))
        name = label(value)
        tmp = base / (".tmp_" + name + ".sqlite")
        try:
            counts, spaces, attachments = _snapshot(tmp)
            raw = tmp.stat().st_size
            gz = base / (name + ".sqlite.gz")
            with open(tmp, "rb") as f, gzip.open(gz, "wb", compresslevel=9) as g:
                shutil.copyfileobj(f, g)
        finally:
            if tmp.exists():
                tmp.unlink()
        previous = records(data_dir)
        now = dt.datetime.now()
        rec = {"label": name, "number": value, "title": title, "note": str(note or "").strip(),
               "created_at": db.utc_now(), "local": now.strftime("%Y-%m-%d %H:%M"),
               "by_id": user["id"], "by": user["display_name"], "by_username": user["username"],
               "initials": user.get("initials", "") if isinstance(user, dict) else "",
               "app_version": APP_VERSION, "file": gz.name, "bytes_raw": raw, "bytes": gz.stat().st_size,
               "sha256": _sha(gz), "counts": counts, "spaces": spaces, "attachments": attachments,
               "previous": previous[-1]["label"] if previous else None,
               "previous_hash": previous[-1].get("hash") if previous else None}
        rec["hash"] = record_hash(rec)
        (base / (name + ".json")).write_text(json.dumps(rec, ensure_ascii=False, indent=1), "utf-8")
        (base / "counter.json").write_text(json.dumps({"high_water": value, "label": name}), "utf-8")
    return rec


def verify(data_dir, rec):
    """Integrity of a revision: its data file, its record and its link to the previous one."""
    problems = []
    path = data_file(data_dir, rec)
    if not path.exists():
        problems.append("Fichier de données {} absent.".format(path.name))
    elif _sha(path) != rec.get("sha256"):
        problems.append("Empreinte SHA-256 du fichier de données différente de la fiche : fichier modifié.")
    if record_hash(rec) != rec.get("hash"):
        problems.append("Fiche modifiée après sa création (empreinte de la fiche différente).")
    prev = next((r for r in records(data_dir) if r["label"] == rec.get("previous")), None)
    if rec.get("previous") and (prev is None or prev.get("hash") != rec.get("previous_hash")):
        problems.append("Lien vers la révision précédente {} rompu.".format(rec.get("previous")))
    return problems


def public(rec):
    keys = ("label", "number", "title", "note", "created_at", "local", "by", "initials", "app_version", "bytes_raw",
            "bytes", "sha256", "spaces", "attachments", "previous")
    out = {k: rec.get(k) for k in keys}
    out["rows"] = sum((rec.get("counts") or {}).values())
    return out


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
def api_list(ctx):
    from . import prefs
    recs = records(ctx.data_dir)
    high = high_water(ctx.data_dir)
    view = prefs.get(ctx.conn, ctx.user["id"]).get("baseline_view") or ""
    return {"baselines": [public(r) for r in reversed(recs)], "next": label(next_auto(high)),
            "last": label(high) if high else None, "view": view if find(ctx.data_dir, view) else "",
            "can_create": bool(ctx.user["is_admin"]), "folder": "data/{}/".format(FOLDER),
            "bytes_total": sum(r.get("bytes", 0) for r in recs)}


def api_create(ctx):
    permissions.require_admin(ctx.user)
    from . import prefs
    user = dict(ctx.user)
    user["initials"] = prefs.get(ctx.conn, ctx.user["id"]).get("initials", "")
    rec = create(ctx.data_dir, ctx.body.get("number"), ctx.body.get("title"), ctx.body.get("note"), user)
    audit.log_action(ctx.conn, ctx.user["id"], "baseline_created", "baseline", None,
                     {"label": rec["label"], "title": rec["title"], "sha256": rec["sha256"], "bytes": rec["bytes"]}, ctx.ip)
    return {"baseline": public(rec)}


def api_view(ctx):
    """Enter (label) or leave ("") the read-only view of a revision -- for the person only."""
    from . import baseline_view, prefs
    text = str(ctx.body.get("label") or "").strip()
    rec = find(ctx.data_dir, text) if text else None
    if text and rec is None:
        raise ApiError(404, "Révision « {} » introuvable. Correctif : choisissez-la dans la liste.".format(text[:20]))
    prefs._put(ctx.conn, ctx.user["id"], {"baseline_view": rec["label"] if rec else ""})  # 0.60.19: merge
    if rec is None:
        baseline_view.drop_copies(ctx.data_dir, ctx.user["id"])
    audit.log_action(ctx.conn, ctx.user["id"], "baseline_view_entered" if rec else "baseline_view_left", "baseline",
                     None, {"label": rec["label"]} if rec else None, ctx.ip)
    return {"view": rec["label"] if rec else ""}


def api_verify(ctx):
    permissions.require_admin(ctx.user)
    rec = find(ctx.data_dir, ctx.params.get("label"))
    if rec is None:
        raise ApiError(404, "Révision introuvable.")
    problems = verify(ctx.data_dir, rec)
    audit.log_action(ctx.conn, ctx.user["id"], "baseline_verified", "baseline", None,
                     {"label": rec["label"], "ok": not problems}, ctx.ip)
    return {"label": rec["label"], "ok": not problems, "problems": problems, "sha256": rec["sha256"]}


def _extracts(ctx):
    from . import stamp
    return stamp.api_extracts(ctx)


def _extracts_csv(ctx):
    from . import stamp
    return stamp.api_extracts_csv(ctx)


L = r"/api/baselines/(?P<label>rev\d{1,4}\.\d{2})"
ROUTES = [
    ("GET", r"/api/baselines", api_list, "user"),
    ("POST", r"/api/baselines", api_create, "admin"),
    ("POST", r"/api/baselines/view", api_view, "user"),
    ("GET", r"/api/baselines/extracts", _extracts, "admin"),
    ("GET", r"/api/baselines/extracts\.csv", _extracts_csv, "admin"),
    ("GET", L + r"/verify", api_verify, "admin"),
]
