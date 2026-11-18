"""« Changements » of a Space (core lot v0.39, 0.60.120, D-O-133): every change made in a Space, by hand or by an AI
assistant, with where it is (a link that opens the page and points at the item) and the three letters of who made it.

The source is the audit trail (core/audit.py), which every write already fills: nothing new to write in the modules.
Each line is placed in its Space and its tab, then described:

  - the Space: audit_log.project_id (kept at the time of the write, so a deleted item still shows), else read again from
    the row the object names (a table tied to a Space: « diamond_functions » 12, « agile_issue » 40…);
  - the tab, the code, the title and the link: the module's hook change_link(conn, entry, row, key) when it has one
    (core/modules.change_hooks), else read from the row (number, code, title, name…) and the tab named by the prefix;
  - what changed: the verb of the action (created, modified, removed…) and, when the entry lists them, the fields.

Several entries of the same person on the same item the same day become one line (« ×5 »). Exports, views and reads are
not changes and stay out. Read state is personal (core/changes_api.py: the last visit of a Space, « Vu » per line).
"""
import json
import re

from . import audit, modules

MIGRATIONS = [
    (21, """
        -- 0.60.120 (D-O-133): « Changements » of a Space -- the trail keeps who (three letters), how (by hand, ai, import)
        -- and which Space at the time of the write; the read state of each person (last visit, lines marked « Vu »).
        ALTER TABLE audit_log ADD COLUMN initials TEXT;
        ALTER TABLE audit_log ADD COLUMN source TEXT;
        ALTER TABLE audit_log ADD COLUMN project_id INTEGER;
        CREATE INDEX idx_audit_project ON audit_log(project_id, id);
        CREATE TABLE change_seen (
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            seen_at    TEXT NOT NULL,
            seen_id    INTEGER NOT NULL DEFAULT 0,      -- the last line of the trail at that visit
            PRIMARY KEY (user_id, project_id)
        );
        CREATE TABLE change_acks (
            user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            audit_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, audit_id)
        );
    """),
]

SCAN = 8000          # audit lines read at most for one request
NOT_A_CHANGE = re.compile(r"export|download|viewed|_view$|bot_read|login|logout|privacy|^changes_|copy_name|_print|_opened")
TITLE_COLS = ("title", "name", "label", "text", "failure_mode", "statement", "question")
CODE_COLS = ("test_id", "reference", "code", "number")
ALIASES = {"tools": "tools", "goldmine": "goldmine", "codex": "codex"}
VERBS = [
    (re.compile(r"(create|created|add|added|new|derive|duplicat|copied|copy)"), "Création"),
    (re.compile(r"(delete|deleted|remove|removed|retire)"), "Retrait"),
    (re.compile(r"(archive|archived)"), "Archivage"),
    (re.compile(r"(restore|unarchive|reopen)"), "Remise en service"),
    (re.compile(r"(import|apply|applied|rt_)"), "Import"),
    (re.compile(r"(comment)"), "Commentaire"),
    (re.compile(r"(freeze|frozen|unfreeze|sign|review|approve|status|transition|move)"), "Changement d'état"),
]


def tabs():
    """module key -> label, for the tabs that hold a Space's content."""
    return {e["key"]: e["label"] for e in modules.MODULE_MANIFEST
            if e["module"] is not None and e.get("placement") not in ("end",) and e["key"] not in ("help", "about")}


def tab_of(name):
    """The tab an action or an object type belongs to, by its prefix (« diamond_dfmea » -> diamond)."""
    known = tabs()
    head = str(name or "").split("_")[0]
    if head in ALIASES:
        return ALIASES[head]
    return head if head in known else ""


def verb(action):
    for pattern, word in VERBS:
        if pattern.search(action):
            return word
    return "Modification"


def _details(raw):
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def fields(details):
    """The fields an entry says it changed (a list, or the keys of a dict of changes)."""
    for key in ("fields", "changed", "changes"):
        value = details.get(key)
        if isinstance(value, dict):
            return [str(k) for k in value][:12]
        if isinstance(value, list):
            return [str(v) for v in value if isinstance(v, (str, int))][:12]
    return []


def _first(row, cols):
    for c in cols:
        if c in row and row[c] not in (None, ""):
            return row[c]
    return None


def _code(row, tab):
    value = _first(row, CODE_COLS)
    if value is None:
        return ""
    return str(value)


