"""Validation of one tickets.csv row before anything is written (D-A-030).

Every refusal is a RowError carrying two texts: `message` (what is wrong,
naming the offending value) and `fix` (what to change so the import
works, listing the accepted values when there are any). Nothing is
written for a refused row: validate_row() runs completely first, then
csv_io applies the resolved values.

Status rule (D-A-030): an explicit status must exist in the workflow of
the ticket's type AND be reachable from the current status (the initial
status for a new ticket) through one transition the importer is allowed
to run -- exactly what the ticket page allows. An empty cell keeps the
current status.
"""
import re

from core import permissions
from core.errors import ApiError

from . import common as c

PRIORITY_ALIASES = {
    "blocker": "blocker", "bloquante": "blocker",
    "high": "high", "haute": "high",
    "medium": "medium", "moyenne": "medium",
    "low": "low", "basse": "low",
    "trivial": "trivial", "minime": "trivial",
}
DATE_FORMATS = (
    (re.compile(r"^(\d{4})-(\d{2})-(\d{2})$"), (1, 2, 3)),   # 2026-11-15
    (re.compile(r"^(\d{4})/(\d{2})/(\d{2})$"), (1, 2, 3)),   # 2026/11/15
    (re.compile(r"^(\d{2})/(\d{2})/(\d{4})$"), (3, 2, 1)),   # 15/11/2026 (Excel fr-CA)
)
MAX_LISTED = 12


class RowError(Exception):
    """One or more problems on a row. `problems` is a list of (message,
    fix); `message`/`fix` expose the first one for simple callers."""

    def __init__(self, message, fix, problems=None):
        super().__init__(message)
        self.problems = problems or [(message, fix)]
        self.message, self.fix = self.problems[0]


def _listing(names):
    names = [n for n in names if n]
    if not names:
        return "(aucun)"
    shown = ", ".join(names[:MAX_LISTED])
    return shown + (" … ({} au total)".format(len(names)) if len(names) > MAX_LISTED else "")


def _cell(row, name):
    return (row.get(name) or "").strip()


def _by_name(rows, value):
    """Case-insensitive, accent-sensitive match on a `name` column; the former French default names of statuses and
    types (« Reçue », « Task »…) still match their English names (D-B-085)."""
    from .vocab import STATUS_EN, TYPE_EN
    wanted = value.casefold()
    found = next((r for r in rows if r["name"].casefold() == wanted), None)
    if found is None:
        legacy = {k.casefold(): v for k, v in dict(STATUS_EN, **TYPE_EN).items()}.get(wanted)
        if legacy:
            found = next((r for r in rows if r["name"] == legacy), None)
    return found


def _type(conn, project_id, row):
    value = _cell(row, "type")
    types = conn.execute("SELECT * FROM agile_issue_types WHERE project_id = ? ORDER BY position",
                         (project_id,)).fetchall()
    if not value:
        raise RowError("Colonne « type » vide.", "Indiquez un type : " + _listing([t["name"] for t in types]) + ".")
    found = _by_name(types, value)
    if found is None:
        raise RowError("Type « {} » inconnu dans ce projet.".format(value),
                       "Types acceptés : {}. Un nouveau type se crée dans Agile → Paramètres → "
                       "Types (admin).".format(_listing([t["name"] for t in types])))
    return found


def _priority(row, existing):
    value = _cell(row, "priority")
    if not value:
        return existing["priority"] if existing else "medium"
    key = PRIORITY_ALIASES.get(value.casefold())
    if key is None:
        raise RowError("Priorité « {} » inconnue.".format(value),
                       "Valeurs acceptées : Bloquante, Haute, Moyenne, Basse, Minime "
                       "(ou blocker, high, medium, low, trivial).")
    return key


