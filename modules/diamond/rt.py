"""Diamond · « ↔ IA », the round trip of every Diamond page with an AI assistant (0.60.111, D-O-124).

The team works as on a blackboard with post-its -- the AI is the blackboard -- and the real artefacts stay in the Space:

  export   the page (or all of Diamond) leaves as one JSON document {section: [items]}: every item carries its code (F12, CB-4,
           L7, PT-3…), its fields, and its links written as codes (« parent »: « F2 »). It goes inside a prompt (Claude, Gemini or
           another LLM) or as a .json file.
  import   the assistant gives the document back, sections complete. Item by item, against the Space:
             new       no code, or a temporary code that starts with « + » (« +F1 », that other new items may point to);
             update    a known code, at least one field different (a key left out keeps its value);
             same      a known code, nothing different;
             remove    a known code absent from a section that came back: the item leaves the Space (archived when the page
                       archives, deleted otherwise) -- only the sections present in the answer are compared;
             refused   what cannot hold (an unknown code, a link to nothing, a value out of its list), with its reason.
  apply    the preview's ticked lines, in one transaction: a full backup of the Space first (⚙ Admin → Spaces → Sauvegardes),
           then the sections in the order of their links (functions before the DFMEA that hangs on them), the removals last.
           Every write goes through the page's own route (its checks, its numbering, its journal): nothing is written here
           that the page itself would refuse.

A section is declared in rt_sections_*.py (Section, Field); this file is the engine and the routes.
"""
import copy
import json
import re
import sqlite3
from collections import Counter

from core import audit, permissions, validate
from core.errors import ApiError
from core.files import RawFile

from . import ai_io

KINDS = {"new": "Nouveau", "update": "Modifié", "same": "Identique", "remove": "Retiré", "refused": "Refusé"}
TRUNCATED = 0.5  # an answer that keeps less than half of a section's items: its removals start unticked (a truncated answer)


class Field:
    """key: the JSON key of the document; src: the key of the page's list (default key); api: the body field of the page's routes
    (default src); kind: text | int | num | bool | enum | ref | refs; ref: the section a ref / refs points to; values: the allowed
    values of an enum; ro: shown to the AI, never written; setter(rt, item_id, value): a field written by its own route."""

    def __init__(self, key, src=None, api=None, kind="text", ref=None, values=None, ro=False, setter=None, note="",
                 out=None, check=None, to_api=None, create_only=False):
        self.key, self.src, self.kind, self.ref, self.values, self.ro, self.setter, self.note = key, src or key, kind, ref, values, ro, setter, note
        self.api = api or self.src
        self.create_only = create_only  # given when the item is created, never changed after (a sheet's brick, a row's plan)
        self.out, self.check, self.to_api = out, check, to_api  # hooks of a field that is none of the kinds: out(rt, rec),
        # check(rt, value, temps) -> (value, reason), to_api(rt, value)


class Section:
    """One kind of artefact. items(rt) -> the page's records; code(rec) -> its code; create / update / remove: a path under
    /api/diamond/p/<pid> (« {id} » replaced) or a function(rt, ...); table: where a created item's id is found."""

    def __init__(self, key, label, pages, fields, items, code, table, create=None, update=None, remove=None, removes="supprime",
                 prefix="", guide="", new_id=None, create_body=None, order=0, removable=None, listed=True):
        self.key, self.label, self.pages, self.fields, self.items, self.code = key, label, pages, fields, items, code
        self.table, self.create, self.update, self.remove, self.removes = table, create, update, remove, removes
        self.prefix, self.guide, self.new_id, self.create_body, self.order = prefix, guide, new_id, create_body, order
        self.removable = removable  # removable(rec) -> False: an item that leaving the answer does not remove (an unpriced part)
        self.listed = listed  # False: a read-only list given as context only (the catalogue of the competencies, 0.60.116)


def registry():
    from . import rt_sections_a, rt_sections_b, rt_sections_c, rt_sections_d
    out = rt_sections_a.SECTIONS + rt_sections_b.SECTIONS + rt_sections_c.SECTIONS + rt_sections_d.SECTIONS
    return {s.key: s for s in sorted(out, key=lambda s: s.order)}


_PATTERNS = {}


def _compiled(text):
    if text not in _PATTERNS:
        _PATTERNS[text] = re.compile(text)
    return _PATTERNS[text]


