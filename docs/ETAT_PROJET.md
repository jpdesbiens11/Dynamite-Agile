# Dynamite | Agile — État du projet (branche `open/v0.60`)

**Dernière mise à jour :** 2026-11-04 (v0.60.09)
**Version :** 0.60.09 — +1 sur le dernier chiffre à chaque livraison (D-O-001)
**Chantier actif :** démarrer un projet avec un assistant IA (D-O-019) — 0.60.09 livrée (PDP modernisé, Lean Startup, D-O-021) ; suite : 0.60.10 `starter.md`

Décisions : `docs/DECISIONS.md` (D-O-xxx) ; décisions antérieures citées dans le code : `docs/DECISIONS_ANTERIEURES.md`.

---

## Table 1 : Feuille de route

| Version | Contenu | Statut |
|---|---|---|
| 0.60.01 | Identité générique, About, Test Base et requis grand public, Generator et Timesheet sur le PDP, équipe d'exemple et « Profil d'études », vacances et réclamations de financement, licence MIT (D-O-001 à D-O-011) | Livré |
| 0.60.02 | Base propre sans aucune référence à l'usage d'origine (D-O-012), réponses Q4 / Q5 (D-O-013), noms de la mine (D-O-014), site web distinct dans `site/` : page d'entrée en storyline, installation, guide (D-O-015), `deploy/install.sh` pour un VPS | Livré |
| 0.60.03 | Installation pour débutants : choix de la destination, commandes remplies et copiables, assistant IA guidé (`installer.md`), installation en une commande et essai privé (D-O-016) | Livré |
| 0.60.04 | FR / EN, étape 1 (D-O-017) : le site web en anglais (`site/en/`), sélecteur FR \| EN, `installer.md` anglais, messages de `install.sh` en anglais avec `DA_LANG=en` | Livré |
| 0.60.05 | Format Project Starter (D-O-019) : `core/starter.py`, `tools/check_starter.py`, `docs/STARTER_FORMAT.md`, trois exemples dans `deploy/starter_exemples/` | Livré |
| 0.60.06 | « Commencer » côté serveur (D-O-019) : `core/starter_apply.py`, `/api/starter/check` et `/apply`, création du Space en une transaction, « À vérifier » stocké (migrations agile 15, testing 5) | Livré |
| 0.60.07 | Écran « Commencer » (téléverser, aperçu, renommer les codes, mots de passe temporaires) ; badge « À vérifier » et confirmation de la norme ; « Accepted » / « Approved » refusés tant qu'elle n'est pas confirmée (D-O-019) | Livré |
| 0.60.08 | Page « Débuter » (D-O-020) : parcours du projet phase par phase, module par module ; page d'arrivée jusqu'à ce qu'on la ferme, puis onglet | Livré |
| 0.60.09 | PDP modernisé avec le Lean Startup (D-O-021) : phases Discovery / Concept / Design / Validation et lancement, une boucle MVP par phase (tornade de « Débuter »), Lean Canvas, Concept Review, PDR / CDR, Validation Report ; MIP, RCS, RC, RVE retirés | Livré |
| 0.60.10 | Prompt `site/starter.md` (FR / EN), sa page sur le site, liens depuis « Commencer », « Débuter » et Help (D-O-019) | À faire |
| 0.60.11 et suivantes | Une à la fois : FR / EN étapes 2 à 4 (cadre de l'outil, modules, contenu) ; analyse fonctionnelle visuelle (arbre à 3 niveaux, méthodes de recherche des fonctions, lien CdCF) ; boundary diagram éditable ; exemples remplis de Pugh et Kepner-Tregoe ; Storyline (outil) ; Spaces de référence réécrits (pistolet à colle, imprimante à jet d'encre, machine à commande numérique pour bois mou) ; notes de cours réécrites ; évaluation par les pairs ; captures du guide Agile sur l'équipe d'exemple | À faire |

## Table 2 : Questions du brief §5 (toutes tranchées)

