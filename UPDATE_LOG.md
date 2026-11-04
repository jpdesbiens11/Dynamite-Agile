# Journal de mise à jour — 0.60.04

- **Version :** 0.60.03 → 0.60.04 (2026-11-04)
- **Changements :**
  1. **Site web en anglais** (D-O-017, étape 1) : les trois pages dans `site/en/` (accueil avec la descente dans la mine,
     la journée de l'équipe, la chaîne et les dix outils ; installation ; guide), bouton FR | EN dans la barre du haut,
     liens `hreflang` entre les deux versions. Noms des modules et termes techniques inchangés.
  2. **Installation en anglais** : `site/en/installer.md` pour l'assistant IA, message à coller en anglais, libellés
     « on your computer » / « on the server », boutons Copy ; `deploy/install.sh` affiche ses messages en anglais avec
     `DA_LANG=en` (`curl … | sudo DA_LANG=en bash -s -- domaine courriel`).
- **Base de données :** aucune migration.