class RoundTrip:
    """The request seen by the sections: internal calls to Diamond's own routes, codes <-> ids."""

    def __init__(self, ctx, pid):
        self.ctx, self.pid, self.sections = ctx, pid, registry()
        self._records, self._codes, self.temp = {}, {}, {}

    def call(self, method, path, body=None):
        from core import features
        from . import ROUTES
        full = "/api/diamond/p/{}{}".format(self.pid, path)
        features.guard(self.ctx.conn, full)  # a part an administrator turned off stays off (D-O-111)
        for route in ROUTES:
            pattern = route[1] if hasattr(route[1], "fullmatch") else _compiled(route[1])
            m = pattern.fullmatch(full)
            if m and route[0] == method:
                child = copy.copy(self.ctx)
                child.body, child.params, child.query = body or {}, m.groupdict(), {}
                return route[2](child)
        raise ApiError(500, "Route interne introuvable : {} {}".format(method, path))

    def records(self, key):
        if key not in self._records:
            self._records[key] = list(self.sections[key].items(self))
        return self._records[key]

    def codes(self, key):
        """{code: id} of a section, the items created by this import included (their temporary code)."""
        if key not in self._codes:
            sec = self.sections[key]
            self._codes[key] = {sec.code(r): r["id"] for r in self.records(key)}
        return self._codes[key]

    def code_of(self, key, item_id):
        return next((c for c, i in self.codes(key).items() if i == item_id), None)

    def forget(self, key):
        self._records.pop(key, None)
        self._codes.pop(key, None)


# ---------------------------------------------------------------- export

def _out_value(rt, f, rec):
    if f.out:
        return f.out(rt, rec)
    v = rec.get(f.src)
    if f.kind == "ref":
        return rt.code_of(f.ref, v) if v else ""
    if f.kind == "refs":
        return [c for c in (rt.code_of(f.ref, i) for i in (v or [])) if c]
    if f.kind == "bool":
        return bool(v)
    return "" if v is None else v


def dump(rt, keys):
    doc = {}
    for key in keys:
        sec = rt.sections[key]
        doc[key] = [dict({"code": sec.code(r)}, **{f.key: _out_value(rt, f, r) for f in sec.fields}) for r in rt.records(key)]
    return doc


def context(rt, keys):
    """What the exported sections point to without being exported: codes and names, read only."""
    wanted = {f.ref for k in keys for f in rt.sections[k].fields if f.ref and f.ref not in keys}
    out = {}
    for key in sorted(wanted):
        sec = rt.sections[key]
        name = next((f for f in sec.fields if f.kind == "text"), None)
        out[key] = [{"code": sec.code(r), "name": str(r.get(name.src) or "")[:120] if name else ""} for r in rt.records(key)]
    return out


# ---------------------------------------------------------------- plan

