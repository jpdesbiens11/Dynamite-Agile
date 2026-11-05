"""DEMO « Base de connaissances (BDC) » section (D-B-033, renamed D-B-040): the main ideas of Getting
Things Done (David Allen), written in our own words, with practical examples
for mechatronic product development done on this platform.

Added once to DEMO (at creation, or at the next start-up for an existing
DEMO): a « Connaissances » hub page and three child pages. Pages are
created through the Dynamite API handlers (local_api), like the rest of
DEMO, so they are validated, versioned and journalled.
"""
from .headlamp import KEY, _doc, _h, _link, _p, _panel, _t, _table, project_id
from .local_api import LocalApi

HUB = "Base de connaissances (BDC)"
OLD_HUB = "Connaissances"  # name before 0.21.0 (D-B-040)
MAIN = "Getting Things Done — les principes"
APPLIED = "GTD appliqué au développement mécatronique"
REVIEW = "Revue hebdomadaire GTD — gabarit"


def _ul(*items):
    return {"type": "bullet_list", "items": [[_p(*i) if isinstance(i, tuple) else _p(i)] for i in items]}


def _ol(*items):
    return {"type": "ordered_list", "items": [[_p(*i) if isinstance(i, tuple) else _p(i)] for i in items]}


def _b(text):
    return _t(text, "bold")


def _nugget(*nodes):
    """A « pépite » (gold nugget): something to remember from the team's own experience."""
    return _p(_t("◆ Pépite — ", "bold", {"type": "color", "color": "orange"}), *nodes)


PEPITE_MARK = "◆ Pépite"  # present in the v2 content (D-B-040): used to upgrade older DEMO pages


