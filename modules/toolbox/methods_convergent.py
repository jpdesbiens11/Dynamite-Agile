"""Explanation pages and FAQ of the convergent methods and of Generator (D-B-065)."""
CONVERGENT = [
    {"key": "pugh", "name": "Pugh Matrix", "family": "convergent", "tool": "pugh",
     "tagline": "Comparer des concepts à un Datum, Criterion par Criterion : +, S ou −.",
     "goal": "Choisir et améliorer des concepts de façon structurée (Stuart Pugh). Chaque concept est comparé à une "
             "Datum sur chaque Criterion : meilleur (+), pareil (S), moins bon (−). Les totaux révèlent "
             "forces et faiblesses ; on combine les meilleures idées et on itère.",
     "when": "Après l'idéation, avec 3 à 8 concepts, et des Criteria issus des Needs et Requirements Goldmine.",
     "steps": ["Choisir les Criteria dans Goldmine : Needs, Requirements, toute une Life-Cycle Phase (DFX) ou "
               "une category.", "Choisir la référence : la solution actuelle ou le concept le plus connu.",
               "Noter chaque case +, S ou − en équipe, avec une note quand ce n'est pas évident (double-clic).",
               "Lire les totaux (Σ+, ΣS, Σ−, net) : ne pas choisir au net seulement, regarder les − forts.",
               "Améliorer : combiner les + des concepts, lever les −.", "Nouveau tour avec le meilleur concept "
               "comme référence, jusqu'à ce qu'un concept domine ; « Décider » et justifier."],
     "roles": "Équipe pluridisciplinaire, un animateur ; 1 à 3 heures par tour.",
     "pitfalls": ["Pondérer en douce : Pugh classique ne pondère pas ; si des Criteria sont éliminatoires, passer "
                  "à Kepner-Tregoe.", "Criteria redondants qui comptent deux fois la même chose.",
                  "Référence mal choisie : tout devient + ou tout devient −."],
     "example": "Fixation des deux coquilles d'un pistolet à colle : vis, clips, collage, ultrasons ; Criteria = "
                "assemblage, réparation, fin de vie. Les clips dominent ; le collage est éliminé (démontage).",
     "faq": [("Pourquoi pas de poids ?", "La méthode sert à comprendre et améliorer les concepts, pas à calculer "
              "un gagnant ; les poids viennent ensuite avec Kepner-Tregoe."),
             ("Combien de tours ?", "Deux ou trois en général ; on s'arrête quand un concept est meilleur ou égal "
              "partout, ou que les − restants sont acceptés."),
             ("Peut-on utiliser des Needs comme Criteria ?", "Oui : « tous les Needs » est proposé dans la liste ; "
              "c'est souvent le meilleur premier tour.")]},
    {"key": "kepner_tregoe", "name": "Kepner-Tregoe (Decision Analysis)", "family": "convergent", "tool": "kt",
     "tagline": "Doit / Veut pondérés, puis risques : décider et justifier.",
     "goal": "Prendre une décision rationnelle et traçable (Kepner et Tregoe) : énoncer la décision, séparer les "
             "Criteria obligatoires (DOIT, éliminatoires) des souhaits (VEUT, pondérés de 1 à 10), noter les "
             "alternatives, puis évaluer les conséquences négatives (risques) des meilleures.",
     "when": "Pour trancher entre des options finalistes (souvent issues de Pugh), quand le choix doit être "
             "défendu (revue de conception, CCB, client).",
     "steps": ["Énoncer la décision : « Choisir … pour … ».", "Lister les DOIT : mesurables, éliminatoires (Requirements "
               "Goldmine de criticité élevée, standards).", "Lister les VEUT et leur poids (10 = le plus important).",
               "Pour chaque alternative : passe-t-elle chaque DOIT ? Sinon elle est éliminée.",
               "Noter chaque alternative de 1 à 10 sur chaque VEUT (10 = la meilleure) : score pondéré = Σ poids × "
               "note.", "Risques : pour les 2 ou 3 meilleures, lister les conséquences négatives, probabilité et "
               "gravité (Faible, Moyenne, Élevée).", "Décider en pesant score et risques ; consigner la "
               "justification."],
     "roles": "Décideur + experts ; 1 à 2 heures.",
     "pitfalls": ["Mettre un souhait en DOIT : il élimine une bonne option à tort.",
                  "Noter avant d'avoir fixé les poids.", "Ignorer les risques du gagnant."],
     "example": "Choisir l'élément chauffant : DOIT = certifiable CSA C22.2 / UL, alimentation 120 V ; VEUT = "
                "temps de chauffe (10), coût (8), délai d'approvisionnement (6), recyclabilité (4).",
     "faq": [("Différence avec Pugh ?", "Pugh explore et améliore sans poids ; Kepner-Tregoe tranche entre "
              "finalistes avec poids, éliminatoires et risques."),
             ("Les DOIT peuvent-ils venir de Goldmine ?", "Oui : chaque Criterion peut être lié à un requirement ou un "
              "Need Goldmine."),
             ("Et l'analyse de problème (cause racine) ?", "Kepner-Tregoe propose aussi l'analyse de problème "
              "(EST / N'EST PAS) ; l'outil couvre pour l'instant l'analyse de décision.")]},
]

REFERENCE = [
    {"key": "generator", "name": "Reference Generator", "family": "reference", "tool": "codex",
     "tagline": "Numéroter et classer les documents du PDP (MIP, RCS, CdCF, RC, RVE…).",
     "goal": "Réserver une référence documentaire unique (numéro série attribué par le serveur), avec le nom de "
             "fichier et le dossier.",
     "when": "Avant de créer tout document de conception, d'analyse ou de test.",
     "steps": ["Choisir le Space.", "Choisir le type de document et l'étape du PDP.", "Réserver : le nom de fichier "
               "et le dossier sont proposés.", "Réviser ou annuler depuis le registre (jamais effacer)."],
     "roles": "Tout auteur de document.", "pitfalls": ["Créer le fichier avant de réserver la référence."],
     "example": "CDCF (Cahier des charges fonctionnel), étape 11, « CdCF du pistolet à colle chaude ».",
     "faq": [("Où est passé l'onglet Generator ?", "Dans Tools, section « Generator » (Tools → Generator) ; son "
              "adresse (#/codex) ne change pas."), ("Une référence peut-elle être réutilisée ?", "Non : une référence s'annule, elle ne "
              "s'efface jamais.")]},
]