| # | Question | Réponse |
|---|---|---|
| 1 | Droits sur le contenu de référence | Réécrit en contenu original (D-O-009) |
| 2 | Licence du code | MIT (D-O-010) |
| 3 | Hébergement et nom du dépôt public | GitHub, https://github.com/jpdesbiens11/Dynamite-Agile (D-O-011) ; site : https://jpdesbiens11.github.io/Dynamite-Agile |
| 4 | Modules hors cours | Gardés ; évaluation par les pairs à venir (D-O-013) |
| 5 | Profils d'études de l'équipe d'exemple | Confirmés (D-O-013) |
| 6 | Langue : français seulement ou FR / EN | **FR / EN au moins** (D-O-017), par étapes : site, cadre de l'outil, modules, contenu ; noms des modules et contenu technique en anglais inchangés |
| 7 | Règle A/B à tour de rôle pour cette branche | **Non** : un seul compte, un seul projet (D-O-018) |

## Relais (fin de 0.60.09)

- PDP Lean (D-O-021) : `modules/codex/catalog.py` (DOC_GROUPS, RETIRED, STEP_GROUPS), `modules/timesheet/catalog.py` (libellés, `OLD_PDP_LABELS` relus par `budget.seed`), `static/js/tools/debuter_content.js` (champs `mvp`, `review`) et `debuter_tornado.js` ; `tests/test_lean.py` refuse les anciens noms dans l'interface.

- « Débuter » : `static/js/tools/debuter.js` + `debuter_content.js` (données, ordre du PDP), préférence `debuter_done` (`core/prefs.py`), arrivée dans `app.js` (`route()`), onglet dans `DA.NAV.groups[0]` (`sketch.js`) ; `tests/test_debuter.py` vérifie que chaque bouton mène à un écran qui existe.

- Écran : `static/js/admin_starter.js` (Admin → Spaces → Commencer), carte du Dashboard (`/api/starter/status`), `DA.review` (`static/js/tools/review.js`) dans Goldmine et Testing. 0.60.08 : le prompt `site/starter.md` (sources `tools/site/`), FR / EN, une question à la fois, qui produit le format de `docs/STARTER_FORMAT.md` ; lien depuis l'écran « Commencer » et Help.

- Project Starter (D-O-019) : `core/starter.parse(bytes)` → `(clean, warnings)`, ne touche pas la base ; `starter.summary(clean)` pour l'aperçu. Création : `core/starter_apply.py` (check / apply, réutilise `admin.create_project_record`, `goldmine.api_create`, `tests_api.create`, `pages.api_create`). 0.60.07 : l'écran, puis la confirmation de la norme (`standard_review` → `verified`, `standard_checked` = date · personne · édition) et le refus d'« Accepted » (requis) / « Approved » (essai) d'ici là.

- Tests : `python3 -m unittest discover -s tests -t .` + `node tests/js/ai_markdown.js`, `node tests/js/editor_roundtrip.js`.
  `tests/test_open_v060.py` balaie tout le dépôt (noms de fichiers, textes, contenu des .docx) à la recherche des mots
  de l'usage d'origine (liste encodée dans le test) et vérifie que le site est à jour.
- Démarrage de développement : `python3 app_dynamite_agile.py --dev-admin` → Spaces EQP (équipe d'exemple, 47 besoins et
  requis génériques), INT (temps interne et congés), HEADLAMP, TESTING, TOOLS, TRAINING.
- Site web : `python3 tools/build_site.py` → `site/` (publié par `.github/workflows/pages.yml`) ; sources dans
  `tools/site/` (français) et `tools/site/en/` (anglais, publié dans `site/en/`) ; textes partagés par langue dans
  `tools/site_text.py` ; il reprend le CSS, le sprite, les logos et la « journée » de la vitrine (`tools/build_vitrine.py`).
- FR / EN : prochaine étape (2) = le cadre de l'outil : choix `language` fr / en dans `core/prefs.py` (CHOICES n'a que
  `fr` aujourd'hui), barre du haut, menus, Paramètres, Admin, messages d'erreur du serveur par catalogue.
- Installation : `deploy/install.sh` (Ubuntu / Debian, Let's Encrypt, ufw, systemd) ; résumé dans
  `deploy/DEPLOIEMENT_VPS.md`, procédure illustrée dans `site/installation.html`, guide de l'assistant IA
  `site/installer.md`. Pas encore essayé sur un vrai VPS ; site publié par GitHub Pages sur https://jpdesbiens11.github.io/Dynamite-Agile une fois le code poussé et Pages activé (Settings → Pages → Source : GitHub Actions).
- 0.60.02 est la base propre (D-O-012) : elle s'installe sur une base de données neuve ; migrations additives à partir d'ici.
