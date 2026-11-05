"""Rover example, Dynamite pages 2/2: C. Design (MVP 2) -- architecture, sensors, power budget, approach law and stopping
distance, avoidance algorithm, phone app and safety, PDR / CDR -- and D. Validation (MVP 3) -- test plan, validation report,
assembly notice."""
from .doc import children, code, h, ol, p, page, panel, table, ul

ALGO = """# Boucle de décision à 20 Hz (machine à états)
d = carte.distance_min()                 # fusion : la plus courte distance plausible
si arret_urgence ou liaison_perdue: etat = ARRET
si pare_chocs: etat = RECUL               # recule de 0,3 m, puis CHOIX
selon etat:
  ROULE    : vitesse = 1.0 si d > 1.2 sinon (etat = APPROCHE)
  APPROCHE : vitesse = 0.3 si d > 0.6 sinon 0.1 + 0.2 * (d - 0.30) / 0.30
             si d <= 0.30: etat = CHOIX
  CHOIX    : cote = gauche si carte.gauche > carte.droite + 0.10 sinon droite   # hystérésis 10 cm
             cap_initial = imu.cap(); etat = ECARTE
  ECARTE   : braque vers cote à 0,15 m/s jusqu'à carte.centre > 0.8 ; etat = LONGE
  LONGE    : avance 1 s à 0,3 m/s en gardant l'obstacle de côté ; etat = REVIENT
  REVIENT  : braque vers cap_initial jusqu'à |imu.cap() - cap_initial| < 15° ; etat = ROULE"""