def _status(conn, itype, row, existing, role):
    """Return (status_row, transition_or_None). Raises RowError if refused."""
    workflow = conn.execute("SELECT * FROM agile_workflows WHERE id = ?", (itype["workflow_id"],)).fetchone()
    statuses = conn.execute("SELECT * FROM agile_statuses WHERE workflow_id = ? ORDER BY position",
                            (itype["workflow_id"],)).fetchall()
    initial = next((s for s in statuses if s["is_initial"]), statuses[0] if statuses else None)
    if initial is None:
        raise RowError("Le workflow « {} » n'a aucun status.".format(workflow["name"]),
                       "Ajoutez au moins un status dans Agile → Paramètres (admin).")
    current = (next(s for s in statuses if s["id"] == existing["status_id"])
               if existing else initial)
    value = _cell(row, "status")
    if not value:
        return current, None
    target = _by_name(statuses, value)
    if target is None:
        raise RowError("Status « {} » absent du workflow « {} » (type « {} »).".format(
            value, workflow["name"], itype["name"]),
            "Statuts acceptés : {} — ou laissez la cellule vide pour conserver « {} ».".format(
                _listing([s["name"] for s in statuses]), current["name"]))
    if target["id"] == current["id"]:
        return current, None
    candidates = conn.execute(
        "SELECT * FROM agile_transitions WHERE workflow_id = ? AND to_status_id = ? "
        "AND (from_status_id = ? OR from_status_id IS NULL)",
        (itype["workflow_id"], target["id"], current["id"])).fetchall()
    level = permissions.ROLE_LEVEL[role]
    allowed = [t for t in candidates if level >= permissions.ROLE_LEVEL[t["min_role"]]]
    if allowed:
        return target, allowed[0]
    if candidates:
        raise RowError("La transition « {} » → « {} » est réservée aux administrateurs.".format(
            current["name"], target["name"]),
            "Faites importer ce fichier par un administrateur, ou laissez « {} » dans la "
            "colonne status.".format(current["name"]))
    reachable = conn.execute(
        "SELECT t.name AS t_name, s.name AS s_name, t.min_role FROM agile_transitions t "
        "JOIN agile_statuses s ON s.id = t.to_status_id WHERE t.workflow_id = ? "
        "AND (t.from_status_id = ? OR t.from_status_id IS NULL) AND t.to_status_id != ?",
        (itype["workflow_id"], current["id"], current["id"])).fetchall()
    options = ["{} (« {} »)".format(r["s_name"], r["t_name"]) for r in reachable
               if level >= permissions.ROLE_LEVEL[r["min_role"]]]
    start = "À la création, un ticket part de « {} »".format(current["name"]) if not existing \
        else "Depuis « {} »".format(current["name"])
    raise RowError("Transition « {} » → « {} » absente du workflow « {} ».".format(
        current["name"], target["name"], workflow["name"]),
        "{}, statuts atteignables en une étape : {}. Passez par ces étapes (un import par "
        "étape), ou ajoutez la transition dans Agile → Paramètres → Transitions (admin).".format(
            start, _listing(options)))


def _assignee(conn, project_id, row, existing):
    value = _cell(row, "assignee")
    if not value:
        return None
    members = c.members(conn, project_id)
    wanted = value.casefold()
    found = next((m for m in members if m["display_name"].casefold() == wanted
                  or m["username"].casefold() == wanted), None)
    if found is None:
        raise RowError("Assigné « {} » introuvable parmi les membres du projet.".format(value),
                       "Noms acceptés : {}. Une personne s'ajoute au projet dans Admin → "
                       "Projets → Membres, ou videz la cellule.".format(
                           _listing([m["display_name"] for m in members])))
    return found["id"]


def _named_ref(conn, project_id, row, column, table, label, where_hint):
    value = _cell(row, column)
    if not value:
        return None
    extra = " AND state != 'closed'" if table == "agile_sprints" else ""
    rows = conn.execute("SELECT id, name FROM {} WHERE project_id = ?{} ORDER BY id".format(table, extra),
                        (project_id,)).fetchall()
    found = _by_name(rows, value)
    if found is None:
        raise RowError("{} « {} » introuvable.".format(label, value),
                       "{} existants : {}. Créez-le d'abord dans {}, ou videz la cellule.".format(
                           label + "s", _listing([r["name"] for r in rows]), where_hint))
    return found["id"]


def _points(row):
    value = _cell(row, "points").replace(",", ".")
    if not value:
        return None
    try:
        points = float(value)
    except ValueError:
        raise RowError("Points « {} » non numériques.".format(row.get("points")),
                       "Indiquez un nombre (ex. 3 ou 2,5), ou videz la cellule.")
    if not 0 <= points <= 1000:
        raise RowError("Points {} hors limites.".format(value), "Indiquez un nombre entre 0 et 1000.")
    return points


