"""« Mettre à jour le site (Admin → Update) — pas à pas » (D-A-049; three parts and the step-by-step review, D-B-094; one tab
« Update et sauvegardes » with five parts and the 2 × 3 chances, D-B-104 / D-B-105): the step-by-step guide, in plain words,
in the « Base de connaissances (BDC) » of HEADLAMP. Generated at start-up while nobody edited it (then left alone). The
title stays the same: it is how the page is found again.
"""
import json

from . import gtd
from .headlamp import _doc, _h, _link, _p, _panel, _t
from .local_api import LocalApi

TITLE = "Mettre à jour le site (Admin → Update) — pas à pas"
GENERATED = "Généré — guide Update"


def _ol(*items):
    return gtd._ol(*items)


def body():
    from core.update import MIN_CLAUDE, PROMPT, ROOT
    prompt = PROMPT.format(min_claude=MIN_CLAUDE, version="(version en ligne)", date="(date de l'export)",
                           who="(votre nom)", root=ROOT, last_log="(le journal de la dernière mise à jour, ajouté au zip)")
    return _doc(
        _panel("info", _p(_t("En une phrase :", "bold"), " on met le site dans une boîte (un fichier zip), on donne la boîte à "
                          "Claude avec une lettre qui dit quoi changer, Claude rend une boîte neuve, et on la remet dans le site. "
                          "Tout ce que les gens ont écrit dans le site reste à sa place : seule la « mécanique » change.")),
        _p("Admin → « Update et sauvegardes » a cinq volets : ", _t("↺ Restaurer", "bold"), " (les 2 × 3 chances : les 3 "
           "dernières versions du code et les 3 derniers points de restauration des données), ", _t("Framework", "bold"),
           " (le code : fonctions, menus, options — cette page, étapes 1 à 6), ", _t("Configuration", "bold"), " (tous les "
           "réglages dans un fichier .md), ", _t("Données", "bold"), " (comptes et Spaces, pour sauvegarder ou en ajouter à un "
           "autre site, et les sauvegardes .zip de chaque Space) et ", _t("Site complet", "bold"), " (le code et toutes les "
           "données, pour déménager le site). L'encadré « Que voulez-vous faire ? » en haut mène au bon volet. Pour un import, "
           "rien ne s'applique avant que chaque étape de la revue soit approuvée."),
        _h(2, "Ce qu'il faut avant de commencer"),
        gtd._ul("Être administrateur du site (onglet « ⚙ Admin », tout à droite en haut).",
                "Un accès à " + MIN_CLAUDE + " ou plus récent (les versions plus anciennes ne suffisent pas).",
                "Le fichier des instructions du projet (FONDATIONS) — il est dans le projet Claude, ou dans docs/FONDATIONS.md.",
                "Une heure calme : le site redémarre une dizaine de secondes à la fin."),
        _h(2, "Étape 1 — Mettre le site dans une boîte"),
        _ol("Cliquez sur « ⚙ Admin » (tout à droite en haut), puis sur « Update et sauvegardes » (groupe Plateforme), "
            "volet « Framework ».",
            "Cliquez sur le bouton bleu « Exporter le code (.zip) ».",
            "Un fichier arrive dans vos Téléchargements, par exemple « Dynamite_Agile_v0.41.0_code_pour_Claude.zip ». "
            "Il ne contient aucune donnée des employés : seulement le programme, la lettre de départ (UPDATE_PROMPT.md) et la "
            "description de la base."),
        _h(2, "Étape 2 — Donner la boîte à Claude"),
        _ol("Ouvrez une nouvelle conversation avec " + MIN_CLAUDE + " ou plus récent.",
            "Joignez trois choses : le zip de l'étape 1, le fichier des instructions (FONDATIONS) et, s'il existe, le dernier "
            "UPDATE_LOG.md.",
            "Copiez le texte du prompt de départ (plus bas sur cette page, ou dans UPDATE_PROMPT.md du zip) comme premier message.",
            "Sous « Demande de mise à jour », écrivez ce qu'il faut changer, avec des mots simples : « Ajouter un champ Date de "
            "livraison aux Test Plans », par exemple.",
            "Claude travaille en mode « verbose » : il explique chaque étape. Répondez à ses questions une à la fois."),
        _h(2, "Étape 3 — Récupérer la boîte neuve"),
        _ol("À la fin, Claude donne un zip du code (même forme que celui de l'étape 1), un UPDATE_LOG.md qui raconte ce qui a "
            "changé et un UPDATE_CHANGES.json : la liste des changements, chacun avec sa raison et ses fichiers.",
            "Enregistrez le zip sur votre ordinateur."),
        _h(2, "Étape 4 — Vérifier avant de remettre dans le site"),
        _ol("Admin → Update et sauvegardes → Framework → « Vérifier un zip de mise à jour… », choisissez le zip de Claude.",
            "Le site lit la boîte sans rien changer : il montre la nouvelle version, les fichiers ajoutés, modifiés ou retirés, et "
            "le journal de Claude.",
            "S'il y a un problème (version pas plus haute, erreur dans un fichier, tentative d'effacer des données, dossier data/ "
            "dans la boîte), il le dit en rouge avec la correction à demander à Claude. Rien n'est appliqué.",
            "Si la vérification est verte, la revue pas à pas commence : une étape par changement déclaré par Claude, plus une "
            "étape « Changement non déclaré » pour tout fichier qu'il n'a pas expliqué.",
            "Ouvrez chaque étape : elle montre la raison du changement et, pour chaque fichier, les lignes retirées (en rouge) et "
            "ajoutées (en vert). Cliquez « Approuver cette étape », ou « Refuser… » en écrivant ce qui ne va pas.",
            "Un seul refus arrête tout : rien n'est appliqué, et le site écrit un « Retour pour Claude » (bouton « Copier le "
            "retour pour Claude »). Collez-le dans la conversation : Claude corrige ce qui a été refusé et garde le reste ; "
            "vérifiez ensuite le nouveau zip."),
        _h(2, "Étape 5 — Appliquer"),
        _ol("Quand toutes les étapes sont approuvées, le bouton « Appliquer la mise à jour » apparaît : cliquez-le et confirmez.",
            "Le site fait d'abord deux copies de sécurité : l'ancien code (les 3 dernières versions sont gardées) et un point de "
            "restauration des données (les 3 derniers sont gardés).",
            "Il remplace le code, puis redémarre tout seul (environ 10 secondes). La page se recharge."),
        _h(2, "Étape 6 — Regarder ce qui est nouveau"),
        _ol("Les champs nouveaux portent l'étiquette jaune « [new] » tant qu'ils sont vides : remplissez-les.",
            "Les boutons ou onglets nouveaux portent « [new] » jusqu'à ce que vous les utilisiez une fois.",
            "Admin → Update et sauvegardes → Framework → « Historique des mises à jour » montre la mise à jour, qui l'a faite "
            "et son journal."),
        _h(2, "Si quelque chose ne va pas"),
        _panel("warning", _p("Volet « ↺ Restaurer », à gauche : « Revenir à la v… » remet l'une des 3 dernières versions du "
                             "code ; le site redémarre et les données restent telles qu'elles sont. À droite, le point « Avant la "
                             "mise à jour … » garde les données d'avant l'étape 5 (voir plus bas).")),
        _h(2, "Volet ↺ Restaurer — 2 × 3 chances"),
        _ol("Code (Framework) : chaque mise à jour garde une copie du code qu'elle remplace ; les 3 plus récentes restent. "
            "« Revenir à la v… » remet cette version du code sans toucher aux données (un point de données est pris d'abord).",
            "Données : un point de restauration est une copie exacte de la base. Il est pris tout seul avant chaque mise à jour, "
            "import de données, configuration appliquée ou retour à un point, et une fois par jour à la première activité "
            "(l'état de la veille au soir). « Créer un point maintenant » en prend un avant une manipulation risquée. Les 3 plus "
            "récents restent : un nouveau point efface le plus ancien.",
            "Une erreur dans un seul Space (page, tickets ou requirements effacés) : « Récupérer un Space… » sur le bon point. "
            "Le Space revient tel qu'il était, dans un NOUVEAU Space (ex. EQPR) : rien de ce qui est en service n'est écrasé. "
            "Recopiez ce qu'il faut, puis archivez la copie. Un numéro Generator encore en service n'est pas recopié (il reste "
            "unique).",
            "Une erreur partout (mauvaise configuration, import raté) : « Revenir à ce point… », cochez « J'ai compris », "
            "confirmez. Tout le site revient à ce moment ; un point « avant retour » est pris d'abord (on peut donc revenir à "
            "l'état d'avant), le journal d'audit écrit depuis est gardé, et tout le monde se reconnecte.",
            "Les fichiers joints (images, PDF) ne sont pas dans les points : ils restent sur le serveur. Ceux d'un Space supprimé "
            "sont dans sa sauvegarde « avant suppression » (volet Données → Sauvegardes des Spaces)."),
        _h(2, "Volet Données — sauvegarder ou ajouter des Spaces à un autre site"),
        _ol("Admin → Update et sauvegardes → « Données » → cochez les Spaces, tapez deux fois une phrase de passe (12 caractères au moins), "
            "« Exporter (.zip scellé) ». Le fichier se télécharge une seule fois puis est effacé du serveur.",
            "Il contient les comptes sans leurs mots de passe, chaque Space avec tout son contenu, et leurs pièces jointes. La "
            "phrase de passe le scelle : un fichier modifié, ou une mauvaise phrase, et l'import est refusé. Gardez le fichier sur "
            "un support chiffré approuvé par l'IT et donnez la phrase par un autre canal.",
            "Pour importer : « Importer un paquet scellé… », puis la phrase de passe. La revue montre le contenu, les comptes "
            "(les absents sont créés avec un mot de passe temporaire, jamais administrateurs ; les existants ne changent pas), "
            "puis un Space par étape.",
            "Un Space qui existe déjà ici n'est jamais écrasé : sautez-le, ou importez-le comme nouveau Space sous une autre clé "
            "(ex. EQP2), avec les types cochés. Les heures Timesheet ne voyagent qu'avec « Site complet ».",
            "Après « Importer les données approuvées », notez les mots de passe temporaires affichés une seule fois.",
            "Plus bas dans ce volet, « Sauvegardes des Spaces (.zip) » : les sauvegardes faites avant chaque suppression de Space, "
            "à télécharger ou à restaurer (toujours dans un nouveau Space)."),
        _h(2, "Volet Site complet — déménager le site"),
        _ol("Sur l'ancien serveur : « Site complet » → phrase de passe → « Exporter (.zip scellé) ». Le paquet contient le code, "
            "une copie exacte de la base (comptes et mots de passe compris) et les fichiers. La configuration du serveur et ses "
            "certificats ne voyagent pas : l'IT les prépare sur le nouveau serveur.",
            "Sur le nouveau serveur : installez la plateforme, connectez-vous avec l'admin initial, puis « Site complet » → "
            "« Importer un paquet scellé… ». Ce volet refuse tout site qui a déjà d'autres comptes : il ne remplace jamais un site "
            "en service.",
            "Revue : sceau, Framework (différences de code, ou « code identique »), chaque Space, comptes et administrateurs. "
            "Approuvez chaque étape, puis « Appliquer le déménagement ».",
            "Le site garde une copie de l'état d'avant, remplace la base et les fichiers, puis redémarre. Reconnectez-vous avec "
            "un compte du site déménagé (même identifiant, même mot de passe)."),
        _h(2, "Ce qui ne change jamais"),
        gtd._ul("Les données saisies (tickets, requirements, pages, heures, tests, plans…) : l'import ne touche pas au dossier data/.",
                "Un champ retiré de l'écran reste dans la base : rien n'est effacé.",
                "Les comptes, mots de passe et droits."),
        _h(2, "Questions fréquentes"),
        gtd._ul("« Puis-je utiliser une version plus ancienne de Claude ? » Non : " + MIN_CLAUDE + " ou plus récent.",
                "« Le zip contient-il des données personnelles ? » Non : seulement le code et la structure de la base (noms des "
                "tables et des colonnes, nombre de lignes), jamais leur contenu.",
                "« Combien de temps le site est-il arrêté ? » Une dizaine de secondes, au moment d'appliquer.",
                "« Puis-je n'appliquer qu'une partie des changements ? » Non : le code a été testé comme un tout. Refusez, et "
                "demandez à Claude de retirer ce que vous ne voulez pas.",
                "« Les paquets Données et Site complet sont-ils chiffrés ? » Non, scellés : toute modification est détectée. La "
                "confidentialité vient du support chiffré de l'IT.",
                "« Où est le guide détaillé ? » Ici, et le prompt complet est dans le zip exporté."),
        _h(2, "Le prompt de départ (à copier)"),
        {"type": "code", "text": prompt},
        _p("Écran : ", _link("Admin → Update et sauvegardes", "#/admin/update"), "."))


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
    doc = body()
    if page is None:
        api.post(base, {"title": TITLE, "parent_id": hub["id"] if hub else None, "body": doc})
        return True
    versions = ctx.conn.execute("SELECT author_id, note FROM dynamite_versions WHERE page_id = ?", (page["id"],)).fetchall()
    if not all(v["author_id"] == ctx.user["id"] and ((v["note"] or "").startswith(GENERATED) or (v["note"] or "") in ("", "Création"))
               for v in versions):
        return False  # edited by hand: left alone
    full = api.get(base + "/{}".format(page["id"]))["page"]
    if full.get("body") != json.loads(content.validate(doc)):
        api.put(base + "/{}".format(page["id"]), {"title": TITLE, "body": doc, "base_version": full["version"], "note": GENERATED})
    return True