DESIGN = [
    page("PC", "C. Design — MVP 2", None,
         p("**Question du MVP 2 : ça fonctionne ?** Tous les sous-systèmes sont conçus, calculés, revus (PDR, puis CDR) et assemblés. "
           "Le DFMEA de Diamond suit chaque action jusqu'à son essai."),
         children()),
    page("PC1", "Architecture et structure fonctionnelle", "PC",
         p("La structure fonctionnelle (boundary diagram) est dans **Diamond → Structure** : entrées à gauche, fonctions au centre, "
           "sorties à droite. Elle devient l'architecture en sous-systèmes."),
         table(["Sous-système", "Fonctions", "Responsable", "Interfaces"],
               [["Énergie", "F2, F3, F29", "Léa", "7,4 V au variateur ; 5 V au Pi et aux capteurs ; I2C (INA219)"],
                ["Perception", "F9 à F15", "Léa", "GPIO (ultrasons), I2C (temps de vol, centrale inertielle), GPIO (Hall, pare-chocs)"],
                ["Décision", "F16 à F20", "Alexis", "Logiciel Python sur le Pi, boucle de 20 Hz"],
                ["Propulsion et direction", "F21 à F25", "Nina", "PWM 50 Hz par la carte PCA9685"],
                ["Sécurité", "F26 à F28", "Léa", "MOSFET de coupure en série ; chien de garde matériel du Pi"],
                ["Structure", "F30 à F32", "Nina", "Plaque porte-modules, boîtier, pare-chocs"],
                ["Interface utilisateur", "F6 à F8, F33 à F35", "Hugo", "Page web et WebSocket sur le point d'accès Wi-Fi"]])),
    page("PC2", "Capteurs : choix et couverture", "PC",
         table(["Capteur", "Portée", "Cône", "Prix", "Pourquoi"],
               [["3 × ultrasons HC-SR04", "0,02 à 4 m", "≈ 30°", "≈ 4 $ chacun", "Couvrent ± 45° devant ; voient le verre"],
                ["Temps de vol VL53L1X", "0,04 à 4 m", "≈ 27°", "≈ 15 $", "Voit les obstacles mous que les ultrasons ratent"],
                ["Centrale inertielle ICM-20948", "—", "—", "≈ 15 $", "Cap pendant le contournement"],
                ["Effet Hall sur l'arbre", "—", "—", "≈ 5 $", "Vitesse réelle pour la loi d'approche"],
                ["2 microrupteurs de pare-chocs", "contact", "—", "≈ 2 $", "Dernier recours"]]),
         p("**Couverture vérifiée sur grille (ESSAI-19)** : aucun angle mort entre ± 45° au-delà de 0,3 m. Les ultrasons se déclenchent "
           "à tour de rôle, 25 ms d'écart, pour ne pas entendre l'écho du voisin (risque d'interférence)."),
         panel("note", "Les échos des HC-SR04 sont en 5 V : un diviseur de tension les ramène à 3,3 V pour le Pi (fonction technique F15).")),
    page("PC3", "Bilan de puissance et autonomie", "PC",
         table(["Consommateur", "Puissance moyenne"],
               [["Raspberry Pi 4", "4,0 W"], ["Capteurs", "0,5 W"], ["Servo de direction", "1,0 W"],
                ["Moteur de traction à vitesse lente", "9,0 W"], ["Pertes du convertisseur 5 V", "0,5 W"],
                ["Marge", "1,0 W"], ["**Total**", "**16 W**"]]),
         p("Batterie LiPo 2S : 7,4 V × 2,2 Ah = 16,3 Wh ; 80 % utilisables = 13,0 Wh. **Autonomie ≈ 13,0 / 16 = 0,81 h ≈ 49 min**, "
           "pour 30 min exigées (REQ-8). Mesuré à l'ESSAI-8 : 41 min."),
         panel("warning", "Coupure à 3,4 V par élément (6,8 V) et alerte à 3,6 V (REQ-19) : une LiPo trop déchargée gonfle et peut prendre feu.")),
    page("PC4", "Loi d'approche lente et distance d'arrêt", "PC",
         p("Distance d'arrêt = vitesse × latence + vitesse² / (2 × décélération), avec une latence de 0,1 s (boucle de 20 Hz et "
           "variateur) et une décélération mesurée de 2 m/s² sur le béton."),
         table(["Vitesse", "Distance d'arrêt", "Zone"],
               [["1,0 m/s", "0,10 + 0,25 = 0,35 m", "Seulement au-delà de 1,2 m"], ["0,3 m/s", "0,03 + 0,02 = 0,05 m", "De 1,2 à 0,6 m"],
                ["0,1 m/s", "0,01 + 0,003 ≈ 0,01 m", "Arrêt à 0,30 m"]]),
         table(["Distance de l'obstacle", "Vitesse permise"],
               [["Plus de 1,2 m", "1,0 m/s (vitesse maximale choisie dans l'application)"], ["1,2 à 0,6 m", "0,3 m/s"],
                ["0,6 à 0,30 m", "De 0,3 à 0,1 m/s, linéaire"], ["0,30 m et moins", "Arrêt, puis choix du côté"]]),
         panel("success", "À 1,0 m/s, le robot détecte l'obstacle à 2 m et passe à 0,3 m/s à 1,2 m : il lui reste 0,85 m de marge. Décision D-7.")),
    page("PC5", "Algorithme de contournement", "PC",
         p("Une machine à états simple, que les étudiants lisent et modifient. Chaque état apparaît en direct dans l'application."),
         code(ALGO, "text"),
         ul(["L'hystérésis de 10 cm sur le choix du côté corrige le bug B2 (oscillation devant un mur).",
             "Le gyroscope est calibré 2 s à l'arrêt au « Prêt » : sans calibration, le cap dérive (DFMEA, F20).",
             "Simulation sur ordinateur avant le robot : même code, capteurs simulés (risque « équipe en retard »)."])),
    page("PC6", "Application téléphone et sécurité", "PC",
         ol(["Le Pi démarre son point d'accès Wi-Fi « ROVER-xx » (le mot de passe est sur l'étiquette du robot).",
             "Le téléphone s'y connecte et ouvre l'adresse affichée sur l'étiquette : la page s'ouvre, rien à installer.",
             "« Démarrer » n'est actif qu'après l'autotest : coupure de traction vérifiée, capteurs lus, batterie au-dessus de 3,6 V par élément.",
             "Pendant le roulage : vue radar (trois ultrasons et temps de vol), vitesse, état de la machine, batterie, à 5 Hz ou plus.",
             "Le bouton d'arrêt d'urgence occupe le bas de l'écran ; un deuxième bouton est sur le robot."]),
         table(["Défaillance", "Réaction", "Requirement"],
               [["Plus de message du téléphone pendant 300 ms", "Traction coupée", "REQ-6"],
                ["Logiciel bloqué", "Chien de garde matériel : redémarrage, traction coupée", "REQ-6"],
                ["Arrêt d'urgence (téléphone ou robot)", "MOSFET ouvert ≤ 0,2 s", "REQ-7"],
                ["Batterie sous 3,4 V par élément", "Arrêt et message", "REQ-19"]])),
    page("PC7", "PDR et CDR : comptes rendus", "PC",
         h(2, "PDR (semaine 9)"),
         ul(["Présentés : architecture, bilan de puissance, distance d'arrêt, registre des risques, DFMEA préliminaire.",
             "Décisions : vitesse limitée à 0,3 m/s sous 1,2 m (D-7) ; coupure matérielle en plus du logiciel (D-6).",
             "Actions : rampe de démarrage du moteur (Léa), séquenceur des ultrasons (Alexis)."]),
         h(2, "CDR (semaine 12)"),
         ul(["Design figé : nomenclature de 23 pièces dans Diamond, environ 210 $ par robot.",
             "DFMEA : toutes les lignes de sévérité 9 ou 10 ont une action faite et un essai relié.",
             "Test Plan de validation approuvé : 20 essais, 3 parcours (A : boucle intérieure ; B : un obstacle ; C : dehors).",
             "Décision : passer à la phase D."])),
]

