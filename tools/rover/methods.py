"""Rover example: the design methods filled in the tools themselves -- a brainstorming session (Tools → Idéation), the Pugh
Matrix of the four concepts on the Space's requirements (Goldmine → Pugh) and the Kepner-Tregoe analysis of the two finalists
(Tools → Kepner-Tregoe). The pages « Matrice de Pugh » and « Kepner-Tregoe » of phase B explain the same decisions."""

C1, C2, C3, C4 = ("C1 · 3 ultrasons (référence)", "C2 · Lidar rotatif 360°", "C3 · Caméra et vision", "C4 · Ultrasons + temps de vol + pare-chocs")

IDEATION = [{
    "title": "Comment le Rover peut-il percevoir et contourner un obstacle ?",
    "prompt": "Toutes les façons de savoir qu'un obstacle est devant, et de le contourner lentement. Pas de critique pendant la séance.",
    "ideas": ["Trois ultrasons en éventail", "Un seul ultrason sur un servo qui balaie", "Lidar rotatif 360°", "Caméra et détection d'objets",
              "Capteur à temps de vol dans l'axe", "Pare-chocs avec microrupteurs", "Moustaches en fil d'acier comme un chat",
              "Infrarouge analogique (Sharp)", "Suivre le mur à droite (règle de la main droite)", "Reculer, tourner au hasard, repartir",
              "Champ de potentiel : l'obstacle repousse, le but attire", "Ralentir avant de décider", "Choisir le côté le plus libre",
              "Revenir au cap initial avec le gyroscope", "Montrer la décision dans l'application", "Carte des obstacles sur le téléphone"],
}]

PUGH = [{
    "title": "Concept de perception et de décision du Rover",
    "description": "Quatre concepts tirés de la matrice morphologique, comparés à la référence C1 sur les requirements du CdCF.",
    "concepts": [{"name": C1, "description": "Trois HC-SR04 à ± 45°, règles simples, application web, LiPo."},
                 {"name": C2, "description": "Lidar 2D, champ de potentiel, application web, LiPo."},
                 {"name": C3, "description": "Caméra du Pi, réseau de neurones, application native, LiPo."},
                 {"name": C4, "description": "Trois ultrasons, temps de vol dans l'axe, pare-chocs, règles, application web, LiPo."}],
    "criteria": [
        {"requirement": "REQ-1", "scores": {C2: "+", C3: "+", C4: "+"}},
        {"requirement": "REQ-2", "scores": {C2: "+", C3: "S", C4: "+"}},
        {"requirement": "REQ-3", "scores": {C2: "S", C3: "-", C4: "S"}},
        {"requirement": "REQ-8", "scores": {C2: "-", C3: "-", C4: "S"}},
        {"requirement": "REQ-10", "scores": {C2: "+", C3: "-", C4: "S"}},
        {"requirement": "REQ-12", "scores": {C2: "-", C3: "S", C4: "-"}},
        {"requirement": "REQ-13", "scores": {C2: "-", C3: "S", C4: "S"}},
        {"requirement": "REQ-23", "scores": {C2: "-", C3: "S", C4: "+"}},
        {"requirement": "BES-7", "scores": {C2: "+", C3: "+", C4: "+"}},
    ],
    "decision": C4,
    "note": "C4 et C2 ont le plus de « + » ; C3 est éliminé (vision trop lourde pour un premier projet, consommation). "
            "Kepner-Tregoe départage C4 et C2 (décision D-3).",
}]

KT = [{
    "title": "Choix final : fusion de capteurs ou lidar",
    "statement": "Choisir le concept de perception et de décision du Rover pour le MVP 2.",
    "alternatives": [{"name": C4, "description": "Environ 210 $ par robot."}, {"name": C2, "description": "Environ 240 $ par robot."}],
    "criteria": [
        {"kind": "must", "text": "Pièces à 250 $ ou moins par robot", "requirement": "REQ-12", "scores": {C4: 1, C2: 1}},
        {"kind": "must", "text": "Arrêt avant contact possible", "requirement": "REQ-2", "scores": {C4: 1, C2: 1}},
        {"kind": "must", "text": "Pièces disponibles chez deux fournisseurs", "scores": {C4: 1, C2: 1}},
        {"kind": "want", "text": "Détecter les obstacles bas et mous", "weight": 10, "requirement": "REQ-1", "scores": {C4: 8, C2: 7}},
        {"kind": "want", "text": "Apprendre par étapes, un capteur à la fois", "weight": 9, "scores": {C4: 9, C2: 6}},
        {"kind": "want", "text": "Coût", "weight": 8, "scores": {C4: 8, C2: 5}},
        {"kind": "want", "text": "Robustesse aux chocs du terrain", "weight": 7, "requirement": "REQ-23", "scores": {C4: 8, C2: 5}},
        {"kind": "want", "text": "Consommation", "weight": 5, "requirement": "REQ-8", "scores": {C4: 8, C2: 6}},
        {"kind": "want", "text": "Montrer la technologie", "weight": 4, "requirement": "BES-7", "scores": {C4: 6, C2: 9}},
    ],
    "risks": [{"alternative": C4, "text": "Interférence entre les ultrasons", "probability": 2, "seriousness": 1},
              {"alternative": C2, "text": "Lidar tournant brisé par une chute", "probability": 2, "seriousness": 3},
              {"alternative": C2, "text": "Rupture de stock du lidar", "probability": 2, "seriousness": 2}],
    "decision": C4,
    "note": "C4 : 345 points contre 265, et des risques plus faibles. Le lidar reste une idée pour un MVP x (décision D-3).",
}]

TOOLS = {"ideation": IDEATION, "pugh": PUGH, "kt": KT}