def main_page():
    return _doc(
        _panel("info", _p(_b("Getting Things Done (GTD)"), " est la méthode d'organisation personnelle de David Allen : "
                          "votre tête sert à avoir des idées, pas à les retenir. Ce qui vous « travaille » va dans des listes "
                          "fiables, relues chaque semaine ; vous choisissez alors quoi faire en confiance. Cette page garde "
                          "d'abord nos ", _b("pépites"), " : ce qui marche vraiment en équipe de conception.")),
        {"type": "toc"},
        _h(1, "Nos pépites (retour d'expérience)"),
        _nugget(_b("Moins de 2 minutes ? Faites-le maintenant, quand vous y pensez. "),
                "L'organiser coûterait plus cher que le faire. Exemples : répondre « oui, 180 °C ± 10 °C » à une question "
                "Goldmine ; « Prendre le ticket » ; passer un ticket à « In Review » ; envoyer la référence Generator d'un "
                "document ; noter une idée avec le bouton Audit."),
        _nugget(_b("Le calendrier, seulement pour le travail d'équipe. "),
                "Réunions, CCB Reviews, Tests au Test Bench réservés avec d'autres : au calendrier. Le reste n'y va pas : selon "
                "votre niveau d'énergie dans la semaine, réservez des plages de travail et abattez vos listes pendant ces "
                "plages (ex. matinées de conception, après-midis de tests ou de documentation)."),
        _nugget(_b("Des listes simples : 20 éléments au maximum, avec un status. "),
                "Chaque task est simple, claire, et fait avancer le projet concrètement — comme un ticket de sprint Agile. "
                "Au-delà de 20, la liste n'est plus relue : on découpe, on délègue ou on passe au backlog."),
        _nugget(_b("Des listes par contexte, accessibles là où la task se fait. "),
                "Au Test Bench, au poste CAO, au laboratoire, au bureau, au téléphone : un label de contexte "
                "(@banc, @cao, @labo, @appel) sur les tickets et le filtre « Mes éléments » donnent la bonne liste, "
                "sur place, en un clic."),
        _nugget(_b("Vous ne savez pas quoi faire ? "),
                "Prenez la task la plus prioritaire dans le contexte où vous êtes, selon le temps disponible et votre "
                "énergie. C'est l'ordre de David Allen : contexte, temps, énergie, puis priority."),
        _nugget(_b("On planifie en début de semaine, on fait le retour avant de partir pour la fin de semaine. "),
                "Lundi matin : Dashboard, tickets du sprint, plages réservées. Vendredi après-midi : Weekly Review "
                "(gabarit ci-dessous) et Timesheet."),
        _nugget(_b("Des tasks assez petites pour se fermer vite. "),
                "C'est la discrétisation du travail : une task dure une demi-journée au plus, idéalement moins de 2 heures, "
                "et disparaît vite de la liste. « Qualifier l'élément chauffant » est un projet ; « Écrire la Test Procedure "
                "de rigidité diélectrique » est une task."),
        _nugget(_b("Un flux naturel. "),
                "Capturer, clarifier, faire : si la méthode demande un effort de plus que le travail lui-même, elle est trop "
                "lourde. Simplifiez les listes plutôt que d'ajouter des règles."),
        _h(1, "Les cinq étapes de GTD"),
        _table(["Étape", "Ce qu'on fait", "Dans Dynamite | Agile"],
               [_b("1. Capturer"), "Tout noter dans peu d'Inbox, sans trier.",
                "Bouton Audit ; commentaire « Question » ; PR ou bug ; ticket sans détail dans le backlog ; "
                "question client dans Goldmine."],
               [_b("2. Clarifier"), "Est-ce actionnable ? Quelle est la Next Action ? Moins de 2 minutes → maintenant.",
                "Liste Audit ; analyse d'un PR ; requirement « Received » → « In Analysis » ; Q&A."],
               [_b("3. Organiser"), "Chaque chose à sa place : projets, Next Actions, Waiting For, agenda, "
                "Someday / Maybe, référence.",
                "Epic = projet ; ticket assigné = Next Action ; « CCB Review » et « Customer Clarification » = Waiting For ; backlog = Someday / Maybe ; Dynamite et Generator = référence."],
               [_b("4. Revoir"), "Relire assez souvent pour faire confiance aux listes ; Weekly Review.",
                "Dashboard avec « Mes éléments » ; Board du sprint ; gabarit de Weekly Review."],
               [_b("5. Faire"), "Choisir selon le contexte, le temps, l'énergie, puis la priority.",
                "Menu de status du Dashboard ; colonne « To Do » ; heures dans Timesheet avec une description."]),
        _h(1, "Les listes du système"),
        _ul((_b("Next Actions "), "par contexte (@banc, @cao, @labo, @appel, @bureau)."),
            (_b("Projets : "), "chaque résultat en cours a au moins une Next Action."),
            (_b("Waiting For : "), "ce que vous avez délégué ou demandé, avec la date."),
            (_b("Agenda : "), "seulement ce qui a une date ou demande l'équipe (pépite du calendrier)."),
            (_b("Someday / Maybe : "), "les idées sans engagement, relues pendant la revue."),
            (_b("Référence : "), "l'information utile sans action (fiches, standards, comptes rendus).")),
        _h(1, "Les horizons de responsabilité"),
        _table(["Horizon", "Question", "Exemple en conception de produit"],
               ["Sol — actions", "Que dois-je faire ?", "Relancer le Supplier des éléments chauffants"],
               ["1 — projets", "Quels résultats sont en cours ?", "Qualifier l'élément chauffant du prototype 3"],
               ["2 — domaines", "De quoi suis-je responsable ?", "Sous-système de chauffage du produit"],
               ["3 — objectifs 1-2 ans", "Où allons-nous ?", "Prototype fonctionnel validé (voir « Mes objectifs »)"],
               ["4 — vision 3-5 ans", "À quoi ressemble le succès ?", "Gamme de propulsion électrique certifiée"],
               ["5 — raison d'être", "Pourquoi ?", "La mission de l'entreprise"]),
        _panel("note", _p("Sources : David Allen, « Getting Things Done » (édition révisée 2015) et le site "
                          "gettingthingsdone.com (règle des 2 minutes, choix selon contexte / temps / énergie / priority, "
                          "Weekly Review). Résumé avec nos mots ; les pépites viennent de l'expérience des équipes de conception.")),
        _h(1, "Pages de cette section"),
        {"type": "children"})


