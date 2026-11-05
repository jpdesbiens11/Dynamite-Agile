"""Training catalogue (D-A-045): the TRAINING Space that holds the topics (D-A-010), the default topics -- the
DEMO sections (linked to their Help chapter), the knowledge-base pages, the Tools methods of the Dynamite
wiki and the personal follow-up (RH, 0.50.10) -- one example test for the administrators, and the default workflow
(editable by the administrators, stored in app_settings).

0.50.10 (D-B-128): every topic but the group headings has a default test (modules/training/quizzes/); ensure() puts
it in an existing topic whose test is empty or still a previous default, never over a test edited by an administrator.
"""
import json

from core import admin, db

from . import quizzes

KEY = "TRAINING"
NAME = "Training — Topics et plans de formation"
DESCRIPTION = "Topics de formation (contenu, référence, test), plans individuels et évaluation par le gestionnaire."

STATUSES = {"todo": "To Do", "in_progress": "In Progress", "completed": "Completed", "achieved": "Achieved"}
ROLES = {"employee": "Employé", "manager": "Gestionnaire"}
# (from, to, label, roles allowed by default). Guards stay in plan.py: « Achieved » needs the test passed (when the
# topic has one) and the manager's evaluation.
DEFAULT_WORKFLOW = [
    ["todo", "in_progress", "Commencer", ["employee", "manager"]],
    ["in_progress", "completed", "Marquer complété", ["employee"]],
    ["completed", "in_progress", "Reprendre", ["employee", "manager"]],
    ["completed", "achieved", "Atteint", ["manager"]],
    ["achieved", "completed", "Rouvrir", ["manager"]],
    ["in_progress", "todo", "Remettre à faire", ["employee", "manager"]],
]
SETTING = "training_workflow"

EXAMPLE_QUIZ = """# Quiz : Timesheet — déclarer ses heures (exemple)
pass: 80
## Quel code de temps choisit-on pour une séance sur l'arbre des fonctions ?
- [ ] A-03 · Définition du projet
- [x] B-09 · Recherche des fonctions
- [ ] D-21 · Tests de validation
> Les codes de temps sont les étapes du PDP : la phase (A à D) et le numéro de l'étape.
## Que faut-il pour pouvoir soumettre la semaine ?
- [ ] Au moins 40 h
- [x] Une courte description sur chaque plage
- [ ] L'accord préalable de l'administrateur
> Une plage sans description bloque la soumission (ligne en rouge).
## Qui approuve votre semaine ?
- [x] Votre approbateur, choisi dans le menu à votre nom → Paramètres
- [x] Un administrateur
- [ ] N'importe quel collègue
> L'approbateur choisi dans vos Paramètres (l'enseignant, un chef d'équipe), ou un administrateur.
## Les heures se saisissent par…
- [ ] Minute
- [x] Quart d'heure (0,25 h)
- [ ] Heure entière
## Une semaine « Returned » signifie…
- [ ] Elle est approuvée
- [x] Elle doit être corrigée puis soumise de nouveau
- [ ] Elle est supprimée
> La note de l'approbateur explique quoi corriger.
"""

def project_id(conn):
    """The Space of the training topics: TRAINING on an installation made before 0.60.41, else DEMO (D-O-050)."""
    from modules.help import reference
    return reference.space(conn, KEY)


def workflow(conn):
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (SETTING,)).fetchone()
    if row:
        try:
            return json.loads(row["value"])
        except ValueError:
            pass
    return [list(t) for t in DEFAULT_WORKFLOW]


def save_workflow(conn, rules):
    conn.execute("INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET "
                 "value = excluded.value, updated_at = excluded.updated_at", (SETTING, json.dumps(rules), db.utc_now()))


