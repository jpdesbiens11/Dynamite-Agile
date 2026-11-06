"""Tour of the site (0.47.0, D-B-092): the steps of the Help path in the order of the top bar and of a project, the
DEMO exercise of each step, and the one-time update of an existing DEMO Space.

- STEPS is the order of static/js/help/content_path.js (the chapter id is the key; the number is the position).
- TOPIC_CODES keeps the Training topic code of each chapter stable (HL-01…HL-11 were numbered in the 0.37 order:
  a training plan that already holds HL-09 « Timesheet » keeps it); new chapters get the next codes.
- sync(): an existing DEMO gets one ticket per new chapter, its step tickets renumbered to the new order (keys
  and statuses kept), and its wiki home rebuilt -- only if nobody has edited it. Idempotent, journalled (LocalApi).
"""
import re

from .local_api import LocalApi

# (chapter id of the Help path, title, exercise) -- order of the top bar: Accueil, Dashboard | Goldmine … | Tools …
STEPS = [
    ("bienvenue", "Bienvenue, barre du haut et réglages",
     "Lisez la page d'accueil DEMO (Dynamite). Dans le menu à votre nom, essayez le Thème par défaut et Terminal R&D ; "
     "appuyez sur Ctrl+K et tapez « headlamp » ; sur l'Accueil, parcourez « Qui contacter ? »."),
    ("dashboard", "Dashboard et Messages (@mentions)",
     "Ouvrez le Dashboard. Dans votre page d'exercice Dynamite, écrivez « @<votre identifiant> » : une Note arrive dans "
     "Messages → Reçus. Mentionnez un collègue, puis retrouvez le message dans Messages → Envoyés."),
    ("projets", "Spaces, rôles et droits",
     "Sur l'Accueil, repérez votre rôle dans DEMO (Editor) et dans vos Spaces. Qui est l'Assignee de ce ticket ?"),
    ("goldmine", "Goldmine : un requirement",
     "Goldmine → DEMO : lisez les deux Requirements d'exemple, puis créez le vôtre (Statement vérifiable, "
     "Verification Method, Acceptance Criteria, Test Procedure) et faites-le passer « In Analysis »."),
    ("exploration", "Exploration : lire un plan",
     "Exploration → DEMO : repérez les quatre semaines du parcours sur le Gantt, puis « Exporter Excel » et "
     "ouvrez le fichier (feuille « Lisez-moi »)."),
    ("agile", "Agile : mon premier ticket",
     "Créez « Mon premier ticket — <prénom> » ; sur le Board, faites-le avancer jusqu'à Done. Ajoutez un "
     "commentaire coché « Question »."),
    ("changements", "Change Management : un ECN de test",
     "Agile → Change Management : ouvrez un PR de test, « Derive to ECN », ajoutez un Affected Item et lisez ce "
     "qui manque pour « Submit to CCB »."),
    ("dynamite", "Dynamite : ma première page",
     "Ouvrez « Exercice — Ma première page ». Créez une sous-page à votre nom ; ajoutez-y un tableau, un status, "
     "le bloc Ticket de cette étape, puis importez le Markdown d'exemple avec « ✨ Importer d'une IA »."),
    ("testing", "Testing : un test et un Test Plan",
     "Testing → Test Base : créez un test custom (Subject « Electrical Safety »), ouvrez-le et ses requirements ; "
     "cochez-le, « Créer un plan de test avec la sélection », générez le Word, puis passez le plan à Cancelled."),
    ("generator", "Tools : Design et Generator",
     "Tools → Generator → DEMO : réservez une TN (Note technique), étape 09 Recherche des fonctions, titre « Notes DEMO <prénom> » ; "
     "puis Tools → Design : ouvrez la page et la FAQ de la Pugh Matrix."),
    ("training", "Training : mon plan de formation",
     "Training → Mon plan : ajoutez le topic HL-09 (Timesheet) et passez son test ; sous 80 %, reprenez les questions "
     "manquées jusqu'à les réussir : l'item passe à Completed (vert). Votre gestionnaire (l'enseignant) l'évalue et le passe à Achieved."),
    ("timesheet", "Timesheet : ma première semaine",
     "Timesheet : ajoutez une plage sur le Space de votre équipe, code B-09 · Recherche des fonctions, avec la description « Parcours DEMO », "
     "puis soumettez la semaine."),
    ("recherche-audit", "Recherche, palette et Audit",
     "Cherchez « DEMO » dans la barre du haut, puis retrouvez la même page avec Ctrl+K. Envoyez un Audit de test "
     "de type « Question » depuis n'importe quel écran."),
    ("administration", "Admin (administrateurs seulement)",
     "Administrateurs : ouvrez Règles d'accès et exportez le texte ; Admin → Sécurité réseau ; Timesheet → Spaces et "
     "organismes ; Liste Audit : planifiez une observation dans une révision."),
]
TOPIC_CODES = {"bienvenue": "HL-01", "projets": "HL-02", "dynamite": "HL-03", "goldmine": "HL-04", "exploration": "HL-05",
               "agile": "HL-06", "changements": "HL-07", "generator": "HL-08", "timesheet": "HL-09",
               "recherche-audit": "HL-10", "administration": "HL-11", "dashboard": "HL-12", "testing": "HL-13",
               "training": "HL-14"}