def _norm(value):
    if isinstance(value, list) and any(isinstance(x, dict) for x in value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    if isinstance(value, list):
        return sorted(str(x).strip() for x in value if str(x).strip())
    if isinstance(value, bool):
        return value
    return " ".join(ai_io.cell(value).split())


def _check(rt, f, value, temps):
    """(clean value, reason) of a field of the document; reason non-empty: refused."""
    if f.check:
        return f.check(rt, value, temps)
    if f.kind in ("ref", "refs"):
        vals = value if isinstance(value, list) else ([] if value in (None, "") else [value])
        known = set(rt.codes(f.ref)) | temps.get(f.ref, set())
        bad = [str(v) for v in vals if str(v).strip() not in known]
        if bad:
            return None, "{} : « {} » n'existe pas dans {}.".format(f.key, ", ".join(bad), rt.sections[f.ref].label)
        vals = [str(v).strip() for v in vals]
        return (vals if f.kind == "refs" else (vals[0] if vals else "")), ""
    if f.kind == "enum" and value not in (None, "") and f.values and str(value) not in f.values:
        return None, "{} : « {} » n'est pas une valeur permise ({}).".format(f.key, value, ", ".join(f.values))
    if f.kind in ("int", "num") and value not in (None, ""):
        try:
            value = int(value) if f.kind == "int" else float(value)
        except (TypeError, ValueError):
            return None, "{} : « {} » n'est pas un nombre.".format(f.key, value)
    if f.kind == "bool":
        value = value if isinstance(value, bool) else str(value).strip().lower() in ("1", "true", "oui", "yes", "x")
    return value, ""


def _label(sec, item, rec=None):
    for f in sec.fields:
        if f.kind == "text" and not f.ro:
            text = item.get(f.key) if item and f.key in item else (rec or {}).get(f.src)
            if text:
                return str(text)[:140]
    return ""


def plan(rt, doc):
    """[entries] of a document against the Space, and the warnings."""
    entries, warnings = [], []
    keys = [k for k in rt.sections if k in doc]
    unknown = [k for k in doc if k not in rt.sections and not k.startswith("_")]
    if unknown:
        warnings.append("Sections ignorées (inconnues) : " + ", ".join(unknown) + ".")
    temps = {}
    for key in keys:  # the temporary codes first: a new item may point to another one, in any section
        items = doc[key] if isinstance(doc[key], list) else []
        temps[key] = {str(it.get("code")).strip() for it in items if isinstance(it, dict) and str(it.get("code") or "").startswith("+")}
    for key in keys:
        sec, items = rt.sections[key], doc[key]
        if not isinstance(items, list):
            warnings.append("{} : une liste d'objets est attendue ; section ignorée.".format(sec.label))
            continue
        current = {sec.code(r): r for r in rt.records(key)}
        seen = set()
        for n, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or "").strip()
            base = dict(section=key, n=n, id="{}:{}".format(key, n), code=code)
            if code and not code.startswith("+") and code not in current:
                entries.append(_entry(base, "refused", _label(sec, item), reason="Code inconnu dans ce Space. Correctif : retirez le code "
                                      "pour créer l'élément, ou « +… » pour un nouveau que d'autres pointent."))
                continue
            if code and code in seen:
                entries.append(_entry(base, "refused", _label(sec, item), reason="Code présent deux fois dans la réponse."))
                continue
            if code:
                seen.add(code)
            rec = current.get(code)
            values, changes, reasons = {}, [], []
            for f in sec.fields:
                if f.ro or f.key not in item:
                    continue
                value, why = _check(rt, f, item[f.key], temps)
                if why:
                    reasons.append(why)
                    continue
                before = _out_value(rt, f, rec) if rec else None
                if rec is not None and f.create_only and _norm(before) != _norm(value):
                    reasons.append("{} ne change pas après la création (« {} » → « {} »). Correctif : gardez la valeur, ou retirez l'élément "
                                   "et créez-en un nouveau.".format(f.key, _show(before), _show(value)))
                    continue
                if rec is None or _norm(before) != _norm(value):
                    values[f.key] = value
                    changes.append([f.key, _show(before), _show(value)])
            label = _label(sec, item, rec)
            if reasons:
                entries.append(_entry(base, "refused", label, reason=" ".join(reasons)))
            elif rec is None:
                entries.append(_entry(base, "new", label, changes=changes, values=values))
            else:
                entries.append(_entry(base, "update" if values else "same", label, changes=changes, values=values, item_id=rec["id"]))
        gone = [c for c in current if c not in seen and (sec.removable is None or sec.removable(current[c]))]
        if gone and sec.remove:
            short = len(seen) < TRUNCATED * len(current)
            if short:
                warnings.append("{} : la réponse garde {} élément(s) sur {} ; les retraits sont décochés (réponse peut-être tronquée)."
                                .format(sec.label, len(seen), len(current)))
            for i, c in enumerate(gone, start=1):
                rec = current[c]
                entries.append(_entry(dict(section=key, n=len(items) + i, id="{}:-{}".format(key, i), code=c), "remove", _label(sec, None, rec),
                                      reason="Absent de la réponse : " + ("archivé." if sec.removes == "archive" else "supprimé."),
                                      item_id=rec["id"], default=not short))
    return entries, warnings


def _show(v):
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    if isinstance(v, bool):
        return "oui" if v else "non"
    return "" if v is None else str(v)


def _entry(base, kind, label, changes=None, reason="", values=None, item_id=None, default=True):
    out = dict(base, kind=kind, kind_label=KINDS[kind], label=label, changes=changes or [], reason=reason,
               default=default and kind in ("new", "update", "remove"))
    out["_values"], out["_item"] = values or {}, item_id
    return out


# ---------------------------------------------------------------- apply

def _api_value(rt, f, value):
    """The id(s) behind a code. A code the Space does not know (a new item refused or unticked) raises KeyError: the line that
    points to it is refused, never written without its link."""
    if f.to_api:
        return f.to_api(rt, value)
    if f.kind == "ref":
        return rt.codes(f.ref)[value] if value else None
    if f.kind == "refs":
        return [rt.codes(f.ref)[v] for v in value]
    return value


def _path(template, item_id):
    return template.replace("{id}", str(item_id))


