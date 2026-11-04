# Dynamite | Agile — Registre des décisions (branche `open/v0.60`)

Décisions de la branche open source, numérotées **D-O-xxx**. Les décisions plus anciennes (D-A-xxx, D-B-xxx), citées
par leur numéro dans le code, sont indexées dans `docs/DECISIONS_ANTERIEURES.md` : elles restent valables pour le
noyau tant qu'une décision D-O ne les remplace pas.

---

### D-O-001 — Branche open source et numérotation (2026-11-03)
**Contexte :** Dynamite | Agile devient un outil générique et open source pour les étudiants du baccalauréat en
conception de produit et les équipes de start-up, installable sur un VPS Linux.
**Décision :** branche `open/v0.60`. Première version 0.60.01, puis +1 sur le dernier chiffre à chaque livraison
(0.60.02, 0.60.03…). Les règles techniques restent : bibliothèque standard Python, aucune ressource externe, CSRF,
journal d'audit, `el()`, fichiers sous 500 lignes, `data-new` sur tout élément nouveau, migrations additives, une
question à la fois, termes techniques en anglais et phrases en français.

### D-O-002 — Identité générique (2026-11-03)
**Décision :** nom et logo en texte « Dynamite | Agile » (favicon + nom, classe `.da-logo`), jeton `--brand-blue`,
gabarit Word générique `modules/testing/templates/document.docx` (`tools/brand_doc_template.py` pour y mettre son
logo et son pied de page), formats de fichiers `dynamite-*` (sauvegarde, paquet de données, déménagement), balises de
configuration `da:`. About : l'auteur et la construction avec Claude Opus 5.5 en octobre 2026.