def _due_date(row):
    value = _cell(row, "due_date")
    if not value:
        return None
    for pattern, (y, m, d) in DATE_FORMATS:
        match = pattern.match(value)
        if match:
            iso = "{}-{}-{}".format(match.group(y), match.group(m), match.group(d))
            if not c.is_real_date(iso):
                raise RowError("Date « {} » inexistante au calendrier.".format(value),
                               "Vérifiez le jour et le mois (jj/mm/aaaa ou aaaa-mm-jj) ; Excel inverse "
                               "parfois jour et mois selon la langue du poste.")
            return iso
    raise RowError("Date d'échéance « {} » non reconnue.".format(value),
                   "Formats acceptés : aaaa-mm-jj (recommandé), aaaa/mm/jj ou jj/mm/aaaa.")


def _labels(row):
    labels = [x.strip() for x in _cell(row, "labels").split(";") if x.strip()]
    bad = [label for label in labels if not c.LABEL_RE.match(label)]
    if bad:
        raise RowError("Label(s) invalide(s) : {}.".format(", ".join("« {} »".format(b) for b in bad)),
                       "Un label n'a ni espace ni caractère spécial (40 caractères max) : remplacez "
                       "les espaces par un tiret, ex. « {} ». Séparez plusieurs labels par « ; ».".format(
                           bad[0].replace(" ", "-")[:40]))
    if len(labels) > 20:
        raise RowError("{} labels sur une seule ligne.".format(len(labels)), "Vingt labels au maximum par ticket.")
    return labels


def _existing(conn, project_id, prefix, key, row, tickets_mode=False):
    """Ticket named by `key`. Goldmine keeps the strict rules (unknown key
    refused, stale updated_at refused). The tickets import (tickets_mode,
    D-B-008) returns None for an unknown key -- the row becomes a creation --
    and leaves the updated_at check to csv_io, which refuses only a stale row
    that would actually change something."""
    match = c.KEY_RE.match(key.upper())
    if not match:
        raise RowError("Clé « {} » invalide.".format(key),
                       "Format attendu : {}-numéro (ex. {}-4), ou cellule vide pour créer un ticket.".format(
                           prefix, prefix))
    if match.group(1) != prefix:
        raise RowError("La clé {} appartient au projet {}, pas à {}.".format(key, match.group(1), prefix),
                       "Importez cette ligne dans le projet {}, ou videz la clé pour créer un nouveau "
                       "ticket ici.".format(match.group(1)))
    try:
        existing = c.get_issue(conn, project_id, int(match.group(2)))
    except ApiError:
        if tickets_mode:
            return created_from_key(conn, project_id, key.upper())
        raise RowError("Le ticket {} n'existe pas (ou a été supprimé).".format(key),
                       "Videz la cellule « key » pour le recréer comme nouveau ticket.")
    if tickets_mode:
        return existing
    sent = _cell(row, "updated_at")
    if sent and sent != existing["updated_at"]:
        raise RowError("{} a été modifié sur le serveur depuis votre export ({}).".format(
            key, existing["updated_at"]),
            "Réexportez les tickets et reportez vos changements sur le nouveau fichier, ou videz "
            "« updated_at » pour écraser volontairement la version du serveur.")
    return existing


IMPORT_KEY_FIELD = "csv_key"


def created_from_key(conn, project_id, key):
    """Ticket an earlier import created from the unknown file key `key`
    (recorded in its history), so re-importing the same file updates it
    instead of creating it a second time. None if there is none."""
    row = conn.execute(
        "SELECT i.* FROM agile_history h JOIN agile_issues i ON i.id = h.issue_id "
        "WHERE i.project_id = ? AND h.field = ? AND h.new_value = ? ORDER BY h.id DESC LIMIT 1",
        (project_id, IMPORT_KEY_FIELD, key)).fetchone()
    return row


def _parent(conn, project_id, prefix, row, existing):
    value = _cell(row, "parent_key")
    if not value:
        return None
    match = c.KEY_RE.match(value.upper())
    if not match or match.group(1) != prefix:
        raise RowError("Parent « {} » invalide.".format(value),
                       "Le parent doit être un ticket du même projet ({}-numéro), ou une cellule vide.".format(prefix))
    try:
        parent = c.get_issue(conn, project_id, int(match.group(2)))
    except ApiError:
        raise RowError("Parent {} introuvable.".format(value),
                       "Créez d'abord le parent (une ligne plus haut ne suffit pas : sa clé n'existe "
                       "qu'après l'import), ou videz la cellule.")
    if existing and parent["id"] == existing["id"]:
        raise RowError("Le ticket est son propre parent.", "Indiquez un autre parent ou videz la cellule.")
    return parent["id"]