def _write(rt, sec, e):
    plain = {f.api: _api_value(rt, f, e["_values"][f.key]) for f in sec.fields if f.key in e["_values"] and not f.setter}
    later = [(f, e["_values"][f.key]) for f in sec.fields if f.key in e["_values"] and f.setter]
    if e["kind"] == "new":
        body = sec.create_body(rt, plain) if sec.create_body else plain
        if callable(sec.create):
            item_id = sec.create(rt, body)
        else:
            rt.call("POST", sec.create, body)
            item_id = sec.new_id(rt) if sec.new_id else rt.ctx.conn.execute(
                "SELECT MAX(id) FROM {} WHERE project_id = ?".format(sec.table), (rt.pid,)).fetchone()[0]
        rt.codes(sec.key)[e["code"] or "+{}:{}".format(sec.key, e["n"])] = item_id
    else:
        item_id = e["_item"]
        if plain:
            if callable(sec.update):
                sec.update(rt, item_id, plain)
            else:
                rt.call("PATCH", _path(sec.update, item_id), plain)
    for f, value in later:
        f.setter(rt, item_id, _api_value(rt, f, value))


def apply(rt, entries, skip, dry=False):
    """Writes the ticked entries. dry: the preview's rehearsal -- each entry in its own savepoint, what the page's route refuses
    becomes « refused » with the route's own message, and everything is rolled back."""
    todo = [e for e in entries if e["kind"] in ("new", "update", "remove") and e["id"] not in skip]
    order = list(rt.sections)
    done = Counter()
    steps = []
    for key in order:  # creations and updates, in the order of the links
        sec = rt.sections[key]
        steps += [(sec, e) for e in _parents_first(sec, [e for e in todo if e["section"] == key and e["kind"] in ("new", "update")])]
    for key in reversed(order):  # the removals last, what hangs on an item before the item
        steps += [(rt.sections[key], e) for e in todo if e["section"] == key and e["kind"] == "remove"]
    conn = rt.ctx.conn
    if dry:
        if not conn.in_transaction:
            conn.execute("BEGIN")
        conn.execute("SAVEPOINT rt_dry")
    try:
        for i, (sec, e) in enumerate(steps):
            if dry:
                conn.execute("SAVEPOINT rt_step")
            try:
                _step(rt, sec, e)
                done[e["kind"]] += 1
            except (ApiError, KeyError, ValueError, TypeError, sqlite3.Error) as err:
                if not dry:
                    raise _named(sec, e, err)
                conn.execute("ROLLBACK TO rt_step")
                _refuse(e, err)
            if dry:
                conn.execute("RELEASE rt_step")
    finally:
        if dry:
            conn.execute("ROLLBACK TO rt_dry")
            conn.execute("RELEASE rt_dry")
    return dict(done)


def _step(rt, sec, e):
    if e["kind"] != "remove":
        _write(rt, sec, e)
    elif callable(sec.remove):
        sec.remove(rt, e["_item"])
    else:
        rt.call("POST", _path(sec.remove, e["_item"]), {})


def _why(err):
    if isinstance(err, ApiError):
        return err.message
    if isinstance(err, KeyError):
        return "il pointe un élément refusé ou décoché ({}).".format(str(err).strip("'"))
    return "la page ne peut pas l'enregistrer ({}).".format(type(err).__name__)


def _refuse(e, err):
    e.update(kind="refused", kind_label=KINDS["refused"], default=False, reason="Refusé par la page : " + _why(err))


def _named(sec, e, err):
    return ApiError(getattr(err, "status", 409), "{} {} : {} Rien n'a été appliqué. Correctif : décochez cette ligne ou corrigez-la, "
                    "puis vérifiez de nouveau.".format(sec.label, e["code"] or "(nouveau)", _why(err)))


def _parents_first(sec, entries):
    """New items that point to other new items of the same section (a sub-function under a new function) come after them."""
    self_refs = [f.key for f in sec.fields if f.kind == "ref" and f.ref == sec.key]
    if not self_refs:
        return entries
    pending, out, placed = list(entries), [], set()
    while pending:
        ready = [e for e in pending if all(not str(e["_values"].get(k) or "").startswith("+") or e["_values"][k] in placed for k in self_refs)]
        ready = ready or pending[:1]
        for e in ready:
            out.append(e)
            placed.add(e["code"])
            pending.remove(e)
    return out


# ---------------------------------------------------------------- reading the answer

def read_doc(text):
    text = str(text or "").lstrip("﻿")
    if not text.strip():
        raise ApiError(400, "Réponse vide. Correctif : collez la réponse de l'assistant IA (son bloc JSON) ou choisissez le .json.")
    if len(text) > ai_io.MAX_TEXT:
        raise ApiError(413, "Texte trop long ({} caractères au plus).".format(ai_io.MAX_TEXT))
    blocks = re.findall(r"```(?:json)?[ \t]*\n(.*?)```", text, re.S)
    for body in reversed(blocks) if blocks else [text]:
        start, end = body.find("{"), body.rfind("}")
        if 0 <= start < end:
            try:
                data = json.loads(body[start:end + 1])
            except ValueError:
                continue
            if isinstance(data, dict):
                return data.get("diamond") if isinstance(data.get("diamond"), dict) else data
    raise ApiError(400, "Aucun objet JSON lu. Correctif : la réponse doit contenir un bloc ```json { \"functions\": [...], ... } ```.")


