"""Diamond · round trip with an AI assistant (0.60.104, D-O-116): what the DFMEA, the PFMEA and the control plans share.

A table leaves as a CSV (« Exporter (.csv) », for a spreadsheet) or inside a prompt (« Prompt pour l'IA », for Claude, Gemini or
another LLM, in an interview or a review); it comes back as the assistant's answer -- a ```json block, an array of objects whose
keys are the headers of the CSV -- or as the CSV edited in a spreadsheet. read_rows() reads both. The module of the table turns
each row into an entry:

  new       no code: a row to create;
  update    the code of an existing row, at least one field different (only the fields present in the row are compared:
            a key left out keeps its value, an empty value clears it);
  same      the code of an existing row, nothing different;
  refused   what cannot hold (an unknown code, an operation or a C-n that does not exist, a rating out of 1 to 10…), with its
            reason -- never written.

run() answers the preview (mode « preview », the default) or applies (mode « apply »): the new and updated entries, except the
lines the person unticked (skip), journalled. Nothing is ever deleted: a row absent from the file stays as it is.
"""
import csv
import io
import json
import re
import unicodedata
from collections import Counter

from core import audit
from core.errors import ApiError
from core.files import RawFile

MAX_TEXT = 800_000
MAX_ROWS = 800
KINDS = {"new": "Nouvelle", "update": "Modifiée", "same": "Identique", "refused": "Refusée"}


def norm(name):
    """« Failure Mode » -> « failuremode », « Échéance » -> « echeance »: a key compared without case, accent or punctuation."""
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", text)


def cell(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _json_items(text):
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end < start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None
    if isinstance(data, dict):
        data = data.get("rows") or data.get("lignes") or []
    return data if isinstance(data, list) else None


def read_rows(text):
    """(« json » | « csv », [(n, {normalized key: text})]) from an AI answer or a CSV file. n is the proposal number (JSON) or
    the line of the file (CSV), the one the preview and the messages name."""
    text = str(text or "").lstrip("﻿")
    if not text.strip():
        raise ApiError(400, "Fichier vide. Correctif : collez la réponse de l'assistant IA ou choisissez le .csv.")
    if len(text) > MAX_TEXT:
        raise ApiError(413, "Texte trop long ({} caractères au plus). Correctif : importez en plusieurs fois.".format(MAX_TEXT))
    fence = re.search(r"```([A-Za-z]*)[ \t]*\n(.*?)```", text, re.S)
    body = fence.group(2) if fence else text
    lang = fence.group(1).lower() if fence else ""
    items = None
    if lang == "json" or body.lstrip()[:1] in "[{" or (not fence and re.search(r"\[\s*\{", text)):
        items = _json_items(body)
    if items is not None:
        rows = [(n, {norm(k): cell(v) for k, v in item.items()}) for n, item in enumerate(items, start=1) if isinstance(item, dict)]
        return "json", _cap(rows)
    lines = body.strip("\n")
    first = lines.split("\n", 1)[0]
    delimiter = ";" if ";" in first else "\t" if "\t" in first else ","
    table = list(csv.reader(io.StringIO(lines), delimiter=delimiter))
    head_at = next((i for i, r in enumerate(table) if any(c.strip() for c in r)), None)
    if head_at is None:
        raise ApiError(400, "Aucune ligne lue.")
    head = [norm(h) for h in table[head_at]]
    rows = []
    for i, r in enumerate(table[head_at + 1:], start=head_at + 2):
        if any(c.strip() for c in r):
            rows.append((i, {h: cell(r[j]) if j < len(r) else "" for j, h in enumerate(head) if h}))
    return "csv", _cap(rows)


def _cap(rows):
    if not rows:
        raise ApiError(400, "Aucune ligne lue. Correctif : un tableau JSON d'objets (la réponse de l'IA) ou le CSV de l'export, avec sa ligne "
                            "d'en-tête.")
    if len(rows) > MAX_ROWS:
        raise ApiError(413, "{} lignes au plus par import.".format(MAX_ROWS))
    return rows


def get(row, *names):
    """(present, value) of the first of the names the row has (names compared normalized)."""
    for name in names:
        key = norm(name)
        if key in row:
            return True, row[key]
    return False, ""


def same(a, b):
    return " ".join(cell(a).split()) == " ".join(cell(b).split())


def entry(n, code, kind, label="", changes=None, reason="", **private):
    out = {"n": n, "code": code, "kind": kind, "kind_label": KINDS[kind], "label": label, "changes": changes or [], "reason": reason}
    out.update({"_" + k: v for k, v in private.items()})
    return out


def run(ctx, pid, planner, applier, action):
    """Preview or apply. planner(rows) -> entries; applier(entries) applies the new and updated ones it is given."""
    fmt, rows = read_rows(ctx.body.get("file"))
    entries = planner(rows)
    counts = Counter(e["kind"] for e in entries)
    public = [{k: v for k, v in e.items() if not k.startswith("_")} for e in entries]
    summary = {k: counts.get(k, 0) for k in KINDS}
    if ctx.body.get("mode") != "apply":
        return {"mode": "preview", "format": fmt, "entries": public, "counts": summary}
    skip = {int(x) for x in ctx.body.get("skip") or [] if str(x).isdigit()}
    todo = [e for e in entries if e["kind"] in ("new", "update") and e["n"] not in skip]
    applier(todo)
    done = {"new": sum(1 for e in todo if e["kind"] == "new"), "update": sum(1 for e in todo if e["kind"] == "update")}
    audit.log_action(ctx.conn, ctx.user["id"], action, "project", pid,
                     dict(done, refused=summary["refused"], skipped=summary["new"] + summary["update"] - done["new"] - done["update"], format=fmt), ctx.ip)
    return {"mode": "apply", "format": fmt, "applied": done, "counts": summary}


def csv_file(headers, rows, filename):
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(headers)
    w.writerows(rows)
    return RawFile(("﻿" + out.getvalue()).encode("utf-8"), filename, "text/csv")


def number(value, prefix):
    """« L12 », « 12 », « OP30 », « PC-2 », « C-14 », « P-21 », « F13 Mesurer… » -> 12, 30, 2, 14, 21, 13 (None when absent)."""
    m = re.match(r"\s*(?:" + prefix + r")?\s*-?\s*(\d+)\b", str(value or ""), re.I)
    return int(m.group(1)) if m else None
