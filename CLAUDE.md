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
- **Modules** : Dynamite (wiki), Agile (tickets, Change Management), Goldmine (requirements, needs, Q&R, Pugh),
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