def applied_page():
    return _doc(
        _panel("info", _p("Des situations réelles d'un produit mécatronique (mécanique, électronique, "
                          "logiciel embarqué, design), traitées avec GTD et les outils de la plateforme. "
                          "Objectif : exécuter comme un dirigeant — peu de choses en tête, tout en mouvement.")),
        {"type": "toc"},
        _h(1, "1. Un Test échoue au banc d'essai (capturer, clarifier)"),
        _p("L'élément chauffant dépasse sa température limite pendant le test d'endurance."),
        _ol(("Capturer ", _b("tout de suite"), " : Agile → Change Management → « Signaler un problème (PR) », "
             "avec la photo et la mesure. Deux minutes, pas plus."),
            ("Clarifier pendant l'analyse : actionnable ? Oui → Root Cause. Si la correction touche la conception, "
             "« Dériver en ECN »."),
            ("Organiser : l'ECN passe « CCB Review » = liste ", _b("Waiting For"), " ; la Next Action "
             "(préparer l'analyse d'impact) devient une sub-task ECN assignée."),
            "S'engager : la sub-task apparaît dans votre Dashboard ; filtre « Mes éléments » pour ne voir qu'elle."),
        _h(1, "2. Une spécification client arrive (organiser la référence)"),
        _ol("Goldmine : importez les requirements (CSV) — chaque requirement est « Received ».",
            "Clarifiez une à une : vérifiable ? verification method (I, A, D, T) ? sinon « Customer Clarification ».",
            "Allouez chaque Requirement « Accepted » à un ticket de travail (lien « implements ») : c'est la Next Action.",
            "Le source document va dans Generator (référence), les notes de lecture dans Dynamite."),
        _h(1, "3. Lancer la conception d'un nouveau produit (planifier naturellement)"),
        _table(["Phase", "Outil", "Exemple concret"],
               ["Raison d'être", "Dynamite", "Page « Pourquoi ce pistolet à colle » : usage, masse, coût cible"],
               ["Vision", "Goldmine", "Requirements de performance et de sécurité, acceptance criteria"],
               ["Remue-méninges", "Dynamite / Audit « Idée »", "Principes de chauffe et d'alimentation de la colle possibles"],
               ["Organisation", "Exploration + Epics Agile", "Gantt : concept, PDR, prototypes, tests, CDR"],
               ["Next Actions", "Tickets Agile assignés", "« Modéliser la chauffe de la buse » à Léa, sprint 3"]),
        _h(1, "4. Réunion de conception (capturer sans perdre)"),
        _ul("Chaque décision → compte rendu Dynamite (référence) ; chaque action → un ticket assigné, créé pendant la réunion.",
            "Une question sans réponse → commentaire « Question » sur le ticket concerné, adressé à la bonne personne.",
            "Rien ne reste dans un carnet : le carnet est une boîte de réception à vider le jour même."),
        _h(1, "5. Déléguer et suivre (liste « En attente »)"),
        _ul("Déléguer = assigner le ticket à la personne. Elle le voit dans son Dashboard.",
            "Vous gardez la trace : filtre du tableau par assigné, ou tickets « In Review » / ECN au CCB.",
            "Un fournisseur doit répondre ? Ticket à votre nom intitulé « Waiting For — réponse Supplier X », échéance = relance."),
        _h(1, "6. Les idées pour plus tard (Someday / Maybe)"),
        _ul("Backlog Agile hors sprint, avec le label « un-jour ».",
            "Observations Audit en status « Nouveau » : relues et planifiées dans une révision lors de la revue."),
        _h(1, "7. La journée d'un ingénieur, version GTD"),
        _table(["Moment", "Action", "Où"],
               ["8 h 00", "Ouvrir le Dashboard : ce qui est en retard, ce qui m'attend", "Dashboard"],
               ["8 h 10", "Activer « Mes éléments », choisir 1 à 3 actions selon le contexte (banc, CAO)", "Barre du haut"],
               ["Journée", "Capturer tout ce qui surgit en moins de 2 minutes", "Audit, PR, ticket"],
               ["16 h 30", "Vider les boîtes : clarifier les captures du jour", "Liste Audit, backlog"],
               ["Vendredi", "Weekly Review puis Timesheet", "Gabarit ci-dessous, Timesheet"]),
        _panel("success", _p(_b("Comme un dirigeant en exécution : "), "il décide vite (clarifier), délègue clairement "
                             "(assigner), suit sans micro-gérer (En attente, Dashboard) et protège une revue "
                             "hebdomadaire. La plateforme fournit chaque liste ; la discipline, c'est la revue.")))


