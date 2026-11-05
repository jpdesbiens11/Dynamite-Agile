"""HeadLamp: the learning project (D-B-024) -- a sandbox that walks a new user
through the platform in the same order as the Help path (#/help/<chapter>).

Created once at start-up, through the same API handlers a user would call
(local_api), so everything is validated and journalled:
- Agile: epic « Parcours HeadLamp » + one ticket per step (Étape 1 … 14, modules/help/tour.py);
- Dynamite: the home page becomes the hub of the path; child pages hold the
  exercises (first page, AI import) and a syntax cheat sheet;
- Goldmine: two example requirements traced to their step tickets;
- Exploration: a four-week onboarding plan;
- Generator: an example reference (the user guide);
- Timesheet: closed (the time sheet exercise uses the team Space and a time code of the PDP).
Every active user becomes an editor at creation; later accounts join from
the Help screen (« Rejoindre HeadLamp »).
"""
from core import audit, permissions
from core.errors import ApiError

from .local_api import LocalApi

KEY = "HEADLAMP"
NAME = "HeadLamp [Sandbox] — Prise en main"  # D-B-054: « [Sandbox] » everywhere
HOME_TITLE = "HeadLamp [Sandbox] — Bienvenue"
OLD_HOME_TITLE = "HeadLamp — Bienvenue"
DESCRIPTION = ("Projet d'apprentissage : un bac à sable pour essayer chaque outil dans l'ordre du guide Help. "
               "Rien ici ne touche aux vrais projets.")

from .tour import STEPS, TOPIC_CODES, WEEKS, number, ticket_fields  # noqa: E402,F401 (0.47.0: order of the tour)


def _t(text, *marks):
    node = {"type": "text", "text": text}
    if marks:
        node["marks"] = list(marks)
    return node


def _link(text, href):
    return _t(text, {"type": "link", "href": href})


def _p(*nodes):
    return {"type": "paragraph", "content": [n if isinstance(n, dict) else _t(n) for n in nodes]}


def _h(level, text):
    return {"type": "heading", "level": level, "content": [_t(text)]}


def _panel(kind, *blocks):
    return {"type": "panel", "kind": kind, "content": list(blocks)}


def _cells(row):
    return [[c] if isinstance(c, dict) else ([_t(c)] if c else []) for c in row]


def _table(header, *rows):
    return {"type": "table", "header": True, "rows": [_cells(header)] + [_cells(r) for r in rows]}


def _doc(*blocks):
    return {"type": "doc", "content": list(blocks)}


SAMPLE_MARKDOWN = """## Compte rendu — Review du prototype 3

**Décision :** on garde l'élément chauffant actuel.

- [x] Température de la buse mesurée
- [ ] Test de Thermal Cut-off

| Paramètre | Valeur |
|---|---|
| Nominal Voltage | 120 V |

> [!WARNING]
> Surface chaude : ne pas toucher la buse."""


def project_id(conn):
    row = conn.execute("SELECT id FROM projects WHERE key = ?", (KEY,)).fetchone()
    return row["id"] if row else None


def label_sandbox(ctx):
    """D-B-054: an existing HEADLAMP space (and its wiki home) gets the « [Sandbox] » mark. Journalled."""
    from core import audit
    pid = project_id(ctx.conn)
    if pid is None:
        return False
    changed = False
    row = ctx.conn.execute("SELECT name FROM projects WHERE id = ?", (pid,)).fetchone()
    if "[Sandbox]" not in row["name"]:
        ctx.conn.execute("UPDATE projects SET name = ? WHERE id = ?", (NAME, pid))
        audit.log_action(ctx.conn, None, "project_renamed", "project", pid, {"name": NAME}, None)
        changed = True
    home = ctx.conn.execute("SELECT id FROM dynamite_pages WHERE project_id = ? AND title = ?", (pid, OLD_HOME_TITLE)).fetchone()
    if home is not None:
        api = LocalApi(ctx)
        url = "/api/dynamite/p/{}/pages/{}".format(pid, home["id"])
        page = api.get(url)["page"]
        api.put(url, {"title": HOME_TITLE, "body": page["body"], "base_version": page["version"],
                      "note": "Titre marqué [Sandbox]"})
        changed = True
    return changed


def ensure(ctx):
    pid = project_id(ctx.conn)
    if pid is not None:
        from . import tour
        label_sandbox(ctx)
        return tour.sync(ctx, pid, build_hub)  # 0.47.0: the tour of the site reaches an existing HeadLamp
    return ensure_space(ctx)


