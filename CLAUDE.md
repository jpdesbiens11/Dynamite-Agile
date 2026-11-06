# Dynamite | Agile — Contexte pour Claude Code (branche open source `open/v0.60`)

## Où on en est

- **0.60.01** (2026-11-03) : première version de la branche open source pour les étudiants du baccalauréat en
  conception de produit. Identité générique (logo texte, `--brand-blue`, gabarit Word
  `modules/testing/templates/document.docx`), About (auteur, construit avec Claude Opus 5.5 en octobre 2026),
  « Thème par défaut » + Terminal R&D ; Test Base et requis d'un produit grand public mécatronique
  (`modules/testing/data_tests.py`, `tools/generic_requirements.py` → `deploy/requis_generiques.csv`) ; Generator sur
  les livrables du PDP (`modules/codex/catalog.py`) ; Timesheet : codes du PDP (A-01 … D-21), Space INT (temps interne,
  INT-VAC / INT-SAN), banque de vacances, Funding Spaces et Budget Lines pour les réclamations de financement ; équipe
  d'exemple Nina, Léa, Hugo, Alexis (`deploy/utilisateurs_exemple.txt`, `tools/seed_demo.py`, Space EQP) et
  « Profil d'études » (`users.study_profile`, migration core 17). Décisions D-O-001 à D-O-011.
- **0.60.02** (2026-11-03) : base propre, sans aucune référence à l'usage d'origine (D-O-012, garde dans
  `tests/test_open_v060.py`) ; colonnes Generator `pdp_step` / `pdp_sub` ; noms de la mine (`docs/NOMS_DES_MODULES.md`,
  FAQ de Help) ; site web distinct (`site/`, sources `tools/site/`, `tools/build_site.py`, GitHub Pages) ; installation
  VPS `deploy/install.sh`. Décisions D-O-012 à D-O-015.
