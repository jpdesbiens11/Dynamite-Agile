# Journal de mise à jour — 0.60.02

- **Version :** 0.60.01 → 0.60.02 (2026-11-03)
- **Changements :**
  1. **Base propre** (D-O-012) : plus aucune référence à l'usage ni au domaine d'origine, nulle part dans le dépôt (code,
     migrations, commentaires, exemples, tests, documentation, journaux). Colonnes du Generator `pdp_step` / `pdp_sub` ;
     index des décisions antérieures `docs/DECISIONS_ANTERIEURES.md`. Garde automatique dans `tests/test_open_v060.py`.
  2. **Réponses du brief** (D-O-013) : modules hors cours gardés, profils d'études et code D-FAB confirmés.
  3. **Les noms de la mine** (D-O-014) : `docs/NOMS_DES_MODULES.md`, FAQ de Help, site web.
  4. **Site web distinct** (D-O-015) : `site/index.html` (storyline défilante : la descente dans la mine, la journée de
     l'équipe, la chaîne, les outils, l'installation en trois commandes), `site/installation.html`, `site/guide.html` ;
     publication GitHub Pages (`.github/workflows/pages.yml`).
  5. **Installation sur un VPS** : `deploy/install.sh` (HTTPS Let's Encrypt, pare-feu, service systemd, configuration de
     production), `deploy/redeploy.sh`, `deploy/DEPLOIEMENT_VPS.md`.
- **Base de données :** 0.60.02 s'installe sur une base neuve (base propre) ; migrations additives à partir de cette version.
- **Champs [new] :** `0.60.02-faq-mine`.