def ensure_space(ctx):
    """0.60.41 (D-O-050): HeadLamp with its sandbox content, created by whichever start-up hook needs it first (it is
    also the library of reference content, see reference.py)."""
    pid = project_id(ctx.conn)
    if pid is not None:
        return pid
    from core import admin
    from modules.timesheet import manage as timesheet
    pid = admin.create_project_record(ctx, KEY, NAME, DESCRIPTION)["id"]
    api = LocalApi(ctx)
    tickets = _agile(api, pid)
    _goldmine(api, pid, tickets)
    _dynamite(api, pid, tickets)
    _exploration(api, pid)
    api.post("/api/codex/p/{}/refs".format(pid), {"doc_type": "MAN", "step": "03", "sub": "00",
                                                  "system_code": "HEADLAMP", "revision": 1,
                                                  "title": "Guide de prise en main de la plateforme"})
    timesheet.save_settings(ctx.conn, pid, organism="Interne", enabled=False)
    for user in ctx.conn.execute("SELECT id FROM users WHERE is_active = 1 AND is_admin = 0").fetchall():
        ctx.conn.execute("INSERT OR IGNORE INTO memberships (user_id, project_id, role) VALUES (?, ?, 'editor')",
                         (user["id"], pid))
    return pid


def _agile(api, pid):
    base = "/api/agile/p/{}".format(pid)
    types = {t["icon_key"]: t for t in api.get(base + "/meta")["types"] if t["bucket"] == "agile"}
    epic = api.post(base + "/issues", {"type_id": types["epic"]["id"], "title": "Parcours HeadLamp", "priority": "high",
                                       "description": "Les {} étapes de la prise en main, dans l'ordre du guide Help.".format(len(STEPS))})
    tickets = []
    for n, (chapter, title, exercise) in enumerate(STEPS, start=1):
        tickets.append(api.post(base + "/issues", dict(ticket_fields(n, chapter, title, exercise), type_id=types["task"]["id"],
                                                       priority="medium", parent_number=epic["number"])))
    return tickets


def _goldmine(api, pid, tickets):
    base = "/api/agile/p/{}".format(pid)
    examples = [
        ("bienvenue", "Prise en main en une semaine", {
            "external_id": "HL-001", "category": "performance", "verification_method": "D", "test_ref": "TST-VER-03",
            "statement": "Un nouveau membre de l'équipe doit pouvoir réaliser les étapes du parcours HeadLamp (hors Admin) en moins "
                         "de 5 jours ouvrables.",
            "acceptance_criteria": "Les tickets d'étape (hors Admin) sont faits par le nouveau membre en 5 jours ou moins.",
            "source_doc": "Exemple HeadLamp", "allocation": "Training"}),
        ("timesheet", "Heures de formation déclarées", {
            "external_id": "HL-002", "category": "functional", "verification_method": "I", "test_ref": "TST-VER-01",
            "statement": "Chaque séance de travail doit être déclarée dans Timesheet, avec le code de l'étape du PDP travaillée.",
            "acceptance_criteria": "Une plage avec un code du PDP et une description existe dans la première semaine soumise.",
            "source_doc": "Exemple HeadLamp", "allocation": "Timesheet"}),
    ]
    for chapter, title, fields in examples:
        req = api.post(base + "/goldmine/requirements", dict(fields, title=title))
        api.post(base + "/issues/{}/links".format(tickets[number(chapter) - 1]["number"]),
                 {"link_type": "implements", "target_key": req["key"]})


def build_hub(tickets):
    """Wiki home of HeadLamp: the path table (one row per step, in the order of the tour) and the first tickets."""
    rows = [[str(n), title, _link("Chapitre {}".format(n), "#/help/" + chapter), tickets[n - 1]["key"]]
            for n, (chapter, title, _ex) in enumerate(STEPS, start=1)]
    return _doc(
        _panel("info", _p(_t("Bienvenue dans HeadLamp.", "bold"), " Ce projet est un bac à sable : suivez les étapes dans "
                          "l'ordre, avec le guide ", _link("Help", "#/help"), " ouvert à côté. Rien ici ne touche aux vrais projets.")),
        {"type": "toc"},
        _h(1, "Le parcours en {} étapes".format(len(STEPS))),
        _table(["Étape", "Ce que vous apprenez", "Aide", "Ticket"], *rows),
        _panel("success", _p("Dans Timesheet, chaque séance de travail se déclare sur le Space de votre équipe, avec le "
                             "code de l'étape du PDP : ", _t("A-01 … D-21", "bold"), ".")),
        _h(1, "Vos tickets de parcours"),
        *[{"type": "ticket", "key": t["key"]} for t in tickets[:3]],
        _p("… et les suivants dans ", _link("Agile → HEADLAMP", "#/agile/{}/backlog".format(KEY)), "."),
        _h(1, "Pages d'exercice"),
        {"type": "children"})