def _topics():
    from modules.help.headlamp import STEPS, TOPIC_CODES  # 0.47.0: stable code per chapter, whatever its position
    out = [("HL", None, "DEMO — prise en main de la plateforme",
            "Le parcours d'accueil : une section par outil, chacune avec son exercice dans le Space DEMO.",
            "#/dynamite/DEMO", "Space DEMO")]
    for n, (chapter, title, exercise) in enumerate(STEPS, start=1):
        out.append((TOPIC_CODES[chapter], "HL", title, "Exercice : " + exercise, "#/help/" + chapter,
                    "Help — chapitre {}".format(n)))
    out += [("KB", None, "Base de connaissances (BDC)", "Les pages de référence du wiki Dynamite.", "#/dynamite/DEMO",
             "Base de connaissances"),
            ("KB-01", "KB", "Definitions et Acronyms de l'outil",
             "Les termes techniques (en anglais) et leur équivalent français ; le vocabulaire de l'analyse fonctionnelle.",
             "#/testing/lists", "Testing → Listes centrales"),
            ("KB-02", "KB", "Getting Things Done — les principes", "Organiser ses tâches : Inbox, Next Actions, Weekly Review.",
             "#/dynamite/DEMO", "Page « Getting Things Done »"),
            ("KB-03", "KB", "Structure des fonctions du produit (F-XX)", "Les fonctions de l'analyse fonctionnelle "
             "et leurs composants.", "#/testing/lists", "Page BDC des fonctions"),
            ("TL", None, "Méthodes de conception (Tools)", "Les méthodes de l'onglet Tools et leurs pages dans le Space TOOLS.",
             "#/tools", "Tools"),
            ("TL-01", "TL", "Idéation et brainwriting", "Générer des idées en équipe, les regrouper, voter.", "#/tools/design",
             "Tools → Design"),
            ("TL-02", "TL", "Matrice de Pugh", "Comparer des concepts à un Datum sur des Criteria pondérés.", "#/tools/design",
             "Tools → Design"),
            ("TL-03", "TL", "Kepner-Tregoe", "Décider entre alternatives : MUST, WANT, risques.", "#/tools/design", "Tools → Design")]
    # 0.50.10 (D-B-128): platform coverage -- what the topics above did not cover yet.
    out += [("TL-06", "TL", "Generator — références documentaires du PDP",
             "Numéro série UTC, nom de fichier, dossier, livrables par phase du PDP (LCV, CRV, CdCF, PDR, CDR, VVR), registre.",
             "#/help/generator", "Help — Tools, Generator pas à pas"),
            ("RH", None, "Suivi personnel — objectifs, évaluation, profil",
             "Les pages du menu à votre nom : Mes objectifs, l'évaluation de l'année ou du stage, le profil, Mon équipe.",
             "#/objectives", "Mes objectifs"),
            ("RH-01", "RH", "Mes objectifs et évaluation annuelle",
             "Objectifs annuels et de développement, les 3 étapes signées (Début d'année, Mi-année, Fin d'année), fermer l'année.",
             "#/objectives", "Menu à votre nom → Mes objectifs"),
            ("RH-02", "RH", "Évaluation de stage, profil professionnel et Mon équipe",
             "Accueil, Mi-stage, Évaluation finale ; ce que le gestionnaire et l'employé écrivent au profil ; « Mon équipe ».",
             "#/team", "Menu à votre nom → Mon équipe")]
    out += [("DM", None, "Diamond — analyse fonctionnelle", "L'onglet Diamond : arbre fonctionnel, puis structure fonctionnelle, "
             "risques et DFMEA (0.60.11, D-O-023).", "#/diamond", "Diamond"),
            ("DM-01", "DM", "Arbre fonctionnel", "Fonction primaire, secondaires, tertiaires ; comment, pourquoi, quand ; chemin "
             "critique, rétroaction, fonctions hors arbre.", "#/diamond", "Diamond → Arbre fonctionnel"),
            ("DM-02", "DM", "Structure fonctionnelle", "Boundary diagram : entrées et sorties du système, vue générale par "
             "sous-systèmes, vue détaillée, flux d'énergie, de matière et d'information.", "#/diamond", "Diamond → Structure fonctionnelle"),
            ("DM-03", "DM", "Analyse de risque projet", "Registre des risques : si / alors / ce qui, probabilité × impact, "
             "stratégie, action, responsable, risque résiduel, lien vers le DFMEA.", "#/diamond", "Diamond → Risques projet"),
            ("DM-04", "DM", "DFMEA (AIAG-VDA)", "Les trois niveaux de la structure, la chaîne de défaillance (effet, mode, cause), "
             "S / O / D, RPN et Action Priority.", "#/diamond", "Diamond → DFMEA et sa légende AP"),
            ("DM-05", "DM", "Golden Nuggets", "Penser à partir des premiers principes : vingt principes dans l'esprit de TRIZ, "
             "l'algorithme en cinq étapes et les règles de conception de SpaceX et Tesla.", "#/diamond", "Diamond → Golden Nuggets")]
    return out