WEEKS = [("S1", "Semaine 1", "Découvrir : Help, réglages, Dashboard, Spaces", "Étapes 1 à 3.", "J0"),
         ("S2", "Semaine 2", "Requirements et plan : Goldmine, Exploration", "Étapes 4 et 5.", "S1"),
         ("S3", "Semaine 3", "Exécuter et documenter : Agile, Change Management, Dynamite, Testing", "Étapes 6 à 9.", "S2"),
         ("S4", "Semaine 4", "Outils et suivi : Tools, Training, Timesheet, Recherche, Admin", "Étapes 10 à 14.", "S3")]
SYSTEM_NOTES = ("Parcours DEMO", "Titre marqué [Sandbox]", "Parcours DEMO — tour du site 0.47.0", "Space renommé DEMO", "Space renommé ROVER",
                "Parcours HeadLamp", "Parcours HeadLamp — tour du site 0.47.0")  # 0.60.49: notes written before DEMO
CHAPTER = re.compile(r"#/help/([a-z-]+)\)")


def number(chapter):
    return next(n for n, step in enumerate(STEPS, start=1) if step[0] == chapter)


def ticket_fields(n, chapter, title, exercise):
    return {"title": "Étape {} — {}".format(n, title),
            "description": "{}\n\nAide : Help → chapitre {} (#/help/{}).".format(exercise, n, chapter)}


def step_tickets(conn, pid):
    """chapter id -> {number, title, description} of the existing step tickets of DEMO."""
    out = {}
    for r in conn.execute("SELECT number, title, description FROM agile_issues WHERE project_id = ? AND title LIKE 'Étape %'",
                          (pid,)).fetchall():
        found = CHAPTER.search(r["description"] or "")
        if found:
            out.setdefault(found.group(1), dict(r, key="DEMO-{}".format(r["number"])))
    return out


def sync(ctx, pid, hub_builder):
    """Existing DEMO: add the missing step tickets, renumber the others, refresh the untouched hub page."""
    conn, api = ctx.conn, LocalApi(ctx)
    base = "/api/agile/p/{}".format(pid)
    have = step_tickets(conn, pid)
    epic = conn.execute("SELECT number, description FROM agile_issues WHERE project_id = ? AND title IN ('Parcours DEMO', 'Parcours HeadLamp')",
                        (pid,)).fetchone()
    changed = 0
    for n, (chapter, title, exercise) in enumerate(STEPS, start=1):
        fields = ticket_fields(n, chapter, title, exercise)
        current = have.get(chapter)
        if current is None:
            types = {t["icon_key"]: t for t in api.get(base + "/meta")["types"] if t["bucket"] == "agile"}
            body = dict(fields, type_id=types["task"]["id"], priority="medium")
            if epic:
                body["parent_number"] = epic["number"]
            have[chapter] = dict(api.post(base + "/issues", body), **fields)
            changed += 1
        elif current["title"] != fields["title"] or current["description"] != fields["description"]:
            api.patch(base + "/issues/{}".format(current["number"]), fields)
            changed += 1
    wanted = "Les {} étapes de la prise en main, dans l'ordre du guide Help.".format(len(STEPS))
    if epic and epic["description"] != wanted:
        api.patch(base + "/issues/{}".format(epic["number"]), {"description": wanted})
    _refresh_hub(ctx, api, pid, have, hub_builder)
    return changed


def _refresh_hub(ctx, api, pid, tickets, hub_builder):
    base = "/api/dynamite/p/{}/pages".format(pid)
    home = ctx.conn.execute("SELECT p.id, p.current_version, v.note, v.body FROM dynamite_pages p JOIN dynamite_versions v "
                            "ON v.page_id = p.id AND v.version = p.current_version WHERE p.project_id = ? AND p.parent_id IS NULL "
                            "ORDER BY p.id LIMIT 1", (pid,)).fetchone()
    if home is None or home["note"] not in SYSTEM_NOTES:
        return False  # edited by a person: left alone
    ordered = [tickets[chapter] for chapter, _t, _e in STEPS if chapter in tickets]
    from .headlamp import HUB_MARK  # 0.60.55 (D-O-064): a hub written before « the Rover is the demo » is refreshed once
    body = home["body"] or ""
    if len(ordered) != len(STEPS) or ("Le parcours en {} étapes".format(len(STEPS)) in body and HUB_MARK in body):
        return False
    page = api.get(base + "/{}".format(home["id"]))["page"]
    api.put(base + "/{}".format(home["id"]), {"title": page["title"], "body": hub_builder(ordered),
                                               "base_version": page["version"], "note": SYSTEM_NOTES[2]})
    return True
