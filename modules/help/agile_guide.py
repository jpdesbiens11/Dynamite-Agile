"""« Méthode Agile avec l'outil Agile — guide pas à pas » (D-A-050): the Agile method (Scrum style) explained with the
names of the functions of the Agile tab, a worked example on the team project Space EQP, fall-backs, pros and cons,
limitations, known issues and a FAQ -- in French, technical terms in English (D-B-085). Page of the « Base de
connaissances (BDC) » of DEMO, generated at start-up while nobody edited it. Screenshots (guide_agile/*.png),
when the folder holds some, are stored once as images of the DEMO Space; 0.60.01 ships none (the former ones
showed the former example and are to be redone on the example team).
"""
import json
from pathlib import Path

from . import gtd
from .headlamp import _doc, _h, _link, _p, _panel, _table
from .local_api import LocalApi

TITLE = "Méthode Agile avec l'outil Agile — guide pas à pas"
GENERATED = "Généré — guide Agile"
IMAGES = Path(__file__).parent / "guide_agile"
SHOTS = ["01_backlog", "02_create_sprint", "03_sprint_planned", "04_start_sprint", "05_board", "06_ticket",
         "07_create_ticket", "08_settings"]
_b, _ul = gtd._b, gtd._ul


def _ol(*items):
    return gtd._ol(*items)


def _step(n, title, ids, shot, alt, *items):
    """One step; its screenshot when one was stored (none: the text alone)."""
    image = [{"type": "image", "id": ids[shot], "alt": alt}] if shot and shot in ids else []
    return [_h(3, "Étape {} — {}".format(n, title)), _ol(*items)] + image


