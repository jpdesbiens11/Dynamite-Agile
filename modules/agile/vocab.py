"""Technical vocabulary in English (D-B-085, docs/GLOSSARY_EN.md).

Workflow, status, transition and issue-type names are stored in the database (they can be renamed by an admin);
agile migration 14 renames the platform's former French defaults to English, and the CSV imports still accept
the French names (STATUS_ALIASES).
"""

STATUS_EN = {
    # Requirement Workflow (Goldmine)
    "Reçue": "Received", "En analyse": "In Analysis", "Clarification client": "Customer Clarification",
    "Acceptée": "Accepted", "Allouée": "Allocated", "Implémentée": "Implemented", "En vérification": "In Verification",
    "Vérifiée": "Verified", "Rejetée": "Rejected", "Obsolète": "Obsolete",
    # Standard Workflow (Agile)
    "À faire": "To Do", "En cours": "In Progress", "En revue": "In Review", "Terminé": "Done",
    # PR / Bug and ECN workflows (Change Management)
    "Ouvert": "Open", "Dérivé en ECN": "Derived to ECN", "Fermé": "Closed", "Rejeté": "Rejected",
    "Brouillon": "Draft", "Soumis": "Submitted", "En revue CCB": "CCB Review", "Approuvé": "Approved",
    "En implantation": "In Implementation", "Annulé": "Cancelled",
}
TRANSITION_EN = {
    "Analyser": "Analyze", "Demander une clarification": "Request Clarification",
    "Réponse du client reçue": "Customer Answer Received", "Accepter (validée avec le client)": "Accept (validated with customer)",
    "Rejeter": "Reject", "Allouer à un sous-système": "Allocate to Subsystem", "Déclarer implémentée": "Declare Implemented",
    "Lancer la vérification": "Start Verification", "Vérification réussie": "Verification Passed",
    "Échec de vérification": "Verification Failed", "Rendre obsolète (nouvelle révision)": "Make Obsolete (new revision)",
    "Démarrer": "Start", "Envoyer en revue": "Send to Review", "Renvoyer en cours": "Back to In Progress",
    "Terminer": "Done", "Remettre à faire": "Back to To Do",
    "Dériver en ECN": "Derive to ECN", "Fermer sans ECN (cause traitée)": "Close without ECN (cause addressed)",
    "Fermer (ECN fermé)": "Close (ECN closed)", "Rouvrir": "Reopen", "Soumettre au CCB": "Submit to CCB",
    "Mettre en revue": "Start CCB Review", "Approuver (CCB)": "Approve (CCB)", "Rejeter (CCB)": "Reject (CCB)",
    "Retourner pour correction": "Return for Correction", "Démarrer l'implantation": "Start Implementation",
    "Implantation terminée": "Implementation Done", "Fermer l'ECN": "Close ECN",
    "Reprendre l'implantation": "Resume Implementation", "Annuler": "Cancel",
}
TYPE_EN = {"Tâche": "Task", "Bogue": "Bug", "Sous-tâche": "Sub-task", "Exigence": "Requirement", "Tâche ECN": "ECN Task"}
WORKFLOW_EN = {"Workflow standard": "Standard Workflow", "Workflow Exigence": "Requirement Workflow",
               "Workflow Problème (PR / bogue)": "PR / Bug Workflow",
               "Workflow ECN (gestion du changement)": "ECN Workflow (Change Management)"}

STATUS_ALIASES = {fr.casefold(): en for fr, en in STATUS_EN.items()}


def _q(text):
    return "'" + text.replace("'", "''") + "'"


def migration_sql():
    """Agile migration 14: the former French defaults renamed in English (customised names are left alone)."""
    out = []
    for fr, en in STATUS_EN.items():
        out.append("UPDATE OR IGNORE agile_statuses SET name = {} WHERE name = {};".format(_q(en), _q(fr)))
    for fr, en in TRANSITION_EN.items():
        out.append("UPDATE OR IGNORE agile_transitions SET name = {} WHERE name = {};".format(_q(en), _q(fr)))
    for fr, en in TYPE_EN.items():
        out.append("UPDATE OR IGNORE agile_issue_types SET name = {} WHERE name = {};".format(_q(en), _q(fr)))
    for fr, en in WORKFLOW_EN.items():
        out.append("UPDATE OR IGNORE agile_workflows SET name = {} WHERE name = {};".format(_q(en), _q(fr)))
    return "\n".join(out)


# Former French labels of Goldmine, still accepted by the CSV import (D-B-085)
LEGACY_LABELS = {
    "source": {"Client": "client", "Norme / Standard": "standard", "Norme": "standard", "Interne": "internal",
               "Dérivée": "derived"},
    "category": {"Fonctionnelle": "functional", "Environnementale": "environmental", "Sécurité": "safety",
                 "Sécurité des personnes": "personnel_safety", "Norme / Standard": "regulatory", "Réglementaire": "regulatory"},
    "lifecycle": {"Conception": "design", "Coût (DTC)": "cost", "Fabrication des pièces (DFM)": "manufacturing",
                  "Assemblage (DFA)": "assembly", "Test et vérification (DFT)": "test", "Transport et stockage": "transport",
                  "Installation et intégration": "installation", "Utilisation": "operation", "Exploitation": "operation",
                  "Maintenance et réparation": "maintenance", "Apparence et attrait": "appearance", "Seconde vie": "second_life",
                  "Fin de vie (désassemblage, recyclage)": "end_of_life"},
    "kind": {"Exigence": "requirement", "Besoin": "need"},
    "stakeholder": {"Client / acheteur": "client", "Client": "client", "Utilisateur": "user", "Utilisateur final": "user",
                    "Organisme de normalisation": "authority", "Intégrateur / distributeur": "integrator",
                    "Production / assembleurs": "production", "Logistique": "logistics", "Recyclage / fin de vie": "recycling",
                    "Marketing / ventes": "marketing", "Direction du projet": "management",
                    "Santé et sécurité des personnes": "safety"},
}