class Resolver:
    """Object (type, id) -> its Space, tab, code, title and link; rows read once per type."""

    def __init__(self, conn, keys):
        self.conn, self.keys = conn, keys          # keys: project id -> Space key
        self.hooks = modules.change_hooks()
        self.rows = {}

    def _row(self, object_type, object_id):
        table = audit.space_table(self.conn, object_type)
        if not table or object_id is None:
            return None
        cache = self.rows.setdefault(object_type, {})
        if object_id not in cache:
            row = None
            if str(object_id).isdigit():
                found = self.conn.execute('SELECT * FROM "{}" WHERE id = ?'.format(table), (int(object_id),)).fetchone()
                row = dict(found) if found else None
            cache[object_id] = row
        return cache[object_id]

    def describe(self, entry):
        """{project_id, tab, code, title, href, gone} or None when the entry is not tied to a visible Space."""
        otype, oid = entry["object_type"], entry["object_id"]
        details = entry["_details"]
        row = None if otype in ("project", "projects") else self._row(otype, oid)
        pid = entry["project_id"] or (row or {}).get("project_id")
        if pid is None and otype in ("project", "projects") and str(oid or "").isdigit():
            pid = int(oid)
        for hook in self.hooks:  # a module may know objects the core cannot read (a key « DEMO-12 » instead of an id)
            if pid is None or pid in self.keys:
                got = hook(self.conn, dict(entry, project_id=pid), row, self.keys.get(pid))
                if got:
                    pid = got.get("project_id", pid)
                    if pid not in self.keys:
                        return None
                    return self._out(entry, pid, got, row, details)
        if pid not in self.keys:
            return None
        return self._out(entry, pid, {}, row, details)

    def _out(self, entry, pid, got, row, details):
        key = self.keys[pid]
        tab = got.get("tab") or tab_of(entry["object_type"]) or tab_of(entry["action"])
        title = got.get("title") or (_first(row, TITLE_COLS) if row else None) or details.get("title") or details.get("name") or ""
        code = got.get("code") or (_code(row, tab) if row else "") or str(details.get("code") or details.get("key") or "")
        if entry["object_type"] in ("project", "projects") and not title:
            title = "Space {}".format(key) if not tab else "{} · réglages du Space".format(tabs().get(tab, tab))
        href = got.get("href") or ("#/{}/{}".format(tab, key) if tab else "#/dashboard")
        return {"project_id": pid, "space": key, "tab": tab, "tab_label": tabs().get(tab, "Space"), "code": code,
                "title": str(title)[:160], "href": href, "gone": row is None and entry["object_type"] not in ("project", "projects")}


def scan(conn, keys, since=None, limit=SCAN):
    """The audit entries of these Spaces (keys: project id -> key) since a time, newest first, described."""
    sql = ("SELECT a.id, a.ts, a.user_id, a.action, a.object_type, a.object_id, a.details, a.initials, a.source, a.project_id, "
           "u.display_name, u.username FROM audit_log a LEFT JOIN users u ON u.id = a.user_id")
    where, args = [], []
    if since:
        where.append("a.ts >= ?")
        args.append(since)
    if len(keys) == 1:  # one Space: its own lines, and the old ones that did not keep their Space
        where.append("(a.project_id = ? OR a.project_id IS NULL)")
        args.append(next(iter(keys)))
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY a.id DESC LIMIT ?"
    args.append(int(limit))
    initials = _current_initials(conn)
    res = Resolver(conn, keys)
    out = []
    for r in conn.execute(sql, args).fetchall():
        entry = dict(r)
        if NOT_A_CHANGE.search(entry["action"]):
            continue
        if entry["project_id"] is not None and entry["project_id"] not in keys:
            continue
        entry["_details"] = _details(entry["details"])
        where = res.describe(entry)
        if not where:
            continue
        who = entry["initials"] or initials.get(entry["user_id"]) or (entry["username"] or "?")[:3].upper()
        out.append(dict(where, id=entry["id"], ts=entry["ts"], user_id=entry["user_id"], initials=who,
                        user=entry["display_name"] or "", source=entry["source"] or "", action=entry["action"],
                        verb=verb(entry["action"]), fields=fields(entry["_details"])))
    return out


def _current_initials(conn):
    out = {}
    for r in conn.execute("SELECT user_id, prefs FROM user_prefs"):
        try:
            value = str(json.loads(r["prefs"]).get("initials") or "").upper()
        except (TypeError, ValueError):
            value = ""
        if value:
            out[r["user_id"]] = value
    return out


def group(items):
    """The same person on the same item the same day, by the same means: one line (the newest), counted."""
    out, index = [], {}
    for it in items:
        k = (it["space"], it["tab"], it["href"], it["code"], it["title"], it["user_id"], it["source"], it["ts"][:10])
        if k in index:
            line = out[index[k]]
            line["count"] += 1
            line["ids"].append(it["id"])
            line["fields"] = sorted(set(line["fields"]) | set(it["fields"]))[:12]
            if it["verb"] == "Création":
                line["verb"] = "Création"
            continue
        index[k] = len(out)
        out.append(dict(it, count=1, ids=[it["id"]]))
    return out