def body(ids):
    blocks = [
        _panel("info", _p(_b("En bref : "), "la méthode Agile découpe un gros travail en petits morceaux (tickets), qu'on "
                          "réalise par courtes périodes de 1 à 3 semaines (Sprints). À la fin de chaque Sprint, on montre ce "
                          "qui est fait, on apprend, et on ajuste la suite. L'onglet ", _b("Agile"), " de la plateforme est "
                          "l'outil de ticket (comme Jira) qui porte cette méthode.")),
        _h(2, "1. Le vocabulaire (termes de l'outil)"),
        _table(["Terme", "Où dans l'outil", "Ce que c'est"],
               ["Backlog", "Agile → Backlog", "La liste priorisée de tout ce qu'il reste à faire, du plus important au moins important."],
               ["Sprint", "Backlog → « Créer un sprint »", "Une période fixe (ex. 2 semaines) avec un objectif et une sélection de tickets."],
               ["Board", "Agile → Board", "Le tableau du Sprint actif : une colonne par status (To Do, In Progress, In Review, Done)."],
               ["Epic", "Type de ticket", "Un gros sujet (ex. « Sous-système de chauffage »), découpé en Stories et Tasks."],
               ["Story / Task", "Type de ticket", "Un morceau de travail réalisable dans un Sprint ; Story = valeur pour l'utilisateur, Task = travail technique."],
               ["Sub-task", "Fiche du ticket → Sous-tickets", "Une étape d'une Story ou d'une Task."],
               ["Bug, PR, ECN", "Agile → Change Management", "Problèmes et modifications (voir le guide Change Management)."],
               ["Story Points", "Champ « Points »", "L'effort estimé, en valeur relative (1, 2, 3, 5, 8…), pas en heures."],
               ["Assignee", "Champ « Assignee »", "La personne qui réalise le ticket ; elle seule (ou un administrateur) le modifie."],
               ["Status", "Menu en haut à droite de la fiche", "L'étape du workflow : To Do → In Progress → In Review → Done."],
               ["Labels, Version", "Champs de la fiche", "Étiquettes libres et version livrable visée (ex. v1.0)."]),
        _h(2, "2. Les rôles"),
        _table(["Rôle Agile", "Qui dans l'équipe", "Dans l'outil"],
               ["Product Owner", "Le chef de projet de l'équipe (ou l'enseignant)", "Priorise le Backlog (flèches ↑ ↓), écrit les Epics et Stories."],
               ["Équipe", "Les étudiants de l'équipe", "Editor du Space : créent, prennent et font avancer les tickets."],
               ["Facilitateur (Scrum Master)", "Un membre de l'équipe, en rotation", "Anime les réunions, lève les obstacles."],
               ["Admin du Space", "Le responsable du Space", "Paramètres du Space : workflow, types, labels, versions, membres."]),
        _h(2, "3. Le cycle en un coup d'œil"),
        _ol("Remplir et prioriser le Backlog.", "Sprint Planning : choisir ce qui entre dans le prochain Sprint.",
            "Démarrer le Sprint avec un objectif et des dates.", "Chaque jour : un court point (Daily, 15 min) devant le Board.",
            "Fin du Sprint : Sprint Review (on montre le résultat), puis Retrospective (on améliore la façon de travailler).",
            "Clôturer le Sprint ; recommencer."),
        _h(2, "4. Pas à pas — exemple sur le Space EQP (Projet d'équipe)"),
    ]
    blocks += _step(1, "Préparer le Space (Admin du Space)", ids, "08_settings", "Paramètres du Space : Standard Workflow",
                    "Agile → marge gauche → « ⚙ Admin » → « Paramètres du Space ».",
                    "Vérifiez le workflow (Statuses et Transitions), les types de ticket, les labels et les versions.",
                    "Un ticket ne change de status que par une transition listée : ajoutez-en une au besoin (« Ajouter la transition »).")
    blocks += _step(2, "Remplir le Backlog", ids, "07_create_ticket", "Fenêtre « Créer un ticket »",
                    "« Créer un ticket » : choisissez le Type (Epic, Story, Task…), un Title court et précis, une Description.",
                    "Parent : le numéro de l'Epic ; Points : l'effort estimé ; Assignee : laissez « Non assigné » si personne n'est choisi.",
                    "Écrivez les critères de fin dans la Description (« Terminé quand… »).")
    blocks += _step(3, "Prioriser", ids, "01_backlog", "Backlog de EQP",
                    "Agile → Backlog : les tickets les plus importants en haut, avec les flèches ↑ ↓.",
                    "Découpez tout ticket trop gros (plus de 8 points) en plusieurs Tasks ou en Sub-tasks.")
    blocks += _step(4, "Créer le Sprint", ids, "02_create_sprint", "Sprint 1 créé, à venir",
                    "Backlog → « Créer un sprint » : « Sprint 1 » apparaît en haut, « À venir ».")
    blocks += _step(5, "Sprint Planning : choisir les tickets", ids, "03_sprint_planned", "4 tickets, 16 points dans Sprint 1",
                    "Dans la liste à droite de chaque ticket, choisissez « Sprint 1 ».",
                    "Regardez le total de points du Sprint : visez ce que l'équipe a réellement terminé les Sprints précédents.",
                    "Chaque ticket du Sprint doit avoir un Assignee et des Points.")
    blocks += _step(6, "Démarrer le Sprint", ids, "04_start_sprint", "Fenêtre « Démarrer Sprint 1 »",
                    "« Démarrer » à droite du Sprint : écrivez l'Objectif (une phrase), la date de Début et la date de Fin.",
                    "« Démarrer le sprint » : un seul Sprint peut être actif à la fois par Space.")
    blocks += _step(7, "Travailler chaque jour sur le Board", ids, "05_board", "Board du Sprint actif",
                    "Agile → Board : glissez votre carte de To Do vers In Progress quand vous commencez, puis In Review, puis Done.",
                    "Daily (15 min) : chacun dit ce qu'il a fini, ce qu'il fait aujourd'hui, ce qui le bloque.",
                    "Filtres « All Assignees », « All Types », « All Labels » ; « Mes éléments » en haut ne montre que vos tickets.")
    blocks += _step(8, "Suivre et documenter un ticket", ids, "06_ticket", "Fiche d'un ticket",
                    "Cliquez sur une carte : Status (en haut à droite), Assignee, Priority, Labels, Sprint, Version, Points, Due Date.",
                    "Links : « implémente » un requirement Goldmine (traçabilité) ; Sous-tickets : les étapes.",
                    "Commentaires : écrivez « @identifiant » pour prévenir un collègue (pastille rouge sur son Dashboard) ; cochez "
                    "« Question » pour une question ouverte.")
    blocks += _step(9, "Terminer le Sprint", ids, None, "",
                    "Sprint Review : montrez ce qui est Done (démonstration, pas de diapositives).",
                    "Retrospective : ce qui a bien marché, ce qui a moins bien marché, une action d'amélioration — notez-la dans une "
                    "page Dynamite du Space.",
                    "Backlog → « Clôturer » : les tickets non terminés retournent automatiquement au Backlog.")
    blocks += _step(10, "Recommencer", ids, None, "", "« Créer un sprint » (Sprint 2), repriorisez le Backlog, et reprenez à l'étape 5.")
    blocks += [
        _h(2, "5. Retours arrière (quand ça ne se passe pas comme prévu)"),
        _table(["Situation", "Quoi faire dans l'outil"],
               ["Un ticket est trop gros pour le Sprint", "Découpez-le : « Créer un ticket » avec Parent = ce ticket, ou Sous-tickets → Ajouter."],
               ["Le Sprint est surchargé", "Dans le Backlog, remettez des tickets sur « Backlog » avec leur liste ; gardez l'Objectif."],
               ["Un ticket est passé au mauvais status", "Menu Status → la transition inverse (ex. « Back to In Progress ») ; s'il n'y en a pas, "
                "l'Admin du Space l'ajoute dans Paramètres du Space."],
               ["Je ne peux pas modifier un ticket", "Seul son Assignee (ou un administrateur) le modifie : commentez, ou prenez-le s'il n'est pas assigné."],
               ["Le Sprint a été démarré trop tôt", "Terminez-le (« Clôturer ») : les tickets reviennent au Backlog, puis créez-en un nouveau."],
               ["Un travail imprévu urgent arrive", "Créez le ticket, mettez-le dans le Sprint actif, et retirez un ticket d'effort équivalent."],
               ["L'import CSV refuse des lignes", "Lisez le message : chaque ligne fautive est nommée avec son correctif ; corrigez le fichier et réimportez."]),
        _h(2, "6. Pour et contre"),
        _table(["Pour", "Contre"],
               ["Des résultats visibles toutes les 1 à 3 semaines", "Demande de la discipline : Daily, Review et Retrospective à chaque Sprint"],
               ["Les priorités s'ajustent souvent, sans tout replanifier", "Peu adapté seul aux jalons fixes d'un cours (revues de fin de phase : à combiner avec Exploration)"],
               ["Chacun voit qui fait quoi (Board)", "Estimer en points s'apprend : les premiers Sprints sont souvent mal dosés"],
               ["La traçabilité est gardée (liens vers Goldmine, historique)", "Un Backlog non tenu à jour devient vite une liste inutile"]),
        _h(2, "7. Limites de l'outil"),
        _ul("Un seul Sprint actif à la fois par Space.",
            "Pas de graphique de vélocité ni de burndown : faites le total des points Done à chaque Clôture (notez-le dans la page de Retrospective).",
            "Pas de suivi des heures dans Agile : les heures se déclarent dans Timesheet.",
            "Pas de notification par courriel (fonction réservée) : utilisez les @mentions (pastille sur le Dashboard).",
            "Un ticket se modifie par son Assignee ou un administrateur seulement (règle de traçabilité D-B-017)."),
        _h(2, "8. Problèmes connus"),
        _ul("« Initiales requises » à la première écriture : définissez vos 3 lettres dans le menu à votre nom → Paramètres.",
            "Une carte ne se glisse pas sur le Board : vous n'êtes pas son Assignee, ou la transition n'existe pas dans le workflow.",
            "« Un sprint est déjà actif : clôturez-le d'abord » : c'est normal, un seul Sprint actif par Space.",
            "Un ticket clôturé avec le Sprint revient au Backlog même s'il était presque fini : c'est voulu, il sera replanifié."),
        _h(2, "9. FAQ"),
        _ul("« Combien de temps dure un Sprint ? » 2 semaines est un bon départ ; gardez la même durée d'un Sprint à l'autre.",
            "« Faut-il estimer en heures ? » Non : en Story Points relatifs (1, 2, 3, 5, 8). Comparez à un ticket de référence.",
            "« Qui décide de l'ordre du Backlog ? » Le Product Owner, avec l'équipe.",
            "« Et les remises du cours ? » Un Epic par boucle du PDP (MVP 0 à 3, jusqu'à sa revue : Lean Canvas, Concept Review, PDR / CDR, Validation Report) ; ses Stories et Tasks dans les "
            "Sprints, et la date de remise dans Exploration.",
            "« Où parler d'un ticket ? » Dans ses commentaires, avec @identifiant : la discussion reste au bon endroit.",
            "« Comment voir mon travail ? » Le Dashboard, et « Mes éléments » dans la barre du haut."),
        _p("Voir aussi : ", _link("Help — Agile : exécuter", "#/help/agile"), " · ",
           _link("Help — Change Management", "#/help/changements"), " · ", _link("Board EQP", "#/agile/EQP/board"), "."),
    ]
    return _doc(*blocks)


