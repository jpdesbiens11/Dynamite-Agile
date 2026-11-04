# Journal de mise à jour — 0.60.05

- **Version :** 0.60.04 → 0.60.05 (2026-11-04)
- **Changements :**
  1. **Format Project Starter** (D-O-019) : un fichier JSON `dynamite-project-starter` décrit un projet (équipe,
     besoins et requis, essais, codes de temps, pages Dynamite), préparé avec un assistant IA. `core/starter.py` le
     vérifie champ par champ et donne le correctif de chaque refus ; tout requis et tout essai arrive « À vérifier »,
     chaque page en « Brouillon IA », aucun membre n'est administrateur. Spécification : `docs/STARTER_FORMAT.md`.
  2. **Vérifier un fichier sans rien créer** : `python3 tools/check_starter.py mon_projet.json`.
  3. **Trois exemples** dans `deploy/starter_exemples/` : lampe de bureau connectée, tensiomètre de poignet,
     convoyeur de table modulaire.
- **Base de données :** aucune migration.