def review_page():
    return _doc(
        _panel("note", _p("Environ 60 minutes, chaque vendredi. Copiez cette page sous votre nom (« + Sous-page »), "
                          "ou suivez-la telle quelle.")),
        _h(1, "Vider"),
        _ol("Rassembler papiers, notes de réunion, courriels : tout ce qui n'est pas encore dans la plateforme.",
            "Créer les tickets, PR, observations Audit correspondants (capturer).",
            "Vider sa tête : écrire tout ce qui préoccupe encore."),
        _h(1, "Mettre à jour"),
        _ol(("Dashboard avec ", _b("Mes éléments"), " : chaque ticket a-t-il un status juste et une Next Action claire ?"),
            "Agenda : échéances passées et des deux prochaines semaines (tickets, tasks Exploration, CCB Reviews).",
            "En attente : relancer ce qui dort (ECN au CCB, questions sans réponse, fournisseurs).",
            "Projets : chaque Epic et chaque ECN ont au moins une Next Action assignée.",
            "Liste Audit : trier les nouvelles observations, en planifier dans une révision."),
        _h(1, "Voir plus loin"),
        _ol("Someday / Maybe : promouvoir, garder ou supprimer.",
            "Horizons : le travail de la semaine sert-il les objectifs du projet (jalons Exploration, requirements Goldmine) ?",
            ("Soumettre la ", _link("Timesheet", "#/timesheet"), " avec une description par plage.")),
        _panel("success", _p("Fin de revue : rien en tête, tout dans le système. Lundi, ouvrez le ",
                             _link("Dashboard", "#/dashboard"), " et engagez-vous.")))


def _find(pages, title):
    return next((p for p in pages if p["title"] == title), None)


def _rewrite(api, base, page_id, title=None, body=None, note=""):
    page = api.get(base + "/{}".format(page_id))["page"]
    api.put(base + "/{}".format(page_id), {"title": title or page["title"], "body": body or page["body"],
                                           "base_version": page["version"], "note": note})


def ensure(ctx):
    """Create or upgrade the « Base de connaissances (BDC) » section (idempotent, title-based):
    renames the pre-0.21 « Connaissances » hub and rewrites the GTD page with the pépites
    (a new version, the old one stays in the history)."""
    pid = project_id(ctx.conn)
    if pid is None:
        return False
    api = LocalApi(ctx)
    base = "/api/dynamite/p/{}/pages".format(pid)
    pages = api.get(base)["pages"]
    hub = _find(pages, HUB)
    old = _find(pages, OLD_HUB)
    changed = False
    if hub is None and old is not None:
        _rewrite(api, base, old["id"], title=HUB, note="Renommée « Base de connaissances (BDC) »")
        hub, changed = old, True
    if hub is None:
        root = next((p for p in pages if not p.get("parent_id")), pages[0])
        made = api.post(base, {"title": HUB, "parent_id": root["id"], "body": _doc(
            _p("Les méthodes et savoirs utiles à tous, reliés à l'outil : Getting Things Done, la structure des fonctions du produit, le glossaire."),
            {"type": "children"})})
        hub_id = (made.get("page") or made)["id"]
        main = api.post(base, {"title": MAIN, "parent_id": hub_id, "body": main_page()})
        main_id = (main.get("page") or main)["id"]
        api.post(base, {"title": APPLIED, "parent_id": main_id, "body": applied_page()})
        api.post(base, {"title": REVIEW, "parent_id": main_id, "body": review_page()})
        ensure_policy(ctx)
        return True
    main = _find(pages, MAIN)
    if main is not None:
        body = api.get(base + "/{}".format(main["id"]))["page"]["body"]
        if PEPITE_MARK not in str(body):
            _rewrite(api, base, main["id"], body=main_page(), note="Pépites (0.21.0)")
            changed = True
    return ensure_policy(ctx) or changed