def _images(ctx, pid):
    """Store the screenshots once as images of the DEMO Space (deduplicated by content)."""
    from core import uploads
    ids = {}
    for name in SHOTS:
        path = IMAGES / (name + ".png")
        if path.exists():
            row = uploads._store(ctx, pid, "dynamite", uploads.Upload(path.read_bytes(), "image/png", name + ".png"), "image/png")
            ids[name] = row["id"]
    return ids


def _refresh_images(ctx, api, base, page_id, pid):
    """D-B-095 / D-B-096: a page edited by hand keeps its text, but its screenshots follow the current ones -- an image
    block pointing to an older stored copy of a screenshot (same file name) is pointed to the current copy."""
    current = _images(ctx, pid)
    names = {r["id"]: r["original_name"][:-4] for r in ctx.conn.execute(
        "SELECT id, original_name FROM attachments WHERE project_id = ? AND module = 'dynamite' AND original_name LIKE '0%.png'", (pid,))}
    full = api.get(base + "/{}".format(page_id))["page"]
    changed = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "image" and node.get("id") in names:
                new = current.get(names[node["id"]])
                if new and new != node["id"]:
                    node["id"] = new
                    changed.append(new)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    body = full.get("body")
    walk(body)
    if changed:
        api.put(base + "/{}".format(page_id), {"title": full["title"], "body": body, "base_version": full["version"],
                                               "note": GENERATED + " (captures)"})
    return bool(changed)


