# Dynamite | Agile — État du projet (branche `open/v0.60`)

**Dernière mise à jour :** 2026-11-06 (v0.60.52)
**Version :** 0.60.52 — +1 sur le dernier chiffre à chaque livraison (D-O-001)
**Chantier actif :** 0.60.52 (demande de JP du 2026-11-06) : Copier pour l'IA, importer la réponse, Storyline du Rover, Storytelling retiré de Tools

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
| 0.60.10 | Serveur d'équipe sur un PC Windows (D-O-022) : `deploy/install.ps1`, autorité de certification de l'équipe (`tools/make_team_ca.py`), tâche planifiée, pare-feu privé ; 4e destination de la page d'installation FR / EN | Livré — à essayer sur un vrai PC Windows |
| 0.60.11 | Diamond 💎 (D-O-023), 1 000 m : module, onglet, logo ; Arbre fonctionnel (primaire / secondaires / tertiaires / techniques, comment · pourquoi · quand, chemin critique, rétroaction, hors arbre, glisser-déposer, Alt + flèches, exemple lampe de bureau) | Livré |
| 0.60.12 | Versions officielles (D-O-024) : paquet par version (`tools/build_release.py`, workflow Pages), page `versions.html` FR / EN, Admin → Update : manifeste, une étape par version, plusieurs versions d'un coup, fichiers modifiés à la main, « Plus tard » ; installateurs qui ne bloquent plus | Livré — essayé de 0.60.11 à 0.60.12 |
| 0.60.13 | Diamond : structure fonctionnelle (D-O-025) : entrées à gauche, sorties à droite, vue générale (sous-systèmes) et détaillée (tertiaires), flux énergie / matière / information selon la légende du cours, conseils de la méthode, glisser, relier | Livré |
| 0.60.14 | Diamond : analyse de risque projet (D-O-026) : registre R-n, carte 5 × 5 maintenant / résiduelle, stratégie, action, responsable, échéance, lien vers une fonction et vers le DFMEA, conseils, CSV | Livré |
| 0.60.15 | Diamond : DFMEA AIAG-VDA (D-O-027) : trois niveaux aux en-têtes blanc / bleu / orange, fonctions de l'arbre, S / O / D, RPN et AP, page de la légende AP, colonnes masquables, lignes ajouter / dupliquer / déplacer / effacer, Depuis l'arbre, Depuis les risques | Livré |
| 0.60.16 | Diamond : Golden Nuggets (D-O-028) : 20 principes (esprit TRIZ), algorithme en 5 étapes, règles de SpaceX et Tesla, exemples et usage sur le projet | Livré |
| 0.60.17 | Installation derrière Traefik (D-O-029) : `install.sh --traefik`, conteneur avec étiquettes, noyau `trusted_proxies` (X-Forwarded-For / -Proto), accès direct refusé | Livré |
| 0.60.18 | Prompt `site/starter.md` (FR / EN) : entrevue de 20 questions, format exact tiré de l'outil, « Copier le prompt » dans Commencer, section du guide (D-O-019) | Livré |
| 0.60.19 | Initiales données d'après le nom (JDE, ADM) ; Space par défaut corrigé : sauvegardes des réglages fusionnées (D-O-030) | Livré |
| 0.60.20 | Diamond : pièces sur les fonctions, matrice pièces × fonctions, conseils d'architecture (D-O-031) ; Timesheet : code hors du Funding Space montré et refusé à la soumission | Livré |
| 0.60.21 | Le Space de travail suit d'un onglet à l'autre, ☆ / ★ Space par défaut près de chaque liste ; copie de Space avec Diamond (D-O-030) | Livré |
| 0.60.22 | Commencer : Diamond préliminaire (arbre, structure, pièces, risques, DFMEA) et plan de référence du PDP selon l'équipe ; prompt de 26 questions (D-O-032) | Livré |
| 0.60.23 | La page reste où l'on regarde (DA.keepScroll, routeur) ; panneau d'un sous-système avec les pièces de ses tertiaires | Livré |
| 0.60.24 | DFMEA : un essai clé de la Test Base par ligne dans Detection Controls ; Project Starter dfmea[].test (D-O-033) | Livré |
| 0.60.25 | Téléphones : barre compacte, menu tiroir, une colonne, tableaux défilants, cibles de 44 px (D-O-034) | Livré |
| 0.60.26 | Choix multiples appliqués ensemble : Appliquer ou clic à côté, Échap pour annuler (D-O-035) | Livré |
| 0.60.27 | Téléphone : cartes pour Goldmine / Testing / Timesheet, Dynamite + Page / IA / Partager, grands écrans pour l'ordinateur (D-O-036) | Livré |
| 0.60.28 | DFMEA : une ligne par fonction, essai clé relié, bonnes pratiques en prévention, RAS justifié ; Space étoilé ; About (D-O-037) | Livré |
| 0.60.29 | « Partager » : feuille du téléphone, lien, courriel, texto, Messenger, WhatsApp, Teams (D-O-038) | Livré |
| 0.60.30 | Partager : lien copié d'abord, versions web, code QR vers le téléphone (D-O-038) | Livré |
| 0.60.31 | Performances : ETag / 304 et gzip des fichiers de l'interface (D-O-039) | Livré |
| 0.60.32 | Logo « DynamiteAgile » : un mot, deux couleurs, Baloo 2 (D-O-040) | Livré |
| 0.60.33 | Exporter Diamond : Excel, draw.io, Word, marque Co-Intelligence WorkFlow™ (D-O-041) | Livré |
| 0.60.34 | Installation : question Traefik, détection par install.sh ; site web avec Diamond et les nouveautés (D-O-042) | Livré |
| 0.60.35 | Le pointeur et Bob le mineur en lecture seule (D-O-043, D-O-044) | Livré |
| 0.60.36 | Mise à jour en ligne : vérifier, approuver, progression (D-O-045) | Livré |
| 0.60.37 et suivantes | Une à la fois : FR / EN étapes 2 à 4 (cadre de l'outil, modules, contenu) ; méthodes de recherche des fonctions et lien CdCF dans Diamond ; exemples remplis de Pugh et Kepner-Tregoe ; Storyline (outil) ; Spaces de référence réécrits (pistolet à colle, imprimante à jet d'encre, machine à commande numérique pour bois mou) ; notes de cours réécrites ; évaluation par les pairs ; captures du guide Agile sur l'équipe d'exemple | À faire |

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