LEAVE_TITLE = "Politique de l'équipe — vacances et congés"
POLICY_HUB = "Politiques de l'équipe"


def leave_page():
    return _doc(
        _panel("warning", _p(_b("À compléter par l'équipe ou la direction. "), "Cette page porte vos principes sur les "
                             "vacances et congés ; les valeurs entre crochets sont à confirmer avant diffusion.")),
        _h(1, "Vacances"),
        _ul("Banque annuelle : [à confirmer] heures, au prorata [à confirmer].",
            "Demande à son approbateur au moins [à confirmer] semaines à l'avance pour une absence de plus de 3 jours.",
            ("Dans Timesheet : Space ", _b("INT"), ", code ", _b("INT-VAC · Vacances"), " — chaque heure est déduite de "
             "votre banque (solde affiché en haut de la semaine, visible par votre approbateur).")),
        _h(1, "Congé santé"),
        _ul("Un congé santé peut être accordé sous approbation, sans être déduit de la banque de vacances [à confirmer].",
            ("Dans Timesheet : Space ", _b("INT"), ", code ", _b("INT-SAN · Congé santé"), " ; aucune justification médicale "
             "n'est saisie dans la plateforme.")),
        _h(1, "Projets financés"),
        _p("Les vacances et les congés ne sont jamais réclamés à un organisme : INT-VAC et INT-SAN ne sont pas « réclamables » "
           "et ne sortent pas dans l'export Excel ni dans le rapport Word d'une réclamation."),
        _h(1, "Où régler sa banque et son approbateur"),
        _p("Menu à votre nom → Paramètres → « Feuille de temps » : banque de vacances à une date, et approbateur. "
           "Un administrateur peut corriger ces valeurs (⚙ Admin → Comptes → « Feuille de temps… ») ; chaque changement est "
           "journalisé."))


def ensure_policy(ctx):
    """The leave principles live in the internal Space INT, under « Politiques de l'équipe » (once; never rewritten)."""
    from modules.timesheet import catalog
    from . import reference
    pid = reference.space(ctx.conn, catalog.INTERNAL_KEY)  # 0.60.41 (D-O-050): INT on an older installation, else DEMO
    if pid is None:
        return False
    row = {"id": pid}
    api = LocalApi(ctx)
    base = "/api/dynamite/p/{}/pages".format(row["id"])
    pages = api.get(base)["pages"]
    if _find(pages, LEAVE_TITLE) is not None:
        return False
    hub = _find(pages, POLICY_HUB)
    if hub is None:
        root = next((p for p in pages if not p.get("parent_id")), None)
        made = api.post(base, {"title": POLICY_HUB, "parent_id": root["id"] if root else None, "body": _doc(
            _p("Les principes qui s'appliquent à toute l'équipe : congés, horaires, déplacements…"), {"type": "children"})})
        hub = {"id": (made.get("page") or made)["id"]}
    api.post(base, {"title": LEAVE_TITLE, "parent_id": hub["id"], "body": leave_page()})
    return True