def _dynamite(api, pid, tickets):
    base = "/api/dynamite/p/{}/pages".format(pid)
    home = api.get(base)["pages"][0]
    page = api.get(base + "/{}".format(home["id"]))["page"]
    hub = build_hub(tickets)
    api.put(base + "/{}".format(home["id"]), {"title": HOME_TITLE, "body": hub,
                                               "base_version": page["version"], "note": "Parcours HeadLamp"})
    api.post(base, {"title": "Exercice — Ma première page", "parent_id": home["id"], "body": _doc(
        _panel("note", _p("Étape {} du parcours — ".format(number("dynamite")), _link("Aide : Dynamite", "#/help/dynamite"))),
        _h(1, "To Do"),
        {"type": "ordered_list", "items": [[_p(x)] for x in (
            "Sur cette page, cliquez « + Sous-page » et nommez-la « Page de <votre prénom> ».",
            "Dans votre page : ajoutez un tableau (menu « / »), un status coloré et le bloc Ticket de cette étape.",
            "Cliquez « ✨ Importer d'une IA », collez le Markdown ci-dessous, vérifiez l'aperçu puis insérez.",
            "Enregistrez (Ctrl+S), puis ouvrez « Historique » pour voir vos versions.")]},
        {"type": "ticket", "key": tickets[number("dynamite") - 1]["key"]},
        _h(1, "Markdown d'exemple à importer"),
        {"type": "code", "lang": "markdown", "text": SAMPLE_MARKDOWN},
        _h(1, "Ce que donne le résultat"),
        _table(["Élément", "Exemple"], ["Status", {"type": "status", "text": "IN PROGRESS", "color": "blue"}],
               ["Couleur", _t("texte en rouge", {"type": "color", "color": "red"})]),
        _panel("warning", _p("Pour la vraie documentation, travaillez dans le Space Dynamite de votre projet.")))})
    api.post(base, {"title": "Aide-mémoire — syntaxe du mode Source", "parent_id": home["id"], "body": _doc(
        _p("Le mode Source de l'éditeur accepte cette syntaxe courte (même résultat que l'éditeur visuel) :"),
        _table(["Syntaxe", "Résultat"],
               ["# Titre / ## Sous-titre / ### Level 3", "Titres"],
               ["**gras**  *italique*  __souligné__  ~~barré~~  `code`", "Mise en forme"],
               ["[texte](https://…)  ou  [texte](#/dynamite/CLE)", "Lien externe ou interne"],
               ["- élément   /   1. élément", "Listes"],
               ["> citation", "Citation"],
               ["```langage … ```", "Bloc de code"],
               [":::info … :::  (info, note, warning, success)", "Panneau"],
               ["[[CLE-12]] seul sur sa ligne", "Bloc Ticket vivant"],
               ["{{red:texte}}  /  {{status:green:DONE}}", "Couleur / status"],
               ["[[toc]]  /  [[sous-pages]]", "Table des matières / sous-pages"],
               ["---", "Séparateur"]))})


def _exploration(api, pid):
    base = "/api/exploration/p/{}".format(pid)
    weeks = WEEKS
    for code, phase, title, description, pred in weeks:
        api.post(base + "/tasks", {"code": code, "phase": phase, "title": title, "description": description,
                                   "duration_weeks": 1, "predecessors": pred})
    api.post(base + "/tasks", {"code": "FIN", "phase": "Semaine 4", "title": "Prise en main terminée",
                               "duration_weeks": 0, "predecessors": "S4"})


# --------------------------------------------------------------------------
# API for the Help screen
# --------------------------------------------------------------------------
def api_status(ctx):
    pid = project_id(ctx.conn)
    if pid is None:
        return {"project": None}
    role = permissions.project_role(ctx.conn, ctx.user, pid)
    rows = ctx.conn.execute(
        "SELECT i.number, i.title, s.name AS status FROM agile_issues i JOIN agile_statuses s ON s.id = i.status_id "
        "WHERE i.project_id = ? AND i.title LIKE 'Étape %' ORDER BY i.number", (pid,)).fetchall()
    from .tour import step_tickets
    by_chapter = {chapter: {"key": t["key"], "number": t["number"]} for chapter, t in step_tickets(ctx.conn, pid).items()}
    steps = {}
    for r in rows:
        try:
            n = int(r["title"].split(" ")[1])
        except (IndexError, ValueError):
            continue
        steps[n] = {"key": "{}-{}".format(KEY, r["number"]), "number": r["number"], "status": r["status"]}
    for chapter, t in by_chapter.items():  # 0.47.0: the Help screen finds the exercise by chapter, whatever its number
        t["status"] = next((s["status"] for s in steps.values() if s["number"] == t["number"]), "")
    return {"project": {"id": pid, "key": KEY, "name": NAME}, "role": role, "member": role is not None, "steps": steps,
            "by_chapter": by_chapter}


def api_join(ctx):
    pid = project_id(ctx.conn)
    if pid is None:
        raise ApiError(404, "Le projet HeadLamp n'existe pas encore. Correctif : redémarrez le serveur, il le crée au démarrage.")
    if permissions.project_role(ctx.conn, ctx.user, pid) is None:
        ctx.conn.execute("INSERT INTO memberships (user_id, project_id, role) VALUES (?, ?, 'editor')", (ctx.user["id"], pid))
        audit.log_action(ctx.conn, ctx.user["id"], "headlamp_joined", "project", pid, None, ctx.ip)
    return api_status(ctx)