def ensure(ctx):
    """Create the TRAINING Space and the default topics once (a topic edited by an administrator is left alone)."""
    conn = ctx.conn
    from modules.help import reference
    pid = reference.ensure(ctx, KEY)  # 0.60.41 (D-O-050): DEMO, or TRAINING on an older installation
    have = {r["code"]: r["id"] for r in conn.execute("SELECT id, code FROM training_topics WHERE project_id = ?", (pid,))}
    now = db.utc_now()
    for pos, (code, parent, title, content, ref, ref_label) in enumerate(_topics()):
        if code in have:
            continue
        have[code] = conn.execute(
            "INSERT INTO training_topics (project_id, parent_id, code, title, content, reference, ref_label, quiz_md, "
            "position, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, have.get(parent), code, title, content, ref, ref_label, quizzes.default(code), pos, now, now)).lastrowid
    _fill_quizzes(conn, pid, now)
    # Retired topics stay inactive (out of the catalogue, plans keep their history); never deleted.
    conn.execute("UPDATE training_topics SET active = 0, updated_at = ? WHERE project_id = ? AND code IN ({}) AND active = 1"
                 .format(",".join("?" * len(RETIRED_TOPICS))), (now, pid) + RETIRED_TOPICS)
    conn.execute("INSERT OR IGNORE INTO memberships (user_id, project_id, role) SELECT id, ?, 'reader' FROM users "
                 "WHERE is_active = 1 AND is_admin = 0", (pid,))
    return pid


RETIRED_TOPICS = ("TL-04", "TL-05", "KB-04")  # retired topics stay inactive
UPGRADES = {"HL-09": (EXAMPLE_QUIZ,)}  # topic code -> previous default tests a new default may replace (0.37.0 example)


QUIZ_SETTING = "training_default_quizzes"  # version of the default tests already handed out
QUIZ_VERSION = "0.60.01"  # 0.50.10: first tests; 0.60.01: generic tests


def _fill_quizzes(conn, pid, now):
    """0.50.10, once: give its default test to a topic whose test is empty or still a previous default (never one
    edited by an administrator; a test emptied later on purpose stays empty)."""
    done = conn.execute("SELECT value FROM app_settings WHERE key = ?", (QUIZ_SETTING,)).fetchone()
    if done and done["value"] == QUIZ_VERSION:
        return
    conn.execute("INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET "
                 "value = excluded.value, updated_at = excluded.updated_at", (QUIZ_SETTING, QUIZ_VERSION, now))
    for row in conn.execute("SELECT id, code, quiz_md FROM training_topics WHERE project_id = ?", (pid,)).fetchall():
        text = quizzes.default(row["code"])
        current = (row["quiz_md"] or "").strip()
        if not text or current == text.strip():
            continue
        if current and current not in (q.strip() for q in UPGRADES.get(row["code"], ())):
            continue
        conn.execute("UPDATE training_topics SET quiz_md = ?, updated_at = ? WHERE id = ?", (text, now, row["id"]))