- **0.60.03** : installation pour débutants (`tools/site/installation.html`, `install.js`, `installer.md` pour l'assistant IA),
  `deploy/install.sh` en une commande (`curl … | sudo bash -s -- domaine courriel`, ou `--essai`). D-O-016.
- **0.60.04** (2026-11-04) : FR / EN étape 1 (D-O-017) : site web en anglais (`tools/site/en/` → `site/en/`, textes
  partagés dans `tools/site_text.py`, bouton FR | EN), `installer.md` anglais, `install.sh` en anglais avec `DA_LANG=en`.
- **0.60.05** (2026-11-04) : format Project Starter (D-O-019) : fichier JSON préparé avec un assistant IA, validé par `core/starter.py` (`tools/check_starter.py`, `docs/STARTER_FORMAT.md`, exemples `deploy/starter_exemples/`) ; l'écran « Commencer » suit en 0.60.06.
- **0.60.06** (2026-11-04) : « Commencer » côté serveur (D-O-019) : `core/starter_apply.py`, `POST /api/starter/check` et `/api/starter/apply` (admins) créent le Space, l'équipe, les codes de temps, les essais et requis « À vérifier », les pages « Brouillon IA », en une transaction ; migrations agile 15 et testing 5. L'écran suit en 0.60.07.
- **0.60.07** (2026-11-04) : écran ⚙ Admin → Spaces → « Commencer » (`static/js/admin_starter.js`), carte du Dashboard, « À vérifier » et « Confirmer la norme » (`DA.review`, `goldmine_review.py`, `testing/review.py`) ; « Accepted » / « Approved » refusés tant que la norme n'est pas confirmée. Le prompt `starter.md` suit en 0.60.09.
- **0.60.08** (2026-11-04) : page « Débuter » (D-O-020, `#/debuter`, `static/js/tools/debuter.js` + `debuter_content.js`) : le parcours d'un projet selon le PDP, module par module ; page d'arrivée tant qu'on ne l'a pas fermée (pref `debuter_done`), puis onglet au début de la barre du haut.
- **0.60.09** (2026-11-04) : PDP modernisé avec le Lean Startup (D-O-021) : A. Discovery, B. Concept, C. Design, D. Validation et lancement, une boucle Build-Measure-Learn et son MVP par phase (tornade de « Débuter ») ; Lean Canvas (LCV), Concept Review (CRV), PDR / CDR, Validation Report (VVR), MVP et BML dans le Generator ; MIP, RCS, RC, RVE retirés.
- **0.60.10** (2026-11-04) : serveur d'équipe sur un PC Windows (D-O-022) : `deploy/install.ps1` (PowerShell admin, winget, tâche planifiée, pare-feu privé), autorité de certification de l'équipe `tools/make_team_ca.py`, `tools/write_config.py` ; 4e destination de la page d'installation. Le prompt `starter.md` suit en 0.60.11.
- **0.60.11** (2026-11-04) : module **Diamond** 💎 à 1 000 m (D-O-023, `modules/diamond/`, `static/js/diamond/`) : Arbre fonctionnel
  (primaire / secondaires / tertiaires / techniques, comment · pourquoi · quand, chemin critique, rétroaction, hors arbre,
  numéros F gardés pour toujours). Suivent : structure fonctionnelle, risques projet, DFMEA, Golden Nuggets, puis `starter.md`.
- **0.60.12** (2026-11-04) : **versions officielles** (D-O-024) : paquet par version construit par le workflow Pages
  (`tools/build_release.py`), page `versions.html`, Admin → Update (`core/release.py`) : une étape par version, plusieurs
  d'un coup, « Plus tard », données intactes. **À chaque version : écrire `docs/releases/<version>.json`.**
- **0.60.13** (2026-11-04) : Diamond → **Structure fonctionnelle** (D-O-025, `modules/diamond/structure.py`,
  `static/js/diamond/structure*.js`) : boundary diagram, entrées / sorties, vues générale et détaillée, flux énergie /
  matière / information, glisser, relier. Suivent : risques projet (0.60.14), DFMEA (0.60.15), Golden Nuggets (0.60.16).
- **0.60.14** (2026-11-04) : Diamond → **Risques projet** (D-O-026, `modules/diamond/risks.py`, `static/js/diamond/risks*.js`) :
  registre R-n, P × I sur 5 × 5, carte maintenant / résiduelle, stratégie, responsable, lien vers le DFMEA. Suivent : DFMEA
  (0.60.15), Golden Nuggets (0.60.16), `starter.md` (0.60.17).
- **0.60.15** (2026-11-04) : Diamond → **DFMEA** AIAG-VDA (D-O-027, `modules/diamond/dfmea*.py`, `static/js/diamond/dfmea*.js`) :
  trois niveaux, fonctions de l'arbre, S / O / D, RPN et AP, légende AP (#/diamond/KEY/dfmeaap). Suivent : Golden Nuggets
  (0.60.16), `starter.md` (0.60.17).
- **0.60.16** (2026-11-04) : Diamond → **Golden Nuggets** (D-O-028, `static/js/diamond/nuggets*.js`) : 20 premiers principes,
  algorithme en 5 étapes, règles SpaceX / Tesla. Diamond complet. Suit : `starter.md` (0.60.17).
- **0.60.17** (2026-11-04) : **installation derrière Traefik** (D-O-029) : `install.sh --traefik`, `deploy/install_traefik.sh`,
  noyau `core/proxy.py` (`trusted_proxies`). Suit : `starter.md` (0.60.18).
- **0.60.18** (2026-11-04) : **prompt de départ** `starter.md` (D-O-019) : entrevue de 20 questions pour un assistant IA,
  format exact tiré de l'outil (`core/starter_prompt.py`), « Copier le prompt » dans Commencer (`/api/starter/prompt`).
- **0.60.19** (2026-11-04) : **initiales d'office** d'après le nom (JDE, ADM ; D-O-030, `core/prefs.ensure_initials`) ; **Space par défaut**
  corrigé : `prefs._put` fusionne ses clés (json_patch), deux sauvegardes simultanées ne s'annulent plus.
- **0.60.20** (2026-11-04) : Diamond → **pièces sur les fonctions** (D-O-031, `modules/diamond/parts.py`, `static/js/diamond/structure_parts.js`) :
  matrice pièces × fonctions, pièces intégrées, fonctions à plusieurs pièces ; Timesheet : code hors du Funding Space refusé.
- **0.60.21** (2026-11-04) : **un seul Space pour tous les onglets** (`DA.spaces.workKey`, ☆ / ★ Space par défaut près de chaque liste) ;
  Copier / Dupliquer un Space emporte Diamond (`core/spacecopy.py`).
- **0.60.22** (2026-11-04) : **Commencer remplit Diamond** (D-O-032, `core/starter_diamond.py`) et un **plan de référence du PDP**
  (`modules/exploration/reference.py`, selon `project.weeks` et l'équipe) ; prompt de 26 questions.
- **0.60.23** (2026-11-04) : **la page reste où l'on regarde** (`DA.keepScroll`, `static/js/tools/scrollkeep.js` ; routeur du même Space) ;
  panneau d'un sous-système avec les pièces de ses tertiaires.
- **0.60.24** (2026-11-04) : DFMEA → **essai clé de la Test Base** dans Detection Controls (D-O-033, `diamond_dfmea.test_id`, migration diamond 6) ;
  Project Starter `dfmea[].test`.
- **0.60.25** (2026-11-04) : **téléphones** (D-O-034, `static/js/tools/mobile.js`, `static/css/mobile.css`) : barre compacte et menu tiroir ☰,
  une colonne, tableaux défilants, cibles de 44 px.
- **0.60.26** (2026-11-04) : **choix multiples appliqués ensemble** (D-O-035, `DA.choiceBatch`, `static/js/tools/choices.js`) : Appliquer ou clic à côté,
  Échap pour annuler (pièces d'une fonction, colonnes du DFMEA).
- **0.60.27** (2026-11-04) : **téléphone, l'essentiel** (D-O-036, `static/js/tools/mobile_views.js`) : Goldmine / Testing / Timesheet en cartes,
  Dynamite « + Page / ✨ Avec l'IA / Partager », Diamond, Gantt et Tools pour l'ordinateur.
- **0.60.28** (2026-11-04) : **DFMEA complet** (D-O-037, `modules/diamond/dfmea_complete.py`, `dfmea_practices.py`) : une ligne par fonction, essai clé relié,
  bonnes pratiques de l'industrie en prévention, RAS justifié ; Space étoilé d'abord (`DA.spaces.workKey`) ; About enrichi.
- **0.60.29** (2026-11-04) : **Partager** (D-O-038, `static/js/tools/share.js`) : feuille de partage du téléphone, ou lien, courriel, texto, Messenger,
  WhatsApp, Teams ; bouton de la barre du haut et, au téléphone, à côté du ☰.
- **0.60.30** (2026-11-04) : **Partager, 2e passe** (D-O-038, `static/js/tools/qr.js`) : lien copié à chaque choix, Gmail / Outlook / Messenger / WhatsApp /
  Telegram / Teams sur le web, code QR vers le téléphone.
- **0.60.31** (2026-11-04) : **plus léger sur le réseau** (D-O-039, `core/static_cache.py`) : ETag / 304 et gzip des fichiers de l'interface ;
  rechargement ~120 Ko au lieu de 1,5 Mo, première visite ~520 Ko.
- **0.60.32** (2026-11-04) : **logo « DynamiteAgile »** (D-O-040, `static/fonts/baloo2-logo.woff2`) : un mot, deux couleurs, Baloo 2 servie par le serveur ;
  outil, vitrine, site.
- **0.60.33** (2026-11-04) : **Exporter Diamond** (D-O-041, `modules/diamond/export_*.py`, `xlsx_book.py`) : tableaux → Excel, diagrammes → draw.io, rapport → Word ;
  marque « DynamiteAgile · Co-Intelligence WorkFlow™ ».
- **0.60.34** (2026-11-04) : **installation selon le serveur** (D-O-042) : question Traefik sur la page, l'assistant IA confirme, `install.sh` détecte Traefik ;
  site web avec Diamond et « Les nouveautés ».
- **0.60.35** (2026-11-04) : **le pointeur et Bob le mineur** (D-O-043 `static/js/tools/pointer.js`, D-O-044 `core/bot.py`, ⚙ Admin → Bob) : liens qui encadrent
  le point d'intérêt ; clé d'agent en lecture seule par Space, migration core 18.
- **0.60.36** (2026-11-04) : **mise à jour en ligne** (D-O-045, `core/update_online.py`, `static/js/admin_update_online.js`) : coupée par défaut, vérifier, cocher « Lu »,
  approuver, barre en % et détail en direct ; dernière version et date sur la page d'installation.
- **0.60.37** (2026-11-04) : **Bob plus sûr et plus rapide** (D-O-046) : commande `dynamite` (`deploy/bob/da.sh`), fiche directive sans curl,
  recherche de l'agent qui comprend une phrase et donne `best`.
- **0.60.38** (2026-11-04) : **responsables des actions** (D-O-047, `modules/diamond/actions.py`, migration diamond 7) : DFMEA avec responsable, échéance,
  status ; « Suivre dans Agile » (status lu sur le ticket) ; Mes actions Diamond ; actions dans la synthèse de Bob.
- **0.60.39** (2026-11-05) : **installation en 5 étapes** (D-O-048, `tools/site/installation.html`, `install.js`) : Linux ou Windows, VPS vide (Hostinger, Oracle
  Cloud gratuit, DigitalOcean), adresse (ou DuckDNS), connexion, une commande ; install.sh ouvre les iptables des images Oracle.
- **0.60.40** (2026-11-05) : **accueil en storyline** (D-O-049, `tools/site_text.py` MINE / STORY) : le besoin en 4 scènes, puis la descente dans l'ordre du projet,
  plus profonde et plus sombre, jusqu'aux diamants ; HeadLamp ne se traduit pas.
- **0.60.41** (2026-11-05) : **un Space, un produit** (D-O-050, `modules/help/reference.py`) : installation neuve vide sauf HeadLamp (bac à sable et bibliothèque de
  référence) ; TESTING / TOOLS / TRAINING / INT plus créés ; Test Base par Space, DFMEA sur ses essais, congés dans chaque Space ; `--exemple`.
- **0.60.42** (2026-11-05) : **le Space par défaut, tout l'environnement** (D-O-051) : Dashboard du produit (?all=1), recherche dans le Space par défaut,
  feuille de temps sur lui ; « Commencer » le règle pour l'équipe.
- **0.60.43** (2026-11-05) : **Project Starter complet** (D-O-052, `core/starter_more.py`, `core/starter_export.py`) : backlog Agile par MVP et livrables du
  Generator ; un Space éprouvé relu en fichier Project Starter sert de modèle au prompt (`/api/starter/export`, `?source=`).
- **0.60.44** (2026-11-05) : **installation selon l'endroit et l'ordinateur** (D-O-053) : VPS, serveur local sans Internet (`install.sh --local`) ou PC Windows ;
  « Votre ordinateur » (Windows, macOS, Linux) choisit chaque commande ; adresse Hostinger expliquée.
- **0.60.45** (2026-11-05) : **documentation des modules** (D-O-054, `modules/help/module_docs*.py`) : pourquoi, besoin, pas à pas, MVP 0 à MVP x, références classées ;
  HeadLamp (Help → Documentation des modules) et page Modules du site.
- **0.60.46** (2026-11-05) : **exemple académique Rover** (D-O-055, `tools/rover/`, `deploy/spaces_exemples/rover.json`) : tous les modules remplis de MVP 0 à MVP 3,
  à charger depuis la page d'installation (jamais par défaut) ; Project Starter `tools` (idéation, Pugh, Kepner-Tregoe, `core/starter_tools.py`).
- **0.60.47** (2026-11-05) : **Partager sur le site** (D-O-056, `tools/site/site.js`, `site_text.SHARE`) : la page en cours, feuille du téléphone ou menu de liens.
- **0.60.48** (2026-11-05) : **FR | EN dans la barre du haut** (D-O-057, `static/js/tools/langswitch.js`) ; thèmes seulement dans Paramètres.
- **0.60.49** (2026-11-05) : **un seul Space, DEMO** (D-O-058, `modules/help/headlamp.py`, `demo_example.py`) : ancien HeadLamp + Rover, sans compte d'exemple ;
  « Cacher pour tous » (`/api/admin/demo`) ; HEADLAMP renommé DEMO au démarrage.
- **0.60.50** (2026-11-05) : **exporter l'arbre et la structure** (D-O-059, `modules/diamond/export_pptx.py`, `pptx_book.py`, `static/js/diamond/export_menu.js`) :
  « Exporter ▾ » sur chaque écran (draw.io, PowerPoint à formes natives, Excel) ; `?only=tree | structure`.
- **0.60.51** (2026-11-06) : **Storyline** (D-O-060, `modules/diamond/story.py`, `static/js/diamond/story*.js`, `tools/story_pictos.py`) : l'usage du produit
  scène par scène avec 39 pictogrammes, avant l'arbre ; migration diamond 8. Suit : « Copier pour l'IA » (0.60.52).
- **0.60.52** (2026-11-06) : **Storyline → IA** (D-O-061, `modules/diamond/story_ai.py`, `static/js/diamond/story_ai.js`) : « Copier pour l'IA », « Importer la réponse
  de l'IA » (arbre vide) ; `diamond.story` au format Project Starter ; Storyline du Rover ; Storytelling retiré de Tools.
- **0.60.53** (2026-11-06) : **import Compléter / Tout remplacer** (D-O-062, `modules/diamond/import_merge.py`) : une partie manquante à la fois
  (accrochée à l'arbre existant) ou, pour un admin du Space, sauvegarde complète puis Diamond refait à partir du fichier.
- **0.60.54** (2026-11-06) : **le Rover, projet vivant** (D-O-063, `modules/help/demo_life*.py`) : dans DEMO, à la semaine 15 sur 15, équipe en comptes
  inactifs `demo.nina` … (personne ne s'y connecte), sprints, tickets, Change Management, Q&R, Test Plans, plan du PDP, heures, responsables.
- **0.60.55** (2026-11-06) : **la démo, c'est le Rover** (D-O-064) : le Space DEMO s'appelle « ROVER — la démo… » (clé DEMO gardée), accueil
  centré sur le Rover, plan du Rover en premier.
- **0.60.56** (2026-11-06) : **page d'installation sans serveur Linux local** (D-O-065) : serveur en ligne ou PC Windows de l'équipe.
- **0.60.57** (2026-11-06) : **install.ps1 réparé** (D-O-066) : dans `( … )`, une commande PowerShell coupée sur deux lignes finit par un accent grave.
- **0.60.58** (2026-11-06) : **winget `--source winget`** (D-O-067) : la source du Microsoft Store expirait et bloquait Git.
- **0.60.59** (2026-11-06) : **certificat depuis Documents** (D-O-068) : étape 5 Windows en trois sous-étapes, commande indépendante du dossier.
- **0.60.62** (2026-11-06) : **schémas Mermaid dans les exports PDF / Word** (D-O-071, `mermaid_png.js`, `export_mermaid.py`) : le navigateur
  dessine en PNG, le serveur met l'image et garde le code dessous en petit ; correctif des lignes de code qui se chevauchaient dans le PDF.
- **0.60.61** (2026-11-06) : **coûts et budget dans Diamond** (D-O-070, `modules/diamond/costs*.py`) : NRE, pièces en prototype et à trois
  volumes, budget global (NRE, prototypes, temps, contingence), CSV et version investisseurs ; le Rover est chiffré.
- **0.60.60** (2026-11-06) : **diagrammes Mermaid dans Dynamite** (D-O-069, `static/js/dynamite/mermaid_*.js`) : moteur maison (flowchart,
  séquence, états), schéma + « Voir le code » à la lecture, aperçu en direct dans l'éditeur (`data-skip`, jamais enregistré).
- **Modules** : Dynamite (wiki), Diamond (analyse fonctionnelle), Agile (tickets, Change Management), Goldmine (requirements, needs, Q&R, Pugh),
  Testing (Test Base, procédures, plans), Exploration (planification), Tools (Design : idéation, Pugh, Kepner-Tregoe ;
  Generator), Training, Timesheet, Help (HEADLAMP), About ; noyau `core/` (comptes, sessions + CSRF, droits par Space,
  audit, recherche, révisions, sauvegardes, Update, TLS).
- Feuille de route, questions ouvertes et relais : `docs/ETAT_PROJET.md` ; décisions : `docs/DECISIONS.md` ;
  règles techniques : `docs/FONDATIONS.md` (prime sur ce fichier) ; décisions antérieures D-A / D-B citées dans le
  code : `docs/DECISIONS_ANTERIEURES.md`.
- Tests : `python3 -m unittest discover -s tests -t .` puis `node tests/js/ai_markdown.js` et
  `node tests/js/editor_roundtrip.js`. Démarrage : `python3 app_dynamite_agile.py --dev-admin` (admin / admin).

## Comment travailler ici

- Une question à la fois si quelque chose est ambigu ; sinon, prendre
  l'hypothèse la plus raisonnable, la dire en une ligne, et avancer.
- Teste avant de considérer une fonctionnalité terminée : démarre le
  serveur localement (`python3 app_dynamite_agile.py --port 8080`, ou `python lancer_dev.py`), fais un
  test fonctionnel bout en bout (curl ou un petit script Python), pas
  seulement une relecture du code.
- Commit git après chaque étape fonctionnelle qui marche, avec un message
  clair. C'est le filet de sécurité — mieux vaut plusieurs petits commits
  qu'un gros.
- **Tout champ ou fonction nouveau porte `data-new="<version>-<clé>"`** (ex. `0.60.02-function-tree`) ;
  migrations additives seulement (jamais de colonne renommée ni supprimée).
- Interface, messages d'erreur : français et anglais (D-O-017, par étapes) ; les noms des modules et les **termes
  techniques restent en anglais** dans les deux langues (`docs/GLOSSARY_EN.md`). Code, commentaires, variables : en anglais.
- Un seul projet Claude porte la branche, un chantier à la fois (D-O-018, `docs/FONDATIONS.md` §11).
- Chaque fichier Python/JS reste sous 500 lignes ; découper plutôt que
  laisser grossir.

## Architecture — ne pas casser ces règles

- **`core/` est le socle partagé** : sessions, CSRF, permissions, audit,
  routeur, base de données. Un module ne le modifie jamais pour ses propres
  besoins — il l'utilise.
- **Un nouveau module** (Dynamite, Agile, ou un futur outil) s'ajoute via
  `core/modules.py` : ses tables (`SCHEMA`, toujours liées à
  `projects(id)`), ses routes (`ROUTES`, même forme que
  `core/session_api.py`), et une entrée dans `MODULE_MANIFEST`. Le routeur
  et la navigation les ramassent automatiquement — jamais besoin de
  toucher `core/router.py` ou `static/js/app.js` pour un nouvel onglet.
- **Sécurité non négociable** : toute écriture vérifie le rôle minimal via
  `core.permissions.require_project_role(...)`, tout contenu HTML affiché
  passe par une liste blanche avant stockage (à construire pour Dynamite),
  le DOM se construit avec `el()`/`textContent` en JS — jamais `innerHTML`
  sur une donnée serveur. Chaque écriture appelle
  `core.audit.log_action(...)`.
- **Aucune dépendance externe** : bibliothèque standard Python uniquement,
  aucun CDN, aucune police externe, aucun appel réseau sortant depuis le
  serveur ou la page. Chaque équipe l'héberge sur son propre serveur : le code
  se comporte comme sur un réseau fermé.
- **Exports** : un fichier construit à partir des données part en `RawFile` ; le noyau le marque de sa révision et l'inscrit au
  registre (D-B-129). Un fichier déposé par quelqu'un et renvoyé tel quel : `RawFile(..., export=False)`.
- **Transport** : jamais de TLS, de cookie ni d'en-tête de sécurité dans un module ; le noyau (`core/tls.py`,
  `core/router.py`) s'en charge. L'état de la connexion est dans `ctx.transport`.
- **Chemins** : toujours `Path(__file__).parent`, jamais le dossier
  courant. Le dossier `data/` (base, pièces jointes, logs, config) n'est
  jamais suivi par git et diffère par environnement.

## Réservé, ne pas construire avant qu'on le demande explicitement

Notifications courriel, agent de supervision, miroir chiffré des fichiers. Si une tâche semble s'en approcher,
signaler la question plutôt que de commencer.

## Système de conception (une fois qu'on attaque l'UI de Dynamite/Agile)

**Avant tout écran ou style : skill `.claude/skills/dynamite-design/SKILL.md`** (D-B-093), chargée
automatiquement par Claude Code. Elle prime sur toute autre skill de design ; `docs/FONDATIONS.md` prime sur elle.

Couleurs déjà en place dans `static/css/app.css` : `--dynamite` (accent
wiki, orange), `--agile` (accent action, bleu), `--panel` (barre du haut,
marine). Réutiliser les classes existantes (`.btn`, `.badge`, `.table
.data`, `.modal`, `.toast`) plutôt qu'en inventer de nouvelles. Police
système (`Segoe UI Variable Text`), pas de police chargée depuis le web.

## Déploiement

Ce dépôt tourne ici (VPS) comme environnement de développement et de test.
`deploy/DEPLOIEMENT_VPS.md` documente le service systemd pour le faire
tourner en continu une fois qu'un module est prêt à être testé en dehors
d'une session Claude Code. Le guide d'installation pas à pas pour une équipe
(VPS Linux, ligne de commande) et de personnalisation viendra dans l'outil (0.60.x).