### D-O-003 — Thèmes (2026-11-03)
**Décision :** deux thèmes au choix : « Thème par défaut » (croquis d'ingénieur, valeur stockée `carnet`) et
Terminal R&D ; `prefs.get` ramène tout thème inconnu au défaut (ex. après la restauration d'une vieille sauvegarde).
Les éléments graphiques actuels (icônes, logos des modules, illustrations) sont gardés tels quels et servent aussi au
site web (D-O-015).

### D-O-004 — Contenu retiré (2026-11-03)
**Décision :** tout le contenu propre à l'usage d'origine est retiré : projets et Spaces d'exemple, catalogues de
requis, besoins et essais d'un autre domaine, normes sectorielles, cycle de documents, codes de temps et feuilles
fictives, skill de mentorat, guide TLS d'une PKI d'entreprise, captures du guide Agile, outils séparés. Les mécanismes
génériques restent (Funding Spaces et Budget Lines, organismes, réclamations, banque de vacances, listes centrales) :
voir D-O-008.

### D-O-005 — Contenu générique d'un produit grand public mécatronique (2026-11-03)
**Décision :** Test Base de 34 essais (sécurité électrique CSA C22.2 / UL 60335-1, CEM ICES-003 / FCC Part 15 / CISPR 32
/ IEC 61000-4-x, IEC 60335 ou 62368-1, environnement IEC 60068, IP IEC 60529, chute, durée de vie, RoHS, UL 94,
firmware, usage, fin de ligne, vérification sans essai) et 7 procédures ; un sujet sans procédure propre est couvert
par une voisine (`data_procedures.COVERS`). Catalogue de requis : 12 besoins (GN-xxx) et 35 requis (GR-xxx),
`tools/generic_requirements.py` → `deploy/requis_generiques.csv`, chaque requis relié à son essai ; importé dans le
Space d'exemple EQP au démarrage de développement. Les valeurs [TBD] viennent du CdCF de l'équipe.

### D-O-006 — Generator et Timesheet campés sur le PDP du cours (2026-11-03)
**Décision :** Generator : livrables du PDP par phase (MIP, ETM, SPP, ECH, RSK ; RCS, BES, AF, CDCF, DFQ, MMO, PUGH ;
RC, SSY, CALC, AMDEC, DR ; RVE, PEX, REX, FAB ; documents généraux), dossier
`Documents/<phase>/<étape>-<sous-étape>_<SYSTÈME>/`, colonnes `codex_refs.pdp_step` / `pdp_sub`. Timesheet : jeu de
codes `pdp` par défaut — A. Pré-étude (A-01 à A-06), B. Étude conceptuelle (B-07 à B-12), C. Conception (C-13 à
C-15), D. Fabrication et validation du prototype (D-FAB, D-19 à D-21). La figure du PDP ne numérote pas les étapes
16 à 18 : « Mise en plan et fabrication du prototype » porte le code D-FAB (validé, D-O-013).

### D-O-007 — Équipe d'exemple et « Profil d'études » (2026-11-03)
**Décision :** comptes fictifs Nina (Génie mécanique, cheffe de projet, admin du Space EQP), Léa (Génie électrique),
Hugo (Design industriel), Alexis (Génie informatique), dans `deploy/utilisateurs_exemple.txt`. Nouveau champ
« Profil d'études » : colonne `users.study_profile` (migration `core` 17), directive `profil` des règles d'accès,
champ de création et bouton « Profil… » dans ⚙ Admin → Comptes (`data-new="0.60.01-study-profile"`). Les questions
Q&R de l'équipe au client ont la direction `team`.

### D-O-008 — Vacances et réclamations de financement gardées (2026-11-03, demande de JP)
**Contexte :** des équipes de start-up utiliseront aussi l'outil ; elles réclament des heures à des programmes de
financement publics et doivent justifier chaque heure.
**Décision :** la banque de vacances reste dans le profil (Paramètres, et ⚙ Admin → Comptes → « Feuille de
temps… », journalisée), avec le congé santé. Ils vivent dans le Space **INT** « Interne — temps hors projet et
congés », créé au premier démarrage, ouvert à tous, organisme « Interne », jeu `interne` : INT-01 à INT-05 (réunions,
formation, administration et demandes de financement, équipement, représentation) et **INT-VAC** (déduit de la
banque) / **INT-SAN** (sous approbation, non déduit), jamais réclamables. Page « Politique de l'équipe — vacances et
congés » dans INT (à compléter). Le vocabulaire **Funding Space / Budget Line** est gardé : un projet financé reçoit
son Funding Space, ses Budget Lines (réclamables ou non, import / export Excel), son organisme et son contrat ;
l'export Excel (Sommaire, Budget Lines avec chaque plage et sa justification, Détail, Lisez-moi) et le rapport Word
au destinataire (organisme de subvention ou client, attestation) se produisent sans ressaisie.

### D-O-009 — Contenu de référence réécrit en contenu original (2026-11-03, brief §5 Q1)
**Contexte :** les documents de cours d'origine (2005 et 2012) ne sont plus utilisés depuis une vingtaine d'années.
**Décision :** les Spaces de référence (pistolet à colle chaude, imprimante à jet d'encre, machine à commande
numérique pour bois mou) et les notes de cours sont **réécrits en contenu original** : mêmes méthodes (analyse
fonctionnelle, arbre à 3 niveaux, SAFE, RESEAU, interacteurs, matrice morphologique, Pugh, CdCF), mais textes, arbres,
valeurs et figures rédigés pour Dynamite | Agile, sans reprise de texte, de figure ni de mise en page, et sans nom
d'entreprise. Les documents d'origine ne vont ni dans le dépôt ni dans un paquet de données.

### D-O-010 — Licence MIT (2026-11-03, brief §5 Q2)
**Décision :** le code et le contenu réécrit (D-O-009) sont publiés sous licence **MIT**, « Copyright (c) 2026
Jean-Philippe Desbiens » (fichier `LICENSE` à la racine). Mention dans About (`data-new="0.60.01-license"`).
Toute bibliothèque ajoutée un jour devra avoir une licence compatible (aucune pour l'instant : bibliothèque standard).

### D-O-011 — Dépôt public sur GitHub : `dynamite-agile` (2026-11-03, brief §5 Q3)
**Décision :** le dépôt public est hébergé sur **GitHub**, sous le nom **`dynamite-agile`** ; le site web (D-O-015)
est publié avec GitHub Pages. Compte propriétaire (compte personnel de JP ou organisation dédiée) à préciser au moment
de créer le dépôt.

### D-O-012 — Aucune référence à l'usage ni au domaine d'origine, base propre (2026-11-03, demande de JP)
**Décision :** ni le code, ni les migrations, ni les commentaires, ni les tests, ni la documentation, ni les journaux,
ni le site, ni l'historique git ne nomment l'entreprise ni le domaine d'origine (produits, normes, vocabulaire du
secteur). Comme aucune base de données antérieure n'est migrée vers cette branche, 0.60.02 en est la **base propre** :
les migrations d'origine sont nettoyées (Q&R `team` dès la création de la table, colonnes du Generator `pdp_step` /
`pdp_sub`, plus de colonnes de structure inutilisées, plus de migration de nettoyage) ; à partir de là, les migrations
redeviennent strictement additives. L'historique des versions d'avant est remplacé par l'index
`docs/DECISIONS_ANTERIEURES.md`. `tests/test_open_v060.py` balaie tout le dépôt à la recherche de ces mots.

### D-O-013 — Réponses aux questions du brief §5 Q4 et Q5 (2026-11-03, « oui pour toutes tes questions »)
**Décision :** modules hors cours gardés : évaluation annuelle et Mes objectifs (pour les start-ups ; une évaluation
par les pairs en trois étapes — début, mi-session, fin de projet — viendra pour les équipes étudiantes), évaluation de
stage, Mon équipe, Training (les méthodes du cours s'y ajouteront), Help et HEADLAMP. Profils d'études de l'équipe
d'exemple confirmés (D-O-007) ; code D-FAB confirmé (D-O-006).

### D-O-014 — Les noms des modules suivent la mine (2026-11-03, demande de JP)
**Décision :** les noms des modules reprennent le vocabulaire minier ; leurs analogies sont documentées dans
`docs/NOMS_DES_MODULES.md`, dans Help (FAQ) et sur le site web : on prospecte (Exploration), on dynamite le savoir brut
(Dynamite), on extrait l'or des requis (Goldmine), on fait l'essai du minerai (Testing), etc.

### D-O-015 — Le site web est un livrable distinct de la plateforme (2026-11-03, demande de JP)
**Décision :** le site web marketing (page d'entrée, procédure d'installation, guide d'utilisation) vit dans le dossier
`site/` du dépôt, publié avec GitHub Pages ; il n'est pas servi par la plateforme. Il peut reprendre des contenus de
l'outil, mais ses objectifs sont autres : faire comprendre et donner envie, puis installer et prendre en main. Page
d'entrée : une storyline défilante à animations progressives, qui reprend la séquence de la journée de l'équipe
(Dashboard → Goldmine → Exploration → Agile → Dynamite → Testing → Timesheet → Training & Help) et amène doucement au
vif du sujet ; graphiques actuels de l'outil, aucune ressource externe, mouvement coupé par `prefers-reduced-motion`.

### D-O-016 — Installation pour débutants, en une commande (2026-11-03, demande de JP)
**Contexte :** l'installation doit être aussi facile que celle des outils qui donnent leurs commandes prêtes à copier ; la
destination change d'une personne à l'autre.
**Décision :** `site/installation.html` commence par le choix de la destination — **serveur en ligne** (VPS + domaine,
HTTPS), **serveur en essai privé** (sans domaine, tunnel SSH, `install.sh --essai`), **mon ordinateur** (onglets Windows,
macOS, Linux). Des champs domaine, courriel et IP remplissent les commandes (rien n'est envoyé ; mémorisés dans le
navigateur seulement) ; chaque bloc dit où le coller (« sur votre ordinateur » / « sur le serveur »), ce qu'on doit voir
ensuite, et se copie d'un clic ; cases « C'est fait » et barre de progression ; aides Hostinger repliables ; dépannage par
message. Un encadré invite à ouvrir un assistant IA à côté et lui donne un message prêt à coller avec le lien de la
procédure et `site/installer.md`, guide écrit pour l'assistant (une commande à la fois, jamais de mot de passe).
`deploy/install.sh` se lance aussi par `curl … | sudo bash -s -- domaine courriel` : il récupère le code dans
`/opt/dynamite_agile`, vérifie le DNS et les ports 80 / 443 avant certbot ; le site publie sa copie (`site/install.sh`,
dépôt renseigné par `tools/build_site.py`, constantes `OWNER` et `NAME` : `jpdesbiens11/Dynamite-Agile`, renseignées le 2026-11-04).

### D-O-017 — Interface et site en français et en anglais (2026-11-03, brief §5 Q6 : « FR/EN for sure at least »)
**Décision :** Dynamite | Agile devient bilingue FR / EN (au moins ; d'autres langues pourront suivre par le même
mécanisme). Remplace D-B-042 (français seulement). Le français reste la langue de référence. **Les noms des modules
(Dashboard, Goldmine, Exploration, Agile, Dynamite, Testing, Tools, Generator, Training, Timesheet, Help, HeadLamp, About)
et tout le contenu technique déjà en anglais restent tels quels dans les deux langues** (champs, statuts, types,
workflows, catégories, catalogues, Test Base, codes) ; seules les phrases françaises reçoivent leur version anglaise. Ordre prévu, une itération à la fois : (1) le site web (pages EN, sélecteur de
langue, `installer.md` en anglais) ; (2) le cadre de l'outil (choix `language` fr / en dans les Paramètres, barre du
haut, menus, Paramètres, Admin, messages d'erreur du serveur par catalogue) ; (3) chaque module ; (4) le contenu de
Help, de HEADLAMP, des tests Training, des exemples et des exports Word.

### D-O-018 — Un seul projet Claude porte la branche (2026-11-03, brief §5 Q7)
**Décision :** la règle A / B à tour de rôle ne s'applique plus : un seul compte (Max), un seul projet Claude, un chantier
à la fois. `docs/FONDATIONS.md` §11 est simplifié ; `ETAT_PROJET.md` garde son bloc « Relais » pour reprendre d'une
conversation à l'autre, sans champ « Session active ».

### D-O-019 — Démarrer un projet avec un assistant IA : le fichier Project Starter (2026-11-04, demande de JP)
**Contexte :** un débutant installe l'outil, puis se retrouve devant des modules vides ; il ne sait pas quels requis,
quelles normes, quels essais ni quels codes de temps conviennent à son industrie et à son marché.
**Décision :** un prompt public `site/starter.md`, à coller dans Claude.ai, Claude Code ou un autre assistant, pose ses
questions une à la fois, avec des choix de réponse, et produit un fichier JSON `dynamite-project-starter` (version 1,
`docs/STARTER_FORMAT.md`). Le bouton « Commencer », mis en évidence dans l'outil, le lit et crée un **nouveau Space à
côté des exemples** (rien n'est supprimé ni écrasé). Choix de JP, une question à la fois : (1) texte à coller plutôt
qu'un skill ; (2) nouveau Space à côté des exemples ; (3) comptes de l'équipe créés à l'approbation, mot de passe
temporaire affiché une fois, jamais administrateur, nom existant réutilisé tel quel ; (4) normes et essais générés
librement par l'IA, tous « À vérifier » — un requis ne passe à « Approuvé » qu'après confirmation de sa norme (édition,
date) par une personne ; (5) codes de temps générés par l'IA, deux niveaux, 40 au plus, modifiables dans l'aperçu ;
(6) pages Dynamite libres, 30 au plus, deux niveaux, texte et blocs seulement, marquées « Brouillon IA » ;
(7) livraison en pull request sur `jpdesbiens11/Dynamite-Agile`. Le fichier n'est pas scellé : `core/starter.py` vérifie
tout et retire au fichier ce qu'une personne seule décide. Itérations : 0.60.05 le format, le validateur,
`tools/check_starter.py` et trois exemples ; 0.60.06 l'écran « Commencer » (aperçu, création en une transaction,
audit) ; 0.60.07 le prompt FR / EN et sa page.
**Complément (0.60.06, 2026-11-04) :** la création du Space est livrée côté serveur (`core/starter_apply.py`,
`POST /api/starter/check` puis `/api/starter/apply`, administrateurs), l'écran « Commencer » et la confirmation des
normes suivent en 0.60.07, le prompt `starter.md` en 0.60.08. Précisions prises en codant : (a) le `subject` d'un essai
est un code de Testing (`func`, `elec`…) et un code de temps suit la forme de Timesheet (`[A-Z]{1,5}-[A-Z0-9]{2,4}`,
unique sur le site ; un code déjà pris bloque la création jusqu'à ce qu'il soit renommé ou retiré) ; (b) les codes du
projet forment un Funding Space `starter-<clé>` rattaché au Space ; (c) la première page sans parent remplace la page
d'accueil créée avec le Space, les autres pages sans parent vont sous elle ; (d) un requis sans essai, quand le fichier
en contient, est lié à un essai « Essai à définir (Project Starter) » — un Space qui a des essais exige qu'un requis en
nomme un (D-B-079) ; (e) la norme, l'édition et la clause d'un requis vont dans « Source Document » ; « À vérifier » est
gardé dans `agile_requirements.standard_review` et `testing_tests.review` (migrations additives agile 15, testing 5).
**Complément (0.60.07, 2026-11-04) :** l'écran est livré dans ⚙ Admin → Spaces → « Commencer » (`static/js/admin_starter.js`) :
choisir le fichier ou un exemple de `deploy/starter_exemples/` (servis par `GET /api/starter/examples`), lire l'aperçu,
changer la clé du Space, renommer ou retirer un code de temps, créer, puis lire une seule fois les mots de passe
temporaires. Le Dashboard d'un administrateur met « Commencer » en avant tant qu'aucun projet n'a été démarré ainsi
(`GET /api/starter/status`). « À vérifier » : `DA.review` (`static/js/tools/review.js`) montre le badge et le dialogue
« Confirmer la norme » (édition en vigueur obligatoire, clause facultative ; date et personne gardées) dans la fiche
requirement (`POST …/issues/<n>/standard-check`, `modules/agile/goldmine_review.py`) et la fiche d'essai
(`POST /api/testing/tests/<id>/review`, `modules/testing/review.py`). D'ici là, « Accepted » (requis) et « Approved »
(essai) sont refusés avec leur correctif, à l'écran comme à l'import CSV.

### D-O-020 — « Débuter » : le parcours d'un projet, à l'entrée de l'outil (2026-11-04, demande de JP)
**Contexte :** une fois l'outil installé, un débutant ne sait pas par où commencer ni à quoi sert chaque module au fil
du projet.
**Décision :** une page « Débuter » (`#/debuter`, `static/js/tools/debuter.js`, contenu dans `debuter_content.js`) déroule
le projet dans l'ordre du PDP du cours : avant le projet (démarrer avec un assistant IA ou à la main, prendre ses
repères, trouver son Space), A. Pré-étude, B. Étude conceptuelle, C. Conception, D. Fabrication et validation du
prototype (étapes et livrable de chaque phase), puis ce qui revient chaque semaine. Chaque étape nomme le module, dit
quoi y faire et ouvre l'écran dans le Space par défaut ; une étape d'administrateur est marquée et, pour les autres,
remplacée par « Votre administrateur s'en charge ». Choix de JP : **page d'arrivée après la connexion tant qu'on ne l'a
pas fermée** (préférence `debuter_done`), puis **onglet « Débuter » au début de la barre du haut** ; « Débuter » peut
aussi être choisie comme page d'arrivée dans les Paramètres. Le prompt `starter.md` passe en 0.60.09.

### D-O-021 — Le PDP modernisé avec le Lean Startup : une tornade de boucles MVP (2026-11-04, demande de JP)
**Contexte :** le MIP et les rapports du cours (RCS, RC, RVE) datent d'un PDP par phases ; en 2026, les équipes produit
matériel et logiciel travaillent par hypothèses, MVP successifs et Sprints Agile.
**Décision (choix de JP, une question à la fois) :**
1. **Les quatre phases restent** (lettres A à D, codes de temps A-01 … D-21 et clés inchangés), **et chacune devient une
   boucle Build → Measure → Learn** : un MVP teste les hypothèses les plus risquées, les Sprints Agile rythment le travail
   matériel et logiciel, la phase se ferme sur une revue et la décision de persévérer ou de pivoter. Les étapes « Rappel et
   mise à jour » (07, 13, 19) deviennent ce bilan. Image retenue : **une tornade** — les étapes se lisent de haut en bas,
   chaque boucle est une spire qui monte et s'élargit, et le produit sort par le haut à grande vitesse (schéma de
   « Débuter », `static/js/tools/debuter_tornado.js`, SVG sans texte).
2. **Le Lean Canvas et ses hypothèses à tester (LCV, MVP 0) remplace le MIP.**
3. **Revues industrielles et bilan MVP** pour les autres phases : Concept Review (CRV, MVP 1) remplace le RCS ; PDR puis
   CDR (MVP 2) remplacent le RC ; Validation Report (VVR, vérification et validation, MVP 3) remplace le RVE. Nouveaux
   types MVP (plan du MVP) et BML (bilan Build-Measure-Learn). MIP, RCS, RC et RVE sont des codes retirés : une référence
   déjà émise garde son code et son dossier, une nouvelle reçoit le code qui le remplace.
4. **Noms modernes des phases** : A. Discovery, B. Concept, C. Design, D. Validation et lancement ; dossiers du Generator
   `01_Discovery` … `04_Validation`, `05_Lean`.
Un site existant reçoit les nouveaux libellés de Timesheet au démarrage, seulement là où le libellé d'origine n'a pas été
reformulé. Le prompt `starter.md` passe en 0.60.10.
