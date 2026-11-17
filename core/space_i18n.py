"""FR | EN of a Space's content (core lot v0.38, 0.60.108, D-O-120).

The FR | EN switch of the top bar translates on screen what the display dictionary knows (static/js/tools/i18n_dom.js):
the interface (static/i18n/en_*.json) and the demo content (demo_en_*.json), both files of the code. The content a team
writes in its own Space (requirements, functions, bricks, pages, Budget Lines…) is in no file of the code and must never
be: it may be confidential. Each Space therefore keeps its own dictionary, French text -> English text, in the database
(table space_i18n, tied to the Space). It travels with the Space's backup (.zip), its copies and the site move, and the
browser adds it to the display dictionary when the person reading switches to EN.

The French text stays the reference (what is edited, searched, exported); English is only shown. A pair is the text as
the screen shows it (a text node: a requirement statement, a function, a paragraph of a page), spaces collapsed.

Filling it: « Copier pour l'IA » takes the Space's French texts not translated yet (read from every row of the Space,
backup.collect) with the instructions; the team gives them to its AI assistant, pastes the answer {French: English},
sees the preview (new, changed, removed) and applies it. The server never calls an AI (D-O-015). Every write is journalled.
"""
import json
import re
from pathlib import Path

from . import audit, backup, db, permissions, validate
from .errors import ApiError
from .files import RawFile

MIGRATIONS = [
    (20, """
        -- 0.60.108 (D-O-120): the English text of a Space's content, shown with the FR | EN switch. Tied to the Space,
        -- so it follows its backup, copies and site move, and is deleted with it.
        CREATE TABLE space_i18n (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            fr         TEXT NOT NULL,
            en         TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (project_id, fr)
        );
        CREATE INDEX idx_space_i18n_project ON space_i18n(project_id);
    """),
]

MAX_PAIRS = 6000      # per Space
MAX_TEXT = 4000       # characters, French or English
MAX_EXPORT = 2500     # French texts handed to the AI at once
STATIC = Path(__file__).resolve().parent.parent / "static" / "i18n"
SKIP_TABLE = re.compile(r"^(space_i18n|audit|sessions|memberships|search|exports|timesheet_entries|timesheet_weeks|"
                        r"attachments|uploads|baseline|stamp)")
SKIP_COLUMN = {"created_at", "updated_at", "key", "status", "username", "password_hash", "icon_key", "color", "code", "test_id",
               "sent_at", "closed_at", "decided_at", "resolved_at", "due_date", "start_date", "work_date", "week_start", "date",
               "sha256", "mime", "filename", "kind", "type", "view", "side", "role", "source", "ftype", "task_set", "lang"}
SKIP_JSON_KEYS = ("type", "kind", "href", "src", "p", "icon", "id", "ref", "key", "color", "url", "lang")
LETTERS = re.compile(r"[A-Za-zÀ-ÿ]{3}")
IDENT = re.compile(r"^[A-Za-z0-9_.:/#@-]+$")  # a code, an identifier, a path: never shown as a sentence
PROMPT = """Translate into English the French texts below. They are the content of an engineering project (requirements,
functions, design notes, test procedures, time codes) as shown on screen, one text at a time.
- Answer ONLY with one JSON object: {"French text exactly as given": "English translation", ...}. Keep every key unchanged.
- Keep codes, numbers, units, standards and references as they are (REQ-12, F7, IEC 60068-2-6, 900 $/unit, ≤ 30 min, TRL 5).
- Technical terms already in English stay in English. Same tone, same length, no explanation, no Markdown.
- A text you cannot translate (a proper name, a code): leave it out of the answer.
"""


