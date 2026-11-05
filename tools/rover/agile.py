"""Rover example: the Agile backlog by MVP (one Version per MVP, epics then stories, tasks and a few bugs found in test) and
the Generator deliverables of the PDP. Each MVP answers one question of the course (Lean Startup):
MVP 0 does the problem exist? MVP 1 does the concept appeal? MVP 2 does it work? MVP 3 is it ready for the market?"""


def _e(ref, mvp, title, description):
    return {"ref": ref, "type": "epic", "mvp": mvp, "title": title, "description": description, "priority": "high"}


def _s(ref, epic, mvp, title, who, points, kind="story", priority="medium", description=""):
    item = {"ref": ref, "type": kind, "parent": epic, "mvp": mvp, "title": title, "assignee": who, "points": points,
            "priority": priority}
    if description:
        item["description"] = description
    return item


BACKLOG = [
    _e("E0", "MVP0", "MVP 0 — Le problème existe-t-il ?",
       "Hypothèse : des étudiants veulent apprendre la robotique sur un vrai véhicule autonome, à moins de 250 $. "
       "MVP 0 : entrevues, maquette papier de l'application et une auto téléguidée du commerce poussée à la main devant des obstacles."),
    _s("S1", "E0", "MVP0", "Entrevues de 12 étudiants et 3 enseignants", "hugo", 3, description="Guide d'entrevue dans le wiki (A. Discovery)."),
    _s("S2", "E0", "MVP0", "Lean Canvas et liste des hypothèses risquées", "nina", 2),
    _s("S3", "E0", "MVP0", "Étude des kits de référence (prix, capteurs, ce qui manque)", "lea", 3),
    _s("S4", "E0", "MVP0", "Maquette papier de l'application, testée avec 5 étudiants", "hugo", 2),
    _s("S5", "E0", "MVP0", "Essai « magicien d'Oz » : un étudiant pilote l'auto, les autres disent si elle « évite bien »", "alexis", 2,
       description="On mesure ce que les gens appellent « lent » et « trop près » avant d'écrire une ligne de code."),
    _s("T1", "E0", "MVP0", "Bilan du MVP 0 : persévérer ou pivoter", "nina", 1, kind="task", priority="high"),
    _e("E1", "MVP1", "MVP 1 — Le concept plaît-il ?",
       "Concept retenu par Pugh et Kepner-Tregoe ; MVP 1 : le châssis télécommandé par le téléphone, avec un seul ultrason qui l'arrête."),
    _s("S6", "E1", "MVP1", "Arbre fonctionnel et structure fonctionnelle (Diamond)", "nina", 5),
    _s("S7", "E1", "MVP1", "CdCF : requirements, critères et niveaux (Goldmine)", "lea", 5),
    _s("S8", "E1", "MVP1", "Idéation et matrice morphologique des capteurs et de la commande", "hugo", 3),
    _s("S9", "E1", "MVP1", "Matrice de Pugh des 4 concepts, puis Kepner-Tregoe des 2 meilleurs", "nina", 3),
    _s("S10", "E1", "MVP1", "Pi en point d'accès Wi-Fi et page web « Avancer / Arrêter »", "alexis", 5),
    _s("S11", "E1", "MVP1", "Un ultrason devant : arrêt sous 30 cm", "lea", 3),
    _s("S12", "E1", "MVP1", "Démonstration à 10 étudiants et Concept Review", "hugo", 2),
    _s("T2", "E1", "MVP1", "Bilan du MVP 1 : persévérer ou pivoter", "nina", 1, kind="task", priority="high"),
    _e("E2", "MVP2", "MVP 2 — Ça fonctionne ?",
       "Tous les sous-systèmes : trois ultrasons, temps de vol, centrale inertielle, encodeur, pare-chocs, arrêts d'urgence, "
       "loi d'approche lente et contournement. Revues PDR puis CDR."),
    _s("S13", "E2", "MVP2", "Plaque porte-modules et support des capteurs", "nina", 5),
    _s("S14", "E2", "MVP2", "Alimentation : batterie, 5 V, INA219, coupure de traction", "lea", 5, priority="high"),
    _s("S15", "E2", "MVP2", "Pilotes des capteurs et séquenceur des ultrasons", "alexis", 5),
    _s("S16", "E2", "MVP2", "Carte locale et loi d'approche lente", "alexis", 8, priority="high"),
    _s("S17", "E2", "MVP2", "Choix du côté et reprise du cap", "alexis", 5),
    _s("S18", "E2", "MVP2", "Chien de garde et arrêt d'urgence dans l'application", "lea", 3, priority="high"),
    _s("S19", "E2", "MVP2", "Télémétrie et vue radar dans l'application", "hugo", 5),
    _s("S20", "E2", "MVP2", "Boîtier électronique et pare-chocs imprimés", "hugo", 5),
    _s("S21", "E2", "MVP2", "DFMEA et actions suivies (Diamond)", "nina", 3),
    _s("T3", "E2", "MVP2", "PDR : architecture, calculs, risques", "nina", 2, kind="task", priority="high"),
    _s("T4", "E2", "MVP2", "CDR : design figé, nomenclature, plan d'essais", "nina", 2, kind="task", priority="high"),
    _s("B1", "E2", "MVP2", "Le Pi redémarre quand le moteur démarre", "lea", 2, kind="bug", priority="high",
       description="Chute du 5 V au démarrage du moteur (DFMEA). Correctif : rampe de 0,5 s et condensateur de 1 000 µF."),
    _s("B2", "E2", "MVP2", "Le robot oscille gauche-droite devant un mur", "alexis", 2, kind="bug",
       description="Distances gauche et droite presque égales. Correctif : hystérésis de 10 cm, côté gardé 2 s."),
    _e("E3", "MVP3", "MVP 3 — Prêt pour le marché ?",
       "Validation sur les parcours A, B et C, essais de sécurité et de pré-conformité, notice et kit pour une autre équipe."),
    _s("S22", "E3", "MVP3", "Essais de validation du Test Plan (ESSAI-1 à ESSAI-20)", "lea", 8, priority="high"),
    _s("S23", "E3", "MVP3", "Pré-balayage CEM et dossier radio, batterie et RoHS", "lea", 3),
    _s("S24", "E3", "MVP3", "Notice de montage et consignes de sécurité de la batterie", "hugo", 3),
    _s("S25", "E3", "MVP3", "Reprise du MVP 2 par une autre équipe à partir du wiki", "alexis", 3),
    _s("S26", "E3", "MVP3", "Nomenclature finale et coût par robot", "nina", 2),
    _s("B3", "E3", "MVP3", "Le temps de vol sature au soleil", "lea", 2, kind="bug",
       description="Trouvé sur le parcours C. Correctif : mode courte portée et filtre de plausibilité avec les ultrasons."),
    _s("T5", "E3", "MVP3", "Validation Report et décision de lancement du kit", "nina", 2, kind="task", priority="high"),
]

