"""Exports stamped with their revision, and the register of extractions (core lot v0.33, D-B-129).

Every file the platform BUILDS from its data (Word, Excel, PowerPoint, CSV, PDF -- not the attachments people
uploaded, nor backups or code) leaves through the router, which calls apply() on it:
- its file name gets the revision before the extension: « …_rev1.10.docx », or « …_hors-rev-20261009-1620.docx » when
  it was taken from the live database (outside any revision);
- Word, Excel and PowerPoint get the reference inside too (core/stamp_office.py): revision, its title and date, who
  extracted it and when, the number of the extraction;
- one line is added to data/baselines/extracts.jsonl: number, when, who (name, account, initials), revision (or the
  last one before, for a live export), route, file name, size and SHA-256 of the file sent -- chained by hash like the
  revision records, so a removed or edited line shows. Also journalled (audit_log « data_extracted »).
A CSV keeps its content unchanged (it must stay importable); its name and the register carry the reference.
"""
import csv
import datetime as dt
import hashlib
import io
import json
import threading

from . import APP_VERSION, audit, baselines, prefs
from .files import RawFile
from .stamp_office import stamp as office_stamp

KINDS = {"docx", "xlsx", "pptx", "csv", "pdf"}
REGISTER = "extracts.jsonl"
_lock = threading.Lock()


def _ext(filename):
    name = str(filename or "")
    return name.rsplit(".", 1)[1].lower() if "." in name else ""


def wants(raw):
    return isinstance(raw, RawFile) and not raw.inline and getattr(raw, "export", None) is not False \
        and _ext(raw.filename) in KINDS


def entries(data_dir):
    path = baselines.folder(data_dir) / REGISTER
    if not path.exists():
        return []
    out = []
    for line in path.read_text("utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _line_hash(entry):
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _append(data_dir, entry):
    path = baselines.folder(data_dir) / REGISTER
    with _lock:
        last = entries(data_dir)
        entry["n"] = (last[-1]["n"] + 1) if last else 1
        entry["prev"] = last[-1]["hash"] if last else None
        entry["hash"] = _line_hash(entry)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def tag(rec, now):
    return rec["label"] if rec else "hors-rev-" + now.strftime("%Y%m%d-%H%M")


def renamed(filename, label):
    name, dot, ext = str(filename).rpartition(".")
    return "{}_{}.{}".format(name, label, ext) if dot else "{}_{}".format(filename, label)


def apply(ctx, raw, path, live_conn):
    """Stamp `raw` (a RawFile) for the person and register it; returns the RawFile to send."""
    data_dir = ctx.data_dir
    rec = getattr(ctx, "baseline", None)
    now = dt.datetime.now()
    ext = _ext(raw.filename)
    who = ctx.user
    initials = prefs.get(live_conn, who["id"]).get("initials", "") or ""
    recs = baselines.records(data_dir)
    last = recs[-1] if recs else None
    number = (entries(data_dir)[-1]["n"] + 1) if entries(data_dir) else 1  # final number given by _append (same lock order)
    if rec:
        first = "Révision de référence {} — « {} » — figée le {} (empreinte {})".format(
            rec["label"], rec["title"], rec["local"], rec["sha256"][:12])
    else:
        first = "Hors révision — base courante au {}{}".format(
            now.strftime("%Y-%m-%d %H:%M"), " (dernière révision : {} du {})".format(last["label"], last["local"])
            if last else " (aucune révision de référence)")
    second = "Extrait le {} par {} ({}) — extraction n° {} — Dynamite | Agile v{}".format(
        now.strftime("%Y-%m-%d %H:%M"), who["display_name"], initials or "—", number, APP_VERSION)
    reference = rec["label"] if rec else "hors révision"
    rows = [("Référence de révision", reference), ("Titre de la révision", rec["title"] if rec else "—"),
            ("Révision figée le", rec["local"] if rec else "—"),
            ("Empreinte SHA-256 de la révision", rec["sha256"] if rec else "—"),
            ("Dernière révision connue", last["label"] if last else "—"),
            ("Extrait le", now.strftime("%Y-%m-%d %H:%M")), ("Extrait par", "{} ({})".format(who["display_name"], initials or "—")),
            ("Extraction n°", str(number)), ("Source", path), ("Outil", "Dynamite | Agile v" + APP_VERSION)]
    props = [("DA Revision", reference), ("DA Revision date", rec["local"] if rec else ""),
             ("DA Extracted by", "{} ({})".format(who["display_name"], initials)), ("DA Extracted at", now.strftime("%Y-%m-%d %H:%M")),
             ("DA Extract no", str(number))]
    data = office_stamp(raw.data, ext, [first, second], rows, props) if ext in ("docx", "xlsx", "pptx") else raw.data
    filename = renamed(raw.filename, tag(rec, now))
    entry = _append(data_dir, {
        "at": now.strftime("%Y-%m-%d %H:%M:%S"), "user_id": who["id"], "username": who["username"],
        "name": who["display_name"], "initials": initials, "baseline": rec["label"] if rec else None,
        "baseline_sha256": rec["sha256"] if rec else None, "after": last["label"] if (last and not rec) else None,
        "route": path, "query": {k: v for k, v in (ctx.query or {}).items()}, "file": filename,
        "original": raw.filename, "kind": ext, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    audit.log_action(live_conn, who["id"], "data_extracted", "baseline", entry["n"],
                     {"file": filename, "baseline": entry["baseline"], "sha256": entry["sha256"]}, ctx.ip)
    out = RawFile(data, filename, raw.content_type)
    out.export = False
    return out


# --------------------------------------------------------------------------
# API (administrators): the register
# --------------------------------------------------------------------------
def _check_chain(rows):
    prev = None
    for row in rows:
        if row.get("prev") != prev or _line_hash(row) != row.get("hash"):
            return row["n"]
        prev = row["hash"]
    return None


def api_extracts(ctx):
    rows = entries(ctx.data_dir)
    who = str(ctx.query.get("q") or "").strip().lower()
    rev = str(ctx.query.get("baseline") or "").strip()
    shown = [r for r in rows if (not who or who in (r.get("name", "") + " " + r.get("initials", "") + " "
                                                   + r.get("file", "")).lower())
             and (not rev or (r.get("baseline") or "hors") == rev)]
    return {"extracts": list(reversed(shown))[:500], "total": len(rows), "broken_at": _check_chain(rows)}


def api_extracts_csv(ctx):
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(["n", "date", "nom", "initiales", "compte", "révision", "dernière révision (hors révision)", "fichier",
                "type", "octets", "SHA-256 du fichier", "route"])
    for r in entries(ctx.data_dir):
        w.writerow([r["n"], r["at"], r.get("name"), r.get("initials"), r.get("username"), r.get("baseline") or "hors révision",
                    r.get("after") or "", r.get("file"), r.get("kind"), r.get("bytes"), r.get("sha256"), r.get("route")])
    raw = RawFile.csv(out.getvalue(), "registre_extractions_{}.csv".format(dt.date.today().isoformat()))
    raw.export = False
    return raw