def norm(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------
def pairs_for(conn, project_ids):
    if not project_ids:
        return {}
    marks = ",".join("?" * len(project_ids))
    rows = conn.execute("SELECT fr, en FROM space_i18n WHERE project_id IN ({}) ORDER BY project_id, id".format(marks),
                        list(project_ids)).fetchall()
    return {r["fr"]: r["en"] for r in rows}


def api_all(ctx):
    """The pairs of every Space the person can open, for the display dictionary of the browser (asked only in EN)."""
    ids = [p["id"] for p in permissions.visible_projects(ctx.conn, ctx.user)]
    return {"pairs": pairs_for(ctx.conn, ids)}


def _pid(ctx, minimum="reader"):
    pid = validate.int_param(ctx.params, "project_id")
    permissions.require_project_role(ctx.conn, ctx.user, pid, minimum)
    return pid


def _require_manager(ctx, pid):
    if not permissions.is_project_manager(ctx.conn, ctx.user, pid):
        raise ApiError(403, "Réservé aux administrateurs et à l'Admin du projet de ce Space.")


def _static_known():
    known = set()
    for path in sorted(STATIC.glob("*en_*.json")):
        try:
            known.update(norm(k) for k in json.loads(path.read_text("utf-8")))
        except (OSError, ValueError):
            continue
    return known


def space_texts(conn, pid):
    """The French texts of a Space as the screens show them: every text column of every row of the Space
    (backup.collect follows the foreign keys), and the JSON ones (wiki pages, Storyline…) value by value."""
    found = set()

    def add(value):
        value = norm(value)
        if 2 <= len(value) <= MAX_TEXT and LETTERS.search(value) and not IDENT.match(value):
            found.add(value)
            head, sep, tail = value.partition(" · ")  # a screen may show « group · item » in two pieces (Budget Lines)
            if sep and head and tail and len(value) <= 200:
                add(head)
                add(tail)

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and k not in SKIP_JSON_KEYS:
                    add(v)
                elif not isinstance(v, str):
                    walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    from . import modules  # a module may add texts the Space shows but keeps elsewhere (its Budget Lines: Timesheet)
    for entry in modules.MODULE_MANIFEST:
        hook = getattr(entry["module"], "i18n_texts", None) if entry["module"] is not None else None
        if hook:
            for value in hook(conn, pid):
                add(value)
    _info, rows = backup.collect(conn, pid)
    for table, items in rows.items():
        if SKIP_TABLE.match(table):
            continue
        for row in items:
            for col, value in row.items():
                if col in SKIP_COLUMN or col.startswith("__") or col.endswith("_id") or not isinstance(value, str):
                    continue
                if value[:1] in "{[":
                    try:
                        walk(json.loads(value))
                        continue
                    except ValueError:
                        pass
                add(value)
    return found


def api_get(ctx):
    pid = _pid(ctx)
    rows = ctx.conn.execute("SELECT fr, en, updated_at FROM space_i18n WHERE project_id = ? ORDER BY fr", (pid,)).fetchall()
    return {"pairs": [dict(r) for r in rows], "count": len(rows)}


def api_texts(ctx):
    """The French texts of the Space that nothing translates yet, and the instructions for the AI (« Copier pour l'IA »)."""
    pid = _pid(ctx, "editor")
    have = set(pairs_for(ctx.conn, [pid])) | _static_known()
    texts = sorted(t for t in space_texts(ctx.conn, pid) if t not in have)
    return {"texts": texts[:MAX_EXPORT], "total": len(texts), "translated": len(pairs_for(ctx.conn, [pid])), "prompt": PROMPT}


def api_export(ctx):
    pid = _pid(ctx)
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()["key"]
    data = json.dumps(pairs_for(ctx.conn, [pid]), ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    return RawFile(data, "{}_traduction_EN.json".format(key), "application/json; charset=utf-8", export=False)


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------
def _clean(raw):
    """{French: English} or [[French, English], …] or [{fr, en}, …] -> {French: English}; an empty English removes."""
    if isinstance(raw, dict):
        items = list(raw.items())
    elif isinstance(raw, list):
        items = [(x.get("fr"), x.get("en")) if isinstance(x, dict) else tuple(x)[:2] for x in raw if isinstance(x, (dict, list, tuple))]
    else:
        raise ApiError(400, "Traduction illisible. Correctif : un objet JSON {\"texte français\": \"English text\", …}.")
    out = {}
    for fr, en in items:
        if not isinstance(fr, str) or not isinstance(en, (str, type(None))):
            raise ApiError(400, "Une paire n'est pas du texte. Correctif : {\"texte français\": \"English text\"}.")
        fr, en = norm(fr), norm(en or "")
        if not fr:
            continue
        if len(fr) > MAX_TEXT or len(en) > MAX_TEXT:
            raise ApiError(400, "Texte de plus de {} caractères : « {}… ». Correctif : coupez-le.".format(MAX_TEXT, fr[:40]))
        out[fr] = en
    return out


def api_put(ctx):
    """{pairs, mode: merge | replace, dry_run} -> what changes (added, changed, removed, unchanged)."""
    pid = _pid(ctx)
    _require_manager(ctx, pid)
    body = ctx.body if isinstance(ctx.body, dict) else {}
    wanted = _clean(body.get("pairs"))
    mode = body.get("mode") or "merge"
    if mode not in ("merge", "replace"):
        raise ApiError(400, "Mode inconnu. Correctif : merge (ajouter et corriger) ou replace (tout remplacer).")
    have = pairs_for(ctx.conn, [pid])
    added = {fr: en for fr, en in wanted.items() if en and fr not in have}
    changed = {fr: en for fr, en in wanted.items() if en and fr in have and have[fr] != en}
    removed = {fr for fr, en in wanted.items() if not en and fr in have}
    if mode == "replace":
        removed |= {fr for fr in have if fr not in wanted}
    if len(have) + len(added) - len(removed) > MAX_PAIRS:
        raise ApiError(400, "Plus de {} textes traduits pour ce Space. Correctif : importez moins de textes.".format(MAX_PAIRS))
    summary = {"added": len(added), "changed": len(changed), "removed": len(removed),
               "unchanged": sum(1 for fr, en in wanted.items() if en and have.get(fr) == en),
               "examples": [{"fr": fr, "en": en} for fr, en in list(added.items())[:5]]}
    if body.get("dry_run"):
        return dict(summary, dry_run=True)
    now = db.utc_now()
    for fr in removed:  # one request, one transaction (db.connect)
        ctx.conn.execute("DELETE FROM space_i18n WHERE project_id = ? AND fr = ?", (pid, fr))
    for fr, en in list(added.items()) + list(changed.items()):
        ctx.conn.execute("INSERT INTO space_i18n (project_id, fr, en, updated_at) VALUES (?, ?, ?, ?) "
                         "ON CONFLICT (project_id, fr) DO UPDATE SET en = excluded.en, updated_at = excluded.updated_at",
                         (pid, fr, en, now))
    audit.log_action(ctx.conn, ctx.user["id"], "space_i18n_import", "project", pid,
                     dict({k: summary[k] for k in ("added", "changed", "removed")}, mode=mode), ctx.ip)
    return dict(summary, count=len(pairs_for(ctx.conn, [pid])))


P = r"/api/projects/(?P<project_id>\d+)/i18n"
ROUTES = [
    ("GET", r"/api/i18n/spaces", api_all, "user"),
    ("GET", P, api_get, "user"),
    ("GET", P + r"/texts", api_texts, "user"),
    ("GET", P + r"\.json", api_export, "user"),
    ("PUT", P, api_put, "user"),
]