DELIVERABLES = [
    {"doc_type": "LCV", "title": "Lean Canvas du Rover"},
    {"doc_type": "ETM", "title": "Étude des kits de référence et entrevues"},
    {"doc_type": "RSK", "title": "Registre des risques du projet"},
    {"doc_type": "MVP", "title": "MVP 0 — essai « magicien d'Oz »", "step": "05"},
    {"doc_type": "BES", "title": "Besoins des étudiants et des enseignants"},
    {"doc_type": "AF", "title": "Analyse fonctionnelle du Rover"},
    {"doc_type": "CDCF", "title": "Cahier des charges fonctionnel du Rover"},
    {"doc_type": "MMO", "title": "Matrice morphologique des capteurs et de la commande"},
    {"doc_type": "PUGH", "title": "Matrice de Pugh des quatre concepts"},
    {"doc_type": "CRV", "title": "Concept Review du Rover"},
    {"doc_type": "MVP", "title": "MVP 1 — châssis piloté par le téléphone", "step": "12"},
    {"doc_type": "PDR", "title": "Preliminary Design Review du Rover"},
    {"doc_type": "CALC", "title": "Bilan de puissance et distance d'arrêt"},
    {"doc_type": "AMDEC", "title": "DFMEA du Rover"},
    {"doc_type": "CDR", "title": "Critical Design Review du Rover"},
    {"doc_type": "BOM", "title": "Nomenclature du Rover"},
    {"doc_type": "MVP", "title": "MVP 2 — évitement lent complet", "step": "15"},
    {"doc_type": "PRO", "title": "Test Plan de validation du Rover"},
    {"doc_type": "VVR", "title": "Validation Report du Rover"},
    {"doc_type": "MAN", "title": "Notice de montage du kit Rover"},
    {"doc_type": "REX", "title": "Leçons apprises du projet Rover"},
]