## Relais (fin de 0.60.54)

- Rover vivant (D-O-063) : `modules/help/demo_life.py` (équipe, horloge, Agile), `demo_life_more.py` (Change, Goldmine, Testing, Exploration, Timesheet, Diamond), contenu `demo_life_data.py` ; appel au démarrage dans `modules/help/__init__.py`.

- Import Compléter / Tout remplacer (D-O-062) : `modules/diamond/import_merge.py` (plan, wipe, sauvegarde), `story_ai.api_import` (mode add | replace), `starter_diamond.apply(known=)` ; écran `static/js/diamond/story_ai.js`.


- Storyline → IA (D-O-061) : `modules/diamond/story_ai.py` (prompt, import), `static/js/diamond/story_ai.js` ; format `diamond.story` dans `core/starter_diamond.py` ; Rover `tools/rover/story.py` ; `demo_example.ensure_story`.


- Storyline (D-O-060) : `modules/diamond/story.py`, écran `static/js/diamond/story*.js`, pictogrammes `tools/story_pictos.py` (relancer `python3 tools/make_sketch_assets.py`). Suit : « Copier pour l'IA » et import d'un fichier Project Starter dans un Space existant (0.60.52).


- Exports Diamond (D-O-059) : `export_pptx.py` lit `Page.items` de `export_drawio.py` ; `?only=` dans `export_api.py` ; menu `static/js/diamond/export_menu.js`.


- DEMO (D-O-058) : `modules/help/headlamp.py` (KEY, migrate), `modules/help/demo_example.py` (Rover, une fois), `permissions.demo_hidden`, `/api/admin/demo`.


- Langue (D-O-057) : `static/js/tools/langswitch.js` (bouton), `prefs.CHOICES["language"]`, textes du cadre dans `static/js/tools/i18n.js` (`DA.t`). Suit : traduire les écrans des modules.


- Partager sur le site (D-O-056) : `build_site._share`, textes `site_text.SHARE`, menu dans `tools/site/site.js`.


- Exemple Rover (D-O-055) : `tools/rover/` (contenu), `tools/make_rover_example.py` → `deploy/spaces_exemples/rover.json` (relancer après chaque changement ; le test compare). Format `tools` : `core/starter_tools.py`, relu par `core/starter_export_tools.py`.


- Documentation des modules (D-O-054) : `modules/help/module_docs*.py` (texte, références), `module_docs_pages.py` (HeadLamp), `tools/site_modules.py` (site). Pour ajouter un module : une entrée dans MODULES, ses références dans REFS.