def validate_row(ctx, project_id, prefix, row, role):
    """Resolve every column of one row; raise RowError before any write.

    All independent columns are checked even after a first problem, so
    the report lists everything to fix on the line in one pass."""
    conn = ctx.conn
    problems = []
    resolved = {}

    def check(name, func, *args):
        try:
            resolved[name] = func(*args)
        except RowError as exc:
            problems.extend(exc.problems)
            resolved[name] = None

    key = _cell(row, "key")
    check("existing", lambda: _existing(conn, project_id, prefix, key, row, tickets_mode=True) if key else None)
    if problems:
        raise RowError(*problems[0], problems=problems)  # nothing else is meaningful
    existing = resolved["existing"]
    unknown_key = key.upper() if key and (existing is None or
                                          "{}-{}".format(prefix, existing["number"]) != key.upper()) else ""

    def title():
        value = _cell(row, "title")
        if not value:
            raise RowError("Titre vide.", "Chaque ligne doit avoir un titre (colonne « title »).")
        if len(value) > 255:
            raise RowError("Titre de {} caractères.".format(len(value)), "255 caractères au maximum.")
        return value

    def description():
        value = row.get("description") or ""
        if len(value) > 20000:
            raise RowError("Description trop longue.", "20 000 caractères au maximum.")
        return value

    def type_and_status():
        itype = _type(conn, project_id, row)
        if existing and itype["id"] != existing["type_id"]:
            old = conn.execute("SELECT workflow_id, name FROM agile_issue_types WHERE id = ?",
                               (existing["type_id"],)).fetchone()
            if old["workflow_id"] != itype["workflow_id"]:
                raise RowError("Passage du type « {} » à « {} » : les deux types n'ont pas le même "
                               "workflow.".format(old["name"], itype["name"]),
                               "Remettez « {} », ou changez d'abord le workflow du type dans "
                               "Paramètres (admin).".format(old["name"]))
        status, transition = _status(conn, itype, row, existing, role)
        if transition is not None and existing is not None and itype["is_requirement"]:
            from . import goldmine
            blocked = goldmine.verification_guard(conn, existing["id"], status["name"])
            if not blocked:
                from . import qa
                blocked = qa.clarification_guard(conn, existing, status["name"])
            if blocked:
                raise RowError(*blocked)
        if transition is not None and existing is not None and itype["change_role"]:
            from . import changes  # D-B-010: same ECN / PR guards as the ticket page
            blocked = changes.transition_guard(conn, existing, status["name"])
            if blocked:
                raise RowError(*blocked)
        return itype, status, transition

    def client_summary():
        from . import summary
        value = summary.csv_cell(row)
        if value is not None and len(value) > summary.MAX_LENGTH:
            raise RowError(*summary.too_long_message(len(value)))
        return value

    check("title", title)
    check("description", description)
    check("client_summary", client_summary)
    check("type_status", type_and_status)
    check("priority", _priority, row, existing)
    check("assignee_id", _assignee, conn, project_id, row, existing)
    check("sprint_id", _named_ref, conn, project_id, row, "sprint", "agile_sprints", "Sprint",
          "Agile → Backlog → Créer un sprint")
    check("version_id", _named_ref, conn, project_id, row, "version", "agile_versions", "Version",
          "Agile → Paramètres → Versions")
    check("points", _points, row)
    check("due_date", _due_date, row)
    check("labels", _labels, row)
    check("parent_id", _parent, conn, project_id, prefix, row, existing)
    if problems:
        raise RowError(*problems[0], problems=problems)
    itype, status, transition = resolved["type_status"]
    return {
        "existing": existing, "title": resolved["title"], "description": resolved["description"],
        "type": itype, "status": status, "transition": transition,
        "priority": resolved["priority"], "assignee_id": resolved["assignee_id"],
        "sprint_id": resolved["sprint_id"], "version_id": resolved["version_id"],
        "points": resolved["points"], "due_date": resolved["due_date"],
        "labels": resolved["labels"], "parent_id": resolved["parent_id"],
        "client_summary": resolved["client_summary"],
        "unknown_key": unknown_key,
        "stale": bool(existing is not None and _cell(row, "updated_at")
                      and _cell(row, "updated_at") != existing["updated_at"]),
    }