# ---------------------------------------------------------------- routes

def _pid(ctx, minimum):
    pid = validate.int_param(ctx.params, "pid")
    permissions.require_project_role(ctx.conn, ctx.user, pid, minimum)
    return pid


def _keys(rt, raw):
    keys = [k for k in str(raw or "").split(",") if k in rt.sections and rt.sections[k].listed]
    return keys or [k for k, s in rt.sections.items() if s.listed]


def api_sections(ctx):
    pid = _pid(ctx, "reader")
    rt = RoundTrip(ctx, pid)
    return {"sections": [{"key": s.key, "label": s.label, "pages": s.pages, "count": len(rt.records(s.key))} for s in rt.sections.values()
                         if s.listed]}


def api_export(ctx):
    pid = _pid(ctx, "reader")
    rt = RoundTrip(ctx, pid)
    keys = _keys(rt, ctx.query.get("sections"))
    doc = dict(dump(rt, keys), _context=context(rt, keys))
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()[0]
    return RawFile((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"),
                   "{}_diamond_{}.json".format(key, "-".join(keys) if len(keys) < 4 else "complet"), "application/json")


def api_prompt(ctx):
    from . import rt_prompt
    pid = _pid(ctx, "reader")
    rt = RoundTrip(ctx, pid)
    keys = _keys(rt, ctx.query.get("sections"))
    mode = ctx.query.get("mode") if ctx.query.get("mode") in rt_prompt.MODES else "review"
    board = None
    if str(ctx.query.get("ideation") or "").isdigit():  # 0.60.112 (D-O-125): the post-its of an Idéation session as source
        from modules.toolbox import ideation_ai
        board = ideation_ai.board(ctx.conn, pid, int(ctx.query["ideation"]))
    return {"prompt": rt_prompt.build(rt, keys, mode, ctx.query.get("goal", ""), board), "sections": keys}


def api_import(ctx):
    pid = _pid(ctx, "editor")
    rt = RoundTrip(ctx, pid)
    doc = read_doc(ctx.body.get("file"))
    entries, warnings = plan(rt, doc)
    counts = Counter(e["kind"] for e in entries)
    public = [{k: v for k, v in e.items() if not k.startswith("_")} for e in entries]
    summary = {k: counts.get(k, 0) for k in KINDS}
    labels = {k: rt.sections[k].label for k in {e["section"] for e in entries}}
    if ctx.body.get("mode") != "apply":
        apply(rt, entries, set(), dry=True)  # the rehearsal: what the pages' routes would refuse, refused now
        counts = Counter(e["kind"] for e in entries)
        summary = {k: counts.get(k, 0) for k in KINDS}
        public = [{k: v for k, v in e.items() if not k.startswith("_")} for e in entries]
        return {"mode": "preview", "entries": public, "counts": summary, "warnings": warnings, "labels": labels}
    skip = {str(x) for x in ctx.body.get("skip") or []}
    forced = {str(x) for x in ctx.body.get("confirm") or []}  # removals of a truncated section the person ticked herself
    skip |= {e["id"] for e in entries if e["kind"] == "remove" and not e["default"] and e["id"] not in forced}
    apply(rt, entries, skip, dry=True)  # the same rehearsal: what the routes refuse now (a line it hung on was unticked) stays out
    if not [e for e in entries if e["kind"] in ("new", "update", "remove") and e["id"] not in skip]:
        raise ApiError(400, "Rien à appliquer : toutes les lignes sont identiques, refusées ou décochées.")
    from .import_merge import backup
    saved = backup(ctx, pid)
    with audit.source("ai"):  # 0.60.120 (D-O-133): « Changements » shows these lines as written by the AI
        done = apply(RoundTrip(ctx, pid), entries, skip)  # a fresh view of the Space: the rehearsal's ids are gone
        counts = Counter(e["kind"] for e in entries)
        audit.log_action(ctx.conn, ctx.user["id"], "diamond_rt_import", "project", pid,
                         dict(done, refused=counts.get("refused", 0), sections=sorted(labels), backup=saved), ctx.ip)
    return {"mode": "apply", "applied": {k: done.get(k, 0) for k in ("new", "update", "remove")},
            "refused": counts.get("refused", 0), "backup": saved}