- Installation (D-O-053) : `deploy/install.sh --local`, page `tools/site/installation.html` (dest online/local/windows, pc win/mac/linux), `install.js`. Suit : documentation par module avec références (0.60.45).


- Project Starter complet (D-O-052) : `core/starter_more.py` (backlog, deliverables), `core/starter_export.py` + `starter_export_more.py` (Space → fichier), `starter_prompt.render(proven=)`. Suit : documentation par module (0.60.44).


- Space par défaut (D-O-051) : `core/dashboard.py` (scope, ?all=1), `search.js` scope(). Suivent : prompt complet et export d'un Space éprouvé (0.60.43), documentation par module (0.60.44).


- Spaces en vase clos (D-O-050) : `modules/help/reference.py` (space, ensure) ; `catalog.ref_key` (Testing) ; `budget.leave`. Suivent : le Space par défaut couvre toute la plateforme (0.60.42), le prompt complet et l'export d'un Space éprouvé (0.60.43), la documentation (0.60.44).


- Accueil (D-O-049) : `tools/site_text.py` (MINE, STORY, DIAMONDS), `build_site._story`, `site.js` (--deep). Suit : plateforme vide et Spaces en vase clos (0.60.41).


- Page d'installation (D-O-048) : `tools/site/installation.html` et `en/`, `install.js` (state os / vps / domain / email / ip) ; suivent la storyline de l'accueil (0.60.40), la plateforme vide et les Spaces en vase clos (0.60.41).


- Actions de Diamond (D-O-047) : `modules/diamond/actions.py` (owner, due, enrich, api_track, mine, dashboard) ; le status d'une ligne suivie vient de `agile_statuses.category`.


- Bob : `deploy/bob/da.sh` → `/opt/data/dynamite` sur le serveur de l'agent, fiche `deploy/bob/BOB_LE_MINEUR.md` → SOUL de l'agent ; recherche élargie dans `core/bot.py` (`_widen`, `STOP`).


- Mise à jour en ligne (D-O-045) : `core/update_online.py` (réglage dans data/updates/online.json, tâche `_run`, `/progress`), écran `static/js/admin_update_online.js` ; le site de test se règle par `release_site` dans la config.


- Bob (D-O-044) : `core/bot.py` (routes, clés, liens), `core/bot_admin.py`, `static/js/admin_bob.js`, fiche `deploy/bob/BOB_LE_MINEUR.md` ; un module se branche par `bot_summary` et `search`. Pointeur : `static/js/tools/pointer.js` (`DA.pointTo`, `DA.pointLink`).


- Installation (D-O-042) : page `tools/site/installation.html` (`#f-traefik`, `[data-proxy]`), `install.js` (`state.traefik`), `installer.md` section A étape 4, `deploy/install.sh` (détection avant le pare-feu). Site : `tools/site_text.NEWS` pour les nouveautés.


- Exporter Diamond (D-O-041) : `modules/diamond/export_data.gather` lit tout une fois ; `export_xlsx.build`, `export_drawio.build`, `export_docx.build` ; `xlsx_book.Book` pour d'autres classeurs de présentation. Vérification visuelle : LibreOffice (xlsx / docx → PDF) et mxGraph (draw.io) dans le navigateur de test.


- Logo (D-O-040) : `.brand` dans `static/css/app.css` (`@font-face "DA Logo"`), `brand()` dans `static/js/app.js` ; pour d'autres lettres, refaire le sous-ensemble de Baloo 2 avec fontTools (`instancer` wght=800 puis `subset` en woff2).


- Performances (D-O-039) : `core/static_cache.py` (`get`, `not_modified`, `accepts_gzip`). Prochaine piste si besoin : chargement des scripts d'un module à l'ouverture de son onglet (`DA.loadModuleAssets`).


- Partager (D-O-038) : `static/js/tools/share.js` (`WAYS` : [groupe, nom, adresse(w, téléphone)] ; `null` = montrer le code QR) et `static/js/tools/qr.js` (`DA.qr`, `DA.qrCanvas`).


- Partager (D-O-038) : `static/js/tools/share.js` (`WAYS` pour ajouter un mode, `what()` pour le titre et la citation) ; icône `share` dans `tools/make_sketch_assets.py`.