def ensure(ctx):
    from modules.dynamite import content
    pid = gtd.project_id(ctx.conn)
    if pid is None:
        return False
    api = LocalApi(ctx)
    base = "/api/dynamite/p/{}/pages".format(pid)
    pages = api.get(base)["pages"]
    hub = next((p for p in pages if p["title"] == gtd.HUB), None)
    page = next((p for p in pages if p["title"] == TITLE), None)
    doc = body(_images(ctx, pid))
    if page is None:
        api.post(base, {"title": TITLE, "parent_id": hub["id"] if hub else None, "body": doc})
        return True
    versions = ctx.conn.execute("SELECT author_id, note FROM dynamite_versions WHERE page_id = ?", (page["id"],)).fetchall()
    if not all(v["author_id"] == ctx.user["id"] and ((v["note"] or "").startswith(GENERATED) or (v["note"] or "") in ("", "Création"))
               for v in versions):
        return _refresh_images(ctx, api, base, page["id"], pid)  # edited by hand: only the screenshots are renewed
    full = api.get(base + "/{}".format(page["id"]))["page"]
    if full.get("body") != json.loads(content.validate(doc)):
        api.put(base + "/{}".format(page["id"]), {"title": TITLE, "body": doc, "base_version": full["version"], "note": GENERATED})
    return True