VALIDATION = [
    page("PD", "D. Validation et lancement — MVP 3", None,
         p("**Question du MVP 3 : prêt pour le marché ?** Les essais prouvent chaque requirement ; une autre équipe refait le projet à "
           "partir du wiki ; la décision de lancer le kit se prend sur les résultats."),
         children()),
    page("PD1", "Test Plan de validation", "PD",
         table(["Parcours", "Description", "Essais"],
               [["A", "Boucle intérieure de 40 m, 6 obstacles fixes", "ESSAI-3, ESSAI-8"],
                ["B", "Couloir de 10 m, un obstacle de 40 cm au centre", "ESSAI-2, ESSAI-4, ESSAI-6, ESSAI-7"],
                ["C", "Dehors : gazon court, gravier fin, trottoir, marche de 3 cm", "ESSAI-9"]]),
         p("Les 20 essais sont dans **Testing** (ESSAI-1 à ESSAI-20), chacun relié aux requirements qu'il prouve. Ordre d'exécution : "
           "banc (couverture, détection), sécurité (arrêts d'urgence, chien de garde), parcours, puis essais de normes en pré-conformité.")),
    page("PD2", "Validation Report et décision", "PD",
         panel("info", "Résultats fictifs de l'exemple, pour montrer la forme d'un rapport."),
         table(["Essai", "Requirement", "Critère", "Résultat", "Verdict"],
               [["ESSAI-1", "REQ-1", "≥ 95 %", "97 % (194 / 200)", "Réussi"], ["ESSAI-2", "REQ-2", "0 contact", "0 / 50", "Réussi"],
                ["ESSAI-3", "REQ-3", "écart ≤ 10 %", "6 % au pire", "Réussi"], ["ESSAI-4", "REQ-4", "9 / 10, ± 15°", "9 / 10, 11° au pire", "Réussi"],
                ["ESSAI-6", "REQ-6", "≤ 0,5 s", "0,34 s au pire", "Réussi"], ["ESSAI-7", "REQ-7", "≤ 0,2 s", "0,06 s", "Réussi"],
                ["ESSAI-8", "REQ-8, REQ-19", "≥ 30 min", "41 min, coupure à 6,81 V", "Réussi"],
                ["ESSAI-9", "REQ-10", "3 / 3", "2 / 3 avant correctif, 3 / 3 après (bug B3)", "Réussi"],
                ["ESSAI-11", "REQ-14, REQ-15", "6 dB de marge", "4 dB à 120 MHz", "Justifié : ferrite sur le câble moteur, à confirmer au laboratoire"],
                ["ESSAI-14", "REQ-12", "≤ 250 $", "212 $", "Réussi"]]),
         panel("success", "Décision D-10 : lancer le kit pour les écoles. Action ouverte : essai CEM au laboratoire reconnu avec la ferrite.")),
    page("PD3", "Notice de montage et sécurité de la batterie", "PD",
         ol(["Vérifiez le contenu du kit avec la nomenclature (Diamond → Pièces).",
             "Vissez la plaque porte-modules sur le châssis (4 entretoises M3).",
             "Posez les trois ultrasons et le temps de vol dans le support avant ; branchez-les selon le schéma.",
             "Branchez le variateur et le servo sur la carte PCA9685, puis la coupure de traction.",
             "Insérez la carte microSD préparée, fermez le boîtier électronique avec son joint.",
             "Chargez la batterie dans son sac ignifuge, sous surveillance, avec un chargeur LiPo certifié.",
             "Mettez sous tension, connectez le téléphone au Wi-Fi « ROVER-xx », attendez « Prêt »."]),
         panel("warning", "Batterie LiPo : jamais de charge sans surveillance ni hors du sac ignifuge ; une batterie gonflée ou percée "
                          "ne se recharge plus et se rapporte à un point de collecte. Kit destiné aux 14 ans et plus.")),
]

PAGES_CD = DESIGN + VALIDATION
