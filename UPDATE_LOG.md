# Journal de mise à jour — 0.60.13

- **Version :** 0.60.12 → 0.60.13 (2026-11-04)
- **Changements :**
  1. **Diamond → Structure fonctionnelle** (D-O-025) : le boundary diagram du produit, tiré de l'arbre fonctionnel :
     entrées à gauche, sorties à droite, vue générale par sous-systèmes, vue détaillée par fonctions tertiaires ; flux
     d'énergie, de matière et d'information (légende du cours), avec libellés ; glisser les blocs, relier en cliquant la
     cible ; conseils de la méthode ; exemple de la lampe de bureau.
  2. **Training** : topic DM-02 et son test.
- **Base de données :** migration diamond 2 (tables `diamond_ports`, `diamond_flows`, `diamond_positions`), additive.

## Précédent

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