- DFMEA complet (D-O-037) : `modules/diamond/dfmea_complete.py` (`complete`, `pick`, `api_complete`) et `modules/diamond/dfmea_practices.py` (`THEMES`, `GENERAL`, `block`, `ras`). Pour ajouter une bonne pratique ou un thème, éditer `THEMES` (mots sans accents, au début d'un mot). `starter_diamond.apply` appelle `complete` en dernier.


- Téléphone, l'essentiel (D-O-036) : `static/js/tools/mobile_views.js` (`PC_ONLY`, `CARDS`, `dynamiteBar`, `share`) ; règles dans la deuxième partie de `static/css/mobile.css` (`table.data[data-cards]`, `.pc-only-note`, `.dy-fab`). Les colonnes cachées des cartes se nomment par leur en-tête (`td[data-label=…]`).


- Choix multiples (D-O-035) : `DA.choiceBatch(box, apply)` dans `static/js/tools/choices.js` ; usages : `structure_parts.js` (panneau d'une fonction → `state.runMany`), `dfmea.js` (Colonnes, `state.colsOpen`).


- Téléphones (D-O-034) : `static/js/tools/mobile.js` (observe `#app`, déplace `nav.tabs`, `.topbar-tools`, `nav.tabs-end`, `.admin-tab` dans `body > .nav-drawer`), `static/css/mobile.css` (règles `html.da-phone …` sous 760 px). Un écran neuf : vérifier à 384 px que `document.documentElement.scrollWidth` reste 384.


- Essai clé (D-O-033) : `modules/diamond/dfmea.py` (`tests()` : Space puis TESTING ; `_fields` valide `test_id` ; `_rows` joint `test_code`, `test_title`, `test_space`) ; écran `dfmea_table.js` (`keyTest`) ; Starter : `starter_diamond.parse(..., test_refs)`, `apply(..., test_ids)` (ref → id de ligne).


- Défilement (0.60.23) : `static/js/tools/scrollkeep.js` (`DA.keepScroll(fn)`, `DA.holdScroll()` / `DA.releaseScroll(s)`) ; `DA.diamond.later` l'utilise ; `app.js` `route()` → `routeTo()` tient la position quand `module/KEY` ne change pas. Un module qui redessine hors de ces chemins peut appeler `DA.keepScroll(() => draw(...))`.


- Starter + Diamond (D-O-032) : `core/starter_diamond.py` (`parse`, `apply`, `counts`) appelé par `core/starter.parse` et `starter_apply.api_apply` ; plan : `modules/exploration/reference.py` (`build`, `apply`). Exemple : `tools/make_starter_diamond_example.py` réécrit la clé `diamond` de `lampe_bureau.json` depuis `modules/diamond/example*.py`. Prompt : bloc 5 de `tools/site/starter.md` / `en/starter.md`. `tests/test_starter_diamond.py`.


- Space de travail (D-O-030) : `static/js/tools/spaces.js` (`track` sur hashchange → sessionStorage `da.workSpace`, `workKey()` utilisé par `enter()` et Tools, `star()` / `withStar()` à côté des listes déroulantes). `core/spacecopy.py` : partie `diamond` (tables `DIAMOND`).


- Pièces (D-O-031) : `modules/diamond/parts.py` (`rows`, `analysis`, API), `example_parts.py` ; migration diamond 5 ; `structure.payload` ajoute `parts`, `part_checks`, `part_stats`. Écran : `static/js/diamond/structure_parts.js` (vue « parts », `partsPanel`, `partsByFunction`), étiquettes dans `structure_draw.js` (`partTags`). Timesheet : `weeks.problems(rows, conn)` contrôle le Funding Space. Reste à faire : `core/spacecopy.py` ne connaît pas encore les tables Diamond.


- Initiales et réglages (D-O-030) : `core/prefs.py` (`initial_candidates`, `ensure_initials`, `fill_initials`, `_put` = fusion json_patch : passer seulement les clés à changer) ; appels dans `router.py` (avant le garde 428), `session_api._me_payload`, `startup.run`, créations de comptes. `tests/test_initials_auto.py`.


- Prompt Project Starter (D-O-019) : textes `tools/site/starter.md` et `tools/site/en/starter.md` ({{VALUES}}, {{EXAMPLE}} remplis par `core/starter_prompt.py`) ; `GET /api/starter/prompt?lang=fr|en[&download=1]` ; écran `static/js/admin_starter.js` (`promptBox`). `tests/test_starter_prompt.py`.


- Derrière Traefik (D-O-029) : `core/proxy.py` (appelé par `core/router.py` : `_peer()` par requête, refus en tête de `_dispatch`), `core/tls.check_start` accepte HTTP sur le réseau seulement avec `trusted_proxies`. Installation : `deploy/install_traefik.sh` (appelé par `install.sh --traefik`). Sur le VPS de JP : Traefik `/docker/traefik` (une autre application Docker à côté), Dynamite | Agile `/docker/dynamite-agile` + `/opt/dynamite_agile` ; sauvegarde d'avant installation `/root/sauvegarde-avant-dynamite-20261104-1930.tgz`.


- Golden Nuggets (D-O-028) : contenu dans `static/js/diamond/nuggets_content.js` (PRINCIPLES, ALGORITHM, RULES), écran `nuggets.js` ; `tests/test_diamond_nuggets.py` compte 20 / 5 / 5 et vérifie l'usage de chacun. Diamond est complet : arbre, structure, risques, DFMEA, nuggets.


- DFMEA (D-O-027) : `modules/diamond/dfmea.py` (lignes, positions, `checks`, Depuis l'arbre / les risques, CSV), `dfmea_ap.py` (tableau AP, échelles, RPN), `example_dfmea.py` ; migration diamond 4. Écran : `static/js/diamond/dfmea.js` (vue, outils, colonnes en localStorage `diamond.dfmea.columns`), `dfmea_table.js` (tableur), `dfmea_legend.js` (#/diamond/KEY/dfmeaap) ; `static/css/diamond_dfmea.css`. `tests/test_diamond_dfmea.py`. Reste à faire : « Copier / composer un Space » ne connaît pas encore les tables Diamond (core/spacecopy.py).


- Risques projet (D-O-026) : `modules/diamond/risks.py` (champs, niveaux `level()`, `checks`, CSV), `example_risks.py` ; migration diamond 3. Écran : `static/js/diamond/risks.js` (carte, filtres, registre compact quand le panneau est ouvert), `risks_panel.js`. Le DFMEA (0.60.15) reprend `diamond_functions` et les risques `to_dfmea = 1`. `tests/test_diamond_risks.py`.


- Structure fonctionnelle (D-O-025) : `modules/diamond/structure.py` (vues, règles des flux, `checks`, positions), `example_structure.py` (lampe) ; migration diamond 2. Écran : `static/js/diamond/structure.js` (vue, onglets, outils), `structure_draw.js` (disposition, cadres, courbes SVG sans texte, glisser), `structure_panel.js`. `tests/test_diamond_structure.py`. Le DFMEA (0.60.15) reprendra `diamond_functions` ; « Copier / composer un Space » ne connaît pas encore Diamond.


- Versions officielles (D-O-024) : **à chaque version, écrire `docs/releases/<version>.json`** (résumé FR / EN, changements, fichiers). `core/release.py` (manifeste, série, étapes par version, fichiers modifiés à la main, `api_later`), appelé par `core/update.py` ; `tools/build_release.py` ; `tools/site/versions.html` + `versions.js` (FR / EN) ; workflow `.github/workflows/pages.yml` (construit `site/updates/`). Écran : `static/js/admin_update_official.js`. `tests/test_release.py` (paquet reproductible, refus d'un paquet modifié, Plus tard, série 0.60.98 → 0.60.99 appliquée, page et workflow).


- Diamond (D-O-023) : `modules/diamond/` — `functions.py` (règles de l'arbre : niveaux, `in_tree`, conseils `checks`, déplacements, archivage qui garde le numéro), `example.py` (lampe de bureau), migration diamond 1 (`diamond_functions`, liée à `projects(id)` : sauvegarde et restauration par le noyau). Écran : `static/js/diamond/` (`diamond.js` coquille Agile, `tree_layout.js` dessin HTML + SVG sans texte, `tree_panel.js`, `tree.js`) et `static/css/diamond.css`. Le DFMEA lira `diamond_functions` (id et numéro). « Copier / composer un Space » (`core/spacecopy.py`) ne connaît pas encore Diamond : à ajouter avec le DFMEA. `tests/test_diamond.py`.


- Windows (D-O-022) : `deploy/install.ps1` (UTF-8 avec BOM, PowerShell 5.1), `tools/make_team_ca.py`, `tools/write_config.py`, chemin D de `tools/site/installation.html` et `installer.md` (FR / EN). **Pas encore exécuté sur un vrai Windows** : la session de développement n'a ni Windows ni PowerShell ; à essayer avant de l'annoncer.

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
