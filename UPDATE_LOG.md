# Journal de mise à jour — 0.60.19

- **Version :** 0.60.18 → 0.60.19 (2026-11-04)
- **Changements :**
  1. **Initiales automatiques** (D-O-030) : JDE d'après le nom, ADM pour admin, uniques, modifiables ; données aux comptes existants au démarrage.
  2. **Space par défaut** : corrigé, il ne revient plus en arrière (sauvegardes des réglages fusionnées) ; le wiki TOOLS n'est plus proposé.
- **Base de données :** aucune migration ; au démarrage, les comptes sans initiales en reçoivent (réglages personnels, rien d'autre ne change).

## Précédent

### Journal de mise à jour — 0.60.18

- **Version :** 0.60.17 → 0.60.18 (2026-11-04)
- **Changements :**
  1. **Prompt de départ** `starter.md` (D-O-019) : l'entrevue d'un assistant IA, 20 questions une à la fois, qui produit le fichier Project Starter ; valeurs permises et exemple tirés de l'outil.
  2. **Commencer** : étape « 1. Préparer le fichier avec un assistant IA », Copier le prompt / Télécharger, hors ligne aussi.
  3. **Site** : `starter.md` (FR / EN) et une section du guide.
- **Base de données :** aucune migration.

### Journal de mise à jour — 0.60.17

- **Version :** 0.60.16 → 0.60.17 (2026-11-04)
- **Changements :**
  1. **Installation derrière Traefik** (D-O-029) : `install.sh --traefik <adresse>` pour un serveur où Traefik tient déjà les
     ports 80 et 443 (VPS Hostinger avec applications Docker) : Dynamite | Agile dans son conteneur, Traefik donne le HTTPS,
     rien d'autre ne bouge.
  2. **Noyau** : `trusted_proxies` ; derrière le proxy, l'adresse du visiteur et le HTTPS sont reconnus ; accès direct refusé.
  3. **Site** : dépannage « ports 80 ou 443 déjà pris » quand c'est Traefik.
- **Base de données :** aucune migration.

### Journal de mise à jour — 0.60.16

- **Version :** 0.60.15 → 0.60.16 (2026-11-04)
- **Changements :**
  1. **Diamond → Golden Nuggets** (D-O-028) : vingt principes pour concevoir à partir des premiers principes (esprit TRIZ),
     l'algorithme en cinq étapes et les règles de conception de SpaceX et Tesla, chacun avec un exemple de l'industrie et
     son usage sur le projet ; recherche et thèmes.
  2. **Training** : topic DM-05 et son test.
- **Base de données :** aucune migration.

### Journal de mise à jour — 0.60.15

- **Version :** 0.60.14 → 0.60.15 (2026-11-04)
- **Changements :**
  1. **Diamond → DFMEA** (D-O-027) : le Design FMEA AIAG-VDA sur les fonctions de l'arbre : trois niveaux aux en-têtes blanc,
     bleu et orange, chaîne effet / mode / cause, S / O / D, RPN et Action Priority côte à côte ; édition en place, lignes à
     ajouter, dupliquer, déplacer (Alt + flèches) et effacer ; colonnes masquables ; Depuis l'arbre, Depuis les risques ;
     conseils ; export CSV ; exemple de la lampe.
  2. **Légende AP** : page de formation (pourquoi l'AP, tableau complet, échelles S / O / D).
  3. **Training** : topic DM-04 et son test.
- **Base de données :** migration diamond 4 (table `diamond_dfmea`), additive.

### Journal de mise à jour — 0.60.14

- **Version :** 0.60.13 → 0.60.14 (2026-11-04)
- **Changements :**
  1. **Diamond → Risques projet** (D-O-026) : le registre des risques du projet, avant le DFMEA : « Si / alors / ce qui »,
     probabilité × impact (1 à 5), niveaux Faible / Moyen / Élevé / Critique, carte 5 × 5 maintenant et résiduelle, stratégie,
     action, responsable, échéance, lien vers une fonction et « À détailler dans le DFMEA », conseils, export CSV.
  2. **Training** : topic DM-03 et son test.
- **Base de données :** migration diamond 3 (table `diamond_risks`), additive.

### Journal de mise à jour — 0.60.13

- **Version :** 0.60.12 → 0.60.13 (2026-11-04)
- **Changements :**
  1. **Diamond → Structure fonctionnelle** (D-O-025) : le boundary diagram du produit, tiré de l'arbre fonctionnel :
     entrées à gauche, sorties à droite, vue générale par sous-systèmes, vue détaillée par fonctions tertiaires ; flux
     d'énergie, de matière et d'information (légende du cours), avec libellés ; glisser les blocs, relier en cliquant la
     cible ; conseils de la méthode ; exemple de la lampe de bureau.
  2. **Training** : topic DM-02 et son test.
- **Base de données :** migration diamond 2 (tables `diamond_ports`, `diamond_flows`, `diamond_positions`), additive.

### Journal de mise à jour — 0.60.12

- **Version :** 0.60.11 → 0.60.12 (2026-11-04)
- **Changements :**
  1. **Versions officielles** (D-O-024) : Admin → Update → Framework, bloc « Versions officielles » : lien vers la page des
     versions du site, avec votre version ; le paquet téléchargé se dépose ici ; une étape de revue par version, plusieurs
     versions d'un coup, « Plus tard » ; empreinte SHA-256 et fichiers modifiés à la main affichés. Données jamais touchées.
  2. **Site** : nouvelle page « Versions » (FR / EN) ; paquet construit à chaque publication.
  3. **Installation** : relancer la commande d'installation met à jour même après un paquet appliqué (copie `.patch`).
- **Base de données :** aucune migration.

### Journal de mise à jour — 0.60.11

- **Version :** 0.60.10 → 0.60.11 (2026-11-04)
- **Changements :**
  1. **Diamond 💎** (D-O-023) : nouvel onglet, à 1 000 m dans la mine, pour l'analyse fonctionnelle du produit.
  2. **Arbre fonctionnel** : fonction primaire à gauche, « comment » à droite, « quand » de haut en bas ; secondaires,
     tertiaires et fonctions techniques ; chemin critique, rétroaction, fonctions hors arbre ; glisser-déposer, Alt + flèches ;
     panneau de lecture (pourquoi ? comment ? quand ?) ; vue liste ; exemple « lampe de bureau connectée ».
- **Base de données :** migration diamond 1 (table `diamond_functions`), additive.

### Journal de mise à jour — 0.60.10

- **Version :** 0.60.09 → 0.60.10 (2026-11-04)
- **Changements :**
  1. **Serveur d'équipe sur un PC Windows** (D-O-022) : nouvelle destination « Sur un PC Windows de l'équipe » de la page
     d'installation (FR / EN). Dans PowerShell en administrateur, une commande installe Python et Git, récupère le code,
     crée le certificat HTTPS de l'équipe, règle la production, ouvre le pare-feu pour les réseaux privés seulement et
     crée la tâche qui démarre l'outil avec Windows. La relancer met à jour sans toucher aux données.
  2. **HTTPS sans domaine** : `tools/make_team_ca.py` crée l'autorité de certification de l'équipe et le certificat du PC ;
     chaque poste importe une fois `ca-dynamite.crt`.
  3. **Configuration** : `tools/write_config.py` règle `data/config.json` en ligne de commande ; `config.json` modifié dans
     le Bloc-notes (avec BOM) est accepté.
- **Base de données :** aucune migration.
