"""Timesheet catalogs (D-B-023; product development process since 0.60.01): time codes and week statuses.

One default set of time codes, « pdp »: the steps of the product development process (PDP) taught in the design
course, grouped by phase -- since 0.60.09 (D-O-021) A. Discovery, B. Concept, C. Design, D. Validation et lancement, each a
Build-Measure-Learn loop with its MVP. The code gives the phase and the number of the step (A-01 … D-21; the course figure numbers 1 to 15 and
19 to 21), plus « D-FAB » for the drawings and the making of the prototype, which the figure shows without a number.
A second set, « interne », serves the INT Space (created at first launch, open to everyone): time that serves the
team or the start-up rather than one funded project, and the leave -- INT-VAC vacation (deducted from the person's
bank) and INT-SAN health leave (subject to approval, not deducted), both not claimable from a funding organism.
For a funded project, an administrator adds a Funding Space with its Budget Lines (Timesheet → « Spaces et
organismes ») and attaches the project to it; the Excel export and the Word report then justify every hour
claimed, range by range (D-B-036, D-A-042).
Keys are stable (they go into the Excel exports); labels may be reworded.
"""
DEFAULT_SET = "pdp"
TASK_SETS = {
    "pdp": ("Processus de développement de produit (PDP)", [
        ("A-01", "A. Discovery · 1. Étude de marché et entrevues clients"),
        ("A-02", "A. Discovery · 2. Spécifications préliminaires du produit avec le client"),
        ("A-03", "A. Discovery · 3. Définition du projet et Lean Canvas"),
        ("A-04", "A. Discovery · 4. Échéancier, budget et sources de financement"),
        ("A-05", "A. Discovery · 5. Pré-faisabilité et MVP 0"),
        ("A-06", "A. Discovery · 6. Analyse des risques et hypothèses à tester"),
        ("B-07", "B. Concept · 7. Bilan du MVP 0 : persévérer ou pivoter"),
        ("B-08", "B. Concept · 8. Recherche des besoins du client"),
        ("B-09", "B. Concept · 9. Recherche des fonctions"),
        ("B-10", "B. Concept · 10. Définition de la structure fonctionnelle"),
        ("B-11", "B. Concept · 11. Définition des spécifications d'ingénierie (CdCF)"),
        ("B-12", "B. Concept · 12. Recherche et sélection des concepts, MVP 1"),
        ("C-13", "C. Design · 13. Bilan du MVP 1 : persévérer ou pivoter"),
        ("C-14", "C. Design · 14. Identification des sous-systèmes (PDR)"),
        ("C-15", "C. Design · 15. Conception des sous-systèmes, MVP 2 (CDR)"),
        ("D-FAB", "D. Validation et lancement · Mise en plan et fabrication du prototype"),
        ("D-19", "D. Validation et lancement · 19. Bilan du MVP 2 : persévérer ou pivoter"),
        ("D-20", "D. Validation et lancement · 20. Validation de certains aspects qualitatifs de la conception"),
        ("D-21", "D. Validation et lancement · 21. Tests de validation des spécifications par sous-système, MVP 3"),
    ]),
    "interne": ("Temps interne et congés", [
        ("INT-01", "Réunions et gestion de l'équipe"),
        ("INT-02", "Formation et veille"),
        ("INT-03", "Administration, contrats et demandes de financement"),
        ("INT-04", "Équipement, outils et installations"),
        ("INT-05", "Représentation, recrutement et événements"),
        ("INT-VAC", "Vacation (deducted from my bank)"),
        ("INT-SAN", "Health Leave (subject to approval, not deducted)"),
    ]),
}
PHASES = {"A": "Discovery", "B": "Concept", "C": "Design", "D": "Validation et lancement"}  # 0.60.09 (D-O-021)
TASKS = {key: label for _, (_, items) in TASK_SETS.items() for key, label in items}

STATUSES = {"draft": "Draft", "submitted": "Submitted", "approved": "Approved", "returned": "Returned"}
EDITABLE = ("draft", "returned")

# The time codes (timesheet_budget_sets / _lines) belong to the Space TOOLS, the wiki of the design methods (D-A-010:
# every table is tied to a project), created at start-up by the Tools module.
CODES_KEY = "TOOLS"
INTERNAL_ORGANISM = "Interne"

# The INT Space: internal time and leave (0.60.01)
INTERNAL_KEY = "INT"
INTERNAL_SET = "interne"
INTERNAL_NAME = "Interne — temps hors projet et congés"
INTERNAL_DESCRIPTION = ("Heures au bénéfice de l'équipe ou de l'entreprise, hors projet financé (réunions, formation, "
                        "administration, demandes de financement, équipement), vacances et congés santé. Ouvert à tous.")

MAX_DESCRIPTION = 300
MAX_DAY_HOURS = 24


def task_list(task_set):
    return [{"key": k, "label": v} for k, v in TASK_SETS.get(task_set, TASK_SETS[DEFAULT_SET])[1]]


def meta():
    return {"task_sets": {k: {"label": label, "tasks": task_list(k)} for k, (label, _) in TASK_SETS.items()},
            "statuses": STATUSES}

# 0.60.09 (D-O-021): the labels of the « pdp » codes before the Lean renaming, replaced at start-up when unchanged.
OLD_PDP_LABELS = {
    "A-01": "A. Pré-étude · 1. Étude de marché",
    "A-02": "A. Pré-étude · 2. Spécifications préliminaires du produit avec le client",
    "A-03": "A. Pré-étude · 3. Définition du projet",
    "A-04": "A. Pré-étude · 4. Échéancier, budget et sources de financement",
    "A-05": "A. Pré-étude · 5. Pré-faisabilité",
    "A-06": "A. Pré-étude · 6. Analyse des risques et solutions potentielles",
    "B-07": "B. Étude conceptuelle · 7. Rappel et mise à jour de la pré-étude",
    "B-08": "B. Étude conceptuelle · 8. Recherche des besoins du client",
    "B-09": "B. Étude conceptuelle · 9. Recherche des fonctions",
    "B-10": "B. Étude conceptuelle · 10. Définition de la structure fonctionnelle",
    "B-11": "B. Étude conceptuelle · 11. Définition des spécifications d'ingénierie (CdCF)",
    "B-12": "B. Étude conceptuelle · 12. Recherche et sélection des concepts",
    "C-13": "C. Conception · 13. Rappel et mise à jour de l'étude conceptuelle",
    "C-14": "C. Conception · 14. Identification des sous-systèmes",
    "C-15": "C. Conception · 15. Conception des sous-systèmes",
    "D-FAB": "D. Fabrication et validation · Mise en plan et fabrication du prototype",
    "D-19": "D. Fabrication et validation · 19. Rappel et mise à jour de la phase de conception",
    "D-20": "D. Fabrication et validation · 20. Validation de certains aspects qualitatifs de la conception",
    "D-21": "D. Fabrication et validation · 21. Tests de validation des spécifications par sous-système",
}
